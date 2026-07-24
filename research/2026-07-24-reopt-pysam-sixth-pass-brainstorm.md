---
title: "reopt-pysam: sixth-pass brainstorm — CI truth confirmed, one client-facing number still unaudited"
date: "2026-07-24"
type: "brainstorm"
depth: "standard"
source_request: "unattended orchestrator: analyze reopt-pysam state and brainstorm next-level improvements"
slug: "reopt-pysam-sixth-pass"
supersedes: none
complements:
  - "research/2026-07-11-reopt-pysam-next-level-brainstorm.md"
  - "research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md"
  - "research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md"
  - "research/2026-07-18-execution-debt-decree-243-brainstorm.md"
  - "research/2026-07-22-reopt-pysam-execution-unblock-brainstorm.md"
  - "plans/2026-07-17-truth-and-correctness-sprint-plan.md"
---

# Brainstorm: reopt-pysam — Sixth Pass

> Produced **unattended** on 2026-07-24 (**sixth** consecutive next-level pass in
> thirteen days). Every open decision below is self-answered with the option I
> would have marked "(Recommended)", tagged `(auto-selected)`. No human
> confirmation. This document verifies everything with live tools this
> session — `git log`, `gh run list`, `ruff check --statistics`, `git worktree
> list`, direct source reads — rather than trusting any prior brainstorm's
> claims, and it deliberately does not re-derive content the five priors
> already specified correctly. It surfaces exactly one genuinely new,
> evidence-backed finding that changes the priority ordering, plus three
> smaller new observations.

---

## 1. What actually changed since the last pass (verified live, today)

The 2026-07-22 pass ended with an unusually blunt instruction: don't run
`/brainstorm` again until PHASE-01 of the truth-and-correctness plan lands and
`gh run list` shows green. **That happened.** This is the first of the six
passes where the thing the prior pass asked for is verifiably true:

| Item | 07-22 state | Verified today (2026-07-24) | Evidence |
|---|---|---|---|
| CI on `main` | red, unchanged since 2026-07-14 | **green** — last two runs `29942520141` and `29942791577` both `completed success` | `gh run list --limit 5` |
| Stale git worktrees (~433 MB) | present, 6 directories | **gone** — `git worktree list` shows only the main checkout | `git worktree list` |
| pytest markers (`network`/`requires_artifacts`/`golden_machine`) | not registered | **registered and applied** — plus a fourth, `requires_julia`, added mid-session when the plan's anticipated label turned out to be factually wrong | `pyproject.toml` markers list; `activeContext.md` |
| PySAM pin in CI | unpinned | **pinned** to `nrel-pysam==7.1.0`, matching local `.venv` | `.github/workflows/ci.yml:20` |
| Webapp tests' dependency on a real NREL key | present (CI-only failures) | **removed** via an autouse fixture stubbing `load_nrel_api_key` | commit `0f5d1a0`; `activeContext.md` |
| A genuinely new bug found only by fixing the above | n/a | **found and fixed**: hermetic webapp tests ran two tests further than any prior CI run ever had, exposing a real non-atomic-write race in `RunStorage.set_status`; fixed with a temp-file + `os.replace` pattern and a 200-iteration concurrency regression test | commit `5656ca7`; CI run `29942520141` green |

This is real, verified progress — the first calendar day in this repo's
recent history where "CI is green" is true rather than aspirational, and it
happened by executing exactly the plan five prior passes converged on rather
than writing a sixth roadmap. Good.

**Also unchanged today (still open, still zero-risk to fix, still fully
specified with copy-pasteable commands in the plan):**

| Item | Status today | Evidence |
|---|---|---|
| ruff violations | 207 (was 206 two days ago — growth has essentially stopped, not compounding the way it was 07-17→07-22) | `ruff check . --statistics` |
| Tracked deck `.pptx` binaries | still 3 tracked | `git ls-files \| grep pptx$` |
| Tracked root PNGs | still 2 tracked | `git ls-files \| grep -E "^\w.*\.png$"` |
| `.gitignore` bracket-glob bug | still present, unescaped | `.gitignore:96,98` |
| `requirements.txt` duplication | still present alongside `pyproject.toml` | `git ls-files requirements.txt` |
| NREL key rotation documentation | **still nowhere** — no mention of rotation in README, `activeContext.md`, or any doc | `grep -rn "rotat" README.md activeContext.md docs/*.md` → only an unrelated worklog-archive hit |
| Config-driven case runner (`run_case`, `--offline`, a `CaseConfig`) | **zero code exists** — same as every prior pass | `grep -rn "run_case\|--offline\|CaseConfig" src/` → 0 hits |
| Script sprawl under `scripts/` | **121** files (was 119 on 07-14) — still growing, just slowly | `find scripts/python -name "*.py" \| wc -l` |

