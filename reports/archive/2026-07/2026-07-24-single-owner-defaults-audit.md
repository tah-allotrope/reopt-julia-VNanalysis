# Single Owner Reference-Plant Defaults Audit

**Date:** 2026-07-24 (executed 2026-07-25)
**Scope:** `plans/2026-07-24-post-ci-hygiene-finance-audit-plan.md` PHASE-02
**Status:** Audit only — no golden file changed, no default flipped.

## Summary

`src/python/reopt_pysam_vn/pysam/single_owner.py::_configure_financial_model`
never touched twelve SAM `Singleowner.FinancialParameters` fields that carry
non-zero, ~100 MW-reference-plant cost defaults. This session added an
opt-in `zero_reference_plant_defaults` flag (default `False`, preserving
legacy behavior exactly) and `apply_clean_slate_financials()` to zero them
when a caller explicitly requests it. **No existing caller passes the new
flag** — every tracked and published result produced by this repository to
date, including the Samsung/TTC golden fixture, was generated with these
twelve fields at their unaudited SAM defaults. This report enumerates every
caller of the Single Owner finance path, quantifies the effect of the
un-zeroed defaults on two representative cases, and asks the people who own
the Samsung/TTC and CEBA client relationships to decide whether any
already-delivered number needs a second look.

## Verified SAM defaults (2026-07-24/25, `nrel-pysam==7.1.0`)

| Field | Default value | Zeroed by clean-slate flag |
|---|---|---|
| `insurance_rate` | `0.5` (percent) | Yes |
| `construction_financing_cost` | `2,866,500.0` (USD, flat) | Yes |
| `cost_debt_fee` | `2.75` (percent of debt principal) | Yes |
| `cost_debt_closing` | `0.0` (already zero) | Yes (no-op) |
| `months_working_reserve` | `6.0` (months) | Yes |
| `dscr_reserve_months` | `6.0` (months) | Yes |
| `equip1_reserve_cost` | `0.0` (already zero) | Yes (no-op) |
| `equip2_reserve_cost` | `0.0` (already zero) | Yes (no-op) |
| `equip3_reserve_cost` | `0.0` (already zero) | Yes (no-op) |
| `prop_tax_cost_assessed_percent` | `100.0` (percent) | Yes |
| `reserves_interest` | `1.75` (percent) | Yes |
| `salvage_percentage` | `0.0` (already zero) | Yes (no-op) |

## Caller table

Produced by `git grep -l "run_single_owner_model\|_configure_financial_model\|SingleOwnerInputs" -- src/ scripts/ tests/` on 2026-07-25.

