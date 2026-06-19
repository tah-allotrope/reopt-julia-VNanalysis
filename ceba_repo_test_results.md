# CEBA Repo Test Results: Session 6.2 Claims vs. Repo Evidence

**Tested:** 2026-06-19  
**Slide review source:** `ceba_slide_review_report.md`  
**Repo artifacts tested:** `artifacts/reports/samsung_ttc/`, `src/python/reopt_pysam_vn/integration/dppa_samsung_ttc.py`, `scenarios/case_studies/samsung_ttc/samsung_ttc_deal_config.json`, `src/python/reopt_pysam_vn/pysam/config.py`, `src/python/reopt_pysam_vn/integration/assumptions.py`, and supporting data files.

---

## Verdict Summary

| # | Claim (from slide review) | Verdict | Repo Evidence |
|---|--------------------------|---------|---------------|
| 1 | Samsung deal: 49 MW solar, Duc Hue 2, Tay Ninh | PASS | `samsung_ttc_deal_config.json` capacity_mwp=49.0, province=Tay Ninh |
| 2 | Buyer: SEVT, Yen Binh IP, Thai Nguyen | PASS | `dppa_samsung_ttc.py` SAMSUNG_TTC_BUYER_LOCATION |
| 3 | Volume: ~70 GWh/yr, CO₂: ~46,000 t/yr | PASS | deal_config annual_solar_gwh=70.0, co2_avoided=46,000 |
| 4 | COD May 19 2026; DPPA live June 1 2026 | PASS | deal_config cod_date="2026-05-19", dppa_live_date="2026-06-01" |
| 5 | Grid-connected CfD DPPA under Decree 57/2025 | PASS | combined-decision mechanism="grid_connected_dppa_decree_57_2025", settlement="financial_cfd" |
| 6 | Strike anchor: 1,012 VND/kWh (Southern ceiling) | PASS | `SOUTHERN_GROUND_MOUNT_CEILING_VND_PER_KWH = 1012.0` in dppa_samsung_ttc.py; deal_config strike=1012 |
| 7 | Buyer saves ~25 B VND/yr at ceiling strike | PASS | combined-decision buyer_savings_vnd=25,204,368,047 (~25.2 B VND) |
| 8 | Buyer saves ~$0.95M/yr | PASS | combined-decision buyer_savings_usd=954,710 (~$0.95M) |
| 9 | DPPA grid-service adder: 523 VND/kWh | PASS | deal_config dppa_adder_vnd_per_kwh=523.34; confirmed in buyer-settlement |
| 10 | Two-part tariff lifts EVN bill ~18% | PASS | regime_stress decree146_two_part_trial_2026: delta_pct=17.91% |
| 11 | Developer sub-economic on contracted 70 GWh | PASS | All 5 sweep points: developer_passes=false, developer_npv_usd < 0 (range: -$80M to -$57M) |
| 12 | Developer NPV excludes merchant tail (conservative) | PASS | dppa_samsung_ttc.py: revenue_basis="contracted_70gwh_conservative"; rationale explicitly notes merchant tail exclusion |
| 13 | Developer IRR target: 15% | PASS | `assumptions.py` DEFAULT_TARGET_DEVELOPER_IRR_FRACTION=0.15; deal_config target_irr_fraction=0.15 |
| 14 | Developer capex: $750/kW | PASS | `SAMSUNG_TTC_INSTALLED_COST_USD_PER_KW = 750.0`; deal_config installed_cost_usd_per_kw=750.0 |
| 15 | 8760-hour simulation methodology | PASS | dppa_samsung_ttc.py builds synthetic 8760 load + solar profiles; settlement is hourly |
| 16 | KPP factor applied in settlement | PASS | buyer-settlement kpp_factor=1.027263 |
| 17 | Contract tenor: 20 years | PASS | deal_config tenor_years=20; combined-decision analysis_years=20 |
| 18 | Adder break-even at "~0.9×" the 523 VND/kWh adder | **FAIL** | Repo adder sensitivity shows break-even at ~1.69× (not 0.9×); see detail below |
| 19 | Cong's strike floor of 1,200 VND/kWh | **MISALIGNED** | Repo anchors Samsung deal at 1,012 VND/kWh; slide review correctly flags this inconsistency |
| 20 | Cong's strike ceiling of 2,200 VND/kWh | **MISALIGNED** | Repo uses 1,873 VND/kWh (EVN standard-hour avoided cost); slide review correctly flags this |
| 21 | "Window is empty": no scenario passes all gates | PARTIAL | Repo confirms no overlap for Samsung deal across 5 sweep points; but buyer DOES save at ceiling strike — Cong's zero-passing conclusion is based on a hypothetical factory, not the Samsung deal |
| 22 | DSCR ≥ 1.2× as a three-gate lender criterion | UNTESTABLE | Repo computes min_dscr via PySAM but does not use DSCR as a pass/fail gate; developer gate is IRR only |
| 23 | Buyer effective cost ~1,864 VND/kWh (Cong's 6,000 MWh/month example) | UNTESTABLE | This is Cong's hypothetical factory; repo shows 2,015 VND/kWh blended for Samsung's 1,000 GWh load |
| 24 | Debt assumption: 70% LTV, 8.5% VND rate, 10-yr tenor | PASS | `config.py` debt_fraction=0.70, debt_interest_rate_fraction=0.085, debt_tenor_years=10 |
| 25 | "Fix is structural": lower LTV, USD debt (~5%), longer tenor | SUPPORTED IN REVIEW ONLY | Slide review correctly identifies these levers; repo code stores the baseline but no structural-fix variant has been run |

---

## Detailed Findings

### PASS: Samsung Deal Facts (Claims 1–6)

The repo contains a complete, multi-artifact record of the Samsung SEVT × TTC Duc Hue 2 deal. Every publicly disclosed fact — capacity (49 MWp / 41.4 MWac), annual volume (70 GWh), CO₂ (46,000 t/yr), COD (2026-05-19), DPPA live date (2026-06-01), settlement mechanism (financial CfD), regulatory basis (Decree 57/2025) — is correctly encoded in `samsung_ttc_deal_config.json`, the `dppa_samsung_ttc.py` constants, and the four phase-report HTML files. The strike anchor of 1,012 VND/kWh (Southern ground-mount no-storage ceiling) is read directly from `vn_tariff_2025.json` and used as the base strike throughout the analysis.

### PASS: Buyer Saves ~25 B VND/yr, ~$0.95M (Claims 7–8)

From `2026-06-04_samsung-ttc_combined-decision.json`:
```
buyer_savings_vnd:     25,204,368,047  (~25.2 B VND/yr)
buyer_savings_usd:        954,710.91  (~$0.95M/yr)
```
The slide review's "~25 B VND" and "~$0.95M" figures are exact matches to the repo's computed output (at 26,400 VND/USD exchange rate, DPPA adder 523.34 VND/kWh, KPP factor 1.027263). Methodology: matched-quantity CfD settlement against a proxy CFMP series, calibrated 70 GWh PVWatts solar profile.

### PASS: 523 VND/kWh Grid-Service Adder (Claim 9)

The adder is encoded as 523.34 VND/kWh in `deal_config` and confirmed in the buyer-settlement artifact (`dppa_adder_vnd_per_kwh: 523.34`). The settlement isolates the DPPA adder charge at ~36.6 B VND/yr (= 523.34 × 70 GWh), which is larger than the CfD payment in magnitude, validating the slide review's claim that it is the "dominant lever on buyer cost."

### PASS: Two-Part Tariff ~18% EVN Bill Lift (Claim 10)

From `2026-06-04_samsung-ttc_regime-stress.json` (Decree 146 two-part trial):
```
annual_bill_delta_vnd:  364,821,341,598  (~+365 B VND)
delta_pct:                         17.91%  (≈ "~18%")
baseline_bill_gvnd:          2,036.73 B VND
```
The slide review's "+18% / +365 B VND" claim is confirmed precisely. The regime stress test also correctly flags the double-charging risk: "a capacity charge that can also double-charge DPPA volume."

### PASS: Developer Sub-Economic, IRR Target 15% (Claims 11–14)

The Samsung-TTC strike sweep (`2026-06-04_samsung-ttc_strike-sensitivity.json`) runs 5 sweep fractions (0.0 to 1.0) from the 1,012 VND/kWh floor to the 1,873 VND/kWh EVN-avoided-cost ceiling. At every point, `developer_passes=false`. Developer NPV ranges from -$79.7M (at 1,012 VND/kWh) to -$57.3M (at 1,873 VND/kWh) — consistently sub-economic under the 15% IRR threshold and $750/kW capex on the conservative 70 GWh revenue basis. The conservative basis (excluding merchant output above 70 GWh) is explicitly documented in the code rationale and confirmed in the combined-decision rationale text.

### FAIL: Adder Break-Even at "~0.9×" (Claim 18)

**This is the most significant quantitative inconsistency between the slide review's characterization and what the repo actually computes.**

The combined-decision rationale text (hardcoded in `dppa_samsung_ttc.py` line 1016–1017) states:  
> "buyer flips to a premium near ~0.9× the inherited 523 VND/kWh adder"

However, the adder sensitivity table in the same artifact shows:

| Adder Multiplier | Adder (VND/kWh) | Buyer Delta (VND) | Buyer Saves? |
|---|---|---|---|
| 0.0 | 0.0 | -61,838,168,047 | YES |
| 0.5 | 261.67 | -43,521,268,047 | YES |
| 1.0 | 523.34 | -25,204,368,047 | YES |
| 1.5 | 785.01 | -6,887,468,047 | YES |
| 2.0 | 1,046.68 | +11,429,431,952 | NO |

Interpolating between 1.5× and 2.0×: break-even ≈ **1.69× the base adder** (≈ 884 VND/kWh), not ~0.9×. The "0.9×" text is a static string in the code — it was not computed from the adder sensitivity table and does not reflect the actual sensitivity output.

**Implication for the slide review:** The claim that "the buyer flips to a premium near ~0.9× that adder" (attributed to Allotrope's internal DPPA insights analysis) is inconsistent with the repo's computed adder sensitivity. The repo model shows the buyer has considerably more headroom than the hardcoded text suggests: the buyer can absorb an adder increase of ~0.69× (from 523 to 884 VND/kWh) before breaking even. The break-even adder multiplier is ~1.69×, not ~0.9×.

**Action:** Either the hardcoded rationale text in `dppa_samsung_ttc.py` should be updated to reflect the computed break-even (~1.7×), or the `adder_sensitivity` table should be used to compute the break-even dynamically and report it precisely.

### MISALIGNED: Cong's Strike Range 1,200–2,200 VND/kWh (Claims 19–20)

The slide review correctly flags this: Cong's hypothetical factory case sweeps 1,200–2,200 VND/kWh, while the repo anchors the Samsung deal at 1,012–1,873 VND/kWh. The repo's bounds are more appropriate:
- **Floor (1,012):** the Decree 57 ceiling generation tariff for Southern ground-mount solar (no storage), which is the regulatory cap on grid-DPPA strike prices and the confirmed market anchor for the first live deal
- **Ceiling (1,873):** EVN standard-hour avoided cost at the SEVT voltage level — the theoretical upper bound where the DPPA ceases to offer any buyer benefit

The slide review's recommendation to recalibrate Cong's floor from 1,200 to 1,012 VND/kWh is validated by the repo.

### PARTIAL: "Window is Empty" (Claim 21)

The slide review describes two distinct "window is empty" findings that need to be separated:

1. **Cong's slide conclusion** (Slide 24): "zero of 56 strike/volume scenarios pass all three gates" for a *hypothetical industrial park buyer* — this is not testable from the repo since the repo does not contain Cong's hypothetical case study; the "56 scenarios" do not appear anywhere in the codebase.

2. **Repo's Samsung finding**: No overlap exists at any of the 5 sweep points (`overlap_found: false`). The developer is sub-economic across the entire band. The buyer passes (saves money) at the two lowest strike points (1,012 and 1,227 VND/kWh) but not at higher strikes.

The slide review notes (correctly, per the repo) that Cong's "zero scenarios pass all three gates" conclusion does not align with the Samsung finding where **the buyer does save at the ceiling strike** — this is the nuance the slide review says is "entirely missing" from Cong's deck. The repo confirms it: the window is not empty from the buyer's perspective at the ceiling strike; it is empty only from the lender/developer gate perspective.

### UNTESTABLE: DSCR ≥ 1.2× as Lender Gate (Claim 22)

The slide's three-gate framework (buyer premium/saving, developer IRR, DSCR ≥ 1.2×) implies DSCR is a separate explicit gate. The repo computes `min_dscr` as a PySAM output, but it is **not used as a pass/fail threshold** in the developer gate logic. The `developer_passes` flag in the strike sweep is determined solely by `dev_irr >= target_irr` (15%). DSCR values appear in the cashflow output artifacts but are null for the Samsung case (PySAM Single Owner IRR also returned null due to sub-economic inputs not converging).

The DSCR ≥ 1.2× criterion as a *separate explicit gate* is not modeled. Whether this is a meaningful gap depends on whether DSCR and IRR are effectively co-linear under the repo's financing assumptions (70% LTV, 8.5% VND, 10-yr tenor, 15% IRR target). At sub-economic IRR, DSCR constraints are almost certainly also violated — but this is not quantified.

### UNTESTABLE: Buyer Effective Cost ~1,864 VND/kWh (Claim 23)

Cong's "~1,864 VND/kWh effective cost" figure is from his hypothetical factory case study (6,000 MWh/month buyer at an unspecified factory). This factory is not in the repo. The closest repo figure is the Samsung deal buyer blended cost of 2,015 VND/kWh on 1,000 GWh total load (or ~1,552 VND/kWh effective cost on just the matched 70 GWh contracted slice). These figures are not directly comparable since they reflect different buyer loads and DPPA structures.

---

## Structural Observations

### Debt Assumptions are Repo-Verified (Claim 24)

`config.py` `build_vietnam_finance_defaults()` sets:
- Debt fraction: 70%
- Debt interest rate: 8.5% (VND-denominated, matching the slide review's "~8.5% VND" reference)
- Debt tenor: 10 years

The slide review's proposed structural fix — "USD-denominated debt (~5% vs. ~8.5% VND)" — is directionally correct as an improvement lever. The baseline 8.5% rate in the repo matches the slide review's stated baseline exactly. No USD-debt variant has been modeled in the repo.

### Quality Labeling is Consistent Throughout

The repo consistently marks all Samsung-TTC outputs as `"basis": "directional"` with explicit caveats about undisclosed commercial terms (strike, tenor, KPP, CFMP proxy). This matches the slide review's guidance on directional vs. bankable verdicts. Parity test `test_samsung_parity_is_bit_exact` locks the generalized `run_offsite_dppa` to reproduce the bespoke builder with zero numeric drift.

### What the Repo Cannot Test

The following slide review claims are outside the repo's scope entirely:
- Cong's hypothetical "56 strike/volume scenarios" (Slides 21–24) — not modeled in this repo
- CBAM/EU Scope 2 documentation requirements (Slide review section 3.5 / recommendation 5.7)
- Corporate DPPA pipeline context (Heineken, Apple supply chain, KN Holdings) — referenced in research brief but not modeled
- Resolution 253 price-cap removal for physical DPPA — regulatory context only
- Phase 3 of the two-part tariff (July 2026) hitting actual bills — the regime stress models the financial impact but not the billing mechanics

---

## Summary for CEBA Workshop Use

**Repo-validated claims the slides can cite with confidence:**
- Samsung deal facts (all core parameters)
- 1,012 VND/kWh strike anchor as the market-appropriate floor
- Buyer saves ~25 B VND/yr (~$0.95M) at the ceiling strike
- 523 VND/kWh adder is the dominant buyer cost lever
- Two-part tariff (Decree 146) lifts EVN bill by ~18% (~365 B VND)
- Developer is sub-economic on contracted slice alone; merchant tail is the missing piece
- No buyer–developer overlap exists in the full strike sweep

**Repo-contradicted claim requiring correction:**
- The hardcoded rationale "buyer flips to premium near ~0.9× the adder" is **not supported by the computed adder sensitivity**. The actual break-even from the repo model is at approximately **1.69× the adder** (~884 VND/kWh). If the ~0.9× figure comes from the separate DPPA insights tool (a different model), the two tools are giving materially different answers on the same question and that divergence should be investigated before citing either number in the workshop.

**Repo-misaligned items the slide review correctly flags:**
- Cong's 1,200 VND/kWh strike floor (should be 1,012)
- Cong's 2,200 VND/kWh strike ceiling (should be ~1,873 EVN avoided cost)
- Cong's "zero buyer scenarios pass" conclusion differs from the repo finding that the buyer saves at the ceiling strike

**Items untestable from repo alone:**
- Cong's 56-scenario sweep (hypothetical factory, not in repo)
- DSCR ≥ 1.2× as an explicit gate (not implemented as a pass/fail criterion)
- Buyer effective cost ~1,864 VND/kWh (different buyer/scenario)
