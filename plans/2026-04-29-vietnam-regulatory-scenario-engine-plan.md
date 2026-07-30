---
title: "Vietnam TOU and Regulatory Scenario Engine"
date: "2026-04-29"
status: "open"
request: "Take Idea 2 from research/2026-04-26_commercial-product-ideas.md and create a multi-phase plan using the plan skill."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-04-26_commercial-product-ideas.md"
  - "research/2026-04-25_vietnam-tou-rooftop-ppa.md"
---

# Plan: Vietnam TOU and Regulatory Scenario Engine

## Objective
Turn Idea 2 from the commercial-product brief into a repo-native productization plan: a deterministic regulatory scenario engine that can run the same Vietnam project under named regime bundles and report the economic delta side by side. This matters now because Decision 963/QD-BCT already created immediate demand for old-vs-new TOU comparisons, and the current repo already has the versioned data, dual-language preprocessing, parity tests, and HTML reporting surfaces needed to commercialize that workflow without modifying REopt.jl itself.

## Context Snapshot
- **Current state:** The repo already has manifest-driven Vietnam data in `data/vietnam/`, dual-language preprocessing in `src/julia/REoptVietnam.jl` and `src/python/reopt_pysam_vn/reopt/preprocess.py`, Layer 1-3 parity coverage, and downstream reporting/sensitivity scripts such as `scripts/python/reopt/two_part_tariff_sensitivity.py`, `scripts/python/integration/generate_html_report.py`, and `scripts/python/integration/generate_cross_project_dashboard.py`. The current regulatory logic is split across `data/vietnam/vn_tariff_2025.json` and `data/vietnam/vn_export_rules_decree57.json`, and the existing TOU comparison work is still a one-off plan in `plans/active/2026-04-25-vn-tou-rts-comparison-plan.md` rather than a reusable engine.
- **Desired state:** A first-class `regime_id` selects TOU schedule, demand-charge mode, export-cap rules, surplus-purchase assumptions, and optional BESS capacity-payment preview metadata. The same project input can be run across many regimes and assumption sets, cached by deterministic hash, and reduced into HTML/CSV comparison packs suitable for monthly regulatory subscription updates.
- **Key repo surfaces:** `data/vietnam/manifest.json`, `data/vietnam/vn_tariff_2025.json`, `data/vietnam/vn_export_rules_decree57.json`, `src/julia/REoptVietnam.jl`, `src/python/reopt_pysam_vn/reopt/preprocess.py`, `tests/python/reopt/test_data_validation.py`, `tests/julia/test_data_validation.jl`, `tests/python/reopt/test_unit.py`, `tests/julia/test_unit.jl`, `tests/cross_language/cross_validate.py`, `tests/julia/export_processed_dict.jl`, `scripts/julia/run_vietnam_scenario.jl`, `scripts/python/reopt/two_part_tariff_sensitivity.py`, `scripts/python/integration/generate_html_report.py`, and `plans/active/2026-04-25-vn-tou-rts-comparison-plan.md`.
- **Out of scope:** SaaS UI/auth/billing, lender-grade Monte Carlo and cashflow waterfalls from Idea 3, upstream `REopt.jl` modifications, live legal-source scraping, and sub-hourly solver support for exact 30-minute tariff boundaries.

## Research Inputs
- `research/2026-04-26_commercial-product-ideas.md` - Establishes Idea 2 as the recommended first commercial direction, defines the target product shape (`regime registry`, `scenario combinatorics runner`, `comparison reports`, and `subscription feed`), and explicitly identifies the existing TOU comparison plan as the seed validation case rather than a separate product.
- `research/2026-04-25_vietnam-tou-rooftop-ppa.md` - Supplies the canonical Decision 14/2025 vs Decision 963/QD-BCT window changes, confirms that tariff multipliers may be remapped or reissued, and makes sensitivity handling a first-order requirement rather than an optional enhancement.

