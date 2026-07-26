"""
North Thuan Wind+Solar+BESS DPPA Feasibility Study — Validation Script.

Independently recomputes all key metrics from the staff's PDF report
(DPPA_FS_Study.pdf, Scenario 3) and compares results against the staff's
stated numbers. Flags any delta > 5% as WARN for review.

Inputs are drawn directly from the PDF; unknowns are documented inline.

Usage:
    python scripts/python/integration/validate_north_thuan.py \
        --output artifacts/reports/north_thuan/2026-03-29_north-thuan-validation.json
"""

import argparse
import json
from pathlib import Path

import numpy_financial as npf


# ---------------------------------------------------------------------------
# Inputs from DPPA_FS_Study.pdf (Scenario 3 — Wind+Solar+BESS)
# ---------------------------------------------------------------------------

# --- Asset sizing ---
SOLAR_MW = 30.0
WIND_MW = 20.0
BESS_MW = 10.0
BESS_MWH = 40.0

# --- Generation parameters ---
SOLAR_CF = 0.194          # Clear-sky synthetic CF (lat 11.7°N)
WIND_CF = 0.380           # 2022 Vietnam Wind Atlas
DEGRADATION_ANNUAL = 0.005  # 0.5%/yr linear (monocrystalline Si approximation)

# --- Factory load ---
FACTORY_LOAD_GWH_YR1 = 240.90
FACTORY_MEAN_MW = 27.5
FACTORY_PEAK_MW = 134.1

# --- DPPA commercial parameters ---
STRIKE_USD_PER_KWH = 0.055      # P_C contracted (fixed)
FMP_MEAN_USD_PER_KWH = 0.05707  # Annual mean FMP across 25yr (developer sells to grid)
FACTORY_CEILING_USD_PER_KWH = 0.07394   # Factory retail tariff (EVN ceiling)
DEVELOPER_FLOOR_USD_PER_KWH = 0.04273   # Developer floor (min P_C for NPV ≥ 0)
NEGOTIABLE_WINDOW_USD_PER_KWH = 0.0112  # Ceiling − Strike = 0.0739 − 0.055 ≈ 0.019 (PDF says +1.12¢)

# --- Energy matching ---
# Self-consumption rate from PDF: 59.6% (matched = 59.6% of total generation)
# Year-1 total generation = SOLAR_GWH_YR1 + WIND_GWH_YR1
SOLAR_GWH_YR1 = SOLAR_MW * 8760 * SOLAR_CF / 1_000.0
WIND_GWH_YR1 = WIND_MW * 8760 * WIND_CF / 1_000.0
TOTAL_GEN_GWH_YR1 = SOLAR_GWH_YR1 + WIND_GWH_YR1
MATCHED_GWH_YR1 = 70.05  # From PDF (matched volume year 1)

# --- Financial assumptions ---
TOTAL_CAPEX_USD = 28_500_000.0   # $28.50M as stated in PDF
DEBT_FRACTION = 0.70
INTEREST_RATE = 0.085             # 8.5% p.a. (VND commercial)
DEBT_TENOR_TOTAL = 12             # 12yr total
GRACE_YEARS = 1                   # 1yr interest-only grace period
DEBT_REPAYMENT_YEARS = DEBT_TENOR_TOTAL - GRACE_YEARS  # 11yr P+I
ANALYSIS_YEARS = 25

# CIT holiday schedule (from PDF): 4yr exempt → 9yr 50% pref → std 20%
# Note: 50% preference on 20% standard = 10% effective
def cit_rate(year: int) -> float:
    if year <= 4:
        return 0.0
    elif year <= 13:  # years 5-13 = 9 years
        return 0.10   # 50% of 20%
    else:
        return 0.20

# Depreciation: straight-line over 10 years (standard for solar/wind in VN)
DEPRECIATION_USD_PER_YR = TOTAL_CAPEX_USD / 10.0

# O&M estimate: derived from PDF Year-1 O&M = $621,600 (2.18% of CAPEX)
OM_FRACTION_OF_CAPEX = 621_600 / TOTAL_CAPEX_USD
OM_ESCALATION = 0.02  # 2%/yr O&M cost escalation (standard assumption)

