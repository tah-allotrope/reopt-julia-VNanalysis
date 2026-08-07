"""PHASE-03: generalized offsite/DPPA pipeline.

`run_offsite_dppa` is the generalized front door: it maps a DealConfig + extracted
inputs through an orchestrator (resolved from an extensible registry, or injected)
into an `OffsiteDppaResult` mirroring the combined-decision artifact. Unit tests
use an injected fake orchestrator to stay fast and deterministic; the real Samsung
orchestration is exercised end-to-end by the CLI smoke test and the PHASE-04
parity gate.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.analysis import offsite_dppa as od
from reopt_pysam_vn.analysis.offsite_dppa import run_offsite_dppa
from reopt_pysam_vn.analysis.types import DealConfig, OffsiteDppaResult

GOLDEN = REPO_ROOT / "examples" / "samsung-ttc_combined-decision.example.json"


def _fake_combined(extracted, *, run_developer=True):
    import json

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    golden["_run_developer_seen"] = run_developer
    golden["_extracted_keys"] = sorted(extracted.keys())
    return golden


def _deal(case="DPPA_SAMSUNG_TTC"):
    return DealConfig.from_dict({"case": case, "mode": "offsite_dppa"})


def test_run_offsite_dppa_uses_injected_orchestrator():
    res = run_offsite_dppa(
        _deal(), extracted={"loads_kw": [1.0]}, combined_decision_fn=_fake_combined
    )
    assert isinstance(res, OffsiteDppaResult)
    assert res.case == "DPPA_SAMSUNG_TTC"
    # the rich blocks survive into the typed result
    assert res.base_settlement["contracted_slice"]["matched_quantity_gwh"] == pytest.approx(70.0)
    assert res.strike_sweep["strike_band"]["floor_vnd_per_kwh"] == 1012.0


def test_run_offsite_dppa_passes_run_developer_flag():
    res = run_offsite_dppa(
        _deal(), extracted={"loads_kw": [1.0]}, run_developer=False, combined_decision_fn=_fake_combined
    )
    assert res.raw["_run_developer_seen"] is False


def test_run_offsite_dppa_resolves_registered_orchestrator(monkeypatch):
    monkeypatch.setitem(od._ORCHESTRATORS, "DPPA_SAMSUNG_TTC", _fake_combined)
    res = run_offsite_dppa(_deal(), extracted={"loads_kw": [1.0]})
    assert res.case == "DPPA_SAMSUNG_TTC"
    assert res.raw["_extracted_keys"] == ["loads_kw"]


def test_run_offsite_dppa_unregistered_deal_without_fn_raises():
    with pytest.raises(ValueError, match="orchestrator"):
        run_offsite_dppa(_deal(case="BRAND_NEW_DEAL"), extracted={"loads_kw": [1.0]})


def test_run_offsite_dppa_requires_extracted():
    with pytest.raises(ValueError, match="extracted"):
        run_offsite_dppa(_deal(), combined_decision_fn=_fake_combined)
