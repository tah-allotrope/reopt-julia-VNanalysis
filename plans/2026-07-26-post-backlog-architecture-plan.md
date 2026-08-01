---
status: "complete — PHASE-01..06 shipped (commits 3943c5b, 31732d2, a70e0c5, c9b16d8, 0f40be8, 2fce33a, + PHASE-06 move commit): 3.10/3.12 CI matrix + ruff gate, DealConfig schema validator, Samsung parity docs honest, assumptions resolver + deal_defaults, FX unified on 26,400 with delta memo, Julia archived under legacy/julia/ with verified REPO_ROOT + Layer 1/2/3 green"
---

# Plan: Post-Backlog Architecture — Reproducibility Floor, API Contract, Canonical Assumptions, Julia Archive

## Objective

Close four structural gaps in the `reopt-pysam-vn` toolkit that no test currently catches: (1) the repo declares Python `>=3.10` but contains code that cannot parse on 3.10 and runs CI on 3.12 only; (2) the declared public API (`reopt_pysam_vn.analysis`) accepts arbitrary dicts and its headline bit-exact parity guarantee is disabled twice over while the README still advertises it; (3) four different VND/USD exchange rates are hardcoded across 17 files (a 5.6% spread on every USD figure the toolkit emits) while a canonical value sits in a manifest-registered data file that the loader never reads; and (4) the Julia half of the codebase is presented as a co-equal implementation twin when it is a stale subset whose equivalence nothing verifies.

This matters now because the toolkit's outputs go to external counterparties as PPTX decks and HTML reports, and because the prior implementation backlog is fully drained — every phase from the 2026-07-22 and 2026-07-24 sprint plans has shipped, so this is the moment to fix the foundation before more deliverables are generated on divergent assumptions.

## Context Snapshot

- **Current state:**
  - Test suite is green: `589 passed, 18 deselected, 3 xfailed` in ~65s; 85% line coverage across 4,599 statements.
  - CI (`.github/workflows/ci.yml`) runs `mypy` on `analysis/` + `webapp/`, then pytest on `tests/python` with markers `network`, `requires_artifacts`, `golden_machine`, `requires_julia` excluded. Single Python version: 3.12. No lint step.
  - `data/vietnam/vn_deal_defaults_2026.json` holds `exchange_rate.vnd_per_usd = 26400` with a source citation, is registered in `data/vietnam/manifest.json` under key `deal_defaults`, and is listed `CURRENT` in `docs/regulatory-watch.md` — but `load_vietnam_data()` never loads it, and it could not be loaded as-is because it lacks the `{_meta, data}` envelope the loader hard-requires.
  - 22 hardcoded VND/USD literals across 17 Python files, using four distinct values: `26_400`, `26_000`, `25_450`, `25_000`.
  - `reopt_pysam_vn/common/` contains three stub modules (8 statements total, zero importers, 0% coverage).
  - `data/schemas/deal_config.schema.json` is a complete JSON Schema that is never used to validate anything at runtime.
  - `tests/python/analysis/test_samsung_ttc_parity.py` is `pytest.mark.golden_machine` at module level (CI-excluded) **and** both meaningful assertions carry `@pytest.mark.xfail(strict=False)`.
  - `tests/cross_language/` and `tests/julia/` sit outside CI's collection path (`tests/python`) entirely.
  - `ruff check src scripts tests` reports 187 violations including one hard syntax error.
- **Desired state:**
  - CI runs on Python 3.10 and 3.12, enforces `ruff`, and the syntax error is fixed.
  - `DealConfig.from_dict` structurally validates against the shipped schema with actionable errors.
  - The Samsung/TTC parity gate is either genuinely enforced in CI or the documentation honestly describes what is enforced — with no third state.
  - One canonical assumptions resolver reads the data layer; `PRESET_CONTRACTS` is guarded against policy drift; all 22 FX literals route through the resolver.
  - Julia lives under `legacy/julia/` with the README describing the real stack.
- **Key repo surfaces:**
  - `src/python/reopt_pysam_vn/reopt/preprocess.py` (890 lines) — `VNData`, `load_vietnam_data()`, `resolve_vietnam_regime()`, `DEFAULT_EXCHANGE_RATE`
  - `src/python/reopt_pysam_vn/integration/settlement.py` (~330 lines) — `ContractParams`, `PRESET_CONTRACTS`
  - `src/python/reopt_pysam_vn/analysis/types.py` — `DealConfig`, result dataclasses
  - `src/python/reopt_pysam_vn/common/` — stub package to be promoted
  - `src/julia/REoptVietnam.jl` (981 lines), `scripts/julia/`, `Project.toml`, `Manifest.toml`
  - `.github/workflows/ci.yml`, `pyproject.toml`, `data/vietnam/manifest.json`
- **Out of scope:**
  - The config-driven case runner / reporting-pipeline decomposition of the 106 scripts under `scripts/python/` (a separate multi-sprint initiative; this plan is its prerequisite).
  - The webapp → PPTX deck export endpoint.
  - Multi-tenant auth, cloud hosting, containerization.
  - Rotating the NREL API key (an out-of-band human action; see ASM-009).
  - Deciding which VND/USD rate is *contractually* correct for any individual deal (see ASM-005).

## Environment & Conventions

- **Stack:** Python 3.10+ (declared) / 3.12 (the interpreter that actually works locally). Package manager: `pip` with an editable install — **not** `uv`, **not** `poetry`. Julia 1.10.10 with REopt.jl v0.56.4 for the Julia half. Web layer: FastAPI + Uvicorn + Jinja2. Finance: `nrel-pysam` 7.1.0, `numpy-financial`. No lockfile exists.
- **Setup:**
  ```bash
  python -m pip install -e ".[webapp]"
  python -m pip install mypy pytest pytest-cov ruff "nrel-pysam==7.1.0"
  ```
  On the primary Windows dev machine, PySAM and `python-pptx` live **only** in the repo-local `.venv` (Python 3.12). Use `.venv/Scripts/python.exe` there. See the `PYTHONPATH` trap below.
- **Build / Run:**
  ```bash
  # Web app (localhost only)
  PYTHONPATH=src/python python -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000

  # Analysis CLI
  PYTHONPATH=src/python python -m reopt_pysam_vn.analysis offsite_dppa \
    --config scenarios/case_studies/samsung_ttc/samsung_ttc_deal_config.json \
    --extracted data/interim/samsung_ttc/samsung_ttc_extracted_inputs.json --out out.json
  ```
- **Test:** full portable suite (exactly what CI runs):
  ```bash
  PYTHONPATH= python -m pytest tests/python \
    -m "not network and not requires_artifacts and not golden_machine and not requires_julia" \
    -q --cov=reopt_pysam_vn --cov-report=term-missing
  ```
  Expected today: `589 passed, 18 deselected, 3 xfailed`.

  Single test:
  ```bash
  PYTHONPATH= python -m pytest tests/python/reopt/test_unit.py::test_build_vietnam_tariff_industrial_south -v
  ```
  Type gate:
  ```bash
  mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp
  ```
  Julia/cross-language layers (not in CI, run manually on a machine with Julia installed):
  ```bash
  JULIA_PKG_PRECOMPILE_AUTO=0 julia --project --compile=min tests/julia/test_unit.jl
  PYTHONPATH= python tests/cross_language/cross_validate.py
  ```
- **Conventions & traps:**
  - **`PYTHONPATH` trap (critical):** a global `PYTHONPATH` pointing at an unrelated `hermes-agent` venv shadows this repo's dependencies and breaks webapp tests with `ModuleNotFoundError: pydantic_core._pydantic_core`. **Always clear it** (`PYTHONPATH=` prefix) when running pytest. Set `PYTHONPATH=src/python` **only** when invoking `uvicorn` or scripts directly — pytest does not need it (`[tool.pytest.ini_options] pythonpath` handles it).
  - **Currency:** all VND amounts are **VND per kWh** or **VND absolute**, always **excluding VAT**. USD conversion is always **divide by VND-per-USD**. Never write a bare numeric FX literal in new code.
  - **Data layer:** every file in `data/vietnam/` uses a `{"_meta": {...}, "data": {...}}` envelope. Code reads **only** the `data` block. To update policy data, create a **new versioned file** and change one line in `data/vietnam/manifest.json` — never edit a published file's numbers in place.
  - **Scripts are canonical-only:** they live at `scripts/python/{reopt,pysam,integration}/<name>.py`. A flat `scripts/python/*.py` file is banned and mechanically enforced by `tests/python/test_repo_invariants.py::test_no_flat_python_scripts`.
  - **Generated outputs are git-ignored:** `artifacts/`, `reports/*.html`, `present/`, `scenarios/generated/`. Tracked deliverables are `reports/*.md`, `examples/`, `tests/baselines/`.
  - **Public API boundary:** `reopt_pysam_vn.analysis` and `reopt_pysam_vn.webapp` are the type-checked, supported surfaces (`mypy` gate + `py.typed`). `integration`, `reopt`, and `pysam` are internal engines.
  - **Time:** all 8760-hour series are hour-of-year indexed, `[0..8759]`, local Vietnam time (UTC+7), non-leap-year basis.
  - Line length is not enforced today; do not reformat unrelated code.
- **Repo map:**
  ```
  data/vietnam/          Versioned policy JSON + manifest.json (the data layer)
  data/schemas/          JSON Schemas (deal_config, extracted_inputs)
  src/python/reopt_pysam_vn/
    analysis/            PUBLIC API: DealConfig, run_onsite, run_offsite_dppa, CLI
    common/              Stub package (3 files, no importers) — promoted in PHASE-04
    reopt/               REopt preprocessing, regime resolution, tariff deltas
    pysam/               PySAM Single Owner finance, PVWatts
    integration/         Per-deal orchestration engines + settlement engine
    webapp/              FastAPI localhost UI over analysis/
  src/julia/             REoptVietnam.jl — the preprocessing twin (archived in PHASE-06)
  scripts/python/{reopt,pysam,integration}/   106 workflow + report scripts
  tests/python/          The CI-collected suite
  tests/cross_language/  Julia-vs-Python parity (NOT collected by CI)
  tests/julia/           Julia layers 1-4 (NOT collected by CI)
  ```

