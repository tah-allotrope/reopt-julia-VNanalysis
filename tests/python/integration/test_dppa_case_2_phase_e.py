"""Regression tests for Ninhsim DPPA Case 2 Phase E sensitivity surfaces."""

from __future__ import annotations

import importlib.util
import math
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))


def _load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load module spec for {relative_path}")
    spec_checked: ModuleSpec = spec
    module = importlib.util.module_from_spec(spec_checked)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUILD_NINHSIM_REOPT_INPUT = _load_module(
    "build_ninhsim_reopt_input_dppa_case_2_phase_e_module",
    "scripts/python/integration/build_ninhsim_reopt_input.py",
)

from reopt_pysam_vn.integration.bridge import (
    build_dppa_case_2_single_owner_inputs,
)
from reopt_pysam_vn.integration.dppa_case_2 import (
    build_dppa_case_2_contract_risk_sensitivity,
    build_dppa_case_2_physical_summary,
    build_dppa_case_2_settlement_inputs,
    build_dppa_case_2_strike_sensitivity,
)

build_scenario_dppa_case_2 = BUILD_NINHSIM_REOPT_INPUT.build_scenario_dppa_case_2


def _synthetic_extracted() -> dict:
    load_series = [100.0, 100.0, 100.0]
    retail_series = [100.0, 100.0, 100.0]
    return {
        "data_year": 2024,
        "site": {
            "latitude": 12.5,
            "longitude": 109.0,
            "customer_type": "industrial",
            "voltage_level": "medium_voltage_22kv_to_110kv",
            "region": "south",
        },
        "loads_kw": load_series,
        "benchmark": {
            "annual_load_kwh": sum(load_series),
            "annual_load_gwh": sum(load_series) / 1_000_000.0,
            "weighted_evn_price_vnd_per_kwh": 100.0,
            "weighted_evn_price_usd_per_kwh": 0.004,
            "wholesale_rate_vnd_per_kwh": 33.0,
            "wholesale_rate_usd_per_kwh": 0.00132,
            "exchange_rate_vnd_per_usd": 25_000.0,
        },
        "evn_tariff": {
            "tou_energy_rates_vnd_per_kwh": retail_series,
            "tou_energy_rates_usd_per_kwh": [
                value / 25_000.0 for value in retail_series
            ],
        },
        "wind_production_factor_series": [0.0, 0.0, 0.0],
        "source_load_path": "synthetic_load.json",
        "source_tariff_path": "synthetic_tariff.json",
    }


def _synthetic_results() -> dict:
    return {
        "status": "optimal",
        "PV": {
            "size_kw": 1_500.0,
            "annual_energy_produced_kwh": 330.0,
            "electric_to_load_series_kw": [50.0, 70.0, 40.0],
            "electric_to_grid_series_kw": [30.0, 50.0, 0.0],
            "electric_to_storage_series_kw": [5.0, 0.0, 0.0],
            "electric_curtailed_series_kw": [0.0, 10.0, 0.0],
        },
        "Wind": {
            "size_kw": 0.0,
            "annual_energy_produced_kwh": 0.0,
            "electric_to_load_series_kw": [0.0, 0.0, 0.0],
            "electric_to_grid_series_kw": [0.0, 0.0, 0.0],
        },
        "ElectricStorage": {
            "size_kw": 250.0,
            "size_kwh": 500.0,
            "initial_capital_cost": 90_000.0,
            "storage_to_load_series_kw": [30.0, 30.0, 0.0],
        },
        "ElectricUtility": {
            "electric_to_load_series_kw": [20.0, 0.0, 60.0],
        },
        "Financial": {
            "npv": 750_000.0,
            "analysis_years": 20,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "owner_tax_rate_fraction": 0.0575,
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.04,
            "initial_capital_costs": 1_200_000.0,
        },
    }


def _phase_e_base_inputs() -> tuple[dict, dict, dict, dict, dict]:
    extracted = _synthetic_extracted()
    results = _synthetic_results()
    scenario = build_scenario_dppa_case_2(extracted)
    physical = build_dppa_case_2_physical_summary(results, extracted, scenario)
    settlement_inputs = build_dppa_case_2_settlement_inputs(
        results, extracted, scenario
    )
    return extracted, results, scenario, physical, settlement_inputs


