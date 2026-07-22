"""Filesystem run storage: one directory per run under the runs root.

Each run directory holds ``deal_config.json``, ``status.json``, and (once
solved) ``result.json`` / ``reopt_results.json``. No database — this mirrors
the repo's existing ``artifacts/results`` convention (PHASE-01, DEC-003).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

__all__ = ["RunStorage", "default_runs_dir"]

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_NON_TERMINAL_STATES = frozenset({"queued", "solving", "analyzing"})


def _write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON so a concurrent reader never observes a partial file.

    ``Path.write_text`` truncates then writes in place; a reader polling the
    same path (e.g. the webapp's status-polling HTTP endpoint, read from a
    different thread than the background solve worker) can land in that
    window and see a zero-length or partial file. Writing to a same-directory
    temp file and swapping it in with ``os.replace`` (atomic on POSIX and on
    Windows for same-volume renames) means a reader always sees either the
    fully-old or fully-new content, never an in-between state.

    On Windows, ``os.replace`` can raise a transient ``PermissionError``
    (WinError 5) if another thread has the destination open for reading at
    the exact instant of the swap — a sharing-violation, not a real failure.
    POSIX rename has no such restriction. Retry briefly rather than letting a
    concurrent reader turn a routine status update into a crash.
    """
    tmp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    last_error: Optional[OSError] = None
    for attempt in range(20):
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.005 * (attempt + 1))
    tmp_path.unlink(missing_ok=True)
    raise last_error  # type: ignore[misc]


def _read_json_with_retry(path: Path) -> Dict[str, Any]:
    """Read JSON, retrying briefly on Windows sharing-violation ``PermissionError``.

    Mirrors ``_write_json_atomic``'s retry: ``status.json`` is written by a
    background worker thread and polled by an HTTP handler thread at the same
    time, so a read can land in the same narrow Windows-only window where
    ``os.replace`` momentarily holds the destination path.
    """
    last_error: Optional[OSError] = None
    for attempt in range(20):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.005 * (attempt + 1))
    raise last_error  # type: ignore[misc]


def default_runs_dir() -> Path:
    import os

    override = os.environ.get("REOPT_PYSAM_VN_WEBAPP_RUNS_DIR")
    if override:
        return Path(override)
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "artifacts" / "webapp" / "runs"


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug or "deal"


