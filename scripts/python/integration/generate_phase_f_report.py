"""
Generate Phase F HTML report for Saigon18 DPPA Case 3.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILL_TEMPLATE = (
    Path.home()
    / ".config"
    / "opencode"
    / "skills"
    / "report"
    / "assets"
    / "report-template.html"
)

REPORT_DATE = "2026-04-21"
PROJECT = "Saigon18 DPPA Case 3"
REPO = "reopt-pysam-vn"
PHASE_NAME = "dppa-case-3-phase-f"

screening = json.loads(
    (
        REPO_ROOT
        / "artifacts/reports/saigon18/2026-04-21_saigon18_dppa-case-3_developer-screening.json"
    ).read_text(encoding="utf-8")
)

pysam = screening["pysam"]
outputs = pysam.get("outputs", {})
inputs = screening["inputs"]
decision = screening["decision"]

annual_cfs = pysam.get("annual_cashflows", [])

decline_reason_lines = [
    f"Min DSCR = {decision.get('min_dscr', 0):.3f} — deeply negative throughout debt tenor (years 1-10), indicating annual revenue is structurally insufficient to cover debt service even before O&M.",
    f"After-tax NPV = {outputs.get('project_return_aftertax_npv_usd', 0):,.0f} USD — project destroys value at the 5%-below-EVN strike.",
    f"Year-1 revenue = {annual_cfs[0]['total_revenue_usd']:,.0f} USD vs debt service = {annual_cfs[0]['debt_service_usd']:,.0f} USD — revenue covers only {annual_cfs[0]['total_revenue_usd'] / annual_cfs[0]['debt_service_usd'] * 100:.0f}% of debt service.",
    "Negative DSCR confirms the bounded-opt case fails the developer solvency test at the buyer-constrained strike.",
]

input_output_content = f"""
<div class="column-card">
  <h3 class="column-label">Inputs</h3>
  <ul>
    <li>PV: {inputs["pv_size_kw"]:,.0f} kW / BESS: {inputs["bess_size_kw"]:,.0f} kW / {inputs["bess_size_kwh"]:,.0f} kWh</li>
    <li>Capital cost: {inputs["capital_cost_usd"]:,.0f} USD</li>
    <li>Annual generation: {inputs["annual_gen_kwh"]:,.0f} kWh</li>
    <li>Developer rate: {inputs["developer_rate_vnd_per_kwh"]:,.2f} VND/kWh ({inputs["developer_rate_usd_per_kwh"]:.4f} USD/kWh)</li>
    <li>Strike: {inputs["strike_vnd_per_kwh"]:,.2f} VND/kWh | DPPA adder: {inputs["dppa_adder_vnd_per_kwh"]:,.2f} | KPP×CFMP: {inputs["market_price_vnd_per_kwh"] * inputs["kpp_factor"]:.4f} VND/kWh</li>
    <li>Fixed O&M: {inputs["fixed_om_usd_per_year"]:,.0f} USD/yr | Debt: {inputs["debt_fraction"] * 100:.0f}% | Discount: {inputs["developer_discount_rate"] * 100:.0f}%</li>
  </ul>
</div>
<div class="column-card">
  <h3 class="column-label">Output</h3>
  <ul>
    <li>Decision: <strong style="color:#ff4d4d">REJECT_CURRENT_CASE</strong></li>
    <li>After-tax NPV: {outputs.get("project_return_aftertax_npv_usd", "N/A"):,.0f} USD</li>
    <li>Min DSCR: {decision.get("min_dscr", 0):.3f} (negative throughout debt period)</li>
    <li>IRR: {outputs.get("project_return_aftertax_irr_fraction", "N/A")} (not achievable)</li>
    <li>Debt sized: {outputs.get("size_of_debt_usd", 0):,.0f} USD (108% of installed cost — PySAM sized to max leverage at target IRR, still fails)</li>
    <li>Year-1 revenue: {annual_cfs[0]["total_revenue_usd"]:,.0f} USD vs debt service {annual_cfs[0]["debt_service_usd"]:,.0f} USD</li>
  </ul>
</div>
"""

mermaid_diagram = """
flowchart TD
    A[ bounded-opt REopt solve<br/>PV=4800kW BESS=1500kW/3300kWh ] --> B[Build developer PPA rate]
    B --> C[strike = 95% × weighted EVN = 1809.61 VND/kWh]
    C --> D[developer_rate = strike + DPPA_adder + KPP × CFMP<br/>= 1809.61 + 523.34 + 1.50 = 2334.46 VND/kWh]
    D --> E[PySAM SingleOwner execute]
    E --> F{revenue ≥ debt_service + O&M?}
    F -->|No| G[REJECT: min_dscr = -0.175<br/>NPV = -$6.05M]
    F -->|Yes| H[ADVANCE: check NPV ≥ 0<br/>and DSCR ≥ 1.0]
    G --> I[Buyer strike too low at PV max.<br/>BESS floor binding → no upside.]
