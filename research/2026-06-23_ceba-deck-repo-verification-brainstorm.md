---
title: "CEBA DPPA 2026 Deck — Repo Verification & In-Deck Review Notes"
date: "2026-06-23"
type: "brainstorm"
depth: "standard"
source_request: "given findings i want to execute testables with current repo and ultimately insert comments into the deck for colleagues to review"
slug: "ceba-deck-repo-verification"
---

# Brainstorm: CEBA DPPA 2026 Deck — Repo Verification & In-Deck Review Notes

## Problem & Why Now
`ceba-review/CEBA DPPA 2026.pptx` ("Session 5.2: Off-Site Solutions Deep Dive — Vietnam's
DPPA Pricing Considerations," Cong Nguyen, 57 slides) is going to colleagues and a CEBA
workshop audience. It makes ~20 quantitative claims — the five-line bill, CfD math, the
buyer/seller/lender three-gate framework, Case Studies 5 & 6 (Solar + Large/Min BESS), a
56-scenario "empty window" strike sweep, and five worked workshop settlement scenarios.

A prior mapping (this session) showed the repo (`reopt_pysam_vn`) can reproduce most of
those numbers with real functions. The work now is to **actually execute** those testables
against the current repo and **write the results back into the deck as per-slide review
notes**, so colleagues review against repo-computed figures instead of unverified slide
numbers — before the deck is presented. The repo is also where Vietnam tariff/financial
reference data lives, so it is the natural authority for catching dated or off figures
(e.g. the TOU peak window).

## Current vs Desired State
- **Current state:** The 2026 deck is unverified. The repo holds the settlement engine,
  PySAM developer-finance model, strike sweep, matching engine, and sourced Vietnam data —
  but nothing has been run against this specific deck, and the deck carries no review notes.
  Prior reports (`ceba_delta_report.md`, `ceba_repo_test_results.md`,
  `ceba_slide_review_report.md`) targeted the **older Session 6.2** deck, not this one.
- **Desired state:** A committed, rerunnable verification script computes every A/B/C
  testable; a results artifact (JSON + summary markdown) records deck-vs-repo deltas; and a
  **copy** of the pptx carries a structured `[Repo check]` note in the speaker-notes pane of
  each quantitative slide (plus short "known gap" notes on relevant-but-unmodeled slides).
- **Key repo surfaces:**
  - `src/python/reopt_pysam_vn/integration/settlement.py` — `compute_hourly_settlement`,
    `compute_buyer_benchmark`, `run_strike_sweep` (five-line bill, CfD, blended cost).
  - `src/python/reopt_pysam_vn/pysam/single_owner.py` + `pysam/metrics.py` —
    `run_single_owner_model`, `extract_single_owner_outputs` (IRR, NPV, **min_dscr**, debt).
  - `src/python/reopt_pysam_vn/integration/strike_search.py` — `sweep_strike_prices`
    (minimum strike clearing a target IRR).
  - `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` — `build_samsung_ttc_strike_sweep`,
    `build_samsung_ttc_combined_decision` (buyer+seller gate overlap, "empty window").
  - `src/python/reopt_pysam_vn/integration/matching.py` — `match_projects_to_factory`,
    `physical_fit_from_profile` (8760 load-shape overlap).
  - `src/python/reopt_pysam_vn/analysis/onsite.py` / `offsite_dppa.py` — `run_onsite`,
    `run_offsite_dppa` (DealConfig front doors).
  - Data: `data/vietnam/vn_tariff_2025.json` (TOU per Decision 963/QD-BCT, avg 2204.0655,
    523-ish fees), `vn_financial_defaults_2025.json` (CIT 20%/10%, 4+9 holiday, escalation),
    `vn_deal_defaults_2026.json` (70% debt / 8.5% / 10yr, strike & FMP sweep ranges).
  - `.venv` (Python 3.12) — the **only** environment with PySAM installed.

## Resolved Decisions
- **DEC-001:** Execute **all** mapped testables (buckets A/B/C exhaustively), not a subset —
  the deck is going to external review, so completeness beats speed.
- **DEC-002:** Deliver comments as **per-slide speaker notes** via python-pptx, written to a
  **copy** of the pptx (original untouched). Reliable and non-destructive; avoids fragile
  native-comment XML.
- **DEC-003:** Each `[Repo check]` note is a **structured verdict block** per claim — verdict
  icon (✅ match / ⚠️ reconcile / ❌ mismatch / ➖ no coverage), deck value, repo-computed
  value, % delta, the repo function + `file:line` that produced it, and a one-line takeaway.
- **DEC-004:** Match rule = **±1% → ✅ match; beyond → ⚠️/❌ flag**, and where the gap is a
  known model-structure choice (k×Kpp collapsed to one factor; TOU window definition), name
  the structural reason rather than just flagging a number.
- **DEC-005:** Compute non-out-of-box items (Case 5/6, escalation horizon crossover,
  load-shape overlap) via a **committed reproducible script** under `scripts/python/` that
  calls the real functions directly and dumps a results JSON the note generator consumes.
- **DEC-006:** Annotate **quantitative slides + flagged known gaps** — note every slide with a
  repo-testable number, plus a short "➖ out of repo scope / known gap" note on the few
  relevant-but-unmodeled slides (two-part tariff / Decree 146, RECs/EACs, GHG scopes).
- **DEC-007:** For Case 5/6 and the 56-scenario sweep (undisclosed inputs), verify
  **method + direction with assumptions stated** — reproduce the relationship the slide
  teaches (oversized BESS → min DSCR < 1.20×; buyer flips positive exactly as lender drops
  out) using repo defaults + the deck's stated inputs; verdict is "method-consistent" or not,
  and the note lists which inputs were assumed.
- **DEC-008:** *(resolves Q-001)* **Respect the deck's citation.** Where a slide cites a
  source for a value that diverges from repo data (e.g. Slide 11 "EAVCED public training";
  TOU window; FMP; 360 + 163.3 fee split), the value is **not** marked ❌ mismatch — it reads
  ⚠️ reconcile with both sides shown (deck value + its cited source vs repo value + its
  sourced data file) and a "verify which basis applies" takeaway. Repo data is *a* reference,
  not an override, when the deck has a citation. Uncited divergent numbers can still be ❌.
- **DEC-009:** *(resolves Q-002)* **Default provenance handling.** Commit the verification
  script + `reports/` JSON/markdown to git; leave the large `[repo-checked].pptx` **untracked**
  (consistent with the other untracked decks in `ceba-review/`) for colleague hand-off.

## Assumptions & Constraints
- **ASM-001:** The repo's sourced Vietnam data (TOU per Decision 963/QD-BCT eff. 2026-04-22,
  avg retail 2204.0655, fees 523.34, exchange 26,400 VND/USD) is *a* reference, not an
  override. Per DEC-008, where the deck **cites** a diverging value (peak 18:00–23:00 vs repo
  evening-only 17:30–22:30; k×Kpp; FMP), the note shows both bases as ⚠️ reconcile and asks
  colleagues to confirm which applies — it never silently "corrects" a cited slide.
