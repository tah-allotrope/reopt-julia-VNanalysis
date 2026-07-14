---
title: "reopt-pysam: strategic-lens next-level brainstorm"
date: "2026-07-14"
type: "brainstorm"
depth: "standard"
source_request: "unattended orchestrator: analyze reopt-pysam state and brainstorm what takes it to the next level"
slug: "reopt-pysam-strategic-lens"
supersedes: none
complements: "research/2026-07-11-reopt-pysam-next-level-brainstorm.md"
---

# Brainstorm: reopt-pysam — Strategic-Lens Next-Level

> Produced **unattended**. Every decision was self-answered with the option I would
> have marked "(Recommended)" and is tagged `(auto-selected)`. No human confirmation.
>
> **Relationship to the existing roadmap.** A thorough next-level brainstorm and a
> 6-phase plan already exist from **2026-07-11** (`research/2026-07-11-*`,
> `plans/2026-07-11-*`), both still **uncommitted and unexecuted** as of today. That
> roadmap is good and I endorse its P0–P2 (security → CI → offsite generalization);
> I do **not** rehash it. This document does two things instead: (1) a fresh
> **verification pass** confirming which of its claims still hold on 2026-07-14, and
> (2) a set of **higher-altitude themes it under-weighted or omitted** — the items
> that decide whether this repo becomes a durable *product* rather than a widening
> pile of bespoke analysis scripts. Grounding: direct repo inspection today (git
> history, source tree, `jobs.py`, `pyproject.toml`, `docs/`, script census) plus the
> README, AGENTS.md, activeContext.md, lessons.md, and both prior brainstorms.

---

## 1. Verification refresh — what is still true on 2026-07-14

Re-checked the 2026-07-11 brainstorm's load-bearing claims against the live repo:

| Claim (2026-07-11) | Status today | Evidence |
|---|---|---|
| No CI | **Still true** | no `.github/workflows/` directory exists |
| ruff used but unconfigured | **Still true** | `grep tool.ruff pyproject.toml` → 0 hits; `.ruff_cache/` present |
| Leaked NREL key in history | **Confirmed present** | commits `3911032`, `b14bc0b` exist; `NREL_API.env` no longer tracked (only `.example`) — key value is recoverable from history, rotation still the fix |
| Ignored-but-tracked binaries | **Still true** | `git ls-files` shows both `ceba-review/*.pptx`; `Regina.xlsx` correctly still tracked (live test input) |
| Stray root screenshots + uncommitted plans | **Still true** | `phase04_new_deal_*.png` + 6 untracked plan/research files in `git status` |
| `requirements.txt` drift from `pyproject.toml` | **Still true** | separate dep lists |
| Offsite path single-tenant (Samsung only) | **Confirmed** | `jobs.py:65` hard-blocks non-onsite live solves; offsite needs a pre-solved `extracted` upload |
| 5 red benchmark tests, no owner | **Assumed still true** | not re-run this pass (network/venv cost); no commits since 2026-07-06 touched them |

**Bottom line:** nothing in the 2026-07-11 foundation diagnosis has been fixed. The
last 4 commits (through 2026-07-06) shipped the map site picker; the next-level plan
was written and shelved. So P0–P2 of that plan remain the correct *first* moves and
I will not re-argue them. What follows is what that plan did **not** frame.

---

## 2. What the existing roadmap under-weighted (the value-add)

The 2026-07-11 plan is a debt-paydown-then-two-features plan. It treats the
architecture as basically sound and the destination as "the same toolkit, hardened."
The strategic question the orchestrator actually asked — *what takes it to the next
level* — surfaces four things that plan either scoped out or touched only glancingly.
Each is a genuine fork in the road, not a chore.

### Theme A — Script sprawl is the *real* architecture problem (bigger than the Samsung monolith)

The prior plan fixated on `dppa_samsung_ttc.py` (1058 lines) as "the monolith" and
sized script debt at "~30 near-duplicate `analyze_*/build_*` scripts" (its DEC-016,
deferred). The live census is worse and more revealing:

- **119 Python scripts** under `scripts/` — **77 in `integration/` alone**, plus a
  14-file `integration/ceba_deck/` subtree.
- **72** of them match `analyze_* / build_* / run_* / generate_*` — the one-off-per-
  deliverable pattern.
- The largest *source* module is **not** Samsung — it is **`dppa_case_2.py` at 1481
  lines** (Samsung is 1058; `dppa_case_3.py` is 593). The plan's parity-gated
  extraction targets Samsung; the biggest bespoke blob is a different, ungated file.

