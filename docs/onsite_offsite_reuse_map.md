# Onsite / Offsite-DPPA Pipeline — Reuse Map (Sprint 3, PHASE-01)

What the generalized `reopt_pysam_vn/analysis/{onsite,offsite_dppa}.py` pipelines reuse,
and which primitives each bespoke case module currently orchestrates. Built by inventorying
the in-package imports of the five case modules (TASK-01-04). Confirms the gap analysis claim:
the case modules are **orchestration glue over existing primitives**, so generalization is
extraction + parameterization, not new modeling.

## Shared primitives (the building blocks both pipelines compose)

| Primitive | Role | Used by |
|---|---|---|
| `reopt/preprocess.py` — `load_vietnam_data`, `apply_vietnam_defaults` | Vietnam policy defaults (tariff, costs, emissions, Decree 57) onto a REopt input dict | onsite; offsite (load/benchmark build) |
| `reopt/regime_runner.py` | TOU regime resolution + bill computation | onsite; offsite regime stress |
| `integration/bridge.py` — `build_*_single_owner_inputs` | **PySAM hub**: imports `pysam.{config,ppa,pvwatts_battery,single_owner}`; bridges REopt output → PySAM finance inputs | offsite developer screen; onsite finance |
| `integration/dppa_case_2.py` — `run_dppa_case_2_buyer_settlement`, `build_dppa_case_2_buyer_benchmark`, `build_dppa_case_2_physical_summary`, `build_dppa_case_2_settlement_inputs`, `build_dppa_case_2_contract_risk_sensitivity` | **Settlement/benchmark engine** (CfD settlement, buyer benchmark, physical match, adder sensitivity) | offsite (Samsung delegates wholesale) |
| `integration/strike_search.py` | Strike sweep / negotiation-band search | offsite strike sweep |
| `integration/assumptions.py` — `DEFAULT_TARGET_DEVELOPER_IRR_FRACTION` | Shared developer-IRR assumption | offsite developer screen |
| `pysam/{pvwatts_battery,single_owner,cashflow,ppa,metrics,config}.py` | PVWatts generation + Single Owner finance | both (via `bridge.py`) |

## Per-case orchestration (what each module imports from the package)

| Case module | In-package imports | Notes |
|---|---|---|
| `dppa_case_1.py` | `assumptions.DEFAULT_TARGET_DEVELOPER_IRR_FRACTION`, `reopt.preprocess.load_vietnam_data` | Earliest case; light reuse |
| `dppa_case_2.py` | `reopt.preprocess.{apply_vietnam_defaults, load_vietnam_data}` | **The engine** — everyone else delegates here |
| `dppa_case_3.py` | *(none from package)* | Self-contained `load_saigon18_*` helpers |
| `dppa_samsung_ttc.py` | `dppa_case_2.{run_dppa_case_2_buyer_settlement, build_dppa_case_2_buyer_benchmark, build_dppa_case_2_physical_summary, build_dppa_case_2_settlement_inputs, build_dppa_case_2_contract_risk_sensitivity}`, `reopt.preprocess.{apply_vietnam_defaults, load_vietnam_data}` | **Cleanest template** for `run_offsite_dppa` — orchestrates settlement + strike sweep + adder + regime stress into one combined decision |
| `ninhsim_solar_storage_60pct.py` | `assumptions.DEFAULT_TARGET_DEVELOPER_IRR_FRACTION`, `reopt.preprocess.load_vietnam_data` | Onsite-leaning (coverage fraction + developer revenue path) |

## Generalization plan

- **`run_offsite_dppa(deal_config)`** follows `build_samsung_ttc_combined_decision`: map the
  `DealConfig` → an `extracted`-style dict, then compose the `dppa_case_2` settlement engine +
  `strike_search` + `bridge` developer screen + regime stress into an `OffsiteDppaResult`
  (key-for-key the combined-decision artifact, so PHASE-04 parity is exact-comparable).
- **`run_onsite(deal_config)`** composes `preprocess` (Vietnam defaults) + `regime_runner` +
  `bridge`, producing an `OnsiteResult` (sizing / dispatch / economics).
- **Samsung-TTC is the parity gate** (PHASE-04): it has the richest, most recent golden output
  (`examples/samsung-ttc_combined-decision.example.json`) and already delegates to the shared engine.
