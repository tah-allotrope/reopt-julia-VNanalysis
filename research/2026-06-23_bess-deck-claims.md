# Research Brief: Validating "Cong BESS Session" deck claims vs. 2026 Vietnam energy market

**Date:** 2026-06-23
**Modes run:** domain, codebase
**Depth:** exhaustive
**Invocation context:** Validate the factual/regulatory claims in `ceba-review/cong bess session.pptx` (Session 4.3 — On-Site Solutions Deep Dive) against the latest 2026 Vietnam energy-market information, cross-referencing repo data in `data/vietnam/`.
**Sources (wide/deep):** 97/29 | **Ratio used:** industry=0.55, web=0.45 (github & academia excluded by user)

---

## Synthesis

Across three escalating passes (standard → deep → exhaustive) the deck's **core market mechanics hold up**: the Decision 963 TOU restructure (evening-only peak 17:30–22:30, morning peak abolished), the Decree 146/2025 two-component capacity tariff (Phase 2 paper trial Jan–Jun 2026, Phase 3 real-money Jul 2026–Jul 2027), the ~17% three-year retail rise, the 15 TCVN BESS standards, NSMO's operator role, and curtailment risk are all corroborated by primary EVN/MOIT/standards sources. The full legal chain is confirmed: **Electricity Law 2024 Art. 50 → Circular 60/2025 (TOU framework, eff 2 Dec 2025) → Decision 963/2026 (clock windows)**, with Decree 146/2025 governing the two-part tariff.

**Two hard errors survive all passes, both buyer-favorable.** (1) **Capacity-charge band:** the deck applies **209,459 VND/kW/month (110 kV+)** to a factory it labels "22–110 kV," whose correct rate is **235,414** — confirmed across EVN's release, Arcus Energy, and the repo `vn_tariff_2025.json`. Case 3's demand charge is ~11% too low, flattering its 12.4% IRR / 1.01 DSCR / $0.59M NPV. (2) **Slide 9 "Decree 58 raises the export ceiling to 50%"** is wrong: Decree 58/2025 **Art. 14(2) caps surplus export at 20%**; the 50% figure is a **Jan 2026 MOIT draft amendment, not enacted** (pv-magazine, Vietnam News). The repo models 50% correctly as a *draft* sensitivity.

The exhaustive pass surfaced **three new issues the lighter passes missed.** (3) **Slide 8 overstates and self-contradicts:** "peak shaving completely eliminating expensive capacity charges" is contradicted by the literature — grid-connected buyers keep paying the full capacity charge for backup/availability, and DPPA savings are cut 30–50% by it (Reccessary, NRF) — and by the deck's *own* slide 17, which shows a **−46% peak reduction, not elimination**. (4) **The DPPA double-charging risk is absent:** the deck covers DPPA+BESS firming but omits that CDPPA and the capacity charge recover the *same* grid CAPEX twice — a central 2026 corporate-buyer concern (Reccessary). (5) **"LEGO, H&M" is a weak anchor:** LEGO Manufacturing Vietnam's **DPPA with VSIP** (integrated rooftop solar + BESS, ~75% of demand for 5 yrs, ~15,000 tCO2e/yr, live early 2026) is a *real, on-point* Vietnam case that validates the deck's whole thesis and should replace the generic name-drop; the implied LEGO–H&M supplier link is unsupported.

[NOTE] Several instruments now central to the deck and to 2026 reality are **absent from the repo data layer**: Decree 58, Decree 61, Circular 60/2025, Circular 62/2025 (BESS two-part; an *unverified* vendor-sourced "12% IRR cap"), Circulars 09/12/2025 (10%/2 h storage mandate for centralized solar), and the PDP8 BESS target (10–16.3 GW by 2030). The repo tracks Decision 963 + Decree 146 only. Add the others so deck and model stay reconcilable.

## Source Coverage

| bucket | target | gathered | qualified | cited | reallocated |
|---|---|---|---|---|---|
| industry | 83 | 55 | 52 | 19 | 0 |
| web | 68 | 42 | 25 | 10 | 0 |
| **total** | **151** | **97** | **77** | **29** | **0** |