## Research Inputs

- From `research/2026-07-26-reopt-pysam-post-backlog-architecture-brainstorm.md`:
  - **Currency fragmentation is the largest correctness-adjacent defect and is invisible to every existing test**, because each module is internally consistent. Four rates (`26,400 / 26,000 / 25,450 / 25,000`) across 17 files, a 5.6% spread. Cross-case artifacts (`generate_cross_project_dashboard.py`, `integration/matching.py`, `integration/procurement.py`, the `match_*.json` reports) compare figures built on different denominators.
  - **The canonical FX value already exists and is orphaned:** `vn_deal_defaults_2026.json` is manifest-registered and regulatory-watch-listed, but absent from `load_vietnam_data()`'s `required_keys` and from the `VNData` dataclass. It is also the only data file lacking the `{_meta, data}` envelope, so adding it to the loader today would raise `KeyError`.
  - **`ContractParams.export_cap_pct` defaults to `20.0`** — the cap Decree 243/2026 repealed on 2026-06-26. The 2026-07-18 fix added a fifth preset rather than making the engine read the data layer; three presets remain pinned at the repealed value.
  - **The parity guarantee is enforced nowhere:** `test_samsung_ttc_parity.py` is `golden_machine` (CI-excluded) *and* both assertions are `xfail`. `README.md` and `docs/onsite_vs_offsite.md` both claim "parity-gated bit-for-bit".
  - **`generate_cross_project_dashboard.py:331` uses a comment inside an f-string** — valid from Python 3.12, a hard syntax error on 3.10/3.11, while `pyproject.toml` declares `requires-python = ">=3.10"`.
  - **The ruff backlog is tractable, not large:** 187 violations, 66 auto-fixable, and 35 of the 36 `F821`s are a single annotation pattern in one file. The CI comment framing this as "a larger follow-on effort" is stale.
  - **Sequencing decision:** the canonical assumptions resolver must land **before** any reporting-pipeline work, because building a template layer over 17 divergent FX constants would make the divergence structural.
  - **The FX migration must be two commits** — a value-preserving refactor first, then a deliberate value-changing flip with a delta memo — never one.
- From `research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md`:
  - The Julia half was already stale then and is now a scope **subset**: Python has `reopt/two_part_tariff.py`, `reopt/decree243_delta.py`, `reopt/regime_impact.py`, and `reopt/regime_runner.py` with no Julia counterpart. The recommended resolution (unchanged across passes) is archive-in-place, keeping the code because the Decree 57/243 export-cap JuMP constraint is genuinely Julia-only.
- From `lessons.md` (repo root, 2026-06-12 entries):
  - After **any** structural move, run the **full** test suite — `--collect-only` is not enough, and running a subset previously missed integration-test breakage.
  - Before deleting or moving a directory, grep for the **bare** directory name (e.g. `julia`), not the path form `julia/` — code builds paths from segments like `REPO_ROOT / "scripts" / "julia"`, which a `julia/` grep never matches.
  - Scope `.gitignore` negations precisely and run `git status` afterward; a loose negation silently re-tracks unrelated files.

## Assumptions and Constraints

- **ASM-001:** The intended minimum Python version is **3.10**, not 3.12 — it is the declared contract in `pyproject.toml` and `[tool.mypy] python_version = "3.10"` agrees. **BINDING DEFAULT:** treat `generate_cross_project_dashboard.py:331` as the bug and fix the f-string; do **not** raise `requires-python` to `>=3.12`.
- **ASM-002:** The canonical VND/USD rate is **26,400**, sourced from `vn_tariff_2025.json._meta.exchange_rate_vnd_per_usd` (Decision 599/QD-EVN, 2025-05-10) and mirrored with a citation in `vn_deal_defaults_2026.json`. It is the majority value, the only one with provenance, and already the fallback in both the Python and Julia loaders. **BINDING DEFAULT:** 26,400 becomes canonical; deals with a contractually fixed different rate carry it as an explicit per-deal override in their `*_extracted_inputs.json`, never as a module constant.
- **ASM-003:** `jsonschema` is **not** installed and must not become a runtime dependency — `data/schemas/deal_config.schema.json`'s own `description` field states it is "Validated structurally (no jsonschema dependency required at runtime)". **BINDING DEFAULT:** PHASE-02 implements a hand-rolled structural validator covering `required`, `type`, and `enum` only. Do not add `jsonschema` to `pyproject.toml`.
- **ASM-004:** The 35 `F821 Undefined name 'Check'` violations in `scripts/python/integration/verify_ceba_dppa_deck.py` are annotation-only and harmless at runtime (`from __future__ import annotations` is present; `Check` is resolved dynamically via `getattr(module, "Check")`). **BINDING DEFAULT:** fix with a `typing.TYPE_CHECKING` guarded import rather than restructuring the dynamic registry loading.
- **ASM-005:** Whether any *individual* published USD figure is wrong depends on which rate that deal's counterparty actually contracted at — a question repo inspection cannot answer. **BINDING DEFAULT:** PHASE-05's value-preserving commit changes no numbers; the value-changing commit flips **only** the four `scripts/python/reopt/*` and `src/python/reopt_pysam_vn/reopt/*` general-purpose modules to 26,400, and leaves the per-deal modules (`dppa_case_3.py`, `analyze_saigon18_*`, `build_saigon18_*`) on their deal-specific 25,450 rate, recorded as an explicit documented override.
- **ASM-006:** `analysis/__main__.py` reporting 0% coverage is a measurement artifact — `tests/python/analysis/test_cli.py` drives it as a subprocess, which `coverage` does not instrument. **BINDING DEFAULT:** do not "fix" this by rewriting the CLI test; note it in the coverage section of `docs/testing.md`.
- **ASM-007:** Adding Python 3.10 to the CI matrix will surface currently-unknown 3.10 incompatibilities beyond the one known syntax error. **BINDING DEFAULT:** if the 3.10 job fails on something outside `scripts/`, fix it if it is a genuine 3.10 incompatibility; if a dependency (e.g. a `nrel-pysam` wheel) is genuinely unavailable on 3.10, restrict the 3.10 job to `ruff check` plus a compile-only check (`python -m compileall`) and leave pytest on 3.12 — record the reason in a comment in `ci.yml`.
- **ASM-008:** `data/vietnam/vn_deal_defaults_2026.json` is currently read by **no** Python code path (only referenced as documentation strings in `scripts/python/integration/ceba_deck/deck_checks.py` and `july_deck_checks.py`, which resolve it through a separate ad-hoc loader in `verify_ceba_dppa_deck.py::resolve_data_vietnam`). **BINDING DEFAULT:** restructuring it into the `{_meta, data}` envelope requires updating those two ad-hoc reference strings and the `resolve_data_vietnam` path in `july_deck_checks.py:256` from `vn_deal_defaults_2026.sensitivity_ranges.*` to `vn_deal_defaults_2026.data.sensitivity_ranges.*`.
- **ASM-009:** The NREL Developer API key committed historically in commits `3911032` and `b14bc0b` has still not been confirmed rotated (open across seven sessions). **BINDING DEFAULT:** out of scope for this plan; `README.md`'s existing "API key rotation required" section already documents the requirement and must not be removed by PHASE-06's README rewrite.
- **CON-001:** **Samsung/TTC bit-exact parity is inviolable.** `examples/samsung-ttc_combined-decision.example.json` must not be edited casually. PHASE-03 may regenerate it only under the explicit, logged procedure specified there.
- **CON-002:** The webapp must never fork analytics logic — it always calls `run_onsite` / `run_offsite_dppa` / `run_vietnam_reopt` from `reopt_pysam_vn` as-is.
- **CON-003:** Windows-first repo. All CI changes target Linux runners; nothing may require a POSIX-only tool locally.
- **CON-004:** `ContractParams` is constructed at **24 call sites across 14 files**. No change may make any existing keyword argument required or rename any field.
- **DEC-001:** Theme E (assumptions resolver) is sequenced **ahead of** the config-driven case runner, reversing six prior passes' ordering, because a reporting template layer built over divergent FX constants would make the divergence structural.
- **DEC-002:** The FX migration ships as **two separate commits** — value-preserving refactor, then value-changing flip with a delta memo.
- **DEC-003:** The Samsung parity gate is **restored**, not documented away — the bit-exactness is the strongest correctness signal the repo has and its output goes to counterparties. PHASE-03 carries an explicit, fully-specified fallback if restoration proves infeasible.
- **DEC-004:** Julia is **archived in place** under `legacy/julia/`, not deleted — the Decree 57/243 export-cap JuMP constraint is Julia-only and has no Python equivalent.
- **DEC-005:** `reopt_pysam_vn/common/` is **promoted**, not deleted — it is the correct namespace for the resolver, and deleting-then-recreating would churn imports.

## Specification

### S1 — Canonical assumption resolution order

For any assumption `A` needed by any module, resolve in this exact order and stop at the first hit:

1. An explicit function argument passed by the caller (e.g. `exchange_rate_vnd_per_usd=25450.0`).
2. A per-deal value in the deal's `*_extracted_inputs.json`, at `benchmark.exchange_rate_vnd_per_usd` or `settlement_inputs.exchange_rate_vnd_per_usd`.
3. The regime-resolved data layer: `resolve_vietnam_regime(vn, regime_id)["export_rules"]` / `["tariff"]`.
4. The deal-defaults data file: `vn_deal_defaults_2026.json` → `data.*`.
5. **Never** a module-level literal. There is no step 5.

### S2 — Exchange-rate resolution

```
exchange_rate_vnd_per_usd = first_non_null(
    caller_argument,
    extracted["benchmark"]["exchange_rate_vnd_per_usd"],
    vn.deal_defaults["exchange_rate"]["vnd_per_usd"],
    vn.exchange_rate
)
```

Symbols:
- `caller_argument` — the value the calling function received as a keyword argument; `None` when not supplied.
- `extracted[...]` — the per-deal extracted-inputs dict; absent for deals that do not pin a rate.
- `vn.deal_defaults["exchange_rate"]["vnd_per_usd"]` — the new canonical field, `26400` (integer VND per one USD).
- `vn.exchange_rate` — the existing fallback already parsed from `vn_tariff_2025.json._meta.exchange_rate_vnd_per_usd`, currently `26400.0`.

