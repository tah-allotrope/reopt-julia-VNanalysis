"""PHASE-04 tests: regime stress (GAP-05) + combined decision artifact.

Regime stress is pure tariff math (no PySAM). The combined decision's developer
roll-up is exercised with an injected fake runner for determinism.
"""

from __future__ import annotations

import pytest

from reopt_pysam_vn.integration.dppa_samsung_ttc import (
    build_samsung_ttc_combined_decision,
    build_samsung_ttc_extracted_inputs,
    build_samsung_ttc_regime_stress,
)


def _fake_developer_runner(inputs):
    ppa = float(inputs.ppa_price_input_usd_per_kwh)
    return {
        "status": "ok",
        "outputs": {
            "project_return_aftertax_irr_fraction": ppa * 3.0,
            "project_return_aftertax_npv_usd": (ppa - 0.045) * 5e8,
        },
    }


def test_regime_stress_nonzero_and_two_part_worse():
    ex = build_samsung_ttc_extracted_inputs()
    stress = build_samsung_ttc_regime_stress(ex)
    regimes = {r["regime_id"]: r for r in stress["regimes"]}
    # Baseline (Decision 963) compares against itself => zero delta.
    base = regimes[stress["baseline_regime_id"]]
    assert base["annual_bill_delta_vnd"] == pytest.approx(0.0, abs=1.0)
    # Decree 146 two-part trial raises the buyer's EVN bill (capacity charge).
    two_part = regimes["decree146_two_part_trial_2026"]
    assert two_part["annual_bill_delta_vnd"] > 0
    assert two_part["delta_pct"] > 5.0
    # Decision 14 legacy shifts the peak window (morning peak returns).
    legacy = regimes["decision_14_2025_legacy"]
    assert legacy["peak_hours_changed"] == 5
    assert stress["quality"]["basis"] == "directional"


def test_combined_decision_rolls_up_all_phases():
    ex = build_samsung_ttc_extracted_inputs()
    decision = build_samsung_ttc_combined_decision(
        ex, developer_runner=_fake_developer_runner
    )
    # Disclosed facts + each phase surface present.
    assert decision["deal"]["plant"]["capacity_mwp"] == pytest.approx(49.0)
    assert "base_settlement" in decision
    assert "strike_sweep" in decision
    assert "adder_sensitivity" in decision
    assert "regime_stress" in decision
    # Decision block is explicit and directional.
    assert decision["decision"]["buyer_saves_at_base_strike"] is True
    assert decision["decision"]["recommended_position"] in (
        "advance_negotiable_band_exists",
        "buyer_favorable_developer_subeconomic",
        "reject_no_buyer_saving",
    )
    assert decision["quality"]["basis"] == "directional"
    assert "strike" in decision["quality"]["caveat"].lower()


def test_combined_decision_buyer_only_path_without_developer():
    ex = build_samsung_ttc_extracted_inputs()
    decision = build_samsung_ttc_combined_decision(ex, run_developer=False)
    # Buyer saves at the base (Southern ceiling) strike even without a developer run.
    assert decision["decision"]["buyer_saves_at_base_strike"] is True
    assert decision["decision"]["recommended_position"] in (
        "buyer_favorable_developer_subeconomic",
        "reject_no_buyer_saving",
    )
