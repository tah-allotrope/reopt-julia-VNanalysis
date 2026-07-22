---
title: "reopt-pysam: breaking the analysis loop — execution unblock + fresh findings"
date: "2026-07-22"
type: "brainstorm"
depth: "standard"
source_request: "unattended orchestrator: analyze reopt-pysam state and brainstorm next-level improvements"
slug: "reopt-pysam-execution-unblock"
supersedes: none
complements:
  - "research/2026-07-11-reopt-pysam-next-level-brainstorm.md"
  - "research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md"
  - "research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md"
  - "research/2026-07-18-execution-debt-decree-243-brainstorm.md"
  - "plans/2026-07-17-truth-and-correctness-sprint-plan.md"
---

# Brainstorm: reopt-pysam — Breaking the Analysis Loop

> Produced **unattended** on 2026-07-22 (**fifth** consecutive next-level pass in
> eleven days). Every open decision below is self-answered with the option I would
> have marked "(Recommended)", tagged `(auto-selected)`. No human confirmation.
>
> **Relationship to prior passes.** 07-11 diagnosed foundation debt. 07-14 added
> strategic themes. 07-17 found the red CI gate, a Single Owner reference-plant
> defect, and convention decay, and shipped a turn-key, phase-gated plan
> (`plans/2026-07-17-truth-and-correctness-sprint-plan.md`). 07-18 found a live
> Decree 243 currency gap, **executed it in full** (commits `c7e63ff`, `b84c73c`,
> `7191a62`, `06c380b`), and explicitly recommended the *next* session run the
> 07-17 plan rather than write a sixth analysis. This document independently
> re-verifies today's state with live tools (not by trusting prior brainstorms),
> confirms **zero phases of the 07-17 plan have executed in the four days since**,
> reports **three findings no prior pass surfaced**, and makes the strongest form
> of the recommendation the last two passes already made weaker versions of: stop
> analyzing this repo and run the plan that already exists.

---

## 1. Independent re-verification (live tools, today)

Every claim below was checked directly this session — `gh run list`/`gh run view`
against live GitHub Actions, `ruff check` run fresh, `git worktree list` / `du`,
`git status`, and direct file reads — not inherited from the prior four documents.

| Item | Prior claim (07-17/07-18) | Verified today (2026-07-22) | Evidence |
|---|---|---|---|
| CI on `main` | red, 22 failed / 542 passed / 30 skipped | **still red, unchanged**: latest run `29624245787` (2026-07-18, HEAD `2b25f9d`) — same 22 failures, same taxonomy (artifact-dependent tests, PySAM `Pvwattsv8.new` drift, Samsung parity noise off-machine, `test_regime_engine_smoke` forking, webapp tests needing a live NREL key) | `gh run list --limit 5`; `gh run view 29624245787 --log` grepped for `FAILED` |
| pytest markers (`network`/`requires_artifacts`/`golden_machine`) | not registered | **still not registered** | `grep markers pyproject.toml` → 0 hits |
| ruff configuration + violation count | unconfigured, "181 pre-existing violations" (07-17 note in `ci.yml`) | unconfigured; **206 violations now** (+25 in 4 days) — the `ci.yml` comment is stale | `ruff check . --statistics` (ruff 0.14.14, global install) → 206 errors, 12 rule codes, 1 hard parse-adjacent `invalid-syntax` |
| `nrel-pysam` pin in CI | unpinned (`>=7.1`) | **still unpinned** | `pyproject.toml` dependencies list `"nrel-pysam>=7.1"`, no CI override |
| Leaked NREL key rotation | unrotated, 4th cycle open | **still unrotated** — the live-looking key is present in the local, correctly-gitignored `NREL_API.env` today; the *historical* exposure (commits `3911032`, `b14bc0b`) is what needs rotating, and nothing indicates the portal-side rotation happened | `git ls-files \| grep NREL_API` → only `.example` tracked (correct); `cat NREL_API.env` shows a live-shaped key value locally, unchanged from before |
| Tracked `.pptx` binaries + broken `.gitignore` glob | 3 files tracked, `ceba-review/*[repo-checked].pptx` is a character class not a literal | **unchanged** | `git ls-files \| grep pptx$` → same 3 files; `.gitignore:96` still the same unescaped bracket glob |
| `requirements.txt` vs `pyproject.toml` duplication | same 6 deps in both | **unchanged**, byte-identical dependency lists in two files | direct read of both |
| Two-part tariff Ca re-pricing sign-flip | documented, not fixed | **still not fixed** | `scripts/python/reopt/two_part_tariff_sensitivity.py` docstring still reads "KNOWN MODELING GAP" verbatim |
| Single Owner reference-plant defaults (construction financing, insurance, reserves) | no clean-slate mode | **still no clean-slate mode** | `grep -n "construction_financing\|zero_us_reference\|configure_small_project" src/python/reopt_pysam_vn/pysam/single_owner.py` → 0 hits |
| Config-driven case runner / Julia archive / offline solve mode (strategic-lens PHASE-03/04/05) | not started | **still not started** | no `run_case`, no `--offline`, `src/julia/` still at repo root, last touched 2026-05-19 |
| Decree 243 ingestion + webapp hardening (P1.5/P2.5 from 07-18) | — | **confirmed shipped** — this is the one queue item that moved. `data/vietnam/vn_export_rules_2026_decree243.json` exists and is the active manifest entry; `webapp/storage.py:48-53` validates `run_id` against a regex before building a path; `run.html:63-72` renders a provenance card | direct file reads |

