"""Run the Ninhsim DPPA Case 2 workflow through REopt and buyer-settlement analysis."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PYTHON = sys.executable

EXTRACTED_PATH = "data/interim/ninhsim/ninhsim_extracted_inputs.json"
SCENARIO_PATH = "scenarios/case_studies/ninhsim/2026-04-14_ninhsim_dppa-case-2.json"
REOPT_RESULT = (
    "artifacts/results/ninhsim/2026-04-14_ninhsim_dppa-case-2_reopt-results.json"
)
PHYSICAL_REPORT = (
    "artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_physical-summary.json"
)
SETTLEMENT_REPORT = (
    "artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_buyer-settlement.json"
)
BENCHMARK_REPORT = (
    "artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_buyer-benchmark.json"
)
PHASE_E_STRIKE_REPORT = (
    "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_strike-sensitivity.json"
)
PHASE_E_RISK_REPORT = (
    "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_contract-risk.json"
)
PHASE_F_MARKET_REPORT = (
    "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_market-reference.json"
)
PHASE_F_SETTLEMENT_REPORT = "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_buyer-settlement-actual-market.json"
PHASE_F_BENCHMARK_REPORT = "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_buyer-benchmark-actual-market.json"
PHASE_F_PYSAM_REPORT = (
    "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_pysam-results.json"
)
PHASE_F_COMPARISON_REPORT = "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_reopt-pysam-comparison.json"
PHASE_F_SCREENING_REPORT = (
    "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_developer-screening.json"
)


def run_command(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Ninhsim DPPA Case 2 REopt plus buyer-settlement workflow"
    )
    parser.add_argument(
        "--no-solve",
        action="store_true",
        help="Validate the REopt scenario without solving or running downstream analysis",
    )
    args = parser.parse_args()

    run_command(
        [
            PYTHON,
            "scripts/python/integration/build_ninhsim_extracted_inputs.py",
            "--output",
            EXTRACTED_PATH,
        ]
    )
    run_command(
        [
            PYTHON,
            "scripts/python/integration/build_ninhsim_reopt_input.py",
            "--extracted",
            EXTRACTED_PATH,
            "--scenarios",
            "dppa_case_2",
        ]
    )

    julia_command = [
        "julia",
        f"--project={REPO_ROOT / 'legacy' / 'julia'}",
        "--compile=min",
        "legacy/julia/scripts/run_vietnam_scenario.jl",
        "--scenario",
        SCENARIO_PATH,
    ]
    if args.no_solve:
        julia_command.append("--no-solve")
        run_command(julia_command)
        return

    run_command(julia_command)
    run_command(
        [
            PYTHON,
            "scripts/python/integration/analyze_ninhsim_dppa_case_2.py",
            "--reopt",
            REOPT_RESULT,
            "--scenario",
            SCENARIO_PATH,
            "--extracted",
            EXTRACTED_PATH,
            "--physical-output",
            PHYSICAL_REPORT,
            "--settlement-output",
            SETTLEMENT_REPORT,
            "--benchmark-output",
            BENCHMARK_REPORT,
        ]
    )
    run_command(
        [
            PYTHON,
            "scripts/python/integration/analyze_ninhsim_dppa_case_2_phase_e.py",
            "--reopt",
            REOPT_RESULT,
            "--scenario",
            SCENARIO_PATH,
            "--extracted",
            EXTRACTED_PATH,
            "--strike-output",
            PHASE_E_STRIKE_REPORT,
            "--risk-output",
            PHASE_E_RISK_REPORT,
        ]
    )
    run_command(
        [
            PYTHON,
            "scripts/python/integration/analyze_ninhsim_dppa_case_2_phase_f.py",
            "--reopt",
            REOPT_RESULT,
            "--scenario",
            SCENARIO_PATH,
            "--extracted",
            EXTRACTED_PATH,
            "--market-output",
            PHASE_F_MARKET_REPORT,
            "--settlement-output",
            PHASE_F_SETTLEMENT_REPORT,
            "--benchmark-output",
            PHASE_F_BENCHMARK_REPORT,
            "--pysam-output",
            PHASE_F_PYSAM_REPORT,
            "--comparison-output",
            PHASE_F_COMPARISON_REPORT,
            "--screening-output",
            PHASE_F_SCREENING_REPORT,
        ]
    )


if __name__ == "__main__":
    main()
