---
title: "Verify DPPA July 2026 Case Studies deck against the repo (calibrate-then-validate)"
date: "2026-06-26"
type: "brainstorm"
depth: "standard"
source_request: "Verify the claims and figures in ceba-review/DPPA Presentation July 2026 Case Studies.pptx against the reopt_pysam_vn repo, making explicit assumptions for any data not disclosed in the deck, and checking whether Cong reused a repo load profile for the case studies."
slug: "dppa-july-deck-verification"
---

# Brainstorm: Verify DPPA July 2026 Case Studies deck against the repo (calibrate-then-validate)

## Problem & Why Now
`ceba-review/DPPA Presentation July 2026 Case Studies.pptx` (28 slides, "Session 5.1: Off-Site
Solutions Deep Dive — Understanding DPPA Mechanisms") is a **revised, trimmed successor** to the
already-verified `CEBA DPPA 2026.pptx` (was "Session 5.2", ~50+ slides). It goes to a CEBA
workshop, so its quantitative claims need to hold up against the repo's PySAM/settlement model.

The new deck **sharpens the exact tension the prior verification left open.** The prior CEBA run
(`reports/ceba_dppa_2026_repo_check.md`: 16 ✅ / 5 ⚠️ / 14 ℹ️ / 0 ❌) could not reproduce Cases 5/6
(seller IRR 16.9% / 26.9%, min DSCR 1.14× / 1.50×): PySAM with **proxy CAPEX returned *negative*
DSCR (−2.42 / −2.81) at strike 2,000 VND/kWh** — the project didn't even service debt — and the
result was filed as ℹ️ "needs author disclosure" (DEC-007). The new deck now asserts the project
**is** financeable at strike 2,000 (positive IRR/DSCR, with the *buyer* overpaying ~9–14% vs BAU)
and builds a headline **"0 of 56 scenarios pass all three gates"** strike-sweep on top of it.

Per the user's instruction, the job is no longer to flag "can't reproduce." It is to **make the
undisclosed inputs (CAPEX, BESS size, FMP series) explicit, back-solve them so the deck's anchor
numbers are reproducible, then test whether the deck's downstream logic survives that calibration** —
clearly separating repo-reproducible claims from assumption-dependent ones.

## Current vs Desired State
- **Current state:** A purpose-built verification pipeline exists but is hardcoded to the *old*
  CEBA deck (slide numbers, deck-cited values, deck path). Cases 5/6 are unreproducible under proxy
  CAPEX. The new deck is untracked, unreviewed, and its richer disclosures (project IRR, NPV,
  payback, buyer-vs-BAU per horizon, 4 explicit 56-sweep gate rows) have no checks.
- **Desired state:** A parametrized pipeline that, for the July deck, (1) reproduces the disclosed
  settlement/tariff/finance claims, (2) back-solves project CAPEX so Cases 5/6 seller IRR matches at
  strike 2,000 and reports whether the *other* five metrics fall out consistently, (3) reproduces
  the 56-scenario sweep + "0 of 56" headline, and (4) emits a delta report + an annotated
  `[repo-checked]` copy of the deck — all with explicit, documented assumptions.
- **Key repo surfaces:**
  - **Load (the "same factory"):** `data/raw/factory_a/emivest_load_profile_1hr_2024.csv` (real 2024
    meter, ~9,315 MWh); `data/interim/factory_a/factory_a_extracted_inputs.json` +
    `scenarios/case_studies/factory_a/*.json` (synthetic 9,750 MWh, 2,430 kW peak, avg 1,113 kW,
    `medium_voltage_22kv_to_110kv`, south, industrial); `src/python/reopt_pysam_vn/integration/factory_a.py`.
    On-site Case 2 reference financials (the basis Cases 5/6 build on): PV 5.91 MW, BESS 1.8 MW /
    **10.7 MWh**, CAPEX **$4.27M**, slide IRR 18.2%, NPV $1.65M, DSCR 1.31.
  - **Settlement engine:** `src/python/reopt_pysam_vn/integration/settlement.py` —
    `compute_hourly_settlement(loads_kw, generation_kw, tariff_rates, fmp, ContractParams)`;
    `ContractParams(mode="virtual_cfd", strike_vnd_kwh, escalation_rate, dppa_adder_vnd_kwh=523.34,
    kpp_pct=2.7263 → kpp_factor 1.02726)`.
  - **Developer finance:** `src/python/reopt_pysam_vn/pysam/single_owner.py` —
    `run_single_owner_model(SingleOwnerInputs)` → `project_return_aftertax_irr_fraction`, `min_dscr`,
    `project_return_aftertax_npv_usd`. `depreciation_schedule` supports `vn_sl_15yr`.
  - **Strike sweep:** `src/python/reopt_pysam_vn/integration/strike_search.py` — `sweep_strike_prices(...)`.
  - **Offsite front door:** `src/python/reopt_pysam_vn/analysis/offsite_dppa.py` —
    `run_offsite_dppa(DealConfig, ...)`, extensible via `register_orchestrator(case, fn)`.
  - **Data layer:** `data/vietnam/vn_tariff_2025.json` (retail 2,204.0655; TOU peak hours [17–22];
    22–110kV multipliers peak 1.57 / standard 0.86 → ratio 1.826); `vn_financial_defaults_2025.json`
    (escalation 0.04; CIT 4+9); `vn_deal_defaults_2026.json` (VND/USD 26,400; debt 0.70 / 8.5% /
    10yr; FMP sensitivity 1,400 / **1,700** / 2,000). **No CAPEX/BESS-cost defaults** — proxy is
    hardcoded in `verify_ceba_dppa_deck.py` (~$700/kW PV, $420/kW BESS, $1.2M Case-5 replacement).
  - **Pipeline:** `scripts/python/integration/ceba_deck/deck_checks.py` (`Check` dataclass: id,
    slide, bucket, claim, deck_value, deck_unit, deck_citation, repo_fn, repo_source_ref,
    assumptions, repo_value, delta_pct, verdict, takeaway, notes), `verify_ceba_dppa_deck.py`
    (orchestrator + `classify()` + per-check runners + `_flat_profile()` + `_try_pysam_check()`),
    `synthesize_md_report.py`, `inject_repo_notes.py`; tests `test_deck_checks.py`,
    `test_inject_idempotency.py`.

## Resolved Decisions
- **DEC-001:** **Calibrate-then-validate**, not flag-gaps-only. Back-solve undisclosed inputs so the
  deck's anchors reproduce, document them as explicit assumptions, then test the downstream logic.
  — The user explicitly wants the assumptions made visible, not just "unreproducible."
- **DEC-002:** **Load = synthetic 9,750 MWh anchor + real-Emivest-meter sensitivity.** Calibrate on
  the synthetic profile the on-site session/deck actually used (so Cases 5/6 reproduce the deck),
  and report the real meter (`emivest_load_profile_1hr_2024.csv`, ~9,315 MWh, different day/night
  split per the M1 finding) as a sensitivity row quantifying the load-data risk.
- **DEC-003:** **FMP = deck 1,426.6 anchor + repo 1,700 sensitivity.** Calibrate at the deck's stated
  FMP to reproduce its story; re-run at the repo center 1,700 to show robustness; carry the A12
  reconcile forward. Hourly FMP shape defaults to **flat-at-monthly-mean** (ASM-001).
- **DEC-004:** **Pin BESS from hints, solve CAPEX only.** Fix Case 5 BESS energy from the "~$1.2M
  year-11 replacement" hint and Case 6 from the on-site 10.7 MWh reference; solve project
  `installed_cost_usd` so the model's seller IRR matches the deck at strike 2,000 / FMP 1,426.6.
  Treat the remaining five metrics (project IRR, NPV, min DSCR, payback, buyer-vs-BAU) as pass/fail
  checks, not solve targets. — Simpler than a 2-lever joint solve; fewer degrees of freedom.
- **DEC-005:** **Parametrized pipeline + delta report + annotated deck.** Parametrize the pipeline
  around a `deck_config` (deck path, slide map, output names) so the CEBA and July decks are both
  first-class. Produce: a July-scoped registry (28 slides) + a calibration module + a delta
  markdown/JSON (repro vs calibrated-under-assumption vs unverifiable) + an annotated
  `DPPA July 2026 [repo-checked].pptx` with `[Repo check]` notes. CEBA artifacts/tests untouched.
- **DEC-006 (mechanical):** **Slide remap + scope to the 28-slide deck.** Port reusable checks with
  new slide numbers (worked example B01–B04 → slides 11–12; A-bucket fees/tariffs/debt → slides
  4/8/10/14/15/18/22; Case 5/6 → slides 23/24; 56-sweep → slide 25). **Drop** checks whose slides
  don't exist in this deck (old workshop scenarios B05–B10 on slides 39–47; C06 slide 52; KG02/KG03
  slide 53). **Add** new checks for the new disclosures: Case 5/6 project IRR, NPV, payback,
  buyer-vs-BAU (Y1 / 10-yr / lifetime), and the four explicit 56-sweep gate rows.
