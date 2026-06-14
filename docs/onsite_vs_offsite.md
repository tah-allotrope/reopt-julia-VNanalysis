# Onsite vs Offsite/DPPA — Analysis Modes

The repo's key function is analyzing future Vietnam clean-energy projects in two modes.
Both are driven from one descriptor (`DealConfig`) through the `reopt_pysam_vn.analysis`
package — the first-class front door (library + CLI).

| | **Onsite (behind-the-meter)** | **Offsite / DPPA** |
|---|---|---|
| Question | "Size & dispatch PV+BESS at my site to cut my EVN bill" | "Does a Direct PPA with an offsite plant pencil for buyer and developer?" |
| Engine | REopt PV+BESS optimization vs EVN TOU | PySAM developer finance + CfD settlement + strike search |
| Entry point | `run_onsite(deal_config)` → `OnsiteResult` | `run_offsite_dppa(deal_config)` → `OffsiteDppaResult` |
| CLI | `python -m reopt_pysam_vn.analysis onsite ...` | `python -m reopt_pysam_vn.analysis offsite_dppa ...` |
| `DealConfig.mode` | `"onsite"` | `"offsite_dppa"` (`"both"` runs both) |

## Library usage

```python
from reopt_pysam_vn.analysis import DealConfig, run_onsite, run_offsite_dppa

deal = DealConfig.from_dict(json.load(open("scenarios/case_studies/samsung_ttc/samsung_ttc_deal_config.json")))

# Offsite/DPPA — registry routes the Samsung case to its orchestrator
offsite = run_offsite_dppa(deal, extracted=json.load(open(".../samsung_ttc_extracted_inputs.json")))
print(offsite.decision["recommended_position"])

# Onsite — post-process a (pre-solved or injected) REopt results dict
onsite = run_onsite(deal, results=reopt_results, extracted={"loads_kw": [...]})
print(onsite.dispatch["achieved_delivered_fraction_of_load"])
```

`run_onsite` never invokes the Julia solver implicitly — pass a pre-solved `results`
dict or a `solve_fn`. `run_offsite_dppa` resolves the orchestrator from
`deal_config.case` via a registry (`register_orchestrator(case, fn)`), or accepts an
injected `combined_decision_fn`.

## CLI usage

```powershell
# onsite (post-process a solved REopt results dict)
python -m reopt_pysam_vn.analysis onsite `
  --config scenarios/case_studies/<case>/deal_config.json `
  --results <reopt-results>.json --extracted <inputs>.json --out out.json

# offsite/DPPA (runs the registered orchestrator end-to-end)
python -m reopt_pysam_vn.analysis offsite_dppa `
  --config scenarios/case_studies/samsung_ttc/samsung_ttc_deal_config.json `
  --extracted data/interim/samsung_ttc/samsung_ttc_extracted_inputs.json --out out.json
```

JSON inputs may carry a UTF-8 BOM (Windows editors) — the CLI reads with `utf-8-sig`.

## Relationship to the bespoke case modules (migration status)

The generalized pipelines reuse the same tested primitives the per-deal modules
orchestrate (see [`onsite_offsite_reuse_map.md`](onsite_offsite_reuse_map.md)):
`dppa_case_2` (settlement engine), `bridge.py` (PySAM hub), `reopt/preprocess.py`.

- **Samsung-TTC** is parity-gated: `run_offsite_dppa` reproduces the bespoke
  combined-decision **bit-for-bit** (`tests/python/analysis/test_samsung_ttc_parity.py`).
- The case modules (`integration/dppa_case_1/2/3`, `dppa_samsung_ttc`,
  `ninhsim_solar_storage_60pct`) remain the orchestration engines behind the registry
  and keep their own tests. They are **deprecated as direct public entry points** — new
  work should call `reopt_pysam_vn.analysis`.
- **Follow-up (next cycle):** invert the delegation — move each orchestration into
  `analysis/` and leave the case modules as thin wrappers emitting `DeprecationWarning`,
  then remove them. Staged separately because it must preserve the bit-exact parity and
  the existing `test_dppa_*` suites.
