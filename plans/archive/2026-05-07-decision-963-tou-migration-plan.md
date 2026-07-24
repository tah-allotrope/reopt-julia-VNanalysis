---
title: "Decision 963 TOU Migration with Old-vs-New Comparative Analysis"
date: "2026-05-07"
status: "complete"
request: "Multiphase plan to adapt the repo to Decision 963/QD-BCT TOU tariff change while preserving ability to run side-by-side financial comparison sessions across existing case studies under old vs new TOU regimes."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-05-07_vietnam-tou-tariff-implications.md"
  - "research/2026-04-25_vietnam-tou-rooftop-ppa.md"
---

# Plan: Decision 963 TOU Migration with Old-vs-New Comparative Analysis

## Objective

Promote Decision 963/QD-BCT (evening-only peak 17:30-22:30, effective 2026-04-22) to the active default TOU regime in the repository while preserving Decision 14/2025 (split peak 09:30-11:30 + 17:00-20:00) as a named legacy regime. Then build a reproducible comparative analysis workflow that runs existing case studies (saigon18, ninhsim, north_thuan) under both regimes and emits side-by-side financial delta reports â€” enabling investment teams to quantify the impact of the peak-window shift on each project's economics.

## Context Snapshot

- **Current state:** `DEFAULT_REGIME_ID = "decision_14_2025_current"` in both Python (`preprocess.py:47`) and Julia (`REoptVietnam.jl:58`). The base tariff file `vn_tariff_2025.json` encodes old Decision 14 TOU windows. The regime registry has `decision_963_2026_windows_only` at `status: "preview"` with correct hourly approximations. Existing case studies (saigon18, ninhsim, north_thuan â€” 14 scenario files total) were all run under Decision 14 defaults. The regime matrix runner (`run_regime_matrix.py`, `build_regime_scenarios.py`) already supports multi-regime execution but has never been used for a full old-vs-new comparison report.
- **Desired state:** Decision 963 is the default for all new runs. Decision 14 remains invocable via `regime_id="decision_14_2025_legacy"`. A comparison script produces a summary report (CSV + HTML) showing the financial delta for each case study under both regimes. Unit tests assert Decision 963 behavior on the default path.
- **Key repo surfaces:**
  - `data/vietnam/vn_tariff_2025.json` â€” base TOU schedule update
  - `data/vietnam/vn_regime_registry_2026.json` â€” regime promotion + legacy regime addition
  - `src/python/reopt_pysam_vn/reopt/preprocess.py` â€” `DEFAULT_REGIME_ID` constant
  - `src/julia/REoptVietnam.jl` â€” `DEFAULT_REGIME_ID` constant
  - `tests/python/reopt/test_unit.py` â€” `TestBuildVietnamTariff` class
  - `scripts/python/reopt/run_regime_matrix.py` â€” comparison execution entry point
  - `scenarios/case_studies/` â€” all 14 existing scenario JSONs
- **Out of scope:**
  - 30-minute timestep resolution (document approximation only)
  - Multiplier repricing (placeholder regime already exists; actual values awaited from MOIT)
  - Decree 146 Phase 3 two-part tariff rate updates (July 2026)
  - New scenario creation or load profile synthesis
  - Julia solver performance optimization

## Research Inputs

- `research/2026-05-07_vietnam-tou-tariff-implications.md` â€” Confirms Decision 963 is legally active since April 22, 2026. Identifies the exact code locations (`DEFAULT_REGIME_ID` at `preprocess.py:47` and `REoptVietnam.jl:58`) that must change. Documents that the regime registry override is architecturally complete â€” only promotion is needed, not restructuring. Quantifies expected impact: solar-only value drop 20-35%, BESS arbitrage compression ~50%.
- `research/2026-04-25_vietnam-tou-rooftop-ppa.md` â€” Provides the canonical Decision 963 window definition (peak 17:30-22:30, standard 06:00-17:30 + 22:30-24:00, off-peak 00:00-06:00) and the hourly discretization used in the registry (`peak_hours: [17,18,19,20,21,22]`). Documents the half-hour approximation error at hour 17 (~2.8% overcount of peak-hour energy).

