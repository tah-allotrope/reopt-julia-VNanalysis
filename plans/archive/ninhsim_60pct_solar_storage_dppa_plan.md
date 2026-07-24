# Ninhsim 60% Solar + Storage REopt + PySAM Plan

> Status: Draft for review - 2026-04-06
> Scope: Build a reproducible workflow that uses the existing Ninhsim load profile to size solar and storage with REopt, then calculate developer-side revenue and financial returns with PySAM under a DPPA strike pegged to 5% below the weighted EVN industrial tariff for `22-110 kV`.
> Canonical plan path: `plans/active/ninhsim_60pct_solar_storage_dppa_plan.md`

## 1. Objective

Create a single case-study workflow for Ninhsim that does all of the following:

1. Uses the existing Ninhsim `8760` load profile as the demand basis.
2. Sizes `solar PV + BESS` only in REopt.
3. Targets a project that serves `60%` of site demand.
4. Prices the DPPA at `95%` of the weighted EVN industrial tariff for `22-110 kV`.
5. Calculates developer revenue and project finance outputs in PySAM for the party taking on the site.
6. Produces machine-readable artifacts and a clear report for review.

## 2. Working interpretation and why it matters

The cleanest two-engine workflow is:

1. Use REopt for the physical and tariff-aware sizing problem.
2. Use PySAM for the developer-side finance problem on the solved REopt sizing and delivery profile.

This keeps each engine in the role it is already strongest at in this repo.

### Recommended default interpretation

- REopt solves the `solar + storage` sizing problem.
- PySAM does not resize the system; it evaluates the solved REopt case from the developer perspective.
- The main sizing constraint is annual demand coverage, while the strike is fixed by the tariff peg.

### Clarifying question 1 (agreed with default)

Does "meet 60% of the demand" mean `annual renewable energy delivered to site load >= 60% of annual site load`?

Recommended default: Yes, interpret `60%` on an annual delivered-energy basis, not as hourly self-sufficiency and not as nameplate capacity relative to peak load.

Why this matters: REopt can optimize around annual energy and dispatch more cleanly than around an implicit hourly coverage target, and the result will be much easier to explain.

### Clarifying question 2 (agreed with default)

Should the target be treated as `at least 60%` or `as close as possible to exactly 60%`?

Recommended default: `At least 60%`, then report the achieved percentage and any overbuild.

Why this matters: exact-equality constraints are harder to implement cleanly and are usually less stable than a minimum target plus transparent reporting.

## 3. Current repo baseline that this plan should build on

The repo already has reusable Ninhsim building blocks:

- Canonical Ninhsim load and solved REopt workflow already exist.
- A buyer-side tariff benchmark already exists in `artifacts/reports/ninhsim/2026-04-01_ninhsim-cppa-analysis.json`.
- A PySAM `Single Owner` developer-finance bridge already exists from Phase 4.
- A strike discovery workflow already exists from Phase 5.

Known current Ninhsim reference values from repo artifacts:

- Annual site load: about `184.286 GWh`
- Existing weighted EVN benchmark: about `2018.878 VND/kWh`
- `5%` below that benchmark: about `1917.935 VND/kWh`
- Same value in USD at the repo exchange rate `26,400 VND/USD`: about `0.072649 USD/kWh`

Important note: this requested strike peg is slightly lower than the prior Phase 4 commercial input of about `1934.498 VND/kWh`, so the developer finance outcome may be weaker than the current Phase 4 artifact unless the new solar-plus-storage-only sizing materially changes cost or delivery.

### Clarifying question 3 (agreed with default)

Please confirm that the intended strike anchor is `5% below the weighted EVN tariff itself`, not `5% below the maximum CPPA ceiling` from the earlier Ninhsim passes.

Recommended default: use `0.95 x weighted EVN benchmark tariff` directly, because that is what your latest instruction states.

## 4. Recommended modeling scope

### Technologies in scope

- `Solar PV`
- `Battery energy storage`
- Residual grid supply from EVN

### Technologies out of scope by default

- `Wind`
- Diesel or other thermal generation
- Merchant export optimization unless it is already unavoidable in the solved REopt case

### Clarifying question 4 (agreed with default)

Should this workflow be strictly `solar + storage only`, with `wind fully removed` from the Ninhsim optimization inputs?

Recommended default: Yes, remove wind entirely so the study answers the exact solar-plus-storage question without hidden help from prior wind-heavy Ninhsim results.

### Clarifying question 5 (agreed with default)

Should storage be allowed to charge from the grid, or should it be limited to charging from on-site solar only?

