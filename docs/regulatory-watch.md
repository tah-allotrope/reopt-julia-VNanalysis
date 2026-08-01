# Regulatory Watch

Tracks which regulation governs each `data/vietnam/*.json` file and whether the
active file is current. Whenever a `research/` brief lands documenting a
regulatory change, add or update a row here in the same commit. A row whose
Status is `STALE` blocks new client-facing analysis that relies on that file
until it is refreshed.

| Manifest key | Active file | Governing instrument(s) | Known supersession | Status |
|---|---|---|---|---|
| tariff | vn_tariff_2025.json | Decision 963/QD-BCT (TOU, active), Decision 14/2025 (legacy), Decree 146/2025 (two-part trial) | — | CURRENT |
| tech_costs | vn_tech_costs_2025.json | Market price surveys | — | CURRENT |
| financials | vn_financial_defaults_2025.json | CIT law 20%, decrees on incentives | — | CURRENT |
| emissions | vn_emissions_2024.json | HUST/MONRE grid-factor study | Annual MONRE update expected | CURRENT |
| export_rules | vn_export_rules_2026_decree243.json | Decree 243/2026 (amends Decree 57/2025, Decree 58/2025) | Cap raised 20%→50% (fixed 2026-07-18); prior-year FMP average for the new surplus pricing formula not yet published — surplus rate stays at 671 VND/kWh pending EVN/NSMO publication | CURRENT — surplus-rate figure PENDING publication of the prior-year average |
| regimes | vn_regime_registry_2026.json | Repo-defined bundles over the above | — | CURRENT |
| deal_defaults | vn_deal_defaults_2026.json | Repo-defined deal seeds | 2026-07-26 (v2026.2): wrapped in the standard `{_meta, data}` envelope so `load_vietnam_data()` reads it; added `data.dppa_settlement` (adder + KPP loss, seeded from `integration/settlement.py`'s previously code-only constants). No numeric values changed. | CURRENT |
