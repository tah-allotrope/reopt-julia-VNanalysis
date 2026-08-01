"""Samsung SEVT - TTC Duc Hue 2 grid-connected DPPA economics case.

.. deprecated:: 2026-06-14 (Sprint 3)
    Prefer the generalized front door ``reopt_pysam_vn.analysis.run_offsite_dppa``
    (and the ``python -m reopt_pysam_vn.analysis offsite_dppa`` CLI), which reproduces
    this module's combined-decision bit-for-bit (``test_samsung_ttc_parity``) and is the
    first-class entry point for offsite/DPPA analysis. This module remains the registered
    orchestration engine behind ``run_offsite_dppa`` and keeps its own tests; a future
    cycle will invert the delegation and reduce it to a thin wrapper. See
    ``docs/onsite_vs_offsite.md``.

Vietnam's first grid-connected DPPA (live 2026-06-01): Samsung Electronics
Vietnam Thai Nguyen (SEVT, buyer, north) takes ~70 GWh/yr of solar from the
TTC Duc Hue 2 plant (49 MWp / ~41.4 MWac ground-mount, Tay Ninh, south) under
a financial / contract-for-differences settlement.

This module REUSES the tested synthetic-DPPA settlement engine in
``dppa_case_2.py`` (strike, CFMP/FMP market reference, matched-quantity CfD,
buyer benchmark, developer screen). It only supplies the deal-specific pieces:
a synthetic megafactory buyer load, a fixed-sizing scenario (PV pinned to the
built 49 MWp plant, no BESS), and a strike anchored to the Southern
ground-mount solar ceiling.

All commercial terms (strike, tenor, KPP/grid fee) are undisclosed and
triangulated from the market landscape; every artifact this module produces is
flagged ``directional`` with an explicit strike + market-reference basis.
See research/2026-06-04_samsung-ttc-dppa.md.
"""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from reopt_pysam_vn.integration.dppa_case_2 import (
    build_dppa_case_2_buyer_benchmark,
    build_dppa_case_2_contract_risk_sensitivity,
    build_dppa_case_2_physical_summary,
    build_dppa_case_2_settlement_inputs,
    run_dppa_case_2_buyer_settlement,
)
from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.reopt.preprocess import apply_vietnam_defaults, load_vietnam_data

# --- Disclosed deal facts (multi-source; see research brief) ------------------
SAMSUNG_TTC_SOLAR_MWP = 49.0
SAMSUNG_TTC_SOLAR_MWAC = 41.4
SAMSUNG_TTC_ANNUAL_SOLAR_GWH = 70.0
SAMSUNG_TTC_CO2_AVOIDED_TONNES = 46_000.0
SAMSUNG_TTC_COD_DATE = "2026-05-19"
SAMSUNG_TTC_DPPA_LIVE_DATE = "2026-06-01"

# Generation site: Duc Hue 2, Tay Ninh province (south). Buyer SEVT is in the
# north (Thai Nguyen); the modeling Site uses the SOLAR location because that
# drives the PV resource. The buyer location is recorded in the definition.
SAMSUNG_TTC_SOLAR_SITE = {
    "latitude": 10.88,
    "longitude": 106.28,
    "region": "south",
    # SEVT industrial connection. No public voltage disclosure -> default 110 kV
    # (high_voltage_above_35kv_below_220kv, standard multiplier 0.85). 220 kV is
    # plausible at this scale; the rate delta vs 110 kV is ~1%.
    "voltage_level": "high_voltage_above_35kv_below_220kv",
    "customer_type": "industrial",
}
SAMSUNG_TTC_BUYER_LOCATION = "Yen Binh Industrial Park, Thai Nguyen province (north)"

# --- Triangulated assumptions (labelled; not disclosed) -----------------------
# Q1: SEVT total annual load is not public. SEVT is "Samsung's largest
# smartphone production base" (>50% of global output); the 70 GWh pilot is a
# small slice. Model a high-load-factor megafactory at ~1,000 GWh/yr so the
# 70 GWh is ~7% RE share and dwarfs the 41.4 MWac solar peak (full matching).
SAMSUNG_TTC_TARGET_ANNUAL_LOAD_KWH = 1_000_000_000.0
SAMSUNG_TTC_BUYER_LOAD_SOURCE = "synthetic_megafactory_high_load_factor"

# Strike anchor: Southern ground-mount no-storage ceiling (Decree 57 caps the
# grid-DPPA forward price at the RE-type ceiling generation tariff). This is the
# repo tariff value decree_57_dppa.solar_ceiling_tariffs.ground_mounted_no_storage
# .range_min (South). Used as the directional base strike.
SOUTHERN_GROUND_MOUNT_CEILING_VND_PER_KWH = 1012.0

# Developer (TTC) finance assumptions for the directional Single Owner screen.
# Vietnam utility ground-mount solar capex ~ $700-900/kW; use the scenario's
# $750/kW. Revenue is taken on the contracted (calibrated 70 GWh) volume, which
# is conservative vs the plant's full physical yield. All directional.
SAMSUNG_TTC_INSTALLED_COST_USD_PER_KW = 750.0

# Already the canonical rate (ASM-002); routed through the resolver so no bare
# FX literal remains, but the caller_value pin keeps this parity-gated path
# byte-identical (RISK-05-02) - see plans/2026-07-26-post-backlog-architecture-plan.md.
EXCHANGE_RATE_VND_PER_USD = _resolve_exchange_rate(load_vietnam_data(), caller_value=26_400.0)
WHOLESALE_RATE_VND_PER_KWH = 671.0
WHOLESALE_RATE_USD_PER_KWH = 0.0254
DATA_YEAR = 2024

