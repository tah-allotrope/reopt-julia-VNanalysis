# DPPA Case 2 - Synthetic DPPA Buyer-Cost Workflow Plan

> Status: Draft for review - 2026-04-14
> Scope: Create a new `DPPA Case 2` workflow that builds on the Ninhsim load basis and the `DPPA Case 1` lessons, but shifts the commercial model from a private-wire ceiling-tariff screen to a synthetic / financial DPPA workflow with explicit buyer-side settlement logic, excess-generation risk treatment, and separate buyer-versus-developer outputs.
> Canonical plan path: `plans/active/dppa_case_2_plan.md`

## 1. Objective

Create a new case-study workflow that does all of the following:

1. Reuses the existing Ninhsim `8760` site load profile unless you choose a different load basis.
2. Creates a new scenario family named `DPPA Case 2`.
3. Treats the commercial structure as a synthetic / financial DPPA by default, not a private-wire sale.
4. Separates the physical energy model from the buyer-side settlement model.
5. Computes an hourly buyer payment stack that includes EVN-linked power cost, DPPA adder, CfD true-up, and retail shortfall treatment.
6. Makes settlement quantity and excess-generation treatment explicit instead of leaving them implicit.
7. Keeps a developer-side screening view, but does not collapse buyer and developer economics into one blended strike assumption.
8. Produces machine-readable artifacts plus a review-ready markdown or HTML summary once implementation begins.

## 2. Why this scenario is different from Case 1

`DPPA Case 1` already answers a useful question, but it is not the same commercial structure as the repo's DPPA buyer research note.

### Case 1 did this

- used `private_wire` logic,
- disabled export pathways in the case design,
- used the Decree 57 private-wire ceiling tariff as the year-one strike basis,
- and fed PySAM a direct PPA-price view rather than a synthetic-DPPA settlement ledger.

### Case 2 should do this instead

- preserve a physical generation-and-load matching model,
- then settle the case through a synthetic DPPA buyer-cost stack,
- explicitly model what part of renewable generation is matched to load,
- explicitly model what happens to shortfall and excess volumes,
- and show separate buyer and developer economic conclusions.

### Recommended default interpretation

- `DPPA Case 2` should be the repo's first canonical synthetic / financial DPPA case.
- `DPPA Case 1` should remain the private-wire reference point.
- The main decision lens for Case 2 should be buyer all-in cost and contract-shape risk first, with developer finance retained as a second screen.

## 3. Working commercial interpretation

The repo research note says the clean buyer view for a synthetic DPPA is:

```text
Total buyer payment = payment to EVN PC + CfD payment to/from generator
```

and that matched DPPA energy is approximately:

```text
all-in matched kWh ~= strike + DPPA adder + small basis/loss adjustment
```

That means Case 2 should explicitly represent at least these commercial elements:

1. EVN market-linked payment for DPPA-covered volume.
2. DPPA system charge / adder.
3. KPP or loss-coefficient effect if applicable.
4. CfD payment or receipt against the market reference price.
5. Normal EVN retail tariff on shortfall energy.
6. Contract-shape exposure if settled generation exceeds actual load in an interval.

## 4. Recommended modeling philosophy

### Engine roles

#### REopt role

- Continue to handle the first-pass physical sizing and hourly energy-flow problem.
- Optimize the physical asset mix under a clearly stated physical objective.
- Output hourly renewable delivery, grid purchases, curtailment, charging, discharging, and any export or spill.

#### Settlement role

- Add a dedicated post-processing layer for buyer-side DPPA settlement.
- Use the solved hourly physical outputs plus explicit contract rules to compute buyer bills and CfD cashflows.
- Keep the settlement logic separate from REopt so the commercial assumptions are transparent and replaceable.

#### PySAM role

- Stay available as the fuller developer-side plant and finance validation layer.
- Be used only after the physical case and settlement rules are frozen, so buyer and developer stories do not drift.

### Recommended default final decision logic

- `Gate 1`: physical case is feasible and operationally credible.
- `Gate 2`: buyer all-in cost is acceptable against the chosen benchmark.
- `Gate 3`: excess-generation settlement risk is visible and tolerable.
- `Gate 4`: developer-side finance is at least reviewable under the chosen strike assumptions.

## 5. Core design choice: what exactly is Case 2 solving for?

This is the most important scoping decision.

### Recommended default interpretation

Treat `DPPA Case 2` as:

`a customer-first synthetic DPPA case that tests whether a candidate solar-plus-storage project can produce acceptable buyer all-in cost once Vietnam-style DPPA settlement mechanics are applied.`

