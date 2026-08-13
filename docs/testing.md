# Testing Strategy

## 4 Layers

| Layer | What | Speed | Files |
|---|---|---|---|
| **1: Data Validation** | Schema compliance, value bounds for all `data/vietnam/` files | <2s | `legacy/julia/tests/test_data_validation.jl`, `tests/python/reopt/test_data_validation.py` |
| **2: Unit Tests** | Every exported function, edge cases, error handling, non-destructive merge | <3s | `legacy/julia/tests/test_unit.jl`, `tests/python/reopt/test_unit.py` |
| **3: Cross-Validation** | Julia vs Python produce identical dicts (tolerance 1e-10) | <5s | `tests/cross_language/cross_validate.py`, `legacy/julia/tests/export_processed_dict.jl` |
| **4: Integration** | Scenario() construction, solver runs, regression baselines, incentive verification, API domain connectivity | ~30-60s/scenario | `legacy/julia/tests/test_integration.jl`, `tests/python/reopt/test_integration.py` |

**Baselines:** Stored in `tests/baselines/`. Auto-generated on first run; subsequent runs compare within 5% tolerance. Delete baseline file to regenerate.

## Test Runner

```powershell
# Run all layers (Layers 1-3 fast, Layer 4 slow)
.\\tests\\run_all_tests.ps1

# Skip solver-dependent tests
.\\tests\\run_all_tests.ps1 -SkipLayer4

# Layer 4 smoke tests only (Scenario construction, no solver)
.\\tests\\run_all_tests.ps1 -SmokeOnly

# Run a single layer
.\\tests\\run_all_tests.ps1 -Layer 2
```

**Julia tests directly (archived under `legacy/julia/`, not CI-collected):**
```powershell
$env:JULIA_PKG_PRECOMPILE_AUTO="0"
julia --project=legacy/julia --compile=min legacy/julia/tests/test_unit.jl
julia --project=legacy/julia --compile=min legacy/julia/tests/test_integration.jl --smoke-only
```

**Python tests directly:**
```powershell
python -m pytest tests/python/reopt/test_unit.py -v
python -m pytest tests/python/reopt/test_integration.py -v -k smoke

# Run only the API domain connectivity check (fast, ~3s)
python -m pytest tests/python/reopt/test_integration.py::TestAPIIntegration::test_nlr_domain_connectivity -v
```

## What CI Actually Runs

CI (`.github/workflows/ci.yml`) runs exactly one test command, against a pinned
dependency set (`pip install -e ".[webapp,dev]" -c constraints-ci.txt`) and also
on a weekly `cron` schedule:

```bash
PYTHONPATH= python -m pytest tests/python \
  -m "not network and not requires_artifacts and not golden_machine and not requires_julia and not requires_nrel_key and not requires_pysam_resource" \
  -rs -q --cov=reopt_pysam_vn --cov-report=term-missing
```

with `REOPT_PYSAM_VN_MAX_SKIPS: "0"` set — a skip budget enforced by
`tests/conftest.py` that fails the build if any test in the portable suite
skips (so the number cannot drift upward unnoticed). `-rs` prints every skip
reason in the log.

That means:

- **`legacy/julia/tests/` (Layer 1/2/4 Julia) and `tests/cross_language/` (Layer 3
  cross-validation) are never collected by CI.** They live outside
  `tests/python`, which is the only path CI's `pytest` invocation names. The
  "Julia vs Python produce identical dicts (tolerance 1e-10)" claim in the
  Layer 3 row above, and the "identical output, max diff = 0.00e+00" claim in
  `docs/architecture.md`, are **manual-verification claims** — true only when
  someone runs `tests/run_all_tests.ps1` or `tests/cross_language/cross_validate.py`
  by hand on a machine with Julia installed. No automation checks this today.
- **`tests/python/analysis/test_samsung_ttc_parity.py` is CI-excluded** via
  its module-level `golden_machine` marker, and its two strongest assertions
  additionally carry `xfail`. See `reports/2026-07-26-samsung-parity-diagnosis.md`
  for why, and the "Samsung-TTC" bullets in `README.md` / `docs/onsite_vs_offsite.md`
  for the honest current status.
- **Environment-dependent skips are declarative markers, not runtime guards.**
  Tests that need a live NREL key or network are `@pytest.mark.requires_nrel_key`;
  tests that need a git-untracked PVWatts solar-resource cache are
  `@pytest.mark.requires_pysam_resource`. Both are excluded by the CI filter and
  auditable in `pyproject.toml`'s `markers` list. `--strict-markers` (in
  `addopts`) makes a typo'd marker an error.
- `analysis/__main__.py` is measured by coverage via the in-process
  `main(argv)` call in `tests/python/analysis/test_cli.py`
  (`test_cli_onsite_subcommand_in_process`), alongside the subprocess smoke tests.

## Known L4 Status (as of 2026-03)

| Test | Status | Notes |
|---|---|---|
| `TestTemplateSmokeTests` (9 tests) | PASS | No API key required |
| `TestAPIIntegration::test_nlr_domain_connectivity` | PASS | Verifies `developer.nlr.gov` reachable; ~3s |
| `TestAPIIntegration::test_commercial_rooftop_api_solve` | FAIL (pre-existing) | HTTP 400 from `/job/` — payload issue, unrelated to domain migration |
| `TestAPIIntegration::test_api_vs_baseline_regression` | FAIL (pre-existing) | Same HTTP 400 root cause |
| `TestJuliaVsAPICrossCheck` | SKIP | Requires local Julia + API key together |
