# Client Demo Gap Analysis: Factory Data + Developer Matching Platform

**Date:** 2026-05-22
**Author:** Allotrope VC Engineering
**Status:** Draft for Review
**Scope:** Gaps between current `reopt-pysam-vn` repo capabilities and a client-facing demo that ingests real factory data, matches factories with developers' renewables projects (onsite and offsite), and produces decision-grade procurement reports under Vietnam's current regulatory framework.

---

## Executive Summary

The repo has strong analytical foundations — REopt.jl optimization, PySAM developer finance, Vietnam-specific preprocessing, DPPA settlement engines, TOU regime scenarios, and validated case studies. However, the current architecture is **research-grade and case-study-oriented**, not **client-demo-ready**. Five critical gaps separate the current state from a compelling demo with real factory data and developer project matching.

---

## Current Capabilities (What We Have)

| Capability | Status | Key Surfaces |
|---|---|---|
| REopt.jl optimization (PV, Wind, BESS) | Mature | `src/julia/REoptVietnam.jl`, `scripts/julia/run_vietnam_scenario.jl` |
| PySAM developer finance (Single Owner) | Working | `src/python/reopt_pysam_vn/pysam/`, `integration/bridge.py` |
| Vietnam preprocessing (tariff, costs, export rules) | Mature | `preprocess.py`, `data/vietnam/` (5 versioned JSON files) |
| Decision 963 TOU + regime engine | Working | `vn_regime_registry_2026.json`, `regime_runner.py`, materialize scripts |
| DPPA settlement (buyer-side hourly) | Working | `dppa_case_2.py` — strongest hourly settlement engine |
| Private-wire PPA screening | Working | `dppa_case_1.py` — tariff-ceiling screen |
| Strike-price discovery | Working | `strike_search.py` — PySAM sweep |
| Case studies | 3 validated | saigon18 (40 MWp), ninhsim (CPPA), north_thuan (30 MW wind+solar) |
| Physical-match ranking | Working | `rank_case_study_offtakers.py` — ranks factories for a fixed project |
| HTML/PPTX reporting | Working | Chart.js reports, Allotrope-branded deck generation |
| 4-layer test suite | Green | Data validation, unit, cross-language, integration |
| Decree 57 export-cap support | Working | Hard constraint in REopt via `REoptVietnam.jl` |

---

## Demo Narrative Target

> A Vietnamese C&I factory uploads its real 8760 load profile. The platform matches it against available developer renewables projects — both onsite (private-wire PPA behind the meter) and offsite (virtual/CfD DPPA through the grid). Under Vietnam's current regulatory framework (Decision 963 TOU windows, Decree 57 export rules, EVN tariff structure), it produces a side-by-side procurement recommendation with buyer economics, developer returns, settlement projections, and regulatory risk flags.

---

## Gap Analysis

### GAP-01: Factory Data Ingestion Pipeline

**Severity:** CRITICAL — Blocks the "real data" demo story entirely

**Current state:** Every case study has a bespoke extraction script (`extract_excel_inputs.py` for saigon18, `build_north_thuan_load_profile.py` for north_thuan, `build_ninhsim_extracted_inputs.py` for ninhsim). There is no generic "drop a file, get a normalized 8760 load profile" pathway.

**What's needed:**
- Generic 8760 load ingestion accepting CSV, XLSX, or JSON with flexible column mapping
- Load profile validation: 8760-hour check, negative/zero cleaning, interpolation for gaps
- Automatic metadata extraction: peak demand (kW), annual consumption (MWh), load factor, TOU profile classification
- Industry archetype classification (single-shift factory, two-shift, continuous process, commercial)
- Visual load-shape summary for immediate client feedback ("here's what we see in your data")
- Graceful handling of partial data (e.g., monthly bills → synthetic 8760 via REopt `simulated_load` API)

