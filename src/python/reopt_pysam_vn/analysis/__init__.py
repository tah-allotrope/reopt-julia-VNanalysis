"""Generalized onsite + offsite/DPPA analysis pipelines for Vietnam projects.

This package is the first-class home for the repo's key function: take a project
``DealConfig`` and run the full chain — onsite (behind-the-meter REopt PV+BESS
optimization) and/or offsite/DPPA (PySAM developer finance + settlement + strike
search) — replacing the bespoke per-deal modules under ``integration/``.

**Public API boundary (strategic-lens PHASE-02, DEC-106):**
``reopt_pysam_vn.analysis`` (this package: ``DealConfig``, ``run_onsite``,
``run_offsite_dppa``, ``register_orchestrator``) is the supported, type-checked
surface for callers outside this repo (the web app, external scripts). It ships
with a ``py.typed`` marker and is covered by a ``mypy`` gate. ``integration``,
``reopt``, and ``pysam`` are internal engines this package composes — they may
change shape between commits without a deprecation cycle. Code outside
``reopt_pysam_vn`` should depend on ``analysis``, not on those internals.

Public surface (built across Sprint 3 phases):
- ``types``        — shared contract: ``DealConfig``, ``OnsiteResult``,
                     ``OffsiteDppaResult``, ``CombinedDecision`` (PHASE-01).
- ``onsite``       — ``run_onsite(deal_config)`` (PHASE-02).
- ``offsite_dppa`` — ``run_offsite_dppa(deal_config)`` (PHASE-03).
- ``__main__``     — ``python -m reopt_pysam_vn.analysis {onsite,offsite_dppa}`` CLI.
"""

from reopt_pysam_vn.analysis.offsite_dppa import (
    OrchestratorInputError,
    register_orchestrator,
    run_offsite_dppa,
    set_generic_orchestrator,
)
from reopt_pysam_vn.analysis.onsite import run_onsite
from reopt_pysam_vn.analysis.types import (
    CombinedDecision,
    DealConfig,
    OffsiteDppaResult,
    OnsiteResult,
)
from reopt_pysam_vn.analysis.validation import DealConfigValidationError


def _register_offsite_orchestrators() -> None:
    # Lazy import: keep `analysis` importable without pulling the heavy
    # integration.dppa_case_1 module (and PySAM) at import time. Mirrors the
    # lazy-import comment on _samsung_ttc_orchestrator.
    from reopt_pysam_vn.analysis.orchestrators.dppa_case_1 import build_case_1_offsite_artifact
    from reopt_pysam_vn.analysis.orchestrators.generic_vn_dppa import build_generic_offsite_artifact

    register_orchestrator("DPPA_CASE_1_NINHSIM", build_case_1_offsite_artifact)
    # Generic fallback: any unregistered `case` routes here (DEC-004/PHASE-05).
    set_generic_orchestrator(build_generic_offsite_artifact)


_register_offsite_orchestrators()

__all__ = [
    # contract
    "CombinedDecision",
    "DealConfig",
    "DealConfigValidationError",
    "OffsiteDppaResult",
    "OnsiteResult",
    "OrchestratorInputError",
    # pipelines (first-class entry points)
    "register_orchestrator",
    "run_offsite_dppa",
    "run_onsite",
]
