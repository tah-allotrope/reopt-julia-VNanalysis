"""Helpers for the Ninhsim solar-plus-storage 60% DPPA workflow."""

from __future__ import annotations

from reopt_pysam_vn.integration.assumptions import DEFAULT_TARGET_DEVELOPER_IRR_FRACTION
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

DEFAULT_REQUESTED_TARGET_FRACTION = 0.60
DEFAULT_TARGET_STEP_DOWN = 0.025
DEFAULT_MINIMUM_TARGET_FRACTION = 0.50
DEFAULT_STRIKE_DISCOUNT_FRACTION = 0.05
DEFAULT_ANNUAL_GENERATION_DEGRADATION_FRACTION = 0.005
DEFAULT_ANNUAL_LOAD_GROWTH_FRACTION = 0.01


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) >= 8760:
        return list(series[:8760])
    return list(series) + [0.0] * (8760 - len(series))


def _sum_series(*series_list: list[float]) -> list[float]:
    padded = [_pad_to_8760(series) for series in series_list]
    return [sum(values) for values in zip(*padded)]


def _annual_energy_kwh(tech_results: dict) -> float:
    return float(
        tech_results.get("year_one_energy_produced_kwh")
        or tech_results.get("annual_energy_produced_kwh")
        or 0.0
    )


def _financial_value(results: dict, key: str, default: float) -> float:
    return float(results.get("Financial", {}).get(key) or default)


def _clean_small(value: float, tolerance: float = 1e-6) -> float:
    return 0.0 if abs(value) <= tolerance else value


def _discounted_npv(entries: list[dict], key: str, discount_rate: float) -> float:
    npv = 0.0
    for entry in entries:
        year = int(entry["year"])
        npv += float(entry[key]) / ((1.0 + discount_rate) ** year)
    return _clean_small(npv)


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


def build_target_fraction_candidates(
    requested_target_fraction: float,
    *,
    minimum_target_fraction: float = DEFAULT_MINIMUM_TARGET_FRACTION,
    step_down_fraction: float = DEFAULT_TARGET_STEP_DOWN,
) -> list[float]:
    requested = float(requested_target_fraction)
    minimum = float(minimum_target_fraction)
    step = float(step_down_fraction)
    if step <= 0.0:
        raise ValueError("step_down_fraction must be positive")
    if minimum > requested:
        raise ValueError("minimum_target_fraction must be <= requested_target_fraction")

    values: list[float] = []
    current = requested
    while current >= minimum - 1e-9:
        values.append(round(current, 6))
        current -= step
    return values


