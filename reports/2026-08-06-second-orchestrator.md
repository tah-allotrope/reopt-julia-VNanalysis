# Second Offsite Orchestrator Report (2026-08-06)

**Date:** 2026-08-06
**Scope:** `plans/2026-08-06-ci-gate-integrity-and-second-orchestrator-plan.md` PHASE-04
**Status:** Complete — `run_offsite_dppa` now serves two registered deals.

## Summary

The public `reopt_pysam_vn.analysis` offsite API served exactly one deal:
`DPPA_SAMSUNG_TTC`. Every other `DealConfig.case` raised `ValueError: no
offsite orchestrator registered`. This phase widened the orchestrator contract
to accommodate deals that consume a REopt results dict, and registered
`dppa_case_1` (Ninhsim) behind it — so the front door is now a two-deal API and
the generic-path abstraction is no longer a design question but a diff.

## The widened contract (S1/S2)

```
orchestrator(extracted: dict, *, run_developer: bool = True,
             results: dict | None = None, scenario: dict | None = None) -> dict
```

- **`results`** — the `results` block of a REopt solve output (PV, Wind,
  ElectricStorage, ElectricUtility, Financial sub-dicts with 8760 `*_series_kw`).
- **`scenario`** — the REopt `Scenario` input dict the solve was built from.
- **Backward compatibility:** `run_offsite_dppa` forwards `results`/`scenario`
  to an orchestrator **only when not `None`**, so the existing
  two-parameter Samsung orchestrator keeps its exact call shape. Verified by
  `test_two_parameter_orchestrator_keeps_its_call_shape`.
- **Resolution order (S2):** explicit keyword arg → `deal_config.raw[<name>]` →
  `None`. `extracted=None` stays a hard error; `results=None`/`scenario=None`
  is legal (the Samsung case). Verified by
  `test_case_1_raw_fallback_resolves_all_three_inputs`.

## The S3 composition and S4 adapter

`analysis/orchestrators/dppa_case_1.py::build_case_1_offsite_artifact`
composes the four tested `integration.dppa_case_1` builders:

```
reopt_summary = build_dppa_case_1_reopt_summary(results, extracted, scenario)
pysam_results = developer_runner(reopt_summary) if run_developer and runner
                else build_dppa_case_1_placeholder_pysam_results(reopt_summary)
comparison    = build_dppa_case_1_comparison(reopt_summary, pysam_results)
artifact      = build_dppa_case_1_combined_decision(reopt_summary, pysam_results, comparison)
```

`_adapt_case_1_artifact` maps the raw case-1 artifact onto the `OffsiteDppaResult`
block vocabulary. The mapping actually used:

| `OffsiteDppaResult` block | Source in the case-1 artifact |
|---|---|
| `case` | literal `"DPPA_CASE_1_NINHSIM"` |
| `model` | `artifact["model"]` |
| `deal` | `artifact["site_and_tariff_basis"]` |
| `base_settlement` | `{energy_summary, optimal_mix, financial}` from `reopt_summary` |
| `strike_sweep` | `{}` |
| `adder_sensitivity` | `{}` |
| `regime_stress` | `{}` |
| `decision` | `artifact["decision"]` |
| `quality` | `{basis: "directional", status, warnings, developer_basis}` |
| `raw["case_1_artifact"]` | the complete unmodified artifact |

## What the three empty blocks reveal (the phase's main analytical output)

Case 1 is a **fixed private-wire strike** with no sweep, no adder lever, and no
regime stress — so `strike_sweep`, `adder_sensitivity`, and `regime_stress`
all came back `{}`. This is the honest representation: `OffsiteDppaResult.to_dict()`
emits every block unconditionally, and an empty dict is exactly "this deal
structure does not have that lever." Nothing is lost — the full original lives
under `raw["case_1_artifact"]`.

**The observation for a future third registration:** the `_OFFSITE_BLOCKS`
vocabulary is Samsung-shaped (built around a strike sweep and negotiation
summary). A deal with no sweep will legitimately emit empty blocks; a deal with
a *different* lever (e.g. a wind/capacity-factor stress, or a tariff-regime
sensitivity) will need its data placed in `base_settlement` or `regime_stress`
by its own adapter. The adapter pattern — map onto the common blocks where a
defensible mapping exists, preserve the complete original under `raw` — is the
extension rule. The block vocabulary itself was **not** renamed, widened, or
reordered (that order is load-bearing for the Samsung golden comparison).

