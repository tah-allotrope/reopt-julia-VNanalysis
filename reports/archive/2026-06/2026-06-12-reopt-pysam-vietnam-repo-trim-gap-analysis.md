# Gap Analysis: Trimmed & Restructured ReOpt + PySAM Vietnam Repo

**Date:** 2026-06-12
**Scope:** Reduce repo bloat and converge on a clean structure whose key function is using NREL **REopt** (buyer-side optimization) and **PySAM** (developer-side finance) to analyze future **onsite** (behind-the-meter) and **offsite / DPPA** clean-energy projects in Vietnam.
**Status:** Draft for Review

---

## Executive Summary

The core engine is healthy and capable: `src/python/reopt_pysam_vn/` cleanly separates `reopt/`, `pysam/`, and `integration/`, backed by a 56-file test suite and versioned Vietnam policy data in `data/vietnam/`. The problem is **not** capability — it's that the working toolkit is buried under ~250 committed generated artifacts (62 MB `artifacts/`, 13 MB `reports/`, 16 MB `present/`), **two shadow "compatibility-shim" layers** (3 stray `src/` files + ~37 flat `scripts/python/*.py` redirects), and 19 MB of dead `archive/colab/` plus foreign tooling (`.opencode/`). Of 631 tracked files, well over half are regenerable output or cruft.

Three gaps are CRITICAL/HIGH bloat removal (generated artifacts, shim layers, foreign dirs); one is structural — the onsite vs offsite/DPPA distinction is implemented as **bespoke per-deal modules** (`dppa_case_1/2/3`, `dppa_samsung_ttc`) rather than one generalized, parameterized pipeline. **Recommendation:** do the mechanical de-bloat first (Sprints 1–2, low risk, high signal-to-noise gain), then generalize the onsite/offsite analysis entry point (Sprint 3).

---

## Current Capabilities (What We Have)

| Capability | Status | Key Surfaces |
|---|---|---|
| REopt buyer-side optimization w/ Vietnam defaults | Mature | `src/python/reopt_pysam_vn/reopt/preprocess.py`, `regime_runner.py`, `regime_impact.py`; `src/julia/REoptVietnam.jl`; `scripts/julia/run_vietnam_scenario.jl` |
| PySAM developer-side finance (PVWatts+battery, single-owner, PPA) | Working | `src/python/reopt_pysam_vn/pysam/{pvwatts_battery,single_owner,cashflow,ppa,metrics,config}.py` |
| Offsite / DPPA settlement + strike search | Working (per-case) | `integration/{settlement,strike_search,dppa_case_1,dppa_case_2,dppa_case_3,dppa_samsung_ttc}.py` |
| Onsite (BTM) PV+BESS analysis | Working (per-case) | `integration/{bridge,ninhsim_solar_storage_60pct}.py`, `scenarios/templates/vn_*` |
| Project / offtaker matching + procurement compare | Working | `integration/{matching,procurement,project_catalog}.py` |
| Vietnam policy data (tariff, costs, emissions, Decree 57, regimes) | Mature | `data/vietnam/` (9 versioned JSON + manifest) |
| Ingestion (Excel → canonical inputs, load synthesis) | Working | `integration/`/`ingestion/{loader,metadata,synthesize}.py`, `scripts/python/reopt/extract_excel_inputs.py` |
| 4-layer test suite + cross-language validation | Mature | `tests/python/{reopt,pysam,integration,ingestion}/`, `tests/julia/`, `tests/cross_language/`, `tests/run_all_tests.ps1` |
| Reporting / decks | Bloat-heavy | `scripts/python/.../generate_*_report.py`, `present/`, `reports/decks/` |

---

## Target State

> A lean repo where the **only** top-level story is: *ingest a Vietnam project → run REopt (onsite/BTM optimization) and/or PySAM (offsite/DPPA developer finance) → produce a settlement + decision result.* Source, tests, Vietnam data, and a small set of golden examples are tracked; all regenerable outputs, one-off deal scripts, decks, and foreign tooling are removed or git-ignored. Onsite and offsite/DPPA are first-class, generalized concepts rather than copy-pasted per-deal modules.

Proposed converged structure:

