---
title: "CI Gate Integrity, Truth Sweep, FX Derivation, and a Second Offsite Orchestrator"
date: "2026-08-06"
status: "draft"
request: "Execute the 2026-08-06 gate-integrity brainstorm: restore CI integrity with a pinned dev toolchain and cleared ruff backlog, finish the truth sweep across AGENTS.md / webapp README / drift test / stale branches / regulatory-watch dates, complete the FX derivation by dropping the caller_value pins, and register a second offsite DPPA orchestrator so the public analysis API serves more than one deal."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-08-06-reopt-pysam-gate-integrity-brainstorm.md"
  - "research/2026-07-26-reopt-pysam-post-backlog-architecture-brainstorm.md"
---

# Plan: CI Gate Integrity, Truth Sweep, FX Derivation, and a Second Offsite Orchestrator

## Objective

Restore the repository's continuous-integration pipeline, which has failed on
every push since 2026-07-26, then close the three structural gaps that the red
pipeline masked: documentation that still advertises guarantees the code does not
make, an exchange-rate resolver whose data layer is never actually consulted, and
a public offsite/DPPA analysis API that can execute exactly one deal. This
matters now because the toolkit's outputs go to external counterparties, five
commits have already landed on an unverified pipeline, and the single-deal
limitation blocks every downstream initiative (reporting pipeline, deck export)
that the project has queued behind it.

## Context Snapshot

- **Current state:**
  - **CI is red.** The three most recent GitHub Actions runs on `main`
    (`30211921197` 2026-07-26, `30693998928` 2026-08-01, `30722078575`
    2026-08-01) all fail at the `Lint (ruff)` step. The last green run
    (`30135167312`, 2026-07-24) predates the lint gate. `Install dependencies`
    succeeds on both matrix legs; the `mypy` and `pytest` steps have therefore
    **not executed in CI since 2026-07-24**.
  - `.github/workflows/ci.yml` installs `mypy pytest pytest-cov ruff` with no
    version constraints. The ruff release current when the gate was written
    defaulted to rule set `["E4", "E7", "E9", "F"]`; ruff 0.16 expanded the
    default selection. The unmodified tree now reports **766 violations**
    (606 auto-fixable). Under the historical narrow selection the same tree
    still reports `All checks passed!`.
  - The local suite is green: `634 passed, 18 deselected, 3 xfailed`, 85 % line
    coverage over 4,713 statements. `mypy` passes locally
    (`Success: no issues found in 21 source files`).
  - `reopt_pysam_vn.analysis.offsite_dppa._ORCHESTRATORS` contains exactly one
    entry, `"DPPA_SAMSUNG_TTC"`. `register_orchestrator` is exported in
    `__all__` and called from nowhere in `src/`, `scripts/`, or `tests/`. Any
    other `DealConfig.case` raises `ValueError: no offsite orchestrator
    registered for case '…'`.
  - `common/assumptions.py` implements a documented four-step precedence chain,
    but 14 call sites pass `caller_value=<literal>`, which is step 1 and always
    wins — so the data layer is never reached at those sites.
  - `src/python/reopt_pysam_vn/webapp/README.md` lines 63–66 claim the webapp
    parity test "proves the web API path reproduces
    `examples/samsung-ttc_combined-decision.example.json` bit-for-bit"; that
    test's own module docstring states it "deliberately does NOT re-assert
    parity" against that golden.
  - `AGENTS.md` §4 carries a "Test Suite Status (last run: Mar 2026)" table and
    §6 lists a next step to implement the 20 % Decree 57 export cap, which
    Decree 243/2026 repealed on 2026-06-26.
- **Desired state:**
  - CI is green on both matrix legs, with every gate tool pinned to an exact
    version so a third-party release cannot break the build.
  - No document in the repository claims a guarantee the code does not enforce.
  - Editing `data/vietnam/vn_deal_defaults_2026.json`'s exchange rate changes
    the resolved rate in every general-purpose module.
  - `reopt_pysam_vn.analysis.run_offsite_dppa` executes at least two distinct
    deals, and the orchestrator contract accommodates deals that consume a REopt
    results dict rather than deriving generation internally.
- **Key repo surfaces:**
  - `.github/workflows/ci.yml`, `pyproject.toml`
  - `src/python/reopt_pysam_vn/analysis/offsite_dppa.py` (89 lines),
    `analysis/types.py` (200 lines), `analysis/__init__.py`
  - `src/python/reopt_pysam_vn/integration/dppa_case_1.py` (347 lines),
    `integration/dppa_samsung_ttc.py` (1,064 lines)
  - `src/python/reopt_pysam_vn/common/assumptions.py` (68 lines)
  - `src/python/reopt_pysam_vn/webapp/README.md`, `webapp/service.py`
  - `tests/python/webapp/test_golden_parity.py`,
    `tests/python/test_repo_invariants.py`,
    `tests/python/integration/test_dppa_case_1.py`
  - `AGENTS.md`, `activeContext.md`, `docs/regulatory-watch.md`
- **Out of scope:**
  - Rotating the NREL Developer API key committed in history (commits
    `3911032`, `b14bc0b`) — an out-of-band human action; see ASM-011.
  - Root-causing or repairing the Samsung/TTC `developer_irr_fraction`
    divergence itself. It was timeboxed and documented in
    `reports/2026-07-26-samsung-parity-diagnosis.md`; this plan changes only how
    it is *reported*.
  - Regenerating `examples/samsung-ttc_combined-decision.example.json` (CON-001).
  - Consolidating the 36 `generate_*.py` report builders onto
    `assets/report-template.html` — a separate initiative sequenced after this
    plan.
  - The webapp → PPTX deck export endpoint.
  - Reviving the archived Julia layer under `legacy/julia/`.
  - Registering a third or fourth orchestrator. This plan adds exactly one.

## Environment & Conventions

- **Stack:** Python 3.10+ declared (`requires-python = ">=3.10"` in
  `pyproject.toml`); Python 3.12 is the interpreter that works locally.
  Package manager is **`pip` with an editable install — not `uv`, not
  `poetry`**. Web layer: FastAPI + Uvicorn + Jinja2. Finance: `nrel-pysam`
  7.1.0 (the only currently pinned dependency), `numpy-financial`. No lockfile
  exists. CI runs a two-leg matrix on `ubuntu-latest`: Python 3.10 and 3.12.
- **Setup:**
  ```bash
  python -m pip install -e ".[webapp]"
  python -m pip install "ruff==0.16.1" "mypy==2.3.0" "pytest==8.4.2" "pytest-cov==7.1.0"
  ```
  On the primary Windows development machine, PySAM and `python-pptx` are
  installed **only** in the repository-local `.venv` (Python 3.12). Use
  `.venv/Scripts/python.exe` there in place of bare `python`.
- **Build / Run:**
  ```bash
  # Web app (localhost only)
  PYTHONPATH=src/python python -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000

  # Analysis CLI
  PYTHONPATH=src/python python -m reopt_pysam_vn.analysis offsite_dppa \
    --config scenarios/case_studies/samsung_ttc/samsung_ttc_deal_config.json \
    --extracted data/interim/samsung_ttc/samsung_ttc_extracted_inputs.json --out out.json
  ```
- **Test:** full portable suite — exactly what CI runs:
  ```bash
  PYTHONPATH= python -m pytest tests/python \
    -m "not network and not requires_artifacts and not golden_machine and not requires_julia" \
    -q --cov=reopt_pysam_vn --cov-report=term-missing
  ```
  Baseline before any change in this plan: `634 passed, 18 deselected, 3 xfailed`,
  85 % coverage, 90–135 s wall time.

  Single test:
  ```bash
  PYTHONPATH= python -m pytest tests/python/analysis/test_offsite_dppa.py -v
  ```
  Type gate:
  ```bash
  mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp
  ```
  Lint gate:
  ```bash
  ruff check src scripts tests
  ```
  CI status (this is a required verification step in this plan, not optional):
  ```bash
  gh run list --limit 3
  ```
- **Conventions & traps:**
  - **`PYTHONPATH` trap (critical):** a global `PYTHONPATH` pointing at an
    unrelated `hermes-agent` virtualenv shadows this repository's dependencies
    and breaks webapp tests with
    `ModuleNotFoundError: pydantic_core._pydantic_core`. **Always clear it**
    (`PYTHONPATH=` prefix) when running pytest. Set `PYTHONPATH=src/python`
    **only** when invoking `uvicorn` or scripts directly — pytest does not need
    it (`[tool.pytest.ini_options] pythonpath` handles it).
  - **Currency:** all VND amounts are **VND per kWh** or **VND absolute**,
    always **excluding VAT**. USD conversion is always **divide by
    VND-per-USD**. The canonical rate is **26,400 VND/USD**. Never write a bare
    numeric exchange-rate literal in new code.
  - **Data layer:** every file in `data/vietnam/` uses a
    `{"_meta": {...}, "data": {...}}` envelope, and code reads **only** the
    `data` block. To update policy data, create a **new versioned file** and
    change one line in `data/vietnam/manifest.json` — never edit a published
    file's numbers in place.
  - **JSON reads use `encoding="utf-8-sig"`** throughout — Windows editors emit
    a byte-order mark and every reader in this repository tolerates it. Match
    that in any new reader.
  - **Time:** all 8760-hour series are hour-of-year indexed `[0..8759]`, local
    Vietnam time (UTC+7), non-leap-year basis.
  - **Scripts are canonical-only:** they live at
    `scripts/python/{reopt,pysam,integration}/<name>.py`. A flat
    `scripts/python/*.py` file is banned and mechanically enforced by
    `tests/python/test_repo_invariants.py::test_no_flat_python_scripts`.
  - **Generated outputs are git-ignored:** `artifacts/`, `reports/*.html`,
    `present/`, `scenarios/generated/`. Tracked deliverables are `reports/*.md`,
    `examples/`, `tests/baselines/`.
  - **Public API boundary:** `reopt_pysam_vn.analysis` and
    `reopt_pysam_vn.webapp` are the type-checked, supported surfaces (`mypy`
    gate plus a `py.typed` marker). `integration`, `reopt`, and `pysam` are
    internal engines and may change shape without a deprecation cycle.
  - **`bool` is a subclass of `int` in Python.** Any numeric comparison or type
    check must guard `bool` **before** `int`, or decision flags get compared as
    numbers. This has bitten this repository before.
  - Line length is capped at 120 (`[tool.ruff] line-length = 120`). Do not
    reformat unrelated code.
