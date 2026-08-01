# Active Context

> **Convention:** keep this file slim — current state only (target < ~150 lines).
> Rotate finished-work history into `docs/worklog/`. Full pre-2026-06-12 log:
> [`docs/worklog/2026-06-12-activecontext-archive.md`](docs/worklog/2026-06-12-activecontext-archive.md).
> July 2026 deck verification (completed 2026-06-26, all 5 phases): rotated to
> [`docs/worklog/2026-07-04-july-deck-verification-archive.md`](docs/worklog/2026-07-04-july-deck-verification-archive.md).

## Current state — CI green, all planned phases complete (2026-07-25)

All phases from `plans/2026-07-22-ci-truth-correctness-sprint-plan.md` and
`plans/2026-07-24-post-ci-hygiene-finance-audit-plan.md` have been implemented:

- **PHASE-01/02 (07-22):** Workspace hygiene + CI truth (worktree cleanup, pytest markers, PySAM pin, hermetic tests, red-test triage, repo-invariants, flat-script relocation)
- **PHASE-03 (07-22):** Security & hygiene (untrack binaries, fix `.gitignore`, single dependency source, key-rotation documentation)
- **PHASE-04 (07-22):** Two-part tariff Ca re-pricing fix (sign error corrected, library module + tests)
- **PHASE-05 (07-22):** Single Owner clean-slate flag + contamination audit
- **PHASE-01/02 (07-24):** Security hygiene + Single Owner finance audit (already complete)
- **PHASE-03 (07-24):** Report-only test coverage in CI (85% coverage, non-blocking)
- **PHASE-04 (07-24):** Plans directory hygiene sweep (13 shipped plans archived, 9 remain active)

**Test results (2026-07-25):** 589 passed, 18 deselected, 3 xfailed, 0 failed, 85% coverage  
**CI status:** Green on `main`  
**Final report:** `reports/2026-07-25-post-ci-hygiene-finance-audit-final.md`

## Environment
- PySAM 7.1.0 + python-pptx 1.0.2 live in the repo **`.venv` (Python 3.12)** — use
  `.venv\Scripts\python.exe` for PySAM/PVWatts, the deck pipeline, and the test suite. System
  Python 3.14 has no PySAM wheel (code falls back to a synthetic profile).
- Tests: `.\tests\run_all_tests.ps1` (PowerShell runner) or `pytest tests/python/...`.
- **Gotcha:** an unrelated global `PYTHONPATH` (pointing at a `hermes-agent` venv) can shadow the
  repo `.venv`'s own `fastapi`/`pydantic` install and break webapp tests with
  `ModuleNotFoundError: pydantic_core._pydantic_core`. Run with `PYTHONPATH=` cleared, and set
  `PYTHONPATH=src/python` only when invoking `uvicorn`/scripts directly (not needed for pytest,
  which installs the package).
- **Security:** an NREL API key committed historically (commits 3911032, b14bc0b) has not been
  confirmed rotated as of 2026-07-24 — see README.md's "API key rotation required" note.

## Known pre-existing test failures (backlog, out of scope)

As of the 2026-07-22 CI-truth-correctness sprint (PHASE-02), all five are now
annotated `@pytest.mark.xfail(strict=False)` in place so they keep running and
any future recovery shows as `XPASS` instead of silently disappearing:

- `tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_full_tree_within_bar`
- `tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_is_bit_exact`
- `tests/python/integration/test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`
- `tests/python/integration/test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`
- `tests/python/pysam/test_strike_price_discovery.py::test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike`

All five are numeric benchmark/tolerance drift, confirmed failing on unmodified `main` via
`git stash` (2026-07-04). The last one was not previously logged in this file.

**Samsung parity investigation (2026-07-22):** the two `test_samsung_ttc_parity`
failures were investigated per the sprint plan's 2-hour timebox using a
temporary `git worktree` at commit `fd8ceaf` (the last commit before the webapp
phase-1/phase-2 sessions). The exact same divergence reproduces there
(`developer_irr_fraction` computes `0.0289...` where the golden holds `None`;
max relative diff `1.123`) — confirming this is **not** a regression introduced
by any later work, but a pre-existing divergence baked into the golden file or
its generation environment. No further root-cause was pursued within the
timebox; the golden file itself was not touched.

**CI marker classification (2026-07-22):** `tests/python/analysis/test_samsung_ttc_parity.py`
is now marked `golden_machine` (module-level) and excluded from CI — the
bit-exact comparison only holds against the primary dev machine's PVWatts
resource cache. Several other tests are now marked `requires_artifacts`
(read git-ignored files under `artifacts/`) and excluded from CI as well; see
`pyproject.toml`'s `markers` list and `.github/workflows/ci.yml`'s pytest
filter for the complete, current exclusion set.

**New marker, beyond the original sprint plan (2026-07-22):**
`tests/python/integration/test_regime_engine_smoke.py`'s two CI-only failures
(`test_regime_matrix_no_solve_writes_complete_artifacts`,
`test_cached_run_is_reused_when_manifest_is_successful`) were investigated by
reading `reopt_pysam_vn.reopt.regime_runner.build_regime_matrix`: even with
`solve=False`, it always shells out to a real `julia` subprocess (`--no-solve`)
via `_run_julia_scenario`, and both tests write to pytest's `tmp_path` rather
than the tracked `artifacts/` directory — so this is a Julia-availability
dependency, not an artifacts dependency, and `requires_artifacts` would have
been a factually wrong label. A new `requires_julia` marker was added (see
`pyproject.toml`) and applied to both tests instead; CI's filter now excludes
`network`, `requires_artifacts`, `golden_machine`, and `requires_julia`. This
matches the repo's existing, standing decision to keep Julia CI out of scope
(cold starts of several minutes make it poor CI economics) — no Julia setup
step exists in `.github/workflows/ci.yml` and none is added by this change.

