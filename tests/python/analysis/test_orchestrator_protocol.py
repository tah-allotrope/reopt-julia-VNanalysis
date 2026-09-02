"""C2.3/C2.4: the offsite orchestrator seam is declared, not discovered.

The seam is real — three adapters sit at it (Samsung, Ninhsim case 1, and the
generic fallback). But its interface used to be undeclared: typed
``Callable[..., dict[str, Any]]`` and dispatched by narrowing a candidate kwarg
set with ``inspect.signature`` at call time, so every adapter had a different
call shape and mypy could say nothing about any of them.

These tests pin the declared interface: one context object in, one artifact out.
"""

from __future__ import annotations

import pytest
from reopt_pysam_vn.analysis import offsite_dppa as od
from reopt_pysam_vn.analysis.offsite_dppa import (
    OrchestratorContext,
    register_orchestrator,
    run_offsite_dppa,
)
from reopt_pysam_vn.analysis.types import DealConfig

_VALID_EXTRACTED = {"loads_kw": [1.0] * 8760}


def _deal(case: str = "PROTOCOL_TEST_CASE") -> DealConfig:
    return DealConfig.from_dict({"case": case, "mode": "offsite_dppa"})


def _minimal_artifact() -> dict:
    return {"case": "PROTOCOL_TEST_CASE", "quality": {"basis": "directional"}}


# ---------------------------------------------------------------------------
# The declared interface
# ---------------------------------------------------------------------------


def test_context_carries_every_input_an_orchestrator_may_need():
    """One object, so a new adapter learns one thing rather than four kwargs."""
    deal = _deal()
    ctx = OrchestratorContext(deal_config=deal)

    assert ctx.deal_config is deal
    assert ctx.results is None
    assert ctx.scenario is None
    assert ctx.run_developer is True


def test_protocol_orchestrator_is_called_with_the_context(monkeypatch):
    seen: dict = {}

    def orchestrator(extracted: dict, ctx: OrchestratorContext) -> dict:
        seen["extracted_keys"] = sorted(extracted)
        seen["case"] = ctx.deal_config.case
        seen["run_developer"] = ctx.run_developer
        seen["results"] = ctx.results
        seen["scenario"] = ctx.scenario
        return _minimal_artifact()

    monkeypatch.setitem(od._ORCHESTRATORS, "PROTOCOL_TEST_CASE", orchestrator)
    run_offsite_dppa(
        _deal(),
        extracted=_VALID_EXTRACTED,
        results={"r": 1},
        scenario={"s": 2},
        run_developer=False,
    )

    assert seen["extracted_keys"] == ["loads_kw"]
    assert seen["case"] == "PROTOCOL_TEST_CASE"
    assert seen["run_developer"] is False
    assert seen["results"] == {"r": 1}
    assert seen["scenario"] == {"s": 2}


def test_a_protocol_orchestrator_always_gets_every_field(monkeypatch):
    """No reflective narrowing: an adapter that ignores `scenario` still receives it."""

    def orchestrator(extracted: dict, ctx: OrchestratorContext) -> dict:
        assert hasattr(ctx, "scenario")
        assert hasattr(ctx, "results")
        return _minimal_artifact()

    monkeypatch.setitem(od._ORCHESTRATORS, "PROTOCOL_TEST_CASE", orchestrator)
    result = run_offsite_dppa(_deal(), extracted=_VALID_EXTRACTED)
    assert result.case == "PROTOCOL_TEST_CASE"


def test_registered_protocol_orchestrator_round_trips():
    def orchestrator(extracted: dict, ctx: OrchestratorContext) -> dict:
        return _minimal_artifact()

    register_orchestrator("C2_ROUND_TRIP", orchestrator)
    try:
        result = run_offsite_dppa(_deal(case="C2_ROUND_TRIP"), extracted=_VALID_EXTRACTED)
        assert result.quality["basis"] == "directional"
    finally:
        od._ORCHESTRATORS.pop("C2_ROUND_TRIP", None)


# ---------------------------------------------------------------------------
# The three shipped adapters all speak the declared interface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", ["DPPA_SAMSUNG_TTC", "DPPA_CASE_1_NINHSIM"])
def test_shipped_adapters_take_the_context(case):
    import inspect

    fn = od._ORCHESTRATORS[case]
    params = list(inspect.signature(fn).parameters)
    assert params[:2] == ["extracted", "ctx"], f"{case} adapter has not migrated: {params}"


def test_generic_fallback_adapter_takes_the_context():
    import inspect

    assert od._GENERIC_ORCHESTRATOR is not None
    params = list(inspect.signature(od._GENERIC_ORCHESTRATOR).parameters)
    assert params[:2] == ["extracted", "ctx"]


# ---------------------------------------------------------------------------
# Legacy keyword-style orchestrators still work, for callers outside the repo
# ---------------------------------------------------------------------------


def test_legacy_keyword_orchestrator_still_supported():
    """`combined_decision_fn` is public API; an old-shape callable must not break."""

    def legacy(extracted, *, run_developer=True):
        return {**_minimal_artifact(), "_seen_run_developer": run_developer}

    result = run_offsite_dppa(
        _deal(), extracted=_VALID_EXTRACTED, run_developer=False, combined_decision_fn=legacy
    )
    assert result.raw["_seen_run_developer"] is False


def test_legacy_orchestrator_only_receives_kwargs_it_declares():
    def legacy(extracted, *, results=None):
        return {**_minimal_artifact(), "_seen_results": results}

    result = run_offsite_dppa(
        _deal(),
        extracted=_VALID_EXTRACTED,
        results={"r": 1},
        scenario={"s": 2},
        combined_decision_fn=legacy,
    )
    assert result.raw["_seen_results"] == {"r": 1}