Conversion direction, always:
```
value_usd = value_vnd / exchange_rate_vnd_per_usd
value_vnd = value_usd * exchange_rate_vnd_per_usd
```

### S3 — Settlement policy resolution

```
export_cap_fraction  = resolve_vietnam_regime(vn, regime_id)["export_rules"]["rooftop_solar"]["max_export_fraction"]
export_cap_pct       = export_cap_fraction * 100.0
surplus_rate_vnd_kwh = resolve_vietnam_regime(vn, regime_id)["export_rules"]["rooftop_solar"]["surplus_purchase_rate_vnd_per_kwh"]
dppa_adder_vnd_kwh   = vn.deal_defaults["dppa_settlement"]["adder_vnd_per_kwh"]
kpp_pct              = vn.deal_defaults["dppa_settlement"]["kpp_loss_pct"]
```

Symbols:
- `regime_id` — a key of `vn_regime_registry_2026.json` → `data.regimes`. Valid keys today: `decision_14_2025_current`, `decision_14_2025_legacy`, `decision_963_2026_current`, `decision_963_2026_repriced_multipliers`, `decree57_rooftop_50pct_draft`, `decree_57_2025_legacy`, `decree146_two_part_trial_2026`.
- `max_export_fraction` — a **fraction** in `[0, 1]`. `ContractParams.export_cap_pct` is a **percentage** in `[0, 100]`. The `* 100.0` is mandatory; conflating them is a 100× error.
- `adder_vnd_per_kwh` and `kpp_loss_pct` do **not exist in `data/vietnam/` today** — PHASE-04 creates them, seeded with the current code constants `523.34` and `2.7263` respectively (value-preserving).
- `kpp_pct` is a percentage; `ContractParams.kpp_factor` returns `1.0 + kpp_pct / 100.0`, i.e. `1.027263`.

### S4 — Preset → regime mapping (for the PHASE-04 drift guard)

| Preset key | Declared regime | Expected `export_cap_pct` | Expected `surplus_rate_vnd_kwh` |
|---|---|---|---|
| `decree57_private_wire_standard` | `decree_57_2025_legacy` | `20.0` | `671.0` |
| `virtual_cfd_matched_only` | `decree_57_2025_legacy` | `20.0` | `671.0` |
| `virtual_cfd_full_volume` | `decree_57_2025_legacy` | `20.0` | `671.0` |
| `physical_dppa_export_50pct` | `decision_963_2026_current` | `50.0` | `671.0` |
| `decree243_export_50pct_standard` | `decision_963_2026_current` | `50.0` | `671.0` |

The three `20.0` presets are **correct as legacy presets** once each declares `decree_57_2025_legacy` as its regime — the defect today is that they claim to be current-policy presets. The guard test asserts each preset's values equal `S3`'s resolution for its declared regime.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Reproducibility floor: 3.10 in CI, lint gate, fix the real syntax error | None | `ci.yml` matrix, `[tool.ruff]`, PySAM pin in `pyproject.toml`, 187→0 violations |
| PHASE-02 | Make `DealConfig` a validated contract | PHASE-01 | `analysis/validation.py`, schema-backed `from_dict` |
| PHASE-03 | Reconcile the Samsung parity gate with reality | PHASE-01 | Enforced gate in CI, or honest docs — never both-disabled-and-advertised |
| PHASE-04 | Canonical assumptions resolver + settlement drift guard | PHASE-01 | `common/assumptions.py`, `deal_defaults` in `VNData` (Python + Julia), preset guard test |
| PHASE-05 | FX unification, two commits | PHASE-04 | 22 literals routed through the resolver; delta memo |
| PHASE-06 | Archive Julia in place; honest README | PHASE-04 | `legacy/julia/`, rewritten stack section, `docs/legacy-path-map.md` entry |

## Detailed Phases

### PHASE-01 - Reproducibility Floor and Lint Gate

**Goal**
Make the declared Python floor real, turn on the lint gate the CI comment has deferred for six sessions, and fix the one violation that is a genuine bug.

**Tasks**
- [x] TASK-01-01: Fix the f-string syntax error at `scripts/python/integration/generate_cross_project_dashboard.py:331`. The line currently is `f'<td>{fmt_money(s * 65226 * 1000 / 26000 * 10.675)}</td>'  # rough 20yr NPV factor at 8% with 5% esc` — the trailing comment sits **inside** the f-string expression block spanning lines 327-334. Move the comment to its own line **above** the `{"".join(` expression that begins at line 327. Change no numbers.
- [x] TASK-01-02: Add a `[tool.ruff]` section to `pyproject.toml` (see File Changes for exact content). Set `target-version = "py310"` and `line-length = 120`. Ignore `E402` repo-wide — the `sys.path.insert(...)` -then-import pattern in `scripts/` is deliberate and already carries `# noqa: E402` in places.
- [x] TASK-01-03: Apply `ruff check --fix src scripts tests` to clear the 66 auto-fixable violations (`F401` unused-import ×48, `F841` unused-variable ×28, `F541` f-string-without-placeholders ×16, `E401`, `F811`). Review the diff before committing — do **not** use `--unsafe-fixes`.
- [x] TASK-01-04: Fix the 35 `F821 Undefined name 'Check'` violations in `scripts/python/integration/verify_ceba_dppa_deck.py` by adding a `TYPE_CHECKING`-guarded import. Do not restructure `_load_registry`.
- [x] TASK-01-05: Fix the residual violations: `E741` ambiguous-variable-name ×4, `E702` multiple-statements-on-one-line ×10, `E721` type-comparison ×1. For `E721`, replace `type(x) == T` with `isinstance(x, T)`.
- [x] TASK-01-06: Move the `nrel-pysam` pin from CI-only into `pyproject.toml`: change `"nrel-pysam>=7.1"` to `"nrel-pysam==7.1.0"` in `[project] dependencies`, and drop the trailing `"nrel-pysam==7.1.0"` from the CI `pip install` line.
- [x] TASK-01-07: Add a Python version matrix (`["3.10", "3.12"]`) to `.github/workflows/ci.yml` and add a `ruff check` step. Delete the stale 11-line comment explaining why ruff is absent.
- [x] TASK-01-08: If the 3.10 job fails for a reason other than the fixed syntax error, apply ASM-007's binding default.

**File Changes**
- `scripts/python/integration/generate_cross_project_dashboard.py` (modify): relocate the inline comment out of the f-string expression at line 331. Leave every numeric literal and all surrounding HTML untouched.
- `pyproject.toml` (modify): add a new `[tool.ruff]` + `[tool.ruff.lint]` section after the existing `[tool.mypy]` block; change `nrel-pysam>=7.1` → `nrel-pysam==7.1.0` in `[project] dependencies`. Leave `[tool.pytest.ini_options]`, `[tool.coverage.run]`, and the `markers` list untouched. Exact new section:
  ```toml
  [tool.ruff]
  target-version = "py310"
  line-length = 120
  extend-exclude = [".venv", "legacy", "artifacts", "present"]

  [tool.ruff.lint]
  # E402 (import-not-at-top) is repo-wide intentional: scripts under scripts/python/
  # bootstrap sys.path before importing reopt_pysam_vn. Do not "fix" these.
  ignore = ["E402"]
  ```
- `scripts/python/integration/verify_ceba_dppa_deck.py` (modify): after the existing `from typing import Any, Callable` on line 41, add `TYPE_CHECKING` to that import and insert below the import block:
  ```python
  if TYPE_CHECKING:  # pragma: no cover - annotation-only; Check is loaded dynamically at runtime
      from integration.ceba_deck.deck_checks import Check
  ```
  Leave `_load_registry`'s `getattr(module, "Check")` runtime lookup exactly as-is.
- `.github/workflows/ci.yml` (modify): add `strategy.matrix.python-version: ["3.10", "3.12"]`, wire `${{ matrix.python-version }}` into `actions/setup-python`, add a `ruff check src scripts tests` step before the mypy step, and delete the stale ruff-deferral comment. Keep the existing marker filter string and `PYTHONPATH: ""` env exactly as they are.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
- `python -m compileall -q scripts/python/integration/generate_cross_project_dashboard.py` under Python 3.10 → exit code `0`, no output. (Before the fix: `SyntaxError`.)
- `ruff check src scripts tests` → `All checks passed!`, exit code `0`.
- Full portable suite after all edits → still `589 passed, 18 deselected, 3 xfailed`. **Any change to these counts means TASK-01-03's auto-fix removed something load-bearing — revert and re-apply selectively.**
- `python -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); assert 'nrel-pysam==7.1.0' in d['project']['dependencies'], d['project']['dependencies']"` → exit code `0`.

**Dependencies**
- `ruff` must be installed: `python -m pip install ruff` (version 0.14.14 or later — earlier versions do not emit the `invalid-syntax` diagnostic used above).

**Exit Criteria**
- [ ] `ruff check src scripts tests` exits `0`.
- [ ] `python -m compileall -q src scripts tests` exits `0` under Python 3.10.
- [ ] CI shows two green jobs (3.10 and 3.12) on the branch.
- [ ] Test counts are unchanged at `589 passed, 18 deselected, 3 xfailed`.

**Phase Risks**
- **RISK-01-01:** `ruff --fix` removing an "unused" import that is actually a side-effecting import (e.g. registering an orchestrator). Mitigation: read the full `--fix` diff before committing; specifically check every removed import in `src/python/reopt_pysam_vn/analysis/` and `integration/`, where the registry pattern lives. Run the full suite after.
- **RISK-01-02:** the 3.10 CI job fails on a `nrel-pysam` wheel that does not publish for 3.10. Mitigation: apply ASM-007 — degrade the 3.10 job to `ruff check` + `compileall` and comment the reason inline.

---

### PHASE-02 - Make DealConfig a Validated Contract

**Goal**
Wire the shipped `data/schemas/deal_config.schema.json` into the public API so `DealConfig.from_dict` rejects malformed input with an actionable message instead of accepting arbitrary dicts.