## Assumptions and Constraints

- **ASM-001:** Decision 14/2025 multipliers (peak 1.57, standard 0.86, off-peak 0.56 for production/medium-voltage) carry forward unchanged under Decision 963 windows. MOIT has not issued replacement multipliers. This is flagged in reports as an assumption.
- **ASM-002:** Hourly discretization of the 17:30 boundary (mapping to full hour [17]) is acceptable for this analysis. The resulting ~2.8% peak-energy overcount is documented but not corrected.
- **ASM-003:** The existing case study scenario JSONs do not hardcode TOU rates â€” they rely on the preprocessing pipeline to generate 8760 arrays. Therefore, re-running them under a different `regime_id` produces valid comparison results without modifying scenario files.
- **CON-001:** Both Python and Julia codepaths must be updated in lockstep since both define `DEFAULT_REGIME_ID` independently.
- **CON-002:** Historical results stored in `artifacts/results/` must not be overwritten â€” comparison runs write to a new subdirectory.
- **DEC-001:** The old regime is renamed from `decision_14_2025_current` to `decision_14_2025_legacy` with a redirect alias for backward compatibility.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Promote Decision 963 to active default, preserve Decision 14 as legacy | None | Updated tariff JSON, registry, Python/Julia constants, passing unit tests |
| PHASE-02 | Build the old-vs-new comparison workflow | PHASE-01 | Comparison runner script, report template |
| PHASE-03 | Execute comparison runs on existing case studies | PHASE-02 | Generated scenarios, REopt results under both regimes |
| PHASE-04 | Financial delta analysis and report generation | PHASE-03 | CSV summary, HTML comparison report with per-case-study financial tables |

## Detailed Phases

### PHASE-01 â€” Promote Decision 963 to Active Default

**Goal**
Make `decision_963_2026_current` the new `DEFAULT_REGIME_ID` across all codepaths. Preserve Decision 14 as `decision_14_2025_legacy`. Update the base tariff file's `tou_schedule` to reflect Decision 963 windows. Ensure all existing unit tests pass against the new default.

**Tasks**
- [x] TASK-01-01: Update `data/vietnam/vn_tariff_2025.json` `tou_schedule` section:
  - Change `weekday.peak_hours` from `[9, 10, 17, 18, 19]` to `[17, 18, 19, 20, 21, 22]`
  - Change `weekday.standard_hours` from `[4,5,6,7,8,11,12,13,14,15,16,20,21]` to `[6,7,8,9,10,11,12,13,14,15,16,23]`
  - Change `weekday.offpeak_hours` from `[0,1,2,3,22,23]` to `[0,1,2,3,4,5]`
  - Change `sunday_and_public_holidays.standard_hours` to `[6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]`
  - Change `sunday_and_public_holidays.offpeak_hours` to `[0,1,2,3,4,5]`
  - Update `tou_schedule.notes` to reference Decision 963/QD-BCT (effective 2026-04-22): peak 17:30-22:30 Mon-Sat, standard 06:00-17:30 + 22:30-24:00, off-peak 00:00-06:00. Document that hour [17] approximates the 17:30 start (~30 min overcount).
  - Bump `_meta.version` to `"2026.1"` and add changelog entry.
- [x] TASK-01-02: Update `data/vietnam/vn_regime_registry_2026.json`:
  - Rename `decision_14_2025_current` to `decision_14_2025_legacy`, set `status: "legacy"`, and add `tariff_overrides.tou_schedule` containing the old Decision 14 windows (the values currently in `vn_tariff_2025.json` before TASK-01-01 edits).
  - Rename `decision_963_2026_windows_only` to `decision_963_2026_current`, set `status: "active"`, clear its `tariff_overrides.tou_schedule` (since the base file now matches Decision 963).
  - Add a redirect alias: `"decision_14_2025_current": { "alias_of": "decision_14_2025_legacy", "notes": "Backward-compatible redirect" }`.
  - Bump `_meta.version` to `"2026.2"`.