```
src/
  julia/REoptVietnam.jl              # solve-path preprocessing
  python/reopt_pysam_vn/
    common/  ingestion/  reopt/  pysam/
    analysis/                        # NEW: generalized onsite + offsite/dppa pipelines
      onsite.py      (BTM REopt sizing/dispatch)
      offsite_dppa.py (PySAM finance + settlement + strike search)
data/vietnam/                        # versioned policy data (keep)
scenarios/templates/                 # parameterized inputs (keep)
scripts/
  julia/run_vietnam_scenario.jl
  python/{reopt,pysam,integration}/  # canonical scripts only — no flat shims
tests/                               # keep
docs/                                # keep, add onsite/offsite overview
examples/                            # 2-3 golden runs (in place of 62MB artifacts/)
```

Everything under `artifacts/`, `reports/*.html`, `present/`, `archive/`, `legacy/`, `.opencode/`, and `scenarios/generated/` is **regenerable or dead** and should not live in the tracked tree.

---

## Gap Analysis

### GAP-01: No generalized onsite / offsite-DPPA entry point — capability fragmented into per-deal modules

**Severity:** CRITICAL — The repo's stated "key function" exists only as copy-pasted one-off deal scripts, so adding a *future* Vietnam project means cloning a case module rather than calling a pipeline.

**Current state:** The integration layer hard-codes individual deals: `integration/dppa_case_1.py`, `dppa_case_2.py`, `dppa_case_3.py`, `dppa_samsung_ttc.py`, `ninhsim_solar_storage_60pct.py`, each with a matching `scripts/python/integration/analyze_*` and `tests/python/integration/test_dppa_*`. The generic primitives already exist alongside them — `settlement.py` (covered by `test_settlement_generic.py`/`test_settlement_presets.py`), `strike_search.py`, `bridge.py`, `project_catalog.py`, `assumptions.py` — but there is no single `onsite`/`offsite_dppa` API that takes a project config and runs the full REopt+PySAM+settlement chain.

**What's needed:**
- An `analysis/onsite.py` that wraps REopt (BTM PV+BESS sizing/dispatch vs EVN TOU) for any project config.
- An `analysis/offsite_dppa.py` that wraps PySAM single-owner finance + generic settlement + strike search for any DPPA deal.
- Retire the five bespoke case modules into thin config + golden-output examples driven by the generalized pipeline.

**Existing assets to reuse:**
- `integration/settlement.py`, `strike_search.py`, `bridge.py`, `assumptions.py`, `project_catalog.py` — already generic; the case modules are mostly orchestration glue on top of these.
- `data/projects/*.json` + `data/schemas/extracted_inputs.schema.json` — a project-config schema already exists to parameterize against.

**Effort estimate:** 1 multi-phase plan (3–4 phases): extract onsite pipeline, extract offsite/DPPA pipeline, migrate one case as proof, deprecate remaining case modules.

---

### GAP-02: ~250 regenerable generated artifacts are committed to git

**Severity:** CRITICAL — Dominates repo size and file count; every solve/report run produces tracked diff noise and obscures the ~70 files that are actual source.

**Current state:** Tracked generated output includes `artifacts/` (62 MB: 152 files of `*_reopt-results.json`, per-deal report JSON, dashboards), `reports/` (76 tracked `.html` phase reports + 4 `.pptx` decks + stray `.html.txt`), `scenarios/generated/` (regime/TOU solver inputs), and `artifacts/reports/test_runs/`. `.gitignore` already excludes `**/reopt-results.json` and `artifacts/sysimage/` and `test_runs/*.html` — but the bulk of generated JSON/HTML predates those rules and remains tracked.

**What's needed:**
- `git rm --cached` the regenerable trees (`artifacts/`, `reports/*.html`, `reports/decks/`, `scenarios/generated/`) and extend `.gitignore`.
- Preserve 2–3 canonical "golden" runs under a small `examples/` dir for documentation/regression.
- Confirm regression baselines stay tracked (`tests/baselines/` — these are intentionally versioned).

**Existing assets to reuse:** `.gitignore` already has the right pattern shape (`**/reopt-results.json`, `artifacts/sysimage/`); extend it. `legacy/README.md` documents the canonical output paths, so nothing is lost by untracking them.

