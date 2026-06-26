---
title: "Verify the DPPA July 2026 Case Studies deck against the repo (calibrate-then-validate)"
date: "2026-06-26"
status: "draft"
request: "Fix activeContext, then from the brainstorm produce a multi-phase plan to verify the claims/figures in ceba-review/DPPA Presentation July 2026 Case Studies.pptx against reopt_pysam_vn, making explicit assumptions for undisclosed data and back-solving Cases 5/6, then commit and push."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-06-26_dppa-july-deck-verification-brainstorm.md"
  - "research/2026-06-23_bess-deck-claims.md"
---

# Plan: Verify the DPPA July 2026 Case Studies deck against the repo (calibrate-then-validate)

## Objective
Verify every repo-testable claim in `ceba-review/DPPA Presentation July 2026 Case Studies.pptx`
(28 slides, "Session 5.1: Off-Site Solutions Deep Dive") against the `reopt_pysam_vn` model. Where
the deck withholds inputs (project CAPEX, BESS size, FMP series), make the assumptions **explicit**
and **back-solve project CAPEX** so Cases 5/6 reproduce at strike 2,000, then test whether the
deck's downstream logic — the six per-case metrics, the buyer-vs-BAU horizons, and the headline
"0 of 56 scenarios pass all three gates" — survives that calibration. Output a delta report and an
annotated `[repo-checked]` copy of the deck for the CEBA workshop.

## Context Snapshot
- **Current state:** The CEBA verification pipeline (`scripts/python/integration/ceba_deck/`) is
  hardcoded to the *old* CEBA deck (deck path, slide numbers, deck-cited values) and used a generic
  **49 MW @ 18% CF proxy** with placeholder CAPEX (~$700/kW PV + $420/kW BESS + a $1.2M shock bolted
  on as upfront CAPEX) that returns *negative* DSCR at strike 2,000 — so Cases 5/6 are filed ℹ️
  "cannot reproduce" (DEC-007). The new deck is untracked and unreviewed; its richer disclosures
  (project IRR, NPV, payback, per-horizon buyer-vs-BAU, four explicit 56-sweep gate rows) have no
  checks.
- **Desired state:** A `deck_config`-parametrized pipeline that, for the July deck, (1) reproduces
  the disclosed A-bucket + worked-example settlement claims, (2) back-solves project CAPEX so each
  case's seller IRR matches at strike 2,000 / FMP 1,426.6 and reports whether the other five metrics
  fall out consistently (🔧 "calibrated" verdict), (3) reproduces the 56-scenario sweep + "0 of 56"
  headline, with load and FMP sensitivities, and (4) emits a delta markdown/JSON + an annotated
  `DPPA July 2026 [repo-checked].pptx`. The committed CEBA pipeline/tests stay green.
- **Key repo surfaces:**
  - Pipeline to parametrize: `scripts/python/integration/ceba_deck/deck_checks.py`,
    `scripts/python/integration/verify_ceba_dppa_deck.py`,
    `scripts/python/integration/ceba_deck/synthesize_md_report.py`,
    `scripts/python/integration/ceba_deck/inject_repo_notes.py`,
    `scripts/python/integration/_extract_ceba_deck_text.py`.
  - Engines (reuse, do not re-implement): `src/python/reopt_pysam_vn/integration/settlement.py`
    (`compute_hourly_settlement`, `ContractParams`), `src/python/reopt_pysam_vn/pysam/single_owner.py`
    (`run_single_owner_model` → `project_return_aftertax_irr_fraction`, `min_dscr`,
    `project_return_aftertax_npv_usd`; IRR derived from `cf_project_return_aftertax_cash` @ line 175,
    DSCR from `cf_pretax_dscr` @ line 185), `src/python/reopt_pysam_vn/integration/strike_search.py`
    (`sweep_strike_prices`), `src/python/reopt_pysam_vn/integration/factory_a.py`.
  - Load: `data/interim/factory_a/factory_a_extracted_inputs.json` +
    `scenarios/case_studies/factory_a/*.json` (synthetic 9,750 MWh, 2,430 kW peak, 22–110kV south);
    `data/raw/factory_a/emivest_load_profile_1hr_2024.csv` (real meter, ~9,315 MWh).
  - Data layer: `data/vietnam/vn_tariff_2025.json`, `vn_financial_defaults_2025.json`,
    `vn_deal_defaults_2026.json` (FMP 1,400/1,700/2,000; VND/USD 26,400; debt 0.70/8.5%/10yr).
  - Deck (untracked): `ceba-review/DPPA Presentation July 2026 Case Studies.pptx`.