The security/hygiene phase (PHASE-02 in the sprint plan's own numbering, called
"Phase 3" in the 2026-07-23 final report) is the one item that is now
**explicitly, plainly overdue relative to the plan's own stated intent**: the
final report you can read right now at
`reports/2026-07-23-final-phase-1-2-ci-truth-workspace-hygiene.html` says, in
its own words, "proceed directly to PHASE-03 (security/hygiene)... a
credential-exposure item that has now gone unaddressed across five consecutive
analysis sessions." That report is dated yesterday. Today makes it **six**.
Every task in that phase is a already-written shell command with no design
judgment required (`git rm --cached <3 named files>`, two `.gitignore` line
edits, `git rm requirements.txt`, one README paragraph). There is no more
"convention decay" or "ambiguous plan" excuse left for this one — it is the
cheapest, most mechanical, most-repeated-as-urgent item in the entire backlog
across six sessions, and it takes under 30 minutes.

---

## 2. The one genuinely new finding this pass

### Finding — the still-unaudited PySAM Single Owner defect sits directly on the client-facing Samsung/TTC deliverable path, not just internal test golden files

Every prior pass (07-17 onward) has described the Single Owner clean-slate gap
in *test/correctness* terms: SAM's `Singleowner` financial model silently
carries ~100 MW-reference-plant cost defaults (a flat **$2,866,500**
construction-financing charge among twelve contaminated fields) into sub-2 MWp
Vietnam project economics, and the fix (an opt-in `zero_reference_plant_defaults`
flag + an audit report) is fully specified in PHASE-04/05 of the sprint plan.
What no prior pass traced all the way through is **which real files call this
path**, verified today by direct source read:

- `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py:771` imports and
  calls `run_single_owner_model` directly — this is the Samsung/TTC
  orchestrator, the repo's flagship, bit-exact-parity-gated case.
- `scripts/python/integration/generate_samsung_ttc_deck.py` exists alongside
  `analyze_samsung_ttc_combined.py`, `analyze_samsung_ttc_dppa.py`,
  `analyze_samsung_ttc_strike_developer.py`, and `build_samsung_ttc_inputs.py`
  — a full pipeline from Single-Owner-backed analysis to a generated deck.
- `present/Allotrope DPPA insights.pptx` (plus `.../original template.pptx` and
  `.../local run.pptx`) and `reports/2026-06-04-final-samsung-ttc-dppa.html`
  are **tracked, dated artifacts that read as real client deliverables**, not
  test fixtures — this is Allotrope's actual external-facing output format for
  this kind of engagement (the same pipeline shape recurs for the CEBA/DPPA
  July 2026 deck under `ceba-review/`).

Put together: **it is not established whether the specific finance numbers
already shown to Samsung/TTC (or embedded in a deck someone may have sent)
include the SAM reference-plant defaults documented as a defect three sessions
ago.** The sprint plan's PHASE-05 audit (TASK-04-03) is designed to answer
exactly this — "for each caller, determine whether its published/tracked
outputs... embed the nonzero SAM defaults" — but it has not been run. This
reframes PHASE-05 from "a correctness nice-to-have queued behind CI" to **a
question about whether a number already delivered to an external counterparty
needs a correction communicated**, which is a different urgency class
entirely (reputational/contractual, not just test-suite hygiene) — and it is
answerable in an afternoon without touching the golden file, per the plan's own
CON-001 (audit-only, no restatement without a human decision).

`(auto-selected — DEC-601: escalate PHASE-05's audit task specifically, ahead
of the general phase ordering, precisely because it is the one item in the
backlog whose unresolved state carries external-facing risk rather than
internal-quality risk. This does not change what to build — the plan's TASK-04-03
already specifies the audit exactly — only which phase to run first if there is
limited execution budget today.)`

---

## 3. Three smaller new observations

