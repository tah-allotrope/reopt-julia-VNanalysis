"""Run the Ninhsim DPPA Case 1 workflow end to end."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PYTHON = sys.executable

EXTRACTED_PATH = "data/interim/ninhsim/ninhsim_extracted_inputs.json"
SCENARIO_PATH = "scenarios/case_studies/ninhsim/2026-04-09_ninhsim_dppa-case-1.json"
REOPT_RESULT = (
    "artifacts/results/ninhsim/2026-04-09_ninhsim_dppa-case-1_reopt-results.json"
)
REOPT_SUMMARY = (
    "artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_reopt-summary.json"
)
PYSAM_RESULT = (
    "artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_pysam-results.json"
)
COMPARISON = "artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_comparison.json"
COMBINED = (
    "artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_combined-decision.json"
)


def run_command(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Ninhsim DPPA Case 1 REopt plus fuller PySAM workflow"
    )
    parser.add_argument(
        "--no-solve",
        action="store_true",
        help="Validate the REopt scenario without solving or running downstream analysis",
    )
    parser.add_argument(
        "--force-download-resource",
        action="store_true",
        help="Force a fresh solar resource fetch for the PySAM stage",
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
            "dppa_case_1",
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
            "scripts/python/integration/analyze_ninhsim_dppa_case_1.py",
            "--reopt",
            REOPT_RESULT,
            "--scenario",
            SCENARIO_PATH,
            "--extracted",
            EXTRACTED_PATH,
            "--summary-output",
            REOPT_SUMMARY,
        ]
    )

    pysam_command = [
        PYTHON,
        "scripts/python/integration/run_ninhsim_dppa_case_1_pvwatts.py",
        "--reopt",
        REOPT_RESULT,
        "--scenario",
        SCENARIO_PATH,
        "--extracted",
        EXTRACTED_PATH,
        "--output",
        PYSAM_RESULT,
    ]
    if args.force_download_resource:
        pysam_command.append("--force-download-resource")
    run_command(pysam_command)

    run_command(
        [
            PYTHON,
            "scripts/python/integration/analyze_ninhsim_dppa_case_1.py",
            "--reopt",
            REOPT_RESULT,
            "--scenario",
            SCENARIO_PATH,
            "--extracted",
            EXTRACTED_PATH,
            "--summary-output",
            REOPT_SUMMARY,
            "--pysam",
            PYSAM_RESULT,
            "--comparison-output",
            COMPARISON,
            "--combined-output",
            COMBINED,
        ]
    )


if __name__ == "__main__":
    main()