- **Repo map:**
  ```
  data/vietnam/          Versioned policy JSON + manifest.json (the data layer)
  data/interim/          Per-deal *_extracted_inputs.json payloads
  data/schemas/          JSON Schemas (deal_config, extracted_inputs)
  src/python/reopt_pysam_vn/
    analysis/            PUBLIC API: DealConfig, run_onsite, run_offsite_dppa, CLI
    common/              assumptions.py — the canonical assumption resolver
    reopt/               REopt preprocessing, regime resolution, tariff deltas
    pysam/               PySAM Single Owner finance, PVWatts
    integration/         Per-deal orchestration engines + settlement engine
    webapp/              FastAPI localhost UI over analysis/
  scripts/python/{reopt,pysam,integration}/   ~106 workflow + report scripts
  tests/python/          The CI-collected suite
  tests/cross_language/  Julia-vs-Python parity (NOT collected by CI)
  legacy/julia/          Archived Julia preprocessing/solve layer
  ```

## Research Inputs

- From `research/2026-08-06-reopt-pysam-gate-integrity-brainstorm.md`:
  - CI has failed at `Lint (ruff)` on every push since 2026-07-26 — three
    consecutive runs across eleven days and five commits — while
    `activeContext.md` states "CI status: Green on `main`". The root cause is an
    unpinned linter whose default rule set expanded between releases, not a code
    regression.
  - The 766 current violations break down as `UP006` non-pep585-annotation ×224,
    `I001` unsorted-imports ×142, `RUF100` unused-noqa ×101, `UP045`
    non-pep604-annotation-optional ×97, `ISC004` ×57, `UP035` ×39, `BLE001`
    blind-except ×14, `DTZ001` ×11, `S110` try-except-pass ×5, plus ~80 others.
    606 are auto-fixable.
  - The 101 `RUF100` violations are ruff flagging the `# noqa: E402` comments the
    lint-gate phase itself added, because `E402` is now globally ignored in
    `[tool.ruff.lint]`. The configuration is self-inconsistent under the new
    rule set.
  - `run_offsite_dppa` serves exactly one deal; `run_onsite` by contrast is
    genuinely generic (184 lines, no per-deal branching). Offsite was given a
    front door with one key cut for it.
  - The FX unification achieved **unification** (one value everywhere) without
    **derivation** (one source of truth): 14 call sites pin `caller_value`, so
    editing the canonical data file moves 5 sites, not 19.
  - Unpinning is provably value-preserving *right now* precisely because all
    general-purpose sites already agree with the data layer at 26,400 — the
    window closes the moment any rate diverges again.
  - `tests/python/webapp/test_golden_parity.py::test_samsung_ttc_golden_drift_is_the_known_pre_existing_gap`
    asserts the drift **exists**, so the suite is green *because* the analytics
    are wrong and fixing them would turn CI red.
  - `docs/regulatory-watch.md` marks rows "CURRENT" with no verification date,
    making the claim unfalsifiable. A live check on 2026-08-06 found the EVN
    average retail price of 2,204.0655 VND/kWh (ex-VAT) still standing, so this
    is a process gap, not a known-wrong number.
  - Every unattended verification pass so far has verified by running the suite
    locally; none has run `gh run list`. Local green and CI green are different
    claims.
- From `research/2026-07-26-reopt-pysam-post-backlog-architecture-brainstorm.md`:
  - The canonical VND/USD rate is **26,400**, sourced from
    `vn_tariff_2025.json._meta.exchange_rate_vnd_per_usd` (Decision 599/QD-EVN,
    2025-05-10) and mirrored with a citation in `vn_deal_defaults_2026.json`.
  - Deals with a contractually fixed different rate carry it as an explicit
    per-deal override, never as a module constant. The Saigon18 / DPPA-case-3
    family legitimately uses 25,450 VND/USD on that basis.
  - Value-preserving refactors and value-changing flips must ship as **separate
    commits**, never one, so that a golden movement can be attributed.
- From `lessons.md` (repository root, 2026-06-12 entries):
  - After **any** structural move, run the **full** test suite — `--collect-only`
    is not enough, and running a subset previously missed integration-test
    breakage.
  - When a numeric test fails after a refactor, prove cause versus pre-existing
    by running it at the prior commit in a `git worktree` before assuming it is
    yours.
  - Scope `.gitignore` negations precisely and run `git status` afterward.

## Assumptions and Constraints

- **ASM-001:** The 766 ruff violations are caused by ruff's expanded default
  rule selection, not by code changes — verified because the same tree under
  `--select E4,E7,E9,F --ignore E402` reports `All checks passed!`. The exact
  release boundary was not bisected. **BINDING DEFAULT:** pin `ruff==0.16.1` and
  clear the violations against that version. If `ruff --version` after install
  reports anything other than `0.16.1`, stop and correct the pin before
  proceeding — the counts in this plan are measured against 0.16.1 only.
- **ASM-002:** The `mypy` and `pytest` CI steps have not run since 2026-07-24
  because the lint step fails first. They may or may not be green on the
  3.10 leg. **BINDING DEFAULT:** treat PHASE-01 as potentially uncovering
  further CI failures behind the lint step. If the 3.10 leg fails at `mypy` or
  `pytest` after lint is fixed, fix it within PHASE-01 rather than deferring —
  the phase is not complete until both legs are green end to end.
- **ASM-003:** The expanded ruff rules should be adopted permanently rather than
  narrowed back to the historical selection. **BINDING DEFAULT:** keep the
  expanded default set. The annotation modernizations (`UP006`, `UP045`,
  `UP035`) are safe because every module in `src/` and `tests/` already carries
  `from __future__ import annotations`, and the diagnostic rules (`BLE001`,
  `S110`, `DTZ001`) surface real defects worth reading.
- **ASM-004:** `ISC004` implicit-string-concatenation-in-collection ×57 mostly
  flags multi-line string literals inside list/tuple literals in report-builder
  scripts, where the concatenation is intentional. **BINDING DEFAULT:** add
  `"ISC004"` to `[tool.ruff.lint] ignore` with an explanatory comment rather
  than rewriting 57 deliberate multi-line strings. Do **not** ignore `BLE001`,
  `S110`, or `DTZ001`.
- **ASM-005:** The second orchestrator target is **`dppa_case_1`**, not
  `ninhsim_solar_storage_60pct` and not `dppa_case_2`. Rationale established by
  direct inspection: `dppa_case_1` is 347 lines at 99 % coverage, its four
  builders chain entirely in-process, and
  `build_dppa_case_1_placeholder_pysam_results` provides a PySAM-free path.
  `dppa_case_2`'s chain is driven by separate phase scripts that read
  git-ignored intermediate JSON from `artifacts/` and cannot be composed
  in-process without substantial new plumbing.
  `ninhsim_solar_storage_60pct` is structurally an onsite case (its coverage
  function is the one `run_onsite` mirrors). **BINDING DEFAULT:** register
  `dppa_case_1` under case id `DPPA_CASE_1_NINHSIM`.
- **ASM-006:** The existing orchestrator contract
  `(extracted: dict, *, run_developer: bool) -> dict` is Samsung-shaped:
  Samsung derives its generation profile from PVWatts internally, whereas
  `dppa_case_1` consumes a REopt `results` dict and a `scenario` dict.
  **BINDING DEFAULT:** widen the contract to
  `(extracted, *, run_developer, results=None, scenario=None) -> dict` with all
  new parameters keyword-only and defaulted to `None`, so the existing Samsung
  orchestrator remains call-compatible and unchanged.
- **ASM-007:** `dppa_case_1`'s combined-decision artifact uses the key set
  `model / status / site_and_tariff_basis / reopt_summary / pysam_summary /
  comparison / decision / warnings`, which overlaps `OffsiteDppaResult`'s block
  vocabulary (`deal / base_settlement / strike_sweep / adder_sensitivity /
  regime_stress / decision / quality`) only at `decision`.
  **BINDING DEFAULT:** write a thin adapter that maps case-1 output onto the
  block vocabulary where a defensible mapping exists and preserves the complete
  original artifact under `raw["case_1_artifact"]`. Do **not** widen, rename, or
  reorder `_OFFSITE_BLOCKS` — that vocabulary is load-bearing for the Samsung
  golden comparison.
- **ASM-008:** No git-tracked REopt results fixture exists for DPPA case 1;
  real results live under git-ignored `artifacts/`.
  **BINDING DEFAULT:** the new orchestrator test builds its REopt results dict
  from a synthetic fixture, following the `_synthetic_results()` helper already
  present in `tests/python/integration/test_dppa_case_1.py` (line 49). Tests
  must be hermetic and must not be marked `requires_artifacts`.
- **ASM-009:** Of the 14 `caller_value=` pin sites, 9 pin the canonical 26,400
  and 5 pin the deal-specific 25,450. **BINDING DEFAULT:** unpin 8 of the 9
  (making them derive from the data layer), deliberately **keep** the pin at
  `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py:94` to insulate the
  parity-gated path from future data-layer edits, and **keep** all 5 of the
  25,450 deal-specific pins. Because the data layer holds exactly 26,400 today,
  the 8 unpinnings are bit-identical and change no published number.
