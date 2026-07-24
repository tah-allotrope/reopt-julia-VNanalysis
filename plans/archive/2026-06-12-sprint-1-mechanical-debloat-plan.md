---
title: "Sprint 1 — Mechanical De-bloat (untrack generated artifacts, remove dead/foreign dirs, stray files)"
date: "2026-06-12"
status: "complete"
request: "Plan Sprint 1 from the repo-trim gap analysis: GAP-02 untrack ~250 generated artifacts, GAP-04 remove foreign/dead dirs, GAP-09 stray files."
plan_type: "multi-phase"
research_inputs:
  - "reports/2026-06-12-reopt-pysam-vietnam-repo-trim-gap-analysis.md"
---

# Plan: Sprint 1 — Mechanical De-bloat

## Objective
Shrink the tracked tree from 631 files (~190 MB working set) to its actual source + data + tests by untracking regenerable outputs and deleting dead/foreign directories — with **zero behavior change** to the REopt/PySAM pipeline. This is the highest signal-to-noise, lowest-risk step and unblocks Sprints 2–3 by making the real surfaces visible.

## Context Snapshot
- **Current state:** `artifacts/` (62 MB, 152 files), `reports/` (76 tracked `.html` + 4 `.pptx` + stray `.html.txt`), `scenarios/generated/`, `archive/colab/` (19 MB), `present/` (16 MB), `.opencode/` + `.opencode_http.log`, `ninhsim-report-review-fixed.png`, `legacy/`, and `tests/.stdout.tmp` are all tracked. Report-generation scripts under `scripts/python/integration/` **write into** `artifacts/`/`reports/` at runtime (284 path references across `src/`+`scripts/`+`tests/`), so these directories must remain writable on disk.
- **Desired state:** Generated outputs are git-ignored but still writable locally; 2–3 golden runs preserved under a tracked `examples/`; dead/foreign dirs deleted; `.gitignore` extended; test suite still green.
- **Key repo surfaces:** `.gitignore`, `artifacts/`, `reports/`, `scenarios/generated/`, `archive/`, `present/`, `.opencode/`, `legacy/`, `tests/baselines/` (must stay tracked), `tests/run_all_tests.ps1`.
- **Out of scope:** Removing shim layers (Sprint 2 / GAP-03), relocating heavy binaries (Sprint 2 / GAP-05), any source/logic refactor (Sprint 3 / GAP-01).

## Research Inputs
- `reports/2026-06-12-reopt-pysam-vietnam-repo-trim-gap-analysis.md` — defines GAP-02/04/09, the sprint sequencing, and the risk that untracking `artifacts/` could break scripts that read from it (mitigated here by `--cached`-only untracking + golden `examples/`).
- `legacy/README.md` — documents canonical output paths (`artifacts/results/`, `artifacts/reports/`); confirms nothing is lost by untracking those trees.

## Assumptions and Constraints
- **ASM-001:** Everything under `artifacts/`, `reports/*.html`, `reports/decks/`, and `scenarios/generated/` is regenerable from tracked source + `data/` + `scenarios/`.
- **ASM-002:** `tests/baselines/*.json` are intentionally versioned regression baselines and MUST remain tracked.
- **CON-001:** Untracking must use `git rm -r --cached` (keep files on disk); a plain `rm -rf` would break the ~50 report scripts that write into `artifacts/`/`reports/`.
- **CON-002:** `archive/` has no inbound references from `src/`/`scripts/`/`tests/` (verified by grep) and can be fully deleted.
- **DEC-001:** Branch is `main`; user has authorized commit + push to `main` for this trim work.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Preserve golden examples before untracking | None | `examples/` with 2–3 canonical runs |
| PHASE-02 | Untrack regenerable outputs + extend `.gitignore` | PHASE-01 | Updated `.gitignore`, `git rm --cached` of `artifacts/`, `reports/*.html`, decks, `scenarios/generated/` |
| PHASE-03 | Delete dead/foreign dirs + stray files | None (parallel to 02) | Removal of `archive/`, `.opencode/`, `present/`, root png, `legacy/`, `tests/.stdout.tmp` |
| PHASE-04 | Verify + document | PHASE-02, PHASE-03 | Green test run, updated README/AGENTS notes, size report |

## Detailed Phases

### PHASE-01 - Preserve golden examples
**Goal**
Capture a small, representative set of canonical outputs in a tracked `examples/` directory so a fresh clone retains reference results after `artifacts/`/`reports/` are untracked.

**Tasks**
- [ ] TASK-01-01: Create `examples/` and copy 2–3 representative runs (recommend: one REopt solve `artifacts/results/saigon18/2026-03-23_scenario-a_fixed-sizing_evntou_reopt-results.json`, one DPPA settlement `artifacts/reports/samsung_ttc/2026-06-04_samsung-ttc_combined-decision.json`, one final HTML `reports/2026-06-04-final-samsung-ttc-dppa.html`).
- [ ] TASK-01-02: Add `examples/README.md` explaining these are frozen golden references, with the command that regenerates each.

