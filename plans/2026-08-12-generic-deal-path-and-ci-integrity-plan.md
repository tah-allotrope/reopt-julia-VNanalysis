---
title: "Generic Deal Path and CI Integrity"
date: "2026-08-12"
status: "complete"
request: "Implement the roadmap from research/2026-08-12-reopt-pysam-generic-deal-path-brainstorm.md — Theme J (regulatory reviews + offsite 500 fix + CI skip visibility), Theme K (dependency constraints + scheduled CI), Theme L (generic deal path: market-price data file, shared market reference, generic_vn_dppa fallback orchestrator, extracted-inputs schema validation), Theme M (auditable test surface)."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-08-12-reopt-pysam-generic-deal-path-brainstorm.md"
  - "research/2026-08-06-reopt-pysam-gate-integrity-brainstorm.md"
---

# Plan: Generic Deal Path and CI Integrity

## Objective

Make `reopt_pysam_vn.analysis` able to analyse an **arbitrary** Vietnamese
offsite/DPPA deal instead of only the two historical deals hard-registered in its
orchestrator table, and close the three verified defects that make the current
"green" signal weaker than it looks: a CI invariant that turns red on 2026-08-19
with no code change, a reproducible HTTP 500 on the second registered deal, and
26 tests that silently skip in CI. The generic path is the unlock — the web app
already offers a free-text **Case id** field and an error hint promising "the
generic runner", and neither is true today.

## Context Snapshot

- **Current state:** `run_offsite_dppa` resolves an orchestrator from a two-entry
  registry (`DPPA_SAMSUNG_TTC`, `DPPA_CASE_1_NINHSIM`); any other `case` value
  returns an error. `run_onsite` is genuinely generic. Every building block for a
  generic offsite run already exists and is tested (hourly settlement, contract
  params resolved from the policy data layer, strike sweep, PVWatts generation,
  load synthesis, 8760 TOU tariff) except one: there is **no market-reference
  (FMP/CFMP) price series** anywhere in `data/vietnam/`, and the only synthesis
  method is buried inside the 1,491-line `integration/dppa_case_2.py` and keyed
  off per-deal data. CI is green (`ruff`, `mypy`, `pytest` all pass) but runs
  only on push, reports 627 passed / 26 skipped where a local run reports 653
  passed / 0 skipped, and `docs/regulatory-watch.md` carries three rows that
  expire 2026-08-18 against an invariant test that fails on overdue rows.
- **Desired state:** a `GENERIC_VN_DPPA` fallback orchestrator answers any
  unregistered `case` with a `directional`-flagged result; the market reference
  is a versioned data-layer file behind `data/vietnam/manifest.json`; the offsite
  path works end-to-end through both the CLI and the web API; CI runs on a weekly
  schedule against a pinned constraints file, prints every skip reason, and fails
  if the skip count exceeds a declared budget.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/analysis/` (`offsite_dppa.py`,
  `__main__.py`, `types.py`, `validation.py`, `orchestrators/`),
  `src/python/reopt_pysam_vn/integration/` (`settlement.py`, `dppa_case_2.py`,
  `strike_search.py`), `src/python/reopt_pysam_vn/webapp/`
  (`service.py`, `routes/api.py`, `errors.py`),
  `src/python/reopt_pysam_vn/reopt/preprocess.py` (`VNData`,
  `load_vietnam_data`), `data/vietnam/` (policy data + `manifest.json`),
  `data/schemas/`, `docs/regulatory-watch.md`, `.github/workflows/ci.yml`,
  `tests/python/`.
- **Out of scope:** rotating the historically committed NREL API key (an
  out-of-band human action, tracked in `README.md`); reviving the Julia path in
  `legacy/julia/`; consolidating the 36 report-generator scripts onto
  `assets/report-template.html`; the web-app-to-PPTX deck export; any change to
  `examples/samsung-ttc_combined-decision.example.json`; optimising the
  settlement engine (measured at 23 ms per settlement — it is not a bottleneck).

## Environment & Conventions

- **Stack:** Python 3.10+ (`requires-python = ">=3.10"`), setuptools packaging
  with `package-dir = {"" = "src/python"}`. Runtime deps: `nrel-pysam==7.1.0`
  (the only pinned runtime dep), `pandas>=2.0`, `numpy-financial>=1.0`,
  `matplotlib>=3.8`, `openpyxl>=3.1`, `requests>=2.31`. Optional extras:
  `webapp` (FastAPI, uvicorn, jinja2, python-multipart, httpx) and `dev`
  (`ruff==0.16.1`, `mypy==2.3.0`, `pytest==8.4.2`, `pytest-cov==7.1.0`).
  A Julia layer exists under `legacy/julia/` but is not on the primary path and
  is not exercised by CI.
- **Setup:**
  ```bash
  python -m pip install -e ".[webapp,dev]"
  ```
  The repository has a local virtualenv at `.venv` (Python 3.12) that already
  contains PySAM. On Windows invoke it as `.venv\Scripts\python.exe`; on
  Linux/macOS as `.venv/bin/python`. Every command below is written with a bare
  `python`; substitute the interpreter path if the venv is not activated.
- **Build / Run:** there is no build step (pure Python, editable install).
  Run the analysis CLI with
  `python -m reopt_pysam_vn.analysis offsite_dppa --config <deal.json> --extracted <extracted.json>`.
  Run the internal web UI with
  `PYTHONPATH=src/python python -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000`.
- **Test:** full portable suite exactly as CI runs it:
  ```bash
  PYTHONPATH= python -m pytest tests/python \
    -m "not network and not requires_artifacts and not golden_machine and not requires_julia" \
    -q --cov=reopt_pysam_vn --cov-report=term-missing
  ```
  Single test:
  ```bash
  python -m pytest tests/python/analysis/test_offsite_dppa.py::test_run_offsite_dppa_uses_injected_orchestrator -v
  ```
  Lint and type gates (both are CI steps and must pass):
  ```bash
  ruff check src scripts tests
  mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp
  ```
  **Baseline before any work in this plan:** `653 passed, 19 deselected, 3 xfailed`
  locally in ~108 s at 85 % coverage; `627 passed, 26 skipped, 19 deselected,
  3 xfailed` in CI at 84 %. Any phase that changes these counts must say so in
  its exit criteria.
- **Conventions & traps:**
  - **Currency:** all VND figures are **VND per kWh** unless the identifier says
    `_vnd_per_mwh` or `_vnd`. The canonical VND/USD exchange rate is resolved
    from `data/vietnam/vn_deal_defaults_2026.json` through
    `reopt_pysam_vn.common.assumptions.exchange_rate()`. **Never write a bare FX
    literal in new code.** Two documented exception classes exist and must not be
    "cleaned up": `integration/dppa_samsung_ttc.py` (pinned to keep a golden
    stable) and the Saigon18 25,450 VND/USD contract basis.
  - **Time series:** every hourly series is exactly **8760** floats (no leap-day
    handling). `integration/settlement._pad_to_8760` truncates longer input and
    zero-pads shorter input — do not rely on it to catch a wrong-length series.
  - **Data layer:** every file in `data/vietnam/` uses a `{"_meta": {...},
    "data": {...}}` envelope; `load_vietnam_data()` reads only the `data` block
    and raises `KeyError` if it is absent. Policy updates are made by adding a
    **new versioned file** and repointing one key in
    `data/vietnam/manifest.json` — never by editing an active file's numbers in
    place.
  - **Assumption resolution order** (from `common/assumptions.py`, and binding on
    new code): (1) explicit function argument, (2) per-deal value in the deal's
    `*_extracted_inputs.json`, (3) regime-resolved data layer via
    `resolve_vietnam_regime(vn, regime_id)`, (4) `vn_deal_defaults_2026.json`.
    There is no step 5 — no module-level literals.
  - **JSON reads** use `encoding="utf-8-sig"` throughout (Windows BOM tolerance).
  - **Lint:** `ruff` 0.16.1 with `line-length = 120`, `target-version = "py310"`,
    `ignore = ["E402", "ISC004"]`, and `extend-exclude` covering `.venv`,
    `legacy`, `artifacts`, `present`. Run `ruff check --fix` before committing.
  - **Types:** `mypy` runs only over `reopt_pysam_vn.analysis.*` and
    `reopt_pysam_vn.webapp.*`, where `disallow_untyped_defs = true`. Any new
    function in those two packages needs full annotations. `integration`,
    `reopt`, and `pysam` are internal engines and are not type-gated.
  - **Public API boundary:** `analysis` and `webapp` are the supported surfaces
    (`py.typed`). `integration`, `reopt`, `pysam` may change shape freely. New
    external-facing code depends on `analysis`.
  - **Test markers** (declared in `pyproject.toml`, excluded by CI):
    `network`, `requires_artifacts`, `golden_machine`, `requires_julia`.
  - **Windows-first repo.** Prefer commands that work in both `bash` and
    PowerShell; where a shell builtin differs, the plan gives the `bash` form.
  - **`PYTHONPATH` gotcha:** an unrelated global `PYTHONPATH` on the primary dev
    machine can shadow the repo venv and break webapp tests with
    `ModuleNotFoundError: pydantic_core._pydantic_core`. Always run pytest with
    `PYTHONPATH=` cleared, as the commands above do.
- **Repo map:**
  ```
  data/vietnam/            versioned policy data + manifest.json (7 keys today)
  data/schemas/            deal_config.schema.json (validated), extracted_inputs.schema.json (unused)
  data/interim/<deal>/     per-deal *_extracted_inputs.json  (the offsite input layer)
  src/python/reopt_pysam_vn/
    analysis/              PUBLIC API: DealConfig, run_onsite, run_offsite_dppa, CLI, orchestrators/
    common/                assumptions.py (canonical resolver) + 3 unused stub modules
    integration/           settlement.py (generic engine) + 5 bespoke per-deal modules
    pysam/                 PVWatts + Single Owner finance
    reopt/                 preprocess.py (VNData, tariff series, Vietnam defaults)
    webapp/                FastAPI localhost UI: service.py, routes/, jobs.py, storage.py
  scripts/python/{reopt,pysam,integration}/   workflow scripts (~31k lines, not coverage-measured)
  tests/python/{analysis,common,ingestion,integration,pysam,reopt,webapp}/
  .github/workflows/ci.yml  3.10 + 3.12 matrix: ruff -> mypy -> pytest
  ```

## Research Inputs

- From `research/2026-08-12-reopt-pysam-generic-deal-path-brainstorm.md`:
  - Three rows in `docs/regulatory-watch.md` (`tech_costs`, `financials`,
    `emissions`) carry `Next review = 2026-08-18`. `tests/python/test_repo_invariants.py::test_regulatory_watch_rows_are_not_overdue`
    fails when any row's date is in the past, so the suite goes red on
    2026-08-19. CI triggers on `push`/`pull_request` only, so the failure will
    attach to whatever unrelated commit lands next.
  - The `DPPA_CASE_1_NINHSIM` orchestrator requires `results` and `scenario`,
    but `webapp/service.run_analysis` never forwards them and the CLI has no
    `--results`/`--scenario` flags. Reproduced: `POST /api/runs` with
    `{"deal_config": {"case": "DPPA_CASE_1_NINHSIM", "mode": "offsite_dppa"}, "extracted": {...}, "results": {...}}`
    raises a bare `ValueError` past `except service.AnalysisError`, yielding a
    500 and leaving the run persisted in `state: "queued"` until the next app
    restart mislabels it "interrupted by an app restart".
  - Same commit, same marker filter: local `653 passed, 0 skipped`; CI
    `627 passed, 26 skipped`. The 26 are runtime `pytest.skip("… not available")`
    guards (49 such sites exist), invisible because CI runs `pytest -q` with no
    `-rs`. Four are `pytest.skip("No NREL API key available")` in
    `tests/python/reopt/test_integration.py` at lines 283, 315, 357, 441.
  - Every generic building block for an offsite run exists and is tested; the one
    missing input is a market-reference price series. `data/vietnam/manifest.json`
    has seven keys and none is market prices. Samsung's extracted file carries no
    market series at all; the only synthesis method is
    `dppa_case_2.build_dppa_case_2_market_proxy` ("hourly EVN tariff scaled by
    weighted wholesale ratio"), whose ratio comes from
    `extracted["benchmark"]["wholesale_rate_vnd_per_kwh"]`.
  - `data/schemas/extracted_inputs.schema.json` is referenced by nothing in
    `src/`, `scripts/`, or `tests/`, and **all five** tracked
    `*_extracted_inputs.json` files violate its `required` list — so it cannot be
    switched on as-is.
  - The settlement engine is not a performance problem: 23.1 ms per
    `compute_hourly_settlement`, 0.49 s for a 21-point `run_strike_sweep`.
- From `research/2026-08-06-reopt-pysam-gate-integrity-brainstorm.md`:
  - The eleven-day CI outage was caused by an **unpinned gate tool** (ruff)
    expanding its default rule set. The fix pinned the four gate tools in a `dev`
    extra; the ten runtime dependencies remain `>=` with no lockfile, so the same
    failure mode is still open on `pandas`, `numpy-financial`, `fastapi` and the
    rest.
  - "Local green and CI green are different claims" — work is reported complete
    only after `gh run list --limit 3` shows success on both matrix legs.
  - `CON-002` (the web app must never fork analytics) is enforced by
    `tests/python/webapp/test_golden_parity.py::test_samsung_ttc_web_api_matches_direct_library_call_bit_exact`,
    which does run in CI. It must keep passing through every refactor here.

## Assumptions and Constraints

- **ASM-001:** The executor may not have network access to Vietnamese regulatory
  primary sources when performing the PHASE-01 review. — **BINDING DEFAULT:** for
  any row that cannot be confirmed against a named primary source (a decision,
  decree, circular, or the issuing body's published figure), do **not** write a
  new `Last verified` date. Instead set that row's `Status` cell to
  `UNVERIFIED (pending primary-source check)`, set `Next review` to today's date
  plus 30 days, and append one sentence to the prose block under the table naming
  what was attempted. Never bump `Last verified` without a source.
- **ASM-002:** No published hourly Vietnamese FMP/CFMP series is available to
  commit to the repository. — **BINDING DEFAULT:** `vn_market_prices_2026.json`
  ships with `data.hourly_shape_24 = null` and a scalar
  `data.proxy.wholesale_reference_vnd_per_kwh = 671.0` (the surplus purchase rate
  already carried in `vn_export_rules_2026_decree243.json`, in VND per kWh),
  `data.proxy.method = "hourly_evn_tariff_scaled_by_wholesale_ratio"`, and
  `_meta.status = "PROXY — no published hourly FMP/CFMP series ingested"`. Any
  result built on it is flagged `market_reference_price_type = "proxy_cfmp_or_fmp"`.
- **ASM-003:** The exact set of 26 tests that skip in CI is not known from
  outside CI. — **BINDING DEFAULT:** PHASE-01 adds `-rs` so one CI run enumerates
  them; PHASE-03 then converts exactly those enumerated tests, and no others.
  Do not guess the list from local inspection.
- **ASM-004:** A `pip freeze` constraints file generated on Python 3.12 may pin
  wheels that do not resolve on Python 3.10. — **BINDING DEFAULT:** generate
  `constraints-ci.txt` on **Python 3.10** (the repo's declared floor) and verify
  both matrix legs install. If a single package cannot satisfy both, drop that
  one line from the constraints file and add a `#` comment above the gap naming
  the package and the conflict.
