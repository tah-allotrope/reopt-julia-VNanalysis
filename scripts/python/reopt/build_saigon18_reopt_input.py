"""
Build REopt JSON input files for the Saigon18 Vietnam Solar+BESS project.

Reads extracted data from data/interim/saigon18/2026-03-20_saigon18_extracted_inputs.json and produces
scenario-specific REopt input dicts aligned with the Saigon18 Excel feasibility model.

Usage:
    python scripts/python/reopt/build_saigon18_reopt_input.py \
        --extracted data/interim/saigon18/2026-03-20_saigon18_extracted_inputs.json \
        --outdir scenarios/case_studies/saigon18
"""

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.preprocess import load_vietnam_data, apply_vietnam_defaults  # noqa: E402

# ---------------------------------------------------------------------------
# Project constants (sourced from Excel Assumption sheet / plan Section 4.3)
# ---------------------------------------------------------------------------

PV_KW = 40_360.0  # fixed design capacity
BESS_KW = 20_000.0  # fixed design power
BESS_KWH = 66_000.0  # fixed design energy

PVCAPEX_PER_KW = 750.0  # $/kW  (Excel: $750k/MWp)
BESS_CAPEX_PER_KW = (
    200.0  # $/kW  (power component; Excel not separated — use 0 override)
)
BESS_CAPEX_PER_KWH = 200.0  # $/kWh (Excel: $200k/MWh = $200/kWh)

ANALYSIS_YEARS = 20
EXCHANGE_RATE = 26_000.0  # VND/USD (Excel Assumption row 9)

# Blended effective CIT over 20-year tax holiday:
# 4yr @ 0% + 9yr @ 5% (50% of 10%) + 7yr @ 10% = (0+0.45+0.70)/20 = 0.0575
CIT_BLENDED_20YR = 0.0575

VOLTAGE_LEVEL = "high_voltage_above_35kv_below_220kv"  # 110 kV connection


# ---------------------------------------------------------------------------
# Builder functions
# ---------------------------------------------------------------------------


def build_base_scenario(extracted: dict) -> dict:
    """Build the base REopt input dict shared by all scenarios.

    Applies:
    - Site coordinates (HCMC area defaults; confirm actual lat/lon with developer)
    - Loads and PV production profile from extracted Excel data
    - Fixed PV and BESS sizing from the Saigon18 design
    - All project-specific financial and technical overrides
    - Vietnam defaults (TOU tariff, emissions, export rules) via apply_vietnam_defaults()
    """
    assumptions = extracted.get("assumptions", {})

    d = {
        "Site": {
            # NOTE: Confirm exact lat/lon with project developer (see plan Open Question #1)
            "latitude": 10.9577,
            "longitude": 106.8426,
        },
        "ElectricLoad": {
            "loads_kw": extracted["loads_kw"],
            "year": extracted["data_year"],  # required when loads_kw is provided
        },
        "PV": {
            "min_kw": PV_KW,
            "max_kw": PV_KW,
            "installed_cost_per_kw": assumptions.get(
                "pv_capex_usd_per_kw", PVCAPEX_PER_KW
            ),
            "om_cost_per_kw": assumptions.get("om_pv_per_kw_per_year", 6.0),
            "production_factor_series": extracted["pv_production_factor_series"],
            "location": "ground",
            "tilt": 10.96,
            "azimuth": 180.0,
            "dc_ac_ratio": 1.2,
            "losses": 0.14,
        },
        "ElectricStorage": {
            "min_kw": BESS_KW,
            "max_kw": BESS_KW,
            "min_kwh": BESS_KWH,
            "max_kwh": BESS_KWH,
            "installed_cost_per_kw": BESS_CAPEX_PER_KW,
            "installed_cost_per_kwh": assumptions.get(
                "bess_capex_usd_per_kwh", BESS_CAPEX_PER_KWH
            ),
            "installed_cost_constant": 0,  # override US $222k default
            "replace_cost_per_kw": 100.0,
            "replace_cost_per_kwh": 100.0,
            "battery_replacement_year": 10,  # discrete replacement at mid-life
            "inverter_replacement_year": 10,
            "soc_min_fraction": round(
                1.0 - assumptions.get("bess_dod_fraction", 0.85), 4
            ),  # 1 − DoD = 0.15
            "charge_efficiency": assumptions.get("bess_half_cycle_efficiency", 0.95),
            "discharge_efficiency": assumptions.get("bess_half_cycle_efficiency", 0.95),
            "om_cost_fraction_of_installed_cost": round(
                assumptions.get("om_bess_per_kwh_per_year", 2.0)
                / assumptions.get("bess_capex_usd_per_kwh", BESS_CAPEX_PER_KWH),
                6,
            ),  # $/kWh/yr ÷ $/kWh capex
            "can_grid_charge": False,  # grid charging disabled per BESS strategy
        },
        "Financial": {
            "analysis_years": assumptions.get("analysis_years", ANALYSIS_YEARS),
            "owner_tax_rate_fraction": CIT_BLENDED_20YR,
            "offtaker_tax_rate_fraction": 0.20,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": 0.05,  # 5% EVN price escalation
            "om_cost_escalation_rate_fraction": assumptions.get(
                "opex_escalation", 0.04
            ),
        },
    }

    vn = load_vietnam_data()
    apply_vietnam_defaults(
        d,
        vn,
        customer_type="industrial",
        voltage_level=VOLTAGE_LEVEL,
        region="south",
        pv_type="ground",
        apply_financials=False,  # Financial block set explicitly above
        apply_tariff=True,  # inject EVN TOU series
        apply_emissions=True,
        apply_tech_costs=False,  # CAPEX set explicitly above
        apply_export_rules=True,
        apply_zero_incentives=True,
    )
    return d


