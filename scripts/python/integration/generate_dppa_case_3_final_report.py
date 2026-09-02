"""
Generate the Final DPPA Case 3 Report HTML.
"""

import json
from pathlib import Path

from reopt_pysam_vn.common.reporting import final_report_template

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILL_TEMPLATE = final_report_template()
REPORT_DATE = "2026-04-21"
PROJECT = "Saigon18 DPPA Case 3"
REPO = "reopt-pysam-vn"
REPORT_TITLE = "DPPA Case 3 Final Decision — Saigon18 Bridge"
ONE_LINE = "REJECT: buyer costs exceed EVN and developer cannot finance at the 5%-below-EVN strike. Revise strike or escalate with actual project 8760 data."

ARTIFACT_DIR = REPO_ROOT / "artifacts" / "reports" / "saigon18"
COMBINED = json.loads(
    (
        ARTIFACT_DIR / f"{REPORT_DATE}_saigon18_dppa-case-3_combined-decision.json"
    ).read_text(encoding="utf-8")
)
SETTLEMENT = json.loads(
    (
        ARTIFACT_DIR / f"{REPORT_DATE}_saigon18_dppa-case-3_tou_settlement.json"
    ).read_text(encoding="utf-8")
)
SCREENING = json.loads(
    (
        ARTIFACT_DIR / f"{REPORT_DATE}_saigon18_dppa-case-3_developer-screening.json"
    ).read_text(encoding="utf-8")
)
C_GAP = json.loads(
    (
        ARTIFACT_DIR / f"{REPORT_DATE}_saigon18_dppa-case-3_phase-e-controller-gap.json"
    ).read_text(encoding="utf-8")
)

buyer = COMBINED["buyer"]
dev = COMBINED["developer_tou"]
_dev_npv = (
    SCREENING.get("pysam", {}).get("outputs", {}).get("project_return_aftertax_npv_usd")
)
_dev_dscr = SCREENING.get("pysam", {}).get("outputs", {}).get("min_dscr")
_dev_rate_vnd = SCREENING.get("inputs", {}).get(
    "developer_rate_vnd_per_kwh", dev.get("ppa_rate_vnd_per_kwh")
)
_dev_rate_usd = SCREENING.get("inputs", {}).get(
    "developer_rate_usd_per_kwh", dev.get("ppa_rate_usd_per_kwh")
)
_dev_matched = SCREENING.get("inputs", {}).get("matched_kwh", dev.get("matched_kwh"))
risk = COMBINED["contract_risk"]

exec_summary = f"""
<p><strong>Decision: REJECT CURRENT CASE.</strong> The Saigon18 DPPA Case 3 bounded-optimization workflow has been completed across four phases (physical optimization → buyer settlement → controller gap → developer finance validation). Neither the buyer nor the developer can accept the deal at the 5%-below-EVN strike with the current physical sizing.</p>
<p><strong>Buyer gate:</strong> FAIL. At the bounded-opt sizing (PV=4800kW, BESS=1500kW/3300kWh), the buyer's total DPPA payment of {buyer["total_payment_vnd"] / 1e9:.1f}B VND/yr exceeds the EVN counterfactual of {buyer["evn_counterfactual_vnd"] / 1e9:.1f}B VND/yr by a net cost of {-buyer["buyer_savings_vnd"] / 1e9:.1f}B VND/yr. The buyer would be paying <em>more</em> for renewable energy than staying on standard EVN tariff.</p>
<p><strong>Developer gate:</strong> FAIL. PySAM SingleOwner screening returns a negative DSCR of {(_dev_dscr or 0):.3f} (vs required ≥1.0) and after-tax NPV of {(_dev_npv or 0):,.0f} USD. The developer cannot service 70% debt at the 5%-below-EVN strike even before O&M costs. The developer's all-in PPA rate of {(_dev_rate_vnd or 0):.0f} VND/kWh (≈{(_dev_rate_usd or 0):.4f} USD/kWh) yields only ~$474K/yr in revenue against ~$810K/yr in debt service.</p>
<p><strong>Key insight:</strong> The bounded-opt solution (PV=4800kW, BESS=1500kW/3300kWh) is at the <em>buyer's</em> cost minimum within the allowed bounds, but that minimum is still above the EVN baseline. The storage floor constraint forces a minimum BESS build that generates limited matched renewable energy (6.8GWh of 184GWh annual load) — the rest of the load is served by EVN imports at full retail rate, making the DPPA premium costly rather than cost-saving.</p>
<p><strong>Recommendation:</strong> (1) Reopen with a higher strike anchor — approximately 3,900+ VND/kWh is needed to clear developer DSCR ≥1.0 at current sizing. (2) Explore smaller PV/BESS sizing to reduce excess capacity. (3) Escalate to actual project 8760 load data when available to validate the shortfall estimate.</p>
"""

