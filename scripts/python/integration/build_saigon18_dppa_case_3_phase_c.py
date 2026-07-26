"""Build bounded-optimization REopt input for Saigon18 DPPA Case 3."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_3 import (
    BASE_BESS_KW,
    BASE_BESS_KWH,
    BASE_PV_KWP,
    BESS_BOUND_FACTOR_HIGH,
    BESS_BOUND_FACTOR_LOW,
    PV_BOUND_FACTOR_HIGH,
    PV_BOUND_FACTOR_LOW,
    build_dppa_case_3_input_package,
    load_saigon18_cfmp_series,
    load_saigon18_fmp_series,
    load_saigon18_load_series,
    load_saigon18_tou_series,
)


REPORT_DATE = "2026-04-21"
DEFAULT_EXTRACTED = (
    REPO_ROOT
    / "data"
    / "interim"
    / "saigon18"
    / "2026-03-20_saigon18_extracted_inputs.json"
)
DEFAULT_OUTPUT_SCENARIO_DIR = REPO_ROOT / "scenarios" / "case_studies" / "saigon18"
DEFAULT_OUTPUT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "reports" / "saigon18"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_saigon18_case3_bounded_opt_scenario(
    extracted: dict,
    pv_kw: float,
    bess_kw: float,
    bess_kwh: float,
) -> dict:
    load_kw = load_saigon18_load_series(extracted)
    tou = load_saigon18_tou_series(extracted)
    cfmp = load_saigon18_cfmp_series(extracted)
    fmp = load_saigon18_fmp_series(extracted)
    _annual_load_kwh = sum(load_kw)
    _peak_load_kw = max(load_kw)

    exchange_rate = 25450.0
    weighted_evn = sum(tou) / len(tou) if tou else 0.0

    pv_min_kw = BASE_PV_KWP * PV_BOUND_FACTOR_LOW
    pv_max_kw = BASE_PV_KWP * PV_BOUND_FACTOR_HIGH
    bess_min_kw = BASE_BESS_KW * BESS_BOUND_FACTOR_LOW
    bess_max_kw = BASE_BESS_KW * BESS_BOUND_FACTOR_HIGH
    bess_min_kwh = BASE_BESS_KWH * BESS_BOUND_FACTOR_LOW
    bess_max_kwh = BASE_BESS_KWH * BESS_BOUND_FACTOR_HIGH

    return {
        "_meta": {
            "model": "Saigon18 DPPA Case 3 Bounded Optimization Scenario",
            "case": "DPPA Case 3",
            "lane": "bounded_optimization",
            "pv_base_kwp": BASE_PV_KWP,
            "bess_base_kw": BASE_BESS_KW,
            "bess_base_kwh": BASE_BESS_KWH,
            "pv_bounds": {"min": pv_min_kw, "max": pv_max_kw},
            "bess_power_bounds": {"min": bess_min_kw, "max": bess_max_kw},
            "bess_energy_bounds": {"min": bess_min_kwh, "max": bess_max_kwh},
            "storage_floor": "mandatory_min_kw_and_min_kwh_gt_zero",
            "tariff_branch": "legacy_tou_one_component",
            "data_basis": "saigon18_extracted_8760",
            "same_site_basis": True,
        },
        "Site": {
            "latitude": extracted.get("latitude", 12.48),
            "longitude": extracted.get("longitude", 109.09),
        },
        "ElectricLoad": {
            "loads_kw": load_kw,
            "year": 2024,
        },
        "PV": {
            "min_kw": pv_min_kw,
            "max_kw": pv_max_kw,
            "installed_cost_per_kw": 750.0,
            "om_cost_per_kw": 6.0,
            "location": "ground",
            "tilt": 12.0,
            "azimuth": 180.0,
            "dc_ac_ratio": 1.2,
            "losses": 0.14,
            "macrs_option_years": 0,
            "macrs_bonus_fraction": 0.0,
            "federal_itc_fraction": 0.0,
            "federal_rebate_per_kw": 0.0,
            "state_ibi_fraction": 0.0,
            "state_ibi_max": 0.0,
            "state_rebate_per_kw": 0.0,
            "utility_ibi_fraction": 0.0,
            "utility_ibi_max": 0.0,
            "utility_rebate_per_kw": 0.0,
            "production_incentive_per_kwh": 0.0,
            "production_incentive_max_benefit": 0.0,
            "production_incentive_years": 0,
            "can_net_meter": False,
            "can_wholesale": False,
            "can_export_beyond_nem_limit": False,
            "can_curtail": True,
        },
        "ElectricStorage": {
            "min_kw": bess_min_kw,
            "max_kw": bess_max_kw,
            "min_kwh": bess_min_kwh,
            "max_kwh": bess_max_kwh,
            "installed_cost_per_kw": 200.0,
            "installed_cost_per_kwh": 0.0,
            "installed_cost_constant": 0.0,
            "replace_cost_per_kw": 0.0,
            "replace_cost_per_kwh": 175.0,
            "battery_replacement_year": 10,
            "inverter_replacement_year": 10,
            "soc_min_fraction": 0.2,
            "charge_efficiency": 0.95,
            "discharge_efficiency": 0.95,
            "om_cost_fraction_of_installed_cost": 0.0,
            "can_grid_charge": False,
            "macrs_option_years": 0,
            "macrs_bonus_fraction": 0.0,
            "total_itc_fraction": 0.0,
            "total_rebate_per_kw": 0.0,
        },
        "ElectricUtility": {
            "emissions_factor_series_lb_CO2_per_kwh": [0.92 * 0.453592 * (1.0 / 1000.0)]
            * 8760,
        },
        "Financial": {
            "analysis_years": 20,
            "owner_tax_rate_fraction": 0.2,
            "offtaker_tax_rate_fraction": 0.2,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.08,
            "elec_cost_escalation_rate_fraction": 0.04,
            "om_cost_escalation_rate_fraction": 0.04,
        },
        "_tariff_branch": "legacy_tou_one_component",
        "ElectricTariff": {
            "urdb_label": "",
            "blended_annual_energy_rate": 0,
            "tou_energy_rates_per_kwh": tou,
        },
        "_market_series": {
            "cfmp_vnd_per_kwh": cfmp,
            "fmp_vnd_per_kwh": fmp,
        },
        "_strike": {
            "weighted_evn_vnd_per_kwh": round(weighted_evn, 6),
            "strike_discount_fraction": 0.05,
            "year_one_strike_vnd_per_kwh": round(weighted_evn * (1.0 - 0.05), 6),
            "exchange_rate": exchange_rate,
        },
    }


def build_22kv_two_part_scenario(extracted: dict) -> dict:
    load_kw = load_saigon18_load_series(extracted)
    _annual_load_kwh = sum(load_kw)
    _peak_load_kw = max(load_kw)
    exchange_rate = 25450.0
    tou = load_saigon18_tou_series(extracted)
    weighted_evn = sum(tou) / len(tou) if tou else 0.0

    pv_min_kw = BASE_PV_KWP * PV_BOUND_FACTOR_LOW
    pv_max_kw = BASE_PV_KWP * PV_BOUND_FACTOR_HIGH
    bess_min_kw = BASE_BESS_KW * BESS_BOUND_FACTOR_LOW
    bess_max_kw = BASE_BESS_KW * BESS_BOUND_FACTOR_HIGH
    bess_min_kwh = BASE_BESS_KWH * BESS_BOUND_FACTOR_LOW
    bess_max_kwh = BASE_BESS_KWH * BESS_BOUND_FACTOR_HIGH

    energy_rates = []
    for h in range(8760):
        day = h // 24
        hour = h % 24
        weekday = day % 7 < 5
        if weekday:
            if 9 <= hour < 12 or 17 <= hour < 20:
                energy_rates.append(3266.0)
            elif 22 <= hour or hour < 4:
                energy_rates.append(1146.0)
            else:
                energy_rates.append(1811.0)
        else:
            if 22 <= hour or hour < 4:
                energy_rates.append(1146.0)
            else:
                energy_rates.append(1811.0)

    return {
        "_meta": {
            "model": "Saigon18 DPPA Case 3 Bounded Optimization Scenario",
            "case": "DPPA Case 3",
            "lane": "bounded_optimization_22kv_two_part",
            "pv_base_kwp": BASE_PV_KWP,
            "bess_base_kw": BASE_BESS_KW,
            "bess_base_kwh": BASE_BESS_KWH,
            "pv_bounds": {"min": pv_min_kw, "max": pv_max_kw},
            "bess_power_bounds": {"min": bess_min_kw, "max": bess_max_kw},
            "bess_energy_bounds": {"min": bess_min_kwh, "max": bess_max_kwh},
            "storage_floor": "mandatory_min_kw_and_min_kwh_gt_zero",
            "tariff_branch": "22kv_two_part_evn",
            "data_basis": "saigon18_extracted_8760",
            "same_site_basis": True,
        },
        "Site": {
            "latitude": extracted.get("latitude", 12.48),
            "longitude": extracted.get("longitude", 109.09),
        },
        "ElectricLoad": {
            "loads_kw": load_kw,
            "year": 2024,
        },
        "PV": {
            "min_kw": pv_min_kw,
            "max_kw": pv_max_kw,
            "installed_cost_per_kw": 750.0,
            "om_cost_per_kw": 6.0,
            "location": "ground",
            "tilt": 12.0,
            "azimuth": 180.0,
            "dc_ac_ratio": 1.2,
            "losses": 0.14,
            "macrs_option_years": 0,
            "macrs_bonus_fraction": 0.0,
            "federal_itc_fraction": 0.0,
            "federal_rebate_per_kw": 0.0,
            "state_ibi_fraction": 0.0,
            "state_ibi_max": 0.0,
            "state_rebate_per_kw": 0.0,
            "utility_ibi_fraction": 0.0,
            "utility_ibi_max": 0.0,
            "utility_rebate_per_kw": 0.0,
            "production_incentive_per_kwh": 0.0,
            "production_incentive_max_benefit": 0.0,
            "production_incentive_years": 0,
            "can_net_meter": False,
            "can_wholesale": False,
            "can_export_beyond_nem_limit": False,
            "can_curtail": True,
        },
        "ElectricStorage": {
            "min_kw": bess_min_kw,
            "max_kw": bess_max_kw,
            "min_kwh": bess_min_kwh,
            "max_kwh": bess_max_kwh,
            "installed_cost_per_kw": 200.0,
            "installed_cost_per_kwh": 0.0,
            "installed_cost_constant": 0.0,
            "replace_cost_per_kw": 0.0,
            "replace_cost_per_kwh": 175.0,
            "battery_replacement_year": 10,
            "inverter_replacement_year": 10,
            "soc_min_fraction": 0.2,
            "charge_efficiency": 0.95,
            "discharge_efficiency": 0.95,
            "om_cost_fraction_of_installed_cost": 0.0,
            "can_grid_charge": False,
            "macrs_option_years": 0,
            "macrs_bonus_fraction": 0.0,
            "total_itc_fraction": 0.0,
            "total_rebate_per_kw": 0.0,
        },
        "ElectricUtility": {
            "emissions_factor_series_lb_CO2_per_kwh": [0.92 * 0.453592 * (1.0 / 1000.0)]
            * 8760,
        },
        "Financial": {
            "analysis_years": 20,
            "owner_tax_rate_fraction": 0.2,
            "offtaker_tax_rate_fraction": 0.2,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.08,
            "elec_cost_escalation_rate_fraction": 0.04,
            "om_cost_escalation_rate_fraction": 0.04,
        },
        "_tariff_branch": "22kv_two_part_evn",
        "ElectricTariff": {
            "urdb_label": "",
            "blended_annual_energy_rate": 0,
            "tou_energy_rates_per_kwh": energy_rates,
        },
        "_strike": {
            "weighted_evn_vnd_per_kwh": round(weighted_evn, 6),
            "strike_discount_fraction": 0.05,
            "year_one_strike_vnd_per_kwh": round(weighted_evn * (1.0 - 0.05), 6),
            "exchange_rate": exchange_rate,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Saigon18 DPPA Case 3 bounded-optimization scenario JSONs"
    )
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument(
        "--scenario-dir", type=Path, default=DEFAULT_OUTPUT_SCENARIO_DIR
    )
    parser.add_argument(
        "--artifact-dir", type=Path, default=DEFAULT_OUTPUT_ARTIFACT_DIR
    )
    args = parser.parse_args()

    extracted = _load_json(args.extracted)
    args.scenario_dir.mkdir(parents=True, exist_ok=True)
    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    scenario_tou = build_saigon18_case3_bounded_opt_scenario(
        extracted, BASE_PV_KWP, BASE_BESS_KW, BASE_BESS_KWH
    )
    scenario_22kv = build_22kv_two_part_scenario(extracted)

    scenario_tou_path = (
        args.scenario_dir / f"{REPORT_DATE}_saigon18_dppa-case-3_bounded-opt_tou.json"
    )
    scenario_22kv_path = (
        args.scenario_dir / f"{REPORT_DATE}_saigon18_dppa-case-3_bounded-opt_22kv.json"
    )

    _write_json(scenario_tou_path, scenario_tou)
    _write_json(scenario_22kv_path, scenario_22kv)

    input_package = build_dppa_case_3_input_package(extracted)
    input_package_path = (
        args.artifact_dir / f"{REPORT_DATE}_saigon18_dppa-case-3_input-package.json"
    )
    _write_json(input_package_path, input_package)

    print(f"TOU scenario written to: {scenario_tou_path}")
    print(f"22kV scenario written to: {scenario_22kv_path}")
    print(f"Input package written to: {input_package_path}")


if __name__ == "__main__":
    main()
