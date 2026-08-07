---
date: 2026-08-06
slug: reopt-pysam-gate-integrity
kind: brainstorm
mode: unattended (no user input; all open choices self-resolved and flagged)
repo: reopt-pysam
branch: main @ dc1cfc9
predecessors:
  - research/2026-07-11-reopt-pysam-next-level-brainstorm.md
  - research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md
  - research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md
  - research/2026-07-18-execution-debt-decree-243-brainstorm.md
  - research/2026-07-22-reopt-pysam-execution-unblock-brainstorm.md
  - research/2026-07-24-reopt-pysam-sixth-pass-brainstorm.md
  - research/2026-07-26-reopt-pysam-post-backlog-architecture-brainstorm.md
---

# Brainstorm: reopt-pysam — Eighth Pass (gate integrity & deal generalization)

## 0. Why this pass leads with a defect, not a roadmap

The seventh pass wrote `plans/2026-07-26-post-backlog-architecture-plan.md`, and
that plan is now marked `complete — PHASE-01..06 shipped`. Six phases landed
across `3943c5b … dc1cfc9`: a Python 3.10/3.12 CI matrix plus a ruff gate, a
schema-validated `DealConfig`, honest parity documentation, a canonical
assumptions resolver, FX unification on 26,400 VND/USD, and Julia archived under
`legacy/julia/`. The local suite is green and larger than it was: **634 passed,
18 deselected, 3 xfailed, 85 % coverage.**

So by the repo's own record the backlog is drained again, and the standing
instruction (`DEC-602`) is to verify-and-execute rather than write another
roadmap. I started by verifying. Verification did not confirm the record.

**The CI pipeline has been failing on every push since the lint gate was
introduced — three consecutive red runs spanning 2026-07-26 to 2026-08-01 — and
every phase from PHASE-02 onward was pushed onto a red `main`.** The failure is
not in any of that work; it is in the gate itself, and it is the same class of
defect the seventh pass was written to fix: a control that *looks* enforced,
is documented as enforced, and enforces nothing. `activeContext.md` still reads
"**CI status:** Green on `main`".

That is the material change this pass reports. Sections 2–3 then set out what I
believe is the genuinely next-level work, which turns out to be much more
concrete than "config-driven case runner" — see F2.

---

## 1. Verification refresh — what is true on 2026-08-06 (run live, not assumed)

| Claim | Verified | Evidence |
|---|---|---|
| Portable suite green locally | ✅ | `634 passed, 18 deselected, 3 xfailed` in 94–131 s on `.venv` (Py 3.12), CI's exact marker filter |
| Coverage instrumented | ✅ | **85 %**, 4,713 statements (up from 4,599) |
| `mypy` gate passes locally | ✅ | `Success: no issues found in 21 source files` (mypy 2.3.0) |
| **CI green on `main`** | ❌ | **3 consecutive failures**: runs `30211921197` (07-26), `30693998928` (08-01), `30722078575` (08-01). All fail at step `Lint (ruff)`. Last green run: `30135167312`, 2026-07-24 — *before* the gate existed |
| `ruff check src scripts tests` exits 0 | ❌ | **766 errors** under ruff 0.16.1 |
| PHASE-01 lint cleanup was real | ✅ | `ruff check --isolated --select E4,E7,E9,F --ignore E402 …` → `All checks passed!` — the cleanup was correct *for the rule set ruff shipped at the time* |
| Julia archived, paths rewired | ✅ | `src/julia/` gone; `legacy/julia/{src,scripts,tests}` present; `tests/run_all_tests.ps1` points at `legacy\julia\…` |
| Assumptions resolver exists and is imported | ✅ | `common/assumptions.py`; 21 import sites across `src/`, `scripts/`, `tests/` |
| FX literals unified | ⚠️ partial | Uniform *value* (26,400) but **14 of 19** call sites still pin it as `caller_value=`, short-circuiting the resolver at step 1 — see F3 |
| Parity docs reconciled | ⚠️ partial | `README.md` and `docs/onsite_vs_offsite.md` fixed; **`src/python/reopt_pysam_vn/webapp/README.md` still claims bit-for-bit against the golden** — see F4 |

**Unchanged and still open:** the NREL key from commits `3911032` / `b14bc0b` is
still not confirmed rotated. That is now **eight sessions, 26 days.**

