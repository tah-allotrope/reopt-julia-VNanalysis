# DPPA Case 2 readiness review

Date: 2026-04-14

## Scope

This review cross-checks the implemented `DPPA Case 1` workflow against the repo research note `research/2026-04-07-vietnam-dppa-buyer-guide.md` and highlights the updates that should be made before running `DPPA Case 2`.

## Sources reviewed

- `research/2026-04-07-vietnam-dppa-buyer-guide.md`
- `plans/active/dppa_case_1_plan.md`
- `scripts/python/integration/build_ninhsim_reopt_input.py`
- `src/python/reopt_pysam_vn/integration/dppa_case_1.py`
- `src/python/reopt_pysam_vn/integration/bridge.py`
- `src/python/reopt_pysam_vn/pysam/pvwatts_battery.py`
- `scripts/python/reopt/dppa_settlement.py`
- `data/vietnam/vn_export_rules_decree57.json`
- `scenarios/case_studies/ninhsim/2026-04-09_ninhsim_dppa-case-1.json`
- `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_reopt-summary.json`
- `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_combined-decision.json`

## Executive view

`DPPA Case 1` is internally consistent as a `private_wire` / behind-the-meter screening workflow, but it does not implement the synthetic or financial DPPA buyer payment stack described in the buyer guide.

That means the buyer-guide research is not really being used as the commercial basis for Case 1, even though the plan explicitly said the contract structure should be chosen by reviewing that guide at `plans/active/dppa_case_1_plan.md:225`.

If `DPPA Case 2` is meant to follow the buyer-guide mechanism, it should be treated as a new commercial model, not just a rerun of Case 1 with different sizing.

## What Case 1 currently assumes

| Area | Case 1 implementation | Evidence | Case 2 implication |
| --- | --- | --- | --- |
| Contract structure | Explicitly modeled as `private_wire` | `scripts/python/integration/build_ninhsim_reopt_input.py:215`, `scenarios/case_studies/ninhsim/2026-04-09_ninhsim_dppa-case-1.json:26408` | If Case 2 is synthetic DPPA, this must change |
| Export posture | Wholesale, net metering, and export are disabled in design intent; sell rate is zero in PySAM | `scripts/python/integration/build_ninhsim_reopt_input.py:202`, `src/python/reopt_pysam_vn/integration/bridge.py:343` | Valid for private wire, not for market-settled synthetic DPPA |
| Strike basis | Uses Decree 57 private-wire ceiling lookup, not negotiated strike discovery | `src/python/reopt_pysam_vn/integration/dppa_case_1.py:60`, `data/vietnam/vn_export_rules_decree57.json:22` | Case 2 should not assume ceiling equals transacted price |
| BESS uplift rule | Higher tariff only if BESS clears 10% power, 2h duration, and 5% stored-output thresholds | `src/python/reopt_pysam_vn/integration/dppa_case_1.py:83`, `data/vietnam/vn_export_rules_decree57.json:72` | Relevant only if Case 2 stays private wire and keeps the ceiling logic |
| Buyer payment model | No DPPA adder, no KPP, no CFMP/FMP-linked buyer bill, no shortfall settlement ledger | `src/python/reopt_pysam_vn/pysam/pvwatts_battery.py:23`, `src/python/reopt_pysam_vn/pysam/pvwatts_battery.py:249` | Main gap if Case 2 is meant to follow the buyer guide |
| Settlement quantity | No explicit contract quantity or excess-generation settlement logic | omission across Case 1 bridge/runtime surfaces | Case 2 needs this defined up front |
| Battery requirement | Duration is locked at 2h, but nonzero storage is not enforced | `scenarios/case_studies/ninhsim/2026-04-09_ninhsim_dppa-case-1.json:8840`, `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_reopt-summary.json:10` | Case 2 must force storage if a real BESS case is required |
| REopt objective | Metadata says minimum-capex intent, but the scenario still appears to rely on default lifecycle-cost optimization | `plans/active/dppa_case_1_plan.md:184`, `scripts/python/integration/build_ninhsim_reopt_input.py:225` | Case 2 should either implement the intended objective or rename it accurately |

## Where Case 1 diverges from the buyer guide

The buyer guide describes a synthetic or financial DPPA buyer stack where total buyer payment is:

```text
payment to EVN PC + CfD payment to/from generator
```

with the matched-volume approximation:

```text
all-in matched kWh ~= strike + DPPA charge + small basis/loss adjustment
```

at `research/2026-04-07-vietnam-dppa-buyer-guide.md:97` and `research/2026-04-07-vietnam-dppa-buyer-guide.md:128`.

Case 1 does not model that stack. Instead it does all of the following:

- uses a direct `private_wire` strike basis, not a financial CfD, at `src/python/reopt_pysam_vn/integration/dppa_case_1.py:119`
- feeds PySAM a plain PPA price plus utility buy rate, with export sell rate forced to zero, at `src/python/reopt_pysam_vn/integration/bridge.py:343` and `src/python/reopt_pysam_vn/integration/bridge.py:353`
- omits the DPPA adder, KPP, CFMP/FMP-linked EVN payment, and contract-quantity settlement rules described in the buyer guide

So the key conclusion is:

`DPPA Case 1 is a private-wire tariff-ceiling screen, not a synthetic DPPA buyer-cost model.`

## Specific revisions needed before DPPA Case 2

### 1. Decide the contract structure first

Recommended default: make `DPPA Case 2` a synthetic or grid-connected DPPA if the goal is to follow the buyer-guide research.

Why:

- the buyer guide is explicitly about the synthetic or financial DPPA mechanism at `research/2026-04-07-vietnam-dppa-buyer-guide.md:3`
- Case 1 already covers the private-wire interpretation

