"""Rapid regulatory-regime bill comparison (GAP-05, PHASE-01).

Computes the annual EVN bill impact of switching a factory between two regulatory
regimes (e.g. Decision 963 vs Decision 14) in under a second, Python-only — no Julia
or REopt solve. This is the "instant toggle" surface for the client demo.

The heavy lifting reuses the existing tariff engine in ``preprocess.py``:
``build_vietnam_tariff()`` materializes the 8760-hour TOU rate series for any regime,
and ``resolve_vietnam_regime()`` exposes the regime's TOU window definitions for
peak/standard/off-peak consumption classification.

Usage:
    from reopt_pysam_vn.reopt.regime_impact import compute_regime_impact

    impact = compute_regime_impact(
        loads_kw,
        regime_a_id="decision_963_2026_current",
        regime_b_id="decision_14_2025_legacy",
        customer_type="industrial",
        voltage_level="medium_voltage_22kv_to_110kv",
    )
    print(impact.delta.annual_bill_delta_vnd, impact.delta.delta_pct)
"""

from dataclasses import asdict, dataclass
from datetime import date
from typing import Dict, List, Optional

from .preprocess import (
    HOURS_PER_YEAR,
    VNData,
    build_vietnam_tariff,
    convert_usd_to_vnd,
    load_vietnam_data,
    resolve_vietnam_regime,
)

# Hour-classification labels.
PEAK = "peak"
STANDARD = "standard"
OFFPEAK = "offpeak"


def _require_8760(series: List[float], name: str) -> None:
    """Raise ValueError unless ``series`` has exactly 8760 elements."""
    if len(series) != HOURS_PER_YEAR:
        raise ValueError(
            f"{name} must be {HOURS_PER_YEAR} hours long, got {len(series)}"
        )


@dataclass(frozen=True)
class RegimeSide:
    """Per-regime bill and consumption breakdown for one side of the comparison."""

    id: str
    name: str
    annual_bill_vnd: float
    peak_consumption_mwh: float
    offpeak_consumption_mwh: float
    normal_consumption_mwh: float


@dataclass(frozen=True)
class RegimeDelta:
    """Difference between regime B and regime A (B minus A)."""

    annual_bill_delta_vnd: float
    delta_pct: float
    peak_hours_changed: int
    peak_consumption_delta_mwh: float


