---
title: "Sprint 3 — Generalize onsite + offsite/DPPA pipelines and make them first-class"
date: "2026-06-12"
status: "ready"
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
- **Desired state:** Two generalized entry points — `reopt_pysam_vn/analysis/onsite.py` and `reopt_pysam_vn/analysis/offsite_dppa.py` — that take a project/deal config and run the full chain, plus a `python -m reopt_pysam_vn.analysis` CLI (DEC-004); the five case modules become **deprecated thin wrappers** delegating to the pipeline (DEC-003); docs lead with the onsite-vs-offsite decision.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/integration/` (all modules), `reopt_pysam_vn/reopt/{preprocess,regime_runner}.py`, `reopt_pysam_vn/pysam/{pvwatts_battery,single_owner,cashflow,ppa}.py`, `scenarios/case_studies/`, `data/projects/`, `tests/python/integration/`, `docs/`.
- **Out of scope:** De-bloat (Sprints 1–2); changing the Julia solve path or Vietnam policy data semantics; PySAM env packaging (GAP-08 backlog).

## Research Inputs
- `reports/2026-06-12-reopt-pysam-vietnam-repo-trim-gap-analysis.md` — GAP-01/06; names the generic primitives to reuse and the regression-parity risk (migrate one case as a gate before retiring others).
- `research/2026-04-07-vietnam-dppa-buyer-guide.md` — buyer-side DPPA settlement framing for the offsite pipeline's contract/settlement semantics.
- `research/2026-04-25_vietnam-tou-rooftop-ppa.md` — onsite (rooftop/BTM) TOU + PPA-discount framing for the onsite pipeline.

## Assumptions and Constraints
- **ASM-001:** The five case modules are mostly orchestration glue over `settlement.py`, `strike_search.py`, `bridge.py`, `single_owner.py`, `pvwatts_battery.py` — generalization is extraction + parameterization, not new modeling.
- **ASM-002:** A project/deal config schema can be derived from `data/schemas/extracted_inputs.schema.json` + the existing `scenarios/case_studies/*/*.json` shapes.
- **CON-001:** Numeric outputs of a migrated case must match its existing golden JSON within the parity bar (DEC-002) before the bespoke module is wrapped.
- **CON-002:** Follow repo TDD law (CLAUDE.md): write failing tests first for each new pipeline API.
- **DEC-001:** PySAM-dependent paths must keep skipping gracefully when `nrel-pysam` is absent (pattern already in `tests/python/pysam/test_pysam_import.py`).

## Decisions Resolved (Grill Me answered 2026-06-14)
- **DEC-002 (Q-001 parity bar):** Exact match on deterministic post-processing (settlement/finance); ≤0.5% tolerance on solver-dependent REopt sizing metrics (HiGHS build variance). This is the per-case retirement gate in PHASE-04.
- **DEC-003 (Q-002 case modules):** Keep `dppa_case_1/2/3`, `dppa_samsung_ttc`, `ninhsim_solar_storage_60pct` as **deprecated thin wrappers** that delegate to the generalized pipeline for one release, then remove next cycle. Rationale reinforced by Sprint 2: tests import these modules, so wrappers avoid repointing test imports now.
- **DEC-004 (Q-003 CLI):** **Include a CLI this sprint** — `python -m reopt_pysam_vn.analysis` with `onsite` and `offsite_dppa` subcommands, built incrementally in PHASE-02/03 plus a CLI smoke test. (Deviation from the recommended library-only default; expands PHASE-02/03 scope by one task each.)

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Define deal-config schema + extract common contract | None | `reopt_pysam_vn/analysis/__init__.py`, deal-config schema, shared types |
| PHASE-02 | Generalized `onsite` pipeline + `onsite` CLI subcommand (red→green) | PHASE-01 | `analysis/onsite.py`, `analysis/__main__.py` (onsite), + tests |
| PHASE-03 | Generalized `offsite_dppa` pipeline + `offsite_dppa` CLI subcommand (red→green) | PHASE-01 | `analysis/offsite_dppa.py`, CLI offsite subcommand + CLI smoke test |
| PHASE-04 | Migrate Samsung-TTC as parity gate (DEC-002) | PHASE-02, PHASE-03 | Samsung-TTC config + parity test vs golden JSON |
| PHASE-05 | Wrap case modules as deprecated shims (DEC-003) + make modes first-class in docs | PHASE-04 | Deprecated wrappers, `docs/onsite_vs_offsite.md`, README restructure |

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
- [ ] TASK-02-04 (DEC-004 CLI): Create `analysis/__main__.py` with an argparse `onsite` subcommand (`python -m reopt_pysam_vn.analysis onsite --config <path> [--out <path>] [--no-solve]`) that loads a deal-config JSON, calls `run_onsite`, and writes/prints the result.

**Files / Surfaces**
- `analysis/onsite.py` (new), `analysis/__main__.py` (new, CLI), `reopt/preprocess.py`, `reopt/regime_runner.py`, `integration/bridge.py`, `tests/python/analysis/test_onsite.py` (new).

**Dependencies**
- PHASE-01.

**Exit Criteria**
- [ ] `run_onsite()` reproduces the reference case's onsite metrics within the parity bar (DEC-002).
- [ ] `python -m reopt_pysam_vn.analysis onsite --config <fixture> --no-solve` produces a result.
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
- [ ] TASK-03-05 (DEC-004 CLI): Add the `offsite_dppa` subcommand to `analysis/__main__.py` (`python -m reopt_pysam_vn.analysis offsite_dppa --config <path> [--out <path>]`) and a `tests/python/analysis/test_cli.py` smoke test driving both subcommands as a subprocess against a fixture config.

**Files / Surfaces**
- `analysis/offsite_dppa.py` (new), `analysis/__main__.py` (offsite subcommand), `pysam/*.py`, `integration/{settlement,strike_search,assumptions}.py`, `tests/python/analysis/test_offsite_dppa.py` (new), `tests/python/analysis/test_cli.py` (new).

**Dependencies**
- PHASE-01 (independent of PHASE-02 logic, but shares `analysis/__main__.py` — coordinate the CLI scaffold).

**Exit Criteria**
- [ ] `run_offsite_dppa()` reproduces the reference case's settlement + strike outputs within the parity bar (DEC-002).
- [ ] PySAM-absent path skips cleanly.
- [ ] CLI smoke test green: both `onsite` and `offsite_dppa` subcommands run from a fixture config.

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

### PHASE-05 - Wrap case modules as deprecated shims + make modes first-class
**Goal**
Convert the bespoke modules into deprecated wrappers (DEC-003) and lead the repo with the onsite/offsite distinction.

**Tasks**
- [ ] TASK-05-01: Once each case's parity gate (DEC-002) holds, rewrite `dppa_case_1/2/3`, `dppa_samsung_ttc`, `ninhsim_solar_storage_60pct` as **thin deprecated wrappers** that build the `deal_config` and delegate to `run_onsite`/`run_offsite_dppa`, emitting a `DeprecationWarning`. Keep their public function signatures so existing `analyze_*` scripts and `test_dppa_*` imports keep working unchanged (no test repointing this cycle).
- [ ] TASK-05-02: Write `docs/onsite_vs_offsite.md` — when to use onsite (BTM optimization) vs offsite/DPPA (settlement/finance), with config examples.
- [ ] TASK-05-03: Restructure `README.md` to lead with the two analysis modes and the `analysis/` entry points instead of the generic preprocessing tool.
- [ ] TASK-05-04: Update `AGENTS.md`/`activeContext.md` to reflect the new structure.

**Files / Surfaces**
- `integration/dppa_case_*`, `integration/dppa_samsung_ttc.py`, `integration/ninhsim_solar_storage_60pct.py`, `scripts/python/integration/analyze_*`, `tests/python/integration/test_dppa_*`, `docs/onsite_vs_offsite.md` (new), `README.md`, `AGENTS.md`.

**Dependencies**
- PHASE-04 (never wrap a module before its parity gate passes).

**Exit Criteria**
- [ ] Full suite green after case modules become deprecated wrappers (existing `test_dppa_*` still pass unchanged).
- [ ] Each wrapper emits a `DeprecationWarning`; README + `docs/onsite_vs_offsite.md` present the two modes as the primary navigation.

**Phase Risks**
- **RISK-05-01:** A wrapper silently drops a behavior not covered by parity tests. Mitigation: wrap incrementally, one case at a time, each behind its own parity gate; the unchanged `test_dppa_*` suite is the safety net.
- **RISK-05-02 (next cycle):** Wrappers linger past one release. Mitigation: file a follow-up to delete them + repoint tests once the new API is proven in use.

## Verification Strategy
- **TEST-001:** New `tests/python/analysis/test_onsite.py`, `test_offsite_dppa.py`, `test_cli.py`, `test_samsung_ttc_parity.py` green (TDD red→green per phase).
- **TEST-002:** `.\tests\run_all_tests.ps1` full run green after each migration step (including the existing `test_dppa_*` suite, which must stay green since the wrappers preserve signatures).
- **TEST-003 (CLI, DEC-004):** `python -m reopt_pysam_vn.analysis onsite|offsite_dppa --config <fixture>` exits 0 and emits a parseable result; covered by `test_cli.py`.
- **MANUAL-001:** Run `run_onsite()` and `run_offsite_dppa()` from a fresh `deal_config` and confirm a `CombinedDecision` result without touching any `dppa_case_*` module.
- **OBS-001:** Compare migrated-case numeric outputs to golden JSON; record max diff (target: within documented tolerance, ideally 0).

## Risks and Alternatives
- **RISK-001:** Generalization subtly changes published case numbers, undermining prior client deliverables. Mitigation: parity gate per case before retirement; keep golden JSON as regression fixtures.
- **RISK-002:** Scope creep into re-modeling settlement/finance. Mitigation: this sprint is extraction + parameterization only; new modeling is a separate plan.
- **ALT-001:** Keep per-deal modules and only add a thin dispatcher. Rejected — leaves the duplication the gap analysis flagged; a future project still needs a new module.

## Grill Me — RESOLVED 2026-06-14
All three questions answered; resolutions captured in DEC-002/003/004 above.
1. **Q-001 (parity tolerance):** ✅ Exact on deterministic post-processing; ≤0.5% on solver-dependent sizing. → **DEC-002**.
2. **Q-002 (retire vs wrap):** ✅ Deprecated thin wrappers for one cycle. → **DEC-003**.
3. **Q-003 (CLI):** ✅ Include a CLI this sprint (deviation from default). → **DEC-004**.

No open clarification questions remain — the plan is execution-ready.

## Suggested Next Step
Decisions resolved (DEC-002/003/004). Execute PHASE-01 → PHASE-05 with strict red→green TDD and the per-phase `/report` + commit + push flow. Land each migrated case behind its own parity gate (DEC-002) before wrapping the bespoke module (DEC-003); build the CLI incrementally across PHASE-02/03 (DEC-004).