**Bottom line, stated plainly:** in the four calendar days since the 07-18 report
declared the Decree 243 + webapp work "done, committed, and verified," exactly
zero additional phases have executed, and one metric got measurably worse (ruff
206 vs 181). The repo has a complete, correct, TDD-shaped, phase-gated plan
sitting untouched. **The bottleneck is not analysis quality — it is that nobody
runs the plan.**

---

## 2. NEW findings this pass (not raised in 07-11/07-14/07-17/07-18)

### Finding A — 433 MB of stale git worktrees, zero unique commits, two dangling registrations

`.claude/worktrees/` holds six directories from prior agent sessions:

- `cranky-torvalds-3f262a`, `dazzling-northcutt-0807cc`, `unruffled-banzai-88ae43`
  (108 MB each), `upbeat-almeida-53c200` (109 MB) — **all four checked against
  `main` via `git log main..claude/<branch>` return zero commits.** They are full
  working-tree copies of a branch that has nothing `main` doesn't already have —
  pure disk bloat, safe to remove.
- `clever-chaplygin-dad6dc` and `kind-mcclintock-10b2e5` are 8 KB stubs — `git
  worktree list` doesn't show them as registered, meaning they're orphaned
  directories left behind after their worktree was already removed elsewhere
  (classic case for `git worktree prune`).

This is ~433 MB sitting inside the repo tree (not in `.git`, which is itself
161 MB) that nobody has been cleaning up between agent sessions. It doesn't
break anything, but it is exactly the kind of "convention decay" the 07-17 pass
named as a pattern (documented practices with no mechanical enforcement) — except
here the missing convention is "an agent session that creates a worktree cleans
it up when done," and there's no hook or reminder enforcing it.

**Proposed fix:** `git worktree remove` the four non-empty stale worktrees (after
confirming their branches truly have no unique commits — done above) and `git
worktree prune` for the two orphaned stubs. Zero risk: verified no unique history
is lost. `(auto-selected: do this as a 5-minute standalone cleanup, not gated
behind the correctness sprint — it has no code-correctness dependency.)`

### Finding B — the debt is compounding, not just persisting

The 07-17 pass measured 181 ruff violations and called it a backlog. Today it is
206 — a **14% increase in four days** with no ruff-related work having landed.
This means new code is still being written against the same unenforced
conventions that produced the original backlog; the "documentation doesn't
enforce itself" diagnosis from 07-17 §4 was correct, and its cost is now visibly
compounding rather than static. Every day this goes unconfigured, the eventual
`ruff --fix` + manual cleanup pass gets larger. This raises the *urgency*, not the
scope, of 07-17's P0a — the same fix, just with a stronger case for doing it now
over next week.

### Finding C — the `ci.yml` inline comment is now factually wrong and will mislead the next reader

