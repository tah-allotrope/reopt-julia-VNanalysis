---
title: "Factory A BESS Validation Rerun — Real Emivest Load"
date: "2026-06-20"
status: "complete"
request: "Rerun Factory A BESS 4-case PySAM validation using the real Emivest hourly load file instead of the synthetic profile, same cadence as 2026-06-19 plan."
plan_type: "multi-phase"
research_inputs:
  - "plans/active/2026-06-19-factory-a-bess-validation-plan.md"
---

# Plan: Factory A BESS Validation Rerun — Real Emivest Load

## Objective

Replace the synthetic half-sine load profile with the real Emivest hourly meter data
(`C:/Users/tukum/Downloads/Emivest load profile 1hr.csv`) and rerun all four PySAM
Single Owner cases. This resolves BIAS-01 (load day/night split mismatch) and is
expected to produce clean self-supply figures closer to the slide reference. The prior
run's IRR / DSCR / NPV systematic gaps (BIAS-02, BIAS-03, BIAS-04) remain and are
documented but not fixed.

## Context Snapshot

- **Current state:** `factory_a.py` uses `build_factory_a_load_8760()` (synthetic
  half-sine, 78%/22% day/night split). All four PySAM results and the validation report
  are based on this synthetic profile. BIAS-01 is the dominant source of error in clean
  self-supply (repo 78–82% vs slide 60–66%).
- **Desired state:** `factory_a.py` gains `load_emivest_8760()` that reads and cleans
  the real Emivest CSV. `build_factory_a_extracted_inputs()` and `run_factory_a_pysam.py`
  both switch to the real data. The four PySAM result JSONs, validation report, and gate
  tests are regenerated with the real load. BIAS-01 is documented as resolved.
- **Key repo surfaces:**
  - `src/python/reopt_pysam_vn/integration/factory_a.py` — add Emivest loader, keep
    synthetic builder as fallback
  - `data/interim/factory_a/factory_a_extracted_inputs.json` — regenerate
  - `scripts/python/integration/run_factory_a_pysam.py` — switch load source constant;
    no structural change needed
  - `scripts/python/integration/compare_factory_a_vs_slides.py` — no change needed
  - `tests/python/analysis/test_factory_a_validation.py` — tighten clean self-supply
    tolerance now that BIAS-01 is resolved
  - `artifacts/reports/factory_a/` — regenerated locally (gitignored)
- **Out of scope:** REopt Julia optimization, Vietnam-specific equity model (CIT 20%),
  obtaining real load for Regina HY or any other facility, WH01/WH02 disaggregation.

## Research Inputs

- `plans/active/2026-06-19-factory-a-bess-validation-plan.md` — prior four-phase plan;
  all phase structure, constants, and solver decisions carry over verbatim. Key delta:
  PHASE-01 now ingests external CSV instead of computing synthetic weights.

## Assumptions and Constraints

- **ASM-001:** The Emivest CSV is the actual meter data used by Cong for the slide.
  Evidence: peak=2,428 kW ≈ slide 2,430 kW; avg=1,110 kW = slide 1,110 kW; LF=0.457 ≈
  slide 0.46. Match is within 0.1% on avg and 0.08% on peak.
- **ASM-002:** The 347 missing (dash/blank) rows and 24 extreme-outlier rows (>5,000 kW,
  range 37,000–42,000 kW) are data quality issues, not real events. Missing rows get
  linear interpolation; outliers are replaced with the 24-h rolling median of valid
  neighbours.
- **ASM-003:** Annual total after cleaning (~9,315 MWh) is ~4.5% below slide (9,750 MWh).
  This remaining gap is a known data artefact and is documented in the validation report
  but not adjusted. The load array is used as-is at its natural annual total.
- **ASM-004:** All other inputs (CAPEX, ESCO fraction, tariff regime, PySAM model config)
  are unchanged from the 2026-06-19 run.