- **ASM-010:** The three stale git branches (`real-project-data` last committed
  2026-03-03; `claude/clever-chaplygin-dad6dc` and `claude/kind-mcclintock-10b2e5`
  both 2026-05-06) may contain unique commits. **BINDING DEFAULT:** do not
  delete any branch whose `git log main..<branch>` output is non-empty. Record
  the unique-commit count for each in the phase report and leave such branches
  in place; delete only branches fully merged into `main`.
- **ASM-011:** The NREL Developer API key committed in commits `3911032` and
  `b14bc0b` has not been confirmed rotated across eight prior sessions.
  **BINDING DEFAULT:** out of scope for this plan. The existing "API key
  rotation required" section in `README.md` documents the requirement and must
  not be removed or weakened by any documentation edit in PHASE-02.
- **CON-001:** **Samsung/TTC bit-exact parity is inviolable.**
  `examples/samsung-ttc_combined-decision.example.json` must not be edited or
  regenerated by any phase of this plan.
- **CON-002:** The webapp must never fork analytics logic — it always calls
  `run_onsite` / `run_offsite_dppa` / `run_vietnam_reopt` from
  `reopt_pysam_vn` as-is. `tests/python/webapp/test_golden_parity.py::test_samsung_ttc_web_api_matches_direct_library_call_bit_exact`
  enforces this and must keep passing through PHASE-04.
- **CON-003:** `ContractParams` in
  `src/python/reopt_pysam_vn/integration/settlement.py` is constructed at 24
  call sites across 14 files. No change may rename a field or make an existing
  keyword argument required.
- **CON-004:** Windows-first repository. All CI changes target Linux runners;
  nothing may require a POSIX-only tool for local development.
- **CON-005:** The portable suite's passing count must never decrease. Baseline
  is `634 passed, 18 deselected, 3 xfailed`. A drop means something
  load-bearing was removed.
- **DEC-001:** Pin the gate tooling to exact versions rather than loosening the
  rule set. An unpinned gate that redefines itself between runs is the root
  cause; narrowing `select` would restore green while leaving the same trap
  armed for `mypy`.
- **DEC-002:** Clear the violations rather than suppress them wholesale, with the
  single documented exception in ASM-004.
- **DEC-003:** Widen the orchestrator contract rather than force `dppa_case_1`
  to synthesize a REopt results dict internally. The contract's Samsung shape is
  the actual defect; a second deal is what exposes it.
- **DEC-004:** Keep the drift tripwire in `test_golden_parity.py` but invert its
  polarity to a bounded, catalogued field manifest, so shrinking the divergence
  stays green and growing it turns red. Deleting it would re-hide the
  divergence.
- **DEC-005:** Add a CI-status check to the repository's own documented
  verification convention, not merely to this plan's steps. The blind spot cost
  eleven days; the instance is cheap to fix and the convention is what prevents
  recurrence.

## Specification

### S1 — Widened offsite orchestrator contract

The orchestrator callable signature becomes:

```
orchestrator(
    extracted: dict,
    *,
    run_developer: bool = True,
    results: dict | None = None,
    scenario: dict | None = None,
) -> dict
```

Symbols:
- `extracted` — the deal's `*_extracted_inputs.json` payload, the same dict the
  settlement engine consumes. Always required.
- `run_developer` — whether to run the PySAM developer-finance screen. When
  `False`, an orchestrator must still return a complete artifact, using a
  placeholder developer block rather than raising.
- `results` — a REopt results dictionary (the `results` block of a REopt solve
  output, containing `PV`, `Wind`, `ElectricStorage`, `ElectricUtility`, and
  `Financial` sub-dicts with 8760-length `*_series_kw` lists). `None` for
  orchestrators that derive generation internally.
- `scenario` — the REopt `Scenario` input dictionary the solve was built from,
  containing at minimum `Site` and `_meta`. `None` for orchestrators that do not
  need it.

Backward compatibility rule: an orchestrator registered before this change
accepts only `(extracted, *, run_developer)`. `run_offsite_dppa` must therefore
**only pass `results` and `scenario` when they are not `None`**, so existing
two-parameter orchestrators continue to be called with exactly the arguments
they accept.

### S2 — Orchestrator input resolution order

For each of `extracted`, `results`, and `scenario`, `run_offsite_dppa` resolves
in this exact order and stops at the first non-`None` hit:

1. The explicit keyword argument passed by the caller
   (`extracted=`, `results=`, `scenario=`).
2. `deal_config.raw[<name>]` — i.e. `deal_config.raw["extracted"]`,
   `deal_config.raw["results"]`, `deal_config.raw["scenario"]`.
3. `None`.

`extracted` resolving to `None` remains a hard error with the existing message.
`results` and `scenario` resolving to `None` is legal — it is the Samsung case.

### S3 — DPPA case-1 orchestrator composition

```
reopt_summary = build_dppa_case_1_reopt_summary(results, extracted, scenario)
pysam_results = (
    developer_runner(reopt_summary) if run_developer and developer_runner is not None
    else build_dppa_case_1_placeholder_pysam_results(reopt_summary)
)
comparison    = build_dppa_case_1_comparison(reopt_summary, pysam_results)
artifact      = build_dppa_case_1_combined_decision(reopt_summary, pysam_results, comparison)
```

Symbols:
- `developer_runner` — an optional callable performing the real PySAM Single
  Owner run. Not wired in this plan; when `run_developer=True` and no runner is
  injected, the placeholder path is used and a warning string is appended (see
  S4). This keeps the orchestrator hermetic and PySAM-optional, matching the
  existing behaviour of `build_dppa_case_1_placeholder_pysam_results`.

### S4 — Case-1 artifact → `OffsiteDppaResult` block mapping

`build_dppa_case_1_combined_decision` returns keys
`model / status / site_and_tariff_basis / reopt_summary / pysam_summary /
comparison / decision / warnings`. The adapter maps them as follows:

| `OffsiteDppaResult` block | Source in the case-1 artifact |
|---|---|
| `case` | the literal string `"DPPA_CASE_1_NINHSIM"` |
| `model` | `artifact["model"]` |
| `deal` | `artifact["site_and_tariff_basis"]` |
| `base_settlement` | `{"energy_summary": artifact["reopt_summary"]["energy_summary"], "optimal_mix": artifact["reopt_summary"]["optimal_mix"], "financial": artifact["reopt_summary"]["financial"]}` |
| `strike_sweep` | `{}` — case 1 is a fixed private-wire strike, it runs no sweep |
| `adder_sensitivity` | `{}` — not modelled for case 1 |
| `regime_stress` | `{}` — not modelled for case 1 |
| `decision` | `artifact["decision"]` |
| `quality` | `{"basis": "directional", "status": artifact["status"], "warnings": artifact["warnings"], "developer_basis": "placeholder" or "pysam"}` |
| `raw["case_1_artifact"]` | the complete unmodified `artifact` dict |

The three empty blocks are deliberate and must be `{}`, not omitted —
`OffsiteDppaResult.to_dict()` emits every block in `_OFFSITE_BLOCKS`
unconditionally, and an empty dict is the honest representation of "this deal
structure does not have that lever." Nothing is lost: `raw["case_1_artifact"]`
carries the full original.

`quality.developer_basis` is `"placeholder"` when
`build_dppa_case_1_placeholder_pysam_results` produced `pysam_results`, and
`"pysam"` when a `developer_runner` produced them.

### S5 — Bounded drift manifest (replaces the inverted drift assertion)

The current test asserts a specific field **differs** from the golden. Replace
with a manifest-bounded check:

1. Define `KNOWN_DRIFTED_PATHS`, a frozen set of dotted JSON paths currently
   known to diverge between a live `run_offsite_dppa` call and
   `examples/samsung-ttc_combined-decision.example.json`. Seed it with exactly
   the paths the diagnosis report names.
2. Compute the actual set of diverging leaf paths.
3. Assert `actual_drifted <= KNOWN_DRIFTED_PATHS` (subset, not equality).

Consequences, which are the point of the change:
- Fixing a divergence shrinks `actual_drifted` → still a subset → **green**.
- A *new* divergence appears → not in the manifest → **red**.
- Fixing everything → empty set → still a subset → **green**, and the manifest
  can then be emptied in a follow-up.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Restore CI: pin the gate toolchain, clear 766 ruff violations, confirm both matrix legs green | None | `pyproject.toml` `dev` extra, updated `ci.yml`, 766→0 violations, `gh run list` showing success |
| PHASE-02 | Truth sweep: reconcile every remaining document and tripwire with what is actually enforced | PHASE-01 | Corrected `AGENTS.md`, `webapp/README.md`, `dppa_samsung_ttc.py` docstring, re-polarized drift test, dated `regulatory-watch.md` + invariant, branch triage |
| PHASE-03 | Complete the FX derivation: make the data layer authoritative for the canonical rate | PHASE-01 | 8 unpinned call sites, a data-layer-authority test, delta memo confirming zero numeric movement |
| PHASE-04 | Widen the orchestrator contract and register a second offsite deal | PHASE-01, PHASE-03 | Widened contract in `offsite_dppa.py`, `analysis/orchestrators/dppa_case_1.py`, non-Samsung tests, webapp acceptance |

## Detailed Phases

### PHASE-01 - Restore CI Gate Integrity

**Goal**
Make the lint gate pass again, pin every gate tool to an exact version so a
third-party release cannot break the build, and prove both CI matrix legs are
green by querying GitHub Actions rather than by running the suite locally.

**Tasks**
- [ ] TASK-01-01: Record the pre-change baseline. Run
      `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q`
      and write the exact result line to `reports/2026-08-06-ci-restoration.md`
      (create the file). Expected: `634 passed, 18 deselected, 3 xfailed`.
