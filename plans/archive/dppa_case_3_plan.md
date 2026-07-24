# DPPA Case 3 - Saigon18 Real-Project Bridge Plan

> Status: Revised for implementation (user-reviewed)
> Canonical plan path: `plans/active/dppa_case_3_plan.md`
> Case-study basis: `saigon18`
> Scope: Build a new `DPPA Case 3` workflow that keeps the strong synthetic-DPPA settlement architecture from Case 2, but replaces the `ninhsim` + transferred-market mismatch with one site-consistent Vietnam basis, enforces a real battery buildout, adds controller-vs-optimizer comparison, and aligns the tariff / strike setup more closely with the real-project notes.

### User decisions applied (2026-04-20)

1. **Physical lanes:** Lane B only (bounded optimization with storage floor). No fixed-size Lane A.
2. **Strike anchor:** Keep 5% below EVN weighted tariff as base, with sensitivity sweep.
3. **Tariff branches:** Two branches (22kV two-part + legacy TOU) with explicit side-by-side comparison in reports.

## 1. Objective

Create a `DPPA Case 3` workflow that does all of the following:

1. Uses the `saigon18` extracted `8760` load shape as the base Vietnam load profile.
2. Uses the same `saigon18` hourly `CFMP` / `FMP` source as the market reference, so load and market are no longer pulled from different sites.
3. Preserves the Case 2 synthetic-DPPA buyer settlement ledger instead of falling back to Case 1 private-wire shortcuts.
4. Makes `BESS` mandatory via hard lower bounds so the workflow cannot silently collapse to PV-only again.
5. Runs a single bounded-optimization lane with storage floor enforced.
6. Adds a controller-aligned dispatch sensitivity so the optimizer-vs-real-controller gap is visible.
7. Adds a `22 kV` two-part EVN tariff branch alongside the legacy TOU branch, with side-by-side delta reporting.
8. Anchors the strike path at `5% below EVN weighted tariff`, then sweeps sensitivity around that anchor.
9. Keeps buyer, developer, and contract-risk outputs separate.
10. Produces machine-readable artifacts plus one final combined decision artifact and report.

## 2. Why Case 3 exists

### Case 1 lessons to keep

- The REopt-to-PySAM comparison pattern was useful.
- Export checks were explicit and reviewable.
- Scenario and report naming stayed clean.

### Case 1 shortcomings to fix

- The workflow allowed REopt to choose zero storage, so the intended PV+BESS question was never actually answered.
- The commercial basis stayed private-wire and ceiling-tariff-driven.
- The stated solve intent and the actual optimization basis drifted apart.
- The fixed-controller-vs-optimizer gap was recognized but not promoted into a first-class workflow branch.

### Case 2 lessons to keep

- The synthetic-DPPA settlement architecture is the right direction.
- Buyer settlement, buyer benchmark, developer screening, and combined-decision artifacts should be reused.
- Contract-risk sensitivities were explicit and auditable.

### Case 2 shortcomings to fix

- The physical case still optimized to PV-only.
- The load basis and market basis were mismatched.
- The strike sweep started from assumptions that were still too far from the real-project notes.
- The workflow widened sensitivities around a rejected base case instead of changing foundational assumptions.
- The case was still too optimization-led and not project-led.

## 3. Chosen load profile: `saigon18`

### Recommended default

Use the extracted `saigon18` `8760` load shape as the Case 3 base load profile, not `ninhsim` and not `north_thuan`.

### Why this is the best next load basis

- `saigon18` is the only repo-local Vietnam workstream already tied to:
  - extracted hourly load,
  - extracted hourly market data,
  - real-project-style tariff assumptions,
  - and existing REopt-vs-project comparison scaffolding.
- It lets Case 3 use a site-consistent load + market + tariff workstream.
- It shortens the path to the real-project-data branch because the repo already has comparison, settlement, and finance support around `saigon18`.

### Why not `north_thuan`

- `north_thuan` ranked best for pure physical absorption, but that ranking explicitly ignored tariff, settlement, and contract risk.
- `north_thuan` is still a synthetic industrial profile built for staff-case validation, not the strongest realism-first bridge.

### Important caveat

- `saigon18` is not the strongest pure behind-the-meter absorption profile.
- Its daytime minimum load collapses to zero in some hours, so excess-risk and dispatch/controller assumptions must stay explicit.
- Case 3 should therefore treat `saigon18` as a realism-first bridge case, not as a guaranteed easy commercial pass.

### Scaling hook

If actual project annual demand, monthly EVN bills, or seasonal peak data become available later, keep the `saigon18` hourly shape but add a `scale_to_annual_kwh` or `scale_to_monthly_bill_shape` hook so the same Case 3 architecture can be retuned without redesign.

