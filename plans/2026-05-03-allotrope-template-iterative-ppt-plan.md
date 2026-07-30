---
title: "Iterative Allotrope-Template PPT Generation From Recent Final Reports"
date: "2026-05-03"
status: "complete — all 5 phases shipped: rubric + 3 decks under reports/decks/, 3 conformance files, trajectory summary, final report reports/2026-05-06-final-allotrope-template.html (commit 267cf21)"
request: "Multi-phase plan: use the present skill to generate ppts for the 3 most recent final reports in sequence; after each ppt, compare against the Allotrope presentation template fetched via the drive skill; feed deltas forward so each next ppt better matches the Allotrope template."
plan_type: "multi-phase"
research_inputs:
  - "none-applicable"
---

# Plan: Iterative Allotrope-Template PPT Generation From Recent Final Reports

## Objective
Generate three PowerPoint decks from the three most recent `*-final.html` reports under `reports/`, comparing each against the Allotrope presentation template (fetched from Google Drive) and feeding the conformance deltas forward so each successive deck matches the Allotrope template more closely than the prior one. The output is three decks plus a written conformance trajectory showing measurable convergence to the template.

## Context Snapshot
- **Current state:** `reports/` contains four `*-final.html` files. The three most recent (by file date) are the natural "most recent 3 final reports": `2026-04-09-dppa-case-1-final.html`, `2026-04-16-dppa-case-2-final.html`, `2026-04-21-dppa-case-3-final.html`. No PPTs have been generated from them. The Allotrope deck template lives on Google Drive (location to confirm in Grill Me Q-001).
- **Desired state:** Three `.pptx` files saved under `reports/decks/` (created), each with an accompanying `*-conformance.md` delta against the Allotrope template, plus a final `2026-05-03-allotrope-conformance-trajectory.md` summary showing how lessons compounded across iterations.
- **Key repo surfaces:**
  - `reports/2026-04-09-dppa-case-1-final.html`
  - `reports/2026-04-16-dppa-case-2-final.html`
  - `reports/2026-04-21-dppa-case-3-final.html`
  - `plans/` (this plan)
  - new: `reports/decks/` (deck artifacts)
  - new: `reports/decks/conformance/` (delta + trajectory notes)
- **Out of scope:** Editing the source HTML reports, regenerating model outputs, modifying the Allotrope brand template itself, automating Drive uploads of the resulting decks (decks stay local unless the user says otherwise), and producing decks for non-final reports or phase reports.

## Research Inputs
- No applicable research briefs were found in `research/`. The four briefs there cover Vietnam DPPA / TOU / commercial product topics — useful as report content background but not relevant to template-conformance methodology.

## Assumptions and Constraints
- **ASM-001:** "3 most recent final reports" means the three distinct `*-final.html` files with the latest modification dates (case-1 Apr 9, case-2 Apr 16 superseding Apr 15, case-3 Apr 21). The earlier `2026-04-15-dppa-case-2-final.html` is treated as a superseded draft and excluded.
- **ASM-002:** "present skill" refers to the listed `present:present` skill (".../create a presentation"), invoked once per report to produce a `.pptx`.
- **ASM-003:** "drive skill" refers to the connected Google Drive MCP / connector in this environment. If no Drive MCP is connected at execution time, the executor pauses and prompts the user to connect one rather than scraping or guessing template content.
- **ASM-004:** Iteration order is chronological (case-1 → case-2 → case-3), so the most recent report receives the most accumulated template-conformance feedback.
- **CON-001:** The Allotrope template is treated as authoritative; conformance changes only deck structure/visuals, never the underlying analytical claims from the source reports.
- **CON-002:** Decks must merge cleanly to `main` — work happens on the current branch and lands as one PR. No long-lived feature branch.
- **DEC-001:** Three iterations only (one per report). No re-generation of earlier decks after later lessons land; the trajectory document captures what a re-run would change.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Locate inputs, fetch Allotrope template, define rubric | None | `reports/decks/conformance/allotrope-template-rubric.md`, cached template artifact |
| PHASE-02 | Generate Deck 1 (case-1) and capture deltas | PHASE-01 | `reports/decks/2026-04-09-dppa-case-1.pptx`, `…-case-1-conformance.md` |
| PHASE-03 | Generate Deck 2 (case-2) applying Deck 1 lessons | PHASE-02 | `…-case-2.pptx`, `…-case-2-conformance.md` |
| PHASE-04 | Generate Deck 3 (case-3) applying cumulative lessons | PHASE-03 | `…-case-3.pptx`, `…-case-3-conformance.md` |
| PHASE-05 | Conformance trajectory summary + commit | PHASE-04 | `2026-05-03-allotrope-conformance-trajectory.md`, single PR-ready commit |