---

## 2. New findings — things no prior pass has named

Verified by direct inspection or by pulling the actual CI logs today. Ordered by
consequence.

### F1 — The lint gate has never been green in CI, and it broke because nothing in the toolchain is pinned

`.github/workflows/ci.yml` installs its own gates unpinned:

```yaml
pip install -e ".[webapp]" mypy pytest pytest-cov ruff
```

PHASE-01 correctly cleaned the repo to zero violations under the ruff release
current on 2026-07-26, whose default rule selection was `["E4", "E7", "E9", "F"]`.
Ruff 0.16 substantially **expanded the default rule set**. The identical,
unmodified source tree now reports 766 violations:

| Rule | Count | Character |
|---|---|---|
| `UP006` non-pep585-annotation (`List[str]` → `list[str]`) | 224 | auto-fixable |
| `I001` unsorted-imports | 142 | auto-fixable |
| `RUF100` unused-noqa | 101 | auto-fixable — *and these are the `# noqa: E402` comments PHASE-01 deliberately added* |
| `UP045` non-pep604-annotation-optional | 97 | auto-fixable |
| `ISC004` implicit-string-concat-in-collection | 57 | manual |
| `UP035` deprecated-import | 39 | manual |
| `BLE001` blind-except | 14 | manual, and the only genuinely diagnostic one |
| others (DTZ, S110, PLW, B, SIM, RUF012 …) | 92 | mixed |
| **total** | **766** | 606 auto-fixable |

None of this is a code regression. It is a **supply-chain-timing regression in
the gate**, and it is structurally identical to the defect the seventh pass
called F3 ("the headline correctness guarantee is enforced nowhere"): the
control exists on paper and does not hold.

Three compounding facts make this worth leading with:

1. **It went unnoticed for eleven days across five commits.** PHASE-02 → PHASE-06
   were each verified locally and each pushed onto a red pipeline. The final
   report for phases 1–2 states "606 tests green / ruff + mypy clean" — true
   locally, false in CI, and nothing in the workflow checked.
2. **The unattended verification loop has a blind spot.** Every pass so far has
   verified by *running the suite locally*. No pass has run `gh run list`. Local
   green and CI green are different claims, and this repo has been reporting the
   first as if it were the second.
3. **The same exposure applies to `mypy` and every `>=` dependency.**
   `nrel-pysam==7.1.0` is the only pin. `mypy` currently passes at 2.3.0; it is
   one release away from the same failure mode, and a mypy break would be much
   harder to distinguish from a real type defect than a lint break was.

`RUF100` deserves a specific note: 101 of the violations are ruff objecting to
`# noqa: E402` suppressions that PHASE-01 itself introduced, because `E402` is
now globally ignored in `[tool.ruff.lint]`. The gate is flagging the gate's own
configuration as redundant. That is a clean signal that the config was written
against one rule set and is being evaluated against another.

### F2 — The declared public API can run offsite/DPPA analysis for exactly one deal

This is the finding I would act on if only one thing gets done, and I do not
think any prior pass has stated it this plainly.

`reopt_pysam_vn.analysis` is the declared, type-checked, `py.typed` public
surface, and `run_offsite_dppa` is its flagship entry point — offsite/DPPA is the
repo's entire commercial framing. Its orchestrator registry is:

```python
_ORCHESTRATORS: Dict[str, CombinedDecisionFn] = {
    "DPPA_SAMSUNG_TTC": _samsung_ttc_orchestrator,
}
```

`register_orchestrator` is exported in `__all__`, documented in the package
docstring, named in the error message — and **called from nowhere in `src/`,
`scripts/`, or `tests/`.** Any `DealConfig` whose `case` is not the literal
string `DPPA_SAMSUNG_TTC` raises:

```
ValueError: no offsite orchestrator registered for case '…'
```

The four other bespoke engines that exist and are tested — `dppa_case_1`,
`dppa_case_2` (1,491 lines, the largest module in the repo),
`dppa_case_3`, `ninhsim_solar_storage_60pct` — are described in `README.md` as
"the orchestration engines behind a registry." They are not behind the registry.
They are reachable only by importing the internal module directly, which the same
README deprecates.

