# DPPA Case 1 - Ninhsim Load REopt + Full PySAM Plan

> Status: Draft for review - 2026-04-09
> Scope: Create a new `DPPA Case 1` workflow that reuses the Ninhsim `8760` load profile, uses REopt for initial optimal sizing with a fixed `2-hour` BESS duration and no-excess solar intent, then uses a fuller PySAM solar-plus-battery configuration to evaluate plant behavior, battery behavior, and project finance with a tighter coupling between physical and financial assumptions.
> Canonical plan path: `plans/active/dppa_case_1_plan.md`

## 1. Objective

Create a new case-study workflow that does all of the following:

1. Reuses the existing Ninhsim `8760` site load profile as the customer demand basis.
2. Creates a new scenario family named `DPPA Case 1`.
3. Uses REopt as the first-pass sizing engine for `solar PV + BESS` only.
4. Fixes the REopt battery duration at `2.0 hours`, meaning `BESS kWh = 2 x BESS kW`.
5. Sizes the solar farm around a `full site use` intent so renewable generation is absorbed by the site-plus-battery system rather than deliberately oversized into merchant export.
6. Uses PySAM as a fuller downstream model for solar generation, battery operation, and finance rather than the earlier finance-only custom-generation shortcut.
7. Produces a review-ready set of machine-readable artifacts plus a markdown or HTML summary once implementation begins.

## 2. Working interpretation and why this scenario is different

This requested workflow is not the same as the latest Ninhsim `60%` solar-storage run.

That earlier run used:

- REopt to solve the physical sizing problem,
- merchant treatment for excess renewable energy, and
- PySAM `Single Owner` mainly as a finance screen fed by a blended realized revenue price.

`DPPA Case 1` should instead use the best of both tools in a more explicit split:

1. REopt should do the initial optimization and tariff-aware first sizing pass.
2. PySAM should then run a fuller plant configuration for PV plus battery, with revenue and battery behavior grounded in a more physical PySAM setup rather than only a custom hourly generation feed.

### Recommended default interpretation

- REopt remains the primary optimization engine for the first candidate size.
- REopt should be constrained to a `2-hour` battery duration rather than free-sizing energy and power independently.
- The initial REopt candidate should prefer designs that serve on-site demand without intentional excess generation.
- PySAM should become the second-stage validation and refinement engine for solar output, battery cycling assumptions, and finance.

### Why this matters

This approach avoids asking PySAM to do the global economic search that REopt already does well, while also avoiding the earlier simplification where PySAM only received a blended revenue stream and a custom generation vector.

## 3. Current repo baseline to build on

Relevant repo assets already exist:

- The canonical Ninhsim `8760` load basis already exists in the case-study workflow and extracted inputs.
- The latest Ninhsim solar-storage workflow already proved the repo can clone the Ninhsim case into a new solar-plus-storage scenario and run REopt plus PySAM end to end.
- The current PySAM runtime in the repo is `Single Owner` attached to `CustomGenerationProfileSingleOwner`, which is useful for finance screening but is still intentionally narrow.
- Vietnam-specific finance defaults, exchange-rate handling, and incentive zeroing already exist in the wrapper layer.

Important implication:

- `DPPA Case 1` should reuse the Ninhsim demand and tariff basis where possible, but it likely needs a broader PySAM module choice and a richer bridge than the current `CustomGeneration` finance-only workflow.

## 4. Recommended modeling philosophy

### Engine roles

#### REopt role

- Solve the first-pass optimal size under the Ninhsim load and Vietnam tariff assumptions.
- Enforce `solar + BESS only`.
- Enforce `2-hour` battery duration.
- Penalize or disallow excess generation to the extent REopt can support it cleanly.
- Output an initial candidate design and hourly energy-balance story.

#### PySAM role

- Rebuild the candidate project in a fuller solar-plus-battery PySAM configuration.
- Use explicit PV and battery physical assumptions instead of only a post-REopt blended generation profile.
- Evaluate annual generation, clipping, curtailment, charging/discharging behavior, degradation assumptions, replacement assumptions, and finance outputs.
- Provide the final bankability-oriented and operational review layer.