- [ ] TASK-01-02: Install the exact gate versions:
      `python -m pip install "ruff==0.16.1" "mypy==2.3.0" "pytest==8.4.2" "pytest-cov==7.1.0"`.
      Confirm with `ruff --version` → `ruff 0.16.1`. If it reports a different
      version, stop and reconcile the pin (ASM-001).
- [ ] TASK-01-03: Capture the violation census before fixing:
      `ruff check src scripts tests --statistics > /tmp/ruff-before.txt`.
      Expected total: `Found 766 errors.`
- [ ] TASK-01-04: Add a `dev` optional-dependency group to `pyproject.toml`
      pinning `ruff==0.16.1`, `mypy==2.3.0`, `pytest==8.4.2`,
      `pytest-cov==7.1.0`.
- [ ] TASK-01-05: Add `"ISC004"` to `[tool.ruff.lint] ignore` with an
      explanatory comment (ASM-004). Leave the existing `"E402"` ignore and its
      comment in place.
- [ ] TASK-01-06: Run `ruff check --fix src scripts tests` to clear the 606
      auto-fixable violations. Do **not** pass `--unsafe-fixes`. Read the full
      diff before committing; specifically inspect every removed import under
      `src/python/reopt_pysam_vn/analysis/` and
      `src/python/reopt_pysam_vn/integration/`, where the orchestrator-registry
      pattern lives and a side-effecting import could look unused.
- [ ] TASK-01-07: Re-run `ruff check src scripts tests` and fix the residual
      manual violations by category. Expected residual categories after the
      auto-fix and the `ISC004` ignore: `BLE001` blind-except ×14,
      `DTZ001` call-datetime-without-tzinfo ×11, `DTZ011` call-date-today ×8,
      `S110` try-except-pass ×5, `UP035` deprecated-import ×39,
      `PLW1510` subprocess-run-without-check ×4, `C401` ×5, `RUF007` ×3,
      `RUF012` mutable-class-default ×3, `RUF046` ×3, `RUF059` ×3, `B008` ×2,
      `B009` ×3, `C408` ×2, `B017` ×1, `PERF402` ×1, `PLC0206` ×1, `RUF034` ×1,
      `SIM102` ×1, `SIM114` ×1, `SIM115` ×1, `SIM118` ×1, `SIM222` ×1,
      `W605` invalid-escape-sequence ×1, `PLR1730` ×2.
      For `BLE001` and `S110`, narrow each bare `except Exception:` /
      `except: pass` to the specific exception actually expected, and add a
      one-line comment naming why it is swallowed. **These 19 are the only
      violations in the census with real diagnostic value — read each site
      rather than mechanically silencing it.** For `DTZ001`/`DTZ011`, prefer
      `datetime.now(timezone.utc)` / `datetime.now(timezone.utc).date()`; these
      appear in report-timestamp code where the change is behaviour-neutral for
      a date-stamped filename.
- [ ] TASK-01-08: Remove the `# noqa: E402` comments that `RUF100` flags as
      unused (101 of them). They became redundant when `E402` was added to the
      global ignore list. Verify none of the removed comments suppressed a
      second, still-active rule on the same line.
- [ ] TASK-01-09: Update `.github/workflows/ci.yml`'s install step to
      `pip install -e ".[webapp,dev]"`, removing the inline
      `mypy pytest pytest-cov ruff` list. Keep the matrix, the marker filter
      string, and `PYTHONPATH: ""` exactly as they are.
- [ ] TASK-01-10: Re-run the full portable suite. Confirm
      `634 passed, 18 deselected, 3 xfailed` — **unchanged**. Any reduction
      means TASK-01-06's auto-fix removed something load-bearing; revert and
      re-apply selectively (CON-005).
- [ ] TASK-01-11: Run `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp`
      → `Success: no issues found in 21 source files`.
- [ ] TASK-01-12: Commit and push. Then run `gh run list --limit 2` and confirm
      **both** matrix legs report `success`. If the 3.10 leg now fails at `mypy`
      or `pytest` (previously unreached — ASM-002), fix it inside this phase.
- [ ] TASK-01-13: Append the post-change result and the CI run id to
      `reports/2026-08-06-ci-restoration.md`.

**File Changes**
- `pyproject.toml` (modify): add to `[project.optional-dependencies]`:
  ```toml
  dev = [
    "ruff==0.16.1",
    "mypy==2.3.0",
    "pytest==8.4.2",
    "pytest-cov==7.1.0",
  ]
  ```
  and add `"ISC004"` to the existing `[tool.ruff.lint] ignore` list with the
  comment
  `# ISC004: multi-line string literals inside list/tuple literals in report builders are deliberate.`
  Leave `[project] dependencies`, `[tool.pytest.ini_options]`, the `markers`
  list, `[tool.mypy]`, and `[tool.coverage.run]` untouched.
- `.github/workflows/ci.yml` (modify): change the install line to
  `pip install -e ".[webapp,dev]"`. Change nothing else — not the matrix, not
  the marker filter, not the `PYTHONPATH: ""` env block.
- `src/**/*.py`, `scripts/**/*.py`, `tests/**/*.py` (modify): mechanical lint
  fixes only. **No behavioural change is permitted in this phase.** The
  annotation modernizations (`List[str]` → `list[str]`,
  `Optional[X]` → `X | None`) are safe because every affected module already has
  `from __future__ import annotations`.
- `reports/2026-08-06-ci-restoration.md` (create): before/after suite counts,
  before/after violation counts, the residual-category triage decisions, and the
  green CI run id. Tracked Markdown deliverable per the `reports/*.md`
  convention.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
- `ruff check src scripts tests` → `All checks passed!`, exit code `0`.
- `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q`
  → `634 passed, 18 deselected, 3 xfailed` — byte-identical to the baseline.
- `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp`
  → `Success: no issues found in 21 source files`.
- `python -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); assert 'ruff==0.16.1' in d['project']['optional-dependencies']['dev']"`
  → exit code `0`, no output.
- `gh run list --limit 2 --json conclusion --jq '[.[].conclusion] | unique'`
  → `["success"]`.

**Dependencies**
- `ruff==0.16.1` must be installable. Requires network access on first install.
- The `gh` CLI must be authenticated for the CI-status verification
  (`gh auth status` → logged in).

**Exit Criteria**
- [ ] `ruff check src scripts tests` exits `0`.
- [ ] Portable suite count is exactly `634 passed, 18 deselected, 3 xfailed`.
- [ ] `mypy` reports no issues.
- [ ] `gh run list --limit 2` shows both the 3.10 and 3.12 legs as `success` on
      the pushed commit. **This, not a local run, is what closes the phase.**
- [ ] `reports/2026-08-06-ci-restoration.md` records the green run id.

**Phase Risks**
- **RISK-01-01:** `ruff --fix` removes an import that is unused for typing but
  load-bearing as a side effect (module registration). Mitigation: read the full
  `--fix` diff before committing, with specific attention to
  `analysis/` and `integration/`; run the full suite immediately after and
  compare counts against the recorded baseline.
- **RISK-01-02:** the `UP006`/`UP045` annotation rewrites touch 321 sites and
  could alter a runtime-evaluated annotation in a module lacking
  `from __future__ import annotations`. Mitigation: before running `--fix`,
  confirm coverage with
  `grep -rLn "from __future__ import annotations" --include="*.py" src/python scripts/python`
  and hand-review any file that appears in that list before letting the
  auto-fixer touch it.
- **RISK-01-03:** narrowing `BLE001` blind excepts changes which errors
  propagate, turning a previously-swallowed failure into a visible one.
  Mitigation: this is the desired outcome, but run the full suite after each
  batch of `BLE001` fixes rather than all 14 at once, so an escaped exception is
  attributable.
- **RISK-01-04:** the Python 3.10 leg fails at a step never previously reached.
  Mitigation: ASM-002 — fix within this phase; do not merge a partially green
  matrix.

---

### PHASE-02 - Truth Sweep

**Goal**
Ensure no document, docstring, or test in the repository asserts a guarantee
that is not actually enforced, and give the regulatory watch table a
falsifiable currency claim.

**Tasks**
- [ ] TASK-02-01: Correct `src/python/reopt_pysam_vn/webapp/README.md` lines
      63–66. The current text claims the parity test "proves the web API path
      reproduces `examples/samsung-ttc_combined-decision.example.json`
      bit-for-bit." Replace with a description matching what
      `tests/python/webapp/test_golden_parity.py` actually asserts: that
      `POST /api/runs` reproduces a direct `run_offsite_dppa` call bit-for-bit
      (proving the webapp forks no analytics, CON-002), and that it deliberately
      does **not** re-assert parity against the golden, which carries a known
      pre-existing divergence documented in
      `reports/2026-07-26-samsung-parity-diagnosis.md`.
- [ ] TASK-02-02: Correct the module docstring at
      `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py:6`, which still
      describes the combined decision as parity-gated bit-for-bit. Match the
      wording already used in `docs/onsite_vs_offsite.md`: a local-only
      diagnostic, CI-excluded via the `golden_machine` marker, currently
      `xfail`ed.
- [ ] TASK-02-03: Re-polarize
      `tests/python/webapp/test_golden_parity.py::test_samsung_ttc_golden_drift_is_the_known_pre_existing_gap`
      per S5. Rename it to
      `test_samsung_ttc_golden_drift_stays_within_the_known_manifest`. Seed
      `KNOWN_DRIFTED_PATHS` from the paths named in
      `reports/2026-07-26-samsung-parity-diagnosis.md` — at minimum
      `strike_sweep.negotiation_summary.buyer_saves_candidates[*].developer_irr_fraction`
      and `strike_sweep.negotiation_summary.buyer_saves_candidates[*].developer_npv_usd`.
      Run the test first to enumerate the *actual* diverging paths and seed the
      manifest from that measured list, not from a guess — the repository's own
      `lessons.md` records that guessing a tolerance instead of measuring it is a
      repeat mistake here. Leave
      `test_samsung_ttc_web_api_matches_direct_library_call_bit_exact` completely
      unchanged.