def calculate_ninhsim_fixed_strike(
    results: dict,
    extracted: dict,
    *,
    strike_discount_fraction: float = DEFAULT_STRIKE_DISCOUNT_FRACTION,
) -> dict:
    weighted_vnd = float(extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"])
    weighted_usd = float(extracted["benchmark"]["weighted_evn_price_usd_per_kwh"])
    merchant_usd = float(
        extracted["benchmark"].get("wholesale_rate_usd_per_kwh") or 0.0
    )
    escalation = _financial_value(results, "elec_cost_escalation_rate_fraction", 0.05)
    discount = float(strike_discount_fraction)
    merchant_fraction = merchant_usd / weighted_usd if weighted_usd else 0.0
    return {
        "weighted_evn_price_vnd_per_kwh": weighted_vnd,
        "weighted_evn_price_usd_per_kwh": weighted_usd,
        "strike_discount_fraction": discount,
        "year_one_strike_vnd_per_kwh": weighted_vnd * (1.0 - discount),
        "year_one_strike_usd_per_kwh": weighted_usd * (1.0 - discount),
        "merchant_price_fraction_of_evn": merchant_fraction,
        "merchant_price_vnd_per_kwh": float(
            extracted["benchmark"].get("wholesale_rate_vnd_per_kwh") or 0.0
        ),
        "merchant_price_usd_per_kwh": merchant_usd,
        "escalation_rate_fraction": escalation,
    }


def calculate_ninhsim_coverage_summary(
    results: dict,
    extracted: dict,
    *,
    target_fraction: float = DEFAULT_REQUESTED_TARGET_FRACTION,
    enforced_target_fraction: float | None = None,
) -> dict:
    renewable_delivery = load_reopt_delivery_profile(results)
    renewable_export = load_renewable_export_profile(results)
    grid_supply = load_grid_supply_profile(results)
    total_load_kwh = sum(
        max(0.0, value) for value in _pad_to_8760(extracted["loads_kw"])
    )
    renewable_delivered_kwh = sum(max(0.0, value) for value in renewable_delivery)
    exported_renewable_kwh = sum(max(0.0, value) for value in renewable_export)
    grid_supplied_kwh = sum(max(0.0, value) for value in grid_supply)
    sold_renewable_kwh = renewable_delivered_kwh + exported_renewable_kwh
    achieved_fraction = (
        renewable_delivered_kwh / total_load_kwh if total_load_kwh else 0.0
    )
    enforced = float(
        enforced_target_fraction
        if enforced_target_fraction is not None
        else target_fraction
    )
    return {
        "requested_target_fraction": float(target_fraction),
        "enforced_target_fraction": enforced,
        "renewable_delivered_kwh": renewable_delivered_kwh,
        "exported_renewable_kwh": exported_renewable_kwh,
        "sold_renewable_kwh": sold_renewable_kwh,
        "grid_supplied_kwh": grid_supplied_kwh,
        "total_load_kwh": total_load_kwh,
        "achieved_delivered_fraction_of_load": achieved_fraction,
        "gap_to_requested_target_fraction": achieved_fraction - float(target_fraction),
        "gap_to_enforced_target_fraction": achieved_fraction - enforced,
        "meets_requested_target": achieved_fraction + 1e-9 >= float(target_fraction),
        "meets_enforced_target": achieved_fraction + 1e-9 >= enforced,
    }


def calculate_ninhsim_developer_revenue_path(
    results: dict,
    extracted: dict,
    fixed_strike: dict,
    *,
    analysis_years: int | None = None,
    annual_generation_degradation_fraction: float = DEFAULT_ANNUAL_GENERATION_DEGRADATION_FRACTION,
    annual_load_growth_fraction: float = DEFAULT_ANNUAL_LOAD_GROWTH_FRACTION,
) -> list[dict]:
    years = int(analysis_years or _financial_value(results, "analysis_years", 20))
    exchange_rate = float(extracted["benchmark"]["exchange_rate_vnd_per_usd"])
    load_series_kw = _pad_to_8760(extracted["loads_kw"])
    evn_rates_usd = _pad_to_8760(
        extracted["evn_tariff"]["tou_energy_rates_usd_per_kwh"]
    )
    renewable_available_kw = _sum_series(
        load_reopt_delivery_profile(results),
        load_renewable_export_profile(results),
    )

    path = []
    for year in range(1, years + 1):
        generation_factor = (1.0 - annual_generation_degradation_fraction) ** (year - 1)
        load_factor = (1.0 + annual_load_growth_fraction) ** (year - 1)
        price_factor = (1.0 + float(fixed_strike["escalation_rate_fraction"])) ** (
            year - 1
        )
        strike_usd = float(fixed_strike["year_one_strike_usd_per_kwh"]) * price_factor
        strike_vnd = float(fixed_strike["year_one_strike_vnd_per_kwh"]) * price_factor
        merchant_fraction = float(fixed_strike["merchant_price_fraction_of_evn"])

        available_kw = [value * generation_factor for value in renewable_available_kw]
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
        merchant_sold_kwh = sum(unmatched_kw)
        grid_supplied_kwh = sum(residual_grid_kw)
        total_load_kwh = sum(load_kw)
        total_sold_kwh = renewable_delivered_kwh + merchant_sold_kwh
        customer_revenue_usd = renewable_delivered_kwh * strike_usd
        merchant_revenue_usd = sum(
            unmatched * rate for unmatched, rate in zip(unmatched_kw, merchant_rates)
        )
        developer_revenue_usd = customer_revenue_usd + merchant_revenue_usd
        residual_grid_cost_usd = sum(
            grid_kw * rate for grid_kw, rate in zip(residual_grid_kw, scaled_evn_rates)
        )
        customer_total_cost_usd = customer_revenue_usd + residual_grid_cost_usd
        benchmark_evn_cost_usd = sum(
            load * rate for load, rate in zip(load_kw, scaled_evn_rates)
        )
        realized_price_usd = (
            developer_revenue_usd / total_sold_kwh if total_sold_kwh else 0.0
        )

        path.append(
            {
                "year": year,
                "strike_usd_per_kwh": strike_usd,
                "strike_vnd_per_kwh": strike_vnd,
                "merchant_price_usd_per_kwh": (
                    merchant_revenue_usd / merchant_sold_kwh
                    if merchant_sold_kwh
                    else float(fixed_strike["merchant_price_usd_per_kwh"])
                    * price_factor
                ),
                "merchant_price_vnd_per_kwh": (
                    merchant_revenue_usd / merchant_sold_kwh * exchange_rate
                    if merchant_sold_kwh
                    else float(fixed_strike["merchant_price_vnd_per_kwh"])
                    * price_factor
                ),
                "renewable_delivered_kwh": renewable_delivered_kwh,
                "merchant_sold_kwh": merchant_sold_kwh,
                "grid_supplied_kwh": grid_supplied_kwh,
                "total_load_kwh": total_load_kwh,
                "total_sold_kwh": total_sold_kwh,
                "developer_revenue_usd": developer_revenue_usd,
                "developer_revenue_from_customer_usd": customer_revenue_usd,
                "developer_revenue_from_merchant_usd": merchant_revenue_usd,
                "realized_blended_price_usd_per_kwh": realized_price_usd,
                "realized_blended_price_vnd_per_kwh": realized_price_usd
                * exchange_rate,
                "customer_total_cost_usd": customer_total_cost_usd,
                "benchmark_evn_cost_usd": benchmark_evn_cost_usd,
                "customer_savings_vs_evn_usd": max(
                    0.0, _clean_small(benchmark_evn_cost_usd - customer_total_cost_usd)
                ),
                "customer_premium_vs_evn_usd": max(
                    0.0, customer_total_cost_usd - benchmark_evn_cost_usd
                ),
            }
        )
    return path


def build_ninhsim_60pct_analysis(
    results: dict,
    extracted: dict,
    scenario: dict,
    *,
    requested_target_fraction: float = DEFAULT_REQUESTED_TARGET_FRACTION,
    enforced_target_fraction: float | None = None,
) -> dict:
    requested = float(
        scenario.get("_meta", {}).get(
            "requested_renewable_delivered_fraction_of_load", requested_target_fraction
        )
    )
    enforced = float(
        enforced_target_fraction
        if enforced_target_fraction is not None
        else scenario.get("Site", {}).get(
            "renewable_electricity_min_fraction", requested
        )
    )
    fixed_strike = calculate_ninhsim_fixed_strike(results, extracted)
    coverage_summary = calculate_ninhsim_coverage_summary(
        results,
        extracted,
        target_fraction=requested,
        enforced_target_fraction=enforced,
    )
    developer_revenue_path = calculate_ninhsim_developer_revenue_path(
        results,
        extracted,
        fixed_strike,
    )

    financial = results.get("Financial", {})
    owner_discount_rate = _financial_value(
        results, "owner_discount_rate_fraction", 0.08
    )
    offtaker_discount_rate = _financial_value(
        results, "offtaker_discount_rate_fraction", 0.10
    )
    year_one = developer_revenue_path[0]
    warnings: list[str] = []
    if not coverage_summary["meets_requested_target"]:
        warnings.append(
            "The requested 60% delivered-energy target was not achieved; the workflow reports the nearest feasible solve that cleared the enforced threshold instead of forcing an infeasible design."
        )
    if float(results.get("Wind", {}).get("size_kw") or 0.0) > 0.0:
        warnings.append(
            "Wind capacity is non-zero in the solved result even though the case-study workflow is intended to be solar-plus-storage only."
        )

    return {
        "model": "Ninhsim Solar Storage 60% Analysis",
        "status": results.get("status", "unknown"),
        "site_load_basis": {
            "annual_load_gwh": float(extracted["benchmark"]["annual_load_gwh"]),
            "customer_type": extracted["site"]["customer_type"],
            "voltage_level": extracted["site"]["voltage_level"],
            "region": extracted["site"]["region"],
        },
        "fixed_strike": fixed_strike,
        "coverage_summary": coverage_summary,
        "developer_revenue_path": developer_revenue_path,
        "year_one_financial_screen": {
            **year_one,
            "developer_revenue_npv_usd": _discounted_npv(
                developer_revenue_path,
                "developer_revenue_usd",
                owner_discount_rate,
            ),
            "customer_savings_npv_usd": _discounted_npv(
                developer_revenue_path,
                "customer_savings_vs_evn_usd",
                offtaker_discount_rate,
            ),
            "customer_premium_npv_usd": _discounted_npv(
                developer_revenue_path,
                "customer_premium_vs_evn_usd",
                offtaker_discount_rate,
            ),
        },
        "optimal_mix": {
            "pv_size_mw": float(results.get("PV", {}).get("size_kw") or 0.0) / 1_000.0,
            "wind_size_mw": float(results.get("Wind", {}).get("size_kw") or 0.0)
            / 1_000.0,
            "bess_mw": float(results.get("ElectricStorage", {}).get("size_kw") or 0.0)
            / 1_000.0,
            "bess_mwh": float(results.get("ElectricStorage", {}).get("size_kwh") or 0.0)
            / 1_000.0,
        },
        "year_one_energy": {
            "pv_gwh": _annual_energy_kwh(results.get("PV", {})) / 1_000_000.0,
            "wind_gwh": _annual_energy_kwh(results.get("Wind", {})) / 1_000_000.0,
            "renewable_delivered_gwh": coverage_summary["renewable_delivered_kwh"]
            / 1_000_000.0,
            "exported_renewable_gwh": coverage_summary["exported_renewable_kwh"]
            / 1_000_000.0,
            "sold_renewable_gwh": coverage_summary["sold_renewable_kwh"] / 1_000_000.0,
            "grid_supplied_gwh": coverage_summary["grid_supplied_kwh"] / 1_000_000.0,
        },
        "financial": {
            "reopt_npv_usd": float(financial.get("npv") or 0.0),
            "analysis_years": int(
                financial.get("analysis_years") or len(developer_revenue_path)
            ),
            "owner_discount_rate_fraction": owner_discount_rate,
            "offtaker_discount_rate_fraction": offtaker_discount_rate,
            "target_project_irr_fraction": DEFAULT_TARGET_DEVELOPER_IRR_FRACTION,
        },
        "assumptions": {
            "annual_generation_degradation_fraction": DEFAULT_ANNUAL_GENERATION_DEGRADATION_FRACTION,
            "annual_load_growth_fraction": DEFAULT_ANNUAL_LOAD_GROWTH_FRACTION,
            "merchant_price_fraction_of_evn": fixed_strike[
                "merchant_price_fraction_of_evn"
            ],
            "pysam_revenue_modeling_note": "PySAM Single Owner is fed a blended realized revenue price across customer-served and merchant-sold energy because the local wrapper supports one escalated price stream.",
        },
        "warnings": warnings,
    }


def build_combined_decision_artifact(
    analysis: dict,
    pysam_results: dict,
    *,
    target_project_irr_fraction: float = DEFAULT_TARGET_DEVELOPER_IRR_FRACTION,
) -> dict:
    coverage = analysis["coverage_summary"]
    outputs = pysam_results.get("outputs", {})
    project_irr = outputs.get("project_return_aftertax_irr_fraction")
    financeable = project_irr is not None and float(project_irr) >= float(
        target_project_irr_fraction
    )
    return {
        "model": "Ninhsim Solar Storage 60% Combined Decision",
        "status": "ok" if pysam_results.get("status") == "ok" else "warning",
        "site_and_tariff_basis": {
            **analysis["site_load_basis"],
            **analysis["fixed_strike"],
        },
        "reopt_summary": {
            "status": analysis["status"],
            "coverage_summary": coverage,
            "optimal_mix": analysis["optimal_mix"],
            "year_one_energy": analysis["year_one_energy"],
        },
        "developer_finance_summary": {
            "project_return_aftertax_npv_usd": outputs.get(
                "project_return_aftertax_npv_usd"
            ),
            "project_return_aftertax_irr_fraction": project_irr,
            "project_return_pretax_irr_fraction": outputs.get(
                "project_return_pretax_irr_fraction"
            ),
            "size_of_debt_usd": outputs.get("size_of_debt_usd"),
            "min_dscr": outputs.get("min_dscr"),
            "npv_ppa_revenue_usd": outputs.get("npv_ppa_revenue_usd"),
            "year_one_total_revenue_usd": (
                pysam_results.get("annual_cashflows", [{}])[0].get("total_revenue_usd")
                if pysam_results.get("annual_cashflows")
                else None
            ),
        },
        "decision": {
            "requested_60pct_achieved": bool(coverage["meets_requested_target"]),
            "operationally_feasible": bool(coverage["meets_enforced_target"]),
            "financeable_at_default_target_irr": financeable,
            "target_project_irr_fraction": float(target_project_irr_fraction),
            "recommended_position": (
                "advance_for_review"
                if coverage["meets_enforced_target"] and financeable
                else "needs_reprice_or_scope_change"
            ),
        },
        "warnings": list(analysis.get("warnings", [])),
        "notes": {
            "merchant_sale_treatment": "Excess renewable energy is valued at a rough spot-market proxy based on the repo wholesale-to-weighted-EVN price ratio.",
            "pysam_revenue_modeling_note": analysis["assumptions"][
                "pysam_revenue_modeling_note"
            ],
        },
    }


def build_default_vn_exchange_rate() -> float:
    return float(load_vietnam_data().exchange_rate)
