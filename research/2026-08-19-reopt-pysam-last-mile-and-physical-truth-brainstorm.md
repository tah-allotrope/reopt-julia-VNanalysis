---
date: 2026-08-19
slug: reopt-pysam-last-mile-and-physical-truth
kind: brainstorm
mode: unattended (no user input; all open choices self-resolved and flagged)
repo: reopt-pysam
branch: main @ 4641cac (clean)
predecessors:
  - research/2026-07-11-reopt-pysam-next-level-brainstorm.md
  - research/2026-07-14-reopt-pysam-strategic-lens-brainstorm.md
  - research/2026-07-17-reopt-pysam-ci-truth-brainstorm.md
  - research/2026-07-18-execution-debt-decree-243-brainstorm.md
  - research/2026-07-22-reopt-pysam-execution-unblock-brainstorm.md
  - research/2026-07-24-reopt-pysam-sixth-pass-brainstorm.md
  - research/2026-07-26-reopt-pysam-post-backlog-architecture-brainstorm.md
  - research/2026-08-06-reopt-pysam-gate-integrity-brainstorm.md
  - research/2026-08-12-reopt-pysam-generic-deal-path-brainstorm.md
---

# Brainstorm: reopt-pysam — Tenth Pass (the last mile, and the physics nobody checked)

## 0. Summary in one paragraph

The ninth pass argued the repo needed a generic DPPA path instead of a third
hand-registered deal. That path was built, and it works — I called it directly
today and it returned a complete, correctly-flagged `directional` result. But
**it is not reachable from the product's own front door**: submitting a new deal
through `/deals/new` with a load CSV — the exact motion the generic path exists
to serve — still ends in `MISSING_INPUTS`, because nothing assembles the
`extracted` dict the orchestrator consumes, even though every ingredient is
already in the repo. That is finding one, and it is a day of work. Findings two
through four are more serious and are new to every pass: this repo has exactly
**one** solar resource file (Ninh Thuan, 12.53 °N), every PVWatts call site
silently falls back to it regardless of the deal's coordinates, both call sites
silently model a **single-axis tracker** because nobody sets `array_type`
(+23.6 % annual yield vs fixed-tilt, measured), and the generic path's
AC-clipping routine **injects solar generation into night hours** — up to 13.9 %
of annual energy at 457 kW at 02:00, measured. Nine passes have audited whether
the repo tells the truth about its own process. None has audited whether it
tells the truth about the sun.

---

## 1. Verification refresh — what is true on 2026-08-19 (run live, not assumed)

| Claim | Verified | Evidence |
|---|---|---|
| CI green on `main` | ✅ | `gh run list`: `31989898604` **success on a `schedule` trigger** (2026-08-17, 1m36s), both matrix legs. The eighth pass's cron recommendation is real and firing. |
| Local suite == CI suite | ✅ | Local `.venv` (Py 3.12), CI's exact six-marker filter: **655 passed, 46 deselected, 3 xfailed** in 61.4 s. CI logs: **655 passed, 46 deselected, 3 xfailed**, both legs. First pass in the series where the two numbers are identical. |
| Skip budget holds | ✅ | `REOPT_PYSAM_VN_MAX_SKIPS: "0"`; CI reports **0 skipped**. The 26 phantom skips the ninth pass measured are gone. |
| Pinned gates hold | ✅ | `ruff check` → `All checks passed!`; `mypy` → `Success: no issues found in 24 source files`. |
| Constraints file used | ✅ | `pip install -e ".[webapp,dev]" -c constraints-ci.txt` in the workflow; the 08-13 backtick corruption is fixed. |
| Regulatory-watch fuse defused | ✅ | No row is overdue today. `financials` re-verified 2026-08-13 → next 2027-02-13. |
| …but two rows are `UNVERIFIED` with a new 24-day fuse | ⚠️ | `tech_costs` and `emissions` both carry `Next review: 2026-09-12` and status `UNVERIFIED (pending primary-source check)`. See F11. |
| Generic fallback orchestrator exists and runs | ✅ | Called directly today: an unregistered case returns a full artifact, `quality.orchestrator == "generic_vn_dppa"`, `basis == "directional"`. |
| **Generic path reachable from the web UI** | ❌ | **`MISSING_INPUTS` on a form + load-CSV submission.** Reproduced today. See **F1**. |
| Market-price data layer landed | ✅ | `data/vietnam/vn_market_prices_2026.json` behind `manifest.json`, `market_prices` key, PROXY-flagged watch row, `integration/market_reference.py` shared. |
| Coverage | ⚠️ | **82 %** in CI (5,003 statements / 916 missed). Was 85 % local / 84 % CI at the ninth pass. **Down 3 points, and there is no `--cov-fail-under`.** |
| F8 hygiene items from the ninth pass | ❌ | All still open: bare `assert` at `jobs.py:149`; three `status: complete` plans in `plans/active/`; three `ceba_*.md` at the repo root; three zero-coverage `common/` stubs (DEC-909 not executed). |
| NREL key rotated | ❓ | **Tenth session, ~47 days.** `README.md` still says "rotation required"; `activeContext.md` still says "not confirmed rotated as of 2026-07-24". |

Two prior-pass claims I can now sharpen:

- **The ninth pass's Theme J/K/M all landed and held.** The scheduled run on
  2026-08-17 is the proof the eighth pass wanted and could not have: a green
  build produced by nothing but the passage of time. I would stop re-auditing
  the CI gate; it is the healthiest part of this repo.
- **ASM-905 ("Samsung's CI run uses a synthetic profile") is right about CI and
  wrong about the dev machine.** Locally, `dppa_samsung_ttc` does *not* fall back
  to synthetic — it falls back to the **Ninh Thuan** resource file, ~350 km from
  Samsung's site. That is a materially different and worse failure mode than the
  one that was recorded. See F2.

---

## 2. New findings

Ordered by consequence. Every one was reproduced today on this machine.

### F1 — The generic deal path is unreachable from the product's own front door