- [ ] TASK-02-04: Rewrite `AGENTS.md` §4 "Current Status". Delete the
      "Test Suite Status (last run: Mar 2026)" table entirely and replace it
      with a one-line pointer to `activeContext.md` as the authority for current
      test state, plus the standing note that CI runs `pytest tests/python` with
      the four-marker exclusion filter. Keep §4's Julia version line, API-key
      line, and API-domain line.
- [ ] TASK-02-05: Rewrite `AGENTS.md` §6 "Real Project Data Notes". Its
      "Next steps" list item 3 says "Custom JuMP constraint for 20% generation
      export cap (Decree 57)" — that cap was raised to 50 % by Decree 243/2026
      effective 2026-06-26 and the data layer was updated on 2026-07-18. Either
      delete §6 as historical or rewrite it to state the current cap and point
      at `data/vietnam/vn_export_rules_2026_decree243.json`. **BINDING
      DEFAULT: rewrite rather than delete**, keeping the three "Identified gaps"
      (they remain accurate) and replacing the stale next-steps list.
- [ ] TASK-02-06: Add `Last verified` and `Next review` columns to the table in
      `docs/regulatory-watch.md` (header currently at line 9). Populate
      `Last verified` = `2026-08-06` for the `tariff` row, and
      `Next review` = `2026-11-06` (a 3-month horizon, matching the minimum
      adjustment interval Decision 07/2025/QD-TTg permits EVN). For every other
      row, set `Last verified` = the date of the commit that last touched its
      active file and `Next review` = that date plus 6 months. Record in the
      `tariff` row's notes that the EVN average retail price of
      2,204.0655 VND/kWh excluding VAT was confirmed still standing on
      2026-08-06.
- [ ] TASK-02-07: Add `test_regulatory_watch_rows_are_not_overdue` to
      `tests/python/test_repo_invariants.py`. It parses the Markdown table in
      `docs/regulatory-watch.md`, reads each row's `Next review` date, and fails
      naming every row whose date is in the past.
- [ ] TASK-02-08: Triage the three stale branches. For each of
      `real-project-data`, `claude/clever-chaplygin-dad6dc`, and
      `claude/kind-mcclintock-10b2e5`, run
      `git log --oneline main..<branch> | wc -l`. Delete only branches whose
      count is `0` (fully merged), using `git branch -d <branch>` (the safe
      form, which refuses unmerged branches) and `git push origin --delete
      <branch>` for the remote counterpart. Record each branch's unique-commit
      count in the phase report (ASM-010).
- [ ] TASK-02-09: Delete `tests/cross_validate.py` — a 14-line `runpy` shim
      delegating to `tests/cross_language/cross_validate.py`. First confirm no
      caller references it:
      `grep -rn "cross_validate" --include="*.py" --include="*.ps1" --include="*.md" . | grep -v cross_language`
      must return no live invocation. Then extend
      `tests/python/test_repo_invariants.py::test_no_flat_python_scripts` — or
      add a sibling `test_no_test_shims` — so a re-added shim under `tests/`
      fails the invariant.
- [ ] TASK-02-10: Add `*.log` at the repository root to `.gitignore`
      (the rule is `/*.log` — the leading slash anchors it to the repository
      root so nested log files elsewhere are unaffected). An untracked
      `phase6_test.log` currently sits at the root. Run `git status` afterward
      and confirm no previously tracked file became ignored (this repository has
      been bitten by loose `.gitignore` edits before — see `lessons.md`
      2026-06-12).
- [ ] TASK-02-11: Update `activeContext.md`'s "CI status" line, which currently
      reads "Green on `main`", to reference the PHASE-01 run id and the date it
      was verified.
- [ ] TASK-02-12: Add a "Verify CI, not just local tests" bullet to `AGENTS.md`
      §2 "Environment & Commands", specifying `gh run list --limit 3` as a
      required step before reporting any work complete (DEC-005).

**File Changes**
- `src/python/reopt_pysam_vn/webapp/README.md` (modify): rewrite the final
  paragraph of the `## Tests` section (lines ~62–66). Leave the Launch, NREL API
  key, Storage layout, and Solve cache sections untouched.
- `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` (modify): module
  docstring only, around line 6. **Change no code and no numeric literal in this
  file** — it is the parity-gated path (CON-001).
- `tests/python/webapp/test_golden_parity.py` (modify): replace the second test
  per S5; add a `KNOWN_DRIFTED_PATHS` module constant and a leaf-path diff
  helper. Leave the first test and the module's `_read` helper unchanged.
- `AGENTS.md` (modify): §4 (delete the March test table, add the pointer), §6
  (rewrite next steps), §2 (add the CI-verification bullet). Leave §1, §3, and
  §5 untouched.
- `docs/regulatory-watch.md` (modify): add two columns to the table and populate
  all seven rows. Keep every existing column and every existing cell value.
- `tests/python/test_repo_invariants.py` (modify): add
  `test_regulatory_watch_rows_are_not_overdue` and the test-shim invariant.
  Leave `test_no_flat_python_scripts`, `test_no_tracked_artifacts`, and
  `test_no_root_level_binaries` behaviourally unchanged.
- `tests/cross_validate.py` (delete): the shim.
- `.gitignore` (modify): add a root-anchored `*.log` rule.
- `activeContext.md` (modify): the CI status line only.
- `reports/2026-08-06-truth-sweep.md` (create): what each corrected claim said
  before and after, the branch triage counts, and the measured drift-path list
  seeded into the manifest.

**Function Signatures**
- `_leaf_paths(obj: Any, prefix: str = "") -> Iterator[tuple[str, Any]]` — yields
  `(dotted_path, scalar_value)` for every leaf in a nested dict/list structure;
  list indices render as `[i]`.
- `_diverging_paths(actual: dict, golden: dict) -> set[str]` — returns the set of
  dotted leaf paths whose values differ between the two structures, including
  paths present in one and absent from the other.
- `test_regulatory_watch_rows_are_not_overdue() -> None` — parses
  `docs/regulatory-watch.md`'s table and asserts no row's `Next review` date is
  earlier than today; the failure message names every overdue row and its date.

**Test Specs**
- `_leaf_paths({"a": {"b": 1}, "c": [2, 3]})` → yields
  `("a.b", 1)`, `("c[0]", 2)`, `("c[1]", 3)`.
- `_diverging_paths({"a": 1, "b": 2}, {"a": 1, "b": 3})` → `{"b"}`.
- `_diverging_paths({"a": 1}, {"a": 1, "b": 2})` → `{"b"}` (a path present in
  only one side counts as diverging).
- `_diverging_paths({"a": 1}, {"a": 1})` → `set()`.
- `_diverging_paths({"ok": True}, {"ok": 1})` → `{"ok"}` — **`bool` must be
  compared as `bool`, not numerically**; `True == 1` is `True` in Python and a
  naive comparator would call this identical.
- `test_samsung_ttc_golden_drift_stays_within_the_known_manifest` with the
  current live divergence → **passes** (actual ⊆ manifest).
- The same test with a manifest artificially emptied → **fails**, and the
  failure message lists the unexpected paths.
- The same test simulating a *fixed* divergence (actual = empty set) →
  **passes** — this is the polarity inversion the phase exists to deliver.
- `test_regulatory_watch_rows_are_not_overdue` with all `Next review` dates in
  the future → passes.
- The same test with the `tariff` row's `Next review` set to `2020-01-01` →
  fails with a message containing `tariff` and `2020-01-01`.
- `grep -c "bit-for-bit" src/python/reopt_pysam_vn/webapp/README.md` → the
  remaining occurrences describe only the web-API-vs-direct-call comparison,
  never the golden.

**Dependencies**
- PHASE-01 complete (CI green), so any test change is verifiable end to end.
- `gh` CLI authenticated, and push access to `origin` for the branch deletions.

**Exit Criteria**
- [ ] `grep -rn "parity-gated\|bit-for-bit" README.md docs/ src/python/reopt_pysam_vn/`
      returns only statements that are factually true — each hit read and
      confirmed.
- [ ] `PYTHONPATH= python -m pytest tests/python/webapp/test_golden_parity.py -v`
      → `2 passed`.
- [ ] `PYTHONPATH= python -m pytest tests/python/test_repo_invariants.py -v`
      → all pass, including the two new invariants.
- [ ] Full portable suite green with a passing count of at least 634 (it rises
      by the number of new invariant tests).
- [ ] `git branch -a` shows only branches that either are `main` or carry
      unique commits recorded in the phase report.
- [ ] `AGENTS.md` contains no reference to a 20 % export cap as a pending task
      and no March 2026 test-status table.

**Phase Risks**
- **RISK-02-01:** seeding `KNOWN_DRIFTED_PATHS` from the diagnosis report rather
  than from a live measurement produces a manifest that is too narrow, making
  the test red on arrival. Mitigation: TASK-02-03 explicitly requires running
  the comparison first and seeding from the measured set.
- **RISK-02-02:** the drift test depends on PySAM and a cached PVWatts resource,
  so the measured path set may differ between machines. Mitigation: keep the
  existing `pytest.skip` guards at the top of the test (fixtures present,
  `pvwatts` in `quality.solar_profile_source`) — they already handle this and
  must not be removed.
- **RISK-02-03:** `git push origin --delete` is irreversible for a branch that
  turns out to hold unique work. Mitigation: ASM-010's binding default — never
  delete a branch with a non-empty `main..<branch>` log; use `git branch -d`
  (which refuses unmerged branches) rather than `-D`.