# Solar 8760 sources for the fixed 49 MWp plant. Preferred path is PySAM PVWatts
# v8 driven by the cached southern-Vietnam Himawari resource (real irradiance
# shape), scaled to the disclosed ~70 GWh. When PySAM/resource is unavailable, a
# deterministic representative profile (half-sine arc x seasonal) is used instead.
# Both are non-site-specific (resource is Khanh Hoa, not Tay Ninh) and flagged.
SAMSUNG_TTC_SOLAR_PROFILE_SOURCE = "synthetic_clear_sky_south_calibrated"
SAMSUNG_TTC_PVWATTS_PROFILE_SOURCE = "pvwatts_v8_cached_south_himawari_calibrated_70gwh"


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def build_samsung_synthetic_load_8760(
    total_annual_kwh: float = SAMSUNG_TTC_TARGET_ANNUAL_LOAD_KWH,
    *,
    reference_year: int = DATA_YEAR,
) -> list[float]:
    """Deterministic 8760 high-load-factor electronics-megafactory profile.

    Continuous 24/7 fab base with a mild day-shift diurnal lift and a light
    Sunday dip, normalized to sum to ``total_annual_kwh`` exactly. Shaped so the
    minimum hourly load stays well above the 41.4 MWac solar peak.
    """
    hours = 8760
    start = datetime(reference_year, 1, 1)
    weights: list[float] = []
    for hour_index in range(hours):
        ts = start + timedelta(hours=hour_index)
        diurnal = 1.0 + 0.12 * math.sin(2.0 * math.pi * (ts.hour - 8) / 24.0)
        weekly = 0.93 if ts.weekday() == 6 else 1.0  # Sunday dip
        weights.append(max(0.1, diurnal * weekly))
    average_weight = sum(weights) / len(weights)
    base = total_annual_kwh / hours
    series = [base * (weight / average_weight) for weight in weights]
    scale = total_annual_kwh / sum(series)
    return [value * scale for value in series]


def _build_hourly_rate_series(
    tariff_data: dict,
    customer_type: str,
    voltage_level: str,
    year: int = DATA_YEAR,
) -> list[float]:
    base_vnd = tariff_data["base_avg_price_vnd_per_kwh"]
    schedule = tariff_data["tou_schedule"]
    multipliers = tariff_data["rate_multipliers"][customer_type][voltage_level]

    def daily(block: dict) -> list[float]:
        rates = [base_vnd * multipliers["standard"]] * 24
        for hour in block.get("peak_hours", []):
            rates[int(hour)] = base_vnd * multipliers["peak"]
        for hour in block.get("offpeak_hours", []):
            rates[int(hour)] = base_vnd * multipliers["offpeak"]
        for hour in block.get("standard_hours", []):
            rates[int(hour)] = base_vnd * multipliers["standard"]
        return rates

    weekday_rates = daily(schedule["weekday"])
    sunday_rates = daily(
        schedule.get("sunday_and_public_holidays", schedule["weekday"])
    )

    rates: list[float] = []
    cursor = datetime(year, 1, 1)
    for _ in range(366 if _is_leap_year(year) else 365):
        rates.extend(sunday_rates if cursor.weekday() == 6 else weekday_rates)
        cursor += timedelta(days=1)
    return rates


def _southern_ground_mount_ceiling(tariff_data: dict) -> float:
    try:
        return float(
            tariff_data["decree_57_dppa"]["solar_ceiling_tariffs_vnd_per_kwh"][
                "ground_mounted_no_storage"
            ]["range_min"]
        )
    except (KeyError, TypeError):
        return SOUTHERN_GROUND_MOUNT_CEILING_VND_PER_KWH


def build_samsung_ttc_extracted_inputs(
    *,
    total_annual_load_kwh: float = SAMSUNG_TTC_TARGET_ANNUAL_LOAD_KWH,
) -> dict:
    """Build the Case-2-compatible ``extracted`` contract for the Samsung deal.

    Synthetic megafactory load + SEVT EVN tariff series + load-weighted benchmark
    + Southern-ceiling strike basis. No file IO beyond loading the tariff data.
    """
    vn = load_vietnam_data()
    tariff_data = vn.tariff
    site: Dict[str, Any] = dict(SAMSUNG_TTC_SOLAR_SITE)
    customer_type = site["customer_type"]
    voltage_level = site["voltage_level"]

    loads_kw = build_samsung_synthetic_load_8760(total_annual_load_kwh)
    tou_rates_vnd = _build_hourly_rate_series(tariff_data, customer_type, voltage_level)

    annual_load_kwh = sum(loads_kw)
    paired = zip(loads_kw, tou_rates_vnd)
    weighted_vnd = sum(load * rate for load, rate in paired) / annual_load_kwh
    multiplier_block = tariff_data["rate_multipliers"][customer_type][voltage_level]
    base_vnd = tariff_data["base_avg_price_vnd_per_kwh"]
    ceiling_vnd = _southern_ground_mount_ceiling(tariff_data)

    return {
        "project": "Samsung SEVT - TTC Duc Hue 2 grid-connected DPPA economics",
        "data_year": DATA_YEAR,
        "site": site,
        "buyer_location": SAMSUNG_TTC_BUYER_LOCATION,
        "loads_kw": loads_kw,
        "buyer_load": {
            "source": SAMSUNG_TTC_BUYER_LOAD_SOURCE,
            "total_annual_gwh": annual_load_kwh / 1_000_000.0,
            "re_share_of_total": (SAMSUNG_TTC_ANNUAL_SOLAR_GWH * 1e6)
            / annual_load_kwh,
            "basis": "directional",
            "notes": [
                "SEVT total consumption is not public; modeled as a high-load-factor "
                "megafactory so the 70 GWh contracted slice is fully matched.",
            ],
        },
        "benchmark": {
            "annual_load_kwh": annual_load_kwh,
            "annual_load_gwh": annual_load_kwh / 1_000_000.0,
            "weighted_evn_price_vnd_per_kwh": weighted_vnd,
            "weighted_evn_price_usd_per_kwh": weighted_vnd / EXCHANGE_RATE_VND_PER_USD,
            "exchange_rate_vnd_per_usd": EXCHANGE_RATE_VND_PER_USD,
            "peak_rate_vnd_per_kwh": base_vnd * multiplier_block["peak"],
            "standard_rate_vnd_per_kwh": base_vnd * multiplier_block["standard"],
            "offpeak_rate_vnd_per_kwh": base_vnd * multiplier_block["offpeak"],
            "wholesale_rate_vnd_per_kwh": WHOLESALE_RATE_VND_PER_KWH,
            "wholesale_rate_usd_per_kwh": WHOLESALE_RATE_USD_PER_KWH,
        },
        "evn_tariff": {
            "tou_energy_rates_vnd_per_kwh": tou_rates_vnd,
            "tou_energy_rates_usd_per_kwh": [
                rate / EXCHANGE_RATE_VND_PER_USD for rate in tou_rates_vnd
            ],
        },
        "strike_basis": {
            "anchor": "southern_ground_mount_no_storage_ceiling",
            "southern_ground_mount_ceiling_vnd_per_kwh": ceiling_vnd,
            "sweep_top_basis": "evn_standard_hour_avoided_cost",
            "regulatory_cap_note": (
                "Decree 57 caps the grid-DPPA forward price at the RE-type ceiling "
                "generation tariff (Southern ground-mount no-storage ~1,012 VND/kWh). "
                "Sweep points above the ceiling are sensitivity-only."
            ),
            "basis": "directional",
        },
        "assumptions": {
            "customer_type": customer_type,
            "voltage_level": voltage_level,
            "region": site["region"],
            "buyer_load_source": SAMSUNG_TTC_BUYER_LOAD_SOURCE,
            "voltage_default_note": "No public SEVT connection-voltage disclosure; 110 kV default.",
        },
    }


