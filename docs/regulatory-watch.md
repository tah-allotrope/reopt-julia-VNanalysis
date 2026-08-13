# Regulatory Watch

Tracks which regulation governs each `data/vietnam/*.json` file and whether the
active file is current. Whenever a `research/` brief lands documenting a
regulatory change, add or update a row here in the same commit. A row whose
Status is `STALE` blocks new client-facing analysis that relies on that file
until it is refreshed.

| Manifest key | Active file | Governing instrument(s) | Known supersession | Status | Last verified | Next review |
|---|---|---|---|---|---|---|
| tariff | vn_tariff_2025.json | Decision 963/QD-BCT (TOU, active), Decision 14/2025 (legacy), Decree 146/2025 (two-part trial) | — | CURRENT | 2026-08-06 | 2026-11-06 |
| tech_costs | vn_tech_costs_2025.json | Market price surveys | — | UNVERIFIED (pending primary-source check) | 2026-02-18 | 2026-09-12 |
| financials | vn_financial_defaults_2025.json | CIT Law 67/2025/QH15 (eff. 2025-10-01) — standard rate 20%, plus 15% micro / 17% small-enterprise rates | Law 67/2025/QH15 supersedes the prior CIT law | CURRENT | 2026-08-13 | 2027-02-13 |
| emissions | vn_emissions_2024.json | HUST/MONRE grid-factor study | 2023 factor 0.6592 tCO2/MWh published (Official Letter 1726/BDKH-PTCBT); repo file still carries 0.681 | UNVERIFIED (pending primary-source check) | 2026-02-18 | 2026-09-12 |
| export_rules | vn_export_rules_2026_decree243.json | Decree 243/2026 (amends Decree 57/2025, Decree 58/2025) | Cap raised 20%→50% (fixed 2026-07-18); prior-year FMP average for the new surplus pricing formula not yet published — surplus rate stays at 671 VND/kWh pending EVN/NSMO publication | CURRENT — surplus-rate figure PENDING publication of the prior-year average | 2026-07-18 | 2027-01-18 |
| regimes | vn_regime_registry_2026.json | Repo-defined bundles over the above | — | CURRENT | 2026-07-18 | 2027-01-18 |
| deal_defaults | vn_deal_defaults_2026.json | Repo-defined deal seeds | 2026-07-26 (v2026.2): wrapped in the standard `{_meta, data}` envelope so `load_vietnam_data()` reads it; added `data.dppa_settlement` (adder + KPP loss, seeded from `integration/settlement.py`'s previously code-only constants). No numeric values changed. | CURRENT | 2026-08-01 | 2027-02-01 |
| market_prices | vn_market_prices_2026.json | Decree 243/2026 surplus purchase rate (proxy wholesale reference) | — | PROXY — no published hourly FMP/CFMP series ingested | 2026-08-13 | 2027-02-13 |

The `tariff` row was verified live on 2026-08-06: the EVN average retail price
of 2,204.0655 VND/kWh (ex-VAT) is still the standing figure. `Next review`
for the `tariff` row is 2026-11-06 — a 3-month horizon matching the minimum
adjustment interval Decision 07/2025/QD-TTg permits EVN; every other row is
the last-edit date of its active file plus 6 months.

Reviewed 2026-08-13:
- `financials`: the standard CIT rate remains 20% under Law No. 67/2025/QH15
  (enacted 2025-06-14, effective 2025-10-01), which additionally introduces 15%
  (micro-enterprise) and 17% (small-enterprise) rates — confirmed against the
  PwC and EY Vietnam corporate-tax summaries.
- `tech_costs`: no single named primary source governs market price surveys, so
  the row is marked `UNVERIFIED` pending a primary-source check; no new
  `Last verified` date was written (ASM-001).
- `emissions`: the latest published Vietnamese grid emission factor is 0.6592
  tCO2/MWh for 2023 (Official Letter 1726/BDKH-PTCBT), whereas the repo's
  `vn_emissions_2024.json` still carries 0.681; the row is marked `UNVERIFIED`
  pending reconciliation with the latest MONRE figure (ASM-001).
- `market_prices`: added as a PROXY — no published hourly FMP/CFMP series has
  been ingested; the wholesale reference is the Decree 243/2026 surplus
  purchase rate (671 VND/kWh).
