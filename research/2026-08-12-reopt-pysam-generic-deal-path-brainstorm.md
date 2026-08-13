---
date: 2026-08-12
slug: reopt-pysam-generic-deal-path
kind: brainstorm
mode: unattended (no user input; all open choices self-resolved and flagged)
repo: reopt-pysam
branch: main @ 7155199
predecessors:
  - research/2026-07-11-reopt-pysam-next-level-brainstorm.md
  - research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md
  - research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md
  - research/2026-07-18-execution-debt-decree-243-brainstorm.md
  - research/2026-07-22-reopt-pysam-execution-unblock-brainstorm.md
  - research/2026-07-24-reopt-pysam-sixth-pass-brainstorm.md
  - research/2026-07-26-reopt-pysam-post-backlog-architecture-brainstorm.md
  - research/2026-08-06-reopt-pysam-gate-integrity-brainstorm.md
---

# Brainstorm: reopt-pysam — Ninth Pass (the generic deal path)

## 0. Summary in one paragraph

The eighth pass found a red pipeline and a one-deal API. Both were fixed: the
gate is pinned and genuinely green in CI, and the offsite registry now has two
entries. I re-verified all of it live today and the record holds — this is the
first pass in three where the repo's own status file is accurate. So this pass
is not another truth sweep. It reports one **dated defect** (a CI invariant that
turns red on 2026-08-19 with no code change), one **reproducible bug** (the
newly registered second orchestrator 500s through the web API and leaves a run
stuck at `queued`), one **measurement gap** (26 tests silently skip in CI and
nothing names them), and then argues the substantive point: registering
historical deals one at a time will never make this a product, and the single
missing ingredient for a genuinely deal-generic DPPA path is now identifiable
and small — a versioned market-price reference series in `data/vietnam/`.

---

## 1. Verification refresh — what is true on 2026-08-12 (run live, not assumed)

| Claim | Verified | Evidence |
|---|---|---|
| CI green on `main` | ✅ | `gh run list`: `31163146500` success (2026-08-07, 1m35s), preceded by `31162752294` and `31162599693`, both success on both matrix legs |
| Pinned gates hold | ✅ | `ruff check src scripts tests` → `All checks passed!` (ruff 0.16.1 from the `dev` extra); `mypy` → `Success: no issues found in 23 source files` |
| Portable suite green locally | ✅ | **653 passed, 19 deselected, 3 xfailed** in 107.95 s on `.venv` (Py 3.12), CI's exact marker filter |
| Coverage | ✅ | **85 %** local, 4,751 statements / 719 missed. CI reports **84 %** (776 missed) — the 57-statement delta is real, see F2 |
| Second orchestrator registered | ✅ | `_ORCHESTRATORS` resolves to `['DPPA_CASE_1_NINHSIM', 'DPPA_SAMSUNG_TTC']` at runtime; registration is in `analysis/__init__.py::_register_offsite_orchestrators` |
| Second orchestrator reachable end-to-end | ❌ | **500 + dangling run through the web API; no CLI flags at all** — see F3 |
| FX derivation complete | ✅ | `common/assumptions.exchange_rate` is the resolver; the general-purpose sites no longer pass `caller_value=` |
| Truth sweep landed | ✅ | `webapp/README.md:65` now reads "reproduces a direct `run_offsite_dppa` call bit-for-bit"; `AGENTS.md` §4 points at `activeContext.md`; §6's repealed-Decree-57 next-step carries a correction note |
| Stale branches gone | ✅ | `git branch -a` → `main` only; `real-project-data` and both `claude/*` branches deleted |
| Drift tripwire re-polarized | ✅ | `test_samsung_ttc_golden_drift_stays_within_the_known_manifest` asserts a *subset* of `KNOWN_DRIFTED_PATHS` — shrinking the drift now stays green |
| Regulatory watch has dates + invariant | ✅ | `Last verified` / `Next review` columns present; `test_regulatory_watch_rows_are_not_overdue` enforces them |
| …and the invariant is about to fire | ❌ | **3 rows expire 2026-08-18, six days from today** — see F1 |
| NREL key rotated | ❓ | Still no record. `README.md:197` still says "rotation required"; `activeContext.md:41` still says "not confirmed rotated as of 2026-07-24". **Nine sessions, ~40 days.** |

Two prior-pass claims I checked and can now sharpen rather than repeat:

