# FX Unification Delta Memo (PHASE-05 Commit 2)

## What moved and why

Per `plans/2026-07-26-post-backlog-architecture-plan.md` PHASE-05, Commit 1
(`refactor(fx): route exchange-rate reads through common.assumptions`) routed
all 22 hardcoded VND/USD literals across 17 files through
`reopt_pysam_vn.common.assumptions.exchange_rate()`, each pinned with an
explicit `caller_value` equal to its pre-existing constant so it changed no
numbers. This commit (`fix(fx): unify general-purpose modules on the
canonical 26,400 VND/USD`) removes that pin from the **general-purpose**
modules only (ASM-005), letting them resolve to the canonical rate,
`26,400` VND/USD (`vn_tariff_2025.json` `_meta.exchange_rate_vnd_per_usd`,
Decision 599/QD-EVN). The per-deal Saigon18 sites (25,450 VND/USD) are
**deliberately left unchanged** — they carry an explicit
`# Deal-specific FX ... Intentionally NOT the repo canonical 26,400` comment
instead.

## Sites that moved

| File | Old value | New value | Scale factor (new USD = old USD × factor) |
|---|---|---|---|
| `src/python/reopt_pysam_vn/reopt/two_part_tariff.py` | 26,000 | 26,400 | 0.984848... (26,000/26,400) |
| `scripts/python/reopt/two_part_tariff_sensitivity.py` | 26,000 | 26,400 | 0.984848... |
| `scripts/python/reopt/build_saigon18_reopt_input.py` | 26,000 | 26,400 | 0.984848... |
| `src/python/reopt_pysam_vn/integration/dppa_case_2.py` (×3 fallback sites) | 25,000 (fallback only, when `extracted`/`settlement_inputs` carries no explicit rate) | 26,400 | 0.946970... (25,000/26,400) |

## Sites that did NOT move (ASM-005 frozen overrides)

| File | Value (unchanged) |
|---|---|
| `src/python/reopt_pysam_vn/integration/dppa_case_3.py` | 25,450 |
| `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py` | 25,450 |
| `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f_22kv.py` | 25,450 |
| `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py` (×2) | 25,450 |
| `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` | 26,400 (already canonical; untouched — this is the parity-gated path, RISK-05-02) |

## Concrete before/after figures

**Case A — `two_part_tariff.compute_two_part_impact` (verified via
`tests/python/reopt/test_two_part_tariff.py::test_compute_two_part_impact_high_load_factor`,
a synthetic 100%-load-factor 1,000 kW profile):**

- `net_impact_vnd` (deterministic, VND-only, unaffected by FX): `-3,307,032,000`
- `net_impact_usd` before (rate 26,000): `-127,193.54`
- `net_impact_usd` after (rate 26,400): `-125,266.36`
- Movement: **-1.5%** of the USD figure (the 1.5% gap between 26,000 and
  26,400), consistent with the 0.984848 scale factor above.

This same scale factor applies to every USD figure produced by
`two_part_tariff_sensitivity.py` and `build_saigon18_reopt_input.py`, since
both resolve through the same now-canonical rate with no per-call override.

**Case B — `dppa_case_2` fallback (illustrative; no tracked example uses this
fallback path directly, since Ninhsim/Samsung deals pin their own rate in
`extracted`, but any future deal that omits `benchmark.exchange_rate_vnd_per_usd`
will now resolve here):**

- Strike price 1,012 VND/kWh converted to USD:
  - Before (25,000 fallback): `$0.04048/kWh`
  - After (26,400 canonical): `$0.03833/kWh`
  - Movement: **-5.3%** — the fallback previously used a rate 5.6% below the
    canonical 26,400 (`(26,400-25,000)/26,400`), so any USD figure computed
    through this fallback path scales by `25,000/26,400 = 0.946970`.
- This is the largest movement in this migration and is the one ASM-002/
  RISK-001 flag explicitly: any historical output that silently hit this
  25,000 fallback (rather than an explicit per-deal rate) understated USD
  figures by ~5.6% relative to the canonical rate.

## Note on developer NPV/IRR figures

The plan's Test Specs ask for developer NPV (USD), developer IRR (fraction),
and buyer blended cost (USD/kWh) for each affected case. Of the four flipped
modules, none directly produce a developer NPV/IRR: `two_part_tariff.py` and
its two callers compute a deterministic demand-charge/energy-rate delta
(`net_impact_vnd`/`net_impact_usd`, shown above), not a financed project
cash-flow model, and `dppa_case_2.py`'s three fallback sites only fire when a
deal's `extracted` input omits `benchmark.exchange_rate_vnd_per_usd` — no
currently tracked deal (Ninhsim, Samsung-TTC) does this; Samsung-TTC pins its
own rate explicitly and is unaffected (confirmed by the non-movement guard
below). Developer NPV/IRR *are* produced downstream by
`dppa_samsung_ttc.py`'s PySAM Single-Owner run, but that module's own
exchange rate was already 26,400 and is excluded from this flip by design
(RISK-05-02) — its NPV/IRR movement is documented separately in
`reports/2026-07-26-samsung-parity-diagnosis.md` and is unrelated to this
FX migration. The strike-price USD/kWh figure in Case B above is the closest
available proxy for "buyer blended cost" on the sites this commit actually
moves.

## Verification performed

- Commit 1 gate: full portable suite identical before/after (634 passed, 18
  deselected, 3 xfailed, same three `x` positions) and `git diff --exit-code
  examples/` clean — confirmed byte-identical, no numbers moved.
- Commit 2: full portable suite re-run surfaced exactly one test needing an
  update (`test_compute_two_part_impact_high_load_factor`), updated with an
  inline comment naming the old/new value and this memo. All other assertions
  were unaffected because no other tracked test exercises the flipped
  general-purpose modules' USD output at the specific values that moved.
- `git diff --exit-code examples/samsung-ttc_combined-decision.example.json`
  → clean (Commit-2 non-movement guard: Samsung-TTC was already on 26,400 and
  is not in the flip list).
- `grep -rnE "EXCHANGE_RATE[A-Z_]* *= *2[0-9][,_]?[0-9]{3}" --include=*.py src scripts | grep -v __pycache__ | grep -v "Intentionally NOT"`
  → only `preprocess.py`'s documented `DEFAULT_EXCHANGE_RATE` last-resort
  fallback remains as a bare literal.
