"""Maps a DealConfig + optional pre-solved inputs onto the analysis package.

CON-002: never forks analytics logic — always calls ``run_onsite`` /
``run_offsite_dppa`` / ``run_vietnam_reopt`` from ``reopt_pysam_vn`` as-is.

Repo constraint discovered during PHASE-01 research: ``run_offsite_dppa`` has
no generic fresh-solve path — it requires pre-solved ``extracted`` inputs and a
registered orchestrator keyed by ``deal_config.case`` (today only
``DPPA_SAMSUNG_TTC``). So offsite/both modes always need an ``extracted``
upload; only onsite can be solved live via the NREL REopt API.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from reopt_pysam_vn.analysis.types import DealConfig

__all__ = [
    "AnalysisError",
    "MissingInputsError",
    "OrchestratorNotRegisteredError",
    "load_nrel_api_key",
    "run_analysis",
    "solve_onsite_via_nrel",
    "solve_relevant_hash",
]


class AnalysisError(ValueError):
    """Base class for analysis-request errors surfaced as HTTP 422."""


class MissingInputsError(AnalysisError):
    pass


class OrchestratorNotRegisteredError(AnalysisError):
    pass


def run_analysis(
    deal_config: DealConfig,
    *,
    results: dict[str, Any] | None = None,
    extracted: dict[str, Any] | None = None,
    run_developer: bool = True,
) -> dict[str, Any]:
    """Run the pipeline(s) ``deal_config.mode`` selects and return a result dict.

    For ``mode == "both"`` the result is ``{"onsite": {...}, "offsite_dppa": {...}}``.
    Raises ``MissingInputsError`` / ``OrchestratorNotRegisteredError`` (both
    ``AnalysisError``) on bad input rather than a bare stack trace.
    """
    from reopt_pysam_vn.analysis.offsite_dppa import _ORCHESTRATORS, run_offsite_dppa
    from reopt_pysam_vn.analysis.onsite import run_onsite

    mode = deal_config.mode

    def _run_onsite() -> dict[str, Any]:
        if results is None:
            raise MissingInputsError(
                "onsite analysis needs pre-solved `results`; submit without `results` "
                "to trigger a background NREL solve instead."
            )
        return run_onsite(deal_config, results=results, extracted=extracted).to_dict()

    def _run_offsite() -> dict[str, Any]:
        if extracted is None:
            raise MissingInputsError(
                "offsite_dppa analysis needs pre-solved `extracted` inputs; there is "
                "no generic fresh-solve path for offsite/DPPA yet (only onsite can "
                "be solved live via the NREL REopt API)."
            )
        if deal_config.case not in _ORCHESTRATORS:
            raise OrchestratorNotRegisteredError(
                f"no offsite orchestrator registered for case {deal_config.case!r}; "
                f"registered cases: {sorted(_ORCHESTRATORS)}."
            )
        return run_offsite_dppa(deal_config, extracted=extracted, run_developer=run_developer).to_dict()

    if mode == "onsite":
        return _run_onsite()
    if mode == "offsite_dppa":
        return _run_offsite()
    if mode == "both":
        return {"onsite": _run_onsite(), "offsite_dppa": _run_offsite()}
    raise AnalysisError(f"unsupported mode {mode!r}")


def solve_relevant_hash(deal_config: dict[str, Any]) -> str:
    """Hash of the solve-relevant DealConfig subset, for the solve cache (DEC-005).

    Only ``site``/``plant``/``load`` affect the REopt solve; ``contract``/
    ``finance`` only affect post-processing, so they are excluded deliberately.
    """
    relevant = {
        "case": deal_config.get("case", ""),
        "site": deal_config.get("site", {}),
        "plant": deal_config.get("plant", {}),
        "load": deal_config.get("load", {}),
    }
    blob = json.dumps(relevant, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_nrel_api_key() -> str:
    """Load the NREL developer API key, mirroring
    ``scripts/python/reopt/solve_via_api.py:load_api_key``."""
    api_key = os.environ.get("NREL_DEVELOPER_API_KEY") or os.environ.get("NREL_API_KEY")
    if api_key:
        return api_key

    repo_root = Path(__file__).resolve().parents[4]
    env_path = repo_root / "NREL_API.env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == "API_KEY_NAME":
                return value.strip().strip('"')

    raise RuntimeError(
        "NREL API key not found. Set NREL_DEVELOPER_API_KEY env var or create "
        "NREL_API.env with API_KEY_NAME=<key>."
    )


def solve_onsite_via_nrel(deal_config: DealConfig) -> dict[str, Any]:
    """Build the REopt scenario from ``deal_config`` and solve it via the NREL
    REopt API (DEC-003). Kept import-light: ``reopt`` (network/requests) is
    only imported when a live solve is actually requested."""
    from reopt_pysam_vn.analysis.onsite import build_onsite_scenario
    from reopt_pysam_vn.reopt.preprocess import run_vietnam_reopt

    scenario = build_onsite_scenario(deal_config)
    api_key = load_nrel_api_key()
    return run_vietnam_reopt(scenario, api_key=api_key, apply_defaults=False)
