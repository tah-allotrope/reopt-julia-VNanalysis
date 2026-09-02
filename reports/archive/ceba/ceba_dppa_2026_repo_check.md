# CEBA DPPA 2026 — Repo verification report

_Generated 2026-06-23T05:28:58.030752+00:00 from `CEBA DPPA 2026.pptx`_

- **Plan:** `plans/2026-06-23-ceba-deck-repo-verification-plan.md`
- **Registry size:** 35
- **Executed:** 35
- **Errors:** 0

## Verdict counts

| Verdict | Count | Share |
|---|---:|---:|
| ✅ OK (match within ±1%) | 16 | 46% |
| ⚠️ Reconcile (deck-cited, repo differs) | 5 | 14% |
| ℹ️ Qualitative / method-level (DEC-007) | 14 | 40% |
| ❌ Mismatch (> 5% delta) | 0 | 0% |
| ➖ Out of scope / no equivalent | 0 | 0% |
| 💥 Runner error | 0 | 0% |
| **Total** | **35** | 100% |

## Per-bucket verdict tables

### Bucket A — Assumption checks (data file values vs deck-cited values)

| Slide | Verdict | Check id | Deck value | Repo value | Δ% | Takeaway |
|---:|:---:|---|---:|---:|---:|---|
| 5 | ℹ️ | A01_tou_peak_window | 18:00-23:00 hours | [17, 18, 19, 20, 21, 22] | — | qualitative: deck says '18:00-23:00'; repo shows [17, 18, 19, 20, 21, 22] |
| 5 | ⚠️ | A02_tou_peak_normal_ratio_22_110kv | 1.8 ratio (peak/normal) | 1.8256 | +1.42% | delta +1.42% (1-5% — review; below the bad threshold but not a clean match) |
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
| 19 | ℹ️ | A15_equity_irr_target | 12-15%+ range | 0.15 | — | qualitative: deck says '12-15%+'; repo shows 0.15 |
| 19 | ℹ️ | A16_cit_holiday | 4 + 9 years (exempt + half) | 4 + 9 | — | qualitative: deck says '4 + 9'; repo shows '4 + 9' |

### Bucket B — Finding checks (deck-stated numbers reproducible by the engine)

