"""
Regression tests for the Ninhsim bundled-CPPA optimization workflow.
"""

from importlib.machinery import ModuleSpec
import math
import importlib.util
import sys
from pathlib import Path

import pytest

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


ANALYZE_NINHSIM_CPPA = _load_module(
    "analyze_ninhsim_cppa_module",
    "scripts/python/integration/analyze_ninhsim_cppa.py",
)
BUILD_NINHSIM_EXTRACTED = _load_module(
    "build_ninhsim_extracted_inputs_module",
    "scripts/python/integration/build_ninhsim_extracted_inputs.py",
)
BUILD_NINHSIM_REOPT_INPUT = _load_module(
    "build_ninhsim_reopt_input_module",
    "scripts/python/integration/build_ninhsim_reopt_input.py",
)

build_commercial_candidate_memo = ANALYZE_NINHSIM_CPPA.build_commercial_candidate_memo
build_summary = ANALYZE_NINHSIM_CPPA.build_summary
calculate_customer_first_annual_path = (
    ANALYZE_NINHSIM_CPPA.calculate_customer_first_annual_path
)
calculate_cppa_sensitivity_bands = ANALYZE_NINHSIM_CPPA.calculate_cppa_sensitivity_bands
calculate_customer_bill_breakdown = (
    ANALYZE_NINHSIM_CPPA.calculate_customer_bill_breakdown
)
calculate_customer_equivalent_strike = (
    ANALYZE_NINHSIM_CPPA.calculate_customer_equivalent_strike
)
calculate_financial_screening_view = (
    ANALYZE_NINHSIM_CPPA.calculate_financial_screening_view
)
calculate_multi_year_cppa_path = ANALYZE_NINHSIM_CPPA.calculate_multi_year_cppa_path
from reopt_pysam_vn.integration.ninhsim_solar_storage_60pct import (  # noqa: E402
    build_combined_decision_artifact,
    build_ninhsim_60pct_analysis,
    build_target_fraction_candidates,
    calculate_ninhsim_coverage_summary,
    calculate_ninhsim_fixed_strike,
)

PROJECT_SITE = BUILD_NINHSIM_EXTRACTED.PROJECT_SITE
build_extracted_inputs = BUILD_NINHSIM_EXTRACTED.build_extracted_inputs
build_scenario_a = BUILD_NINHSIM_REOPT_INPUT.build_scenario_a
build_scenario_b = BUILD_NINHSIM_REOPT_INPUT.build_scenario_b
build_scenario_c = BUILD_NINHSIM_REOPT_INPUT.build_scenario_c
build_scenario_dppa_case_1 = BUILD_NINHSIM_REOPT_INPUT.build_scenario_dppa_case_1


def _synthetic_results() -> dict:
    renewable_to_load_kw = 10_000.0
    residual_grid_kw = 11_000.0
    return {
        "status": "optimal",
        "PV": {
            "size_kw": 18_000.0,
            "year_one_energy_produced_kwh": 40_000_000.0,
            "electric_to_load_series_kw": [6_000.0] * 8760,
            "electric_to_grid_series_kw": [200.0] * 8760,
        },
        "Wind": {
            "size_kw": 12_000.0,
            "year_one_energy_produced_kwh": 32_000_000.0,
            "electric_to_load_series_kw": [3_000.0] * 8760,
        },
        "ElectricStorage": {
            "size_kw": 4_000.0,
            "size_kwh": 16_000.0,
            "storage_to_load_series_kw": [1_000.0] * 8760,
        },
        "ElectricUtility": {
            "electric_to_load_series_kw": [residual_grid_kw] * 8760,
        },
        "Financial": {
            "npv": 12_500_000.0,
            "year_one_total_operating_cost_savings_before_tax": 1_700_000.0,
        },
        "_test_total_load_series_kw": [renewable_to_load_kw + residual_grid_kw] * 8760,
    }


