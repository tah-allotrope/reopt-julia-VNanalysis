"""In-process background job manager for NREL solves (PHASE-02, DEC-004).

One worker thread processes a FIFO queue so at most one solve runs at a time
(protects NREL rate limits on a single-user tool). Deterministic runs (a
pre-solved ``results``/``extracted`` payload already in hand) never touch this
queue — ``routes/api.py`` executes those inline because they are sub-second.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Dict, Optional

from reopt_pysam_vn.analysis.types import DealConfig
from reopt_pysam_vn.webapp import service
from reopt_pysam_vn.webapp.storage import RunStorage

__all__ = ["JobManager"]

logger = logging.getLogger("reopt_pysam_vn.webapp.jobs")

_SENTINEL = object()


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
                self.storage.set_status(run_id, state="error", message=str(exc))

    def _process(self, run_id: str, deal_config: Dict[str, Any], *, force_resolve: bool) -> None:
        deal = DealConfig.from_dict(deal_config)
        if deal.mode != "onsite":
            self.storage.set_status(
                run_id,
                state="error",
                message=(
                    "only onsite deals can be solved live via the NREL REopt API; "
                    "offsite_dppa/both need a pre-solved `extracted` upload."
                ),
            )
            return

        solve_hash = service.solve_relevant_hash(deal_config)
        cached_run_id = None if force_resolve else self.storage.find_cached_run_id(solve_hash)

        self.storage.set_status(run_id, state="solving", solve_hash=solve_hash)
        if cached_run_id is not None:
            reopt_results = self.storage.get_reopt_results(cached_run_id)
        else:
            reopt_results = service.solve_onsite_via_nrel(deal)
        self.storage.save_reopt_results(run_id, reopt_results)

        self.storage.set_status(run_id, state="analyzing")
        extracted = {"loads_kw": list(deal.load.get("loads_kw", []))}
        result = service.run_analysis(deal, results=reopt_results, extracted=extracted)
        self.storage.save_result(run_id, result)
        self.storage.set_status(run_id, state="done")