def build_samsung_ttc_definition(extracted: dict) -> dict:
    """Deal definition artifact recording disclosed facts + directional caveat."""
    return {
        "case": "DPPA_SAMSUNG_TTC",
        "title": "Samsung SEVT - TTC Duc Hue 2 grid-connected DPPA (Vietnam's first)",
        "parties": {
            "buyer": "Samsung Electronics Vietnam Thai Nguyen (SEVT)",
            "buyer_location": SAMSUNG_TTC_BUYER_LOCATION,
            "generator": "TTC Duc Hue 2 (developer: TTC Duc Hue-Long An Power JSC)",
        },
        "plant": {
            "capacity_mwp": SAMSUNG_TTC_SOLAR_MWP,
            "capacity_mwac": SAMSUNG_TTC_SOLAR_MWAC,
            "technology": "ground_mounted_solar_no_storage",
            "province": "Tay Ninh (south)",
            "cod_date": SAMSUNG_TTC_COD_DATE,
        },
        "contract": {
            "annual_solar_gwh": SAMSUNG_TTC_ANNUAL_SOLAR_GWH,
            "co2_avoided_tonnes_per_year": SAMSUNG_TTC_CO2_AVOIDED_TONNES,
            "mechanism": "grid_connected_dppa_decree_57_2025",
            "settlement_mechanism": "financial_cfd",
            "dppa_live_date": SAMSUNG_TTC_DPPA_LIVE_DATE,
            "tenor_years": 20,
            "tenor_basis": "assumed_matches_financial_analysis_horizon",
        },
        "strike_basis": dict(extracted["strike_basis"]),
        "quality": {
            "basis": "directional",
            "caveat": (
                "All commercial terms (strike, tenor, KPP/grid fee) are undisclosed "
                "and triangulated; headline numbers ride on the assumed strike and a "
                "proxy CFMP series. Treat as directional, not bankable."
            ),
        },
    }


def samsung_strike_vnd_per_kwh(
    extracted: dict,
    sweep_fraction: float = 0.0,
    *,
    sweep_top_vnd_per_kwh: float | None = None,
) -> float:
    """Strike price anchored to the Southern ceiling, sweepable toward avoided cost.

    ``sweep_fraction = 0`` returns the directional base strike (Southern
    ground-mount ceiling). ``sweep_fraction = 1`` returns the sweep top (EVN
    standard-hour avoided cost by default), used to bracket the buyer-premium
    surface in PHASE-03. Strikes above the ceiling are regulatory sensitivity
    points only.
    """
    base = float(extracted["strike_basis"]["southern_ground_mount_ceiling_vnd_per_kwh"])
    if sweep_top_vnd_per_kwh is None:
        top = float(extracted["benchmark"]["standard_rate_vnd_per_kwh"])
    else:
        top = float(sweep_top_vnd_per_kwh)
    return base + float(sweep_fraction) * (top - base)