**Tasks**
- [x] TASK-02-01: Write failing tests first (`tests/python/analysis/test_validation.py`) covering the Test Specs below. Run them and confirm they fail before implementing.
- [x] TASK-02-02: Create `src/python/reopt_pysam_vn/analysis/validation.py` with a dependency-free structural validator supporting exactly three JSON Schema keywords: `required`, `type`, and `enum`. Ignore all other keywords (`description`, `$id`, `additionalProperties`, `properties` nesting beyond one level for the six known sections).
- [x] TASK-02-03: Call the validator from `DealConfig.from_dict` in `src/python/reopt_pysam_vn/analysis/types.py`, replacing the existing bare `d["case"]` `KeyError` path. Keep the existing `__post_init__` `mode` check (it guards direct construction, which bypasses `from_dict`).
- [x] TASK-02-04: Add a `validate: bool = True` keyword to `from_dict` so a caller with a deliberately partial config can opt out. Default `True`.
- [x] TASK-02-05: Confirm the Samsung/TTC and sample fixture configs still validate: `scenarios/case_studies/samsung_ttc/samsung_ttc_deal_config.json` and `tests/python/analysis/fixtures/sample_deal_config.json`.

**File Changes**
- `src/python/reopt_pysam_vn/analysis/validation.py` (create): the validator module. Loads the schema from `<repo_root>/data/schemas/deal_config.schema.json` with `encoding="utf-8-sig"` (Windows editors emit a BOM — every other JSON reader in this repo uses `utf-8-sig`; matching that is mandatory). Cache the parsed schema in a module-level variable so repeated `from_dict` calls do not re-read the file.
- `src/python/reopt_pysam_vn/analysis/types.py` (modify): in `DealConfig.from_dict`, call `validate_deal_config(d)` before constructing. Add the `validate: bool = True` keyword. Do **not** change `to_dict`, the `raw` escape-hatch behavior, or any of `OnsiteResult` / `OffsiteDppaResult` / `CombinedDecision`.
- `src/python/reopt_pysam_vn/analysis/__init__.py` (modify): export `DealConfigValidationError` alongside the existing exports.
- `tests/python/analysis/test_validation.py` (create): the tests below.

**Function Signatures**
- `validate_deal_config(d: Dict[str, Any], *, schema: Optional[Dict[str, Any]] = None) -> None` — returns `None` on success; raises `DealConfigValidationError` listing **every** violation found, not just the first.
- `load_deal_config_schema() -> Dict[str, Any]` — returns the parsed schema dict, cached after first read.
- `class DealConfigValidationError(ValueError)` — carries a `.errors: list[str]` attribute of human-readable violation strings.
- `DealConfig.from_dict(cls, d: Dict[str, Any], *, validate: bool = True) -> "DealConfig"` — unchanged behavior when the dict is valid; raises `DealConfigValidationError` when it is not and `validate` is `True`.

**Test Specs**
- `validate_deal_config({"case": "X", "mode": "onsite"})` → returns `None` (both required fields present; all sections optional).
- `validate_deal_config({"mode": "onsite"})` → raises `DealConfigValidationError` with `.errors == ["missing required property: 'case'"]`.
- `validate_deal_config({})` → raises `DealConfigValidationError` with `.errors` containing **both** `"missing required property: 'case'"` and `"missing required property: 'mode'"` (proves all-errors collection, not fail-fast).
- `validate_deal_config({"case": "X", "mode": "hybrid"})` → raises; `.errors[0]` contains `"mode"`, `"hybrid"`, and the three allowed values `onsite`, `offsite_dppa`, `both`.
- `validate_deal_config({"case": 123, "mode": "onsite"})` → raises; error names `case` and the expected type `string`.
- `validate_deal_config({"case": "X", "mode": "onsite", "site": {"region": "westeros"}})` → raises; error names `site.region` and lists `north`, `central`, `south`.
- `validate_deal_config({"case": "X", "mode": "onsite", "site": {"region": "south", "province": "Binh Thuan"}})` → returns `None` (`province` is a free string; unknown extra keys are allowed since the schema sets `additionalProperties: true`).
- `validate_deal_config({"case": "X", "mode": "onsite", "plant": {"capacity_mwp": "big"}})` → raises; error names `plant.capacity_mwp` and expected type `number`.
- `validate_deal_config({"case": "X", "mode": "onsite", "site": "south"})` → raises; error names `site` and expected type `object`.
- `DealConfig.from_dict({"mode": "onsite"})` → raises `DealConfigValidationError` (not a bare `KeyError`).
- `DealConfig.from_dict({"mode": "onsite"}, validate=False)` → raises `KeyError: 'case'` (opt-out preserves the old behavior exactly).
- `DealConfig.from_dict(json.load(open("scenarios/case_studies/samsung_ttc/samsung_ttc_deal_config.json", encoding="utf-8-sig")))` → succeeds, `.case == "DPPA_SAMSUNG_TTC"`.
- Integer-vs-number edge case: `validate_deal_config({"case": "X", "mode": "onsite", "contract": {"tenor_years": 20}})` → returns `None`; `{"contract": {"tenor_years": 20.5}}` → raises (schema declares `integer`). Note Python `bool` is a subclass of `int` — `{"contract": {"tenor_years": True}}` must **raise**, so check `isinstance(v, bool)` **before** `isinstance(v, int)`.

**Dependencies**
- None beyond the standard library. **Do not add `jsonschema`** (ASM-003).

**Exit Criteria**
- [ ] `PYTHONPATH= python -m pytest tests/python/analysis/test_validation.py -v` → all pass.
- [ ] Full portable suite still green with no reduction in passing count.
- [ ] `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` → `Success: no issues found`.
- [ ] `PYTHONPATH= python -c "import json,sys; sys.path.insert(0,'src/python'); from reopt_pysam_vn.analysis.types import DealConfig; DealConfig.from_dict(json.load(open('tests/python/analysis/fixtures/sample_deal_config.json',encoding='utf-8-sig')))"` → exit code `0`.

**Phase Risks**
- **RISK-02-01:** the webapp's form-submission path (`src/python/reopt_pysam_vn/webapp/forms.py`) builds a dict that the schema rejects, breaking `/deals/new`. Mitigation: before implementing, run the webapp test suite (`PYTHONPATH= python -m pytest tests/python/webapp/ -q`) and confirm it stays green after; `forms.py:71` already documents that its sections mirror this schema, so a mismatch is a real bug to fix in `forms.py`, not a reason to weaken the validator.

---

### PHASE-03 - Reconcile the Samsung/TTC Parity Gate

**Goal**
End the state where the repo's headline correctness guarantee is disabled twice (CI-excluded **and** `xfail`) while `README.md` advertises it as enforced. Either it is enforced, or the docs say what is actually true.

**Tasks**
- [x] TASK-03-01: Reproduce the divergence. Run `PYTHONPATH= python -m pytest tests/python/analysis/test_samsung_ttc_parity.py -v -rX --runxfail` and capture the actual failure output to `reports/2026-07-26-samsung-parity-diagnosis.md`. The known symptom from the 2026-07-22 investigation: `developer_irr_fraction` computes `0.0289...` where the golden holds `None`; max relative diff `1.123`.
- [x] TASK-03-02: Determine whether the divergence is environmental (PVWatts resource cache) or logical. Check whether `data/interim/pysam_resources/` contains the resource file the run consumes and whether it is git-tracked: `git ls-files data/interim/pysam_resources/`.
- [ ] TASK-03-03: **Branch A (preferred, per DEC-003) — restore the gate.** N/A — not taken. Candidate regeneration (into a scratch file, never committed) showed the divergence is **not** confined to the single documented `developer_irr_fraction` field: `developer_npv_usd` also moves substantially (~5x magnitude change) across all 5 swept strike prices, and one candidate's `developer_passes` verdict flips. Per RISK-03-01/MANUAL-002 this triggers Branch B instead.
- [x] TASK-03-04: **Branch B (fallback) — honest documentation.** Taken. `golden_machine` marker and both `xfail`s retained in `test_samsung_ttc_parity.py` (unchanged); `README.md` and `docs/onsite_vs_offsite.md` amended so neither claims an enforced bit-for-bit gate — both now describe it as a local-only, CI-excluded, currently-xfailed diagnostic and point to the diagnosis report.
- [x] TASK-03-05: Regardless of branch, add `tests/cross_language/` to CI's awareness by documenting in `docs/testing.md` that Layers 1-4 Julia and Layer 3 cross-validation are **not** CI-collected (CI runs `pytest tests/python` only), so the "identical output, max diff 0.00e+00" claim in `docs/architecture.md` is a manual-verification claim.
- [x] TASK-03-06: Amend `docs/architecture.md`'s "produce identical output (verified by Layer 3 cross-validation, max diff = 0.00e+00)" to state **when** that verification runs (locally, via `tests/run_all_tests.ps1`) and that it is not automated.

**File Changes**
- `reports/2026-07-26-samsung-parity-diagnosis.md` (create): the captured failure output, the branch taken, and why. This is a tracked Markdown deliverable per the repo's `reports/*.md` convention.
- `tests/python/analysis/test_samsung_ttc_parity.py` (modify): **Branch A** — delete line 31 (`pytestmark = pytest.mark.golden_machine`) and both `@pytest.mark.xfail(...)` decorators at lines 78 and 103. **Branch B** — leave the file unchanged, and add a module-docstring paragraph stating explicitly that this test is CI-excluded and `xfail`ed, with a pointer to the diagnosis report.
- `examples/samsung-ttc_combined-decision.example.json` (modify, **Branch A only**): regenerated golden. Commit alone, never bundled with other changes.
- `README.md` (modify): the line "Samsung-TTC is parity-gated bit-for-bit (`tests/python/analysis/test_samsung_ttc_parity.py`)" becomes either (Branch A) unchanged and now true, or (Branch B) "Samsung-TTC has a bit-for-bit parity check (`tests/python/analysis/test_samsung_ttc_parity.py`); it is a **local-only diagnostic** — it is excluded from CI and currently `xfail`ed pending the divergence documented in `reports/2026-07-26-samsung-parity-diagnosis.md`."
- `docs/onsite_vs_offsite.md` (modify): apply the same correction to the "**Samsung-TTC** is parity-gated" bullet.
- `docs/testing.md` (modify): add a "What CI actually runs" subsection naming the exact command and stating that `tests/julia/` and `tests/cross_language/` are outside it. Also record ASM-006 (the `__main__.py` 0%-coverage measurement artifact).
- `docs/architecture.md` (modify): qualify the Layer 3 equivalence claim as manually verified.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
- **Branch A:** `PYTHONPATH= python -m pytest tests/python/analysis/test_samsung_ttc_parity.py -v` → `2 passed` (no `xfail`, no `xpass`), and the same command **without** any `-m` marker filter must be collected by the CI filter string: verify with `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" --collect-only -q | grep test_samsung_ttc_parity` → 2 matching lines.
- **Branch B:** `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" --collect-only -q | grep -c test_samsung_ttc_parity` → `0`, **and** `grep -c "local-only diagnostic" README.md` → `1`.
- Both branches: `grep -n "parity-gated bit-for-bit" README.md docs/onsite_vs_offsite.md` → either zero hits (Branch B rewrote them) or hits that are now factually true (Branch A).

