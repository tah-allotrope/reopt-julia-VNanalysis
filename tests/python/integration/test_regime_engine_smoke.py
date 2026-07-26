"""Smoke coverage for the Vietnam regulatory regime matrix runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.regime_runner import (  # noqa: E402
    build_regime_matrix,
    canonicalize_for_hash,
    scenario_hash,
)


@pytest.mark.requires_julia
def test_regime_matrix_no_solve_writes_complete_artifacts(tmp_path: Path):
    scenario_path = REPO_ROOT / "scenarios" / "templates" / "vn_industrial_pv_storage.json"
    _assumption_dir = REPO_ROOT / "scenarios" / "regime_engine" / "assumption_sets"

    runs = build_regime_matrix(
        scenario_path=scenario_path,
        regime_ids=["decision_963_2026_current", "decree146_two_part_trial_2026"],
        assumption_set_ids=["base", "capacity_payment_preview"],
        generated_root=tmp_path / "generated",
        result_store_root=tmp_path / "results",
        solve=False,
    )

    assert len(runs) == 4
    first = runs[0]
    required = {
        "generated_scenario_path",
        "result_dir",
        "input_path",
        "resolved_regime_path",
        "summary_path",
        "manifest_path",
        "scenario_hash",
    }
    assert required.issubset(first.keys())

    manifest = json.loads(Path(first["manifest_path"]).read_text(encoding="utf-8"))
    summary = json.loads(Path(first["summary_path"]).read_text(encoding="utf-8"))
    resolved = json.loads(Path(first["resolved_regime_path"]).read_text(encoding="utf-8"))
    scenario = json.loads(Path(first["generated_scenario_path"]).read_text(encoding="utf-8"))

    assert manifest["status"] == "scenario_built_no_solve"
    assert manifest["regime_id"] == scenario["_meta"]["resolved_regime_id"]
    assert manifest["assumption_set_id"] in {"base", "capacity_payment_preview"}
    assert summary["status"] == manifest["status"]
    assert resolved["regime_id"] == manifest["regime_id"]
    assert Path(first["input_path"]).is_file()


def test_scenario_hash_is_stable_for_same_materialized_input(tmp_path: Path):
    canonical = canonicalize_for_hash(
        {
            "regime_id": "decision_963_2026_current",
            "assumption_set_id": "base",
            "scenario": {"ElectricLoad": {"annual_kwh": 1000}, "_meta": {"skip": True}},
        }
    )

    first = scenario_hash(canonical)
    second = scenario_hash(canonical)

    assert first == second
    assert len(first) == 16


@pytest.mark.requires_julia
def test_cached_run_is_reused_when_manifest_is_successful(tmp_path: Path):
    scenario_path = REPO_ROOT / "scenarios" / "templates" / "vn_industrial_pv_storage.json"

    first_runs = build_regime_matrix(
        scenario_path=scenario_path,
        regime_ids=["decision_963_2026_current"],
        assumption_set_ids=["base"],
        generated_root=tmp_path / "generated",
        result_store_root=tmp_path / "results",
        solve=False,
    )

    second_runs = build_regime_matrix(
        scenario_path=scenario_path,
        regime_ids=["decision_963_2026_current"],
        assumption_set_ids=["base"],
        generated_root=tmp_path / "generated",
        result_store_root=tmp_path / "results",
        solve=False,
    )

    first_manifest = json.loads(Path(first_runs[0]["manifest_path"]).read_text(encoding="utf-8"))
    second_manifest = json.loads(Path(second_runs[0]["manifest_path"]).read_text(encoding="utf-8"))

    assert first_runs[0]["scenario_hash"] == second_runs[0]["scenario_hash"]
    assert second_manifest["cache_hit"] is True
    assert second_manifest["status"] == first_manifest["status"]
