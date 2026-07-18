---
title: "reopt-pysam: execution debt, Decree 243/2026 regulatory currency, and webapp hardening"
date: "2026-07-18"
type: "brainstorm"
depth: "standard"
source_request: "unattended orchestrator: analyze reopt-pysam state and brainstorm next-level improvements"
slug: "execution-debt-decree-243"
supersedes: none
complements:
  - "research/2026-07-11-reopt-pysam-next-level-brainstorm.md"
  - "research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md"
  - "research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md"
  - "plans/2026-07-17-truth-and-correctness-sprint-plan.md"
---

# Brainstorm: reopt-pysam — Execution Debt, Decree 243/2026 Currency, Webapp Hardening

> Produced **unattended** on 2026-07-18 (fourth next-level pass). Every open
> decision was self-answered with the recommended option, tagged `(auto-selected)`.
>
> **Relationship to prior passes.** 07-11 diagnosed foundation debt; 07-14 added
> the strategic themes; 07-17 found the red CI gate, the Single Owner
> reference-plant defect, and convention decay — and produced a complete,
> executable 4-phase plan (`plans/2026-07-17-truth-and-correctness-sprint-plan.md`).
> This pass verified today's state against the working tree, live GitHub Actions,
> and a fresh full local test run. It contributes: (1) confirmation that **nothing
> from the 07-17 plan has been executed** — the top recommendation of this pass is
> to execute, not ideate; (2) one genuinely new headline finding — the data layer
> still encodes the **Decree 57 20% export cap that Decree 243/2026 superseded on
> June 26**, three weeks ago, despite the repo holding a research brief on the new
> decree since June 30; (3) fresh local test-suite ground truth; and (4) a short
> list of webapp hardening items no prior pass audited.

---

## 1. Verification refresh — what changed since 2026-07-17

Checked directly against the working tree, `git status`, live GitHub Actions, and a full local pytest run today.

| Item | Status 2026-07-17 | Status today (2026-07-18) | Evidence |
|---|---|---|---|
| Truth-and-correctness sprint (PHASE-01..04) | plan written | **NOT STARTED — and the plan itself is untracked** | `git status`: `plans/2026-07-17-truth-and-correctness-sprint-plan.md` and the 07-17 brainstorm are `??` (untracked); no pytest `markers` in `pyproject.toml`; `ci.yml` still filters only the unregistered `network` marker; PySAM still unpinned in CI |
| CI on `main` | red (22 failures) | **still red, no new runs** | `gh run list`: latest run is still `29559973037` (2026-07-17, failure); nothing has been pushed since |
| KBC cross-check script | untracked at forbidden flat path | **unchanged** — still `?? scripts/python/2026-07-17_kbc_proforma_pysam_crosscheck.py` | `git status` |
| Leaked NREL key rotation | open (3rd cycle) | **open (4th cycle)** | commits `3911032`, `b14bc0b` still in history; no README rotation note |
| Tracked pptx binaries, root PNGs, broken `.gitignore` globs, `requirements.txt` duplication | open | **unchanged** | `git ls-files`; `.gitignore` character-class globs intact |
| Two-part tariff sign-flip fix (PHASE-03) | specified | **not implemented** | `two_part_tariff_sensitivity.py` unchanged; gap still listed in `activeContext.md` |
| Single Owner clean-slate mode (PHASE-04) | specified | **not implemented** | `single_owner.py::_configure_financial_model` unchanged |
| Local test suite | 552 passed / 5 failed (2026-07-04 count) | **re-verified today — see §5** | fresh `pytest tests/python -q` run 2026-07-18 |

**Bottom line:** one calendar day has passed; zero execution has occurred. The
07-17 pass already concluded "the repo does not primarily need new ideas — it
needs the already-agreed queue executed." That conclusion now has a fourth data
point, plus a new risk: the entire sprint plan and its source brainstorm exist
only as untracked files on one machine. A stray `git clean -fd` erases three
days of planning.

---

## 2. NEW FINDING (headline): the data layer models a repealed export regime — Decree 243/2026 is missing

**The regulation changed on 2026-06-26; the repo researched it on 2026-06-30; the
data layer still encodes the old rule three weeks later.**

Decree 243/2026/ND-CP (effective June 26, 2026 — fully documented in the repo's
own `research/2026-06-30_decree-243-2026-nd-cp.md`) amends Decrees 57 and 58:

1. **Surplus export cap: 20% → 50%** as the general rule, with an explicit
   allowance to exceed 50% through Dec 31, 2030 where local grid capacity permits.
