"""Tests for the generic extracted-inputs assembler (PHASE-02, S3)."""

import pytest
from reopt_pysam_vn.analysis.types import DealConfig


def test_build_evn_tou_series_length_and_distinct():
    from reopt_pysam_vn.reopt.preprocess import build_evn_tou_series_vnd_per_kwh, load_vietnam_data

    vn = load_vietnam_data()
    series = build_evn_tou_series_vnd_per_kwh(
        vn, customer_type="industrial", voltage_level="medium_voltage_22kv_to_110kv", year=2024
    )
    assert len(series) == 8760
    assert all(v > 0 for v in series)
    assert len(set(series)) == 3


def test_build_evn_tou_series_consistency_with_usd_builder():
    from reopt_pysam_vn.common.assumptions import exchange_rate
    from reopt_pysam_vn.reopt.preprocess import (
        build_evn_tou_series_vnd_per_kwh,
        build_vietnam_tariff,
        load_vietnam_data,
    )

    vn = load_vietnam_data()
    fx = exchange_rate(vn)
    vnd = build_evn_tou_series_vnd_per_kwh(
        vn, customer_type="industrial", voltage_level="medium_voltage_22kv_to_110kv", year=2024
    )
    usd_dict = build_vietnam_tariff(vn, "industrial", "medium_voltage_22kv_to_110kv", year=2024)
    usd = usd_dict["tou_energy_rates_per_kwh"]
    for i in [0, 1000, 5000, 8759]:
        expected = vnd[i]
        got = usd[i] * fx
        assert got == pytest.approx(expected, rel=1e-6), f"mismatch at index {i}"


def test_build_extracted_inputs_basic():
    from reopt_pysam_vn.analysis.extracted import build_extracted_inputs

    cfg = DealConfig.from_dict(
        {"case": "X", "mode": "offsite_dppa", "load": {"loads_kw": [1000.0] * 8760}}
    )
    result = build_extracted_inputs(cfg)
    assert len(result["loads_kw"]) == 8760
    assert len(result["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]) == 8760
    assert result["benchmark"]["annual_load_kwh"] == pytest.approx(8_760_000.0)
    assert result["benchmark"]["peak_demand_kw"] == pytest.approx(1000.0)
    assert result["benchmark"]["wholesale_rate_vnd_per_kwh"] == pytest.approx(671.0)
    assert result["extraction_meta"]["customer_type"] == "industrial"
    assert result["extraction_meta"]["voltage_level"] == "medium_voltage_22kv_to_110kv"
    assert "customer_type" in result["extraction_meta"]["defaulted_fields"]
    assert "generation_kw" not in result


def test_build_extracted_inputs_load_weighted_benchmark():
    from reopt_pysam_vn.analysis.extracted import build_extracted_inputs

    loads = [0.0] * 4380 + [1000.0] * 4380
    cfg = DealConfig.from_dict({"case": "X", "mode": "offsite_dppa", "load": {"loads_kw": loads}})
    result = build_extracted_inputs(cfg)
    tariff = result["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]
    weighted = result["benchmark"]["weighted_evn_price_vnd_per_kwh"]
    calc = sum(l * t for l, t in zip(loads, tariff)) / 4_380_000.0
    simple = sum(tariff) / 8760
    assert weighted == pytest.approx(calc, rel=1e-9)
    assert weighted != pytest.approx(simple)


def test_build_extracted_inputs_wrong_length_raises():
    from reopt_pysam_vn.analysis.extracted import build_extracted_inputs
    from reopt_pysam_vn.analysis.offsite_dppa import OrchestratorInputError

    cfg = DealConfig.from_dict({"case": "X", "mode": "offsite_dppa", "load": {"loads_kw": [1000.0] * 8000}})
    with pytest.raises(OrchestratorInputError) as excinfo:
        build_extracted_inputs(cfg)
    msg = str(excinfo.value)
    assert "8760" in msg
    assert "8000" in msg


def test_build_extracted_inputs_missing_loads_raises():
    from reopt_pysam_vn.analysis.extracted import build_extracted_inputs
    from reopt_pysam_vn.analysis.offsite_dppa import OrchestratorInputError

    cfg = DealConfig.from_dict({"case": "X", "mode": "offsite_dppa"})
    with pytest.raises(OrchestratorInputError) as excinfo:
        build_extracted_inputs(cfg)
    assert "deal_config.load['loads_kw']" in str(excinfo.value)


def test_build_extracted_inputs_negative_load_raises():
    from reopt_pysam_vn.analysis.extracted import build_extracted_inputs
    from reopt_pysam_vn.analysis.offsite_dppa import OrchestratorInputError

    loads = [1000.0] * 8759 + [-1.0]
    cfg = DealConfig.from_dict({"case": "X", "mode": "offsite_dppa", "load": {"loads_kw": loads}})
    with pytest.raises(OrchestratorInputError) as excinfo:
        build_extracted_inputs(cfg)
    assert "non-negative" in str(excinfo.value)


def test_build_extracted_inputs_passes_validation():
    from reopt_pysam_vn.analysis.extracted import build_extracted_inputs
    from reopt_pysam_vn.analysis.validation import validate_extracted_inputs

    cfg = DealConfig.from_dict(
        {"case": "X", "mode": "offsite_dppa", "load": {"loads_kw": [1000.0] * 8760}}
    )
    result = build_extracted_inputs(cfg)
    validate_extracted_inputs(result)


def test_build_extracted_inputs_preserves_site_and_project():
    from reopt_pysam_vn.analysis.extracted import build_extracted_inputs

    cfg = DealConfig.from_dict(
        {
            "case": "MY_CASE",
            "mode": "offsite_dppa",
            "title": "My Project",
            "site": {"latitude": 10.0, "longitude": 105.0, "customer_type": "commercial", "voltage_level": "low_voltage_1kv_and_below"},
            "load": {"loads_kw": [500.0] * 8760},
        }
    )
    result = build_extracted_inputs(cfg)
    assert result["project"] == "My Project"
    assert result["site"]["latitude"] == 10.0
    assert result["site"]["customer_type"] == "commercial"
    assert result["extraction_meta"]["defaulted_fields"] == []


def test_build_extracted_inputs_title_fallback_to_case():
    from reopt_pysam_vn.analysis.extracted import build_extracted_inputs

    cfg = DealConfig.from_dict(
        {"case": "FALLBACK_CASE", "mode": "offsite_dppa", "load": {"loads_kw": [100.0] * 8760}}
    )
    result = build_extracted_inputs(cfg)
    assert result["project"] == "FALLBACK_CASE"