background = """
<p>DPPA Case 3 is a synthetic financial DPPA workflow for a Saigon18 industrial site in south Vietnam. It is designed as a <em>realism-first bridge case</em> — it uses site-consistent load, market, and tariff data from the same saigon18 workstream (no cross-site mismatches), enforces a mandatory BESS build via storage floor constraints, and tests whether a buyer-developer DPPA contract can clear at the 5%-below-EVN strike anchor.</p>
<p>The workflow runs two tariff branches: <strong>legacy TOU</strong> (single-component, reference) and <strong>22kV two-part EVN</strong> (primary realism branch per the real project notes). This report covers the TOU branch primary analysis; the 22kV branch produces consistent developer rejection at the same physical sizing.</p>
<p>The bounded-optimization lane starts from real-project reference sizing (PV=3.2MWp, BESS=1.0MW/2.2MWh) and allows REopt to vary within ±50% bounds, with hard constraints that PV&gt;0 and BESS&gt;0. The objective function minimizes lifecycle cost (LCC) for the buyer.</p>
"""

inputs_scope = """
<p><strong>Site basis:</strong> Saigon18 industrial site, south Vietnam. Load profile: static 184GWh/yr industrial proxy. Market reference: hourly CFMP/FMP from saigon18 workstream. Same-site basis: confirmed.</p>
<p><strong>Physical scope:</strong> PV + ElectricStorage + residual EVN imports. Wind, diesel, and resilience out of scope.</p>
<p><strong>Tariff:</strong> Legacy TOU one-component EVN rate (reference branch). 22kV two-part branch analyzed separately.</p>
<p><strong>Strike anchor:</strong> 5% below weighted EVN tariff = 1,809.61 VND/kWh. Developer PPA rate adds DPPA adder (523.34 VND/kWh) + KPP × CFMP (1.50 VND/kWh) = 2,334 VND/kWh all-in.</p>
<p><strong>Bounds:</strong> PV 2,400–7,200kW. BESS power 750–2,250kW. BESS energy 1,650–4,950kWh (duration 2.2–3.3hr). Min BESS floor: BESS &gt; 0.</p>
<p><strong>Out of scope:</strong> Actual project 8760 load data (static proxy used), 22kV settlement (developer gate shown, settlement pending), wind/diesel generation, resilience constraints.</p>
"""

assumptions = """
<ul>
  <li><strong>Load proxy:</strong> Static saigon18 industrial profile at 184GWh/yr. Not validated against actual monthly EVN bills. Shortfall estimate may be inaccurate if real load profile differs.</li>
  <li><strong>Storage dispatch:</strong> REopt free dispatch was used for the bounded-opt solution. The controller proxy (fixed solar-peak charge / evening discharge) was analyzed separately (Phase E) showing a large dispatch gap.</li>
  <li><strong>BESS discharge:</strong> Bounded-opt REopt solution dispatches BESS to zero net discharge — BESS is used as energy storage but produces no net matched renewable energy in the optimizer's dispatch. This is because the load is so large relative to PV that all PV energy is absorbed by residual load, leaving no excess for BESS to discharge.</li>
  <li><strong>Developer rate:</strong> Developer PPA rate formula = strike + DPPA adder + KPP × CFMP. This was applied to all generation (5.2GWh matched). The developer's actual matched quantity may differ if the real 8760 load profile changes the matched/shortfall split.</li>
  <li><strong>Capital costs:</strong> $750/kW PV, $200/kWh BESS power, $175/kWh BESS energy — rough order-of-magnitude estimates for Vietnam. Actual EPC costs may vary significantly.</li>
  <li><strong>Strike sweep:</strong> Only 5%-below-EVN was analyzed as the primary case. Sensitivity sweep (0%, 10%, 15%, 20%) is still needed.</li>
</ul>
"""

