# 2026-08-19 Solar Resource and Array Configuration (PHASE-03)

## Measured yields on tracked Ninh Thuan resource (`ninhsim_himawari_2019_60min.csv` at 12.5257°N, 109.0200°E)

- 1 MWp DC, `dc_ac_ratio=1.2`, `losses=14`, `inv_eff=96`:
  - Inherited `array_type=2` (1-axis backtracked tracking, tilt 0): **1,888.3 kWh/kWp/yr**
  - Fixed open rack at tilt = latitude (12.5257°): **1,527.9 kWh/kWp/yr**
  - Delta: **+23.6%** on identical irradiance when tracking is assumed.

- 50 MW capacity factors on same file (`annual_energy / (system_capacity_kw × 8760)`):
  - Fixed open rack tilt=latitude, `array_type=0`: **17.44%** (inside 14–20% band)
  - 1-axis tracking `array_type=2`: **21.56%** (outside band, `xfail` previously)

## Changes in this phase

- Added `SOLAR_RESOURCE_CATALOG` and `great_circle_km` (haversine, R=6371 km) in `pysam/pvwatts_battery.py`.
- `generic_vn_dppa._try_pvwatts_generation` now sets `array_type`/`tilt`/`azimuth`/`gcr` explicitly via `_array_config(deal_config, site_lat)` and computes site-to-resource distance.
- `quality` now carries `solar_resource_file`, `solar_resource_latitude`, `solar_resource_longitude`, `solar_resource_distance_km` (rounded to 0.1 km), `array_type`, `tilt_degrees`. When distance ≥100 km, `solar_profile_source` becomes `pvwatts_fallback_resource` and a warning is appended.
- `_calibrate_to_target` rewritten per S2: daylight-only headroom redistribution, 50 iterations, infeasible annual targets clipped at AC cap with a warning and never injecting night energy.
- `integration/dppa_samsung_ttc._pvwatts_south_solar_8760` pinned explicitly to `array_type=2.0`, `tilt=0.0` so its output is bit-identical (plan 2026-08-19, ASM-005).
- `data/schemas/deal_config.schema.json` `plant.mounting` enum added (`fixed_open_rack` default, `fixed_roof`, `single_axis_tracking`).
- Capacity-factor gate rewritten to use the tracked file with explicit fixed-tilt config, no network, no `xfail`.

## Samsung invariance

- `integration/dppa_samsung_ttc.py` pins exactly the values `PySAM.Pvwattsv8.default("PVWattsSingleOwner")` ships (`array_type 2.0`, `tilt 0.0`), verified via `python -c "import PySAM.Pvwattsv8 as p; m=p.default('PVWattsSingleOwner'); print(m.SystemDesign.array_type, m.SystemDesign.tilt)"` on `nrel-pysam==7.1.0`.

## Disclosure threshold

- 100 km great-circle (ASM-003). Below: `solar_profile_source == "pvwatts"`, no warning. At or above: `pvwatts_fallback_resource` + warning.
