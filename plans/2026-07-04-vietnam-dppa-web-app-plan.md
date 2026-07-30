---
title: "Vietnam DPPA Web App"
date: "2026-07-04"
status: "complete — all 5 phases shipped in commit a656102: webapp package (storage/jobs/service/forms/uploads/results_view/compare), 5 Jinja templates, 13 test modules including test_golden_parity.py"
request: "vietnam-dppa-web-app — multi-phase implementation plan from research/2026-07-04_vietnam-dppa-web-app-brainstorm.md"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-04_vietnam-dppa-web-app-brainstorm.md"
  - "research/2026-04-26_commercial-product-ideas.md"
---

# Plan: Vietnam DPPA Web App

## Objective
Build an internal, localhost FastAPI web app that exposes the repo's Vietnam DPPA analytics (`reopt_pysam_vn.analysis`) to non-technical Allotrope users: a guided deal form seeded from scenario templates, CSV/xlsx load upload, NREL REopt API solves in background jobs, a native results page with interactive charts, run history with clone-and-edit, and two-run comparison — the whole DealConfig loop with zero terminal use.

## Context Snapshot
- **Current state:** Analytics are CLI/JSON-only. `src/python/reopt_pysam_vn/analysis/` provides `run_onsite(deal, results=..., extracted=...)` and `run_offsite_dppa(deal, extracted=...)` over the `DealConfig` contract (`analysis/types.py`, schema at `data/schemas/deal_config.schema.json`, CLI at `analysis/__main__.py`). Fresh solves go through `reopt/preprocess.py:run_vietnam_reopt` (NREL REopt API; key in `NREL_API.env`). Vietnam policy defaults are versioned JSON in `data/vietnam/` behind `manifest.json` (`load_vietnam_data` at preprocess.py:163, `apply_vietnam_defaults` at :730). Four deal archetypes live in `scenarios/templates/*.json`. Golden artifacts: `examples/samsung-ttc_combined-decision.example.json` and `examples/samsung-ttc_final-report.example.html`. There is **no web layer** and no web dependencies; env is a uv-managed Python 3.12 `.venv` on Windows (PySAM only exists there).
- **Desired state:** `uvicorn reopt_pysam_vn.webapp:app` serves a Jinja2 + vanilla-JS app on 127.0.0.1: new-deal form → background solve+analyze job → results page (Plotly charts, JSON/HTML downloads) → runs index (list/reopen/clone) → two-run compare. Runs persist as JSON under git-ignored `artifacts/webapp/runs/`. Samsung/TTC golden parity holds through the web path.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/analysis/{types.py,onsite.py,offsite_dppa.py,__main__.py}`, `src/python/reopt_pysam_vn/reopt/preprocess.py`, `data/schemas/deal_config.schema.json`, `data/vietnam/*.json` + `manifest.json`, `scenarios/templates/*.json`, `src/python/reopt_pysam_vn/integration/generate_html_report.py` (report download), `examples/samsung-ttc_*.example.*`, `tests/python/analysis/` (test conventions), `pyproject.toml`, `.gitignore`.
- **Out of scope:** SaaS features (auth, billing, multi-tenant, cloud hosting); strike-sweep/regime-toggle/sensitivity UIs; local Julia solve path; reference-load-shape picker; `.xlsm` workbook extraction; editing `data/vietnam/` policy files from the UI; PPTX generation.

## Research Inputs
- `research/2026-07-04_vietnam-dppa-web-app-brainstorm.md` — resolves the entire design (23 DEC-* decisions): audience, stack, job model, input/results UX, persistence, hosting, acceptance bar. This plan implements it directly; its two open questions carry into Grill Me.
- `research/2026-04-26_commercial-product-ideas.md` — the "DPPA Deal Screener" product sketch; confirms module mapping (load upload → analysis pipelines → report) and frames this app as its internal precursor. No SaaS scope is pulled in.

## Assumptions and Constraints
- **ASM-001:** NREL REopt API key in `NREL_API.env` is valid; interactive single-user usage stays within rate limits.
- **ASM-002:** Plotly via CDN is acceptable (internal, browser-side); results pages degrade to metric tables if the CDN is unreachable.
- **ASM-003:** `DealConfig` and the `analysis` package contracts are stable; the form maps to `deal_config.schema.json` sections (site/plant/load/contract/finance).
- **ASM-004:** Single user, Windows, running inside the repo `.venv` (Python 3.12; PySAM only there).
- **CON-001:** No new heavy infra: no DB, no Redis/Celery, no npm build step, no Julia on the serving path.
- **CON-002:** The webapp must not fork analytics logic — it calls `run_onsite`/`run_offsite_dppa`/`run_vietnam_reopt` as-is; needed changes go into the library.
- **CON-003:** Deprecated `integration/dppa_case_*.py` engines are not wired in.
- **CON-004:** Solves take tens of seconds to minutes; every solve-triggering interaction is async with visible status (in-process jobs + polling).
- **CON-005:** Red/green TDD with FastAPI `TestClient`; NREL calls mocked with recorded responses so tests never hit the network.
- **DEC-001:** Stack: FastAPI + Jinja2 templates + one vanilla-JS file; interactive charts via Plotly CDN; served by `uvicorn` on 127.0.0.1, no auth.
- **DEC-002:** Webapp lives at `src/python/reopt_pysam_vn/webapp/` (app factory, `routes/`, `templates/`, `static/`, `jobs.py`, `storage.py`, `uploads.py`); web deps go in a `webapp` optional-dependency extra in `pyproject.toml` (`fastapi`, `uvicorn`, `jinja2`, `python-multipart`).
- **DEC-003:** Persistence: one directory per run under `artifacts/webapp/runs/<run_id>/` holding `deal_config.json`, `status.json`, `result.json`, and (when solved fresh) `reopt_results.json`; `run_id` = timestamp + slug.
- **DEC-004:** Concurrency: one active solve at a time; additional submissions queue FIFO in-process.
- **DEC-005:** Solve-result caching: hash of the solve-relevant DealConfig subset → reuse a prior run's `reopt_results.json`, with a "force re-solve" checkbox (Grill Me Q-002 default, adopted).
- **DEC-006:** Launch analysis scope: onsite, offsite_dppa, and both/combined — mirroring the CLI modes.
- **DEC-007:** Acceptance bar: Samsung/TTC golden parity through the web path + cold-start form→solve→results demo with no terminal.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Webapp skeleton, run storage, JSON API over the analysis package | None | `webapp/` package, `/api/runs` CRUD on pre-solved inputs, tests |
| PHASE-02 | Background solve pipeline: NREL solve + analyze jobs, polling, cache | PHASE-01 | `jobs.py`, `POST /api/runs` async, status polling, solve cache |
| PHASE-03 | Deal form UI: template seeding, guided form, load upload | PHASE-02 | `templates/` pages, upload parsing, form→DealConfig mapping |
| PHASE-04 | Results page, charts, downloads, run history | PHASE-03 | Results + runs-index pages, Plotly charts, JSON/HTML downloads, clone-and-edit |
| PHASE-05 | Two-run compare, golden parity gate, cold-start verification, docs | PHASE-04 | Compare page, parity test, README/run instructions |

## Detailed Phases

### PHASE-01 - Webapp Skeleton and Run Storage
**Goal**
A FastAPI app importable as `reopt_pysam_vn.webapp:app` with filesystem run storage and a JSON API that can execute the fast, deterministic path (analysis over pre-solved results) end-to-end — no UI, no solving yet.

**Tasks**
- [x] TASK-01-01: Add `webapp` optional extra to `pyproject.toml` (`fastapi`, `uvicorn[standard]`, `jinja2`, `python-multipart`) and install into `.venv` with uv; add `artifacts/webapp/` to `.gitignore` if not already covered by `artifacts/`.
- [x] TASK-01-02: Write failing tests `tests/python/webapp/test_storage.py` for `storage.py`: create run dir (`artifacts/webapp/runs/<run_id>/`), write/read `deal_config.json`/`status.json`/`result.json`, list runs sorted by date, storage root overridable via env var for tests (point at tmp dir).
- [x] TASK-01-03: Implement `src/python/reopt_pysam_vn/webapp/storage.py` to green.
- [x] TASK-01-04: Write failing tests `tests/python/webapp/test_api_runs.py` (FastAPI `TestClient`): `GET /api/health`; `POST /api/runs` with a DealConfig JSON + pre-solved `results`/`extracted` payloads returns a run whose `result.json` matches calling `run_onsite`/`run_offsite_dppa` directly; `GET /api/runs` lists; `GET /api/runs/{id}` fetches; invalid DealConfig (bad `mode`) returns 422 with the `ValueError` message.
- [x] TASK-01-05: Implement `webapp/__init__.py` (app factory), `webapp/routes/api.py`, and a thin `webapp/service.py` that maps mode → `run_onsite` / `run_offsite_dppa` / both, to green.

**Files / Surfaces**
- `pyproject.toml` — add `webapp` extra.
- `src/python/reopt_pysam_vn/webapp/{__init__.py,storage.py,service.py,routes/api.py}` — new package.
- `tests/python/webapp/` — new test dir following `tests/python/analysis/` conventions.
- `src/python/reopt_pysam_vn/analysis/{onsite.py,offsite_dppa.py}` — inspected only (CON-002).

**Dependencies**
- None.

**Exit Criteria**
- [ ] `pytest tests/python/webapp/` green from the repo `.venv`.
- [ ] `uvicorn reopt_pysam_vn.webapp:app` starts and `GET /api/health` returns 200.
- [ ] A pre-solved run POSTed through the API produces `result.json` identical to the direct library call.

**Phase Risks**
- **RISK-01-01:** FastAPI/pydantic version friction with Python 3.12/uv — pin versions in the extra; verify install before writing code.

### PHASE-02 - Solve Pipeline and Job Manager
**Goal**
`POST /api/runs` accepts a DealConfig with no pre-solved results, runs the NREL solve (`run_vietnam_reopt`) plus analysis in an in-process background job, and exposes status polling — with a config-hash solve cache and a one-solve-at-a-time queue.

**Tasks**
- [x] TASK-02-01: Write failing tests `tests/python/webapp/test_jobs.py` for `jobs.py`: submit job → status transitions `queued → solving → analyzing → done` (or `error` with message); FIFO queue admits one active solve; job state persisted to `status.json` so a restart shows the last known state.
- [x] TASK-02-02: Implement `webapp/jobs.py` (thread-based worker; FastAPI lifespan startup/shutdown) to green.
- [x] TASK-02-03: Record one real NREL solve response as a fixture (`tests/python/webapp/fixtures/reopt_response.json`) or reuse an existing sanitized results JSON (see `tests/python/reopt/test_api_result_sanitization.py` fixtures); write failing tests where `run_vietnam_reopt` is monkeypatched to return it — `POST /api/runs` (no results) returns `202` + run id, polling `GET /api/runs/{id}` reaches `done`, and `result.json` matches the deterministic path over the fixture.
- [x] TASK-02-04: Implement the solve step in `service.py`: build the REopt scenario from DealConfig via `apply_vietnam_defaults`/`load_vietnam_data`, call `run_vietnam_reopt`, persist `reopt_results.json`, then run analysis; wire NREL key loading from `NREL_API.env`/env vars exactly as `scripts/python/reopt/solve_via_api.py` does.
- [x] TASK-02-05: Write failing tests for the solve cache: identical solve-relevant config subset → second run reuses the first run's `reopt_results.json` (no `run_vietnam_reopt` call); `force_resolve: true` bypasses. Implement to green.
- [x] TASK-02-06: Error-path tests: NREL failure/timeout marks the run `error` with a human-readable message surfaced by the status endpoint; the worker survives and processes the next job.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/webapp/{jobs.py,service.py,routes/api.py}` — job manager, solve integration.
- `src/python/reopt_pysam_vn/reopt/preprocess.py` — called, not modified (`run_vietnam_reopt` at :823, `apply_vietnam_defaults` at :730).
- `scripts/python/reopt/solve_via_api.py` — reference for key loading and scenario POST/poll shape.
- `tests/python/webapp/{test_jobs.py,fixtures/}`.

**Dependencies**
- PHASE-01. One live NREL call (manual, not in tests) to record/verify the fixture.

**Exit Criteria**
- [ ] All webapp tests green with `run_vietnam_reopt` mocked; no test touches the network.
- [ ] MANUAL: one real solve through `POST /api/runs` completes on the live NREL API and lands `reopt_results.json` + `result.json` in the run dir.
- [ ] Cache hit verified: cloned config re-run completes in under ~2s without an NREL call.

**Phase Risks**
- **RISK-02-01:** Mapping DealConfig → REopt scenario for fresh solves may need glue that only exists in scripts — if so, promote it into the library (`analysis` or `reopt`), not the webapp (CON-002).
- **RISK-02-02:** In-process jobs die with the server — mitigated by persisting `status.json` and marking interrupted runs `stale` on startup.

### PHASE-03 - Deal Form UI
**Goal**
Non-technical users create a deal in the browser: pick one of the four archetype templates, edit a guided form (site / plant / contract / finance key overrides, Vietnam defaults prefilled and shown), upload an 8760-hour CSV/xlsx load profile, and submit — producing a valid DealConfig and a queued run.

**Tasks**
- [x] TASK-03-01: Write failing tests `tests/python/webapp/test_uploads.py` for `uploads.py`: parse a single-column CSV (header optional) and basic `.xlsx` (first sheet, first numeric column) into `loads_kw`; reject wrong length (≠8760), non-numeric rows, and empty files with specific messages.
- [x] TASK-03-02: Implement `webapp/uploads.py` (csv module + openpyxl, both already available) to green.
- [x] TASK-03-03: Write failing tests for form→DealConfig mapping (`webapp/forms.py`): template id + form fields + uploaded loads → DealConfig dict that validates against `data/schemas/deal_config.schema.json`; key overrides (capex, discount rate, PPA/strike terms, escalations) land in the right sections; untouched defaults come from `scenarios/templates/*.json` + `load_vietnam_data`.
- [x] TASK-03-04: Implement `webapp/forms.py` to green.
- [x] TASK-03-05: Build Jinja2 pages: `templates/base.html` (nav, Plotly CDN tag), `templates/new_deal.html` (template picker → form sections with defaults shown read-only vs override fields, mode select onsite/offsite_dppa/both, load-file input, force re-solve checkbox), and `static/app.js` (submit via fetch, redirect to run page). Route: `GET /deals/new`, `POST /api/runs` (multipart).
- [x] TASK-03-06: Server-side validation errors render inline next to fields (422 payload → form messages); TestClient tests for the happy path and one rejection.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/webapp/{uploads.py,forms.py,routes/pages.py,templates/,static/app.js}` — new.
- `scenarios/templates/vn_{commercial_rooftop_pv,industrial_pv_storage,hospital_resilience,offgrid_microgrid}.json` — template seeds (read-only).
- `data/schemas/deal_config.schema.json` — form validation target.
- `data/vietnam/manifest.json` + policy JSONs — displayed defaults.

**Dependencies**
- PHASE-02 (submission queues a real job).

**Exit Criteria**
- [ ] `pytest tests/python/webapp/` green including upload and form-mapping suites.
- [ ] MANUAL: in a browser, seed from `vn_industrial_pv_storage`, upload a CSV, submit, and watch the run reach `done` (mocked or live).
- [ ] A malformed upload (100 rows) shows a clear inline error, not a stack trace.

**Phase Risks**
- **RISK-03-01:** The four templates may not populate every form section — fill gaps from `vn_deal_defaults_2026.json` and mark template-missing fields as required inputs.

### PHASE-04 - Results, Charts, Downloads, Run History
**Goal**
A native results page per run — headline metrics (NPV/LCC, PV/BESS sizing, delivered fraction, IRR/DSCR), interactive Plotly charts, raw-JSON and HTML-report downloads — plus a runs index with reopen and clone-and-edit.

**Tasks**
- [x] TASK-04-01: Write failing tests for a results-view model (`webapp/results_view.py`): given an `OnsiteResult`/`OffsiteDppaResult` dict, extract headline metrics and chart series (monthly/hourly dispatch aggregates, cashflow series, strike-settlement summary) as plain JSON for the template; must handle onsite-only, offsite-only, and both.
- [x] TASK-04-02: Implement `results_view.py` to green (metric paths taken from `analysis/types.py` block names: `deal`, `base_settlement`, `strike_sweep`, `adder_sensitivity`, `regime_stress`, `decision`, `quality`; onsite `sizing`/`dispatch`/`economics`).
- [x] TASK-04-03: Build `templates/run.html`: status banner with JS polling while queued/solving; on done, metric cards + Plotly charts fed by an embedded JSON blob; graceful table-only fallback when Plotly fails to load (ASM-002). Route `GET /runs/{id}`.
- [x] TASK-04-04: Downloads: `GET /api/runs/{id}/result.json` (raw), `GET /api/runs/{id}/report.html` generated on demand via `integration/generate_html_report.py` (inspect its input contract; adapt inputs in the webapp layer, not the generator). TestClient tests for both.
- [x] TASK-04-05: Runs index `templates/runs.html` at `GET /runs`: name, date, mode, status, one headline metric; reopen link; "duplicate as new deal" opens `GET /deals/new?from={id}` with the form pre-filled from the stored `deal_config.json` (loads carried over, re-upload optional). Tests for prefill mapping.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/webapp/{results_view.py,routes/pages.py,templates/run.html,templates/runs.html,static/app.js}`.
- `src/python/reopt_pysam_vn/integration/generate_html_report.py` — inspected/wrapped for the report download (not modified unless its contract requires a library-side shim).
- `examples/samsung-ttc_final-report.example.html` — reference for report content.

**Dependencies**
- PHASE-03.

**Exit Criteria**
- [ ] MANUAL: a completed run renders metrics + at least dispatch and cashflow charts; downloads return valid JSON and standalone HTML.
- [ ] Clone-and-edit round-trip: duplicate a run, change one field, re-run; cache makes it fast when solve inputs are unchanged (DEC-005).
- [ ] All view-model and download tests green.

**Phase Risks**
- **RISK-04-01:** `generate_html_report.py` may expect bespoke case inputs rather than `analysis` results — if adaptation is nontrivial, ship raw-JSON download in v1 exit and log the report shim as a follow-up rather than forking report logic.

### PHASE-05 - Compare, Golden Parity, Cold-Start Acceptance
**Goal**
Two-run side-by-side comparison, the Samsung/TTC golden-parity gate through the web path, and the documented cold-start demo that proves the no-terminal loop.

**Tasks**
- [x] TASK-05-01: Write failing tests for compare view-model: any two saved runs → aligned two-column headline metrics with per-metric deltas; mixed modes degrade to the intersection of metrics. Implement `webapp/compare.py` + `templates/compare.html` (`GET /compare?a={id}&b={id}`, picker on the runs index).
- [x] TASK-05-02: Golden parity test `tests/python/webapp/test_golden_parity.py`: POST the Samsung/TTC deal config with its pre-solved inputs through the API (mirror `tests/python/analysis/test_samsung_ttc_parity.py` setup) and assert `result.json` equals `examples/samsung-ttc_combined-decision.example.json` key-for-key.
- [x] TASK-05-03: MANUAL cold-start demo: fresh browser, `uvicorn reopt_pysam_vn.webapp:app`, template → form → CSV upload → live NREL solve → results page → compare against a cloned variant. Record the outcome in `activeContext.md`.
- [x] TASK-05-04: Docs: `src/python/reopt_pysam_vn/webapp/README.md` (launch command from `.venv`, NREL key expectation, storage layout, cache semantics) and a pointer from the repo README.
- [x] TASK-05-05: Full-suite regression: `pytest tests/python/` green; confirm no analytics module was modified except any library promotions from RISK-02-01 (diff review).

**Files / Surfaces**
- `src/python/reopt_pysam_vn/webapp/{compare.py,templates/compare.html}`.
- `tests/python/webapp/test_golden_parity.py` — acceptance gate.
- `tests/python/analysis/test_samsung_ttc_parity.py` — setup reference.
- `README.md`, `src/python/reopt_pysam_vn/webapp/README.md`, `activeContext.md`.

**Dependencies**
- PHASE-04. One live NREL solve for the cold-start demo.

**Exit Criteria**
- [ ] Golden parity test green through the web API path.
- [ ] Cold-start demo completed and recorded: form → solve → results with no terminal beyond launching uvicorn.
- [ ] Compare page renders deltas for two real runs.
- [ ] Full `pytest tests/python/` green.

**Phase Risks**
- **RISK-05-01:** Parity may fail on float formatting/JSON ordering rather than substance — compare with the same tolerance/normalization the existing parity test uses.

## Verification Strategy
- **TEST-001:** `pytest tests/python/webapp/` — unit + TestClient suites per phase (storage, jobs, uploads, forms, view-models, downloads, compare), all NREL calls mocked (CON-005).
- **TEST-002:** `pytest tests/python/webapp/test_golden_parity.py` — Samsung/TTC combined-decision parity through the web API (DEC-007 gate).
- **TEST-003:** `pytest tests/python/` — full regression proving the analytics library is behaviorally untouched.
- **MANUAL-001:** One live NREL solve end-of-PHASE-02 (API path) and one end-of-PHASE-05 (browser cold-start demo).
- **MANUAL-002:** Upload rejection UX check — wrong-length CSV yields an inline message, not a 500.
- **OBS-001:** Job status transitions and NREL call attempts logged via the standard `logging` module to console + `artifacts/webapp/webapp.log`; error runs keep the message in `status.json` for post-mortem.

## Risks and Alternatives
- **RISK-001:** DealConfig→fresh-solve glue may live only in scripts today; promoting it into the library (per CON-002) could grow PHASE-02. Mitigation: timebox; the deterministic pre-solved path (PHASE-01) already delivers value if solving slips.
- **RISK-002:** In-process job loss on server restart — accepted for a single-user tool; `status.json` persistence + `stale` marking keeps history honest (RISK-02-02).
- **RISK-003:** NREL API instability or rate limits during demos — the solve cache (DEC-005) and pre-solved path are the fallback.
- **ALT-001:** Streamlit instead of FastAPI — faster to ship but rejected in brainstorm (DEC-004): the API layer is reusable by scripts and a future client-facing frontend.
- **ALT-002:** Celery/Redis queue — rejected (CON-001); FIFO in-process worker suffices for one user.
- **ALT-003:** Embedding `generate_html_report.py` output as the main results view — rejected; kept only as a download (brainstorm ALT-004).

## Grill Me
1. **Q-001:** Will teammates need to reach the app from their machines soon (bind beyond 127.0.0.1)?
   - **Recommended default:** Localhost-only v1; revisit after first real usage.
   - **Why this matters:** Beyond localhost, no-auth is unsafe and one-worker concurrency may not hold.
   - **If answered differently:** Add a PHASE-05 task for a shared-password gate (env var) + `--host` flag, and raise the job queue's concurrency review.
2. **Q-002:** Is the solve cache (config-hash → reuse prior NREL results, with force re-solve) the desired default, as assumed in DEC-005?
   - **Recommended default:** Yes — protects rate limits and makes clone-and-edit fast.
   - **Why this matters:** Affects run-storage layout and PHASE-02 scope.
   - **If answered differently:** Drop TASK-02-05; every run always solves fresh; clone-and-edit re-runs take minutes.
3. **Q-003:** For the report download, is raw-JSON-only an acceptable v1 fallback if `generate_html_report.py` proves incompatible with `analysis` results (RISK-04-01)?
   - **Recommended default:** Yes — ship JSON download, log the HTML shim as follow-up.
   - **Why this matters:** Caps PHASE-04 scope; the HTML report is a convenience, not the acceptance gate.
   - **If answered differently:** Add a library-side adapter task (new module under `integration/`) and extend PHASE-04 exit criteria to require the HTML report.

## Suggested Next Step
Answer the three Grill Me questions (defaults are safe), then begin PHASE-01. Per project practice, copy the phase checklist into `activeContext.md` before implementation and work red/green from `tests/python/webapp/`.
