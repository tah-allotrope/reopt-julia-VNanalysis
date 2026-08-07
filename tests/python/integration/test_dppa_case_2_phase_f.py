"""Regression tests for Ninhsim DPPA Case 2 Phase F execution surfaces."""

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
    "build_ninhsim_reopt_input_dppa_case_2_phase_f_module",
    "scripts/python/integration/build_ninhsim_reopt_input.py",
)

from reopt_pysam_vn.integration.bridge import (
    build_dppa_case_2_single_owner_inputs,
)
from reopt_pysam_vn.integration.dppa_case_2 import (
    build_dppa_case_2_buyer_benchmark,
    build_dppa_case_2_developer_screening,
    build_dppa_case_2_market_reference_artifact,
    build_dppa_case_2_physical_summary,
    build_dppa_case_2_reopt_pysam_comparison,
    build_dppa_case_2_settlement_inputs,
    run_dppa_case_2_buyer_settlement,
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


def test_build_dppa_case_2_market_reference_artifact_prefers_cfmp_and_normalizes_units():
    source_payload = {
        "cfmp_vnd_per_mwh": [1_500_000.0, 1_600_000.0, 1_700_000.0],
        "fmp_vnd_per_mwh": [1_200_000.0, 1_250_000.0, 1_300_000.0],
    }

    artifact = build_dppa_case_2_market_reference_artifact(
        source_payload,
        source_path="data/interim/example_market.json",
        source_case="example_south_case",
    )

    assert artifact["market_reference_price_type"] == "repo_actual_cfmp_transfer"
    assert artifact["selected_series_field"] == "cfmp_vnd_per_mwh"
    assert artifact["normalization_method"] == "vnd_per_mwh_converted_to_vnd_per_kwh"
    assert artifact["hourly_series_vnd_per_kwh"] == [1500.0, 1600.0, 1700.0]


def test_phase_f_screening_keeps_buyer_and_developer_failures_separate_with_actual_market_series():
    extracted = _synthetic_extracted()
    results = _synthetic_results()
    scenario = build_scenario_dppa_case_2(extracted)
    physical = build_dppa_case_2_physical_summary(results, extracted, scenario)
    market_reference = build_dppa_case_2_market_reference_artifact(
        {"cfmp_vnd_per_mwh": [1_500.0, 1_550.0, 1_600.0]},
        source_path="data/interim/example_market.json",
        source_case="example_south_case",
    )
    settlement_inputs = build_dppa_case_2_settlement_inputs(
        results,
        extracted,
        scenario,
        market_reference_artifact=market_reference,
    )
    settlement = run_dppa_case_2_buyer_settlement(settlement_inputs)
    benchmark = build_dppa_case_2_buyer_benchmark(physical, settlement)
    developer_inputs = build_dppa_case_2_single_owner_inputs(
        results,
        scenario,
        settlement_inputs,
    )

    pysam_results = {
        "model": "PySAM Single Owner",
        "status": "ok",
        "runtime": {"python": ".venv/Scripts/python.exe"},
        "inputs": {
            "system_capacity_kw": developer_inputs.system_capacity_kw,
            "annual_generation_kwh": developer_inputs.annual_generation_kwh,
            "ppa_price_input_usd_per_kwh": developer_inputs.ppa_price_input_usd_per_kwh,
            "target_irr_fraction": developer_inputs.target_irr_fraction,
        },
        "case": {
            "year_one_ppa_price_vnd_per_kwh": settlement_inputs[
                "strike_price_vnd_per_kwh"
            ]
        },
        "outputs": {
            "project_return_aftertax_irr_fraction": 0.12,
            "project_return_aftertax_npv_usd": -5000.0,
            "min_dscr": 0.91,
        },
        "annual_cashflows": [],
    }

    comparison = build_dppa_case_2_reopt_pysam_comparison(
        physical,
        settlement,
        pysam_results,
    )
    screening = build_dppa_case_2_developer_screening(
        benchmark,
        pysam_results,
        comparison,
        market_reference_artifact=market_reference,
        phase_e_reference={"recommended_position": "no_viable_case_found"},
    )

    assert math.isclose(comparison["alignment"]["pv_size_gap_kw"], 0.0, abs_tol=1e-9)
    assert math.isclose(
        comparison["alignment"]["annual_generation_gap_kwh"], 0.0, abs_tol=1e-9
    )
    assert screening["buyer_view"]["buyer_passes"] is False
    assert screening["developer_view"]["developer_passes_target_irr"] is False
    assert screening["decision"]["combined_pass"] is False
    assert screening["decision"]["recommended_position"] == "reject_current_case"
    assert (
        screening["market_reference"]["market_reference_price_type"]
        == "repo_actual_cfmp_transfer"
    )
