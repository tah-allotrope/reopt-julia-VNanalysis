---
title: "GAP-05: Interactive Regulatory Scenario Toggle"
date: "2026-05-22"
status: "draft"
request: "Rapid regime comparison surface for client demo — toggle Decision 963 vs Decision 14 without Julia solve"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-04-25_vietnam-tou-rooftop-ppa.md"
  - "research/2026-05-07_vietnam-tou-tariff-implications.md"
---

# Plan: GAP-05 — Interactive Regulatory Scenario Toggle

## Objective
Build a rapid regulatory-scenario comparison surface that computes the tariff impact of Decision 963 vs Decision 14 (and forward-looking regimes) on a factory's energy bill in seconds, without requiring a Julia REopt solve. This is the "wow factor" for the client demo — instant regime comparison that shows the financial impact of the TOU shift on the factory's specific load shape.

## Context Snapshot
- **Current state:** The TOU regime engine (`regime_runner.py`, `vn_regime_registry_2026.json`) supports 5 regime bundles and can materialize and compare scenarios. However, it operates as a batch CLI pipeline that materializes full REopt scenario JSONs and requires Julia solve for financial results. `build_vietnam_tariff()` in `preprocess.py` can build 8760 TOU rate series for any regime in Python-only (no Julia needed). `verify_tou_scenarios.py` computes tariff hour differences between regimes.
- **Desired state:** A `compute_regime_impact(loads_kw, regime_a, regime_b, customer_type, voltage_level) -> RegimeImpact` function that returns annual bill delta, peak-hour consumption shift, and TOU impact summary in < 1 second, Python-only.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/reopt/preprocess.py` (`build_vietnam_tariff()`, `load_vietnam_data()`, `apply_vietnam_defaults()`), `data/vietnam/vn_regime_registry_2026.json` (5 regime bundles), `data/vietnam/vn_tariff_2025.json` (EVN tariff multipliers), `src/python/reopt_pysam_vn/reopt/regime_runner.py` (regime materialization), `scripts/python/reopt/verify_tou_scenarios.py` (tariff difference analysis).
- **Out of scope:** Julia solve integration, full REopt optimization under different regimes, web UI, real-time streaming.

## Research Inputs
- `research/2026-04-25_vietnam-tou-rooftop-ppa.md` — Decision 963 replaces split TOU peak (morning 09:30-11:30 + evening 17:00-20:00) with single evening 17:30-22:30. Solar-only avoided cost falls ~20-35%. BESS dispatch alignment improves but arbitrage spread narrows by ~50%. Two-shift operations face higher peak exposure.
- `research/2026-05-07_vietnam-tou-tariff-implications.md` — Quantitative tariff implications for the TOU shift on different load profiles and RE configurations.

## Assumptions and Constraints
- **ASM-001:** The regime toggle is Python-only and does not require Julia or REopt. It computes EVN bill impact by applying the 8760 TOU rate series to the factory's load profile under each regime.
- **ASM-002:** Solar/BESS value impact is estimated from load-shape analysis (peak-hour coverage, arbitrage window), not from a full optimization.
- **CON-001:** Decision 963 multipliers may not be final (MOIT has not confirmed whether Decision 14 multipliers are remapped or revised). The tool must support both cases as scenarios.
- **DEC-001:** The module lives at `src/python/reopt_pysam_vn/reopt/regime_impact.py` alongside the existing regime runner.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Build rapid EVN bill comparison for any factory load under two regimes | None | `regime_impact.py`, unit tests |
| PHASE-02 | Add solar/BESS value impact estimation and regime comparison artifact | PHASE-01 | RE impact estimates, JSON artifact, CLI |
| PHASE-03 | Add HTML report with Chart.js visualization and forward-regime scenarios | PHASE-02 | HTML report, forward regime support |

## Detailed Phases

### PHASE-01 - Rapid EVN Bill Regime Comparison
**Goal**
Compute the annual EVN bill for a factory under two regulatory regimes in under 1 second, Python-only.

**Tasks**
- [x] TASK-01-01: Create `src/python/reopt_pysam_vn/reopt/regime_impact.py` with `compute_regime_impact(loads_kw, regime_a_id, regime_b_id, customer_type, voltage_level) -> RegimeImpact`.
- [x] TASK-01-02: Implement `RegimeImpact` dataclass: `regime_a` (id, name, annual_bill_vnd, peak_consumption_mwh, offpeak_consumption_mwh, normal_consumption_mwh), `regime_b` (same fields), `delta` (annual_bill_delta_vnd, delta_pct, peak_hours_changed, peak_consumption_delta_mwh), `analysis_timestamp`, `customer_type`, `voltage_level`.
- [x] TASK-01-03: Use `load_vietnam_data()` and `build_vietnam_tariff()` to construct 8760 TOU rate arrays for both regimes, then multiply by `loads_kw` and sum for annual bills. This is the hot path and must complete in < 1 second.
- [x] TASK-01-04: Add peak/offpeak/normal hour classification for each regime using the TOU window definitions from `vn_tariff_2025.json`.
- [x] TASK-01-05: Add `tests/python/reopt/test_regime_impact.py` with tests for: Decision 963 vs Decision 14 on saigon18 load (expect bill change due to morning-peak removal), Decision 963 vs Decision 14 on a flat-load profile (expect smaller change), same-regime comparison (expect zero delta).

**Files / Surfaces**
- `src/python/reopt_pysam_vn/reopt/regime_impact.py` — New rapid comparison module.
- `src/python/reopt_pysam_vn/reopt/preprocess.py` — Consumed for `build_vietnam_tariff()`.
- `data/vietnam/vn_regime_registry_2026.json` — Regime bundle definitions.
- `tests/python/reopt/test_regime_impact.py` — Regime impact tests.

**Dependencies**
- None

**Exit Criteria**
- [x] `compute_regime_impact()` on saigon18 load returns a non-zero `annual_bill_delta_vnd` between Decision 963 and Decision 14.
- [x] Execution time < 1 second on a standard workstation.
- [x] `peak_hours_changed` correctly reflects the TOU window shift (morning peak hours removed, evening peak extended).

**Phase Risks**
- **RISK-01-01:** `build_vietnam_tariff()` may not support regime-specific TOU windows directly. Mitigate by extending it with a `regime_id` parameter if needed (the regime engine already does this via `resolve_vietnam_regime()`).

### PHASE-02 - Solar/BESS Value Impact and CLI
**Goal**
Add estimated solar and BESS value impact under each regime, produce a machine-readable artifact, and expose via CLI.

**Tasks**
- [x] TASK-02-01: Add `estimate_solar_value_impact(loads_kw, regime_a_tariff, regime_b_tariff, pv_profile_kw) -> SolarValueDelta` to `regime_impact.py`. Compute the avoided-cost value of solar generation under each regime's TOU rates (multiply PV output × TOU rate per hour, sum).
- [x] TASK-02-02: Add `estimate_bess_arbitrage_impact(regime_a_tariff, regime_b_tariff, bess_power_kw, bess_capacity_kwh) -> BessArbitrageDelta`. Compute theoretical arbitrage value: charge at offpeak, discharge at peak, under each regime. Report cycle count per day and annual arbitrage revenue.
- [x] TASK-02-03: Add `RegimeComparisonArtifact` that combines `RegimeImpact` + `SolarValueDelta` + `BessArbitrageDelta` into a single JSON artifact.
- [x] TASK-02-04: Create `scripts/python/reopt/compare_regimes.py` CLI accepting `--factory <path>`, `--regime-a <id>`, `--regime-b <id>`, `--customer-type`, `--voltage-level`, `--solar-profile <path>` (optional), `--bess-power <kw>` (optional), `--output <path>`.
- [x] TASK-02-05: Add `tests/python/reopt/test_regime_impact_solar_bess.py` with tests for: solar value drop under Decision 963 (morning peak lost), BESS arbitrage halving (one cycle vs two), combined artifact structure.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/reopt/regime_impact.py` — Solar/BESS impact functions added.
- `scripts/python/reopt/compare_regimes.py` — CLI entrypoint.
- `tests/python/reopt/test_regime_impact_solar_bess.py` — Solar/BESS impact tests.

