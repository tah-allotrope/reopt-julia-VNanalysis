# Active Context

> **Convention:** keep this file slim — current state only (target < ~150 lines).
> Rotate finished-work history into `docs/worklog/`. Full pre-2026-06-12 log:
> [`docs/worklog/2026-06-12-activecontext-archive.md`](docs/worklog/2026-06-12-activecontext-archive.md).

## Current focus — Repo trim & restructure (started 2026-06-12)

Goal: a trimmed, restructured repo whose key function is **ReOpt + PySAM analysis of
future onsite (BTM) and offsite/DPPA clean-energy projects in Vietnam**. Driven by the
gap analysis and three sprint plans.

- **Gap analysis:** `reports/2026-06-12-reopt-pysam-vietnam-repo-trim-gap-analysis.md`
- **Sprint plans:** `plans/active/2026-06-12-sprint-{1,2,3}-*.md`
- **Per-phase workflow:** implement → `/report <phase>` → git commit → git push origin main.

### Status

| Sprint | Scope | State |
|---|---|---|
| 1 — Mechanical de-bloat | Untrack generated artifacts, remove dead/foreign dirs, golden `examples/` | ✅ complete (635 → 371 tracked files) |
| 2 — Shim removal + binaries | Remove 2 shim layers, untrack ~35MB binaries, slim this file | ✅ complete |
| 3 — Onsite/offsite pipelines | Generalize per-deal modules into `analysis/onsite.py` + `analysis/offsite_dppa.py` | ⬜ planned (not started) |

Final reports: `reports/2026-06-12-final-sprint-1-repo-trim.html` (+ Sprint 2 final to follow).

### Sprint 1 result (✅ 2026-06-12)
Tracked files 635 → 371. Generated `artifacts/`, `reports/*.html`, `present/`, `scenarios/generated/`
untracked (regenerable, kept on disk, git-ignored). Dead `archive/` dropped; `.opencode/` untracked;
`legacy/README.md` → `docs/legacy-path-map.md`. Golden runs frozen in `examples/`. One archive-deletion
test regression caught + fixed (`reopt/sanitize.py`).

### Sprint 2 result (✅ 2026-06-12)
Removed both shadow shim layers: 44 flat `scripts/python/*.py` shims deleted, **7 real scripts**
(no twin) relocated to `scripts/python/integration/`, 3 `src/` shims deleted. Untracked ~35MB
binaries (TOU PDF, FMP CSV, Saigon18 `.xlsm`) with `SOURCES.md`/`SOURCE.md` manifests. README
"Script Paths (canonical)" mapping table added. The shims were load-bearing for tests — repointed
7 tests (CLI subprocess + 6 flat-import tests) to canonical subdirs.

### Sprint 3 — next (planned)
`plans/active/2026-06-12-sprint-3-onsite-offsite-pipeline-plan.md`. Generalize the bespoke per-deal
modules (`dppa_case_1/2/3`, `dppa_samsung_ttc`, `ninhsim_solar_storage_60pct`) into reusable
`reopt_pysam_vn/analysis/{onsite,offsite_dppa}.py`, migrate Samsung-TTC behind a parity gate, make
the two modes first-class. **Has open Grill Me decisions** (parity tolerance; retire vs wrap; CLI now/later).

## Environment
- PySAM 7.1.0 lives in the repo **`.venv` (Python 3.12)** — use `.venv\Scripts\python.exe` for PySAM/PVWatts
  and for the test suite. System Python 3.14 has no PySAM wheel (code falls back to a synthetic profile).
- Tests: `.\tests\run_all_tests.ps1` (PowerShell runner) or `pytest tests/python/...`.

## Known pre-existing test failures (out of scope for the trim — backlog)
- `tests/python/integration/test_capacity_factor_benchmark.py::test_pvwatts_capacity_factor_binh_thuan`
- `tests/python/integration/test_ninhsim_cppa.py::test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`

Both are numeric benchmark/tolerance drift — confirmed failing before the trim work (verified at commit `5297f89`).