The ninth pass's argument was: registering deals one at a time will never make
this a product; build the generic fallback instead. The fallback was built and
it works. But the motion a real user performs — open `/deals/new`, fill the
guided form, upload an hourly load CSV, pick `offsite_dppa`, submit — still
fails.

Reproduced against a live `TestClient` today:

```
POST /api/deals   case=MEKONG_NEW_DEAL  mode=offsite_dppa
                  site.latitude=10.03 site.longitude=105.78 site.region=south
                  contract.strike_vnd_per_kwh=1200 contract.annual_solar_gwh=8.76
                  plant.capacity_mwac=5   + an 8760-row load.csv
→ 202 Accepted, run created
→ state: error   error_code: MISSING_INPUTS
   "offsite_dppa analysis needs pre-solved `extracted` inputs; there is no
    generic fresh-solve path for offsite/DPPA yet…"
```

The cause is a mismatch of *location*, not a missing capability:

| The orchestrator reads | The form writes |
|---|---|
| `extracted["loads_kw"]` | `deal_config["load"]["loads_kw"]` ✅ *(present!)* |
| `extracted["site"]` | `deal_config["site"]` ✅ *(present!)* |
| `extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]` | — *(derivable: `reopt/preprocess`)* |
| `extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"]` | — *(derivable: `settlement.compute_buyer_benchmark`)* |
| `extracted["benchmark"]["wholesale_rate_vnd_per_kwh"]` | — *(derivable: `common.assumptions.market_wholesale_reference_vnd_per_kwh`, added last sprint)* |
| generation | — *(the generic orchestrator derives it itself)* |

**Every missing ingredient already has a deal-agnostic producer in this repo.**
Two are literally sitting in `deal_config` under a different key. The third is
a function added by last sprint's PHASE-04 and called by nothing but the market
proxy.

So the ninth pass's own framing applies to itself one level down. It named the
missing *data artifact* (the market-price series) and shipped it. The missing
*code artifact* is the assembler:

```python
# reopt_pysam_vn/analysis/extracted.py
def build_extracted_inputs(deal_config: DealConfig, *, vn: VNData | None = None) -> dict:
    """Assemble the offsite `extracted` contract from a DealConfig + the data layer."""
```

…called from `webapp/service._run_offsite()` when `extracted is None` and
`deal_config.load.loads_kw` is present, and exposed as
`python -m reopt_pysam_vn.analysis offsite_dppa --derive-extracted`.

One blocker worth naming so it is not discovered mid-sprint: `preprocess`'s TOU
builder (`_build_8760_rates` → `apply_vietnam_tariff`) emits rates already
converted to **USD** for REopt, nested inside an `ElectricTariff` block. The
assembler needs VND/kWh. That is an extraction of the pre-conversion series into
a public
`build_evn_tou_series_vnd_per_kwh(vn, *, customer_type, region, voltage_level, year)`
— a small, value-preserving refactor, not a rewrite.

**Sizing: ~1 day.** It is the highest value-per-hour item in this document by a
wide margin, because it is what converts the last two sprints of investment
from a library capability into a thing a person can use.

### F2 — This repo has exactly one solar resource file, and every PVWatts path silently falls back to it

```
data/interim/pysam_resources/
  ninhsim_himawari_2019_60min.csv                                     ← the fallback
  nsrdb_12.525729252783036_109.02003383567742_himawari_60_2019.csv    ← same site
  nsrdb_data_query_response_12.525729252783036_109.02003383567742.json
```

`DEFAULT_SOLAR_RESOURCE_FILE` is the Ninh Thuan file (12.5257 °N, 109.0200 °E).
Three call sites resolve to it, and each does so *silently*:

1. **`pysam/pvwatts_battery.ensure_solar_resource_file`** — if the file expected
   for the requested lat/lon is not cached, it returns `DEFAULT_SOLAR_RESOURCE_FILE`
   rather than raising or warning (`if fallback.is_file(): return fallback`).
2. **`integration/dppa_samsung_ttc._pvwatts_south_solar_8760`** — docstring says
   "the cached **southern** resource"; the file is south-*central* coast.
3. **`analysis/orchestrators/generic_vn_dppa._try_pvwatts_generation`** —
   **checks that `site.latitude`/`site.longitude` are present, then never uses
   them.** It sets `model.SolarResource.solar_resource_file = DEFAULT_SOLAR_RESOURCE_FILE`
   and reports `quality.solar_profile_source = "pvwatts"`.

The distances are not academic:

| Deal | Site | Resource used | Separation |
|---|---|---|---|
| Samsung / TTC (Duc Hue, Long An) | 10.88 °N, 106.28 °E | 12.53 °N, 109.02 °E | **≈ 350 km**, Mekong Delta → semi-arid south-central coast |
| Factory A | 10.88 °N, 106.28 °E | same | ≈ 350 km |
| Any new generic deal | wherever the user clicked on the map | same | unbounded |

Measured yield off that file today (1 MWp DC, dc/ac 1.2, 14 % losses):
**1,888 kWh/kWp/yr** — Ninh Thuan-class, among the best irradiance in Vietnam.
The Mekong Delta is typically 1,300–1,450. The *shape* differs even more than
the total: Ninh Thuan is semi-arid with a dry-season peak; the Delta and the
north are monsoonal. For a DPPA CfD, hourly generation shape against hourly
load is the entire settlement.

Mitigating, and worth stating fairly: when a deal supplies `annual_solar_gwh`,
both Samsung's builder and the generic path rescale the series to that target,
so the **annual energy** is pinned to the deal's own number. What survives the
rescale is the **shape**, which is what drives `matched_mwh`, `shortfall_mwh`,
`exported_mwh`, and every CfD hour. And when no target is supplied, nothing is
corrected at all.

The worst part is not the substitution — a single reference year is a defensible
starting point for a small toolkit. It is that **the output says `"pvwatts"` and
nothing says *which* pvwatts**. `quality.solar_profile_source` was added
specifically so a reader knows what was computed and from what, and on this
axis it misinforms.

