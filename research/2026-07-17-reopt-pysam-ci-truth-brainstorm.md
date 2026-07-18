---
title: "reopt-pysam: CI truth, small-project finance gap, and the execution backlog"
date: "2026-07-17"
type: "brainstorm"
depth: "standard"
source_request: "unattended orchestrator: analyze reopt-pysam state and brainstorm next-level improvements"
slug: "reopt-pysam-ci-truth"
supersedes: none
complements:
  - "research/2026-07-11-reopt-pysam-next-level-brainstorm.md"
  - "research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md"
---

# Brainstorm: reopt-pysam — CI Truth, Small-Project Finance Gap, and the Execution Backlog

> Produced **unattended** on 2026-07-17. Every open decision was self-answered with
> the option I would have recommended, tagged `(auto-selected)`. No human input.
>
> **Relationship to prior brainstorms.** This is the third next-level pass. The
> 2026-07-11 brainstorm diagnosed foundation debt (security, CI, hygiene, offsite
> generalization); the 2026-07-14 overlay added the strategic themes (ops readiness,
> type gate, offline solve, Julia archive, config-driven case runner). Both remain
> substantially correct and I do not rehash them. This document contributes:
> (1) a verification refresh of what actually shipped since 07-14, (2) **three new
> findings unique to this pass** — a red-on-main CI gate, a PySAM Single Owner
> wrapper defect surfaced by the KBC cross-check, and convention decay in the
> scripts layer — and (3) a re-prioritized forward roadmap that folds all three
> documents into one execution order.

---

## 1. Verification refresh — what changed since 2026-07-14

Checked directly against the working tree, git history, and live GitHub Actions runs today.

| Item | Status 2026-07-14 | Status today (2026-07-17) | Evidence |
|---|---|---|---|
| Strategic-lens PHASE-01 (ops readiness) | planned | **SHIPPED** | commit `d8349e6`; `webapp/{logging_config,errors,prune}.py` exist; `storage.py` has `write_provenance`/`get_provenance` |
| Strategic-lens PHASE-02 (type gate + CI) | planned | **SHIPPED** | commit `7255ca9`; `.github/workflows/ci.yml` (mypy on `analysis`+`webapp`), `py.typed`, mypy overrides in `pyproject.toml`, AGENTS.md §5 public-API rule |
| Strategic-lens PHASE-03 (offline solve), PHASE-04 (Julia archive), PHASE-05 (config runner `run_case`), PHASE-06 (settlement perf) | planned | **NOT STARTED** | no `run_case` / `--offline` in `analysis/__main__.py`; `src/julia/` still at root; Julia still README headline |
| 2026-07-11 foundation plan P0 security (rotate leaked NREL key) | open | **STILL OPEN** | key recoverable from commits `3911032`, `b14bc0b` |
| ruff configuration + lint paydown | open | **STILL OPEN** | no `[tool.ruff]` in `pyproject.toml`; ci.yml carries an explicit "ruff intentionally omitted, 181 violations" comment |
| Tracked deck binaries | open | **STILL OPEN** | `git ls-files` shows 3 `ceba-review/*.pptx`; the `.gitignore` glob `ceba-review/*[repo-checked].pptx` is a **character class**, not a literal — it can never match the intended filename (see §4.3) |
| 5 red benchmark tests | open, unowned | **STILL OPEN — and worse in CI** (see §2) | CI run `29559973037` |
| Two-part tariff energy-rate reduction gap | newly documented | **documented, fix not implemented** | commit `3d61d64` documents it; `two_part_tariff_sensitivity.py` unchanged |
| requirements.txt vs pyproject drift | drifted | **contents now identical, duplication remains** | both list the same 6 deps; still two sources of truth |
| New since 07-14 | — | untracked `scripts/python/2026-07-17_kbc_proforma_pysam_crosscheck.py` at the **flat path** (violates the canonical-subdir rule), referencing a plan file that does not exist in this repo | `git status`; `plans/2026-07-17-kbc-feedback-package-update-plan.md` absent |

