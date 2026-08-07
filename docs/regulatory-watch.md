# Regulatory Watch

Tracks which regulation governs each `data/vietnam/*.json` file and whether the
active file is current. Whenever a `research/` brief lands documenting a
regulatory change, add or update a row here in the same commit. A row whose
Status is `STALE` blocks new client-facing analysis that relies on that file
until it is refreshed.

| Manifest key | Active file | Governing instrument(s) | Known supersession | Status | Last verified | Next review |
|---|---|---|---|---|---|---|
| tariff | vn_tariff_2025.json | Decision 963/QD-BCT (TOU, active), Decision 14/2025 (legacy), Decree 146/2025 (two-part trial) | — | CURRENT | 2026-08-06 | 2026-11-06 |
| tech_costs | vn_tech_costs_2025.json | Market price surveys | — | CURRENT | 2026-02-18 | 2026-08-18 |
| financials | vn_financial_defaults_2025.json | CIT law 20%, decrees on incentives | — | CURRENT | 2026-02-18 | 2026-08-18 |
| emissions | vn_emissions_2024.json | HUST/MONRE grid-factor study | Annual MONRE update expected | CURRENT | 2026-02-18 | 2026-08-18 |
| export_rules | vn_export_rules_2026_decree243.json | Decree 243/2026 (amends Decree 57/2025, Decree 58/2025) | Cap raised 20%→50% (fixed 2026-07-18); prior-year FMP average for the new surplus pricing formula not yet published — surplus rate stays at 671 VND/kWh pending EVN/NSMO publication | CURRENT — surplus-rate figure PENDING publication of the prior-year average | 2026-07-18 | 2027-01-18 |
| regimes | vn_regime_registry_2026.json | Repo-defined bundles over the above | — | CURRENT | 2026-07-18 | 2027-01-18 |
| deal_defaults | vn_deal_defaults_2026.json | Repo-defined deal seeds | 2026-07-26 (v2026.2): wrapped in the standard `{_meta, data}` envelope so `load_vietnam_data()` reads it; added `data.dppa_settlement` (adder + KPP loss, seeded from `integration/settlement.py`'s previously code-only constants). No numeric values changed. | CURRENT | 2026-08-01 | 2027-02-01 |

The `tariff` row was verified live on 2026-08-06: the EVN average retail price
of 2,204.0655 VND/kWh (ex-VAT) is still the standing figure. `Next review`
for the `tariff` row is 2026-11-06 — a 3-month horizon matching the minimum
adjustment interval Decision 07/2025/QD-TTg permits EVN; every other row is
the last-edit date of its active file plus 6 months.
