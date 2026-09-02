# DPPA Case 3 Plan vs Implementation Review

Date: 2026-04-21

Plan under review: `plans/active/dppa_case_3_plan.md`

Primary implementation surfaces reviewed:

- `src/python/reopt_pysam_vn/integration/dppa_case_3.py`
- `scripts/python/integration/prepare_saigon18_dppa_case_3_phase_ab.py`
- `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py`
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_cd.py`
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_e.py`
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py`
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f_22kv.py`
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_g.py`
- `scripts/python/integration/generate_dppa_case_3_final_report.py`
- `scripts/julia/run_bounded_opt_solve.jl`
- `scripts/julia/run_bounded_opt_22kv_solve.jl`

Supporting evidence reviewed:

- `tests/python/integration/test_dppa_case_3_phase_ab.py`
- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_phase-cd-combined.json`
- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_phase-e-controller-gap.json`
- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_developer-screening.json`
- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_combined-decision.json`
- `reports/2026-04-21-dppa-case-3-final.html`

## Bottom line

The implementation is strongest in **Phase A/B definition work** and in the fact that **the bounded-opt REopt solve did run with a real storage floor and did not collapse to PV-only**.

However, the later phases are only **partially aligned** with the original plan. The repo currently has a **directionally plausible reject signal**, but not a fully trustworthy, decision-grade implementation of the full Case 3 plan.

The biggest reasons are:

1. **Phase D buyer settlement is not branch-faithful or hourly-faithful**; it uses annual totals and average prices instead of the promised hourly settlement logic.
2. **The 22kV two-part branch is only partially implemented**; the real demand-charge branch logic and side-by-side delta reporting are still missing.
3. **Phase E controller analysis is numerically flawed** and compares different physical candidates instead of the same bounded-opt candidate under two dispatch modes.
4. **Phase F runs PySAM successfully**, but the planned REopt-vs-PySAM comparison artifact is missing and key output extraction is buggy.
5. **Phase G combined aggregation has real data-wiring bugs**, and the final HTML report repeats some of those wrong values.

My overall assessment is:

- **A/B**: strong and aligned
- **C**: mostly aligned
- **D/E/F/G**: partial and not yet fully validated

## Phase-by-phase scorecard

| Phase | Plan expectation | Current status | Review |
| --- | --- | --- | --- |
| A | Freeze case definition, assumptions, gap register | Delivered | Good alignment |
| B | Canonical data package, scaling hook, site consistency metadata, regression coverage | Delivered | Good alignment |
| C | Bounded-opt physical lane with hard storage floor, no-solve first, solve, physical summary, storage-floor regression | Partially delivered | Real solve exists and storage floor works, but no no-solve evidence or Phase C regression test was found |
| D | Reuse Case 2 settlement engine, tariff-branch-aware benchmark logic, strike handling, buyer settlement, benchmark, risk, tests | Partially delivered | TOU artifacts exist, but settlement math is simplified and 22kV branch is not truly delivered |
| E | Controller-vs-optimizer realism screen on relevant lane outputs, artifact, regression coverage | Partially delivered | Artifact exists, but controller model is flawed and comparison is not same-candidate |
| F | PySAM results, REopt-vs-PySAM comparison, developer screening, DSCR/NPV/IRR/payback, regression coverage | Partially delivered | PySAM screening exists, but comparison artifact, payback, and tests are missing; some outputs are wired incorrectly |
| G | Combined decision artifact, explicit recommendation, final report, final summary, handoff notes | Partially delivered | Combined artifact and final HTML exist, but final-summary artifact is missing and combined wiring bugs contaminate the output |

## Goods

### 1. The plan intent is encoded clearly in Phase A/B

The repo does a good job turning the markdown plan into explicit machine-readable design surfaces.

- `src/python/reopt_pysam_vn/integration/dppa_case_3.py:57-166` freezes the Phase A definition, including:
  - `synthetic_financial_dppa`
  - site-consistent `saigon18` load + market basis
  - mandatory storage floor
  - two tariff branches
  - 5% strike anchor plus declared sweep points
- `src/python/reopt_pysam_vn/integration/dppa_case_3.py:207-289` implements the canonical input package and the `scale_to_annual_kwh` hook.
- `src/python/reopt_pysam_vn/integration/dppa_case_3.py:292-546` implements the assumptions register, gap register, settlement design, schema, and edge-case matrix.

This is the cleanest part of the implementation and closely matches the original markdown plan.

### 2. Site consistency is genuinely preserved in the declared data basis

The plan strongly emphasized eliminating the Case 2 cross-site mismatch. That is implemented well.

- `src/python/reopt_pysam_vn/integration/dppa_case_3.py:159-165` and `:223-229` set:
  - `load_source_case = saigon18`
  - `market_source_case = saigon18`
  - `tariff_source_case = saigon18`
  - `same_site_basis = true`
  - `same_project_workstream = true`
- `tests/python/integration/test_dppa_case_3_phase_ab.py:67-77` locks this in with regression tests.

This is one of the most important success criteria from the plan, and it is met.

### 3. The bounded-opt physical lane really does enforce nonzero storage

The plan wanted a hard break from the PV-only outcomes in Case 1 and Case 2. The implementation achieves that.

- `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py:66-71` and `:125-129` set positive battery lower bounds.
- `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py:187-192` and `:265-268` do the same for the 22kV branch.
- The solved TOU physical artifact confirms:
  - `PV = 4800 kW`
  - `BESS = 1500 kW / 3300 kWh`
  - `storage_floor_respected = true`
  - `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_phase-cd-combined.json:8-23`

This is a real improvement over the earlier cases.

### 4. Buyer, developer, and risk views are at least separated structurally

The plan asked not to blend everything into one headline number.

- `src/python/reopt_pysam_vn/integration/dppa_case_3.py:465-488` explicitly separates buyer, developer, risk, and tariff-delta views.
- Produced artifacts also follow this separation pattern:
  - buyer surfaces: `...tou_settlement.json`, `...tou_benchmark.json`, `...tou_risk.json`
  - developer surfaces: `...developer-screening.json`, `...22kv_developer-screening.json`
  - combined view: `...combined-decision.json`

Even though some of those later artifacts have issues, the structural separation is the right direction.

### 5. The final recommendation class is directionally aligned with the plan

The final state is `reject_current_case`, which is an allowed decision class in the plan's decision rules.

- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_combined-decision.json:4-12`