- **Out of scope:** RECs/EACs + GHG scopes (KG02/KG03, not in this deck); Decree 146 two-part buyer
  P&L (KG01, on-site topic); regulatory/legal fact-checking (covered by the 2026 market briefs);
  on-site Cases 1–4 (done in the Factory A validation); re-validating EVN tariff data already
  confirmed in the CEBA run.

## Research Inputs
- `research/2026-06-26_dppa-july-deck-verification-brainstorm.md` — sets the approach (DEC-001
  calibrate-then-validate), the load choice (DEC-002 synthetic anchor + real-meter sensitivity),
  the FMP basis (DEC-003 deck 1,426.6 anchor + repo 1,700 sensitivity, flat-at-mean shape), the
  BESS/CAPEX strategy (DEC-004 pin BESS, solve CAPEX), the deliverables (DEC-005 parametrized
  pipeline + delta report + annotated deck), and the three open questions carried into `## Grill Me`.
- `research/2026-06-23_bess-deck-claims.md` — confirms the "same factory" is Emivest/Factory A,
  documents the synthetic-9,750 vs real-meter-9,315 MWh load gap and the day/night split mismatch
  (M1), and validates the regulatory frame (Decree 57/58/61, Decision 963, two-component tariff) so
  this plan can stay numeric-only.

## Assumptions and Constraints
- **ASM-001:** Hourly FMP shape = flat at the disclosed monthly average (deck gives only an average;
  matches the slide-10/11 worked example).
- **ASM-002:** The synthetic 9,750 MWh Factory A profile is the load the deck used for Cases 5/6
  ("same factory as yesterday"); the real Emivest meter is a sensitivity, not the anchor.
- **ASM-003:** Disclosed deal terms are authoritative: strike 2,000 VND/kWh, 4%/yr escalation, 70%
  debt / 8.5% VND / 10-yr tenor, 25-yr analysis, Decree 57/2025 virtual CfD, VN SL-15yr depreciation.
- **ASM-004:** VND/USD = 26,400 (`vn_deal_defaults_2026.json`) for USD metrics (NPV).
- **CON-001:** Do not break the committed CEBA pipeline, registry, reports, or tests — the July work
  is `deck_config`-parametrized / parallel, never an in-place rewrite of the CEBA path.
- **CON-002:** Deck binaries (source + `[repo-checked]` copy) stay untracked; commit code + reports
  only.
- **CON-003:** Note injection stays idempotent (delimiter `=== [Repo check] (generated) ===`,
  byte-stable on re-run), matching `inject_repo_notes.py` / `test_inject_idempotency.py`.
- **CON-004:** PySAM 7.1.0 + python-pptx run only in `.venv` (Py 3.12); invoke everything via
  `.venv\Scripts\python.exe` with `PYTHONPATH=src/python;scripts/python` and `PYTHONIOENCODING=utf-8`.
- **DEC-001..005:** As locked in the brainstorm (see Research Inputs). **DEC-006:** slide remap +
  scope to 28 slides (drop old B05–B10/C06/KG02/KG03; add the new disclosures). **DEC-007:** verdict
  bands reuse ±1%/1–5%/>5% + ⚠️ citation-preserving, plus a new 🔧 "calibrated" tier. **DEC-008:**
  reuse settlement/single_owner/strike_search/factory_a engines.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Parametrize the pipeline around a `deck_config`; build the July registry + deck text | None | `deck_config`, `july_deck_checks.py`, extracted text, green CEBA tests |
| PHASE-02 | Reproduce the disclosed A-bucket + worked-example settlement checks (slides 4–15) | PHASE-01 | Populated A/B-worked-example results in the July JSON |
| PHASE-03 | Back-solve project CAPEX for Cases 5/6 (pin BESS, solve to seller IRR) | PHASE-01 | `calibrate_cases.py`, solved-assumptions JSON |
| PHASE-04 | Validate downstream: 5 remaining metrics + 56-sweep + load/FMP sensitivities | PHASE-03 | Case 5/6 + sweep verdicts + sensitivity tables in JSON |
| PHASE-05 | Synthesize delta report, inject annotated deck, add tests | PHASE-02, PHASE-04 | Delta `.md`, `[repo-checked]` deck, smoke + idempotency tests |

## Detailed Phases