- **RISK-02-04:** a root-anchored `*.log` rule un-tracks a previously tracked
  log file. Mitigation: run `git status --porcelain` before and after and diff
  the output; no tracked file may change state.

---

### PHASE-03 - Complete the FX Derivation

**Goal**
Make `data/vietnam/vn_deal_defaults_2026.json` the authoritative source for the
canonical exchange rate, so changing it changes every general-purpose module —
without moving a single published number today.

**Tasks**
- [ ] TASK-03-01: Write the failing test first
      (`tests/python/common/test_assumptions_authority.py`). It must fail before
      any source change, proving the data layer is currently non-authoritative.
      See Test Specs.
- [ ] TASK-03-02: Remove the `caller_value=26_400.0` argument from these **8**
      call sites, leaving the surrounding assignment and the
      `load_vietnam_data()` argument intact:
      - `src/python/reopt_pysam_vn/integration/factory_a.py:45`
      - `src/python/reopt_pysam_vn/reopt/decree243_delta.py:28`
      - `scripts/python/integration/build_ninhsim_extracted_inputs.py:28`
      - `scripts/python/reopt/bess_dispatch_analysis.py:33`
      - `scripts/python/reopt/decree146_demand_charge.py:43`
      - `scripts/python/reopt/decree243_export_cap_delta.py:33`
      - `scripts/python/reopt/dppa_settlement.py:28`
      - `scripts/python/reopt/fmp_sensitivity.py:41`
      Each becomes `_resolve_exchange_rate(load_vietnam_data())`.
- [ ] TASK-03-03: **Deliberately keep** the pin at
      `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py:94`
      (`caller_value=26_400.0`). Update its adjacent comment to state that the
      pin is retained on purpose to insulate the parity-gated path from
      data-layer edits, referencing CON-001. This is the ninth 26,400 site and
      it is the one exception (ASM-009).
- [ ] TASK-03-04: **Deliberately keep** all 5 deal-specific 25,450 pins,
      confirming each carries an explanatory comment naming the Saigon18
      contract basis:
      - `src/python/reopt_pysam_vn/integration/dppa_case_3.py:70`
      - `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py:41`
      - `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f_22kv.py:32`
      - `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py:67`
      - `scripts/python/integration/build_saigon18_dppa_case_3_phase_c.py:189`
      Add the comment where one is missing. Change no value.
- [ ] TASK-03-05: Run the full portable suite and confirm the count is
      **unchanged**. Because `vn_deal_defaults_2026.json` holds exactly
      `26400`, every unpinned site resolves to the identical float and no
      numeric output may move. **If any test's numbers change, stop** — it means
      the data layer and the literal disagree somewhere, which is itself the
      finding, and it must be investigated before proceeding.
- [ ] TASK-03-06: Write `reports/2026-08-06-fx-derivation-delta.md` recording:
      the 8 sites unpinned, the 6 deliberately retained (1 parity, 5 Saigon18),
      the confirmation that no test count or numeric assertion changed, and the
      new invariant that the data layer is now authoritative.
- [ ] TASK-03-07: Add a "Currency" note to `AGENTS.md` §5 "Key Learnings &
      Notes" stating that the canonical VND/USD rate is resolved from
      `data/vietnam/vn_deal_defaults_2026.json` via
      `reopt_pysam_vn.common.assumptions.exchange_rate()`, that new code must
      never write a bare FX literal, and that the two documented exception
      classes are the parity-gated Samsung path and the Saigon18 25,450 contract
      basis.

**File Changes**
- The 8 files listed in TASK-03-02 (modify): delete the `caller_value=26_400.0`
  keyword argument only. Change nothing else on the line, and no other line.
- `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py` (modify): comment
  text at/near line 92–94 only. **No code change.**
- `scripts/python/integration/analyze_saigon18_dppa_case_3_phase_f.py`,
  `..._phase_f_22kv.py`, `build_saigon18_dppa_case_3_phase_c.py`,
  `src/python/reopt_pysam_vn/integration/dppa_case_3.py` (modify): add or
  normalise the explanatory comment above each retained 25,450 pin. **No value
  change.**
- `tests/python/common/test_assumptions_authority.py` (create): the
  data-layer-authority test.
- `AGENTS.md` (modify): one bullet appended to §5.
- `reports/2026-08-06-fx-derivation-delta.md` (create): the delta memo.

**Function Signatures**
None — no code interfaces change in this phase. `exchange_rate()` in
`src/python/reopt_pysam_vn/common/assumptions.py` keeps its current signature
`exchange_rate(vn: VNData, *, caller_value: float | None = None, extracted: dict | None = None) -> float`
unchanged; this phase changes only how it is *called*.

**Test Specs**
- Authority test, the core case: build a `VNData` whose
  `deal_defaults["exchange_rate"]["vnd_per_usd"]` is `30000.0` (by loading the
  real data and overriding the field on a copy, not by editing the tracked JSON),
  call `exchange_rate(vn_modified)` → returns `30000.0`, **not** `26400.0`.
- Precedence still honoured: `exchange_rate(vn_modified, caller_value=25450.0)`
  → returns `25450.0` (an explicit caller argument still wins, per the
  documented chain).
- Per-deal override still honoured:
  `exchange_rate(vn_modified, extracted={"benchmark": {"exchange_rate_vnd_per_usd": 25000.0}})`
  → returns `25000.0`.
- Unmodified default: `exchange_rate(load_vietnam_data())` → returns `26400.0`.
- Guard: `exchange_rate(vn_with_zero_rate)` where the deal-defaults rate is
  `0.0` → raises `ValueError` whose message contains `must be positive`.
- Source-level invariant (this is the test that fails before TASK-03-02 and
  passes after): scan the 8 files listed in TASK-03-02 for the literal
  `caller_value=26_400.0` → **zero matches**. Scan
  `dppa_samsung_ttc.py` for the same literal → **exactly one match** (the
  deliberate retention).
- Regression: `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q`
  → passing count unchanged from PHASE-02's exit state, and **no numeric
  assertion anywhere changes**.

**Dependencies**
- PHASE-01 complete, so the suite result is trustworthy and CI verifies it.
- `data/vietnam/vn_deal_defaults_2026.json` must already carry the
  `{_meta, data}` envelope with `data.exchange_rate.vnd_per_usd = 26400`. This
  shipped on 2026-07-26 — confirm with
  `python -c "import json;d=json.load(open('data/vietnam/vn_deal_defaults_2026.json',encoding='utf-8-sig'));print(d['data']['exchange_rate']['vnd_per_usd'])"`
  → `26400`.

**Exit Criteria**
- [ ] `grep -rn "caller_value=26_400.0" src scripts | wc -l` → `1` (Samsung only).
- [ ] `grep -rn "caller_value=25450.0\|caller_value=25_450.0" src scripts | wc -l`
      → `5`.
- [ ] `PYTHONPATH= python -m pytest tests/python/common/ -v` → all pass.
- [ ] Full portable suite passing count unchanged from PHASE-02's exit state.
- [ ] `reports/2026-08-06-fx-derivation-delta.md` states explicitly that zero
      published numbers moved, with the before/after suite counts as evidence.

**Phase Risks**
- **RISK-03-01:** an unpinned module silently picks up a *different* rate
  because the data layer and its former literal disagree. Mitigation:
  TASK-03-05's stop condition. The pre-check in Dependencies confirms the data
  layer holds exactly `26400` before any unpinning happens.
- **RISK-03-02:** a module-level constant resolved at import time makes the new
  test order-dependent if it mutates global state. Mitigation: the authority
  test must build a **copy** of `VNData` and never mutate the shared instance or
  the tracked JSON file on disk.
- **RISK-03-03:** someone later reads the retained Samsung pin as an oversight
  and removes it, moving the parity golden. Mitigation: TASK-03-03's comment
  must name CON-001 explicitly, and the delta memo must record the retention as
  deliberate.

---

### PHASE-04 - Widen the Orchestrator Contract and Register a Second Deal

**Goal**
Make `reopt_pysam_vn.analysis.run_offsite_dppa` execute a deal other than
Samsung-TTC, by widening the orchestrator contract to accommodate deals that
consume a REopt results dictionary and registering `dppa_case_1` behind it.

**Tasks**
- [ ] TASK-04-01: Write the failing tests first
      (`tests/python/analysis/test_offsite_dppa_case_1.py`). Confirm they fail
      with `ValueError: no offsite orchestrator registered for case
      'DPPA_CASE_1_NINHSIM'` before implementing anything.
- [ ] TASK-04-02: Widen `CombinedDecisionFn` and `run_offsite_dppa` in
      `src/python/reopt_pysam_vn/analysis/offsite_dppa.py` per S1 and S2. Add
      `results` and `scenario` keyword arguments to `run_offsite_dppa`, resolve
      each from `deal_config.raw` when not passed, and **pass them to the
      orchestrator only when they are not `None`** so the existing
      two-parameter Samsung orchestrator keeps its exact current call shape.
- [ ] TASK-04-03: Create the package
      `src/python/reopt_pysam_vn/analysis/orchestrators/` with an
      `__init__.py`, and add `dppa_case_1.py` implementing the S3 composition
      and the S4 adapter.
- [ ] TASK-04-04: Register the orchestrator. Call
      `register_orchestrator("DPPA_CASE_1_NINHSIM", build_case_1_offsite_artifact)`
      from `src/python/reopt_pysam_vn/analysis/__init__.py`, importing the
      orchestrator module lazily inside a small registration function so
      `import reopt_pysam_vn.analysis` does not pull the heavy
      `integration.dppa_case_1` module (mirroring the lazy-import comment already
      present on `_samsung_ttc_orchestrator`).
