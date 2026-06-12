---
title: "Sprint 2 — Remove shadow shim layers, relocate heavy binaries, trim activeContext"
date: "2026-06-12"
status: "draft"
request: "Plan Sprint 2 from the repo-trim gap analysis: GAP-03 remove the two shadow shim layers, GAP-05 relocate heavy binaries, GAP-07 trim activeContext.md."
plan_type: "multi-phase"
research_inputs:
  - "reports/2026-06-12-reopt-pysam-vietnam-repo-trim-gap-analysis.md"
---

# Plan: Sprint 2 — Shim Removal, Binary Relocation, activeContext Trim

## Objective
Eliminate the duplicate-filename ambiguity that makes the tree hard to read (two shadow compatibility-shim layers), move multi-megabyte reference binaries out of normal git tracking, and shrink the 169 KB running log at repo root — leaving a single canonical source layout. Runs after Sprint 1 has cleared generated-output noise.

## Context Snapshot
- **Current state:**
  - `src/` root holds 3 dead shims: `src/REoptVietnam.jl` (6-line `include`), `src/__init__.py`, `src/reopt_vietnam.py` (re-exports `reopt_pysam_vn.reopt.preprocess`). **Verified:** no tracked `.py` imports them (the only `reopt_vietnam` hits in tests are docstring comments).
  - `scripts/python/` holds ~37 flat `*.py` files that are 5–9-line `runpy.run_path(...)` redirects into `scripts/python/integration/` or `scripts/python/reopt/`; 35 collide by name with their canonical targets. The only inbound references are in git-ignored `.claude/worktrees/`, `__pycache__/`, `activeContext.md` (a log), and archived plans/research — none in live tracked code.
  - Heavy tracked binaries: `research/TOU-Analysis_SolarBESS-ENG.pdf` (13.6 MB), `research/fmp_modeling.csv` (12 MB), `data/raw/saigon18/2026-01-29_saigon18_excel_model_v2.xlsm` (9.5 MB).
  - `activeContext.md` = 169 KB / 2,117 lines committed at repo root.
- **Desired state:** One canonical `src/python/reopt_pysam_vn/` package and one canonical `scripts/python/{reopt,pysam,integration}/` tree; heavy binaries out of normal tracking; `activeContext.md` reduced to a current-state pointer with history rotated into `docs/worklog/`.
- **Key repo surfaces:** `src/REoptVietnam.jl`, `src/__init__.py`, `src/reopt_vietnam.py`, `scripts/python/*.py` (flat), `research/`, `data/raw/saigon18/`, `data/interim/saigon18/`, `activeContext.md`, `docs/worklog/`, `.gitattributes` (new, if LFS).
- **Out of scope:** The generated-artifact untracking (Sprint 1), the onsite/offsite generalization (Sprint 3).

## Research Inputs
- `reports/2026-06-12-reopt-pysam-vietnam-repo-trim-gap-analysis.md` — GAP-03/05/07 definitions and the risk that an un-migrated caller depends on a shim (resolved: grep shows no tracked-code dependency).
- `research/2026-04-26_commercial-product-ideas.md` — references the flat script names (`scripts/python/dppa_settlement.py`, etc.); these are doc references only, updated in PHASE-01 if desired (non-blocking).

## Assumptions and Constraints
- **ASM-001:** The flat `scripts/python/*.py` shims and the 3 `src/` shims add zero capability; canonical targets are tested and current.
- **ASM-002:** `data/interim/saigon18/2026-03-20_saigon18_extracted_inputs.json` already captures the distilled output of the `.xlsm`, so day-to-day analysis does not re-read the workbook.
- **CON-001:** Deleting shims must not break `tests/run_all_tests.ps1` — verify with a full L1–L3 + smoke run.
- **CON-002:** Git LFS migration of existing files rewrites history; only adopt it if the user accepts a force-push / fresh-clone step (see Grill Me).
- **DEC-001:** `pytest` resolves the package via `pyproject.toml` `pythonpath = ["src/python"]`, not via the `src/` root shims — confirming the shims are inert for tests.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Remove the two shim layers | None | Deleted `src/` shims + ~37 flat `scripts/python/*.py`; green tests |
| PHASE-02 | Relocate / de-track heavy binaries | None (parallel to 01) | `.gitattributes` (LFS) or external store + manifest; binaries out of normal tracking |
| PHASE-03 | Trim `activeContext.md` | PHASE-01, PHASE-02 | Slim current-state `activeContext.md`; history in `docs/worklog/` |

