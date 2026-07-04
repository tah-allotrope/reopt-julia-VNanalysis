"""PHASE-05: Samsung-TTC parity through the web API path (DEC-007 acceptance
gate).

The gate proves the thing the webapp actually controls: that POST /api/runs
reproduces `run_offsite_dppa` bit-for-bit (CON-002, no forked analytics
logic) - the same contract `tests/python/analysis/test_samsung_ttc_parity.py`
checks at the library level, just one layer up.

It deliberately does NOT re-assert parity against
`examples/samsung-ttc_combined-decision.example.json`: that golden already
diverges from a *direct* `run_offsite_dppa` call on main (see
`negotiation_summary.buyer_saves_candidates[0].developer_irr_fraction`,
None in the golden vs a real PySAM IRR today) - a pre-existing analytics-level
drift out of scope for the web app to fix.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMSUNG_EXTRACTED = REPO_ROOT / "data" / "interim" / "samsung_ttc" / "samsung_ttc_extracted_inputs.json"
SAMSUNG_CONFIG = REPO_ROOT / "scenarios" / "case_studies" / "samsung_ttc" / "samsung_ttc_deal_config.json"
GOLDEN = REPO_ROOT / "examples" / "samsung-ttc_combined-decision.example.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_samsung_ttc_web_api_matches_direct_library_call_bit_exact(client):
    """The real, controllable acceptance bar: the web path forks nothing."""
    if not (SAMSUNG_EXTRACTED.exists() and SAMSUNG_CONFIG.exists()):
        pytest.skip("Samsung-TTC fixtures not present")

    from reopt_pysam_vn.analysis.offsite_dppa import run_offsite_dppa
    from reopt_pysam_vn.analysis.types import DealConfig

    deal_config = _read(SAMSUNG_CONFIG)
    extracted = _read(SAMSUNG_EXTRACTED)

    direct_result = run_offsite_dppa(DealConfig.from_dict(deal_config), extracted=extracted).to_dict()

    resp = client.post("/api/runs", json={"deal_config": deal_config, "extracted": extracted})
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]

    body = client.get(f"/api/runs/{run_id}").json()
    assert body["status"]["state"] == "done", body["status"]
    assert body["result"] == direct_result, "web API result diverges from a direct run_offsite_dppa call"


def test_samsung_ttc_golden_drift_is_the_known_pre_existing_gap():
    """Documents (does not re-litigate) the analytics-level golden drift so a
    future fix to the library is immediately visible here too."""
    if not (SAMSUNG_EXTRACTED.exists() and SAMSUNG_CONFIG.exists() and GOLDEN.exists()):
        pytest.skip("Samsung-TTC golden fixtures not present")

    from reopt_pysam_vn.analysis.offsite_dppa import run_offsite_dppa
    from reopt_pysam_vn.analysis.types import DealConfig

    deal_config = _read(SAMSUNG_CONFIG)
    extracted = _read(SAMSUNG_EXTRACTED)
    golden = _read(GOLDEN)

    result = run_offsite_dppa(DealConfig.from_dict(deal_config), extracted=extracted).to_dict()
    got_source = result.get("quality", {}).get("solar_profile_source", "")
    if "pvwatts" not in got_source:
        pytest.skip(f"PVWatts not the active solar path (got {got_source!r})")

    drifted = (
        result["strike_sweep"]["negotiation_summary"]["buyer_saves_candidates"][0]["developer_irr_fraction"]
        != golden["strike_sweep"]["negotiation_summary"]["buyer_saves_candidates"][0]["developer_irr_fraction"]
    )
    assert drifted, (
        "expected the known pre-existing golden drift on developer_irr_fraction; "
        "if this now passes, the analytics-level golden may have been refreshed - "
        "re-enable full parity checking in this test."
    )