- The eighth pass called `test_samsung_ttc_web_api_matches_direct_library_call_bit_exact`
  "genuinely enforced, runs in CI." **Confirmed** — its only skip guard is on
  tracked fixture files, so it does run on both legs. CON-002 is really enforced.
  Worth noting *how*: it compares the web path against a direct library call in
  the same process, so it holds even in CI where the Samsung solar profile falls
  back to synthetic. It proves "no forked analytics," not "the numbers are right."
- The settlement engine is **not** a performance problem and nobody should sell
  it as one. Measured today on an 8760 random profile: `compute_hourly_settlement`
  = **23.1 ms**, a 21-point `run_strike_sweep` = **0.49 s**. Pure-Python loops
  building 8,760 sixteen-key dicts per settlement are fine at this scale. I
  looked because it is the obvious "optimization" theme; it is not one.

---

## 2. New findings

Ordered by consequence. Each was reproduced today.

### F1 — A CI gate with a fuse: three regulatory-watch rows expire on 2026-08-18

`tests/python/test_repo_invariants.py::test_regulatory_watch_rows_are_not_overdue`
fails when any row's `Next review` date is in the past. Today's table:

| Row | Last verified | Next review | Days left |
|---|---|---|---|
| tech_costs | 2026-02-18 | **2026-08-18** | **6** |
| financials | 2026-02-18 | **2026-08-18** | **6** |
| emissions | 2026-02-18 | **2026-08-18** | **6** |
| tariff | 2026-08-06 | 2026-11-06 | 86 |
| export_rules / regimes | 2026-07-18 | 2027-01-18 | 159 |
| deal_defaults | 2026-08-01 | 2027-02-01 | 173 |

This is a good invariant and I would keep it. But three properties combine badly:

1. **It is time-triggered and CI is not.** `.github/workflows/ci.yml` runs on
   `push` and `pull_request` only — there is no `schedule:`. So the failure will
   not appear on 2026-08-19; it will appear on whatever unrelated push comes
   next, attached to a commit that did not cause it. That is precisely the
   failure mode of the eleven-day ruff outage read backwards: the eighth pass
   fixed *what* the gate checks and left *when* it runs unchanged.
2. **Nothing owns the review.** The three rows are `tech_costs` (market price
   surveys), `financials` (CIT law), `emissions` (annual MONRE grid factor).
   Each needs an external check no automated step performs.
3. **The cheap fix is the corrosive one.** When a red build blocks an unrelated
   push six days from now, the two-second remedy is to bump three dates. Do that
   twice and the column means "someone edited this cell," which is the exact
   unfalsifiable state the eighth pass introduced the column to end.

The `emissions` row is also the substantively interesting one: `vn_emissions_2024.json`
carries a 0.681 tCO2e/MWh grid factor whose own update trigger is "annual MONRE
study," and it has been six months. Every CO2 figure the toolkit emits rides on it.

**What I would do:** perform the three reviews before 2026-08-19 (each is a
source lookup, not modeling work), record the outcome in `Last verified`, and
add `schedule: cron` to CI so the invariant fires on its own date instead of
ambushing a contributor. Optionally split the gate into warn-tier (30 days out,
prints) and block-tier (overdue, fails) so there is a runway rather than a cliff.

### F2 — 26 tests skip in CI, 0 skip locally, and no artifact says which

Same commit, same marker filter, two environments:

```
local  (.venv, Py 3.12):  653 passed, 19 deselected, 3 xfailed          — 0 skipped
CI     (run 31163146500): 627 passed, 26 skipped, 19 deselected, 3 xfailed
```

The 26 are runtime `pytest.skip("… not available")` guards, not markers. There
are **49 such guard sites** across `tests/python`, including four
`pytest.skip("No NREL API key available")` in `tests/python/reopt/test_integration.py`
(lines 283, 315, 357, 441) and a family keyed on PySAM solar-resource caches.
They skip in CI and pass locally because this dev box has a git-ignored
`NREL_API.env` and a warm resource cache; CI has neither.

Why this matters more than the raw number:

- **The repo's headline test count is not the enforced test count.** `AGENTS.md`
  and `activeContext.md` quote the local figure. CI enforces 627. The 26-test
  gap is invisible in both documents and in the CI summary itself, because the
  workflow runs `pytest -q` with no `-rs`.
- **Marker exclusions are audited; skips are not.** `pyproject.toml` lists four
  markers with rationale and CI names them explicitly in its filter — that
  machinery exists precisely so nobody silently drops a test. Runtime skips
  route around all of it.
