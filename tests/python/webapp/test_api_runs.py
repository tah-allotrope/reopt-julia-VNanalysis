"""PHASE-01: JSON API over the analysis package (pre-solved / deterministic path)."""

_HOURS = 8760


def _onsite_results():
    return {
        "PV": {
            "size_kw": 3000.0,
            "electric_to_load_series_kw": [100.0] * _HOURS,
            "electric_to_grid_series_kw": [10.0] * _HOURS,
        },
        "Wind": {"size_kw": 0.0, "electric_to_load_series_kw": [], "electric_to_grid_series_kw": []},
        "ElectricStorage": {
            "size_kw": 1000.0,
            "size_kwh": 2000.0,
            "storage_to_load_series_kw": [20.0] * _HOURS,
        },
        "ElectricUtility": {"electric_to_load_series_kw": [50.0] * _HOURS},
        "Financial": {
            "npv": 1_500_000.0,
            "lifecycle_capital_costs": 3_000_000.0,
            "year_one_bill_before_tax": 2_000_000.0,
        },
    }


def _onsite_extracted():
    return {"loads_kw": [170.0] * _HOURS}


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_onsite_run_with_presolved_results_matches_library_call(client):
    from reopt_pysam_vn.analysis.onsite import run_onsite
    from reopt_pysam_vn.analysis.types import DealConfig

    deal_config = {
        "case": "TEST_ONSITE",
        "mode": "onsite",
        "title": "Test onsite",
        "contract": {"target_delivered_fraction": 0.6},
    }
    resp = client.post(
        "/api/runs",
        json={
            "deal_config": deal_config,
            "results": _onsite_results(),
            "extracted": _onsite_extracted(),
        },
    )
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]

    status_resp = client.get(f"/api/runs/{run_id}")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"]["state"] == "done"

    expected = run_onsite(
        DealConfig.from_dict(deal_config),
        results=_onsite_results(),
        extracted=_onsite_extracted(),
    ).to_dict()
    assert body["result"] == expected


def test_list_runs_returns_created_run(client):
    deal_config = {"case": "TEST_ONSITE", "mode": "onsite", "title": "Listed deal"}
    resp = client.post(
        "/api/runs",
        json={"deal_config": deal_config, "results": _onsite_results(), "extracted": _onsite_extracted()},
    )
    run_id = resp.json()["run_id"]
    listing = client.get("/api/runs").json()["runs"]
    assert any(r["run_id"] == run_id for r in listing)


def test_invalid_mode_returns_422(client):
    resp = client.post(
        "/api/runs",
        json={"deal_config": {"case": "BAD", "mode": "not_a_mode"}},
    )
    assert resp.status_code == 422
    assert "mode" in resp.json()["detail"]


def test_get_unknown_run_returns_404(client):
    resp = client.get("/api/runs/does-not-exist")
    assert resp.status_code == 404


def test_get_run_with_traversal_run_id_returns_404(client):
    resp = client.get("/api/runs/%2e%2e%2f%2e%2e")
    assert resp.status_code == 404


def test_onsite_without_results_or_solve_queues_for_background_solve(client):
    deal_config = {"case": "TEST_ONSITE_FRESH", "mode": "onsite", "title": "Fresh deal"}
    resp = client.post("/api/runs", json={"deal_config": deal_config})
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]
    # `block_live_nrel_calls` (conftest, CON-005) prevents an actual network
    # call; the job still legitimately passes through queued/solving first.
    status = client.get(f"/api/runs/{run_id}").json()["status"]
    assert status["state"] in ("queued", "solving", "error")


def test_offsite_dppa_case_1_run_reaches_done(client):
    """A second registered offsite case reaches ``done`` rather than a 422
    ``OrchestratorNotRegisteredError`` (PHASE-04). Case 1 consumes a REopt
    ``results`` dict and its ``scenario``; those ride on the deal config and
    land in ``DealConfig.raw``, which ``run_offsite_dppa`` resolves per S2."""
    _CASE_1_RESULTS = {
        "status": "optimal",
        "PV": {
            "size_kw": 20_000.0,
            "year_one_energy_produced_kwh": 43_800_000.0,
            "electric_to_load_series_kw": [4_500.0] * _HOURS,
            "electric_to_grid_series_kw": [20.0] * _HOURS,
            "electric_to_storage_series_kw": [300.0] * _HOURS,
            "electric_curtailed_series_kw": [50.0] * _HOURS,
        },
        "Wind": {
            "size_kw": 0.0,
            "year_one_energy_produced_kwh": 0.0,
            "electric_to_load_series_kw": [0.0] * _HOURS,
            "electric_to_grid_series_kw": [0.0] * _HOURS,
        },
        "ElectricStorage": {
            "size_kw": 2_500.0,
            "size_kwh": 5_000.0,
            "storage_to_load_series_kw": [260.0] * _HOURS,
        },
        "ElectricUtility": {
            "electric_to_load_series_kw": [6_000.0] * _HOURS,
        },
        "Financial": {
            "npv": 4_200_000.0,
            "analysis_years": 20,
            "owner_discount_rate_fraction": 0.08,
            "offtaker_discount_rate_fraction": 0.10,
        },
    }
    deal_config = {
        "case": "DPPA_CASE_1_NINHSIM",
        "mode": "offsite_dppa",
        "title": "Ninhsim DPPA Case 1",
        "site": {"region": "central"},
        "results": _CASE_1_RESULTS,
        "scenario": {"Site": {}, "_meta": {"contract_type": "private_wire"}},
    }
    resp = client.post(
        "/api/runs",
        json={
            "deal_config": deal_config,
            "extracted": {
                "loads_kw": [100.0] * _HOURS,
                "benchmark": {"annual_load_gwh": 200.0},
                "site": {
                    "region": "south",
                    "customer_type": "industrial",
                    "voltage_level": "medium_voltage_22kv_to_110kv",
                },
            },
        },
    )
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]

    body = client.get(f"/api/runs/{run_id}").json()
    assert body["status"]["state"] == "done", body["status"]
    assert body["result"]["case"] == "DPPA_CASE_1_NINHSIM"