| File | Calls `run_single_owner_model` | Feeds a published/tracked deliverable | Verdict |
|---|---|---|---|
| `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py:771` | **Yes** — inside the strike-sweep function, as the default developer-side runner | **Yes** — this is the Samsung/TTC flagship case, feeding `examples/samsung-ttc_combined-decision.example.json` (the bit-exact golden), `reports/2026-06-04-final-samsung-ttc-dppa.html`, and `present/Allotrope DPPA insights.pptx` | **Confirmed on unaudited-defaults path.** No caller passes the new flag; the golden was generated before the flag existed. |
| `src/python/reopt_pysam_vn/integration/dppa_case_2.py:972-974` | **Yes** — default runner in a sweep function | Feeds Case 2 phase reports (`reports/2026-04-14-dppa-case-2-*.html`, `reports/2026-04-16-dppa-case-2-final.html`) | Confirmed on unaudited-defaults path. |
| `src/python/reopt_pysam_vn/integration/strike_search.py:51,152` | **Yes** — `run_single_owner_model` is the default value for a `runner` parameter used by both `dppa_case_2.py` and `dppa_samsung_ttc.py` | Shared utility; see the two callers above | Confirmed on unaudited-defaults path (shared code, not a separate exposure). |
| `src/python/reopt_pysam_vn/integration/bridge.py` | No — only builds `SingleOwnerInputs`/`PVWattsBatterySingleOwnerInputs` objects; does not call the runner | Indirect (feeds the callers above) | Builder only; none of its three `SingleOwnerInputs`-returning functions set `zero_reference_plant_defaults`, so every input it builds still carries the un-zeroed defaults downstream. |
| `scripts/python/integration/ceba_deck/calibrate_cases.py` | **Yes** | Feeds `reports/ceba_dppa_2026_repo_check.{md,json}` and `reports/dppa_july_2026_calibration.json` (CEBA/DPPA July 2026 client-deck verification) | **Confirmed on unaudited-defaults path.** |
| `scripts/python/integration/ceba_deck/sweep_56.py` | **Yes** | Feeds `reports/dppa_july_2026_sweep_56*.json` (CEBA deck sensitivity sweeps) | **Confirmed on unaudited-defaults path.** |
| `scripts/python/integration/ceba_deck/deck_checks.py`, `july_deck_checks.py`, `july_runners.py` | No — these read `SingleOwnerInputs`'s *default field values* (e.g. `debt_fraction`, `debt_interest_rate_fraction`) for deck-claim verification; they do not execute the finance model | N/A (verification-only) | Not a runner caller. Because the clean-slate flag defaults to `False`, nothing in these files' behavior changes as a result of this session's work. |
| `scripts/python/integration/analyze_ninhsim_dppa_case_2_phase_f.py` | **Yes** | Writes to `artifacts/reports/...` (git-ignored); feeds Case 2 Phase F narrative in `generate_ninhsim_dppa_case_2_phase_f_report.py`'s output | Confirmed on unaudited-defaults path; output tier is local artifacts, not directly tracked. |
| `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py`, `analyze_saigon18_dppa_case_3_phase_f_22kv.py` | **Yes** | Write to local JSON payloads feeding DPPA Case 3 phase reports (`reports/2026-04-21-dppa-case-3-*.html`) | Confirmed on unaudited-defaults path. |
| `scripts/python/integration/generate_ninhsim_dppa_case_2_phase_f_report.py` | No (references the function name in a docstring/citation only) | Writes an HTML report (git-ignored per repo convention) | Not a runner caller. |
| `scripts/python/integration/run_factory_a_pysam.py` | **Yes** (via the same import path) | Writes to a local JSON output path; feeds `reports/2026-06-19-factory-a-bess-validation.html` and the Factory A / Emivest rerun reports | Confirmed on unaudited-defaults path. |
| `scripts/python/integration/run_ninhsim_single_owner.py` | **Yes** | Writes to `artifacts/reports/ninhsim/...` (git-ignored); feeds `reports/2026-04-02-ninhsim-commercial-candidate-memo.html` and related Ninhsim reports | Confirmed on unaudited-defaults path. |
| `scripts/python/integration/run_ninhsim_solar_storage_60pct_single_owner.py` | **Yes** | Writes to `artifacts/reports/ninhsim/...` (git-ignored); feeds `reports/2026-04-08-ninhsim-solar-storage-60pct-dppa.html` | Confirmed on unaudited-defaults path — **used as the TASK-02-06 comparison case below.** |
| `scripts/python/integration/verify_ceba_dppa_deck.py` | **Yes** (two call sites, lines 602/875) | This is the CEBA/DPPA July 2026 client-deck verification orchestrator itself; writes `reports/ceba_dppa_2026_repo_check.{md,json}` and `reports/dppa_july_2026_repo_check.{md,json}` | **Confirmed on unaudited-defaults path.** Highest-stakes caller alongside `dppa_samsung_ttc.py` — this is the exact pipeline that checked and annotated the CEBA client deck. |
| `scripts/python/pysam/2026-07-17_kbc_proforma_pysam_crosscheck.py` | No — this script **re-implements** its own copy of `_configure_financial_model`-equivalent logic (`run_single_owner_model_clean`) rather than calling the shared function, specifically because it hit the same un-zeroed-defaults problem independently before this session's fix existed | Feeds an external KBC workspace, not this repo's tracked deliverables | Pre-existing, independent workaround. Docstring updated (see below) to point at the new library-level flag as the durable replacement. |
| `scripts/python/pysam/run_single_owner_smoke.py` | **Yes** | Smoke-test script; no tracked output | Confirmed on unaudited-defaults path; no external stakes. |
| `tests/python/integration/test_dppa_samsung_ttc_phase_03.py`, `tests/python/pysam/test_single_owner_phase4.py` | **Yes** (test fixtures) | Test-only, no external deliverable | Not in scope for client-facing risk. |
| `src/python/reopt_pysam_vn/pysam/__init__.py` | No — re-exports `SingleOwnerInputs`/`run_single_owner_model` from `single_owner.py` | N/A | Package export only. |
| `src/python/reopt_pysam_vn/pysam/pvwatts_battery.py` | No — matched only because `PVWattsBatterySingleOwnerInputs` contains the substring `SingleOwnerInputs`; this is a **separate** dataclass and a **separate** financial-model wrapper, not a caller of `single_owner.py`'s code | Not evaluated in this audit | False-positive grep match. Flagged as a candidate for a **separate, future** audit of its own reference-plant-defaults handling — out of scope here per this plan's Out of Scope section. |

