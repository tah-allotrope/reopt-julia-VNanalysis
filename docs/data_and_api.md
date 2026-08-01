# Data Layer & API Reference

## API Keys
- `NREL_API.env` file; `ENV["NREL_DEVELOPER_API_KEY"]` (PVWatts, Wind, NSRDB) and `ENV["NREL_DEVELOPER_EMAIL"]` (Cambium emissions).

## REopt API Reference
- **Base URL:** `https://developer.nlr.gov/api/reopt/stable`
- **Endpoints:** `/job/` (optimize), `/simulated_load/` (load profiles), `/peak_load_outage_times/` (outage starts)
- **API key signup:** `https://developer.nlr.gov/signup/`

> **Domain migration (completed 2026-03):** NREL retired `developer.nrel.gov` in favour of `developer.nlr.gov` (NLR = National Laboratory of the Rockies). All URLs in this repo have been updated. Existing API keys continue to work — only the domain changed. Old domain brownouts begin May 1 2026; full expiry May 29 2026.

## Extended Reference (DeepWiki — fetch on demand)
For deep REopt.jl internals (constraint math, source files, MPC, multi-node), fetch:
→ https://deepwiki.com/NatLabRockies/REopt.jl
Key pages: `/5.1-scenario-construction`, `/5.3-technology-configuration`, `/6.2-model-building-with-build_reopt!`, `/6.3-constraint-system`, `/7-results-and-post-processing`

## Vietnam Data Layer (`data/vietnam/`)
Versioned JSON files with Vietnam-specific assumptions, loaded by `legacy/julia/src/REoptVietnam.jl` (Julia, archived) and `src/python/reopt_pysam_vn/reopt/preprocess.py` (Python, primary) **before** `Scenario()`. Manifest-driven: update policy data by creating a new file + changing one line in `manifest.json`.

### Key Vietnam Values
| Parameter | Value | Source |
|---|---|---|
| Grid emission factor | 0.681 tCO2e/MWh (1.50 lb CO2/kWh) | HUST/MONRE 2024 study |
| Avg retail electricity price | VND 2,204/kWh (~$0.084/kWh) | EVN Decision 599/2025 |
| Standard CIT | 20% (10% preferential for RE) | CIT Law 2025 |
| RE tax holiday | 4yr exempt + 9yr 50% reduction | CIT Law 2025 |
| Rooftop solar export cap | 20% of generation to EVN | Decree 57/2025 |
| Surplus purchase rate | VND 671/kWh (~$0.026/kWh) | Decree 57/2025 |
| PV rooftop cost (South) | $600/kW | Market estimate 2025 |
| Battery `installed_cost_constant` | $0 (overrides US $222,115 default) | Vietnam market |

### Data Files
| Manifest Key | File | Update Trigger |
|---|---|---|
| `tariff` | `vn_tariff_2025.json` | New EVN pricing decision (~annual) |
| `tech_costs` | `vn_tech_costs_2025.json` | Market price surveys (~annual) |
| `financials` | `vn_financial_defaults_2025.json` | New CIT law or incentive decree |
| `emissions` | `vn_emissions_2024.json` | Annual MONRE/HUST study (Q1) |
| `export_rules` | `vn_export_rules_decree57.json` | New decree replacing Decree 57 |

### File Schema
Every file has `_meta` (version, effective_date, source, source_url, last_updated, currency) + `data` block. Code reads only `data`; `_meta` is for audit.
