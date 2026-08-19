# Active Context

> **Convention:** keep this file slim — current state only (target < ~150 lines).
> Rotate finished-work history into `docs/worklog/`. Full pre-2026-06-12 log:
> [`docs/worklog/2026-06-12-activecontext-archive.md`](docs/worklog/2026-06-12-activecontext-archive.md).
> July 2026 deck verification (completed 2026-06-26, all 5 phases): rotated to
> [`docs/worklog/2026-07-04-july-deck-verification-archive.md`](docs/worklog/2026-07-04-july-deck-verification-archive.md).

## Current state — last mile and physical truth landed (2026-08-19)

All six phases from `plans/2026-08-19-last-mile-and-physical-truth-plan.md` are implemented:

- **PHASE-01 — Gate ratchets + hygiene:** deselect budget (`REOPT_PYSAM_VN_MAX_DESELECTED` in `tests/conftest.py` + CI), `--cov-fail-under=82` (now 83); replaced bare `assert` in `webapp/jobs.py`; deleted three `common/` stubs; archived three `plans/active/*gap0*.md`; moved three `ceba_*.md` to `reports/`; corrected `generation_kw` description.
- **PHASE-02 — Generic extracted assembler (last mile):** `build_evn_tou_series_vnd_per_kwh` in `reopt/preprocess.py`; `analysis/extracted.py::build_extracted_inputs` per S3 (loads, site defaults, TOU VND series, benchmarks, extraction_meta, validation); wired into `webapp/service.run_analysis` (derive once, both-safe) and `analysis/__main__ --derive-extracted`; web form + CSV now reaches `done` via generic orchestrator.
- **PHASE-03 — Physical model honesty:** `pysam/pvwatts_battery.py` catalog + `great_circle_km` (S1); `generic_vn_dppa` now sets `array_type`/`tilt`/`azimuth`/`gcr` via `_array_config` (mounting enum in schema), discloses resource distance with 100 km `pvwatts_fallback_resource` warning, and uses S2 `_calibrate_to_target` (daylight-only, infeasible warning); pinned `dppa_samsung_ttc` to `array_type 2`/`tilt 0`; rewrote capacity-factor gate to tracked file (fixed-tilt 17.44% inside 14-20% band); memo at `reports/2026-08-19-solar-resource-and-array-config.md`.
- **PHASE-04 — Split result payload:** `storage.save_ledger_csv` / `get_ledger_csv_path`; `service.run_analysis` now returns `(summary, ledger)` and pops `hourly_ledger`; `GET /api/runs/{id}/ledger.csv` (`text/csv`); run page "Download hourly ledger (CSV)" link; standalone report no longer inlines raw JSON.
- **PHASE-05 — Unify load ingestion:** `webapp/uploads.parse_load_upload` now delegates to `ingestion.loader.ingest_factory_load` (temp-file, Windows-safe) with `screen_load_plausibility` advisories; `deal_config_from_form` threads `load_cleaning` through `analysis.extracted` to the run page "Load data quality" card; accepts `.json` uploads.
- **PHASE-06 — Numeric regression into CI:** `scripts/python/integration/build_regression_fixtures.py` builds `tests/fixtures/regression/*.json.gz` (~47 KB + 21 KB) and four 9–11 KB Factory-A JSONs under `tests/fixtures/factory_a/`; repointed 25 tests (13 settlement + 12 Factory-A) off `requires_artifacts`; `REOPT_PYSAM_VN_MAX_DESELECTED` lowered to 21, `--cov-fail-under` raised to 83; `.gitignore` negates `tests/fixtures/`.

**Test results (2026-08-19):** 708 passed, 21 deselected, 2 xfailed (portable suite, CI six-marker filter + skips 0, verified locally). The 2 xfailed are the Samsung parity pair (pre-existing divergence, `golden_machine` excluded). 703 collected + 21 deselected = 724 total; fixtures are under 2 MB each / 5 MB total. Coverage 83.82% (>83 floor).  
**CI status:** to be verified with `gh run list --limit 3` after push — both matrix legs must report `success`.

## Environment
- PySAM 7.1.0 + python-pptx 1.0.2 live in the repo **`.venv` (Python 3.12)** — use `.venv\Scripts\python.exe` for PySAM/PVWatts, the deck pipeline, and the test suite. System Python 3.14 has no PySAM wheel (code falls back to a synthetic profile).
- Tests: `.\tests\run_all_tests.ps1` (PowerShell runner) or `pytest tests/python/...`.
- **Gotcha:** an unrelated global `PYTHONPATH` (pointing at a `hermes-agent` venv) can shadow the repo `.venv`'s own `fastapi`/`pydantic` install and break webapp tests with `ModuleNotFoundError: pydantic_core._pydantic_core`. Run with `PYTHONPATH=` cleared, and set `PYTHONPATH=src/python` only when invoking `uvicorn`/scripts directly (not needed for pytest, which installs the package).
- **Security:** an NREL API key committed historically (commits 3911032, b14bc0b) has not been confirmed rotated as of 2026-07-24 — see README.md's "API key rotation required" note.

## Known pre-existing test failures (backlog, out of scope)

As of 2026-08-19, two remain `@pytest.mark.xfail(strict=False)`:

- `tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_full_tree_within_bar`
- `tests/python/analysis/test_samsung_ttc_parity.py::test_samsung_parity_is_bit_exact`

Both are the Samsung parity divergence (developer_irr 0.0289 vs golden None, max rel diff 1.123) reproducing at `fd8ceaf` predating webapp work. The capacity-factor gate is now passing on the tracked resource.

## Decree 243/2026 ingestion (2026-07-18)

The rooftop-solar surplus export cap was raised from 20% to 50% by Decree 243/2026/ND-CP (effective 2026-06-26). Fixed by manifest flip to `vn_export_rules_2026_decree243.json` (`max_export_fraction: 0.50`) and regime plumbing; `decree_57_2025_legacy` preserves pre-2026 results.