**Bottom line:** the strategic-lens plan is 2/6 phases executed; the foundation
plan's security/hygiene P0 has now been open across three brainstorm cycles. The
repo does not primarily need new ideas — it needs the already-agreed queue executed.
That said, this pass found three genuinely new problems, below.

---

## 2. NEW FINDING (headline): the CI gate is red on main — and lying by omission

The 2026-07-15 phase-2 commit added `.github/workflows/ci.yml` and the local
verification recorded "5 known pre-existing failures." But the **actual GitHub
Actions runs on main fail**: run `29559973037` (2026-07-17, HEAD = `3d61d64`)
finished **22 failed, 525 passed, 30 skipped**. Both post-merge runs are red.
So the repo currently has a CI badge-shaped object that provides *negative*
assurance: a future regression cannot turn CI red because it already is.

Failure taxonomy from the CI log (verified, not guessed):

1. **Local-artifact dependencies (~9+ failures).** Tests read
   `artifacts/results/saigon18/2026-03-23_..._reopt-results.json` — `artifacts/`
   is git-ignored by design (2026-06-12 de-bloat), so these tests can *never* pass
   on a fresh clone. The de-bloat made the suite machine-bound and nobody noticed
   because the suite was only ever run on the one machine that has the artifacts.
2. **PySAM version drift (~1+).** `Pvwattsv8 has no attribute 'new'` — CI installs
   whatever `nrel-pysam>=7.1` resolves to today on ubuntu/py3.12, which differs
   from the local pinned reality (PySAM 7.1.0 in `.venv`). The floor-only
   constraint means CI tests a different engine than production.
3. **Samsung parity is not portable (3).** `test_samsung_ttc_parity` fails in CI
   with max relative diff **1.12** (112%!) — the "bit-exact" golden gate is only
   bit-exact on the local machine (its PVWatts resource files / artifacts). In CI
   it degenerates into noise. The parity gate that CON-001 treats as inviolable
   does not actually exist off-machine.
4. **Environment-behavior tests (2).** `test_regime_engine_smoke` expects
   `scenario_built_no_solve` but gets `error` — behavior forks on missing local
   state.
5. **The 5 locally-known red tests** ride along on top.

Also: ci.yml runs `pytest -m "not network"`, but **no `network` marker is
registered and no test carries one** (ASM-005's binding default in the 07-14 plan
was simply not implemented) — the filter selects everything.

**Why this is the top finding:** every future initiative (config runner refactor,
Julia archive, offline mode) is explicitly gated on "full suite green / CI
protects the refactor" (lessons.md structural-move rule, plan ASM-001). With CI
red-by-construction, that protection is fictional and the whole roadmap's safety
argument collapses.

**Proposed fix (one focused sprint, ~half day):**
- Register three pytest markers in `pyproject.toml`: `network` (real HTTP),
  `requires_artifacts` (reads git-ignored `artifacts/`), `golden_machine`
  (bit-exact parity vs local resource). Mark the offending tests (the CI log is
  the exact worklist).
- CI runs `-m "not network and not requires_artifacts and not golden_machine"`.
  Parity stays enforced **locally** via `run_all_tests.ps1` and as a documented
  pre-merge ritual; CI enforces everything portable.
- Pin `nrel-pysam==7.1.0` in CI (or in `[project.optional-dependencies].dev`) so
  CI tests the engine actually used.
- Triage the 5 local reds at the same time: each becomes either a fixed test, an
  `xfail(reason=..., strict=False)` with an owner note, or a recalibrated
  tolerance (per lessons.md: calibrate to reality via exploratory diff).
- Longer-term (ties to strategic-lens PHASE-03): the offline/frozen-resource mode
  is what eventually lets CI run the *full* pipeline honestly — this sprint is the
  bridge, not the destination.

`(auto-selected: marker-quarantine + pin now, rather than waiting for PHASE-03
offline mode to make everything portable — a red gate today is worse than a
narrower green gate today.)`

---

## 3. NEW FINDING: PySAM Single Owner wrapper is miscalibrated for small projects

