"""
Build extracted inputs for the Ninhsim bundled-CPPA optimization workflow.

This script normalizes the raw Ninhsim 8760 load CSV, computes the current EVN
weighted TOU benchmark at 22 kV to 110 kV, and persists the extracted-inputs
JSON consumed by the Ninhsim scenario builder and analysis workflow.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

PROJECT_NAME = "Ninhsim Solar+BESS+Wind Bundled CPPA Optimization"
DATA_YEAR = 2024
EXCHANGE_RATE_VND_PER_USD = _resolve_exchange_rate(load_vietnam_data(), caller_value=26_400.0)
VOLTAGE_LEVEL = "medium_voltage_22kv_to_110kv"
CUSTOMER_TYPE = "industrial"
REGION = "south"
WIND_CAPACITY_FACTOR_FALLBACK = 0.35

PROJECT_SITE = {
    "latitude": 12.525729252783036,
    "longitude": 109.02003383567742,
    "region": REGION,
    "voltage_level": VOLTAGE_LEVEL,
    "customer_type": CUSTOMER_TYPE,
}


@dataclass
class LoadCleaningSummary:
    missing_count: int
    interpolated_indices: list[int]
    clipped_negative_count: int
    final_count: int


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _read_raw_loads(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [row["Load_kW"] for row in reader]


def clean_load_series(raw_values: list[str]) -> tuple[list[float], LoadCleaningSummary]:
    parsed: list[float | None] = []
    interpolated_indices: list[int] = []
    clipped_negative_count = 0

    for value in raw_values:
        text = value.replace(",", "").replace('"', "").strip()
        if text == "-":
            parsed.append(None)
            continue
        numeric = float(text)
        if numeric < 0:
            numeric = 0.0
            clipped_negative_count += 1
        parsed.append(numeric)

    cleaned = list(parsed)
    for idx, value in enumerate(cleaned):
        if value is not None:
            continue
        prev_idx = idx - 1
        while prev_idx >= 0 and cleaned[prev_idx] is None:
            prev_idx -= 1
        next_idx = idx + 1
        while next_idx < len(cleaned) and cleaned[next_idx] is None:
            next_idx += 1

        if prev_idx >= 0 and next_idx < len(cleaned):
            prev_raw = cleaned[prev_idx]
            next_raw = cleaned[next_idx]
            if prev_raw is None or next_raw is None:
                raise ValueError("Interpolation neighbors unexpectedly missing")
            prev_val = float(prev_raw)
            next_val = float(next_raw)
            ratio = (idx - prev_idx) / (next_idx - prev_idx)
            cleaned[idx] = prev_val + (next_val - prev_val) * ratio
        elif prev_idx >= 0:
            prev_raw = cleaned[prev_idx]
            if prev_raw is None:
                raise ValueError("Previous interpolation neighbor unexpectedly missing")
            cleaned[idx] = float(prev_raw)
        elif next_idx < len(cleaned):
            next_raw = cleaned[next_idx]
            if next_raw is None:
                raise ValueError("Next interpolation neighbor unexpectedly missing")
            cleaned[idx] = float(next_raw)
        else:
            raise ValueError(
                "Unable to interpolate Ninhsim load series; all values are missing"
            )

        interpolated_indices.append(idx)

    final_values = []
    for value in cleaned:
        if value is None:
            raise ValueError(
                "Load cleaning left a missing value in the final Ninhsim series"
            )
        final_values.append(float(value))
    summary = LoadCleaningSummary(
        missing_count=len(interpolated_indices),
        interpolated_indices=interpolated_indices,
        clipped_negative_count=clipped_negative_count,
        final_count=len(final_values),
    )
    return final_values, summary


def build_hourly_rate_series(tariff_data: dict, year: int = DATA_YEAR) -> list[float]:
    base_vnd = tariff_data["base_avg_price_vnd_per_kwh"]
    schedule = tariff_data["tou_schedule"]
    multipliers = tariff_data["rate_multipliers"][CUSTOMER_TYPE][VOLTAGE_LEVEL]

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
    cursor = date(year, 1, 1)
    for _ in range(366 if _is_leap_year(year) else 365):
        rates.extend(sunday_rates if cursor.weekday() == 6 else weekday_rates)
        cursor += timedelta(days=1)
    return rates


def calculate_weighted_price(
    loads_kw: list[float], rates_vnd_per_kwh: list[float]
) -> dict:
    annual_load_kwh = sum(loads_kw)
    weighted_vnd = (
        sum(load * rate for load, rate in zip(loads_kw, rates_vnd_per_kwh))
        / annual_load_kwh
    )
    weighted_usd = weighted_vnd / EXCHANGE_RATE_VND_PER_USD
    return {
        "annual_load_kwh": annual_load_kwh,
        "annual_load_gwh": annual_load_kwh / 1_000_000.0,
        "weighted_evn_price_vnd_per_kwh": weighted_vnd,
        "weighted_evn_price_usd_per_kwh": weighted_usd,
    }


def build_wind_production_factor_series(
    annual_capacity_factor: float = WIND_CAPACITY_FACTOR_FALLBACK,
    year: int = DATA_YEAR,
) -> list[float]:
    """Build a deterministic 8760 wind production-factor fallback for Ninhsim."""
    start = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    weights = []

    for hour_index in range(8760):
        ts = start + timedelta(hours=hour_index)
        hour = ts.hour
        day_of_year = ts.timetuple().tm_yday

        seasonal = 1.0 + 0.16 * math.cos(2.0 * math.pi * (day_of_year - 35) / 365.0)
        diurnal = 1.0 + 0.06 * math.sin(2.0 * math.pi * (hour - 1) / 24.0)
        weekly = 1.0 + 0.015 * math.cos(2.0 * math.pi * ts.weekday() / 7.0)
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
    raw_path = (
        REPO_ROOT / "scenarios" / "case_studies" / "ninhsim" / "NinhsimSample.csv"
    )
    tariff_path = REPO_ROOT / "data" / "vietnam" / "vn_tariff_2025.json"

    raw_values = _read_raw_loads(raw_path)
    loads_kw, cleaning = clean_load_series(raw_values)
    tariff_raw = json.loads(tariff_path.read_text(encoding="utf-8"))
    tariff_data = tariff_raw["data"]
    tou_rates_vnd = build_hourly_rate_series(tariff_data)
    wind_pf_series = build_wind_production_factor_series()
    benchmark = calculate_weighted_price(loads_kw, tou_rates_vnd)
    multiplier_block = tariff_data["rate_multipliers"][CUSTOMER_TYPE][VOLTAGE_LEVEL]

    return {
        "project": PROJECT_NAME,
        "data_year": DATA_YEAR,
        "site": PROJECT_SITE,
        "source_load_path": str(raw_path.relative_to(REPO_ROOT)),
        "source_tariff_path": str(tariff_path.relative_to(REPO_ROOT)),
        "loads_kw": loads_kw,
        "load_cleaning": {
            "missing_count": cleaning.missing_count,
            "interpolated_indices": cleaning.interpolated_indices,
            "clipped_negative_count": cleaning.clipped_negative_count,
            "final_count": cleaning.final_count,
        },
        "benchmark": {
            **benchmark,
            "exchange_rate_vnd_per_usd": EXCHANGE_RATE_VND_PER_USD,
            "peak_rate_vnd_per_kwh": tariff_data["base_avg_price_vnd_per_kwh"]
            * multiplier_block["peak"],
            "standard_rate_vnd_per_kwh": tariff_data["base_avg_price_vnd_per_kwh"]
            * multiplier_block["standard"],
            "offpeak_rate_vnd_per_kwh": tariff_data["base_avg_price_vnd_per_kwh"]
            * multiplier_block["offpeak"],
            "wholesale_rate_vnd_per_kwh": 671.0,
            "wholesale_rate_usd_per_kwh": 0.0254,
        },
        "evn_tariff": {
            "tou_energy_rates_vnd_per_kwh": tou_rates_vnd,
            "tou_energy_rates_usd_per_kwh": [
                rate / EXCHANGE_RATE_VND_PER_USD for rate in tou_rates_vnd
            ],
        },
        "wind_production_factor_series": wind_pf_series,
        "assumptions": {
            "customer_type": CUSTOMER_TYPE,
            "voltage_level": VOLTAGE_LEVEL,
            "region": REGION,
            "cPPA_structure": "bundled_strike_with_residual_evn_tou",
            "cPPA_escalates_with_evn": True,
            "price_target_basis": "customer_blended_year1_price_lte_current_weighted_evn_price",
            "wind_capacity_factor_fallback": WIND_CAPACITY_FACTOR_FALLBACK,
            "wind_series_method": "synthetic_profile_used_when_nrel_wind_toolkit_has_no_data_at_site",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Ninhsim extracted inputs with cleaned load and EVN benchmark"
    )
    parser.add_argument(
        "--output",
        default="data/interim/ninhsim/ninhsim_extracted_inputs.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    extracted = build_extracted_inputs()
    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(extracted, indent=2), encoding="utf-8")

    print(f"Ninhsim extracted inputs written to: {output_path}")
    print(f"  Annual load : {extracted['benchmark']['annual_load_gwh']:.3f} GWh")
    print(
        "  Weighted EVN benchmark : "
        f"{extracted['benchmark']['weighted_evn_price_vnd_per_kwh']:.2f} VND/kWh "
        f"({extracted['benchmark']['weighted_evn_price_usd_per_kwh']:.6f} USD/kWh)"
    )


if __name__ == "__main__":
    main()