"""

math_section = """
<p style="margin-top:0">The developer PPA rate is the sum of three components:</p>
<table>
  <thead><tr><th>Component</th><th>Value (VND/kWh)</th><th>Notes</th></tr></thead>
  <tbody>
    <tr><td>Strike (95% × weighted EVN)</td><td>1,809.61</td><td>Buyer cost ceiling constraint</td></tr>
    <tr><td>DPPA Adder</td><td>523.34</td><td>Vietnam renewable premium, fixed</td></tr>
    <tr><td>KPP × CFMP market ref.</td><td>1.50</td><td>KPP=1.0273 × CFMP=1.465 VND/kWh</td></tr>
    <tr><td><strong>Total developer rate</strong></td><td><strong>2,334.46</strong></td><td>≈ 0.0917 USD/kWh</td></tr>
  </tbody>
</table>
<p><strong>Revenue = generation_kwh × developer_rate_usd</strong></p>
<p>Year 1 revenue = 5,224,499 kWh × 0.0917 USD/kWh = <strong>~479,000 USD</strong></p>
<p>Annual debt service (70% LTV, 8.5%, 10yr on $5.3M) ≈ <strong>810,000 USD</strong></p>
<p>→ Revenue / Debt service = 59% → structurally insolvent regardless of tax benefits</p>
"""

tools_section = """
<ul>
  <li><code>reopt_pysam_vn.pysam.single_owner</code> — PySAM CustomGenerationProfileSingleOwner wrapper with Vietnam defaults (zero ITC/PTC, zero bonus depreciation, MACRS-5)</li>
  <li><code>reopt_pysam_vn.integration.dppa_case_3</code> — Saigon18 TOU tariff, CFMP/FMP series, load series</li>
  <li><code>PySAM.Singleowner</code> — debt-sizing mode <code>ppa_soln_mode=1</code> (PySAM maximizes leverage to hit target IRR)</li>
  <li><code>PySAM.CustomGeneration</code> — hourly generation profile from bounded-opt PV delivery series</li>
</ul>
<p>Key parameters: analysis_years=20, debt_fraction=70%, real_discount_rate=8%, debt_interest=8.5%, tenor=10yr, inflation=4%, PPA_escalation=4%.</p>
"""

decline_note = (
    "The bounded-opt case was buyer-constrained: the 5% below EVN strike "
    "was accepted to minimize buyer cost, leaving the developer with economics "
    "that cannot support debt. This is the expected outcome of the strike-anchor "
    "workflow: Phase C locks in buyer-optimized physicals; Phase F tests whether "
    "the developer can finance them at that price."
)

charts_section = (
    """
<div class="chart-frame" style="height:320px">
  <canvas id="revenueVsDebtChart"></canvas>
</div>
<div class="chart-frame" style="height:320px; margin-top:16px">
  <canvas id="dscrChart"></canvas>
