---
title: "Sprint 3 — Generalize onsite + offsite/DPPA pipelines and make them first-class"
date: "2026-06-12"
status: "draft"
request: "Plan Sprint 3 from the repo-trim gap analysis: GAP-01 generalize onsite + offsite/DPPA pipelines, GAP-06 make onsite/offsite first-class in docs/structure."
plan_type: "multi-phase"
research_inputs:
  - "reports/2026-06-12-reopt-pysam-vietnam-repo-trim-gap-analysis.md"
  - "research/2026-04-07-vietnam-dppa-buyer-guide.md"
  - "research/2026-04-25_vietnam-tou-rooftop-ppa.md"
---

# Plan: Sprint 3 — Generalized Onsite + Offsite/DPPA Analysis Pipelines

## Objective
Turn the repo's stated key function into actual, reusable APIs: a single `onsite` pipeline (behind-the-meter REopt PV+BESS optimization vs EVN TOU) and a single `offsite_dppa` pipeline (PySAM developer finance + generic settlement + strike search), each driven by a project/deal config — so analyzing a *future* Vietnam project means writing a config, not cloning a 200–850-line case module. This is the only sprint that touches tested logic; run it after Sprints 1–2 de-bloat.

## Context Snapshot
- **Current state:** Onsite and offsite logic exists only as bespoke per-deal modules: `src/python/reopt_pysam_vn/integration/{dppa_case_1,dppa_case_2,dppa_case_3,dppa_samsung_ttc,ninhsim_solar_storage_60pct}.py`, each with a matching `scripts/python/integration/analyze_*` and `tests/python/integration/test_dppa_*`. The generic primitives they orchestrate already exist: `integration/{settlement,strike_search,bridge,assumptions,matching,procurement,project_catalog}.py` (e.g. `settlement.py` is already exercised generically by `test_settlement_generic.py` / `test_settlement_presets.py`). Project configs + schema exist: `data/projects/*.json`, `data/schemas/extracted_inputs.schema.json`.
- **Desired state:** Two generalized entry points — `reopt_pysam_vn/analysis/onsite.py` and `reopt_pysam_vn/analysis/offsite_dppa.py` — that take a project/deal config and run the full chain; the five case modules become thin configs + golden-output regression fixtures; docs lead with the onsite-vs-offsite decision.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/integration/` (all modules), `reopt_pysam_vn/reopt/{preprocess,regime_runner}.py`, `reopt_pysam_vn/pysam/{pvwatts_battery,single_owner,cashflow,ppa}.py`, `scenarios/case_studies/`, `data/projects/`, `tests/python/integration/`, `docs/`.
- **Out of scope:** De-bloat (Sprints 1–2); changing the Julia solve path or Vietnam policy data semantics; PySAM env packaging (GAP-08 backlog).

## Research Inputs
- `reports/2026-06-12-reopt-pysam-vietnam-repo-trim-gap-analysis.md` — GAP-01/06; names the generic primitives to reuse and the regression-parity risk (migrate one case as a gate before retiring others).
- `research/2026-04-07-vietnam-dppa-buyer-guide.md` — buyer-side DPPA settlement framing for the offsite pipeline's contract/settlement semantics.
- `research/2026-04-25_vietnam-tou-rooftop-ppa.md` — onsite (rooftop/BTM) TOU + PPA-discount framing for the onsite pipeline.

## Assumptions and Constraints
- **ASM-001:** The five case modules are mostly orchestration glue over `settlement.py`, `strike_search.py`, `bridge.py`, `single_owner.py`, `pvwatts_battery.py` — generalization is extraction + parameterization, not new modeling.
- **ASM-002:** A project/deal config schema can be derived from `data/schemas/extracted_inputs.schema.json` + the existing `scenarios/case_studies/*/*.json` shapes.
- **CON-001:** Numeric outputs of a migrated case must match its existing golden JSON within tolerance (regression gate) before the bespoke module is retired.
- **CON-002:** Follow repo TDD law (CLAUDE.md): write failing tests first for each new pipeline API.
- **DEC-001:** PySAM-dependent paths must keep skipping gracefully when `nrel-pysam` is absent (pattern already in `tests/python/pysam/test_pysam_import.py`).

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Define deal-config schema + extract common contract | None | `reopt_pysam_vn/analysis/__init__.py`, deal-config schema, shared types |
| PHASE-02 | Generalized `onsite` pipeline (red→green) | PHASE-01 | `analysis/onsite.py` + tests |
| PHASE-03 | Generalized `offsite_dppa` pipeline (red→green) | PHASE-01 | `analysis/offsite_dppa.py` + tests |
| PHASE-04 | Migrate Samsung-TTC as regression proof | PHASE-02, PHASE-03 | Samsung-TTC config + parity test vs golden JSON |
| PHASE-05 | Deprecate case modules + make modes first-class in docs | PHASE-04 | Retired case modules, `docs/onsite_vs_offsite.md`, README restructure |

## Detailed Phases

### PHASE-01 - Deal-config schema + shared analysis contract
**Goal**
Establish one config shape and a shared result contract both pipelines consume/produce.

**Tasks**
- [ ] TASK-01-01: Create package `src/python/reopt_pysam_vn/analysis/` with `__init__.py`.
- [ ] TASK-01-02: Derive a `deal_config` schema (`data/schemas/deal_config.schema.json`) from `data/schemas/extracted_inputs.schema.json` + the union of fields used across `dppa_case_1/2/3` and `dppa_samsung_ttc` (site, load, tech sizing, tariff/regime, contract: strike/volume/tenor, finance: discount/CIT/PPA-discount).
- [ ] TASK-01-03: Define shared dataclasses/result types (`analysis/types.py`): `OnsiteResult`, `OffsiteDppaResult`, `CombinedDecision` — mirror keys already emitted in `artifacts/reports/.../combined-decision.json`.
- [ ] TASK-01-04: Inventory which primitives each case module calls (grep `dppa_case_*`, `dppa_samsung_ttc`, `ninhsim_solar_storage_60pct`) and record the reuse map in the plan.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/analysis/{__init__,types}.py` (new), `data/schemas/deal_config.schema.json` (new), the five `integration/dppa_*`/`ninhsim_*` modules (read for field/primitive inventory).

**Dependencies**
- None.

**Exit Criteria**
- [ ] `deal_config.schema.json` validates all existing `scenarios/case_studies/*/*dppa*.json` (or documents required field additions).
- [ ] Reuse map enumerates every primitive each case module depends on.

**Phase Risks**
- **RISK-01-01:** Case modules diverge more than expected (per-deal special cases). Mitigation: capture divergences as explicit config flags rather than forking the pipeline.

### PHASE-02 - Generalized onsite pipeline
**Goal**
One function that runs BTM REopt PV+BESS sizing/dispatch for any deal config.

**Tasks**
- [ ] TASK-02-01: Write failing tests `tests/python/analysis/test_onsite.py` asserting an onsite run from a config reproduces a known case's physical summary (reuse a `ninhsim_solar_storage_60pct` fixture).
- [ ] TASK-02-02: Implement `analysis/onsite.py::run_onsite(deal_config) -> OnsiteResult`, composing `reopt/preprocess.py` (Vietnam defaults) + `reopt/regime_runner.py` + `integration/bridge.py`.
- [ ] TASK-02-03: Make tests green; ensure no-solver smoke path works (validate-only, like `run_vietnam_scenario.jl --no-solve`).

**Files / Surfaces**
- `analysis/onsite.py` (new), `reopt/preprocess.py`, `reopt/regime_runner.py`, `integration/bridge.py`, `tests/python/analysis/test_onsite.py` (new).

**Dependencies**
- PHASE-01.

**Exit Criteria**
- [ ] `run_onsite()` reproduces the reference case's onsite metrics within tolerance.
- [ ] New tests green; existing onsite tests untouched and green.

**Phase Risks**
- **RISK-02-01:** Solver runtime makes tests slow. Mitigation: default tests to validate/no-solve; gate full-solve parity behind the Layer-4 marker.

### PHASE-03 - Generalized offsite/DPPA pipeline
**Goal**
One function that runs developer finance + settlement + strike search for any DPPA deal config.

**Tasks**
- [ ] TASK-03-01: Write failing tests `tests/python/analysis/test_offsite_dppa.py` asserting an offsite run reproduces a known case's buyer-settlement + strike-sensitivity (reuse Samsung-TTC or dppa_case_2 fixtures).
- [ ] TASK-03-02: Implement `analysis/offsite_dppa.py::run_offsite_dppa(deal_config) -> OffsiteDppaResult`, composing `pysam/{pvwatts_battery,single_owner,cashflow,ppa}.py` + `integration/{settlement,strike_search,assumptions}.py`.
- [ ] TASK-03-03: Preserve graceful PySAM skip when `nrel-pysam` is unavailable.
- [ ] TASK-03-04: Make tests green.

**Files / Surfaces**
- `analysis/offsite_dppa.py` (new), `pysam/*.py`, `integration/{settlement,strike_search,assumptions}.py`, `tests/python/analysis/test_offsite_dppa.py` (new).

**Dependencies**
- PHASE-01 (independent of PHASE-02; can run in parallel).

**Exit Criteria**
- [ ] `run_offsite_dppa()` reproduces the reference case's settlement + strike outputs within tolerance.
- [ ] PySAM-absent path skips cleanly.

**Phase Risks**
- **RISK-03-01:** Settlement variants across cases (physical vs virtual, FMP overlay) don't unify. Mitigation: drive variant via `deal_config.settlement.type`; `settlement.py` already supports presets per `test_settlement_presets.py`.

### PHASE-04 - Migrate Samsung-TTC as regression proof
**Goal**
Prove the generalized pipelines reproduce a full real case before retiring any bespoke module.

**Tasks**
- [ ] TASK-04-01: Express the Samsung-TTC deal as a `deal_config` JSON under `scenarios/case_studies/samsung_ttc/`.
- [ ] TASK-04-02: Add `tests/python/analysis/test_samsung_ttc_parity.py` comparing `run_onsite`+`run_offsite_dppa` outputs to the golden `artifacts/reports/samsung_ttc/2026-06-04_samsung-ttc_combined-decision.json` (or the `examples/` copy from Sprint 1) within tolerance.
- [ ] TASK-04-03: Resolve any parity gaps by extending config flags (not by forking the pipeline).

**Files / Surfaces**
- `scenarios/case_studies/samsung_ttc/*deal_config*.json` (new), `tests/python/analysis/test_samsung_ttc_parity.py` (new), the Samsung-TTC golden JSON.

**Dependencies**
- PHASE-02, PHASE-03.

**Exit Criteria**
- [ ] Samsung-TTC parity test green within tolerance.

**Phase Risks**
- **RISK-04-01:** Golden JSON was untracked in Sprint 1. Mitigation: Sprint 1 preserves it under `examples/`; reference that path.

### PHASE-05 - Deprecate case modules + make modes first-class
**Goal**
Retire the bespoke modules and lead the repo with the onsite/offsite distinction.

**Tasks**
- [ ] TASK-05-01: Once parity holds, convert `dppa_case_1/2/3`, `dppa_samsung_ttc`, `ninhsim_solar_storage_60pct` into thin config + golden fixtures, or remove them and repoint their `analyze_*` scripts + tests at the generalized pipelines.
- [ ] TASK-05-02: Write `docs/onsite_vs_offsite.md` — when to use onsite (BTM optimization) vs offsite/DPPA (settlement/finance), with config examples.
- [ ] TASK-05-03: Restructure `README.md` to lead with the two analysis modes and the `analysis/` entry points instead of the generic preprocessing tool.
- [ ] TASK-05-04: Update `AGENTS.md`/`activeContext.md` to reflect the new structure.

**Files / Surfaces**
- `integration/dppa_case_*`, `integration/dppa_samsung_ttc.py`, `integration/ninhsim_solar_storage_60pct.py`, `scripts/python/integration/analyze_*`, `tests/python/integration/test_dppa_*`, `docs/onsite_vs_offsite.md` (new), `README.md`, `AGENTS.md`.

**Dependencies**
- PHASE-04 (never retire a module before its parity gate passes).

**Exit Criteria**
- [ ] Full suite green after case modules are retired/repointed.
- [ ] README + `docs/onsite_vs_offsite.md` present the two modes as the primary navigation.

**Phase Risks**
- **RISK-05-01:** Retiring a module silently drops a behavior not covered by parity tests. Mitigation: retire incrementally, one case at a time, each behind its own parity test.

## Verification Strategy
- **TEST-001:** New `tests/python/analysis/test_onsite.py`, `test_offsite_dppa.py`, `test_samsung_ttc_parity.py` green (TDD red→green per phase).
- **TEST-002:** `.\tests\run_all_tests.ps1` full run green after each migration step.
- **MANUAL-001:** Run `run_onsite()` and `run_offsite_dppa()` from a fresh `deal_config` and confirm a `CombinedDecision` result without touching any `dppa_case_*` module.
- **OBS-001:** Compare migrated-case numeric outputs to golden JSON; record max diff (target: within documented tolerance, ideally 0).

## Risks and Alternatives
- **RISK-001:** Generalization subtly changes published case numbers, undermining prior client deliverables. Mitigation: parity gate per case before retirement; keep golden JSON as regression fixtures.
- **RISK-002:** Scope creep into re-modeling settlement/finance. Mitigation: this sprint is extraction + parameterization only; new modeling is a separate plan.
- **ALT-001:** Keep per-deal modules and only add a thin dispatcher. Rejected — leaves the duplication the gap analysis flagged; a future project still needs a new module.

## Grill Me
1. **Q-001:** What numeric tolerance counts as "parity" when migrating a case (exact match, or e.g. ≤0.5% on headline metrics)?
   - **Recommended default:** Exact match on deterministic post-processing (settlement/finance); ≤0.5% on any solver-dependent metric (REopt sizing may vary by solver build).
   - **Why this matters:** Sets the pass/fail bar for PHASE-04 and whether a case can be retired.
   - **If answered differently:** A stricter bar may require pinning solver versions; a looser bar speeds migration.
2. **Q-002:** Retire the bespoke case modules outright, or keep them as deprecated thin wrappers that call the new pipelines for one release?
   - **Recommended default:** Keep as deprecated thin wrappers for one cycle, then remove — preserves any external callers while signaling the new path.
   - **Why this matters:** Determines PHASE-05 scope (delete vs wrap).
   - **If answered differently:** Outright deletion is leaner but riskier for anything outside this repo.
3. **Q-003:** Should `onsite` and `offsite_dppa` be exposed as a CLI (`python -m reopt_pysam_vn.analysis ...`) in this sprint, or library functions only?
   - **Recommended default:** Library functions only this sprint; add a CLI in a follow-up once the API stabilizes.
   - **Why this matters:** A CLI adds argument-parsing + UX scope to PHASE-02/03.
   - **If answered differently:** Including a CLI adds one task per pipeline and a CLI smoke test.

## Suggested Next Step
Answer Grill Me Q-001 (parity tolerance) and Q-002 (retire vs wrap), then execute PHASE-01 → PHASE-05 with strict red→green TDD. Land each migrated case behind its own parity gate before retiring the bespoke module.