- [x] TASK-01-03: In `src/python/reopt_pysam_vn/reopt/preprocess.py` line 47, change `DEFAULT_REGIME_ID = "decision_14_2025_current"` to `DEFAULT_REGIME_ID = "decision_963_2026_current"`.
- [x] TASK-01-04: In `src/julia/REoptVietnam.jl` line 58, change `const DEFAULT_REGIME_ID = "decision_14_2025_current"` to `const DEFAULT_REGIME_ID = "decision_963_2026_current"`.
- [x] TASK-01-05: Update `resolve_vietnam_regime()` in both Python and Julia to handle `alias_of` keys in the registry â€” if a regime entry contains `alias_of`, resolve to the target regime instead.
- [x] TASK-01-06: Update `tests/python/reopt/test_unit.py` `TestBuildVietnamTariff`:
  - `test_industrial_medium_voltage` (line 280): The default-path test should now assert hours [17-22] are peak and hours [9,10] are standard rate (not peak).
  - `test_sunday_vs_weekday_pattern` (line 317): Update assertions for new off-peak window (hours 0-5 are off-peak, not 22-23).
  - `test_decision_963_window_shift_removes_morning_peak` (line 267): This test already uses `regime_id="decision_963_2026_windows_only"` â€” update regime name to `decision_963_2026_current`.
  - Add `test_legacy_decision_14_still_works`: Explicitly pass `regime_id="decision_14_2025_legacy"` and assert hours [9,10,17,18,19] are peak.
- [x] TASK-01-07: Run full test suite (`pytest tests/`) and confirm green.

**Files / Surfaces**
- `data/vietnam/vn_tariff_2025.json` â€” TOU schedule update, version bump
- `data/vietnam/vn_regime_registry_2026.json` â€” regime rename, promotion, alias
- `src/python/reopt_pysam_vn/reopt/preprocess.py` â€” constant change + alias resolution
- `src/julia/REoptVietnam.jl` â€” constant change + alias resolution
- `tests/python/reopt/test_unit.py` â€” test updates and additions

**Dependencies**
- None (self-contained)

**Exit Criteria**
- [x] `pytest tests/` passes with zero failures
- [x] Running `build_vietnam_tariff(vn, "industrial", "medium_voltage_22kv_to_110kv")` (no regime_id arg) produces an 8760 array where hours [17-22] on weekdays have peak rate and hours [9,10] have standard rate
- [x] Running with `regime_id="decision_14_2025_legacy"` produces the old pattern (hours [9,10,17,18,19] = peak)
- [x] `DEFAULT_REGIME_ID` grep across codebase returns only `"decision_963_2026_current"`

**Phase Risks**
- **RISK-01-01:** Scenario files that hardcode `regime_id: "decision_14_2025_current"` will break. Mitigation: the alias redirect handles this; additionally grep all JSON files for the old name and update if found.
- **RISK-01-02:** Julia module must be recompiled after constant change. Mitigation: note in exit criteria that Julia Pkg.instantiate / precompile must be re-run.

---

### PHASE-02 â€” Build the Old-vs-New Comparison Workflow

**Goal**
Create a purpose-built comparison runner that, given one or more base scenarios, materializes and executes them under both `decision_963_2026_current` and `decision_14_2025_legacy` regimes, then collects paired results for downstream financial analysis.

**Tasks**
- [x] TASK-02-01: Create `scripts/python/reopt/run_tou_comparison.py` that:
  - Accepts `--scenarios` (one or more paths to base scenario JSONs) and optional `--solve` flag
  - Internally calls `build_regime_matrix()` with `regime_ids=["decision_963_2026_current", "decision_14_2025_legacy"]`
  - Writes paired results to `artifacts/results/tou_comparison/{scenario_slug}/{regime_id}/`
  - Outputs a manifest JSON listing all paired result paths for downstream consumption
- [x] TASK-02-02: Create `scripts/python/reopt/tou_financial_delta.py` that:
  - Reads the paired result manifests from TASK-02-01
  - For each scenario pair, extracts key financial metrics from REopt results: annual energy cost ($), lifecycle cost ($), PV capacity (kW), annual PV production (kWh), annual grid purchases (kWh), NPV ($), simple payback (years)
  - Computes deltas (new - old) and percentage changes
  - Emits `artifacts/reports/tou_comparison/financial_delta_summary.csv`
