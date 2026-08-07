"""
Phase F for 22kV branch — quick PySAM screening.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.integration.dppa_case_3 import (
    BASE_BESS_KW,
    BASE_BESS_KWH,
    BASE_PV_KWP,
    DEFAULT_DPPA_ADDER_VND_PER_KWH,
    DEFAULT_KPP_FACTOR,
    load_saigon18_cfmp_series,
    load_saigon18_fmp_series,
    load_saigon18_load_series,
    load_saigon18_tou_series,
)
from reopt_pysam_vn.pysam.single_owner import (
    build_single_owner_inputs,
    run_single_owner_model,
)
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

# Deal-specific FX: Saigon18 contract basis, 25,450 VND/USD.
# Intentionally NOT the repo canonical 26,400 (see plans/2026-07-26-post-backlog-architecture-plan.md ASM-005).
EXCHANGE_RATE = _resolve_exchange_rate(load_vietnam_data(), caller_value=25450.0)
REPORT_DATE = "2026-04-21"
DEFAULT_EXTRACTED = (
    REPO_ROOT
    / "data"
    / "interim"
    / "saigon18"
    / "2026-03-20_saigon18_extracted_inputs.json"
)
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "reports" / "saigon18"


def main():
    reopt_path = (
        REPO_ROOT
        / "artifacts/results/saigon18/2026-04-21_saigon18_dppa-case-3_bounded-opt_22kv_reopt-results.json"
    )
    extracted = json.loads(DEFAULT_EXTRACTED.read_text(encoding="utf-8"))
    reopt = json.loads(reopt_path.read_text(encoding="utf-8"))

    pv_kw = reopt.get("PV", {}).get("size_kw", BASE_PV_KWP)
    bess_kw = reopt.get("ElectricStorage", {}).get("size_kw", BASE_BESS_KW)
    bess_kwh = reopt.get("ElectricStorage", {}).get("size_kwh", BASE_BESS_KWH)

    pv_to_load = reopt.get("PV", {}).get("electric_to_load_series_kw", [])
    pv_to_grid = reopt.get("PV", {}).get("electric_to_grid_series_kw", [])

    if pv_to_load and pv_to_grid:
        generation_profile_kw = [
            float(pv_to_load[i]) + float(pv_to_grid[i]) for i in range(8760)
        ]
    else:
        annual_gen = reopt.get("PV", {}).get(
            "year_one_energy_produced_kwh", pv_kw * 1500.0
        )
        generation_profile_kw = [annual_gen / 8760.0] * 8760

    annual_gen_kwh = sum(generation_profile_kw)

    load = load_saigon18_load_series(extracted)
    cfmp = load_saigon18_cfmp_series(extracted)
    fmp = load_saigon18_fmp_series(extracted)
    tou = load_saigon18_tou_series(extracted)

    annual_load_kwh = sum(load)
    avg_tou = sum(tou) / len(tou) if tou else 0.0
    avg_cfmp = sum(cfmp) / len(cfmp) if cfmp else 0.0
    avg_fmp = sum(fmp) / len(fmp) if fmp else 0.0
    market_price_vnd = avg_cfmp if avg_cfmp > 0 else avg_fmp
    weighted_evn = avg_tou
    strike_vnd = weighted_evn * 0.95
    adder = DEFAULT_DPPA_ADDER_VND_PER_KWH
    kpp = DEFAULT_KPP_FACTOR
    matched_kwh = min(annual_load_kwh, annual_gen_kwh)
    developer_rate_vnd = (
        float(strike_vnd) + float(adder) + float(market_price_vnd) * float(kpp)
    )
    developer_rate_usd = developer_rate_vnd / EXCHANGE_RATE

    capital_cost_usd = float(
        reopt.get("Financial", {}).get("initial_capital_costs_after_incentives")
        or reopt.get("Financial", {}).get("initial_capital_costs", 0.0)
    )
    if capital_cost_usd == 0.0:
        capital_cost_usd = pv_kw * 750.0 + bess_kw * 200.0 + bess_kwh * 175.0

    fixed_om_usd = pv_kw * 6.0
    depreciation_schedule = tuple(100.0 for _ in range(25))

    so_inputs = build_single_owner_inputs(
        system_capacity_kw=pv_kw,
        generation_profile_kw=generation_profile_kw,
        annual_generation_kwh=annual_gen_kwh,
        installed_cost_usd=capital_cost_usd,
        fixed_om_usd_per_year=fixed_om_usd,
        ppa_price_input_usd_per_kwh=developer_rate_usd,
        analysis_years=20,
        debt_fraction=0.70,
        target_irr_fraction=0.15,
        owner_tax_rate_fraction=0.20,
        owner_discount_rate_fraction=0.08,
        inflation_rate_fraction=0.04,
        debt_interest_rate_fraction=0.085,
        debt_tenor_years=10,
        ppa_escalation_rate_fraction=0.04,
        om_escalation_rate_fraction=0.03,
        depreciation_schedule=depreciation_schedule,
        metadata={
            "tariff_branch": "22kv_two_part",
            "pv_kw": pv_kw,
            "bess_kw": bess_kw,
            "bess_kwh": bess_kwh,
        },
    )

    pysam_result = run_single_owner_model(so_inputs)

    outputs = pysam_result.get("outputs", {})
    npv = outputs.get("project_return_aftertax_npv")
    min_dscr = outputs.get("min_dscr")
    irr = outputs.get("project_return_aftertax_irr")

    if npv is not None and npv < 0:
        decision = "reject_current_case"
        reason = f"After-tax NPV {npv:,.0f} USD < 0; project does not clear developer return threshold"
    elif min_dscr is not None and min_dscr < 1.0:
        decision = "reject_current_case"
        reason = f"Min DSCR {min_dscr:.3f} < 1.0; debt service coverage inadequate"
    elif npv is not None and npv > 0 and (min_dscr is None or min_dscr >= 1.0):
        decision = "advance"
        reason = f"After-tax NPV {npv:,.0f} USD > 0 and min DSCR {min_dscr:.3f if min_dscr else 'N/A'} >= 1.0"
    else:
        decision = "revise_assumptions"
        reason = "Inconclusive: review PySAM outputs manually"

    screening = {
        "model": "Saigon18 DPPA Case 3 22kV Developer Screening",
        "status": pysam_result.get("status", "unknown"),
        "inputs": {
            "pv_size_kw": pv_kw,
            "bess_size_kw": bess_kw,
            "bess_size_kwh": bess_kwh,
            "annual_gen_kwh": annual_gen_kwh,
            "matched_kwh": matched_kwh,
            "capital_cost_usd": capital_cost_usd,
            "developer_rate_vnd_per_kwh": round(developer_rate_vnd, 4),
            "developer_rate_usd_per_kwh": round(developer_rate_usd, 6),
            "strike_vnd_per_kwh": round(float(strike_vnd), 4),
            "dppa_adder_vnd_per_kwh": float(adder),
            "kpp_factor": float(kpp),
            "market_price_vnd_per_kwh": round(float(market_price_vnd), 6),
            "exchange_rate_vnd_per_usd": EXCHANGE_RATE,
            "fixed_om_usd_per_year": fixed_om_usd,
        },
        "pysam": pysam_result,
        "decision": {
            "class": decision,
            "npv_usd": npv,
            "min_dscr": min_dscr,
            "irr_fraction": irr,
            "reason": reason,
        },
    }

    out_path = (
        ARTIFACT_DIR
        / f"{REPORT_DATE}_saigon18_dppa-case-3_22kv_developer-screening.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(screening, indent=2), encoding="utf-8")
    print(f"Written: {out_path}")
    print(f"Decision: {decision} | NPV: {npv} | Min DSCR: {min_dscr}")


if __name__ == "__main__":
    main()
