# Architecture & Tech Stack

## Tech Stack
- **Core:** REopt.jl → JuMP → HiGHS (default). Optional: Cbc/SCIP/Xpress/CPLEX.
- **Pipeline:** `Scenario(dict)` → `REoptInputs(s)` → `run_reopt(m, inputs)` → results dict.
- **HiGHS limitation:** No indicator constraints — `model_degradation=true` and `FlexibleHVAC` require Xpress/CPLEX.
- **Library internals** (workflow code, struct anatomy, decision variables, tech params, results keys): see `docs/reopt_internals.md`.

## Preprocessing Modules
Dual Julia/Python modules that apply Vietnam defaults to a REopt input dict **before** `Scenario()` construction.

| Module | Language | Key Function |
|---|---|---|
| `legacy/julia/src/REoptVietnam.jl` (archived — see `legacy/julia/README.md`) | Julia | `apply_vietnam_defaults!(dict, vn; customer_type, voltage_level, region)` |
| `src/python/reopt_pysam_vn/reopt/preprocess.py` | Python | `apply_vietnam_defaults(dict, vn, customer_type, voltage_level, region)` |

Both modules share the same `data/vietnam/` data files and are intended to produce identical output. This is verified by Layer 3 cross-validation (`tests/cross_language/cross_validate.py`, max diff = 0.00e+00 when last run), but that check is **not automated** — CI only collects `tests/python` and excludes `requires_julia`/`golden_machine`-marked tests, so Layer 3 must be run manually (`tests/run_all_tests.ps1` or the script directly) on a machine with Julia installed to confirm equivalence still holds. See `docs/testing.md` § "What CI Actually Runs".

**Exported functions (both languages):**
- `load_vietnam_data()` - Load all data files via manifest
- `apply_vietnam_defaults!()` / `apply_vietnam_defaults()` - Full pipeline (tariff + financials + emissions + tech costs + export rules + zero incentives)
- `build_vietnam_tariff()` - Build 8760 TOU energy rate series
- `zero_us_incentives!()` / `zero_us_incentives()` - Zero all US-specific incentive fields
- `apply_vietnam_financials!()` / `apply_vietnam_financials()` - Set CIT, discount rates, analysis years
- `apply_vietnam_emissions!()` / `apply_vietnam_emissions()` - Set constant 8760 emissions series
- `apply_vietnam_tech_costs!()` / `apply_vietnam_tech_costs()` - Set PV/Wind/Battery/Generator costs by region
- `apply_decree57_export!()` / `apply_decree57_export()` - Set export rules per Decree 57
- `convert_vnd_to_usd()` / `convert_usd_to_vnd()` - Currency conversion

**Non-destructive:** User values already present in the dict are never overwritten.

## Coding Standards
- Prefer REopt's `handle_errors` patterns and structured warnings/errors via the custom logger.