def build_scenario_samsung_ttc(extracted: dict) -> dict:
    """Fixed-sizing REopt scenario: PV pinned to the built 49 MWp, no BESS, no wind.

    Clone of ``build_scenario_dppa_case_2`` with the optimization removed because
    the deal's plant is already built and fixed.
    """
    fixed_pv_dc_kw = SAMSUNG_TTC_SOLAR_MWP * 1000.0
    dc_ac_ratio = SAMSUNG_TTC_SOLAR_MWP / SAMSUNG_TTC_SOLAR_MWAC
    site = extracted["site"]
    scenario = {
        "Site": {
            "latitude": site["latitude"],
            "longitude": site["longitude"],
        },
        "ElectricLoad": {
            "loads_kw": [float(value) for value in extracted["loads_kw"]],
            "year": extracted.get("data_year", DATA_YEAR),
        },
        "PV": {
            "min_kw": fixed_pv_dc_kw,
            "max_kw": fixed_pv_dc_kw,
            "installed_cost_per_kw": 750.0,
            "om_cost_per_kw": 6.0,
            "location": "ground",
            "tilt": site["latitude"],
            "azimuth": 180.0,
            "dc_ac_ratio": dc_ac_ratio,
            "losses": 0.14,
            "can_wholesale": True,
            "can_net_meter": False,
            "can_export_beyond_nem_limit": True,
            "can_curtail": True,
        },
        "Wind": {
            "min_kw": 0.0,
            "max_kw": 0.0,
            "production_factor_series": [],
        },
        "ElectricStorage": {
            "min_kw": 0.0,
            "max_kw": 0.0,
            "min_kwh": 0.0,
            "max_kwh": 0.0,
        },
        "Financial": {
            "analysis_years": 20,
            "owner_tax_rate_fraction": 0.0575,
            "offtaker_tax_rate_fraction": 0.20,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.04,
        },
        "_meta": {
            "scenario": "DPPA_SAMSUNG_TTC",
            "name": "Samsung SEVT - TTC Duc Hue 2 fixed-plant grid DPPA",
            "site": dict(site),
            "buyer_location": extracted.get("buyer_location", SAMSUNG_TTC_BUYER_LOCATION),
            "description": (
                "Fixed-plant synthetic/financial DPPA. PV pinned to the built "
                "49 MWp (~41.4 MWac) Duc Hue 2 plant, no storage; buyer settlement "
                "computed in post-processing under a matched-volume CfD ledger."
            ),
            "contract_type": "synthetic_financial_dppa",
            "buyer_settlement_model": "post_processed_hourly_cfd",
            "storage_requirement": "none_fixed_plant",
            "plant_capacity_mwp": SAMSUNG_TTC_SOLAR_MWP,
            "plant_capacity_mwac": SAMSUNG_TTC_SOLAR_MWAC,
            "buyer_load_source": SAMSUNG_TTC_BUYER_LOAD_SOURCE,
            "quality_basis": "directional",
        },
    }
    vietnam_data = load_vietnam_data()
    apply_vietnam_defaults(
        scenario,
        vietnam_data,
        customer_type=site["customer_type"],
        voltage_level=site["voltage_level"],
        region=site["region"],
        pv_type="ground",
        wind_type="onshore",
        apply_financials=False,
        apply_tariff=True,
        apply_emissions=True,
        apply_tech_costs=False,
        apply_export_rules=True,
        apply_zero_incentives=True,
    )
    scenario["ElectricTariff"].pop("tou_energy_rates_vnd_per_kwh", None)
    return scenario


# --- PHASE-02: solar generation, REopt-shaped results, buyer settlement -------
def _calibrate_to_target(
    series: list[float], annual_target_kwh: float, cap_kw: float
) -> list[float]:
    """Scale a shape to the annual target, AC-clip, and redistribute clip loss."""
    total = sum(series)
    scale = annual_target_kwh / total if total else 0.0
    out = [min(value * scale, cap_kw) for value in series]
    deficit = annual_target_kwh - sum(out)
    if deficit > 1.0:
        headroom = [cap_kw - value for value in out]
        head_total = sum(headroom)
        if head_total > 0.0:
            out = [
                value + deficit * (room / head_total)
                for value, room in zip(out, headroom)
            ]
    return out


def _synthetic_south_solar_8760(
    annual_target_kwh: float, cap_kw: float, reference_year: int
) -> list[float]:
    """Deterministic representative southern profile (half-sine arc x seasonal)."""
    start = datetime(reference_year, 1, 1)
    weights: list[float] = []
    for hour_index in range(8760):
        ts = start + timedelta(hours=hour_index)
        hour = ts.hour
        arc = math.sin(math.pi * (hour - 6) / 12.0) if 6 <= hour < 18 else 0.0
        day_of_year = ts.timetuple().tm_yday
        # Southern Vietnam: dry season (~Jan) sunnier, wet season (~Jul) cloudier.
        seasonal = 1.0 + 0.18 * math.cos(2.0 * math.pi * (day_of_year - 15) / 365.0)
        weights.append(max(0.0, arc * seasonal))
    return _calibrate_to_target(weights, annual_target_kwh, cap_kw)


def _pvwatts_south_solar_8760(
    system_capacity_kw_dc: float,
    dc_ac_ratio: float,
    *,
    losses_pct: float = 14.0,
    inv_eff_pct: float = 96.0,
    resource_file: str | None = None,
) -> list[float] | None:
    """Run PySAM PVWatts v8 on the cached southern resource. None if unavailable."""
    try:
        import PySAM.Pvwattsv8 as pv
    except Exception:
        return None
    default_resource_file: Path | None = None
    try:
        from reopt_pysam_vn.pysam.pvwatts_battery import DEFAULT_SOLAR_RESOURCE_FILE as default_resource_file
    except Exception:
        pass
    resource = Path(resource_file) if resource_file else default_resource_file
    if resource is None or not Path(resource).is_file():
        return None
    try:
        model = pv.default("PVWattsSingleOwner")
        model.SolarResource.solar_resource_file = str(resource)
        model.SystemDesign.system_capacity = float(system_capacity_kw_dc)
        model.SystemDesign.dc_ac_ratio = float(dc_ac_ratio)
        model.SystemDesign.inv_eff = float(inv_eff_pct)
        model.SystemDesign.losses = float(losses_pct)
        model.execute(0)
        gen = list(model.Outputs.gen)
    except Exception:
        return None
    series = [max(0.0, float(value)) for value in gen[:8760]]
    if len(series) < 8760:
        series.extend([0.0] * (8760 - len(series)))
    return series