- **ASM-005:** A brand-new deal's buyer load may arrive as an 8760 upload or as
  an annual total only. — **BINDING DEFAULT:** the generic orchestrator requires
  `extracted["loads_kw"]` with exactly 8760 values and raises
  `OrchestratorInputError` otherwise. Synthesising a load from an annual total is
  explicitly out of scope for this plan (`reopt_pysam_vn.ingestion.synthesize`
  already exists for callers that want it upstream).
- **ASM-006:** New deals will frequently have no cached PVWatts solar resource
  file and no NREL API key. — **BINDING DEFAULT:** the generic orchestrator
  prefers, in order, (1) an explicit `extracted["generation_kw"]` 8760 series,
  (2) PySAM PVWatts against a cached resource for the site coordinates,
  (3) a deterministic synthetic profile — and records which one ran in
  `quality.solar_profile_source`. It never fetches over the network.
- **CON-001:** `examples/samsung-ttc_combined-decision.example.json` is not to be
  modified, regenerated, or deleted by any phase of this plan.
- **CON-002:** The web app must never fork analytics logic — it calls
  `run_onsite` / `run_offsite_dppa` as-is.
  `tests/python/webapp/test_golden_parity.py::test_samsung_ttc_web_api_matches_direct_library_call_bit_exact`
  enforces this and must pass unchanged after every phase.
- **CON-003:** `integration.settlement.ContractParams` has ~24 call sites across
  14 files. No existing field may be renamed, removed, or made required. New
  behaviour is added through `ContractParams.from_regime(..., **overrides)`,
  which already exists for this purpose.
- **CON-004:** Numeric outputs for the two currently registered deals
  (`DPPA_SAMSUNG_TTC`, `DPPA_CASE_1_NINHSIM`) must be **bit-identical** before
  and after PHASE-04's market-reference refactor. That refactor is
  value-preserving by construction: the shared helper reads per-deal data first
  and only falls back to the data layer when the deal supplies nothing.
- **CON-005:** No test may place a live call to the NREL API. The web-app test
  suite enforces this with an autouse fixture in
  `tests/python/webapp/conftest.py`; new tests elsewhere must not regress it.
- **DEC-001:** The next generalisation increment is a **generic fallback
  orchestrator**, not a third hard-registered historical deal. Two registered
  implementations already exist, which is the sample needed to abstract from.
- **DEC-002:** The market reference belongs in `data/vietnam/` behind
  `manifest.json` with a `docs/regulatory-watch.md` row — not in code and not in
  a per-deal extracted file.
- **DEC-003:** Orchestrator input errors are raised as a typed
  `OrchestratorInputError` (a `ValueError` subclass) so the web layer can map
  them to HTTP 422 without broadening an `except` clause to bare `ValueError`,
  which would also swallow genuine programming errors.
- **DEC-004:** The generic orchestrator is the registry **fallback** (any
  unregistered `case` routes to it), and the resolved orchestrator name is echoed
  in the result's `quality.orchestrator` field so no reader is left guessing what
  ran.
- **DEC-005:** `data/schemas/extracted_inputs.schema.json` is corrected to
  describe the files that actually exist before it is switched on. Its `required`
  list is reduced to `["loads_kw"]`; everything else becomes documented-optional
  and is validated for type and length only when present.

## Specification

### S1 — Orchestrator resolution and keyword forwarding

`run_offsite_dppa(deal_config, *, extracted, results, scenario, combined_decision_fn, run_developer)`
resolves and invokes an orchestrator by these numbered steps:

