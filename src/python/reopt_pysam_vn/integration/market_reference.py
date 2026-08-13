"""Shared market-reference (FMP/CFMP) price series resolution (PHASE-04, S2).

Resolves the 8760 market-reference price series (VND per kWh) a DPPA settlement
consumes, in this order and stopping at the first hit:

1. ``extracted["cfmp_vnd_per_mwh"]`` — an actual hourly CFMP series; divide every
   element by 1,000 (VND/MWh -> VND/kWh). Label ``"cfmp"``.
2. ``extracted["fmp_vnd_per_mwh"]`` — an actual hourly FMP series; same
   conversion. Label ``"fmp"``.
3. The proxy — the hourly EVN retail tariff scaled by
   ``wholesale_reference / weighted_retail``. Label ``"proxy_cfmp_or_fmp"``.

The proxy reproduces ``dppa_case_2.build_dppa_case_2_market_proxy`` exactly for
any deal whose ``extracted`` carries both benchmark fields, which is why lifting
it out is value-preserving (CON-004). The data-layer fallback engages only when
``wholesale_rate_vnd_per_kwh`` is absent or zero.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "market_proxy_fraction",
    "resolve_market_reference_series",
]

_HOURS = 8760

_PROXY_METHOD = "hourly_evn_tariff_scaled_by_wholesale_ratio"
_PROXY_NOTES = [
    "Proxy uses the repo wholesale benchmark divided by the weighted EVN tariff and scales the hourly EVN retail series by that ratio.",
    "Replace with actual hourly CFMP/FMP once a trusted market series is available.",
]


def _pad_to_8760(series: list[float]) -> list[float]:
    values = [float(value) for value in series[: _HOURS]]
    if len(values) < _HOURS:
        values.extend([0.0] * (_HOURS - len(values)))
    return values


def _wholesale_reference(extracted: dict[str, Any], vn: Any | None) -> float:
    wholesale = extracted.get("benchmark", {}).get("wholesale_rate_vnd_per_kwh")
    if wholesale:
        return float(wholesale)
    # Absent or zero: resolve from the market-prices data layer.
    if vn is None:
        from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

        vn = load_vietnam_data()
    from reopt_pysam_vn.common.assumptions import market_wholesale_reference_vnd_per_kwh

    return market_wholesale_reference_vnd_per_kwh(vn)


def market_proxy_fraction(extracted: dict[str, Any], *, vn: Any | None = None) -> float:
    """Return ``wholesale_reference / weighted_retail``, or ``0.0`` when the
    denominator is zero."""
    weighted = float(
        extracted.get("benchmark", {}).get("weighted_evn_price_vnd_per_kwh") or 0.0
    )
    wholesale = _wholesale_reference(extracted, vn)
    return wholesale / weighted if weighted else 0.0


def resolve_market_reference_series(
    extracted: dict[str, Any], *, vn: Any | None = None
) -> tuple[list[float], str, dict[str, Any]]:
    """Return ``(series_vnd_per_kwh_8760, market_reference_price_type, provenance)``.

    ``provenance`` carries ``{"method", "proxy_fraction_of_evn", "notes"}``.
    Resolution follows S2: an explicit CFMP/FMP series wins, then the proxy.
    """
    cfmp = extracted.get("cfmp_vnd_per_mwh")
    if cfmp:
        series = [value / 1_000.0 for value in _pad_to_8760(list(cfmp))]
        return series, "cfmp", {
            "method": "extracted_cfmp_vnd_per_mwh",
            "proxy_fraction_of_evn": None,
            "notes": ["CFMP series supplied directly (VND/MWh, converted to VND/kWh)."],
        }

    fmp = extracted.get("fmp_vnd_per_mwh")
    if fmp:
        series = [value / 1_000.0 for value in _pad_to_8760(list(fmp))]
        return series, "fmp", {
            "method": "extracted_fmp_vnd_per_mwh",
            "proxy_fraction_of_evn": None,
            "notes": ["FMP series supplied directly (VND/MWh, converted to VND/kWh)."],
        }

    retail = _pad_to_8760(extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"])
    fraction = market_proxy_fraction(extracted, vn=vn)
    series = [rate * fraction for rate in retail]
    return series, "proxy_cfmp_or_fmp", {
        "method": _PROXY_METHOD,
        "proxy_fraction_of_evn": fraction,
        "notes": list(_PROXY_NOTES),
    }
