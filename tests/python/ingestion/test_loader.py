"""Tests for the generic factory load ingestion module."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.ingestion.loader import (
    FactoryLoadResult,
    LoadLengthError,
    clean_numeric,
    ingest_factory_load,
    interpolate_missing,
    sanitize_load_series,
)


CASE_STUDIES = REPO_ROOT / "scenarios" / "case_studies"


# ── clean_numeric ───────────────────────────────────────────────────────


class TestCleanNumeric:
    def test_quoted_comma_separated(self):
        assert clean_numeric(' " 18,205 " ') == 18205.0

    def test_plain_float(self):
        assert clean_numeric("123.45") == 123.45

    def test_none_returns_none(self):
        assert clean_numeric(None) is None

    def test_dash_returns_none(self):
        assert clean_numeric("-") is None

    def test_na_returns_none(self):
        assert clean_numeric("N/A") is None

    def test_empty_string_returns_none(self):
        assert clean_numeric("") is None

    def test_bom_marker_stripped(self):
        assert clean_numeric("﻿100") == 100.0

    def test_integer_passthrough(self):
        assert clean_numeric(42) == 42.0


# ── interpolate_missing ────────────────────────────────────────────────


class TestInterpolateMissing:
    def test_no_gaps(self):
        filled, info = interpolate_missing([1.0, 2.0, 3.0])
        assert filled == [1.0, 2.0, 3.0]
        assert info["missing_count"] == 0

    def test_middle_gap(self):
        filled, info = interpolate_missing([10.0, None, 20.0])
        assert filled == [10.0, 15.0, 20.0]
        assert info["missing_count"] == 1

    def test_leading_gap(self):
        filled, info = interpolate_missing([None, 5.0, 10.0])
        assert filled == [5.0, 5.0, 10.0]
        assert info["missing_count"] == 1

    def test_trailing_gap(self):
        filled, info = interpolate_missing([5.0, 10.0, None])
        assert filled == [5.0, 10.0, 10.0]
        assert info["missing_count"] == 1

    def test_all_none_raises(self):
        with pytest.raises(ValueError, match="only missing"):
            interpolate_missing([None, None, None])


# ── sanitize_load_series ───────────────────────────────────────────────


class TestSanitizeLoadSeries:
    def test_clips_negatives_and_interpolates(self):
        cleaned, issues = sanitize_load_series([1000.0, None, -4.0, 1600.0])
        assert cleaned == [1000.0, 500.0, 0.0, 1600.0]
        assert issues["missing_count"] == 1
        assert issues["clipped_negative_count"] == 1
        assert issues["final_count"] == 4


# ── CSV ingestion ──────────────────────────────────────────────────────


class TestCSVIngestion:
    def test_ninhsim_csv(self):
        path = CASE_STUDIES / "ninhsim" / "NinhsimSample.csv"
        if not path.exists():
            pytest.skip("ninhsim CSV not available")
        result = ingest_factory_load(path)
        assert isinstance(result, FactoryLoadResult)
        assert len(result.loads_kw) == 8760
        assert result.source_format == "csv"
        assert result.detected_column == "Load_kW"
        assert all(v >= 0 for v in result.loads_kw)

    def test_auto_column_detection(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "demand_kw", "other"])
            for i in range(8760):
                writer.writerow([f"2024-01-01T{i % 24:02d}:00", 100.0 + i * 0.01, 0])
            path = Path(f.name)

        try:
            result = ingest_factory_load(path)
            assert result.detected_column == "demand_kw"
            assert len(result.loads_kw) == 8760
        finally:
            path.unlink()

    def test_explicit_column_hint(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["hour", "pv_kw", "factory_power"])
            for i in range(8760):
                writer.writerow([i, 50.0, 200.0 + i * 0.01])
            path = Path(f.name)

        try:
            result = ingest_factory_load(path, column_hint="factory_power")
            assert result.detected_column == "factory_power"
            assert len(result.loads_kw) == 8760
        finally:
            path.unlink()

    def test_wrong_length_raises_load_length_error(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["load_kw"])
            for i in range(100):
                writer.writerow([100.0])
            path = Path(f.name)

        try:
            with pytest.raises(LoadLengthError) as exc_info:
                ingest_factory_load(path)
            assert exc_info.value.actual_length == 100
        finally:
            path.unlink()


# ── XLSX ingestion ─────────────────────────────────────────────────────


class TestXLSXIngestion:
    def test_regina_xlsx(self):
        path = CASE_STUDIES / "regina" / "Regina.xlsx"
        if not path.exists():
            pytest.skip("regina XLSX not available")
        result = ingest_factory_load(path)
        assert isinstance(result, FactoryLoadResult)
        assert len(result.loads_kw) == 8760
        assert result.source_format == "xlsx"
        assert all(v >= 0 for v in result.loads_kw)


# ── JSON ingestion ─────────────────────────────────────────────────────


class TestJSONIngestion:
    def test_saigon18_scenario_json(self):
        path = CASE_STUDIES / "saigon18" / "2026-03-20_scenario-a_fixed-sizing_evntou.json"
        if not path.exists():
            pytest.skip("saigon18 scenario JSON not available")
        result = ingest_factory_load(path)
        assert isinstance(result, FactoryLoadResult)
        assert len(result.loads_kw) == 8760
        assert result.source_format == "json"
        assert result.detected_column == "ElectricLoad.loads_kw"

    def test_flat_json_array(self):
        data = [100.0 + i * 0.01 for i in range(8760)]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        try:
            result = ingest_factory_load(path)
            assert len(result.loads_kw) == 8760
            assert result.detected_column == "root_array"
        finally:
            path.unlink()

    def test_nested_loads_kw(self):
        data = {"loads_kw": [100.0] * 8760}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        try:
            result = ingest_factory_load(path)
            assert len(result.loads_kw) == 8760
            assert result.detected_column == "loads_kw"
        finally:
            path.unlink()


# ── Validation gate ────────────────────────────────────────────────────


class TestValidationGate:
    def test_8760_length_required(self):
        data = [100.0] * 100
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        try:
            with pytest.raises(LoadLengthError) as exc_info:
                ingest_factory_load(path)
            assert exc_info.value.actual_length == 100
        finally:
            path.unlink()

    def test_15min_resolution_detected(self):
        data = [100.0] * 35040
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        try:
            with pytest.raises(LoadLengthError) as exc_info:
                ingest_factory_load(path)
            assert "15-minute" in exc_info.value.likely_resolution
        finally:
            path.unlink()

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            ingest_factory_load("/nonexistent/file.csv")

    def test_unsupported_format_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            path = Path(f.name)
        try:
            with pytest.raises(ValueError, match="Unsupported"):
                ingest_factory_load(path)
        finally:
            path.unlink()


# ── Negative clipping ──────────────────────────────────────────────────


class TestNegativeClipping:
    def test_negative_values_clipped_to_zero(self):
        values = [100.0] * 8759 + [-50.0]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(values, f)
            path = Path(f.name)

        try:
            result = ingest_factory_load(path)
            assert result.loads_kw[-1] == 0.0
            assert result.cleaning_summary["clipped_negative_count"] == 1
        finally:
            path.unlink()
