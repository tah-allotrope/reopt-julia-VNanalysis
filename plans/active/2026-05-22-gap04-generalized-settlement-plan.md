---
title: "GAP-04: Generalized Settlement Engine"
date: "2026-05-22"
status: "draft"
request: "Extract and parameterize the DPPA settlement engine from case-study-specific code into a shared module"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-04-07-vietnam-dppa-buyer-guide.md"
  - "research/2026-05-18_practical-refinements-operational-engine.md"
---

# Plan: GAP-04 — Generalized Settlement Engine

## Objective
Extract the hourly DPPA settlement logic from Case 2's `dppa_case_2.py` and the private-wire settlement from `dppa_case_1.py` / `dppa_settlement.py` into a shared, parameterized settlement module that any factory+project pair can use. This is a dependency for GAP-02 (procurement comparison) and a prerequisite for the Bankability Studio product concept.

## Context Snapshot
- **Current state:** Settlement logic is scattered across three files: `src/python/reopt_pysam_vn/integration/dppa_case_2.py` (strongest hourly buyer settlement with matched/shortfall/excess decomposition, ~800 lines, ninhsim-wired), `src/python/reopt_pysam_vn/integration/dppa_case_1.py` (private-wire tariff-ceiling screening), `scripts/python/reopt/dppa_settlement.py` (original CfD settlement with `compute_virtual_dppa_developer_revenue()`). All three are case-study-specific with hardcoded paths and assumptions.
- **Desired state:** A single `src/python/reopt_pysam_vn/integration/settlement.py` module that exposes `compute_settlement(mode, loads_kw, generation_kw, contract_params) -> SettlementResult` for both private-wire and virtual-CfD modes.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/integration/dppa_case_2.py` (canonical source — `buyer_settlement_ledger()`, `buyer_benchmark_artifact()`, `strike_negotiation_screen()`, `contract_risk_sensitivity()`), `src/python/reopt_pysam_vn/integration/dppa_case_1.py`, `scripts/python/reopt/dppa_settlement.py` (original `compute_dppa_settlement()`, `compute_virtual_dppa_developer_revenue()`).
- **Out of scope:** Monte Carlo risk simulation (Bankability Studio scope), lender-pack generation, multi-year cashflow waterfall, modification of existing case-study scripts.

## Research Inputs
- `research/2026-04-07-vietnam-dppa-buyer-guide.md` — Settlement payment stack must include: EVN base payment, CfD net payment (strike - FMP), matched-quantity rule, excess-generation treatment, DPPA adder, KPP, shortfall billing. All must be explicit parameters, not hardcoded.
- `research/2026-05-18_practical-refinements-operational-engine.md` — Financial post-processing modules have hardcoded constants and no integration with each other, preventing parameterized sensitivity analysis. This plan directly addresses that gap.

## Assumptions and Constraints
- **ASM-001:** The generalized settlement module is a refactoring/extraction, not a rewrite. Logic comes from Case 2's proven hourly settlement math.
- **ASM-002:** Existing case-study scripts (`dppa_case_1.py`, `dppa_case_2.py`) continue to work unchanged. They may be refactored to call the shared module in a future sprint, but not in this one.
- **CON-001:** FMP/CFMP market series are proxy-quality. The settlement engine must accept any 8760 market series and label its provenance in the output.
- **DEC-001:** The module lives at `src/python/reopt_pysam_vn/integration/settlement.py`.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Extract and parameterize hourly settlement logic for both modes | None | `settlement.py` with core functions, unit tests |
| PHASE-02 | Add contract-parameter presets, sensitivity sweep, and benchmark comparison | PHASE-01 | Contract presets, sweep function, benchmark tests |
| PHASE-03 | Add regression validation against existing Case 1 and Case 2 outputs | PHASE-02 | Regression tests, validation artifacts |

## Detailed Phases

### PHASE-01 - Core Settlement Extraction
**Goal**
Extract the hourly settlement math from Case 2 into parameterized functions supporting both private-wire and virtual-CfD modes.

**Tasks**
- [ ] TASK-01-01: Create `src/python/reopt_pysam_vn/integration/settlement.py` with `ContractParams` dataclass: `mode` (private_wire/virtual_cfd), `strike_vnd_kwh`, `escalation_rate`, `settlement_quantity_rule` (matched_only/contracted_volume), `excess_treatment` (curtail/export_at_surplus/cfd_on_excess), `export_cap_pct`, `surplus_rate_vnd_kwh`, `dppa_adder_vnd_kwh`, `kpp_pct`, `shortfall_billing` (evn_tariff/strike).
- [ ] TASK-01-02: Implement `compute_hourly_settlement(loads_kw, generation_kw, tariff_rates_kwh, fmp_vnd_mwh, contract_params) -> SettlementResult` that performs hourly decomposition: matched_kwh, shortfall_kwh, excess_kwh, exported_kwh, curtailed_kwh per hour.
- [ ] TASK-01-03: Implement `SettlementResult` dataclass: `hourly_ledger` (8760×N DataFrame or dict-of-lists), `annual_summary` (buyer_cost_vnd, buyer_savings_vs_evn_vnd, developer_revenue_vnd, matched_mwh, exported_mwh, curtailed_mwh, buyer_blended_rate_vnd_kwh), `contract_params` (echo back for traceability), `market_source_label`.
- [ ] TASK-01-04: Implement private-wire mode: matched energy at strike, residual on EVN tariff, excess subject to Decree 57 export cap and surplus purchase rate.
- [ ] TASK-01-05: Implement virtual-CfD mode: full EVN bill + CfD net payment (strike - FMP) on settlement quantity, excess per treatment rule.
- [ ] TASK-01-06: Add `tests/python/integration/test_settlement_generic.py` with tests for: private-wire with zero export (all matched), private-wire with export cap (20% Decree 57), virtual-CfD with positive and negative CfD hours, excess treatment variants.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/settlement.py` — New generalized settlement module.
- `tests/python/integration/test_settlement_generic.py` — Settlement unit tests.