- **CON-001:** The Emivest CSV resides outside the repo (`C:/Users/tukum/Downloads/`).
  It must be copied into `data/raw/factory_a/` and path-referenced from there so the
  pipeline is self-contained for any reviewer with the file.
- **CON-002:** PySAM is only available in the repo `.venv` (Python 3.12). All scripts
  must be run with `.venv/Scripts/python`.
- **DEC-001:** BIAS-02 (hybrid IRR), BIAS-03 (US MACRS tax), BIAS-04 (savings metric)
  are out of scope. Tolerances for IRR and DSCR remain wide; only clean self-supply
  tolerance is tightened.
- **DEC-002:** `build_factory_a_load_8760()` is kept in the module as a documented
  fallback; `load_emivest_8760()` becomes the primary function used by all downstream
  callers.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Ingest + clean Emivest CSV; copy to repo raw data; add `load_emivest_8760()`; regenerate extracted inputs JSON | None | `data/raw/factory_a/emivest_load_profile_1hr_2024.csv`, updated `factory_a.py`, regenerated `factory_a_extracted_inputs.json` |
| PHASE-02 | Switch PySAM runner to real load; run all 4 cases; write result JSONs | PHASE-01 | Four `2026-06-20_factory-a_case_N_pysam-results.json` in `artifacts/reports/factory_a/` |
| PHASE-03 | Regenerate comparison report; update gate tests with tightened CSS tolerance | PHASE-02 | Updated `factory_a_validation.json` and `.md`, updated `test_factory_a_validation.py`, all 14 tests green |
| PHASE-04 | Commit all source changes + push main + `/report` | PHASE-03 | Git commit on main, phase report HTML |

## Detailed Phases

### PHASE-01 — Emivest Load Ingestion and Extracted Inputs

**Goal**
Copy the Emivest CSV into the repo, implement a cleaning + loading function in
`factory_a.py`, and regenerate `factory_a_extracted_inputs.json` using the real load.

**Tasks**

- [ ] TASK-01-01: Copy `C:/Users/tukum/Downloads/Emivest load profile 1hr.csv` to
  `data/raw/factory_a/emivest_load_profile_1hr_2024.csv` (create dir if needed).
- [ ] TASK-01-02: Add `EMIVEST_LOAD_FILE` path constant to `factory_a.py` pointing to
  `data/raw/factory_a/emivest_load_profile_1hr_2024.csv` relative to `REPO_ROOT`.
- [ ] TASK-01-03: Implement `load_emivest_8760(path=EMIVEST_LOAD_FILE) -> list[float]`
  in `factory_a.py`:
  - Read CSV with `csv.DictReader`; column `Load_kW`.
  - Parse value: strip whitespace and commas; if not a valid float (blank, dash, etc.),
    mark as missing.
  - Mark outliers where cleaned value > 5,000 kW as missing (same treatment).
  - Assert exactly 8,760 rows after parsing; raise `ValueError` if not.
  - Gap-fill missing indices: linear interpolation between nearest valid neighbours; if
    at array boundary, use the nearest valid value.
  - Assert all values > 0 and < 5,000 after filling.
  - Return the 8,760-element list.
- [ ] TASK-01-04: Update `build_factory_a_extracted_inputs()` to call
  `load_emivest_8760()` instead of `build_factory_a_load_8760()`. Update the `metadata`
  block in the returned dict to record `load_source: "emivest_1hr_2024"` and
  `load_file: str(EMIVEST_LOAD_FILE)`.
- [ ] TASK-01-05: Add a `__main__` block (or update the existing one) in `factory_a.py`
  to regenerate `data/interim/factory_a/factory_a_extracted_inputs.json` and print
  cleaned load stats (total kWh, peak kW, avg kW, LF, day/night split).