## Detailed Phases

### PHASE-01 - Inputs, Template Fetch, Rubric
**Goal**
Lock the three input reports, retrieve the Allotrope presentation template from Drive, and convert it into a written conformance rubric that can be applied identically across all three iterations.

**Tasks**
- [x] TASK-01-01: Confirm the three target inputs are exactly: `reports/2026-04-09-dppa-case-1-final.html`, `reports/2026-04-16-dppa-case-2-final.html`, `reports/2026-04-21-dppa-case-3-final.html`. Skip `2026-04-15-dppa-case-2-final.html` as superseded.
- [x] TASK-01-02: Use the `drive` (Google Drive) skill/connector to locate the Allotrope deck template (see Grill Me Q-001 for path). Cache it locally as `reports/decks/conformance/_template/allotrope-template.pptx` (do not commit binary if repo policy forbids — see Q-002).
- [x] TASK-01-03: Extract the rubric from the template into `reports/decks/conformance/allotrope-template-rubric.md` covering: cover slide layout, section dividers, color palette + hex values, typography (font families, sizes per role), required slide types and order (e.g., Executive Summary → Context → Approach → Findings → Recommendation → Appendix), chart styling conventions, footer/page-number style, and logo placement.
- [x] TASK-01-04: Define a 0–5 scoring scale per rubric dimension and a results format that each conformance file will reuse verbatim.
- [x] TASK-01-05: Create `reports/decks/` and `reports/decks/conformance/` directories.

**Files / Surfaces**
- `reports/decks/conformance/allotrope-template-rubric.md` — new
- `reports/decks/conformance/_template/` — new, cached template
- `reports/2026-04-*-final.html` — read-only inputs

**Dependencies**
- Working Google Drive connector with read access to the Allotrope template.

**Exit Criteria**
- [ ] Rubric file exists and lists every dimension with its 0–5 scoring anchor.
- [ ] Template artifact is locally accessible to the present skill in later phases.
- [ ] Three input HTML paths are written into the rubric file's "Targets" section.

**Phase Risks**
- **RISK-01-01:** Drive connector not configured in this session. Mitigation: pause and prompt the user to run `/discord:configure`-style setup or attach the template file directly via Read.
- **RISK-01-02:** Template uses raster-only assets that the rubric cannot describe textually. Mitigation: include screenshot crops in `_template/` and reference them by filename in the rubric.

### PHASE-02 - Deck 1 (case-1) + Initial Conformance
**Goal**
Produce the first deck with the present skill using only the rubric (no prior iteration lessons yet), then score it.

**Tasks**
- [x] TASK-02-01: Invoke the `present:present` skill against `reports/2026-04-09-dppa-case-1-final.html`, instructing it to follow the rubric in `reports/decks/conformance/allotrope-template-rubric.md`. Save output as `reports/decks/2026-04-09-dppa-case-1.pptx`.
- [x] TASK-02-02: Manually open or programmatically inspect the deck slide-by-slide. Score each rubric dimension 0–5.
- [x] TASK-02-03: Write `reports/decks/conformance/2026-04-09-dppa-case-1-conformance.md` containing: per-dimension scores, total, top 5 deviations from template, explicit "lessons to carry forward" list (concrete, prescriptive — e.g., "Use #0B2A4A for section dividers, not slate gray").
- [x] TASK-02-04: Compute the aggregate conformance score and record it as the Deck 1 baseline.

