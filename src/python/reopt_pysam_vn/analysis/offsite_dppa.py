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

Orchestrator contract (C2): ``(extracted: dict, ctx: OrchestratorContext) -> dict``.
The context carries everything an orchestrator may need — the driving
``DealConfig``, the REopt ``results`` block, the ``Scenario`` input dict it was
solved from, and the ``run_developer`` flag — so every adapter has the same call
shape and a new one has a single thing to learn. Adapters that do not need a
field simply ignore it.

Legacy keyword-style orchestrators — ``(extracted, *, run_developer=..., results=...,
scenario=..., deal_config=...)`` — remain supported because ``combined_decision_fn``
is public API. They are detected by signature and called with the narrowed keyword
set they declare. All three shipped adapters speak the declared contract; the
legacy path exists only for callers outside this repo and is deprecated.

Input resolution order (S2): for each of ``extracted``, ``results``, and
``scenario``, the first non-``None`` of (a) the explicit keyword argument, (b)
``deal_config.raw[<name>]``, (c) ``None`` wins. ``extracted`` resolving to
``None`` is a hard error; ``results``/``scenario`` resolving to ``None`` is
legal (the Samsung case).

New deals register their orchestrator here (or inject one).
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from reopt_pysam_vn.analysis.types import DealConfig, OffsiteDppaResult
from reopt_pysam_vn.analysis.validation import ExtractedInputsValidationError, validate_extracted_inputs

__all__ = [
    "OffsiteOrchestrator",
    "OrchestratorContext",
    "OrchestratorInputError",
    "register_orchestrator",
    "run_offsite_dppa",
]


@dataclass(frozen=True)
class OrchestratorContext:
    """Everything an offsite orchestrator may need, in one object.

    Passing a context rather than a narrowed keyword set means every adapter has
    the same call shape: one parameter to learn, and no reflective inspection at
    call time to decide what an adapter is allowed to see.
    """

    deal_config: DealConfig
    results: dict[str, Any] | None = None
    scenario: dict[str, Any] | None = None
    run_developer: bool = True


@runtime_checkable
class OffsiteOrchestrator(Protocol):
    """The declared interface at the orchestrator seam."""

    def __call__(self, extracted: dict[str, Any], ctx: OrchestratorContext) -> dict[str, Any]:
        ...


#: Registry values are either an :class:`OffsiteOrchestrator` or a deprecated
#: keyword-style callable. ``Callable[..., dict]`` remains the stored type only
#: because the legacy shape must keep working for callers outside this repo.
CombinedDecisionFn = Callable[..., dict[str, Any]]


class OrchestratorInputError(ValueError):
    """Raised when an orchestrator's required inputs are missing.

    A ``ValueError`` subclass so existing callers that catch ``ValueError`` keep
    working, but typed so the web layer can map it to HTTP 422 without
    broadening an ``except`` clause to bare ``ValueError``.
    """


def _samsung_ttc_orchestrator(
    extracted: dict[str, Any], ctx: OrchestratorContext
) -> dict[str, Any]:
    # Lazy import: keep `analysis` importable without pulling the heavy case module
    # (and PySAM) until an offsite run actually needs it.
    from reopt_pysam_vn.integration.dppa_samsung_ttc import build_samsung_ttc_combined_decision

    return build_samsung_ttc_combined_decision(extracted, run_developer=ctx.run_developer)


_ORCHESTRATORS: dict[str, CombinedDecisionFn] = {
    "DPPA_SAMSUNG_TTC": _samsung_ttc_orchestrator,
}

# Registry fallback: any unregistered ``case`` routes here (PHASE-05). None
# disables the fallback and restores the "no orchestrator" error path.
_GENERIC_ORCHESTRATOR: CombinedDecisionFn | None = None


def register_orchestrator(case: str, fn: CombinedDecisionFn) -> None:
    """Register an offsite orchestrator for a deal ``case`` id."""
    _ORCHESTRATORS[case] = fn


def set_generic_orchestrator(fn: CombinedDecisionFn | None) -> None:
    """Install (or, with ``None``, remove) the registry fallback orchestrator."""
    global _GENERIC_ORCHESTRATOR
    _GENERIC_ORCHESTRATOR = fn


def _takes_context(fn: CombinedDecisionFn) -> bool:
    """True when ``fn`` speaks the declared ``(extracted, ctx)`` contract."""
    try:
        parameters = list(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        return False
    return parameters[:2] == ["extracted", "ctx"]


def _supported_kwargs(fn: CombinedDecisionFn, candidates: dict[str, Any]) -> dict[str, Any]:
    """Return the subset of ``candidates`` whose keys ``fn`` accepts as keywords.

    A callable declaring ``**kwargs`` receives all candidates unchanged. Any
    failure to introspect ``fn`` (e.g. a ``functools.partial`` or a C callable)
    falls back to passing the full candidate set, preserving prior behaviour.
    """
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return dict(candidates)
    parameters = signature.parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        return dict(candidates)
    return {key: value for key, value in candidates.items() if key in parameters}


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
        raise OrchestratorInputError(
            "run_offsite_dppa needs `extracted` inputs (the *_extracted_inputs dict); "
            "pass extracted=... or set deal_config.raw['extracted']."
        )

    try:
        validate_extracted_inputs(extracted)
    except ExtractedInputsValidationError as exc:
        raise OrchestratorInputError(
            "offsite `extracted` inputs failed validation: " + str(exc)
        ) from exc

    fn = combined_decision_fn or _ORCHESTRATORS.get(deal_config.case) or _GENERIC_ORCHESTRATOR
    if fn is None:
        raise ValueError(
            f"no offsite orchestrator registered for case {deal_config.case!r}; "
            "pass combined_decision_fn=... or register one via "
            "reopt_pysam_vn.analysis.offsite_dppa.register_orchestrator(case, fn)."
        )

    results = _resolve_input(deal_config, "results", results)
    scenario = _resolve_input(deal_config, "scenario", scenario)

    if _takes_context(fn):
        ctx = OrchestratorContext(
            deal_config=deal_config,
            results=results,
            scenario=scenario,
            run_developer=run_developer,
        )
        raw = fn(extracted, ctx)
    else:
        # Deprecated keyword-style adapter (external `combined_decision_fn`).
        candidates: dict[str, Any] = {
            "run_developer": run_developer,
            "results": results,
            "scenario": scenario,
            "deal_config": deal_config,
        }
        if results is None:
            candidates.pop("results")
        if scenario is None:
            candidates.pop("scenario")
        raw = fn(extracted, **_supported_kwargs(fn, candidates))
    return OffsiteDppaResult.from_dict(raw)
