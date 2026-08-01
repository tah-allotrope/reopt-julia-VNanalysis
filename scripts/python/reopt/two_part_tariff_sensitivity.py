"""
Decree 146/2025 two-part tariff sensitivity for the Saigon18 case study.

Decree 146/2025 introduces a pilot two-part tariff (capacity charge + lower
trial energy rates) for industrial customers (Jan-Jun 2026). This script
computes the NET economic impact: the lower trial energy rates (Ca, ~30-38%
below baseline) PLUS the new demand charge (Cp x monthly peak).

The core arithmetic is in the library module
``reopt_pysam_vn.reopt.two_part_tariff``; this script is a thin CLI wrapper
that reads REopt results and tariff data, calls the library, and writes JSON.

Cross-reference: XanhTerra's two-component tariff case study
(https://xanhterra.com/twocomponent-tariff) shows that medium-to-high
load-factor profiles save money under the trial tariff.

Usage:
    python scripts/python/reopt/two_part_tariff_sensitivity.py \
        --reopt artifacts/results/saigon18/2026-03-23_scenario-a_fixed-sizing_evntou_reopt-results.json \
        --output artifacts/reports/saigon18/2026-03-29_two-part-tariff-sensitivity.json \
        --voltage-level medium_voltage_22kv_to_110kv
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.reopt.preprocess import (
    _build_8760_rates,
    _build_hourly_rates,
    load_vietnam_data,
)
from reopt_pysam_vn.reopt.two_part_tariff import (
    build_trial_energy_rate_series,
    compute_two_part_impact,
)

EXCHANGE_RATE_VND_PER_USD = _resolve_exchange_rate(load_vietnam_data(), caller_value=26_000.0)
HOURS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

DEFAULT_RATE_SWEEP_VND_PER_KW_MONTH = [0, 20_000, 40_000, 60_000, 80_000, 100_000]

VOLTAGE_LEVEL_CHOICES = [
    "high_voltage_110kv_plus",
    "medium_voltage_22kv_to_110kv",
    "medium_voltage_6kv_to_22kv",
    "low_voltage_below_6kv",
]
DEFAULT_VOLTAGE_LEVEL = "medium_voltage_22kv_to_110kv"


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) >= 8760:
        return list(series[:8760])
    return list(series) + [0.0] * (8760 - len(series))


def extract_monthly_grid_import(results: dict) -> list[float]:
    """Return 8760-point total grid import series (kW) = grid→load + grid→BESS."""
    eu = results.get("ElectricUtility", {})
    grid_to_load = _pad_to_8760(eu.get("electric_to_load_series_kw", []))
    grid_to_storage = _pad_to_8760(eu.get("electric_to_storage_series_kw", []))
    return [a + b for a, b in zip(grid_to_load, grid_to_storage)]


def monthly_peaks(series: list[float]) -> list[float]:
    """Compute maximum hourly value for each calendar month (8760 series assumed)."""
    peaks = []
    idx = 0
    for days in HOURS_PER_MONTH:
        hrs = days * 24
        chunk = series[idx : idx + hrs]
        peaks.append(max(chunk) if chunk else 0.0)
        idx += hrs
    return peaks


def estimate_demand_shaving_peaks(series: list[float], bess_power_kw: float) -> list[float]:
    """Estimate monthly peaks after BESS demand shaving (upper-bound heuristic).

    For each month, the BESS is assumed to shave any hour that exceeds the
    95th-percentile grid import for that month, limited by the BESS rated power.
    This is a proxy for what a re-optimised REopt solve would achieve without
    needing to re-run Julia.
    """
    peaks = []
    idx = 0
    for days in HOURS_PER_MONTH:
        hrs = days * 24
        chunk = series[idx : idx + hrs]
        if not chunk:
            peaks.append(0.0)
            idx += hrs
            continue
        p95 = statistics.quantiles(chunk, n=100)[94]  # 95th percentile
        # Shaveable peak = peak hour minus BESS power, floored at p95
        raw_peak = max(chunk)
        shaved_peak = max(p95, raw_peak - bess_power_kw)
        peaks.append(shaved_peak)
        idx += hrs
    return peaks


def compute_demand_charge_savings(
    bau_peaks: list[float],
    solar_peaks: list[float],
    rate_vnd_per_kw_month: float,
) -> dict:
    """Return demand charge impact metrics for a given capacity charge rate."""
    bau_annual_charge_vnd = sum(bau_peaks) * rate_vnd_per_kw_month
    solar_annual_charge_vnd = sum(solar_peaks) * rate_vnd_per_kw_month
    demand_savings_vnd = bau_annual_charge_vnd - solar_annual_charge_vnd
    return {
        "rate_vnd_per_kw_month": rate_vnd_per_kw_month,
        "bau_annual_demand_charge_vnd": round(bau_annual_charge_vnd, 0),
        "solar_bess_annual_demand_charge_vnd": round(solar_annual_charge_vnd, 0),
        "demand_savings_vnd": round(demand_savings_vnd, 0),
        "demand_savings_usd": round(demand_savings_vnd / EXCHANGE_RATE_VND_PER_USD, 2),
        "bau_annual_demand_charge_usd": round(
            bau_annual_charge_vnd / EXCHANGE_RATE_VND_PER_USD, 2
        ),
        "solar_bess_annual_demand_charge_usd": round(
            solar_annual_charge_vnd / EXCHANGE_RATE_VND_PER_USD, 2
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Decree 146/2025 two-part tariff sensitivity for Saigon18"
    )
    parser.add_argument(
        "--reopt",
        default="artifacts/results/saigon18/2026-03-23_scenario-a_fixed-sizing_evntou_reopt-results.json",
        help="Scenario A REopt results JSON",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/saigon18/2026-03-29_two-part-tariff-sensitivity.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--voltage-level",
        default=DEFAULT_VOLTAGE_LEVEL,
        choices=VOLTAGE_LEVEL_CHOICES,
        help="Voltage level for capacity charge selection",
    )
    parser.add_argument(
        "--tariff",
        default="data/vietnam/vn_tariff_2025.json",
        help="Vietnam tariff data JSON",
    )
    args = parser.parse_args()

    results = json.loads(Path(args.reopt).read_text(encoding="utf-8"))
    tariff_data = json.loads(Path(args.tariff).read_text(encoding="utf-8-sig"))["data"]

    fin = results.get("Financial", {})
    year1_energy_savings_usd = (
        fin.get("year_one_total_operating_cost_savings_before_tax") or 0.0
    )

    bess_power_kw = results.get("ElectricStorage", {}).get("size_kw") or 20_000.0

    grid_import_series = extract_monthly_grid_import(results)

    bau_monthly = results.get("ElectricLoad", {}).get("monthly_peaks_kw") or monthly_peaks(
        _pad_to_8760(results.get("ElectricLoad", {}).get("load_series_kw", []))
    )
    solar_bess_monthly = monthly_peaks(grid_import_series)
    demand_shaved_monthly = estimate_demand_shaving_peaks(
        grid_import_series, bess_power_kw
    )

    bau_annual_peak = max(bau_monthly)
    solar_bess_annual_peak = max(solar_bess_monthly)
    demand_shaved_annual_peak = max(demand_shaved_monthly)

    base_price = tariff_data["base_avg_price_vnd_per_kwh"]
    mults = tariff_data["rate_multipliers"]["industrial"][args.voltage_level]
    weekday_rates = _build_hourly_rates(
        tariff_data["tou_schedule"]["weekday"],
        base_price * mults["peak"],
        base_price * mults["standard"],
        base_price * mults["offpeak"],
    )
    sunday_rates = _build_hourly_rates(
        tariff_data["tou_schedule"]["sunday_and_public_holidays"],
        base_price * mults["peak"],
        base_price * mults["standard"],
        base_price * mults["offpeak"],
    )
    baseline_rates = _build_8760_rates(weekday_rates, sunday_rates, year=2025)
    trial_rates = build_trial_energy_rate_series(tariff_data)

    capacity_charge = tariff_data["demand_charge"]["two_part_tariff_trial"][
        "capacity_charge_vnd_per_kw_month"
    ][args.voltage_level]

    net_impact = compute_two_part_impact(
        grid_import_series, baseline_rates, trial_rates, capacity_charge
    )

    sweep_results = []
    for rate in DEFAULT_RATE_SWEEP_VND_PER_KW_MONTH:
        current = compute_demand_charge_savings(bau_monthly, solar_bess_monthly, rate)
        shaved = compute_demand_charge_savings(bau_monthly, demand_shaved_monthly, rate)
        sweep_results.append(
            {
                "rate_vnd_per_kw_month": rate,
                "current_dispatch": current,
                "demand_shaving_optimised": shaved,
                "total_savings_current_usd": round(
                    year1_energy_savings_usd + current["demand_savings_usd"], 2
                ),
                "total_savings_shaved_usd": round(
                    year1_energy_savings_usd + shaved["demand_savings_usd"], 2
                ),
            }
        )

    pilot_rate = capacity_charge
    pilot = next(
        (r for r in sweep_results if r["rate_vnd_per_kw_month"] == pilot_rate),
        sweep_results[-1],
    )

    output = {
        "source_reopt": str(Path(args.reopt)),
        "exchange_rate_vnd_per_usd": EXCHANGE_RATE_VND_PER_USD,
        "voltage_level": args.voltage_level,
        "trial_rate_basis": "range_midpoint",
        "capacity_charge_vnd_per_kw_month": capacity_charge,
        "bau_annual_peak_kw": round(bau_annual_peak, 1),
        "solar_bess_annual_peak_kw": round(solar_bess_annual_peak, 1),
        "demand_shaved_annual_peak_kw": round(demand_shaved_annual_peak, 1),
        "peak_reduction_current_kw": round(bau_annual_peak - solar_bess_annual_peak, 1),
        "peak_reduction_shaved_kw": round(bau_annual_peak - demand_shaved_annual_peak, 1),
        "bau_monthly_peaks_kw": [round(p, 1) for p in bau_monthly],
        "solar_bess_monthly_peaks_kw": [round(p, 1) for p in solar_bess_monthly],
        "demand_shaved_monthly_peaks_kw": [round(p, 1) for p in demand_shaved_monthly],
        "year1_energy_savings_usd": round(year1_energy_savings_usd, 2),
        "bess_power_kw": bess_power_kw,
        "energy_delta_vnd": round(net_impact["energy_delta_vnd"], 0),
        "annual_demand_charge_vnd": round(net_impact["annual_demand_charge_vnd"], 0),
        "net_impact_vnd": round(net_impact["net_impact_vnd"], 0),
        "net_impact_usd": round(net_impact["net_impact_usd"], 2),
        "pilot_case": pilot,
        "sweep": sweep_results,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"Two-part tariff sensitivity saved to: {out_path}")
    print(f"  Voltage level             : {args.voltage_level}")
    print(f"  Capacity charge           : {capacity_charge:,.0f} VND/kW-month")
    print(f"  BAU annual peak           : {bau_annual_peak:,.0f} kW")
    print(f"  Post-solar+BESS peak      : {solar_bess_annual_peak:,.0f} kW")
    print(f"  Peak reduction            : {bau_annual_peak - solar_bess_annual_peak:,.0f} kW")
    print(f"  Demand-shaved peak (est.) : {demand_shaved_annual_peak:,.0f} kW")
    print()
    print(f"  Energy re-pricing delta   : {net_impact['energy_delta_vnd']:,.0f} VND/yr")
    print(f"  Annual demand charge      : {net_impact['annual_demand_charge_vnd']:,.0f} VND/yr")
    print(f"  Net two-part impact       : {net_impact['net_impact_vnd']:,.0f} VND/yr")
    print(f"  Net two-part impact       : ${net_impact['net_impact_usd']:,.0f}/yr")
    sign = "SAVINGS" if net_impact["net_impact_vnd"] < 0 else "EXTRA COST"
    print(f"  Direction                 : {sign}")


if __name__ == "__main__":
    main()