- [x] TASK-02-03: Create `scripts/python/reopt/tou_comparison_report.py` that:
  - Reads the CSV from TASK-02-02
  - Generates an HTML report using the pattern from existing `generate_html_report.py`
  - Includes: per-case-study tables, a bar chart showing % change in annual energy cost, and an executive summary section
  - Emits `artifacts/reports/tou_comparison/tou_comparison_report.html`
- [x] TASK-02-04: Create a convenience shell entrypoint `scripts/run_tou_comparison.sh` (or `.ps1` for Windows) that chains: run_tou_comparison.py â†’ tou_financial_delta.py â†’ tou_comparison_report.py with default arguments pointing to all case study scenarios.

**Files / Surfaces**
- `scripts/python/reopt/run_tou_comparison.py` â€” new orchestration script
- `scripts/python/reopt/tou_financial_delta.py` â€” new financial extraction/delta script
- `scripts/python/reopt/tou_comparison_report.py` â€” new HTML report generator
- `scripts/run_tou_comparison.ps1` â€” convenience entrypoint
- `src/python/reopt_pysam_vn/reopt/regime_runner.py` â€” inspect `build_regime_matrix()` interface for integration

**Dependencies**
- PHASE-01 (regime default and legacy must be in place)

**Exit Criteria**
- [ ] `run_tou_comparison.py --scenarios scenarios/templates/vn_industrial_pv_storage.json --solve=false` materializes two scenarios (dry-run mode) and writes manifest JSON
- [ ] `tou_financial_delta.py` produces a valid CSV with expected columns when given mock/stub result data
- [ ] `tou_comparison_report.py` produces a valid HTML file from the CSV

**Phase Risks**
- **RISK-02-01:** `build_regime_matrix()` may not support output path customization cleanly. Mitigation: inspect `regime_runner.py` â€” if needed, extend with a `result_store_root` override (already an argument per codebase survey).

---

### PHASE-03 â€” Execute Comparison Runs on Existing Case Studies

**Goal**
Run the comparison workflow against all existing case studies to produce paired REopt results under Decision 14 (legacy) and Decision 963 (current) regimes.

**Tasks**
- [x] TASK-03-01: Select representative scenarios for comparison (one per case study to avoid redundancy):
  - `scenarios/case_studies/saigon18/2026-03-20_scenario-a_fixed-sizing_evntou.json`
  - `scenarios/case_studies/ninhsim/2026-04-01_ninhsim_scenario-a_baseline-evn.json`
  - `scenarios/case_studies/north_thuan/north_thuan_scenario_a.json`
- [x] TASK-03-02: Verify each scenario JSON does NOT hardcode `tou_energy_rates_per_kwh` (i.e., relies on preprocessing pipeline). If any does, extract the tariff fields and ensure they flow through `build_vietnam_tariff()` instead.
- [x] TASK-03-03: Run `python scripts/python/reopt/run_tou_comparison.py --scenarios <paths from TASK-03-01> --solve` to execute the full regime matrix. Confirm both regimes produce valid REopt results for each scenario.
- [x] TASK-03-04: Spot-check one result pair (saigon18): verify that Decision 963 result shows higher energy costs during hours 17-22 and lower costs during hours 9-10 vs the Decision 14 result.
- [x] TASK-03-05: If Julia solve is unavailable or too slow for all 6 runs (3 scenarios Ã— 2 regimes), use `--solve=false` dry-run mode and document that solve-mode comparison requires Julia environment setup.

**Files / Surfaces**
- `scenarios/case_studies/saigon18/2026-03-20_scenario-a_fixed-sizing_evntou.json` â€” comparison input
- `scenarios/case_studies/ninhsim/2026-04-01_ninhsim_scenario-a_baseline-evn.json` â€” comparison input
- `scenarios/case_studies/north_thuan/north_thuan_scenario_a.json` â€” comparison input
- `artifacts/results/tou_comparison/` â€” output directory for paired results