**Fix, in ascending order of cost:**
1. *(hours)* Record `resource_file`, its lat/lon, and the great-circle distance
   to the site in the `quality` block; emit a warning above some threshold
   (100 km is a reasonable line for Vietnam's climate zones); rename the source
   label to `pvwatts_fallback_resource` when the coordinates do not match.
2. *(~1 day)* Track three or four small TMY files — north / central / south /
   south-central — under `data/interim/pysam_resources/`, and select by the
   site's region (which the map picker already derives from latitude) rather
   than by a module constant.
3. *(optional)* Wire `ensure_solar_resource_file`'s real fetch path into the
   webapp behind the NREL key, cached per rounded lat/lon.

### F3 — Both PVWatts call sites silently model a single-axis tracker

Neither `generic_vn_dppa` nor `dppa_samsung_ttc` sets `array_type` or `tilt`.
They call `PySAM.Pvwattsv8.default("PVWattsSingleOwner")` and override only
`system_capacity`, `dc_ac_ratio`, `inv_eff`, and `losses`. I dumped what the
remaining defaults are:

```
array_type = 2.0   ← 1-axis backtracked TRACKING
tilt       = 0.0
azimuth    = 180.0
gcr        = 0.3
```

Measured on the same resource file, same capacity, same losses:

| Configuration | Annual yield | Δ |
|---|---|---|
| **repo default (1-axis tracking, tilt 0)** | **1,888.3 kWh/kWp** | — |
| fixed open rack, tilt = latitude | 1,527.9 kWh/kWp | **−19.1 %** |
| fixed roof mount, tilt 10.9° | 1,514.7 kWh/kWp | −19.8 % |

So the production path is **+23.6 % above fixed-tilt** on identical irradiance,
for a configuration nobody chose and no document mentions. Rooftop C&I solar —
the majority of what this repo models — is fixed-tilt by construction.

The repo already knows the right answer and has forgotten it. Its own physical
validity test, `tests/python/integration/test_capacity_factor_benchmark.py`,
explicitly sets `array_type = 1` and `tilt = BINH_THUAN_LAT`, and asserts
14 % ≤ CF ≤ 20 % against a 16.49 % benchmark. The production path yields
**25.9 % AC capacity factor** on the same class of site. That test has been
`xfail`ed since 2026-07-04 as "numeric benchmark drift" — it is not drift, it is
the only physical-plausibility gate in the repo, and it is switched off.

Note the interaction with F2: F3's +23.6 % and F2's location error compound on
any deal that does not supply `annual_solar_gwh`, and the *shape* error from
both survives on deals that do. Tracking produces a broad midday plateau;
fixed-tilt produces a peak. In a CfD settled hour by hour against an industrial
load and a market price, those are different contracts.

**Fix:** set `array_type` and `tilt` explicitly at both call sites, driven by a
`plant.mounting` field on `DealConfig` (`fixed_open_rack` / `fixed_roof` /
`single_axis_tracking`, defaulting to fixed for a rooftop customer type),
record the choice in `quality`, and **un-`xfail` the Binh Thuan benchmark** as a
CI-enforced plausibility gate once the production path agrees with it.

### F4 — The generic path injects solar generation into night hours

`analysis/orchestrators/generic_vn_dppa._calibrate_to_target` scales a shape to
an annual target and AC-clips it at the plant's `capacity_mwac`. When clipping
removes energy, it redistributes the deficit in proportion to each hour's
remaining headroom:

```python
out = [min(value * scale, cap_kw) for value in series]
deficit = annual_target_kwh - sum(out)
if deficit > 1.0:
    headroom = [cap_kw - value for value in out]          # ← a 02:00 hour has
    head_total = sum(headroom)                            #   headroom == cap_kw
    if head_total > 0.0:
        out = [v + deficit * (room / head_total) for v, room in zip(out, headroom)]
```

A night hour has `out == 0`, therefore `headroom == cap_kw` — **the maximum
possible share**. The redistribution preferentially fills the hours with no sun.

Measured today (deterministic synthetic shape, so these are exact):

| Plant cap | Annual target | Night-hour energy (23:00–03:00) | Peak night output |
|---|---|---|---|
| 5.0 MWac | 12.0 GWh | 1.3 MWh (0.0 %) | 1 kW |
| 2.0 MWac | 8.0 GWh | **457.0 MWh (5.7 %)** | **250 kW** |
| 1.0 MWac | 6.0 GWh | **834.5 MWh (13.9 %)** | **457 kW** |

In a DPPA settlement, night generation is matched against night load at the
off-peak retail rate and the off-peak market price — it inflates `matched_mwh`,
suppresses `shortfall_mwh`, and shifts the recommended strike. Nothing warns;
`quality` reports a clean `synthetic`/`pvwatts` source.

This function is in the **uncovered** range of the module (CI coverage names
lines 55–65 as missed). Every test in `test_generic_vn_dppa.py` supplies
`generation_kw` explicitly, so the entire generation-resolution subsystem —
`_calibrate_to_target`, `_synthetic_generation_8760`, `_try_pvwatts_generation`,
`_dc_capacity_kw` — ships untested. `generic_vn_dppa.py` is **56 % covered, the
lowest of any module on the declared public API surface**, and it is the module
the last sprint was built around.

**Fix:** redistribute only across hours with non-zero shape, iterate to
convergence, and when the annual target is infeasible at the stated AC cap
(`target > cap_kw × hours_with_sun`), stop and record an explicit
`quality.warnings` entry rather than manufacturing energy. Then test all four
resolution branches.

### F5 — The generic result is 3.79 MB where the bespoke result it substitutes for is 11.8 KB

Both orchestrators return an `OffsiteDppaResult`. Measured:

| | `base_settlement.hourly_ledger` | total `result.json` |
|---|---|---|
| `examples/samsung-ttc_combined-decision.example.json` | absent | **11.8 KB** |
| `generic_vn_dppa` (measured today) | 8,760 rows × 16 keys | **3.79 MB** (99.8 % ledger) |

That is a **320×** payload difference behind one type. Consequences, all live:

- `webapp/storage` writes 3.79 MB per generic run to `artifacts/webapp/runs/<id>/result.json`.
- `GET /api/runs/{run_id}` returns `{"status": …, "result": <3.79 MB>}` on every call.
- `webapp/compare.py` loads two of them.
- `results_view.render_standalone_report_html` **inlines the entire 3.79 MB**
  into the "report" a user downloads, as a `<script type="application/json">` blob.

The design question is real and worth deciding rather than drifting into: the
hourly ledger is genuinely valuable (it is the audit trail for a settlement
calculation, and it is what a counterparty's analyst will ask for). It just is
not a *summary result*. The clean split is `result.json` (summary blocks, the
Samsung shape) + a ledger served separately, with `GET /runs/{id}/ledger.csv` as
its own download and the API returning the summary only. CSV also happens to be
the format an analyst actually wants.

### F6 — The market proxy is shaped like the retail tariff, which inverts the one feature that matters for a solar CfD

`integration/market_reference.resolve_market_reference_series` falls back to:

```
market_price[h] = evn_retail_tou[h] × (wholesale_reference / weighted_retail)
                = evn_retail_tou[h] × 0.3355
```

This is honest about being a proxy — it is labeled `proxy_cfmp_or_fmp`, it
carries `proxy_fraction_of_evn` in provenance, and Q-903 explicitly adopted
"a flagged proxy beats a 422." I agree with that decision. But the *shape* has
a specific, known, directional error that the flag does not communicate:

- **EVN retail TOU** is a three-step administrative schedule. Midday
  (09:30–11:30) sits in the *peak* band; daytime generally sits in *normal*.
  So the proxy's market price is **highest exactly when solar generates most**.
- **Real Vietnamese FMP** is a market clearing price. With the solar fleet
  Vietnam has installed, the defining feature of the daily FMP curve is the
  **midday depression** — the cannibalization effect that is the single largest
  economic risk in a solar CfD anywhere in the world.

The proxy therefore gets the sign of the correlation between generation and
market price **backwards**. For a virtual/financial CfD this systematically
overstates the developer's merchant revenue and understates the buyer's CfD
top-up obligation — i.e. it flatters the deal in the direction a counterparty
will attack first.

The good news: the data file already has the slot. `vn_market_prices_2026.json`
carries `"hourly_shape_24": null` and nothing fills it. A documented 24-value
normalized intraday shape with a midday trough, sourced from published VN market
data (or, failing that, from a named comparable market with the substitution
recorded in the `_meta` block and a `regulatory-watch` row), converts the proxy
from "wrong shape, flagged as a proxy" to "approximate shape, flagged as a
proxy." That is a genuinely different quality of number, and it is a data-file
edit plus ~20 lines in `market_reference.py`.

### F7 — The webapp forks load ingestion, and uses the weaker of the two paths

| | `ingestion/loader.py` | `webapp/uploads.py` |
|---|---|---|
| Lines | 342 | 47 |
| Coverage | 81 % | 94 % |
| Formats | CSV, XLSX (multi-sheet scan), JSON | CSV, XLSX (first column) |
| Column detection | header matching (`_match_column_header`, `_detect_load_column_index`) | first column, always |
| Resolution | detects 15-min / 30-min / hourly (`_guess_resolution`) | must be exactly 8760 rows |
| Missing values | interpolates, reports `missing_count` / `interpolated_indices` | hard error |
| Negatives | clips, reports `clipped_negative_count` | passes through unchecked |
| Used by | the bespoke case pipelines | **the web UI — the product surface** |

CON-002 says the webapp never forks analytics logic, and the golden-parity test
enforces it for the settlement path. Ingestion is the same principle one layer
earlier, and it is forked. The user-visible cost is concrete: an analyst with
15-minute interval data, or a two-column export with a timestamp, or a meter
file with three missing hours, gets `expected 8760 hourly kW values, got 35040`
from the product — while the library sitting next to it handles all three.

There is also nothing physical in either path. No plausibility screen on a load
profile: no zero-fraction check, no load-factor sanity, no order-of-magnitude
check against the stated plant size. A user who uploads kWh where kW was
expected, or MW where kW was expected, gets a confident wrong answer. The
schema's `load_cleaning` block exists to carry exactly this metadata and the
webapp path never populates it.

**Fix:** delete `webapp/uploads.py`'s parsers and route the upload through
`ingestion.loader.ingest_factory_load`, surfacing its `load_cleaning` summary on
the run page ("3 hours interpolated, 12 negative values clipped, resampled from
15-minute data"). That is a user-facing *feature* delivered by deleting code.

### F8 — The tests CI does not run are the ones that check the numbers

The ninth pass's Theme M worked: 26 silent runtime skips became declarative
markers, the skip budget is 0, and CI reports 0 skipped. That is a real
improvement in *auditability*. It is not an improvement in *enforcement* — the
same tests moved from an invisible bucket to a visible one. And the visible
bucket grew:

| | 8th pass | 9th pass | **today** |
|---|---|---|---|
| deselected in CI | 19 | 19 | **46** |
| skipped in CI | 26 | 26 | **0** |
| not enforced, total | 45 / 672 (6.7 %) | 45 / 672 | **46 / 704 (6.5 %)** |

Composition of the 46, measured today:

| Marker | Count | Heaviest files |
|---|---|---|
| `requires_artifacts` | **35** | `test_settlement_regression.py` (13), `test_factory_a_validation.py` (12), `test_single_owner_phase4.py` (4), `test_saigon18_phase3.py` (3) |
| `golden_machine` | 4 | `test_samsung_ttc_parity.py` |
| `network` | 4 | |
| `requires_nrel_key` | 4 | |
| `requires_julia` | 2 | |
| `requires_pysam_resource` | 1 | |

Read the top row again. **The settlement regression suite and the Factory-A
validation suite — 25 tests, the numeric heart of what this repo sells — run on
exactly one laptop.** CI enforces structure, contracts, error paths, and the
web/library parity invariant. It does not enforce a single economic number.

Two structural notes:

- **There is a skip budget and no deselect budget.** The mechanism that stopped
  skips from drifting has an exact twin that does not exist, and the deselect
  count went 19 → 46 in one sprint without tripping anything.
- **There is no coverage floor.** `--cov-report=term-missing` with no
  `--cov-fail-under`. Coverage went 85 → 82 in one sprint, and the module that
  drove the drop is the flagship feature (`generic_vn_dppa` at 56 %).

**Fix:** the `requires_artifacts` tests read git-ignored files that are
*regenerable from tracked sources*. Most of what they need is a handful of
summary JSONs, not the 8760-row solve outputs. Committing small, frozen
fixtures under `tests/fixtures/` (the `examples/` pattern the repo already uses
for golden runs) would bring the majority of those 35 into CI. Pair that with
`--cov-fail-under` and an assertion on the deselected count, and "CI green"
finally means "the numbers still hold."

### F9 — The package cannot be installed outside a source tree

`pyproject.toml` declares a distributable package with a `py.typed` marker, and
`AGENTS.md` designates `analysis` + `webapp` as "the type-checked, supported
surfaces." But nine modules locate their data by walking up a fixed number of
directories from `__file__`:

```
analysis/validation.py:25      parents[3].parent / "data" / "schemas"
integration/factory_a.py:29    parents[4]
integration/project_catalog.py parents[4]
webapp/forms.py:17             parents[4] / "scenarios" / "templates"
webapp/jobs.py:32              parents[4]
webapp/projects.py:15          parents[4] / "data" / "projects"
webapp/service.py:130          parents[4]      ← NREL_API.env
webapp/storage.py:83           parents[4]
reopt/preprocess.py:39         .parent × 5
```

`[tool.setuptools.package-data]` ships **only `py.typed`**. So `data/vietnam/`,
`data/schemas/`, `data/projects/`, and `scenarios/templates/` are all outside
the wheel, and every one of those paths resolves into `site-packages`' parent on
a non-editable install. The package works in exactly one configuration: an
editable install from this checkout, run from this checkout.

Note also that `analysis/validation.py` writes `parents[3].parent` where
everything else writes `parents[4]` — the same magic number expressed two ways,
which is what magic numbers do.

**Fix:** one `reopt_pysam_vn/paths.py` with `repo_root()` / `data_dir()` /
`schema_dir()`, honoring a `REOPT_PYSAM_VN_DATA_DIR` env override, and either
ship `data/` + `scenarios/templates/` as package data or document the source-tree
requirement honestly in `README.md`. This is a prerequisite for anything that
looks like deployment, and it removes nine copies of a fragile assumption.

### F10 — The reporting layer gained a tenth renderer

The ninth pass counted nine hand-rolled HTML builders in `scripts/` against two
unused shared templates in `assets/`. The count today is nine — plus a new tenth
renderer inside `src/`: `webapp/results_view.render_standalone_report_html`,
which builds a `<!doctype html>` string with inline `<style>` and deliberately
declined to reuse `assets/report-template.html` (its docstring says so, citing
the bespoke-vs-generalized input shape).

I do not think that decision was wrong at the time — the existing template was
built for the case modules' input shape. But the outcome is that the repo now
renders client-facing HTML through **twelve** independent code paths, and the
newest one produces a two-column metrics table plus a 3.79 MB inline JSON blob
(F5). What a user downloads from the product today is not a deliverable.

Census, for continuity with prior passes:

| Metric | 07-26 | 08-06 | 08-12 | **today** |
|---|---|---|---|---|
| `scripts/` Python LOC | — | 31,202 | 31,141 | **31,141** |
| `src/` Python LOC | — | 12,847 | 13,027 | **13,601** |
| ratio | — | 2.43 : 1 | 2.39 : 1 | **2.29 : 1** |
| `generate_*.py` count / LOC | 34 / 10,189 | 36 / 10,868 | 36 / 10,854 | **36 / 10,854** |
| hand-rolled HTML builders | 9 | 9 | 9 | **9 (+1 in `src/`)** |

The ratio is improving only because `src/` is growing. `scripts/` has not moved
in three passes, is not measured by coverage (`source = ["reopt_pysam_vn"]`),
and 17 test files still `sys.path.insert` into it and import scripts as modules
— the exact coupling `lessons.md` warns about from the 2026-06-12 shim removal.

The right sequencing has not changed and I would keep it: **after F1**. A report
generator over a pipeline nobody can reach is a report generator for two
historical deals. After F1, `render_standalone_report_html` becomes the natural
single renderer and the nine script builders become its migration backlog.

### F11 — The grid emission factor is sourced from a news article, and disagrees with the official figure

`vn_emissions_2024.json` carries `grid_emission_factor_tCO2e_per_mwh: 0.681`,
and its `_meta.source_url` is **`vietnamnews.vn/environment/1716087/…`** — a
newspaper article. Every CO₂ figure the toolkit emits rides on it.

The repo's own `docs/regulatory-watch.md` already records the conflict:

> `emissions` … 2023 factor 0.6592 tCO₂/MWh published (Official Letter
> 1726/BDKH-PTCBT); repo file still carries 0.681 — **UNVERIFIED (pending
> primary-source check)**, `Next review: 2026-09-12`

And the file's own `historical_context` block puts 2023 at 0.6598.

The gap is 3.3 %, which is small — but the *provenance* gap is not small, and
there is a product distinction hiding underneath it that is worth deciding
explicitly rather than by default:

- For a **corporate buyer's Scope 2 / RE100 claim**, the number that counts is
  the officially published MONRE factor (the Official Letter figure). That is
  the number an auditor will accept.
- For **physical grid-average avoided emissions**, the newer, higher 2024
  figure is arguably the better estimate.

The repo currently uses the second and reports it in contexts that read like the
first. I would carry **both**, keyed (`official_reporting_factor` /
`physical_grid_average_factor`), with the official one as the default for
buyer-facing output, and I would replace the newspaper URL with the Official
Letter citation. That closes the `UNVERIFIED` row with actual work rather than a
date bump — which is precisely what DEC-903 established as this repo's standard.

### F12 — Carried and small (all still open from the ninth pass)

- **`webapp/jobs.py:149` uses a bare `assert`** for a cache invariant in a
  production path. Under `python -O` it vanishes.
- **Three `status: complete` plans still sit in `plans/active/`**
  (`gap01-factory-ingestion`, `gap02-procurement-comparison`,
  `gap04-generalized-settlement`).
- **Three `ceba_*.md` (49 KB) still sit at the repo root** rather than `reports/`.
  `ceba-review/` (three tracked files including a `download_day2.py`) is also
  root-level and outside every documented convention.
- **The three `common/` stubs are still there at 0 % coverage** (DEC-909 said
  delete; not executed). `common/` remains three-quarters decorative.
- **New, tiny:** `extracted_inputs.schema.json` documents `generation_kw` as
  used "when a PVWatts resource is unavailable"; the code prefers it *first*,
  above PVWatts. Doc and code disagree about precedence.
- **41 test files still `sys.path.insert(REPO_ROOT/"src"/"python")`** despite
  `pythonpath` in `pyproject.toml` — up from 32 at the ninth pass, because new
  test files copy the pattern. It masks a genuinely broken install.

---

## 3. Themes

### Theme N (#1, new) — Close the last mile

F1. A generic `build_extracted_inputs(deal_config)` in `analysis/`, plus the
small extraction of a VND-denominated EVN TOU series out of `preprocess`, wired
into `webapp/service._run_offsite()` and the CLI. Ship with the webapp test that
would have caught it: a form submission for an unregistered case with only a
load CSV reaches `done`.

**Sizing: ~1 day.** This is the difference between "the generic path exists" and
"a person can use the generic path," and every prerequisite already exists.

### Theme O (#2, new, and the one I would not defer) — Make the physical model honest

F2 + F3 + F4, in that order of blast radius:

1. Record the resolved resource file, its coordinates, and the distance to the
   site in `quality`; warn past a threshold; stop labeling a fallback `pvwatts`.
2. Set `array_type` / `tilt` explicitly at both call sites from a
   `plant.mounting` field; default fixed-tilt.
3. Fix `_calibrate_to_target`'s night-hour injection and cover all four
   generation-resolution branches.
4. Un-`xfail` `test_capacity_factor_benchmark.py` and make it the CI-enforced
   plausibility gate it was written to be.
5. *(stretch)* Three or four regional TMY files selected by the region the map
   picker already derives.

**Sizing: ~1 sprint** for items 1–4; item 5 adds ~1 day plus the resource fetch.

This is the first pass to look at the physics, and it found three defects that
each move a headline number by 10–25 %. Nine passes of process integrity are
worth much less if the generation profile is a different province with the wrong
racking. I would run this *concurrently* with Theme N, not after it.

### Theme P (#3, new) — Decide the result payload contract

F5. Split `OffsiteDppaResult` into a summary (the Samsung shape, ~12 KB) and a
separately-served hourly ledger (`GET /runs/{id}/ledger.csv`). Stop inlining
3.79 MB into a downloadable HTML file. Cheap, and it unblocks Theme A.

**Sizing: half a day.**

### Theme Q (#4, new) — Enforce what is now merely measured

F8. Add a deselect budget alongside the skip budget; add `--cov-fail-under`
pinned at today's 82 %; and bring the `requires_artifacts` numeric-regression
tests into CI by freezing small tracked fixtures (the `examples/` pattern this
repo already uses). Target: `test_settlement_regression.py` (13) and
`test_factory_a_validation.py` (12) first — 25 of the 35.

**Sizing: ~1 sprint** for the fixtures; the two budgets are an hour.

### Theme R (#5, new) — Unify load ingestion

F7. Route `webapp/uploads.py` through `ingestion/loader.py` and surface the
`load_cleaning` summary on the run page. Add a plausibility screen (zero
fraction, load factor, magnitude vs stated plant size). A user-facing feature
delivered mostly by deleting code.

**Sizing: ~1 day.**

### Theme S (#6, new) — Give the market proxy a shape

F6. Fill `hourly_shape_24` in `vn_market_prices_2026.json` with a documented,
cited intraday shape carrying the midday solar depression; consume it in
`market_reference`; add the `regulatory-watch` row. Keep every existing flag.

**Sizing: ~1 day**, most of it sourcing.

### Theme T (#7, new) — One path resolver, and an installable package

F9. `reopt_pysam_vn/paths.py`, env-overridable, replacing nine `parents[N]`
walks; ship `data/` + `scenarios/templates/` as package data or document the
source-tree requirement. Prerequisite for deployment of any kind.

**Sizing: ~1 day.**

### Theme A (#8, carried, unchanged) — Consolidate the reporting layer

F10. Nine script builders + the new `results_view` renderer onto one path. Still
correctly sequenced **after** Theme N and Theme P.

**Sizing: ~1 sprint.**

### Carried, unstarted — webapp → deck export

The 07-24 pass's Finding A stands, unchanged, for the fourth pass running. It is
a consumer of N, P, and A.

---

## 4. Suggested sequencing

| # | Item | Size | Why here |
|---|---|---|---|
| 1 | **Theme N** — generic `extracted` assembler; form + load CSV reaches `done` | ~1 day | Makes two sprints of prior investment usable; every ingredient exists |
| 2 | **Theme O items 1–4** — resource provenance + explicit array config + clip fix + un-`xfail` the CF gate | ~1 sprint | Three defects that each move a headline number 10–25 %; the flagship module is 56 % covered |
| 3 | **Theme P** — split summary from hourly ledger | half day | 3.79 MB per run is already in production; cheap and unblocks reporting |
| 4 | **Theme Q** — deselect budget + coverage floor + fixtures for the 25 numeric-regression tests | ~1 sprint | "CI green" should mean the numbers hold, not just the contracts |
| 5 | **Theme R** — unify load ingestion | ~1 day | User-facing capability, mostly by deletion; natural pair with #1 |
| 6 | **Theme S** — intraday market shape | ~1 day | Fixes the sign of the solar/price correlation; slot already exists |
| 7 | **Theme T** — one path resolver + package data | ~1 day | Prerequisite for deployment; retires nine copies of a fragile assumption |
| 8 | **Theme A** — reporting consolidation | ~1 sprint | Strictly better after #1 and #3 |
| 9 | webapp → deck export | ~1 sprint | Consumer of #1, #3, #8 |
| — | **F12 hygiene** | ~1 hour | Fold into whichever sprint runs first; it has survived two passes as a separate line item, which is how it keeps not happening |

**If only one item runs: #1.** **If two: #1 and #2 in parallel** — they touch
different files (`analysis/extracted.py` + `webapp/service.py` vs
`orchestrators/generic_vn_dppa.py` + `pysam/pvwatts_battery.py`) and together
they turn the generic path into something both reachable and defensible.

---

## 5. Decisions self-resolved this pass (no user input was solicited, per workflow)

- **DEC-1001** — Write a roadmap rather than execute. Brainstorm-only workflow;
  no repo file modified except this document. *(carried from DEC-901)*
- **DEC-1002** — Lead with F1 (reachability) rather than F2–F4 (physics), even
  though the physics defects are larger in magnitude. F1 is one day and it is
  what makes the physics matter to anyone outside this repo. *(auto-selected)*
- **DEC-1003** — Do **not** recommend deferring Theme O behind Theme N. Nine
  passes have audited process truth and none has audited physical truth; a
  fourth pass of "sequence it later" would be the same mistake this repo has
  already corrected twice for the reporting layer. Run them concurrently.
  *(auto-selected)*
- **DEC-1004** — Classify F2 as primarily a **provenance** defect and only
  secondarily a data-coverage defect. A single reference year is a defensible
  choice for a toolkit this size; labeling a 350 km substitution as `"pvwatts"`
  is not. Fix the label first (hours), the resource library second (a day).
  *(auto-selected)*
- **DEC-1005** — Treat the `xfail` on `test_capacity_factor_benchmark.py` as
  **mis-classified, not drift**. It was filed under "numeric benchmark drift"
  alongside four genuine tolerance failures; it is the repo's only physical
  plausibility gate and F3 shows the production path is outside its band for a
  structural reason. Recommend re-opening it under Theme O rather than leaving
  it in the drift backlog. *(auto-selected)*
- **DEC-1006** — For F3's default, choose **fixed-tilt**, not tracking. Rooftop
  and small C&I ground-mount dominate this repo's cases, PySAM's tracking default
  was inherited rather than chosen, and the conservative number is the defensible
  one in a client deliverable. Make it explicit and overridable via
  `plant.mounting`. *(auto-selected)*
- **DEC-1007** — For F5, split the payload rather than truncate the ledger. The
  hourly ledger is the audit trail for a settlement and a counterparty will ask
  for it; the fix is where it is served from, not whether it exists. Serve it as
  CSV. *(auto-selected)*
- **DEC-1008** — For F11, carry **both** emission factors keyed by purpose, with
  the officially published figure as the default for buyer-facing output. A
  single number cannot serve both a Scope 2 claim and a physical-grid estimate,
  and picking one silently is how the current mismatch arose. *(auto-selected)*
- **DEC-1009** — Recommend a **deselect budget**, not a reduction of the marker
  set. The markers are correct and well-documented; the missing piece is the
  same ratchet the skip budget provides. *(auto-selected)*
- **DEC-1010** — Pin `--cov-fail-under` at **82 %** (today's actual), not at the
  historical 85 %. A floor that fails on the first push is a floor that gets
  removed. Raise it as Theme O and Theme Q land. *(auto-selected)*
- **DEC-1011** — Do not touch `examples/samsung-ttc_combined-decision.example.json`.
  Carried unchanged from DEC-910 / DEC-809 / DEC-706 / CON-001. *(auto-selected)*
- **DEC-1012** — Do not re-propose vectorizing the settlement engine. DEC-908
  measured it (23.1 ms per settlement, 0.49 s per 21-point sweep); the sweep
  still runs inside a sub-second budget today. Recording it again so an eleventh
  pass does not rediscover it. *(auto-selected)*

## 6. Assumptions & constraints

- **ASM-1001** — F2's yield comparison for the Mekong Delta (1,300–1,450
  kWh/kWp) is from general knowledge of Vietnamese solar resource, **not
  measured in this repo** — the repo has no Delta resource file, which is the
  finding. The 1,888 kWh/kWp figure for the Ninh Thuan file **is** measured
  (PySAM, this machine, today). Treat the comparison as directional and the
  repo-side number as exact.
- **ASM-1002** — F3's fixed-vs-tracking delta (+23.6 %) is measured on the Ninh
  Thuan resource file with `losses=14`, `dc_ac_ratio=1.2`, `azimuth=180`. The
  magnitude will differ by site and by racking, but the *sign and rough scale*
  hold anywhere in Vietnam.
- **ASM-1003** — F4's night-injection percentages are exact for the deterministic
  synthetic shape and the three (cap, target) pairs listed. They are worst-case
  illustrations: the effect is zero when the annual target is feasible without
  clipping, which is the common case for a well-specified deal. The defect is
  that an *over*-specified deal produces a plausible-looking wrong answer with
  no warning, not that every deal is affected.
- **ASM-1004** — F6's claim about the Vietnamese FMP midday depression is drawn
  from the general economics of high-solar-penetration markets, not from an
  ingested VN market series — the repo has none, which is the finding. The
  *repo-side* half of the claim (the proxy is strictly proportional to the retail
  TOU shape, so its market price peaks in solar hours) is read directly from
  `market_reference.py` and is certain. Sourcing a real shape is Theme S's work.
- **ASM-1005** — F1's reproduction used `fastapi.testclient.TestClient` with
  `REOPT_PYSAM_VN_WEBAPP_RUNS_DIR` pointed at a scratch directory outside the
  repo. The run reached `state: error` / `MISSING_INPUTS` cleanly — no 500, no
  dangling `queued`. The ninth pass's F3 fix holds; this is a *different*
  finding about a path that never had inputs, not a regression of that one.
- **ASM-1006** — I did not verify the two `UNVERIFIED` regulatory rows against
  primary sources. That is Theme O/F11's work item, and the repo's own watch
  file already states the conflict; I am reporting the conflict, not resolving it.
- **ASM-1007** — F9's claim that a non-editable install breaks is by inspection
  of the nine `parents[N]` sites and `[tool.setuptools.package-data]`, not by
  building a wheel and installing it into a clean venv. The inspection is
  unambiguous (only `py.typed` is shipped), but the empirical check is a
  ten-minute confirmation worth doing at the start of Theme T.
- **CON-1001** — CON-001 holds: Samsung/TTC bit-exact parity remains the goal and
  the golden is untouched. **Note for Theme O:** fixing F2/F3 will move Samsung's
  PVWatts-derived numbers. The parity test is `golden_machine`-marked and already
  `xfail`ed, so it will not break CI — but the change must be recorded
  deliberately in `reports/`, not absorbed silently.
- **CON-1002** — CON-002 holds and is CI-enforced
  (`test_samsung_ttc_web_api_matches_direct_library_call_bit_exact`). Theme N
  must keep it passing: the assembler belongs in `analysis/`, called by the
  webapp, never reimplemented in `webapp/`.
- **CON-1003** — CON-004 holds: `ContractParams` fields may not be renamed or
  made required.
- **CON-1004** — Windows-first repo. Themes N, P, Q, R, S, T are pure Python;
  Theme O touches PySAM, which lives only in the repo `.venv` (Py 3.12).
- **CON-1005** — Analysis-only pass. The only file written is this brainstorm;
  all reproduction scripts were written to the session scratchpad.

## 7. Out of scope

- Executing any of the above (brainstorm-only workflow).
- Rotating the NREL API key — out-of-band human action, see Q-1001.
- Re-litigating the Samsung parity divergence's root cause; timeboxed and
  documented in `reports/2026-07-26-samsung-parity-diagnosis.md`. **But see
  F2/F3**: if the golden was generated against the Ninh Thuan resource with
  tracking defaults, that is a plausible contributing mechanism nobody has
  looked at, and Theme O would surface it as a side effect.
- Reviving the Julia path. DEC-004 / DEC-705 (archive in place) stands.
- Multi-tenant auth, cloud hosting, containerization.
- Optimizing the settlement engine (DEC-1012 — measured twice now).

## 8. Open questions (with adopted defaults, since no input is solicited)

1. **Q-1001 (open across TEN sessions, ~47 days):** Has the NREL key from
   commits `3911032` / `b14bc0b` been rotated?
   - *Adopted default:* assume **no**. Unchanged, and still the only item in
     this document that cannot be closed from inside the repo.
2. **Q-1002 (new):** Should the generic path be allowed to run at all when no
   solar resource within N km of the site is available?
   - *Adopted default:* **yes, with a loud `quality.warnings` entry naming the
     substituted resource and the distance.** Refusing would reintroduce the
     422 the ninth pass just removed; a flagged approximation is this repo's
     established and correct answer (Q-903). But the flag must name the
     substitution, which today it does not.
3. **Q-1003 (new):** What racking default should a deal with no `plant.mounting`
   get?
   - *Adopted default:* **fixed-tilt at tilt = latitude**, per DEC-1006 — the
     conservative, defensible choice for a client deliverable. Tracking becomes
     an explicit opt-in.
4. **Q-1004 (new):** Should the hourly ledger ship as CSV or Parquet?
   - *Adopted default:* **CSV.** No new dependency, an analyst can open it, and
     3.79 MB of JSON is roughly 1 MB of CSV. Parquet is the right answer only
     once someone is loading many runs programmatically, which nobody is.
5. **Q-1005 (new):** For F11, which emission factor should be the default in
   buyer-facing output?
   - *Adopted default:* **the officially published MONRE figure**, with the
     physical-grid-average carried alongside under a distinct key. An auditor
     will accept the first and question the second.
6. **Q-1006 (carried, unanswerable from the repo):** Has any deliverable already
   gone to an external counterparty carrying a non-26,400 FX rate or pre-audit
   Single-Owner defaults?
   - *Adopted default:* unresolvable by inspection. **F2 and F3 widen this
     question considerably** — any PySAM-derived solar number in any shipped
     deliverable was computed on Ninh Thuan irradiance with tracking defaults.
     A recipient list would now be worth having for two independent reasons.

## 9. Suggested next step

**If the next session's budget is small: Theme N.** Write
`analysis/extracted.py::build_extracted_inputs(deal_config)`, extract
`build_evn_tou_series_vnd_per_kwh` from `reopt/preprocess`, call the assembler
from `webapp/service._run_offsite()` when `extracted is None` and
`deal_config.load.loads_kw` is present, add `--derive-extracted` to the CLI, and
ship the test that would have caught this: a `/api/deals` multipart submission
for an unregistered case with only a load CSV reaches `state: done` with
`quality.orchestrator == "generic_vn_dppa"`. Verify with `gh run list`, not a
local run. That single day converts the last two sprints from a library
capability into a product motion.

**If there is room for one substantial item: Theme O items 1–4, in parallel.**
Record the resolved solar resource file, its coordinates, and its distance from
the site in `quality`, and stop calling a 350 km substitution `"pvwatts"`; set
`array_type` and `tilt` explicitly at both PVWatts call sites from a new
`plant.mounting` field defaulting to fixed-tilt; fix `_calibrate_to_target` so
AC clipping never redistributes energy into hours with no sun, and cover all
four generation-resolution branches; then re-open
`test_capacity_factor_benchmark.py` as the CI-enforced plausibility gate it was
written to be. Record the resulting movement in Samsung's numbers deliberately
in `reports/` — CON-1001 permits the movement, but not the silence.