- **It is the last unaudited slice of the "green means what?" question** the
  seventh and eighth passes worked through. 26 skipped + 19 deselected = 45 of
  672 collected tests (6.7 %) not enforced on `main`, of which only the 19 are
  documented.

Fix is genuinely small: add `-rs` to CI's pytest invocation so every skip prints
its reason in the log, and add a skip-budget assertion (fail if skipped > N) so
the number cannot drift upward unnoticed. The deeper fix — convert
environment-dependent skips into markers so they show as *deselected* — is a
half-day and makes the exclusion set auditable in one place.

Related, and the explanation for the 85 %-vs-84 % coverage gap:
**`analysis/__main__.py` has 0 % coverage (57 statements)** even though
`tests/python/analysis/test_cli.py` exercises it — the test drives it as a
`subprocess`, so `coverage` never sees it. The declared public CLI is the
least-measured module on the declared public API surface.

### F3 — PHASE-04 widened the contract in the library and nowhere else; the second deal 500s

This is a real bug with a reproduction, and it is the direct cost of shipping a
contract change without walking its consumers.

`run_offsite_dppa` now accepts `(extracted, *, run_developer, results, scenario)`
and `DPPA_CASE_1_NINHSIM` requires `results` + `scenario`. Neither consumer
surface forwards them:

- **CLI:** `python -m reopt_pysam_vn.analysis offsite_dppa` has flags for
  `--config`, `--extracted`, `--out`, `--no-developer`. There is no `--results`
  and no `--scenario`. `_cmd_offsite_dppa` calls
  `run_offsite_dppa(deal, extracted=extracted, run_developer=…)`. So case 1 is
  unreachable from the CLI unless the caller hand-embeds an 8760-series REopt
  results dict inside the deal-config JSON (legal — the schema sets
  `additionalProperties: true` — but undocumented and awkward).
- **Web API:** `POST /api/runs` *accepts* a `results` key in the payload, and
  `webapp/service.run_analysis` *accepts* `results=`, but `_run_offsite()` calls
  `run_offsite_dppa(deal_config, extracted=extracted, run_developer=…)` and drops
  it on the floor.

Reproduced today against a real `TestClient`:

```python
POST /api/runs {"deal_config": {"case": "DPPA_CASE_1_NINHSIM", "mode": "offsite_dppa"},
                "extracted": {...}, "results": {...}}
→ ValueError: run_offsite_dppa for DPPA_CASE_1_NINHSIM needs `results` …
```

The `ValueError` is raised inside the orchestrator, which is **not** a
`service.AnalysisError`, so `routes/api.py::_submit_deal_config`'s
`except service.AnalysisError` does not catch it. The request becomes a 500 and
— because `storage.create_run()` already ran — the run row persists **stuck in
`state: "queued"`**. It is only cleared at the next app restart, by
`mark_interrupted_runs()`, which mislabels it "Run was interrupted by an app
restart before it finished."

For contrast, the *unregistered*-case path is handled beautifully:

```json
{"state": "error", "error_code": "NO_ORCHESTRATOR",
 "message": "no offsite orchestrator registered for case 'MY_NEW_DEAL'; registered cases: [...]",
 "error_hint": "This deal case has no offsite model yet; use a registered case or the generic runner."}
```

So the deal the repo *has not* built an orchestrator for fails cleanly, and the
deal it just *did* build one for fails with a 500. Note also that this hint
promises **"the generic runner"** — a thing that does not exist. The UX has
already been written for the architecture in F5.

Minimum fix (hours): forward `results`/`scenario` through `run_analysis`, add
`--results`/`--scenario` to the CLI subcommand, and re-raise orchestrator
`ValueError` as a `MissingInputsError` so the route's existing 422 path catches
it. Then add the test that would have caught it: a webapp test that a
`DPPA_CASE_1_NINHSIM` submission reaches `done`.

### F4 — The offsite pipeline's real input contract is the unvalidated one

`data/schemas/deal_config.schema.json` — the thin descriptor — is validated on
every `DealConfig.from_dict()` by `analysis/validation.py`, which collects every
violation rather than raising on the first. Good work, PHASE-02 of the 07-26 plan.

`data/schemas/extracted_inputs.schema.json` — the *rich* contract that every
offsite orchestrator actually consumes (8760 `loads_kw`, `benchmark`,
`pv_production_factor`, `fmp_vnd_per_mwh`, `evn_tariff`, site coords) — is
**referenced by nothing** in `src/`, `scripts/`, or `tests/`. I grepped for both
the filename and the schema id. Zero hits.

