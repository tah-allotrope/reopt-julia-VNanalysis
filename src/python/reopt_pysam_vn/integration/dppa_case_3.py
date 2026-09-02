"""Helpers for Saigon18 DPPA Case 3 definition, settlement, and analysis."""

from __future__ import annotations

from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.common.series import pad_to_8760
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

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

BASE_PV_KWP = 3200.0
BASE_BESS_KW = 1000.0
BASE_BESS_KWH = 2200.0
PV_BOUND_FACTOR_LOW = 0.75
PV_BOUND_FACTOR_HIGH = 1.50
BESS_BOUND_FACTOR_LOW = 0.75
BESS_BOUND_FACTOR_HIGH = 1.50


def _compute_weighted_evn_from_tou(tou_series: list[float]) -> float:
    values = [float(v) for v in tou_series[:8760]]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _build_tou_from_tariff_assumptions(assumptions: dict) -> list[float]:
    peak = float(assumptions.get("tariff_peak_vnd_per_kwh", 3266.0))
    standard = float(assumptions.get("tariff_standard_vnd_per_kwh", 1811.0))
    offpeak = float(assumptions.get("tariff_offpeak_vnd_per_kwh", 1146.0))
    tou = []
    for hour in range(8760):
        day = hour // 24
        h = hour % 24
        weekday = day % 7 < 5
        if weekday:
            if 9 <= h < 12 or 17 <= h < 20:
                tou.append(peak)
            elif 22 <= h or h < 4:
                tou.append(offpeak)
            else:
                tou.append(standard)
        else:
            if 22 <= h or h < 4:
                tou.append(offpeak)
            else:
                tou.append(standard)
    return tou


