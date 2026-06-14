"""Generalized offsite / DPPA analysis pipeline.

``run_offsite_dppa(deal_config)`` is the generalized front door for offsite/DPPA
analysis: it maps a ``DealConfig`` + ``extracted`` inputs through an *orchestrator*
into an ``OffsiteDppaResult`` (settlement + strike sweep + adder + regime stress +
decision), mirroring the combined-decision artifact the bespoke case modules emit.

The orchestrator is resolved in this order:
1. an explicitly injected ``combined_decision_fn`` (used by tests and callers that
   want full control);
2. the ``_ORCHESTRATORS`` registry, keyed by ``deal_config.case`` — today this holds
   the proven Samsung-TTC builder (``build_samsung_ttc_combined_decision``), which
   internally composes the tested case-2 settlement engine + PySAM developer screen.

A from-scratch generic orchestrator for a brand-new deal needs a REopt/PySAM solve
to produce the generation ``results`` the settlement engine consumes; that
solver-dependent path is a documented follow-up rather than a faked generic engine.
New deals register their orchestrator here (or inject one).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from reopt_pysam_vn.analysis.types import DealConfig, OffsiteDppaResult

__all__ = ["run_offsite_dppa", "register_orchestrator"]

# orchestrator signature: (extracted: dict, *, run_developer: bool) -> dict
CombinedDecisionFn = Callable[..., Dict[str, Any]]


def _samsung_ttc_orchestrator(extracted: Dict[str, Any], *, run_developer: bool = True) -> Dict[str, Any]:
    # Lazy import: keep `analysis` importable without pulling the heavy case module
    # (and PySAM) until an offsite run actually needs it.
    from reopt_pysam_vn.integration.dppa_samsung_ttc import build_samsung_ttc_combined_decision

    return build_samsung_ttc_combined_decision(extracted, run_developer=run_developer)


_ORCHESTRATORS: Dict[str, CombinedDecisionFn] = {
    "DPPA_SAMSUNG_TTC": _samsung_ttc_orchestrator,
}


def register_orchestrator(case: str, fn: CombinedDecisionFn) -> None:
    """Register an offsite orchestrator for a deal ``case`` id."""
    _ORCHESTRATORS[case] = fn


def run_offsite_dppa(
    deal_config: DealConfig,
    *,
    extracted: Optional[Dict[str, Any]] = None,
    combined_decision_fn: Optional[CombinedDecisionFn] = None,
    run_developer: bool = True,
) -> OffsiteDppaResult:
    """Run offsite/DPPA analysis for ``deal_config``.

    Parameters
    ----------
    extracted:
        The ``*_extracted_inputs`` dict the settlement engine consumes. May instead
        be carried on ``deal_config.raw['extracted']``.
    combined_decision_fn:
        Explicit orchestrator override. If omitted, resolved from the registry by
        ``deal_config.case``.
    run_developer:
        Whether to run the PySAM developer screen (skipped cleanly when PySAM is
        absent inside the orchestrator).
    """
    if extracted is None:
        extracted = deal_config.raw.get("extracted")
    if extracted is None:
        raise ValueError(
            "run_offsite_dppa needs `extracted` inputs (the *_extracted_inputs dict); "
            "pass extracted=... or set deal_config.raw['extracted']."
        )

    fn = combined_decision_fn or _ORCHESTRATORS.get(deal_config.case)
    if fn is None:
        raise ValueError(
            f"no offsite orchestrator registered for case {deal_config.case!r}; "
            "pass combined_decision_fn=... or register one via "
            "reopt_pysam_vn.analysis.offsite_dppa.register_orchestrator(case, fn)."
        )

    raw = fn(extracted, run_developer=run_developer)
    return OffsiteDppaResult.from_dict(raw)
