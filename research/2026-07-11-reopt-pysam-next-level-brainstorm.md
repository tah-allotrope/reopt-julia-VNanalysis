---
title: "reopt-pysam: next-level improvement roadmap"
date: "2026-07-11"
type: "brainstorm"
depth: "standard"
source_request: "autonomous mode: analyze reopt-pysam project state and brainstorm next-level improvements"
slug: "reopt-pysam-next-level"
---

# Brainstorm: reopt-pysam — Next-Level Improvement Roadmap

> Produced unattended (`--auto`): every decision below was self-answered with the
> option that would have been marked "(Recommended)". All are suffixed
> `(auto-selected)` so a reviewer can see nothing was human-confirmed.
> Grounding: one Explore subagent full-repo pass (2026-07-11) + README, AGENTS.md,
> activeContext.md, lessons.md, webapp README, and the 2026-07-04 / 2026-07-06
> brainstorms.

## Problem & Why Now

The repo has matured into **two coupled products**: (1) a Vietnam DPPA
techno-economic analysis toolkit (`reopt_pysam_vn` — REopt via NREL API/Julia +
PySAM developer finance, ~11.8k LOC, 550+ tests) and (2) a freshly shipped
internal FastAPI web app with a Leaflet site picker over it. The feature velocity
has outrun the foundation:

- **A live NREL API key sits in git history** (added in commit `3911032`, untracked
  in `b14bc0b` — rotation never happened).
- **5 numeric benchmark tests fail on `main`** and are logged as "backlog" with no
  owner; with **no CI**, they silently persist and mask new regressions.
- **The offsite/DPPA path is single-tenant**: `run_offsite_dppa` only serves the
  one registered Samsung/TTC orchestrator (a 1058-line monolith) and requires a
  pre-solved `extracted` payload; every other case (dppa_case_1/2/3, ninhsim,
  factory_a) is a bespoke module + one-off script — ~30 near-duplicate
  `analyze_*/build_*` scripts.
- Hygiene drift: ignored-but-still-tracked `.pptx`/`.xlsx` binaries, stray
  screenshots at repo root, uncommitted plan/research files, `requirements.txt`
  drifting from `pyproject.toml`, ruff used but unconfigured.

Why now: the web app makes the toolkit usable by non-technical colleagues, which
multiplies both the value of a generic offsite path and the blast radius of the
security/quality gaps. Fixing foundations before the queued phase-2 features
(strike-sweep views, regime toggles, LAN access) is the cheap ordering.

## Current vs Desired State

- **Current state:** Working end-to-end DealConfig loop (onsite live-solve via NREL
  API; offsite only via pre-solved Samsung/TTC payload), 50/50 webapp tests green,
  552/557 package tests green, all verification manual/local, no CI, no auth
  (localhost by design), filesystem run store with a restart-fragile class-level
  run counter, leaked key unrotated.
