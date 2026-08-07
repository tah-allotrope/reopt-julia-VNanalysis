# FX Derivation Delta Memo (2026-08-06)

**Date:** 2026-08-06
**Scope:** `plans/2026-08-06-ci-gate-integrity-and-second-orchestrator-plan.md` PHASE-03
**Status:** Complete — **zero published numbers moved.**

## Summary

The FX refactor in PHASE-04/05 achieved *unification* (one value, 26,400
VND/USD, everywhere) without *derivation* (one source of truth): 14 call sites
passed `caller_value=26_400.0`, which is step 1 of the resolver's precedence
chain and always wins — so editing `data/vietnam/vn_deal_defaults_2026.json`'s
rate moved 5 sites, not 19. This phase dropped the `caller_value` argument from
the 8 general-purpose sites so the data layer is now authoritative, and proved
it with a new test suite.

## The 8 unpinned sites (TASK-03-02)

| File | Line | Constant |
|---|---|---|
| `src/python/reopt_pysam_vn/integration/factory_a.py` | 45 | `EXCHANGE_RATE_VND_PER_USD` |
| `src/python/reopt_pysam_vn/reopt/decree243_delta.py` | 28 | `_DEFAULT_EXCHANGE_RATE_VND_PER_USD` |
| `scripts/python/integration/build_ninhsim_extracted_inputs.py` | 28 | `EXCHANGE_RATE_VND_PER_USD` |
| `scripts/python/reopt/bess_dispatch_analysis.py` | 33 | `EXCHANGE_RATE_VND_PER_USD` |
| `scripts/python/reopt/decree146_demand_charge.py` | 43 | `EXCHANGE_RATE_VND_PER_USD` |
| `scripts/python/reopt/decree243_export_cap_delta.py` | 33 | `DEFAULT_EXCHANGE_RATE` |
| `scripts/python/reopt/dppa_settlement.py` | 28 | `EXCHANGE_RATE_VND_PER_USD` |
| `scripts/python/reopt/fmp_sensitivity.py` | 41 | `EXCHANGE_RATE_VND_PER_USD` |

Each became `_resolve_exchange_rate(load_vietnam_data())` — the surrounding
assignment and the `load_vietnam_data()` argument are untouched.

## The 6 deliberately retained pins (TASK-03-03 / TASK-03-04, ASM-009)

- **1 parity pin:** `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py:97`
  keeps `caller_value=26_400.0`. Its comment now states explicitly that the pin
  is deliberate — to insulate the parity-gated path (CON-001) from data-layer
  edits so the Samsung golden cannot move under it.
- **5 deal-specific pins (Saigon18 contract basis, 25,450 VND/USD):**
  - `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py:41`
  - `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f_22kv.py:32`
  - `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py:66` and `:188`
  - `src/python/reopt_pysam_vn/integration/dppa_case_3.py:70`
  Each already carried (or was confirmed to carry) the comment "Deal-specific
  FX: Saigon18 contract basis, 25,450 VND/USD." **No value changed.**

## Proof of zero numeric movement (TASK-03-05)

Because `vn_deal_defaults_2026.json` holds exactly `26400`, every unpinned site
resolves to the identical float. Verified:

- **Pre-change:** `636 passed, 18 deselected, 3 xfailed`
- **Post-change:** `643 passed, 18 deselected, 3 xfailed` — the +7 are the new
  `tests/python/common/test_assumptions_authority.py` cases; **no test count
  dropped and no numeric assertion changed.**
- Source-level invariant: `grep -rn "caller_value=26_400.0" src scripts` → `1`
  (Samsung only). `grep -rn "caller_value=25450.0|caller_value=25_450.0" src scripts`
  → `5`.
- `ruff check src scripts tests` → `All checks passed!`
- `mypy ...analysis ...webapp` → `Success: no issues found in 21 source files`

## New authority invariant (tests/python/common/test_assumptions_authority.py)

| Test | Asserts |
|---|---|
| `test_deal_defaults_rate_is_authoritative` | a copy of `VNData` with rate `30000.0` resolves to `30000.0`, **not** `26400.0` |
| `test_caller_value_still_wins_over_data_layer` | `caller_value=25450.0` still beats a modified data layer |
| `test_per_deal_override_still_honoured` | `extracted` per-deal override still wins |
| `test_unmodified_default_rate` | `exchange_rate(load_vietnam_data()) == 26400.0` |
| `test_zero_rate_raises` | zero rate raises `ValueError: ... must be positive` |
| `test_general_purpose_modules_do_not_pin_caller_value` | the 8 files carry **zero** `caller_value=26_400.0` matches |
| `test_samsung_path_retains_the_single_deliberate_pin` | `dppa_samsung_ttc.py` carries **exactly one** |

The last two are the source-level invariant that failed before TASK-03-02 and
passed after — the Red/Green pair.

## Risk mitigations exercised

- **RISK-03-01 (silent rate pickup):** the pre-check confirmed the data layer
  holds exactly `26400`; the full suite ran immediately after and no numeric
  assertion moved.
- **RISK-03-02 (order-dependent global mutation):** the authority test builds a
  deep-copied `VNData` via `dataclasses.replace` and never mutates the shared
  instance or the tracked JSON on disk.
- **RISK-03-03 (Samsung pin removed as an oversight):** the pin's comment names
  CON-001 explicitly, and this memo records the retention as deliberate.

## Consequence

Editing `data/vietnam/vn_deal_defaults_2026.json`'s
`data.exchange_rate.vnd_per_usd` now moves **every general-purpose module** —
a one-line edit instead of a nine-file sweep. The two documented exception
classes (Samsung parity pin, Saigon18 25,450 contract basis) are recorded in
`AGENTS.md` §5.