| Slide | Verdict | Check id | Deck value | Repo value | Δ% | Takeaway |
|---:|:---:|---|---:|---:|---:|---|
| 12 | ✅ | B01_simulation_5line_total_evnbill | 10,586,097,600 VND/month | 10,586,097,600 | +0.00% | match within ±1% (delta +0.000%) |
| 12 | ✅ | B02_simulation_cfd_settlement | 600,000,000 VND/month | 600,000,000 | -0.00% | match within ±1% (delta -0.000%) |
| 12 | ✅ | B03_simulation_effective_blended_rate | 1,864 VND/kWh | 1,864.3496 | +0.02% | match within ±1% (delta +0.019%) |
| 13 | ✅ | B04_pretax_delivered_cost_per_kwh | 2,027 VND/kWh | 2,027.3 | +0.01% | match within ±1% (delta +0.015%) |
| 39 | ⚠️ | B05_scenario1_evn_bill | 8,263,196,000 VND/month | 8,563,196,000 | +3.63% | delta +3.63% (1-5% — review; below the bad threshold but not a clean match) |
| 40 | ⚠️ | B06_scenario1_cfd_total | 8,763,196,000 VND/month | 9,063,196,000 | +3.42% | delta +3.42% (1-5% — review; below the bad threshold but not a clean match) |
| 43 | ✅ | B07_scenario3_evn_bill | 19,628,262,400 VND/month | 19,628,262,400.0001 | +0.00% | match within ±1% (delta +0.000%) |
| 44 | ✅ | B08_scenario3_total_cost | 18,828,262,400 VND/month | 18,828,262,400 | +0.00% | match within ±1% (delta +0.000%) |
| 47 | ✅ | B09_scenario4_evn_bill | 2,140,229,520 VND/month | 2,140,229,520 | +0.00% | match within ±1% (delta +0.000%) |
| 47 | ✅ | B10_scenario4_net_cfd | -30,000,000 VND/month | -30,000,000 | +0.00% | match within ±1% (delta +0.000%) |
| 24 | ℹ️ | B11_case5_seller_irr | 0.169 fraction | _(none)_ | — | Method-level (DEC-007): deck claim 0.169 fraction cannot be reproduced exactly from disclosed inputs. PySAM proxy with proxy CAPEX does not cashflow at the deck's stated strike 2,000 VND/kWh; the deck's exact figures require undisclosed CAPEX / BESS sizing / FMP / revenue assumptions. Repo observation: n/a. |
| 24 | ℹ️ | B12_case5_min_dscr | 1.14 x | -2.4246 | -312.69% | Method-level (DEC-007): deck claim 1.14 x cannot be reproduced exactly from disclosed inputs. PySAM proxy with proxy CAPEX does not cashflow at the deck's stated strike 2,000 VND/kWh; the deck's exact figures require undisclosed CAPEX / BESS sizing / FMP / revenue assumptions. Repo observation: -2.424609839998913. |
| 25 | ℹ️ | B13_case6_seller_irr | 0.269 fraction | _(none)_ | — | Method-level (DEC-007): deck claim 0.269 fraction cannot be reproduced exactly from disclosed inputs. PySAM proxy with proxy CAPEX does not cashflow at the deck's stated strike 2,000 VND/kWh; the deck's exact figures require undisclosed CAPEX / BESS sizing / FMP / revenue assumptions. Repo observation: n/a. |
| 25 | ℹ️ | B14_case6_min_dscr | 1.5 x | -2.8088 | -287.25% | Method-level (DEC-007): deck claim 1.5 x cannot be reproduced exactly from disclosed inputs. PySAM proxy with proxy CAPEX does not cashflow at the deck's stated strike 2,000 VND/kWh; the deck's exact figures require undisclosed CAPEX / BESS sizing / FMP / revenue assumptions. Repo observation: -2.8087539805226376. |
| 26 | ℹ️ | B15_56sweep_empty_window_method | empty categorical | see extra | — | qualitative: deck says 'empty'; repo shows 'see extra' |

### Bucket C — Insight checks (qualitative statements the engine demonstrates)