**Files / Surfaces**
- `examples/` (new) — frozen golden references.
- `artifacts/results/...`, `artifacts/reports/...`, `reports/...` — copy sources.

**Dependencies**
- None.

**Exit Criteria**
- [ ] `examples/` contains 2–3 runs + a README; each entry names its regeneration command.

**Phase Risks**
- **RISK-01-01:** Picking outputs that drift from current code. Mitigation: pick the most recently generated case (Samsung-TTC, Jun 2026) whose scripts are current.

### PHASE-02 - Untrack regenerable outputs + extend `.gitignore`
**Goal**
Remove generated trees from git tracking while keeping them on disk, and codify the exclusion in `.gitignore`.

**Tasks**
- [ ] TASK-02-01: Append to `.gitignore`: `artifacts/`, `reports/*.html`, `reports/*.html.txt`, `reports/decks/`, `scenarios/generated/` — but explicitly NOT `tests/baselines/` and NOT `examples/`.
- [ ] TASK-02-02: `git rm -r --cached artifacts reports/decks scenarios/generated` and `git rm --cached reports/*.html reports/*.html.txt` (keeps files on disk).
- [ ] TASK-02-03: Re-add the tracked Markdown deliverables that live under `reports/` and should stay (e.g. `reports/*.md` review/readiness notes and the gap-analysis report) so only generated HTML/decks are dropped.
- [ ] TASK-02-04: `git status` review to confirm only deletions-from-index (not worktree) and that `tests/baselines/`, `reports/*.md`, `examples/` remain tracked.

**Files / Surfaces**
- `.gitignore` — add exclusions (already contains `**/reopt-results.json`, `artifacts/sysimage/`, `artifacts/reports/test_runs/*.html`; extend that pattern).
- `artifacts/`, `reports/`, `scenarios/generated/` — untracked from index, retained on disk.

**Dependencies**
- PHASE-01 (golden copies exist before the source trees are untracked).

**Exit Criteria**
- [ ] `git ls-files artifacts/ reports/ scenarios/generated/` returns only intended keepers (`reports/*.md`).
- [ ] `tests/baselines/` still fully tracked.
- [ ] Working tree on disk still contains the files (scripts can still write/read them locally).

**Phase Risks**
- **RISK-02-01:** Accidentally untracking `tests/baselines/` or `reports/*.md`. Mitigation: scoped `git rm` globs + explicit re-add; verify with `git ls-files`.

### PHASE-03 - Delete dead/foreign dirs + stray files
**Goal**
Remove material that is not part of the REopt+PySAM Vietnam analysis function.

**Tasks**
- [ ] TASK-03-01: Confirm no inbound refs, then `git rm -r archive/` (19 MB dead colab; grep showed zero references from `src/`/`scripts/`/`tests/`).
- [ ] TASK-03-02: `git rm -r --cached present/` + add `present/` to `.gitignore` (16 MB decks; regenerable via `/present`), and `git rm .opencode_http.log` + `git rm -r .opencode/` (foreign OpenCode tooling).
- [ ] TASK-03-03: `git rm ninhsim-report-review-fixed.png` (stray root screenshot) and `git rm tests/.stdout.tmp` (scratch); add `tests/.stdout.tmp` to `.gitignore`.
- [ ] TASK-03-04: Fold the still-useful path-map note from `legacy/README.md` into `docs/` if relevant, then `git rm -r legacy/`.
- [ ] TASK-03-05: Verify `NREL_API.env` remains untracked (already git-ignored via `*.env`); do not touch the on-disk secret.

**Files / Surfaces**
- `archive/`, `.opencode/`, `.opencode_http.log`, `present/`, `ninhsim-report-review-fixed.png`, `legacy/`, `tests/.stdout.tmp`, `.gitignore`.

**Dependencies**
- None (can run alongside PHASE-02).

**Exit Criteria**
- [ ] `git ls-files` no longer lists `archive/`, `.opencode/`, `legacy/`, the root png, or `tests/.stdout.tmp`.
- [ ] `present/` untracked but retained on disk.

**Phase Risks**
- **RISK-03-01:** `archive/` or `present/` referenced by an un-grepped doc/script. Mitigation: re-grep `archive/` and `present/` across all tracked files immediately before deletion; `present/` is only untracked (not deleted) so recoverable.

### PHASE-04 - Verify + document
**Goal**
Prove the pipeline is unaffected and record the new conventions.

**Tasks**
- [ ] TASK-04-01: Run `.\tests\run_all_tests.ps1 -SkipLayer4` (L1–L3) then `-SmokeOnly` (L4 no-solver); confirm green.
- [ ] TASK-04-02: Run one report script end-to-end (e.g. `python scripts/python/integration/generate_cross_project_dashboard.py`) to confirm it still writes into the now-untracked `artifacts/` on disk.
- [ ] TASK-04-03: Update `README.md` "Generated Outputs" + `AGENTS.md` to state that `artifacts/`/`reports/*.html`/`present/` are local-only and `examples/` holds golden references.
- [ ] TASK-04-04: Record before/after tracked-file count and repo size in the plan's results section.

