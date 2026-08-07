"""Helpers for the Ninhsim DPPA Case 1 REopt plus fuller PySAM workflow."""

from __future__ import annotations

from reopt_pysam_vn.integration.assumptions import DEFAULT_TARGET_DEVELOPER_IRR_FRACTION
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

DEFAULT_EXPORT_NEGLIGIBLE_FRACTION = 0.005
DEFAULT_EQUITY_IRR_TARGET_FRACTION = 0.15


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


def load_reopt_delivery_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    storage = results.get("ElectricStorage", {})
    return _sum_series(
        pv.get("electric_to_load_series_kw", []),
        storage.get("storage_to_load_series_kw", []),
    )


def load_reopt_export_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    return _pad_to_8760(pv.get("electric_to_grid_series_kw", []))


def load_reopt_charge_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    return _pad_to_8760(pv.get("electric_to_storage_series_kw", []))


def load_reopt_curtailment_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    return _pad_to_8760(pv.get("electric_curtailed_series_kw", []))


def calculate_private_wire_strike_basis(
    results: dict, extracted: dict, scenario: dict
) -> dict:
    """Return the private-wire strike basis for a south ground-mounted PV+BESS case."""

    vn = load_vietnam_data()
    export_rules = vn.export_rules
    storage = results.get("ElectricStorage", {})
    pv = results.get("PV", {})
    delivery = load_reopt_delivery_profile(results)
    storage_delivery = _pad_to_8760(storage.get("storage_to_load_series_kw", []))

    pv_size_kw = float(pv.get("size_kw") or 0.0)
    battery_power_kw = float(storage.get("size_kw") or 0.0)
    battery_capacity_kwh = float(storage.get("size_kwh") or 0.0)
    battery_duration_hours = (
        battery_capacity_kwh / battery_power_kw if battery_power_kw else 0.0
    )
    battery_power_fraction = battery_power_kw / pv_size_kw if pv_size_kw else 0.0
    delivered_kwh = sum(max(0.0, value) for value in delivery)
    stored_output_kwh = sum(max(0.0, value) for value in storage_delivery)
    stored_output_fraction = stored_output_kwh / delivered_kwh if delivered_kwh else 0.0

    thresholds = export_rules["bess_incentive_requirements"]
    qualifies = (
        battery_power_fraction + 1e-9
        >= float(thresholds["min_storage_capacity_fraction"])
        and battery_duration_hours + 1e-9
        >= float(thresholds["min_storage_duration_hours"])
        and stored_output_fraction + 1e-9
        >= float(thresholds["min_stored_output_fraction"])
    )

    region = extracted.get("site", {}).get("region", "south")
    if qualifies:
        strike_vnd = float(
            export_rules["dppa_ceiling_tariffs_vnd_per_kwh"]["solar_ground_with_bess"][
                region
            ]
        )
        strike_usd = float(
            export_rules["dppa_ceiling_tariffs_usd_per_kwh"]["solar_ground_with_bess"][
                region
            ]
        )
        tariff_key = "solar_ground_with_bess"
    else:
        strike_vnd = float(
            export_rules["dppa_ceiling_tariffs_vnd_per_kwh"]["solar_ground_no_storage"][
                region
            ]
        )
        strike_usd = float(
            export_rules["dppa_ceiling_tariffs_usd_per_kwh"]["solar_ground_no_storage"][
                region
            ]
        )
        tariff_key = "solar_ground_no_storage"

    return {
        "contract_type": scenario.get("_meta", {}).get("contract_type", "private_wire"),
        "private_wire_tariff_key": tariff_key,
        "qualifies_for_bess_private_wire_ceiling": qualifies,
        "year_one_private_wire_strike_vnd_per_kwh": strike_vnd,
        "year_one_private_wire_strike_usd_per_kwh": strike_usd,
        "battery_power_fraction_of_pv": battery_power_fraction,
        "battery_duration_hours": battery_duration_hours,
        "stored_output_fraction_of_delivered_energy": stored_output_fraction,
    }


