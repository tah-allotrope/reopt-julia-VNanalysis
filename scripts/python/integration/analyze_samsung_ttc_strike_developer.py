"""PHASE-03: Samsung-TTC strike sweep (buyer-premium surface) + PySAM developer
screen + DPPA grid-service adder sensitivity. Run under the repo .venv (PySAM).

All outputs are directional (undisclosed/triangulated commercial terms).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_samsung_ttc import (  # noqa: E402
    build_samsung_ttc_adder_sensitivity,
    build_samsung_ttc_extracted_inputs,
    build_samsung_ttc_strike_sweep,
)

OUT_DIR = REPO_ROOT / "artifacts" / "reports" / "samsung_ttc"
DEFAULT_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "samsung_ttc" / "samsung_ttc_extracted_inputs.json"
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Samsung-TTC PHASE-03 strike + developer")
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    if args.extracted.exists():
        extracted = json.loads(args.extracted.read_text(encoding="utf-8"))
    else:
        extracted = build_samsung_ttc_extracted_inputs()

    sweep = build_samsung_ttc_strike_sweep(extracted, run_developer=True)
    adder = build_samsung_ttc_adder_sensitivity(extracted)

    _write_json(args.out_dir / "2026-06-04_samsung-ttc_strike-sensitivity.json", sweep)
    _write_json(args.out_dir / "2026-06-04_samsung-ttc_contract-risk.json", adder)

    print("Samsung-TTC DPPA PHASE-03 — strike sweep + developer (DIRECTIONAL)")
    dev = sweep["developer_screen"]
    print(f"  Developer screen ran     : {dev['ran']} "
          f"(target IRR {dev['target_irr_fraction'] * 100:.0f}%, "
          f"capex ${dev['installed_cost_usd'] / 1e6:.1f}M, {dev['system_capacity_kw'] / 1000:.0f} MWdc)")
    print("  strike    buyer-vs-EVN       dev IRR    dev NPV     overlap")
    for row in sweep["sweep"]:
        irr = row["developer_irr_fraction"]
        npv = row["developer_npv_usd"]
        irr_s = f"{irr * 100:6.1f}%" if irr is not None else "   n/a"
        npv_s = f"${npv / 1e6:7.1f}M" if npv is not None else "    n/a"
        print(f"  {row['strike_vnd_per_kwh']:7.0f}  "
              f"{row['buyer_minus_benchmark_vnd'] / 1e9:+8.2f} B VND  "
              f"{irr_s}  {npv_s}  {'YES' if row['overlap'] else 'no'}")
    print(f"  Recommended position     : {sweep['negotiation_summary']['recommended_position']}")
    print("  --- DPPA adder lever (buyer Δ vs EVN) ---")
    for row in adder["adder_sensitivity"]["results"]:
        print(f"  adder {row['dppa_adder_vnd_per_kwh']:7.1f} VND/kWh -> "
              f"{row['buyer_minus_benchmark_vnd'] / 1e9:+7.2f} B VND")
    print(f"  Artifacts written to     : {args.out_dir}")


if __name__ == "__main__":
    main()