### Practical implication

This means the primary outputs should not be limited to PV size, BESS size, and developer IRR. They should also include:

- matched-energy cost,
- blended full-load cost,
- shortfall cost,
- excess-generation exposure,
- and the difference versus the buyer's benchmark EVN path.

### Question for review 1

What is the main business question for `DPPA Case 2`?

> **User answer:** All three below
> 1. Can a synthetic DPPA lower buyer all-in cost versus EVN?
> 2. Can a synthetic DPPA work for developer at one negotiated strike?
> 3. What contract shape minimizes buyer excess-settlement risk?

## 6. Contract structure recommendation

### Recommended default

Use `synthetic` / `grid_connected` DPPA logic for Case 2.

### Why

- It aligns with the buyer guide that drove the readiness review.
- It avoids duplicating Case 1's private-wire logic.
- It creates a clean split between the repo's two DPPA case families.

### Question for review 2

Should `DPPA Case 2` be modeled as:

> **User answer:** 1. synthetic / financial DPPA

## 7. Settlement quantity and contract-shape rule

The buyer guide says settlement quantity is one of the biggest commercial questions.

### Candidate rules

1. `generated volume`
2. `allocated contract volume`
3. `consumed volume`
4. `min(load, contracted generation)`
5. another hybrid rule

### Recommended default

Use `min(load, contracted generation)` as the matched block for the first-pass buyer-cost case, then report excess generation separately as an explicit exposure layer.

### Why

- It is the cleanest customer-first first pass.
- It avoids overstating buyer value by assuming all generated volume is beneficial.
- It still keeps the excess-risk question visible instead of burying it.

### Question for review 3

What settlement quantity should Case 2 use first?

> **User answer:** `4` — use `min(load, contracted generation)`

## 8. Excess-generation treatment

Case 2 should not hide overgeneration behind a simple export flag.

### Recommended default treatment

Split each hour into:

- matched renewable volume,
- shortfall volume,
- excess generation volume,
- and, if applicable, excess volume that still triggers CfD exposure.

### Reporting requirement

Every Case 2 output should publish at least:

- annual matched MWh,
- annual shortfall MWh,
- annual excess MWh,
- annual CfD on matched volume,
- annual CfD on excess volume,
- blended buyer cost per consumed kWh,
- and peak-risk hours or intervals.

### Question for review 4

If generation exceeds load in an interval, should Case 2 assume:

> **User answer:** 1. excess is excluded from buyer settlement

## 9. Strike-price treatment

Case 1 used a private-wire tariff ceiling lookup. Case 2 should not do that by default.

### Recommended default

Treat strike price as an explicit commercial input or sweep variable.

### Candidate approaches

1. single strike input chosen by you,
2. strike sweep across a negotiation band,
3. buyer ceiling versus developer floor comparison,
4. dynamic strike path with escalation logic.

### Recommended default path

Start with `2` and `3` together:

- run a strike sweep around a plausible band,
- and publish where buyer-cost acceptability and developer-finance acceptability overlap, if anywhere.

### Question for review 5

How should Case 2 treat the strike?

> **User answer:** strike 5% below EVN weighted tariff with escalation logic

## 10. DPPA adder and loss-coefficient assumptions

The buyer guide notes that the DPPA adder and loss coefficient materially affect all-in cost.

### Recommended default treatment

- model the DPPA adder as an explicit parameter block,
- model KPP / loss coefficient as an explicit parameter block,
- keep both visible in the machine-readable artifact even if one is held constant.

### Question for review 6

For the first Case 2 pass, should the settlement layer use:

> **User answer:** 1. one fixed DPPA adder and one fixed KPP assumption

## 11. Market-price series and EVN benchmark basis

Case 2 needs a clear market reference series for settlement.

### Recommended default

Use an hourly market-price proxy or actual FMP / CFMP series if available, and keep the EVN retail tariff basis separate for shortfall billing.

### Why

The synthetic DPPA settlement cannot be explained cleanly if market reference price and retail benchmark are blended together.

### Question for review 7

What market-price basis should Case 2 use first?

> **User answer:** 1. an actual hourly FMP or CFMP series if we have one from web search if not a proxy series derived from repo data

## 12. Physical scope recommendation

### In scope by default

- `PV`
- `ElectricStorage`
- residual EVN imports
- settlement post-processing

### Out of scope by default

- `Wind`
- diesel or thermal generation
- resilience constraints
- private-wire ceiling-tariff logic as the main pricing basis

### Battery recommendation

If the project concept still includes storage, Case 2 should require nonzero storage rather than only locking duration.