1. Resolve `extracted`: first non-`None` of (a) the `extracted=` argument,
   (b) `deal_config.raw["extracted"]`. If both are `None`, raise
   `OrchestratorInputError`.
2. Resolve `results` and `scenario` by the same two-step rule. `None` is legal
   for both.
3. Choose the orchestrator: (a) an explicit `combined_decision_fn=` argument,
   else (b) `_ORCHESTRATORS[deal_config.case]` when that key exists, else
   (c) the generic fallback `_GENERIC_ORCHESTRATOR`.
4. Build the candidate keyword set
   `{"run_developer": run_developer, "results": results, "scenario": scenario, "deal_config": deal_config}`,
   drop `results`/`scenario` when they are `None`, then filter the remainder to
   the parameter names the chosen callable actually accepts, using
   `inspect.signature`. A callable declaring `**kwargs` receives all of them.
5. Call `fn(extracted, **filtered_kwargs)` and wrap the returned dict with
   `OffsiteDppaResult.from_dict`.

Step 4 replaces the current ad-hoc "forward only when not `None`" branching and
is what lets the generic orchestrator receive `deal_config` while the two
existing orchestrators, which do not declare it, keep their exact call shape.

### S2 — Market reference series

The market reference is an 8760 series in **VND per kWh**, resolved in this
order, stopping at the first hit:

1. `extracted["cfmp_vnd_per_mwh"]` — an actual hourly CFMP series; divide every
   element by 1,000 to convert VND/MWh to VND/kWh. Label
   `market_reference_price_type = "cfmp"`.
2. `extracted["fmp_vnd_per_mwh"]` — an actual hourly FMP series; same conversion.
   Label `"fmp"`.
3. The proxy. Label `"proxy_cfmp_or_fmp"`.

The proxy is, for every hour *h*:

```
market[h] = retail[h] × ratio
ratio     = wholesale_reference ÷ weighted_retail
```

| Symbol | Meaning | Units | Source |
|---|---|---|---|
| `market[h]` | proxy market reference price in hour *h* | VND/kWh | computed |
| `retail[h]` | EVN retail tariff in hour *h* | VND/kWh | `extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]` |
| `wholesale_reference` | wholesale price benchmark | VND/kWh | `extracted["benchmark"]["wholesale_rate_vnd_per_kwh"]`, else `vn_market_prices_2026.json` → `data.proxy.wholesale_reference_vnd_per_kwh` |
| `weighted_retail` | load-weighted average retail price | VND/kWh | `extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"]` |
| `ratio` | dimensionless scaling factor | — | computed; `0.0` when `weighted_retail == 0` |

This reproduces `dppa_case_2.build_dppa_case_2_market_proxy` exactly for any deal
whose `extracted` carries both benchmark fields, which is why the refactor is
value-preserving (CON-004). The data-layer fallback only engages when
`wholesale_rate_vnd_per_kwh` is absent or zero.

### S3 — Generic offsite artifact assembly

Given `extracted` and `deal_config`, the generic orchestrator produces the
`OffsiteDppaResult` block vocabulary in these numbered steps:

1. **Load:** `loads_kw = extracted["loads_kw"]`; raise `OrchestratorInputError`
   unless it is a list of exactly 8760 numbers (ASM-005).
2. **Generation:** the first available of `extracted["generation_kw"]` (8760
   list), a PVWatts run for `extracted["site"]["latitude"]/["longitude"]`, or a
   deterministic synthetic profile (ASM-006). When
   `deal_config.contract["annual_solar_gwh"]` is present, calibrate the chosen
   series so its annual sum equals `annual_solar_gwh × 1e6` kWh, preserving the
   hourly shape and clamping any hour to at most the plant's AC rating
   (`deal_config.plant["capacity_mwac"] × 1000`) when that field is present.
3. **Tariff:** `extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]`,
   padded/truncated to 8760.
4. **Market reference:** S2.
5. **Contract:**
   `ContractParams.from_regime(regime_id, mode=…, strike_vnd_kwh=…, **overrides)`
   where `regime_id` is `deal_config.contract.get("regime_id", "decision_963_2026_current")`,
   `mode` is `"virtual_cfd"` when
   `deal_config.contract["settlement_mechanism"]` is `"financial_cfd"` or
   `"virtual"` and `"private_wire"` when it is `"physical"` (default
   `"virtual_cfd"` when the field is absent), and `strike_vnd_kwh` is
   `deal_config.contract["strike_vnd_per_kwh"]` (default: the weighted retail
   price from `extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"]` when
   absent). `dppa_adder_vnd_kwh` is overridden from
   `deal_config.contract["dppa_adder_vnd_per_kwh"]` when present.
6. **Base settlement:** `compute_hourly_settlement(...)` plus
   `compute_buyer_benchmark(...)`; `buyer_savings_vs_evn_vnd = evn_only_cost_vnd − buyer_cost_vnd`.
7. **Strike sweep:** `run_strike_sweep` over 21 points spanning
   `0.6 × strike` to `1.4 × strike` inclusive, in equal steps.
8. **Decision:** `{"buyer_savings_positive": savings > 0, "recommended_strike_vnd_kwh": <the largest swept strike whose buyer savings remain positive, or null>}`.
9. **Quality:** `{"basis": "directional", "orchestrator": "generic_vn_dppa",
   "market_reference_price_type": …, "solar_profile_source": …, "warnings": [...]}`.
   `adder_sensitivity` and `regime_stress` are emitted as `{}` — the generic path
   has no lever for them, and `OffsiteDppaResult.to_dict()` emits every block
   unconditionally, so `{}` is the honest representation.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Make CI self-firing, reproducible, and honest about skips; clear the dated regulatory-watch failure | None | `constraints-ci.txt`, weekly `schedule:` trigger, `-rs` + skip budget, refreshed `docs/regulatory-watch.md` |
| PHASE-02 | Fix the offsite 500: forward `results`/`scenario` through every consumer surface | None (parallel with PHASE-01) | `OrchestratorInputError`, signature-aware kwarg forwarding, CLI flags, 422 instead of 500 |
| PHASE-03 | Convert environment-dependent skips into declared markers; measure the public CLI | PHASE-01 (needs the enumerated skip list) | Two new markers, updated CI filter, in-process CLI test |
| PHASE-04 | Add the market-price data layer and a shared market-reference module | None (parallel with PHASE-01/02) | `vn_market_prices_2026.json`, `integration/market_reference.py`, `dppa_case_2` delegation |
| PHASE-05 | Ship the generic fallback orchestrator and honest extracted-inputs validation | PHASE-02, PHASE-04 | `orchestrators/generic_vn_dppa.py`, registry fallback, corrected schema + validator |

## Detailed Phases

### PHASE-01 - CI integrity: reproducible, scheduled, and honest about skips

**Goal**

Remove the 2026-08-19 time bomb, make dependency resolution reproducible so a
third-party release cannot break `main` unannounced, and make every skipped test
visible in the CI log with a budget that fails when the count grows.

**Tasks**

- [ ] TASK-01-01: Review the three overdue rows in `docs/regulatory-watch.md`
      (`tech_costs`, `financials`, `emissions`) against primary sources. For each
      confirmed row set `Last verified` to today's date (`YYYY-MM-DD`) and
      `Next review` to today plus six months. Apply ASM-001 for any row that
      cannot be confirmed.