**Dependencies**
- PySAM 7.1.0 must be importable, and the PVWatts resource under `data/interim/pysam_resources/` must be present, or the test skips rather than runs.

**Exit Criteria**
- [x] `reports/2026-07-26-samsung-parity-diagnosis.md` exists and names the branch taken with evidence.
- [x] No document in the repo claims an enforced parity gate that is not enforced. Verify: `grep -rn "parity-gated" README.md docs/` and read each hit.
- [x] Full portable suite green.

**Phase Risks**
- **RISK-03-01:** regenerating the golden silently launders a real regression into the baseline. Mitigation: TASK-03-01's diagnosis report must be written **and reviewed** before TASK-03-03 runs; the regenerated golden ships in its own commit so `git diff HEAD~1 examples/samsung-ttc_combined-decision.example.json` shows exactly which fields moved. If more than the known `developer_irr_fraction` field changes, stop and take Branch B.
- **RISK-03-02:** un-`xfail`ing makes CI red on a machine-dependent PVWatts result. Mitigation: TASK-03-02 gates Branch A on the resource being git-tracked; if `git ls-files data/interim/pysam_resources/` returns nothing, Branch A is not available.

---

### PHASE-04 - Canonical Assumptions Resolver

**Goal**
Give the toolkit exactly one place that answers "what assumption applies here?", make the orphaned `vn_deal_defaults_2026.json` load-bearing, and mechanically prevent the settlement engine from drifting from the data layer again.

**Tasks**
- [x] TASK-04-01: Write failing tests first (`tests/python/common/test_assumptions.py`, `tests/python/integration/test_settlement_policy_drift.py`). Confirm red before implementing.
- [x] TASK-04-02: Restructure `data/vietnam/vn_deal_defaults_2026.json` into the `{"_meta": {...}, "data": {...}}` envelope every other data file uses. Move `exchange_rate`, `debt_terms`, `analysis`, `dppa`, `bess`, `sensitivity_ranges` under a new `"data"` key. Keep `_meta` exactly as-is but bump `version` to `"2026.2"` and set `last_updated` to `"2026-07-26"`, appending a `changelog` entry: `"2026.2: Wrapped payload in the standard {_meta, data} envelope so load_vietnam_data() can read it. Added data.dppa_settlement block (adder_vnd_per_kwh 523.34, kpp_loss_pct 2.7263) seeded from the previously code-only constants in integration/settlement.py. No numeric values changed."`
- [x] TASK-04-03: Add a `dppa_settlement` block inside `data` with `{"adder_vnd_per_kwh": 523.34, "kpp_loss_pct": 2.7263, "source": "Seeded from integration/settlement.py ContractParams defaults, 2026-07-26. Originally derived from the Decree 57/2025 DPPA fee structure; no primary-source citation was recorded when introduced."}`.
- [x] TASK-04-04: Fix the two ad-hoc reference strings broken by the envelope change (ASM-008): `scripts/python/integration/ceba_deck/july_deck_checks.py:256` and the `resolve_data_vietnam(...)` call at `scripts/python/integration/verify_ceba_dppa_deck.py:434` must become `data.vietnam.vn_deal_defaults_2026.data.sensitivity_ranges.fmp_vnd_per_kwh`. The `repo_fn` string at `scripts/python/integration/ceba_deck/deck_checks.py:230` already contains `.data.` and needs no change. **Additional readers found beyond ASM-008's two:** `scripts/python/integration/ceba_deck/july_runners.py`'s `_resolve_vietnam_data` call, and six CLI scripts (`bess_dispatch_analysis.py`, `bess_regime_comparison.py` (via import), `dppa_settlement.py`, `equity_irr.py`, `fmp_sensitivity.py`, `sensitivity_sweep.py`) whose own `load_deal_config`/`load_config` read the file flat (`cfg.get("debt_terms", {})` etc.) — fixed by unwrapping `raw.get("data", raw)` in each, and `tests/python/reopt/test_unit.py::TestDealDefaultsConfig` (3 tests) which asserted the pre-envelope flat shape.
- [x] TASK-04-05: Add `deal_defaults` to the Python loader: append `"deal_defaults"` to `required_keys` in `load_vietnam_data()` (`src/python/reopt_pysam_vn/reopt/preprocess.py:180-187`), add `deal_defaults: Dict[str, Any]` to the `VNData` dataclass (line 91-102), load it via the existing `_load("deal_defaults")` helper, and pass `deal_defaults=deal_defaults_raw["data"]` to the constructor.
- [x] TASK-04-06: Mirror the same change in the Julia twin: add `"deal_defaults"` to `required_keys` at `src/julia/REoptVietnam.jl:117`, add a `deal_defaults::Dict{String,Any}` field to the `VNData` struct (line 91-99, inserted **before** `exchange_rate` to match the Python field order), load via the existing `_load` closure, and pass it positionally in the `VNData(...)` construction at line 141. **The struct is positional — inserting a field in the wrong position silently mis-assigns every subsequent field.**
- [x] TASK-04-07: Promote `src/python/reopt_pysam_vn/common/` — create `assumptions.py` implementing the S1/S2/S3 resolution. Leave the three existing stub modules in place (they are harmless and removing them churns nothing useful).
- [x] TASK-04-08: Add a `regime_id: str` field to `ContractParams` with default `"decree_57_2025_legacy"`, and a `ContractParams.from_regime(...)` classmethod. **Do not change any existing field's name, type, or default** (CON-004: 24 call sites).
- [x] TASK-04-09: Set the correct `regime_id` on each of the five entries in `PRESET_CONTRACTS` per the S4 table. Change no other preset value.
- [x] TASK-04-10: Add the drift-guard test asserting every preset's policy values equal the S3 resolution for its declared `regime_id`.
- [x] TASK-04-11: Update `data/vietnam/vn_tariff_2025.json` → `data.decree_57_dppa.models.private_wire.rooftop_solar_surplus_export_cap_pct`, currently `20`, which is a **second stale copy** of the repealed cap living outside the export-rules file. Do **not** change the number (it correctly describes Decree 57, which the `decree_57_2025_legacy` regime still needs). Instead append to the sibling `notes` string: `"NOTE (2026-07-26): this 20% figure describes Decree 57/2025 as originally enacted. Decree 243/2026 (eff. 2026-06-26) raised the general cap to 50%; the authoritative current value is data/vietnam/vn_export_rules_2026_decree243.json -> rooftop_solar.max_export_fraction. Resolve export caps via reopt_pysam_vn.common.assumptions.export_cap_fraction(), never from this field."`
- [x] TASK-04-12: Update `docs/regulatory-watch.md`'s `deal_defaults` row to note the envelope change and the new `dppa_settlement` block.

**File Changes**
- `data/vietnam/vn_deal_defaults_2026.json` (modify): envelope restructure + new `data.dppa_settlement` block + `_meta` version bump. **No existing numeric value changes.**
- `data/vietnam/vn_tariff_2025.json` (modify): append the cross-reference sentence to the `decree_57_dppa.models.private_wire.notes` string. Change no numbers.
- `src/python/reopt_pysam_vn/reopt/preprocess.py` (modify): `VNData` gains `deal_defaults`; `load_vietnam_data()` requires and loads it. Leave `DEFAULT_EXCHANGE_RATE`, `resolve_vietnam_regime`, and every `apply_*` function untouched in this phase — FX call sites move in PHASE-05.
- `src/julia/REoptVietnam.jl` (modify): `VNData` struct gains `deal_defaults::Dict{String,Any}` before `exchange_rate`; `load_vietnam_data` requires and loads it.
- `src/python/reopt_pysam_vn/common/assumptions.py` (create): the resolver.
- `src/python/reopt_pysam_vn/common/__init__.py` (modify): export the resolver functions.
- `src/python/reopt_pysam_vn/integration/settlement.py` (modify): add `regime_id` field + `from_regime` classmethod to `ContractParams`; set `regime_id` on all five presets. Leave `compute_hourly_settlement`, `compute_buyer_benchmark`, `run_strike_sweep`, and every existing field default untouched.
- `scripts/python/integration/ceba_deck/july_deck_checks.py` (modify): the one `repo_fn` path string at line 256.
- `scripts/python/integration/verify_ceba_dppa_deck.py` (modify): the `resolve_data_vietnam` argument at line 434.
- `docs/regulatory-watch.md` (modify): the `deal_defaults` row.
- `tests/python/common/__init__.py` (create): empty, to match the package-per-test-dir convention.
- `tests/python/common/test_assumptions.py` (create).
- `tests/python/integration/test_settlement_policy_drift.py` (create).