## 4. Recommended Case 3 definition

### Contract structure

- Keep `synthetic_financial_dppa` as the canonical commercial structure.
- Do not reopen private-wire logic as the main Case 3 path.
- Private-wire can remain a reference branch only if needed for comparison.

### Site and data basis

- Base load profile: `saigon18` extracted `8760`.
- Base market series: `saigon18` extracted hourly `CFMP` / `FMP`.
- Base region: south Vietnam.
- Base customer type: industrial.
- Base voltage treatment: `22 kV` industrial customer branch.

### Physical scope

#### In scope by default

- `PV`
- `ElectricStorage`
- residual EVN imports
- buyer settlement post-processing
- developer-side PySAM validation

#### Out of scope by default

- `Wind`
- diesel or thermal generation
- resilience constraints
- merchant-export-optimizing objective
- broad multi-site portfolio comparison

### Battery rule (user decision: Lane B only)

Case 3 should not permit another silent PV-only outcome. Run a single bounded-optimization lane:

1. **Bounded optimization lane**
   - allow REopt to adjust the base concept within a narrow envelope
   - starting concept (real-project reference):
     - `PV = 3.2 MWp`
     - `BESS = 1.0 MW / 2.2 MWh`
   - optimization bounds:
     - PV: `0.75x` to `1.50x` base
     - BESS power: `0.75x` to `1.50x` base
     - BESS energy: tied to the chosen duration band
   - hard rule: `min_kw > 0` and `min_kwh > 0`

No fixed-size Lane A is run. The bounded optimization lane is the sole physical lane.

### Dispatch rule

The real-project notes already say the current project uses controller-style charge/discharge windows while REopt optimizes freely.

#### Recommended default

Make this explicit in Case 3 instead of leaving it as a narrative caveat:

- **Base lane:** REopt free dispatch
- **Sensitivity lane:** controller-aligned dispatch approximation
  - recommended first proxy:
    - charge during midday solar window
    - discharge during evening / peak window
- publish the value gap between:
  - optimized dispatch
  - controller-style dispatch

This is required so Case 3 shortens the gap with real operations instead of hiding it.

## 5. Tariff and strike treatment

### Tariff basis

The real-project notes reference a `22 kV` two-part EVN tariff, while the earlier `saigon18` workstream also carries a one-component TOU basis.

#### Recommended default (user decision: two branches with side-by-side delta reporting)

Run two tariff branches explicitly:

1. **Primary realism branch:** `22 kV` two-part EVN tariff
   - energy charges inside REopt where faithfully representable
   - demand / capacity charge inside REopt if the current tariff structure maps cleanly
   - otherwise add a post-processing demand-charge reconciliation layer

2. **Reference branch:** legacy one-component EVN TOU
   - keep only as a cross-check against earlier repo artifacts

3. **Reporting:** Each report section shows both tariff branches in a side-by-side comparison table with delta columns so the cost impact of the two-part vs one-component choice is explicit and auditable.

### Strike basis

Case 2 anchored around `5% below EVN weighted tariff`, but the real-project notes point to `15% discount`.

#### Recommended default (user decision: keep 5% with sensitivity)

- Base strike path: `EVN tariff x 0.95` (5% below weighted EVN)
- Escalation: explicit and visible in artifact metadata
- Sensitivity band around the base strike:
  - `0% below EVN` (parity)
  - `5% below EVN` (base)
  - `10% below EVN`
  - `15% below EVN`
  - `20% below EVN`

Do not reuse the private-wire tariff ceiling as the synthetic-DPPA strike anchor.

## 6. Settlement rules to preserve from Case 2

### Keep these as first-class surfaces

- settlement quantity rule
- excess-generation treatment
- DPPA adder
- KPP / loss-factor assumption
- buyer benchmark comparison
- developer-side screen
- combined decision artifact

### Recommended defaults

- **Settlement quantity:** `min(load, contracted_generation)`
- **Excess treatment base case:** excluded from buyer settlement
- **Excess stress case:** `cfd_on_excess_generation`
- **DPPA adder / KPP:** explicit parameters, never hidden constants
- **Buyer benchmark:** EVN bill under the same tariff branch as the case being tested

### New Case 3 addition

Add a `site_consistency_block` to every machine-readable artifact:

- `load_source_case`
- `market_source_case`
- `tariff_source_case`
- `same_site_basis = true/false`
- `same_project_workstream = true/false`

Case 3 should fail review if the base branch is still site-inconsistent.

## 7. Recommended modeling philosophy

### REopt role

- Provide the first-pass physical energy-flow solution.
- Solve the bounded-optimization lane under clearly labeled objectives.
- Never be allowed to remove storage from the case silently.

