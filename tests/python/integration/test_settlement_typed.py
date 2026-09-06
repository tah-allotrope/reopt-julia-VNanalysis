"""Tests for the deepened typed settlement seam (Candidate 1, steps 1-3).

Typed constructors replace the ``settlement_inputs: dict`` key chains so a
swapped or misspelled series name becomes a type error, not a silent KeyError.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.settlement import (
    BuyerBenchmark,
    ContractParams,
    HourlySeries,
    MarketReference,
    SettlementInputs,
    build_settlement_inputs,
    compute_buyer_benchmark_typed,
    compute_hourly_settlement,
    compute_hourly_settlement_typed,
    resolve_market_reference,
    resolve_samsung_strike,
    resolve_strike_weighted_discount,
    run_strike_sweep_typed,
)


def _const(value: float, n: int = 8760) -> list[float]:
    return [value] * n


class TestHourlySeries:
    def test_coerces_ints_to_float(self):
        series = HourlySeries(values=tuple([1, 2, 3] * 2920))
        assert all(isinstance(value, float) for value in series.values)
        assert series.to_list() == [1.0, 2.0, 3.0] * 2920

    def test_rejects_short_series(self):
        with pytest.raises(ValueError):
            HourlySeries(values=tuple([1.0] * 100))

    def test_rejects_long_series(self):
        with pytest.raises(ValueError):
            HourlySeries(values=tuple([1.0] * 9000))

    def test_to_list_roundtrip(self):
        raw = _const(7.5)
        assert HourlySeries(values=tuple(raw)).to_list() == raw


class TestResolveMarketReference:
    def test_explicit_cfmp_beats_everything(self):
        retail = _const(1900.0)
        ref = resolve_market_reference(
            cfmp_vnd_per_mwh=_const(1_700_000.0),
            fmp_vnd_per_mwh=_const(1_000_000.0),
            retail_vnd_per_kwh=retail,
            weighted_evn_price_vnd_per_kwh=1900.0,
            wholesale_rate_vnd_per_kwh=900.0,
        )
        assert isinstance(ref, MarketReference)
        assert ref.reference_type == "cfmp"
        assert ref.series_vnd_per_kwh.to_list() == _const(1700.0)
        assert ref.proxy_fraction_of_evn is None

    def test_fmp_used_when_cfmp_absent(self):
        ref = resolve_market_reference(
            fmp_vnd_per_mwh=_const(1_600_000.0),
            retail_vnd_per_kwh=_const(1900.0),
            weighted_evn_price_vnd_per_kwh=1900.0,
            wholesale_rate_vnd_per_kwh=900.0,
        )
        assert ref.reference_type == "fmp"
        assert ref.series_vnd_per_kwh.to_list() == _const(1600.0)

    def test_proxy_scales_retail_by_wholesale_ratio(self):
        ref = resolve_market_reference(
            retail_vnd_per_kwh=_const(2000.0),
            weighted_evn_price_vnd_per_kwh=2000.0,
            wholesale_rate_vnd_per_kwh=1000.0,
        )
        assert ref.reference_type == "proxy_cfmp_or_fmp"
        assert ref.proxy_fraction_of_evn == pytest.approx(0.5)
        assert ref.series_vnd_per_kwh.to_list() == _const(1000.0)

    def test_proxy_zero_weighted_gives_zero_fraction(self):
        ref = resolve_market_reference(
            retail_vnd_per_kwh=_const(2000.0),
            weighted_evn_price_vnd_per_kwh=0.0,
            wholesale_rate_vnd_per_kwh=1000.0,
        )
        assert ref.proxy_fraction_of_evn == 0.0
        assert ref.series_vnd_per_kwh.to_list() == _const(0.0)


class TestStrikeResolvers:
    @pytest.mark.parametrize(
        ("discount", "expected"),
        [(0.0, 2000.0), (0.05, 1900.0), (0.10, 1800.0), (0.15, 1700.0), (0.20, 1600.0)],
    )
    def test_weighted_discount_table(self, discount, expected):
        assert resolve_strike_weighted_discount(2000.0, discount) == pytest.approx(expected)

    def test_samsung_strike_endpoints_and_midpoint(self):
        assert resolve_samsung_strike(1500.0, 2500.0, 0.0) == pytest.approx(1500.0)
        assert resolve_samsung_strike(1500.0, 2500.0, 1.0) == pytest.approx(2500.0)
        assert resolve_samsung_strike(1500.0, 2500.0, 0.5) == pytest.approx(2000.0)


def _virtual_cfd_params(**overrides) -> ContractParams:
    defaults = {
        "mode": "virtual_cfd",
        "strike_vnd_kwh": 1900.0,
        "settlement_quantity_rule": "matched_only",
        "excess_treatment": "curtail",
    }
    defaults.update(overrides)
    return ContractParams(**defaults)


class TestBuildSettlementInputs:
    def test_builds_typed_inputs(self):
        market = resolve_market_reference(
            retail_vnd_per_kwh=_const(1900.0),
            weighted_evn_price_vnd_per_kwh=1900.0,
            wholesale_rate_vnd_per_kwh=900.0,
        )
        inputs = build_settlement_inputs(
            loads_kw=_const(1000.0),
            generation_kw=_const(800.0),
            tariff_vnd_per_kwh=_const(1900.0),
            market=market,
            contract=_virtual_cfd_params(),
            exchange_rate_vnd_per_usd=26400.0,
        )
        assert isinstance(inputs, SettlementInputs)
        assert inputs.loads_kw.to_list() == _const(1000.0)
        assert inputs.market_type == "proxy_cfmp_or_fmp"
        assert inputs.exchange_rate_vnd_per_usd == pytest.approx(26400.0)
        assert inputs.notes == ()

    def test_rejects_short_series(self):
        market = resolve_market_reference(
            retail_vnd_per_kwh=_const(1900.0),
            weighted_evn_price_vnd_per_kwh=1900.0,
            wholesale_rate_vnd_per_kwh=900.0,
        )
        with pytest.raises(ValueError):
            build_settlement_inputs(
                loads_kw=[1000.0] * 100,
                generation_kw=_const(800.0),
                tariff_vnd_per_kwh=_const(1900.0),
                market=market,
                contract=_virtual_cfd_params(),
                exchange_rate_vnd_per_usd=26400.0,
            )


def _typed_inputs(**overrides) -> SettlementInputs:
    market = resolve_market_reference(
        retail_vnd_per_kwh=_const(1900.0),
        weighted_evn_price_vnd_per_kwh=1900.0,
        wholesale_rate_vnd_per_kwh=1700.0,
    )
    kwargs = {
        "loads_kw": _const(1000.0),
        "generation_kw": _const(800.0),
        "tariff_vnd_per_kwh": _const(1900.0),
        "market": market,
        "contract": _virtual_cfd_params(),
        "exchange_rate_vnd_per_usd": 26400.0,
    }
    kwargs.update(overrides)
    return build_settlement_inputs(**kwargs)


class TestTypedEngine:
    def test_typed_matches_list_engine_exactly(self):
        inputs = _typed_inputs()
        typed = compute_hourly_settlement_typed(inputs)
        listed = compute_hourly_settlement(
            inputs.loads_kw.to_list(),
            inputs.generation_kw.to_list(),
            inputs.tariff_vnd_per_kwh.to_list(),
            inputs.market_vnd_per_kwh.to_list(),
            inputs.contract,
            market_source_label=inputs.market_type,
        )
        assert typed.annual_summary == listed.annual_summary
        assert typed.hourly_ledger == listed.hourly_ledger

    def test_benchmark_clamp_never_both_positive(self):
        cheap = _typed_inputs(
            tariff_vnd_per_kwh=_const(100.0),
            contract=_virtual_cfd_params(strike_vnd_kwh=5000.0),
        )
        benchmark = compute_buyer_benchmark_typed(cheap)
        assert isinstance(benchmark, BuyerBenchmark)
        assert benchmark.buyer_premium_vs_evn_vnd > 0.0
        assert benchmark.buyer_savings_vs_evn_vnd == 0.0

        rich = _typed_inputs(contract=_virtual_cfd_params(strike_vnd_kwh=100.0))
        benchmark = compute_buyer_benchmark_typed(rich)
        assert benchmark.buyer_savings_vs_evn_vnd > 0.0
        assert benchmark.buyer_premium_vs_evn_vnd == 0.0

    def test_strike_sweep_monotonic_buyer_cost(self):
        inputs = _typed_inputs()
        sweep = run_strike_sweep_typed(inputs, [1500.0, 1900.0, 2300.0])
        costs = [entry["buyer_cost_vnd"] for entry in sweep]
        assert costs == sorted(costs)
        assert [entry["strike_vnd_kwh"] for entry in sweep] == [1500.0, 1900.0, 2300.0]

    def test_excess_treatment_matrix_on_short_synthetic(self):
        import dataclasses

        base = _typed_inputs(
            loads_kw=[500.0] * 8760,
            generation_kw=[900.0] * 8760,
        )
        curtail = compute_hourly_settlement_typed(base)
        export = compute_hourly_settlement_typed(
            dataclasses.replace(
                base,
                contract=ContractParams(
                    mode="private_wire",
                    strike_vnd_kwh=1900.0,
                    excess_treatment="export_at_surplus",
                    export_cap_pct=50.0,
                ),
            )
        )
        assert curtail.annual_summary["exported_mwh"] == pytest.approx(0.0)
        assert curtail.annual_summary["curtailed_mwh"] > 0.0
        assert export.annual_summary["exported_mwh"] > 0.0
