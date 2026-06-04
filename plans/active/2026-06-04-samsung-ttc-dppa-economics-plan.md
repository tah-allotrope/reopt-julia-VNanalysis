---
title: "Samsung–TTC Duc Hue 2 DPPA Economics Case"
date: "2026-06-04"
status: "draft"
request: "Model the economics of the Samsung SEVT ↔ TTC Duc Hue 2 grid-connected DPPA by cloning the synthetic/financial DPPA engine (dppa_case_2.py) with fixed solar sizing (~41.4 MWac / 70 GWh, no BESS), strike anchored to the Southern solar ceiling with a strike sweep up to EVN avoided cost, CfD settled against a CFMP proxy, buyer benchmarked vs EVN production tariff, stressed across regimes via the GAP-05 toggle (Decision 963 vs Decree 146), producing buyer-premium and developer-IRR/NPV surfaces plus an HTML report. Every headline number labeled directional with explicit strike + CFMP basis."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-06-04_samsung-ttc-dppa.md"
---

# Plan: Samsung–TTC Duc Hue 2 DPPA Economics Case

## Objective
Stand up a new `dppa_samsung_ttc` case that reuses the repo's tested synthetic/financial DPPA settlement engine to estimate the economics of Vietnam's first grid-connected DPPA (Samsung SEVT ↔ TTC Duc Hue 2, live 2026-06-01). Because all commercial terms are undisclosed, the deliverable is a *directional* buyer-premium and developer-IRR/NPV surface across a defensible strike band and regime set — not a single point estimate — with the strike and CFMP basis labeled on every output.

## Context Snapshot
- **Current state:** The repo has a fully tested synthetic/financial DPPA engine for the `ninhsim` Case 2 (`src/python/reopt_pysam_vn/integration/dppa_case_2.py`, Phases A–G) and a <1s regime toggle (`src/python/reopt_pysam_vn/reopt/regime_impact.py`, GAP-05). No Samsung/TTC case exists. The deal's physical facts are known (49 MWp / ~41.4 MWac southern ground-mount, ~70 GWh/yr, financial CfD); strike, tenor, KPP/grid fee are undisclosed (see research brief).
- **Desired state:** A new `dppa_samsung_ttc` module + case-data JSON + scripts + tests that (1) pin PV to the deal's fixed 49 MWp/70 GWh with no BESS, (2) generate a southern-Vietnam solar 8760 without requiring a Julia solve, (3) run the existing Case-2 settlement/benchmark/strike-sweep/developer surfaces with a strike anchored to the Southern solar ceiling, (4) stress the result across Decision 963 vs Decree 146 regimes, and (5) publish buyer-premium + developer-IRR/NPV surfaces and an HTML report.
- **Key repo surfaces:**
  - `src/python/reopt_pysam_vn/integration/dppa_case_2.py` — settlement engine to REUSE (`build_dppa_case_2_settlement_inputs`, `run_dppa_case_2_buyer_settlement`, `build_dppa_case_2_buyer_benchmark`, `build_dppa_case_2_strike_sensitivity`, `build_dppa_case_2_contract_risk_sensitivity`, `build_dppa_case_2_combined_decision_artifact`).
  - `src/python/reopt_pysam_vn/integration/bridge.py` — `build_dppa_case_2_single_owner_inputs` (PySAM developer screen).
  - `src/python/reopt_pysam_vn/integration/__init__.py` — package exports.
  - `src/python/reopt_pysam_vn/reopt/regime_impact.py` — `compute_multi_regime_impact`, `FORWARD_REGIME_PRESETS`, `build_regime_comparison` (GAP-05).
  - `src/python/reopt_pysam_vn/pysam/` — PySAM PVWatts/Single Owner runtime for fixed-size solar 8760 and developer IRR/NPV.
  - `data/vietnam/vn_tariff_2025.json` — base price 2,204.0655 VND/kWh, production multipliers, Decision 963 windows, Decree 57 solar ceilings (`ground_mounted_no_storage.range_min = 1012`), FX 26,400 VND/USD.
  - `scripts/python/integration/`, `tests/python/integration/` — script/test layout to mirror.
- **Out of scope:** Negotiating or sourcing the actual confidential strike/tenor; sourcing a Duc Hue 2 site-specific FMP/CFMP series (proxy only); modeling SEVT's full plant load beyond what is needed to match the 70 GWh contracted slice; any change to the existing Case 1/2/3 modules.

