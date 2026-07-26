---
date: 2026-07-26
slug: reopt-pysam-post-backlog-architecture
kind: brainstorm
mode: unattended (no user input; all open choices self-resolved and flagged)
repo: reopt-pysam
branch: main @ 2137b6e
predecessors:
  - research/2026-07-11-reopt-pysam-next-level-brainstorm.md
  - research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md
  - research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md
  - research/2026-07-18-execution-debt-decree-243-brainstorm.md
  - research/2026-07-22-reopt-pysam-execution-unblock-brainstorm.md
  - research/2026-07-24-reopt-pysam-sixth-pass-brainstorm.md
---

# Brainstorm: reopt-pysam — Seventh Pass (post-backlog architecture)

## 0. Why this pass writes a roadmap when the last one said not to

`DEC-602` (2026-07-24) instructed future unattended passes to default to
**verify-and-execute** — "open the plan, run the next unexecuted phase" — rather
than write a seventh roadmap, *unless the verified state changes materially.*

It changed materially. As of `5b221c8` / `2137b6e` (2026-07-25) **the queue is
empty.** Every phase from both outstanding plans has shipped, `plans/active/`
has been swept, CI is green, and coverage reporting exists. There is no "next
unexecuted phase" to open. Verify-and-execute has nothing left to execute, so
the honest move is to re-derive direction — which is exactly the exception
`DEC-602` carved out.

This pass therefore spends its budget on (a) confirming the drained state with
live tools, and (b) surfacing findings that **no prior pass has named**, plus a
re-scoped version of the two themes that survived six passes unexecuted.

---

## 1. Verification refresh — what is true on 2026-07-26 (run live, not assumed)

| Claim | Verified | Evidence |
|---|---|---|
| Portable suite green | ✅ | `589 passed, 18 deselected, 3 xfailed, 1 warning in 64.86s` — reproduced locally on `.venv` (Py 3.12), same filter CI uses |
| Coverage instrumented | ✅ | `85%` total, 4,599 statements, per-module report available |
| `mypy` gate live | ✅ | `.github/workflows/ci.yml` step over `analysis/` + `webapp/` |
| `plans/active/` swept | ✅ | 9 active / 16 archived (was 20 active, ~90% historical) |
| `.gitignore` malformed glob fixed | ✅ | `ceba-review/*\[repo-checked\].pptx` — brackets now escaped |
| Two-part tariff sign error fixed | ✅ | `reopt/two_part_tariff.py` (157 lines) + 89 lines of tests, `docs/pitfalls.md` updated |
| Single Owner clean-slate flag exists | ✅ | `pysam/single_owner.py`, default-off, regression-guarded |
| Backlog drained | ✅ | no plan in `plans/active/` has unexecuted phases traceable to the 07-22 / 07-24 sprints |

**Unchanged and still open from prior passes:** the NREL key rotation
(commits `3911032` / `b14bc0b`) is still unconfirmed — now **seven sessions**,
15 days. Nothing in the repo records a rotation.

---

## 2. New findings — things no prior pass has named

Each was verified by direct inspection today. Ordered by how much a wrong
number costs a client.

### F1 — Currency fragmentation: the canonical FX rate exists, is registered in the manifest, and is never loaded

This is the largest correctness-adjacent defect I found, and it is invisible to
every existing test because every test is internally consistent.

- **Four different VND/USD rates are hardcoded across 17 Python files**
  (`src/` and `scripts/`): `26,400`, `26,000`, `25,450`, `25,000`.
  - `integration/dppa_samsung_ttc.py:90` → `26_400.0`
  - `integration/dppa_case_3.py:65` → `25_450.0`
  - `integration/dppa_case_2.py:668,801,968` → `25_000.0` (fallback)
  - `reopt/two_part_tariff.py:23` → `26_000.0`
  - `reopt/preprocess.py:43` → `26_400.0` (`DEFAULT_EXCHANGE_RATE`)
  - …plus 12 more under `scripts/`.