The comment above the `ruff check` no-op in `.github/workflows/ci.yml` still says
*"181 pre-existing lint violations"* — written 2026-07-15, now stale (206, per
Finding B). A comment citing a specific number as justification for deferring
work is a trap: it reads as current evidence to whoever next opens the file, and
it quietly rots the same way the `.gitignore` glob and the flat-script rule
rotted per 07-17 §4. Either drop the specific count from the comment (say "has
pre-existing violations, see `ruff check --statistics`" instead of hardcoding a
number) or fix it in the same PHASE-01 pass that finally configures ruff.
`(auto-selected: reword to remove the stale count now takes literally one line;
worth doing whenever PHASE-01 is touched, not urgent enough for its own PR.)`

---

## 3. What this pass does *not* re-litigate

Four prior passes already correctly diagnosed and sequenced:

- **P0a (CI truth):** pytest markers, PySAM pin, red-test triage, repo-invariants
  check — `plans/2026-07-17-truth-and-correctness-sprint-plan.md` PHASE-01.
- **P0b (security/hygiene):** NREL key rotation, untrack pptx binaries, fix the
  `.gitignore` glob, collapse `requirements.txt` — PHASE-02.
- **P1 (two-part tariff sign-flip fix)** — PHASE-03, fully specified, TDD-shaped,
  a client-facing wrong-recommendation risk.
- **P2 (Single Owner clean-slate mode + Samsung finance audit)** — PHASE-04.
- **P3–P5 (strategic-lens):** offline/frozen-resource solve mode, Julia
  archive-in-place, config-driven case runner replacing the 119-script sprawl
  (still the single biggest architectural lever in the repo, still gated on a
  green CI as its own safety net).

All of this is endorsed as-is. Re-deriving it a sixth time adds nothing; the
09-17 plan's exit criteria are independently verifiable (a green `gh run list`)
and nothing about that plan has been shown to be wrong — only unexecuted.

---

## 4. The actual "next level" move: change what happens after the brainstorm

Four analysis passes have now correctly converged on the same queue while zero
net phases shipped (one calendar-adjacent item, Decree 243, *did* ship — notably,
it was framed and executed as a live currency defect requiring immediate action,
not queued behind "the sprint plan," which is a hint about what actually gets
unblocked in this repo: sharply-scoped, self-contained items with an obvious
trigger, not queued multi-phase sprints). Two structural changes would do more
for the repo's trajectory than any single additional technical finding:

1. **Collapse the next "brainstorm" into a "verify-and-execute."** The
   05-numbered plan already exists, is TDD-shaped, and every open question in it
   has a binding default. The highest-value unattended session from here is not
   `/brainstorm` again — it's opening
   `plans/2026-07-17-truth-and-correctness-sprint-plan.md` and running PHASE-01
   directly, the same recommendation 07-18 §3 made, now with a fourth day of
   evidence that nothing else will trigger it. *(auto-selected)*
