---
status: "complete — all 6 phases implemented in commit 62b81f3 (plus follow-ups ea4020d/34ab245/b6b5885); verified in-tree and by a green portable suite run: 758 passed, 21 deselected, 2 xfailed"
---

# Plan: Last Mile and Physical Truth

## Objective

Make the generic Vietnam DPPA analysis path reachable from the product's own web
form, correct three measured physical-modelling defects in the PVWatts generation
layer, split the oversized offsite result payload, unify load ingestion on the
mature loader, and convert the repo's largest block of CI-excluded numeric tests
into CI-enforced ones. Today a user who fills in the new-deal form and uploads an
hourly load CSV for an unregistered deal case gets `MISSING_INPUTS`, and every
solar number the toolkit has ever produced was computed on a single cached solar
resource file located ~350 km from the modelled sites, using a single-axis-tracker
array configuration that nobody chose.

## Context Snapshot

- **Current state:**
  - `reopt_pysam_vn.analysis.run_offsite_dppa` resolves an orchestrator from a
    registry keyed by `DealConfig.case`, with `analysis/orchestrators/generic_vn_dppa.py`
    installed as the fallback for any unregistered case. Called directly with a
    hand-built `extracted` dict it returns a complete `directional`-flagged result.
  - `POST /api/deals` (the guided web form) writes the uploaded 8760-hour load
    series to `deal_config["load"]["loads_kw"]`. The offsite path reads
    `extracted["loads_kw"]`. Nothing bridges the two, so
    `webapp/service.run_analysis` raises `MissingInputsError` and the run ends in
    `state: error`, `error_code: MISSING_INPUTS`.
  - `data/interim/pysam_resources/` contains exactly one usable solar resource
    file, `ninhsim_himawari_2019_60min.csv` at 12.525729 °N / 109.020034 °E
    (Ninh Thuan). It is tracked in git (1.2 MB) and therefore present in CI.
    `pysam/pvwatts_battery.DEFAULT_SOLAR_RESOURCE_FILE` points at it, and three
    call sites fall back to it silently.
  - `analysis/orchestrators/generic_vn_dppa._try_pvwatts_generation` verifies that
    `extracted["site"]["latitude"]`/`["longitude"]` are present and then never uses
    them; it reports `quality.solar_profile_source == "pvwatts"` regardless.
  - Neither PVWatts call site sets `array_type` or `tilt`. `PySAM.Pvwattsv8.default("PVWattsSingleOwner")`
    ships `array_type = 2.0` (1-axis backtracked tracking) and `tilt = 0.0`.
  - `analysis/orchestrators/generic_vn_dppa._calibrate_to_target` redistributes
    AC-clipping deficit in proportion to `cap_kw - value`, which is maximal at
    zero-generation hours, so it injects solar output into the middle of the night.
  - A generic offsite `result.json` is ~3.79 MB, of which 99.8 % is
    `base_settlement.hourly_ledger` (8,760 rows × 16 keys). The bespoke Samsung
    result for the same type is 11.8 KB. `GET /api/runs/{run_id}` returns the whole
    thing and `results_view.render_standalone_report_html` inlines it into the
    downloadable HTML.
  - `webapp/uploads.py` (47 lines) reimplements load parsing: first column only,
    exactly 8760 rows, hard error on any gap. `ingestion/loader.py` (342 lines)
    already does header matching, multi-sheet XLSX scanning, JSON input,
    missing-value interpolation, negative clipping, and 15-min/30-min/monthly
    resampling.
  - CI runs `pytest tests/python` with a six-marker exclusion filter. 46 of 704
    collected tests are deselected; 35 of those carry `requires_artifacts`, and
    they include the 13 settlement-regression tests and the 12 Factory-A validation
    tests — the numeric core.
  - CI has a skip budget (`REOPT_PYSAM_VN_MAX_SKIPS`) but no deselect budget and no
    `--cov-fail-under`. Coverage is 82 % and fell 3 points in the last sprint.

- **Desired state:**
  - Submitting the guided form with only an hourly load file, for a deal case that
    has no registered orchestrator, produces a completed run
    (`state: done`, `quality.orchestrator == "generic_vn_dppa"`).
  - Every PVWatts-derived result names the resource file it used, that file's
    coordinates, and the great-circle distance to the modelled site, and warns
    above 100 km. Array type and tilt are set explicitly at both call sites.
  - `_calibrate_to_target` never places energy in an hour whose input shape is
    zero, and reports infeasible annual targets instead of manufacturing energy.
  - `tests/python/integration/test_capacity_factor_benchmark.py` runs in CI,
    network-free, un-`xfail`ed, and fails if the fixed-tilt capacity factor leaves
    the 14–20 % band.
  - The offsite result stored and served by the webapp is summary-only; the hourly
    ledger is a separate CSV download.
  - The web upload path routes through `ingestion/loader.py` and surfaces its
    cleaning summary on the run page.
  - CI enforces a deselect budget, a coverage floor, and at least the 13
    settlement-regression tests plus the 12 Factory-A tests.

- **Key repo surfaces:**
  - `src/python/reopt_pysam_vn/analysis/` — `offsite_dppa.py`, `onsite.py`,
    `types.py`, `validation.py`, `__main__.py`, `orchestrators/generic_vn_dppa.py`
  - `src/python/reopt_pysam_vn/webapp/` — `service.py`, `routes/api.py`,
    `routes/pages.py`, `uploads.py`, `storage.py`, `results_view.py`, `jobs.py`,
    `templates/run.html`
  - `src/python/reopt_pysam_vn/reopt/preprocess.py` — `build_vietnam_tariff`,
    `_build_8760_rates`, `_build_hourly_rates`, `load_vietnam_data`, `VNData`
  - `src/python/reopt_pysam_vn/pysam/pvwatts_battery.py` — resource resolution
  - `src/python/reopt_pysam_vn/integration/` — `settlement.py`,
    `market_reference.py`, `dppa_samsung_ttc.py`
  - `src/python/reopt_pysam_vn/ingestion/loader.py` — `ingest_factory_load`
  - `data/schemas/deal_config.schema.json`, `data/schemas/extracted_inputs.schema.json`
  - `.github/workflows/ci.yml`, `pyproject.toml`, `tests/conftest.py`

- **Out of scope:**
  - Rotating the NREL developer API key committed in historical commits
    `3911032` / `b14bc0b` (an out-of-band human action).
  - Consolidating the nine hand-rolled HTML report builders under `scripts/python/`
    onto the shared templates in `assets/`.
  - Any webapp-to-PowerPoint deck export.
  - Downloading new solar resource files over the network, or adding regional TMY
    files beyond the one already tracked.
  - Filling `hourly_shape_24` in `data/vietnam/vn_market_prices_2026.json` with a
    real intraday market-price shape.
  - Reviving the Julia layer under `legacy/julia/`.
  - Multi-tenant auth, cloud hosting, or containerisation.
  - Changing any numeric output of `integration/dppa_samsung_ttc.py`.

## Environment & Conventions

- **Stack:** Python. `requires-python = ">=3.10"`; CI matrix is 3.10 and 3.12.
  The repository `.venv/` is Python 3.12 and is the interpreter that has
  `nrel-pysam` installed on a typical developer machine — a system Python 3.14
  has no PySAM wheel. Runtime dependencies: `matplotlib>=3.8`, `nrel-pysam==7.1.0`,
  `numpy-financial>=1.0`, `openpyxl>=3.1`, `pandas>=2.0`, `requests>=2.31`.
  Webapp extra: `fastapi>=0.110`, `uvicorn[standard]>=0.29`, `jinja2>=3.1`,
  `python-multipart>=0.0.9`, `httpx>=0.27`. Dev extra pins exactly:
  `ruff==0.16.1`, `mypy==2.3.0`, `pytest==8.4.2`, `pytest-cov==7.1.0`.
  Build backend is setuptools; the package root is `src/python`.

- **Setup:**
  ```
  python -m pip install --upgrade pip
  python -m pip install -e ".[webapp,dev]" -c constraints-ci.txt
  ```
  Never install a gate tool (`ruff`, `mypy`, `pytest`, `pytest-cov`) unpinned.
  `constraints-ci.txt` pins the whole transitive set; edit it deliberately, and
  when editing it from PowerShell use a single-quoted here-string (`@'…'@`) —
  a double-quoted here-string mangles backticks and produces a file `pip` cannot
  parse.

- **Build / Run:** There is no build step. To run the localhost web UI:
  ```
  PYTHONPATH=src/python python -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000
  ```
  Then open `http://127.0.0.1:8000/deals/new`.

- **Test:** full portable suite, exactly as CI runs it:
  ```
  PYTHONPATH="" REOPT_PYSAM_VN_MAX_SKIPS=0 python -m pytest tests/python \
    -m "not network and not requires_artifacts and not golden_machine and not requires_julia and not requires_nrel_key and not requires_pysam_resource" \
    -rs -q --cov=reopt_pysam_vn --cov-report=term-missing
  ```
  Baseline before this plan: `655 passed, 46 deselected, 3 xfailed`, coverage 82 %.

  Single test:
  ```
  PYTHONPATH="" python -m pytest tests/python/analysis/test_generic_vn_dppa.py::test_annual_summary_numbers_are_exact -q
  ```

  Lint and type gates, run exactly as CI does:
  ```
  ruff check src scripts tests
  mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp
  ```
  Expected: `All checks passed!` and `Success: no issues found in 24 source files`
  (the file count rises as this plan adds modules).

- **Conventions & traps:**
  - **`PYTHONPATH` must be cleared for pytest.** An unrelated global `PYTHONPATH`
    can shadow the repo environment and produce
    `ModuleNotFoundError: pydantic_core._pydantic_core` in the webapp tests.
    `pyproject.toml` already sets `pythonpath = ["src/python"]` for pytest; set
    `PYTHONPATH=src/python` only when invoking `uvicorn` or a script directly.
  - **Units.** Load and generation series are **kW**, hourly, length exactly
    **8760** (index 0 = 1 Jan 00:00, no leap day). Ledger rows are in **kWh**.
    Annual summaries are in **MWh** and **VND**. `contract.annual_solar_gwh` is
    **GWh**. Tariff and settlement prices are **VND per kWh**; REopt scenario
    inputs are **USD per kWh**. `fmp_vnd_per_mwh` / `cfmp_vnd_per_mwh` in the
    extracted-inputs contract are **VND per MWh** and are divided by 1,000 on read.
  - **Currency.** Never write a bare VND/USD literal. Resolve it via
    `reopt_pysam_vn.common.assumptions.exchange_rate(vn)`, which reads
    `data/vietnam/vn_deal_defaults_2026.json`. The two documented exceptions are
    `integration/dppa_samsung_ttc.py` (deliberately pinned) and the Saigon18
    25,450 VND/USD contract basis.
  - **Markers are strict.** `addopts = ["--strict-markers"]`. Any new marker must
    be declared in `pyproject.toml`'s `[tool.pytest.ini_options] markers` list with
    a rationale string, or collection fails.
  - **Lint.** `ruff` with `line-length = 120`, `target-version = "py310"`,
    `ignore = ["E402", "ISC004"]`, `extend-exclude = [".venv", "legacy", "artifacts", "present"]`.
    E402 is intentional repo-wide (scripts bootstrap `sys.path` before importing).
  - **Types.** `mypy` runs only over `reopt_pysam_vn.analysis` and
    `reopt_pysam_vn.webapp`, and those two packages have `disallow_untyped_defs = true`.
    Every new function in those packages needs full annotations.
    `integration`, `reopt`, `pysam`, `ingestion`, and `common` are not type-checked.
  - **Public API boundary.** `analysis` and `webapp` are the supported surfaces.
    `integration`, `reopt`, and `pysam` are internal engines. New consumer-facing
    code depends on `analysis`, never on those internals.
  - **JSON reads use `encoding="utf-8-sig"`** throughout, to tolerate a UTF-8 BOM
    from Windows editors.
  - **Generated output is git-ignored.** `artifacts/`, `reports/*.html`,
    `present/`, `reports/decks/`, `scenarios/generated/`. Tracked deliverables are
    `reports/*.md`, `examples/`, and `tests/baselines/`.
  - **Windows-first repo.** Prefer `pathlib`; do not assume a POSIX shell inside
    Python code.
  - **CI green is the completion signal.** Verify with `gh run list --limit 3` and
    confirm both matrix legs (`test (3.10)` and `test (3.12)`) report `success`.
    A run that finishes far under ~1m30s did not reach the test step.

