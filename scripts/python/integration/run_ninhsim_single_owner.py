"""Run the Phase 4 Ninhsim Single Owner PySAM finance workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reopt_pysam_vn.integration.bridge import build_ninhsim_single_owner_inputs
from reopt_pysam_vn.pysam.single_owner import run_single_owner_model

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_REOPT = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "ninhsim"
    / "2026-04-01_ninhsim_scenario-b_optimized-cppa_reopt-results.json"
)
DEFAULT_SCENARIO = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "ninhsim"
    / "2026-04-01_ninhsim_scenario-b_optimized-cppa.json"
)
DEFAULT_MEMO = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-02_ninhsim-commercial-candidate-memo.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-04_ninhsim-single-owner-finance.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Ninhsim Phase 4 Single Owner PySAM workflow"
    )
    parser.add_argument("--reopt", type=Path, default=DEFAULT_REOPT)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--memo", type=Path, default=DEFAULT_MEMO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    inputs = build_ninhsim_single_owner_inputs(
        reopt_results=_load_json(args.reopt),
        scenario=_load_json(args.scenario),
        commercial_memo=_load_json(args.memo),
    )
    results = run_single_owner_model(inputs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Phase 4 Single Owner artifact written to: {args.output}")


if __name__ == "__main__":
    main()
