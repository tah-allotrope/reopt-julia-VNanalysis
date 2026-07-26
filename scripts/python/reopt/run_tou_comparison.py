"""Run TOU comparison: materialize and execute scenarios under both Decision 963 and Decision 14 regimes.

Produces paired result directories under artifacts/results/tou_comparison/ and a manifest JSON
listing all paired result paths for downstream financial analysis.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.regime_runner import build_regime_matrix

REGIME_NEW = "decision_963_2026_current"
REGIME_LEGACY = "decision_14_2025_legacy"
COMPARISON_ROOT = REPO_ROOT / "artifacts" / "results" / "tou_comparison"


def slugify(path: Path) -> str:
    stem = path.stem.lower()
    out = []
    for ch in stem:
        if ch.isalnum():
            out.append(ch)
        elif ch in "_- ":
            out.append("-")
    return "".join(out).strip("-") or "scenario"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TOU comparison across two regimes.")
    parser.add_argument("--scenarios", nargs="+", required=True, help="Paths to base scenario JSONs")
    parser.add_argument("--solve", action="store_true", help="Run Julia solve (default: dry-run)")
    parser.add_argument("--output-root", default=str(COMPARISON_ROOT), help="Output root directory")
    parser.add_argument("--force", action="store_true", help="Re-run even if cached")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    regime_ids = [REGIME_NEW, REGIME_LEGACY]

    manifest_entries = []
    for scenario_path in args.scenarios:
        scenario_path = Path(scenario_path).resolve()
        scenario_slug = slugify(scenario_path)

        scenario_runs = []
        for regime_id in regime_ids:
            runs = build_regime_matrix(
                scenario_path=scenario_path,
                regime_ids=[regime_id],
                assumption_set_ids=["base"],
                result_store_root=output_root / scenario_slug,
                solve=args.solve,
                force=args.force,
            )
            if runs:
                scenario_runs.append({"regime_id": regime_id, "run": runs[0]})

        manifest_entries.append({
            "scenario_slug": scenario_slug,
            "scenario_path": str(scenario_path),
            "pair": scenario_runs,
        })

        for entry in scenario_runs:
            r = entry["run"]
            print(f"  {scenario_slug}/{entry['regime_id']}: "
                  f"hash={r['scenario_hash']} status={r['manifest']['status']} "
                  f"dir={r['result_dir']}")

    manifest_path = output_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_entries, indent=2), encoding="utf-8")
    print(f"\nManifest written to {manifest_path}")
    print(f"Total scenario pairs: {len(manifest_entries)}")


if __name__ == "__main__":
    main()