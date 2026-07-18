---
title: "Decree 243/2026 Regulatory Currency + Webapp Hardening"
date: "2026-07-18"
status: "draft"
request: "research/2026-07-18-execution-debt-decree-243-brainstorm.md — turn the new findings (Decree 243 export-cap ingestion, planning-artifact preservation, webapp hardening batch) into a multi-phase implementation plan"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-18-execution-debt-decree-243-brainstorm.md"
  - "research/2026-06-30_decree-243-2026-nd-cp.md"
---

# Plan: Decree 243/2026 Regulatory Currency + Webapp Hardening

## Objective

Bring the Vietnam data layer up to date with Decree 243/2026/ND-CP (effective 2026-06-26), which raised the rooftop-solar surplus export cap from 20% to 50% — the repo currently applies the repealed 20% cap on every preprocessing run, a client-facing correctness defect. Alongside: preserve the currently-untracked planning artifacts in git, add a regulatory-watch table so the next decree does not sit unread in `research/` for three weeks, publish a first-order delta memo quantifying the cap change on a tracked reference run, and close three small webapp gaps (run-id path traversal, runs stranded by process restarts, invisible provenance).

## Context Snapshot

- **Current state:** `data/vietnam/vn_export_rules_decree57.json` (active via `manifest.json` key `export_rules`) sets `rooftop_solar.max_export_fraction: 0.20`. Both preprocessing twins — `src/python/reopt_pysam_vn/reopt/preprocess.py::apply_decree57_export` (line ~682) and `src/julia/REoptVietnam.jl::apply_decree57_export!` (line ~740) — read that value and additionally hard-code `0.20` as the "no warning" sentinel: any other value triggers a UserWarning/`@warn`. Decree 243/2026 (effective 2026-06-26) raised the general cap to 50%, allows >50% through 2030-12-31 where grid capacity permits, makes BESS discharge charged from rooftop solar tradable surplus, and codifies the surplus pricing formula. The repo has a research brief on this (`research/2026-06-30_decree-243-2026-nd-cp.md`) but `grep -rn "243" src/` returns zero hits. Separately: the 2026-07-17 sprint plan, two brainstorm briefs, and the KBC cross-check script are untracked files on one machine; the webapp joins URL-supplied `run_id` values directly onto its storage root; a webapp process restart strands queued/solving runs forever; and `provenance.json` is written per run but never rendered.
- **Desired state:** A new versioned data file `vn_export_rules_2026_decree243.json` is the active `export_rules` source (50% cap, Decree 243 metadata); a `decree_57_2025_legacy` regime reproduces the pre-2026-06-26 world; both preprocessing twins warn only when a caller explicitly overrides the regime-resolved cap; a tracked memo quantifies the 20%→50% first-order effect on the Saigon18 golden run; all planning artifacts are committed; `docs/regulatory-watch.md` maps each data file to its governing instrument; the webapp rejects malformed run ids, marks interrupted runs as errors on startup, and shows an "About this run" provenance card.
- **Key repo surfaces:** `data/vietnam/{manifest.json,vn_export_rules_decree57.json,vn_regime_registry_2026.json}`, `src/python/reopt_pysam_vn/reopt/preprocess.py`, `src/julia/REoptVietnam.jl`, `src/python/reopt_pysam_vn/integration/settlement.py`, `tests/python/reopt/{test_unit.py,test_data_validation.py,test_regime_impact_multi.py}`, `tests/python/integration/test_settlement_presets.py`, `tests/julia/{test_unit.jl,test_integration.jl}`, `tests/cross_language/cross_validate.py`, `src/python/reopt_pysam_vn/webapp/{storage.py,jobs.py,routes/pages.py,templates/run.html,README.md}`, `tests/python/webapp/{test_storage.py,test_jobs.py,test_pages.py,test_api_runs.py}`, `examples/saigon18_scenario-a_reopt-solve.example.json`, `docs/regulatory-watch.md` (new), `reports/` (tracked `.md` only).
- **Out of scope:** Everything in `plans/2026-07-17-truth-and-correctness-sprint-plan.md` (CI markers, PySAM pin, two-part tariff fix, Single Owner clean-slate) except the single KBC-script relocation noted in DEC-005; any re-optimization of existing REopt solves under the new cap (the memo is fixed-dispatch first-order only); modeling the new surplus pricing formula or BESS-surplus value stack (documented as data-file notes and regulatory-watch rows, not implemented); any change to `examples/` golden files; git-history rewrites; webapp authentication.

## Environment & Conventions

- **Stack:** Python 3.12 via the repo-local virtualenv `.venv` (Windows: `.venv\Scripts\python.exe`). **PySAM 7.1.0 (`nrel-pysam`) exists only inside `.venv`** — system Python 3.14 has no PySAM wheel and code silently falls back to synthetic solar profiles. Always use the `.venv` interpreter. Package layout: setuptools, `package-dir = {"" = "src/python"}`. Julia 1.10.10 with REopt.jl v0.56.4 exists for the Julia twin and cross-validation layers.
- **Setup:** From repo root, PowerShell: `.venv\Scripts\python.exe -m pip install -e ".[webapp]"` (add `pytest` if missing).
- **Build / Run:** No build step. Web app: `$env:PYTHONPATH = "src/python"; .venv\Scripts\python.exe -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000`.
- **Test:** Full Python suite: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q`. Single file: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/reopt/test_unit.py -q`. Julia layers via PowerShell runner: `.\tests\run_all_tests.ps1 -Layer 2 -JuliaTimeoutSeconds 1800` (Julia cold start 3–8 min) and `.\tests\run_all_tests.ps1 -Layer 3` for Julia↔Python cross-validation. Set `$env:JULIA_PKG_PRECOMPILE_AUTO = "0"` before any direct Julia invocation.
- **Conventions & traps:**
  - **`PYTHONPATH` gotcha:** a stray global `PYTHONPATH` on the primary machine shadows the `.venv` FastAPI/pydantic install (`ModuleNotFoundError: pydantic_core._pydantic_core`). Clear it (`$env:PYTHONPATH = ""`) before every pytest run.
  - **Known-red baseline:** 5 tests fail on unmodified `main` (numeric drift, tracked in `activeContext.md` "Known pre-existing test failures"): 2 in `tests/python/analysis/test_samsung_ttc_parity.py`, plus `test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`, `test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`, `test_strike_price_discovery.py::test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike`. GitHub Actions CI on `main` is red for these plus environment reasons. "Suite green" in this plan means **no failures beyond that list** (or `0 failed` if the 2026-07-17 sprint plan has landed first and xfail-annotated them). The full suite also runs live NREL API tests when `NREL_API.env` is present and can exceed 10 minutes — the scoped per-phase commands below are the primary gates.
  - **JSON reads use `encoding="utf-8-sig"`** (tolerates Windows UTF-8 BOM). Every new reader in this plan must match.
  - **Units:** `max_export_fraction` is a **fraction** (0.50); `ContractParams.export_cap_pct` is a **percent** (50.0). EVN tariffs and settlement are **VND/kWh**; REopt tariff series are **USD/kWh**; convert at the export-rules file's `_meta.exchange_rate_vnd_per_usd` = 26,400. Do not mix the two cap representations.
  - **Data files use a `_meta` envelope**; code reads only the `"data"` block. Policy updates = new versioned file + one-line `manifest.json` change; never edit an old file's `data` block in place.
  - **Bit-exact golden gates:** `tests/python/webapp/test_golden_parity.py` (and `tests/python/analysis/test_samsung_ttc_parity.py`) compare against `examples/samsung-ttc_combined-decision.example.json`. The Samsung/TTC offsite path is PySAM/CfD-based and does not consume the rooftop export cap, but verify `test_golden_parity.py` passes after every phase; any diff there is a defect in this plan's changes.
  - Type hints everywhere in `src/python/reopt_pysam_vn/`; only `analysis/` and `webapp/` are mypy-gated in CI (`mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` must stay clean — PHASE-04 touches `webapp/`).