</div>
<script>
(function() {
  const cfs = """
    + json.dumps(annual_cfs, ensure_ascii=False)
    + """;
  const labels = cfs.map(r => 'Yr ' + r.year);
  const revenues = cfs.map(r => r.total_revenue_usd / 1000);
  const debtSvc = cfs.map(r => r.debt_service_usd / 1000);
  const dscrs = cfs.map(r => r.dscr);

  Chart.defaults.devicePixelRatio = 1;
  Chart.defaults.animation = false;
  Chart.defaults.resizeDelay = 150;
  Chart.defaults.normalized = true;
  Chart.defaults.maintainAspectRatio = false;

  const rvChart = new Chart(document.getElementById('revenueVsDebtChart'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        { label: 'Revenue (kUSD)', data: revenues, backgroundColor: 'rgba(0,245,255,0.7)', borderColor: '#00f5ff', borderWidth: 1 },
        { label: 'Debt Service (kUSD)', data: debtSvc, backgroundColor: 'rgba(255,77,77,0.7)', borderColor: '#ff4d4d', borderWidth: 1 }
      ]
    },
    options: {
      responsive: true,
      plugins: { title: { display: true, text: 'Revenue vs Debt Service (kUSD/yr)', color: '#e9f6ff' }, legend: { labels: { color: '#e9f6ff' } } },
      scales: { x: { ticks: { color: '#8ea3ad' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#8ea3ad' }, grid: { color: 'rgba(255,255,255,0.05)' } } }
    }
  });

  const dscrChart = new Chart(document.getElementById('dscrChart'), {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{ label: 'DSCR', data: dscrs, borderColor: '#ff4d4d', backgroundColor: 'rgba(255,77,77,0.15)', borderWidth: 2, fill: true, tension: 0.3 }]
    },
    options: {
      responsive: true,
      plugins: { title: { display: true, text: 'Debt Service Coverage Ratio (DSCR)', color: '#e9f6ff' }, legend: { labels: { color: '#e9f6ff' } }, annotation: { annotations: { hline: { type: 'line', yMin: 1, yMax: 1, borderColor: '#39ff14', borderWidth: 1, borderDash: [4,4] } } } },
      scales: { x: { ticks: { color: '#8ea3ad' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#8ea3ad' }, grid: { color: 'rgba(255,255,255,0.05)' } } }
    }
  });
})();
</script>
"""
)

limitations_alternatives = """
<p style="margin-top:0"><strong>Why this happened:</strong> At the buyer-optimized strike (5% below EVN), the developer's total PPA rate of 2,334 VND/kWh yields ~479K USD/yr in revenue. The project's 70% debt financing (sized at $5.3M by PySAM's IRR-targeting algorithm) requires ~$810K/yr in debt service — a 41% shortfall before O&M. The negative DSCR (-0.175) confirms structural insolvency.</p>
<p><strong>Second-best path:</strong> Raise the strike above the 5% discount threshold. The developer's rate needs to reach approximately <strong>3,900+ VND/kWh</strong> (≈ $0.153/kWh) at current capital costs to achieve a 1.0 DSCR at 70% leverage. This would increase buyer cost but unlock developer financing. Alternatively, increase project size to spread fixed costs over more generation.</p>
<p><strong>Note:</strong> The bounded-opt solution is at the <em>buyer's</em> cost minimum — Phase F reveals the developer cannot finance at that price. This is not a model failure; it is the correct output of the Phase F gate.</p>
"""

errors_section = """
<ul>
  <li><strong>PySAM tuple attrs (pre-fix):</strong> <code>ppa_price_input</code> and <code>depr_custom_schedule</code> required tuple/list conversion — fixed by using existing <code>single_owner.py</code> wrapper which handles all type conversions correctly.</li>
  <li><strong>LSP false positives:</strong> All 50+ LSP type errors in <code>single_owner.py</code> and <code>analyze_saigon18_dppa_case_3_phase_f.py</code> are PySAM dynamic-attribute false positives — runtime succeeds after each fix.</li>
  <li><strong>IRR=None:</strong> PySAM returns null IRR when cashflows never cross into positive cumulative territory — consistent with deeply negative NPV.</li>
  <li><strong>Result validity:</strong> Model executed successfully to completion with <code>status: ok</code>. Outputs are economically meaningful (negative DSCR, -$6M NPV).</li>
</ul>
"""

open_questions = """
<ul>
  <li><strong>What strike enables developer financing?</strong> Phase G combined decision should estimate the minimum developer rate (at PV=4800kW, BESS=1500kW/3300kWh) that achieves DSCR ≥ 1.0 and NPV ≥ 0.</li>
  <li><strong>22kV branch:</strong> The 22kV two-part EVN tariff branch bounded-opt results are available — confirm they reach Phase G comparison.</li>
  <li><strong>Phase G:</strong> The final combined decision should synthesize: buyer settlement (TOU), developer rejection (Phase F), and risk profile (Phase CD) into a single recommendation.</li>
  <li><strong>Real project data:</strong> The 3.2 MWp / 2.2 MWh feasibility study parameters are on the <code>real-project-data</code> branch — compare against bounded-opt sizing for commercial validation.</li>
</ul>
"""

html_content = SKILL_TEMPLATE.read_text(encoding="utf-8")

replacements = {
    "{{PHASE_NAME}}": PHASE_NAME,
    "{{DATE}}": REPORT_DATE,
    "{{PROJECT}}": PROJECT,
    "{{REPO}}": REPO,
    "{{INPUT_OUTPUT_CONTENT}}": input_output_content,
    "{{MERMAID_DIAGRAM}}": mermaid_diagram,
    "{{MATH_ALGORITHM_SECTION}}": math_section,
    "{{TOOLS_METHODS}}": tools_section,
    "{{CHARTS_SECTION}}": charts_section,
    "{{LIMITATIONS_ALTERNATIVES}}": limitations_alternatives,
    "{{ERRORS_WARNINGS_FLAGS}}": errors_section,
    "{{OPEN_QUESTIONS}}": open_questions,
}

for token, value in replacements.items():
    html_content = html_content.replace(token, value)

out_path = REPO_ROOT / "reports" / f"{REPORT_DATE}-{PHASE_NAME}.html"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(html_content, encoding="utf-8")
print(f"Written: {out_path}")