def _synthetic_solar_storage_results() -> dict:
    _renewable_to_load_kw = 12_000.0
    renewable_to_grid_kw = 2_000.0
    residual_grid_kw = 8_000.0
    return {
        "status": "optimal",
        "PV": {
            "size_kw": 24_000.0,
            "year_one_energy_produced_kwh": 70_000_000.0,
            "electric_to_load_series_kw": [10_000.0] * 8760,
            "electric_to_grid_series_kw": [renewable_to_grid_kw] * 8760,
        },
        "Wind": {
            "size_kw": 0.0,
            "year_one_energy_produced_kwh": 0.0,
            "electric_to_load_series_kw": [0.0] * 8760,
            "electric_to_grid_series_kw": [0.0] * 8760,
        },
        "ElectricStorage": {
            "size_kw": 6_000.0,
            "size_kwh": 24_000.0,
            "initial_capital_cost": 4_800_000.0,
            "storage_to_load_series_kw": [2_000.0] * 8760,
        },
        "ElectricUtility": {
            "electric_to_load_series_kw": [residual_grid_kw] * 8760,
        },
        "Financial": {
            "npv": 9_000_000.0,
            "analysis_years": 20,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.04,
            "initial_capital_costs": 22_800_000.0,
            "initial_capital_costs_after_incentives": 22_800_000.0,
        },
    }


@pytest.mark.xfail(
    reason="numeric benchmark drift, red since 2026-07-04, tracked in activeContext.md 'Known pre-existing test failures'",
    strict=False,
)
def test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark():
    extracted = build_extracted_inputs()

    assert extracted["project"].startswith("Ninhsim")
    assert extracted["site"] == PROJECT_SITE
    assert len(extracted["loads_kw"]) == 8760
    assert min(extracted["loads_kw"]) > 0.0
    assert extracted["load_cleaning"]["missing_count"] == 1
    assert extracted["load_cleaning"]["final_count"] == 8760
    assert math.isclose(
        extracted["benchmark"]["weighted_evn_price_usd_per_kwh"],
        0.076473,
        rel_tol=0,
        abs_tol=1e-6,
    )


def test_scenario_builders_preserve_capex_and_enable_wind_optimization():
    extracted = build_extracted_inputs()

    scenario_a = build_scenario_a(extracted)
    scenario_b = build_scenario_b(extracted)

    assert scenario_a["Site"] == {
        "latitude": PROJECT_SITE["latitude"],
        "longitude": PROJECT_SITE["longitude"],
    }
    assert scenario_a["_meta"]["site"] == PROJECT_SITE
    assert scenario_a["PV"]["installed_cost_per_kw"] == 750.0
    assert scenario_a["ElectricStorage"]["installed_cost_per_kw"] == 200.0
    assert scenario_a["ElectricStorage"]["installed_cost_per_kwh"] == 200.0
    assert scenario_a["Wind"]["installed_cost_per_kw"] == 1350.0
    assert scenario_a["Wind"]["max_kw"] == 0.0
    assert scenario_a["Financial"]["analysis_years"] == 20

    assert scenario_b["PV"]["min_kw"] == 0.0
    assert scenario_b["PV"]["max_kw"] > 0.0
    assert scenario_b["Wind"]["min_kw"] == 0.0
    assert scenario_b["Wind"]["max_kw"] > 0.0
    assert scenario_b["ElectricStorage"]["min_kwh"] == 0.0
    assert scenario_b["PV"].get("production_factor_series") is None


def test_scenario_c_builds_solar_storage_only_case_with_delivered_energy_target():
    extracted = build_extracted_inputs()

    scenario_c = build_scenario_c(extracted)

    assert scenario_c["Wind"]["max_kw"] == 0.0
    assert scenario_c["Wind"]["min_kw"] == 0.0
    assert scenario_c["PV"]["max_kw"] == 100_000.0
    assert scenario_c["ElectricStorage"]["max_kw"] == 60_000.0
    assert scenario_c["ElectricStorage"]["max_kwh"] == 240_000.0
    assert scenario_c["ElectricStorage"]["can_grid_charge"] is False
    assert scenario_c["Site"]["renewable_electricity_min_fraction"] == 0.60
    assert (
        scenario_c["Site"]["include_grid_renewable_fraction_in_RE_constraints"] is False
    )
    assert (
        scenario_c["Site"]["include_exported_renewable_electricity_in_total"] is False
    )
    assert scenario_c["_meta"]["requested_renewable_delivered_fraction_of_load"] == 0.60