- **DEC-007 (mechanical):** **Verdict framework** reuses DEC-004 bands (±1% → ✅ ok; 1–5% → ⚠️;
  >5% → ❌) and citation-preserving ⚠️ reconcile, and **adds a 🔧 "calibrated" tier** = "reproducible
  under stated assumption" for Case 5/6 metrics that match once CAPEX is back-solved — distinct from
  the prior ℹ️ "cannot reproduce."
- **DEC-008 (mechanical):** Reuse `compute_hourly_settlement`, `run_single_owner_model`,
  `sweep_strike_prices`, and `factory_a.py` rather than re-implement; the new calibration is a thin
  driver over these. PySAM runs only in `.venv` (Py 3.12) via `.venv\Scripts\python.exe`.

## Assumptions & Constraints
- **ASM-001:** Hourly FMP shape = flat at the monthly-average value (deck discloses only an average;
  matches the slide-10/11 worked example which uses a single monthly-avg FMP).
- **ASM-002:** The synthetic 9,750 MWh Factory A profile (`load_source: "synthetic"`) is the load the
  deck used for Cases 5/6 ("same factory as yesterday"); verified against the real meter as DEC-002.
- **ASM-003:** Disclosed deal terms are authoritative and used as-is: strike 2,000 VND/kWh, 4%/yr
  escalation, 70% debt / 8.5% VND / 10-yr tenor, 25-yr analysis, Decree 57/2025 virtual CfD.
