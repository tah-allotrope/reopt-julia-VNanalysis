"""
Compare Saigon18 REopt results against Excel model outputs.

This script supports the canonical fixed-size/optimized scenarios and the DPPA
post-processed Scenario D workflow used in the final Saigon18 report.
"""

import argparse
import json
from pathlib import Path

EXCEL_TARGETS = {
    "pv_gen_mwh": {"value": 71_808.0, "tolerance": 0.01, "unit": "MWh"},
    "pv_to_load_mwh": {"value": 62_106.0, "tolerance": 0.02, "unit": "MWh"},
    "pv_to_grid_mwh": {"value": 1_087.0, "tolerance": 0.05, "unit": "MWh"},
    "bess_discharge_mwh": {"value": 8_591.0, "tolerance": 0.05, "unit": "MWh"},
    "bess_discharge_peak_mwh": {"value": 7_364.0, "tolerance": 0.05, "unit": "MWh"},
    "bess_discharge_standard_mwh": {"value": 1_227.0, "tolerance": 0.05, "unit": "MWh"},
    "bess_discharge_offpeak_mwh": {"value": 0.0, "tolerance": None, "unit": "MWh"},
    "grid_purchases_mwh": {"value": 112_454.0, "tolerance": 0.02, "unit": "MWh"},
    "npv_usd": {"value": 22_034_000.0, "tolerance": None, "unit": "USD"},
    "payback_years": {"value": 6.0, "tolerance": 1.0, "unit": "years"},
    "year1_revenue_usd": {"value": 5_056_418.0, "tolerance": None, "unit": "USD"},
    "equity_irr": {"value": 0.194, "tolerance": 0.01, "unit": "fraction"},
}


DISCREPANCY_EXPLANATIONS = {
    "npv_usd": (
        "REopt NPV is unlevered. Scenario D can add a DPPA settlement NPV, but the Excel "
        "headline still mixes contract structure and financing assumptions."
    ),
    "payback_years": (
        "REopt simple payback is based on avoided cost. Excel frames project economics as "
        "contract revenue and financing-driven payback."
    ),
    "bess_discharge_mwh": (
        "Total BESS throughput overstates the difference because Excel tracks only the peak "
        "+ standard-hour dispatch it intends to monetize."
    ),
    "bess_discharge_peak_mwh": (
        "Peak-hour discharge is the most apples-to-apples comparison against the Excel battery "
        "controller logic."
    ),
    "bess_discharge_standard_mwh": (
        "Standard-hour discharge captures the second part of the Excel dispatch target."
    ),
    "bess_discharge_offpeak_mwh": (
        "Any off-peak discharge indicates REopt is using the battery more flexibly than the "
        "Excel fixed-window strategy."
    ),
    "pv_to_grid_mwh": (
        "The Decree 57 export cap is now enforced as a hard JuMP constraint in the canonical "
        "Saigon18 reruns, so low export reflects the constrained solve rather than stale "
        "post-processing."
    ),
    "year1_revenue_usd": (
        "Scenario D adds DPPA top-up settlement to the base REopt avoided-cost savings."
    ),
    "equity_irr": (
        "Equity IRR is post-processed from REopt EBITDA through the debt schedule; it is not a "
        "native REopt output."
    ),
}


def _load_json(path: str | Path | None) -> dict | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) >= 8760:
        return list(series[:8760])
    return list(series) + [0.0] * (8760 - len(series))


def get_tariff_rate_levels(rates: list[float]) -> tuple[float, float, float] | None:
    unique_rates = sorted({round(r, 10) for r in rates})
    if len(unique_rates) < 3:
        return None
    return unique_rates[0], unique_rates[1], unique_rates[-1]


def classify_tariff_period(
    rate: float, rate_levels: tuple[float, float, float] | None
) -> str:
    if rate_levels is None:
        return "standard"

    offpeak, standard, peak = rate_levels
    rounded = round(rate, 10)
    if rounded == peak:
        return "peak"
    if rounded == offpeak:
        return "offpeak"
    if rounded == standard:
        return "standard"
    return "standard"