## Assumptions and Constraints
- **ASM-001:** The first commercialized cut stays repo-native and file-based (CLI + JSON/HTML artifacts), because the current workspace is organized around scripts, versioned data files, and artifact outputs rather than a persistent service or database.
- **ASM-002:** `regime_id` becomes the single public selector for regulatory conditions. Avoid adding one-off flags such as `tou_regime`, `export_cap_override`, or `two_part_tariff_mode` that would need another migration later.
- **ASM-003:** The first acceptance workload is the medium-factory TOU comparison already scoped in `plans/active/2026-04-25-vn-tou-rts-comparison-plan.md`.
- **CON-001:** Julia and Python must stay parity-safe for any identical resolved regime and input pair, preserving the current Layer 3 contract.
- **CON-002:** Existing callers that omit `regime_id` must retain current Decision 14/2025 behavior with no required caller changes.
- **CON-003:** Full Layer 4 green is not a realistic release gate because `docs/testing.md` documents two pre-existing Python API failures unrelated to this work. Verification should rely on Layers 1-3 plus targeted smoke/integration checks.
- **CON-004:** The current hourly engine still approximates half-hour tariff boundaries, so Decision 963 outputs remain directional until a separate sub-hourly plan exists.
- **DEC-001:** Initial regime bundles are `decision_14_2025_current`, `decision_963_2026_windows_only`, `decision_963_2026_repriced_multipliers`, `decree57_rooftop_50pct_draft`, and `decree146_two_part_trial_2026`.
- **DEC-002:** Initial BESS capacity-payment support is metadata/post-processing only. Do not inject custom revenue terms into the REopt objective in this plan.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Add a versioned regime registry and data contract | None | `data/vietnam/vn_regime_registry_2026.json`, manifest/loader updates, Layer 1 validation |
| PHASE-02 | Make `regime_id` a first-class preprocessing input with Julia/Python parity | PHASE-01 | Updated `REoptVietnam.jl`, `preprocess.py`, unit and cross-language tests |
| PHASE-03 | Build deterministic multi-regime execution and artifact storage | PHASE-02 | Scenario generator, matrix runner, hashed result-store layout |
| PHASE-04 | Ship regime-delta reporting and the first reference deliverables | PHASE-03 | Summary reducers, HTML/CSV comparison outputs, medium-factory reference report |
| PHASE-05 | Operationalize monthly updates, changelogs, and regression baselines | PHASE-04 | Update workflow docs, change-summary script, subscription artifact pattern |

## Detailed Phases

### PHASE-01 - Regime Registry Foundation
**Goal**
Introduce a versioned, machine-readable regime registry that sits beside the existing tariff and export-rule files and can express named regulatory bundles without duplicating the whole Vietnam data layer.

**Tasks**
- [x] TASK-01-01: Add `data/vietnam/vn_regime_registry_2026.json` with `_meta` and `data.regimes`. Each regime bundle should contain `label`, `effective_date`, `status`, `tariff_overrides`, `export_rule_overrides`, `postprocess_overrides`, `source_refs`, and `notes`, so changes are stored as override fragments rather than whole-file copies.
- [x] TASK-01-02: Seed the registry with the five initial bundles from DEC-001. The `decision_14_2025_current` bundle should resolve to current repo behavior, while the others should override only the fields they actually change (TOU windows, multiplier interpretation, export cap, demand-charge mode, or BESS payment preview).
- [x] TASK-01-03: Extend `data/vietnam/manifest.json` with a new `regimes` entry and update `load_vietnam_data()` in both languages so `VNData` carries a `regimes` payload alongside `tariff`, `tech_costs`, `financials`, `emissions`, and `export_rules`.
- [x] TASK-01-04: Update Layer 1 validation in `tests/python/reopt/test_data_validation.py` and `tests/julia/test_data_validation.jl` to require the new manifest key and validate the registry schema: valid `regime_id` keys, allowed `status` values, 24-hour TOU coverage when schedules are present, export fractions in `[0,1]`, and source references present for every non-baseline bundle.