def build_samsung_ttc_solar_profile(
    extracted: dict | None = None,
    *,
    annual_target_kwh: float = SAMSUNG_TTC_ANNUAL_SOLAR_GWH * 1e6,
    use_pysam: bool = True,
    reference_year: int = DATA_YEAR,
) -> dict:
    """Build the fixed 49 MWp solar 8760 with provenance.

    Prefers PySAM PVWatts v8 (cached southern Himawari resource) for a real
    irradiance shape, scaled to the disclosed ~70 GWh; falls back to the
    deterministic synthetic profile when PySAM/resource is unavailable.
    """
    cap_kw = SAMSUNG_TTC_SOLAR_MWAC * 1000.0
    dc_kw = SAMSUNG_TTC_SOLAR_MWP * 1000.0
    dc_ac_ratio = SAMSUNG_TTC_SOLAR_MWP / SAMSUNG_TTC_SOLAR_MWAC

    pvwatts = (
        _pvwatts_south_solar_8760(dc_kw, dc_ac_ratio) if use_pysam else None
    )
    if pvwatts is not None and sum(pvwatts) > 0.0:
        native_annual_gwh = sum(pvwatts) / 1e6
        series = _calibrate_to_target(pvwatts, annual_target_kwh, cap_kw)
        source = SAMSUNG_TTC_PVWATTS_PROFILE_SOURCE
        resource_note = (
            "PySAM PVWatts v8 on the cached southern-Vietnam Himawari 2019 resource "
            "(Khanh Hoa site, not Tay Ninh-specific); hourly shape scaled to the "
            "disclosed 70 GWh."
        )
    else:
        native_annual_gwh = None
        series = _synthetic_south_solar_8760(annual_target_kwh, cap_kw, reference_year)
        source = SAMSUNG_TTC_SOLAR_PROFILE_SOURCE
        resource_note = (
            "PySAM unavailable; deterministic representative southern profile "
            "calibrated to the disclosed 70 GWh."
        )
    return {
        "series_kw": series,
        "source": source,
        "native_annual_gwh": native_annual_gwh,
        "calibrated_to_gwh": annual_target_kwh / 1e6,
        "resource_note": resource_note,
    }


def generate_samsung_ttc_solar_8760(
    extracted: dict | None = None,
    *,
    annual_target_kwh: float = SAMSUNG_TTC_ANNUAL_SOLAR_GWH * 1e6,
    use_pysam: bool = True,
    reference_year: int = DATA_YEAR,
) -> list[float]:
    """Fixed 49 MWp solar 8760 (kW AC) — PVWatts when available, else synthetic.

    The deal plant is built and fixed, so no optimization is needed; this only
    supplies the hourly generation shape, calibrated to the disclosed ~70 GWh.
    """
    return build_samsung_ttc_solar_profile(
        extracted,
        annual_target_kwh=annual_target_kwh,
        use_pysam=use_pysam,
        reference_year=reference_year,
    )["series_kw"]


def build_samsung_ttc_results(
    solar_kw: list[float],
    extracted: dict,
    *,
    solar_profile_source: str = SAMSUNG_TTC_SOLAR_PROFILE_SOURCE,
) -> dict:
    """Pack the fixed solar 8760 into the REopt ``results`` shape the Case-2
    settlement and physical-summary helpers consume (no Julia solve).

    The buyer load dwarfs solar at every hour, so all generation serves load
    (no export); the grid supplies the residual.
    """
    load = [float(value) for value in extracted["loads_kw"]]
    horizon = len(solar_kw)
    to_load: list[float] = []
    to_grid: list[float] = []
    grid_supply: list[float] = []
    for index in range(horizon):
        generation = float(solar_kw[index])
        demand = load[index] if index < len(load) else 0.0
        matched = min(generation, demand)
        to_load.append(matched)
        to_grid.append(max(0.0, generation - matched))
        grid_supply.append(max(0.0, demand - matched))
    annual_kwh = sum(solar_kw)
    zeros = [0.0] * horizon

    return {
        "status": "synthetic_fixed_plant_no_solve",
        "PV": {
            "size_kw": SAMSUNG_TTC_SOLAR_MWP * 1000.0,
            "size_kw_ac": SAMSUNG_TTC_SOLAR_MWAC * 1000.0,
            "year_one_energy_produced_kwh": annual_kwh,
            "electric_to_load_series_kw": to_load,
            "electric_to_grid_series_kw": to_grid,
            "electric_to_storage_series_kw": zeros,
            "electric_curtailed_series_kw": zeros,
        },
        "Wind": {
            "size_kw": 0.0,
            "electric_to_load_series_kw": [],
            "electric_to_grid_series_kw": [],
        },
        "ElectricStorage": {"size_kw": 0.0, "size_kwh": 0.0},
        "ElectricUtility": {"electric_to_load_series_kw": grid_supply},
        "Financial": {
            "npv": None,
            "analysis_years": 20,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": 0.05,
            # Directional capex for the developer Single Owner screen (PHASE-03).
            "initial_capital_costs": SAMSUNG_TTC_SOLAR_MWP
            * 1000.0
            * SAMSUNG_TTC_INSTALLED_COST_USD_PER_KW,
        },
        "_meta": {
            "solar_profile_source": solar_profile_source,
            "plant_capacity_mwp": SAMSUNG_TTC_SOLAR_MWP,
            "plant_capacity_mwac": SAMSUNG_TTC_SOLAR_MWAC,
            "ac_capacity_factor": annual_kwh
            / (SAMSUNG_TTC_SOLAR_MWAC * 1000.0 * 8760.0),
        },
    }


