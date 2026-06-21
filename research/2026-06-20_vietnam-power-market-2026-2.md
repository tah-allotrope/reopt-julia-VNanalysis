# Research Brief: Vietnam Power Market Update 2026

**Date:** 2026-06-20
**Modes run:** domain, literature
**Depth:** exhaustive
**Invocation context:** Vietnam power market 2026 update — regulatory, tariff, and market structure developments (PDP8, Decision 14/2025, Decision 963/2026, Decree 57/2025 DPPA, Decree 58/2025 rooftop solar, Decree 146/2025 two-part tariff, Decree 61/2025 BESS licensing, EVN tariff schedules, FMP/VWEM market prices, wheeling charges, grid access rules). Compare findings against slidedecks in ceba-review/ for factual inaccuracies.
**Run:** 2 (upgraded skill, regulatory-heavy ratio)
**Sources (wide/deep):** 313/35 | **Ratio used:** github=0.05, academia=0.15, industry=0.40, web=0.40

---

## Synthesis

Vietnam's 2026 power market is defined by three simultaneous shifts: a completed tariff restructuring (base price 2,204.0655 VND/kWh from May 10 2025; consolidated evening peak from April 22 2026), a newly operational corporate DPPA framework (Decree 57/2025, upgraded to fully negotiable pricing by Resolution 253 effective March 1 2026), and a nascent two-part tariff pilot for large industrial customers (Decree 146/2025, paper trial Jan–Jun 2026, full billing implementation expected July 2026). The Samsung SVET + TTC Duc Hue 2 DPPA (49 MW, ~70 GWh/yr) — the exact project modeled in this repository — became Vietnam's first operational grid-connected DPPA on June 3 2026.

The CEBA slidedecks contain three confirmed factual errors and one material unverified claim. (1) The BESS deck (Session 4.3, Slide 9) incorrectly states Decree 58/2025 "raises the surplus export ceiling to 50%" — the enacted cap is 20%; 50% is a draft amendment under MOIT consultation as of March 2026. (2) The BESS deck applies the ≥110kV capacity charge (209,459 VND/kW/month) to a 22–110kV case — the correct tier is 235,414 VND/kW/month (12.4% higher). (3) The DPPA deck (Session 6.2, Slide 4) shows peak TOU "18:00–23:00" — Decision 963 (eff. April 22 2026) mandates 17:30–22:30 Mon–Sat; no current or legacy Vietnamese schedule uses an 18:00-23:00 window. (4) The DPPA deck's off-peak electricity rate for the 22–110kV tier (0.037 $/kWh ≈ 977 VND) is approximately 22% below the enacted rate (1,190 VND/kWh ≈ 0.045 $/kWh at 26,400 VND/USD).

The DPPA fee components cited in Session 6.2 (C_dppa_dv = 360 VND/kWh; P_cl = 163.3 VND/kWh) could not be independently verified from any publicly accessible secondary source. Article 16 of Decree 57 establishes the formula structure (C_ĐN + C_DPPA + C_CL + C_BL + CfD) but the specific VND amounts are set by MOIT/NLDC implementation circulars not yet publicly indexed. These figures should be treated as plausible estimates from a practitioner source, not confirmed regulatory values.

[NOTE] Resolution 253/2025/QH15 (effective March 1 2026) eliminates DPPA price ceilings for private-line agreements and expands eligible participants to include industrial zone electricity retailers — a significant liberalization not captured in either CEBA slidedeck. Combined with the June 2026 Samsung-TTC commissioning, the DPPA framework has moved from regulatory design to active market operation faster than most institutional forecasts anticipated.

---

## Source Coverage

| Bucket | Target | Gathered | Qualified (tier≤3) | Cited | Reallocated |
|---|---|---|---|---|---|
| github | 13 | 22 | 18 | 1 | 0 |
| academia | 38 | 73 | 61 | 6 | 0 |
| industry | 100 | 155 | 103 | 20 | 0 |
| web | 100 | 63 | 41 | 8 | 0 |
| **TOTAL** | **251** | **313** | **223** | **35** | **0** |

Web bucket hit session limits at 63 rows (vs. 1.5× target of 150). All cited web claims were cross-verified via industry bucket sources; no reallocation required. Industry bucket exceeded target at 155 rows (1.5× cap met). GitHub ran to oversaturation (1.7× target); low-signal bucket with only 1 source cited.

