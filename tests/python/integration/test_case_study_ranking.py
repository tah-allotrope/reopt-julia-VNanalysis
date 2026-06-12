"""
Regression tests for case-study physical-fit ranking.

These tests lock the mixed-format parsing, cleaning, and physical-match ranking
heuristics used to screen offtakers against the reference 30 MWp solar profile.
"""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python" / "integration"))

from rank_case_study_offtakers import (  # noqa: E402
    BESS_POWER_KW,
    SOLAR_CAPACITY_KW,
    build_results,
    clean_numeric,
    compute_fit_score,
    sanitize_load_series,
    summarize_case,
)


def test_clean_numeric_handles_quotes_commas_and_missing_markers():
    assert clean_numeric(' " 18,205 " ') == 18205.0
    assert clean_numeric("-") is None
    assert clean_numeric("") is None
    assert clean_numeric(None) is None


def test_sanitize_load_series_interpolates_missing_and_clips_negative_values():
    cleaned, issues = sanitize_load_series([1000.0, None, -4.0, 1600.0])

    assert cleaned == [1000.0, 500.0, 0.0, 1600.0]
    assert issues["missing_count"] == 1
    assert issues["clipped_negative_count"] == 1
    assert issues["final_count"] == 4


def test_compute_fit_score_rewards_high_absorption_and_solar_hour_floor():
    strong = {
        "solar_absorption_with_bess_pct": 100.0,
        "solar_absorption_no_bess_pct": 95.0,
        "solar_hours_fully_absorbed_with_bess_pct": 98.0,
        "min_solar_hour_load_mw": 28.0,
    }
    weak = {
        "solar_absorption_with_bess_pct": 25.0,
        "solar_absorption_no_bess_pct": 10.0,
        "solar_hours_fully_absorbed_with_bess_pct": 5.0,
        "min_solar_hour_load_mw": 0.5,
    }

    assert compute_fit_score(strong) > compute_fit_score(weak)


def test_summarize_case_captures_direct_and_bess_augmented_match():
    solar_series_kw = [10_000.0] * 8760
    load_series_kw = [8_000.0] * 8760
    case_definition = {
        "case": "synthetic",
        "label": "Synthetic",
        "kind": "csv",
        "path": REPO_ROOT / "synthetic.csv",
        "notes": "Synthetic case",
    }

    summary = summarize_case(
        case_definition=case_definition,
        load_series_kw=load_series_kw,
        solar_series_kw=solar_series_kw,
        issues={
            "missing_count": 0,
            "interpolated_indices": [],
            "clipped_negative_count": 0,
            "final_count": 8760,
        },
    )

    assert summary["direct_match_gwh"] == 70.08
    assert summary["matched_with_bess_gwh"] == 87.6
    assert summary["solar_absorption_no_bess_pct"] == 80.0
    assert summary["solar_absorption_with_bess_pct"] == 100.0
    assert summary["average_solar_hour_load_mw"] == 8.0


def test_build_results_preserves_expected_physical_ranking_order():
    results = build_results()
    ranking = [row["case"] for row in results["ranking"]]

    assert results["screening_basis"]["mode"] == "pure_physical_load_matching"
    assert results["screening_basis"]["solar_capacity_kw"] == SOLAR_CAPACITY_KW
    assert results["screening_basis"]["bess_power_cap_kw"] == BESS_POWER_KW
    assert ranking == [
        "north_thuan",
        "ninhsim",
        "saigon18",
        "verdant",
        "emivest",
        "regina",
    ]

    north_thuan = results["ranking"][0]
    assert north_thuan["solar_absorption_with_bess_pct"] > 99.0
    assert north_thuan["curtailment_with_bess_gwh"] < 0.2