**Dependencies**
- None

**Exit Criteria**
- [ ] `compute_hourly_settlement()` in private-wire mode produces annual buyer cost and developer revenue for synthetic inputs.
- [ ] `compute_hourly_settlement()` in virtual-CfD mode produces annual CfD net payment and developer revenue.
- [ ] All 8760 hours in the ledger sum correctly to annual totals.

**Phase Risks**
- **RISK-01-01:** Case 2's settlement logic may have implicit dependencies on ninhsim-specific data shapes. Mitigate by reading `dppa_case_2.py` carefully during extraction and testing with synthetic inputs first.

### PHASE-02 - Contract Presets and Sensitivity
**Goal**
Add named contract-parameter presets for common Vietnam DPPA structures and a sensitivity sweep function for strike-price analysis.

**Tasks**
- [ ] TASK-02-01: Add `PRESET_CONTRACTS` dict to `settlement.py` with named presets: `decree57_private_wire_standard` (20% cap, surplus at 671 VND/kWh), `virtual_cfd_matched_only` (matched-only settlement, curtail excess), `virtual_cfd_full_volume` (contracted volume settlement, CfD on excess), `physical_dppa_export_50pct` (draft 50% surplus rule).
- [ ] TASK-02-02: Implement `run_strike_sweep(loads_kw, generation_kw, tariff_rates, fmp_vnd_mwh, contract_preset, strike_range_vnd_kwh) -> list[SettlementResult]` that runs settlement at each strike point and returns a list of annual summaries.
- [ ] TASK-02-03: Implement `compute_buyer_benchmark(loads_kw, tariff_rates) -> BuyerBenchmark` that computes the EVN-only baseline cost for comparison.
- [ ] TASK-02-04: Add `tests/python/integration/test_settlement_presets.py` with tests for: each preset produces valid output, strike sweep returns correct number of results, benchmark cost matches hand-computed EVN total.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/settlement.py` — Presets and sweep added.
- `tests/python/integration/test_settlement_presets.py` — Preset and sweep tests.

**Dependencies**
- PHASE-01

**Exit Criteria**
- [ ] Each preset produces a valid `SettlementResult` with non-zero annual values.
- [ ] Strike sweep across 5%-15% below EVN produces monotonically decreasing buyer cost.

**Phase Risks**
- **RISK-02-01:** Preset parameter values may not match the latest regulatory state. Mitigate by sourcing values from `data/vietnam/vn_export_rules_decree57.json` and documenting the regulatory basis.

### PHASE-03 - Regression Validation Against Existing Cases
**Goal**
Prove that the generalized settlement engine reproduces existing Case 1 and Case 2 outputs when given the same inputs.

**Tasks**
- [ ] TASK-03-01: Extract the input parameters used in Case 1 (saigon18 private-wire) and run them through `compute_hourly_settlement()` in private-wire mode. Compare annual buyer cost and developer revenue against `artifacts/reports/saigon18/2026-03-29_scenario-d_dppa-settlement.json`.
- [ ] TASK-03-02: Extract the input parameters used in Case 2 (ninhsim CfD) and run them through `compute_hourly_settlement()` in virtual-CfD mode. Compare annual buyer cost against `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_buyer-settlement.json`.
- [ ] TASK-03-03: Add `tests/python/integration/test_settlement_regression.py` asserting < 1% deviation between generalized and case-specific outputs.
- [ ] TASK-03-04: Document any intentional deviations (e.g., bug fixes found during extraction) in the test file comments.

**Files / Surfaces**
- `tests/python/integration/test_settlement_regression.py` — Regression tests against existing case outputs.
- `artifacts/reports/saigon18/` — Case 1 reference outputs (read-only).
- `artifacts/reports/ninhsim/` — Case 2 reference outputs (read-only).

**Dependencies**
- PHASE-01, PHASE-02

**Exit Criteria**
- [ ] Generalized settlement on saigon18 inputs matches Case 1 output within 1%.
- [ ] Generalized settlement on ninhsim inputs matches Case 2 output within 1%.
- [ ] All regression tests pass.

**Phase Risks**
- **RISK-03-01:** Case-specific outputs may have been generated with slightly different assumptions than what's documented. Mitigate by reading the case-specific code to extract exact parameters, not just documented assumptions.

## Verification Strategy
- **TEST-001:** Run `python -m pytest tests/python/integration/test_settlement_generic.py tests/python/integration/test_settlement_presets.py tests/python/integration/test_settlement_regression.py -q` after each phase.
- **TEST-002:** Run `.\tests\run_all_tests.ps1 -SkipLayer4` to confirm no regressions in existing tests.
- **MANUAL-001:** Compare annual settlement totals between generalized and Case 2 outputs in a spreadsheet to verify the hourly math.

## Risks and Alternatives
- **RISK-001:** Extraction may reveal bugs in existing case-specific logic that were masked by hardcoded inputs. Mitigate by documenting and fixing in the generalized module while preserving backward compatibility.
- **ALT-001:** Instead of extracting, wrap existing case functions with adapter layers. Not chosen because the existing functions have hardcoded paths that make them non-reusable without modification.

## Grill Me
No open clarification questions. The scope is well-defined by the existing case-study implementations and the buyer-guide research.

## Suggested Next Step
Begin implementation with PHASE-01. This plan is a direct dependency for GAP-02 PHASE-01 and should be prioritized accordingly. Can be implemented in parallel with GAP-01 and GAP-03.
