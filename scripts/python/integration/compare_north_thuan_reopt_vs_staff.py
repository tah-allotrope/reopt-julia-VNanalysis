"""
Compare North Thuan REopt outputs against the staff feasibility-study claims.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python"))

from dppa_settlement import compute_virtual_dppa_developer_revenue
from validate_north_thuan import STAFF_CLAIMS, TOLERANCE_PCT, compare_result

REOPT_TARGET_KEYS = [
    "solar_gwh_yr1",
    "wind_gwh_yr1",
    "total_gen_gwh_yr1",
    "matched_gwh_yr1",
    "re_penetration_pct",
    "self_consumption_pct",
    "factory_npv_usd",
]

STAFF_SETTLEMENT_REVENUE_USD = 6_000_000.0
SETTLEMENT_TOLERANCE_PCT = 15.0


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) >= 8760:
        return list(series[:8760])
    return list(series) + [0.0] * (8760 - len(series))


def _series_total(series_kw: list[float]) -> float:
    return sum(_pad_to_8760(series_kw))


def _tech_generation_series(tech_results: dict) -> list[float]:
    to_load = _pad_to_8760(tech_results.get("electric_to_load_series_kw", []))
    to_storage = _pad_to_8760(tech_results.get("electric_to_storage_series_kw", []))
    to_grid = _pad_to_8760(tech_results.get("electric_to_grid_series_kw", []))
    curtailed = _pad_to_8760(tech_results.get("electric_curtailed_series_kw", []))

    if any(to_load) or any(to_storage) or any(to_grid) or any(curtailed):
        return [
            to_load_kw + to_storage_kw + to_grid_kw + curtailed_kw
            for to_load_kw, to_storage_kw, to_grid_kw, curtailed_kw in zip(
                to_load, to_storage, to_grid, curtailed
            )
        ]

    annual_kwh = (
        tech_results.get("year_one_energy_produced_kwh")
        or tech_results.get("annual_energy_produced_kwh")
        or 0.0
    )
    return [annual_kwh / 8760.0] * 8760


def extract_scenario_metrics(results: dict, extracted: dict) -> dict:
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    storage = results.get("ElectricStorage", {})
    utility = results.get("ElectricUtility", {})
    financial = results.get("Financial", {})

    pv_gen_kwh = float(
        pv.get("year_one_energy_produced_kwh")
        or pv.get("annual_energy_produced_kwh")
        or 0.0
    )
    wind_gen_kwh = float(
        wind.get("year_one_energy_produced_kwh")
        or wind.get("annual_energy_produced_kwh")
        or 0.0
    )
    total_gen_kwh = pv_gen_kwh + wind_gen_kwh
    load_kwh = float(sum(extracted.get("loads_kw", [])))

    pv_to_load_series = _pad_to_8760(pv.get("electric_to_load_series_kw", []))
    wind_to_load_series = _pad_to_8760(wind.get("electric_to_load_series_kw", []))
    storage_to_load_series = _pad_to_8760(storage.get("storage_to_load_series_kw", []))
    grid_to_load_series = _pad_to_8760(utility.get("electric_to_load_series_kw", []))

    matched_series = [
        pv_kw + wind_kw + storage_kw
        for pv_kw, wind_kw, storage_kw in zip(
            pv_to_load_series, wind_to_load_series, storage_to_load_series
        )
    ]
    generation_series = [
        pv_kw + wind_kw
        for pv_kw, wind_kw in zip(
            _tech_generation_series(pv), _tech_generation_series(wind)
        )
    ]

    matched_kwh = sum(matched_series)
    re_penetration_pct = (total_gen_kwh / load_kwh * 100.0) if load_kwh else 0.0
    self_consumption_pct = (
        (matched_kwh / total_gen_kwh * 100.0) if total_gen_kwh else 0.0
    )
    factory_savings_yr1 = float(
        financial.get("year_one_total_operating_cost_savings_before_tax") or 0.0
    )

    return {
        "status": results.get("status", "unknown"),
        "solar_gwh_yr1": pv_gen_kwh / 1_000_000.0,
        "wind_gwh_yr1": wind_gen_kwh / 1_000_000.0,
        "total_gen_gwh_yr1": total_gen_kwh / 1_000_000.0,
        "matched_gwh_yr1": matched_kwh / 1_000_000.0,
        "re_penetration_pct": re_penetration_pct,
        "self_consumption_pct": self_consumption_pct,
        "factory_npv_usd": float(financial.get("npv") or 0.0),
        "factory_gross_saving_yr1_usd": factory_savings_yr1,
        "grid_to_load_gwh_yr1": sum(grid_to_load_series) / 1_000_000.0,
        "pv_size_mw": float(pv.get("size_kw") or 0.0) / 1_000.0,
        "wind_size_mw": float(wind.get("size_kw") or 0.0) / 1_000.0,
        "bess_mw": float(storage.get("size_kw") or 0.0) / 1_000.0,
        "bess_mwh": float(storage.get("size_kwh") or 0.0) / 1_000.0,
        "simple_payback_years": float(financial.get("simple_payback_years") or 0.0),
        "matched_series_kw": matched_series,
        "generation_series_kw": generation_series,
    }


def build_staff_comparison(metrics: dict) -> list[dict]:
    rows = []
    for key in REOPT_TARGET_KEYS:
        rows.append(compare_result(key, float(metrics[key]), float(STAFF_CLAIMS[key])))
    return rows


def build_settlement_check(metrics: dict, extracted: dict) -> dict:
    strike_price = extracted["assumptions"]["dppa_strike_usd_per_kwh"]
    settlement = compute_virtual_dppa_developer_revenue(
        matched_series_kw=metrics["matched_series_kw"],
        generation_series_kw=metrics["generation_series_kw"],
        strike_price_usd_per_kwh=strike_price,
        fmp_usd_per_kwh=extracted.get("fmp_usd_per_kwh", []),
    )
    delta_pct = (
        (settlement["developer_revenue_yr1_usd"] - STAFF_SETTLEMENT_REVENUE_USD)
        / STAFF_SETTLEMENT_REVENUE_USD
        * 100.0
    )
    settlement["staff_revenue_yr1_usd"] = STAFF_SETTLEMENT_REVENUE_USD
    settlement["delta_pct"] = round(delta_pct, 1)
    settlement["status"] = (
        "OK" if abs(delta_pct) <= SETTLEMENT_TOLERANCE_PCT else "WARN"
    )
    return settlement


def _strip_large_series(metrics: dict) -> dict:
    clean = dict(metrics)
    clean.pop("matched_series_kw", None)
    clean.pop("generation_series_kw", None)
    return clean


def _optional_metrics(path: str | None, extracted: dict) -> dict | None:
    if not path:
        return None
    results_path = Path(path)
    if not results_path.exists():
        return None
    results = json.loads(results_path.read_text(encoding="utf-8"))
    return _strip_large_series(extract_scenario_metrics(results, extracted))


def build_summary(scenario_a_rows: list[dict], settlement_check: dict) -> dict:
    total_rows = list(scenario_a_rows) + [{"status": settlement_check["status"]}]
    ok = sum(1 for row in total_rows if row["status"] == "OK")
    warn = sum(1 for row in total_rows if row["status"] == "WARN")
    return {
        "ok": ok,
        "warn": warn,
        "total": len(total_rows),
        "tolerance_pct": TOLERANCE_PCT,
        "settlement_tolerance_pct": SETTLEMENT_TOLERANCE_PCT,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare North Thuan REopt outputs against staff claims"
    )
    parser.add_argument(
        "--extracted",
        default="data/interim/north_thuan/north_thuan_extracted_inputs.json",
        help="Extracted North Thuan inputs JSON",
    )
    parser.add_argument(
        "--reopt-a",
        default="artifacts/results/north_thuan/north_thuan_scenario_a_reopt-results.json",
        help="Scenario A REopt results path",
    )
    parser.add_argument(
        "--reopt-b",
        default="artifacts/results/north_thuan/north_thuan_scenario_b_reopt-results.json",
        help="Scenario B REopt results path",
    )
    parser.add_argument(
        "--reopt-c",
        default="artifacts/results/north_thuan/north_thuan_scenario_c_reopt-results.json",
        help="Scenario C REopt results path",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/north_thuan/2026-03-31_north-thuan-reopt-validation.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    extracted = json.loads(Path(args.extracted).read_text(encoding="utf-8"))
    scenario_a_results = json.loads(Path(args.reopt_a).read_text(encoding="utf-8"))
    scenario_a_metrics_full = extract_scenario_metrics(scenario_a_results, extracted)
    scenario_a_metrics = _strip_large_series(scenario_a_metrics_full)
    scenario_a_comparison = build_staff_comparison(scenario_a_metrics_full)
    settlement_check = build_settlement_check(scenario_a_metrics_full, extracted)

    scenario_b_metrics = _optional_metrics(args.reopt_b, extracted)
    scenario_c_metrics = _optional_metrics(args.reopt_c, extracted)

    sizing_sensitivity = {
        "fixed_case": {
            "pv_size_mw": scenario_a_metrics["pv_size_mw"],
            "wind_size_mw": scenario_a_metrics["wind_size_mw"],
            "bess_mw": scenario_a_metrics["bess_mw"],
            "bess_mwh": scenario_a_metrics["bess_mwh"],
            "factory_npv_usd": scenario_a_metrics["factory_npv_usd"],
        },
        "optimized_case": scenario_b_metrics,
        "no_bess_case": scenario_c_metrics,
    }

    output = {
        "project": "North Thuan Wind+Solar+BESS REopt Validation",
        "generated_on": "2026-03-31",
        "staff_targets": {key: STAFF_CLAIMS[key] for key in REOPT_TARGET_KEYS},
        "scenario_a": {
            "metrics": scenario_a_metrics,
            "comparison": scenario_a_comparison,
        },
        "scenario_b": None
        if scenario_b_metrics is None
        else {"metrics": scenario_b_metrics},
        "scenario_c": None
        if scenario_c_metrics is None
        else {"metrics": scenario_c_metrics},
        "sizing_sensitivity": sizing_sensitivity,
        "settlement_check": settlement_check,
        "summary": build_summary(scenario_a_comparison, settlement_check),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"North Thuan REopt comparison written to: {output_path}")
    print(
        f"  Summary: {output['summary']['ok']} OK | {output['summary']['warn']} WARN | {output['summary']['total']} checks"
    )
    print(
        f"  Scenario A matched volume : {scenario_a_metrics['matched_gwh_yr1']:.2f} GWh/year"
    )
    print(
        f"  DPPA developer revenue    : ${settlement_check['developer_revenue_yr1_usd']:,.0f}/year"
    )


if __name__ == "__main__":
    main()