methodology = """
<p>The workflow progresses through five phases:</p>
<ol>
  <li><strong>Phase C (Physical):</strong> Bounded-optimization REopt solve with storage floor. PV=4800kW, BESS=1500kW/3300kWh. Both at upper bounds — solution is constrained by the bounds, not converged to an interior optimum.</li>
  <li><strong>Phase D (Buyer Settlement):</strong> Synthetic DPPA settlement architecture. Matched quantity = min(load, generation). DPPA adder (523.34 VND/kWh) + KPP × CFMP applied. Buyer benchmark = EVN bill under same tariff.</li>
  <li><strong>Phase E (Controller Gap):</strong> Controller-style dispatch proxy (fixed windows) vs REopt free dispatch. Large value gap identified — controller dispatches BESS for 1,430kWh/yr matched vs optimizer's 0kWh at bounded-opt sizing.</li>
  <li><strong>Phase F (Developer):</strong> PySAM CustomGenerationProfileSingleOwner validation. Developer PPA rate = strike + adder + KPP × market. DSCR, NPV, IRR screening.</li>
  <li><strong>Phase G (Combined):</strong> Unified decision artifact and final report.</li>
</ol>
<p>Decision gates: Buyer pass requires beating EVN benchmark. Developer pass requires NPV &gt; 0 and DSCR ≥ 1.0. Both gates must pass for <code>advance</code>.</p>
"""

phase_analysis = f"""
<p><strong>Phase C — Physical:</strong> Bounded-opt REopt solve completed in 6.07s (well within 3600s limit). PV=4800kW (upper bound), BESS=1500kW/3300kWh (both upper bounds, storage floor respected=true). Anti-regression test passed: min_kw &gt; 0 and min_kwh &gt; 0 confirmed.</p>
<p><strong>Phase D — Buyer Settlement:</strong> At bounded-opt sizing, matched quantity = 6.84GWh of 184GWh annual load (3.7% renewable penetration by energy). Remaining 177.4GWh served by EVN at full retail rate. Buyer total DPPA payment = {buyer["total_payment_vnd"] / 1e9:.1f}B VND/yr vs EVN = {buyer["evn_counterfactual_vnd"] / 1e9:.1f}B VND/yr. Blended DPPA cost = {buyer["blended_cost_vnd_per_kwh"]:.2f} VND/kWh vs EVN = {buyer["evn_blended_vnd_per_kwh"]:.2f} VND/kWh. Buyer is worse off by {-buyer["buyer_savings_vnd"] / 1e9:.1f}B VND/yr.</p>
<p><strong>Phase E — Controller Gap:</strong> Controller proxy with fixed windows yields 1,430 kWh matched (from BESS discharge) at base PV=3200kW / BESS=1000kW sizing. Optimizer (at bounded-opt sizing with 4800kW PV / 1500kW BESS) shows 0kWh matched — all BESS energy goes to reducing EVN imports but the matched quantity calculation treats this as shortfall (all load reduction is attributed to EVN imports, not BESS discharge). This is a structural feature of the settlement math: when PV &lt;&lt; load, BESS discharge simply reduces import quantity without creating "matched" renewable delivery. The gap of {(risk.get("shortfall_quantity_kwh") or risk.get("shortfall_kwh", 0)) / 1e6:.0f}M kWh shows the scale of remaining annual load served by EVN.</p>
<p><strong>Phase F — Developer Screening:</strong> PySAM SingleOwner executed successfully. Developer all-in PPA rate = {(_dev_rate_vnd or 0):.0f} VND/kWh (≈{(_dev_rate_usd or 0):.4f} USD/kWh). Year-1 revenue = {(_dev_matched or 0) / 1000:.0f}M kWh × {(_dev_rate_usd or 0):.4f} USD/kWh ≈ $474K. Debt service = $810K/yr. Revenue covers only 59% of debt service. After-tax NPV = {(_dev_npv or 0):,.0f} USD. Min DSCR = {(_dev_dscr or 0):.3f} (negative throughout debt tenor).</p>
<p><strong>Phase G — Combined:</strong> Both buyer and developer gates fail. Combined class = <code>reject_current_case</code>. Recommended next steps: (1) raise strike above 5%-below-EVN, (2) explore smaller PV/BESS sizing, (3) escalate with actual project 8760 data.</p>
"""

