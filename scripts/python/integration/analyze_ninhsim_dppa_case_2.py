"""Analyze Ninhsim DPPA Case 2 REopt results into physical and buyer-settlement artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_2 import (
    build_dppa_case_2_buyer_benchmark,
    build_dppa_case_2_physical_summary,
    build_dppa_case_2_settlement_inputs,
    run_dppa_case_2_buyer_settlement,
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
DEFAULT_PHYSICAL = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_physical-summary.json"
)
DEFAULT_SETTLEMENT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_buyer-settlement.json"
)
DEFAULT_BENCHMARK = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_buyer-benchmark.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Ninhsim DPPA Case 2 REopt results into physical and buyer-settlement artifacts"
    )
    parser.add_argument("--reopt", type=Path, default=DEFAULT_REOPT)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--physical-output", type=Path, default=DEFAULT_PHYSICAL)
    parser.add_argument("--settlement-output", type=Path, default=DEFAULT_SETTLEMENT)
    parser.add_argument("--benchmark-output", type=Path, default=DEFAULT_BENCHMARK)
    args = parser.parse_args()

    results = _load_json(args.reopt)
    scenario = _load_json(args.scenario)
    extracted = _load_json(args.extracted)

    physical = build_dppa_case_2_physical_summary(results, extracted, scenario)
    settlement_inputs = build_dppa_case_2_settlement_inputs(
        results, extracted, scenario
    )
    settlement = run_dppa_case_2_buyer_settlement(settlement_inputs)
    benchmark = build_dppa_case_2_buyer_benchmark(physical, settlement)

    _write_json(args.physical_output, physical)
    _write_json(args.settlement_output, settlement)
    _write_json(args.benchmark_output, benchmark)

    print(f"DPPA Case 2 physical summary written to: {args.physical_output}")
    print(f"DPPA Case 2 buyer settlement written to: {args.settlement_output}")
    print(f"DPPA Case 2 buyer benchmark written to: {args.benchmark_output}")
    print(
        "  Matched fraction      : "
        f"{physical['energy_summary']['matched_fraction_of_load'] * 100.0:.2f}%"
    )
    print(
        "  Buyer blended cost    : "
        f"{settlement['summary']['buyer_blended_cost_vnd_per_kwh']:.2f} VND/kWh"
    )


if __name__ == "__main__":
    main()