Recommended default: solar-only charging unless the repo's current Ninhsim scenario or commercial structure explicitly intends grid-charged arbitrage.

Why this matters: grid charging can materially change both the 60% coverage interpretation and the developer revenue story.

### Clarifying question 6

What should happen to renewable energy that is not consumed by the site in the same hour?

User answer: should follow the guide for dppa for developers to sell excess to spot market and rough estimation of fmp price 

## 5. Recommended optimization objective (agreed with default)

There are two possible meanings of "optimal sizing" here, and they are not the same.

### Option A: Customer-anchored optimum

Use REopt to find the least-cost solar-plus-storage design that achieves the `60%` demand target under the pegged DPPA strike, then feed that design into PySAM for developer returns.

### Option B: Developer-anchored optimum

Search across feasible REopt solar-plus-storage designs and choose the one that gives the developer the best return while still satisfying the `60%` demand target and contract assumptions.

### Recommended default

Start with Option A for the first pass.

Why: REopt is already the buyer-side sizing engine in this repo, and PySAM can then evaluate whether the customer-feasible design is investable for the developer.

### Clarifying question 7 (agreed with default)

Which definition of "optimal" do you want for this study?

Recommended default: `customer-anchored optimum`, then a second decision block that states whether the resulting design is financeable for the developer at the pegged strike.

## 6. Proposed workflow

## Phase A - Freeze the commercial target and tariff peg

### Tasks

1. Reuse the Ninhsim load profile already stored in the repo.
2. Recompute the weighted EVN industrial tariff for the `22-110 kV` class using the Ninhsim load profile and the current tariff assumptions in the repo.
3. Set the year-one DPPA strike to `95%` of that weighted tariff.
4. Record the tariff basis and conversion to USD explicitly in a machine-readable assumptions block.

### Deliverables

- Assumptions block embedded in the new case-study artifacts
- Year-one strike derivation in both `VND/kWh` and `USD/kWh`

### Clarifying question 8 (agreed with default)

Should the DPPA strike remain a fixed year-one discount only, or should the full strike path continue to track EVN tariff escalation over time?

Recommended default: peg the year-one strike at `95%` of the weighted EVN tariff, then escalate it using the same tariff-escalation assumption already used in the Ninhsim workflow.

Why this matters: a fixed nominal strike and an EVN-linked strike path can produce very different PySAM finance results.

## Phase B - Build the REopt solar-plus-storage sizing case

### Tasks

1. Clone the Ninhsim scenario into a new solar-plus-storage-only case-study input.
2. Remove wind from the candidate technologies.
3. Preserve the Ninhsim load profile and the `22-110 kV` EVN tariff basis.
4. Add a constraint or deterministic outer-loop method so the final design achieves the `60%` demand target.
5. Solve the REopt case and record the optimal `PV kW`, `BESS kW`, and `BESS kWh`.

### Recommended implementation pattern

If REopt cannot express the `60%` target directly with existing inputs, use a controlled outer loop:

1. solve candidate solar-plus-storage designs,
2. measure `renewable_delivered_to_load / total_load`,
3. tighten the search until the minimum-cost design that clears the target is found.

This is safer than inventing a hidden approximation.

### Deliverables

- New Ninhsim solar-plus-storage scenario JSON
- Solved REopt results JSON
- Coverage summary block showing the achieved percent of site demand served

### Clarifying question 9 

If the least-cost solar-plus-storage design cannot hit `60%` cleanly without major curtailment or impractical battery sizing, should the workflow:

1. still force `60%`,
2. report the nearest feasible result, or
3. open a sensitivity band such as `50%`, `55%`, `60%`, `65%`?

User answer: 2. report nearest feasible result

## Phase C - Build the developer-side PySAM finance case

### Tasks

1. Reuse the existing `Single Owner` bridge pattern rather than creating a new finance stack.
2. Convert the solved REopt delivery profile into PySAM custom-generation inputs.
3. Apply the pegged DPPA strike assumption from Phase A.
4. Calculate annual revenue, project NPV, project IRR, pre-tax IRR, DSCR, debt size, and annual cash flow.
5. Keep the result normalized into a canonical JSON artifact.

### Recommended default finance basis

- Use the repo's current Vietnam wrapper defaults first.
- Make any project-specific overrides explicit and isolated.

### Clarifying question 10

Should I use the current repo-default developer finance assumptions for tax, leverage, debt tenor, discount rate, and inflation, or do you want project-specific assumptions for this site?

User answer: use default from vn_tech_cost and/or other vietnam specific assumptions

### Clarifying question 11

Do you want the output to emphasize `project returns`, `equity returns`, or both?

