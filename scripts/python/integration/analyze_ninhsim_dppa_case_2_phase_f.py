"""Analyze Ninhsim DPPA Case 2 Phase F with market replacement and PySAM validation."""

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
    build_dppa_case_2_buyer_benchmark,
    build_dppa_case_2_developer_screening,
    build_dppa_case_2_market_reference_artifact,
    build_dppa_case_2_physical_summary,
    build_dppa_case_2_reopt_pysam_comparison,
    build_dppa_case_2_settlement_inputs,
    run_dppa_case_2_buyer_settlement,
)
from reopt_pysam_vn.pysam.single_owner import run_single_owner_model

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
DEFAULT_MARKET_SOURCE = (
    REPO_ROOT
    / "data"
    / "interim"
    / "saigon18"
    / "2026-03-20_saigon18_extracted_inputs.json"
)
DEFAULT_PHASE_E = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_strike-sensitivity.json"
)
DEFAULT_MARKET_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_market-reference.json"
)
DEFAULT_SETTLEMENT_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_buyer-settlement-actual-market.json"
)
DEFAULT_BENCHMARK_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_buyer-benchmark-actual-market.json"
)
DEFAULT_PYSAM_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_pysam-results.json"
)
DEFAULT_COMPARISON_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_reopt-pysam-comparison.json"
)
DEFAULT_SCREENING_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_developer-screening.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Ninhsim DPPA Case 2 Phase F with market replacement and PySAM validation"
    )
    parser.add_argument("--reopt", type=Path, default=DEFAULT_REOPT)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--market-source", type=Path, default=DEFAULT_MARKET_SOURCE)
    parser.add_argument("--phase-e", type=Path, default=DEFAULT_PHASE_E)
    parser.add_argument("--market-output", type=Path, default=DEFAULT_MARKET_OUTPUT)
    parser.add_argument(
        "--settlement-output", type=Path, default=DEFAULT_SETTLEMENT_OUTPUT
    )
    parser.add_argument(
        "--benchmark-output", type=Path, default=DEFAULT_BENCHMARK_OUTPUT
    )
    parser.add_argument("--pysam-output", type=Path, default=DEFAULT_PYSAM_OUTPUT)
    parser.add_argument(
        "--comparison-output", type=Path, default=DEFAULT_COMPARISON_OUTPUT
    )
    parser.add_argument(
        "--screening-output", type=Path, default=DEFAULT_SCREENING_OUTPUT
    )
    args = parser.parse_args()

    results = _load_json(args.reopt)
    scenario = _load_json(args.scenario)
    extracted = _load_json(args.extracted)
    market_source = _load_json(args.market_source)
    phase_e = _load_json(args.phase_e)

    physical = build_dppa_case_2_physical_summary(results, extracted, scenario)
    market_reference = build_dppa_case_2_market_reference_artifact(
        market_source,
        source_path=str(args.market_source.relative_to(REPO_ROOT)),
        source_case="saigon18",
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
    pysam_results = run_single_owner_model(developer_inputs)
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
        phase_e_reference=phase_e.get("negotiation_summary", {}),
    )

    _write_json(args.market_output, market_reference)
    _write_json(args.settlement_output, settlement)
    _write_json(args.benchmark_output, benchmark)
    _write_json(args.pysam_output, pysam_results)
    _write_json(args.comparison_output, comparison)
    _write_json(args.screening_output, screening)

    print(f"DPPA Case 2 market reference written to: {args.market_output}")
    print(f"DPPA Case 2 actual-market settlement written to: {args.settlement_output}")
    print(f"DPPA Case 2 actual-market benchmark written to: {args.benchmark_output}")
    print(f"DPPA Case 2 PySAM results written to: {args.pysam_output}")
    print(f"DPPA Case 2 REopt/PySAM comparison written to: {args.comparison_output}")
    print(f"DPPA Case 2 developer screening written to: {args.screening_output}")
    print(f"  Combined pass        : {screening['decision']['combined_pass']}")
    print(f"  Recommended position : {screening['decision']['recommended_position']}")


if __name__ == "__main__":
    main()