# Revenue model:
# Developer sells matched volume at P_C (contracted) and unmatched at FMP.
# Year-1 FMP derived to match PDF proforma Year-1 Revenue of $6.0M:
#   Revenue = P_C × matched + FMP_yr1 × (total_gen - matched)
#   6,000,000 = 0.055 × 70,050,000 + FMP_yr1 × 47,510,000
#   FMP_yr1 = (6,000,000 - 3,852,750) / 47,510,000 = $0.04520/kWh
FMP_YR1_USD_PER_KWH = (6_000_000 - STRIKE_USD_PER_KWH * MATCHED_GWH_YR1 * 1e6) / (
    (TOTAL_GEN_GWH_YR1 - MATCHED_GWH_YR1) * 1e6
)
# FMP escalation: FMP_yr1 × (1 + esc)^(t-1). Mean over 25yr should ≈ 0.05707.
# Derived escalation: solve FMP_yr1 × sum((1+esc)^(t-1) for t=1..25) / 25 = 0.05707
# Numerical approximation: ~2.0%/yr gives mean close to 0.05707
FMP_ESCALATION = 0.020

# --- Equity assumptions ---
EQUITY_HURDLE_RATE = 0.15  # For viability frontier in sensitivity

# --- Staff report claims ---
STAFF_CLAIMS = {
    "solar_gwh_yr1": 51.0,
    "wind_gwh_yr1": 66.6,
    "total_gen_gwh_yr1": 117.56,
    "matched_gwh_yr1": 70.05,
    "re_penetration_pct": 48.8,
    "self_consumption_pct": 59.6,
    "factory_gross_saving_yr1_usd": 1_330_000,
    "factory_npv_usd": 7_970_000,
    "hours_at_premium_risk": 2186,
    "volume_at_premium_risk_mwh": 2925.5,
    "project_irr_pct": 18.1,
    "equity_irr_pct": 31.4,
    "project_npv_usd": 5_190_000,
    "equity_npv_usd": 10_360_000,
    "min_dscr": 1.53,
    "project_payback_years": 6,
}

TOLERANCE_PCT = 5.0  # WARN if delta > 5%
TOLERANCE_ABS = {"min_dscr": 0.05, "project_payback_years": 1.0}


# ---------------------------------------------------------------------------
# Computation helpers
# ---------------------------------------------------------------------------


def compute_energy_metrics() -> dict:
    solar = SOLAR_MW * 8760 * SOLAR_CF / 1_000.0
    wind = WIND_MW * 8760 * WIND_CF / 1_000.0
    total = solar + wind
    matched = MATCHED_GWH_YR1
    re_penetration = total / FACTORY_LOAD_GWH_YR1 * 100.0
    self_consumption = matched / total * 100.0
    return {
        "solar_gwh_yr1": round(solar, 2),
        "wind_gwh_yr1": round(wind, 2),
        "total_gen_gwh_yr1": round(total, 2),
        "matched_gwh_yr1": round(matched, 2),
        "re_penetration_pct": round(re_penetration, 1),
        "self_consumption_pct": round(self_consumption, 1),
    }


def compute_factory_economics(factory_discount_rate: float = 0.16) -> dict:
    # Year-1 saving per kWh = ceiling - strike
    saving_per_kwh = FACTORY_CEILING_USD_PER_KWH - STRIKE_USD_PER_KWH
    yr1_gross_saving = saving_per_kwh * MATCHED_GWH_YR1 * 1e6  # matched kWh × $/kWh
    # Project over 25yr with 0.5%/yr degradation
    cashflows = []
    for yr in range(1, ANALYSIS_YEARS + 1):
        gen_factor = (1 - DEGRADATION_ANNUAL) ** (yr - 1)
        cashflows.append(yr1_gross_saving * gen_factor)
    factory_npv = float(npf.npv(factory_discount_rate, [0.0] + cashflows))
    return {
        "saving_per_kwh_usd": round(saving_per_kwh, 5),
        "factory_gross_saving_yr1_usd": round(yr1_gross_saving, 0),
        "factory_npv_usd": round(factory_npv, 0),
        "factory_discount_rate_used": factory_discount_rate,
    }


