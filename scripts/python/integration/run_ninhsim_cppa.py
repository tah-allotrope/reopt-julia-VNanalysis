"""
Run the Ninhsim bundled-CPPA workflow end to end.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PYTHON = sys.executable

EXTRACTED_PATH = "data/interim/ninhsim/ninhsim_extracted_inputs.json"
SCENARIO_A = (
    "scenarios/case_studies/ninhsim/2026-04-01_ninhsim_scenario-a_baseline-evn.json"
)
SCENARIO_B = (
    "scenarios/case_studies/ninhsim/2026-04-01_ninhsim_scenario-b_optimized-cppa.json"
)
RESULT_B = "artifacts/results/ninhsim/2026-04-01_ninhsim_scenario-b_optimized-cppa_reopt-results.json"
REPORT_B = "artifacts/reports/ninhsim/2026-04-01_ninhsim-cppa-analysis.json"


def run_command(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Ninhsim CPPA workflow")
    parser.add_argument(
        "--no-solve",
        action="store_true",
        help="Validate the optimized scenario without running the solver",
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
            "all",
        ]
    )

    julia_cmd = [
        "julia",
        f"--project={REPO_ROOT / 'legacy' / 'julia'}",
        "--compile=min",
        "legacy/julia/scripts/run_vietnam_scenario.jl",
        "--scenario",
        SCENARIO_B,
    ]
    if args.no_solve:
        julia_cmd.append("--no-solve")
    run_command(julia_cmd)

    if not args.no_solve:
        run_command(
            [
                PYTHON,
                "scripts/python/integration/analyze_ninhsim_cppa.py",
                "--reopt",
                RESULT_B,
                "--extracted",
                EXTRACTED_PATH,
                "--output",
                REPORT_B,
            ]
        )


if __name__ == "__main__":
    main()
