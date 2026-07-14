"""In-process background job manager for NREL solves (PHASE-02, DEC-004).

One worker thread processes a FIFO queue so at most one solve runs at a time
(protects NREL rate limits on a single-user tool). Deterministic runs (a
pre-solved ``results``/``extracted`` payload already in hand) never touch this
queue — ``routes/api.py`` executes those inline because they are sub-second.
"""

from __future__ import annotations

import hashlib
import json
import logging
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from reopt_pysam_vn.analysis.types import DealConfig
from reopt_pysam_vn.webapp import service
from reopt_pysam_vn.webapp.errors import to_user_error
from reopt_pysam_vn.webapp.storage import RunStorage

__all__ = ["JobManager"]

logger = logging.getLogger("reopt_pysam_vn.webapp.jobs")

_SENTINEL = object()

_REPO_ROOT = Path(__file__).resolve().parents[4]
_MANIFEST_PATH = _REPO_ROOT / "data" / "vietnam" / "manifest.json"


def _policy_data_versions() -> Dict[str, str]:
    """Read ``data/vietnam/manifest.json`` and return ``{key: version}`` for
    every active policy data file, using each file's own ``_meta.version``
    (falling back to the filename if a file has no version field)."""
    if not _MANIFEST_PATH.exists():
        return {}
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    versions: Dict[str, str] = {}
    for key, filename in manifest.items():
        if key == "_meta":
            continue
        file_path = _MANIFEST_PATH.parent / filename
        version = filename
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8-sig"))
                version = data.get("_meta", {}).get("version", filename)
            except (json.JSONDecodeError, OSError):
                pass
        versions[key] = version
    return versions


def _pysam_available() -> bool:
    try:
        import PySAM  # noqa: F401

        return True
    except ImportError:
        return False


def _package_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("reopt-pysam-vn")
    except PackageNotFoundError:
        return "unknown"


class JobManager:
    """Owns the background worker thread and the run's solve lifecycle."""

    def __init__(self, storage: RunStorage):
        self.storage = storage
        self._queue: "queue.Queue[Any]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="webapp-solve-worker")
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=5)
        self._thread = None

    def submit_solve(self, run_id: str, deal_config: Dict[str, Any], *, force_resolve: bool = False) -> None:
        self._queue.put((run_id, deal_config, force_resolve))

    def _worker_loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is _SENTINEL:
                return
            run_id, deal_config, force_resolve = item
            try:
                self._process(run_id, deal_config, force_resolve=force_resolve)
            except Exception as exc:  # noqa: BLE001 - surfaced to the run's status, not swallowed
                logger.exception("run %s failed", run_id)
                user_error = to_user_error(exc)
                self.storage.set_status(
                    run_id,
                    state="error",
                    message=user_error["message"],
                    error_code=user_error["code"],
                    error_hint=user_error["hint"],
                )

    def _process(self, run_id: str, deal_config: Dict[str, Any], *, force_resolve: bool) -> None:
        start_time = time.perf_counter()
        deal = DealConfig.from_dict(deal_config)
        if deal.mode != "onsite":
            user_error = to_user_error(
                service.MissingInputsError(
                    "only onsite deals can be solved live via the NREL REopt API; "
                    "offsite_dppa/both need a pre-solved `extracted` upload."
                )
            )
            self.storage.set_status(
                run_id,
                state="error",
                message=user_error["message"],
                error_code=user_error["code"],
                error_hint=user_error["hint"],
            )
            return

        solve_hash = service.solve_relevant_hash(deal_config)
        cached_run_id = None if force_resolve else self.storage.find_cached_run_id(solve_hash)

        self.storage.set_status(run_id, state="solving", solve_hash=solve_hash)
        key_fingerprint: Optional[str] = None
        if cached_run_id is not None:
            reopt_results = self.storage.get_reopt_results(cached_run_id)
            solver = "cached"
        else:
            api_key = service.load_nrel_api_key()
            key_fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]
            reopt_results = service.solve_onsite_via_nrel(deal)
            solver = "nrel_api"
        self.storage.save_reopt_results(run_id, reopt_results)

        self.storage.set_status(run_id, state="analyzing")
        extracted = {"loads_kw": list(deal.load.get("loads_kw", []))}
        result = service.run_analysis(deal, results=reopt_results, extracted=extracted)
        self.storage.save_result(run_id, result)

        provenance = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"),
            "solver": solver,
            "nrel_key_fingerprint": key_fingerprint,
            "solve_hash": solve_hash,
            "cache_hit": cached_run_id is not None,
            "cached_from_run_id": cached_run_id,
            "policy_data_versions": _policy_data_versions(),
            "wall_time_seconds": time.perf_counter() - start_time,
            "pysam_available": _pysam_available(),
            "package_version": _package_version(),
        }
        self.storage.write_provenance(run_id, provenance)
        self.storage.set_status(run_id, state="done")