### Recommended default final decision logic

- Use REopt to pick the initial candidate design.
- Use PySAM to validate whether that design still behaves acceptably once the more detailed plant and battery model is applied.
- If the PySAM result materially diverges from the REopt expectation, iterate with a bounded design loop rather than treating the first REopt size as final truth.

## 5. Key design requirement: `full site use` / no excess

This is the most important modeling change and needs to be made explicit.

### Recommended default interpretation

Interpret `solar farm generation that will be fully used by site without excess` as:

`annual exported renewable energy should be zero or near-zero by design, with the preferred outcome being that PV generation is absorbed by site load directly or shifted through the battery to later site load.`

### Practical modeling consequence

This should not mean forcing every single hour to have zero export at all costs if that creates an unstable or infeasible model. Instead, the clean default is:

1. first target `no intentional overbuild for merchant sales`,
2. prefer zero-export or de minimis export in the optimized result,
3. if small residual exports remain because of hourly granularity or solver limitations, report them explicitly and decide whether to tighten the constraint in a second pass.

### Recommended implementation options

#### Option A - Hard no-export target where feasible

- Use REopt settings and, if needed, the Vietnam-specific Julia wrapper to make exports impossible or uneconomic.
- Treat any export in the solved result as a modeling failure that triggers redesign.

#### Option B - Near-zero-export target with explicit reporting

- Set export compensation to zero and constrain or discourage export.
- Accept trivial residual export if it is operationally negligible.
- Publish annual exported energy and export fraction explicitly.

### Recommended default

Use Option B first.

Why: it is safer and more transparent than pretending hourly zero export is always mathematically clean in REopt, especially when we are also fixing battery duration.

### Question for review 1 (agreed with default)

Should `without excess` mean:

1. absolutely zero export in every hour,
2. zero or near-zero annual export with tolerance for tiny residual spill, or
3. simply no merchant business model, even if modest operational export remains?

Recommended default: `2`, because it is the most practical first implementation target and still aligns with the commercial intent.

## 6. Battery duration requirement

The request specifies `2 hours duration BESS`.

### Recommended default interpretation

- REopt should optimize battery power `kW` while battery energy `kWh` is tied to exactly `2 x kW`.
- PySAM should mirror the same nameplate duration in its detailed plant configuration unless a later sensitivity intentionally changes it.

### Why this matters

The latest Ninhsim `60%` case let REopt choose about a `6.05-hour` battery. `DPPA Case 1` should answer a different commercial question: what is the best first design when duration is fixed at `2 hours`.

### Question for review 2 (agreed with default)

Should `2 hours` be treated as:

1. an exact design lock for both REopt and PySAM,
2. an REopt initial-sizing lock only, with PySAM allowed to test nearby variants, or
3. a minimum duration, not an exact duration?

Recommended default: `1`, because your request sounds like a defined project configuration rather than a sensitivity sweep.

## 7. Proposed REopt scope

### In scope

- `PV`
- `ElectricStorage`
- residual EVN grid imports

### Out of scope by default

- `Wind`
- merchant export optimization
- diesel or thermal generation
- resilience constraints unless explicitly requested later

### Core REopt job

Use REopt to answer:

`Given the Ninhsim load shape, Vietnam tariff basis, solar-only plus 2-hour battery configuration, and no-excess intent, what is the initial customer-anchored optimal PV kW and BESS kW?`

### Recommended REopt implementation points

1. Clone the Ninhsim case into a new `DPPA Case 1` scenario JSON.
2. Remove wind entirely.
3. Preserve the Ninhsim `loads_kw` and site/tariff basis.
4. Constrain the battery to `2-hour` duration if REopt inputs allow that directly; if not, use a controlled outer loop or wrapper constraint.
5. Make export unattractive or disallowed in the first pass.
6. Solve for the lowest-cost or best-customer-value design under those constraints.
7. Report PV production, battery throughput, grid purchases, curtailment, and any remaining export.

