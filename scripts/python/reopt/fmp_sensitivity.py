"""
FMP sweep sensitivity analysis.

Sweeps the Forward Market Price (FMP) from VND 1,400 to VND 2,000 in
VND 100 steps. For each FMP level, computes:

  - DPPA CfD settlement revenue (year 1 + NPV)
  - Offtaker avoided cost (REopt-derived EBITDA)
  - Developer equity IRR

Outputs a CSV matrix and a tornado chart data JSON.

Usage:
    python scripts/python/reopt/fmp_sensitivity.py \
        --reopt artifacts/results/saigon18/..._reopt-results.json \
        --scenario artifacts/results/saigon18/..._reopt-input-scenario.json \
        --config data/vietnam/vn_deal_defaults_2026.json \
        --output artifacts/reports/saigon18/fmp_sensitivity.csv

    python scripts/python/reopt/fmp_sensitivity.py \
        --reopt artifacts/results/examples/wind_battery_hospital_reopt-results.json \
        --fmp-min 1400 --fmp-max 2000 --fmp-step 100 \
        --output artifacts/reports/fmp_sensitivity.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy_financial as npf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "python"))

from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

EXCHANGE_RATE_VND_PER_USD = _resolve_exchange_rate(load_vietnam_data(), caller_value=26_400.0)
ANALYSIS_YEARS = 20
ESCALATION_RATE = 0.05
DISCOUNT_RATE = 0.08
DEBT_FRACTION = 0.70
INTEREST_RATE = 0.085
DEBT_TENOR_YEARS = 10
DELIVERY_FACTOR = 0.98
STRIKE_PRICE_VND_PER_KWH = 1_800.0
CONTRACT_TYPE = "grid_connected"
FMP_MIN = 1_400
FMP_MAX = 2_000
FMP_STEP = 100


def load_deal_config(config_path: str | None) -> dict:
    if not config_path:
        return {}
    raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return raw.get("data", raw)


def _constant_series(value: float, length: int = 8760) -> list[float]:
    return [value] * length


def compute_dppa_settlement(
    fmp_vnd_per_kwh: float,
    q_delivered_kwh: float = 1_000_000.0,
    strike_vnd: float = STRIKE_PRICE_VND_PER_KWH,
    contract_type: str = CONTRACT_TYPE,
    delivery_factor: float = DELIVERY_FACTOR,
    exchange_rate: float = EXCHANGE_RATE_VND_PER_USD,
) -> dict:
    """Compute settlement for a single FMP level with uniform hourly delivery."""
    if contract_type == "private_wire":
        settlement_per_kwh = strike_vnd
    else:
        spread = max(0.0, strike_vnd - fmp_vnd_per_kwh)
        settlement_per_kwh = spread

    net_delivery_kwh = q_delivered_kwh * delivery_factor
    total_settlement_vnd = settlement_per_kwh * net_delivery_kwh
    total_settlement_usd = total_settlement_vnd / exchange_rate

    annual_cashflows = [
        total_settlement_usd * (1 + ESCALATION_RATE) ** (y - 1)
        for y in range(1, ANALYSIS_YEARS + 1)
    ]

    npv_usd = sum(
        cf / ((1 + DISCOUNT_RATE) ** y)
        for y, cf in enumerate(annual_cashflows, start=1)
    )

    return {
        "fmp_vnd_per_kwh": round(fmp_vnd_per_kwh, 2),
        "contract_type": contract_type,
        "strike_vnd_per_kwh": strike_vnd,
        "spread_vnd_per_kwh": round(max(0.0, strike_vnd - fmp_vnd_per_kwh), 2),
        "annual_delivery_kwh": round(q_delivered_kwh, 0),
        "net_delivery_kwh": round(net_delivery_kwh, 0),
        "year_one_settlement_vnd": round(total_settlement_vnd, 0),
        "year_one_settlement_usd": round(total_settlement_usd, 2),
        "settlement_npv_usd": round(npv_usd, 2),
    }


def extract_base_ebitda(results: dict, analysis_years: int = ANALYSIS_YEARS) -> list[float]:
    """Derive annual unlevered free cash flows from REopt results.

    Falls back through three strategies:
      1. year_one_total_operating_cost_savings_before_tax
      2. year_one_energy_cost_before - year_one_energy_cost_after
      3. npv / analysis_years approximation
    """
    fin = results.get("Financial", {})
    year1_ebitda = fin.get("year_one_total_operating_cost_savings_before_tax")

    if not year1_ebitda:
        et = results.get("ElectricTariff", {})
        base_cost = et.get("year_one_energy_cost_before", 0) or 0
        with_solar = et.get("year_one_energy_cost_after", 0) or 0
        if base_cost and with_solar:
            year1_ebitda = base_cost - with_solar

    if not year1_ebitda:
        npv = fin.get("npv", 0) or 0
        year1_ebitda = abs(npv) / max(analysis_years, 1)

    if not year1_ebitda:
        year1_ebitda = 0.0

    return [
        float(year1_ebitda) * (1 + ESCALATION_RATE) ** y
        for y in range(analysis_years)
    ]


def compute_equity_irr(
    ebitda_series: list[float],
    total_capex: float,
    debt_fraction: float = DEBT_FRACTION,
    interest_rate: float = INTEREST_RATE,
    debt_tenor_years: int = DEBT_TENOR_YEARS,
    analysis_years: int = ANALYSIS_YEARS,
) -> dict:
    if total_capex <= 0:
        return {"equity_irr": None, "equity_npv": None}

    debt = total_capex * debt_fraction
    equity = total_capex * (1 - debt_fraction)

    annual_debt_service = float(npf.pmt(interest_rate, debt_tenor_years, -debt))

    equity_cashflows = [-equity]
    for yr in range(1, analysis_years + 1):
        ds = annual_debt_service if yr <= debt_tenor_years else 0.0
        equity_cashflows.append(ebitda_series[yr - 1] - ds)

    try:
        irr = float(npf.irr(equity_cashflows))
    except ValueError:
        irr = None

    npv = float(npf.npv(DISCOUNT_RATE, equity_cashflows))

    return {
        "equity_irr": round(irr, 6) if irr is not None else None,
        "equity_npv_usd": round(npv, 2),
        "equity_usd": round(equity, 2),
        "debt_usd": round(debt, 2),
        "annual_debt_service_usd": round(annual_debt_service, 2),
    }


def compute_offtaker_avoided_cost(
    ebitda_series: list[float],
    discount_rate: float = DISCOUNT_RATE,
) -> dict:
    npv = sum(
        cf / ((1 + discount_rate) ** y)
        for y, cf in enumerate(ebitda_series, start=1)
    )
    return {
        "offtaker_avoided_cost_npv_usd": round(npv, 2),
        "year_one_savings_usd": round(ebitda_series[0], 2) if ebitda_series else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="FMP sensitivity sweep for DPPA deal evaluation"
    )
    parser.add_argument("--reopt", required=True, help="Solved REopt results JSON")
    parser.add_argument("--scenario", help="REopt input scenario JSON (for load/tech info)")
    parser.add_argument("--config", help="Deal defaults JSON")
    parser.add_argument(
        "--output",
        default="artifacts/reports/fmp_sensitivity.csv",
        help="Output CSV path (default: artifacts/reports/fmp_sensitivity.csv)",
    )
    parser.add_argument("--fmp-min", type=float, default=FMP_MIN)
    parser.add_argument("--fmp-max", type=float, default=FMP_MAX)
    parser.add_argument("--fmp-step", type=float, default=FMP_STEP)
    parser.add_argument("--strike", type=float, default=STRIKE_PRICE_VND_PER_KWH)
    parser.add_argument(
        "--contract-type",
        choices=["private_wire", "grid_connected"],
        default=CONTRACT_TYPE,
    )
    parser.add_argument(
        "--delivery-mwh",
        type=float,
        default=None,
        help="Annual delivery MWh (default: derived from REopt PV size x CF)",
    )
    parser.add_argument(
        "--capex", type=float, default=None, help="Total CAPEX in USD"
    )
    parser.add_argument(
        "--tornado-json",
        help="Optional path for tornado chart data JSON output",
    )
    args = parser.parse_args()

    cfg = load_deal_config(args.config)
    debt_cfg = cfg.get("debt_terms", {})
    xr_cfg = cfg.get("exchange_rate", {})
    exchange_rate = xr_cfg.get("vnd_per_usd", EXCHANGE_RATE_VND_PER_USD)

    results = json.loads(Path(args.reopt).read_text(encoding="utf-8"))

    pv = results.get("PV", {})
    pv_size_kw = pv.get("size_kw", 0) or 0
    pv_year_one = pv.get("year_one_energy_produced_kwh", 0) or 0

    annual_delivery_kwh = (
        args.delivery_mwh * 1_000
        if args.delivery_mwh
        else (pv_year_one * 0.85 if pv_year_one else pv_size_kw * 1_500)
    )

    capex = args.capex if args.capex else (results.get("Financial", {}).get("initial_capital_costs", 0) or 0)
    if not capex:
        capex = pv_size_kw * 1_200

    base_ebitda = extract_base_ebitda(results)
    offtaker = compute_offtaker_avoided_cost(base_ebitda)

    fmp_range = list(
        range_f(args.fmp_min, args.fmp_max + args.fmp_step * 0.5, args.fmp_step)
    )

    rows = []
    tornado_data = []

    for fmp in fmp_range:
        settlement = compute_dppa_settlement(
            fmp_vnd_per_kwh=fmp,
            q_delivered_kwh=annual_delivery_kwh,
            strike_vnd=args.strike,
            contract_type=args.contract_type,
            exchange_rate=exchange_rate,
        )

        # Build settlement series: escalate year-1 value annually
        settlement_series = [
            settlement["year_one_settlement_usd"] * (1 + ESCALATION_RATE) ** y
            for y in range(ANALYSIS_YEARS)
        ]
        combined_ebitda = [b + s for b, s in zip(base_ebitda, settlement_series)]

        equity = compute_equity_irr(
            ebitda_series=combined_ebitda,
            total_capex=capex,
            debt_fraction=debt_cfg.get("debt_fraction", DEBT_FRACTION),
            interest_rate=debt_cfg.get("interest_rate", INTEREST_RATE),
            debt_tenor_years=debt_cfg.get("debt_tenor_years", DEBT_TENOR_YEARS),
        )

        rows.append({
            "fmp_vnd_per_kwh": round(fmp, 0),
            "year_one_settlement_usd": settlement["year_one_settlement_usd"],
            "settlement_npv_usd": settlement["settlement_npv_usd"],
            "offtaker_avoided_cost_npv_usd": offtaker["offtaker_avoided_cost_npv_usd"],
            "equity_irr": equity["equity_irr"] if equity["equity_irr"] is not None else "",
            "equity_npv_usd": equity["equity_npv_usd"],
            "combined_npv_usd": round(offtaker["offtaker_avoided_cost_npv_usd"] + settlement["settlement_npv_usd"], 2),
            "spread_vnd_per_kwh": settlement["spread_vnd_per_kwh"],
        })

        tornado_data.append({
            "fmp_vnd_per_kwh": round(fmp, 0),
            "parameter": "FMP",
            "base_case_value": round((FMP_MIN + FMP_MAX) / 2, 0),
            "low_value": round(fmp, 0),
            "equity_irr_at_low": equity["equity_irr"] if equity["equity_irr"] is not None else 0,
            "settlement_npv_at_low": settlement["settlement_npv_usd"],
        })

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "fmp_vnd_per_kwh",
        "year_one_settlement_usd",
        "settlement_npv_usd",
        "offtaker_avoided_cost_npv_usd",
        "equity_irr",
        "equity_npv_usd",
        "combined_npv_usd",
        "spread_vnd_per_kwh",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"FMP sensitivity sweep: {len(rows)} rows written to {out_path}")
    irrs = [r["equity_irr"] for r in rows if r["equity_irr"] != ""]
    if irrs:
        print(f"  Equity IRR range: {min(irrs):.4f} to {max(irrs):.4f}")
    print(f"  Offtaker avoided cost NPV: ${offtaker['offtaker_avoided_cost_npv_usd']:,.0f}")
    print(f"  Annual delivery: {annual_delivery_kwh:,.0f} kWh")

    if args.tornado_json:
        tornado_path = Path(args.tornado_json)
        tornado_path.parent.mkdir(parents=True, exist_ok=True)
        tornado_path.write_text(
            json.dumps(
                {
                    "analysis_type": "fmp_tornado",
                    "base_fmp_midpoint": round((FMP_MIN + FMP_MAX) / 2, 0),
                    "strike_vnd_per_kwh": args.strike,
                    "contract_type": args.contract_type,
                    "annual_delivery_kwh": round(annual_delivery_kwh, 0),
                    "total_capex_usd": round(capex, 0),
                    "offtaker_avoided_cost_npv_usd": offtaker["offtaker_avoided_cost_npv_usd"],
                    "sweep": tornado_data,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Tornado chart data written to {tornado_path}")


def range_f(start: float, stop: float, step: float):
    r = start
    while r <= stop + 0.001:
        yield r
        r += step


if __name__ == "__main__":
    main()