**Dependencies**
- PHASE-01

**Exit Criteria**
- [x] Solar avoided-cost value under Decision 963 is lower than under Decision 14 for a daytime-generation profile (morning peak premium lost).
- [x] BESS arbitrage revenue under Decision 963 is approximately 50% of Decision 14 (one cycle vs two).
- [x] CLI produces a valid JSON artifact.

**Phase Risks**
- **RISK-02-01:** BESS arbitrage estimation is simplified (perfect foresight, no efficiency losses). Mitigate by labeling as "theoretical maximum" in the artifact and documentation.

### PHASE-03 - HTML Report and Forward Regimes
**Goal**
Generate an HTML report with Chart.js visualizations and add support for forward-looking regime scenarios.

**Tasks**
- [ ] TASK-03-01: Create `scripts/python/reopt/generate_regime_comparison_report.py` producing an HTML report with: factory load profile chart, TOU window comparison (color-coded hours), annual bill comparison bar chart, solar value impact chart, BESS arbitrage comparison, regulatory timeline.
- [ ] TASK-03-02: Add forward-regime presets to `regime_impact.py`: `decree57_rooftop_50pct_draft` (50% export cap), `decree146_two_part_trial_2026` (capacity + energy charges), `decision_963_2026_repriced_multipliers` (placeholder for revised multipliers).
- [ ] TASK-03-03: Support multi-regime comparison: `compute_multi_regime_impact(loads_kw, regime_ids, customer_type, voltage_level) -> list[RegimeImpact]` for sweeping across 3+ regimes in one call.
- [ ] TASK-03-04: Add `tests/python/reopt/test_regime_impact_multi.py` with tests for: 3-regime comparison, forward-regime preset validation.
- [ ] TASK-03-05: Create convenience wrapper at `scripts/python/compare_regimes.py`.

