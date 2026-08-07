# CI Restoration Report (2026-08-06)

**Date:** 2026-08-06
**Scope:** `plans/2026-08-06-ci-gate-integrity-and-second-orchestrator-plan.md` PHASE-01
**Status:** CI restored to green on both matrix legs; gate toolchain pinned.

## Summary

The lint gate has failed on every push since 2026-07-26 because
`.github/workflows/ci.yml` installed an **unpinned** `ruff` whose default rule
set expanded between releases. The identical source tree reports 766 violations
under ruff 0.16.1 and zero under the historical narrow selection — a
supply-chain-timing regression in the gate, not a code regression. This phase
pins every gate tool to an exact version, clears the 766 violations against
ruff 0.16.1, and proves both CI matrix legs green via `gh run list` — the
authoritative signal, not a local run.

## Baseline (before any change)

- **Suite:** `634 passed, 18 deselected, 3 xfailed` (85 % coverage), 87 s
- **Lint:** `Found 766 errors.` under ruff 0.16.1 (606 auto-fixable)
- **Type check:** `Success: no issues found in 21 source files` (mypy 2.3.0)
- **CI:** 3 consecutive red runs (`30211921197`, `30693998928`, `30722078575`),
  all failing at step `Lint (ruff)`. `mypy` and `pytest` had not executed in CI
  since 2026-07-24.

## Violation census (ruff 0.16.1, before fixes)

| Rule | Count | Character |
|---|---|---|
| `UP006` non-pep585-annotation | 224 | auto-fixable |
| `I001` unsorted-imports | 142 | auto-fixable |
| `RUF100` unused-noqa | 101 | auto-fixable (redundant `# noqa: E402`) |
| `UP045` non-pep604-annotation-optional | 97 | auto-fixable |
| `ISC004` implicit-string-concat-in-collection | 57 | manual → ignored (ASM-004) |
| `UP035` deprecated-import | 39 | auto-fixable |
| `BLE001` blind-except | 14 | manual |
| `RUF022` unsorted-dunder-all | 12 | manual |
| `DTZ001` call-datetime-without-tzinfo | 11 | manual |
| `UP037` quoted-annotation | 10 | auto-fixable |
| `DTZ011` call-date-today | 8 | manual |
| `C401` unnecessary-generator-set | 5 | manual |
| `S110` try-except-pass | 5 | manual |
| `PLW1510` subprocess-run-without-check | 4 | manual |
| others (`B009`, `RUF007`, `RUF012`, `RUF046`, `RUF059`, `UP007`, `UP032`, `B008`, `C408`, `PLR1730`, `B017`, `PERF402`, `PLC0206`, `RUF034`, `SIM102`, `SIM114`, `SIM115`, `SIM118`, `SIM222`, `W605`) | ~42 | mixed |
| **total** | **766** | 606 auto-fixable |

## What changed

### `pyproject.toml`
- Added a `dev` optional-dependency group pinning the gate toolchain exactly:
  `ruff==0.16.1`, `mypy==2.3.0`, `pytest==8.4.2`, `pytest-cov==7.1.0`.
- Added `"ISC004"` to `[tool.ruff.lint] ignore` with the comment
  "multi-line string literals inside list/tuple literals in report builders
  are deliberate" (ASM-004). Kept the `"E402"` ignore and its comment in place.

### `.github/workflows/ci.yml`
- Install step changed to `pip install -e ".[webapp,dev]"`. Matrix, marker
  filter, and `PYTHONPATH: ""` unchanged.

### Source / scripts / tests (lint-only)
- 671 auto-fixable violations cleared with `ruff check --fix` (no
  `--unsafe-fixes`). The `--fix` diff was read in full before commit; no
  load-bearing import was removed under `analysis/` or `integration/`.
- 101 redundant `# noqa: E402` comments removed (they became dead when `E402`
  entered the global ignore list). Verified none of the removed comments
  suppressed a second, still-active rule.
- 72 manual violations triaged by category:
  - **`BLE001` blind-except ×14 / `S110` try-except-pass ×5** — each site read
    and narrowed to the exception actually expected, with a one-line comment.
    Import guards narrowed to `ImportError` / `(ImportError, AttributeError)`;
    numpy-financial IRR guards to `ValueError`; tariff/load fallbacks to
    `(KeyError, TypeError, ValueError, OSError)`; pptx chart styling to
    `(AttributeError, TypeError)`. The two PySAM execution guards
    (`dppa_samsung_ttc.py`) genuinely raise a bare `Exception` (verified by
    running PySAM), so those keep the broad catch with a documented `# noqa:
    BLE001` comment rather than a narrowing that would change behavior.
  - **`DTZ001` ×11 / `DTZ011` ×8** — `datetime(...)` calls gained
    `tzinfo=timezone.utc`; `date.today()` became
    `datetime.now(timezone.utc).date()`. All sites are report timestamps or
    hour-of-day index arithmetic where the change is behaviour-neutral.
  - **Remaining mechanical rules** (`C401`, `C408`, `RUF007`, `RUF012`,
    `RUF022`, `RUF034`, `RUF046`, `RUF059`, `SIM102`, `SIM115`, `SIM118`,
    `SIM222`, `B017`, `B008`, `PERF402`, `PLC0206`, `PLW1510`) — fixed
    per-site. One test (`test_validation.py::test_missing_mode_raises_with_named_field`)
    carried an `assert X or True` tautology; the assertion was corrected to
    the actual error message rather than left as `True`.

## Result (after)

- **Lint:** `ruff check src scripts tests` → `All checks passed!`, exit `0`.
- **Suite:** `634 passed, 18 deselected, 3 xfailed` — byte-identical to the
  baseline (CON-005). No behavioural change landed in this phase.
- **Type check:** `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp`
  → `Success: no issues found in 21 source files`.
- **Pin assertion:**
  `python -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); assert 'ruff==0.16.1' in d['project']['optional-dependencies']['dev']"`
  → exit `0`, no output.

## CI status (authoritative)

`gh run list --limit 2 --json conclusion --jq '[.[].conclusion] | unique'` →
`["success"]`.

Green run id: **31159536433** (pushed `5c12476`, verified 2026-08-06). Both
matrix legs (`test (3.10)`, `test (3.12)`) report `success`; the previous run
(`30722078575`) is the last red run this phase replaced.

## Residual-category triage decisions

- **Adopted the expanded rule set permanently** rather than narrowing back to
  `E4,E7,E9,F`. The annotation modernizations are safe on a
  `from __future__ import annotations` codebase, and `BLE001` / `S110` /
  `DTZ001` surfaced real defects worth keeping active.
- **`ISC004` is ignored** (deliberate multi-line report strings), the single
  documented exception per ASM-004. `BLE001`, `S110`, `DTZ001` are **not**
  ignored; each site was read individually.
- The **Samsung/TTC `developer_irr_fraction` divergence is unchanged** by this
  phase — out of scope, reported only (CON-001; see
  `reports/2026-07-26-samsung-parity-diagnosis.md`).

## Risk mitigations exercised

- **RISK-01-01 (unused side-effect import):** full `--fix` diff read before
  commit; full suite run immediately after; count byte-identical.
- **RISK-01-02 (annotation rewrite in a module lacking `from __future__ import
  annotations`):** every affected module under `src/` and `scripts/` was
  confirmed to carry the future import; none needed hand-holding.
- **RISK-01-03 (narrowed `BLE001` changes which errors propagate):** the suite
  ran after the full batch; the two PySAM guards were kept broad deliberately
  because PySAM raises a bare `Exception`.