**Existing assets to reuse:**
- `extract_excel_inputs.py` has proven cleaning logic (negative clipping, interpolation)
- `rank_case_study_offtakers.py` has mixed-format ingestion (CSV, XLSX, JSON normalization)
- REopt `simulated_load` API is documented in `docs/data_and_api.md` for synthetic load generation

**Effort estimate:** 1 multi-phase plan (3-4 phases)

---

### GAP-02: Onsite vs Offsite Side-by-Side Procurement Comparison

**Severity:** CRITICAL — This IS the procurement decision; no existing workflow produces it

**Current state:** Cases 1-4 each evaluate ONE procurement model per case. Case 1 = private-wire PPA. Case 2 = synthetic financial DPPA. Case 3 = real-project realism bridge. Case 4 = planned but unimplemented. No workflow runs the same factory through both onsite and offsite models and produces a single comparison artifact.

**What's needed:**
- Unified procurement comparison engine that takes one factory input and evaluates:
  - **Onsite PPA:** Behind-the-meter solar (+ optional BESS), private-wire settlement, buyer avoided-cost economics
  - **Offsite virtual DPPA:** Grid-connected RE project, CfD settlement against FMP/CFMP, buyer CfD payment stack (EVN bill + CfD net), developer IRR/DSCR
  - **Hybrid:** Onsite PV + offsite wind/solar CfD combination
- Side-by-side comparison artifact:
  - Buyer total cost of energy (VND/kWh blended) for each option
  - Buyer savings vs EVN-only baseline for each option
  - Developer returns (IRR, NPV, DSCR) for each option
  - RE penetration and emissions reduction for each option
  - Regulatory risk flags (export-cap exposure, FMP volatility, CfD basis risk)
- Single HTML report with decision matrix and recommendation logic

**Existing assets to reuse:**
- Case 1 private-wire settlement logic in `dppa_case_1.py`
- Case 2 hourly buyer settlement engine in `dppa_case_2.py` (canonical for CfD)
- PySAM Single Owner bridge in `bridge.py`
- Strike-price discovery in `strike_search.py`
- TOU regime engine for regulatory scenario sensitivity

**Effort estimate:** 1 multi-phase plan (5-6 phases)

---

### GAP-03: Developer Project Catalog and Matching Engine

**Severity:** HIGH — Without this, "matching" is manual and per-engagement

**Current state:** The repo has no concept of "available developer projects" as a data structure. Each case study hardcodes one project configuration. The physical-match ranking script ranks factories for a fixed project — not projects for a factory.

**What's needed:**
- Developer project catalog schema:
  ```json
  {
    "project_id": "string",
    "name": "string",
    "developer": "string",
    "location": {"lat": float, "lon": float, "province": "string", "region": "north|central|south"},
    "technology": "solar|wind|solar_bess|wind_bess|hybrid",
    "capacity_mw": float,
    "bess_mw": float | null,
    "bess_mwh": float | null,
    "grid_connection": "onsite_private_wire|grid_connected_22kv|grid_connected_110kv",
    "indicative_strike_usc_kwh": float | null,
    "available_from": "YYYY-MM",
    "dppa_structure": "private_wire|virtual_cfd|physical_dppa",
    "status": "operational|construction|development|prospective"
  }
  ```
- Matching engine that scores project-factory pairs on:
  - **Physical fit:** Load vs generation profile alignment (reuse ranking logic)
  - **Geographic proximity:** Onsite eligibility, grid zone compatibility
  - **Capacity fit:** Project size relative to factory demand
  - **Commercial fit:** Indicative strike vs factory's EVN cost baseline
  - **Regulatory fit:** Export-cap headroom, DPPA structure eligibility
- Ranked match list with explanation of fit/misfit for each pair

**Existing assets to reuse:**
- `rank_case_study_offtakers.py` physical-match scoring logic (invert direction)
- Case study metadata patterns from saigon18/ninhsim/north_thuan extracted inputs
- TOU benchmark computation from `preprocess.py`

