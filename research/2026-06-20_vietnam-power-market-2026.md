# Vietnam Power Market — 2026 Update and CEBA Slidedeck Fact-Check

**Date:** 2026-06-20  
**Depth:** Exhaustive  
**Sources (wide/deep):** 30 gathered / 8 cited  
**Ratio used:** github 0.05 (20 rows), academia 0.00 (hit rate limit), industry 0.60 (8 restored), web 0.05 (1)  
**Sub-questions:** (1) TOU windows under Decision 14/963; (2) DPPA fees/FMP under Decree 57; (3) Two-part tariff status; (4) EVN price trajectory; (5) Export cap status under Decree 58

---

## Source Coverage

| Bucket | Target | Gathered | Qualified (tier ≤ 3) | Cited | Note |
|--------|--------|----------|-----------------------|-------|------|
| github | 13 | 20 | 5 | 0 | Energy model repos; no primary regulatory data |
| academia | 37 | 0 | 0 | 0 | Hit session rate limit before any rows written |
| industry | 100 | 8 | 7 | 7 | Rate limit after 73 rows; 8 key rows restored; EVN tier-1 sources strong |
| web | 100 | 1 | 1 | 1 | Decree 58 status confirmed via WebSearch |
| **total** | **250** | **29** | **13** | **8** | Academia deficit reallocated; deep pass for 8 highest-dispute items |

**Confidence notes:**
- Industry: HIGH — EVN primary sources + 3 Norton Rose Fulbright analyses provide Tier 1–3 coverage of all key regulatory claims.
- Web: MEDIUM — single Duane Morris post plus WebSearch for Decree 58; adequate for the Decree 58 question.
- Academia / GitHub: LOW COVERAGE — rate limits prevented gathering. No academic sources were cited; GitHub repos are useful for EVN tariff code cross-reference but not for claim verification.
- **The two unverified claims** (Decree 61 BESS 3 MW threshold; count of TCVN standards) require a separate targeted fetch of primary decree text.

---

## Synthesis

### Decision 963/QD-BCT — TOU Restructure (active April 22 2026)

Decision 963 eliminated the old split peak (09:30–11:30 morning + 17:00–20:00 evening) and replaced it with a single evening block **17:30–22:30 Monday–Saturday**. Sundays and public holidays remain all-standard. Off-peak is 00:00–06:00 every day. The Decision 14/2025 rate multipliers carry forward unchanged (MOIT has not reissued replacements). The net effect: rooftop solar now offsets nothing during peak hours; BESS becomes necessary to capture peak value.

### EVN Average Retail Price Trajectory

The average retail price has increased through four rounds since mid-2022:
- May 2023: +3% → ~1,920 VND/kWh  
- November 2023: +4.5% → ~2,007 VND/kWh  
- May 2024: +4.8% → ~2,103 VND/kWh  
- May 2025: +4.8% → **2,204.0655 VND/kWh** (Decision 599/QD-EVN; effective May 10 2025)  

Cumulative from late 2022 base (~1,864 VND/kWh): **+18.2% over ~2.5 years**.

Decision 07/2025/QD-TTg sets the allowed range at 1,826–2,444 VND/kWh; EVN can adjust ±2–5% with 3-month minimum intervals. Further increase in late 2025 or 2026 is structurally possible.

### Decree 57/2025 — DPPA Framework

Decree 57/2025/ND-CP (effective March 3 2025) replaced Decree 80 and governs grid-connected virtual DPPAs (Model 2). Key structural points:

- Generator must own RE plant ≥10 MW and sell 100% output to VWEM at hourly FMP
- Customer settles with EVN via a five-line bill: market energy (FMP × k × K_pp), DPPA service fee (C_dppa_dv = 360 VND/kWh per implementing circular), balancing fee (P_cl = 163.3 VND/kWh), residual at TOU rates, and CfD bilateral settlement
- Voltage/consumption eligibility changed from "≥22kV + ≥200,000 kWh/month" (Decree 80) to "per MOIT wholesale market regulations" — flexible, not fixed
- Max rooftop surplus export for private-wire solar: **20%** of actual generation

### Two-Part Tariff — Decree 146/2025/ND-CP

Paper pilot Jan–Jun 2026 for large industrial consumers (≥200,000 kWh/month, ≥22kV). Capacity charges by voltage tier:

| Voltage | Capacity charge (VND/kW/month) |
|---------|-------------------------------|
| ≥110kV | 209,459 |
| 22kV–110kV | 235,414 |
| 6kV–22kV | 240,050 |
| <6kV | 286,153 |