**Files / Surfaces**
- `reports/decks/2026-04-09-dppa-case-1.pptx` — new
- `reports/decks/conformance/2026-04-09-dppa-case-1-conformance.md` — new

**Dependencies**
- PHASE-01 rubric.

**Exit Criteria**
- [ ] Deck 1 `.pptx` opens without errors.
- [ ] Conformance file lists numeric scores for every rubric dimension.
- [ ] "Lessons to carry forward" section contains ≥3 prescriptive, deck-actionable items.

**Phase Risks**
- **RISK-02-01:** Present skill ignores rubric specifics it cannot encode (e.g., exact hex). Mitigation: post-process the .pptx with a small `python-pptx` script if the gap is mechanical.

### PHASE-03 - Deck 2 (case-2) Applying Deck 1 Lessons
**Goal**
Produce the second deck consuming the rubric *plus* Deck 1's "lessons to carry forward", and verify measurable improvement.

**Tasks**
- [x] TASK-03-01: Build the present-skill prompt by concatenating the rubric + Deck 1's lessons-to-carry-forward block, then run against `reports/2026-04-16-dppa-case-2-final.html`. Output: `reports/decks/2026-04-16-dppa-case-2.pptx`.
- [x] TASK-03-02: Score Deck 2 with the identical rubric. Write `reports/decks/conformance/2026-04-16-dppa-case-2-conformance.md`.
- [x] TASK-03-03: Diff Deck 2 scores against Deck 1. Record per-dimension delta and overall delta.
- [x] TASK-03-04: Update "lessons to carry forward" — keep unresolved Deck 1 items, add new Deck 2 deviations, drop items that are now resolved.

**Files / Surfaces**
- `reports/decks/2026-04-16-dppa-case-2.pptx` — new
- `reports/decks/conformance/2026-04-16-dppa-case-2-conformance.md` — new

**Dependencies**
- PHASE-02 lessons file.

**Exit Criteria**
- [ ] Deck 2 conformance score ≥ Deck 1 score on aggregate (target: improvement on at least 2 dimensions where Deck 1 scored ≤3).
- [ ] If aggregate score regresses, the conformance file documents why and proposes a corrective action for Deck 3.

**Phase Risks**
- **RISK-03-01:** Carrying forward too many lessons makes the prompt overflow or confuses the present skill. Mitigation: cap carry-forward at top 7 items by impact.

### PHASE-04 - Deck 3 (case-3) Applying Cumulative Lessons
**Goal**
Produce the third deck with cumulative lessons from Decks 1+2 and confirm the iteration has converged toward the template.

**Tasks**
- [x] TASK-04-01: Build the prompt with rubric + cumulative lessons (Deck 1 unresolved + Deck 2 lessons). Run against `reports/2026-04-21-dppa-case-3-final.html`. Output: `reports/decks/2026-04-21-dppa-case-3.pptx`.
- [x] TASK-04-02: Score Deck 3 with the same rubric. Write `reports/decks/conformance/2026-04-21-dppa-case-3-conformance.md`.
- [x] TASK-04-03: Tag any remaining template gaps as "would require manual touchup" vs "addressable by a future rubric edit".

**Files / Surfaces**
- `reports/decks/2026-04-21-dppa-case-3.pptx` — new
- `reports/decks/conformance/2026-04-21-dppa-case-3-conformance.md` — new

**Dependencies**
- PHASE-03 cumulative lessons.

**Exit Criteria**
- [ ] Deck 3 aggregate conformance score is the highest of the three decks, OR the conformance file explains the specific blocker preventing further gain.
- [ ] No rubric dimension scores below the corresponding Deck 2 value without an explicit explanation.

**Phase Risks**
- **RISK-04-01:** Source report content (case-3) is structurally different and resists the template's slide ordering. Mitigation: document the structural mismatch rather than forcing a misleading slide order.

### PHASE-05 - Trajectory Summary and Merge
**Goal**
Produce the cross-iteration synthesis and land everything as one clean commit on `main` (per user direction that future changes merge to main).