@dataclass(frozen=True)
class RegimeImpact:
    """Result of comparing a factory load under two regulatory regimes."""

    regime_a: RegimeSide
    regime_b: RegimeSide
    delta: RegimeDelta
    analysis_timestamp: str
    customer_type: str
    voltage_level: str

    def to_dict(self) -> Dict:
        """Return a JSON-serializable dict (used by the artifact writer in PHASE-02)."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Hour classification
# ---------------------------------------------------------------------------


def _weekday_peak_hours(resolved_tariff: dict) -> set:
    """Return the set of weekday peak hours for a resolved regime tariff."""
    weekday = resolved_tariff["tou_schedule"]["weekday"]
    return {int(h) for h in weekday.get("peak_hours", [])}


def _build_day_classes(schedule_block: dict) -> List[str]:
    """Build a 24-element list mapping hour 0-23 to its TOU class.

    Mirrors ``preprocess._build_hourly_rates``: default to standard, then overlay
    peak / off-peak / standard hour assignments from the schedule block.
    """
    classes = [STANDARD] * 24
    for h in schedule_block.get("peak_hours", []):
        classes[int(h)] = PEAK
    for h in schedule_block.get("offpeak_hours", []):
        classes[int(h)] = OFFPEAK
    for h in schedule_block.get("standard_hours", []):
        classes[int(h)] = STANDARD
    return classes


def _classify_8760(resolved_tariff: dict, year: int) -> List[str]:
    """Build an 8760-length list of TOU classes using the same calendar mapping
    as ``preprocess._build_8760_rates`` (weekday schedule Mon-Sat, Sunday schedule Sun).
    """
    schedule = resolved_tariff["tou_schedule"]
    weekday_classes = _build_day_classes(schedule["weekday"])
    sunday_key = "sunday" if "sunday" in schedule else "sunday_and_public_holidays"
    sunday_classes = _build_day_classes(schedule[sunday_key])

    classes: List[str] = []
    from datetime import timedelta

    start_date = date(year, 1, 1)
    for day_offset in range(365):
        d = start_date + timedelta(days=day_offset)
        dow = d.isoweekday()  # 1=Monday ... 7=Sunday
        classes.extend(sunday_classes if dow == 7 else weekday_classes)
    return classes


def _month_index_8760(year: int) -> List[int]:
    """Return an 8760-length list of 0-based month indices using the 365-day calendar."""
    from datetime import timedelta

    months: List[int] = []
    start_date = date(year, 1, 1)
    for day_offset in range(365):
        d = start_date + timedelta(days=day_offset)
        months.extend([d.month - 1] * 24)
    return months


# ---------------------------------------------------------------------------
# Core: single-regime bill and breakdown
# ---------------------------------------------------------------------------


def _compute_regime_side(
    loads_kw: List[float],
    vn: VNData,
    regime_id: str,
    customer_type: str,
    voltage_level: str,
    year: int,
    month_index: List[int],
) -> RegimeSide:
    """Compute one regime's annual bill (VND) and peak/standard/off-peak MWh."""
    resolved = resolve_vietnam_regime(vn, regime_id)
    tariff_dict = build_vietnam_tariff(
        vn, customer_type, voltage_level, regime_id=regime_id, year=year
    )
    rates_usd = tariff_dict["tou_energy_rates_per_kwh"]
    demand_rates_usd = tariff_dict.get("monthly_demand_rates", [0.0] * 12)

    classes = _classify_8760(resolved["tariff"], year)

    # Energy bill (USD) + consumption buckets (kWh) in a single pass.
    energy_usd = 0.0
    peak_kwh = 0.0
    offpeak_kwh = 0.0
    normal_kwh = 0.0
    monthly_peak_kw = [0.0] * 12
    for h in range(HOURS_PER_YEAR):
        load = loads_kw[h]
        energy_usd += load * rates_usd[h]
        cls = classes[h]
        if cls == PEAK:
            peak_kwh += load
        elif cls == OFFPEAK:
            offpeak_kwh += load
        else:
            normal_kwh += load
        m = month_index[h]
        if load > monthly_peak_kw[m]:
            monthly_peak_kw[m] = load

    demand_usd = sum(
        monthly_peak_kw[m] * demand_rates_usd[m] for m in range(12)
    )
    annual_bill_vnd = convert_usd_to_vnd(
        energy_usd + demand_usd, exchange_rate=vn.exchange_rate
    )

    return RegimeSide(
        id=regime_id,
        name=resolved.get("label", regime_id),
        annual_bill_vnd=annual_bill_vnd,
        peak_consumption_mwh=peak_kwh / 1000.0,
        offpeak_consumption_mwh=offpeak_kwh / 1000.0,
        normal_consumption_mwh=normal_kwh / 1000.0,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_regime_impact(
    loads_kw: List[float],
    regime_a_id: str,
    regime_b_id: str,
    customer_type: str,
    voltage_level: str,
    vn: Optional[VNData] = None,
    year: Optional[int] = None,
) -> RegimeImpact:
    """Compare a factory's annual EVN bill under two regulatory regimes.

    Args:
        loads_kw: 8760-hour load profile in kW.
        regime_a_id: Baseline regime id (the "from" side).
        regime_b_id: Comparison regime id (the "to" side); delta is B minus A.
        customer_type: "industrial" or "commercial".
        voltage_level: e.g. "medium_voltage_22kv_to_110kv".
        vn: Pre-loaded Vietnam data (auto-loaded once if None).
        year: Calendar year for the 8760 schedule (defaults to current year).

    Returns:
        A ``RegimeImpact`` with per-regime bills/consumption and the A→B delta.

    Raises:
        ValueError: if ``loads_kw`` is not 8760 hours long.
    """
    _require_8760(loads_kw, "loads_kw")
    if vn is None:
        vn = load_vietnam_data()
    if year is None:
        year = date.today().year

    month_index = _month_index_8760(year)

    side_a = _compute_regime_side(
        loads_kw, vn, regime_a_id, customer_type, voltage_level, year, month_index
    )
    side_b = _compute_regime_side(
        loads_kw, vn, regime_b_id, customer_type, voltage_level, year, month_index
    )

    peak_a = _weekday_peak_hours(resolve_vietnam_regime(vn, regime_a_id)["tariff"])
    peak_b = _weekday_peak_hours(resolve_vietnam_regime(vn, regime_b_id)["tariff"])
    peak_hours_changed = len(peak_a.symmetric_difference(peak_b))

    bill_delta = side_b.annual_bill_vnd - side_a.annual_bill_vnd
    delta_pct = (
        (bill_delta / side_a.annual_bill_vnd) * 100.0
        if side_a.annual_bill_vnd
        else 0.0
    )

    delta = RegimeDelta(
        annual_bill_delta_vnd=bill_delta,
        delta_pct=delta_pct,
        peak_hours_changed=peak_hours_changed,
        peak_consumption_delta_mwh=(
            side_b.peak_consumption_mwh - side_a.peak_consumption_mwh
        ),
    )

    return RegimeImpact(
        regime_a=side_a,
        regime_b=side_b,
        delta=delta,
        analysis_timestamp=date.today().isoformat(),
        customer_type=customer_type,
        voltage_level=voltage_level,
    )


# ---------------------------------------------------------------------------
# PHASE-02 — Solar / BESS value impact, artifact, orchestration
# ---------------------------------------------------------------------------


def regime_tou_rates_vnd(
    vn: VNData,
    customer_type: str,
    voltage_level: str,
    regime_id: str,
    year: Optional[int] = None,
) -> List[float]:
    """Return the 8760-hour TOU energy rate series for a regime in VND per kWh.

    Wraps ``build_vietnam_tariff()`` (which returns USD) and converts back to VND
    so downstream monetary outputs stay in VND, consistent with PHASE-01 bills.
    """
    if year is None:
        year = date.today().year
    tariff_dict = build_vietnam_tariff(
        vn, customer_type, voltage_level, regime_id=regime_id, year=year
    )
    return [
        convert_usd_to_vnd(r, exchange_rate=vn.exchange_rate)
        for r in tariff_dict["tou_energy_rates_per_kwh"]
    ]


@dataclass(frozen=True)
class SolarValueDelta:
    """Avoided-cost value of a PV profile under two regimes (delta is B minus A)."""

    pv_annual_generation_mwh: float
    regime_a_value_vnd: float
    regime_b_value_vnd: float
    delta_value_vnd: float
    delta_pct: float


@dataclass(frozen=True)
class BessArbitrageDelta:
    """Theoretical-maximum BESS arbitrage value under two regimes (delta is B minus A).

    Arbitrage is idealized: perfect foresight, no round-trip efficiency losses. The
    number of cycles per day equals the number of distinct daily peak windows (charge
    at off-peak, discharge at peak). Treat values as a theoretical ceiling.
    """

    bess_power_kw: float
    bess_capacity_kwh: float
    regime_a_cycles_per_day: int
    regime_b_cycles_per_day: int
    regime_a_annual_arbitrage_vnd: float
    regime_b_annual_arbitrage_vnd: float
    delta_annual_arbitrage_vnd: float
    basis: str = "theoretical_maximum_no_efficiency_losses"


def estimate_solar_value_impact(
    loads_kw: List[float],
    regime_a_tariff: List[float],
    regime_b_tariff: List[float],
    pv_profile_kw: List[float],
) -> SolarValueDelta:
    """Estimate the avoided-cost value of a PV profile under two regimes.

    Avoided cost per hour is the energy the PV displaces (capped at on-site load)
    valued at that regime's TOU rate: ``min(pv[h], load[h]) * rate[h]``.

    Args:
        loads_kw: 8760 on-site load (caps behind-the-meter avoided energy).
        regime_a_tariff: 8760 VND/kWh rates for regime A.
        regime_b_tariff: 8760 VND/kWh rates for regime B.
        pv_profile_kw: 8760 PV generation profile in kW.
    """
    _require_8760(loads_kw, "loads_kw")
    _require_8760(regime_a_tariff, "regime_a_tariff")
    _require_8760(regime_b_tariff, "regime_b_tariff")
    _require_8760(pv_profile_kw, "pv_profile_kw")

    value_a = 0.0
    value_b = 0.0
    for h in range(HOURS_PER_YEAR):
        avoided = pv_profile_kw[h]
        if loads_kw[h] < avoided:
            avoided = loads_kw[h]
        value_a += avoided * regime_a_tariff[h]
        value_b += avoided * regime_b_tariff[h]

    delta_value = value_b - value_a
    delta_pct = (delta_value / value_a) * 100.0 if value_a else 0.0
    return SolarValueDelta(
        pv_annual_generation_mwh=sum(pv_profile_kw) / 1000.0,
        regime_a_value_vnd=value_a,
        regime_b_value_vnd=value_b,
        delta_value_vnd=delta_value,
        delta_pct=delta_pct,
    )


def _weekday_peak_window_count(rates: List[float]) -> int:
    """Count distinct daily peak windows from an 8760 rate series.

    Peak hours-of-day are those that ever carry the maximum rate (peak appears only on
    weekdays in these schedules). Contiguous runs of peak hours-of-day are counted as
    separate windows; a wrap-around run (hour 23 and hour 0 both peak) counts as one.
    """
    peak_rate = max(rates)
    is_peak_hod = [False] * 24
    for h in range(HOURS_PER_YEAR):
        if rates[h] == peak_rate:
            is_peak_hod[h % 24] = True

    windows = 0
    for hour in range(24):
        if is_peak_hod[hour] and not is_peak_hod[(hour - 1) % 24]:
            windows += 1
    return windows


def _arbitrage_days(rates: List[float]) -> int:
    """Number of days in the year that contain at least one peak hour."""
    peak_rate = max(rates)
    days = 0
    for d in range(365):
        slice_ = rates[d * 24 : (d + 1) * 24]
        if any(r == peak_rate for r in slice_):
            days += 1
    return days


def _annual_arbitrage_vnd(
    rates: List[float], bess_power_kw: float, bess_capacity_kwh: float
) -> tuple:
    """Return (cycles_per_day, annual_arbitrage_vnd) for one regime.

    Per cycle, the battery charges its usable energy at the off-peak rate and discharges
    it at the peak rate. Usable energy per cycle is capped by power over a 2-hour nominal
    charge/discharge block (``power * 2``) and by capacity — a theoretical maximum.
    """
    peak_rate = max(rates)
    offpeak_rate = min(rates)
    spread = peak_rate - offpeak_rate
    cycles_per_day = _weekday_peak_window_count(rates)
    usable_energy_kwh = min(bess_capacity_kwh, bess_power_kw * 2.0)
    annual = (
        _arbitrage_days(rates) * cycles_per_day * usable_energy_kwh * spread
    )
    return cycles_per_day, annual


def estimate_bess_arbitrage_impact(
    regime_a_tariff: List[float],
    regime_b_tariff: List[float],
    bess_power_kw: float,
    bess_capacity_kwh: float,
) -> BessArbitrageDelta:
    """Estimate theoretical BESS arbitrage value under two regimes (delta is B minus A)."""
    _require_8760(regime_a_tariff, "regime_a_tariff")
    _require_8760(regime_b_tariff, "regime_b_tariff")
    if bess_power_kw <= 0 or bess_capacity_kwh <= 0:
        raise ValueError("bess_power_kw and bess_capacity_kwh must be positive")

    cycles_a, annual_a = _annual_arbitrage_vnd(
        regime_a_tariff, bess_power_kw, bess_capacity_kwh
    )
    cycles_b, annual_b = _annual_arbitrage_vnd(
        regime_b_tariff, bess_power_kw, bess_capacity_kwh
    )
    return BessArbitrageDelta(
        bess_power_kw=bess_power_kw,
        bess_capacity_kwh=bess_capacity_kwh,
        regime_a_cycles_per_day=cycles_a,
        regime_b_cycles_per_day=cycles_b,
        regime_a_annual_arbitrage_vnd=annual_a,
        regime_b_annual_arbitrage_vnd=annual_b,
        delta_annual_arbitrage_vnd=annual_b - annual_a,
    )


@dataclass(frozen=True)
class RegimeComparisonArtifact:
    """Combined PHASE-01 + PHASE-02 result, ready to serialize to JSON."""

    regime_impact: RegimeImpact
    solar: Optional[SolarValueDelta]
    bess: Optional[BessArbitrageDelta]
    generated_at: str
    inputs: Dict

    def to_dict(self) -> Dict:
        return {
            "regime_impact": self.regime_impact.to_dict(),
            "solar": asdict(self.solar) if self.solar is not None else None,
            "bess": asdict(self.bess) if self.bess is not None else None,
            "generated_at": self.generated_at,
            "inputs": self.inputs,
        }


def build_regime_comparison(
    loads_kw: List[float],
    regime_a_id: str,
    regime_b_id: str,
    customer_type: str,
    voltage_level: str,
    pv_profile_kw: Optional[List[float]] = None,
    bess_power_kw: Optional[float] = None,
    bess_capacity_kwh: Optional[float] = None,
    vn: Optional[VNData] = None,
    year: Optional[int] = None,
) -> RegimeComparisonArtifact:
    """Orchestrate the full regime comparison: bill impact + optional solar + optional BESS."""
    if vn is None:
        vn = load_vietnam_data()
    if year is None:
        year = date.today().year

    impact = compute_regime_impact(
        loads_kw, regime_a_id, regime_b_id, customer_type, voltage_level, vn=vn, year=year
    )

    rates_a = regime_tou_rates_vnd(vn, customer_type, voltage_level, regime_a_id, year)
    rates_b = regime_tou_rates_vnd(vn, customer_type, voltage_level, regime_b_id, year)

    solar = None
    if pv_profile_kw is not None:
        solar = estimate_solar_value_impact(loads_kw, rates_a, rates_b, pv_profile_kw)

    bess = None
    if bess_power_kw is not None and bess_capacity_kwh is not None:
        bess = estimate_bess_arbitrage_impact(
            rates_a, rates_b, bess_power_kw, bess_capacity_kwh
        )

    return RegimeComparisonArtifact(
        regime_impact=impact,
        solar=solar,
        bess=bess,
        generated_at=date.today().isoformat(),
        inputs={
            "regime_a_id": regime_a_id,
            "regime_b_id": regime_b_id,
            "customer_type": customer_type,
            "voltage_level": voltage_level,
            "year": year,
            "has_pv": pv_profile_kw is not None,
            "bess_power_kw": bess_power_kw,
            "bess_capacity_kwh": bess_capacity_kwh,
        },
    )