## Detailed Phases

### PHASE-01 - Remove the two shadow shim layers
**Goal**
Delete the `src/` root shims and the flat `scripts/python/*.py` redirects, leaving only canonical paths.

**Tasks**
- [ ] TASK-01-01: Re-grep tracked code for live imports/calls of each shim before deletion: `from reopt_vietnam`, `import reopt_vietnam`, `src/REoptVietnam.jl`, and each flat script name. Confirm only logs/pycache/worktrees match.
- [ ] TASK-01-02: `git rm src/REoptVietnam.jl src/__init__.py src/reopt_vietnam.py`.
- [ ] TASK-01-03: `git rm` the ~37 flat shim scripts under `scripts/python/*.py` (the `NF==3` files — those directly in `scripts/python/`, not in `reopt/`, `pysam/`, `integration/`). Enumerate via `git ls-files scripts/python/ | awk -F/ 'NF==3'`.
- [ ] TASK-01-04: Fix the two cosmetic docstrings in `tests/python/reopt/test_unit.py` and `tests/python/reopt/test_integration.py` ("Tests for reopt_vietnam.py" → "Tests for reopt_pysam_vn.reopt.preprocess").
- [ ] TASK-01-05: Update any tracked doc that points at a removed flat path (`docs/`, `README.md`) to the canonical `scripts/python/{reopt,integration}/` path.

**Files / Surfaces**
- `src/REoptVietnam.jl`, `src/__init__.py`, `src/reopt_vietnam.py` — delete.
- `scripts/python/*.py` (flat, ~37) — delete.
- `tests/python/reopt/test_unit.py`, `tests/python/reopt/test_integration.py` — docstring fix.

**Dependencies**
- None (Sprint 1 recommended first but not required).

**Exit Criteria**
- [ ] `git ls-files scripts/python/ | awk -F/ 'NF==3'` returns empty.
- [ ] `git ls-files src/ | grep -vE 'src/(julia|python)/'` returns empty.
- [ ] `.\tests\run_all_tests.ps1 -SkipLayer4` + `-SmokeOnly` green.

**Phase Risks**
- **RISK-01-01:** A user muscle-memory command (`python scripts/python/run_ninhsim_dppa_case_1.py`) breaks. Mitigation: document the one-line path change (`integration/run_...`) in `README.md`; canonical scripts are unchanged.

### PHASE-02 - Relocate / de-track heavy binaries
**Goal**
Stop normal-tracking the 35 MB of reference binaries while keeping them accessible.

**Tasks**
- [ ] TASK-02-01: Decide mechanism per Grill Me Q-001 (Git LFS vs untrack+external+manifest vs leave-as-is).
- [ ] TASK-02-02 (if LFS): add `.gitattributes` with `*.pdf`, `*.xlsm`, large `*.csv` under `research/`/`data/raw/` tracked by LFS; `git lfs migrate import --include="research/TOU-Analysis_SolarBESS-ENG.pdf,research/fmp_modeling.csv,data/raw/saigon18/*.xlsm"` (history rewrite — confirm acceptance).
- [ ] TASK-02-03 (if untrack+external): `git rm --cached` the three files, add to `.gitignore`, and add `research/SOURCES.md` + `data/raw/saigon18/SOURCE.md` recording origin + retrieval instructions.
- [ ] TASK-02-04: Confirm the Saigon18 ingestion path still works from `data/interim/saigon18/*_extracted_inputs.json` without the raw `.xlsm` present (run `tests/python/integration/test_saigon18_data.py`).

**Files / Surfaces**
- `research/TOU-Analysis_SolarBESS-ENG.pdf`, `research/fmp_modeling.csv`, `data/raw/saigon18/2026-01-29_saigon18_excel_model_v2.xlsm`.
- `.gitattributes` (new) or `.gitignore` + `SOURCES.md`/`SOURCE.md`.

