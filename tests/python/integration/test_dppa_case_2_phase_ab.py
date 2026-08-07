"""Regression tests for Ninhsim DPPA Case 2 Phase A/B design artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_2 import (
    DEFAULT_DPPA_ADDER_VND_PER_KWH,
    DEFAULT_KPP_FACTOR,
    DEFAULT_STRIKE_DISCOUNT_FRACTION,
    build_dppa_case_2_assumptions_register,
    build_dppa_case_2_edge_case_matrix,
    build_dppa_case_2_phase_a_definition,
    build_dppa_case_2_settlement_design,
    build_dppa_case_2_settlement_schema,
)

EXTRACTED_PATH = (
    REPO_ROOT / "data" / "interim" / "ninhsim" / "ninhsim_extracted_inputs.json"
)


def _load_extracted() -> dict:
    return json.loads(EXTRACTED_PATH.read_text(encoding="utf-8"))


def test_phase_a_definition_freezes_synthetic_case_and_weighted_evn_strike_anchor():
    extracted = _load_extracted()

    definition = build_dppa_case_2_phase_a_definition(extracted)

    assert definition["case_identity"]["scenario_family"] == "DPPA Case 2"
    assert (
        definition["case_identity"]["contract_structure"] == "synthetic_financial_dppa"
    )
    assert (
        definition["strike_basis"]["strike_discount_fraction"]
        == DEFAULT_STRIKE_DISCOUNT_FRACTION
    )
    assert definition["strike_basis"]["year_one_strike_vnd_per_kwh"] == (
        extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"]
        * (1.0 - DEFAULT_STRIKE_DISCOUNT_FRACTION)
    )


def test_assumptions_register_captures_user_answers_for_phase_a_and_b():
    extracted = _load_extracted()

    assumptions = build_dppa_case_2_assumptions_register(extracted)

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
        assumptions["questions"]["pysam_scope"]["selected_answer"]
        == "full_buyer_plus_developer_workflow_in_one_pass"
    )


def test_settlement_design_and_schema_freeze_fixed_adder_kpp_and_actual_series_priority():
    extracted = _load_extracted()
    definition = build_dppa_case_2_phase_a_definition(extracted)
    assumptions = build_dppa_case_2_assumptions_register(extracted)

    design = build_dppa_case_2_settlement_design(definition, assumptions)
    schema = build_dppa_case_2_settlement_schema()

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


def test_edge_case_matrix_includes_bilateral_cfd_and_excess_exclusion_cases():
    matrix = build_dppa_case_2_edge_case_matrix()

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
        / "prepare_ninhsim_dppa_case_2_phase_ab.py"
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
    assert (
        output_dir / "2026-04-14_ninhsim_dppa-case-2_phase-a-definition.json"
    ).is_file()
    assert (
        output_dir / "2026-04-14_ninhsim_dppa-case-2_phase-a-assumptions-register.json"
    ).is_file()
    assert (
        output_dir / "2026-04-14_ninhsim_dppa-case-2_phase-b-settlement-design.json"
    ).is_file()
    assert (
        output_dir / "2026-04-14_ninhsim_dppa-case-2_phase-b-settlement-schema.json"
    ).is_file()
    assert (
        output_dir / "2026-04-14_ninhsim_dppa-case-2_phase-b-edge-case-matrix.json"
    ).is_file()
