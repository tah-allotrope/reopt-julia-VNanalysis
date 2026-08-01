"""PHASE-04: canonical assumption resolver (S1-S3)."""

import pytest

from reopt_pysam_vn.common.assumptions import (
    dppa_adder_vnd_per_kwh,
    exchange_rate,
    export_cap_fraction,
    kpp_loss_pct,
    surplus_rate_vnd_per_kwh,
)
from reopt_pysam_vn.integration.settlement import ContractParams
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data


@pytest.fixture(scope="module")
def vn():
    return load_vietnam_data()


def test_deal_defaults_exchange_rate(vn):
    assert vn.deal_defaults["exchange_rate"]["vnd_per_usd"] == 26400


def test_deal_defaults_dppa_settlement_adder(vn):
    assert vn.deal_defaults["dppa_settlement"]["adder_vnd_per_kwh"] == 523.34


def test_exchange_rate_default(vn):
    assert exchange_rate(vn) == 26400.0


def test_exchange_rate_caller_wins(vn):
    assert exchange_rate(vn, caller_value=25450.0) == 25450.0


def test_exchange_rate_extracted(vn):
    assert exchange_rate(vn, extracted={"benchmark": {"exchange_rate_vnd_per_usd": 25000.0}}) == 25000.0


def test_exchange_rate_caller_beats_extracted(vn):
    result = exchange_rate(
        vn,
        caller_value=25450.0,
        extracted={"benchmark": {"exchange_rate_vnd_per_usd": 25000.0}},
    )
    assert result == 25450.0


def test_exchange_rate_zero_raises(vn):
    with pytest.raises(ValueError):
        exchange_rate(vn, caller_value=0.0)


def test_exchange_rate_missing_key_falls_through(vn):
    assert exchange_rate(vn, extracted={"benchmark": {}}) == 26400.0


def test_export_cap_fraction_current(vn):
    assert export_cap_fraction(vn, regime_id="decision_963_2026_current") == 0.5


def test_export_cap_fraction_legacy(vn):
    assert export_cap_fraction(vn, regime_id="decree_57_2025_legacy") == 0.2


def test_export_cap_fraction_draft(vn):
    assert export_cap_fraction(vn, regime_id="decree57_rooftop_50pct_draft") == 0.5


def test_export_cap_fraction_unknown_regime_raises(vn):
    with pytest.raises(ValueError) as exc_info:
        export_cap_fraction(vn, regime_id="not_a_regime")
    msg = str(exc_info.value)
    for regime in (
        "decision_14_2025_current",
        "decision_14_2025_legacy",
        "decision_963_2026_current",
        "decision_963_2026_repriced_multipliers",
        "decree57_rooftop_50pct_draft",
        "decree_57_2025_legacy",
        "decree146_two_part_trial_2026",
    ):
        assert regime in msg


def test_surplus_rate_current(vn):
    assert surplus_rate_vnd_per_kwh(vn, regime_id="decision_963_2026_current") == 671.0


def test_kpp_loss_pct_and_factor(vn):
    pct = kpp_loss_pct(vn)
    assert pct == 2.7263
    assert ContractParams(mode="virtual_cfd", strike_vnd_kwh=1800.0, kpp_pct=pct).kpp_factor == pytest.approx(1.027263)


def test_dppa_adder(vn):
    assert dppa_adder_vnd_per_kwh(vn) == 523.34


def test_contract_params_backwards_compatible_no_regime_id():
    params = ContractParams(mode="private_wire", strike_vnd_kwh=1012.0)
    assert params.export_cap_pct == 20.0


def test_from_regime_resolves_export_cap(vn):
    params = ContractParams.from_regime(
        "decision_963_2026_current", mode="private_wire", strike_vnd_kwh=1012.0, vn=vn
    )
    assert params.export_cap_pct == 50.0
    assert params.export_cap_pct > 1.0


def test_from_regime_override_wins(vn):
    params = ContractParams.from_regime(
        "decision_963_2026_current",
        mode="private_wire",
        strike_vnd_kwh=1012.0,
        vn=vn,
        export_cap_pct=99.0,
    )
    assert params.export_cap_pct == 99.0
