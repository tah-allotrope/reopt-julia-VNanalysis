# Final Report: Post-CI Hygiene, Finance Audit, Coverage, and Plans Sweep

**Date:** 2026-07-25  
**Status:** ✅ Complete  
**CI Status:** Green (589 passed, 3 xfailed, 18 deselected, 85% coverage)

## Executive Summary

This report documents the completion of four unimplemented phases from two prior planning documents:
1. **PHASE-03 (07-24 plan):** Report-only test coverage in CI
2. **PHASE-04 (07-24 plan):** Plans directory hygiene sweep
3. **PHASE-04 (07-22 plan):** Two-part tariff Ca re-pricing fix

All phases have been successfully implemented, tested, and verified. The repository now has:
- 85% test coverage reported in every CI run (non-blocking)
- 9 plans in `plans/active/` (down from 22), with 13 shipped plans archived
- Corrected two-part tariff economics that properly account for trial energy rates

## Phase Details

### PHASE-03: Report-Only Test Coverage in CI

**Objective:** Add pytest-cov to CI to report what fraction of `src/python/reopt_pysam_vn/` the test suite exercises, without gating on any threshold.

**Changes:**
- Added `[tool.coverage.run]` section to `pyproject.toml` (source = reopt_pysam_vn, omit webapp/static and __pycache__)
- Added `pytest-cov` to CI install dependencies in `.github/workflows/ci.yml`
- Added `--cov=reopt_pysam_vn --cov-report=term-missing` flags to pytest invocation in CI

**Verification:**
- Local run: 589 passed, 18 deselected, 3 xfailed, 85% coverage
- Coverage report shows per-file breakdown with missing lines identified
- No `--cov-fail-under` flag (report-only, non-blocking)

**Impact:** Future refactoring work can now prioritize by coverage gaps. Current 85% coverage is a strong baseline.

---

### PHASE-04 (07-24): Plans Directory Hygiene Sweep

**Objective:** Archive 13 confirmed-shipped plans from `plans/active/` to `plans/archive/` to prevent planning directory drift.

**Changes:**
Moved 13 plans with unambiguous shipped evidence (matching `reports/*final*` files, 100%-checked task lists, or explicit completion statements):
1. 2026-05-07-decision-963-tou-migration-plan.md
2. 2026-05-22-gap05-regime-toggle-plan.md
3. 2026-05-22-gap03-developer-project-catalog-plan.md
4. 2026-06-04-samsung-ttc-dppa-economics-plan.md
5. 2026-06-12-sprint-1-mechanical-debloat-plan.md
6. 2026-06-12-sprint-2-shim-removal-binary-relocation-plan.md
7. 2026-06-12-sprint-3-onsite-offsite-pipeline-plan.md
8. 2026-06-20-factory-a-emivest-rerun-plan.md
9. 2026-06-26-dppa-july-deck-verification-plan.md
10. dppa_case_1_plan.md
11. dppa_case_2_plan.md
12. dppa_case_3_plan.md
13. ninhsim_60pct_solar_storage_dppa_plan.md

**Verification:**
- `plans/active/` now contains 9 files (down from 22)
- `plans/archive/` now contains 16 files (13 moved + 3 pre-existing)
- All moves performed with `git mv` to preserve history
- 9 remaining plans in `plans/active/` have no unambiguous shipped evidence

**Impact:** Planning directory now accurately reflects current work state. Shipped plans are archived but still reachable by filename.

---

### PHASE-04 (07-22): Two-Part Tariff Ca Re-Pricing Fix

**Objective:** Fix the sign error in two-part tariff economics by computing NET impact (trial energy rates + demand charge) instead of demand-charge-only stacked on baseline rates.

**Problem:**
The script previously added the demand charge (Cp × monthly peak) on top of baseline single-component TOU energy rates, ignoring the lower trial energy rates (Ca, ~30-38% below baseline). This caused a sign error for high-load-factor profiles:
- **Before fix:** Saigon18 (+69.5% LF) showed +73B VND/yr extra cost
- **After fix:** Saigon18 shows -7.4B VND/yr net savings (correct)

**Changes:**
1. **New library module:** `src/python/reopt_pysam_vn/reopt/two_part_tariff.py`
   - `build_trial_energy_rate_series()` - builds 8760-element trial Ca rate series from tariff data
   - `reprice_energy_series()` - computes energy cost delta between baseline and trial rates
   - `compute_two_part_impact()` - computes net impact (energy delta + demand charge)
   - All functions use 8760-element hourly series and import TOU-window logic from `preprocess.py`

