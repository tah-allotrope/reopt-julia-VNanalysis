# Active Context

> **Convention:** keep this file slim — current state only (target < ~150 lines).
> Rotate finished-work history into `docs/worklog/`. Full pre-2026-06-12 log:
> [`docs/worklog/2026-06-12-activecontext-archive.md`](docs/worklog/2026-06-12-activecontext-archive.md).

## Current focus — CEBA DPPA 2026 deck repo verification (started 2026-06-23)

Goal: run every repo-testable claim in `ceba-review/CEBA DPPA 2026.pptx` through
real `reopt_pysam_vn` functions, emit a results JSON + delta markdown, and write
structured `[Repo check]` notes into a copy of the deck so colleagues review
against repo-computed figures before the CEBA workshop.

- **Plan:** `plans/2026-06-23-ceba-deck-repo-verification-plan.md` (5 phases)
- **Brainstorm:** `research/2026-06-23_ceba-deck-repo-verification-brainstorm.md`
- **Source deck text:** `ceba-review/ceba_dppa_2026_text.txt` (extracted via `_extract_ceba_deck_text.py`)
- **Workflow:** implement phase → run `/report <phase>` → git commit → git push origin main.
- **After all phases:** run `/report final plans/2026-06-23-ceba-deck-repo-verification-plan.md`.

### Status

| Phase | Goal | State |
|---|---|---|
| 0 | Extract deck text, write plan | ✅ done (text extracted 2026-06-23) |
| 1 | Build `deck_checks.py` registry | ⏳ in progress |
| 2 | Compute all A/B/C testables → JSON | pending |
| 3 | Synthesize `reports/ceba_dppa_2026_repo_check.md` | pending |
| 4 | Inject `[Repo check]` notes into a deck copy | pending |
| 5 | End-to-end run, commit, push, final report | pending |

### Phase 1 progress (started 2026-06-23)
Created `scripts/python/integration/_extract_ceba_deck_text.py` (uses `.venv` + `python-pptx`)
to dump the 57-slide deck into `ceba-review/ceba_dppa_2026_text.txt` (35,935 chars).
Reviewed the full text; identified 20+ repo-testable claims across A/B/C buckets
plus 3 known gaps (Decree 146 two-part tariff, RECs/EACs, GHG scopes).

## Environment
- PySAM 7.1.0 lives in the repo **`.venv` (Python 3.12)** — use `.venv\Scripts\python.exe` for PySAM/PVWatts
  and for the test suite. System Python 3.14 has no PySAM wheel (code falls back to a synthetic profile).
- Tests: `.\tests\run_all_tests.ps1` (PowerShell runner) or `pytest tests/python/...`.
- python-pptx 1.0.2 is also installed in `.venv` for the deck note injector.

## Known pre-existing test failures (out of scope for the trim — backlog)
- `tests/python/integration/test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`
- `tests/python/integration/test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`

Both are numeric benchmark/tolerance drift — confirmed failing before the trim work (verified at commit `5297f89`).
