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
`scripts/python/reopt/solve_via_api.py`. `offsite_dppa`/`both` runs always need
a pre-solved `extracted` payload; there is no live-solve path for them yet.

## Storage layout

One directory per run under `artifacts/webapp/runs/<run_id>/` (git-ignored;
override the root with `REOPT_PYSAM_VN_WEBAPP_RUNS_DIR` for tests or a second
instance):

- `deal_config.json` — the submitted `DealConfig`
- `status.json` — state machine: `queued → solving → analyzing → done` (or
  `error` with a message)
- `reopt_results.json` — raw REopt output, once solved
- `result.json` — `run_onsite`/`run_offsite_dppa` output

## Solve cache

Runs are keyed by a hash of the solve-relevant `DealConfig` subset. A new
submission with the same hash reuses the prior run's `reopt_results.json`
instead of calling NREL again; check "force re-solve" in the form to bypass.
One solve runs at a time — additional submissions queue FIFO in-process
(`jobs.py`). Job state lives in `status.json`, so a server restart shows the
last known status rather than losing history, but an in-flight job does not
resume — resubmit if a run is stuck `solving`/`analyzing` after a restart.

## Tests

```powershell
$env:PYTHONPATH = ""
.venv\Scripts\python.exe -m pytest tests/python/webapp/
```

All NREL calls are mocked; nothing in the suite touches the network. The
Samsung/TTC golden-parity test (`test_golden_parity.py`) proves the web API
path reproduces `examples/samsung-ttc_combined-decision.example.json`
bit-for-bit.