def analyze_samsung_ttc_settlement(
    extracted: dict,
    *,
    sweep_fraction: float = 0.0,
) -> dict:
    """Run the full PHASE-02 settlement: fixed solar -> Case-2 CfD ledger.

    Reuses the tested Case-2 settlement engine but overrides the strike with the
    Samsung Southern-ceiling anchor and adds a contracted-slice summary plus the
    mandatory ``directional`` quality block (CON-001).
    """
    scenario = build_scenario_samsung_ttc(extracted)
    profile = build_samsung_ttc_solar_profile(extracted)
    solar_kw = profile["series_kw"]
    results = build_samsung_ttc_results(
        solar_kw, extracted, solar_profile_source=profile["source"]
    )

    physical = build_dppa_case_2_physical_summary(results, extracted, scenario)
    settlement_inputs = build_dppa_case_2_settlement_inputs(
        results, extracted, scenario
    )
    strike = samsung_strike_vnd_per_kwh(extracted, sweep_fraction)
    settlement_inputs["strike_price_vnd_per_kwh"] = strike
    settlement = run_dppa_case_2_buyer_settlement(settlement_inputs)
    benchmark = build_dppa_case_2_buyer_benchmark(physical, settlement)

    # Contracted-slice economics: isolate the matched (solar) volume so the deal
    # signal is not diluted by the 930 GWh of non-solar residual load.
    ledger = settlement["hourly_ledger"]
    matched_kwh = float(settlement["summary"]["matched_quantity_kwh"])
    evn_on_matched = sum(
        float(entry["matched_quantity_kwh"])
        * float(entry["evn_retail_rate_vnd_per_kwh"])
        for entry in ledger
    )
    buyer_on_matched = sum(
        float(entry["buyer_evn_matched_payment_vnd"])
        + float(entry["buyer_dppa_charge_vnd"])
        + float(entry["buyer_cfd_payment_vnd"])
        for entry in ledger
    )
    contracted_slice = {
        "matched_quantity_gwh": matched_kwh / 1e6,
        "buyer_cost_on_matched_vnd": buyer_on_matched,
        "evn_avoided_cost_on_matched_vnd": evn_on_matched,
        "buyer_savings_vnd": evn_on_matched - buyer_on_matched,
        "buyer_savings_usd": (evn_on_matched - buyer_on_matched)
        / EXCHANGE_RATE_VND_PER_USD,
        "buyer_effective_cost_vnd_per_kwh": (
            buyer_on_matched / matched_kwh if matched_kwh else 0.0
        ),
        "evn_avoided_cost_vnd_per_kwh": (
            evn_on_matched / matched_kwh if matched_kwh else 0.0
        ),
        "dppa_adder_vnd_per_kwh": float(
            settlement["parameters"]["dppa_adder_vnd_per_kwh"]
        ),
        "kpp_factor": float(settlement["parameters"]["kpp_factor"]),
    }

    solar_summary = {
        "annual_solar_gwh": sum(solar_kw) / 1e6,
        "ac_capacity_factor": results["_meta"]["ac_capacity_factor"],
        "peak_ac_kw": max(solar_kw),
        "solar_profile_source": profile["source"],
        "native_annual_gwh": profile["native_annual_gwh"],
        "resource_note": profile["resource_note"],
    }

    quality = {
        "basis": "directional",
        "strike_vnd_per_kwh": strike,
        "strike_basis": extracted["strike_basis"]["anchor"],
        "market_reference_price_type": settlement["market_reference_price_type"],
        "solar_profile_source": profile["source"],
        "caveat": (
            "Directional only: strike anchored to the Southern ground-mount ceiling, "
            "CfD settled against a proxy CFMP series, solar from a representative "
            "(non-site-specific) southern profile, and the DPPA grid-service adder "
            "inherited from the Case-2 default. Not bankable."
        ),
    }

    return {
        "case": "DPPA_SAMSUNG_TTC",
        "solar_summary": solar_summary,
        "physical": physical,
        "settlement": settlement,
        "benchmark": benchmark,
        "contracted_slice": contracted_slice,
        "quality": quality,
    }


# --- PHASE-03: strike sweep, developer screen, DPPA-adder lever ---------------
def _samsung_ttc_physical_and_settlement_inputs(extracted: dict):
    """Shared setup: fixed-plant scenario, solar profile, REopt-shaped results,
    physical summary, and base Case-2 settlement inputs (CFMP proxy)."""
    scenario = build_scenario_samsung_ttc(extracted)
    profile = build_samsung_ttc_solar_profile(extracted)
    results = build_samsung_ttc_results(
        profile["series_kw"], extracted, solar_profile_source=profile["source"]
    )
    physical = build_dppa_case_2_physical_summary(results, extracted, scenario)
    settlement_inputs = build_dppa_case_2_settlement_inputs(
        results, extracted, scenario
    )
    return scenario, profile, results, physical, settlement_inputs