- **The spread is 5.6%** (25,000 → 26,400). Every USD-denominated NPV, IRR,
  LCOE, and $/kWh figure this repo emits is scaled by whichever constant its
  module happened to hardcode. Cross-case artifacts —
  `generate_cross_project_dashboard.py`, `match_*.json`,
  `integration/procurement.py`, `integration/matching.py` — compare numbers
  built on **different denominators**. A 5.6% spread is larger, in relative
  terms, than several findings prior passes escalated.
- **A canonical source already exists and is orphaned.**
  `data/vietnam/vn_deal_defaults_2026.json` holds
  `exchange_rate.vnd_per_usd = 26400` with a proper source citation, is
  registered in `data/vietnam/manifest.json` under key `deal_defaults`, and is
  listed as `CURRENT` in `docs/regulatory-watch.md` — **but
  `load_vietnam_data()` never loads it.** It is absent from the loader's
  `required_keys` tuple and from the `VNData` dataclass
  (`reopt/preprocess.py:166–228`). The Julia twin ignores it too.
- **It could not be loaded as-is if someone tried.** Every other data file uses
  the documented `{_meta, data}` envelope, and the loader hard-fails without it
  (`raise KeyError(f'Data file {filename} missing "data" block')`).
  `vn_deal_defaults_2026.json` puts `exchange_rate` / `debt_terms` / `analysis`
  / `dppa` / `bess` / `sensitivity_ranges` at the **top level** with no `data`
  block. So the file silently violates the convention its own manifest entry
  implies, and adding it to the loader today would raise.

The net effect: the repo has a versioned-data-layer architecture, a canonical
FX value inside it, a manifest entry pointing at it, a regulatory-watch row
claiming it is current — and 17 files that ignore all of that.

### F2 — Policy constants are hardcoded in the settlement engine, and the Decree 243 fix worked *around* that rather than through it

`integration/settlement.py` is the generalized settlement engine (the GAP-04
deliverable). Its `ContractParams` dataclass carries **policy values as Python
defaults**:

```python
export_cap_pct: float = 20.0          # repealed by Decree 243/2026
surplus_rate_vnd_kwh: float = 671.0
dppa_adder_vnd_kwh: float = 523.34
kpp_pct: float = 2.7263
```

`export_cap_pct = 20.0` is the cap Decree 243/2026 **repealed** on 2026-06-26.
The data layer was correctly updated (`vn_export_rules_2026_decree243.json`,
`max_export_fraction: 0.50`, manifest flipped) — but the settlement engine never
reads the data layer at all. The 07-18 fix instead added a **fifth preset**
(`decree243_export_50pct_standard`) alongside three presets still pinned at
`20.0`. Any caller constructing `ContractParams` directly, or picking one of the
three legacy presets, still settles against the repealed cap.

This is the exact failure class the versioned data layer was built to prevent,
reappearing one layer downstream. It is also *structurally identical* to F1: a
canonical source exists, and the consuming module hardcodes instead.

### F3 — The repo's headline correctness guarantee is enforced nowhere

`README.md` and `docs/onsite_vs_offsite.md` both state that Samsung-TTC is
"parity-gated bit-for-bit". In reality
`tests/python/analysis/test_samsung_ttc_parity.py` is:

1. `pytestmark = pytest.mark.golden_machine` (module-level) → **excluded from
   CI** by the workflow's marker filter; **and**
2. both meaningful assertions —
   `test_samsung_parity_full_tree_within_bar` and
   `test_samsung_parity_is_bit_exact` — carry
   `@pytest.mark.xfail(strict=False)` → **do not fail locally either.**

So the flagship guarantee of the declared public API is asserted by
documentation and by nothing else. (The underlying divergence was correctly
diagnosed on 2026-07-22 as pre-existing, not a regression — that finding stands.
What is new here is that the *documentation was never reconciled* with the
double-disabled gate, so a reader of `README.md` today is told a false thing.)

**Related, and also new:** CI runs `pytest tests/python`. `tests/cross_language/`
and `tests/julia/` are **structurally outside that path** — not marker-excluded,
simply never collected. `docs/architecture.md` claims the Julia and Python
preprocessing twins "produce identical output (verified by Layer 3
cross-validation, max diff = 0.00e+00)". That verification runs only when a
human runs `tests/run_all_tests.ps1` locally. The twin invariant has no
automated enforcement anywhere.