# ---------------------------------------------------------------------------
# PHASE-02: `results` / `scenario` in the POST payload are forwarded, and a
# missing required input lands in `error` (MISSING_INPUTS) — never a dangling
# `queued` run.
# ---------------------------------------------------------------------------


def _case_1_results():
    return {
        "status": "optimal",
        "PV": {
            "size_kw": 20_000.0,
            "year_one_energy_produced_kwh": 43_800_000.0,
            "electric_to_load_series_kw": [4_500.0] * _HOURS,
            "electric_to_grid_series_kw": [20.0] * _HOURS,
            "electric_to_storage_series_kw": [300.0] * _HOURS,
            "electric_curtailed_series_kw": [50.0] * _HOURS,
        },
        "Wind": {
            "size_kw": 0.0,
            "year_one_energy_produced_kwh": 0.0,
            "electric_to_load_series_kw": [0.0] * _HOURS,
            "electric_to_grid_series_kw": [0.0] * _HOURS,
        },
        "ElectricStorage": {
            "size_kw": 2_500.0,
            "size_kwh": 5_000.0,
            "storage_to_load_series_kw": [260.0] * _HOURS,
        },
        "ElectricUtility": {"electric_to_load_series_kw": [6_000.0] * _HOURS},
        "Financial": {"npv": 4_200_000.0, "analysis_years": 20},
    }


def _case_1_extracted():
    return {
        "loads_kw": [100.0] * _HOURS,
        "benchmark": {"annual_load_gwh": 200.0},
        "site": {
            "region": "south",
            "customer_type": "industrial",
            "voltage_level": "medium_voltage_22kv_to_110kv",
        },
    }


def _case_1_scenario():
    return {"Site": {}, "_meta": {"contract_type": "private_wire"}}


def test_offsite_case_1_payload_results_and_scenario_reach_done(client):
    deal_config = {
        "case": "DPPA_CASE_1_NINHSIM",
        "mode": "offsite_dppa",
        "title": "Payload-forwarded case 1",
        "site": {"region": "central"},
    }
    resp = client.post(
        "/api/runs",
        json={
            "deal_config": deal_config,
            "extracted": _case_1_extracted(),
            "results": _case_1_results(),
            "scenario": _case_1_scenario(),
        },
    )
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]
    body = client.get(f"/api/runs/{run_id}").json()
    assert body["status"]["state"] == "done", body["status"]
    assert body["result"]["case"] == "DPPA_CASE_1_NINHSIM"


def test_offsite_case_1_missing_results_marks_error_not_queued(client):
    deal_config = {
        "case": "DPPA_CASE_1_NINHSIM",
        "mode": "offsite_dppa",
        "title": "Missing results",
        "site": {"region": "central"},
    }
    resp = client.post(
        "/api/runs",
        json={
            "deal_config": deal_config,
            "extracted": _case_1_extracted(),
            "scenario": _case_1_scenario(),
        },
    )
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]
    body = client.get(f"/api/runs/{run_id}").json()
    status = body["status"]
    assert status["state"] == "error", status
    assert status["state"] != "queued", "regression: run stranded in `queued`"
    assert status["error_code"] == "MISSING_INPUTS"
    assert "`results`" in status["message"]


def _generic_extracted():
    return {
        "loads_kw": [1000.0] * _HOURS,
        "generation_kw": [500.0] * _HOURS,
        "evn_tariff": {"tou_energy_rates_vnd_per_kwh": [2000.0] * _HOURS},
        "benchmark": {
            "weighted_evn_price_vnd_per_kwh": 2000.0,
            "wholesale_rate_vnd_per_kwh": 671.0,
        },
    }


def test_offsite_unregistered_case_reaches_done_via_generic(client):
    deal_config = {
        "case": "MY_NEW_DEAL",
        "mode": "offsite_dppa",
        "title": "Generic",
        "contract": {"settlement_mechanism": "physical", "strike_vnd_per_kwh": 1200.0},
    }
    resp = client.post(
        "/api/runs",
        json={"deal_config": deal_config, "extracted": _generic_extracted()},
    )
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]
    body = client.get(f"/api/runs/{run_id}").json()
    assert body["status"]["state"] == "done", body["status"]
    assert body["result"]["case"] == "MY_NEW_DEAL"
    assert body["result"]["quality"]["orchestrator"] == "generic_vn_dppa"
