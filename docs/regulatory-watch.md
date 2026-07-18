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
| export_rules | vn_export_rules_decree57.json | Decree 57/2025, Decree 58/2025 | **Decree 243/2026 (eff. 2026-06-26): cap 20%→50%, BESS surplus tradable, new pricing formula — see research/2026-06-30_decree-243-2026-nd-cp.md** | **STALE — fixed by PHASE-02 of plans/2026-07-18-decree-243-currency-webapp-hardening-plan.md** |
| regimes | vn_regime_registry_2026.json | Repo-defined bundles over the above | — | CURRENT |
| deal_defaults | vn_deal_defaults_2026.json | Repo-defined deal seeds | — | CURRENT |
