"""Tests for procurement evaluation pipelines (GAP-02 PHASE-02)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.procurement import (
    OffsiteEvaluation,
    OnsiteEvaluation,
    ProjectConfig,
    evaluate_offsite,
    evaluate_onsite,
)

SAIGON18_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "saigon18"
    / "2026-03-20_saigon18_extracted_inputs.json"
)


def _synthetic_gen_8760(capacity_mw: float, capacity_factor: float = 0.18) -> list[float]:
    """Generate a simple synthetic 8760 generation profile."""
    hourly_kw = capacity_mw * 1000.0 * capacity_factor
    return [hourly_kw] * 8760


def _synthetic_fmp_8760(base_vnd_kwh: float = 1.5) -> list[float]:
    """Generate a simple synthetic 8760 FMP profile."""
    return [base_vnd_kwh] * 8760


def _synthetic_tariff_8760(base_vnd_kwh: float = 2.0) -> list[float]:
    """Generate a simple synthetic 8760 tariff profile."""
    return [base_vnd_kwh] * 8760


class TestOnsiteEvaluation:
    """Test onsite (private-wire) evaluation pipeline."""

    @pytest.fixture
    def loads(self):
        if not SAIGON18_EXTRACTED.exists():
            pytest.skip("Saigon18 extracted inputs not available")
        data = json.loads(SAIGON18_EXTRACTED.read_text(encoding="utf-8"))
        return data["loads_kw"][:8760]

    def test_evaluate_onsite_produces_buyer_savings(self, loads):
        project = ProjectConfig(
            project_id="saigon18_onsite",
            name="Saigon18 Onsite Solar+BESS",
            technology="solar_bess",
            capacity_mw=40.0,
            bess_mw=20.0,
            bess_mwh=66.0,
            grid_connection="onsite_private_wire",
            generation_profile_kw=_synthetic_gen_8760(40.0),
            indicative_strike_vnd_kwh=1012.0,
        )

        tariff = _synthetic_tariff_8760(2.0)

        result = evaluate_onsite(loads, project, tariff)

        assert isinstance(result, OnsiteEvaluation)
        assert result.settlement.annual_summary["buyer_cost_vnd"] > 0
        assert result.settlement.annual_summary["matched_mwh"] > 0
        assert result.re_penetration_pct > 0
        assert result.export_exposure_pct >= 0

    def test_evaluate_onsite_missing_generation_raises(self, loads):
        project = ProjectConfig(
            project_id="no_gen",
            name="No Generation",
            technology="solar",
            capacity_mw=10.0,
        )

        with pytest.raises(ValueError, match="no generation_profile_kw"):
            evaluate_onsite(loads, project, _synthetic_tariff_8760())

    def test_evaluate_onsite_default_strike(self, loads):
        project = ProjectConfig(
            project_id="default_strike",
            name="Default Strike",
            technology="solar",
            capacity_mw=10.0,
            generation_profile_kw=_synthetic_gen_8760(10.0),
        )

        result = evaluate_onsite(loads, project, _synthetic_tariff_8760())
        assert result.settlement.contract_params.strike_vnd_kwh == 1012.0


class TestOffsiteEvaluation:
    """Test offsite (virtual CfD) evaluation pipeline."""

    @pytest.fixture
    def loads(self):
        if not SAIGON18_EXTRACTED.exists():
            pytest.skip("Saigon18 extracted inputs not available")
        data = json.loads(SAIGON18_EXTRACTED.read_text(encoding="utf-8"))
        return data["loads_kw"][:8760]

    def test_evaluate_offsite_produces_cfd_results(self, loads):
        project = ProjectConfig(
            project_id="ninhsim_offsite",
            name="Ninhsim Offsite CfD",
            technology="solar_wind",
            capacity_mw=54.0,
            grid_connection="offsite_grid_connected",
            generation_profile_kw=_synthetic_gen_8760(54.0, 0.25),
            indicative_strike_vnd_kwh=1800.0,
            dppa_structure="virtual_cfd",
        )

        tariff = _synthetic_tariff_8760(2.0)
        fmp = _synthetic_fmp_8760(1.5)

        result = evaluate_offsite(loads, project, tariff, fmp)

        assert isinstance(result, OffsiteEvaluation)
        assert result.settlement.annual_summary["buyer_cost_vnd"] > 0
        assert result.settlement.annual_summary["matched_mwh"] > 0
        assert result.re_penetration_pct > 0
        assert 0 <= result.fmp_risk_score <= 100

    def test_evaluate_offsite_missing_generation_raises(self, loads):
        project = ProjectConfig(
            project_id="no_gen_offsite",
            name="No Generation",
            technology="wind",
            capacity_mw=20.0,
        )

        with pytest.raises(ValueError, match="no generation_profile_kw"):
            evaluate_offsite(loads, project, _synthetic_tariff_8760(), _synthetic_fmp_8760())

    def test_evaluate_offsite_default_strike(self, loads):
        project = ProjectConfig(
            project_id="default_strike_offsite",
            name="Default Strike Offsite",
            technology="solar",
            capacity_mw=20.0,
            generation_profile_kw=_synthetic_gen_8760(20.0),
        )

        result = evaluate_offsite(loads, project, _synthetic_tariff_8760(), _synthetic_fmp_8760())
        assert result.settlement.contract_params.strike_vnd_kwh == 1800.0


class TestProcurementComparison:
    """Test side-by-side comparison logic (GAP-02 PHASE-03)."""

    @pytest.fixture
    def loads(self):
        if not SAIGON18_EXTRACTED.exists():
            pytest.skip("Saigon18 extracted inputs not available")
        data = json.loads(SAIGON18_EXTRACTED.read_text(encoding="utf-8"))
        return data["loads_kw"][:8760]

    def _make_onsite(self, loads, strike: float = 1012.0) -> OnsiteEvaluation:
        project = ProjectConfig(
            project_id="onsite_test",
            name="Test Onsite",
            technology="solar_bess",
            capacity_mw=40.0,
            grid_connection="onsite_private_wire",
            generation_profile_kw=_synthetic_gen_8760(40.0),
            indicative_strike_vnd_kwh=strike,
        )
        return evaluate_onsite(loads, project, _synthetic_tariff_8760(2.0))

    def _make_offsite(self, loads, strike: float = 1800.0) -> OffsiteEvaluation:
        project = ProjectConfig(
            project_id="offsite_test",
            name="Test Offsite",
            technology="solar_wind",
            capacity_mw=54.0,
            grid_connection="offsite_grid_connected",
            generation_profile_kw=_synthetic_gen_8760(54.0, 0.25),
            indicative_strike_vnd_kwh=strike,
        )
        return evaluate_offsite(loads, project, _synthetic_tariff_8760(2.0), _synthetic_fmp_8760(1.5))

    def test_comparison_produces_complete_artifact(self, loads):
        from reopt_pysam_vn.integration.procurement import compare_procurement_options

        onsite = self._make_onsite(loads)
        offsite = self._make_offsite(loads)

        comparison = compare_procurement_options(
            onsite, offsite,
            {"factory_id": "test_factory", "name": "Test Factory"},
        )

        assert comparison.factory_id == "test_factory"
        assert comparison.onsite is not None
        assert comparison.offsite is not None
        assert comparison.recommendation in ("onsite", "offsite", "neither")
        assert comparison.recommendation_reason != ""
        assert isinstance(comparison.delta, dict)
        assert isinstance(comparison.regulatory_flags, list)

    def test_comparison_to_dict(self, loads):
        from reopt_pysam_vn.integration.procurement import compare_procurement_options

        onsite = self._make_onsite(loads)
        offsite = self._make_offsite(loads)

        comparison = compare_procurement_options(onsite, offsite)
        d = comparison.to_dict()

        assert d["onsite"] is not None
        assert d["offsite"] is not None
        assert d["recommendation"] != ""
        assert "buyer_cost_delta_vnd" in d["delta"]

    def test_onsite_only_recommendation(self, loads):
        from reopt_pysam_vn.integration.procurement import compare_procurement_options

        onsite = self._make_onsite(loads)

        comparison = compare_procurement_options(onsite, None)
        assert comparison.recommendation == "onsite"

    def test_offsite_only_recommendation(self, loads):
        from reopt_pysam_vn.integration.procurement import compare_procurement_options

        offsite = self._make_offsite(loads)

        comparison = compare_procurement_options(None, offsite)
        assert comparison.recommendation == "offsite"

    def test_neither_recommendation(self):
        from reopt_pysam_vn.integration.procurement import compare_procurement_options

        comparison = compare_procurement_options(None, None)
        assert comparison.recommendation == "neither"

    def test_delta_fields_populated(self, loads):
        from reopt_pysam_vn.integration.procurement import compare_procurement_options

        onsite = self._make_onsite(loads)
        offsite = self._make_offsite(loads)

        comparison = compare_procurement_options(onsite, offsite)

        assert "buyer_cost_delta_vnd" in comparison.delta
        assert "buyer_savings_delta_vnd" in comparison.delta
        assert "developer_revenue_delta_vnd" in comparison.delta
        assert "onsite_cheaper_by_pct" in comparison.delta
