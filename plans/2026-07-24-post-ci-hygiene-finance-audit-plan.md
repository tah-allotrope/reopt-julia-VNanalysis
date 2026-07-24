---
title: "Post-CI Hygiene, Single Owner Finance Audit, Coverage Reporting, and Plans Sweep"
date: "2026-07-24"
status: "draft"
request: "research/2026-07-24-reopt-pysam-sixth-pass-brainstorm.md — turn the sixth-pass brainstorm's four action items into a multi-phase implementation plan"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-24-reopt-pysam-sixth-pass-brainstorm.md"
---

# Plan: Post-CI Hygiene, Single Owner Finance Audit, Coverage Reporting, and Plans Sweep

## Objective

With CI on `main` now genuinely green (confirmed live: GitHub Actions runs
`29942520141` and `29942791577` both `completed success`), close the four
concrete, low-risk items the 2026-07-24 brainstorm identified as ready to
execute: (1) the six-session-overdue security/hygiene cleanup (untracked
credentials-adjacent binaries, a broken `.gitignore` glob, dependency-file
duplication, undocumented key-rotation obligation), (2) a PySAM Single Owner
finance audit that answers whether the SAM reference-plant cost defaults
(led by a flat $2,866,500 construction-financing charge) have contaminated
numbers already used in the Samsung/TTC and CEBA client-facing deliverable
pipelines, (3) report-only test-coverage visibility to prioritize future
refactoring risk, and (4) a `plans/active/` hygiene sweep to stop a
22-file planning directory from silently drifting the same way
`activeContext.md` and `.gitignore` have drifted before in this repo's
history.

## Context Snapshot

- **Current state:** CI is green. Three deck `.pptx` files and two root
  screenshots remain tracked in git despite `.gitignore` entries; two
  `.gitignore` lines use unescaped bracket-glob syntax that does not match
  the filenames they are meant to ignore; `requirements.txt` duplicates
  `pyproject.toml`'s dependency list; a historically leaked NREL Developer
  API key (recoverable from commits `3911032` and `b14bc0b`) has no rotation
  record anywhere in the repo's docs. Separately,
  `src/python/reopt_pysam_vn/pysam/single_owner.py::_configure_financial_model`
  never touches twelve PySAM `Singleowner.FinancialParameters` fields that
  carry non-zero, ~100 MW-reference-plant cost defaults (verified live
  against the installed `nrel-pysam==7.1.0`: `construction_financing_cost` =
  `2866500.0`, `insurance_rate` = `0.5`, `cost_debt_fee` = `2.75`,
  `months_working_reserve` = `6.0`, `dscr_reserve_months` = `6.0`,
  `prop_tax_cost_assessed_percent` = `100.0`, `reserves_interest` = `1.75`;
  `cost_debt_closing`, `equip1_reserve_cost`, `equip2_reserve_cost`,
  `equip3_reserve_cost`, and `salvage_percentage` are already `0.0` by
  default). `run_single_owner_model` is called directly from
  `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py:771` (the
  Samsung/TTC strike-sweep path) and, per a live `grep`, from at least 18
  other files including five under `scripts/python/integration/ceba_deck/`
  — the same pipeline that verifies the CEBA/DPPA July 2026 client deck.
  No test currently measures what fraction of the ~12,300-line
  `src/python/` package is exercised by the 62 test files under
  `tests/python/`. `plans/active/` holds 22 plan files dating back to
  2026-04-23; at least 13 correspond to features with either an explicit
  `reports/*final*.html`/`.md` deliverable, a fully-checked task list, or an
  explicit "completed" note in `activeContext.md`, yet remain in `active/`.
- **Desired state:** `git ls-files` contains no deck binaries or root
  screenshots; the `.gitignore` bracket-glob patterns actually match the
  filenames they name; there is one dependency source of truth
  (`pyproject.toml`); the key-rotation obligation is written down in
  `README.md` and `activeContext.md` with both source commit hashes. PySAM
  `Singleowner` finance runs support an explicit, tested, opt-in
  `zero_reference_plant_defaults` flag that zeroes the twelve reference-plant
  fields with no change to default (flag-off) behavior; a written audit
  report enumerates every caller of `run_single_owner_model` and states,
  for each, whether its tracked/published outputs carry the untouched SAM
  defaults, with an explicit "decision required" section for whoever owns
  the Samsung/TTC and CEBA client relationships. CI reports (non-blocking)
  test coverage on every push. `plans/active/` contains only plans without
  unambiguous shipped evidence; the 13 confirmed-shipped plans live in
  `plans/archive/` instead, reachable by their unchanged filenames.
- **Key repo surfaces:** `.gitignore`, `requirements.txt`, `README.md`,
  `activeContext.md`, `ceba-review/*.pptx`, `phase04_new_deal_*.png`,
  `tests/python/test_repo_invariants.py`,
  `src/python/reopt_pysam_vn/pysam/single_owner.py`,
  `src/python/reopt_pysam_vn/integration/{dppa_samsung_ttc.py,dppa_case_2.py,bridge.py,strike_search.py}`,
  `scripts/python/integration/ceba_deck/`,
  `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py`,
  `tests/python/pysam/test_single_owner_phase4.py`,
  `.github/workflows/ci.yml`, `pyproject.toml`, `plans/active/`,
  `plans/archive/`, `plans/README.md`.
- **Out of scope:** Flipping `zero_reference_plant_defaults` to `True` by
  default anywhere (a default flip could silently shift Samsung/TTC golden
  numbers and needs a human decision, made only after the audit report in
  this plan exists); restating or regenerating any golden/parity fixture,
  including `examples/samsung-ttc_combined-decision.example.json`;
  rewriting git history to purge the leaked NREL key (rotation, not history
  scrubbing, is the remediation); the Decree 146/2025 two-part tariff
  Ca-re-pricing fix (separately specified in
  `plans/2026-07-17-truth-and-correctness-sprint-plan.md` PHASE-03); the
  config-driven case runner / script-sprawl decomposition, Julia
  archive-in-place decision, frozen-resource offline solve mode, and
  webapp→deck export endpoint (all still valid, still larger, and
  deliberately not bundled into this smaller hygiene-and-audit plan);
  enforcing a minimum coverage percentage (report-only this phase); actually
  rotating the NREL key (requires the human account owner at
  developer.nlr.gov — this plan only documents the requirement, per the
  standing decision already recorded in the prior sprint plan).

## Environment & Conventions

- **Stack:** Python 3.10+ (`pyproject.toml` `requires-python = ">=3.10"`);
  local development uses a repo-local virtualenv at `.venv` running Python
  3.12 with `nrel-pysam==7.1.0` installed — the system Python on this
  machine has no PySAM wheel and PySAM-dependent tests skip automatically
  there via `pytest.importorskip("PySAM")`. Package layout: setuptools,
  `package-dir = {"" = "src/python"}`. CI runs on `ubuntu-latest` with
  Python 3.12 via GitHub Actions (`.github/workflows/ci.yml`).
- **Setup:** From repo root, PowerShell:
  `.venv\Scripts\python.exe -m pip install -e ".[webapp]"` (installs the
  `webapp` extra too; add `pytest pytest-cov` if not already present:
  `.venv\Scripts\python.exe -m pip install pytest pytest-cov`).