def split_series_by_tariff_period(
    series_kw: list[float], tou_rates_per_kwh: list[float]
) -> dict:
    series_kw = _pad_to_8760(series_kw)
    tou_rates_per_kwh = _pad_to_8760(tou_rates_per_kwh)
    rate_levels = get_tariff_rate_levels(tou_rates_per_kwh)

    buckets = {"peak": 0.0, "standard": 0.0, "offpeak": 0.0}
    for value, rate in zip(series_kw, tou_rates_per_kwh):
        period = classify_tariff_period(rate, rate_levels)
        buckets[period] += value
    return {key: value / 1_000.0 for key, value in buckets.items()}


def load_reopt_metrics(results: dict, scenario: dict | None = None) -> dict:
    pv = results.get("PV", {})
    storage = results.get("ElectricStorage", {})
    utility = results.get("ElectricUtility", {})
    fin = results.get("Financial", {})

    pv_gen_kwh = pv.get("year_one_energy_produced_kwh") or 0
    pv_export_kwh = pv.get("annual_energy_exported_kwh") or 0
    bess_to_load_series = storage.get("storage_to_load_series_kw", [])
    tariff_series = []
    if scenario:
        tariff_series = scenario.get("ElectricTariff", {}).get(
            "tou_energy_rates_per_kwh", []
        )

    tariff_split = (
        split_series_by_tariff_period(bess_to_load_series, tariff_series)
        if tariff_series
        else {
            "peak": None,
            "standard": None,
            "offpeak": None,
        }
    )

    return {
        "pv_gen_mwh": pv_gen_kwh / 1_000.0,
        "pv_to_load_mwh": (pv_gen_kwh - pv_export_kwh) / 1_000.0,
        "pv_to_grid_mwh": pv_export_kwh / 1_000.0,
        "bess_discharge_mwh": sum(bess_to_load_series) / 1_000.0,
        "bess_discharge_peak_mwh": tariff_split["peak"],
        "bess_discharge_standard_mwh": tariff_split["standard"],
        "bess_discharge_offpeak_mwh": tariff_split["offpeak"],
        "grid_purchases_mwh": (utility.get("annual_energy_supplied_kwh") or 0)
        / 1_000.0,
        "npv_usd": fin.get("npv") or 0.0,
        "payback_years": fin.get("simple_payback_years") or 0.0,
        "year1_revenue_usd": fin.get("year_one_total_operating_cost_savings_before_tax")
        or 0.0,
        "lcc": fin.get("lcc") or 0.0,
        "unlevered_irr": fin.get("internal_rate_of_return") or fin.get("irr") or 0.0,
    }


def apply_dppa_adjustments(
    metrics: dict, settlement: dict | None, equity: dict | None
) -> dict:
    adjusted = dict(metrics)
    if settlement:
        adjusted["year1_revenue_usd"] = adjusted.get(
            "year1_revenue_usd", 0.0
        ) + settlement.get("total_settlement_usd", 0.0)
        adjusted["npv_usd"] = adjusted.get("npv_usd", 0.0) + settlement.get(
            "settlement_npv_usd", 0.0
        )
        adjusted["dppa_settlement_usd"] = settlement.get("total_settlement_usd", 0.0)
        adjusted["dppa_delivery_mwh"] = settlement.get("total_q_mwh", 0.0)
        adjusted["dppa_contract_type"] = settlement.get("contract_type")
    if equity:
        adjusted["equity_irr"] = equity.get("equity_irr")
        adjusted["equity_npv_usd"] = equity.get("equity_npv_usd")
    return adjusted


