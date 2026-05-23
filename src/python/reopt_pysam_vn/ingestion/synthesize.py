"""Partial-data handling: resampling, monthly-to-8760 synthesis, and offline fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


_REFERENCE_SHAPES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "vietnam" / "reference_load_shapes"


def detect_resolution(row_count: int) -> str:
    resolutions = {
        35040: "15min",
        17520: "30min",
        8760: "hourly",
        4380: "2hour",
        2920: "3hour",
        12: "monthly",
        52: "weekly",
        365: "daily",
    }
    return resolutions.get(row_count, "unknown")


def resample_to_hourly(values: list[float], source_resolution: str) -> list[float]:
    if source_resolution == "15min":
        if len(values) != 35040:
            raise ValueError(f"Expected 35040 values for 15-min data, got {len(values)}")
        hourly = []
        for i in range(0, 35040, 4):
            chunk = values[i:i + 4]
            hourly.append(sum(chunk) / len(chunk))
        return hourly

    if source_resolution == "30min":
        if len(values) != 17520:
            raise ValueError(f"Expected 17520 values for 30-min data, got {len(values)}")
        hourly = []
        for i in range(0, 17520, 2):
            chunk = values[i:i + 2]
            hourly.append(sum(chunk) / len(chunk))
        return hourly

    raise ValueError(f"Unsupported resolution for resampling: {source_resolution}")


def synthesize_from_monthly(
    monthly_kwh: list[float],
    latitude: float = 10.8,
    longitude: float = 106.6,
    building_type: str = "LargeOffice",
    api_key: Optional[str] = None,
) -> tuple[list[float], str]:
    """Synthesize 8760 hourly kW from 12 monthly kWh totals.

    Attempts REopt simulated_load API first, falls back to offline reference shape.
    Returns (loads_kw_8760, synthesis_method).
    """
    if len(monthly_kwh) != 12:
        raise ValueError(f"Expected 12 monthly values, got {len(monthly_kwh)}")

    annual_kwh = sum(monthly_kwh)

    resolved_key = api_key or os.environ.get("NREL_DEVELOPER_API_KEY")
    if resolved_key:
        try:
            loads = _call_simulated_load_api(
                annual_kwh, latitude, longitude, building_type, resolved_key
            )
            if loads and len(loads) == 8760:
                return loads, "api_simulated_load"
        except Exception:
            pass

    loads = _offline_shape_scaling(monthly_kwh, annual_kwh)
    return loads, "offline_archetype_scaled"


def _call_simulated_load_api(
    annual_kwh: float,
    latitude: float,
    longitude: float,
    building_type: str,
    api_key: str,
) -> list[float]:
    """Call REopt simulated_load API to generate an 8760 profile."""
    import urllib.request
    import urllib.parse

    params = urllib.parse.urlencode({
        "api_key": api_key,
        "latitude": latitude,
        "longitude": longitude,
        "doe_reference_name": building_type,
        "annual_kwh": annual_kwh,
    })

    url = f"https://developer.nrel.gov/api/reopt/stable/simulated_load/?{params}"

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "loads_kw" in data:
        return data["loads_kw"]
    if "outputs" in data and "loads_kw" in data["outputs"]:
        return data["outputs"]["loads_kw"]

    raise ValueError("Unexpected API response format")


def _offline_shape_scaling(
    monthly_kwh: list[float], annual_kwh: float
) -> list[float]:
    """Scale a reference load shape to match monthly energy targets."""
    shape = _load_reference_shape("industrial_south")

    # Monthly adjustment: scale each month's hours to match monthly target
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    month_hours = [d * 24 for d in month_days]

    hour_offset = 0
    loads = []
    for month_idx in range(12):
        n_hours = month_hours[month_idx]
        month_shape = shape[hour_offset:hour_offset + n_hours]
        month_shape_sum = sum(month_shape)

        if month_shape_sum > 0:
            scale = monthly_kwh[month_idx] / (month_shape_sum * annual_kwh)
        else:
            scale = 1.0

        for h in range(n_hours):
            loads.append(shape[hour_offset + h] * annual_kwh * scale)

        hour_offset += n_hours

    return loads


def _load_reference_shape(name: str) -> list[float]:
    """Load a normalized reference load shape from the data directory."""
    path = _REFERENCE_SHAPES_DIR / f"{name}.json"
    if not path.exists():
        return [1.0 / 8760] * 8760

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    return data.get("shape", [1.0 / 8760] * 8760)


def route_synthesis(
    values: list[float], row_count: int
) -> tuple[list[float], str]:
    """Route input data through the appropriate synthesis path.

    Returns (loads_kw_8760, synthesis_method).
    """
    if row_count == 8760:
        return values, "none"

    resolution = detect_resolution(row_count)

    if resolution in ("15min", "30min"):
        return resample_to_hourly(values, resolution), f"resampled_{resolution}"

    if resolution == "monthly" and row_count == 12:
        loads, method = synthesize_from_monthly(values)
        return loads, method

    raise ValueError(
        f"Cannot synthesize 8760 from {row_count} rows "
        f"(detected resolution: {resolution})"
    )
