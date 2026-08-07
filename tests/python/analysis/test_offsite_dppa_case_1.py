"""PHASE-04 (2026-08-06 plan): DPPA case 1 registered as a second offsite deal.

``run_offsite_dppa`` gains a second registered orchestrator so the public
analysis API serves more than one deal. Case 1 consumes a REopt ``results``
dict plus the ``scenario`` it was solved from — the first non-Samsung shape the
orchestrator contract must accommodate (S1/S2).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))


def _load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load module spec for {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_BUILD_EXTRACTED = _load_module(
    "build_ninhsim_extracted_inputs_case1_orch_module",
    "scripts/python/integration/build_ninhsim_extracted_inputs.py",
)

from reopt_pysam_vn.analysis.offsite_dppa import register_orchestrator, run_offsite_dppa
from reopt_pysam_vn.analysis.types import DealConfig, OffsiteDppaResult

build_extracted_inputs = _BUILD_EXTRACTED.build_extracted_inputs

NINHSIM_SCENARIO = REPO_ROOT / "scenarios" / "case_studies" / "ninhsim" / "2026-04-09_ninhsim_dppa-case-1.json"
_OFFSITE_BLOCKS = (
    "deal",
    "base_settlement",
    "strike_sweep",
    "adder_sensitivity",
    "regime_stress",
    "decision",
    "quality",
)


def _ninhsim_extracted() -> dict:
    return build_extracted_inputs()


def _ninhsim_scenario() -> dict:
    return json.loads(NINHSIM_SCENARIO.read_text(encoding="utf-8-sig"))


def _case_1_config() -> dict:
    return {
        "case": "DPPA_CASE_1_NINHSIM",
        "mode": "offsite_dppa",
        "title": "Ninhsim DPPA Case 1 - private-wire solar plus 2h BESS",
        "site": {"region": "central"},
    }


def _synthetic_results() -> dict:
    return {
        "status": "optimal",
        "PV": {
            "size_kw": 20_000.0,
            "year_one_energy_produced_kwh": 43_800_000.0,
            "electric_to_load_series_kw": [4_500.0] * 8760,
            "electric_to_grid_series_kw": [20.0] * 8760,
            "electric_to_storage_series_kw": [300.0] * 8760,
            "electric_curtailed_series_kw": [50.0] * 8760,
        },
        "Wind": {
            "size_kw": 0.0,
            "year_one_energy_produced_kwh": 0.0,
            "electric_to_load_series_kw": [0.0] * 8760,
            "electric_to_grid_series_kw": [0.0] * 8760,
        },
        "ElectricStorage": {
            "size_kw": 2_500.0,
            "size_kwh": 5_000.0,
            "initial_capital_cost": 1_250_000.0,
            "storage_to_load_series_kw": [260.0] * 8760,
        },
        "ElectricUtility": {
            "electric_to_load_series_kw": [6_000.0] * 8760,
        },
        "Financial": {
            "npv": 4_200_000.0,
            "analysis_years": 20,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
        },
    }


# ---------------------------------------------------------------------------
# Happy path (after registration) and the S4 block mapping.
# ---------------------------------------------------------------------------


def test_case_1_happy_path_returns_typed_result():
    result = run_offsite_dppa(
        DealConfig.from_dict(_case_1_config()),
        extracted=_ninhsim_extracted(),
        results=_synthetic_results(),
        scenario=_ninhsim_scenario(),
    )
    assert isinstance(result, OffsiteDppaResult)
    assert result.case == "DPPA_CASE_1_NINHSIM"


def test_case_1_result_has_all_seven_blocks():
    result = run_offsite_dppa(
        DealConfig.from_dict(_case_1_config()),
        extracted=_ninhsim_extracted(),
        results=_synthetic_results(),
        scenario=_ninhsim_scenario(),
    )
    emitted = result.to_dict()
    for block in _OFFSITE_BLOCKS:
        assert block in emitted, f"missing block {block}"


def test_case_1_empty_by_design_blocks_are_empty_dicts():
    result = run_offsite_dppa(
        DealConfig.from_dict(_case_1_config()),
        extracted=_ninhsim_extracted(),
        results=_synthetic_results(),
        scenario=_ninhsim_scenario(),
    )
    assert result.strike_sweep == {}
    assert result.adder_sensitivity == {}
    assert result.regime_stress == {}


def test_case_1_populated_blocks():
    result = run_offsite_dppa(
        DealConfig.from_dict(_case_1_config()),
        extracted=_ninhsim_extracted(),
        results=_synthetic_results(),
        scenario=_ninhsim_scenario(),
    )
    assert result.decision["recommended_position"] in ("advance_for_review", "needs_reprice_or_resize")
    assert result.deal, "deal block must be non-empty"
    for key in ("energy_summary", "optimal_mix", "financial"):
        assert key in result.base_settlement


def test_case_1_raw_preserves_complete_original_artifact():
    result = run_offsite_dppa(
        DealConfig.from_dict(_case_1_config()),
        extracted=_ninhsim_extracted(),
        results=_synthetic_results(),
        scenario=_ninhsim_scenario(),
    )
    artifact = result.raw["case_1_artifact"]
    assert artifact["model"] == "Ninhsim DPPA Case 1 Combined Decision"
    assert set(artifact) == {
        "model",
        "status",
        "site_and_tariff_basis",
        "reopt_summary",
        "pysam_summary",
        "comparison",
        "decision",
        "warnings",
    }


def test_case_1_developer_basis_placeholder_without_runner():
    result = run_offsite_dppa(
        DealConfig.from_dict(_case_1_config()),
        extracted=_ninhsim_extracted(),
        results=_synthetic_results(),
        scenario=_ninhsim_scenario(),
    )
    assert result.quality["developer_basis"] == "placeholder"


def test_case_1_run_developer_false_still_returns_complete_artifact():
    result = run_offsite_dppa(
        DealConfig.from_dict(_case_1_config()),
        extracted=_ninhsim_extracted(),
        results=_synthetic_results(),
        scenario=_ninhsim_scenario(),
        run_developer=False,
    )
    assert result.quality["developer_basis"] == "placeholder"
    assert result.decision["recommended_position"] in ("advance_for_review", "needs_reprice_or_resize")


def test_case_1_missing_results_raises_naming_results():
    with pytest.raises(ValueError, match="results"):
        run_offsite_dppa(
            DealConfig.from_dict(_case_1_config()),
            extracted=_ninhsim_extracted(),
        )


def test_case_1_raw_fallback_resolves_all_three_inputs():
    deal = DealConfig.from_dict(
        {
            **_case_1_config(),
            "extracted": _ninhsim_extracted(),
            "results": _synthetic_results(),
            "scenario": _ninhsim_scenario(),
        }
    )
    result = run_offsite_dppa(deal)
    assert result.case == "DPPA_CASE_1_NINHSIM"
    assert result.quality["developer_basis"] == "placeholder"


# ---------------------------------------------------------------------------
# Contract widening: a two-parameter orchestrator must remain call-compatible.
# ---------------------------------------------------------------------------


def test_two_parameter_orchestrator_keeps_its_call_shape(monkeypatch):
    calls: list[tuple] = []

    def _two_param(extracted, *, run_developer=True):
        calls.append((extracted, run_developer))
        return {
            "case": "TWO_PARAM_STUB",
            "model": "stub",
            "deal": {},
            "base_settlement": {},
            "strike_sweep": {},
            "adder_sensitivity": {},
            "regime_stress": {},
            "decision": {},
            "quality": {},
        }

    register_orchestrator("TWO_PARAM_STUB", _two_param)
    result = run_offsite_dppa(
        DealConfig.from_dict({"case": "TWO_PARAM_STUB", "mode": "offsite_dppa"}),
        extracted={"loads_kw": [1.0]},
    )
    assert result.case == "TWO_PARAM_STUB"
    assert len(calls) == 1
    assert calls[0][0] == {"loads_kw": [1.0]}
    assert calls[0][1] is True  # run_developer forwarded positionally by keyword only
