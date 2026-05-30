"""PHASE-01 tests for the rapid regulatory-regime bill comparison (GAP-05).

Covers `compute_regime_impact()` from `reopt_pysam_vn.reopt.regime_impact`:
Python-only EVN bill comparison between two regulatory regimes, no Julia solve.

Run: pytest tests/python/reopt/test_regime_impact.py -q
"""

import json
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.regime_impact import (  # noqa: E402
    RegimeImpact,
    compute_regime_impact,
)

DECISION_963 = "decision_963_2026_current"
DECISION_14 = "decision_14_2025_legacy"
CUSTOMER_TYPE = "industrial"
VOLTAGE = "medium_voltage_22kv_to_110kv"

SAIGON18_SCENARIO = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "saigon18"
    / "2026-03-20_scenario-a_fixed-sizing_evntou.json"
)


@pytest.fixture(scope="module")
def saigon18_loads():
    with open(SAIGON18_SCENARIO, "r", encoding="utf-8") as f:
        d = json.load(f)
    loads = d["ElectricLoad"]["loads_kw"]
    assert len(loads) == 8760
    return loads


@pytest.fixture(scope="module")
def flat_loads():
    return [1000.0] * 8760


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


def test_returns_regime_impact_with_expected_structure(saigon18_loads):
    impact = compute_regime_impact(
        saigon18_loads, DECISION_963, DECISION_14, CUSTOMER_TYPE, VOLTAGE
    )
    assert isinstance(impact, RegimeImpact)

    for side in (impact.regime_a, impact.regime_b):
        assert side.id
        assert side.name
        assert side.annual_bill_vnd > 0
        assert side.peak_consumption_mwh >= 0
        assert side.offpeak_consumption_mwh >= 0
        assert side.normal_consumption_mwh >= 0

    # regime_a is the first id passed
    assert impact.regime_a.id == DECISION_963
    assert impact.regime_b.id == DECISION_14
    assert impact.customer_type == CUSTOMER_TYPE
    assert impact.voltage_level == VOLTAGE
    assert impact.analysis_timestamp

    # Consumption buckets must sum to total annual consumption (MWh) per side.
    total_mwh = sum(saigon18_loads) / 1000.0
    for side in (impact.regime_a, impact.regime_b):
        bucket_sum = (
            side.peak_consumption_mwh
            + side.offpeak_consumption_mwh
            + side.normal_consumption_mwh
        )
        assert bucket_sum == pytest.approx(total_mwh, rel=1e-6)


# ---------------------------------------------------------------------------
# Exit criteria
# ---------------------------------------------------------------------------


def test_saigon18_963_vs_14_has_nonzero_bill_delta(saigon18_loads):
    impact = compute_regime_impact(
        saigon18_loads, DECISION_963, DECISION_14, CUSTOMER_TYPE, VOLTAGE
    )
    assert impact.delta.annual_bill_delta_vnd != 0
    assert impact.delta.delta_pct != 0


def test_peak_hours_changed_reflects_window_shift(saigon18_loads):
    # Decision 14 weekday peak = {9,10,17,18,19}; Decision 963 = {17..22}.
    # Symmetric difference = {9,10,20,21,22} -> 5 hours changed.
    impact = compute_regime_impact(
        saigon18_loads, DECISION_963, DECISION_14, CUSTOMER_TYPE, VOLTAGE
    )
    assert impact.delta.peak_hours_changed == 5


def test_peak_consumption_shifts_between_regimes(saigon18_loads):
    impact = compute_regime_impact(
        saigon18_loads, DECISION_963, DECISION_14, CUSTOMER_TYPE, VOLTAGE
    )
    # Peak-hour windows differ, so peak-classified consumption must differ.
    assert impact.regime_a.peak_consumption_mwh != impact.regime_b.peak_consumption_mwh
    assert impact.delta.peak_consumption_delta_mwh != 0


def test_same_regime_yields_zero_delta(saigon18_loads):
    impact = compute_regime_impact(
        saigon18_loads, DECISION_963, DECISION_963, CUSTOMER_TYPE, VOLTAGE
    )
    assert impact.delta.annual_bill_delta_vnd == pytest.approx(0.0, abs=1e-6)
    assert impact.delta.delta_pct == pytest.approx(0.0, abs=1e-9)
    assert impact.delta.peak_hours_changed == 0
    assert impact.delta.peak_consumption_delta_mwh == pytest.approx(0.0, abs=1e-6)


def test_flat_load_change_smaller_than_peaky_load():
    """A flat load is less sensitive to a peak-window reshuffle than a peaky load."""
    flat = [1000.0] * 8760
    # Peaky load: heavy consumption only during Decision-14 morning peak (09:00-10:59).
    peaky = []
    for h in range(8760):
        hour = h % 24
        peaky.append(5000.0 if hour in (9, 10) else 200.0)

    flat_impact = compute_regime_impact(
        flat, DECISION_963, DECISION_14, CUSTOMER_TYPE, VOLTAGE
    )
    peaky_impact = compute_regime_impact(
        peaky, DECISION_963, DECISION_14, CUSTOMER_TYPE, VOLTAGE
    )
    assert abs(flat_impact.delta.delta_pct) < abs(peaky_impact.delta.delta_pct)


def test_runs_under_one_second(saigon18_loads):
    start = time.perf_counter()
    compute_regime_impact(
        saigon18_loads, DECISION_963, DECISION_14, CUSTOMER_TYPE, VOLTAGE
    )
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"compute_regime_impact took {elapsed:.3f}s (> 1s budget)"