### Settlement role

- Reuse the Case 2 buyer settlement architecture.
- Consume solved hourly outputs from REopt.
- Keep buyer economics fully separate from developer economics.
- Add two-part tariff and controller-gap handling without blending them into one shortcut number.

### PySAM role

- Validate the candidate plant and finance path after the settlement logic is frozen.
- Preserve separate buyer and developer outputs.
- Add DSCR, NPV, and IRR as explicit screening metrics.
- Compare:
  - REopt vs PySAM
  - optimized dispatch vs controller-aligned dispatch
  - 22kV two-part tariff vs legacy TOU tariff (side-by-side delta)

## 8. Proposed implementation phases

## Phase A - Freeze Case 3 definition and gap register

### Tasks

1. Create the Case 3 assumptions register.
2. Record the exact shortcomings inherited from Case 1 and Case 2.
3. Freeze the `saigon18` data basis as the base load / market workstream.
4. Freeze the base tariff branch and strike anchor.
5. Freeze the fixed-lane and bounded-optimization-lane definitions.
6. Record which parts are realism-first vs convenience-first.

### Deliverables

- Case 3 definition artifact
- assumptions register
- gap register linking each known shortcoming to one Case 3 mitigation

## Phase B - Build the canonical Case 3 data package

### Tasks

1. Add a loader that pulls:
   - `saigon18` hourly load
   - `saigon18` hourly `CFMP` / `FMP`
   - tariff inputs for one-component and two-part branches
2. Add the `scale_to_annual_kwh` hook for later real-project retuning.
3. Add artifact metadata proving whether the case is site-consistent.
4. Add failing-then-passing regression tests for:
   - same-site basis tagging
   - strike-path metadata
   - tariff-branch metadata
   - scaling-hook behavior

### Deliverables

- canonical Case 3 input-preparation script
- Case 3 input package artifact
- Phase B regression tests

## Phase C - Build the bounded-optimization physical lane

### Tasks

1. Build a new Case 3 scenario JSON under `scenarios/case_studies/saigon18/`.
2. Encode the bounded-optimization lane with hard storage floor (`min_kw > 0`, `min_kwh > 0`).
3. Keep wind out of scope.
4. Run no-solve validation first.
5. Solve and publish the physical summary.
6. Add regression coverage that fails if storage becomes zero.

### Deliverables

- bounded-optimization scenario JSON
- REopt results JSON
- physical-summary artifact
- storage-floor regression test

## Phase D - Implement the Case 3 buyer settlement and benchmark

### Tasks

1. Reuse the Case 2 settlement engine as the base.
2. Replace any `ninhsim`-specific assumptions with Case 3 source metadata.
3. Add tariff-branch-aware EVN benchmark logic.
4. Add explicit strike-path handling using the `5% below EVN` base anchor.
5. Publish:
   - buyer settlement
   - buyer benchmark
   - contract-risk summary
6. Add failing-then-passing tests for:
   - same-site load + market basis
   - two-part tariff benchmark math
   - strike anchor metadata
   - excess-treatment branch math

### Deliverables

- buyer-settlement artifact
- buyer-benchmark artifact
- contract-risk artifact
- settlement regression tests

## Phase E - Add controller-vs-optimizer realism screens

### Tasks

1. Define a controller-style dispatch proxy that approximates the real project's intended charging/discharging windows.
2. Re-run the relevant settlement outputs under the controller proxy.
3. Compare optimized vs controller-style:
   - matched MWh
   - excess MWh
   - buyer blended cost
   - developer revenue / IRR / DSCR
4. Publish the `controller_gap` artifact.
5. If the gap is large, make that a first-class decision signal rather than a footnote.

### Deliverables

- controller-gap artifact
- optimizer-vs-controller comparison artifact
- controller-gap regression tests

## Phase F - Add PySAM developer validation

### Tasks

1. Map the bounded-optimization lane into the existing PySAM finance path.
2. Preserve separate buyer and developer outputs.
3. Use the same strike / tariff / escalation assumptions already frozen in Case 3.
4. Publish:
   - PySAM results
   - REopt-vs-PySAM comparison
   - developer screening
5. Include DSCR, NPV, IRR, and payback in the screening artifact.
6. Add regression coverage for the bounded-optimization lane.

### Deliverables

- PySAM results artifact
- REopt-vs-PySAM comparison artifact
- developer screening artifact
- PySAM regression tests

## Phase G - Publish the final decision package

### Tasks

1. Build a combined decision artifact from the bounded-optimization lane, settlement outputs, controller-gap outputs, and PySAM outputs.
2. Make the final recommendation explicit:
   - `advance`
   - `revise`
   - `reject`
   - `escalate_for_actual_8760`