The asymmetry with the onsite path is instructive and makes the fix look
tractable: `run_onsite` **is** genuinely generic. It post-processes a REopt
results dict with no per-deal branching anywhere in its 184 lines. Onsite was
generalized; offsite was given a front door with one key cut for it.

The consequence propagates to the product. `webapp/service.py` documents it
honestly in its own docstring and even ships a dedicated
`OrchestratorNotRegisteredError` — but `/deals/new` still offers "Offsite DPPA"
and "Both / combined" in its mode dropdown. An analyst can fill in the whole
form for a new Vietnamese offtaker and get a 422.

Six passes have named "config-driven case runner" as Theme A and none has
started it, partly because "restructure 106 scripts" is not a task anyone can
start on a Tuesday. **Registering a second orchestrator is.** It is the same
initiative reduced to its first falsifiable increment: pick `dppa_case_2` or
`ninhsim_solar_storage_60pct`, adapt it to the
`(extracted, *, run_developer) -> dict` contract, register it, and add a
`test_offsite_dppa` case that is not Samsung. The moment the registry has two
entries, the shape of the generic path stops being a design question and becomes
a diff.

### F3 — The FX resolver is threaded through the call path but short-circuited at 14 of 19 sites

PHASE-04/05 did the hard part correctly: `common/assumptions.py` implements the
S1–S4 precedence chain, `vn_deal_defaults_2026.json` got its `{_meta, data}`
envelope, `VNData` loads it, and the two-commit discipline (`0f40be8`
value-preserving, then `2fce33a` value-changing) was followed exactly as
`DEC-703` required. That was good work and the delta memo exists.

But the resulting call sites read:

```python
EXCHANGE_RATE_VND_PER_USD = _resolve_exchange_rate(load_vietnam_data(), caller_value=26_400.0)
```

`caller_value` is **step 1** of the precedence chain. It always wins. So in these
modules the resolver is a pass-through: it reads the data layer, then discards it
in favour of the literal it was handed. Editing
`vn_deal_defaults_2026.json`'s `exchange_rate.vnd_per_usd` today would change the
output of **5** call sites (`reopt/two_part_tariff.py`,
`scripts/python/reopt/build_saigon18_reopt_input.py`,
`scripts/python/reopt/two_part_tariff_sensitivity.py`, and `dppa_case_2`'s three
per-deal lookups), not 19.

The seventh pass's F1 was "a canonical FX value exists and nothing loads it."
The current state is one notch better — everything now *routes through* the
loader — but the data layer is still not authoritative. The refactor achieved
**unification** (one value everywhere) without achieving **derivation** (one
source of truth). Those look identical in a diff and behave differently the first
time someone needs to change the rate.

This is genuinely low-risk to finish now, precisely *because* the values are
already unified: dropping `caller_value=26_400.0` from the fourteen
general-purpose sites is provably value-preserving today (the data layer holds
26,400), and it is the only thing that makes the next FX change a one-line edit
instead of a fourteen-file sweep. The five deal-specific 25,450 pins
(`dppa_case_3`, `analyze_saigon18_*`, `build_saigon18_*`) should **stay** pinned
— per `ASM-005` those are deliberate contract-basis overrides, and each already
carries an explanatory comment.

A smaller related note: all fourteen resolve at **module import time** into a
module-level constant. That makes the value un-overridable per run and the
modules awkward to test with an alternate rate. I measured the cost —
`load_vietnam_data()` is ~2.8 ms, so ~57 ms across the tree; **this is not a
performance problem** and should not be sold as one. It is a testability and
override-surface issue only.

### F4 — The parity-honesty sweep missed two files, one of which is a README

PHASE-03 chose Branch B (honest documentation over a restored gate) and executed
it correctly in `README.md`, `docs/onsite_vs_offsite.md`, `docs/testing.md`, and
`docs/architecture.md`. `docs/onsite_vs_offsite.md` now reads exactly right:
"a **local-only diagnostic**: excluded from CI (`golden_machine` marker) and
currently `xfail`ed."

Two artifacts still carry the old claim:

- **`src/python/reopt_pysam_vn/webapp/README.md:63-66`** — "The Samsung/TTC
  golden-parity test (`test_golden_parity.py`) proves the web API path reproduces
  `examples/samsung-ttc_combined-decision.example.json` bit-for-bit." The test's
  own module docstring says the opposite: *"It deliberately does NOT re-assert
  parity against `examples/samsung-ttc_combined-decision.example.json`."*