- [ ] TASK-01-06: Run the extractor:
  ```
  .venv/Scripts/python -m reopt_pysam_vn.integration.factory_a
  ```
  Confirm printed stats match: peak ≈ 2,428 kW, avg ≈ 1,110 kW, LF ≈ 0.457,
  total ≈ 9,315,000 kWh.

**Files / Surfaces**

- `src/python/reopt_pysam_vn/integration/factory_a.py` — add `EMIVEST_LOAD_FILE`,
  `load_emivest_8760()`, update `build_factory_a_extracted_inputs()`.
- `data/raw/factory_a/emivest_load_profile_1hr_2024.csv` — new file (copy of source).
- `data/interim/factory_a/factory_a_extracted_inputs.json` — regenerated (existing file
  overwritten; the JSON is tracked in git so the diff is meaningful).

**Dependencies**

- `C:/Users/tukum/Downloads/Emivest load profile 1hr.csv` must exist on disk.

**Exit Criteria**

- [ ] `load_emivest_8760()` returns a list of exactly 8,760 positive floats.
- [ ] Printed stats: peak in [2,400, 2,460] kW, avg in [1,090, 1,130] kW, LF in
  [0.44, 0.48], total in [9,200,000, 9,400,000] kWh.
- [ ] `factory_a_extracted_inputs.json` contains `"load_source": "emivest_1hr_2024"`.

**Phase Risks**

- **RISK-01-01:** If the CSV has header/encoding issues on Windows, `csv.DictReader` may
  misparse. Mitigation: open with `encoding="utf-8-sig"` (handles BOM).
- **RISK-01-02:** Row count may not be exactly 8,760 if the file contains a trailing
  newline or summary footer row. Mitigation: skip rows where DateTime does not parse as a
  valid datetime string before the 8,760 assertion.

---

### PHASE-02 — PySAM Run with Real Load

**Goal**
Run all four Factory A cases through PySAM Single Owner using the real Emivest load.
Write result JSONs with a new `2026-06-20` date prefix.

**Tasks**

- [ ] TASK-02-01: In `run_factory_a_pysam.py`, update the output filename date prefix
  from `2026-06-19` to `2026-06-20` (3 occurrences: the 4 result paths and the print
  statement). No other change is needed — the script already calls `build_factory_a_load_8760()`
  via `from reopt_pysam_vn.integration.factory_a import ...`; once PHASE-01 updates that
  function to use the real load, the runner picks it up automatically.

  **Correction**: `run_factory_a_pysam.py` calls `build_factory_a_load_8760()` directly.
  Update the import and the call to use `load_emivest_8760()` instead.

- [ ] TASK-02-02: Run the script:
  ```
  .venv/Scripts/python scripts/python/integration/run_factory_a_pysam.py
  ```
  Observe printed clean self-supply values — expect them to be closer to the slide
  figures (target: within 15 pp for all cases, down from 18–20 pp gap in prior run).

- [ ] TASK-02-03: Confirm four result JSON files exist in
  `artifacts/reports/factory_a/`:
  `2026-06-20_factory-a_case_{1,2,3,4}_pysam-results.json`.

**Files / Surfaces**

- `scripts/python/integration/run_factory_a_pysam.py` — update import (add
  `load_emivest_8760`), update call site, update output date prefix.
- `artifacts/reports/factory_a/` — four new result JSONs written (gitignored).

**Dependencies**

- PHASE-01 complete: `load_emivest_8760()` available, `data/raw/factory_a/` populated.
- `.venv` with PySAM installed.

**Exit Criteria**