def build_dppa_case_3_phase_a_definition(extracted: dict) -> dict:
    assumptions = extracted.get("assumptions", {})
    load_kw = extracted.get("loads_kw", [])
    tou_series = _build_tou_from_tariff_assumptions(assumptions)
    weighted_evn = _compute_weighted_evn_from_tou(tou_series)
    annual_load_kwh = sum(float(v) for v in load_kw[:8760])
    annual_load_gwh = annual_load_kwh / 1e6
    peak_load_kw = float(extracted.get("peak_load_kw", max(load_kw) if load_kw else 0))
    # Deal-specific FX: Saigon18 contract basis, 25,450 VND/USD.
    # Intentionally NOT the repo canonical 26,400 (see plans/2026-07-26-post-backlog-architecture-plan.md ASM-005).
    exchange_rate = _resolve_exchange_rate(load_vietnam_data(), caller_value=25_450.0)
    strike_vnd = weighted_evn * (1.0 - DEFAULT_STRIKE_DISCOUNT_FRACTION)
    strike_usd = strike_vnd / exchange_rate
    return {
        "model": "Saigon18 DPPA Case 3 Phase A Definition",
        "status": "agreed_user_reviewed",
        "case_identity": {
            "scenario_family": "DPPA Case 3",
            "slug": "saigon18_dppa_case_3",
            "contract_structure": DEFAULT_CONTRACT_STRUCTURE,
            "project_basis": "saigon18_8760_load_and_market",
            "customer_priority": "customer_best_interest_first",
            "main_business_questions": [
                "buyer_all_in_cost_vs_evn_two_part_and_tou",
                "developer_finance_at_5pct_discount_strike",
                "controller_vs_optimizer_dispatch_gap",
                "tariff_branch_delta_two_part_vs_tou",
            ],
        },
        "site_load_basis": {
            "location": extracted.get("location", "Vietnam (south, HCMC area)"),
            "data_year": extracted.get("data_year", 2024),
            "annual_load_kwh": annual_load_kwh,
            "annual_load_gwh": annual_load_gwh,
            "peak_load_kw": peak_load_kw,
            "load_profile_source": "saigon18_extracted_8760",
            "market_profile_source": "saigon18_extracted_cfmp_fmp",
        },
        "strike_basis": {
            "anchor": "weighted_evn_tariff_discount",
            "strike_discount_fraction": float(DEFAULT_STRIKE_DISCOUNT_FRACTION),
            "weighted_evn_price_vnd_per_kwh": round(weighted_evn, 6),
            "weighted_evn_price_usd_per_kwh": round(weighted_evn / exchange_rate, 6),
            "year_one_strike_vnd_per_kwh": round(strike_vnd, 6),
            "year_one_strike_usd_per_kwh": round(strike_usd, 6),
            "strike_escalation_basis": "matches_case_financial_electricity_escalation",
            "default_strike_escalation_fraction": float(
                DEFAULT_STRIKE_ESCALATION_FRACTION
            ),
            "sensitivity_sweep_discounts": [0.0, 0.05, 0.10, 0.15, 0.20],
        },
        "physical_scope": {
            "lane_structure": "bounded_optimization_only",
            "technologies_in_scope": ["PV", "ElectricStorage", "ElectricUtility"],
            "technologies_out_of_scope": ["Wind", "Generator", "Resilience"],
            "battery_requirement": "mandatory_storage_floor",
            "storage_floor_min_kw": BASE_BESS_KW * BESS_BOUND_FACTOR_LOW,
            "storage_floor_min_kwh": BASE_BESS_KWH * BESS_BOUND_FACTOR_LOW,
            "pv_bounds_kw": {
                "min": BASE_PV_KWP * PV_BOUND_FACTOR_LOW,
                "max": BASE_PV_KWP * PV_BOUND_FACTOR_HIGH,
            },
            "bess_power_bounds_kw": {
                "min": BASE_BESS_KW * BESS_BOUND_FACTOR_LOW,
                "max": BASE_BESS_KW * BESS_BOUND_FACTOR_HIGH,
            },
            "bess_energy_bounds_kwh": {
                "min": BASE_BESS_KWH * BESS_BOUND_FACTOR_LOW,
                "max": BASE_BESS_KWH * BESS_BOUND_FACTOR_HIGH,
            },
            "base_concept": {
                "pv_kwp": BASE_PV_KWP,
                "bess_kw": BASE_BESS_KW,
                "bess_kwh": BASE_BESS_KWH,
            },
            "export_posture": "reported_separately_not_settled_to_buyer",
        },
        "tariff_branches": [
            {
                "branch_name": "22kv_two_part_evn",
                "role": "primary_realism",
                "description": "22 kV two-part EVN tariff with energy and demand charges",
            },
            {
                "branch_name": "legacy_tou_one_component",
                "role": "reference_cross_check",
                "description": "Legacy one-component EVN TOU from saigon18 assumptions",
            },
        ],
        "tariff_reporting_style": "side_by_side_with_delta_columns",
        "decision_metrics": {
            "primary_metrics": [
                "buyer_savings_vs_evn",
                "project_irr",
                "payback_years",
                "tariff_branch_delta",
            ],
            "secondary_metrics": [
                "matched_renewable_delivery",
                "developer_finance_review",
                "contract_shape_risk",
                "controller_vs_optimizer_dispatch_gap",
            ],
        },
        "site_consistency_block": {
            "load_source_case": "saigon18",
            "market_source_case": "saigon18",
            "tariff_source_case": "saigon18",
            "same_site_basis": True,
            "same_project_workstream": True,
        },
    }


_pad_to_8760 = pad_to_8760

def load_saigon18_load_series(extracted: dict) -> list[float]:
    return _pad_to_8760(extracted.get("loads_kw", []))


def load_saigon18_cfmp_series(extracted: dict) -> list[float]:
    raw = extracted.get("cfmp_vnd_per_mwh", [])
    converted = [float(v) / 1000.0 for v in raw]
    return _pad_to_8760(converted)


def load_saigon18_fmp_series(extracted: dict) -> list[float]:
    raw = extracted.get("fmp_vnd_per_mwh", [])
    converted = [float(v) / 1000.0 for v in raw]
    return _pad_to_8760(converted)


def load_saigon18_tou_series(extracted: dict) -> list[float]:
    assumptions = extracted.get("assumptions", {})
    tou = _build_tou_from_tariff_assumptions(assumptions)
    return _pad_to_8760(tou)