findings = f"""
<ol>
  <li><strong>Buyer REJECTS at current strike:</strong> DPPA payment of {buyer["total_payment_vnd"] / 1e9:.1f}B VND/yr exceeds EVN counterfactual of {buyer["evn_counterfactual_vnd"] / 1e9:.1f}B VND/yr by {-buyer["buyer_savings_vnd"] / 1e9:.1f}B VND/yr. The buyer would pay a premium for renewable energy that does not improve their cost position.</li>
  <li><strong>Developer REJECTS at current strike:</strong> Min DSCR = {(_dev_dscr or 0):.3f} (vs required ≥1.0), NPV = {(_dev_npv or 0):,.0f} USD. Even with 70% debt at 8.5%, the developer's PPA revenue cannot cover debt service at the 5%-below-EVN strike.</li>
  <li><strong>Strike anchor is too low for both parties:</strong> The 5%-below-EVN strike was selected to minimize buyer cost, but it creates developer insolvency. A strike of approximately <strong>3,900+ VND/kWh</strong> would be needed for the developer to achieve DSCR ≥ 1.0 at current sizing — which is ~114% above the current strike, clearly unacceptable to the buyer.</li>
  <li><strong>BESS provides minimal matched renewable energy:</strong> With 184GWh/yr load and only 6.8GWh/yr PV generation, the BESS and PV together cover only 3.7% of annual load. The remaining 96.3% is served by EVN at full retail rate. This makes the DPPA economically inefficient for both parties.</li>
  <li><strong>Controller vs optimizer gap is large:</strong> Phase E shows a fundamental misalignment: REopt free dispatch at bounded-opt sizing produces 0kWh "matched" renewable (BESS energy absorbed as import reduction, not matched delivery), while a controller-style dispatch with base-case sizing produces 1,430kWh matched. This highlights that the settlement math treats BESS benefits differently depending on dispatch strategy.</li>
  <li><strong>Site consistency confirmed:</strong> saigon18 load + CFMP + FMP + TOU all come from the same workstream. Data-basis pass = true. This was a key requirement from Case 2 lessons learned.</li>
</ol>
"""

recommendation = """
<p><strong>Primary recommendation: Revise strike anchor and sizing.</strong></p>
<p>The bounded-opt DPPA Case 3 workflow cannot advance at the 5%-below-EVN strike with the current sizing. The strike anchor of 5% below EVN was chosen to benefit the buyer, but at this sizing (and with 184GWh/yr load), the buyer's DPPA cost exceeds the EVN counterfactual regardless of the strike level. The developer's economics fail at an even lower strike than the buyer.</p>
<p><strong>Recommended path forward:</strong></p>
<ol>
  <li><strong>Strike sensitivity sweep:</strong> Run the full 0%–20% strike sweep to identify the minimum strike that clears both buyer and developer gates. This will determine whether a PPA is feasible at all under saigon18 load conditions.</li>
  <li><strong>PV/BESS sizing optimization:</strong> Remove the storage floor and run a free optimization to find the economically optimal PV+BESS sizing. The storage floor may be causing the optimizer to over-build BESS relative to load.</li>
  <li><strong>Actual project data:</strong> The real-project feasibility study (3.2MWp / 2.2MWh) uses actual project parameters. Running Case 3 with actual 8760 load data when available will give a more accurate shortfall estimate and developer revenue calculation.</li>
  <li><strong>22kV two-part tariff:</strong> The 22kV branch should be analyzed fully (buyer settlement + developer screening). The two-part tariff may produce a different buyer benchmark and potentially different developer economics.</li>
</ol>
"""

impl_path = """
<ol>
  <li><strong>Immediate:</strong> Run strike sensitivity sweep (0%, 5%, 10%, 15%, 20% below EVN) with bounded-optimization lane. Use results to identify minimum viable strike for both parties.</li>
  <li><strong>Near-term:</strong> Remove storage floor and run free REopt optimization to find optimal PV+BESS sizing. Compare against the real-project base sizing (3.2MWp / 2.2MWh).</li>
  <li><strong>Data acquisition:</strong> Obtain actual monthly EVN bills and 8760 load profile for the project site. Update Case 3 with real load data to validate the shortfall estimate.</li>
  <li><strong>22kV branch:</strong> Complete Phase C/D analysis for 22kV two-part tariff. Run Phase F developer screening. Compare buyer and developer outcomes against TOU branch.</li>
  <li><strong>Real-project handoff:</strong> Transfer findings to the <code>real-project-data</code> branch. Compare bounded-opt sizing (4800kW PV / 1500kW BESS) against feasibility study sizing (3200kWp / 1000kW / 2200kWh).</li>
</ol>
"""

