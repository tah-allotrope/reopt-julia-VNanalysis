"""Tests for two-part tariff (Decree 146/2025) corrected economics."""
import json
from pathlib import Path

import pytest

from reopt_pysam_vn.reopt.two_part_tariff import (
    build_trial_energy_rate_series,
    compute_two_part_impact,
    reprice_energy_series,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_reprice_energy_series_flat_profile():
    """Flat 1000 kW profile with constant rates should produce exact delta."""
    grid_import = [1000.0] * 8760
    baseline_rates = [2000.0] * 8760
    trial_rates = [1300.0] * 8760

    result = reprice_energy_series(grid_import, baseline_rates, trial_rates)

    assert result["baseline_energy_cost_vnd"] == 17_520_000_000.0
    assert result["trial_energy_cost_vnd"] == 11_388_000_000.0
    assert result["energy_delta_vnd"] == -6_132_000_000.0


def test_reprice_energy_series_length_mismatch():
    """Mismatched input lengths should raise ValueError."""
    with pytest.raises(ValueError, match="8760"):
        reprice_energy_series([1000.0] * 100, [2000.0] * 8760, [1300.0] * 8760)


def test_build_trial_energy_rate_series_real_tariff():
    """Trial rate series from real tariff data should have correct structure."""
    tariff_path = REPO_ROOT / "data" / "vietnam" / "vn_tariff_2025.json"
    tariff_data = json.loads(tariff_path.read_text(encoding="utf-8-sig"))["data"]

    trial_rates = build_trial_energy_rate_series(tariff_data)

    assert len(trial_rates) == 8760
    unique_rates = set(trial_rates)
    assert unique_rates == {873.5, 1292.5, 2206.5}


def test_compute_two_part_impact_high_load_factor():
    """High load factor (100% constant) profile should save money under two-part tariff."""
    grid_import = [1000.0] * 8760
    baseline_rates = [2000.0] * 8760
    trial_rates = [1300.0] * 8760
    capacity_charge = 235_414.0

    result = compute_two_part_impact(
        grid_import, baseline_rates, trial_rates, capacity_charge
    )

    assert result["energy_delta_vnd"] == -6_132_000_000.0
    assert result["annual_demand_charge_vnd"] == 2_824_968_000.0
    assert result["net_impact_vnd"] == -3_307_032_000.0
    # PHASE-05 Commit 2 unified two_part_tariff.py's exchange rate onto the
    # canonical 26,400 (was 26,000): -3_307_032_000 / 26_000 = -127_193.54;
    # -3_307_032_000 / 26_400 = -125_266.36 (see plans/2026-07-26-post-backlog-architecture-plan.md ASM-002).
    assert result["net_impact_usd"] == pytest.approx(-125_266.36, rel=1e-3)
    assert result["net_impact_vnd"] < 0


def test_compute_two_part_impact_low_load_factor():
    """Low load factor profile should lose money under two-part tariff."""
    grid_import = [10.0] * 8760
    grid_import[0] = 5000.0
    grid_import[720] = 5000.0
    grid_import[1440] = 5000.0
    grid_import[2160] = 5000.0
    grid_import[2880] = 5000.0
    grid_import[3600] = 5000.0
    grid_import[4320] = 5000.0
    grid_import[5040] = 5000.0
    grid_import[5760] = 5000.0
    grid_import[6480] = 5000.0
    grid_import[7200] = 5000.0
    grid_import[7920] = 5000.0

    baseline_rates = [2000.0] * 8760
    trial_rates = [1300.0] * 8760
    capacity_charge = 235_414.0

    result = compute_two_part_impact(
        grid_import, baseline_rates, trial_rates, capacity_charge
    )

    assert result["net_impact_vnd"] > 0