### F4 — One script is unparseable on the minimum supported Python

`pyproject.toml` declares `requires-python = ">=3.10"`. CI runs 3.12 only.

`scripts/python/integration/generate_cross_project_dashboard.py:331` uses a
comment inside an f-string expression — **valid from Python 3.12, a hard syntax
error on 3.10 and 3.11**:

```
scripts\python\integration\generate_cross_project_dashboard.py:331:69:
invalid-syntax: Cannot use comments in f-strings on Python 3.10
```

Nothing catches this: the file is a script (not imported by any test), and no
linter or 3.10 job runs in CI. Either the floor is really 3.12 and
`requires-python` is wrong, or the file is broken. Both readings are bugs.

### F5 — The ruff backlog is now small enough that the CI comment blocking it is stale

`.github/workflows/ci.yml` carries a long comment explaining that a `ruff check`
step is deliberately omitted because the violation count "has been growing over
time" and cleanup is "a separate, larger follow-on effort". The live count:

| Rule | Count | Notes |
|---|---|---|
| `F401` unused-import | 48 | auto-fixable |
| `E402` import-not-at-top | 41 | mostly the deliberate `sys.path` + `# noqa` scripts pattern — configure, don't fix |
| `F821` undefined-name | 36 | **35 of them are one file**, `verify_ceba_dppa_deck.py`, using `Check` as an annotation that only exists via `getattr(module, "Check")`. Harmless at runtime (`from __future__ import annotations`), trivially fixed with a `TYPE_CHECKING` import |
| `F841` unused-variable | 28 | auto-fixable |
| `F541` f-string-no-placeholder | 16 | auto-fixable |
| others | 17 | incl. F4's real syntax error |
| **total** | **187** | **66 auto-fixable; ~120 collapse to two mechanical patterns** |

That is a half-day task with a `[tool.ruff]` block, not a "larger effort". The
comment's premise no longer holds, and the one violation that actually matters
(F4) is currently hidden behind it.

### F6 — Scaffolding that reads as architecture but is inert

- `reopt_pysam_vn/common/` — three modules (`currency.py`, `time_series.py`,
  `validation.py`), **8 statements total, 0% coverage, zero importers anywhere
  in `src/`, `scripts/`, or `tests/`**. It occupies the exact namespace where
  F1's canonical currency resolver belongs, which makes it actively misleading:
  a reader looking for "where does currency live" finds a stub.
- `data/schemas/deal_config.schema.json` — a complete, well-written JSON Schema
  for the public input type. **Never used to validate anything at runtime.**
  `DealConfig.from_dict` does one `mode` check; the only test that touches the
  schema (`test_types.py`) asserts the schema file is valid JSON. The declared
  public API accepts arbitrary dicts.
- `legacy/` — tracked directory, **empty**.

### F7 — Library/script boundary leak

`src/python/reopt_pysam_vn/integration/factory_a.py` — a library module, 52%
covered — prints seven lines of load statistics to stdout (lines 449–460). In
total, library code under `src/` has **15 bare `print()` calls across 5
modules**, while only **3 modules import `logging`**. The webapp imports this
package; anything it prints lands in the server's stdout uncorrelated with a run
id. This was noted at "14 prints" in the 07-14 pass under Theme C; that theme
shipped the *webapp's* logging story but never cleaned the library's.

---

## 3. Themes — the roadmap this pass proposes

### Theme E (new, and now the highest-leverage single change) — One canonical assumptions resolver

F1, F2, and half of F6 are the same defect wearing three costumes: **there is no
single function that answers "what assumption applies to this deal?"** Modules
each answer it locally, by hardcoding.

Proposed shape — small, testable, and it makes the existing data layer actually
load-bearing:

1. Fix `vn_deal_defaults_2026.json` to use the `{_meta, data}` envelope every
   other file uses (it is the only file that doesn't, and the loader would
   reject it today).
2. Add `deal_defaults` to `VNData` + `load_vietnam_data()`'s `required_keys`;
   mirror in `src/julia/REoptVietnam.jl`.
