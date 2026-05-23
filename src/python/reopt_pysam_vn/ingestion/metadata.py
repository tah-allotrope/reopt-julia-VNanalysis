"""Metadata extraction and load-shape classification for ingested factory profiles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass
class LoadMetadata:
    peak_demand_kw: float
    annual_consumption_mwh: float
    average_demand_kw: float
    load_factor: float
    min_demand_kw: float
    daytime_avg_kw: float
    nighttime_avg_kw: float
    weekend_avg_kw: float
    weekday_avg_kw: float


@dataclass
class TOUClassification:
    peak_consumption_mwh: float
    offpeak_consumption_mwh: float
    normal_consumption_mwh: float
    peak_share_pct: float
    offpeak_share_pct: float
    normal_share_pct: float
    regime_id: str
    customer_type: str
    voltage_level: str


@dataclass
class ArchetypeResult:
    archetype: str
    confidence: str
    weekend_weekday_ratio: float
    night_day_ratio: float
    peak_concentration: float


VALID_ARCHETYPES = [
    "single_shift_factory",
    "two_shift_factory",
    "continuous_process",
    "commercial_daytime",
    "commercial_extended",
]


def _build_day_type_mask(year: int) -> list[int]:
    """Return 8760-length list: 0=weekday, 1=weekend (Sunday) for each hour."""
    mask = []
    start = date(year, 1, 1)
    for day_offset in range(365):
        d = start + timedelta(days=day_offset)
        is_weekend = 1 if d.isoweekday() == 7 else 0
        mask.extend([is_weekend] * 24)
    return mask


def extract_load_metadata(loads_kw: list[float], year: int = 2024) -> LoadMetadata:
    if len(loads_kw) != 8760:
        raise ValueError(f"Expected 8760 values, got {len(loads_kw)}")

    peak = max(loads_kw)
    avg = sum(loads_kw) / 8760
    annual_mwh = sum(loads_kw) / 1000.0

    day_mask = _build_day_type_mask(year)

    daytime_values = []
    nighttime_values = []
    weekend_values = []
    weekday_values = []

    for i, kw in enumerate(loads_kw):
        hour_of_day = i % 24
        is_weekend = day_mask[i]

        if 6 <= hour_of_day < 18:
            daytime_values.append(kw)
        else:
            nighttime_values.append(kw)

        if is_weekend:
            weekend_values.append(kw)
        else:
            weekday_values.append(kw)

    return LoadMetadata(
        peak_demand_kw=peak,
        annual_consumption_mwh=annual_mwh,
        average_demand_kw=avg,
        load_factor=avg / peak if peak > 0 else 0.0,
        min_demand_kw=min(loads_kw),
        daytime_avg_kw=sum(daytime_values) / len(daytime_values) if daytime_values else 0.0,
        nighttime_avg_kw=sum(nighttime_values) / len(nighttime_values) if nighttime_values else 0.0,
        weekend_avg_kw=sum(weekend_values) / len(weekend_values) if weekend_values else 0.0,
        weekday_avg_kw=sum(weekday_values) / len(weekday_values) if weekday_values else 0.0,
    )


def classify_tou_consumption(
    loads_kw: list[float],
    customer_type: str = "industrial",
    voltage_level: str = "medium_voltage_22kv_to_110kv",
    regime_id: str = "decision_963_2026_current",
    year: int = 2024,
    vn=None,
) -> TOUClassification:
    """Classify load consumption by TOU period under a given regime.

    If `vn` (VNData) is provided, uses `build_vietnam_tariff` to get the
    regime-specific TOU windows. Otherwise falls back to hardcoded Decision 963
    windows (peak 17-22 weekday, offpeak 0-5).
    """
    if len(loads_kw) != 8760:
        raise ValueError(f"Expected 8760 values, got {len(loads_kw)}")

    if vn is not None:
        tou_schedule = _resolve_tou_schedule(vn, regime_id)
    else:
        tou_schedule = {
            "weekday": {
                "peak_hours": [17, 18, 19, 20, 21, 22],
                "standard_hours": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 23],
                "offpeak_hours": [0, 1, 2, 3, 4, 5],
            },
            "sunday_and_public_holidays": {
                "peak_hours": [],
                "standard_hours": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
                "offpeak_hours": [0, 1, 2, 3, 4, 5],
            },
        }

    day_mask = _build_day_type_mask(year)

    weekday_peak = set(tou_schedule["weekday"].get("peak_hours", []))
    weekday_offpeak = set(tou_schedule["weekday"].get("offpeak_hours", []))
    sunday_peak = set(tou_schedule.get("sunday_and_public_holidays", {}).get("peak_hours", []))
    sunday_offpeak = set(tou_schedule.get("sunday_and_public_holidays", {}).get("offpeak_hours", []))

    peak_kwh = 0.0
    offpeak_kwh = 0.0
    normal_kwh = 0.0

    for i, kw in enumerate(loads_kw):
        hour_of_day = i % 24
        is_weekend = day_mask[i]

        if is_weekend:
            if hour_of_day in sunday_peak:
                peak_kwh += kw
            elif hour_of_day in sunday_offpeak:
                offpeak_kwh += kw
            else:
                normal_kwh += kw
        else:
            if hour_of_day in weekday_peak:
                peak_kwh += kw
            elif hour_of_day in weekday_offpeak:
                offpeak_kwh += kw
            else:
                normal_kwh += kw

    total_kwh = peak_kwh + offpeak_kwh + normal_kwh
    total_mwh = total_kwh / 1000.0

    return TOUClassification(
        peak_consumption_mwh=peak_kwh / 1000.0,
        offpeak_consumption_mwh=offpeak_kwh / 1000.0,
        normal_consumption_mwh=normal_kwh / 1000.0,
        peak_share_pct=(peak_kwh / total_kwh * 100) if total_kwh > 0 else 0.0,
        offpeak_share_pct=(offpeak_kwh / total_kwh * 100) if total_kwh > 0 else 0.0,
        normal_share_pct=(normal_kwh / total_kwh * 100) if total_kwh > 0 else 0.0,
        regime_id=regime_id,
        customer_type=customer_type,
        voltage_level=voltage_level,
    )


def _resolve_tou_schedule(vn, regime_id: str) -> dict:
    """Extract TOU schedule from VNData via regime resolution."""
    from reopt_pysam_vn.reopt.preprocess import resolve_vietnam_regime

    resolved = resolve_vietnam_regime(vn, regime_id)
    tariff = resolved.get("tariff", {})
    return tariff.get("tou_schedule", vn.tariff.get("tou_schedule", {}))


def classify_industry_archetype(
    loads_kw: list[float], year: int = 2024
) -> ArchetypeResult:
    if len(loads_kw) != 8760:
        raise ValueError(f"Expected 8760 values, got {len(loads_kw)}")

    meta = extract_load_metadata(loads_kw, year)

    weekend_weekday_ratio = (
        meta.weekend_avg_kw / meta.weekday_avg_kw
        if meta.weekday_avg_kw > 0
        else 0.0
    )
    night_day_ratio = (
        meta.nighttime_avg_kw / meta.daytime_avg_kw
        if meta.daytime_avg_kw > 0
        else 0.0
    )

    day_mask = _build_day_type_mask(year)
    peak_hours_kw = []
    for i, kw in enumerate(loads_kw):
        hour_of_day = i % 24
        is_weekend = day_mask[i]
        if not is_weekend and 9 <= hour_of_day < 17:
            peak_hours_kw.append(kw)

    peak_concentration = (
        sum(peak_hours_kw) / len(peak_hours_kw) / meta.average_demand_kw
        if peak_hours_kw and meta.average_demand_kw > 0
        else 0.0
    )

    archetype, confidence = _classify(
        weekend_weekday_ratio, night_day_ratio, peak_concentration, meta.load_factor
    )

    return ArchetypeResult(
        archetype=archetype,
        confidence=confidence,
        weekend_weekday_ratio=round(weekend_weekday_ratio, 4),
        night_day_ratio=round(night_day_ratio, 4),
        peak_concentration=round(peak_concentration, 4),
    )


def _classify(
    ww_ratio: float, nd_ratio: float, peak_conc: float, load_factor: float
) -> tuple[str, str]:
    """Heuristic classification based on load-shape features."""

    # Continuous process: high night-to-day ratio AND high weekend-to-weekday ratio
    if nd_ratio > 0.7 and ww_ratio > 0.7:
        confidence = "high" if (nd_ratio > 0.85 and ww_ratio > 0.85) else "medium"
        return "continuous_process", confidence

    # Single shift factory: very low weekend activity, low night activity
    if ww_ratio < 0.3 and nd_ratio < 0.4:
        confidence = "high" if (ww_ratio < 0.15 and nd_ratio < 0.25) else "medium"
        return "single_shift_factory", confidence

    # Two shift factory: moderate weekend, moderate-to-high night activity
    if ww_ratio < 0.6 and nd_ratio > 0.4:
        confidence = "high" if nd_ratio > 0.6 else "medium"
        return "two_shift_factory", confidence

    # Commercial daytime: high peak concentration, low night, moderate weekend
    if peak_conc > 1.15 and nd_ratio < 0.5:
        confidence = "high" if peak_conc > 1.3 else "medium"
        return "commercial_daytime", confidence

    # Commercial extended: moderate all-around
    if peak_conc > 1.0 and nd_ratio >= 0.5:
        confidence = "medium"
        return "commercial_extended", confidence

    # Fallback: use load factor as tiebreaker
    if load_factor > 0.7:
        return "continuous_process", "low"
    if load_factor < 0.4:
        return "single_shift_factory", "low"

    return "two_shift_factory", "low"