**Files / Surfaces**
- `data/vietnam/vn_regime_registry_2026.json` - New source-of-truth file for named regulatory bundles.
- `data/vietnam/manifest.json` - Adds the new registry to the active Vietnam data contract.
- `src/python/reopt_pysam_vn/reopt/preprocess.py` - `VNData` dataclass and loader must understand the new file.
- `src/julia/REoptVietnam.jl` - `VNData` struct and loader must stay aligned with Python.
- `tests/python/reopt/test_data_validation.py` - Layer 1 schema gate for the new registry.
- `tests/julia/test_data_validation.jl` - Julia mirror of the registry schema checks.

**Dependencies**
- None.

**Exit Criteria**
- [ ] `load_vietnam_data()` succeeds in both languages with the new `regimes` manifest entry.
- [ ] The registry file contains all five seed bundles and no bundle duplicates entire tariff or export files unnecessarily.
- [ ] Layer 1 data-validation tests pass for the expanded manifest contract.

**Phase Risks**
- **RISK-01-01:** The registry schema becomes too abstract and hard to maintain. Mitigation: keep it limited to explicit override fragments needed by the current engine, not a generic policy DSL.

### PHASE-02 - Preprocessing API and Cross-Language Parity
**Goal**
Make `regime_id` a first-class argument across the preprocessing layer so any named regulatory bundle can be resolved into the exact tariff and export settings used to build a scenario.

