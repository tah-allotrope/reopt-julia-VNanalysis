"""Validate PySAM PVWatts capacity factor on the tracked Ninh Thuan resource (network-free).

Uses the tracked 1.2 MB solar resource file so CI is deterministic.
The fixed open-rack at tilt = latitude gives 17.44% CF (inside 14-20% band);
the same configuration with array_type=2 (1-axis tracking) yields 21.56%,
outside the band — which is why the production default had to become explicit.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

SYSTEM_CAPACITY_KW = 50_000
HOURS_PER_YEAR = 8760
CF_MIN_PCT = 14.0
CF_MAX_PCT = 20.0


def test_pvwatts_capacity_factor_ninh_thuan_fixed_tilt():
    import PySAM.Pvwattsv8 as pv

    resource = REPO_ROOT / "data" / "interim" / "pysam_resources" / "ninhsim_himawari_2019_60min.csv"
    assert resource.is_file(), f"tracked resource missing: {resource}"

    model = pv.default("PVWattsSingleOwner")
    model.SolarResource.solar_resource_file = str(resource)
    model.SystemDesign.system_capacity = float(SYSTEM_CAPACITY_KW)
    model.SystemDesign.dc_ac_ratio = 1.2
    model.SystemDesign.inv_eff = 96.0
    model.SystemDesign.losses = 14.0
    model.SystemDesign.array_type = 0
    model.SystemDesign.tilt = 12.525729252783036
    model.SystemDesign.azimuth = 180.0
    model.SystemDesign.gcr = 0.3
    model.SystemDesign.module_type = 0
    model.execute(0)
    annual_kwh = float(model.Outputs.ac_annual) if hasattr(model.Outputs, "ac_annual") else float(sum(model.Outputs.gen))
    # Alternative fallback if ac_annual not present
    if annual_kwh == 0.0:
        annual_kwh = float(sum(list(model.Outputs.gen)[:8760]))
    cf_pct = annual_kwh / (SYSTEM_CAPACITY_KW * HOURS_PER_YEAR) * 100.0

    # Expected 17.44% on the tracked file; band is 14-20.
    # Same config with array_type=2 yields 21.56%, outside the band.
    assert CF_MIN_PCT <= cf_pct <= CF_MAX_PCT, (
        f"PVWatts CF {cf_pct:.2f}% for Ninh Thuan fixed-tilt outside expected range [{CF_MIN_PCT}%, {CF_MAX_PCT}%]. "
        f"Annual energy: {annual_kwh:,.0f} kWh."
    )
    # Rough check near expected 17.44%
    assert 16.0 <= cf_pct <= 19.0, f"CF {cf_pct:.2f}% not near expected 17.44%"