class RunStorage:
    """Reads and writes run state under ``root`` (created lazily)."""

    def __init__(self, root: Union[str, Path]):
        self.root = Path(root)
        self._lock = threading.Lock()

    def _run_dir(self, run_id: str) -> Path:
        if not _RUN_ID_RE.match(run_id):
            raise KeyError(f"no such run: {run_id!r}")
        path = self.root / run_id
        if not path.exists():
            raise KeyError(f"no such run: {run_id!r}")
        return path

    _counter = 0

    def create_run(self, deal_config: Dict[str, Any]) -> str:
        with self._lock:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
            RunStorage._counter += 1
            slug = _slugify(deal_config.get("title") or deal_config.get("case") or "deal")
            run_id = f"{timestamp}-{RunStorage._counter:08d}-{slug}-{uuid.uuid4().hex[:6]}"
            run_dir = self.root / run_id
            run_dir.mkdir(parents=True, exist_ok=False)
            _write_json_atomic(run_dir / "deal_config.json", deal_config)
            status = {
                "run_id": run_id,
                "state": "queued",
                "created_at": timestamp,
                "seq": RunStorage._counter,
                "case": deal_config.get("case", ""),
                "mode": deal_config.get("mode", ""),
                "title": deal_config.get("title", ""),
            }
            _write_json_atomic(run_dir / "status.json", status)
            return run_id

    def get_deal_config(self, run_id: str) -> Dict[str, Any]:
        run_dir = self._run_dir(run_id)
        return json.loads((run_dir / "deal_config.json").read_text(encoding="utf-8"))

    def get_status(self, run_id: str) -> Dict[str, Any]:
        run_dir = self._run_dir(run_id)
        return _read_json_with_retry(run_dir / "status.json")

    def set_status(self, run_id: str, **fields: Any) -> None:
        with self._lock:
            run_dir = self._run_dir(run_id)
            status_path = run_dir / "status.json"
            status = _read_json_with_retry(status_path)
            status.update(fields)
            _write_json_atomic(status_path, status)

    def save_result(self, run_id: str, result: Dict[str, Any]) -> None:
        run_dir = self._run_dir(run_id)
        _write_json_atomic(run_dir / "result.json", result)

    def get_result(self, run_id: str) -> Optional[Dict[str, Any]]:
        run_dir = self._run_dir(run_id)
        result_path = run_dir / "result.json"
        if not result_path.exists():
            return None
        return json.loads(result_path.read_text(encoding="utf-8"))

    def save_reopt_results(self, run_id: str, reopt_results: Dict[str, Any]) -> None:
        run_dir = self._run_dir(run_id)
        _write_json_atomic(run_dir / "reopt_results.json", reopt_results)

    def get_reopt_results(self, run_id: str) -> Optional[Dict[str, Any]]:
        run_dir = self._run_dir(run_id)
        path = run_dir / "reopt_results.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_provenance(self, run_id: str, provenance: Dict[str, Any]) -> None:
        run_dir = self._run_dir(run_id)
        _write_json_atomic(run_dir / "provenance.json", provenance)

    def get_provenance(self, run_id: str) -> Optional[Dict[str, Any]]:
        run_dir = self._run_dir(run_id)
        path = run_dir / "provenance.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    _TERMINAL_STATES = frozenset({"done", "error"})

    def prune(self, older_than_days: int, *, dry_run: bool = True) -> List[str]:
        """Return run_ids in a terminal state older than ``older_than_days``.

        Never selects a run whose state is not terminal (``queued``/``solving``/
        ``analyzing`` are always kept regardless of age). When ``dry_run`` is
        False, the selected run directories are deleted.
        """
        if not self.root.exists():
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        stale: List[str] = []
        for run in self.list_runs():
            if run.get("state") not in self._TERMINAL_STATES:
                continue
            created_at = run.get("created_at", "")
            try:
                created = datetime.strptime(created_at, "%Y%m%dT%H%M%S%f").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
            if created < cutoff:
                stale.append(run["run_id"])
        if not dry_run:
            for run_id in stale:
                run_dir = self.root / run_id
                if run_dir.exists():
                    shutil.rmtree(run_dir)
        return stale

    def list_runs(self) -> List[Dict[str, Any]]:
        if not self.root.exists():
            return []
        runs = []
        for run_dir in self.root.iterdir():
            if not run_dir.is_dir():
                continue
            status_path = run_dir / "status.json"
            if not status_path.exists():
                continue
            runs.append(json.loads(status_path.read_text(encoding="utf-8")))
        runs.sort(key=lambda r: r.get("seq", 0), reverse=True)
        return runs

    def mark_interrupted_runs(self) -> List[str]:
        """Mark every run whose state is non-terminal (``queued``/``solving``/
        ``analyzing``) as ``error``. Called on app startup: a non-terminal run
        found at that point was orphaned by a previous process exiting mid-solve
        and can never progress on its own. Never auto-requeued (would silently
        re-spend NREL API quota on a run the user may have abandoned)."""
        interrupted: List[str] = []
        for run in self.list_runs():
            if run.get("state") in _NON_TERMINAL_STATES:
                run_id = run["run_id"]
                self.set_status(
                    run_id,
                    state="error",
                    message="Run was interrupted by an app restart before it finished.",
                    error_code="interrupted_restart",
                    error_hint="Clone this run from the history page and submit it again.",
                )
                interrupted.append(run_id)
        return interrupted

    def find_cached_run_id(self, solve_hash: str) -> Optional[str]:
        for run in self.list_runs():
            if run.get("solve_hash") == solve_hash and run.get("state") == "done":
                return run["run_id"]
        return None