def build_dppa_case_1_reopt_summary(
    results: dict, extracted: dict, scenario: dict
) -> dict:
    delivery = load_reopt_delivery_profile(results)
    exports = load_reopt_export_profile(results)
    charge = load_reopt_charge_profile(results)
    curtailed = load_reopt_curtailment_profile(results)
    grid = _pad_to_8760(
        results.get("ElectricUtility", {}).get("electric_to_load_series_kw", [])
    )
    total_load_kwh = sum(
        max(0.0, value) for value in _pad_to_8760(extracted["loads_kw"])
    )
    delivered_kwh = sum(max(0.0, value) for value in delivery)
    export_kwh = sum(max(0.0, value) for value in exports)
    charge_kwh = sum(max(0.0, value) for value in charge)
    curtailed_kwh = sum(max(0.0, value) for value in curtailed)
    grid_kwh = sum(max(0.0, value) for value in grid)
    pv_size_kw = float(results.get("PV", {}).get("size_kw") or 0.0)
    battery_power_kw = float(results.get("ElectricStorage", {}).get("size_kw") or 0.0)
    battery_capacity_kwh = float(
        results.get("ElectricStorage", {}).get("size_kwh") or 0.0
    )
    duration_hours = (
        battery_capacity_kwh / battery_power_kw if battery_power_kw else 0.0
    )
    strike = calculate_private_wire_strike_basis(results, extracted, scenario)
    export_fraction_of_generation = (
        export_kwh / _annual_energy_kwh(results.get("PV", {}))
        if _annual_energy_kwh(results.get("PV", {}))
        else 0.0
    )

    return {
        "model": "Ninhsim DPPA Case 1 REopt Summary",
        "status": results.get("status", "unknown"),
        "site_load_basis": {
            "annual_load_gwh": float(extracted["benchmark"]["annual_load_gwh"]),
            "customer_type": extracted["site"]["customer_type"],
            "voltage_level": extracted["site"]["voltage_level"],
            "region": extracted["site"]["region"],
        },
        "optimal_mix": {
            "pv_size_mw": pv_size_kw / 1_000.0,
            "bess_mw": battery_power_kw / 1_000.0,
            "bess_mwh": battery_capacity_kwh / 1_000.0,
            "bess_duration_hours": duration_hours,
        },
        "energy_summary": {
            "pv_gwh": _annual_energy_kwh(results.get("PV", {})) / 1_000_000.0,
            "renewable_delivered_kwh": delivered_kwh,
            "grid_supplied_kwh": grid_kwh,
            "exported_renewable_kwh": export_kwh,
            "curtailed_renewable_kwh": curtailed_kwh,
            "renewable_charged_to_battery_kwh": charge_kwh,
            "total_load_kwh": total_load_kwh,
            "export_fraction_of_generation": export_fraction_of_generation,
        },
        "design_checks": {
            "battery_duration_exactly_two_hours": abs(duration_hours - 2.0) <= 1e-6,
            "export_is_negligible": export_fraction_of_generation
            <= DEFAULT_EXPORT_NEGLIGIBLE_FRACTION,
            "solar_only_battery_charging_requested": not bool(
                scenario.get("ElectricStorage", {}).get("can_grid_charge", False)
            ),
        },
        "private_wire_strike": strike,
        "financial": {
            "reopt_npv_usd": float(results.get("Financial", {}).get("npv") or 0.0),
            "analysis_years": int(
                results.get("Financial", {}).get("analysis_years") or 20
            ),
            "owner_discount_rate_fraction": _financial_value(
                results, "owner_discount_rate_fraction", 0.08
            ),
            "offtaker_discount_rate_fraction": _financial_value(
                results, "offtaker_discount_rate_fraction", 0.10
            ),
            "target_project_irr_fraction": DEFAULT_TARGET_DEVELOPER_IRR_FRACTION,
            "target_equity_irr_fraction": DEFAULT_EQUITY_IRR_TARGET_FRACTION,
        },
        "warnings": [],
    }


def build_dppa_case_1_comparison(reopt_summary: dict, pysam_results: dict) -> dict:
    reopt_energy = reopt_summary["energy_summary"]
    pysam_energy = pysam_results.get("energy_summary", {})
    return {
        "model": "Ninhsim DPPA Case 1 REopt vs PySAM Comparison",
        "energy_alignment": {
            "reopt_export_kwh": float(reopt_energy["exported_renewable_kwh"]),
            "pysam_export_kwh": float(pysam_energy.get("annual_export_kwh") or 0.0),
            "pysam_export_delta_kwh": float(
                pysam_energy.get("annual_export_kwh") or 0.0
            )
            - float(reopt_energy["exported_renewable_kwh"]),
            "reopt_delivered_kwh": float(reopt_energy["renewable_delivered_kwh"]),
            "pysam_delivered_kwh": float(
                pysam_energy.get("annual_matched_load_kwh") or 0.0
            ),
            "delivered_delta_kwh": float(
                pysam_energy.get("annual_matched_load_kwh") or 0.0
            )
            - float(reopt_energy["renewable_delivered_kwh"]),
            "reopt_curtailment_kwh": float(reopt_energy["curtailed_renewable_kwh"]),
            "pysam_curtailment_kwh": float(
                pysam_energy.get("annual_estimated_curtailment_kwh") or 0.0
            ),
        },
        "financial_alignment": {
            "project_irr_fraction": pysam_results.get("outputs", {}).get(
                "project_return_aftertax_irr_fraction"
            ),
            "equity_irr_fraction": pysam_results.get("outputs", {}).get(
                "equity_irr_fraction"
            ),
            "project_npv_usd": pysam_results.get("outputs", {}).get(
                "project_return_aftertax_npv_usd"
            ),
            "reopt_npv_usd": reopt_summary.get("financial", {}).get("reopt_npv_usd"),
        },
    }


