---
title: "reopt-pysam next-level: security, CI, offsite generalization, webapp phase 2"
date: "2026-07-11"
status: "complete — bulk-corrected 2026-07-31 per directive: plan predates 2026-07-20 and is presumed fully implemented (NOT individually verified against git/code evidence)"
request: "reopt-pysam-next-level"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-11-reopt-pysam-next-level-brainstorm.md"
  - "research/2026-06-30_decree-243-2026-nd-cp.md"
  - "research/2026-07-04_vietnam-dppa-web-app-brainstorm.md"
---

# Plan: reopt-pysam Next-Level — Security, CI, Offsite Generalization, Webapp Phase 2

## Objective

Pay down the foundation debt that the recently shipped DPPA web app now amplifies — a leaked NREL API key in git history, 5 unowned red tests with no CI, and an offsite/DPPA path that only works for one hardcoded deal — then unlock the two highest-value analyst features (strike-sweep chart, map-marker deal prefill) and bring the policy data layer current with Decree 243/2026/ND-CP.

## Context Snapshot

- **Current state:** A Vietnam DPPA techno-economic toolkit (`src/python/reopt_pysam_vn/`, ~11.8k LOC; REopt via NREL API + PySAM developer finance) with a localhost FastAPI web app over it. Onsite deals live-solve via the NREL API; offsite deals only work for the registered `DPPA_SAMSUNG_TTC` case and require a pre-solved `extracted` JSON upload. 552/557 package tests pass locally; 5 numeric benchmark tests fail on `main` with no owner; there is no CI, no ruff config, and no auth (by design, localhost-only). A live NREL API key was committed in history (added in commit `3911032`, untracked in `b14bc0b`, never rotated). Two `.pptx` decks are tracked despite `.gitignore` rules; stray screenshots sit at repo root.
- **Desired state:** Rotated credential + secret-scan hook; clean index; GitHub Actions running ruff + the non-network pytest suite green on every push; the 5 red tests fixed or deliberately re-baselined with documented rationale; a registry-based offsite path with ≥2 registered cases and a live PVWatts solve option in the web app; strike-sweep chart and marker-prefill shipped; Decree 243 surplus rules in the versioned data layer.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/{analysis,integration,webapp}/`, `tests/python/`, `pyproject.toml`, `requirements.txt`, `.gitignore`, `data/vietnam/`, `data/projects/`, `scenarios/templates/`, `examples/samsung-ttc_combined-decision.example.json`, `NREL_API.env` (git-ignored, local).
- **Out of scope:** Multi-tenant SaaS features (accounts, billing, cloud hosting); LAN binding/auth (hardening in PHASE-03 makes it a config change later); local Julia solve path from the web app; regime/TOU scenario toggle UI (own plan later); Playwright E2E as a CI gate; git history rewrite; Julia-side CI; editing `data/vietnam/` files from the UI.

## Environment & Conventions

- **Stack:** Python 3.12 via the repo-local `.venv` (**PySAM 7.1.0 only exists there** — system Python 3.14 has no `nrel-pysam` wheel and code falls back to synthetic solar profiles). FastAPI + Jinja2 + vanilla JS + Leaflet web app (no build step, no npm). Julia 1.10 + REopt.jl v0.56.4 exists but is **not touched by this plan**. Package layout: setuptools, `package-dir = {"" = "src/python"}`.
- **Setup:** `.venv\Scripts\python.exe -m pip install -e ".[webapp]"` (PowerShell, from repo root).
- **Build / Run (web app):** `$env:PYTHONPATH = "src/python"; .venv\Scripts\python.exe -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000`
- **Test (full Python suite):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python` — single test: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp/test_storage.py::test_name -x`. The 4-layer PowerShell runner `.\tests\run_all_tests.ps1` covers Julia too; not needed for this plan except final regression.
- **Conventions & traps:**
  - **`PYTHONPATH` gotcha:** a global `PYTHONPATH` pointing at an unrelated venv breaks webapp tests with `ModuleNotFoundError: pydantic_core._pydantic_core`. Always clear it (`$env:PYTHONPATH = ""`) before pytest; pytest resolves the package via `pyproject.toml` `pythonpath = ["src/python"]`.
  - Currency/units: VND/kWh for tariffs and strikes internally, US cents/kWh in strike sweeps (`sweep_strike_prices(... )` in `integration/strike_search.py` works in cents), USD for finance outputs. Never mix without an explicit conversion field.
  - JSON files are read with `encoding="utf-8-sig"` throughout (Windows BOM tolerance) — match that in new readers.
  - Versioned policy data: `data/vietnam/` files carry a `_meta` envelope; code reads only the `"data"` block; updates = new versioned file + one-line change in `data/vietnam/manifest.json`.
  - Bit-exact parity gates: `tests/python/webapp/test_golden_parity.py` and `tests/python/analysis/test_samsung_ttc_parity.py` compare against `examples/samsung-ttc_combined-decision.example.json` **exactly**. Any change that alters Samsung/TTC numeric output is a defect, not drift.
  - Generated outputs (`artifacts/`, `reports/*.html`, `present/`) are git-ignored by policy; don't track new ones.
- **Repo map:**
  - `src/python/reopt_pysam_vn/analysis/` — public front door: `types.py` (`DealConfig`, `OffsiteDppaResult` with blocks `deal, base_settlement, strike_sweep, adder_sensitivity, regime_stress, decision, quality`), `onsite.py`, `offsite_dppa.py` (`_ORCHESTRATORS` registry, currently only `"DPPA_SAMSUNG_TTC"`), `__main__.py` (CLI).
  - `src/python/reopt_pysam_vn/integration/` — engines: `settlement.py` (`ContractParams`, `compute_hourly_settlement`, `compute_buyer_benchmark`, `run_strike_sweep`), `strike_search.py` (`sweep_strike_prices`, `build_strike_price_summary`), `dppa_samsung_ttc.py` (1058-line golden path: `build_samsung_ttc_extracted_inputs`, `build_samsung_ttc_results`, `analyze_samsung_ttc_settlement`, `build_samsung_ttc_strike_sweep`, `build_samsung_ttc_adder_sensitivity`, `build_samsung_ttc_regime_stress`, `build_samsung_ttc_combined_decision`), bespoke case modules `dppa_case_1/2/3.py`, `ninhsim_solar_storage_60pct.py`, `factory_a.py`.
  - `src/python/reopt_pysam_vn/webapp/` — FastAPI app: `__init__.py` (`create_app`), `routes/api.py` (`_nest_form_fields`, `POST /api/deals`), `routes/pages.py`, `service.py` (`run_analysis`, `solve_relevant_hash`, `load_nrel_api_key`, `solve_onsite_via_nrel`), `jobs.py` (FIFO worker), `storage.py` (`RunStorage`), `forms.py`, `uploads.py`, `projects.py`, `results_view.py`, `compare.py`, `templates/*.html`, `static/{app.js,map.js}`.
  - `tests/python/{analysis,ingestion,integration,pysam,reopt,webapp}/` — pytest; webapp tests mock all NREL calls.
  - `data/vietnam/` — versioned policy JSON + `manifest.json`; `data/projects/` — map catalog; `scenarios/templates/` — 4 form-seeding templates.

## Research Inputs

- From `research/2026-07-11-reopt-pysam-next-level-brainstorm.md`:
  - A live NREL API key is recoverable from git history (added in commit `3911032`, removed from tracking in `b14bc0b`); rotation chosen over history rewrite.
  - Priority order fixed as: security/hygiene → CI + red tests → webapp hardening → offsite generalization → phase-2 features → Decree 243 data.
  - Offsite generalization = registry expansion + new generic builders, **not** a rewrite of `dppa_samsung_ttc.py`; keep parity tests green at every commit.
  - Run storage stays filesystem/no-DB; only the restart-fragile ordering (class-level `seq` counter) gets fixed.
  - Web feature order: strike-sweep view first (engine exists), then catalog-marker prefill; regime toggle deferred.
- From `research/2026-06-30_decree-243-2026-nd-cp.md` (Decree 243/2026/ND-CP, effective 2026-06-26):
  - Rooftop surplus export cap raised from 20% (Decree 58/2025) to **50% general rule**, with a transitional >50% allowance through 2030-12-31 where grid capacity permits; no cap in off-grid areas.
  - BESS discharge from rooftop-solar-charged storage is now explicitly tradable surplus.
  - Surplus price = prior-year average market price (VND/kWh), **capped** at the max regional utility-scale ground-mount solar tariff without BESS (excl. VAT); metering at inverter output; monthly settlement pays min(actual, agreed) volume.
  - Repo implication: new versioned export-rules data file, and `ContractParams` in `integration/settlement.py` may need an optional `surplus_price_cap` field (must default to inert to protect Samsung parity).
- From `research/2026-07-04_vietnam-dppa-web-app-brainstorm.md`:
  - The app is deliberately localhost-only, single-user, no auth, no DB (DEC-015/022 there) — those decisions stand; this plan hardens inputs so LAN exposure later is a config change.
  - Strike-sweep interactive views were explicitly deferred as "phase 2 candidates" — picked up here in PHASE-05.

## Assumptions and Constraints

- **ASM-001:** Rotating the NREL developer key happens in the NREL developer portal, outside the repo — **BINDING DEFAULT:** the executor performs every in-repo step (secret-scan hook, docs) and lists the rotation as a human action item in the final report; no plan step requires the new key (all tests mock NREL).
- **ASM-002:** GitHub Actions is available on the `origin` remote (`https://github.com/tah-allotrope/reopt-pysam.git`) — verified the remote exists. **BINDING DEFAULT:** if Actions is disabled for the repo, still commit the workflow file; it activates when enabled.
- **ASM-003:** `nrel-pysam>=7.1` installs from PyPI on ubuntu-latest / Python 3.12 — **BINDING DEFAULT:** if the install fails in CI, drop it from the CI install line and rely on the suite's existing skip-when-PySAM-unavailable behavior; PySAM-numeric coverage then remains local-only.
- **ASM-004:** The 5 failing tests are numeric tolerance/benchmark drift as `activeContext.md` records — **BINDING DEFAULT:** for each test, first produce an exploratory diff (actual vs expected values printed); re-baseline **only** if `git worktree` bisection to an older commit shows the drift comes from environment/data updates rather than a code regression; a real regression gets a root-cause fix.
- **ASM-005:** No pytest marker currently distinguishes network-hitting tests — **BINDING DEFAULT:** introduce marker name `network` (registered in `pyproject.toml`), applied to every test that opens a real HTTP connection; CI runs `-m "not network"`.
- **ASM-006:** No ruff configuration exists — **BINDING DEFAULT:** configure ruff with its default rule set (`E4`, `E7`, `E9`, `F`) plus `I` (import sorting) **disabled** for now, `line-length = 100`, `target-version = "py310"`; do not run a repo-wide autofix sweep beyond what CI needs to pass.
- **ASM-007:** The exact key shape of the `strike_sweep` block inside run results is not restated here — **BINDING DEFAULT:** derive it at implementation time from `examples/samsung-ttc_combined-decision.example.json` (`offsite` block) and write the chart-series extractor against that golden file's actual keys.
- **ASM-008:** `ninhsim_solar_storage_60pct.py` has an end-to-end analysis function but may not emit the exact 7-block combined-decision dict — **BINDING DEFAULT:** the ninhsim orchestrator wrapper maps its output into the 7-block contract (`deal, base_settlement, strike_sweep, adder_sensitivity, regime_stress, decision, quality`), filling genuinely inapplicable blocks with `{}`; correctness is asserted with unit tests on block presence + spot values, not a bit-exact golden.
- **ASM-009:** The tracked `ceba-review/*.pptx` decks are local-only deliverables, not versioned assets — **BINDING DEFAULT:** untrack via `git rm --cached` (files stay on disk). `scenarios/case_studies/regina/Regina.xlsx` is a **live test input** (referenced by `tests/python/ingestion/test_loader.py`, `test_metadata.py`, `test_case_study_validation.py`, `tests/python/integration/test_matching_e2e.py`) and **stays tracked**.
- **ASM-010:** Teammates do not yet need LAN access to the web app — **BINDING DEFAULT:** keep `127.0.0.1` binding; PHASE-03 input hardening ships regardless.
- **CON-001:** Samsung/TTC output is bit-exact-gated; `tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_is_bit_exact` and `tests/python/webapp/test_golden_parity.py` must pass unchanged after every phase (except where PHASE-02 re-baselines them per ASM-004).
- **CON-002:** The web app must never fork analytics logic; it only calls `reopt_pysam_vn.analysis` / `integration` code (standing constraint from the web-app plan).
- **CON-003:** All new JSON readers use `encoding="utf-8-sig"`.
- **DEC-001:** Rotate the leaked key; do **not** rewrite git history (breaks clones/worktrees for no gain once the key is dead).
- **DEC-002:** CI = GitHub Actions, ubuntu-latest, Python 3.12, ruff + `pytest tests/python -m "not network"`; Julia stays local-only.
- **DEC-003:** Dependencies live in `pyproject.toml` only; `requirements.txt` becomes a one-line `-e .[webapp]` pointer.
- **DEC-004:** Run ordering fix: sort runs by `created_at` (the `%Y%m%dT%H%M%S%f` UTC format sorts lexicographically); the class-level `RunStorage._counter` becomes an instance attribute seeded from existing runs.
- **DEC-005:** Form input hardening: whitelist top-level form keys to `case`, `mode`, `title` and dotted keys whose first segment is one of `site`, `plant`, `load`, `contract`, `finance`, with at most one dot; reject any other key with HTTP 422 naming the offending keys.

## Specification

**Form-key validation logic (PHASE-03),** applied inside `_nest_form_fields` in `src/python/reopt_pysam_vn/webapp/routes/api.py`:

1. Skip keys `load_file`, `extracted_file`, `force_resolve` (existing behavior).
2. Skip empty/None values (existing behavior).
3. Split the key on `.`:
   - 1 part → allowed only if the key is exactly `case`, `mode`, or `title`.
   - 2 parts → allowed only if part 1 is in `{"site", "plant", "load", "contract", "finance"}`.
   - 3+ parts → rejected.
4. Collect all rejected keys; if the set is non-empty, raise a validation error carrying the sorted offending key names. The route converts it to HTTP 422 with detail `unexpected form field(s): <comma-separated names>`.
5. Value coercion is unchanged: attempt `float(value)`, fall back to the raw string.

**Decree 243 surplus price (PHASE-06),** for the new data file (formula stored as data, not yet wired into settlement math):

`P_surplus = min(P_avg_prev_year, P_cap_ground_mount)`

- `P_surplus` — price paid for surplus rooftop-solar electricity, VND/kWh, excl. VAT.
- `P_avg_prev_year` — previous calendar year's average electricity market price announced by the market operator, VND/kWh.
- `P_cap_ground_mount` — maximum regional tariff for utility-scale ground-mounted solar **without** BESS, VND/kWh, excl. VAT.
- Monthly settled volume = `min(actual_surplus_kwh, agreed_surplus_kwh)`; surplus is metered at inverter output; general cap = 50% of system output, with a >50% allowance permitted by agreement through 2030-12-31.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Security & repo hygiene | None | Untracked binaries, secret-scan hook, deps consolidated, `CLAUDE.md`, clean `git status` |
| PHASE-02 | CI pipeline + fix the 5 red tests | PHASE-01 | `.github/workflows/ci.yml`, ruff config, `network` marker, green suite |
| PHASE-03 | Webapp hardening (input allowlist, run ordering) | PHASE-02 | 422 on unknown form keys; restart-safe run ordering |
| PHASE-04 | Offsite generalization + live offsite solve | PHASE-02 | ninhsim registered as 2nd orchestrator; `build_extracted_inputs_from_deal`; webapp offsite runs without pre-solved upload |
| PHASE-05 | Analyst features: strike-sweep chart + marker prefill | PHASE-03, PHASE-04 | Strike-sweep Plotly chart on run page; "Use as deal site" map prefill |
| PHASE-06 | Decree 243/2026 policy data refresh | PHASE-02 | `vn_export_rules_decree243.json`, manifest bump, optional `surplus_price_cap` in `ContractParams` |

## Detailed Phases

### PHASE-01 - Security & Repo Hygiene

**Goal**
Remove the credential exposure risk, untrack ignored binaries, consolidate dependency declarations, and leave `git status` clean.

**Tasks**
- [x] TASK-01-01: Verify the leak: `git log --all --oneline -S "API_KEY_NAME" -- NREL_API.env` shows the key was committed (expect commits `3911032` and `b14bc0b`). Record the finding; the **human action item** is rotating the key at the NREL developer portal and updating the local `NREL_API.env` (ASM-001).
- [x] TASK-01-02: Untrack the two ignored-but-tracked decks: `git rm --cached "ceba-review/cong bess session.pptx" "ceba-review/cong bess session [reviewed].pptx"` (files stay on disk). Do **not** touch `scenarios/case_studies/regina/Regina.xlsx` — it is a live test input (ASM-009).
- [x] TASK-01-03: Delete the stray root screenshots `phase04_new_deal_initial.png` and `phase04_new_deal_scrolled.png` (session artifacts of a completed verification; the worklog retains the record).
- [x] TASK-01-04: Commit the outstanding untracked docs: `plans/2026-07-06-map-site-picker-webapp-plan.md`, `research/2026-06-30_decree-243-2026-nd-cp.md`, `research/2026-07-06_map-site-picker-webapp-brainstorm.md`, `research/2026-07-11-reopt-pysam-next-level-brainstorm.md`, and this plan file. Leave `ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx` untracked (covered by existing ignore rules; if not, add `ceba-review/*.pptx` to `.gitignore`).
- [x] TASK-01-05: Reduce `requirements.txt` to a pointer: replace its 6 dependency lines with a single line `-e .[webapp]` plus a comment `# Dependencies are declared in pyproject.toml; this file exists for pip -r muscle memory.`
- [ ] TASK-01-06: Create `.pre-commit-config.yaml` with two hooks: `gitleaks` (repo `https://github.com/gitleaks/gitleaks`, hook id `gitleaks`, pinned to a current release tag) and `ruff` (repo `https://github.com/astral-sh/ruff-pre-commit`, hook id `ruff`, same pin discipline). Installation (`pip install pre-commit; pre-commit install`) is opt-in; document it in `README.md` under a short "Pre-commit hooks" heading.
- [ ] TASK-01-07: Create `CLAUDE.md` at repo root containing a pointer: a one-paragraph note that `AGENTS.md` is the project law file (environment, commands, pitfalls, docs index) and must be read first, plus the test command and the `PYTHONPATH` gotcha verbatim.

**File Changes**
- `requirements.txt` (modify): replace all content per TASK-01-05.
- `.pre-commit-config.yaml` (create): gitleaks + ruff hooks per TASK-01-06.
- `CLAUDE.md` (create): pointer to `AGENTS.md` per TASK-01-07.
- `README.md` (modify): add a 4-6 line "Pre-commit hooks" section after "Python Setup"; leave everything else alone.
- `.gitignore` (modify only if needed): ensure `ceba-review/*.pptx` is covered; otherwise leave untouched (loose negation edits have burned this repo before — see Gotchas).
- `phase04_new_deal_initial.png`, `phase04_new_deal_scrolled.png` (delete).

**Function Signatures**
- None — no code interfaces change in this phase.

**Test Specs**
- `git ls-files | grep -i pptx` → empty output.
- `git status --porcelain` after commits → empty output (clean tree).
- `.venv\Scripts\python.exe -m pip install -r requirements.txt` → succeeds (installs the package editable with webapp extra).

**Dependencies**
- None.

**Exit Criteria**
- [ ] No `.pptx` in `git ls-files`; `Regina.xlsx` still tracked.
- [ ] `git status` clean; stray PNGs gone; docs committed.
- [ ] `CLAUDE.md` and `.pre-commit-config.yaml` exist and are committed.
- [ ] Rotation action item recorded for the human (key name/portal, plus updating local `NREL_API.env`).

**Phase Risks**
- **RISK-01-01:** Untracking a file someone expected versioned — mitigated by ASM-009 defaults and by grepping test references before untracking (done: only the two decks go).

### PHASE-02 - CI Pipeline + Red Test Paydown

**Goal**
Every push runs ruff + the non-network Python suite green on GitHub Actions; the 5 known-failing tests are fixed or deliberately re-baselined.

**Tasks**
- [x] TASK-02-01: Add `[tool.ruff]` to `pyproject.toml` per ASM-006 (`line-length = 100`, `target-version = "py310"`; default rule set). Run `ruff check src/python tests scripts/python` locally and fix only actual errors it reports (default rules are lenient; expect few).
- [x] TASK-02-02: Register the `network` marker in `pyproject.toml` (`[tool.pytest.ini_options] markers = ["network: makes real HTTP calls; excluded in CI"]`). Find network-hitting tests with `grep -rlE "requests\.(get|post)|urlopen|nlr\.gov" tests/python` and by inspecting `tests/python/integration/` (the NREL connectivity/solve tests, e.g. anything calling `solve_via_api` or `developer.nlr.gov`); decorate each with `@pytest.mark.network`. Webapp tests are already fully mocked — none should need the marker.
- [x] TASK-02-03: Create `.github/workflows/ci.yml`: trigger on `push` + `pull_request`; ubuntu-latest; `actions/setup-python@v5` with `python-version: "3.12"`; steps `pip install -e ".[webapp]" pytest ruff`, `ruff check src/python tests scripts/python`, `python -m pytest tests/python -m "not network" -q`. If `nrel-pysam` fails to install on the runner, apply ASM-003.
- [ ] TASK-02-04: Fix the 5 red tests, one at a time, using the exploratory-diff-first protocol (ASM-004). The list (all confirmed failing on unmodified `main`, 2026-07-04):
  1. `tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_full_tree_within_bar`
  2. `tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_is_bit_exact`
  3. `tests/python/integration/test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`
  4. `tests/python/integration/test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`
  5. `tests/python/pysam/test_strike_price_discovery.py::test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike`
  For each: (a) run it and capture the actual-vs-expected numbers; (b) `git worktree add ../reopt-prior <older-commit>` and run the same test there to date the drift; (c) root-cause fix if code regression, else re-baseline the expected values/golden file with an inline comment stating the date, the observed delta, and why it is environmental (e.g., PySAM version, NREL resource data revision). If the Samsung bit-exact golden is re-baselined, regenerate `examples/samsung-ttc_combined-decision.example.json` via its documented builder script and note the regeneration command in the commit message.
- [ ] TASK-02-05: Update `activeContext.md`: remove the "Known pre-existing test failures" backlog section (now resolved) and note the CI gate.

**File Changes**
- `pyproject.toml` (modify): add `[tool.ruff]` table and `markers` under `[tool.pytest.ini_options]`; leave dependencies and packaging untouched.
- `.github/workflows/ci.yml` (create): per TASK-02-03.
- `tests/python/...` (modify): `@pytest.mark.network` decorators; baseline/tolerance updates from TASK-02-04 only.
- `examples/samsung-ttc_combined-decision.example.json` (modify, only if TASK-02-04(b) proves environmental drift): regenerated golden.
- `activeContext.md` (modify): per TASK-02-05.

**Function Signatures**
- None — no code interfaces change in this phase.

**Test Specs**
- `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network" -q` → `0 failed` (previously 5 failed).
- `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` (network included, with `NREL_API.env` present) → 0 failed or documented skips only.
- `ruff check src/python tests scripts/python` → exit code 0.
- Push a branch → the Actions run appears and finishes green.

**Dependencies**
- PHASE-01 (clean tree to commit against).

**Exit Criteria**
- [ ] CI workflow green on the default branch.
- [ ] All 5 listed tests pass locally; each fix/re-baseline commit explains cause and evidence.
- [ ] `activeContext.md` backlog section cleared.

**Phase Risks**
- **RISK-02-01:** A "drift" is actually a real numeric regression — mitigated by the mandatory worktree bisection step before any re-baseline (ASM-004).
- **RISK-02-02:** Re-baselining the Samsung golden while PHASE-04/05 are in flight would mask their bugs — do TASK-02-04 to completion **before** starting PHASE-04.

### PHASE-03 - Webapp Hardening

**Goal**
Close the mass-assignment surface on the deal form and make run ordering restart-safe, without changing the filesystem storage design.

**Tasks**
- [ ] TASK-03-01: Implement the form-key allowlist per `## Specification` in `src/python/reopt_pysam_vn/webapp/routes/api.py`: add module constants `_ALLOWED_SCALAR_KEYS = {"case", "mode", "title"}` and `_ALLOWED_SECTIONS = {"site", "plant", "load", "contract", "finance"}`; make `_nest_form_fields` collect violations and raise `ValueError` listing them; wrap the call site in `create_deal` to convert `ValueError` → `HTTPException(422, detail=...)` (the existing `deal_config_from_form` 422 wrapping pattern at the same call site shows the idiom).
- [ ] TASK-03-02: Fix run ordering in `src/python/reopt_pysam_vn/webapp/storage.py`: change `list_runs()` sort key from `r.get("seq", 0)` to `(r.get("created_at", ""), r.get("run_id", ""))`, descending — the `%Y%m%dT%H%M%S%f` UTC timestamp sorts lexicographically. Convert the class attribute `_counter = 0` to an instance attribute initialized in `__init__` by scanning existing run dirs for the max `seq` in their `status.json` (0 when none); keep writing `seq` into `status.json` for backward compatibility with existing run dirs.
- [ ] TASK-03-03: Extend `tests/python/webapp/test_api_runs.py` (or the test module currently covering `POST /api/deals`) and `tests/python/webapp/test_storage.py` per the Test Specs below.

**File Changes**
- `src/python/reopt_pysam_vn/webapp/routes/api.py` (modify): `_nest_form_fields` validation + 422 wrapping; leave upload handling, `force_resolve` parsing, and all other routes alone.
- `src/python/reopt_pysam_vn/webapp/storage.py` (modify): sort key + counter seeding; leave the run-dir layout, file names, and all read/write methods alone.
- `tests/python/webapp/test_api_runs.py`, `tests/python/webapp/test_storage.py` (modify): new cases.

**Function Signatures**
- `_nest_form_fields(form_data) -> Dict[str, Any]` — unchanged signature; now raises `ValueError` whose message lists rejected keys, instead of silently nesting arbitrary keys.
- `RunStorage.__init__(self, root: Union[str, Path]) -> None` — unchanged signature; now seeds `self._counter` from the max existing `seq` under `root`.

**Test Specs**
- POST `/api/deals` multipart with a valid CSV and an extra field `evil.injected=1` → HTTP 422, detail contains `unexpected form field(s): evil.injected`.
- POST with field `site.latitude.extra=1` (3 segments) → HTTP 422 naming that key.
- POST with only legitimate keys (`case`, `mode`, `title`, `site.latitude`, `finance.discount_rate_fraction`, CSV load file) → HTTP 202 with a `run_id` (existing happy path still green).
- `RunStorage(tmp)` A creates 2 runs; a **new** `RunStorage(tmp)` B creates a 3rd run → `B.list_runs()[0]` is the 3rd run and its `seq` is 3 (not 1).
- Two runs created in the same instance → `list_runs()` returns newest `created_at` first.

**Dependencies**
- PHASE-02 (CI catches regressions from here on).

**Exit Criteria**
- [ ] `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp -q` → 0 failed, with the new cases included.
- [ ] Unknown-key submissions return 422; existing form flow unaffected.

**Phase Risks**
- **RISK-03-01:** The form template posts a field the allowlist misses (e.g., a hidden helper input) — before merging, submit the real `/deals/new` form via a running server and confirm 202; add any legitimately posted key to the skip list, not the section whitelist.

### PHASE-04 - Offsite Generalization + Live Offsite Solve

**Goal**
A second deal case runs through `run_offsite_dppa` without touching Samsung code, and the web app can run an offsite deal from form inputs alone — generating the PVWatts profile in-process instead of requiring a pre-solved `extracted` upload.

**Tasks**
- [ ] TASK-04-01: Register ninhsim as the second orchestrator. In `src/python/reopt_pysam_vn/integration/ninhsim_solar_storage_60pct.py`, locate its end-to-end analysis entry point and add a wrapper `build_ninhsim_combined_decision(extracted: dict, *, run_developer: bool = True) -> dict` that emits the 7-block contract (ASM-008). Register it in `analysis/offsite_dppa.py`'s `_ORCHESTRATORS` under its case id (match the case string used in `scenarios/`/`data/interim/` for ninhsim, e.g. `"NINHSIM_SOLAR_STORAGE_60PCT"` — verify against the module's own constants) via a lazy-import wrapper exactly like `_samsung_ttc_orchestrator`.
- [ ] TASK-04-02: Create `src/python/reopt_pysam_vn/analysis/extracted_builders.py` with `build_extracted_inputs_from_deal(deal_config: DealConfig) -> dict`. Model it on `build_samsung_ttc_extracted_inputs` (in `integration/dppa_samsung_ttc.py`, line ~177): produce the `*_extracted_inputs`-shaped dict the settlement engine consumes — 8760 solar generation series from PySAM PVWatts at `site.latitude`/`site.longitude` (falling back to the existing synthetic-profile path when PySAM is absent, mirroring `_pvwatts_south_solar_8760` / `_synthetic_south_solar_8760`), 8760 EVN TOU rate series from `data/vietnam/vn_tariff_2025.json` for the deal's `site.region`/`site.customer_type`/`site.voltage_level`, load series from `deal_config.load["loads_kw"]`, and contract fields from `deal_config.contract`. Raise `ValueError` naming each missing required field (`site.latitude`, `site.longitude`, `plant.capacity_mw` or the equivalent capacity key used by the settlement inputs, `load.loads_kw`).
- [ ] TASK-04-03: Create a generic orchestrator `build_generic_combined_decision(extracted: dict, *, run_developer: bool = True) -> dict` in `src/python/reopt_pysam_vn/integration/offsite_generic.py`, composed **only** of existing engines: `compute_hourly_settlement` + `compute_buyer_benchmark` (base_settlement block), `run_strike_sweep` (strike_sweep block), and — when `run_developer=True` and PySAM is available — the PySAM developer screen the Samsung builder uses; `adder_sensitivity` and `regime_stress` return `{}` in v1 with a `quality` note `"generic-v1: adder/regime blocks not modeled"`. Wire it as the registry **fallback** in `run_offsite_dppa`: after the `_ORCHESTRATORS.get(deal_config.case)` lookup fails, use the generic builder instead of raising, and record `"orchestrator": "generic"` in the result's `quality` block. Keep the explicit error only when `extracted` lacks the minimum keys the generic path needs.
- [ ] TASK-04-04: Wire the live offsite path into the web app: in `src/python/reopt_pysam_vn/webapp/service.py`, where `run_analysis` currently requires `extracted` for offsite modes, call `build_extracted_inputs_from_deal(deal_config)` when `extracted is None`, inside the background job (this is minutes-cheap: PVWatts is local). Update `webapp/README.md` ("NREL API key" section) to say offsite deals now live-solve from form inputs, with pre-solved `extracted` upload remaining as the power-user override.
- [ ] TASK-04-05: Tests per Test Specs; then run the **full** suite (structural-change rule from this repo's history: subsets have missed breakage).

**File Changes**
- `src/python/reopt_pysam_vn/integration/ninhsim_solar_storage_60pct.py` (modify): add the wrapper function only; leave existing functions untouched.
- `src/python/reopt_pysam_vn/analysis/offsite_dppa.py` (modify): add `_ninhsim_orchestrator` lazy wrapper + registry entry; add generic fallback in `run_offsite_dppa`; keep `register_orchestrator` and the injected-`combined_decision_fn` path unchanged.
- `src/python/reopt_pysam_vn/analysis/extracted_builders.py` (create): per TASK-04-02.
- `src/python/reopt_pysam_vn/integration/offsite_generic.py` (create): per TASK-04-03.
- `src/python/reopt_pysam_vn/webapp/service.py` (modify): offsite branch of `run_analysis` only.
- `src/python/reopt_pysam_vn/webapp/README.md` (modify): live-offsite note.
- `tests/python/analysis/test_extracted_builders.py` (create), `tests/python/analysis/test_offsite_generic.py` (create), `tests/python/webapp/test_api_runs.py` (modify): new coverage.

**Function Signatures**
- `build_ninhsim_combined_decision(extracted: dict, *, run_developer: bool = True) -> dict` — returns the 7-block combined-decision dict for the ninhsim case.
- `build_extracted_inputs_from_deal(deal_config: DealConfig) -> dict` — returns a settlement-engine-ready `*_extracted_inputs` dict built from form-level deal fields (PVWatts or synthetic 8760 generation, EVN TOU 8760 rates, load series, contract params).
- `build_generic_combined_decision(extracted: dict, *, run_developer: bool = True) -> dict` — returns a 7-block combined-decision dict using only the generic settlement/strike engines; `adder_sensitivity`/`regime_stress` empty in v1.

**Test Specs**
- `run_offsite_dppa(DealConfig(case="NINHSIM_...", mode="offsite_dppa"), extracted=<ninhsim extracted fixture>)` → `OffsiteDppaResult` with non-empty `base_settlement` and `decision`; no `ValueError`.
- `run_offsite_dppa(DealConfig(case="BRAND_NEW_CASE", mode="offsite_dppa"), extracted=<minimal generic fixture>)` → succeeds via generic fallback; `result.quality["orchestrator"] == "generic"`.
- `build_extracted_inputs_from_deal` with `site.latitude` missing → `ValueError` whose message contains `site.latitude`.
- `build_extracted_inputs_from_deal` on a complete synthetic deal (lat 10.9, lon 106.7, region "south", 8760-length constant load) → dict whose generation series has length 8760 and whose rate series has length 8760.
- Webapp: POST an offsite deal **without** `extracted_file` → 202; after the (mocked-PVWatts or synthetic) job completes, `GET /api/runs/{id}` shows `state == "done"` with a result containing `base_settlement`.
- **Parity guard:** `pytest tests/python/analysis/test_samsung_ttc_parity.py tests/python/webapp/test_golden_parity.py` → pass, bit-exact, untouched.

**Dependencies**
- PHASE-02 complete (goldens stabilized first — RISK-02-02).

**Exit Criteria**
- [ ] Two registry entries + generic fallback live; Samsung parity bit-exact green.
- [ ] Web app runs an offsite deal end-to-end from the form with no `extracted` upload.
- [ ] Full suite green: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network" -q` → 0 failed.

**Phase Risks**
- **RISK-04-01:** The ninhsim module's output shape resists the 7-block mapping — mitigation: blocks may be `{}` (ASM-008); the contract requires presence, not richness.
- **RISK-04-02:** PVWatts resource fetch inside the job worker needs network/API access some machines lack — mitigation: the synthetic-profile fallback path already exists in `dppa_samsung_ttc.py`; reuse it and surface which path ran in the result's `quality` block.

### PHASE-05 - Analyst Features: Strike-Sweep Chart + Marker Prefill

**Goal**
Analysts see the strike sweep as an interactive chart on the run page and can seed a new deal's site directly from a catalog project marker.

**Tasks**
- [ ] TASK-05-01: Inspect `examples/samsung-ttc_combined-decision.example.json` to fix the exact `strike_sweep` key names (ASM-007). Add `strike_sweep_series(result: Dict[str, Any]) -> Optional[Dict[str, Any]]` to `src/python/reopt_pysam_vn/webapp/results_view.py` returning `None` when the result has no non-empty `strike_sweep` block, else a dict of parallel lists shaped for Plotly (x = strike prices in the golden's native unit — label the unit from the data, do not guess; y-series = the sweep's buyer/developer outcome arrays).
- [ ] TASK-05-02: Render it in `src/python/reopt_pysam_vn/webapp/templates/run.html`: a new chart card, hidden when the series function returns `None` (onsite-only runs), following the existing Plotly chart-card pattern in that template; route change in `src/python/reopt_pysam_vn/webapp/routes/pages.py` to pass the series.
- [ ] TASK-05-03: Marker prefill in `src/python/reopt_pysam_vn/webapp/static/map.js`: add a pure function `projectPrefillFields(project)` mapping a `/api/projects` record to form-field values (`site.latitude`, `site.longitude`, plus region via the existing latitude-band helper), and a "Use as deal site" button inside the existing catalog-marker popup on `/deals/new` that applies those values through the existing two-way input sync. No behavior change on the read-only run-page context map.
- [ ] TASK-05-04: Tests: pure-Python tests for `strike_sweep_series`; a pages test asserting the run page for an offsite run contains the strike-sweep card and an onsite-only run does not; a pages test asserting `/deals/new` HTML ships the prefill hook (`projectPrefillFields` present in served `map.js`, button template string present). JS logic beyond that stays manually verified (browser automation against this app has proven flaky; do not add a CI-gating E2E).

**File Changes**
- `src/python/reopt_pysam_vn/webapp/results_view.py` (modify): add `strike_sweep_series`; leave existing series builders alone.
- `src/python/reopt_pysam_vn/webapp/templates/run.html` (modify): one new chart card.
- `src/python/reopt_pysam_vn/webapp/routes/pages.py` (modify): pass series to the template.
- `src/python/reopt_pysam_vn/webapp/static/map.js` (modify): `projectPrefillFields` + popup button; leave `initContextMap` alone.
- `tests/python/webapp/test_results_view.py`, `tests/python/webapp/test_pages.py` (modify): new cases.

**Function Signatures**
- `strike_sweep_series(result: Dict[str, Any]) -> Optional[Dict[str, Any]]` — returns Plotly-ready parallel lists for the strike sweep, or `None` when the run has no sweep.
- `projectPrefillFields(project) -> object` (JS) — returns `{ "site.latitude": number, "site.longitude": number, "site.region": string }` from a catalog project record.

**Test Specs**
- `strike_sweep_series(<golden samsung result loaded from examples/samsung-ttc_combined-decision.example.json>)` → non-`None`; every list in the returned dict has equal length ≥ 2.
- `strike_sweep_series({"strike_sweep": {}})` → `None`; `strike_sweep_series({})` → `None`.
- GET `/runs/{id}` for a stored offsite run fixture → HTML contains the strike-sweep card marker (e.g., element id `strike-sweep-chart`); for an onsite-only fixture → it does not.
- GET `/static/map.js` → body contains `projectPrefillFields`.

**Dependencies**
- PHASE-03 (allowlist settled so prefill posts only allowed keys), PHASE-04 (offsite runs from the form produce sweeps to look at).

**Exit Criteria**
- [ ] Webapp suite green with the new cases.
- [ ] Manual check: run the app, open a completed offsite run → sweep chart renders; click a catalog marker on `/deals/new` → "Use as deal site" fills lat/lon/region and the marker moves.

**Phase Risks**
- **RISK-05-01:** Sweep units (VND/kWh vs cents/kWh) mislabeled on the chart axis — mitigation: TASK-05-01 takes the unit from the golden's own field names/values, and the axis label states it explicitly.

### PHASE-06 - Decree 243/2026 Policy Data Refresh

**Goal**
The versioned Vietnam data layer reflects Decree 243/2026/ND-CP (effective 2026-06-26): 50% surplus cap, transitional >2030 allowance, BESS surplus eligibility, and the surplus price-cap formula — without changing any existing model output.

**Tasks**
- [x] TASK-06-01: Create `data/vietnam/vn_export_rules_decree243.json` following the existing `vn_export_rules_decree57.json` structure (`_meta` envelope with source citations + `"data"` block). Data block fields: `surplus_cap_fraction: 0.50`, `transitional_above_cap_allowed: true`, `transitional_above_cap_until: "2030-12-31"`, `offgrid_unlimited: true`, `bess_surplus_eligible: true`, `surplus_price_rule: {"base": "prior_year_avg_market_price_vnd_per_kwh", "cap": "max_regional_ground_mount_solar_tariff_no_bess_vnd_per_kwh", "vat": "excluded", "metering_point": "inverter_output", "monthly_volume_rule": "min(actual, agreed)"}`, `effective_date: "2026-06-26"`, `supersedes: "decree57_20pct_cap"` (adjust key names to mirror whatever the decree57 file actually uses — copy its schema, change its values).
- [x] TASK-06-02: Register the new file in `data/vietnam/manifest.json` as a new entry; **do not** repoint existing consumers of the decree57 file — the old file stays for regime-stress comparisons. Add the manifest key the same way the other five files are declared.
- [ ] TASK-06-03: Add an optional inert field to the settlement contract: `surplus_price_cap_vnd_per_kwh: Optional[float] = None` on `ContractParams` in `src/python/reopt_pysam_vn/integration/settlement.py`, documented as "Decree 243 surplus price cap; not yet applied in settlement math — reserved for the surplus-trading model." **No computation change** — this protects Samsung parity (CON-001) while making the field available to the generic pipeline.
- [x] TASK-06-04: Layer-1 data validation: add the new file to whatever `tests/python/` data-validation covers `data/vietnam/*.json` (schema/envelope checks), plus a unit test loading it and asserting the values in TASK-06-01.
- [ ] TASK-06-05: Update stale claims: in `research/2026-06-23_bess-deck-claims.md` and (if tracked) `reports/dppa_july_2026_repo_check.md`, add a dated note that the 50% cap is now **enacted** under Decree 243 (both previously flagged it as draft). Append a line to `AGENTS.md` §5 noting the decree243 data file.

**File Changes**
- `data/vietnam/vn_export_rules_decree243.json` (create): per TASK-06-01.
- `data/vietnam/manifest.json` (modify): one new entry.
- `src/python/reopt_pysam_vn/integration/settlement.py` (modify): one new optional dataclass field, no logic change.
- `tests/python/...` (modify/create): validation + load test per TASK-06-04.
- `research/2026-06-23_bess-deck-claims.md`, `AGENTS.md` (modify): dated notes per TASK-06-05.

**Function Signatures**
- `ContractParams` gains field `surplus_price_cap_vnd_per_kwh: Optional[float] = None` — carried but unused by `compute_hourly_settlement` in this phase.

**Test Specs**
- Loading `data/vietnam/vn_export_rules_decree243.json` (utf-8-sig) → `data["surplus_cap_fraction"] == 0.50`, `data["bess_surplus_eligible"] is True`, `data["effective_date"] == "2026-06-26"`.
- Existing decree57 consumers unchanged: full suite green, Samsung parity bit-exact.
- `ContractParams(**existing_kwargs)` without the new field → constructs fine (default `None`).

**Dependencies**
- PHASE-02 (CI verifies the no-output-change claim).

**Exit Criteria**
- [ ] New data file + manifest entry committed; L1 validation green.
- [ ] Full suite green; parity tests bit-exact (proving the `ContractParams` change is inert).

**Phase Risks**
- **RISK-06-01:** `ContractParams` is constructed positionally somewhere, so appending a field breaks call sites — mitigation: add the field **last** with a default, and grep `ContractParams(` for positional construction before committing.

## Gotchas

- **Clear `PYTHONPATH` before pytest** (`$env:PYTHONPATH = ""`): a stray global value shadows the `.venv` and fails webapp tests with a `pydantic_core` import error.
- **Use `.venv\Scripts\python.exe`, never system Python** — PySAM 7.1.0 exists only in the repo venv (Python 3.12); system 3.14 silently falls back to synthetic solar profiles and will change numbers.
- **Samsung/TTC parity is bit-exact.** Two test files gate it. Any refactor near `dppa_samsung_ttc.py`, `settlement.py`, or the webapp analysis path must leave those tests untouched-green; "close" is failing.
- **`.gitignore` negations have burned this repo** (a loose `!reports/*sprint-*.html` once re-tracked unrelated files). Don't restructure ignore sections opportunistically; make only the minimal addition PHASE-01 needs and run `git status` after.
- **Before deleting/untracking anything, grep the bare name, not the path form** (`Regina`, not `regina/`) — tests build paths from segments. This is why `Regina.xlsx` stays tracked.
- **After any structural move, run the FULL Python suite**, not the subsystem's tests — subset runs have missed integration breakage here before.
- **In numeric comparators, guard `bool` before `int`** (Python `bool ⊂ int`) — relevant if TASK-02-04 touches the parity comparator.
- **JSON reads use `encoding="utf-8-sig"`** — new readers that use plain `utf-8` will explode on BOM'd files that currently work.
- **Strike sweeps run in US cents/kWh; tariffs in VND/kWh** — label chart axes from the data, and never convert implicitly.
- **CI yaml is bash; local commands are PowerShell** — don't paste `$env:` syntax into the workflow file.

## Verification Strategy

- **TEST-001 (PHASE-01):** `git ls-files | grep -i "\.pptx"` → empty; `git ls-files | grep Regina` → `scenarios/case_studies/regina/Regina.xlsx`.
- **TEST-002 (PHASE-02):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network" -q` → ends `0 failed`.
- **TEST-003 (PHASE-02):** `ruff check src/python tests scripts/python` → exit 0.
- **TEST-004 (PHASE-03):** with the app running, `curl.exe -s -o NUL -w "%{http_code}" -X POST http://127.0.0.1:8000/api/deals -F "case=X" -F "mode=onsite" -F "evil.key=1" -F "load_file=@tests/python/webapp/fixtures/<any load csv fixture>"` → `422`.
- **TEST-005 (PHASE-04):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/analysis/test_samsung_ttc_parity.py tests/python/webapp/test_golden_parity.py -q` → 0 failed (bit-exact parity preserved).
- **TEST-006 (PHASE-04):** submit an offsite deal via the form with **no** extracted upload → run reaches `state: "done"`; `result.json` contains a non-empty `base_settlement`.
- **TEST-007 (PHASE-05):** `curl.exe -s http://127.0.0.1:8000/static/map.js | findstr projectPrefillFields` → a match; run page of an offsite run contains `strike-sweep-chart`.
- **TEST-008 (PHASE-06):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network" -q` → 0 failed after the data + `ContractParams` change (proves inertness).
- **MANUAL-001:** NREL key rotated at the developer portal; old key returns 403 on a test call; local `NREL_API.env` updated. (Human action item — ASM-001.)
- **MANUAL-002:** In a browser: `/deals/new` → click catalog marker → "Use as deal site" → lat/lon/region inputs update and marker moves; submit; watch run complete; strike-sweep chart renders on the run page.
- **OBS-001:** GitHub Actions run visible and green on the default branch after each phase's merge.

## Risks and Alternatives

- **RISK-001:** Re-baselined goldens (PHASE-02) could hide a real regression that PHASE-04/05 then build on — mitigated by mandatory worktree bisection before re-baselining and by sequencing PHASE-02 strictly before PHASE-04.
- **RISK-002:** The generic offsite pipeline (PHASE-04) produces plausible-but-wrong economics for deals it wasn't calibrated on — mitigated by stamping `quality.orchestrator = "generic"` into every generic result and leaving `adder_sensitivity`/`regime_stress` visibly empty rather than fabricated.
- **RISK-003:** CI green becomes a false comfort because network-marked tests never run — mitigated by keeping the full-suite PowerShell runner as the documented pre-release gate and running it at each phase exit.
- **ALT-001:** Rewrite `dppa_samsung_ttc.py` into the generic pipeline — rejected: bit-exact parity gates make decomposition high-risk for zero analyst-visible gain; the registry + generic-fallback approach adds capability without touching the golden path.
- **ALT-002:** SQLite for run storage — rejected: single-user localhost design; the ordering fix is ~15 lines.
- **ALT-003:** Git history rewrite (`git filter-repo`) to purge the leaked key — rejected: rotation kills the credential's value; a rewrite breaks the existing worktree and any clones.
- **ALT-004:** Playwright E2E suite for the map UI — rejected as a CI gate: prior attempt hung on tile loading; server-rendered assertions + manual checks cover it.

## Suggested Next Step

Execute PHASE-01 (one short session — hygiene and the rotation action item), then PHASE-02; every later phase assumes CI is watching. Each phase's exit criteria are independently verifiable before the next begins.
