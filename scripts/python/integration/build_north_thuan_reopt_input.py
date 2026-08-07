"""
Build REopt JSON input files for the North Thuan Wind+Solar+BESS validation.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.preprocess import apply_vietnam_defaults, load_vietnam_data

STRIKE_USD_PER_KWH = 0.055
VOLTAGE_LEVEL = "medium_voltage_22kv_to_110kv"


def _flat_tariff(rate_usd_per_kwh: float, hours: int = 8760) -> list[float]:
    return [float(rate_usd_per_kwh)] * hours


def build_base_scenario(extracted: dict) -> dict:
    assumptions = extracted["assumptions"]
    loads_kw = extracted["loads_kw"]

    d = {
        "Site": {
            "latitude": extracted["site"]["latitude"],
            "longitude": extracted["site"]["longitude"],
        },
        "ElectricLoad": {
            "loads_kw": loads_kw,
            "year": extracted["data_year"],
        },
        "PV": {
            "min_kw": 30_000.0,
            "max_kw": 30_000.0,
            "installed_cost_per_kw": 700.0,
            "om_cost_per_kw": 8.0,
            "tilt": extracted["site"]["latitude"],
            "azimuth": 180.0,
            "dc_ac_ratio": 1.2,
            "losses": 0.14,
            "location": "ground",
        },
        "Wind": {
            "min_kw": 20_000.0,
            "max_kw": 20_000.0,
            "installed_cost_per_kw": 1_200.0,
            "om_cost_per_kw": 25.0,
            "production_factor_series": extracted.get(
                "wind_production_factor_series", []
            ),
        },
        "ElectricStorage": {
            "min_kw": 10_000.0,
            "max_kw": 10_000.0,
            "min_kwh": 40_000.0,
            "max_kwh": 40_000.0,
            "installed_cost_per_kw": 200.0,
            "installed_cost_per_kwh": 200.0,
            "installed_cost_constant": 0.0,
            "soc_min_fraction": 0.10,
            "charge_efficiency": 0.95,
            "discharge_efficiency": 0.95,
            "can_grid_charge": False,
        },
        "ElectricTariff": {
            "tou_energy_rates_per_kwh": _flat_tariff(
                assumptions["dppa_strike_usd_per_kwh"]
            ),
        },
        "Financial": {
            "analysis_years": int(assumptions["analysis_years"]),
            "owner_tax_rate_fraction": 0.10,
            "offtaker_tax_rate_fraction": 0.20,
            "owner_discount_rate_fraction": 0.085,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.02,
        },
    }

    vn = load_vietnam_data()
    apply_vietnam_defaults(
        d,
        vn,
        customer_type="industrial",
        voltage_level=VOLTAGE_LEVEL,
        region=extracted["site"]["region"],
        pv_type="ground",
        wind_type="onshore",
        apply_financials=False,
        apply_tariff=False,
        apply_emissions=True,
        apply_tech_costs=False,
        apply_export_rules=True,
        apply_zero_incentives=True,
    )
    return d


def build_scenario_a(extracted: dict) -> dict:
    d = build_base_scenario(extracted)
    d["_meta"] = {
        "scenario": "A",
        "name": "North Thuan A - fixed sizing, flat DPPA strike tariff",
        "description": (
            "Mirror of the staff sizing case: 30 MW solar, 20 MW wind, and 10 MW / 40 MWh battery. "
            "Uses a flat 0.055 USD/kWh tariff as the DPPA approximation inside REopt."
        ),
    }
    return d


def build_scenario_b(extracted: dict) -> dict:
    d = build_base_scenario(extracted)
    d["PV"]["min_kw"] = 0.0
    d["PV"]["max_kw"] = 60_000.0
    d["Wind"]["min_kw"] = 0.0
    d["Wind"]["max_kw"] = 50_000.0
    d["ElectricStorage"]["min_kw"] = 0.0
    d["ElectricStorage"]["max_kw"] = 20_000.0
    d["ElectricStorage"]["min_kwh"] = 0.0
    d["ElectricStorage"]["max_kwh"] = 120_000.0
    d["_meta"] = {
        "scenario": "B",
        "name": "North Thuan B - optimized sizing",
        "description": (
            "Lets REopt optimize solar, wind, and storage size under the same flat strike-price tariff "
            "to test whether the staff fixed design is economically efficient."
        ),
    }
    return d


def build_scenario_c(extracted: dict) -> dict:
    d = build_base_scenario(extracted)
    d["ElectricStorage"]["min_kw"] = 0.0
    d["ElectricStorage"]["max_kw"] = 0.0
    d["ElectricStorage"]["min_kwh"] = 0.0
    d["ElectricStorage"]["max_kwh"] = 0.0
    d["_meta"] = {
        "scenario": "C",
        "name": "North Thuan C - fixed sizing without BESS",
        "description": (
            "Keeps the staff solar and wind sizes fixed while removing storage to isolate the hybrid-generation-only case."
        ),
    }
    return d


def save_scenario(d: dict, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    path.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"  Saved: {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build North Thuan REopt scenario JSON files"
    )
    parser.add_argument(
        "--extracted",
        default="data/interim/north_thuan/north_thuan_extracted_inputs.json",
        help="Path to extracted inputs JSON",
    )
    parser.add_argument(
        "--outdir",
        default="scenarios/case_studies/north_thuan",
        help="Output directory for scenario JSON files",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=["a", "b", "c", "all"],
        default=["all"],
        help="Which scenarios to build",
    )
    args = parser.parse_args()

    extracted = json.loads(Path(args.extracted).read_text(encoding="utf-8"))
    output_dir = Path(args.outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = set(args.scenarios)
    build_all = "all" in selected
    builders = {
        "a": (build_scenario_a, "north_thuan_scenario_a.json"),
        "b": (build_scenario_b, "north_thuan_scenario_b.json"),
        "c": (build_scenario_c, "north_thuan_scenario_c.json"),
    }

    print("Building North Thuan REopt scenarios...")
    for key, (builder, filename) in builders.items():
        if build_all or key in selected:
            print(f"\n  Building Scenario {key.upper()}...")
            save_scenario(builder(extracted), output_dir, filename)
    print("\nDone.")


if __name__ == "__main__":
    main()