That said, the confidence level behind the current reject conclusion is weaker than the final report suggests because of the defects listed below.

## Bads / deviations from the original plan

### 1. Phase D does not actually reuse the hourly Case 2-style settlement engine

The plan called for reusing the Case 2 settlement architecture and consuming solved hourly outputs.

Instead, `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_cd.py:89-128` does this:

- uses `PV.year_one_energy_produced_kwh`
- uses annual totals rather than hourly matched volumes
- uses average market price rather than hourly market prices
- uses average TOU rather than branch-faithful hourly tariff treatment

That is materially simpler than the plan and weaker than the Case 2 implementation style it was supposed to preserve.

### 2. The 22kV branch is not truly implemented as a two-part tariff branch

The markdown plan promised a primary realism branch for `22kV` with demand/capacity charge treatment or explicit post-processing reconciliation.

What exists today is weaker:

- `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py:194-210` builds a synthetic hourly energy-only TOU schedule for the 22kV branch.
- `src/python/reopt_pysam_vn/integration/dppa_case_3.py:249-253` explicitly says demand charges are deferred.
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_cd.py:154-166` ignores the branch and always benchmarks using TOU averages.
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_cd.py:89-128` also ignores `tariff_branch` in the actual math.

So the code has two branch labels, but not two fully implemented, auditable tariff pathways.

### 3. Side-by-side two-branch delta reporting was promised, but not actually delivered

The plan required explicit side-by-side reporting for `22kV two-part + legacy TOU`.

What exists:

- the Phase C/D analyzer has a possible `delta` block if both branches are passed in (`scripts/python/integration/analyze_saigon18_dppa_case_3_phase_cd.py:245-254`)

