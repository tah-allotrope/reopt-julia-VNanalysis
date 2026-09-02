# Decree 243/2026 Export-Cap Delta — Fixed-Dispatch First-Order Estimate

**Date:** 2026-07-18
**Input:** `examples/saigon18_scenario-a_reopt-solve.example.json`
**Method:** `reopt_pysam_vn.reopt.decree243_delta.compute_export_cap_delta`

## Caveat

This is a **fixed-dispatch** comparison: the underlying REopt solve was not
re-optimized under the new 50% cap. It answers "given the PV/BESS sizing and
dispatch REopt already chose under the old 20%-cap assumption, how much more
of the *already-curtailed* surplus becomes exportable under Decree 243/2026's
50% cap" — a **lower bound** on the true benefit. A re-optimized solve under
the 50% cap would likely size PV larger and could capture additional value;
that re-optimization is flagged as follow-on work, not performed here.

## Presets compared

- **Decree 57/2025 (legacy, 20% cap):** `decree57_private_wire_standard`
- **Decree 243/2026 (active, 50% cap):** `decree243_export_50pct_standard`

Both are `private_wire` mode, `strike_vnd_kwh=1012.0`,
`excess_treatment="export_at_surplus"`, `surplus_rate_vnd_kwh=671.0` — the
only difference is `export_cap_pct` (20.0 vs 50.0).

## Results (annual)

| Metric | 20% cap (Decree 57) | 50% cap (Decree 243) | Delta |
|---|---:|---:|---:|
| Exported energy (kWh/yr) | 6,969,272 | 8,893,683 | 1,924,411 |
| Curtailed energy (kWh/yr) | 1,937,968 | 13,557 | -1,924,411 |
| Surplus revenue (VND/yr) | 4,676,381,226 | 5,967,661,070 | 1,291,279,843 |

**Headline: Decree 243/2026's 50% cap is worth an additional
1,291,279,843 VND/yr (~48,912 USD/yr at
26,400 VND/USD) in surplus export revenue on this fixed dispatch,
before any re-optimization.**

## Reproduce

```
.venv/Scripts/python.exe scripts/python/reopt/decree243_export_cap_delta.py
```