## Research Inputs
- `research/2026-06-04_samsung-ttc-dppa.md` — Supplies all disclosed deal facts (capacity, volume, parties, CfD mechanism), the financial triangulation (strike anchored to Southern ceiling ~1,012–1,150 VND/kWh; EVN avoided cost ~1,873–1,895 VND/kWh standard-hour; CFMP proxy; AC capacity factor ~19.3%; FX 26,400), and the concrete 6-point input mapping onto Case 2. This brief fixes the scope (fixed-sizing clone, not re-optimization), the strike band, and the directional-labeling requirement.

## Assumptions and Constraints
- **ASM-001:** The deal is a financial/CfD grid-connected DPPA; settlement is post-processed hourly CfD on the matched (contracted) solar volume — identical mechanism class to Case 2. (Research brief, Norton Rose.)
- **ASM-002:** Fixed plant: PV pinned to 49 MWp DC (~41.4 MWac, `dc_ac_ratio≈1.18`) calibrated to deliver ~70 GWh/yr; no BESS (deal has none). Solar profile sourced from southern Vietnam (Tay Ninh), not the buyer's northern location.
- **ASM-003:** Strike anchored to the Southern ground-mount no-storage ceiling (1,012 VND/kWh) as the base case, swept up to EVN avoided cost (~1,885 VND/kWh). Tenor defaults to 20 years (matches Case 2 `Financial.analysis_years = 20`).
- **ASM-004:** Market reference (CfD leg) uses the existing repo CFMP proxy (`build_dppa_case_2_market_proxy` / saigon18 transfer series), flagged `market_reference_price_type = proxy_cfmp_or_fmp`, transferred / not site-specific.
- **CON-001:** Every headline number must be emitted with an explicit `strike_basis` and `market_reference_price_type` field and a `directional` quality flag. No single number may be presented as the deal's actual economics.
- **CON-002:** Per-phase workflow follows repo convention: TDD red→green, then `/report <phase>`, then `git commit`, then `git push origin main`. Commits stay scoped to this case's new files; do not touch unrelated working-tree changes (`Manifest.toml`, `scripts/build_sysimage.ps1`, `tests/.stderr.tmp`, stray artifacts).
- **DEC-001 (computational lane):** Primary lane is **Python-only** — generate the fixed 49 MWp solar 8760 via PySAM PVWatts and run the Case-2 settlement post-processing directly, **with no Julia/REopt solve** (the deal is fixed-size, so there is nothing to optimize, and prior sessions repeatedly hit Julia cold-start timeouts). A REopt Julia solve with pinned sizing is an optional later validation, not on the critical path.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Case definition, Samsung data extract, fixed-sizing scenario | None | `dppa_samsung_ttc.py` (definition + extract + fixed scenario), case-data JSON, tests |
| PHASE-02 | Southern solar 8760 + buyer settlement + EVN benchmark | PHASE-01 | Solar generation series, buyer-settlement + buyer-benchmark artifacts, tests |
| PHASE-03 | Strike sweep (buyer-premium surface) + developer IRR/NPV | PHASE-02 | Strike-sensitivity + contract-risk + developer-screening artifacts, tests |
| PHASE-04 | Regime stress (GAP-05) + combined decision + HTML report | PHASE-03 | Multi-regime delta, combined-decision artifact, HTML report, tests |

## Detailed Phases

### PHASE-01 - Case Definition, Data Extract, and Fixed-Sizing Scenario
**Goal**
Create the `dppa_samsung_ttc` module skeleton that reuses Case 2's settlement helpers but provides Samsung-specific deal definition, a case-data `extracted` dict, and a fixed-sizing scenario (pinned PV, no BESS, Southern-ceiling strike anchor).