- **`src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py:6`** — module
  docstring still describes the combined-decision as parity-gated bit-for-bit.

The webapp README is the one a new analyst or a client-side reviewer would read
first when asked "how do I know this tool is right?". It is the highest-traffic
remaining instance of the exact claim the phase was written to retire.

### F5 — A test now pins the bug in place

`tests/python/webapp/test_golden_parity.py::test_samsung_ttc_golden_drift_is_the_known_pre_existing_gap`
asserts that the drift **exists**:

```python
assert drifted, (
    "expected the known pre-existing golden drift on developer_irr_fraction; "
    "if this now passes, the analytics-level golden may have been refreshed - "
    "re-enable full parity checking in this test."
)
```

The intent is defensible and the failure message is unusually thoughtful — it is
a tripwire that fires when someone fixes the underlying divergence, so the
disabled parity assertions get re-enabled instead of forgotten. But the mechanism
inverts the meaning of green: the suite is green **because** the analytics are
wrong, and fixing them turns CI red. Combined with the two `xfail`s and the
`golden_machine` exclusion, the Samsung divergence is now held in place by three
separate mechanisms, one of which actively resists repair.

I would keep the tripwire and change its polarity: assert the drift is *bounded
and catalogued* (a stored diff manifest of the specific fields known to diverge),
so shrinking the divergence stays green and *growing* it goes red. That preserves
the alerting intent without making correctness a test failure.

The companion test in the same file —
`test_samsung_ttc_web_api_matches_direct_library_call_bit_exact` — is genuinely
valuable and genuinely enforced (8.7 s, the slowest test in the suite, runs in
CI). It proves `CON-002`: the webapp forks no analytics. That one is real.

### F6 — `AGENTS.md`'s status sections are five months stale, and stale branches back them up

`AGENTS.md` is the file every agent session reads first. Sections 4 and 6 are
from March 2026:

- **§4 "Test Suite Status (last run: Mar 2026)"** — a table reporting
  `test_commercial_rooftop_api_solve` and `test_api_vs_baseline_regression` as
  FAIL and "L4 Julia: NOT RUN". Superseded three times over; the current truth is
  the 634/18/3 line and the five documented `xfail`s in `activeContext.md`.
- **§6 "Real Project Data Notes"** — describes a branch `real-project-data` and
  lists "Next steps" including "Custom JuMP constraint for 20% generation export
  cap (Decree 57)". Decree 243/2026 raised that cap to 50 % on 2026-06-26 and the
  repo ingested the change on 2026-07-18. The branch's last commit is 2026-03-03.

Live branches, none touched since May: `real-project-data` (2026-03-03),
`claude/clever-chaplygin-dad6dc` and `claude/kind-mcclintock-10b2e5` (both
2026-05-06). The 07-22 sprint cleaned up stale *worktrees*; the branches survived.

This matters more here than in a human-only repo. Stale context in `AGENTS.md`
is not documentation debt, it is **input to every future session** — an agent
reading §6 today would go implement a repealed 20 % cap.

### F7 — The regulatory watch has no verification date, no owner, and no expiry

`docs/regulatory-watch.md` is a good idea, well-executed as far as it goes: seven
rows, governing instruments named, one row (`export_rules`) honestly flagged
`PENDING`. But "Status: CURRENT" carries no date, so it is an unfalsifiable
claim — nothing distinguishes "verified current last week" from "nobody has
looked since March."

The exposure is concrete. `vn_tariff_2025.json` derives every VND figure the
toolkit emits from an average retail price of **2,204.0655 VND/kWh**, sourced to
Decision 599/QD-EVN of **2025-05-10**. Its own `_meta.notes` records that
Decision 07/2025/QD-TTg lets EVN adjust that price by 2–5 % at three-month
minimum intervals. Fifteen months have passed, so up to five adjustment windows
have opened.

**I checked, and the number appears to still be right:** 2,204 VND/kWh
(ex-VAT) is still reported as the standing average retail price in 2026, the
4.8 % May-2025 increase from 2,103 being the most recent. So this is a **process
finding, not a known-wrong number** — I want to be precise about that, because
overstating it would be exactly the kind of thing the repo's own `lessons.md`
warns against. The defect is that the table cannot tell you it was checked; the
next check will be as unrecorded as this one unless the schema changes.