**Tasks**
- [x] TASK-05-01: Write `reports/decks/conformance/2026-05-03-allotrope-conformance-trajectory.md` containing: scores table (rows = decks, cols = rubric dimensions + total), narrative of which lessons stuck and which kept reappearing, and recommended template/rubric edits if the rubric itself proved incomplete.
- [x] TASK-05-02: Confirm the working tree builds a clean commit (no `tmp_phase3/`, no `nul`, no cached template binary if Q-002 says exclude).
- [x] TASK-05-03: Stage only the deck + conformance artifacts and the trajectory file. Open a PR to `main` summarizing the iteration arc and the final deck quality.

**Files / Surfaces**
- `reports/decks/conformance/2026-05-03-allotrope-conformance-trajectory.md` — new
- `.gitignore` — possibly amended to exclude `_template/` if Q-002 = exclude
- PR description on `main`

**Dependencies**
- PHASES 02–04 completed.

**Exit Criteria**
- [ ] Trajectory file shows a 3-row scores table and a clear improvement story (or a documented plateau).
- [ ] `git status` is clean except for intended artifacts.
- [ ] PR opened against `main`.

**Phase Risks**
- **RISK-05-01:** Committing the cached Allotrope template `.pptx` could leak proprietary brand assets. Mitigation: gitignore `_template/` by default; only commit if Q-002 explicitly allows.

## Verification Strategy
- **TEST-001:** For each `.pptx`, run a `python-pptx` smoke check that loads the file and reports slide count and slide titles, ensuring the file isn't corrupt.
- **TEST-002:** Lint each `*-conformance.md` to confirm it has a scores table with all rubric dimensions filled (no blank cells).
- **MANUAL-001:** Visually open each deck in PowerPoint or LibreOffice Impress and confirm cover slide, section dividers, and the recommendation slide use the template's color palette and typography.
- **MANUAL-002:** Spot-check that no analytical numbers from the source HTML reports were altered, dropped, or invented in the deck.
- **OBS-001:** Track the aggregate conformance score per deck. Convergence criterion: Deck 3 ≥ Deck 2 ≥ Deck 1 on aggregate, with at least one dimension reaching 5/5 by Deck 3.

## Risks and Alternatives
- **RISK-001:** The present skill may not expose enough styling control to hit pixel-level template parity, leaving a permanent gap. Mitigation: a thin `python-pptx` post-processor handles deterministic fixes (colors, fonts, footer text) after the skill produces the deck.
- **RISK-002:** Drive access flakiness mid-run could force a partial result. Mitigation: PHASE-01 caches the template locally so PHASES 02–04 don't re-hit Drive.
- **ALT-001:** Generate all three decks in parallel from the same rubric, then pick the best. Rejected — it removes the iteration-feedback loop the user explicitly asked for.
- **ALT-002:** Skip the rubric and feed the raw `.pptx` template to the present skill each time. Rejected — without an explicit rubric the conformance scoring is subjective and the trajectory cannot be measured.

## Grill Me
No open clarification questions. Resolutions captured below (recorded 2026-05-04):

- **Q-001 → RESOLVED:** Allotrope template is the most-recent Google Slides deck at https://docs.google.com/presentation/d/1E0HTpklTMu8fjiZCVi_7Ka41WcKqfAMgt6PSN8Qcrtw/edit?usp=drivesdk. PHASE-01 fetches this exact deck via the drive skill (export to `.pptx` for python-pptx parsing) and caches it under `reports/decks/conformance/_template/allotrope-template.pptx`.
- **Q-002 → DEFAULT:** Gitignore `_template/` cache; commit generated decks under `reports/decks/` plus all conformance + trajectory markdown.
- **Q-003 → DEFAULT:** Inputs are the three latest distinct-case finals: `2026-04-09-dppa-case-1-final.html`, `2026-04-16-dppa-case-2-final.html`, `2026-04-21-dppa-case-3-final.html`. `2026-04-15-dppa-case-2-final.html` is excluded as superseded.
- **Q-004 → DEFAULT:** Local-only. No Drive upload of generated decks in this plan; revisit as a follow-up if needed.

## Suggested Next Step
Begin PHASE-01: fetch the Allotrope template from the resolved Drive link, cache it, and write the conformance rubric.