def compare_metrics(reopt_metrics: dict, excel_targets: dict) -> list[dict]:
    rows = []
    for key, target_info in excel_targets.items():
        excel_val = target_info["value"]
        reopt_val = reopt_metrics.get(key)
        unit = target_info["unit"]
        tol = target_info["tolerance"]

        if reopt_val is None:
            delta_pct = None
            status = "MISSING"
        elif excel_val == 0:
            delta_pct = None
            status = "INFO"
        else:
            delta_pct = (reopt_val - excel_val) / abs(excel_val)
            if tol is None:
                status = "INFO"
            elif unit == "years" or unit == "fraction":
                status = "OK" if abs(reopt_val - excel_val) <= tol else "WARN"
            else:
                status = "OK" if abs(delta_pct) <= tol else "WARN"

        rows.append(
            {
                "metric": key,
                "unit": unit,
                "excel": excel_val,
                "reopt": reopt_val,
                "delta_pct": delta_pct,
                "tolerance": tol,
                "status": status,
            }
        )
    return rows


def _fmt(v, unit: str) -> str:
    if v is None:
        return "-"
    if unit == "years":
        return f"{v:.1f}"
    if unit == "USD":
        return f"${v:,.0f}"
    if unit == "MWh":
        return f"{v:,.0f}"
    if unit == "fraction":
        return f"{v:.1%}"
    return str(v)


def _fmt_delta(delta_pct) -> str:
    if delta_pct is None:
        return "-"
    return f"{delta_pct:+.1%}"