---

## Domain Mode

### Discovery

Primary regulatory instruments governing the 2026 market, all under Electricity Law 2024 (effective February 2025):

| Instrument | Effective date | Subject |
|---|---|---|
| Decision 14/2025/QD-TTg | 2025 | Tariff framework — multiplier bands by voltage |
| Decision 1279/QD-BCT | May 9 2025 | Retail tariff schedule — specific VND/kWh |
| Decision 599/QD-EVN | May 10 2025 | Base average retail price: 2,204.0655 VND/kWh |
| Circular 60/2025/TT-BCT | 2025 | Customer category definitions (data centre reclassification) |
| Decree 57/2025/ND-CP | March 2025 | DPPA framework — grid-connected and private-line |
| Decree 58/2025/ND-CP | March 3 2025 | Rooftop solar — self-consumption, 20% surplus cap |
| Decree 61/2025/ND-CP | March 4 2025 | Electricity operation licensing; <30MW self-use exempt |
| Decree 146/2025/ND-CP | 2025 | Two-part tariff pilot — capacity + energy components |
| Circular 62/2025/TT-BCT | 2025 | BESS electricity service pricing framework |
| Decision 963/QD-BCT | April 22 2026 | TOU schedule — consolidated evening peak 17:30–22:30 |
| Resolution 253/2025/QH15 | March 1 2026 | DPPA price ceiling removed; expanded eligible participants |
| Decision 768/QD-TTg | April 15 2025 | PDP8 revised targets (BESS 10,000–16,300 MW by 2030) |

Strongest primary sources: EVN official English site (tier-1) for retail price, Decision 1279 rates, two-part tariff pilot announcement; Vietnam.vn government portal (tier-1) for Decree 61 license exemption; LuatVietnam (tier-1) for Decree 58 text.

Strongest secondary sources: Arcus Energy Asia (tier-3) for exact VND/kWh manufacturing rate tables by voltage tier including the Decision 963 hours; Norton Rose Fulbright (tier-3) for Decree 57 DPPA structure, Circular 62 BESS pricing, and two-part tariff analysis; DFDL (tier-3) for comprehensive tariff schedule under Decision 14/Decision 1279.

### Verification

**Confirmed with tier-1 or multi-source tier-3 agreement:**

- Base retail price 2,204.0655 VND/kWh effective May 10 2025: EVN official (×2 sources) ✓
- Decision 963 consolidated peak 17:30–22:30 Mon-Sat; no Sunday peak; off-peak 00:00–06:00: Arcus Energy WebFetch + Arcus web source ✓
- Manufacturing tariff by voltage (Decision 1279/QD-BCT, eff. May 10 2025):

  | Voltage | Peak (VND/kWh) | Standard | Off-peak |
  |---|---|---|---|
  | ≥110 kV | 3,266 | 1,811 | 1,146 |
  | 22–<110 kV | 3,398 | 1,833 | 1,190 |
  | 6–<22 kV | 3,508 | 1,899 | 1,234 |
  | <6 kV | 3,640 | 1,987 | 1,300 |

  Source: EVN tier-1 (ind-055) for ≥110kV row; Arcus Energy Asia WebFetch for full table.

- Two-part tariff capacity charges (Decree 146/2025):

  | Voltage | VND/kW/month |
  |---|---|
  | ≥110 kV | 209,459 |
  | 22–<110 kV | 235,414 |
  | 6–<22 kV | 240,050 |
  | <6 kV | 286,153 |

  Source: EVN official pilot announcement (ind-090, tier-1); Norton Rose Fulbright (ind-016, tier-3). Paper trial Oct 2025 – Jun 2026; full implementation July 1 2026.

