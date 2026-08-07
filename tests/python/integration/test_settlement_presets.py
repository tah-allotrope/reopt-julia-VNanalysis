"""Tests for settlement contract presets and strike sweep (GAP-04 PHASE-02)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.settlement import (
    PRESET_CONTRACTS,
    ContractParams,
    compute_buyer_benchmark,
    compute_hourly_settlement,
    run_strike_sweep,
)


def _constant_series(value: float, n: int = 8760) -> list[float]:
    return [value] * n


# ---------------------------------------------------------------------------
# Preset validation
# ---------------------------------------------------------------------------

class TestPresetContracts:
    def test_all_presets_are_valid_contract_params(self):
        for name, params in PRESET_CONTRACTS.items():
            assert isinstance(params, ContractParams), f"{name} is not ContractParams"

    def test_decree57_private_wire_standard(self):
        p = PRESET_CONTRACTS["decree57_private_wire_standard"]
        assert p.mode == "private_wire"
        assert p.export_cap_pct == 20.0
        assert p.surplus_rate_vnd_kwh == 671.0

    def test_virtual_cfd_matched_only(self):
        p = PRESET_CONTRACTS["virtual_cfd_matched_only"]
        assert p.mode == "virtual_cfd"
        assert p.settlement_quantity_rule == "matched_only"
        assert p.excess_treatment == "curtail"

    def test_virtual_cfd_full_volume(self):
        p = PRESET_CONTRACTS["virtual_cfd_full_volume"]
        assert p.mode == "virtual_cfd"
        assert p.settlement_quantity_rule == "contracted_volume"
        assert p.excess_treatment == "cfd_on_excess"

    def test_physical_dppa_export_50pct(self):
        p = PRESET_CONTRACTS["physical_dppa_export_50pct"]
        assert p.mode == "private_wire"
        assert p.export_cap_pct == 50.0
        assert p.excess_treatment == "export_at_surplus"

    def test_decree243_export_50pct_standard(self):
        p = PRESET_CONTRACTS["decree243_export_50pct_standard"]
        assert p.mode == "private_wire"
        assert p.strike_vnd_kwh == 1012.0
        assert p.excess_treatment == "export_at_surplus"
        assert p.export_cap_pct == 50.0
        assert p.surplus_rate_vnd_kwh == 671.0

    def test_at_least_four_presets(self):
        assert len(PRESET_CONTRACTS) >= 4

    def test_each_preset_produces_valid_settlement(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(800.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)

        for name, params in PRESET_CONTRACTS.items():
            result = compute_hourly_settlement(loads, generation, tariff, fmp, params)
            assert len(result.hourly_ledger) == 8760, f"{name}: ledger length wrong"
            assert result.annual_summary["buyer_cost_vnd"] != 0.0, f"{name}: zero buyer cost"


# ---------------------------------------------------------------------------
# Strike sweep
# ---------------------------------------------------------------------------

class TestStrikeSweep:
    def test_sweep_returns_correct_count(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(800.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        preset = PRESET_CONTRACTS["virtual_cfd_matched_only"]
        strikes = [1600.0, 1700.0, 1800.0, 1900.0, 2000.0]

        results = run_strike_sweep(
            loads, generation, tariff, fmp, preset, strikes
        )
        assert len(results) == 5

    def test_sweep_results_have_required_keys(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(800.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        preset = PRESET_CONTRACTS["virtual_cfd_matched_only"]
        strikes = [1700.0, 1800.0]

        results = run_strike_sweep(loads, generation, tariff, fmp, preset, strikes)
        for entry in results:
            assert "strike_vnd_kwh" in entry
            assert "buyer_cost_vnd" in entry
            assert "buyer_blended_rate_vnd_kwh" in entry
            assert "developer_revenue_vnd" in entry
            assert "buyer_savings_vs_evn_vnd" in entry

    def test_higher_strike_increases_buyer_cost_cfd(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        preset = PRESET_CONTRACTS["virtual_cfd_matched_only"]
        strikes = [1600.0, 1800.0, 2000.0]

        results = run_strike_sweep(loads, generation, tariff, fmp, preset, strikes)
        costs = [r["buyer_cost_vnd"] for r in results]
        assert costs[0] < costs[1] < costs[2]

    def test_higher_strike_increases_developer_revenue_private_wire(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(0.0)
        preset = PRESET_CONTRACTS["decree57_private_wire_standard"]
        strikes = [900.0, 1000.0, 1100.0]

        results = run_strike_sweep(loads, generation, tariff, fmp, preset, strikes)
        revenues = [r["developer_revenue_vnd"] for r in results]
        assert revenues[0] < revenues[1] < revenues[2]

    def test_sweep_includes_benchmark_savings(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        preset = PRESET_CONTRACTS["virtual_cfd_matched_only"]
        strikes = [1500.0, 2200.0]

        results = run_strike_sweep(loads, generation, tariff, fmp, preset, strikes)
        benchmark = compute_buyer_benchmark(loads, tariff)
        for entry in results:
            expected_savings = benchmark["evn_only_cost_vnd"] - entry["buyer_cost_vnd"]
            assert abs(entry["buyer_savings_vs_evn_vnd"] - expected_savings) < 1.0

    def test_sweep_with_single_strike(self):
        loads = _constant_series(1000.0)
        generation = _constant_series(800.0)
        tariff = _constant_series(1900.0)
        fmp = _constant_series(1700.0)
        preset = PRESET_CONTRACTS["virtual_cfd_matched_only"]

        results = run_strike_sweep(loads, generation, tariff, fmp, preset, [1800.0])
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Enhanced benchmark with settlement comparison
# ---------------------------------------------------------------------------

class TestBenchmarkComparison:
    def test_benchmark_total_matches_manual(self):
        loads = _constant_series(1000.0)
        tariff = _constant_series(1900.0)
        benchmark = compute_buyer_benchmark(loads, tariff)
        assert abs(benchmark["evn_only_cost_vnd"] - 1000.0 * 1900.0 * 8760) < 1.0

    def test_varying_tariff_benchmark(self):
        loads = _constant_series(1000.0)
        tariff = [1500.0 if h < 4380 else 2300.0 for h in range(8760)]
        benchmark = compute_buyer_benchmark(loads, tariff)
        expected = 1000.0 * (1500.0 * 4380 + 2300.0 * 4380)
        assert abs(benchmark["evn_only_cost_vnd"] - expected) < 1.0