**No caller anywhere in the repository passes `zero_reference_plant_defaults=True`** — expected, since the flag was added in this same session and defaults to `False`.

## TASK-02-06: quantified comparison (flag off vs. flag on)

Two cases were run, holding every input identical except the flag, using
the local `.venv` (`nrel-pysam==7.1.0`):

### Case 1 — Ninhsim 60% solar-storage (representative real project, ~100 MW)

Built via `build_ninhsim_solar_storage_single_owner_inputs()` from the
tracked local artifacts `artifacts/results/ninhsim/2026-04-08_ninhsim_solar-storage_60pct_reopt-results.json`,
`scenarios/case_studies/ninhsim/2026-04-08_ninhsim_solar-storage_60pct.json`,
and `data/interim/ninhsim/ninhsim_extracted_inputs.json` (system capacity
100,000 kW, installed cost $113,865,571.62):

| Metric | Flag off (legacy) | Flag on (clean-slate) | Delta |
|---|---|---|---|
| `project_return_aftertax_npv_usd` | -$40,785,148.25 | -$27,000,430.08 | **+$13,784,718.17** |
| `project_return_aftertax_irr_fraction` | 3.83% | 5.96% | **+2.14 percentage points** |

### Case 2 — 1 MW synthetic smoke case (representative small Vietnam C&I scale)

`build_single_owner_inputs(system_capacity_kw=1000.0, installed_cost_usd=550_000.0, ppa_price_input_usd_per_kwh=0.065)`,
matching the scale this defect was originally flagged against (sub-2 MWp
C&I projects):

| Metric | Flag off (legacy) | Flag on (clean-slate) | Delta |
|---|---|---|---|
| `project_return_aftertax_npv_usd` | -$2,472,269.01 | -$76,762.61 | **+$2,395,506.40** |
| `project_return_aftertax_irr_fraction` | `None` (never crosses into positive territory — see the model's own `irr_warning` note) | 7.95% | **flips from a null/negative-signal IRR to a real, positive IRR** |

**Reading these together:** the un-zeroed defaults are not a rounding-level
effect at either scale. At real-project scale (Case 1, ~100 MW), they shift
NPV by nearly $13.8M and IRR by over two full percentage points. At small
C&I scale (Case 2, 1 MW), the effect is proportionally far larger relative
to installed cost — a project can look non-viable (`None` IRR) under the
legacy defaults and clearly viable (7.95% IRR) once the ~100 MW-reference
costs are removed. This is the concrete magnitude behind the concern raised
in `research/2026-07-24-reopt-pysam-sixth-pass-brainstorm.md`.

## Decision required

This audit does not conclude that any specific delivered number is wrong —
SAM's defaults are a legitimate modeling choice for a 100 MW-class US
reference plant, and whether they should apply to a given Vietnam project is
a judgment call this report does not make. What this audit does establish,
as fact:

1. Every tracked and published Single Owner result in this repository to
   date — including the **Samsung/TTC golden fixture**
   (`examples/samsung-ttc_combined-decision.example.json`, via
   `dppa_samsung_ttc.py:771`) and every result behind the **CEBA/DPPA July
   2026 client-deck verification pipeline**
   (`scripts/python/integration/ceba_deck/{calibrate_cases,sweep_56}.py` and
   `scripts/python/integration/verify_ceba_dppa_deck.py`) — was generated
   with the twelve reference-plant fields at their unaudited SAM defaults,
   because no caller could pass the clean-slate flag before this session.
2. The magnitude of that choice is material at both real-project and small
   C&I scale, per the two comparison cases above.

**Whoever owns the Samsung/TTC and CEBA client relationships should read
this report and decide whether any number already shown to Samsung, TTC, or
CEBA warrants a re-review** — for example, whether the SAM reference-plant
defaults were an intentional, disclosed modeling choice for those specific
engagements, or an unexamined default that happened to be inherited. This
plan takes no position on which is true and makes no change to any golden
file or published number; it only surfaces the fact that the question is
now answerable and, until now, was not being asked.

## What this audit did not do

- Did not flip `zero_reference_plant_defaults` to `True` by default anywhere
  (CON-001/DEC-002 of the source plan).
- Did not touch `examples/samsung-ttc_combined-decision.example.json` or any
  other golden/parity fixture.
- Did not regenerate any previously-published report, deck, or artifact.
- Did not contact Samsung, TTC, or CEBA — that determination belongs to the
  relationship owner, not to this automated pass.
