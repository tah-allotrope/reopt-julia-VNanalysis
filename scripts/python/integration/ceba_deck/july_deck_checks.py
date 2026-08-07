"""DPPA July 2026 Case Studies deck — repo-testable claim registry.

This module is the single source of truth for the **July deck** verification
pipeline. It mirrors the shape of ``deck_checks`` (CEBA) but remaps the slide
numbers to the July deck's 28 slides and adds the new disclosures (Case 5/6
project IRR / NPV / payback / buyer-vs-BAU, the 56-scenario sweep, and the
"0 of 56" headline).

The orchestrator (``verify_ceba_dppa_deck.py --deck july``) loads this module
via the ``DeckConfig.registry_module`` indirection, dispatches each check's
``repo_fn`` (data lookup, settlement, or PySAM), fills the verdict, and writes
the results to ``reports/dppa_july_2026_repo_check.json``.

Slide map (28 slides total):
  Slide 1  — title
  Slide 2  — session roadmap
  Slide 3  — Module 1 title
  Slide 4  — TOU table + voltage table  (A01, A02, A05-bau-escalation)
  Slide 5  — Module 2 title
  Slide 6  — five-line flow diagram
  Slide 7  — five-line flow diagram (with CFD overlay)
  Slide 8  — five-line bill formula            (A03, A04, A06, A07, A12)
  Slide 9  — Q_adj / Q_Khc / Q_CfD definitions
  Slide 10 — worked example parameters         (B01..B04 inputs)
  Slide 11 — worked example 5-line table       (B01, B02, B03)
  Slide 12 — pre-CfD delivered cost 2,027      (B04)
  Slide 13 — Module 3 title
  Slide 14 — CfD mechanics                     (A14 CfD direction)
  Slide 15 — strike escalation 4%              (A08)
  Slide 16 — over-contracting cap              (C01)
  Slide 17 — Module 4 title
  Slide 18 — capital structure                 (A09, A10, A14, A15, A16)
  Slide 19 — three gates                       (C02, C03, C04, C05)
  Slide 20 — typical assumptions               (A11 PV degradation)
  Slide 21 — Module 5 title
  Slide 22 — Case 5/6 deal frame               (B05 case frame, A08/A09 applied)
  Slide 23 — Case 5 metrics                    (B06..B11, B17..B19)
  Slide 24 — Case 6 metrics                    (B12..B16, B20)
  Slide 25 — 56-scenario sweep                 (B21, B22, B23, B24, B25)
  Slide 26 — wrap-up                           (C07, C08)
  Slide 27 — Module 6 title
  Slide 28 — checklist                         (C09, C10)

Calibration context: the Case 5/6 numbers (16.9% / 26.9% seller IRR, etc.)
require undisclosed project CAPEX. The plan's DEC-004 pins BESS from the deck
hints and back-solves CAPEX to hit seller IRR; the calibration ledger is at
``reports/dppa_july_2026_calibration.json``. Per the plan (DEC-007), the
calibrated Case 5/6 family is allowed a 🔧 "calibrated" verdict distinct
from the ℹ️ method+directional verdict used for the un-solvable CEBA Cases.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = ["CHECKS", "Check", "all_rows", "to_dict"]


@dataclass
class Check:
    """One repo-testable claim pinned to a specific slide in the deck."""

    id: str
    slide: int
    bucket: str
    claim: str
    deck_value: Any
    deck_unit: str
    deck_citation: str | None
    repo_fn: str
    repo_source_ref: str
    assumptions: list[str] = field(default_factory=list)
    repo_value: Any = None
    delta_pct: float | None = None
    verdict: str | None = None
    takeaway: str | None = None
    notes: dict[str, Any] = field(default_factory=dict)


def _line(
    cid: str,
    slide: int,
    bucket: str,
    claim: str,
    deck_value: Any,
    deck_unit: str,
    citation: str | None,
    repo_fn: str,
    repo_source_ref: str,
    assumptions: list[str] | None = None,
) -> Check:
    return Check(
        id=cid,
        slide=slide,
        bucket=bucket,
        claim=claim,
        deck_value=deck_value,
        deck_unit=deck_unit,
        deck_citation=citation,
        repo_fn=repo_fn,
        repo_source_ref=repo_source_ref,
        assumptions=list(assumptions or []),
    )


# --------------------------------------------------------------------------
# A — Assumption checks (data file values vs deck-cited values)
# --------------------------------------------------------------------------
# Decimals, not percents.   Sources: data/vietnam/vn_*.json (manifest).
A: list[Check] = [
    _line(
        "J_A01_tou_peak_window",
        slide=4,
        bucket="A",
        claim="TOU peak window (deck 18:00-23:00 vs repo Decision 963 evening 17:30-22:30)",
        deck_value="18:00-23:00",
        deck_unit="hours",
        citation=None,
        repo_fn="data.vietnam.vn_tariff_2025.data.tou_schedule.weekday.peak_hours",
        repo_source_ref="data/vietnam/vn_tariff_2025.json:26",
        assumptions=[
            "Hourly discretization (decision-963 boundaries map to 17:30/22:30 -> integer hours 17,22).",
        ],
    ),
    _line(
        "J_A02_tou_peak_normal_ratio_22_110kv",
        slide=4,
        bucket="A",
        claim="TOU peak/Normal ratio for 22-110 kV (deck 0.126/0.070 ≈ 1.80)",
        deck_value=1.80,
        deck_unit="ratio (peak/normal)",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.ContractParams (kpp_factor / standard_factor via vn_tariff_2025.rate_multipliers.industrial.medium_voltage_22kv_to_110kv)",
        repo_source_ref="data/vietnam/vn_tariff_2025.json:99-104 (peak=1.57, standard=0.86 → 1.57/0.86=1.826)",
        assumptions=[
            "Compare peak/normal ratios on both sides (peak vs base-avg gives 1.57; vs standard gives 1.826).",
        ],
    ),
    _line(
        "J_A03_avg_retail_price",
        slide=8,
        bucket="A",
        claim="Average retail electricity price (residual / P1, 2025)",
        deck_value=2204.0,
        deck_unit="VND/kWh",
        citation=None,
        repo_fn="data.vietnam.vn_tariff_2025.data.base_avg_price_vnd_per_kwh",
        repo_source_ref="data/vietnam/vn_tariff_2025.json:22",
    ),
    _line(
        "J_A04_combined_dppa_fees",
        slide=8,
        bucket="A",
        claim="Combined DPPA fees: service (360) + balancing (163.3) = 523.3 VND/kWh",
        deck_value=523.3,
        deck_unit="VND/kWh",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.ContractParams.dppa_adder_vnd_kwh (default)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:26 (default 523.34)",
        assumptions=[
            "The engine takes one combined dppa_adder_vnd_kwh input and does not split it.",
        ],
    ),
    _line(
        "J_A05_bau_escalation_rate",
        slide=4,
        bucket="A",
        claim="BAU escalation rate (deck ~4%/yr historical EVN trend)",
        deck_value=0.04,
        deck_unit="fraction/yr",
        citation=None,
        repo_fn="data.vietnam.vn_financial_defaults_2025.data.standard.elec_cost_escalation_rate_fraction",
        repo_source_ref="data/vietnam/vn_financial_defaults_2025.json:18",
    ),
    _line(
        "J_A06_k_loss_factor",
        slide=8,
        bucket="A",
        claim="Price conversion factor k (FMP -> customer delivery point)",
        deck_value=1.026,
        deck_unit="ratio",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.ContractParams.kpp_factor (collapse check)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:46",
        assumptions=[
            "Deck treats k and K_pp as independent; engine collapses both into kpp_factor=1.02726.",
        ],
    ),
    _line(
        "J_A07_kpp_loss_factor",
        slide=8,
        bucket="A",
        claim="Loss factor K_pp at 110 kV",
        deck_value=1.008,
        deck_unit="ratio",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.ContractParams.kpp_pct=2.7263",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:27",
        assumptions=[
            "Engine uses a single blended kpp_pct (2.7263 -> 1.02726), not a 1.008 voltage-tier table.",
        ],
    ),
    _line(
        "J_A08_strike_escalation_rate",
        slide=15,
        bucket="A",
        claim="Strike escalation rate (deck 4%/yr, 25-year tenor)",
        deck_value=0.04,
        deck_unit="fraction/yr",
        citation=None,
        repo_fn="data.vietnam.vn_financial_defaults_2025.data.standard.elec_cost_escalation_rate_fraction",
        repo_source_ref="data/vietnam/vn_financial_defaults_2025.json:18",
    ),
    _line(
        "J_A09_debt_fraction",
        slide=18,
        bucket="A",
        claim="Capital structure: debt fraction",
        deck_value=0.70,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.SingleOwnerInputs.debt_fraction (default)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:24 (default 0.70)",
    ),
    _line(
        "J_A10_debt_rate_vnd",
        slide=18,
        bucket="A",
        claim="VND debt interest rate",
        deck_value=0.085,
        deck_unit="fraction/yr",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.SingleOwnerInputs.debt_interest_rate_fraction (default)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:30 (default 0.085)",
    ),
    _line(
        "J_A11_pv_degradation",
        slide=20,
        bucket="A",
        claim="PV annual degradation rate",
        deck_value=0.005,
        deck_unit="fraction/yr",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.SingleOwnerInputs (degradation is hard-coded 0.5% in engine at single_owner.py:163)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:163 (generic_degradation=0.5)",
    ),
    _line(
        "J_A12_fmp_2025_avg",
        slide=8,
        bucket="A",
        claim="2025 average FMP (Wholesale Electricity Market reference)",
        deck_value=1426.6,
        deck_unit="VND/kWh",
        citation="EAVCED public training (deck only)",
        repo_fn="data.vietnam.vn_deal_defaults_2026.data.sensitivity_ranges.fmp_vnd_per_kwh",
        repo_source_ref="data/vietnam/vn_deal_defaults_2026.json:39-43",
        assumptions=[
            "Repo's vn_deal_defaults_2026 sensitivity range (1,400-2,000 VND/kWh, center 1,700) is a forward-looking sweep midpoint, not an observed 2025 average. There is no repo data file that holds an observed 2025 monthly FMP. The deck's 1,426.6 is the anchor for the Case 5/6 calibration (DEC-003); the repo center 1,700 is a sensitivity.",
        ],
    ),
    _line(
        "J_A14_debt_tenor_years",
        slide=18,
        bucket="A",
        claim="Capital structure: debt tenor",
        deck_value=10,
        deck_unit="years",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.SingleOwnerInputs.debt_tenor_years (default)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:31 (default 10)",
    ),
    _line(
        "J_A15_equity_irr_target",
        slide=18,
        bucket="A",
        claim="Equity target IRR (range consistency, not value match)",
        deck_value="12-15%+",
        deck_unit="range",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.SingleOwnerInputs.target_irr_fraction (default)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:25 (default 0.15)",
        assumptions=[
            "Deck Slide 18 lists the range 12-15%+; engine default 0.15 falls within the deck's range.",
            "Qualitative check — value comparison is meaningless because target_irr_fraction is a tunable knob.",
        ],
    ),
    _line(
        "J_A16_cit_holiday",
        slide=18,
        bucket="A",
        claim="CIT tax holiday (RE projects): 4 yr exempt + 9 yr half rate",
        deck_value="4 + 9",
        deck_unit="years (exempt + half)",
        citation=None,
        repo_fn="data.vietnam.vn_financial_defaults_2025.data.renewable_energy_preferential.tax_holiday",
        repo_source_ref="data/vietnam/vn_financial_defaults_2025.json:32-37",
    ),
    _line(
        "J_A17_analysis_period",
        slide=22,
        bucket="A",
        claim="Analysis period (Case 5/6 deal frame)",
        deck_value=25,
        deck_unit="years",
        citation="deck Slide 22 (Case 5/6 deal frame); PHASE-03 calibration will set SingleOwnerInputs.analysis_years=25 explicitly",
        repo_fn="reopt_pysam_vn.pysam.single_owner.SingleOwnerInputs.analysis_years",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:23",
    ),
]


# --------------------------------------------------------------------------
# B — Finding checks (computed via the engine for a deck scenario)
# --------------------------------------------------------------------------
# deck_value is the deck-stated target; repo_value is what the engine returns
# when run with the same parameters.
B: list[Check] = [
    # --- Worked example (slides 10-12) ----------------------------------
    _line(
        "J_B01_simulation_5line_total_evnbill",
        slide=11,
        bucket="B",
        claim="Module-2 simulation EVN bill (lines 1+2+3+4) for Q=6,000,000 kWh",
        deck_value=10586097600.0,
        deck_unit="VND/month",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (flat single-month profile)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:65",
        assumptions=[
            "Flat profile: load=generation=Q/720h in the relevant hours; tariff=FMP=k*K_pp=1200*1.026*1.008 over all 720h.",
            "Excess_treatment=curtail (no exports); mode=virtual_cfd.",
        ],
    ),
    _line(
        "J_B02_simulation_cfd_settlement",
        slide=11,
        bucket="B",
        claim="Module-2 simulation CfD settlement (line 5) for Q=6,000,000 kWh @ (1,300-1,200)",
        deck_value=600000000.0,
        deck_unit="VND/month",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement.buyer_cfd_payment_vnd",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:147",
        assumptions=["Same flat profile as J_B01."],
    ),
    _line(
        "J_B03_simulation_effective_blended_rate",
        slide=11,
        bucket="B",
        claim="Module-2 simulation effective blended rate (total/Q)",
        deck_value=1864.0,
        deck_unit="VND/kWh",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement.annual_summary.buyer_blended_rate_vnd_kwh",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:182",
        assumptions=["Same flat profile as J_B01."],
    ),
    _line(
        "J_B04_pretax_delivered_cost_per_kwh",
        slide=12,
        bucket="B",
        claim="Pre-CfD delivered cost per matched kWh at 22-110 kV (1,504 + 360 + 163.3)",
        deck_value=2027.0,
        deck_unit="VND/kWh",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (1-line decomposition)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:119-122",
        assumptions=[
            "FMP=2025-avg; k*K_pp=1.03421; fees 360+163.3 applied to matched volume.",
        ],
    ),
    # --- Case 5 (slide 23) -------------------------------------------------
    _line(
        "J_B05_case5_deal_frame",
        slide=22,
        bucket="B",
        claim="Case 5 deal frame: virtual DPPA, strike 2,000 VND, 4%/yr, 70/8.5/10-yr, 25-yr",
        deck_value="2,000 VND/kWh",
        deck_unit="strike (VND/kWh)",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.ContractParams (strike=2000, escalation=0.04)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:18-27",
    ),
    _line(
        "J_B06_case5_seller_irr",
        slide=23,
        bucket="B",
        claim="Case 5 (Solar + Large BESS) — Seller equity IRR (aftertax/levered)",
        deck_value=0.169,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model (solved CAPEX, calibrated BESS)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141 (irr derived from cf_project_return_aftertax_cash)",
        assumptions=[
            "BESS energy pinned to 7.5 MWh (~$160/kWh × 7,500 kWh ≈ $1.2M replacement, DEC-004).",
            "CAPEX back-solved by 1-D root find on installed_cost_usd to hit deck IRR (DEC-001).",
            "Solar sized to ~85% of factory 9,750 MWh/yr load (≈ 5.25 MWp at 18% CF; Q-001 default).",
        ],
    ),
    _line(
        "J_B07_case5_project_irr",
        slide=23,
        bucket="B",
        claim="Case 5 (Solar + Large BESS) — Project IRR (unlevered/pretax consistency check)",
        deck_value=0.135,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.metrics.extract_single_owner_outputs.project_return_pretax_irr_fraction",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/metrics.py:43",
        assumptions=[
            "Project IRR is the unlevered (pretax) IRR; should be lower than seller IRR under positive leverage (DEC-001, Q-002).",
        ],
    ),
    _line(
        "J_B08_case5_developer_npv",
        slide=23,
        bucket="B",
        claim="Case 5 (Solar + Large BESS) — Developer NPV @ 26,400 VND/USD",
        deck_value=1_520_000.0,
        deck_unit="USD",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.metrics.extract_single_owner_outputs.project_return_aftertax_npv_usd",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/metrics.py:35",
    ),
    _line(
        "J_B09_case5_min_dscr",
        slide=23,
        bucket="B",
        claim="Case 5 (Solar + Large BESS) — Minimum DSCR (replacement year)",
        deck_value=1.14,
        deck_unit="x",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.metrics.extract_single_owner_outputs.min_dscr",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/metrics.py:47",
        assumptions=[
            "BESS replacement modeled as a year-11 cash outflow (~$1.2M); deck-observed dip is the binding lender gate.",
        ],
    ),
    _line(
        "J_B10_case5_payback_years",
        slide=23,
        bucket="B",
        claim="Case 5 (Solar + Large BESS) — Payback period",
        deck_value=9.1,
        deck_unit="years",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model + custom payback extraction",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:174-185 (cash flow from cf_project_return_aftertax_cash)",
        assumptions=[
            "Payback = first year the cumulative aftertax cash flow turns non-negative.",
        ],
    ),
    _line(
        "J_B11_case5_buyer_vs_bau_year1",
        slide=23,
        bucket="B",
        claim="Case 5 — Buyer cost vs BAU (Year 1)",
        deck_value=-0.087,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (Y1 buyer vs BAU)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:65",
    ),
    _line(
        "J_B17_case5_buyer_vs_bau_10yr",
        slide=23,
        bucket="B",
        claim="Case 5 — Buyer cost vs BAU (10-yr cumulative)",
        deck_value=-0.089,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (10-yr cum vs BAU)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:65",
    ),
    _line(
        "J_B18_case5_buyer_vs_bau_lifetime",
        slide=23,
        bucket="B",
        claim="Case 5 — Buyer cost vs BAU (25-yr lifetime cumulative)",
        deck_value=-0.093,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (25-yr cum vs BAU)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:65",
    ),
    # --- Case 6 (slide 24) -------------------------------------------------
    _line(
        "J_B12_case6_seller_irr",
        slide=24,
        bucket="B",
        claim="Case 6 (Solar + Min BESS) — Seller equity IRR (aftertax/levered)",
        deck_value=0.269,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model (solved CAPEX, lean BESS)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141",
        assumptions=[
            "Lean BESS: 4 MWh (no replacement shock; BTM Case 2 reference is 10.7 MWh, scaled down to differentiate as 'minimum').",
            "CAPEX back-solved by 1-D root find on installed_cost_usd to hit deck IRR (DEC-001).",
        ],
    ),
    _line(
        "J_B13_case6_project_irr",
        slide=24,
        bucket="B",
        claim="Case 6 (Solar + Min BESS) — Project IRR (unlevered/pretax consistency check)",
        deck_value=0.182,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.metrics.extract_single_owner_outputs.project_return_pretax_irr_fraction",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/metrics.py:43",
    ),
    _line(
        "J_B14_case6_developer_npv",
        slide=24,
        bucket="B",
        claim="Case 6 (Solar + Min BESS) — Developer NPV @ 26,400 VND/USD",
        deck_value=2_540_000.0,
        deck_unit="USD",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.metrics.extract_single_owner_outputs.project_return_aftertax_npv_usd",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/metrics.py:35",
    ),
    _line(
        "J_B15_case6_min_dscr",
        slide=24,
        bucket="B",
        claim="Case 6 (Solar + Min BESS) — Minimum DSCR",
        deck_value=1.50,
        deck_unit="x",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.metrics.extract_single_owner_outputs.min_dscr",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/metrics.py:47",
        assumptions=["Lean BESS: no replacement shock assumed within loan tenor."],
    ),
    _line(
        "J_B16_case6_payback_years",
        slide=24,
        bucket="B",
        claim="Case 6 (Solar + Min BESS) — Payback period",
        deck_value=4.7,
        deck_unit="years",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model + custom payback extraction",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:174-185",
    ),
    _line(
        "J_B20_case6_buyer_vs_bau_lifetime",
        slide=24,
        bucket="B",
        claim="Case 6 — Buyer cost vs BAU (all horizons, single number)",
        deck_value=-0.144,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (cumulative vs BAU)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:65",
    ),
    # --- 56-scenario sweep (slide 25) -------------------------------------
    _line(
        "J_B21_sweep_offer_buyer",
        slide=25,
        bucket="B",
        claim="Sweep row 1 (~2,000 offer): Buyer gate",
        deck_value=-0.14,
        deck_unit="fraction (vs BAU)",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.run_strike_sweep (strike=2000, vol=100%)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:274",
    ),
    _line(
        "J_B22_sweep_1400_seller",
        slide=25,
        bucket="B",
        claim="Sweep row 2 (~1,400): Seller gate (seller IRR)",
        deck_value=0.19,
        deck_unit="fraction (seller IRR)",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model (strike=1400, vol=100%)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141",
    ),
    _line(
        "J_B23_sweep_1300_70pct_lender",
        slide=25,
        bucket="B",
        claim="Sweep row 3 (~1,300 x 70% vol): Lender gate (min DSCR)",
        deck_value=1.14,
        deck_unit="x (min DSCR)",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model (strike=1300, vol=70%)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141",
    ),
    _line(
        "J_B24_sweep_1200_buyer",
        slide=25,
        bucket="B",
        claim="Sweep row 4 (~1,200): Buyer gate (lifetime cumulative vs BAU)",
        deck_value=0.029,
        deck_unit="fraction (vs BAU)",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.run_strike_sweep (strike=1200, vol=100%)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:274",
    ),
    _line(
        "J_B25_sweep_zero_of_56",
        slide=25,
        bucket="B",
        claim="Sweep headline: 0 of 56 scenarios pass all three gates at current market prices and fee levels",
        deck_value=0,
        deck_unit="scenarios passing all three gates",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.run_strike_sweep x strike_search.sweep_strike_prices (12 strikes x 4 vol)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:274 + src/python/reopt_pysam_vn/integration/strike_search.py:44",
        assumptions=[
            "Gates: buyer cumulative <= BAU (Y10 + lifetime); seller IRR >= 12-15%; lender min DSCR >= 1.20x.",
        ],
    ),
]


# --------------------------------------------------------------------------
# C — Insight checks (qualitative, verified via the engine qualitatively)
# --------------------------------------------------------------------------
# verdict and takeaway populated by the orchestrator; deck_value holds the
# slide claim (a qualitative statement) and repo_value holds a quantitative
# reproduction.
C: list[Check] = [
    _line(
        "J_C01_overcontracting_cap",
        slide=16,
        bucket="C",
        claim="Over-contracting (Q_c > hourly consumption) caps CfD at consumed volume",
        deck_value="capped at min(load, gen)",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (matched = min(load, gen))",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:103",
    ),
    _line(
        "J_C02_buyer_gate_formula",
        slide=19,
        bucket="C",
        claim="Buyer gate: cumulative cost <= BAU over 10 yr AND lifetime (pushes strike DOWN)",
        deck_value="buyer_cumulative <= BAU_10yr AND buyer_cumulative <= BAU_lifetime",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (10yr & 25yr cumulative vs BAU escalated 4%/yr)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:65",
    ),
    _line(
        "J_C03_seller_gate_formula",
        slide=19,
        bucket="C",
        claim="Seller gate: Equity IRR >= 12-15% (pushes strike UP)",
        deck_value="seller_irr >= 0.12",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model (target_irr_fraction=0.12)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:25 (default 0.15)",
    ),
    _line(
        "J_C04_lender_gate_formula",
        slide=19,
        bucket="C",
        claim="Lender gate: min DSCR >= ~1.20x every year (pushes strike UP, hardest gate)",
        deck_value="min_dscr >= 1.20",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.metrics.extract_single_owner_outputs.min_dscr",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/metrics.py:47",
    ),
    _line(
        "J_C05_battery_replacement_dscr_dip",
        slide=20,
        bucket="C",
        claim="One CAPEX heavy year (e.g., a battery replacement) can sink the whole financing",
        deck_value="replacement-year min DSCR < 1.20x",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model (with BESS year-11 cash shock)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141",
    ),
    _line(
        "J_C06_negotiation_window",
        slide=19,
        bucket="C",
        claim="The negotiation window is the strike range where all three gates 'pass'; it can be empty",
        deck_value="triple-gate window may be empty",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.run_strike_sweep x strike_search.sweep_strike_prices",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:274 + src/python/reopt_pysam_vn/integration/strike_search.py:44",
    ),
    _line(
        "J_C07_bankability_floor",
        slide=26,
        bucket="C",
        claim="A strike below the developer's bankability floor does not mean a cheap deal; it means no project",
        deck_value="strike_floor exists",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.strike_search.sweep_strike_prices (find min strike at target IRR)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/strike_search.py:44",
    ),
    _line(
        "J_C08_y1_premium",
        slide=26,
        bucket="C",
        claim="Expect Year 1 to cost more than BAU; savings build with EVN escalation",
        deck_value="Y1 buyer > BAU",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.analysis.offsite_dppa.run_offsite_dppa (Y1 vs BAU)",
        repo_source_ref="src/python/reopt_pysam_vn/analysis/offsite_dppa.py",
    ),
    _line(
        "J_C09_financing_structure_matters",
        slide=26,
        bucket="C",
        claim="Deal feasibility is decided by financing structure as much as by price",
        deck_value="leverage / debt terms drive feasibility",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.strike_search.sweep_strike_prices (vary debt_fraction)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/strike_search.py:44",
    ),
    _line(
        "J_C10_voltage_kpp",
        slide=28,
        bucket="C",
        claim="Voltage eligibility & K_pp: >=22kV only today; which K_pp applies decides your loss adjustment",
        deck_value="22kV-110kV -> K_pp ≈ 1.008",
        deck_unit="qualitative",
        citation=None,
        repo_fn="data.vietnam.vn_tariff_2025.data.tou_schedule (kpp_factor per voltage tier)",
        repo_source_ref="data/vietnam/vn_tariff_2025.json",
    ),
]


CHECKS: list[Check] = A + B + C


# --------------------------------------------------------------------------
# Calibration set — the Case 5/6 family that the plan calibrates by design
# --------------------------------------------------------------------------
# Per DEC-001 + DEC-007: the Case 5/6 metrics are reached by back-solving
# CAPEX, so they are not "method+directional" anymore — they are
# "calibrated" (the seller IRR is allowed to match by construction; the
# other five are independent checks).
# Per the plan: "only the solved-for metric (seller IRR) is allowed to
# match by construction; the other five are independent checks, and the
# report foregrounds any inconsistency."
JULY_CALIBRATED_CHECKS: set[str] = {
    # Case 5 (J_B06 is the SOLVED target; J_B07..J_B18 are consistency checks)
    "J_B06_case5_seller_irr",
    "J_B07_case5_project_irr",
    "J_B08_case5_developer_npv",
    "J_B09_case5_min_dscr",
    "J_B10_case5_payback_years",
    "J_B11_case5_buyer_vs_bau_year1",
    "J_B17_case5_buyer_vs_bau_10yr",
    "J_B18_case5_buyer_vs_bau_lifetime",
    # Case 6
    "J_B12_case6_seller_irr",
    "J_B13_case6_project_irr",
    "J_B14_case6_developer_npv",
    "J_B15_case6_min_dscr",
    "J_B16_case6_payback_years",
    "J_B20_case6_buyer_vs_bau_lifetime",
}

# Sweep checks: these are independent of calibration (run at the solved CAPEX
# from calibration but exercise a different code path). They get the standard
# ±1% / 1-5% / >5% / structural verdict — no calibrated tier.
JULY_SWEEP_CHECKS: set[str] = {
    "J_B21_sweep_offer_buyer",
    "J_B22_sweep_1400_seller",
    "J_B23_sweep_1300_70pct_lender",
    "J_B24_sweep_1200_buyer",
    "J_B25_sweep_zero_of_56",
}


def to_dict(obj: Any) -> dict:
    """asdict wrapper."""
    return asdict(obj)


def all_rows() -> list[dict]:
    """Return all registry rows as plain dicts."""
    return [to_dict(c) for c in CHECKS]