**Function Signatures**
- `exchange_rate(vn: VNData, *, caller_value: Optional[float] = None, extracted: Optional[Dict[str, Any]] = None) -> float` — returns VND per USD per S2's precedence chain; raises `ValueError` if the resolved value is `<= 0`.
- `export_cap_fraction(vn: VNData, *, regime_id: str = "decision_963_2026_current") -> float` — returns `max_export_fraction` as a fraction in `[0, 1]` for the resolved regime.
- `surplus_rate_vnd_per_kwh(vn: VNData, *, regime_id: str = "decision_963_2026_current") -> float` — returns the surplus purchase rate in VND per kWh.
- `dppa_adder_vnd_per_kwh(vn: VNData) -> float` — returns `data.dppa_settlement.adder_vnd_per_kwh`.
- `kpp_loss_pct(vn: VNData) -> float` — returns `data.dppa_settlement.kpp_loss_pct` as a percentage (e.g. `2.7263`, not `0.027263`).
- `ContractParams.from_regime(cls, regime_id: str, *, mode: str, strike_vnd_kwh: float, vn: Optional[VNData] = None, **overrides: Any) -> ContractParams` — builds a `ContractParams` whose `export_cap_pct`, `surplus_rate_vnd_kwh`, `dppa_adder_vnd_kwh`, and `kpp_pct` are resolved from the data layer for `regime_id`; `**overrides` wins over resolution. Loads `VNData` itself when `vn` is `None`.

**Test Specs**
- `load_vietnam_data().deal_defaults["exchange_rate"]["vnd_per_usd"]` → `26400`.
- `load_vietnam_data().deal_defaults["dppa_settlement"]["adder_vnd_per_kwh"]` → `523.34`.
- `exchange_rate(vn)` → `26400.0`.
- `exchange_rate(vn, caller_value=25450.0)` → `25450.0` (caller wins over everything).
- `exchange_rate(vn, extracted={"benchmark": {"exchange_rate_vnd_per_usd": 25000.0}})` → `25000.0`.
- `exchange_rate(vn, caller_value=25450.0, extracted={"benchmark": {"exchange_rate_vnd_per_usd": 25000.0}})` → `25450.0` (precedence: caller beats extracted).
- `exchange_rate(vn, caller_value=0.0)` → raises `ValueError`.
- `exchange_rate(vn, extracted={"benchmark": {}})` → `26400.0` (missing key falls through, does not raise).
- `export_cap_fraction(vn, regime_id="decision_963_2026_current")` → `0.5`.
- `export_cap_fraction(vn, regime_id="decree_57_2025_legacy")` → `0.2`.
- `export_cap_fraction(vn, regime_id="decree57_rooftop_50pct_draft")` → `0.5`.
- `export_cap_fraction(vn, regime_id="not_a_regime")` → raises `ValueError` whose message lists the seven valid regime ids.
- `surplus_rate_vnd_per_kwh(vn, regime_id="decision_963_2026_current")` → `671.0`.
- `kpp_loss_pct(vn)` → `2.7263`; and `ContractParams(mode="virtual_cfd", strike_vnd_kwh=1800.0, kpp_pct=kpp_loss_pct(vn)).kpp_factor` → `1.027263`.
- **Drift guard**, for each of the five presets in the S4 table: `PRESET_CONTRACTS[key].export_cap_pct == export_cap_fraction(vn, regime_id=PRESET_CONTRACTS[key].regime_id) * 100.0` → `True`, and the same for `surplus_rate_vnd_kwh`. This is the test that would have caught the Decree 243 drift.
- **Backwards compatibility:** `ContractParams(mode="private_wire", strike_vnd_kwh=1012.0)` (no `regime_id`) → constructs successfully with `export_cap_pct == 20.0`, proving CON-004 holds for all 24 existing call sites.
- `ContractParams.from_regime("decision_963_2026_current", mode="private_wire", strike_vnd_kwh=1012.0).export_cap_pct` → `50.0`.
- `ContractParams.from_regime("decision_963_2026_current", mode="private_wire", strike_vnd_kwh=1012.0, export_cap_pct=99.0).export_cap_pct` → `99.0` (override wins).
- **Fraction-vs-percent guard:** `ContractParams.from_regime("decision_963_2026_current", mode="private_wire", strike_vnd_kwh=1012.0).export_cap_pct` must be `50.0`, **not** `0.5`. Assert `> 1.0` explicitly.
- **Julia twin:** `julia --project --compile=min tests/julia/test_unit.jl` → all Layer 2 tests pass with the new struct field.

**Dependencies**
- PHASE-01 (lint gate green, so new files land clean).

**Exit Criteria**
- [ ] `PYTHONPATH= python -m pytest tests/python/common/ tests/python/integration/test_settlement_policy_drift.py -v` → all pass.
- [ ] Full portable suite green with **no** change to any existing numeric assertion — this phase is strictly additive.
- [ ] `PYTHONPATH= python tests/cross_language/cross_validate.py` → still reports exact match, max diff `0.00e+00`, for all exercised regimes (proves the Julia struct change did not mis-assign fields).
- [ ] `ruff check src scripts tests` exits `0`.
- [ ] `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` → clean.

**Phase Risks**
- **RISK-04-01:** the Julia `VNData` struct is **positional**; inserting `deal_defaults` at the wrong index silently shifts `exchange_rate`, `regimes`, and `data_dir` into each other's slots with no error. Mitigation: TASK-04-06 specifies the exact insertion point (before `exchange_rate`), and the Layer 3 cross-validation in Exit Criteria is the detector — it must be run, not assumed.
- **RISK-04-02:** the envelope restructure of `vn_deal_defaults_2026.json` breaks the two ad-hoc `resolve_data_vietnam` readers. Mitigation: TASK-04-04 fixes them explicitly; verify with `PYTHONPATH= python -m pytest tests/python/integration/ -q` and by grepping for any other reader: `grep -rn "vn_deal_defaults_2026" --include=*.py src scripts tests | grep -v __pycache__`.
- **RISK-04-03:** the drift-guard test fails immediately on the three legacy presets if their `regime_id` is set wrong. Mitigation: the S4 table fixes the mapping; the three `20.0` presets map to `decree_57_2025_legacy`, whose `export_rule_overrides` genuinely resolve to `0.2`.

---

### PHASE-05 - Exchange-Rate Unification (Two Commits)

**Goal**
Route all 22 hardcoded VND/USD literals through the PHASE-04 resolver, in a way that makes it provable which commit changed numbers and which did not.

**Tasks**

**Commit 1 — value-preserving refactor (changes no output):**
- [x] TASK-05-01: For each of the 22 sites listed in File Changes, replace the module-level literal with a resolver call **that passes the module's current value as an explicit `caller_value`**. Example: `EXCHANGE_RATE_VND_PER_USD = 26_400.0` becomes a call whose result is still exactly `26400.0`. Every number the toolkit emits must be byte-identical after this commit.
- [x] TASK-05-02: Run the full portable suite and confirm `589 passed` (plus any tests added in PHASE-02/03/04) with **zero** changed numeric assertions. (634 passed after PHASE-02/03/04 additions; unchanged across Commit 1.)
- [x] TASK-05-03: Regenerate the two tracked golden artifacts and confirm zero diff: `git diff --exit-code examples/` → exit code `0`.
- [x] TASK-05-04: Commit with message `refactor(fx): route exchange-rate reads through common.assumptions (value-preserving, no numbers change)`.

**Commit 2 — value-changing flip (moves numbers deliberately):**
- [x] TASK-05-05: Remove the explicit `caller_value` pass-through from the **general-purpose** modules only, letting them resolve to the canonical 26,400: `src/python/reopt_pysam_vn/reopt/two_part_tariff.py:23` (26,000 → 26,400), `src/python/reopt_pysam_vn/integration/dppa_case_2.py:668,801,968` (25,000 fallback → 26,400), `scripts/python/reopt/two_part_tariff_sensitivity.py:39` (26,000 → 26,400), `scripts/python/reopt/build_saigon18_reopt_input.py:40` (26,000 → 26,400).
- [x] TASK-05-06: **Leave the per-deal 25,450 sites unchanged** per ASM-005 — `src/python/reopt_pysam_vn/integration/dppa_case_3.py:65`, `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py:38`, `..._phase_f_22kv.py:28`, `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py:63,183`. Convert each to an explicit, commented deal-specific override: `# Deal-specific FX: Saigon18 contract basis, 25,450 VND/USD. Intentionally NOT the repo canonical 26,400 (see plans/2026-07-26-post-backlog-architecture-plan.md ASM-005).`
- [x] TASK-05-07: Identify every test whose expected value moves. Update each with a comment naming this plan and the old→new value. (One test moved: `tests/python/reopt/test_two_part_tariff.py::test_compute_two_part_impact_high_load_factor`.)
- [x] TASK-05-08: Write `reports/2026-07-26-fx-unification-delta.md` quantifying, for each affected case, the before/after on at least: developer NPV (USD), developer IRR (fraction), and buyer blended cost (USD/kWh). (Neither flipped module produces a financed NPV/IRR; the memo documents this and uses the closest available proxies — see its "Note on developer NPV/IRR figures" section.)
- [x] TASK-05-09: Commit with message `fix(fx): unify general-purpose modules on the canonical 26,400 VND/USD` and the delta memo in the same commit.

**File Changes**
Commit 1 touches all 17 files (22 sites). Enumerated exactly:
- `src/python/reopt_pysam_vn/integration/dppa_case_2.py` (modify): lines 668, 801, 968 — `or 25_000.0` fallbacks.
- `src/python/reopt_pysam_vn/integration/dppa_case_3.py` (modify): line 65 — `exchange_rate = 25_450.0`.
- `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` (modify): line 90 — `EXCHANGE_RATE_VND_PER_USD = 26_400.0`. **Highest risk file** — it is the parity-gated golden path; its value is already canonical so Commit 2 must not touch it.
- `src/python/reopt_pysam_vn/integration/factory_a.py` (modify): line 44.
- `src/python/reopt_pysam_vn/reopt/decree243_delta.py` (modify): lines 37, 93 — default parameter values.
- `src/python/reopt_pysam_vn/reopt/preprocess.py` (modify): line 43 — `DEFAULT_EXCHANGE_RATE`. Keep the constant as the last-resort fallback; it is what the resolver's own final step reads.
- `src/python/reopt_pysam_vn/reopt/two_part_tariff.py` (modify): line 23 — 26,000. **Flipped in Commit 2.**
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py` (modify): line 38.
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f_22kv.py` (modify): line 28.
- `scripts/python/integration/build_ninhsim_extracted_inputs.py` (modify): line 23.
- `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py` (modify): lines 63, 183.
- `scripts/python/reopt/bess_dispatch_analysis.py` (modify): line 27.
- `scripts/python/reopt/build_saigon18_reopt_input.py` (modify): line 40 — 26,000. **Flipped in Commit 2.**
- `scripts/python/reopt/decree146_demand_charge.py` (modify): line 36.
- `scripts/python/reopt/decree243_export_cap_delta.py` (modify): line 31.
- `scripts/python/reopt/dppa_settlement.py` (modify): line 22.
- `scripts/python/reopt/fmp_sensitivity.py` (modify): line 39.
- `scripts/python/reopt/two_part_tariff_sensitivity.py` (modify): line 39 — 26,000. **Flipped in Commit 2.**
- `reports/2026-07-26-fx-unification-delta.md` (create, Commit 2).

