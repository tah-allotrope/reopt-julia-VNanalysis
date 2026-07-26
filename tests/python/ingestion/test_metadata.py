"""Tests for metadata extraction, TOU classification, and industry archetype detection."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.ingestion.loader import ingest_factory_load
from reopt_pysam_vn.ingestion.metadata import (
    ArchetypeResult,
    LoadMetadata,
    TOUClassification,
    classify_industry_archetype,
    classify_tou_consumption,
    extract_load_metadata,
)

CASE_STUDIES = REPO_ROOT / "scenarios" / "case_studies"


@pytest.fixture
def saigon18_loads() -> list[float]:
    path = CASE_STUDIES / "saigon18" / "2026-03-20_scenario-a_fixed-sizing_evntou.json"
    if not path.exists():
        pytest.skip("saigon18 scenario JSON not available")
    result = ingest_factory_load(path)
    return result.loads_kw


@pytest.fixture
def ninhsim_loads() -> list[float]:
    path = CASE_STUDIES / "ninhsim" / "NinhsimSample.csv"
    if not path.exists():
        pytest.skip("ninhsim CSV not available")
    result = ingest_factory_load(path)
    return result.loads_kw


@pytest.fixture
def flat_loads() -> list[float]:
    return [1000.0] * 8760


# ── extract_load_metadata ──────────────────────────────────────────────


class TestExtractLoadMetadata:
    def test_saigon18_peak_demand(self, saigon18_loads):
        meta = extract_load_metadata(saigon18_loads, year=2024)
        assert isinstance(meta, LoadMetadata)
        assert abs(meta.peak_demand_kw - 30246) / 30246 < 0.01

    def test_saigon18_annual_consumption(self, saigon18_loads):
        meta = extract_load_metadata(saigon18_loads, year=2024)
        assert abs(meta.annual_consumption_mwh - 184260) / 184260 < 0.02

    def test_load_factor_range(self, saigon18_loads):
        meta = extract_load_metadata(saigon18_loads, year=2024)
        assert 0.0 < meta.load_factor <= 1.0

    def test_daytime_nighttime_split(self, saigon18_loads):
        meta = extract_load_metadata(saigon18_loads, year=2024)
        assert meta.daytime_avg_kw > 0
        assert meta.nighttime_avg_kw > 0

    def test_weekend_weekday_split(self, saigon18_loads):
        meta = extract_load_metadata(saigon18_loads, year=2024)
        assert meta.weekday_avg_kw > 0
        assert meta.weekend_avg_kw > 0

    def test_flat_load_perfect_load_factor(self, flat_loads):
        meta = extract_load_metadata(flat_loads, year=2024)
        assert meta.load_factor == pytest.approx(1.0)
        assert meta.peak_demand_kw == 1000.0
        assert meta.average_demand_kw == 1000.0

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="8760"):
            extract_load_metadata([100.0] * 100)


# ── classify_tou_consumption ───────────────────────────────────────────


class TestTOUClassification:
    def test_decision_963_nonzero_peak_share(self, saigon18_loads):
        tou = classify_tou_consumption(
            saigon18_loads,
            customer_type="industrial",
            voltage_level="medium_voltage_22kv_to_110kv",
            regime_id="decision_963_2026_current",
            year=2024,
        )
        assert isinstance(tou, TOUClassification)
        assert tou.peak_share_pct > 0
        assert tou.offpeak_share_pct > 0
        assert tou.normal_share_pct > 0

    def test_shares_sum_to_100(self, saigon18_loads):
        tou = classify_tou_consumption(saigon18_loads, year=2024)
        total = tou.peak_share_pct + tou.offpeak_share_pct + tou.normal_share_pct
        assert abs(total - 100.0) < 0.01

    def test_consumption_sums_to_annual(self, saigon18_loads):
        tou = classify_tou_consumption(saigon18_loads, year=2024)
        total_mwh = tou.peak_consumption_mwh + tou.offpeak_consumption_mwh + tou.normal_consumption_mwh
        annual_mwh = sum(saigon18_loads) / 1000.0
        assert abs(total_mwh - annual_mwh) / annual_mwh < 0.001

    def test_flat_load_peak_share_matches_hour_fraction(self, flat_loads):
        tou = classify_tou_consumption(flat_loads, year=2024)
        # Decision 963: 6 peak hours/day on weekdays (Mon-Sat), 0 on Sunday
        # 313 weekdays (Mon-Sat in 2024) * 6 peak hours = 1878 peak hours
        # Total 8760 hours
        # Peak share ~ 1878/8760 ~ 21.4%
        assert 18.0 < tou.peak_share_pct < 25.0

    def test_ninhsim_tou(self, ninhsim_loads):
        tou = classify_tou_consumption(ninhsim_loads, year=2024)
        assert tou.peak_consumption_mwh > 0
        assert tou.regime_id == "decision_963_2026_current"

    def test_with_vn_data(self, saigon18_loads):
        """Test TOU classification with real VNData for regime resolution."""
        try:
            from reopt_pysam_vn.reopt.preprocess import load_vietnam_data
            vn = load_vietnam_data()
        except Exception:
            pytest.skip("VNData not loadable")

        tou = classify_tou_consumption(
            saigon18_loads,
            customer_type="industrial",
            voltage_level="medium_voltage_22kv_to_110kv",
            regime_id="decision_963_2026_current",
            year=2024,
            vn=vn,
        )
        assert tou.peak_share_pct > 0
        total = tou.peak_share_pct + tou.offpeak_share_pct + tou.normal_share_pct
        assert abs(total - 100.0) < 0.01


# ── classify_industry_archetype ────────────────────────────────────────


class TestArchetypeClassification:
    def test_saigon18_archetype(self, saigon18_loads):
        result = classify_industry_archetype(saigon18_loads, year=2024)
        assert isinstance(result, ArchetypeResult)
        assert result.archetype in [
            "continuous_process",
            "two_shift_factory",
            "single_shift_factory",
            "commercial_daytime",
            "commercial_extended",
        ]
        assert result.confidence in ["high", "medium", "low"]

    def test_ninhsim_archetype(self, ninhsim_loads):
        result = classify_industry_archetype(ninhsim_loads, year=2024)
        assert result.archetype in [
            "continuous_process",
            "two_shift_factory",
        ]

    def test_flat_load_classified_as_continuous(self, flat_loads):
        result = classify_industry_archetype(flat_loads, year=2024)
        assert result.archetype == "continuous_process"
        assert result.confidence == "high"

    def test_single_shift_pattern(self):
        """Synthetic single-shift: high weekday daytime, near-zero nights/weekends."""
        loads = []
        start = __import__("datetime").date(2024, 1, 1)
        for day_offset in range(365):
            d = start + __import__("datetime").timedelta(days=day_offset)
            dow = d.isoweekday()
            for hour in range(24):
                if dow <= 5 and 8 <= hour < 17:
                    loads.append(1000.0)
                else:
                    loads.append(50.0)

        result = classify_industry_archetype(loads, year=2024)
        assert result.archetype == "single_shift_factory"

    def test_commercial_daytime_pattern(self):
        """Synthetic commercial: high 9-5, moderate evenings, low nights."""
        loads = []
        start = __import__("datetime").date(2024, 1, 1)
        for day_offset in range(365):
            d = start + __import__("datetime").timedelta(days=day_offset)
            dow = d.isoweekday()
            for hour in range(24):
                if dow <= 5 and 9 <= hour < 17:
                    loads.append(800.0)
                elif dow <= 5 and (7 <= hour < 9 or 17 <= hour < 21):
                    loads.append(400.0)
                elif dow == 6:
                    loads.append(300.0)
                else:
                    loads.append(100.0)

        result = classify_industry_archetype(loads, year=2024)
        assert result.archetype in ["commercial_daytime", "single_shift_factory"]

    def test_at_least_4_case_studies_classified(self):
        """Verify archetype classification succeeds for at least 4 of 6 case studies."""
        classified_count = 0
        case_files = [
            ("ninhsim", CASE_STUDIES / "ninhsim" / "NinhsimSample.csv"),
            ("regina", CASE_STUDIES / "regina" / "Regina.xlsx"),
            ("saigon18", CASE_STUDIES / "saigon18" / "2026-03-20_scenario-a_fixed-sizing_evntou.json"),
            ("emivest", CASE_STUDIES / "emivest" / "Emivest.csv"),
            ("verdant", CASE_STUDIES / "verdant" / "Verdant.csv"),
        ]

        for name, path in case_files:
            if not path.exists():
                continue
            try:
                result = ingest_factory_load(path)
                archetype = classify_industry_archetype(result.loads_kw, year=2024)
                assert archetype.archetype in [
                    "continuous_process",
                    "two_shift_factory",
                    "single_shift_factory",
                    "commercial_daytime",
                    "commercial_extended",
                ]
                classified_count += 1
            except Exception:
                pass

        assert classified_count >= 4, f"Only classified {classified_count}/5 case studies"

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="8760"):
            classify_industry_archetype([100.0] * 100)
