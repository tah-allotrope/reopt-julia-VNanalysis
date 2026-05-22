---
title: "GAP-02: Onsite vs Offsite Procurement Comparison Engine"
date: "2026-05-22"
status: "draft"
request: "Side-by-side onsite PPA vs offsite CfD DPPA evaluation for the same factory under Vietnam regulatory framework"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-04-07-vietnam-dppa-buyer-guide.md"
  - "research/2026-04-26_commercial-product-ideas.md"
  - "reports/2026-05-22-client-demo-gap-analysis.md"
---

# Plan: GAP-02 — Onsite vs Offsite Procurement Comparison Engine

## Objective
Build a unified procurement comparison workflow that evaluates the same factory under both onsite (private-wire PPA, behind-the-meter solar+BESS) and offsite (virtual/CfD DPPA, grid-connected RE project) energy procurement models, producing a single side-by-side decision artifact with buyer economics, developer returns, and regulatory risk flags under Vietnam's current framework (Decision 963, Decree 57). This is the core analytical product for the client demo — it answers the question "which procurement route is better for this factory?"

## Context Snapshot
- **Current state:** Cases 1-4 each evaluate one procurement model in isolation. Case 1 = private-wire PPA screening (`dppa_case_1.py`). Case 2 = synthetic financial DPPA with hourly buyer settlement (`dppa_case_2.py`). Case 3 = real-project bridge. Case 4 = planned but unimplemented. No single workflow produces a side-by-side comparison.
- **Desired state:** A `compare_procurement_options()` function that takes a factory load profile + candidate projects and produces a `ProcurementComparison` artifact with onsite vs offsite vs hybrid evaluation, buyer savings, developer returns, and a recommended procurement route.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/integration/dppa_case_1.py` (onsite settlement), `src/python/reopt_pysam_vn/integration/dppa_case_2.py` (offsite hourly settlement engine — canonical), `src/python/reopt_pysam_vn/integration/bridge.py` (PySAM developer finance), `src/python/reopt_pysam_vn/integration/strike_search.py` (strike discovery), `src/python/reopt_pysam_vn/reopt/preprocess.py` (tariff builder), `scripts/python/reopt/dppa_settlement.py` (original settlement logic).
- **Out of scope:** Portfolio optimization across multiple factories, hybrid onsite+offsite combination modeling (noted as future phase), lender-grade bankability pack (GAP-04 territory), web UI.

## Research Inputs
- `research/2026-04-07-vietnam-dppa-buyer-guide.md` — Confirms buyer-side synthetic DPPA payment stack must stay explicit (EVN payment + CfD +/- generator). Settlement quantity, excess-generation treatment, DPPA adder, KPP, and shortfall billing are core commercial design inputs.
- `research/2026-04-26_commercial-product-ideas.md` — Idea 1 (DPPA Deal Screener) directly consumes this comparison engine. Idea 3 (Bankability Studio) extends the settlement outputs. This plan is the MVP core of both.

## Assumptions and Constraints
- **ASM-001:** The comparison engine consumes factory load from GAP-01's `FactoryLoadResult` or from an existing `data/interim/<project>/` artifact.
- **ASM-002:** Onsite evaluation uses the existing `apply_vietnam_defaults()` preprocessing + REopt optimization. Offsite evaluation uses the Case 2 hourly settlement engine adapted for arbitrary factory+project pairs.
- **ASM-003:** Developer returns are computed via PySAM `Single Owner` bridge for both onsite and offsite, using the same finance assumptions for fair comparison.
- **CON-001:** REopt Julia solve takes 30-60s per scenario. For the demo, pre-computed results may be necessary; the comparison engine must accept both live-solve and pre-computed result inputs.
- **CON-002:** FMP/CFMP market reference series are proxy-quality (transferred from saigon18). CfD settlement outputs must be labeled as "indicative" until actual market data is available.
- **DEC-001:** The comparison module lives in `src/python/reopt_pysam_vn/integration/procurement.py` as a new module alongside existing case modules.
- **DEC-002:** Onsite = behind-the-meter, private-wire PPA, Decree 57 export rules apply. Offsite = grid-connected, virtual CfD DPPA, wholesale market settlement.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Extract and parameterize the settlement engines for arbitrary factory+project pairs | None | `src/python/reopt_pysam_vn/integration/settlement.py` |
| PHASE-02 | Build onsite and offsite evaluation pipelines using parameterized settlement | PHASE-01 | `src/python/reopt_pysam_vn/integration/procurement.py` |
| PHASE-03 | Build side-by-side comparison artifact and decision logic | PHASE-02 | Comparison JSON artifact, decision matrix |
| PHASE-04 | Add CLI entrypoint, HTML report, and end-to-end validation | PHASE-03 | CLI script, HTML report, integration tests |

## Detailed Phases

### PHASE-01 - Parameterized Settlement Engines
**Goal**
Extract the hourly settlement logic from `dppa_case_2.py` and the private-wire logic from `dppa_case_1.py` into a shared, parameterized settlement module that accepts arbitrary factory+project inputs.

**Tasks**
- [ ] TASK-01-01: Create `src/python/reopt_pysam_vn/integration/settlement.py` with two core functions: `compute_onsite_settlement(loads_kw, generation_kw, tariff_rates, strike_vnd_kwh, export_cap_pct, surplus_rate_vnd_kwh) -> OnsiteSettlement` and `compute_offsite_settlement(loads_kw, generation_kw, tariff_rates, strike_vnd_kwh, fmp_vnd_mwh, settlement_quantity_rule, excess_treatment) -> OffsiteSettlement`.
- [ ] TASK-01-02: Port the hourly settlement math from `dppa_case_2.py::buyer_settlement_ledger()` into `compute_offsite_settlement()`, replacing ninhsim-specific paths with parameters. Preserve the matched/shortfall/excess hourly decomposition.
- [ ] TASK-01-03: Port the private-wire settlement math from `dppa_case_1.py` and `dppa_settlement.py` into `compute_onsite_settlement()`, including Decree 57 export-cap application and surplus purchase rate.
- [ ] TASK-01-04: Define `OnsiteSettlement` and `OffsiteSettlement` dataclasses with standardized fields: `annual_buyer_cost_vnd`, `annual_buyer_savings_vs_evn_vnd`, `annual_developer_revenue_vnd`, `matched_kwh`, `exported_kwh`, `curtailed_kwh`, `buyer_blended_rate_vnd_kwh`, `hourly_ledger` (optional, for detailed analysis).
- [ ] TASK-01-05: Add `tests/python/integration/test_settlement_engine.py` with failing-then-passing tests: onsite settlement on saigon18 inputs (compare against Case 1 existing outputs), offsite settlement on ninhsim inputs (compare against Case 2 existing outputs).

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/settlement.py` — New shared settlement module.
- `src/python/reopt_pysam_vn/integration/dppa_case_2.py` — Source for offsite settlement logic (read-only reference).
- `src/python/reopt_pysam_vn/integration/dppa_case_1.py` — Source for onsite settlement logic (read-only reference).
- `tests/python/integration/test_settlement_engine.py` — Settlement engine unit tests.

