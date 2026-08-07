"""Assemble Ninhsim DPPA Case 2 Phase G combined decision artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_2 import (
    build_dppa_case_2_combined_decision_artifact,
    build_dppa_case_2_final_summary_artifact,
)

DEFAULT_PHYSICAL = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_physical-summary.json"
)
DEFAULT_BENCHMARK = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_buyer-benchmark-actual-market.json"
)
DEFAULT_STRIKE = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_strike-sensitivity.json"
)
DEFAULT_RISK = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_contract-risk.json"
)
DEFAULT_SCREENING = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_developer-screening.json"
)
DEFAULT_COMBINED = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_combined-decision.json"
)
DEFAULT_FINAL = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_final-summary.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble Ninhsim DPPA Case 2 Phase G combined decision artifacts"
    )
    parser.add_argument("--physical", type=Path, default=DEFAULT_PHYSICAL)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--strike", type=Path, default=DEFAULT_STRIKE)
    parser.add_argument("--risk", type=Path, default=DEFAULT_RISK)
    parser.add_argument("--screening", type=Path, default=DEFAULT_SCREENING)
    parser.add_argument("--combined-output", type=Path, default=DEFAULT_COMBINED)
    parser.add_argument("--final-output", type=Path, default=DEFAULT_FINAL)
    args = parser.parse_args()

    physical = _load_json(args.physical)
    _benchmark = _load_json(args.benchmark)
    strike = _load_json(args.strike)
    risk = _load_json(args.risk)
    screening = _load_json(args.screening)

    combined = build_dppa_case_2_combined_decision_artifact(
        physical_summary=physical,
        strike_sensitivity=strike,
        contract_risk=risk,
        developer_screening=screening,
    )
    final_summary = build_dppa_case_2_final_summary_artifact(
        combined_decision=combined,
        phase_artifact_paths={
            "phase_c": str(args.physical.relative_to(REPO_ROOT)),
            "phase_d": str(args.benchmark.relative_to(REPO_ROOT)),
            "phase_e": str(args.strike.relative_to(REPO_ROOT)),
            "phase_f": str(args.screening.relative_to(REPO_ROOT)),
            "phase_g": str(args.combined_output.relative_to(REPO_ROOT)),
        },
    )

    _write_json(args.combined_output, combined)
    _write_json(args.final_output, final_summary)

    print(f"DPPA Case 2 combined decision written to: {args.combined_output}")
    print(f"DPPA Case 2 final summary written to: {args.final_output}")
    print(f"  Recommended position : {combined['decision']['recommended_position']}")
    print(f"  Decision class       : {combined['decision']['decision_class']}")


if __name__ == "__main__":
    main()
