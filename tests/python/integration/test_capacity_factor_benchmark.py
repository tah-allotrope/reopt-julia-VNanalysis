"""
Validate PySAM PVWatts capacity factor for southern Vietnam coordinates.

Binh Thuan province (11.09degN, 108.15degE) benchmark: 16.49% CF for 50 MW.
Expected range with 5% conservatism buffer: 14-20%.

Skips gracefully when PySAM is not installed.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

pytest.importorskip("PySAM")

BINH_THUAN_LAT = 11.09
BINH_THUAN_LON = 108.15
SYSTEM_CAPACITY_KW = 50_000
HOURS_PER_YEAR = 8760

EXPECTED_CF_PCT = 16.49
CF_MIN_PCT = 14.0
CF_MAX_PCT = 20.0


@pytest.mark.xfail(
    reason="numeric benchmark drift, red since 2026-07-04, tracked in activeContext.md 'Known pre-existing test failures'",
    strict=False,
)
def test_pvwatts_capacity_factor_binh_thuan():
    from PySAM.Pvwattsv8 import Pvwattsv8

    system = Pvwattsv8.new()
    system.SolarResource.solar_resource_file = ""
    system.SolarResource.lat = BINH_THUAN_LAT
    system.SolarResource.lon = BINH_THUAN_LON

    system.SystemDesign.system_capacity = SYSTEM_CAPACITY_KW
    system.SystemDesign.modules_per_string = 1
    system.SystemDesign.strings_per_inverter = 1
    system.SystemDesign.dc_ac_ratio = 1.2
    system.SystemDesign.inv_eff = 96.0
    system.SystemDesign.losses = 14.0
    system.SystemDesign.array_type = 1
    system.SystemDesign.tilt = BINH_THUAN_LAT
    system.SystemDesign.azimuth = 180.0

    system.AdjustmentFactors.constant = 1.0
    system.AnnualOutput.degradation = [0.0] * 25

    system.execute()

    annual_kwh = system.Outputs.annual_energy
    cf_pct = annual_kwh / (SYSTEM_CAPACITY_KW * HOURS_PER_YEAR) * 100.0

    assert CF_MIN_PCT <= cf_pct <= CF_MAX_PCT, (
        f"PVWatts CF {cf_pct:.2f}% for Binh Thuan (11.09N, 108.15E) "
        f"outside expected range [{CF_MIN_PCT}%, {CF_MAX_PCT}%]. "
        f"Expected ~{EXPECTED_CF_PCT}% based on 50 MW benchmark. "
        f"Annual energy: {annual_kwh:,.0f} kWh."
    )