3. Record exactly which assumption changes would justify reopening the case.
4. Publish one final HTML or markdown report.
5. Update `activeContext.md` only after all validations pass.

### Deliverables

- combined-decision artifact
- final Case 3 report
- final-summary artifact
- implementation notes for next-step handoff

## 9. Testing and validation strategy

### Test-first rule

Every phase should start with failing coverage before implementation.

### Recommended test files

- `tests/python/integration/test_dppa_case_3_phase_ab.py`
- `tests/python/integration/test_dppa_case_3_phase_c.py`
- `tests/python/integration/test_dppa_case_3_phase_d.py`
- `tests/python/integration/test_dppa_case_3_phase_e.py`
- `tests/python/integration/test_dppa_case_3_phase_f.py`

### Validation commands

#### Phase A/B
```powershell
.venv\Scripts\python.exe -m pytest tests/python/integration/test_dppa_case_3_phase_ab.py -q
.venv\Scripts\python.exe scripts/python/integration/prepare_saigon18_dppa_case_3_phase_ab.py
```

#### Phase C
```powershell
julia --project --compile=min scripts/julia/run_vietnam_scenario.jl --scenario scenarios/case_studies/saigon18/<date>_saigon18_dppa-case-3_bounded-opt.json --no-solve
julia --project --compile=min scripts/julia/run_vietnam_scenario.jl --scenario scenarios/case_studies/saigon18/<date>_saigon18_dppa-case-3_bounded-opt.json
.venv\Scripts\python.exe -m pytest tests/python/integration/test_dppa_case_3_phase_c.py -q
```

#### Phase D/E/F
```powershell
.venv\Scripts\python.exe -m pytest tests/python/integration/test_dppa_case_3_phase_d.py tests/python/integration/test_dppa_case_3_phase_e.py tests/python/integration/test_dppa_case_3_phase_f.py -q
.venv\Scripts\python.exe scripts/python/integration/run_saigon18_dppa_case_3.py
.venv\Scripts\python.exe scripts/python/integration/generate_saigon18_dppa_case_3_report.py
```

## 10. Recommended outputs

- `plans/active/dppa_case_3_plan.md`
- `scenarios/case_studies/saigon18/<date>_saigon18_dppa-case-3_bounded-opt.json`
- `artifacts/results/saigon18/<date>_saigon18_dppa-case-3_bounded-opt_reopt-results.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_input-package.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_physical-summary-bounded-opt.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_buyer-settlement.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_buyer-benchmark.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_contract-risk.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_controller-gap.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_pysam-results.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_reopt-pysam-comparison.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_developer-screening.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_combined-decision.json`
- `artifacts/reports/saigon18/<date>_saigon18_dppa-case-3_final-summary.json`
- `reports/<date>-dppa-case-3-final.html`

## 11. Decision rules

### Buyer pass

At least one tested Case 3 candidate should beat the EVN benchmark on blended buyer cost under the primary tariff branch.

### Developer pass

At least one tested candidate should clear the chosen IRR / NPV / DSCR thresholds.

### Realism pass

The workflow should quantify, not hide, the gap between optimized dispatch and controller-style dispatch.

### Data-basis pass

The base case should keep load, market, and tariff basis in the same declared workstream.

### Case recommendation classes

- `advance`
- `revise_assumptions`
- `reject_current_case`
- `escalate_for_actual_project_8760`

## 12. Explicit anti-regression guardrails

Case 3 should fail review if any of the following reappear:

1. PV-only outcome in a case that is supposed to answer a BESS question.
2. Transferred market series without explicit site-consistency labeling.
3. Private-wire ceiling reused as a synthetic-DPPA strike shortcut.
4. Weighted-tariff shortcut used where a two-part tariff branch was promised.
5. Buyer and developer economics blended into one headline number.
6. Optimizer-vs-controller gap pushed back into narrative text instead of artifact outputs.
7. New sensitivity branches added before the fixed base case is trustworthy.

## 13. Recommended default path

- Use `saigon18` as the Case 3 base load and market profile.
- Keep Case 3 synthetic-DPPA, not private-wire.
- Run a single bounded-optimization lane with hard storage floor (`min_kw > 0`, `min_kwh > 0`).
- Use `5% below EVN` as the strike anchor, sweep 0% to 20%.
- Run two tariff branches (22kV two-part + legacy TOU) with side-by-side delta reporting.
- Add a controller-style dispatch sensitivity.
- Reuse the Case 2 settlement engine and combined-decision architecture.
- Treat Case 3 as a realism-first bridge case whose main job is to narrow the gap to real-project implementation, not to maximize the chance of an easy commercial pass.
