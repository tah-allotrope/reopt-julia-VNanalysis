"""Shared fixtures for webapp tests: an isolated storage root per test."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))


@pytest.fixture()
def storage_root(tmp_path, monkeypatch):
    root = tmp_path / "webapp_runs"
    monkeypatch.setenv("REOPT_PYSAM_VN_WEBAPP_RUNS_DIR", str(root))
    return root


@pytest.fixture(autouse=True)
def block_live_nrel_calls(monkeypatch):
    """CON-005: no test may hit the live NREL API, even from the background
    solve worker. The real ``NREL_API.env`` key is present in this repo, so a
    test that forgets to mock ``solve_onsite_via_nrel`` must fail loudly
    rather than silently placing a real API call."""
    from reopt_pysam_vn.webapp import service

    def _blocked(*_args, **_kwargs):
        raise RuntimeError("live NREL API calls are blocked in tests; mock service.solve_onsite_via_nrel")

    monkeypatch.setattr(service, "solve_onsite_via_nrel", _blocked)


@pytest.fixture()
def client(storage_root):
    from reopt_pysam_vn.webapp import create_app

    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as c:
        yield c