- [ ] TASK-01-02: Append one sentence per reviewed row to the prose block below
      the table naming the source consulted (for example "MONRE grid emission
      factor study, <year>"), mirroring the existing `tariff` row sentence.
- [ ] TASK-01-03: Create `constraints-ci.txt` from a clean Python 3.10
      environment (ASM-004):
      ```bash
      python3.10 -m venv /tmp/reopt-constraints
      /tmp/reopt-constraints/bin/python -m pip install --upgrade pip
      /tmp/reopt-constraints/bin/python -m pip install -e ".[webapp,dev]"
      /tmp/reopt-constraints/bin/python -m pip freeze --exclude-editable > constraints-ci.txt
      ```
      On Windows use `py -3.10 -m venv C:\Temp\reopt-constraints` and
      `C:\Temp\reopt-constraints\Scripts\python.exe` for the three following
      commands.
- [ ] TASK-01-04: Add a header comment block to the top of `constraints-ci.txt`
      stating what it is, that it is generated on Python 3.10, the exact
      regeneration command, and that upgrading a dependency means regenerating
      this file in its own commit.
- [ ] TASK-01-05: Point the CI install step at the constraints file and add a
      weekly schedule trigger.
- [ ] TASK-01-06: Add `-rs` to the CI pytest step so every skip prints its reason.
- [ ] TASK-01-07: Create `tests/conftest.py` implementing the skip budget: count
      skipped test reports and fail the session when the count exceeds the value
      of the `REOPT_PYSAM_VN_MAX_SKIPS` environment variable. When the variable is
      unset, the budget is not enforced (so local runs are unaffected).
- [ ] TASK-01-08: Set `REOPT_PYSAM_VN_MAX_SKIPS: "26"` in the CI pytest step's
      `env:` block — the current observed CI count, so the number cannot drift
      upward unnoticed. PHASE-03 lowers it.

**File Changes**

- `docs/regulatory-watch.md` (modify): update the `Last verified` / `Next review`
  / `Status` cells for the `tech_costs`, `financials`, and `emissions` rows only;
  extend the prose block below the table. Leave the `tariff`, `export_rules`,
  `regimes`, and `deal_defaults` rows untouched — their dates are not due.
- `constraints-ci.txt` (create): pip-freeze output at repo root, plus the header
  comment from TASK-01-04.
- `.github/workflows/ci.yml` (modify): add a `schedule:` trigger alongside the
  existing `push`/`pull_request`; change the install line from
  `pip install -e ".[webapp,dev]"` to
  `pip install -e ".[webapp,dev]" -c constraints-ci.txt`; add `-rs` to the pytest
  command; add `REOPT_PYSAM_VN_MAX_SKIPS: "26"` to that step's existing `env:`
  block (which already sets `PYTHONPATH: ""`). Do not change the matrix, the
  marker filter, or the ruff/mypy steps.
  The schedule block is:
  ```yaml
  on:
    push:
    pull_request:
    schedule:
      - cron: "0 2 * * 1"   # Mondays 02:00 UTC — catches date-based invariants
                            # and dependency drift between pushes
  ```
- `tests/conftest.py` (create): the skip-budget hooks. This is the first
  repo-root test conftest; it applies to the whole `tests/` tree.
- `.gitignore` (modify): no change needed — verify `constraints-ci.txt` is **not**
  matched by any existing pattern before committing, with
  `git check-ignore -v constraints-ci.txt` (expected: no output, exit code 1).

**Function Signatures**

- `pytest_runtest_logreport(report: pytest.TestReport) -> None` — pytest hook in
  `tests/conftest.py`; increments a module-level skip counter when
  `report.skipped` is truthy and `report.when == "setup"` (a skipped test emits
  exactly one setup-phase skipped report, so this counts each test once).
- `pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None` —
  pytest hook; when `REOPT_PYSAM_VN_MAX_SKIPS` is set and the counted skips
  exceed it, prints
  `SKIP BUDGET EXCEEDED: <n> skipped, budget <m>` to stderr and sets
  `session.exitstatus = 1`.

**Test Specs**

- Run the full portable suite with the budget deliberately set below the local
  count:
  `REOPT_PYSAM_VN_MAX_SKIPS=0 PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q`
  → exit code `0` locally, because a local run skips 0 tests. This confirms the
  hook does not fire spuriously.
- Run a single deliberately-skipped test with a zero budget:
  `REOPT_PYSAM_VN_MAX_SKIPS=0 python -m pytest tests/python/reopt/test_integration.py -q -k nlr_domain_connectivity`
  → when that test skips, exit code `1` and `SKIP BUDGET EXCEEDED: 1 skipped, budget 0`
  on stderr; when it runs and passes, exit code `0`.
- With `REOPT_PYSAM_VN_MAX_SKIPS` unset, the same command → exit code `0`
  regardless of skips (budget disabled).
- `python -m pytest tests/python/test_repo_invariants.py::test_regulatory_watch_rows_are_not_overdue -v`
  → `PASSED`, and every `Next review` cell in the table parses as a date at least
  30 days in the future.

**Dependencies**

- None. This phase touches only CI configuration, a test conftest, and a docs
  table; it can run in parallel with PHASE-02 and PHASE-04.

**Exit Criteria**

- [ ] `git check-ignore -v constraints-ci.txt` produces no output (the file is
      tracked, not ignored) and `git ls-files constraints-ci.txt` prints the path.
- [ ] `python -m pytest tests/python/test_repo_invariants.py -q` → all tests pass
      and no row's `Next review` is within 30 days.
- [ ] `gh run list --limit 3` shows the latest `main` run `success` on **both**
      matrix legs (`test (3.10)` and `test (3.12)`).
- [ ] The CI log for that run contains a `SKIPPED` reason block (the `-rs`
      output) listing each skipped test and its reason. **Copy that list into the
      commit message or a scratch note — PHASE-03 consumes it (ASM-003).**
- [ ] The CI pytest summary still reads `627 passed, 26 skipped, 19 deselected,
      3 xfailed` (unchanged counts; this phase changes visibility, not selection).

**Phase Risks**

- **RISK-01-01:** The constraints file pins a version that fails to resolve on
  one matrix leg. Mitigation: ASM-004 — generate on 3.10, and if a single package
  conflicts, drop that one line with an explanatory comment rather than
  abandoning the file.
- **RISK-01-02:** `pytest_sessionfinish` setting `session.exitstatus` interacts
  with `pytest-cov`'s own exit handling. Mitigation: the two test-spec commands
  above exercise both the firing and non-firing paths under the same
  `--cov` flags CI uses; run them before pushing.
- **RISK-01-03:** A scheduled workflow run only executes on the repository's
  default branch, and GitHub disables schedules on repositories with no activity
  for 60 days. Mitigation: note this in the `cron` comment; the weekly run is a
  safety net, not the primary trigger.

### PHASE-02 - Fix the offsite consumer surfaces

**Goal**

Make the already-registered `DPPA_CASE_1_NINHSIM` deal reachable end-to-end: the
web API and the CLI must both be able to hand an orchestrator the `results` and
`scenario` it requires, and a missing input must produce a clean HTTP 422 with a
run marked `error`, never a 500 with a run stranded in `queued`.

**Tasks**

- [ ] TASK-02-01: Add `OrchestratorInputError(ValueError)` to
      `analysis/offsite_dppa.py`, export it in `__all__`, and re-export it from
      `analysis/__init__.py`.
- [ ] TASK-02-02: Replace the two bare `ValueError` raises in
      `analysis/orchestrators/dppa_case_1.py` (missing `results`, missing
      `scenario`) and the missing-`extracted` raise in
      `analysis/offsite_dppa.run_offsite_dppa` with `OrchestratorInputError`,
      keeping every message string byte-identical so existing assertions and user
      guidance are unchanged.
- [ ] TASK-02-03: Implement signature-aware keyword forwarding in
      `run_offsite_dppa` per S1 step 4, replacing the current `if results is not
      None` / `if scenario is not None` block.
- [ ] TASK-02-04: Add a `scenario` parameter to
      `webapp/service.run_analysis` and forward both `results` and `scenario`
      into `run_offsite_dppa` from `_run_offsite()`. Wrap the call so
      `OrchestratorInputError` is re-raised as `service.MissingInputsError`
      preserving the original message.
- [ ] TASK-02-05: Thread `scenario` through `webapp/routes/api.py`:
      `_submit_deal_config` gains a `scenario` keyword, `create_run` reads
      `payload.get("scenario")`, and both pass it to `service.run_analysis`.
- [ ] TASK-02-06: Add `--results` and `--scenario` options to the
      `offsite_dppa` subcommand in `analysis/__main__.py` and pass the loaded
      dicts to `run_offsite_dppa`.
- [ ] TASK-02-07: Update the module docstring of `webapp/service.py` to state
      that `results`/`scenario` are now forwarded, replacing the sentence that
      says they "may … be added to the submission payload and forwarded here in a
      future change".

**File Changes**

- `src/python/reopt_pysam_vn/analysis/offsite_dppa.py` (modify): add the
  exception class; import `inspect`; implement S1 step 4. Keep
  `_resolve_input`, the registry, `register_orchestrator`, and the docstring's
  input-resolution description intact (update the paragraph describing
  conditional forwarding to describe signature filtering instead).
- `src/python/reopt_pysam_vn/analysis/__init__.py` (modify): import and re-export
  `OrchestratorInputError`; add it to `__all__` in alphabetical position. Leave
  `_register_offsite_orchestrators` untouched.
- `src/python/reopt_pysam_vn/analysis/orchestrators/dppa_case_1.py` (modify):
  swap the two raise types only.
- `src/python/reopt_pysam_vn/analysis/__main__.py` (modify): add the two CLI
  options and pass them through `_cmd_offsite_dppa`. Leave `_cmd_onsite` alone.
- `src/python/reopt_pysam_vn/webapp/service.py` (modify): `run_analysis` gains
  `scenario: dict[str, Any] | None = None`; `_run_offsite` forwards `results` and
  `scenario` and translates `OrchestratorInputError`. Leave the
  `OrchestratorNotRegisteredError` pre-check in place for now — PHASE-05 changes
  it.
- `src/python/reopt_pysam_vn/webapp/routes/api.py` (modify): thread `scenario`
  through `_submit_deal_config` and `create_run`. Leave the multipart form
  endpoint unchanged (the guided form does not submit REopt results).
- `tests/python/analysis/test_offsite_dppa_case_1.py` (modify): add the two
  error-type assertions below.
- `tests/python/webapp/test_api_runs.py` (modify): add the two web-path tests
  below.
- `tests/python/analysis/test_cli.py` (modify): add the CLI flag test below.

**Function Signatures**

- `class OrchestratorInputError(ValueError)` — raised when an orchestrator's
  required inputs are missing; carries the same human-readable message as the
  previous bare `ValueError`.
- `_supported_kwargs(fn: CombinedDecisionFn, candidates: dict[str, Any]) -> dict[str, Any]`
  — returns the subset of `candidates` whose keys `fn` accepts as keyword
  parameters; returns `candidates` unchanged when `fn` declares `**kwargs`.
- `run_analysis(deal_config: DealConfig, *, results: dict[str, Any] | None = None, scenario: dict[str, Any] | None = None, extracted: dict[str, Any] | None = None, run_developer: bool = True) -> dict[str, Any]`
  — unchanged return contract; `scenario` is new and is forwarded only to the
  offsite branch.
- `_submit_deal_config(request: Request, deal_config_dict: dict[str, Any], *, results: dict[str, Any] | None = None, scenario: dict[str, Any] | None = None, extracted: dict[str, Any] | None = None, force_resolve: bool = False) -> str`
  — returns the created `run_id`.

**Test Specs**

- `run_offsite_dppa(DealConfig.from_dict({"case": "DPPA_CASE_1_NINHSIM", "mode": "offsite_dppa"}), extracted=<ninhsim extracted>, scenario=<ninhsim scenario>)`
  with no `results` → raises `OrchestratorInputError` whose message starts
  `run_offsite_dppa for DPPA_CASE_1_NINHSIM needs \`results\``.
- Same call with `results=` supplied but no `scenario=` → raises
  `OrchestratorInputError` naming `` `scenario` ``.
- `isinstance(OrchestratorInputError("x"), ValueError)` → `True` (existing
  callers that catch `ValueError` keep working).
- Web path, happy: `POST /api/runs` with
  `{"deal_config": {"case": "DPPA_CASE_1_NINHSIM", "mode": "offsite_dppa", "title": "t"}, "extracted": <ninhsim extracted>, "results": <synthetic results>, "scenario": <ninhsim scenario>}`
  → HTTP `202`; then `GET /api/runs/{run_id}` → `body["status"]["state"] == "done"`
  and `body["result"]["case"] == "DPPA_CASE_1_NINHSIM"`.
  Build the three payload pieces exactly as
  `tests/python/analysis/test_offsite_dppa_case_1.py` already does:
  `build_extracted_inputs()` from
  `scripts/python/integration/build_ninhsim_extracted_inputs.py`, the
  `_synthetic_results()` literal in that file, and
  `scenarios/case_studies/ninhsim/2026-04-09_ninhsim_dppa-case-1.json`. Copy the
  helpers rather than importing across test packages.
- Web path, missing input: the same POST **without** `"results"` → HTTP `202`
  (the run is created), then `GET /api/runs/{run_id}` →
  `body["status"]["state"] == "error"`,
  `body["status"]["error_code"] == "MISSING_INPUTS"`, and the message names
  `` `results` ``. Assert explicitly that the state is **not** `"queued"` — that
  regression is the bug this phase fixes.
- CLI: `python -m reopt_pysam_vn.analysis offsite_dppa --config <case1 deal json> --extracted <extracted json> --results <results json> --scenario <scenario json> --no-developer --out <tmp>/out.json`
  → exit code `0` and `json.load(open(out))["case"] == "DPPA_CASE_1_NINHSIM"`.
- CLI negative: the same command without `--results` → exit code `2` and stderr
  contains `` needs `results` `` (the CLI's `except (ValueError, …)` path already
  catches `OrchestratorInputError` because it subclasses `ValueError`).
- Regression: `python -m pytest tests/python/webapp/test_golden_parity.py -q` →
  all tests pass (CON-002 intact).

**Dependencies**

- None. Can run in parallel with PHASE-01 and PHASE-04.

**Exit Criteria**

- [ ] `PYTHONPATH= python -m pytest tests/python/analysis tests/python/webapp -q`
      → all pass, with the 7 new tests from the Test Specs above added.
- [ ] The full portable suite passes with a local count of `660 passed` (653
      baseline + 7 new), `19 deselected`, `3 xfailed`.
- [ ] `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp`
      → `Success: no issues found in 23 source files`.
- [ ] `ruff check src scripts tests` → `All checks passed!`.
- [ ] Manually confirmed: no run directory is left in `state: "queued"` after a
      failed offsite submission (see MANUAL-001).

**Phase Risks**

- **RISK-02-01:** `inspect.signature` on a `functools.partial` or a C-implemented
  callable can raise `ValueError`. Mitigation: wrap the introspection in
  `try/except (TypeError, ValueError)` and fall back to passing the full
  candidate set, preserving today's behaviour.
- **RISK-02-02:** Re-raising `OrchestratorInputError` as `MissingInputsError`
  could mask a genuine analytics bug that happens to raise the same type.
  Mitigation: only the two orchestrator entry-point guards raise the new type;
  nothing deeper in the call stack does.

### PHASE-03 - Make the enforced test surface auditable

**Goal**

Replace runtime "skip because the environment lacks X" guards with declared
markers so the CI exclusion set lives in one auditable place, and get the
declared public CLI measured by coverage instead of sitting at 0 %.

**Tasks**

- [ ] TASK-03-01: Take the skip list captured in PHASE-01's exit criteria and
      classify each entry as either `requires_nrel_key` (needs a live NREL
      developer API key or a network fetch of a solar resource) or
      `requires_pysam_resource` (needs a cached PVWatts solar-resource file that
      is not tracked in git). Convert **only** the tests on that list (ASM-003).
- [ ] TASK-03-02: Declare both markers in `pyproject.toml` `[tool.pytest.ini_options] markers`
      with one-line descriptions matching the existing style.
- [ ] TASK-03-03: Add `--strict-markers` to `[tool.pytest.ini_options]` via an
      `addopts` entry so a typo'd marker becomes an error rather than a silent
      no-op.
- [ ] TASK-03-04: Apply the markers with `@pytest.mark.<marker>` and delete the
      now-redundant `pytest.skip(...)` guard bodies. Where a guard also covers a
      genuinely optional local file, keep the guard **and** add the marker.
- [ ] TASK-03-05: Extend CI's pytest `-m` filter to
      `"not network and not requires_artifacts and not golden_machine and not requires_julia and not requires_nrel_key and not requires_pysam_resource"`.
- [ ] TASK-03-06: Lower `REOPT_PYSAM_VN_MAX_SKIPS` in `.github/workflows/ci.yml`
      to the new observed CI skip count (expected `0`; use whatever the first
      post-change CI run reports, and no higher).
- [ ] TASK-03-07: Add an in-process CLI test that calls
      `reopt_pysam_vn.analysis.__main__.main(argv)` directly so `coverage` can see
      it, alongside the existing subprocess smoke tests.
- [ ] TASK-03-08: Update `docs/testing.md` and `AGENTS.md` §4 to name the new
      markers and the current CI filter.

**File Changes**

- `pyproject.toml` (modify): add the two marker declarations and an
  `addopts = ["--strict-markers"]` entry under `[tool.pytest.ini_options]`. Do
  not change `pythonpath`, `testpaths`, or the four existing markers.
- `tests/python/reopt/test_integration.py` (modify): mark the four
  NREL-key-guarded tests at lines 283, 315, 357, 441 with
  `@pytest.mark.requires_nrel_key` and remove those four `pytest.skip` bodies.
- Additional test modules named by the PHASE-01 skip list (modify): apply the
  appropriate marker. Do not modify any test not on that list.
- `.github/workflows/ci.yml` (modify): extend the `-m` filter; lower the skip
  budget.
- `tests/python/analysis/test_cli.py` (modify): add the in-process test.
- `docs/testing.md` (modify): document both new markers in the existing marker
  list and update the quoted CI command.
- `AGENTS.md` (modify): update the §4 "Test Suite Status" standing note to quote
  the six-marker filter.

**Function Signatures**

- `main(argv: list | None = None) -> int` — already exists in
  `analysis/__main__.py`; this phase only adds an in-process caller. No signature
  changes.

**Test Specs**

- `main(["onsite", "--config", str(cfg), "--results", str(res), "--out", str(out)])`
  → returns `0`, and `out` contains JSON whose `"case"` equals the config's
  `case`. Reuse the tiny injected results fixture already defined in
  `tests/python/analysis/test_cli.py::test_cli_onsite_subcommand` (PV
  `size_kw = 3000.0` with flat 8760 series).
- `main(["offsite_dppa", "--config", str(cfg)])` with a config whose `case` is
  unregistered and no `--extracted` → returns `2` (usage/runtime error path).
- `python -m pytest tests/python -m "requires_nrel_key" -q --collect-only` →
  collects exactly the four tests marked in TASK-03-04's NREL group.
- `python -m pytest tests/python -m "not requires_nrel_key" -q --collect-only`
  → the collected count equals the full collected count minus those four.
- A deliberately misspelled marker (`@pytest.mark.requires_nrel_keyy`) →
  pytest errors with `'requires_nrel_keyy' not found in \`markers\` configuration
  option` (proves `--strict-markers` is active). Revert the typo after checking.

**Dependencies**

- PHASE-01 (the `-rs` CI run that enumerates the 26 skips).

**Exit Criteria**

- [ ] The CI pytest summary reports `0 skipped` (or the documented residual), and
      the deselected count has risen by the number of converted tests.
- [ ] `REOPT_PYSAM_VN_MAX_SKIPS` in CI equals the new observed count.
- [ ] Local coverage for `src/python/reopt_pysam_vn/analysis/__main__.py` is
      above `0 %` in the `--cov-report=term-missing` output.
- [ ] `gh run list --limit 3` shows `success` on both matrix legs.

**Phase Risks**

- **RISK-03-01:** A converted test turns out to pass in CI after all, so
  excluding it by marker *loses* coverage. Mitigation: convert only tests the
  PHASE-01 CI log actually reported as skipped; those are, by definition, not
  running in CI today.
- **RISK-03-02:** `--strict-markers` in `addopts` breaks an ad-hoc local
  invocation that uses an undeclared marker. Mitigation: run the full suite
  locally before pushing; any breakage is a genuine undeclared marker and should
  be declared.

### PHASE-04 - Market-price data layer and shared market reference

**Goal**

Give the repository a versioned market-reference price source behind the data
manifest, and lift the market-proxy method out of the 1,491-line case-2 module
into a shared, deal-agnostic function — without moving a single number for the
existing deals.

**Tasks**

- [ ] TASK-04-01: Create `data/vietnam/vn_market_prices_2026.json` with the
      standard `{_meta, data}` envelope and the ASM-002 contents.
- [ ] TASK-04-02: Add `"market_prices": "vn_market_prices_2026.json"` to
      `data/vietnam/manifest.json` and bump its `_meta.last_updated` to today.
- [ ] TASK-04-03: Add a `market_prices: dict[str, Any]` field to the `VNData`
      dataclass in `reopt/preprocess.py` **with a default of an empty dict** so
      the frozen dataclass stays constructible from an older manifest, and load
      the key in `load_vietnam_data()` **optionally** — if the manifest lacks
      `market_prices`, set `{}` rather than raising. Do **not** add it to the
      `required_keys` tuple.
- [ ] TASK-04-04: Create `src/python/reopt_pysam_vn/integration/market_reference.py`
      implementing S2.
- [ ] TASK-04-05: Add `market_wholesale_reference_vnd_per_kwh(vn)` to
      `common/assumptions.py`, following the existing resolver style, reading
      `vn.market_prices["proxy"]["wholesale_reference_vnd_per_kwh"]`.
- [ ] TASK-04-06: Rewrite `dppa_case_2.build_dppa_case_2_market_proxy` to
      delegate to the shared function while returning the exact same dict keys
      and values it returns today (including the `"model": "Ninhsim DPPA Case 2
      Market Proxy"` label and both note strings).
- [ ] TASK-04-07: Add a `market_prices` row to `docs/regulatory-watch.md` with
      `Status: PROXY — no published hourly FMP/CFMP series ingested`,
      `Last verified` = today, `Next review` = today plus six months.

**File Changes**

- `data/vietnam/vn_market_prices_2026.json` (create):
  ```json
  {
    "_meta": {
      "version": "2026.1",
      "description": "Wholesale/market price reference for DPPA settlement. No published hourly FMP/CFMP series has been ingested; the proxy block below drives a tariff-scaled reference series.",
      "status": "PROXY - no published hourly FMP/CFMP series ingested",
      "source": "Surplus purchase rate carried by data/vietnam/vn_export_rules_2026_decree243.json (Decree 243/2026/ND-CP), used as the wholesale reference",
      "last_updated": "2026-08-12",
      "units": "VND per kWh unless a key says otherwise"
    },
    "data": {
      "hourly_shape_24": null,
      "proxy": {
        "wholesale_reference_vnd_per_kwh": 671.0,
        "method": "hourly_evn_tariff_scaled_by_wholesale_ratio",
        "market_reference_price_type": "proxy_cfmp_or_fmp"
      }
    }
  }
  ```
- `data/vietnam/manifest.json` (modify): add the `market_prices` key; update
  `_meta.last_updated`. Leave the seven existing keys unchanged.
- `src/python/reopt_pysam_vn/reopt/preprocess.py` (modify): add the `VNData`
  field with a default and the optional load. Because `VNData` is
  `@dataclass(frozen=True)` and every existing field is non-default, the new
  field **must be declared last** and **must** carry
  `field(default_factory=dict)` or Python raises
  `TypeError: non-default argument follows default argument` at import time.
- `src/python/reopt_pysam_vn/integration/market_reference.py` (create): S2.
- `src/python/reopt_pysam_vn/common/assumptions.py` (modify): add the one
  resolver function; leave the existing five untouched.
- `src/python/reopt_pysam_vn/integration/dppa_case_2.py` (modify): rewrite the
  body of `build_dppa_case_2_market_proxy` to delegate. Leave
  `_proxy_market_fraction`, `_load_retail_series`, and every other function in
  the module alone.
- `docs/regulatory-watch.md` (modify): add one row.
- `tests/python/integration/test_market_reference.py` (create): the specs below.

**Function Signatures**

- `resolve_market_reference_series(extracted: dict[str, Any], *, vn: Any | None = None) -> tuple[list[float], str, dict[str, Any]]`
  — returns `(series_vnd_per_kwh_8760, market_reference_price_type, provenance)`
  where `provenance` carries `{"method", "proxy_fraction_of_evn", "notes"}`;
  resolution follows S2.
- `market_proxy_fraction(extracted: dict[str, Any], *, vn: Any | None = None) -> float`
  — returns `wholesale_reference ÷ weighted_retail`, or `0.0` when the
  denominator is zero.
- `market_wholesale_reference_vnd_per_kwh(vn: VNData) -> float` — returns
  `vn.market_prices["proxy"]["wholesale_reference_vnd_per_kwh"]`; raises
  `KeyError` naming the manifest key when `market_prices` is empty.

**Test Specs**

- `market_proxy_fraction({"benchmark": {"weighted_evn_price_vnd_per_kwh": 2000.0, "wholesale_rate_vnd_per_kwh": 671.0}})`
  → `0.3355`.
- `market_proxy_fraction({"benchmark": {"weighted_evn_price_vnd_per_kwh": 0.0, "wholesale_rate_vnd_per_kwh": 671.0}})`
  → `0.0` (no `ZeroDivisionError`).
- `market_proxy_fraction({"benchmark": {"weighted_evn_price_vnd_per_kwh": 2000.0}})`
  with a loaded `vn` → `671.0 / 2000.0 == 0.3355` (data-layer fallback engages).
- `resolve_market_reference_series({"cfmp_vnd_per_mwh": [1_500_000.0] * 8760, ...})`
  → `(series, "cfmp", …)` with `series[0] == 1500.0` (VND/MWh → VND/kWh).
- `resolve_market_reference_series({"fmp_vnd_per_mwh": [1_200_000.0] * 8760, "cfmp_vnd_per_mwh": [1_500_000.0] * 8760, ...})`
  → type `"cfmp"` (CFMP wins per S2 order).
- `resolve_market_reference_series` with neither series present but a full
  `benchmark` + `evn_tariff` → type `"proxy_cfmp_or_fmp"`, series length `8760`,
  and `series[0] == extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"][0] * 0.3355`
  for the 2000/671 benchmark above.
- **Value-preservation gate (CON-004):** capture
  `build_dppa_case_2_market_proxy(<ninhsim extracted>)` before the change, then
  assert the post-change return dict is equal key-for-key and value-for-value,
  including `proxy_fraction_of_evn` to full float precision. Implement this as a
  test that recomputes the expected series inline from
  `extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]` rather than storing a
  new golden file.
- `load_vietnam_data()` against a temp manifest **without** the `market_prices`
  key → returns a `VNData` whose `.market_prices == {}` and does not raise.

**Dependencies**

- None for the data file and shared module. Must land before PHASE-05.

**Exit Criteria**

- [ ] `python -m pytest tests/python/integration/test_market_reference.py tests/python/integration/test_dppa_case_2_phase_ab.py tests/python/integration/test_dppa_case_2_phase_cd.py tests/python/integration/test_dppa_case_2_phase_e.py tests/python/integration/test_dppa_case_2_phase_f.py tests/python/integration/test_dppa_case_2_phase_g.py -q`
      → all pass.
- [ ] The full portable suite passes with no change to any existing assertion —
      **zero** numeric test values were edited in this phase.
- [ ] `python -c "from reopt_pysam_vn.reopt.preprocess import load_vietnam_data; print(load_vietnam_data().market_prices['proxy']['wholesale_reference_vnd_per_kwh'])"`
      → `671.0`.
- [ ] `python -m pytest tests/python/test_repo_invariants.py -q` → passes (the
      new watch row carries a future review date).

**Phase Risks**

- **RISK-04-01:** Adding a field to the frozen `VNData` dataclass breaks
  construction. Mitigation: the field is declared last with a
  `default_factory`; `load_vietnam_data` is the only construction site in the
  repo (verified), so no other caller needs updating.
- **RISK-04-02:** The delegation silently changes a float by a last-bit rounding
  difference, moving a case-2 golden. Mitigation: the shared function must
  perform the multiplication in the same order as today
  (`rate * fraction`, not `fraction * rate`) and compute `fraction` with the same
  single division; the value-preservation test above catches any drift.

### PHASE-05 - Generic fallback orchestrator and honest extracted-inputs validation

**Goal**

Make any `DealConfig` runnable through `run_offsite_dppa`, and validate the
offsite input layer against a schema that describes the files that actually
exist.

**Tasks**

- [ ] TASK-05-01: Correct `data/schemas/extracted_inputs.schema.json` per
      DEC-005: reduce top-level `required` to `["loads_kw"]`; keep every existing
      property definition; add a `description` on each newly-optional property
      naming which pipeline needs it; add `generation_kw` as an optional 8760
      array property.
- [ ] TASK-05-02: Generalise the structural validator so it can serve both
      schemas: move the schema-agnostic machinery out of
      `analysis/validation.py` into reusable functions, add support for the
      keywords the extracted schema uses that the validator does not yet handle
      (`minItems`, `maxItems`, `minLength`, `minimum`, `maximum`), and add
      `validate_extracted_inputs`. Keep `validate_deal_config` and
      `DealConfigValidationError` exported and behaviourally identical.
- [ ] TASK-05-03: Create `analysis/orchestrators/generic_vn_dppa.py` implementing
      S3.
- [ ] TASK-05-04: Wire the generic orchestrator as the registry fallback in
      `analysis/offsite_dppa.py` per S1 step 3 (a module-level
      `_GENERIC_ORCHESTRATOR` plus a `set_generic_orchestrator` setter used by
      `analysis/__init__.py`, mirroring the existing lazy registration pattern).
- [ ] TASK-05-05: Delete the `if deal_config.case not in _ORCHESTRATORS: raise
      OrchestratorNotRegisteredError` pre-check from
      `webapp/service._run_offsite` — with a fallback registered it would reject
      requests the library can now serve. Keep the
      `OrchestratorNotRegisteredError` class and its `errors.py` mapping in
      place: `run_offsite_dppa` still raises it when a caller explicitly disables
      the fallback.
- [ ] TASK-05-06: Update `_NO_ORCHESTRATOR_HINT` in `webapp/errors.py` — the
      current text promises a "generic runner" that now exists; make it name the
      real condition instead.
- [ ] TASK-05-07: Call `validate_extracted_inputs` at the top of
      `run_offsite_dppa` (after `extracted` resolution) and raise
      `OrchestratorInputError` carrying every collected violation when it fails.
- [ ] TASK-05-08: Update `README.md`'s "Analysis Modes" paragraph and
      `docs/onsite_vs_offsite.md` to describe the fallback: any unregistered case
      now returns a `directional` generic result rather than an error.

**File Changes**

- `data/schemas/extracted_inputs.schema.json` (modify): `required` list and
  property descriptions; add `generation_kw`. Leave `$id`, `$schema`, and the
  existing type/bound keywords alone.
- `src/python/reopt_pysam_vn/analysis/validation.py` (modify): generalise;
  add `validate_extracted_inputs`, `ExtractedInputsValidationError`, and the five
  new keyword checks. Both error classes subclass `ValueError` and carry
  `.errors`.
- `src/python/reopt_pysam_vn/analysis/orchestrators/generic_vn_dppa.py` (create):
  S3.
- `src/python/reopt_pysam_vn/analysis/offsite_dppa.py` (modify): fallback
  resolution and the validation call.
- `src/python/reopt_pysam_vn/analysis/__init__.py` (modify): register the generic
  orchestrator alongside the existing case-1 registration.
- `src/python/reopt_pysam_vn/webapp/service.py` (modify): remove the pre-check;
  update the module docstring's "no generic fresh-solve path" paragraph.
- `src/python/reopt_pysam_vn/webapp/errors.py` (modify): the hint string only.
- `README.md`, `docs/onsite_vs_offsite.md` (modify): the two paragraphs above.
- `tests/python/analysis/test_generic_vn_dppa.py` (create): the specs below.
- `tests/python/analysis/test_validation.py` (modify): add extracted-schema cases.
- `tests/python/webapp/test_api_runs.py` (modify): add the unregistered-case
  end-to-end test.

**Function Signatures**

- `build_generic_offsite_artifact(extracted: dict[str, Any], *, deal_config: DealConfig, run_developer: bool = True, results: dict[str, Any] | None = None, scenario: dict[str, Any] | None = None) -> dict[str, Any]`
  — returns a dict in the `OffsiteDppaResult` block vocabulary per S3.
- `build_generic_generation_profile(extracted: dict[str, Any], deal_config: DealConfig) -> dict[str, Any]`
  — returns `{"series_kw": list[float], "source": str, "calibrated_to_gwh": float | None}`
  per S3 step 2 and ASM-006.
- `set_generic_orchestrator(fn: CombinedDecisionFn | None) -> None` — installs
  (or, with `None`, removes) the registry fallback.
- `validate_extracted_inputs(d: dict[str, Any], *, schema: dict[str, Any] | None = None) -> None`
  — returns `None`; raises `ExtractedInputsValidationError` carrying every
  violation.
- `load_extracted_inputs_schema() -> dict[str, Any]` — loads and caches
  `data/schemas/extracted_inputs.schema.json`.

**Test Specs**

Use this deterministic fixture for the numeric assertions — flat series make
every expected value an exact integer:

```
loads_kw        = [1000.0] * 8760          # kW, so 1000 kWh per hour
generation_kw   = [500.0]  * 8760          # supplied directly, no PVWatts
evn_tariff      = [2000.0] * 8760          # VND/kWh
benchmark       = {"weighted_evn_price_vnd_per_kwh": 2000.0,
                   "wholesale_rate_vnd_per_kwh": 671.0}
contract        = {"settlement_mechanism": "physical",     # -> private_wire
                   "strike_vnd_per_kwh": 1200.0}
```

- `build_generic_offsite_artifact(...)["base_settlement"]["annual_summary"]["matched_mwh"]`
  → `4380.0` (500 kWh × 8760 ÷ 1000).
- `... ["buyer_cost_vnd"]` → `14_016_000_000.0`
  (4,380,000 kWh × 1200 + 4,380,000 kWh × 2000).
- `... ["buyer_blended_rate_vnd_kwh"]` → `1600.0`
  (14,016,000,000 ÷ 8,760,000 kWh).
- `... ["developer_revenue_vnd"]` → `5_256_000_000.0`
  (4,380,000 kWh × 1200; no export in `curtail`/`export_at_surplus` with zero
  excess).
- `buyer_savings_vs_evn_vnd` → `3_504_000_000.0`
  (EVN-only cost 8,760,000 × 2000 = 17,520,000,000 minus buyer cost).
- `result["quality"]["orchestrator"]` → `"generic_vn_dppa"`;
  `result["quality"]["basis"]` → `"directional"`;
  `result["quality"]["market_reference_price_type"]` → `"proxy_cfmp_or_fmp"`;
  `result["quality"]["solar_profile_source"]` → `"extracted_generation_kw"`.
- `len(result["strike_sweep"]["sweep"])` → `21`, with
  `sweep[0]["strike_vnd_kwh"] == 720.0` (0.6 × 1200) and
  `sweep[-1]["strike_vnd_kwh"] == 1680.0` (1.4 × 1200).
- Excess/export edge case: same fixture with `generation_kw = [1500.0] * 8760`
  and `contract["regime_id"] = "decision_963_2026_current"` (50 % export cap,
  `excess_treatment="export_at_surplus"`) → `matched_mwh == 8760.0`,
  `excess_mwh == 4380.0`, `exported_mwh == 4380.0` (500 kWh excess is below the
  750 kWh hourly cap), `curtailed_mwh == 0.0`.
- Wrong-length load: `loads_kw = [1000.0] * 8000` → raises
  `OrchestratorInputError` (not a silent zero-pad), message naming `8760`.
- Registry fallback through the public API:
  `run_offsite_dppa(DealConfig.from_dict({"case": "SOME_NEW_DEAL", "mode": "offsite_dppa"}), extracted=<fixture>)`
  → returns an `OffsiteDppaResult` with `case == "SOME_NEW_DEAL"` and
  `quality["orchestrator"] == "generic_vn_dppa"`.
- Registered cases still win: `run_offsite_dppa` for `DPPA_SAMSUNG_TTC` →
  `quality` does **not** contain `"orchestrator": "generic_vn_dppa"`, and
  `python -m pytest tests/python/webapp/test_golden_parity.py tests/python/analysis/test_offsite_dppa.py -q`
  passes unchanged.
- Web path: `POST /api/runs` with
  `{"deal_config": {"case": "MY_NEW_DEAL", "mode": "offsite_dppa"}, "extracted": <fixture>}`
  → HTTP `202`, then `GET /api/runs/{run_id}` → `state == "done"` and
  `result["quality"]["orchestrator"] == "generic_vn_dppa"`. This is the
  regression that proves the free-text **Case id** field works.
- `validate_extracted_inputs({"loads_kw": [1.0] * 8760})` → returns `None`.
- `validate_extracted_inputs({})` → raises `ExtractedInputsValidationError` with
  `.errors == ["missing required property: 'loads_kw'"]`.
- `validate_extracted_inputs({"loads_kw": [1.0] * 100})` → raises, and the error
  string names both `8760` and the actual length.
- All five tracked files validate:
  ```bash
  python - <<'PY'
  import glob, json
  from reopt_pysam_vn.analysis.validation import validate_extracted_inputs
  for p in sorted(glob.glob("data/interim/*/*extracted_inputs.json")):
      d = json.load(open(p, encoding="utf-8-sig"))
      if "loads_kw" not in d:
          print("SKIP (not an offsite input file):", p); continue
      validate_extracted_inputs(d); print("OK", p)
  PY
  ```
  → `OK` for the ninhsim, north_thuan, saigon18, and samsung_ttc files;
  `SKIP` for `data/interim/factory_a/factory_a_extracted_inputs.json`, which has
  no `loads_kw` and is an ingestion artifact of a different shape.

**Dependencies**

- PHASE-02 (`OrchestratorInputError` and signature-aware forwarding).
- PHASE-04 (`integration/market_reference.py` and the data-layer fallback).

**Exit Criteria**

- [ ] `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia and not requires_nrel_key and not requires_pysam_resource" -q`
      → all pass, with the new generic-orchestrator and validation tests included.
- [ ] `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp`
      → `Success: no issues found` (the new orchestrator lives under `analysis`,
      so every function needs full annotations).
- [ ] `ruff check src scripts tests` → `All checks passed!`.
- [ ] `tests/python/webapp/test_golden_parity.py` passes unchanged (CON-002).
- [ ] Submitting an unregistered case through the web API reaches `done`, not
      `error` (MANUAL-002).
- [ ] `gh run list --limit 3` shows `success` on both matrix legs.

**Phase Risks**

- **RISK-05-01:** The fallback masks a genuine typo in a `case` id — an analyst
  fat-fingers `DPPA_SAMSUNG_TTCC` and silently gets a generic run instead of the
  bespoke one. Mitigation: `quality.orchestrator` names what ran on every result,
  and the generic path is always flagged `basis: "directional"`. Additionally,
  append a warning to `quality.warnings` naming the registered cases whenever the
  fallback is used.
- **RISK-05-02:** Switching on extracted-inputs validation breaks an existing
  deal path. Mitigation: DEC-005 reduces `required` to `loads_kw`, and the
  five-file check in the test specs above is a hard exit criterion.
- **RISK-05-03:** Generalising `analysis/validation.py` changes
  `validate_deal_config`'s error messages, breaking
  `tests/python/analysis/test_validation.py`. Mitigation: the refactor is
  mechanical — keep the existing message format strings byte-identical and run
  that test file first.

## Gotchas

- **The offsite `extracted` files are heterogeneous.** All five tracked
  `*_extracted_inputs.json` files violate the current schema's `required` list,
  and they disagree with each other: Saigon18 has no `project` or `site` key;
  Samsung has no `load_cleaning`, `pv_production_factor`, or `fmp_vnd_per_mwh`;
  Factory A has no `loads_kw` at all (it is an ingestion artifact with a
  `load_profile` block, not an offsite input). Do not "fix" the data files to
  match the schema — fix the schema to match the data (DEC-005).
- **`VNData` is a frozen dataclass with no defaulted fields.** A new field must
  be declared last with `field(default_factory=dict)`, or the module fails to
  import with `TypeError: non-default argument follows default argument`.
- **`load_vietnam_data()` has a hard `required_keys` tuple.** Adding
  `market_prices` there would break any manifest that predates this change,
  including test fixtures. Load it optionally instead.
- **`_pad_to_8760` hides length errors.** `integration/settlement` silently
  truncates a 10,000-element series and zero-pads a 100-element one. The generic
  orchestrator must validate lengths *before* calling into settlement, or a
  wrong-length upload produces a plausible-looking wrong answer.
- **VND/MWh vs VND/kWh.** `fmp_vnd_per_mwh` and `cfmp_vnd_per_mwh` are in VND per
  **MWh** and must be divided by 1,000 before entering the settlement engine,
  which works entirely in VND per kWh. `dppa_case_2._normalize_market_series_vnd_per_kwh`
  uses a `max > 10_000` heuristic to auto-detect units; the new shared function
  should convert explicitly by key name instead of re-deriving from magnitudes.
- **`bool` is a subclass of `int` in Python.** Any recursive numeric comparator
  written for these artifacts must check `bool` before `int`, or a decision flag
  compares equal to `1`. This has bitten the repo before.
- **Do not add a `DeprecationWarning` to any function the new layer itself
  calls.** The generic path routes through `integration.settlement`, and a
  runtime warning there would fire during normal operation and pollute the test
  output. Deprecate through docstrings only.
- **Do not run `ruff check --fix` across the whole tree as a convenience.** The
  repo's `E402` and `ISC004` ignores are deliberate, and a broad autofix has
  previously churned unrelated files. Fix only what the phase touches.
- **`register_orchestrator` mutates module state.** Any test that registers an
  orchestrator must restore the previous registry entry in a fixture teardown, or
  it leaks into later tests in the same session. The existing
  `tests/python/analysis/test_offsite_dppa_case_1.py` shows the pattern.
- **Skipped-report counting.** A skipped test emits reports for multiple phases;
  count only `report.when == "setup"` or the budget will double-count.
- **Report "done" only after CI is green.** Local green and CI green are
  different claims. Every phase's exit criteria include `gh run list --limit 3`
  for that reason. A CI run that finishes far faster than the historical ~1m30s
  has probably aborted at the lint step rather than reaching the tests.

## Verification Strategy

- **TEST-001:** `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q --cov=reopt_pysam_vn --cov-report=term-missing`
  → after PHASE-02: `660 passed, 19 deselected, 3 xfailed`. After PHASE-05 the
  marker filter gains `and not requires_nrel_key and not requires_pysam_resource`
  and the passed count rises by the number of tests each phase adds; no test may
  fail or error at any point.
- **TEST-002:** `ruff check src scripts tests` → `All checks passed!`
- **TEST-003:** `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp`
  → `Success: no issues found in 23 source files`, rising to `24 source files`
  after PHASE-05 adds `analysis/orchestrators/generic_vn_dppa.py`.
- **TEST-004:** `python -m pytest tests/python/test_repo_invariants.py -q`
  → `5 passed`, and no `Next review` date in `docs/regulatory-watch.md` is within
  30 days of today.
- **TEST-005:** `python -m pytest tests/python/webapp/test_golden_parity.py -q`
  → all pass — the CON-002 no-forked-analytics gate, run after every phase.
- **TEST-006:** value-preservation check for PHASE-04, run before and after the
  refactor and diffed:
  ```bash
  PYTHONPATH=src/python python - <<'PY' > /tmp/market_proxy_after.json
  import json, sys
  sys.path.insert(0, "scripts/python/integration")
  from build_ninhsim_extracted_inputs import build_extracted_inputs
  from reopt_pysam_vn.integration.dppa_case_2 import build_dppa_case_2_market_proxy
  print(json.dumps(build_dppa_case_2_market_proxy(build_extracted_inputs()), sort_keys=True))
  PY
  diff /tmp/market_proxy_before.json /tmp/market_proxy_after.json
  ```
  → no output (files identical).
- **TEST-007:** `python -c "from reopt_pysam_vn.reopt.preprocess import load_vietnam_data as l; d=l(); print(d.market_prices['proxy']['wholesale_reference_vnd_per_kwh'], d.exchange_rate)"`
  → `671.0 26400.0`
- **MANUAL-001:** After PHASE-02, start the web app
  (`PYTHONPATH=src/python python -m uvicorn reopt_pysam_vn.webapp:app --port 8000`),
  POST an offsite `DPPA_CASE_1_NINHSIM` deal **without** `results`, then
  `curl -s localhost:8000/api/runs | python -m json.tool` and confirm the run's
  `state` is `error` with `error_code` `MISSING_INPUTS` — **not** `queued`, and
  no HTTP 500 in the server log.
- **MANUAL-002:** After PHASE-05, open `http://127.0.0.1:8000/deals/new`, choose
  mode **Offsite DPPA**, type a novel Case id (for example `MY_NEW_DEAL`), attach
  an 8760-row load CSV, submit, and confirm the run page renders a result with a
  visible `directional` quality flag rather than an error banner.
- **OBS-001:** Inspect the CI log for the first run after PHASE-01 and copy the
  `-rs` skip-reason block verbatim into the PHASE-01 commit message; PHASE-03
  consumes exactly that list and nothing else (ASM-003).
- **OBS-002:** After each phase, `gh run list --limit 3` → the latest `main` run
  reports `success` with a duration in the historical ~1m30s range on both
  matrix legs. A markedly shorter run means the pipeline aborted early.

## Risks and Alternatives

- **RISK-001:** The generic orchestrator produces plausible-looking but
  commercially wrong numbers for a deal whose contract shape it does not really
  model (for example a contracted-volume CfD with a floor). Mitigation: every
  generic result is flagged `basis: "directional"` and carries the resolved
  `market_reference_price_type`; the fallback appends a warning naming the
  registered bespoke cases. This is the same honesty convention the Samsung path
  already uses.
- **RISK-002:** PHASE-04's refactor moves a number in a case-2 golden by a
  floating-point last bit, turning a currently-green test red. Mitigation:
  TEST-006 diffs the full proxy artifact before and after; the shared function
  must preserve operation order exactly.
- **RISK-003:** Pinning CI to a constraints file freezes a security fix out of
  the build. Mitigation: the weekly scheduled run plus the header comment in
  `constraints-ci.txt` documenting the regeneration command make refreshing it a
  routine, deliberate commit.
- **RISK-004:** PHASE-03 excludes a test by marker that was actually providing
  CI value. Mitigation: only tests the PHASE-01 CI log reports as *skipped* are
  converted — those provide zero CI value today by definition.
- **ALT-001:** *Register a third bespoke orchestrator (`dppa_case_2` or
  `ninhsim_solar_storage_60pct`) instead of building a generic one.* Rejected:
  it grows the registry without changing its nature, and the web app's free-text
  Case id field stays broken for every deal that is not already in the
  repository. Two registered implementations is already the sample needed to
  abstract from (DEC-001).
- **ALT-002:** *Fabricate an hourly FMP/CFMP shape so the market-price file has
  real 8760 data.* Rejected: inventing a market shape and shipping it in the
  policy data layer is exactly the kind of unfalsifiable claim the repository has
  spent several cycles removing. `hourly_shape_24: null` plus an explicit
  `PROXY` status is honest and can be replaced by a real ingest later without a
  schema change (ASM-002).
- **ALT-003:** *Make `validate_extracted_inputs` strict against the schema as
  written today.* Rejected: all five tracked input files would fail immediately,
  including the flagship Samsung deal. The schema is stale relative to the data
  it describes, so the schema is what changes (DEC-005).
- **ALT-004:** *Fix the offsite 500 by broadening the web layer's `except
  service.AnalysisError` to `except ValueError`.* Rejected: it would also swallow
  genuine `ValueError`s from deep inside the analytics and report them to the
  analyst as "missing inputs". A typed `OrchestratorInputError` is precise
  (DEC-003).

## Suggested Next Step

Execute PHASE-01. It is the only phase with a deadline — the regulatory-watch
rows expire 2026-08-18 and the invariant test fails on the first push on or
after 2026-08-19 — and its `-rs` CI output is the input PHASE-03 depends on.
PHASE-02 and PHASE-04 have no dependencies and can be executed in parallel by a
second engineer. Verify each phase's exit criteria, including
`gh run list --limit 3` showing green on both matrix legs, before starting the
next.