Consequences visible in the code today: `dppa_case_2._proxy_market_fraction`
does `extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"]` bare;
`dppa_case_1` builders index into `extracted` and `results` directly; a
malformed analyst upload surfaces as a `KeyError` several frames deep inside a
1,491-line case module rather than as a collected list of violations at the
boundary. And per F3, a bare `ValueError`/`KeyError` from that depth is a 500,
not a 422.

The asymmetry is worth stating plainly: **the file the schema exists for is the
one nothing checks.** The fix reuses machinery that already works — point
`validate_deal_config`'s structural validator at the extracted schema and call
it in `webapp/uploads.py` and at the top of each orchestrator.

### F5 — The one thing missing for a deal-generic DPPA path is a market-price reference series

This is the finding I would build the next quarter around, and it is much more
concrete than "config-driven case runner" (the theme six passes named and none
started).

**The generic pieces already exist, are parameterized, and are tested:**

| Need | Existing component | Deal-agnostic? |
|---|---|---|
| Hourly settlement (both modes) | `integration/settlement.compute_hourly_settlement` | ✅ 8760-in/8760-out, zero per-deal branching, 361 lines |
| Contract terms from policy | `ContractParams.from_regime(regime_id, …)` | ✅ resolves export cap, surplus rate, DPPA adder, KPP loss from the data layer |
| Strike discovery | `settlement.run_strike_sweep` + `integration/strike_search` | ✅ |
| Generation from coordinates | `pysam/pvwatts_battery.ensure_solar_resource_file` + PVWatts | ✅ (needs an NREL key on first fetch) |
| Load from partial data | `ingestion/synthesize` (monthly→8760, resampling, reference shapes) | ✅ |
| 8760 EVN TOU tariff | `reopt/preprocess` | ✅ |
| Buyer benchmark | `settlement.compute_buyer_benchmark` | ✅ |
| Developer finance | `pysam/single_owner` | ✅ |
| **Market reference (FMP/CFMP) series** | **— nothing generic —** | ❌ |

`data/vietnam/manifest.json` has seven keys: tariff, tech_costs, financials,
emissions, export_rules, regimes, deal_defaults. **No market-price file.** The
per-deal `*_extracted_inputs.json` carry `fmp_vnd_per_mwh` for Saigon18 and
Ninhsim; Samsung/TTC's extracted file has no market series at all (I dumped its
keys: `project`, `data_year`, `site`, `loads_kw`, `buyer_load`, `benchmark`,
`evn_tariff`, `strike_basis`, `assumptions`).

The only synthesis path is `dppa_case_2.build_dppa_case_2_market_proxy` —
"hourly EVN tariff scaled by weighted wholesale ratio" — and its scaling factor
comes from `extracted["benchmark"]["wholesale_rate_vnd_per_kwh"]`, i.e. from
*deal* data, not repo data. So the repo's one reusable market-price method is
buried in its largest bespoke module (1,491 lines) and keyed off an input a new
deal does not have.

**Therefore the next increment is not "register orchestrator #3."** It is:

1. Add `data/vietnam/vn_market_prices_2026.json` (manifest key `market_prices`)
   holding a documented reference hourly FMP/CFMP shape plus the wholesale/retail
   ratio, with the standard `{_meta, data}` envelope, a `regulatory-watch` row,
   and an honest `PENDING`/`proxy` quality flag where the published data does not
   exist yet. This is the same move the repo already made for tariff, emissions,
   and export rules — it is a well-worn path here.
2. Lift the proxy method out of `dppa_case_2` into `integration/settlement` (or
   a small `market_reference` module) so it reads the data layer and falls back
   to deal data, not the reverse.
3. Write `analysis/orchestrators/generic_vn_dppa.py`: assemble load (upload or
   synthesized) + generation (PVWatts from `site.latitude/longitude`) + tariff
   (preprocess) + market reference (new module) + `ContractParams.from_regime`
   from `DealConfig.contract`, then run settlement → strike sweep → developer
   screen. Register it as the **fallback** the registry uses when
   `deal_config.case` matches nothing.
4. The registry becomes "a default path plus per-deal exceptions" instead of "a
   list of two historical deals." `MY_NEW_DEAL` stops being a 422/500 and starts
   being an answer flagged `directional`.

That is what makes the free-text **Case id** field on `/deals/new` honest, and it
is what the existing error hint already promises the user.

