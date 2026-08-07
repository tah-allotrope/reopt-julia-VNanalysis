"""PHASE-04: settlement preset drift guard (S4).

Mechanically prevents `PRESET_CONTRACTS` from drifting from the data layer's
regime-resolved policy values again, the way the `export_cap_pct=20.0` /
Decree 243 repeal drift previously went uncaught.
"""

import pytest
from reopt_pysam_vn.common.assumptions import export_cap_fraction, surplus_rate_vnd_per_kwh
from reopt_pysam_vn.integration.settlement import PRESET_CONTRACTS
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data


@pytest.fixture(scope="module")
def vn():
    return load_vietnam_data()


@pytest.mark.parametrize("preset_key", list(PRESET_CONTRACTS.keys()))
def test_preset_export_cap_matches_declared_regime(vn, preset_key):
    preset = PRESET_CONTRACTS[preset_key]
    expected = export_cap_fraction(vn, regime_id=preset.regime_id) * 100.0
    assert preset.export_cap_pct == expected, (
        f"{preset_key} export_cap_pct={preset.export_cap_pct} drifted from "
        f"regime {preset.regime_id!r} resolution {expected}"
    )


@pytest.mark.parametrize("preset_key", list(PRESET_CONTRACTS.keys()))
def test_preset_surplus_rate_matches_declared_regime(vn, preset_key):
    preset = PRESET_CONTRACTS[preset_key]
    expected = surplus_rate_vnd_per_kwh(vn, regime_id=preset.regime_id)
    assert preset.surplus_rate_vnd_kwh == expected, (
        f"{preset_key} surplus_rate_vnd_kwh={preset.surplus_rate_vnd_kwh} drifted "
        f"from regime {preset.regime_id!r} resolution {expected}"
    )