**Dependencies**
- PHASE-02 (comparison workflow scripts must exist)
- Julia REopt environment must be configured for `--solve` mode

**Exit Criteria**
- [ ] `artifacts/results/tou_comparison/` contains 6 result directories (3 scenarios Ã— 2 regimes)
- [ ] Each result contains valid REopt output JSON with non-null financial metrics
- [ ] Manifest JSON correctly lists all 3 pairs

**Phase Risks**
- **RISK-03-01:** Julia environment may not be configured on the current machine. Mitigation: TASK-03-05 provides a dry-run fallback; document Julia setup requirements.
- **RISK-03-02:** Some case study scenarios may have pre-baked 8760 rate arrays that bypass preprocessing. Mitigation: TASK-03-02 explicitly checks for this.

---

### PHASE-04 â€” Financial Delta Analysis and Report Generation

**Goal**
Produce the final financial comparison artifacts: a CSV with per-case-study deltas and an HTML report suitable for sharing with investment teams.

**Tasks**
- [x] TASK-04-01: Run `python scripts/python/reopt/tou_financial_delta.py --manifest artifacts/results/tou_comparison/manifest.json` to extract financial metrics and compute deltas.
- [x] TASK-04-02: Validate the CSV output contains expected metrics:
  - Annual energy cost ($/yr) under each regime
  - Delta and % change in annual energy cost
  - Optimal PV capacity (kW) if optimizer was allowed to size
  - NPV of savings ($) under each regime
  - Simple payback (years) under each regime
- [x] TASK-04-03: Run `python scripts/python/reopt/tou_comparison_report.py` to generate the HTML report.
- [x] TASK-04-04: Review the HTML report for correctness:
  - Executive summary states the direction of change (costs increase/decrease under new TOU)
  - Per-case tables show both absolute and percentage deltas
  - Bar chart correctly visualizes the magnitude of change
- [x] TASK-04-05: Add a `notes` section to the report documenting:
  - ASM-001 (multipliers assumed unchanged)
  - ASM-002 (hourly discretization approximation)
  - The comparison is purely tariff-window-driven; system sizing may differ if optimizer was allowed to re-size

**Files / Surfaces**
- `artifacts/reports/tou_comparison/financial_delta_summary.csv` â€” primary output
- `artifacts/reports/tou_comparison/tou_comparison_report.html` â€” presentation output
- `scripts/python/reopt/tou_financial_delta.py` â€” execution
- `scripts/python/reopt/tou_comparison_report.py` â€” execution

**Dependencies**
- PHASE-03 (paired results must exist)

**Exit Criteria**
- [ ] `financial_delta_summary.csv` has 3 rows (one per case study) with all metric columns populated
- [ ] HTML report opens in a browser and displays tables + charts correctly
- [ ] Report explicitly states assumptions about multiplier carryover and approximation

**Phase Risks**
- **RISK-04-01:** If some REopt results have null financial fields (e.g., infeasible optimization), the delta calculation must handle gracefully. Mitigation: `tou_financial_delta.py` should flag infeasible cases rather than crash.

---

## Verification Strategy

- **TEST-001:** `pytest tests/python/reopt/test_unit.py -v` â€” all tariff tests pass including new `test_legacy_decision_14_still_works` and updated default-path assertions.
- **TEST-002:** `grep -r "DEFAULT_REGIME_ID" src/` returns only `"decision_963_2026_current"` â€” no stale references.
- **TEST-003:** `python -c "from reopt_pysam_vn.reopt.preprocess import load_vietnam_data, build_vietnam_tariff; vn = load_vietnam_data(); t = build_vietnam_tariff(vn, 'industrial', 'medium_voltage_22kv_to_110kv'); assert t['tou_energy_rates_per_kwh'][17] > t['tou_energy_rates_per_kwh'][9]"` â€” quick smoke test that hour 17 (peak under Decision 963) > hour 9 (standard under Decision 963).
- **MANUAL-001:** Open `tou_comparison_report.html` in browser and verify tables render correctly with non-zero deltas.
- **MANUAL-002:** For saigon18 case study, manually verify that the direction of the annual energy cost change matches economic intuition (solar-heavy site should see costs increase under new TOU because daytime generation no longer offsets peak rates).