### Question for review 3

What should REopt optimize for in `DPPA Case 1`?

1. minimum customer lifecycle cost,
2. minimum project capex while satisfying the no-excess design intent,
3. maximum on-site renewable utilization, or
4. a hybrid objective with customer cost first and export avoidance as a guardrail?

User answer: 2. min project capex

## 8. Recommended PySAM scope for this scenario

This is the part that most differs from the current repo workflow.

### Recommended default direction

Move beyond the current `CustomGenerationProfileSingleOwner` shortcut for this scenario and instead build a fuller PySAM configuration that explicitly represents:

- PV system sizing and generation behavior,
- battery nameplate energy and power,
- battery dispatch/control assumptions,
- degradation and replacement assumptions,
- and project finance.

### Recommended module path to investigate first

The most likely useful direction is a PySAM stack that couples a detailed PV model and battery-capable system model into `Single Owner`, rather than feeding `Single Owner` only a custom hourly generation array.

The exact module pair should be confirmed during implementation research, but the plan assumption is:

- REopt determines the first candidate size and operating intent,
- PySAM reconstructs that candidate with a more detailed PV+battery model,
- `Single Owner` remains the first finance model unless a more complex ownership structure is requested later.

### Why this is better than the current shortcut

- It captures PV-side production behavior more realistically.
- It gives battery losses, battery throughput, and dispatch assumptions a more native home.
- It avoids collapsing customer-served and other energy values into one blended price stream unless that simplification is still consciously chosen.

### Question for review 4

For the fuller PySAM pass, should the default commercial structure still be `Single Owner`, or do you already want a different ownership model in scope?

User answer: review the dppa buyer guide to use the structure most suitable

### Question for review 5

Should the PySAM battery be allowed to charge from the grid, or only from on-site solar?

User: solar only 

### Question for review 6 (agree wit default)

Should PySAM dispatch be configured to:

1. prioritize self-consumption and export avoidance,
2. prioritize bill savings under TOU pricing,
3. follow a fixed charge/discharge window, or
4. evaluate multiple dispatch logics as sensitivities?

Recommended default: `1` first, then test `2` only if needed as a sensitivity.

## 9. Proposed two-engine workflow

## Phase A - Freeze case definition and naming

### Tasks

1. Name the new scenario family `DPPA Case 1` across scenario, artifact, and report surfaces.
2. Reuse the Ninhsim load profile and site basis.
3. Freeze initial design intent: `PV + 2-hour BESS + no-excess target + fuller PySAM pass`.
4. Record all unresolved questions in the assumptions block before implementation starts.

### Deliverables

- Planning artifact with agreed defaults
- Case naming convention for scenarios, results, and reports

## Phase B - Build the REopt initial-sizing scenario

### Tasks

1. Clone the Ninhsim scenario into a new `DPPA Case 1` REopt input.
2. Remove wind and any merchant-export logic from the case intent.
3. Set battery duration to `2 hours`.
4. Configure export to be zero, near-zero, or uneconomic based on the agreed interpretation.
5. Run a no-solve validation first, then solve the case.
6. Save the solved REopt result and an energy-balance summary artifact.

### Deliverables

- New scenario JSON
- REopt results JSON
- Energy-balance summary with delivered load, curtailment, and any export residual

## Phase C - Design the fuller PySAM bridge

### Tasks

1. Choose the PySAM physical module path that best supports PV plus battery behavior for this case.
2. Map REopt first-pass sizes into PySAM physical inputs.
3. Decide which assumptions stay anchored to REopt and which are re-evaluated inside PySAM.
4. Make dispatch and charging-source assumptions explicit.
5. Keep ownership and finance assumptions explicit and Vietnam-localized.

### Deliverables

- Documented REopt-to-PySAM bridge design
- Canonical PySAM input payload or builder module
- Assumptions block for dispatch, degradation, replacement, and finance

## Phase D - Run the PySAM full-cycle case

### Tasks

