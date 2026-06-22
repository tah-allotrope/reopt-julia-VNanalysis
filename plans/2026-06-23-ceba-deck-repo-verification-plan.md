---
title: "CEBA DPPA 2026 Deck — Repo Verification & In-Deck Review Notes"
date: "2026-06-23"
status: "draft"
request: "based on brainstorm, execute the deck testables with the current repo and insert review comments into the deck for colleagues"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-06-23_ceba-deck-repo-verification-brainstorm.md"
---

# Plan: CEBA DPPA 2026 Deck — Repo Verification & In-Deck Review Notes

## Objective
Run every repo-testable quantitative claim in `ceba-review/CEBA DPPA 2026.pptx` through the
real `reopt_pysam_vn` functions, capture deck-vs-repo deltas in a reproducible artifact, and
write structured `[Repo check]` review notes into the speaker-notes pane of a **copy** of the
deck so colleagues review against repo-computed figures before the CEBA workshop.

## Context Snapshot
- **Current state:** The 2026 deck is unverified and carries no review notes. The repo holds
  the settlement engine, PySAM developer-finance model, strike sweep, matching engine, and
  sourced Vietnam data, but nothing has been run against this specific deck. Prior `ceba_*`
  reports at repo root targeted the older Session 6.2 deck, not this one.
- **Desired state:** A committed, rerunnable script computes all A/B/C testables → a results
  JSON → a `reports/` summary markdown; and `ceba-review/CEBA DPPA 2026 [repo-checked].pptx`
  carries a structured `[Repo check]` note on each quantitative slide plus short "known gap"
  notes on relevant-but-unmodeled slides.
- **Key repo surfaces:**
  - `src/python/reopt_pysam_vn/integration/settlement.py` — `compute_hourly_settlement`,
    `compute_buyer_benchmark`, `run_strike_sweep`, `ContractParams`.
  - `src/python/reopt_pysam_vn/pysam/single_owner.py` + `pysam/metrics.py` —
    `run_single_owner_model`, `SingleOwnerInputs`, `extract_single_owner_outputs` (IRR, NPV, `min_dscr`).
  - `src/python/reopt_pysam_vn/integration/strike_search.py` — `sweep_strike_prices`.
  - `src/python/reopt_pysam_vn/integration/matching.py` — `match_projects_to_factory`,
    `physical_fit_from_profile`, `FactoryProfile`.
  - `data/vietnam/vn_tariff_2025.json`, `vn_financial_defaults_2025.json`, `vn_deal_defaults_2026.json`.
  - `.venv` (Python 3.12) — only environment with PySAM; `python-pptx` 1.0.2 also installed there.
- **Out of scope:** Editing slide content/figures (notes only); back-solving Case 5/6 exact
  inputs; modeling the Decree 146 two-part tariff buyer P&L; RECs/EACs & GHG accounting;
  re-verifying the Session 6.2 deck; native PowerPoint threaded comments.

## Research Inputs
- `research/2026-06-23_ceba-deck-repo-verification-brainstorm.md` — supplies all nine resolved
  decisions (DEC-001..DEC-009): exhaustive A/B/C scope, speaker-notes-into-a-copy delivery,
  structured verdict-block note format, ±1% match rule with structural diffs named, committed
  reproducible harness, quant-slides-plus-known-gaps coverage, method+directional standard for
  Case 5/6, respect-the-deck's-citation for divergent sourced values, and commit
  script+reports/ but leave the annotated pptx untracked. This plan is the execution of that brief.

## Assumptions and Constraints
- **ASM-001:** Repo Vietnam data is *a* reference, not an override. Per DEC-008, a slide that
  **cites** a diverging value (TOU window, FMP, fee split) is marked ⚠️ reconcile with both
  bases shown — never silently corrected or auto-❌.
- **ASM-002:** The five-line worked examples (Slides 12, 39–48) are flat monthly volumes, so
  they are modeled as a constant load=generation profile over the relevant hours; the engine's
  8760 ledger collapses to the deck's single-month arithmetic.
