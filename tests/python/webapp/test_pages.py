"""PHASE-04/05: server-rendered pages actually render (smoke tests)."""

_HOURS = 8760


def _onsite_results():
    return {
        "PV": {
            "size_kw": 3000.0,
            "electric_to_load_series_kw": [100.0] * _HOURS,
            "electric_to_grid_series_kw": [10.0] * _HOURS,
        },
        "Wind": {"size_kw": 0.0, "electric_to_load_series_kw": [], "electric_to_grid_series_kw": []},
        "ElectricStorage": {"size_kw": 1000.0, "size_kwh": 2000.0, "storage_to_load_series_kw": [20.0] * _HOURS},
        "ElectricUtility": {"electric_to_load_series_kw": [50.0] * _HOURS},
        "Financial": {"npv": 1_500_000.0, "lifecycle_capital_costs": 3_000_000.0, "year_one_bill_before_tax": 2_000_000.0},
    }


def test_runs_index_renders_empty(client):
    resp = client.get("/runs")
    assert resp.status_code == 200
    assert "No runs yet" in resp.text


def test_new_deal_form_renders_with_templates(client):
    resp = client.get("/deals/new")
    assert resp.status_code == 200
    assert "vn_industrial_pv_storage" in resp.text
    assert "New deal" in resp.text


def test_multipart_deal_submission_queues_a_background_solve(client):
    import io
    import time

    csv_text = "load_kw\n" + "\n".join(str(150.0) for _ in range(_HOURS))
    resp = client.post(
        "/api/deals",
        data={
            "case": "E2E_TEST",
            "mode": "onsite",
            "title": "E2E test deal",
            "site.region": "south",
            "site.customer_type": "industrial",
        },
        files={"load_file": ("load.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")},
    )
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]

    # No results were supplied, so this queues a live-solve job; the
    # `block_live_nrel_calls` fixture makes that solve fail fast (no network),
    # so the run should settle into `error` rather than hang.
    for _ in range(20):
        status = client.get(f"/api/runs/{run_id}").json()["status"]
        if status["state"] in ("done", "error"):
            break
        time.sleep(0.1)
    assert status["state"] == "error"
    assert "blocked" in status["message"]


def test_run_results_page_via_presolved_api_run(client):
    resp2 = client.post(
        "/api/runs",
        json={
            "deal_config": {"case": "E2E_TEST", "mode": "onsite", "title": "E2E via API"},
            "results": _onsite_results(),
            "extracted": {"loads_kw": [150.0] * _HOURS},
        },
    )
    assert resp2.status_code == 202
    run_id = resp2.json()["run_id"]

    run_page = client.get(f"/runs/{run_id}")
    assert run_page.status_code == 200
    assert "NPV" in run_page.text

    json_dl = client.get(f"/api/runs/{run_id}/result.json")
    assert json_dl.status_code == 200
    assert json_dl.json()["sizing"]["pv_kw"] == 3000.0

    html_dl = client.get(f"/api/runs/{run_id}/report.html")
    assert html_dl.status_code == 200
    assert "E2E via API" in html_dl.text


def test_run_detail_unknown_id_is_404(client):
    resp = client.get("/runs/does-not-exist")
    assert resp.status_code == 404


def test_compare_page_renders_with_no_selection(client):
    resp = client.get("/compare")
    assert resp.status_code == 200


def test_run_page_shows_context_map_when_site_coords_exist(client):
    resp = client.post(
        "/api/runs",
        json={
            "deal_config": {
                "case": "MAP_TEST",
                "mode": "onsite",
                "title": "Map context test",
                "site": {"latitude": 10.82, "longitude": 106.63, "region": "south"},
            },
            "results": _onsite_results(),
        },
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    run_page = client.get(f"/runs/{run_id}")
    assert run_page.status_code == 200
    assert 'id="context-map"' in run_page.text
    assert "initContextMap" in run_page.text


def test_run_page_shows_provenance_card_when_present(client):
    resp = client.post(
        "/api/runs",
        json={
            "deal_config": {"case": "PROV_TEST", "mode": "onsite", "title": "Provenance test"},
            "results": _onsite_results(),
        },
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    storage = client.app.state.storage
    storage.write_provenance(
        run_id,
        {
            "run_id": run_id,
            "created_at": "20260718T000000000000",
            "solver": "nrel_api",
            "nrel_key_fingerprint": None,
            "solve_hash": "x",
            "cache_hit": False,
            "cached_from_run_id": None,
            "policy_data_versions": {"export_rules": "2026.1"},
            "wall_time_seconds": 12.34,
            "pysam_available": True,
            "package_version": "0.1.0",
        },
    )

    run_page = client.get(f"/runs/{run_id}")
    assert run_page.status_code == 200
    assert "About this run" in run_page.text
    assert "nrel_api" in run_page.text
    assert "2026.1" in run_page.text


def test_run_page_hides_provenance_card_when_absent(client):
    resp = client.post(
        "/api/runs",
        json={
            "deal_config": {"case": "NO_PROV_TEST", "mode": "onsite", "title": "No provenance test"},
            "results": _onsite_results(),
        },
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    run_page = client.get(f"/runs/{run_id}")
    assert run_page.status_code == 200
    assert "About this run" not in run_page.text


def test_run_page_hides_context_map_when_site_coords_missing(client):
    resp = client.post(
        "/api/runs",
        json={
            "deal_config": {"case": "NO_MAP_TEST", "mode": "onsite", "title": "No map test"},
            "results": _onsite_results(),
        },
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    run_page = client.get(f"/runs/{run_id}")
    assert run_page.status_code == 200
    assert 'id="context-map"' not in run_page.text
    assert "initContextMap" not in run_page.text
