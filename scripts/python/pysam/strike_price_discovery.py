"""Run the Phase 5 Ninhsim strike-price discovery workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reopt_pysam_vn.integration.bridge import build_ninhsim_single_owner_inputs
from reopt_pysam_vn.integration.strike_search import build_strike_price_summary

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_PHASE4 = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-04_ninhsim-single-owner-finance.json"
)
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
    / "2026-04-04_ninhsim-strike-price.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Ninhsim Phase 5 PySAM strike-price discovery workflow"
    )
    parser.add_argument("--phase4", type=Path, default=DEFAULT_PHASE4)
    parser.add_argument("--reopt", type=Path, default=DEFAULT_REOPT)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--memo", type=Path, default=DEFAULT_MEMO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-irr", type=float, default=0.10)
    parser.add_argument("--min-strike", type=float, default=5.0)
    parser.add_argument("--max-strike", type=float, default=15.0)
    parser.add_argument("--step", type=float, default=0.5)
    args = parser.parse_args()

    phase4_results = _load_json(args.phase4)
    base_inputs = build_ninhsim_single_owner_inputs(
        reopt_results=_load_json(args.reopt),
        scenario=_load_json(args.scenario),
        commercial_memo=_load_json(args.memo),
    )
    results = build_strike_price_summary(
        phase4_results=phase4_results,
        base_inputs=base_inputs,
        target_irr_fraction=args.target_irr,
        min_strike_cents_per_kwh=args.min_strike,
        max_strike_cents_per_kwh=args.max_strike,
        step_cents_per_kwh=args.step,
        phase4_artifact_path=str(args.phase4.relative_to(REPO_ROOT)).replace("\\", "/"),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Phase 5 strike-price artifact written to: {args.output}")


if __name__ == "__main__":
    main()