- **ASM-003:** Case 5/6 and the 56-scenario sweep use repo defaults + the deck's stated inputs
  (strike 2,000 VND escalating 4%/yr, 70% debt / 8.5% / 10yr, 25-yr tenor) plus a proxy hourly
  FMP/solar series; verdicts are "method-consistent / not," with assumed inputs listed in-note.
- **CON-001:** All PySAM runs **must** use `.venv` (Python 3.12); system Python has no PySAM
  wheel. Standardize the single command path on `.venv/Scripts/python.exe`. *(see [[pysam-venv-environment]])*
- **CON-002:** Never modify the original `.pptx`. A `~$CEBA DPPA 2026.pptx` lock file is present
  (deck open in PowerPoint) — write only the `[repo-checked]` copy.
- **CON-003:** Note injection must be idempotent — replace any prior `[Repo check]` block in a
  slide's notes rather than appending a duplicate; preserve pre-existing notes content.
- **DEC-001..DEC-009:** Fixed by the brainstorm (see Research Inputs); not re-litigated here.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Check registry + deck-fact extraction | None | `deck_checks.py` registry, extracted deck values |
| PHASE-02 | Compute all A/B/C testables via real repo functions | PHASE-01 | `verify_ceba_dppa_deck.py`, `reports/ceba_dppa_2026_repo_check.json` |
| PHASE-03 | Synthesize human-readable delta report | PHASE-02 | `reports/ceba_dppa_2026_repo_check.md` |
| PHASE-04 | Inject `[Repo check]` notes into a deck copy | PHASE-02 | `inject_repo_notes.py`, `[repo-checked].pptx` |
| PHASE-05 | End-to-end run, verify, commit & push | PHASE-03, PHASE-04 | Verified artifacts on `main` |

## Detailed Phases

### PHASE-01 - Check Registry & Deck-Fact Extraction
**Goal**
Define a single structured registry of every testable claim (one row per check) and pin the
deck-side values to specific slides, so computation and note-injection share one source of truth.

**Tasks**
- [ ] TASK-01-01: Create `scripts/python/integration/ceba_deck/__init__.py` and `deck_checks.py`
      defining a `Check` dataclass: `id`, `slide`, `bucket` (A/B/C), `claim`, `deck_value`,
      `deck_unit`, `deck_citation` (or `None`), `repo_fn` (e.g. `"settlement.compute_hourly_settlement"`),
      `repo_source_ref` (`file:line`), `assumptions` (list), and placeholders for computed
      `repo_value`, `delta_pct`, `verdict`, `takeaway`.
- [ ] TASK-01-02: Populate the registry with all A-bucket assumption checks: TOU multipliers &
      peak window (Slide 5), avg retail 2,204 (Slides 11/37), fees 360+163.3=523 (Slides 9/13/30),
      k=1.026 & Kpp=1.008 (Slides 9–11), escalation 4% (Slides 5/16), capital structure
      (Slides 19/21), PV degradation 0.5% (Slide 21), FMP ~1,427 (Slides 9/15).
- [ ] TASK-01-03: Populate B-bucket finding checks: five-line example 1,864 VND/kWh (Slide 12),
      pre-CfD ~2,027 (Slide 13), workshop Scenarios 1/3/4 line totals (Slides 39–48), Case 5
      metrics (Slide 24), Case 6 metrics (Slide 25), 56-scenario empty-window (Slide 26).
- [ ] TASK-01-04: Populate C-bucket insight checks: over-contracting caps (Slides 10/17),
      load-shape overlap (Slides 17/52/54), Year 1 ≥ BAU crossover (Slides 13/16/27), oversized
      BESS DSCR dip (Slide 24), bankability floor (Slide 20), daytime-vs-night economics (Slides 52/54).
- [ ] TASK-01-05: Add `known_gap` rows (no `repo_fn`): two-part tariff/Decree 146, RECs/EACs,
      GHG scopes — verdict pre-set `➖ out of repo scope`.