def scale_load_to_annual_kwh(
    load_series: list[float], target_annual_kwh: float
) -> list[float]:
    current_annual = sum(float(v) for v in load_series[:8760])
    if current_annual == 0:
        return load_series
    factor = target_annual_kwh / current_annual
    return [float(v) * factor for v in load_series[:8760]]


def build_dppa_case_3_input_package(
    extracted: dict,
    target_annual_kwh: float | None = None,
) -> dict:
    load = load_saigon18_load_series(extracted)
    if target_annual_kwh is not None:
        load = scale_load_to_annual_kwh(load, target_annual_kwh)
    cfmp = load_saigon18_cfmp_series(extracted)
    fmp = load_saigon18_fmp_series(extracted)
    tou = load_saigon18_tou_series(extracted)
    annual_load_kwh = sum(load)
    annual_cfmp_mean = sum(cfmp) / len(cfmp) if cfmp else 0.0
    weighted_evn = _compute_weighted_evn_from_tou(tou)
    return {
        "model": "Saigon18 DPPA Case 3 Input Package",
        "status": "canonical",
        "site_consistency_block": {
            "load_source_case": "saigon18",
            "market_source_case": "saigon18",
            "tariff_source_case": "saigon18",
            "same_site_basis": True,
            "same_project_workstream": True,
        },
        "load": {
            "series_kwh": load,
            "annual_kwh": round(annual_load_kwh, 2),
            "annual_gwh": round(annual_load_kwh / 1e6, 4),
            "peak_kw": round(max(load), 2),
            "source": "saigon18_extracted_8760",
            "scaled": target_annual_kwh is not None,
            "scale_target_annual_kwh": target_annual_kwh,
        },
        "market": {
            "cfmp_vnd_per_kwh": cfmp,
            "fmp_vnd_per_kwh": fmp,
            "cfmp_annual_mean_vnd_per_kwh": round(annual_cfmp_mean, 6),
            "source": "saigon18_extracted_cfmp_fmp",
            "market_price_type": "cfmp",
        },
        "tariff": {
            "branches": [
                {
                    "branch_name": "22kv_two_part_evn",
                    "role": "primary_realism",
                    "energy_rates_vnd_per_kwh": tou,
                    "demand_charge_notes": "Demand charges deferred to post-processing until exact schedule is confirmed.",
                },
                {
                    "branch_name": "legacy_tou_one_component",
                    "role": "reference_cross_check",
                    "energy_rates_vnd_per_kwh": tou,
                },
            ],
            "weighted_evn_vnd_per_kwh": round(weighted_evn, 6),
            "tariff_assumptions": extracted.get("assumptions", {}),
        },
        "strike": {
            "base_discount_fraction": DEFAULT_STRIKE_DISCOUNT_FRACTION,
            "base_strike_vnd_per_kwh": round(
                weighted_evn * (1.0 - DEFAULT_STRIKE_DISCOUNT_FRACTION), 6
            ),
            "sensitivity_sweep_discounts": [0.0, 0.05, 0.10, 0.15, 0.20],
        },
        "physical_bounds": {
            "pv_bounds_kw": {
                "min": BASE_PV_KWP * PV_BOUND_FACTOR_LOW,
                "max": BASE_PV_KWP * PV_BOUND_FACTOR_HIGH,
            },
            "bess_power_bounds_kw": {
                "min": BASE_BESS_KW * BESS_BOUND_FACTOR_LOW,
                "max": BASE_BESS_KW * BESS_BOUND_FACTOR_HIGH,
            },
            "bess_energy_bounds_kwh": {
                "min": BASE_BESS_KWH * BESS_BOUND_FACTOR_LOW,
                "max": BASE_BESS_KWH * BESS_BOUND_FACTOR_HIGH,
            },
        },
        "meta": {
            "data_year": extracted.get("data_year", 2024),
            "location": extracted.get("location", "Vietnam (south, HCMC area)"),
            "validation_passed": extracted.get("validation_passed", True),
        },
    }


