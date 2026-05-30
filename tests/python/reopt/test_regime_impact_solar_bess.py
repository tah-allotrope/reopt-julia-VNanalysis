"""PHASE-02 tests for solar/BESS value impact and the combined artifact (GAP-05).

Covers `estimate_solar_value_impact()`, `estimate_bess_arbitrage_impact()`, and
`build_regime_comparison()` from `reopt_pysam_vn.reopt.regime_impact`.

Run: pytest tests/python/reopt/test_regime_impact_solar_bess.py -q
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.regime_impact import (  # noqa: E402
    BessArbitrageDelta,
    RegimeComparisonArtifact,
    SolarValueDelta,
    build_regime_comparison,
    estimate_bess_arbitrage_impact,
    estimate_solar_value_impact,
    regime_tou_rates_vnd,
)
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data  # noqa: E402

DECISION_963 = "decision_963_2026_current"
DECISION_14 = "decision_14_2025_legacy"
CUSTOMER_TYPE = "industrial"
VOLTAGE = "medium_voltage_22kv_to_110kv"


@pytest.fixture(scope="module")
def vn():
    return load_vietnam_data()


@pytest.fixture(scope="module")
def rates_963(vn):
    return regime_tou_rates_vnd(vn, CUSTOMER_TYPE, VOLTAGE, DECISION_963, year=2026)


@pytest.fixture(scope="module")
def rates_14(vn):
    return regime_tou_rates_vnd(vn, CUSTOMER_TYPE, VOLTAGE, DECISION_14, year=2026)


@pytest.fixture(scope="module")
def daytime_pv():
    """A daytime PV profile that generates 7:00-16:59, including the Decision-14
    morning peak hours (09:00-10:59)."""
    pv = []
    for h in range(8760):
        hour = h % 24
        pv.append(1000.0 if 7 <= hour <= 16 else 0.0)
    return pv


@pytest.fixture(scope="module")
def big_flat_load():
    return [9999.0] * 8760


# ---------------------------------------------------------------------------
# Solar value impact
# ---------------------------------------------------------------------------


def test_solar_value_lower_under_963_for_daytime_profile(
    daytime_pv, big_flat_load, rates_963, rates_14
):
    result = estimate_solar_value_impact(
        big_flat_load, rates_963, rates_14, daytime_pv
    )
    assert isinstance(result, SolarValueDelta)
    # Decision 14 prices the morning hours 09:00-10:59 as peak; Decision 963 does not.
    # A daytime PV profile therefore earns less avoided cost under Decision 963.
    assert result.regime_a_value_vnd < result.regime_b_value_vnd
    # delta is B - A; B(Decision 14) values daytime solar higher, so delta > 0.
    assert result.delta_value_vnd > 0
    assert result.pv_annual_generation_mwh == pytest.approx(
        sum(daytime_pv) / 1000.0, rel=1e-6
    )


# ---------------------------------------------------------------------------
# BESS arbitrage impact
# ---------------------------------------------------------------------------


def test_bess_cycles_reflect_distinct_peak_windows(rates_963, rates_14):
    result = estimate_bess_arbitrage_impact(rates_963, rates_14, 1000.0, 4000.0)
    assert isinstance(result, BessArbitrageDelta)
    # Decision 963: one evening peak window -> 1 cycle/day.
    # Decision 14: split morning + evening peaks -> 2 cycles/day.
    assert result.regime_a_cycles_per_day == 1
    assert result.regime_b_cycles_per_day == 2


def test_bess_arbitrage_963_about_half_of_14(rates_963, rates_14):
    result = estimate_bess_arbitrage_impact(rates_963, rates_14, 1000.0, 4000.0)
    assert result.regime_a_annual_arbitrage_vnd > 0
    assert result.regime_b_annual_arbitrage_vnd > 0
    ratio = (
        result.regime_a_annual_arbitrage_vnd / result.regime_b_annual_arbitrage_vnd
    )
    assert 0.4 < ratio < 0.6, f"963/14 arbitrage ratio {ratio:.3f} not ~0.5"


# ---------------------------------------------------------------------------
# Combined artifact
# ---------------------------------------------------------------------------


def test_build_regime_comparison_artifact_structure(daytime_pv, big_flat_load):
    artifact = build_regime_comparison(
        big_flat_load,
        DECISION_963,
        DECISION_14,
        CUSTOMER_TYPE,
        VOLTAGE,
        pv_profile_kw=daytime_pv,
        bess_power_kw=1000.0,
        bess_capacity_kwh=4000.0,
        year=2026,
    )
    assert isinstance(artifact, RegimeComparisonArtifact)
    assert artifact.regime_impact is not None
    assert artifact.solar is not None
    assert artifact.bess is not None

    d = artifact.to_dict()
    # Must be JSON-serializable.
    s = json.dumps(d)
    assert "regime_impact" in d
    assert "solar" in d
    assert "bess" in d
    assert d["regime_impact"]["delta"]["peak_hours_changed"] == 5
    assert isinstance(s, str)


def test_build_regime_comparison_without_optional_tech(big_flat_load):
    artifact = build_regime_comparison(
        big_flat_load,
        DECISION_963,
        DECISION_14,
        CUSTOMER_TYPE,
        VOLTAGE,
        year=2026,
    )
    assert artifact.solar is None
    assert artifact.bess is None
    # Core impact still present and serializable.
    d = artifact.to_dict()
    assert d["solar"] is None
    assert d["bess"] is None
    json.dumps(d)