**Files / Surfaces**
- `scripts/python/integration/ceba_deck/deck_checks.py` - new registry module.
- `ceba-review/CEBA DPPA 2026.pptx` - source of deck values (read-only; re-extract text via
  `python-pptx` with `PYTHONIOENCODING=utf-8` to avoid the cp1252 crash seen earlier).

**Dependencies**
- None.

**Exit Criteria**
- [ ] `deck_checks.py` imports cleanly and enumerates ≥20 checks across buckets A/B/C plus the
      `known_gap` rows, each with a slide number and (where applicable) a `repo_fn`.

**Phase Risks**
- **RISK-01-01:** Deck text extraction mis-reads grouped shapes / tables. Mitigation: reuse the
  recursive `walk()` extractor already validated this session; spot-check Slides 12, 24, 26.

### PHASE-02 - Compute All Testables via Real Repo Functions
**Goal**
Run each check's `repo_fn` with the deck's stated inputs, fill `repo_value`/`delta_pct`/`verdict`,
and emit the results JSON. No faked numbers — every value traces to a real function call.

**Tasks**
- [ ] TASK-02-01: Implement `verify_ceba_dppa_deck.py` orchestrator that loads the registry,
      dispatches each `repo_fn`, and writes `reports/ceba_dppa_2026_repo_check.json`.
- [ ] TASK-02-02: A-bucket: load `data/vietnam/*.json` and compare data-file values to deck
      values (TOU window, 2,204, 523.34, escalation, capital structure, degradation). For
      k×Kpp, compute deck `1.026*1.008=1.03421` vs engine `ContractParams().kpp_factor` and
      record the structural delta.
- [ ] TASK-02-03: B-bucket settlement: build a flat single-month profile (load=gen) and call
      `compute_hourly_settlement` with deck params (Slide 11/12: Q=6,000 MWh, strike 1,300,
      FMP 1,200, adder 523.3) — assert line-1..5 totals and blended 1,864 VND/kWh. Repeat for
      workshop Scenarios 1 (Slide 39–41), 3 (negative CfD, Slides 43–45), 4 (multi-plant,
      Slides 46–49) using `compute_hourly_settlement` per plant + manual netting.
- [ ] TASK-02-04: B-bucket developer economics: call `run_single_owner_model` (in `.venv`) with
      deck Case-5/6 inputs (49 MWp-class plant, 70% debt, 8.5%, 10yr, 25-yr analysis, strike
      2,000 escalating 4%) for IRR / NPV / `min_dscr` / payback; compare to Slide 24/25 and mark
      method-consistent per DEC-007. Guard for PySAM-absent → status `skipped`, verdict `➖`.
- [ ] TASK-02-05: B-bucket empty-window: drive `run_strike_sweep` (buyer side) across the deck's
      12 strikes (1,200–2,200) and `sweep_strike_prices` / `run_single_owner_model` per strike
      for the lender `min_dscr`, reproducing "buyer turns positive as lender drops below 1.20×".
- [ ] TASK-02-06: C-bucket: demonstrate over-contract caps (`matched=min(load,gen)`), build two
      `FactoryProfile`s (daytime vs night-heavy) and run `physical_fit_from_profile` /
      `compute_hourly_settlement` to show the overlap and BAU-crossover relationships.
- [ ] TASK-02-07: Apply the ±1% verdict rule (DEC-004) and citation rule (DEC-008) in a single
      `classify(check)` helper; serialize verdicts + computed values into the JSON.

**Files / Surfaces**
- `scripts/python/integration/verify_ceba_dppa_deck.py` - new orchestrator/entry point.
- `src/python/reopt_pysam_vn/integration/settlement.py` - `compute_hourly_settlement` (lines 65, 274).
- `src/python/reopt_pysam_vn/pysam/single_owner.py` - `run_single_owner_model` (line 141).
- `src/python/reopt_pysam_vn/integration/strike_search.py` - `sweep_strike_prices` (line 44).
- `src/python/reopt_pysam_vn/integration/matching.py` - `physical_fit_from_profile` (line 183).
- `reports/ceba_dppa_2026_repo_check.json` - results artifact.