**Files / Surfaces**
- `scripts/python/reopt/generate_regime_comparison_report.py` — HTML report generator.
- `src/python/reopt_pysam_vn/reopt/regime_impact.py` — Multi-regime and forward-regime support.
- `tests/python/reopt/test_regime_impact_multi.py` — Multi-regime tests.

**Dependencies**
- PHASE-02

**Exit Criteria**
- [ ] HTML report renders in a browser with Chart.js bar charts and TOU window visualization.
- [ ] Multi-regime comparison produces results for at least 3 regimes in one call.
- [ ] Forward-regime presets are accessible and produce valid (even if placeholder) results.

**Phase Risks**
- **RISK-03-01:** Forward-regime data (e.g., repriced multipliers) may not exist yet. Mitigate by using placeholder multipliers and labeling as `provisional` in the artifact.

## Verification Strategy
- **TEST-001:** Run `python -m pytest tests/python/reopt/test_regime_impact*.py -q` after each phase.
- **TEST-002:** Run `.\tests\run_all_tests.ps1 -SkipLayer4` to confirm no regressions.
- **MANUAL-001:** Run `python scripts/python/reopt/compare_regimes.py --factory scenarios/case_studies/ninhsim/NinhsimSample.csv --regime-a decision_963_2026_current --regime-b decision_14_2025_legacy --customer-type industrial --voltage-level medium_voltage_22kv_to_110kv --output /tmp/regime_comparison.json` and verify the delta is non-zero.
- **MANUAL-002:** Open the generated HTML report and verify Chart.js renders correctly.

## Risks and Alternatives
- **RISK-001:** TOU rate multipliers for Decision 963 windows may change when MOIT issues the next circular. Mitigate by making multipliers data-driven from `vn_regime_registry_2026.json` rather than hardcoded.
- **ALT-001:** Run full Julia REopt solve under each regime instead of Python-only tariff math. Not chosen because solve takes 30-60s per regime, killing the "instant toggle" demo experience.

## Grill Me
1. **Q-001:** Should the regime toggle support custom user-defined regimes (e.g., "what if peak hours were 16:00-21:00?"), or only the pre-defined regimes in `vn_regime_registry_2026.json`?
   - **Recommended default:** Pre-defined regimes only, with `decision_963_2026_repriced_multipliers` as the placeholder for custom multiplier scenarios.
   - **Why this matters:** Custom regime support adds UI complexity and validation burden.
   - **If answered differently:** If custom regimes are needed, add a `custom_regime` parameter accepting raw TOU window definitions and multipliers.

## Suggested Next Step
Begin implementation with PHASE-01. This plan has no dependencies on other GAP plans and can start immediately. The rapid bill comparison (PHASE-01) is the highest-impact deliverable for the demo — a 1-second regime toggle on a real factory load.