def test_scenario_dppa_case_1_builds_private_wire_two_hour_no_export_case():
    extracted = build_extracted_inputs()

    scenario = build_scenario_dppa_case_1(extracted)

    assert scenario["Wind"]["max_kw"] == 0.0
    assert scenario["PV"]["can_wholesale"] is False
    assert scenario["PV"]["can_net_meter"] is False
    assert scenario["ElectricStorage"]["can_grid_charge"] is False
    assert scenario["ElectricStorage"]["min_duration_hours"] == 2.0
    assert scenario["ElectricStorage"]["max_duration_hours"] == 2.0
    assert scenario["_meta"]["contract_type"] == "private_wire"


def test_build_target_fraction_candidates_starts_at_requested_target_and_steps_down():
    assert build_target_fraction_candidates(0.60) == [0.6, 0.575, 0.55, 0.525, 0.5]


def test_fixed_strike_peg_uses_weighted_evn_discount_directly():
    extracted = build_extracted_inputs()
    results = _synthetic_solar_storage_results()

    fixed_strike = calculate_ninhsim_fixed_strike(results, extracted)

    assert math.isclose(
        fixed_strike["year_one_strike_vnd_per_kwh"],
        extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"] * 0.95,
        rel_tol=0,
        abs_tol=1e-9,
    )
    assert math.isclose(
        fixed_strike["merchant_price_fraction_of_evn"],
        extracted["benchmark"]["wholesale_rate_usd_per_kwh"]
        / extracted["benchmark"]["weighted_evn_price_usd_per_kwh"],
        rel_tol=0,
        abs_tol=1e-12,
    )


def test_coverage_summary_tracks_delivered_fraction_and_excludes_exports_from_target():
    extracted = build_extracted_inputs()
    results = _synthetic_solar_storage_results()

    coverage = calculate_ninhsim_coverage_summary(
        results, extracted, target_fraction=0.60
    )

    assert coverage["renewable_delivered_kwh"] == 105_120_000.0
    assert coverage["exported_renewable_kwh"] == 17_520_000.0
    assert coverage["sold_renewable_kwh"] == 122_640_000.0
    assert coverage["achieved_delivered_fraction_of_load"] < 0.60
    assert coverage["meets_requested_target"] is False


def test_build_ninhsim_60pct_analysis_includes_tariff_peg_coverage_and_finance_screen():
    extracted = build_extracted_inputs()
    results = _synthetic_solar_storage_results()
    scenario = build_scenario_c(extracted)

    analysis = build_ninhsim_60pct_analysis(results, extracted, scenario)

    assert analysis["coverage_summary"]["requested_target_fraction"] == 0.60
    assert analysis["coverage_summary"]["meets_requested_target"] is False
    assert analysis["optimal_mix"]["wind_size_mw"] == 0.0
    assert analysis["year_one_financial_screen"]["developer_revenue_usd"] > 0.0
    assert analysis["developer_revenue_path"]
    assert analysis["warnings"]


def test_combined_decision_artifact_flags_customer_feasible_but_not_financeable_when_irr_fails():
    extracted = build_extracted_inputs()
    results = _synthetic_solar_storage_results()
    scenario = build_scenario_c(extracted)
    analysis = build_ninhsim_60pct_analysis(results, extracted, scenario)
    analysis["coverage_summary"]["meets_requested_target"] = True
    analysis["coverage_summary"]["meets_enforced_target"] = True
    pysam_results = {
        "status": "ok",
        "case": {
            "source_case": "ninhsim_60pct_solar_storage",
            "requested_target_fraction": 0.60,
            "achieved_delivered_fraction_of_load": analysis["coverage_summary"][
                "achieved_delivered_fraction_of_load"
            ],
            "year_one_strike_vnd_per_kwh": analysis["fixed_strike"][
                "year_one_strike_vnd_per_kwh"
            ],
        },
        "outputs": {
            "project_return_aftertax_npv_usd": -5_000_000.0,
            "project_return_aftertax_irr_fraction": 0.09,
            "project_return_pretax_irr_fraction": 0.11,
            "size_of_debt_usd": 12_000_000.0,
            "min_dscr": 0.82,
            "npv_ppa_revenue_usd": 55_000_000.0,
        },
        "annual_cashflows": [{"year": 1, "total_revenue_usd": 6_200_000.0}],
    }

    combined = build_combined_decision_artifact(analysis, pysam_results)

    assert combined["decision"]["operationally_feasible"] is True
    assert combined["decision"]["financeable_at_default_target_irr"] is False
    assert (
        combined["developer_finance_summary"]["project_return_aftertax_irr_fraction"]
        == 0.09
    )