Minimal fix: add `Last verified` (date) and `Next review` columns, and a repo
invariant test that fails when any row's `Next review` is in the past. That turns
a documentation habit into a gate — and unlike most gates, this one costs nothing
to keep green.

### F8 — The reporting layer census, updated, plus one surviving shim

Refreshed numbers for the carried Theme A:

- **36** `generate_*.py` scripts totalling **10,868 lines** (was 34 / 10,189).
- **9** of them hand-roll a complete HTML document (`<style>` block, fonts, cards,
  Chart.js wiring) — nine independent copies of the same page chrome.
- Meanwhile **`assets/report-template.html` (694 lines) and
  `assets/final-report-template.html` (717 lines) already exist** and are used by
  ~10 other scripts. So the repo is not missing a template; it has one, and a
  third of the report builders ignore it. That reframes Theme A's first
  increment from "design a reporting pipeline" to "migrate nine files onto the
  template that already works."
- `scripts/python/` totals **31,202 lines** against `src/python/`'s **12,847** —
  the ratio of un-tested workflow code to library code is roughly 2.4 : 1.

Separately: **`tests/cross_validate.py`** is a 14-line `runpy` shim delegating to
`tests/cross_language/cross_validate.py`. The repo banned exactly this pattern
for `scripts/python/*.py` on 2026-06-12, wrote a `lessons.md` entry about it, and
mechanically enforces the ban with
`test_repo_invariants.py::test_no_flat_python_scripts`. The invariant does not
cover `tests/`. Trivial, but it is the same shape of debt the repo has already
decided it does not want.

---

## 3. Themes — the roadmap this pass proposes

### Theme H (new, #1) — Make the gates real, and make "green" mean CI

F1 is not a lint problem; it is a **verification-integrity** problem, and it
invalidates the "CI green" line in every recent status document. Three parts,
all small:

1. **Pin the toolchain.** Add a `[project.optional-dependencies] dev` group with
   `ruff==<current>`, `mypy==<current>`, `pytest`, `pytest-cov` at exact
   versions, and have CI install that group instead of naming tools inline. A
   linter that changes its own defaults between runs is not a gate.
2. **Clear the 766.** 606 are auto-fixable and land in two mechanical sweeps:
   `UP006`/`UP045`/`UP035` (PEP 585/604 annotations — safe, and the repo is
   already `from __future__ import annotations` throughout) and `I001` import
   sorting. Then delete the 101 now-redundant `# noqa: E402` comments the
   `E402` global ignore made obsolete. The ~90 manual ones (`ISC004`, `BLE001`,
   `DTZ001`, `S110`) are worth reading rather than suppressing — `BLE001`
   blind-except ×14 and `S110` try-except-pass ×5 are the kind of thing that
   silently swallows a real solver error.
3. **Close the blind spot in the workflow itself.** Every unattended pass has
   verified locally and reported CI status from memory. Add `gh run list --limit 3`
   (or a `gh run watch` after push) to the repo's own verification convention —
   `AGENTS.md` §2 and the `/verify` flow. This is the cheapest of the three and
   prevents the recurrence, not just the instance.

**Sizing:** hours, and it unblocks honest reporting on everything below.

### Theme I (new, #2 — this is the reframed Theme A, and the highest-value substantive work) — Register a second offsite orchestrator

F2 turns six passes of "config-driven case runner" into one concrete deliverable.
The proposed increment:

1. Choose `ninhsim_solar_storage_60pct` (462 lines, 97 % covered, already has a
   combined-decision shape) over `dppa_case_2` (1,491 lines) for the first
   registration. Smaller blast radius; `dppa_case_2` is the settlement engine
   several other paths depend on and should move last, not first.
2. Adapt it to the `(extracted, *, run_developer) -> dict` orchestrator contract
   and call `register_orchestrator("NINHSIM_SOLAR_STORAGE_60PCT", …)` from the
   `analysis` package.
3. Add a non-Samsung case to `tests/python/analysis/test_offsite_dppa.py`, and a
   webapp test that a second `case` value reaches `done` rather than 422.
4. **Only then** extract whatever the two orchestrators visibly share into the
   generic path. Two implementations is the minimum from which a real abstraction
   can be derived; one is just a shim with aspirations.

