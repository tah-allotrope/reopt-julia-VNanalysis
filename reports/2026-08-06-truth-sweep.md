# Truth Sweep Report (2026-08-06)

**Date:** 2026-08-06
**Scope:** `plans/2026-08-06-ci-gate-integrity-and-second-orchestrator-plan.md` PHASE-02
**Status:** Complete — no document now claims a guarantee the code does not enforce.

## Summary

The red CI pipeline (fixed in PHASE-01) had masked three structural gaps: two
files still advertised a bit-for-bit parity guarantee the tests deliberately do
not make, one test actively pinned the known golden divergence in place, and
`AGENTS.md` carried five-month-old status sections including a repealed
regulatory cap. This phase corrected each claim, gave the regulatory watch a
falsifiable currency check, triaged the stale branches, and removed the last
test shim.

## Claims corrected

### 1. `src/python/reopt_pysam_vn/webapp/README.md` (lines 63–66)
- **Before:** "The Samsung/TTC golden-parity test (`test_golden_parity.py`)
  proves the web API path reproduces
  `examples/samsung-ttc_combined-decision.example.json` bit-for-bit."
- **After:** states that `test_samsung_ttc_web_api_matches_direct_library_call_bit_exact`
  proves `POST /api/runs` reproduces a direct `run_offsite_dppa` call
  bit-for-bit (CON-002, no forked analytics), and that it deliberately does
  **not** re-assert parity against the golden, which carries a known
  pre-existing divergence documented in
  `reports/2026-07-26-samsung-parity-diagnosis.md`.

### 2. `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` (module docstring)
- **Before:** described the combined-decision as reproduced "bit-for-bit"
  (`test_samsung_ttc_parity`) — a parity-gated claim.
- **After:** matches `docs/onsite_vs_offsite.md`: a **local-only diagnostic**,
  CI-excluded via the `golden_machine` marker, currently `xfail`ed because
  `developer_irr_fraction` diverges from the golden. No code changed (CON-001).

### 3. `AGENTS.md` §4 "Test Suite Status (last run: Mar 2026)"
- **Before:** a March-2026 table reporting two FAIL rows and "L4 Julia: NOT RUN".
- **After:** deleted; replaced with a one-line pointer to `activeContext.md` as
  the authority for current test state, plus the standing note that CI runs
  `pytest tests/python` with the four-marker exclusion filter.

### 4. `AGENTS.md` §6 "Real Project Data Notes"
- **Before:** listed "Custom JuMP constraint for 20% generation export cap
  (Decree 57)" as a next step.
- **After:** the next-steps list no longer references the repealed cap; a note
  states Decree 243/2026 raised the cap to 50 % effective 2026-06-26 and points
  at `data/vietnam/vn_export_rules_2026_decree243.json`. The three "Identified
  gaps" are retained (still accurate).

## Drift test re-polarization (S5)

`tests/python/webapp/test_golden_parity.py::test_samsung_ttc_golden_drift_is_the_known_pre_existing_gap`
asserted the drift **exists** — the suite was green *because* the analytics
were wrong. Replaced with
`test_samsung_ttc_golden_drift_stays_within_the_known_manifest`, which asserts
the actual diverging path set is a **subset** of a measured, catalogued manifest:

- **Measured** (live `run_offsite_dppa` vs golden, 2026-08-06): 15 diverging
  leaf paths across 3 families:
  - `strike_sweep.sweep[*].developer_irr_fraction` (5 sites)
  - `strike_sweep.sweep[*].developer_npv_usd` (5 sites)
  - `strike_sweep.negotiation_summary.buyer_saves_candidates[*].developer_irr_fraction` (2 sites)
  - `strike_sweep.negotiation_summary.buyer_saves_candidates[*].developer_npv_usd` (2 sites)
  - `strike_sweep.sweep[*].developer_passes` (1 site — the golden's
    `developer_irr_fraction` is `None`, so its `developer_passes` is `False`
    while live computes a passing IRR)
- **Manifest seeded from that measured list** (`[*]` wildcards), not from a
  guess.
- **Polarity consequences verified:** a *new* divergence turns red; a *fixed*
  divergence (empty actual set) stays green; fixing everything leaves the
  manifest empty-able in a follow-up.
- Helper functions `_leaf_paths` / `_diverging_paths` pass their spec, including
  the **`bool` guard** — `True` vs `1` diverges (`True == 1` in Python).

## Regulatory watch (F7 / TASK-02-06/07)

- Added `Last verified` and `Next review` columns to `docs/regulatory-watch.md`.
- `tariff` row: `Last verified 2026-08-06` (live check — EVN average retail
  price 2,204.0655 VND/kWh ex-VAT still standing), `Next review 2026-11-06`
  (3-month horizon, matching the minimum adjustment interval Decision
  07/2025/QD-TTg permits EVN).
- Every other row: `Last verified` = the commit date that last touched its
  active file; `Next review` = that date + 6 months.
- Added `tests/python/test_repo_invariants.py::test_regulatory_watch_rows_are_not_overdue`,
  which fails naming every row whose `Next review` is in the past. Verified the
  failure mode: with `tariff`'s date set to `2020-01-01` the test reports the
  overdue row and date.

## Branch triage (TASK-02-08, ASM-010)

| Branch | Unique commits (`main..<branch>`) | Action |
|---|---|---|
| `real-project-data` | 0 | Deleted (`git branch -d` + `git push origin --delete`) |
| `claude/clever-chaplygin-dad6dc` | 0 | Deleted (local-only) |
| `claude/kind-mcclintock-10b2e5` | 0 | Deleted (local-only) |

All three were fully merged into `main`; no unique work was lost. Remote now
holds only `main`.

## Test-shim removal (TASK-02-09)

- Deleted `tests/cross_validate.py` — a 14-line `runpy` shim delegating to
  `tests/cross_language/cross_validate.py`. Confirmed no live caller references
  the flat path.
- Added `tests/python/test_repo_invariants.py::test_no_test_shims`, which fails
  if a flat `.py` file is re-added under `tests/`.

## Housekeeping

- `.gitignore`: added root-anchored `/*.log` (covers the stray
  `phase6_test.log`; nested log files unaffected). `git status` confirmed no
  previously tracked file changed ignore state.
- `activeContext.md`: "CI status" line now cites run `31159536433` (2026-08-06)
  and notes it was verified with `gh run list`, not just a local run.
- `AGENTS.md` §2: added the "Verify CI, not just local tests" bullet (DEC-005) —
  `gh run list --limit 3` is a required step before reporting work complete.

## Verification

- `PYTHONPATH= python -m pytest tests/python/webapp/test_golden_parity.py -v` → `2 passed`.
- `PYTHONPATH= python -m pytest tests/python/test_repo_invariants.py -v` → `5 passed`.
- Full portable suite: **636 passed, 18 deselected, 3 xfailed** (634 baseline
  + 2 new invariant tests: `test_no_test_shims` and
  `test_regulatory_watch_rows_are_not_overdue`; the re-polarized drift test is
  still one test).
- `grep -rn "parity-gated|bit-for-bit" README.md docs/ src/python/reopt_pysam_vn/`
  returns only factually true statements (each hit read and confirmed).
