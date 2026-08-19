# CEBA Repo Delta Report: ceba-review Folder vs. Review Report Findings

**Generated:** 19 June 2026  
**Based on:** `ceba_slide_review_report.md` (15 June 2026)  
**Folder audited:** `C:\Users\tukum\Downloads\reopt-pysam\ceba-review\`

---

## 1. What Is in the ceba-review Folder

Two PPTX files are present. One was reviewed on 15 June; the other is new.

| File | Size | Slides | Status |
|------|------|--------|--------|
| `cong_session_6.2_DPPA.pptx` | 2.45 MB | 29 | **Previously reviewed** — basis for the 15 June report |
| `cong bess session.pptx` | 11.89 MB | 19 | **NEW — not reviewed before**; Session 4.3: "On-Site Solutions Deep Dive Additional Considerations" |

No other files, no PDFs, no speaker notes exports, no data workbooks.

---

## 2. Gap-by-Gap Status Check

The original report identified 9 issues across two CRITICAL, two HIGH, and five MEDIUM/LOW buckets. Here is the status of each after examining the new BESS file.

### 2.1 CRITICAL: Samsung SEVT × TTC Duc Hue 2 Deal (June 1, 2026)

**Status: ❌ STILL MISSING from both files**

Neither the DPPA deck (Session 6.2) nor the BESS deck (Session 4.3) references the Samsung SEVT × TTC Duc Hue 2 deal by name. The BESS deck's Slide 9 lists "Peer-to-Peer Trading (DPPA): Paves the way for industrial parks to establish micro-grids" as a regulatory positive, but this is a general description — not the live deal.

The BESS deck uses a generic "Factory A" case study (an unnamed 22–110 kV industrial consumer in Vietnam). This is directionally helpful but does not anchor either session to the one confirmed live precedent that workshop attendees will be asking about.

**Verdict:** The most important gap in the original review remains open. Cong's two prepared sessions together still contain zero explicit reference to Vietnam's first executed DPPA.

---

### 2.2 CRITICAL: Two-Part Tariff Risk (Decree 146 / Phase 3, July 2026)

**Status: ✅ ADDRESSED in the BESS deck — ❌ STILL MISSING from the DPPA deck**

The new BESS deck addresses the two-part tariff in meaningful depth:

- **Slide 14:** Case 3 scenario explicitly models "New TOU + two-component capacity tariff (~209,459 VND/kW/month)."
- **Slide 17:** Full quantitative impact — peak demand cut from 2,428 kW to 1,311 kW (−46%), demand-charge savings of $129k/yr, equity IRR of 12.4%, DSCR of 1.01.
- **Slide 8:** Lists "Capacity Management" as the "largest revenue stream" for BESS — directly tied to peak-shaving the capacity component of the two-part bill.

However, Session 6.2 (DPPA) still contains zero mention of the two-part tariff. The two sessions are structured independently; a workshop attendee who only attends Session 6.2 will evaluate a virtual DPPA with no knowledge that their EVN bill structure is fundamentally changing the same month as the workshop.

**Verdict:** Gap half-closed at the workshop level (BESS session covers it), but not closed within the DPPA session where it is most directly relevant to DPPA economics. The forward action remains: add a two-part tariff warning slide to Session 6.2.

---

### 2.3 HIGH: Resolution 253 (December 2025) — Ceiling Price Removed for Physical DPPA

**Status: ❌ NOT MENTIONED in either file**

Neither deck references Resolution 253/2025/QH15. The BESS deck's regulatory slide (Slide 9) cites Decree 61 and Decree 58, but not Resolution 253. For a workshop audience weighing physical vs. virtual DPPA options, this remains a gap.

---

### 2.4 HIGH: Strike Floor Inconsistency (1,200 vs. 1,012 VND/kWh)

**Status: ❌ NOT RESOLVED**

The BESS deck does not reference DPPA strike pricing. The original discrepancy — Cong's case study uses 1,200 VND/kWh as the floor while the Samsung deal was anchored near the Southern ceiling of 1,012 VND/kWh — is unaddressed.

---

### 2.5 MEDIUM: Grid-Service Adder Framing

**Status: ❌ NOT ADDRESSED in new file** (different session scope)

The BESS deck does not discuss off-site DPPA grid-service fees. The adder sensitivity gap remains in Session 6.2.

---

### 2.6 MEDIUM: "Window is Empty" — Path to Bankability

**Status: ⚠️ PARTIALLY ADDRESSED — via BESS framing**

The BESS deck's "Firmed VPPA" concept (Slides 10–11) is directly relevant here. The deck argues that co-locating BESS with a virtual DPPA transforms a financially fragile CfD contract into a "gold standard asset" with stable cash flows and improved lender comfort. Slide 11 explicitly says: "Stable payment cash flows and highly predictable long-term costs make BESS-integrated VPPAs a 'gold standard' asset, making green credit disbursement significantly easier."

This is one structural path to bankability (BESS firming) that Session 6.2 does not mention. It does not substitute for the structural levers missing from Slide 28 (lower leverage, USD debt, longer tenor), but it adds a valid fourth lever.

---

### 2.7 MEDIUM: Developer "Sub-Economic" Needs Merchant Tail Nuance

**Status: ❌ NOT ADDRESSED in new file**

The BESS deck is buyer-side only; it does not address developer economics or merchant tail. Gap unchanged.

---

### 2.8 MEDIUM: CBAM / Supply Chain Documentation

**Status: ❌ NOT ADDRESSED in either file**

Neither deck mentions EU CBAM, hourly matching, or additionality documentation. Gap unchanged.

---

### 2.9 LOW: Corporate Buyer Pipeline Context

**Status: ❌ NOT ADDRESSED in either file**

No pipeline context (Apple supply chain, Heineken, KN Holdings × Samsung C&T floating solar) in either deck.

---

## 3. New Content in the BESS Deck — What Wasn't in the Original Review

The following are material findings in `cong bess session.pptx` that are **net-new** and either fill gaps or create new cross-session considerations.

### 3.1 Decision 963 New TOU (17:30–22:30 Evening Peak)

The BESS deck (Slides 14–16) models the shift from the current TOU peak window to Decision 963's 17:30–22:30 evening peak. This is directly relevant to the DPPA session: a DPPA buyer's "profile risk" (paying retail during evening peak while DPPA solar generates only at midday) is dramatically worsened by the Decision 963 shift. The BESS deck quantifies this gap and proposes BESS as the solution. Session 6.2 does not acknowledge that the TOU peak window is moving — only the BESS session does.

**Action:** Session 6.2 should cross-reference Session 4.3 on this point, or add one sentence noting that the profile risk in DPPA CfD settlement is heightened by the Decision 963 TOU shift.

### 3.2 Decree 61: BESS License Exemption for Under-3 MW Systems

Slide 9 cites Decree 61 as proposing "complete exemption of generation licenses for BESS under 3 MW, removing the biggest administrative bottleneck." This is new information not mentioned anywhere in the DPPA review. For buyers considering a hybrid on-site + DPPA strategy, this materially lowers the deployment barrier for behind-the-meter storage.

### 3.3 Firmed VPPA as a Distinct Product Category

Slides 10–11 introduce "Firmed VPPA" or "Firmed PPA" — a CfD DPPA backed by co-located battery storage, which the deck describes as achieving "100% elimination of merchant-tail risk" for the offtaker and enabling "green credit disbursement significantly easier." This is a distinct product positioning not present in Session 6.2's virtual DPPA framing, and it directly addresses the curtailment risk and profile risk that Session 6.2 warns about.

If Allotrope positions Firmed VPPA as an offering, it needs to be consistent across sessions — either Session 6.2 scopes to "unfirmed" virtual DPPA and explicitly defers to Session 4.3 for the firmed variant, or there should be a bridge slide.

### 3.4 Factory A Case Study — Four-Scenario Financial Model

Session 4.3 delivers a concrete, quantified case study that Session 6.2 lacks. Key outputs that are useful reference data for the overall workshop:

| Scenario | PV | BESS | Tariff | Clean Supply | Annual Bill Savings | Equity IRR | DSCR |
|----------|-----|------|--------|-------------|--------------------|-----------|----- |
| Case 4: Solar only | 3.45 MW | none | Decision 963 new TOU | 36% | $245k | 18.7% | — |
| Case 1: Solar + BESS | optimized | yes | Current TOU | ~60–66% | ~$500–570k | ~16–18% | ≥ 1.0 |
| Case 2: Solar + BESS | optimized | yes | Decision 963 new TOU | ~60–66% | ~$570k (+$324k vs. solar) | ~16% | ≥ 1.0 |
| Case 3: Solar + BESS | optimized | yes | New TOU + capacity charge | ~60–66% | $263k effective ($758k → $263k EVN bill) | 12.4% | 1.01 |

All four scenarios are DSCR-positive and financeable. This data reinforces the claim from Session 6.2 that viable economics exist — it just lives in a different session with a different scope.

**Note for alignment:** Session 6.2 concludes "zero of 56 scenarios pass all three gates" for grid DPPA. Session 4.3 concludes "all scenarios are financeable" for on-site solar + BESS. These are consistent (different mechanisms), but without an explicit bridge between sessions, a workshop attendee could read them as contradictory.

### 3.5 Two-Part Tariff: Capacity Charge Quantified in BESS Model

The BESS deck quantifies the capacity charge at ~209,459 VND/kW/month in its Case 3 scenario. This number is new and useful context for Session 6.2: the original review report referenced the two-part tariff as "+18% EVN bill" without a per-kW figure. The Factory A BESS model (Case 3) shows peak demand cut from 2,428 kW to 1,311 kW — a $129k/yr demand-charge saving — which directionally confirms the scale of the risk for a mid-size industrial buyer.

---

## 4. Delta Summary Table

| Gap from 15-Jun Review | Priority | Addressed in New File? | Evidence |
|------------------------|----------|----------------------|---------|
| Samsung-TTC live deal | CRITICAL | ❌ No | Neither file mentions it |
| Two-part tariff (Decree 146 Phase 3) | CRITICAL | ⚠️ Partially — BESS deck only | BESS Slides 14, 17; not in DPPA deck |
| Resolution 253 | HIGH | ❌ No | Neither file |
| Strike floor (1,012 vs 1,200) | HIGH | ❌ No | BESS deck not relevant to strike |
| Grid-service adder dominance | MEDIUM | ❌ No | Different session scope |
| "Window is empty" path to bankability | ⚠️ Partial | ⚠️ BESS firming adds one structural lever | BESS Slides 10–11 |
| Developer merchant tail nuance | MEDIUM | ❌ No | BESS deck buyer-side only |
| CBAM / supply chain documentation | MEDIUM | ❌ No | Neither file |
| Corporate buyer pipeline context | LOW | ❌ No | Neither file |
| **NEW: Decision 963 TOU shift** | HIGH | ✅ In BESS deck | BESS Slides 14–16 — should cross-ref in DPPA |
| **NEW: Firmed VPPA product framing** | HIGH | ✅ In BESS deck | BESS Slides 10–11 — cross-session alignment needed |
| **NEW: Decree 61 BESS license exemption** | MEDIUM | ✅ In BESS deck | BESS Slide 9 |
| **NEW: Factory A four-scenario model** | MEDIUM | ✅ In BESS deck | BESS Slides 14–19 |

---

## 5. Revised Recommendations (Delta-Only)

The nine recommendations from the 15-June report stand unchanged. The following are addenda based on the new BESS deck.

**R10 (NEW): Cross-reference Decision 963 TOU shift in Session 6.2**  
Add one sentence to Session 6.2's profile risk section noting that Decision 963 shifts the priced peak to 17:30–22:30 — worsening the DPPA buyer's mismatch between solar generation and load during the priced window. Point attendees to Session 4.3 for the quantified analysis.

**R11 (NEW): Explicitly scope "Firmed VPPA" to Session 4.3 — or add a bridge slide in Session 6.2**  
Session 6.2 currently ends with "the window is empty." Session 4.3 introduces BESS firming as a path to better DPPA economics. These should be explicitly linked, either by adding a handoff line at the end of Session 6.2 ("Session 4.3 covers a battery-firmed variant that addresses some of these constraints"), or by having Session 6.2 include the Firmed VPPA concept as a module.

**R12 (NEW): Align Samsung-TTC omission across BOTH sessions simultaneously**  
Adding the Samsung case study to Session 6.2 alone is insufficient — if Session 4.3 also goes out without it, a participant who attends 4.3 but not 6.2 has the same knowledge gap. A single "Vietnam DPPA: As of June 2026" slide (as recommended in R1 of the original report) should be added to both sessions as a consistent opening anchor.

---

## 6. Bottom Line

Two of the nine original gaps are partially addressed — the two-part tariff and the path to bankability — and only by the newly discovered BESS deck (Session 4.3), not by any revision to the DPPA deck (Session 6.2). The single most important gap — the Samsung SEVT × TTC deal — remains fully open in both prepared sessions.

The BESS deck is a strong addition to the CEBA workshop material on its own terms: it has the most concrete financial model (Factory A, four scenarios), the clearest regulatory update coverage (Decision 963, Decree 61, Decree 58), and the most compelling framing of bankability (Firmed VPPA). These strengths make the absence of the Samsung deal even more notable — the deck could easily anchor its "Firmed VPPA" concept to the live deal as a proof point, but it doesn't.

Both sessions need the Samsung-TTC anchor. Adding it to one without the other would leave inconsistent coverage across Allotrope's CEBA workshop presence.
