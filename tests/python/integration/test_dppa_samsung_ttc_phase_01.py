"""PHASE-01 tests for the Samsung SEVT - TTC Duc Hue 2 DPPA economics case.

Covers the deal definition, the synthetic megafactory buyer load, the
fixed-sizing scenario (pinned PV, no BESS), the Southern-ceiling strike anchor,
and Case-2 settlement-engine compatibility of the extracted contract.
"""

from __future__ import annotations

import pytest
from reopt_pysam_vn.integration.dppa_samsung_ttc import (
    SAMSUNG_TTC_ANNUAL_SOLAR_GWH,
    SAMSUNG_TTC_SOLAR_MWAC,
    SAMSUNG_TTC_SOLAR_MWP,
    SAMSUNG_TTC_TARGET_ANNUAL_LOAD_KWH,
    SOUTHERN_GROUND_MOUNT_CEILING_VND_PER_KWH,
    build_samsung_synthetic_load_8760,
    build_samsung_ttc_definition,
    build_samsung_ttc_extracted_inputs,
    build_scenario_samsung_ttc,
    samsung_strike_vnd_per_kwh,
)

BASE_AVG_PRICE_VND_PER_KWH = 2204.0655
STANDARD_MULTIPLIER_110KV = 0.85


def test_synthetic_load_scale_and_factor():
    load = build_samsung_synthetic_load_8760(SAMSUNG_TTC_TARGET_ANNUAL_LOAD_KWH)
    assert len(load) == 8760
    total = sum(load)
    assert abs(total - SAMSUNG_TTC_TARGET_ANNUAL_LOAD_KWH) / SAMSUNG_TTC_TARGET_ANNUAL_LOAD_KWH < 1e-9
    avg = total / 8760.0
    load_factor = avg / max(load)
    assert 0.80 <= load_factor <= 0.92
    # Buyer load must dwarf the 41.4 MWac solar peak at all hours so the
    # contracted 70 GWh is fully matched (no excluded midday excess).
    assert min(load) > SAMSUNG_TTC_SOLAR_MWAC * 1000.0 * 1.5


def test_target_load_implies_small_re_share():
    # 70 GWh solar against ~1,000 GWh total => single-digit-percent pilot share,
    # consistent with SEVT being a >50%-of-global-output megafactory.
    re_share = (SAMSUNG_TTC_ANNUAL_SOLAR_GWH * 1e6) / SAMSUNG_TTC_TARGET_ANNUAL_LOAD_KWH
    assert 0.04 <= re_share <= 0.12


def test_definition_records_disclosed_facts_and_directional_flag():
    extracted = build_samsung_ttc_extracted_inputs()
    d = build_samsung_ttc_definition(extracted)
    assert d["plant"]["capacity_mwp"] == pytest.approx(49.0)
    assert d["plant"]["capacity_mwac"] == pytest.approx(41.4, abs=0.2)
    assert d["contract"]["annual_solar_gwh"] == pytest.approx(70.0)
    assert "samsung" in d["parties"]["buyer"].lower()
    gen = d["parties"]["generator"].lower()
    assert "ttc" in gen or "duc hue" in gen
    assert "tay ninh" in d["plant"]["province"].lower()
    assert d["contract"]["settlement_mechanism"] == "financial_cfd"
    # CON-001: every Samsung-TTC artifact must carry the directional basis flag.
    assert d["quality"]["basis"] == "directional"
    assert "strike" in d["quality"]["caveat"].lower()


def test_scenario_pv_is_fixed_and_storage_disabled():
    extracted = build_samsung_ttc_extracted_inputs()
    s = build_scenario_samsung_ttc(extracted)
    pv = s["PV"]
    fixed_dc_kw = SAMSUNG_TTC_SOLAR_MWP * 1000.0
    assert pv["min_kw"] == pytest.approx(fixed_dc_kw)
    assert pv["max_kw"] == pytest.approx(fixed_dc_kw)
    assert s["ElectricStorage"]["max_kw"] == 0
    assert s["ElectricStorage"]["max_kwh"] == 0
    assert s["Wind"]["max_kw"] == 0
    assert s["_meta"]["scenario"] == "DPPA_SAMSUNG_TTC"
    assert s["_meta"]["storage_requirement"] == "none_fixed_plant"


def test_scenario_uses_southern_solar_site():
    extracted = build_samsung_ttc_extracted_inputs()
    s = build_scenario_samsung_ttc(extracted)
    # Generation is at Duc Hue 2 (Tay Ninh, south): lat ~10-12 N, lon ~105.5-107 E.
    assert 10.0 <= s["Site"]["latitude"] <= 12.0
    assert 105.5 <= s["Site"]["longitude"] <= 107.0


def test_strike_anchor_is_southern_ceiling_and_sweepable():
    extracted = build_samsung_ttc_extracted_inputs()
    base = samsung_strike_vnd_per_kwh(extracted)
    assert base == pytest.approx(SOUTHERN_GROUND_MOUNT_CEILING_VND_PER_KWH)
    assert base == pytest.approx(1012.0)
    top = samsung_strike_vnd_per_kwh(extracted, sweep_fraction=1.0)
    assert top == pytest.approx(extracted["benchmark"]["standard_rate_vnd_per_kwh"])
    assert top > base
    mid = samsung_strike_vnd_per_kwh(extracted, sweep_fraction=0.5)
    assert base < mid < top


def test_extracted_contract_is_case2_compatible():
    extracted = build_samsung_ttc_extracted_inputs()
    assert "loads_kw" in extracted and len(extracted["loads_kw"]) == 8760
    b = extracted["benchmark"]
    assert b["exchange_rate_vnd_per_usd"] == pytest.approx(26400.0)
    assert "weighted_evn_price_vnd_per_kwh" in b
    assert b["standard_rate_vnd_per_kwh"] == pytest.approx(
        BASE_AVG_PRICE_VND_PER_KWH * STANDARD_MULTIPLIER_110KV, rel=1e-6
    )
    site = extracted["site"]
    assert site["customer_type"] == "industrial"
    assert site["voltage_level"] == "high_voltage_above_35kv_below_220kv"
    assert site["region"] == "south"
    assert len(extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]) >= 8760
