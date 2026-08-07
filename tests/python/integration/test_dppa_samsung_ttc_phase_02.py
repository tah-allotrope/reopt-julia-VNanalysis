"""PHASE-02 tests: southern solar 8760, REopt-shaped results, buyer settlement.

The deal plant is fixed (49 MWp / 41.4 MWac), so a deterministic representative
southern-Vietnam solar profile (PySAM unavailable in this env) is calibrated to
the disclosed ~70 GWh/yr and fed through the reused Case-2 settlement engine with
the Samsung Southern-ceiling strike (not the Case-2 default).
"""

from __future__ import annotations

import pytest
from reopt_pysam_vn.integration.dppa_samsung_ttc import (
    SAMSUNG_TTC_ANNUAL_SOLAR_GWH,
    SAMSUNG_TTC_SOLAR_MWAC,
    analyze_samsung_ttc_settlement,
    build_samsung_ttc_extracted_inputs,
    build_samsung_ttc_results,
    generate_samsung_ttc_solar_8760,
    samsung_strike_vnd_per_kwh,
)


def test_solar_8760_calibrated_to_70_gwh():
    extracted = build_samsung_ttc_extracted_inputs()
    solar = generate_samsung_ttc_solar_8760(extracted)
    assert len(solar) == 8760
    annual_gwh = sum(solar) / 1e6
    assert abs(annual_gwh - SAMSUNG_TTC_ANNUAL_SOLAR_GWH) / SAMSUNG_TTC_ANNUAL_SOLAR_GWH <= 0.03
    # AC-clipped: never exceeds inverter nameplate.
    assert max(solar) <= SAMSUNG_TTC_SOLAR_MWAC * 1000.0 + 1e-6
    # Night hours produce nothing (hour 0 of day 1 is pre-dawn).
    assert solar[0] == 0.0
    # AC capacity factor in the realistic southern-Vietnam band.
    cf = sum(solar) / (SAMSUNG_TTC_SOLAR_MWAC * 1000.0 * 8760.0)
    assert 0.16 <= cf <= 0.23


def test_results_dict_full_match_no_export():
    extracted = build_samsung_ttc_extracted_inputs()
    solar = generate_samsung_ttc_solar_8760(extracted)
    results = build_samsung_ttc_results(solar, extracted)
    pv = results["PV"]
    assert len(pv["electric_to_load_series_kw"]) == 8760
    # Buyer load dwarfs solar at every hour => all solar serves load, no export.
    assert sum(pv["electric_to_grid_series_kw"]) == pytest.approx(0.0, abs=1.0)
    assert sum(pv["electric_to_load_series_kw"]) == pytest.approx(sum(solar), rel=1e-9)
    assert results["ElectricStorage"]["size_kw"] == 0.0
    assert "ElectricUtility" in results
    # Grid supplies the residual (load - solar-to-load) and stays non-negative.
    grid = results["ElectricUtility"]["electric_to_load_series_kw"]
    assert min(grid) >= -1e-6


def test_settlement_matches_contracted_70_gwh_with_samsung_strike():
    extracted = build_samsung_ttc_extracted_inputs()
    out = analyze_samsung_ttc_settlement(extracted)
    settlement = out["settlement"]
    matched_gwh = settlement["summary"]["matched_quantity_kwh"] / 1e6
    assert abs(matched_gwh - SAMSUNG_TTC_ANNUAL_SOLAR_GWH) / SAMSUNG_TTC_ANNUAL_SOLAR_GWH <= 0.03
    # CFMP/FMP proxy market reference flagged.
    assert settlement["market_reference_price_type"] == "proxy_cfmp_or_fmp"
    # Uses the Samsung Southern-ceiling strike, NOT the Case-2 default (~1,938).
    strike = settlement["parameters"]["strike_price_vnd_per_kwh"]
    assert strike == pytest.approx(samsung_strike_vnd_per_kwh(extracted))
    assert strike == pytest.approx(1012.0)


def test_benchmark_is_directional_and_evn_based():
    extracted = build_samsung_ttc_extracted_inputs()
    out = analyze_samsung_ttc_settlement(extracted)
    costs = out["benchmark"]["year_one_costs"]
    assert costs["benchmark_evn_total_cost_vnd"] > 0
    # CON-001: directional basis + explicit strike/market reference on the artifact.
    assert out["quality"]["basis"] == "directional"
    assert out["quality"]["strike_vnd_per_kwh"] == pytest.approx(1012.0)
    assert out["quality"]["market_reference_price_type"] == "proxy_cfmp_or_fmp"
    # Solar source is either real PVWatts (when PySAM is available) or the
    # deterministic synthetic fallback — both are valid, non-site-specific proxies.
    assert any(
        out["quality"]["solar_profile_source"].startswith(prefix)
        for prefix in ("pvwatts", "synthetic")
    )


def test_buyer_saves_on_contracted_slice_at_base_strike():
    extracted = build_samsung_ttc_extracted_inputs()
    out = analyze_samsung_ttc_settlement(extracted)
    costs = out["benchmark"]["year_one_costs"]
    # Base strike 1,012 is far below the EVN standard-hour avoided cost (~1,873),
    # so even with the inherited DPPA grid-service adder the buyer saves vs EVN.
    assert costs["buyer_savings_vs_evn_vnd"] > 0
    assert costs["buyer_minus_benchmark_vnd"] < 0
    slice_summary = out["contracted_slice"]
    assert abs(slice_summary["matched_quantity_gwh"] - SAMSUNG_TTC_ANNUAL_SOLAR_GWH) / SAMSUNG_TTC_ANNUAL_SOLAR_GWH <= 0.03
    assert slice_summary["buyer_savings_vnd"] > 0
    assert slice_summary["buyer_effective_cost_vnd_per_kwh"] < slice_summary["evn_avoided_cost_vnd_per_kwh"]