def generate_report(
    rows: list[dict],
    reopt_metrics: dict,
    scenario_label: str,
    output_path: Path,
) -> None:
    lines = [
        "# Saigon18 REopt vs. Excel Comparison Report",
        "",
        f"**Scenario:** {scenario_label}",
        "",
        "## Energy Metrics (Year 1)",
        "",
        "| Metric | Unit | Excel | REopt | Delta | Tol | Status |",
        "|---|---|---|---|---|---|---|",
    ]

    energy_keys = {
        "pv_gen_mwh",
        "pv_to_load_mwh",
        "pv_to_grid_mwh",
        "bess_discharge_mwh",
        "bess_discharge_peak_mwh",
        "bess_discharge_standard_mwh",
        "bess_discharge_offpeak_mwh",
        "grid_purchases_mwh",
    }
    fin_keys = {"npv_usd", "payback_years", "year1_revenue_usd", "equity_irr"}

    def add_rows(keys):
        for r in rows:
            if r["metric"] not in keys:
                continue
            if isinstance(r["tolerance"], float) and r["unit"] == "years":
                tol_str = f"+/-{r['tolerance']:.1f} yr"
            elif isinstance(r["tolerance"], float) and r["unit"] == "fraction":
                tol_str = f"+/-{r['tolerance']:.1%}"
            elif isinstance(r["tolerance"], float) and r["tolerance"] < 1:
                tol_str = f"+/-{r['tolerance']:.0%}"
            else:
                tol_str = "-"
            lines.append(
                f"| {r['metric']} | {r['unit']} | {_fmt(r['excel'], r['unit'])} | "
                f"{_fmt(r['reopt'], r['unit'])} | {_fmt_delta(r['delta_pct'])} | "
                f"{tol_str} | {r['status']} |"
            )

    add_rows(energy_keys)

    lines += [
        "",
        "## Financial Metrics",
        "",
        "| Metric | Unit | Excel | REopt | Delta | Notes | Status |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in rows:
        if r["metric"] not in fin_keys:
            continue
        note = DISCREPANCY_EXPLANATIONS.get(r["metric"], "")
        note = note[:80] + ("..." if len(note) > 80 else "")
        lines.append(
            f"| {r['metric']} | {r['unit']} | {_fmt(r['excel'], r['unit'])} | "
            f"{_fmt(r['reopt'], r['unit'])} | {_fmt_delta(r['delta_pct'])} | {note} | {r['status']} |"
        )

    lines += ["", "## Tariff-Period BESS Dispatch", ""]
    for key, label in (
        ("bess_discharge_peak_mwh", "Peak"),
        ("bess_discharge_standard_mwh", "Standard"),
        ("bess_discharge_offpeak_mwh", "Off-peak"),
    ):
        value = reopt_metrics.get(key)
        lines.append(f"- {label}: {_fmt(value, 'MWh')} MWh")

    if "dppa_settlement_usd" in reopt_metrics:
        lines += ["", "## Scenario D DPPA Adders", ""]
        lines.append(
            f"- Year-1 DPPA top-up settlement: {_fmt(reopt_metrics['dppa_settlement_usd'], 'USD')}"
        )
        lines.append(
            f"- DPPA delivery volume: {_fmt(reopt_metrics['dppa_delivery_mwh'], 'MWh')} MWh"
        )
        lines.append(
            f"- Contract type: {reopt_metrics.get('dppa_contract_type', 'unknown')}"
        )

    warn_rows = [r for r in rows if r["status"] == "WARN"]
    if warn_rows:
        lines += ["", "## Discrepancies Requiring Investigation", ""]
        for r in warn_rows:
            lines.append(f"### `{r['metric']}`")
            lines.append(
                f"- REopt: {_fmt(r['reopt'], r['unit'])}, Excel: {_fmt(r['excel'], r['unit'])}, Delta: {_fmt_delta(r['delta_pct'])}"
            )
            lines.append(
                f"- {DISCREPANCY_EXPLANATIONS.get(r['metric'], 'No specific explanation documented.')}"
            )
            lines.append("")

    lines += [
        "## REopt Additional Outputs",
        "",
        f"- LCC: ${reopt_metrics.get('lcc', 0):,.0f}",
    ]
    if reopt_metrics.get("unlevered_irr"):
        lines.append(f"- Unlevered IRR: {reopt_metrics['unlevered_irr']:.1%}")
    if reopt_metrics.get("equity_irr") is not None:
        lines.append(f"- Equity IRR: {reopt_metrics['equity_irr']:.1%}")
    lines += ["", "_Generated by compare_reopt_vs_excel.py_"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Comparison report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare REopt vs. Saigon18 Excel outputs"
    )
    parser.add_argument("--reopt", required=True, help="REopt results JSON file")
    parser.add_argument(
        "--scenario-json",
        help="Scenario JSON used to recover the EVN TOU schedule for tariff-period analysis",
    )
    parser.add_argument(
        "--settlement",
        help="Optional Scenario D DPPA settlement JSON",
    )
    parser.add_argument(
        "--equity",
        help="Optional equity IRR JSON for the scenario",
    )
    parser.add_argument(
        "--scenario",
        default="A",
        help="Scenario label for the report header",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/saigon18/2026-03-26_scenario-a_vs_excel_comparison.md",
        help="Output markdown report path",
    )
    args = parser.parse_args()

    results = _load_json(args.reopt)
    scenario = _load_json(args.scenario_json)
    settlement = _load_json(args.settlement)
    equity = _load_json(args.equity)

    if results is None:
        raise ValueError(f"Could not load REopt results JSON: {args.reopt}")

    reopt_metrics = load_reopt_metrics(results, scenario)
    reopt_metrics = apply_dppa_adjustments(reopt_metrics, settlement, equity)
    rows = compare_metrics(reopt_metrics, EXCEL_TARGETS)

    warn_count = sum(1 for r in rows if r["status"] == "WARN")
    ok_count = sum(1 for r in rows if r["status"] == "OK")
    print(
        f"\nComparison: {ok_count} OK, {warn_count} WARN, "
        f"{sum(1 for r in rows if r['status'] == 'MISSING')} MISSING"
    )

    for r in rows:
        status_sym = {"OK": "OK", "WARN": "!", "MISSING": "?", "INFO": "i"}.get(
            r["status"], " "
        )
        print(
            f"  [{status_sym}] {r['metric']:25s}  "
            f"Excel={_fmt(r['excel'], r['unit']):>12}  "
            f"REopt={_fmt(r['reopt'], r['unit']):>12}  "
            f"delta={_fmt_delta(r['delta_pct']):>8}"
        )

    generate_report(rows, reopt_metrics, args.scenario, Path(args.output))


if __name__ == "__main__":
    main()
