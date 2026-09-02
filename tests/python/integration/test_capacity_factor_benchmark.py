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
    """The physical gate now runs through the generation-profile module.

    This used to hand-roll a fourth PVWatts model construction, independent of
    the two in the orchestrators. Going through the module means the gate
    measures the configuration production actually uses.
    """
    from reopt_pysam_vn.pysam.generation_profile import ArrayConfig, run_pvwatts

    resource = REPO_ROOT / "data" / "interim" / "pysam_resources" / "ninhsim_himawari_2019_60min.csv"
    assert resource.is_file(), f"tracked resource missing: {resource}"

    series = run_pvwatts(
        system_capacity_kw_dc=float(SYSTEM_CAPACITY_KW),
        array=ArrayConfig(array_type=0, tilt_degrees=12.525729252783036),
        resource_file=resource,
    )
    assert series is not None, "PVWatts returned no series on the tracked resource"

    annual_kwh = float(sum(series))
    cf_pct = annual_kwh / (SYSTEM_CAPACITY_KW * HOURS_PER_YEAR) * 100.0

    # Expected 17.44% on the tracked file; band is 14-20.
    # Same config with array_type=2 yields 21.56%, outside the band.
    assert CF_MIN_PCT <= cf_pct <= CF_MAX_PCT, (
        f"PVWatts CF {cf_pct:.2f}% for Ninh Thuan fixed-tilt outside expected range "
        f"[{CF_MIN_PCT}%, {CF_MAX_PCT}%]. Annual energy: {annual_kwh:,.0f} kWh."
    )
    # Rough check near expected 17.44%
    assert 16.0 <= cf_pct <= 19.0, f"CF {cf_pct:.2f}% not near expected 17.44%"
