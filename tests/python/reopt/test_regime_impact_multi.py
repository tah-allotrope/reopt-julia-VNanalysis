"""PHASE-03 tests for multi-regime comparison and forward-regime presets (GAP-05).

Run: pytest tests/python/reopt/test_regime_impact_multi.py -q
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.preprocess import load_vietnam_data
from reopt_pysam_vn.reopt.regime_impact import (
    FORWARD_REGIME_PRESETS,
    RegimeImpact,
    compute_multi_regime_impact,
    compute_regime_impact,
)

CUSTOMER_TYPE = "industrial"
VOLTAGE = "medium_voltage_22kv_to_110kv"

SAIGON18_SCENARIO = (
    REPO_ROOT / "scenarios" / "case_studies" / "saigon18"
    / "2026-03-20_scenario-a_fixed-sizing_evntou.json"
)


@pytest.fixture(scope="module")
def vn():
    return load_vietnam_data()


@pytest.fixture(scope="module")
def saigon18_loads():
    with open(SAIGON18_SCENARIO, encoding="utf-8") as f:
        d = json.load(f)
    return d["ElectricLoad"]["loads_kw"]

def test_multi_regime_returns_one_result_per_id(saigon18_loads, vn):
    regime_ids = [
        "decision_963_2026_current",
        "decision_14_2025_legacy",
        "decree146_two_part_trial_2026",
    ]
    results = compute_multi_regime_impact(
        saigon18_loads, regime_ids, CUSTOMER_TYPE, VOLTAGE, vn=vn, year=2026
    )
    assert isinstance(results, list)
    assert len(results) == 3
    assert all(isinstance(r, RegimeImpact) for r in results)


def test_multi_regime_baseline_is_first_id(saigon18_loads, vn):
    regime_ids = [
        "decision_963_2026_current",
        "decision_14_2025_legacy",
        "decree146_two_part_trial_2026",
    ]
    results = compute_multi_regime_impact(
        saigon18_loads, regime_ids, CUSTOMER_TYPE, VOLTAGE, vn=vn, year=2026
    )
    # Every result compares the baseline (first id) against one regime.
    assert all(r.regime_a.id == regime_ids[0] for r in results)
    assert [r.regime_b.id for r in results] == regime_ids
    # Baseline vs itself => zero delta.
    assert results[0].delta.annual_bill_delta_vnd == pytest.approx(0.0, abs=1e-6)
    # Decree-146 two-part trial adds a demand charge => higher bill.
    assert results[2].delta.annual_bill_delta_vnd > 0


def test_requires_at_least_two_regimes(saigon18_loads, vn):
    with pytest.raises(ValueError):
        compute_multi_regime_impact(
            saigon18_loads, ["decision_963_2026_current"], CUSTOMER_TYPE, VOLTAGE, vn=vn
        )


def test_forward_regime_presets_exposed():
    for rid in (
        "decree57_rooftop_50pct_draft",
        "decree146_two_part_trial_2026",
        "decision_963_2026_repriced_multipliers",
    ):
        assert rid in FORWARD_REGIME_PRESETS


def test_forward_regime_presets_produce_valid_results(saigon18_loads, vn):
    for rid in FORWARD_REGIME_PRESETS:
        impact = compute_regime_impact(
            saigon18_loads,
            "decision_963_2026_current",
            rid,
            CUSTOMER_TYPE,
            VOLTAGE,
            vn=vn,
            year=2026,
        )
        assert impact.regime_b.annual_bill_vnd > 0
        assert impact.regime_b.id == rid