What was actually produced:

- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_phase-cd-combined.json` contains only `tou`, no `22kv`, no `delta`

This is a direct miss against one of the plan's user-confirmed requirements.

### 4. The strike sensitivity sweep exists only as metadata and future work

The plan explicitly required a sweep around the 5% base anchor.

What exists:

- sweep points appear in metadata in `src/python/reopt_pysam_vn/integration/dppa_case_3.py:104` and `:268`
- the combined decision mentions `strike_sweep` as future work in `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_g.py:209-214`
- the final report recommends running the sweep later in `reports/2026-04-21-dppa-case-3-final.html:723-725`

What is missing:

- no sweep artifact
- no sweep script
- no tested sweep outputs for 0%, 5%, 10%, 15%, 20%

This is a core commercial deliverable that remains unimplemented.

### 5. Phase F is missing planned outputs

The plan asked for:

- PySAM results
- REopt-vs-PySAM comparison
- developer screening
- DSCR, NPV, IRR, and payback

What exists:

- developer screening with embedded PySAM outputs in `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_developer-screening.json`

What is missing:

- no dedicated Case 3 `reopt-pysam-comparison.json`
- no payback metric in the screening artifact
- no Phase F regression tests

### 6. Phase G is missing some promised closeout surfaces

The plan called for:

- combined decision artifact
- final Case 3 report
- final-summary artifact
- implementation notes for next-step handoff

What exists:

- combined decision artifact
- final HTML report

What is missing:

- no Case 3 `final-summary.json`
- no explicit handoff notes artifact

## Likely errors / weak spots

### 1. Phase E controller model is numerically broken

This is the most serious analytical defect.

Evidence:

- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_e.py:66-72` generates the fallback PV profile using the absolute hour index `h` instead of hour-of-day.
- That makes almost the entire year zero-PV after the first day.
- The resulting artifact shows only `7680 kWh/year` PV generation for a `3200 kW` system:
  - `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_phase-e-controller-gap.json:27-35`

That result is not physically credible and makes the controller comparison unreliable.

### 2. Phase E compares different physical candidates, not the same candidate under two dispatch modes

The plan wanted the controller-style sensitivity on the relevant bounded-opt lane.

What the code does:

- controller path uses base sizing `3200 / 1000 / 2200` (`scripts/python/integration/analyze_saigon18_dppa_case_3_phase_e.py:184-189`)
- optimizer path uses solved sizing `4800 / 1500 / 3300` (`...phase_e.py:194-215`)

So the gap is not only dispatch-vs-dispatch. It is also base-size-vs-solved-size.

### 3. Phase E hardcodes settlement inputs instead of deriving them from the branch case

Evidence:

- hardcoded strike `1809.613356` at `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_e.py:179`
- flat `tou = [1811.0] * 8760` at `:181-182`

That means the controller-gap artifact is not branch-faithful and does not truly preserve the frozen Case 3 tariff/strike surfaces.

### 4. Phase D branch-aware logic is mostly nominal, not real

`tariff_branch` is passed through as a label, but the math ignores it.

Examples:

- `compute_buyer_settlement` uses TOU average regardless of branch (`scripts/python/integration/analyze_saigon18_dppa_case_3_phase_cd.py:121-128`)
- `compute_evn_benchmark` always uses TOU average (`:154-166`)
- `compute_contract_risk` uses annual totals and average CFMP (`:169-196`)

This makes the 22kV promise largely superficial in the current implementation.

### 5. Phase F extracts the wrong PySAM keys into the decision block

Evidence:

- the code reads `project_return_aftertax_npv` and `project_return_aftertax_irr` from `pysam_result["outputs"]` at `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py:173-175`
- but the produced payload stores:
  - `project_return_aftertax_npv_usd`
  - `project_return_aftertax_irr_fraction`
  - `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_developer-screening.json:63-71`

Result:

- the screening artifact's `decision.npv_usd` is `null` even though the underlying PySAM NPV is clearly negative:
  - `...developer-screening.json:240-246`