3. Promote `reopt_pysam_vn/common/` from stub to real: an `assumptions`
   resolver exposing `exchange_rate()`, `export_cap_fraction(regime)`,
   `surplus_rate()`, `dppa_adder()`, `kpp()` — all reading `VNData`, all
   overridable per-call.
4. Make `ContractParams`' policy fields **required, not defaulted** (or defaulted
   *from* the resolver), so a caller cannot silently settle against a repealed
   cap. Rebuild the five presets on top of the resolver.
5. Migrate the 17 FX-hardcoding files. **Critically: do this as a
   value-preserving refactor first** — pass each module's current constant in
   explicitly, prove byte-identical output against existing tests and goldens,
   *then* flip them to the canonical value as a separate, deliberately
   numbers-changing commit with a delta memo. Conflating the two would blow up
   every golden at once with no way to attribute the change.

Estimated blast radius: high (it moves published numbers), which is exactly why
it needs the two-commit discipline above and why it should land *before* more
deliverables are generated on divergent denominators.

### Theme A (carried from 07-14, still unexecuted, still #1 structurally) — Config-driven case runner + reporting pipeline

Six passes have named this; none has started it. New evidence quantifying it:

- **106 scripts** under `scripts/python/{reopt,pysam,integration}/`.
- **34 of them are `generate_*` report builders totalling 10,189 lines**, of
  which **9 embed a full hand-rolled HTML document** (`<style>` block, fonts,
  cards, Chart.js wiring) — nine independent copies of the same page chrome.
- The largest bespoke source module remains `integration/dppa_case_2.py` at
  **1,481 lines** (Samsung is 1,060) — and it is the *ungated* one.
- The pattern is unchanged: every new deal or deck spawns a new hand-written
  file rather than a config + a shared engine run.

The decomposition is the same one 07-14 specified — a declarative deal/deliverable
descriptor plus `python -m reopt_pysam_vn.report`. What this pass adds is the
sequencing argument: **Theme E should land first.** A reporting pipeline built
on top of 17 divergent FX constants would bake the divergence into the
template layer and make it permanent.

### Theme B (carried from 07-14, still undecided) — Julia keep-or-archive

Still ambiguous, still zero-risk to defer, but this pass adds two facts that
should settle it:

1. **The twins have already diverged in scope.** Python has
   `reopt/two_part_tariff.py`, `reopt/decree243_delta.py`,
   `reopt/regime_impact.py`, `reopt/regime_runner.py` — the Julia module has no
   counterpart for any of them. `docs/architecture.md` still presents the two as
   equivalent implementations.
2. **The equivalence claim is unenforced** (F3): Layer 3 lives outside the CI
   collection path entirely.

So the choice is no longer "keep vs archive a maintained twin" — it is "keep vs
archive a twin that is already a *subset* and whose subset-ness nothing checks."
`(auto-selected, unchanged from 07-14's DEC-104: B2 — archive in place under
legacy/julia/, rewrite the README stack section to lead with the NREL REopt API
+ PySAM, and keep Julia documented as the offline/no-API solve path. The Decree
57/243 export-cap JuMP constraint is genuinely Julia-only and is the one real
reason not to delete it — archiving preserves that.)`

### Theme F (new) — Make the declared public API an actual contract

`analysis/` was declared the supported surface on 2026-07-15 and given `mypy` +
`py.typed`. Two holes remain:

- **Wire `deal_config.schema.json` into `DealConfig.from_dict`** (F6) —
  structural validation with a clear error, `jsonschema` optional with a
  hand-rolled fallback so the runtime dependency stays optional as the schema's
  own description promises.
- **Reconcile the parity claim with reality** (F3). Two honest options: restore
  the gate (regenerate the golden on the current environment, drop the `xfail`,
  and find a CI-runnable form — e.g. commit the cached PVWatts resource so
  `golden_machine` stops being needed), or amend `README.md` and
  `docs/onsite_vs_offsite.md` to say the parity check is a local-only
  diagnostic. `(auto-selected: restore the gate. The bit-exactness is the single
  strongest correctness signal this repo has; downgrading the documentation
  instead of the risk is the wrong trade for a tool whose output goes to
  counterparties.)`

### Theme G (new, small) — Reproducibility floor