def build_dppa_case_3_assumptions_register(extracted: dict) -> dict:
    return {
        "model": "Saigon18 DPPA Case 3 Phase A Assumptions Register",
        "status": "agreed_user_reviewed",
        "questions": {
            "business_questions": {
                "selected_answer": "buyer_cost_developer_finance_contract_risk_tariff_delta_and_dispatch_gap",
                "summary": [
                    "Can a synthetic DPPA lower buyer all-in cost versus EVN under both tariff branches?",
                    "Can a synthetic DPPA work for developer at 5% below EVN strike?",
                    "What is the dispatch gap between optimizer and controller-style operation?",
                    "What is the buyer-cost delta between 22kV two-part and legacy TOU?",
                ],
            },
            "contract_structure": {
                "selected_answer": DEFAULT_CONTRACT_STRUCTURE,
                "summary": "Synthetic / financial DPPA is the only structure in scope for Case 3.",
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
                "selected_answer": "five_percent_below_weighted_evn_with_sensitivity_sweep",
                "summary": "Year-one strike anchors at 5% below the weighted EVN tariff with a sensitivity sweep from 0% to 20% discount.",
            },
            "physical_lane": {
                "selected_answer": "bounded_optimization_only_with_storage_floor",
                "summary": "Single bounded-optimization lane with mandatory storage floor. No fixed-size lane.",
            },
            "adder_and_kpp": {
                "selected_answer": "fixed_dppa_adder_and_fixed_kpp",
                "summary": (
                    f"Use fixed DPPA adder {DEFAULT_DPPA_ADDER_VND_PER_KWH:.2f} VND/kWh and fixed KPP {DEFAULT_KPP_FACTOR:.6f} in the first pass."
                ),
            },
            "market_price_source": {
                "selected_answer": "actual_saigon18_cfmp_fmp",
                "summary": "Use saigon18 repo-local actual hourly CFMP/FMP series directly. No proxy transfer needed.",
            },
            "tariff_branches": {
                "selected_answer": "two_branches_side_by_side",
                "summary": "Run 22kV two-part EVN tariff as primary realism branch and legacy TOU as reference. Side-by-side delta reporting.",
            },
            "battery_requirement": {
                "selected_answer": "mandatory_storage_floor",
                "summary": "Storage is mandatory via hard lower bounds. REopt cannot optimize storage away.",
            },
            "dispatch_comparison": {
                "selected_answer": "optimizer_vs_controller_gap_quantified",
                "summary": "Controller-style dispatch sensitivity added as a first-class comparison, not a narrative footnote.",
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
                "selected_answer": "buyer_savings_project_irr_payback_years_tariff_delta",
                "summary": "Primary pass/fail metrics are buyer savings, project IRR, payback years, and tariff branch delta.",
            },
            "customer_priority": {
                "selected_answer": "customer_best_interest_over_nonfinanceable_overlap",
                "summary": "Customer best interest remains the reporting priority even if no financeable developer overlap appears.",
            },
        },
        "known_open_inputs": [
            "Confirm exact 22kV two-part tariff structure (demand charge schedule, energy charge tiers).",
            "Confirm controller dispatch windows if real-project charge/discharge schedules are available.",
        ],
    }


