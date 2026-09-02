# DPPA Case 1-3 Retrospective Review

Date: 2026-04-23

## Scope

This report reviews the implementation and documentation of `DPPA Case 1`, `DPPA Case 2`, and `DPPA Case 3` across:

- the canonical plans in `plans/active/`
- the main implementation modules under `src/python/reopt_pysam_vn/integration/`
- the orchestration scripts under `scripts/python/integration/`
- available regression tests under `tests/python/integration/`
- canonical machine-readable artifacts under `artifacts/reports/` and `artifacts/results/`
- the generated HTML and markdown reports under `reports/`
- the session worklog in `activeContext.md`
- the commercial research basis in `research/2026-04-07-vietnam-dppa-buyer-guide.md`

The main questions for this review are:

1. Did each case implement what its plan said it would implement?
2. What shortcomings remain in the implementation and the documentation?
3. What should be improved next?
4. What did the project learn as it progressed from Case 1 to Case 3?

## Sources reviewed

Key planning and review sources:

- `plans/active/dppa_case_1_plan.md`
- `plans/active/dppa_case_2_plan.md`
- `plans/active/dppa_case_3_plan.md`
- `reports/2026-04-14-dppa-case-2-readiness-review.md`
- `reports/2026-04-21-dppa-case-3-plan-implementation-review.md`
- `research/2026-04-07-vietnam-dppa-buyer-guide.md`
- `activeContext.md`

Key implementation surfaces:

- `src/python/reopt_pysam_vn/integration/dppa_case_1.py`
- `src/python/reopt_pysam_vn/integration/dppa_case_2.py`
- `src/python/reopt_pysam_vn/integration/dppa_case_3.py`
- `src/python/reopt_pysam_vn/integration/bridge.py`
- `scripts/python/integration/build_ninhsim_reopt_input.py`
- `scripts/python/integration/run_ninhsim_dppa_case_1.py`
- `scripts/python/integration/analyze_ninhsim_dppa_case_1.py`

Key validation and artifact surfaces:

