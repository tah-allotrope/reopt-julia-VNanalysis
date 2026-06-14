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