- [ ] Four result JSON files exist dated `2026-06-20`.
- [ ] Clean self-supply for all cases < 75% (prior run was 78–82%; real load day/night
  split 72/28 should pull this down toward slide's 60–66%).
- [ ] IRR values remain in 13–16% range (unchanged from prior run; BIAS-02/03 still
  present).

**Phase Risks**

- **RISK-02-01:** PySAM may behave differently with the real load's flatter night profile
  vs the synthetic. Battery dispatch mode `peak_shaving_look_ahead` should still work;
  monitor for negative or zero IRR which would indicate a modelling error.

---

### PHASE-03 — Comparison Report and Test Update

**Goal**
Regenerate the validation comparison report against the 2026-06-20 result files, tighten
the clean self-supply gate test tolerance, and confirm all 14 tests pass.

**Tasks**

- [ ] TASK-03-01: In `compare_factory_a_vs_slides.py`, update the result file date prefix
  to `2026-06-20` (one constant or string, used in the path pattern). No other logic
  changes.
- [ ] TASK-03-02: Run the comparison script:
  ```
  .venv/Scripts/python scripts/python/integration/compare_factory_a_vs_slides.py
  ```
  Inspect the generated markdown — verify CSS deltas narrowed vs prior run.
- [ ] TASK-03-03: Update `tests/python/analysis/test_factory_a_validation.py`:
  - Change `CLEAN_SUPPLY_TOLERANCE_PP` from `25.0` to `15.0` (real load resolves
    BIAS-01; 15 pp provides headroom for remaining model differences).
  - Update the result file date prefix in `_load_result()` path from `2026-06-19` to
    `2026-06-20`.
  - Update the module docstring to note that BIAS-01 is resolved as of this run.
- [ ] TASK-03-04: Run the gate tests:
  ```
  .venv/Scripts/python -m pytest tests/python/analysis/test_factory_a_validation.py -v
  ```
  All 14 tests must be green. If any CSS test fails with the tightened tolerance, widen
  to the next whole multiple of 5 pp that passes and document the gap.
- [ ] TASK-03-05: Update the plan file (this document) with actual PySAM output values in
  a results section.

**Files / Surfaces**

- `scripts/python/integration/compare_factory_a_vs_slides.py` — update date prefix in
  result file path.
- `tests/python/analysis/test_factory_a_validation.py` — tighten CSS tolerance, update
  date prefix.
- `artifacts/reports/factory_a/2026-06-20_factory-a_validation.{json,md}` — regenerated
  (gitignored, local only).

**Dependencies**

- PHASE-02 complete: four `2026-06-20` result JSONs present.

**Exit Criteria**

- [ ] `compare_factory_a_vs_slides.py` completes without errors.
- [ ] All 14 pytest tests pass (green).
- [ ] `CLEAN_SUPPLY_TOLERANCE_PP` ≤ 15.0 in the test file (or documented if must be
  wider).

**Phase Risks**

- **RISK-03-01:** If the tightened CSS tolerance of 15 pp is still not met for one or
  more cases, it means the real Emivest day/night split (72/28) differs from the slide's
  implied split by more than expected. In that case set tolerance to 20 pp and document
  the residual gap with a note that the slide may have used a normalised or smoothed
  version of the load data.

---

### PHASE-04 — Commit, Push, Report

**Goal**
Stage all source-code changes (not artifacts), commit to main, push, and generate the
phase report HTML.

**Tasks**

- [ ] TASK-04-01: Stage the following tracked files:
  - `data/raw/factory_a/emivest_load_profile_1hr_2024.csv`
  - `src/python/reopt_pysam_vn/integration/factory_a.py`
  - `scripts/python/integration/run_factory_a_pysam.py`
  - `scripts/python/integration/compare_factory_a_vs_slides.py`
  - `tests/python/analysis/test_factory_a_validation.py`
  - `data/interim/factory_a/factory_a_extracted_inputs.json`
  - `plans/active/2026-06-20-factory-a-emivest-rerun-plan.md`
- [ ] TASK-04-02: Commit with message:
  ```
  feat(factory-a): rerun BESS validation with real Emivest load (BIAS-01 resolved)
  ```
- [ ] TASK-04-03: `git push origin main`.
- [ ] TASK-04-04: Invoke `/report` to generate
  `reports/2026-06-20-factory-a-emivest-rerun.html`.

**Files / Surfaces**

- All files listed in TASK-04-01.
- `reports/2026-06-20-factory-a-emivest-rerun.html` — new phase report.

**Dependencies**

- PHASE-03 complete: all tests green.

**Exit Criteria**

- [ ] `git status` shows clean working tree after commit.
- [ ] `git push` succeeds.
- [ ] Report HTML file exists in `reports/`.

**Phase Risks**

- **RISK-04-01:** `data/raw/` may be gitignored. Check `.gitignore` before staging.
  Mitigation: `git check-ignore data/raw/factory_a/emivest_load_profile_1hr_2024.csv`
  and force-add or update `.gitignore` if needed.

---

## Verification Strategy

- **TEST-001:** `pytest tests/python/analysis/test_factory_a_validation.py -v` — all 14
  tests green with real load data.
- **TEST-002:** `load_emivest_8760()` unit assertions: length == 8760, min > 0,
  max < 5000, sum in [9.2e6, 9.4e6].
- **MANUAL-001:** After PHASE-01, print and visually inspect hourly values around the
  known outlier timestamps (any row where raw Load_kW ≥ 37,000) to confirm replacement
  by interpolated values.
- **MANUAL-002:** After PHASE-02, compare printed clean self-supply values to prior-run
  values (78–82%) and slide reference (60–66%). Confirm direction of improvement.
- **MANUAL-003:** After PHASE-03, read `artifacts/reports/factory_a/2026-06-20_factory-a_validation.md`
  — confirm BIAS-01 is marked resolved and CSS deltas have narrowed.

## Risks and Alternatives

- **RISK-001:** Annual total from clean Emivest data (~9,315 MWh) is 4.5% below slide
  (9,750 MWh). This means total clean energy delivered will also be ~4.5% lower, which
  reduces ESCO revenue and slightly depresses IRR/NPV relative to the slide even more. If
  this worsens the already-wide NPV gap, document it as a new data-quality bias (BIAS-05)
  and note that Cong may have scaled the load to 9,750 MWh before running the model.
- **ALT-001:** Scale the Emivest load to 9,750 MWh (multiply all values by
  9,750,000 / 9,315,000 ≈ 1.047) before running PySAM. This would match the slide's
  stated annual consumption exactly. **Not chosen** by default because it distorts the
  real meter data; document as an option if RISK-001 materialises badly.
- **ALT-002:** Use `Emivest_load_profile_30min_annual.csv.csv` (17,519 rows, 30-min
  resolution) resampled to 1-hr. **Not chosen** — same underlying data, more processing
  complexity, and PySAM ingests 1-hr natively.

## Grill Me

1. **Q-001:** Should the raw Emivest CSV be tracked in git (`data/raw/`) or treated as
   a local-only reference file (not committed)?
   - **Recommended default:** Track in `data/raw/factory_a/` — it is the ground-truth
     input for this validation and should be reproducible from the repo.
   - **Why this matters:** If not tracked, the validation cannot be reproduced by another
     reviewer without the external file.
   - **If answered differently:** Add `data/raw/` to `.gitignore` and document the source
     path; accept that the pipeline requires the external file on disk.

2. **Q-002:** Should `load_emivest_8760()` scale the cleaned load to exactly 9,750 MWh
   (ALT-001) or use the natural ~9,315 MWh total?
   - **Recommended default:** Use natural total (~9,315 MWh); document the 4.5% gap as
     BIAS-05.
   - **Why this matters:** Scaling to 9,750 MWh would make the annual total match the
     slide exactly but alters the actual meter data.
   - **If answered differently:** Add a `scale_to_kwh` parameter (default `None`); when
     set to `9_750_000.0`, normalise after cleaning. This is the same pattern as
     `build_factory_a_load_8760()`.

## Suggested Next Step

No open blockers. Begin implementation at PHASE-01 immediately.
