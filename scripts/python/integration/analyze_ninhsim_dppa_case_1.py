"""Analyze Ninhsim DPPA Case 1 REopt and fuller PySAM results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_1 import (
    build_dppa_case_1_combined_decision,
    build_dppa_case_1_comparison,
    build_dppa_case_1_reopt_summary,
)

DEFAULT_REOPT = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1_reopt-results.json"
)
DEFAULT_SCENARIO = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1.json"
)
DEFAULT_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "ninhsim" / "ninhsim_extracted_inputs.json"
)
DEFAULT_SUMMARY = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1_reopt-summary.json"
)
DEFAULT_COMPARISON = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1_comparison.json"
)
DEFAULT_COMBINED = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1_combined-decision.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Ninhsim DPPA Case 1 REopt results and optional fuller PySAM results"
    )
    parser.add_argument("--reopt", type=Path, default=DEFAULT_REOPT)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--pysam", type=Path, default=None)
    parser.add_argument("--comparison-output", type=Path, default=DEFAULT_COMPARISON)
    parser.add_argument("--combined-output", type=Path, default=DEFAULT_COMBINED)
    args = parser.parse_args()

    results = _load_json(args.reopt)
    scenario = _load_json(args.scenario)
    extracted = _load_json(args.extracted)

    summary = build_dppa_case_1_reopt_summary(results, extracted, scenario)
    _write_json(args.summary_output, summary)
    print(f"DPPA Case 1 REopt summary written to: {args.summary_output}")
    print(
        "  Export fraction       : "
        f"{summary['energy_summary']['export_fraction_of_generation'] * 100.0:.3f}%"
    )
    print(
        "  Private-wire strike   : "
        f"{summary['private_wire_strike']['year_one_private_wire_strike_vnd_per_kwh']:.2f} VND/kWh"
    )

    if args.pysam is None:
        return

    pysam_results = _load_json(args.pysam)
    comparison = build_dppa_case_1_comparison(summary, pysam_results)
    combined = build_dppa_case_1_combined_decision(summary, pysam_results, comparison)

    _write_json(args.comparison_output, comparison)
    _write_json(args.combined_output, combined)
    print(f"DPPA Case 1 comparison written to: {args.comparison_output}")
    print(f"DPPA Case 1 combined decision written to: {args.combined_output}")


if __name__ == "__main__":
    main()