- `tests/python/integration/test_dppa_case_1.py`
- `tests/python/integration/test_dppa_case_2_phase_ab.py`
- `tests/python/integration/test_dppa_case_2_phase_cd.py`
- `tests/python/integration/test_dppa_case_2_phase_e.py`
- `tests/python/integration/test_dppa_case_2_phase_f.py`
- `tests/python/integration/test_dppa_case_2_phase_g.py`
- `tests/python/integration/test_dppa_case_3_phase_ab.py`
- `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_reopt-summary.json`
- `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_pysam-results.json`
- `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_combined-decision.json`
- `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_combined-decision.json`
- `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_final-summary.json`
- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_phase-cd-combined.json`
- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_phase-e-controller-gap.json`
- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_developer-screening.json`
- `artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_combined-decision.json`

## Executive summary

The three DPPA cases show real progress, but they are not equally mature.

- `DPPA Case 1` established a usable private-wire reference workflow, but it did not actually deliver the intended `PV + 2-hour BESS + fuller PySAM` validation loop because REopt optimized storage away and the published PySAM pass was skipped.
- `DPPA Case 2` is the strongest and most reusable implementation of the three. It cleanly split away from Case 1's private-wire logic, built an explicit synthetic-DPPA buyer settlement ledger, kept buyer and developer outputs separate, and closed with a stable `reject_current_case` decision artifact. Its biggest remaining weakness is evidence quality rather than architecture quality: it still depends on transferred market data and a simplified developer-side finance screen.
- `DPPA Case 3` has the strongest realism-first intent and the best A/B scaffolding, but the weakest downstream execution. Site consistency and mandatory storage are real improvements, yet Phases D-G are only partially implemented, contain analytical and data-wiring defects, and are not sufficiently validated to support decision-grade conclusions.

The most important repo-level conclusion is:

> The project improved materially from Case 1 to Case 2 in architecture, auditability, and conceptual correctness, but Case 3 shows that strong planning and polished reports are not enough unless downstream analytics, artifact contracts, and regression coverage are equally strong.

## Cross-case scorecard

| Case | Intended role | Current maturity | Strongest contribution | Biggest weakness | Recommended current role |
| --- | --- | --- | --- | --- | --- |
| Case 1 | Private-wire PV+BESS reference with REopt plus fuller PySAM validation | Partial | Established the private-wire reference lane and the REopt -> PySAM workflow shape | Storage was not enforced, so the delivered case became PV-only and PySAM was skipped | Keep as a historical private-wire reference, not as the canonical PV+BESS decision workflow |
| Case 2 | Canonical synthetic-DPPA buyer-cost workflow | Strongest of the three | Introduced the explicit hourly buyer settlement architecture and auditable phase artifacts | Still relies on transferred market data and a simplified developer screen | Keep as the repo's current canonical synthetic-DPPA baseline |
| Case 3 | Realism-first site-consistent bridge using Saigon18 | Mixed | Added site consistency, storage floor enforcement, and a realism-first framing | Downstream D-G analysis is incomplete or buggy, so final outputs are not decision-grade | Treat as a partial bridge workflow that must be repaired before reuse |

## Case 1 review

### What Case 1 was supposed to do

`DPPA Case 1` was planned as a new Ninhsim workflow that would:

- reuse the Ninhsim `8760` load profile
- use REopt for initial `PV + BESS` sizing
- fix battery duration at exactly `2 hours`
- pursue a near-zero-export / full-site-use design intent
- run a fuller downstream PySAM PV-plus-battery configuration
- compare REopt and PySAM and iterate if needed

This intent is explicit in `plans/active/dppa_case_1_plan.md`.

### What was actually delivered

Case 1 did deliver a coherent end-to-end workflow surface:

- scenario builder in `scripts/python/integration/build_ninhsim_reopt_input.py`
- REopt summary / comparison / combined decision helpers in `src/python/reopt_pysam_vn/integration/dppa_case_1.py`
- orchestration in `scripts/python/integration/run_ninhsim_dppa_case_1.py`
- REopt analysis in `scripts/python/integration/analyze_ninhsim_dppa_case_1.py`
- PySAM bridge in `src/python/reopt_pysam_vn/integration/bridge.py`

However, the published result did not answer the intended PV+BESS question:

- `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_reopt-summary.json` shows `38.108 MW` PV and `0 MW / 0 MWh` BESS.
- `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_pysam-results.json` shows the PySAM stage was `skipped` because REopt selected zero battery.
- `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_combined-decision.json` concludes `needs_reprice_or_resize`.

So the workflow exists, but the delivered canonical artifact is a PV-only private-wire screen, not a validated solar-plus-storage DPPA case.

### Main strengths

1. **Clear private-wire reference logic**
   - Case 1 is internally coherent as a private-wire / behind-the-meter reference workflow.
   - The strike logic in `src/python/reopt_pysam_vn/integration/dppa_case_1.py` is grounded in the Decree 57 ceiling rules and explicitly checks storage qualification thresholds.

2. **Good workflow continuity**
   - The scripts and helper functions give the repo a clean build -> solve -> analyze -> compare -> decide pattern.
   - Even the zero-battery outcome is handled gracefully through a placeholder PySAM artifact rather than a crash.

3. **Regression coverage exists for the core contract**
   - `tests/python/integration/test_dppa_case_1.py` locks scenario construction, strike logic, REopt summary behavior, comparison logic, and the skipped-PySAM case.
   - This is better than having an untested script-only workflow.

4. **Export behavior is explicit**
   - The scenario builder disables wholesale/net-meter/export pathways and the artifact reports export and curtailment separately.
   - That makes the no-export design intent reviewable.

### Main shortcomings

1. **The case does not enforce nonzero storage**
   - `scripts/python/integration/build_ninhsim_reopt_input.py` locks battery duration but leaves storage optional.
   - This is the direct reason the solved case became PV-only.
   - It is the most important implementation shortcoming because it prevents the workflow from answering the stated BESS question.

2. **The fuller PySAM validation was not actually exercised on the canonical case**
   - The repo has the bridge and runtime surface, but the published case never used them on a nonzero battery candidate.
   - That means the REopt-vs-PySAM comparison artifact is not a true second-engine validation for the delivered case.

3. **The stated optimization objective drifted from the delivered metadata**
   - The plan records the user answer as `minimum project capex`.
   - The scenario metadata and tests encode `minimum_lifecycle_cost_with_no_export_intent`.
   - That mismatch weakens trust in the case definition because the artifact story is not fully truthful to the plan.

4. **The no-excess idea was reduced to no export, not full utilization**
   - The delivered artifact shows zero export, but still material curtailment (`~2.055 GWh`).
   - That means the workflow controlled export but did not fully resolve the broader "full site use" design goal.

5. **Dispatch assumptions are not clearly aligned with the plan narrative**
   - The bridge hardcodes a PySAM dispatch mode in `src/python/reopt_pysam_vn/integration/bridge.py` without making that assumption a first-class reviewed artifact.
   - That is acceptable for a prototype, but not ideal for a case intended to teach a reusable DPPA design pattern.

### Documentation review

Case 1 documentation is weaker than its code structure.

- The plan exists and is detailed in `plans/active/dppa_case_1_plan.md`.
- The implementation history is well captured in `activeContext.md`.
- But a repo-level search found no `README.md` or `docs/*.md` coverage for `DPPA Case 1`.

That means the most important truth about Case 1 currently lives in the session log, not in stable project documentation:

- it is a private-wire reference case
- it did not produce a real battery buildout
- the PySAM stage was skipped for the canonical run

This is a documentation gap because a future contributor could easily assume the HTML report and artifact set imply a fully validated REopt-plus-PySAM PV+BESS workflow.

### Best improvement opportunities

1. Enforce nonzero storage if Case 1 is meant to remain a PV+BESS case.
2. Align the plan, scenario metadata, and tests on the actual optimization objective.
3. Mark placeholder PySAM outputs more explicitly as `not validated`, not merely `skipped`.
4. Add a bounded redesign loop so zero-battery REopt outcomes automatically trigger a resize/tightened-storage rerun.
5. Document Case 1 in `README.md` or `docs/` as a private-wire reference case, not as the main synthetic-DPPA path.

### Lessons learned from Case 1

- Locking battery duration is not enough if storage itself is optional.
- A placeholder artifact is useful for workflow continuity, but it is not equivalent to second-engine validation.
- Commercial structure must be explicit early; otherwise a case can appear more general than it really is.
- Session notes should not be the only place where major implementation caveats are documented.

## Case 2 review

### What Case 2 was supposed to do

Case 2 was explicitly created to fix the conceptual gap in Case 1.

Its plan and readiness review made a clean split:

- `Case 1` remains the private-wire reference case.
- `Case 2` becomes the repo's first canonical synthetic / financial DPPA workflow with:
  - explicit buyer-side settlement
  - explicit settlement quantity rule
  - explicit excess-generation treatment
  - separate buyer and developer outputs

This intent is clear in `plans/active/dppa_case_2_plan.md` and `reports/2026-04-14-dppa-case-2-readiness-review.md`.

### What was actually delivered

Case 2 is the most complete of the three implementations.

It delivered an A-G phase progression with:

- definition and assumptions artifacts
- settlement design and schema artifacts
- physical REopt scenario and summary
- hourly buyer settlement and benchmark logic
- strike and contract-risk sensitivities
- market-reference replacement
- PySAM developer screening
- combined decision artifact
- final summary artifact

The core implementation is in `src/python/reopt_pysam_vn/integration/dppa_case_2.py` and the finance bridge is in `src/python/reopt_pysam_vn/integration/bridge.py`.

The final machine-readable closeout is explicit:

- `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_combined-decision.json`
- `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_final-summary.json`

The final decision is stable and honest: `reject_current_case`.

### Main strengths

1. **Case splitting was done correctly**
   - The project did not quietly mutate Case 1 into a synthetic DPPA workflow.
   - It created a separate Case 2 architecture and documented the reason clearly.

2. **The settlement architecture is strong and reusable**
   - Case 2 introduced the repo's clearest hourly buyer-payment stack.
   - The buyer-side settlement engine explicitly handles matched quantity, shortfall, excess, EVN-linked payment, DPPA adder, KPP, CfD, and blended buyer cost.
   - This is the strongest reusable analytical surface produced across the three cases.

3. **Buyer and developer outputs remain separated**
   - Case 2 consistently resists collapsing the commercial story into one headline strike number.
   - Buyer settlement, buyer benchmark, contract risk, market basis, PySAM developer screen, and final decision each have their own artifacts.

4. **The phase structure is auditable**
   - Case 2 is well documented in `activeContext.md`.
   - The phase-by-phase implementation notes, validations, artifact paths, and outcomes are unusually clear for an internal modeling workflow.

5. **Regression coverage is materially better than Case 1 and Case 3**
   - Phases AB, CD, E, F, and G all have test files.
   - The tests lock the commercial mechanics rather than just smoke-test script existence.

### Main shortcomings

1. **Market evidence is still the biggest weak point**
   - The final decision depends on a transferred `saigon18` CFMP series rather than a true Ninhsim hourly market series.
   - The architecture is strong, but the evidence quality is still provisional.

2. **The developer-side PySAM screen is still only an approximation of synthetic DPPA economics**
   - The buyer side models a synthetic settlement ledger explicitly.
   - The developer side still maps the case into a simpler strike-based `Single Owner` finance screen.
   - That is useful for screening, but it is not yet a full synthetic-DPPA bilateral cashflow model.

3. **The REopt objective is still not fully truthful to the plan language**
   - The assumptions register says buyer-cost-plus-matched-delivery.
   - The scenario metadata still effectively position REopt as a lifecycle-cost physical optimization with post-processed commercial screening.
   - The repo handled this more honestly than Case 1, but it did not completely solve the mismatch.

4. **Storage was intentionally left optional, so the case still did not answer a mandatory-BESS question**
   - This matches the user decision in the plan.
   - But it also means Case 2 still lands at PV-only in practice and therefore should not be mistaken for the repo's final solar-plus-storage synthetic-DPPA answer.

5. **Schema and runtime drift appeared in Phase F**
   - The A/B schema allows only generic market reference types.
   - Later artifacts introduce `repo_actual_cfmp_transfer` style values that are not cleanly reflected in the original schema contract.
   - That is a maintainability issue rather than a conceptual one, but it matters for long-term trust.

### Documentation review

Case 2 documentation is much better than Case 1 documentation, but it still has a few gaps.

Strengths:

- The readiness review is excellent and should be kept as a model for future case transitions.
- `activeContext.md` provides a clear A-G narrative.
- The final summary artifact exists, which Case 3 still lacks.

Documentation gaps / inconsistencies:

1. No top-level `README.md` or `docs/` page explains the role and status of Case 2.
2. The final summary says it rolls up the whole case history, but it only records phases C-G and omits the important A/B design freeze.
3. The final summary points its Phase D history to a later actual-market artifact, which blurs the real chronology.
4. There are duplicate or drifting report surfaces in `reports/`, including both `2026-04-15-dppa-case-2-final.html` and `2026-04-16-dppa-case-2-final.html`, plus the Phase F filename drift to `2026-04-15-dppa-case-2-phase-f-fmp-overlay.html`.

These are not fatal, but they make canonical-path discovery harder than it should be.

### Best improvement opportunities

1. Source a true Ninhsim hourly CFMP/FMP series and retire the transferred-market dependency.
2. Unify the settlement schema with the actual runtime market-reference values used in later phases.
3. Make the REopt objective language fully truthful across plan, metadata, reports, and code comments.
4. Upgrade the developer-side screen so it more faithfully represents synthetic-DPPA cashflows instead of a plain strike-based PPA approximation.
5. Add artifact-level regression tests on the published canonical JSONs and report metadata.
6. Canonicalize the HTML reports and explicitly mark superseded outputs.

### Lessons learned from Case 2

- Splitting Case 1 and Case 2 by commercial structure was the right architectural move.
- Freezing the settlement schema before widening the analysis was a major improvement over the more implicit Case 1 approach.
- Buyer-side transparency and auditability are now a real strength of the repo.
- Data provenance and canonical-path discipline still matter just as much as good arithmetic.

## Case 3 review

### What Case 3 was supposed to do

Case 3 was designed as the realism-first bridge case.

Its plan promised:

- a site-consistent `saigon18` load + market basis
- one bounded optimization lane with a mandatory storage floor
- two tariff branches (`22kV two-part` and `legacy TOU`) with side-by-side delta reporting
- a controller-vs-optimizer realism screen
- a downstream PySAM validation layer
- a final combined decision artifact and report

This is documented in `plans/active/dppa_case_3_plan.md`.

### What was actually delivered

Case 3 did deliver the strongest definition work of all three cases:

- a strong Phase A definition
- a site-consistent input package with scaling hook
- a gap register
- a settlement design and schema
- A/B regression coverage

It also delivered a real bounded-opt physical lane with nonzero storage in the canonical TOU result.

However, the downstream phases are not fully trustworthy.

The repo's own review in `reports/2026-04-21-dppa-case-3-plan-implementation-review.md` already says the same thing: Case 3 is directionally useful, but not decision-grade.

### Main strengths

1. **The best A/B plan translation in the repo**
   - Case 3 converts the plan into explicit machine-readable design surfaces better than Case 1 and at least as well as Case 2.
   - The `site_consistency_block`, strike metadata, scaling hook, tariff-branch metadata, and storage-floor assumptions are all first-class outputs.

2. **Site consistency is genuinely fixed**
   - This is one of Case 3's biggest conceptual wins over Case 2.
   - Load, market, and tariff basis are all declared as `saigon18`.
   - That closes one of the most important realism gaps left open in Case 2.

3. **Mandatory storage finally became real in the physical lane**
   - The bounded-opt scenario uses positive lower bounds.
   - The published TOU physical artifact shows nonzero BESS and a respected storage floor.

4. **The repo produced an honest internal critique of Case 3**
   - `reports/2026-04-21-dppa-case-3-plan-implementation-review.md` is one of the most valuable documents in the repo because it clearly distinguishes what landed from what only partially landed.

### Main shortcomings

1. **Phase D does not preserve the Case 2 hourly settlement architecture**
   - Instead of reusing the strong Case 2 settlement logic on solved hourly series, the implementation simplifies to annual totals and average prices.
   - This is the single biggest design regression from Case 2 to Case 3.

2. **The 22kV two-part branch is only partially real**
   - The plan promised a real two-part branch or an explicit demand-charge reconciliation layer.
   - The delivered code mostly produces an alternate energy-rate label rather than a complete branch-faithful tariff model.
   - The published Phase C/D artifact contains only the TOU branch and no side-by-side delta block.

3. **The strike sweep was promised but not executed**
   - Sweep metadata exists.
   - A sweep artifact, sweep script, and tested sweep outputs do not.
   - This matters because the strike sweep was one of the user-confirmed commercial requirements in the plan.

4. **Phase E controller math is analytically broken**
   - The fallback PV profile logic generates non-credible annual PV output.
   - The controller and optimizer are not compared on the same physical candidate.
   - Settlement inputs are hardcoded rather than branch-derived.
   - This makes the controller-gap artifact unsuitable for decision use.

5. **Phase F is incomplete and partly mis-wired**
   - PySAM developer screening exists.
   - The planned REopt-vs-PySAM comparison artifact is missing.
   - Key output extraction uses the wrong field names, which makes decision-level NPV values null even when the underlying PySAM outputs contain the value.

6. **Phase G combined aggregation is materially wrong**
   - The script expects nested structures from flat artifacts.
   - As a result, the combined decision artifact writes zeroes into key benchmark, risk, and physical fields.
   - The final HTML report then repeats some of those incorrect values.

7. **Validation coverage collapses after Phase AB**
   - Case 3 only has an AB test file.
   - The most error-prone phases (C-F) do not have the regression coverage the plan explicitly called for.

### Documentation review

Case 3 documentation is internally mixed.

Strong points:

- The plan is detailed and thoughtful.
- The A/B artifacts are self-describing.
- The review memo is honest and technically useful.

Weak points:

1. The final HTML report is more polished than trustworthy.
   - It contains materially wrong values copied from the buggy combined artifact.
   - That is dangerous because reports are often treated as the human-facing source of truth.

2. The plan is stronger than the delivered execution.
   - A reader of the plan alone would expect a much more complete 22kV branch, a real strike sweep, and a tested controller-gap workflow than the repo actually provides.

3. Documentation and output surfaces disagree on maturity.
   - The review memo and `activeContext.md` correctly say the workflow is not decision-grade.
   - The final HTML report reads more like a finished closeout.

4. Important closeout surfaces are missing.
   - There is no Case 3 `final-summary.json`.
   - There are no dedicated Phase C-F regression test files.

### Best improvement opportunities

1. Fix Phase G aggregation first so the final combined decision surface stops emitting wrong zeros.
2. Rebuild Phase D on hourly solved series and reuse the Case 2 settlement architecture faithfully.
3. Fix Phase E so controller and optimizer are compared on the same solved candidate with physically credible controller math.
4. Implement the 22kV demand-charge reconciliation layer and publish true side-by-side delta artifacts.
5. Complete Phase F outputs, including the missing REopt-vs-PySAM comparison artifact and corrected key extraction.
6. Add the missing Phase C-F regression test suite.
7. Only after those repairs, run the planned strike sweep and publish a new final summary / closeout package.

### Lessons learned from Case 3

- Strong plan translation in A/B does not protect the repo from downstream analytical defects.
- Branch labels are not enough; branch-specific math and branch-specific artifacts must exist.
- Internal review artifacts are valuable and should gate publication of stakeholder-facing final reports.
- Schema and artifact-contract drift can quietly undermine an otherwise promising workflow.

## Cross-case themes

### 1. Commercial structure clarity improved over time

The repo became much clearer about commercial structure as it moved from Case 1 to Case 3.

- Case 1 was a private-wire reference workflow.
- Case 2 correctly established the synthetic-DPPA buyer-settlement architecture.
- Case 3 tried to preserve that architecture while improving realism.

This progression is real progress.

### 2. Hard constraints matter more than narrative intent

The most repeated pattern across the three cases is that narrative intent is not enough.

- Case 1 wanted a 2-hour BESS case but did not enforce nonzero storage.
- Case 2 consciously left storage optional, so it still solved to PV-only.
- Case 3 finally enforced storage floor bounds and therefore actually prevented collapse back to PV-only.

The repo should treat this as a durable lesson: if a case is supposed to answer a physical question, encode it as a hard rule, not a descriptive intention.

### 3. Case 2 is the strongest reusable analytical core

Even though Case 3 is newer and more realistic in intent, Case 2 is still the better reusable analytical foundation right now because:

- the settlement engine is clearer
- the tests are stronger
- the artifacts are more coherent
- the final decision package is more stable

The practical implication is that Case 3 should probably be repaired by reusing Case 2 more faithfully, not by inventing more bespoke downstream logic.

### 4. Documentation quality does not yet match implementation importance

Across all three cases, top-level project documentation is lagging behind the case work.

- No `README.md` coverage was found for Case 1, 2, or 3.
- No `docs/*.md` overview was found for the DPPA case family.
- Important truths are currently preserved in `activeContext.md` and review reports rather than in stable repo documentation.

This makes onboarding and future reuse harder than necessary.

### 5. Report polish started to outpace validation discipline

The HTML reports are visually strong and easy to scan, but the repo needs to be careful not to let report polish outrun analytical truth.

- Case 1's HTML can look more complete than the underlying zero-battery result really is.
- Case 2's reports are generally honest, but canonical-path drift is starting to appear.
- Case 3's final HTML contains wrong values because the combined artifact feeding it is wrong.

The repo now needs stronger report-input validation and canonical-surface discipline.

## Prioritized repo-level improvement program

### Priority 1 - Stabilize the canonical DPPA architecture

1. Make the Case 2 hourly settlement engine the canonical shared engine for synthetic-DPPA buyer analysis.
2. Refactor Case 3 to consume that engine directly instead of simplifying to annual-average math.
3. Add artifact schema validation so flat-vs-nested mismatches are caught before reports are generated.

### Priority 2 - Fix Case 3 before expanding it

1. Repair Phase G aggregation.
2. Repair Phase E controller analysis.
3. Complete the 22kV branch properly.
4. Add the missing Phase C-F tests.
5. Only then run the strike sweep.

### Priority 3 - Improve evidence quality

1. Obtain true site-specific hourly market series for Ninhsim and other active cases.
2. Add provenance and quality metadata consistently to every market-based artifact.
3. Distinguish clearly between `directional`, `screening`, and `decision-grade` outputs.

### Priority 4 - Clean up documentation and canonical paths

1. Add a DPPA cases overview section to `README.md`.
2. Add a dedicated `docs/dppa_cases.md` or equivalent overview describing:
   - each case's purpose
   - current status
   - canonical artifacts
   - known limitations
3. Mark superseded reports explicitly and eliminate duplicate closeout surfaces where possible.

### Priority 5 - Make implementation truth more explicit

1. Align scenario metadata with real optimization behavior.
2. Surface warning states directly in the machine-readable summary artifacts, not only in worklog notes.
3. Treat placeholder or skipped downstream runs as a separate status class from successful validation.

## Final recommendations by case

### Case 1

- Keep it as a private-wire reference case.
- Do not treat it as the repo's answer to the PV+BESS validation problem unless storage enforcement is added and PySAM is rerun on a nonzero-battery candidate.

### Case 2

- Keep it as the repo's current canonical synthetic-DPPA workflow.
- Use it as the base architecture for future buyer-side synthetic-DPPA work.
- Improve data quality and developer-side fidelity before using it for negotiation-grade conclusions.

### Case 3

- Treat the current implementation as a partial realism-first bridge, not a final closeout.
- Reopen it only after the downstream D-G defects are fixed and the missing test coverage is added.

## Final lessons learned

1. Freeze commercial structure early and keep case families cleanly separated.
2. Convert key physical requirements into hard constraints, not just metadata.
3. Treat buyer settlement as a first-class layer and keep it independent from developer finance.
4. Do not let placeholder artifacts or visually polished reports stand in for true validation.
5. Make canonical data provenance, artifact contracts, and report paths part of the engineering discipline, not just documentation cleanup.
6. Use internal review reports the way Case 3 did: as honest gates that prevent the repo from overstating what is actually complete.

## Bottom line

The project has made meaningful progress.

- Case 1 established the private-wire reference lane.
- Case 2 established the strongest synthetic-DPPA analytical architecture now in the repo.
- Case 3 established the strongest realism-first framing and site-consistency discipline, but not yet the strongest execution.

If the repo wants one durable takeaway from the Case 1 -> 3 progression, it should be this:

> Build future DPPA work on the Case 2 settlement architecture, borrow Case 3's site-consistency and storage-floor discipline, and do not publish a final closeout report until the downstream analytics and artifact contracts are as robust as the planning surfaces.
