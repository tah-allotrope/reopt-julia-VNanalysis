"""PHASE-04: Samsung-TTC regime stress + combined decision artifacts.

Run under the repo .venv so the developer screen inside the combined decision
uses the real PySAM Single Owner model. All outputs directional.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_samsung_ttc import (  # noqa: E402
    build_samsung_ttc_combined_decision,
    build_samsung_ttc_extracted_inputs,
    build_samsung_ttc_regime_stress,
)

OUT_DIR = REPO_ROOT / "artifacts" / "reports" / "samsung_ttc"
DEFAULT_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "samsung_ttc" / "samsung_ttc_extracted_inputs.json"
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Samsung-TTC PHASE-04 regime + decision")
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    if args.extracted.exists():
        extracted = json.loads(args.extracted.read_text(encoding="utf-8"))
    else:
        extracted = build_samsung_ttc_extracted_inputs()

    stress = build_samsung_ttc_regime_stress(extracted)
    decision = build_samsung_ttc_combined_decision(extracted, run_developer=True)

    _write_json(args.out_dir / "2026-06-04_samsung-ttc_regime-stress.json", stress)
    _write_json(args.out_dir / "2026-06-04_samsung-ttc_combined-decision.json", decision)

    print("Samsung-TTC DPPA PHASE-04 — regime stress + combined decision (DIRECTIONAL)")
    print("  --- Regime stress (buyer EVN bill) ---")
    for row in stress["regimes"]:
        print(f"  {row['regime_id']:38s} {row['annual_bill_gvnd']:8.1f} B VND "
              f"({row['delta_pct']:+5.1f}%, peakhrs_chg {row['peak_hours_changed']})")
    dec = decision["decision"]
    print("  --- Combined decision ---")
    print(f"  buyer saves at base strike : {dec['buyer_saves_at_base_strike']}")
    print(f"  developer overlap found    : {dec['developer_overlap_found']}")
    print(f"  recommended position       : {dec['recommended_position']}")
    print(f"  Artifacts written to       : {args.out_dir}")


if __name__ == "__main__":
    main()