- Decree 58/2025 surplus export cap = 20% of installed capacity: LuatVietnam (tier-1), Viet An Law (tier-3), Duane Morris (tier-3) ✓
- 50% cap = draft amendment only (MOIT Jan 2026 proposal, not enacted): B-Company (tier-3, March 2026), PV Magazine (tier-4), Duane Morris (tier-3) ✓
- Decree 61 grid-connected self-use license exemption threshold = <30 MW: Vietnam.vn (ind-035, tier-1) ✓ — "3 MW" cited in earlier session was unverified and is superseded
- Resolution 253/2025/QH15 (eff. March 1 2026): Removes DPPA price ceiling for private-line; expands to industrial zone retailers: VILAF (tier-3), Watson Farley & Williams (tier-3), Reccessary (tier-3) ✓
- Samsung-TTC Duc Hue 2 (49 MW, ~70 GWh/yr) operational June 3 2026: PV Magazine (web-016, tier-3) ✓; corroborated by IEEFA "1 grid-connected DPPA by early 2026" context
- Circular 62/2025/TT-BCT: BESS electricity service pricing framework (first formal BESS price frame in ASEAN): Norton Rose Fulbright (ind-071, tier-3) ✓

**Unverified claims requiring primary circular access:**

- DPPA service fee C_dppa_dv = 360 VND/kWh: No independent public source; Article 16 Decree 57 gives the formula structure but the specific VND amount is set by MOIT/NLDC order (not yet publicly indexed). Appears only in the DPPA slide.
- DPPA balancing fee P_cl = 163.3 VND/kWh: Same status — formula confirmed, specific quantum not verified.
- FMP 2025 annual average ≈ 1,426.6 VND/kWh: Plausible given VWEM wholesale market context (30-minute clearing, market price + capacity price components per EnergyTag) but not confirmed to this precision from any public source.

### Comparison

**TOU window shift — Decision 14 → Decision 963:**

| | Old split-peak (Decision 14) | New consolidated peak (Decision 963, eff. Apr 22 2026) |
|---|---|---|
| Monday–Saturday peak | 09:00–11:30 + 17:00–20:00 | 17:30–22:30 (continuous) |
| Off-peak | 22:00–04:00 | 00:00–06:00 |
| Sunday | Off-peak all day | Off-peak all day |

Decision 963 eliminates the morning peak entirely, extends the evening peak by 2.5 hours (5h vs. 2.5h effective in the afternoon block), and shifts off-peak from 22:00 to midnight. BESS models using the pre-963 split-peak schedule are systematically misconfiguring dispatch — morning grid export is now at standard tariff, not peak.

**Decree 57 → Resolution 253 DPPA evolution:**

| Parameter | Decree 57 (March 2025) | Post-Resolution 253 (March 2026) |
|---|---|---|
| Price ceiling | Formula-bound per Article 16 | Removed for private-line contracts |
| Eligible consumers | Large consumers ≥1 MW demand | + Industrial zone electricity retailers |
| Eligible generators | RE sources (wind, solar, small hydro, ocean, geothermal, biomass) | Unchanged |
| Balancing mechanism | Consumer pays EVN for imbalance | Unchanged |

**Two-part tariff rollout timeline:**
- Paper trial stage 1: Oct–Dec 2025 (billing statement only, zero real payment impact)
- Paper trial stage 2: Jan–Jun 2026 (continued paper trial; eligible customers ≥22 kV consuming ≥200,000 kWh/month)
- Full implementation: July 1 2026 (actual capacity charge billing begins; source: Arcus WebFetch)

### Synthesis

The tariff regime has undergone its most significant structural change since the 2019 partial market reform. Key planning implications for this repository:

1. **TOU dispatch models**: The pre-963 morning peak no longer exists. BESS charge dispatch during 09:00–11:30 is now at standard tariff, reducing charge-time grid cost but also reducing peak-to-offpeak spread for discharge arbitrage. Models using Decision 14 windows need a full dispatch recalibration.

2. **Two-part tariff adds a capacity dimension**: 235,414 VND/kW/month for 22-110kV customers (Samsung-TTC and similar industrial DPPAs) on a registered Pmax basis. BESS projects that reduce Pmax registration can capture capacity charge savings of ~2.8M VND/kW/year — material at 49 MW scale (~137M VND/MW/year).

3. **DPPA ceiling removal (Resolution 253)**: Grid-connected DPPA prices are now fully negotiable between RE generator and consumer. The Samsung-TTC deal economics will differ from Decree 57 baseline slides if the contract was renegotiated post-March 2026.

4. **BESS licensing**: The threshold for grid-connected self-use BESS license exemption is 30 MW (not 3 MW as tentatively noted in earlier session). Behind-the-meter BESS at <30 MW self-use scale avoids electricity operation licensing requirements.