2. **BESS discharge charged from rooftop solar is now tradable surplus** — the
   first decree-level BESS-in-the-value-chain provision, directly relevant to
   this repo's PV+BESS sizing and IRR modeling.
3. **Surplus pricing formula codified**: prior-year average market price, capped
   at the utility-scale ground-mount solar ceiling tariff (ex-VAT) — different
   from the formula assumptions embedded in the current deck pipeline.

What the repo actually encodes today (verified in the working tree):

- `data/vietnam/vn_export_rules_decree57.json` → `rooftop_solar.max_export_fraction: 0.20`,
  `_meta.last_updated: 2026-02-18`.
- `src/python/reopt_pysam_vn/reopt/preprocess.py:682` defaults
  `max_export_fraction = rooftop.get("max_export_fraction", 0.20)` and even
  warns when a caller passes anything ≠ 0.20 (line 689) — the *new legal default*
  would trigger the "non-standard" warning.
- `vn_regime_registry_2026.json` (last updated 2026-05-07) has regimes for
  Decision 14/2025 and Decision 963/2026 — **no Decree 243 regime**.
- `grep -rn "243" src/` → zero hits. The decree exists only in `research/`.
- Case modules (`dppa_case_1.py` etc.) consume the ceiling tariffs and BESS
  incentive thresholds from this same file; the `sweep_56` scenarios and the
  July deck verification assumed the 20% cap (with 50% only as a draft
  sensitivity).

**Why this is the headline:** this is the same defect class as the two-part
tariff sign flip — a client-facing recommendation risk — but *fresher* and
structural: every onsite run through `apply_vietnam_defaults` since June 26 has
constrained exports to a cap that no longer exists, understating export revenue
and potentially mis-sizing PV/BESS. For a firm advising on Vietnam DPPA/rooftop
economics, "our model enforces a repealed decree" is exactly the kind of thing
the repo's own regime-registry machinery was built to prevent — and the
machinery works (the Decision 963 TOU update went through it cleanly in May);
it just wasn't fed.