- **No lockfile, no `Dockerfile`, no `Makefile`/`justfile`, no `tox`/`nox`.**
  Dependencies are floors (`pandas>=2.0`) with one exception (`nrel-pysam==7.1.0`
  pinned in CI only, *not* in `pyproject.toml`).
- **CI tests exactly one Python version (3.12)** while claiming `>=3.10` — which
  is how F4 survived.
- `activeContext.md` documents a machine-specific `PYTHONPATH` collision with an
  unrelated `hermes-agent` venv as a standing gotcha. That is a symptom of no
  isolated, reproducible entrypoint.

Cheapest meaningful step: add 3.10 to the CI matrix (catches F4 immediately),
move the PySAM pin into `pyproject.toml`, and add `[tool.ruff]` + the `ruff`
step (F5). All three are hours, not days.

### Carried, unchanged — webapp → deck export

The 07-24 pass's Finding A (the analyst-facing webapp cannot emit the PPTX the
client actually receives) stands, unchanged and unstarted. Its sequencing
argument also stands: it is a *consumer* of Theme A's reporting pipeline, not a
substitute for it.

---

## 4. Suggested sequencing

| # | Item | Size | Why here |
|---|---|---|---|
| 1 | Theme G quick wins: 3.10 in CI matrix, PySAM pin into `pyproject.toml`, `[tool.ruff]` + ruff step, fix F4 | hours | Catches a real bug today; retires a stale CI comment; makes every later refactor safer |
| 2 | Theme F: schema validation on `DealConfig`; decide + execute the parity-gate reconciliation | ~1 day | Cheap, and F3 means the docs are currently wrong — that is a truth defect, not a feature gap |
| 3 | **Theme E: canonical assumptions resolver** (two-commit discipline) | ~2–3 days | Highest-value correctness work; must precede any new deliverable generation |
| 4 | Theme B: archive Julia in place, rewrite README stack section | ~half day | Removes a standing ambiguity; blocked by nothing |
| 5 | Theme A: config-driven case runner + reporting pipeline | multi-sprint | The structural fix; strictly better after #3 |
| 6 | webapp → deck export | ~1 sprint | Consumer of #5 |

---

## 5. Decisions self-resolved this pass (no user input was solicited, per workflow)

- **DEC-701** — Write a roadmap despite `DEC-602`. The backlog being drained is
  the material state change `DEC-602` itself carved out. *(auto-selected)*
- **DEC-702** — Theme E (assumptions resolver) ranks above Theme A (case runner),
  reversing six passes of ordering. Rationale: Theme A builds a template layer;
  building it over 17 divergent FX constants makes the divergence structural.
  *(auto-selected)*