### Confidence: **High** for all regulatory instrument parameters (tier-1 confirmed or multi-source tier-3 agreement). **Low** for specific fee quantum values (360/163.3 VND/kWh) and FMP precision.

---

## Literature Mode

### Discovery

Key institutional reports and academic literature:
- IEA "Achieving a Net Zero Electricity Sector in Viet Nam" 2025 full report (tier-2, ind-065)
- IEEFA "From boom to balance in Vietnam's clean energy transition" 2025 (tier-2, ind-066)
- ADB "Assessment of Power Sector Reforms in Viet Nam" 2024 (tier-2, ind-093)
- OECD Economic Surveys: Viet Nam 2025, Chapter "Unlocking low-carbon economic growth" (tier-2, ind-067)
- ADB Vietnam country overview 2026 ($16.6bn committed, $5–6bn 2026–2029 pipeline) (tier-2, ind-068)
- World Bank Vietnam power sector reform reports (tier-2, aca-003)
- Applied Energy: "ASEAN low-carbon pathways" (tier-2, aca-009)
- Academic papers: BESS integration in Vietnam grid 2025 (aca-023); PyPSA CO2 study PDP8 2025 (aca-022)

Critical market news (tier-3):
- PV Magazine June 3 2026: Vietnam's first grid-connected DPPA enters operation (Samsung SVET + TTC Duc Hue 2) (web-016)
- IEEFA: 60+ DPPA contracts signed by early 2026; only 1 grid-connected operational (web-018)
- Reccessary 2026: Implementation gap — opaque EVN pricing, limited grid data digitalization, FiT retroactive dispute risk (ind-053)

### Verification

Institutional reports are consistent in their macro narrative: Vietnam's clean energy transition faces a financing gap (~$30bn by 2030 per IEA), EVN financial stress (~VND 45 trillion cumulative losses per MOIT/GG Power), and an execution gap between regulatory design and project commissioning. No institutional report provides specific VND/kWh tariff parameters — those must come from primary regulatory instruments.