**Effort estimate:** 1 multi-phase plan (3 phases)

---

### GAP-04: Generalized Settlement Engine

**Severity:** HIGH — Current settlement code is case-study-wired, not parameterized

**Current state:** The Case 2 hourly settlement engine (`dppa_case_2.py`) is the strongest analytical surface, but it's wired to ninhsim-specific paths and assumptions. It cannot accept arbitrary factory+project pairs without code changes.

**What's needed:**
- Extract the hourly settlement engine into a shared module accepting:
  - Factory load profile (8760 kW)
  - Project generation profile (8760 kW or production factor series)
  - EVN tariff parameters (customer type, voltage level, regime_id)
  - DPPA contract terms (strike, escalation, settlement quantity rule, excess treatment, DPPA adder, KPP)
  - Market reference series (FMP/CFMP for CfD settlement)
- Support both settlement modes:
  - **Private-wire:** Matched energy at strike price, residual on EVN, export under Decree 57 cap
  - **Virtual CfD:** Full EVN bill + CfD net payment (strike - FMP) on contracted quantity
- Output standardized settlement artifact with buyer economics, developer revenue, and risk metrics

**Existing assets to reuse:**
- Case 2 `buyer_settlement_ledger()`, `buyer_benchmark_artifact()`, `strike_negotiation_screen()` — the analytical logic exists, needs parameterization
- `dppa_settlement.py` — original settlement script with FMP-based CfD logic
- `compute_virtual_dppa_developer_revenue()` in `dppa_settlement.py`

**Effort estimate:** Part of GAP-02 plan, or standalone 2-phase effort

---

### GAP-05: Interactive Regulatory Scenario Surface

**Severity:** MEDIUM — The machinery exists but no interactive surface

**Current state:** The TOU regime engine (`regime_runner.py`, `vn_regime_registry_2026.json`) can materialize and compare scenarios across regulatory regimes, but only through batch CLI scripts. No interactive or rapid-feedback surface exists.

**What's needed:**
- Rapid regime comparison: "Show me this factory's economics under Decision 963 vs Decision 14" without running a full Julia solve
- Pre-computed tariff impact calculator: Given a load profile and voltage class, compute the annual EVN bill delta between regimes in seconds (Python-only, no REopt solve)
- Regime impact summary: hours affected, peak-hour revenue impact for solar-only vs solar+BESS, arbitrage cycle change
- Toggle for forward-looking regimes: draft 50% export cap, two-part tariff trial, BESS capacity payment

**Existing assets to reuse:**
- `vn_regime_registry_2026.json` — 5 regime bundles already defined
- `materialize_tou_comparison.py` — scenario materialization
- `build_vietnam_tariff()` — 8760 TOU rate builder
- `verify_tou_scenarios.py` — tariff difference analysis

**Effort estimate:** 1 multi-phase plan (2-3 phases)

---

## Second-Tier Gaps

| Gap | Severity | Description |
|---|---|---|
| GAP-06: Real project 8760 data | MEDIUM | CON-001 in Case 4 plan remains unresolved — no actual project load data available. Blocks decision-grade closeout. |
| GAP-07: 22kV demand-charge reconciliation | MEDIUM | REopt cannot natively represent two-part tariff demand charges. Post-processing layer needed for 22kV buyer benchmarks. |
| GAP-08: Multi-factory portfolio view | LOW | Current architecture is one-factory-at-a-time. No portfolio dashboard showing multiple factories' procurement options together. |
| GAP-09: Developer financial templates | LOW | PySAM Single Owner bridge is basic. No EPC margin modeling, no detailed debt structuring, no tax equity structures. |
| GAP-10: Market price data source | MEDIUM | FMP/CFMP series are synthetic proxies (transferred from saigon18). No live or historical wholesale market data feed. |
| GAP-11: Automated report generation | LOW | Report generators exist but are case-study-specific scripts. No generic "generate report for any factory+project pair" surface. |
| GAP-12: API / web service layer | LOW | Everything runs as local scripts. No REST API or web service for external consumption. |

