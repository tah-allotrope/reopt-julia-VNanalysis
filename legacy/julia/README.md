# Julia Layer (Archived)

This directory holds the Julia half of the toolkit's REopt preprocessing
layer. It is **archived, not deleted or deprecated for removal** — see
"Why it's kept" below.

## Archive status

Julia is **not** on the primary solve path and is **not** run in CI. The
primary, supported path is the NREL REopt web API
(`developer.nlr.gov`) via `src/python/reopt_pysam_vn/reopt/preprocess.py`
+ `webapp/service.py`. This directory is retained for:

1. **Offline solves** where the hosted API is unavailable or a local solve
   is preferred (`REopt.jl` + `HiGHS`/`Xpress` locally, no network round trip).
2. **The Decree 57/243 rooftop-solar export-cap constraint**
   (`add_decree57_export_cap_constraint!` in `src/REoptVietnam.jl`) — a JuMP
   constraint enforced at solve time. Plain `REopt.run_reopt` (the Python
   path's underlying solver call, via the web API) does **not** enforce this
   cap; there is currently no Python-side equivalent.

## Contents

```
legacy/julia/
  Project.toml, Manifest.toml   Julia environment (REopt.jl v0.56.4, Julia 1.10.10)
  src/REoptVietnam.jl            Preprocessing module (mirror of reopt_pysam_vn.reopt.preprocess)
  scripts/                       CLI solve scripts (run_vietnam_scenario.jl, bounded-opt variants, sysimage builder)
  tests/                         Layer 1/2/4 Julia tests + the Layer 3 cross-validation Julia side
```

## Running it

All commands below assume the repo root as the working directory.

```powershell
# One-time: instantiate the Julia environment
julia --project=legacy/julia -e "using Pkg; Pkg.instantiate()"

# Layer 2: unit tests
$env:JULIA_PKG_PRECOMPILE_AUTO = "0"
julia --project=legacy/julia --compile=min legacy/julia/tests/test_unit.jl

# Layer 1: data validation
julia --project=legacy/julia --compile=min legacy/julia/tests/test_data_validation.jl

# Layer 4: integration tests (needs a solver + NREL API key for some paths)
julia --project=legacy/julia --compile=min legacy/julia/tests/test_integration.jl --smoke-only

# Solve a scenario directly
julia --project=legacy/julia --compile=min legacy/julia/scripts/run_vietnam_scenario.jl `
    --scenario scenarios/templates/vn_commercial_rooftop_pv.json

# Or via the wrapper script (handles sysimage / API fallback):
.\scripts\run_solve.ps1 -Scenario scenarios/templates/vn_commercial_rooftop_pv.json
```

Layer 3 cross-validation (Julia vs Python, both preprocessing paths on the
same input) runs from the Python side and shells out to Julia:

```powershell
PYTHONPATH= python tests/cross_language/cross_validate.py
```

None of the above run in CI — see `docs/testing.md` § "What CI Actually
Runs". They must be run manually on a machine with Julia 1.10 installed.

## History

This directory was moved here on 2026-07-26 via `git mv` (history preserved
with `git log --follow`) from `src/julia/`, `scripts/julia/`, `tests/julia/`,
and the repo-root `Project.toml`/`Manifest.toml`. See
`docs/legacy-path-map.md` for the old→new path mapping and
`plans/2026-07-26-post-backlog-architecture-plan.md` PHASE-06 for the
rationale.
