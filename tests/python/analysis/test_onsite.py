"""PHASE-02: generalized onsite (BTM) pipeline.

`run_onsite` post-processes a (pre-solved or injected) REopt results dict into an
`OnsiteResult` — sizing, dispatch coverage, economics. The deterministic parity
target is the bespoke `calculate_ninhsim_coverage_summary`; run_onsite must
reproduce it EXACTLY on the same fixture (DEC-002 exact bucket), with no solver.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.analysis.onsite import run_onsite
from reopt_pysam_vn.analysis.types import DealConfig, OnsiteResult
from reopt_pysam_vn.integration.ninhsim_solar_storage_60pct import (
    calculate_ninhsim_coverage_summary,
)

_HOURS = 8760


def _fixture_results() -> dict:
    return {
        "PV": {
            "size_kw": 3000.0,
            "electric_to_load_series_kw": [100.0] * _HOURS,
            "electric_to_grid_series_kw": [10.0] * _HOURS,
        },
        "Wind": {"size_kw": 0.0, "electric_to_load_series_kw": [], "electric_to_grid_series_kw": []},
        "ElectricStorage": {
            "size_kw": 1000.0,
            "size_kwh": 2000.0,
            "storage_to_load_series_kw": [20.0] * _HOURS,
        },
        "ElectricUtility": {"electric_to_load_series_kw": [50.0] * _HOURS},
        "Financial": {
            "npv": 1_500_000.0,
            "lifecycle_capital_costs": 3_000_000.0,
            "year_one_bill_before_tax": 2_000_000.0,
        },
    }


def _fixture_extracted() -> dict:
    return {"loads_kw": [170.0] * _HOURS, "benchmark": {"weighted_evn_price_vnd_per_kwh": 2040.0}}


def _deal_config() -> DealConfig:
    return DealConfig.from_dict(
        {
            "case": "NINHSIM_ONSITE",
            "mode": "onsite",
            "contract": {"target_delivered_fraction": 0.6},
        }
    )


def test_run_onsite_returns_onsite_result():
    res = run_onsite(_deal_config(), results=_fixture_results(), extracted=_fixture_extracted())
    assert isinstance(res, OnsiteResult)
    assert res.case == "NINHSIM_ONSITE"


def test_run_onsite_sizing_pulled_from_results():
    res = run_onsite(_deal_config(), results=_fixture_results(), extracted=_fixture_extracted())
    assert res.sizing["pv_kw"] == 3000.0
    assert res.sizing["bess_power_kw"] == 1000.0
    assert res.sizing["bess_energy_kwh"] == 2000.0


def test_run_onsite_dispatch_matches_ninhsim_coverage_exactly():
    results, extracted = _fixture_results(), _fixture_extracted()
    res = run_onsite(_deal_config(), results=results, extracted=extracted, target_fraction=0.6)
    cov = calculate_ninhsim_coverage_summary(results, extracted, target_fraction=0.6)
    for key in (
        "renewable_delivered_kwh",
        "exported_renewable_kwh",
        "sold_renewable_kwh",
        "grid_supplied_kwh",
        "total_load_kwh",
        "achieved_delivered_fraction_of_load",
    ):
        assert res.dispatch[key] == cov[key], f"coverage parity mismatch on {key}"


def test_run_onsite_economics_from_financial_block():
    res = run_onsite(_deal_config(), results=_fixture_results(), extracted=_fixture_extracted())
    assert res.economics["npv"] == 1_500_000.0
    assert res.economics["lifecycle_capital_costs"] == 3_000_000.0


def test_run_onsite_requires_solver_when_no_results():
    # No pre-solved results and no solve_fn → explicit error, never silently hits Julia.
    with pytest.raises(ValueError, match="solve"):
        run_onsite(_deal_config())


def test_build_onsite_scenario_carries_site_lat_long():
    # REopt's API rejects a Site with no coordinates; the webapp's live-solve
    # path depends on these making it into the scenario dict (PHASE-02).
    from reopt_pysam_vn.analysis.onsite import build_onsite_scenario

    deal = DealConfig.from_dict(
        {
            "case": "LATLONG_TEST",
            "mode": "onsite",
            "site": {
                "latitude": 10.9577,
                "longitude": 106.8426,
                "customer_type": "industrial",
                "region": "south",
                "voltage_level": "medium_voltage_22kv_to_110kv",
            },
            "plant": {"capacity_mwp": 2.0},
        }
    )
    scenario = build_onsite_scenario(deal)
    assert scenario["Site"]["latitude"] == pytest.approx(10.9577)
    assert scenario["Site"]["longitude"] == pytest.approx(106.8426)


def test_build_onsite_scenario_omits_lat_long_when_absent():
    from reopt_pysam_vn.analysis.onsite import build_onsite_scenario

    deal = DealConfig.from_dict(
        {
            "case": "NO_LATLONG",
            "mode": "onsite",
            "site": {
                "customer_type": "commercial",
                "region": "south",
                "voltage_level": "medium_voltage_22kv_to_110kv",
            },
        }
    )
    scenario = build_onsite_scenario(deal)
    assert "latitude" not in scenario["Site"]
    assert "longitude" not in scenario["Site"]
