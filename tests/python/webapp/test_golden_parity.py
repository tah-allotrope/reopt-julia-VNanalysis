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
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMSUNG_EXTRACTED = REPO_ROOT / "data" / "interim" / "samsung_ttc" / "samsung_ttc_extracted_inputs.json"
SAMSUNG_CONFIG = REPO_ROOT / "scenarios" / "case_studies" / "samsung_ttc" / "samsung_ttc_deal_config.json"
GOLDEN = REPO_ROOT / "examples" / "samsung-ttc_combined-decision.example.json"

_MISSING = object()


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _leaf_paths(obj: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Yield (dotted_path, scalar_value) for every leaf in a nested structure.

    List indices render as ``[i]`` (e.g. ``c[0]``).
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            yield from _leaf_paths(value, child)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _leaf_paths(value, f"{prefix}[{index}]")
    else:
        yield prefix, obj


def _scalar_equivalent(a: Any, b: Any) -> bool:
    """Scalar equality that treats ``bool`` as ``bool``, never as ``int``.

    ``True == 1`` is ``True`` in Python, so a naive comparator would call a
    boolean field equal to an integer field that differs in meaning.
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return a == b


def _diverging_paths(actual: dict, golden: dict) -> set[str]:
    """Return dotted leaf paths whose values differ between the two structures.

    A path present in only one side counts as diverging.
    """
    actual_leaves = dict(_leaf_paths(actual))
    golden_leaves = dict(_leaf_paths(golden))
    diverged: set[str] = set()
    for key in set(actual_leaves) | set(golden_leaves):
        if not _scalar_equivalent(actual_leaves.get(key, _MISSING), golden_leaves.get(key, _MISSING)):
            diverged.add(key)
    return diverged


# Measured on 2026-08-06 against a live run_offsite_dppa call; the golden's
# developer screen was built before the Single-Owner reference-plant defaults
# audit, so the developer NPV/IRR family diverges. `[*]` matches any list index.
KNOWN_DRIFTED_PATHS = frozenset({
    "strike_sweep.negotiation_summary.buyer_saves_candidates[*].developer_irr_fraction",
    "strike_sweep.negotiation_summary.buyer_saves_candidates[*].developer_npv_usd",
    "strike_sweep.sweep[*].developer_irr_fraction",
    "strike_sweep.sweep[*].developer_npv_usd",
    "strike_sweep.sweep[*].developer_passes",
})


def _unexpected_drift_paths(actual: dict, golden: dict) -> set[str]:
    diverged = _diverging_paths(actual, golden)
    return {
        path
        for path in diverged
        if re.sub(r"\[\d+\]", "[*]", path) not in KNOWN_DRIFTED_PATHS
    }


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


@pytest.mark.golden_machine
def test_samsung_ttc_golden_drift_stays_within_the_known_manifest():
    """The analytics-level golden drift is bounded and catalogued.

    Shrinking the divergence stays green (subset), a *new* divergence turns red
    (outside the manifest), and fixing everything yields the empty set - which
    is also a subset, so the manifest can be emptied in a follow-up.

    ``golden_machine``: the manifest is measured against
    ``examples/samsung-ttc_combined-decision.example.json``, and the golden is
    only reproducible on the primary dev machine's PySAM resources. On other
    machines the whole settlement diverges from the golden (measured ~45 paths
    in CI vs the 15 here), so this comparison is meaningful only where the
    golden was made. The web-API-vs-direct gate above is the CI-enforced check;
    this is the local-only tripwire for the analytics divergence.
    """
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

    unexpected = _unexpected_drift_paths(result, golden)
    assert not unexpected, (
        "golden drift grew beyond the known manifest; catalog each path or fix "
        f"the analytics before re-running: {sorted(unexpected)}"
    )