def build_samsung_ttc_strike_sweep(
    extracted: dict,
    *,
    sweep_fractions: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
    run_developer: bool = True,
    developer_runner=None,
    target_irr_fraction: float | None = None,
) -> dict:
    """Buyer-premium surface across the strike band + PySAM developer IRR/NPV.

    Strike sweeps from the Southern ground-mount ceiling (floor) to the EVN
    standard-hour avoided cost (top). The buyer side is pure tariff math; the
    developer side runs the PySAM Single Owner model at the fixed 49 MWp, varying
    only the PPA price (= strike). All outputs directional.
    """
    from reopt_pysam_vn.integration.assumptions import (
        DEFAULT_TARGET_DEVELOPER_IRR_FRACTION,
    )
    from reopt_pysam_vn.integration.bridge import (
        build_dppa_case_2_single_owner_inputs,
    )

    target_irr = float(
        target_irr_fraction
        if target_irr_fraction is not None
        else DEFAULT_TARGET_DEVELOPER_IRR_FRACTION
    )
    scenario, profile, results, physical, base_inputs = (
        _samsung_ttc_physical_and_settlement_inputs(extracted)
    )
    exchange_rate = float(
        base_inputs.get("exchange_rate_vnd_per_usd") or EXCHANGE_RATE_VND_PER_USD
    )

    developer_base = None
    runner = developer_runner
    if run_developer:
        developer_base = build_dppa_case_2_single_owner_inputs(
            results, scenario, base_inputs
        )
        if runner is None:
            try:
                from reopt_pysam_vn.pysam.single_owner import run_single_owner_model

                runner = run_single_owner_model
            except Exception:
                runner = None

    sweep: list[dict] = []
    for fraction in sweep_fractions:
        strike = samsung_strike_vnd_per_kwh(extracted, fraction)
        candidate = dict(base_inputs)
        candidate["strike_price_vnd_per_kwh"] = strike
        settlement = run_dppa_case_2_buyer_settlement(candidate)
        benchmark = build_dppa_case_2_buyer_benchmark(physical, settlement)
        costs = benchmark["year_one_costs"]
        buyer_savings = float(costs["buyer_savings_vs_evn_vnd"])
        buyer_delta = float(costs["buyer_minus_benchmark_vnd"])
        buyer_passes = buyer_savings > 0.0

        dev_irr = dev_npv = None
        dev_passes = False
        dev_status = "not_run"
        if developer_base is not None and runner is not None:
            try:
                dev_inputs = replace(
                    developer_base,
                    ppa_price_input_usd_per_kwh=float(strike) / exchange_rate,
                    metadata={
                        **dict(developer_base.metadata),
                        "year_one_ppa_price_vnd_per_kwh": float(strike),
                    },
                )
                dev_result = runner(dev_inputs)
                outputs = dev_result.get("outputs", {})
                dev_irr = outputs.get("project_return_aftertax_irr_fraction")
                dev_npv = outputs.get("project_return_aftertax_npv_usd")
                dev_status = dev_result.get("status", "ok")
                dev_passes = dev_irr is not None and float(dev_irr) >= target_irr
            except Exception as exc:  # pragma: no cover - PySAM runtime guard
                dev_status = f"error: {exc}"

        sweep.append(
            {
                "sweep_fraction": float(fraction),
                "strike_vnd_per_kwh": float(strike),
                "strike_usd_per_kwh": float(strike) / exchange_rate,
                "buyer_savings_vs_evn_vnd": buyer_savings,
                "buyer_minus_benchmark_vnd": buyer_delta,
                "buyer_blended_cost_vnd_per_kwh": float(
                    costs["buyer_blended_cost_vnd_per_kwh"]
                ),
                "buyer_passes": buyer_passes,
                "developer_status": dev_status,
                "developer_irr_fraction": (None if dev_irr is None else float(dev_irr)),
                "developer_npv_usd": (None if dev_npv is None else float(dev_npv)),
                "developer_passes": dev_passes,
                "overlap": bool(buyer_passes and dev_passes),
            }
        )

    overlap = [row for row in sweep if row["overlap"]]
    buyer_saves = [row for row in sweep if row["buyer_passes"]]
    if overlap:
        recommended = "buyer_and_developer_overlap"
    elif buyer_saves and developer_base is not None and runner is not None:
        recommended = "buyer_saves_developer_subeconomic"
    elif buyer_saves:
        recommended = "buyer_saves_developer_not_screened"
    else:
        recommended = "no_viable_strike_found"

    return {
        "case": "DPPA_SAMSUNG_TTC",
        "model": "Samsung-TTC DPPA Strike Sweep",
        "strike_band": {
            "floor_vnd_per_kwh": samsung_strike_vnd_per_kwh(extracted, 0.0),
            "ceiling_vnd_per_kwh": samsung_strike_vnd_per_kwh(extracted, 1.0),
            "floor_basis": "southern_ground_mount_no_storage_ceiling",
            "ceiling_basis": "evn_standard_hour_avoided_cost",
            "regulatory_note": (
                "Decree 57 caps the grid-DPPA forward price at the Southern ceiling "
                "(~1,012); strikes above it are sensitivity-only."
            ),
        },
        "developer_screen": {
            "included": developer_base is not None,
            "ran": developer_base is not None and runner is not None,
            "target_irr_fraction": target_irr,
            "system_capacity_kw": (
                None if developer_base is None else float(developer_base.system_capacity_kw)
            ),
            "installed_cost_usd": (
                None if developer_base is None else float(developer_base.installed_cost_usd)
            ),
            "revenue_basis": "contracted_70gwh_conservative",
        },
        "sweep": sweep,
        "negotiation_summary": {
            "overlap_found": bool(overlap),
            "overlap_candidates": overlap,
            "buyer_saves_candidates": buyer_saves,
            "recommended_position": recommended,
        },
        "quality": {
            "basis": "directional",
            "strike_basis": "southern_ceiling_to_evn_avoided_sweep",
            "market_reference_price_type": base_inputs["market_reference_price_type"],
            "solar_profile_source": profile["source"],
            "caveat": (
                "Directional: strike band, proxy CFMP series, non-site-specific solar, "
                "inherited DPPA grid-service adder, and assumed $750/kW developer capex "
                "on the contracted 70 GWh. Not bankable."
            ),
        },
    }


def build_samsung_ttc_adder_sensitivity(
    extracted: dict,
    *,
    adder_multipliers: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0),
) -> dict:
    """DPPA grid-service adder sensitivity at the base (Southern-ceiling) strike.

    The inherited Case-2 adder (523.34 VND/kWh) is the dominant lever on buyer
    cost; this sweep shows where the buyer flips from saving to premium. Reuses
    build_dppa_case_2_contract_risk_sensitivity. Directional.
    """
    _, profile, _, physical, base_inputs = (
        _samsung_ttc_physical_and_settlement_inputs(extracted)
    )
    base_inputs["strike_price_vnd_per_kwh"] = samsung_strike_vnd_per_kwh(extracted, 0.0)
    risk = build_dppa_case_2_contract_risk_sensitivity(
        base_inputs, physical, dppa_adder_multipliers=adder_multipliers
    )
    risk["case"] = "DPPA_SAMSUNG_TTC"
    risk["model"] = "Samsung-TTC DPPA Contract-Risk Sensitivity"
    risk["quality"] = {
        "basis": "directional",
        "strike_vnd_per_kwh": samsung_strike_vnd_per_kwh(extracted, 0.0),
        "market_reference_price_type": base_inputs["market_reference_price_type"],
        "solar_profile_source": profile["source"],
        "caveat": (
            "Directional: the DPPA grid-service adder is inherited from the Case-2 "
            "default (523.34 VND/kWh) and is the single biggest lever on buyer cost; "
            "deal-calibrate before relying on the sign of the buyer result."
        ),
    }
    return risk


