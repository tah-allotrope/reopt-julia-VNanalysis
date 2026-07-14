"""Build synthetic 8760-hour industrial load profiles for the Trang Due
validation scenarios, using the existing VIDA pilot benchmark shape
(two-shift industrial, weekday/Saturday/Sunday day-type + monthly seasonal
index) rather than inventing a new one.

Source shape: cpi workspace
  pipeline analytics/pilot/benchmark-load-profiles.csv (Sections 1 & 2).
"""
from __future__ import annotations

import calendar
import csv
from pathlib import Path
from typing import List

BENCHMARK_CSV = Path(
    r"C:\Users\tukum\Downloads\remote\cpi\pipeline analytics\pilot\benchmark-load-profiles.csv"
)

YEAR = 2025  # non-leap year, 8760 hours, matches template ElectricLoad.year


def _load_hourly_shape() -> dict:
    """Returns {'weekday': [24 floats], 'saturday': [...], 'sunday': [...]}."""
    shape = {"weekday": [0.0] * 24, "saturday": [0.0] * 24, "sunday": [0.0] * 24}
    with open(BENCHMARK_CSV, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "hour" and "weekday" in r)
    for r in rows[header_idx + 1 : header_idx + 25]:
        if not r or not r[0].strip().isdigit():
            break
        h = int(r[0])
        shape["weekday"][h] = float(r[1])
        shape["saturday"][h] = float(r[2])
        shape["sunday"][h] = float(r[3])
    return shape


def _load_monthly_index() -> List[float]:
    with open(BENCHMARK_CSV, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "month" and r[1] == "index")
    idx = [0.0] * 12
    for r in rows[header_idx + 1 : header_idx + 13]:
        if not r or not r[0].strip().isdigit():
            break
        idx[int(r[0]) - 1] = float(r[1])
    return idx


def build_synthetic_load(annual_kwh: float, shape: str = "two_shift_industrial") -> List[float]:
    """Returns an 8760-element hourly kW list whose sum equals annual_kwh."""
    if shape != "two_shift_industrial":
        raise ValueError(f"unsupported shape {shape!r}")

    hourly_shape = _load_hourly_shape()
    monthly_index = _load_monthly_index()

    raw: List[float] = []
    day_types: List[str] = []
    import datetime

    d = datetime.date(YEAR, 1, 1)
    while d.year == YEAR:
        wd = d.weekday()  # 0=Mon .. 6=Sun
        day_type = "sunday" if wd == 6 else ("saturday" if wd == 5 else "weekday")
        month_idx = monthly_index[d.month - 1]
        for h in range(24):
            raw.append(hourly_shape[day_type][h] * month_idx)
            day_types.append(day_type)
        d += datetime.timedelta(days=1)

    assert len(raw) == 8760, f"expected 8760 hours, got {len(raw)}"
    total_raw = sum(raw)
    scale = annual_kwh / total_raw
    loads_kw = [v * scale for v in raw]
    return loads_kw


if __name__ == "__main__":
    archetype = build_synthetic_load(3_000_000.0)
    print("archetype sum:", round(sum(archetype), 1), "len:", len(archetype))
    flagship = build_synthetic_load(8_923_200.0)
    print("flagship sum:", round(sum(flagship), 1), "len:", len(flagship))
