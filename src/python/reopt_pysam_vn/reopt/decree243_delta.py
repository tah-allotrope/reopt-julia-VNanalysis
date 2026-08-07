"""Fixed-dispatch (no re-optimization) first-order quantification of the
Decree 243/2026 rooftop-solar export-cap change (20% -> 50%, effective
2026-06-26), using the repo's own hourly settlement engine
(``reopt_pysam_vn.integration.settlement``) against a tracked REopt solve.

This deliberately does NOT re-optimize PV/BESS sizing under the new cap --
it answers "given an already-solved dispatch, how much more surplus energy
becomes exportable" as a lower-bound, deterministic number computable from
tracked inputs alone. See plans/2026-07-18-decree-243-currency-webapp-hardening-plan.md
PHASE-03.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.integration.settlement import (
    PRESET_CONTRACTS,
    compute_hourly_settlement,
)
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

__all__ = ["compute_export_cap_delta", "extract_saigon18_series"]

_DEFAULT_EXCHANGE_RATE_VND_PER_USD = _resolve_exchange_rate(load_vietnam_data(), caller_value=26_400.0)

_PV_GENERATION_SERIES_KEYS = (
    "electric_to_load_series_kw",
    "electric_to_grid_series_kw",
    "electric_to_storage_series_kw",
    "electric_curtailed_series_kw",
)


def extract_saigon18_series(
    results_json_path: str | Path,
    *,
    exchange_rate_vnd_per_usd: float = _DEFAULT_EXCHANGE_RATE_VND_PER_USD,
) -> dict[str, list[float]]:
    """Read a REopt results JSON and return the three 8760-length series
    needed for a Decree 243 export-cap delta: hourly load (kW), hourly PV
    generation (kW, summed across all four PV disposition series), and
    hourly EVN tariff (VND/kWh, converted from the REopt USD/kWh series).

    Raises ``KeyError`` naming the missing JSON path if any required series
    is absent, or ``ValueError`` if any series does not have length 8760.
    """
    path = Path(results_json_path)
    with open(path, "r", encoding="utf-8-sig") as f:
        d: dict[str, Any] = json.load(f)

    try:
        loads_kw = list(d["ElectricLoad"]["load_series_kw"])
    except KeyError as exc:
        raise KeyError(f"missing ElectricLoad.load_series_kw in {path}") from exc

    try:
        pv = d["PV"]
        generation_kw = [0.0] * len(pv[_PV_GENERATION_SERIES_KEYS[0]])
        for key in _PV_GENERATION_SERIES_KEYS:
            series = pv[key]
            generation_kw = [g + float(v) for g, v in zip(generation_kw, series)]
    except KeyError as exc:
        raise KeyError(f"missing one of PV.{_PV_GENERATION_SERIES_KEYS} in {path}") from exc

    try:
        tariff_usd_per_kwh = d["ElectricTariff"]["energy_rate_series"]["Tier_1"]
    except KeyError as exc:
        raise KeyError(
            f"missing ElectricTariff.energy_rate_series.Tier_1 in {path}"
        ) from exc
    tariff_vnd_per_kwh = [float(v) * exchange_rate_vnd_per_usd for v in tariff_usd_per_kwh]

    for name, series in (
        ("loads_kw", loads_kw),
        ("generation_kw", generation_kw),
        ("tariff_vnd_per_kwh", tariff_vnd_per_kwh),
    ):
        if len(series) != 8760:
            raise ValueError(f"{name} from {path} has length {len(series)}, expected 8760")

    return {
        "loads_kw": loads_kw,
        "generation_kw": generation_kw,
        "tariff_vnd_per_kwh": tariff_vnd_per_kwh,
    }


def compute_export_cap_delta(
    loads_kw: list[float],
    generation_kw: list[float],
    tariff_vnd_per_kwh: list[float],
    *,
    exchange_rate_vnd_per_usd: float = _DEFAULT_EXCHANGE_RATE_VND_PER_USD,
) -> dict[str, float]:
    """Compare the Decree 57 (20% cap) and Decree 243 (50% cap) private-wire
    export presets on the same fixed hourly dispatch and return the annual
    exported/curtailed energy and surplus revenue under each cap, plus the
    deltas in VND/yr and USD/yr.

    ``fmp_vnd_kwh`` is fixed at zero for all 8760 hours: ``compute_hourly_settlement``
    only reads the FMP series in ``virtual_cfd`` mode, and both presets
    compared here are ``private_wire``.

    Raises ``ValueError`` unless all three input series have length 8760.
    """
    for name, series in (
        ("loads_kw", loads_kw),
        ("generation_kw", generation_kw),
        ("tariff_vnd_per_kwh", tariff_vnd_per_kwh),
    ):
        if len(series) != 8760:
            raise ValueError(f"{name} has length {len(series)}, expected 8760")

    fmp_vnd_kwh = [0.0] * 8760

    cap20 = PRESET_CONTRACTS["decree57_private_wire_standard"]
    cap50 = PRESET_CONTRACTS["decree243_export_50pct_standard"]

    result_cap20 = compute_hourly_settlement(
        loads_kw, generation_kw, tariff_vnd_per_kwh, fmp_vnd_kwh, cap20
    )
    result_cap50 = compute_hourly_settlement(
        loads_kw, generation_kw, tariff_vnd_per_kwh, fmp_vnd_kwh, cap50
    )

    exported_kwh_cap20 = result_cap20.annual_summary["exported_mwh"] * 1000.0
    exported_kwh_cap50 = result_cap50.annual_summary["exported_mwh"] * 1000.0
    curtailed_kwh_cap20 = result_cap20.annual_summary["curtailed_mwh"] * 1000.0
    curtailed_kwh_cap50 = result_cap50.annual_summary["curtailed_mwh"] * 1000.0

    surplus_revenue_vnd_cap20 = exported_kwh_cap20 * cap20.surplus_rate_vnd_kwh
    surplus_revenue_vnd_cap50 = exported_kwh_cap50 * cap50.surplus_rate_vnd_kwh

    delta_exported_kwh = exported_kwh_cap50 - exported_kwh_cap20
    delta_surplus_revenue_vnd = surplus_revenue_vnd_cap50 - surplus_revenue_vnd_cap20
    delta_surplus_revenue_usd = delta_surplus_revenue_vnd / exchange_rate_vnd_per_usd

    return {
        "exported_kwh_cap20": exported_kwh_cap20,
        "exported_kwh_cap50": exported_kwh_cap50,
        "curtailed_kwh_cap20": curtailed_kwh_cap20,
        "curtailed_kwh_cap50": curtailed_kwh_cap50,
        "surplus_revenue_vnd_cap20": surplus_revenue_vnd_cap20,
        "surplus_revenue_vnd_cap50": surplus_revenue_vnd_cap50,
        "delta_exported_kwh": delta_exported_kwh,
        "delta_surplus_revenue_vnd": delta_surplus_revenue_vnd,
        "delta_surplus_revenue_usd": delta_surplus_revenue_usd,
    }