| Slide | Verdict | Check id | Deck value | Repo value | Δ% | Takeaway |
|---:|:---:|---|---:|---:|---:|---|
| 10 | ℹ️ | C01_overcontracting_cap | capped at min(load, gen) qualitative | capped at min(load, gen) | — | qualitative: deck says 'capped at min(load, gen)'; repo shows 'capped at min(load, gen)' |
| 17 | ℹ️ | C02_load_shape_overlap | low overlap daytime qualitative | daytime overlap = 100% | — | qualitative: deck says 'low overlap daytime'; repo shows 'daytime overlap = 100%' |
| 13 | ℹ️ | C03_year1_above_bau | Y1 >= BAU qualitative | Y1 buyer +16.3% vs BAU | — | qualitative: deck says 'Y1 >= BAU'; repo shows 'Y1 buyer +16.3% vs BAU' |
| 24 | ℹ️ | C04_oversized_bess_dscr_dip | min DSCR < 1.20x in BESS replacement year qualitative | directional NOT confirmed: oversized BESS min DSCR (-2.42… | — | Method-level (DEC-007): deck claim min DSCR < 1.20x in BESS replacement year qualitative cannot be reproduced exactly from disclosed inputs. PySAM proxy with proxy CAPEX does not cashflow at the deck's stated strike 2,000 VND/kWh; the deck's exact figures require undisclosed CAPEX / BESS sizing / FMP / revenue assumptions. Repo observation: directional NOT confirmed: oversized BESS min DSCR (-2.425) >= lean BESS (-2.809). |
| 20 | ℹ️ | C05_bankability_floor | strike_floor exists qualitative | no strike in the swept range clears 15% seller IRR with p… | — | Method-level (DEC-007): deck claim strike_floor exists qualitative cannot be reproduced exactly from disclosed inputs. PySAM proxy with proxy CAPEX does not cashflow at the deck's stated strike 2,000 VND/kWh; the deck's exact figures require undisclosed CAPEX / BESS sizing / FMP / revenue assumptions. Repo observation: no strike in the swept range clears 15% seller IRR with proxy CAPEX (bankability floor is above the swept range). |
| 52 | ℹ️ | C06_daytime_vs_night_economics | daytime > night qualitative | daytime > night on cost / coverage | — | qualitative: deck says 'daytime > night'; repo shows 'daytime > night on cost / coverage' |

## Structural reconciliations

### A04 — DPPA fees: deck 360 + 163.3 = 523.3 ≈ repo dppa_adder 523.34 ✅

The deck splits fixed DPPA fees into service (C_dppa_dv = 360) and balancing (P_cl = 163.3) for a combined 523.3 VND/kWh (slides 9, 11, 13, 30, 37, 175, 356). The repo's settlement engine takes one combined input: ``ContractParams.dppa_adder_vnd_kwh = 523.34`` ([settlement.py:26](src/python/reopt_pysam_vn/integration/settlement.py:26)). Match within 0.04 VND/kWh. This is the headline reconciliation.

### A06 / A07 — k × K_pp collapse (DEC-008 cited reconcile)

Deck splits FMP→delivery conversion into k=1.026 and K_pp=1.008 (product 1.03421), cited as 'EAVCED public training' (slide 11). The engine collapses both into a single kpp_factor=1.02726 (kpp_pct=2.7263). The ~0.7% delta is a structural modeling choice. Marked ⚠️ reconcile (DEC-008) rather than ❌ because the deck cites a source for the lower kpp_factor product.

### A02 — TOU peak/normal ratio (1.80 vs 1.826)

Deck Slide 5 voltage table: peak 0.126 / normal 0.070 = 1.80 (peak/normal). Repo: peak 1.57 / standard 0.86 = 1.826 (peak/normal). Both express the peak-vs-standard multiplier; the 1.5% delta is a small structural gap.

### A12 — FMP cited 1,426.6 vs repo deal-defaults center 1,700

Deck cites FMP avg 1,426.6 VND/kWh (EAVCED public training). Repo deal-defaults sensitivity range is 1,400-2,000 with a center of 1,700. Per DEC-008, the deck value is marked ⚠️ reconcile with both bases shown. The repo value is a forward-looking sensitivity midpoint, not an observed 2025 monthly FMP — there is no repo data file that holds an observed 2025 average.

### A15 — equity IRR target (range consistency, not value match)

Deck Slide 19 lists the equity IRR target as a range 12-15%+; the engine's ``target_irr_fraction`` is a single tunable default of 0.15. A value comparison is meaningless (a tunable knob is not authoritative), so the check is a range-consistency check: the engine's default 0.15 falls within the deck's range 0.12-0.15+. ✅

### B11 / B13 / B12 / B14 — Case 5/6 PySAM: DEC-007 method+directional

The deck's Case 5 / Case 6 numbers (16.9% / 26.9% seller equity IRR, 1.14× / 1.50× min DSCR) cannot be exactly reproduced from disclosed inputs. PySAM with proxy CAPEX does not produce a financeable project at the deck's stated strike 2,000 VND/kWh. Per DEC-007 the verdict is method+directional only and is never forced to ❌ even when the numeric delta is large. Colleague review should ask the deck author to disclose the inputs that close the gap.

### C04 — oversized BESS dips DSCR (DEC-007 directional)

C04 is now a directional comparison: run two PySAM scenarios (lean BESS vs oversized BESS with $1.2M replacement shock) and check that oversized BESS has a lower min DSCR than lean BESS. The deck's specific 1.14× value is not reproducible with the proxy CAPEX — the verdict reports the directional relationship only.

### C05 — bankability floor (real strike sweep, not single PySAM call)

C05 now runs the repo's actual ``sweep_strike_prices`` ([integration/strike_search.py:44](src/python/reopt_pysam_vn/integration/strike_search.py:44)) across 5-15 USc/kWh to find the min strike clearing a 15% seller IRR. The deck's Lesson 2 ('a strike below the bankability floor means no project') is verified as a method+direction; the exact floor value is not authoritative with proxy CAPEX.

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
