"""Materialize the Samsung SEVT - TTC Duc Hue 2 DPPA case inputs (PHASE-01).

Writes the Case-2-compatible extracted-inputs JSON, the fixed-sizing REopt
scenario, and the deal-definition artifact. All commercial terms are
triangulated; outputs are flagged ``directional``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_samsung_ttc import (
    build_samsung_ttc_definition,
    build_samsung_ttc_extracted_inputs,
    build_scenario_samsung_ttc,
)

DEFAULT_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "samsung_ttc" / "samsung_ttc_extracted_inputs.json"
)
DEFAULT_SCENARIO = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "samsung_ttc"
    / "2026-06-04_samsung-ttc_dppa-scenario.json"
)
DEFAULT_DEFINITION = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "samsung_ttc"
    / "2026-06-04_samsung-ttc_dppa-definition.json"
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Samsung-TTC DPPA extracted inputs, scenario, and definition"
    )
    parser.add_argument("--extracted-output", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--scenario-output", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--definition-output", type=Path, default=DEFAULT_DEFINITION)
    args = parser.parse_args()

    extracted = build_samsung_ttc_extracted_inputs()
    scenario = build_scenario_samsung_ttc(extracted)
    definition = build_samsung_ttc_definition(extracted)

    _write_json(args.extracted_output, extracted)
    _write_json(args.scenario_output, scenario)
    _write_json(args.definition_output, definition)

    b = extracted["benchmark"]
    print(f"Samsung-TTC extracted inputs written to : {args.extracted_output}")
    print(f"Samsung-TTC scenario written to         : {args.scenario_output}")
    print(f"Samsung-TTC definition written to       : {args.definition_output}")
    print(f"  Buyer load (synthetic)   : {b['annual_load_gwh']:.1f} GWh "
          f"(RE share {extracted['buyer_load']['re_share_of_total'] * 100:.1f}%)")
    print(f"  Weighted EVN benchmark   : {b['weighted_evn_price_vnd_per_kwh']:.2f} VND/kWh")
    print(f"  EVN standard-hour rate   : {b['standard_rate_vnd_per_kwh']:.2f} VND/kWh "
          "(buyer avoided-cost anchor)")
    print(f"  Base strike (S. ceiling) : "
          f"{extracted['strike_basis']['southern_ground_mount_ceiling_vnd_per_kwh']:.2f} VND/kWh")
    print(f"  PV fixed at              : {scenario['PV']['min_kw'] / 1000:.1f} MWdc "
          f"(dc/ac {scenario['PV']['dc_ac_ratio']:.3f}), storage disabled")


if __name__ == "__main__":
    main()
