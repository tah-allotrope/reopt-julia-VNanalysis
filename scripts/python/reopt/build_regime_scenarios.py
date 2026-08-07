"""Materialize resolved Vietnam regime scenarios from one base input."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.regime_runner import build_regime_scenarios


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize resolved regime scenarios.")
    parser.add_argument("--scenario", required=True, help="Base scenario or template JSON path")
    parser.add_argument("--regimes", nargs="+", required=True, help="Named regime IDs to materialize")
    parser.add_argument(
        "--assumption-sets",
        nargs="+",
        default=["base"],
        help="Named assumption sets to combine with the regimes",
    )
    parser.add_argument(
        "--generated-root",
        default=str(REPO_ROOT / "scenarios" / "generated" / "regime_engine"),
        help="Destination root for generated resolved scenarios",
    )
    parser.add_argument(
        "--result-store-root",
        default=str(REPO_ROOT / "artifacts" / "results" / "regime_engine"),
        help="Destination root for deterministic run artifacts",
    )
    args = parser.parse_args()

    outputs = build_regime_scenarios(
        scenario_path=Path(args.scenario),
        regime_ids=args.regimes,
        assumption_set_ids=args.assumption_sets,
        generated_root=Path(args.generated_root),
        result_store_root=Path(args.result_store_root),
    )
    for output in outputs:
        print(f"materialized {output['scenario_hash']} -> {output['generated_scenario_path']}")


if __name__ == "__main__":
    main()