### Question for review 8

Should Case 2 require a real battery buildout?

> **User answer:** 2. no, let REopt optimize storage away if it wants

## 13. REopt objective recommendation

Case 1 exposed a mismatch between the recorded user intent and the apparent implemented solve behavior.

### Recommended default

Keep REopt on a clear physical objective, not a pseudo-commercial objective that the tool does not natively implement cleanly.

### Candidate physical objectives

1. minimum lifecycle cost,
2. minimum buyer-cost subject to physical constraints,
3. minimum curtailment or excess,
4. maximum matched renewable delivery,
5. paired objective with a simple physical primary objective and reporting-based commercial filters.

### Recommended default

Use `5`: solve on a simple physical objective, then let the buyer-settlement layer decide whether the commercial case passes.

### Question for review 9

What REopt objective should Case 2 use first?

> **User answer:** 1. minimum buyer-cost subject to physical constraints and maximum matched renewable delivery

## 14. PySAM role recommendation

Case 2 should not force PySAM into the loop before the buyer-side settlement logic is stable.

### Recommended default

Phase the work so that:

1. REopt physical case and settlement ledger land first,
2. PySAM developer-side validation comes second,
3. any final dual-party negotiation screen comes third.

### Why

This keeps the first Case 2 pass focused on the main repo gap revealed by the readiness review: missing buyer settlement logic.

### Question for review 10

Should the first implementation of Case 2 include PySAM immediately?

> **User answer:** 1. yes, full buyer plus developer workflow in one pass

## 15. Proposed multi-phase implementation path

## Phase A - Freeze case definition and naming

### Tasks

1. Name the new scenario family `DPPA Case 2` across plan, scenario, artifact, and report surfaces.
2. Freeze whether the case is synthetic only or a branch comparison against private wire.
3. Freeze the load basis, site basis, voltage basis, and tariff basis.
4. Record all unresolved questions and recommended defaults before implementation starts.

### Deliverables

- Planning artifact with agreed defaults
- Case naming convention for scenarios, results, and reports
- Assumptions register for open contract-rule questions

## Phase B - Design the commercial settlement ledger

### Tasks

1. Define the hourly settlement formula and data contract.
2. Define the settlement quantity rule.
3. Define how DPPA adder and KPP are represented.
4. Define how shortfall and excess volumes are billed.
5. Define separate buyer and developer cashflow outputs.

### Deliverables

- Settlement design note
- Canonical settlement-input schema
- Unit-test matrix for settlement edge cases

## Phase C - Build the REopt physical-sizing scenario

### Tasks

1. Clone the Ninhsim case into a new `DPPA Case 2` scenario JSON.
2. Remove legacy private-wire pricing shortcuts from the physical case definition.
3. Configure the physical asset scope for the chosen Case 2 branch.
4. If BESS is required, enforce a nonzero storage floor rather than duration lock only.
5. Run a no-solve validation first, then solve the case.

### Deliverables

- New scenario JSON
- REopt results JSON
- Physical energy-balance summary artifact

## Phase D - Implement and validate buyer-side settlement

### Tasks

1. Compute hourly matched, shortfall, and excess quantities.
2. Compute EVN-linked payment, DPPA adder, KPP adjustment, and CfD payment.
3. Compute buyer full-load blended cost and benchmark delta.
4. Publish scenario-level buyer-cost and contract-risk outputs.
5. Add failing-then-passing regression coverage for the ledger and edge cases.

### Deliverables

- Buyer settlement artifact
- Buyer benchmark comparison artifact
- Settlement regression tests

## Phase E - Add strike and contract-rule sensitivities

### Tasks

1. Sweep strike inputs across the agreed negotiation band.
2. Sweep at least one excess-settlement rule if not fixed.
3. Sweep at least one DPPA-adder or KPP sensitivity if not fixed.
4. Identify overlap zones where buyer and developer views are both acceptable.

### Deliverables

- Strike sensitivity artifact
- Contract-rule sensitivity artifact
- Candidate negotiation band summary

## Phase F - Add developer-side PySAM validation

### Tasks

1. Map the physical Case 2 candidate into the fuller PySAM workflow if requested.
2. Keep buyer settlement and developer finance outputs separate.
3. Compare REopt physical outputs versus PySAM plant behavior.
4. Report whether the candidate remains credible once fuller plant logic is applied.

### Deliverables

- PySAM results artifact
- REopt versus PySAM comparison artifact
- Developer screening artifact

## Phase G - Publish the final decision package

### Tasks

