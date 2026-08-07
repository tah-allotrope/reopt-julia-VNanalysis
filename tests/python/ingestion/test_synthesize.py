"""Tests for partial-data handling: resampling, monthly synthesis, and offline fallback."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.ingestion.loader import FactoryLoadResult, ingest_factory_load
from reopt_pysam_vn.ingestion.synthesize import (
    detect_resolution,
    resample_to_hourly,
    route_synthesis,
    synthesize_from_monthly,
)

# ── detect_resolution ──────────────────────────────────────────────────


class TestDetectResolution:
    def test_15min(self):
        assert detect_resolution(35040) == "15min"

    def test_30min(self):
        assert detect_resolution(17520) == "30min"

    def test_hourly(self):
        assert detect_resolution(8760) == "hourly"

    def test_monthly(self):
        assert detect_resolution(12) == "monthly"

    def test_unknown(self):
        assert detect_resolution(999) == "unknown"


# ── resample_to_hourly ─────────────────────────────────────────────────


class TestResampleToHourly:
    def test_15min_to_hourly(self):
        """15-min data with 4 values per hour averaging correctly."""
        values_15min = []
        for hour in range(8760):
            values_15min.extend([100.0, 200.0, 300.0, 400.0])

        assert len(values_15min) == 35040
        hourly = resample_to_hourly(values_15min, "15min")
        assert len(hourly) == 8760
        assert hourly[0] == pytest.approx(250.0)

    def test_30min_to_hourly(self):
        """30-min data with 2 values per hour averaging correctly."""
        values_30min = []
        for hour in range(8760):
            values_30min.extend([100.0, 300.0])

        assert len(values_30min) == 17520
        hourly = resample_to_hourly(values_30min, "30min")
        assert len(hourly) == 8760
        assert hourly[0] == pytest.approx(200.0)

    def test_wrong_length_15min(self):
        with pytest.raises(ValueError, match="35040"):
            resample_to_hourly([1.0] * 100, "15min")

    def test_wrong_length_30min(self):
        with pytest.raises(ValueError, match="17520"):
            resample_to_hourly([1.0] * 100, "30min")

    def test_unsupported_resolution(self):
        with pytest.raises(ValueError, match="Unsupported"):
            resample_to_hourly([1.0] * 100, "daily")

    def test_15min_preserves_total_energy(self):
        """Total energy (sum of averages * hours) should be preserved."""
        values_15min = [float(i % 1000 + 100) for i in range(35040)]
        hourly = resample_to_hourly(values_15min, "15min")

        original_hourly_avg_sum = sum(
            sum(values_15min[i:i + 4]) / 4 for i in range(0, 35040, 4)
        )
        assert sum(hourly) == pytest.approx(original_hourly_avg_sum, rel=1e-9)


# ── synthesize_from_monthly ────────────────────────────────────────────


class TestSynthesizeFromMonthly:
    def test_offline_fallback_produces_8760(self):
        monthly = [15000.0] * 12
        loads, method = synthesize_from_monthly(monthly)
        assert len(loads) == 8760
        assert method == "offline_archetype_scaled"

    def test_offline_total_matches_annual(self):
        monthly = [15000.0] * 12
        annual_kwh = sum(monthly)
        loads, _ = synthesize_from_monthly(monthly)
        assert sum(loads) == pytest.approx(annual_kwh, rel=0.01)

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="12"):
            synthesize_from_monthly([1000.0] * 6)

    def test_variable_monthly_totals(self):
        monthly = [10000, 12000, 14000, 16000, 18000, 20000,
                   20000, 18000, 16000, 14000, 12000, 10000]
        loads, method = synthesize_from_monthly(monthly)
        assert len(loads) == 8760
        assert method == "offline_archetype_scaled"
        assert all(v >= 0 for v in loads)

    @patch("reopt_pysam_vn.ingestion.synthesize._call_simulated_load_api")
    def test_api_success_path(self, mock_api):
        mock_api.return_value = [500.0] * 8760
        monthly = [15000.0] * 12
        loads, method = synthesize_from_monthly(monthly, api_key="test_key")
        assert len(loads) == 8760
        assert method == "api_simulated_load"
        mock_api.assert_called_once()

    @patch("reopt_pysam_vn.ingestion.synthesize._call_simulated_load_api")
    def test_api_failure_falls_back(self, mock_api):
        mock_api.side_effect = ConnectionError("No network")
        monthly = [15000.0] * 12
        loads, method = synthesize_from_monthly(monthly, api_key="test_key")
        assert len(loads) == 8760
        assert method == "offline_archetype_scaled"


# ── route_synthesis ────────────────────────────────────────────────────


class TestRouteSynthesis:
    def test_hourly_passthrough(self):
        values = [100.0] * 8760
        result, method = route_synthesis(values, 8760)
        assert method == "none"
        assert len(result) == 8760

    def test_15min_routes_to_resample(self):
        values = [100.0] * 35040
        result, method = route_synthesis(values, 35040)
        assert method == "resampled_15min"
        assert len(result) == 8760

    def test_30min_routes_to_resample(self):
        values = [100.0] * 17520
        result, method = route_synthesis(values, 17520)
        assert method == "resampled_30min"
        assert len(result) == 8760

    def test_monthly_routes_to_synthesis(self):
        values = [15000.0] * 12
        result, method = route_synthesis(values, 12)
        assert len(result) == 8760
        assert method in ("api_simulated_load", "offline_archetype_scaled")

    def test_unknown_length_raises(self):
        with pytest.raises(ValueError, match="Cannot synthesize"):
            route_synthesis([1.0] * 999, 999)


# ── Integration: ingest_factory_load with synthesis ────────────────────


class TestIngestWithSynthesis:
    def test_15min_csv_resampled(self):
        """A 35040-row CSV should be auto-resampled to 8760."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["load_kw"])
            for i in range(35040):
                writer.writerow([100.0 + (i % 100)])
            path = Path(f.name)

        try:
            result = ingest_factory_load(path)
            assert isinstance(result, FactoryLoadResult)
            assert len(result.loads_kw) == 8760
            assert result.synthesis_method == "resampled_15min"
        finally:
            path.unlink()

    def test_monthly_json_synthesized(self):
        """A 12-element JSON array should be synthesized to 8760."""
        data = [15000.0] * 12
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        try:
            result = ingest_factory_load(path)
            assert len(result.loads_kw) == 8760
            assert result.synthesis_method in (
                "api_simulated_load",
                "offline_archetype_scaled",
            )
        finally:
            path.unlink()

    def test_synthesis_method_none_for_8760(self):
        """Normal 8760 input should have synthesis_method = 'none'."""
        data = [100.0] * 8760
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        try:
            result = ingest_factory_load(path)
            assert result.synthesis_method == "none"
        finally:
            path.unlink()