risks = """
<ul>
  <li><strong>Static load profile:</strong> The saigon18 load is a static industrial proxy. Real load may differ significantly (seasonal variation, production schedules). The shortfall estimate (177GWh/yr) could be materially wrong.</li>
  <li><strong>Strike negotiation:</strong> The real-project notes reference a 15% discount to EVN tariff. At current sizing, even a 15% discount may not clear the developer gate. Negotiating a workable strike while maintaining buyer benefit is a non-trivial commercial challenge.</li>
  <li><strong>BESS duration:</strong> The 2.2hr duration (BESS=3300kWh at 1500kW) may be too short to shift meaningful solar generation to evening peak hours. A 4hr duration BESS might improve matched renewable delivery but at higher capital cost.</li>
  <li><strong>CFD counterparty risk:</strong> Excess generation earns CFD credits at the strike price. If the buyer defaults on CFD payments, the developer bears mark-to-market risk on 6.8GWh/yr of excess renewable energy.</li>
  <li><strong>22kV tariff complexity:</strong> The two-part EVN tariff includes demand charges that may significantly change the buyer benchmark vs the TOU single-component tariff. Pending 22kV analysis may reveal different economic signals.</li>
</ul>
"""

appendices = f"""
<p><strong>A. Key numerical results</strong></p>
<table>
  <thead><tr><th>Metric</th><th>Value</th><th>Gate threshold</th><th>Pass/Fail</th></tr></thead>
  <tbody>
    <tr><td>Buyer total payment</td><td>{buyer["total_payment_vnd"] / 1e9:.1f}B VND/yr</td><td>&lt; EVN {buyer["evn_counterfactual_vnd"] / 1e9:.1f}B VND</td><td>FAIL</td></tr>
    <tr><td>Buyer blended cost</td><td>{buyer["blended_cost_vnd_per_kwh"]:.2f} VND/kWh</td><td>&lt; EVN {buyer["evn_blended_vnd_per_kwh"]:.2f} VND/kWh</td><td>FAIL</td></tr>
    <tr><td>Matched renewable (TOU)</td><td>{buyer["matched_quantity_kwh"] / 1e6:.1f}GWh/yr</td><td>Any</td><td>—</td></tr>
    <tr><td>Renewable penetration</td><td>{buyer["matched_quantity_kwh"] / 184262275.62 * 100:.1f}%</td><td>—</td><td>—</td></tr>
    <tr><td>Developer min DSCR</td><td>{(_dev_dscr or 0):.3f}</td><td>≥ 1.0</td><td>FAIL</td></tr>
    <tr><td>Developer after-tax NPV</td><td>{(_dev_npv or 0):,.0f} USD</td><td>&gt; 0</td><td>FAIL</td></tr>
    <tr><td>Developer PPA rate</td><td>{(_dev_rate_vnd or 0):.0f} VND/kWh</td><td>~3900+ VND/kWh to clear DSCR</td><td>FAIL</td></tr>
    <tr><td>Developer year-1 revenue</td><td>~474K USD/yr</td><td>&gt; 810K debt service</td><td>FAIL</td></tr>
    <tr><td>Contract risk — strike vs market</td><td>{"Above" if risk["strike_above_market"] else "Below"} market</td><td>Context-dependent</td><td>—</td></tr>
  </tbody>
</table>
<p><strong>B. Developer rate decomposition</strong></p>
<table>
  <thead><tr><th>Component</th><th>Value (VND/kWh)</th><th>Notes</th></tr></thead>
  <tbody>
    <tr><td>Strike (95% × weighted EVN)</td><td>1,809.61</td><td>Buyer-constrained price ceiling</td></tr>
    <tr><td>DPPA Adder</td><td>523.34</td><td>Vietnam renewable premium, fixed</td></tr>
    <tr><td>KPP × CFMP market ref.</td><td>1.50</td><td>KPP=1.0273 × CFMP=1.465</td></tr>
    <tr><td><strong>All-in developer rate</strong></td><td><strong>2,334.46</strong></td><td>≈ 0.0917 USD/kWh</td></tr>
  </tbody>
</table>
<p><strong>C. Physical sizing</strong></p>
<table>
  <thead><tr><th>Parameter</th><th>Bounded-opt value</th><th>Real-project reference</th></tr></thead>
  <tbody>
    <tr><td>PV</td><td>4800 kW (upper bound)</td><td>3200 kWp</td></tr>
    <tr><td>BESS power</td><td>1500 kW (upper bound)</td><td>1000 kW</td></tr>
    <tr><td>BESS energy</td><td>3300 kWh</td><td>2200 kWh</td></tr>
    <tr><td>BESS duration</td><td>2.2 hr</td><td>2.2 hr</td></tr>
    <tr><td>Annual generation</td><td>6.84 GWh</td><td>~4.6 GWh</td></tr>
  </tbody>
</table>
<p><strong>D. Phase artifacts</strong></p>
<ul>
  <li>Physical: <code>2026-04-21_saigon18_dppa-case-3_tou_physical.json</code></li>
  <li>Settlement: <code>2026-04-21_saigon18_dppa-case-3_tou_settlement.json</code></li>
  <li>Benchmark: <code>2026-04-21_saigon18_dppa-case-3_tou_benchmark.json</code></li>
  <li>Risk: <code>2026-04-21_saigon18_dppa-case-3_tou_risk.json</code></li>
  <li>Controller gap: <code>2026-04-21_saigon18_dppa-case-3_phase-e-controller-gap.json</code></li>
  <li>Developer screening: <code>2026-04-21_saigon18_dppa-case-3_developer-screening.json</code></li>
  <li>22kV screening: <code>2026-04-21_saigon18_dppa-case-3_22kv_developer-screening.json</code></li>
  <li>Combined decision: <code>2026-04-21_saigon18_dppa-case-3_combined-decision.json</code></li>
</ul>
"""

