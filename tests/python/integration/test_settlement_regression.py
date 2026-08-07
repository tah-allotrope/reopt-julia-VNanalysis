"""Regression tests: generalized settlement vs existing Case 1 and Case 2 outputs (GAP-04 PHASE-03).

These tests extract the exact input series from reference settlement artifacts
and replay them through the generalized engine, asserting < 1% deviation on
annual totals.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.settlement import (
    ContractParams,
    compute_hourly_settlement,
)

NINHSIM_SETTLEMENT = (
    REPO_ROOT / "artifacts" / "reports" / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_buyer-settlement.json"
)

SAIGON18_SETTLEMENT = (
    REPO_ROOT / "artifacts" / "reports" / "saigon18"
    / "2026-03-29_scenario-d_dppa-settlement.json"
)

SAIGON18_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "saigon18"
    / "2026-03-20_saigon18_extracted_inputs.json"
)

SAIGON18_REOPT = (
    REPO_ROOT / "artifacts" / "results" / "saigon18"
    / "2026-03-20_scenario-d_dppa-baseline_reopt-results.json"
)


def _pct_deviation(actual: float, expected: float) -> float:
    if expected == 0.0:
        return 0.0 if actual == 0.0 else float("inf")
    return abs(actual - expected) / abs(expected) * 100.0


class TestNinhsimCaseRegression:
    """Replay ninhsim DPPA Case 2 buyer settlement through generalized engine."""

    @pytest.fixture(scope="class")
    def reference(self):
        if not NINHSIM_SETTLEMENT.exists():
            pytest.skip("Ninhsim settlement artifact not available")
        return json.loads(NINHSIM_SETTLEMENT.read_text(encoding="utf-8"))

    @pytest.fixture(scope="class")
    def generalized_result(self, reference):
        ledger = reference["hourly_ledger"]
        loads = [entry["load_kwh"] for entry in ledger]
        generation = [entry["contracted_generation_kwh"] for entry in ledger]
        market = [entry["market_reference_price_vnd_per_kwh"] for entry in ledger]
        retail = [entry["evn_retail_rate_vnd_per_kwh"] for entry in ledger]

        params = reference["parameters"]
        kpp_factor = params["kpp_factor"]
        kpp_pct = (kpp_factor - 1.0) * 100.0

        contract = ContractParams(
            mode="virtual_cfd",
            strike_vnd_kwh=params["strike_price_vnd_per_kwh"],
            settlement_quantity_rule="matched_only",
            excess_treatment="curtail",
            dppa_adder_vnd_kwh=params["dppa_adder_vnd_per_kwh"],
            kpp_pct=kpp_pct,
        )

        return compute_hourly_settlement(
            loads, generation, retail, market, contract,
            market_source_label="proxy_cfmp_or_fmp",
        )

    def test_matched_quantity_within_1pct(self, reference, generalized_result):
        expected = reference["summary"]["matched_quantity_kwh"]
        actual = generalized_result.annual_summary["matched_mwh"] * 1000.0
        assert _pct_deviation(actual, expected) < 1.0, (
            f"matched: {actual:.0f} vs {expected:.0f} ({_pct_deviation(actual, expected):.2f}%)"
        )

    def test_shortfall_quantity_within_1pct(self, reference, generalized_result):
        expected = reference["summary"]["shortfall_quantity_kwh"]
        actual = generalized_result.annual_summary["shortfall_mwh"] * 1000.0
        assert _pct_deviation(actual, expected) < 1.0

    def test_excess_quantity_within_1pct(self, reference, generalized_result):
        expected = reference["summary"]["excess_quantity_kwh"]
        actual = generalized_result.annual_summary["excess_mwh"] * 1000.0
        assert _pct_deviation(actual, expected) < 1.0

    def test_buyer_evn_matched_payment_within_1pct(self, reference, generalized_result):
        expected = reference["summary"]["buyer_evn_matched_payment_vnd"]
        actual = generalized_result.annual_summary["buyer_evn_matched_payment_vnd"]
        assert _pct_deviation(actual, expected) < 1.0

    def test_buyer_dppa_charge_within_1pct(self, reference, generalized_result):
        expected = reference["summary"]["buyer_dppa_charge_vnd"]
        actual = generalized_result.annual_summary["buyer_dppa_charge_vnd"]
        assert _pct_deviation(actual, expected) < 1.0

    def test_buyer_shortfall_payment_within_1pct(self, reference, generalized_result):
        expected = reference["summary"]["buyer_shortfall_payment_vnd"]
        actual = generalized_result.annual_summary["buyer_shortfall_payment_vnd"]
        assert _pct_deviation(actual, expected) < 1.0

    def test_buyer_cfd_payment_within_1pct(self, reference, generalized_result):
        expected = reference["summary"]["buyer_cfd_payment_vnd"]
        actual = generalized_result.annual_summary["buyer_cfd_payment_vnd"]
        assert _pct_deviation(actual, expected) < 1.0

    def test_buyer_total_payment_within_1pct(self, reference, generalized_result):
        expected = reference["summary"]["buyer_total_payment_vnd"]
        actual = generalized_result.annual_summary["buyer_cost_vnd"]
        assert _pct_deviation(actual, expected) < 1.0, (
            f"total: {actual:.0f} vs {expected:.0f} ({_pct_deviation(actual, expected):.2f}%)"
        )

    def test_buyer_blended_cost_within_1pct(self, reference, generalized_result):
        expected = reference["summary"]["buyer_blended_cost_vnd_per_kwh"]
        actual = generalized_result.annual_summary["buyer_blended_rate_vnd_kwh"]
        assert _pct_deviation(actual, expected) < 1.0

    def test_negative_cfd_hours_match(self, reference, generalized_result):
        expected = reference["summary"]["hours_with_negative_cfd_credit"]
        actual = generalized_result.annual_summary["hours_with_negative_cfd"]
        assert actual == expected


class TestSaigon18CaseRegression:
    """Replay saigon18 DPPA private-wire settlement through generalized engine.

    The original dppa_settlement.py uses a delivery_factor (0.98) that multiplies
    delivered kWh before settlement. The generalized engine does not have this
    concept — it settles on raw matched quantity. We account for this by
    pre-scaling the generation series by the delivery factor.
    """

    @pytest.fixture(scope="class")
    def reference(self):
        if not SAIGON18_SETTLEMENT.exists():
            pytest.skip("Saigon18 settlement artifact not available")
        return json.loads(SAIGON18_SETTLEMENT.read_text(encoding="utf-8"))

    @pytest.fixture(scope="class")
    def extracted(self):
        if not SAIGON18_EXTRACTED.exists():
            pytest.skip("Saigon18 extracted inputs not available")
        return json.loads(SAIGON18_EXTRACTED.read_text(encoding="utf-8"))

    @pytest.fixture(scope="class")
    def reopt_results(self):
        if not SAIGON18_REOPT.exists():
            pytest.skip("Saigon18 REopt results not available")
        return json.loads(SAIGON18_REOPT.read_text(encoding="utf-8"))

    @pytest.fixture(scope="class")
    def generalized_result(self, reference, extracted, reopt_results):
        loads = extracted["loads_kw"][:8760]

        pv = reopt_results.get("PV", {})
        storage = reopt_results.get("ElectricStorage", {})
        pv_to_load = pv.get("electric_to_load_series_kw", [])
        bess_to_load = storage.get("storage_to_load_series_kw", [])

        def pad(s):
            if len(s) >= 8760:
                return [float(v) for v in s[:8760]]
            return [float(v) for v in s] + [0.0] * (8760 - len(s))

        delivery = [a + b for a, b in zip(pad(pv_to_load), pad(bess_to_load))]

        delivery_factor = reference["delivery_factor"]
        generation_scaled = [d * delivery_factor for d in delivery]

        strike = reference["strike_price_vnd_per_kwh"]

        tariff = [0.0] * 8760
        fmp = [0.0] * 8760

        contract = ContractParams(
            mode="private_wire",
            strike_vnd_kwh=strike,
            excess_treatment="curtail",
            dppa_adder_vnd_kwh=0.0,
            kpp_pct=0.0,
        )

        return compute_hourly_settlement(
            loads, generation_scaled, tariff, fmp, contract,
        )

    def test_total_delivered_quantity_within_1pct(self, reference, generalized_result):
        expected = reference["total_q_kwh"]
        actual = generalized_result.annual_summary["matched_mwh"] * 1000.0
        assert _pct_deviation(actual, expected) < 1.0, (
            f"delivered: {actual:.0f} vs {expected:.0f} ({_pct_deviation(actual, expected):.2f}%)"
        )

    def test_total_settlement_revenue_within_1pct(self, reference, generalized_result):
        expected = reference["total_settlement_vnd"]
        actual = generalized_result.annual_summary["developer_revenue_vnd"]
        assert _pct_deviation(actual, expected) < 1.0, (
            f"revenue: {actual:.0f} vs {expected:.0f} ({_pct_deviation(actual, expected):.2f}%)"
        )

    def test_hours_with_settlement_match(self, reference, generalized_result):
        expected = reference["hours_with_settlement"]
        ledger = generalized_result.hourly_ledger
        actual = sum(1 for e in ledger if e["matched_kwh"] > 0)
        assert actual == expected, f"settlement hours: {actual} vs {expected}"
