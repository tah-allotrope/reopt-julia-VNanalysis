"""
Regime comparison for BESS economics under Decision 963 vs Decision 14.

Runs the Option B dispatch simulation under both legacy (Decision 14) and
active (Decision 963) TOU regimes, then compares financial outcomes:
  - Cycles per day
  - Annual arbitrage revenue (USD & VND)
  - Simple payback period
  - Break-even year (cumulative net revenue exceeds capex)
  - NPV of BESS investment under each regime

Usage:
    python scripts/python/reopt/bess_regime_comparison.py \
        --reopt artifacts/results/saigon18/..._reopt-results.json \
        --scenario scenarios/case_studies/saigon18/...json \
        --config data/vietnam/vn_deal_defaults_2026.json \
        --output artifacts/reports/saigon18/bess-regime-comparison.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bess_dispatch_analysis import (
    DEFAULT_BESS_LIFETIME_YEARS,
    DEFAULT_DEGRADATION_RATE,
    DEFAULT_DISCOUNT_RATE,
    EXCHANGE_RATE_VND_PER_USD,
    _pad_to_8760,
    compute_bess_capex,
    compute_bess_npv,
    compute_cycles_per_day,
    compute_dispatch_value,
    compute_net_arbitrage,
    compute_simple_payback,
    load_deal_config,
    load_regime_tou_periods,
    load_tech_costs,
    load_tou_periods_from_tariff,
    make_classify_hour,
    model_degradation,
    simulate_option_b_dispatch,
)

REGIMES_TO_COMPARE = [
    ("decision_14_2025_legacy", "Decision 14/2025 legacy (split peak)"),
    ("decision_963_2026_current", "Decision 963/2026 current (evening peak)"),
]


def _extract_tariff_rates(tou_rates_8760: list[float]) -> tuple[float, float, float]:
    unique = sorted({round(r, 10) for r in tou_rates_8760})
    if len(unique) >= 3:
        return unique[0], unique[1], unique[-1]
    return 0.0, 0.0, 0.0


def run_regime_dispatch(
    regime_id: str,
    bess_power_kw: float,
    bess_capacity_kwh: float,
    soc_min: float,
    load_series: list[float],
    pv_series: list[float],
    tou_rates: list[float],
    exchange_rate: float,
    round_trip_eff: float,
) -> dict:
    peak_hours, offpeak_hours = load_tou_periods_from_tariff()
    regime_periods = load_regime_tou_periods(regime_id)
    if regime_periods:
        rp, ro = regime_periods
        if rp:
            peak_hours = rp
        if ro:
            offpeak_hours = ro

    classify = make_classify_hour(peak_hours, offpeak_hours)
    offpeak_rate, standard_rate, peak_rate = _extract_tariff_rates(tou_rates)
    tariff_vnd = {
        "peak": peak_rate * exchange_rate,
        "standard": standard_rate * exchange_rate,
        "offpeak": offpeak_rate * exchange_rate,
    }

    dispatch = simulate_option_b_dispatch(
        bess_power_kw=bess_power_kw,
        bess_capacity_kwh=bess_capacity_kwh,
        soc_min=soc_min,
        soc_max=1.0,
        load_series_kw=load_series,
        pv_series_kw=pv_series,
        classify=classify,
        round_trip_efficiency=round_trip_eff,
    )

    by_period = {
        "peak": dispatch["peak_discharge_mwh"],
        "standard": dispatch["standard_discharge_mwh"],
        "offpeak": dispatch["offpeak_discharge_mwh"],
    }
    discharge_value_vnd = compute_dispatch_value(by_period, tariff_vnd)

    net_arb = compute_net_arbitrage(
        charge_series_kw=dispatch["charge_series_kw"],
        discharge_series_kw=dispatch["discharge_series_kw"],
        tou_rates_per_kwh=tou_rates,
        exchange_rate=exchange_rate,
        classify=classify,
    )

    cycles = compute_cycles_per_day(
        dispatch["total_charge_mwh"] * 1000.0, bess_capacity_kwh
    )

    return {
        "regime_id": regime_id,
        "peak_hours": sorted(peak_hours),
        "offpeak_hours": sorted(offpeak_hours),
        "tariff_rates_vnd_per_kwh": {k: round(v, 4) for k, v in tariff_vnd.items()},
        "dispatch": {
            "peak_discharge_mwh": dispatch["peak_discharge_mwh"],
            "standard_discharge_mwh": dispatch["standard_discharge_mwh"],
            "offpeak_discharge_mwh": dispatch["offpeak_discharge_mwh"],
            "total_discharge_mwh": dispatch["total_discharge_mwh"],
            "total_charge_mwh": dispatch["total_charge_mwh"],
            "discharge_value_vnd": round(discharge_value_vnd, 0),
            "discharge_value_usd": round(discharge_value_vnd / exchange_rate, 2),
        },
        "net_arbitrage": net_arb,
        "cycles_per_day": cycles,
    }


def compute_break_even_year(
    capex_usd: float,
    year1_net_usd: float,
    degradation_rate: float = DEFAULT_DEGRADATION_RATE,
    lifetime_years: int = DEFAULT_BESS_LIFETIME_YEARS,
) -> int | None:
    cumulative = 0.0
    for yr in range(1, lifetime_years + 1):
        capacity_factor = max(0.0, 1.0 - degradation_rate * (yr - 1))
        cumulative += year1_net_usd * capacity_factor
        if cumulative >= capex_usd:
            return yr
    return None


def _build_finding(regime_results: list, opt_regime: dict) -> str:
    parts = []
    for r in regime_results:
        pb = r["simple_payback_years"]
        payback_str = f"{pb}-year payback" if pb is not None else "no payback"
        parts.append(
            f"Under {r['label']}, annual arbitrage is "
            f"${r['net_arbitrage']['net_usd']:,.0f} with {payback_str}."
        )
    parts.append(f"Preferred: {opt_regime['label']}.")
    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Compare BESS economics under Decision 963 vs Decision 14 regimes"
    )
    parser.add_argument("--reopt", required=True, help="REopt results JSON")
    parser.add_argument("--scenario", required=True, help="Scenario JSON")
    parser.add_argument("--config", help="Deal defaults JSON")
    parser.add_argument(
        "--output",
        default="artifacts/reports/saigon18/bess-regime-comparison.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    cfg = load_deal_config(args.config)
    exchange_rate = EXCHANGE_RATE_VND_PER_USD
    round_trip_eff = 0.92
    degradation_rate = DEFAULT_DEGRADATION_RATE
    discount_rate = DEFAULT_DISCOUNT_RATE
    bess_lifetime = DEFAULT_BESS_LIFETIME_YEARS

    if cfg:
        xr_cfg = cfg.get("exchange_rate", {})
        exchange_rate = xr_cfg.get("vnd_per_usd", exchange_rate)
        bess_cfg = cfg.get("bess", {})
        round_trip_eff = bess_cfg.get("round_trip_efficiency", round_trip_eff)
        degradation_rate = bess_cfg.get("degradation_rate_per_year", degradation_rate)

    results = json.loads(Path(args.reopt).read_text(encoding="utf-8"))
    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))

    storage = results.get("ElectricStorage", {})
    bess_power_kw = storage.get("size_kw") or 20_000.0
    bess_capacity_kwh = storage.get("size_kwh") or 66_000.0
    soc_min = storage.get("soc_min_fraction") or 0.15

    load_series = _pad_to_8760(
        results.get("ElectricLoad", {}).get("load_series_kw", [])
    )
    pv_series = _pad_to_8760(
        results.get("PV", {}).get("electric_to_load_series_kw", [])
    )
    tou_rates = _pad_to_8760(
        scenario.get("ElectricTariff", {}).get("tou_energy_rates_per_kwh", [])
    )

    tech_costs = load_tech_costs()
    bess_capex_usd = compute_bess_capex(tech_costs, bess_power_kw, bess_capacity_kwh)

    regime_results = []
    for regime_id, label in REGIMES_TO_COMPARE:
        rd = run_regime_dispatch(
            regime_id=regime_id,
            bess_power_kw=bess_power_kw,
            bess_capacity_kwh=bess_capacity_kwh,
            soc_min=soc_min,
            load_series=load_series,
            pv_series=pv_series,
            tou_rates=tou_rates,
            exchange_rate=exchange_rate,
            round_trip_eff=round_trip_eff,
        )

        net_usd = rd["net_arbitrage"]["net_usd"]
        payback = compute_simple_payback(bess_capex_usd, net_usd)
        break_even = compute_break_even_year(
            bess_capex_usd, net_usd, degradation_rate, bess_lifetime
        )
        npv_result = compute_bess_npv(
            capex_usd=bess_capex_usd,
            year1_net_usd=net_usd,
            degradation_rate=degradation_rate,
            discount_rate=discount_rate,
            lifetime_years=bess_lifetime,
        )
        degradation_schedule = model_degradation(
            year1_net_revenue_vnd=rd["net_arbitrage"]["net_vnd"],
            degradation_rate=degradation_rate,
            lifetime_years=bess_lifetime,
        )

        regime_results.append({
            "regime_id": regime_id,
            "label": label,
            "peak_hours": rd["peak_hours"],
            "offpeak_hours": rd["offpeak_hours"],
            "tariff_rates_vnd_per_kwh": rd["tariff_rates_vnd_per_kwh"],
            "dispatch": rd["dispatch"],
            "net_arbitrage": rd["net_arbitrage"],
            "cycles_per_day": rd["cycles_per_day"],
            "simple_payback_years": payback,
            "break_even_year": break_even,
            "npv": npv_result,
            "degradation_schedule": degradation_schedule,
        })

    opt_regime = max(regime_results, key=lambda r: r["net_arbitrage"]["net_usd"])
    output = {
        "source_reopt": str(Path(args.reopt)),
        "scenario": str(Path(args.scenario)),
        "config": args.config,
        "bess_power_kw": bess_power_kw,
        "bess_capacity_kwh": bess_capacity_kwh,
        "soc_min": soc_min,
        "bess_capex_usd": round(bess_capex_usd, 0),
        "exchange_rate_vnd_per_usd": exchange_rate,
        "round_trip_efficiency": round_trip_eff,
        "degradation_rate": degradation_rate,
        "discount_rate": discount_rate,
        "bess_lifetime_years": bess_lifetime,
        "regime_comparison": regime_results,
        "preferred_regime": opt_regime["regime_id"],
        "preferred_regime_label": opt_regime["label"],
        "delta_best_vs_other_usd": round(
            opt_regime["net_arbitrage"]["net_usd"]
            - min(r["net_arbitrage"]["net_usd"] for r in regime_results)
            if len(regime_results) > 1 else 0.0,
            2,
        ),
        "finding": _build_finding(regime_results, opt_regime),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Regime comparison saved to: {out_path}")
    for r in regime_results:
        print(f"  {r['label']}: ${r['net_arbitrage']['net_usd']:,.0f}/yr  "
              f"{r['cycles_per_day']} cycles/day  "
              f"NPV=${r['npv']['npv_usd']:,.0f}  "
              f"Payback={r['simple_payback_years'] or 'N/A'}yr")


if __name__ == "__main__":
    main()
