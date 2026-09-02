"""C1: the generation profile is one deep module with one interface.

The 8760 solar profile used to be resolved twice — once in
``analysis/orchestrators/generic_vn_dppa`` and once in
``integration/dppa_samsung_ttc`` — each with its own three-tier ladder, its own
PySAM import guard, and its own ``source`` vocabulary. Both signalled a
fall-back by returning ``None``, so a degraded profile read exactly like a real
one at the call site.

These tests pin the interface of the module that replaces both ladders:
``resolve_generation_profile`` returns a ``GenerationProfile`` carrying the
series, the resolved source, and any warnings **as data**.
"""

from __future__ import annotations

import pytest
from reopt_pysam_vn.pysam.generation_profile import (
    ArrayConfig,
    GenerationProfile,
    calibrate_to_target,
    resolve_generation_profile,
    synthetic_shape_8760,
)

HOURS = 8760


def _flat_daylight_shape() -> list[float]:
    """12 daylight hours at 1.0, 12 night hours at 0.0, every day."""
    return ([1.0] * 12 + [0.0] * 12) * 365


# ---------------------------------------------------------------------------
# The ladder: extracted -> pvwatts -> synthetic, with the choice stated
# ---------------------------------------------------------------------------


def test_extracted_series_wins_and_names_its_source():
    supplied = [2.0] * HOURS
    profile = resolve_generation_profile(extracted_series=supplied)

    assert isinstance(profile, GenerationProfile)
    assert profile.source == "extracted"
    assert profile.series_kw == supplied
    assert profile.warnings == []


def test_extracted_series_of_wrong_length_is_rejected_not_silently_padded():
    profile = resolve_generation_profile(
        extracted_series=[1.0] * 100, target_kwh=1.0e6, use_pvwatts=False
    )

    assert profile.source == "synthetic"
    assert any("8760" in w for w in profile.warnings), profile.warnings


def test_synthetic_fallback_states_why_it_fell_back():
    """The old ladders returned None here. A degraded profile must announce itself."""
    profile = resolve_generation_profile(target_kwh=1.0e6, use_pvwatts=False)

    assert profile.source == "synthetic"
    assert len(profile.series_kw) == HOURS
    assert profile.warnings, "synthetic fall-back must be stated, not silent"
    assert any("pvwatts" in w.lower() or "synthetic" in w.lower() for w in profile.warnings)


def test_profile_always_returns_8760_hours():
    profile = resolve_generation_profile(target_kwh=5.0e6, use_pvwatts=False)
    assert len(profile.series_kw) == HOURS


# ---------------------------------------------------------------------------
# Calibration: the S2 daylight-only semantic, shared by every caller
# ---------------------------------------------------------------------------


def test_calibration_hits_the_annual_target():
    series, warnings = calibrate_to_target(_flat_daylight_shape(), 70.0e6, 41_400.0)

    assert sum(series) == pytest.approx(70.0e6, rel=1e-9)
    assert warnings == []


def test_calibration_never_puts_energy_in_a_dark_hour():
    """Redistributing clip loss must stay inside the daylight set."""
    shape = _flat_daylight_shape()
    # Force clipping: target needs more than the flat scale, cap bites.
    series, _ = calibrate_to_target(shape, 70.0e6, 16_000.0)

    dark = [value for hour, value in enumerate(series) if shape[hour] == 0.0]
    assert max(dark) == 0.0, "clip-loss redistribution leaked into dark hours"


def test_infeasible_target_warns_and_clips_at_the_cap():
    series, warnings = calibrate_to_target(_flat_daylight_shape(), 1.0e12, 10_000.0)

    assert warnings, "an infeasible annual target must be stated"
    assert any("infeasible" in w.lower() for w in warnings)
    assert max(series) == pytest.approx(10_000.0)


def test_calibration_without_a_cap_scales_without_clipping():
    series, warnings = calibrate_to_target(_flat_daylight_shape(), 70.0e6, None)

    assert sum(series) == pytest.approx(70.0e6, rel=1e-9)
    assert warnings == []


def test_zero_shape_is_reported_not_divided_by():
    series, warnings = calibrate_to_target([0.0] * HOURS, 70.0e6, 1_000.0)

    assert series == [0.0] * HOURS
    assert any("zero" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# The synthetic shape is one implementation, with no inert knobs
# ---------------------------------------------------------------------------


def test_synthetic_shape_is_deterministic_and_dark_at_night():
    shape = synthetic_shape_8760()

    assert len(shape) == HOURS
    assert shape == synthetic_shape_8760()
    assert all(shape[hour] == 0.0 for hour in range(HOURS) if (hour % 24) in (0, 1, 2, 3, 22, 23))


def test_synthetic_shape_takes_no_reference_year():
    """The old Samsung ladder took a ``reference_year`` that could not matter.

    The shape is a function of hour-of-day and day-of-year only, and both run
    1..365 across the first 8760 hours of any year, leap or not. Keeping the
    argument would have widened the interface without widening behaviour.
    """
    import inspect

    assert inspect.signature(synthetic_shape_8760).parameters == {}


# ---------------------------------------------------------------------------
# Array configuration is part of the interface, not hidden per-caller state
# ---------------------------------------------------------------------------


def test_array_config_carries_the_pvwatts_parameters():
    array = ArrayConfig(array_type=2, tilt_degrees=0.0, dc_ac_ratio=49.0 / 41.4)

    assert array.array_type == 2
    assert array.tilt_degrees == 0.0
    # The values the two old ladders disagreed about are now explicit defaults.
    assert array.azimuth == 180.0
    assert array.gcr == 0.3
    assert array.module_type == 0
    assert array.losses_pct == 14.0
    assert array.inv_eff_pct == 96.0
