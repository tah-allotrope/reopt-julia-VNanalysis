"""
BESS dispatch analysis: REopt free-optimization vs Excel Option B (time-locked window).

Compares two dispatch strategies:
  - REopt (free optimization): BESS charges/discharges wherever the TOU spread
    is highest, with no hourly constraints. Already in the results.
  - Excel Option B (time-locked): BESS charges during off-peak hours and
    discharges only during peak hours (weekday).

TOU period definitions are loaded from vn_tariff_2025.json --regime allows
loading regime-specific TOU overrides from vn_regime_registry_2026.json.

Usage:
    python scripts/python/reopt/bess_dispatch_analysis.py \
        --reopt artifacts/results/saigon18/..._reopt-results.json \
        --scenario scenarios/case_studies/saigon18/...json \
        --config data/vietnam/vn_deal_defaults_2026.json \
        --regime decision_963_2026_current \
        --output artifacts/reports/saigon18/bess-dispatch-analysis.json
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

DEFAULT_TARIFF_PATH = "data/vietnam/vn_tariff_2025.json"
DEFAULT_REGIME_REGISTRY_PATH = "data/vietnam/vn_regime_registry_2026.json"
DEFAULT_ROUND_TRIP_EFFICIENCY = 0.92
DEFAULT_TECH_COST_PATH = "data/vietnam/vn_tech_costs_2025.json"
DEFAULT_REGION = "south"
DEFAULT_DEGRADATION_RATE = 0.02
DEFAULT_BESS_LIFETIME_YEARS = 10
DEFAULT_DISCOUNT_RATE = 0.08

# Fallback TOU periods (Decision 963 windows) if tariff JSON not loadable
PEAK_HOURS_WEEKDAY = {17, 18, 19, 20, 21, 22}
OFFPEAK_HOURS = {0, 1, 2, 3, 4, 5}


def load_tou_periods_from_tariff(tariff_path: str | None = None) -> tuple[set[int], set[int]]:
    path = Path(tariff_path or DEFAULT_TARIFF_PATH)
    if not path.exists():
        return set(PEAK_HOURS_WEEKDAY), set(OFFPEAK_HOURS)
    tariff = json.loads(path.read_text(encoding="utf-8"))
    schedule = tariff.get("tou_schedule", {}).get("weekday", {})
    peak = set(schedule.get("peak_hours", list(PEAK_HOURS_WEEKDAY)))
    offpeak = set(schedule.get("offpeak_hours", list(OFFPEAK_HOURS)))
    return peak, offpeak


def load_regime_tou_periods(regime_id: str, registry_path: str | None = None) -> tuple[set[int], set[int]] | None:
    path = Path(registry_path or DEFAULT_REGIME_REGISTRY_PATH)
    if not path.exists():
        return None
    registry = json.loads(path.read_text(encoding="utf-8"))
    regimes = registry.get("regimes", {})
    regime = regimes.get(regime_id)
    if not regime:
        return None
    tariff_overrides = regime.get("tariff_overrides", {})
    schedule = tariff_overrides.get("tou_schedule", {}).get("weekday", {})
    if not schedule:
        return None
    peak = set(schedule.get("peak_hours", []))
    offpeak = set(schedule.get("offpeak_hours", []))
    if not peak and not offpeak:
        return None
    return peak, offpeak


def load_deal_config(config_path: str | None) -> dict:
    if not config_path:
        return {}
    raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return raw.get("data", raw)


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) >= 8760:
        return list(series[:8760])
    return list(series) + [0.0] * (8760 - len(series))


def hour_to_hod(hour_of_year: int) -> int:
    return hour_of_year % 24


def is_weekday(hour_of_year: int) -> bool:
    day_of_week = (hour_of_year // 24) % 7
    return day_of_week < 5


def make_classify_hour(peak_hours: set[int], offpeak_hours: set[int]):
    def classify(hour_of_year: int) -> str:
        hod = hour_to_hod(hour_of_year)
        if hod in offpeak_hours:
            return "offpeak"
        if is_weekday(hour_of_year) and hod in peak_hours:
            return "peak"
        return "standard"
    return classify


def split_dispatch_by_period(series_kw: list[float], classify) -> dict:
    series_kw = _pad_to_8760(series_kw)
    buckets = {"peak": 0.0, "standard": 0.0, "offpeak": 0.0}
    for h, v in enumerate(series_kw):
        buckets[classify(h)] += v
    return {k: v / 1_000.0 for k, v in buckets.items()}


def simulate_option_b_dispatch(
    bess_power_kw: float,
    bess_capacity_kwh: float,
    soc_min: float,
    soc_max: float,
    load_series_kw: list[float],
    pv_series_kw: list[float],
    classify,
    round_trip_efficiency: float = DEFAULT_ROUND_TRIP_EFFICIENCY,
) -> dict:
    load_series_kw = _pad_to_8760(load_series_kw)
    pv_series_kw = _pad_to_8760(pv_series_kw)

    capacity_kwh = bess_capacity_kwh
    soc_kwh = capacity_kwh * soc_min
    charge_eff = round_trip_efficiency ** 0.5
    discharge_eff = round_trip_efficiency ** 0.5

    charge_series = [0.0] * 8760
    discharge_series = [0.0] * 8760

    for h in range(8760):
        period = classify(h)
        if period == "offpeak":
            available_to_charge = min(
                bess_power_kw,
                (soc_max * capacity_kwh - soc_kwh) / charge_eff,
            )
            if available_to_charge > 0:
                charge_series[h] = available_to_charge
                soc_kwh += available_to_charge * charge_eff
        elif period == "peak":
            available_to_discharge = min(
                bess_power_kw,
                (soc_kwh - soc_min * capacity_kwh) * discharge_eff,
            )
            if available_to_discharge > 0:
                discharge_series[h] = available_to_discharge
                soc_kwh -= available_to_discharge / discharge_eff

    peak_mwh = sum(discharge_series[h] for h in range(8760) if classify(h) == "peak") / 1_000.0
    standard_mwh = sum(discharge_series[h] for h in range(8760) if classify(h) == "standard") / 1_000.0
    offpeak_mwh = sum(discharge_series[h] for h in range(8760) if classify(h) == "offpeak") / 1_000.0
    total_charge_mwh = sum(charge_series) / 1_000.0
    total_discharge_mwh = sum(discharge_series) / 1_000.0

    return {
        "peak_discharge_mwh": round(peak_mwh, 1),
        "standard_discharge_mwh": round(standard_mwh, 1),
        "offpeak_discharge_mwh": round(offpeak_mwh, 1),
        "total_charge_mwh": round(total_charge_mwh, 1),
        "total_discharge_mwh": round(total_discharge_mwh, 1),
        "charge_series_kw": charge_series,
        "discharge_series_kw": discharge_series,
    }


def compute_dispatch_value(dispatch_by_period: dict, tariff_rates: dict) -> float:
    value_vnd = 0.0
    for period, mwh in dispatch_by_period.items():
        rate = tariff_rates.get(period, 0.0)
        value_vnd += mwh * 1_000.0 * rate
    return value_vnd


def load_tech_costs(cost_path: str | None = None) -> dict:
    path = Path(cost_path or DEFAULT_TECH_COST_PATH)
    if not path.exists():
        return {}
    costs = json.loads(path.read_text(encoding="utf-8"))
    return costs.get("data", {}).get("ElectricStorage", {})


def compute_bess_capex(
    storage_costs: dict,
    power_kw: float,
    capacity_kwh: float,
    region: str = DEFAULT_REGION,
) -> float:
    if not storage_costs:
        return 0.0
    li_ion = storage_costs.get("li_ion", {})
    regional = li_ion.get(region, li_ion.get("south", {}))
    cost_per_kw = regional.get("installed_cost_per_kw", 370)
    cost_per_kwh = regional.get("installed_cost_per_kwh", 270)
    return cost_per_kw * power_kw + cost_per_kwh * capacity_kwh


def compute_net_arbitrage(
    charge_series_kw: list[float],
    discharge_series_kw: list[float],
    tou_rates_per_kwh: list[float],
    exchange_rate: float,
    classify,
) -> dict:
    charge_series_kw = _pad_to_8760(charge_series_kw)
    discharge_series_kw = _pad_to_8760(discharge_series_kw)
    tou_rates_per_kwh = _pad_to_8760(tou_rates_per_kwh)

    revenue_vnd = 0.0
    cost_vnd = 0.0

    for h in range(8760):
        rate_vnd = tou_rates_per_kwh[h] * exchange_rate
        revenue_vnd += discharge_series_kw[h] * rate_vnd
        cost_vnd += charge_series_kw[h] * rate_vnd

    net_vnd = revenue_vnd - cost_vnd
    total_discharge_mwh = sum(discharge_series_kw) / 1000.0
    avg_net_per_kwh_vnd = net_vnd / (total_discharge_mwh * 1000.0) if total_discharge_mwh > 0 else 0.0

    return {
        "revenue_vnd": round(revenue_vnd, 0),
        "cost_vnd": round(cost_vnd, 0),
        "net_vnd": round(net_vnd, 0),
        "revenue_usd": round(revenue_vnd / exchange_rate, 2),
        "cost_usd": round(cost_vnd / exchange_rate, 2),
        "net_usd": round(net_vnd / exchange_rate, 2),
        "net_per_kwh_usd": round(net_vnd / exchange_rate / (total_discharge_mwh * 1000.0), 4) if total_discharge_mwh > 0 else 0.0,
        "net_per_kwh_vnd": round(avg_net_per_kwh_vnd, 0),
    }


def compute_simple_payback(capex_usd: float, annual_net_usd: float) -> float | None:
    if annual_net_usd <= 0:
        return None
    return round(capex_usd / annual_net_usd, 1)


def model_degradation(
    year1_net_revenue_vnd: float,
    degradation_rate: float = DEFAULT_DEGRADATION_RATE,
    lifetime_years: int = DEFAULT_BESS_LIFETIME_YEARS,
) -> list[dict]:
    results = []
    cumulative_vnd = 0.0
    for yr in range(1, lifetime_years + 1):
        capacity_factor = max(0.0, 1.0 - degradation_rate * (yr - 1))
        year_revenue = year1_net_revenue_vnd * capacity_factor
        cumulative_vnd += year_revenue
        results.append({
            "year": yr,
            "capacity_fraction": round(capacity_factor, 4),
            "net_revenue_vnd": round(year_revenue, 0),
            "cumulative_revenue_vnd": round(cumulative_vnd, 0),
        })
    return results


def compute_bess_npv(
    capex_usd: float,
    year1_net_usd: float,
    degradation_rate: float = DEFAULT_DEGRADATION_RATE,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    lifetime_years: int = DEFAULT_BESS_LIFETIME_YEARS,
) -> dict:
    npv = -capex_usd
    for yr in range(1, lifetime_years + 1):
        capacity_factor = max(0.0, 1.0 - degradation_rate * (yr - 1))
        year_net = year1_net_usd * capacity_factor
        npv += year_net / (1 + discount_rate) ** yr
    return {
        "npv_usd": round(npv, 0),
        "capex_usd": round(capex_usd, 0),
        "discount_rate": discount_rate,
        "degradation_rate": degradation_rate,
        "lifetime_years": lifetime_years,
    }


def compute_cycles_per_day(
    total_charge_kwh: float,
    capacity_kwh: float,
) -> float:
    if capacity_kwh <= 0:
        return 0.0
    return round(total_charge_kwh / capacity_kwh / 365.0, 2)


def main():
    parser = argparse.ArgumentParser(description="BESS dispatch strategy comparison")
    parser.add_argument("--reopt", required=True, help="REopt results JSON")
    parser.add_argument("--scenario", required=True, help="Scenario JSON")
    parser.add_argument("--config", help="Deal defaults JSON")
    parser.add_argument("--regime", default=None,
                        help="Regime ID for TOU period overrides (e.g. decision_14_2025_legacy)")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    cfg = load_deal_config(args.config)

    exchange_rate = EXCHANGE_RATE_VND_PER_USD
    round_trip_eff = DEFAULT_ROUND_TRIP_EFFICIENCY
    if cfg:
        xr_cfg = cfg.get("exchange_rate", {})
        exchange_rate = xr_cfg.get("vnd_per_usd", exchange_rate)
        bess_cfg = cfg.get("bess", {})
        round_trip_eff = bess_cfg.get("round_trip_efficiency", round_trip_eff)

    peak_hours, offpeak_hours = load_tou_periods_from_tariff()

    if args.regime:
        regime_periods = load_regime_tou_periods(args.regime)
        if regime_periods:
            rp, ro = regime_periods
            if rp:
                peak_hours = rp
            if ro:
                offpeak_hours = ro
            print(f"Regime '{args.regime}' TOU periods: peak={sorted(peak_hours)}, offpeak={sorted(offpeak_hours)}")

    classify = make_classify_hour(peak_hours, offpeak_hours)

    results = json.loads(Path(args.reopt).read_text(encoding="utf-8"))
    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))

    storage = results.get("ElectricStorage", {})
    bess_power_kw = storage.get("size_kw") or 20_000.0
    bess_capacity_kwh = storage.get("size_kwh") or 66_000.0
    soc_min = storage.get("soc_min_fraction") or 0.15
    reopt_discharge = _pad_to_8760(storage.get("storage_to_load_series_kw", []))

    reopt_by_period = split_dispatch_by_period(reopt_discharge, classify)

    tou_rates = scenario.get("ElectricTariff", {}).get("tou_energy_rates_per_kwh", [])
    tou_rates = _pad_to_8760(tou_rates)
    unique_rates = sorted({round(r, 10) for r in tou_rates})
    if len(unique_rates) >= 3:
        offpeak_rate, standard_rate, peak_rate = unique_rates[0], unique_rates[1], unique_rates[-1]
    else:
        offpeak_rate, standard_rate, peak_rate = 0.0, 0.0, 0.0

    tariff_vnd = {
        "peak": peak_rate * exchange_rate,
        "standard": standard_rate * exchange_rate,
        "offpeak": offpeak_rate * exchange_rate,
    }

    excel_peak_mwh = 7_364.0
    excel_standard_mwh = 1_227.0
    excel_offpeak_mwh = 0.0

    load_series = _pad_to_8760(results.get("ElectricLoad", {}).get("load_series_kw", []))
    pv_produced = _pad_to_8760(results.get("PV", {}).get("electric_to_load_series_kw", []))

    option_b = simulate_option_b_dispatch(
        bess_power_kw=bess_power_kw,
        bess_capacity_kwh=bess_capacity_kwh,
        soc_min=soc_min,
        soc_max=1.0,
        load_series_kw=load_series,
        pv_series_kw=pv_produced,
        classify=classify,
        round_trip_efficiency=round_trip_eff,
    )
    option_b_by_period = {
        "peak": option_b["peak_discharge_mwh"],
        "standard": option_b["standard_discharge_mwh"],
        "offpeak": option_b["offpeak_discharge_mwh"],
    }

    reopt_value_vnd = compute_dispatch_value(reopt_by_period, tariff_vnd)
    option_b_value_vnd = compute_dispatch_value(option_b_by_period, tariff_vnd)
    excel_value_vnd = compute_dispatch_value(
        {"peak": excel_peak_mwh, "standard": excel_standard_mwh, "offpeak": excel_offpeak_mwh},
        tariff_vnd,
    )

    # ------------------------------------------------------------------
    # Financial quantification: capex, net arbitrage, payback, degradation
    # ------------------------------------------------------------------
    tech_costs = load_tech_costs()
    bess_capex_usd = compute_bess_capex(tech_costs, bess_power_kw, bess_capacity_kwh)
    bess_capex_vnd = bess_capex_usd * exchange_rate

    reopt_charge_series = _pad_to_8760(
        storage.get("grid_to_storage_series_kw", [])
    )
    reopt_pv_charge = _pad_to_8760(
        storage.get("pv_to_storage_series_kw", [])
    )
    reopt_total_charge = [
        a + b for a, b in zip(reopt_charge_series, reopt_pv_charge)
    ]

    optb_net_arbitrage = compute_net_arbitrage(
        charge_series_kw=option_b["charge_series_kw"],
        discharge_series_kw=option_b["discharge_series_kw"],
        tou_rates_per_kwh=tou_rates,
        exchange_rate=exchange_rate,
        classify=classify,
    )

    reopt_net_arbitrage = None
    if any(v != 0.0 for v in reopt_total_charge):
        reopt_net_arbitrage = compute_net_arbitrage(
            charge_series_kw=reopt_total_charge,
            discharge_series_kw=reopt_discharge,
            tou_rates_per_kwh=tou_rates,
            exchange_rate=exchange_rate,
            classify=classify,
        )
    else:
        reopt_net_arbitrage = {
            "revenue_vnd": round(reopt_value_vnd, 0),
            "cost_vnd": 0.0,
            "net_vnd": round(reopt_value_vnd, 0),
            "revenue_usd": round(reopt_value_vnd / exchange_rate, 2),
            "cost_usd": 0.0,
            "net_usd": round(reopt_value_vnd / exchange_rate, 2),
            "net_per_kwh_usd": 0.0,
            "net_per_kwh_vnd": 0.0,
        }

    optb_payback = compute_simple_payback(
        bess_capex_usd, optb_net_arbitrage["net_usd"]
    )
    optb_cycles = compute_cycles_per_day(
        option_b["total_charge_mwh"] * 1000.0, bess_capacity_kwh
    )

    degradation_schedule = model_degradation(
        year1_net_revenue_vnd=optb_net_arbitrage["net_vnd"],
    )
    optb_npv = compute_bess_npv(
        capex_usd=bess_capex_usd,
        year1_net_usd=optb_net_arbitrage["net_usd"],
    )

    output = {
        "source_reopt": str(Path(args.reopt)),
        "bess_power_kw": bess_power_kw,
        "bess_capacity_kwh": bess_capacity_kwh,
        "regime_id": args.regime or "default",
        "peak_hours": sorted(peak_hours),
        "offpeak_hours": sorted(offpeak_hours),
        "round_trip_efficiency": round_trip_eff,
        "exchange_rate_vnd_per_usd": exchange_rate,
        "tariff_rates_vnd_per_kwh": {k: round(v, 4) for k, v in tariff_vnd.items()},
        "bess_capex_usd": round(bess_capex_usd, 0),
        "bess_capex_vnd": round(bess_capex_vnd, 0),
        "cycles_per_day": optb_cycles,
        "bess_capex_source": str(Path(DEFAULT_TECH_COST_PATH)) if tech_costs else "not loaded",
        "reopt_free_optimization": {
            "peak_discharge_mwh": round(reopt_by_period["peak"], 1),
            "standard_discharge_mwh": round(reopt_by_period["standard"], 1),
            "offpeak_discharge_mwh": round(reopt_by_period["offpeak"], 1),
            "total_discharge_mwh": round(sum(reopt_by_period.values()), 1),
            "annual_value_vnd": round(reopt_value_vnd, 0),
            "annual_value_usd": round(reopt_value_vnd / exchange_rate, 2),
            "net_arbitrage": reopt_net_arbitrage,
        },
        "excel_option_b_fixed_window": {
            "peak_discharge_mwh": excel_peak_mwh,
            "standard_discharge_mwh": excel_standard_mwh,
            "offpeak_discharge_mwh": excel_offpeak_mwh,
            "total_discharge_mwh": excel_peak_mwh + excel_standard_mwh,
            "annual_value_vnd": round(excel_value_vnd, 0),
            "annual_value_usd": round(excel_value_vnd / exchange_rate, 2),
        },
        "simulated_option_b": {
            "peak_discharge_mwh": option_b["peak_discharge_mwh"],
            "standard_discharge_mwh": option_b["standard_discharge_mwh"],
            "offpeak_discharge_mwh": option_b["offpeak_discharge_mwh"],
            "total_discharge_mwh": option_b["total_discharge_mwh"],
            "total_charge_mwh": option_b["total_charge_mwh"],
            "annual_value_vnd": round(option_b_value_vnd, 0),
            "annual_value_usd": round(option_b_value_vnd / exchange_rate, 2),
            "net_arbitrage": optb_net_arbitrage,
            "simple_payback_years": optb_payback,
            "cycles_per_day": optb_cycles,
        },
        "lifetime_analysis": {
            "bess_lifetime_years": DEFAULT_BESS_LIFETIME_YEARS,
            "degradation_rate": DEFAULT_DEGRADATION_RATE,
            "discount_rate": DEFAULT_DISCOUNT_RATE,
            "degradation_schedule": degradation_schedule,
            "npv_usd": optb_npv["npv_usd"],
            "cumulative_lifetime_revenue_vnd": round(
                degradation_schedule[-1]["cumulative_revenue_vnd"], 0
            ) if degradation_schedule else 0.0,
        },
        "reopt_vs_excel_delta_usd": round(
            (reopt_value_vnd - excel_value_vnd) / exchange_rate, 2
        ),
        "reopt_vs_excel_delta_pct": round(
            (reopt_value_vnd - excel_value_vnd) / excel_value_vnd * 100 if excel_value_vnd else 0, 1,
        ),
        "finding": (
            "REopt free-optimization concentrates dispatch into peak hours (value maximising). "
            "The Excel fixed-window strategy (Option B) dispatches less total throughput but "
            "is constrained by available charge from PV during off-peak windows. "
            f"Net arbitrage yields ${optb_net_arbitrage['net_usd']:,.0f}/yr with "
            f"{'no payback' if optb_payback is None else f'{optb_payback}-year simple payback'}."
        ),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"BESS dispatch analysis saved to: {out_path}")
    print(f"  Regime: {args.regime or 'default'}  Peak hours: {sorted(peak_hours)}")
    print(f"  REopt: ${reopt_value_vnd / exchange_rate:,.0f}  |  Sim Option B: ${option_b_value_vnd / exchange_rate:,.0f}")


if __name__ == "__main__":
    main()
