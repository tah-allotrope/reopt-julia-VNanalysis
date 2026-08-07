"""Regression tests for the Ninhsim DPPA Case 1 workflow."""

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


BUILD_NINHSIM_EXTRACTED = _load_module(
    "build_ninhsim_extracted_inputs_dppa_case_1_module",
    "scripts/python/integration/build_ninhsim_extracted_inputs.py",
)
BUILD_NINHSIM_REOPT_INPUT = _load_module(
    "build_ninhsim_reopt_input_dppa_case_1_module",
    "scripts/python/integration/build_ninhsim_reopt_input.py",
)

from reopt_pysam_vn.integration.dppa_case_1 import (
    build_dppa_case_1_combined_decision,
    build_dppa_case_1_comparison,
    build_dppa_case_1_placeholder_pysam_results,
    build_dppa_case_1_reopt_summary,
    calculate_private_wire_strike_basis,
)

build_extracted_inputs = BUILD_NINHSIM_EXTRACTED.build_extracted_inputs
build_scenario_dppa_case_1 = BUILD_NINHSIM_REOPT_INPUT.build_scenario_dppa_case_1


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
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.04,
            "initial_capital_costs": 16_250_000.0,
            "initial_capital_costs_after_incentives": 16_250_000.0,
        },
    }


def _synthetic_pysam_results() -> dict:
    return {
        "model": "PySAM PVWatts Battery Single Owner",
        "status": "ok",
        "case": {
            "source_case": "ninhsim_dppa_case_1",
            "year_one_private_wire_strike_vnd_per_kwh": 1149.86,
        },
        "outputs": {
            "project_return_aftertax_npv_usd": 2_500_000.0,
            "project_return_aftertax_irr_fraction": 0.162,
            "project_return_pretax_irr_fraction": 0.188,
            "size_of_debt_usd": 11_000_000.0,
            "debt_fraction": 0.70,
            "min_dscr": 1.21,
            "npv_ppa_revenue_usd": 21_000_000.0,
            "equity_irr_fraction": 0.174,
            "size_of_equity_usd": 4_750_000.0,
        },
        "energy_summary": {
            "annual_pv_ac_energy_kwh": 42_000_000.0,
            "annual_matched_load_kwh": 40_500_000.0,
            "annual_export_kwh": 18_000.0,
            "annual_battery_charge_from_system_kwh": 2_100_000.0,
            "annual_battery_charge_from_grid_kwh": 0.0,
            "annual_battery_discharge_to_load_kwh": 1_850_000.0,
            "annual_estimated_curtailment_kwh": 220_000.0,
        },
        "annual_cashflows": [
            {
                "year": 1,
                "total_revenue_usd": 1_900_000.0,
                "aftertax_cashflow_usd": 620_000.0,
                "debt_service_usd": 410_000.0,
                "debt_balance_usd": 10_600_000.0,
                "dscr": 1.21,
            }
        ],
        "notes": {},
    }


def _synthetic_results_without_battery() -> dict:
    results = _synthetic_results()
    results["ElectricStorage"] = {
        "size_kw": 0.0,
        "size_kwh": 0.0,
        "initial_capital_cost": 0.0,
        "storage_to_load_series_kw": [0.0] * 8760,
    }
    return results


def test_build_scenario_dppa_case_1_disables_export_and_locks_two_hour_storage():
    extracted = build_extracted_inputs()

    scenario = build_scenario_dppa_case_1(extracted)

    assert scenario["Wind"]["max_kw"] == 0.0
    assert scenario["PV"]["can_wholesale"] is False
    assert scenario["PV"]["can_net_meter"] is False
    assert scenario["ElectricStorage"]["can_grid_charge"] is False
    assert scenario["ElectricStorage"]["min_duration_hours"] == 2.0
    assert scenario["ElectricStorage"]["max_duration_hours"] == 2.0
    assert scenario["_meta"]["contract_type"] == "private_wire"
    assert (
        scenario["_meta"]["reopt_objective"]
        == "minimum_lifecycle_cost_with_no_export_intent"
    )


def test_private_wire_strike_basis_uses_bess_ceiling_only_when_thresholds_are_met():
    extracted = build_extracted_inputs()
    scenario = build_scenario_dppa_case_1(extracted)
    results = _synthetic_results()

    strike = calculate_private_wire_strike_basis(results, extracted, scenario)

    assert strike["qualifies_for_bess_private_wire_ceiling"] is True
    assert math.isclose(strike["battery_duration_hours"], 2.0, abs_tol=1e-9)
    assert strike["year_one_private_wire_strike_vnd_per_kwh"] == 1149.86
    assert strike["battery_power_fraction_of_pv"] >= 0.10
    assert strike["stored_output_fraction_of_delivered_energy"] >= 0.05


def test_dppa_case_1_reopt_summary_tracks_export_curtailment_and_strike_basis():
    extracted = build_extracted_inputs()
    scenario = build_scenario_dppa_case_1(extracted)
    results = _synthetic_results()

    summary = build_dppa_case_1_reopt_summary(results, extracted, scenario)

    assert summary["optimal_mix"]["bess_duration_hours"] == 2.0
    assert summary["energy_summary"]["exported_renewable_kwh"] == 175_200.0
    assert summary["energy_summary"]["curtailed_renewable_kwh"] == 438_000.0
    assert summary["design_checks"]["export_is_negligible"] is True
    assert (
        summary["private_wire_strike"]["year_one_private_wire_strike_vnd_per_kwh"]
        == 1149.86
    )


def test_dppa_case_1_combined_decision_requires_project_and_equity_irr_hurdles():
    extracted = build_extracted_inputs()
    scenario = build_scenario_dppa_case_1(extracted)
    results = _synthetic_results()
    summary = build_dppa_case_1_reopt_summary(results, extracted, scenario)
    pysam_results = _synthetic_pysam_results()

    comparison = build_dppa_case_1_comparison(summary, pysam_results)
    combined = build_dppa_case_1_combined_decision(summary, pysam_results, comparison)

    assert combined["decision"]["export_design_passes"] is True
    assert combined["decision"]["financeable_at_default_project_irr"] is True
    assert combined["decision"]["financeable_at_default_equity_irr"] is True
    assert combined["decision"]["recommended_position"] == "advance_for_review"
    assert comparison["energy_alignment"]["pysam_export_delta_kwh"] < 0.0


def test_dppa_case_1_placeholder_pysam_result_marks_zero_battery_case_as_needing_resize():
    extracted = build_extracted_inputs()
    scenario = build_scenario_dppa_case_1(extracted)
    results = _synthetic_results_without_battery()
    summary = build_dppa_case_1_reopt_summary(results, extracted, scenario)

    placeholder = build_dppa_case_1_placeholder_pysam_results(summary)
    comparison = build_dppa_case_1_comparison(summary, placeholder)
    combined = build_dppa_case_1_combined_decision(summary, placeholder, comparison)

    assert placeholder["status"] == "skipped"
    assert placeholder["case"]["skip_reason"] == "reopt_selected_zero_battery"
    assert combined["decision"]["financeable_at_default_project_irr"] is False
    assert combined["decision"]["recommended_position"] == "needs_reprice_or_resize"
    assert any("zero battery" in warning for warning in combined["warnings"])