1. Build one combined artifact with physical, buyer, developer, and risk layers.
2. Publish a review report in markdown or HTML.
3. Record the final assumptions and unresolved commercial questions.
4. Update `activeContext.md` with the canonical artifact paths and next-step guidance.

### Deliverables

- Combined decision artifact
- Review report
- Updated `activeContext.md` notes

## 16. Recommended outputs

Exact filenames can be finalized during implementation, but the expected shape is:

- `plans/active/dppa_case_2_plan.md`
- `scenarios/case_studies/ninhsim/<date>_ninhsim_dppa-case-2.json`
- `artifacts/results/ninhsim/<date>_ninhsim_dppa-case-2_reopt-results.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-2_physical-summary.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-2_buyer-settlement.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-2_buyer-benchmark.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-2_strike-sensitivity.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-2_contract-risk.json`
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-2_pysam-results.json` if PySAM is included
- `artifacts/reports/ninhsim/<date>_ninhsim_dppa-case-2_combined-decision.json`
- `reports/<date>-dppa-case-2.html` or `reports/<date>-dppa-case-2.md`

## 17. Key risks and modeling traps

1. The case can silently drift back into a private-wire or behind-the-meter simplification if buyer settlement is not treated as its own first-class layer.
2. Settlement quantity can dominate buyer economics more than the physical size does, so it must be frozen explicitly.
3. Using a weak market-price proxy can create false confidence in the buyer all-in result.
4. If DPPA adder and KPP are hidden as constants, reviewers may mistake them for validated facts rather than placeholders.
5. If storage is optional, the case can optimize to PV-only again and never answer the intended BESS question.
6. If buyer and developer views are blended too early, the strike discussion can become muddy and non-auditable.
7. If sensitivity branches multiply too early, the case can become slow and hard to review before the base logic is trusted.

## 18. Questions for your review

Please review these before implementation. Recommended defaults are already embedded above.

1. What is the main business question for `DPPA Case 2`? → **User:** All three — buyer cost, developer finance, contract risk
2. Should `DPPA Case 2` be synthetic only, private-wire only, or an explicit side-by-side comparison? → **User:** synthetic / financial DPPA
3. What settlement quantity rule should be used first? → **User:** min(load, contracted generation)
4. How should excess generation be treated in buyer settlement? → **User:** excess excluded from buyer settlement
5. Should strike be a single value, a sweep, or a buyer-ceiling versus developer-floor overlap analysis? → **User:** 5% below EVN weighted tariff with escalation
6. Should DPPA adder and KPP be fixed inputs or sensitivity ranges in the first pass? → **User:** fixed DPPA adder and fixed KPP
7. What market-price basis should be used first: actual hourly series, proxy hourly series, flat proxy, or scenario range? → **User:** actual FMP/CFMP if available, otherwise proxy
8. Should Case 2 force a nonzero battery, allow PV-only, or branch both ways? → **User:** let REopt optimize
9. What REopt objective should be used first? → **User:** minimum buyer-cost + maximum matched renewable delivery
10. Should PySAM be part of the first Case 2 implementation pass or follow after buyer-settlement logic lands? → **User:** yes, full workflow in one pass
11. What should the primary pass / fail metric be? → **User:** buyer savings, project IRR, payback years
12. Should the first Case 2 report prioritize customer best interest even if no financeable developer overlap appears? → **User:** Yes

## 19. Agreed DPPA Case 2 baseline after user review

> The following reflects all user decisions from the review above. This is the agreed implementation baseline.

- Build `DPPA Case 2` as the repo's first canonical synthetic / financial DPPA case.
- Reuse the Ninhsim `8760` load profile and current site basis unless you choose another basis.
- Keep REopt responsible for physical sizing and hourly energy flows.
- Add a dedicated buyer-side settlement ledger as the first implementation priority.
- Use `min(load, contracted generation)` as the matched-volume rule.
- Exclude excess generation from buyer settlement (excess is reported separately but does not create buyer CfD exposure).
- Use strike price at 5% below EVN weighted tariff with escalation logic.
- Use fixed DPPA adder and fixed KPP assumption (from Vietnam data or web search).
- Use actual hourly FMP/CFMP series if available from web search, otherwise proxy series from repo data.
- Let REopt optimize storage — do not force nonzero BESS (PV-only allowed unless REopt selects storage).
- REopt objective: minimum buyer-cost subject to physical constraints AND maximum matched renewable delivery.
- Include PySAM in the first pass: full buyer plus developer workflow in one pass.
- Primary pass/fail metrics: buyer savings, project IRR, and payback years.
- Prioritize customer best interest even if no financeable developer overlap appears.