If you keep Case 2 as private wire, then the buyer guide should be treated as background only, not as the governing commercial basis.

### 2. Add a buyer-side settlement ledger

Case 2 should add an hourly post-processing layer that computes at least:

- matched-volume EVN market-linked payment
- DPPA adder (`CDPPAdv` + `CCL`, or separate if invoiced that way)
- KPP or loss-coefficient adjustment by voltage level
- CfD payment to or from generator
- shortfall energy billed at EVN retail tariff
- blended buyer all-in cost per consumed kWh

This is the biggest missing piece relative to `research/2026-04-07-vietnam-dppa-buyer-guide.md:101`.

### 3. Define the settlement quantity explicitly

The buyer guide flags settlement quantity as the first negotiation issue at `research/2026-04-07-vietnam-dppa-buyer-guide.md:265`.

Case 2 should not proceed without an explicit rule such as:

- `min(load, allocated_generation)` for a customer-first screen, or
- `generated volume` if you want to stress the buyer's over-contract risk

Recommended default for first pass: use `min(load, allocated_generation)` for the matched block, then report any excess-generation exposure separately.

### 4. Model excess-generation risk explicitly

The buyer guide is clear that excess contracted generation can materially worsen buyer economics at `research/2026-04-07-vietnam-dppa-buyer-guide.md:215` and `research/2026-04-07-vietnam-dppa-buyer-guide.md:268`.

Case 1 avoids this risk by design through a near-zero-export private-wire setup. Case 2 should instead report:

- matched MWh
- shortfall MWh
- excess generation MWh
- CfD paid on excess, if applicable

### 5. Fix the battery requirement if the case must include storage

Case 1 locked battery duration to 2 hours but still solved to `0 MW / 0 MWh` storage at `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_reopt-summary.json:10`.

That happened because duration was constrained, but a nonzero build was not required.

For Case 2, if storage is mandatory, add one of these:

- `ElectricStorage.min_kw > 0` and matching `min_kwh`, or
- an outer loop that rejects zero-storage REopt solves and reruns with a bounded storage floor

Without that change, another "2-hour BESS" case can still optimize to no battery.

### 6. Resolve the REopt objective mismatch

The plan records the user answer as minimum project capex at `plans/active/dppa_case_1_plan.md:193`, but the scenario metadata still says `minimum_lifecycle_cost_with_no_export_intent` at `scenarios/case_studies/ninhsim/2026-04-09_ninhsim_dppa-case-1.json:26411`, and the builder does not appear to introduce a real capex-minimization mechanism.

For Case 2, choose one:

- actually implement a capex-first solve strategy, or
- rename the objective everywhere to lifecycle-cost minimization so the artifacts are truthful

I recommend the second option unless there is a strong commercial reason to optimize capex directly.

### 7. Do not use the private-wire ceiling as the actual strike by default

The Decree 57 file says those values are maximum tariffs and parties negotiate within them at `data/vietnam/vn_export_rules_decree57.json:23`.

Case 1 effectively treats the ceiling lookup as the year-one strike input. For Case 2, use one of these instead:

- negotiated strike as an explicit scenario input
- strike sweep around an assumed negotiation band
- buyer-ceiling versus developer-floor comparison artifact

If Case 2 is synthetic DPPA, a separate strike discovery path is even more important because the buyer all-in price is not just the strike itself.

### 8. Reconcile the finance-path overrides with canonical Vietnam defaults

Case 1 uses `20` years and `5%` electricity escalation at `scenarios/case_studies/ninhsim/2026-04-09_ninhsim_dppa-case-1.json:8844`, while the repo's `2025` standard defaults are `25` years and `4%` escalation at `data/vietnam/vn_financial_defaults_2025.json:13`.

That may be intentional, but it is currently a silent case-study override.

For Case 2, either:

- adopt the canonical `2025` defaults, or
- keep the override but state it explicitly in the scenario metadata and report assumptions section

### 9. Upgrade the existing grid-connected settlement helper before reusing it

The current `grid_connected` path in `scripts/python/reopt/dppa_settlement.py` computes developer settlement as `max(0, strike - FMP)` at `scripts/python/reopt/dppa_settlement.py:149`.

That is not yet a full bilateral buyer-side CfD ledger, because the buyer guide also allows the generator to pay the buyer when strike is below FMP at `research/2026-04-07-vietnam-dppa-buyer-guide.md:54`.

So if Case 2 uses synthetic DPPA logic, do not reuse that helper unchanged.

## Recommended Case 2 implementation path

### Option A - Recommended: synthetic DPPA buyer-cost case

Build Case 2 as a new synthetic or grid-connected workflow with:

1. REopt or PySAM physical sizing pass
2. hourly settlement post-processing for buyer all-in cost
3. explicit settlement-quantity rule
4. explicit excess-generation exposure reporting
5. separate buyer and developer views in the final artifact

This is the cleanest way to make the buyer-guide research operational.

### Option B - Simpler: keep private-wire but make it a better private-wire case

If you want Case 2 to stay private wire, then revise only these:

1. force nonzero BESS if storage is required
2. replace ceiling-as-strike with negotiated-strike input or strike sweep
3. fix the objective labeling mismatch
4. document the finance overrides explicitly

This would improve the current Case 1 logic, but it would still not be a buyer-guide synthetic DPPA model.

## Bottom line

You probably need a real branch in the workflow now:

- `Case 1` = private-wire tariff-ceiling screen
- `Case 2` = synthetic-DPPA buyer-cost model

If that is the intended split, the most important changes before running Case 2 are:

1. switch the commercial structure away from `private_wire`
2. add the buyer-side settlement ledger
3. define settlement quantity and excess-generation treatment
4. force nonzero storage if BESS is part of the case definition
5. stop treating the tariff ceiling as the actual negotiated strike