**Deficit (97 vs 150) is structural, not a stopping-short.** With `github`/`academia` excluded, both active buckets are WebSearch-bound and share one hard 16-query budget (8 industry + 8 web), which was fully spent. Saturation fired on novelty-drop: the last queries returned heavily overlapping URLs (Arcus, NRF, EVN, Reccessary, vietnamnet recur). Vietnam-decree coverage is intrinsically duplicative — dozens of law-firm blogs rehash the same primary texts — so unique tier-≤3 volume plateaus well below 150. Reaching 150 would require the quota-free `github`/`academia` backends the ratio excluded.

## Domain
### Discovery
Primary/authoritative sources: Decree 58 & 61 English texts (luatvietnam, thuvienphapluat), EVN official releases (pilot two-component tariff, Decision 1279 base tariff, new TOU periods, retail-price adjustment), the TCVN standards portal, LEGO's own DPPA press release, Norton Rose Fulbright / Duane Morris / PECC3 analyses, Arcus Energy tariff breakdowns, Reccessary on double-charging, and pv-magazine on the 50% draft and grid strain. Full pool in the ledger (97 rows).

### Verification
- **Decision 963 TOU — CONFIRMED (primary).** Evening peak 17:30–22:30 Mon–Sat; morning peak 09:30–11:30 abolished; off-peak 00:00–06:00; windows-only restructure, effective 22 Apr 2026 ([EVN/MOIT](https://en.evn.com.vn/d/en-US/news/Ministry-of-Industry-and-Trade-issues-new-regulations-on-peak-off-peak-and-normal-time-of-use-periods-of-national-power-system-60-163-501410); [ThuVienPhapLuat](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/thong-bao-van-ban-moi/email/111373/peak-off-peak-and-normal-time-frames-of-vietnam-s-national-power-system); [Arcus Energy](https://arcusenergyasia.com/resources/regulations/decision-963)). Deck slide 5 accurate.
- **Two-component tariff — CONFIRMED.** Phases (paper Jan–Jun 2026; real-money Jul 2026–Jul 2027), scope (≥200,000 kWh/mo at ≥22 kV), legal basis (Art. 50 + Decree 146/2025) ([NRF](https://www.nortonrosefulbright.com/en/knowledge/publications/9f5d6ce8/vietnams-shift-to-capacity-and-energy-pricing-what-the-two-component-tariff-means)). Capacity charges 209,459 / 235,414 / 240,050 / 286,153 by voltage ([EVN](https://en.evn.com.vn/d/en-US/news/Pilot-implementation-of-two-component-retail-electricity-tariff-from-October-2025-60-142-501015); [Arcus manufacturing](https://arcusenergyasia.com/resources/tariffs/manufacturing) puts 22 kV at 235,414) — confirms the deck should use 235,414.
- **Decree 58 export — 20% law, 50% draft.** Art. 14(2) caps at 20%; no 50% provision ([Decree 58 text](https://english.luatvietnam.vn/cong-nghiep/decree-58-2025-nd-cp-detail-law-on-electricity-on-renewable-energy-392208-d1.html)). 50% is a Jan 2026 MOIT draft, with >50% allowed by agreement to 31 Dec 2030 ([pv-magazine](https://www.pv-magazine.com/2026/01/13/vietnam-proposes-increase-to-surplus-power-sale-from-rooftop-solar/); [Vietnam News](https://vietnamnews.vn/economy/1763453/proposal-to-allow-rooftop-solar-to-sell-up-to-50-per-cent-of-surplus-power-to-grid.html)).
- **Decree 61 license exemptions — CONFIRMED; no BESS/3 MW.** Off-grid self-use no limit; grid self-use <30 MW; resale <1 MW; rural retail <100 kVA ([Vu Phong](https://vuphong.com/decree-no-61-2025-nd-cp/)). Deck's "BESS <3 MW exemption" unsupported.
- **TCVN / IEC 62619 — CONFIRMED.** 15 BESS standards, 16 Oct 2025 ([TCVN](https://tcvn.gov.vn/publication-of-15-national-standards-tcvn-on-battery-energy-storage-systems-in-vietnam/16/10/2025/?lang=en)).
- **Retail +17%/3 yr — CONFIRMED (directional).** To 2,204 VND/kWh by May 2025 ([EVN](https://en.evn.com.vn/d/en-US/news/Vietnams-retail-electricity-price-climbs-48-60-163-500704)).
- **NEW — capacity charge is not "eliminated" by peak shaving.** Grid-connected buyers keep paying the full capacity charge for availability/backup; DPPA savings fall 30–50% ([Reccessary](https://www.reccessary.com/en/news/vietnam-power-reform-dppa-two-component-tariff)). Contradicts slide 8 ("completely eliminating") and the deck's own slide 17 (−46%).
- **NEW — DPPA double-charging risk (omitted by deck).** CDPPA + capacity charge recover the same grid CAPEX twice; proposed fix is capacity netting ([Reccessary insight](https://www.reccessary.com/en/insight/vietnam-dppa-two-part-electricity-tariff-mechanism)).
- **NEW — LEGO–VSIP DPPA anchor.** Integrated rooftop solar + BESS; 12,400 panels; ~75% of demand first 5 yrs; ~15,000 tCO2e/yr; live early 2026 ([LEGO press release](https://www.lego.com/en-us/aboutus/news/2025/september/lego-manufacturing-vietnam-signs-dppa-with-vsip)). H&M is RE100 but no Vietnam DPPA / LEGO-supplier link found.
- **RE100 additionality — PARTIAL.** Encouraged, not mandated; 15-yr asset rule; coal co-firing excluded from 2027 ([Monsoon Carbon](https://monsooncarbon.com/re100s-2025-technical-update-stronger-guidance-on-recs-and-what-it-means-for-your-renewable-electricity-strategy/)). Deck's framing OK if softened from "prioritize/required."
- **Self-consumption 40%→70% (slide 8) — overstated vs deck's own table.** Real solar-only factory examples ~35%; the deck's own case table shows 36% (solar only) → 60–66% (solar+BESS), not "40% → well over 70%."
- **Circular 62/2025 "12% IRR cap" — UNVERIFIED.** Only a vendor/marketing source asserts it ([Pilotech](https://www.pilotech.ai/blogs/vietnam-energy-storage-2026-how-circular-62-redefines-c-i-battery-storage-roi/)); needs MOIT primary. Noted because deck Case 3 lands at 12.4% IRR.

### Comparison
High-confidence, multiply-triangulated: Decision 963 windows, two-component phases/scope/values, TCVN, retail trend, curtailment, BESS-market immaturity (<100 kW after-meter). The deck's defects cluster as **buyer-favorable framing** (low capacity band; draft 50% as law; capacity charge "eliminated"; 40%→70%) plus one **omission** (double-charging). The LEGO–VSIP case is a net opportunity, not a defect.

### Synthesis
Reconcile the deck to repo ground truth and fix: (a) rerun Case 3 at **235,414**; (b) slide 9 → "Decree 58 caps export at 20%; Jan 2026 MOIT draft proposes 50% (not enacted)"; (c) slide 8 → capacity charge "reduced" (cite the −46%), not "eliminated," and add the double-charging caveat; (d) replace generic "LEGO, H&M" with the LEGO–VSIP DPPA; (e) align the 40%→70% claim with the case table's 36%→66%; (f) cite a primary or mark "proposed" for the Decree 61 BESS-3 MW and Circular 62 12% IRR claims.

### Confidence
- **industry bucket:** High — 52/55 qualified, primary EVN/MOIT/decree texts read; saturated honestly below target.
- **web bucket:** Medium — 25/42 qualified; strong on the 50% draft, LEGO, RE100; thinner/lower-tier on case-study economics.

## Codebase
### Discovery
`data/vietnam/vn_tariff_2025.json` (voltage-banded capacity charges; 20% export), `vn_regime_registry_2026.json` (Decision 963; Decree 146; `decree57_rooftop_50pct_draft`), `vn_financial_defaults_2025.json`, `src/python/reopt_pysam_vn/analysis/onsite.py` (`run_onsite`), `scripts/python/reopt/decree146_demand_charge.py`.

### Verification
- Repo capacity schedule = external sources exactly → deck's 209,459 is a band-selection error, not stale data.
- Repo two-part default (`decree146_two_part_trial_2026`) and demand-charge script default to **235,414** — the house assumption for 22–110 kV.
- `decree57_rooftop_50pct_draft` encodes 50% as **draft** (correct vs reality), though attributed to Decree 57 rather than the Decree 58 amendment.
- Financial defaults: owner discount 8% vs deck's "10% owner discount" (= repo's *offtaker* rate) — confirm ESCO convention.
- **Factory A load (9,750 MWh, 2,430 kW, LF 0.46) is not a tracked case**; the four-case results appear in no tracked artifact — an un-checked-in run.

### Comparison
Repo onsite engine + data layer are current and externally validated; the deck's numbers are reproducible only by committing the Factory A 8760 load and running `run_onsite` under the four regimes with Case 3 at 235,414.

### Synthesis
(1) Commit Factory A load to `scenarios/case_studies/`; (2) rerun four cases (Case 3 @ 235,414); (3) diff vs deck. Add `data/vietnam` entries for Decree 58 (20% + Jan 2026 50% draft), Decree 61, Circular 60/2025, and BESS circulars 09/12/62-2025.

### Confidence
High on data-layer alignment; Low on case-study results (no checked-in run to diff).

## Sources
Cited (deep set, tier ≤3):
- [Decree 58/2025 — English text](https://english.luatvietnam.vn/cong-nghiep/decree-58-2025-nd-cp-detail-law-on-electricity-on-renewable-energy-392208-d1.html) — Art. 14(2) 20% cap; no 50%.
- [pv-magazine — 20%→50% surplus draft (Jan 2026)](https://www.pv-magazine.com/2026/01/13/vietnam-proposes-increase-to-surplus-power-sale-from-rooftop-solar/) — 50% is a draft.
- [Vietnam News — 50% surplus proposal](https://vietnamnews.vn/economy/1763453/proposal-to-allow-rooftop-solar-to-sell-up-to-50-per-cent-of-surplus-power-to-grid.html)
- [Decree 61/2025 — Vu Phong summary](https://vuphong.com/decree-no-61-2025-nd-cp/) — no BESS/3 MW provision.
- [EVN — pilot two-component tariff](https://en.evn.com.vn/d/en-US/news/Pilot-implementation-of-two-component-retail-electricity-tariff-from-October-2025-60-142-501015) — capacity charges by voltage.
- [EVN/MOIT — new TOU periods](https://en.evn.com.vn/d/en-US/news/Ministry-of-Industry-and-Trade-issues-new-regulations-on-peak-off-peak-and-normal-time-of-use-periods-of-national-power-system-60-163-501410) — Decision 963 windows.
- [Norton Rose Fulbright — two-component tariff](https://www.nortonrosefulbright.com/en/knowledge/publications/9f5d6ce8/vietnams-shift-to-capacity-and-energy-pricing-what-the-two-component-tariff-means) — phases, scope.
- [Arcus Energy — manufacturing tariff](https://arcusenergyasia.com/resources/tariffs/manufacturing) — 22 kV = 235,414.
- [Reccessary — DPPA & two-component tariff](https://www.reccessary.com/en/news/vietnam-power-reform-dppa-two-component-tariff) — full capacity charge persists; savings cut 30–50%.
- [Reccessary — DPPA double-charging](https://www.reccessary.com/en/insight/vietnam-dppa-two-part-electricity-tariff-mechanism) — grid CAPEX recovered twice.
- [LEGO — DPPA with VSIP](https://www.lego.com/en-us/aboutus/news/2025/september/lego-manufacturing-vietnam-signs-dppa-with-vsip) — rooftop solar + BESS anchor.
- [TCVN portal — 15 BESS standards](https://tcvn.gov.vn/publication-of-15-national-standards-tcvn-on-battery-energy-storage-systems-in-vietnam/16/10/2025/?lang=en)
- [Monsoon Carbon — RE100 2025 update](https://monsooncarbon.com/re100s-2025-technical-update-stronger-guidance-on-recs-and-what-it-means-for-your-renewable-electricity-strategy/)
- [EVN — retail price +4.8%](https://en.evn.com.vn/d/en-US/news/Vietnams-retail-electricity-price-climbs-48-60-163-500704)
- [Duane Morris — DPPA + BESS (Feb 2026)](https://blogs.duanemorris.com/vietnam/2026/02/26/vietnam-investing-in-solar-projects-with-dppa-and-bess-what-you-must-know/)
- Repo: `data/vietnam/vn_tariff_2025.json`, `vn_regime_registry_2026.json`, `vn_financial_defaults_2025.json`; `src/python/reopt_pysam_vn/analysis/onsite.py`; `scripts/python/reopt/decree146_demand_charge.py`.

Full source pool: `research/sources/2026-06-23_bess-deck-claims.sources.jsonl` (97 rows).
