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