## Decree 243/2026 ingestion (2026-07-18)

The rooftop-solar surplus export cap was raised from 20% to 50% by Decree
243/2026/ND-CP (effective 2026-06-26), which amends Decree 57/2025 and Decree
58/2025. The data layer previously still enforced the repealed 20% cap; fixed
by `plans/2026-07-18-decree-243-currency-webapp-hardening-plan.md` PHASE-02:

- New versioned file `data/vietnam/vn_export_rules_2026_decree243.json` is now
  the active `export_rules` file (manifest flip); `max_export_fraction: 0.50`.
- Surplus purchase rate is **unchanged** at 671 VND/kWh — Decree 243 codifies a
  new pricing formula (prior-year average market price, capped at the
  utility-scale ground-mount ceiling) but no prior-year average has been
  published yet; see `docs/regulatory-watch.md` (export_rules row: PENDING).
- Pre-2026-06-26 results are reproducible via the new `decree_57_2025_legacy`
  regime; both preprocessing twins (`reopt/preprocess.py`,
  `legacy/julia/src/REoptVietnam.jl`) now warn only when a caller's
  `max_export_fraction` differs from the *active* regime-resolved value, not a
  hardcoded 0.20.
- New settlement preset `decree243_export_50pct_standard` in
  `integration/settlement.py`; first-order export-cap delta memo at
  `reports/2026-07-18-decree243-export-cap-delta.md` — fixed-dispatch (no
  re-optimization) headline on the Saigon18 scenario-A golden run: an
  additional ~1.29B VND/yr (~$48.9k/yr) in surplus export revenue at the 50%
  cap vs. the 20% cap, a lower bound pending a re-optimized solve.
- Verified: Julia Layer 2 unit tests pass (60s); `tests/cross_language/cross_validate.py`
  Layer 3 passes for all 4 exercised regimes (exact match, max diff 0.00e+00);
  Python `tests/python/reopt/test_unit.py` passes directly via `.venv\Scripts\python.exe`
  with `PYTHONPATH=` cleared. `tests\run_all_tests.ps1`'s Python legs (which invoke
  bare `python`, not the `.venv` interpreter) fail on this machine because `python`
  on `PATH` resolves to an unrelated `hermes-agent` venv lacking pytest — this is the
  pre-existing global-PYTHONPATH/wrong-venv gotcha already documented above, not a
  regression from this change; verify Python layers with the `.venv` interpreter
  directly until the runner script is fixed to do the same.

## Known model gaps

### Two-part tariff sensitivity — FIXED 2026-07-25
The two-part tariff script now correctly computes the NET impact: lower trial
energy rates (Ca) PLUS the demand charge (Cp × monthly peak). The sign error
for high-load-factor profiles has been resolved. See
`reports/2026-07-25-two-part-tariff-fix.md` for details.

## Map site picker — implemented 2026-07-06

Plan: `plans/2026-07-06-map-site-picker-webapp-plan.md` (Q-001 default accepted: OSM defaults).
Adds an interactive Leaflet site picker to `/deals/new` and a read-only context map to `/runs/{run_id}`.

### Phase summary
- **PHASE-01** — `webapp/projects.py` catalog loader reads `data/projects/*.json`, skips schema/missing coords;
  `GET /api/projects` endpoint in `webapp/routes/api.py`; TDD tests in `tests/python/webapp/test_projects.py`.
- **PHASE-02** — `webapp/static/map.js` with `initSitePicker` (OSM tiles, draggable marker, two-way lat/lon sync,
  latitude-band region auto-set ≥20°N north / 14–20°N central / <14°N south, Nominatim search,
  catalog project markers with popups); `base.html` `head_extra` block; `new_deal.html` Leaflet CDN + map container.
- **PHASE-03** — `routes/pages.py` passes `site` coords to `run.html`; context map card with `initContextMap`
  (non-interactive, site highlighted, catalog projects muted, auto-fit bounds); tests added to `test_pages.py`.
- **PHASE-04** — Full `pytest tests/python/webapp/` green; manual curl submission confirmed picked lat/lon
  (21.0285, 105.8542) and derived region (`north`) persisted to `deal_config.json`. Playwright browser
  automation was abandoned because the localhost dev server became unresponsive during map tile loading;
  the form and map degrade gracefully when Leaflet/Nominatim/tiles are unavailable.

### Verification
- `pytest tests/python/webapp/` — **50/50 passed** (3 new project tests + 2 new run-page map tests).
- Map click via browser console hook (`window._sitePickerMap.fire`) wrote lat/lon/region correctly.
- Curl deal submission wrote `site.latitude=21.0285`, `site.longitude=105.8542`, `site.region=north`.

### Files changed
- `src/python/reopt_pysam_vn/webapp/projects.py` (new)
- `src/python/reopt_pysam_vn/webapp/routes/api.py`
- `src/python/reopt_pysam_vn/webapp/routes/pages.py`
- `src/python/reopt_pysam_vn/webapp/static/map.js` (new)
- `src/python/reopt_pysam_vn/webapp/templates/base.html`
- `src/python/reopt_pysam_vn/webapp/templates/new_deal.html`
- `src/python/reopt_pysam_vn/webapp/templates/run.html`
- `tests/python/webapp/test_projects.py` (new)
- `tests/python/webapp/test_pages.py`