The honest sequencing argument: the seventh pass argued the assumptions resolver
must precede the reporting pipeline so the template layer is not built over
divergent constants. That argument held and the resolver shipped. The same logic
now applies here — a *reporting* pipeline over an *analysis* API that serves one
deal would be a template engine for a single client.

**Sizing:** ~1 sprint for steps 1–3; step 4 is the multi-sprint part and should
be scoped after 1–3 reveal the real shared surface.

### Theme E-finish (#3) — Complete the FX derivation

F3, and it is genuinely small: drop `caller_value=26_400.0` from the fourteen
general-purpose call sites so the data layer becomes authoritative, keep the five
deal-specific 25,450 pins as documented contract overrides, and add a test that
mutating a temp copy of `vn_deal_defaults_2026.json` moves the resolved rate in
the general-purpose modules. Provably value-preserving today because the values
already agree — which is exactly the window in which to do it.

While there: consider making the fourteen module-level constants lazy
(a `_exchange_rate()` function or `functools.cache`d accessor) so a per-run
override is possible at all. Optional; do not let it expand the change.

**Sizing:** half a day.

### Theme F′ (#4) — Finish the truth sweep

F4, F5, F6 are one job: bring every remaining document and tripwire in line with
what is actually enforced.

- Correct `webapp/README.md`'s bit-for-bit claim and
  `dppa_samsung_ttc.py`'s module docstring.
- Re-polarize the drift-pinning test to a bounded, catalogued diff manifest so
  *fixing* the divergence stays green.
- Rewrite `AGENTS.md` §4 (point at `activeContext.md` rather than restating a
  March test table) and §6 (the Decree 57 20 % "next step" is repealed).
- Delete or merge the `real-project-data` and two `claude/*` branches after
  confirming nothing unique is on them; delete `tests/cross_validate.py` and
  extend `test_repo_invariants.py` to cover `tests/` shims.
- Add `Last verified` / `Next review` to `docs/regulatory-watch.md` plus the
  invariant test (F7). Record today's tariff check as the first entry: average
  retail price 2,204.0655 VND/kWh ex-VAT still standing as of 2026-08-06.

**Sizing:** ~1 day, and it is the item with the best ratio of future-agent-hours
saved to hours spent, because `AGENTS.md` is read by every session.

### Theme A (#5, carried and re-scoped) — Consolidate the reporting layer

F8 gives this a much cheaper first step than prior passes assumed: the shared
templates already exist and already serve ~10 scripts. Migrate the 9 hand-rolled
HTML builders onto `assets/report-template.html` before designing anything new.
That alone removes nine copies of the page chrome and tells you what the template
is actually missing — which is the requirements document for
`python -m reopt_pysam_vn.report`.

**Sizing:** the migration is ~1 sprint; the `report` module remains multi-sprint
and remains correctly sequenced after Theme I.

### Carried, unchanged — webapp → deck export

The 07-24 pass's Finding A (the analyst-facing webapp cannot emit the PPTX the
client actually receives) stands, unstarted, and is still a consumer of Theme A.
F2 adds a second prerequisite: exporting a deck for a deal the API cannot run is
not a feature.

---

## 4. Suggested sequencing

| # | Item | Size | Why here |
|---|---|---|---|
| 1 | **Theme H** — pin the dev toolchain, clear 766 ruff violations, add a CI-status check to the verification convention | hours | Every other item's "done" claim is unverifiable until CI is green again, and the blind spot recurs otherwise |
| 2 | Theme F′ — finish the truth sweep (`AGENTS.md`, `webapp/README.md`, drift-test polarity, stale branches, watch-table dates) | ~1 day | Cheap; `AGENTS.md` is input to every future session, and §6 currently points at a repealed regulation |
| 3 | Theme E-finish — drop the 14 `caller_value` pins | half day | Provably value-preserving *right now*; the window closes the moment any rate diverges again |
| 4 | **Theme I** — register a second offsite orchestrator | ~1 sprint | The highest-value substantive work; converts six passes of abstract Theme A into a diff |
| 5 | Theme A — migrate 9 hand-rolled report builders onto the existing template | ~1 sprint | Strictly better after #4; produces the requirements for a real `report` module |
| 6 | webapp → deck export | ~1 sprint | Consumer of #4 and #5 |

