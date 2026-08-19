# Vietnam DPPA Web App

Internal, localhost-only FastAPI app over `reopt_pysam_vn.analysis`: guided deal
form → NREL REopt solve (background job) → results page with charts → run
history → two-run compare. No auth, single user, no database.

## Launch

From the repo `.venv` (Python 3.12 — PySAM only lives here):

```powershell
.venv\Scripts\python.exe -m pip install -e ".[webapp]"
$env:PYTHONPATH = "src/python"
.venv\Scripts\python.exe -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000/deals/new`.

## NREL API key

Live solves (onsite mode only) need a developer key. Either set an env var
(`NREL_DEVELOPER_API_KEY` or `NREL_API_KEY`) or create `NREL_API.env` at the
repo root with `API_KEY_NAME=<key>` — the same convention as
`scripts/python/reopt/solve_via_api.py`. `offsite_dppa`/`both` runs need
either a pre-solved `extracted` payload or a `deal_config.load["loads_kw"]`
8760-hour series (the web form supplies the latter; `POST /api/deals` with a
load CSV and `POST /api/runs` with `deal_config.load.loads_kw` both derive
`extracted` via `analysis.extracted.build_extracted_inputs`); there is no
live-solve path for them yet.

## Storage layout

One directory per run under `artifacts/webapp/runs/<run_id>/` (git-ignored;
override the root with `REOPT_PYSAM_VN_WEBAPP_RUNS_DIR` for tests or a second
instance):

- `deal_config.json` — the submitted `DealConfig`
- `status.json` — state machine: `queued → solving → analyzing → done` (or
  `error` with a message). Any run still in a non-terminal state (`queued`/
  `solving`/`analyzing`) when the app starts was orphaned by a previous
  process exiting mid-solve; it is marked `error` (`interrupted_restart`)
  rather than silently re-queued, so it never re-spends NREL API quota —
  clone it from the history page and resubmit.
- `reopt_results.json` — raw REopt output, once solved
- `result.json` — `run_onsite`/`run_offsite_dppa` output (summary only; the
  hourly ledger is not inlined)
- `ledger.csv` — hourly CfD settlement ledger (8760 rows + header) for offsite
  runs that produced a ledger; absent for onsite runs and bespoke artifacts that
  carry no ledger
- `provenance.json` — solver, cache hit, policy data versions, wall time;
  rendered as an "About this run" card on `/runs/{run_id}` once the run is done

## Solve cache

Runs are keyed by a hash of the solve-relevant `DealConfig` subset. A new
submission with the same hash reuses the prior run's `reopt_results.json`
instead of calling NREL again; check "force re-solve" in the form to bypass.
One solve runs at a time — additional submissions queue FIFO in-process
(`jobs.py`). Job state lives in `status.json`, so a server restart shows the
last known status rather than losing history; an in-flight job does not
resume, and any run left non-terminal by the restart is marked `error`
automatically on the next startup (see Storage layout above).

## Load uploads

The guided form accepts `CSV`, `XLSX`/`XLSM`/`XLS`, and `JSON` load files via
`ingestion.loader.ingest_factory_load`. A header row is auto-detected (e.g.
`load_kw`, `demand`, `consumption`), multi-sheet workbooks are scanned, missing
values are interpolated, negatives clipped, and 15-minute / 30-minute / monthly
series are resampled to 8760 hourly.

A "Load data quality" card on the run page reports the cleaning summary
(`missing_count`, `clipped_negative_count`, `synthesis_method`,
`synthesis_source_rows`, plus any `plausibility_warnings` such as a 20%+ zero
fraction or an unusually large peak).

## Tests

```powershell
$env:PYTHONPATH = ""
.venv\Scripts\python.exe -m pytest tests/python/webapp/
```

All NREL calls are mocked; nothing in the suite touches the network. The
Samsung/TTC golden-parity test (`test_golden_parity.py`) proves `POST /api/runs`
reproduces a direct `run_offsite_dppa` call bit-for-bit — the contract that the
webapp forks no analytics logic (CON-002). It deliberately does **not** re-assert
parity against `examples/samsung-ttc_combined-decision.example.json`, which
carries a known pre-existing divergence documented in
`reports/2026-07-26-samsung-parity-diagnosis.md`.
