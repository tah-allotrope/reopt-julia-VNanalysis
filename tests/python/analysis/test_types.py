"""PHASE-01: shared analysis contract — deal-config schema + result types.

These lock the generalized contract that the onsite / offsite_dppa pipelines
(PHASE-02/03) produce and that the deprecated case-module wrappers (PHASE-05)
delegate to. Round-trip against the real Samsung-TTC golden combined-decision.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.analysis.types import (  # noqa: E402
    CombinedDecision,
    DealConfig,
    OffsiteDppaResult,
    OnsiteResult,
)

SCHEMA_PATH = REPO_ROOT / "data" / "schemas" / "deal_config.schema.json"
GOLDEN_OFFSITE = REPO_ROOT / "examples" / "samsung-ttc_combined-decision.example.json"
FIXTURE_CONFIG = Path(__file__).resolve().parent / "fixtures" / "sample_deal_config.json"


def test_deal_config_schema_is_valid_json_with_required_sections():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema.get("$schema"), "schema must declare a $schema dialect"
    assert "case" in schema["required"] and "mode" in schema["required"]
    props = schema["properties"]
    for section in ("site", "plant", "load", "contract", "finance"):
        assert section in props, f"schema missing section: {section}"
    # mode is an enum of the three analysis modes
    assert set(props["mode"]["enum"]) == {"onsite", "offsite_dppa", "both"}


def test_fixture_deal_config_satisfies_schema_required_fields():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    cfg = json.loads(FIXTURE_CONFIG.read_text(encoding="utf-8"))
    for req in schema["required"]:
        assert req in cfg, f"fixture missing required field: {req}"
    assert cfg["mode"] in schema["properties"]["mode"]["enum"]


def test_deal_config_round_trips():
    cfg = DealConfig.from_dict(
        {
            "case": "X_DEAL",
            "mode": "offsite_dppa",
            "title": "test deal",
            "contract": {"strike_vnd_per_kwh": 1012.0, "annual_solar_gwh": 70.0},
            "finance": {"installed_cost_usd_per_kw": 750.0},
        }
    )
    assert cfg.case == "X_DEAL"
    assert cfg.mode == "offsite_dppa"
    assert cfg.contract["strike_vnd_per_kwh"] == 1012.0
    d = cfg.to_dict()
    assert DealConfig.from_dict(d).to_dict() == d


def test_offsite_result_round_trips_golden():
    golden = json.loads(GOLDEN_OFFSITE.read_text(encoding="utf-8"))
    res = OffsiteDppaResult.from_dict(golden)
    assert res.case == golden["case"]
    out = res.to_dict()
    for key in (
        "case",
        "deal",
        "base_settlement",
        "strike_sweep",
        "adder_sensitivity",
        "regime_stress",
        "decision",
        "quality",
    ):
        assert out[key] == golden[key], f"round-trip mismatch on {key}"


def test_onsite_result_round_trips():
    payload = {
        "case": "X_DEAL",
        "sizing": {"pv_kw": 3200.0, "bess_power_kw": 1000.0, "bess_energy_kwh": 2200.0},
        "dispatch": {"annual_load_kwh": 8_000_000.0, "pv_to_load_kwh": 4_000_000.0},
        "economics": {"npv_vnd": 1.0e9, "year_one_bill_vnd": 2.0e9},
    }
    res = OnsiteResult.from_dict(payload)
    assert res.sizing["pv_kw"] == 3200.0
    assert res.to_dict() == OnsiteResult.from_dict(res.to_dict()).to_dict()


def test_combined_decision_wraps_both_modes():
    off = OffsiteDppaResult.from_dict(json.loads(GOLDEN_OFFSITE.read_text(encoding="utf-8")))
    on = OnsiteResult.from_dict({"case": "X", "sizing": {}, "dispatch": {}, "economics": {}})
    combined = CombinedDecision(
        case="X",
        onsite=on,
        offsite_dppa=off,
        recommendation="buyer_favorable_developer_subeconomic",
    )
    d = combined.to_dict()
    assert d["case"] == "X"
    assert d["recommendation"] == "buyer_favorable_developer_subeconomic"
    assert d["offsite_dppa"]["case"] == off.case
    assert d["onsite"]["case"] == "X"
    # mode-absent serialises as None
    only_off = CombinedDecision(case="Y", onsite=None, offsite_dppa=off, recommendation="x")
    assert only_off.to_dict()["onsite"] is None