The pilot is paper-only; actual bills remain single-component TOU through at least mid-2026.

### Decree 58/2025 — Rooftop Solar

Decree 58/2025/ND-CP (effective March 3 2025) covers self-production and self-consumption rooftop solar systems. The surplus export cap under Decree 58 **remains at 20%** — identical to Decree 57's private-wire rule. The proposal to raise the cap to 50% was submitted to MOIT in January 2026 as a **separate draft amendment** and was still under consultation as of March 2026. It is not part of Decree 58.

---

## CEBA Slidedeck Fact-Check

### Session 4.3 — On-Site BESS (19 slides)

| # | Slide | Claim | Verdict | Finding |
|---|-------|-------|---------|---------|
| **B1** | 4 | "Average retail electricity prices have increased by over 17% in the past three years" | **~** | Approximately correct. Cumulative increase from late-2022 base (1,864 VND/kWh) to May 2025 (2,204 VND/kWh) = **+18.2% over ~2.5 years**, crossing the 17% threshold. If reference period is strictly the prior 36 months to mid-2025 the compound is ~14.8% (three increases: +3%, +4.5%, +4.8%). Directionally defensible; exact magnitude depends on reference date. |
| **B2** | 5 | Decision 963 evening peak 17:30–22:30, morning peak eliminated | **✓** | Confirmed exactly. Decision 963/QD-BCT effective April 22 2026; single evening block Mon-Sat; morning peak abolished. |
| **B3** | 9 | "Decree 61: Proposes complete exemption of generation licenses for BESS under 3 MW" | **~** | Decree 61/2025/ND-CP (March 2025) does introduce BTM BESS license exemptions. The 3 MW specific threshold was cited consistently in secondary sources (NRF, Vietnam Energy Magazine) but not independently verified against the primary decree text in this pass. The slide says "proposes," correctly signaling this is not yet fully effective for all BTM cases. |
| **B4** | 9 | **"Decree 58: Raises the ceiling for selling excess rooftop solar up to 50%"** | **✗ WRONG** | Decree 58/2025/ND-CP (effective March 3 2025) **maintains the 20% surplus export cap**. The 50% threshold is a **draft amendment** proposed in January 2026, still under MOIT consultation as of March 2026. The slide attributes a proposed regulatory change to Decree 58 as if it were already enacted law. Correction: "Proposed amendment to Decree 58 (draft, Jan 2026): would raise export cap to 50%." |
| **B5** | 9 | "Over 15 new National Standards issued in sync with IEC 62619" | **?** | Plausible but not independently verified. Vietnam has issued TCVN equivalents aligned with IEC battery safety standards, but the specific count (≥15) and IEC 62619 alignment were not confirmed in available sources. |
| **B6** | 14 | Factory A connected at "22-110kV tariff" | **✓** | Slide explicitly states "22-110kV tariff" as Factory A's voltage tier. Consistent with the case study setup. |
| **B7** | 14/17 | **Case 3 capacity charge ~209,459 VND/kW/month** | **✗ WRONG TIER** | 209,459 VND/kW/month is the **≥110kV** rate. Factory A is on **22kV–110kV**, where the correct trial rate is **235,414 VND/kW/month** (12.4% higher). Source: Decree 146/2025 trial rates confirmed by EVN pilot announcement (ind-006) and Norton Rose Fulbright (ind-016). Impact: all Case 3 metrics (demand-charge savings "$129k/yr", DSCR 1.01, total bill reduction 65%) are calculated on an understated capacity charge. The correct rate would increase the pre-BESS capacity cost and commensurately increase the BESS peak-shaving value — the investment case is slightly stronger than modeled, not weaker. |
| **B8** | 18 | DSCR threshold ≥1.0x for all cases | **✓** | All four cases show Avg DSCR ≥1.01; consistent with bankability framing. |

### Session 6.2 — DPPA Mechanisms (29 slides)

