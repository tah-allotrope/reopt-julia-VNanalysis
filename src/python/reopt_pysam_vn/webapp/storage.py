"""Filesystem run storage: one directory per run under the runs root.

Each run directory holds ``deal_config.json``, ``status.json``, and (once
solved) ``result.json`` / ``reopt_results.json``. No database — this mirrors
the repo's existing ``artifacts/results`` convention (PHASE-01, DEC-003).
"""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

__all__ = ["RunStorage", "default_runs_dir"]

_SLUG_RE = re.compile(r"[^a-z0-9]+")


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
            (run_dir / "deal_config.json").write_text(
                json.dumps(deal_config, indent=2), encoding="utf-8"
            )
            status = {
                "run_id": run_id,
                "state": "queued",
                "created_at": timestamp,
                "seq": RunStorage._counter,
                "case": deal_config.get("case", ""),
                "mode": deal_config.get("mode", ""),
                "title": deal_config.get("title", ""),
            }
            (run_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
            return run_id

    def get_deal_config(self, run_id: str) -> Dict[str, Any]:
        run_dir = self._run_dir(run_id)
        return json.loads((run_dir / "deal_config.json").read_text(encoding="utf-8"))

    def get_status(self, run_id: str) -> Dict[str, Any]:
        run_dir = self._run_dir(run_id)
        return json.loads((run_dir / "status.json").read_text(encoding="utf-8"))

    def set_status(self, run_id: str, **fields: Any) -> None:
        with self._lock:
            run_dir = self._run_dir(run_id)
            status_path = run_dir / "status.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status.update(fields)
            status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    def save_result(self, run_id: str, result: Dict[str, Any]) -> None:
        run_dir = self._run_dir(run_id)
        (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    def get_result(self, run_id: str) -> Optional[Dict[str, Any]]:
        run_dir = self._run_dir(run_id)
        result_path = run_dir / "result.json"
        if not result_path.exists():
            return None
        return json.loads(result_path.read_text(encoding="utf-8"))

    def save_reopt_results(self, run_id: str, reopt_results: Dict[str, Any]) -> None:
        run_dir = self._run_dir(run_id)
        (run_dir / "reopt_results.json").write_text(
            json.dumps(reopt_results, indent=2), encoding="utf-8"
        )

    def get_reopt_results(self, run_id: str) -> Optional[Dict[str, Any]]:
        run_dir = self._run_dir(run_id)
        path = run_dir / "reopt_results.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

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

    def find_cached_run_id(self, solve_hash: str) -> Optional[str]:
        for run in self.list_runs():
            if run.get("solve_hash") == solve_hash and run.get("state") == "done":
                return run["run_id"]
        return None