def test_customer_equivalent_strike_matches_weighted_price_target():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    bill = calculate_customer_bill_breakdown(results, extracted)
    strike = calculate_customer_equivalent_strike(results, extracted)

    assert bill["renewable_delivered_kwh"] == 87_600_000.0
    assert bill["grid_supplied_kwh"] == 96_360_000.0
    assert strike["max_cppa_strike_usd_per_kwh"] > 0.0
    assert (
        strike["max_cppa_strike_vnd_per_kwh"]
        > extracted["benchmark"]["wholesale_rate_vnd_per_kwh"]
    )
    assert math.isclose(
        strike["customer_blended_price_at_max_strike_usd_per_kwh"],
        extracted["benchmark"]["weighted_evn_price_usd_per_kwh"],
        rel_tol=0,
        abs_tol=1e-9,
    )


def test_build_summary_accepts_wind_annual_energy_key():
    extracted = build_extracted_inputs()
    results = _synthetic_results()
    results["Wind"].pop("year_one_energy_produced_kwh")
    results["Wind"]["annual_energy_produced_kwh"] = 32_000_000.0

    summary = build_summary(results, extracted)

    assert math.isclose(summary["year_one_energy"]["wind_gwh"], 32.0, abs_tol=1e-9)


def test_multi_year_cppa_path_escalates_with_evn_tariff_growth():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    path = calculate_multi_year_cppa_path(results, extracted, analysis_years=4)

    assert path[0]["year"] == 1
    assert math.isclose(
        path[0]["cPPA_strike_usd_per_kwh"],
        calculate_customer_equivalent_strike(results, extracted)[
            "max_cppa_strike_usd_per_kwh"
        ],
        rel_tol=0,
        abs_tol=1e-12,
    )
    assert math.isclose(
        path[1]["weighted_evn_benchmark_usd_per_kwh"],
        path[0]["weighted_evn_benchmark_usd_per_kwh"] * 1.05,
        rel_tol=0,
        abs_tol=1e-12,
    )
    assert math.isclose(
        path[3]["cPPA_strike_usd_per_kwh"],
        path[0]["cPPA_strike_usd_per_kwh"] * (1.05**3),
        rel_tol=0,
        abs_tol=1e-12,
    )
    for year in path:
        assert math.isclose(
            year["customer_blended_price_usd_per_kwh"],
            year["weighted_evn_benchmark_usd_per_kwh"],
            rel_tol=0,
            abs_tol=1e-12,
        )


def test_build_summary_includes_multi_year_cppa_path():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    summary = build_summary(results, extracted)

    assert summary["multi_year_cppa_path"]
    assert summary["multi_year_cppa_path"][0]["year"] == 1
    assert summary["multi_year_cppa_path"][-1]["year"] == 20


def test_financial_screening_view_projects_customer_cost_and_developer_revenue():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    view = calculate_financial_screening_view(results, extracted, analysis_years=3)

    assert view[0]["year"] == 1
    assert view[0]["developer_revenue_usd"] > 0.0
    assert math.isclose(
        view[0]["customer_total_cost_usd"],
        extracted["benchmark"]["annual_load_kwh"]
        * extracted["benchmark"]["weighted_evn_price_usd_per_kwh"],
        rel_tol=0,
        abs_tol=1e-6,
    )
    assert view[2]["developer_revenue_usd"] > view[0]["developer_revenue_usd"]
    assert view[2]["customer_savings_vs_evn_usd"] == 0.0