**Function Signatures**
None — no new interfaces; this phase consumes PHASE-04's `exchange_rate()`.

**Test Specs**
- **Commit 1 gate (the single most important check in this plan):**
  ```bash
  git stash && PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q > /tmp/before.txt; git stash pop
  PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q > /tmp/after.txt
  diff /tmp/before.txt /tmp/after.txt
  ```
  → **empty diff.** Any difference means Commit 1 changed a number and must be reworked.
- **Commit 1 golden gate:** `git diff --exit-code examples/` → exit code `0`.
- **Commit 2 expected movement:** `two_part_tariff` USD outputs scale by exactly `26000 / 26400 = 0.984848...` — i.e. a USD figure previously `X` becomes `X * 0.98485`. Assert one concrete case in the delta memo with both figures.
- **Commit 2 non-movement guard:** `git diff --exit-code examples/samsung-ttc_combined-decision.example.json` → exit code `0`. Samsung is already on 26,400; if it moves, TASK-05-05 touched a file it should not have.
- Per-deal override guard: `grep -c "Intentionally NOT the repo canonical" src/python/reopt_pysam_vn/integration/dppa_case_3.py` → `1`.

**Dependencies**
- PHASE-04 must be complete and green — the resolver must exist before anything calls it.

**Exit Criteria**
- [x] Exactly two commits, in order, with the specified messages.
- [x] Commit 1's test output is byte-identical to the pre-change run.
- [x] `reports/2026-07-26-fx-unification-delta.md` exists and quantifies NPV, IRR, and blended cost deltas for every case Commit 2 moved (with an explicit note where NPV/IRR do not apply to the flipped modules).
- [x] `grep -rnE "EXCHANGE_RATE[A-Z_]* *= *2[0-9][,_]?[0-9]{3}" --include=*.py src scripts | grep -v __pycache__ | grep -v "Intentionally NOT"` → returns only `preprocess.py`'s `DEFAULT_EXCHANGE_RATE` last-resort fallback.
- [x] Full portable suite green. (634 passed, 18 deselected, 3 xfailed.)

**Phase Risks**
- **RISK-05-01:** Commit 1 accidentally changes a value, making Commit 2's delta memo untrustworthy. Mitigation: the byte-identical `diff` gate above is mandatory and must be run before committing, not after.
- **RISK-05-02:** `dppa_samsung_ttc.py` is on the parity-gated path; any FX change there breaks the golden. Mitigation: its value is already 26,400, so Commit 2 must not list it. The Commit 2 non-movement guard detects a mistake.
- **RISK-05-03:** a test asserts a USD figure to more precision than the 0.98485 scaling preserves, producing a confusing near-miss. Mitigation: TASK-05-07 requires updating each moved assertion with an explicit old→new comment rather than loosening tolerances.

---

### PHASE-06 - Archive Julia In Place and Tell the Truth About the Stack

**Goal**
End the ambiguity about whether Julia is core or cruft, without losing the one capability it uniquely provides.

**Tasks**
- [x] TASK-06-01: **Before moving anything**, grep for the **bare** directory name, not the path form — code builds paths from segments. Run all of:
  ```bash
  grep -rn '"julia"' --include=*.py --include=*.ps1 --include=*.jl . | grep -v __pycache__ | grep -v "^./.venv"
  grep -rn "scripts/julia\|src/julia" --include=* . | grep -v __pycache__ | grep -v "^./.git" | grep -v "^./.venv"
  ```
  Record every hit; each is a call site that must be updated.
- [x] TASK-06-02: Move with `git mv` (never copy-delete): `src/julia/` → `legacy/julia/src/`, `scripts/julia/` → `legacy/julia/scripts/`, `tests/julia/` → `legacy/julia/tests/`, `Project.toml` → `legacy/julia/Project.toml`, `Manifest.toml` → `legacy/julia/Manifest.toml`.
- [x] TASK-06-03: Update the known Python call sites: `src/python/reopt_pysam_vn/reopt/regime_runner.py:21` (`JULIA_RUNNER = REPO_ROOT / "scripts" / "julia" / "run_vietnam_scenario.jl"` → `REPO_ROOT / "legacy" / "julia" / "scripts" / "run_vietnam_scenario.jl"`) and any hit from TASK-06-01.
- [x] TASK-06-04: Update `tests/run_all_tests.ps1` and `tests/cross_language/cross_validate.py` for the new paths.
- [x] TASK-06-05: Update the Julia module's own `REPO_ROOT` computation — `legacy/julia/src/REoptVietnam.jl:48` currently does `abspath(joinpath(@__DIR__, "..", ".."))` which resolves to the repo root from `src/julia/`. From `legacy/julia/src/` it must become `abspath(joinpath(@__DIR__, "..", "..", ".."))`. **Getting this wrong makes `DEFAULT_DATA_DIR` point at a nonexistent directory and every Julia test fail with a file-not-found error.**
- [x] TASK-06-06: Create `legacy/julia/README.md` explaining the archive status, what Julia uniquely provides (the Decree 57/243 export-cap JuMP constraint, `add_decree57_export_cap_constraint!`, which has no Python equivalent — plain `REopt.run_reopt` does not enforce the cap), and the exact commands to run it.
- [x] TASK-06-07: Rewrite `README.md`'s "Tech Stack" section to lead with the real primary path. Replace the current three bullets with: NREL REopt web API (`developer.nlr.gov`) as the primary solve path via `reopt/preprocess.py` + `webapp/service.py`; PySAM 7.1.0 for developer finance; Python 3.10+; and Julia 1.10 + REopt.jl v0.56.4 **retained in `legacy/julia/` for offline solves and the Decree 57/243 export-cap constraint**. **Do not remove** the "Security note — API key rotation required" section (ASM-009).
- [x] TASK-06-08: Update `AGENTS.md` §1 Mission and §2 Environment to match, and `docs/architecture.md`'s preprocessing-module table with the new Julia path.
- [x] TASK-06-09: Add a `legacy/julia/` row to `docs/legacy-path-map.md` recording the old→new paths and the date.
- [x] TASK-06-10: Update `.gitignore` if it references the moved paths, and run `git status` afterward to confirm nothing was silently un-ignored or re-tracked.