**Effort estimate:** 1 short plan (1–2 phases), mostly mechanical `git rm --cached` + `.gitignore` edits; low risk.

---

### GAP-03: Two shadow "compatibility-shim" layers duplicate the canonical tree

**Severity:** HIGH — Creates duplicate filenames and import ambiguity; a reader can't tell which `analyze_ninhsim_cppa.py` is real.

**Current state:**
- `src/` root holds 3 shims redirecting into the canonical package: `src/REoptVietnam.jl` (6-line `include`), `src/__init__.py`, `src/reopt_vietnam.py` (re-exports `reopt_pysam_vn.reopt.preprocess`).
- `scripts/python/` holds **~37 flat `*.py` files** that are 5–9-line `runpy`/path shims into `scripts/python/integration/` or `scripts/python/reopt/` (verified: e.g. `scripts/python/run_ninhsim_dppa_case_1.py` just `runpy.run_path(... integration/run_ninhsim_dppa_case_1.py)`). 35 of these collide by name with the canonical files they point to.

**What's needed:** Delete both shim layers; update the handful of internal references (README already points at the canonical `scripts/python/reopt/` and `integration/` paths — 2 vs 1 references found). Keep canonical `src/python/reopt_pysam_vn/` and `scripts/python/{reopt,pysam,integration}/`.

**Existing assets to reuse:** The canonical targets already exist and are tested; shims add zero capability.

**Effort estimate:** 1 short plan (1 phase): delete shims, grep-and-fix stragglers, run the test suite.

---

### GAP-04: Foreign tooling, dead colab archive, and deck binaries inflate the tree

**Severity:** HIGH — ~35 MB and ~190 files of non-core material that has nothing to do with the ReOpt+PySAM analysis function.

**Current state:**
- `archive/colab/` (19 MB) — old Google Colab Julia/Python scenario scripts + results, superseded by the current pipeline.
- `.opencode/` (OpenCode agent skill bundle) + `.opencode_http.log` — a different AI tool's artifacts.
- `present/` (16 MB, 2 `.pptx`) + `reports/decks/*.pptx` (4 decks + conformance template) — presentation outputs.
- `ninhsim-report-review-fixed.png` (426 KB) — stray screenshot at repo root.
- `legacy/` — a single path-map README (historical breadcrumb only).

**What's needed:** Remove `archive/`, `.opencode/`, `.opencode_http.log`, root `*.png`, and deck binaries from the tracked tree (archive externally if any historical value). Fold the one useful `legacy/README.md` note into `docs/` if still relevant, else drop.

**Existing assets to reuse:** None needed — pure removal.

**Effort estimate:** 1 short plan (1 phase); low risk, but confirm nothing in `scripts/` reads from `archive/`.

---

### GAP-05: Heavy reference binaries tracked in `research/` and `data/raw/`

**Severity:** MEDIUM — 35 MB of binary reference material in normal git history bloats clones; not part of the analysis runtime.

**Current state:** `research/TOU-Analysis_SolarBESS-ENG.pdf` (13.6 MB), `research/fmp_modeling.csv` (12 MB), `data/raw/saigon18/2026-01-29_saigon18_excel_model_v2.xlsm` (9.5 MB source workbook). The `.xlsm` is a genuine input to the Saigon18 ingestion path; the PDF/CSV are reference docs.

**What's needed:** Move large reference binaries out of normal tracking (Git LFS, or an external `research/` store with a manifest). Keep the Saigon18 workbook if ingestion regression depends on it, otherwise LFS it.

**Existing assets to reuse:** `data/interim/saigon18/*_extracted_inputs.json` already captures the workbook's distilled output, reducing dependence on the raw `.xlsm`.

**Effort estimate:** 1 short plan (1 phase), or fold into Sprint 2.

---

### GAP-06: Onsite vs offsite/DPPA is not first-class in structure or docs

**Severity:** MEDIUM — The target's central distinction (behind-the-meter optimization vs offsite PPA settlement/finance) is implicit, scattered across case modules and templates.

