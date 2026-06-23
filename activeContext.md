# Active Context

> **Convention:** keep this file slim — current state only (target < ~150 lines).
> Rotate finished-work history into `docs/worklog/`. Full pre-2026-06-12 log:
> [`docs/worklog/2026-06-12-activecontext-archive.md`](docs/worklog/2026-06-12-activecontext-archive.md).

## Current focus — CEBA DPPA 2026 deck repo verification (started 2026-06-23, all 5 phases complete 2026-06-23)

Goal: run every repo-testable claim in `ceba-review/CEBA DPPA 2026.pptx` through
real `reopt_pysam_vn` functions, emit a results JSON + delta markdown, and write
structured `[Repo check]` notes into a copy of the deck so colleagues review
against repo-computed figures before the CEBA workshop.

- **Plan:** `plans/2026-06-23-ceba-deck-repo-verification-plan.md` (5 phases, all complete)
- **Brainstorm:** `research/2026-06-23_ceba-deck-repo-verification-brainstorm.md`
- **Source deck text:** `ceba-review/ceba_dppa_2026_text.txt` (extracted via `_extract_ceba_deck_text.py`)
- **Workflow:** implement phase → run `/report <phase>` → git commit → git push origin main. ✅

### Status — all 5 phases done (commits on main)

| Phase | Goal | State | Commit |
|---|---|---|---|
| 0 | Extract deck text, write plan | ✅ | dd1a59e (brainstorm+plan) |
| 1 | Build `deck_checks.py` registry | ✅ | b87f2cb |
| 2 | Build `verify_ceba_dppa_deck.py` + JSON | ✅ | 62bc0e3 |
| 3 | Synthesize markdown report | ✅ | 3c26003 |
| 4 | Inject notes into `[repo-checked].pptx` | ✅ | 919503a |
| 5 | End-to-end run + final report | ✅ | c6800c5 |

### Final results (34 checks)
- 9 ✅ ok (match within ±1%)
- 1 ⚠️ warn (A12 FMP cited 1,426.6 vs repo center 1,700 — DEC-008 reconcile)
- 18 ℹ️ info (qualitative / method-level — most B-bucket settlement checks at 1-5% delta from kpp collapse)
- 5 ❌ bad (> 5% delta: A02, A04, B04, B12, B14)
- 1 ➖ skip (A05 — no single-value repo equivalent)
- 0 💥 err

### Headline finding
**PySAM returns null IRR for Case 5 (deck: 16.9%) and Case 6 (deck: 26.9%).**
The repo model says the project does not cashflow under the deck's stated inputs
(49 MWp, 70% debt / 8.5% / 10-yr, strike 2,000 VND/kWh, 25-yr). The deck's
figures require undisclosed CAPEX / BESS sizing / FMP assumptions that cannot
be reproduced from disclosed inputs (DEC-007 method+directional). This is in
the deck note for Slides 24/25, in the markdown's structural reconciliations,
and in the final HTML report.

### Deliverables (all on main, all in scripts/python/integration/ceba_deck/ or reports/)
- `deck_checks.py` — registry (34 checks + 3 known gaps)
- `test_deck_checks.py` — 5 smoke tests (all pass)
- `verify_ceba_dppa_deck.py` — orchestrator (writes JSON)
- `synthesize_md_report.py` — JSON → markdown
- `inject_repo_notes.py` — JSON → pptx notes (idempotent)
- `test_inject_idempotency.py` — sha256 byte-stability check
- `_extract_ceba_deck_text.py` — pptx → txt (Phase 0 helper, sits in integration/)
- `ceba-review/CEBA DPPA 2026 [repo-checked].pptx` — 12.96 MB, 24 slides annotated (UNTRACKED, DEC-009)
- `reports/ceba_dppa_2026_repo_check.json` (30,552 bytes)
- `reports/ceba_dppa_2026_repo_check.md` (10,768 bytes)
- 5 per-phase HTML reports under `reports/2026-06-23-phase-{01..05}-*.html`
- `reports/2026-06-23-final-ceba-deck-repo-verification.html` — final synthesis

## Environment
- PySAM 7.1.0 lives in the repo **`.venv` (Python 3.12)** — use `.venv\Scripts\python.exe` for PySAM/PVWatts
  and for the test suite. System Python 3.14 has no PySAM wheel (code falls back to a synthetic profile).
- Tests: `.\tests\run_all_tests.ps1` (PowerShell runner) or `pytest tests/python/...`.
- python-pptx 1.0.2 is also installed in `.venv` for the deck note injector.

## Known pre-existing test failures (out of scope for the trim — backlog)
- `tests/python/integration/test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`
- `tests/python/integration/test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`

Both are numeric benchmark/tolerance drift — confirmed failing before the trim work (verified at commit `5297f89`).


## Environment
- PySAM 7.1.0 lives in the repo **`.venv` (Python 3.12)** — use `.venv\Scripts\python.exe` for PySAM/PVWatts
  and for the test suite. System Python 3.14 has no PySAM wheel (code falls back to a synthetic profile).
- Tests: `.\tests\run_all_tests.ps1` (PowerShell runner) or `pytest tests/python/...`.
- python-pptx 1.0.2 is also installed in `.venv` for the deck note injector.

## Known pre-existing test failures (out of scope for the trim — backlog)
- `tests/python/integration/test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`
- `tests/python/integration/test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`

Both are numeric benchmark/tolerance drift — confirmed failing before the trim work (verified at commit `5297f89`).