def test_build_dppa_case_2_single_owner_inputs_maps_case2_strike_and_generation():
    extracted, results, scenario, _physical, settlement_inputs = _phase_e_base_inputs()

    inputs = build_dppa_case_2_single_owner_inputs(results, scenario, settlement_inputs)

    assert inputs.system_capacity_kw == 1500.0
    assert len(inputs.generation_profile_kw) == 8760
    assert math.isclose(sum(inputs.generation_profile_kw), 240.0, abs_tol=1e-9)
    assert math.isclose(inputs.annual_generation_kwh, 240.0, abs_tol=1e-9)
    assert math.isclose(
        inputs.ppa_price_input_usd_per_kwh,
        settlement_inputs["strike_price_vnd_per_kwh"]
        / settlement_inputs["exchange_rate_vnd_per_usd"],
        abs_tol=1e-12,
    )
    assert inputs.metadata["source_case"] == "ninhsim_dppa_case_2"
    assert math.isclose(
        inputs.metadata["weighted_evn_price_vnd_per_kwh"],
        extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"],
        abs_tol=1e-9,
    )


def test_build_dppa_case_2_strike_sensitivity_reports_buyer_only_candidates_when_no_overlap():
    _extracted, results, scenario, physical, settlement_inputs = _phase_e_base_inputs()
    settlement_inputs["dppa_adder_vnd_per_kwh"] = 0.0
    settlement_inputs["kpp_factor"] = 0.8
    developer_inputs = build_dppa_case_2_single_owner_inputs(
        results,
        scenario,
        settlement_inputs,
    )

    def fake_runner(inputs):
        irr = 0.16 if inputs.ppa_price_input_usd_per_kwh >= 0.0042 else 0.08
        return {
            "model": "PySAM Single Owner",
            "status": "ok",
            "inputs": {
                "ppa_price_input_usd_per_kwh": inputs.ppa_price_input_usd_per_kwh,
                "target_irr_fraction": inputs.target_irr_fraction,
            },
            "case": dict(inputs.metadata),
            "outputs": {
                "project_return_aftertax_irr_fraction": irr,
                "project_return_aftertax_npv_usd": irr * 1000.0,
                "min_dscr": irr,
            },
            "annual_cashflows": [],
        }

    artifact = build_dppa_case_2_strike_sensitivity(
        settlement_inputs,
        physical,
        strike_discount_fractions=(0.50, 0.10, 0.05),
        developer_base_inputs=developer_inputs,
        developer_runner=fake_runner,
    )

    assert artifact["status"] == "ok"
    assert [
        entry["strike_price_vnd_per_kwh"] for entry in artifact["strike_sweep_results"]
    ] == [50.0, 90.0, 95.0]
    assert artifact["developer_screen"]["target_irr_fraction"] == 0.15
    assert artifact["negotiation_summary"]["overlap_found"] is False
    assert len(artifact["negotiation_summary"]["buyer_only_candidates"]) == 3
    assert (
        artifact["negotiation_summary"]["buyer_only_candidates"][0][
            "strike_price_vnd_per_kwh"
        ]
        == 50.0
    )
    assert artifact["negotiation_summary"]["developer_only_candidates"] == []
    assert (
        artifact["negotiation_summary"]["recommended_position"]
        == "buyer_only_no_overlap"
    )


def test_build_dppa_case_2_contract_risk_sensitivity_shows_adder_kpp_and_excess_exposure_effects():
    _extracted, _results, _scenario, physical, settlement_inputs = (
        _phase_e_base_inputs()
    )

    artifact = build_dppa_case_2_contract_risk_sensitivity(
        settlement_inputs,
        physical,
        dppa_adder_multipliers=(0.5, 1.0, 1.5),
        kpp_multipliers=(0.8, 1.0, 1.2),
        excess_generation_treatments=(
            "excluded_from_buyer_settlement",
            "cfd_on_excess_generation",
        ),
    )

    adder_results = artifact["adder_sensitivity"]["results"]
    kpp_results = artifact["kpp_sensitivity"]["results"]
    excess_results = artifact["excess_treatment_sensitivity"]["results"]

    assert (
        adder_results[0]["buyer_minus_benchmark_vnd"]
        < adder_results[-1]["buyer_minus_benchmark_vnd"]
    )
    assert (
        kpp_results[0]["buyer_minus_benchmark_vnd"]
        < kpp_results[-1]["buyer_minus_benchmark_vnd"]
    )
    assert (
        excess_results[0]["excess_generation_treatment"]
        == "excluded_from_buyer_settlement"
    )
    assert (
        excess_results[1]["excess_generation_treatment"] == "cfd_on_excess_generation"
    )
    assert excess_results[1]["buyer_excess_cfd_payment_vnd"] == 1240.0
    assert (
        excess_results[1]["buyer_minus_benchmark_vnd"]
        > excess_results[0]["buyer_minus_benchmark_vnd"]
    )
