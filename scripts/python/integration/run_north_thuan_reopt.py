"""
Build and run the North Thuan REopt scenarios through the existing Julia runner.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python"))

from build_north_thuan_load_profile import main as build_inputs_main
from build_north_thuan_reopt_input import main as build_scenarios_main

SCENARIO_PATHS = {
    "a": REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "north_thuan"
    / "north_thuan_scenario_a.json",
    "b": REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "north_thuan"
    / "north_thuan_scenario_b.json",
    "c": REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "north_thuan"
    / "north_thuan_scenario_c.json",
}


def _run_builder(entrypoint, argv: list[str]) -> None:
    old_argv = sys.argv[:]
    try:
        sys.argv = argv
        entrypoint()
    finally:
        sys.argv = old_argv


def run_julia_scenario(scenario_path: Path, no_solve: bool) -> None:
    command = [
        "julia",
        f"--project={REPO_ROOT / 'legacy' / 'julia'}",
        "--compile=min",
        "legacy/julia/scripts/run_vietnam_scenario.jl",
        "--scenario",
        str(scenario_path),
    ]
    if no_solve:
        command.append("--no-solve")

    env = os.environ.copy()
    env["JULIA_PKG_PRECOMPILE_AUTO"] = "0"
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and run the North Thuan REopt scenarios"
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=["a", "b", "c", "all"],
        default=["all"],
        help="Which scenarios to run",
    )
    parser.add_argument(
        "--no-solve",
        action="store_true",
        help="Validate Scenario() only and skip the Julia solver",
    )
    args = parser.parse_args()

    selected = {"a", "b", "c"} if "all" in args.scenarios else set(args.scenarios)

    _run_builder(
        build_inputs_main,
        [
            "build_north_thuan_load_profile.py",
            "--output",
            "data/interim/north_thuan/north_thuan_extracted_inputs.json",
        ],
    )
    _run_builder(
        build_scenarios_main,
        [
            "build_north_thuan_reopt_input.py",
            "--extracted",
            "data/interim/north_thuan/north_thuan_extracted_inputs.json",
            "--outdir",
            "scenarios/case_studies/north_thuan",
            "--scenarios",
            *sorted(selected),
        ],
    )

    for key in sorted(selected):
        print(f"\nRunning North Thuan Scenario {key.upper()}...")
        run_julia_scenario(SCENARIO_PATHS[key], no_solve=args.no_solve)


if __name__ == "__main__":
    main()
