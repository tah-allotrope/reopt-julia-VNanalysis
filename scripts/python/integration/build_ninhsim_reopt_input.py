"""
Build REopt JSON input files for the Ninhsim bundled-CPPA optimization study.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_2 import build_scenario_dppa_case_2
from reopt_pysam_vn.reopt.preprocess import apply_vietnam_defaults, load_vietnam_data

PV_CAPEX_PER_KW = 750.0
PV_OM_PER_KW = 6.0
WIND_CAPEX_PER_KW = 1350.0
WIND_OM_PER_KW = 27.0
BESS_CAPEX_PER_KW = 200.0
BESS_CAPEX_PER_KWH = 200.0

ANALYSIS_YEARS = 20
OWNER_TAX_RATE = 0.0575
OFFTAKER_TAX_RATE = 0.20
OWNER_DISCOUNT_RATE = 0.08
OFFTAKER_DISCOUNT_RATE = 0.10
ELEC_COST_ESCALATION = 0.05
OM_COST_ESCALATION = 0.04

REGION = "south"
VOLTAGE_LEVEL = "medium_voltage_22kv_to_110kv"
SOLAR_STORAGE_TARGET_FRACTION = 0.60
DPPA_CASE_1_BESS_DURATION_HOURS = 2.0


def build_base_scenario(extracted: dict) -> dict:
    d = {
        "Site": {
            "latitude": extracted["site"]["latitude"],
            "longitude": extracted["site"]["longitude"],
        },
        "ElectricLoad": {
            "loads_kw": extracted["loads_kw"],
            "year": extracted["data_year"],
        },
        "PV": {
            "min_kw": 0.0,
            "max_kw": 45_000.0,
            "installed_cost_per_kw": PV_CAPEX_PER_KW,
            "om_cost_per_kw": PV_OM_PER_KW,
            "location": "ground",
            "tilt": extracted["site"]["latitude"],
            "azimuth": 180.0,
            "dc_ac_ratio": 1.2,
            "losses": 0.14,
        },
        "Wind": {
            "min_kw": 0.0,
            "max_kw": 40_000.0,
            "installed_cost_per_kw": WIND_CAPEX_PER_KW,
            "om_cost_per_kw": WIND_OM_PER_KW,
            "production_factor_series": extracted.get(
                "wind_production_factor_series", []
            ),
        },
        "ElectricStorage": {
            "min_kw": 0.0,
            "max_kw": 30_000.0,
            "min_kwh": 0.0,
            "max_kwh": 120_000.0,
            "installed_cost_per_kw": BESS_CAPEX_PER_KW,
            "installed_cost_per_kwh": BESS_CAPEX_PER_KWH,
            "installed_cost_constant": 0.0,
            "replace_cost_per_kw": 100.0,
            "replace_cost_per_kwh": 100.0,
            "battery_replacement_year": 10,
            "inverter_replacement_year": 10,
            "soc_min_fraction": 0.15,
            "charge_efficiency": 0.95,
            "discharge_efficiency": 0.95,
            "om_cost_fraction_of_installed_cost": 0.01,
            "can_grid_charge": False,
        },
        "Financial": {
            "analysis_years": ANALYSIS_YEARS,
            "owner_tax_rate_fraction": OWNER_TAX_RATE,
            "offtaker_tax_rate_fraction": OFFTAKER_TAX_RATE,
            "owner_discount_rate_fraction": OWNER_DISCOUNT_RATE,
            "offtaker_discount_rate_fraction": OFFTAKER_DISCOUNT_RATE,
            "elec_cost_escalation_rate_fraction": ELEC_COST_ESCALATION,
            "om_cost_escalation_rate_fraction": OM_COST_ESCALATION,
        },
    }

    vn = load_vietnam_data()
    apply_vietnam_defaults(
        d,
        vn,
        customer_type=extracted["site"]["customer_type"],
        voltage_level=extracted["site"]["voltage_level"],
        region=REGION,
        pv_type="ground",
        wind_type="onshore",
        apply_financials=False,
        apply_tariff=True,
        apply_emissions=True,
        apply_tech_costs=False,
        apply_export_rules=True,
        apply_zero_incentives=True,
    )
    return d


def build_scenario_a(extracted: dict) -> dict:
    d = build_base_scenario(extracted)
    d["PV"]["max_kw"] = 0.0
    d["Wind"]["max_kw"] = 0.0
    d["ElectricStorage"]["max_kw"] = 0.0
    d["ElectricStorage"]["max_kwh"] = 0.0
    d["ElectricStorage"]["min_kw"] = 0.0
    d["ElectricStorage"]["min_kwh"] = 0.0
    d["_meta"] = {
        "scenario": "A",
        "name": "Ninhsim baseline EVN TOU",
        "site": dict(extracted["site"]),
        "description": (
            "No new solar, wind, or BESS. Uses the current EVN TOU tariff at 22kV-110kV "
            "as the customer price benchmark for the bundled CPPA study."
        ),
    }
    return d


def build_scenario_b(extracted: dict) -> dict:
    d = build_base_scenario(extracted)
    d["_meta"] = {
        "scenario": "B",
        "name": "Ninhsim optimized solar+BESS+wind under bundled CPPA constraint",
        "site": dict(extracted["site"]),
        "description": (
            "Optimizes solar, wind, and storage sizes using EVN TOU for avoided-cost and residual-grid benchmarking. "
            "Customer-equivalent CPPA strike is solved in post-processing so the delivered blended customer price does not exceed the current weighted EVN benchmark."
        ),
        "customer_price_target_usd_per_kwh": extracted["benchmark"][
            "weighted_evn_price_usd_per_kwh"
        ],
        "customer_price_target_vnd_per_kwh": extracted["benchmark"][
            "weighted_evn_price_vnd_per_kwh"
        ],
        "cPPA_structure": "bundled_strike_with_residual_evn_tou",
        "cPPA_escalates_with_evn": True,
    }
    return d


def build_scenario_c(
    extracted: dict,
    enforced_target_fraction: float = SOLAR_STORAGE_TARGET_FRACTION,
    requested_target_fraction: float = SOLAR_STORAGE_TARGET_FRACTION,
) -> dict:
    d = build_base_scenario(extracted)
    d["PV"]["max_kw"] = 100_000.0
    d["ElectricStorage"]["max_kw"] = 60_000.0
    d["ElectricStorage"]["max_kwh"] = 240_000.0
    d["Wind"]["min_kw"] = 0.0
    d["Wind"]["max_kw"] = 0.0
    d["Wind"]["production_factor_series"] = []
    d["Site"]["renewable_electricity_min_fraction"] = float(enforced_target_fraction)
    d["Site"]["include_grid_renewable_fraction_in_RE_constraints"] = False
    d["Site"]["include_exported_renewable_electricity_in_total"] = False
    d["_meta"] = {
        "scenario": "C",
        "name": "Ninhsim optimized solar+storage for 60% delivered-energy target",
        "site": dict(extracted["site"]),
        "description": (
            "Optimizes solar PV and battery storage only, with wind removed, while targeting at least 60% annual renewable delivery to site load. "
            "Exports remain merchant-valued in post-processing and are excluded from the delivered-energy target basis."
        ),
        "requested_renewable_delivered_fraction_of_load": float(
            requested_target_fraction
        ),
        "enforced_renewable_delivered_fraction_of_load": float(
            enforced_target_fraction
        ),
        "target_definition": "annual_renewable_delivered_to_load_fraction",
        "target_treatment": "minimum_threshold",
        "wind_enabled": False,
        "battery_grid_charging_allowed": False,
        "excess_energy_treatment": "merchant_sale_proxy_from_weighted_evn_ratio",
        "strike_anchor": "95_percent_of_weighted_evn_tariff",
        "strike_escalation": "matches_evn_escalation",
    }
    return d


def build_scenario_dppa_case_1(extracted: dict) -> dict:
    d = build_base_scenario(extracted)
    d["PV"]["max_kw"] = 80_000.0
    d["PV"]["can_wholesale"] = False
    d["PV"]["can_net_meter"] = False
    d["PV"]["can_export_beyond_nem_limit"] = False
    d["PV"]["can_curtail"] = True
    d["Wind"]["min_kw"] = 0.0
    d["Wind"]["max_kw"] = 0.0
    d["Wind"]["production_factor_series"] = []
    d["ElectricStorage"]["max_kw"] = 30_000.0
    d["ElectricStorage"]["max_kwh"] = 60_000.0
    d["ElectricStorage"]["min_duration_hours"] = DPPA_CASE_1_BESS_DURATION_HOURS
    d["ElectricStorage"]["max_duration_hours"] = DPPA_CASE_1_BESS_DURATION_HOURS
    d["ElectricStorage"]["can_grid_charge"] = False
    d["_meta"] = {
        "scenario": "DPPA_CASE_1",
        "name": "Ninhsim DPPA Case 1 - private-wire no-excess solar plus 2h BESS",
        "site": dict(extracted["site"]),
        "description": (
            "Initial REopt sizing pass for a private-wire Ninhsim DPPA case using solar PV plus a fixed 2-hour battery. "
            "The design intent is full site use with negligible export, solar-only battery charging, and minimum project capex under a private-wire tariff ceiling."
        ),
        "contract_type": "private_wire",
        "target_design_intent": "near_zero_export_full_site_use",
        "reopt_objective": "minimum_lifecycle_cost_with_no_export_intent",
        "battery_duration_hours": DPPA_CASE_1_BESS_DURATION_HOURS,
        "battery_grid_charging_allowed": False,
        "solar_export_treatment": "disallowed_in_design_intent_with_negligible_spill_tolerance",
        "private_wire_pricing_basis": "south_ground_mounted_with_bess_ceiling_when_bess_thresholds_met",
        "final_decision_metrics": ["project_irr", "equity_irr"],
    }
    return d


def build_scenario_dppa_case_2_wrapper(extracted: dict) -> dict:
    return build_scenario_dppa_case_2(extracted)


def save_scenario(d: dict, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    path.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"  Saved: {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Ninhsim REopt scenario JSON files"
    )
    parser.add_argument(
        "--extracted",
        default="data/interim/ninhsim/ninhsim_extracted_inputs.json",
        help="Path to extracted inputs JSON",
    )
    parser.add_argument(
        "--outdir",
        default="scenarios/case_studies/ninhsim",
        help="Output directory for scenario JSON files",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=["a", "b", "c", "dppa_case_1", "dppa_case_2", "all"],
        default=["all"],
        help="Which scenarios to build",
    )
    args = parser.parse_args()

    extracted = json.loads((REPO_ROOT / args.extracted).read_text(encoding="utf-8"))
    output_dir = REPO_ROOT / args.outdir
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = set(args.scenarios)
    build_all = "all" in selected
    builders = {
        "a": (build_scenario_a, "2026-04-01_ninhsim_scenario-a_baseline-evn.json"),
        "b": (build_scenario_b, "2026-04-01_ninhsim_scenario-b_optimized-cppa.json"),
        "c": (
            build_scenario_c,
            "2026-04-08_ninhsim_solar-storage_60pct.json",
        ),
        "dppa_case_1": (
            build_scenario_dppa_case_1,
            "2026-04-09_ninhsim_dppa-case-1.json",
        ),
        "dppa_case_2": (
            build_scenario_dppa_case_2_wrapper,
            "2026-04-14_ninhsim_dppa-case-2.json",
        ),
    }

    print("Building Ninhsim REopt scenarios...")
    for key, (builder, filename) in builders.items():
        if build_all or key in selected:
            print(f"\n  Building Scenario {key.upper()}...")
            save_scenario(builder(extracted), output_dir, filename)
    print("\nDone.")


if __name__ == "__main__":
    main()