Recommended default: report both, but keep `project IRR`, `equity IRR`, `NPV`, and `min DSCR` as the headline finance metrics.

## Phase D - Produce the combined decision artifact

### Tasks

1. Join the REopt sizing result and the PySAM finance result into one Ninhsim decision artifact.
2. Show the energy story and the finance story in the same payload.
3. Make the contract peg explicit so the reader can audit the tariff-to-strike logic without recomputing it.
4. Highlight whether the design is both operationally feasible and financially investable.

### Minimum combined artifact contents

- Site load basis and tariff basis
- Solved PV and BESS size
- Annual renewable-delivered percentage of load
- Year-one and escalated strike path
- Year-one developer revenue
- Lifetime discounted revenue
- Project and equity return metrics
- DSCR path and minimum DSCR
- Customer benchmark comparison at the pegged strike
- Key assumptions and warnings

### Clarifying question 12 (agreed with default)

Do you want the final combined output to be a single decision artifact, or do you want separate REopt and PySAM artifacts plus a summary report that cross-references both?

Recommended default: produce both the engine-specific artifacts and one combined decision artifact for review.

## Phase E - Validation and review outputs

### Tasks

1. Add targeted regression coverage for the tariff peg, the `60%` target logic, and the REopt-to-PySAM bridge.
2. Re-run the Ninhsim case-study scripts in the repo-local `.venv` where PySAM is required.
3. Generate a synchronized HTML report in the repo's established report-template style.
4. Record the final assumptions, open questions, and caveats in `activeContext.md`.

### Deliverables

- Targeted tests in `tests/python/integration/` and `tests/python/pysam/`
- Canonical JSON artifacts
- HTML report in `reports/`
- `activeContext.md` review block

## 7. Proposed output file set

Exact filenames can be finalized during implementation, but the expected shape is:

- `scenarios/case_studies/ninhsim/<date>_ninhsim_solar-storage_60pct.json`
- `artifacts/results/ninhsim/<date>_ninhsim_solar-storage_60pct_reopt-results.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_solar-storage_60pct_analysis.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_solar-storage_60pct_single-owner.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_solar-storage_60pct_combined-decision.json`
- `reports/<date>-ninhsim-solar-storage-60pct-dppa.html`

## 8. Key risks to call out before implementation

1. A `solar + storage only` design may need significant oversizing or battery duration to truly serve `60%` of annual load at Ninhsim.
2. The requested strike peg is lower than the prior Phase 4 developer-finance run, so developer returns may weaken further.
3. If export treatment is not fixed up front, the result can look much better or much worse than intended.
4. "Optimal" is ambiguous unless we explicitly choose whether customer economics or developer economics drives sizing.
5. A system that clears the `60%` physical target may still fail the developer finance screen at the pegged strike.

## 9. Recommended execution order once questions are answered

1. Confirm the `60%` target definition and whether it is minimum or exact.
2. Confirm solar-only vs solar-plus-grid-charged-storage behavior.
3. Confirm strike escalation treatment.
4. Confirm whether "optimal" means customer-anchored or developer-anchored.
5. Build the new REopt Ninhsim solar-plus-storage case.
6. Solve the case and lock the achieved coverage metrics.
7. Feed the solved case into PySAM with the pegged strike.
8. Publish combined artifacts, tests, and a report.

## 10. Questions for your review

Please answer these before implementation if you want the workflow to match your exact intent:

1. Is `60%` measured on annual renewable energy delivered to load?
2. Should the target be `at least 60%` or `exactly 60%`?
3. Confirm the strike anchor is `5% below weighted EVN tariff`, not `5% below the prior CPPA ceiling`.
4. Should wind be removed entirely from the optimization?
5. Can the battery charge from the grid, or solar only?
6. How should excess renewable energy be treated: curtailment, export, or merchant sale?
7. Should sizing be customer-optimal or developer-optimal?
8. Should the strike escalate with EVN tariff assumptions after year one?
9. If `60%` is hard to reach cleanly, should we force it or open a sensitivity band?
10. Should I use repo-default developer finance assumptions, or do you have project-specific finance terms?
11. Which finance metrics matter most for the decision: project returns, equity returns, or both?
12. Do you want one combined decision artifact in addition to the engine-specific outputs?

Until you answer otherwise, the recommended default is:

- annual delivered-energy target,
- minimum `60%` threshold,
- solar plus storage only,
- solar-only battery charging,
- conservative excess-energy treatment,
- customer-anchored REopt sizing,
- year-one strike pegged at `95%` of weighted EVN tariff with EVN-style escalation afterward,
- repo-default Vietnam finance assumptions,
- combined REopt plus PySAM decision artifact.