- [ ] TASK-04-05: Create the deal config
      `scenarios/case_studies/ninhsim/dppa_case_1_deal_config.json` with
      `case = "DPPA_CASE_1_NINHSIM"`, `mode = "offsite_dppa"`, a `title`, and
      `site.region = "central"`. It must validate against
      `data/schemas/deal_config.schema.json` — confirm by loading it through
      `DealConfig.from_dict` with validation on.
- [ ] TASK-04-06: Add the hermetic fixture. Copy the `_synthetic_results()`
      helper pattern from `tests/python/integration/test_dppa_case_1.py:49` into
      the new test module (or import it if it can be made importable without
      restructuring). The test must **not** read anything under `artifacts/` and
      must **not** carry the `requires_artifacts` marker (ASM-008).
- [ ] TASK-04-07: Verify the Samsung path is byte-for-byte unaffected. Run
      `tests/python/webapp/test_golden_parity.py` and
      `tests/python/analysis/test_offsite_dppa.py` and confirm no change
      (CON-002).
- [ ] TASK-04-08: Add a webapp acceptance test to
      `tests/python/webapp/test_api_runs.py` proving `POST /api/runs` with the
      case-1 deal config plus its `extracted`, `results`, and `scenario`
      payloads reaches state `done` rather than returning 422
      `OrchestratorNotRegisteredError`.
- [ ] TASK-04-09: Update the docstring at the top of
      `src/python/reopt_pysam_vn/analysis/offsite_dppa.py`, which currently says
      the registry "today ... holds the proven Samsung-TTC builder". State that
      it holds two orchestrators, document the widened contract, and explain the
      `results`/`scenario` resolution order from S2.
- [ ] TASK-04-10: Update `src/python/reopt_pysam_vn/webapp/service.py`'s module
      docstring, which states the registry holds "today only
      `DPPA_SAMSUNG_TTC`". Correct it and note that offsite deals consuming a
      REopt results dict must supply `results` and `scenario` alongside
      `extracted`.
- [ ] TASK-04-11: Update `README.md`'s Analysis Modes section and
      `docs/onsite_vs_offsite.md` to state that `run_offsite_dppa` serves two
      registered cases and to document `register_orchestrator` as the extension
      point for a third.
- [ ] TASK-04-12: Write `reports/2026-08-06-second-orchestrator.md` recording
      the widened contract, the block mapping actually used, which
      `_OFFSITE_BLOCKS` came back empty for case 1, and what that reveals about
      whether the block vocabulary generalizes — this observation is the main
      analytical output of the phase and the input to any future third
      registration.

**File Changes**
- `src/python/reopt_pysam_vn/analysis/offsite_dppa.py` (modify): widen
  `CombinedDecisionFn`'s documented signature, add `results` and `scenario`
  parameters to `run_offsite_dppa` with `deal_config.raw` fallbacks, build the
  orchestrator kwargs conditionally, and rewrite the module docstring. Leave
  `register_orchestrator`'s signature, the `extracted is None` error message,
  and the `OffsiteDppaResult.from_dict(raw)` return path unchanged.
- `src/python/reopt_pysam_vn/analysis/orchestrators/__init__.py` (create): empty
  package marker.
- `src/python/reopt_pysam_vn/analysis/orchestrators/dppa_case_1.py` (create):
  the S3 composition and S4 adapter.
- `src/python/reopt_pysam_vn/analysis/__init__.py` (modify): add the lazy
  registration call. Keep every existing export in `__all__`.
- `src/python/reopt_pysam_vn/webapp/service.py` (modify): module docstring only.
  **No behavioural change** — CON-002.
- `scenarios/case_studies/ninhsim/dppa_case_1_deal_config.json` (create).
- `tests/python/analysis/test_offsite_dppa_case_1.py` (create).
- `tests/python/webapp/test_api_runs.py` (modify): add the case-1 acceptance
  test. Leave existing tests untouched.
- `README.md`, `docs/onsite_vs_offsite.md` (modify): the registry description.
- `reports/2026-08-06-second-orchestrator.md` (create).

**Function Signatures**
- `build_case_1_offsite_artifact(extracted: dict, *, run_developer: bool = True, results: dict | None = None, scenario: dict | None = None, developer_runner: Callable[[dict], dict] | None = None) -> dict`
  — composes the four `dppa_case_1` builders per S3 and returns a dict already
  shaped to `_OFFSITE_BLOCKS` per S4. Raises `ValueError` naming the missing
  argument when `results` or `scenario` is `None`.
- `_adapt_case_1_artifact(artifact: dict, *, developer_basis: str) -> dict`
  — maps a raw `build_dppa_case_1_combined_decision` output onto the
  `OffsiteDppaResult` block vocabulary per S4, returning a dict with keys
  `case`, `model`, the seven `_OFFSITE_BLOCKS`, and `case_1_artifact`.
- `run_offsite_dppa(deal_config: DealConfig, *, extracted: dict | None = None, results: dict | None = None, scenario: dict | None = None, combined_decision_fn: CombinedDecisionFn | None = None, run_developer: bool = True) -> OffsiteDppaResult`
  — unchanged behaviour for the Samsung case; resolves `results`/`scenario` per
  S2 and forwards them only when non-`None`.

**Test Specs**
- Pre-implementation (must fail):
  `run_offsite_dppa(DealConfig.from_dict({"case": "DPPA_CASE_1_NINHSIM", "mode": "offsite_dppa"}), extracted=<ninhsim extracted>)`
  → raises `ValueError` whose message contains
  `no offsite orchestrator registered` and `DPPA_CASE_1_NINHSIM`.
- Post-implementation, happy path:
  `run_offsite_dppa(case_1_config, extracted=<ninhsim extracted>, results=_synthetic_results(), scenario=<case-1 scenario>)`
  → returns an `OffsiteDppaResult` with `.case == "DPPA_CASE_1_NINHSIM"`.
- Block presence: the result's `.to_dict()` contains **all seven** keys
  `deal`, `base_settlement`, `strike_sweep`, `adder_sensitivity`,
  `regime_stress`, `decision`, `quality`.
- Empty-by-design blocks: `result.strike_sweep == {}`,
  `result.adder_sensitivity == {}`, `result.regime_stress == {}`.
- Populated blocks: `result.decision["recommended_position"]` is one of
  `"advance_for_review"` or `"needs_reprice_or_resize"`;
  `result.deal` is non-empty; `result.base_settlement` contains keys
  `energy_summary`, `optimal_mix`, and `financial`.
- Nothing lost: `result.raw["case_1_artifact"]["model"] == "Ninhsim DPPA Case 1 Combined Decision"`,
  and `result.raw["case_1_artifact"]` contains all eight original case-1 keys.
- Developer basis: with `run_developer=False` →
  `result.quality["developer_basis"] == "placeholder"`.
- Missing input: `run_offsite_dppa(case_1_config, extracted=<extracted>)` with
  no `results` → raises `ValueError` whose message names `results`.
- `raw` fallback (S2): a `DealConfig` built from a dict carrying
  `{"extracted": …, "results": …, "scenario": …}` as extra top-level keys (which
  land in `.raw`) runs successfully with **no** keyword arguments passed to
  `run_offsite_dppa`.
- Samsung regression (CON-002): `run_offsite_dppa(samsung_config, extracted=<samsung extracted>)`
  → still succeeds with `.case == "DPPA_SAMSUNG_TTC"`, and
  `tests/python/webapp/test_golden_parity.py::test_samsung_ttc_web_api_matches_direct_library_call_bit_exact`
  still passes.
- Two-parameter orchestrator compatibility: register a stub orchestrator
  accepting only `(extracted, *, run_developer)`, call `run_offsite_dppa` for
  its case with `results=None, scenario=None` → succeeds without a
  `TypeError` about unexpected keyword arguments.
- Webapp acceptance: `POST /api/runs` with
  `{"deal_config": <case-1 config>, "extracted": …, "results": …, "scenario": …}`
  → HTTP `202`, then `GET /api/runs/{run_id}` shows
  `status.state == "done"` — **not** a 422.
- Registry size: `len(reopt_pysam_vn.analysis.offsite_dppa._ORCHESTRATORS) == 2`
  after importing `reopt_pysam_vn.analysis`.

**Dependencies**
- PHASE-01 (green CI) and PHASE-03 (FX derivation settled, so any numeric
  movement in this phase is attributable to the orchestrator work alone).
- `data/interim/ninhsim/ninhsim_extracted_inputs.json` — tracked, present.
- `scenarios/case_studies/ninhsim/2026-04-09_ninhsim_dppa-case-1.json` — tracked,
  present; use it as the `scenario` input.
- No PySAM requirement: the placeholder developer path keeps the test hermetic.

**Exit Criteria**
- [ ] `PYTHONPATH= python -m pytest tests/python/analysis/test_offsite_dppa_case_1.py -v`
      → all pass.
- [ ] `PYTHONPATH= python -c "import sys; sys.path.insert(0,'src/python'); import reopt_pysam_vn.analysis as a; print(sorted(a.offsite_dppa._ORCHESTRATORS))"`
      → `['DPPA_CASE_1_NINHSIM', 'DPPA_SAMSUNG_TTC']`.
- [ ] `PYTHONPATH= python -m pytest tests/python/webapp/ -q` → all pass,
      including the new acceptance test.
- [ ] `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp`
      → `Success: no issues found` (the new `orchestrators/` package is inside
      the `analysis` type-checked surface and must satisfy
      `disallow_untyped_defs`).
- [ ] Full portable suite green; passing count has risen by the number of new
      tests and no previously passing test now fails.
- [ ] `gh run list --limit 2 --json conclusion --jq '[.[].conclusion] | unique'`
      → `["success"]`.