- **ASM-004:** VND/USD = 26,400 (`vn_deal_defaults_2026.json`) for all USD-denominated metrics (NPV).
- **ASM-005:** "Seller equity IRR" maps to PySAM `project_return_aftertax_irr_fraction` (levered,
  after-tax); "Project IRR" maps to the unlevered/pre-finance IRR — to be confirmed in /plan (Q-002).
- **CON-001:** Must not break the committed CEBA pipeline, registry, reports, or tests — the July
  pipeline is parametrized/parallel, not an in-place rewrite.
- **CON-002:** Deck binaries (source + `[repo-checked]` copy) stay **untracked** per the DEC-009
  precedent (large binaries not committed); only code + reports are committed.
- **CON-003:** Note injection must stay idempotent (delimiter-based, byte-stable on re-run), matching
  `inject_repo_notes.py` / `test_inject_idempotency.py`.

## Approaches Considered
- **Chosen:** Calibrate-then-validate with **pinned BESS + CAPEX-only solve**, synthetic-load anchor,
  deck-FMP anchor, targeted load/FMP sensitivities — reproduces the deck honestly while exposing
  exactly which conclusions depend on undisclosed assumptions.
- **ALT-001:** Flag-gaps-only (prior DEC-007 stance) — rejected by the user: it doesn't make the
  assumptions explicit and leaves the deck's central claim untested.
- **ALT-002:** Two-lever joint solve (CAPEX + BESS size to hit IRR + DSCR simultaneously) — rejected
  (DEC-004): more degrees of freedom, harder to attribute residuals; the pinned-BESS approach is
  simpler and keeps the internal-consistency check meaningful.
- **ALT-003:** Full sensitivity bands on every undisclosed input — rejected as too heavy; only the
  two highest-leverage uncertainties (load, FMP) get explicit sensitivities.

## Out of Scope
- RECs/EACs attribute economics and GHG Scope 1/2/3 accounting (not in this 28-slide deck; KG02/KG03).
- Decree 146 two-part-tariff buyer P&L (an on-site / Session-4.x topic; KG01).
- Re-validating EVN tariff/TOU data already confirmed in the prior CEBA run and the 2026 market brief.
- The on-site Cases 1–4 (covered by the completed Factory A BESS validation; M1–M4 comments).
- Regulatory fact-checking of the deck's legal claims (Decree 57/58/61) — covered by the existing
  Vietnam market research briefs; this work is numeric reproduction only.

## Open Questions
1. **Q-001:** What solar (and BESS power) sizing does the offsite Case 5/6 *project* use? The deck
   discloses neither; slide-10's "50 MW solar plant" is a generic 6,000 MWh/month industrial-park
   illustration, **not** the ~9,750 MWh/yr Case 5/6 factory.
   - **Recommended default:** Size the offsite solar+BESS so contracted/matched volume ≈ the deck's
     70–100% contract-volume axis applied to the factory's 9,750 MWh/yr (i.e., a few MW of solar,
     not 50 MW), consistent with the 56-sweep's volume dimension.
   - **Why this matters:** Generation sets matched volume Q_Khc, which drives *both* the buyer
     settlement (buyer-vs-BAU) and the developer's CfD revenue — so it co-determines every Case 5/6
     metric and the sweep.
2. **Q-002:** Does "Seller equity IRR" = PySAM `project_return_aftertax_irr_fraction` (levered,
   after-tax to equity), and "Project IRR" = the unlevered/pre-finance IRR?
   - **Recommended default:** Yes (ASM-005). Confirm against `single_owner.py` output names before
     calibrating, since solving CAPEX to the wrong IRR definition mis-sizes the whole case.
   - **Why this matters:** The calibration target *is* this metric; a wrong mapping silently biases
     CAPEX and cascades into DSCR/NPV/payback residuals.
3. **Q-003:** What BESS energy-replacement $/kWh converts the "~$1.2M year-11 replacement" hint into
   a Case-5 MWh size? The repo proxy uses $420/**kW** (power), not $/kWh.
   - **Recommended default:** Use a market/repo BESS *energy* replacement cost (~$150–200/kWh) →
     $1.2M ≈ 6–8 MWh; sanity-check against the on-site 10.7 MWh reference and adjust if inconsistent.
   - **Why this matters:** It pins Case 5's BESS size (DEC-004), which sets the replacement-year DSCR
     dip the deck's "battery eats the deal" lesson depends on.

## Suggested Next Step
Run `/plan dppa-july-deck-verification` to turn this into a multi-phase implementation plan.
