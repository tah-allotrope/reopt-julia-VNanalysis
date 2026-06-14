"""Generalized onsite + offsite/DPPA analysis pipelines for Vietnam projects.

This package is the first-class home for the repo's key function: take a project
``DealConfig`` and run the full chain — onsite (behind-the-meter REopt PV+BESS
optimization) and/or offsite/DPPA (PySAM developer finance + settlement + strike
search) — replacing the bespoke per-deal modules under ``integration/``.

Public surface (built across Sprint 3 phases):
- ``types``        — shared contract: ``DealConfig``, ``OnsiteResult``,
                     ``OffsiteDppaResult``, ``CombinedDecision`` (PHASE-01).
- ``onsite``       — ``run_onsite(deal_config)`` (PHASE-02).
- ``offsite_dppa`` — ``run_offsite_dppa(deal_config)`` (PHASE-03).
- ``__main__``     — ``python -m reopt_pysam_vn.analysis {onsite,offsite_dppa}`` CLI.
"""

from reopt_pysam_vn.analysis.offsite_dppa import register_orchestrator, run_offsite_dppa
from reopt_pysam_vn.analysis.onsite import run_onsite
from reopt_pysam_vn.analysis.types import (
    CombinedDecision,
    DealConfig,
    OffsiteDppaResult,
    OnsiteResult,
)

__all__ = [
    # contract
    "DealConfig",
    "OnsiteResult",
    "OffsiteDppaResult",
    "CombinedDecision",
    # pipelines (first-class entry points)
    "run_onsite",
    "run_offsite_dppa",
    "register_orchestrator",
]
