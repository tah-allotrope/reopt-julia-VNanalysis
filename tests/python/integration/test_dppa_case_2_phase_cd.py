"""Regression tests for Ninhsim DPPA Case 2 Phase C/D execution surfaces."""

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
    "build_ninhsim_reopt_input_dppa_case_2_module",
    "scripts/python/integration/build_ninhsim_reopt_input.py",
)

from reopt_pysam_vn.integration.dppa_case_2 import (
    build_dppa_case_2_buyer_benchmark,
    build_dppa_case_2_market_proxy,
    build_dppa_case_2_physical_summary,
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
            "electric_to_grid_series_kw": [30.0, 20.0, 0.0],
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
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.04,
        },
    }


def _settlement_inputs() -> dict:
    # Full 8760 hours: the three meaningful hours first, zero-padded after.
    # Zero hours contribute nothing to any total, so every numeric assertion
    # below matches the pre-typed-core 3-hour run exactly.
    pad = [0.0] * (8760 - 3)
    return {
        "settlement_quantity_rule": "min_load_and_contracted_generation",
        "matched_quantity_rule": "min_load_and_contracted_generation",
        "excess_generation_treatment": "excluded_from_buyer_settlement",
        "market_reference_price_type": "proxy_cfmp_or_fmp",
        "load_kwh_series": [100.0, 100.0, 100.0] + pad,
        "contracted_generation_kwh_series": [80.0, 120.0, 40.0] + pad,
        "market_reference_price_vnd_per_kwh_series": [70.0, 90.0, 110.0] + pad,
        "evn_retail_rate_vnd_per_kwh_series": [100.0, 100.0, 100.0] + pad,
        "strike_price_vnd_per_kwh": 95.0,
        "dppa_adder_vnd_per_kwh": 5.0,
        "kpp_factor": 1.1,
        "exchange_rate_vnd_per_usd": 25_000.0,
    }


def test_build_scenario_dppa_case_2_uses_synthetic_scope_without_private_wire_shortcuts():
    extracted = _synthetic_extracted()

    scenario = build_scenario_dppa_case_2(extracted)

    assert "ElectricTariff" in scenario
    assert "tou_energy_rates_per_kwh" in scenario["ElectricTariff"]
    assert "tou_energy_rates_vnd_per_kwh" not in scenario["ElectricTariff"]
    assert scenario["Wind"]["max_kw"] == 0.0
    assert scenario["ElectricStorage"]["can_grid_charge"] is False
    assert "min_duration_hours" not in scenario["ElectricStorage"]
    assert scenario["_meta"]["contract_type"] == "synthetic_financial_dppa"
    assert scenario["_meta"]["buyer_settlement_model"] == "post_processed_hourly_cfd"
    assert (
        scenario["_meta"]["excess_generation_treatment"]
        == "excluded_from_buyer_settlement"
    )


def test_market_proxy_and_settlement_inputs_use_hourly_proxy_when_actual_market_series_missing():
    extracted = _synthetic_extracted()
    results = _synthetic_results()
    scenario = build_scenario_dppa_case_2(extracted)

    proxy = build_dppa_case_2_market_proxy(extracted)
    settlement_inputs = build_dppa_case_2_settlement_inputs(
        results, extracted, scenario
    )

    assert proxy["market_reference_price_type"] == "proxy_cfmp_or_fmp"
    assert math.isclose(proxy["hourly_series_vnd_per_kwh"][0], 33.0, abs_tol=1e-9)
    assert settlement_inputs["market_reference_price_type"] == "proxy_cfmp_or_fmp"
    assert settlement_inputs["contracted_generation_kwh_series"] == [80.0, 90.0, 40.0]
    assert settlement_inputs["load_kwh_series"] == [100.0, 100.0, 100.0]


def test_physical_summary_tracks_contract_generation_grid_shortfall_and_optional_storage():
    extracted = _synthetic_extracted()
    results = _synthetic_results()
    scenario = build_scenario_dppa_case_2(extracted)

    summary = build_dppa_case_2_physical_summary(results, extracted, scenario)

    assert summary["optimal_mix"]["pv_size_mw"] == 1.5
    assert summary["optimal_mix"]["bess_mw"] == 0.25
    assert math.isclose(
        summary["energy_summary"]["contracted_generation_kwh"],
        210.0,
        abs_tol=1e-9,
    )
    assert math.isclose(
        summary["energy_summary"]["grid_supplied_kwh"],
        80.0,
        abs_tol=1e-9,
    )
    assert summary["design_checks"]["wind_disabled"] is True
    assert summary["design_checks"]["storage_is_optional"] is True


def test_buyer_settlement_engine_computes_matched_shortfall_excess_and_negative_cfd_hours():
    settlement = run_dppa_case_2_buyer_settlement(_settlement_inputs())

    hourly = settlement["hourly_ledger"]
    summary = settlement["summary"]

    assert hourly[0]["matched_quantity_kwh"] == 80.0
    assert hourly[1]["excess_quantity_kwh"] == 20.0
    assert hourly[2]["buyer_cfd_payment_vnd"] == -600.0
    assert summary["matched_quantity_kwh"] == 220.0
    assert summary["shortfall_quantity_kwh"] == 80.0
    assert summary["excess_quantity_kwh"] == 20.0
    assert summary["hours_with_negative_cfd_credit"] == 1
    assert summary["buyer_total_payment_vnd"] == 31_900.0


def test_buyer_benchmark_artifact_flags_customer_premium_when_settlement_exceeds_evn():
    settlement = run_dppa_case_2_buyer_settlement(_settlement_inputs())
    physical_summary = {
        "model": "synthetic physical summary",
        "status": "optimal",
        "site_load_basis": {"annual_load_gwh": 0.0003},
        "optimal_mix": {"pv_size_mw": 1.5, "bess_mw": 0.25, "bess_mwh": 0.5},
        "energy_summary": {
            "contracted_generation_kwh": 240.0,
            "grid_supplied_kwh": 80.0,
            "total_load_kwh": 300.0,
        },
    }

    benchmark = build_dppa_case_2_buyer_benchmark(physical_summary, settlement)

    assert benchmark["year_one_costs"]["benchmark_evn_total_cost_vnd"] == 30_000.0
    assert benchmark["year_one_costs"]["buyer_total_payment_vnd"] == 31_900.0
    assert benchmark["year_one_costs"]["buyer_premium_vs_evn_vnd"] == 1_900.0
    assert benchmark["decision"]["buyer_savings_positive"] is False
    assert benchmark["decision"]["recommended_position"] == "customer_premium_vs_evn"