- [ ] No document states that `run_offsite_dppa` serves only one case.

**Phase Risks**
- **RISK-04-01:** widening the contract breaks the Samsung orchestrator's call
  shape and moves the parity golden. Mitigation: S1's backward-compatibility
  rule — pass `results`/`scenario` only when non-`None` — plus TASK-04-07's
  explicit regression check before anything else in the phase is considered
  done. `_samsung_ttc_orchestrator`'s own signature must not be edited.
- **RISK-04-02:** the S4 mapping is judged wrong later and the adapter has to
  change, moving any golden built on it. Mitigation: no golden is created for
  case 1 in this plan. The complete original artifact is preserved under
  `raw["case_1_artifact"]`, so a future remapping is lossless.
- **RISK-04-03:** `mypy`'s `disallow_untyped_defs` applies to
  `reopt_pysam_vn.analysis.*`, so the new `orchestrators/` package needs full
  annotations while the `integration.dppa_case_1` functions it calls are
  untyped. Mitigation: annotate the new module's own signatures completely and
  treat values crossing the boundary as `dict` / `Dict[str, Any]`; do **not**
  add the new package to a mypy override or loosen the existing gate.
- **RISK-04-04:** three of the seven blocks come back empty, which a reviewer
  may read as a broken adapter. Mitigation: TASK-04-12 documents the emptiness
  as a deliberate, meaningful finding about the block vocabulary, and the tests
  assert the empty dicts explicitly so the intent is executable, not just
  written down.

## Gotchas

- **`bool` is a subclass of `int`.** In the PHASE-02 diff comparator, `True == 1`
  evaluates `True`. Guard `isinstance(x, bool)` **before** `isinstance(x, int)`
  or the decision flags in the Samsung artifact will compare as identical when
  they are not. This exact mistake is recorded in `lessons.md` (2026-06-14).
- **`export_cap_pct` is a percentage in `[0, 100]`; `max_export_fraction` is a
  fraction in `[0, 1]`.** Conflating them is a 100× error. This plan does not
  touch either, but any incidental edit near `settlement.py` must respect it.
- **Clear `PYTHONPATH` before running pytest.** A global `PYTHONPATH` pointing at
  an unrelated `hermes-agent` virtualenv shadows this repository's `fastapi` and
  `pydantic` installs and produces
  `ModuleNotFoundError: pydantic_core._pydantic_core`, which looks like a broken
  test and is not.
- **`ruff --fix` is not a no-op on semantics.** Removing an "unused" import can
  break a module-registration side effect. This repository has a registry
  pattern in `analysis/` — read that part of the diff by hand.
- **`RUF100` will keep reappearing** if `E402` is later removed from the global
  ignore list. If a future change re-enables `E402`, the `# noqa: E402` comments
  deleted in TASK-01-08 must be restored, not re-suppressed.
- **The Samsung PVWatts resource is machine-dependent.** Tests touching it carry
  `golden_machine` or explicit `pytest.skip` guards. Never remove those guards to
  make a test "run everywhere" — it will fail in CI for environmental reasons and
  teach everyone to ignore red.
- **Do not run the whole suite with `-p no:cacheprovider` as the official check.**
  Use the exact command in Environment & Conventions; a different invocation
  produces different deselection counts and makes CON-005 unenforceable.
- **`git branch -D` versus `-d`.** Use `-d`. It refuses to delete a branch with
  unmerged commits, which is precisely the safety property ASM-010 relies on.
- **Every `data/vietnam/*.json` read uses `encoding="utf-8-sig"`.** A reader
  written with plain `utf-8` will fail on a byte-order mark that other readers
  silently tolerate, producing an error that looks like malformed JSON.
- **`_OFFSITE_BLOCKS` order is emit order.** `OffsiteDppaResult.to_dict()`
  iterates it to build the output dict. Reordering it reorders every serialized
  artifact and would move the Samsung golden even with identical values.
- **Report a phase complete only after `gh run list` confirms green.** A local
  green run is the precondition, not the proof. This is the specific failure
  this plan exists to correct.

## Verification Strategy

- **TEST-001:** `ruff check src scripts tests` → `All checks passed!`, exit `0`.
- **TEST-002:** `PYTHONPATH= python -m pytest tests/python -m "not network and not requires_artifacts and not golden_machine and not requires_julia" -q`
  → at PHASE-01 exit exactly `634 passed, 18 deselected, 3 xfailed`; at
  PHASE-04 exit at least `634 passed` with zero failures.
- **TEST-003:** `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp`
  → `Success: no issues found in 21 source files` (the file count rises by the
  number of modules added under `analysis/orchestrators/`).
- **TEST-004:** `gh run list --limit 2 --json conclusion --jq '[.[].conclusion] | unique'`
  → `["success"]`. Run after every phase's push. **This is the authoritative
  green signal for this plan; a local pass never substitutes for it.**
- **TEST-005:** `grep -rn "caller_value=26_400.0" src scripts | wc -l` → `1`.
- **TEST-006:** `PYTHONPATH= python -c "import sys; sys.path.insert(0,'src/python'); import reopt_pysam_vn.analysis as a; print(sorted(a.offsite_dppa._ORCHESTRATORS))"`
  → `['DPPA_CASE_1_NINHSIM', 'DPPA_SAMSUNG_TTC']`.
- **TEST-007:** `PYTHONPATH= python -m pytest tests/python/webapp/test_golden_parity.py -v`
  → `2 passed` (the web-API-vs-direct-call gate and the re-polarized manifest
  check).
- **TEST-008:** `PYTHONPATH= python -m pytest tests/python/test_repo_invariants.py -v`
  → all pass, including `test_regulatory_watch_rows_are_not_overdue`.
- **TEST-009:** `git diff --stat examples/` after every phase → **empty**. The
  goldens must not move (CON-001).
- **MANUAL-001:** Read the complete `ruff --fix` diff before committing
  PHASE-01, with specific attention to every removed import under
  `src/python/reopt_pysam_vn/analysis/` and
  `src/python/reopt_pysam_vn/integration/`.
- **MANUAL-002:** Read every hit of
  `grep -rn "parity-gated\|bit-for-bit" README.md docs/ src/python/reopt_pysam_vn/`
  after PHASE-02 and confirm each remaining statement is factually true against
  the test file it describes.
- **MANUAL-003:** Before PHASE-02's branch deletions, run
  `git log --oneline main..<branch>` for each of the three branches and record
  the counts. Delete only those returning zero lines.
- **MANUAL-004:** Start the web app
  (`PYTHONPATH=src/python python -m uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000`),
  open `http://127.0.0.1:8000/deals/new`, and confirm the "Offsite DPPA" mode is
  still selectable and that submitting the case-1 payload reaches a `done` run
  page rather than an error card.
- **OBS-001:** After PHASE-01, confirm the CI job duration returns to the
  ~1m30s range seen on the last green run (`30135167312`). The three red runs
  completed in 44–48 s because they aborted at the lint step; a run that is
  still under ~60 s has not reached the test step.

## Risks and Alternatives

- **RISK-001:** PHASE-01 touches hundreds of files mechanically, making any
  genuine regression hard to spot in review. Mitigation: the phase is
  behaviour-frozen — the suite count must be byte-identical before and after
  (CON-005) — and the auto-fix, the manual fixes, and the `noqa` cleanup should
  land as three separate commits so a bisect is meaningful.
- **RISK-002:** clearing 766 violations conflicts with any in-flight branch.
  Mitigation: the three known branches are stale (last commits 2026-03-03 and
  2026-05-06) and are triaged in PHASE-02; no active development is in flight.
- **RISK-003:** pinning `ruff==0.16.1` freezes the lint rule set, so the
  repository stops receiving new diagnostics. Mitigation: accepted — a
  deliberate, reviewed version bump is strictly better than an unannounced one.
  Note the pin in `AGENTS.md` §2 so a future upgrade is a conscious task.
- **RISK-004:** PHASE-04's widened contract is the second design of an interface
  with only two implementations, so it may still be wrong for a third deal.
  Mitigation: this is expected and is why TASK-04-12 documents which blocks came
  back empty. Two implementations is the minimum from which a real abstraction
  can be derived; the alternative — designing for a hypothetical third — is what
  produced the current single-key front door.
- **ALT-001:** Narrow ruff's `select` back to `["E4","E7","E9","F"]` instead of
  clearing the violations. Rejected: it would restore green in minutes but leave
  the identical trap armed for `mypy` and every unpinned dependency, and it
  discards 19 genuinely diagnostic findings (`BLE001` ×14, `S110` ×5).
- **ALT-002:** Register `ninhsim_solar_storage_60pct` as the second orchestrator.
  Rejected per ASM-005: it is structurally an onsite case — `run_onsite`'s
  dispatch-coverage block was written to mirror its coverage function — so
  registering it under the offsite front door would misclassify it.
- **ALT-003:** Register `dppa_case_2` (the largest and most complete DPPA
  engine). Rejected per ASM-005: its pipeline is driven by separate phase
  scripts exchanging git-ignored JSON under `artifacts/`, so composing it
  in-process is substantial new work that would dominate the phase and obscure
  the contract question it exists to answer. It is the natural third
  registration, once the contract has been proven by a smaller case.
- **ALT-004:** Delete the drift tripwire in `test_golden_parity.py` outright.
  Rejected: it would remove the only automated signal that the Samsung
  divergence exists, re-hiding a known defect. S5's manifest keeps the signal
  and fixes only the inverted polarity.

## Suggested Next Step

Execute PHASE-01. It is the shortest phase, it is a prerequisite for trusting
any result from the other three, and its exit criterion —
`gh run list --limit 2` reporting `success` on both matrix legs — is the first
verified-green CI this repository will have had since 2026-07-24. Do not begin
PHASE-02 until that command returns `["success"]`.