**A. The webapp cannot produce the client deliverable it feeds.** The web app
(`webapp/routes/api.py`) exports a run as JSON or a Plotly-charted HTML page —
useful for an analyst, but the actual external deliverable format this repo
produces (verified above) is a PPTX deck, generated today by a fully separate,
manual, script-driven pipeline (`scripts/python/integration/generate_*_deck.py`
+ `ceba-review/` + `present/`) with no connection to a webapp run at all. No
prior pass named this gap directly — the 07-14 pass's Theme C (ops readiness)
and Theme A (config runner) are adjacent but neither says "the tool an analyst
runs and the deck a client receives are two disconnected systems." Once the
config-driven case runner (Theme A, still unstarted) exists, a natural
follow-on is a `POST /api/runs/{run_id}/deck` that reuses the existing PPTX
generation code against a webapp run's output — closing the loop from
"analyst clicks a button" to "client-ready deck," which is the actual
end-to-end value chain this whole toolkit exists to shorten. `(auto-selected:
sequence this behind the config-driven runner, not before it — it is a
consumer of that refactor, not a substitute for it.)`

**B. No coverage measurement exists anywhere in the toolchain.** `mypy` gates
`analysis/`+`webapp/`; nothing gates or even *reports* what fraction of the
~12.3k-line `src/python/` package the 62 test files actually exercise. Adding
`pytest-cov` with a report-only (non-blocking) CI step is a one-line, zero-risk
addition that would turn "552+ tests pass" from a raw count into an actual
signal about which of `integration/`'s 79 files have real coverage versus none
— directly useful evidence for prioritizing the Theme-A script-sprawl
decomposition, since files with zero test coverage are the riskiest to
refactor first. `(auto-selected: report-only, not a %-threshold gate — this
repo's parity-gated numeric tests already carry the real correctness burden;
a coverage gate on top would be measuring the wrong thing.)`

**C. `plans/active/` holds 20 files, all dated 2026-04-23 through 2026-06-26,
whose corresponding features already exist and ship in the repo today**
(dppa_case_1/2/3, the map site picker's precursor gap-0X plans, the
mechanical-debloat sprints). Nothing distinguishes "still executing" from
"finished, never rotated to `archive/`" the way `activeContext.md` does with
its own worklog-rotation convention. This is the same shape of drift
`lessons.md` already warns about for `activeContext.md` itself — a directory
literally named `active` that is ~90% historical is a small but real
onboarding trap for the next fresh session. `(auto-selected: a `plans/README.md`
sweep — move anything whose plan is fully checked-off and whose feature is
verifiably shipped into `plans/archive/` — is a 15-minute hygiene task, lower
priority than Finding A but cheaper than any of PHASE-02's items individually.)`

---

## 4. What this pass does *not* re-litigate

Confirmed still valid, still unexecuted, still exactly as specified — no new
analysis added:

- **PHASE-02 (security/hygiene)** — untrack 3 pptx + 2 PNGs, fix 2 `.gitignore`
  lines, remove `requirements.txt`, document key rotation. Fully specified in
  `plans/2026-07-17-truth-and-correctness-sprint-plan.md` PHASE-02
  (TASK-02-01 through 02-06). **Six sessions overdue.**
- **PHASE-03 (two-part tariff Ca re-pricing fix)** — fully TDD-specified,
  exact formulas and toy-case expected values already in the plan.
- **PHASE-04/05 (Single Owner clean-slate + audit)** — fully specified;
  §2 above only changes *which phase to prioritize first*, not what to build.
- **Theme A (config-driven case runner)** — still the single biggest
  architectural lever (07-14's diagnosis stands; script count grew 119→121,
  confirming the "every new deal spawns a new file" pattern continues).
- **Theme B (Julia archive-in-place decision)** — still an open, human-vetoable
  call (Q-101 from 07-14), still unexecuted, still zero technical risk to defer.
- **Frozen-resource offline solve mode, settlement vectorization (measure
  first), domain data dictionary** — all still valid, still unstarted,
  still correctly deprioritized behind the above.

---

## 5. Resolved decisions (self-answered this pass)

- **DEC-601:** Escalate PHASE-05's audit (TASK-04-03) specifically, ahead of
  the plan's own default ordering, because unresolved state there carries
  external-facing risk (§2), not just internal test-quality risk. The audit
  itself makes no code or golden changes (CON-001 unaffected). *(auto-selected)*
- **DEC-602:** Do not write a seventh roadmap next time either, unless the
  verified state changes materially — the queue is stable, well-specified, and
  small. Future unattended passes on this repo should default to a
  **verify-and-execute** posture (open the plan, run the next unexecuted
  phase) rather than **verify-and-re-analyze**, now that CI truth proves the
  execute path works when it's actually taken. *(auto-selected)*
- **DEC-603:** Add `pytest-cov` as a report-only CI step (§3.B) — cheap,
  additive, no gate, no risk. *(auto-selected)*
- **DEC-604:** Sequence a webapp→deck export endpoint (§3.A) behind the
  config-driven case runner, as that runner's natural first consumer, not as
  an independent feature. *(auto-selected)*