The untracked `2026-07-17_kbc_proforma_pysam_crosscheck.py` had to **re-implement**
`reopt_pysam_vn.pysam.single_owner.run_single_owner_model` because the shared
wrapper leaves SAM's Single Owner defaults untouched — and those defaults are
calibrated for a ~100 MW reference plant: `construction_financing_cost` defaults
to a **flat $2,866,500**, plus nonzero insurance rate, debt fees/closing costs,
working/DSCR reserves, and property tax. For the sub-2 MWp KBC projects these
defaults swamp the economics (the script's docstring: NPV/IRR "far more negative
than the workbook's cost/OM structure can explain").

This is not a script problem — it is a **library defect** affecting every small
C&I-scale run through `pysam/single_owner.py`, which is exactly the project class
this repo models (rooftop C&I, 1–10 MWp). The offsite DPPA path's developer
finance numbers deserve an audit for the same contamination.

**Proposed fix:**
- Add an explicit, tested "clean-slate" mode to `single_owner.py` (e.g.
  `SingleOwnerInputs.zero_us_reference_defaults: bool = True` or a
  `configure_small_project(financial_model)` helper) that zeroes
  construction financing, insurance, debt fees, reserves, and property tax unless
  the caller sets them. Mirrors the existing REopt-side philosophy ("US federal
  incentives apply by default even for non-US sites — zeroed by preprocessing").
- Unit test asserting the zeroed fields, plus a characterization test that a
  small-project IRR from the wrapper matches a hand-computed `numpy_financial`
  cash flow within tolerance.
- **Audit** `dppa_samsung_ttc` / case modules' Single Owner usage: if they inherit
  the same defaults, either the golden numbers embed a hidden $2.87M phantom cost
  (a real modeling error worth a documented restatement) or they already override
  it (then document where). Do the audit read-only first — Samsung parity is
  bit-exact-gated, so any correction is a *deliberate, documented* golden refresh,
  never a silent one.
- Promote the one-off script itself to the canonical path
  (`scripts/python/pysam/`) or into `tests/` as a characterization fixture; a
  dated flat-path throwaway that discovered a library bug is exactly the artifact
  that should not evaporate.

`(auto-selected: default the clean-slate behavior ON for new callers but keep the
current behavior reachable behind a flag, with the Samsung path audited before
any default flip that could touch parity.)`

---

## 4. NEW FINDING: convention decay — the guardrails are documentation, not machinery

Three small observations that share one root cause: repo conventions live in
markdown, and markdown does not enforce itself.

1. **Flat-script rule already violated.** The canonical-path rule ("scripts live
   only under `scripts/python/{reopt,pysam,integration}/`", 2026-06-12) lasted
   five weeks before today's `scripts/python/2026-07-17_*.py` landed at the flat
   level. Trivial fix: a 10-line CI check (or pre-commit) failing on `scripts/python/*.py`
   glob matches. Same pattern available for "no new bare `print()` in
   `src/`", "no tracked files under `artifacts/`".
2. **Root screenshots are now tracked.** `phase04_new_deal_*.png` (0.5 MB) got
   committed to the repo root — the 07-11 brainstorm flagged them as stray; instead
   of deletion they were immortalized. Move to `docs/worklog/` assets or delete.
3. **The `.gitignore` pptx glob is broken syntax.** `ceba-review/*[repo-checked].pptx`
   is a glob **character class** (matches one char from `{r,e,p,o,-,c,h,k,d}`), not
   a literal `[repo-checked]` suffix — it also hard-crashes ruff's parser (per the
   ci.yml comment). The escaped form `ceba-review/*\[repo-checked\].pptx` is what
   was meant; and the files are tracked anyway, so the ignore is doubly moot until
   `git rm --cached` runs (07-11 plan P0 territory).

**Theme:** each item is minutes of work, but collectively they show that
"documented convention + discipline" has a measured half-life of weeks in this
repo. The fix is to make the two or three highest-value conventions *mechanical*
(CI checks), which is also exactly what the type gate did successfully for the
public-API boundary. `(auto-selected: add a small "repo-invariants" CI step —
flat-script check, tracked-artifacts check, root-binary check — as part of the §2
CI-truth sprint.)`

---

## 5. Secondary observations (new or sharpened this pass)

- **Two-part tariff fix is the highest-value *small* model change.** The gap is
  fully specified (commit `3d61d64`, activeContext §Known model gaps, script
  docstring): re-price the 8760 energy series with the trial Ca rates before
  adding the Cp demand charge. The current script **gets the sign of the answer
  wrong** for high-load-factor sites (+73B VND/yr claimed cost vs −53B VND/yr
  actual saving for Saigon18). For a firm advising clients on the Decree 146/2025
  two-part tariff trial, this is a wrong-recommendation risk sitting in a tracked
  script. It is also perfectly TDD-shaped: the docstring's worked numbers are the
  failing test. Estimated effort: half a day including tests.
- **The webapp now writes provenance but the UI does not show it.** PHASE-01
  shipped `provenance.json` (solver, cache hit, policy vintage, wall time) and a
  prune command; the natural next 10% is surfacing provenance on `/runs/{id}`
  (a small "About this run" card) and exposing prune/queue-depth in the UI —
  cheap trust-building for the non-technical users the app exists for.
- **KBC-style workbook cross-checks are becoming a genre.** This is the third
  "validate an external deck/workbook against the repo" exercise (ceba-deck, July
  deck, now KBC pro formas). Each spawned bespoke scripts. When strategic-lens
  PHASE-05 builds the reporting pipeline, "cross-check an external claim set
  against a repo run" deserves to be a first-class subcommand (a
  `checks.json` registry pattern already exists in `ceba_deck/`), not a fourth
  hand-rolled script family.
- **REopt energy-accounting footnote worth one doc paragraph.** The KBC script
  notes `year_one_energy_produced_kwh` vs `annual_energy_produced_kwh` differ by
  ~4.5% in REopt outputs (degradation-year convention). That trap will bite again;
  it belongs in `docs/pitfalls.md`.
- **Julia ambiguity now has a third data point.** Still untouched since
  2026-05-19; CI (ubuntu) does not install it; the KBC work didn't touch it. Every
  week of drift strengthens the 07-14 archive-in-place call (DEC-104). No new
  decision needed — just execute PHASE-04 after the CI-truth sprint.
- **Memory hygiene:** `plans/2026-07-17-kbc-feedback-package-update-plan.md` is
  referenced by the new script but exists in some *other* repo/session. Either
  copy the plan in, or fix the docstring reference — dangling cross-repo pointers
  in committed code rot fast.

---

## 6. Re-prioritized forward roadmap (folding all three brainstorms)

Ordering principle: restore the safety net first (it was believed to exist and
does not), then ship the highest-value small correctness fix, then resume the
already-planned strategic phases.

| # | Initiative | Source | Size | Why this order |
|---|---|---|---|---|
| P0a | **CI-truth sprint**: markers (`network`/`requires_artifacts`/`golden_machine`), pin `nrel-pysam==7.1.0` in CI, triage the 5 local reds (fix/xfail-with-owner/recalibrate), repo-invariants CI step (§4) | NEW (§2, §4) | 0.5–1 day | Everything downstream assumes a green gate; today's gate is red-by-construction |
| P0b | **Security/hygiene**: rotate the leaked NREL key, `git rm --cached` the pptx binaries + fix the gitignore glob, relocate/delete root PNGs, single dependency source (drop `requirements.txt` or generate it) | 07-11 plan | 0.5 day | Third cycle open; the key is live in public history |
| P1 | **Two-part tariff Ca re-pricing fix** (TDD off the documented worked example) | activeContext gap | 0.5 day | Sign-flipping client-facing correctness bug, fully specified |
| P2 | **Single Owner clean-slate mode + Samsung finance audit** (§3) | NEW | 1 day | Library-level correctness for the repo's core project class; audit before any golden change |
| P3 | **Strategic-lens PHASE-03**: offline/frozen-resource solve mode | 07-14 plan | 1–2 days | Makes CI honest end-to-end; unblocks demos; prerequisite quality-of-life for PHASE-05 |
| P4 | **Strategic-lens PHASE-04**: Julia archive-in-place + doc honesty | 07-14 plan | 0.5 day | Reversible; kills the stack ambiguity |
| P5 | **Strategic-lens PHASE-05**: config-driven case runner + reporting pipeline, proven on `dppa_case_2` behind characterization tests; fold in a `crosscheck` subcommand (§5) | 07-14 plan | 1–2 weeks | The true "next level"; must not start before P0a restores the net |
| P6 | Settlement perf (measure-first), provenance UI card, docs (pitfalls ¶, analyst data dictionary) | 07-14 plan + §5 | opportunistic | Fill-in work between phases |

**One-line thesis:** the last two brainstorms correctly designed the product; this
pass found that the safety net those plans lean on (a green CI gate and a portable
parity test) does not actually exist off the primary machine — restore truth to
the gate first, fix the two live correctness defects (two-part tariff sign flip,
Single Owner phantom costs), then resume the planned strategic phases in order.

---

## 7. Resolved decisions (self-answered this pass)

- **DEC-201:** Fix CI by quarantining non-portable tests with explicit markers +
  pinning PySAM, rather than waiting for the offline mode to make them portable.
  A narrow green gate now beats a broad red one. *(auto-selected)*
- **DEC-202:** Keep Samsung bit-exact parity as a **local/pre-merge** gate
  (documented ritual + PowerShell runner), marked `golden_machine` in CI, until
  PHASE-03's frozen resources make it portable. CON-001 stays inviolable where it
  is actually enforceable. *(auto-selected)*
- **DEC-203:** Single Owner clean-slate defaults ON for new callers, legacy
  behavior behind a flag; Samsung/cases audited read-only before any change that
  could shift golden numbers; any needed restatement is explicit and documented.
  *(auto-selected)*
- **DEC-204:** Two-part tariff fix is promoted above all strategic-phase work —
  it is small, specified, and client-facing-wrong today. *(auto-selected)*
- **DEC-205:** Add a "repo-invariants" CI step for the conventions that have
  demonstrably decayed (flat scripts, tracked artifacts, root binaries).
  *(auto-selected)*
- **DEC-206:** Endorse (not re-derive) 07-11 P0 security and 07-14 PHASE-03/04/05
  in that order after P0a/P0b/P1/P2 land. *(auto-selected)*

## 8. Assumptions

- **ASM-201:** The two red CI runs on main (`29358882830`, `29559973037`) are
  representative — no secret/branch-protection nuance makes them expected-red.
  Verified only from run logs, not from repo settings.
- **ASM-202:** The KBC cross-check script's claim about Single Owner defaults is
  accurate as far as it goes (it cites direct inspection); §3's *library* fix
  still needs its own failing test first per TDD — the script is evidence, not
  proof.
- **ASM-203:** Nobody depends on CI currently exercising the artifact-dependent
  tests (they can never have passed in CI; there is nothing to preserve).
- **ASM-204:** The 07-17 KBC plan lives in another repo; nothing in *this* repo's
  roadmap depends on its contents beyond the script finding already captured here.

## 9. Open questions (with adopted defaults)

1. **Q-201:** Should Samsung parity ever run in CI at all, even post-offline-mode?
   *Default adopted:* yes, once PHASE-03 freezes the resource — a portable golden
   is the whole point of freezing.
2. **Q-202:** Does the Samsung/TTC golden embed the Single Owner US reference
   defaults (phantom $2.87M construction financing)? *Default adopted:* audit
   read-only first (P2); if contaminated, propose a documented golden restatement
   to the human rather than silently refreshing — this is the one item here that
   could change client-facing historical numbers.
3. **Q-203 (carried from 07-14 Q-101):** Julia archive veto — still assumed
   no local Julia solves; archive remains reversible.

## 10. Suggested next step

Run `/plan` over this brainstorm scoped to **P0a + P0b + P1 + P2** as a single
"truth and correctness" sprint (CI markers/pin, security/hygiene, two-part tariff
fix, Single Owner clean-slate + audit). It is roughly 3 days of work, has zero
architectural risk, and leaves the repo with an honest green gate — the
precondition every already-written strategic phase declares for itself.