**Dependencies**
- None

**Exit Criteria**
- [ ] `compute_offsite_settlement()` on ninhsim inputs produces `annual_buyer_cost_vnd` within 1% of existing Case 2 buyer settlement output.
- [ ] `compute_onsite_settlement()` on saigon18 inputs produces results consistent with existing Case 1 outputs.
- [ ] Both functions accept arbitrary 8760 load and generation series without any case-study-specific hardcoding.

**Phase Risks**
- **RISK-01-01:** Case 1 and Case 2 settlement logic may have subtle differences in how they handle edge cases (zero-generation hours, negative FMP). Mitigate by adding edge-case test coverage and documenting any normalization decisions.

### PHASE-02 - Onsite and Offsite Evaluation Pipelines
**Goal**
Build the evaluation pipelines that take a factory load + project definition and produce buyer+developer economics for both procurement modes.

**Tasks**
- [ ] TASK-02-01: Create `src/python/reopt_pysam_vn/integration/procurement.py` with `evaluate_onsite(factory_load, project_config, tariff_params, strike_params) -> OnsiteEvaluation` and `evaluate_offsite(factory_load, project_config, tariff_params, strike_params, market_params) -> OffsiteEvaluation`.
- [ ] TASK-02-02: Implement `OnsiteEvaluation`: run REopt scenario builder with factory load + onsite project sizing → extract solved generation profile → run `compute_onsite_settlement()` → run PySAM `Single Owner` for developer returns → package results.
- [ ] TASK-02-03: Implement `OffsiteEvaluation`: take offsite project generation profile (from project catalog or pre-solved) → run `compute_offsite_settlement()` → run PySAM `Single Owner` for developer returns → package results.
- [ ] TASK-02-04: Define `ProjectConfig` dataclass consumed by both pipelines: `project_id`, `technology`, `capacity_mw`, `bess_mw`, `bess_mwh`, `location`, `grid_connection` (onsite/offsite), `generation_profile_kw` (8760, optional — if missing, use PVWatts via coordinates).
- [ ] TASK-02-05: Add `tests/python/integration/test_procurement.py` with tests for: onsite evaluation on saigon18 (fixed sizing, no-solve mode using pre-computed results), offsite evaluation on ninhsim (using existing solved results).

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/procurement.py` — Procurement evaluation module.
- `src/python/reopt_pysam_vn/integration/bridge.py` — PySAM developer finance bridge (consumed).
- `src/python/reopt_pysam_vn/reopt/preprocess.py` — Tariff construction (consumed).
- `tests/python/integration/test_procurement.py` — Evaluation pipeline tests.

**Dependencies**
- PHASE-01

**Exit Criteria**
- [ ] `evaluate_onsite()` produces buyer savings and developer IRR for a saigon18-like input.
- [ ] `evaluate_offsite()` produces buyer CfD costs and developer IRR for a ninhsim-like input.
- [ ] Both evaluations use the same PySAM finance assumptions for fair comparison.

**Phase Risks**
- **RISK-02-01:** REopt solve may fail or timeout for some factory+project combinations. Mitigate by supporting pre-computed result input (`result_json_path` parameter) so the demo can use pre-solved scenarios.

### PHASE-03 - Side-by-Side Comparison and Decision Logic
**Goal**
Produce a single comparison artifact that places onsite and offsite evaluations side-by-side with a recommendation.

**Tasks**
- [ ] TASK-03-01: Add `compare_procurement_options(onsite_eval, offsite_eval, factory_metadata) -> ProcurementComparison` to `procurement.py`.
- [ ] TASK-03-02: Implement `ProcurementComparison` with: `factory_summary` (from GAP-01 metadata), `onsite_summary` (buyer cost, savings, developer IRR, RE penetration, export exposure), `offsite_summary` (buyer cost, CfD net, developer IRR, RE penetration, FMP risk), `delta` (cost difference, savings difference, IRR difference), `recommendation` (onsite/offsite/neither with reason), `regulatory_flags` (export-cap utilization, FMP volatility exposure, Decree 57 compliance).
- [ ] TASK-03-03: Implement recommendation logic: prefer the option with lower buyer blended cost and positive developer returns. Flag `neither` if both options produce buyer premium or negative developer NPV.
- [ ] TASK-03-04: Add `tests/python/integration/test_procurement_comparison.py` with tests for: comparison artifact structure, recommendation logic (buyer-favorable onsite wins, buyer-favorable offsite wins, neither-viable case).

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/procurement.py` — Comparison logic added.
- `tests/python/integration/test_procurement_comparison.py` — Comparison tests.