**Dependencies**
- PHASE-01 registry; `.venv` for PySAM-backed checks (CON-001).

**Exit Criteria**
- [ ] `.venv/Scripts/python.exe scripts/python/integration/verify_ceba_dppa_deck.py` runs to
      completion and writes the JSON with a filled `verdict` for every non-gap check.
- [ ] The Slide 12 five-line totals reproduce to the deck's exact VND figures (within rounding)
      and the k×Kpp structural delta is recorded explicitly.

**Phase Risks**
- **RISK-02-01:** PySAM IRR returns null when cashflow never turns positive (documented in
  `single_owner.py`). Mitigation: treat `None` IRR as a reportable verdict, not a crash.
- **RISK-02-02:** Case 5/6 numbers won't match exactly (undisclosed inputs). Mitigation: DEC-007
  method+directional — assert the *relationship*, list assumed inputs, never force ❌.

### PHASE-03 - Synthesize Delta Report
**Goal**
Turn the results JSON into a colleague-readable `reports/` markdown: a verdict summary table
plus per-slide detail, mirroring the structure of the existing `ceba_*` reports at repo root.

**Tasks**
- [ ] TASK-03-01: Implement a `--report` mode (or sibling function) that reads the JSON and
      writes `reports/ceba_dppa_2026_repo_check.md` with: header counts (✅/⚠️/❌/➖), a
      bucket-grouped table (slide, claim, deck, repo, delta, verdict), and a "Structural
      reconciliations" section calling out k×Kpp and the TOU window.
- [ ] TASK-03-02: Include a "Known gaps" section listing the `➖` rows so reviewers see coverage
      boundaries (DEC-006).

**Files / Surfaces**
- `reports/ceba_dppa_2026_repo_check.md` - new human-readable report.
- `ceba_delta_report.md`, `ceba_repo_test_results.md` - prior reports to mirror tone/format only.

**Dependencies**
- PHASE-02 JSON.

**Exit Criteria**
- [ ] The markdown renders a complete verdict table and the counts equal the JSON's check count.

**Phase Risks**
- **RISK-03-01:** Report drifts from JSON if hand-edited. Mitigation: generate it from the JSON,
  never hand-author numbers.

### PHASE-04 - Inject `[Repo check]` Notes into a Deck Copy
**Goal**
Write a structured per-slide note into a copy of the pptx, idempotently, from the same results JSON.

**Tasks**
- [ ] TASK-04-01: Implement `scripts/python/integration/ceba_deck/inject_repo_notes.py` that
      copies `ceba-review/CEBA DPPA 2026.pptx` → `ceba-review/CEBA DPPA 2026 [repo-checked].pptx`
      and opens the copy with `python-pptx`.
- [ ] TASK-04-02: For each slide with checks, build a structured `[Repo check]` block per
      DEC-003: verdict icon, deck value, repo value, % delta, `repo_fn` + `file:line`, one-line
      takeaway, and (Case 5/6) the assumed-inputs line.
- [ ] TASK-04-03: Write into `slide.notes_slide.notes_text_frame`, idempotently — detect a
      delimiter (e.g. `=== [Repo check] (generated) ===`) and replace everything below it,
      preserving any author notes above (CON-003).
- [ ] TASK-04-04: Add `known_gap` notes to the two-part-tariff / RECs / GHG slides (DEC-006).
- [ ] TASK-04-05: Save the copy; never touch the source or the `~$` lock file (CON-002).

**Files / Surfaces**
- `scripts/python/integration/ceba_deck/inject_repo_notes.py` - new injector.
- `ceba-review/CEBA DPPA 2026 [repo-checked].pptx` - generated output (untracked, DEC-009).

**Dependencies**
- PHASE-02 JSON; `python-pptx` (in `.venv`).

**Exit Criteria**
- [ ] Re-running the injector twice yields a byte-stable notes payload (idempotent), verified by
      re-reading notes of Slides 12, 24, 26.
