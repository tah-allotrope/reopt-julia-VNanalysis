"""Cross-validates the Allotrope-KBC JV Year-One Financials workbook's Project
Pro Formas (20-yr unlevered buyer IRR/NPV per project) against NREL PySAM's
Single Owner model, per the Allotrope-KBC JV feedback-package plan (external
workspace) PHASE-2B.

Run with the reopt-pysam repo's own venv (already has nrel-pysam>=7.1):
    .venv/Scripts/python.exe scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py

Methodology: the workbook prices only SELF-CONSUMED generation, escalating at
4%/yr, degrading at 0.5%/yr, against O&M of $10/kWp/yr escalating 3%/yr, at a
buyer purchase price of kWp x $650/kWp x 1.12 (PV-only, fee-inclusive). PySAM's
Single Owner model (ppa_soln_mode=1, fixed PPA price) prices ALL of whatever
hourly generation profile it is given -- so the input profile here is built
from REopt's actual solved self-consumption SHAPE (realistic intra-year
distribution), but its ANNUAL TOTAL is normalized to exactly match the
workbook's own Year-1 self-consumed-generation convention (kWp x 1,216.4 x sc).
This isolates the comparison to "does an independent engine agree with our
cash-flow/IRR/NPV FORMULA given the same inputs" rather than re-litigating a
separate REopt internal accounting nuance (year_one_energy_produced_kwh vs.
annual_energy_produced_kwh differ by ~4.5% in the REopt output files
themselves -- not a PySAM cross-check concern).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "python"))


from reopt_pysam_vn.pysam.config import PySAMRuntimeConfig
from reopt_pysam_vn.pysam.single_owner import (
    SingleOwnerInputs, _configure_financial_model, build_single_owner_inputs,
)


def run_single_owner_model_clean(inputs: SingleOwnerInputs) -> dict:
    """Re-implements reopt_pysam_vn.pysam.single_owner.run_single_owner_model,
    adding explicit zeroing of SAM's Single Owner defaults that the upstream
    wrapper does NOT touch and which are calibrated for a ~100MW reference
    project -- construction_financing_cost ($2,866,500 flat dollar default),
    insurance_rate, debt-fee/reserve costs, and property tax. Left at their
    defaults, these swamp a sub-2 MWp project's economics (confirmed via
    direct inspection: the unmodified wrapper returns NPV/IRR far more
    negative than the workbook's cost/OM structure can explain). This does
    NOT modify the shared wrapper module -- it is a self-contained,
    throwaway comparison harness per PHASE-2B's design. The durable,
    library-level replacement for this reimplementation is
    reopt_pysam_vn.pysam.single_owner.SingleOwnerInputs(zero_reference_plant_defaults=True),
    added in plans/2026-07-24-post-ci-hygiene-finance-audit-plan.md PHASE-02
    -- see reports/2026-07-24-single-owner-defaults-audit.md."""
    import PySAM.CustomGeneration as cg
    import PySAM.Grid as gr
    import PySAM.Singleowner as so
    import PySAM.Utilityrate5 as ur

    runtime = PySAMRuntimeConfig()
    system_model = cg.default("CustomGenerationProfileNone")
    grid_model = gr.from_existing(system_model, runtime.system_config)
    utility_model = ur.from_existing(system_model, runtime.system_config)
    financial_model = so.from_existing(system_model, runtime.system_config)

    system_model.Plant.system_capacity = float(inputs.system_capacity_kw)
    system_model.Plant.derate = 1.0
    system_model.Plant.energy_output_array = [float(v) for v in inputs.generation_profile_kw]
    system_model.Plant.spec_mode = 1
    system_model.Lifetime.analysis_period = int(inputs.analysis_years)
    system_model.Lifetime.system_use_lifetime_output = 0
    system_model.Lifetime.generic_degradation = [0.5]

    _configure_financial_model(financial_model, inputs)

    fp = financial_model.FinancialParameters
    fp.insurance_rate = 0.0
    fp.construction_financing_cost = 0.0
    fp.cost_debt_fee = 0.0
    fp.cost_debt_closing = 0.0
    fp.months_working_reserve = 0.0
    fp.dscr_reserve_months = 0.0
    fp.equip1_reserve_cost = 0.0
    fp.equip2_reserve_cost = 0.0
    fp.equip3_reserve_cost = 0.0
    fp.prop_tax_cost_assessed_percent = 0.0
    fp.reserves_interest = 0.0
    fp.salvage_percentage = 0.0

    system_model.execute()
    grid_model.execute()
    utility_model.execute()
    financial_model.execute()

    from reopt_pysam_vn.pysam.metrics import extract_single_owner_outputs
    return {"outputs": extract_single_owner_outputs(financial_model)}

REOPT_ARCHETYPE = Path(r"C:\Users\tukum\Downloads\reopt-pysam\artifacts\results\trangdue\2026-07-14_trangdue-archetype_1200kwp_solar_reopt-results.json")
REOPT_FLAGSHIP = Path(r"C:\Users\tukum\Downloads\reopt-pysam\artifacts\results\trangdue\2026-07-14_trangdue-flagship_1999kwp_bess1mw2mwh_reopt-results.json")

# --- CONFIG mirror (models/build_jv_year1_model.py CONFIG, 2026-07-17 capex/fee revision) ---
PV_CAPEX_PER_KWP = 550.0
DEV_FEE_PCT = 0.15
YIELD_KWH_PER_KWP = 1216.4
OM_PER_KWP = 10.0
ESC_OM = 0.03
ESC_REVENUE = 0.04
DEGRADATION = 0.005
DISCOUNT_RATE = 0.08
PPA_USD_PER_KWH = 2233.25 * (1 - 0.14) / 26400  # S2a base case, d=14% (revised capex/fee basis)

SC_DEFAULT = 0.826
SC_FLAGSHIP = 0.978

# (label, kwp, sc, workbook_irr, workbook_npv) -- workbook values recomputed 2026-07-17
# for the revised $550/kWp, 15% dev-fee, 14% discount basis (see jv-year1-inputs.md §14).
PROJECTS = [
    ("Green Works (Vietnam) Co. Ltd — Trang Due", 1998.582104904, SC_FLAGSHIP, 0.1382, 690464.0),
    ("Crystal Sweater", 1498.152291552, SC_DEFAULT, 0.1108, 261340.0),
    ("Power 7 Technology Vietnam Co., Ltd", 461.652472764, SC_DEFAULT, 0.1108, 80531.0),
    ("LG-satellite archetype A", 1200.0, SC_DEFAULT, 0.1108, 209330.0),
    ("LG-satellite archetype B", 1200.0, SC_DEFAULT, 0.1108, 209330.0),
    ("LG-satellite archetype C", 1200.0, SC_DEFAULT, 0.1108, 209330.0),
]


def load_self_consumption_shape(path: Path) -> list[float]:
    """Returns the REopt-solved hourly self-consumed-PV-to-load series (8760
    values, kW), normalized so its own annual sum equals 1.0 (a pure shape)."""
    with open(path) as f:
        d = json.load(f)
    series = d["outputs"]["PV"]["electric_to_load_series_kw"]
    total = sum(series)
    return [v / total for v in series]


def build_profile_for_project(kwp: float, sc: float, shape: list[float]) -> list[float]:
    """Scales a normalized hourly shape so its annual total equals the
    workbook's own Year-1 self-consumed-generation convention: kWp x
    yield_kwh_per_kwp x sc. PySAM applies its own 0.5%/yr degradation (built
    into the wrapper's Lifetime.generic_degradation) and the PPA escalation
    to this Year-1 baseline for later years, mirroring the workbook exactly."""
    target_annual_kwh = kwp * YIELD_KWH_PER_KWP * sc
    return [f * target_annual_kwh for f in shape]


def run_project(label: str, kwp: float, sc: float, shape: list[float]) -> dict:
    profile = build_profile_for_project(kwp, sc, shape)
    inputs = build_single_owner_inputs(
        system_capacity_kw=kwp,
        generation_profile_kw=profile,
        annual_generation_kwh=sum(profile),
        installed_cost_usd=kwp * PV_CAPEX_PER_KWP * (1 + DEV_FEE_PCT),
        fixed_om_usd_per_year=kwp * OM_PER_KWP,
        ppa_price_input_usd_per_kwh=PPA_USD_PER_KWH,
        analysis_years=20,
        debt_fraction=0.0,
        owner_tax_rate_fraction=0.0,
        owner_discount_rate_fraction=DISCOUNT_RATE,
        inflation_rate_fraction=0.0,
        debt_interest_rate_fraction=0.0,
        debt_tenor_years=1,
        ppa_escalation_rate_fraction=ESC_REVENUE,
        om_escalation_rate_fraction=ESC_OM,
        metadata={"label": label},
    )
    result = run_single_owner_model_clean(inputs)
    return result["outputs"]


def run_degenerate_check(shape: list[float]) -> None:
    """PPA price = 0 must give a strictly negative NPV approx equal to
    -(installed cost + PV of O&M) -- proves the harness isn't silently
    earning revenue on unpriced/exported energy."""
    kwp, sc = 1200.0, SC_DEFAULT
    profile = build_profile_for_project(kwp, sc, shape)
    inputs = build_single_owner_inputs(
        system_capacity_kw=kwp,
        generation_profile_kw=profile,
        annual_generation_kwh=sum(profile),
        installed_cost_usd=kwp * PV_CAPEX_PER_KWP * (1 + DEV_FEE_PCT),
        fixed_om_usd_per_year=kwp * OM_PER_KWP,
        ppa_price_input_usd_per_kwh=0.0,
        analysis_years=20,
        debt_fraction=0.0,
        owner_tax_rate_fraction=0.0,
        owner_discount_rate_fraction=DISCOUNT_RATE,
        inflation_rate_fraction=0.0,
        debt_interest_rate_fraction=0.0,
        debt_tenor_years=1,
        ppa_escalation_rate_fraction=ESC_REVENUE,
        om_escalation_rate_fraction=ESC_OM,
    )
    result = run_single_owner_model_clean(inputs)
    npv = result["outputs"]["project_return_pretax_npv_usd"]
    installed = kwp * PV_CAPEX_PER_KWP * (1 + DEV_FEE_PCT)
    om_pv = sum(
        kwp * OM_PER_KWP * (1 + ESC_OM) ** (y - 1) / (1 + DISCOUNT_RATE) ** y
        for y in range(1, 21)
    )
    expected = -(installed + om_pv)
    print(f"\nDEGENERATE CHECK (ppa=$0): NPV = ${npv:,.0f}  expected approx ${expected:,.0f}  "
          f"strictly negative: {npv < 0}")


def main() -> None:
    archetype_shape = load_self_consumption_shape(REOPT_ARCHETYPE)
    flagship_shape = load_self_consumption_shape(REOPT_FLAGSHIP)

    print(f"{'Project':<44} {'WB IRR':>8} {'PySAM IRR':>10} {'d(IRR,pp)':>10} "
          f"{'WB NPV':>12} {'PySAM NPV':>12} {'d(NPV,%)':>9}  Tol")
    all_ok = True
    rows = []
    for label, kwp, sc, wb_irr, wb_npv in PROJECTS:
        shape = flagship_shape if sc == SC_FLAGSHIP else archetype_shape
        out = run_project(label, kwp, sc, shape)
        pysam_irr = out["project_return_pretax_irr_fraction"]
        pysam_npv = out["project_return_pretax_npv_usd"]
        d_irr_pp = (pysam_irr - wb_irr) * 100
        d_npv_pct = (pysam_npv - wb_npv) / wb_npv * 100
        ok = abs(d_irr_pp) <= 0.5 and abs(d_npv_pct) <= 5.0
        all_ok = all_ok and ok
        rows.append((label, wb_irr, pysam_irr, d_irr_pp, wb_npv, pysam_npv, d_npv_pct, ok))
        print(f"{label:<44} {wb_irr*100:7.2f}% {pysam_irr*100:9.2f}% {d_irr_pp:9.2f}pp "
              f"${wb_npv:11,.0f} ${pysam_npv:11,.0f} {d_npv_pct:8.2f}%  {'OK' if ok else 'FAIL'}")

    print(f"\nALL WITHIN TOLERANCE: {all_ok}")
    run_degenerate_check(archetype_shape)

    print("\n--- CSV for brief ---")
    print("project,wb_irr,pysam_irr,delta_irr_pp,wb_npv,pysam_npv,delta_npv_pct,ok")
    for r in rows:
        print(f"{r[0]},{r[1]:.6f},{r[2]:.6f},{r[3]:.4f},{r[4]:.2f},{r[5]:.2f},{r[6]:.4f},{r[7]}")


if __name__ == "__main__":
    main()