Sequencing note, in the tradition of the last two passes: the seventh pass
argued the assumptions resolver must precede the reporting pipeline; the eighth
argued a second orchestrator must precede the reporting pipeline. Both held.
The same logic applies once more — a report template over an API that serves two
named historical deals is a template for two clients. The generic path is what
turns the reporting theme into something worth building.

### F6 — `common/` is three-quarters decorative

`src/python/reopt_pysam_vn/common/` presents as the shared-helpers package. It
contains four modules:

| Module | Statements | Coverage | Importers outside itself |
|---|---|---|---|
| `assumptions.py` | 63 | 98 % | 21 |
| `currency.py` (`identity_currency`) | 2 | **0 %** | **0** |
| `time_series.py` (`constant_series`) | 2 | **0 %** | **0** |
| `validation.py` (`require_positive`) | 4 | **0 %** | **0** |

The three stubs are early scaffolding nobody ever wired up — `identity_currency`
literally returns `float(value)`. Meanwhile `_constant_series` is re-implemented
privately in `scripts/python/reopt/fmp_sensitivity.py` and
`tests/python/integration/test_settlement_generic.py`. Either delete the three
(they contribute nothing but a misleading package shape) or make them the real
home for the helpers people keep rewriting. I would delete: `common` earns its
name from `assumptions.py` alone.

### F7 — The script layer has not moved, and the census is unchanged

| Metric | 07-26 pass | 08-06 pass | **today** |
|---|---|---|---|
| `scripts/` Python LOC | — | 31,202 | **31,141** |
| `src/` Python LOC | — | 12,847 | **13,027** |
| ratio | — | 2.43 : 1 | **2.39 : 1** |
| `generate_*.py` count / LOC | 34 / 10,189 | 36 / 10,868 | **36 / 10,854** |
| hand-rolled HTML builders | 9 | 9 | **9** |

The nine that hand-roll a full HTML document (`<style>`, fonts, cards, Chart.js)
while `assets/report-template.html` and `assets/final-report-template.html` sit
there serving ~10 other scripts:

```
scripts/python/integration/compare_procurement.py
scripts/python/integration/generate_cross_project_dashboard.py
scripts/python/integration/generate_html_report.py
scripts/python/integration/generate_north_thuan_reopt_report.py
scripts/python/integration/generate_north_thuan_validation_report.py
scripts/python/integration/generate_saigon18_dppa_case_3_phase_cde_report.py
scripts/python/reopt/generate_bess_economics_report.py
scripts/python/reopt/generate_regime_comparison_report.py
scripts/python/reopt/tou_comparison_report.py
```

Two structural notes that make this less optional than it looks:

- **Coverage does not measure any of it.** `[tool.coverage.run] source = ["reopt_pysam_vn"]`.
  The 85 % figure describes 13,027 lines and is silent on 31,141.
- **Parts of it are load-bearing.** Eight test files `sys.path.insert` into
  `scripts/python/{reopt,integration}` and import scripts as modules — the exact
  coupling that made the 2026-06-12 shim removal dangerous (see `lessons.md`).
  Any "just delete old scripts" instinct should re-read that entry first.

Adjacent hygiene: **32 test files still do `sys.path.insert(0, REPO_ROOT/"src"/"python")`**
even though `pyproject.toml` sets `pythonpath = ["src/python"]` and CI installs
the package editable. Harmless, but it is 32 copies of a workaround the build
config has handled since the package was created, and it would mask a genuinely
broken install.

### F8 — Small, verified, cheap

- **`jobs.py:149` uses a bare `assert` for a cache invariant** in a production
  code path (`assert reopt_results is not None, "cache invariant violated…"`).
  Under `python -O` it vanishes and the failure becomes a confusing `None` a few
  lines later. Should be an explicit raise.
- **Three plans marked `status: "complete"` still sit in `plans/active/`**
  (`2026-05-22-gap01-factory-ingestion`, `gap02-procurement-comparison`,
  `gap04-generalized-settlement`). The 07-24 sweep archived 13 and missed these.
- **Three `ceba_*.md` reports (49 KB) sit at the repo root** rather than
  `reports/`, against the repo's own convention that `reports/*.md` is the home
  for tracked markdown deliverables.
- **`analysis/__init__.py::_register_offsite_orchestrators` is documented as a
  lazy import but is called at module import time.** The claim is *effectively*
  true (the module it eagerly imports is a thin adapter that defers the heavy
  `integration.dppa_case_1` import into the function body), but the comment
  describes a mechanism the code does not use, and this repo has spent three
  passes on comments that describe intentions rather than behavior.
