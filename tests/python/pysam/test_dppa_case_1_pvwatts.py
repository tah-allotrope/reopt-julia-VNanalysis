from __future__ import annotations

from pathlib import Path

import pytest
from reopt_pysam_vn.integration.bridge import build_dppa_case_1_pvwatts_inputs
from reopt_pysam_vn.pysam.pvwatts_battery import (
    build_pvwatts_battery_single_owner_inputs,
    ensure_solar_resource_file,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _synthetic_results() -> dict:
    return {
        "status": "optimal",
        "PV": {
            "size_kw": 20_000.0,
            "year_one_energy_produced_kwh": 43_800_000.0,
            "electric_to_load_series_kw": [4_500.0] * 8760,
            "electric_to_grid_series_kw": [20.0] * 8760,
            "electric_to_storage_series_kw": [300.0] * 8760,
            "electric_curtailed_series_kw": [50.0] * 8760,
        },
        "Wind": {
            "size_kw": 0.0,
            "year_one_energy_produced_kwh": 0.0,
            "electric_to_load_series_kw": [0.0] * 8760,
            "electric_to_grid_series_kw": [0.0] * 8760,
        },
        "ElectricStorage": {
            "size_kw": 2_500.0,
            "size_kwh": 5_000.0,
            "initial_capital_cost": 1_250_000.0,
            "storage_to_load_series_kw": [260.0] * 8760,
        },
        "ElectricUtility": {
            "electric_to_load_series_kw": [6_000.0] * 8760,
        },
        "Financial": {
            "npv": 4_200_000.0,
            "analysis_years": 20,
            "owner_tax_rate_fraction": 0.0575,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.04,
            "initial_capital_costs": 16_250_000.0,
            "initial_capital_costs_after_incentives": 16_250_000.0,
        },
    }


def _synthetic_scenario() -> dict:
    return {
        "Site": {
            "latitude": 12.525729252783036,
            "longitude": 109.02003383567742,
        },
        "PV": {
            "om_cost_per_kw": 6.0,
            "tilt": 12.525729252783036,
            "azimuth": 180.0,
            "dc_ac_ratio": 1.2,
            "losses": 0.14,
            "location": "ground",
            "can_wholesale": False,
        },
        "ElectricStorage": {
            "om_cost_fraction_of_installed_cost": 0.01,
            "can_grid_charge": False,
            "min_duration_hours": 2.0,
            "max_duration_hours": 2.0,
        },
        "Financial": {
            "analysis_years": 20,
            "owner_tax_rate_fraction": 0.0575,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.04,
        },
        "_meta": {
            "contract_type": "private_wire",
        },
    }


def _synthetic_extracted() -> dict:
    return {
        "site": {
            "latitude": 12.525729252783036,
            "longitude": 109.02003383567742,
            "customer_type": "industrial",
            "region": "south",
            "voltage_level": "medium_voltage_22kv_to_110kv",
        },
        "loads_kw": [10_000.0] * 8760,
        "benchmark": {
            "annual_load_kwh": 87_600_000.0,
            "annual_load_gwh": 87.6,
            "weighted_evn_price_vnd_per_kwh": 2_000.0,
            "weighted_evn_price_usd_per_kwh": 2_000.0 / 26_400.0,
            "exchange_rate_vnd_per_usd": 26_400.0,
        },
        "evn_tariff": {
            "tou_energy_rates_usd_per_kwh": [2_000.0 / 26_400.0] * 8760,
        },
    }


def test_build_pvwatts_battery_single_owner_inputs_requires_matching_two_hour_storage():
    inputs = build_pvwatts_battery_single_owner_inputs(
        system_capacity_kw=20_000.0,
        battery_power_kw=2_500.0,
        battery_capacity_kwh=5_000.0,
        load_profile_kw=[10_000.0] * 8760,
        buy_rate_usd_per_kwh=[0.08] * 8760,
        sell_rate_usd_per_kwh=[0.0] * 8760,
        ppa_price_input_usd_per_kwh=1149.86 / 26_400.0,
        solar_resource_file="data/interim/pysam_resources/test.csv",
    )

    assert inputs.battery_duration_hours == pytest.approx(2.0)
    assert inputs.battery_can_grid_charge is False
    assert inputs.battery_dispatch_mode == "peak_shaving_look_ahead"


def test_build_dppa_case_1_pvwatts_inputs_maps_private_wire_strike_and_zero_grid_charge():
    inputs = build_dppa_case_1_pvwatts_inputs(
        reopt_results=_synthetic_results(),
        scenario=_synthetic_scenario(),
        extracted=_synthetic_extracted(),
        solar_resource_file="data/interim/pysam_resources/test.csv",
    )

    assert inputs.case_metadata["source_case"] == "ninhsim_dppa_case_1"
    assert inputs.case_metadata["contract_type"] == "private_wire"
    assert inputs.case_metadata[
        "year_one_private_wire_strike_vnd_per_kwh"
    ] == pytest.approx(1149.86)
    assert inputs.battery_power_kw == pytest.approx(2_500.0)
    assert inputs.battery_capacity_kwh == pytest.approx(5_000.0)
    assert inputs.battery_can_grid_charge is False
    assert inputs.sell_rate_usd_per_kwh[0] == 0.0


def test_ensure_solar_resource_file_returns_cached_path_when_present(tmp_path: Path):
    cached = tmp_path / "resource.csv"
    cached.write_text("meta\n", encoding="utf-8")

    resolved = ensure_solar_resource_file(
        latitude=12.5,
        longitude=109.0,
        cache_dir=tmp_path,
        force_download=False,
        cached_resource_file=cached,
    )

    assert resolved == cached


PySAM = pytest.importorskip("PySAM")


@pytest.mark.requires_pysam_resource
def test_run_pvwatts_battery_model_returns_canonical_result_shape():
    from reopt_pysam_vn.pysam.pvwatts_battery import (
        run_pvwatts_battery_single_owner_model,
    )

    resource_file = (
        REPO_ROOT
        / "data"
        / "interim"
        / "pysam_resources"
        / "ninhsim_himawari_2019_60min.csv"
    )
    if not resource_file.is_file():
        pytest.skip("cached Ninhsim weather resource not present")

    inputs = build_pvwatts_battery_single_owner_inputs(
        system_capacity_kw=1_000.0,
        battery_power_kw=500.0,
        battery_capacity_kwh=1_000.0,
        load_profile_kw=[800.0] * 8760,
        buy_rate_usd_per_kwh=[0.08] * 8760,
        sell_rate_usd_per_kwh=[0.0] * 8760,
        ppa_price_input_usd_per_kwh=0.0436,
        solar_resource_file=str(resource_file),
        analysis_years=20,
    )

    results = run_pvwatts_battery_single_owner_model(inputs)

    assert results["model"] == "PySAM PVWatts Battery Single Owner"
    assert results["status"] == "ok"
    assert results["energy_summary"][
        "annual_battery_charge_from_grid_kwh"
    ] == pytest.approx(
        0.0,
        abs=1e-6,
    )
    assert "equity_irr_fraction" in results["outputs"]
    assert len(results["annual_cashflows"]) == 20
