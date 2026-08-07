"""Analyze Ninhsim DPPA Case 2 Phase E sensitivities into canonical artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.bridge import (
    build_dppa_case_2_single_owner_inputs,
)
from reopt_pysam_vn.integration.dppa_case_2 import (
    build_dppa_case_2_contract_risk_sensitivity,
    build_dppa_case_2_physical_summary,
    build_dppa_case_2_settlement_inputs,
    build_dppa_case_2_strike_sensitivity,
)

DEFAULT_REOPT = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_reopt-results.json"
)
DEFAULT_SCENARIO = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2.json"
)
DEFAULT_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "ninhsim" / "ninhsim_extracted_inputs.json"
)
DEFAULT_STRIKE_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_strike-sensitivity.json"
)
DEFAULT_RISK_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_contract-risk.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Ninhsim DPPA Case 2 Phase E strike and contract sensitivities"
    )
    parser.add_argument("--reopt", type=Path, default=DEFAULT_REOPT)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--strike-output", type=Path, default=DEFAULT_STRIKE_OUTPUT)
    parser.add_argument("--risk-output", type=Path, default=DEFAULT_RISK_OUTPUT)
    args = parser.parse_args()

    results = _load_json(args.reopt)
    scenario = _load_json(args.scenario)
    extracted = _load_json(args.extracted)

    physical = build_dppa_case_2_physical_summary(results, extracted, scenario)
    settlement_inputs = build_dppa_case_2_settlement_inputs(
        results, extracted, scenario
    )
    developer_inputs = build_dppa_case_2_single_owner_inputs(
        results,
        scenario,
        settlement_inputs,
    )

    strike_sensitivity = build_dppa_case_2_strike_sensitivity(
        settlement_inputs,
        physical,
        strike_discount_fractions=(0.15, 0.10, 0.05, 0.0),
        developer_base_inputs=developer_inputs,
    )
    contract_risk = build_dppa_case_2_contract_risk_sensitivity(
        settlement_inputs,
        physical,
        dppa_adder_multipliers=(0.75, 1.0, 1.25),
        kpp_multipliers=(0.98, 1.0, 1.02),
        excess_generation_treatments=(
            "excluded_from_buyer_settlement",
            "cfd_on_excess_generation",
        ),
    )

    _write_json(args.strike_output, strike_sensitivity)
    _write_json(args.risk_output, contract_risk)

    print(f"DPPA Case 2 strike sensitivity written to: {args.strike_output}")
    print(f"DPPA Case 2 contract risk written to: {args.risk_output}")
    print(
        "  Overlap found        : "
        f"{strike_sensitivity['negotiation_summary']['overlap_found']}"
    )
    print(
        "  Recommended position : "
        f"{strike_sensitivity['negotiation_summary']['recommended_position']}"
    )


if __name__ == "__main__":
    main()