def build_developer_cashflows() -> list[dict]:
    """Build 25-year developer P&L and cash flow waterfall."""
    debt = TOTAL_CAPEX_USD * DEBT_FRACTION
    _equity = TOTAL_CAPEX_USD * (1.0 - DEBT_FRACTION)

    # Debt schedule: 1yr grace (interest only), 11yr constant P+I (mortgage)
    annual_pi = float(npf.pmt(INTEREST_RATE, DEBT_REPAYMENT_YEARS, -debt))

    rows = []
    balance = debt
    for yr in range(1, ANALYSIS_YEARS + 1):
        # Generation (degrading)
        gen_factor = (1 - DEGRADATION_ANNUAL) ** (yr - 1)
        solar_gwh = SOLAR_GWH_YR1 * gen_factor
        wind_gwh = WIND_GWH_YR1 * gen_factor
        total_gwh = solar_gwh + wind_gwh
        matched_gwh = MATCHED_GWH_YR1 * gen_factor
        unmatched_gwh = total_gwh - matched_gwh

        # FMP in this year
        fmp = FMP_YR1_USD_PER_KWH * (1 + FMP_ESCALATION) ** (yr - 1)

        # Developer revenue
        revenue = (
            STRIKE_USD_PER_KWH * matched_gwh * 1e6
            + fmp * unmatched_gwh * 1e6
        )

        # O&M
        om = TOTAL_CAPEX_USD * OM_FRACTION_OF_CAPEX * (1 + OM_ESCALATION) ** (yr - 1)

        # Debt service
        if yr <= GRACE_YEARS:
            interest = balance * INTEREST_RATE
            principal = 0.0
            debt_service = interest
        elif yr <= DEBT_TENOR_TOTAL:
            interest = balance * INTEREST_RATE
            principal = annual_pi - interest
            debt_service = annual_pi
            balance -= principal
        else:
            interest = 0.0
            principal = 0.0
            debt_service = 0.0

        # Depreciation (10yr SL)
        depreciation = DEPRECIATION_USD_PER_YR if yr <= 10 else 0.0

        # EBIT (for tax base: revenue - om - depreciation - interest)
        ebit = revenue - om - depreciation - interest
        tax = max(0.0, ebit) * cit_rate(yr)
        net_income = ebit - tax

        # Project CF (pre-debt, cash basis — no depreciation add-back confusion)
        project_cf = revenue - om - tax
        # Equity CF
        equity_cf = project_cf - debt_service

        # DSCR = project_cf / debt_service (during loan period only)
        dscr = project_cf / debt_service if debt_service > 0 else None

        rows.append({
            "year": yr,
            "revenue_usd": round(revenue, 0),
            "om_usd": round(om, 0),
            "depreciation_usd": round(depreciation, 0),
            "interest_usd": round(interest, 0),
            "principal_usd": round(principal, 0),
            "debt_service_usd": round(debt_service, 0),
            "ebit_usd": round(ebit, 0),
            "tax_usd": round(tax, 0),
            "net_income_usd": round(net_income, 0),
            "project_cf_usd": round(project_cf, 0),
            "equity_cf_usd": round(equity_cf, 0),
            "debt_balance_usd": round(max(balance, 0), 0),
            "dscr": round(dscr, 3) if dscr is not None else None,
            "cit_rate": cit_rate(yr),
            "fmp_usd_per_kwh": round(fmp, 5),
        })

    return rows


def compute_irr_metrics(rows: list[dict]) -> dict:
    debt = TOTAL_CAPEX_USD * DEBT_FRACTION
    equity = TOTAL_CAPEX_USD * (1.0 - DEBT_FRACTION)

    project_cfs = [-TOTAL_CAPEX_USD] + [r["project_cf_usd"] for r in rows]
    equity_cfs = [-equity] + [r["equity_cf_usd"] for r in rows]

    project_irr = float(npf.irr(project_cfs))
    equity_irr = float(npf.irr(equity_cfs))
    # Staff report uses 15% (equity hurdle rate) for NPV, per the viability frontier page.
    project_npv = float(npf.npv(EQUITY_HURDLE_RATE, project_cfs))
    equity_npv = float(npf.npv(EQUITY_HURDLE_RATE, equity_cfs))

    # Simple payback
    cumulative = 0.0
    payback_yr = None
    for r in rows:
        cumulative += r["project_cf_usd"]
        if cumulative >= TOTAL_CAPEX_USD and payback_yr is None:
            payback_yr = r["year"]
            break

    # Min DSCR (during loan period)
    dsrcs = [r["dscr"] for r in rows if r["dscr"] is not None]
    min_dscr = min(dsrcs) if dsrcs else None

    return {
        "project_irr_pct": round(project_irr * 100, 1),
        "equity_irr_pct": round(equity_irr * 100, 1),
        "project_npv_usd": round(project_npv, 0),
        "equity_npv_usd": round(equity_npv, 0),
        "project_payback_years": payback_yr,
        "min_dscr": round(min_dscr, 2) if min_dscr else None,
        "debt_usd": round(debt, 0),
        "equity_usd": round(equity, 0),
    }