- **Repo map:**
  ```
  data/vietnam/          Versioned policy data behind manifest.json (tariff, tech_costs,
                         financials, emissions, export_rules, regimes, deal_defaults,
                         market_prices). Each file is a {_meta, data} envelope.
  data/schemas/          deal_config.schema.json, extracted_inputs.schema.json
  data/interim/          Per-deal extracted-input JSON + pysam_resources/ (tracked TMY)
  src/python/reopt_pysam_vn/
    analysis/            Public API: DealConfig, run_onsite, run_offsite_dppa, CLI,
                         orchestrators/ (dppa_case_1, generic_vn_dppa)
    common/              assumptions.py (canonical resolver) + three unused stubs
    ingestion/           loader.py, synthesize.py, metadata.py
    integration/         settlement.py, market_reference.py, bespoke dppa_case_* modules
    pysam/               pvwatts_battery.py, single_owner.py, cashflow.py
    reopt/               preprocess.py (Vietnam defaults, tariff builder), regime_*
    webapp/              FastAPI localhost UI: service, routes/, storage, uploads,
                         results_view, jobs, templates/, static/
  scripts/python/{reopt,pysam,integration}/   Workflow + report-generation scripts
  tests/python/          Pytest suite (analysis, webapp, integration, reopt, pysam,
                         ingestion, common) + test_repo_invariants.py
  tests/conftest.py      CI skip budget
  ```

## Research Inputs

