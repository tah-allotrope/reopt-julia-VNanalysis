"""Run a deterministic regime matrix across named regimes and assumption sets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.regime_runner import build_regime_matrix


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Vietnam regulatory regime matrix.")
    parser.add_argument("--scenario", required=True, help="Base scenario or template JSON path")
    parser.add_argument("--regimes", nargs="+", required=True, help="Named regime IDs to run")
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
    parser.add_argument("--solve", action="store_true", help="Run the Julia solve path instead of no-solve validation")
    parser.add_argument("--force", action="store_true", help="Ignore successful cached manifests and rerun the matrix")
    args = parser.parse_args()

    runs = build_regime_matrix(
        scenario_path=Path(args.scenario),
        regime_ids=args.regimes,
        assumption_set_ids=args.assumption_sets,
        generated_root=Path(args.generated_root),
        result_store_root=Path(args.result_store_root),
        solve=args.solve,
        force=args.force,
    )
    for run in runs:
        print(
            f"{run['scenario_hash']} {run['manifest']['regime_id']} {run['manifest']['assumption_set_id']} "
            f"status={run['manifest']['status']} cache_hit={run['manifest']['cache_hit']}"
        )


if __name__ == "__main__":
    main()