---

## Recommended Sequencing for Demo Readiness

### Sprint 1: Foundation (Weeks 1-2)
- **GAP-01:** Factory data ingestion pipeline (generic 8760 loader + validator)
- **GAP-03:** Developer project catalog schema + seed data (3-5 representative projects)

### Sprint 2: Core Engine (Weeks 3-4)
- **GAP-04:** Generalized settlement engine (extract from Case 2, parameterize)
- **GAP-02 Phase 1-2:** Onsite vs offsite evaluation paths (unified scenario builder)

### Sprint 3: Comparison and Matching (Weeks 5-6)
- **GAP-02 Phase 3-4:** Side-by-side comparison artifact + decision matrix
- **GAP-03 Phase 2:** Matching engine scoring + ranked output

### Sprint 4: Demo Polish (Week 7)
- **GAP-05:** Rapid regime comparison (pre-computed tariff impact, no-solve)
- **GAP-02 Phase 5:** Unified HTML report with recommendation
- Demo script preparation with real factory data walkthrough

---

## Demo Scenario Outline

### Setup
- 2-3 real Vietnamese factory load profiles (anonymized if needed)
- 3-5 developer projects in catalog (mix of onsite solar, onsite solar+BESS, offsite wind, offsite solar CfD)

### Demo Flow
1. **Ingest:** Upload Factory A's 8760 load data → immediate load shape visualization + metadata
2. **Match:** System scores Factory A against available developer projects → ranked match list with fit explanations
3. **Compare:** For top 2 matches, run side-by-side onsite PPA vs offsite CfD evaluation
4. **Regulate:** Toggle Decision 963 vs Decision 14 → see bill impact and economics shift
5. **Report:** Generate procurement recommendation report (HTML or PPTX in Allotrope template)

### Decision Output
- "Factory A should pursue [onsite solar+BESS PPA / offsite wind CfD / hybrid] because [buyer savings / RE penetration / risk profile], with indicative strike at [X VND/kWh] producing [Y% developer IRR] under Decision 963."

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| No real factory 8760 data available for demo | Demo falls back to synthetic/proxy data | Pre-arrange 1-2 factory data sharing agreements; prepare synthetic fallback with clear staging labels |
| Julia cold-start latency in live demo | 3-8 minute wait during demo for REopt solve | Pre-solve scenarios; use no-solve validation for live demo; show pre-computed results with live tariff toggles |
| FMP/CFMP market data quality | CfD settlement results are directional, not bankable | Label as "indicative" in all outputs; document proxy basis; plan market data integration as Phase 2 |
| Regulatory uncertainty (Decision 963 multipliers) | Tariff levels are preliminary until next MOIT circular | Build sensitivity toggle into demo; show both "remapped multipliers" and "revised multipliers" scenarios |
| Demo scope creep | Demo tries to show everything, lands nothing | Hard-scope to one factory + one onsite + one offsite comparison with regime toggle |

---

## Appendix: Mapping to Existing Commercial Product Ideas

This gap analysis directly seeds the three commercial product concepts from `research/2026-04-26_commercial-product-ideas.md`:

| Gap | Maps to Product Idea |
|---|---|
| GAP-01 (ingestion) | Idea 1 — DPPA Deal Screener (load-curve ingestion) |
| GAP-02 (onsite vs offsite) | Idea 1 — DPPA Deal Screener (scenario engine) |
| GAP-03 (project catalog) | Idea 1 — DPPA Deal Screener (site-data service) |
| GAP-04 (settlement engine) | Idea 3 — Bankability & Settlement Studio |
| GAP-05 (regime toggle) | Idea 2 — TOU & Regulatory Scenario Engine |
| GAP-10 (market data) | Idea 3 — Bankability & Settlement Studio (FMP simulation) |

The demo acts as the **MVP validation surface** for all three product ideas simultaneously.