The pattern underneath both the module monoliths and the script pile is the same:
**every new deal or deck spawns a new hand-written file** instead of a new *config +
a shared engine run*. That is why offsite is single-tenant, why there are 119
scripts, and why `dppa_case_2` ballooned. The 2026-07-11 "registry expansion" (its
DEC-008) treats a symptom (one registry slot) without naming the disease (no
declarative deal/deliverable pipeline). **Next level = a config-driven case runner +
a reporting pipeline, so a new deal is a JSON descriptor and a `python -m ... report`
call, not a new module and a new script.** This is a superset of the plan's DEC-008
and DEC-016 and reframes them as one initiative rather than two deferred chores.

### Theme B — The Julia half is stagnant dead-weight; make an explicit keep/archive call

README and AGENTS.md present Julia + REopt.jl v0.56.4 as the tech-stack headline
("Julia-based techno-economic optimization"). Reality on the ground:

- `src/julia/` and `scripts/julia/` were **last touched 2026-05-19** — ~2 months
  stale while Python changes weekly.
- The live solve path is the **NREL REopt web API** (`developer.nlr.gov`) via
  `reopt/preprocess.py` + `webapp/service.py`; the web app never invokes Julia.
- The 2026-07-11 plan explicitly puts "local Julia solve path" and "Julia-side CI"
  **out of scope** — i.e. it quietly concedes Julia is not part of the future but
  never says so, leaving the README selling a stack the product no longer uses.

This is a strategic fork the prior roadmap ducked. Two honest options: **(B1)**
formally maintain Julia (pin, CI-smoke, keep as the offline/no-API solve engine), or
**(B2)** formally **archive** it — move `src/julia`, `scripts/julia`, `Project.toml`,
`Manifest.toml` under `legacy/julia/`, rewrite the README stack section to "NREL
REopt API (primary) + PySAM finance; Julia REopt.jl retained for offline solves in
`legacy/`," and stop implying it is load-bearing. Either is fine; **the debt is the
ambiguity.** A newcomer today cannot tell whether Julia is core or cruft. *(auto-
selected: B2 — archive-in-place, because the API path won and nothing calls Julia;
keep the code, drop the pretense. See DEC-104.)*

### Theme C — Operational readiness of the web app (it is now the primary UI, but has no operator story)

The web app is the thing non-technical colleagues touch, yet it has none of the
production hygiene a background-job service needs:

- **Logging is inconsistent** — `jobs.py` logs properly, but only **1 module** in the
  whole package imports `logging`; there are **14 bare `print()`** calls in library
  code. No structured run log, no per-solve provenance record (which key, which
  resource vintage, cache hit/miss, wall-time).
- **Errors reach the user as a raw `str(exc)`** (`jobs.py:61`, `jobs.py:72`) — fine
  for a dev, opaque for an analyst. No error taxonomy, no "what to do next."
- **No run audit trail / retention policy** — the filesystem run store grows
  unbounded; there is no "these are stale, prune them" and no record of *who* ran
  *what* (single-user today, but Q-001 LAN exposure changes that overnight).
- **No health/readiness beyond `/api/health`** — no visibility into queue depth or
  whether the worker thread died.

The 2026-07-11 plan hardens *inputs* (its DEC-011 allowlist) and fixes the *run-ID
counter* (its DEC-010) — both real — but says nothing about **observability or
operator ergonomics**. For a tool that just became someone's daily UI, a structured
run-log + surfaced solve provenance + a friendly error layer is a bigger day-2 win
than a second offsite orchestrator.

### Theme D — Typing and public-API discipline (the cheap multiplier CI should carry)

Signatures across the package are already richly type-hinted (`-> dict`,
`Optional[...]`, dataclasses everywhere), but:

- **No `mypy`, no `py.typed`, no typing gate** — the hints are decoration, not
  enforced contracts. A refactor can silently break a type invariant and only a
  numeric test (maybe) catches it.
- **No declared public API surface.** `analysis/` is "the front door" by convention
  and docstring, but nothing marks what is stable vs internal; the 119 scripts and
  the webapp reach into `integration/` internals freely (that is *how* forking
  happens).

The prior plan adds ruff (lint) to CI but stops short of a type gate. Adding `mypy
--strict`-ish on `analysis/` + `webapp/` (the surfaces that must stay stable), a
`py.typed` marker, and a documented "public = `analysis`, everything else internal"
rule is a small, high-leverage complement to its DEC-005 CI — and it directly defends
CON-002 (no forking analytics into the webapp) mechanically instead of by discipline.

---

## 3. Secondary observations (smaller, still real)

- **Determinism / offline mode.** A config-hash solve cache already exists
  (`webapp/jobs.py` + `service.solve_relevant_hash`). One step further — a **frozen
  golden resource + offline solve mode** — would let CI, demos, and colleagues run
  the *full* pipeline (including onsite) with **no NREL key and no network**, closing
  the plan's ASM-003/CON-003 anxiety and making the tool demoable on a plane. This is
  also the natural home for an archived-but-retained Julia solver (Theme B1).