- **The runtime dependency floor is still unpinned** — see Theme K below.

---

## 3. Themes

### Theme J (#1) — Close the three concrete defects

F1 (dated invariant), F3 (500 + dangling run), F2 (`-rs` + skip budget). All
three are hours, not sprints, and F1 has a deadline six days out. F3 is the one
a user could hit today.

**Sizing:** ~1 day for all three, including the regression tests.

### Theme K (#2, new) — Finish the supply-chain fix the eighth pass started

The eighth pass's root-cause statement was correct — "an unpinned gate tool that
redefines its own defaults between releases breaks every push without touching a
line of code" — and the fix was applied to the four tools that happened to
break. The runtime floor is unchanged:

```toml
matplotlib>=3.8, nrel-pysam==7.1.0, numpy-financial>=1.0,
openpyxl>=3.1, pandas>=2.0, requests>=2.31
fastapi>=0.110, uvicorn[standard]>=0.29, jinja2>=3.1, python-multipart>=0.0.9, httpx>=0.27
```

One pin, ten floats, no lockfile, and CI resolves from PyPI on every run. Pandas
3.0 is the obvious next candidate for exactly the ruff failure mode, and a
pandas break would look like a data bug, not a tooling bug — much harder to
diagnose than a lint break. Two changes close it:

1. A CI constraints file (`pip install -e ".[webapp,dev]" -c constraints-ci.txt`)
   so the enforced build is reproducible, with the floors left permissive in
   `pyproject.toml` for library consumers.
2. `schedule: cron` on the workflow — weekly is enough — so a dependency-side
   break, or F1's date-based invariant, surfaces on its own schedule instead of
   ambushing the next unrelated push. This also directly addresses the eighth
   pass's real lesson: the eleven-day outage was eleven days because nothing ran
   between pushes.

**Sizing:** half a day. It is the difference between "we fixed ruff" and "a
third-party release can no longer break `main` unannounced."

### Theme L (#3, the substantive one) — The generic deal path

F5, in four steps: market-price data file → lift the proxy out of `dppa_case_2` →
`generic_vn_dppa` orchestrator → register it as the registry fallback. Plus F4
(validate `extracted` against the schema that already exists) as its input
boundary, because the generic path is the first one that will receive inputs from
someone who did not build the deal by hand.

This is the first version of the six-pass-old "config-driven case runner" theme
with a named missing artifact and a four-step diff. It also finally makes the
webapp's free-text **Case id** field mean something, and it retires the
`NO_ORCHESTRATOR` hint's promise of a "generic runner."

**Sizing:** ~1–2 sprints. Step 1 alone (the data file + watch row) is a day and
unblocks the rest.

### Theme M (#4) — Make the enforced surface auditable

The deeper half of F2: convert environment-dependent `pytest.skip()` guards into
markers so the CI exclusion set lives in one auditable place, and get the public
CLI measured (an in-process `main(argv)` test alongside the subprocess smoke
test — `__main__.main()` already takes `argv`, so this is a five-line test).
Then the repo can state one number and have it be true in both environments.

**Sizing:** half a day.

### Theme A (#5, carried, unchanged) — Consolidate the reporting layer

F7. Migrate the nine hand-rolled builders onto the two existing templates; that
migration is the requirements document for a real `python -m reopt_pysam_vn.report`.
Still correctly sequenced *after* the generic path, for the reason stated in F5.

### Carried, unstarted — webapp → deck export

The 07-24 pass's Finding A stands. It is a consumer of Themes L and A both.

---

## 4. Suggested sequencing

| # | Item | Size | Why here |
|---|---|---|---|
| 1 | **Theme J** — three regulatory reviews before 08-19; fix the offsite 500 + dangling run; `-rs` + skip budget in CI | ~1 day | F1 has a six-day fuse and F3 is a live bug on the feature that shipped last |
| 2 | **Theme K** — CI constraints file + `schedule: cron` | half day | Closes the class of defect the eighth pass closed one instance of; the cron also makes #1's invariant self-firing |
| 3 | Theme L step 1 — `vn_market_prices_2026.json` + manifest key + watch row | ~1 day | The single named blocker for everything generic; standalone and value-preserving |
| 4 | **Theme L steps 2–4** — lift the market proxy, build `generic_vn_dppa`, register as fallback; F4's schema validation at the boundary | ~1–2 sprints | The highest-value substantive work; turns the registry into a default path |
| 5 | Theme M — markers for environment skips, in-process CLI test | half day | Cheap; makes the post-L test story honest in both environments |
| 6 | Theme A — migrate 9 report builders onto the existing templates | ~1 sprint | Strictly better after #4 |
| 7 | webapp → deck export | ~1 sprint | Consumer of #4 and #6 |

