"""Maps a DealConfig + optional pre-solved inputs onto the analysis package.

CON-002: never forks analytics logic — always calls ``run_onsite`` /
``run_offsite_dppa`` / ``run_vietnam_reopt`` from ``reopt_pysam_vn`` as-is.

Offsite/both modes need either a pre-solved ``extracted`` payload or a
``deal_config.load["loads_kw"]`` 8760-hour series (from which ``extracted`` is
derived via ``analysis.extracted.build_extracted_inputs``). Only onsite can be
solved live via the NREL REopt API. Offsite deals that consume a REopt
``results`` dict (currently ``DPPA_CASE_1_NINHSIM``) must also supply the
``results`` and ``scenario`` payloads — those may ride on the deal config
(landing in ``DealConfig.raw`` and resolved by ``run_offsite_dppa``) or be
submitted in the payload and forwarded here (both ``results`` and ``scenario``
are now forwarded to ``run_offsite_dppa``).
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
    scenario: dict[str, Any] | None = None,
    extracted: dict[str, Any] | None = None,
    run_developer: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
    """Run the pipeline(s) ``deal_config.mode`` selects and return a result dict.

    For ``mode == "both"`` the result is ``{"onsite": {...}, "offsite_dppa": {...}}``.
    Returns ``(summary_result, ledger_rows_or_None)`` where the ledger is the
    8760-hour hourly ledger that was previously inlined in
    ``base_settlement["hourly_ledger"]``.  The returned summary no longer
    contains the ledger.

    Raises ``MissingInputsError`` / ``OrchestratorNotRegisteredError`` (both
    ``AnalysisError``) on bad input rather than a bare stack trace.
    """
    from reopt_pysam_vn.analysis.offsite_dppa import OrchestratorInputError, run_offsite_dppa
    from reopt_pysam_vn.analysis.onsite import run_onsite

    mode = deal_config.mode

    # Derive extracted once when a load series is present (PHASE-02).
    derived_extracted: dict[str, Any] | None = extracted
    if derived_extracted is None and isinstance(deal_config.load.get("loads_kw"), list):
        try:
            from reopt_pysam_vn.analysis.extracted import build_extracted_inputs

            derived_extracted = build_extracted_inputs(deal_config)
        except OrchestratorInputError as exc:
            raise MissingInputsError(str(exc)) from exc

    def _run_onsite() -> dict[str, Any]:
        if results is None:
            raise MissingInputsError(
                "onsite analysis needs pre-solved `results`; submit without `results` "
                "to trigger a background NREL solve instead."
            )
        return run_onsite(deal_config, results=results, extracted=derived_extracted).to_dict()

    def _run_offsite() -> dict[str, Any]:
        if derived_extracted is None:
            raise MissingInputsError(
                "offsite_dppa analysis needs pre-solved `extracted` inputs or a "
                "load series in `deal_config.load['loads_kw']` (8760 hourly kW values); "
                "neither was supplied."
            )
        try:
            return run_offsite_dppa(
                deal_config,
                extracted=derived_extracted,
                results=results,
                scenario=scenario,
                run_developer=run_developer,
            ).to_dict()
        except OrchestratorInputError as exc:
            raise MissingInputsError(str(exc)) from exc

    def _pop_ledger(result: dict[str, Any]) -> list[dict[str, Any]] | None:
        base = result.get("base_settlement")
        if isinstance(base, dict) and "hourly_ledger" in base:
            ledger = base.pop("hourly_ledger")
            return ledger if isinstance(ledger, list) else None
        return None

    if mode == "onsite":
        result = _run_onsite()
        ledger = _pop_ledger(result)
        return result, ledger
    if mode == "offsite_dppa":
        result = _run_offsite()
        ledger = _pop_ledger(result)
        return result, ledger
    if mode == "both":
        onsite = _run_onsite()
        offsite = _run_offsite()
        ledger = _pop_ledger(offsite)
        # Also pop from onsite if it ever carries one (currently not).
        _pop_ledger(onsite)
        return {"onsite": onsite, "offsite_dppa": offsite}, ledger
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
