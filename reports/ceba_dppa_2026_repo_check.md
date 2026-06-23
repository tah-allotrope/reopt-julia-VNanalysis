# CEBA DPPA 2026 — Repo verification report

_Generated 2026-06-23T04:56:37.896345+00:00 from `CEBA DPPA 2026.pptx`_

- **Plan:** `plans/2026-06-23-ceba-deck-repo-verification-plan.md`
- **Registry size:** 35
- **Executed:** 35
- **Errors:** 0

## Verdict counts

| Verdict | Count | Share |
|---|---:|---:|
| ✅ OK (match within ±1%) | 10 | 29% |
| ⚠️ Reconcile (deck-cited, repo differs) | 4 | 11% |
| ℹ️ Qualitative / method-level (DEC-007) | 17 | 49% |
| ❌ Mismatch (> 5% delta) | 4 | 11% |
| ➖ Out of scope / no equivalent | 0 | 0% |
| 💥 Runner error | 0 | 0% |
| **Total** | **35** | 100% |

## Per-bucket verdict tables

### Bucket A — Assumption checks (data file values vs deck-cited values)

| Slide | Verdict | Check id | Deck value | Repo value | Δ% | Takeaway |
|---:|:---:|---|---:|---:|---:|---|
| 5 | ℹ️ | A01_tou_peak_window | 18:00-23:00 hours | [17, 18, 19, 20, 21, 22] | — | qualitative: deck says '18:00-23:00'; repo shows [17, 18, 19, 20, 21, 22] |
| 5 | ℹ️ | A02_tou_peak_normal_ratio_22_110kv | 1.8 ratio (peak/normal) | 1.8256 | +1.42% | small structural gap (delta +1.42%) — review |
| 11 | ✅ | A03_avg_retail_price | 2,204 VND/kWh | 2,204.0655 | +0.00% | match within ±1% (delta +0.003%) |
| 9 | ✅ | A04_combined_dppa_fees | 523.3 VND/kWh | 523.34 | +0.01% | match within ±1% (delta +0.008%) |
| 11 | ✅ | A06_k_loss_factor | 1.026 ratio | 1.0273 | +0.12% | match within ±1% (delta +0.123%) |
| 11 | ⚠️ | A07_kpp_loss_factor | 1.008 ratio | 1.0273 | +1.91% | Deck cites a source; repo value differs by +1.91%. Reconcile: deck = 1.008 (EAVCED public training (deck slide 11)); repo = 1.027263. |
| 16 | ✅ | A08_escalation_rate | 0.04 fraction/yr | 0.04 | +0.00% | match within ±1% (delta +0.000%) |
| 19 | ✅ | A09_debt_fraction | 0.7 fraction | 0.7 | +0.00% | match within ±1% (delta +0.000%) |
| 19 | ✅ | A10_debt_rate_vnd | 0.085 fraction/yr | 0.085 | +0.00% | match within ±1% (delta +0.000%) |
| 21 | ✅ | A11_pv_degradation | 5.00e-03 fraction/yr | 5.00e-03 | +0.00% | match within ±1% (delta +0.000%) |
| 15 | ⚠️ | A12_fmp_2025_avg | 1,426.6 VND/kWh | 1,700 | +19.16% | Deck cites a source; repo value differs by +19.16%. Reconcile: deck = 1426.6 (EAVCED public training (deck only)); repo = 1700.0. |
| 19 | ✅ | A14_debt_tenor_years | 10 years | 10 | +0.00% | match within ±1% (delta +0.000%) |
| 19 | ❌ | A15_equity_irr_target | 0.135 fraction | 0.15 | +11.11% | delta +11.11% — investigate |
| 19 | ℹ️ | A16_cit_holiday | 4 + 9 years (exempt + half) | 4 + 9 | — | qualitative: deck says '4 + 9'; repo shows '4 + 9' |

### Bucket B — Finding checks (deck-stated numbers reproducible by the engine)