---

## 5. Decisions self-resolved this pass (no user input was solicited, per workflow)

- **DEC-801** — Lead with F1 and write a roadmap rather than verify-and-execute.
  The plan is complete but its PHASE-01 exit criterion ("CI shows two green jobs")
  is **not met**, so there is no drained-backlog state to execute against.
  *(auto-selected)*
- **DEC-802** — Pin the linters exactly rather than loosen the rule set to match
  the old defaults. An unpinned gate that redefines itself between runs is the
  root cause; `select = ["E4","E7","E9","F"]` would restore green while leaving
  the same trap armed for `mypy`. *(auto-selected)*
- **DEC-803** — Clear the 766 rather than suppress them. 606 are auto-fixable and
  the ~90 manual ones include `BLE001` ×14 and `S110` ×5, which are worth
  reading. *(auto-selected)*
- **DEC-804** — Theme I (second orchestrator) outranks Theme A (reporting
  pipeline), continuing the seventh pass's logic one layer up: do not build a
  template layer over an API that serves one deal. *(auto-selected)*
- **DEC-805** — First registration target is `ninhsim_solar_storage_60pct`
  (462 lines, 97 % covered), **not** `dppa_case_2` (1,491 lines, load-bearing
  settlement engine). Smallest viable second implementation. *(auto-selected)*
- **DEC-806** — Keep the drift tripwire, invert its polarity to a bounded diff
  manifest. Deleting it would re-hide the divergence; leaving it makes fixing the
  bug fail CI. *(auto-selected)*
- **DEC-807** — Keep the five deal-specific 25,450 FX pins. `ASM-005` from the
  07-26 plan established these as deliberate contract-basis overrides and nothing
  found today contradicts that. *(auto-selected, carried)*
- **DEC-808** — Add a CI-status check (`gh run list`) to the repo's verification
  convention, not just to this pass's habits. The instance is cheap to fix; the
  blind spot is what actually cost eleven days. *(auto-selected)*
- **DEC-809** — Do not touch `examples/samsung-ttc_combined-decision.example.json`.
  Carried unchanged from `DEC-706` / `CON-001` across every prior pass.
  *(auto-selected)*

## 6. Assumptions & constraints

- **ASM-801** — The three red CI runs fail *only* at `Lint (ruff)`; `Install
  dependencies` succeeded on both the 3.10 and 3.12 legs in each. I read the step
  list for all three runs. So the mypy and pytest legs are **unverified in CI
  since 2026-07-24** — they may be green, but no run has reached them. Fixing the
  lint step could surface further failures behind it; plan for that rather than
  assuming a one-step fix.
- **ASM-802** — I attribute the 766 violations to ruff's expanded defaults rather
  than to code changes. Evidence: the same tree under the classic default select
  (`E4,E7,E9,F`, `E402` ignored) reports `All checks passed!`. I did not install
  the historical ruff release to confirm the exact version boundary.
- **ASM-803** — The EVN average retail price check (F7) used a web search, not a
  primary MOIT/EVN gazette source. It supports "no evidence of supersession," not
  "confirmed unchanged." The recommendation is the process fix; a proper
  primary-source verification is its own small task.
- **ASM-804** — Local suite timing moved from ~65 s (07-26) to 94–131 s. Test
  count also grew 589 → 634, so I do **not** claim a performance regression; the
  spread across my own runs (94 s vs 131 s) is wide enough that this is an
  observation to watch, not a finding. `load_vietnam_data()` at 2.8 ms/call is
  measured and is not a contributor.
- **ASM-805** — `webapp/prune.py` shows 0 % coverage, but it is a 23-line
  argparse wrapper over `RunStorage.prune`, which is covered (`storage.py` 93 %).
  Noted so the 85 % figure is not over-read; not proposed as work.
- **ASM-806** — I did not inspect the three stale branches' contents before
  proposing deletion. Theme F′ must confirm nothing unique is on them first;
  `real-project-data` in particular is referenced by `AGENTS.md` §6.
- **CON-801** — Samsung/TTC bit-exact parity remains inviolable as a *goal*;
  nothing here relaxes `CON-001`. Theme F′ changes how the divergence is
  *reported*, never the golden.