### 6. Phase F uses a different generation basis than Phase D

This creates cross-phase inconsistency.

- Phase D settlement uses `annual_generation_kwh = 6843120` from `PV.year_one_energy_produced_kwh`:
  - `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_phase-cd-combined.json:24-45`
- Phase F developer screening uses `annual_gen_kwh = 5224499.359`:
  - `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_developer-screening.json:4-24`

The code path explains why:

- Phase F builds generation from `PV.electric_to_load_series_kw + electric_to_grid_series_kw` rather than the same buyer-side matched or production basis (`scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py:77-97`)

This mismatch weakens the buyer-developer comparison.

### 7. Phase G combined artifact is wired incorrectly

Evidence:

- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_g.py:61-67` expects nested `tou` keys inside the flat TOU benchmark artifact
- `:183-191` expects nested `tou` keys inside the flat TOU risk artifact
- `TOU_PHYSICAL_PATH` is defined but never loaded (`:25-41`, `:53-60`)

Resulting artifact defects:

- `buyer.evn_blended_vnd_per_kwh = 0`
- all `contract_risk` quantities are `0`
- `physical.capital_cost_usd = 0`
- `physical.lcc_usd = 0`
- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_combined-decision.json:13-24, 42-49, 77-83`

These are not just cosmetic. They contaminate the final decision package.

### 8. The final HTML report repeats wrong numbers from the buggy combined artifact

Examples:

- EVN blended cost shown as `0.00 VND/kWh`:
  - `reports/2026-04-21-dppa-case-3-final.html:671`
  - `reports/2026-04-21-dppa-case-3-final.html:768`
- Phase E says the remaining annual load gap is `0M kWh`:
  - `reports/2026-04-21-dppa-case-3-final.html:672`

The report therefore looks polished but contains materially wrong values.

### 9. Bounds reported in the final HTML do not match the actual implemented bounds

The final report states:

- PV `2400-7200`
- BESS power `750-2250`
- BESS energy `1650-4950`

But the actual implementation uses:

- PV `2400-4800`
- BESS power `750-1500`
- BESS energy `1650-3300`

Evidence:

- actual implementation: `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py:66-71` and `:187-192`
- wrong report statement: `reports/2026-04-21-dppa-case-3-final.html:598`

### 10. Case-class logic drifts outside the plan's allowed classes

The plan's recommendation classes are constrained.

But `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_g.py:116-121` introduces `advance_22kv`, which is not one of the planned classes.

This is minor compared with the arithmetic defects, but it is still a plan deviation.

### 11. Strike escalation assumptions are internally inconsistent

Evidence:

- `src/python/reopt_pysam_vn/integration/dppa_case_3.py:6` sets `DEFAULT_STRIKE_ESCALATION_FRACTION = 0.05`
- the Phase A definition records that value at `:100-103`
- but the scenario financials use `elec_cost_escalation_rate_fraction = 0.04` in `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py:151-159` and `:290-297`
- Phase F also uses `ppa_escalation_rate_fraction = 0.04` at `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py:151`

This inconsistency is small but should be cleaned up before sensitivity work.

## Missing deliverables / validation gaps

### 1. Tests stop at Phase AB

The plan explicitly called for:

- `tests/python/integration/test_dppa_case_3_phase_c.py`
- `...phase_d.py`
- `...phase_e.py`
- `...phase_f.py`

I found only:

- `tests/python/integration/test_dppa_case_3_phase_ab.py`

There is no regression lock on the most error-prone phases.

### 2. No storage-floor regression test was found for Phase C

The physical solve does show storage was nonzero, but there is no separate Phase C test file proving that a future refactor would fail if storage dropped to zero.

### 3. No evidence of the planned no-solve validation step

The plan asked to run no-solve validation first. I found solve scripts, but no dedicated no-solve execution surface or recorded artifact proving that step happened.

### 4. No Case 3 REopt-vs-PySAM comparison artifact

This was a named planned output and remains absent.

### 5. No final-summary artifact

