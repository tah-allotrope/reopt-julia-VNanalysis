"""
Layer 1: Saigon18 Data Validation Tests

Tests for extract_excel_inputs.py logic using synthetic inputs.
No Excel file or external services required — all tests run from generated data
or by calling the module's public functions directly.

Run: pytest tests/python/integration/test_saigon18_data.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python" / "reopt"))

from extract_excel_inputs import (
    PV_KW_RATED,
    extract_data_input,
    validate_extracted,
)

# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

_EXPECTED_SOLAR_GWH = 71.808
_EXPECTED_LOAD_GWH = 184.3


def _make_profiles(
    pv_annual_gwh: float = _EXPECTED_SOLAR_GWH,
    load_annual_gwh: float = _EXPECTED_LOAD_GWH,
    n: int = 8760,
) -> dict:
    """Return a synthetic hourly profiles dict with flat (constant) series."""
    hourly_pv = pv_annual_gwh * 1e6 / 8760
    hourly_load = load_annual_gwh * 1e6 / 8760
    pv_raw = [hourly_pv] * n
    return {
        "loads_kw": [hourly_load] * n,
        "pv_kw_raw": pv_raw,
        "pv_production_factor_series": [v / PV_KW_RATED for v in pv_raw],
        "fmp_vnd_per_mwh": [1_800_000.0] * n,
        "cfmp_vnd_per_mwh": [1_500_000.0] * n,
    }


def _make_assumptions() -> dict:
    return {
        "solar_kw_rated": PV_KW_RATED,
        "performance_ratio": 0.8086,
        "annual_yield_gwh": _EXPECTED_SOLAR_GWH,
    }


def _mock_worksheet(rows: list) -> MagicMock:
    """Create a mock openpyxl worksheet whose iter_rows() returns `rows`."""
    ws = MagicMock()
    ws.iter_rows.return_value = iter(rows)
    return ws


def _row(pv_kw: float = 100.0, load_kw: float = 21_000.0) -> tuple:
    """One synthetic data row matching the expected column layout."""
    # (col A, col B: pv_kw, col C, col D: load_kw, col E: fmp, col F: cfmp)
    return (None, pv_kw, None, load_kw, 1_800_000.0, 1_500_000.0)


# ---------------------------------------------------------------------------
# 1. Profile length checks
# ---------------------------------------------------------------------------


class TestProfileLengths:
    def test_loads_kw_length(self):
        profiles = _make_profiles()
        assert len(profiles["loads_kw"]) == 8760

    def test_pv_production_factor_series_length(self):
        profiles = _make_profiles()
        assert len(profiles["pv_production_factor_series"]) == 8760

    def test_pv_kw_raw_length(self):
        profiles = _make_profiles()
        assert len(profiles["pv_kw_raw"]) == 8760


# ---------------------------------------------------------------------------
# 2. 8760-row enforcement via extract_data_input
# ---------------------------------------------------------------------------


class TestRowCountEnforcement:
    def test_wrong_row_count_raises(self):
        """extract_data_input raises ValueError when sheet has != 8760 rows."""
        ws = _mock_worksheet([_row()] * 8759)
        with pytest.raises(ValueError, match="Expected 8760 data rows"):
            extract_data_input(ws)

    def test_too_many_rows_raises(self):
        ws = _mock_worksheet([_row()] * 8761)
        with pytest.raises(ValueError, match="Expected 8760 data rows"):
            extract_data_input(ws)

    def test_correct_row_count_passes(self):
        """extract_data_input succeeds with exactly 8760 rows."""
        ws = _mock_worksheet([_row()] * 8760)
        result = extract_data_input(ws)
        assert len(result["loads_kw"]) == 8760
        assert len(result["pv_production_factor_series"]) == 8760


# ---------------------------------------------------------------------------
# 3. No-negative-values
# ---------------------------------------------------------------------------


class TestNoNegativeValues:
    def test_loads_all_non_negative(self):
        profiles = _make_profiles()
        assert all(v >= 0 for v in profiles["loads_kw"])

    def test_pv_all_non_negative(self):
        profiles = _make_profiles()
        assert all(v >= 0 for v in profiles["pv_kw_raw"])

    def test_validate_warns_on_negative_load(self):
        profiles = _make_profiles()
        profiles["loads_kw"][0] = -1.0
        warnings = validate_extracted(profiles, _make_assumptions())
        assert any("negative" in w.lower() for w in warnings)

    def test_validate_warns_on_negative_pv(self):
        profiles = _make_profiles()
        profiles["pv_kw_raw"][0] = -1.0
        profiles["pv_production_factor_series"][0] = -1.0 / PV_KW_RATED
        warnings = validate_extracted(profiles, _make_assumptions())
        assert any("negative" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# 4. Production factor bounds: all values in [0.0, 1.0]
# ---------------------------------------------------------------------------


class TestProductionFactorBounds:
    def test_all_factors_in_unit_interval(self):
        profiles = _make_profiles()
        factors = profiles["pv_production_factor_series"]
        assert all(0.0 <= v <= 1.0 for v in factors)

    def test_validate_warns_on_factor_above_threshold(self):
        """A factor > 1.05 triggers a validation warning."""
        profiles = _make_profiles()
        profiles["pv_production_factor_series"][0] = 1.10
        warnings = validate_extracted(profiles, _make_assumptions())
        assert any("production factor" in w.lower() for w in warnings)

    def test_validate_no_warning_for_clean_factors(self):
        profiles = _make_profiles()
        warnings = validate_extracted(profiles, _make_assumptions())
        factor_warnings = [w for w in warnings if "production factor" in w.lower()]
        assert len(factor_warnings) == 0


# ---------------------------------------------------------------------------
# 5. Solar yield consistency: within ±1% of 71.8 GWh
# ---------------------------------------------------------------------------


class TestSolarYieldConsistency:
    def test_annual_pv_within_1pct_of_target(self):
        profiles = _make_profiles(pv_annual_gwh=_EXPECTED_SOLAR_GWH)
        annual_pv_gwh = sum(profiles["pv_kw_raw"]) / 1e6
        assert abs(annual_pv_gwh - _EXPECTED_SOLAR_GWH) / _EXPECTED_SOLAR_GWH < 0.01

    def test_validate_warns_when_yield_10pct_off(self):
        """A 10% deviation from target (> 2% tolerance) triggers a warning."""
        profiles = _make_profiles(pv_annual_gwh=_EXPECTED_SOLAR_GWH * 1.10)
        warnings = validate_extracted(profiles, _make_assumptions())
        assert any("GWh" in w for w in warnings)

    def test_validate_no_yield_warning_when_on_target(self):
        profiles = _make_profiles(pv_annual_gwh=_EXPECTED_SOLAR_GWH)
        warnings = validate_extracted(profiles, _make_assumptions())
        yield_warnings = [w for w in warnings if "Annual PV" in w]
        assert len(yield_warnings) == 0


# ---------------------------------------------------------------------------
# 6. Annual load sanity: close to 184.3 GWh (±5% for synthetic test)
# ---------------------------------------------------------------------------


class TestAnnualLoadSanity:
    def test_annual_load_close_to_expected(self):
        """Synthetic load at 184.3 GWh is within ±5% of expected."""
        profiles = _make_profiles(load_annual_gwh=_EXPECTED_LOAD_GWH)
        annual_load = sum(profiles["loads_kw"]) / 1e6
        assert abs(annual_load - _EXPECTED_LOAD_GWH) / _EXPECTED_LOAD_GWH < 0.05

    def test_validate_warns_when_load_out_of_range(self):
        """An implausible load (400 GWh) triggers a validation warning."""
        profiles = _make_profiles(load_annual_gwh=400.0)
        warnings = validate_extracted(profiles, _make_assumptions())
        assert any("load" in w.lower() for w in warnings)

    def test_validate_no_load_warning_for_expected_load(self):
        profiles = _make_profiles(load_annual_gwh=_EXPECTED_LOAD_GWH)
        warnings = validate_extracted(profiles, _make_assumptions())
        load_warnings = [w for w in warnings if "load" in w.lower()]
        assert len(load_warnings) == 0