**Dependencies**
- None.

**Exit Criteria**
- [ ] The three large files are no longer normal-tracked blobs (LFS pointer or untracked).
- [ ] `test_saigon18_data.py` passes without the raw workbook in the working tree.

**Phase Risks**
- **RISK-02-01:** LFS migration force-push disrupts collaborators / the remote. Mitigation: gate on Grill Me Q-001; if chosen, coordinate a fresh-clone note. Default avoids history rewrite.

### PHASE-03 - Trim activeContext.md
**Goal**
Reduce the 2,117-line root log to a concise current-state file and preserve history where worklogs belong.

**Tasks**
- [ ] TASK-03-01: Move the historical body of `activeContext.md` into `docs/worklog/2026-06-12-activecontext-archive.md`.
- [ ] TASK-03-02: Rewrite `activeContext.md` as a short current-state pointer: active plans (this Sprint set), test-suite status, and a link to the worklog archive.
- [ ] TASK-03-03: Note in `CLAUDE.md`/`AGENTS.md` convention that `activeContext.md` stays slim and history rotates to `docs/worklog/`.

**Files / Surfaces**
- `activeContext.md`, `docs/worklog/`, `AGENTS.md`/`CLAUDE.md`.

**Dependencies**
- PHASE-01, PHASE-02 (so the new current-state reflects the post-trim repo).

**Exit Criteria**
- [ ] `activeContext.md` < ~150 lines and links to the worklog archive.
- [ ] No information lost (history present under `docs/worklog/`).

**Phase Risks**
- **RISK-03-01:** Global CLAUDE.md workflow writes verbose state back into `activeContext.md` over time. Mitigation: document the slim-file convention so future sessions append to worklog instead.

## Verification Strategy
- **TEST-001:** `.\tests\run_all_tests.ps1 -SkipLayer4` + `-SmokeOnly` green after shim removal.
- **TEST-002:** `pytest tests/python/integration/test_saigon18_data.py` green without the raw `.xlsm` present.
- **MANUAL-001:** `git ls-files` shows a single canonical `src/python/` package and no flat `scripts/python/*.py`.
- **OBS-001:** Tracked-blob size drops by ~35 MB (binaries) and file count by ~40 (shims).

## Risks and Alternatives
- **RISK-001:** Removing shims breaks an external automation outside this repo that calls a flat script path. Mitigation: shims only ever redirected; document the canonical path mapping in the commit body.
- **ALT-001:** Keep shims "just in case." Rejected — they are the primary source of duplicate-filename confusion the gap analysis flagged; git history preserves them if ever needed.
- **ALT-002:** `git filter-repo` to purge large blobs from all history (max size reduction). Deferred — higher blast radius than LFS; revisit only if clone size becomes a real pain point.

## Grill Me
1. **Q-001:** For the 35 MB of heavy binaries (PDF, CSV, xlsm), which mechanism — Git LFS (rewrites history, smallest future clones), untrack + external store + manifest (no rewrite, files leave git), or leave tracked (do nothing this sprint)?
   - **Recommended default:** Untrack + external + manifest — no history rewrite, no collaborator disruption, and the distilled `extracted_inputs.json` already covers the analysis path.
   - **Why this matters:** Determines PHASE-02 tasks and whether a force-push/fresh-clone is needed.
   - **If answered differently:** LFS adds `.gitattributes` + a `git lfs migrate` history rewrite; "leave tracked" drops PHASE-02 entirely.
2. **Q-002:** Keep backward-compat path notes for the removed flat scripts (a one-line mapping in README), or remove silently?
   - **Recommended default:** Add a short mapping table to `README.md` so existing muscle-memory commands have a clear redirect.
   - **Why this matters:** Affects PHASE-01 documentation tasks.
   - **If answered differently:** Skip the mapping table to keep README leaner.

## Suggested Next Step
Answer Grill Me Q-001 (binary mechanism), then execute PHASE-01 → PHASE-03. Commit as "refactor: remove shim layers + relocate heavy binaries + slim activeContext" and push to `main`.