- **ASM-002:** The k (1.026) × Kpp (1.008) = ~1.034 market-energy multiplier in the deck vs
  the engine's single `kpp_factor` (~1.0273) is the most likely real discrepancy and is the
  prime reconciliation target.
- **ASM-003:** Output copy named e.g. `ceba-review/CEBA DPPA 2026 [repo-checked].pptx`;
  results under `reports/` (JSON + summary markdown); script under
  `scripts/python/integration/`.
- **CON-001:** All PySAM-dependent runs (IRR/NPV/DSCR, strike-IRR sweep) **must** use `.venv`
  (Python 3.12); system Python has no PySAM wheel. Settlement/matching math is pure-Python and
  runs anywhere, but standardize on `.venv` for one command path. *(see [[pysam-venv-environment]])*
- **CON-002:** The original `.pptx` is never modified in place; there is also a `~$...pptx`
  lock file present (deck open in PowerPoint), so write the copy, don't touch the source.
- **CON-003:** Notes must round-trip safely — preserve existing notes-slide content if any,
  and re-run idempotently (replace a prior `[Repo check]` block rather than stacking).

## Approaches Considered
- **Chosen:** Reproducible script computes all A/B/C testables → results JSON → python-pptx
  note injector writes a structured `[Repo check]` block into a deck copy's speaker notes,
  plus a `reports/` summary markdown. Real functions, idempotent, colleague-rerunnable.
- **ALT-001:** Native PowerPoint threaded comments — rejected (DEC-002): python-pptx 1.0.2
  lacks robust modern-comment support; raw XML injection risks corrupting a 13 MB deck.
- **ALT-002:** Standalone companion review memo only, pptx untouched — rejected: the explicit
  goal is notes *in the deck* for in-context review (kept the `reports/` markdown as the
  provenance trail, not as the deliverable).
- **ALT-003:** Build full registered Case 5/6 orchestrators in `offsite_dppa` — rejected
  (DEC-005/DEC-007): turns a review task into a feature build; direct function calls suffice
  for method-level verification.

## Out of Scope
- Reproducing Case 5/6 **exact** figures by back-solving undisclosed CAPEX/sizing/FMP (DEC-007
  is method+directional only).
- Modeling the Decree 146 two-part tariff buyer P&L (data exists in the regime registry; no
  buyer-side model wired) — flagged as a known gap, not built.
- RECs/EACs attribute economics and GHG Scope 1/2/3 accounting (Slides 53, 55) — qualitative,
  no repo coverage.
- Editing slide *content* (text/figures); we only add notes. Any suggested figure change lives
  inside the note's takeaway line, not as an applied edit.
- Re-verifying the older Session 6.2 deck (already covered by prior `ceba_*` reports).

## Open Questions
None. (Q-001 → DEC-008: respect the deck's citation, ⚠️ reconcile not ❌. Q-002 → DEC-009:
commit script + `reports/`, leave the annotated pptx untracked.)

## Suggested Next Step
Run `/plan ceba-deck-repo-verification` to turn this into a multi-phase implementation plan.
