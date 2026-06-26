# Active Context

> **Convention:** keep this file slim — current state only (target < ~150 lines).
> Rotate finished-work history into `docs/worklog/`. Full pre-2026-06-12 log:
> [`docs/worklog/2026-06-12-activecontext-archive.md`](docs/worklog/2026-06-12-activecontext-archive.md).

## Current focus — July 2026 Case Studies deck verification (calibrate-then-validate) — started 2026-06-26

Goal: verify the claims/figures in `ceba-review/DPPA Presentation July 2026 Case Studies.pptx`
(28 slides, "Session 5.1: Off-Site Solutions Deep Dive") against `reopt_pysam_vn`, making the
deck's undisclosed inputs (CAPEX, BESS size, FMP series) **explicit assumptions** and back-solving
them so Cases 5/6 are reproducible — then testing whether the deck's downstream logic (gate
crossing, "0 of 56 scenarios pass", buyer-vs-BAU) survives that calibration.

- **Brainstorm:** `research/2026-06-26_dppa-july-deck-verification-brainstorm.md` (8 DECs, 3 open Qs)
- **Plan:** `plans/active/2026-06-26-dppa-july-deck-verification-plan.md` (multi-phase) — see plan for phase status
- **Deck (untracked binary):** `ceba-review/DPPA Presentation July 2026 Case Studies.pptx`

### Phase status (PHASE-01..04 ✅ done 2026-06-26; PHASE-05 in progress)
- **PHASE-01 ✅** — `DeckConfig` parametrization + `july_deck_checks.py` registry (50 checks across
  15 slides) + 🔧 "calibrated" verdict tier + extractor's `--deck` flag + new smoke test
  (`test_july_deck_checks.py`, 8 tests passing). CEBA tests still green (13 tests).
- **PHASE-02 ✅** — `july_runners.py` (49 per-check runners: 10 A-bucket + 4 worked example +
  14 calibrated stubs + 5 deferred-to-PHASE-04 sweep stubs + 5 C-bucket functional). Worked
  example (B01-B04) lands ✅ on the engine's flat-profile sim (10,586,097,600 VND; 600,000,000 VND;
  1,864 VND/kWh; 2,027.30 VND/kWh). 13 ok / 3 warn / 10 info / 1 bad (A17, fixed in PHASE-03) / 9 skip /
  14 calibrated.
- **PHASE-03 ✅** — `calibrate_cases.py` (1-D bisection on `installed_cost_usd`, BESS pinned from
  deck hints, year-11 BESS replacement cashflow). Initially reported monotonic miss at the
  default CAPEX range [1M, 10M]; rerun with wider range [100K, 10M] converges:
  - Case 5: CAPEX $1.78M ($339/kW), modeled IRR 16.7% (target 16.9%)
  - Case 6: CAPEX $487K ($93/kW), modeled IRR 27.1% (target 26.9%)
  Implied CAPEX is unrealistically low → the deck's stated metrics require undisclosed
  inputs (higher matched volume, higher CF, etc.). The 🔧 calibrated verdict records the
  solved CAPEX + modeled value per case; the calibration JSON preserves the assumption ledger.
- **PHASE-04 ✅** — `sweep_56.py` (11 strikes 1,200–2,200 VND/kWh × 4 volumes 70–100% = 44 scenarios;
  buyer cumulative ≤ BAU + seller IRR ≥ 12% + lender min DSCR ≥ 1.20x gates) +
  `sweep_56_sensitivities.py` (FMP=1,426.6 vs 1,700 + synthetic vs Emivest). All three configurations
  return **0 of 44 scenarios passing all three gates at the calibration's $4M CAPEX basis**.
  The deck's qualitative "0 of 56" headline is supported; the deck's quantitative numbers
  (specific deltas, IRRs, DSCRs) are not reproducible from disclosed terms.
- **PHASE-05 in progress** — `inject_repo_notes.py --deck july` produces
  `ceba-review/DPPA Presentation July 2026 Case Studies [repo-checked].pptx` with 15 slides
  annotated; idempotency test (`test_inject_idempotency_july.py`) confirms byte-stable notes
  payload across two runs.

### Final verdict counts (PHASE-04 post-sweep)
- 13 ✅ ok (≤ ±1%) — A-bucket (10) + worked example B01-B04 (4) + A11 (1, offset by A17 moving to ⚠️)
- 4 ⚠️ warn (1–5% / structural reconcile) — A02 ratio, A07 Kpp collapse, A12 FMP cite, A17 analysis years
- 15 ℹ️ info (qualitative / method-level / directional) — A01, A15, A16, B05, C01-C10
- 4 ❌ bad (> 5% delta) — B21-B24 (the four disclosed gate rows; deck's stated numbers don't reproduce)
- 0 ➖ skip
- 0 💥 err
- 14 🔧 calibrated — Case 5/6 family (model hits deck value ±0.5pp at the solved CAPEX)