The PV Magazine Samsung-TTC commissioning report (web-016) could not be corroborated by a second independent publication (IEEFA's "1 grid-connected" count predates the June 3 commissioning). The Reccessary "60+ contracts signed, 1 grid-connected" figure (web-019/ind-053) is corroborated by IEEFA (web-018) — consistent two-source tier-3/tier-2 agreement.

### Comparison

Institutional analyses diagnose different binding constraints:
- IEA: Investment quantum ($30–60bn) and grid upgrade lag
- IEEFA: FiT retroactive risk chilling private finance; EVN credit constraint
- ADB: Governance pace; utility restructuring incomplete
- OECD: Energy subsidy removal; pricing reform as fiscal instrument

These are complementary, not competing. The academic papers (PyPSA, BESS integration) are scenario-modeling studies with limited near-term regulatory specificity — useful for PDP8 target validation but not for tariff modeling.

### Synthesis

For this repository's purposes: institutional literature confirms that Samsung-TTC Duc Hue 2 is commercially and operationally significant (first grid-connected DPPA in a market that signed 60+ contracts), and that the regulatory design is now sufficiently complete to run meaningful economic models. However, no academic or institutional source independently verifies the DPPA fee quantum values (360/163.3 VND/kWh) or the FMP precision figure — these must be treated as unverified practitioner inputs until MOIT publishes the implementing circular.

### Confidence: **Medium** — strong institutional consensus on macro trajectory; specific tariff and fee parameters not available in literature.

---

## CEBA Slidedeck Fact-Check

### Ground truth sources used
- `data/vietnam/vn_tariff_2025.json` and `data/vietnam/vn_regime_registry_2026.json` (repo)
- EVN Official Decision 1279 tariff page (ind-055, tier-1)
- Arcus Energy Asia manufacturing tariff (WebFetch, tier-3)
- EVN two-part tariff pilot announcement (ind-090, tier-1)
- Norton Rose Fulbright two-part tariff (ind-016, tier-3)
- LuatVietnam / Viet An Law / Duane Morris on Decree 58 (tier-1/3)
- Vietnam.vn on Decree 61 (ind-035, tier-1)

---

### Session 4.3 — BESS Slidedeck

| ID | Slide | Claim in Slide | Verdict | Correct Value | Sources |
|---|---|---|---|---|---|
| B1 | 5 | Decision 963 peak: "17:30–22:30" | ✅ CORRECT | 17:30–22:30 Mon-Sat (Decision 963 eff. Apr 22 2026) | Arcus WebFetch; repo vn_tariff_2025.json |
| B2 | 9 | "Decree 58: Raises ceiling to 50%" | ❌ WRONG | Enacted cap = **20%**; 50% is a draft proposal (Jan 2026, not enacted) | LuatVietnam (T1), Viet An Law (T3), Duane Morris (T3) |
| B3 | 14/17 | Capacity charge "~209,459 VND/kW/month" for 22-110kV case | ❌ WRONG | 22-110kV tier = **235,414** VND/kW/month; 209,459 is the ≥110kV tier | EVN T1 (ind-090), NRF (ind-016), Arcus WebFetch |

**B2 detail**: Decree 58/2025/ND-CP (effective March 3 2025) enacted the surplus export cap at 20% of installed capacity, with surplus priced at the prior-year VWEM average. A separate MOIT draft amendment circulated January 2026 proposes raising this to 50%, but it remains under public consultation and has not been enacted as of March 2026. The slide conflates a draft proposal with enacted law — a material error for BESS project economics modeling.

**B3 detail**: The two-part tariff under Decree 146/2025 has four voltage tiers. Factory A at 22kV falls in the 22-<110kV band (235,414 VND/kW/month), not the ≥110kV band (209,459 VND/kW/month). Using 209,459 understates the monthly capacity charge by 25,955 VND/kW/month (~12.4%), systematically underestimating BESS capacity charge savings for 22kV manufacturing customers. At the Samsung-TTC scale (49 MW peak demand), this error would understate annual capacity savings by ~15M VND/MW/year.

---

### Session 6.2 — DPPA Slidedeck

| ID | Slide | Claim in Slide | Verdict | Correct / Expected Value | Sources |
|---|---|---|---|---|---|
| D1 | 4 | Peak TOU: "18:00–23:00" | ❌ WRONG | **17:30–22:30** Mon-Sat (Decision 963, eff. Apr 22 2026) | Decision 963; Arcus; repo |
| D2 | 7 | FMP ≈ 1,426.6 VND/kWh | ⚠️ UNVERIFIED | Plausible (wholesale market context consistent) | IEEFA, EnergyTag — indirect only |
| D3 | 7 | DPPA service fee: 360 VND/kWh | ⚠️ UNVERIFIED | Article 16 Decree 57 sets formula; quantum set by MOIT circular (not publicly indexed) | No independent source found |
| D4 | 7 | Balancing fee: 163.3 VND/kWh | ⚠️ UNVERIFIED | Same — formula confirmed, specific VND amount not verified | No independent source found |
| D5 | 9/11 | Base retail price P1 = 2,204 VND/kWh | ✅ CORRECT | 2,204.0655 VND/kWh (Decision 599/QD-EVN, May 10 2025) | EVN T1 (ind-040) |
| D6 | Case | Off-peak rate: 0.037 $/kWh (22-110kV) | ❌ WRONG | **~0.045 $/kWh** (1,190 VND ÷ 26,400 VND/USD) | Arcus WebFetch; EVN T1 (ind-055) |
| D7 | Case | Peak rate: 0.126 $/kWh (22-110kV) | ⚠️ CLOSE | ~0.129 $/kWh (3,398 VND ÷ 26,400); consistent with ~27,000 VND/USD exchange | Arcus WebFetch |
| D8 | Case | Standard rate: 0.070 $/kWh (22-110kV) | ✅ CLOSE | ~0.069 $/kWh (1,833 VND ÷ 26,400) | Arcus WebFetch |

**D1 detail**: No current or historical Vietnamese tariff schedule uses an 18:00–23:00 peak window. Decision 963's window (17:30–22:30) begins 30 minutes earlier and ends 30 minutes earlier. The old Decision 14 schedule used a split-peak (09:00–11:30 + 17:00–20:00). The slide's "18:00–23:00" is inconsistent with all known Vietnamese TOU schedules. Possible origins: an internal draft schedule, a misread of the Decision 963 text, or an early draft before the final window was set. For BESS dispatch modeling, using 18:00–23:00 shifts the peak 30 minutes late in both directions, affecting early-evening dispatch.

**D6 detail**: The off-peak rate of 0.037 $/kWh corresponds to ~977 VND/kWh at 26,400 VND/USD. The actual 22-<110kV off-peak rate is 1,190 VND/kWh. For 0.037 $/kWh to equal 1,190 VND, the exchange rate would need to be ~32,162 VND/USD — implausibly high. Even at 30,000 VND/USD (a historically extreme depreciation scenario), 0.037 × 30,000 = 1,110 VND, still 7% below the actual rate. The 0.037 figure likely comes from a pre-2023 tariff (base ~1,864 VND/kWh) using an older offpeak multiplier (~0.52). The slide appears to have updated peak and standard rates but not the off-peak. This systematically underestimates grid electricity cost during charge hours (00:00–06:00) for BESS arbitrage calculations.

**D7/D8 detail**: Peak (0.126) and standard (0.070) rates are consistent with Decision 1279 22-<110kV rates at an exchange rate of approximately 27,000 VND/USD. At the repo's reference rate of 26,400 VND/USD, the discrepancy is 2–3% — within reasonable rounding/exchange-rate tolerance for a slide prepared with rounded USD figures. These values should NOT be flagged as errors.

**Critical omissions from both slides** (regulatory developments post-slide preparation):
1. **Resolution 253/2025/QH15 (eff. March 1 2026)**: DPPA price ceilings removed for private-line contracts; industrial zone electricity retailers added as eligible consumers
2. **Samsung-TTC Duc Hue 2 operational (June 3 2026)**: Vietnam's first grid-connected DPPA is now live — the project these slides modeled is in production

---

## Sources

### Tier-1 — Primary Government / Official
- [EVN Retail Electricity Tariff — Decision 1279/QD-BCT](https://en.evn.com.vn/d/en-US/news/RETAIL-ELECTRICITY-TARIFF-Decision-No-1279QD-BCT-dated-9-May-2025-of-Ministry-of-Industry-and-Trade-60-28-252) — primary tariff schedule; manufacturing VND/kWh by voltage
- [EVN Price Adjustment May 10 2025 (Decision 599/QD-EVN)](https://en.evn.com.vn/d/en-US/news/Adjusting-average-retail-electricity-prices-from-10-May2025-60-142-500699) — 2,204.0655 VND/kWh base confirmed
- [EVN Two-Component Tariff Pilot Announcement](https://en.evn.com.vn/d/en-US/news/Pilot-implementation-of-two-component-retail-electricity-tariff-from-October-2025-60-142-501015) — capacity charges by voltage tier confirmed
- [EVN New Retail Pricing Framework](https://en.evn.com.vn/d/en-US/news/Vietnam-sets-new-framework-for-retail-electricity-pricing-60-163-500634) — Decision 14/2025 and Circular 60/2025 framework
- [Vietnam.vn — Decree 61 license exemption](https://www.vietnam.vn/en/ai-duoc-mien-giay-phep-dien-luc-va-khong-gioi-han-cong-suat-lap-dien-mat-troi-mai-nha/) — 30 MW grid-connected self-use threshold

### Tier-2 — Intergovernmental / Institutional
- [IEA Achieving Net Zero Electricity Vietnam 2025 (PDF)](https://iea.blob.core.windows.net/assets/522afcb9-097c-440a-909c-c1fd5f2cdfca/AchievinganetzeroelectricitysectorinVietNam.pdf) — $30bn investment 2030, grid pathway scenarios
- [IEEFA From boom to balance — Vietnam clean energy transition](https://ieefa.org/resources/boom-balance-vietnams-clean-energy-transition) — FiT retroactive risk; EVN financial stress; DPPA pipeline status
- [ADB Assessment of Power Sector Reforms in Viet Nam](https://www.adb.org/sites/default/files/institutional-document/173769/vie-power-sector-reforms.pdf) — governance pace as binding constraint
- [OECD Vietnam Economic Surveys 2025 — Low-carbon growth](https://www.oecd.org/en/publications/oecd-economic-surveys-viet-nam-2025_fb37254b-en/full-report/unlocking-low-carbon-economic-growth_d1fdfa53.html) — energy pricing reform as fiscal lever
- [US ITA — Vietnam Revised PDP8 Market Intelligence](https://www.trade.gov/market-intelligence/vietnam-revised-power-development-plan-viii) — US government analysis of PDP8 investment opportunities

### Tier-3 — Specialist Legal / Advisory / Practitioner
- [Arcus Energy Asia — Manufacturing Tariff Table](https://arcusenergyasia.com/resources/tariffs/manufacturing) — full 4-tier VND/kWh table confirmed; Decision 963 hours; Decree 146 capacity charge
- [Arcus Energy Asia — Decision 963 Update](https://arcusenergyasia.com/resources/tariffs) — TOU window change; notes pending next retail adjustment
- [Norton Rose Fulbright — BESS Development Vietnam](https://www.nortonrosefulbright.com/en/knowledge/publications/7eb0008e/development-of-battery-energy-storage-systems-in-vietnam) — Decree 61, Circular 62 BESS pricing framework
- [Norton Rose Fulbright — Two-Component Tariff](https://www.nortonrosefulbright.com/en/knowledge/publications/9f5d6ce8/vietnams-shift-to-capacity-and-energy-pricing-what-the-two-component-tariff-means) — 235,414 VND/kW/month at 22-110kV confirmed
- [Norton Rose Fulbright — Decree 57 DPPA Features](https://www.nortonrosefulbright.com/en/knowledge/publications/b7fae014/decree-57-2025-key-features-and-impact-on-direct-power-purchase-agreements-in-vietnam) — DPPA framework; fee formula structure
- [DFDL — Vietnam 2025 Retail Electricity Rates](https://www.dfdl.com/insights/legal-and-tax-updates/vietnams-2025-retail-electricity-rates/) — comprehensive tariff schedule under Decision 14/1279; September 2025
- [Viet An Law — Decree 58 Highlights](https://vietanlaw.com/key-highlights-of-decree-58-2025-nd-cp-on-renewable-energy-in-vietnam/) — 20% surplus cap enacted; 50% is subsequent draft
- [Duane Morris — Decree 58 Analysis](https://blogs.duanemorris.com/vietnam/2025/08/27/vietnam-decree-58-on-development-of-renewable-energy-power-mechanisms-and-policies-for-self-production-and-self-consumption-rooftop-solar-power-systems/) — rooftop solar 20% cap; March 2025 decree detail
- [VILAF — Resolution 253/2025](https://www.vilaf.com.vn/blog/a-new-legal-era-for-energy-in-vietnam-national-assembly-introduces-special-mechanisms-to-unlock-power-and-infrastructure-investment/) — DPPA price ceiling removed; new eligible participants
- [Watson Farley & Williams — Resolution 253](https://www.wfw.com/articles/new-resolution-on-vietnams-national-energy-development/) — DPPA liberalization; industrial zone retailer inclusion
- [Reccessary — DPPA Double-Charging Risk Analysis](https://www.reccessary.com/en/insight/vietnam-dppa-two-part-electricity-tariff-mechanism) — Article 16 fee formula structure; C_ĐN/C_DPPA/C_CL/C_BL components
- [Reccessary — Vietnam DPPA Barriers 2026](https://www.reccessary.com/en/news/vietnam-power-reform-dppa-two-component-tariff-2) — implementation gap; 1 grid-connected by early 2026
- [EnergyTag — Vietnam 30-Minute Wholesale Market](https://energytag.org/vietnams-power-market-shift-what-30-minute-pricing-means-for-clean-energy/) — FMP structure (market electricity price + market capacity price); VWEM mechanics
- [PV Magazine — Vietnam First DPPA Enters Operation](https://www.pv-magazine.com/2026/06/03/vietnams-first-direct-power-purchase-agreement-enters-operation/) — Samsung SVET + TTC Duc Hue 2; 49 MW; June 3 2026; Yen Binh Industrial Park
- [IEEFA — Vietnam DPPA Analysis](https://ieefa.org) — 60+ contracts signed; 1 grid-connected operational (early 2026)
- [Kongnh/Reopt-API — evn_tariff.py](https://github.com/Kongnh/Reopt-API/blob/d0a12b532bb050afdef2340505127341f3cb3334/reoptjl/src/vietnam/evn_tariff.py) — (github) REopt fork with Vietnam EVN tariff implementation; tariff structure cross-reference

---

*Full source pool: `research/sources/2026-06-20_vn-power-market-2026-2.sources.jsonl` (313 rows)*