**Dependencies**
- PHASE-02

**Exit Criteria**
- [ ] `compare_procurement_options()` produces a complete `ProcurementComparison` with non-null fields in all sections.
- [ ] Recommendation logic correctly picks the lower-cost option in test cases.

**Phase Risks**
- **RISK-03-01:** Comparison may not be apples-to-apples if onsite and offsite projects have very different capacities. Mitigate by normalizing to per-kWh metrics and documenting the capacity mismatch.

### PHASE-04 - CLI, Report, and End-to-End Validation
**Goal**
Wire the comparison engine into a runnable CLI script, generate an HTML report, and validate the full pipeline end-to-end.

**Tasks**
- [ ] TASK-04-01: Create `scripts/python/integration/compare_procurement.py` CLI accepting `--factory <path>`, `--onsite-project <path_or_config>`, `--offsite-project <path_or_config>`, `--output <path>`, `--report <path>`.
- [ ] TASK-04-02: Create `scripts/python/integration/generate_procurement_report.py` producing an HTML report with: factory load summary, onsite economics table, offsite economics table, side-by-side delta chart (Chart.js bar chart), recommendation callout, regulatory flags section.
- [ ] TASK-04-03: Run end-to-end validation: saigon18 factory load → onsite (40 MWp solar + 66 MWh BESS private-wire) vs offsite (ninhsim-style CfD) → comparison artifact → HTML report.
- [ ] TASK-04-04: Add `tests/python/integration/test_procurement_e2e.py` validating the full pipeline from factory input to comparison output.
- [ ] TASK-04-05: Create convenience wrapper at `scripts/python/compare_procurement.py`.

