"""Regression tests for Saigon18 DPPA Case 3 Phase A/B design artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_3 import (
    DEFAULT_DPPA_ADDER_VND_PER_KWH,
    DEFAULT_KPP_FACTOR,
    DEFAULT_STRIKE_DISCOUNT_FRACTION,
    build_dppa_case_3_assumptions_register,
    build_dppa_case_3_edge_case_matrix,
    build_dppa_case_3_gap_register,
    build_dppa_case_3_input_package,
    build_dppa_case_3_phase_a_definition,
    build_dppa_case_3_settlement_design,
    build_dppa_case_3_settlement_schema,
    load_saigon18_cfmp_series,
    load_saigon18_fmp_series,
    load_saigon18_load_series,
    load_saigon18_tou_series,
    scale_load_to_annual_kwh,
)

EXTRACTED_PATH = (
    REPO_ROOT
    / "data"
    / "interim"
    / "saigon18"
    / "2026-03-20_saigon18_extracted_inputs.json"
)


def _load_extracted() -> dict:
    return json.loads(EXTRACTED_PATH.read_text(encoding="utf-8"))


def test_phase_a_definition_freezes_synthetic_case_and_5pct_strike_anchor():
    extracted = _load_extracted()

    definition = build_dppa_case_3_phase_a_definition(extracted)

    assert definition["case_identity"]["scenario_family"] == "DPPA Case 3"
    assert (
        definition["case_identity"]["contract_structure"] == "synthetic_financial_dppa"
    )
    assert (
        definition["strike_basis"]["strike_discount_fraction"]
        == DEFAULT_STRIKE_DISCOUNT_FRACTION
    )
    weighted_vnd = definition["strike_basis"]["weighted_evn_price_vnd_per_kwh"]
    expected_strike = weighted_vnd * (1.0 - DEFAULT_STRIKE_DISCOUNT_FRACTION)
    assert (
        abs(definition["strike_basis"]["year_one_strike_vnd_per_kwh"] - expected_strike)
        < 0.01
    )


def test_phase_a_definition_marks_site_consistent():
    extracted = _load_extracted()

    definition = build_dppa_case_3_phase_a_definition(extracted)

    block = definition["site_consistency_block"]
    assert block["load_source_case"] == "saigon18"
    assert block["market_source_case"] == "saigon18"
    assert block["tariff_source_case"] == "saigon18"
    assert block["same_site_basis"] is True
    assert block["same_project_workstream"] is True


def test_phase_a_definition_enforces_single_bounded_opt_lane():
    extracted = _load_extracted()

    definition = build_dppa_case_3_phase_a_definition(extracted)

    assert definition["physical_scope"]["lane_structure"] == "bounded_optimization_only"
    assert (
        definition["physical_scope"]["battery_requirement"] == "mandatory_storage_floor"
    )
    assert definition["physical_scope"]["storage_floor_min_kw"] > 0
    assert definition["physical_scope"]["storage_floor_min_kwh"] > 0


def test_phase_a_definition_includes_two_tariff_branches():
    extracted = _load_extracted()

    definition = build_dppa_case_3_phase_a_definition(extracted)

    branches = definition["tariff_branches"]
    assert len(branches) == 2
    branch_names = [b["branch_name"] for b in branches]
    assert "22kv_two_part_evn" in branch_names
    assert "legacy_tou_one_component" in branch_names
    reporting = definition["tariff_reporting_style"]
    assert reporting == "side_by_side_with_delta_columns"


def test_assumptions_register_captures_case_3_decisions():
    extracted = _load_extracted()

    assumptions = build_dppa_case_3_assumptions_register(extracted)

    assert (
        assumptions["questions"]["contract_structure"]["selected_answer"]
        == "synthetic_financial_dppa"
    )
    assert (
        assumptions["questions"]["settlement_quantity_rule"]["selected_answer"]
        == "min_load_and_contracted_generation"
    )
    assert (
        assumptions["questions"]["excess_generation_treatment"]["selected_answer"]
        == "excluded_from_buyer_settlement"
    )
    assert (
        assumptions["questions"]["physical_lane"]["selected_answer"]
        == "bounded_optimization_only_with_storage_floor"
    )
    assert (
        assumptions["questions"]["strike_treatment"]["selected_answer"]
        == "five_percent_below_weighted_evn_with_sensitivity_sweep"
    )
    assert (
        assumptions["questions"]["tariff_branches"]["selected_answer"]
        == "two_branches_side_by_side"
    )


def test_gap_register_links_shortcomings_to_mitigations():
    gap_register = build_dppa_case_3_gap_register()

    assert len(gap_register["inherited_shortcomings"]) >= 4
    for entry in gap_register["inherited_shortcomings"]:
        assert "shortcoming" in entry
        assert "source_case" in entry
        assert "case_3_mitigation" in entry
    pv_only_entries = [
        e
        for e in gap_register["inherited_shortcomings"]
        if "PV-only" in e["shortcoming"]
    ]
    assert len(pv_only_entries) >= 1
    assert any("storage_floor" in e["case_3_mitigation"] for e in pv_only_entries)


def test_settlement_design_and_schema_freeze_fixed_adder_kpp_and_actual_series_priority():
    extracted = _load_extracted()
    definition = build_dppa_case_3_phase_a_definition(extracted)
    assumptions = build_dppa_case_3_assumptions_register(extracted)

    design = build_dppa_case_3_settlement_design(definition, assumptions)
    schema = build_dppa_case_3_settlement_schema()

    assert (
        design["fixed_parameters"]["dppa_adder_vnd_per_kwh"]
        == DEFAULT_DPPA_ADDER_VND_PER_KWH
    )
    assert design["fixed_parameters"]["kpp_factor"] == DEFAULT_KPP_FACTOR
    assert (
        design["market_price_source_priority"][0] == "actual_hourly_cfmp_or_fmp_series"
    )
    assert (
        design["hourly_settlement"]["excess_generation_treatment"]
        == "excluded_from_buyer_settlement"
    )
    assert schema["properties"]["settlement_quantity_rule"]["enum"] == [
        "min_load_and_contracted_generation"
    ]
    assert schema["properties"]["excess_generation_treatment"]["enum"] == [
        "excluded_from_buyer_settlement"
    ]
    assert design["site_consistency_block"]["same_site_basis"] is True


def test_edge_case_matrix_includes_bilateral_cfd_and_excess_exclusion_cases():
    matrix = build_dppa_case_3_edge_case_matrix()

    case_names = {entry["case_name"] for entry in matrix["cases"]}

    assert "matched_hour_with_positive_buyer_cfd" in case_names
    assert "matched_hour_with_negative_buyer_cfd_credit" in case_names
    assert "excess_generation_hour_excluded_from_buyer_settlement" in case_names


def test_phase_ab_preparation_script_writes_canonical_artifacts(tmp_path: Path):
    output_dir = tmp_path / "reports"
    script = (
        REPO_ROOT
        / "scripts"
        / "python"
        / "integration"
        / "prepare_saigon18_dppa_case_3_phase_ab.py"
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Phase A definition written to" in completed.stdout
    assert "Phase B settlement schema written to" in completed.stdout
    date_prefix = "2026-04-20"
    assert (
        output_dir / f"{date_prefix}_saigon18_dppa-case-3_phase-a-definition.json"
    ).is_file()
    assert (
        output_dir
        / f"{date_prefix}_saigon18_dppa-case-3_phase-a-assumptions-register.json"
    ).is_file()
    assert (
        output_dir
        / f"{date_prefix}_saigon18_dppa-case-3_phase-b-settlement-design.json"
    ).is_file()
    assert (
        output_dir
        / f"{date_prefix}_saigon18_dppa-case-3_phase-b-settlement-schema.json"
    ).is_file()
    assert (
        output_dir / f"{date_prefix}_saigon18_dppa-case-3_phase-b-edge-case-matrix.json"
    ).is_file()
    assert (
        output_dir / f"{date_prefix}_saigon18_dppa-case-3_phase-a-gap-register.json"
    ).is_file()


def test_load_series_returns_8760_elements():
    extracted = _load_extracted()

    load = load_saigon18_load_series(extracted)

    assert len(load) == 8760
    assert all(isinstance(v, float) for v in load)
    assert sum(load) > 0


def test_market_series_returns_8760_elements_in_vnd_per_kwh():
    extracted = _load_extracted()

    cfmp = load_saigon18_cfmp_series(extracted)
    fmp = load_saigon18_fmp_series(extracted)

    assert len(cfmp) == 8760
    assert len(fmp) == 8760
    assert all(v >= 0 for v in cfmp)
    assert all(v >= 0 for v in fmp)
    assert max(cfmp) < 10.0


def test_tou_series_returns_8760_elements_with_known_rates():
    extracted = _load_extracted()

    tou = load_saigon18_tou_series(extracted)

    assert len(tou) == 8760
    assumptions = extracted["assumptions"]
    unique_rates = {round(v) for v in tou}
    assert int(assumptions["tariff_peak_vnd_per_kwh"]) in unique_rates
    assert int(assumptions["tariff_offpeak_vnd_per_kwh"]) in unique_rates
    assert int(assumptions["tariff_standard_vnd_per_kwh"]) in unique_rates


def test_scale_to_annual_kwh_adjusts_load_shape():
    extracted = _load_extracted()
    original = load_saigon18_load_series(extracted)
    _original_annual = sum(original)

    target = 200_000_000.0
    scaled = scale_load_to_annual_kwh(original, target)

    assert len(scaled) == 8760
    assert abs(sum(scaled) - target) < 1.0
    assert scaled[0] != original[0]


def test_input_package_has_site_consistency_and_two_tariff_branches():
    extracted = _load_extracted()

    package = build_dppa_case_3_input_package(extracted)

    assert package["site_consistency_block"]["same_site_basis"] is True
    assert package["site_consistency_block"]["load_source_case"] == "saigon18"
    assert package["site_consistency_block"]["market_source_case"] == "saigon18"
    branches = package["tariff"]["branches"]
    assert len(branches) == 2
    branch_names = [b["branch_name"] for b in branches]
    assert "22kv_two_part_evn" in branch_names
    assert "legacy_tou_one_component" in branch_names
    assert len(package["load"]["series_kwh"]) == 8760
    assert len(package["market"]["cfmp_vnd_per_kwh"]) == 8760
    assert (
        package["strike"]["base_discount_fraction"] == DEFAULT_STRIKE_DISCOUNT_FRACTION
    )
    assert len(package["strike"]["sensitivity_sweep_discounts"]) == 5


def test_input_package_scaling_hook_produces_correct_annual():
    extracted = _load_extracted()

    target = 150_000_000.0
    package = build_dppa_case_3_input_package(extracted, target_annual_kwh=target)

    assert package["load"]["scaled"] is True
    assert package["load"]["scale_target_annual_kwh"] == target
    assert abs(package["load"]["annual_kwh"] - target) < 1.0


def test_input_package_unscaled_preserves_original_annual():
    extracted = _load_extracted()

    package = build_dppa_case_3_input_package(extracted)

    assert package["load"]["scaled"] is False
    original_annual = sum(load_saigon18_load_series(extracted))
    assert abs(package["load"]["annual_kwh"] - original_annual) < 1.0
