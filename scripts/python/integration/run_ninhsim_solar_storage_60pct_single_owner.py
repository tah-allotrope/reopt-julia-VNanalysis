"""Run the Ninhsim 60% solar-storage Single Owner PySAM workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reopt_pysam_vn.integration.bridge import (
    build_ninhsim_solar_storage_single_owner_inputs,
)
from reopt_pysam_vn.pysam.single_owner import run_single_owner_model

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_REOPT = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "ninhsim"
    / "2026-04-08_ninhsim_solar-storage_60pct_reopt-results.json"
)
DEFAULT_SCENARIO = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "ninhsim"
    / "2026-04-08_ninhsim_solar-storage_60pct.json"
)
DEFAULT_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "ninhsim" / "ninhsim_extracted_inputs.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-08_ninhsim_solar-storage_60pct_single-owner.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Ninhsim 60% solar-storage Single Owner PySAM workflow"
    )
    parser.add_argument("--reopt", type=Path, default=DEFAULT_REOPT)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    inputs = build_ninhsim_solar_storage_single_owner_inputs(
        reopt_results=_load_json(args.reopt),
        scenario=_load_json(args.scenario),
        extracted=_load_json(args.extracted),
    )
    results = run_single_owner_model(inputs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Ninhsim 60% Single Owner artifact written to: {args.output}")


if __name__ == "__main__":
    main()