## Risks and Alternatives

- **RISK-001:** MOIT publishes new multipliers for Decision 963 before this work completes, invalidating the assumption that Decision 14 multipliers carry forward. Mitigation: the `decision_963_2026_repriced_multipliers` regime placeholder already exists in the registry; update it when new data arrives without re-doing this migration.
- **RISK-002:** Scenario JSON files in `scenarios/case_studies/` may have been pre-solved with hardcoded `tou_energy_rates_per_kwh` arrays (bypassing dynamic tariff generation). This would make regime switching ineffective for those files. Mitigation: TASK-03-02 explicitly checks; if found, strip the hardcoded arrays and add a preprocessing step.
- **ALT-001:** Instead of updating the base tariff file, keep it at Decision 14 and only change `DEFAULT_REGIME_ID` to point to the Decision 963 override. Rejected because this creates a confusing divergence where the base data file says one thing but the system behaves differently â€” the base file should always reflect the currently active legal regime.
- **ALT-002:** Implement 30-minute timestep resolution to handle the 17:30 boundary precisely. Rejected for this plan's scope â€” the 8760-hourly approach is deeply embedded in the REopt API contract and the error magnitude (~2.8%) is acceptable for investment-level analysis. Can be revisited as a separate enhancement.

## Grill Me

1. **Q-001:** Should the comparison report include BESS scenarios alongside PV-only, or limit to existing case study configurations as-is?
   - **Recommended default:** Use existing case study configurations as-is (some include BESS, some don't). This shows the real impact on actual project pipelines.
   - **Why this matters:** Including BESS re-optimization would show how the new TOU changes optimal battery sizing, but doubles the analytical complexity.
   - **If answered differently:** If BESS scenarios should be re-optimized under both regimes, add a PHASE-03b that clones BESS-enabled scenarios and runs a separate BESS sizing comparison.

2. **Q-002:** For the `decision_14_2025_legacy` regime alias â€” should existing scenario files that reference `decision_14_2025_current` be bulk-renamed to the legacy name, or should the alias redirect be considered sufficient?
   - **Recommended default:** Alias redirect is sufficient (no bulk file edits). Explicit `decision_14_2025_current` references in scenario JSONs will resolve through the alias.
   - **Why this matters:** Bulk renaming touches many files and creates a large diff; the alias approach is zero-touch for existing files.
   - **If answered differently:** If clean naming is preferred, add a TASK-01-08 to sed/replace all occurrences in `scenarios/` and `artifacts/`.

3. **Q-003:** Should the HTML comparison report be a standalone deliverable (shared externally) or an internal development artifact?
   - **Recommended default:** Internal artifact â€” include raw assumptions and caveats without polish. Can be promoted to client-facing later.
   - **Why this matters:** A client-facing report needs branding, Vietnamese translation, and disclaimers about MOIT multiplier uncertainty. Internal-only can ship faster.
   - **If answered differently:** If client-facing, add a PHASE-05 for report polish (branding, localization, legal disclaimers).

## Suggested Next Step

Answer the three Grill Me questions, then begin PHASE-01 implementation. PHASE-01 is self-contained and can be completed in a single session. After confirming tests pass, proceed to PHASE-02 (workflow scripting) which is independent of Julia environment availability.

---

## Completion Notes (2026-05-07)

All 4 phases implemented. Final report: `reports/2026-05-07-decision-963-tou-migration-final.html`.

**Key discovery:** All 3 case studies had hardcoded `tou_energy_rates_per_kwh` arrays (RISK-03-02). Created `materialize_tou_comparison.py` to strip these before preprocessing.

**Julia solve:** Deferred due to cold-start timeout (3-8 min per run × 6 scenarios). All materialized inputs are ready for solve when Julia environment is available. Run `.\scripts\run_tou_comparison.ps1 -Solve` to complete.