**Tasks**
- [x] TASK-02-01: Add a `resolve_vietnam_regime` helper in both `src/python/reopt_pysam_vn/reopt/preprocess.py` and `src/julia/REoptVietnam.jl` that overlays a chosen regime bundle onto the base `vn.tariff` and `vn.export_rules` payloads and returns a fully resolved regime object.
- [x] TASK-02-02: Extend `build_vietnam_tariff(...)` and `apply_vietnam_defaults(...)` / `apply_vietnam_defaults!(...)` with a `regime_id` argument. The default should be `decision_14_2025_current` so all existing builders and tests remain backward compatible.
- [x] TASK-02-03: Update `apply_decree57_export(...)` / `apply_decree57_export!(...)` to consume regime-specific `max_export_fraction`, `surplus_purchase_rate`, and export-policy overrides from the resolved regime rather than assuming a hard-coded 20 percent rooftop cap.
- [x] TASK-02-04: Persist `resolved_regime_id`, registry version, and any post-processing-only preview fields (for example `bess_capacity_payment_vnd_per_kw_month`) into `_meta` so later runners and reports can trace exactly which regime generated a scenario.
- [x] TASK-02-05: Extend `tests/python/reopt/test_unit.py` and `tests/julia/test_unit.jl` to cover old/new TOU hour mappings, draft 50 percent export-cap metadata, two-part tariff demand-rate injection, and omission-of-`regime_id` backward compatibility.
- [x] TASK-02-06: Extend `tests/julia/export_processed_dict.jl` and `tests/cross_language/cross_validate.py` to compare at least two explicit regimes end to end, not just one baseline tariff.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/reopt/preprocess.py` - Add regime resolution, `regime_id`, and `_meta` propagation.
- `src/julia/REoptVietnam.jl` - Julia mirror of the same public and internal interfaces.
- `tests/python/reopt/test_unit.py` - New unit coverage for regime-specific behavior.
- `tests/julia/test_unit.jl` - Julia mirror of regime-specific unit coverage.
- `tests/julia/export_processed_dict.jl` - Cross-language fixture must accept explicit regimes.
- `tests/cross_language/cross_validate.py` - Layer 3 must compare multiple resolved regimes.

**Dependencies**
- PHASE-01.

**Exit Criteria**
- [ ] Omitting `regime_id` reproduces current Decision 14/2025 outputs.
- [ ] Explicit `regime_id` selection changes TOU/export behavior only through data-driven overlays, not duplicated code paths.
- [ ] Layers 1-3 pass via `./tests/run_all_tests.ps1 -SkipLayer4` and cross-language comparisons succeed for at least two regimes.

**Phase Risks**
- **RISK-02-01:** Python and Julia overlay logic drifts over time. Mitigation: keep helper structure and tests mirrored, and make multi-regime cross-validation a release gate.

### PHASE-03 - Multi-Regime Runner and Deterministic Result Store
**Goal**
Build a reusable runner that defines a project once, materializes fully resolved scenario JSONs for each regime/assumption combination, executes them through the existing Julia solve path, and stores results in a deterministic, cacheable layout.

**Tasks**
- [x] TASK-03-01: Add `scenarios/regime_engine/assumption_sets/` with named JSON assumption packs such as `base.json`, `repriced_multipliers.json`, `export_cap_sweep.json`, and `capacity_payment_preview.json` so sweeps are explicit artifacts rather than ad hoc CLI flags.
- [x] TASK-03-02: Add `scripts/python/reopt/build_regime_scenarios.py` that takes a base template or case-study input plus one or more `regime_id` values and writes fully resolved scenario JSONs to `scenarios/generated/regime_engine/<project_slug>/`.
- [x] TASK-03-03: Add `src/python/reopt_pysam_vn/reopt/regime_runner.py` and `scripts/python/reopt/run_regime_matrix.py` to orchestrate `N regimes x M assumption sets`, compute a deterministic scenario hash from canonicalized inputs, and skip reruns when a successful hash directory already exists unless `--force` is set.
- [x] TASK-03-04: Extend `scripts/julia/run_vietnam_scenario.jl` with an explicit `--output-dir` argument so the new engine is not blocked by the current hard-coded result routing that only recognizes `saigon18`, `north_thuan`, and `ninhsim` path markers.
- [x] TASK-03-05: Standardize per-run artifacts under `artifacts/results/regime_engine/<project_slug>/<scenario_hash>/` with `input.json`, `resolved_regime.json`, `reopt-results.json`, `summary.json`, and `run_manifest.json` containing `regime_id`, `assumption_set_id`, registry version, runtime, and status.
- [x] TASK-03-06: Add a targeted smoke test such as `tests/python/integration/test_regime_engine_smoke.py` that runs a tiny two-regime matrix with `--no-solve` or the repo's smoke-mode path and asserts artifact completeness plus stable hashing.

**Files / Surfaces**
- `scenarios/regime_engine/assumption_sets/` - Named sweep definitions for repeatable comparisons.
- `scenarios/generated/regime_engine/` - Materialized scenario JSONs for solve execution.
- `src/python/reopt_pysam_vn/reopt/regime_runner.py` - Reusable orchestration logic behind the CLI runner.
- `scripts/python/reopt/build_regime_scenarios.py` - Scenario materialization entrypoint.
- `scripts/python/reopt/run_regime_matrix.py` - Matrix execution entrypoint.
- `scripts/julia/run_vietnam_scenario.jl` - Needs explicit output control for the new artifact layout.
- `artifacts/results/regime_engine/` - Deterministic result store for caching and auditability.

**Dependencies**
- PHASE-02.

**Exit Criteria**
- [ ] A single base project can be run across at least `2 regimes x 2 assumption sets` with one command.
- [ ] Re-running the same matrix reuses cached successful result directories via scenario hash matching.
- [ ] Every run writes a complete manifest with enough metadata to reproduce the scenario later.

**Phase Risks**
- **RISK-03-01:** Unbounded combinatorics create a large artifact footprint and long runtimes. Mitigation: require named assumption-set files, deterministic hashing, and cache-first execution from the start.

### PHASE-04 - Regime Delta Reporting and Reference Deliverables
**Goal**
Reduce raw regime-run outputs into decision-ready deltas and use the existing TOU comparison plan as the first market-facing reference pack.

**Tasks**
- [ ] TASK-04-01: Add a reducer such as `scripts/python/integration/summarize_regime_matrix.py` that normalizes each run into a compact metric row: PV size, storage size, year-1 bill, exports, NPV, IRR, payback, demand charges, and any regime-specific post-processing adders.
- [ ] TASK-04-02: Add `scripts/python/integration/generate_regime_comparison_report.py`, reusing layout ideas from `generate_html_report.py` and `generate_cross_project_dashboard.py` but making the input fully regime-driven instead of project-specific.
- [ ] TASK-04-03: Use `plans/active/2026-04-25-vn-tou-rts-comparison-plan.md` as the first acceptance case and generate a reference comparison pack for `decision_14_2025_current`, `decision_963_2026_windows_only`, and `decision_963_2026_repriced_multipliers`.
- [ ] TASK-04-04: Validate that the engine is generic by producing a second archetype report from an existing template, preferably `scenarios/templates/vn_industrial_pv_storage.json` or `scenarios/templates/vn_commercial_rooftop_pv.json`.
- [ ] TASK-04-05: Add targeted reporter tests that verify reducer math, delta signs, and basic HTML artifact generation without depending on browser automation.

**Files / Surfaces**
- `scripts/python/integration/summarize_regime_matrix.py` - Metric normalization layer between raw solves and reporting.
- `scripts/python/integration/generate_regime_comparison_report.py` - New generic regime comparison reporter.
- `plans/active/2026-04-25-vn-tou-rts-comparison-plan.md` - Acceptance workload and product seed for the first report.
- `scenarios/templates/vn_industrial_pv_storage.json` - Existing archetype input for a second validation case.
- `artifacts/reports/regime_engine/` - Output location for HTML/CSV/JSON comparison packs.

**Dependencies**
- PHASE-03.

**Exit Criteria**
- [ ] A self-contained HTML report opens cleanly and shows side-by-side deltas for at least three regimes on the medium-factory reference case.
- [ ] A second archetype run proves the reporter is not overfit to the first TOU comparison case.
- [ ] The reference Decision 14 vs Decision 963 deltas match the research-brief direction and are traceable back to run manifests and summary rows.

**Phase Risks**
- **RISK-04-01:** The first reporter implementation overfits to the medium-factory TOU case. Mitigation: require a second archetype in the same phase before calling the reporting surface reusable.

### PHASE-05 - Subscription Update Workflow and Regression Discipline
**Goal**
Turn the engine from a one-time analysis tool into a repeatable monthly product surface with changelog discipline, archetype refreshes, and baseline regression checks.

**Tasks**
- [ ] TASK-05-01: Add `docs/regimes.md` and a `README.md` section describing how to add a new regime bundle, regenerate archetype comparisons, and publish a monthly update pack.
- [ ] TASK-05-02: Add `scripts/python/reopt/build_regime_change_summary.py` that diffs two registry versions and emits a machine-readable change summary plus a human-readable one-pager source file for subscription updates.
- [ ] TASK-05-03: Standardize default subscription artifacts under `artifacts/reports/regime_engine/subscriptions/<date>/` with the updated registry version, archetype deltas, and the generated change summary.
- [ ] TASK-05-04: Add regression baselines under `tests/baselines/regime_engine/` and a targeted test such as `tests/python/integration/test_regime_engine_baselines.py` so new bundles or revised assumptions only change outputs intentionally.
- [ ] TASK-05-05: Document a monthly operating workflow: update registry data, run the default archetype matrix, inspect changed baselines, publish the HTML/CSV pack, and record the update in the registry changelog.

**Files / Surfaces**
- `docs/regimes.md` - Operational documentation for the new engine.
- `README.md` - High-level user-facing entrypoint for the workflow.
- `scripts/python/reopt/build_regime_change_summary.py` - Diff/changelog helper for subscription updates.
- `tests/baselines/regime_engine/` - Canonical outputs for update regression checks.
- `artifacts/reports/regime_engine/subscriptions/` - Standardized destination for monthly commercial deliverables.

**Dependencies**
- PHASE-04.

**Exit Criteria**
- [ ] A new regime bundle can be added and rolled through the default archetype pack with one documented workflow.
- [ ] Baseline diffs clearly identify what changed between registry versions.
- [ ] The repo contains enough docs and scripted helpers that another agent can produce a monthly update without rediscovering the process.

**Phase Risks**
- **RISK-05-01:** Monthly updates still require code edits for normal rule changes. Mitigation: keep regulatory changes data-driven in the registry and reserve code changes for schema evolution only.

## Verification Strategy
- **TEST-001:** Run `./tests/run_all_tests.ps1 -SkipLayer4 -JuliaTimeoutSeconds 1200` after PHASE-02 to validate manifest changes, preprocessing behavior, and cross-language parity without being blocked by unrelated API failures.
- **TEST-002:** Run `python tests/cross_language/cross_validate.py` with explicit multi-regime fixtures to confirm that resolved tariff/export behavior matches between Julia and Python for at least two named bundles.
- **TEST-003:** Add and run a targeted smoke test such as `python -m pytest tests/python/integration/test_regime_engine_smoke.py -v` after PHASE-03 and a baseline comparison test after PHASE-05.
- **MANUAL-001:** Open the first medium-factory HTML comparison pack and verify that Decision 963 removes the morning-peak value capture from the old TOU case and that the repriced-multipliers scenario is clearly labeled as a sensitivity rather than a base case.
- **MANUAL-002:** Inspect one run directory under `artifacts/results/regime_engine/...` and confirm it contains the scenario hash, resolved regime payload, result JSON, and summary manifest needed for auditability.
- **OBS-001:** Record `regime_id`, registry version, assumption-set id, runtime, and solve status in every `run_manifest.json` so regression drift and monthly update deltas can be traced back to exact inputs.

## Risks and Alternatives
- **RISK-001:** The regime model may conflate retail TOU, export policy, and post-processing preview economics into a single opaque blob. Mitigation: keep regime bundles split into explicit `tariff_overrides`, `export_rule_overrides`, and `postprocess_overrides` sections.
- **RISK-002:** Hourly discretization still approximates 17:30 and 22:30 boundaries, so some regimes will remain directional rather than invoice-accurate. Mitigation: make this a standing caveat in reports and keep sub-hourly support as a separate future plan.
- **ALT-001:** Add only a `tou_regime` flag to the existing tariff builder and defer broader regulatory modeling. Rejected because the target product already spans export caps, two-part tariff trial logic, and BESS payment previews across multiple data files, so a TOU-only flag would force another interface migration later.
- **ALT-002:** Duplicate full tariff/export JSON files per regime and swap the active manifest pointer to compare scenarios. Rejected because it hides the true delta, increases maintenance burden, and weakens monthly update traceability.

## Grill Me
1. **Q-001:** Should the initial subscription archetype pack stop at `medium factory + one existing template`, or do you want a storage-heavy industrial archetype included from the first release?
   - **Recommended default:** Start with the medium-factory TOU reference case plus one existing template-based industrial/storage archetype.
   - **Why this matters:** It changes the acceptance scope for PHASE-04 and the default monthly refresh surface in PHASE-05.
   - **If answered differently:** Adding more archetypes early increases Phase 4/5 runtime, baseline volume, and reporting complexity but may improve commercial coverage.
2. **Q-002:** Should initial BESS capacity-payment regimes remain post-processing-only, or should they alter solve economics immediately?
   - **Recommended default:** Keep them post-processing-only in this plan.
   - **Why this matters:** The current repo has strong preprocessing and reporting seams, but no native Vietnam-specific capacity-payment objective hook inside the solve path.
   - **If answered differently:** PHASE-02 and PHASE-03 expand into solver customization, more integration risk, and materially larger regression coverage.

## Suggested Next Step
Answer the two Grill Me questions only if you want to override the defaults. Otherwise start PHASE-01 by adding the regime registry file, manifest entry, and Layer 1 validation checks.