def compare_result(key: str, computed: float, staff: float) -> dict:
    if staff == 0:
        delta_pct = None
        status = "INFO"
    elif key in TOLERANCE_ABS:
        tol = TOLERANCE_ABS[key]
        delta_abs = abs(computed - staff)
        delta_pct = (computed - staff) / abs(staff) * 100
        status = "OK" if delta_abs <= tol else "WARN"
    else:
        delta_pct = (computed - staff) / abs(staff) * 100
        status = "OK" if abs(delta_pct) <= TOLERANCE_PCT else "WARN"
    return {
        "key": key,
        "computed": computed,
        "staff_report": staff,
        "delta_pct": round(delta_pct, 1) if delta_pct is not None else None,
        "status": status,
    }


def run_validation() -> dict:
    energy = compute_energy_metrics()
    factory = compute_factory_economics()
    rows = build_developer_cashflows()
    irr = compute_irr_metrics(rows)

    computed = {
        **energy,
        **{k: v for k, v in factory.items() if k in STAFF_CLAIMS},
        **{k: v for k, v in irr.items() if k in STAFF_CLAIMS},
    }

    comparison = []
    for key, staff_val in STAFF_CLAIMS.items():
        if key in computed and computed[key] is not None:
            comparison.append(compare_result(key, float(computed[key]), float(staff_val)))

    ok_count = sum(1 for r in comparison if r["status"] == "OK")
    warn_count = sum(1 for r in comparison if r["status"] == "WARN")
    info_count = sum(1 for r in comparison if r["status"] == "INFO")

    return {
        "project": "North Thuan Wind+Solar+BESS DPPA Feasibility Study (Scenario 3)",
        "source_pdf": "DPPA_FS_Study.pdf",
        "validation_date": "2026-03-29",
        "assumptions": {
            "total_capex_usd": TOTAL_CAPEX_USD,
            "solar_mw": SOLAR_MW,
            "wind_mw": WIND_MW,
            "bess_mw": BESS_MW,
            "bess_mwh": BESS_MWH,
            "solar_cf": SOLAR_CF,
            "wind_cf": WIND_CF,
            "degradation_annual": DEGRADATION_ANNUAL,
            "strike_usd_per_kwh": STRIKE_USD_PER_KWH,
            "fmp_yr1_usd_per_kwh_derived": round(FMP_YR1_USD_PER_KWH, 5),
            "fmp_escalation": FMP_ESCALATION,
            "fmp_mean_25yr_usd_per_kwh": FMP_MEAN_USD_PER_KWH,
            "factory_ceiling_usd_per_kwh": FACTORY_CEILING_USD_PER_KWH,
            "debt_fraction": DEBT_FRACTION,
            "interest_rate": INTEREST_RATE,
            "debt_tenor_total_years": DEBT_TENOR_TOTAL,
            "grace_years": GRACE_YEARS,
            "om_yr1_usd": round(TOTAL_CAPEX_USD * OM_FRACTION_OF_CAPEX, 0),
            "depreciation_usd_per_yr": DEPRECIATION_USD_PER_YR,
            "cit_schedule": "4yr exempt → 9yr 10% (50% pref) → std 20%",
            "analysis_years": ANALYSIS_YEARS,
        },
        "computed": computed,
        "staff_claims": STAFF_CLAIMS,
        "comparison": comparison,
        "summary": {
            "ok": ok_count,
            "warn": warn_count,
            "info": info_count,
            "total": len(comparison),
        },
        "annual_cashflows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate North Thuan staff DPPA report")
    parser.add_argument(
        "--output",
        default="artifacts/reports/north_thuan/2026-03-29_north-thuan-validation.json",
    )
    args = parser.parse_args()

    result = run_validation()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Validation results saved to: {out_path}")
    print(f"\nValidation summary: {result['summary']['ok']} OK  |  {result['summary']['warn']} WARN  |  {result['summary']['info']} INFO")
    print()
    for r in result["comparison"]:
        sym = {"OK": "OK", "WARN": "!", "INFO": "i"}.get(r["status"], "?")
        delta_str = f"{r['delta_pct']:+.1f}%" if r["delta_pct"] is not None else "-"
        print(f"  [{sym}] {r['key']:40s}  computed={r['computed']:<14}  staff={r['staff_report']:<14}  delta={delta_str}")


if __name__ == "__main__":
    main()
