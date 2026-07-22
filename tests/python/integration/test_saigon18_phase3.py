"""
Regression tests for the Saigon18 Phase 3 completion workflow.

These tests lock the Scenario D post-processing and tariff-period comparison
behavior against the canonical local result artifacts.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python" / "reopt"))

from compare_reopt_vs_excel import apply_dppa_adjustments, load_reopt_metrics  # noqa: E402
from dppa_settlement import (  # noqa: E402
    compute_dppa_annual_revenue,
    load_reopt_delivery_profile,
    normalize_fmp_vnd_per_kwh,
    project_dppa_cashflows,
)

pytestmark = pytest.mark.requires_artifacts

SCENARIO_A_RESULTS = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "saigon18"
    / "2026-03-23_scenario-a_fixed-sizing_evntou_reopt-results.json"
)

SCENARIO_A_JSON = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "saigon18"
    / "2026-03-20_scenario-a_fixed-sizing_evntou.json"
)

EXTRACTED_INPUTS = (
    REPO_ROOT
    / "data"
    / "interim"
    / "saigon18"
    / "2026-03-20_saigon18_extracted_inputs.json"
)


def test_load_reopt_delivery_profile_uses_actual_results_schema():
    results = json.loads(SCENARIO_A_RESULTS.read_text(encoding="utf-8"))

    delivery = load_reopt_delivery_profile(results)

    assert len(delivery) == 8760
    assert sum(delivery) > 60_000_000


def test_load_reopt_metrics_splits_bess_dispatch_by_tariff_period():
    results = json.loads(SCENARIO_A_RESULTS.read_text(encoding="utf-8"))
    scenario = json.loads(SCENARIO_A_JSON.read_text(encoding="utf-8"))

    metrics = load_reopt_metrics(results, scenario)

    total = metrics["bess_discharge_mwh"]
    split_total = (
        (metrics["bess_discharge_peak_mwh"] or 0)
        + (metrics["bess_discharge_standard_mwh"] or 0)
        + (metrics["bess_discharge_offpeak_mwh"] or 0)
    )

    assert abs(split_total - total) < 1e-9
    assert metrics["bess_discharge_peak_mwh"] > 0
    assert metrics["bess_discharge_standard_mwh"] > 0


def test_scenario_d_adjustment_adds_settlement_to_revenue_and_npv():
    results = json.loads(SCENARIO_A_RESULTS.read_text(encoding="utf-8"))
    scenario = json.loads(SCENARIO_A_JSON.read_text(encoding="utf-8"))
    extracted = json.loads(EXTRACTED_INPUTS.read_text(encoding="utf-8"))

    metrics = load_reopt_metrics(results, scenario)
    delivery = load_reopt_delivery_profile(results)
    fmp_vnd_per_kwh, _ = normalize_fmp_vnd_per_kwh(extracted["fmp_vnd_per_mwh"])
    settlement = compute_dppa_annual_revenue(
        q_delivered_kw=delivery,
        fmp_vnd_per_kwh=fmp_vnd_per_kwh,
        strike_price_vnd_per_kwh=1800.0,
    )
    settlement.update(project_dppa_cashflows(settlement["total_settlement_usd"]))

    adjusted = apply_dppa_adjustments(metrics, settlement, None)

    assert adjusted["year1_revenue_usd"] > metrics["year1_revenue_usd"]
    assert adjusted["npv_usd"] > metrics["npv_usd"]
    assert adjusted["dppa_settlement_usd"] == settlement["total_settlement_usd"]
