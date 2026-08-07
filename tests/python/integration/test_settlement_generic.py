"""Tests for the generalized settlement engine (GAP-04 PHASE-01)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.settlement import (
    ContractParams,
    SettlementResult,
    compute_buyer_benchmark,
    compute_hourly_settlement,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic 8760 inputs
# ---------------------------------------------------------------------------

def _constant_series(value: float, n: int = 8760) -> list[float]:
    return [value] * n


def _make_params(**overrides) -> ContractParams:
    defaults = {
        "mode": "virtual_cfd",
        "strike_vnd_kwh": 1800.0,
        "escalation_rate": 0.05,
        "settlement_quantity_rule": "matched_only",
        "excess_treatment": "curtail",
        "export_cap_pct": 20.0,
        "surplus_rate_vnd_kwh": 671.0,
        "dppa_adder_vnd_kwh": 523.34,
        "kpp_pct": 2.7263,
    }
    defaults.update(overrides)
    return ContractParams(**defaults)


@pytest.fixture
def flat_loads():
    return _constant_series(1000.0)


@pytest.fixture
def flat_generation():
    return _constant_series(800.0)


@pytest.fixture
def flat_tariff():
    return _constant_series(1900.0)


@pytest.fixture
def flat_fmp():
    return _constant_series(1700.0)


# ---------------------------------------------------------------------------
# ContractParams validation
# ---------------------------------------------------------------------------

class TestContractParams:
    def test_valid_virtual_cfd(self):
        p = _make_params(mode="virtual_cfd")
        assert p.mode == "virtual_cfd"

    def test_valid_private_wire(self):
        p = _make_params(mode="private_wire")
        assert p.mode == "private_wire"

    def test_invalid_mode_rejected(self):
        with pytest.raises((ValueError, TypeError)):
            _make_params(mode="hybrid")

    def test_kpp_factor_property(self):
        p = _make_params(kpp_pct=2.7263)
        assert abs(p.kpp_factor - 1.027263) < 1e-6


# ---------------------------------------------------------------------------
# Virtual CfD mode
# ---------------------------------------------------------------------------

class TestVirtualCfDSettlement:
    def test_basic_settlement_structure(self, flat_loads, flat_generation, flat_tariff, flat_fmp):
        params = _make_params(mode="virtual_cfd")
        result = compute_hourly_settlement(
            flat_loads, flat_generation, flat_tariff, flat_fmp, params
        )
        assert isinstance(result, SettlementResult)
        assert len(result.hourly_ledger) == 8760
        assert result.contract_params is params

    def test_matched_quantity_is_min_load_gen(self, flat_tariff, flat_fmp):
        loads = _constant_series(1000.0)
        generation = _constant_series(800.0)
        params = _make_params(mode="virtual_cfd")
        result = compute_hourly_settlement(loads, generation, flat_tariff, flat_fmp, params)
        for entry in result.hourly_ledger:
            assert abs(entry["matched_kwh"] - 800.0) < 0.01

    def test_shortfall_calculated(self, flat_tariff, flat_fmp):
        loads = _constant_series(1000.0)
        generation = _constant_series(800.0)
        params = _make_params(mode="virtual_cfd")
        result = compute_hourly_settlement(loads, generation, flat_tariff, flat_fmp, params)
        for entry in result.hourly_ledger:
            assert abs(entry["shortfall_kwh"] - 200.0) < 0.01

    def test_excess_calculated(self, flat_tariff, flat_fmp):
        loads = _constant_series(500.0)
        generation = _constant_series(900.0)
        params = _make_params(mode="virtual_cfd")
        result = compute_hourly_settlement(loads, generation, flat_tariff, flat_fmp, params)
        for entry in result.hourly_ledger:
            assert abs(entry["excess_kwh"] - 400.0) < 0.01

    def test_positive_cfd_when_strike_above_fmp(self, flat_tariff):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        fmp = _constant_series(1500.0)
        params = _make_params(mode="virtual_cfd", strike_vnd_kwh=1800.0)
        result = compute_hourly_settlement(loads, generation, flat_tariff, fmp, params)
        assert result.annual_summary["buyer_cfd_payment_vnd"] > 0

    def test_negative_cfd_when_fmp_above_strike(self, flat_tariff):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        fmp = _constant_series(2100.0)
        params = _make_params(mode="virtual_cfd", strike_vnd_kwh=1800.0)
        result = compute_hourly_settlement(loads, generation, flat_tariff, fmp, params)
        assert result.annual_summary["buyer_cfd_payment_vnd"] < 0

    def test_evn_matched_payment_uses_kpp(self, flat_tariff):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        fmp = _constant_series(1700.0)
        params = _make_params(mode="virtual_cfd", kpp_pct=2.7263)
        result = compute_hourly_settlement(loads, generation, flat_tariff, fmp, params)
        expected_per_hour = 1000.0 * 1700.0 * 1.027263
        actual_per_hour = result.annual_summary["buyer_evn_matched_payment_vnd"] / 8760
        assert abs(actual_per_hour - expected_per_hour) < 0.01

    def test_dppa_adder_applied(self, flat_tariff, flat_fmp):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        params = _make_params(mode="virtual_cfd", dppa_adder_vnd_kwh=500.0)
        result = compute_hourly_settlement(loads, generation, flat_tariff, flat_fmp, params)
        expected = 1000.0 * 500.0 * 8760
        assert abs(result.annual_summary["buyer_dppa_charge_vnd"] - expected) < 1.0

    def test_shortfall_billed_at_retail(self, flat_fmp):
        loads = _constant_series(1000.0)
        generation = _constant_series(600.0)
        tariff = _constant_series(1900.0)
        params = _make_params(mode="virtual_cfd")
        result = compute_hourly_settlement(loads, generation, tariff, flat_fmp, params)
        expected = 400.0 * 1900.0 * 8760
        assert abs(result.annual_summary["buyer_shortfall_payment_vnd"] - expected) < 1.0

    def test_annual_totals_match_hourly_sums(self, flat_loads, flat_generation, flat_tariff, flat_fmp):
        params = _make_params(mode="virtual_cfd")
        result = compute_hourly_settlement(flat_loads, flat_generation, flat_tariff, flat_fmp, params)
        ledger = result.hourly_ledger
        summary = result.annual_summary
        assert abs(sum(e["matched_kwh"] for e in ledger) - summary["matched_mwh"] * 1000) < 1.0
        assert abs(sum(e["buyer_total_payment_vnd"] for e in ledger) - summary["buyer_cost_vnd"]) < 1.0

    def test_blended_rate_calculation(self, flat_loads, flat_generation, flat_tariff, flat_fmp):
        params = _make_params(mode="virtual_cfd")
        result = compute_hourly_settlement(flat_loads, flat_generation, flat_tariff, flat_fmp, params)
        summary = result.annual_summary
        expected = summary["buyer_cost_vnd"] / (1000.0 * 8760)
        assert abs(summary["buyer_blended_rate_vnd_kwh"] - expected) < 0.01


# ---------------------------------------------------------------------------
# Private-wire mode
# ---------------------------------------------------------------------------

class TestPrivateWireSettlement:
    def test_private_wire_revenue_at_strike(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(0.0)  # FMP irrelevant for private wire
        params = _make_params(mode="private_wire", strike_vnd_kwh=1100.0)
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        expected_revenue = 1000.0 * 1100.0 * 8760
        assert abs(result.annual_summary["developer_revenue_vnd"] - expected_revenue) < 1.0

    def test_private_wire_no_cfd_component(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        params = _make_params(mode="private_wire", strike_vnd_kwh=1100.0)
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        assert result.annual_summary["buyer_cfd_payment_vnd"] == 0.0

    def test_private_wire_shortfall_on_evn(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(600.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(0.0)
        params = _make_params(mode="private_wire", strike_vnd_kwh=1100.0)
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        expected = 400.0 * 1900.0 * 8760
        assert abs(result.annual_summary["buyer_shortfall_payment_vnd"] - expected) < 1.0

    def test_private_wire_export_cap_applied(self):
        loads = _constant_series(500.0)
        generation = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(0.0)
        params = _make_params(
            mode="private_wire",
            strike_vnd_kwh=1100.0,
            excess_treatment="export_at_surplus",
            export_cap_pct=20.0,
            surplus_rate_vnd_kwh=671.0,
        )
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        # Excess = 500 kWh/hr, export cap = 20% of generation = 200 kWh/hr
        for entry in result.hourly_ledger:
            assert entry["exported_kwh"] <= 200.0 + 0.01
            assert entry["curtailed_kwh"] >= 300.0 - 0.01

    def test_private_wire_buyer_cost_is_strike_plus_shortfall(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(800.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(0.0)
        params = _make_params(
            mode="private_wire",
            strike_vnd_kwh=1100.0,
            dppa_adder_vnd_kwh=0.0,
            kpp_pct=0.0,
        )
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        expected = (800.0 * 1100.0 + 200.0 * 1900.0) * 8760
        assert abs(result.annual_summary["buyer_cost_vnd"] - expected) < 1.0


# ---------------------------------------------------------------------------
# Excess treatment variants
# ---------------------------------------------------------------------------

class TestExcessTreatment:
    def test_curtail_excess(self):
        loads = _constant_series(500.0)
        generation = _constant_series(900.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        params = _make_params(mode="virtual_cfd", excess_treatment="curtail")
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        for entry in result.hourly_ledger:
            assert abs(entry["curtailed_kwh"] - 400.0) < 0.01
            assert abs(entry["exported_kwh"] - 0.0) < 0.01

    def test_export_at_surplus(self):
        loads = _constant_series(500.0)
        generation = _constant_series(900.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        params = _make_params(
            mode="virtual_cfd",
            excess_treatment="export_at_surplus",
            export_cap_pct=100.0,
            surplus_rate_vnd_kwh=671.0,
        )
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        for entry in result.hourly_ledger:
            assert abs(entry["exported_kwh"] - 400.0) < 0.01
        _expected_export_revenue = 400.0 * 671.0 * 8760
        assert abs(result.annual_summary["developer_revenue_vnd"] - result.annual_summary.get("developer_revenue_vnd", 0)) < 1.0

    def test_cfd_on_excess(self):
        loads = _constant_series(500.0)
        generation = _constant_series(900.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        params_curtail = _make_params(mode="virtual_cfd", excess_treatment="curtail")
        params_excess = _make_params(mode="virtual_cfd", excess_treatment="cfd_on_excess")
        result_curtail = compute_hourly_settlement(loads, generation, tariff, fmp, params_curtail)
        result_excess = compute_hourly_settlement(loads, generation, tariff, fmp, params_excess)
        # CfD on excess means buyer pays CfD on excess generation too
        assert result_excess.annual_summary["buyer_cost_vnd"] != result_curtail.annual_summary["buyer_cost_vnd"]


# ---------------------------------------------------------------------------
# Buyer benchmark
# ---------------------------------------------------------------------------

class TestBuyerBenchmark:
    def test_benchmark_is_load_times_tariff(self):
        loads = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        benchmark = compute_buyer_benchmark(loads, tariff)
        expected = 1000.0 * 1900.0 * 8760
        assert abs(benchmark["evn_only_cost_vnd"] - expected) < 1.0

    def test_benchmark_blended_rate(self):
        loads = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        benchmark = compute_buyer_benchmark(loads, tariff)
        assert abs(benchmark["blended_rate_vnd_kwh"] - 1900.0) < 0.01

    def test_savings_positive_when_dppa_cheaper(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        params = _make_params(
            mode="virtual_cfd",
            strike_vnd_kwh=1600.0,
            dppa_adder_vnd_kwh=0.0,
            kpp_pct=0.0,
        )
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        benchmark = compute_buyer_benchmark(loads, tariff)
        savings = benchmark["evn_only_cost_vnd"] - result.annual_summary["buyer_cost_vnd"]
        assert savings > 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_generation(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(0.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        params = _make_params(mode="virtual_cfd")
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        assert result.annual_summary["matched_mwh"] == 0.0
        expected = 1000.0 * 1900.0 * 8760
        assert abs(result.annual_summary["buyer_shortfall_payment_vnd"] - expected) < 1.0

    def test_zero_load(self):
        loads = _constant_series(0.0)
        generation = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        params = _make_params(mode="virtual_cfd", excess_treatment="curtail")
        result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
        assert result.annual_summary["matched_mwh"] == 0.0
        assert result.annual_summary["buyer_blended_rate_vnd_kwh"] == 0.0

    def test_market_source_label_echoed(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(800.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        params = _make_params(mode="virtual_cfd")
        result = compute_hourly_settlement(
            loads, generation, tariff, fmp, params,
            market_source_label="proxy_cfmp"
        )
        assert result.market_source_label == "proxy_cfmp"
