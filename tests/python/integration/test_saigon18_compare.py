"""
Regression tests for Saigon18 REopt comparison metric extraction.

These tests lock the expected key mapping against the actual local REopt
results schema used by the Saigon18 analysis scripts.

Run: pytest tests/python/integration/test_saigon18_compare.py -v
"""

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python" / "reopt"))

from compare_reopt_vs_excel import load_reopt_metrics  # noqa: E402


RESULTS_PATH = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "saigon18"
    / "2026-03-23_scenario-a_fixed-sizing_evntou_reopt-results.json"
)


def test_load_reopt_metrics_uses_actual_results_keys():
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    pv = results["PV"]
    storage = results["ElectricStorage"]
    utility = results["ElectricUtility"]
    fin = results["Financial"]

    metrics = load_reopt_metrics(results)

    assert metrics["pv_gen_mwh"] == pv["year_one_energy_produced_kwh"] / 1_000
    assert (
        metrics["pv_to_load_mwh"]
        == (pv["year_one_energy_produced_kwh"] - pv["annual_energy_exported_kwh"])
        / 1_000
    )
    assert metrics["pv_to_grid_mwh"] == pv["annual_energy_exported_kwh"] / 1_000
    assert (
        metrics["bess_discharge_mwh"]
        == sum(storage["storage_to_load_series_kw"]) / 1_000
    )
    assert (
        metrics["grid_purchases_mwh"] == utility["annual_energy_supplied_kwh"] / 1_000
    )
    assert (
        metrics["year1_revenue_usd"]
        == fin["year_one_total_operating_cost_savings_before_tax"]
    )
