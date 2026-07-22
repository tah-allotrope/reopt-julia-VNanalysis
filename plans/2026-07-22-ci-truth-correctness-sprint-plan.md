---
title: "CI Truth & Correctness Sprint — Workspace Hygiene, Green CI Gate, Security Cleanup, Two-Part Tariff Fix, Single Owner Clean-Slate"
date: "2026-07-22"
status: "draft"
request: "research/2026-07-22-reopt-pysam-execution-unblock-brainstorm.md — turn the confirmed, still-unexecuted P0-P2 backlog (plus two newly-verified findings) into one executable multi-phase plan"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-22-reopt-pysam-execution-unblock-brainstorm.md"
  - "research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md"
  - "plans/2026-07-17-truth-and-correctness-sprint-plan.md"
---

# Plan: CI Truth & Correctness Sprint — Workspace Hygiene, Green CI Gate, Security Cleanup, Two-Part Tariff Fix, Single Owner Clean-Slate

## Objective

Make the `reopt-pysam-vn` repository's CI gate on `main` actually green and honest
(it has been red on every push since 2026-07-14 while quietly claiming to protect
the codebase), close a four-times-repeated-and-never-actioned security/hygiene
backlog, fix two live numeric-correctness defects that a Vietnam DPPA advisory firm
would ship to a client today, and remove ~433 MB of stale, zero-value git worktree
checkouts discovered during the latest verification pass. This is a paydown sprint,
not a feature sprint: every later architectural initiative in this repo's own
roadmap (a config-driven case runner, an offline/frozen-resource solve mode, an
archive decision for the dormant Julia stack) explicitly declares a green CI gate
as its precondition, and that precondition has never been true.

## Context Snapshot