def build_dppa_case_1_placeholder_pysam_results(reopt_summary: dict) -> dict:
    """Return a canonical placeholder when the REopt design has no battery to simulate."""

    strike = reopt_summary["private_wire_strike"]
    mix = reopt_summary["optimal_mix"]
    energy = reopt_summary["energy_summary"]
    return {
        "model": "PySAM PVWatts Battery Single Owner",
        "status": "skipped",
        "case": {
            "source_case": "ninhsim_dppa_case_1",
            "contract_type": strike["contract_type"],
            "year_one_private_wire_strike_vnd_per_kwh": strike[
                "year_one_private_wire_strike_vnd_per_kwh"
            ],
            "skip_reason": "reopt_selected_zero_battery",
        },
        "outputs": {
            "project_return_aftertax_npv_usd": None,
            "project_return_aftertax_irr_fraction": None,
            "project_return_pretax_irr_fraction": None,
            "size_of_debt_usd": None,
            "debt_fraction": None,
            "min_dscr": None,
            "npv_ppa_revenue_usd": None,
            "equity_irr_fraction": None,
            "size_of_equity_usd": None,
        },
        "energy_summary": {
            "annual_pv_ac_energy_kwh": float(energy["pv_gwh"]) * 1_000_000.0,
            "annual_matched_load_kwh": float(energy["renewable_delivered_kwh"]),
            "annual_export_kwh": float(energy["exported_renewable_kwh"]),
            "annual_battery_charge_from_system_kwh": 0.0,
            "annual_battery_charge_from_grid_kwh": 0.0,
            "annual_battery_discharge_to_load_kwh": 0.0,
            "annual_estimated_curtailment_kwh": float(
                energy["curtailed_renewable_kwh"]
            ),
        },
        "annual_cashflows": [],
        "notes": {
            "phase_scope": "PySAM battery execution was skipped because the REopt DPPA Case 1 solve selected zero battery under the current minimum-capex objective.",
            "skip_note": (
                f"REopt returned PV {mix['pv_size_mw']:.3f} MW with zero battery, so the fuller battery workflow cannot run without a bounded resize or stricter storage requirement."
            ),
        },
    }


def build_dppa_case_1_combined_decision(
    reopt_summary: dict, pysam_results: dict, comparison: dict
) -> dict:
    outputs = pysam_results.get("outputs", {})
    project_irr = outputs.get("project_return_aftertax_irr_fraction")
    equity_irr = outputs.get("equity_irr_fraction")
    project_target = reopt_summary["financial"]["target_project_irr_fraction"]
    equity_target = reopt_summary["financial"]["target_equity_irr_fraction"]
    export_ok = bool(reopt_summary["design_checks"]["export_is_negligible"])
    project_ok = project_irr is not None and float(project_irr) >= float(project_target)
    equity_ok = equity_irr is not None and float(equity_irr) >= float(equity_target)
    warnings = list(reopt_summary.get("warnings", []))
    skip_reason = pysam_results.get("case", {}).get("skip_reason")
    if skip_reason == "reopt_selected_zero_battery":
        warnings.append(
            "REopt selected zero battery under the current DPPA Case 1 objective, so the fuller PySAM battery run was skipped and the case should be resized or the storage requirement tightened."
        )
    return {
        "model": "Ninhsim DPPA Case 1 Combined Decision",
        "status": "ok" if pysam_results.get("status") == "ok" else "warning",
        "site_and_tariff_basis": {
            **reopt_summary["site_load_basis"],
            **reopt_summary["private_wire_strike"],
        },
        "reopt_summary": reopt_summary,
        "pysam_summary": {
            "model": pysam_results.get("model"),
            "outputs": outputs,
            "energy_summary": pysam_results.get("energy_summary", {}),
        },
        "comparison": comparison,
        "decision": {
            "export_design_passes": export_ok,
            "financeable_at_default_project_irr": project_ok,
            "financeable_at_default_equity_irr": equity_ok,
            "recommended_position": (
                "advance_for_review"
                if export_ok and project_ok and equity_ok
                else "needs_reprice_or_resize"
            ),
        },
        "warnings": warnings,
    }