**Files / Surfaces**
- `scripts/python/integration/compare_procurement.py` — CLI entrypoint.
- `scripts/python/integration/generate_procurement_report.py` — HTML report generator.
- `tests/python/integration/test_procurement_e2e.py` — End-to-end tests.

**Dependencies**
- PHASE-03, GAP-01 (for factory ingestion, but can use pre-built artifacts)

**Exit Criteria**
- [ ] `python scripts/python/integration/compare_procurement.py --factory data/interim/saigon18/... --onsite-project ... --offsite-project ... --output /tmp/comparison.json --report /tmp/comparison.html` produces valid JSON and HTML.
- [ ] HTML report renders correctly in a browser with Chart.js visualizations.
- [ ] All procurement tests pass: `python -m pytest tests/python/integration/test_settlement_engine.py tests/python/integration/test_procurement.py tests/python/integration/test_procurement_comparison.py tests/python/integration/test_procurement_e2e.py -q`.

**Phase Risks**
- **RISK-04-01:** HTML report generation may conflict with existing report patterns if Chart.js versions differ. Mitigate by reusing the existing `report-template.html` shell.

## Verification Strategy
- **TEST-001:** Run `python -m pytest tests/python/integration/test_settlement_engine.py tests/python/integration/test_procurement*.py -q` after each phase.
- **TEST-002:** Run `.\tests\run_all_tests.ps1 -SkipLayer4` to confirm no regressions.
- **MANUAL-001:** Verify that onsite settlement on saigon18 data matches the existing Case 1 settlement output within 5%.
- **MANUAL-002:** Verify that offsite settlement on ninhsim data matches the existing Case 2 buyer settlement output within 1%.
- **MANUAL-003:** Open the HTML comparison report in a browser and confirm Chart.js renders and the recommendation text is non-empty.

## Risks and Alternatives
- **RISK-001:** The generalized settlement engine may diverge from case-study-specific logic that was tuned for particular projects. Mitigate by running regression tests against existing case outputs.
- **RISK-002:** Pre-computed REopt results may not exist for arbitrary factory+project combinations during the demo. Mitigate by pre-solving 2-3 representative scenarios before the demo.
- **ALT-001:** Skip generalization and hardcode a saigon18-vs-ninhsim comparison. Not chosen because it doesn't scale and teaches the team nothing reusable.

## Grill Me
1. **Q-001:** Should the comparison include a hybrid option (onsite PV + offsite CfD simultaneously) in this sprint, or defer it?
   - **Recommended default:** Defer hybrid to a follow-up sprint. Focus on clean onsite vs offsite comparison first.
   - **Why this matters:** Hybrid modeling doubles the settlement complexity and requires split-load logic.
   - **If answered differently:** If hybrid is needed for demo, add a PHASE-05 that combines onsite residual load with offsite CfD and produces a three-way comparison.

2. **Q-002:** What strike-price basis should the default comparison use: 5% below EVN, 15% below EVN, or both as a sensitivity?
   - **Recommended default:** 5% below EVN as base, with a note that strike sensitivity is available via the existing `strike_search.py` module.
   - **Why this matters:** The strike choice determines whether the comparison shows buyer savings or buyer premium.
   - **If answered differently:** If both are needed in the comparison artifact, add a `strike_scenarios` list and loop the evaluation.

## Suggested Next Step
Answer the Grill Me questions, then begin implementation with PHASE-01 (the parameterized settlement engine is the foundation). GAP-01 can proceed in parallel since this plan can use existing `data/interim/` artifacts until the generic ingestion module is ready.
