# PHASE-02 — Reproducible checks (A-bucket + worked-example settlement, slides 4–15)

_Generated 2026-06-26 from the in-progress plan
`plans/active/2026-06-26-dppa-july-deck-verification-plan.md`._

## Goal

Populate the deterministic, disclosed-input checks: tariff/fee/loss-factor/finance
assumptions and the slides 10–12 five-line worked example.

## What shipped

- **`scripts/python/integration/ceba_deck/july_runners.py`** — new module
  with 49 per-check runners keyed by July check id (`J_A*`, `J_B*`, `J_C*`).
  The orchestrator loads this module when `--deck july` is passed and merges
  it with the inline `_SCENARIO_RUNNERS` dispatch (CEBA ids never collide
  with `J_*` ids, so the two decks coexist cleanly).
- **`scripts/python/integration/verify_ceba_dppa_deck.py`** — added a
  `_load_july_runners()` helper and an `extra_runners` parameter on
  `run_check()`; the main() loads July runners only when `config.key == "july"`.
  Status line prints the runner count (e.g. `july_runners=49`).
- **`scripts/python/integration/ceba_deck/synthesize_md_report.py`** —
  fixed a bug where the July-specific structural-reconciliations note
  was being added character-by-character (the `out += (string)` was
  treating the string as an iterable). Replaced with `out += [...]`.

## What each runner does

| Bucket | Check ids | Status |
|---|---|---|
| **A — data lookups** | `J_A02..J_A17` (10 of 16: A02, A04, A06, A07, A09, A10, A11, A14, A15, A16, A17) | Runners wire to `ContractParams` / `SingleOwnerInputs` defaults or `_resolve_vietnam_data` lookups. A03 / A05 / A08 / A12 use the generic `data.vietnam.*` path. |
| **B — worked example** | `J_B01..J_B04` | Re-implement the deck's 6,000 MWh flat-profile sim. Engine collapses to the deck's line 1+2+3+4 = **10,586,097,600 VND** (✅ match), line 5 = **600,000,000 VND** (✅ match), total / Q = **~1,864 VND/kWh** (✅ match). J_B04 reproduces 1,504 + 360 + 163.3 = **2,027 VND/kWh** pre-CfD delivered cost. |
| **B — Case 5/6 metrics** | `J_B05..J_B20` (14 ids) | `_calibrated_stub` returns the deck value; classify() routes to 🔧 `calibrated` tier (PHASE-03 replaces). |
| **B — 56-sweep** | `J_B21..J_B25` (5 ids) | `_deferred_to_phase04` — verdict is `skip` with a "deferred to PHASE-04" takeaway. |
| **C — qualitative** | `J_C01..J_C10` | Engine-supported (overcontracting cap, load-shape overlap, year-1 vs BAU, voltage/K_pp, three-gate formulas) wired in. C05 (battery-replacement DSCR dip) and C06/C07/C09 (sweep-derived) deferred to PHASE-03/04. |

## Verdict counts (this run, 2026-06-26)

| Verdict | Count | Share | Notes |
|---|---:|---:|---|
| ✅ ok (≤ ±1%) | 13 | 26% | A03, A04, A05, A06, A08, A09, A10, A11, A14, B01, B02, B03, B04 — deck text matches the engine's flat-profile sim line-for-line. |
| ⚠️ warn (1–5% / structural reconcile) | 3 | 6% | A02 (1.42%, peak/normal ratio), A07 (1.91%, Kpp collapse), A12 (+19%, FMP cited anchor vs repo sensitivity center). |
| ℹ️ info (qualitative / method-level) | 10 | 20% | A01, A15, A16, B05, C01, C02, C03, C04, C08, C10. |
| ❌ bad (> 5% delta) | 1 | 2% | A17 — engine default `analysis_years=20` vs deck `25`. The 25-yr deal frame is authoritative; **PHASE-03 will set `analysis_years=25` on the calibration inputs and this will become ✅** (`-20%` → `+0%`). |
| ➖ skip (out of scope / deferred) | 9 | 18% | B21–B25 (sweep) + C05 (battery-replacement DSCR dip) + C06, C07, C09 (sweep-derived). |
| 💥 err (runner error) | 0 | 0% | |
| 🔧 calibrated (solver target) | 14 | 28% | The Case 5/6 family. PHASE-03 replaces. |
| **Total** | **50** | 100% | |

## Exit criteria check

- [x] Worked-example checks (B01–B04) match to ≤ 0.1%:
  - B01: deck 10,586,097,600 VND; engine returns 10,586,097,600 VND; **delta +0.000%** ✅
  - B02: deck 600,000,000 VND; engine returns 600,000,000 VND; **delta -0.000%** ✅
  - B03: deck 1,864 VND/kWh; engine returns 1,864 VND/kWh; **delta +0.000%** ✅
  - B04: deck 2,027 VND/kWh; engine returns 2,027.30 VND/kWh; **delta +0.015%** ✅
- [x] A-bucket verdicts match the prior CEBA values (the underlying data didn't change), differing only in slide numbers and id prefixes (J_*).
- [x] The J_B01..B04 runners do not require PySAM; the orchestrator
  reads the engine's `compute_hourly_settlement` return dict directly.
- [x] 0 runner errors; the orchestrator runs end-to-end on `--deck july`.

## What did NOT ship (deferred to later phases)

- **A17** (`analysis_years=25` mismatch). The 25-yr deal frame is
  authoritative; PHASE-03 will set `analysis_years=25` on the calibration
  inputs so the verdict becomes ✅.
- **Case 5/6 family** (14 checks) — all 🔧 `calibrated` from this phase.
  PHASE-03 will replace the stubs with real computed values from the
  back-solved CAPEX.
- **56-sweep + 4 downstream checks** (B21–B25, C05, C06, C07, C09) — all
  ➖ `skip` from this phase. PHASE-04 will run the full sweep and the
  load/FMP sensitivities.

## Artifacts

- **`reports/dppa_july_2026_repo_check.json`** — 48 KB. 50 checks with
  full `repo_value`, `extra`, `verdict`, `takeaway` per row.
- **`reports/dppa_july_2026_repo_check.md`** — 14.7 KB. Header counts
  + per-bucket tables + slim structural-reconciliations note + methodology
  + re-run instructions.

## Verification commands

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='src/python;scripts/python'

# 1) Orchestrator
.venv\Scripts\python.exe scripts\python\integration\verify_ceba_dppa_deck.py --deck july

# 2) Synthesizer
.venv\Scripts\python.exe scripts\python\integration\ceba_deck\synthesize_md_report.py --deck july

# 3) Confirm CEBA still green
.venv\Scripts\python.exe -m unittest scripts.python.integration.ceba_deck.test_deck_checks
.venv\Scripts\python.exe -m unittest scripts.python.integration.ceba_deck.test_july_deck_checks
```
