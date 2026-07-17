"""
Decree 146/2025 two-part tariff sensitivity for the Saigon18 case study.

Decree 146/2025 introduces a pilot capacity charge for industrial customers
(Jan–Jun 2026). This script computes how adding a VND/kW-month demand charge
to the existing EVN TOU energy bill changes the project's economics.

Key idea: REopt solved Scenario A optimising only for energy (TOU). The existing
dispatch is therefore not tuned for demand shaving. Two scenarios are compared:
  - "current dispatch" (energy-optimised): apply the demand charge to actual
    monthly grid-import peaks from the REopt result.
  - "demand-shaving potential" (estimated): BESS is assumed to shave the single
    highest grid-import hour in each month down to the 95th-percentile hourly
    demand — an upper bound on achievable demand reduction without re-solving.

!!!!! KNOWN MODELING GAP — Energy rate reduction not applied !!!!!
Under the actual two-part tariff (per Decree 146), the single-component
TOU energy rates are replaced by lower trial energy rates (~30-38% below
baseline). This script DOES NOT swap in the lower trial energy rates — it
only adds the demand charge on top of the existing (higher) baseline TOU
energy rates. As a result, the output OVERSTATES the cost impact of the
two-part tariff.

Cross-reference: XanhTerra's two-component tariff case study
(https://xanhterra.com/twocomponent-tariff) shows that after accounting
for the energy rate reduction, medium-to-high load-factor profiles can
save money under the trial tariff. The repo's Factory A case (~46% LF)
is approximately breakeven when the energy reduction is included.

Fix required: Before applying the demand charge, re-price the 8760 energy
series using the two-part trial rates (Ca) from
data/vietnam/vn_tariff_2025.json → demand_charge → two_part_tariff_trial →
energy_charge_vnd_per_kwh, rather than the baseline single-component TOU
rates. See also: docs/pitfalls.md "two-part tariff energy rates".

Usage:
    python scripts/python/two_part_tariff_sensitivity.py \
        --reopt artifacts/results/saigon18/2026-03-23_scenario-a_fixed-sizing_evntou_reopt-results.json \
        --output artifacts/reports/saigon18/2026-03-29_two-part-tariff-sensitivity.json
"""

import argparse
import json
import statistics
from pathlib import Path

EXCHANGE_RATE_VND_PER_USD = 26_000.0
HOURS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# Capacity-charge rate sweep: 0 to 100 kVND/kW-month in 6 steps
DEFAULT_RATE_SWEEP_VND_PER_KW_MONTH = [0, 20_000, 40_000, 60_000, 80_000, 100_000]

# Assumed Decree 146/2025 pilot rate for the base-case result card
DECREE_146_PILOT_RATE_VND_PER_KW_MONTH = 60_000


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
    args = parser.parse_args()

    results = json.loads(Path(args.reopt).read_text(encoding="utf-8"))

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

    sweep_results = []
    for rate in DEFAULT_RATE_SWEEP_VND_PER_KW_MONTH:
        current = compute_demand_charge_savings(bau_monthly, solar_bess_monthly, rate)
        shaved = compute_demand_charge_savings(bau_monthly, demand_shaved_monthly, rate)
        sweep_results.append(
            {
                "rate_vnd_per_kw_month": rate,
                "current_dispatch": current,
                "demand_shaving_optimised": shaved,
                # Total year-1 savings with two-part tariff (energy + demand savings)
                "total_savings_current_usd": round(
                    year1_energy_savings_usd + current["demand_savings_usd"], 2
                ),
                "total_savings_shaved_usd": round(
                    year1_energy_savings_usd + shaved["demand_savings_usd"], 2
                ),
            }
        )

    # Base-case result at Decree 146 pilot rate
    pilot = next(
        (r for r in sweep_results if r["rate_vnd_per_kw_month"] == DECREE_146_PILOT_RATE_VND_PER_KW_MONTH),
        sweep_results[-1],
    )

    output = {
        "source_reopt": str(Path(args.reopt)),
        "exchange_rate_vnd_per_usd": EXCHANGE_RATE_VND_PER_USD,
        "decree_146_pilot_rate_vnd_per_kw_month": DECREE_146_PILOT_RATE_VND_PER_KW_MONTH,
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
        "pilot_case": pilot,
        "sweep": sweep_results,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"Two-part tariff sensitivity saved to: {out_path}")
    print(f"  BAU annual peak           : {bau_annual_peak:,.0f} kW")
    print(f"  Post-solar+BESS peak      : {solar_bess_annual_peak:,.0f} kW")
    print(f"  Peak reduction            : {bau_annual_peak - solar_bess_annual_peak:,.0f} kW")
    print(f"  Demand-shaved peak (est.) : {demand_shaved_annual_peak:,.0f} kW")
    print()
    print(f"  At Decree 146 pilot rate ({DECREE_146_PILOT_RATE_VND_PER_KW_MONTH:,} VND/kW-month):")
    print(f"    Demand savings (current dispatch) : ${pilot['current_dispatch']['demand_savings_usd']:,.0f}/yr")
    print(f"    Demand savings (shaved dispatch)  : ${pilot['demand_shaving_optimised']['demand_savings_usd']:,.0f}/yr")
    print(f"    Total year-1 savings (current)    : ${pilot['total_savings_current_usd']:,.0f}")
    print(f"    Total year-1 savings (shaved)     : ${pilot['total_savings_shaved_usd']:,.0f}")


if __name__ == "__main__":
    main()