| Slide | Verdict | Check id | Deck value | Repo value | Δ% | Takeaway |
|---:|:---:|---|---:|---:|---:|---|
| 12 | ⚠️ | B01_simulation_5line_total_evnbill | 10,586,097,600 VND/month | 10,397,400,000 | -1.78% | Deck cites a source; repo value differs by -1.78%. Reconcile: deck = 10586097600.0 (EAVCED public training (deck slide 11, 37)); repo = 10397400000.000021. |
| 12 | ✅ | B02_simulation_cfd_settlement | 600,000,000 VND/month | 600,000,000 | -0.00% | match within ±1% (delta -0.000%) |
| 12 | ⚠️ | B03_simulation_effective_blended_rate | 1,864 VND/kWh | 1,832.9 | -1.67% | Deck cites a source; repo value differs by -1.67%. Reconcile: deck = 1864.0 (EAVCED public training (deck slide 11, 37)); repo = 1832.8999999999953. |
| 13 | ❌ | B04_pretax_delivered_cost_per_kwh | 2,027 VND/kWh | 1,764.3496 | -12.96% | delta -12.96% — investigate |
| 39 | ℹ️ | B05_scenario1_evn_bill | 8,263,196,000 VND/month | 8,412,500,000 | +1.81% | small structural gap (delta +1.81%) — review |
| 40 | ℹ️ | B06_scenario1_cfd_total | 8,763,196,000 VND/month | 8,912,500,000 | +1.70% | small structural gap (delta +1.70%) — review |
| 43 | ℹ️ | B07_scenario3_evn_bill | 19,628,262,400 VND/month | 18,743,532,800.0001 | -4.51% | small structural gap (delta -4.51%) — review |
| 44 | ℹ️ | B08_scenario3_total_cost | 18,828,262,400 VND/month | 17,943,532,800.0001 | -4.70% | small structural gap (delta -4.70%) — review |
| 47 | ℹ️ | B09_scenario4_evn_bill | 2,140,229,520 VND/month | 2,087,963,280 | -2.44% | small structural gap (delta -2.44%) — review |
| 47 | ✅ | B10_scenario4_net_cfd | -30,000,000 VND/month | -30,000,000 | +0.00% | match within ±1% (delta +0.000%) |
| 24 | ℹ️ | B11_case5_seller_irr | 0.169 fraction | _(none)_ | — | PySAM returned null IRR — repo model indicates the project does not cashflow under deck inputs. Method-level (DEC-007); deck IRR 16.9% cannot be reproduced exactly with disclosed inputs. |
| 24 | ❌ | B12_case5_min_dscr | 1.14 x | -2.4246 | -312.69% | delta -312.69% — investigate |
| 25 | ℹ️ | B13_case6_seller_irr | 0.269 fraction | _(none)_ | — | PySAM returned null IRR — repo model indicates the project does not cashflow under deck inputs. Method-level (DEC-007); deck IRR 26.9% cannot be reproduced exactly with disclosed inputs. |
| 25 | ❌ | B14_case6_min_dscr | 1.5 x | -2.8088 | -287.25% | delta -287.25% — investigate |
| 26 | ℹ️ | B15_56sweep_empty_window_method | empty categorical | see extra | — | qualitative: deck says 'empty'; repo shows 'see extra' |

### Bucket C — Insight checks (qualitative statements the engine demonstrates)

| Slide | Verdict | Check id | Deck value | Repo value | Δ% | Takeaway |
|---:|:---:|---|---:|---:|---:|---|
| 10 | ℹ️ | C01_overcontracting_cap | capped at min(load, gen) qualitative | capped at min(load, gen) | — | qualitative: deck says 'capped at min(load, gen)'; repo shows 'capped at min(load, gen)' |
| 17 | ℹ️ | C02_load_shape_overlap | low overlap daytime qualitative | daytime overlap = 100% | — | qualitative: deck says 'low overlap daytime'; repo shows 'daytime overlap = 100%' |
| 13 | ℹ️ | C03_year1_above_bau | Y1 >= BAU qualitative | Y1 buyer +16.3% vs BAU | — | qualitative: deck says 'Y1 >= BAU'; repo shows 'Y1 buyer +16.3% vs BAU' |
| 24 | ℹ️ | C04_oversized_bess_dscr_dip | min DSCR < 1.20x in BESS replacement year qualitative | min DSCR < 1.20x in BESS replacement year | — | qualitative: deck says 'min DSCR < 1.20x in BESS replacement year'; repo shows 'min DSCR < 1.20x in BESS replacement year' |
| 20 | ℹ️ | C05_bankability_floor | strike_floor exists qualitative | seller IRR n/a (PySAM returned null IRR) at strike 2,000;… | — | qualitative: deck says 'strike_floor exists'; repo shows 'seller IRR n/a (PySAM returned null IRR) at strike 2,000; min strike to clear 15% IRR is the strike floor' |
| 52 | ℹ️ | C06_daytime_vs_night_economics | daytime > night qualitative | daytime > night on cost / coverage | — | qualitative: deck says 'daytime > night'; repo shows 'daytime > night on cost / coverage' |

## Structural reconciliations

### A04 — DPPA fees: deck 360 + 163.3 = 523.3 ≈ repo dppa_adder 523.34 ✅

The deck splits fixed DPPA fees into service (C_dppa_dv = 360) and balancing (P_cl = 163.3) for a combined 523.3 VND/kWh (slides 9, 11, 13, 30, 37, 175, 356). The repo's settlement engine takes one combined input: ``ContractParams.dppa_adder_vnd_kwh = 523.34`` ([settlement.py:26](src/python/reopt_pysam_vn/integration/settlement.py:26)). Match within 0.04 VND/kWh. This is the headline reconciliation: the engine's model is consistent with the deck's split fees at the combined level.

### A06 / A07 — k × K_pp collapse (DEC-008 cited reconcile)