- **Current state (independently verified 2026-07-22 against live tools — `gh run
  list`, `gh run view --log`, `ruff check --statistics`, `git worktree list`,
  direct file reads):**
  - GitHub Actions CI on `main` (workflow file `.github/workflows/ci.yml`) is red
    on every run since it was added. The latest run, `29624245787` (triggered by
    commit `2b25f9d`), completed with **22 failed, 542 passed, 30 skipped** in
    39.62s.
  - No pytest markers are registered in `pyproject.toml`; `ci.yml` filters
    `-m "not network"` but no test in the suite carries a `network` marker, so the
    filter selects everything and excludes nothing.
  - `nrel-pysam` is unpinned in CI (`pyproject.toml` declares `"nrel-pysam>=7.1"`);
    the local `.venv` has exactly `7.1.0` installed (verified via
    `PySAM.__version__` and `pip show nrel-pysam`).
  - `ruff check . --statistics` (ruff 0.14.14) reports **206 violations** across 12
    rule codes today, up from 181 four days ago per the prior verification pass —
    the backlog is actively growing, not static. `ci.yml` contains a comment citing
    "181 pre-existing violations" as the reason ruff is not yet wired into CI; that
    number is now stale.
  - Two flat, canonical-path-violating scripts are tracked at
    `scripts/python/_extract_pptx.py` and `scripts/python/add_bess_review_comments.py`
    (the repo's own convention, in force since 2026-06-12, requires all scripts
    under `scripts/python/{reopt,pysam,integration}/`). Neither script is imported
    by bare module name anywhere else in the repo (verified via
    `grep -rn "add_bess_review_comments\|_extract_pptx" plans/ docs/ scripts/ src/ tests/`
    — only documentation and this plan reference them by name).
  - Three `.pptx` deck binaries remain tracked in git despite `.gitignore` entries
    intended to exclude them, because two of those `.gitignore` glob patterns are
    malformed **bracket character classes** rather than literal-bracket matches:
    `ceba-review/*[repo-checked].pptx` matches any single character from the set
    `{r,e,p,o,-,c,h,k,d}`, not the literal substring `[repo-checked]`.
  - Two 0.5 MB screenshots (`phase04_new_deal_initial.png`,
    `phase04_new_deal_scrolled.png`) are tracked at the repo root.
  - `requirements.txt` and `pyproject.toml`'s `[project].dependencies` list the
    same six packages — two sources of truth for one dependency set.
  - An NREL Developer API key was committed historically (recoverable from commits
    `3911032` and `b14bc0b`); nothing in the repo's tracked files, commit messages,
    or docs indicates it has ever been rotated at the issuing developer portal,
    across four prior review passes spanning 2026-07-11 through 2026-07-18.
  - `scripts/python/reopt/two_part_tariff_sensitivity.py` computes the Decree
    146/2025 two-part-tariff capacity charge on top of the *baseline* single-rate
    TOU energy cost instead of the lower two-part *trial* energy rates — its own
    docstring documents this as a known gap that **overstates the tariff's cost
    impact enough to flip the sign of the answer** for high-load-factor sites (a
    Saigon18-type profile at 69.5% load factor).
  - `src/python/reopt_pysam_vn/pysam/single_owner.py::_configure_financial_model`
    never assigns 12 specific `Singleowner.FinancialParameters` fields, so PySAM
    applies its built-in ~100 MW-reference-plant defaults to every run — verified
    directly today by executing the model with today's code: `construction_financing_cost
    = 2_866_500.0` (USD, flat), `insurance_rate = 0.5` (percent),
    `cost_debt_fee = 2.75` (percent), `months_working_reserve = 6.0`,
    `dscr_reserve_months = 6.0`, `prop_tax_cost_assessed_percent = 100.0`,
    `reserves_interest = 1.75` (percent); `cost_debt_closing`, `equip1_reserve_cost`,
    `equip2_reserve_cost`, `equip3_reserve_cost`, and `salvage_percentage` already
    default to `0.0`. These costs are sized for reference utility-scale plants and
    swamp the economics of the repo's actual project class (sub-2 MWp Vietnam C&I
    rooftop).
  - `.claude/worktrees/` holds six directories left behind by prior agent sessions:
    `cranky-torvalds-3f262a`, `dazzling-northcutt-0807cc`, `unruffled-banzai-88ae43`
    (108 MB each) and `upbeat-almeida-53c200` (109 MB) are registered git
    worktrees (`git worktree list` shows all four) whose branches
    (`claude/cranky-torvalds-3f262a`, `claude/dazzling-northcutt-0807cc`,
    `claude/unruffled-banzai-88ae43`, `claude/upbeat-almeida-53c200`) each contain
    **zero commits ahead of `main`** (verified via `git log main..<branch>`
    returning empty for all four) and have a clean working tree (verified via
    `git -C <path> status --porcelain=v1 -uall` returning empty for all four).
    `clever-chaplygin-dad6dc` and `kind-mcclintock-10b2e5` are 8 KB stub
    directories **not** listed by `git worktree list` — orphaned registrations
    from already-removed worktrees. Total reclaimable space: ~433 MB.
- **Desired state:** CI on `main` is green on the first push of this sprint's
  PHASE-02 and stays green through every subsequent phase. Non-portable tests carry
  registered, documented pytest markers and are excluded in CI; CI's PySAM version
  matches the version actually used locally; webapp tests pass with no dependency
  on a real NREL key; the 5 previously-unowned local-red tests are each triaged to
  a fix, a documented `xfail`, or a reclassified marker — never silently skipped.
  A repo-invariants test module mechanically enforces the flat-script ban, the
  no-tracked-artifacts rule, and the no-root-binaries rule. The two tracked flat
  scripts are relocated to their canonical subdirectories. The three `.pptx`
  binaries and two root PNGs are untracked (files remain on disk); the `.gitignore`
  glob bugs are fixed and verified to actually match; `requirements.txt` is
  removed in favor of the single `pyproject.toml` source; the key-rotation
  obligation is written down in `README.md` where the account owner will see it.
  `two_part_tariff_sensitivity.py` reports the *net* two-part-tariff impact (energy
  re-pricing plus demand charge) through a new, unit-tested library module, with
  the sign error eliminated for high-load-factor profiles. `SingleOwnerInputs`
  gains an opt-in `zero_reference_plant_defaults` flag that zeroes the 12
  reference-plant cost fields, with regression tests proving both the legacy
  (flag-off) and clean-slate (flag-on) behavior, plus a read-only audit report
  naming every caller and whether its published numbers are affected — with **no**
  change to the Samsung/TTC golden output at any point. The four zero-commit
  worktrees are removed and the two orphaned stubs pruned, reclaiming ~433 MB with
  zero loss of unique work.
- **Key repo surfaces:** `.github/workflows/ci.yml`, `pyproject.toml`,
  `.gitignore`, `requirements.txt`, `README.md`, `activeContext.md`,
  `docs/pitfalls.md`, `tests/python/webapp/conftest.py`,
  `tests/python/analysis/test_samsung_ttc_parity.py`,
  `tests/python/integration/{test_saigon18_compare,test_saigon18_phase3,test_regime_engine_smoke,test_ninhsim_cppa,test_capacity_factor_benchmark}.py`,
  `tests/python/pysam/{test_single_owner_phase4,test_strike_price_discovery}.py`,
  `scripts/python/{_extract_pptx.py,add_bess_review_comments.py}`,
  `scripts/python/reopt/two_part_tariff_sensitivity.py`,
  `data/vietnam/vn_tariff_2025.json`,
  `src/python/reopt_pysam_vn/reopt/preprocess.py`,
  `src/python/reopt_pysam_vn/pysam/single_owner.py`,
  `src/python/reopt_pysam_vn/webapp/{service.py,jobs.py}`,
  `ceba-review/*.pptx`, `phase04_new_deal_initial.png`,
  `phase04_new_deal_scrolled.png`, `.claude/worktrees/`.
- **Out of scope:** Every already-planned strategic-lens phase that this sprint is
  itself the precondition for — an offline/frozen-resource solve mode, an
  archive-vs-maintain decision for the Julia stack (`src/julia/`, last touched
  2026-05-19), a config-driven case runner to replace the ~120-script sprawl under
  `scripts/`, and settlement-kernel performance work. Also out of scope: any
  `git filter-repo` / git-history rewrite (key rotation is the remediation, not
  history editing); flipping `zero_reference_plant_defaults` to `True` by default
  anywhere (audit-only this sprint; a default flip is a human decision because it
  could shift golden numbers); any edit to `examples/samsung-ttc_combined-decision.example.json`
  or any other file under `examples/`; configuring `ruff` in CI or paying down its
  206-violation backlog (tracked as a still-open, larger follow-on item); webapp
  UI/feature changes; the actual key rotation at the NREL developer portal (an
  executor cannot perform this — it requires the human account owner, see
  ASM-006).

## Environment & Conventions

- **Stack:** Python 3.12 via the repo-local virtual environment `.venv`. On
  Windows, invoke it as `.venv\Scripts\python.exe`. **PySAM 7.1.0
  (`nrel-pysam`) exists only inside `.venv`** — the system Python (3.14 on the
  primary dev machine) has no PySAM wheel and PySAM-dependent code paths fall back
  to synthetic data, silently changing numbers. Always use the `.venv`
  interpreter for anything touching PySAM or the test suite. Package layout is
  setuptools with `package-dir = {"" = "src/python"}` (see `pyproject.toml`). A
  Julia stack also exists in the repo (`src/julia/`, `Project.toml`,
  `Manifest.toml`) but nothing in this plan touches it.
- **Setup:** From the repo root: `.venv\Scripts\python.exe -m pip install -e ".[webapp]"`
  (add `.venv\Scripts\python.exe -m pip install pytest mypy` if either is
  missing).
- **Build / Run:** No build step. The web app (not required for this plan, but
  referenced by PHASE-02's hermetic-test work):
  `$env:PYTHONPATH = "src/python"; .venv\Scripts\python.exe -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000`.
- **Test:** Full suite (PowerShell):
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q`.
  Single test:
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp/test_jobs.py::test_background_solve_reaches_done_when_mocked -q`.
- **Conventions & traps:**
  - **Always clear `PYTHONPATH` before running pytest** (`$env:PYTHONPATH = ""`).
    A stray global `PYTHONPATH` on the primary dev machine (pointing at an
    unrelated virtual environment) shadows the `.venv` FastAPI/pydantic install
    and produces a confusing `ModuleNotFoundError: pydantic_core._pydantic_core`
    that looks like a real failure. `pytest` resolves the package correctly via
    `pythonpath = ["src/python"]` already configured in `pyproject.toml`'s
    `[tool.pytest.ini_options]` — you do not need to set `PYTHONPATH` for pytest.
  - All commands shown in this plan are **PowerShell** (the primary dev machine is
    Windows). `.github/workflows/ci.yml` runs on `ubuntu-latest` with a bash
    shell — never paste `$env:...` syntax into that file.
  - Every JSON reader in this codebase opens files with `encoding="utf-8-sig"`
    (tolerates a Windows UTF-8 byte-order mark). Any new reader added by this plan
    must match.
  - **Units:** EVN tariff rates are in **VND/kWh**; capacity/demand charges are in
    **VND/kW-month**; PySAM finance fields are in **USD**; the two-part tariff
    script's fixed conversion constant is `EXCHANGE_RATE_VND_PER_USD = 26_000.0`.
    PySAM/SAM percentage-type fields (e.g. `insurance_rate`, `debt_percent`) are
    stored as **percent values (0-100), not fractions** — the existing wrapper
    code multiplies stored fractions by 100 before assignment; new code must
    follow the same convention or produce economics that are 100× wrong.
  - **Bit-exact parity gates:** `tests/python/analysis/test_samsung_ttc_parity.py`
    and `tests/python/webapp/test_golden_parity.py` compare live output against
    the tracked golden file `examples/samsung-ttc_combined-decision.example.json`.
    Any change that alters Samsung/TTC numeric output anywhere in this sprint is a
    defect to be fixed, never a golden file to be updated.
  - **Structural-move rule (this repo's own convention, learned the hard way):**
    after moving or renaming any file, run the **full** Python test suite, never a
    subset; before moving a file, `grep` for its **bare module name** (e.g.
    `_extract_pptx`), not the path form (`_extract_pptx.py` or
    `scripts/python/_extract_pptx`), since importers may reference it via
    `sys.path` manipulation rather than a normal package import.
  - **`.gitignore` edits must be minimal and re-checked immediately.** A prior
    loose negation in this file accidentally re-tracked unrelated files; run
    `git status` right after any `.gitignore` change.
  - **`git rm --cached` vs `git rm`:** `--cached` untracks a file while leaving it
    on disk (use this for the deck `.pptx` binaries, which stay useful locally);
    plain `git rm` deletes the file outright (use this for the root PNGs and
    `requirements.txt`, which are genuinely obsolete). Do not swap these.
- **Repo map:**
  - `src/python/reopt_pysam_vn/` — the installed package. `analysis/` and
    `webapp/` are the type-checked, documented public API surface (mypy gate
    already covers exactly these two in `pyproject.toml`'s
    `[[tool.mypy.overrides]]`); `integration/` (deal orchestration engines),
    `pysam/` (`single_owner.py`, `config.py`, `metrics.py`, `cashflow.py`),
    `reopt/` (`preprocess.py` builds the Vietnam TOU rate structures from
    `data/vietnam/`), and `common/` are internal and not mypy-gated but should
    still carry full type hints.
  - `scripts/python/{reopt,pysam,integration}/` — the only permitted script
    locations per the 2026-06-12 flat-script ban; `scripts/python/__init__.py` (a
    package marker, not a script) is exempt, but `_extract_pptx.py` and
    `add_bess_review_comments.py` currently violate the rule.
  - `tests/python/{analysis,integration,pysam,reopt,webapp,ingestion}/` — the
    pytest suite. `tests/python/webapp/conftest.py` already contains a fixture
    that monkeypatches `reopt_pysam_vn.webapp.service.solve_onsite_via_nrel` to
    block live NREL calls during tests.
  - `data/vietnam/vn_tariff_2025.json` — versioned EVN tariff data with a
    `_meta` envelope; application code reads only the `"data"` block. The
    top-level `data.tou_schedule` object defines `weekday` and
    `sunday_and_public_holidays` blocks, each with `peak_hours`,
    `standard_hours`, and `offpeak_hours` arrays of 0-23 hour indices (0 =
    midnight-1am). The two-part-tariff trial data lives at
    `data.demand_charge.two_part_tariff_trial`, with
    `capacity_charge_vnd_per_kw_month` (four voltage-level keys:
    `high_voltage_110kv_plus`, `medium_voltage_22kv_to_110kv`,
    `medium_voltage_6kv_to_22kv`, `low_voltage_below_6kv`) and
    `energy_charge_vnd_per_kwh` (three range pairs:
    `normal_hours_range: [1253, 1332]`, `peak_hours_range: [2162, 2251]`,
    `offpeak_hours_range: [843, 904]`).
  - `src/python/reopt_pysam_vn/reopt/preprocess.py` contains two currency-agnostic
    private helper functions directly reusable for the two-part tariff fix:
    `_build_hourly_rates(schedule_block: dict, peak: float, standard: float, offpeak: float) -> List[float]`
    (builds a 24-element hour-indexed rate array from one `tou_schedule` block)
    and `_build_8760_rates(weekday_rates: List[float], sunday_rates: List[float], year: int) -> List[float]`
    (expands a weekday/Sunday pair into a full 8760-hour year, handling calendar
    weekday/Sunday assignment). Both take and return plain floats — they were
    written for USD but have no USD-specific logic, so they can be called
    directly with VND magnitudes.
  - `artifacts/` is git-ignored by design (2026-06-12 de-bloat) and holds
    machine-local solve outputs; several tests incorrectly depend on files under
    it existing.

## Research Inputs

- From `research/2026-07-22-reopt-pysam-execution-unblock-brainstorm.md`:
  - Independently re-verified today (not inherited) that CI on `main` is still
    exactly as red as the 07-17 pass found it: same 22 failures, same taxonomy,
    latest run `29624245787`.
  - `ruff check --statistics` grew from 181 violations (07-17) to 206 (today,
    07-22) with no ruff-related work having landed — the backlog is compounding,
    which raises the *urgency* (not the scope) of registering pytest markers and
    fixing CI now rather than later.
  - New finding: `.claude/worktrees/` holds ~433 MB across six directories from
    prior agent sessions; four are registered worktrees whose branches contain
    zero commits beyond `main` (safe to remove); two are 8 KB orphaned stubs no
    longer tracked by `git worktree list` (need `git worktree prune`).
  - New finding: the `ci.yml` inline comment citing "181 pre-existing lint
    violations" is now factually stale and should be reworded to avoid citing a
    specific number that will rot again.
  - New finding (this session, verifying the prior plan's file inventory): a
    **second** flat-level script violates the canonical-path rule —
    `scripts/python/add_bess_review_comments.py` — alongside the previously known
    `scripts/python/_extract_pptx.py`. Neither has a bare-name importer elsewhere
    in the repo.
  - Recommendation adopted verbatim: stop producing further analysis passes on
    this repo and execute the already-correct, already-scoped plan.
- From `research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md`:
  - Full CI failure taxonomy (used directly in PHASE-02's task list): artifact-
    dependent tests reading git-ignored `artifacts/` paths; PySAM version drift
    (`Pvwattsv8` has no attribute `'new'` on CI's newer, unpinned PySAM); Samsung
    parity drifting up to 112% off the primary dev machine; five webapp tests
    failing only where the git-ignored `NREL_API.env` is absent; five tests red
    even locally (numeric drift, unowned since 2026-07-04).
  - The PySAM Single Owner reference-plant defaults were discovered via an
    external KBC pro-forma cross-check that had to reimplement the wrapper to get
    sane small-project economics; the specific contaminated fields and their
    default magnitudes are independently re-verified in this plan's Context
    Snapshot by executing the model directly today.
  - The two-part tariff sign-flip is fully specified in the script's own
    docstring: for a Saigon18-type 69.5%-load-factor profile the net effect flips
    from roughly +73B VND/yr (overstated cost, current script) to roughly -53B
    VND/yr (actual saving, order of magnitude) once the trial energy rates are
    correctly applied.

## Assumptions and Constraints

- **ASM-001:** The primary dev machine has the `artifacts/results/**` and
  `artifacts/reports/**` files that the artifact-dependent tests read, so those
  tests continue to pass locally once marked. — **BINDING DEFAULT:** pytest
  markers only change test *selection* in CI, never test bodies or local
  behavior; if a marked test also fails locally for a reason unrelated to missing
  artifacts, it falls under PHASE-02's red-test triage instead of being silently
  swept under the marker.
- **ASM-002:** The locally installed PySAM version is exactly what CI should pin
  to. — **BINDING DEFAULT:** verified today via
  `.venv\Scripts\python.exe -c "import PySAM; print(PySAM.__version__)"` → `7.1.0`
  and `pip show nrel-pysam` → `Version: 7.1.0`. Pin CI's install step to
  `"nrel-pysam==7.1.0"` exactly.
- **ASM-003:** The two `tests/python/integration/test_regime_engine_smoke.py`
  failures seen in CI (`test_cached_run_is_reused_when_manifest_is_successful`,
  `test_regime_matrix_no_solve_writes_complete_artifacts`) are caused by missing
  machine-local `artifacts/` state, the same root cause as the FileNotFoundError
  group, rather than a genuine environment-behavior bug. — **BINDING DEFAULT:**
  verify by temporarily renaming `artifacts/` to `artifacts_hold/` locally and
  re-running both tests; if they then fail the same way, mark them
  `requires_artifacts`; if they still pass, they are a real CI-environment defect
  and must be debugged and fixed within PHASE-02 rather than marked away.
  Rename `artifacts_hold/` back to `artifacts/` immediately after the check
  regardless of outcome.
- **ASM-004:** Three of the five long-standing locally-red tests are pure
  numeric/benchmark drift with no available root-cause fix in this sprint's
  scope: `tests/python/integration/test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`,
  `tests/python/integration/test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`,
  `tests/python/pysam/test_strike_price_discovery.py::test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike`.
  — **BINDING DEFAULT:** annotate each with
  `@pytest.mark.xfail(reason="numeric benchmark drift, red since 2026-07-04, tracked in activeContext.md 'Known pre-existing test failures'", strict=False)`
  and keep them running as `xfail` (never `skip`), so a future fix is visible as
  an unexpected pass rather than silently invisible.
- **ASM-005:** The two locally-red Samsung parity tests
  (`tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_full_tree_within_bar`,
  `::test_samsung_parity_is_bit_exact`) indicate a real, unresolved numeric
  divergence (`developer_irr_fraction` computing `0.0289...` where the golden file
  holds `None`), not tolerance noise. — **BINDING DEFAULT:** timebox root-cause
  investigation to 2 hours using a separate `git worktree` checked out at commit
  `fd8ceaf` (the last commit before the webapp phase-1/phase-2 sessions) to
  classify the divergence as a code regression vs. an environment difference. If
  unresolved within the timebox, annotate both tests with
  `@pytest.mark.xfail(reason="parity divergence under investigation: developer_irr_fraction 0.0289 vs golden None; see plans/2026-07-22-ci-truth-correctness-sprint-plan.md PHASE-02", strict=False)`
  and record the investigation's findings in `activeContext.md`. Under no
  circumstance regenerate or edit the golden file to make these tests pass.
- **ASM-006:** Rotating the leaked NREL API key requires access to the NREL
  Developer Network account, which only the human account owner has — an
  automated executor cannot perform this step. — **BINDING DEFAULT:** PHASE-03
  documents the rotation requirement clearly in `README.md` and `activeContext.md`
  (including both implicated commit hashes) and verifies `NREL_API.env` remains
  untracked; no git-history rewrite is attempted.
- **ASM-007:** Neither flat script (`scripts/python/_extract_pptx.py`,
  `scripts/python/add_bess_review_comments.py`) is imported by its bare module
  name anywhere in the codebase. — **BINDING DEFAULT:** verified today via
  `grep -rn "add_bess_review_comments\|_extract_pptx" scripts/ src/ tests/`
  returning no hits outside the scripts themselves; re-run this exact grep
  immediately before moving either file in PHASE-02, and if it now returns a hit
  in `scripts/`, `src/`, or `tests/`, update that importer's path in the same
  commit as the move.
- **ASM-008:** `preprocess.py`'s private helpers `_build_hourly_rates` and
  `_build_8760_rates` (see Environment & Conventions repo map) can be imported
  directly from `reopt_pysam_vn.reopt.preprocess` into the new two-part tariff
  module without modification, since they are pure float-in/float-out functions
  with no currency-specific logic. — **BINDING DEFAULT:** import them directly
  (`from reopt_pysam_vn.reopt.preprocess import _build_hourly_rates, _build_8760_rates`);
  if a future refactor of `preprocess.py` breaks this import, promote both
  functions to non-underscore-prefixed public names in the same commit rather
  than duplicating their logic.
- **ASM-009:** The two-part tariff trial energy rates in
  `vn_tariff_2025.json` are published as ranges, not single values per voltage
  level (`normal_hours_range: [1253, 1332]`, `peak_hours_range: [2162, 2251]`,
  `offpeak_hours_range: [843, 904]`, all VND/kWh). — **BINDING DEFAULT:** use the
  arithmetic midpoint of each range — normal 1292.5, peak 2206.5, off-peak 873.5
  VND/kWh — and record this choice explicitly in the output JSON under the key
  `"trial_rate_basis": "range_midpoint"`.
- **ASM-010:** The Saigon18 case study (the script's default input) connects at
  22 kV. — **BINDING DEFAULT:** the default trial capacity charge is
  `medium_voltage_22kv_to_110kv` = 235,414 VND/kW-month; expose a
  `--voltage-level` CLI argument accepting any of the four published keys, with
  this value as the default.
- **ASM-011:** No other session is concurrently using any of the four non-empty
  worktrees identified for removal in PHASE-01. — **BINDING DEFAULT:** before
  removing any worktree, confirm its working tree is still clean
  (`git -C <path> status --porcelain=v1 -uall` returns empty) and its branch
  still has zero commits ahead of `main` (`git log main..<branch>` returns
  empty); if either check now shows activity, skip that specific worktree and
  proceed with the others.
- **CON-001:** Samsung/TTC bit-exact parity must never regress:
  `tests/python/webapp/test_golden_parity.py` must pass unmodified at every
  commit in this sprint, and `examples/samsung-ttc_combined-decision.example.json`
  must never be edited.
- **CON-002:** No git-history rewrite anywhere in this sprint. "Untracking" means
  `git rm --cached` only (file stays on disk); it never means purging history.
- **CON-003:** Every new JSON reader added by this plan uses
  `encoding="utf-8-sig"`.
- **CON-004:** New library code goes under `src/python/reopt_pysam_vn/`; new
  scripts stay thin wrappers under the canonical `scripts/python/{reopt,pysam,integration}/`
  subdirectories. The mypy CI gate covers only `analysis/` and `webapp/`; new
  modules under `reopt/` and `pysam/` are not mypy-gated in CI but should still
  carry complete type hints to match house style.
- **DEC-001:** Ruff configuration and its 206-violation backlog are explicitly
  deferred past this sprint (see Out of Scope) — this sprint's goal is a green
  gate on the tests that already run, not a new lint gate.
- **DEC-002:** Marker-based CI quarantine (register `network`, `requires_artifacts`,
  `golden_machine`) is chosen over waiting for a future offline/frozen-resource
  solve mode to make everything portable — a narrow, honest green gate today beats
  a broad, silently-red one.
- **DEC-003:** The Single Owner clean-slate flag defaults to `False` (legacy
  behavior preserved byte-for-byte); flipping the default anywhere is explicitly
  deferred to a human decision informed by this sprint's audit report.

## Specification

**Two-part tariff corrected economics (PHASE-04).** For an 8760-element hourly
grid-import series `g(h)` in kW, where each element already represents one
1-hour timestep (so a value in kW is numerically equal to kWh for that hour —
never multiply by hours again):

- Baseline annual energy cost: `B = Σ_h g(h) · r_base(h)`, where `r_base(h)` is
  the existing single-component EVN TOU rate for hour `h` in VND/kWh, classified
  into peak/standard/off-peak windows per the EVN TOU schedule already encoded in
  `data/vietnam/vn_tariff_2025.json`'s `tou_schedule` block.
- Trial annual energy cost: `T = Σ_h g(h) · r_trial(h)`, where `r_trial(h)` is
  the two-part-tariff trial energy rate (Ca) for hour `h`: 2206.5 VND/kWh in peak
  windows, 1292.5 in standard windows, 873.5 in off-peak windows (range midpoints
  per ASM-009) — using the **same** hour-window classification as `r_base` (same
  `tou_schedule` block, same weekday/Sunday split).
- Energy re-pricing delta: `ΔE = T − B` (VND/yr). This is negative for every
  real profile, because every trial Ca rate is below its baseline single-rate
  counterpart.
- Trial demand charge: `D = Cp · Σ_m P(m)`, where `Cp` is the trial capacity
  charge in VND/kW-month (235,414 default per ASM-010, selectable by
  `--voltage-level`) and `P(m)` is the maximum hourly value of `g(h)` within
  calendar month `m` (12 months, using the existing non-leap-year
  `HOURS_PER_MONTH = [31,28,31,30,31,30,31,31,30,31,30,31]` day counts already
  defined in the script).
- Net two-part impact: `Δ = ΔE + D` (VND/yr). **`Δ < 0` means the customer SAVES
  money under the two-part trial tariff relative to the baseline single-rate
  tariff.** This is the quantity the current script gets sign-wrong for
  high-load-factor sites, because today it computes only `D` (using an obsolete
  60,000 VND/kW-month placeholder rate) while treating `ΔE` as zero.
- USD conversion: divide any VND amount by
  `EXCHANGE_RATE_VND_PER_USD = 26_000.0` (unchanged from the existing script).

**Single Owner clean-slate field set (PHASE-05).** When
`zero_reference_plant_defaults=True`, set exactly these 12
`Singleowner.FinancialParameters` attributes to `0.0`, immediately after
`_configure_financial_model`'s existing assignments (i.e. as the last step inside
that function, so every existing assignment stays byte-identical when the flag is
`False`): `insurance_rate`, `construction_financing_cost`, `cost_debt_fee`,
`cost_debt_closing`, `months_working_reserve`, `dscr_reserve_months`,
`equip1_reserve_cost`, `equip2_reserve_cost`, `equip3_reserve_cost`,
`prop_tax_cost_assessed_percent`, `reserves_interest`, `salvage_percentage`.
Verified today by direct execution against the local PySAM 7.1.0 install: before
zeroing, these fields hold `insurance_rate=0.5`, `construction_financing_cost=2_866_500.0`,
`cost_debt_fee=2.75`, `cost_debt_closing=0.0`, `months_working_reserve=6.0`,
`dscr_reserve_months=6.0`, `equip1_reserve_cost=0.0`, `equip2_reserve_cost=0.0`,
`equip3_reserve_cost=0.0`, `prop_tax_cost_assessed_percent=100.0`,
`reserves_interest=1.75`, `salvage_percentage=0.0` (five of the twelve are
already zero; all twelve are included for defensiveness against future SAM
version changes to their defaults).

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Workspace hygiene: remove ~433 MB of stale zero-commit git worktrees; reword the stale ruff-violation-count comment in `ci.yml` | None | Clean `.claude/worktrees/`; accurate `ci.yml` comment |
| PHASE-02 | Green, honest CI: pytest markers, PySAM pin, hermetic webapp tests, red-test triage, repo-invariants test, both flat scripts relocated | PHASE-01 (comment fix lands in the same file this phase edits) | Green `main` CI run; `tests/python/test_repo_invariants.py` |
| PHASE-03 | Security & hygiene: untrack `.pptx`/PNG binaries, fix `.gitignore` globs, single dependency source, key-rotation documentation | PHASE-02 (repo-invariants test enforces the untracking) | Clean `git ls-files`; rotation note in `README.md` |
| PHASE-04 | Two-part tariff Ca re-pricing fix (TDD), correcting the sign error for high-load-factor sites | PHASE-02 (green baseline) | `reopt_pysam_vn/reopt/two_part_tariff.py` + tests; corrected script output |
| PHASE-05 | Single Owner clean-slate mode + read-only contamination audit (no golden changes) | PHASE-02 (green baseline) | Opt-in flag + tests; `reports/2026-07-22-single-owner-defaults-audit.md` |

## Detailed Phases

### PHASE-01 - Workspace Hygiene: Stale Worktree Cleanup and Stale Comment Fix

**Goal**
Reclaim the ~433 MB of stale, zero-value git worktree checkouts sitting in
`.claude/worktrees/` and correct a now-inaccurate inline code comment, with zero
risk to any in-progress work, before touching CI or test files.

**Tasks**
- [ ] TASK-01-01: For each of the four non-empty worktrees
  (`cranky-torvalds-3f262a`, `dazzling-northcutt-0807cc`, `unruffled-banzai-88ae43`,
  `upbeat-almeida-53c200`), re-verify per ASM-011 immediately before removal:
  `git -C .claude/worktrees/<dir> status --porcelain=v1 -uall` must print nothing,
  and `git log main..claude/<dir>` must print nothing. If either check now shows
  output for a given directory, skip it and note the exception in the commit
  message; proceed with the remaining directories.
- [ ] TASK-01-02: Remove each directory that passed TASK-01-01 with
  `git worktree remove .claude/worktrees/<dir>` (run from the repo root). Do not
  pass `--force` unless the plain command reports the working tree is dirty
  (which TASK-01-01 should have already ruled out) — if it does report dirty,
  stop and treat that directory as a skip per TASK-01-01's exception path rather
  than forcing removal.
- [ ] TASK-01-03: Prune the two orphaned stub directories
  (`clever-chaplygin-dad6dc`, `kind-mcclintock-10b2e5`), which are not listed by
  `git worktree list` and are therefore not real worktrees: run
  `git worktree prune -v` from the repo root, then confirm both directories are
  gone. If either directory persists after `git worktree prune -v` (because it
  truly isn't a worktree artifact at all), remove it directly since it is at most
  8 KB and contains no git-tracked content.
- [ ] TASK-01-04: Delete any now-empty `claude/<branch>` remote-tracking or local
  branch references left behind by the removed worktrees only if `git branch -a`
  shows them as fully merged/empty duplicates of `main` — do not delete a branch
  that still exists independently of its worktree unless it is one of the four
  confirmed-zero-commit branches from TASK-01-01 (`claude/cranky-torvalds-3f262a`,
  `claude/dazzling-northcutt-0807cc`, `claude/unruffled-banzai-88ae43`,
  `claude/upbeat-almeida-53c200`). Use `git branch -d claude/<name>` (lowercase
  `-d`, not `-D`) so git itself refuses the deletion if it turns out the branch
  has unmerged commits — this makes the safety check self-enforcing.
- [ ] TASK-01-05: In `.github/workflows/ci.yml`, reword the comment above the
  (currently absent) ruff step. Replace the sentence that hardcodes "181
  pre-existing lint violations" with wording that does not embed a specific,
  soon-to-be-stale count — e.g. "ruff has no `[tool.ruff]` configuration in
  `pyproject.toml` yet and currently reports pre-existing lint violations; see
  `ruff check --statistics` for the current count. Configuring ruff and paying
  down the backlog is a separate, larger follow-on effort." Leave every other
  line of the comment and the rest of the file untouched.
- [ ] TASK-01-06: `git add -A` the worktree removal (git tracks worktree
  metadata under `.git/worktrees/`, not the working directories themselves, so
  there is likely nothing to stage from the removal itself — verify with
  `git status`) and the `ci.yml` comment change; commit.

**File Changes**
- `.claude/worktrees/cranky-torvalds-3f262a/`,
  `.claude/worktrees/dazzling-northcutt-0807cc/`,
  `.claude/worktrees/unruffled-banzai-88ae43/`,
  `.claude/worktrees/upbeat-almeida-53c200/` (delete via `git worktree remove`):
  entire directory trees removed from disk; no repo history affected (these
  directories were never tracked as file content — they are separate git working
  trees pointing at existing branches).
- `.claude/worktrees/clever-chaplygin-dad6dc/`,
  `.claude/worktrees/kind-mcclintock-10b2e5/` (delete via `git worktree prune` or
  direct removal): orphaned stub directories.
- `.github/workflows/ci.yml` (modify): reword one comment sentence only. No
  functional workflow change in this phase.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
None — no testable application behavior changes in this phase. Verification is
filesystem/git-state based (see Exit Criteria and Verification Strategy).

**Dependencies**
None (first phase; independent of all others — safe to run before or in
parallel with PHASE-02, sequenced first here only because it is fastest and
lowest-risk).

**Exit Criteria**
- [ ] `git worktree list` shows only the primary working directory (`main`) — no
  `claude/*` worktrees remain, unless TASK-01-01 found and documented an
  exception.
- [ ] `.claude/worktrees/` contains no directories, or contains only directories
  explicitly noted as skipped-with-reason in the phase commit message.
- [ ] `du -sh .claude/worktrees` (or equivalent) shows a size reduction of
  roughly 400+ MB versus the pre-phase measurement of ~433 MB.
- [ ] `.github/workflows/ci.yml`'s comment no longer contains the literal string
  "181".
- [ ] `git status` is clean after the commit.

**Phase Risks**
- **RISK-01-01:** A worktree thought to be zero-commit actually has uncommitted
  work that TASK-01-01's checks somehow missed (e.g. a detached-HEAD state with
  commits not reachable from the recorded branch name). Mitigation: `git worktree
  remove` itself refuses to remove a worktree with uncommitted changes unless
  `--force` is passed; this plan explicitly forbids passing `--force` on a
  refusal, so the command failing safely IS the safety net, not just the
  pre-check.

### PHASE-02 - CI Truth: Markers, PySAM Pin, Hermetic Tests, Red-Test Triage, Invariants, Flat-Script Relocation

**Goal**
`main`'s GitHub Actions CI workflow passes, and what it deliberately excludes is
explicit, documented, and machine-checkable rather than silently and
accidentally broken.

**Tasks**
- [ ] TASK-02-01: Register three pytest markers. In `pyproject.toml`, add a
  `markers` key to the existing `[tool.pytest.ini_options]` table:
  ```toml
  markers = [
    "network: makes real HTTP calls to external services; excluded in CI",
    "requires_artifacts: reads git-ignored machine-local files under artifacts/; excluded in CI",
    "golden_machine: bit-exact golden comparison only valid on the primary dev machine's resources; excluded in CI",
  ]
  ```
- [ ] TASK-02-02: Mark the artifact-dependent tests with
  `@pytest.mark.requires_artifacts` (or a module-level
  `pytestmark = pytest.mark.requires_artifacts` when every test in the file
  qualifies):
  - `tests/python/integration/test_saigon18_compare.py::test_load_reopt_metrics_uses_actual_results_keys`
  - `tests/python/integration/test_saigon18_phase3.py` — all three currently
    failing tests: `test_load_reopt_delivery_profile_uses_actual_results_schema`,
    `test_load_reopt_metrics_splits_bess_dispatch_by_tariff_period`,
    `test_scenario_d_adjustment_adds_settlement_to_revenue_and_npv`
  - `tests/python/pysam/test_single_owner_phase4.py` — all four currently
    failing tests (they read
    `artifacts/results/ninhsim/2026-04-01_ninhsim_scenario-b_optimized-cppa_reopt-results.json`):
    `test_build_ninhsim_single_owner_inputs_uses_recommended_candidate_band`,
    `test_build_ninhsim_single_owner_inputs_preserves_explicit_zero_escalation`,
    `test_build_ninhsim_single_owner_inputs_rejects_mismatched_hourly_series`,
    `test_run_single_owner_model_for_ninhsim_preserves_candidate_metadata`
  - `tests/python/pysam/test_strike_price_discovery.py` — the one failing test
    that depends on artifacts (they read
    `artifacts/reports/ninhsim/2026-04-04_ninhsim-single-owner-finance.json`):
    `test_sweep_strike_prices_returns_first_viable_candidate_with_ordered_results`
    (the second failing test in this file,
    `test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike`, is
    numeric drift per ASM-004 — mark it per TASK-02-05 instead, not here)
- [ ] TASK-02-03: Classify the two `tests/python/integration/test_regime_engine_smoke.py`
  failures per ASM-003: temporarily `Rename-Item artifacts artifacts_hold`, run
  `.venv\Scripts\python.exe -m pytest tests/python/integration/test_regime_engine_smoke.py -q`,
  observe whether `test_cached_run_is_reused_when_manifest_is_successful` and
  `test_regime_matrix_no_solve_writes_complete_artifacts` now fail the same way
  they do in CI, then `Rename-Item artifacts_hold artifacts` to restore state.
  If they fail as expected, mark both `@pytest.mark.requires_artifacts`; if
  either still passes, debug and fix that test's real CI-environment bug within
  this task before moving on.
- [ ] TASK-02-04: Mark the whole of `tests/python/analysis/test_samsung_ttc_parity.py`
  with a module-level `pytestmark = pytest.mark.golden_machine` (covers all three
  tests in the file, including `test_samsung_parity_headline_settlement_exact`,
  which fails only in CI today). Leave `tests/python/webapp/test_golden_parity.py`
  completely untouched — it passes in CI already and must keep running there.
- [ ] TASK-02-05: Apply the ASM-004 xfail annotations to the three numeric-drift
  tests (`test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`,
  `test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`,
  `test_strike_price_discovery.py::test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike`)
  and the ASM-005 timeboxed-investigation-then-xfail treatment to the two
  Samsung parity tests. Update the "Known pre-existing test failures" section of
  `activeContext.md` to state each test's new xfail status, reason, and (for the
  two parity tests) the outcome of the 2-hour investigation.
- [ ] TASK-02-06: Make webapp tests hermetic. In `tests/python/webapp/conftest.py`,
  add a new **autouse** fixture (separate from the existing
  `block_live_nrel_calls`-style fixture that patches `service.solve_onsite_via_nrel`
  — do not merge them, some tests re-patch the solve stub individually) that
  monkeypatches `reopt_pysam_vn.webapp.service.load_nrel_api_key` to return the
  literal string `"test-webapp-key"`. This removes the dependency on the
  git-ignored `NREL_API.env` file for these five currently CI-only failures:
  `test_jobs.py::test_background_solve_reaches_done_when_mocked`,
  `test_jobs.py::test_second_identical_deal_reuses_cached_solve`,
  `test_jobs.py::test_force_resolve_bypasses_cache`,
  `test_jobs.py::test_solve_failure_marks_run_error_and_worker_survives`,
  `test_pages.py::test_multipart_deal_submission_queues_a_background_solve`.
  Check that any test asserting on a key-derived provenance fingerprint (e.g. a
  `sha256` hash of the key) still passes — its expected value becomes
  `sha256(b"test-webapp-key").hexdigest()[:12]` deterministically; update the
  literal expected value in that test if it currently hardcodes the real key's
  fingerprint.
- [ ] TASK-02-07: Pin PySAM in CI and tighten the marker filter. In
  `.github/workflows/ci.yml`, change the dependency install line to
  `pip install -e ".[webapp]" mypy pytest "nrel-pysam==7.1.0"` (version per
  ASM-002) and change the pytest invocation to
  `python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine" -q`.
  Leave the mypy step and the (PHASE-01-reworded) ruff-omission comment
  otherwise unchanged.
- [ ] TASK-02-08: Create `tests/python/test_repo_invariants.py` with three tests
  (see Test Specs) that shell out to `git ls-files` to enforce: no flat-level
  Python scripts under `scripts/python/` (excluding `__init__.py`), no tracked
  files under `artifacts/`, and no root-level tracked binaries
  (`.png`/`.pptx`/`.xlsx`/`.xlsm` with no `/` in their tracked path). Until
  PHASE-03 untracks the two root PNGs, the root-binaries test **will fail** by
  design — implement it fully, then mark it with
  `@pytest.mark.xfail(reason="tracked root binaries removed in PHASE-03 of plans/2026-07-22-ci-truth-correctness-sprint-plan.md", strict=True)`.
  Using `strict=True` here is deliberate: once PHASE-03 untracks the binaries,
  this xfail becomes a hard failure (an "unexpectedly passed" error) until its
  annotation is removed, which makes forgetting to remove the annotation
  impossible to miss.
- [ ] TASK-02-09: Relocate both flat scripts to their canonical subdirectories,
  after re-running the ASM-007 grep to confirm no new importer has appeared:
  `git mv scripts/python/_extract_pptx.py scripts/python/integration/_extract_pptx.py`
  and `git mv scripts/python/add_bess_review_comments.py scripts/python/integration/add_bess_review_comments.py`.
  If either script computes its own repo-root path via something like
  `Path(__file__).resolve().parents[N]`, increment `N` by 1 to account for the
  new subdirectory depth — check both files for this pattern before moving and
  fix it in the same commit if present.
- [ ] TASK-02-10: Run the full local suite (`$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q`),
  confirm `0 failed` (xfails reporting as `xfailed` is expected and fine), then
  commit, push, and confirm the resulting GitHub Actions run on `main` completes
  with status `success` (`gh run list --limit 1` or the Actions tab).

**File Changes**
- `pyproject.toml` (modify): add the `markers` list inside the existing
  `[tool.pytest.ini_options]` table. Leave dependencies, the mypy configuration,
  and packaging settings untouched.
- `.github/workflows/ci.yml` (modify): pin `nrel-pysam==7.1.0` in the install
  step; expand the `-m` pytest filter to exclude all three new markers. Nothing
  else in the file changes in this phase (the comment reword already happened in
  PHASE-01).
- `tests/python/webapp/conftest.py` (modify): add the new autouse
  `stub_nrel_api_key` fixture alongside the existing NREL-blocking fixture.
- `tests/python/integration/test_saigon18_compare.py`,
  `tests/python/integration/test_saigon18_phase3.py`,
  `tests/python/pysam/test_single_owner_phase4.py`,
  `tests/python/pysam/test_strike_price_discovery.py`,
  `tests/python/integration/test_regime_engine_smoke.py` (modify): add marker
  annotations only — no test-body logic changes.
- `tests/python/analysis/test_samsung_ttc_parity.py` (modify):
  `pytestmark = pytest.mark.golden_machine` at module scope, plus per-ASM-005
  xfail annotations on the two locally-red tests.
- `tests/python/integration/test_capacity_factor_benchmark.py`,
  `tests/python/integration/test_ninhsim_cppa.py` (modify): ASM-004 xfail
  annotations.
- `tests/python/test_repo_invariants.py` (create): the three invariant tests
  described in Test Specs.
- `scripts/python/integration/_extract_pptx.py` (create, via `git mv` from
  `scripts/python/_extract_pptx.py`).
- `scripts/python/integration/add_bess_review_comments.py` (create, via `git mv`
  from `scripts/python/add_bess_review_comments.py`).
- `activeContext.md` (modify): update the "Known pre-existing test failures"
  section with the new xfail statuses and the parity-investigation outcome.

**Function Signatures**
- `stub_nrel_api_key(monkeypatch: pytest.MonkeyPatch) -> None` — new autouse
  pytest fixture in `tests/python/webapp/conftest.py`; monkeypatches
  `reopt_pysam_vn.webapp.service.load_nrel_api_key` to
  `lambda: "test-webapp-key"`; returns nothing (fixtures that mutate global
  state via `monkeypatch` conventionally return `None`).
- `_tracked_files(prefix: str = "") -> list[str]` — helper function in the new
  `tests/python/test_repo_invariants.py`; runs
  `subprocess.run(["git", "ls-files", "--", prefix] if prefix else ["git", "ls-files"], capture_output=True, text=True, cwd=<repo root>)`
  and returns its stdout split into non-empty lines.

**Test Specs**
- `test_no_flat_python_scripts()`: call `_tracked_files("scripts/python")`,
  filter to paths matching the pattern `scripts/python/<name>.py` (exactly one
  path segment after `scripts/python/`, i.e. no further `/`), excluding
  `scripts/python/__init__.py` → expected `[]`. Before TASK-02-09 this returns
  `["scripts/python/_extract_pptx.py", "scripts/python/add_bess_review_comments.py"]`;
  after TASK-02-09 it returns `[]`.
- `test_no_tracked_artifacts()`: call `_tracked_files("artifacts")` → expected
  `[]` (already true today — regression guard).
- `test_no_root_level_binaries()`: call `_tracked_files()` (no prefix), filter to
  paths containing no `/` with a suffix in
  `{".png", ".pptx", ".xlsx", ".xlsm"}` → expected `[]`. Today this returns
  `["phase04_new_deal_initial.png", "phase04_new_deal_scrolled.png"]`, hence the
  `strict=True` xfail until PHASE-03 (note: `ceba-review/*.pptx` and
  `scenarios/case_studies/regina/Regina.xlsx` both contain `/` and are correctly
  excluded by this filter — `Regina.xlsx` is a live test input and must remain
  tracked).
- Hermetic-key check (manual shell verification, not a new automated test):
  `Rename-Item NREL_API.env NREL_API.env.bak; $env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp -q; Rename-Item NREL_API.env.bak NREL_API.env`
  → all webapp tests pass with the real key file absent, proving no webapp test
  depends on it.
- CI-filter simulation: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine" -q`
  → `0 failed`.

**Dependencies**
- PHASE-01 (this phase's TASK-02-07 edits `.github/workflows/ci.yml`, the same
  file PHASE-01's TASK-01-05 touched — sequencing avoids a merge conflict on the
  same lines).

**Exit Criteria**
- [ ] Full local suite: `0 failed` (xfails report as `xfailed`, never `failed`).
- [ ] The CI-filter simulation command above reports `0 failed` locally with
  `NREL_API.env` renamed away.
- [ ] The next GitHub Actions run on `main` concludes with status `success`.
- [ ] `.venv\Scripts\python.exe -m pytest --collect-only -m requires_artifacts -q tests/python`
  lists at least the 9 tests marked in TASK-02-02/02-03; the equivalent
  `-m golden_machine` collection lists exactly the 3 tests in
  `test_samsung_ttc_parity.py`.

**Phase Risks**
- **RISK-02-01:** The Samsung parity divergence (ASM-005) turns out to be a real
  regression rather than environment drift. Mitigation: the worktree-based
  bisection in ASM-005 is designed to distinguish this; if it IS a regression,
  fixing the regression supersedes the xfail plan and must keep
  `test_golden_parity.py` green throughout (CON-001).
- **RISK-02-02:** Pinning `nrel-pysam==7.1.0` fails to install on the CI runner's
  `ubuntu-latest`/Python 3.12 image. Mitigation: fall back to the nearest
  installable `7.1.x` patch version and re-run; the marker filter already
  excludes the tests most sensitive to PySAM API surface changes.

### PHASE-03 - Security & Hygiene: Untrack Binaries, Fix Globs, One Dependency Source, Key-Rotation Documentation

**Goal**
`git ls-files` no longer lists any deck binaries or root-level screenshots,
every `.gitignore` pattern that names a specific file actually matches it,
dependencies have exactly one source of truth, and the leaked-key rotation
obligation is documented where the human account owner will see it.

**Tasks**
- [ ] TASK-03-01: Untrack the three deck binaries (files remain on disk per
  CON-002):
  `git rm --cached "ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx" "ceba-review/cong bess session [reviewed].pptx" "ceba-review/cong bess session.pptx"`.
- [ ] TASK-03-02: Fix the two malformed `.gitignore` bracket-character-class
  patterns by escaping the brackets so they match literal substrings instead of
  character classes: change `ceba-review/*[repo-checked].pptx` to
  `ceba-review/*\[repo-checked\].pptx` and `ceba-review/*[*reviewed*].pptx` to
  `ceba-review/*\[reviewed\].pptx`. Touch nothing else in `.gitignore` on this
  pass (the file has a documented history of loose-negation accidents). After
  editing, verify each of the three untracked filenames now actually matches a
  rule: `git check-ignore -v "ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx"`,
  `git check-ignore -v "ceba-review/cong bess session [reviewed].pptx"`, and
  `git check-ignore -v "ceba-review/cong bess session.pptx"` must each print a
  matching rule and exit with code `0`.
- [ ] TASK-03-03: Delete the tracked root screenshots outright (not
  `--cached` — these are stale session artifacts, not useful local files):
  `git rm phase04_new_deal_initial.png phase04_new_deal_scrolled.png`. Then
  remove the `strict=True` xfail annotation added in PHASE-02's TASK-02-08 from
  `test_no_root_level_binaries` in `tests/python/test_repo_invariants.py` — this
  is the deliberate cross-phase tripwire; if you forget this step, the test
  suite itself will now fail loudly (an "unexpectedly passed" xfail error)
  rather than silently staying green.
- [ ] TASK-03-04: Consolidate to a single dependency source:
  `git rm requirements.txt`. In `README.md`'s "Python Setup" section, replace the
  two-line `python -m pip install -r requirements.txt` +
  `python -m pip install -e .` sequence with the single line
  `python -m pip install -e ".[webapp]"`.
- [ ] TASK-03-05: Document the key-rotation requirement. Add a short "Security
  note — API key rotation required" subsection to `README.md` (placed under
  "Quick Start") stating: an NREL Developer API key was committed historically
  in commits `3911032` and `b14bc0b` and remains recoverable from git history;
  the repository account owner must rotate it at the NREL Developer Network
  account page and update the local, git-ignored `NREL_API.env` file
  accordingly; no git-history rewrite is planned, since rotation alone fully
  remediates the exposure (per CON-002/ASM-006). Add a matching one-line note to
  `activeContext.md`.
- [ ] TASK-03-06: Run the full local suite (now including the un-xfailed
  `test_no_root_level_binaries`), run `git status` to confirm nothing was
  accidentally re-tracked, commit, push, and confirm the resulting CI run on
  `main` is `success`.

**File Changes**
- `.gitignore` (modify): the two escaped-bracket lines only, in the existing
  July-2026-deck section — no other lines touched.
- `README.md` (modify): Python Setup consolidation (TASK-03-04) and the new
  security note (TASK-03-05). No other section of the file changes.
- `activeContext.md` (modify): one new key-rotation line.
- `requirements.txt` (delete via `git rm`).
- `phase04_new_deal_initial.png`, `phase04_new_deal_scrolled.png` (delete via
  `git rm`).
- `ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx`,
  `ceba-review/cong bess session [reviewed].pptx`,
  `ceba-review/cong bess session.pptx` (untrack via `git rm --cached`; files
  remain on disk unchanged).
- `tests/python/test_repo_invariants.py` (modify): remove the `strict=True`
  xfail decorator from `test_no_root_level_binaries` only.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
- `git ls-files ceba-review` → empty output (no `.pptx` files listed; any other
  tracked files under `ceba-review/`, if present, are unaffected by this phase
  and may still appear).
- `git ls-files -- "*.png"` → no root-level match; `tests/python/test_repo_invariants.py::test_no_root_level_binaries`
  now passes without the `xfail` marker (it was `strict=True` xfail before this
  phase; after this phase it must run as an ordinary passing test).
- `git check-ignore -v "ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx"`
  → prints a matching rule, exit code `0`. Same check for the other two pptx
  filenames.
- `git ls-files NREL_API.env` → empty (already true today; this is a regression
  guard, not a new behavior).
- `git ls-files requirements.txt` → empty.

**Dependencies**
- PHASE-02 (the repo-invariants test and its `strict=True` xfail hand-off depend
  on that test module existing first).

**Exit Criteria**
- [ ] All five Test Specs above hold exactly as stated.
- [ ] Full local suite: `0 failed`. CI run on `main`: `success`.
- [ ] `README.md` contains the key-rotation note with both commit hashes
  (`3911032`, `b14bc0b`) visible in the text.

**Phase Risks**
- **RISK-03-01:** Some script or test elsewhere in the repo reads one of the
  now-untracked `.pptx` files by its tracked path and only worked because the
  file happened to be present in a fresh clone. Mitigation: the files remain on
  disk on the primary dev machine (untracking is not deletion), and the
  full-suite run in TASK-03-06 will surface any test that fails because it
  expected the file to be freshly cloned rather than locally present — the
  existing deck pipeline already treats these binaries as local-only inputs by
  convention.

### PHASE-04 - Two-Part Tariff Correction: Trial Energy Rates Plus Real Capacity Charge

**Goal**
`scripts/python/reopt/two_part_tariff_sensitivity.py` reports the *net* two-part
tariff impact (lower trial energy rates AND the demand charge) instead of
demand-charge-only stacked on baseline energy rates, eliminating the sign error
for high-load-factor profiles. The core arithmetic moves into a new, independently
unit-tested library module; the script becomes a thin CLI around it.

**Tasks**
- [ ] TASK-04-01 (RED): Create `tests/python/reopt/test_two_part_tariff.py`
  containing the failing tests listed in Test Specs below, importing from
  `reopt_pysam_vn.reopt.two_part_tariff` (a module that does not exist yet). Run
  `.venv\Scripts\python.exe -m pytest tests/python/reopt/test_two_part_tariff.py -q`
  and confirm it fails with a collection/import error, proving the tests are
  wired correctly before any implementation exists.
- [ ] TASK-04-02 (GREEN): Create `src/python/reopt_pysam_vn/reopt/two_part_tariff.py`
  implementing the three functions in Function Signatures below, following the
  Specification's formulas exactly. Import `_build_hourly_rates` and
  `_build_8760_rates` directly from `reopt_pysam_vn.reopt.preprocess` per ASM-008
  rather than reimplementing hour-window classification — this guarantees the
  trial-rate series uses the identical peak/standard/off-peak windows as the
  baseline series, and it means `preprocess.py`'s own output stays byte-identical
  (required for the Julia/Python cross-validation Layer 3 to keep passing) since
  this phase does not modify `preprocess.py` itself.
- [ ] TASK-04-03: Rewire `scripts/python/reopt/two_part_tariff_sensitivity.py`:
  load `data/vietnam/vn_tariff_2025.json` with `encoding="utf-8-sig"` and read
  its `"data"` block; build the baseline rate series (reuse the existing
  single-component TOU logic already present via `preprocess.py`'s tariff
  resolution, expressed directly in VND rather than the USD `preprocess.py`
  normally emits — construct it locally using the same `tou_schedule` block and
  the appropriate `base_avg_price_vnd_per_kwh × multiplier` values already used
  elsewhere in the tariff data) and the trial rate series (via the new
  `build_trial_energy_rate_series` function); compute `ΔE` from the existing
  `extract_monthly_grid_import(results)` series; replace the hardcoded
  `DECREE_146_PILOT_RATE_VND_PER_KW_MONTH = 60_000` constant with the trial
  `capacity_charge_vnd_per_kw_month` value selected by a new `--voltage-level`
  CLI argument (choices = the four keys under
  `data.demand_charge.two_part_tariff_trial.capacity_charge_vnd_per_kw_month`,
  default per ASM-010); keep the existing capacity-charge rate sweep
  (`DEFAULT_RATE_SWEEP_VND_PER_KW_MONTH`) unchanged; add `energy_delta_vnd`,
  `net_impact_vnd`, and `net_impact_usd` fields to every sweep row and to the
  base-case result card. Update the module docstring: delete the entire
  `!!!!! KNOWN MODELING GAP !!!!!` block and replace it with a short description
  of the corrected method, keeping the XanhTerra cross-reference URL.
- [ ] TASK-04-04: Close out the documentation trail:
  - Remove the "Two-part tariff sensitivity — missing energy rate reduction"
    entry from `activeContext.md`'s "Known model gaps" section, noting the fix
    date (2026-07-22) in its place.
  - Update the `WARNING:` sentence inside `data/vietnam/vn_tariff_2025.json`'s
    `data.demand_charge.notes` string to state that the script now correctly
    applies the trial Ca rates (this is a string-only edit to the `notes` field;
    no numeric field in the JSON changes).
  - Add a new entry to `docs/pitfalls.md` titled "Two-part tariff energy rates"
    summarizing the sign-flip defect and its fix, plus a second new entry
    documenting the REopt `year_one_energy_produced_kwh` vs
    `annual_energy_produced_kwh` ~4.5% divergence (a degradation-year accounting
    convention difference worth flagging for future analysts, surfaced during
    the KBC cross-check work referenced in this sprint's research inputs).
- [ ] TASK-04-05: If the primary dev machine has the Saigon18 scenario-A
  artifacts locally available, regenerate the sensitivity output:
  `.venv\Scripts\python.exe scripts/python/reopt/two_part_tariff_sensitivity.py`
  (its defaults already point at the Saigon18 scenario-A results path) and
  sanity-check the sign: for the ~69.5%-load-factor Saigon18 profile, the net
  `Δ` at the real default capacity charge must be **negative** (a saving),
  consistent in order of magnitude (not exact value — the prior estimate was
  approximate) with the previously-documented ≈ −53B VND/yr expectation. If the
  artifacts are not available on the machine running this task, skip this task
  and note it as deferred in the phase commit message — TASK-04-01/02/03's
  library-level tests do not require the artifacts and remain the phase's binding
  verification.
- [ ] TASK-04-06: Run the full local suite, confirm `0 failed`, commit, push, and
  confirm CI is `success`.

**File Changes**
- `src/python/reopt_pysam_vn/reopt/two_part_tariff.py` (create): the three
  functions in Function Signatures below.
- `tests/python/reopt/test_two_part_tariff.py` (create): unit tests using
  synthetic toy inputs only — no dependency on `artifacts/`, no network calls, no
  PySAM.
- `scripts/python/reopt/two_part_tariff_sensitivity.py` (modify): as described in
  TASK-04-03. Keep `extract_monthly_grid_import`, `monthly_peaks`,
  `estimate_demand_shaving_peaks`, and the existing BAU-vs-solar demand-charge
  comparison logic intact and unchanged.
- `activeContext.md`, `docs/pitfalls.md`, `data/vietnam/vn_tariff_2025.json`
  (modify): documentation trail per TASK-04-04. The JSON edit touches only the
  `data.demand_charge.notes` string value — no numeric field anywhere in the
  file changes.

**Function Signatures**
- `build_trial_energy_rate_series(tariff_data: dict, *, basis: str = "range_midpoint") -> list[float]`
  — returns an 8760-length list of trial Ca rates in VND/kWh, classified into
  peak/standard/off-peak by the same `tou_schedule` windows used for the
  baseline series (via `_build_hourly_rates`/`_build_8760_rates` imported from
  `preprocess.py` per ASM-008); raises `ValueError` if `basis` is not
  `"range_midpoint"` (the only supported value for now).
- `reprice_energy_series(grid_import_kw: list[float], baseline_rates_vnd_per_kwh: list[float], trial_rates_vnd_per_kwh: list[float]) -> dict`
  — returns
  `{"baseline_energy_cost_vnd": float, "trial_energy_cost_vnd": float, "energy_delta_vnd": float}`
  where `energy_delta_vnd = trial_energy_cost_vnd − baseline_energy_cost_vnd`;
  raises `ValueError` unless all three input lists have exactly length 8760.
- `compute_two_part_impact(grid_import_kw: list[float], baseline_rates_vnd_per_kwh: list[float], trial_rates_vnd_per_kwh: list[float], capacity_charge_vnd_per_kw_month: float) -> dict`
  — returns
  `{"energy_delta_vnd": float, "annual_demand_charge_vnd": float, "net_impact_vnd": float, "net_impact_usd": float}`
  per the Specification (`net_impact_vnd = energy_delta_vnd + annual_demand_charge_vnd`;
  `net_impact_usd = net_impact_vnd / 26_000.0`).

**Test Specs**
- Flat toy profile:
  `reprice_energy_series([1000.0]*8760, [2000.0]*8760, [1300.0]*8760)` →
  `energy_delta_vnd == -6_132_000_000.0` exactly (computed as
  `8760 × 1000 × (1300 − 2000)`); `baseline_energy_cost_vnd == 17_520_000_000.0`
  exactly (`8760 × 1000 × 2000`).
- Length-mismatch guard:
  `reprice_energy_series([1000.0]*100, [2000.0]*8760, [1300.0]*8760)` → raises
  `ValueError`.
- `build_trial_energy_rate_series` called on the real `vn_tariff_2025.json`
  `"data"` block → returns a list of length 8760; every element is one of
  `{873.5, 1292.5, 2206.5}`; the resulting multiset contains all three distinct
  values (confirming peak, standard, and off-peak windows all occur across a
  year, per the `tou_schedule` block's weekday/Sunday split).
- `compute_two_part_impact` with a constant 1000 kW import for all 8760 hours,
  constant baseline rate 2000 VND/kWh, constant trial rate 1300 VND/kWh,
  `capacity_charge_vnd_per_kw_month=235_414.0` →
  `annual_demand_charge_vnd == 235_414.0 * 12_000.0 == 2_824_968_000.0` (12
  monthly peaks of 1000 kW each, since the profile is constant);
  `net_impact_vnd == -6_132_000_000.0 + 2_824_968_000.0 == -3_307_032_000.0`
  (negative — a 100%-load-factor extreme profile saves money under the two-part
  tariff, matching the domain expectation that high load factor favors the
  two-part structure).
- Sign edge case: a low-load-factor profile (`g(h) = 5000.0` for the first hour
  of every calendar month, `g(h) = 10.0` for every other hour) with the same
  rate inputs as above → `net_impact_vnd > 0` (a low-load-factor customer loses
  money under the two-part tariff — the opposite sign from the high-load-factor
  case, demonstrating the fix is directionally correct rather than
  coincidentally negative).

**Dependencies**
- PHASE-02 (a green baseline suite so this phase's test-count impact is
  unambiguous). Independent of PHASE-03 and PHASE-05 — may run in either order
  relative to them, but must follow PHASE-02.

**Exit Criteria**
- [ ] `tests/python/reopt/test_two_part_tariff.py` passes in full; full suite
  `0 failed`; CI run on `main` is `success`.
- [ ] `.venv\Scripts\python.exe scripts/python/reopt/two_part_tariff_sensitivity.py --help`
  shows a `--voltage-level` argument with exactly four choices and the
  ASM-010-specified default.
- [ ] If TASK-04-05 ran (artifacts available): the regenerated Saigon18 output
  JSON has `energy_delta_vnd < 0` and a negative net impact at the default
  voltage level's capacity charge.
- [ ] `activeContext.md` no longer lists the two-part tariff gap under "Known
  model gaps".

**Phase Risks**
- **RISK-04-01:** Reusing `_build_hourly_rates`/`_build_8760_rates` from
  `preprocess.py` accidentally changes their behavior for the *baseline* series
  and breaks the Julia/Python cross-validation Layer 3 (a standing, high-value
  invariant of this repo). Mitigation: this phase strictly imports these two
  functions unchanged and never edits `preprocess.py`; if `preprocess.py` must be
  touched at all for any reason, additionally run
  `.\tests\run_all_tests.ps1 -Layer 3` (PowerShell) alongside the pytest suite
  before considering the phase done.
- **RISK-04-02:** The trial-rate ranges published in `vn_tariff_2025.json` get
  revised by EVN mid-sprint. Mitigation: the new module reads rates from the
  versioned data file at runtime and never hardcodes VND magnitudes in code; the
  `"trial_rate_basis": "range_midpoint"` field records exactly which convention
  produced the output, so any future rate revision is transparent in the output
  JSON.

### PHASE-05 - Single Owner Clean-Slate Mode and Contamination Audit

**Goal**
Small Vietnam C&I projects can be run through PySAM Single Owner finance without
silently inheriting SAM's ~100 MW reference-plant cost defaults, via an explicit,
tested, opt-in flag — and a written audit states exactly which existing callers
and published results are affected by those defaults today, without changing any
golden number anywhere in the repo.

**Tasks**
- [ ] TASK-05-01 (RED): Create `tests/python/pysam/test_single_owner_clean_slate.py`
  (new file; add `PySAM = pytest.importorskip("PySAM")` at module top, matching
  the pattern in sibling PySAM test files) containing the tests in Test Specs
  below. Run it and confirm every test fails (the flag does not exist yet).
- [ ] TASK-05-02 (GREEN): In `src/python/reopt_pysam_vn/pysam/single_owner.py`:
  add a new field `zero_reference_plant_defaults: bool = False` to the
  `SingleOwnerInputs` dataclass (default `False` — existing behavior stays
  byte-identical for every current caller, satisfying CON-001/DEC-003); add a
  new module-level function `apply_clean_slate_financials(financial_model: Any) -> None`
  that sets the 12 Specification fields to `0.0` on the passed-in PySAM
  `Singleowner` model instance; call this function as the very last statement
  inside `_configure_financial_model` only when `inputs.zero_reference_plant_defaults`
  is `True` (every existing assignment inside `_configure_financial_model` stays
  in its current order, untouched); in `run_single_owner_model`'s returned
  dictionary, add `"zero_reference_plant_defaults": bool(inputs.zero_reference_plant_defaults)`
  to the existing `"inputs"` sub-dictionary, and when the flag is `True`, add a
  `"clean_slate"` string to the existing `"notes"` sub-dictionary describing
  which 12 fields were zeroed (when the flag is `False`, the `"notes"` dict must
  contain no `"clean_slate"` key at all — not an empty string, an absent key).
- [ ] TASK-05-03: Perform a read-only contamination audit. Run
  `grep -rn "run_single_owner_model\|_configure_financial_model\|SingleOwnerInputs" src/ scripts/ tests/`
  and enumerate every caller found. For each caller, determine by inspection
  whether any of its published or tracked outputs (`examples/`, `reports/*.md`
  numeric claims, deck-check registries under `scripts/python/integration/ceba_deck/`)
  embed the nonzero SAM reference-plant defaults documented in this plan's
  Specification. Write the findings to
  `reports/2026-07-22-single-owner-defaults-audit.md`: a table of every caller
  with a yes/no/uncertain contamination verdict, a re-run of one representative
  small project (e.g. a Ninhsim or KBC-style case, run locally with the flag off
  then on) reporting the IRR/NPV delta between the two runs as a concrete
  magnitude estimate, and an explicit "Decision required" section addressed to
  the repo maintainer covering whether/when to flip the default and whether any
  historical golden number needs a documented, human-approved restatement. Make
  no code changes and no golden-file changes as part of this task — it is
  read-only analysis captured in a markdown report.
- [ ] TASK-05-04: If a KBC-style cross-check script exists at
  `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py` (verify with
  `Test-Path` before editing), update any docstring reference to a manually
  reimplemented clean-slate calculation to instead point at the new
  `apply_clean_slate_financials` library function as the durable, tested
  replacement — a one-line comment change only; the script's own behavior and
  output remain frozen and unchanged (it exists as a historical comparison
  harness, not a maintained tool).
- [ ] TASK-05-05: Run the full local suite, with particular attention to
  `tests/python/webapp/test_golden_parity.py` (must pass unmodified, zero
  diffs against `examples/`), commit, push, and confirm CI is `success`.

**File Changes**
- `src/python/reopt_pysam_vn/pysam/single_owner.py` (modify): add the
  `zero_reference_plant_defaults` field, the `apply_clean_slate_financials`
  function, the conditional call at the end of `_configure_financial_model`, and
  the two output-dictionary additions in `run_single_owner_model`. Every
  existing line inside `_configure_financial_model` stays exactly as-is,
  including assignment order.
- `tests/python/pysam/test_single_owner_clean_slate.py` (create): the tests
  described below.
- `reports/2026-07-22-single-owner-defaults-audit.md` (create): the audit
  findings and "Decision required" section (this file is a tracked markdown
  report, consistent with the repo's convention that `reports/*.md` are tracked
  while `reports/*.html` are not).
- `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py` (modify,
  only if it exists): one docstring-comment line per TASK-05-04; no behavior
  change.

**Function Signatures**
- `apply_clean_slate_financials(financial_model: Any) -> None` — sets exactly
  the 12 `FinancialParameters` fields listed in the Specification to `0.0` on a
  PySAM `Singleowner` model instance, in place; returns nothing. Typed `Any`
  because PySAM's generated modules are untyped at the Python level and this
  module is outside the mypy CI gate per CON-004. Implementation should use
  plain `setattr`-equivalent assignment (direct attribute assignment, e.g.
  `financial_model.FinancialParameters.insurance_rate = 0.0`) so that a renamed
  or removed PySAM attribute in a future SAM version raises an `AttributeError`
  loudly at call time rather than silently doing nothing.
- `SingleOwnerInputs.zero_reference_plant_defaults: bool = False` — new
  dataclass field on the existing `SingleOwnerInputs` class; when `True`,
  `run_single_owner_model`'s finance outputs have the 12 US-reference-plant cost
  defaults zeroed instead of left at SAM's built-in values.

**Test Specs**
- Default-off regression guard: build a `SingleOwnerInputs` via
  `build_single_owner_inputs(1000.0)` (flag defaults to `False`), run it through
  the same PySAM model-construction sequence `run_single_owner_model` uses
  internally (or call `_configure_financial_model` directly on a freshly
  constructed `Singleowner` model, matching the pattern in this plan's verified
  Context Snapshot), then assert
  `financial_model.FinancialParameters.construction_financing_cost == 2_866_500.0`
  and `financial_model.FinancialParameters.insurance_rate == 0.5` — proving
  legacy behavior is preserved exactly when the flag is off.
- Flag-on zeroing: same setup with
  `build_single_owner_inputs(1000.0, zero_reference_plant_defaults=True)` → all
  12 Specification fields read exactly `0.0` after `_configure_financial_model`
  runs (including the five that were already `0.0` before this change:
  `cost_debt_closing`, `equip1_reserve_cost`, `equip2_reserve_cost`,
  `equip3_reserve_cost`, `salvage_percentage` — asserting all 12 rather than
  only the 7 that change is a defense against a future SAM version silently
  introducing a nonzero default for one of the already-zero fields).
- End-to-end direction: run `run_single_owner_model` twice with identical small-
  project inputs (`system_capacity_kw=1000.0`, `installed_cost_usd=550_000.0`,
  `ppa_price_input_usd_per_kwh=0.065`, all other fields at their dataclass
  defaults), once with the flag `False` and once `True` → the clean-slate run's
  NPV-equivalent output metric is strictly greater than the legacy run's (zeroing
  cost defaults can only improve or leave unchanged the project's financial
  outcome, never worsen it); the flag-`True` run's dictionary has
  `["inputs"]["zero_reference_plant_defaults"] == True` and a `"clean_slate"` key
  present under `["notes"]`; the flag-`False` run's dictionary has
  `["inputs"]["zero_reference_plant_defaults"] == False` and **no**
  `"clean_slate"` key under `["notes"]` at all.
- Golden-parity guard (not a new test, a re-run of an existing one):
  `tests/python/webapp/test_golden_parity.py` passes with zero diff against
  `examples/samsung-ttc_combined-decision.example.json`, proving this phase's
  default-`False` behavior did not alter the Samsung/TTC path's output in any
  way.

**Dependencies**
- PHASE-02 (a settled marker/xfail landscape so this phase's suite runs are
  interpretable in isolation). Requires the local `.venv` PySAM 7.1.0
  installation (already confirmed present).

**Exit Criteria**
- [ ] All new tests in `test_single_owner_clean_slate.py` pass locally under
  `.venv`; full suite `0 failed`; CI run on `main` is `success`.
- [ ] `tests/python/webapp/test_golden_parity.py` passes with zero diff to
  `examples/`.
- [ ] `reports/2026-07-22-single-owner-defaults-audit.md` exists, lists every
  caller found by the TASK-05-03 grep, and contains a "Decision required"
  section explicitly addressed to the repo maintainer.
- [ ] `git diff --stat examples/` produces no output for the entire phase (no
  file under `examples/` is touched at any point).

**Phase Risks**
- **RISK-05-01:** The audit (TASK-05-03) discovers that the Samsung/TTC golden
  itself was produced with the phantom reference-plant defaults still active.
  Mitigation: this phase is designed to only *report* such a finding in the
  audit's "Decision required" section; CON-001 forbids touching the golden file
  in this sprint regardless of what the audit finds — any restatement is a
  separate, later, human-approved change.
- **RISK-05-02:** A PySAM attribute name in the Specification's 12-field list
  differs from what a future or different PySAM version exposes (e.g. if the
  CI-pinned version from PHASE-02 differs from a developer's local version).
  Mitigation: the field list was independently re-verified in this plan against
  the exact locally-installed PySAM 7.1.0 by direct execution (see Context
  Snapshot for the observed default values); PHASE-02 pins CI to the same
  version; `apply_clean_slate_financials` uses direct attribute assignment so a
  missing/renamed attribute raises an immediate, loud `AttributeError` rather
  than silently no-op'ing.

## Gotchas

- **Always run `$env:PYTHONPATH = ""` before every pytest invocation.** A
  polluted global `PYTHONPATH` on the primary dev machine shadows the `.venv`
  FastAPI/pydantic install and produces `ModuleNotFoundError: pydantic_core._pydantic_core`,
  which looks like a genuine test failure but is purely an environment artifact.
- **`xfail(strict=False)` vs `xfail(strict=True)`:** use `strict=False` for the
  numeric-drift tests (ASM-004/ASM-005) so they keep executing and any future
  recovery is visible as `XPASS` rather than invisible. The **one**
  `strict=True` xfail in this plan (the repo-invariants root-binary test, added
  in PHASE-02, removed in PHASE-03) is a deliberate cross-phase tripwire — do
  not add `strict=True` anywhere else without an equally clear reason.
- **`git rm --cached` vs plain `git rm`:** the deck `.pptx` files stay on disk
  (`--cached`, PHASE-03); the root PNGs and `requirements.txt` are fully deleted
  (plain `git rm`, PHASE-03). Do not swap these two operations.
- **`.gitignore` edits must be minimal and immediately re-checked** with
  `git status` — this repo has previously re-tracked unrelated files via a loose
  negation pattern.
- **1-hour timesteps mean kW numerically equals kWh per step** in all 8760-array
  arithmetic in this plan — never multiply by an extra hours-factor. Monthly
  peak sums use the non-leap-year `HOURS_PER_MONTH` list already defined in
  `two_part_tariff_sensitivity.py`.
- **VND magnititudes are large (10⁹-10¹⁰ range) but must still be asserted as
  exact floats** in the deterministic toy-profile test cases in PHASE-04 (e.g.
  `-6_132_000_000.0`), not approximations — the toy inputs are chosen so the
  arithmetic is exact in floating point.
- **PySAM/SAM percentage fields take percent (0-100), not fractions.** New code
  anywhere in this plan that sets a SAM percentage-type field must multiply a
  stored fraction by 100 first, matching the existing wrapper convention, or
  produce economics that are 100× wrong.
- **`_build_hourly_rates`/`_build_8760_rates` are underscore-prefixed "private"
  functions being imported cross-module in PHASE-04.** This is a deliberate,
  documented choice (ASM-008) to avoid duplicating TOU-window logic, not an
  oversight — if `preprocess.py` is ever refactored such that this import
  breaks, promote both functions to public names in the same commit rather than
  reimplementing their logic elsewhere.
- **`Path(__file__).resolve().parents[N]` path math breaks when a script moves
  one directory deeper.** Check both flat scripts relocated in PHASE-02 for this
  pattern and increment `N` by exactly 1 if present, or their imports of
  `reopt_pysam_vn` will silently resolve against a stale installed copy instead
  of the `src/python` source tree.
- **Never edit `examples/samsung-ttc_combined-decision.example.json`** under any
  circumstance in any phase of this plan — two independent test files
  (`test_samsung_ttc_parity.py`'s non-quarantined test and `test_golden_parity.py`)
  gate this file bit-exactly.
- **`git worktree remove` refuses to act on a dirty working tree by default** —
  treat that refusal as the safety net it is; do not override it with `--force`
  in PHASE-01 without first re-confirming per ASM-011 that the refusal is a
  false positive.

## Verification Strategy

- **TEST-001 (all phases):**
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` →
  the final summary line reports `0 failed` (nonzero `xfailed`/`xpassed`/
  `skipped` counts are acceptable and expected after PHASE-02).
- **TEST-002 (PHASE-02):**
  `Rename-Item NREL_API.env NREL_API.env.bak; $env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine" -q; Rename-Item NREL_API.env.bak NREL_API.env`
  → `0 failed` — proves the exact CI test selection passes with no NREL key file
  present.
- **TEST-003 (all phases, after each push):** `gh run list --limit 1` → the
  latest run against `main` shows `completed success`.
- **TEST-004 (PHASE-01):** `git worktree list` → shows only the primary working
  directory; no `claude/*` entries remain (barring a documented ASM-011
  exception).
- **TEST-005 (PHASE-03):** `git ls-files ceba-review` → no `.pptx` output;
  `git ls-files requirements.txt` → empty;
  `git check-ignore "ceba-review/cong bess session.pptx"` → exit code `0`.
- **TEST-006 (PHASE-04):**
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/reopt/test_two_part_tariff.py -q`
  → all pass, including the exact `-6_132_000_000.0` and `-3_307_032_000.0`
  expectations.
- **TEST-007 (PHASE-04, only on a machine with Saigon18 artifacts present):**
  `.venv\Scripts\python.exe scripts/python/reopt/two_part_tariff_sensitivity.py`
  → output JSON's base-case card has `energy_delta_vnd < 0` and a negative net
  impact at the default voltage level.
- **TEST-008 (PHASE-05):**
  `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/pysam/test_single_owner_clean_slate.py tests/python/webapp/test_golden_parity.py -q`
  → all pass; then `git diff --stat examples/` → no output at all.
- **MANUAL-001 (PHASE-03):** The NREL Developer Network account owner rotates
  the API key at the issuing portal and updates the local, git-ignored
  `NREL_API.env` file; afterward, confirm a live solve still succeeds, e.g. via
  `scripts/python/reopt/solve_via_api.py` or the web app's deal-submission flow.
- **OBS-001 (PHASE-02):** In the green CI run's log output, the pytest summary
  line's `deselected` count is nonzero and roughly matches the number of tests
  carrying the three new markers — confirming the filter is actively excluding
  tests rather than the overall suite having silently shrunk for an unrelated
  reason.

## Risks and Alternatives

- **RISK-001:** Marker-based CI quarantine narrows what CI actually exercises,
  and a future maintainer could mistake "CI is green" for "the full pipeline is
  tested." Mitigation: the three markers are self-documenting directly in
  `pyproject.toml`; `activeContext.md` records the exclusion rationale
  explicitly; the repo's own already-scoped-but-out-of-scope-here
  offline/frozen-resource solve mode is the intended future path to restoring
  full-pipeline CI coverage.
- **RISK-002:** Running two of this plan's phases concurrently in separate
  sessions could collide on shared files (`pyproject.toml`, `.github/workflows/ci.yml`,
  `activeContext.md` are each touched by multiple phases). Mitigation: phases
  are explicitly sequenced by their stated Dependencies; execute them in order,
  one at a time, never in parallel.
- **ALT-001:** Fix CI by committing the missing `artifacts/` fixture files
  instead of marking the dependent tests — rejected: re-tracking regenerable
  binary/solve-output files reverses the repo's own deliberate 2026-06-12
  de-bloat decision and re-bloats the repository.
- **ALT-002:** Rewrite git history (`git filter-repo`) to purge the leaked NREL
  key — rejected: rotation at the issuing portal fully remediates the exposure;
  a history rewrite breaks every existing clone and worktree for no additional
  security benefit once the key is dead (CON-002).
- **ALT-003:** Flip `zero_reference_plant_defaults` to `True` by default
  immediately in PHASE-05 — rejected: any existing caller in the Samsung/offsite
  finance path could have its golden numbers shift silently; the audit-then-
  human-decision path (DEC-003) preserves CON-001 while still delivering the
  opt-in capability now.
- **ALT-004:** Patch the two-part tariff fix directly into the script without
  extracting a library module — rejected: script-only logic that reads
  machine-local artifact files is exactly the untestable pattern this repo is
  trying to move away from; a library module makes the arithmetic unit-testable
  against synthetic toy profiles with no dependency on artifacts or PySAM.
- **ALT-005:** Defer the worktree cleanup (PHASE-01) to the very end of the
  sprint, after the correctness phases — rejected: it has zero dependency on any
  other phase, carries essentially zero risk once ASM-011's checks pass, and
  doing it first means every subsequent `git worktree list` / disk-usage check
  during the rest of the sprint reflects the already-cleaned state.

## Suggested Next Step

Execute PHASE-01 first (fastest, lowest-risk, fully independent), then PHASE-02.
PHASE-02's exit criteria — a green local suite, a green CI-filter simulation with
`NREL_API.env` renamed away, and a green GitHub Actions run on `main` — are
independently verifiable before PHASE-03 begins, and PHASE-03/04/05 each re-run
TEST-001 and TEST-003 so any regression localizes cleanly to a single phase
rather than being discovered only at the end of the sprint.
