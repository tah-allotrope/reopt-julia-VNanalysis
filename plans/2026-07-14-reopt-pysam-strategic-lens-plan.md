---
title: "reopt-pysam Strategic Lens — Ops Readiness, Type Gate, Offline Solve, Julia Archive, Config-Driven Case Runner"
date: "2026-07-14"
status: "draft"
request: "reopt-pysam-strategic-lens — turn research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md into a multi-phase implementation plan"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md"
  - "research/2026-07-11-reopt-pysam-next-level-brainstorm.md"
---

# Plan: reopt-pysam Strategic Lens — Ops Readiness, Type Gate, Offline Solve, Julia Archive, Config-Driven Case Runner

## Objective

Move `reopt-pysam` from "a hardened toolkit plus an internal web app" to "a durable product": give the web app an operator story (structured logging + per-run provenance + friendly errors + retention), enforce type contracts and a public-API boundary, add a no-key/no-network offline solve mode, end the "is Julia core or cruft?" ambiguity by archiving the stagnant Julia tree in place, and — the centerpiece — replace the one-off-module-per-deal pattern with a config-driven case runner + reporting pipeline proven on the largest bespoke monolith (`dppa_case_2.py`, 1481 lines) behind characterization tests, with Samsung/TTC bit-exact parity green throughout. This matters now because the web app just became a non-technical colleague's daily UI, which multiplies the value of these product-grade foundations and the blast radius of their absence.

## Context Snapshot