def build_scenario_a(extracted: dict) -> dict:
    """Scenario A — Baseline EVN TOU optimization, fixed sizing.

    Pure REopt optimization against full EVN TOU tariff.
    Shows what REopt recommends vs. Excel fixed-schedule assumptions.
    """
    d = build_base_scenario(extracted)
    d["_meta"] = {
        "scenario": "A",
        "name": "Baseline EVN TOU (fixed sizing)",
        "description": (
            "REopt optimizes BESS dispatch freely against full EVN TOU tariff. "
            "PV and BESS sizes fixed at Saigon18 design values."
        ),
    }
    return d


def build_scenario_b(extracted: dict) -> dict:
    """Scenario B — PPA Bundled Discount (15% off EVN TOU), fixed sizing.

    Mirrors Excel Scenario 1. Tariff adjusted to EVN TOU × 0.85 to represent
    the PPA price the project owner receives from the offtaker.
    """
    d = build_base_scenario(extracted)

    ppa_discount = extracted.get("assumptions", {}).get("ppa_discount_fraction", 0.15)
    tariff_series = d.get("ElectricTariff", {}).get("tou_energy_rates_per_kwh", [])
    if not tariff_series:
        raise ValueError(
            "ElectricTariff.tou_energy_rates_per_kwh is missing after apply_vietnam_defaults(). "
            "Check that apply_tariff=True is set and the tariff data file is present."
        )
    d["ElectricTariff"]["tou_energy_rates_per_kwh"] = [
        r * (1.0 - ppa_discount) for r in tariff_series
    ]

    d["_meta"] = {
        "scenario": "B",
        "name": f"PPA Bundled Discount ({ppa_discount:.0%} off EVN TOU, fixed sizing)",
        "description": (
            f"Tariff = EVN TOU × {1 - ppa_discount:.2f} to represent PPA price. "
            "Mirrors Excel Scenario 1 (bundled DPPA 15% discount)."
        ),
        "ppa_discount_fraction": ppa_discount,
    }
    return d


