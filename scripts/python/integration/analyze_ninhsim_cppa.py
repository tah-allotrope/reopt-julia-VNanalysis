"""
Analyze Ninhsim REopt outputs for the bundled-CPPA customer-price target.

The study logic is:
- customer buys renewable delivery under a bundled CPPA strike
- residual unmet load remains on EVN TOU
- the maximum customer-equivalent strike is the strike that keeps the blended
  paid price equal to the current weighted EVN benchmark
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_STRIKE_ADJUSTMENT_FRACTIONS = [-0.15, -0.10, -0.05, 0.0, 0.05]
DEFAULT_ANNUAL_GENERATION_DEGRADATION_FRACTION = 0.005
DEFAULT_ANNUAL_LOAD_GROWTH_FRACTION = 0.01


def _financial_value(results: dict, key: str, default: float) -> float:
    return float(results.get("Financial", {}).get(key) or default)


def _annual_energy_kwh(tech_results: dict) -> float:
    return float(
        tech_results.get("year_one_energy_produced_kwh")
        or tech_results.get("annual_energy_produced_kwh")
        or 0.0
    )


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) >= 8760:
        return list(series[:8760])
    return list(series) + [0.0] * (8760 - len(series))


def _sum_series(*series_list: list[float]) -> list[float]:
    padded = [_pad_to_8760(series) for series in series_list]
    return [sum(values) for values in zip(*padded)]


def _band_label(relative_to_ceiling_fraction: float) -> str:
    if abs(relative_to_ceiling_fraction) < 1e-12:
        return "ceiling"

    percentage = abs(relative_to_ceiling_fraction) * 100.0
    whole_percentage = round(percentage)
    if whole_percentage == percentage:
        percentage_text = str(whole_percentage)
    else:
        percentage_text = f"{percentage:.1f}".rstrip("0").rstrip(".")

    direction = "below" if relative_to_ceiling_fraction < 0.0 else "above"
    return f"{percentage_text}% {direction} ceiling"


def _clean_small(value: float, tolerance: float = 1e-6) -> float:
    return 0.0 if abs(value) <= tolerance else value


def load_reopt_delivery_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    storage = results.get("ElectricStorage", {})
    return _sum_series(
        pv.get("electric_to_load_series_kw", []),
        wind.get("electric_to_load_series_kw", []),
        storage.get("storage_to_load_series_kw", []),
    )


def load_grid_supply_profile(results: dict) -> list[float]:
    utility = results.get("ElectricUtility", {})
    return _pad_to_8760(utility.get("electric_to_load_series_kw", []))


def load_renewable_export_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    return _sum_series(
        pv.get("electric_to_grid_series_kw", []),
        wind.get("electric_to_grid_series_kw", []),
    )


def _merchant_price_fraction_of_evn(extracted: dict) -> float:
    weighted = float(extracted["benchmark"]["weighted_evn_price_usd_per_kwh"] or 0.0)
    wholesale = float(extracted["benchmark"].get("wholesale_rate_usd_per_kwh") or 0.0)
    if weighted <= 0.0:
        return 0.0
    return wholesale / weighted


def calculate_customer_bill_breakdown(results: dict, extracted: dict) -> dict:
    renewable_delivery_kw = load_reopt_delivery_profile(results)
    grid_supply_kw = load_grid_supply_profile(results)
    evn_rates_usd = _pad_to_8760(
        extracted["evn_tariff"]["tou_energy_rates_usd_per_kwh"]
    )
    load_series_kw = _pad_to_8760(extracted["loads_kw"])

    renewable_kwh = sum(max(0.0, value) for value in renewable_delivery_kw)
    grid_kwh = sum(max(0.0, value) for value in grid_supply_kw)
    total_load_kwh = sum(max(0.0, value) for value in load_series_kw)
    grid_cost_usd = sum(
        max(0.0, grid_kw) * rate for grid_kw, rate in zip(grid_supply_kw, evn_rates_usd)
    )
    benchmark_cost_usd = (
        total_load_kwh * extracted["benchmark"]["weighted_evn_price_usd_per_kwh"]
    )

    return {
        "renewable_delivered_kwh": renewable_kwh,
        "grid_supplied_kwh": grid_kwh,
        "total_load_kwh": total_load_kwh,
        "grid_cost_usd": grid_cost_usd,
        "benchmark_customer_cost_usd": benchmark_cost_usd,
    }


def calculate_customer_equivalent_strike(results: dict, extracted: dict) -> dict:
    bill = calculate_customer_bill_breakdown(results, extracted)
    renewable_kwh = bill["renewable_delivered_kwh"]
    benchmark_cost_usd = bill["benchmark_customer_cost_usd"]
    grid_cost_usd = bill["grid_cost_usd"]

    max_strike_usd = 0.0
    if renewable_kwh > 0:
        max_strike_usd = max(0.0, (benchmark_cost_usd - grid_cost_usd) / renewable_kwh)

    customer_blended_price = (
        (grid_cost_usd + renewable_kwh * max_strike_usd) / bill["total_load_kwh"]
        if bill["total_load_kwh"]
        else 0.0
    )
    exchange_rate = extracted["benchmark"]["exchange_rate_vnd_per_usd"]

    return {
        **bill,
        "max_cppa_strike_usd_per_kwh": max_strike_usd,
        "max_cppa_strike_vnd_per_kwh": max_strike_usd * exchange_rate,
        "customer_blended_price_at_max_strike_usd_per_kwh": customer_blended_price,
        "customer_blended_price_at_max_strike_vnd_per_kwh": customer_blended_price
        * exchange_rate,
        "weighted_evn_benchmark_usd_per_kwh": extracted["benchmark"][
            "weighted_evn_price_usd_per_kwh"
        ],
        "weighted_evn_benchmark_vnd_per_kwh": extracted["benchmark"][
            "weighted_evn_price_vnd_per_kwh"
        ],
    }


def calculate_multi_year_cppa_path(
    results: dict,
    extracted: dict,
    analysis_years: int | None = None,
    strike_adjustment_fraction: float = 0.0,
) -> list[dict]:
    pricing = calculate_customer_equivalent_strike(results, extracted)
    escalation = _financial_value(results, "elec_cost_escalation_rate_fraction", 0.05)
    years = int(
        analysis_years
        or _financial_value(results, "analysis_years", 20)
        or extracted.get("assumptions", {}).get("analysis_years", 20)
    )
    renewable_kwh = pricing["renewable_delivered_kwh"]
    grid_kwh = pricing["grid_supplied_kwh"]
    total_load_kwh = pricing["total_load_kwh"]
    year_one_grid_rate = pricing["grid_cost_usd"] / grid_kwh if grid_kwh else 0.0
    exchange_rate = extracted["benchmark"]["exchange_rate_vnd_per_usd"]

    path = []
    for year in range(1, years + 1):
        multiplier = (1.0 + escalation) ** (year - 1)
        strike_usd = (
            pricing["max_cppa_strike_usd_per_kwh"]
            * (1.0 + strike_adjustment_fraction)
            * multiplier
        )
        grid_rate_usd = year_one_grid_rate * multiplier
        benchmark_usd = pricing["weighted_evn_benchmark_usd_per_kwh"] * multiplier
        blended_usd = (
            (renewable_kwh * strike_usd + grid_kwh * grid_rate_usd) / total_load_kwh
            if total_load_kwh
            else 0.0
        )
        path.append(
            {
                "year": year,
                "escalation_multiplier": multiplier,
                "relative_to_ceiling_fraction": strike_adjustment_fraction,
                "band_label": _band_label(strike_adjustment_fraction),
                "renewable_delivered_kwh": renewable_kwh,
                "grid_supplied_kwh": grid_kwh,
                "total_load_kwh": total_load_kwh,
                "cPPA_strike_usd_per_kwh": strike_usd,
                "cPPA_strike_vnd_per_kwh": strike_usd * exchange_rate,
                "residual_grid_price_usd_per_kwh": grid_rate_usd,
                "residual_grid_price_vnd_per_kwh": grid_rate_usd * exchange_rate,
                "weighted_evn_benchmark_usd_per_kwh": benchmark_usd,
                "weighted_evn_benchmark_vnd_per_kwh": benchmark_usd * exchange_rate,
                "customer_blended_price_usd_per_kwh": blended_usd,
                "customer_blended_price_vnd_per_kwh": blended_usd * exchange_rate,
            }
        )
    return path


def calculate_financial_screening_view(
    results: dict,
    extracted: dict,
    analysis_years: int | None = None,
    strike_adjustment_fraction: float = 0.0,
) -> list[dict]:
    path = calculate_multi_year_cppa_path(
        results,
        extracted,
        analysis_years,
        strike_adjustment_fraction=strike_adjustment_fraction,
    )

    view = []
    for year in path:
        renewable_kwh = year["renewable_delivered_kwh"]
        grid_kwh = year["grid_supplied_kwh"]
        total_load_kwh = year["total_load_kwh"]
        renewable_cost_usd = renewable_kwh * year["cPPA_strike_usd_per_kwh"]
        grid_cost_usd = grid_kwh * year["residual_grid_price_usd_per_kwh"]
        customer_total_cost_usd = renewable_cost_usd + grid_cost_usd
        benchmark_cost_usd = year["weighted_evn_benchmark_usd_per_kwh"] * total_load_kwh
        customer_delta_vs_evn_usd = _clean_small(
            benchmark_cost_usd - customer_total_cost_usd
        )

        view.append(
            {
                "year": year["year"],
                "relative_to_ceiling_fraction": year["relative_to_ceiling_fraction"],
                "band_label": year["band_label"],
                "developer_revenue_usd": renewable_cost_usd,
                "offtaker_renewable_payment_usd": renewable_cost_usd,
                "offtaker_residual_grid_cost_usd": grid_cost_usd,
                "customer_total_cost_usd": customer_total_cost_usd,
                "benchmark_evn_cost_usd": benchmark_cost_usd,
                "customer_delta_vs_evn_usd": customer_delta_vs_evn_usd,
                "customer_savings_vs_evn_usd": max(0.0, customer_delta_vs_evn_usd),
                "customer_premium_vs_evn_usd": max(
                    0.0, customer_total_cost_usd - benchmark_cost_usd
                ),
            }
        )

    return view


def _discounted_npv(entries: list[dict], key: str, discount_rate: float) -> float:
    npv = 0.0
    for entry in entries:
        year = int(entry["year"])
        npv += float(entry[key]) / ((1.0 + discount_rate) ** year)
    return _clean_small(npv)


def calculate_cppa_sensitivity_bands(
    results: dict,
    extracted: dict,
    strike_adjustment_fractions: list[float] | None = None,
    analysis_years: int | None = None,
) -> list[dict]:
    financial = results.get("Financial", {})
    owner_discount_rate = float(financial.get("owner_discount_rate_fraction") or 0.08)
    offtaker_discount_rate = float(
        financial.get("offtaker_discount_rate_fraction") or 0.10
    )
    adjustments = strike_adjustment_fractions or DEFAULT_STRIKE_ADJUSTMENT_FRACTIONS
    bands = []

    for adjustment in adjustments:
        path = calculate_multi_year_cppa_path(
            results,
            extracted,
            analysis_years=analysis_years,
            strike_adjustment_fraction=float(adjustment),
        )
        screening_view = calculate_financial_screening_view(
            results,
            extracted,
            analysis_years=analysis_years,
            strike_adjustment_fraction=float(adjustment),
        )
        year_one = screening_view[0]
        year_one_path = path[0]
        developer_revenue_npv = _discounted_npv(
            screening_view,
            "developer_revenue_usd",
            owner_discount_rate,
        )
        offtaker_cost_npv = _discounted_npv(
            screening_view,
            "customer_total_cost_usd",
            offtaker_discount_rate,
        )
        benchmark_evn_cost_npv = _discounted_npv(
            screening_view,
            "benchmark_evn_cost_usd",
            offtaker_discount_rate,
        )
        customer_savings_npv = _discounted_npv(
            screening_view,
            "customer_savings_vs_evn_usd",
            offtaker_discount_rate,
        )
        customer_premium_npv = _discounted_npv(
            screening_view,
            "customer_premium_vs_evn_usd",
            offtaker_discount_rate,
        )

        bands.append(
            {
                "band_label": _band_label(float(adjustment)),
                "relative_to_ceiling_fraction": float(adjustment),
                "strike_multiplier_vs_ceiling": 1.0 + float(adjustment),
                "year_one_cppa_strike_usd_per_kwh": year_one_path[
                    "cPPA_strike_usd_per_kwh"
                ],
                "year_one_cppa_strike_vnd_per_kwh": year_one_path[
                    "cPPA_strike_vnd_per_kwh"
                ],
                "year_one_customer_total_cost_usd": year_one["customer_total_cost_usd"],
                "year_one_customer_savings_usd": year_one[
                    "customer_savings_vs_evn_usd"
                ],
                "year_one_customer_premium_usd": year_one[
                    "customer_premium_vs_evn_usd"
                ],
                "developer_revenue_npv_usd": developer_revenue_npv,
                "offtaker_cost_npv_usd": offtaker_cost_npv,
                "benchmark_evn_cost_npv_usd": benchmark_evn_cost_npv,
                "customer_savings_npv_usd": customer_savings_npv,
                "customer_premium_npv_usd": customer_premium_npv,
                "customer_delta_npv_usd": benchmark_evn_cost_npv - offtaker_cost_npv,
                "screening_view": screening_view,
                "review_flag": (
                    "savings"
                    if customer_savings_npv > 0.0
                    else ("premium" if customer_premium_npv > 0.0 else "parity")
                ),
            }
        )

    return bands


def select_customer_first_recommendation(strike_sensitivity_bands: list[dict]) -> dict:
    shortlist = [
        band
        for band in strike_sensitivity_bands
        if abs(float(band["relative_to_ceiling_fraction"])) <= 0.05
    ]
    savings_positive = [
        band for band in shortlist if band["customer_savings_npv_usd"] > 0.0
    ]

    if savings_positive:
        recommended = max(
            savings_positive,
            key=lambda band: (
                float(band["developer_revenue_npv_usd"]),
                float(band["customer_savings_npv_usd"]),
            ),
        )
        selection_rule = (
            "Choose the highest developer-revenue shortlist band that still keeps "
            "customer savings positive."
        )
    else:
        parity_bands = [
            band for band in shortlist if band["customer_premium_npv_usd"] == 0.0
        ]
        recommended = (
            parity_bands[0]
            if parity_bands
            else min(
                shortlist,
                key=lambda band: float(band["customer_premium_npv_usd"]),
            )
        )
        selection_rule = (
            "No savings-positive shortlist band remains, so choose the lowest-risk "
            "customer outcome."
        )

    return {
        "recommended_band_label": recommended["band_label"],
        "relative_to_ceiling_fraction": recommended["relative_to_ceiling_fraction"],
        "year_one_cppa_strike_vnd_per_kwh": recommended[
            "year_one_cppa_strike_vnd_per_kwh"
        ],
        "year_one_cppa_strike_usd_per_kwh": recommended[
            "year_one_cppa_strike_usd_per_kwh"
        ],
        "screening_developer_revenue_npv_usd": recommended["developer_revenue_npv_usd"],
        "screening_customer_savings_npv_usd": recommended["customer_savings_npv_usd"],
        "screening_customer_premium_npv_usd": recommended["customer_premium_npv_usd"],
        "selection_rule": selection_rule,
        "why_this_band": (
            "This is the strongest shortlist band that still protects the customer "
            "from paying above the EVN benchmark in the simple screening view."
        ),
    }


def calculate_customer_first_annual_path(
    results: dict,
    extracted: dict,
    strike_adjustment_fraction: float,
    analysis_years: int | None = None,
    annual_generation_degradation_fraction: float = DEFAULT_ANNUAL_GENERATION_DEGRADATION_FRACTION,
    annual_load_growth_fraction: float = DEFAULT_ANNUAL_LOAD_GROWTH_FRACTION,
    unmatched_energy_price_fraction_of_evn: float | None = None,
) -> list[dict]:
    pricing = calculate_customer_equivalent_strike(results, extracted)
    escalation = _financial_value(results, "elec_cost_escalation_rate_fraction", 0.05)
    years = int(
        analysis_years
        or _financial_value(results, "analysis_years", 20)
        or extracted.get("assumptions", {}).get("analysis_years", 20)
    )
    exchange_rate = extracted["benchmark"]["exchange_rate_vnd_per_usd"]
    load_series_kw = _pad_to_8760(extracted["loads_kw"])
    evn_rates_usd = _pad_to_8760(
        extracted["evn_tariff"]["tou_energy_rates_usd_per_kwh"]
    )
    renewable_available_series_kw = _sum_series(
        load_reopt_delivery_profile(results),
        load_renewable_export_profile(results),
    )
    merchant_fraction = (
        float(unmatched_energy_price_fraction_of_evn)
        if unmatched_energy_price_fraction_of_evn is not None
        else _merchant_price_fraction_of_evn(extracted)
    )

    path = []
    for year in range(1, years + 1):
        generation_factor = (1.0 - annual_generation_degradation_fraction) ** (year - 1)
        load_factor = (1.0 + annual_load_growth_fraction) ** (year - 1)
        price_factor = (1.0 + escalation) ** (year - 1)
        strike_usd = (
            pricing["max_cppa_strike_usd_per_kwh"]
            * (1.0 + strike_adjustment_fraction)
            * price_factor
        )
        available_kw = [
            value * generation_factor for value in renewable_available_series_kw
        ]
        load_kw = [value * load_factor for value in load_series_kw]
        matched_kw = [
            min(available, load) for available, load in zip(available_kw, load_kw)
        ]
        residual_grid_kw = [
            max(0.0, load - matched) for load, matched in zip(load_kw, matched_kw)
        ]
        unmatched_kw = [
            max(0.0, available - matched)
            for available, matched in zip(available_kw, matched_kw)
        ]
        scaled_evn_rates = [rate * price_factor for rate in evn_rates_usd]
        merchant_rates = [rate * merchant_fraction for rate in scaled_evn_rates]

        renewable_delivered_kwh = sum(matched_kw)
        residual_grid_kwh = sum(residual_grid_kw)
        unmatched_renewable_kwh = sum(unmatched_kw)
        total_load_kwh = sum(load_kw)
        total_generation_kwh = sum(available_kw)
        customer_renewable_payment_usd = renewable_delivered_kwh * strike_usd
        residual_grid_cost_usd = sum(
            grid_kw * rate for grid_kw, rate in zip(residual_grid_kw, scaled_evn_rates)
        )
        customer_total_cost_usd = (
            customer_renewable_payment_usd + residual_grid_cost_usd
        )
        benchmark_evn_cost_usd = sum(
            load * rate for load, rate in zip(load_kw, scaled_evn_rates)
        )
        merchant_revenue_usd = sum(
            unmatched * rate for unmatched, rate in zip(unmatched_kw, merchant_rates)
        )
        developer_revenue_usd = customer_renewable_payment_usd + merchant_revenue_usd
        customer_delta_vs_evn_usd = _clean_small(
            benchmark_evn_cost_usd - customer_total_cost_usd
        )

        path.append(
            {
                "year": year,
                "band_label": _band_label(strike_adjustment_fraction),
                "relative_to_ceiling_fraction": strike_adjustment_fraction,
                "generation_degradation_multiplier": generation_factor,
                "load_growth_multiplier": load_factor,
                "price_escalation_multiplier": price_factor,
                "cPPA_strike_usd_per_kwh": strike_usd,
                "cPPA_strike_vnd_per_kwh": strike_usd * exchange_rate,
                "merchant_price_fraction_of_evn": merchant_fraction,
                "merchant_price_usd_per_kwh": (
                    merchant_revenue_usd / unmatched_renewable_kwh
                    if unmatched_renewable_kwh
                    else merchant_fraction
                    * pricing["weighted_evn_benchmark_usd_per_kwh"]
                    * price_factor
                ),
                "merchant_price_vnd_per_kwh": (
                    (
                        merchant_revenue_usd / unmatched_renewable_kwh
                        if unmatched_renewable_kwh
                        else merchant_fraction
                        * pricing["weighted_evn_benchmark_usd_per_kwh"]
                        * price_factor
                    )
                    * exchange_rate
                ),
                "residual_grid_price_usd_per_kwh": (
                    residual_grid_cost_usd / residual_grid_kwh
                    if residual_grid_kwh
                    else 0.0
                ),
                "residual_grid_price_vnd_per_kwh": (
                    (residual_grid_cost_usd / residual_grid_kwh) * exchange_rate
                    if residual_grid_kwh
                    else 0.0
                ),
                "weighted_evn_benchmark_usd_per_kwh": (
                    benchmark_evn_cost_usd / total_load_kwh if total_load_kwh else 0.0
                ),
                "weighted_evn_benchmark_vnd_per_kwh": (
                    (benchmark_evn_cost_usd / total_load_kwh) * exchange_rate
                    if total_load_kwh
                    else 0.0
                ),
                "total_generation_kwh": total_generation_kwh,
                "renewable_delivered_kwh": renewable_delivered_kwh,
                "unmatched_renewable_kwh": unmatched_renewable_kwh,
                "grid_supplied_kwh": residual_grid_kwh,
                "total_load_kwh": total_load_kwh,
                "developer_revenue_usd": developer_revenue_usd,
                "developer_revenue_from_customer_usd": customer_renewable_payment_usd,
                "developer_revenue_from_merchant_usd": merchant_revenue_usd,
                "customer_total_cost_usd": customer_total_cost_usd,
                "customer_renewable_payment_usd": customer_renewable_payment_usd,
                "customer_residual_grid_cost_usd": residual_grid_cost_usd,
                "benchmark_evn_cost_usd": benchmark_evn_cost_usd,
                "customer_delta_vs_evn_usd": customer_delta_vs_evn_usd,
                "customer_savings_vs_evn_usd": max(0.0, customer_delta_vs_evn_usd),
                "customer_premium_vs_evn_usd": max(
                    0.0, customer_total_cost_usd - benchmark_evn_cost_usd
                ),
            }
        )

    return path


def summarize_customer_first_annual_path(
    annual_path: list[dict], owner_discount_rate: float, offtaker_discount_rate: float
) -> dict:
    return {
        "developer_revenue_npv_usd": _discounted_npv(
            annual_path, "developer_revenue_usd", owner_discount_rate
        ),
        "developer_merchant_revenue_npv_usd": _discounted_npv(
            annual_path, "developer_revenue_from_merchant_usd", owner_discount_rate
        ),
        "offtaker_cost_npv_usd": _discounted_npv(
            annual_path, "customer_total_cost_usd", offtaker_discount_rate
        ),
        "benchmark_evn_cost_npv_usd": _discounted_npv(
            annual_path, "benchmark_evn_cost_usd", offtaker_discount_rate
        ),
        "customer_savings_npv_usd": _discounted_npv(
            annual_path, "customer_savings_vs_evn_usd", offtaker_discount_rate
        ),
        "customer_premium_npv_usd": _discounted_npv(
            annual_path, "customer_premium_vs_evn_usd", offtaker_discount_rate
        ),
        "unmatched_renewable_npv_kwh": _discounted_npv(
            annual_path, "unmatched_renewable_kwh", offtaker_discount_rate
        ),
    }


def build_commercial_candidate_memo(summary: dict) -> dict:
    recommendation = summary["customer_first_recommendation"]
    screening_bands = {
        band["band_label"]: band for band in summary["strike_sensitivity_bands"]
    }
    shortlist_labels = ["5% below ceiling", "ceiling", "5% above ceiling"]
    candidates = []

    for label in shortlist_labels:
        screening = screening_bands[label]
        if label == recommendation["recommended_band_label"]:
            status = "advance"
            rationale = (
                "Best customer-first option: preserves positive customer savings while "
                "still keeping strong developer revenue."
            )
        elif screening["customer_premium_npv_usd"] > 0.0:
            status = "discard"
            rationale = (
                "Creates explicit customer premium, so it conflicts with the accepted "
                "customer-first framing."
            )
        else:
            status = "hold"
            rationale = (
                "Commercially viable fallback with lower customer risk, but weaker customer "
                "savings upside than the recommended band."
            )

        candidates.append(
            {
                "band_label": label,
                "status": status,
                "year_one_cppa_strike_vnd_per_kwh": screening[
                    "year_one_cppa_strike_vnd_per_kwh"
                ],
                "developer_revenue_npv_usd": screening["developer_revenue_npv_usd"],
                "customer_savings_npv_usd": screening["customer_savings_npv_usd"],
                "customer_premium_npv_usd": screening["customer_premium_npv_usd"],
                "screening_view_flag": screening["review_flag"],
                "rationale": rationale,
            }
        )

    return {
        "recommended_band_label": recommendation["recommended_band_label"],
        "decision": "advance",
        "decision_summary": (
            f"Advance `{recommendation['recommended_band_label']}` as the primary commercial "
            "candidate; keep `ceiling` only as fallback and discard the premium band."
        ),
        "customer_first_reason": recommendation["why_this_band"],
        "candidates": candidates,
    }


def build_summary(results: dict, extracted: dict) -> dict:
    pricing = calculate_customer_equivalent_strike(results, extracted)
    multi_year_cppa_path = calculate_multi_year_cppa_path(results, extracted)
    financial_screening_view = calculate_financial_screening_view(results, extracted)
    strike_sensitivity_bands = calculate_cppa_sensitivity_bands(results, extracted)
    customer_first_recommendation = select_customer_first_recommendation(
        strike_sensitivity_bands
    )
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    storage = results.get("ElectricStorage", {})
    financial = results.get("Financial", {})
    owner_discount_rate = float(financial.get("owner_discount_rate_fraction") or 0.08)
    offtaker_discount_rate = float(
        financial.get("offtaker_discount_rate_fraction") or 0.10
    )
    customer_first_annual_path = calculate_customer_first_annual_path(
        results,
        extracted,
        strike_adjustment_fraction=float(
            customer_first_recommendation["relative_to_ceiling_fraction"]
        ),
    )
    customer_first_financial = summarize_customer_first_annual_path(
        customer_first_annual_path,
        owner_discount_rate,
        offtaker_discount_rate,
    )
    customer_first_recommendation_summary = {
        **customer_first_recommendation,
        "annual_generation_degradation_fraction": DEFAULT_ANNUAL_GENERATION_DEGRADATION_FRACTION,
        "annual_load_growth_fraction": DEFAULT_ANNUAL_LOAD_GROWTH_FRACTION,
        "unmatched_energy_price_fraction_of_evn": _merchant_price_fraction_of_evn(
            extracted
        ),
        "finance_grade_developer_revenue_npv_usd": customer_first_financial[
            "developer_revenue_npv_usd"
        ],
        "finance_grade_customer_savings_npv_usd": customer_first_financial[
            "customer_savings_npv_usd"
        ],
        "finance_grade_customer_premium_npv_usd": customer_first_financial[
            "customer_premium_npv_usd"
        ],
        "finance_grade_unmatched_renewable_npv_kwh": customer_first_financial[
            "unmatched_renewable_npv_kwh"
        ],
    }
    commercial_candidate_memo = build_commercial_candidate_memo(
        {
            "customer_first_recommendation": customer_first_recommendation_summary,
            "strike_sensitivity_bands": strike_sensitivity_bands,
        }
    )

    return {
        "status": results.get("status", "unknown"),
        "pricing": pricing,
        "multi_year_cppa_path": multi_year_cppa_path,
        "financial_screening_view": financial_screening_view,
        "strike_sensitivity_bands": strike_sensitivity_bands,
        "customer_first_recommendation": customer_first_recommendation_summary,
        "customer_first_annual_path": customer_first_annual_path,
        "commercial_candidate_memo": commercial_candidate_memo,
        "review_endpoint": {
            "question": (
                "Should the team advance the recommended customer-first band into commercial "
                "discussion, while holding parity as fallback and discarding the premium band?"
            ),
            "decision_artifact": (
                "Review commercial_candidate_memo together with customer_first_recommendation "
                "to confirm the advance / hold / discard shortlist."
            ),
            "suggested_review_bands": [
                customer_first_recommendation["recommended_band_label"]
            ],
        },
        "optimal_mix": {
            "pv_size_mw": float(pv.get("size_kw") or 0.0) / 1_000.0,
            "wind_size_mw": float(wind.get("size_kw") or 0.0) / 1_000.0,
            "bess_mw": float(storage.get("size_kw") or 0.0) / 1_000.0,
            "bess_mwh": float(storage.get("size_kwh") or 0.0) / 1_000.0,
        },
        "year_one_energy": {
            "pv_gwh": _annual_energy_kwh(pv) / 1_000_000.0,
            "wind_gwh": _annual_energy_kwh(wind) / 1_000_000.0,
            "renewable_delivered_gwh": pricing["renewable_delivered_kwh"] / 1_000_000.0,
            "grid_supplied_gwh": pricing["grid_supplied_kwh"] / 1_000_000.0,
        },
        "financial": {
            "npv_usd": float(financial.get("npv") or 0.0),
            "analysis_years": int(
                financial.get("analysis_years") or len(multi_year_cppa_path)
            ),
            "owner_discount_rate_fraction": owner_discount_rate,
            "offtaker_discount_rate_fraction": offtaker_discount_rate,
            "elec_cost_escalation_rate_fraction": float(
                financial.get("elec_cost_escalation_rate_fraction") or 0.05
            ),
            "year_one_operating_savings_before_tax_usd": float(
                financial.get("year_one_total_operating_cost_savings_before_tax") or 0.0
            ),
            "developer_revenue_npv_usd": _discounted_npv(
                financial_screening_view, "developer_revenue_usd", owner_discount_rate
            ),
            "offtaker_cost_npv_usd": _discounted_npv(
                financial_screening_view,
                "customer_total_cost_usd",
                offtaker_discount_rate,
            ),
            "benchmark_evn_cost_npv_usd": _discounted_npv(
                financial_screening_view,
                "benchmark_evn_cost_usd",
                offtaker_discount_rate,
            ),
            "offtaker_savings_npv_usd": _discounted_npv(
                financial_screening_view,
                "customer_savings_vs_evn_usd",
                offtaker_discount_rate,
            ),
            "customer_first_developer_revenue_npv_usd": customer_first_financial[
                "developer_revenue_npv_usd"
            ],
            "customer_first_offtaker_savings_npv_usd": customer_first_financial[
                "customer_savings_npv_usd"
            ],
            "customer_first_offtaker_premium_npv_usd": customer_first_financial[
                "customer_premium_npv_usd"
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Ninhsim REopt results under bundled CPPA target pricing"
    )
    parser.add_argument(
        "--reopt",
        required=True,
        help="Path to REopt results JSON",
    )
    parser.add_argument(
        "--extracted",
        default="data/interim/ninhsim/ninhsim_extracted_inputs.json",
        help="Path to Ninhsim extracted inputs JSON",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/ninhsim/2026-04-01_ninhsim-cppa-analysis.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    results = json.loads((REPO_ROOT / args.reopt).read_text(encoding="utf-8"))
    extracted = json.loads((REPO_ROOT / args.extracted).read_text(encoding="utf-8"))
    summary = build_summary(results, extracted)

    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Ninhsim CPPA analysis written to: {output_path}")
    print(f"  Status               : {summary['status']}")
    print(
        "  Max bundled strike   : "
        f"{summary['pricing']['max_cppa_strike_vnd_per_kwh']:.2f} VND/kWh "
        f"({summary['pricing']['max_cppa_strike_usd_per_kwh']:.6f} USD/kWh)"
    )
    print(
        "  Customer benchmark   : "
        f"{summary['pricing']['weighted_evn_benchmark_vnd_per_kwh']:.2f} VND/kWh"
    )
    print(
        "  Year-20 strike       : "
        f"{summary['multi_year_cppa_path'][-1]['cPPA_strike_vnd_per_kwh']:.2f} VND/kWh"
    )
    print(
        "  Developer NPV screen : "
        f"${summary['financial']['developer_revenue_npv_usd']:,.0f}"
    )
    print(
        "  Review endpoint      : "
        f"{summary['review_endpoint']['suggested_review_bands']}"
    )
    print(
        "  Customer-first band  : "
        f"{summary['customer_first_recommendation']['recommended_band_label']}"
    )
    print(
        "  Commercial memo      : "
        f"{summary['commercial_candidate_memo']['decision_summary']}"
    )


if __name__ == "__main__":
    main()