### PHASE-01 - Parametrize the pipeline + July registry + deck text
**Goal**
Make the pipeline deck-agnostic and stand up a July-scoped check registry, without disturbing the
committed CEBA path.

**Tasks**
- [ ] TASK-01-01: Introduce a `DeckConfig` dataclass (deck pptx path, extracted-text path, registry
      module, output JSON/MD/pptx names, deck title) in a new
      `scripts/python/integration/ceba_deck/deck_config.py`; define `CEBA_2026` and `JULY_2026`
      configs. Refactor `verify_ceba_dppa_deck.py`, `synthesize_md_report.py`, and
      `inject_repo_notes.py` to take a `DeckConfig` (default = `CEBA_2026` so existing entry points
      and tests keep working).
- [ ] TASK-01-02: Generalize `_extract_ceba_deck_text.py` to accept a deck path (or add a thin
      `extract_deck_text(path)` helper) and emit
      `ceba-review/dppa_july_2026_case_studies_text.txt` for the new deck.
- [ ] TASK-01-03: Create `scripts/python/integration/ceba_deck/july_deck_checks.py` — port the
      reusable CEBA checks with **remapped slide numbers** and **new deck-cited values**, drop checks
      whose slides are absent, and add stubs for the new disclosures. Mapping:
      A03 retail 2,204 → s10/s4; A04 fees 360+163.3=523.3 → s8; A06 k 1.026 / A07 K_pp 1.008 → s10;
      A08 escalation 4% → s15/s22; A09/A10/A14 debt 70%/8.5%/10yr → s18/s22; A11 PV degr 0.5% → s20;
      A12 FMP 1,426.6 → s8/s14; A15 IRR 12–15% / A16 CIT 4+9 → s18; B01–B04 worked example → s11/s12;
      Case 5/6 → s23/s24; 56-sweep → s25. New checks: Case 5/6 project IRR (13.5%/18.2%), NPV
      ($1.52M/$2.54M), payback (9.1/4.7 yr), buyer-vs-BAU (s23 −8.7%/−8.9%/−9.3%; s24 −14.4%), and
      the four s25 gate rows.
- [ ] TASK-01-04: Add the 🔧 "calibrated" verdict to `classify()` (verdict set + icon in
      `synthesize_md_report.py` / `inject_repo_notes.py`); keep DEC-007/DEC-008 lineage intact.

**Files / Surfaces**
- `scripts/python/integration/ceba_deck/deck_config.py` (new) — deck parametrization.
- `scripts/python/integration/ceba_deck/july_deck_checks.py` (new) — July registry.
- `scripts/python/integration/verify_ceba_dppa_deck.py` — accept `DeckConfig`; route runners by config.
- `scripts/python/integration/ceba_deck/synthesize_md_report.py`, `inject_repo_notes.py` — config-driven paths + new icon.
- `scripts/python/integration/_extract_ceba_deck_text.py` — generalize to any deck path.

**Dependencies**
- None.

**Exit Criteria**
- [ ] `pytest tests/python/.../test_deck_checks.py` (CEBA) still passes unchanged.
- [ ] New `july_deck_checks.py` imports cleanly; `all_rows()` returns the remapped/new check set with
      unique IDs and every check carrying `slide`, `repo_fn`, `repo_source_ref`.
- [ ] `dppa_july_2026_case_studies_text.txt` exists and slide numbers in the registry match it.

**Phase Risks**
- **RISK-01-01:** Refactoring shared modules breaks CEBA. Mitigation: default `DeckConfig=CEBA_2026`,
  run the full CEBA pipeline + tests before moving on (lessons.md: run the FULL suite after any
  structural move, not a subset).

### PHASE-02 - Reproducible checks (A-bucket + worked-example settlement, slides 4–15)
**Goal**
Populate the deterministic, disclosed-input checks: tariff/fee/loss-factor/finance assumptions and
the slides 10–12 five-line worked example.

**Tasks**
- [ ] TASK-02-01: Wire the A-bucket runners to the data layer for the new slide map (retail, TOU
      ratio, fees 523.34, k/K_pp collapse, escalation, debt terms, CIT, PV degradation, FMP). Carry
      forward the A07 (K_pp 1.008 vs 1.0273) and A12 (FMP 1,426.6 vs 1,700) ⚠️ reconciles.
- [ ] TASK-02-02: Reproduce the worked example via `compute_hourly_settlement` with a flat 8760
      profile (Q=6,000 MWh/mo, strike 1,300, FMP 1,200, K_pp 110kV 1.008, fees 523.3, retail 2,204):
      EVN bill 10,586,097,600; CfD 600,000,000; total 11,186,097,600; effective 1,864; pre-CfD 2,027.