### Grill Me decisions (locked 2026-06-26)
- **Q-001** ✅ Solar sized to ~85% of factory 9,750 MWh/yr load (≈ 5.25 MWp at 18% CF,
  per the 56-sweep volume axis).
- **Q-002** ✅ Seller equity IRR = `project_return_aftertax_irr_fraction` (levered, aftertax);
  Project IRR = unlevered/pretax IRR (`project_return_pretax_irr_fraction`), consistency
  check only.
- **Q-003** ✅ ~$160/kWh → Case 5 BESS = 7.5 MWh (pin from "~$1.2M year-11 replacement"
  hint); Case 6 = 4 MWh (lean "minimum" sizing, scaled down from the 10.7 MWh on-site
  reference).

### Key decisions locked in the brainstorm
- **DEC-001** Calibrate-then-validate (not flag-gaps-only).
- **DEC-002** Load = synthetic 9,750 MWh anchor (Emivest/Factory A "same factory") + real 2024 meter
  (`data/raw/factory_a/emivest_load_profile_1hr_2024.csv`, ~9,315 MWh) as a sensitivity.
- **DEC-003** FMP = deck 1,426.6 anchor + repo 1,700 sensitivity; flat-at-mean hourly shape.
- **DEC-004** Pin BESS from hints (Case 5 ← $1.2M replacement, Case 6 ← on-site 10.7 MWh), solve
  project CAPEX only to hit seller IRR; other 5 metrics are pass/fail consistency checks.
- **DEC-005** Parametrize the pipeline (deck_config) so CEBA + July decks coexist → July registry +
  calibration module + delta report + annotated `[repo-checked]` deck. CEBA artifacts untouched.

### Reuse map (no re-implementation)
- Settlement: `src/python/reopt_pysam_vn/integration/settlement.py` (`compute_hourly_settlement`, `ContractParams`)
- Finance: `src/python/reopt_pysam_vn/pysam/single_owner.py` (`run_single_owner_model`)
- Strike sweep: `src/python/reopt_pysam_vn/integration/strike_search.py` (`sweep_strike_prices`)
- Load: `src/python/reopt_pysam_vn/integration/factory_a.py` + `scenarios/case_studies/factory_a/`
- Pipeline to parametrize: `scripts/python/integration/ceba_deck/` (`deck_checks.py`, `verify_ceba_dppa_deck.py`, `synthesize_md_report.py`, `inject_repo_notes.py`)

## Recently completed (on main)

### Cong BESS session deck review (2026-06-23)
- Research brief `research/2026-06-23_bess-deck-claims.md` (97 sources) validating Session 4.3 claims.
- 9 OOXML comments (4 regulatory fact-checks B1–B4 + 4 model-validation findings M1–M4) injected into
  `ceba-review/cong bess session [reviewed].pptx` via `scripts/python/add_bess_review_comments.py`
  (commits `17f4cc3`, `e5539c3`). M1 surfaced the synthetic-9,750 vs real-meter-9,315 MWh load gap.

### CEBA DPPA 2026 deck verification (2026-06-23, 5 phases)
- Full pipeline under `scripts/python/integration/ceba_deck/` + `reports/ceba_dppa_2026_repo_check.{json,md}`.
- **Actual outcome (per the report): 16 ✅ ok / 5 ⚠️ reconcile (A02, A07, A12, B05, B06) / 14 ℹ️ / 0 ❌.**
  (Earlier drafts of this file said "5 bad" — that was never the committed result; DEC-007 means
  PySAM null-IRR is filed ℹ️, never forced to ❌.)
- Headline: Cases 5/6 (deck IRR 16.9% / 26.9%) not reproducible under proxy CAPEX — repo gives
  *negative* DSCR at strike 2,000. A12: deck FMP 1,426.6 vs repo center 1,700. ← the July deck
  verification picks this exact thread up via calibration.

## Environment
- PySAM 7.1.0 + python-pptx 1.0.2 live in the repo **`.venv` (Python 3.12)** — use
  `.venv\Scripts\python.exe` for PySAM/PVWatts, the deck pipeline, and the test suite. System
  Python 3.14 has no PySAM wheel (code falls back to a synthetic profile).
- Tests: `.\tests\run_all_tests.ps1` (PowerShell runner) or `pytest tests/python/...`.

## Known pre-existing test failures (backlog, out of scope)
- `tests/python/integration/test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`
- `tests/python/integration/test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`

Both are numeric benchmark/tolerance drift — confirmed failing before recent work (verified at commit `5297f89`).
