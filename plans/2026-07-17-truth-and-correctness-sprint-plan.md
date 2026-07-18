---
title: "Truth and Correctness Sprint — CI Green Gate, Security Hygiene, Two-Part Tariff Fix, Single Owner Clean-Slate"
date: "2026-07-17"
status: "draft"
request: "research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md — turn the P0a+P0b+P1+P2 'truth and correctness' sprint into a multi-phase implementation plan"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md"
---

# Plan: Truth and Correctness Sprint — CI Green Gate, Security Hygiene, Two-Part Tariff Fix, Single Owner Clean-Slate

## Objective

Restore an honest, green CI gate on `main` (it is currently red with 22 failures — the gate added 2026-07-15 provides negative assurance), close the third-cycle-open security/hygiene items (leaked NREL key exposure, tracked deck binaries, broken `.gitignore` globs), and fix two live correctness defects: the Decree 146/2025 two-part tariff sensitivity script whose result has the wrong *sign* for high-load-factor sites, and the PySAM Single Owner wrapper that silently inherits ~100 MW-reference-plant cost defaults (a flat $2,866,500 construction-financing charge among them) into sub-2 MWp Vietnam C&I project economics. This sprint is the declared precondition for every already-planned strategic phase (config-driven case runner, offline solve mode, Julia archive).

## Context Snapshot

- **Current state:** GitHub Actions CI on `main` (`.github/workflows/ci.yml`, added commit `7255ca9`) fails every run: run `29559973037` on HEAD `3d61d64` = **22 failed, 525 passed, 30 skipped**. Failure classes: (a) 10+ tests read git-ignored files under `artifacts/results/` and `artifacts/reports/` that exist only on the primary dev machine; (b) `nrel-pysam>=7.1` unpinned in CI resolves to a newer PySAM whose `Pvwattsv8` API changed (`no attribute 'new'`); (c) the three Samsung/TTC "bit-exact" parity tests in `tests/python/analysis/test_samsung_ttc_parity.py` drift up to 112% off-machine; (d) 5 webapp tests fail only in CI because `webapp/jobs.py:152` calls `service.load_nrel_api_key()`, which reads the git-ignored `NREL_API.env` present locally but absent in CI; (e) 5 tests are also red locally (numeric drift, known since 2026-07-04, unowned). Separately: an old NREL API key is recoverable from git history (commits `3911032`, `b14bc0b`); three `ceba-review/*.pptx` deck binaries are tracked despite `.gitignore` entries (two of the ignore globs are broken glob character classes, e.g. `*[repo-checked].pptx`); two 0.5 MB screenshots (`phase04_new_deal_*.png`) are tracked at repo root; `requirements.txt` duplicates `pyproject.toml` dependencies; a new analysis script sits at the forbidden flat path `scripts/python/2026-07-17_kbc_proforma_pysam_crosscheck.py` (untracked) and references a plan file that does not exist in this repo; `scripts/python/reopt/two_part_tariff_sensitivity.py` adds the Decree 146/2025 demand charge on top of baseline single-component TOU energy rates without swapping in the ~30–38% lower trial energy rates (Ca), overstating the tariff's cost impact so badly the sign flips for high-load-factor sites; `src/python/reopt_pysam_vn/pysam/single_owner.py::_configure_financial_model` never touches SAM Single Owner's US-reference-plant defaults (insurance, construction financing, debt fees, reserves, property tax, salvage).
- **Desired state:** CI on `main` is green and honest: non-portable tests carry registered pytest markers (`requires_artifacts`, `golden_machine`, `network`) and are excluded in CI; PySAM is pinned in CI to the locally-used version; webapp tests are hermetic (no dependence on `NREL_API.env`); the 5 local reds are each fixed, `xfail`-annotated with a reason, or reclassified; a repo-invariants pytest module mechanically enforces the flat-script ban, the no-tracked-artifacts rule, and the no-root-binaries rule. The pptx binaries and root PNGs are untracked, the `.gitignore` globs actually match, `requirements.txt` is gone, and the key-rotation requirement is documented for the human account owner. The two-part tariff script re-prices the 8760 energy series with trial Ca rates (via a new tested library module) before applying the demand charge, and uses the real Decree 146 trial capacity charge by voltage level. `SingleOwnerInputs` exposes an opt-in clean-slate flag that zeroes the 12 US-reference cost defaults, with tests, and an audit report records which existing result sets are contaminated — without changing any golden number.
- **Key repo surfaces:** `.github/workflows/ci.yml`, `pyproject.toml`, `.gitignore`, `tests/python/webapp/conftest.py`, `tests/python/analysis/test_samsung_ttc_parity.py`, `tests/python/integration/{test_saigon18_compare,test_saigon18_phase3,test_regime_engine_smoke,test_ninhsim_cppa,test_capacity_factor_benchmark}.py`, `tests/python/pysam/{test_single_owner_phase4,test_strike_price_discovery}.py`, `scripts/python/reopt/two_part_tariff_sensitivity.py`, `data/vietnam/vn_tariff_2025.json`, `src/python/reopt_pysam_vn/reopt/preprocess.py`, `src/python/reopt_pysam_vn/pysam/single_owner.py`, `src/python/reopt_pysam_vn/webapp/{service.py,jobs.py}`, `scripts/python/2026-07-17_kbc_proforma_pysam_crosscheck.py`, `scripts/python/_extract_pptx.py`, `README.md`, `activeContext.md`, `docs/pitfalls.md`.
- **Out of scope:** The strategic-lens phases 3–6 (offline/frozen-resource solve mode, Julia archive, config-driven case runner, settlement performance); any git-history rewrite (`git filter-repo`) — key rotation makes the historical copy harmless; flipping the Single Owner clean-slate default ON (audit-only this sprint; a default flip could touch the bit-exact Samsung golden and needs a human decision); restating any golden/parity number; ruff configuration and the 181-violation lint backlog; webapp UI changes.

## Environment & Conventions

