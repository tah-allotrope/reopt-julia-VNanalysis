"""Analyze the Samsung SEVT - TTC Duc Hue 2 DPPA buyer settlement (PHASE-02).

Generates the fixed 49 MWp southern solar 8760 (no Julia solve), runs the reused
Case-2 settlement engine with the Samsung Southern-ceiling strike, and writes the
physical / settlement / benchmark / contracted-slice artifacts. All outputs are
flagged ``directional``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_samsung_ttc import (
    analyze_samsung_ttc_settlement,
    build_samsung_ttc_extracted_inputs,
)

OUT_DIR = REPO_ROOT / "artifacts" / "reports" / "samsung_ttc"
DEFAULT_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "samsung_ttc" / "samsung_ttc_extracted_inputs.json"
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Samsung-TTC DPPA buyer settlement (PHASE-02)"
    )
    parser.add_argument(
        "--extracted",
        type=Path,
        default=DEFAULT_EXTRACTED,
        help="Extracted inputs JSON (defaults to the materialized PHASE-01 file)",
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    if args.extracted.exists():
        extracted = json.loads(args.extracted.read_text(encoding="utf-8"))
    else:
        extracted = build_samsung_ttc_extracted_inputs()

    out = analyze_samsung_ttc_settlement(extracted)

    # The hourly ledger is 8760 rows; write a compact settlement (summary only)
    # alongside the full physical/benchmark/slice artifacts.
    settlement_compact = {k: v for k, v in out["settlement"].items() if k != "hourly_ledger"}

    _write_json(args.out_dir / "2026-06-04_samsung-ttc_solar-summary.json", out["solar_summary"])
    _write_json(args.out_dir / "2026-06-04_samsung-ttc_physical-summary.json", out["physical"])
    _write_json(args.out_dir / "2026-06-04_samsung-ttc_buyer-settlement.json", settlement_compact)
    _write_json(args.out_dir / "2026-06-04_samsung-ttc_buyer-benchmark.json", out["benchmark"])
    _write_json(args.out_dir / "2026-06-04_samsung-ttc_contracted-slice.json",
                {"contracted_slice": out["contracted_slice"], "quality": out["quality"]})

    sol = out["solar_summary"]
    slc = out["contracted_slice"]
    costs = out["benchmark"]["year_one_costs"]
    print("Samsung-TTC DPPA settlement (PHASE-02) — DIRECTIONAL")
    print(f"  Solar (fixed 49 MWp)     : {sol['annual_solar_gwh']:.2f} GWh  "
          f"(AC CF {sol['ac_capacity_factor'] * 100:.1f}%, peak {sol['peak_ac_kw'] / 1000:.1f} MW)")
    print(f"  Matched (contracted)     : {slc['matched_quantity_gwh']:.2f} GWh")
    print(f"  Strike (S. ceiling)      : {out['quality']['strike_vnd_per_kwh']:.2f} VND/kWh")
    print(f"  Buyer eff. cost (matched): {slc['buyer_effective_cost_vnd_per_kwh']:.2f} VND/kWh")
    print(f"  EVN avoided  (matched)   : {slc['evn_avoided_cost_vnd_per_kwh']:.2f} VND/kWh")
    print(f"  Buyer savings on slice   : {slc['buyer_savings_vnd'] / 1e9:.2f} B VND/yr "
          f"(~${slc['buyer_savings_usd'] / 1e6:.2f}M)")
    print(f"  Whole-bill savings vs EVN: {costs['buyer_savings_vs_evn_vnd'] / 1e9:.2f} B VND/yr")
    print(f"  Market ref / solar source: {out['quality']['market_reference_price_type']} / "
          f"{out['quality']['solar_profile_source']}")
    print(f"  Artifacts written to     : {args.out_dir}")


if __name__ == "__main__":
    main()