1. Execute the detailed PV plus battery PySAM configuration for the REopt-sized candidate.
2. Compare PySAM annual production and energy allocation against REopt first-pass expectations.
3. Measure any divergence in export, curtailment, battery utilization, and financial outputs.
4. Decide whether the first REopt size is still acceptable or needs a bounded re-iteration.

### Deliverables

- PySAM results artifact
- REopt vs PySAM comparison artifact
- Decision note on whether re-iteration is required

## Phase E - Publish the final decision package

### Tasks

1. Build a combined artifact that shows the REopt initial size, the PySAM detailed result, and any iteration delta.
2. Show whether the no-excess requirement was actually met in both tools.
3. Surface the final PV size, BESS size, annual energy flows, and finance results.
4. Publish either a markdown memo or HTML report in the repo's established style.

### Deliverables

- Combined decision artifact
- Review report
- Updated `activeContext.md` notes

## 10. Recommended outputs

Exact filenames can be finalized during implementation, but the expected shape is:

- `plans/active/dppa_case_1_plan.md`
- `scenarios/case_studies/ninhsim/<date>_ninhsim_dppa-case-1.json`
- `artifacts/results/ninhsim/<date>_ninhsim_dppa-case-1_reopt-results.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-1_reopt-summary.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-1_pysam-results.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-1_comparison.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-1_combined-decision.json`
- `reports/<date>-ninhsim-dppa-case-1.html`

## 11. Key risks and modeling traps

1. A strict no-export requirement can push the system toward undersizing, which may conflict with the commercial instinct to maximize solar yield.
2. A fixed `2-hour` battery may be too short to absorb midday surplus cleanly at the load shape Ninhsim has, especially if the PV system is large.
3. REopt and PySAM may disagree materially once PySAM uses fuller plant and battery logic rather than the current custom-generation shortcut.
4. If charging-source logic is not fixed up front, the battery can silently shift from self-consumption support into grid-arbitrage behavior.
5. If the DPPA revenue structure is not frozen clearly, the scenario can drift into a pure behind-the-meter TOU savings case instead of a true DPPA-oriented case.

## 12. Questions for your review

Please review these before implementation. Recommended defaults are already embedded above.

1. What exactly does `without excess` mean: hourly zero export, near-zero annual export, or simply no merchant commercial intent?
2. Should `2-hour` duration be an exact lock in both REopt and PySAM?
3. What should REopt optimize for: customer cost, capex minimization, self-consumption maximization, or a hybrid objective?
4. Should the fuller PySAM pass keep `Single Owner` as the ownership model, or do you want another structure in scope now?
5. Can the battery charge from grid, or solar only?
6. What dispatch philosophy should PySAM use first: self-consumption, TOU savings, fixed controller, or multiple sensitivities?
7. If REopt returns a design with small residual export, should that be accepted, iterated, or rejected? user: accepted if negligible, rejected if significant
8. Should PySAM be allowed to recommend a small resize after the REopt initial sizing pass, or is REopt sizing meant to stay fixed? user: allowed if not significant
9. What is the intended commercial settlement basis for this case: behind-the-meter DPPA, private-wire logic, virtual DPPA logic, or a simplified internal price benchmark for now? user: private wire logic
10. Which final metric should determine the recommended design if REopt and PySAM differ: customer savings, project IRR, equity IRR, export avoidance, or another metric? user: project and equity IRR

## 13. Recommended default path if no further edits are made

- Reuse the Ninhsim `8760` load profile unchanged.
- Build a new `DPPA Case 1` scenario under `scenarios/case_studies/ninhsim/`.
- Use REopt for initial `PV + BESS` sizing with an exact `2-hour` battery duration.
- Treat no-excess as a near-zero-export design target, not a merchant-export business model.
- Use solar-only battery charging first.
- Keep `Single Owner` as the first finance model, but replace the finance-only custom-generation shortcut with a fuller PV-plus-battery PySAM configuration.
- Compare the REopt first-pass candidate against the PySAM detailed run and iterate only if the mismatch is material.