- **Stack:** Python 3.12 via the repo-local virtualenv `.venv` (Windows: `.venv\Scripts\python.exe`). **PySAM 7.1.0 (`nrel-pysam`) exists only inside `.venv`** — system Python 3.14 has no PySAM wheel and code silently falls back to synthetic solar profiles, which changes numbers. Always use the `.venv` interpreter. Package layout: setuptools, `package-dir = {"" = "src/python"}`. Julia exists in the repo but nothing in this plan touches it.
- **Setup:** From repo root, PowerShell: `.venv\Scripts\python.exe -m pip install -e ".[webapp]"` (add `pytest` if missing: `.venv\Scripts\python.exe -m pip install pytest`).
- **Build / Run:** No build step. Web app (not needed for this plan): `$env:PYTHONPATH = "src/python"; .venv\Scripts\python.exe -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000`.
- **Test:** Full suite: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` — single test: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp/test_jobs.py::test_background_solve_reaches_done_when_mocked -q`.
- **Conventions & traps:**
  - **`PYTHONPATH` gotcha:** a stray global `PYTHONPATH` (points at an unrelated venv on the primary machine) breaks webapp tests with `ModuleNotFoundError: pydantic_core._pydantic_core`. Clear it (`$env:PYTHONPATH = ""`) before every pytest run; pytest resolves the package via `pythonpath = ["src/python"]` in `pyproject.toml`.
  - All commands above are **PowerShell**. CI (`ci.yml`) is bash on ubuntu — never paste `$env:` syntax into it.
  - **JSON reads use `encoding="utf-8-sig"`** everywhere (tolerates Windows UTF-8 BOM). Every new reader in this plan must match.
  - **Units:** EVN tariffs are **VND/kWh**; capacity charges **VND/kW-month**; PySAM finance is **USD**; `two_part_tariff_sensitivity.py` converts at `EXCHANGE_RATE_VND_PER_USD = 26_000.0`. SAM percentage fields take **percent, not fraction** (the wrapper multiplies fractions by 100 — keep that convention).
  - **Bit-exact parity gates:** `tests/python/analysis/test_samsung_ttc_parity.py` and `tests/python/webapp/test_golden_parity.py` compare against `examples/samsung-ttc_combined-decision.example.json`. Any change that alters Samsung/TTC output is a defect, not drift.
  - **Structural-move rule:** after ANY file move, run the FULL Python suite, never a subset; grep for **bare** module names (e.g. `_extract_pptx`), not path forms, before moving files.
  - **`.gitignore` negations have burned this repo** — make only minimal, precisely-scoped edits and run `git status` immediately after.
- **Repo map:**
  - `src/python/reopt_pysam_vn/` — the package: `analysis/` (public API), `webapp/` (FastAPI app; `service.py` has `load_nrel_api_key()` reading env var `NREL_DEVELOPER_API_KEY` then `NREL_API.env`), `integration/` (deal engines), `pysam/` (`single_owner.py`, `config.py`, `metrics.py`, `cashflow.py`), `reopt/` (`preprocess.py` builds 8760 TOU rate series from `data/vietnam/vn_tariff_2025.json`), `common/`.
  - `scripts/python/{reopt,pysam,integration}/` — canonical script locations; the flat level `scripts/python/*.py` is banned (rule dated 2026-06-12) but currently violated by `_extract_pptx.py` (tracked) and `2026-07-17_kbc_proforma_pysam_crosscheck.py` (untracked).
  - `tests/python/{analysis,integration,pysam,reopt,webapp,ingestion}/` — pytest suite; `tests/python/webapp/conftest.py` already blocks live NREL calls by monkeypatching `service.solve_onsite_via_nrel`.
  - `artifacts/` — git-ignored, machine-local solve outputs; several tests wrongly depend on them.
  - `data/vietnam/vn_tariff_2025.json` — versioned EVN tariff data with `_meta` envelope; code reads the `"data"` block. Two-part trial data at `data → demand_charge → two_part_tariff_trial`.

## Research Inputs

