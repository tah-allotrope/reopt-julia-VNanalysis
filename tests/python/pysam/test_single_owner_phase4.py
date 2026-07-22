import json
from pathlib import Path

import pytest

from reopt_pysam_vn.integration.bridge import (
    build_ninhsim_single_owner_inputs,
    build_ninhsim_solar_storage_single_owner_inputs,
)
from reopt_pysam_vn.pysam.single_owner import (
    build_single_owner_inputs,
    run_single_owner_model,
)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
NINHSIM_REOPT = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "ninhsim"
    / "2026-04-01_ninhsim_scenario-b_optimized-cppa_reopt-results.json"
)
NINHSIM_SCENARIO = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "ninhsim"
    / "2026-04-01_ninhsim_scenario-b_optimized-cppa.json"
)
NINHSIM_MEMO = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-02_ninhsim-commercial-candidate-memo.json"
)


def _synthetic_solar_storage_results() -> dict:
    return {
        "status": "optimal",
        "PV": {
            "size_kw": 24_000.0,
            "year_one_energy_produced_kwh": 70_000_000.0,
            "electric_to_load_series_kw": [8_000.0] * 8760,
            "electric_to_grid_series_kw": [2_000.0] * 8760,
        },
        "Wind": {
            "size_kw": 0.0,
            "year_one_energy_produced_kwh": 0.0,
            "electric_to_load_series_kw": [0.0] * 8760,
            "electric_to_grid_series_kw": [0.0] * 8760,
        },
        "ElectricStorage": {
            "size_kw": 6_000.0,
            "size_kwh": 24_000.0,
            "initial_capital_cost": 4_800_000.0,
            "storage_to_load_series_kw": [2_000.0] * 8760,
        },
        "ElectricUtility": {
            "electric_to_load_series_kw": [0.0] * 8760,
        },
        "Financial": {
            "npv": 9_000_000.0,
            "analysis_years": 20,
            "owner_tax_rate_fraction": 0.0575,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.04,
            "initial_capital_costs": 22_800_000.0,
            "initial_capital_costs_after_incentives": 22_800_000.0,
        },
    }


def _synthetic_solar_storage_scenario() -> dict:
    return {
        "Site": {
            "latitude": 12.525729252783036,
            "longitude": 109.02003383567742,
            "renewable_electricity_min_fraction": 0.60,
            "include_grid_renewable_fraction_in_RE_constraints": False,
            "include_exported_renewable_electricity_in_total": False,
        },
        "PV": {"om_cost_per_kw": 6.0},
        "Wind": {"om_cost_per_kw": 27.0},
        "ElectricStorage": {"om_cost_fraction_of_installed_cost": 0.01},
        "Financial": {
            "analysis_years": 20,
            "owner_tax_rate_fraction": 0.0575,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
            "elec_cost_escalation_rate_fraction": 0.05,
            "om_cost_escalation_rate_fraction": 0.04,
        },
        "_meta": {
            "requested_renewable_delivered_fraction_of_load": 0.60,
        },
    }


def _synthetic_extracted() -> dict:
    return {
        "loads_kw": [10_000.0] * 8760,
        "benchmark": {
            "annual_load_kwh": 87_600_000.0,
            "annual_load_gwh": 87.6,
            "weighted_evn_price_vnd_per_kwh": 2_000.0,
            "weighted_evn_price_usd_per_kwh": 2_000.0 / 26_400.0,
            "exchange_rate_vnd_per_usd": 26_400.0,
            "wholesale_rate_vnd_per_kwh": 671.0,
            "wholesale_rate_usd_per_kwh": 671.0 / 26_400.0,
        },
        "evn_tariff": {
            "tou_energy_rates_usd_per_kwh": [2_000.0 / 26_400.0] * 8760,
        },
    }


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.requires_artifacts
def test_build_ninhsim_single_owner_inputs_uses_recommended_candidate_band():
    inputs = build_ninhsim_single_owner_inputs(
        reopt_results=_load_json(NINHSIM_REOPT),
        scenario=_load_json(NINHSIM_SCENARIO),
        commercial_memo=_load_json(NINHSIM_MEMO),
    )

    assert inputs.metadata["recommended_band_label"] == "5% below ceiling"
    assert inputs.metadata["source_case"] == "ninhsim"
    assert inputs.system_capacity_kw == pytest.approx(54_282.8948, abs=1e-3)
    assert inputs.annual_generation_kwh == pytest.approx(138_177_842.921, abs=1e-3)
    assert inputs.installed_cost_usd == pytest.approx(65_029_300.9089, abs=1e-3)
    assert inputs.fixed_om_usd_per_year == pytest.approx(
        14_282.8948 * 6.0 + 40_000.0 * 27.0 + 317_130.0 * 0.01,
        abs=1e-3,
    )
    assert inputs.ppa_price_input_usd_per_kwh == pytest.approx(
        1934.4978824895795 / 26_400.0,
        abs=1e-12,
    )
    assert len(inputs.generation_profile_kw) == 8760


