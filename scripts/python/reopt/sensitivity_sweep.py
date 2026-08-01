"""
Multi-parameter sensitivity sweep for REopt deal evaluation.

Given a solved REopt result, sweeps across strike price, debt fraction,
interest rate, and FMP. Outputs a CSV matrix of equity IRR × parameter
combinations.

Usage:
    python scripts/python/reopt/sensitivity_sweep.py \
        --reopt artifacts/results/saigon18/..._reopt-results.json \
        --config data/vietnam/vn_deal_defaults_2026.json \
        --output artifacts/reports/saigon18/sensitivity-sweep.csv

    python scripts/python/reopt/sensitivity_sweep.py \
        --reopt <results.json> \
        --strike-min 800 --strike-max 1400 --strike-step 50 \
        --output <output.csv>
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "python"))


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def load_config(config_path: str | None) -> dict:
    if not config_path:
        return {}
    raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return raw.get("data", raw)


def extract_base_ebitda(results: dict, analysis_years: int = 20) -> list[float]:
    fin = results.get("Financial", {})
    lcc = fin.get("lcc", 0)
    npv = fin.get("npv", 0)
    _capital_cost = fin.get("initial_capital_costs", 0)

    base_cost = results.get("ElectricTariff", {}).get("year_one_energy_cost_before", 0)
    with_solar = results.get("ElectricTariff", {}).get("year_one_energy_cost_after", 0)

    if base_cost and with_solar:
        year_one_savings = base_cost - with_solar
    elif lcc and npv:
        year_one_savings = abs(npv) / analysis_years if analysis_years > 0 else 0
    else:
        year_one_savings = 0

    ebitda = []
    for y in range(analysis_years):
        ebitda.append(year_one_savings * (1.05 ** y))
    return ebitda


def compute_equity_irr(
    ebitda_series: list[float],
    total_capex: float,
    debt_fraction: float,
    interest_rate: float,
    debt_tenor_years: int = 10,
    analysis_years: int = 20,
) -> dict:
    try:
        import numpy_financial as npf
    except ImportError:
        raise ImportError("numpy_financial required. Run: pip install numpy-financial")

    if total_capex <= 0:
        return {"equity_irr": None, "equity_npv": None, "error": "CAPEX must be positive"}

    equity_investment = total_capex * (1 - debt_fraction)
    debt_amount = total_capex * debt_fraction

    if debt_amount > 0 and interest_rate > 0 and debt_tenor_years > 0:
        annual_payment = abs(npf.pmt(interest_rate, debt_tenor_years, debt_amount))
    else:
        annual_payment = 0

    net_cashflows = []
    for y in range(analysis_years):
        ebitda = ebitda_series[y] if y < len(ebitda_series) else 0
        debt_service = annual_payment if y < debt_tenor_years else 0
        net = ebitda - debt_service
        net_cashflows.append(net)

    net_cashflows[0] -= equity_investment

    try:
        irr = float(npf.irr(net_cashflows))
    except Exception:
        irr = None

    return {
        "equity_irr": round(irr, 6) if irr is not None else None,
        "equity_npv": round(float(npf.npv(0.08, net_cashflows)), 2),
        "equity_investment": round(equity_investment, 2),
        "debt_amount": round(debt_amount, 2),
        "annual_debt_service": round(annual_payment, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-parameter sensitivity sweep")
    parser.add_argument("--reopt", required=True, help="Solved REopt results JSON")
    parser.add_argument("--config", help="Deal defaults JSON")
    parser.add_argument("--output", default="sensitivity_sweep.csv", help="Output CSV path")

    # Override sweep ranges
    parser.add_argument("--strike-min", type=float, default=None)
    parser.add_argument("--strike-max", type=float, default=None)
    parser.add_argument("--strike-step", type=float, default=None)
    parser.add_argument("--debt-min", type=float, default=None)
    parser.add_argument("--debt-max", type=float, default=None)
    parser.add_argument("--debt-step", type=float, default=None)
    parser.add_argument("--rate-min", type=float, default=None)
    parser.add_argument("--rate-max", type=float, default=None)
    parser.add_argument("--rate-step", type=float, default=None)
    parser.add_argument("--fmp-min", type=float, default=None)
    parser.add_argument("--fmp-max", type=float, default=None)
    parser.add_argument("--fmp-step", type=float, default=None)

    parser.add_argument("--top-n", type=int, default=None,
                        help="Show only top N combinations by IRR delta")

    args = parser.parse_args()

    cfg = load_config(args.config)
    sweep_range = cfg.get("sensitivity_ranges", {})

    results = json.loads(Path(args.reopt).read_text(encoding="utf-8"))

    # Build parameter sweep ranges
    strike_range = range(
        int(args.strike_min or sweep_range.get("strike_vnd_per_kwh", {}).get("min", 800)),
        int(args.strike_max or sweep_range.get("strike_vnd_per_kwh", {}).get("max", 1400)) + 1,
        int(args.strike_step or sweep_range.get("strike_vnd_per_kwh", {}).get("step", 50)),
    )
    debt_range = [round(x, 2) for x in list(
        range_f(
            args.debt_min or sweep_range.get("debt_fraction", {}).get("min", 0.60),
            args.debt_max or sweep_range.get("debt_fraction", {}).get("max", 0.80),
            args.debt_step or sweep_range.get("debt_fraction", {}).get("step", 0.05),
        )
    )]
    rate_range = [round(x, 4) for x in list(
        range_f(
            args.rate_min or sweep_range.get("interest_rate", {}).get("min", 0.07),
            args.rate_max or sweep_range.get("interest_rate", {}).get("max", 0.10),
            args.rate_step or sweep_range.get("interest_rate", {}).get("step", 0.005),
        )
    )]
    fmp_range = range(
        int(args.fmp_min or sweep_range.get("fmp_vnd_per_kwh", {}).get("min", 1400)),
        int(args.fmp_max or sweep_range.get("fmp_vnd_per_kwh", {}).get("max", 2000)) + 1,
        int(args.fmp_step or sweep_range.get("fmp_vnd_per_kwh", {}).get("step", 100)),
    )
    fmp_range = list(fmp_range)

    debt_cfg = cfg.get("debt_terms", {})
    analysis_cfg = cfg.get("analysis", {})
    capex = results.get("Financial", {}).get("initial_capital_costs", 49_510_000.0)

    ebitda = extract_base_ebitda(results, analysis_cfg.get("analysis_years", 20))
    debt_tenor = debt_cfg.get("debt_tenor_years", 10)
    analysis_years = analysis_cfg.get("analysis_years", 20)

    rows = []
    for strike in strike_range:
        for debt_frac in debt_range:
            for int_rate in rate_range:
                irr_result = compute_equity_irr(
                    ebitda_series=ebitda,
                    total_capex=capex,
                    debt_fraction=debt_frac,
                    interest_rate=int_rate,
                    debt_tenor_years=debt_tenor,
                    analysis_years=analysis_years,
                )
                rows.append({
                    "strike_vnd_per_kwh": strike,
                    "debt_fraction": debt_frac,
                    "interest_rate": int_rate,
                    "equity_irr": irr_result.get("equity_irr", ""),
                    "equity_npv": irr_result.get("equity_npv", ""),
                    "equity_investment": irr_result.get("equity_investment", ""),
                    "debt_amount": irr_result.get("debt_amount", ""),
                })

    if args.top_n:
        scored = [(r, abs(r.get("equity_irr") or 0)) for r in rows if r.get("equity_irr") is not None]
        scored.sort(key=lambda x: x[1], reverse=True)
        rows = [r for r, _ in scored[:args.top_n]]

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if rows:
        fieldnames = ["strike_vnd_per_kwh", "debt_fraction", "interest_rate",
                       "equity_irr", "equity_npv", "equity_investment", "debt_amount"]
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    total_combos = len(strike_range) * len(debt_range) * len(rate_range)
    print(f"Sensitivity sweep complete: {len(rows)} rows from {total_combos} combinations")
    print(f"Output: {out_path}")
    if rows:
        irrs = [r["equity_irr"] for r in rows if r["equity_irr"] is not None]
        if irrs:
            print(f"IRR range: {min(irrs):.1%} to {max(irrs):.1%}")


def range_f(start: float, stop: float, step: float):
    r = start
    while r <= stop + 1e-9:
        yield r
        r += step


if __name__ == "__main__":
    main()
