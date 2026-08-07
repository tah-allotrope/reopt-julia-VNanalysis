"""GAP-03 PHASE-03: end-to-end CLI and artifact tests.

Validates the artifact builder directly and drives the CLI wrapper as a
subprocess against the real case-study load files. Red/Green TDD.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from reopt_pysam_vn.integration.matching import (
    DEFAULT_WEIGHTS,
    FactoryProfile,
    build_match_artifact,
    match_projects_to_factory,
)
from reopt_pysam_vn.integration.project_catalog import load_project_catalog

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "scripts" / "python" / "integration" / "match_factory_to_projects.py"
CASE_DIR = REPO_ROOT / "scenarios" / "case_studies"

CASE_FILES = {
    "saigon18": CASE_DIR / "saigon18" / "2026-03-20_scenario-a_fixed-sizing_evntou.json",
    "ninhsim": CASE_DIR / "ninhsim" / "NinhsimSample.csv",
    "north_thuan": CASE_DIR / "north_thuan" / "north_thuan_scenario_a.json",
    "verdant": CASE_DIR / "verdant" / "Verdant.csv",
    "regina": CASE_DIR / "regina" / "Regina.xlsx",
    "emivest": CASE_DIR / "emivest" / "Emivest.csv",
}

REQUIRED_ARTIFACT_KEYS = {
    "schema",
    "match_timestamp",
    "factory_summary",
    "catalog_size",
    "scoring_weights",
    "matches",
}
DIMENSIONS = {"physical", "geographic", "capacity", "commercial", "regulatory"}


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_valid_artifact(artifact: dict) -> None:
    assert REQUIRED_ARTIFACT_KEYS.issubset(artifact), artifact.keys()
    assert artifact["catalog_size"] >= 1
    assert set(artifact["scoring_weights"]) == DIMENSIONS
    matches = artifact["matches"]
    assert matches, "expected at least one match"
    scores = [m["overall_score"] for m in matches]
    assert scores == sorted(scores, reverse=True)
    for m in matches:
        assert set(m["dimension_scores"]) == DIMENSIONS
        assert isinstance(m["fit_explanation"], str) and m["fit_explanation"].strip()
        assert "is_viable" in m


def test_build_match_artifact_structure():
    catalog = load_project_catalog()
    factory = FactoryProfile.from_annuals(
        name="Test Factory",
        region="south",
        annual_consumption_kwh=120_000_000.0,
        peak_demand_kw=20_000.0,
    )
    matches = match_projects_to_factory(factory, catalog)
    artifact = build_match_artifact(
        factory, matches, catalog_size=len(catalog), top_n=3, weights=DEFAULT_WEIGHTS
    )
    _assert_valid_artifact(artifact)
    assert artifact["catalog_size"] == len(catalog)
    assert len(artifact["matches"]) == 3
    assert artifact["factory_summary"]["name"] == "Test Factory"
    assert artifact["factory_summary"]["region"] == "south"


def test_cli_produces_valid_artifact(tmp_path):
    out = tmp_path / "matches.json"
    result = _run_cli(
        [
            "--factory",
            str(CASE_FILES["ninhsim"]),
            "--region",
            "south",
            "--output",
            str(out),
        ]
    )
    assert result.returncode == 0, result.stderr
    assert out.is_file()
    artifact = json.loads(out.read_text(encoding="utf-8"))
    _assert_valid_artifact(artifact)


def test_cli_top_n_limits_results(tmp_path):
    out = tmp_path / "top2.json"
    result = _run_cli(
        [
            "--factory",
            str(CASE_FILES["ninhsim"]),
            "--region",
            "south",
            "--top-n",
            "2",
            "--output",
            str(out),
        ]
    )
    assert result.returncode == 0, result.stderr
    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert len(artifact["matches"]) == 2


@pytest.mark.parametrize("case", sorted(CASE_FILES))
def test_cli_runs_for_each_case_study(case, tmp_path):
    out = tmp_path / f"{case}.json"
    result = _run_cli(
        ["--factory", str(CASE_FILES[case]), "--output", str(out)]
    )
    assert result.returncode == 0, f"{case}: {result.stderr}"
    artifact = json.loads(out.read_text(encoding="utf-8"))
    _assert_valid_artifact(artifact)
    assert artifact["factory_summary"]["annual_consumption_mwh"] > 0