def test_build_summary_includes_financial_screening_view_and_npv_fields():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    summary = build_summary(results, extracted)

    assert summary["financial_screening_view"]
    assert summary["financial"]["developer_revenue_npv_usd"] > 0.0
    assert summary["financial"]["offtaker_cost_npv_usd"] > 0.0


def test_cppa_sensitivity_bands_capture_savings_and_premium_tradeoffs():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    bands = calculate_cppa_sensitivity_bands(
        results,
        extracted,
        strike_adjustment_fractions=[-0.10, -0.05, 0.0, 0.05],
        analysis_years=2,
    )

    assert [band["band_label"] for band in bands] == [
        "10% below ceiling",
        "5% below ceiling",
        "ceiling",
        "5% above ceiling",
    ]
    assert bands[0]["customer_savings_npv_usd"] > 0.0
    assert bands[0]["customer_premium_npv_usd"] == 0.0
    assert bands[2]["customer_savings_npv_usd"] == 0.0
    assert bands[2]["customer_premium_npv_usd"] == 0.0
    assert bands[3]["customer_premium_npv_usd"] > 0.0
    assert bands[3]["developer_revenue_npv_usd"] > bands[2]["developer_revenue_npv_usd"]


def test_build_summary_includes_strike_sensitivity_band_view():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    summary = build_summary(results, extracted)

    assert summary["strike_sensitivity_bands"]
    assert summary["strike_sensitivity_bands"][0]["relative_to_ceiling_fraction"] < 0.0
    assert summary["strike_sensitivity_bands"][-1]["relative_to_ceiling_fraction"] > 0.0


def test_customer_first_annual_path_applies_degradation_load_drift_and_caps_customer_exposure():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    annual_path = calculate_customer_first_annual_path(
        results,
        extracted,
        strike_adjustment_fraction=-0.05,
        analysis_years=3,
        annual_generation_degradation_fraction=0.01,
        annual_load_growth_fraction=0.02,
        unmatched_energy_price_fraction_of_evn=0.35,
    )

    assert annual_path[0]["band_label"] == "5% below ceiling"
    assert (
        annual_path[1]["renewable_delivered_kwh"]
        < annual_path[0]["renewable_delivered_kwh"]
    )
    assert annual_path[1]["total_load_kwh"] > annual_path[0]["total_load_kwh"]
    assert (
        annual_path[1]["unmatched_renewable_kwh"]
        >= annual_path[0]["unmatched_renewable_kwh"]
    )
    assert annual_path[0]["customer_savings_vs_evn_usd"] > 0.0
    assert (
        annual_path[0]["merchant_price_usd_per_kwh"]
        < annual_path[0]["residual_grid_price_usd_per_kwh"]
    )
    assert (
        annual_path[0]["customer_total_cost_usd"]
        < annual_path[0]["benchmark_evn_cost_usd"]
    )


def test_build_summary_includes_customer_first_recommendation_and_annual_path():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    summary = build_summary(results, extracted)

    assert (
        summary["customer_first_recommendation"]["recommended_band_label"]
        == "5% below ceiling"
    )
    assert summary["customer_first_annual_path"]
    assert summary["customer_first_annual_path"][0]["band_label"] == "5% below ceiling"


def test_commercial_candidate_memo_marks_shortlist_as_advance_hold_discard():
    extracted = build_extracted_inputs()
    results = _synthetic_results()
    summary = build_summary(results, extracted)

    memo = build_commercial_candidate_memo(summary)

    candidates = {
        candidate["band_label"]: candidate for candidate in memo["candidates"]
    }
    assert memo["recommended_band_label"] == "5% below ceiling"
    assert candidates["5% below ceiling"]["status"] == "advance"
    assert candidates["ceiling"]["status"] == "hold"
    assert candidates["5% above ceiling"]["status"] == "discard"
    assert candidates["5% above ceiling"]["customer_premium_npv_usd"] > 0.0


def test_build_summary_includes_commercial_candidate_memo():
    extracted = build_extracted_inputs()
    results = _synthetic_results()

    summary = build_summary(results, extracted)

    assert summary["commercial_candidate_memo"]
    assert (
        summary["commercial_candidate_memo"]["recommended_band_label"]
        == "5% below ceiling"
    )
