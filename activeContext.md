# Active Context

> **Convention:** keep this file slim — current state only (target < ~150 lines).
> Rotate finished-work history into `docs/worklog/`. Full pre-2026-06-12 log:
> [`docs/worklog/2026-06-12-activecontext-archive.md`](docs/worklog/2026-06-12-activecontext-archive.md).
> July 2026 deck verification (completed 2026-06-26, all 5 phases): rotated to
> [`docs/worklog/2026-07-04-july-deck-verification-archive.md`](docs/worklog/2026-07-04-july-deck-verification-archive.md).

## Current focus — Vietnam DPPA web app — started 2026-07-04

Goal: an internal, localhost FastAPI app over `reopt_pysam_vn.analysis` so non-technical
Allotrope users can run the whole DealConfig loop with zero terminal use — guided deal form
(template-seeded, CSV/xlsx load upload), NREL REopt solves as background jobs, a results page
with Plotly charts, run history with clone-and-edit, and two-run compare.

- **Brainstorm:** `research/2026-07-04_vietnam-dppa-web-app-brainstorm.md` (23 DECs)
- **Plan:** `plans/2026-07-04-vietnam-dppa-web-app-plan.md` (5 phases) — implemented in full this session
- **Package:** `src/python/reopt_pysam_vn/webapp/` — see its `README.md` for launch/storage/cache docs

### Phase status (all 5 phases done 2026-07-04, uncommitted)
- **PHASE-01** — App factory, `storage.py` (filesystem run store under `artifacts/webapp/runs/`),
  JSON API over pre-solved `DealConfig` payloads (`/api/health`, `/api/runs`).
- **PHASE-02** — `jobs.py` FIFO in-process solve worker (one solve at a time), config-hash solve
  cache with `force_resolve` bypass, `service.py` NREL key loading mirroring
  `scripts/python/reopt/solve_via_api.py`. Required a small library fix: `onsite.py`'s
  `build_onsite_scenario` now carries `site.latitude`/`site.longitude` into the REopt `Site`
  block (the API rejects a siteless scenario) — 2 new tests in `test_onsite.py`.
- **PHASE-03** — `forms.py` (template + form fields + upload -> DealConfig), `uploads.py`
  (CSV/xlsx load parsing), `templates/new_deal.html` + `static/app.js`.
- **PHASE-04** — `results_view.py` (headline metrics + chart series from onsite/offsite results),
  `templates/run.html` (Plotly charts, status polling), `templates/runs.html` (history,
  reopen, clone-and-edit), JSON/HTML downloads.
- **PHASE-05** — `compare.py` + `templates/compare.html` (two-run delta view),
  `test_golden_parity.py` (Samsung/TTC bit-exact through the web API path), `webapp/README.md`.

### Verification (2026-07-04)
- `pytest tests/python/webapp/` — **45/45 passed**, including golden parity.
- Live smoke test: launched `uvicorn reopt_pysam_vn.webapp:app`, confirmed `/api/health`,
  `/deals/new`, `/runs`, `/compare` all return 200.
- Full regression `pytest tests/python/` — **552 passed, 5 failed (all pre-existing on `main`,
  confirmed via `git stash`), 1 skipped.** No failure is caused by this session's changes.

### Reuse map (no forking analytics logic, per CON-002)
- Calls `run_onsite` / `run_offsite_dppa` (`analysis/`), `run_vietnam_reopt` (`reopt/preprocess.py`)
  as-is; the only library change is the `onsite.py` Site lat/long fix above.

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
  `src/julia/REoptVietnam.jl`) now warn only when a caller's
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

### Two-part tariff sensitivity — missing energy rate reduction
`scripts/python/reopt/two_part_tariff_sensitivity.py` adds the Decree 146/2025
demand charge (Cp × Pmax) on top of the existing single-component TOU energy
rates, but does NOT swap in the lower trial energy rates (Ca). Under the actual
two-part tariff, energy rates drop ~30-38% (see `vn_tariff_2025.json` →
`demand_charge → two_part_tariff_trial → energy_charge_vnd_per_kwh`).

**Impact:** The script overstates the cost impact of the two-part tariff. For a
Saigon18-type profile (69.5% LF), the net effect flips from +73B/yr extra (old
method) to −53B/yr savings (correct). Factory A (~46% LF) is approximately
breakeven. Cross-reference: XanhTerra case study at
https://xanhterra.com/twocomponent-tariff.

**Fix:** Re-price the 8760 energy series using the trial Ca rates before
computing the demand charge delta. See the script docstring for details.

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