**Current state:** `scenarios/templates/` mixes onsite (`vn_commercial_rooftop_pv`, `vn_industrial_pv_storage`) and resilience templates; DPPA logic lives inside per-case integration modules. `docs/` (`architecture.md`, `scenarios.md`, `reopt_internals.md`, `pysam.md`) documents the engines but not an onsite/offsite decision framework. README leads with the generic preprocessing tool, not the two analysis modes.

**What's needed:** A short `docs/onsite_vs_offsite.md` (or README section) and a structural split (`analysis/onsite.py` + `analysis/offsite_dppa.py` per GAP-01) that makes the two modes the primary navigation of the repo.

**Existing assets to reuse:** `research/2026-04-07-vietnam-dppa-buyer-guide.md`, `research/2026-04-25_vietnam-tou-rooftop-ppa.md` already contain the domain framing to draw from.

**Effort estimate:** Folds into GAP-01's plan; ~0.5 phase of docs.

---

## Second-Tier Gaps

| Gap | Severity | Summary | Existing Assets |
|---|---|---|---|
| GAP-07 | MEDIUM | `activeContext.md` is a 169 KB / 2,117-line running log committed at root — trim to a current-state pointer and rotate history into `docs/worklog/` | `docs/worklog/` already exists for this purpose |
| GAP-08 | MEDIUM | PySAM env fragility — `nrel-pysam` only installs in repo `.venv` (Py 3.12); system Python has no wheel. Repro env undocumented in README beyond `pip install` | `pyproject.toml` pins `nrel-pysam>=7.1`; PySAM tests already skip when absent (`test_pysam_import.py`) — needs a pinned/lock + README note |
| GAP-09 | LOW | Stray tracked scratch/lock files: `tests/.stdout.tmp` tracked, `Manifest.toml` (43 KB) committed, `NREL_API.env` present on disk (verify it stays untracked — it is git-ignored) | `.gitignore` already covers `*.env`; add `tests/.stdout.tmp` |

---

## Recommended Sprint Sequencing

| Priority | Gap | Rationale |
|---|---|---|
| Sprint 1 | GAP-02, GAP-04, GAP-09 | Pure mechanical removal (`git rm --cached` + `.gitignore`). Biggest size/noise reduction, near-zero risk, makes everything else easier to navigate. |
| Sprint 2 | GAP-03, GAP-05, GAP-07 | Delete shim layers, LFS/move heavy binaries, trim `activeContext.md`. Low risk once Sprint 1 clears the noise; run full test suite to confirm shim removal is clean. |
| Sprint 3 | GAP-01, GAP-06 | The one real engineering effort: generalize onsite + offsite/DPPA pipelines, retire per-deal modules, document the two modes. Do last — it benefits from a de-bloated tree and is the only gap that touches tested logic. |
| Backlog | GAP-08 | Reproducible PySAM env; valuable but not blocking the trim/restructure. |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Untracking `artifacts/`/`reports/` removes data a script reads at runtime | Broken report/analysis script | M | Grep `scripts/` and `src/` for reads from `artifacts/`/`reports/` before `git rm --cached`; keep golden examples under `examples/` |
| Deleting shim layers breaks an un-migrated caller | Import/runpath error | M | Full grep for each shim name; run `tests/run_all_tests.ps1` (L1–L3 + smoke) after removal |
| Removing `archive/colab` discards a still-referenced baseline | Lost reference result | L | Confirm `tests/baselines/` (the *tracked* baselines) are independent of `archive/`; archive externally before delete |
| GAP-01 generalization changes per-deal numeric output | Regression vs published case reports | M | Migrate one case (e.g. Samsung-TTC) against its existing golden JSON as a regression gate before retiring others |
| LFS migration rewrites history / clone friction | Onboarding breakage | L | Use LFS only for new large blobs or document a fresh-clone step; avoid history rewrite unless explicitly chosen |

---

## Suggested Next Step

This report is analysis-only (the `/gap` skill does not modify product files). Review it, then invoke `/plan` per sprint — start with **`/plan` on Sprint 1 (GAP-02 + GAP-04 + GAP-09)** for the high-impact, low-risk de-bloat, then **`/plan` on Sprint 3 (GAP-01)** for the onsite/offsite-DPPA generalization that delivers the restructured "key function." Sprints 1–2 are mechanical enough to execute directly if you'd rather skip planning.
