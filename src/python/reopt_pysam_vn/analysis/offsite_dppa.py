"""Generalized offsite / DPPA analysis pipeline.

``run_offsite_dppa(deal_config)`` is the generalized front door for offsite/DPPA
analysis: it maps a ``DealConfig`` + ``extracted`` inputs through an *orchestrator*
into an ``OffsiteDppaResult`` (settlement + strike sweep + adder + regime stress +
decision), mirroring the combined-decision artifact the bespoke case modules emit.

The orchestrator is resolved in this order:
1. an explicitly injected ``combined_decision_fn`` (used by tests and callers that
   want full control);
2. the ``_ORCHESTRATORS`` registry, keyed by ``deal_config.case`` — today this
   holds two builders: the proven Samsung-TTC builder
   (``build_samsung_ttc_combined_decision``, which internally composes the tested
   case-2 settlement engine + PySAM developer screen) and the Ninhsim DPPA case-1
   builder (``analysis.orchestrators.dppa_case_1``, which consumes a REopt
   ``results`` dict + the ``scenario`` it was solved from).

Orchestrator contract (S1): ``(extracted, *, run_developer=True, results=None,
scenario=None) -> dict``. ``results`` is the ``results`` block of a REopt solve
output; ``scenario`` is the ``Scenario`` input dict the solve was built from.
Orchestrators that derive generation internally (Samsung) take neither. For
backward compatibility, ``run_offsite_dppa`` only forwards ``results`` and
``scenario`` when they are not ``None``, so existing two-parameter orchestrators
keep their exact call shape.

Input resolution order (S2): for each of ``extracted``, ``results``, and
``scenario``, the first non-``None`` of (a) the explicit keyword argument, (b)
``deal_config.raw[<name>]``, (c) ``None`` wins. ``extracted`` resolving to
``None`` is a hard error; ``results``/``scenario`` resolving to ``None`` is
legal (the Samsung case).

New deals register their orchestrator here (or inject one).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from reopt_pysam_vn.analysis.types import DealConfig, OffsiteDppaResult

__all__ = ["register_orchestrator", "run_offsite_dppa"]

# orchestrator signature:
#   (extracted: dict, *, run_developer: bool = True,
#    results: dict | None = None, scenario: dict | None = None) -> dict
CombinedDecisionFn = Callable[..., dict[str, Any]]


def _samsung_ttc_orchestrator(extracted: dict[str, Any], *, run_developer: bool = True) -> dict[str, Any]:
    # Lazy import: keep `analysis` importable without pulling the heavy case module
    # (and PySAM) until an offsite run actually needs it.
    from reopt_pysam_vn.integration.dppa_samsung_ttc import build_samsung_ttc_combined_decision

    return build_samsung_ttc_combined_decision(extracted, run_developer=run_developer)


_ORCHESTRATORS: dict[str, CombinedDecisionFn] = {
    "DPPA_SAMSUNG_TTC": _samsung_ttc_orchestrator,
}


def register_orchestrator(case: str, fn: CombinedDecisionFn) -> None:
    """Register an offsite orchestrator for a deal ``case`` id."""
    _ORCHESTRATORS[case] = fn


def _resolve_input(
    deal_config: DealConfig, name: str, explicit: dict[str, Any] | None
) -> dict[str, Any] | None:
    """S2 resolution: explicit keyword arg, then ``deal_config.raw[name]``."""
    if explicit is not None:
        return explicit
    value = deal_config.raw.get(name)
    return value if isinstance(value, dict) else None


def run_offsite_dppa(
    deal_config: DealConfig,
    *,
    extracted: dict[str, Any] | None = None,
    results: dict[str, Any] | None = None,
    scenario: dict[str, Any] | None = None,
    combined_decision_fn: CombinedDecisionFn | None = None,
    run_developer: bool = True,
) -> OffsiteDppaResult:
    """Run offsite/DPPA analysis for ``deal_config``.

    Parameters
    ----------
    extracted:
        The ``*_extracted_inputs`` dict the settlement engine consumes. May instead
        be carried on ``deal_config.raw['extracted']``.
    results:
        A REopt ``results`` dict (the ``results`` block of a REopt solve output).
        Consumed by orchestrators that do not derive generation internally (e.g.
        ``DPPA_CASE_1_NINHSIM``); ``None`` for orchestrators that do (Samsung).
        May instead be carried on ``deal_config.raw['results']``.
    scenario:
        The REopt ``Scenario`` input dict the solve was built from, containing at
        minimum ``Site`` and ``_meta``. ``None`` for orchestrators that do not
        need it. May instead be carried on ``deal_config.raw['scenario']``.
    combined_decision_fn:
        Explicit orchestrator override. If omitted, resolved from the registry by
        ``deal_config.case``.
    run_developer:
        Whether to run the PySAM developer screen (skipped cleanly when PySAM is
        absent inside the orchestrator).
    """
    extracted = _resolve_input(deal_config, "extracted", extracted)
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

    results = _resolve_input(deal_config, "results", results)
    scenario = _resolve_input(deal_config, "scenario", scenario)

    kwargs: dict[str, Any] = {"run_developer": run_developer}
    if results is not None:
        kwargs["results"] = results
    if scenario is not None:
        kwargs["scenario"] = scenario

    raw = fn(extracted, **kwargs)
    return OffsiteDppaResult.from_dict(raw)
