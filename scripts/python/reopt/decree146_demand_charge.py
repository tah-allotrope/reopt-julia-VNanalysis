"""
Decree 146/2025 demand-charge reduction value stream.

Decree 146/2025 introduces a pilot two-part tariff (capacity charge) for
industrial customers in Vietnam effective Jan–Jun 2026. Under this structure,
customers pay a monthly demand charge (VND/kW/month) on top of the existing
TOU energy charge.

This module computes the potential demand-charge savings achievable by using
a BESS to shave monthly grid-import peaks. Trial values are populated from
vn_regime_registry_2026.json: decree146_two_part_trial_2026.

Key assumptions:
  - Monthly peak shaving is limited by BESS power rating (kW).
  - The BESS dispatch assumed here is a heuristic (95th-percentile shaving),
    not a re-optimised REopt solve.
  - The capacity charge rate is configurable from the registry or CLI.

Usage:
    python scripts/python/reopt/decree146_demand_charge.py \
        --reopt artifacts/results/saigon18/..._reopt-results.json \
        --rate 235414 \
        --output artifacts/reports/saigon18/decree146-demand-charge.json

    # Retrieve rate from regime registry
    python scripts/python/reopt/decree146_demand_charge.py \
        --reopt artifacts/results/saigon18/..._reopt-results.json \
        --regime decree146_two_part_trial_2026 \
        --output artifacts/reports/saigon18/decree146-demand-charge.json
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

EXCHANGE_RATE_VND_PER_USD = _resolve_exchange_rate(load_vietnam_data(), caller_value=26_400.0)
HOURS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
DEFAULT_REGIME_REGISTRY_PATH = "data/vietnam/vn_regime_registry_2026.json"
DEFAULT_DECREE146_REGIME_ID = "decree146_two_part_trial_2026"

# Fallback rate if registry is unavailable
FALLBACK_DEMAND_RATE_VND_PER_KW_MONTH = 235_414


def load_demand_rate_from_registry(
    regime_id: str = DEFAULT_DECREE146_REGIME_ID,
    registry_path: str | None = None,
) -> int:
    path = Path(registry_path or DEFAULT_REGIME_REGISTRY_PATH)
    if not path.exists():
        return FALLBACK_DEMAND_RATE_VND_PER_KW_MONTH
    registry = json.loads(path.read_text(encoding="utf-8"))
    regimes = registry.get("data", {}).get("regimes", {})
    regime = regimes.get(regime_id, {})
    tariff_overrides = regime.get("tariff_overrides", {})
    demand_charge = tariff_overrides.get("demand_charge", {})
    rate = demand_charge.get("monthly_demand_rate_vnd_per_kw")
    if rate is None:
        return FALLBACK_DEMAND_RATE_VND_PER_KW_MONTH
    return int(rate)


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) >= 8760:
        return list(series[:8760])
    return list(series) + [0.0] * (8760 - len(series))


def extract_monthly_grid_import(results: dict) -> list[float]:
    eu = results.get("ElectricUtility", {})
    grid_to_load = _pad_to_8760(eu.get("electric_to_load_series_kw", []))
    grid_to_storage = _pad_to_8760(eu.get("electric_to_storage_series_kw", []))
    return [a + b for a, b in zip(grid_to_load, grid_to_storage)]


def monthly_peaks(series: list[float]) -> list[float]:
    peaks = []
    idx = 0
    for days in HOURS_PER_MONTH:
        hrs = days * 24
        chunk = series[idx : idx + hrs]
        peaks.append(max(chunk) if chunk else 0.0)
        idx += hrs
    return peaks


def estimate_shaved_peaks(
    series: list[float], bess_power_kw: float
) -> list[float]:
    import statistics

    peaks = []
    idx = 0
    for days in HOURS_PER_MONTH:
        hrs = days * 24
        chunk = series[idx : idx + hrs]
        if not chunk:
            peaks.append(0.0)
            idx += hrs
            continue
        p95 = statistics.quantiles(chunk, n=100)[94]
        raw_peak = max(chunk)
        shaved_peak = max(p95, raw_peak - bess_power_kw)
        peaks.append(shaved_peak)
        idx += hrs
    return peaks


def compute_demand_charge(
    monthly_peaks_kw: list[float],
    rate_vnd_per_kw_month: float,
) -> float:
    return sum(monthly_peaks_kw) * rate_vnd_per_kw_month


def rate_sweep(
    bau_peaks: list[float],
    shaved_peaks: list[float],
    exchange_rate: float = EXCHANGE_RATE_VND_PER_USD,
) -> list[dict]:
    trial_rates = [0, 50_000, 100_000, 150_000, 200_000, 235_414, 300_000, 400_000]
    results = []
    for rate in trial_rates:
        bau = compute_demand_charge(bau_peaks, rate)
        shaved = compute_demand_charge(shaved_peaks, rate)
        savings = bau - shaved
        results.append({
            "rate_vnd_per_kw_month": rate,
            "bau_annual_charge_vnd": round(bau, 0),
            "shaved_annual_charge_vnd": round(shaved, 0),
            "savings_vnd": round(savings, 0),
            "savings_usd": round(savings / exchange_rate, 2),
        })
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Decree 146/2025 demand-charge reduction value stream"
    )
    parser.add_argument("--reopt", required=True, help="REopt results JSON")
    parser.add_argument(
        "--rate",
        type=int,
        default=None,
        help=f"Capacity charge rate (VND/kW/month). Default from registry ({DEFAULT_DECREE146_REGIME_ID}).",
    )
    parser.add_argument(
        "--regime",
        default=DEFAULT_DECREE146_REGIME_ID,
        help="Regime ID in vn_regime_registry_2026.json for the demand charge rate",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/saigon18/decree146-demand-charge.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    results_data = json.loads(Path(args.reopt).read_text(encoding="utf-8"))
    bess_power_kw = results_data.get("ElectricStorage", {}).get("size_kw") or 20_000.0

    rate_vnd = args.rate if args.rate is not None else load_demand_rate_from_registry(args.regime)

    grid_import = extract_monthly_grid_import(results_data)
    bau_monthly = monthly_peaks(
        _pad_to_8760(results_data.get("ElectricLoad", {}).get("load_series_kw", []))
    )
    solar_bess_monthly = monthly_peaks(grid_import)
    shaved_monthly = estimate_shaved_peaks(grid_import, bess_power_kw)

    bau_cost = compute_demand_charge(bau_monthly, rate_vnd)
    solar_bess_cost = compute_demand_charge(solar_bess_monthly, rate_vnd)
    shaved_cost = compute_demand_charge(shaved_monthly, rate_vnd)

    sweep = rate_sweep(bau_monthly, shaved_monthly)

    output = {
        "module": "decree146_demand_charge",
        "version": "1.0.0",
        "description": "Decree 146/2025 two-part tariff demand-charge reduction estimates",
        "source_reopt": str(Path(args.reopt)),
        "regime_id": args.regime,
        "capacity_charge_rate_vnd_per_kw_month": rate_vnd,
        "exchange_rate_vnd_per_usd": EXCHANGE_RATE_VND_PER_USD,
        "bess_power_kw": bess_power_kw,
        "bau_monthly_peaks_kw": [round(p, 1) for p in bau_monthly],
        "solar_bess_monthly_peaks_kw": [round(p, 1) for p in solar_bess_monthly],
        "shaved_monthly_peaks_kw": [round(p, 1) for p in shaved_monthly],
        "bau_annual_demand_charge_vnd": round(bau_cost, 0),
        "bau_annual_demand_charge_usd": round(bau_cost / EXCHANGE_RATE_VND_PER_USD, 2),
        "solar_bess_annual_demand_charge_vnd": round(solar_bess_cost, 0),
        "solar_bess_annual_demand_charge_usd": round(solar_bess_cost / EXCHANGE_RATE_VND_PER_USD, 2),
        "demand_shaved_annual_charge_vnd": round(shaved_cost, 0),
        "demand_shaved_annual_charge_usd": round(shaved_cost / EXCHANGE_RATE_VND_PER_USD, 2),
        "savings_current_dispatch_vnd": round(bau_cost - solar_bess_cost, 0),
        "savings_current_dispatch_usd": round((bau_cost - solar_bess_cost) / EXCHANGE_RATE_VND_PER_USD, 2),
        "savings_shaved_dispatch_vnd": round(bau_cost - shaved_cost, 0),
        "savings_shaved_dispatch_usd": round((bau_cost - shaved_cost) / EXCHANGE_RATE_VND_PER_USD, 2),
        "rate_sweep": sweep,
        "notes": (
            "Savings under 'current dispatch' reflect the existing REopt energy-optimised "
            "BESS schedule. 'Shaved dispatch' estimates an upper-bound where BESS shaves "
            "monthly peaks down to the 95th percentile. Actual savings depend on re-solving "
            "REopt with demand-charge minimization."
        ),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Decree 146 demand-charge report saved to: {out_path}")
    print(f"  Capacity charge rate: {rate_vnd:,} VND/kW/month")
    print(f"  BAU annual charge   : ${bau_cost / EXCHANGE_RATE_VND_PER_USD:,.0f}")
    print(f"  Current savings     : ${(bau_cost - solar_bess_cost) / EXCHANGE_RATE_VND_PER_USD:,.0f}")
    print(f"  Shaved savings (est): ${(bau_cost - shaved_cost) / EXCHANGE_RATE_VND_PER_USD:,.0f}")


if __name__ == "__main__":
    main()