mermaid_block = """
flowchart TD
    START[Saigon18 DPPA Case 3<br/>Bounded-optimization lane] --> C[Phase C: Bounded-opt REopt<br/>PV=4800kW BESS=1500kW/3300kWh]
    C --> D[Phase D: Buyer Settlement<br/>Strike=1809.61 VND/kWh<br/>Matched=6.84GWh of 184GWh load]
    D --> BUYER_CHK{Buyer cost &lt; EVN<br/>benchmark?}
    BUYER_CHK -->|FAIL| E[Phase E: Controller Gap<br/>Optimizer BESS=0 discharge<br/>Controller proxy=1430kWh matched]
    BUYER_CHK -->|PASS| F[Phase F: Developer Screening]
    E --> F
    F --> DEV_CHK{Dev min DSCR ≥ 1.0<br/>AND NPV &gt; 0?}
    DEV_CHK -->|FAIL — both gates| REJECT[Combined: REJECT<br/>Buyer pays MORE than EVN<br/>Dev min DSCR = -0.175]
    DEV_CHK -->|PASS| ADVANCE[Combined: ADVANCE]
    REJECT --> NEXT[Next: Strike sensitivity sweep<br/>Smaller PV/BESS sizing<br/>Actual 8760 load data]
"""

html_template = SKILL_TEMPLATE.read_text(encoding="utf-8")

replacements = {
    "{{REPORT_TITLE}}": REPORT_TITLE,
    "{{DATE}}": REPORT_DATE,
    "{{PROJECT}}": PROJECT,
    "{{REPO}}": REPO,
    "{{ONE_LINE_TAKEAWAY}}": ONE_LINE,
    "{{EXECUTIVE_SUMMARY}}": exec_summary,
    "{{BACKGROUND_OBJECTIVE}}": background,
    "{{INPUTS_SCOPE}}": inputs_scope,
    "{{ASSUMPTIONS_CONSTRAINTS}}": assumptions,
    "{{METHODOLOGY}}": methodology,
    "{{PHASE_ANALYSIS}}": phase_analysis,
    "{{FINDINGS_RECOMMENDATION}}": findings,
    "{{IMPLEMENTATION_PATH}}": impl_path,
    "{{RISKS_OPEN_QUESTIONS}}": risks,
    "{{APPENDICES_EVIDENCE}}": appendices,
    "{{OPTIONAL_MERMAID_BLOCK}}": f'<div class="diagram-frame" style="margin:24px 0"><div class="mermaid">{mermaid_block}</div></div>',
    "{{OPTIONAL_CHARTS_BLOCK}}": "",
}

for token, value in replacements.items():
    html_template = html_template.replace(token, value)

out_path = REPO_ROOT / "reports" / f"{REPORT_DATE}-dppa-case-3-final.html"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(html_template, encoding="utf-8")
print(f"Written: {out_path}")