- **CON-802** — `CON-002` holds: the webapp must never fork analytics.
  `test_samsung_ttc_web_api_matches_direct_library_call_bit_exact` enforces this
  today and must survive any Theme I refactor.
- **CON-803** — `CON-004` holds: `ContractParams` has 24 call sites across 14
  files; no field may be renamed or made required.
- **CON-804** — Windows-first repo. Theme H's changes are CI/config only.
- **CON-805** — Analysis-only pass. No code was modified; the only file written
  is this brainstorm. (`phase6_test.log` was already untracked in the working
  tree at session start and was left alone — though `.gitignore` covering root
  `*.log` would be a one-line courtesy during Theme F′.)

## 7. Out of scope

- Executing any of the above (brainstorm-only workflow).
- Rotating the NREL API key — an out-of-band human action (see Q-801).
- Adjudicating which VND/USD rate is contractually correct per deal; unchanged
  from `ASM-005`, still needs deal documents rather than repo inspection.
- Re-litigating the Samsung parity divergence's root cause. PHASE-03 timeboxed
  and documented it in `reports/2026-07-26-samsung-parity-diagnosis.md`; this
  pass only addresses how it is *reported*.
- Multi-tenant auth, cloud hosting, containerization.
- Reviving the Julia path. `DEC-004` / `DEC-705` (archive in place) stands and
  PHASE-06 executed it cleanly.

## 8. Open questions (with adopted defaults, since no input is solicited)

1. **Q-801 (was Q-701/Q-601/Q-402 — open across EIGHT sessions, 26 days):** Has
   the NREL key from commits `3911032` / `b14bc0b` been rotated?
   - *Adopted default:* assume **no**. `README.md` documents the requirement;
     nothing records a rotation. It remains the single most overdue mechanical
     item in the repo and the only one that cannot be closed from inside it.
2. **Q-802 (new):** Was the red CI known and accepted, or unnoticed?
   - *Adopted default:* **unnoticed.** `activeContext.md` states "CI status:
     Green on `main`" and the phase-1/2 final report claims "ruff + mypy clean",
     both of which read as sincere local-verification results rather than an
     accepted-failure decision. Treating it as unnoticed is also the safer
     reading, since it implies the workflow fix (DEC-808) is needed either way.
3. **Q-803 (new):** Should the ruff config adopt the expanded default rule set
   permanently, or pin to the narrow historical one?
   - *Adopted default:* **adopt the expanded set** and pin the version. The
     expanded rules found real things (`BLE001`, `S110`, `DTZ001`) and the
     annotation modernizations are safe on a `from __future__ import annotations`
     codebase. Pin so the *next* expansion is a deliberate upgrade, not an
     outage.
4. **Q-804 (new):** Which second deal should the offsite registry serve first?
   - *Adopted default:* **`ninhsim_solar_storage_60pct`** (DEC-805). If its
     `extracted` contract turns out to diverge too far from the Samsung shape,
     fall back to `dppa_case_1` (347 lines, 99 % covered) before considering
     `dppa_case_2`.
5. **Q-805 (carried, unanswerable from the repo):** Has any deliverable already
   gone to an external counterparty carrying a non-26,400 FX rate or Single-Owner
   reference-plant defaults?
   - *Adopted default:* unresolvable by inspection; the numbers half was answered
     by `reports/2026-07-24-single-owner-defaults-audit.md`, the send-history
     half needs a human. Flagging beats guessing.

## 9. Suggested next step

**If the next session's budget is small: Theme H.** Add a pinned `dev`
dependency group to `pyproject.toml`, point CI at it, run
`ruff check --fix src scripts tests` for the 606 auto-fixable violations, delete
the ~101 now-redundant `# noqa: E402` comments, triage the ~90 manual ones, and
confirm with `gh run list` — *not* with a local run — that both matrix legs go
green. That restores eleven days of unverified CI in a few hours and, with the
`gh run list` convention added to `AGENTS.md`, stops the same gap recurring.

**If there is room for one substantial item: Theme I steps 1–3** — adapt
`ninhsim_solar_storage_60pct` to the orchestrator contract, register it, and add
the non-Samsung tests. It is the smallest change that makes
`reopt_pysam_vn.analysis` a two-deal API, and it converts the oldest unstarted
theme in this repo's planning history into something with a diff attached.