- **Repo map:**
  - `data/vietnam/` — versioned policy JSON + `manifest.json` registry (keys: tariff, tech_costs, financials, emissions, export_rules, regimes, deal_defaults).
  - `src/python/reopt_pysam_vn/reopt/preprocess.py` — Python preprocessing: `load_vietnam_data()`, `resolve_vietnam_regime()`, `apply_decree57_export()` (line ~667), `apply_vietnam_defaults()` (line ~733). `DEFAULT_REGIME_ID = "decision_963_2026_current"` (line 50).
  - `src/julia/REoptVietnam.jl` — Julia twin with identical behavior; Layer-3 cross-validation (`tests/cross_language/cross_validate.py`) asserts byte-identical output of the two.
  - `src/python/reopt_pysam_vn/integration/settlement.py` — hourly DPPA settlement engine: `ContractParams` (dataclass, `export_cap_pct: float = 20.0`), `compute_hourly_settlement(loads_kw, generation_kw, tariff_rates_vnd_kwh, fmp_vnd_kwh, contract_params, *, market_source_label="") -> SettlementResult`, `PRESET_CONTRACTS` dict (4 presets).
  - `src/python/reopt_pysam_vn/webapp/` — FastAPI app: `storage.py` (`RunStorage`, one dir per run under `artifacts/webapp/runs/<run_id>/`), `jobs.py` (`JobManager`, in-memory FIFO + worker thread), `routes/pages.py` (HTML pages), `routes/api.py` (JSON API), `templates/run.html`.
  - `tests/python/{reopt,integration,webapp}/`, `tests/julia/`, `tests/cross_language/` — pytest + Julia Test suites; `examples/` — tracked golden runs.
  - `plans/`, `research/`, `reports/` (only `*.md` tracked), `docs/`.

## Research Inputs

- From `research/2026-06-30_decree-243-2026-nd-cp.md`:
  - Decree 243/2026/ND-CP took effect **2026-06-26** (immediate, no 45-day lag). General surplus export cap: **50%** of rooftop system output measured at the inverter; parties may agree to **>50% through 2030-12-31** where local grid capacity permits; off-grid (mountainous/border/island) areas have no cap.
  - **BESS discharge charged from rooftop solar is explicitly tradable surplus** — first decree-level BESS provision; affects BESS value-stack assumptions but is out of implementation scope here (recorded in data-file notes + regulatory watch).
  - **Surplus pricing formula codified:** previous-year average electricity market price, capped at the max regional utility-scale ground-mount solar tariff without BESS (ex-VAT), metered at the inverter, settled monthly at min(actual, agreed) volume. No new VND figure published — the existing 671 VND/kWh stays until a prior-year FMP average is published (DEC-002).
  - Sellers of surplus need an **electricity operation license** unless exempt — OPEX consideration only, recorded in notes.
  - Primary source: VietnamNet (2026-06-28), `https://vietnamnet.vn/en/new-rules-ease-limits-on-surplus-rooftop-solar-power-sales-in-vietnam-2530279.html`.
- From `research/2026-07-18-execution-debt-decree-243-brainstorm.md`:
  - `grep -rn "243" src/` → zero hits; `vn_export_rules_decree57.json` `_meta.last_updated` = 2026-02-18; regime registry last updated 2026-05-07 with no Decree 243 entry. The miss happened despite the 06-30 brief — hence the regulatory-watch table (PHASE-01).
  - The planning artifacts `plans/2026-07-17-truth-and-correctness-sprint-plan.md`, `research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md`, `research/2026-07-18-execution-debt-decree-243-brainstorm.md`, and `scripts/python/2026-07-17_kbc_proforma_pysam_crosscheck.py` are untracked (`git status` `??`) — single-machine loss risk (PHASE-01).
  - Webapp: `storage.py::_run_dir` does `self.root / run_id` with URL-supplied ids (traversal); `jobs.py` keeps the queue in memory so a restart strands `queued`/`solving` runs; `provenance.json` (solver, cache hit, `policy_data_versions`, wall time) is written but never rendered. Interrupted runs should be **marked error, not auto-requeued** (protects NREL API quota).
  - The Samsung/TTC golden path is offsite-CfD and does not consume the rooftop export cap — verify rather than assume (ASM-004).

## Assumptions and Constraints

