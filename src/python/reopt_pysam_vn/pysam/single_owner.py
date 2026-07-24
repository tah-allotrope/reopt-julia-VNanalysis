"""Single Owner entry points for PySAM finance modeling."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from reopt_pysam_vn.pysam.cashflow import build_annual_cashflow_table, trim_year_zero
from reopt_pysam_vn.pysam.config import PySAMRuntimeConfig
from reopt_pysam_vn.pysam.metrics import extract_single_owner_outputs


@dataclass
class SingleOwnerInputs:
    """Normalized developer-finance inputs for the Phase 4 Single Owner MVP."""

    system_capacity_kw: float
    generation_profile_kw: list[float] = field(default_factory=lambda: [100.0] * 8760)
    annual_generation_kwh: float = 876_000.0
    installed_cost_usd: float = 1_000_000.0
    fixed_om_usd_per_year: float = 10_000.0
    ppa_price_input_usd_per_kwh: float = 0.08
    analysis_years: int = 20
    debt_fraction: float = 0.70
    target_irr_fraction: float = 0.15
    owner_tax_rate_fraction: float = 0.20
    owner_discount_rate_fraction: float = 0.08
    offtaker_discount_rate_fraction: float = 0.10
    inflation_rate_fraction: float = 0.035
    debt_interest_rate_fraction: float = 0.085
    debt_tenor_years: int = 10
    ppa_escalation_rate_fraction: float = 0.04
    om_escalation_rate_fraction: float = 0.03
    # "vn_sl_15yr" = VN Circular 45 SL 15-yr | "vn_sl_10yr" = SL 10-yr custom | "us_macrs_5yr" = US MACRS
    depreciation_schedule: str = "vn_sl_15yr"
    # When True, zeroes SAM's ~100 MW-reference-plant cost defaults (insurance,
    # construction financing, debt fees, reserves, property tax, salvage) via
    # apply_clean_slate_financials(). Default False preserves legacy behavior
    # exactly (CON-001: Samsung/TTC bit-exact parity is never affected by this
    # flag unless a caller explicitly opts in). See
    # reports/2026-07-24-single-owner-defaults-audit.md.
    zero_reference_plant_defaults: bool = False
    metadata: dict = field(default_factory=dict)


def build_single_owner_inputs(
    system_capacity_kw: float, **overrides
) -> SingleOwnerInputs:
    """Create a normalized Single Owner input bundle."""

    inputs = SingleOwnerInputs(
        system_capacity_kw=float(system_capacity_kw), **overrides
    )
    if not inputs.generation_profile_kw:
        raise ValueError("generation_profile_kw must not be empty")
    if len(inputs.generation_profile_kw) != 8760:
        raise ValueError("generation_profile_kw must contain 8760 hourly values")
    if inputs.annual_generation_kwh <= 0.0:
        inputs.annual_generation_kwh = float(sum(inputs.generation_profile_kw))
    return inputs


def _safe_float(value: float) -> float | None:
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return value


# The twelve SAM Singleowner.FinancialParameters fields that carry non-zero,
# ~100 MW-reference-plant cost defaults (verified live against nrel-pysam
# 7.1.0 on 2026-07-24; see reports/2026-07-24-single-owner-defaults-audit.md
# and this repo's plans/2026-07-24-post-ci-hygiene-finance-audit-plan.md
# Specification section for the full field-by-field rationale).
CLEAN_SLATE_REFERENCE_PLANT_FIELDS = (
    "insurance_rate",
    "construction_financing_cost",
    "cost_debt_fee",
    "cost_debt_closing",
    "months_working_reserve",
    "dscr_reserve_months",
    "equip1_reserve_cost",
    "equip2_reserve_cost",
    "equip3_reserve_cost",
    "prop_tax_cost_assessed_percent",
    "reserves_interest",
    "salvage_percentage",
)


def apply_clean_slate_financials(financial_model) -> None:
    """Zero SAM's reference-plant cost defaults on ``financial_model`` in place.

    Sets each field in CLEAN_SLATE_REFERENCE_PLANT_FIELDS to 0.0 via plain
    attribute assignment, so a renamed or missing PySAM attribute raises
    ``AttributeError`` immediately rather than being silently skipped.
    """

    for name in CLEAN_SLATE_REFERENCE_PLANT_FIELDS:
        setattr(financial_model.FinancialParameters, name, 0.0)


def _configure_financial_model(financial_model, inputs: SingleOwnerInputs) -> None:
    financial_model.Revenue.ppa_soln_mode = 1
    financial_model.Revenue.ppa_price_input = [
        float(inputs.ppa_price_input_usd_per_kwh)
    ]
    financial_model.Revenue.ppa_escalation = (
        float(inputs.ppa_escalation_rate_fraction) * 100.0
    )

    financial_model.SystemCosts.total_installed_cost = float(inputs.installed_cost_usd)
    financial_model.SystemCosts.om_fixed = [float(inputs.fixed_om_usd_per_year)]
    financial_model.SystemCosts.om_capacity = [0.0]
    financial_model.SystemCosts.om_production = [0.0]
    financial_model.SystemCosts.om_fuel_cost = [0.0]
    financial_model.SystemCosts.om_fixed_escal = (
        float(inputs.om_escalation_rate_fraction) * 100.0
    )
    financial_model.SystemCosts.om_capacity_escal = 0.0
    financial_model.SystemCosts.om_production_escal = 0.0

    financial_model.FinancialParameters.analysis_period = int(inputs.analysis_years)
    financial_model.FinancialParameters.debt_option = 0
    financial_model.FinancialParameters.debt_percent = (
        float(inputs.debt_fraction) * 100.0
    )
    financial_model.FinancialParameters.federal_tax_rate = [
        float(inputs.owner_tax_rate_fraction) * 100.0
    ]
    financial_model.FinancialParameters.state_tax_rate = [0.0]
    financial_model.FinancialParameters.real_discount_rate = (
        float(inputs.owner_discount_rate_fraction) * 100.0
    )
    financial_model.FinancialParameters.inflation_rate = (
        float(inputs.inflation_rate_fraction) * 100.0
    )
    financial_model.FinancialParameters.term_int_rate = (
        float(inputs.debt_interest_rate_fraction) * 100.0
    )
    financial_model.FinancialParameters.term_tenor = int(inputs.debt_tenor_years)

    sched = inputs.depreciation_schedule
    if sched == "us_macrs_5yr":
        financial_model.Depreciation.depr_fedbas_method = 1
        financial_model.Depreciation.depr_stabas_method = 1
        financial_model.Depreciation.depr_alloc_macrs_5_percent = 100.0
        financial_model.Depreciation.depr_alloc_sl_15_percent = 0.0
        financial_model.Depreciation.depr_alloc_custom_percent = 0.0
    elif sched == "vn_sl_10yr":
        financial_model.Depreciation.depr_fedbas_method = 1
        financial_model.Depreciation.depr_stabas_method = 0
        financial_model.Depreciation.depr_alloc_macrs_5_percent = 0.0
        financial_model.Depreciation.depr_alloc_sl_15_percent = 0.0
        financial_model.Depreciation.depr_alloc_custom_percent = 100.0
        financial_model.Depreciation.depr_custom_schedule = [10.0] * 10 + [0.0] * 15
    else:  # vn_sl_15yr (VN Circular 45 default)
        financial_model.Depreciation.depr_fedbas_method = 1
        financial_model.Depreciation.depr_stabas_method = 0
        financial_model.Depreciation.depr_alloc_macrs_5_percent = 0.0
        financial_model.Depreciation.depr_alloc_sl_15_percent = 100.0
        financial_model.Depreciation.depr_alloc_custom_percent = 0.0
    financial_model.Depreciation.depr_alloc_macrs_15_percent = 0.0
    financial_model.Depreciation.depr_alloc_sl_5_percent = 0.0
    financial_model.Depreciation.depr_alloc_sl_20_percent = 0.0
    financial_model.Depreciation.depr_alloc_sl_39_percent = 0.0
    financial_model.Depreciation.depr_bonus_fed = 0.0
    financial_model.Depreciation.depr_bonus_sta = 0.0

    financial_model.TaxCreditIncentives.itc_fed_percent = (0.0,)
    financial_model.TaxCreditIncentives.itc_sta_percent = (0.0,)
    financial_model.TaxCreditIncentives.itc_fed_amount = (0.0,)
    financial_model.TaxCreditIncentives.itc_sta_amount = (0.0,)
    financial_model.TaxCreditIncentives.ptc_fed_amount = (0.0,)
    financial_model.TaxCreditIncentives.ptc_sta_amount = (0.0,)
    financial_model.TaxCreditIncentives.ptc_fed_term = 10
    financial_model.TaxCreditIncentives.ptc_sta_term = 10
    financial_model.TaxCreditIncentives.ptc_fed_escal = 0.0
    financial_model.TaxCreditIncentives.ptc_sta_escal = 0.0

    if inputs.zero_reference_plant_defaults:
        apply_clean_slate_financials(financial_model)


def run_single_owner_model(inputs: SingleOwnerInputs) -> dict:
    """Execute the Phase 4 Single Owner workflow and normalize the outputs."""

    import PySAM.CustomGeneration as cg
    import PySAM.Grid as gr
    import PySAM.Singleowner as so
    import PySAM.Utilityrate5 as ur

    runtime = PySAMRuntimeConfig()
    system_model = cg.default("CustomGenerationProfileNone")
    grid_model = gr.from_existing(system_model, runtime.system_config)
    utility_model = ur.from_existing(system_model, runtime.system_config)
    financial_model = so.from_existing(system_model, runtime.system_config)

    system_model.Plant.system_capacity = float(inputs.system_capacity_kw)
    system_model.Plant.derate = 1.0
    system_model.Plant.energy_output_array = [
        float(value) for value in inputs.generation_profile_kw
    ]
    system_model.Plant.spec_mode = 1
    system_model.Lifetime.analysis_period = int(inputs.analysis_years)
    system_model.Lifetime.system_use_lifetime_output = 0
    system_model.Lifetime.generic_degradation = [0.5]

    _configure_financial_model(financial_model, inputs)

    system_model.execute()
    grid_model.execute()
    utility_model.execute()
    financial_model.execute()

    analysis_years = int(inputs.analysis_years)
    revenue = trim_year_zero(financial_model.Outputs.cf_total_revenue, analysis_years)
    aftertax_cash = trim_year_zero(
        financial_model.Outputs.cf_project_return_aftertax_cash,
        analysis_years,
    )
    debt_service = trim_year_zero(
        financial_model.Outputs.cf_debt_payment_total,
        analysis_years,
    )
    debt_balance = trim_year_zero(
        financial_model.Outputs.cf_debt_balance, analysis_years
    )
    dscr = trim_year_zero(financial_model.Outputs.cf_pretax_dscr, analysis_years)

    notes = {
        "phase_scope": "Phase 4 MVP uses CustomGenerationProfileSingleOwner with wrapper-driven Vietnam defaults and zeroed US-style incentives.",
        "irr_warning": "PySAM can return null-equivalent IRR when the configured cashflow never crosses into positive territory under the selected strike and cost assumptions.",
    }
    if inputs.zero_reference_plant_defaults:
        notes["clean_slate"] = (
            "US SAM reference-plant cost defaults zeroed; "
            "see reports/2026-07-24-single-owner-defaults-audit.md"
        )

    return {
        "model": runtime.model_name,
        "status": "ok",
        "runtime": {
            "country": runtime.country,
            "currency": runtime.currency,
            "python": runtime.local_python,
            "system_config": runtime.system_config,
        },
        "inputs": {
            "system_capacity_kw": float(inputs.system_capacity_kw),
            "annual_generation_kwh": float(inputs.annual_generation_kwh),
            "installed_cost_usd": float(inputs.installed_cost_usd),
            "fixed_om_usd_per_year": float(inputs.fixed_om_usd_per_year),
            "ppa_price_input_usd_per_kwh": float(inputs.ppa_price_input_usd_per_kwh),
            "analysis_years": analysis_years,
            "debt_fraction": float(inputs.debt_fraction),
            "target_irr_fraction": float(inputs.target_irr_fraction),
            "owner_tax_rate_fraction": float(inputs.owner_tax_rate_fraction),
            "owner_discount_rate_fraction": float(inputs.owner_discount_rate_fraction),
            "debt_interest_rate_fraction": float(inputs.debt_interest_rate_fraction),
            "debt_tenor_years": int(inputs.debt_tenor_years),
            "zero_reference_plant_defaults": bool(inputs.zero_reference_plant_defaults),
        },
        "case": dict(inputs.metadata),
        "outputs": extract_single_owner_outputs(financial_model),
        "annual_cashflows": build_annual_cashflow_table(
            analysis_years,
            revenue,
            aftertax_cash,
            debt_service,
            debt_balance,
            dscr,
        ),
        "notes": notes,
    }
