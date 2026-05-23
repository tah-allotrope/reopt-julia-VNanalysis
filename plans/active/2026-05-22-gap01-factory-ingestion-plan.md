---
title: "GAP-01: Factory Data Ingestion Pipeline"
date: "2026-05-22"
status: "complete"
request: "Generic factory 8760 load data ingestion pipeline for client demo with real factory data"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-05-18_practical-refinements-operational-engine.md"
  - "reports/2026-05-22-client-demo-gap-analysis.md"
---

# Plan: GAP-01 — Factory Data Ingestion Pipeline

## Objective
Build a generic factory data ingestion module that accepts CSV, XLSX, or JSON load files, validates and normalizes them to 8760 hourly kW series, extracts operational metadata (peak demand, annual consumption, load factor, TOU classification, industry archetype), and handles partial data via REopt `simulated_load` API fallback. This is the critical-path blocker for the client demo — without generic ingestion, every new factory requires a custom extraction script.

## Context Snapshot
- **Current state:** Three bespoke extraction scripts exist: `scripts/python/reopt/extract_excel_inputs.py` (saigon18-specific, openpyxl, hardcoded column layout), `scripts/python/integration/build_ninhsim_extracted_inputs.py` (ninhsim CSV, hardcoded `Load_kW` column), `scripts/python/integration/rank_case_study_offtakers.py` (multi-format but ranking-specific, contains reusable `clean_numeric()`, `interpolate_missing()`, `sanitize_load_series()`, `read_csv_loads()`, `read_xlsx_loads()` functions).
- **Desired state:** A single `ingest_factory_load()` function in a new shared module that any downstream workflow can call with a file path and optional column-mapping hints, receiving back a validated 8760 kW series plus a metadata summary artifact.
- **Key repo surfaces:** `scripts/python/integration/rank_case_study_offtakers.py` (source of reusable cleaning functions), `scripts/python/reopt/extract_excel_inputs.py` (extraction patterns), `src/python/reopt_pysam_vn/reopt/preprocess.py` (TOU tariff builder for classification), `docs/data_and_api.md` (REopt `simulated_load` API endpoint at `https://developer.nlr.gov/api/reopt/stable/simulated_load/`), `data/vietnam/vn_tariff_2025.json` (TOU window definitions for load classification).
- **Out of scope:** Web UI or API service layer, real-time streaming ingestion, non-electricity load profiles (gas, water), load forecasting or prediction, modification of existing case-study scripts (they continue to work as-is).

## Research Inputs
- `research/2026-05-18_practical-refinements-operational-engine.md` — Confirms 119 scripts in `scripts/python/` with no shared ingestion pathway; workflow orchestration is the operational bottleneck. Factory ingestion is the first shared module that breaks this pattern.
- `reports/2026-05-22-client-demo-gap-analysis.md` — GAP-01 definition: severity CRITICAL, blocks demo story, effort 3-4 phases.

## Assumptions and Constraints
- **ASM-001:** Input files contain at minimum an hourly load column in kW. Files may also contain timestamps, PV generation, FMP, or other columns — the ingestion module should extract load and ignore the rest unless explicitly mapped.
- **ASM-002:** The module should produce a standardized output JSON artifact compatible with the existing `data/interim/<project>/` pattern, so downstream scenario builders can consume it without changes.
- **ASM-003:** Industry archetype classification is heuristic (based on load-shape features like peak-to-trough ratio, weekend dip, night-shift presence) — not ML-based.
- **CON-001:** Some factory datasets may have fewer than 8760 rows (e.g., monthly bills, 15-minute intervals, partial years). The module must detect the resolution and either resample or fall back to `simulated_load`.
- **CON-002:** REopt `simulated_load` API requires `NREL_DEVELOPER_API_KEY` and an internet connection. Offline fallback must exist for demo environments.
- **DEC-001:** The ingestion module lives in `src/python/reopt_pysam_vn/ingestion/` as a new package, not inside `reopt/` or `integration/`.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Extract and generalize cleaning/normalization functions into shared ingestion module | None | `src/python/reopt_pysam_vn/ingestion/loader.py`, unit tests |
| PHASE-02 | Add metadata extraction, TOU classification, and industry archetype detection | PHASE-01 | `src/python/reopt_pysam_vn/ingestion/metadata.py`, metadata tests |
| PHASE-03 | Add partial-data handling (sub-hourly resampling, monthly-to-8760 synthesis, simulated_load fallback) | PHASE-01 | `src/python/reopt_pysam_vn/ingestion/synthesize.py`, integration tests |
| PHASE-04 | Add CLI entrypoint, summary artifact writer, and validation against all 6 existing case studies | PHASE-01, PHASE-02, PHASE-03 | `scripts/python/ingest_factory_load.py`, validated artifacts for all 6 case studies |

