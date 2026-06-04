# Research Brief: Samsung–TTC Vietnam DPPA (Duc Hue 2 Solar) — Deal Facts, Financial Triangulation, and Repo Modeling Map

**Date:** 2026-06-04
**Modes run:** domain, codebase
**Depth:** standard
**Invocation context:** Synthesize all available information on the Samsung–TTC DPPA announcement in Vietnam (early June 2026) and especially its financials; where deal-specific terms are undisclosed, triangulate best-estimate assumptions from the Vietnam DPPA market landscape; map disclosed/assumed parameters onto this repo's existing DPPA scenario/settlement inputs so the user can model the deal economics here.

---

## Synthesis

The deal is **real, narrow, and well-documented on the physical side but commercially opaque**. As of **June 1, 2026**, Samsung Electronics Vietnam Thai Nguyen (SEVT) became the first enterprise to take renewable power under Vietnam's **grid-connected DPPA** (Decree 57/2025), buying **~70 GWh/year of solar** from **TTC Duc Hue 2** (49 MWp / ~41.4 MWac ground-mount in Tay Ninh province, developer *TTC Duc Hue–Long An Power JSC*) [pv-magazine](https://www.pv-magazine.com/2026/06/03/vietnams-first-direct-power-purchase-agreement-enters-operation/) [theinvestor.vn](https://theinvestor.vn/samsung-thai-nguyen-ttc-solar-plant-become-first-participants-in-vietnams-direct-power-purchase-mechanism-d19220.html) [vneconomy](https://en.vneconomy.vn/samsung-electronics-vietnam-thai-nguyen-pioneers-direct-solar-power-purchase-via-dppa.htm). The two sites are ~1,500 km apart (buyer in the north, generator in the south), which is the definitional signature of a **grid-connected / financial (CfD) DPPA**, not a private-wire physical one — confirmed by the fact that Duc Hue 2 "joined Vietnam's competitive wholesale electricity market" on commercial operation (May 19, 2026) and sells its physical output to the spot market while settling a contract-for-differences with SEVT [theinvestor.vn](https://theinvestor.vn/samsung-thai-nguyen-ttc-solar-plant-become-first-participants-in-vietnams-direct-power-purchase-mechanism-d19220.html).

