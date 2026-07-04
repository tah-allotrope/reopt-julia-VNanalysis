# REopt PySAM VN

Techno-economic optimization and finance modeling for solar, wind, storage, and corporate PPA workflows in Vietnam using [NREL REopt.jl](https://github.com/NREL/REopt.jl) plus PySAM.

## Analysis Modes — onsite & offsite/DPPA

The key function is analyzing future Vietnam projects in two modes from one descriptor (`DealConfig`), via the first-class `reopt_pysam_vn.analysis` package — see **[docs/onsite_vs_offsite.md](docs/onsite_vs_offsite.md)**.

| Mode | What | Entry point | CLI |
|---|---|---|---|
| **Onsite (BTM)** | REopt PV+BESS sizing/dispatch vs EVN TOU | `run_onsite(deal_config)` → `OnsiteResult` | `python -m reopt_pysam_vn.analysis onsite ...` |
| **Offsite / DPPA** | PySAM developer finance + CfD settlement + strike search | `run_offsite_dppa(deal_config)` → `OffsiteDppaResult` | `python -m reopt_pysam_vn.analysis offsite_dppa ...` |

```python
from reopt_pysam_vn.analysis import DealConfig, run_onsite, run_offsite_dppa
```

The bespoke per-deal modules under `integration/` (`dppa_case_1/2/3`, `dppa_samsung_ttc`, `ninhsim_solar_storage_60pct`) remain the orchestration engines behind a registry and are **deprecated as direct entry points** — new work should call `reopt_pysam_vn.analysis`. Samsung-TTC is parity-gated bit-for-bit (`tests/python/analysis/test_samsung_ttc_parity.py`).

There is also an internal, localhost-only web UI over this package — see [`src/python/reopt_pysam_vn/webapp/README.md`](src/python/reopt_pysam_vn/webapp/README.md).

## Tech Stack

- **Julia 1.10+** with REopt.jl v0.56.4, JuMP, HiGHS
- **Python 3.10+** for REopt preprocessing, PySAM integration, analytics, and tests
- **Pipeline:** `Scenario(dict)` → `REoptInputs(s)` → `run_reopt(m, inputs)` → results dict

## Project Structure

```
data/
  vietnam/                 Versioned Vietnam-specific policy data
  raw/saigon18/            Source workbook for the Saigon18 case study
  interim/saigon18/        Extracted and transformed Saigon18 inputs
src/
  julia/
    REoptVietnam.jl        Julia preprocessing module
  python/
    reopt_pysam_vn/
      reopt/               REopt-specific Python package code
      pysam/               PySAM package scaffolding and finance modules
      integration/         Cross-engine bridge code
scripts/
  julia/                   Julia execution scripts
  python/
    reopt/                 REopt-oriented Python workflows
    pysam/                 PySAM-oriented Python workflows
    integration/           Combined case-study and reporting workflows
plans/
  active/                  Current planning docs
  archive/                 Historical planning docs
tests/
  julia/                   Julia tests
  python/
    reopt/                 Python REopt tests
    pysam/                 Python PySAM tests
    integration/           Python integration and case-study tests
  cross_language/          Julia/Python cross-validation tests
  baselines/               Regression baselines
```

## Quick Start

```powershell
# 1. Set API keys (or put them in NREL_API.env — see NREL_API.env.example)
$env:NREL_DEVELOPER_API_KEY = "your-key"
$env:NREL_DEVELOPER_EMAIL   = "your-email"

# 2. Validate inputs (no solver — fast)
$env:JULIA_PKG_PRECOMPILE_AUTO = "0"
julia --project --compile=min scripts/julia/run_vietnam_scenario.jl --no-solve

# 3. Run full optimization (HiGHS solver, ~60s first run)
julia --project --compile=min scripts/julia/run_vietnam_scenario.jl

# Output lands in artifacts/results/examples/commercial-rooftop_reopt-results.json
```

## Saigon18 Workflow

```powershell
# 1. Extract the case-study workbook into canonical interim JSON
python scripts/python/reopt/extract_excel_inputs.py `
  --excel data/raw/saigon18/2026-01-29_saigon18_excel_model_v2.xlsm

# 2. Build canonical Saigon18 scenarios
python scripts/python/reopt/build_saigon18_reopt_input.py

# 3. Validate a canonical scenario without solving
$env:JULIA_PKG_PRECOMPILE_AUTO = "0"
julia --project --compile=min scripts/julia/run_vietnam_scenario.jl `
  --scenario scenarios/case_studies/saigon18/2026-03-20_scenario-a_fixed-sizing_evntou.json `
  --no-solve

# 4. Solve a canonical scenario
julia --project --compile=min scripts/julia/run_vietnam_scenario.jl `
  --scenario scenarios/case_studies/saigon18/2026-03-20_scenario-a_fixed-sizing_evntou.json

# Result lands in artifacts/results/saigon18/2026-03-20_scenario-a_fixed-sizing_evntou_reopt-results.json
```

## Vietnam Preprocessing Tool

The preprocessing tool applies Vietnam-specific defaults to any REopt input dict **before** `Scenario()` construction. Available in both Julia and Python with identical output.

### Usage (Julia)

```julia
include("src/julia/REoptVietnam.jl")
using .REoptVietnam

vn = load_vietnam_data()
d = JSON.parsefile("scenarios/templates/vn_commercial_rooftop_pv.json")
delete!(d, "_template")
apply_vietnam_defaults!(d, vn; customer_type="commercial", region="south")
s = Scenario(d)
```

### Usage (Python)

```python
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data, apply_vietnam_defaults

vn = load_vietnam_data()
d = json.load(open("scenarios/templates/vn_commercial_rooftop_pv.json"))
d.pop("_template", None)
apply_vietnam_defaults(d, vn, customer_type="commercial", region="south")
```

### What it does

- Builds 8760 TOU energy rate series from EVN tariff data
- Zeros all US-specific incentives (ITC, MACRS, rebates)
- Sets Vietnam financial defaults (CIT 20%, discount rates, 25-year analysis)
- Sets grid emissions factor (0.681 tCO2e/MWh constant series)
- Applies PV/Wind/Battery/Generator costs by region (north/central/south)
- Configures Decree 57 export rules (20% cap, surplus purchase rate)
- **Non-destructive:** user values already in the dict are never overwritten

### Vietnam Data Files (`data/vietnam/`)

| File | Contents | Update Trigger |
|---|---|---|
| `vn_tariff_2025.json` | EVN TOU tariff by customer type & voltage | New EVN pricing decision |
| `vn_tech_costs_2025.json` | PV/Wind/Battery/Generator costs by region | Market price surveys |
| `vn_financial_defaults_2025.json` | CIT rates, discount rates, tax holidays | New CIT law or decree |
| `vn_emissions_2024.json` | Grid emission factor (HUST/MONRE study) | Annual MONRE study |
| `vn_export_rules_decree57.json` | Rooftop export cap, surplus rate, DPPA | New decree |

Update policy data by creating a new versioned file and changing one line in `manifest.json`.

## Scenario Templates

Pre-filled Vietnam templates in `scenarios/templates/` — override only Site/Load/sizing:

| Template | Use Case | Technologies |
|---|---|---|
| `vn_commercial_rooftop_pv.json` | Commercial building, HCMC | PV + Storage |
| `vn_industrial_pv_storage.json` | Industrial facility, south | PV + Storage |
| `vn_offgrid_microgrid.json` | Remote site, central | PV + Wind + Generator + Storage |
| `vn_hospital_resilience.json` | Hospital, HCMC (4h outage) | PV + Storage |

## Testing

4-layer test suite with a PowerShell test runner:

```powershell
.\tests\run_all_tests.ps1              # All layers (~15s for L1-3, ~60s+ for L4)
.\tests\run_all_tests.ps1 -SkipLayer4  # Fast: Layers 1-3 only
.\tests\run_all_tests.ps1 -SmokeOnly   # Layer 4 smoke tests (no solver)
.\tests\run_all_tests.ps1 -Layer 2     # Single layer only
```

| Layer | What | Speed |
|---|---|---|
| **1: Data Validation** | Schema compliance, value bounds | <2s |
| **2: Unit Tests** | All exported functions, edge cases | <3s |
| **3: Cross-Validation** | Julia vs Python identical output | <5s |
| **4: Integration** | Scenario construction, solver runs, regression baselines | ~30-60s/scenario |

## Python Setup

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

- PySAM support is now scaffolded through the `nrel-pysam` dependency.
- PySAM-specific tests are skipped automatically when the package is unavailable.

## Generated Outputs

- Solve outputs live under `artifacts/results/` and comparison/summary reports under `artifacts/reports/` — these are **local-only and git-ignored** (regenerable from tracked source + `data/` + `scenarios/`). Scripts still write here; git does not track them.
- Generated HTML reports (`reports/*.html`) and decks (`present/`, `reports/decks/`) are likewise local-only. Markdown deliverables (`reports/*.md`) stay tracked.
- A small set of frozen **golden reference runs** is tracked under `examples/` so a fresh clone keeps representative results (see `examples/README.md`).
- Historical path changes are documented in `docs/legacy-path-map.md`.

## Script Paths (canonical)

The top-level `scripts/python/*.py` shim layer was removed (2026-06-12). Call scripts at their canonical subdir path instead — `scripts/python/{reopt,pysam,integration}/<name>.py`.

**Redirect rule for removed shims:** a former `scripts/python/<name>.py` now lives at `scripts/python/integration/<name>.py`, **except**:

| Former flat path | Canonical path |
|---|---|
| `scripts/python/extract_excel_inputs.py` | `scripts/python/reopt/extract_excel_inputs.py` |
| `scripts/python/build_saigon18_reopt_input.py` | `scripts/python/reopt/build_saigon18_reopt_input.py` |
| `scripts/python/dppa_settlement.py` | `scripts/python/reopt/dppa_settlement.py` |
| `scripts/python/equity_irr.py` | `scripts/python/reopt/equity_irr.py` |
| `scripts/python/compare_regimes.py` | `scripts/python/reopt/compare_regimes.py` |
| `scripts/python/compare_reopt_vs_excel.py` | `scripts/python/reopt/compare_reopt_vs_excel.py` |
| `scripts/python/bess_dispatch_analysis.py` | `scripts/python/reopt/bess_dispatch_analysis.py` |
| `scripts/python/two_part_tariff_sensitivity.py` | `scripts/python/reopt/two_part_tariff_sensitivity.py` |
| `scripts/python/strike_price_discovery.py` | `scripts/python/pysam/strike_price_discovery.py` |

**Relocated real scripts** (these were not shims — full implementations moved from the flat level into `integration/`): `generate_deck_2.py`, `generate_deck_3.py`, `generate_final_report.py`, `generate_phase3_report.py`, `generate_phase4_report.py`, `generate_phase5_report.py`, `generate_tou_migration_final_report.py` → all now under `scripts/python/integration/`. They write to cwd-relative paths, so run them from the repo root as before.

## Vietnam-Specific Notes

- The preprocessing tool automatically handles all Vietnam overrides: US incentive zeroing, grid emissions, EVN tariff, tech costs, and Decree 57 export rules.
- When using `loads_kw`, the `ElectricLoad.year` field is **required**.
- Outage modeling is a soft constraint by default — add `Site.min_resil_time_steps` for hard constraint.

## References

- [REopt.jl GitHub](https://github.com/NREL/REopt.jl)
- [REopt API Docs](https://developer.nlr.gov/docs/energy-optimization/reopt/v2/)
- [DeepWiki - REopt.jl Internals](https://deepwiki.com/NatLabRockies/REopt.jl)
