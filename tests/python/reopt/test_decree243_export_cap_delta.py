"""Tests for reopt_pysam_vn.reopt.decree243_delta (PHASE-03 of
plans/2026-07-18-decree-243-currency-webapp-hardening-plan.md).

Fixed-dispatch (no re-optimization) first-order quantification of the
Decree 243/2026 export-cap change (20% -> 50%) using the settlement engine's
own hourly cap semantics. No artifacts, no network, no PySAM.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.decree243_delta import (
    compute_export_cap_delta,
    extract_saigon18_series,
)

EXAMPLE_PATH = REPO_ROOT / "examples" / "saigon18_scenario-a_reopt-solve.example.json"


class TestComputeExportCapDelta:
    def test_flat_toy_profile_closed_form(self):
        loads = [40.0] * 8760
        generation = [100.0] * 8760
        tariff = [2000.0] * 8760

        result = compute_export_cap_delta(loads, generation, tariff)

        assert result["exported_kwh_cap20"] == pytest.approx(20.0 * 8760)
        assert result["exported_kwh_cap50"] == pytest.approx(50.0 * 8760)
        assert result["curtailed_kwh_cap20"] == pytest.approx(40.0 * 8760)
        assert result["curtailed_kwh_cap50"] == pytest.approx(10.0 * 8760)
        assert result["surplus_revenue_vnd_cap20"] == pytest.approx(20.0 * 8760 * 671.0)
        assert result["surplus_revenue_vnd_cap50"] == pytest.approx(50.0 * 8760 * 671.0)
        assert result["delta_exported_kwh"] == pytest.approx(262_800.0)
        assert result["delta_surplus_revenue_vnd"] == pytest.approx(176_338_800.0)
        assert result["delta_surplus_revenue_usd"] == pytest.approx(176_338_800.0 / 26_400.0)

    def test_monotonicity_on_peaky_profile(self):
        loads = [10.0] * 8760
        generation = [0.0] * 8759 + [5000.0]
        tariff = [1900.0] * 8760

        result = compute_export_cap_delta(loads, generation, tariff)

        assert result["delta_exported_kwh"] >= 0.0
        assert result["curtailed_kwh_cap50"] <= result["curtailed_kwh_cap20"]

    def test_length_guard(self):
        with pytest.raises(ValueError):
            compute_export_cap_delta([1.0] * 100, [1.0] * 8760, [1.0] * 8760)

    def test_custom_exchange_rate(self):
        loads = [40.0] * 8760
        generation = [100.0] * 8760
        tariff = [2000.0] * 8760

        result = compute_export_cap_delta(
            loads, generation, tariff, exchange_rate_vnd_per_usd=20_000.0
        )
        assert result["delta_surplus_revenue_usd"] == pytest.approx(176_338_800.0 / 20_000.0)


class TestExtractSaigon18Series:
    @pytest.mark.skipif(not EXAMPLE_PATH.exists(), reason="golden example file not present")
    def test_real_file_smoke(self):
        series = extract_saigon18_series(EXAMPLE_PATH)

        assert len(series["loads_kw"]) == 8760
        assert len(series["generation_kw"]) == 8760
        assert len(series["tariff_vnd_per_kwh"]) == 8760
        assert sum(series["generation_kw"]) > 0
        assert all(v > 0 for v in series["tariff_vnd_per_kwh"])

    def test_missing_series_raises_keyerror(self, tmp_path):
        import json

        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"PV": {}, "ElectricLoad": {}, "ElectricTariff": {}}), encoding="utf-8")
        with pytest.raises(KeyError):
            extract_saigon18_series(bad)