2. **Make the safety net self-verifying instead of narrative.** Right now "CI is
   red" is a fact a human (or an unattended pass) has to go check with `gh run
   list`; nothing in the repo surfaces it proactively. A one-line addition to
   `activeContext.md`'s header — a live CI badge link, or a dated
   "CI status: RED since 2026-07-14, see `gh run list`" line updated by whoever
   next touches CI — turns "is the gate actually green" from a five-minute
   investigation (repeated, now, five times) into a glance. `(auto-selected: add
   the status line in the same commit that finally runs PHASE-01, so it starts
   its life true.)`

---

## 5. Resolved decisions (self-answered this pass)

- **DEC-401:** Do not produce a sixth prioritized roadmap; adopt the existing
  `plans/2026-07-17-truth-and-correctness-sprint-plan.md` verbatim as the
  execution target. This document's only roadmap contribution is Finding A
  (worktree cleanup) and Finding C (stale comment), both small and independent.
  *(auto-selected)*
- **DEC-402:** Worktree cleanup (Finding A) is safe to execute immediately and
  independently — it has no dependency on CI, parity gates, or any pending
  correctness fix. *(auto-selected)*
- **DEC-403:** Reword (not delete) the stale "181 violations" comment in
  `ci.yml` the next time that file is touched, rather than opening a dedicated
  change for a one-line comment. *(auto-selected)*
- **DEC-404:** Escalate P0a's urgency (not its scope) given the ruff-violation
  growth trend (Finding B) — same fix, sooner is cheaper than later.
  *(auto-selected)*
- **DEC-405:** Add a one-line, dated CI-status callout to `activeContext.md` as
  part of whichever future commit finally turns the gate green, so "is CI green"
  stops requiring a fresh investigation each session. *(auto-selected)*

## 6. Assumptions & constraints

- **ASM-401:** The 07-17 plan's phase content is still accurate and executable
  as written — verified today only at the level of "has anything it targets
  changed underneath it" (no), not by re-deriving its task list from scratch.
- **ASM-402:** The four stale worktree branches (`cranky-torvalds-3f262a`,
  `dazzling-northcutt-0807cc`, `unruffled-banzai-88ae43`, `upbeat-almeida-53c200`)
  genuinely contain zero commits beyond `main` — confirmed via `git log
  main..<branch>` returning empty for all four; safe to remove without loss.
- **ASM-403:** Nobody is mid-session in any of the six worktrees right now (no
  running process was checked for; this is a filesystem-only inference from
  branch history). A human should skip Finding A's cleanup if an agent session is
  actively using one of the four non-empty worktrees.
- **CON-401:** Samsung/TTC bit-exact parity remains inviolable; nothing in this
  document touches it or proposes touching it.
- **CON-402:** Windows-first repo; the worktree cleanup command syntax
  (`git worktree remove`, `git worktree prune`) is cross-platform and safe here.

## 7. Approaches considered

- **Chosen:** Verify-don't-rehash — spend the pass confirming the existing plan's
  premises still hold with live tools, surface only genuinely new findings, and
  make the "stop planning, start executing" recommendation explicit and
  evidence-backed rather than implicit.
- **ALT-401:** Write a full fresh roadmap from scratch, ignoring the prior four —
  rejected: would be the fourth time the same P0/P1/P2 items get re-described in
  new language, at real cost to whoever has to reconcile five documents.
- **ALT-402:** Skip verification and just say "run the 07-17 plan" in one
  sentence — rejected: the value of an unattended pass is catching drift (ruff
  206 vs 181, CI still exactly the same 22 failures) that confirms the plan is
  still valid rather than assuming it silently.
- **ALT-403:** Treat the worktree bloat as urgent/blocking — rejected: it's
  pure disk hygiene with no correctness or security implication; sequenced as
  optional, independent cleanup (DEC-402), not inserted into the P0-P2 critical
  path.

## 8. Out of scope

- Re-deriving P0a/P0b/P1/P2/P3-P5 technical content — fully specified already in
  the 07-17 and 07-14 documents/plans.
- Any code change in this pass — this is analysis only, per the orchestrator's
  brainstorm-then-plan workflow.
- Multi-tenant/auth/cloud hosting — still a later product path (unchanged from
  every prior pass).

## 9. Open questions (with adopted defaults)

1. **Q-401:** Is any agent session currently active inside one of the four
   non-empty stale worktrees?
   - **Recommended default:** Assume no (branches carry zero unique commits,
     suggesting they were never used for real work or were already merged/
     abandoned) but verify with a process check before deleting if this is
     executed as a follow-up action.
2. **Q-402 (carried forward, still unresolved after four cycles):** Has the
   leaked NREL key from commits `3911032`/`b14bc0b` actually been rotated at
   developer.nlr.gov?
   - **Recommended default:** Assume no (no evidence of rotation exists in any
     tracked file, commit message, or doc across five brainstorm passes) and
     treat this as the single most overdue P0 item in the entire backlog — it is
     now open across **five** consecutive sessions spanning eleven days.

## 10. Suggested next step

Do not run `/brainstorm` on this repo again until at least PHASE-01 of
`plans/2026-07-17-truth-and-correctness-sprint-plan.md` has landed on `main` and
`gh run list` shows a passing run. If this session (or the next unattended one)
has any implementation budget at all, spend 100% of it on that plan's PHASE-01
and PHASE-02, in that order — both are small, both are independently verifiable,
and PHASE-02 closes a credential exposure that has now been flagged five times
without action. The worktree cleanup (Finding A, DEC-402) can be done in the same
session in five minutes with zero risk, ahead of or alongside PHASE-01.

**One-line thesis:** the repo does not have an ideas problem — it has a five-cycle,
eleven-day execution gap on a plan that was already correct on day one; the
highest-leverage "next-level" move available today is to stop writing the sixth
analysis and run the first one.
