"""Regression tests for Ninhsim DPPA Case 2 Phase G decision surfaces."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_2 import (
    build_dppa_case_2_combined_decision_artifact,
    build_dppa_case_2_final_summary_artifact,
)


def _physical_summary() -> dict:
    return {
        "case_identity": {
            "scenario_family": "DPPA Case 2",
            "contract_structure": "synthetic_financial_dppa",
        },
        "site_load_basis": {
            "annual_load_gwh": 184.2860885,
            "customer_type": "industrial",
        },
        "optimal_mix": {
            "pv_size_mw": 41.7248202,
            "bess_mw": 0.0,
            "bess_mwh": 0.0,
        },
        "energy_summary": {
            "matched_fraction_of_load": 0.2816007756,
            "contracted_fraction_of_load": 0.3015792066,
            "exported_generation_kwh": 3681746.902,
            "contracted_generation_kwh": 55576852.356,
        },
        "financial": {"reopt_npv_usd": 11879346.97},
    }


def _contract_risk() -> dict:
    return {
        "adder_sensitivity": {
            "results": [
                {"buyer_minus_benchmark_vnd": 5235607957.105835},
                {"buyer_minus_benchmark_vnd": 12025304079.179382},
                {"buyer_minus_benchmark_vnd": 18815000201.253662},
            ]
        },
        "kpp_sensitivity": {
            "results": [
                {"buyer_minus_benchmark_vnd": 11235157552.320251},
                {"buyer_minus_benchmark_vnd": 12025304079.179382},
                {"buyer_minus_benchmark_vnd": 12815450606.039246},
            ]
        },
        "excess_treatment_sensitivity": {
            "results": [
                {"buyer_minus_benchmark_vnd": 12025304079.179382},
                {
                    "buyer_minus_benchmark_vnd": 16254278936.776844,
                    "buyer_excess_cfd_payment_vnd": 4228974857.5974627,
                },
            ]
        },
    }


def _strike_sensitivity() -> dict:
    return {
        "negotiation_summary": {
            "overlap_found": False,
            "recommended_position": "no_viable_case_found",
        },
        "strike_sweep_results": [
            {
                "strike_discount_fraction": 0.15,
                "strike_price_vnd_per_kwh": 1716.0467009868748,
                "buyer_minus_benchmark_vnd": 1548312960.1553955,
                "developer_npv_usd": -51454406.5734476,
            },
            {
                "strike_discount_fraction": 0.05,
                "strike_price_vnd_per_kwh": 1917.9345481618013,
                "buyer_minus_benchmark_vnd": 12025304079.179382,
                "developer_npv_usd": -47278699.34445363,
            },
        ],
    }


def _developer_screening() -> dict:
    return {
        "market_reference": {
            "market_reference_price_type": "repo_actual_cfmp_transfer",
            "source_case": "saigon18",
            "selected_series_field": "cfmp_vnd_per_mwh",
        },
        "buyer_view": {
            "buyer_passes": False,
            "buyer_minus_benchmark_vnd": 12812356040.989624,
            "buyer_blended_cost_vnd_per_kwh": 2088.4027431974027,
        },
        "developer_view": {
            "target_irr_fraction": 0.15,
            "developer_passes_target_irr": False,
            "aftertax_irr_fraction": None,
            "aftertax_npv_usd": -47278699.34445363,
            "min_dscr": -0.4667527808782992,
        },
        "comparison": {
            "alignment": {
                "pv_size_gap_kw": 0.0,
                "annual_generation_gap_kwh": 0.0,
            }
        },
        "decision": {
            "combined_pass": False,
            "recommended_position": "reject_current_case",
        },
    }


def test_build_dppa_case_2_combined_decision_artifact_makes_reject_decision_explicit():
    combined = build_dppa_case_2_combined_decision_artifact(
        physical_summary=_physical_summary(),
        strike_sensitivity=_strike_sensitivity(),
        contract_risk=_contract_risk(),
        developer_screening=_developer_screening(),
    )

    assert combined["model"] == "Ninhsim DPPA Case 2 Combined Decision"
    assert combined["decision"]["recommended_position"] == "reject_current_case"
    assert combined["decision"]["decision_class"] == "reject"
    assert combined["decision"]["combined_pass"] is False
    assert combined["decision"]["market_reference_quality"] == "transferred_repo_local"
    assert combined["critical_findings"]["buyer_premium_vnd"] == 12812356040.989624
    assert combined["critical_findings"]["excess_cfd_stress_vnd"] == 4228974857.5974627


def test_build_dppa_case_2_final_summary_artifact_rolls_up_whole_case_history():
    combined = build_dppa_case_2_combined_decision_artifact(
        physical_summary=_physical_summary(),
        strike_sensitivity=_strike_sensitivity(),
        contract_risk=_contract_risk(),
        developer_screening=_developer_screening(),
    )

    final_summary = build_dppa_case_2_final_summary_artifact(
        combined_decision=combined,
        phase_artifact_paths={
            "phase_c": "artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_physical-summary.json",
            "phase_d": "artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_buyer-benchmark.json",
            "phase_e": "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_strike-sensitivity.json",
            "phase_f": "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_developer-screening.json",
            "phase_g": "artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_combined-decision.json",
        },
    )

    assert final_summary["model"] == "Ninhsim DPPA Case 2 Final Summary"
    assert (
        final_summary["final_decision"]["recommended_position"] == "reject_current_case"
    )
    assert final_summary["final_decision"]["decision_class"] == "reject"
    assert len(final_summary["case_history"]) == 5
    assert final_summary["closeout"]["separate_final_report_warranted"] is True
