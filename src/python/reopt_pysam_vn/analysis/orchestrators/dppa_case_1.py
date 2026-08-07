"""Ninhsim DPPA case-1 orchestrator for ``run_offsite_dppa`` (PHASE-04).

Composes the four ``integration.dppa_case_1`` builders (S3) and maps the raw
combined-decision artifact onto the ``OffsiteDppaResult`` block vocabulary (S4).

Case 1 consumes a REopt ``results`` dict plus the ``scenario`` dict the solve
was built from — the first registered deal that does not derive its generation
profile internally, which is exactly the shape the widened contract exists to
serve. The developer screen uses the PySAM-free placeholder path unless a
``developer_runner`` is injected, so this orchestrator is hermetic in CI
(ASM-008).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

DeveloperRunner = Callable[[dict[str, Any]], dict[str, Any]]

_DEVELOPER_RUNNER_MISSING_WARNING = (
    "no developer_runner was injected, so the PySAM developer screen ran in "
    "placeholder mode (project/equity IRR values are not real PySAM outputs)."
)


def _adapt_case_1_artifact(artifact: dict[str, Any], *, developer_basis: str) -> dict[str, Any]:
    """Map a raw ``build_dppa_case_1_combined_decision`` output onto the
    ``OffsiteDppaResult`` block vocabulary per S4.

    The three empty blocks (``strike_sweep``, ``adder_sensitivity``,
    ``regime_stress``) are deliberate: case 1 is a fixed private-wire strike
    with no sweep or lever. ``OffsiteDppaResult.to_dict()`` emits every block
    unconditionally, so ``{}`` is the honest representation. Nothing is lost —
    ``raw["case_1_artifact"]`` carries the complete original.
    """
    reopt_summary = artifact["reopt_summary"]
    return {
        "case": "DPPA_CASE_1_NINHSIM",
        "model": artifact["model"],
        "deal": artifact["site_and_tariff_basis"],
        "base_settlement": {
            "energy_summary": reopt_summary["energy_summary"],
            "optimal_mix": reopt_summary["optimal_mix"],
            "financial": reopt_summary["financial"],
        },
        "strike_sweep": {},
        "adder_sensitivity": {},
        "regime_stress": {},
        "decision": artifact["decision"],
        "quality": {
            "basis": "directional",
            "status": artifact["status"],
            "warnings": artifact["warnings"],
            "developer_basis": developer_basis,
        },
        "case_1_artifact": artifact,
    }


def build_case_1_offsite_artifact(
    extracted: dict[str, Any],
    *,
    run_developer: bool = True,
    results: dict[str, Any] | None = None,
    scenario: dict[str, Any] | None = None,
    developer_runner: DeveloperRunner | None = None,
) -> dict[str, Any]:
    """Compose the four ``dppa_case_1`` builders per S3 and adapt to the
    ``OffsiteDppaResult`` block vocabulary per S4.

    Raises ``ValueError`` naming the missing argument when ``results`` or
    ``scenario`` is ``None``.
    """
    if results is None:
        raise ValueError(
            "run_offsite_dppa for DPPA_CASE_1_NINHSIM needs `results` (the REopt "
            "solve's results block); pass results=... or set deal_config.raw['results']."
        )
    if scenario is None:
        raise ValueError(
            "run_offsite_dppa for DPPA_CASE_1_NINHSIM needs `scenario` (the REopt "
            "Scenario dict the solve was built from); pass scenario=... or set "
            "deal_config.raw['scenario']."
        )

    from reopt_pysam_vn.integration.dppa_case_1 import (
        build_dppa_case_1_combined_decision,
        build_dppa_case_1_comparison,
        build_dppa_case_1_placeholder_pysam_results,
        build_dppa_case_1_reopt_summary,
    )

    reopt_summary = build_dppa_case_1_reopt_summary(results, extracted, scenario)
    if run_developer and developer_runner is not None:
        pysam_results = developer_runner(reopt_summary)
        developer_basis = "pysam"
    else:
        pysam_results = build_dppa_case_1_placeholder_pysam_results(reopt_summary)
        developer_basis = "placeholder"
    comparison = build_dppa_case_1_comparison(reopt_summary, pysam_results)
    artifact = build_dppa_case_1_combined_decision(reopt_summary, pysam_results, comparison)
    if developer_basis == "placeholder" and run_developer:
        artifact["warnings"].append(_DEVELOPER_RUNNER_MISSING_WARNING)
    return _adapt_case_1_artifact(artifact, developer_basis=developer_basis)