# --- PHASE-04: regime stress, combined decision -------------------------------
SAMSUNG_TTC_REGIME_STRESS_IDS = (
    "decision_963_2026_current",
    "decision_14_2025_legacy",
    "decree146_two_part_trial_2026",
)


def build_samsung_ttc_regime_stress(
    extracted: dict,
    *,
    regime_ids: tuple[str, ...] = SAMSUNG_TTC_REGIME_STRESS_IDS,
) -> dict:
    """Stress the buyer's EVN benchmark (outside option) across tariff regimes.

    Uses the GAP-05 ``compute_multi_regime_impact`` on the SEVT load: Decision 963
    (current baseline) vs Decision 14 legacy vs the Decree 146 two-part trial. A
    higher EVN bill under a regime makes the DPPA's avoided cost larger; the
    Decree 146 two-part trial is the key forward risk (capacity charge that can
    also double-charge DPPA volume). Directional.
    """
    from reopt_pysam_vn.reopt.regime_impact import compute_multi_regime_impact

    loads_kw = [float(value) for value in extracted["loads_kw"]]
    customer_type = extracted["site"]["customer_type"]
    voltage_level = extracted["site"]["voltage_level"]
    impacts = compute_multi_regime_impact(
        loads_kw, list(regime_ids), customer_type, voltage_level
    )
    regimes = []
    for impact in impacts:
        regimes.append(
            {
                "regime_id": impact.regime_b.id,
                "regime_name": impact.regime_b.name,
                "annual_bill_vnd": impact.regime_b.annual_bill_vnd,
                "annual_bill_gvnd": impact.regime_b.annual_bill_vnd / 1e9,
                "annual_bill_delta_vnd": impact.delta.annual_bill_delta_vnd,
                "delta_pct": impact.delta.delta_pct,
                "peak_hours_changed": impact.delta.peak_hours_changed,
            }
        )
    return {
        "case": "DPPA_SAMSUNG_TTC",
        "model": "Samsung-TTC DPPA Regime Stress",
        "baseline_regime_id": regime_ids[0],
        "regimes": regimes,
        "interpretation": (
            "Buyer EVN bill (outside option) under each tariff regime. A higher bill "
            "raises the DPPA's avoided-cost value; the Decree 146 two-part trial lifts "
            "the bill via a capacity charge but risks double-charging the DPPA volume."
        ),
        "quality": {
            "basis": "directional",
            "voltage_level": voltage_level,
            "customer_type": customer_type,
            "caveat": (
                "Directional: regime bills are computed on the synthetic SEVT load; "
                "the Decree 146 two-part trial is a paper trial, not yet on actual bills."
            ),
        },
    }


def build_samsung_ttc_combined_decision(
    extracted: dict,
    *,
    run_developer: bool = True,
    developer_runner=None,
) -> dict:
    """Roll up settlement, strike sweep, adder lever, and regime stress into one
    explicit, caveated decision artifact. Directional."""
    base = analyze_samsung_ttc_settlement(extracted)
    sweep = build_samsung_ttc_strike_sweep(
        extracted, run_developer=run_developer, developer_runner=developer_runner
    )
    adder = build_samsung_ttc_adder_sensitivity(extracted)
    stress = build_samsung_ttc_regime_stress(extracted)
    definition = build_samsung_ttc_definition(extracted)

    buyer_saves = (
        float(base["benchmark"]["year_one_costs"]["buyer_savings_vs_evn_vnd"]) > 0.0
    )
    overlap = bool(sweep["negotiation_summary"]["overlap_found"])
    if overlap:
        recommended = "advance_negotiable_band_exists"
    elif buyer_saves:
        recommended = "buyer_favorable_developer_subeconomic"
    else:
        recommended = "reject_no_buyer_saving"

    rationale = [
        f"Buyer saves ~{base['contracted_slice']['buyer_savings_vnd'] / 1e9:.1f} B VND/yr "
        f"on the contracted 70 GWh at the Southern-ceiling strike (1,012 VND/kWh).",
        f"Developer is sub-economic across the strike band (no overlap) under "
        f"conservative {SAMSUNG_TTC_INSTALLED_COST_USD_PER_KW:.0f} USD/kW capex on the "
        f"contracted 70 GWh; counting the plant's full yield would lift developer NPV.",
        "DPPA grid-service adder is the dominant buyer lever; buyer flips to a premium "
        "near ~0.9x the inherited 523 VND/kWh adder.",
        "Decree 146 two-part trial raises the buyer's EVN bill ~18%, making the DPPA "
        "more attractive unless it double-charges the contracted volume.",
    ]

    return {
        "case": "DPPA_SAMSUNG_TTC",
        "model": "Samsung-TTC DPPA Combined Decision",
        "deal": definition,
        "base_settlement": {
            "solar_summary": base["solar_summary"],
            "contracted_slice": base["contracted_slice"],
            "buyer_savings_vs_evn_vnd": float(
                base["benchmark"]["year_one_costs"]["buyer_savings_vs_evn_vnd"]
            ),
        },
        "strike_sweep": {
            "strike_band": sweep["strike_band"],
            "developer_screen": sweep["developer_screen"],
            "negotiation_summary": sweep["negotiation_summary"],
            "sweep": sweep["sweep"],
        },
        "adder_sensitivity": adder["adder_sensitivity"],
        "regime_stress": stress,
        "decision": {
            "buyer_saves_at_base_strike": buyer_saves,
            "developer_overlap_found": overlap,
            "recommended_position": recommended,
            "rationale": rationale,
        },
        "quality": {
            "basis": "directional",
            "strike_basis": "southern_ground_mount_ceiling",
            "market_reference_price_type": base["quality"]["market_reference_price_type"],
            "solar_profile_source": base["quality"]["solar_profile_source"],
            "caveat": (
                "Directional only: undisclosed/triangulated commercial terms (strike, "
                "DPPA adder, KPP, tenor), proxy CFMP series, non-site-specific solar, "
                "conservative developer capex and revenue basis. Not a bankable verdict."
            ),
        },
    }