- [ ] TASK-02-03: Run `verify_ceba_dppa_deck.py --deck july` and confirm these checks land ✅/⚠️ with
      the expected deltas.

**Files / Surfaces**
- `scripts/python/integration/verify_ceba_dppa_deck.py` — A-bucket + B01–B04 runners (config-routed).
- `data/vietnam/vn_tariff_2025.json`, `vn_financial_defaults_2025.json`, `vn_deal_defaults_2026.json` — read-only lookups.

**Dependencies**
- PHASE-01.

**Exit Criteria**
- [ ] Worked-example checks (B01–B04) match to ≤0.1%; A-bucket verdicts match the prior CEBA values
      (the underlying data didn't change), differing only in slide numbers.

**Phase Risks**
- **RISK-02-01:** Slide-text drift (the deck reworded a line) breaks a literal value parse.
  Mitigation: registry holds the deck value explicitly (not parsed live); cross-check against the
  extracted text once.

### PHASE-03 - Case 5/6 CAPEX calibration (pin BESS, solve CAPEX)
**Goal**
Back-solve project `installed_cost_usd` so each case's modeled seller IRR equals the deck's at strike
2,000 / FMP 1,426.6, with BESS size pinned from the deck's hints.

**Tasks**
- [ ] TASK-03-01: Build `scripts/python/integration/ceba_deck/calibrate_cases.py` — load the
      synthetic Factory A 8760 (via `factory_a.py`), size the offsite solar+BESS project (see Q-001),
      build the flat-mean FMP series at 1,426.6, and assemble `SingleOwnerInputs` (debt 0.70/8.5%/10yr,
      25-yr, VN SL-15yr, escalation 4%).
- [ ] TASK-03-02: Pin BESS energy: Case 5 from the "~$1.2M year-11 replacement" hint ÷ BESS energy
      $/kWh (Q-003); Case 6 from the on-site 10.7 MWh reference (or "minimum" lean size). Model the
      replacement as a year-11 cashflow, not an upfront CAPEX shock (improvement over the proxy).
- [ ] TASK-03-03: Implement a 1-D root solver (bisection/secant) on `installed_cost_usd` so
      `run_single_owner_model(...)["...project_return_aftertax_irr_fraction"]` == deck seller IRR
      (Case 5: 0.169; Case 6: 0.269) within tolerance. Emit the solved CAPEX and implied $/kW.
- [ ] TASK-03-04: Write `reports/dppa_july_2026_calibration.json` recording, per case, the pinned
      BESS, solved CAPEX, implied $/kW, and all model inputs — this is the explicit-assumption ledger.

**Files / Surfaces**
- `scripts/python/integration/ceba_deck/calibrate_cases.py` (new) — calibration driver.
- `src/python/reopt_pysam_vn/pysam/single_owner.py`, `integration/settlement.py`, `integration/factory_a.py` — reused.

**Dependencies**
- PHASE-01 (registry, config).

**Exit Criteria**
- [ ] Solver converges for both cases; modeled seller IRR within ±0.1pp of deck; solved CAPEX implies
      a plausible $/kW (flag if outside ~$600–1,100/kW PV-equivalent).
- [ ] `dppa_july_2026_calibration.json` lists every assumption used to close the gap.

**Phase Risks**
- **RISK-03-01:** No CAPEX produces the deck IRR (monotonic miss) → the deck's IRR is unreachable
  under disclosed terms even with free CAPEX. Mitigation: report the achievable IRR envelope and mark
  the case ❌/⚠️ with the binding constraint, rather than forcing convergence.
- **RISK-03-02:** "Seller equity IRR" maps to the wrong PySAM output (Q-002), biasing CAPEX.
  Mitigation: confirm the mapping against `single_owner.py` outputs in TASK-03-01 before solving.

### PHASE-04 - Downstream validation (5 metrics + 56-sweep + sensitivities)
**Goal**
With CAPEX fixed by calibration, test whether the rest of each case and the headline sweep reproduce.

**Tasks**
- [ ] TASK-04-01: For each case at the solved CAPEX, compute project IRR, NPV (USD @ 26,400), min
      DSCR, payback, and buyer-vs-BAU (Y1 / 10-yr / lifetime via `compute_hourly_settlement` vs an
      EVN-TOU BAU bill escalated 4%/yr). Classify each vs the deck (🔧 calibrated if it falls out
      consistently; ⚠️/❌ if not). Internal inconsistency (IRR matches but DSCR/NPV/payback don't) is
      itself a reported finding.
- [ ] TASK-04-02: Reproduce the 56-scenario sweep — 12 strikes (1,200–2,200) × 4 contract volumes
      (70–100%). For each, run settlement (buyer-vs-BAU) + finance (seller IRR, min DSCR) and apply
      the three gates (buyer ≤ BAU cumulative; seller IRR ≥ 12–15%; lender min DSCR ≥ 1.20×). Verify
      the four disclosed gate rows (≈2,000 / ≈1,400 / ≈1,300×70% / ≈1,200) and the "0 of 56 pass"
      headline.
- [ ] TASK-04-03: Sensitivities — re-run Cases 5/6 + the gate-crossing summary with (a) the real
      Emivest meter load (9,315 MWh) and (b) FMP at the repo center 1,700. Record how each moves the
      verdicts (e.g., does "0 of 56" still hold at FMP 1,700?).
- [ ] TASK-04-04: Persist everything to `reports/dppa_july_2026_repo_check.json` (same schema as the
      CEBA JSON; add a `sensitivities` block).

**Files / Surfaces**
- `scripts/python/integration/ceba_deck/calibrate_cases.py` + `verify_ceba_dppa_deck.py` — sweep + metrics.
- `src/python/reopt_pysam_vn/integration/strike_search.py` — `sweep_strike_prices` for the seller gate.

**Dependencies**
- PHASE-03.

**Exit Criteria**
- [ ] All six Case 5/6 metrics carry a verdict; the four sweep gate rows + the "0 of 56" headline are
      each confirmed/contradicted with numbers; both sensitivities are tabulated.

**Phase Risks**
- **RISK-04-01:** The gate definitions (esp. the buyer "cumulative ≤ BAU" horizon and the BAU
  escalation) are ambiguous and could flip a PASS/FAIL. Mitigation: state the exact gate formulas in
  the report; show buyer-vs-BAU on all three horizons so the reader can audit the call.

### PHASE-05 - Delta report + annotated deck + tests
**Goal**
Produce the human-facing deliverables and lock behavior with tests.

**Tasks**
- [ ] TASK-05-01: Extend `synthesize_md_report.py` to emit `reports/dppa_july_2026_repo_check.md` —
      verdict counts (incl. 🔧 calibrated), per-bucket tables, a **calibration ledger** section
      (assumptions used per case), a **sensitivity** section, and structural reconciliations (A07,
      A12, the calibration story, the 56-sweep). Add a short "what changed vs the CEBA verification"
      delta note.
- [ ] TASK-05-02: Run `inject_repo_notes.py --deck july` to write
      `ceba-review/DPPA July 2026 Case Studies [repo-checked].pptx` with idempotent `[Repo check]`
      notes per slide.
- [ ] TASK-05-03: Add `tests/python/.../test_july_deck_checks.py` (registry structure, unique IDs,
      slide coverage, new disclosures present) and extend the idempotency test to the July injector.
- [ ] TASK-05-04: Update `activeContext.md` phase-status table and append a results summary.

**Files / Surfaces**
- `scripts/python/integration/ceba_deck/synthesize_md_report.py`, `inject_repo_notes.py` — config-driven outputs.
- `reports/dppa_july_2026_repo_check.{json,md}`, `reports/dppa_july_2026_calibration.json` (new).
- `tests/python/.../test_july_deck_checks.py` (new); `tests/python/.../test_inject_idempotency.py` (extend).
- `ceba-review/DPPA July 2026 Case Studies [repo-checked].pptx` (new, untracked per CON-002).

**Dependencies**
- PHASE-02, PHASE-04.

**Exit Criteria**
- [ ] `reports/dppa_july_2026_repo_check.md` renders with all buckets, the calibration ledger, and
      the sensitivity tables; re-running the injector is byte-stable; new tests pass; CEBA tests still pass.

**Phase Risks**
- **RISK-05-01:** Note text overflows slide notes or duplicates on re-run. Mitigation: reuse the
  delimiter-based idempotent injector and its byte-stability test (CON-003).

## Verification Strategy
- **TEST-001:** `.venv\Scripts\python.exe -m pytest tests/python` (must keep the two known
  pre-existing failures as the only reds; everything CEBA stays green).
- **TEST-002:** `test_july_deck_checks.py` — registry integrity for the 28-slide deck; new-disclosure
  checks present; unique IDs; slide numbers consistent with the extracted text.
- **TEST-003:** Idempotency — inject twice, assert identical sha256 for the July `[repo-checked]` deck.
- **MANUAL-001:** Re-run end-to-end and read `reports/dppa_july_2026_repo_check.md`: confirm the
  calibration ledger states each assumption, Cases 5/6 carry 🔧/⚠️/❌ verdicts with numbers, and the
  "0 of 56" claim is explicitly confirmed or contradicted (incl. at FMP 1,700).
- **OBS-001:** Sanity-gate the solved CAPEX — log implied $/kW per case and flag if outside a
  plausible band; an implausible CAPEX means the deck's IRR is unreachable, which is itself the finding.

## Risks and Alternatives
- **RISK-001:** Calibrating to reproduce the deck can *launder* an internally inconsistent deck into a
  "verified" look. Mitigation: only the solved-for metric (seller IRR) is allowed to match by
  construction; the other five are independent checks, and the report foregrounds any inconsistency.
- **RISK-002:** The project-sizing assumption (Q-001) dominates every Case 5/6 number; a wrong choice
  invalidates the calibration. Mitigation: make sizing the top Grill Me item, record it in the
  ledger, and run the FMP/load sensitivities to bound its effect.
- **ALT-001:** Flag-gaps-only (prior DEC-007 stance) — rejected by the user; doesn't make the
  undisclosed assumptions explicit.
- **ALT-002:** Two-lever joint solve (CAPEX + BESS to hit IRR + DSCR) — rejected (DEC-004) as harder
  to attribute; pin-BESS/solve-CAPEX keeps the consistency check meaningful.

## Grill Me
1. **Q-001:** How is the offsite Case 5/6 *project* sized? The deck discloses neither solar MW nor
   BESS MW; the old pipeline used a generic 49 MW @ 18% CF (~77 GWh/yr), but the case factory only
   uses 9,750 MWh/yr.
   - **Recommended default:** Size solar+BESS so contracted/matched volume ≈ 70–100% of the factory's
     9,750 MWh/yr (a few MW of solar), consistent with the 56-sweep's volume axis — i.e., a deal
     built *for this factory*, not the 49 MW generic plant.
   - **Why this matters:** Generation sets matched volume Q_Khc, which drives both buyer-vs-BAU and
     developer CfD revenue, hence every Case 5/6 metric and the whole sweep.
   - **If answered differently:** A fixed 49 MW (merchant-plus-CfD) project changes the calibration to
     "developer economics of a large plant with a small matched slice," and the buyer-vs-BAU figures
     would reflect only ~13% of output — reframing the entire case narrative.
2. **Q-002:** Does the deck's "Seller equity IRR" map to PySAM `project_return_aftertax_irr_fraction`
   (levered, after-tax), and "Project IRR" to an unlevered/pre-finance IRR the wrapper doesn't yet
   expose?
   - **Recommended default:** Yes — calibrate CAPEX to `project_return_aftertax_irr_fraction` = seller
     IRR; compute "Project IRR" as an unlevered IRR (add the output if `single_owner.py` lacks it) and
     treat it as a consistency check only.
   - **Why this matters:** The solver's target metric *is* this mapping; a wrong choice mis-sizes CAPEX
     and cascades into DSCR/NPV/payback residuals.
   - **If answered differently:** If "Seller equity IRR" is the unlevered figure, the solver target and
     the new output flip, and the DSCR/leverage interpretation of the gates changes.
3. **Q-003:** What BESS energy-replacement cost ($/kWh) converts the "~$1.2M year-11 replacement" into
   a Case-5 MWh size? (The repo proxy uses $/kW power, not $/kWh, and the data layer has no BESS cost.)
   - **Recommended default:** ~$150–200/kWh → $1.2M ≈ 6–8 MWh; sanity-check against the on-site 10.7
     MWh reference and adjust if inconsistent.
   - **Why this matters:** It pins Case 5's BESS size (DEC-004), which sets the replacement-year DSCR
     dip the deck's "battery eats the deal" lesson depends on.
   - **If answered differently:** A higher $/kWh implies a smaller battery (and vice-versa), moving the
     replacement-year DSCR and the Case-5-vs-Case-6 contrast.

## Suggested Next Step
Answer the three `## Grill Me` questions (the recommended defaults are sound and let work start
immediately), then begin **PHASE-01**. Each phase ends with `/report <phase>` → git commit → push,
mirroring the CEBA workflow.
