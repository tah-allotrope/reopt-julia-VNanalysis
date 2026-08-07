"""Prepare Saigon18 DPPA Case 3 Phase A/B canonical design artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_3 import (
    build_dppa_case_3_assumptions_register,
    build_dppa_case_3_edge_case_matrix,
    build_dppa_case_3_gap_register,
    build_dppa_case_3_input_package,
    build_dppa_case_3_phase_a_definition,
    build_dppa_case_3_settlement_design,
    build_dppa_case_3_settlement_schema,
)

REPORT_DATE = "2026-04-20"
DEFAULT_EXTRACTED = (
    REPO_ROOT
    / "data"
    / "interim"
    / "saigon18"
    / "2026-03-20_saigon18_extracted_inputs.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "reports" / "saigon18"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare Saigon18 DPPA Case 3 Phase A/B canonical artifacts"
    )
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    extracted = _load_json(args.extracted)
    definition = build_dppa_case_3_phase_a_definition(extracted)
    assumptions = build_dppa_case_3_assumptions_register(extracted)
    gap_register = build_dppa_case_3_gap_register()
    design = build_dppa_case_3_settlement_design(definition, assumptions)
    schema = build_dppa_case_3_settlement_schema()
    edge_cases = build_dppa_case_3_edge_case_matrix()
    input_package = build_dppa_case_3_input_package(extracted)

    definition_path = (
        args.output_dir / f"{REPORT_DATE}_saigon18_dppa-case-3_phase-a-definition.json"
    )
    assumptions_path = (
        args.output_dir
        / f"{REPORT_DATE}_saigon18_dppa-case-3_phase-a-assumptions-register.json"
    )
    gap_register_path = (
        args.output_dir
        / f"{REPORT_DATE}_saigon18_dppa-case-3_phase-a-gap-register.json"
    )
    design_path = (
        args.output_dir
        / f"{REPORT_DATE}_saigon18_dppa-case-3_phase-b-settlement-design.json"
    )
    schema_path = (
        args.output_dir
        / f"{REPORT_DATE}_saigon18_dppa-case-3_phase-b-settlement-schema.json"
    )
    edge_cases_path = (
        args.output_dir
        / f"{REPORT_DATE}_saigon18_dppa-case-3_phase-b-edge-case-matrix.json"
    )
    input_package_path = (
        args.output_dir / f"{REPORT_DATE}_saigon18_dppa-case-3_input-package.json"
    )

    _write_json(definition_path, definition)
    _write_json(assumptions_path, assumptions)
    _write_json(gap_register_path, gap_register)
    _write_json(design_path, design)
    _write_json(schema_path, schema)
    _write_json(edge_cases_path, edge_cases)
    _write_json(input_package_path, input_package)

    print(f"Phase A definition written to: {definition_path}")
    print(f"Phase A assumptions register written to: {assumptions_path}")
    print(f"Phase A gap register written to: {gap_register_path}")
    print(f"Phase B settlement design written to: {design_path}")
    print(f"Phase B settlement schema written to: {schema_path}")
    print(f"Phase B edge-case matrix written to: {edge_cases_path}")
    print(f"Phase B input package written to: {input_package_path}")


if __name__ == "__main__":
    main()
