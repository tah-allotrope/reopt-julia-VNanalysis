# Known Pitfalls & Workarounds

### Outage: Soft vs Hard Constraint
Default outage modeling uses a **soft penalty** (`value_of_lost_load_per_kwh = $1.00/kWh`). **Fix:** Add `"min_resil_time_steps": <hours>` to `Site` for hard constraint.

### Non-US Locations (Vietnam)
AVERT, Cambium, EASIUR lookups will warn. **Fix:** Set `ElectricUtility.emissions_factor_series_lb_CO2_per_kwh` manually.

### ElectricLoad.year Required with loads_kw
When using `loads_kw` directly, `"year"` field is **required** (e.g., `"year": 2017`).

### US Incentive Defaults (zero for Vietnam)
- `federal_itc_fraction` (0.30), `macrs_option_years` (5), `macrs_bonus_fraction` (1.0) apply by default.
- `ElectricStorage.installed_cost_constant`: $222,115 fixed cost.
- **Incentive order:** Rebates → ITC → IBI → MACRS → Bonus depreciation → Tax savings.

### Off-Grid Mode
`Settings.off_grid_flag = true`: only PV/Wind/Generator/ElectricStorage allowed; Generator+Storage required; grid export/charge forced off; operating reserves enforced.

### Decree 57 Export Cap (`max_export_fraction`) — Enforcement
`apply_decree57_export!` / `apply_decree57_export` store `max_export_fraction` in scenario `_meta`, but REopt still has no native "max % of generation exportable" input. Enforcement now happens only when solving through the Vietnam-specific Julia wrapper `run_vietnam_reopt(...)` (used by `scripts/julia/run_vietnam_scenario.jl`), which adds a custom JuMP constraint: `annual PV export <= max_export_fraction * annual PV production`. Plain `REopt.run_reopt(...)` still does **NOT** enforce the cap automatically.

### L4 Julia Tests — Cold-Start Timeout
On first run (no precompiled sysimage), loading REopt.jl + ArchGDAL takes **3-8 minutes** even with `--compile=min`. The test runner's `Invoke-Julia` function now accepts `-JuliaTimeoutSeconds` to cap this. Recommended values:

| Scope | Flag | Suggested limit |
|---|---|---|
| L1 / L2 / L3 | (any) | 600s (10 min) |
| L4 smoke-only | `-SmokeOnly` | 1200s (20 min) |
| L4 full solve | (none) | 3600s (60 min) |

Run with timeout: `.\tests\run_all_tests.ps1 -SmokeOnly -JuliaTimeoutSeconds 1200`

Subsequent runs reuse the Julia depot cache and are much faster (~30-60s for smoke, ~5-10 min for solver).


`TestAPIIntegration::test_commercial_rooftop_api_solve` and `test_api_vs_baseline_regression` both fail with `HTTP 400 Bad Request` when submitting the full optimization payload to `/job/`. This is a **pre-existing payload issue**, not caused by the `nrel.gov → nlr.gov` domain migration (connectivity is confirmed working via `test_nlr_domain_connectivity`). Investigation pending — run `python -m pytest tests/python/reopt/test_integration.py::TestAPIIntegration::test_nlr_domain_connectivity -v` to confirm the domain itself is healthy.

### Two-Part Tariff Energy Rates (Decree 146/2025) — FIXED 2026-07-25
The two-part tariff script (`scripts/python/reopt/two_part_tariff_sensitivity.py`) previously only added the demand charge on top of baseline single-component TOU energy rates, ignoring the lower trial energy rates (Ca). This caused a sign error for high-load-factor profiles: the script reported +73B VND/yr extra cost for Saigon18 when the correct answer is -53B VND/yr savings.

**Fix:** The script now uses the library module `reopt_pysam_vn.reopt.two_part_tariff` to compute the NET impact: energy re-pricing delta (trial rates minus baseline rates, always negative) plus the annual demand charge (always positive). For high-load-factor customers, energy savings exceed the demand charge, resulting in net savings. The script accepts a `--voltage-level` argument to select the appropriate capacity charge rate from the tariff data.

**Key insight:** Under the two-part trial tariff, energy rates drop ~30-38% (see `vn_tariff_2025.json` → `demand_charge.two_part_tariff_trial.energy_charge_vnd_per_kwh`), but a new demand charge (Cp × monthly peak) is added. The net impact depends on load factor: high-LF customers save money, low-LF customers pay more.