**Files / Surfaces**
- `tests/run_all_tests.ps1`, `README.md`, `AGENTS.md`.

**Dependencies**
- PHASE-02, PHASE-03.

**Exit Criteria**
- [ ] L1–L3 + L4 smoke tests pass.
- [ ] A report script still produces output locally.
- [ ] Tracked file count materially reduced (target: < ~330 files) and documented.

**Phase Risks**
- **RISK-04-01:** A smoke test reads a now-untracked input it expected in git. Mitigation: smoke tests use `scenarios/templates/` + `data/` (tracked), not `artifacts/`; confirm during run.

## Verification Strategy
- **TEST-001:** `.\tests\run_all_tests.ps1 -SkipLayer4` and `.\tests\run_all_tests.ps1 -SmokeOnly` both green.
- **MANUAL-001:** Run one generator script; confirm fresh files appear under `artifacts/` on disk and are git-ignored (`git status` clean for them).
- **OBS-001:** `git ls-files | wc -l` before vs after; `du -sh` of tracked tree before vs after.

## Risks and Alternatives
- **RISK-001:** History still carries the large blobs, so clone size won't shrink until/unless history is rewritten. Mitigation: out of scope here; note for a possible future `git filter-repo` pass (see Sprint 2 GAP-05 discussion). Untracking still stops future growth and cleans the working view.
- **ALT-001:** Delete `artifacts/`/`reports/` from disk entirely instead of untracking. Rejected — ~50 scripts write there and several read prior outputs; deletion would break them and lose golden references.

## Grill Me
1. **Q-001:** Should `present/` and `reports/decks/*.pptx` be deleted from disk too, or only untracked (kept locally, git-ignored)?
   - **Recommended default:** Untrack only (keep on disk, git-ignore) — decks are regenerable but slow to rebuild.
   - **Why this matters:** Determines whether PHASE-03 uses `git rm` (delete) or `git rm --cached` (untrack) for decks.
   - **If answered differently:** "Delete" removes ~21 MB from disk immediately and drops the deck source entirely.
2. **Q-002:** Keep the 19 MB `archive/colab/` somewhere (separate archive repo / branch) before deleting, or drop it outright?
   - **Recommended default:** Drop outright — it's superseded colab scripts with no inbound references and git history retains it.
   - **Why this matters:** Adds an export step to PHASE-03 if preservation is required.
   - **If answered differently:** Add a TASK to push `archive/` to a `colab-archive` branch/repo before `git rm`.

## Suggested Next Step
Answer the two Grill Me questions, then execute PHASE-01 → PHASE-04. Commit as a single "chore: untrack generated artifacts + remove dead/foreign dirs" change and push to `main`.

---

## Review / Results (completed 2026-06-12)

**Outcome:** Executed across 4 phases, each committed + pushed to `main` with its own HTML report. Grill Me answers: Q-001 untrack-only for `present/`; Q-002 drop `archive/` outright.

| Phase | Commit | Tracked after | Notes |
|---|---|---|---|
| 01 Preserve golden examples | `b8f1e3d` | 640 | `examples/` + 3 golden runs + README |
| 02 Untrack regenerable outputs | `e947904` | 394 | 246 files `git rm --cached`; `.gitignore` extended with negations |
| 03 Remove dead/foreign dirs | `f1e76a3` | 368 | `archive/` dropped; `present/`+`.opencode/` untracked-on-disk; `legacy/README.md`→`docs/legacy-path-map.md` |
| 04 Verify + document | `938cb4b` | 371 | tests run; 1 regression fixed; README/AGENTS/lessons updated |

**Result:** Tracked files **635 → 371 (−42%)**; `artifacts/` (62 MB) regenerable and on disk. Pipeline behavior unchanged (verified: reopt 137 + ingestion/pysam 121 tests pass; dashboard script still writes to `artifacts/`).

**Deviations from plan (intentional):**
- `.opencode/` was untracked + git-ignored rather than deleted — it's the user's OpenCode skill bundle, treated like `.claude/`.
- Sprint reports under `reports/` kept tracked via naming-based `.gitignore` negations (plan assumed all `reports/*.html` ignored).

**Regression caught + fixed:** Deleting `archive/` broke `tests/python/reopt/test_api_result_sanitization.py`, which loaded `redact_sensitive_fields` from it via path segments (missed by a `grep "archive/"`). Fixed by relocating the function to `src/python/reopt_pysam_vn/reopt/sanitize.py` and repointing the test. Lesson recorded in `lessons.md`.

**Final synthesis:** `reports/2026-06-12-final-sprint-1-repo-trim.html`. **Next:** Sprint 2 (`plans/active/2026-06-12-sprint-2-shim-removal-binary-relocation-plan.md`).