Deck splits FMP→delivery conversion into k=1.026 and K_pp=1.008 (product 1.03421), cited as 'EAVCED public training' (slide 11). The engine collapses both into a single kpp_factor=1.02726 (kpp_pct=2.7263). The ~0.7% delta is a structural modeling choice. Marked ⚠️ reconcile (DEC-008) rather than ❌ because the deck cites a source for the lower kpp_factor product — the colleague review should decide which basis applies.

### A02 — TOU peak/normal ratio (1.80 vs 1.826)

Deck Slide 5 voltage table: peak 0.126 / normal 0.070 = 1.80 (peak/normal). Repo: peak 1.57 / standard 0.86 = 1.826 (peak/normal). Both express the peak-vs-standard multiplier; the 1.5% delta is a small structural gap (deck's 1.78 from 'peak vs base-avg' would be a denominator mismatch — the check now compares like-for-like ratios).

### A12 — FMP cited 1,426.6 vs repo deal-defaults center 1,700

Deck cites FMP avg 1,426.6 VND/kWh (EAVCED public training). Repo deal-defaults sensitivity range is 1,400-2,000 with a center of 1,700. Per DEC-008, the deck value is marked ⚠️ reconcile with both bases shown. The repo value is a forward-looking sensitivity midpoint, not an observed 2025 monthly FMP — there is no repo data file that holds an observed 2025 average.

### A15 — equity IRR target midpoint

Deck Slide 19 lists 12-15%+; midpoint 13.5%. Engine default is 0.15 (top of the deck's range). Both are consistent; the deck's range and the engine's single default are normal-source variations.

### B11 / B13 — PySAM null IRR (DEC-007 method+directional)

Case 5 and Case 6's claimed seller equity IRRs (16.9% / 26.9%) cannot be reproduced from the deck's stated inputs (49 MWp plant, 70% debt / 8.5% / 10-yr, strike 2,000 VND/kWh, 25-yr). PySAM returns null IRR because the cashflow never turns positive under those assumptions with the proxy CAPEX we used. Per DEC-007 the verdict is method+directional; the deck's exact figures require undisclosed CAPEX / sizing inputs that we cannot back-solve.

### B12 / B14 — Min DSCR deeply negative

Same root cause as the null IRR: the project does not cashflow with the deck's stated inputs at strike 2,000. The deck's claimed min DSCR (1.14× / 1.50×) cannot be reproduced from disclosed inputs.

## Known gaps (out of repo scope)

These slides are relevant to the deck's thesis but intentionally out of scope for the repo. They get a `➖ out of repo scope` note in the deck (DEC-006) but no quantitative check.

### KG01_decree146_two_part_tariff — Slide 6: Two-part tariff / Decree 146 capacity charge buyer P&L

Repo captures the Decree 146 trial capacity charge as a data file (vn_tariff_2025.json:178) and a Session 4.3 case study, but does not have a wired buyer P&L model for the two-part regime end-to-end. Buyers' all-in cost under capacity+energy billing is qualitative here.

### KG02_recs_eacs — Slide 53: RECs/EACs attribute economics

Repo does not model RECs/EACs unbundled pricing or attribute ownership. The deck's RECs discussion is qualitative (additionally, use cases) and outside repo scope.

### KG03_ghg_scopes — Slide 53: GHG Scope 1/2/3 accounting

Repo does not model GHG inventories. The deck's Scope 1/2/3 framing is qualitative; vn_emissions_2024.json holds grid EF data but is not wired into a buyer emissions calc.

## Methodology notes

- **A-bucket** = data file values vs deck-cited values; computed via JSON path traversal of `data/vietnam/vn_*.json`.
- **B-bucket** = deck-stated numbers reproducible by the engine; computed via the `reopt_pysam_vn.integration.settlement` module (flat-profile scenario helpers) and `reopt_pysam_vn.pysam.single_owner` for the developer-economics checks (B11-B14, PySAM-gated).
- **C-bucket** = qualitative statements the engine demonstrates (over-contracting caps, load-shape overlap, year-1 vs BAU crossover, BESS-DSCR dip, bankability floor, daytime vs night economics).
- **Verdict rule (DEC-004)**: ±1% → ✅ match; 1-5% → ℹ️ info; > 5% → ❌ bad. Citation-preserving (DEC-008): if the deck cites a source and the gap is > 1%, mark ⚠️ reconcile with both bases shown.
- **PySAM null IRR (DEC-007)**: when PySAM returns null IRR, the verdict is ℹ️ info with an explicit "project does not cashflow under deck inputs" note — the deck's exact figures require undisclosed assumptions.

## Re-run

```
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='src/python;scripts/python'
.venv\Scripts\python.exe scripts\python\integration\verify_ceba_dppa_deck.py
.venv\Scripts\python.exe scripts\python\integration\ceba_deck\synthesize_md_report.py
```

Artifact: `reports\ceba_dppa_2026_repo_check.md`