- From `research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md`:
  - CI run `29559973037` (2026-07-17, HEAD `3d61d64`) failed 22 / passed 525 / skipped 30; both post-merge runs on `main` are red. `ci.yml` filters `-m "not network"` but no `network` marker is registered and no test carries one, so the filter selects everything.
  - Verified failure taxonomy (full worklist in PHASE-01 tasks): artifact-dependent tests, PySAM version drift (`Pvwattsv8.new` missing in CI's newer PySAM), Samsung parity drifting 112% off-machine, 5 webapp tests failing only where `NREL_API.env` is absent, plus the 5 locally-known numeric reds.
  - The KBC pro-forma cross-check script had to re-implement `run_single_owner_model` because the shared wrapper leaves SAM Single Owner's ~100 MW-reference defaults untouched: `construction_financing_cost` defaults to a flat **$2,866,500**, plus nonzero insurance rate, debt fees/closing, working/DSCR/equipment reserves, assessed property tax, reserves interest, and salvage percentage — these swamp sub-2 MWp project economics.
  - The two-part tariff gap is fully specified in the script's own docstring and `activeContext.md`: re-price the 8760 energy series with trial Ca rates before computing the demand-charge delta. Net effect flips from +73B VND/yr extra cost to −53B VND/yr savings for a Saigon18-type profile (69.5% load factor); Factory A (~46% LF) is ≈ breakeven. Cross-reference: XanhTerra two-component tariff case study.
  - Convention decay is mechanical-enforcement territory: the flat-script rule lasted five weeks; the `.gitignore` pptx globs are glob **character classes** (`*[repo-checked]` matches one char of `{r,e,p,o,-,c,h,k,d}`), which is also the malformed pattern that crashes ruff's parser.
  - Lifted decisions: **DEC-201** quarantine non-portable tests via markers + pin PySAM now (a narrow green gate beats a broad red one); **DEC-202** Samsung bit-exact parity stays a local/pre-merge gate (`golden_machine` marker) until frozen resources make it portable; **DEC-203** Single Owner clean-slate is opt-in with legacy behavior preserved and an audit before any default flip; **DEC-204** the tariff fix outranks all strategic-phase work; **DEC-205** add a repo-invariants CI check.

## Assumptions and Constraints

- **ASM-001:** The primary dev machine has the `artifacts/results/**` files the artifact-dependent tests read, so those tests still pass locally after being marked. — **BINDING DEFAULT:** markers only change *selection*, never test bodies; if a marked test also fails locally for a non-artifact reason it falls under the PHASE-01 triage table instead.
- **ASM-002:** The local `.venv` PySAM version is exactly 7.1.0 (verify: `.venv\Scripts\python.exe -c "import PySAM; print(PySAM.__version__)"`). — **BINDING DEFAULT:** pin CI to the printed version; if it is not 7.1.0, pin to whatever the command prints.
- **ASM-003:** The two `test_regime_engine_smoke.py` CI failures (`test_cached_run_is_reused_when_manifest_is_successful`, `test_regime_matrix_no_solve_writes_complete_artifacts`) are caused by missing machine-local state, like the FileNotFoundError group. — **BINDING DEFAULT:** reproduce by running them locally with `artifacts/` temporarily renamed; if they then fail, mark `requires_artifacts`; if they still pass, they are genuinely CI-environment bugs — debug and fix within the phase.
- **ASM-004:** The three-of-five local red tests that are pure numeric drift (`test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`, `test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`, `test_strike_price_discovery.py::test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike`) cannot be root-caused inside this sprint. — **BINDING DEFAULT:** annotate each `@pytest.mark.xfail(reason="numeric benchmark drift, red since 2026-07-04, tracked in activeContext.md 'Known pre-existing test failures'", strict=False)` and keep them running (xfail, not skip).
- **ASM-005:** The two locally-red Samsung parity tests (`test_samsung_parity_full_tree_within_bar`, `test_samsung_parity_is_bit_exact`) indicate a real divergence (`developer_irr_fraction` computes `0.02898…` where the golden holds `None`), not tolerance noise. — **BINDING DEFAULT:** timebox root-cause to 2 hours using the repo's own procedure (run the tests at commit `fd8ceaf` — the last commit before the phase-1/phase-2 sessions — in a separate `git worktree` to classify code-change vs environment). If unresolved in the timebox, add `@pytest.mark.xfail(reason="parity divergence under investigation: developer_irr_fraction 0.0289 vs golden None; see plans/2026-07-17-truth-and-correctness-sprint-plan.md TASK-01-06", strict=False)` to exactly those two tests and record findings in `activeContext.md`. Do NOT regenerate the golden.
- **ASM-006:** Rotating the leaked NREL key requires the NREL developer-account owner (human); an executor cannot do it. — **BINDING DEFAULT:** PHASE-02 documents the rotation requirement in `README.md` and `activeContext.md` and verifies `NREL_API.env` is untracked; no history rewrite is performed.
- **ASM-007:** `scripts/python/_extract_pptx.py` at the flat level has importers among the ceba/deck scripts. — **BINDING DEFAULT:** before moving it, run `grep -rn "_extract_pptx" scripts/ tests/ src/` (bare name, per the structural-move rule); move it to `scripts/python/integration/_extract_pptx.py` and update every hit, then run the full suite.
- **ASM-008:** The exact function in `reopt/preprocess.py` that builds the baseline 8760 TOU rate series is discoverable by grep (`grep -n "8760\|tou\|rate" src/python/reopt_pysam_vn/reopt/preprocess.py`). — **BINDING DEFAULT:** reuse its TOU-window logic (which hours are peak/normal/off-peak per EVN rules) for the trial-rate series builder rather than re-deriving windows; if its interface cannot be reused cleanly, extract the window logic into the new `two_part_tariff.py` module and have both call it, leaving `preprocess.py` behavior byte-identical.
- **ASM-009:** Trial energy rates in `vn_tariff_2025.json` are ranges, not per-voltage scalars (`normal_hours_range: [1253, 1332]`, `peak_hours_range: [2162, 2251]`, `offpeak_hours_range: [843, 904]`, all VND/kWh). — **BINDING DEFAULT:** use the arithmetic midpoint of each range (normal 1292.5, peak 2206.5, off-peak 873.5 VND/kWh) and record the choice in the output JSON under `"trial_rate_basis": "range_midpoint"`.
- **ASM-010:** Saigon18 connects at 22 kV. — **BINDING DEFAULT:** the default trial capacity charge is `medium_voltage_22kv_to_110kv` = 235,414 VND/kW-month (EVN's trial targets customers "connected at ≥22kV"); expose `--voltage-level` so any of the four published rates can be selected.
- **ASM-011:** The workbook-derived project set in the KBC cross-check script is external to this repo. — **BINDING DEFAULT:** relocate the script unchanged except its docstring: replace the reference to the nonexistent `plans/2026-07-17-kbc-feedback-package-update-plan.md` with "per the Allotrope–KBC JV feedback-package plan (external workspace)".
- **CON-001:** Samsung/TTC golden output must not change: `tests/python/webapp/test_golden_parity.py` must pass unmodified at every commit of this sprint, and `examples/samsung-ttc_combined-decision.example.json` must not be edited.
- **CON-002:** No git-history rewrite. Untracking = `git rm --cached` only; files stay on disk.
- **CON-003:** All new JSON readers use `encoding="utf-8-sig"`.
- **CON-004:** New library code goes under `src/python/reopt_pysam_vn/`; scripts stay thin. The mypy CI gate covers only `analysis/` and `webapp/` — new modules in `reopt/` and `pysam/` are not gated but should still carry full type hints to match house style.
- **DEC-201..DEC-205:** As inlined under Research Inputs above.

## Specification

**Two-part tariff corrected economics (PHASE-03).** For an 8760-hour grid-import series `g(h)` in kW (1-hour steps, so kW ≡ kWh per step):

- Baseline annual energy cost: `B = Σ_h g(h) · r_base(h)` — `r_base(h)` is the existing single-component EVN TOU rate for hour `h` in VND/kWh (peak/normal/off-peak windows per EVN rules, as already encoded in `reopt/preprocess.py`).
- Trial annual energy cost: `T = Σ_h g(h) · r_trial(h)` — `r_trial(h)` is the two-part trial energy rate (Ca) for hour `h`: 2206.5 VND/kWh in peak windows, 1292.5 in normal, 873.5 in off-peak (range midpoints per ASM-009), using the SAME window classification as `r_base`.
- Energy re-pricing delta: `ΔE = T − B` (negative for every profile, since every Ca rate is below its baseline counterpart).
- Trial demand charge: `D = Cp · Σ_m P(m)` — `Cp` is the trial capacity charge in VND/kW-month (235,414 default per ASM-010); `P(m)` is the maximum hourly `g(h)` in calendar month `m` (existing `monthly_peaks()` logic, 12 months, non-leap-year hour counts).
- Net two-part impact for a given dispatch: `Δ = ΔE + D` in VND/yr. `Δ < 0` means the customer SAVES under the two-part trial tariff. This is the quantity the current script gets sign-wrong for high-load-factor sites because it computes `D` (at an obsolete 60,000 VND/kW-month placeholder) with `ΔE` implicitly 0.
- USD conversion: divide VND amounts by `EXCHANGE_RATE_VND_PER_USD` (26,000.0, unchanged).

**Single Owner clean-slate field set (PHASE-04).** When enabled, set exactly these `Singleowner.FinancialParameters` attributes to `0.0` after `_configure_financial_model`'s existing assignments: `insurance_rate`, `construction_financing_cost`, `cost_debt_fee`, `cost_debt_closing`, `months_working_reserve`, `dscr_reserve_months`, `equip1_reserve_cost`, `equip2_reserve_cost`, `equip3_reserve_cost`, `prop_tax_cost_assessed_percent`, `reserves_interest`, `salvage_percentage`. (12 fields; list verified against SAM's Singleowner module via the KBC cross-check harness.)

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Green, honest CI: markers, PySAM pin, hermetic webapp tests, red-test triage, repo-invariants test, flat-script relocations | None | Green `main` CI run; `pyproject.toml` markers; `tests/python/test_repo_invariants.py` |
| PHASE-02 | Security & hygiene: untrack binaries, fix `.gitignore` globs, drop `requirements.txt`, document key rotation | PHASE-01 (invariants test enforces the untracking) | Clean `git ls-files`; rotation instructions in README |
| PHASE-03 | Two-part tariff Ca re-pricing fix (TDD) with real trial capacity charges | PHASE-01 (green local suite as baseline) | `reopt_pysam_vn/reopt/two_part_tariff.py` + tests; corrected script output |
| PHASE-04 | Single Owner clean-slate mode + contamination audit (no golden changes) | PHASE-01 | Opt-in flag + tests; audit report in `reports/` |

## Detailed Phases

### PHASE-01 - CI Truth: Markers, Pin, Hermetic Tests, Triage, Invariants

**Goal**
`main`'s CI workflow passes, and what it excludes is explicit and machine-checkable rather than silently broken.

**Tasks**
- [ ] TASK-01-01: Register pytest markers. In `pyproject.toml` `[tool.pytest.ini_options]`, add:
  ```toml
  markers = [
    "network: makes real HTTP calls to external services; excluded in CI",
    "requires_artifacts: reads git-ignored machine-local files under artifacts/; excluded in CI",
    "golden_machine: bit-exact golden comparison only valid on the primary dev machine's resources; excluded in CI",
  ]
  ```
- [ ] TASK-01-02: Mark artifact-dependent tests `@pytest.mark.requires_artifacts` (module-level `pytestmark = pytest.mark.requires_artifacts` where every test in the file qualifies, else per-test):
  - `tests/python/integration/test_saigon18_compare.py::test_load_reopt_metrics_uses_actual_results_keys`
  - `tests/python/integration/test_saigon18_phase3.py` — all three failing tests (`test_load_reopt_delivery_profile_uses_actual_results_schema`, `test_load_reopt_metrics_splits_bess_dispatch_by_tariff_period`, `test_scenario_d_adjustment_adds_settlement_to_revenue_and_npv`)
  - `tests/python/pysam/test_single_owner_phase4.py` — all four failing tests (they read `artifacts/results/ninhsim/2026-04-01_ninhsim_scenario-b_optimized-cppa_reopt-results.json`)
  - `tests/python/pysam/test_strike_price_discovery.py` — both failing tests (they read `artifacts/reports/ninhsim/2026-04-04_ninhsim-single-owner-finance.json`)
- [ ] TASK-01-03: Classify the two `tests/python/integration/test_regime_engine_smoke.py` failures per ASM-003 (rename `artifacts/` → `artifacts_hold/` locally, run both tests, rename back) and either mark `requires_artifacts` or fix the CI-environment bug.
- [ ] TASK-01-04: Mark the whole of `tests/python/analysis/test_samsung_ttc_parity.py` with `pytestmark = pytest.mark.golden_machine` (all three tests, including the currently-CI-only failure `test_samsung_parity_headline_settlement_exact`). Leave `tests/python/webapp/test_golden_parity.py` untouched — it did not fail in CI.
- [ ] TASK-01-05: Make webapp tests hermetic. In `tests/python/webapp/conftest.py`, add an autouse fixture that monkeypatches `reopt_pysam_vn.webapp.service.load_nrel_api_key` to return the literal `"test-webapp-key"` (see Function Signatures). This fixes all five CI-only webapp failures (`test_jobs.py` ×4, `test_pages.py::test_multipart_deal_submission_queues_a_background_solve`), which currently depend on the git-ignored `NREL_API.env` existing. Check `tests/python/webapp/test_jobs.py::test_completed_run_writes_provenance_with_key_fingerprint` still passes (the fingerprint becomes `sha256(b"test-webapp-key").hexdigest()[:12]`, deterministic).
- [ ] TASK-01-06: Triage the five locally-red tests: apply ASM-004 xfail annotations to the three numeric-drift tests and ASM-005 (2-hour timeboxed worktree investigation, then xfail) to the two Samsung parity tests. Update the "Known pre-existing test failures" section of `activeContext.md` to state the new xfail status and reasons.
- [ ] TASK-01-07: Pin PySAM in CI. In `.github/workflows/ci.yml`, change the install line to `pip install -e ".[webapp]" mypy pytest "nrel-pysam==7.1.0"` (version per ASM-002), and change the pytest invocation to `python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine" -q`. Leave the mypy step and its explanatory ruff comment unchanged.
- [ ] TASK-01-08: Create `tests/python/test_repo_invariants.py` with three tests using `git ls-files` via `subprocess` (see Test Specs): flat-script ban, no tracked `artifacts/`, no tracked root-level binaries (`*.png`, `*.pptx`, `*.xlsx`, `*.xlsm` directly at repo root). Until PHASE-02 untracks the offenders, the root-binary test WILL fail — implement it complete but mark it `@pytest.mark.xfail(reason="tracked binaries removed in PHASE-02 of plans/2026-07-17-truth-and-correctness-sprint-plan.md", strict=True)` and remove the annotation in PHASE-02 (strict=True makes forgetting impossible: the moment the binaries are untracked, the xfail becomes an error until the mark is deleted).
- [ ] TASK-01-09: Relocate flat scripts. Per ASM-007, `git mv scripts/python/_extract_pptx.py scripts/python/integration/_extract_pptx.py` after grepping for the bare name and updating importers. Move (plain `mv`; it is untracked) `scripts/python/2026-07-17_kbc_proforma_pysam_crosscheck.py` → `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py`, apply the ASM-011 docstring edit, fix its `parents[2]` repo-root computation to `parents[3]` (one directory deeper now), and `git add` it.
- [ ] TASK-01-10: Run the full local suite; then commit, push, and confirm the GitHub Actions run on `main` is green.

**File Changes**
- `pyproject.toml` (modify): add the `markers` list to `[tool.pytest.ini_options]`. Leave dependencies, mypy config, and packaging untouched.
- `.github/workflows/ci.yml` (modify): pin `nrel-pysam==7.1.0` in the install step; expand the `-m` filter. Nothing else.
- `tests/python/webapp/conftest.py` (modify): add the autouse `stub_nrel_api_key` fixture next to the existing `block_live_nrel_calls` fixture.
- `tests/python/integration/test_saigon18_compare.py`, `tests/python/integration/test_saigon18_phase3.py`, `tests/python/pysam/test_single_owner_phase4.py`, `tests/python/pysam/test_strike_price_discovery.py`, `tests/python/integration/test_regime_engine_smoke.py` (modify): marker annotations only; no test-body changes.
- `tests/python/analysis/test_samsung_ttc_parity.py` (modify): `pytestmark = pytest.mark.golden_machine` + per-ASM-005 xfail on the two locally-red tests.
- `tests/python/integration/test_capacity_factor_benchmark.py`, `tests/python/integration/test_ninhsim_cppa.py` (modify): ASM-004 xfail annotations.
- `tests/python/test_repo_invariants.py` (create): three invariant tests.
- `scripts/python/integration/_extract_pptx.py` (create via `git mv` from `scripts/python/_extract_pptx.py`) plus updates to any importer found by the ASM-007 grep.
- `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py` (create via move of the untracked flat file): docstring reference fix + `parents[3]` fix; no logic changes.
- `activeContext.md` (modify): update the known-failures section to record xfail status and the parity-investigation outcome.

**Function Signatures**
- `stub_nrel_api_key(monkeypatch: pytest.MonkeyPatch) -> None` — autouse pytest fixture in `tests/python/webapp/conftest.py`; monkeypatches `reopt_pysam_vn.webapp.service.load_nrel_api_key` to `lambda: "test-webapp-key"`; returns nothing.
- `_tracked_files(prefix: str = "") -> list[str]` — helper in `test_repo_invariants.py`; runs `git ls-files -- <prefix>` from the repo root via `subprocess.run(..., capture_output=True, text=True)` and returns the non-empty output lines.

**Test Specs**
- `test_no_flat_python_scripts()`: `_tracked_files("scripts/python")` filtered to paths matching `scripts/python/<name>.py` (exactly one path segment after `scripts/python/`) → expected `[]`. After TASK-01-09 this passes; before it, it fails on `scripts/python/_extract_pptx.py`.
- `test_no_tracked_artifacts()`: `_tracked_files("artifacts")` → expected `[]` (true already today).
- `test_no_root_level_binaries()`: `_tracked_files()` filtered to paths with no `/` and suffix in `{".png", ".pptx", ".xlsx", ".xlsm"}` → expected `[]`. Today it would return `["phase04_new_deal_initial.png", "phase04_new_deal_scrolled.png"]` — hence the strict xfail until PHASE-02. (Note: `ceba-review/*.pptx` and `scenarios/case_studies/regina/Regina.xlsx` contain `/` and are NOT root-level; `Regina.xlsx` is a live test input and stays tracked.)
- Hermetic-key check: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp -q` passes with `NREL_API.env` temporarily renamed to `NREL_API.env.bak` (rename it back afterwards) — proving no webapp test depends on the real key file.
- CI-filter simulation: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine" -q` → `0 failed` locally.

**Dependencies**
- None (first phase). `gh` CLI or the GitHub web UI to confirm the Actions run.

**Exit Criteria**
- [ ] Full local suite: `0 failed` (xfails report as `xfailed`, not `failed`).
- [ ] CI-filter simulation command above: `0 failed` locally with `NREL_API.env` renamed away.
- [ ] The next GitHub Actions run on `main` concludes `success`.
- [ ] `pytest --collect-only -m requires_artifacts` lists at least the 10 marked tests; `-m golden_machine` lists the 3 parity tests.

**Phase Risks**
- **RISK-01-01:** The Samsung parity divergence (ASM-005) turns out to be a live regression introduced by the phase-1/phase-2 sessions (e.g. the `voltage_level` default fix noted in the 2026-07-15 final report). Mitigation: the worktree bisection distinguishes this; if it IS a regression, fixing it supersedes the xfail and the fix must leave `test_golden_parity.py` green (CON-001).
- **RISK-01-02:** Pinning `nrel-pysam==7.1.0` fails to install on ubuntu-latest/py3.12. Mitigation: fall back to the nearest installable 7.1.x and re-run; the marker filter already excludes the tests most sensitive to PySAM minutiae.

### PHASE-02 - Security & Hygiene: Untrack Binaries, Fix Globs, One Dependency Source, Key Rotation

**Goal**
`git ls-files` contains no deck binaries or root screenshots, `.gitignore` patterns actually match the files they name, dependencies have one source of truth, and the leaked-key rotation obligation is written down where the account owner will see it.

**Tasks**
- [ ] TASK-02-01: Untrack the three deck binaries (files stay on disk, CON-002): `git rm --cached "ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx" "ceba-review/cong bess session [reviewed].pptx" "ceba-review/cong bess session.pptx"`.
- [ ] TASK-02-02: Fix the `.gitignore` character-class bug. In the July-2026-deck section, replace the two bracket patterns with escaped literals: `ceba-review/*[repo-checked].pptx` → `ceba-review/*\[repo-checked\].pptx` and `ceba-review/*[*reviewed*].pptx` → `ceba-review/*\[reviewed\].pptx`. Touch nothing else in the file (the negation-trap rule). Verify each of the three untracked filenames with `git check-ignore -v "<name>"` — every one must match a rule.
- [ ] TASK-02-03: Delete the tracked root screenshots (`git rm phase04_new_deal_initial.png phase04_new_deal_scrolled.png` — history retains them; they are superseded webapp-session evidence). Remove the strict-xfail annotation from `test_no_root_level_binaries` in `tests/python/test_repo_invariants.py` (TASK-01-08 contract).
- [ ] TASK-02-04: Single dependency source: `git rm requirements.txt`; in `README.md` "Python Setup", replace `python -m pip install -r requirements.txt` + `python -m pip install -e .` with the single line `python -m pip install -e ".[webapp]"`.
- [ ] TASK-02-05: Document key rotation. Add a short "Security note — API key rotation required" subsection to `README.md` (under Quick Start) and a line in `activeContext.md`: an NREL Developer API key was committed historically (commits `3911032`, `b14bc0b`) and remains recoverable from git history; the account owner must rotate it at the NREL Developer Network account page and update the local git-ignored `NREL_API.env`; no history rewrite is planned (rotation is the remediation). Per ASM-006 the rotation itself is a human step — record it, do not attempt it.
- [ ] TASK-02-06: Run the full suite (the invariants tests now enforce all of the above), `git status` to confirm no accidental re-tracking, commit, push, confirm CI green.

**File Changes**
- `.gitignore` (modify): the two escaped-bracket lines only.
- `README.md` (modify): Python Setup consolidation + security note. Leave all other sections alone.
- `activeContext.md` (modify): key-rotation line.
- `requirements.txt` (delete via `git rm`).
- `phase04_new_deal_initial.png`, `phase04_new_deal_scrolled.png` (delete via `git rm`).
- `ceba-review/*.pptx` ×3 (untrack via `git rm --cached`; files remain on disk).
- `tests/python/test_repo_invariants.py` (modify): drop the strict xfail.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
- `git ls-files ceba-review` → empty output.
- `git ls-files -- "*.png"` filtered to root-level → empty; `tests/python/test_repo_invariants.py::test_no_root_level_binaries` passes un-xfailed.
- `git check-ignore -v "ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx"` → prints a matching `.gitignore` rule (exit code 0). Same for the other two pptx names.
- `git ls-files NREL_API.env` → empty (already true; regression guard).

**Dependencies**
- PHASE-01 (the invariants test and its xfail hand-off).

**Exit Criteria**
- [ ] All four Test Specs above hold.
- [ ] Full local suite `0 failed`; CI run on `main` green.
- [ ] README contains the rotation note with both commit hashes.

**Phase Risks**
- **RISK-02-01:** A test or script reads one of the untracked pptx files by path and breaks on machines that clone fresh. Mitigation: files remain on disk locally; the full-suite run in TASK-02-06 catches any tracked-path dependency (the deck pipeline scripts already treat deck binaries as local-only inputs per the 2026-06-26 plan's CON-002).

### PHASE-03 - Two-Part Tariff Correction: Trial Energy Rates (Ca) + Real Capacity Charge (Cp)

**Goal**
`two_part_tariff_sensitivity.py` reports the *net* two-part-tariff impact — lower trial energy rates AND the demand charge — instead of demand-charge-only on top of baseline rates, eliminating the sign error for high-load-factor profiles. Logic lives in a tested library module; the script becomes a thin CLI.

**Tasks**
- [ ] TASK-03-01 (RED): Create `tests/python/reopt/test_two_part_tariff.py` with the failing tests in Test Specs below, importing from `reopt_pysam_vn.reopt.two_part_tariff` (module does not exist yet). Run to confirm collection error / failure.
- [ ] TASK-03-02 (GREEN): Create `src/python/reopt_pysam_vn/reopt/two_part_tariff.py` implementing the Specification formulas. Reuse the TOU-window classification from `reopt/preprocess.py` per ASM-008 (extract, don't duplicate; `preprocess.py` output must stay byte-identical — cross-validation Layer 3 depends on it).
- [ ] TASK-03-03: Rewire `scripts/python/reopt/two_part_tariff_sensitivity.py`: load the tariff data (`data/vietnam/vn_tariff_2025.json`, `utf-8-sig`, read the `"data"` block), build baseline and trial rate series, compute `ΔE` from the REopt grid-import series, replace the hardcoded `DECREE_146_PILOT_RATE_VND_PER_KW_MONTH = 60_000` base case with the trial `capacity_charge_vnd_per_kw_month` selected by a new `--voltage-level` argument (choices = the four keys in the data file; default per ASM-010), keep the existing rate sweep, and add `ΔE` and `Δ = ΔE + D` (VND and USD) to every sweep row and the output card. Update the docstring: delete the `!!!!! KNOWN MODELING GAP` block, describe the corrected method, keep the XanhTerra cross-reference.
- [ ] TASK-03-04: Close out the documentation trail: remove the "Two-part tariff sensitivity — missing energy rate reduction" entry from `activeContext.md` "Known model gaps" (note the fix date); update the `WARNING` sentence inside `data/vietnam/vn_tariff_2025.json`'s `demand_charge.notes` to state the script now applies trial Ca rates; add/refresh the "two-part tariff energy rates" entry in `docs/pitfalls.md` (also add the REopt `year_one_energy_produced_kwh` vs `annual_energy_produced_kwh` ~4.5% degradation-convention footnote surfaced by the KBC cross-check).
- [ ] TASK-03-05: Regenerate the Saigon18 sensitivity locally (machine with artifacts): `.venv\Scripts\python.exe scripts/python/reopt/two_part_tariff_sensitivity.py` (defaults point at the Saigon18 scenario-A results) and sanity-check the sign: for the 69.5% load-factor Saigon18 profile the net `Δ` at the real Cp must be **negative** (a saving), consistent with the documented −53B VND/yr expectation (order of magnitude, not exact match — the −53B figure was an estimate).
- [ ] TASK-03-06: Full suite; commit; CI green.

**File Changes**
- `src/python/reopt_pysam_vn/reopt/two_part_tariff.py` (create): the three functions below + any extracted TOU-window helper.
- `tests/python/reopt/test_two_part_tariff.py` (create): unit tests, no artifacts, no network, no PySAM.
- `scripts/python/reopt/two_part_tariff_sensitivity.py` (modify): as TASK-03-03; keep `extract_monthly_grid_import`, `monthly_peaks`, `estimate_demand_shaving_peaks`, and the BAU-vs-solar demand comparison intact.
- `src/python/reopt_pysam_vn/reopt/preprocess.py` (modify only if ASM-008's extraction path is needed): mechanical extraction of window logic, zero behavior change.
- `activeContext.md`, `docs/pitfalls.md`, `data/vietnam/vn_tariff_2025.json` (modify): documentation trail per TASK-03-04 (the JSON edit touches only the two `notes` strings — no numeric fields).

**Function Signatures**
- `build_trial_energy_rate_series(tariff_data: dict, *, basis: str = "range_midpoint") -> list[float]` — returns an 8760-length list of trial Ca rates in VND/kWh, classified into peak/normal/off-peak by the same EVN TOU windows as the baseline series; raises `ValueError` on an unknown `basis`.
- `reprice_energy_series(grid_import_kw: list[float], baseline_rates_vnd_per_kwh: list[float], trial_rates_vnd_per_kwh: list[float]) -> dict` — returns `{"baseline_energy_cost_vnd": float, "trial_energy_cost_vnd": float, "energy_delta_vnd": float}` where `energy_delta_vnd = trial − baseline`; raises `ValueError` unless all three series have length 8760.
- `compute_two_part_impact(grid_import_kw: list[float], baseline_rates_vnd_per_kwh: list[float], trial_rates_vnd_per_kwh: list[float], capacity_charge_vnd_per_kw_month: float) -> dict` — returns `{"energy_delta_vnd": float, "annual_demand_charge_vnd": float, "net_impact_vnd": float, "net_impact_usd": float}` per the Specification (`net = ΔE + D`; USD at 26,000).

**Test Specs**
- Flat toy profile: `reprice_energy_series([1000.0]*8760, [2000.0]*8760, [1300.0]*8760)` → `energy_delta_vnd == -6_132_000_000.0` exactly (8760 × 1000 × (1300−2000)); `baseline_energy_cost_vnd == 17_520_000_000.0`.
- Length guard: `reprice_energy_series([1000.0]*100, [2000.0]*8760, [1300.0]*8760)` → raises `ValueError`.
- `build_trial_energy_rate_series` on the real `vn_tariff_2025.json` `"data"` block → returns 8760 values; every value is one of `{873.5, 1292.5, 2206.5}`; the multiset contains all three values (peak, normal, and off-peak windows all occur in a year).
- `compute_two_part_impact` with a constant 1000 kW import, constant baseline 2000, constant trial 1300, `capacity_charge_vnd_per_kw_month=235_414.0` → `annual_demand_charge_vnd == 235_414.0 * 12_000.0` (12 monthly peaks of 1000 kW) `== 2_824_968_000.0`; `net_impact_vnd == -6_132_000_000.0 + 2_824_968_000.0 == -3_307_032_000.0` (negative: the 100%-load-factor extreme saves — matching the domain expectation that high load factor favors the two-part tariff).
- Sign edge case: a peaky profile (e.g. `g(h) = 5000.0` for the first hour of each month, else `10.0`) with the same rates → `net_impact_vnd > 0` (low load factor loses under the two-part tariff).

**Dependencies**
- PHASE-01 (green baseline so this change's suite impact is unambiguous). Independent of PHASE-02/04.

**Exit Criteria**
- [ ] New unit tests pass; full suite `0 failed`; CI green.
- [ ] `python scripts/python/reopt/two_part_tariff_sensitivity.py --help` shows `--voltage-level` with four choices and the ASM-010 default.
- [ ] Regenerated Saigon18 output JSON contains `energy_delta_vnd < 0` and negative net impact at the default Cp (TASK-03-05).
- [ ] `activeContext.md` no longer lists the gap under "Known model gaps".

**Phase Risks**
- **RISK-03-01:** TOU-window extraction from `preprocess.py` accidentally changes the baseline series and breaks Julia/Python cross-validation (Layer 3). Mitigation: pure mechanical extraction; run `.\tests\run_all_tests.ps1 -Layer 3` (PowerShell) in addition to pytest if `preprocess.py` is touched at all.
- **RISK-03-02:** The trial-rate ranges in the data file get revised by EVN mid-sprint. Mitigation: rates are read from the versioned data file at runtime, never hardcoded in the module; `trial_rate_basis` is recorded in output.

### PHASE-04 - Single Owner Clean-Slate Mode + Contamination Audit

**Goal**
Small Vietnam C&I projects can run PySAM Single Owner finance without inheriting SAM's US ~100 MW reference-plant cost defaults — via an explicit, tested, opt-in flag — and an audit report states exactly which existing repo results carry those phantom costs, without changing any golden number.

**Tasks**
- [ ] TASK-04-01 (RED): Add tests to `tests/python/pysam/test_single_owner_clean_slate.py` (new file; `pytest.importorskip("PySAM")` at module top, matching sibling files) per Test Specs. Confirm they fail.
- [ ] TASK-04-02 (GREEN): In `src/python/reopt_pysam_vn/pysam/single_owner.py`: add field `zero_reference_plant_defaults: bool = False` to `SingleOwnerInputs` (default False — existing behavior is byte-identical, CON-001); add module-level `apply_clean_slate_financials(financial_model) -> None` that zeroes the 12 Specification fields; call it at the end of `_configure_financial_model` when `inputs.zero_reference_plant_defaults` is true; surface the flag in the returned dict under `"inputs"` (`"zero_reference_plant_defaults": bool`) and add a `"clean_slate"` note string under `"notes"` when active.
- [ ] TASK-04-03: Audit contamination. Read-only pass: `grep -rn "run_single_owner_model\|_configure_financial_model\|SingleOwnerInputs" src/ scripts/ tests/` and enumerate every caller; for each, determine whether its published/tracked outputs (examples/, reports/*.md numbers, deck check registries) embed the nonzero SAM defaults. Record findings in `reports/2026-07-17-single-owner-defaults-audit.md`: caller table, affected result sets, magnitude estimate for a representative small project (re-run one ninhsim or KBC-style case locally with the flag on/off and report the IRR/NPV delta), and an explicit recommendation section for the human decision on default-flipping and/or golden restatement. Make no code or golden changes from the audit.
- [ ] TASK-04-04: Point the relocated KBC cross-check script's `run_single_owner_model_clean` docstring at the new library flag as the durable replacement (one-line comment; behavior unchanged — the script remains a frozen comparison harness).
- [ ] TASK-04-05: Full suite (Samsung `test_golden_parity.py` must be green and untouched); commit; CI green.

**File Changes**
- `src/python/reopt_pysam_vn/pysam/single_owner.py` (modify): the flag, the helper, the two output-dict additions. Leave every existing assignment in `_configure_financial_model` exactly as-is (order included).
- `tests/python/pysam/test_single_owner_clean_slate.py` (create): specs below.
- `reports/2026-07-17-single-owner-defaults-audit.md` (create): audit findings + human-decision section. (Note: `reports/*.md` are tracked; `reports/*.html` are not.)
- `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py` (modify): one docstring line per TASK-04-04.

**Function Signatures**
- `apply_clean_slate_financials(financial_model: Any) -> None` — sets the 12 `FinancialParameters` fields listed in the Specification to `0.0` on a PySAM `Singleowner` model in place; returns nothing. (`Any` because PySAM modules are untyped; module is outside the mypy gate per CON-004.)
- `SingleOwnerInputs.zero_reference_plant_defaults: bool = False` — dataclass field; when True, `run_single_owner_model` produces finance outputs with US reference-plant cost defaults zeroed.

**Test Specs**
- Default-off regression guard: build the four PySAM models exactly as `run_single_owner_model` does (or refactor a small seam), run `_configure_financial_model(fm, build_single_owner_inputs(1000.0))`, and assert `fm.FinancialParameters.construction_financing_cost != 0.0` (SAM's default — $2,866,500 for the default config) — proving legacy behavior is preserved.
- Flag-on zeroing: same setup with `build_single_owner_inputs(1000.0, zero_reference_plant_defaults=True)` → each of the 12 Specification fields reads exactly `0.0` after `_configure_financial_model`.
- End-to-end direction: run `run_single_owner_model` twice on identical small-project inputs (`system_capacity_kw=1000.0`, `installed_cost_usd=550_000.0`, `ppa_price_input_usd_per_kwh=0.065`, defaults otherwise), flag off vs on → clean-slate `outputs` NPV strictly greater than legacy NPV, and the run dict carries `inputs.zero_reference_plant_defaults == True` and the `clean_slate` note only in the flag-on run.
- Serialization: the flag-off run dict does NOT contain the `clean_slate` note (no output-shape change for legacy callers beyond the new boolean input field).

**Dependencies**
- PHASE-01 (xfail/marker landscape settled so this phase's suite runs are interpretable). Requires local `.venv` PySAM 7.1.0.

**Exit Criteria**
- [ ] New tests pass locally under `.venv`; full suite `0 failed`; `tests/python/webapp/test_golden_parity.py` green with zero diffs to `examples/`.
- [ ] `reports/2026-07-17-single-owner-defaults-audit.md` exists, lists every caller found by the TASK-04-03 grep, and contains a "Decision required" section addressed to the maintainer.
- [ ] `git diff examples/` is empty for the whole phase.

**Phase Risks**
- **RISK-04-01:** The audit reveals the Samsung/TTC golden itself embeds the phantom defaults. Mitigation: by design this sprint only *reports* it (the audit's Decision-required section); CON-001 forbids touching the golden here — restatement is a separate, human-approved change.
- **RISK-04-02:** PySAM attribute names differ across versions (e.g. `prop_tax_cost_assessed_percent`). Mitigation: the field list was verified against the local PySAM 7.1.0 via the KBC harness, and CI pins the same version (PHASE-01); the zeroing helper should `setattr` plainly so a missing attribute raises loudly rather than silently skipping.

## Gotchas

- **`$env:PYTHONPATH = ""` before every pytest run** — a polluted global PYTHONPATH on the primary machine shadows the `.venv` FastAPI/pydantic install and produces `ModuleNotFoundError: pydantic_core._pydantic_core` that looks like a real failure.
- **xfail vs skip:** use `xfail(strict=False)` for the numeric-drift tests so they keep running and their recovery is visible; the ONE `strict=True` xfail (repo-invariants root-binary test) is a deliberate cross-phase tripwire that MUST be removed in PHASE-02.
- **`git rm --cached` vs `git rm`:** deck pptx files stay on disk (`--cached`); the root PNGs and `requirements.txt` are fully deleted. Do not mix them up.
- **`.gitignore` edits:** minimal lines only; a loose negation elsewhere in the file has previously re-tracked unrelated reports. Run `git status` immediately after every `.gitignore` edit.
- **1-hour steps make kW ≡ kWh** in the 8760 arithmetic — do not multiply by hours again. Monthly peak sums use non-leap-year month lengths (the existing `HOURS_PER_MONTH` list).
- **VND magnitudes overflow expectations, not floats** — annual figures are in the 10⁹–10¹⁰ VND range; write test expectations as exact floats (e.g. `-6_132_000_000.0`), not approximations, for the deterministic toy cases.
- **SAM percent-vs-fraction:** every SAM rate field takes percent; the wrapper multiplies stored fractions by 100. New code must follow suit or produce 100×-off economics.
- **The webapp conftest already monkeypatches `service.solve_onsite_via_nrel`** to block live calls — the new key stub is a *second*, independent fixture; do not merge them (some tests re-patch the solve stub per-test).
- **`parents[N]` path math when moving scripts:** the KBC script computes the repo root as `Path(__file__).resolve().parents[2]`; moving it one directory deeper requires `parents[3]`, or imports of `reopt_pysam_vn` silently resolve against a stale installed copy instead of `src/python`.
- **Do not edit `examples/samsung-ttc_combined-decision.example.json`** under any circumstance in this sprint; two test files gate it bit-exactly.

## Verification Strategy

- **TEST-001 (all phases):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` → last line reports `0 failed` (xfailed/xpassed/skipped counts are acceptable).
- **TEST-002 (PHASE-01):** `Rename-Item NREL_API.env NREL_API.env.bak; $env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine" -q; Rename-Item NREL_API.env.bak NREL_API.env` → `0 failed` — the exact CI selection passes with no key file present.
- **TEST-003 (PHASE-01/02/03/04):** after each phase's push: `gh run list --limit 1` → latest run on `main` shows `completed success` (or check the Actions tab).
- **TEST-004 (PHASE-02):** `git ls-files ceba-review` → empty; `git ls-files requirements.txt` → empty; `git check-ignore "ceba-review/cong bess session.pptx"` → exit 0.
- **TEST-005 (PHASE-03):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/reopt/test_two_part_tariff.py -q` → all pass, including the exact `-6_132_000_000.0` and `-3_307_032_000.0` expectations.
- **TEST-006 (PHASE-03, artifacts machine only):** `.venv\Scripts\python.exe scripts/python/reopt/two_part_tariff_sensitivity.py` → output JSON's base-case card has `energy_delta_vnd < 0` and net impact negative at the default voltage level.
- **TEST-007 (PHASE-04):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/pysam/test_single_owner_clean_slate.py tests/python/webapp/test_golden_parity.py -q` → all pass; then `git diff --stat examples/` → no output.
- **MANUAL-001 (PHASE-02):** The NREL account owner rotates the API key at the NREL Developer Network and updates `NREL_API.env` locally; confirm a live solve still works afterwards via the webapp or `scripts/python/reopt/solve_via_api.py`.
- **OBS-001 (PHASE-01):** In the green CI run's log, the pytest header shows the deselection (e.g. `selected` count ≈ 525-plus-new minus the ~16 marker-excluded tests) — confirming the filter is active rather than the suite silently shrinking.

## Risks and Alternatives

- **RISK-001:** Marker quarantine narrows CI coverage and someone later mistakes "green" for "fully tested." Mitigation: the markers are self-documenting in `pyproject.toml`, `activeContext.md` records the exclusion rationale, and the already-planned offline/frozen-resource solve mode (separate plan) is the path to restoring full-pipeline CI coverage.
- **RISK-002:** Two sessions executing phases concurrently could collide on `activeContext.md`/`pyproject.toml`. Mitigation: phases are sequenced with explicit dependencies; execute in order, one at a time.
- **ALT-001:** Fix CI by committing the needed `artifacts/` fixtures instead of marking tests — rejected: re-tracking artifacts reverses the deliberate 2026-06-12 de-bloat and bloats the repo with regenerable binaries.
- **ALT-002:** Rewrite git history to purge the leaked key — rejected: rotation fully remediates, history rewrite breaks every clone and contradicts CON-002.
- **ALT-003:** Flip `zero_reference_plant_defaults` to True by default immediately — rejected: any caller in the Samsung/offsite path would shift golden numbers silently; the audit-then-human-decision path preserves CON-001.
- **ALT-004:** Patch the tariff fix directly into the script without a library module — rejected: untestable-without-artifacts script logic is exactly the pattern this repo is trying to retire; the module makes the arithmetic unit-testable with toy profiles.

## Suggested Next Step

Execute PHASE-01. Its exit criteria (green local suite, green CI-filter simulation with `NREL_API.env` renamed away, green Actions run on `main`) are independently verifiable before PHASE-02 begins; each later phase re-verifies TEST-001 and TEST-003 so regressions localize to a single phase.