The plan asked for `..._final-summary.json`. I did not find a Case 3 version of that artifact.

### 6. 22kV buyer-side outputs are effectively missing

There is a `22kv` developer screening artifact, but no complete 22kV buyer settlement, benchmark, risk, or side-by-side delta package was produced.

## Insights

### 1. The repo has already built the right scaffolding, but not yet the right decision-grade analytics

The current state is not "nothing works". In fact, the Case 3 definition work is strong, the data basis is cleaner than Case 2, and the physical lane finally forces storage.

The gap is that the later phases simplify too aggressively and then overstate confidence in the final report.

### 2. The current reject signal is probably directionally true, but it is not yet cleanly proven

Given:

- buyer payment above EVN in TOU
- PySAM DSCR deeply negative
- tiny renewable share relative to annual load

the current reject conclusion is plausible.

But because the downstream surfaces have multiple wiring and modeling issues, the current implementation should be treated as **directional evidence**, not a final bankable closeout.

### 3. The biggest implementation gap is not Phase C - it is the untrustworthy chain from Phase D through Phase G

The physical solve is the healthiest part of the later workflow.

The weaker parts are:

- settlement math simplification
- branch handling
- controller proxy bug
- PySAM comparison incompleteness
- combined artifact/report wiring bugs

### 4. The final report currently overstates maturity

The HTML artifact is polished, but it contains wrong values and embeds future work as if it were completed analysis.

That matters because this repo often uses reports as the user-facing source of truth.

### 5. One recommendation in the final report conflicts with the original user decision

`reports/2026-04-21-dppa-case-3-final.html:725` recommends removing the storage floor and running a free optimization.

That conflicts with the original plan's explicit user decision to run **Lane B only** with **mandatory storage floor**.

If the case is reopened, that should happen as a consciously approved new branch, not as a silent reinterpretation of Case 3.

## Prioritized remediation order

If this workflow is reopened, I would fix it in this order:

1. **Fix Phase G wiring first**
   - load the correct flat artifacts
   - stop writing zero-valued benchmark, risk, and physical fields
   - repair the final report inputs

2. **Fix Phase E controller math**
   - correct the PV profile generation bug
   - compare controller vs optimizer on the **same solved physical candidate**
   - derive strike and tariff inputs from the branch case, not hardcoded constants

3. **Rebuild Phase D using hourly solved series**
   - preserve the Case 2 hourly settlement logic
   - calculate matched, shortfall, excess, and risk from hourly surfaces
   - make branch-specific benchmark logic real, not nominal

4. **Complete the 22kV branch properly**
   - implement the demand-charge reconciliation layer the plan called for
   - produce actual 22kV buyer settlement, benchmark, risk, and side-by-side delta artifacts

5. **Complete Phase F outputs**
   - add the missing REopt-vs-PySAM comparison artifact
   - fix the NPV/IRR key extraction bug
   - add payback if it is still a required screening metric

6. **Add the missing tests for Phases C-F**
   - especially around storage floor, settlement math, controller gap, and PySAM outputs

7. **Only after those fixes, run the planned strike sweep**
   - the sweep should be run on a trustworthy base workflow, not on the current partially broken downstream chain

## Recommended final judgment on the current implementation

Use the following judgment for the repo state as of this review:

- **What is complete:** plan translation into A/B definitions, site-consistent basis, bounded-opt physical lane with mandatory storage, first-pass TOU settlement surface, first-pass controller artifact, first-pass PySAM developer screening, first-pass combined decision and report generation
- **What is incomplete:** true two-branch tariff implementation, branch-faithful settlement math, strike sweep, REopt-vs-PySAM comparison, final-summary artifact, Phase C-F tests
- **What is wrong enough to fix before relying on the outputs:** Phase E controller numbers, Phase G aggregation, final report benchmark/risk values, NPV extraction bug, branch-aware benchmark math

The correct synthesis is:

> **Case 3 is partially implemented and directionally useful, but not yet fully faithful to the original plan or ready to be treated as a final decision-grade workflow.**
