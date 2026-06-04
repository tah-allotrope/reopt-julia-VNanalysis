"""Samsung SEVT - TTC Duc Hue 2 grid-connected DPPA economics case.

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
from datetime import datetime, timedelta

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

EXCHANGE_RATE_VND_PER_USD = 26_400.0
WHOLESALE_RATE_VND_PER_KWH = 671.0
WHOLESALE_RATE_USD_PER_KWH = 0.0254
DATA_YEAR = 2024


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
    site = dict(SAMSUNG_TTC_SOLAR_SITE)
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