- From `research/2026-08-19-reopt-pysam-last-mile-and-physical-truth-brainstorm.md`:
  - Submitting `POST /api/deals` with `case=MEKONG_NEW_DEAL`, `mode=offsite_dppa`,
    site coordinates, contract terms and an 8760-row `load.csv` returns HTTP 202 and
    then resolves to `state: error`, `error_code: MISSING_INPUTS`. The generic
    orchestrator is registered and functional but unreachable through the UI.
  - Every ingredient of the `extracted` contract already has a deal-agnostic
    producer: `deal_config["load"]["loads_kw"]` and `deal_config["site"]` are
    already populated by the form; the 8760 EVN TOU series comes from
    `reopt/preprocess`; `weighted_evn_price_vnd_per_kwh` comes from
    `integration/settlement.compute_buyer_benchmark`; `wholesale_rate_vnd_per_kwh`
    comes from `common/assumptions.market_wholesale_reference_vnd_per_kwh`.
  - Measured PVWatts yield on the tracked Ninh Thuan resource file, 1 MWp DC,
    `dc_ac_ratio=1.2`, `losses=14`: **1,888.3 kWh/kWp** with the inherited
    `array_type=2` (1-axis tracking) default versus **1,527.9 kWh/kWp** for a fixed
    open rack at tilt = latitude — the production path is **+23.6 %** on identical
    irradiance.
  - Measured 50 MW capacity factors on the same tracked file, computed as
    `annual_energy / (system_capacity_kw × 8760)`: fixed open rack at tilt =
    latitude gives **17.44 %** (inside the repo's own 14–20 % benchmark band);
    1-axis tracking gives **21.56 %** (outside it). The repo's only physical
    plausibility test asserts that band and has been `xfail`ed since 2026-07-04.
  - Measured night-hour injection from `_calibrate_to_target`, hours 23:00–03:00:
    a 2.0 MWac plant with an 8.0 GWh annual target places **457.0 MWh (5.7 %)** of
    annual energy at night with a 250 kW peak; a 1.0 MWac plant with a 6.0 GWh
    target places **834.5 MWh (13.9 %)** with a 457 kW peak.
  - A generic offsite `result.json` measures **3,790,374 bytes**, of which
    **3,783,213 bytes** is `base_settlement.hourly_ledger`. The comparable bespoke
    artifact `examples/samsung-ttc_combined-decision.example.json` is 11,794 bytes.
  - CI deselects 46 of 704 tests: `requires_artifacts` 35, `golden_machine` 4,
    `network` 4, `requires_nrel_key` 4, `requires_julia` 2,
    `requires_pysam_resource` 1. The `requires_artifacts` bucket is dominated by
    `tests/python/integration/test_settlement_regression.py` (13) and
    `tests/python/analysis/test_factory_a_validation.py` (12).
  - Carried hygiene items, all still open: a bare `assert` at
    `src/python/reopt_pysam_vn/webapp/jobs.py:149`; three plans marked
    `status: complete` still in `plans/active/`; three `ceba_*.md` files at the
    repository root; three zero-coverage stub modules in
    `src/python/reopt_pysam_vn/common/`.
  - The prior pass's note that Samsung/TTC falls back to a *synthetic* profile in
    CI is incorrect: `data/interim/pysam_resources/ninhsim_himawari_2019_60min.csv`
    is tracked in git and `nrel-pysam` is a hard dependency, so CI resolves the
    Ninh Thuan file, not a synthetic shape.

## Assumptions and Constraints

- **ASM-001:** The repository contains exactly one usable solar resource file and
  this plan does not add more. — **BINDING DEFAULT:** all PVWatts paths continue to
  use `data/interim/pysam_resources/ninhsim_himawari_2019_60min.csv`; the work is to
  *disclose* the substitution in the result's `quality` block, not to eliminate it.
- **ASM-002:** The coordinates of that resource file are not recorded in machine-
  readable form anywhere in `src/`. — **BINDING DEFAULT:** hard-code a module-level
  catalogue in `src/python/reopt_pysam_vn/pysam/pvwatts_battery.py` mapping the file
  name to `(12.525729252783036, 109.02003383567742)`, taken from the sibling file
  name `nsrdb_12.525729252783036_109.02003383567742_himawari_60_2019.csv`.
- **ASM-003:** No threshold is defined for "the resource is too far from the site".
  — **BINDING DEFAULT:** 100 km great-circle. Below it, no warning. At or above it,
  append a warning string to `quality.warnings` and set
  `quality.solar_profile_source` to `"pvwatts_fallback_resource"` instead of
  `"pvwatts"`.
- **ASM-004:** `DealConfig` has no field describing array mounting. —
  **BINDING DEFAULT:** add an optional `plant.mounting` string with the enum
  `["fixed_open_rack", "fixed_roof", "single_axis_tracking"]` to
  `data/schemas/deal_config.schema.json`, defaulting to `"fixed_open_rack"` when
  absent. Map to PVWatts `array_type` 0, 1, 2 respectively; set `tilt` to the site
  latitude for the two fixed options and to `0.0` for tracking.
- **ASM-005:** Changing the array configuration would move every number
  `integration/dppa_samsung_ttc.py` produces. — **BINDING DEFAULT:** pin
  `integration/dppa_samsung_ttc.py` explicitly to `array_type = 2` and `tilt = 0.0`
  — the values it currently inherits implicitly — so its output is bit-identical
  before and after this plan. Record the pin in an inline comment naming this plan.
  The new fixed-tilt default applies only to the generic orchestrator.
- **ASM-006:** The guided form does not collect `site.customer_type` or
  `site.voltage_level` on every submission. — **BINDING DEFAULT:** the extracted
  assembler falls back to `customer_type = "industrial"` and
  `voltage_level = "medium_voltage_22kv_to_110kv"` (the value carried by two of the
  three tracked deal files) and records both in the assembled
  `extracted["extraction_meta"]` block so the choice is visible in the output.
- **ASM-007:** The tariff year for the assembled 8760 TOU series is not specified
  by the deal config. — **BINDING DEFAULT:** use `2024`, a non-leap year whose
  1 January is a Monday-adjacent weekday consistent with
  `_build_8760_rates(weekday_rates, sunday_rates, year)`; record it as
  `extracted["data_year"]`.
- **ASM-008:** No file format is specified for the extracted hourly ledger. —
  **BINDING DEFAULT:** RFC-4180 CSV written with `csv.DictWriter`, one header row,
  column order exactly as the ledger dict key order, floats written with
  `repr()`-equivalent full precision (Python's default `str(float)`).
- **ASM-009:** The Factory-A validation tests read stored PySAM result JSON files
  rather than re-executing PySAM. — **BINDING DEFAULT:** track the four existing
  12 KB result files as fixtures and re-label the test module in its docstring as a
  *recorded-output conformance* gate, stating explicitly that it no longer proves
  PySAM was re-run. Do not claim it re-validates the model.
- **ASM-010:** No target is stated for the coverage floor. — **BINDING DEFAULT:**
  set `--cov-fail-under=82`, matching the measured current value. Raise it only
  when a phase's own exit criteria demonstrate a higher figure.
- **ASM-011:** No target is stated for the deselect budget. — **BINDING DEFAULT:**
  set `REOPT_PYSAM_VN_MAX_DESELECTED=46` at the start of PHASE-01 and lower it in
  PHASE-06 to whatever the suite actually reports after the fixtures land.
- **CON-001:** `integration/dppa_samsung_ttc.py` must produce bit-identical output
  before and after this plan. `examples/samsung-ttc_combined-decision.example.json`
  must not be edited.
- **CON-002:** The webapp must never fork analytics logic. It calls `run_onsite`
  and `run_offsite_dppa` from `reopt_pysam_vn.analysis` unchanged.
  `tests/python/webapp/test_golden_parity.py::test_samsung_ttc_web_api_matches_direct_library_call_bit_exact`
  enforces this and must keep passing in CI.
- **CON-003:** `integration/settlement.ContractParams` fields may not be renamed and
  no existing field may be made required. New consumers configure it through
  `ContractParams.from_regime(regime_id, **overrides)`.
- **CON-004:** No test added or modified by this plan may make a network call. The
  webapp test suite blocks live NREL calls through an autouse fixture in
  `tests/python/webapp/conftest.py`; new PVWatts tests must read the tracked
  resource file, never fetch.
- **CON-005:** The CI skip budget stays at `0`. No phase may introduce a runtime
  `pytest.skip()` guard; environment dependence is expressed with a registered
  marker.
- **DEC-001:** Any unregistered `DealConfig.case` routes to the generic fallback
  orchestrator and returns a result flagged `quality.basis == "directional"` and
  `quality.orchestrator == "generic_vn_dppa"`. This plan preserves that behaviour.
- **DEC-002:** The generic path stays permissive rather than refusing work. When a
  substituted solar resource, a defaulted voltage level, or an infeasible annual
  target is detected, the result is still returned — flagged in `quality.warnings`.
- **DEC-003:** The hourly ledger is kept, not truncated. It is the audit trail for a
  settlement and is moved to its own artifact rather than deleted.
- **DEC-004:** The extracted-inputs assembler lives in `reopt_pysam_vn.analysis`,
  never in `webapp`, so both the CLI and the web layer share one implementation.
- **DEC-005:** Errors raised by the assembler use the existing
  `reopt_pysam_vn.analysis.offsite_dppa.OrchestratorInputError`, which
  `webapp/service.run_analysis` already catches and re-raises as
  `MissingInputsError`, which `routes/api.py` already maps to a clean run-level
  error rather than an HTTP 500.

## Specification

### S1 — Great-circle distance between a site and a solar resource

For site latitude `φ₁` and longitude `λ₁`, resource latitude `φ₂` and longitude
`λ₂`, all in decimal degrees:

```
Δφ = radians(φ₂ − φ₁)
Δλ = radians(λ₂ − λ₁)
a  = sin²(Δφ / 2) + cos(radians(φ₁)) · cos(radians(φ₂)) · sin²(Δλ / 2)
d  = 2 · R · atan2(√a, √(1 − a))
```

- `φ₁`, `λ₁` — the modelled site's latitude and longitude in decimal degrees,
  read from `extracted["site"]["latitude"]` and `["longitude"]`.
- `φ₂`, `λ₂` — the solar resource file's own latitude and longitude in decimal
  degrees, from the catalogue described in ASM-002.
- `R` — mean Earth radius, fixed at **6371.0 km**.
- `d` — separation in **kilometres**, rounded to one decimal place for reporting.

Worked check the executor can use as a unit test: site `(10.88, 106.28)` against
resource `(12.525729252783036, 109.02003383567742)` gives `d ≈ 337.0 km` (assert
`330.0 <= d <= 345.0` so a different rounding convention does not break the test).

### S2 — Corrected annual-target calibration with AC clipping

Inputs: a non-negative shape `s[h]` for `h ∈ [0, 8760)`, an annual energy target
`E` in kWh, and an optional AC cap `C` in kW.

1. If `C is None`: return `[s[h] · E / Σs]` for all `h` (or all zeros when
   `Σs == 0`). Stop.
2. Define the **daylight set** `D = { h : s[h] > 0 }`. If `D` is empty, return
   8760 zeros and append the warning `"generation shape is entirely zero"`. Stop.
3. **Feasibility bound:** `E_max = C · |D|` kWh, where `|D|` is the count of
   daylight hours. If `E > E_max`, the target cannot be met at this AC cap:
   set `out[h] = C` for `h ∈ D` and `0` otherwise, append the warning
   `"annual target {E/1e6:.3f} GWh is infeasible at {C/1000:.3f} MWac (max {E_max/1e6:.3f} GWh); series clipped at the AC cap"`,
   and stop.
4. `scale = E / Σs`; `out[h] = min(s[h] · scale, C)` for all `h`.
5. Iterate at most **50** times:
   - `deficit = E − Σout`. If `deficit ≤ 1.0` kWh, stop.
   - `headroom[h] = C − out[h]` for `h ∈ D`, and `0` for `h ∉ D`.
   - `H = Σ headroom`. If `H ≤ 1e-9`, stop.
   - For `h ∈ D`: `out[h] = min(out[h] + deficit · headroom[h] / H, C)`.
6. Return `out`.

The single change of substance versus the current implementation is step 5's
restriction of `headroom` to `D`, plus the loop and the explicit infeasibility
branch. Hours outside `D` are never written to, so no energy can appear at night.

### S3 — The extracted-inputs assembler

`build_extracted_inputs(deal_config, vn=None)` produces a dict satisfying
`data/schemas/extracted_inputs.schema.json`, in this exact order:

1. `loads_kw` — from `deal_config.load["loads_kw"]`. Must be a list of exactly
   8760 numbers, each `>= 0`. Otherwise raise `OrchestratorInputError` with the
   message
   `"generic offsite analysis needs deal_config.load['loads_kw'] with exactly 8760 non-negative values; got <n>"`.
2. `site` — a shallow copy of `deal_config.site`, with `customer_type` and
   `voltage_level` filled from ASM-006 when absent.
3. `project` — `deal_config.title` if non-empty, else `deal_config.case`.
4. `data_year` — the tariff year, `2024` per ASM-007.
5. `evn_tariff.tou_energy_rates_vnd_per_kwh` — from
   `build_evn_tou_series_vnd_per_kwh(...)` (PHASE-02), length exactly 8760,
   units **VND per kWh**.
6. `benchmark.annual_load_kwh` — `sum(loads_kw)`.
7. `benchmark.weighted_evn_price_vnd_per_kwh` —
   `compute_buyer_benchmark(loads_kw, tariff)["blended_rate_vnd_kwh"]`, i.e.
   `Σ(load[h] · tariff[h]) / Σload[h]`, load-weighted, **not** a simple mean.
8. `benchmark.wholesale_rate_vnd_per_kwh` —
   `market_wholesale_reference_vnd_per_kwh(vn)`, currently 671.0 VND/kWh from
   `data/vietnam/vn_market_prices_2026.json`.
9. `benchmark.exchange_rate_vnd_per_usd` — `exchange_rate(vn)`.
10. `benchmark.peak_demand_kw` — `max(loads_kw)`.
11. `extraction_meta` — `{"assembled_by": "build_extracted_inputs", "regime_id": <regime>, "tariff_year": 2024, "customer_type": <resolved>, "voltage_level": <resolved>, "defaulted_fields": [<names of any field filled from ASM-006>]}`.

`generation_kw` is deliberately **not** set: the generic orchestrator resolves
generation itself. The regime id is `deal_config.contract.get("regime_id", "decision_963_2026_current")`.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Ratchet the CI gate and clear carried hygiene debt before anything moves | None | Deselect budget, coverage floor, six hygiene fixes |
| PHASE-02 | Make the generic deal path reachable from the web form and the CLI | PHASE-01 | `analysis/extracted.py`, VND TOU series helper, `--derive-extracted`, end-to-end webapp test |
| PHASE-03 | Correct the physical model: resource provenance, array config, clipping | PHASE-01 | Resource catalogue + distance warning, explicit `array_type`/`tilt`, S2 calibration, un-`xfail`ed capacity-factor gate |
| PHASE-04 | Split the offsite result into a summary plus a separate hourly ledger | PHASE-02 | `ledger.csv` storage + download route, slimmed `result.json` |
| PHASE-05 | Unify load ingestion on `ingestion/loader.py` | PHASE-02 | Rewritten `webapp/uploads.py`, cleaning summary on the run page |
| PHASE-06 | Bring the excluded numeric-regression tests into CI | PHASE-01, PHASE-03 | Reduced regression fixtures, 25 tests un-marked, lowered deselect budget |

## Detailed Phases

### PHASE-01 - Gate Ratchets and Carried Hygiene

**Goal**
Put the two missing CI ratchets in place *before* any behaviour changes, so every
later phase is measured against a floor rather than a moving target, and clear the
six small carried items so they stop being re-discovered.

**Tasks**
- [x] TASK-01-01: Extend `tests/conftest.py` with a deselect budget mirroring the
  existing skip budget. Count deselected tests in `pytest_collection_modifyitems`
  and fail the session in `pytest_sessionfinish` when the count exceeds
  `REOPT_PYSAM_VN_MAX_DESELECTED`. When the variable is unset, do not enforce.
- [x] TASK-01-02: Add `REOPT_PYSAM_VN_MAX_DESELECTED: "46"` to the `env:` block of
  the test step in `.github/workflows/ci.yml`, alongside the existing
  `REOPT_PYSAM_VN_MAX_SKIPS: "0"`.
- [x] TASK-01-03: Add `--cov-fail-under=82` to the pytest invocation in
  `.github/workflows/ci.yml`.
- [x] TASK-01-04: Replace the bare `assert` at
  `src/python/reopt_pysam_vn/webapp/jobs.py:149` with an explicit
  `raise RuntimeError(...)` carrying the same message, so it survives `python -O`.
- [x] TASK-01-05: Delete the three unused stub modules
  `src/python/reopt_pysam_vn/common/currency.py`,
  `src/python/reopt_pysam_vn/common/time_series.py`, and
  `src/python/reopt_pysam_vn/common/validation.py`. First confirm zero importers
  with `grep -rn "common.currency\|common.time_series\|common.validation\|identity_currency\|constant_series\|require_positive" src scripts tests` and
  leave `src/python/reopt_pysam_vn/common/__init__.py` and `assumptions.py` untouched.
- [x] TASK-01-06: `git mv` the three completed plans
  `plans/active/2026-05-22-gap01-factory-ingestion-plan.md`,
  `plans/active/2026-05-22-gap02-procurement-comparison-plan.md`, and
  `plans/active/2026-05-22-gap04-generalized-settlement-plan.md` into
  `plans/archive/`.
- [x] TASK-01-07: `git mv` `ceba_delta_report.md`, `ceba_repo_test_results.md`, and
  `ceba_slide_review_report.md` from the repository root into `reports/`.
- [x] TASK-01-08: Correct the `generation_kw` description in
  `data/schemas/extracted_inputs.schema.json` — it currently says the generic
  orchestrator uses it "when a PVWatts resource is unavailable", whereas the code
  prefers it *first*. Change the text to state that an explicit `generation_kw`
  series takes precedence over the PVWatts and synthetic paths.

**File Changes**
- `tests/conftest.py` (modify): add a module-level `_deselected_count`, a
  `pytest_collection_modifyitems(session, config, items)` hook that records
  `len(config.hook.pytest_deselected)`-equivalent state — implement it by adding a
  `pytest_deselected(items)` hook that accumulates `len(items)` — and extend
  `pytest_sessionfinish` to read `REOPT_PYSAM_VN_MAX_DESELECTED`, print
  `DESELECT BUDGET EXCEEDED: {n} deselected, budget {b}` to stderr and set
  `session.exitstatus = 1` when exceeded. Leave the existing skip-budget logic and
  its `wasxfail` comment exactly as they are.
- `.github/workflows/ci.yml` (modify): in the `Test (portable suite)` step, append
  `--cov-fail-under=82` to the pytest command and add
  `REOPT_PYSAM_VN_MAX_DESELECTED: "46"` under `env:`. Do not change the marker
  filter, `-rs`, or `REOPT_PYSAM_VN_MAX_SKIPS`.
- `src/python/reopt_pysam_vn/webapp/jobs.py` (modify): line 149 only — swap the
  bare `assert` for an explicit raise. Leave the surrounding cache logic alone.
- `src/python/reopt_pysam_vn/common/currency.py` (delete)
- `src/python/reopt_pysam_vn/common/time_series.py` (delete)
- `src/python/reopt_pysam_vn/common/validation.py` (delete)
- `plans/active/2026-05-22-gap01-factory-ingestion-plan.md` (move to `plans/archive/`)
- `plans/active/2026-05-22-gap02-procurement-comparison-plan.md` (move to `plans/archive/`)
- `plans/active/2026-05-22-gap04-generalized-settlement-plan.md` (move to `plans/archive/`)
- `ceba_delta_report.md` (move to `reports/ceba_delta_report.md`)
- `ceba_repo_test_results.md` (move to `reports/ceba_repo_test_results.md`)
- `ceba_slide_review_report.md` (move to `reports/ceba_slide_review_report.md`)
- `data/schemas/extracted_inputs.schema.json` (modify): the `generation_kw`
  `description` string only. Do not change any type, `minItems`, or `maxItems`.

**Function Signatures**
- `pytest_deselected(items: list) -> None` — pytest hook in `tests/conftest.py`;
  accumulates the running count of deselected test items; returns nothing.
- `pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None` —
  existing hook, extended to enforce both the skip budget and the deselect budget.

**Test Specs**
- Run the full portable suite with `REOPT_PYSAM_VN_MAX_DESELECTED=46` → exits `0`
  and reports `655 passed, 46 deselected, 3 xfailed`.
- Run it with `REOPT_PYSAM_VN_MAX_DESELECTED=10` → exit code `1` and stderr contains
  `DESELECT BUDGET EXCEEDED: 46 deselected, budget 10`.
- Run it with `REOPT_PYSAM_VN_MAX_DESELECTED` unset → exits `0`; no budget message.
- `python -O -c "import sys; sys.path.insert(0,'src/python'); import reopt_pysam_vn.webapp.jobs"`
  → exits `0`, and the changed line is a `raise`, not an `assert` (verify with
  `grep -n "assert " src/python/reopt_pysam_vn/webapp/jobs.py` returning no match).
- `grep -rn "identity_currency\|constant_series\|require_positive" src scripts tests`
  → no matches after the deletions.

**Dependencies**
- None.

**Exit Criteria**
- [ ] `PYTHONPATH="" REOPT_PYSAM_VN_MAX_SKIPS=0 REOPT_PYSAM_VN_MAX_DESELECTED=46 python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia and not requires_nrel_key and not requires_pysam_resource" -rs -q --cov=reopt_pysam_vn --cov-report=term-missing --cov-fail-under=82` exits `0`.
- [ ] `ruff check src scripts tests` prints `All checks passed!`.
- [ ] `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` prints `Success: no issues found`.
- [ ] `ls plans/active/*.md | wc -l` returns `6` (nine minus the three archived).
- [ ] `ls ceba_*.md 2>/dev/null | wc -l` returns `0`.
- [ ] `gh run list --limit 3` shows `success` on both `test (3.10)` and `test (3.12)` for the pushed commit.

**Phase Risks**
- **RISK-01-01:** Deleting the three `common/` stubs breaks an importer not found by
  grep (for example a dynamic import or a doc example). Mitigation: run the *full*
  test suite, not a subset, before committing — this repository has previously
  broken tests by deleting code that grep suggested was dead, because the tests
  built paths from string segments rather than importing by name.
- **RISK-01-02:** `--cov-fail-under=82` fails immediately if the measured value is
  81.x on one matrix leg. Mitigation: run the coverage command locally on Python
  3.12 first and, if the figure is below 82, set the floor to `floor(measured)`
  and note the actual value in the commit message.

### PHASE-02 - Generic Extracted-Inputs Assembler (the last mile)

**Goal**
Let a deal that arrives as nothing but a `DealConfig` plus an 8760-hour load series
reach a completed offsite/DPPA result, through both the web form and the CLI,
without a hand-built `extracted` JSON.

**Tasks**
- [x] TASK-02-01: Add a public, VND-denominated TOU series builder to
  `src/python/reopt_pysam_vn/reopt/preprocess.py` by extracting the rate
  computation that currently happens inside `build_vietnam_tariff` before its
  `convert_vnd_to_usd` calls. `build_vietnam_tariff` must keep returning exactly
  what it returns today — refactor it to call the new helper and convert, so no
  existing numeric output changes.
- [x] TASK-02-02: Create `src/python/reopt_pysam_vn/analysis/extracted.py`
  implementing `build_extracted_inputs` per Specification S3.
- [x] TASK-02-03: Validate the assembled dict with
  `reopt_pysam_vn.analysis.validation.validate_extracted_inputs` before returning
  it, so a defect in the assembler surfaces as a collected list of violations
  rather than a `KeyError` deep inside an orchestrator.
- [x] TASK-02-04: Wire the assembler into
  `src/python/reopt_pysam_vn/webapp/service.py::run_analysis._run_offsite`: when
  `extracted is None` **and** `deal_config.load.get("loads_kw")` is a list, call
  `build_extracted_inputs(deal_config)` instead of raising `MissingInputsError`.
  Keep raising `MissingInputsError` when neither is available, with the message
  updated to mention that a load series in `deal_config.load['loads_kw']` is
  sufficient.
- [x] TASK-02-05: Add a `--derive-extracted` flag to the `offsite_dppa` subcommand
  in `src/python/reopt_pysam_vn/analysis/__main__.py`. When set and `--extracted`
  is absent, call `build_extracted_inputs(deal)` and pass the result. When both are
  given, `--extracted` wins and the CLI prints a one-line notice to stderr.
- [x] TASK-02-06: Add tests covering the assembler in isolation and the
  end-to-end web submission.

**File Changes**
- `src/python/reopt_pysam_vn/reopt/preprocess.py` (modify): add
  `build_evn_tou_series_vnd_per_kwh(...)` near `build_vietnam_tariff` (around
  line 375). Refactor `build_vietnam_tariff` so its `rates` list is produced by
  calling the new helper and mapping `convert_vnd_to_usd` over it. Leave
  `_build_hourly_rates`, `_build_8760_rates`, `_resolve_tariff_multiplier_block`,
  and the demand-charge block unchanged. Export the new name in the module's
  public surface if one is declared.
- `src/python/reopt_pysam_vn/analysis/extracted.py` (create): the assembler, fully
  type-annotated (this package has `disallow_untyped_defs = true`). Import
  `OrchestratorInputError` from `reopt_pysam_vn.analysis.offsite_dppa`; import
  `compute_buyer_benchmark` from `reopt_pysam_vn.integration.settlement`;
  import `exchange_rate` and `market_wholesale_reference_vnd_per_kwh` from
  `reopt_pysam_vn.common.assumptions`; import `load_vietnam_data` and
  `build_evn_tou_series_vnd_per_kwh` from `reopt_pysam_vn.reopt.preprocess`.
  Perform the heavy imports inside the function body, matching the lazy-import
  style used by `analysis/offsite_dppa.py`.
- `src/python/reopt_pysam_vn/analysis/__init__.py` (modify): re-export
  `build_extracted_inputs` and add it to `__all__`, beside the existing
  `DealConfig` / `run_onsite` / `run_offsite_dppa` exports.
- `src/python/reopt_pysam_vn/webapp/service.py` (modify): the `_run_offsite` inner
  function inside `run_analysis` only. Do not change `_run_onsite`,
  `solve_relevant_hash`, `load_nrel_api_key`, or `solve_onsite_via_nrel`. Update
  the module docstring, which currently asserts "offsite/both modes always need an
  `extracted` upload" — that becomes false.
- `src/python/reopt_pysam_vn/analysis/__main__.py` (modify): add
  `p_off.add_argument("--derive-extracted", action="store_true", dest="derive_extracted")`
  and branch inside `_cmd_offsite_dppa`. Update the module docstring's usage line.
- `tests/python/analysis/test_extracted.py` (create): assembler unit tests.
- `tests/python/webapp/test_api_runs.py` (modify): add the end-to-end multipart
  submission test described below. Do not alter existing tests.
- `tests/python/analysis/test_cli.py` (modify): add an in-process `main(argv)` test
  for `--derive-extracted`. Do not alter existing tests.
- `README.md` (modify): in the Analysis Modes section, state that an offsite run
  needs either an `extracted` payload or a `deal_config.load.loads_kw` series, and
  document `--derive-extracted`.
- `src/python/reopt_pysam_vn/webapp/README.md` (modify): update the "NREL API key"
  paragraph, which currently states that offsite runs "always need a pre-solved
  `extracted` payload".

**Function Signatures**
- `build_evn_tou_series_vnd_per_kwh(vn: VNData, *, customer_type: str, voltage_level: str, regime_id: str = DEFAULT_REGIME_ID, year: int | None = None) -> list[float]` —
  returns an 8760-element list of EVN time-of-use energy rates in **VND per kWh**
  (365 days × 24 hours, weekday schedule Monday–Saturday and Sunday schedule on
  Sunday), for a `household` customer type a flat tier-2 rate repeated 8760 times.
- `build_extracted_inputs(deal_config: DealConfig, *, vn: VNData | None = None) -> dict[str, Any]` —
  returns a schema-valid extracted-inputs dict assembled from the deal config and
  the Vietnam data layer per Specification S3; raises `OrchestratorInputError` when
  `deal_config.load["loads_kw"]` is missing or is not exactly 8760 non-negative
  numbers.

**Test Specs**
- `build_evn_tou_series_vnd_per_kwh(vn, customer_type="industrial", voltage_level="medium_voltage_22kv_to_110kv", year=2024)`
  → a list of length exactly `8760`, every element `> 0`, and containing exactly
  three distinct values (the peak, standard and off-peak rates).
- Consistency with the existing USD builder: for the same arguments,
  `build_vietnam_tariff(vn, "industrial", "medium_voltage_22kv_to_110kv", year=2024)["tou_energy_rates_per_kwh"][i] * exchange_rate(vn)`
  equals `build_evn_tou_series_vnd_per_kwh(...)[i]` within `1e-6` relative, for
  `i` in `[0, 1000, 5000, 8759]`.
- `build_extracted_inputs(DealConfig.from_dict({"case": "X", "mode": "offsite_dppa", "load": {"loads_kw": [1000.0] * 8760}}))`
  → a dict where `len(result["loads_kw"]) == 8760`,
  `len(result["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]) == 8760`,
  `result["benchmark"]["annual_load_kwh"] == 8_760_000.0`,
  `result["benchmark"]["peak_demand_kw"] == 1000.0`,
  `result["benchmark"]["wholesale_rate_vnd_per_kwh"] == 671.0`,
  `result["extraction_meta"]["customer_type"] == "industrial"`,
  `result["extraction_meta"]["voltage_level"] == "medium_voltage_22kv_to_110kv"`,
  `"customer_type" in result["extraction_meta"]["defaulted_fields"]`,
  and `"generation_kw" not in result`.
- Load-weighted benchmark, not a simple mean: with
  `loads_kw = [0.0] * 4380 + [1000.0] * 4380`, the resulting
  `benchmark["weighted_evn_price_vnd_per_kwh"]` equals
  `sum(l * t for l, t in zip(loads, tariff)) / 4_380_000.0` within `1e-9` relative
  and is **not** equal to `sum(tariff) / 8760` (assert the two differ).
- `build_extracted_inputs(DealConfig.from_dict({"case": "X", "mode": "offsite_dppa", "load": {"loads_kw": [1000.0] * 8000}}))`
  → raises `OrchestratorInputError` whose message contains `8760` and `8000`.
- `build_extracted_inputs(DealConfig.from_dict({"case": "X", "mode": "offsite_dppa"}))`
  → raises `OrchestratorInputError` mentioning `deal_config.load['loads_kw']`.
- The assembled dict passes `validate_extracted_inputs(result)` without raising.
- End-to-end webapp test in `tests/python/webapp/test_api_runs.py`: `POST /api/deals`
  as multipart with fields `case=MEKONG_NEW_DEAL`, `mode=offsite_dppa`,
  `site.latitude=10.03`, `site.longitude=105.78`, `site.region=south`,
  `contract.settlement_mechanism=physical`, `contract.strike_vnd_per_kwh=1200`,
  `contract.annual_solar_gwh=8.76`, `plant.capacity_mwac=5`, and a `load_file`
  containing a `load_kw` header row plus 8760 rows of `1000` → HTTP `202`;
  the subsequent `GET /api/runs/{run_id}` returns `status.state == "done"` and
  `result["quality"]["orchestrator"] == "generic_vn_dppa"` and
  `result["quality"]["basis"] == "directional"`.
- CLI test in `tests/python/analysis/test_cli.py`: write a deal-config JSON
  carrying `load.loads_kw` (8760 values) to `tmp_path`, then
  `main(["offsite_dppa", "--config", str(cfg), "--derive-extracted", "--no-developer", "--out", str(out)])`
  → returns `0` and `json.loads(out.read_text())["quality"]["orchestrator"] == "generic_vn_dppa"`.
- Regression guard: an offsite submission with **no** `loads_kw` and **no**
  `extracted` still ends `state == "error"` with `error_code == "MISSING_INPUTS"`.

**Dependencies**
- PHASE-01 (the coverage floor and deselect budget must exist before new modules
  land, so any coverage drop is caught at the point it is introduced).

**Exit Criteria**
- [ ] The end-to-end webapp test passes: a form submission with only a load CSV,
      for an unregistered case, reaches `state: done`.
- [ ] `tests/python/webapp/test_golden_parity.py::test_samsung_ttc_web_api_matches_direct_library_call_bit_exact` still passes (CON-002).
- [ ] Every existing test in `tests/python/reopt/` still passes, proving the
      `build_vietnam_tariff` refactor changed no USD output.
- [ ] `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` passes with the new module included.
- [ ] Coverage of `src/python/reopt_pysam_vn/analysis/extracted.py` is at least 90 %
      in the `term-missing` report.
- [ ] `gh run list --limit 3` shows `success` on both matrix legs.

**Phase Risks**
- **RISK-02-01:** Refactoring `build_vietnam_tariff` silently changes a USD rate
  through a floating-point reassociation, moving REopt-derived goldens.
  Mitigation: extract the VND rates *before* any conversion and have
  `build_vietnam_tariff` apply `convert_vnd_to_usd` to each element, preserving the
  existing per-element operation order; then run the whole `tests/python/reopt/`
  directory and confirm no numeric assertion moves.
- **RISK-02-02:** Assembling `extracted` for a `mode == "both"` run would call the
  assembler once per mode and duplicate work. Mitigation: assemble at most once per
  `run_analysis` call by hoisting the derived value into a local variable in
  `run_analysis` before the mode dispatch.
- **RISK-02-03:** `validate_extracted_inputs` rejects the assembled dict because of
  a field the assembler adds that the schema does not describe. Mitigation: the
  schema's top level sets `additionalProperties: true` and the `benchmark` block
  does too, so extra keys are legal — but run the validator in a test rather than
  assuming.

### PHASE-03 - Physical Model Honesty

**Goal**
Stop the generation layer from silently misrepresenting where and how it modelled a
plant: disclose the substituted solar resource, choose the array configuration
explicitly, stop manufacturing night-time solar, and restore the repository's only
physical plausibility gate to CI.

**Tasks**
- [x] TASK-03-01: Add a solar-resource catalogue to
  `src/python/reopt_pysam_vn/pysam/pvwatts_battery.py` mapping each tracked resource
  file to its latitude and longitude (ASM-002), plus a great-circle helper
  implementing Specification S1.
- [x] TASK-03-02: Rewrite
  `analysis/orchestrators/generic_vn_dppa._try_pvwatts_generation` to resolve the
  resource through the catalogue, compute the site-to-resource distance, and return
  the distance and file identity alongside the series.
- [x] TASK-03-03: Set `array_type`, `tilt`, `azimuth` and `gcr` explicitly in
  `generic_vn_dppa`, mapped from `deal_config.plant["mounting"]` per ASM-004, with
  `tilt` equal to the site latitude for the two fixed options.
- [x] TASK-03-04: Add `mounting` to the `plant` block of
  `data/schemas/deal_config.schema.json` as an optional string with the three-value
  enum.
- [x] TASK-03-05: Pin `integration/dppa_samsung_ttc._pvwatts_south_solar_8760` to
  `array_type = 2` and `tilt = 0.0` explicitly (ASM-005), and correct its docstring,
  which currently calls the Ninh Thuan file "the cached southern resource".
- [x] TASK-03-06: Replace `_calibrate_to_target` with the Specification S2
  algorithm, returning `(series, warnings)` so the infeasibility warning reaches the
  result.
- [x] TASK-03-07: Extend the generic result's `quality` block with
  `solar_resource_file`, `solar_resource_latitude`, `solar_resource_longitude`,
  `solar_resource_distance_km`, `array_type`, and `tilt_degrees`, and set
  `solar_profile_source` to `"pvwatts_fallback_resource"` when the distance is at
  or above 100 km (ASM-003).
- [x] TASK-03-08: Rewrite `tests/python/integration/test_capacity_factor_benchmark.py`
  to run against the tracked resource file with an explicit fixed open-rack
  configuration, remove the `@pytest.mark.xfail` decorator, and remove the
  `pytest.importorskip("PySAM")` guard — `nrel-pysam` is a hard dependency and is
  installed in CI, so a runtime skip would violate CON-005.
- [x] TASK-03-09: Record the change in a short dated memo under `reports/` naming
  the measured before/after yields, so the movement is documented rather than
  absorbed silently.

**File Changes**
- `src/python/reopt_pysam_vn/pysam/pvwatts_battery.py` (modify): add
  `SOLAR_RESOURCE_CATALOG: dict[str, tuple[float, float]]` mapping
  `"ninhsim_himawari_2019_60min.csv"` and
  `"nsrdb_12.525729252783036_109.02003383567742_himawari_60_2019.csv"` to
  `(12.525729252783036, 109.02003383567742)`; add
  `resource_coordinates(...)` and `great_circle_km(...)`. Leave
  `ensure_solar_resource_file`, `DEFAULT_SOLAR_RESOURCE_FILE`, and every finance
  function unchanged.
- `src/python/reopt_pysam_vn/analysis/orchestrators/generic_vn_dppa.py` (modify):
  rewrite `_calibrate_to_target`, `_try_pvwatts_generation`,
  `build_generic_generation_profile`, and the `quality` block of
  `build_generic_offsite_artifact`. Leave `_synthetic_generation_8760`'s shape
  formula, `_contract_mode`, `_resolve_strike_vnd_kwh`, and the settlement/sweep
  calls unchanged so existing exact-value tests keep passing.
- `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` (modify):
  `_pvwatts_south_solar_8760` only — add the two explicit assignments and the
  corrected docstring. Change nothing else in the module.
- `data/schemas/deal_config.schema.json` (modify): add `mounting` under
  `properties.plant.properties`. Do not add it to any `required` list.
- `tests/python/integration/test_capacity_factor_benchmark.py` (modify): full
  rewrite per the test spec below.
- `tests/python/analysis/test_generic_vn_dppa.py` (modify): add the new cases below.
  Leave the eight existing tests untouched — they supply `generation_kw` explicitly
  and their exact expected values must not move.
- `reports/2026-08-19-solar-resource-and-array-config.md` (create): a short memo
  recording the measured 1,888.3 vs 1,527.9 kWh/kWp figures, the 17.44 % vs 21.56 %
  capacity factors, the Samsung pin, and the 100 km disclosure threshold.

**Function Signatures**
- `resource_coordinates(resource_file: Path | str) -> tuple[float, float] | None` —
  returns the `(latitude, longitude)` in decimal degrees for a catalogued resource
  file, matched on `Path(resource_file).name`; `None` when the file is not catalogued.
- `great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float` —
  returns the great-circle separation in kilometres per Specification S1, using a
  mean Earth radius of 6371.0 km.
- `_calibrate_to_target(series: list[float], annual_target_kwh: float, cap_kw: float | None) -> tuple[list[float], list[str]]` —
  returns the calibrated 8760-element series in kW and a list of warning strings
  (empty when the target was met exactly), implementing Specification S2.
- `_try_pvwatts_generation(extracted: dict[str, Any], deal_config: DealConfig) -> tuple[list[float], dict[str, Any]] | None` —
  returns the 8760-element PVWatts series in kW plus a provenance dict with keys
  `resource_file`, `resource_latitude`, `resource_longitude`, `distance_km`,
  `array_type`, `tilt_degrees`; `None` when PySAM, the resource file, or a
  derivable DC capacity is unavailable.
- `_array_config(deal_config: DealConfig, site_latitude: float | None) -> tuple[int, float]` —
  returns `(array_type, tilt_degrees)` for the deal's `plant.mounting`, defaulting
  to `(0, site_latitude or 0.0)` for `"fixed_open_rack"`.
- `build_generic_generation_profile(extracted: dict[str, Any], deal_config: DealConfig) -> dict[str, Any]` —
  unchanged name; the returned dict gains a `provenance` key (the dict above, or
  `{}` for the explicit-series and synthetic paths) and a `warnings` key (list of
  strings).

**Test Specs**
- `great_circle_km(10.88, 106.28, 12.525729252783036, 109.02003383567742)` → a value
  `x` with `330.0 <= x <= 345.0`.
- `great_circle_km(12.525729252783036, 109.02003383567742, 12.525729252783036, 109.02003383567742)` → `0.0`.
- `resource_coordinates("ninhsim_himawari_2019_60min.csv")` → `(12.525729252783036, 109.02003383567742)`.
- `resource_coordinates("does_not_exist.csv")` → `None`.
- Night-injection regression, the defect this phase fixes: with a synthetic shape,
  `_calibrate_to_target(shape, annual_target_kwh=6.0e6, cap_kw=1000.0)` → the
  returned series has `series[h] == 0.0` for **every** `h` where `shape[h] == 0.0`,
  and the returned warnings list is non-empty and contains the substring
  `"infeasible"`. (Before this change the same call placed 834.5 MWh across night
  hours with a 457 kW peak.)
- Feasible clipping still calibrates exactly:
  `_calibrate_to_target(shape, annual_target_kwh=12.0e6, cap_kw=5000.0)` →
  `sum(series)` equals `12.0e6` within `1.0` kWh, `max(series) <= 5000.0 + 1e-6`,
  and `series[h] == 0.0` wherever `shape[h] == 0.0`.
- No cap: `_calibrate_to_target([1.0] * 8760, annual_target_kwh=8760.0, cap_kw=None)`
  → every element `== 1.0`, warnings empty.
- All-zero shape: `_calibrate_to_target([0.0] * 8760, 1.0e6, 1000.0)` → 8760 zeros
  and a warning containing `"entirely zero"`.
- Distance disclosure: build a generic artifact for a deal with
  `extracted["site"] = {"latitude": 10.03, "longitude": 105.78}`, no
  `generation_kw`, and `plant.capacity_mwac = 5.0`. When PySAM resolves the tracked
  resource, `quality["solar_resource_distance_km"]` is greater than `100.0`,
  `quality["solar_profile_source"] == "pvwatts_fallback_resource"`, and
  `quality["warnings"]` contains a string mentioning both `"solar resource"` and
  the distance. Guard the PySAM-specific part of this test with the registered
  `requires_pysam_resource` marker only if PySAM proves unavailable in CI; the
  tracked resource file and the hard `nrel-pysam` dependency mean it should not be
  needed.
- Array configuration: `_array_config(DealConfig.from_dict({"case": "X", "mode": "offsite_dppa", "plant": {"mounting": "fixed_roof"}}), 10.5)` → `(1, 10.5)`;
  `_array_config(DealConfig.from_dict({"case": "X", "mode": "offsite_dppa", "plant": {"mounting": "single_axis_tracking"}}), 10.5)` → `(2, 0.0)`;
  `_array_config(DealConfig.from_dict({"case": "X", "mode": "offsite_dppa"}), 10.5)` → `(0, 10.5)`.
- Rewritten capacity-factor gate, network-free and CI-enforced. Configure
  `PySAM.Pvwattsv8` with `solar_resource_file` set to the tracked
  `data/interim/pysam_resources/ninhsim_himawari_2019_60min.csv`,
  `system_capacity = 50000`, `dc_ac_ratio = 1.2`, `inv_eff = 96.0`,
  `losses = 14.0`, `array_type = 0`, `tilt = 12.525729252783036`,
  `azimuth = 180.0`, `gcr = 0.3`, `module_type = 0`. Compute
  `cf_pct = annual_energy / (50000 * 8760) * 100`. Assert
  `14.0 <= cf_pct <= 20.0`. Expected measured value: **17.44 %**
  (`annual_energy ≈ 76,391,641 kWh`). Include an assertion comment recording that
  the same configuration with `array_type = 2` yields `21.56 %`, outside the band —
  which is why the production default had to become explicit.
- Samsung invariance: `tests/python/webapp/test_golden_parity.py` and
  `tests/python/analysis/test_samsung_ttc_parity.py` produce exactly the same
  numbers as before this phase. Verify by running
  `PYTHONPATH="" python -m pytest tests/python/analysis/test_samsung_ttc_parity.py -q`
  and confirming the same `xfailed` counts as before, with no new failures.

**Dependencies**
- PHASE-01.
- `nrel-pysam==7.1.0` and `data/interim/pysam_resources/ninhsim_himawari_2019_60min.csv`,
  both already present and tracked.

**Exit Criteria**
- [ ] `PYTHONPATH="" python -m pytest tests/python/integration/test_capacity_factor_benchmark.py -q` reports `1 passed` with no `xfail` and no skip.
- [ ] The full portable suite reports `2 xfailed` instead of `3` (the capacity-factor test has left the xfail set), and the deselect count is unchanged at 46.
- [ ] Building a generic artifact for a site more than 100 km from the tracked resource sets `quality["solar_profile_source"] == "pvwatts_fallback_resource"` and a non-empty `quality["warnings"]`.
- [ ] No hour with zero input shape carries non-zero calibrated generation, asserted by the regression test above.
- [ ] `tests/python/analysis/test_generic_vn_dppa.py` passes with all eight pre-existing exact-value assertions unchanged.
- [ ] Coverage of `src/python/reopt_pysam_vn/analysis/orchestrators/generic_vn_dppa.py` rises from 56 % to at least 85 % in the `term-missing` report.
- [ ] `reports/2026-08-19-solar-resource-and-array-config.md` exists and records the before/after figures.
- [ ] `gh run list --limit 3` shows `success` on both matrix legs.

**Phase Risks**
- **RISK-03-01:** Adding the explicit `array_type` pin to `dppa_samsung_ttc.py`
  accidentally changes its output because the inherited default differs between
  PySAM builds. Mitigation: before editing, dump the current values with
  `python -c "import PySAM.Pvwattsv8 as p; m=p.default('PVWattsSingleOwner'); print(m.SystemDesign.array_type, m.SystemDesign.tilt, m.SystemDesign.gcr, m.SystemDesign.module_type)"`
  and pin exactly what it prints. Expected on `nrel-pysam==7.1.0`:
  `2.0 0.0 0.3 0.0`.
- **RISK-03-02:** The rewritten capacity-factor test fails on the CI runner because
  PySAM's CSV weather reader behaves differently on Linux than on Windows.
  Mitigation: the assertion is a 6-point band (14–20 %) around a measured 17.44 %,
  which absorbs any plausible platform difference. If it still fails, capture the CI
  value from the `-rs` output before widening anything.
- **RISK-03-03:** `_calibrate_to_target` changing its return type from `list` to a
  tuple breaks a caller. Mitigation: `grep -rn "_calibrate_to_target" src scripts tests`
  and update every call site; the function is module-private and currently has two
  call sites, both inside `generic_vn_dppa.py`.

### PHASE-04 - Split the Result Payload

**Goal**
Stop storing, serving, and inlining a 3.79 MB result document. Keep the hourly
ledger as a first-class artifact, served separately as CSV.

**Tasks**
- [x] TASK-04-01: Add `save_ledger_csv` and `get_ledger_csv_path` to
  `src/python/reopt_pysam_vn/webapp/storage.py`, writing `ledger.csv` into the same
  per-run directory as `result.json`.
- [x] TASK-04-02: In `webapp/service.run_analysis`, after producing an offsite
  result dict, pop `base_settlement["hourly_ledger"]` out of the returned document
  and return it separately so the caller can persist it. Preserve
  `base_settlement["annual_summary"]`, `["contract_params"]`,
  `["market_source_label"]`, and `["buyer_benchmark"]` in the summary result.
- [x] TASK-04-03: In `webapp/routes/api.py::_submit_deal_config`, write the ledger
  via `storage.save_ledger_csv` before `storage.save_result`, and add a
  `GET /api/runs/{run_id}/ledger.csv` route returning
  `Content-Type: text/csv` with a `Content-Disposition: attachment` header.
- [x] TASK-04-04: Add a "Download hourly ledger (CSV)" link to
  `src/python/reopt_pysam_vn/webapp/templates/run.html`, rendered only when the
  ledger file exists.
- [x] TASK-04-05: Remove the raw-result JSON blob from
  `webapp/results_view.render_standalone_report_html`. Keep the metrics table; embed
  only the summary blocks, never the ledger.
- [x] TASK-04-06: Document the new artifact in the storage-layout section of
  `src/python/reopt_pysam_vn/webapp/README.md`.

**File Changes**
- `src/python/reopt_pysam_vn/webapp/storage.py` (modify): add the two methods to the
  storage class near `save_result` (around line 146). Do not change `create_run`,
  `set_status`, `list_runs`, `prune`, `mark_interrupted_runs`, or
  `find_cached_run_id`.
- `src/python/reopt_pysam_vn/webapp/service.py` (modify): change `run_analysis`'s
  return type to `tuple[dict[str, Any], list[dict[str, Any]] | None]` — the summary
  result and the extracted ledger rows. Update every caller.
- `src/python/reopt_pysam_vn/webapp/routes/api.py` (modify): `_submit_deal_config`
  to unpack the tuple and persist the ledger; add the new download route beside the
  existing `download_result` and `download_report` routes.
- `src/python/reopt_pysam_vn/webapp/jobs.py` (modify): the background solve worker
  also calls `service.run_analysis`; unpack the tuple there too.
- `src/python/reopt_pysam_vn/webapp/results_view.py` (modify):
  `render_standalone_report_html` only — drop the
  `<script type="application/json" id="raw-result">` element. Leave
  `build_view_model`, `_onsite_metrics`, `_onsite_charts`, `_offsite_metrics`, and
  `_offsite_charts` unchanged.
- `src/python/reopt_pysam_vn/webapp/templates/run.html` (modify): add the CSV link
  in the results block. Do not touch the polling script or the context-map block.
- `src/python/reopt_pysam_vn/webapp/README.md` (modify): add `ledger.csv` to the
  storage-layout list.
- `tests/python/webapp/test_storage.py` (modify): add ledger round-trip tests.
- `tests/python/webapp/test_api_runs.py` (modify): add the download-route tests.
- `tests/python/webapp/test_results_view.py` (modify): assert the raw JSON blob is
  gone.

**Function Signatures**
- `save_ledger_csv(self, run_id: str, ledger: list[dict[str, Any]]) -> None` —
  writes `ledger.csv` into the run directory using the first row's key order as the
  header; writes nothing when `ledger` is empty or `None`.
- `get_ledger_csv_path(self, run_id: str) -> Path | None` — returns the path to the
  run's `ledger.csv`, or `None` when the run has no ledger.
- `run_analysis(deal_config: DealConfig, *, results: dict[str, Any] | None = None, scenario: dict[str, Any] | None = None, extracted: dict[str, Any] | None = None, run_developer: bool = True) -> tuple[dict[str, Any], list[dict[str, Any]] | None]` —
  returns the summary result document with `hourly_ledger` removed, and the removed
  ledger rows (or `None` when the result carried none).

**Test Specs**
- Submit the PHASE-02 end-to-end multipart request, then
  `len(json.dumps(GET /api/runs/{run_id} body))` → **under 200,000 bytes**
  (it is ~3.79 MB before this phase).
- `GET /api/runs/{run_id}/ledger.csv` → HTTP `200`,
  `response.headers["content-type"]` starts with `text/csv`, the body's first line
  is exactly
  `hour,load_kwh,generation_kwh,matched_kwh,shortfall_kwh,excess_kwh,exported_kwh,curtailed_kwh,market_price_vnd_kwh,retail_price_vnd_kwh,evn_matched_payment_vnd,dppa_charge_vnd,shortfall_payment_vnd,buyer_cfd_payment_vnd,buyer_total_payment_vnd,developer_revenue_vnd`,
  and the body has exactly **8,761** lines (header plus 8,760 rows).
- `GET /api/runs/{run_id}/ledger.csv` for a run with no ledger (an onsite run) →
  HTTP `404`.
- `GET /api/runs/{unknown_id}/ledger.csv` → HTTP `404`.
- `GET /api/runs/{run_id}/result.json` still returns HTTP `200` and its body no
  longer contains the key `hourly_ledger`.
- `GET /api/runs/{run_id}/report.html` → HTTP `200`, and the body does **not**
  contain the string `id="raw-result"`; body length under `100,000` bytes.
- Samsung parity: a `DPPA_SAMSUNG_TTC` submission produces a result with no
  `ledger.csv` written (its artifact carries no `hourly_ledger`) and
  `test_samsung_ttc_web_api_matches_direct_library_call_bit_exact` still passes.

**Dependencies**
- PHASE-02 (the end-to-end submission is what produces a large ledger through the
  web layer).

**Exit Criteria**
- [ ] A generic offsite run's `result.json` on disk is under 200 KB, and a sibling `ledger.csv` of 8,761 lines exists in the same run directory.
- [ ] `GET /api/runs/{run_id}` response body is under 200 KB.
- [ ] `GET /api/runs/{run_id}/ledger.csv` returns a well-formed CSV with the exact header above.
- [ ] The downloadable report HTML is under 100 KB and contains no embedded raw result JSON.
- [ ] `tests/python/webapp/test_golden_parity.py` still passes (CON-002).
- [ ] `gh run list --limit 3` shows `success` on both matrix legs.

**Phase Risks**
- **RISK-04-01:** Changing `run_analysis`'s return type breaks a caller outside
  `webapp/`. Mitigation: `grep -rn "run_analysis" src scripts tests` and update every
  hit; the function is webapp-internal, so the blast radius is `routes/api.py` and
  `jobs.py` plus their tests.
- **RISK-04-02:** `webapp/compare.py` reads `result["base_settlement"]` and may
  expect the ledger. Mitigation: read `compare.py` before editing; it operates on
  summary blocks only, but confirm rather than assume, and run
  `tests/python/webapp/test_compare.py`.
- **RISK-04-03:** Existing stored runs under `artifacts/webapp/runs/` still carry the
  old fat `result.json` and have no `ledger.csv`. Mitigation: `get_ledger_csv_path`
  returns `None` when the file is absent and the template hides the link — no
  migration is required and old runs keep rendering.

### PHASE-05 - Unify Load Ingestion

**Goal**
Route the web upload through the mature ingestion library so the product accepts
15-minute and 30-minute data, multi-column and multi-sheet workbooks, JSON, and
files with gaps — and reports exactly what it did to the data.

**Tasks**
- [x] TASK-05-01: Rewrite `src/python/reopt_pysam_vn/webapp/uploads.py` to persist
  the uploaded bytes to a temporary file carrying the original suffix, call
  `reopt_pysam_vn.ingestion.loader.ingest_factory_load` on that path, and delete the
  temporary file in a `finally` block. Return both the series and the cleaning
  summary.
- [x] TASK-05-02: Map `ingestion.loader.LoadLengthError` and any `ValueError` from
  the loader onto the existing `UploadError` so `routes/api.py`'s HTTP 422 handling
  is unchanged.
- [x] TASK-05-03: Accept `.json` uploads in `routes/api.py::create_deal` in addition
  to `.csv`, `.xlsx`, `.xlsm`, and `.xls`; reject any other suffix with a 422 naming
  the accepted list.
- [x] TASK-05-04: Carry the cleaning summary into `deal_config["load"]["load_cleaning"]`
  so it reaches `extracted["load_cleaning"]` through the PHASE-02 assembler, and
  render it as a card on the run page.
- [x] TASK-05-05: Add a load plausibility screen that appends advisory strings to
  the cleaning summary without ever rejecting the upload.

**File Changes**
- `src/python/reopt_pysam_vn/webapp/uploads.py` (modify): replace
  `parse_load_csv`, `parse_load_xlsx`, `_first_numeric_column`, and
  `_validate_length` with a single `parse_load_upload`. Keep the `UploadError` class
  and its name so `routes/api.py`'s `except UploadError` still catches. Keep
  `__all__` exporting `UploadError` and add `parse_load_upload`.
- `src/python/reopt_pysam_vn/webapp/routes/api.py` (modify): `create_deal` only —
  call `parse_load_upload(content, filename)` instead of branching on the suffix,
  and thread the cleaning summary into the deal config before
  `deal_config_from_form`. Do not change `create_run`, `_submit_deal_config`, or
  `_nest_form_fields`.
- `src/python/reopt_pysam_vn/webapp/forms.py` (modify): `deal_config_from_form`
  gains an optional `load_cleaning: dict[str, Any] | None = None` keyword written
  into the `load` block. Existing callers that omit it keep working.
- `src/python/reopt_pysam_vn/analysis/extracted.py` (modify): copy
  `deal_config.load["load_cleaning"]` into `extracted["load_cleaning"]` when present.
- `src/python/reopt_pysam_vn/webapp/routes/pages.py` (modify): `run_detail` passes
  `deal_config.get("load", {}).get("load_cleaning")` into the template context.
- `src/python/reopt_pysam_vn/webapp/templates/run.html` (modify): add a "Load data
  quality" card rendered only when the cleaning summary is present.
- `tests/python/webapp/test_uploads.py` (modify): rewrite for the new entry point.
- `tests/python/webapp/test_api_runs.py` (modify): add the 15-minute upload test.
- `tests/python/webapp/test_pages.py` (modify): assert the card renders.
- `src/python/reopt_pysam_vn/webapp/README.md` (modify): document the accepted
  formats and resolutions.

**Function Signatures**
- `parse_load_upload(content: bytes, filename: str) -> tuple[list[float], dict[str, Any]]` —
  returns an 8760-element hourly kW series and the loader's cleaning summary
  (including `missing_count`, `interpolated_indices`, `clipped_negative_count`,
  `original_row_count`, and, when resampling occurred, `synthesis_method` and
  `synthesis_source_rows`), plus any advisory strings under the key
  `plausibility_warnings`; raises `UploadError` on an unsupported suffix,
  an unreadable file, or a series length the loader cannot resolve to 8760.
- `screen_load_plausibility(loads_kw: list[float]) -> list[str]` — returns advisory
  strings (never raises) for: a zero fraction above 0.20
  (`"{pct}% of hours are zero"`), a load factor `mean/max` below 0.10
  (`"load factor {lf} is unusually low"`), and a maximum above 1,000,000 kW
  (`"peak {max} kW is unusually large; check the units are kW, not W"`).
- `deal_config_from_form(form: dict[str, Any], *, loads_kw: list[float], load_cleaning: dict[str, Any] | None = None) -> dict[str, Any]` —
  unchanged behaviour plus an optional `load.load_cleaning` block.

**Test Specs**
- Single-column CSV, header `load_kw`, 8760 rows of `1000` →
  `parse_load_upload(content, "load.csv")` returns a series of length 8760 where
  every element is `1000.0`, and `summary["original_row_count"] == 8760`.
- **15-minute data:** CSV with header plus **35,040** rows of `1000` →
  returns a series of length exactly `8760`, `summary["synthesis_method"]` is
  truthy and not `"none"`, and `summary["synthesis_source_rows"] == 35040`.
  (Before this phase the same upload raised
  `expected 8760 hourly kW values, got 35040`.)
- **Timestamped two-column CSV:** header `timestamp,load_kw` plus 8760 rows →
  returns a series of length 8760 whose values come from the `load_kw` column,
  and `summary` records the detected column name as `load_kw`.
- **Gaps:** CSV with 8760 rows where rows 100, 101 and 102 are empty →
  returns a length-8760 series, `summary["missing_count"] == 3`, and the
  interpolated values lie between their neighbours.
- **Negatives:** CSV with 8760 rows where row 50 is `-5` → returns a series whose
  element 49 is `0.0` and `summary["clipped_negative_count"] == 1`.
- **Unsupported suffix:** `parse_load_upload(b"...", "load.txt")` raises
  `UploadError` whose message names `csv`, `xlsx`, and `json`.
- **Empty upload:** `parse_load_upload(b"", "load.csv")` raises `UploadError`.
- `screen_load_plausibility([0.0] * 5000 + [1000.0] * 3760)` → a list containing a
  string with `"zero"`; `screen_load_plausibility([1000.0] * 8760)` → `[]`;
  `screen_load_plausibility([2_000_000.0] * 8760)` → a list containing a string with
  `"kW, not W"`.
- End-to-end: `POST /api/deals` with a 35,040-row CSV for an unregistered offsite
  case → HTTP `202`, and the run reaches `state: done`; the run page HTML contains
  the text `Load data quality`.
- Regression: the existing PHASE-02 8760-row submission still reaches `done` and
  produces the same `annual_summary["matched_mwh"]` as before this phase.

**Dependencies**
- PHASE-02 (the cleaning summary flows into `extracted` through the assembler).
- `openpyxl>=3.1`, already a runtime dependency and used by `ingestion/loader.py`.

**Exit Criteria**
- [ ] A 35,040-row 15-minute CSV uploaded through `POST /api/deals` produces a completed run.
- [ ] A CSV with three empty rows produces a completed run and a cleaning summary reporting `missing_count == 3`.
- [ ] `grep -c "csv.reader" src/python/reopt_pysam_vn/webapp/uploads.py` returns `0` — the fork is gone.
- [ ] The run page renders a "Load data quality" card for uploads that were cleaned or resampled, and omits it otherwise.
- [ ] `mypy src/python/reopt_pysam_vn/webapp` still passes.
- [ ] `gh run list --limit 3` shows `success` on both matrix legs.

**Phase Risks**
- **RISK-05-01:** `ingest_factory_load` takes a filesystem path, not bytes, so the
  web layer must write a temporary file. Mitigation: use
  `tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix)`, close
  the handle before calling the loader (Windows will not let a second handle open
  the file otherwise), and unlink in a `finally` block.
- **RISK-05-02:** `ingest_factory_load` may raise exception types the webapp does
  not catch, turning a bad upload into an HTTP 500. Mitigation: wrap the call in a
  broad `except (ValueError, KeyError, OSError)` and re-raise as `UploadError`, and
  add a test that a deliberately malformed XLSX yields HTTP 422, not 500.
- **RISK-05-03:** The loader's column auto-detection picks a timestamp column as the
  load column for an unusual header. Mitigation: the timestamped-CSV test above
  pins the expected detected column name.

### PHASE-06 - Bring the Numeric Regression Tests into CI

**Goal**
Convert the largest block of CI-excluded tests — 13 settlement-regression tests and
12 Factory-A validation tests, all currently `requires_artifacts` and therefore
enforced on one machine only — into tests that run on every push, by replacing
their dependency on git-ignored `artifacts/` files with small tracked fixtures.

**Tasks**
- [x] TASK-06-01: Write a fixture-builder script that reads the git-ignored source
  artifacts (when present on a developer machine) and writes reduced, gzipped
  fixtures containing only the series and scalars the tests actually consume.
- [x] TASK-06-02: Generate and commit the settlement-regression fixtures.
- [x] TASK-06-03: Copy the four 12 KB Factory-A PySAM result files into
  `tests/fixtures/factory_a/` and commit them.
- [x] TASK-06-04: Repoint `tests/python/integration/test_settlement_regression.py`
  and `tests/python/analysis/test_factory_a_validation.py` at the fixtures and
  remove their `requires_artifacts` markers.
- [x] TASK-06-05: Amend the `test_factory_a_validation.py` module docstring per
  ASM-009 so it does not overclaim.
- [x] TASK-06-06: Lower `REOPT_PYSAM_VN_MAX_DESELECTED` in
  `.github/workflows/ci.yml` to the count the suite actually reports, and raise
  `--cov-fail-under` if coverage improved.
- [x] TASK-06-07: Update `AGENTS.md` and `activeContext.md` with the new enforced
  test count and the new exclusion set.

**File Changes**
- `scripts/python/integration/build_regression_fixtures.py` (create): a CLI that
  reads
  `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_buyer-settlement.json`
  (5.1 MB),
  `artifacts/reports/saigon18/2026-03-29_scenario-d_dppa-settlement.json` (4 KB),
  and `artifacts/results/saigon18/2026-03-20_scenario-d_dppa-baseline_reopt-results.json`
  (2.5 MB), extracts only the required fields, and writes gzipped JSON fixtures.
  Exits with a clear message naming the missing path when an artifact is absent.
- `tests/fixtures/regression/ninhsim_case2_settlement.json.gz` (create): a dict with
  keys `load_kwh`, `contracted_generation_kwh`, `market_reference_price_vnd_per_kwh`,
  `evn_retail_rate_vnd_per_kwh` (each an 8760-element list lifted from the source
  `hourly_ledger`), plus the source's `parameters` and `summary` dicts verbatim.
- `tests/fixtures/regression/saigon18_scenario_d.json.gz` (create): a dict with
  keys `pv_electric_to_load_series_kw` and `storage_to_load_series_kw` (each an
  8760-element list from the REopt results), plus the settlement reference's
  `delivery_factor`, `strike_price_vnd_per_kwh`, `total_q_kwh`, and
  `total_settlement_vnd`.
- `tests/fixtures/factory_a/2026-06-20_factory-a_case_1_pysam-results.json` (create)
- `tests/fixtures/factory_a/2026-06-20_factory-a_case_2_pysam-results.json` (create)
- `tests/fixtures/factory_a/2026-06-20_factory-a_case_3_pysam-results.json` (create)
- `tests/fixtures/factory_a/2026-06-20_factory-a_case_4_pysam-results.json` (create)
- `.gitignore` (modify): add `!tests/fixtures/` as an explicit negation anchored to
  this directory only, and verify with `git status` that no unrelated path became
  tracked. Broad negations in this file have previously re-tracked unrelated
  reports.
- `tests/python/integration/test_settlement_regression.py` (modify): replace the
  four `REPO_ROOT / "artifacts" / ...` constants with the two fixture paths, load
  them with `gzip.open(..., "rt", encoding="utf-8")` plus `json.load`, delete the
  `@pytest.mark.requires_artifacts` decorators on both classes, and delete the
  `pytest.skip` guards in the `reference` / `extracted` / `reopt_results` fixtures
  (CON-005 forbids runtime skips). Keep every tolerance and every assertion exactly
  as it is — the point is to run the same checks, not to change them. Note that
  `SAIGON18_EXTRACTED` already points at the tracked
  `data/interim/saigon18/2026-03-20_saigon18_extracted_inputs.json` and needs no
  fixture.
- `tests/python/analysis/test_factory_a_validation.py` (modify): repoint
  `REPORTS_DIR` at `tests/fixtures/factory_a/`, drop the
  `requires_artifacts` markers, remove the `_load_result` `None` branch and its
  skip, and amend the module docstring per ASM-009.
- `.github/workflows/ci.yml` (modify): the two budget values only.
- `AGENTS.md` (modify): the "Test Suite Status" section's counts and exclusion list.
- `activeContext.md` (modify): the current-state test numbers.

**Function Signatures**
- `build_ninhsim_fixture(source: Path, dest: Path) -> dict[str, int]` — writes the
  gzipped reduced ninhsim fixture and returns `{"rows": 8760, "bytes": <size>}`.
- `build_saigon18_fixture(settlement: Path, reopt: Path, dest: Path) -> dict[str, int]` —
  writes the gzipped reduced saigon18 fixture and returns the same shape.
- `main(argv: list[str] | None = None) -> int` — CLI entry point; returns `0` on
  success, `2` when a required source artifact is missing.

**Test Specs**
- All 13 tests in `tests/python/integration/test_settlement_regression.py` pass
  against the fixtures with unchanged tolerances, in particular:
  `TestNinhsimCaseRegression::test_matched_quantity_within_1pct`,
  `::test_buyer_total_payment_within_1pct`, and
  `::test_negative_cfd_hours_match` (an exact integer equality).
- All 12 tests in `tests/python/analysis/test_factory_a_validation.py` pass against
  the tracked result files with the documented tolerances (equity IRR ±0.07
  absolute, average DSCR ±0.40 absolute, clean self-supply ±15 percentage points).
- Both modules collect and run under CI's exact marker filter — verify with
  `PYTHONPATH="" python -m pytest tests/python/integration/test_settlement_regression.py tests/python/analysis/test_factory_a_validation.py -m "not network and not requires_artifacts and not golden_machine and not requires_julia and not requires_nrel_key and not requires_pysam_resource" -q`
  → `25 passed`, `0 deselected`, `0 skipped`.
- Fixture size guard: `tests/fixtures/regression/ninhsim_case2_settlement.json.gz`
  and `tests/fixtures/regression/saigon18_scenario_d.json.gz` are each under
  **2 MB**, asserted by a check in `tests/python/test_repo_invariants.py`.
- Determinism: running the suite twice produces identical results — the fixtures are
  static files, not regenerated at test time.
- `git status --porcelain` after adding the `.gitignore` negation lists only the
  intended `tests/fixtures/` paths and nothing else.

**Dependencies**
- PHASE-01 (the deselect budget must exist so its reduction is a visible,
  deliberate change).
- PHASE-03 (run last: PHASE-03 alters PVWatts configuration, and the Factory-A
  fixtures must be the files that correspond to the final state of the code).
- The git-ignored source artifacts must be present on the machine that runs the
  fixture builder once. They are not needed thereafter, and never in CI.

**Exit Criteria**
- [ ] `PYTHONPATH="" REOPT_PYSAM_VN_MAX_SKIPS=0 python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia and not requires_nrel_key and not requires_pysam_resource" -rs -q` reports at least `680 passed` and at most `21 deselected`.
- [ ] `PYTHONPATH="" python -m pytest tests/python --collect-only -q -m "requires_artifacts" 2>&1 | tail -1` shows at most `10` tests carrying the marker (down from 35).
- [ ] `REOPT_PYSAM_VN_MAX_DESELECTED` in `.github/workflows/ci.yml` equals the count the suite actually reports.
- [ ] `du -sh tests/fixtures/` reports under 5 MB.
- [ ] `AGENTS.md` and `activeContext.md` state the new counts and match the CI log verbatim.
- [ ] `gh run list --limit 3` shows `success` on both matrix legs.

**Phase Risks**
- **RISK-06-01:** A `.gitignore` negation un-ignores more than intended. This has
  happened in this repository before, when a broad `!reports/*sprint-*.html`
  re-tracked unrelated files. Mitigation: anchor the negation to `tests/fixtures/`
  exactly, then run `git status --porcelain` and inspect every listed path before
  `git add`.
- **RISK-06-02:** The reduced ninhsim fixture omits a field a test needs, and the
  test fails with a `KeyError` rather than a numeric assertion. Mitigation: build
  the fixture, run the 13 tests against it, and only then delete nothing — the
  source artifacts stay on disk untouched, so a second extraction pass is cheap.
- **RISK-06-03:** Freezing the Factory-A result files turns a model-validation test
  into a comparison of two constants, which can never fail. Mitigation: this is
  accepted and disclosed under ASM-009 — the docstring must say so explicitly. The
  genuine model-execution coverage in CI comes from the settlement-regression tests,
  which replay real series through `compute_hourly_settlement` on every run.
- **RISK-06-04:** The 2.5 MB Saigon18 REopt artifact is absent on the machine
  running the builder. Mitigation: the builder exits `2` with the missing path
  named; regenerate the artifact with the documented Saigon18 workflow, or ship only
  the ninhsim fixture in this phase and record the Saigon18 half as remaining work.

## Gotchas

- **Clear `PYTHONPATH` for every pytest invocation.** A stale global `PYTHONPATH`
  from an unrelated virtual environment shadows the repo install and produces
  `ModuleNotFoundError: pydantic_core._pydantic_core` in the webapp tests, which
  looks like a dependency bug and is not one.
- **8760, never 8784.** Every series in this codebase is a non-leap year. Some
  tracked extracted-input files carry 8784-element tariff series; the settlement
  engine pads or truncates to 8760 with `_pad_to_8760`. New code must do the same
  rather than assuming the caller got it right.
- **VND versus USD.** `reopt/preprocess.build_vietnam_tariff` returns **USD** per
  kWh because REopt wants USD. The settlement engine and every DPPA artifact work
  in **VND** per kWh. Mixing them silently produces numbers off by roughly 26,400×.
  Resolve the rate with `common.assumptions.exchange_rate(vn)`, never a literal.
- **`fmp_vnd_per_mwh` and `cfmp_vnd_per_mwh` are per MWh**, not per kWh.
  `integration/market_reference.py` divides by 1,000 on read. Anything new that
  writes those keys must write VND per MWh.
- **`bool` is a subclass of `int` in Python.** Any recursive numeric comparator
  must test `isinstance(x, bool)` *before* `isinstance(x, int)`, or decision flags
  get compared numerically. This has bitten this repository before.
- **A failing `@pytest.mark.xfail(strict=False)` test also sets `report.skipped`.**
  The distinguishing attribute is `report.wasxfail`. The existing skip budget in
  `tests/conftest.py` already handles this; do not "simplify" that condition.
- **Do not add runtime `pytest.skip()` guards.** CI enforces a skip budget of `0`.
  Environment dependence goes in a marker registered in `pyproject.toml`, and
  `--strict-markers` means an unregistered marker fails collection.
- **PySAM raises bare `Exception` on simulation failure**, which is why the existing
  call sites use `except Exception:  # noqa: BLE001`. Keep the `noqa` comment or
  `ruff` will fail the build.
- **`PySAM.Pvwattsv8` has no `.new()` on this version.** Construct with
  `PySAM.Pvwattsv8.new()` at module level (`import PySAM.Pvwattsv8 as pvmod;
  pvmod.new()`) or with `PySAM.Pvwattsv8.default("PVWattsSingleOwner")`. The class
  attribute `Pvwattsv8.new` does not exist, and `AdjustmentFactors.constant` is not
  a settable attribute in 7.1.0.
- **`pv.default("PVWattsSingleOwner")` is not a neutral starting point.** It ships
  `array_type = 2.0` (1-axis tracking), `tilt = 0.0`, `dc_ac_ratio = 1.3`,
  `gcr = 0.3`, `system_capacity = 100000`. Any parameter not explicitly overridden
  is inherited from that configuration.
- **Windows file handles.** `tempfile.NamedTemporaryFile` must be closed before a
  second reader opens the same path on Windows; use `delete=False` plus an explicit
  `unlink` in a `finally` block.
- **Read JSON with `encoding="utf-8-sig"`** throughout, matching the rest of the
  repository, so a UTF-8 BOM from a Windows editor does not break a load.
- **`artifacts/` is git-ignored and regenerable.** Never add a test that reads it
  without the `requires_artifacts` marker, and prefer a tracked fixture.
- **Before deleting a directory or module, grep for the bare name**, not the path
  form — code in this repository builds paths from string segments like
  `REPO_ROOT / "archive" / "colab"`, which a `grep "archive/"` never matches.
- **Run the full test suite after any structural move**, not a subset.
  `--collect-only` is not sufficient; this repository has previously shipped a
  breakage that a subset run missed.
- **`_calibrate_to_target`'s bug is subtle in the common case.** A well-specified
  deal whose annual target fits under the AC cap never triggers redistribution at
  all. Reproduce the defect with an over-specified deal (1.0 MWac against a 6.0 GWh
  target) or the fix will look untestable.

## Verification Strategy

- **TEST-001:** `PYTHONPATH="" REOPT_PYSAM_VN_MAX_SKIPS=0 REOPT_PYSAM_VN_MAX_DESELECTED=46 python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia and not requires_nrel_key and not requires_pysam_resource" -rs -q --cov=reopt_pysam_vn --cov-report=term-missing --cov-fail-under=82`
  → exit code `0`, `0 skipped`, and after PHASE-06 at least `680 passed` with at
  most `21 deselected`.
- **TEST-002:** `ruff check src scripts tests` → `All checks passed!`.
- **TEST-003:** `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` → `Success: no issues found`.
- **TEST-004:** `PYTHONPATH="" python -m pytest tests/python/integration/test_capacity_factor_benchmark.py -q` → `1 passed` with no `xfail` and no `skip` (PHASE-03).
- **TEST-005:** `PYTHONPATH="" python -m pytest tests/python/webapp/test_golden_parity.py -q` → all pass, proving CON-002 held through every phase.
- **TEST-006:** `PYTHONPATH="" python -m pytest tests/python/integration/test_settlement_regression.py tests/python/analysis/test_factory_a_validation.py -m "not network and not requires_artifacts and not golden_machine and not requires_julia and not requires_nrel_key and not requires_pysam_resource" -q` → `25 passed` (PHASE-06).
- **TEST-007:** `PYTHONPATH="" python -m pytest tests/python --collect-only -q -m "requires_artifacts" 2>&1 | tail -1` → at most `10` tests (down from 35).
- **MANUAL-001:** Start the app with
  `PYTHONPATH=src/python python -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000`,
  open `http://127.0.0.1:8000/deals/new`, click a point in the Mekong Delta on the
  map, enter a deal case that is not `DPPA_SAMSUNG_TTC` or `DPPA_CASE_1_NINHSIM`,
  select mode `offsite_dppa`, upload an 8760-row load CSV, and submit. The run page
  must reach a completed state showing settlement metrics, a "Download hourly ledger
  (CSV)" link, and a quality note stating the result is directional and naming the
  substituted solar resource with its distance.
- **MANUAL-002:** Repeat MANUAL-001 with a 35,040-row 15-minute CSV. The run must
  complete and the run page must show a "Load data quality" card reporting the
  resampling.
- **MANUAL-003:** Download the ledger CSV from the completed run and confirm it
  opens in a spreadsheet with 8,760 data rows and the 16 documented columns.
- **OBS-001:** After each phase is pushed, run `gh run list --limit 3` and confirm
  `success` on both `test (3.10)` and `test (3.12)`. Check the run duration: a run
  finishing well under the historical ~1m30s did not reach the test step and is not
  evidence of anything. Record the winning run id in `activeContext.md`.
- **OBS-002:** After PHASE-04, measure the stored artifact:
  `python -c "import json,os,glob; p=sorted(glob.glob('artifacts/webapp/runs/*/result.json'))[-1]; print(os.path.getsize(p))"`
  → under `200000` bytes for a generic offsite run.

## Risks and Alternatives

- **RISK-001:** PHASE-03 changes the generation profile the generic orchestrator
  produces, which changes every settlement number the generic path emits. Nothing in
  CI pins those numbers today, so the change would land invisibly. Mitigation: add
  the exact-value assertions listed in PHASE-03's test specs, and write the
  before/after figures into `reports/2026-08-19-solar-resource-and-array-config.md`
  so a future reader can see what moved and why.
- **RISK-002:** The generic path now answers deals it previously refused, and those
  answers are directional. A reader could mistake a flagged approximation for a
  validated result. Mitigation: `quality.basis == "directional"`,
  `quality.warnings`, the substituted-resource disclosure from PHASE-03, and the
  defaulted-field list from PHASE-02's `extraction_meta` all travel with the result
  and must be rendered on the run page, not only present in the JSON.
- **RISK-003:** PHASE-02 and PHASE-03 both touch
  `analysis/orchestrators/generic_vn_dppa.py`'s neighbourhood and could conflict if
  worked in parallel. Mitigation: they are sequenced, and their file sets are
  disjoint — PHASE-02 touches `analysis/extracted.py`, `reopt/preprocess.py`,
  `webapp/service.py`, and `analysis/__main__.py`; PHASE-03 touches
  `generic_vn_dppa.py`, `pysam/pvwatts_battery.py`, and `dppa_samsung_ttc.py`. If
  they are run in parallel, merge PHASE-02 first.
- **RISK-004:** Tightening the coverage floor and deselect budget in PHASE-01 could
  block PHASE-02's first commit if the new module lands before its tests.
  Mitigation: write the tests in the same commit as the module, which the phase's
  task ordering already implies.
- **RISK-005:** The `hourly_ledger` removal in PHASE-04 breaks an external consumer
  that reads `result.json` from a stored run directory. Mitigation: old run
  directories are untouched, the ledger is still produced (as CSV in the same
  directory), and the webapp README documents the new layout.
- **ALT-001:** *Refuse the run when no solar resource is near the site*, instead of
  substituting and disclosing. Not chosen: it would reintroduce the hard error that
  the generic fallback orchestrator was built to remove, and this repository's
  established pattern is a flagged approximation over a refusal (the market-price
  proxy already works this way).
- **ALT-002:** *Download a per-site solar resource file from the NREL API on
  demand.* Not chosen for this plan: it requires a live API key, makes results
  non-deterministic across environments, and would make CI network-dependent. It is
  a natural follow-on once the disclosure machinery from PHASE-03 exists.
- **ALT-003:** *Store the hourly ledger as Parquet rather than CSV.* Not chosen: it
  would add a `pyarrow` dependency for a file whose main consumer is an analyst
  opening it in a spreadsheet. Revisit if programmatic multi-run loading appears.
- **ALT-004:** *Truncate or downsample the hourly ledger to daily aggregates.* Not
  chosen: the hourly ledger is the audit trail for a contract-for-difference
  settlement and a counterparty will ask for it hour by hour.
- **ALT-005:** *Regenerate the `artifacts/` files inside CI instead of committing
  fixtures.* Not chosen: the Saigon18 solve requires an NREL API key and several
  minutes of solver time, which would make every push network-dependent and slow.

## Suggested Next Step

Execute PHASE-01. It has no dependencies, changes no analytical behaviour, and
installs the two ratchets (deselect budget, coverage floor) that make every later
phase measurable. Confirm its exit criteria — a green full-suite run with both
budgets enforced, and `gh run list --limit 3` showing `success` on both matrix legs
— before starting PHASE-02.
