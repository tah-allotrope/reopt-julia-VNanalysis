"""Tests for the opt-in Single Owner clean-slate flag (PHASE-02 of
plans/2026-07-24-post-ci-hygiene-finance-audit-plan.md).

Verifies: (1) default (flag-off) behavior is byte-identical to the existing
SAM reference-plant defaults, (2) flag-on zeroes exactly the twelve fields in
the plan's Specification, (3) the flag-on run produces a strictly higher NPV
than the flag-off run for identical inputs, and (4) the output dict only
carries the "clean_slate" note when the flag is on.
"""

from __future__ import annotations

import pytest

from reopt_pysam_vn.pysam.single_owner import build_single_owner_inputs

CLEAN_SLATE_FIELDS = (
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


def test_single_owner_inputs_default_flag_is_false():
    inputs = build_single_owner_inputs(system_capacity_kw=1000.0)
    assert inputs.zero_reference_plant_defaults is False


def test_single_owner_inputs_accepts_clean_slate_override():
    inputs = build_single_owner_inputs(
        system_capacity_kw=1000.0, zero_reference_plant_defaults=True
    )
    assert inputs.zero_reference_plant_defaults is True


PySAM = pytest.importorskip("PySAM")


# Holds references to every model built by _build_financial_model() so they
# are never garbage-collected mid-test: mirrors the exact model chain in
# run_single_owner_model (Grid and Utilityrate5 must be built from the same
# system_model before Singleowner, or PySAM's Revenue group is left unlinked
# and setting ppa_soln_mode segfaults — a genuine PySAM access violation,
# confirmed during RED-phase test authoring on 2026-07-25).
_MODEL_REFS: list = []


def _build_financial_model():
    import PySAM.CustomGeneration as cg
    import PySAM.Grid as gr
    import PySAM.Singleowner as so
    import PySAM.Utilityrate5 as ur

    system_config = "CustomGenerationProfileSingleOwner"
    system_model = cg.default("CustomGenerationProfileNone")
    grid_model = gr.from_existing(system_model, system_config)
    utility_model = ur.from_existing(system_model, system_config)
    financial_model = so.from_existing(system_model, system_config)
    _MODEL_REFS.append((system_model, grid_model, utility_model, financial_model))
    return financial_model


def test_configure_financial_model_default_off_preserves_sam_reference_defaults():
    from reopt_pysam_vn.pysam.single_owner import _configure_financial_model

    financial_model = _build_financial_model()
    inputs = build_single_owner_inputs(system_capacity_kw=1000.0)

    _configure_financial_model(financial_model, inputs)

    assert financial_model.FinancialParameters.construction_financing_cost == 2866500.0
    assert financial_model.FinancialParameters.insurance_rate == 0.5
    assert financial_model.FinancialParameters.cost_debt_fee == 2.75
    assert financial_model.FinancialParameters.months_working_reserve == 6.0
    assert financial_model.FinancialParameters.dscr_reserve_months == 6.0
    assert financial_model.FinancialParameters.prop_tax_cost_assessed_percent == 100.0
    assert financial_model.FinancialParameters.reserves_interest == 1.75


def test_configure_financial_model_flag_on_zeroes_all_twelve_reference_fields():
    from reopt_pysam_vn.pysam.single_owner import _configure_financial_model

    financial_model = _build_financial_model()
    inputs = build_single_owner_inputs(
        system_capacity_kw=1000.0, zero_reference_plant_defaults=True
    )

    _configure_financial_model(financial_model, inputs)

    for name in CLEAN_SLATE_FIELDS:
        value = getattr(financial_model.FinancialParameters, name)
        assert value == 0.0, f"{name} expected 0.0, got {value}"


def test_apply_clean_slate_financials_zeroes_all_twelve_fields_in_place():
    from reopt_pysam_vn.pysam.single_owner import apply_clean_slate_financials

    financial_model = _build_financial_model()
    # Sanity: at least one field is non-zero before the call.
    assert financial_model.FinancialParameters.construction_financing_cost != 0.0

    apply_clean_slate_financials(financial_model)

    for name in CLEAN_SLATE_FIELDS:
        value = getattr(financial_model.FinancialParameters, name)
        assert value == 0.0, f"{name} expected 0.0, got {value}"


def test_run_single_owner_model_flag_on_yields_strictly_higher_npv_than_flag_off():
    from reopt_pysam_vn.pysam.single_owner import run_single_owner_model

    common_kwargs = dict(
        system_capacity_kw=1000.0,
        installed_cost_usd=550_000.0,
        ppa_price_input_usd_per_kwh=0.065,
    )

    flag_off_inputs = build_single_owner_inputs(**common_kwargs)
    flag_on_inputs = build_single_owner_inputs(
        zero_reference_plant_defaults=True, **common_kwargs
    )

    flag_off_results = run_single_owner_model(flag_off_inputs)
    flag_on_results = run_single_owner_model(flag_on_inputs)

    flag_off_npv = flag_off_results["outputs"]["project_return_aftertax_npv_usd"]
    flag_on_npv = flag_on_results["outputs"]["project_return_aftertax_npv_usd"]
    assert flag_on_npv > flag_off_npv

    assert flag_off_results["inputs"]["zero_reference_plant_defaults"] is False
    assert flag_on_results["inputs"]["zero_reference_plant_defaults"] is True


def test_run_single_owner_model_notes_only_carry_clean_slate_when_flag_is_on():
    from reopt_pysam_vn.pysam.single_owner import run_single_owner_model

    flag_off_inputs = build_single_owner_inputs(system_capacity_kw=1000.0)
    flag_on_inputs = build_single_owner_inputs(
        system_capacity_kw=1000.0, zero_reference_plant_defaults=True
    )

    flag_off_results = run_single_owner_model(flag_off_inputs)
    flag_on_results = run_single_owner_model(flag_on_inputs)

    assert "clean_slate" not in flag_off_results["notes"]
    assert "clean_slate" in flag_on_results["notes"]
    assert flag_on_results["notes"]["clean_slate"] == (
        "US SAM reference-plant cost defaults zeroed; "
        "see reports/2026-07-24-single-owner-defaults-audit.md"
    )
    # Existing note strings must be unchanged for both runs.
    assert (
        flag_off_results["notes"]["phase_scope"]
        == flag_on_results["notes"]["phase_scope"]
    )
    assert (
        flag_off_results["notes"]["irr_warning"]
        == flag_on_results["notes"]["irr_warning"]
    )