- **ASM-001:** The decree numbers (50% general cap, >50% allowed to 2030-12-31, effective 2026-06-26) are taken from the VietnamNet-sourced research brief. — **BINDING DEFAULT:** encode them as-is, citing the brief and the VietnamNet URL in the new data file's `_meta`; do not block on obtaining the Vietnamese decree text.
- **ASM-002:** No official prior-year FMP average has been published for the new surplus pricing formula. — **BINDING DEFAULT:** keep `surplus_purchase_rate_vnd_per_kwh: 671` and `surplus_purchase_rate_usd_per_kwh: 0.0254` unchanged; describe the new formula only in the `pricing_basis` and `notes` strings; add a regulatory-watch row to revisit when EVN/NSMO publishes the average.
- **ASM-003:** Julia 1.10.10 and the REopt.jl environment run on the executing machine (per `AGENTS.md`). — **BINDING DEFAULT:** run the Julia Layer-2 tests and Layer-3 cross-validation as specified; if Julia genuinely cannot run (e.g. fresh clone without the Julia depot), still make the `.jl` source/test edits (they are mechanical twins of the Python edits), record "Julia layers not executed on this machine" in `activeContext.md`, and treat the Python suite plus the Layer-3 data-identity reasoning (both languages read the same JSON) as the gate.
- **ASM-004:** The Samsung/TTC golden does not consume `rooftop_solar.max_export_fraction` (offsite PySAM/CfD path). — **BINDING DEFAULT:** verify empirically by running `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp/test_golden_parity.py -q` immediately after the PHASE-02 data flip; if it fails, stop the phase and revert the manifest flip — the coupling must be root-caused before proceeding.
- **ASM-005:** `SettlementResult.annual_summary` key names for exported/curtailed energy and developer revenue are not documented here. — **BINDING DEFAULT:** at PHASE-03 execution, inspect `sorted(result.annual_summary.keys())` once and use the keys containing export/curtail/revenue; if `annual_summary` lacks an exported-energy total, sum the `exported` field over `result.hourly_ledger` rows (field name per `compute_hourly_settlement`'s ledger-append block, `settlement.py` lines ~150–170).
- **ASM-006:** `tests/python/reopt/test_regime_impact_multi.py` exercises regime lists including `decree57_rooftop_50pct_draft` but computes tariff-side impacts; the export-cap base change does not alter its assertions. — **BINDING DEFAULT:** run that file explicitly in PHASE-02; if an assertion breaks because the 50%-draft regime is now identical to base, update only the broken expectation with a comment citing Decree 243, never by deleting the regime from the registry.
- **ASM-007:** The 2026-07-17 sprint plan (`plans/2026-07-17-truth-and-correctness-sprint-plan.md`) may or may not have been executed when this plan runs. — **BINDING DEFAULT:** this plan is self-contained and does not depend on it; interpret "suite green" per the Known-red baseline note in Environment & Conventions. If that sprint already relocated the KBC script, skip TASK-01-02 here.
- **CON-001:** `examples/` files must not change; `tests/python/webapp/test_golden_parity.py` must pass unmodified at every commit of this plan.
- **CON-002:** Never edit the `"data"` block of `data/vietnam/vn_export_rules_decree57.json`; supersession happens via a new file + `manifest.json` (the repo's versioning policy). A one-line supersession pointer may be appended to that file's `_meta.notes` string only.
- **CON-003:** All new JSON readers use `encoding="utf-8-sig"`.
- **CON-004:** Do not change `ContractParams` field defaults (callers may rely on them; the Samsung path imports this module). New behavior ships as a new `PRESET_CONTRACTS` entry.
- **CON-005:** Keep the regime key `decree57_rooftop_50pct_draft` in the registry (referenced by `tests/python/reopt/test_regime_impact_multi.py` and `tests/julia/test_unit.jl`); supersession is expressed in its `notes`/`status` only.
- **CON-006:** `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` must stay clean (CI type gate covers `webapp/`, which PHASE-04 modifies).
- **DEC-001:** Ingestion mechanism = new versioned base export-rules file + `manifest.json` flip. No new "decree_243" regime entry is added: regimes compose tariff × export overrides on top of the base files, so flipping the base reaches every regime uniformly (exactly how the active file already works). The old world stays reachable via a new `decree_57_2025_legacy` regime whose `export_rule_overrides` pin `max_export_fraction: 0.20`.
- **DEC-002:** Surplus purchase rate value unchanged (see ASM-002); Decree 243's pricing formula, BESS tradability, and licensing requirement are recorded as data-file notes and regulatory-watch rows, not modeled.
- **DEC-003:** The "warn on non-default export fraction" sentinel in both preprocessing twins changes from the literal `0.20` to the regime-resolved data value, so the warning means "caller explicitly overrode the active regulatory value" in every era.
- **DEC-004:** Webapp runs found in a non-terminal state at startup are marked `error` with code `interrupted_restart` — never auto-requeued (an auto-requeue could silently re-spend NREL API quota on abandoned runs).
- **DEC-005:** The untracked KBC cross-check script is committed at its canonical path `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py` in PHASE-01 (with the two mechanical fixes the move requires). This intentionally pre-empts the equivalent half of TASK-01-09 in the 2026-07-17 sprint plan; whoever executes that plan should skip its KBC-script portion.

## Specification

**Decree 243 first-order export delta (PHASE-03).** For the fixed Saigon18 scenario-A dispatch (no re-optimization), per hour `h` of 8760 one-hour steps (kW ≡ kWh per step):

- `gen(h) = pv_to_load(h) + pv_to_grid(h) + pv_to_storage(h) + pv_curtailed(h)` — total PV generation, summed from the four `PV/*_series_kw` arrays of `examples/saigon18_scenario-a_reopt-solve.example.json`.
- `load(h)` = `ElectricLoad/load_series_kw[h]`.
- `tariff_vnd(h)` = `ElectricTariff/energy_rate_series/Tier_1[h]` (USD/kWh) × 26,400 VND/USD.
- `fmp(h) = 0.0` for all `h` — `compute_hourly_settlement` ignores the FMP series in `private_wire` mode (only the `virtual_cfd` branch reads `market_price`).
- Run `compute_hourly_settlement(load, gen, tariff_vnd, fmp, P)` twice with `P` = `PRESET_CONTRACTS["decree57_private_wire_standard"]` (cap 20%) and `P` = `PRESET_CONTRACTS["decree243_export_50pct_standard"]` (cap 50%, created in PHASE-02; identical otherwise: `mode="private_wire"`, `strike_vnd_kwh=1012.0`, `escalation_rate=0.05`, `settlement_quantity_rule="matched_only"`, `excess_treatment="export_at_surplus"`, `surplus_rate_vnd_kwh=671.0`, `dppa_adder_vnd_kwh=0.0`, `kpp_pct=0.0`).
- Per the engine's hourly cap semantics (`settlement.py` line ~111): `exported(h) = min(excess(h), cap_fraction · gen(h))` where `excess(h) = max(0, gen(h) − min(load(h), gen(h)))` and `cap_fraction = export_cap_pct / 100`.
- Report: annual exported kWh, curtailed kWh, and developer surplus revenue (`exported × 671` VND) under each cap, plus deltas in VND/yr and USD/yr (÷ 26,400). `Δrevenue ≥ 0` always (a larger cap can only increase hourly `exported`).
- Closed-form toy check (used as a unit test): constant `gen(h)=100.0` kW, `load(h)=40.0` kW, any tariff, all 8760 h → `excess=60`; cap 20%: `exported=20`, `curtailed=40`; cap 50%: `exported=50`, `curtailed=10`. Annual exported delta = `30 × 8760 = 262,800` kWh; annual developer-revenue delta = `262,800 × 671 = 176,338,800.0` VND.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Preserve planning artifacts in git; create the regulatory-watch table | None | Committed plans/briefs + KBC script at canonical path; `docs/regulatory-watch.md` |
| PHASE-02 | Ingest Decree 243: new export-rules data file, legacy regime, warning-sentinel fix in both language twins, all test updates | PHASE-01 (watch table gets its status flipped here) | Active 50% cap; `decree_57_2025_legacy` regime; green Python + Julia unit layers |
| PHASE-03 | Quantify the 20%→50% first-order effect on the Saigon18 golden run | PHASE-02 (new preset + data) | `scripts/python/reopt/decree243_export_cap_delta.py` + tracked memo in `reports/` |
| PHASE-04 | Webapp hardening: run-id validation, interrupted-run sweep, provenance card | None (independent; sequenced last to keep diffs separable) | Hardened `storage.py`/`jobs.py`; provenance card on `/runs/{run_id}`; tests |

## Detailed Phases

### PHASE-01 - Preserve Planning Artifacts + Regulatory Watch Table

**Goal**
Every planning artifact currently existing only as an untracked file is committed, the KBC script lands at its canonical path, and a tracked table makes "which regulation governs which data file, and is it current?" a diffable question.

**Tasks**
- [ ] TASK-01-01: Commit the untracked planning documents as-is: `git add "plans/2026-07-17-truth-and-correctness-sprint-plan.md" "research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md" "research/2026-07-18-execution-debt-decree-243-brainstorm.md" "plans/2026-07-18-decree-243-currency-webapp-hardening-plan.md"` (this plan file itself).
- [ ] TASK-01-02: Relocate the untracked KBC script (skip if `plans/2026-07-17-truth-and-correctness-sprint-plan.md` TASK-01-09 already did this — check `git ls-files scripts/python/pysam/` first): `mv scripts/python/2026-07-17_kbc_proforma_pysam_crosscheck.py scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py`, then inside it (a) change `Path(__file__).resolve().parents[2]` to `parents[3]` (the file moved one directory deeper; the expression computes the repo root for `sys.path.insert`), and (b) in the module docstring, replace the reference to `plans/2026-07-17-kbc-feedback-package-update-plan.md` (a file that does not exist in this repo) with "per the Allotrope–KBC JV feedback-package plan (external workspace)". `git add` the result. No other changes — the script is a frozen comparison harness.
- [ ] TASK-01-03: Create `docs/regulatory-watch.md` with the table below and a 3-sentence header explaining the rule: *whenever a `research/` brief lands documenting a regulatory change, add or update a row here in the same commit; a row whose Status is `STALE` blocks new client-facing analysis using that file.* Initial rows (one per `data/vietnam/manifest.json` key):

  | Manifest key | Active file | Governing instrument(s) | Known supersession | Status |
  |---|---|---|---|---|
  | tariff | vn_tariff_2025.json | Decision 963/QD-BCT (TOU, active), Decision 14/2025 (legacy), Decree 146/2025 (two-part trial) | — | CURRENT |
  | tech_costs | vn_tech_costs_2025.json | Market price surveys | — | CURRENT |
  | financials | vn_financial_defaults_2025.json | CIT law 20%, decrees on incentives | — | CURRENT |
  | emissions | vn_emissions_2024.json | HUST/MONRE grid-factor study | Annual MONRE update expected | CURRENT |
  | export_rules | vn_export_rules_decree57.json | Decree 57/2025, Decree 58/2025 | **Decree 243/2026 (eff. 2026-06-26): cap 20%→50%, BESS surplus tradable, new pricing formula — see research/2026-06-30_decree-243-2026-nd-cp.md** | **STALE — fixed by PHASE-02 of plans/2026-07-18-decree-243-currency-webapp-hardening-plan.md** |
  | regimes | vn_regime_registry_2026.json | Repo-defined bundles over the above | — | CURRENT |
  | deal_defaults | vn_deal_defaults_2026.json | Repo-defined deal seeds | — | CURRENT |

- [ ] TASK-01-04: Commit ("docs: preserve planning artifacts; add regulatory watch table").

**File Changes**
- `plans/2026-07-17-truth-and-correctness-sprint-plan.md`, `research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md`, `research/2026-07-18-execution-debt-decree-243-brainstorm.md`, `plans/2026-07-18-decree-243-currency-webapp-hardening-plan.md` (track, no content edits).
- `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py` (create via move of the untracked flat file): `parents[3]` fix + docstring reference fix only.
- `docs/regulatory-watch.md` (create): table above + header rule.

**Function Signatures**
None — no code interfaces change in this phase (the two KBC-script edits are mechanical).

**Test Specs**
None — no testable behavior changes in this phase. (Sanity: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -c "import ast; ast.parse(open('scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py', encoding='utf-8').read())"` exits 0 — the moved script still parses.)

**Dependencies**
- None.

**Exit Criteria**
- [ ] `git status --short` shows none of the four planning documents or the KBC script as untracked.
- [ ] `git ls-files scripts/python | grep -E "^scripts/python/[^/]+\.py$"` does not list the KBC script (flat level clean of it).
- [ ] `docs/regulatory-watch.md` exists with the export_rules row marked STALE.

**Phase Risks**
- **RISK-01-01:** Concurrent execution of the 2026-07-17 sprint plan moves the KBC script differently. Mitigation: the `git ls-files` pre-check in TASK-01-02; both plans target the same canonical destination path.

### PHASE-02 - Decree 243 Ingestion: Data, Regimes, Twin Code, Twin Tests

**Goal**
The active export-rules data encodes Decree 243/2026 (50% cap); the pre-243 world is reproducible via a named legacy regime; both preprocessing twins warn only on explicit caller overrides of the active value; every affected Python and Julia test is updated; Layer-3 cross-validation stays exact.

**Tasks**
- [ ] TASK-02-01 (RED): Update Python tests first and confirm they fail against current data/code:
  - `tests/python/reopt/test_unit.py`: change the two assertions `d["_meta"]["decree57_max_export_fraction"] == pytest.approx(0.20)` (lines ~560 and ~671) to `pytest.approx(0.50)`. In `test_default_max_export_fraction_no_warning` (line ~578), change the explicit `max_export_fraction=0.20` to `0.50`. Add two tests to the same class: `test_explicit_legacy_fraction_now_warns` — `apply_decree57_export(d, vn, max_export_fraction=0.20)` raises the `UserWarning` matching `r"max_export_fraction=.*stored for Vietnam custom solve wrappers"` and stores `0.20` in `_meta`; `test_legacy_regime_restores_20pct_without_warning` — `apply_decree57_export(d, vn, regime_id="decree_57_2025_legacy")` stores `pytest.approx(0.20)` and emits no `UserWarning` (use `warnings.catch_warnings()` + `simplefilter("error", UserWarning)`, matching the existing no-warning test's pattern). Leave `test_non_default_max_export_fraction_warns` (0.10) untouched — 0.10 ≠ 0.50 still warns.
  - `tests/python/integration/test_settlement_presets.py`: add a test asserting `PRESET_CONTRACTS["decree243_export_50pct_standard"]` exists with `export_cap_pct == 50.0`, `mode == "private_wire"`, `strike_vnd_kwh == 1012.0`, `excess_treatment == "export_at_surplus"`, `surplus_rate_vnd_kwh == 671.0` (follow the file's existing preset-assertion style).
  - Run: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/reopt/test_unit.py tests/python/integration/test_settlement_presets.py -q` → the changed/new tests fail (RED).
- [ ] TASK-02-02: Create `data/vietnam/vn_export_rules_2026_decree243.json` as a full copy of `vn_export_rules_decree57.json` with these edits and nothing else:
  - `_meta`: `version: "2026.1"`, `effective_date: "2026-06-26"`, `source: "Decree 243/2026/ND-CP (eff. 2026-06-26) amending Decree 57/2025/ND-CP (DPPA) and Decree 58/2025/ND-CP (rooftop solar); supersedes the 20% surplus cap"`, `source_url: "https://vietnamnet.vn/en/new-rules-ease-limits-on-surplus-rooftop-solar-power-sales-in-vietnam-2530279.html"`, `notes` describing: 50% general cap; >50% permitted by agreement through 2030-12-31 where grid capacity allows; BESS discharge charged from rooftop solar is tradable surplus (not yet modeled); surplus price = prior-year average market price capped at the regional utility-scale ground-mount solar ceiling ex-VAT (numeric rate retained at 671 VND/kWh pending a published average — see docs/regulatory-watch.md); sellers require an electricity operation license unless exempt. `last_updated`: the execution date. Keep `currency: "VND"` and `exchange_rate_vnd_per_usd: 26400`.
  - `data.rooftop_solar`: `max_export_fraction: 0.50`; add `transitional_over_cap_allowed_until: "2030-12-31"` and `transitional_max_export_fraction: 1.0`; add `bess_discharge_tradable: true`; update `pricing_basis` to "Previous-year average electricity market price, capped at max regional utility-scale ground-mount solar tariff without BESS (ex-VAT), per Decree 243/2026"; update the block's `notes` accordingly. Keep both `surplus_purchase_rate_*` values unchanged (ASM-002/DEC-002).
  - All other `data` blocks (`dppa_ceiling_tariffs_*`, `bess_incentive_requirements`, `dppa_eligibility`, `reopt_mapping`) byte-identical to the source file.
- [ ] TASK-02-03: Flip `data/vietnam/manifest.json`: `"export_rules": "vn_export_rules_2026_decree243.json"`; update `_meta.last_updated` to the execution date. Append one sentence to `vn_export_rules_decree57.json`'s `_meta.notes` (CON-002 allows `_meta` only): "Superseded 2026-06-26 by Decree 243/2026 — see vn_export_rules_2026_decree243.json; retained for reproducibility."
- [ ] TASK-02-04: Edit `data/vietnam/vn_regime_registry_2026.json`:
  - Add regime `decree_57_2025_legacy`: `label: "Decree 57/2025 legacy 20% surplus export cap"`, `effective_date: "2025-06-01"`, `status: "legacy"`, `tariff_overrides: {}`, `export_rule_overrides: {"rooftop_solar": {"max_export_fraction": 0.20, "pricing_basis": "Previous year average wholesale market price or mutually agreed rate"}}`, `postprocess_overrides: {}`, `source_refs: ["data/vietnam/vn_export_rules_decree57.json"]`, `notes: "Reproduces the pre-2026-06-26 export regime (Decree 57/2025 20% cap) after the base export-rules file moved to Decree 243/2026."`.
  - Update `decree57_rooftop_50pct_draft`'s `notes` to state it was **enacted** by Decree 243/2026 effective 2026-06-26 and is retained for pre-enactment sensitivity reproducibility (now equal to the base rules); leave its key, overrides, and `status: "draft"` untouched (CON-005).
  - `_meta`: bump `version` to `"2026.3"`, set `last_updated`, append `research/2026-06-30_decree-243-2026-nd-cp.md` to `source_refs`.
- [ ] TASK-02-05: Fix the Python warning sentinel in `src/python/reopt_pysam_vn/reopt/preprocess.py::apply_decree57_export` (lines ~680–695): capture `data_default = rooftop.get("max_export_fraction", 0.20)` before the `if max_export_fraction is None` fallback; replace the guard `if max_export_fraction != 0.20:` with `if max_export_fraction != data_default:`. Update the function docstring from "per Decree 57/2025" to "per Decree 57/2025 as amended by Decree 243/2026 (surplus cap 50% from 2026-06-26; resolved from the active export-rules data file)". Do not rename the function, `DECREE57_META_KEY`, or any output key (public-surface stability; the `decree57_` prefix is now historical naming, documented in the docstring).
- [ ] TASK-02-06: Mirror in Julia `src/julia/REoptVietnam.jl::apply_decree57_export!` (lines ~733–748): capture `data_default = get(rooftop, "max_export_fraction", 0.20)` before the `=== nothing` fallback; change `if max_export_fraction != 0.20` to `if max_export_fraction != data_default`. Update the docstring the same way.
- [ ] TASK-02-07: Update Julia tests `tests/julia/test_unit.jl`: `@test d["_meta"]["decree57_max_export_fraction"] == 0.20` (line ~408) → `0.50`; in the "default … emits no warning" testset (line ~434), `max_export_fraction=0.20` → `0.50`; add testsets `apply_decree57_export! — explicit legacy 0.20 now warns` (`@test_logs (:warn, r"max_export_fraction=.*stored for Vietnam custom solve wrappers") apply_decree57_export!(d, VN; max_export_fraction=0.20)`) and `apply_decree57_export! — decree_57_2025_legacy regime restores 20 percent` (`regime_id="decree_57_2025_legacy"` → `_meta` fraction `== 0.20`, wrapped in `@test_nowarn`). Check `tests/julia/test_integration.jl` line ~431 (`apply_decree57_export!(d, VN; max_export_fraction=0.20)`): the call now emits a warning — if it sits under `@test_nowarn` or a strict log check, switch that specific call to `regime_id="decree_57_2025_legacy"` (same 0.20 result, no warning); its downstream `ratio <= 0.20 + 1e-6` assertion (line ~450) stays valid because the fraction is still 0.20.
- [ ] TASK-02-08: Add a Python data-validation guard: in `tests/python/reopt/test_data_validation.py`, add `test_active_export_rules_encode_decree_243` asserting `load_vietnam_data().export_rules["rooftop_solar"]["max_export_fraction"] == 0.50` and that the string `"243"` appears in the active export-rules file's `_meta["source"]` (load the file named by the manifest with `encoding="utf-8-sig"`). Mirror in `tests/julia/test_data_validation.jl` if a parallel spot exists (follow its existing rooftop-solar testset at lines ~205 and ~355); if the Julia file has no natural home, the Python guard alone satisfies this task.
- [ ] TASK-02-09 (GREEN): Add the settlement preset — in `src/python/reopt_pysam_vn/integration/settlement.py`, append to `PRESET_CONTRACTS` the key `"decree243_export_50pct_standard"` with `ContractParams(mode="private_wire", strike_vnd_kwh=1012.0, escalation_rate=0.05, settlement_quantity_rule="matched_only", excess_treatment="export_at_surplus", export_cap_pct=50.0, surplus_rate_vnd_kwh=671.0, dppa_adder_vnd_kwh=0.0, kpp_pct=0.0)` — identical to `decree57_private_wire_standard` except the cap. Leave the `ContractParams` dataclass defaults and all existing presets untouched (CON-004; the pre-existing `physical_dppa_export_50pct` preset stays as-is).
- [ ] TASK-02-10: Run the phase gates: `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/reopt tests/python/integration/test_settlement_presets.py tests/python/webapp/test_golden_parity.py -q` → 0 failed (ASM-004 golden check included; ASM-006 regime-impact check included via `tests/python/reopt`). Then Julia layers: `.\tests\run_all_tests.ps1 -Layer 2 -JuliaTimeoutSeconds 1800` and `.\tests\run_all_tests.ps1 -Layer 3` (ASM-003 fallback applies). Flip the `export_rules` row in `docs/regulatory-watch.md` to `CURRENT (Decree 243/2026, file vn_export_rules_2026_decree243.json)` and add a `PENDING` row note for the unpublished prior-year FMP average. Update `activeContext.md`: add a line under a "Decree 243 ingestion (2026-07-18)" heading recording the flip and the unchanged surplus rate. Commit.

**File Changes**
- `data/vietnam/vn_export_rules_2026_decree243.json` (create): per TASK-02-02.
- `data/vietnam/manifest.json` (modify): one key + `_meta.last_updated`.
- `data/vietnam/vn_export_rules_decree57.json` (modify): one `_meta.notes` sentence only — `data` block untouched.
- `data/vietnam/vn_regime_registry_2026.json` (modify): new `decree_57_2025_legacy` regime; `decree57_rooftop_50pct_draft` notes; `_meta` bump.
- `src/python/reopt_pysam_vn/reopt/preprocess.py` (modify): warning sentinel + docstring in `apply_decree57_export` only; `DEFAULT_REGIME_ID`, all other functions, and the 0.20 literal fallback in the `rooftop.get(...)` call stay as-is (the fallback is shadowed by data and guarded by Layer-1 tests).
- `src/julia/REoptVietnam.jl` (modify): warning sentinel + docstring in `apply_decree57_export!` only.
- `src/python/reopt_pysam_vn/integration/settlement.py` (modify): one new `PRESET_CONTRACTS` entry; nothing else.
- `tests/python/reopt/test_unit.py`, `tests/python/reopt/test_data_validation.py`, `tests/python/integration/test_settlement_presets.py`, `tests/julia/test_unit.jl`, `tests/julia/test_integration.jl` (modify): per TASK-02-01/-02-07/-02-08.
- `docs/regulatory-watch.md`, `activeContext.md` (modify): status flips per TASK-02-10.

**Function Signatures**
- `apply_decree57_export(d: dict, vn: VNData, regime_id: str = DEFAULT_REGIME_ID, max_export_fraction: Optional[float] = None, exchange_rate: Optional[float] = None) -> dict` — signature unchanged; behavior change: resolves the default fraction (now 0.50) and the warning threshold from the regime-resolved data instead of a hardcoded 0.20; returns the same mutated dict.
- `apply_decree57_export!(d::Dict, vn::VNData; regime_id::String=DEFAULT_REGIME_ID, max_export_fraction::Union{Nothing,Real}=nothing, exchange_rate::Real=vn.exchange_rate)` — Julia twin, same behavior change.

**Test Specs**
- `apply_decree57_export(make_base_dict(), vn)` → `d["_meta"]["decree57_max_export_fraction"] == pytest.approx(0.50)`; `d["ElectricTariff"]["wholesale_rate"] == pytest.approx(0.0254, abs=1e-4)` (unchanged rate proves DEC-002).
- `apply_decree57_export(d, vn, max_export_fraction=0.50)` under `warnings.simplefilter("error", UserWarning)` → no exception.
- `apply_decree57_export(d, vn, max_export_fraction=0.20)` → warns `UserWarning` matching `r"max_export_fraction=.*stored for Vietnam custom solve wrappers"`; `_meta` value `pytest.approx(0.20)`.
- `apply_decree57_export(d, vn, regime_id="decree_57_2025_legacy")` → `_meta` value `pytest.approx(0.20)`, no warning.
- `apply_decree57_export(d, vn, regime_id="decree57_rooftop_50pct_draft")` → `_meta` value `pytest.approx(0.50)` (existing Julia twin test at `test_unit.jl` ~411 keeps passing).
- `PRESET_CONTRACTS["decree243_export_50pct_standard"].export_cap_pct == 50.0` and `.strike_vnd_kwh == 1012.0`.
- `load_vietnam_data().export_rules["rooftop_solar"]["max_export_fraction"] == 0.50`.
- Layer 3: `.\tests\run_all_tests.ps1 -Layer 3` → PASS (Julia and Python read the identical new JSON; exact match expected as before).

**Dependencies**
- PHASE-01 (regulatory-watch file exists to be flipped). Julia environment per ASM-003.

**Exit Criteria**
- [ ] Phase-gate pytest command (TASK-02-10) → `0 failed`.
- [ ] `tests/python/webapp/test_golden_parity.py` passes and `git diff examples/` is empty (CON-001/ASM-004).
- [ ] Julia Layer 2 + Layer 3 pass, or the ASM-003 waiver is recorded in `activeContext.md`.
- [ ] `git show HEAD --stat` includes the new data file and `docs/regulatory-watch.md` shows export_rules as CURRENT.

**Phase Risks**
- **RISK-02-01:** An unanticipated consumer treats `max_export_fraction == 0.20` as load-bearing (e.g. a regime-impact expectation). Mitigation: the phase gate runs all of `tests/python/reopt` and `tests/python/integration/test_settlement_presets.py`; ASM-006 prescribes the repair pattern (update the expectation with a Decree 243 comment, never delete the regime).
- **RISK-02-02:** Layer-4 API baselines (`tests/baselines/commercial_api_baseline.json`) embed pre-243 metadata. Mitigation: those regression tests were already failing pre-existing (HTTP 400, recorded in `AGENTS.md` §4) and are outside this plan's gates; note in `activeContext.md` if their diff surface changes.

### PHASE-03 - Decree 243 Export-Cap Delta Memo (No Solver)

**Goal**
A tracked, reproducible memo quantifies the first-order (fixed-dispatch) effect of the 20%→50% cap change on the Saigon18 scenario-A golden run, using the repo's own settlement engine — so client-facing conversations about Decree 243 cite a number, not a shrug.

**Tasks**
- [ ] TASK-03-01 (RED): Create `tests/python/reopt/test_decree243_export_cap_delta.py` with the toy-profile tests from the Specification (import from `reopt_pysam_vn.reopt.decree243_delta`, which does not exist yet). Run to confirm collection failure.
- [ ] TASK-03-02 (GREEN): Create `src/python/reopt_pysam_vn/reopt/decree243_delta.py` implementing `extract_saigon18_series` and `compute_export_cap_delta` per the Specification and Function Signatures. JSON reads use `encoding="utf-8-sig"`. Full type hints (house style; module is outside the mypy gate).
- [ ] TASK-03-03: Create the thin CLI `scripts/python/reopt/decree243_export_cap_delta.py`: argparse with `--results-json` (default `examples/saigon18_scenario-a_reopt-solve.example.json`), `--out-md` (default `reports/2026-07-18-decree243-export-cap-delta.md`), `--exchange-rate` (default `26400.0`); calls the library, writes the memo. The memo must state: the two presets compared, the fixed-dispatch caveat (no re-optimization; a REopt re-solve under the 50% cap would likely size PV/BESS differently — flagged as follow-on work), the input file, annual exported/curtailed kWh and surplus revenue under each cap, and the deltas in VND/yr and USD/yr.
- [ ] TASK-03-04: Run the CLI, commit the memo (`reports/*.md` are tracked; the script writes markdown only, no HTML). Add one line to `activeContext.md` citing the headline delta figure.

**File Changes**
- `src/python/reopt_pysam_vn/reopt/decree243_delta.py` (create): the two functions below.
- `tests/python/reopt/test_decree243_export_cap_delta.py` (create): specs below; no artifacts, no network, no PySAM — the example JSON is tracked.
- `scripts/python/reopt/decree243_export_cap_delta.py` (create): thin CLI per TASK-03-03.
- `reports/2026-07-18-decree243-export-cap-delta.md` (create, generated): the memo.
- `activeContext.md` (modify): one headline line.

**Function Signatures**
- `extract_saigon18_series(results_json_path: Path, *, exchange_rate_vnd_per_usd: float = 26400.0) -> dict[str, list[float]]` — reads a REopt results JSON and returns `{"loads_kw": [...8760...], "generation_kw": [...8760...], "tariff_vnd_per_kwh": [...8760...]}` where generation sums the four `PV/*_series_kw` arrays (`electric_to_load`, `electric_to_grid`, `electric_to_storage`, `electric_curtailed`) element-wise and tariff converts `ElectricTariff/energy_rate_series/Tier_1` (USD/kWh) × exchange rate; raises `KeyError` with the missing JSON path if any series is absent, `ValueError` if any series length ≠ 8760.
- `compute_export_cap_delta(loads_kw: list[float], generation_kw: list[float], tariff_vnd_per_kwh: list[float], *, exchange_rate_vnd_per_usd: float = 26400.0) -> dict[str, float]` — runs `compute_hourly_settlement` (fmp = `[0.0]*8760`) under `PRESET_CONTRACTS["decree57_private_wire_standard"]` and `PRESET_CONTRACTS["decree243_export_50pct_standard"]`; returns `{"exported_kwh_cap20": float, "exported_kwh_cap50": float, "curtailed_kwh_cap20": float, "curtailed_kwh_cap50": float, "surplus_revenue_vnd_cap20": float, "surplus_revenue_vnd_cap50": float, "delta_exported_kwh": float, "delta_surplus_revenue_vnd": float, "delta_surplus_revenue_usd": float}` (annual totals per ASM-005; surplus revenue = exported × 671).

**Test Specs**
- Toy constant profile (Specification closed form): `compute_export_cap_delta([40.0]*8760, [100.0]*8760, [2000.0]*8760)` → `exported_kwh_cap20 == pytest.approx(20.0*8760)`, `exported_kwh_cap50 == pytest.approx(50.0*8760)`, `curtailed_kwh_cap50 == pytest.approx(10.0*8760)`, `delta_exported_kwh == pytest.approx(262_800.0)`, `delta_surplus_revenue_vnd == pytest.approx(176_338_800.0)`, `delta_surplus_revenue_usd == pytest.approx(176_338_800.0/26_400.0)`.
- Monotonicity guard: with any profile, `delta_exported_kwh >= 0.0` and `curtailed_kwh_cap50 <= curtailed_kwh_cap20` (run on the toy peaky profile `loads=[10.0]*8760`, `generation=[0.0]*8759 + [5000.0]`).
- Real-file smoke: `extract_saigon18_series(Path("examples/saigon18_scenario-a_reopt-solve.example.json"))` → all three lists length 8760; `generation_kw` annual sum > 0; every `tariff_vnd_per_kwh` value > 0.
- Length guard: `compute_export_cap_delta([1.0]*100, [1.0]*8760, [1.0]*8760)` → raises `ValueError`.

**Dependencies**
- PHASE-02 (the `decree243_export_50pct_standard` preset and updated data).

**Exit Criteria**
- [ ] `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/reopt/test_decree243_export_cap_delta.py -q` → all pass, including the exact `176_338_800.0` expectation.
- [ ] `.venv\Scripts\python.exe scripts/python/reopt/decree243_export_cap_delta.py` exits 0 and writes the memo; the memo's `delta_surplus_revenue_vnd` ≥ 0.
- [ ] `git ls-files reports/2026-07-18-decree243-export-cap-delta.md` → listed (tracked).

**Phase Risks**
- **RISK-03-01:** The Saigon18 golden run may export little (the solve was constrained by the 20% rules), making the fixed-dispatch delta small and understated. Mitigation: the memo's caveat paragraph states exactly this and frames the number as a lower bound pending a re-optimization follow-on; the memo still quantifies curtailment headroom (curtailed kWh that becomes exportable).

### PHASE-04 - Webapp Hardening: Run-Id Validation, Interrupted-Run Sweep, Provenance Card

**Goal**
The webapp rejects malformed run ids before touching the filesystem, converts restart-stranded runs into visible errors, and shows each run's provenance — closing the three gaps with tests and zero behavior change for well-formed traffic.

**Tasks**
- [ ] TASK-04-01 (RED): Add tests (see Test Specs) to `tests/python/webapp/test_storage.py`, `tests/python/webapp/test_jobs.py`, and `tests/python/webapp/test_pages.py`, following each file's existing fixture pattern (temp-dir `RunStorage` / FastAPI `TestClient` from `tests/python/webapp/conftest.py`). Run `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp -q` → new tests fail.
- [ ] TASK-04-02 (GREEN, storage): In `src/python/reopt_pysam_vn/webapp/storage.py`: add module-level `_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")` (first char alphanumeric — this rejects `..`, absolute paths, and separators; generated ids `{timestamp}-{counter:08d}-{slug}-{hex6}` always match). At the top of `_run_dir`, before joining: `if not _RUN_ID_RE.match(run_id): raise KeyError(f"no such run: {run_id!r}")` — same exception type the routes already translate to 404. Add `mark_interrupted_runs(self) -> List[str]`: iterate `self.list_runs()`; for every run whose `status.json` `state` is in `{"queued", "solving", "analyzing"}`, call `self.set_status(run_id, state="error", message="Run was interrupted by an app restart before it finished.", error_code="interrupted_restart", error_hint="Clone this run from the history page and submit it again.")`; return the affected run ids.
- [ ] TASK-04-03 (GREEN, jobs): In `src/python/reopt_pysam_vn/webapp/jobs.py::JobManager.start`, before spawning the thread: `interrupted = self.storage.mark_interrupted_runs()`, then `logger.warning("marked %d interrupted run(s) as error on startup: %s", len(interrupted), interrupted)` when non-empty. No change to `stop`, `submit_solve`, `_worker_loop`, or `_process`.
- [ ] TASK-04-04 (GREEN, provenance card): In `src/python/reopt_pysam_vn/webapp/routes/pages.py::run_detail` (line ~66), fetch `provenance = storage.get_provenance(run_id)` (returns `Optional[dict]`) and add it to the template context. In `templates/run.html`, after the results section (inside the `status.state == 'done'` block), add a card: heading "About this run"; rows for `solver`, `cache_hit` (render "yes — reused run {cached_from_run_id}" when true), `wall_time_seconds` (rounded to 1 decimal), `package_version`, `pysam_available`, and a small table of `policy_data_versions` (key → version). Wrap the whole card in `{% if provenance %}` so legacy runs without `provenance.json` render unchanged.
- [ ] TASK-04-05: Document both behaviors in `src/python/reopt_pysam_vn/webapp/README.md`: one sentence under the storage-layout section (non-terminal runs are marked `error`/`interrupted_restart` at startup) and one sentence noting the provenance card. Run `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` → clean (CON-006). Run the full webapp suite + golden parity; commit.

**File Changes**
- `src/python/reopt_pysam_vn/webapp/storage.py` (modify): `import re` if absent, `_RUN_ID_RE`, the `_run_dir` guard, `mark_interrupted_runs`. Leave `create_run`'s id format, locking, and all other methods untouched.
- `src/python/reopt_pysam_vn/webapp/jobs.py` (modify): the two `start()` lines only.
- `src/python/reopt_pysam_vn/webapp/routes/pages.py` (modify): provenance fetch + context key in `run_detail` only.
- `src/python/reopt_pysam_vn/webapp/templates/run.html` (modify): the provenance card block only.
- `src/python/reopt_pysam_vn/webapp/README.md` (modify): two sentences.
- `tests/python/webapp/test_storage.py`, `tests/python/webapp/test_jobs.py`, `tests/python/webapp/test_pages.py` (modify): new tests per Test Specs.

**Function Signatures**
- `RunStorage.mark_interrupted_runs(self) -> List[str]` — marks every run in a non-terminal state (`queued`/`solving`/`analyzing`) as `error` with code `interrupted_restart`; returns the list of affected run ids (empty when none).
- `_RUN_ID_RE: re.Pattern[str]` — module constant; `_run_dir` raises `KeyError` for any `run_id` it does not fully match.

**Test Specs**
- Traversal (storage): `storage.get_status("../evil")` → raises `KeyError`; `storage.get_status("..")` → `KeyError`; `storage.get_status("a/b")` → `KeyError`; `storage.get_status(".hidden")` → `KeyError`. Positive control: a real id from `storage.create_run({...})` still round-trips `get_status` → dict with `state == "queued"`.
- Traversal (API): `client.get("/api/runs/..")` → status code 404 (route translates the `KeyError`).
- Interrupted sweep: create three runs; `set_status(a, state="solving")`, `set_status(b, state="done")`, leave `c` as created (`queued`); `storage.mark_interrupted_runs()` → returns exactly `{a, c}` (order-insensitive); `get_status(a)["state"] == "error"` with `error_code == "interrupted_restart"`; `get_status(b)["state"] == "done"` (untouched).
- Sweep-on-start: with a run in `state="solving"`, construct `JobManager(storage)`, call `.start()` then `.stop()` → that run's status is `error`/`interrupted_restart`.
- Provenance card: for a run in `state="done"` with `write_provenance(run_id, {"run_id": run_id, "solver": "nrel_api", "cache_hit": False, "cached_from_run_id": None, "wall_time_seconds": 12.34, "policy_data_versions": {"export_rules": "2026.1"}, "package_version": "0.1.0", "pysam_available": True, "created_at": "20260718T000000000000", "nrel_key_fingerprint": None, "solve_hash": "x"})` → `client.get(f"/runs/{run_id}")` returns 200 and the body contains `About this run`, `nrel_api`, and `2026.1`. For a done run **without** provenance → 200 and the body does **not** contain `About this run`.

**Dependencies**
- None on PHASE-02/03 (independent subsystem). Requires `pip install -e ".[webapp]"` extras.

**Exit Criteria**
- [ ] `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp -q` → 0 failed (includes `test_golden_parity.py`).
- [ ] `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` → no errors.
- [ ] Manual smoke: launch the app, open an existing done run → provenance card renders; `curl -s -o NUL -w "%{http_code}" "http://127.0.0.1:8000/api/runs/.."` → `404`.

**Phase Risks**
- **RISK-04-01:** Some existing webapp test uses a hand-written run id that the new regex rejects (e.g. containing `/`). Mitigation: the regex accepts any id starting alphanumeric with `[A-Za-z0-9._-]` after — covering fixture ids like `"run1"`; if a fixture uses a pathological id, rename the fixture id rather than loosening the regex.
- **RISK-04-02:** The provenance card leaks the NREL key fingerprint. Mitigation: the card's field list (TASK-04-04) deliberately excludes `nrel_key_fingerprint` and `solve_hash`; do not render dict keys generically.

## Gotchas

- **Fraction vs percent:** `max_export_fraction` is `0.50`; `ContractParams.export_cap_pct` is `50.0`. Mixing them produces 100×-off results that still "look plausible" in VND magnitudes.
- **Two representations of the same cap live in different layers** (preprocess `_meta` fraction for the REopt/JuMP constraint wrappers; settlement preset percent for the CfD engine). This plan updates both; nothing synchronizes them automatically — the regulatory-watch row is the reminder.
- **`DECREE57_META_KEY` and the function names keep their `decree57_` prefix on purpose** — they are public surface consumed by the Julia constraint wrapper and tests; Decree 243 amends Decree 57 rather than replacing the mechanism. Renaming would churn both language twins for zero behavior.
- **The hourly cap is `cap_fraction × gen(h)` per hour, not an annual-energy cap** (`settlement.py` line ~111). The toy expectations in this plan are computed under hourly semantics; do not "simplify" to annual ratios.
- **JSON BOM:** every new reader uses `encoding="utf-8-sig"`; `preprocess.py::load_vietnam_data` itself reads plain `utf-8` — write the new data file without a BOM (ASCII-safe content) so both readers are happy.
- **Warning tests are strict on both sides:** Python uses `pytest.warns`/`simplefilter("error", UserWarning)`; Julia uses `@test_logs`/`@test_nowarn`. After the sentinel change, any *other* test that calls `apply_decree57_export(..., max_export_fraction=0.20)` (Python) or `apply_decree57_export!(...; max_export_fraction=0.20)` (Julia) will start warning — run `grep -rn "max_export_fraction" tests/` before declaring the phase done.
- **Do not edit `examples/`** — two golden-parity test files gate `samsung-ttc_combined-decision.example.json` bit-exactly, and PHASE-03 reads (never writes) the Saigon18 example.
- **`$env:PYTHONPATH = ""` before every pytest run** — a polluted global PYTHONPATH on the primary machine shadows the `.venv` install and produces `ModuleNotFoundError: pydantic_core._pydantic_core`.
- **The full suite can exceed 10 minutes locally** (live NREL API tests run when `NREL_API.env` exists). Use the scoped per-phase commands; run the full suite once at the end, expecting only the Known-red baseline failures.
- **`reports/*.md` are tracked; `reports/*.html` are git-ignored** — the PHASE-03 memo must be markdown.
- **Regime keys are load-bearing:** `decree57_rooftop_50pct_draft` and `decision_963_2026_current` are referenced by name in Python and Julia tests; add regimes, never rename or remove them.

## Verification Strategy

- **TEST-001 (PHASE-02):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/reopt tests/python/integration/test_settlement_presets.py tests/python/webapp/test_golden_parity.py -q` → `0 failed`.
- **TEST-002 (PHASE-02):** `.\tests\run_all_tests.ps1 -Layer 3` → Layer-3 cross-validation PASS (exact Julia↔Python match), or ASM-003 waiver recorded.
- **TEST-003 (PHASE-02):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -c "from reopt_pysam_vn.reopt.preprocess import load_vietnam_data; print(load_vietnam_data().export_rules['rooftop_solar']['max_export_fraction'])"` → prints `0.5`.
- **TEST-004 (PHASE-03):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/reopt/test_decree243_export_cap_delta.py -q` → all pass including `delta_surplus_revenue_vnd == 176_338_800.0` on the toy profile.
- **TEST-005 (PHASE-03):** `.venv\Scripts\python.exe scripts/python/reopt/decree243_export_cap_delta.py` → exit 0; `reports/2026-07-18-decree243-export-cap-delta.md` exists and contains a non-negative `delta_surplus_revenue_vnd`.
- **TEST-006 (PHASE-04):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python/webapp -q` → `0 failed`; `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` → clean.
- **TEST-007 (all phases, final):** `$env:PYTHONPATH = ""; .venv\Scripts\python.exe -m pytest tests/python -q` → no failures beyond the Known-red baseline list in Environment & Conventions (or `0 failed` if the 2026-07-17 sprint landed first).
- **MANUAL-001 (PHASE-04):** Launch the webapp, open a completed run: the "About this run" card shows solver and `policy_data_versions` including `export_rules: 2026.1` for any run created after PHASE-02 — the provenance chain proving which regulatory vintage produced the numbers.
- **OBS-001 (PHASE-01/02):** `git ls-files plans/ research/ | grep 2026-07-1` lists the four planning documents; `git log --oneline -5` shows the phase commits; `docs/regulatory-watch.md` export_rules row reads CURRENT after PHASE-02.

## Risks and Alternatives

- **RISK-001:** Downstream consumers (deck pipelines, case modules) silently pick up the 50% default and produce numbers inconsistent with previously published decks. Mitigation: the delta memo (PHASE-03) quantifies and documents the direction; `decree_57_2025_legacy` reproduces old numbers on demand; `activeContext.md` records the flip date; provenance `policy_data_versions` distinguishes vintages for webapp runs.
- **RISK-002:** The two-part-tariff and CI-truth work in `plans/2026-07-17-truth-and-correctness-sprint-plan.md` touches overlapping files (`activeContext.md`, `docs/pitfalls.md`, test trees). Mitigation: execute the two plans sequentially, never interleaved; this plan's edits are additive and localized.
- **ALT-001:** Edit `vn_export_rules_decree57.json` in place to 0.50 — rejected: violates the repo's versioning policy (old files preserved for reproducibility) and would silently change any historical rerun.
- **ALT-002:** Add a `decree_243_2026_current` regime instead of flipping the base file — rejected: the enacted law is the new baseline, not a scenario; regimes are for alternatives (the legacy 20% world is the scenario now). Also keeps `DEFAULT_REGIME_ID` and every existing regime working unchanged.
- **ALT-003:** Re-optimize Saigon18 under the 50% cap for the memo — rejected for this plan: requires the NREL API or Julia solver plus fresh artifacts; the fixed-dispatch first-order number is available deterministically from tracked inputs today, and the memo flags re-optimization as follow-on.
- **ALT-004:** Auto-requeue interrupted webapp runs — rejected per DEC-004 (silent NREL quota spend on abandoned runs); an explicit error with a clone hint keeps the user in control.

## Suggested Next Step

Execute PHASE-01 (minutes, pure preservation), then PHASE-02 — its exit criteria (scoped pytest gate, golden parity, Layer-3 cross-validation) are independently verifiable before PHASE-03's memo or PHASE-04's webapp work begins. If the 2026-07-17 truth-and-correctness sprint has not yet run, prefer running it between PHASE-01 and PHASE-02 of this plan so both land on an honest green gate.