- **Build / Run:** No build step for the library. Not needed for this plan
  (no webapp or solver changes).
- **Test:** Full suite:
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q`
  — single test:
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/pysam/test_single_owner_clean_slate.py -q`
  — CI's exact portable-suite filter:
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q`
- **Conventions & traps:**
  - **`PYTHONPATH` gotcha:** a stray global `PYTHONPATH` environment variable
    on some machines shadows the `.venv`'s own `fastapi`/`pydantic` install
    and produces `ModuleNotFoundError: pydantic_core._pydantic_core` in
    webapp tests. Always clear it (`$env:PYTHONPATH = ""`) before every
    pytest invocation in this plan; pytest resolves the package itself via
    `pythonpath = ["src/python"]` already set in `pyproject.toml`.
  - All commands shown here are **PowerShell** (this is a Windows-first
    repo — see `activeContext.md`). CI (`.github/workflows/ci.yml`) runs on
    `ubuntu-latest` in bash — never paste `$env:`-style syntax into that
    file; use plain shell syntax there instead.
  - **`.gitignore` edits are precisely scoped only** — a prior loose
    negation in this repo once re-tracked unrelated report files. Touch only
    the exact lines named in PHASE-01 below and run `git status` immediately
    after any `.gitignore` edit.
  - **`git rm --cached` vs `git rm`:** the three deck `.pptx` files are
    untracked but kept on disk (`--cached`); the two root PNGs and
    `requirements.txt` are fully deleted (plain `git rm`). Do not swap these.
  - **SAM percent-vs-fraction convention:** every PySAM `Singleowner` rate
    field takes a **percent** value (e.g. `50.0` means 50%), not a fraction;
    `_configure_financial_model` already multiplies stored fractions by
    `100.0` before assignment. The twelve reference-plant fields in this
    plan's PHASE-02 are set to the literal float `0.0`, which is
    percent-or-fraction-agnostic (zero either way), so no conversion is
    needed there.
  - **`xfail(strict=True)` is a deliberate tripwire, not a bug:**
    `tests/python/test_repo_invariants.py::test_no_root_level_binaries`
    currently carries `@pytest.mark.xfail(strict=True, ...)` specifically so
    that forgetting to remove the decorator after untracking the PNGs turns
    into a hard test failure (an unexpectedly-passing strict xfail errors)
    rather than a silent gap. PHASE-01 must remove that decorator in the
    same change that untracks the PNGs.
- **Repo map:**
  - `src/python/reopt_pysam_vn/pysam/single_owner.py` — `SingleOwnerInputs`
    dataclass (line 14), `build_single_owner_inputs()` (line 39),
    `_configure_financial_model()` (line 63, sets `Revenue`, `SystemCosts`,
    `FinancialParameters.{analysis_period,debt_option,debt_percent,
    federal_tax_rate,state_tax_rate,real_discount_rate,inflation_rate,
    term_int_rate,term_tenor}`, `Depreciation.*`, `TaxCreditIncentives.*` —
    never touches the twelve reference-plant fields), `run_single_owner_model()`
    (line 142, builds `PySAM.CustomGeneration`/`Grid`/`Utilityrate5`/`Singleowner`
    models, executes them, returns a normalized dict via
    `extract_single_owner_outputs()` from `pysam/metrics.py`).
  - `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py:771` — inside
    a strike-sweep function, imports and calls `run_single_owner_model`
    against inputs from `build_dppa_case_2_single_owner_inputs()`
    (`integration/bridge.py`) — this is the Samsung/TTC flagship case,
    bit-exact-parity-gated by `tests/python/analysis/test_samsung_ttc_parity.py`
    and `tests/python/webapp/test_golden_parity.py` against
    `examples/samsung-ttc_combined-decision.example.json`.
  - A live `grep -rln "run_single_owner_model\|_configure_financial_model\|SingleOwnerInputs" src/ scripts/ tests/`
    (run 2026-07-24) additionally returns:
    `src/python/reopt_pysam_vn/integration/{bridge.py,dppa_case_2.py,strike_search.py}`,
    `scripts/python/integration/{analyze_ninhsim_dppa_case_2_phase_f.py,
    analyze_saigon18_dppa_case_3_phase_f.py,analyze_saigon18_dppa_case_3_phase_f_22kv.py,
    generate_ninhsim_dppa_case_2_phase_f_report.py,run_factory_a_pysam.py,
    run_ninhsim_single_owner.py,run_ninhsim_solar_storage_60pct_single_owner.py,
    verify_ceba_dppa_deck.py}`,
    `scripts/python/integration/ceba_deck/{calibrate_cases.py,deck_checks.py,
    july_deck_checks.py,july_runners.py,sweep_56.py}`,
    `scripts/python/pysam/{2026-07-17_kbc_proforma_pysam_crosscheck.py,run_single_owner_smoke.py}`,
    `tests/python/integration/test_dppa_samsung_ttc_phase_03.py`, and
    `tests/python/pysam/test_single_owner_phase4.py`. The `ceba_deck/` hits
    mean the CEBA/DPPA July 2026 client-deck verification pipeline
    (`ceba-review/`) sits on the same call graph as the unaudited defaults.
  - `tests/python/pysam/test_single_owner_phase4.py` — existing test
    pattern to follow: non-PySAM tests first, then a module-level
    `PySAM = pytest.importorskip("PySAM")` line (line 214), then PySAM-
    dependent tests below it; `REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent`.
  - `tests/python/test_repo_invariants.py` — three invariant tests reading
    `git ls-files` via `subprocess`; `test_no_root_level_binaries` (line 55)
    carries the strict-xfail tripwire described above.
  - `.gitignore` lines 93-100 — the "July 2026 deck verification" section;
    line 96 (`ceba-review/*[repo-checked].pptx`) and line 98
    (`ceba-review/*[*reviewed*].pptx`) use `[...]` as literal glob character
    classes, not escaped literal brackets, so they do not match the actual
    tracked filenames (which contain the literal substrings `[repo-checked]`
    and `[reviewed]`).
  - `plans/README.md` — states the convention: current plans in
    `plans/active/`, superseded/historical plans in `plans/archive/`, one
    canonical editable copy per plan.

## Research Inputs

- From `research/2026-07-24-reopt-pysam-sixth-pass-brainstorm.md`:
  - CI on `main` is now confirmed green (`gh run list` showed runs
    `29942520141` and `29942791577` both `completed success`) — this plan's
    phases are additive hygiene/audit work, not CI-recovery work.
  - PHASE-02 of `plans/2026-07-17-truth-and-correctness-sprint-plan.md`
    (security/hygiene: untrack binaries, fix `.gitignore`, drop
    `requirements.txt`, document key rotation) has been the single most
    repeatedly-flagged, lowest-risk, fully-specified, unexecuted item across
    six consecutive analysis sessions — re-verified live as still open
    (`git ls-files` still shows the three `.pptx` files and two root PNGs
    tracked; `requirements.txt` still present; no "rotat" mention anywhere
    in `README.md`/`activeContext.md`/`docs/*.md`).
  - The PySAM Single Owner reference-plant-defaults gap
    (`_configure_financial_model` never sets twelve `FinancialParameters`
    fields SAM defaults to non-zero ~100 MW-reference-plant values) sits
    directly on the call path from `dppa_samsung_ttc.py:771` through to
    `present/Allotrope DPPA insights.pptx` and
    `reports/2026-06-04-final-samsung-ttc-dppa.html` — real, dated,
    client-facing-shaped deliverables, not just test fixtures. This
    reframes the existing audit task (already specified in
    `plans/2026-07-17-truth-and-correctness-sprint-plan.md` PHASE-04's
    TASK-04-03) from "correctness nice-to-have" to "unresolved
    external-facing risk question," which is why it is included in this
    plan ahead of lower-stakes items.
  - Smaller findings folded into this plan: no test-coverage measurement
    exists anywhere in the toolchain (report-only `pytest-cov` addition is
    cheap and safe); `plans/active/` holds plans for already-shipped
    features with no rotation to `plans/archive/`, mirroring a documented,
    previously-fixed drift pattern in `activeContext.md` itself.
  - Explicitly out of scope per that brainstorm and folded into this plan's
    own Out of Scope: the config-driven case runner, Julia archive decision,
    webapp→deck export endpoint, and the two-part tariff fix — all larger,
    already separately specified, and correctly deferred.

## Assumptions and Constraints

- **ASM-001:** The three currently-tracked `.pptx` files are exactly
  `ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx`,
  `ceba-review/cong bess session [reviewed].pptx`, and
  `ceba-review/cong bess session.pptx` (verified via `git ls-files | grep -i "\.pptx$"`
  on 2026-07-24). — **BINDING DEFAULT:** if `git ls-files` returns a
  different set at execution time, untrack whatever it actually returns
  instead of this literal list, and update the `.gitignore` glob fix
  (TASK-01-02) to match the real filenames' bracket substrings.
- **ASM-002:** The installed `.venv` PySAM version is `7.1.0` (verified via
  a live Python check on 2026-07-24: `insurance_rate=0.5`,
  `construction_financing_cost=2866500.0`, `cost_debt_fee=2.75`,
  `cost_debt_closing=0.0`, `months_working_reserve=6.0`,
  `dscr_reserve_months=6.0`, `equip1_reserve_cost=0.0`,
  `equip2_reserve_cost=0.0`, `equip3_reserve_cost=0.0`,
  `prop_tax_cost_assessed_percent=100.0`, `reserves_interest=1.75`,
  `salvage_percentage=0.0`, read directly off a
  `PySAM.Singleowner.from_existing(...)` instance). — **BINDING DEFAULT:**
  if the installed version differs, re-run the same live check
  (`FinancialParameters` field-by-field read, see PHASE-02 TASK-02-01) and
  use whatever values it prints as the regression-guard expectations instead
  of the ones recorded here.
- **ASM-003:** No caller of `run_single_owner_model` currently passes a
  `zero_reference_plant_defaults` keyword (the field does not exist yet) —
  confirmed by reading `single_owner.py` in full; adding it as a new
  dataclass field defaulting to `False` cannot break any existing caller.
- **ASM-004:** At least one of the eighteen files found by the PHASE-02
  audit grep is a genuine PPA/finance-analysis entry point suitable as the
  audit's "representative small project" comparison run (flag on vs off).
  — **BINDING DEFAULT:** use
  `scripts/python/integration/run_ninhsim_solar_storage_60pct_single_owner.py`
  or, if it requires artifacts unavailable at execution time, fall back to
  the synthetic `build_single_owner_inputs(system_capacity_kw=1000)` smoke
  case already exercised by
  `tests/python/pysam/test_single_owner_phase4.py::test_run_single_owner_model_returns_canonical_result_shape`
  — either is acceptable evidence for the audit; record which one was used.
- **ASM-005:** The 13 plans identified in PHASE-04 as having unambiguous
  shipped evidence (see that phase's task list) were correctly classified
  as of 2026-07-24 by matching each plan's dated slug against
  `reports/*final*.{html,md}` filenames, fully-checked (`- [x]`) task lists,
  or an explicit "completed" statement in `activeContext.md`. —
  **BINDING DEFAULT:** if the executor finds contradicting evidence for any
  one of the 13 (e.g. a plan file itself states unfinished work, or its
  linked report is missing), leave that specific plan in `plans/active/`
  and proceed with the rest; do not block the whole phase on one
  reclassification.
- **CON-001:** Samsung/TTC bit-exact parity must not change:
  `tests/python/webapp/test_golden_parity.py` must pass unmodified at every
  commit in this plan, and `examples/samsung-ttc_combined-decision.example.json`
  must never be edited. PHASE-02's clean-slate flag defaults to `False`
  specifically to guarantee this.
- **CON-002:** No git-history rewrite anywhere in this plan. Untracking
  always means `git rm --cached` (file stays on disk); full deletion
  (`git rm`) is used only for the root PNGs and `requirements.txt`, which
  are genuinely superseded/redundant, not credentials-adjacent.
- **CON-003:** All new or modified JSON/text readers in this plan use
  `encoding="utf-8-sig"` if they read any of the repo's existing
  `utf-8-sig`-encoded data files; none of this plan's phases add a new JSON
  reader, so this constraint is inherited but not newly exercised.
- **CON-004:** New library code goes under `src/python/reopt_pysam_vn/`;
  the `mypy` CI gate covers only `analysis/` and `webapp/` — PHASE-02's new
  code in `pysam/single_owner.py` is outside that gate (matching the
  existing, unchanged `[[tool.mypy.overrides]]` block in `pyproject.toml`)
  but should still carry full type hints to match house style.
- **DEC-001:** PHASE-02 builds and lands the `zero_reference_plant_defaults`
  flag itself (not just the audit) because the audit task
  (per the source plan's own TASK-04-03 design) needs the flag to exist in
  order to compute an on/off IRR/NPV delta for the "decision required"
  section — the audit cannot be meaningfully separated from the minimal
  flag implementation.
- **DEC-002:** The flag stays default-`False` (legacy behavior preserved)
  and this plan does not flip any default or touch any golden file — the
  audit's "decision required" section is explicitly addressed to whoever
  owns the Samsung/TTC and CEBA client relationships, not resolved here.

## Specification

**PySAM Singleowner reference-plant fields zeroed by `apply_clean_slate_financials`
(PHASE-02).** All twelve fields live on `financial_model.FinancialParameters`
(a PySAM `Singleowner` model instance). Each is set to the literal float
`0.0` when the flag is on; the right-hand column is the value verified live
against the installed `nrel-pysam==7.1.0` on 2026-07-24 (ASM-002's binding
default: re-verify at execution time and use whatever is actually installed
if it differs):

| Field | Meaning (plain English) | Verified SAM default (2026-07-24) |
|---|---|---|
| `insurance_rate` | Annual insurance cost as a percent of installed cost | `0.5` |
| `construction_financing_cost` | Flat one-time construction-financing charge, USD | `2866500.0` |
| `cost_debt_fee` | Up-front debt origination fee, percent of debt principal | `2.75` |
| `cost_debt_closing` | Up-front debt closing cost, USD | `0.0` (already zero) |
| `months_working_reserve` | Working-capital reserve sized in months of operating cost | `6.0` |
| `dscr_reserve_months` | Debt-service-coverage reserve sized in months of debt service | `6.0` |
| `equip1_reserve_cost` | Major-equipment reserve #1, USD | `0.0` (already zero) |
| `equip2_reserve_cost` | Major-equipment reserve #2, USD | `0.0` (already zero) |
| `equip3_reserve_cost` | Major-equipment reserve #3, USD | `0.0` (already zero) |
| `prop_tax_cost_assessed_percent` | Property-tax basis as a percent of installed cost | `100.0` |
| `reserves_interest` | Interest rate earned on reserve account balances, percent | `1.75` |
| `salvage_percentage` | End-of-life salvage value as a percent of installed cost | `0.0` (already zero) |

Five of the twelve — `cost_debt_closing`, `equip1_reserve_cost`,
`equip2_reserve_cost`, `equip3_reserve_cost`, and `salvage_percentage` — are
already `0.0` under SAM's own defaults and are included in
`apply_clean_slate_financials` only for completeness/idempotency, not
because they currently contaminate any result. The remaining seven
(`insurance_rate`, `construction_financing_cost`, `cost_debt_fee`,
`months_working_reserve`, `dscr_reserve_months`,
`prop_tax_cost_assessed_percent`, `reserves_interest`) are non-zero today and
are the ones TASK-02-06's audit comparison must show a measurable NPV/IRR
effect from zeroing.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Security & workspace hygiene: untrack binaries, fix `.gitignore`, single dependency source, document key rotation | None | Clean `git ls-files`; working `.gitignore` globs; rotation note in `README.md`/`activeContext.md` |
| PHASE-02 | PySAM Single Owner clean-slate flag (opt-in, tested) + contamination audit across all 18 callers | None (independent of PHASE-01; both are safe to run in parallel or either order) | `zero_reference_plant_defaults` flag + tests; `reports/2026-07-24-single-owner-defaults-audit.md` |
| PHASE-03 | Report-only pytest coverage in CI | None | `pytest-cov` wired into `.github/workflows/ci.yml`; `[tool.coverage.run]` config |
| PHASE-04 | Archive the 13 confirmed-shipped plans out of `plans/active/` | None | `plans/archive/` gains 13 files; `plans/active/` shrinks from 22 to 9 |

## Detailed Phases

### PHASE-01 - Security & Workspace Hygiene

**Goal**
`git ls-files` contains no deck binaries or root screenshots, `.gitignore`
patterns actually match the files they name, dependencies have one source of
truth, and the leaked-key rotation obligation is written down where the
account owner will see it.

**Tasks**
- [ ] TASK-01-01: Untrack the three deck binaries (files stay on disk, per
  CON-002):
  ```powershell
  git rm --cached "ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx" "ceba-review/cong bess session [reviewed].pptx" "ceba-review/cong bess session.pptx"
  ```
- [ ] TASK-01-02: Fix the two `.gitignore` bracket-glob bugs. In the
  "July 2026 deck verification" section (currently lines 93-100), change:
  - `ceba-review/*[repo-checked].pptx` → `ceba-review/*\[repo-checked\].pptx`
  - `ceba-review/*[*reviewed*].pptx` → `ceba-review/*\[reviewed\].pptx`

  Leave every other line in `.gitignore` untouched. Verify each of the three
  untracked filenames now matches an ignore rule:
  ```powershell
  git check-ignore -v "ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx"
  git check-ignore -v "ceba-review/cong bess session [reviewed].pptx"
  git check-ignore -v "ceba-review/cong bess session.pptx"
  ```
  Each command must print a matching rule and exit `0`.
- [ ] TASK-01-03: Delete the tracked root screenshots (history retains them;
  they are superseded webapp-session evidence from the 2026-07-06 map site
  picker work):
  ```powershell
  git rm phase04_new_deal_initial.png phase04_new_deal_scrolled.png
  ```
- [ ] TASK-01-04: Remove the strict-xfail tripwire in
  `tests/python/test_repo_invariants.py` now that the root PNGs are
  untracked — delete the `@pytest.mark.xfail(reason="...", strict=True)`
  decorator directly above `def test_no_root_level_binaries():` (currently
  lines 51-54), leaving the test function itself unchanged. Do not touch
  `test_no_flat_python_scripts` or `test_no_tracked_artifacts` in the same
  file.
- [ ] TASK-01-05: Single dependency source:
  ```powershell
  git rm requirements.txt
  ```
  In `README.md`, under the `## Python Setup` heading (currently lines
  181-190), replace the two-line install block:
  ```
  python -m pip install -r requirements.txt
  python -m pip install -e .
  ```
  with the single line:
  ```
  python -m pip install -e ".[webapp]"
  ```
  Leave the two bullet points below that block (about PySAM scaffolding and
  test skipping) unchanged.
- [ ] TASK-01-06: Document the key-rotation requirement. Add a new
  subsection titled `### Security note — API key rotation required`
  immediately after the `## Python Setup` section in `README.md`, stating:
  an NREL Developer API key was committed historically (commits `3911032`
  and `b14bc0b`) and remains recoverable from git history; the account
  owner must rotate it at the NREL Developer Network account page and
  update the local, git-ignored `NREL_API.env`; no history rewrite is
  planned (rotation is the remediation, per CON-002). Add a matching
  one-line note to `activeContext.md` under its `## Environment` section
  (currently lines 47-56): `**Security:** an NREL API key committed
  historically (commits 3911032, b14bc0b) has not been confirmed rotated as
  of 2026-07-24 — see README.md's "API key rotation required" note.`
- [ ] TASK-01-07: Run the full local suite, confirm `git status` shows no
  unexpected re-tracked files, commit.

**File Changes**
- `.gitignore` (modify): escape the two bracket-glob lines exactly as in
  TASK-01-02. No other line changes.
- `README.md` (modify): Python Setup consolidation (TASK-01-05) + new
  Security note subsection (TASK-01-06). Leave all other sections alone.
- `activeContext.md` (modify): one new line under `## Environment`
  (TASK-01-06).
- `requirements.txt` (delete via `git rm`).
- `phase04_new_deal_initial.png`, `phase04_new_deal_scrolled.png` (delete
  via `git rm`).
- `ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx`,
  `ceba-review/cong bess session [reviewed].pptx`,
  `ceba-review/cong bess session.pptx` (untrack via `git rm --cached`; files
  remain on disk).
- `tests/python/test_repo_invariants.py` (modify): remove the strict-xfail
  decorator on `test_no_root_level_binaries` only.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
- `git ls-files | grep -i "\.pptx$"` → empty output.
- `git ls-files | grep -E "^\w.*\.png$"` → empty output.
- `git ls-files requirements.txt` → empty output.
- `git check-ignore -v "ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx"` → prints a matching rule, exit code `0` (same for the other two `.pptx` names in TASK-01-02).
- `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/test_repo_invariants.py -q` → all three tests pass, none marked `xfail`.

**Dependencies**
None (first phase; independent of PHASE-02/03/04).

**Exit Criteria**
- [ ] All five Test Specs above hold.
- [ ] Full local suite: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` → `0 failed`.
- [ ] `README.md` contains the rotation note with both commit hashes
  (`3911032`, `b14bc0b`).
- [ ] The next GitHub Actions run on `main` after this phase's push
  concludes `success` (`gh run list --limit 1`).

**Phase Risks**
- **RISK-01-01:** A test or script reads one of the untracked `.pptx` files
  by its tracked git path and breaks on a fresh clone. Mitigation: the
  files remain on disk locally (CON-002); the deck-generation pipeline
  (`scripts/python/integration/generate_samsung_ttc_deck.py` and similar)
  already treats deck binaries as local-only, regenerable inputs per the
  2026-06-12 de-bloat policy recorded in `.gitignore`'s own comments; the
  full-suite run in TASK-01-07 would surface any tracked-path dependency.

### PHASE-02 - PySAM Single Owner Clean-Slate Flag + Contamination Audit

**Goal**
Small Vietnam C&I / DPPA projects can run the PySAM Single Owner finance
model without inheriting SAM's ~100 MW-reference-plant cost defaults, via an
explicit, tested, opt-in flag — and a written audit states, for every one of
the eighteen callers found in this repo, whether its tracked or published
outputs carry those un-zeroed defaults, without changing any golden number
or flipping any default.

**Tasks**
- [ ] TASK-02-01 (confirm, no code yet): Re-verify the twelve field values
  against the locally-installed PySAM before writing any test expectation,
  in case ASM-002's recorded values are stale by execution time:
  ```powershell
  .venv\Scripts\python.exe -c "import PySAM.CustomGeneration as cg; import PySAM.Singleowner as so; sm = cg.default('CustomGenerationProfileNone'); fm = so.from_existing(sm, 'CustomGenerationProfileSingleOwner'); [print(f, getattr(fm.FinancialParameters, f)) for f in ['insurance_rate','construction_financing_cost','cost_debt_fee','cost_debt_closing','months_working_reserve','dscr_reserve_months','equip1_reserve_cost','equip2_reserve_cost','equip3_reserve_cost','prop_tax_cost_assessed_percent','reserves_interest','salvage_percentage']]"
  ```
  Use whatever this prints as the regression-guard expectations in
  TASK-02-03's tests (ASM-002's binding default).
- [ ] TASK-02-02 (RED): Create `tests/python/pysam/test_single_owner_clean_slate.py`
  with the failing tests in Test Specs below. Follow the existing pattern
  in `tests/python/pysam/test_single_owner_phase4.py`: plain tests first,
  then a module-level `PySAM = pytest.importorskip("PySAM")` line, then
  PySAM-dependent tests. Run and confirm they fail (module does not exist
  yet / assertions fail against current zero-flag behavior).
- [ ] TASK-02-03 (GREEN): In `src/python/reopt_pysam_vn/pysam/single_owner.py`:
  - Add a new field `zero_reference_plant_defaults: bool = False` to the
    `SingleOwnerInputs` dataclass (after `depreciation_schedule`, before
    `metadata`).
  - Add a new module-level function `apply_clean_slate_financials(financial_model) -> None`
    that sets each of the twelve fields listed in `## Specification` below
    to the literal float `0.0` via plain `setattr`-equivalent attribute
    assignment (so a renamed/missing PySAM attribute raises loudly rather
    than being silently skipped).
  - At the very end of `_configure_financial_model` (after the existing
    `TaxCreditIncentives.*` assignments, before the function returns), add:
    ```python
    if inputs.zero_reference_plant_defaults:
        apply_clean_slate_financials(financial_model)
    ```
  - In `run_single_owner_model`'s returned dict, add
    `"zero_reference_plant_defaults": bool(inputs.zero_reference_plant_defaults)`
    to the existing `"inputs"` sub-dict, and, only when the flag is `True`,
    add a `"clean_slate": "US SAM reference-plant cost defaults zeroed; see reports/2026-07-24-single-owner-defaults-audit.md"`
    entry to the existing `"notes"` sub-dict (leave the existing
    `"phase_scope"` and `"irr_warning"` note strings unchanged).
- [ ] TASK-02-04: Run the new tests, confirm green; run the full local
  suite; confirm `tests/python/webapp/test_golden_parity.py` still passes
  with zero diff (`git diff --stat examples/` → no output).
- [ ] TASK-02-05 (audit, read-only, no code changes): Re-run the caller
  grep to get the authoritative list at execution time:
  ```powershell
  git grep -l "run_single_owner_model\|_configure_financial_model\|SingleOwnerInputs" -- src/ scripts/ tests/
  ```
  For each file returned (expect at least the eighteen listed in this
  plan's Repo Map, excluding `single_owner.py` itself), read enough of it
  to classify: (a) does it call `run_single_owner_model` at all, directly
  or via a builder in `bridge.py`; (b) if so, does it pass
  `zero_reference_plant_defaults=True` (expect: no caller does, since the
  flag is brand new); (c) does its output feed a tracked file under
  `reports/`, `examples/`, or `present/` (grep each script for its own
  output-write path, e.g. `open(..., "w")` or `json.dump`/`Path(...).write_text`
  calls, and check whether the target path matches a tracked file via
  `git ls-files -- <path-prefix>`).
- [ ] TASK-02-06 (audit, one comparison run): Using
  ASM-004's chosen representative case, run
  `run_single_owner_model` twice — once with
  `zero_reference_plant_defaults=False` (default) and once with `True` —
  holding every other input identical, and record the
  `project_return_aftertax_npv_usd` and `project_return_aftertax_irr_fraction`
  delta between the two runs in the audit report.
- [ ] TASK-02-07: Write `reports/2026-07-24-single-owner-defaults-audit.md`
  containing: (1) a caller table (file path, calls `run_single_owner_model`
  Y/N, feeds a tracked deliverable Y/N + which one, verdict), (2) the
  TASK-02-06 NPV/IRR delta with both numbers and the case used, (3) an
  explicit `## Decision required` section addressed to whoever owns the
  Samsung/TTC and CEBA client relationships, stating plainly that the
  Samsung/TTC strike-sweep path (`dppa_samsung_ttc.py:771`) and the CEBA
  deck verification pipeline (`scripts/python/integration/ceba_deck/*.py`)
  both call into the unaudited-by-default Single Owner path, and asking
  them to confirm whether any number already shown to Samsung, TTC, or CEBA
  needs re-review — with an explicit statement that this plan makes no
  golden-file change and takes no position on whether such a re-review is
  required, only that the facts warrant asking.
- [ ] TASK-02-08: One-line docstring update in
  `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py`
  pointing its `run_single_owner_model_clean` reference at the new
  `zero_reference_plant_defaults` flag as the durable, library-level
  replacement for its ad hoc reimplementation — no behavior change to that
  script.
- [ ] TASK-02-09: Full suite; confirm CI green.

**File Changes**
- `src/python/reopt_pysam_vn/pysam/single_owner.py` (modify): add the
  dataclass field, the `apply_clean_slate_financials` function, the
  conditional call inside `_configure_financial_model`, and the two output-
  dict additions in `run_single_owner_model`. Leave every existing field
  assignment in `_configure_financial_model` exactly as-is, including
  order.
- `tests/python/pysam/test_single_owner_clean_slate.py` (create): specs
  below.
- `reports/2026-07-24-single-owner-defaults-audit.md` (create): audit
  findings + decision-required section, per TASK-02-07. (`reports/*.md`
  files are tracked in this repo; `reports/*.html` are not.)
- `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py`
  (modify): one docstring line per TASK-02-08.

**Function Signatures**
- `apply_clean_slate_financials(financial_model) -> None` — sets each of the
  twelve `FinancialParameters` fields listed in `## Specification` to the
  literal float `0.0` on a PySAM `Singleowner`-derived financial model
  in-place; returns nothing; raises `AttributeError` if any named field is
  missing on the passed model (deliberately not swallowed).
- `SingleOwnerInputs.zero_reference_plant_defaults: bool = False` — new
  dataclass field; when `True`, `run_single_owner_model` produces finance
  outputs with the twelve US reference-plant cost defaults zeroed.

**Test Specs**
- Default-off regression guard: build the models exactly as
  `run_single_owner_model` does (or call `_configure_financial_model`
  directly against a model built the same way), using
  `build_single_owner_inputs(1000.0)` (flag left at its default `False`) →
  `financial_model.FinancialParameters.construction_financing_cost == 2866500.0`
  and `financial_model.FinancialParameters.insurance_rate == 0.5` (or
  whatever TASK-02-01 actually prints) — proving legacy behavior is
  byte-identical to today.
- Flag-on zeroing: same setup with
  `build_single_owner_inputs(1000.0, zero_reference_plant_defaults=True)` →
  each of the twelve fields in `## Specification` reads exactly `0.0` after
  `_configure_financial_model` runs.
- End-to-end direction: call `run_single_owner_model` twice on identical
  small-project inputs (`system_capacity_kw=1000.0`,
  `installed_cost_usd=550_000.0`, `ppa_price_input_usd_per_kwh=0.065`,
  defaults otherwise), flag off vs on →
  `outputs["project_return_aftertax_npv_usd"]` is strictly greater in the
  flag-on run than the flag-off run (removing a real cost cannot lower
  NPV); the flag-on run's `results["inputs"]["zero_reference_plant_defaults"]`
  is `True` and the flag-off run's is `False`.
- Serialization: the flag-off run's `results["notes"]` dict does NOT
  contain a `"clean_slate"` key; the flag-on run's does, with the exact
  string from TASK-02-03.
- Audit report existence: `Path("reports/2026-07-24-single-owner-defaults-audit.md").exists()`
  is `True` and the file contains the literal substring
  `dppa_samsung_ttc.py` and the literal substring `ceba_deck`.

**Dependencies**
None (independent of PHASE-01, PHASE-03, PHASE-04; requires only the local
`.venv` with PySAM 7.1.0 installed).

**Exit Criteria**
- [ ] New tests in `test_single_owner_clean_slate.py` pass locally.
- [ ] Full local suite: `0 failed`.
- [ ] `tests/python/webapp/test_golden_parity.py` passes with
  `git diff --stat examples/` producing no output (no golden change).
- [ ] `reports/2026-07-24-single-owner-defaults-audit.md` exists, lists
  every file the TASK-02-05 grep returned, and contains a
  `## Decision required` section naming both `dppa_samsung_ttc.py` and the
  `ceba_deck/` scripts explicitly.
- [ ] The next GitHub Actions run on `main` after this phase's push
  concludes `success`.

**Phase Risks**
- **RISK-02-01:** The audit's TASK-02-06 comparison run reveals the
  Samsung/TTC golden fixture itself was generated with the un-zeroed
  defaults baked in. Mitigation: by design this phase only *reports* that
  finding in the audit's `## Decision required` section (CON-001/DEC-002
  forbid touching the golden file here) — restatement, if ever warranted,
  is an explicit, separate, human-approved follow-on change.
- **RISK-02-02:** A PySAM attribute name in the twelve-field list differs
  from what TASK-02-01 finds at execution time (version drift). Mitigation:
  TASK-02-01 re-verifies live before any test is written (ASM-002's binding
  default), and `apply_clean_slate_financials` uses plain attribute
  assignment so a missing/renamed attribute raises immediately instead of
  silently no-op'ing.

### PHASE-03 - Report-Only Test Coverage in CI

**Goal**
Every CI run on `main` reports what fraction of `src/python/reopt_pysam_vn/`
the portable test suite actually exercises, without blocking or gating on
any threshold — turning "552+ tests pass" from a raw count into an actual
prioritization signal for future refactoring risk (e.g. Theme-A script-
sprawl decomposition work referenced in prior brainstorms, out of scope
here).

**Tasks**
- [ ] TASK-03-01: Add `[tool.coverage.run]` to `pyproject.toml`:
  ```toml
  [tool.coverage.run]
  source = ["reopt_pysam_vn"]
  omit = ["*/webapp/static/*", "*/__pycache__/*"]
  ```
  Place this new table immediately after the existing
  `[[tool.mypy.overrides]]` block; do not modify any existing table.
- [ ] TASK-03-02: In `.github/workflows/ci.yml`, add `pytest-cov` to the
  install line (currently `pip install -e ".[webapp]" mypy pytest "nrel-pysam==7.1.0"`)
  → `pip install -e ".[webapp]" mypy pytest pytest-cov "nrel-pysam==7.1.0"`.
  Append `--cov=reopt_pysam_vn --cov-report=term-missing` to the existing
  pytest invocation line (currently
  `python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q`)
  → `python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q --cov=reopt_pysam_vn --cov-report=term-missing`.
  Do **not** add `--cov-fail-under`; this step must remain report-only and
  must not cause the job to fail on low coverage.
- [ ] TASK-03-03: Run the same command locally to confirm it works before
  pushing:
  ```powershell
  $env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q --cov=reopt_pysam_vn --cov-report=term-missing
  ```
- [ ] TASK-03-04: Commit, push, confirm the GitHub Actions run on `main`
  still concludes `success` and its log contains a coverage summary table.

**File Changes**
- `pyproject.toml` (modify): add the `[tool.coverage.run]` table per
  TASK-03-01. No other table changes.
- `.github/workflows/ci.yml` (modify): add `pytest-cov` to the install
  step and `--cov=reopt_pysam_vn --cov-report=term-missing` to the pytest
  step, per TASK-03-02. Leave the `mypy` step and its explanatory comment
  about the deferred `ruff` step unchanged.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
- `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q --cov=reopt_pysam_vn --cov-report=term-missing` → exits `0`, and its output contains a line starting with `TOTAL` (the coverage summary's total row).
- A deliberately-broken local run — running the same command with a made-up module name, e.g. `--cov=nonexistent_module_xyz` — should still let pytest itself pass or fail independently of coverage (coverage plugin errors must not mask test results); this is a sanity check only, not committed anywhere.

**Dependencies**
None (independent of PHASE-01, PHASE-02, PHASE-04).

**Exit Criteria**
- [ ] Local coverage run (TASK-03-03) succeeds and prints a `TOTAL` line.
- [ ] The next GitHub Actions run on `main` concludes `success` and its log
  contains a coverage table (visible via `gh run view --log` grepped for
  `TOTAL`).
- [ ] No `--cov-fail-under` flag exists anywhere in `.github/workflows/ci.yml`
  (verify with `grep -n "cov-fail-under" .github/workflows/ci.yml` → no
  output).

**Phase Risks**
- **RISK-03-01:** `pytest-cov` interacts badly with the existing `mypy`
  step or changes CI timing meaningfully. Mitigation: this is a single
  additive flag on the existing pytest invocation with no threshold, so the
  worst case is a slightly longer CI run, not a new failure mode; TASK-03-03
  verifies locally before pushing.

### PHASE-04 - Plans Directory Hygiene Sweep

**Goal**
`plans/active/` contains only plans without unambiguous evidence of having
already shipped; the 13 plans below, each with cited shipped-evidence, move
to `plans/archive/` under their unchanged filenames — mirroring the
`activeContext.md` worklog-rotation convention this repo already applies
elsewhere, and preventing the same "is this still live?" ambiguity that has
previously required manual archaeology in this repo.

**Tasks**
- [ ] TASK-04-01: For each of the following 13 files, confirm the cited
  evidence still exists, then `git mv` it from `plans/active/` to
  `plans/archive/` (same filename, no content edits):

  | Plan file | Shipped evidence (verify before moving) |
  |---|---|
  | `2026-05-07-decision-963-tou-migration-plan.md` | `reports/2026-05-07-decision-963-tou-migration-final.html` exists |
  | `2026-05-22-gap05-regime-toggle-plan.md` | `reports/2026-05-30-final-gap05-regime-toggle.html` exists; plan's own task checkboxes are 24/24 checked |
  | `2026-05-22-gap03-developer-project-catalog-plan.md` | plan's own task checkboxes are 27/27 checked; `reports/2026-05-29-gap03-phase-01.html` through `-03.html` exist |
  | `2026-06-04-samsung-ttc-dppa-economics-plan.md` | `reports/2026-06-04-final-samsung-ttc-dppa.html` exists |
  | `2026-06-12-sprint-1-mechanical-debloat-plan.md` | `reports/2026-06-12-final-sprint-1-repo-trim.html` exists |
  | `2026-06-12-sprint-2-shim-removal-binary-relocation-plan.md` | `reports/2026-06-12-final-sprint-2-repo-trim.html` exists |
  | `2026-06-12-sprint-3-onsite-offsite-pipeline-plan.md` | `reports/2026-06-14-final-sprint-3-repo-trim.html` exists |
  | `2026-06-20-factory-a-emivest-rerun-plan.md` | `reports/2026-06-20-final-factory-a-emivest-rerun.html` exists |
  | `2026-06-26-dppa-july-deck-verification-plan.md` | `activeContext.md`'s header explicitly states "July 2026 deck verification (completed 2026-06-26, all 5 phases): rotated to `docs/worklog/2026-07-04-july-deck-verification-archive.md`" |
  | `dppa_case_1_plan.md` | `reports/2026-04-09-dppa-case-1-final.html` exists |
  | `dppa_case_2_plan.md` | `reports/2026-04-16-dppa-case-2-final.html` (and `2026-04-15-dppa-case-2-final.html`) exist |
  | `dppa_case_3_plan.md` | `reports/2026-04-21-dppa-case-3-final.html` exists |
  | `ninhsim_60pct_solar_storage_dppa_plan.md` | `README.md` lists `ninhsim_solar_storage_60pct` as a currently-registered orchestration module; `reports/2026-04-08-ninhsim-solar-storage-60pct-dppa.html` exists |

  Example command for one file (repeat, substituting the filename, for all
  13):
  ```powershell
  git mv "plans/active/2026-05-07-decision-963-tou-migration-plan.md" "plans/archive/2026-05-07-decision-963-tou-migration-plan.md"
  ```
- [ ] TASK-04-02: Do **not** move any of the following 9 files — each
  either has no matching `reports/*final*` file, has an incomplete or
  ambiguous checkbox state, or (for `pysam_integration_reorg_plan.md`)
  explicitly states unfinished phases in its own text: leave these
  untouched in `plans/active/`:
  `2026-04-23-dppa-case-4-real-project-bridge-plan.md`,
  `2026-04-25-vn-tou-rts-comparison-plan.md`,
  `2026-05-18-operational-decision-engine-plan.md`,
  `2026-05-19-validation-sprint-plan.md`,
  `2026-05-22-gap01-factory-ingestion-plan.md`,
  `2026-05-22-gap02-procurement-comparison-plan.md`,
  `2026-05-22-gap04-generalized-settlement-plan.md`,
  `2026-06-19-factory-a-bess-validation-plan.md`,
  `pysam_integration_reorg_plan.md` (this one's own text reads "Phase 5 is
  partially complete... still the main unfinished bridge item" and lists
  Phase 6/7 as not started — do not treat its Phases 1-4 completion notes
  as evidence for archiving the whole file).
- [ ] TASK-04-03: Confirm the compatibility pointer file
  `plans/pysam_integration_reorg_plan.md` (top-level, 9 lines, states "This
  path is a compatibility pointer only" and points at
  `plans/active/pysam_integration_reorg_plan.md`) is left completely
  unmodified — it is intentional per `plans/README.md`'s own convention
  ("if an older path must remain for compatibility, leave only a short
  pointer note there"), not a stray duplicate.
- [ ] TASK-04-04: `git status` to confirm only the 13 intended moves
  appear (as renames, not add+delete pairs — `git mv` preserves this);
  commit.

**File Changes**
- `plans/active/2026-05-07-decision-963-tou-migration-plan.md` →
  `plans/archive/2026-05-07-decision-963-tou-migration-plan.md` (move, no
  content edit), and the same move pattern for the other 12 files listed
  in TASK-04-01's table.
- No other file in `plans/` is modified. `plans/README.md` is read but not
  edited (its existing active/archive convention already describes the
  desired end state correctly).

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
None — no testable behavior changes in this phase (this is a documentation/
organization move; verification is via `git status` and directory listing,
covered under Verification Strategy below).

**Dependencies**
None (independent of PHASE-01, PHASE-02, PHASE-03; purely a `plans/`
directory reorganization).

**Exit Criteria**
- [ ] `Get-ChildItem plans/active | Measure-Object | Select-Object -ExpandProperty Count`
  (or `ls plans/active | wc -l` in bash) reports `9` (down from 22).
- [ ] All 13 files from TASK-04-01's table exist under `plans/archive/`
  with unchanged filenames and unchanged content
  (`git diff --stat` for each move shows no content diff, only the path
  change).
- [ ] The 9 files listed in TASK-04-02 still exist, unmoved, under
  `plans/active/`.
- [ ] `plans/pysam_integration_reorg_plan.md` (the top-level pointer file)
  is byte-identical to its state before this phase.

**Phase Risks**
- **RISK-04-01:** One of the 13 "shipped" classifications turns out to be
  wrong (e.g. a report file was itself a draft, or work resumed on a plan
  after its report shipped). Mitigation: `git mv` is a trivially reversible
  rename with full history preserved — moving a file back with
  `git mv plans/archive/<name>.md plans/active/<name>.md` costs one command
  if a classification is later found to be wrong; ASM-005's binding default
  already tells the executor to skip any file with contradicting evidence
  found during TASK-04-01 rather than force the move.

## Gotchas

- **`$env:PYTHONPATH = ""` before every pytest run** — a polluted global
  `PYTHONPATH` on some machines shadows the `.venv`'s own FastAPI/pydantic
  install and produces `ModuleNotFoundError: pydantic_core._pydantic_core`
  that looks like a real failure but is purely an environment artifact.
- **`git rm --cached` vs `git rm`:** PHASE-01's deck `.pptx` files stay on
  disk (`--cached`); the root PNGs and `requirements.txt` are fully deleted.
  Mixing these up either leaves credentials-adjacent-shaped binaries fully
  deleted (losing local copies unnecessarily) or leaves genuinely-redundant
  files lingering on disk.
- **`.gitignore` edits: minimal lines only.** A loose negation elsewhere in
  this file has previously re-tracked unrelated report files in this
  repo's history. Touch only the two named lines in PHASE-01 and run
  `git status` immediately after.
- **The `xfail(strict=True)` tripwire in `test_repo_invariants.py` is
  intentional, not a leftover bug** — it exists specifically so that
  forgetting to remove it after untracking the PNGs turns into a hard,
  loud test failure. Remove it in the same commit as TASK-01-03, not
  before, not in a later phase.
- **SAM `Singleowner` fields take percent, not fraction**, except the
  twelve reference-plant fields in PHASE-02, which are simply set to `0.0`
  (percent-or-fraction-agnostic). Do not apply any `* 100.0` conversion to
  the zeroing calls.
- **`git mv` in PHASE-04 must be a rename, not a delete+recreate** — using
  plain filesystem move plus separate `git add`/`git rm` risks losing the
  file's history association in some git clients' diff views; `git mv`
  guarantees Git records it as a rename.
- **The 13-vs-9 plan classification in PHASE-04 is evidence-based, not a
  guess** — every "archive" decision cites a specific existing file path or
  an explicit `activeContext.md` statement; every "leave in place" decision
  is because no such evidence was found. Do not extend the archive list
  further without the same standard of evidence (a matching `reports/*final*`
  file, 100%-checked task boxes, or an explicit completion statement).

## Verification Strategy

- **TEST-001 (all phases):**
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q`
  → last line reports `0 failed` (xfailed/xpassed/skipped counts are
  acceptable).
- **TEST-002 (PHASE-01):**
  `git ls-files | Select-String -Pattern "\.pptx$|phase04_new_deal.*\.png$"`
  → no output.
- **TEST-003 (PHASE-01):**
  `git check-ignore -v "ceba-review/cong bess session.pptx"` → prints a
  matching rule, exit code `0`.
- **TEST-004 (PHASE-02):**
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/pysam/test_single_owner_clean_slate.py tests/python/webapp/test_golden_parity.py -q`
  → all pass; then `git diff --stat -- examples/` → no output.
- **TEST-005 (PHASE-02):**
  `Test-Path "reports/2026-07-24-single-owner-defaults-audit.md"` → `True`.
- **TEST-006 (PHASE-03):**
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q --cov=reopt_pysam_vn --cov-report=term-missing`
  → exit code `0`; output contains a `TOTAL` line.
- **TEST-007 (PHASE-04):**
  `(Get-ChildItem plans/active -Filter *.md).Count` → `9`.
- **TEST-008 (all phases, after each push):** `gh run list --limit 1` →
  latest run on `main` shows `completed success`.
- **MANUAL-001 (PHASE-01):** The NREL account owner rotates the API key at
  the NREL Developer Network account page and updates `NREL_API.env`
  locally; confirm a live solve still works afterwards via
  `scripts/python/reopt/solve_via_api.py` or the web app. This step is
  outside what an automated executor can perform (ASM in the parent sprint
  plan already established this); this plan only ensures the requirement
  is documented (TASK-01-06), not that rotation itself is completed.
- **MANUAL-002 (PHASE-02):** Whoever owns the Samsung/TTC and CEBA client
  relationships reads `reports/2026-07-24-single-owner-defaults-audit.md`'s
  `## Decision required` section and states whether any already-delivered
  number needs re-review — outside what this plan's automated tasks can
  resolve.

## Risks and Alternatives

- **RISK-001:** Running all four phases in the same session creates a
  large combined diff that's harder to review than four separate small
  PRs. Mitigation: the phases have no cross-dependencies (Phase Summary
  table shows `None` for every phase); they can be committed and pushed
  independently, one per commit, in any order, and each phase's own Exit
  Criteria are independently verifiable.
- **RISK-002:** Two sessions executing phases concurrently could collide on
  shared files (`pyproject.toml` is touched by PHASE-03 only; no file is
  touched by more than one phase in this plan, so this risk is low but not
  zero if a session also runs unrelated work concurrently). Mitigation:
  execute one phase at a time, verify its Exit Criteria, then proceed.
- **ALT-001:** Skip PHASE-02's flag implementation and only write the audit
  report using flag-off behavior everywhere — rejected: without the flag,
  TASK-02-06's on/off NPV/IRR delta (the concrete evidence the "decision
  required" section needs) cannot be computed; a report that only restates
  "the defaults exist" without quantifying their effect is weaker evidence
  for the people who need to decide whether to re-review a client number.
- **ALT-002:** Add a hard coverage threshold in PHASE-03 instead of
  report-only — rejected: this repo's real correctness burden is already
  carried by parity-gated numeric tests (Samsung/TTC bit-exact comparison);
  a coverage percentage gate on top would measure test-line-count, not
  correctness, and could pressure someone into padding tests to hit a
  number rather than testing what matters.
- **ALT-003:** Rewrite git history to purge the leaked NREL key instead of
  documenting a rotation requirement — rejected, consistent with the
  standing decision in `plans/2026-07-17-truth-and-correctness-sprint-plan.md`:
  rotation fully remediates a leaked-but-still-recoverable-from-history key,
  and history rewrite breaks every existing clone/worktree for no
  additional security benefit once the key is rotated dead.
- **ALT-004:** Archive all 22 `plans/active/` files and let a human sort
  them back out — rejected: 9 of the 22 have no unambiguous shipped
  evidence, and moving them anyway would just relocate the same ambiguity
  rather than resolve it; the evidence-based 13/9 split in PHASE-04 does
  real classification work instead of punting it.

## Suggested Next Step

Execute PHASE-01 first (fastest, lowest-risk, most-overdue — six sessions
running as of this plan's writing) and PHASE-02 second (resolves the one
item in this plan with external-facing stakes). PHASE-03 and PHASE-04 are
independent, small, and can be executed in any order relative to the first
two, including in parallel by a separate session, since no phase in this
plan shares a file with any other phase.