def build_scenario_c(extracted: dict) -> dict:
    """Scenario C — Optimized sizing (unconstrained).

    Removes fixed kW/kWh bounds to let REopt choose optimal PV and BESS sizes.
    Compare recommendation against Excel's fixed 40.36 MWp + 66 MWh.
    """
    d = build_base_scenario(extracted)

    # Remove fixed sizing constraints; set generous upper bounds
    d["PV"]["min_kw"] = 0
    d["PV"]["max_kw"] = 60_000.0
    # Remove the pre-computed production factor so REopt fetches from NREL
    d["PV"].pop("production_factor_series", None)

    d["ElectricStorage"]["min_kw"] = 0
    d["ElectricStorage"]["max_kw"] = 30_000.0
    d["ElectricStorage"]["min_kwh"] = 0
    d["ElectricStorage"]["max_kwh"] = 100_000.0

    d["_meta"] = {
        "scenario": "C",
        "name": "Optimized sizing (unconstrained)",
        "description": (
            "REopt selects optimal PV and BESS sizes. "
            "Production factor fetched from NREL PVWatts (not injected from Excel). "
            "Compare against design: 40,360 kWp PV + 66,000 kWh BESS."
        ),
    }
    return d


def build_scenario_d(extracted: dict) -> dict:
    """Scenario D — DPPA baseline (same as A, for post-processing).

    Runs REopt with full EVN TOU tariff to produce the dispatch profile needed
    for the DPPA CfD settlement calculation in dppa_settlement.py.
    Identical to Scenario A but tagged separately for clarity.
    """
    d = build_base_scenario(extracted)
    d["_meta"] = {
        "scenario": "D",
        "name": "DPPA baseline (EVN TOU, for post-processing)",
        "description": (
            "Same as Scenario A. Dispatch profile used as input to dppa_settlement.py "
            "to compute DPPA CfD revenue (Excel Scenario 3). "
            "Strike price: VND 1,800/kWh (confirm Decree 57 ceiling compliance)."
        ),
        "dppa_strike_price_vnd_per_kwh": 1_800.0,
        "dppa_note": (
            "Decree 57 ceiling for south ground-mounted solar+BESS: VND 1,149.86/kWh. "
            "Confirm whether project uses private-wire or grid-connected DPPA structure."
        ),
    }
    return d


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------


def save_scenario(d: dict, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    print(f"  Saved: {path}")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Build Saigon18 REopt JSON scenario inputs"
    )
    parser.add_argument(
        "--extracted",
        default="data/interim/saigon18/2026-03-20_saigon18_extracted_inputs.json",
        help="Path to extracted Excel data JSON",
    )
    parser.add_argument(
        "--outdir",
        default="scenarios/case_studies/saigon18",
        help="Output directory for scenario JSON files",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=["a", "b", "c", "d", "all"],
        default=["all"],
        help="Which scenarios to build (default: all)",
    )
    args = parser.parse_args()

    extracted_path = Path(args.extracted)
    if not extracted_path.exists():
        raise FileNotFoundError(
            f"Extracted data file not found: {extracted_path}\n"
            "Run extract_excel_inputs.py first."
        )

    with open(extracted_path, encoding="utf-8") as f:
        extracted = json.load(f)

    output_dir = Path(args.outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = set(args.scenarios)
    build_all = "all" in selected

    builders = {
        "a": (build_scenario_a, "2026-03-20_scenario-a_fixed-sizing_evntou.json"),
        "b": (build_scenario_b, "2026-03-20_scenario-b_fixed-sizing_ppa-discount.json"),
        "c": (build_scenario_c, "2026-03-23_scenario-c_optimized-sizing.json"),
        "d": (build_scenario_d, "2026-03-20_scenario-d_dppa-baseline.json"),
    }

    print("Building Saigon18 REopt scenarios...")
    for key, (builder_fn, filename) in builders.items():
        if build_all or key in selected:
            print(f"\n  Building Scenario {key.upper()}...")
            d = builder_fn(extracted)
            save_scenario(d, output_dir, filename)

    print("\nDone.")


if __name__ == "__main__":
    main()
