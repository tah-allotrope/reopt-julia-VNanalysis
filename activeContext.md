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
- `tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_full_tree_within_bar`
- `tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_is_bit_exact`
- `tests/python/integration/test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`
- `tests/python/integration/test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`
- `tests/python/pysam/test_strike_price_discovery.py::test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike`

All five are numeric benchmark/tolerance drift, confirmed failing on unmodified `main` via
`git stash` (2026-07-04). The last one was not previously logged in this file.
