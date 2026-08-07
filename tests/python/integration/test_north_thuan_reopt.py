"""
Regression tests for the North Thuan REopt validation workflow.

These tests lock the synthetic load builder, scenario generator, comparison
metrics, and virtual DPPA revenue helper used by the North Thuan pipeline.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python" / "reopt"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python" / "integration"))

from build_north_thuan_load_profile import (
    NORTH_THUAN_INPUTS,
    build_extracted_inputs,
    build_synthetic_load_profile,
)
from build_north_thuan_reopt_input import (
    build_scenario_a,
    build_scenario_b,
    build_scenario_c,
)
from compare_north_thuan_reopt_vs_staff import (
    build_staff_comparison,
    extract_scenario_metrics,
)
from dppa_settlement import compute_virtual_dppa_developer_revenue


def _synthetic_results() -> dict:
    matched_per_hour_kw = 70_050_000.0 / 8760.0
    generation_per_hour_kw = 117_560_000.0 / 8760.0
    pv_to_load_kw = 3_000.0
    wind_to_load_kw = 4_000.0
    storage_to_load_kw = matched_per_hour_kw - pv_to_load_kw - wind_to_load_kw

    return {
        "status": "optimal",
        "PV": {
            "size_kw": 30_000.0,
            "year_one_energy_produced_kwh": 51_000_000.0,
            "annual_energy_exported_kwh": 800_000.0,
            "electric_to_load_series_kw": [pv_to_load_kw] * 8760,
            "electric_to_grid_series_kw": [91.324200913242] * 8760,
        },
        "Wind": {
            "size_kw": 20_000.0,
            "year_one_energy_produced_kwh": 66_560_000.0,
            "annual_energy_exported_kwh": 0.0,
            "electric_to_load_series_kw": [wind_to_load_kw] * 8760,
        },
        "ElectricStorage": {
            "size_kw": 10_000.0,
            "size_kwh": 40_000.0,
            "storage_to_load_series_kw": [storage_to_load_kw] * 8760,
        },
        "ElectricUtility": {
            "annual_energy_supplied_kwh": 170_850_000.0,
            "electric_to_load_series_kw": [19_503.424657534245] * 8760,
        },
        "Financial": {
            "npv": 7_970_000.0,
            "simple_payback_years": 6.2,
            "year_one_total_operating_cost_savings_before_tax": 1_300_000.0,
        },
        "_debug_generation_series_kw": [generation_per_hour_kw] * 8760,
    }


def test_build_synthetic_load_profile_hits_8760_annual_energy_and_peak():
    profile = build_synthetic_load_profile(
        annual_gwh=NORTH_THUAN_INPUTS["factory_annual_load_gwh"],
        mean_mw=NORTH_THUAN_INPUTS["factory_mean_mw"],
        peak_mw=NORTH_THUAN_INPUTS["factory_peak_mw"],
        year=2025,
    )

    assert len(profile) == 8760
    assert min(profile) >= 0.0
    assert (
        abs(sum(profile) / 1_000_000.0 - NORTH_THUAN_INPUTS["factory_annual_load_gwh"])
        < 1e-6
    )
    assert abs(max(profile) / 1_000.0 - NORTH_THUAN_INPUTS["factory_peak_mw"]) < 1e-6


def test_build_extracted_inputs_contains_loads_and_market_series():
    extracted = build_extracted_inputs()

    assert extracted["project"].startswith("North Thuan")
    assert len(extracted["loads_kw"]) == 8760
    assert len(extracted["fmp_usd_per_kwh"]) == 8760
    assert extracted["assumptions"]["solar_mw"] == 30.0
    assert extracted["assumptions"]["wind_mw"] == 20.0


def test_scenario_builder_sets_fixed_optimized_and_no_bess_variants():
    extracted = build_extracted_inputs()

    scenario_a = build_scenario_a(extracted)
    scenario_b = build_scenario_b(extracted)
    scenario_c = build_scenario_c(extracted)

    assert scenario_a["PV"]["min_kw"] == 30_000.0
    assert scenario_a["Wind"]["min_kw"] == 20_000.0
    assert scenario_a["ElectricStorage"]["min_kwh"] == 40_000.0
    assert set(scenario_a["ElectricTariff"]["tou_energy_rates_per_kwh"]) == {0.055}

    assert scenario_b["PV"]["min_kw"] == 0.0
    assert scenario_b["PV"]["max_kw"] > scenario_a["PV"]["max_kw"]
    assert scenario_b["Wind"]["min_kw"] == 0.0
    assert scenario_b["ElectricStorage"]["min_kwh"] == 0.0

    assert scenario_c["ElectricStorage"]["max_kw"] == 0.0
    assert scenario_c["ElectricStorage"]["max_kwh"] == 0.0


def test_extract_scenario_metrics_computes_matched_penetration_and_self_consumption():
    results = _synthetic_results()
    extracted = build_extracted_inputs()
    extracted["loads_kw"] = [27_500.0] * 8760

    metrics = extract_scenario_metrics(results, extracted)
    comparison = build_staff_comparison(metrics)
    comparison_by_key = {row["key"]: row for row in comparison}

    assert round(metrics["solar_gwh_yr1"], 1) == 51.0
    assert round(metrics["wind_gwh_yr1"], 2) == 66.56
    assert round(metrics["matched_gwh_yr1"], 2) == 70.05
    assert round(metrics["re_penetration_pct"], 1) == 48.8
    assert round(metrics["self_consumption_pct"], 1) == 59.6
    assert comparison_by_key["matched_gwh_yr1"]["status"] == "OK"


def test_virtual_dppa_revenue_helper_combines_strike_and_fmp_revenue():
    matched_per_hour_kw = 70_050_000.0 / 8760.0
    generation_per_hour_kw = 117_560_000.0 / 8760.0
    strike = 0.055
    fmp = 0.0452

    revenue = compute_virtual_dppa_developer_revenue(
        matched_series_kw=[matched_per_hour_kw] * 8760,
        generation_series_kw=[generation_per_hour_kw] * 8760,
        strike_price_usd_per_kwh=strike,
        fmp_usd_per_kwh=[fmp] * 8760,
    )

    expected = 70_050_000.0 * strike + (117_560_000.0 - 70_050_000.0) * fmp

    assert abs(revenue["matched_volume_mwh"] - 70_050.0) < 1e-6
    assert abs(revenue["unmatched_volume_mwh"] - 47_510.0) < 1e-6
    assert abs(revenue["developer_revenue_yr1_usd"] - expected) < 1e-6


def test_extract_scenario_metrics_uses_wind_annual_fallback_and_counts_storage_charging():
    results = {
        "status": "optimal",
        "PV": {
            "year_one_energy_produced_kwh": 45_000_000.0,
            "electric_to_load_series_kw": [2_000.0] * 8760,
            "electric_to_storage_series_kw": [500.0] * 8760,
            "electric_to_grid_series_kw": [0.0] * 8760,
        },
        "Wind": {
            "annual_energy_produced_kwh": 66_000_000.0,
            "electric_to_load_series_kw": [3_000.0] * 8760,
            "electric_to_storage_series_kw": [250.0] * 8760,
            "electric_to_grid_series_kw": [0.0] * 8760,
        },
        "ElectricStorage": {
            "storage_to_load_series_kw": [500.0] * 8760,
        },
        "ElectricUtility": {
            "electric_to_load_series_kw": [20_000.0] * 8760,
        },
        "Financial": {"npv": 7_000_000.0},
    }
    extracted = build_extracted_inputs()

    metrics = extract_scenario_metrics(results, extracted)

    assert metrics["wind_gwh_yr1"] == 66.0
    assert metrics["total_gen_gwh_yr1"] == 111.0
    assert abs(sum(metrics["generation_series_kw"]) / 1_000_000.0 - 50.37) < 1e-6