## Detailed Phases

### PHASE-01 - Generic Load Normalization Module
**Goal**
Extract the proven cleaning functions from `rank_case_study_offtakers.py` into a reusable ingestion module, generalize the column-detection logic, and support CSV, XLSX, and JSON input formats with flexible column mapping.

**Tasks**
- [ ] TASK-01-01: Create `src/python/reopt_pysam_vn/ingestion/__init__.py` and `src/python/reopt_pysam_vn/ingestion/loader.py` with `ingest_factory_load(path, column_hint=None, timestamp_column=None) -> FactoryLoadResult`.
- [ ] TASK-01-02: Move `clean_numeric()`, `interpolate_missing()`, `sanitize_load_series()` from `rank_case_study_offtakers.py` into `loader.py` as the shared cleaning pipeline. Do not modify the original script — it continues working via its own copy.
- [ ] TASK-01-03: Implement format detection: `.csv` → `read_csv_loads()`, `.xlsx`/`.xlsm` → `read_xlsx_loads()`, `.json` → `read_json_loads()`. For CSV/XLSX, auto-detect the load column by scanning headers for patterns like `Load_kW`, `load`, `demand`, `consumption`, `kW`, or fall back to the first numeric column.
- [ ] TASK-01-04: Implement `FactoryLoadResult` dataclass: `loads_kw: list[float]` (8760), `cleaning_summary: dict` (missing count, interpolated count, clipped negatives, original row count), `source_path: str`, `source_format: str`, `detected_column: str`.
- [ ] TASK-01-05: Add validation gate: if final series length is not 8760, raise `LoadLengthError` with diagnostic info (actual length, likely resolution). Do not attempt resampling in this phase — that's PHASE-03.
- [ ] TASK-01-06: Add `tests/python/ingestion/test_loader.py` with failing-then-passing tests for: CSV ingestion (ninhsim sample), XLSX ingestion (regina sample), JSON ingestion (saigon18 scenario with embedded `loads_kw`), auto-column detection, negative clipping, interpolation, and 8760-length validation.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/ingestion/loader.py` — New generic loader module.
- `src/python/reopt_pysam_vn/ingestion/__init__.py` — Package init, exports `ingest_factory_load`.
- `tests/python/ingestion/test_loader.py` — Unit tests for all format paths.
- `scripts/python/integration/rank_case_study_offtakers.py` — Source of cleaning functions (read-only reference).

**Dependencies**
- None

**Exit Criteria**
- [ ] `ingest_factory_load("scenarios/case_studies/ninhsim/NinhsimSample.csv")` returns a `FactoryLoadResult` with 8760 loads and cleaning summary.
- [ ] `ingest_factory_load("scenarios/case_studies/regina/Regina.xlsx")` returns a `FactoryLoadResult` with 8760 loads.
- [ ] `python -m pytest tests/python/ingestion/test_loader.py -q` passes all tests.

**Phase Risks**
- **RISK-01-01:** Some case-study files may have non-standard layouts (e.g., saigon18 XLSX has load in column D, not column A). Mitigate by supporting explicit `column_hint` parameter and documenting auto-detection limitations.

### PHASE-02 - Metadata Extraction and Load Classification
**Goal**
Compute operational metadata from the ingested 8760 series and classify the factory's load shape for downstream matching and reporting.

**Tasks**
- [ ] TASK-02-01: Create `src/python/reopt_pysam_vn/ingestion/metadata.py` with `extract_load_metadata(loads_kw, year=2024) -> LoadMetadata`.
- [ ] TASK-02-02: Implement `LoadMetadata` dataclass with fields: `peak_demand_kw`, `annual_consumption_mwh`, `average_demand_kw`, `load_factor` (average/peak), `min_demand_kw`, `daytime_avg_kw` (06:00-18:00), `nighttime_avg_kw` (18:00-06:00), `weekend_avg_kw`, `weekday_avg_kw`.
- [ ] TASK-02-03: Add TOU classification: using `build_vietnam_tariff()` from `preprocess.py`, compute `peak_hour_consumption_mwh`, `offpeak_hour_consumption_mwh`, `normal_hour_consumption_mwh`, `peak_share_pct`, `offpeak_share_pct` for the factory's load under Decision 963 windows.
- [ ] TASK-02-04: Add industry archetype classifier: `classify_industry_archetype(loads_kw, year) -> str` returning one of `single_shift_factory`, `two_shift_factory`, `continuous_process`, `commercial_daytime`, `commercial_extended`. Classification uses: weekend-to-weekday ratio (< 0.3 → single shift), night-to-day ratio (> 0.7 → continuous), peak-hour concentration.
- [ ] TASK-02-05: Add `tests/python/ingestion/test_metadata.py` with tests for: metadata computation on known saigon18 profile (peak ~30 MW, annual ~184 GWh), archetype classification on ninhsim (expected: continuous_process or two_shift), TOU classification under Decision 963.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/ingestion/metadata.py` — Metadata extraction and classification.
- `src/python/reopt_pysam_vn/reopt/preprocess.py` — Read-only dependency for `build_vietnam_tariff()`.
- `data/vietnam/vn_tariff_2025.json` — TOU window definitions for classification.
- `tests/python/ingestion/test_metadata.py` — Metadata and classification tests.