- [ ] The original `.pptx` mtime is unchanged after a run.

**Phase Risks**
- **RISK-04-01:** Deck open in PowerPoint locks the copy target. Mitigation: write to a temp file
  then move; fail loudly if the source lock file implies the copy is also open.

### PHASE-05 - End-to-End Run, Verify, Commit & Push
**Goal**
Execute the full pipeline in `.venv`, sanity-check outputs, then commit the script + reports and
push to `main` per DEC-009 (annotated pptx left untracked).

**Tasks**
- [ ] TASK-05-01: Run `verify_ceba_dppa_deck.py` then `inject_repo_notes.py` end-to-end in
      `.venv`; confirm JSON, markdown, and `[repo-checked].pptx` are produced.
- [ ] TASK-05-02: Spot-check three notes (Slide 12 five-line ✅, Slide 9/11 k×Kpp ⚠️ reconcile,
      Slide 26 empty-window method-consistent) open correctly in the Notes pane.
- [ ] TASK-05-03: `git add` only the tracked deliverables — `scripts/python/integration/ceba_deck/`,
      `scripts/python/integration/verify_ceba_dppa_deck.py`, `reports/ceba_dppa_2026_repo_check.*`,
      `research/2026-06-23_*.md`, `plans/2026-06-23-*.md`. Confirm `git status` shows **no** pptx
      staged (DEC-009, CON-002).
- [ ] TASK-05-04: Commit with a descriptive message and `git push origin main`.

**Files / Surfaces**
- `.gitignore` - inspect to confirm `ceba-review/*.pptx` stays untracked (add a rule if needed).

**Dependencies**
- PHASE-03, PHASE-04.

**Exit Criteria**
- [ ] `git status` is clean of the large pptx; the script + reports + plan + brainstorm are on
      `main` and pushed.

**Phase Risks**
- **RISK-05-01:** Accidentally staging the 13 MB pptx. Mitigation: explicit per-path `git add`,
  plus a `.gitignore` guard; never `git add -A`.

## Verification Strategy
- **TEST-001:** `.venv/Scripts/python.exe scripts/python/integration/verify_ceba_dppa_deck.py` —
  produces the JSON with a verdict for every check; non-zero exit on any unhandled exception.
- **TEST-002:** Optional pytest under `tests/python/integration/` asserting the Slide-12 five-line
  totals reproduce exactly and that `classify()` applies the ±1% rule + citation rule correctly.
- **MANUAL-001:** Open `[repo-checked].pptx` in PowerPoint; confirm Notes pane on Slides 12, 24,
  26 shows a clean structured `[Repo check]` block.
- **MANUAL-002:** Run the injector twice; diff the notes payload to confirm idempotency.
- **OBS-001:** `git status` post-commit shows no `.pptx` tracked and the push to `main` succeeded.

## Risks and Alternatives
- **RISK-001:** Repo's hourly FMP/CFMP and solar series are proxies, so Case 5/6 / sweep figures
  are directional. Mitigation: DEC-007 — verdicts say "method-consistent," assumptions stated in
  every relevant note; never presented as bankable.
- **RISK-002:** python-pptx notes-slide creation on slides that lack a notes slide. Mitigation:
  `slide.notes_slide` lazily creates one; confirm on a slide with no prior notes.
- **ALT-001:** Native PowerPoint threaded comments — rejected (DEC-002): weak python-pptx support,
  XML-corruption risk on a 13 MB deck.
- **ALT-002:** Standalone review memo only — rejected: goal is notes *in the deck*; the `reports/`
  markdown is kept as the provenance trail, not the deliverable.

## Grill Me
No open clarification questions. All nine design decisions were resolved in the brainstorm
(`research/2026-06-23_ceba-deck-repo-verification-brainstorm.md`, DEC-001..DEC-009).

## Suggested Next Step
Begin implementation at PHASE-01 (build `deck_checks.py`), then proceed phase by phase; the
brainstorm leaves nothing further to clarify before coding.
