---
title: "GAP-03: Developer Project Catalog and Matching Engine"
date: "2026-05-22"
status: "draft"
request: "Developer project catalog schema and factory-to-project matching engine for client demo"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-04-26_commercial-product-ideas.md"
  - "reports/2026-05-22-client-demo-gap-analysis.md"
---

# Plan: GAP-03 — Developer Project Catalog and Matching Engine

## Objective
Create a structured developer project catalog as a versioned data layer and build a matching engine that scores project-factory pairs for physical, geographic, capacity, commercial, and regulatory fit. This enables the demo narrative: "here are the available developer projects that fit your factory."

## Context Snapshot
- **Current state:** Each case study hardcodes one project configuration. `rank_case_study_offtakers.py` ranks factories for a fixed project (inverse of what the demo needs). No concept of "available developer projects" as a data structure. Six case studies exist with different project archetypes: saigon18 (40 MWp onsite solar+BESS), ninhsim (optimized solar+wind+BESS CPPA), north_thuan (30 MW solar+wind offsite).
- **Desired state:** A `data/projects/` catalog with 3-5 seed projects, and a `match_projects_to_factory(factory_load, project_catalog) -> MatchResult` function that returns a ranked list of compatible projects with fit scores and explanations.
- **Key repo surfaces:** `scripts/python/integration/rank_case_study_offtakers.py` (physical-match scoring logic — source for inversion), `src/python/reopt_pysam_vn/reopt/preprocess.py` (tariff computation for commercial fit), `data/vietnam/vn_tariff_2025.json` (EVN rate benchmarks), `scenarios/case_studies/` (source of seed project data).
- **Out of scope:** Project creation UI, developer self-registration, real-time project inventory sync, detailed project financial modeling (that's GAP-02/GAP-04 territory).

## Research Inputs
- `research/2026-04-26_commercial-product-ideas.md` — Idea 1 (DPPA Deal Screener) requires a site-data service and project catalog. This plan delivers the catalog data layer and matching logic.

## Assumptions and Constraints
- **ASM-001:** The project catalog is a directory of JSON files, one per project, under `data/projects/`. This mirrors the `data/vietnam/` versioned-data pattern.
- **ASM-002:** Seed data is derived from existing case studies and the real-project basis in `AGENTS.md` (3.2 MWp PV, 1 MW/2.2 MWh BESS, 22kV).
- **ASM-003:** Matching is heuristic scoring, not optimization. The engine ranks and explains — it does not prescribe.
- **CON-001:** Generation profiles for offsite projects may not be available. Matching must work with capacity-only metadata and degrade gracefully when 8760 profiles are available.
- **DEC-001:** Matching direction is factory→projects (which projects fit this factory?), not project→factories.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Define project catalog schema and seed with 5 representative projects | None | `data/projects/` catalog, schema validation |
| PHASE-02 | Build matching engine with multi-dimensional scoring | PHASE-01 | `src/python/reopt_pysam_vn/integration/matching.py`, tests |
| PHASE-03 | Add CLI entrypoint, ranked output artifact, and validation against case studies | PHASE-02 | CLI script, match result artifacts, integration tests |

## Detailed Phases

### PHASE-01 - Project Catalog Schema and Seed Data
**Goal**
Define the project catalog schema, create the data directory, and seed it with 5 representative projects derived from existing case studies and the real-project basis.

**Tasks**
- [ ] TASK-01-01: Create `data/projects/catalog_schema.json` defining the project record schema with fields: `project_id`, `name`, `developer`, `location` (lat, lon, province, region), `technology` (solar/wind/solar_bess/wind_bess/hybrid), `capacity_mw`, `bess_mw`, `bess_mwh`, `grid_connection` (onsite_private_wire/grid_connected_22kv/grid_connected_110kv), `indicative_strike_usc_kwh`, `available_from`, `dppa_structure` (private_wire/virtual_cfd/physical_dppa), `status` (operational/construction/development/prospective), `generation_profile_path` (optional path to 8760 JSON), `notes`.
- [ ] TASK-01-02: Create `data/projects/saigon18_onsite_solar_bess.json` — 40.36 MWp PV + 20 MW/66 MWh BESS, onsite private-wire, south region, derived from saigon18 case study.
- [ ] TASK-01-03: Create `data/projects/ninhsim_offsite_solar_wind.json` — 14 MW PV + 40 MW wind, grid-connected virtual CfD, south region, derived from ninhsim optimized result.
- [ ] TASK-01-04: Create `data/projects/north_thuan_offsite_solar_wind_bess.json` — 30 MW solar + 20 MW wind + 10 MW/40 MWh BESS, grid-connected, central region, derived from north_thuan.
- [ ] TASK-01-05: Create `data/projects/real_project_onsite_solar_bess.json` — 3.2 MWp PV + 1 MW/2.2 MWh BESS, onsite 22kV, south region, derived from AGENTS.md real-project basis.
- [ ] TASK-01-06: Create `data/projects/prospective_offsite_wind.json` — 50 MW wind, grid-connected 110kV, central region, prospective status, to demonstrate matching against a large-scale project.
- [ ] TASK-01-07: Add `tests/python/integration/test_project_catalog.py` with schema validation tests for all 5 seed projects.

**Files / Surfaces**
- `data/projects/` — New catalog directory with schema and 5 seed projects.
- `tests/python/integration/test_project_catalog.py` — Schema validation tests.

**Dependencies**
- None

**Exit Criteria**
- [ ] All 5 seed projects pass schema validation.
- [ ] Each project has a valid `project_id`, `technology`, `capacity_mw`, `grid_connection`, and `dppa_structure`.

**Phase Risks**
- **RISK-01-01:** Indicative strike prices for seed projects may not be well-calibrated. Mitigate by deriving from existing case-study results and labeling as `indicative_staging`.

### PHASE-02 - Multi-Dimensional Matching Engine
**Goal**
Build a matching engine that scores project-factory pairs across 5 dimensions and returns a ranked list with explanations.

**Tasks**
- [ ] TASK-02-01: Create `src/python/reopt_pysam_vn/integration/matching.py` with `match_projects_to_factory(factory_load_result, project_catalog, tariff_params) -> list[ProjectMatch]`.
- [ ] TASK-02-02: Implement `ProjectMatch` dataclass: `project_id`, `project_name`, `overall_score` (0-100), `dimension_scores` (dict of 5 dimensions), `fit_explanation` (human-readable string), `flags` (list of warnings/blockers).
- [ ] TASK-02-03: Implement physical fit scoring (0-100): if project has a generation profile, compute hourly load-vs-generation overlap using the same logic as `rank_case_study_offtakers.py` (self-consumption ratio, curtailment ratio, BESS absorption headroom). If no generation profile, estimate from capacity vs peak demand ratio.
- [ ] TASK-02-04: Implement geographic fit scoring (0-100): same-region = 100, adjacent-region = 70, cross-country = 40. For onsite projects, require same location (score 0 if not co-located). For offsite, deduct based on distance proxy.
- [ ] TASK-02-05: Implement capacity fit scoring (0-100): project annual generation vs factory annual consumption ratio. Score peaks at 0.3-0.7 ratio (sweet spot for DPPA), degrades for undersized (< 0.1) or oversized (> 1.5).
- [ ] TASK-02-06: Implement commercial fit scoring (0-100): compare project indicative strike vs factory EVN baseline cost. Positive buyer savings = high score, buyer premium = low score, missing strike data = neutral (50).
- [ ] TASK-02-07: Implement regulatory fit scoring (0-100): check Decree 57 export-cap headroom for onsite, grid-connection voltage compatibility, DPPA structure eligibility. Flag blockers (e.g., private-wire project can't serve an offsite factory).
- [ ] TASK-02-08: Add `tests/python/integration/test_matching.py` with tests for: saigon18 factory matched against all 5 projects (expect onsite solar+BESS to rank highest), ninhsim factory matched against all 5 projects, edge case where no project is viable.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/matching.py` — Matching engine.
- `scripts/python/integration/rank_case_study_offtakers.py` — Source of physical-fit scoring logic (read-only reference for inversion).
- `tests/python/integration/test_matching.py` — Matching engine tests.

**Dependencies**
- PHASE-01

**Exit Criteria**
- [ ] `match_projects_to_factory()` returns a ranked list for saigon18 factory with the onsite project scoring highest in physical fit.
- [ ] Each `ProjectMatch` has non-zero scores in all 5 dimensions.
- [ ] Regulatory fit correctly flags private-wire projects as incompatible with offsite factories.

**Phase Risks**
- **RISK-02-01:** Scoring weights across dimensions are subjective. Mitigate by using equal weights (20% each) as default and documenting the weight choice.

### PHASE-03 - CLI, Output Artifact, and Validation
**Goal**
Wire the matching engine into a CLI, produce a ranked match artifact, and validate against existing case studies.

**Tasks**
- [ ] TASK-03-01: Create `scripts/python/integration/match_factory_to_projects.py` CLI accepting `--factory <path>` (ingested load artifact or raw file), `--catalog <dir>` (default: `data/projects/`), `--output <path>`, `--top-n <int>` (default: 5).
- [ ] TASK-03-02: Implement match result JSON artifact with: `factory_summary`, `matches` (ranked list of `ProjectMatch`), `catalog_size`, `match_timestamp`, `scoring_weights`.
- [ ] TASK-03-03: Run matching for all 6 existing case-study factories against the 5-project catalog and verify results are directionally reasonable.
- [ ] TASK-03-04: Add `tests/python/integration/test_matching_e2e.py` validating the full CLI pipeline.
- [ ] TASK-03-05: Create convenience wrapper at `scripts/python/match_factory_to_projects.py`.

**Files / Surfaces**
- `scripts/python/integration/match_factory_to_projects.py` — CLI entrypoint.
- `scripts/python/match_factory_to_projects.py` — Top-level wrapper.
- `tests/python/integration/test_matching_e2e.py` — End-to-end tests.

**Dependencies**
- PHASE-02, GAP-01 PHASE-01 (for `FactoryLoadResult`, but can use raw files directly)

**Exit Criteria**
- [ ] `python scripts/python/match_factory_to_projects.py --factory scenarios/case_studies/ninhsim/NinhsimSample.csv --output /tmp/matches.json` produces a valid ranked match artifact.
- [ ] All matching tests pass: `python -m pytest tests/python/integration/test_project_catalog.py tests/python/integration/test_matching.py tests/python/integration/test_matching_e2e.py -q`.

**Phase Risks**
- **RISK-03-01:** Auto-detection of load column from raw files may fail without GAP-01 ingestion module. Mitigate by accepting both raw files (with `--column` hint) and pre-ingested artifacts.

## Verification Strategy
- **TEST-001:** Run `python -m pytest tests/python/integration/test_project_catalog.py tests/python/integration/test_matching*.py -q` after each phase.
- **TEST-002:** Run `.\tests\run_all_tests.ps1 -SkipLayer4` to confirm no regressions.
- **MANUAL-001:** Review the ranked match output for saigon18 and confirm the top match is intuitively correct (onsite solar+BESS for a large factory in the south).

## Risks and Alternatives
- **RISK-001:** The 5-project seed catalog may be too small to demonstrate meaningful matching differentiation. Mitigate by ensuring projects span different technologies, sizes, regions, and DPPA structures.
- **ALT-001:** Instead of a file-based catalog, use a SQLite database. Not chosen because JSON files are simpler, version-controlled, and consistent with the repo's `data/vietnam/` pattern.

## Grill Me
1. **Q-001:** Should the project catalog include actual generation profiles (8760 arrays), or just metadata with capacity figures?
   - **Recommended default:** Metadata only for seed data, with optional `generation_profile_path` field pointing to a separate 8760 JSON. Populate profiles for saigon18 and north_thuan (which already have solved results with generation data).
   - **Why this matters:** With profiles, physical-fit scoring is precise. Without profiles, it's estimated from capacity ratios.
   - **If answered differently:** If all profiles are required, add a sub-task to extract generation profiles from existing REopt results for each seed project.

## Suggested Next Step
Answer the Grill Me question, then begin with PHASE-01 (catalog schema and seed data). This plan has no dependency on GAP-01 or GAP-02 and can start immediately.