**Dependencies**
- PHASE-01 (requires `FactoryLoadResult`)

**Exit Criteria**
- [ ] `extract_load_metadata()` on saigon18 loads returns `peak_demand_kw` within 1% of 30,246 kW and `annual_consumption_mwh` within 1% of 184,260 MWh.
- [ ] `classify_industry_archetype()` correctly classifies at least 4 of 6 existing case studies against manually verified labels.
- [ ] TOU classification produces non-zero `peak_share_pct` under Decision 963 for any industrial load.

**Phase Risks**
- **RISK-02-01:** Archetype classification heuristics may misclassify edge cases (e.g., a mall with extended hours looks like a two-shift factory). Mitigate by allowing manual override in downstream workflows and labeling classification as `heuristic` in metadata.

### PHASE-03 - Partial Data Handling and Synthesis
**Goal**
Handle input data that is not already 8760 hourly kW: sub-hourly resampling, sub-annual extrapolation, and monthly-to-8760 synthesis via REopt `simulated_load` API.

**Tasks**
- [ ] TASK-03-01: Create `src/python/reopt_pysam_vn/ingestion/synthesize.py` with resolution detection: if row count is 35040 (15-min) or 17520 (30-min), resample to 8760 hourly averages. If row count is 12 (monthly) or 52 (weekly), flag for API synthesis.
- [ ] TASK-03-02: Implement `synthesize_from_monthly(monthly_kwh, latitude, longitude, building_type) -> list[float]` calling the REopt `simulated_load` API at `https://developer.nlr.gov/api/reopt/stable/simulated_load/` with `doe_reference_name` and `annual_kwh` scaling.
- [ ] TASK-03-03: Add offline fallback: if API is unreachable or no API key is configured, generate a flat-scaled 8760 from monthly totals using a generic industrial load shape (derived from the saigon18 normalized profile stored as a reference series in `data/vietnam/reference_load_shapes/industrial_south.json`).
- [ ] TASK-03-04: Create `data/vietnam/reference_load_shapes/industrial_south.json` by normalizing the saigon18 8760 load profile to a per-unit shape (each hour as fraction of annual total).
- [ ] TASK-03-05: Update `ingest_factory_load()` in `loader.py` to route through synthesis when the input is not 8760. Add `synthesis_method` field to `FactoryLoadResult`: `none` (was already 8760), `resampled_15min`, `resampled_30min`, `api_simulated_load`, `offline_archetype_scaled`.
- [ ] TASK-03-06: Add `tests/python/ingestion/test_synthesize.py` with tests for: 15-min resampling (create a synthetic 35040-row input), monthly-to-8760 API call (mocked), offline fallback shape.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/ingestion/synthesize.py` — Resolution detection and synthesis logic.
- `src/python/reopt_pysam_vn/ingestion/loader.py` — Updated to route through synthesis.
- `data/vietnam/reference_load_shapes/industrial_south.json` — Normalized reference shape for offline fallback.
- `tests/python/ingestion/test_synthesize.py` — Synthesis and resampling tests.

**Dependencies**
- PHASE-01 (requires `ingest_factory_load()` and `FactoryLoadResult`)

**Exit Criteria**
- [ ] A 35040-row CSV (15-min intervals) is correctly resampled to 8760 hourly values.
- [ ] A 12-row monthly CSV triggers API synthesis (or offline fallback) and produces 8760 values.
- [ ] `FactoryLoadResult.synthesis_method` correctly reflects the path taken.

**Phase Risks**
- **RISK-03-01:** REopt `simulated_load` API may not have `doe_reference_name` values representative of Vietnamese industrial loads. Mitigate by using the offline archetype fallback as primary and API as secondary for Vietnam-specific profiles.
- **RISK-03-02:** Normalized reference shape from saigon18 may not generalize well to different factory types. Mitigate by creating 2-3 reference shapes (industrial, commercial, continuous) if time permits.

### PHASE-04 - CLI Entrypoint, Artifact Writer, and Case Study Validation
**Goal**
Wire the ingestion module into a runnable CLI script, produce standardized output artifacts compatible with downstream workflows, and validate against all 6 existing case studies.

**Tasks**
- [ ] TASK-04-01: Create `scripts/python/ingest_factory_load.py` CLI entrypoint accepting `--input <path>`, `--output <path>`, `--column <name>`, `--year <int>`, `--project-name <str>`, `--customer-type <str>`, `--voltage-level <str>`, `--region <str>`.
- [ ] TASK-04-02: Implement artifact writer producing a JSON output compatible with `data/interim/<project>/` pattern: `{"_meta": {...}, "site": {...}, "loads_kw": [...], "metadata": {...}, "cleaning": {...}, "classification": {...}}`.
- [ ] TASK-04-03: Run ingestion against all 6 existing case studies and verify output: saigon18 (from scenario JSON), ninhsim (from CSV), north_thuan (from scenario JSON), regina (from XLSX), verdant (from CSV), emivest (from CSV).
- [ ] TASK-04-04: Add `tests/python/ingestion/test_case_study_validation.py` that ingests each of the 6 case studies and asserts: 8760 length, positive peak demand, non-zero annual consumption, valid archetype classification.
- [ ] TASK-04-05: Add top-level wrapper at `scripts/python/ingest_factory_load.py` (thin shim to `scripts/python/integration/ingest_factory_load.py`).
- [ ] TASK-04-06: Update `README.md` with a "Factory Data Ingestion" section showing the CLI usage and supported formats.

**Files / Surfaces**
- `scripts/python/integration/ingest_factory_load.py` — Canonical CLI entrypoint.
- `scripts/python/ingest_factory_load.py` — Top-level convenience wrapper.
- `tests/python/ingestion/test_case_study_validation.py` — Cross-case-study validation tests.
- `README.md` — Updated with ingestion documentation.

**Dependencies**
- PHASE-01, PHASE-02, PHASE-03

**Exit Criteria**
- [ ] `python scripts/python/ingest_factory_load.py --input scenarios/case_studies/ninhsim/NinhsimSample.csv --output data/interim/test/test_ingestion.json` produces a valid artifact.
- [ ] All 6 case studies produce valid ingestion artifacts with correct metadata.
- [ ] `python -m pytest tests/python/ingestion/ -q` passes all tests across all phases.

**Phase Risks**
- **RISK-04-01:** Some case studies may have edge-case formats that break auto-detection (e.g., emivest CSV with very peaky profile may trigger false cleaning warnings). Mitigate by reviewing cleaning summaries and adjusting thresholds if needed.

## Verification Strategy
- **TEST-001:** Run `python -m pytest tests/python/ingestion/ -q` after each phase to confirm cumulative test passage.
- **TEST-002:** Run `python scripts/python/ingest_factory_load.py --input scenarios/case_studies/ninhsim/NinhsimSample.csv --output /tmp/test.json` and inspect the output artifact manually.
- **TEST-003:** Run the full test suite `.\tests\run_all_tests.ps1 -SkipLayer4` to confirm no regressions in existing code.
- **MANUAL-001:** Visually inspect metadata output for saigon18 (peak ~30 MW, ~184 GWh annual, continuous_process or two_shift archetype) to confirm reasonableness.
- **MANUAL-002:** Compare ingestion output for ninhsim against the existing `data/interim/ninhsim/ninhsim_extracted_inputs.json` to confirm load series match.

## Risks and Alternatives
- **RISK-001:** Auto-column detection may fail on factory files with non-English headers (Vietnamese column names). Mitigate by supporting explicit `--column` override and documenting the auto-detection heuristic.
- **RISK-002:** The `simulated_load` API at `developer.nlr.gov` may have availability issues during the sprint (brownout period before May 29 expiry). Mitigate with offline fallback as the primary synthesis path.
- **ALT-001:** Instead of a shared module, continue writing per-factory extraction scripts. Not chosen because it does not scale for client demos and creates maintenance burden.

## Grill Me
1. **Q-001:** Should the ingestion module support multi-sheet Excel workbooks where load data may be on any named sheet, or only single-sheet / first-sheet?
   - **Recommended default:** First sheet only, with `--sheet <name>` override.
   - **Why this matters:** Multi-sheet auto-detection adds complexity and risk of picking the wrong sheet.
   - **If answered differently:** If multi-sheet is required, add a sheet-scanning step that looks for 8760-row numeric columns across all sheets.

2. **Q-002:** Should the archetype classifier produce confidence scores, or just a single label?
   - **Recommended default:** Single label with a `confidence` field (`high`, `medium`, `low`) based on how cleanly the load shape fits the archetype thresholds.
   - **Why this matters:** Low-confidence classifications should trigger a manual review prompt in downstream workflows.
   - **If answered differently:** If scores are needed, return all archetype scores and let downstream pick.

## Suggested Next Step
Answer the Grill Me questions, then begin implementation with PHASE-01 (the shared cleaning module is the foundation everything else builds on).
