"""Helpers for Ninhsim DPPA Case 2 definition, physical summary, and settlement."""

from __future__ import annotations

from dataclasses import replace

from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.reopt.preprocess import apply_vietnam_defaults, load_vietnam_data

DEFAULT_STRIKE_DISCOUNT_FRACTION = 0.05
DEFAULT_STRIKE_ESCALATION_FRACTION = 0.05
DEFAULT_DPPA_ADDER_VND_PER_KWH = 523.34
DEFAULT_KPP_FACTOR = 1.027263
DEFAULT_SETTLEMENT_QUANTITY_RULE = "min_load_and_contracted_generation"
DEFAULT_EXCESS_GENERATION_TREATMENT = "excluded_from_buyer_settlement"
DEFAULT_CONTRACT_STRUCTURE = "synthetic_financial_dppa"
DEFAULT_MARKET_PRICE_SOURCE_PRIORITY = [
    "actual_hourly_cfmp_or_fmp_series",
    "repo_proxy_hourly_series",
]


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) >= 8760:
        return [float(value) for value in series[:8760]]
    return [float(value) for value in series] + [0.0] * (8760 - len(series))


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


def _proxy_market_fraction(extracted: dict) -> float:
    weighted = float(extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"])
    wholesale = float(extracted["benchmark"].get("wholesale_rate_vnd_per_kwh") or 0.0)
    return wholesale / weighted if weighted else 0.0


def _normalize_market_series_vnd_per_kwh(
    series: list[float],
) -> tuple[list[float], str]:
    if not series:
        raise ValueError("Market reference series is empty")
    values = [float(value) for value in series]
    maximum = max(values)
    minimum = min(values)
    if maximum > 10_000.0:
        return [
            value / 1_000.0 for value in values
        ], "vnd_per_mwh_converted_to_vnd_per_kwh"
    if minimum >= 0.0:
        return values, "vnd_per_kwh_as_extracted"
    raise ValueError(
        f"Unexpected market reference value range: min={minimum}, max={maximum}"
    )


def _load_series(values: list[float]) -> list[float]:
    return [float(value) for value in values]


def _load_retail_series(extracted: dict) -> list[float]:
    return _load_series(extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"])


def _buyer_passes_benchmark(benchmark: dict) -> bool:
    return bool(benchmark["decision"]["buyer_savings_positive"])


def _developer_passes_target(result: dict | None, target_irr_fraction: float) -> bool:
    if result is None:
        return False
    irr = result.get("outputs", {}).get("project_return_aftertax_irr_fraction")
    return irr is not None and float(irr) >= float(target_irr_fraction)


def _copy_settlement_inputs_with_overrides(
    settlement_inputs: dict,
    *,
    strike_price_vnd_per_kwh: float | None = None,
    dppa_adder_vnd_per_kwh: float | None = None,
    kpp_factor: float | None = None,
    excess_generation_treatment: str | None = None,
) -> dict:
    updated = dict(settlement_inputs)
    if strike_price_vnd_per_kwh is not None:
        updated["strike_price_vnd_per_kwh"] = float(strike_price_vnd_per_kwh)
    if dppa_adder_vnd_per_kwh is not None:
        updated["dppa_adder_vnd_per_kwh"] = float(dppa_adder_vnd_per_kwh)
    if kpp_factor is not None:
        updated["kpp_factor"] = float(kpp_factor)
    if excess_generation_treatment is not None:
        updated["excess_generation_treatment"] = excess_generation_treatment
    return updated


def _build_developer_case_result(
    developer_base_inputs,
    *,
    strike_price_vnd_per_kwh: float,
    exchange_rate_vnd_per_usd: float,
    developer_runner,
):
    if developer_base_inputs is None:
        return None
    target_irr = float(developer_base_inputs.target_irr_fraction)
    candidate_inputs = replace(
        developer_base_inputs,
        ppa_price_input_usd_per_kwh=float(strike_price_vnd_per_kwh)
        / float(exchange_rate_vnd_per_usd),
        metadata={
            **dict(developer_base_inputs.metadata),
            "year_one_ppa_price_vnd_per_kwh": float(strike_price_vnd_per_kwh),
            "year_one_ppa_price_usd_per_kwh": float(strike_price_vnd_per_kwh)
            / float(exchange_rate_vnd_per_usd),
        },
    )
    result = developer_runner(candidate_inputs)
    return {
        "result": result,
        "target_irr_fraction": target_irr,
        "passes_target": _developer_passes_target(result, target_irr),
    }


def _pad_to_length(series: list[float], length: int) -> list[float]:
    values = [float(value) for value in series[:length]]
    if len(values) < length:
        values.extend([0.0] * (length - len(values)))
    return values


def _sum_series_to_length(length: int, *series_list: list[float]) -> list[float]:
    padded = [_pad_to_length(series, length) for series in series_list]
    return [sum(values) for values in zip(*padded)]


def _load_reopt_delivery_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    storage = results.get("ElectricStorage", {})
    return _sum_series(
        pv.get("electric_to_load_series_kw", []),
        wind.get("electric_to_load_series_kw", []),
        storage.get("storage_to_load_series_kw", []),
    )


def _load_reopt_export_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    return _sum_series(
        pv.get("electric_to_grid_series_kw", []),
        wind.get("electric_to_grid_series_kw", []),
    )


def _load_reopt_charge_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    return _sum_series(
        pv.get("electric_to_storage_series_kw", []),
        wind.get("electric_to_storage_series_kw", []),
    )


def _load_reopt_curtailment_profile(results: dict) -> list[float]:
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    return _sum_series(
        pv.get("electric_curtailed_series_kw", []),
        wind.get("electric_curtailed_series_kw", []),
    )


def _load_reopt_grid_supply_profile(results: dict) -> list[float]:
    utility = results.get("ElectricUtility", {})
    return _pad_to_8760(utility.get("electric_to_load_series_kw", []))


def _strike_vnd_per_kwh(
    extracted: dict,
    strike_discount_fraction: float = DEFAULT_STRIKE_DISCOUNT_FRACTION,
) -> float:
    weighted_vnd = float(extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"])
    return weighted_vnd * (1.0 - float(strike_discount_fraction))


def _strike_usd_per_kwh(
    extracted: dict,
    strike_discount_fraction: float = DEFAULT_STRIKE_DISCOUNT_FRACTION,
) -> float:
    weighted_usd = float(extracted["benchmark"]["weighted_evn_price_usd_per_kwh"])
    return weighted_usd * (1.0 - float(strike_discount_fraction))


def build_dppa_case_2_phase_a_definition(extracted: dict) -> dict:
    strike_vnd = _strike_vnd_per_kwh(extracted)
    strike_usd = _strike_usd_per_kwh(extracted)
    return {
        "model": "Ninhsim DPPA Case 2 Phase A Definition",
        "status": "agreed_user_reviewed",
        "case_identity": {
            "scenario_family": "DPPA Case 2",
            "slug": "ninhsim_dppa_case_2",
            "contract_structure": DEFAULT_CONTRACT_STRUCTURE,
            "project_basis": "ninhsim_8760_load_reuse",
            "customer_priority": "customer_best_interest_first",
            "main_business_questions": [
                "buyer_all_in_cost_vs_evn",
                "developer_finance_at_negotiated_strike",
                "contract_shape_risk_minimization",
            ],
        },
        "site_load_basis": {
            "site": dict(extracted["site"]),
            "annual_load_kwh": float(extracted["benchmark"]["annual_load_kwh"]),
            "annual_load_gwh": float(extracted["benchmark"]["annual_load_gwh"]),
            "load_profile_source": extracted.get("source_load_path"),
            "tariff_source": extracted.get("source_tariff_path"),
        },
        "strike_basis": {
            "anchor": "weighted_evn_tariff_discount",
            "strike_discount_fraction": float(DEFAULT_STRIKE_DISCOUNT_FRACTION),
            "weighted_evn_price_vnd_per_kwh": float(
                extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"]
            ),
            "weighted_evn_price_usd_per_kwh": float(
                extracted["benchmark"]["weighted_evn_price_usd_per_kwh"]
            ),
            "year_one_strike_vnd_per_kwh": strike_vnd,
            "year_one_strike_usd_per_kwh": strike_usd,
            "strike_escalation_basis": "matches_case_financial_electricity_escalation",
            "default_strike_escalation_fraction": float(
                DEFAULT_STRIKE_ESCALATION_FRACTION
            ),
        },
        "physical_scope": {
            "technologies_in_scope": ["PV", "ElectricStorage", "ElectricUtility"],
            "technologies_out_of_scope": ["Wind", "Generator", "Resilience"],
            "battery_requirement": "reopt_may_optimize_storage_away",
            "export_posture": "reported_separately_not_settled_to_buyer",
        },
        "decision_metrics": {
            "primary_metrics": [
                "buyer_savings_vs_evn",
                "project_irr",
                "payback_years",
            ],
            "secondary_metrics": [
                "matched_renewable_delivery",
                "developer_finance_review",
                "contract_shape_risk",
            ],
        },
    }


def build_dppa_case_2_assumptions_register(extracted: dict) -> dict:
    strike_vnd = _strike_vnd_per_kwh(extracted)
    return {
        "model": "Ninhsim DPPA Case 2 Phase A Assumptions Register",
        "status": "agreed_user_reviewed",
        "questions": {
            "business_questions": {
                "selected_answer": "buyer_cost_developer_finance_and_contract_risk",
                "summary": [
                    "Can a synthetic DPPA lower buyer all-in cost versus EVN?",
                    "Can a synthetic DPPA work for developer at one negotiated strike?",
                    "What contract shape minimizes buyer excess-settlement risk?",
                ],
            },
            "contract_structure": {
                "selected_answer": DEFAULT_CONTRACT_STRUCTURE,
                "summary": "Synthetic / financial DPPA is the only structure in scope for Case 2.",
            },
            "settlement_quantity_rule": {
                "selected_answer": DEFAULT_SETTLEMENT_QUANTITY_RULE,
                "summary": "Match quantity equals min(load, contracted generation) in each interval.",
            },
            "excess_generation_treatment": {
                "selected_answer": DEFAULT_EXCESS_GENERATION_TREATMENT,
                "summary": "Excess generation is reported separately and excluded from buyer settlement.",
            },
            "strike_treatment": {
                "selected_answer": "five_percent_below_weighted_evn_with_escalation",
                "summary": (
                    f"Year-one strike anchors at {strike_vnd:.6f} VND/kWh, or 5% below the current Ninhsim weighted EVN tariff, with escalation logic retained."
                ),
            },
            "adder_and_kpp": {
                "selected_answer": "fixed_dppa_adder_and_fixed_kpp",
                "summary": (
                    f"Use fixed DPPA adder {DEFAULT_DPPA_ADDER_VND_PER_KWH:.2f} VND/kWh and fixed KPP {DEFAULT_KPP_FACTOR:.6f} in the first pass."
                ),
            },
            "market_price_source": {
                "selected_answer": "actual_fmp_cfmp_if_available_else_proxy",
                "summary": "Prefer actual hourly FMP/CFMP series; fall back to a proxy series from repo data only if no trusted actual series is available.",
            },
            "battery_requirement": {
                "selected_answer": "allow_reopt_to_optimize_storage_away",
                "summary": "Battery is optional; PV-only remains a valid outcome if REopt does not select storage.",
            },
            "reopt_objective": {
                "selected_answer": "minimum_buyer_cost_plus_maximum_matched_renewable_delivery",
                "summary": "Physical solve should favor minimum buyer cost under physical constraints while maximizing matched renewable delivery.",
            },
            "pysam_scope": {
                "selected_answer": "full_buyer_plus_developer_workflow_in_one_pass",
                "summary": "The first implementation pass should include PySAM rather than deferring developer-side validation.",
            },
            "pass_fail_metrics": {
                "selected_answer": "buyer_savings_project_irr_payback_years",
                "summary": "Primary pass/fail metrics are buyer savings, project IRR, and payback years.",
            },
            "customer_priority": {
                "selected_answer": "customer_best_interest_over_nonfinanceable_overlap",
                "summary": "Customer best interest remains the reporting priority even if no financeable developer overlap appears.",
            },
        },
        "known_open_inputs": [
            "Identify whether trusted Ninhsim hourly FMP/CFMP data exists locally or requires external research.",
            "Confirm the exact proxy source to use if actual Ninhsim market series cannot be sourced.",
        ],
    }


def build_dppa_case_2_settlement_design(
    phase_a_definition: dict,
    assumptions_register: dict,
) -> dict:
    strike = phase_a_definition["strike_basis"]
    return {
        "model": "Ninhsim DPPA Case 2 Phase B Settlement Design",
        "status": "draft_ready_for_implementation",
        "contract_structure": phase_a_definition["case_identity"]["contract_structure"],
        "hourly_settlement": {
            "settlement_quantity_rule": DEFAULT_SETTLEMENT_QUANTITY_RULE,
            "excess_generation_treatment": DEFAULT_EXCESS_GENERATION_TREATMENT,
            "matched_quantity_formula": "min(load_kwh, contracted_generation_kwh)",
            "shortfall_quantity_formula": "max(0, load_kwh - matched_quantity_kwh)",
            "excess_quantity_formula": "max(0, contracted_generation_kwh - matched_quantity_kwh)",
            "buyer_evn_matched_payment_formula": "matched_quantity_kwh * market_reference_price_vnd_per_kwh * kpp_factor",
            "buyer_dppa_charge_formula": "matched_quantity_kwh * dppa_adder_vnd_per_kwh",
            "buyer_shortfall_payment_formula": "shortfall_quantity_kwh * evn_retail_rate_vnd_per_kwh",
            "buyer_cfd_formula": "matched_quantity_kwh * (strike_price_vnd_per_kwh - market_reference_price_vnd_per_kwh)",
            "buyer_total_payment_formula": "evn_matched_payment + dppa_charge + shortfall_payment + buyer_cfd_payment",
            "buyer_blended_cost_formula": "buyer_total_payment / total_consumed_load_kwh",
            "negative_cfd_credit_allowed": True,
        },
        "fixed_parameters": {
            "year_one_strike_vnd_per_kwh": float(strike["year_one_strike_vnd_per_kwh"]),
            "year_one_strike_usd_per_kwh": float(strike["year_one_strike_usd_per_kwh"]),
            "strike_discount_fraction": float(strike["strike_discount_fraction"]),
            "strike_escalation_fraction": float(
                strike["default_strike_escalation_fraction"]
            ),
            "dppa_adder_vnd_per_kwh": float(DEFAULT_DPPA_ADDER_VND_PER_KWH),
            "kpp_factor": float(DEFAULT_KPP_FACTOR),
        },
        "market_price_source_priority": list(DEFAULT_MARKET_PRICE_SOURCE_PRIORITY),
        "market_price_source_notes": [
            "Use actual hourly CFMP or FMP series if available for Ninhsim or a credible directly transferable benchmark.",
            "If no trusted actual series is available, build a documented proxy series from repo data and mark it as provisional.",
        ],
        "separate_outputs": {
            "buyer_view": [
                "buyer_total_payment_vnd",
                "buyer_blended_cost_vnd_per_kwh",
                "buyer_savings_vs_evn_vnd",
                "buyer_cfd_payment_vnd",
                "buyer_shortfall_payment_vnd",
            ],
            "developer_view": [
                "developer_strike_revenue_vnd",
                "project_irr_fraction",
                "payback_years",
            ],
            "risk_view": [
                "matched_quantity_kwh",
                "shortfall_quantity_kwh",
                "excess_quantity_kwh",
                "hours_with_negative_cfd_credit",
            ],
        },
        "assumptions_trace": assumptions_register["questions"],
    }


def build_dppa_case_2_settlement_schema() -> dict:
    hourly_series = {
        "type": "array",
        "minItems": 8760,
        "maxItems": 8760,
        "items": {"type": "number"},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Ninhsim DPPA Case 2 Settlement Input Schema",
        "type": "object",
        "required": [
            "matched_quantity_rule",
            "excess_generation_treatment",
            "load_kwh_series",
            "contracted_generation_kwh_series",
            "market_reference_price_vnd_per_kwh_series",
            "evn_retail_rate_vnd_per_kwh_series",
            "strike_price_vnd_per_kwh",
            "dppa_adder_vnd_per_kwh",
            "kpp_factor",
        ],
        "properties": {
            "settlement_quantity_rule": {
                "type": "string",
                "enum": [DEFAULT_SETTLEMENT_QUANTITY_RULE],
            },
            "matched_quantity_rule": {
                "type": "string",
                "enum": [DEFAULT_SETTLEMENT_QUANTITY_RULE],
            },
            "excess_generation_treatment": {
                "type": "string",
                "enum": [DEFAULT_EXCESS_GENERATION_TREATMENT],
            },
            "market_reference_price_type": {
                "type": "string",
                "enum": ["cfmp", "fmp", "proxy_cfmp_or_fmp"],
            },
            "load_kwh_series": hourly_series,
            "contracted_generation_kwh_series": hourly_series,
            "market_reference_price_vnd_per_kwh_series": hourly_series,
            "evn_retail_rate_vnd_per_kwh_series": hourly_series,
            "strike_price_vnd_per_kwh": {"type": "number"},
            "dppa_adder_vnd_per_kwh": {"type": "number"},
            "kpp_factor": {"type": "number"},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
    }


def build_dppa_case_2_edge_case_matrix() -> dict:
    return {
        "model": "Ninhsim DPPA Case 2 Phase B Edge Case Matrix",
        "status": "draft_ready_for_tests",
        "cases": [
            {
                "case_name": "matched_hour_with_positive_buyer_cfd",
                "inputs": {
                    "load_kwh": 1000.0,
                    "contracted_generation_kwh": 800.0,
                    "market_reference_price_vnd_per_kwh": 1700.0,
                    "strike_price_vnd_per_kwh": 1917.9345481618014,
                },
                "expected_behavior": "Buyer pays positive CfD top-up on matched quantity only.",
            },
            {
                "case_name": "matched_hour_with_negative_buyer_cfd_credit",
                "inputs": {
                    "load_kwh": 1000.0,
                    "contracted_generation_kwh": 800.0,
                    "market_reference_price_vnd_per_kwh": 2200.0,
                    "strike_price_vnd_per_kwh": 1917.9345481618014,
                },
                "expected_behavior": "Buyer receives a negative CfD credit because market price is above strike on matched quantity.",
            },
            {
                "case_name": "shortfall_hour_with_retail_top_up",
                "inputs": {
                    "load_kwh": 1200.0,
                    "contracted_generation_kwh": 500.0,
                    "evn_retail_rate_vnd_per_kwh": 1895.49633,
                },
                "expected_behavior": "Shortfall quantity is billed at EVN retail tariff on top of the matched DPPA block.",
            },
            {
                "case_name": "excess_generation_hour_excluded_from_buyer_settlement",
                "inputs": {
                    "load_kwh": 500.0,
                    "contracted_generation_kwh": 900.0,
                    "market_reference_price_vnd_per_kwh": 1700.0,
                },
                "expected_behavior": "Buyer settlement caps at matched quantity and excludes excess generation from CfD and EVN matched payment calculations.",
            },
        ],
    }


def build_scenario_dppa_case_2(extracted: dict) -> dict:
    scenario = {
        "Site": {
            "latitude": extracted["site"]["latitude"],
            "longitude": extracted["site"]["longitude"],
        },
        "ElectricLoad": {
            "loads_kw": _load_series(extracted["loads_kw"]),
            "year": extracted.get("data_year", 2024),
        },
        "PV": {
            "min_kw": 0.0,
            "max_kw": 80_000.0,
            "installed_cost_per_kw": 750.0,
            "om_cost_per_kw": 6.0,
            "location": "ground",
            "tilt": extracted["site"]["latitude"],
            "azimuth": 180.0,
            "dc_ac_ratio": 1.2,
            "losses": 0.14,
            "can_wholesale": True,
            "can_net_meter": False,
            "can_export_beyond_nem_limit": True,
            "can_curtail": True,
        },
        "Wind": {
            "min_kw": 0.0,
            "max_kw": 0.0,
            "production_factor_series": [],
        },
        "ElectricStorage": {
            "min_kw": 0.0,
            "max_kw": 30_000.0,
            "min_kwh": 0.0,
            "max_kwh": 120_000.0,
            "installed_cost_per_kw": 200.0,
            "installed_cost_per_kwh": 200.0,
            "installed_cost_constant": 0.0,
            "replace_cost_per_kw": 100.0,
            "replace_cost_per_kwh": 100.0,
            "battery_replacement_year": 10,
            "inverter_replacement_year": 10,
            "soc_min_fraction": 0.15,
            "charge_efficiency": 0.95,
            "discharge_efficiency": 0.95,
            "om_cost_fraction_of_installed_cost": 0.01,
            "can_grid_charge": False,
        },
        "Financial": {
            "analysis_years": 20,
            "owner_tax_rate_fraction": 0.0575,
            "offtaker_tax_rate_fraction": 0.20,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": DEFAULT_STRIKE_ESCALATION_FRACTION,
            "om_cost_escalation_rate_fraction": 0.04,
        },
        "_meta": {
            "scenario": "DPPA_CASE_2",
            "name": "Ninhsim DPPA Case 2 - synthetic DPPA buyer-cost workflow",
            "site": dict(extracted["site"]),
            "description": (
                "Synthetic / financial DPPA physical sizing case for Ninhsim. "
                "REopt handles PV plus optional storage sizing and hourly energy flows, while buyer settlement is computed in post-processing under a matched-volume CfD ledger."
            ),
            "contract_type": DEFAULT_CONTRACT_STRUCTURE,
            "buyer_settlement_model": "post_processed_hourly_cfd",
            "settlement_quantity_rule": DEFAULT_SETTLEMENT_QUANTITY_RULE,
            "excess_generation_treatment": DEFAULT_EXCESS_GENERATION_TREATMENT,
            "battery_grid_charging_allowed": False,
            "storage_requirement": "optional_reopt_choice",
            "strike_discount_fraction": DEFAULT_STRIKE_DISCOUNT_FRACTION,
            "strike_anchor": "95_percent_of_weighted_evn_tariff",
            "strike_escalation": "matches_evn_escalation",
            "market_price_source_priority": list(DEFAULT_MARKET_PRICE_SOURCE_PRIORITY),
            "reopt_objective": "minimum_lifecycle_cost_with_post_processed_buyer_settlement_screen",
            "customer_priority": "customer_best_interest_first",
        },
    }
    vietnam_data = load_vietnam_data()
    apply_vietnam_defaults(
        scenario,
        vietnam_data,
        customer_type=extracted["site"]["customer_type"],
        voltage_level=extracted["site"]["voltage_level"],
        region=extracted["site"]["region"],
        pv_type="ground",
        wind_type="onshore",
        apply_financials=False,
        apply_tariff=True,
        apply_emissions=True,
        apply_tech_costs=False,
        apply_export_rules=True,
        apply_zero_incentives=True,
    )
    scenario["ElectricTariff"].pop("tou_energy_rates_vnd_per_kwh", None)
    return scenario


def build_dppa_case_2_market_proxy(extracted: dict) -> dict:
    retail_series = _load_retail_series(extracted)
    fraction = _proxy_market_fraction(extracted)
    hourly = [rate * fraction for rate in retail_series]
    return {
        "model": "Ninhsim DPPA Case 2 Market Proxy",
        "status": "proxy",
        "market_reference_price_type": "proxy_cfmp_or_fmp",
        "proxy_method": "hourly_evn_tariff_scaled_by_weighted_wholesale_ratio",
        "proxy_fraction_of_evn": fraction,
        "hourly_series_vnd_per_kwh": hourly,
        "notes": [
            "Proxy uses the repo wholesale benchmark divided by the weighted EVN tariff and scales the hourly EVN retail series by that ratio.",
            "Replace with actual hourly CFMP/FMP once a trusted market series is available.",
        ],
    }


def build_dppa_case_2_settlement_inputs(
    results: dict,
    extracted: dict,
    scenario: dict,
    *,
    actual_market_series_vnd_per_kwh: list[float] | None = None,
    market_reference_price_type: str | None = None,
    market_reference_artifact: dict | None = None,
) -> dict:
    load_series = _load_series(extracted["loads_kw"])
    horizon = len(load_series)
    contracted_generation = _sum_series_to_length(
        horizon,
        results.get("PV", {}).get("electric_to_load_series_kw", []),
        results.get("PV", {}).get("electric_to_grid_series_kw", []),
        results.get("Wind", {}).get("electric_to_load_series_kw", []),
        results.get("Wind", {}).get("electric_to_grid_series_kw", []),
    )
    if market_reference_artifact is not None:
        market_series = _pad_to_length(
            market_reference_artifact["hourly_series_vnd_per_kwh"], horizon
        )
        market_type = market_reference_artifact["market_reference_price_type"]
        notes = list(market_reference_artifact.get("notes", []))
    elif actual_market_series_vnd_per_kwh is None:
        proxy = build_dppa_case_2_market_proxy(extracted)
        market_series = _pad_to_length(proxy["hourly_series_vnd_per_kwh"], horizon)
        market_type = proxy["market_reference_price_type"]
        notes = list(proxy["notes"])
    else:
        market_series = _pad_to_length(actual_market_series_vnd_per_kwh, horizon)
        market_type = market_reference_price_type or "cfmp"
        notes = [
            "Settlement uses an externally supplied hourly market reference series."
        ]
    return {
        "settlement_quantity_rule": DEFAULT_SETTLEMENT_QUANTITY_RULE,
        "matched_quantity_rule": DEFAULT_SETTLEMENT_QUANTITY_RULE,
        "excess_generation_treatment": DEFAULT_EXCESS_GENERATION_TREATMENT,
        "market_reference_price_type": market_type,
        "load_kwh_series": load_series,
        "contracted_generation_kwh_series": contracted_generation,
        "market_reference_price_vnd_per_kwh_series": market_series,
        "evn_retail_rate_vnd_per_kwh_series": _pad_to_length(
            _load_retail_series(extracted), horizon
        ),
        "strike_price_vnd_per_kwh": _strike_vnd_per_kwh(extracted),
        "dppa_adder_vnd_per_kwh": DEFAULT_DPPA_ADDER_VND_PER_KWH,
        "kpp_factor": DEFAULT_KPP_FACTOR,
        # Was a hardcoded 25,000 fallback; unified onto the canonical 26,400
        # (ASM-002) in plans/2026-07-26-post-backlog-architecture-plan.md PHASE-05 Commit 2.
        "exchange_rate_vnd_per_usd": _resolve_exchange_rate(
            load_vietnam_data(),
            extracted={"benchmark": extracted["benchmark"]},
        ),
        "notes": notes,
        "scenario_metadata": scenario.get("_meta", {}),
        "market_reference_source": (
            None
            if market_reference_artifact is None
            else dict(market_reference_artifact)
        ),
    }


def build_dppa_case_2_physical_summary(
    results: dict,
    extracted: dict,
    scenario: dict,
) -> dict:
    delivery = _load_reopt_delivery_profile(results)
    exports = _load_reopt_export_profile(results)
    charge = _load_reopt_charge_profile(results)
    curtailed = _load_reopt_curtailment_profile(results)
    grid = _load_reopt_grid_supply_profile(results)
    renewable_generation = _sum_series(
        results.get("PV", {}).get("electric_to_load_series_kw", []),
        results.get("PV", {}).get("electric_to_grid_series_kw", []),
        results.get("Wind", {}).get("electric_to_load_series_kw", []),
        results.get("Wind", {}).get("electric_to_grid_series_kw", []),
    )
    total_load_kwh = sum(
        max(0.0, value) for value in _load_series(extracted["loads_kw"])
    )
    delivered_kwh = sum(max(0.0, value) for value in delivery)
    export_kwh = sum(max(0.0, value) for value in exports)
    contracted_generation_kwh = sum(max(0.0, value) for value in renewable_generation)
    charge_kwh = sum(max(0.0, value) for value in charge)
    curtailed_kwh = sum(max(0.0, value) for value in curtailed)
    grid_kwh = sum(max(0.0, value) for value in grid)
    pv_size_kw = float(results.get("PV", {}).get("size_kw") or 0.0)
    wind_size_kw = float(results.get("Wind", {}).get("size_kw") or 0.0)
    battery_power_kw = float(results.get("ElectricStorage", {}).get("size_kw") or 0.0)
    battery_capacity_kwh = float(
        results.get("ElectricStorage", {}).get("size_kwh") or 0.0
    )
    duration_hours = (
        battery_capacity_kwh / battery_power_kw if battery_power_kw else 0.0
    )
    matched_fraction = delivered_kwh / total_load_kwh if total_load_kwh else 0.0
    contracted_fraction = (
        contracted_generation_kwh / total_load_kwh if total_load_kwh else 0.0
    )

    return {
        "model": "Ninhsim DPPA Case 2 Physical Summary",
        "status": results.get("status", "unknown"),
        "case_identity": {
            "scenario_family": "DPPA Case 2",
            "contract_structure": DEFAULT_CONTRACT_STRUCTURE,
            "settlement_quantity_rule": DEFAULT_SETTLEMENT_QUANTITY_RULE,
            "excess_generation_treatment": DEFAULT_EXCESS_GENERATION_TREATMENT,
        },
        "site_load_basis": {
            "annual_load_gwh": float(extracted["benchmark"]["annual_load_gwh"]),
            "customer_type": extracted["site"]["customer_type"],
            "voltage_level": extracted["site"]["voltage_level"],
            "region": extracted["site"]["region"],
        },
        "optimal_mix": {
            "pv_size_mw": pv_size_kw / 1_000.0,
            "wind_size_mw": wind_size_kw / 1_000.0,
            "bess_mw": battery_power_kw / 1_000.0,
            "bess_mwh": battery_capacity_kwh / 1_000.0,
            "bess_duration_hours": duration_hours,
        },
        "energy_summary": {
            "pv_gwh": _annual_energy_kwh(results.get("PV", {})) / 1_000_000.0,
            "wind_gwh": _annual_energy_kwh(results.get("Wind", {})) / 1_000_000.0,
            "matched_delivery_kwh": delivered_kwh,
            "contracted_generation_kwh": contracted_generation_kwh,
            "grid_supplied_kwh": grid_kwh,
            "exported_generation_kwh": export_kwh,
            "curtailed_generation_kwh": curtailed_kwh,
            "renewable_charged_to_battery_kwh": charge_kwh,
            "total_load_kwh": total_load_kwh,
            "matched_fraction_of_load": matched_fraction,
            "contracted_fraction_of_load": contracted_fraction,
        },
        "design_checks": {
            "wind_disabled": wind_size_kw <= 1e-9,
            "storage_is_optional": scenario.get("_meta", {}).get("storage_requirement")
            == "optional_reopt_choice",
            "battery_grid_charging_requested": bool(
                scenario.get("ElectricStorage", {}).get("can_grid_charge", False)
            ),
        },
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
            "elec_cost_escalation_rate_fraction": _financial_value(
                results,
                "elec_cost_escalation_rate_fraction",
                DEFAULT_STRIKE_ESCALATION_FRACTION,
            ),
        },
        "notes": [
            "Physical summary keeps REopt sizing and hourly energy flows separate from buyer-side synthetic DPPA settlement.",
            "Contracted generation is limited to renewable generator output before the matched-load cap is applied in settlement; storage discharge is tracked separately inside physical delivery.",
        ],
    }


def run_dppa_case_2_buyer_settlement(settlement_inputs: dict) -> dict:
    load_series = _load_series(settlement_inputs["load_kwh_series"])
    generation_series = _load_series(
        settlement_inputs["contracted_generation_kwh_series"]
    )
    market_series = _load_series(
        settlement_inputs["market_reference_price_vnd_per_kwh_series"]
    )
    retail_series = _load_series(
        settlement_inputs["evn_retail_rate_vnd_per_kwh_series"]
    )
    strike = float(settlement_inputs["strike_price_vnd_per_kwh"])
    adder = float(settlement_inputs["dppa_adder_vnd_per_kwh"])
    kpp = float(settlement_inputs["kpp_factor"])
    # Was a hardcoded 25,000 fallback; unified onto the canonical 26,400
    # (ASM-002) in plans/2026-07-26-post-backlog-architecture-plan.md PHASE-05 Commit 2.
    exchange_rate = _resolve_exchange_rate(
        load_vietnam_data(),
        caller_value=settlement_inputs.get("exchange_rate_vnd_per_usd"),
    )

    hourly_ledger = []
    matched_total = 0.0
    shortfall_total = 0.0
    excess_total = 0.0
    evn_matched_total = 0.0
    dppa_charge_total = 0.0
    shortfall_payment_total = 0.0
    cfd_total = 0.0
    buyer_total = 0.0
    negative_cfd_hours = 0

    for index, values in enumerate(
        zip(load_series, generation_series, market_series, retail_series), start=1
    ):
        load_kwh, generation_kwh, market_price, retail_price = [
            float(v) for v in values
        ]
        matched_quantity = min(load_kwh, generation_kwh)
        shortfall_quantity = max(0.0, load_kwh - matched_quantity)
        excess_quantity = max(0.0, generation_kwh - matched_quantity)
        evn_matched_payment = matched_quantity * market_price * kpp
        dppa_charge = matched_quantity * adder
        shortfall_payment = shortfall_quantity * retail_price
        buyer_cfd_payment = matched_quantity * (strike - market_price)
        buyer_total_payment = (
            evn_matched_payment + dppa_charge + shortfall_payment + buyer_cfd_payment
        )
        if buyer_cfd_payment < 0.0:
            negative_cfd_hours += 1

        hourly_ledger.append(
            {
                "hour_index": index,
                "load_kwh": load_kwh,
                "contracted_generation_kwh": generation_kwh,
                "matched_quantity_kwh": matched_quantity,
                "shortfall_quantity_kwh": shortfall_quantity,
                "excess_quantity_kwh": excess_quantity,
                "market_reference_price_vnd_per_kwh": market_price,
                "evn_retail_rate_vnd_per_kwh": retail_price,
                "buyer_evn_matched_payment_vnd": evn_matched_payment,
                "buyer_dppa_charge_vnd": dppa_charge,
                "buyer_shortfall_payment_vnd": shortfall_payment,
                "buyer_cfd_payment_vnd": buyer_cfd_payment,
                "buyer_total_payment_vnd": buyer_total_payment,
            }
        )
        matched_total += matched_quantity
        shortfall_total += shortfall_quantity
        excess_total += excess_quantity
        evn_matched_total += evn_matched_payment
        dppa_charge_total += dppa_charge
        shortfall_payment_total += shortfall_payment
        cfd_total += buyer_cfd_payment
        buyer_total += buyer_total_payment

    total_load = sum(load_series)
    blended_cost = buyer_total / total_load if total_load else 0.0

    return {
        "model": "Ninhsim DPPA Case 2 Buyer Settlement",
        "status": "ok",
        "market_reference_price_type": settlement_inputs["market_reference_price_type"],
        "settlement_quantity_rule": settlement_inputs["settlement_quantity_rule"],
        "excess_generation_treatment": settlement_inputs["excess_generation_treatment"],
        "parameters": {
            "strike_price_vnd_per_kwh": strike,
            "dppa_adder_vnd_per_kwh": adder,
            "kpp_factor": kpp,
            "exchange_rate_vnd_per_usd": exchange_rate,
        },
        "hourly_ledger": hourly_ledger,
        "summary": {
            "matched_quantity_kwh": matched_total,
            "shortfall_quantity_kwh": shortfall_total,
            "excess_quantity_kwh": excess_total,
            "buyer_evn_matched_payment_vnd": evn_matched_total,
            "buyer_dppa_charge_vnd": dppa_charge_total,
            "buyer_shortfall_payment_vnd": shortfall_payment_total,
            "buyer_cfd_payment_vnd": cfd_total,
            "buyer_total_payment_vnd": buyer_total,
            "buyer_total_payment_usd": buyer_total / exchange_rate,
            "buyer_blended_cost_vnd_per_kwh": blended_cost,
            "buyer_blended_cost_usd_per_kwh": blended_cost / exchange_rate,
            "total_consumed_load_kwh": total_load,
            "hours_with_negative_cfd_credit": negative_cfd_hours,
        },
        "notes": list(settlement_inputs.get("notes", [])),
    }


def build_dppa_case_2_buyer_benchmark(
    physical_summary: dict,
    settlement: dict,
) -> dict:
    hourly_ledger = settlement["hourly_ledger"]
    benchmark_total = sum(
        float(entry["load_kwh"]) * float(entry["evn_retail_rate_vnd_per_kwh"])
        for entry in hourly_ledger
    )
    buyer_total = float(settlement["summary"]["buyer_total_payment_vnd"])
    total_load = float(settlement["summary"]["total_consumed_load_kwh"])
    benchmark_blended = benchmark_total / total_load if total_load else 0.0
    buyer_savings = max(0.0, benchmark_total - buyer_total)
    buyer_premium = max(0.0, buyer_total - benchmark_total)
    delta = buyer_total - benchmark_total

    return {
        "model": "Ninhsim DPPA Case 2 Buyer Benchmark",
        "status": settlement.get("status", "unknown"),
        "case_identity": physical_summary.get("case_identity", {}),
        "site_load_basis": physical_summary.get("site_load_basis", {}),
        "year_one_costs": {
            "buyer_total_payment_vnd": buyer_total,
            "benchmark_evn_total_cost_vnd": benchmark_total,
            "buyer_savings_vs_evn_vnd": buyer_savings,
            "buyer_premium_vs_evn_vnd": buyer_premium,
            "buyer_minus_benchmark_vnd": delta,
            "buyer_blended_cost_vnd_per_kwh": float(
                settlement["summary"]["buyer_blended_cost_vnd_per_kwh"]
            ),
            "benchmark_blended_cost_vnd_per_kwh": benchmark_blended,
        },
        "risk_summary": {
            "matched_quantity_kwh": float(
                settlement["summary"]["matched_quantity_kwh"]
            ),
            "shortfall_quantity_kwh": float(
                settlement["summary"]["shortfall_quantity_kwh"]
            ),
            "excess_quantity_kwh": float(settlement["summary"]["excess_quantity_kwh"]),
            "hours_with_negative_cfd_credit": int(
                settlement["summary"]["hours_with_negative_cfd_credit"]
            ),
        },
        "decision": {
            "buyer_savings_positive": buyer_savings > 0.0,
            "customer_premium_present": buyer_premium > 0.0,
            "recommended_position": (
                "buyer_savings_vs_evn"
                if buyer_savings > 0.0
                else "customer_premium_vs_evn"
            ),
        },
    }


def build_dppa_case_2_strike_sensitivity(
    settlement_inputs: dict,
    physical_summary: dict,
    *,
    strike_discount_fractions: tuple[float, ...] = (0.15, 0.10, 0.05, 0.0),
    developer_base_inputs=None,
    developer_runner=None,
) -> dict:
    benchmark_price = float(
        physical_summary["financial"].get("weighted_evn_price_vnd_per_kwh")
        or physical_summary.get("site_load_basis", {}).get(
            "weighted_evn_price_vnd_per_kwh", 0.0
        )
        or settlement_inputs["strike_price_vnd_per_kwh"]
        / (1.0 - DEFAULT_STRIKE_DISCOUNT_FRACTION)
    )
    # Was a hardcoded 25,000 fallback; unified onto the canonical 26,400
    # (ASM-002) in plans/2026-07-26-post-backlog-architecture-plan.md PHASE-05 Commit 2.
    exchange_rate = _resolve_exchange_rate(
        load_vietnam_data(),
        caller_value=settlement_inputs.get("exchange_rate_vnd_per_usd"),
    )
    active_runner = developer_runner
    if developer_base_inputs is not None and active_runner is None:
        from reopt_pysam_vn.pysam.single_owner import run_single_owner_model

        active_runner = run_single_owner_model

    strike_results = []
    overlap = []
    buyer_only = []
    developer_only = []

    for discount in strike_discount_fractions:
        strike_price = benchmark_price * (1.0 - float(discount))
        candidate_inputs = _copy_settlement_inputs_with_overrides(
            settlement_inputs,
            strike_price_vnd_per_kwh=strike_price,
        )
        settlement = run_dppa_case_2_buyer_settlement(candidate_inputs)
        benchmark = build_dppa_case_2_buyer_benchmark(physical_summary, settlement)
        developer_case = _build_developer_case_result(
            developer_base_inputs,
            strike_price_vnd_per_kwh=strike_price,
            exchange_rate_vnd_per_usd=exchange_rate,
            developer_runner=active_runner,
        )
        developer_result = developer_case["result"] if developer_case else None
        developer_pass = developer_case["passes_target"] if developer_case else False
        buyer_pass = _buyer_passes_benchmark(benchmark)
        entry = {
            "strike_discount_fraction": float(discount),
            "strike_price_vnd_per_kwh": float(strike_price),
            "buyer_blended_cost_vnd_per_kwh": float(
                benchmark["year_one_costs"]["buyer_blended_cost_vnd_per_kwh"]
            ),
            "buyer_minus_benchmark_vnd": float(
                benchmark["year_one_costs"]["buyer_minus_benchmark_vnd"]
            ),
            "buyer_passes": buyer_pass,
            "developer_passes": developer_pass,
            "developer_irr_fraction": (
                None
                if developer_result is None
                else developer_result.get("outputs", {}).get(
                    "project_return_aftertax_irr_fraction"
                )
            ),
            "developer_npv_usd": (
                None
                if developer_result is None
                else developer_result.get("outputs", {}).get(
                    "project_return_aftertax_npv_usd"
                )
            ),
        }
        strike_results.append(entry)
        if buyer_pass and developer_pass:
            overlap.append(entry)
        elif buyer_pass:
            buyer_only.append(entry)
        elif developer_pass:
            developer_only.append(entry)

    if overlap:
        recommended_position = "buyer_and_developer_overlap"
    elif buyer_only:
        recommended_position = "buyer_only_no_overlap"
    elif developer_only:
        recommended_position = "developer_only_no_overlap"
    else:
        recommended_position = "no_viable_case_found"

    return {
        "model": "Ninhsim DPPA Case 2 Strike Sensitivity",
        "status": "ok",
        "case_identity": physical_summary.get("case_identity", {}),
        "buyer_screen": {
            "benchmark_anchor_vnd_per_kwh": benchmark_price,
            "strike_discount_fractions": [
                float(value) for value in strike_discount_fractions
            ],
        },
        "developer_screen": {
            "included": developer_base_inputs is not None,
            "target_irr_fraction": (
                None
                if developer_base_inputs is None
                else float(developer_base_inputs.target_irr_fraction)
            ),
        },
        "strike_sweep_results": strike_results,
        "negotiation_summary": {
            "overlap_found": bool(overlap),
            "overlap_candidates": overlap,
            "buyer_only_candidates": buyer_only,
            "developer_only_candidates": developer_only,
            "recommended_position": recommended_position,
        },
        "notes": [
            "Strike sensitivity reuses the frozen Phase D buyer ledger and varies only the year-one strike anchor for the negotiation screen.",
            "Developer overlap is optional and uses the existing PySAM Single Owner runtime when finance inputs are supplied.",
        ],
    }


def build_dppa_case_2_contract_risk_sensitivity(
    settlement_inputs: dict,
    physical_summary: dict,
    *,
    dppa_adder_multipliers: tuple[float, ...] = (0.75, 1.0, 1.25),
    kpp_multipliers: tuple[float, ...] = (0.98, 1.0, 1.02),
    excess_generation_treatments: tuple[str, ...] = (
        "excluded_from_buyer_settlement",
        "cfd_on_excess_generation",
    ),
) -> dict:
    base_adder = float(settlement_inputs["dppa_adder_vnd_per_kwh"])
    base_kpp = float(settlement_inputs["kpp_factor"])
    base_strike = float(settlement_inputs["strike_price_vnd_per_kwh"])
    market_series = _load_series(
        settlement_inputs["market_reference_price_vnd_per_kwh_series"]
    )
    generation_series = _load_series(
        settlement_inputs["contracted_generation_kwh_series"]
    )
    load_series = _load_series(settlement_inputs["load_kwh_series"])

    adder_results = []
    for multiplier in dppa_adder_multipliers:
        candidate_inputs = _copy_settlement_inputs_with_overrides(
            settlement_inputs,
            dppa_adder_vnd_per_kwh=base_adder * float(multiplier),
        )
        settlement = run_dppa_case_2_buyer_settlement(candidate_inputs)
        benchmark = build_dppa_case_2_buyer_benchmark(physical_summary, settlement)
        adder_results.append(
            {
                "adder_multiplier": float(multiplier),
                "dppa_adder_vnd_per_kwh": float(
                    candidate_inputs["dppa_adder_vnd_per_kwh"]
                ),
                "buyer_minus_benchmark_vnd": float(
                    benchmark["year_one_costs"]["buyer_minus_benchmark_vnd"]
                ),
                "buyer_blended_cost_vnd_per_kwh": float(
                    benchmark["year_one_costs"]["buyer_blended_cost_vnd_per_kwh"]
                ),
            }
        )

    kpp_results = []
    for multiplier in kpp_multipliers:
        candidate_inputs = _copy_settlement_inputs_with_overrides(
            settlement_inputs,
            kpp_factor=base_kpp * float(multiplier),
        )
        settlement = run_dppa_case_2_buyer_settlement(candidate_inputs)
        benchmark = build_dppa_case_2_buyer_benchmark(physical_summary, settlement)
        kpp_results.append(
            {
                "kpp_multiplier": float(multiplier),
                "kpp_factor": float(candidate_inputs["kpp_factor"]),
                "buyer_minus_benchmark_vnd": float(
                    benchmark["year_one_costs"]["buyer_minus_benchmark_vnd"]
                ),
                "buyer_blended_cost_vnd_per_kwh": float(
                    benchmark["year_one_costs"]["buyer_blended_cost_vnd_per_kwh"]
                ),
            }
        )

    excess_results = []
    base_settlement = run_dppa_case_2_buyer_settlement(settlement_inputs)
    base_benchmark = build_dppa_case_2_buyer_benchmark(
        physical_summary, base_settlement
    )
    for treatment in excess_generation_treatments:
        extra_cfd_payment = 0.0
        if treatment == "cfd_on_excess_generation":
            extra_cfd_payment = sum(
                max(0.0, generation - min(load, generation)) * (base_strike - market)
                for load, generation, market in zip(
                    load_series, generation_series, market_series
                )
            )
        buyer_minus_benchmark = float(
            base_benchmark["year_one_costs"]["buyer_minus_benchmark_vnd"]
            + extra_cfd_payment
        )
        excess_results.append(
            {
                "excess_generation_treatment": treatment,
                "buyer_excess_cfd_payment_vnd": extra_cfd_payment,
                "buyer_minus_benchmark_vnd": buyer_minus_benchmark,
                "buyer_blended_cost_vnd_per_kwh": (
                    float(base_settlement["summary"]["buyer_blended_cost_vnd_per_kwh"])
                    + extra_cfd_payment
                    / float(base_settlement["summary"]["total_consumed_load_kwh"])
                ),
            }
        )

    return {
        "model": "Ninhsim DPPA Case 2 Contract Risk Sensitivity",
        "status": "ok",
        "case_identity": physical_summary.get("case_identity", {}),
        "adder_sensitivity": {
            "base_dppa_adder_vnd_per_kwh": base_adder,
            "results": adder_results,
        },
        "kpp_sensitivity": {
            "base_kpp_factor": base_kpp,
            "results": kpp_results,
        },
        "excess_treatment_sensitivity": {
            "base_excess_generation_treatment": settlement_inputs[
                "excess_generation_treatment"
            ],
            "results": excess_results,
        },
        "notes": [
            "Contract-risk sensitivity keeps the solved physical output fixed and varies settlement-rule parameters only.",
            "The excess-generation variant adds CfD exposure on excess renewable generation as a stress case against the customer-first base rule.",
        ],
    }


def build_dppa_case_2_market_reference_artifact(
    source_payload: dict,
    *,
    source_path: str,
    source_case: str,
) -> dict:
    selected_field = None
    market_type = None
    for candidate_field, candidate_type in (
        ("cfmp_vnd_per_mwh", "repo_actual_cfmp_transfer"),
        ("fmp_vnd_per_mwh", "repo_actual_fmp_transfer"),
        ("cfmp_vnd_per_kwh", "repo_actual_cfmp_transfer"),
        ("fmp_vnd_per_kwh", "repo_actual_fmp_transfer"),
    ):
        values = source_payload.get(candidate_field)
        if values:
            selected_field = candidate_field
            market_type = candidate_type
            normalized, normalization_method = _normalize_market_series_vnd_per_kwh(
                values
            )
            return {
                "model": "Ninhsim DPPA Case 2 Market Reference",
                "status": "repo_local_transfer",
                "market_reference_price_type": market_type,
                "selected_series_field": selected_field,
                "normalization_method": normalization_method,
                "source_case": source_case,
                "source_path": source_path,
                "hourly_series_vnd_per_kwh": normalized,
                "notes": [
                    "Market reference replaces the Phase D retail-scaled proxy with a repo-local extracted hourly series.",
                    "Series is transferred from another Vietnam project input set and should still be validated against the target site before being treated as bankable.",
                ],
            }
    raise ValueError(
        "No supported market series field found; expected cfmp/fmp series in VND/MWh or VND/kWh."
    )


def build_dppa_case_2_reopt_pysam_comparison(
    physical_summary: dict,
    settlement: dict,
    pysam_results: dict,
) -> dict:
    reopt_pv_kw = float(physical_summary["optimal_mix"]["pv_size_mw"]) * 1_000.0
    reopt_generation_kwh = float(
        physical_summary["energy_summary"]["contracted_generation_kwh"]
    )
    pysam_pv_kw = float(
        pysam_results.get("inputs", {}).get("system_capacity_kw") or 0.0
    )
    pysam_generation_kwh = float(
        pysam_results.get("inputs", {}).get("annual_generation_kwh") or 0.0
    )
    return {
        "model": "Ninhsim DPPA Case 2 REopt vs PySAM Comparison",
        "status": pysam_results.get("status", "unknown"),
        "reopt": {
            "pv_size_kw": reopt_pv_kw,
            "contracted_generation_kwh": reopt_generation_kwh,
            "buyer_blended_cost_vnd_per_kwh": float(
                settlement["summary"]["buyer_blended_cost_vnd_per_kwh"]
            ),
        },
        "pysam": {
            "system_capacity_kw": pysam_pv_kw,
            "annual_generation_kwh": pysam_generation_kwh,
            "aftertax_irr_fraction": pysam_results.get("outputs", {}).get(
                "project_return_aftertax_irr_fraction"
            ),
            "aftertax_npv_usd": pysam_results.get("outputs", {}).get(
                "project_return_aftertax_npv_usd"
            ),
            "min_dscr": pysam_results.get("outputs", {}).get("min_dscr"),
        },
        "alignment": {
            "pv_size_gap_kw": pysam_pv_kw - reopt_pv_kw,
            "annual_generation_gap_kwh": pysam_generation_kwh - reopt_generation_kwh,
        },
    }


def build_dppa_case_2_developer_screening(
    benchmark: dict,
    pysam_results: dict,
    comparison: dict,
    *,
    market_reference_artifact: dict,
    phase_e_reference: dict,
    target_irr_fraction: float | None = None,
) -> dict:
    target_irr = float(
        target_irr_fraction
        if target_irr_fraction is not None
        else pysam_results.get("inputs", {}).get("target_irr_fraction") or 0.15
    )
    irr = pysam_results.get("outputs", {}).get("project_return_aftertax_irr_fraction")
    buyer_passes = bool(benchmark["decision"]["buyer_savings_positive"])
    developer_passes = irr is not None and float(irr) >= target_irr
    combined_pass = buyer_passes and developer_passes
    if combined_pass:
        recommended_position = "advance_current_case"
    elif buyer_passes:
        recommended_position = "buyer_only_revise_finance"
    elif developer_passes:
        recommended_position = "developer_only_revise_buyer_terms"
    else:
        recommended_position = "reject_current_case"

    return {
        "model": "Ninhsim DPPA Case 2 Developer Screening",
        "status": pysam_results.get("status", "unknown"),
        "market_reference": {
            "market_reference_price_type": market_reference_artifact[
                "market_reference_price_type"
            ],
            "source_case": market_reference_artifact["source_case"],
            "source_path": market_reference_artifact["source_path"],
            "selected_series_field": market_reference_artifact["selected_series_field"],
        },
        "phase_e_reference": dict(phase_e_reference),
        "buyer_view": {
            "buyer_passes": buyer_passes,
            "buyer_minus_benchmark_vnd": float(
                benchmark["year_one_costs"]["buyer_minus_benchmark_vnd"]
            ),
            "buyer_blended_cost_vnd_per_kwh": float(
                benchmark["year_one_costs"]["buyer_blended_cost_vnd_per_kwh"]
            ),
        },
        "developer_view": {
            "target_irr_fraction": target_irr,
            "developer_passes_target_irr": developer_passes,
            "aftertax_irr_fraction": irr,
            "aftertax_npv_usd": pysam_results.get("outputs", {}).get(
                "project_return_aftertax_npv_usd"
            ),
            "min_dscr": pysam_results.get("outputs", {}).get("min_dscr"),
        },
        "comparison": comparison,
        "decision": {
            "combined_pass": combined_pass,
            "recommended_position": recommended_position,
        },
        "notes": [
            "Phase F keeps buyer and developer outputs separate, then combines them only in the final screening decision block.",
            "The screening result should be interpreted together with the market-reference source quality before any commercial recommendation is treated as final.",
        ],
    }


def build_dppa_case_2_combined_decision_artifact(
    *,
    physical_summary: dict,
    strike_sensitivity: dict,
    contract_risk: dict,
    developer_screening: dict,
) -> dict:
    market_type = developer_screening["market_reference"]["market_reference_price_type"]
    if market_type.startswith("repo_actual_"):
        market_reference_quality = "transferred_repo_local"
    elif market_type.startswith("proxy"):
        market_reference_quality = "proxy"
    else:
        market_reference_quality = "site_specific_or_external"

    recommended_position = developer_screening["decision"]["recommended_position"]
    if recommended_position.startswith("advance"):
        decision_class = "advance"
    elif recommended_position.startswith("reject"):
        decision_class = "reject"
    else:
        decision_class = "revise"

    strike_results = strike_sensitivity["strike_sweep_results"]
    lowest_buyer_premium = min(
        float(entry["buyer_minus_benchmark_vnd"]) for entry in strike_results
    )
    best_developer_npv = max(
        float(entry["developer_npv_usd"])
        for entry in strike_results
        if entry["developer_npv_usd"] is not None
    )
    excess_stress = contract_risk["excess_treatment_sensitivity"]["results"][-1]

    return {
        "model": "Ninhsim DPPA Case 2 Combined Decision",
        "status": developer_screening.get("status", "unknown"),
        "case_identity": dict(physical_summary.get("case_identity", {})),
        "site_and_market_basis": {
            **dict(physical_summary.get("site_load_basis", {})),
            **dict(developer_screening.get("market_reference", {})),
        },
        "physical_summary": {
            "optimal_mix": dict(physical_summary.get("optimal_mix", {})),
            "energy_summary": dict(physical_summary.get("energy_summary", {})),
            "reopt_financial": dict(physical_summary.get("financial", {})),
        },
        "buyer_summary": dict(developer_screening.get("buyer_view", {})),
        "developer_summary": dict(developer_screening.get("developer_view", {})),
        "contract_risk_summary": {
            "adder_results": list(contract_risk["adder_sensitivity"]["results"]),
            "kpp_results": list(contract_risk["kpp_sensitivity"]["results"]),
            "excess_treatment_results": list(
                contract_risk["excess_treatment_sensitivity"]["results"]
            ),
        },
        "strike_summary": {
            "negotiation_summary": dict(strike_sensitivity["negotiation_summary"]),
            "strike_sweep_results": list(strike_results),
        },
        "critical_findings": {
            "buyer_premium_vnd": float(
                developer_screening["buyer_view"]["buyer_minus_benchmark_vnd"]
            ),
            "lowest_tested_buyer_premium_vnd": lowest_buyer_premium,
            "best_tested_developer_npv_usd": best_developer_npv,
            "excess_cfd_stress_vnd": float(
                excess_stress["buyer_excess_cfd_payment_vnd"]
            ),
            "negative_or_null_irr": developer_screening["developer_view"][
                "aftertax_irr_fraction"
            ]
            is None,
        },
        "decision": {
            "combined_pass": bool(developer_screening["decision"]["combined_pass"]),
            "recommended_position": recommended_position,
            "decision_class": decision_class,
            "market_reference_quality": market_reference_quality,
        },
        "notes": [
            "Phase G combines the published Phase C-F artifacts without rerunning the underlying physical, settlement, or PySAM engines.",
            "The current combined recommendation should be read as a case-screening closeout, not as a substitute for new commercial assumptions or a site-specific CFMP/FMP dataset.",
        ],
    }


def build_dppa_case_2_final_summary_artifact(
    *,
    combined_decision: dict,
    phase_artifact_paths: dict[str, str],
) -> dict:
    history = [
        {
            "phase": "Phase C",
            "focus": "physical sizing and energy-balance summary",
            "artifact_path": phase_artifact_paths["phase_c"],
        },
        {
            "phase": "Phase D",
            "focus": "buyer settlement and benchmark baseline",
            "artifact_path": phase_artifact_paths["phase_d"],
        },
        {
            "phase": "Phase E",
            "focus": "strike and contract-risk sensitivities",
            "artifact_path": phase_artifact_paths["phase_e"],
        },
        {
            "phase": "Phase F",
            "focus": "market replacement and developer validation",
            "artifact_path": phase_artifact_paths["phase_f"],
        },
        {
            "phase": "Phase G",
            "focus": "combined decision package",
            "artifact_path": phase_artifact_paths["phase_g"],
        },
    ]
    return {
        "model": "Ninhsim DPPA Case 2 Final Summary",
        "status": combined_decision.get("status", "unknown"),
        "case_identity": dict(combined_decision.get("case_identity", {})),
        "final_decision": dict(combined_decision.get("decision", {})),
        "critical_findings": dict(combined_decision.get("critical_findings", {})),
        "case_history": history,
        "closeout": {
            "separate_final_report_warranted": True,
            "reason": "The combined-decision artifact benefits from a separate closeout report because the Case 2 workflow spans multiple phases and ends with an explicit reject-or-revise recommendation.",
        },
        "notes": [
            "The final summary exists to close out the full Case 2 phase sequence in one artifact and point reviewers to the canonical phase outputs.",
        ],
    }
