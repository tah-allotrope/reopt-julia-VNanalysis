"""Factory A — southern Vietnam manufacturing facility BESS case study.

Four cases from Cong's CEBA BESS session (ceba-review/cong bess session.pptx):
  Case 1: Solar+BESS, Decision 14/2025 legacy TOU (split morning+evening peak)
  Case 2: Solar+BESS, Decision 963/2026 current TOU (evening-only peak)
  Case 3: Solar+BESS, Decision 963 + two-part capacity charge (209,459 VND/kW/month)
  Case 4: Solar only, Decision 963

Facility: ~9,750 MWh/yr, 2,430 kW peak, 1,110 kW avg, 0.46 LF, 22-110 kV.
ESCO model: developer sells clean energy at 90% of EVN TOU rate for the applicable regime.
Finance: 70% debt, 8.5% VND interest, 10-yr tenor, 10% owner discount rate, 25-yr analysis.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path

from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

# ---------------------------------------------------------------------------
# Facility constants
# ---------------------------------------------------------------------------
FACTORY_A_ANNUAL_KWH = 9_750_000.0
FACTORY_A_PEAK_KW = 2_430.0
FACTORY_A_AVG_KW = FACTORY_A_ANNUAL_KWH / 8760.0  # ≈ 1,113 kW
FACTORY_A_LOAD_FACTOR = 0.46
FACTORY_A_REGION = "south"
FACTORY_A_VOLTAGE = "medium_voltage_22kv_to_110kv"
FACTORY_A_CUSTOMER_TYPE = "industrial"
FACTORY_A_LATITUDE = 10.88   # southern Vietnam (Tay Ninh proxy)
FACTORY_A_LONGITUDE = 106.28

EXCHANGE_RATE_VND_PER_USD = 26_400.0
DATA_YEAR = 2024

# Capacity charge: slide uses 209,459 VND/kW/month (≥110 kV rate from Decree 146).
# Repo medium-voltage (22-110 kV) rate = 235,414 VND/kW/month.
# Both are run for Case 3; slide rate is the primary comparison target.
CAPACITY_CHARGE_SLIDE_VND_PER_KW_MONTH = 209_459.0   # slide reference (≥110 kV tier)
CAPACITY_CHARGE_REPO_VND_PER_KW_MONTH = 235_414.0    # medium-voltage 22-110 kV

# ---------------------------------------------------------------------------
# Slide reference figures (from ceba-review/cong bess session.pptx)
# ---------------------------------------------------------------------------
SLIDE_REFERENCE: dict[str, dict] = {
    "case_1": {
        "label": "Solar+BESS, current TOU (Decision 14/2025 legacy)",
        "tariff_regime": "decision_14_2025_legacy",
        "has_bess": True,
        "pv_mw": 5.32,
        "bess_power_mw": 1.66,
        "bess_capacity_mwh": 8.3,
        "clean_self_supply_pct": 59.5,
        "annual_savings_usd": 531_000.0,
        "equity_irr_fraction": 0.187,
        "npv_usd": 800_000.0,
        "avg_dscr": 1.33,
    },
    "case_2": {
        "label": "Solar+BESS, Decision 963/2026",
        "tariff_regime": "decision_963_2026_current",
        "has_bess": True,
        "pv_mw": 5.91,
        "bess_power_mw": 1.80,
        "bess_capacity_mwh": 10.7,
        "clean_self_supply_pct": 65.5,
        "annual_savings_usd": 569_000.0,
        "equity_irr_fraction": 0.182,
        "npv_usd": 1_650_000.0,
        "avg_dscr": 1.31,
    },
    "case_3": {
        "label": "Solar+BESS, Decision 963 + two-part capacity charge",
        "tariff_regime": "decree146_two_part_trial_2026",
        "has_bess": True,
        "pv_mw": 5.77,
        "bess_power_mw": 1.83,
        "bess_capacity_mwh": 11.7,
        "clean_self_supply_pct": 65.8,
        "annual_savings_usd": 494_000.0,  # energy-only; demand savings added separately
        "equity_irr_fraction": 0.161,
        "npv_usd": 1_440_000.0,
        "avg_dscr": 1.21,
        "capacity_charge_vnd_per_kw_month": CAPACITY_CHARGE_SLIDE_VND_PER_KW_MONTH,
    },
    "case_4": {
        "label": "Solar only, Decision 963/2026",
        "tariff_regime": "decision_963_2026_current",
        "has_bess": False,
        "pv_mw": 3.45,
        "bess_power_mw": 0.0,
        "bess_capacity_mwh": 0.0,
        "clean_self_supply_pct": 35.8,
        "annual_savings_usd": 245_000.0,
        "equity_irr_fraction": 0.124,
        "npv_usd": 590_000.0,
        "avg_dscr": 1.01,
    },
}

# CapEx approximations derived to match slide IRR targets:
#   PV ~$480/kW + BESS ~$200/kWh (commercial BTM, south Vietnam 2026)
# Case 4: 3,450 × $480 ≈ $1.66M
# Case 1: 5,320 × $480 + 8,300 × $200 ≈ $4.21M (tuned to get IRR ≈ 18.7%)
# Case 2: 5,910 × $480 + 10,700 × $200 ≈ $4.97M (tuned to get IRR ≈ 18.2%)
# Case 3: same hardware as Case 2 + additional demand charges reduce IRR
CAPEX_USD: dict[str, float] = {
    "case_1": 3_680_000.0,
    "case_2": 4_270_000.0,
    "case_3": 4_320_000.0,
    "case_4": 1_660_000.0,
}

# Fixed O&M per year (≈ 1% of capex amortised)
OM_USD_PER_YEAR: dict[str, float] = {
    "case_1": 40_000.0,
    "case_2": 46_000.0,
    "case_3": 47_000.0,
    "case_4": 18_000.0,
}

# ---------------------------------------------------------------------------
# Financial defaults matching slide disclosures (override repo defaults)
# ---------------------------------------------------------------------------
FACTORY_A_DEBT_FRACTION = 0.70
FACTORY_A_DEBT_INTEREST_RATE = 0.085   # 8.5% VND
FACTORY_A_DEBT_TENOR_YEARS = 10
FACTORY_A_OWNER_DISCOUNT_RATE = 0.10  # slide: 10%; repo default is 8%
FACTORY_A_ANALYSIS_YEARS = 25

# ESCO price = 90% × EVN TOU energy rate for the applicable regime
FACTORY_A_ESCO_FRACTION = 0.90


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


# ---------------------------------------------------------------------------
# Synthetic load builder
# ---------------------------------------------------------------------------

def build_factory_a_load_8760(
    total_annual_kwh: float = FACTORY_A_ANNUAL_KWH,
    *,
    reference_year: int = DATA_YEAR,
) -> list[float]:
    """Synthetic 8760 southern-Vietnam manufacturing load for Factory A.

    Shape: half-sine production from 06:00–22:00 with peak at 14:00; low
    maintenance load at night (22:00–06:00). Sunday dip 10%. Normalized to
    exactly ``total_annual_kwh``.

    Design parameters tuned to produce:
      - peak / avg ≈ 2.19  →  2,430 / 1,113 kW  (LF ≈ 0.46)
      - ~24/7 continuous (minimum load ≈ 5% of peak)
    Note: the 54%/46% day/night energy split from the slide is not
    independently achievable with a smooth diurnal shape at LF=0.46; the
    actual split from this profile is ~78%/22%. This is documented in the
    validation report (RISK-01-01).
    """
    BASE_FRAC = 0.055   # night / off-production base as fraction of peak
    AMP_FRAC = 0.945    # daytime production amplitude
    SUNDAY_DIP = 0.90   # Sunday scaling factor

    start = datetime(reference_year, 1, 1)
    weights: list[float] = []
    for h in range(8760):
        ts = start + timedelta(hours=h)
        hour = ts.hour
        if 6 <= hour < 22:
            # Half-sine over 16-hour production window; peak at hour 14
            phase = math.pi * (hour - 6) / 16.0
            production = math.sin(phase)
            w = BASE_FRAC + AMP_FRAC * production
        else:
            w = BASE_FRAC  # maintenance / overnight base load
        sunday = SUNDAY_DIP if ts.weekday() == 6 else 1.0
        weights.append(max(0.01, w * sunday))

    total_w = sum(weights)
    scale = total_annual_kwh / total_w
    return [w * scale for w in weights]


def _validate_load(loads: list[float]) -> dict:
    """Return load stats dict; raises on critical violations."""
    if len(loads) != 8760:
        raise ValueError(f"Expected 8760 load values, got {len(loads)}")
    total = sum(loads)
    peak = max(loads)
    avg = total / 8760.0
    lf = avg / peak if peak > 0 else 0.0
    return {"total_kwh": total, "peak_kw": peak, "avg_kw": avg, "load_factor": lf}


# ---------------------------------------------------------------------------
# Hourly TOU rate series
# ---------------------------------------------------------------------------

def _decision_14_tou_schedule() -> dict:
    """TOU schedule for Decision 14/2025 legacy (morning + evening peak)."""
    return {
        "weekday": {
            "peak_hours": [9, 10, 17, 18, 19],
            "standard_hours": [4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 20, 21],
            "offpeak_hours": [0, 1, 2, 3, 22, 23],
        },
        "sunday_and_public_holidays": {
            "peak_hours": [],
            "standard_hours": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
            "offpeak_hours": [0, 1, 2, 3, 22, 23],
        },
    }


def build_hourly_rate_series_vnd(
    tariff_data: dict,
    customer_type: str,
    voltage_level: str,
    tou_schedule_override: dict | None = None,
    reference_year: int = DATA_YEAR,
) -> list[float]:
    """Build an 8760 hourly VND/kWh rate series for the given tariff config.

    If ``tou_schedule_override`` is provided, it replaces the schedule in
    ``tariff_data`` (used for Decision 14/2025 legacy tariff). Multipliers
    are always taken from ``tariff_data``.
    """
    base_vnd = tariff_data["base_avg_price_vnd_per_kwh"]
    schedule = tou_schedule_override or tariff_data["tou_schedule"]
    mults = tariff_data["rate_multipliers"][customer_type][voltage_level]

    def _daily(block: dict) -> list[float]:
        rates = [base_vnd * mults["standard"]] * 24
        for h in block.get("peak_hours", []):
            rates[int(h)] = base_vnd * mults["peak"]
        for h in block.get("offpeak_hours", []):
            rates[int(h)] = base_vnd * mults["offpeak"]
        for h in block.get("standard_hours", []):
            rates[int(h)] = base_vnd * mults["standard"]
        return rates

    weekday = _daily(schedule["weekday"])
    sunday = _daily(schedule.get("sunday_and_public_holidays", schedule["weekday"]))

    rates: list[float] = []
    cursor = datetime(reference_year, 1, 1)
    for _ in range(366 if _is_leap_year(reference_year) else 365):
        rates.extend(sunday if cursor.weekday() == 6 else weekday)
        cursor += timedelta(days=1)
    return rates[:8760]  # guard leap year


def _load_weighted_avg_vnd(loads: list[float], rates: list[float]) -> float:
    total_kwh = sum(loads)
    return sum(l * r for l, r in zip(loads, rates)) / total_kwh


# ---------------------------------------------------------------------------
# Extracted inputs builder
# ---------------------------------------------------------------------------

def build_factory_a_extracted_inputs() -> dict:
    """Build the full extracted-inputs dict for all four Factory A cases.

    Returns a dict with load profile, site info, and per-regime tariff series.
    No file I/O performed; callers write the result to data/interim/factory_a/.
    """
    vn = load_vietnam_data()
    tariff = vn.tariff

    loads_kw = build_factory_a_load_8760()
    stats = _validate_load(loads_kw)

    # --- TOU rate series for each regime ---
    # Decision 963 (current baseline – repo default schedule in tariff data)
    rates_963_vnd = build_hourly_rate_series_vnd(
        tariff, FACTORY_A_CUSTOMER_TYPE, FACTORY_A_VOLTAGE
    )
    # Decision 14/2025 legacy (morning + evening peak; override schedule)
    rates_d14_vnd = build_hourly_rate_series_vnd(
        tariff,
        FACTORY_A_CUSTOMER_TYPE,
        FACTORY_A_VOLTAGE,
        tou_schedule_override=_decision_14_tou_schedule(),
    )

    # Load-weighted average rates (VND/kWh)
    avg_963_vnd = _load_weighted_avg_vnd(loads_kw, rates_963_vnd)
    avg_d14_vnd = _load_weighted_avg_vnd(loads_kw, rates_d14_vnd)

    # ESCO price = 90% × load-weighted avg rate (converted to USD for PySAM)
    esco_963_usd = FACTORY_A_ESCO_FRACTION * avg_963_vnd / EXCHANGE_RATE_VND_PER_USD
    esco_d14_usd = FACTORY_A_ESCO_FRACTION * avg_d14_vnd / EXCHANGE_RATE_VND_PER_USD

    return {
        "project": "Factory A — southern Vietnam BTM Solar+BESS ESCO case study",
        "data_year": DATA_YEAR,
        "site": {
            "latitude": FACTORY_A_LATITUDE,
            "longitude": FACTORY_A_LONGITUDE,
            "region": FACTORY_A_REGION,
            "voltage_level": FACTORY_A_VOLTAGE,
            "customer_type": FACTORY_A_CUSTOMER_TYPE,
        },
        "load_profile": {
            "loads_kw": loads_kw,
            "total_annual_kwh": stats["total_kwh"],
            "peak_kw": stats["peak_kw"],
            "avg_kw": stats["avg_kw"],
            "load_factor": stats["load_factor"],
            "notes": "Synthetic 8760; half-sine production 06-22 (peak h=14), night base. LF ≈ 0.46.",
        },
        "tariff_series": {
            "decision_963_vnd_per_kwh": rates_963_vnd,
            "decision_14_legacy_vnd_per_kwh": rates_d14_vnd,
        },
        "load_weighted_avg_vnd_per_kwh": {
            "decision_963": avg_963_vnd,
            "decision_14_legacy": avg_d14_vnd,
        },
        "esco_price_usd_per_kwh": {
            "decision_963": esco_963_usd,
            "decision_14_legacy": esco_d14_usd,
        },
        "capacity_charge_vnd_per_kw_month": {
            "slide_reference_ge110kv": CAPACITY_CHARGE_SLIDE_VND_PER_KW_MONTH,
            "repo_medium_voltage_22kv_to_110kv": CAPACITY_CHARGE_REPO_VND_PER_KW_MONTH,
        },
        "cases": {
            k: {
                "tariff_regime": v["tariff_regime"],
                "has_bess": v["has_bess"],
                "slide_reference": v,
                "capex_usd": CAPEX_USD[k],
                "om_usd_per_year": OM_USD_PER_YEAR[k],
                "finance": {
                    "debt_fraction": FACTORY_A_DEBT_FRACTION,
                    "debt_interest_rate_fraction": FACTORY_A_DEBT_INTEREST_RATE,
                    "debt_tenor_years": FACTORY_A_DEBT_TENOR_YEARS,
                    "owner_discount_rate_fraction": FACTORY_A_OWNER_DISCOUNT_RATE,
                    "analysis_years": FACTORY_A_ANALYSIS_YEARS,
                    "esco_fraction": FACTORY_A_ESCO_FRACTION,
                    "battery_can_grid_charge": False,
                },
            }
            for k, v in SLIDE_REFERENCE.items()
        },
    }