- **Current state:** A Vietnam DPPA techno-economic toolkit (`src/python/reopt_pysam_vn/`, ~11.8k LOC; REopt via the NREL REopt web API + PySAM developer finance) with a localhost FastAPI web app over it. Observability is inconsistent (only `webapp/jobs.py` uses `logging`; 14 bare `print()` calls in library code); errors reach users as raw `str(exc)`; there is no per-run provenance record and no run-retention policy. There is no `mypy`/`py.typed`/type gate and no declared public-API boundary despite rich type hints. There is no offline solve mode — onsite live solves require an NREL key and network. The Julia half (`src/julia/`, `scripts/julia/`, `Project.toml`, `Manifest.toml`) was last touched 2026-05-19 and is never called by the web app, yet the README sells it as the stack headline. `scripts/` holds **119** Python scripts (72 `analyze_/build_/run_/generate_`), and the largest source module is `integration/dppa_case_2.py` at 1481 lines — a bespoke, non-parity-gated blob with good phase-test coverage.
- **Desired state:** Every run writes a structured log line and a `provenance.json`; analyst-facing errors are typed and actionable; stale runs can be pruned by command. `mypy` runs green in CI on the stable surfaces (`analysis/`, `webapp/`); a `py.typed` marker ships; AGENTS.md documents `analysis` as the public API. A `--offline` / frozen-resource solve mode runs the full onsite pipeline with no key and no network. The Julia tree is relocated under `legacy/julia/` with the docs rewritten to name the NREL API as the primary solver and Julia as the optional offline engine. A `python -m reopt_pysam_vn.analysis run --config <deal>.json` config-driven case runner + a `report` subcommand exist, with `dppa_case_2` re-expressed as a config that routes through shared engines behind characterization tests. Samsung/TTC output stays bit-exact.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/webapp/{jobs.py,service.py,storage.py,results_view.py,routes/api.py}`, `src/python/reopt_pysam_vn/analysis/{__main__.py,offsite_dppa.py,onsite.py,types.py}`, `src/python/reopt_pysam_vn/integration/{dppa_case_2.py,dppa_samsung_ttc.py,settlement.py}`, `src/python/reopt_pysam_vn/reopt/preprocess.py`, `src/python/reopt_pysam_vn/common/`, `src/julia/`, `scripts/julia/`, `pyproject.toml`, `data/schemas/{deal_config,extracted_inputs}.schema.json`, `tests/python/{analysis,integration,webapp}/`, `tests/cross_language/`, `examples/samsung-ttc_combined-decision.example.json`, `AGENTS.md`, `README.md`, `docs/`.
- **Out of scope:** The 2026-07-11 foundation plan's security/hygiene work (NREL key rotation, untracking `.pptx`, `.gitignore` cleanup, `requirements.txt` consolidation) — that plan owns it (see CON-004); rewriting `dppa_samsung_ttc.py` (parity-gated — the config runner *wraps* it, never rewrites it); multi-tenant/auth/cloud hosting/billing; a metrics/tracing backend or external database (the filesystem run store stands); editing `data/vietnam/` policy files from the UI; Decree 243 data refresh (owned by the 2026-07-11 plan PHASE-06); Julia-side CI.

## Environment & Conventions

- **Stack:** Python 3.12 via the repo-local virtualenv at `.venv` (Windows: `.venv\Scripts\python.exe`). **PySAM 7.1.0 (`nrel-pysam`) exists only inside `.venv`** — the system Python (3.14) has no PySAM wheel and silently falls back to synthetic solar profiles, which changes numbers; always use the `.venv` interpreter. Web app is FastAPI + Jinja2 + vanilla JS + Leaflet, no build step, no npm. Julia 1.10 + REopt.jl v0.56.4 exists but is not solved from the app. Package layout: setuptools, `package-dir = {"" = "src/python"}`, declared in `pyproject.toml`.
- **Setup:** `.venv\Scripts\python.exe -m pip install -e ".[webapp]"` (PowerShell, from repo root). Add dev tools this plan needs: `.venv\Scripts\python.exe -m pip install mypy ruff pytest`.
- **Build / Run (web app):** `$env:PYTHONPATH = "src/python"; .venv\Scripts\python.exe -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000`
- **Test (full Python suite):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` — single test: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp/test_storage.py::test_name -x`. The 4-layer PowerShell runner `.\tests\run_all_tests.ps1` also covers Julia; only needed for the final regression and the Julia-archive phase.
- **Conventions & traps:**
  - **`PYTHONPATH` gotcha:** a global `PYTHONPATH` pointing at an unrelated venv breaks webapp tests with `ModuleNotFoundError: pydantic_core._pydantic_core`. Always clear it (`$env:PYTHONPATH = ""`) before pytest; pytest resolves the package via the `pythonpath = ["src/python"]` setting in `pyproject.toml`.
  - **All commands in this plan are PowerShell** (the repo's primary shell on Windows). `$env:NAME = ""` sets an env var for the session; `;` chains statements. Do not paste `$env:` syntax into a bash CI file.
  - **JSON reads use `encoding="utf-8-sig"`** throughout (tolerates a Windows UTF-8 BOM). Match that in every new reader; a plain `utf-8` read will crash on BOM'd files that currently work.
  - **Units:** tariffs and strikes are VND/kWh internally; strike *sweeps* run in US cents/kWh (`integration/strike_search.py`); finance outputs are USD. Never mix without an explicit conversion field. Timestamps in the run store are UTC formatted `%Y%m%dT%H%M%S%f`.
  - **Versioned policy data:** `data/vietnam/` files carry a `_meta` envelope; code reads only the `"data"` block; a policy update = a new versioned file + a one-line change in `data/vietnam/manifest.json`.
  - **Bit-exact parity gates:** `tests/python/webapp/test_golden_parity.py` and `tests/python/analysis/test_samsung_ttc_parity.py` compare `to_dict()` output against `examples/samsung-ttc_combined-decision.example.json` exactly. Any change that alters Samsung/TTC numeric output is a defect, not drift.
  - **Structural-move rule (from `lessons.md`):** after ANY file move or refactor, run the FULL Python suite, never a subset — subset runs have missed integration breakage in this repo before. When a numeric test fails after a refactor, prove cause vs pre-existing by running it at the prior commit in a `git worktree` before assuming it is yours.
  - **`.gitignore` negations have burned this repo** — do not restructure ignore sections opportunistically; make only minimal additions and run `git status` after.
- **Repo map:**
  - `src/python/reopt_pysam_vn/analysis/` — public front door: `types.py` (`DealConfig`, `OnsiteResult`, `OffsiteDppaResult`; `MODES = ("onsite","offsite_dppa","both")`), `onsite.py`, `offsite_dppa.py` (`_ORCHESTRATORS` registry, `register_orchestrator`, currently only `"DPPA_SAMSUNG_TTC"`), `__main__.py` (CLI with `onsite` / `offsite_dppa` subcommands, `_load_json` uses utf-8-sig).
  - `src/python/reopt_pysam_vn/integration/` — engines: `settlement.py` (`ContractParams`, `compute_hourly_settlement`, `compute_buyer_benchmark`, `run_strike_sweep`), `strike_search.py`, `dppa_samsung_ttc.py` (1058-line golden path, `build_samsung_ttc_combined_decision`), bespoke cases `dppa_case_1/2/3.py`, `ninhsim_solar_storage_60pct.py`, `factory_a.py`. `dppa_case_2.py` exposes `build_dppa_case_2_*` builders and `build_scenario_dppa_case_2(extracted)`.
  - `src/python/reopt_pysam_vn/webapp/` — FastAPI app: `__init__.py` (`create_app`), `routes/api.py`, `routes/pages.py`, `service.py` (`run_analysis`, `solve_relevant_hash`, `load_nrel_api_key`, `solve_onsite_via_nrel`, error classes `AnalysisError`/`MissingInputsError`/`OrchestratorNotRegisteredError`), `jobs.py` (`JobManager` FIFO worker), `storage.py` (`RunStorage`), `forms.py`, `uploads.py`, `projects.py`, `results_view.py`, `compare.py`, `templates/*.html`, `static/{app.js,map.js}`.
  - `src/python/reopt_pysam_vn/common/` — `currency.py`, `time_series.py`, `validation.py` (the intended home for shared kernels/unit discipline; currently underused).
  - `data/schemas/` — `deal_config.schema.json`, `extracted_inputs.schema.json`. `data/vietnam/` — versioned policy JSON + `manifest.json`.
  - `tests/python/{analysis,ingestion,integration,pysam,reopt,webapp}/` — pytest; webapp tests mock all NREL calls. `tests/cross_language/cross_validate.py` — Julia vs Python parity.

## Research Inputs

- From `research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md`:
  - The 2026-07-11 foundation roadmap (security → CI → offsite generalization) is correct and **unexecuted**; its P0–P2 remain the correct *first* moves and this plan does not re-argue them. This plan is the strategic overlay that follows.
  - **Script sprawl is the real architecture problem:** 119 scripts (77 in `integration/`), 72 one-off `analyze_/build_/run_/generate_`. The root cause behind both the module monoliths and the single-tenant offsite path is that every new deal spawns a new hand-written module + script instead of a config + a shared engine run. The fix is a config-driven case runner + reporting pipeline (DEC-102), a superset of the 2026-07-11 plan's DEC-008 "registry expansion" and DEC-016 "script debloat".
  - The largest source module is `dppa_case_2.py` (1481 lines), **not** Samsung (1058); `dppa_case_2` is **not** bit-exact-gated and has phase-test coverage (`test_dppa_case_2_phase_{ab,cd,e,f,g}.py`), making it the right lower-risk proving ground for the config runner (DEC-103).
  - The Julia half is stagnant (last touched 2026-05-19), never called by the web app, yet sold as the stack headline; the debt is the ambiguity. Chosen resolution: archive in place under `legacy/julia/` and rewrite docs to name the NREL API as primary (DEC-104), pending the human veto in Q-101.
  - The web app is now the primary UI but has no operator story: inconsistent logging, raw-string errors, no provenance, no retention. A structured run log + per-run provenance + friendly error layer is a bigger day-2 win than a second orchestrator (DEC-105).
  - Type hints are decoration, not enforced: no `mypy`/`py.typed`/type gate, no declared public-API boundary; adding one mechanically defends the "no forking analytics into the webapp" constraint (DEC-106).
  - Add a frozen-resource offline solve mode so the full pipeline runs with no key/network — good for CI, demos, and offline use (DEC-107). Do NOT vectorize settlement speculatively — measure first (DEC-108).
- From `research/2026-07-11-reopt-pysam-next-level-brainstorm.md`:
  - Samsung/TTC parity is bit-exact-gated by two test files; any refactor near `dppa_samsung_ttc.py`, `settlement.py`, or the webapp analysis path must leave those green at every commit.
  - The web app must never fork analytics logic; it only calls `reopt_pysam_vn.analysis`/`integration` code (standing constraint).
  - Run storage stays filesystem/no-DB; the only fragile bit is the restart-fragile ordering — the class-level `RunStorage._counter`. (This plan touches `storage.py` for provenance/retention but leaves the ordering fix to the 2026-07-11 plan to avoid a merge conflict; see CON-004 and Gotchas.)

## Assumptions and Constraints

- **ASM-001:** The 2026-07-11 foundation plan (its PHASE-01 security/hygiene + PHASE-02 CI + red-test paydown) is executed **before** this plan's PHASE-05, so a green CI + parity gate exists to protect the config-runner refactor. — **BINDING DEFAULT:** if that plan has not run when this plan starts, PHASE-02 of *this* plan creates a minimal `.github/workflows/ci.yml` (ruff + `pytest -m "not network"`) as part of adding the `mypy` gate, so the type/parity gate still exists; and PHASE-05 first runs the full suite to record a green baseline before refactoring.
- **ASM-002:** No one currently solves locally in Julia; the NREL REopt web API is the sole live solve path going forward (Q-101). — **BINDING DEFAULT:** proceed with the Julia archive-in-place (PHASE-04); it is reversible (`git mv` only). If a maintainer still runs Julia solves, they edit this ASM line and skip PHASE-04 — no other phase depends on it.
- **ASM-003:** `dppa_case_2.py`'s current output (via its `build_dppa_case_2_*` builders) is a finished analysis safe to freeze behind characterization tests before decomposition (Q-103). — **BINDING DEFAULT:** treat it as finished; PHASE-05 writes characterization tests capturing its exact current output first, then refactors against them.
- **ASM-004:** `nrel-pysam>=7.1` is installable in CI on ubuntu-latest / Python 3.12. — **BINDING DEFAULT:** if it fails to install, drop it from the CI install line and rely on the suite's existing skip-when-PySAM-unavailable behavior; the `mypy` gate and non-PySAM tests still run.
- **ASM-005:** No pytest marker distinguishes network-hitting tests unless the 2026-07-11 plan added one. — **BINDING DEFAULT:** if a `network` marker is not registered in `pyproject.toml`, register it (`markers = ["network: makes real HTTP calls; excluded in CI"]`) and CI runs `-m "not network"`; PHASE-03's offline mode is what lets the onsite pipeline be exercised without the marker.
- **ASM-006:** The web app's run store is single-user localhost; retention pruning is a manual command, not an automatic background sweep. — **BINDING DEFAULT:** implement `prune` as an explicit CLI/route action guarded by an age threshold; never auto-delete on startup.
- **ASM-007:** The exact `strike_sweep`/settlement dict keys are not restated here. — **BINDING DEFAULT:** derive them at implementation time from `examples/samsung-ttc_combined-decision.example.json` and the `data/schemas/extracted_inputs.schema.json`, and write extractors against those actual keys.
- **CON-001:** Samsung/TTC output is bit-exact-gated (`tests/python/analysis/test_samsung_ttc_parity.py`, `tests/python/webapp/test_golden_parity.py`); every phase must leave those green. "Close" is failing.
- **CON-002:** The web app never forks analytics logic — it only calls `reopt_pysam_vn.analysis`/`integration`. The config runner (PHASE-05) lives in `analysis`, not `webapp`.
- **CON-003:** All new JSON readers use `encoding="utf-8-sig"`.
- **CON-004:** This plan does NOT do the 2026-07-11 plan's security/hygiene work and does NOT change `RunStorage` run-ordering (`list_runs` sort key / `_counter`), to avoid conflicting with that plan. It only *adds* `provenance.json` writing and a `prune` method to `storage.py`.
- **DEC-101:** This is a complementary strategic overlay executed after the 2026-07-11 plan's foundation, not a replacement.
- **DEC-102:** Reframe "registry expansion" + "script debloat" as one initiative: a config-driven case runner + reporting pipeline. A new deal becomes a descriptor + a generic run; bespoke modules collapse into config. Parity-gated at every step.
- **DEC-103:** Prove the config runner on `dppa_case_2.py` (1481 lines, not parity-gated, well-tested) — not on the Samsung golden.
- **DEC-104:** Archive Julia in place under `legacy/julia/`; rewrite docs to name the NREL API as primary; keep Julia as the optional offline engine. Reversible.
- **DEC-105:** Add an ops-readiness slice: structured logging, per-run `provenance.json`, a friendly error taxonomy, and a run-retention `prune`.
- **DEC-106:** Add a `mypy` type gate on `analysis/` + `webapp/`, a `py.typed` marker, and a documented public-API boundary.
- **DEC-107:** Add a frozen-resource offline solve mode (no key, no network).
- **DEC-108:** Measure settlement performance before optimizing; vectorize only if the interactive path is demonstrably slow.

## Specification

**Per-run provenance record (PHASE-01).** Every run writes `provenance.json` into its run directory alongside `status.json`. Exact shape:

```
{
  "run_id": "<run_id>",
  "created_at": "<UTC %Y%m%dT%H%M%S%f>",
  "solver": "nrel_api" | "offline_frozen" | "cached",
  "nrel_key_fingerprint": "<sha256(api_key)[:12]>" | null,   // never the key itself
  "solve_hash": "<solve_relevant_hash>",
  "cache_hit": true | false,
  "cached_from_run_id": "<run_id>" | null,
  "policy_data_versions": { "<manifest key>": "<version string>", ... },  // from data/vietnam/manifest.json
  "wall_time_seconds": <float>,
  "pysam_available": true | false,
  "package_version": "<pyproject version>"
}
```

- `nrel_key_fingerprint` is `sha256(api_key.encode()).hexdigest()[:12]` — a stable, non-reversible tag proving *which* key ran without storing the secret. `null` when no key was used (offline/cached).
- `policy_data_versions` is read from `data/vietnam/manifest.json` (the `_meta`/version fields of the active files), so a run records the policy vintage it used.

**Friendly error taxonomy (PHASE-01).** Map internal exceptions to `{code, message, hint}` before writing them into `status.json`:

| Exception | code | analyst-facing message | hint |
|---|---|---|---|
| `MissingInputsError` | `MISSING_INPUTS` | verbatim `str(exc)` | "Upload the required pre-solved inputs, or submit an onsite deal for a live solve." |
| `OrchestratorNotRegisteredError` | `NO_ORCHESTRATOR` | verbatim `str(exc)` | "This deal case has no offsite model yet; use a registered case or the generic runner." |
| `RuntimeError` containing `"NREL API key not found"` | `NO_API_KEY` | "No NREL API key configured." | "Set NREL_DEVELOPER_API_KEY or run in offline mode." |
| any `requests`/HTTP error | `SOLVER_HTTP_ERROR` | "The NREL REopt solver rejected or could not process this request." | "Check site coordinates and load profile; retry, or run offline." |
| anything else | `INTERNAL_ERROR` | "An unexpected error occurred while processing this run." | "See the server log for the full traceback (run_id is logged)." |

**Config-driven case runner routing (PHASE-05).** `run_case(deal_config, extracted=None, run_developer=True)` resolves an orchestrator in this order (extends the existing `run_offsite_dppa` resolution):

1. If `deal_config.mode == "onsite"` → route to `run_onsite` (unchanged).
2. Else (`offsite_dppa`/`both`): look up `deal_config.case` in `_ORCHESTRATORS`.
   - Hit → call the registered orchestrator (Samsung stays exactly as today).
   - Miss → if `extracted` carries the minimum generic keys (a generation `results`/profile + a market/tariff series + a load series + contract params, per `data/schemas/extracted_inputs.schema.json`), route to the generic builder and stamp `result["quality"]["orchestrator"] = "generic"`; otherwise raise `OrchestratorNotRegisteredError` with the list of registered cases.
3. `dppa_case_2` is registered as `"DPPA_CASE_2"` → a thin wrapper `build_dppa_case_2_combined_decision(extracted, *, run_developer=True)` that composes the existing `build_dppa_case_2_*` builders into the 7-block contract (`deal, base_settlement, strike_sweep, adder_sensitivity, regime_stress, decision, quality`), filling genuinely inapplicable blocks with `{}`.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Web-app operational readiness | None | Structured logging, per-run `provenance.json`, friendly error taxonomy, `prune` retention command |
| PHASE-02 | Type gate + public-API boundary | None (parallel to 01) | `mypy` config + green run on `analysis`/`webapp`, `py.typed`, public-API doc, CI `mypy` step |
| PHASE-03 | Offline / frozen-resource solve mode | None (parallel) | `--offline` full onsite pipeline with no key/network; frozen resource fixture |
| PHASE-04 | Archive Julia in place + doc honesty | None (gated by ASM-002/Q-101) | `legacy/julia/` tree; README/AGENTS rewritten; cross-language tests relocated/marked |
| PHASE-05 | Config-driven case runner + reporting pipeline | PHASE-02 (type/parity gate); ASM-001 CI | `run`/`report` CLI subcommands; `dppa_case_2` registered + characterized; generic fallback |
| PHASE-06 | Settlement performance (measure-first) | PHASE-05 | Benchmark harness; vectorized kernel only if measured slow |

## Detailed Phases

### PHASE-01 - Web-App Operational Readiness

**Goal**
Give the web app an operator story without changing analytics output or the storage design: consistent structured logging, a per-run provenance record, an analyst-friendly error layer, and a manual run-retention command.

**Tasks**
- [ ] TASK-01-01: Add a `configure_logging()` helper in a new module `src/python/reopt_pysam_vn/webapp/logging_config.py` that installs a `logging.StreamHandler` with a fixed format (`%(asctime)s %(levelname)s %(name)s %(message)s`) on the `reopt_pysam_vn` logger at `INFO`, idempotently (no duplicate handlers on re-call). Call it once from `create_app` in `webapp/__init__.py`.
- [ ] TASK-01-02: Replace the 14 bare `print()` calls in library code under `src/python/reopt_pysam_vn/` with module-level `logger = logging.getLogger(__name__)` calls at the appropriate level (`info`/`warning`). Find them with `grep -rn "print(" src/python/reopt_pysam_vn --include="*.py"`. Do NOT touch `print()` calls inside `scripts/` (those are user-facing CLI output) or inside `analysis/__main__.py`'s `_emit` (that is the CLI's stdout contract).
- [ ] TASK-01-03: Add `write_provenance(run_id, provenance: dict)` and `get_provenance(run_id)` methods to `RunStorage` in `webapp/storage.py`, writing/reading `provenance.json` in the run dir (utf-8, `indent=2`). Do NOT change `create_run`, `list_runs` sort logic, or `_counter` (CON-004).
- [ ] TASK-01-04: Build the provenance dict in `webapp/jobs.py::_process` per the `## Specification`, timing the solve with `time.perf_counter()`, fingerprinting the key via `hashlib.sha256`, reading `policy_data_versions` from `data/vietnam/manifest.json`, and recording `cache_hit`/`cached_from_run_id`. Call `storage.write_provenance(run_id, prov)` right before the final `set_status(run_id, state="done")`.
- [ ] TASK-01-05: Add `src/python/reopt_pysam_vn/webapp/errors.py` with `to_user_error(exc: Exception) -> dict` implementing the `## Specification` taxonomy (returns `{"code","message","hint"}`). In `jobs.py::_worker_loop`'s `except` block and in `_process`'s offsite-block branch, replace `message=str(exc)` with the mapped dict fields (write `error_code`, `message`, `error_hint` into status). Keep `logger.exception(...)` — the full traceback still goes to the server log.
- [ ] TASK-01-06: Add `RunStorage.prune(older_than_days: int, *, dry_run: bool = True) -> list[str]` that returns run_ids whose `created_at` is older than the threshold and, when `dry_run=False`, deletes those run directories (`shutil.rmtree`). Never delete a run whose `state` is `queued`/`solving`/`analyzing`. Expose it as a CLI subcommand `python -m reopt_pysam_vn.webapp.prune --days N [--apply]` via a new `src/python/reopt_pysam_vn/webapp/prune.py` `main()`.
- [ ] TASK-01-07: Surface the friendly error on the run page: in `webapp/templates/run.html`, where the error state renders, show `message` and `hint` (and `error_code` in small text) when present, falling back to the old raw message for older runs. Leave the happy-path rendering alone.

**File Changes**
- `src/python/reopt_pysam_vn/webapp/logging_config.py` (create): `configure_logging()`.
- `src/python/reopt_pysam_vn/webapp/__init__.py` (modify): call `configure_logging()` in `create_app`; leave routing/mounting alone.
- `src/python/reopt_pysam_vn/webapp/errors.py` (create): `to_user_error`.
- `src/python/reopt_pysam_vn/webapp/storage.py` (modify): add `write_provenance`, `get_provenance`, `prune`; **do not** alter `create_run`/`list_runs`/`_counter`.
- `src/python/reopt_pysam_vn/webapp/jobs.py` (modify): build + write provenance in `_process`; map errors via `errors.to_user_error` in `_worker_loop`/`_process`.
- `src/python/reopt_pysam_vn/webapp/prune.py` (create): CLI `main()`.
- `src/python/reopt_pysam_vn/webapp/templates/run.html` (modify): render friendly error fields.
- Library modules containing `print()` (modify): swap to `logger` calls per TASK-01-02.
- `tests/python/webapp/test_storage.py`, `tests/python/webapp/test_jobs.py`, `tests/python/webapp/test_errors.py` (create/modify): coverage per Test Specs.

**Function Signatures**
- `configure_logging() -> None` — idempotently installs the `reopt_pysam_vn` stream handler at INFO.
- `to_user_error(exc: Exception) -> dict` — returns `{"code": str, "message": str, "hint": str}` per the taxonomy.
- `RunStorage.write_provenance(self, run_id: str, provenance: dict) -> None` — writes `provenance.json` in the run dir.
- `RunStorage.get_provenance(self, run_id: str) -> Optional[dict]` — reads it, or `None` if absent.
- `RunStorage.prune(self, older_than_days: int, *, dry_run: bool = True) -> list[str]` — returns (and optionally deletes) stale terminal-state run_ids.

**Test Specs**
- `to_user_error(MissingInputsError("needs extracted"))` → `{"code": "MISSING_INPUTS", "message": "needs extracted", "hint": <the missing-inputs hint>}`.
- `to_user_error(RuntimeError("NREL API key not found. ..."))` → `code == "NO_API_KEY"`.
- `to_user_error(ValueError("weird"))` → `code == "INTERNAL_ERROR"`, `message` is the generic message (not `"weird"`).
- `RunStorage(tmp)` create a run, `write_provenance(id, {...})`, `get_provenance(id)` → returns the same dict; `get_provenance(<other id>)` → `None`.
- `prune(older_than_days=30, dry_run=True)` on a store with one 40-day-old `done` run and one fresh `done` run → returns `[old_id]` and deletes nothing; with `dry_run=False` → the old run dir no longer exists, the fresh one remains.
- `prune` never returns/deletes a run whose `state` is `solving` even if old.
- After a mocked solve in `test_jobs.py`, the run dir contains `provenance.json` with `solver`, `solve_hash`, `cache_hit`, `wall_time_seconds`, and a 12-char `nrel_key_fingerprint` (or `null`), and no field equals the raw key.

**Dependencies**
- None.

**Exit Criteria**
- [ ] `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp -q` → 0 failed, new cases included.
- [ ] `grep -rn "print(" src/python/reopt_pysam_vn --include="*.py"` returns only `analysis/__main__.py` `_emit` (and none in `webapp`/`integration`/`reopt` libraries).
- [ ] A mocked solve writes `provenance.json`; an errored run shows `code`/`hint` on the run page; the raw key never appears in any run file.

**Phase Risks**
- **RISK-01-01:** Swapping a `print()` that a test asserts on stdout — mitigation: grep tests for `capsys`/`capfd` around the changed modules before swapping; keep CLI/script prints.

### PHASE-02 - Type Gate + Public-API Boundary

**Goal**
Make the type hints enforced contracts on the stable surfaces and declare a public-API boundary that mechanically discourages forking analytics into the web app.

**Tasks**
- [ ] TASK-02-01: Add `[tool.mypy]` to `pyproject.toml`: `python_version = "3.10"`, `warn_unused_ignores = true`, `ignore_missing_imports = true` (PySAM/requests have no stubs), and per-module strictness scoped to the stable surfaces via `[[tool.mypy.overrides]]` — enable `disallow_untyped_defs = true` for modules matching `reopt_pysam_vn.analysis.*` and `reopt_pysam_vn.webapp.*`; leave `integration.*`/`reopt.*`/`scripts` lenient for now.
- [ ] TASK-02-02: Run `.venv\Scripts\python.exe -m mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` and fix only real type errors it reports (add annotations/`Optional`s; do not add blanket `# type: ignore`). Record any unavoidable ignore with a reason comment.
- [ ] TASK-02-03: Add an empty `src/python/reopt_pysam_vn/py.typed` marker file and include it in packaging: add `[tool.setuptools.package-data] "reopt_pysam_vn" = ["py.typed"]` to `pyproject.toml`.
- [ ] TASK-02-04: Document the public-API boundary: add a short "Public API" section to `AGENTS.md` §5 stating that `reopt_pysam_vn.analysis` (`DealConfig`, `run_onsite`, `run_offsite_dppa`, and from PHASE-05 `run_case`) is the supported surface, and `integration`/`reopt`/`pysam` are internal engines that may change. Add the same one-liner to the top docstring of `analysis/__init__.py`.
- [ ] TASK-02-05: Wire `mypy` into CI. If `.github/workflows/ci.yml` exists (from the 2026-07-11 plan), add a step `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` after the ruff step. If it does not exist (ASM-001 default), create `.github/workflows/ci.yml`: trigger on `push` + `pull_request`; `ubuntu-latest`; `actions/setup-python@v5` with `python-version: "3.12"`; steps `pip install -e ".[webapp]" mypy ruff pytest`, `ruff check src/python tests scripts/python`, `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp`, `python -m pytest tests/python -m "not network" -q`.

**File Changes**
- `pyproject.toml` (modify): add `[tool.mypy]` + overrides + `package-data`; leave dependencies/packaging structure otherwise intact.
- `src/python/reopt_pysam_vn/py.typed` (create): empty marker.
- `src/python/reopt_pysam_vn/analysis/__init__.py` (modify): public-API docstring line.
- `AGENTS.md` (modify): "Public API" note in §5.
- `.github/workflows/ci.yml` (create or modify): add `mypy` step (ASM-001).
- `src/python/reopt_pysam_vn/{analysis,webapp}/*.py` (modify): only the minimal annotations mypy requires.

**Function Signatures**
- None — no code interfaces change in this phase (annotations only).

**Test Specs**
- None — no testable behavior changes in this phase. Verification is the `mypy` exit code (TEST-002).

**Dependencies**
- None (parallel to PHASE-01, but easiest after it so the new webapp modules are typed once).

**Exit Criteria**
- [ ] `.venv\Scripts\python.exe -m mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` → exit 0.
- [ ] `py.typed` ships (`.venv\Scripts\python.exe -c "import importlib.resources, reopt_pysam_vn; print((importlib.resources.files('reopt_pysam_vn')/'py.typed').is_file())"` → `True`).
- [ ] CI has a `mypy` step; AGENTS.md and `analysis/__init__.py` state the public-API boundary.

**Phase Risks**
- **RISK-02-01:** `disallow_untyped_defs` surfaces a large error count in `webapp` — mitigation: fix incrementally; if a module is genuinely too noisy this cycle, scope the override to `analysis.*` only and add `webapp.*` in a follow-up, documenting the deferral in the phase exit note.

### PHASE-03 - Offline / Frozen-Resource Solve Mode

**Goal**
Run the full onsite pipeline with no NREL key and no network, so CI, demos, and offline machines exercise the real analysis path against a frozen solar/REopt resource.

**Tasks**
- [ ] TASK-03-01: Capture a frozen resource fixture: save one real onsite REopt solve result (an existing golden under `examples/` or a fresh capture) to `tests/python/fixtures/offline/onsite_reopt_results.json` (utf-8). Document its provenance (source deal, capture date) in a sibling `README.md`.
- [ ] TASK-03-02: Add an offline branch to `webapp/service.py`: a new function `solve_onsite_offline(deal_config: DealConfig) -> Dict[str, Any]` that returns the frozen result (loaded via `utf-8-sig`) instead of calling the NREL API, selected when `os.environ.get("REOPT_PYSAM_VN_OFFLINE") == "1"` or an explicit `offline=True` flag is passed. `solve_onsite_via_nrel` is unchanged; add a thin dispatcher `solve_onsite(deal_config, *, offline: bool = False)` that picks the path.
- [ ] TASK-03-03: Thread `offline` through `jobs.py::_process` (read the env var once) and record `solver: "offline_frozen"` + `nrel_key_fingerprint: null` in the provenance dict (PHASE-01).
- [ ] TASK-03-04: Add `--offline` support to the analysis CLI (`analysis/__main__.py`): when set on the `onsite` subcommand, load the frozen results instead of requiring `--results`. Document offline mode in `webapp/README.md` and `README.md` (a short "Offline mode" subsection).
- [ ] TASK-03-05: Add a CI-runnable offline smoke test that submits an onsite deal with `REOPT_PYSAM_VN_OFFLINE=1` and asserts the run reaches `state == "done"` with a non-empty result — no network, no key, not marked `network`.

**File Changes**
- `tests/python/fixtures/offline/onsite_reopt_results.json` (create) + `tests/python/fixtures/offline/README.md` (create): frozen resource + provenance.
- `src/python/reopt_pysam_vn/webapp/service.py` (modify): add `solve_onsite_offline` + `solve_onsite` dispatcher; leave `solve_onsite_via_nrel`, `run_analysis`, `solve_relevant_hash`, `load_nrel_api_key` intact.
- `src/python/reopt_pysam_vn/webapp/jobs.py` (modify): read the offline flag; pass through; set provenance `solver`.
- `src/python/reopt_pysam_vn/analysis/__main__.py` (modify): `--offline` flag on the `onsite` subcommand.
- `README.md`, `src/python/reopt_pysam_vn/webapp/README.md` (modify): "Offline mode" docs.
- `tests/python/webapp/test_jobs.py` (modify): offline smoke test.

**Function Signatures**
- `solve_onsite_offline(deal_config: DealConfig) -> Dict[str, Any]` — returns the frozen REopt results dict (no network).
- `solve_onsite(deal_config: DealConfig, *, offline: bool = False) -> Dict[str, Any]` — dispatches to the offline or NREL path.

**Test Specs**
- With `REOPT_PYSAM_VN_OFFLINE=1`, submitting an onsite deal (mocked storage, no network) → run reaches `state == "done"`; result has a non-empty onsite block; `provenance.json` has `solver == "offline_frozen"` and `nrel_key_fingerprint is None`.
- `solve_onsite(deal, offline=True)` returns a dict with the same top-level keys as the frozen fixture; `solve_onsite(deal, offline=False)` still routes to the NREL path (assert via a patched `solve_onsite_via_nrel`).
- CLI `python -m reopt_pysam_vn.analysis onsite --config <deal> --offline` writes a result JSON without needing `--results` or a key.

**Dependencies**
- None (provenance `solver` field integrates with PHASE-01 if present; if PHASE-01 not yet done, still set the field where the provenance dict is built).

**Exit Criteria**
- [ ] Offline onsite run completes with `NREL_DEVELOPER_API_KEY` unset and no network access.
- [ ] `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp/test_jobs.py -q` → 0 failed with the offline smoke test included.

**Phase Risks**
- **RISK-03-01:** The frozen fixture drifts from the live REopt schema over time — mitigation: capture the fixture from an existing tracked golden where possible and note in its README that it is a snapshot, not a contract; the `network`-marked live tests still validate the real schema.

### PHASE-04 - Archive Julia In Place + Documentation Honesty

**Goal**
End the "is Julia core or cruft?" ambiguity: relocate the stagnant Julia tree under `legacy/julia/`, keep it runnable as the optional offline engine, and rewrite the docs so the NREL API is named as the primary solver. (Gated by ASM-002 / Q-101 — skip if a maintainer still solves in Julia.)

**Tasks**
- [ ] TASK-04-01: `git mv` the Julia tree into `legacy/julia/`: `src/julia/` → `legacy/julia/src/`, `scripts/julia/` → `legacy/julia/scripts/`, `Project.toml`/`Manifest.toml` → `legacy/julia/`. Use `git mv` (never delete + recreate) so history follows.
- [ ] TASK-04-02: Update every path reference to the moved files. Find them with `grep -rn "src/julia\|scripts/julia\|REoptVietnam\|run_vietnam_scenario\|Project.toml\|Manifest.toml" --include="*.md" --include="*.py" --include="*.jl" --include="*.ps1" .` and rewrite each to the `legacy/julia/...` path. Include `tests/run_all_tests.ps1` (the Julia layer paths) and `tests/cross_language/cross_validate.py`.
- [ ] TASK-04-03: Relocate or re-mark the cross-language parity: move `tests/cross_language/` to `legacy/julia/tests/cross_language/` (or, if pytest still collects it, mark it with a `julia` marker registered in `pyproject.toml` and excluded from the default/CI run). The Python side of the cross-check stays authoritative for the toolkit; the Julia comparison becomes a `legacy` concern.
- [ ] TASK-04-04: Rewrite the README stack section (lines describing "Julia 1.10+ with REopt.jl v0.56.4" as the headline) to: "**Primary solver:** NREL REopt web API (`developer.nlr.gov`) + PySAM developer finance. **Optional offline engine:** Julia REopt.jl v0.56.4, retained under `legacy/julia/`." Update the "Project Structure", "Quick Start", and "Vietnam Preprocessing Tool (Julia)" sections to point at `legacy/julia/` and note it is optional. Update `AGENTS.md` §2 (Environment) and §4 (Current Status) the same way.
- [ ] TASK-04-05: Add `legacy/julia/README.md` explaining the archive decision (date, that the NREL API is now primary, how to still run a local Julia solve), citing this plan.
- [ ] TASK-04-06: Run the FULL Python suite (structural-move rule) and confirm no Python test imported anything via a `src/julia`/`scripts/julia` path segment.

**File Changes**
- `src/julia/`, `scripts/julia/`, `Project.toml`, `Manifest.toml` (move → `legacy/julia/...`).
- `tests/cross_language/` (move or mark per TASK-04-03).
- `tests/run_all_tests.ps1` (modify): Julia layer paths → `legacy/julia/...`.
- `README.md`, `AGENTS.md` (modify): stack/structure/quick-start rewrite per TASK-04-04.
- `legacy/julia/README.md` (create): archive rationale.
- `pyproject.toml` (modify, only if TASK-04-03 marks): register a `julia` marker.

**Function Signatures**
- None — no code interfaces change in this phase.

**Test Specs**
- None — no testable behavior changes; verification is the full suite staying green after the move (TEST-005) and no broken path references (TEST-006).

**Dependencies**
- None; independent of other phases. Gated by ASM-002.

**Exit Criteria**
- [ ] `git ls-files "src/julia/*" "scripts/julia/*"` → empty; `git ls-files "legacy/julia/*"` → the moved tree.
- [ ] `grep -rn "src/julia\|scripts/julia" --include="*.md" --include="*.py" --include="*.ps1" .` → no stale references (only `legacy/julia/...`).
- [ ] `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` → 0 failed after the move.
- [ ] README/AGENTS name the NREL API as primary and Julia as optional/legacy.

**Phase Risks**
- **RISK-04-01:** A Python test loads Julia-adjacent data by path segment (the `lessons.md` `archive/` trap) — mitigation: grep the BARE names (`julia`, `REoptVietnam`, `run_vietnam_scenario`), not just `src/julia/`, before moving, and run the full suite after.

### PHASE-05 - Config-Driven Case Runner + Reporting Pipeline

**Goal**
Replace the one-off-module-per-deal pattern with a config-driven runner: a new deal is a `DealConfig` JSON routed through shared engines, and `dppa_case_2` is re-expressed as a registered case behind characterization tests — with Samsung/TTC bit-exact parity green at every commit.

**Tasks**
- [ ] TASK-05-01: Record a green baseline first: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` and save the summary. Do not proceed until the parity tests pass (or, per ASM-001/RISK, until the 2026-07-11 red-test paydown is done).
- [ ] TASK-05-02: Write characterization tests for `dppa_case_2` in `tests/python/integration/test_dppa_case_2_characterization.py`: call each existing `build_dppa_case_2_*` builder (and `build_scenario_dppa_case_2`) with the module's own extracted fixture and assert the full returned dicts equal a captured golden `tests/python/fixtures/dppa_case_2/*.json`. This freezes current behavior before any refactor.
- [ ] TASK-05-03: Add `build_dppa_case_2_combined_decision(extracted: dict, *, run_developer: bool = True) -> dict` in `integration/dppa_case_2.py` composing the existing builders into the 7-block contract (`deal, base_settlement, strike_sweep, adder_sensitivity, regime_stress, decision, quality`), filling inapplicable blocks with `{}`. Register it in `analysis/offsite_dppa.py::_ORCHESTRATORS` under `"DPPA_CASE_2"` via a lazy-import wrapper exactly like `_samsung_ttc_orchestrator`.
- [ ] TASK-05-04: Add the config-driven runner `run_case(deal_config, *, extracted=None, results=None, run_developer=True)` in a new `src/python/reopt_pysam_vn/analysis/case_runner.py`, implementing the routing in `## Specification` (onsite → `run_onsite`; offsite → registry hit; miss + sufficient `extracted` → generic builder stamped `quality.orchestrator="generic"`; else `OrchestratorNotRegisteredError`). Export it from `analysis/__init__.py`.
- [ ] TASK-05-05: Add a generic offsite builder `build_generic_combined_decision(extracted, *, run_developer=True) -> dict` in `src/python/reopt_pysam_vn/integration/offsite_generic.py`, composed ONLY of existing engines (`compute_hourly_settlement` + `compute_buyer_benchmark` → `base_settlement`; `run_strike_sweep`/`sweep_strike_prices` → `strike_sweep`; `adder_sensitivity`/`regime_stress` → `{}` in v1 with a `quality` note `"generic-v1: adder/regime blocks not modeled"`).
- [ ] TASK-05-06: Add CLI subcommands to `analysis/__main__.py`: `run --config <deal>.json [--extracted e.json] [--results r.json] [--offline] [--out o.json]` (routes through `run_case`), and `report --config <deal>.json [--extracted ...] --format {md,json} [--out ...]` producing a human-readable summary (headline metrics + decision) — reuse `webapp/results_view.py` extractors so reporting is not forked (CON-002). Place shared report-rendering logic in `src/python/reopt_pysam_vn/analysis/reporting.py`.
- [ ] TASK-05-07: Run the FULL suite (structural-change rule). Confirm Samsung parity is bit-exact and the `dppa_case_2` characterization tests pass.

**File Changes**
- `tests/python/integration/test_dppa_case_2_characterization.py` (create) + `tests/python/fixtures/dppa_case_2/*.json` (create): frozen goldens.
- `src/python/reopt_pysam_vn/integration/dppa_case_2.py` (modify): add `build_dppa_case_2_combined_decision` only; leave existing builders untouched.
- `src/python/reopt_pysam_vn/analysis/offsite_dppa.py` (modify): add `_dppa_case_2_orchestrator` lazy wrapper + registry entry + generic fallback in `run_offsite_dppa`; keep `register_orchestrator` and the injected-`combined_decision_fn` path unchanged.
- `src/python/reopt_pysam_vn/analysis/case_runner.py` (create): `run_case`.
- `src/python/reopt_pysam_vn/integration/offsite_generic.py` (create): `build_generic_combined_decision`.
- `src/python/reopt_pysam_vn/analysis/reporting.py` (create): shared report rendering.
- `src/python/reopt_pysam_vn/analysis/__main__.py` (modify): `run` + `report` subcommands; leave `onsite`/`offsite_dppa` intact.
- `src/python/reopt_pysam_vn/analysis/__init__.py` (modify): export `run_case`.
- `tests/python/analysis/test_case_runner.py`, `tests/python/analysis/test_offsite_generic.py`, `tests/python/analysis/test_reporting.py` (create): coverage per Test Specs.

**Function Signatures**
- `run_case(deal_config: DealConfig, *, extracted: Optional[dict] = None, results: Optional[dict] = None, run_developer: bool = True) -> Dict[str, Any]` — routes a deal through the correct engine and returns the result dict.
- `build_dppa_case_2_combined_decision(extracted: dict, *, run_developer: bool = True) -> dict` — the 7-block combined-decision dict for case 2.
- `build_generic_combined_decision(extracted: dict, *, run_developer: bool = True) -> dict` — 7-block dict via generic engines; `adder_sensitivity`/`regime_stress` empty in v1.
- `render_report(result: dict, *, fmt: str = "md") -> str` (in `reporting.py`) — human-readable summary string.

**Test Specs**
- `run_case(DealConfig(case="DPPA_SAMSUNG_TTC", mode="offsite_dppa"), extracted=<samsung fixture>)` → identical `to_dict()`/dict to today's `run_offsite_dppa` for Samsung (bit-exact; assert against `examples/samsung-ttc_combined-decision.example.json`).
- `run_case(DealConfig(case="DPPA_CASE_2", mode="offsite_dppa"), extracted=<case2 fixture>)` → non-empty `base_settlement` and `decision`; no exception.
- `run_case(DealConfig(case="BRAND_NEW_CASE", mode="offsite_dppa"), extracted=<minimal generic fixture>)` → succeeds via generic fallback; `result["quality"]["orchestrator"] == "generic"`.
- `run_case(DealConfig(case="X", mode="offsite_dppa"), extracted=None)` → raises `MissingInputsError`.
- `dppa_case_2` characterization: every `build_dppa_case_2_*` builder output equals its captured golden byte-for-byte.
- `render_report(<samsung result>, fmt="md")` → a string containing the deal title and the decision verdict.
- **Parity guard:** `pytest tests/python/analysis/test_samsung_ttc_parity.py tests/python/webapp/test_golden_parity.py -q` → 0 failed, bit-exact.

**Dependencies**
- PHASE-02 (type/parity gate in CI). ASM-001 (green baseline / red-test paydown done).

**Exit Criteria**
- [ ] `python -m reopt_pysam_vn.analysis run --config <deal>.json` works for Samsung, case 2, and a brand-new case (generic fallback).
- [ ] `dppa_case_2` is a registered orchestrator behind passing characterization tests.
- [ ] `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` → 0 failed; Samsung parity bit-exact.

**Phase Risks**
- **RISK-05-01:** The generic pipeline produces plausible-but-wrong economics for uncalibrated deals — mitigation: stamp `quality.orchestrator="generic"` into every generic result and leave `adder_sensitivity`/`regime_stress` visibly `{}` rather than fabricated.
- **RISK-05-02:** Re-expressing case 2 changes its output — mitigation: the characterization tests (TASK-05-02) fail loudly if so; the wrapper only *composes* existing builders, it does not recompute.

### PHASE-06 - Settlement Performance (Measure-First)

**Goal**
Determine whether the hourly (8760-step) settlement/strike-sweep kernel is a real latency problem for the interactive web app, and vectorize it with numpy/pandas ONLY if measurement proves it slow.

**Tasks**
- [ ] TASK-06-01: Add a micro-benchmark script `scripts/python/pysam/benchmark_settlement.py` that times a full offsite run (`run_case` on the Samsung or case-2 fixture) and the strike sweep in isolation using `time.perf_counter()`, printing per-stage wall times; run it via `.venv\Scripts\python.exe`.
- [ ] TASK-06-02: Record the numbers in `docs/perf/2026-07-14-settlement-benchmark.md`. Decision rule: if a single interactive offsite run's settlement + sweep exceeds ~2 seconds on the dev machine, proceed to TASK-06-03; otherwise stop and document that no optimization is warranted (honoring DEC-108 / the "no speculative improvement" rule).
- [ ] TASK-06-03 (conditional): Vectorize the hottest loop in `integration/settlement.py` using numpy (already a dependency), moving reusable array helpers into `common/time_series.py`. Keep the public function signatures identical and assert bit-exact-equal output against the pre-vectorization result (Samsung parity must stay green).

**File Changes**
- `scripts/python/pysam/benchmark_settlement.py` (create): timing harness.
- `docs/perf/2026-07-14-settlement-benchmark.md` (create): measured results + decision.
- `src/python/reopt_pysam_vn/integration/settlement.py` (modify, conditional): vectorized kernel, identical signatures.
- `src/python/reopt_pysam_vn/common/time_series.py` (modify, conditional): shared array helpers.

**Function Signatures**
- None — signatures are preserved; only internals change (if TASK-06-03 runs).

**Test Specs**
- Benchmark prints per-stage wall times and a total for a full offsite run.
- (Conditional) After vectorization: `pytest tests/python/analysis/test_samsung_ttc_parity.py -q` → 0 failed, bit-exact; a direct equality test asserts the vectorized `compute_hourly_settlement` output equals the previous scalar output on the case-2 fixture.

**Dependencies**
- PHASE-05 (`run_case` exists to benchmark the full path).

**Exit Criteria**
- [ ] Benchmark results committed under `docs/perf/`; a written keep-or-optimize decision recorded.
- [ ] If vectorized: Samsung parity bit-exact green and the equality test passes; if not: the doc states measured runtime is acceptable and no code changed.

**Phase Risks**
- **RISK-06-01:** Vectorization silently changes rounding vs the scalar loop — mitigation: the bit-exact parity gate + the direct equality test catch any divergence; if they diverge, keep the scalar path.

## Gotchas

- **Clear `PYTHONPATH` before pytest** (`$env:PYTHONPATH = ""`) — a stray global value shadows `.venv` and fails webapp tests with a `pydantic_core` import error.
- **Use `.venv\Scripts\python.exe`, never system Python** — PySAM 7.1.0 exists only in the repo venv (Python 3.12); system 3.14 silently falls back to synthetic solar profiles and changes numbers.
- **Samsung/TTC parity is bit-exact.** Two test files gate it (`test_samsung_ttc_parity.py`, `test_golden_parity.py`). Every phase near `settlement.py`, `dppa_samsung_ttc.py`, `offsite_dppa.py`, or the webapp analysis path must leave them green. "Close" is failing.
- **CON-004 boundary:** do NOT change `RunStorage` run-ordering (`list_runs` sort key / `_counter`) — that fix belongs to the 2026-07-11 plan; this plan only *adds* `provenance.json` and `prune`. Touching the counter risks a merge conflict and re-opens a fragility the other plan owns.
- **Never store the raw NREL key** — provenance records only `sha256(key)[:12]`. Grep new run files for the raw key before committing.
- **utf-8-sig on every new JSON reader** — plain `utf-8` crashes on BOM'd files that currently work.
- **Strike sweeps run in US cents/kWh; tariffs/strikes in VND/kWh; finance in USD** — never convert implicitly; label report/chart units from the data.
- **After any structural move (PHASE-04, PHASE-05), run the FULL Python suite**, not a subset — subset runs have missed integration breakage here before. Grep BARE names (`julia`, `REoptVietnam`), not path forms, before moving files.
- **CI yaml is bash; this plan's commands are PowerShell** — don't paste `$env:` syntax into `.github/workflows/ci.yml`.
- **Julia archive (PHASE-04) is gated by ASM-002/Q-101** — if anyone still solves locally in Julia, skip the phase; nothing else depends on it.
- **In numeric comparators, guard `bool` before `int`** (Python `bool ⊂ int`) — relevant if PHASE-05/06 touch a parity comparator.

## Verification Strategy

- **TEST-001 (PHASE-01):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp -q` → 0 failed (provenance, error-taxonomy, prune cases included).
- **TEST-002 (PHASE-02):** `.venv\Scripts\python.exe -m mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` → exit 0.
- **TEST-003 (PHASE-02):** `.venv\Scripts\python.exe -c "import importlib.resources, reopt_pysam_vn; print((importlib.resources.files('reopt_pysam_vn')/'py.typed').is_file())"` → `True`.
- **TEST-004 (PHASE-03):** `$env:NREL_DEVELOPER_API_KEY = ""; $env:REOPT_PYSAM_VN_OFFLINE = "1"; $env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp/test_jobs.py -q` → 0 failed (offline onsite run reaches `done` with no key/network).
- **TEST-005 (PHASE-04):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` → 0 failed after the Julia move.
- **TEST-006 (PHASE-04):** `grep -rn "src/julia\|scripts/julia" --include="*.md" --include="*.py" --include="*.ps1" .` → no matches outside `legacy/julia/`.
- **TEST-007 (PHASE-05):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/analysis/test_samsung_ttc_parity.py tests/python/webapp/test_golden_parity.py tests/python/integration/test_dppa_case_2_characterization.py -q` → 0 failed (parity bit-exact; case-2 characterized).
- **TEST-008 (PHASE-05):** `$env:PYTHONPATH = "src/python"; .venv\Scripts\python.exe -m reopt_pysam_vn.analysis run --config examples/samsung-ttc_combined-decision.example.json` (or a deal JSON) — exits 0 and emits a result with `quality.orchestrator` present; a brand-new case id routes through the generic fallback.
- **TEST-009 (PHASE-06):** `.venv\Scripts\python.exe scripts/python/pysam/benchmark_settlement.py` → prints per-stage wall times; `docs/perf/2026-07-14-settlement-benchmark.md` records the keep-or-optimize decision.
- **TEST-010 (final regression):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` → 0 failed across the whole suite.
- **MANUAL-001 (PHASE-01):** With the app running, force an errored run (submit an offsite deal with no `extracted`) → the run page shows a friendly `message` + `hint` + `error_code`, and the server log has the full traceback with the `run_id`.
- **MANUAL-002 (PHASE-01):** `.venv\Scripts\python.exe -m reopt_pysam_vn.webapp.prune --days 3650` (dry run) → lists nothing to delete on a fresh store; inspect that `provenance.json` exists in a completed run dir and contains no raw key.
- **OBS-001:** After a solve, one structured `INFO` line appears on stdout per run (`configure_logging` format) and `provenance.json` records `solver`, `cache_hit`, `wall_time_seconds`, and `policy_data_versions`.

## Risks and Alternatives

- **RISK-001:** Starting PHASE-05 before the 2026-07-11 red-test paydown lands means the parity baseline may itself be red, masking a real refactor regression — mitigated by ASM-001 (green baseline required; TASK-05-01 records it) and by strict sequencing (PHASE-05 after PHASE-02's CI gate).
- **RISK-002:** The ops/type/offline phases (01–03) touch `webapp/` files the 2026-07-11 plan's PHASE-03 (input allowlist) and DEC-010 (run ordering) also touch — mitigated by CON-004 (this plan does not change the allowlist or the sort/counter logic; it only adds new functions/files), so the two plans compose without conflict.
- **RISK-003:** CI green becomes false comfort because `network`-marked tests never run there — mitigated by keeping `.\tests\run_all_tests.ps1` + TEST-010 as the documented pre-release full gate, and by PHASE-03's offline mode letting the onsite pipeline run in CI without the marker.
- **ALT-001:** Rewrite `dppa_samsung_ttc.py`/`dppa_case_2.py` into a clean framework from scratch — rejected: `lessons.md` documents this exact failure mode; the registry + characterization-test + generic-fallback path adds the config runner without recomputing gated output.
- **ALT-002:** Delete the Julia tree outright — rejected in favor of archive-in-place (DEC-104): it may still be the best offline solver; keep the code, drop the pretense.
- **ALT-003:** Build a full metrics/tracing backend for observability — rejected as over-engineering for a single-user localhost tool; structured logs + `provenance.json` are the right altitude.
- **ALT-004:** Vectorize settlement up front for "obvious" speed — rejected per DEC-108: measure first (PHASE-06); premature optimization violates the repo's no-speculative-change rule and risks the bit-exact gate.

## Suggested Next Step

Execute **PHASE-01** (web-app operational readiness) — it is dependency-free, has no analytics risk, and delivers the biggest day-2 operator win. Run PHASE-02 and PHASE-03 alongside/after it (also dependency-free). Resolve Q-101 before PHASE-04. Do PHASE-05 only once a green baseline + parity gate exist (ASM-001), and PHASE-06 last, measuring before changing anything. Each phase's exit criteria are independently verifiable before the next begins.
