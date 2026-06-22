"""CEBA DPPA 2026 deck — repo-testable claim registry.

This module is the single source of truth for the deck-verification pipeline.
Each entry in ``CHECKS`` is a ``Check`` (one repo-testable claim on a deck
slide) plus zero or more ``KnownGap`` rows for relevant-but-unmodeled slides
(decree-146 two-part tariff, RECs/EACs, GHG scopes).

The orchestrator (``verify_ceba_dppa_deck.py``) iterates the registry,
dispatches each ``repo_fn`` with the listed ``repo_args`` / ``repo_kwargs``,
fills ``repo_value`` / ``delta_pct`` / ``verdict`` / ``takeaway``, and writes
the results to ``reports/ceba_dppa_2026_repo_check.json``.

See ``plans/2026-06-23-ceba-deck-repo-verification-plan.md`` for the
end-to-end design and the resolved decisions (DEC-001..DEC-009).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional

__all__ = [
    "Check",
    "KnownGap",
    "CHECKS",
    "KNOWN_GAPS",
    "to_dict",
    "all_rows",
]


@dataclass
class Check:
    """One repo-testable claim pinned to a specific slide in the deck."""

    id: str
    slide: int
    bucket: str
    claim: str
    deck_value: Any
    deck_unit: str
    deck_citation: Optional[str]
    repo_fn: str
    repo_source_ref: str
    assumptions: list[str] = field(default_factory=list)
    repo_value: Any = None
    delta_pct: Optional[float] = None
    verdict: Optional[str] = None
    takeaway: Optional[str] = None
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnownGap:
    """A slide / topic the deck covers that is intentionally out of repo scope."""

    id: str
    slide: int
    topic: str
    note: str
    verdict: str = "out_of_repo_scope"


def _line(
    cid: str,
    slide: int,
    bucket: str,
    claim: str,
    deck_value: Any,
    deck_unit: str,
    citation: Optional[str],
    repo_fn: str,
    repo_source_ref: str,
    assumptions: Optional[list[str]] = None,
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
        "A01_tou_peak_window",
        slide=5,
        bucket="A",
        claim="TOU peak window (deck 18:00-23:00 vs repo Decision 963 evening 17:30-22:30)",
        deck_value="18:00-23:00",
        deck_unit="hours",
        citation=None,
        repo_fn="data.vietnam.vn_tariff_2025.tou_schedule.weekday.peak_hours",
        repo_source_ref="data/vietnam/vn_tariff_2025.json:26",
        assumptions=[
            "Hourly discretization (decision-963 boundaries map to 17:30/22:30 -> integer hours 17,22).",
        ],
    ),
    _line(
        "A02_tou_peak_multiplier_22_110kv",
        slide=5,
        bucket="A",
        claim="TOU peak multiplier for 22-110 kV (~1.78x per deck table)",
        deck_value=1.78,
        deck_unit="x base avg",
        citation=None,
        repo_fn="data.vietnam.vn_tariff_2025.rate_multipliers.industrial.medium_voltage_22kv_to_110kv.peak",
        repo_source_ref="data/vietnam/vn_tariff_2025.json:99",
    ),
    _line(
        "A03_avg_retail_price",
        slide=11,
        bucket="A",
        claim="Average retail electricity price (P1 / avg EVN tariff, 2025)",
        deck_value=2204.0,
        deck_unit="VND/kWh",
        citation=None,
        repo_fn="data.vietnam.vn_tariff_2025.base_avg_price_vnd_per_kwh",
        repo_source_ref="data/vietnam/vn_tariff_2025.json:22",
    ),
    _line(
        "A04_dppa_service_fee",
        slide=9,
        bucket="A",
        claim="DPPA service fee (C_dppa_dv)",
        deck_value=360.0,
        deck_unit="VND/kWh",
        citation=None,
        repo_fn="data.vietnam.vn_tariff_2025.decree_57_dppa.solar_ceiling_tariffs_vnd_per_kwh",
        repo_source_ref="data/vietnam/vn_tariff_2025.json:218 (region: south ground w/ BESS min)",
    ),
    _line(
        "A05_balancing_fee",
        slide=9,
        bucket="A",
        claim="Balancing / difference clearing fee (P_cl)",
        deck_value=163.3,
        deck_unit="VND/kWh",
        citation=None,
        repo_fn="data.vietnam.vn_tariff_2025.demand_charge.two_part_tariff_trial",
        repo_source_ref="data/vietnam/vn_tariff_2025.json:171 (Decree 146 trial, paper only)",
    ),
    _line(
        "A06_k_loss_factor",
        slide=11,
        bucket="A",
        claim="Price conversion factor k (FMP -> customer delivery point)",
        deck_value=1.026,
        deck_unit="ratio",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.ContractParams.kpp_factor (collapse check)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:46",
        assumptions=[
            "Deck treats k and K_pp as independent; engine collapses both into kpp_factor=1.0273.",
        ],
    ),
    _line(
        "A07_kpp_loss_factor",
        slide=11,
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
        "A08_escalation_rate",
        slide=16,
        bucket="A",
        claim="Strike escalation rate (default 4%/yr)",
        deck_value=0.04,
        deck_unit="fraction/yr",
        citation=None,
        repo_fn="data.vietnam.vn_financial_defaults_2025.standard.elec_cost_escalation_rate_fraction",
        repo_source_ref="data/vietnam/vn_financial_defaults_2025.json:18",
    ),
    _line(
        "A09_debt_fraction",
        slide=19,
        bucket="A",
        claim="Capital structure: debt fraction",
        deck_value=0.70,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.analysis.offsite_dppa.OffsiteDppaResult (default capital structure)",
        repo_source_ref="src/python/reopt_pysam_vn/analysis/types.py",
    ),
    _line(
        "A10_debt_rate_vnd",
        slide=19,
        bucket="A",
        claim="VND debt interest rate",
        deck_value=0.085,
        deck_unit="fraction/yr",
        citation=None,
        repo_fn="data.vietnam.vn_financial_defaults_2025.standard.owner_discount_rate_fraction",
        repo_source_ref="data/vietnam/vn_financial_defaults_2025.json:17 (8% discount used as proxy; debt rate is a separate input)",
    ),
    _line(
        "A11_pv_degradation",
        slide=21,
        bucket="A",
        claim="PV annual degradation rate",
        deck_value=0.005,
        deck_unit="fraction/yr",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.SingleOwnerInputs.degradation_fraction",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py",
    ),
    _line(
        "A12_fmp_2025_avg",
        slide=15,
        bucket="A",
        claim="2025 average FMP (Wholesale Electricity Market reference)",
        deck_value=1426.6,
        deck_unit="VND/kWh",
        citation="EAVCED public training (deck only)",
        repo_fn="reopt_pysam_vn.integration.strike_search.sweep_strike_prices (FMP center)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/strike_search.py:44",
    ),
    _line(
        "A13_voltage_tier_22_110kv_demand_charge",
        slide=23,
        bucket="A",
        claim="Demand / capacity charge at 22-110 kV (Decree 146 trial)",
        deck_value=235414.0,
        deck_unit="VND/kW/month",
        citation=None,
        repo_fn="data.vietnam.vn_tariff_2025.demand_charge.two_part_tariff_trial.capacity_charge_vnd_per_kw_month.medium_voltage_22kv_to_110kv",
        repo_source_ref="data/vietnam/vn_tariff_2025.json:178",
    ),
]


# --------------------------------------------------------------------------
# B — Finding checks (computed via the engine for a deck scenario)
# --------------------------------------------------------------------------
# deck_value is the deck-stated target; repo_value is what the engine returns
# when run with the same parameters.
B: list[Check] = [
    _line(
        "B01_simulation_5line_total_evnbill",
        slide=12,
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
        "B02_simulation_cfd_settlement",
        slide=12,
        bucket="B",
        claim="Module-2 simulation CfD settlement (line 5) for Q=6,000,000 kWh @ (1,300-1,200)",
        deck_value=600000000.0,
        deck_unit="VND/month",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement.buyer_cfd_payment_vnd",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:147",
        assumptions=["Same flat profile as B01."],
    ),
    _line(
        "B03_simulation_effective_blended_rate",
        slide=12,
        bucket="B",
        claim="Module-2 simulation effective blended rate (total/Q)",
        deck_value=1864.0,
        deck_unit="VND/kWh",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement.annual_summary.buyer_blended_rate_vnd_kwh",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:182",
        assumptions=["Same flat profile as B01."],
    ),
    _line(
        "B04_pretax_delivered_cost_per_kwh",
        slide=13,
        bucket="B",
        claim="Pre-CfD delivered cost per matched kWh at 22-110 kV (1,504 + 360 + 163.3)",
        deck_value=2027.0,
        deck_unit="VND/kWh",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (1-line decomposition)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:119-122",
        assumptions=[
            "FMP=1,200; k*K_pp=1.03421; fees 360+163.3 applied to matched volume.",
        ],
    ),
    _line(
        "B05_scenario1_evn_bill",
        slide=39,
        bucket="B",
        claim="Workshop Scenario 1 EVN bill (5,000,000 kWh; FMP=1,150; Pc=1,250)",
        deck_value=8263196000.0,
        deck_unit="VND/month",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (5-line reproduction)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:65",
        assumptions=[
            "Flat 5,000,000 kWh profile in the relevant hours; same constants as deck lines 1-3.",
        ],
    ),
    _line(
        "B06_scenario1_cfd_total",
        slide=40,
        bucket="B",
        claim="Workshop Scenario 1 total customer cost C_KH = C_EVN + C_CfD",
        deck_value=8763196000.0,
        deck_unit="VND/month",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement.buyer_total_payment_vnd",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:127",
        assumptions=["Same flat profile as B05."],
    ),
    _line(
        "B07_scenario3_evn_bill",
        slide=43,
        bucket="B",
        claim="Workshop Scenario 3 EVN bill (Load=9,000,000, Q=8,000,000; FMP=1,600; Pc=1,500)",
        deck_value=19628262400.0,
        deck_unit="VND/month",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (5-line reproduction with residual)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:65",
        assumptions=[
            "Residual purchase 1,000,000 kWh at P1=2,204 VND/kWh.",
        ],
    ),
    _line(
        "B08_scenario3_total_cost",
        slide=44,
        bucket="B",
        claim="Workshop Scenario 3 total customer cost C_KH (after negative CfD)",
        deck_value=18828262400.0,
        deck_unit="VND/month",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement.buyer_total_payment_vnd",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:127",
        assumptions=["Same flat profile as B07."],
    ),
    _line(
        "B09_scenario4_evn_bill",
        slide=47,
        bucket="B",
        claim="Workshop Scenario 4 EVN bill (X+Y plants, 900k matched + 100k residual @ 1,800)",
        deck_value=2140229520.0,
        deck_unit="VND/month",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (per-plant sum)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:65",
        assumptions=[
            "Combined 900,000 kWh (X+Y) at SMP=1,600; residual 100,000 kWh at P1=1,800 (per deck).",
        ],
    ),
    _line(
        "B10_scenario4_net_cfd",
        slide=47,
        bucket="B",
        claim="Workshop Scenario 4 net CfD payment (X +60M, Y -30M)",
        deck_value=-30000000.0,
        deck_unit="VND/month",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (per-plant netting)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:122",
        assumptions=["Per-plant CfD: X=(1,500-1,600)*600k; Y=(1,700-1,600)*300k."],
    ),
    _line(
        "B11_case5_seller_irr",
        slide=24,
        bucket="B",
        claim="Case 5 (Solar + Large BESS) — Seller equity IRR",
        deck_value=0.169,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model (proxy sizing, no real hourly)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141",
        assumptions=[
            "Undisclosed sizing/finance; uses repo 49 MWp-class defaults + deck's stated 70/8.5/10/25-yr inputs.",
            "Method+directional (DEC-007), not exact reproduction.",
        ],
    ),
    _line(
        "B12_case5_min_dscr",
        slide=24,
        bucket="B",
        claim="Case 5 (Solar + Large BESS) — Minimum DSCR (replacement year)",
        deck_value=1.14,
        deck_unit="x",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model + extract_single_owner_outputs",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141",
        assumptions=[
            "BESS replacement year ~11 modeled as a -$1.2M capex shock; DSCR may register < 1.20x.",
        ],
    ),
    _line(
        "B13_case6_seller_irr",
        slide=25,
        bucket="B",
        claim="Case 6 (Solar + Min BESS) — Seller equity IRR",
        deck_value=0.269,
        deck_unit="fraction",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model (proxy, lean sizing)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141",
        assumptions=["Method+directional per DEC-007."],
    ),
    _line(
        "B14_case6_min_dscr",
        slide=25,
        bucket="B",
        claim="Case 6 (Solar + Min BESS) — Minimum DSCR",
        deck_value=1.50,
        deck_unit="x",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model + extract_single_owner_outputs",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141",
        assumptions=["Lean BESS: no replacement shock assumed within loan tenor."],
    ),
    _line(
        "B15_56sweep_empty_window_method",
        slide=26,
        bucket="B",
        claim="56-scenario strike sweep — empty window (no triple-pass scenario at current fees)",
        deck_value="empty",
        deck_unit="categorical",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.run_strike_sweep (12 strikes x Q fractions)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:274",
        assumptions=[
            "Method-level: reproduce the buyer-positive-just-as-lender-drops-below-1.20x pattern (DEC-007).",
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
        "C01_overcontracting_cap",
        slide=10,
        bucket="C",
        claim="Over-contracting (Q_c > hourly consumption) caps CfD at consumed volume",
        deck_value="capped at min(load, gen)",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.settlement.compute_hourly_settlement (matched = min(load, gen))",
        repo_source_ref="src/python/reopt_pysam_vn/integration/settlement.py:103",
    ),
    _line(
        "C02_load_shape_overlap",
        slide=17,
        bucket="C",
        claim="Solar peak at midday vs factory evening peak — overlap is hour-by-hour",
        deck_value="low overlap daytime",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.matching.physical_fit_from_profile",
        repo_source_ref="src/python/reopt_pysam_vn/integration/matching.py:183",
    ),
    _line(
        "C03_year1_above_bau",
        slide=13,
        bucket="C",
        claim="Year 1 DPPA cost typically at/above BAU; savings build with EVN escalation",
        deck_value="Y1 >= BAU",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.analysis.offsite_dppa.run_offsite_dppa (10-yr cumulative vs BAU)",
        repo_source_ref="src/python/reopt_pysam_vn/analysis/offsite_dppa.py",
    ),
    _line(
        "C04_oversized_bess_dscr_dip",
        slide=24,
        bucket="C",
        claim="Oversized BESS -> replacement-year DSCR dip below 1.20x",
        deck_value="min DSCR < 1.20x in BESS replacement year",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.pysam.single_owner.run_single_owner_model (with BESS capex shock)",
        repo_source_ref="src/python/reopt_pysam_vn/pysam/single_owner.py:141",
    ),
    _line(
        "C05_bankability_floor",
        slide=20,
        bucket="C",
        claim="Strike below developer bankability floor means no project (not a cheap deal)",
        deck_value="strike_floor exists",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.strike_search.sweep_strike_prices (find min strike at target IRR)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/strike_search.py:44",
    ),
    _line(
        "C06_daytime_vs_night_economics",
        slide=52,
        bucket="C",
        claim="Daytime-aligned load shapes deliver stronger DPPA outcomes than evening/night-heavy loads",
        deck_value="daytime > night",
        deck_unit="qualitative",
        citation=None,
        repo_fn="reopt_pysam_vn.integration.matching.physical_fit_from_profile (daytime vs night profiles)",
        repo_source_ref="src/python/reopt_pysam_vn/integration/matching.py:183",
    ),
]


CHECKS: list[Check] = A + B + C


# --------------------------------------------------------------------------
# Known gaps — slides that are relevant but intentionally out of repo scope
# --------------------------------------------------------------------------
KNOWN_GAPS: list[KnownGap] = [
    KnownGap(
        id="KG01_decree146_two_part_tariff",
        slide=6,
        topic="Two-part tariff / Decree 146 capacity charge buyer P&L",
        note=(
            "Repo captures the Decree 146 trial capacity charge as a data file (vn_tariff_2025.json:178) "
            "and a Session 4.3 case study, but does not have a wired buyer P&L model for the two-part "
            "regime end-to-end. Buyers' all-in cost under capacity+energy billing is qualitative here."
        ),
    ),
    KnownGap(
        id="KG02_recs_eacs",
        slide=53,
        topic="RECs/EACs attribute economics",
        note=(
            "Repo does not model RECs/EACs unbundled pricing or attribute ownership. The deck's RECs "
            "discussion is qualitative (additionally, use cases) and outside repo scope."
        ),
    ),
    KnownGap(
        id="KG03_ghg_scopes",
        slide=53,
        topic="GHG Scope 1/2/3 accounting",
        note=(
            "Repo does not model GHG inventories. The deck's Scope 1/2/3 framing is qualitative; "
            "vn_emissions_2024.json holds grid EF data but is not wired into a buyer emissions calc."
        ),
    ),
]


def to_dict(obj: Any) -> dict:
    """asdict wrapper that survives the (Check, KnownGap) union type."""
    return asdict(obj)


def all_rows() -> list[dict]:
    """Return all registry rows (checks + known gaps) as plain dicts."""
    return [to_dict(c) for c in CHECKS] + [to_dict(g) for g in KNOWN_GAPS]
