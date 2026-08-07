"""
Build synthetic North Thuan extracted inputs and hourly factory load profile.

This script turns the staff PDF summary inputs into a deterministic 8760 load
series plus the extracted-inputs JSON consumed by the North Thuan REopt
scenario builder.
"""

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_NAME = "North Thuan Wind+Solar+BESS DPPA Feasibility (Scenario 3)"
DATA_YEAR = 2025

SITE = {
    "latitude": 11.55,
    "longitude": 108.98,
    "region": "south",
    "note": "Ninh Thuan province proxy - confirm exact coordinates with developer",
}

NORTH_THUAN_INPUTS = {
    "solar_mw": 30.0,
    "wind_mw": 20.0,
    "bess_mw": 10.0,
    "bess_mwh": 40.0,
    "solar_cf": 0.194,
    "wind_cf": 0.380,
    "total_capex_usd": 28_500_000.0,
    "analysis_years": 25,
    "debt_fraction": 0.70,
    "interest_rate": 0.085,
    "dppa_strike_usd_per_kwh": 0.055,
    "evn_ceiling_usd_per_kwh": 0.07394,
    "factory_annual_load_gwh": 240.90,
    "factory_mean_mw": 27.5,
    "factory_peak_mw": 134.1,
    "matched_gwh_yr1": 70.05,
}

SOLAR_GWH_YR1 = (
    NORTH_THUAN_INPUTS["solar_mw"] * 8760 * NORTH_THUAN_INPUTS["solar_cf"] / 1_000.0
)
WIND_GWH_YR1 = (
    NORTH_THUAN_INPUTS["wind_mw"] * 8760 * NORTH_THUAN_INPUTS["wind_cf"] / 1_000.0
)
TOTAL_GEN_GWH_YR1 = SOLAR_GWH_YR1 + WIND_GWH_YR1
FMP_YR1_USD_PER_KWH = (
    6_000_000
    - NORTH_THUAN_INPUTS["dppa_strike_usd_per_kwh"]
    * NORTH_THUAN_INPUTS["matched_gwh_yr1"]
    * 1e6
) / ((TOTAL_GEN_GWH_YR1 - NORTH_THUAN_INPUTS["matched_gwh_yr1"]) * 1e6)


def _peak_hour_index(year: int) -> int:
    peak_dt = datetime(year, 7, 15, 14, 0, 0, tzinfo=timezone.utc)
    return int((peak_dt - datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)).total_seconds() // 3600)


def build_synthetic_load_profile(
    annual_gwh: float,
    mean_mw: float,
    peak_mw: float,
    year: int = DATA_YEAR,
) -> list[float]:
    """Build a deterministic industrial 8760 profile matching annual energy and peak."""
    start = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    weights = []

    for hour_index in range(8760):
        ts = start + timedelta(hours=hour_index)
        hour = ts.hour
        weekday = ts.weekday()
        day_of_year = ts.timetuple().tm_yday

        if 0 <= hour < 5:
            diurnal = 0.52
        elif 5 <= hour < 8:
            diurnal = 0.70
        elif 8 <= hour < 12:
            diurnal = 1.18
        elif 12 <= hour < 14:
            diurnal = 1.28
        elif 14 <= hour < 18:
            diurnal = 1.16
        elif 18 <= hour < 22:
            diurnal = 1.03
        else:
            diurnal = 0.68

        weekday_factor = 1.00 if weekday < 5 else 0.86
        seasonal_factor = 1.0 + 0.07 * math.sin(
            2.0 * math.pi * (day_of_year - 38) / 365.0
        )
        shoulder_factor = 1.0 + 0.03 * math.cos(2.0 * math.pi * hour / 24.0)
        weights.append(diurnal * weekday_factor * seasonal_factor * shoulder_factor)

    average_weight = sum(weights) / len(weights)
    base_profile = [weight / average_weight * mean_mw * 1_000.0 for weight in weights]

    peak_idx = _peak_hour_index(year)
    target_total_kwh = annual_gwh * 1_000_000.0
    peak_kw = peak_mw * 1_000.0
    other_total = sum(base_profile) - base_profile[peak_idx]
    target_other_total = target_total_kwh - peak_kw
    scale_other = target_other_total / other_total

    profile = []
    for idx, value in enumerate(base_profile):
        if idx == peak_idx:
            profile.append(peak_kw)
        else:
            profile.append(value * scale_other)

    correction = target_total_kwh - sum(profile)
    for idx in range(len(profile)):
        if idx == peak_idx:
            continue
        profile[idx] += correction
        break

    return profile


