"""PHASE-05: the generic Vietnamese DPPA fallback orchestrator.

Any unregistered ``case`` now routes through ``build_generic_offsite_artifact``
instead of erroring. The flat deterministic fixture makes every expected value
an exact integer, so assertions use ``==``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.analysis import offsite_dppa as od
from reopt_pysam_vn.analysis.offsite_dppa import OrchestratorInputError, run_offsite_dppa
from reopt_pysam_vn.analysis.orchestrators.generic_vn_dppa import (
    build_generic_generation_profile,
    build_generic_offsite_artifact,
)
from reopt_pysam_vn.analysis.types import DealConfig, OffsiteDppaResult

_HOURS = 8760


def _extracted(generation_kw=None, loads_kw=None):
    return {
        "loads_kw": [1000.0] * _HOURS if loads_kw is None else loads_kw,
        "generation_kw": [500.0] * _HOURS if generation_kw is None else generation_kw,
        "evn_tariff": {"tou_energy_rates_vnd_per_kwh": [2000.0] * _HOURS},
        "benchmark": {
            "weighted_evn_price_vnd_per_kwh": 2000.0,
            "wholesale_rate_vnd_per_kwh": 671.0,
        },
    }


def _deal(case="SOME_NEW_DEAL", **contract):
    return DealConfig.from_dict(
        {"case": case, "mode": "offsite_dppa", "contract": contract}
    )


def _artifact(**kwargs):
    return build_generic_offsite_artifact(
        _extracted(),
        deal_config=_deal(**kwargs),
    )


def test_annual_summary_numbers_are_exact():
    annual = _artifact(settlement_mechanism="physical", strike_vnd_per_kwh=1200.0)[
        "base_settlement"
    ]["annual_summary"]
    assert annual["matched_mwh"] == 4380.0
    assert annual["buyer_cost_vnd"] == 14_016_000_000.0
    assert annual["buyer_blended_rate_vnd_kwh"] == 1600.0
    assert annual["developer_revenue_vnd"] == 5_256_000_000.0
    assert annual["buyer_savings_vs_evn_vnd"] == 3_504_000_000.0


def test_quality_block_flags_directional_and_sources():
    quality = _artifact(settlement_mechanism="physical", strike_vnd_per_kwh=1200.0)["quality"]
    assert quality["orchestrator"] == "generic_vn_dppa"
    assert quality["basis"] == "directional"
    assert quality["market_reference_price_type"] == "proxy_cfmp_or_fmp"
    assert quality["solar_profile_source"] == "extracted_generation_kw"


def test_strike_sweep_spans_0_6_to_1_4_strike_in_21_steps():
    sweep = _artifact(settlement_mechanism="physical", strike_vnd_per_kwh=1200.0)[
        "strike_sweep"
    ]["sweep"]
    assert len(sweep) == 21
    assert sweep[0]["strike_vnd_kwh"] == 720.0
    assert sweep[-1]["strike_vnd_kwh"] == 1680.0


def test_excess_generation_exports_at_surplus_up_to_cap():
    extracted = _extracted(generation_kw=[1500.0] * _HOURS)
    result = build_generic_offsite_artifact(
        extracted,
        deal_config=_deal(
            settlement_mechanism="physical",
            strike_vnd_per_kwh=1200.0,
            regime_id="decision_963_2026_current",
        ),
    )
    annual = result["base_settlement"]["annual_summary"]
    assert annual["matched_mwh"] == 8760.0
    assert annual["excess_mwh"] == 4380.0
    assert annual["exported_mwh"] == 4380.0
    assert annual["curtailed_mwh"] == 0.0


def test_wrong_length_load_raises_orchestrator_input_error():
    with pytest.raises(OrchestratorInputError, match="8760"):
        build_generic_offsite_artifact(
            _extracted(loads_kw=[1000.0] * 8000),
            deal_config=_deal(settlement_mechanism="physical", strike_vnd_per_kwh=1200.0),
        )


def test_registry_fallback_routes_unregistered_case_to_generic():
    result = run_offsite_dppa(_deal(), extracted=_extracted())
    assert isinstance(result, OffsiteDppaResult)
    assert result.case == "SOME_NEW_DEAL"
    assert result.quality["orchestrator"] == "generic_vn_dppa"


def test_registered_case_still_wins_over_generic(monkeypatch):
    def _stub(extracted, *, run_developer=True):
        return {
            "case": "REGISTERED_WINS",
            "model": "stub",
            "deal": {},
            "base_settlement": {},
            "strike_sweep": {},
            "adder_sensitivity": {},
            "regime_stress": {},
            "decision": {},
            "quality": {"basis": "bespoke"},
        }

    od.register_orchestrator("REGISTERED_WINS", _stub)
    result = run_offsite_dppa(
        DealConfig.from_dict({"case": "REGISTERED_WINS", "mode": "offsite_dppa"}),
        extracted=_extracted(),
    )
    assert result.quality.get("orchestrator") != "generic_vn_dppa"
    assert result.quality["basis"] == "bespoke"


def test_generation_profile_prefers_explicit_series():
    profile = build_generic_generation_profile(_extracted(), _deal())
    assert profile["source"] == "extracted_generation_kw"
    assert len(profile["series_kw"]) == _HOURS
    assert profile["calibrated_to_gwh"] is None


def test_generation_profile_calibrates_to_annual_solar_gwh():
    profile = build_generic_generation_profile(
        _extracted(),
        _deal(settlement_mechanism="physical", annual_solar_gwh=8.76),
    )
    assert profile["calibrated_to_gwh"] == 8.76
    assert sum(profile["series_kw"]) == pytest.approx(8.76e6, rel=1e-6)