- **Performance of 8760-hour settlement.** `settlement.py` (307 lines) and the strike
  sweeps run hourly loops in Python; `numpy`/`pandas` are already dependencies. If a
  strike sweep × regime stress × adder sensitivity grid is being recomputed per run,
  vectorizing the settlement kernel is a straightforward latency win for the
  interactive web app (and the deferred strike-sweep chart, plan PHASE-05). Measure
  before optimizing — but nobody has measured.
- **Policy data as a living layer.** `data/vietnam/` is well-structured (`_meta`
  envelope, manifest, versioned files) and already carries `vn_regime_registry_2026`,
  `vn_deal_defaults_2026`. Decree 243 (plan PHASE-06) is one instance of a recurring
  need: a **changelog / "as-of date" surface** so a run records *which policy vintage*
  it used. Provenance again (ties to Theme C).
- **Docs are strong on internals, thin on the domain.** `docs/` has 14 files
  (architecture, pitfalls, reopt_internals, pysam, onsite_vs_offsite) — genuinely
  good engineering docs. What is missing is a **DPPA domain data dictionary**: what a
  `DealConfig` field *means* in deal terms, unit conventions (the VND/kWh vs
  cents/kWh trap the plan flags in Gotchas), and a glossary an analyst — not an
  engineer — can read. This is the onboarding gap if the app gets real users.
- **`common/` is underused.** There is a `common/{currency,time_series,validation}.py`
  layer — exactly where a vectorized settlement kernel and the unit-conversion
  discipline should live, rather than being re-implemented per case module.

---

## 4. Resolved decisions (self-answered)

- **DEC-101:** Scope = a **complementary strategic overlay** on the 2026-07-11 plan,
  not a replacement. That plan's P0–P2 (security, CI, hygiene, offsite generalization)
  execute as written and **first**; the themes here re-order and extend what comes
  after. *(auto-selected)*
- **DEC-102:** Reframe the prior plan's DEC-008 (registry expansion) + DEC-016 (script
  debloat) as **one initiative: a config-driven case runner + reporting pipeline**
  (Theme A). A new deal becomes a descriptor + a generic run; bespoke modules and
  one-off scripts collapse into thin config. Still parity-gated: Samsung stays
  bit-exact at every step (CON-001). *(auto-selected)*
- **DEC-103:** Target **`dppa_case_2.py` (1481 lines)** as the first monolith to
  decompose into the config runner — it is larger than Samsung and, unlike Samsung,
  is **not** bit-exact-gated, so it is lower-risk to refactor and a better proving
  ground for the generic path than the golden case. *(auto-selected)*
- **DEC-104:** **Archive Julia in place** (Theme B, option B2): relocate `src/julia`,
  `scripts/julia`, `Project.toml`, `Manifest.toml` under `legacy/julia/`, rewrite the
  README/AGENTS stack sections to name the NREL API as the primary solver, and keep
  the code as the optional offline engine. Reversible; removes the "is Julia core?"
  ambiguity. *(auto-selected — but flagged as the highest-judgment call here; a human
  who still solves locally in Julia should veto. See Q-101.)*
- **DEC-105:** Add an **operational-readiness slice** to the web app (Theme C):
  structured run logging, a per-run `provenance.json` (key id hash, resource vintage,
  cache hit/miss, wall-time, policy-data version), a friendly error layer mapping
  exceptions to analyst-readable messages, and a run-retention/prune command. Slots
  **after** the prior plan's PHASE-03 hardening. *(auto-selected)*
- **DEC-106:** Add a **type gate** (Theme D) to CI alongside ruff: `mypy` on
  `analysis/` + `webapp/` (stable surfaces), a `py.typed` marker, and a one-paragraph
  "public API = `analysis`; the rest is internal" rule in AGENTS.md. Extends the prior
  plan's DEC-005 rather than replacing it. *(auto-selected)*
- **DEC-107:** Add a **frozen-resource offline solve mode** so the full pipeline runs
  with no key/network (secondary observation §3). Lands naturally as a CI capability
  and a demo affordance; also the home for a retained Julia offline solve.
  *(auto-selected)*
- **DEC-108:** **Do not** vectorize settlement speculatively — **measure first**. Add
  a `--profile` or a micro-benchmark to time a full offsite run; optimize the hot loop
  only if the interactive path is visibly slow. *(auto-selected — avoids the CLAUDE.md
  "no speculative improvement" anti-pattern.)*

## 5. Assumptions & constraints

- **ASM-101:** The 2026-07-11 plan will be executed roughly as written for its P0–P2;
  this overlay assumes CI + parity gates are in place before the Theme-A refactor
  starts. If that plan is abandoned, DEC-101's ordering must be re-derived.
- **ASM-102:** Nobody is actively developing on the Julia path (last commit
  2026-05-19); archiving it (DEC-104) breaks no active workflow. **Verify with the
  human before moving** (Q-101).