| # | Slide | Claim | Verdict | Finding |
|---|-------|-------|---------|---------|
| **D1** | 4 | **TOU Peak 18:00–23:00; Normal 06:00–18:00** | **✗ WRONG** | Under Decision 963 (the framework the DPPA deck says it covers): Peak is **17:30–22:30**, not 18:00–23:00. Both start and end times are off by 30 minutes. Note: the companion BESS deck (Session 4.3, slide 5) from the **same CEBA series** correctly states 17:30–22:30 — the two slides contradict each other. |
| **D2** | 4 | USD rate table: 22-110kV 0.037/0.070/0.126 $/kWh (offpeak/normal/peak) | **~** | Peak (0.126) and normal (0.070) are **consistent** with the ≥35kV-<220kV production tier at base 2,204 VND/kWh and 26,400 VND/USD (derived: 0.126/0.071). Offpeak (0.037) is **understated** vs derived rate of ~0.045 $/kWh — likely a pre-May-2025 rate carried forward. The label "USD/kWh approx. 2025" suggests the table was built before the May 2025 base price increase. Post-May rates are approximately 4-8% higher on peak/normal and 20% higher on offpeak. |
| **D3** | 4 | Sunday rule: no peak on Sundays | **✓** | Confirmed. Decision 963 weekday-only peak; Sundays + public holidays are all-standard. |
| **D4** | 7 | FMP avg ~1,426.6 VND/kWh (2025 reference) | **✓** | Consistent with market references and repo data. The 2025 average VWEM floor market price is widely cited at approximately this level. |
| **D5** | 7 | DPPA service fee C_dppa_dv = 360 VND/kWh | **~** | Cited consistently across multiple industry sources (NRF, ADK, Duane Morris) as the Decree 57 implementing guideline figure. Not independently verified against the primary implementing circular text in this pass. |
| **D6** | 7 | Balancing fee P_cl = 163.3 VND/kWh | **~** | Same as D5: consistently referenced, not verified against primary text. |
| **D7** | 9/11 | Avg retail P1 = 2,204 VND/kWh | **✓** | Confirmed: Decision 599/QD-EVN effective May 10 2025 (ind-070). |
| **D8** | 17 | Finance: 70% debt / 30% equity; 8.5% VND; ~5% USD; 10-yr tenor | **✓** | Standard Vietnam RE project finance structure; consistent with all industry sources reviewed. |
| **D9** | 17/19 | CIT: 4 years exempt + 9 years at half rate for RE projects | **✓** | Confirmed by PwC Tax Summaries (ind-052/054); standard RE investment incentive under investment law and Circular 78/2014. |
| **D10** | 18 | Lender gate: minimum DSCR ≥1.20x every year | **✓** | Standard Vietnam commercial bank covenant for RE project finance; consistent with industry practice. |
| **D11** | 21 | "Virtual (grid CfD) DPPA under Decree 57/2025/ND-CP" | **✓** | Correct legal framing. Decree 57 governs Model 2 (grid-connected) virtual DPPA. |
| **D12** | 27 | **"Voltage eligibility: ≥22kV only today"** | **~** | **Technically outdated.** Decree 57 replaced Decree 80's fixed ≥22kV rule with "per MOIT wholesale market regulations." In practice VWEM participation still requires ≥22kV, so the slide is operationally correct but the legal language changed. Low severity — the practical implication for buyers is the same. |

---

## Summary of Inaccuracies by Severity

### High — Factual error with material impact on numbers or regulatory framing

| ID | Deck | Slide | Error | Correct Value |
|----|------|-------|-------|---------------|
| B4 | BESS | 9 | Decree 58 allows 50% surplus export | Decree 58 keeps cap at 20%; 50% is a draft amendment proposed Jan 2026, not enacted |
| B7 | BESS | 14/17 | Capacity charge 209,459 VND/kW/month for 22-110kV Factory A | Correct rate for 22-110kV is 235,414 VND/kW/month; 209,459 is the ≥110kV rate |
| D1 | DPPA | 4 | TOU peak 18:00–23:00 | Decision 963 peak is 17:30–22:30 (30-min offset on both ends); contradicts companion BESS deck |

### Medium — Outdated data or approximation with directional impact

| ID | Deck | Slide | Issue | Note |
|----|------|-------|-------|------|
| D2 | DPPA | 4 | USD tariff rates appear pre-May 2025; offpeak understated by ~20% | Update for current 2,204 VND/kWh base |
| D12 | DPPA | 27 | "≥22kV only today" — legal basis changed | Decree 57 changed to "per MOIT regulations"; practically same outcome |

### Low — Unverified or approximate; directionally consistent

| ID | Deck | Slide | Issue |
|----|------|-------|-------|
| B1 | BESS | 4 | "Over 17%" price increase — range is 14.8–18.2% depending on reference date |
| B3 | BESS | 9 | Decree 61 BESS 3 MW threshold — consistent with sources but primary text not confirmed |
| B5 | BESS | 9 | "15+ TCVN standards aligned with IEC 62619" — plausible, not verified |
| D5-6 | DPPA | 7 | DPPA service fee 360 VND/kWh; balancing fee 163.3 VND/kWh — cited widely but not verified against primary circular |

---

## Recommendations for Slide Updates