def build_fmp_series(fmp_usd_per_kwh: float = FMP_YR1_USD_PER_KWH) -> list[float]:
    return [float(fmp_usd_per_kwh)] * 8760


def build_wind_production_factor_series(
    annual_capacity_factor: float = NORTH_THUAN_INPUTS["wind_cf"],
    year: int = DATA_YEAR,
) -> list[float]:
    """Build a deterministic 8760 wind production-factor series with the target annual CF."""
    start = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    weights = []

    for hour_index in range(8760):
        ts = start + timedelta(hours=hour_index)
        hour = ts.hour
        day_of_year = ts.timetuple().tm_yday

        seasonal = 1.0 + 0.18 * math.cos(2.0 * math.pi * (day_of_year - 20) / 365.0)
        diurnal = 1.0 + 0.08 * math.sin(2.0 * math.pi * (hour - 2) / 24.0)
        weekly = 1.0 + 0.02 * math.cos(2.0 * math.pi * ts.weekday() / 7.0)
        weights.append(max(0.05, seasonal * diurnal * weekly))

    average_weight = sum(weights) / len(weights)
    series = [
        min(0.98, weight / average_weight * annual_capacity_factor)
        for weight in weights
    ]

    target_total = annual_capacity_factor * 8760.0
    actual_total = sum(series)
    adjustment = target_total / actual_total if actual_total else 1.0
    adjusted = [min(0.999, value * adjustment) for value in series]

    total_error = target_total - sum(adjusted)
    adjusted[0] = max(0.0, min(0.999, adjusted[0] + total_error))
    return adjusted


def build_extracted_inputs() -> dict:
    loads_kw = build_synthetic_load_profile(
        annual_gwh=NORTH_THUAN_INPUTS["factory_annual_load_gwh"],
        mean_mw=NORTH_THUAN_INPUTS["factory_mean_mw"],
        peak_mw=NORTH_THUAN_INPUTS["factory_peak_mw"],
        year=DATA_YEAR,
    )
    fmp_usd_per_kwh = build_fmp_series()
    wind_production_factor_series = build_wind_production_factor_series()

    return {
        "project": PROJECT_NAME,
        "data_year": DATA_YEAR,
        "site": SITE,
        "loads_kw": loads_kw,
        "fmp_usd_per_kwh": fmp_usd_per_kwh,
        "wind_production_factor_series": wind_production_factor_series,
        "assumptions": {
            **NORTH_THUAN_INPUTS,
            "fmp_year1_usd_per_kwh": FMP_YR1_USD_PER_KWH,
            "solar_gwh_yr1_from_cf": round(SOLAR_GWH_YR1, 2),
            "wind_gwh_yr1_from_cf": round(WIND_GWH_YR1, 2),
            "total_gen_gwh_yr1_from_cf": round(TOTAL_GEN_GWH_YR1, 2),
            "load_profile_method": "synthetic_industrial_diurnal_profile_from_pdf_stats",
            "fmp_series_method": "flat_year1_fmp_derived_from_staff_revenue_claim",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build North Thuan extracted inputs with a synthetic 8760 load profile"
    )
    parser.add_argument(
        "--output",
        default="data/interim/north_thuan/north_thuan_extracted_inputs.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    extracted = build_extracted_inputs()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(extracted, indent=2), encoding="utf-8")

    annual_gwh = sum(extracted["loads_kw"]) / 1_000_000.0
    peak_mw = max(extracted["loads_kw"]) / 1_000.0
    print(f"North Thuan extracted inputs written to: {output_path}")
    print(f"  Annual load : {annual_gwh:.2f} GWh")
    print(f"  Peak demand : {peak_mw:.1f} MW")
    print(f"  FMP year 1  : {FMP_YR1_USD_PER_KWH:.5f} USD/kWh")


if __name__ == "__main__":
    main()