**Proposed fix (0.5–1 day, TDD-shaped):**
- New versioned file `vn_export_rules_2026_decree243.json` (keep the Decree 57
  file untouched for reproducibility, per the data layer's own update policy);
  flip `manifest.json`'s `export_rules` key.
- New regime entry `decree_243_2026_current` in the regime registry with
  `export_rule_overrides` (50% cap, >50%-through-2030 toggle, new pricing
  basis); keep `decree_57_2025` reachable as a legacy regime for reproducing
  pre-June-26 results.
- Relax the `preprocess.py` ≠ 0.20 warning to key off the *active manifest
  value* rather than a hardcoded 0.20.
- Add the >50% transitional allowance and BESS-surplus-tradability as explicit
  scenario toggles, not silent defaults.
- Re-run the affected sensitivity sets (Saigon18 export-relevant scenarios,
  `sweep_56`) and publish a short delta memo — the July deck's numbers were
  produced under the 20% assumption and stakeholders should know the direction
  and rough magnitude of the change.
- One new pitfall paragraph in `docs/pitfalls.md` + a line in the tariff data
  `notes`.

`(auto-selected: new versioned data file + regime entry, never an in-place edit
of the Decree 57 file — matches the repo's own versioning policy and keeps old
results reproducible.)`

---

## 3. NEW FINDING (process): execution debt is now the binding constraint — and the plan is one `git add` from safety

Four brainstorm passes (07-11, 07-14, 07-17, today) have converged on
substantially the same queue. The 07-17 pass went further than any before it: it
produced a fully-specified, phase-gated, TDD-shaped plan with binding defaults
for every open question — explicitly designed so "any coding agent with zero
shared context" can execute it. Nobody has.

Concrete observations:

1. **The planning artifacts are untracked.** `plans/2026-07-17-truth-and-correctness-sprint-plan.md`,
   `research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md`, and the KBC
   cross-check script all sit as `??` in `git status`. They exist on exactly one
   machine, unprotected. First action of any next session: commit them (the
   script goes to its canonical path per the plan's TASK-01-09 in the same
   commit, or is committed as-is and moved in PHASE-01 — either is fine, losing
   it is not).
2. **The brainstorm→plan→brainstorm loop has a measurable cost.** Since 07-11,
   roughly three full analysis passes have been produced against zero executed
   phases. Meanwhile two of the defects those passes identified (two-part tariff
   sign, Single Owner phantom costs) remain live in client-facing scripts, and a
   third accumulated (Decree 243, §2). Each idle week also widens the CI-red
   window in which a genuine regression would be invisible.
3. **The orchestration pattern needs an execution mode.** If the unattended
   session budget allows only one activity, executing PHASE-01 of the existing
   plan (green CI gate, ~half day, zero architectural risk, independently
   verifiable exit criteria) is strictly higher value than a fifth analysis
   pass. This document deliberately adds only findings that change the queue
   (Decree 243) rather than re-deriving it.

`(auto-selected: recommend the next unattended session run the existing plan's
PHASE-01 verbatim instead of any further brainstorming; this pass changes the
roadmap only by inserting the Decree 243 refresh after the correctness phases.)`

---

## 4. NEW FINDINGS (minor): webapp hardening items no prior pass audited

The webapp is localhost-only, single-user, no-auth by design (documented in its
README), so none of these are urgent — but they are cheap and previously
uncatalogued:

1. **`run_id` path traversal.** `storage.py::_run_dir` does `self.root / run_id`
   with the `run_id` taken verbatim from the URL path (`/runs/{run_id}`,
   `?from=` clone param). A crafted id containing `..` segments resolves outside
   the runs root; the existence check plus fixed JSON filenames bound the blast
   radius (read-only, must hit a directory containing `status.json`), but a
   one-line validation — reject any `run_id` not matching the generator's own
   `^\d{8}T\d{6}\d*-\d{8}-[a-z0-9-]+-[0-9a-f]{6}$` shape, or simply containing
   `/`, `\`, or `..` — closes it. Add one test.
2. **Job-queue durability.** `jobs.py` holds the FIFO queue in memory and
   `status.json` on disk. If the process dies mid-solve (or with queued items),
   those runs are stranded in `queued`/`solving` forever — the UI polls a state
   that can never progress. Cheap fix: on `JobManager.start()`, sweep the run
   store for non-terminal states and either re-enqueue (idempotent thanks to the
   solve cache) or mark them `error("interrupted by restart — clone and re-run")`.
   `(auto-selected: mark-as-interrupted over auto-requeue — auto-requeue could
   silently re-spend NREL API quota on a run the user abandoned.)`
3. **Provenance is written but still invisible.** Carried from 07-17: `/runs/{id}`
   should render the `provenance.json` card (solver, cache hit, policy data
   versions, wall time). Note the nice interaction with §2: once the Decree 243
   data file lands, `policy_data_versions` in provenance will automatically
   distinguish pre/post-243 runs — but only if users can see it.
4. **Research-to-data currency has no tripwire.** The Decree 243 miss (§2)
   happened despite a research brief sitting in the repo for three weeks. The
   repo-invariants test module planned in PHASE-01 (TASK-01-08) is the natural
   home for a soft check: a `docs/regulatory-watch.md` table mapping each active
   `data/vietnam/*.json` file to its governing instrument and a "superseded-by"
   column, reviewed whenever a `research/` brief lands with a repo-impact
   section. Mechanical enforcement of *content* currency isn't possible, but a
   single tracked table turns "did we ingest the decree?" into a diffable
   question. `(auto-selected: lightweight tracked table over any automation —
   regulatory ingestion is a judgment call, the failure mode was visibility.)`

---

## 5. Test-suite ground truth (fresh run, 2026-07-18)

Two facts established by running tests today:

1. **The five known-red tests are still exactly the five documented on
   2026-07-04** — re-run directly (9 s, `--tb=no`):
   `test_samsung_parity_full_tree_within_bar`, `test_samsung_parity_is_bit_exact`
   (the third parity test, `headline_settlement_exact`, passes locally and fails
   only in CI), `test_pvwatts_capacity_factor_binh_thuan`,
   `test_build_extracted_inputs_cleans_load_and_computes_weighted_evn_benchmark`,
   `test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike` →
   **5 failed, 1 passed**. The PHASE-01 triage table in the 07-17 plan remains
   exactly correct; nothing has drifted further.
2. **The full local suite no longer finishes in 10 minutes.** A background
   `pytest tests/python -q` run was killed at the 600 s timeout. Root cause is
   almost certainly that with `NREL_API.env` present locally, the unmarked
   live-API tests (`test_commercial_rooftop_api_solve`, domain connectivity,
   regression-vs-baseline) execute real NREL solves at ~60 s+ each — in CI the
   same tests fail fast for lack of a key, which is why CI "finishes" in ~90 s.
   This is one more argument for PHASE-01's `network` marker: today the *local*
   feedback loop is slow precisely because the marker doesn't exist, and the
   2026-07-04 "552 passed" full-run figure likely came with a wall time nobody
   would accept as a pre-commit gate.

---

## 6. Re-prioritized forward roadmap (folding all four passes)

Ordering principle unchanged from 07-17 — restore the safety net, fix live
client-facing correctness defects, then resume strategic phases — with one
insertion (P1.5) and one preamble step (P-1).

| # | Initiative | Source | Size | Notes |
|---|---|---|---|---|
| P-1 | **Commit the planning artifacts** (07-17 plan + brainstorm + this file; KBC script to canonical path) | NEW (§3) | 10 min | Removes the single-machine loss risk before anything else |
| P0a | **Execute PHASE-01 of the 07-17 plan**: pytest markers, PySAM pin, hermetic webapp tests, red-test triage, repo-invariants test, flat-script relocation → green CI | 07-17 plan | 0.5–1 day | The plan is turn-key; run it verbatim |
| P0b | **Execute PHASE-02**: untrack binaries, fix `.gitignore` globs, drop `requirements.txt`, document key rotation | 07-17 plan | 0.5 day | Fourth cycle open |
| P1 | **Execute PHASE-03**: two-part tariff Ca re-pricing fix (TDD) | 07-17 plan | 0.5 day | Sign-flipping client-facing bug |
| P1.5 | **Decree 243/2026 data refresh**: new versioned export-rules file + regime entry + preprocess default fix + sensitivity delta memo (§2) | NEW | 0.5–1 day | Second live client-facing currency defect; slots naturally after P1 (same data file family as the tariff work) |
| P2 | **Execute PHASE-04**: Single Owner clean-slate mode + contamination audit | 07-17 plan | 1 day | Library-level correctness for the repo's core project class |
| P2.5 | **Webapp hardening batch**: run_id validation, interrupted-run sweep, provenance card, regulatory-watch table (§4) | NEW | 0.5 day | Bundle as one small phase; all test-backed |
| P3–P6 | Strategic-lens PHASE-03 (offline solve) → PHASE-04 (Julia archive) → PHASE-05 (config-driven case runner + crosscheck subcommand) → settlement perf/docs | 07-14 plan | 1–3 weeks | Unchanged; still gated on green CI |

**One-line thesis:** the analysis is done — three prior passes and a turn-key
plan agree on the queue; this pass adds one genuinely new correctness item (the
repo enforces an export cap repealed on June 26) and one process correction
(commit and *execute* the plan instead of writing a fifth one).

---

## 7. Resolved decisions (self-answered this pass)

- **DEC-301:** Commit the untracked 07-17 planning artifacts and this brainstorm
  before any other work; planning documents are repo assets, not scratch.
  *(auto-selected)*
- **DEC-302:** Decree 243 ingestion = new versioned data file + new regime-registry
  entry + manifest flip; the Decree 57 file is never edited in place; pre-243
  results stay reproducible via the legacy regime. *(auto-selected)*
- **DEC-303:** Scope the Decree 243 re-run to a delta memo on the export-sensitive
  scenario sets (Saigon18 export cases, `sweep_56`), not a full restatement of
  every historical artifact; goldens untouched (the Samsung/TTC path is
  offsite-CfD and does not consume the rooftop export cap). *(auto-selected —
  verify the golden's independence from export rules during implementation
  before relying on it.)*
- **DEC-304:** Interrupted webapp runs are marked `error` with a clear message on
  startup, not auto-requeued (protects NREL API quota). *(auto-selected)*
- **DEC-305:** The next unattended session should execute PHASE-01 of
  `plans/2026-07-17-truth-and-correctness-sprint-plan.md` rather than produce
  further analysis. *(auto-selected)*

## 8. Assumptions

- **ASM-301:** The VietnamNet-sourced Decree 243 provisions in the 06-30 research
  brief are accurate; implementation should re-verify the 50%/">50% to 2030"
  thresholds against the decree text or a second source before encoding numbers.
- **ASM-302:** No other session is mid-flight on the 07-17 plan (its files being
  untracked and CI unchanged are the evidence).
- **ASM-303:** The Samsung/TTC golden does not consume `max_export_fraction`
  (offsite CfD path) — checked only by code-path reading, not by run; DEC-303
  requires confirmation during P1.5.
- **ASM-304:** Today's fresh test run (§5) is representative of the machine state
  the 07-17 plan's PHASE-01 triage table assumes.

## 9. Suggested next step

Commit the planning artifacts (P-1), then execute
`plans/2026-07-17-truth-and-correctness-sprint-plan.md` PHASE-01. When the
sprint's four phases are done, run `/plan` over §2 of this document to turn the
Decree 243 refresh into its own small phase plan (P1.5) before resuming the
strategic-lens queue.