**No commercial terms are public.** Strike price, tenor, KPP/grid-usage fee, settlement-quantity rule, and excess-generation treatment are all undisclosed across every outlet checked (paywalled trade press included) — this is normal for Vietnamese DPPAs, where Decree 57 leaves the forward-contract price to bilateral negotiation [Norton Rose Fulbright](https://www.nortonrosefulbright.com/en/knowledge/publications/b7fae014/decree-57-2025-key-features-and-impact-on-direct-power-purchase-agreements-in-vietnam). The financials therefore must be **triangulated**: anchor the strike to the **Southern ground-mount solar ceiling (~1,012 VND/kWh, no storage)** which MOIT caps grid DPPA forward prices at [a-osherman/EVN ceilings](https://en.evn.com.vn/d6/news/MoIT-sets-ceiling-prices-for-solar-and-wind-projects-66-163-3288.aspx); benchmark the buyer's avoided cost against the **EVN production tariff** (base 2,204.0655 VND/kWh × standard-hour multiplier 0.85–0.86 ≈ ~1,873–1,895 VND/kWh, since solar delivers in standard TOU hours under Decision 963); and use a CFMP/FMP market-reference series for the CfD leg. See the Domain section for the full assumption set with confidence flags.

**This repo already has the exact workflow.** `integration/dppa_case_2.py` implements a synthetic/financial DPPA settlement engine — strike price, hourly CFMP/FMP market-reference series, matched-quantity rule, KPP factor, excess-generation exclusion, buyer settlement ledger, EVN benchmark, and a PySAM developer-side IRR/NPV bridge (Phases C–G, all tested). The Samsung–TTC deal maps onto it as a **new "saigon18-style fixed-sizing" case**: pin PV to the contracted 41.4 MWac / 70 GWh instead of letting REopt optimize size, set the buyer load to SEVT, anchor the strike to the Southern ceiling, and reuse the existing CFMP transfer series until a Duc Hue 2-specific FMP series is sourced. The GAP-05 regime toggle (`reopt/regime_impact.py`) can then stress the result across Decision 963 vs forward regimes in <1s.

**[NOTE] The single biggest assumption-quality risk is the strike price and the market-reference (CFMP) series** — both directly drive the buyer-premium and developer-IRR outputs, and both are currently best-estimates rather than disclosed/site-specific data. Treat every headline number produced from this deal as *directional* and label the strike + CFMP basis explicitly, exactly as the repo's Case 2 already does (`market_reference_price_type: cfmp|fmp|proxy_cfmp_or_fmp`).

---

## Domain

### Discovery
Strongest primary sources on the deal itself: **pv-magazine Global** (Jun 3, 2026), **TheInvestor.vn** (VAFIE), and **VnEconomy** — all carrying the same core facts with minor extra detail. Reccessary and TechTimes corroborate the "first grid-based DPPA / 70 GWh" framing but are paywalled on financials. For the regulatory/market landscape: **Norton Rose Fulbright** and **Baker McKenzie** on Decree 57/2025 settlement structure, **EVN/MOIT** decisions on tariffs and solar ceilings, and **Reccessary** on the two-component tariff double-charging risk.

### Verification — Disclosed facts (high confidence; multi-source)
| Parameter | Value | Sources |
|---|---|---|
| Buyer | Samsung Electronics Vietnam Thai Nguyen (SEVT), Yen Binh Industrial Park, Thai Nguyen (north) | pv-magazine, theinvestor, vneconomy |
| Generator / plant | TTC Duc Hue 2 solar, Tay Ninh province (south); developer TTC Duc Hue–Long An Power JSC | theinvestor, vneconomy |
| Capacity | **49 MWp DC / ~41.4 MWac** | vneconomy (explicit 41.4 MWac), theinvestor |
| Annual volume to buyer | **~70 GWh/year** (~17,000 households equiv.) | all sources |
| CO₂ avoided | ~46,000 t/year | all sources |
| Mechanism | Grid-connected DPPA via national grid under Decree 57/2025; generator joined VWEM/competitive wholesale market (COD May 19, 2026; DPPA live Jun 1, 2026) | theinvestor, Norton Rose |
| Settlement type | Financial / CfD (implied by north–south split + spot-market participation) | inference from theinvestor + Norton Rose |

### Verification — Undisclosed (must triangulate)
Strike/contract price, tenor, contracted-quantity profile, KPP/grid-usage & transmission fee, settlement-quantity rule, excess-generation treatment, total investment. **None disclosed in any checked source** (several behind paywalls) — consistent with Decree 57 leaving grid-DPPA forward price to bilateral negotiation [Norton Rose Fulbright](https://www.nortonrosefulbright.com/en/knowledge/publications/b7fae014/decree-57-2025-key-features-and-impact-on-direct-power-purchase-agreements-in-vietnam).

### Comparison — Best-estimate assumption set (label all as ASSUMPTION)
Derived numbers from disclosed facts:
- **AC capacity factor** = 70,000 MWh / (41.4 MW × 8,760 h) ≈ **19.3%**; DC specific yield ≈ 70,000 MWh / 49 MWp ≈ **1,429 kWh/kWp/yr** — plausible (slightly conservative) for southern Vietnam fixed-tilt. *Confidence: High (pure arithmetic on disclosed values).*
- **Strike price**: anchor to **Southern ground-mount no-storage ceiling ≈ 1,012 VND/kWh**, plausible negotiated band **~1,000–1,150 VND/kWh** (MOIT caps grid-DPPA forward price at the RE-type ceiling) [EVN ceilings](https://en.evn.com.vn/d6/news/MoIT-sets-ceiling-prices-for-solar-and-wind-projects-66-163-3288.aspx); repo's `vn_tariff_2025.json` already stores `ground_mounted_no_storage.range_min = 1012`. *Confidence: Medium.*
- **EVN avoided-cost benchmark for the buyer**: SEVT is a large factory (likely 110 kV / 220 kV). Solar delivers in **standard** TOU hours (06:00–17:30 under Decision 963), so the avoided rate ≈ base 2,204.0655 × standard multiplier (0.85 at >35–<220 kV, 0.86 at 22–110 kV) ≈ **~1,873–1,895 VND/kWh**, with a small peak-hour tail (17:30–18:00). *Confidence: Medium-High (tariff structure is in-repo and sourced).*
- **CFMP/FMP market-reference (CfD leg)**: no clean public 2025–26 CGM spot series found; EVN's pure generation cost ≈ **1,620 VND/kWh** and total supply cost ≈ **2,092 VND/kWh** (Jan-2024) bound it from above [A&O Shearman](https://www.aoshearman.com/en/insights/direct-ppas-a-new-opportunity-in-vietnam). Use repo's existing **saigon18 hourly `cfmp_vnd_per_mwh` transfer series** as proxy until a Duc Hue 2-specific FMP is sourced. *Confidence: Low (proxy, not site-specific).*
- **Illustrative annual figures** (strike 1,050 VND/kWh, 70 GWh): developer strike revenue ≈ **73.5 B VND/yr (~$2.78M at 26,400 VND/USD)**; buyer EVN-benchmark for same 70 GWh at ~1,885 VND/kWh ≈ **132 B VND/yr**; gross buyer saving on the contracted slice ≈ **~58 B VND/yr before grid-usage/CfD fees**. *Confidence: Low — purely illustrative; the repo should compute these hourly, not this back-of-envelope.*

### Synthesis
The physical deal is locked down; the commercial deal is a negotiation black box. The right move is **not** to guess a single strike but to run the repo's Case-2 engine across a **strike sweep bounded by the Southern ceiling (1,012) up to ~EVN avoided cost (~1,885)**, settling the CfD against the proxy CFMP series, and report the buyer-premium / developer-IRR surface — exactly the strike-sensitivity pattern Case 2 Phase E already produces. The two-component tariff (Decree 146 trial) is a real forward risk: it can "double-charge" capacity on DPPA volume and erode buyer savings [Reccessary](https://www.reccessary.com/en/insight/vietnam-dppa-two-part-electricity-tariff-mechanism) — the repo's `decree146_two_part_trial_2026` regime exists to stress exactly this.

### Confidence
**Medium** — physical facts are High (multi-source), but every financial output depends on undisclosed terms triangulated from ceilings/tariffs and a proxy spot series.

---

## Codebase

### Discovery
- **`src/python/reopt_pysam_vn/integration/dppa_case_2.py`** — the canonical synthetic/financial DPPA settlement engine (Phases A–G). Key surfaces (verified by grep):
  - `build_scenario_dppa_case_2()` (line ~501): REopt scenario; PV `max_kw = 80,000`, battery up to 30 MW / 120 MWh.
  - Settlement formulas (lines ~356–359): `buyer_evn_matched_payment = matched_kwh × market_ref_price × kpp`; `buyer_cfd = matched_kwh × (strike − market_ref)`; with `kpp≈1` the buyer effectively pays **strike × matched** — the synthetic-DPPA identity.
  - Settlement schema (line ~403): `market_reference_price_type ∈ {cfmp, fmp, proxy_cfmp_or_fmp}`, `strike_price_vnd_per_kwh`, hourly `market_reference_price_vnd_per_kwh_series`, `settlement_quantity_rule`.
  - Strike helpers (`_strike_vnd_per_kwh`, default discount fraction off weighted EVN tariff), PySAM developer bridge (REopt↔PySAM PV reconciliation, IRR/NPV), buyer benchmark + combined-decision artifacts.
- **`src/python/reopt_pysam_vn/reopt/regime_impact.py`** (GAP-05) — <1s regime comparison (Decision 963 vs Decision 14 vs forward presets incl. Decree 146 two-part trial).
- **`data/vietnam/vn_tariff_2025.json`** — base price 2,204.0655 VND/kWh, production multipliers by voltage, Decision 963 TOU windows, Decree 57 solar ceilings, FX 26,400 VND/USD, two-part tariff trial values.
- **GAP-01 `ingest_factory_load`** — ingests a real factory 8760 load (for the SEVT buyer profile).

### Verification
Surfaces confirmed by direct grep/read this session (not assumed): the settlement formulas, schema enums, scenario sizing bounds, and tariff values above are present in the current tree. Case 2 is fully tested (Phases C–G regression suites passed in prior sessions per `activeContext.md`).

### Comparison — which existing case to clone
| Repo case | Mechanism | Fit for Samsung–TTC |
|---|---|---|
| **Case 2 (ninhsim)** | Synthetic/financial DPPA, CfD, strike + CFMP + KPP, excess-gen rule | **Best fit** — same mechanism class as the grid-connected Samsung deal |
| Case 1 | Private-wire tariff-ceiling screen | Wrong mechanism (physical private line) |
| Case 3 | Realism-first PV+BESS bounded-opt | Partial; relevant only if modeling storage (deal has none) |
| GAP-05 regime toggle | <1s tariff regime delta, no solve | Use as the post-settlement stress layer |

### Synthesis — concrete input mapping
Build a new case (e.g. `dppa_samsung_ttc`) by cloning Case 2 with these overrides:
1. **PV sizing → fixed, not optimized**: set PV `min_kw = max_kw ≈ 41,400` (AC) — or constrain to hit ~70 GWh/yr — instead of `max_kw = 80,000`; **disable battery** (`max_kw = max_kwh = 0`). This mirrors the existing `saigon18 fixed-sizing` artifacts seen in the working tree.
2. **Buyer load → SEVT**: ingest SEVT's 8760 via GAP-01 `ingest_factory_load`, or use saigon18 as a stand-in factory profile (note SEVT total consumption ≫ 70 GWh; the matched/contracted slice is 70 GWh).
3. **Strike → Southern ceiling band**: seed `strike_price_vnd_per_kwh ≈ 1,012–1,150`, and run Phase-E strike sweep up to ~EVN avoided cost (~1,885) to bracket the buyer premium.
4. **Market reference → CFMP proxy**: reuse the saigon18 `cfmp_vnd_per_mwh` transfer series with `market_reference_price_type = proxy_cfmp_or_fmp`; flag as transferred/not site-specific (same caveat Case 2 Phase F records).
5. **Regime → Decision 963 default**; stress with `decree146_two_part_trial_2026` via GAP-05 to test two-component-tariff erosion of buyer savings.
6. **Location/resolution**: Duc Hue 2 is in the **South** (Tay Ninh) — use a southern solar resource/region for PySAM yield, not the buyer's northern location.

What's **missing / to source before bankable**: (a) actual strike & tenor (confidential), (b) a Duc Hue 2-specific hourly FMP/CFMP series, (c) the negotiated KPP/grid-usage fee and settlement-quantity rule, (d) SEVT's real 8760 load and connection voltage. Until then, outputs are directional and the strike/CFMP basis must be labeled.

### Confidence
**High** — the repo demonstrably already contains a tested engine whose data contract matches this deal's mechanism; only deal-specific inputs are missing.

---

## Sources
- [Vietnam's first direct power purchase agreement enters operation — pv magazine Global](https://www.pv-magazine.com/2026/06/03/vietnams-first-direct-power-purchase-agreement-enters-operation/) — trade press; core deal facts (capacity, 70 GWh, parties, dates).
- [Samsung Thai Nguyen, TTC solar plant become first participants in Vietnam's DPPA — TheInvestor.vn](https://theinvestor.vn/samsung-thai-nguyen-ttc-solar-plant-become-first-participants-in-vietnams-direct-power-purchase-mechanism-d19220.html) — VAFIE outlet; COD date, VWEM participation, developer name.
- [Samsung Electronics Vietnam Thai Nguyen pioneers direct solar via DPPA — VnEconomy](https://en.vneconomy.vn/samsung-electronics-vietnam-thai-nguyen-pioneers-direct-solar-power-purchase-via-dppa.htm) — explicit 49 MWp / 41.4 MWac.
- [Samsung signs Vietnam's first grid-based DPPA, buying 70GWh of solar — Reccessary](https://www.reccessary.com/en/news/vietnam-grid-based-dppa-samsung-electronics) — corroboration (financials paywalled).
- [Decree 57/2025 — Key Features and Impact on DPPAs — Norton Rose Fulbright](https://www.nortonrosefulbright.com/en/knowledge/publications/b7fae014/decree-57-2025-key-features-and-impact-on-direct-power-purchase-agreements-in-vietnam) — grid-connected three-contract CfD structure; price ceilings.
- [MoIT sets ceiling prices for solar and wind projects — EVN](https://en.evn.com.vn/d6/news/MoIT-sets-ceiling-prices-for-solar-and-wind-projects-66-163-3288.aspx) — solar ceiling tariff basis for strike anchor.
- [Direct PPAs – A new opportunity in Vietnam? — A&O Shearman](https://www.aoshearman.com/en/insights/direct-ppas-a-new-opportunity-in-vietnam) — CfD strike framing; EVN avg generation/supply cost (~1,620 / ~2,092 VND/kWh).
- [Vietnam's DPPA and the two-part electricity tariff mechanism — Reccessary](https://www.reccessary.com/en/insight/vietnam-dppa-two-part-electricity-tariff-mechanism) — two-component tariff double-charging risk (Decree 146 forward stress).
- [Investing in Renewable Energy: How Decree 57 Reshapes the Market — Vietnam Briefing](https://www.vietnam-briefing.com/news/vietnam-renewable-energy-decree-57.html/) — Decree 57 / Resolution 253 negotiated-price context.
- Repo (verified this session): `src/python/reopt_pysam_vn/integration/dppa_case_2.py`, `reopt/regime_impact.py`, `data/vietnam/vn_tariff_2025.json`.
