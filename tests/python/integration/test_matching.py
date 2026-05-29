"""GAP-03 PHASE-02: Multi-dimensional matching engine tests.

Covers the five scoring dimensions (physical, geographic, capacity, commercial,
regulatory), ranking behavior, blocker flagging for private-wire projects, and
the no-viable-project edge case. Red/Green TDD.
"""

from __future__ import annotations

import pytest

from reopt_pysam_vn.integration.matching import (
    DEFAULT_WEIGHTS,
    FactoryProfile,
    ProjectMatch,
    match_projects_to_factory,
    physical_fit_from_profile,
)
from reopt_pysam_vn.integration.project_catalog import load_project_catalog

DIMENSIONS = {"physical", "geographic", "capacity", "commercial", "regulatory"}


@pytest.fixture(scope="module")
def catalog():
    return load_project_catalog()


def saigon18_factory() -> FactoryProfile:
    # Large south-region factory co-located with the onsite Saigon18 project.
    return FactoryProfile.from_annuals(
        name="Saigon18 Factory",
        region="south",
        annual_consumption_kwh=184_000_000.0,
        peak_demand_kw=30_000.0,
        colocated_project_id="saigon18_onsite_solar_bess",
        evn_baseline_usc_kwh=7.8,
        voltage_level="medium_voltage_22kv_to_110kv",
    )


def ninhsim_factory() -> FactoryProfile:
    # Central-region offsite factory, not co-located with any onsite project.
    return FactoryProfile.from_annuals(
        name="Ninh Sim Factory",
        region="central",
        annual_consumption_kwh=120_000_000.0,
        peak_demand_kw=22_000.0,
        colocated_project_id=None,
        evn_baseline_usc_kwh=7.9,
    )


def micro_far_north_factory() -> FactoryProfile:
    # Tiny far-north factory: every project is too big and onsite ones aren't co-located.
    return FactoryProfile.from_annuals(
        name="Micro North Factory",
        region="north",
        annual_consumption_kwh=2_000_000.0,
        peak_demand_kw=500.0,
        colocated_project_id=None,
        evn_baseline_usc_kwh=8.0,
    )


def test_returns_project_match_objects_for_every_project(catalog):
    matches = match_projects_to_factory(saigon18_factory(), catalog)
    assert len(matches) == len(catalog)
    assert all(isinstance(m, ProjectMatch) for m in matches)


def test_results_sorted_by_overall_score_descending(catalog):
    matches = match_projects_to_factory(saigon18_factory(), catalog)
    scores = [m.overall_score for m in matches]
    assert scores == sorted(scores, reverse=True)


def test_all_dimensions_present_and_bounded(catalog):
    matches = match_projects_to_factory(saigon18_factory(), catalog)
    for m in matches:
        assert set(m.dimension_scores) == DIMENSIONS
        for dim, value in m.dimension_scores.items():
            assert 0.0 <= value <= 100.0, f"{m.project_id}.{dim}={value}"
        assert 0.0 <= m.overall_score <= 100.0


def test_default_weights_sum_to_one():
    assert set(DEFAULT_WEIGHTS) == DIMENSIONS
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


def test_saigon18_onsite_ranks_highest_physical_fit(catalog):
    matches = match_projects_to_factory(saigon18_factory(), catalog)
    by_physical = sorted(
        matches, key=lambda m: m.dimension_scores["physical"], reverse=True
    )
    assert by_physical[0].project_id == "saigon18_onsite_solar_bess"
    # And it should be the overall #1 match too (co-located, well-sized, savings).
    assert matches[0].project_id == "saigon18_onsite_solar_bess"
    assert matches[0].is_viable


def test_viable_offsite_matches_have_nonzero_scores_in_all_dimensions(catalog):
    matches = match_projects_to_factory(ninhsim_factory(), catalog)
    offsite = [m for m in matches if "BLOCKER" not in " ".join(m.flags)]
    assert offsite, "expected at least one non-blocked offsite match"
    for m in offsite:
        for dim, value in m.dimension_scores.items():
            assert value > 0.0, f"{m.project_id}.{dim} should be > 0"


def test_private_wire_project_blocked_for_offsite_factory(catalog):
    matches = {m.project_id: m for m in match_projects_to_factory(ninhsim_factory(), catalog)}
    saigon18 = matches["saigon18_onsite_solar_bess"]  # private_wire, not co-located
    assert any("BLOCKER" in f for f in saigon18.flags)
    assert saigon18.dimension_scores["geographic"] == 0.0
    assert not saigon18.is_viable


def test_colocated_onsite_project_not_blocked(catalog):
    matches = {m.project_id: m for m in match_projects_to_factory(saigon18_factory(), catalog)}
    saigon18 = matches["saigon18_onsite_solar_bess"]
    assert not any("BLOCKER" in f for f in saigon18.flags)
    assert saigon18.dimension_scores["geographic"] == 100.0


def test_no_viable_project_for_micro_far_north_factory(catalog):
    matches = match_projects_to_factory(micro_far_north_factory(), catalog)
    assert len(matches) == len(catalog)
    assert all(not m.is_viable for m in matches), [
        (m.project_id, m.overall_score, m.is_viable) for m in matches
    ]


def test_fit_explanation_is_nonempty_string(catalog):
    matches = match_projects_to_factory(saigon18_factory(), catalog)
    for m in matches:
        assert isinstance(m.fit_explanation, str) and m.fit_explanation.strip()


def test_physical_fit_from_profile_rewards_self_consumption():
    # A flat load that fully absorbs a solar bell curve should score higher than
    # a tiny load that wastes most of it.
    hours = list(range(24)) * 365
    solar = [max(0.0, 1000.0 * (1 - abs(h - 12) / 6.0)) if 6 <= h <= 18 else 0.0 for h in hours]
    big_load = [1200.0] * 8760
    tiny_load = [100.0] * 8760
    high = physical_fit_from_profile(big_load, solar, bess_power_kw=0.0)
    low = physical_fit_from_profile(tiny_load, solar, bess_power_kw=0.0)
    assert 0.0 <= low < high <= 100.0