`quality.developer_basis` is `"placeholder"` when the placeholder builder
produced `pysam_results` and `"pysam"` when a `developer_runner` produced them.
When `run_developer=True` with no runner injected, a warning string is appended
to `artifact["warnings"]` noting the developer screen ran in placeholder mode.

## Files

- `src/python/reopt_pysam_vn/analysis/offsite_dppa.py` (modify) — widened
  `CombinedDecisionFn` documentation, added `results`/`scenario` to
  `run_offsite_dppa` with `deal_config.raw` fallbacks, conditional kwargs,
  rewritten module docstring. `register_orchestrator`'s signature, the
  `extracted is None` error, and the `OffsiteDppaResult.from_dict(raw)` return
  path unchanged.
- `src/python/reopt_pysam_vn/analysis/orchestrators/{__init__,dppa_case_1}.py`
  (create) — the new package.
- `src/python/reopt_pysam_vn/analysis/__init__.py` (modify) — lazy
  `register_orchestrator("DPPA_CASE_1_NINHSIM", ...)`; every existing export in
  `__all__` kept.
- `src/python/reopt_pysam_vn/webapp/service.py` (modify) — module docstring
  only; **no behavioural change** (CON-002). The acceptance test embeds
  `results`/`scenario` on the deal config, so `run_analysis` needs no new
  plumbing.
- `scenarios/case_studies/ninhsim/dppa_case_1_deal_config.json` (create) —
  validates against `data/schemas/deal_config.schema.json`.
- `tests/python/analysis/test_offsite_dppa_case_1.py` (create) — hermetic
  (synthetic REopt results fixture, no `artifacts/`, no `requires_artifacts`
  marker, PySAM-free placeholder developer path).
- `tests/python/webapp/test_api_runs.py` (modify) — the case-1 acceptance test.
- `README.md`, `docs/onsite_vs_offsite.md` (modify) — two registered cases +
  `register_orchestrator` as the extension point.

## Verification

- `PYTHONPATH= python -m pytest tests/python/analysis/test_offsite_dppa_case_1.py -v`
  → all pass (TDD: the registry-error test failed red before implementation,
  removed once green).
- Registry: `sorted(reopt_pysam_vn.analysis.offsite_dppa._ORCHESTRATORS)` →
  `['DPPA_CASE_1_NINHSIM', 'DPPA_SAMSUNG_TTC']`.
- `tests/python/webapp/` → all pass, including the new acceptance test
  (`POST /api/runs` with the case-1 config reaches state `done`, not 422).
- Samsung regression (CON-002): `tests/python/webapp/test_golden_parity.py`
  and `tests/python/analysis/test_offsite_dppa.py` → `7 passed` — the Samsung
  path is byte-for-byte unaffected.
- `mypy src/python/reopt_pysam_vn/analysis src/python/reopt_pysam_vn/webapp` →
  `Success: no issues found in 23 source files` (21 → 23 with the two new
  orchestrator modules; the `orchestrators/` package satisfies
  `disallow_untyped_defs`).
- Full portable suite: **654 passed, 18 deselected, 3 xfailed** (643 → +10
  case-1 tests +1 webapp acceptance test; no previously passing test now fails).
- `git diff --stat examples/` → empty (CON-001: goldens untouched).

## Risk mitigations exercised

- **RISK-04-01 (Samsung call-shape break):** S1's backward-compatibility rule
  (forward `results`/`scenario` only when non-`None`) plus the explicit
  regression run; `_samsung_ttc_orchestrator`'s signature was not edited.
- **RISK-04-02 (S4 mapping judged wrong later):** no case-1 golden was created;
  the complete original artifact is preserved under `raw["case_1_artifact"]`, so
  a future remapping is lossless.
- **RISK-04-03 (mypy `disallow_untyped_defs`):** the new `orchestrators/` package
  is fully annotated; values crossing to untyped `integration.dppa_case_1` are
  treated as `dict` / `dict[str, Any]`. No mypy override or gate loosening.
- **RISK-04-04 (empty blocks read as a broken adapter):** this report documents
  the emptiness as a deliberate finding about the block vocabulary, and the
  tests assert the empty dicts explicitly so the intent is executable.