**Tasks**
- [ ] TASK-01-01: Add `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` with `build_samsung_ttc_definition(extracted)` recording disclosed facts (parties, 49 MWp/41.4 MWac, 70 GWh, Tay Ninh, financial CfD, COD 2026-05-19, DPPA live 2026-06-01) and `directional` quality flags.
- [ ] TASK-01-02: Add `scenarios/case_studies/samsung_ttc/samsung_ttc_case.json` holding the `extracted` contract: SEVT `site` (region=`south`, customer_type=`industrial`/production, voltage_level per Grill Me Q-002), `benchmark.exchange_rate_vnd_per_usd = 26400`, contracted volume 70 GWh, and a strike-basis block (`southern_ground_mount_ceiling_vnd_per_kwh = 1012`).
- [ ] TASK-01-03: Add `build_scenario_samsung_ttc(extracted)` — clone of `build_scenario_dppa_case_2` but PV `min_kw == max_kw` (49,000 DC), `ElectricStorage.max_kw == max_kwh == 0`, `Wind.max_kw == 0`, `dc_ac_ratio≈1.18`, Site lat/long = Tay Ninh, `_meta.scenario = "DPPA_SAMSUNG_TTC"`, `_meta.storage_requirement = "none_fixed_plant"`.
- [ ] TASK-01-04: Add a Samsung strike helper that anchors to the Southern ceiling band (override of `_strike_vnd_per_kwh`'s discount-off-EVN default) and is sweepable.
- [ ] TASK-01-05: Export new public functions from `src/python/reopt_pysam_vn/integration/__init__.py`.
- [ ] TASK-01-06: Add `tests/python/integration/test_dppa_samsung_ttc_phase_01.py` (red→green): definition records disclosed facts + directional flag; scenario PV is fixed (min==max==49000); storage disabled; strike base == 1012 within tolerance; FX == 26400.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` - new module (reuses Case 2 imports).
- `scenarios/case_studies/samsung_ttc/samsung_ttc_case.json` - new case data.
- `src/python/reopt_pysam_vn/integration/__init__.py` - add exports.
- `tests/python/integration/test_dppa_samsung_ttc_phase_01.py` - new tests.

**Dependencies**
- None (reuses existing Case 2 helpers as library functions).

**Exit Criteria**
- [ ] `pytest tests/python/integration/test_dppa_samsung_ttc_phase_01.py -q` PASS.
- [ ] Existing suite unaffected: `pytest tests/python/integration -q` and `pytest tests/python/reopt -q` still green.
- [ ] `/report` generated, committed, pushed to `origin/main`.

**Phase Risks**
- **RISK-01-01:** Diverging from Case 2 field names breaks settlement reuse downstream. Mitigation: keep the `extracted` dict shape byte-compatible with what `build_dppa_case_2_settlement_inputs` reads (`site`, `loads_kw`, `benchmark`, retail series).

### PHASE-02 - Southern Solar 8760 and Buyer Settlement
**Goal**
Generate the fixed 49 MWp southern-Vietnam solar 8760 via PySAM PVWatts (no Julia solve), assemble a REopt-shaped `results` dict from it, then run the existing Case-2 buyer-settlement and EVN benchmark on the matched 70 GWh.

**Tasks**
- [ ] TASK-02-01: Add `generate_samsung_ttc_solar_8760(extracted)` using `reopt_pysam_vn/pysam` PVWatts at Tay Ninh lat/long, fixed 49 MWp, calibrated to ~70 GWh/yr (assert within ±3%); return hourly kW.
- [ ] TASK-02-02: Add `build_samsung_ttc_results(solar_kw, extracted)` that packs the solar series into the REopt `results` shape the settlement engine expects (`PV.electric_to_load_series_kw` / `electric_to_grid_series_kw`), splitting against the buyer load per the matched-quantity rule.
- [ ] TASK-02-03: Add `analyze_samsung_ttc_settlement(extracted)` that calls `build_dppa_case_2_settlement_inputs` (CFMP proxy), `run_dppa_case_2_buyer_settlement`, and `build_dppa_case_2_buyer_benchmark`; emit artifacts under `artifacts/reports/samsung_ttc/`.
- [ ] TASK-02-04: Add `scripts/python/integration/analyze_samsung_ttc_dppa.py` runner.
- [ ] TASK-02-05: Tests (red→green) in `test_dppa_samsung_ttc_phase_02.py`: annual solar ≈ 70 GWh ±3%; matched_quantity ≈ contracted generation; benchmark uses EVN production tariff; `market_reference_price_type == "proxy_cfmp_or_fmp"`; settlement carries `directional` + strike/CFMP basis.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` - add generation + settlement wrappers.
- `scripts/python/integration/analyze_samsung_ttc_dppa.py` - new runner.
- `artifacts/reports/samsung_ttc/` - settlement + benchmark JSON outputs.
- `tests/python/integration/test_dppa_samsung_ttc_phase_02.py` - new tests.

**Dependencies**
- PHASE-01. PySAM installed (already a repo dependency; if unavailable, fall back to a cached/representative southern solar profile and flag it — see RISK-02-02).

**Exit Criteria**
- [ ] Settlement + benchmark artifacts written; annual solar within ±3% of 70 GWh.
- [ ] Buyer benchmark shows EVN-avoided-cost vs strike on the matched slice, labeled directional.
- [ ] Tests PASS; `/report`, commit, push.

**Phase Risks**
- **RISK-02-01:** Buyer load source is undecided (Grill Me Q-001); if the stand-in load is smaller than solar in midday hours, excess is excluded and matched < 70 GWh. Mitigation: default to a buyer load sized so solar is fully matched (model the contracted 70 GWh as the matched volume).
- **RISK-02-02:** PySAM not available in the environment. Mitigation: cache a representative southern-Vietnam PVWatts 8760 in `data/` and load it, flagging `solar_profile_source = cached_pvwatts_south`.

### PHASE-03 - Strike Sweep and Developer Screen
**Goal**
Produce the buyer-premium surface across the strike band (1,012 → ~1,885 VND/kWh) and the developer IRR/NPV via the PySAM Single Owner bridge, reusing Case 2's sensitivity and screening functions.

**Tasks**
- [ ] TASK-03-01: Wrap `build_dppa_case_2_strike_sensitivity` over the Samsung strike band (ceiling → EVN avoided cost) to produce the buyer-premium-vs-strike surface; emit `samsung_ttc_strike-sensitivity.json`.
- [ ] TASK-03-02: Wrap `build_dppa_case_2_contract_risk_sensitivity` for excess-generation / CfD stress; emit `samsung_ttc_contract-risk.json`.
- [ ] TASK-03-03: Build developer Single Owner inputs via `build_dppa_case_2_single_owner_inputs` at the fixed 49 MWp and strike band; run PySAM; emit `samsung_ttc_developer-screening.json` with after-tax IRR/NPV at each strike.
- [ ] TASK-03-04: Tests (red→green) in `test_dppa_samsung_ttc_phase_03.py`: buyer premium decreases monotonically as strike falls; developer NPV improves as strike rises; both surfaces carry directional + basis flags; sweep endpoints equal ceiling and avoided-cost anchors.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` - add sweep + developer wrappers.
- `scripts/python/integration/analyze_samsung_ttc_dppa.py` - extend to Phase 3.
- `artifacts/reports/samsung_ttc/*.json` - sweep + developer artifacts.
- `tests/python/integration/test_dppa_samsung_ttc_phase_03.py` - new tests.

**Dependencies**
- PHASE-02.

**Exit Criteria**
- [ ] Buyer-premium and developer-IRR/NPV surfaces written across the full strike band.
- [ ] The strike point where buyer premium turns favorable and where developer NPV turns positive are both reported (overlap band, if any).
- [ ] Tests PASS; `/report`, commit, push.

**Phase Risks**
- **RISK-03-01:** PySAM Single Owner returns null IRR for an all-equity / no-revenue config (seen in Case 2 Phase F). Mitigation: feed the strike as PPA price so developer revenue is non-null; assert NPV is finite at the ceiling strike.

### PHASE-04 - Regime Stress, Combined Decision, and HTML Report
**Goal**
Stress the buyer economics across regulatory regimes with the GAP-05 toggle, roll everything into one combined-decision artifact, and publish a client-readable HTML report — all labeled directional.

**Tasks**
- [ ] TASK-04-01: Use `compute_multi_regime_impact` + `FORWARD_REGIME_PRESETS` (`reopt/regime_impact.py`) to compare the buyer benchmark under Decision 963 (current) vs Decision 14 legacy vs `decree146_two_part_trial_2026`; emit `samsung_ttc_regime-stress.json` showing two-part-tariff erosion of buyer savings.
- [ ] TASK-04-02: Build `build_samsung_ttc_combined_decision(...)` (mirroring `build_dppa_case_2_combined_decision_artifact`) rolling up settlement, strike sweep, developer screen, and regime stress into one decision artifact with an explicit `recommended_position` and `directional` caveat.
- [ ] TASK-04-03: Add `scripts/python/integration/generate_samsung_ttc_dppa_report.py` producing `reports/2026-06-04-samsung-ttc-dppa.html` (Chart.js, explicit canvas heights per repo convention): deal facts, strike/CFMP basis banner, buyer-premium curve, developer-IRR/NPV curve, regime-stress bars, assumptions register.
- [ ] TASK-04-04: Tests (red→green) in `test_dppa_samsung_ttc_phase_04.py`: regime delta nonzero; two-part trial worsens buyer position vs 963; combined artifact exposes `recommended_position` + directional flag; report file generated and non-empty.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` - add combined-decision builder.
- `scripts/python/integration/generate_samsung_ttc_dppa_report.py` - new report generator.
- `reports/2026-06-04-samsung-ttc-dppa.html` - HTML report.
- `artifacts/reports/samsung_ttc/samsung_ttc_combined-decision.json` - combined artifact.
- `tests/python/integration/test_dppa_samsung_ttc_phase_04.py` - new tests.

**Dependencies**
- PHASE-03.

**Exit Criteria**
- [ ] HTML report renders all four sections with the directional / strike+CFMP basis banner.
- [ ] Combined-decision artifact states an explicit, caveated `recommended_position`.
- [ ] Full repo suite green; `/report`, commit, push.

**Phase Risks**
- **RISK-04-01:** Over-claiming a bankable conclusion from triangulated inputs. Mitigation: CON-001 enforced in the report banner and the combined artifact; conclusion framed as "directional under stated assumptions," not a deal verdict.

## Verification Strategy
- **TEST-001:** Per-phase pytest files (`test_dppa_samsung_ttc_phase_01..04.py`), each written red→green before implementation.
- **TEST-002:** Regression guard — `pytest tests/python/integration -q` and `pytest tests/python/reopt -q` stay green after every phase (Case 1/2/3 and GAP suites untouched).
- **MANUAL-001:** Open `reports/2026-06-04-samsung-ttc-dppa.html` in a browser; confirm all Chart.js canvases render and the directional/strike+CFMP basis banner is visible.
- **OBS-001:** Sanity arithmetic — annual solar ≈ 70 GWh (±3%); AC capacity factor ≈ 19%; developer strike revenue ≈ 70 GWh × strike; buyer benchmark ≈ 70 GWh × ~1,885 VND/kWh at the EVN-avoided anchor — matching the research brief's illustrative figures within rounding.

## Risks and Alternatives
- **RISK-001:** Headline numbers ride on an undisclosed strike and a proxy CFMP series. Mitigation: sweep instead of point-estimate; label basis on every artifact (CON-001).
- **RISK-002:** Julia cold-start blocking the pipeline. Mitigation: DEC-001 keeps the critical path Python-only; REopt solve is optional validation.
- **ALT-001:** Parametrize Case 2 in place (add a `fixed_sizing`/`samsung` flag) instead of a new module. Rejected: the repo's convention is one module per case (`dppa_case_1/2/3.py`); a new module keeps Case 2's tested surface frozen and the Samsung case independently reportable.
- **ALT-002:** Full REopt optimization of PV+BESS for the SEVT site. Rejected: the deal's plant is fixed and already built (49 MWp, no storage); optimization would answer a different question than "is this specific deal economic?"

## Grill Me
1. **Q-001:** What buyer load should the settlement use, given SEVT's real 8760 is not available and only 70 GWh of solar is contracted?
   - **Recommended default:** A buyer load sized so the 49 MWp solar is fully matched in all generating hours (i.e., treat the contracted 70 GWh as the matched volume; SEVT's true consumption far exceeds it). Flag `buyer_load_source = synthetic_fully_matching`.
   - **Why this matters:** Determines matched quantity, excess-generation exclusion, and therefore the buyer-premium magnitude.
   - **If answered differently:** Using the smaller `saigon18` real factory load would create midday excess (excluded), reducing matched volume below 70 GWh and understating both buyer settlement and developer strike revenue.
2. **Q-002:** What grid connection voltage should the EVN avoided-cost benchmark assume for SEVT?
   - **Recommended default:** `high_voltage_above_35kv_below_220kv` (110 kV) — standard multiplier 0.85 → ~1,873 VND/kWh; SEVT is a very large factory likely at 110 kV+.
   - **Why this matters:** Sets the EVN avoided-cost anchor (top of the strike sweep) and the buyer-saving magnitude.
   - **If answered differently:** 220 kV (0.84) or 22–110 kV (0.86) shift the avoided-cost anchor by ~1–2%, moving the favorable-strike threshold slightly.
3. **Q-003:** Should this pass include an optional REopt Julia solve with pinned sizing as a cross-check, or stay strictly Python-only?
   - **Recommended default:** Stay Python-only for all four phases (DEC-001); add the Julia cross-check only as a follow-on if a reviewer requires REopt-native flows.
   - **Why this matters:** Determines runtime, dependency surface, and exposure to Julia cold-start timeouts.
   - **If answered differently:** Adding the solve introduces a Julia dependency and minutes-scale runtime per phase but yields REopt-native hourly flows instead of PySAM-generated ones.

## Suggested Next Step
Answer the three Grill Me questions (defaults are safe to accept as-is), then begin PHASE-01: create `dppa_samsung_ttc.py` + case-data JSON + fixed-sizing scenario with the red→green tests, then `/report phase-01`, commit, and push.
