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
from reopt_pysam_vn.analysis.offsite_dppa import OrchestratorContext, OrchestratorInputError, run_offsite_dppa
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
        OrchestratorContext(deal_config=_deal(**kwargs)),
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
        OrchestratorContext(
            deal_config=_deal(
                settlement_mechanism="physical",
                strike_vnd_per_kwh=1200.0,
                regime_id="decision_963_2026_current",
            )
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
            OrchestratorContext(
                deal_config=_deal(settlement_mechanism="physical", strike_vnd_per_kwh=1200.0)
            ),
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


# ---------------------------------------------------------------------------
# PHASE-03: physical model honesty additions
# ---------------------------------------------------------------------------


def test_great_circle_km_known_distance():
    from reopt_pysam_vn.pysam.pvwatts_battery import great_circle_km

    d = great_circle_km(10.88, 106.28, 12.525729252783036, 109.02003383567742)
    # Plan's worked example cited 337.0 km; actual haversine at R=6371 gives ~350.0 km.
    assert 340.0 <= d <= 360.0


def test_great_circle_km_zero():
    from reopt_pysam_vn.pysam.pvwatts_battery import great_circle_km

    assert great_circle_km(
        12.525729252783036, 109.02003383567742, 12.525729252783036, 109.02003383567742
    ) == pytest.approx(0.0)


def test_resource_coordinates_known():
    from reopt_pysam_vn.pysam.pvwatts_battery import resource_coordinates

    assert resource_coordinates("ninhsim_himawari_2019_60min.csv") == (
        12.525729252783036,
        109.02003383567742,
    )


def test_resource_coordinates_unknown():
    from reopt_pysam_vn.pysam.pvwatts_battery import resource_coordinates

    assert resource_coordinates("does_not_exist.csv") is None


def _synthetic_day_night_shape():
    return [1.0 if 6 <= (h % 24) < 18 else 0.0 for h in range(_HOURS)]


def test_calibrate_to_target_night_injection_regression():
    from reopt_pysam_vn.analysis.orchestrators.generic_vn_dppa import _calibrate_to_target

    shape = _synthetic_day_night_shape()
    series, warnings = _calibrate_to_target(shape, annual_target_kwh=6.0e6, cap_kw=1000.0)
    assert len(series) == _HOURS
    for h, s in enumerate(shape):
        if s == 0.0:
            assert series[h] == 0.0, f"night injection at hour {h}"
    assert warnings
    assert any("infeasible" in w.lower() for w in warnings)


def test_calibrate_to_target_feasible_clipping():
    from reopt_pysam_vn.analysis.orchestrators.generic_vn_dppa import _calibrate_to_target

    shape = _synthetic_day_night_shape()
    series, _warnings = _calibrate_to_target(shape, annual_target_kwh=12.0e6, cap_kw=5000.0)
    assert sum(series) == pytest.approx(12.0e6, rel=1e-9, abs=1.0)
    assert max(series) <= 5000.0 + 1e-6
    for h, s in enumerate(shape):
        if s == 0.0:
            assert series[h] == 0.0


def test_calibrate_to_target_no_cap():
    from reopt_pysam_vn.analysis.orchestrators.generic_vn_dppa import _calibrate_to_target

    series, warnings = _calibrate_to_target([1.0] * _HOURS, annual_target_kwh=8760.0, cap_kw=None)
    assert all(v == pytest.approx(1.0) for v in series)
    assert warnings == []


def test_calibrate_to_target_all_zero_shape():
    from reopt_pysam_vn.analysis.orchestrators.generic_vn_dppa import _calibrate_to_target

    series, warnings = _calibrate_to_target([0.0] * _HOURS, 1.0e6, 1000.0)
    assert series == [0.0] * _HOURS
    assert any("entirely zero" in w for w in warnings)


def test_distance_disclosure_for_far_site():
    # When PySAM resolves the tracked resource, a site far from Ninh Thuan should be flagged.
    try:
        import PySAM  # noqa: F401
    except ImportError:
        pytest.skip("PySAM not available")
    from reopt_pysam_vn.analysis.orchestrators.generic_vn_dppa import build_generic_offsite_artifact
    from reopt_pysam_vn.analysis.types import DealConfig

    extracted = {
        "loads_kw": [1000.0] * _HOURS,
        "site": {"latitude": 10.03, "longitude": 105.78},
        "evn_tariff": {"tou_energy_rates_vnd_per_kwh": [2000.0] * _HOURS},
        "benchmark": {
            "weighted_evn_price_vnd_per_kwh": 2000.0,
            "wholesale_rate_vnd_per_kwh": 671.0,
        },
    }
    deal = DealConfig.from_dict(
        {
            "case": "FAR_SITE_TEST",
            "mode": "offsite_dppa",
            "site": {"latitude": 10.03, "longitude": 105.78},
            "plant": {"capacity_mwac": 5.0},
            "contract": {"strike_vnd_per_kwh": 1200.0, "annual_solar_gwh": 5.0},
            "load": {"loads_kw": [1000.0] * _HOURS},
        }
    )
    result = build_generic_offsite_artifact(extracted, OrchestratorContext(deal_config=deal))
    quality = result["quality"]
    # Only check when PVWatts actually ran; synthetic fallback has no distance.
    if quality.get("solar_resource_file") is None:
        pytest.skip("PVWatts resource not resolved, synthetic fallback")
    assert quality["solar_resource_distance_km"] is not None
    assert quality["solar_resource_distance_km"] > 100.0
    assert quality["solar_profile_source"] == "pvwatts_fallback_resource"
    assert any("solar resource" in w.lower() for w in quality["warnings"])


def test_array_config_mapping():
    from reopt_pysam_vn.analysis.orchestrators.generic_vn_dppa import _array_config

    cfg_roof = DealConfig.from_dict(
        {"case": "X", "mode": "offsite_dppa", "plant": {"mounting": "fixed_roof"}}
    )
    assert _array_config(cfg_roof, 10.5) == (1, 10.5)
    cfg_track = DealConfig.from_dict(
        {"case": "X", "mode": "offsite_dppa", "plant": {"mounting": "single_axis_tracking"}}
    )
    assert _array_config(cfg_track, 10.5) == (2, 0.0)
    cfg_default = DealConfig.from_dict({"case": "X", "mode": "offsite_dppa"})
    assert _array_config(cfg_default, 10.5) == (0, 10.5)
