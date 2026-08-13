"""
Layer 5: End-to-end financial validation.

Loads a solved REopt result, runs the equity IRR computation, and asserts
IRR/NPV within expected ranges defined by a baseline JSON.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python" / "reopt"))

from equity_irr import compute_equity_irr

EXAMPLE_RESULTS = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "examples"
    / "wind_battery_hospital_reopt-results.json"
)

BASELINE_PATH = (
    REPO_ROOT / "tests" / "baselines" / "financial_e2e_baseline.json"
)

DEFAULT_DEBT_FRACTION = 0.70
DEFAULT_INTEREST_RATE = 0.085
DEFAULT_TENOR_YEARS = 10
DEFAULT_ANALYSIS_YEARS = 20
DEFAULT_ESCALATION_RATE = 0.05


def _extract_base_ebitda(results: dict, analysis_years: int = DEFAULT_ANALYSIS_YEARS) -> list[float]:
    fin = results.get("Financial", {})
    npv = fin.get("npv", 0) or 0
    lcc = fin.get("lcc", 0) or 0

    year_one_savings = fin.get("year_one_total_operating_cost_savings_before_tax")

    if not year_one_savings:
        et = results.get("ElectricTariff", {})
        bau = et.get("year_one_energy_cost_before_tax_bau", 0) or 0
        opt = et.get("year_one_energy_cost_before_tax", 0) or 0
        if bau and opt:
            year_one_savings = bau - opt
        else:
            bau = et.get("year_one_energy_cost_before", 0) or 0
            opt = et.get("year_one_energy_cost_after", 0) or 0
            if bau and opt:
                year_one_savings = bau - opt
            elif npv != 0:
                year_one_savings = abs(npv) / max(analysis_years, 1)
            elif lcc != 0:
                bau_lcc = fin.get("lcc_bau", lcc * 1.5)
                year_one_savings = abs(lcc - bau_lcc) / max(analysis_years, 1)
            else:
                year_one_savings = 0.0

    return [
        year_one_savings * (1 + DEFAULT_ESCALATION_RATE) ** y
        for y in range(analysis_years)
    ]


@pytest.mark.requires_artifacts
def test_e2e_financial_pipeline():
    if not EXAMPLE_RESULTS.is_file():
        pytest.skip(f"Example results not found: {EXAMPLE_RESULTS}")

    results = json.loads(EXAMPLE_RESULTS.read_text(encoding="utf-8"))
    fin = results.get("Financial", {})

    capex = fin.get("initial_capital_costs", 501384.14) or 501384.14
    ebitda = _extract_base_ebitda(results)

    irr_result = compute_equity_irr(
        ebitda_series=ebitda,
        total_capex=capex,
        debt_fraction=DEFAULT_DEBT_FRACTION,
        interest_rate=DEFAULT_INTEREST_RATE,
        debt_tenor_years=DEFAULT_TENOR_YEARS,
        analysis_years=DEFAULT_ANALYSIS_YEARS,
    )

    assert 0 < irr_result["equity_irr"] < 0.5, (
        f"Equity IRR {irr_result['equity_irr']:.4f} outside expected range (0, 0.5)"
    )

    assert irr_result["equity_npv_usd"] > 0, (
        f"Equity NPV ${irr_result['equity_npv_usd']:,.0f} should be positive"
    )

    baseline_data = {}
    if BASELINE_PATH.is_file():
        baseline_data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    if baseline_data:
        irr_min = baseline_data.get("equity_irr_min", 0)
        irr_max = baseline_data.get("equity_irr_max", 0.5)
        npv_min = baseline_data.get("equity_npv_min", 0)
        capex_expected = baseline_data.get("total_capex_usd")

        assert irr_min <= irr_result["equity_irr"] <= irr_max, (
            f"Equity IRR {irr_result['equity_irr']:.4f} outside baseline "
            f"[{irr_min:.4f}, {irr_max:.4f}]"
        )
        assert irr_result["equity_npv_usd"] >= npv_min, (
            f"Equity NPV ${irr_result['equity_npv_usd']:,.0f} below baseline minimum ${npv_min:,.0f}"
        )
        if capex_expected is not None:
            assert abs(capex - capex_expected) / capex_expected < 0.05, (
                f"CAPEX ${capex:,.0f} deviates >5% from baseline ${capex_expected:,.0f}"
            )
