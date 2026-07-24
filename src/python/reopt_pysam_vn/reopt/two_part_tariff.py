"""Two-part tariff (Decree 146/2025) corrected economics for Vietnam.

This module computes the net economic impact of switching from the baseline
single-component TOU tariff to the two-part trial tariff introduced by
Decree 146/2025. The two-part tariff has two components:

1. Lower trial energy rates (Ca) - approximately 30-38% below baseline
2. A capacity/demand charge (Cp × monthly peak) in VND/kW-month

The net impact = energy_delta + demand_charge, where energy_delta is negative
(trial rates are lower) and demand_charge is positive (new charge). For
high-load-factor customers, the energy savings typically exceed the demand
charge, resulting in a net saving (negative net_impact_vnd).

All functions in this module work with 8760-element hourly series (kW or
VND/kWh) and use the same TOU hour-window classification as the baseline
tariff via imports from preprocess.py.
"""
from typing import Any

from reopt_pysam_vn.reopt.preprocess import _build_8760_rates, _build_hourly_rates

EXCHANGE_RATE_VND_PER_USD = 26_000.0


def build_trial_energy_rate_series(
    tariff_data: dict, *, basis: str = "range_midpoint"
) -> list[float]:
    """Build 8760-element trial Ca rate series (VND/kWh) from tariff data.

    Args:
        tariff_data: The "data" block from vn_tariff_2025.json (must contain
            "tou_schedule" and "demand_charge" keys).
        basis: How to convert published ranges to single values. Currently
            only "range_midpoint" is supported.

    Returns:
        8760-element list of trial energy rates in VND/kWh, classified into
        peak/standard/off-peak windows per the tou_schedule block.

    Raises:
        ValueError: If basis is not "range_midpoint".
    """
    if basis != "range_midpoint":
        raise ValueError(
            f"Unsupported basis '{basis}'. Only 'range_midpoint' is supported."
        )

    tou_schedule = tariff_data["tou_schedule"]
    trial_rates = tariff_data["demand_charge"]["two_part_tariff_trial"][
        "energy_charge_vnd_per_kwh"
    ]

    normal_mid = (trial_rates["normal_hours_range"][0] + trial_rates["normal_hours_range"][1]) / 2.0
    peak_mid = (trial_rates["peak_hours_range"][0] + trial_rates["peak_hours_range"][1]) / 2.0
    offpeak_mid = (trial_rates["offpeak_hours_range"][0] + trial_rates["offpeak_hours_range"][1]) / 2.0

    weekday_rates = _build_hourly_rates(
        tou_schedule["weekday"], peak_mid, normal_mid, offpeak_mid
    )
    sunday_rates = _build_hourly_rates(
        tou_schedule["sunday_and_public_holidays"], peak_mid, normal_mid, offpeak_mid
    )

    return _build_8760_rates(weekday_rates, sunday_rates, year=2025)


def reprice_energy_series(
    grid_import_kw: list[float],
    baseline_rates_vnd_per_kwh: list[float],
    trial_rates_vnd_per_kwh: list[float],
) -> dict[str, float]:
    """Compute energy cost delta between baseline and trial rate series.

    Args:
        grid_import_kw: 8760-element hourly grid import series (kW). Since
            each element represents one hour, kW is numerically equal to kWh
            for that hour.
        baseline_rates_vnd_per_kwh: 8760-element baseline TOU rate series.
        trial_rates_vnd_per_kwh: 8760-element trial Ca rate series.

    Returns:
        Dict with keys:
        - baseline_energy_cost_vnd: total energy cost at baseline rates
        - trial_energy_cost_vnd: total energy cost at trial rates
        - energy_delta_vnd: trial - baseline (negative means trial is cheaper)

    Raises:
        ValueError: If any input list is not exactly 8760 elements.
    """
    if len(grid_import_kw) != 8760:
        raise ValueError(
            f"grid_import_kw must be 8760 elements, got {len(grid_import_kw)}"
        )
    if len(baseline_rates_vnd_per_kwh) != 8760:
        raise ValueError(
            f"baseline_rates_vnd_per_kwh must be 8760 elements, got {len(baseline_rates_vnd_per_kwh)}"
        )
    if len(trial_rates_vnd_per_kwh) != 8760:
        raise ValueError(
            f"trial_rates_vnd_per_kwh must be 8760 elements, got {len(trial_rates_vnd_per_kwh)}"
        )

    baseline_cost = sum(g * r for g, r in zip(grid_import_kw, baseline_rates_vnd_per_kwh))
    trial_cost = sum(g * r for g, r in zip(grid_import_kw, trial_rates_vnd_per_kwh))

    return {
        "baseline_energy_cost_vnd": baseline_cost,
        "trial_energy_cost_vnd": trial_cost,
        "energy_delta_vnd": trial_cost - baseline_cost,
    }


def compute_two_part_impact(
    grid_import_kw: list[float],
    baseline_rates_vnd_per_kwh: list[float],
    trial_rates_vnd_per_kwh: list[float],
    capacity_charge_vnd_per_kw_month: float,
) -> dict[str, float]:
    """Compute net two-part tariff impact (energy delta + demand charge).

    Args:
        grid_import_kw: 8760-element hourly grid import series (kW).
        baseline_rates_vnd_per_kwh: 8760-element baseline TOU rate series.
        trial_rates_vnd_per_kwh: 8760-element trial Ca rate series.
        capacity_charge_vnd_per_kw_month: Trial capacity charge rate.

    Returns:
        Dict with keys:
        - energy_delta_vnd: energy cost change (negative = trial cheaper)
        - annual_demand_charge_vnd: total annual demand charge
        - net_impact_vnd: energy_delta + demand_charge (negative = net saving)
        - net_impact_usd: net_impact_vnd converted to USD
    """
    reprice = reprice_energy_series(
        grid_import_kw, baseline_rates_vnd_per_kwh, trial_rates_vnd_per_kwh
    )

    hours_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    idx = 0
    monthly_peaks = []
    for days in hours_per_month:
        hrs = days * 24
        chunk = grid_import_kw[idx : idx + hrs]
        monthly_peaks.append(max(chunk) if chunk else 0.0)
        idx += hrs

    annual_demand_charge = sum(monthly_peaks) * capacity_charge_vnd_per_kw_month

    net_impact_vnd = reprice["energy_delta_vnd"] + annual_demand_charge

    return {
        "energy_delta_vnd": reprice["energy_delta_vnd"],
        "annual_demand_charge_vnd": annual_demand_charge,
        "net_impact_vnd": net_impact_vnd,
        "net_impact_usd": net_impact_vnd / EXCHANGE_RATE_VND_PER_USD,
    }
