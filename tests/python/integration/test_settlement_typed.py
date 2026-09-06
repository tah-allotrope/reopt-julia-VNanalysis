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
    HourlySeries,
    MarketReference,
    resolve_market_reference,
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