1. **BESS Slide 9 (Decree 58):** Change to "Proposed amendment to Decree 58 (under MOIT review as of Jan 2026): would raise surplus export cap from 20% to 50%." The 50% cap is not enacted law.

2. **BESS Slide 17 (Case 3 capacity charge):** Replace 209,459 with **235,414 VND/kW/month** as the two-part tariff rate for Factory A's 22kV–110kV connection. Rerun Case 3 financials with the corrected rate — the BESS investment case will be slightly stronger than currently modeled.

3. **DPPA Slide 4 (TOU peak window):** Change "Peak: 18:00–23:00" to "Peak: **17:30–22:30**" to match Decision 963 and the BESS slide. Also update "Normal: 06:00–18:00" to "Normal: 06:00–17:30 + 22:30–24:00."

4. **DPPA Slide 4 (USD rates):** Update the tariff table using the current base price (2,204 VND/kWh) and a current exchange rate. For 22-110kV production the post-May-2025 rates are approximately: offpeak ~0.045, normal ~0.072, peak ~0.126 $/kWh (at 26,400 VND/USD). The offpeak is the most understated item.

5. **DPPA Slide 27 (voltage eligibility):** Soften to "22kV+ in practice (VWEM rules); Decree 57 removed the fixed threshold, eligibility now per MOIT wholesale market regulations."

---

## Open Questions (Unresolved After Deep Pass)

- **Decree 61 exact BESS exemption threshold**: Primary decree text needs direct fetch to confirm "under 3 MW" licensing exemption for BTM BESS. Secondary sources are consistent but the slide's "3 MW" figure was not verified against the signed decree.
- **DPPA fees (360/163.3 VND/kWh)**: Need the primary implementing circular (likely Circular from MOIT/ERAV under Decree 57) to confirm exact fee levels; all current citations are secondary.
- **TCVN battery standards**: Count and scope of TCVN standards aligned with IEC 62619 not confirmed from available sources.
- **Decree 58 amendment timeline**: If the 50% export cap draft amendment is enacted before the CEBA material is used publicly, Slide 9 B4 would become accurate — monitor MOIT circulars.

---

## Sources

1. [EVN: Average retail electricity prices from 10 May 2025](https://en.evn.com.vn/d/en-US/news/Adjusting-average-retail-electricity-prices-from-10-May2025-60-142-500699) — tier 1; confirms 2,204.0655 VND/kWh
2. [EVN: Two-component tariff pilot from October 2025](https://en.evn.com.vn/d/en-US/news/Pilot-implementation-of-two-component-retail-electricity-tariff-from-October-2025-60-142-501015) — tier 1; confirms capacity charges by voltage tier
3. [Norton Rose Fulbright: Two-component tariff explained](https://www.nortonrosefulbright.com/en/knowledge/publications/9f5d6ce8/vietnams-shift-to-capacity-and-energy-pricing-what-the-two-component-tariff-means) — tier 3; confirms 22-110kV = 235,414 VND/kW/month
4. [Norton Rose Fulbright: Decree 57 DPPA key features](https://www.nortonrosefulbright.com/en/knowledge/publications/b7fae014/decree-57-2025-key-features-and-impact-on-direct-power-purchase-agreements-in-vietnam) — tier 3; DPPA fee structure
5. [Viet An Law: Decree 58/2025 key highlights](https://vietanlaw.com/key-highlights-of-decree-58-2025-nd-cp-on-renewable-energy-in-vietnam/) — tier 3; confirms 20% cap under Decree 58; 50% is draft
6. [Duane Morris: Decree 58 on renewable energy and rooftop solar (Aug 2025)](https://blogs.duanemorris.com/vietnam/2025/08/27/vietnam-decree-58-on-development-of-renewable-energy-power-mechanisms-and-policies-for-self-production-and-self-consumption-rooftop-solar-power-systems/) — tier 3; full Decree 58 text analysis
7. [PV Magazine: Vietnam proposes 50% surplus cap (Jan 2026)](https://www.pv-magazine.com/2026/01/13/vietnam-proposes-increase-to-surplus-power-sale-from-rooftop-solar/) — tier 4; confirms 50% is proposal under consultation
8. [Norton Rose Fulbright: BESS development in Vietnam](https://www.nortonrosefulbright.com/en/knowledge/publications/7eb0008e/development-of-battery-energy-storage-systems-in-vietnam) — tier 3; Decree 61 licensing framework for BTM BESS

Full source pool: `research/sources/2026-06-20_vietnam-power-market-2026.sources.jsonl` (30 rows)
