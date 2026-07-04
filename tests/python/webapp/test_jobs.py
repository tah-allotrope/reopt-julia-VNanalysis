"""PHASE-02: background job manager - state transitions, error path, cache."""

import time

_HOURS = 8760


def _fake_reopt_results():
    return {
        "PV": {
            "size_kw": 500.0,
            "electric_to_load_series_kw": [10.0] * _HOURS,
            "electric_to_grid_series_kw": [0.0] * _HOURS,
        },
        "Wind": {"size_kw": 0.0, "electric_to_load_series_kw": [], "electric_to_grid_series_kw": []},
        "ElectricStorage": {"size_kw": 0.0, "size_kwh": 0.0, "storage_to_load_series_kw": []},
        "ElectricUtility": {"electric_to_load_series_kw": [5.0] * _HOURS},
        "Financial": {"npv": 10.0, "lifecycle_capital_costs": 20.0},
    }


def _deal_config(case="JOB_TEST"):
    return {
        "case": case,
        "mode": "onsite",
        "title": "Job test",
        "site": {"region": "south", "customer_type": "industrial"},
        "plant": {"capacity_mwp": 1.0},
        "load": {"loads_kw": [10.0] * _HOURS},
    }


def _wait_for_terminal(client, run_id, timeout=5.0):
    deadline = time.time() + timeout
    status = None
    while time.time() < deadline:
        status = client.get(f"/api/runs/{run_id}").json()["status"]
        if status["state"] in ("done", "error"):
            return status
        time.sleep(0.05)
    return status


def test_background_solve_reaches_done_when_mocked(client, monkeypatch):
    from reopt_pysam_vn.webapp import service

    monkeypatch.setattr(service, "solve_onsite_via_nrel", lambda deal: _fake_reopt_results())

    resp = client.post("/api/runs", json={"deal_config": _deal_config()})
    run_id = resp.json()["run_id"]

    status = _wait_for_terminal(client, run_id)
    assert status["state"] == "done"
    result = client.get(f"/api/runs/{run_id}").json()["result"]
    assert result["sizing"]["pv_kw"] == 500.0


def test_second_identical_deal_reuses_cached_solve(client, monkeypatch):
    from reopt_pysam_vn.webapp import service

    calls = {"n": 0}

    def _fake_solve(deal):
        calls["n"] += 1
        return _fake_reopt_results()

    monkeypatch.setattr(service, "solve_onsite_via_nrel", _fake_solve)

    resp1 = client.post("/api/runs", json={"deal_config": _deal_config("CACHE_A")})
    run_id_1 = resp1.json()["run_id"]
    _wait_for_terminal(client, run_id_1)

    resp2 = client.post("/api/runs", json={"deal_config": _deal_config("CACHE_A")})
    run_id_2 = resp2.json()["run_id"]
    status2 = _wait_for_terminal(client, run_id_2)

    assert status2["state"] == "done"
    assert calls["n"] == 1, "second identical solve should reuse the cached NREL result"


def test_force_resolve_bypasses_cache(client, monkeypatch):
    from reopt_pysam_vn.webapp import service

    calls = {"n": 0}

    def _fake_solve(deal):
        calls["n"] += 1
        return _fake_reopt_results()

    monkeypatch.setattr(service, "solve_onsite_via_nrel", _fake_solve)

    resp1 = client.post("/api/runs", json={"deal_config": _deal_config("CACHE_B")})
    _wait_for_terminal(client, resp1.json()["run_id"])

    resp2 = client.post(
        "/api/runs", json={"deal_config": _deal_config("CACHE_B"), "force_resolve": True}
    )
    _wait_for_terminal(client, resp2.json()["run_id"])

    assert calls["n"] == 2


def test_solve_failure_marks_run_error_and_worker_survives(client, monkeypatch):
    from reopt_pysam_vn.webapp import service

    def _boom(deal):
        raise RuntimeError("NREL job failed with status: infeasible")

    monkeypatch.setattr(service, "solve_onsite_via_nrel", _boom)

    resp = client.post("/api/runs", json={"deal_config": _deal_config("FAIL_CASE")})
    run_id = resp.json()["run_id"]
    status = _wait_for_terminal(client, run_id)
    assert status["state"] == "error"
    assert "infeasible" in status["message"]

    # worker thread must still process the next job after an error
    monkeypatch.setattr(service, "solve_onsite_via_nrel", lambda deal: _fake_reopt_results())
    resp2 = client.post("/api/runs", json={"deal_config": _deal_config("AFTER_FAIL")})
    status2 = _wait_for_terminal(client, resp2.json()["run_id"])
    assert status2["state"] == "done"