---

## 5. Decisions self-resolved this pass (no user input was solicited, per workflow)

- **DEC-901** — Write a roadmap rather than execute. The workflow for this
  session is brainstorm-only; no repo file was modified except this document.
  *(auto-selected, carried from DEC-801)*
- **DEC-902** — Lead with F1 despite it being small, because it is the only
  finding with a date attached and the window is six days. *(auto-selected)*
- **DEC-903** — Recommend performing the three regulatory reviews rather than
  bumping the three dates. Bumping is the two-second fix and would hollow out
  the column the eighth pass added. *(auto-selected)*
- **DEC-904** — Classify F3 as a defect in the *consumers*, not in the widened
  contract. The `(extracted, *, run_developer, results, scenario)` shape is
  right; the CLI and `webapp/service` simply were not walked. Fix the consumers;
  do not narrow the contract. *(auto-selected)*
- **DEC-905** — Orchestrator input errors should be raised as
  `service.MissingInputsError` (a `AnalysisError`) so the existing 422 path
  catches them, rather than broadening `except` clauses to bare `ValueError` —
  which would also swallow genuine programming errors. *(auto-selected)*
- **DEC-906** — The next generalization increment is a **generic fallback
  orchestrator**, not a third registered historical deal. Two registered
  implementations is the sample the eighth pass wanted before abstracting
  (DEC-804's step 4); that sample now exists and the shared surface is visible.
  *(auto-selected)*
- **DEC-907** — The market-price reference goes in `data/vietnam/` behind the
  manifest with a `regulatory-watch` row, not in code and not in a per-deal
  extracted file. It is policy-adjacent data and the repo has an established,
  working pattern for exactly this. *(auto-selected)*
- **DEC-908** — Do **not** propose vectorizing the settlement engine. Measured:
  23.1 ms per settlement, 0.49 s per 21-point sweep. Recording the measurement
  so a future pass does not re-propose it. *(auto-selected)*
- **DEC-909** — Delete the three `common/` stubs rather than adopt them.
  Adopting would mean editing ~2 call sites to import a two-line function; the
  package's shape is the only thing they cost, and it is misleading.
  *(auto-selected)*
- **DEC-910** — Do not touch `examples/samsung-ttc_combined-decision.example.json`.
  Carried unchanged from DEC-809 / DEC-706 / CON-001. *(auto-selected)*

## 6. Assumptions & constraints

- **ASM-901** — I did not enumerate which 26 tests skip in CI. `-q` prints no
  reasons, and reproducing the CI environment locally would mean moving this
  machine's `NREL_API.env` and resource cache, which I judged out of bounds for
  an analysis-only pass. The 653-vs-627 delta and the 49 guard sites are
  measured; the composition of the 26 is inferred. Theme J's `-rs` change makes
  the question answerable in one CI run — that is most of its value.
- **ASM-902** — F1's "six days" assumes today is 2026-08-12 and the invariant
  compares against `datetime.now(timezone.utc).date()`, which it does. The first
  red build will be the first push on or after 2026-08-19.
- **ASM-903** — F3's 500 was reproduced through `fastapi.testclient.TestClient`,
  which re-raises unhandled exceptions rather than returning 500. A deployed
  uvicorn returns 500. The *dangling run* half is directly observed: the run
  directory persists with `state: "queued"` and no worker will ever pick it up
  (the queue is fed only for `mode == "onsite"`).
- **ASM-904** — F5's claim that the market series is the *only* missing generic
  input is based on reading the settlement engine's five positional inputs
  (loads, generation, tariff, fmp, params) and tracing each to an existing
  deal-agnostic producer. A real implementation will surely surface secondary
  gaps (the benchmark block's `weighted_evn_price_vnd_per_kwh`, voltage-level
  resolution). The claim is "one missing *data* artifact," not "no other work."
- **ASM-905** — The Samsung/TTC offsite path in CI runs on a synthetic solar
  profile, because no resource file for its coordinates is tracked
  (`data/interim/pysam_resources/` holds only Ninhsim's 12.5257/109.0200 pair)
  and CI has no NREL key. The CI-enforced parity test is structural
  (web-vs-direct), so this does not weaken it — but no economic number Samsung
  produces is validated in CI. Stated so it is not over-read either way.
- **ASM-906** — I did not verify the three overdue regulatory rows against
  primary sources. Doing so is Theme J's actual work item, not this pass's.
- **CON-901** — CON-001 holds: Samsung/TTC bit-exact parity remains the goal and
  the golden is untouched.
- **CON-902** — CON-002 holds and is genuinely CI-enforced today; any Theme L
  refactor must keep `test_samsung_ttc_web_api_matches_direct_library_call_bit_exact`
  passing.
- **CON-903** — CON-004 holds: `ContractParams` fields may not be renamed or
  made required. Theme L *adds* a generic consumer of it; it must do so through
  `from_regime(**overrides)`, which already exists for this purpose.
- **CON-904** — Windows-first repo; Themes J and K are CI/config only.
- **CON-905** — Analysis-only pass. The only file written is this brainstorm.
  A scratch `runs/` directory used for the F3 reproduction was created under the
  session scratchpad, not in the repo.

## 7. Out of scope

- Executing any of the above (brainstorm-only workflow).
- Rotating the NREL API key — out-of-band human action, see Q-901.
- Re-litigating the Samsung parity divergence's root cause; timeboxed and
  documented in `reports/2026-07-26-samsung-parity-diagnosis.md`.
- Reviving the Julia path. DEC-004 / DEC-705 (archive in place) stands.
- Multi-tenant auth, cloud hosting, containerization.
- Optimizing the settlement engine (DEC-908 — measured, not a problem).

## 8. Open questions (with adopted defaults, since no input is solicited)

1. **Q-901 (open across NINE sessions, ~40 days):** Has the NREL key from commits
   `3911032` / `b14bc0b` been rotated?
   - *Adopted default:* assume **no**. Still the single most overdue mechanical
     item in the repo and the only one that cannot be closed from inside it.
2. **Q-902 (new):** Should the regulatory-watch invariant block, or warn?
   - *Adopted default:* **block, but add a 30-day warn tier and a scheduled CI
     run** so the block never arrives as a surprise on an unrelated push. A
     pure-warn gate decays to noise; a pure-block gate on a push trigger
     punishes the wrong commit.
3. **Q-903 (new):** For the generic path's market reference, is a documented
   proxy (tariff × wholesale ratio) acceptable in client-facing output?
   - *Adopted default:* **yes, flagged.** The repo already ships `directional`
     and `proxy_cfmp_or_fmp` quality flags and case 2 already uses exactly this
     method. A flagged proxy beats a 422, and beats an unflagged number.
4. **Q-904 (new):** Should the generic orchestrator be the registry *fallback*
   (any unknown case routes to it) or an explicit opt-in case id?
   - *Adopted default:* **fallback**, with the resolved orchestrator name echoed
     in the result's `quality` block so nobody is confused about what ran. The
     explicit-opt-in variant preserves today's clean `NO_ORCHESTRATOR` error but
     leaves the free-text Case id field broken, which is the problem being fixed.
5. **Q-905 (carried, unanswerable from the repo):** Has any deliverable already
   gone to an external counterparty carrying a non-26,400 FX rate or the
   pre-audit Single-Owner reference-plant defaults?
   - *Adopted default:* unresolvable by inspection; needs a human with send
     history. Flagging beats guessing.

## 9. Suggested next step

**If the next session's budget is small: Theme J, F1 first.** Verify the three
regulatory rows (`tech_costs`, `financials`, `emissions`) against their sources,
update `Last verified` / `Next review`, then fix the offsite 500 —
forward `results`/`scenario` through `webapp/service.run_analysis`, add
`--results`/`--scenario` to the CLI, convert the orchestrator's input
`ValueError`s to `MissingInputsError`, and add a webapp test that a
`DPPA_CASE_1_NINHSIM` submission reaches `done`. Finish with `-rs` and a skip
budget in the CI pytest step, and confirm with `gh run list` rather than a local
run. That clears the fuse, fixes the live bug, and makes the next pass's test
numbers mean the same thing in both environments.

**If there is room for one substantial item: Theme L step 1 plus step 2** —
add `data/vietnam/vn_market_prices_2026.json` behind the manifest with its
`regulatory-watch` row, and lift `build_dppa_case_2_market_proxy` out of the
1,491-line case module into a shared `market_reference` path that reads the data
layer first and deal data second. Those two changes are self-contained,
value-preserving for the existing deals, and they convert "config-driven case
runner" from a six-pass-old aspiration into a half-built feature with one
orchestrator left to write.
