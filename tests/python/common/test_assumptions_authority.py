"""PHASE-03 (2026-08-06 plan): the deal-defaults data layer is authoritative.

Editing ``data/vietnam/vn_deal_defaults_2026.json``'s exchange rate must change
the resolved rate in every general-purpose module. This suite pins that
property; it fails before the ``caller_value`` unpinning and passes after.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from reopt_pysam_vn.common.assumptions import exchange_rate
from reopt_pysam_vn.reopt.preprocess import VNData, load_vietnam_data

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_03_02_FILES = [
    "src/python/reopt_pysam_vn/integration/factory_a.py",
    "src/python/reopt_pysam_vn/reopt/decree243_delta.py",
    "scripts/python/integration/build_ninhsim_extracted_inputs.py",
    "scripts/python/reopt/bess_dispatch_analysis.py",
    "scripts/python/reopt/decree146_demand_charge.py",
    "scripts/python/reopt/decree243_export_cap_delta.py",
    "scripts/python/reopt/dppa_settlement.py",
    "scripts/python/reopt/fmp_sensitivity.py",
]
SAMSUNG_PINNED_FILE = "src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py"


def _vn_with_rate(vn: VNData, rate: float) -> VNData:
    """Return a deep-copied VNData with ``deal_defaults.exchange_rate.vnd_per_usd`` overridden."""
    defaults = {k: (dict(v) if isinstance(v, dict) else v) for k, v in vn.deal_defaults.items()}
    defaults["exchange_rate"] = {**defaults["exchange_rate"], "vnd_per_usd": rate}
    return dataclasses.replace(vn, deal_defaults=defaults)


@pytest.fixture(scope="module")
def vn():
    return load_vietnam_data()


def test_deal_defaults_rate_is_authoritative(vn):
    modified = _vn_with_rate(vn, 30000.0)
    assert exchange_rate(modified) == 30000.0


def test_caller_value_still_wins_over_data_layer(vn):
    modified = _vn_with_rate(vn, 30000.0)
    assert exchange_rate(modified, caller_value=25450.0) == 25450.0


def test_per_deal_override_still_honoured(vn):
    modified = _vn_with_rate(vn, 30000.0)
    assert (
        exchange_rate(modified, extracted={"benchmark": {"exchange_rate_vnd_per_usd": 25000.0}})
        == 25000.0
    )


def test_unmodified_default_rate(vn):
    assert exchange_rate(load_vietnam_data()) == 26400.0


def test_zero_rate_raises(vn):
    modified = _vn_with_rate(vn, 0.0)
    with pytest.raises(ValueError, match="must be positive"):
        exchange_rate(modified)


def test_general_purpose_modules_do_not_pin_caller_value():
    """The 8 general-purpose sites must derive from the data layer (ASM-009)."""
    for rel in TASK_03_02_FILES:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "caller_value=26_400.0" not in text, f"{rel} still pins the canonical rate"


def test_samsung_path_retains_the_single_deliberate_pin():
    """The parity-gated Samsung path keeps its one pin on purpose (ASM-009/CON-001)."""
    text = (REPO_ROOT / SAMSUNG_PINNED_FILE).read_text(encoding="utf-8")
    assert text.count("caller_value=26_400.0") == 1