2. **New test suite:** `tests/python/reopt/test_two_part_tariff.py` (5 tests)
   - Flat profile with exact arithmetic verification
   - Length-mismatch guard
   - Real tariff data structure validation
   - High-load-factor sign check (net savings)
   - Low-load-factor sign check (net cost)

3. **Updated script:** `scripts/python/reopt/two_part_tariff_sensitivity.py`
   - Now uses library module for core arithmetic
   - Added `--voltage-level` argument (4 choices, default: medium_voltage_22kv_to_110kv)
   - Loads tariff data and builds both baseline and trial rate series
   - Computes and reports net impact (energy_delta + demand_charge)
   - Output JSON now includes `energy_delta_vnd`, `annual_demand_charge_vnd`, `net_impact_vnd`, `net_impact_usd`
   - Updated docstring to describe corrected method

4. **Documentation updates:**
   - `activeContext.md`: "Known model gaps" section updated to mark two-part tariff as FIXED
   - `docs/pitfalls.md`: New entry documenting the sign-flip defect and fix
   - `data/vietnam/vn_tariff_2025.json`: Updated `demand_charge.notes` to state script now correctly applies trial Ca rates

**Verification:**
- All 5 new tests pass
- Script runs successfully on Saigon18 artifacts:
  - Energy re-pricing delta: -77.5B VND/yr (trial rates cheaper)
  - Annual demand charge: +70.1B VND/yr (new charge)
  - Net impact: -7.4B VND/yr (net savings, correct sign)
- Full test suite: 589 passed, 3 xfailed, 0 failed

**Impact:** High-load-factor customers (like Saigon18) now correctly show net savings under the two-part trial tariff, matching domain expectations and the XanhTerra case study. The fix is unit-tested with synthetic toy profiles, making it independent of artifacts and suitable for CI.

---

## Test Results

**Full suite (CI filter):**
```
589 passed, 18 deselected, 3 xfailed, 1 warning in 133.69s
```

**Coverage:**
```
TOTAL: 4599 stmts, 707 missed, 85% coverage
```

**Key coverage highlights:**
- `reopt/preprocess.py`: 88% (364 stmts)
- `reopt/two_part_tariff.py`: 100% (new module)
- `pysam/single_owner.py`: 87% (includes clean-slate flag from prior phase)
- `webapp/*`: 80-94% across modules

## Files Changed

**New files:**
- `src/python/reopt_pysam_vn/reopt/two_part_tariff.py` (120 lines)
- `tests/python/reopt/test_two_part_tariff.py` (80 lines)

**Modified files:**
- `pyproject.toml` (added [tool.coverage.run] section)
- `.github/workflows/ci.yml` (added pytest-cov to install and pytest flags)
- `scripts/python/reopt/two_part_tariff_sensitivity.py` (rewrote to use library module, added --voltage-level)
- `activeContext.md` (marked two-part tariff as FIXED)
- `docs/pitfalls.md` (added two-part tariff entry)
- `data/vietnam/vn_tariff_2025.json` (updated notes field)

**Moved files (13 plans):**
- 13 files from `plans/active/` to `plans/archive/` (see list above)

## Risks and Mitigations

**Risk 1:** Coverage reporting adds ~10s to CI runtime  
**Mitigation:** Non-blocking, report-only. Value of visibility outweighs cost.

**Risk 2:** Archiving plans might hide unfinished work  
**Mitigation:** Only archived plans with unambiguous shipped evidence. 9 plans remain in `plans/active/` for work without clear completion markers.

**Risk 3:** Two-part tariff fix changes script output format  
**Mitigation:** Output JSON is backward-compatible (added new fields, did not remove existing ones). Script is not imported by other code paths.

## Next Steps

**No immediate next steps required.** All three phases are complete and verified.

**Future work (out of scope for this session):**
- Flip `zero_reference_plant_defaults` to `True` by default (requires human decision per audit report)
- Rotate the leaked NREL API key (requires human account owner)
- Configure ruff in CI and pay down the lint violation backlog
- Implement offline/frozen-resource solve mode
- Archive-vs-maintain decision for Julia stack

## Conclusion

All three unimplemented phases have been successfully completed. The repository now has:
- ✅ Report-only test coverage in CI (85%)
- ✅ Clean plans directory (9 active, 16 archived)
- ✅ Corrected two-part tariff economics (sign error fixed)
- ✅ Green CI (589 passed, 3 xfailed, 0 failed)

The implementation follows TDD principles (tests written before implementation for the two-part tariff fix), maintains backward compatibility, and includes comprehensive documentation updates.
