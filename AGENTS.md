# REopt Vietnam Project Context & Guidelines

## 1. Project Overview
> **Mission:** Techno-economic optimization for cost-optimal energy generation (Solar, Wind, Battery) for buildings and microgrids in Vietnam using NREL REopt, with PySAM-based developer finance. The primary solve path is the NREL REopt web API via Python; a Julia local-solve layer is retained in `legacy/julia/` for offline solves and the Decree 57/243 export-cap constraint.

## 2. Environment & Commands
- **Environment (primary, Python):** Python 3.10+, `nrel-pysam` 7.1.0, editable install (`python -m pip install -e ".[webapp]"`).
- **Environment (Julia, `legacy/julia/`, offline/export-cap-constraint use only):** Julia 1.10+ with REopt.jl v0.56.4 (`julia --project=legacy/julia` for interactive use).
- **Run Command (Julia):** `$env:JULIA_PKG_PRECOMPILE_AUTO="0"; julia --project=legacy/julia --compile=min legacy/julia/<script>.jl` (Bypasses precompilation hangs for scripts).
- **Test Command:** `.\\tests\\run_all_tests.ps1` (Runs all validation layers; CI itself only runs `pytest tests/python` — see `docs/testing.md`).

## 3. Documentation Directory
Detailed instructions have been organized into the `docs/` folder for progressive disclosure. When working on specific areas, read the relevant file:
- **[Architecture & Tech Stack](docs/architecture.md):** JuMP/HiGHS pipeline, preprocessing modules (`legacy/julia/src/REoptVietnam.jl` / `src/python/reopt_pysam_vn/reopt/preprocess.py`), and coding standards.
- **[Data Layer & API Reference](docs/data_and_api.md):** API keys, Vietnam JSON data schema, and DeepWiki URLs.
- **[Known Pitfalls & Workarounds](docs/pitfalls.md):** Common REopt errors, default overrides, and Decree 57 constraint limitations.
- **[Scenario Templates](docs/scenarios.md):** Pre-configured JSON templates and usage patterns.
- **[Testing Strategy](docs/testing.md):** The 4-layer validation strategy and direct test runner commands.
- **[REopt.jl Library Internals](docs/reopt_internals.md):** Execution workflow, struct anatomy, decision variables, results dict keys.

## 4. Current Status
- **Julia:** 1.10.10, REopt v0.56.4 / JuMP / HiGHS. Version bounds in `Project.toml [compat]`.
- **API keys:** Configured via `NREL_API.env` (git-ignored). See `NREL_API.env.example`.
- **API domain:** Migrated from `developer.nrel.gov` → `developer.nlr.gov` (Mar 2026). Old domain expires May 29 2026.
- **REopt Vietnam Tool:** All 9 implementation steps complete. Full preprocessing pipeline, 4 scenario templates, 4-layer test suite, test runner, documentation.

### Implementation Steps (all complete)
1. Data layer — 5 JSON files + manifest (`data/vietnam/`)
2. Julia module — `legacy/julia/src/REoptVietnam.jl` (archived 2026-07-26 from the repo root; old→new paths in `docs/legacy-path-map.md`)
3. Julia Layer 1 + Layer 2 tests
4. Python module — `src/python/reopt_pysam_vn/reopt/preprocess.py`
5. Python Layer 1 + Layer 2 tests + Layer 3 cross-validation
6. 4 scenario templates in `scenarios/templates/`
7. Layer 4 integration/regression tests + baselines
8. Test runner `tests/run_all_tests.ps1`
9. Documentation (`AGENTS.md` → `docs/`, `README.md`)

### Test Suite Status (last run: Mar 2026)
| Layer | Result |
|---|---|
| L1 Julia + Python data validation | PASS |
| L2 Julia + Python unit tests | PASS |
| L3 Julia vs Python cross-validation | PASS (exact match, max diff 0.00e+00) |
| L4 Python: Template smoke tests (9 tests) | PASS |
| L4 Python: `test_nlr_domain_connectivity` | PASS — new domain confirmed healthy |
| L4 Python: `test_commercial_rooftop_api_solve` | FAIL (pre-existing HTTP 400 — payload issue, not domain) |
| L4 Python: `test_api_vs_baseline_regression` | FAIL (same root cause) |
| L4 Julia: Integration tests | NOT RUN — cold-start takes 3-8 min; use `-JuliaTimeoutSeconds 1800` |

## 5. Key Learnings & Notes
- REopt.jl outage modeling is a **soft constraint** by default. Use `Site.min_resil_time_steps` for hard constraint.
- `ElectricStorage.installed_cost_constant` defaults to **$222,115** — Vietnam defaults override to $0.
- US federal incentives (30% ITC, 100% MACRS bonus) apply by default even for non-US sites — zeroed by preprocessing.
- Vietnam data files use `_meta` envelope for versioning; code reads only `"data"` block. Update policy data by creating new versioned file + changing `manifest.json`.
- Pass `voltage_level` explicitly to preprocessing when reliable site voltage info is available.
- **Generated outputs are local-only (git-ignored):** `artifacts/`, `reports/*.html`, `present/`, `reports/decks/`, `scenarios/generated/`. Scripts still write there; git does not track them. Tracked references live in `examples/` (golden runs), `reports/*.md`, and `tests/baselines/`. (2026-06-12 de-bloat.)
- **`activeContext.md` stays slim** (current state only, target < ~150 lines). Rotate finished-work history into `docs/worklog/` rather than appending indefinitely. (2026-06-12.)
- **Scripts are canonical-only:** call them at `scripts/python/{reopt,pysam,integration}/<name>.py`. The flat `scripts/python/*.py` shim layer was removed 2026-06-12 — see the "Script Paths (canonical)" table in `README.md` for redirects.
- **Analysis front door (2026-06-14):** new onsite/offsite work goes through `reopt_pysam_vn.analysis` — `run_onsite` / `run_offsite_dppa` + the `python -m reopt_pysam_vn.analysis` CLI. The `integration/dppa_*` / `ninhsim_*` case modules are the registered orchestration engines behind it and are deprecated as direct entry points. See `docs/onsite_vs_offsite.md`.
- **Public API boundary (2026-07-15, strategic-lens PHASE-02):** `reopt_pysam_vn.analysis` and `reopt_pysam_vn.webapp` are the type-checked, supported surfaces (`mypy` gate, `py.typed` marker). `integration`, `reopt`, and `pysam` are internal engines and may change shape without a deprecation cycle — new external-facing code should depend on `analysis`, not on those internals.

## 6. Real Project Data Notes
A dedicated branch `real-project-data` was created to test the `REoptVietnam.jl` logic against actual project parameters from an Excel-based feasibility study.

**Project analyzed:** 3.2 MWp Solar, 2.2 MWh / 1 MW BESS, 22kV 2-component EVN tariff, 20-year lifetime, 20% CIT, 15% PPA discount.

**Identified gaps:**
1. **Missing 8760 hourly data:** Static Excel data provides annual yields, but REopt requires 8760 hourly load profile (kW) and generation profile (or coordinates for weather data).
2. **Optimizer vs. controller:** Real project uses fixed BESS charge/discharge windows; REopt **optimizes** these based on TOU tariff.
3. **PPA discounting:** "15% discount to EVN tariff" must be pre-calculated by modifying the 8760 tariff series before optimization.

**Next steps (real-project-data branch):**
1. Synthesize load profile via REopt `simulated_load` API.
2. Run comparison scenario: REopt vs. Excel feasibility study results.
3. Custom JuMP constraint for 20% generation export cap (Decree 57).