- **DEC-605:** Sweep `plans/active/` for finished plans into `plans/archive/`
  (§3.C) — 15-minute hygiene, lower priority than any PHASE-0X item.
  *(auto-selected)*

## 6. Assumptions & constraints

- **ASM-601:** The two green CI runs (`29942520141`, `29942791577`) reflect
  the actual current state of `main`, not a transient fluke — reasonable given
  both ran the identical portable-suite filter and both succeeded consecutively.
- **ASM-602:** No one has yet run PHASE-05's audit or confirmed/denied whether
  the Samsung/TTC or CEBA deck pipelines' historical numbers are contaminated —
  this finding is a risk flag based on call-graph evidence (`dppa_samsung_ttc.py`
  calling `run_single_owner_model` directly), not a confirmed defect in any
  specific delivered number. The audit, not this brainstorm, is what would
  confirm magnitude.
- **CON-601:** Samsung/TTC bit-exact parity remains inviolable; nothing here
  proposes touching the golden file, consistent with every prior pass.
- **CON-602:** Windows-first repo; nothing in this pass's findings requires
  cross-platform tooling changes.

## 7. Approaches considered

- **Chosen:** Verify-first, then surface only what changed or what no prior
  pass connected — spend most of the budget confirming the 07-22 recommendation
  actually landed (it did), and use the remaining budget to trace one
  under-examined call path (Single Owner → Samsung/TTC → client deck) that
  changes the priority of an already-specified phase rather than inventing new
  scope.
- **ALT-601:** Re-derive a fresh full roadmap — rejected for the same reason
  as 07-22: five prior passes already did this correctly; a sixth rehash adds
  reading burden without adding information.
- **ALT-602:** Treat "PHASE-02 still not done" as grounds for alarm/escalation
  language disproportionate to its actual risk — rejected: it is genuinely
  low-risk (no external exposure, keys already gitignored going forward), just
  cheap and repeatedly deferred. The tone here is "this is free, do it," not
  "this is an emergency."
- **ALT-603:** Skip verifying CI/worktree state and just assume the 07-22
  report's claims — rejected: the entire value of a fresh pass is confirming
  drift or confirming success with live tools, same standing principle as every
  prior pass.

## 8. Out of scope

- Re-deriving any PHASE-0X technical content (fully specified already).
- Running the Single Owner audit or any code change myself — this is an
  analysis-only pass per the orchestrator's brainstorm-only workflow; §2
  is a priority flag for whoever executes next, not an executed audit.
- Multi-tenant/auth/cloud hosting, Dockerfile/deployment packaging — still
  later-stage product questions with no urgency signal this session.

## 9. Open questions (carried forward, with adopted defaults)

1. **Q-601 (was Q-402, now open across SIX sessions, 13 days):** Has the
   leaked NREL key from commits `3911032`/`b14bc0b` been rotated at
   developer.nlr.gov?
   - **Recommended default:** Still assume no — no doc anywhere records it,
     and PHASE-02 (which would document the requirement even if a human did
     rotate it out-of-band) has not run. Treat as the single most overdue
     mechanical item in the backlog.
2. **Q-602 (new):** Has any Samsung/TTC or CEBA-deck deliverable already been
   sent to an external counterparty using Single-Owner-derived finance numbers
   that may embed the SAM reference-plant defaults (§2)?
   - **Recommended default:** Cannot be answered from repo inspection alone —
     this needs either the PHASE-05 audit (which checks the *numbers*, not
     send history) or a direct human answer about what has actually gone out
     the door. Flagging it is the responsible move; guessing an answer is not.

## 10. Suggested next step

If today's execution budget is small: run PHASE-02 (security/hygiene) in full
— it is six sessions overdue, entirely mechanical, and every command is
already written in `plans/2026-07-17-truth-and-correctness-sprint-plan.md`
TASK-02-01 through TASK-02-06.

If there is room for one more item: run PHASE-05's audit task (TASK-04-03)
specifically — not the whole Single-Owner-clean-slate phase, just the
read-only audit — to close Q-602 with an actual answer instead of a risk flag.
It writes one report file, touches no code, and answers a question that
currently has real (if unquantified) external-facing stakes.

**One-line thesis:** the fifth pass's recommendation worked — CI is
genuinely green for the first time in ten days, proving this repo's execution
gap is fixable, not structural. What's left is not a new roadmap: it's finishing
the same six-session-old cheap phase, and finding out — via one audit, not one
more brainstorm — whether a number already shown to a real counterparty needs
a second look.
