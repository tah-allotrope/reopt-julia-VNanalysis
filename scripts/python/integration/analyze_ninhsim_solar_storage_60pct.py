"""Analyze Ninhsim solar-plus-storage results for the 60% DPPA study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.ninhsim_solar_storage_60pct import (
    build_combined_decision_artifact,
    build_ninhsim_60pct_analysis,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Ninhsim solar-plus-storage REopt results for the 60% DPPA workflow"
    )
    parser.add_argument("--reopt", type=Path, required=True)
    parser.add_argument(
        "--scenario",
        type=Path,
        default=REPO_ROOT
        / "scenarios"
        / "case_studies"
        / "ninhsim"
        / "2026-04-08_ninhsim_solar-storage_60pct.json",
    )
    parser.add_argument(
        "--extracted",
        type=Path,
        default=REPO_ROOT
        / "data"
        / "interim"
        / "ninhsim"
        / "ninhsim_extracted_inputs.json",
    )
    parser.add_argument(
        "--analysis-output",
        type=Path,
        default=REPO_ROOT
        / "artifacts"
        / "reports"
        / "ninhsim"
        / "2026-04-08_ninhsim_solar-storage_60pct_analysis.json",
    )
    parser.add_argument(
        "--combined-output",
        type=Path,
        default=None,
        help="Optional combined-decision output path when a PySAM artifact is also supplied",
    )
    parser.add_argument(
        "--pysam",
        type=Path,
        default=None,
        help="Optional PySAM Single Owner artifact to combine with the REopt analysis",
    )
    args = parser.parse_args()

    results = _load_json(args.reopt)
    scenario = _load_json(args.scenario)
    extracted = _load_json(args.extracted)
    analysis = build_ninhsim_60pct_analysis(results, extracted, scenario)

    args.analysis_output.parent.mkdir(parents=True, exist_ok=True)
    args.analysis_output.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"Ninhsim 60% analysis written to: {args.analysis_output}")
    print(
        "  Achieved coverage     : "
        f"{analysis['coverage_summary']['achieved_delivered_fraction_of_load'] * 100.0:.2f}%"
    )
    print(
        "  Fixed strike          : "
        f"{analysis['fixed_strike']['year_one_strike_vnd_per_kwh']:.2f} VND/kWh"
    )

    if args.pysam is not None:
        combined_path = args.combined_output or (
            REPO_ROOT
            / "artifacts"
            / "reports"
            / "ninhsim"
            / "2026-04-08_ninhsim_solar-storage_60pct_combined-decision.json"
        )
        pysam_results = _load_json(args.pysam)
        combined = build_combined_decision_artifact(analysis, pysam_results)
        combined_path.parent.mkdir(parents=True, exist_ok=True)
        combined_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")
        print(f"Combined decision artifact written to: {combined_path}")


if __name__ == "__main__":
    main()