- **Desired state:** Rotated credentials; clean tree and index; CI gate (ruff +
  pytest layers 1–3 + webapp) on every push; the 5 failing benchmarks fixed or
  deliberately re-baselined; a generic offsite orchestration path with ≥2
  registered cases and a live PVWatts solve option in the web app; phase-2 web
  features unblocked.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/{analysis,integration,webapp}/`,
  `tests/python/`, `scripts/python/integration/`, `pyproject.toml`,
  `.gitignore`, `data/vietnam/`, `data/projects/`, `NREL_API.env` (history),
  `plans/active/` (unfinished streams), `research/2026-06-30_decree-243-2026-nd-cp.md`.

## Framing (Socratic stage, self-answered)

- **Who has the problem?** Allotrope deal analysts (via the web app) and the repo
  maintainer (via unowned red tests and bespoke-script sprawl).
- **What does success look like?** A colleague can model a *new* offsite DPPA deal
  through the web app without anyone writing a bespoke module; `git push` runs a
  green pipeline; no live secret exists anywhere in history that still works.
- **Approaches worth considering at all:** (a) foundation-first debt paydown then
  features; (b) feature-first (phase-2 web app) accepting the debt; (c) big-bang
  rewrite of the integration layer. (a) chosen — see DEC-002; (c) rejected
  outright given bit-exact parity gates and `lessons.md` history.

## Resolved Decisions

- **DEC-001:** Scope = a prioritized whole-project roadmap (P0–P4 below), not one
  feature — the orchestrator asked "what takes it to the next level", and the
  highest-leverage items span security, CI, and architecture. *(auto-selected)*
- **DEC-002:** Order of work: **P0 security/hygiene → P1 CI + red tests → P2
  offsite generalization → P3 web app phase-2 features → P4 Decree 243 data
  refresh.** Foundation before features; each tier unblocks the next.
  *(auto-selected)*
- **DEC-003:** For the leaked NREL key: **rotate the key** (free, instant at
  developer.nlr.gov) and leave history unrewritten — history-scrubbing
  (filter-repo) breaks clones/worktrees for marginal benefit once the key is
  dead. Also add a pre-commit secret scan (gitleaks) to prevent recurrence.
  *(auto-selected)*
- **DEC-004:** Untrack the ignored-but-tracked binaries (`ceba-review/*.pptx`,
  `scenarios/case_studies/regina/Regina.xlsx`) via `git rm --cached`; delete the
  stray root screenshots (`phase04_new_deal_*.png`); commit the outstanding
  plan/research files. Consolidate the 6+ dated `.gitignore` sprint sections into
  a few stable rules, honoring the `lessons.md` warning about loose negations.
  *(auto-selected)*
- **DEC-005:** CI = **GitHub Actions** (repo already has git + gh conventions):
  `ruff check` + `pytest tests/python` (layers 1–3 + webapp, NREL mocked) on
  ubuntu, Python 3.12. **Julia stays local-only** (3–8 min cold starts, solver
  runs — poor CI economics); keep `run_all_tests.ps1` as the full local gate.
  *(auto-selected)*
- **DEC-006:** The 5 failing numeric tests get a dedicated fix pass using the
  `lessons.md` protocol: exploratory diff against goldens FIRST, then either fix
  the root cause (if drift is a real regression, bisect with `git worktree`) or
  re-baseline with a documented tolerance rationale. **Never delete or blind-skip
  them.** *(auto-selected)*
- **DEC-007:** Single dependency source: `pyproject.toml`. Reduce
  `requirements.txt` to a one-line `-e .[webapp]` pointer (kept for muscle-memory
  compatibility) rather than deleting it. Add `[tool.ruff]` config to pyproject
  so the already-in-use linter has pinned rules. *(auto-selected)*
- **DEC-008:** Offsite generalization = **registry expansion, not rewrite**:
  extract the reusable pipeline from `dppa_samsung_ttc.py` (1058 lines) into
  composable steps built on the existing `integration/settlement.py`,
  `strike_search.py`, `matching.py`; register dppa_case_1/2/3 + ninsim as
  orchestrators behind `_ORCHESTRATORS`. Stage the code-move exactly as
  `lessons.md` 2026-06-14 prescribes (no circular delegation, docstring
  deprecation, parity tests bit-exact green at every step). *(auto-selected)*
- **DEC-009:** Add a **live offsite solve path**: PVWatts/PySAM already runs
  locally in `.venv`, so the web app's "offsite needs a pre-solved `extracted`
  payload" constraint can drop for the common case — generate the profile
  in-process in the existing background job worker. Pre-solved upload stays as
  the power-user path. *(auto-selected)*
- **DEC-010:** Keep the **filesystem run store, no database** — single-user
  localhost design (DEC-015/022 of the 2026-07-04 brainstorm) still holds. Fix
  the fragile bit only: replace the class-level `RunStorage._counter` with
  timestamp-sortable IDs (e.g. `YYYYMMDDHHMMSS-<short-hash>`), which also
  survives restarts and parallel instances. *(auto-selected)*
- **DEC-011:** Close the web-app mass-assignment surface: `_nest_form_fields`
  builds nested dicts from arbitrary dotted keys with blind `float()` coercion —
  validate against an explicit allowlist derived from the `DealConfig` dataclass
  fields, rejecting unknown keys. Cheap now, mandatory before any LAN exposure.
  *(auto-selected)*
- **DEC-012:** Web app phase-2 feature order (from the prior brainstorms' deferred
  lists): **(1) strike-sweep interactive view** (highest analyst value; engine
  exists in `strike_search.py`), **(2) click-a-catalog-marker-to-prefill-deal**
  (small; catalog + map already wired), **(3) regime/TOU scenario toggle**
  (regime engine exists in `reopt/regime_runner.py`). LAN binding + shared-secret
  auth only when a teammate actually asks (Q-001 below) — and only after DEC-011.
  *(auto-selected)*
- **DEC-013:** JS/map testing: extract the pure logic in `map.js` (latitude-band
  region derivation, coord round-tripping) into functions unit-testable without a
  browser, and add one **opt-in** Playwright smoke test (marked, excluded from CI
  default) — full browser automation already proved flaky here (PHASE-04
  abandoned it), so don't gate on it. *(auto-selected)*
- **DEC-014:** Decree 243/2026-ND-CP integration is its own follow-on plan: the
  research brief (`research/2026-06-30_decree-243-2026-nd-cp.md`) exists but no
  versioned data file or regime-registry entry does. Follow the established
  pattern: new versioned file in `data/vietnam/` + one-line `manifest.json`
  change + regime registry update. *(auto-selected)*
- **DEC-015:** Add a root `CLAUDE.md` that points at `AGENTS.md` (the de-facto
  project law file) — the user's global instructions say "read CLAUDE.md first",
  and today's file is named such that fresh agent sessions miss it.
  *(auto-selected)*
- **DEC-016:** Script debloat is P2-adjacent, not urgent: as cases migrate into
  the orchestrator registry (DEC-008), convert their `analyze_*/build_*` scripts
  into thin wrappers over `python -m reopt_pysam_vn.analysis` rather than
  attacking all ~30 scripts up front — the 2026-06-12 shim-removal lessons say
  structural moves must be small and full-suite-verified. *(auto-selected)*

## Assumptions & Constraints

- **ASM-001:** The NREL key found in history is still valid and rotation is
  possible via the NREL developer portal without disrupting stored runs (keys are
  read from env/`NREL_API.env` at solve time).
- **ASM-002:** GitHub Actions is available for this repo (a `gh`/GitHub remote is
  the working convention). If the repo is purely local, substitute a pre-commit
  hook running the same gate.
- **ASM-003:** The 5 red tests are tolerance/benchmark drift as `activeContext.md`
  records, not silent numeric regressions — the fix pass (DEC-006) verifies this
  before re-baselining.
- **ASM-004:** Filename convention: the orchestrator's requested
  `research/<date>-<slug>-brainstorm.md` (all-dash) pattern is used for this file
  even though prior briefs use `YYYY-MM-DD_slug` (underscore) — orchestrator
  contract wins for the DONE line to match.
- **CON-001:** Samsung/TTC parity is **bit-exact gated** (`test_golden_parity.py`,
  `test_samsung_ttc_parity.py`); any DEC-008 refactor must keep those green at
  every intermediate commit.
- **CON-002:** No forking of analytics logic into the webapp (standing constraint
  from the 2026-07-04 plan); the app stays a thin layer over
  `reopt_pysam_vn.analysis`.
- **CON-003:** PySAM only exists in the repo `.venv` (Py 3.12); CI must either
  install `nrel-pysam` from PyPI or rely on the existing skip-when-unavailable
  behavior.
- **CON-004:** Web app stays localhost/no-auth until DEC-011 + an explicit
  LAN decision (Q-001).

## Approaches Considered

- **Chosen:** Foundation-first debt paydown (security → CI → offsite
  generalization) followed by the already-scoped phase-2 web features — each tier
  de-risks the next, and every architectural move is parity-gated per repo lessons.
- **ALT-001:** Feature-first (jump straight to strike-sweep UI and regime toggles)
  — rejected: builds more surface on an unowned-red test suite and an unrotated
  leaked credential.
- **ALT-002:** Big-bang rewrite of `integration/` into a clean orchestrator
  framework — rejected: `lessons.md` documents exactly this failure mode; the
  registry + staged-extraction path preserves bit-exact parity.
- **ALT-003:** Introduce SQLite for run storage while touching `RunStorage` —
  rejected: single-user filesystem design is deliberate and adequate; ID scheme
  fix is 20 lines, a DB migration is a project.
- **ALT-004:** Git history rewrite (filter-repo) to purge the key — rejected in
  favor of rotation + gitleaks (DEC-003); rewriting invalidates the stale
  worktree and any clones for no security gain once the key is dead.
- **ALT-005:** Full Playwright E2E suite for the map — rejected: already attempted
  and abandoned (server hung on tile loads); opt-in smoke + extracted pure
  functions gives most of the value at none of the flake.

## Out of Scope

- Multi-tenant SaaS features (auth beyond a shared secret, billing, cloud
  hosting) — the Apr-26 "Deal Screener product" path remains later.
- Local Julia solve path from the web app.
- QGIS/layered GIS overlays, offline tiles (per 2026-07-06 brainstorm).
- Editing versioned `data/vietnam/` policy files from the UI.
- PPTX/deck generation from the app.
- Julia-side CI.

## Open Questions

1. **Q-001:** Will teammates need the web app from their own machines soon
   (LAN binding + shared-secret auth)?
   - **Recommended default:** Stay localhost-only; implement DEC-011 (input
     allowlist) now so LAN exposure is a config change, not a security project.
   - **Why this matters:** Flips the no-auth design decision and adds concurrency
     requirements to the single-worker job queue.
2. **Q-002:** Should the `ceba-review/*.pptx` decks (currently tracked despite
   ignore rules, plus one untracked `[repo-checked]` variant) be versioned
   deliverables or local-only?
   - **Recommended default:** Local-only — `git rm --cached`, keep on disk,
     consistent with the 2026-06-12 de-bloat policy (binaries regenerable or
     external).
   - **Why this matters:** Determines whether DEC-004 untracks or formalizes them;
     they are the largest tracked binaries.
3. **Q-003:** When rotating the NREL key, is the same key used elsewhere
   (other repos, notebooks, Colab) that would break?
   - **Recommended default:** Rotate anyway and update `NREL_API.env` everywhere
     it's used; the key is already exposed.
   - **Why this matters:** Coordinated rotation avoids surprise 403s in other
     workflows.

## Suggested Next Step

Run `/plan reopt-pysam-next-level` to turn this into a multi-phase implementation
plan. Suggested phase cut: **P0** DEC-003/004/007/015 (hygiene, one session),
**P1** DEC-005/006 (CI + red tests), **P2** DEC-008/009/010/011/016 (offsite
generalization + webapp hardening), **P3** DEC-012/013 (phase-2 features),
**P4** DEC-014 (Decree 243 data refresh).
