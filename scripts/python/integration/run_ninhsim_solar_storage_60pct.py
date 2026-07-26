"""Run the Ninhsim solar-storage 60% workflow end to end."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PYTHON = sys.executable
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.ninhsim_solar_storage_60pct import (  # noqa: E402
    build_target_fraction_candidates,
)

EXTRACTED_PATH = "data/interim/ninhsim/ninhsim_extracted_inputs.json"
SCENARIO_C = (
    "scenarios/case_studies/ninhsim/2026-04-08_ninhsim_solar-storage_60pct.json"
)
RESULT_C = "artifacts/results/ninhsim/2026-04-08_ninhsim_solar-storage_60pct_reopt-results.json"
ANALYSIS_C = (
    "artifacts/reports/ninhsim/2026-04-08_ninhsim_solar-storage_60pct_analysis.json"
)
PYSAM_C = (
    "artifacts/reports/ninhsim/2026-04-08_ninhsim_solar-storage_60pct_single-owner.json"
)
COMBINED_C = "artifacts/reports/ninhsim/2026-04-08_ninhsim_solar-storage_60pct_combined-decision.json"


def run_command(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def _load_json(relative_path: str) -> dict:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def _save_json(relative_path: str, payload: dict) -> None:
    path = REPO_ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _solve_threshold_search() -> float:
    scenario_path = REPO_ROOT / SCENARIO_C
    _extracted = _load_json(EXTRACTED_PATH)
    original_scenario = _load_json(SCENARIO_C)
    requested = float(
        original_scenario.get("_meta", {}).get(
            "requested_renewable_delivered_fraction_of_load", 0.60
        )
    )
    candidates = build_target_fraction_candidates(requested)

    for candidate in candidates:
        scenario = json.loads(json.dumps(original_scenario))
        scenario["Site"]["renewable_electricity_min_fraction"] = float(candidate)
        scenario.setdefault("_meta", {})[
            "enforced_renewable_delivered_fraction_of_load"
        ] = float(candidate)
        scenario_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
        run_command(
            [
                "julia",
                "--project",
                "--compile=min",
                "scripts/julia/run_vietnam_scenario.jl",
                "--scenario",
                SCENARIO_C,
            ]
        )
        results = _load_json(RESULT_C)
        if results.get("status") == "optimal":
            return float(candidate)

    raise RuntimeError(
        "Ninhsim solar-storage workflow could not find a feasible threshold in the configured candidate band."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Ninhsim solar-storage 60% DPPA workflow"
    )
    parser.add_argument(
        "--no-solve",
        action="store_true",
        help="Validate the scenario without running the REopt solve or downstream analysis",
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
            "c",
        ]
    )

    julia_cmd = [
        "julia",
        "--project",
        "--compile=min",
        "scripts/julia/run_vietnam_scenario.jl",
        "--scenario",
        SCENARIO_C,
    ]
    if args.no_solve:
        julia_cmd.append("--no-solve")
    if args.no_solve:
        run_command(julia_cmd)
        return

    enforced_target_fraction = _solve_threshold_search()
    scenario_payload = _load_json(SCENARIO_C)
    scenario_payload.setdefault("_meta", {})[
        "enforced_renewable_delivered_fraction_of_load"
    ] = enforced_target_fraction
    _save_json(SCENARIO_C, scenario_payload)

    run_command(
        [
            PYTHON,
            "scripts/python/integration/analyze_ninhsim_solar_storage_60pct.py",
            "--reopt",
            RESULT_C,
            "--scenario",
            SCENARIO_C,
            "--extracted",
            EXTRACTED_PATH,
            "--analysis-output",
            ANALYSIS_C,
        ]
    )
    run_command(
        [
            PYTHON,
            "scripts/python/integration/run_ninhsim_solar_storage_60pct_single_owner.py",
            "--reopt",
            RESULT_C,
            "--scenario",
            SCENARIO_C,
            "--extracted",
            EXTRACTED_PATH,
            "--output",
            PYSAM_C,
        ]
    )
    run_command(
        [
            PYTHON,
            "scripts/python/integration/analyze_ninhsim_solar_storage_60pct.py",
            "--reopt",
            RESULT_C,
            "--scenario",
            SCENARIO_C,
            "--extracted",
            EXTRACTED_PATH,
            "--analysis-output",
            ANALYSIS_C,
            "--pysam",
            PYSAM_C,
            "--combined-output",
            COMBINED_C,
        ]
    )


if __name__ == "__main__":
    main()