- **ASM-103:** `dppa_case_2` has test coverage sufficient to catch a decomposition
  regression; if it does not, characterization tests come **before** the refactor
  (per lessons.md 2026-06-12: run the FULL suite after any structural move).
- **CON-101:** Samsung/TTC bit-exact parity is inviolable (`test_samsung_ttc_parity`,
  `test_golden_parity`) — every Theme-A step keeps it green (same standing constraint
  as the prior plan's CON-001).
- **CON-102:** No forking analytics into the webapp (standing CON-002). Theme D's type
  gate is proposed partly to *enforce* this mechanically.
- **CON-103:** Windows-first repo (PowerShell runner, `utf-8-sig` reads, `.venv` Py
  3.12). New tooling (mypy, offline mode) must not assume POSIX.

## 6. Approaches considered

- **Chosen:** Overlay strategy — execute the existing debt-paydown plan, then layer
  the four strategic themes (config runner, Julia decision, ops readiness, type gate)
  on the hardened base.
- **ALT-101:** Ignore the existing plan and write a fresh full roadmap — rejected: the
  2026-07-11 diagnosis is correct and still-unfixed; duplicating it wastes the reader
  and risks divergent priorities.
- **ALT-102:** Jump straight to the config-driven runner (Theme A) before CI/parity
  gates exist — rejected: lessons.md is explicit that structural moves without a full
  green suite have burned this repo; the runner refactor is exactly that kind of move.
- **ALT-103:** Delete the Julia tree outright — rejected in favor of archive-in-place
  (DEC-104): it may still be the best offline solver; keep it, just stop implying it
  is the primary engine.
- **ALT-104:** Full observability stack (metrics/tracing backend) for the web app —
  rejected as over-engineering for a single-user localhost tool; structured logs + a
  per-run provenance file are the right altitude (DEC-105).

## 7. Out of scope

- Re-litigating the 2026-07-11 plan's P0–P2 (security, CI mechanics, hygiene, offsite
  registry, Decree 243 data) — endorsed as-is.
- Multi-tenant / auth / cloud hosting / billing (still a later product path).
- Rewriting Samsung/TTC (parity-gated; the config runner *wraps*, never rewrites it).
- A metrics/tracing backend or external DB (filesystem store stands).

## 8. Open questions

1. **Q-101 (highest-judgment):** Is anyone still solving locally in Julia, or is the
   NREL API the sole path going forward?
   - **Recommended default:** Archive Julia in place (DEC-104) and name the API as
     primary; retain Julia as the optional offline engine. Reversible.
   - **Why it matters:** Flips the README's stack headline and the "keep vs maintain"
     effort question; a human who runs Julia solves must veto the archive.
2. **Q-102:** Will the web app get LAN/multi-user exposure soon? (Same as the prior
   plan's Q-001 — restated because it now also gates the **run audit trail / retention**
   scope in DEC-105, not just input hardening.)
   - **Recommended default:** Build the provenance/audit log now (cheap, useful
     single-user); defer auth until a teammate actually needs remote access.
3. **Q-103:** Is `dppa_case_2` (the 1481-line target of DEC-103) still an active deal,
   or a finished analysis safe to freeze behind characterization tests before
   refactoring into the config runner?
   - **Recommended default:** Treat as finished — write characterization tests
     capturing its current output, then decompose against them.

## 9. Suggested next step

1. **Execute the 2026-07-11 plan's PHASE-01 → PHASE-02 first** (security rotation,
   hygiene, CI + red-test paydown). Nothing here should start before CI and parity
   gates exist — lessons.md is emphatic on that.
2. Then fold this overlay in with `/plan reopt-pysam-strategic-lens`, suggested cut:
   - **S1 — Ops readiness & type gate** (DEC-105 + DEC-106 + DEC-107): structured
     logging, per-run provenance, friendly errors, `mypy`/`py.typed`, offline solve
     mode. Small, high-leverage, no analytics risk.
   - **S2 — Julia decision** (DEC-104): archive-in-place + doc rewrite, *pending
     Q-101*. One session, reversible.
   - **S3 — Config-driven case runner + reporting pipeline** (DEC-102), proving it on
     **`dppa_case_2`** (DEC-103) behind characterization tests, Samsung parity green
     throughout. This is the big one and the true "next level" — it dissolves the 119-
     script sprawl and the single-tenant offsite path into one declarative surface.
3. Measure before optimizing settlement (DEC-108) — only vectorize if the interactive
   path is demonstrably slow.

**One-line thesis:** the 2026-07-11 plan makes the current toolkit *safe and green*;
this overlay makes it *a product* — one declarative deal pipeline instead of 119
scripts, an honest tech-stack story, and a web app an operator can actually run.
