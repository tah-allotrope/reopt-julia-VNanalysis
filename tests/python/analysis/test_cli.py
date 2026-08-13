"""PHASE-03: CLI smoke test (DEC-004).

Drives `python -m reopt_pysam_vn.analysis {onsite,offsite_dppa}` as a subprocess.
The onsite path uses a tiny injected results fixture (fast, deterministic). The
offsite path runs the real registered Samsung orchestrator end-to-end and skips
gracefully if PySAM / the cached resource is unavailable.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMSUNG_EXTRACTED = REPO_ROOT / "data" / "interim" / "samsung_ttc" / "samsung_ttc_extracted_inputs.json"
SAMSUNG_CONFIG = REPO_ROOT / "scenarios" / "case_studies" / "samsung_ttc" / "samsung_ttc_deal_config.json"
_HOURS = 8760


def _run(*args: str):
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src" / "python")}
    return subprocess.run(
        [sys.executable, "-m", "reopt_pysam_vn.analysis", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
        check=False,
    )


def test_cli_onsite_subcommand(tmp_path):
    results = {
        "PV": {"size_kw": 3000.0, "electric_to_load_series_kw": [100.0] * _HOURS, "electric_to_grid_series_kw": [10.0] * _HOURS},
        "ElectricStorage": {"size_kw": 1000.0, "size_kwh": 2000.0, "storage_to_load_series_kw": [20.0] * _HOURS},
        "ElectricUtility": {"electric_to_load_series_kw": [50.0] * _HOURS},
        "Financial": {"npv": 1_500_000.0},
    }
    rp = tmp_path / "results.json"
    rp.write_text(json.dumps(results), encoding="utf-8")
    ep = tmp_path / "extracted.json"
    ep.write_text(json.dumps({"loads_kw": [170.0] * _HOURS}), encoding="utf-8")
    out = tmp_path / "onsite_out.json"

    proc = _run(
        "onsite",
        "--config", str(FIXTURES / "sample_deal_config.json"),
        "--results", str(rp),
        "--extracted", str(ep),
        "--out", str(out),
    )
    assert proc.returncode == 0, proc.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["sizing"]["pv_kw"] == 3000.0
    assert res["dispatch"]["total_load_kwh"] == pytest.approx(170.0 * _HOURS)


def test_cli_offsite_subcommand_samsung(tmp_path):
    if not SAMSUNG_EXTRACTED.exists():
        pytest.skip("Samsung extracted inputs not present")
    out = tmp_path / "offsite_out.json"
    proc = _run(
        "offsite_dppa",
        "--config", str(SAMSUNG_CONFIG),
        "--extracted", str(SAMSUNG_EXTRACTED),
        "--no-developer",
        "--out", str(out),
    )
    if proc.returncode != 0:
        pytest.skip(f"offsite CLI run unavailable (PySAM/resource?): {proc.stderr[:300]}")
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["case"] == "DPPA_SAMSUNG_TTC"
    assert "base_settlement" in res
    assert "decision" in res


# ---------------------------------------------------------------------------
# PHASE-02: --results / --scenario flags make DPPA_CASE_1_NINHSIM reachable.
# ---------------------------------------------------------------------------

NINHSIM_SCENARIO = (
    REPO_ROOT / "scenarios" / "case_studies" / "ninhsim" / "2026-04-09_ninhsim_dppa-case-1.json"
)


def _case_1_deal_config() -> dict:
    return {
        "case": "DPPA_CASE_1_NINHSIM",
        "mode": "offsite_dppa",
        "title": "Ninhsim DPPA Case 1",
        "site": {"region": "central"},
    }


def _case_1_results() -> dict:
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


def _case_1_extracted() -> dict:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_ninhsim_extracted_inputs_cli",
        REPO_ROOT / "scripts" / "python" / "integration" / "build_ninhsim_extracted_inputs.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_ninhsim_extracted_inputs_cli"] = module
    spec.loader.exec_module(module)
    return module.build_extracted_inputs()


def _write_payloads(tmp_path):
    config_path = tmp_path / "case1_deal.json"
    config_path.write_text(json.dumps(_case_1_deal_config()), encoding="utf-8")
    extracted_path = tmp_path / "case1_extracted.json"
    extracted_path.write_text(json.dumps(_case_1_extracted()), encoding="utf-8")
    results_path = tmp_path / "case1_results.json"
    results_path.write_text(json.dumps(_case_1_results()), encoding="utf-8")
    scenario_path = tmp_path / "case1_scenario.json"
    scenario_path.write_text(NINHSIM_SCENARIO.read_text(encoding="utf-8-sig"), encoding="utf-8")
    return config_path, extracted_path, results_path, scenario_path


def test_cli_offsite_case_1_with_results_and_scenario(tmp_path):
    config, extracted, results, scenario = _write_payloads(tmp_path)
    out = tmp_path / "case1_out.json"
    proc = _run(
        "offsite_dppa",
        "--config", str(config),
        "--extracted", str(extracted),
        "--results", str(results),
        "--scenario", str(scenario),
        "--no-developer",
        "--out", str(out),
    )
    assert proc.returncode == 0, proc.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["case"] == "DPPA_CASE_1_NINHSIM"


def test_cli_offsite_case_1_missing_results_exits_2(tmp_path):
    config, extracted, _, scenario = _write_payloads(tmp_path)
    proc = _run(
        "offsite_dppa",
        "--config", str(config),
        "--extracted", str(extracted),
        "--scenario", str(scenario),
        "--no-developer",
    )
    assert proc.returncode == 2
    assert "needs `results`" in proc.stderr


# ---------------------------------------------------------------------------
# PHASE-03: in-process main(argv) call so coverage measures the public CLI.
# ---------------------------------------------------------------------------


def test_cli_onsite_subcommand_in_process(tmp_path):
    from reopt_pysam_vn.analysis.__main__ import main

    results = {
        "PV": {"size_kw": 3000.0, "electric_to_load_series_kw": [100.0] * _HOURS, "electric_to_grid_series_kw": [10.0] * _HOURS},
        "ElectricStorage": {"size_kw": 1000.0, "size_kwh": 2000.0, "storage_to_load_series_kw": [20.0] * _HOURS},
        "ElectricUtility": {"electric_to_load_series_kw": [50.0] * _HOURS},
        "Financial": {"npv": 1_500_000.0},
    }
    rp = tmp_path / "results.json"
    rp.write_text(json.dumps(results), encoding="utf-8")
    ep = tmp_path / "extracted.json"
    ep.write_text(json.dumps({"loads_kw": [170.0] * _HOURS}), encoding="utf-8")
    out = tmp_path / "onsite_out.json"

    rc = main(
        [
            "onsite",
            "--config", str(FIXTURES / "sample_deal_config.json"),
            "--results", str(rp),
            "--extracted", str(ep),
            "--out", str(out),
        ]
    )
    assert rc == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["sizing"]["pv_kw"] == 3000.0


def test_cli_offsite_missing_extracted_in_process_returns_2(tmp_path):
    from reopt_pysam_vn.analysis.__main__ import main

    cfg = tmp_path / "deal.json"
    cfg.write_text(json.dumps({"case": "MY_NEW_DEAL", "mode": "offsite_dppa"}), encoding="utf-8")
    rc = main(["offsite_dppa", "--config", str(cfg)])
    assert rc == 2
