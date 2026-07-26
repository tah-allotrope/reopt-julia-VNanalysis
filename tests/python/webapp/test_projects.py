"""PHASE-01: project-catalog API tests (red-first TDD)."""

from __future__ import annotations

import json


def test_api_projects_returns_catalog(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "projects" in body
    projects = body["projects"]
    assert len(projects) >= 1
    for p in projects:
        assert "project_id" in p
        assert "name" in p
        assert "technology" in p
        assert "capacity_mw" in p
        assert "status" in p
        assert "indicative_strike_usc_kwh" in p
        loc = p["location"]
        assert "lat" in loc
        assert "lon" in loc
        assert "province" in loc
        assert "region" in loc


def test_api_projects_excludes_catalog_schema(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    ids = {p["project_id"] for p in resp.json()["projects"]}
    assert "catalog_schema" not in ids


def test_list_projects_skips_schema_and_missing_coords(tmp_path, monkeypatch):
    from reopt_pysam_vn.webapp import projects as projects_mod

    proj_dir = tmp_path / "projects"
    proj_dir.mkdir()

    good = {
        "project_id": "good_proj",
        "name": "Good Project",
        "technology": "solar",
        "capacity_mw": 10.0,
        "status": "operational",
        "indicative_strike_usc_kwh": 5.5,
        "location": {"lat": 10.0, "lon": 106.0, "province": "Test", "region": "south"},
    }
    missing_lat = {
        "project_id": "bad_proj",
        "name": "Bad Project",
        "technology": "wind",
        "capacity_mw": 20.0,
        "status": "prospective",
        "indicative_strike_usc_kwh": 6.5,
        "location": {"lon": 106.0, "province": "Test", "region": "central"},
    }

    (proj_dir / "good_proj.json").write_text(json.dumps(good), encoding="utf-8")
    (proj_dir / "bad_proj.json").write_text(json.dumps(missing_lat), encoding="utf-8")
    (proj_dir / "catalog_schema.json").write_text(json.dumps({"schema": True}), encoding="utf-8")

    monkeypatch.setattr(projects_mod, "_PROJECTS_DIR", proj_dir)
    result = projects_mod.list_projects()
    assert len(result) == 1
    assert result[0]["project_id"] == "good_proj"