**File Changes**
- `src/julia/REoptVietnam.jl` → `legacy/julia/src/REoptVietnam.jl` (git mv + modify line 48's `REPO_ROOT`).
- `scripts/julia/*` → `legacy/julia/scripts/*` (git mv).
- `tests/julia/*` → `legacy/julia/tests/*` (git mv).
- `Project.toml`, `Manifest.toml` → `legacy/julia/` (git mv).
- `src/python/reopt_pysam_vn/reopt/regime_runner.py` (modify): the `JULIA_RUNNER` path constant at line 21.
- `tests/run_all_tests.ps1` (modify): the Julia script paths, including the `-Script 'tests\cross_language\cross_validate.py'` invocation at line 235 if its Julia sibling moved.
- `tests/cross_language/cross_validate.py` (modify): the path to `export_processed_dict.jl`.
- `legacy/julia/README.md` (create).
- `README.md` (modify): Tech Stack section, Project Structure tree, and the Quick Start Julia commands. Preserve the API-key-rotation section verbatim.
- `AGENTS.md` (modify): §1 Mission, §2 Environment & Commands.
- `docs/architecture.md` (modify): the preprocessing-module table's Julia path.
- `docs/legacy-path-map.md` (modify): new row.

**Function Signatures**
None — no code interfaces change in this phase; only file locations and one path constant.

**Test Specs**
- `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q` → identical pass count to before the move. **Run the FULL suite, not a subset** — the repo's own `lessons.md` records that a subset previously missed integration-test breakage after exactly this kind of structural move.
- `PYTHONPATH= python -m pytest tests/python/test_repo_invariants.py -v` → all pass (the flat-script, tracked-artifacts, and root-binary invariants must survive the move).
- On a machine with Julia: `JULIA_PKG_PRECOMPILE_AUTO=0 julia --project=legacy/julia --compile=min legacy/julia/tests/test_unit.jl` → all Layer 2 tests pass. This is the check that catches a wrong `REPO_ROOT` in TASK-06-05.
- On a machine with Julia: `PYTHONPATH= python tests/cross_language/cross_validate.py` → exact match, max diff `0.00e+00`.
- `test -d src/julia` → exit code `1` (directory gone). `test -f legacy/julia/src/REoptVietnam.jl` → exit code `0`.
- `grep -rn "src/julia\|scripts/julia" README.md AGENTS.md docs/ --include=*.md | grep -v legacy-path-map` → zero hits.
- `grep -c "API key rotation required" README.md` → `1` (ASM-009 guard).

**Dependencies**
- PHASE-04 must be complete first — it edits `src/julia/REoptVietnam.jl`, and doing that before the move avoids resolving the same edit against a moved file.

**Exit Criteria**
- [x] `git log --follow --oneline legacy/julia/src/REoptVietnam.jl | head -3` shows pre-move history (confirms `git mv`, not copy-delete).
- [x] Full portable suite green with an unchanged pass count.
- [x] Julia Layer 2 tests pass from the new location on a Julia-equipped machine.
- [x] No `.md` file outside `docs/legacy-path-map.md` references `src/julia` or `scripts/julia`.
- [x] `git status` is clean after the move with nothing unexpectedly staged or un-ignored.

**Phase Risks**
- **RISK-06-01:** the `REPO_ROOT` depth change in `REoptVietnam.jl` is silent — a wrong path yields a file-not-found only when a Julia test actually runs, and Julia is not in CI. Mitigation: TASK-06-05 states the exact new expression, and the Julia Layer 2 run is a hard exit criterion, not optional.
- **RISK-06-02:** a path is built from segments (`REPO_ROOT / "scripts" / "julia" / ...`) and a naive `grep "scripts/julia"` misses it. Mitigation: TASK-06-01's bare-name grep is mandatory and must run **before** the move. This exact failure mode is recorded in the repo's `lessons.md` from the 2026-06-12 `archive/` deletion.
- **RISK-06-03:** `Project.toml` moving breaks `julia --project` invocations that assume the repo root. Mitigation: every documented Julia command becomes `julia --project=legacy/julia`; update all of them in `README.md`, `AGENTS.md`, `docs/testing.md`, and `tests/run_all_tests.ps1`.

## Gotchas

- **Fraction vs percent, the 100× trap.** `max_export_fraction` in `data/vietnam/*.json` is a fraction (`0.5`). `ContractParams.export_cap_pct` is a percentage (`50.0`). `kpp_pct` is a percentage (`2.7263`) while `kpp_factor` is a multiplier (`1.027263`). Every conversion between these is a place to put an explicit assertion.
- **`bool` is a subclass of `int` in Python.** In the PHASE-02 type validator and in any recursive numeric comparator, check `isinstance(v, bool)` **before** `isinstance(v, int)` or `True` will validate as an integer. The repo's `lessons.md` records this exact bug being hit before in a comparator.
- **All JSON reads use `encoding="utf-8-sig"`.** Windows editors write a BOM; `encoding="utf-8"` fails on those files with a cryptic `json.JSONDecodeError` at position 0. Match the existing convention in every new file reader.
- **The Julia `VNData` struct is positional.** Inserting a field anywhere but the specified position silently mis-assigns every field after it, with no error — the values just become wrong. Layer 3 cross-validation is the only detector, and it is not in CI, so it must be run manually.
- **`git mv`, never copy-then-delete.** History following (`git log --follow`) is an exit criterion in PHASE-06.
- **Grep bare directory names before any move or delete.** `grep "julia/"` never matches `REPO_ROOT / "scripts" / "julia"`. This is recorded in `lessons.md` as the cause of a prior incident.
- **Run the FULL test suite after any structural change**, never a subset and never `--collect-only`. Recorded in `lessons.md` after a subset run missed integration breakage.
- **`.gitignore` negations must be anchored.** A loose negation silently re-tracks unrelated files; run `git status` after any `.gitignore` edit.
- **Clear `PYTHONPATH` for pytest.** A stale global `PYTHONPATH` pointing at an unrelated venv produces `ModuleNotFoundError: pydantic_core._pydantic_core` that looks like a dependency bug and is not.
- **`artifacts/`, `reports/*.html`, `present/`, and `scenarios/generated/` are git-ignored by design** and mechanically enforced by `tests/python/test_repo_invariants.py`. Write generated output there; write tracked deliverables as `reports/*.md`.
- **Never edit a published `data/vietnam/*.json` file's numbers in place.** Create a new versioned file and flip one line in `manifest.json`. PHASE-04's edits are explicitly structural (envelope) and additive (new block) — no existing number moves, which is why an in-place edit plus a version bump is acceptable there.
- **PySAM lives only in the repo `.venv` on the primary dev machine.** System Python has no wheel and the code silently falls back to a synthetic solar profile — which produces plausible but wrong numbers rather than an error. Always use `.venv/Scripts/python.exe` for anything touching PySAM or PVWatts.

## Verification Strategy

- **TEST-001:** `ruff check src scripts tests` → `All checks passed!`, exit `0`. (PHASE-01)
- **TEST-002:** `python -m compileall -q src scripts tests` under Python 3.10 → exit `0`, no output. (PHASE-01)
- **TEST-003:** `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q --cov=reopt_pysam_vn --cov-report=term-missing` → at least `589 passed, 18 deselected`, coverage ≥ 85%. (All phases)
- **TEST-004:** `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` → `Success: no issues found`. (PHASE-02, PHASE-04)
- **TEST-005:** `PYTHONPATH= python -m pytest tests/python/analysis/test_validation.py tests/python/common/test_assumptions.py tests/python/integration/test_settlement_policy_drift.py -v` → all pass. (PHASE-02, PHASE-04)
- **TEST-006:** Commit-1 byte-identity gate — capture the suite output before and after the value-preserving refactor and `diff` them → empty. (PHASE-05, mandatory)
- **TEST-007:** `git diff --exit-code examples/` after PHASE-05 Commit 1 → exit `0`. (PHASE-05)
- **TEST-008:** `grep -rnE "EXCHANGE_RATE[A-Z_]* *= *2[0-9][,_]?[0-9]{3}" --include=*.py src scripts | grep -v __pycache__ | grep -v "Intentionally NOT"` → only `preprocess.py`'s documented last-resort fallback. (PHASE-05)
- **TEST-009:** On a Julia-equipped machine, `JULIA_PKG_PRECOMPILE_AUTO=0 julia --project=legacy/julia --compile=min legacy/julia/tests/test_unit.jl` → all Layer 2 tests pass. (PHASE-04, PHASE-06)
- **TEST-010:** On a Julia-equipped machine, `PYTHONPATH= python tests/cross_language/cross_validate.py` → exact match, max diff `0.00e+00`, for all exercised regimes. (PHASE-04, PHASE-06 — the only detector for the positional-struct hazard)
- **TEST-011:** `PYTHONPATH= python -m pytest tests/python/test_repo_invariants.py -v` → all pass after every structural change. (PHASE-06)
- **TEST-012:** `git log --follow --oneline legacy/julia/src/REoptVietnam.jl | head -3` → shows commits predating the move. (PHASE-06)
- **MANUAL-001:** Read the full `ruff check --fix` diff before committing PHASE-01, checking every removed import in `analysis/` and `integration/` for side-effecting registry registration.
- **MANUAL-002:** Read `reports/2026-07-26-samsung-parity-diagnosis.md` before executing PHASE-03 TASK-03-03. If more than the known `developer_irr_fraction` field diverges, take Branch B.
- **MANUAL-003:** Launch the web app (`PYTHONPATH=src/python python -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000`), open `http://127.0.0.1:8000/deals/new`, submit a deal, and confirm it still succeeds after PHASE-02's validator lands. A schema/form mismatch is a real bug in `forms.py`, not grounds to weaken the validator.
- **MANUAL-004:** Read `reports/2026-07-26-fx-unification-delta.md` and confirm every figure it cites is reproducible by re-running the named script.
- **OBS-001:** After PHASE-01, confirm both CI matrix jobs (3.10 and 3.12) appear and are green on the branch before merging. A single-job run means the matrix was not wired into `actions/setup-python`.

## Risks and Alternatives

- **RISK-001:** PHASE-05 changes numbers that have already been sent to external counterparties, creating a discrepancy between a delivered deck and what the repo now reproduces. Mitigation: the delta memo (`reports/2026-07-26-fx-unification-delta.md`) is the artifact that makes this explicit and auditable; the per-deal 25,450 sites are deliberately frozen (ASM-005) precisely because they are most likely to correspond to delivered Saigon18 work.
- **RISK-002:** The cumulative change surface across six phases is large enough that a regression is attributed to the wrong phase. Mitigation: every phase has independent exit criteria that must pass before the next begins; PHASE-05 in particular is split into two commits specifically so attribution is mechanical.
- **RISK-003:** PHASE-04's Julia struct edit and PHASE-06's Julia move both touch `REoptVietnam.jl`, and Julia is not in CI, so neither is automatically verified. Mitigation: TEST-009 and TEST-010 are hard exit criteria for both phases and require a Julia-equipped machine. If no such machine is available, **stop before PHASE-04 TASK-04-06** and execute PHASE-04 Python-only, deferring the Julia mirror — but then Layer 3 cross-validation will fail on the field-count mismatch, so record that as known-broken rather than shipping it silently.
- **RISK-004:** PHASE-03 Branch A regenerates a golden that launders a genuine regression into the baseline. Mitigation: MANUAL-002's read-before-regenerate gate, plus the single-commit isolation of the regenerated golden so `git diff HEAD~1` shows exactly what moved.
- **ALT-001:** Make `ContractParams`' policy fields **required** rather than resolver-defaulted, forcing every caller to be explicit. Rejected: 24 call sites across 14 files would break at once (CON-004), and the drift-guard test achieves the same protection without the churn.
- **ALT-002:** Add `jsonschema` as a runtime dependency for PHASE-02 instead of hand-rolling. Rejected: the schema file's own `description` promises no runtime dependency, the package is not currently installable in the working environment, and only three keywords (`required`, `type`, `enum`) are actually used by this schema.
- **ALT-003:** Delete the Julia half entirely rather than archiving it. Rejected: `add_decree57_export_cap_constraint!` is the only implementation of the Decree 57/243 annual export cap anywhere in the repo — plain `REopt.run_reopt` does not enforce it, and there is no Python equivalent.
- **ALT-004:** Do the FX unification as one commit with a delta memo. Rejected: with 22 sites across 17 files there is no way to prove which numeric movements were intended versus accidental. The two-commit split makes Commit 1 mechanically verifiable as a no-op.
- **ALT-005:** Raise `requires-python` to `>=3.12` instead of fixing the f-string. Rejected per ASM-001: `[tool.mypy] python_version = "3.10"` and `[project] requires-python = ">=3.10"` both declare 3.10, so the script is the outlier, and dropping 3.10 support to accommodate one stray comment is the wrong trade.

## Suggested Next Step

Execute PHASE-01. It is self-contained, has no dependencies, fixes a genuine syntax error that is currently invisible, and establishes the lint and version gates that make every subsequent phase safer to verify. Its exit criteria (`ruff check` exits 0, `compileall` passes on 3.10, both CI matrix jobs green, test counts unchanged) are all verifiable in under ten minutes before PHASE-02 begins.