def build_dppa_case_3_gap_register() -> dict:
    return {
        "model": "Saigon18 DPPA Case 3 Gap Register",
        "status": "frozen",
        "inherited_shortcomings": [
            {
                "shortcoming": "PV-only outcome in Case 1 and Case 2 — BESS question never answered",
                "source_case": "Case 1 + Case 2",
                "case_3_mitigation": "Mandatory storage_floor via hard min_kw > 0 and min_kwh > 0 bounds in bounded-optimization lane.",
            },
            {
                "shortcoming": "Load and market basis mismatched across sites",
                "source_case": "Case 2",
                "case_3_mitigation": "Both load and market series come from saigon18. site_consistency_block enforces same_site_basis=True.",
            },
            {
                "shortcoming": "Strike sweep anchored too far from real-project notes",
                "source_case": "Case 2",
                "case_3_mitigation": "Strike anchors at 5% below EVN (user decision) with explicit sensitivity sweep 0-20%.",
            },
            {
                "shortcoming": "Optimizer-vs-controller gap hidden in narrative text",
                "source_case": "Case 1",
                "case_3_mitigation": "Controller-style dispatch sensitivity is a first-class Phase E output, not a footnote.",
            },
            {
                "shortcoming": "Sensitivities widened around a rejected base case instead of changing assumptions",
                "source_case": "Case 2",
                "case_3_mitigation": "Case 3 changes foundational assumptions (site-consistent data, mandatory storage, bounded opt) before any sensitivity work.",
            },
            {
                "shortcoming": "No tariff branch comparison — only one tariff tested",
                "source_case": "Case 1 + Case 2",
                "case_3_mitigation": "Two tariff branches (22kV two-part + legacy TOU) with side-by-side delta reporting.",
            },
            {
                "shortcoming": "Too optimization-led, not project-led",
                "source_case": "Case 2",
                "case_3_mitigation": "Bounded optimization starts from real-project reference sizes (3.2 MWp / 1 MW / 2.2 MWh) and allows narrow envelope only.",
            },
        ],
    }


def build_dppa_case_3_settlement_design(
    phase_a_definition: dict,
    assumptions_register: dict,
) -> dict:
    strike = phase_a_definition["strike_basis"]
    return {
        "model": "Saigon18 DPPA Case 3 Phase B Settlement Design",
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
            "Use saigon18 repo-local actual hourly CFMP/FMP series directly.",
            "No proxy transfer needed because saigon18 provides its own market series.",
        ],
        "tariff_branches": [
            {
                "branch_name": "22kv_two_part_evn",
                "settlement_note": "Energy charges applied hourly; demand charges reconciled in post-processing if not natively in REopt.",
            },
            {
                "branch_name": "legacy_tou_one_component",
                "settlement_note": "Hourly TOU rates from saigon18 tariff assumptions.",
            },
        ],
        "tariff_reporting_style": "side_by_side_with_delta_columns",
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
            "tariff_delta_view": [
                "buyer_cost_delta_two_part_vs_tou_vnd",
                "blended_cost_delta_vnd_per_kwh",
            ],
        },
        "site_consistency_block": phase_a_definition["site_consistency_block"],
        "assumptions_trace": assumptions_register["questions"],
    }


def build_dppa_case_3_settlement_schema() -> dict:
    hourly_series = {
        "type": "array",
        "minItems": 8760,
        "maxItems": 8760,
        "items": {"type": "number"},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Saigon18 DPPA Case 3 Settlement Input Schema",
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
            "tariff_branch": {
                "type": "string",
                "enum": ["22kv_two_part_evn", "legacy_tou_one_component"],
            },
            "notes": {"type": "array", "items": {"type": "string"}},
        },
    }


def build_dppa_case_3_edge_case_matrix() -> dict:
    return {
        "model": "Saigon18 DPPA Case 3 Phase B Edge Case Matrix",
        "status": "draft_ready_for_tests",
        "cases": [
            {
                "case_name": "matched_hour_with_positive_buyer_cfd",
                "inputs": {
                    "load_kwh": 1000.0,
                    "contracted_generation_kwh": 800.0,
                    "market_reference_price_vnd_per_kwh": 1700.0,
                    "strike_price_vnd_per_kwh": 1900.0,
                },
                "expected_behavior": "Buyer pays positive CfD top-up on matched quantity only.",
            },
            {
                "case_name": "matched_hour_with_negative_buyer_cfd_credit",
                "inputs": {
                    "load_kwh": 1000.0,
                    "contracted_generation_kwh": 800.0,
                    "market_reference_price_vnd_per_kwh": 2200.0,
                    "strike_price_vnd_per_kwh": 1900.0,
                },
                "expected_behavior": "Buyer receives a negative CfD credit because market price is above strike on matched quantity.",
            },
            {
                "case_name": "shortfall_hour_with_retail_top_up",
                "inputs": {
                    "load_kwh": 1200.0,
                    "contracted_generation_kwh": 500.0,
                    "evn_retail_rate_vnd_per_kwh": 1811.0,
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