@pytest.mark.requires_artifacts
def test_build_ninhsim_single_owner_inputs_preserves_explicit_zero_escalation():
    scenario = _load_json(NINHSIM_SCENARIO)
    scenario["Financial"]["elec_cost_escalation_rate_fraction"] = 0.0
    scenario["Financial"]["om_cost_escalation_rate_fraction"] = 0.0

    inputs = build_ninhsim_single_owner_inputs(
        reopt_results=_load_json(NINHSIM_REOPT),
        scenario=scenario,
        commercial_memo=_load_json(NINHSIM_MEMO),
    )

    assert inputs.ppa_escalation_rate_fraction == 0.0
    assert inputs.om_escalation_rate_fraction == 0.0


@pytest.mark.requires_artifacts
def test_build_ninhsim_single_owner_inputs_rejects_mismatched_hourly_series():
    reopt_results = _load_json(NINHSIM_REOPT)
    reopt_results["Wind"]["electric_to_load_series_kw"] = reopt_results["Wind"][
        "electric_to_load_series_kw"
    ][:-1]

    with pytest.raises(ValueError, match="length mismatch"):
        build_ninhsim_single_owner_inputs(
            reopt_results=reopt_results,
            scenario=_load_json(NINHSIM_SCENARIO),
            commercial_memo=_load_json(NINHSIM_MEMO),
        )


def test_build_ninhsim_solar_storage_single_owner_inputs_uses_blended_realized_price():
    inputs = build_ninhsim_solar_storage_single_owner_inputs(
        reopt_results=_synthetic_solar_storage_results(),
        scenario=_synthetic_solar_storage_scenario(),
        extracted=_synthetic_extracted(),
    )

    assert inputs.metadata["source_case"] == "ninhsim_60pct_solar_storage"
    assert inputs.metadata["requested_target_fraction"] == pytest.approx(0.60)
    assert inputs.metadata["year_one_customer_price_vnd_per_kwh"] == pytest.approx(
        1900.0
    )
    assert inputs.metadata["year_one_merchant_price_vnd_per_kwh"] == pytest.approx(
        671.0
    )
    assert inputs.metadata["year_one_realized_price_vnd_per_kwh"] < 1900.0
    assert inputs.system_capacity_kw == pytest.approx(24_000.0)
    assert inputs.annual_generation_kwh == pytest.approx(105_120_000.0)
    assert len(inputs.generation_profile_kw) == 8760


def test_build_ninhsim_solar_storage_single_owner_inputs_rejects_missing_pv_delivery_series():
    reopt_results = _synthetic_solar_storage_results()
    reopt_results["PV"]["electric_to_load_series_kw"] = []

    with pytest.raises(ValueError, match=r"PV\.electric_to_load_series_kw"):
        build_ninhsim_solar_storage_single_owner_inputs(
            reopt_results=reopt_results,
            scenario=_synthetic_solar_storage_scenario(),
            extracted=_synthetic_extracted(),
        )


PySAM = pytest.importorskip("PySAM")


def test_run_single_owner_model_returns_canonical_result_shape():
    inputs = build_single_owner_inputs(system_capacity_kw=1000)

    results = run_single_owner_model(inputs)

    assert results["model"] == "PySAM Single Owner"
    assert results["status"] == "ok"
    assert isinstance(results["outputs"]["project_return_aftertax_npv_usd"], float)
    assert len(results["annual_cashflows"]) == inputs.analysis_years
    assert results["annual_cashflows"][0]["year"] == 1
    assert "project_return_aftertax_irr_fraction" in results["outputs"]


@pytest.mark.requires_artifacts
def test_run_single_owner_model_for_ninhsim_preserves_candidate_metadata():
    inputs = build_ninhsim_single_owner_inputs(
        reopt_results=_load_json(NINHSIM_REOPT),
        scenario=_load_json(NINHSIM_SCENARIO),
        commercial_memo=_load_json(NINHSIM_MEMO),
    )

    results = run_single_owner_model(inputs)

    assert results["case"]["source_case"] == "ninhsim"
    assert results["case"]["recommended_band_label"] == "5% below ceiling"
    assert results["case"]["year_one_ppa_price_vnd_per_kwh"] == pytest.approx(
        1934.4978824895795,
        abs=1e-9,
    )
    assert results["outputs"]["min_dscr"] == pytest.approx(
        results["outputs"]["min_dscr"]
    )
    assert len(results["annual_cashflows"]) == inputs.analysis_years