- **DEC-703** — The FX migration is **two commits**: value-preserving refactor
  (explicit pass-through of each module's current constant, goldens unchanged),
  then a separate value-changing flip with a delta memo. Never one commit.
  *(auto-selected — this repo's own `lessons.md` 2026-06-12 entry is exactly
  this mistake in a different domain.)*
- **DEC-704** — Restore the Samsung parity gate rather than downgrade the
  documentation (Theme F). *(auto-selected)*
- **DEC-705** — Theme B stays B2 (archive in place), unchanged from 07-14's
  DEC-104, now with divergence evidence supporting it. *(auto-selected)*
- **DEC-706** — Do not touch the `examples/samsung-ttc_combined-decision.example.json`
  golden as part of Theme E. If the FX flip moves it, that is a deliberate,
  separately-reviewed regeneration. *(auto-selected; preserves CON-601 from
  every prior pass.)*
- **DEC-707** — `common/` is promoted, not deleted. It is the correct namespace
  for the resolver and deleting-then-recreating it would churn imports.
  *(auto-selected)*

## 6. Assumptions & constraints

- **ASM-701** — The green local run (`589 passed … 64.86s`) reflects `main` at
  `2137b6e`; I ran it myself rather than trusting `activeContext.md`.
- **ASM-702** — The 5.6% FX spread is a *comparability* defect with certainty;
  whether any *individual* published number is wrong depends on which rate that
  deal's counterparty actually contracted at. I did not attempt to adjudicate
  which of the four rates is "right" per deal — that needs deal documents, not
  repo inspection. Theme E's step 5 is deliberately structured so this can be
  decided per-module at flip time.
- **ASM-703** — `verify_ceba_dppa_deck.py`'s 35 `F821`s are annotation-only and
  harmless at runtime; I confirmed `from __future__ import annotations` is
  present and that `Check` is resolved dynamically via `getattr`. Not a live bug.
- **ASM-704** — `analysis/__main__.py` reporting 0% coverage is a measurement
  artifact (`test_cli.py` drives it as a subprocess), not an untested CLI. Noted
  so the 85% figure is not over-read.
- **CON-701** — Samsung/TTC bit-exact parity remains inviolable (carried from
  every prior pass). Theme F *restores* it; nothing here relaxes it.
- **CON-702** — Windows-first repo. Theme G's CI matrix addition is
  Linux-runner-only and changes nothing locally.
- **CON-703** — Analysis-only pass. No code was modified; the only file written
  is this brainstorm.

## 7. Out of scope

- Executing any of the above (this is a brainstorm-only workflow).
- Adjudicating which VND/USD rate is contractually correct for each deal —
  needs external documents (see ASM-702).
- Multi-tenant auth, cloud hosting, deployment packaging beyond Theme G's
  reproducibility floor.
- Re-deriving Theme A's decomposition in detail — 07-14 specified it; this pass
  only re-sequences it and adds census numbers.
- Touching goldens or `activeContext.md`.

## 8. Open questions (with adopted defaults, since no input is solicited)

1. **Q-701 (was Q-601/Q-402 — open across SEVEN sessions, 15 days):** Has the
   NREL key from commits `3911032` / `b14bc0b` been rotated?
   - *Adopted default:* assume **no**. `README.md` documents the requirement
     (that part shipped), but nothing records a rotation. Still the single most
     overdue mechanical item, and now the only pre-existing backlog item that
     survived the drain.
2. **Q-702 (new):** Is the real minimum Python 3.10 or 3.12? F4 says the code
   believes 3.12; `pyproject.toml` says 3.10.
   - *Adopted default:* **3.10 is the intended floor** (it is the declared
     contract and `mypy` is configured for `python_version = "3.10"`), so F4 is
     a bug in the script, not in the declaration. Fix the f-string; add 3.10 to
     CI to keep it fixed.
3. **Q-703 (new):** Which of the four FX rates should become canonical?
   - *Adopted default:* **26,400**, sourced from
     `vn_tariff_2025.json._meta.exchange_rate_vnd_per_usd` and already mirrored
     in `vn_deal_defaults_2026.json` with a citation (Decision 599/QD-EVN). It is
     the majority value, the only one with provenance, and the value both
     `preprocess.py` and the Julia twin already use as their fallback. Deals with
     a contractually fixed different rate should carry it as an explicit
     per-deal override, not as a module constant.
4. **Q-704 (carried, unanswerable from the repo):** Has any Samsung/TTC or
   CEBA-deck deliverable already gone to an external counterparty carrying
   Single-Owner reference-plant defaults, or a non-26,400 FX rate?
   - *Adopted default:* cannot be resolved by inspection. The 07-24 audit
     (`reports/2026-07-24-single-owner-defaults-audit.md`) answered the *numbers*
     half; the *send-history* half needs a human. Flagging beats guessing.

## 9. Suggested next step

If the next session's budget is small: **Theme G item 1** — add Python 3.10 to
the CI matrix, move the `nrel-pysam==7.1.0` pin into `pyproject.toml`, add a
`[tool.ruff]` block plus the `ruff check` step, and fix the f-string comment at
`generate_cross_project_dashboard.py:331`. It converts a stale CI comment into a
working gate and fixes a genuine syntax error on the declared minimum Python, in
a few hours, with no numeric blast radius.

If there is room for one substantial item: **start Theme E at step 1–2 only** —
give `vn_deal_defaults_2026.json` the `{_meta, data}` envelope and wire it into
`load_vietnam_data()` + `VNData` + the Julia twin. That alone is additive, breaks
nothing, is fully testable, and turns the orphaned canonical FX value into
something the resolver in step 3 can actually read.
