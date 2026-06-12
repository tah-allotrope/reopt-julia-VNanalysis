import os
from datetime import datetime

template_path = "assets/report-template.html"
if not os.path.exists(template_path):
    template_path = os.path.expanduser("~/.config/opencode/skills/report/assets/report-template.html")

with open(template_path, "r", encoding="utf-8") as f:
    html = f.read()

replacements = {
    "{{PHASE_NAME}}": "allotrope-template-phase-5",
    "{{DATE}}": "2026-05-06",
    "{{PROJECT}}": "reopt-pysam-vn",
    "{{REPO}}": "C:\\Users\\tukum\\Downloads\\reopt-pysam-vn",
    "{{INPUT_OUTPUT_CONTENT}}": """<div class="column-card">
  <div class="column-label">Inputs</div>
  <ul>
    <li>Deck 1, 2, 3 conformance files and PPTX artifacts</li>
    <li>Allotrope template rubric: <code>reports/decks/conformance/allotrope-template-rubric.md</code></li>
    <li>Cumulative lessons across 3-deck iteration</li>
  </ul>
</div>
<div class="column-card">
  <div class="column-label">Outputs</div>
  <ul>
    <li>Trajectory summary: <code>reports/decks/conformance/2026-05-03-allotrope-conformance-trajectory.md</code></li>
    <li>Phase 5 report: <code>reports/2026-05-06-allotrope-template-phase-5.html</code></li>
    <li>Final report: <code>reports/2026-05-06-final-allotrope-template.html</code></li>
    <li>Conformance trajectory: 46 → 53 → 56 / 60</li>
  </ul>
</div>""",
    "{{MERMAID_DIAGRAM}}": """flowchart LR
    D1[Deck 1: 46/60] --> L1[7 Lessons] --> D2[Deck 2: 53/60]
    D2 --> L2[7 Lessons] --> D3[Deck 3: 56/60]
    D3 --> L3[Trajectory Summary]
    L3 --> F[Final Report]
    style D1 fill:#666666,stroke:#666666,color:#fff
    style D2 fill:#00f5ff,stroke:#00f5ff,color:#000
    style D3 fill:#39ff14,stroke:#39ff14,color:#000
    style F fill:#ffd700,stroke:#ffd700,color:#000""",
    "{{MATH_ALGORITHM_SECTION}}": """<p><strong>Conformance Scoring:</strong> Each dimension scored 0–5, aggregate sum across 12 dimensions (max 60).</p>
<p><strong>Improvement mechanics:</strong></p>
<ul>
  <li>Deck 1 → Deck 2: +7 points (7 dimensions +1 each)</li>
  <li>Deck 2 → Deck 3: +3 points (3 dimensions +1 each, 1 visual improvement with no score change)</li>
  <li>Total: +10 points across 3-deck iteration</li>
  <li>11 of 12 dimensions improved; only D07 (charts/tables) stayed flat at 4/5</li>
</ul>""",
    "{{TOOLS_METHODS}}": """<ul>
  <li>python-pptx for PPTX generation and inspection</li>
  <li>Allotrope template rubric (12 dimensions, 0–5 scale)</li>
  <li>Markdown trajectory synthesis</li>
  <li>Report skill template flow for HTML phase and final reports</li>
</ul>""",
    "{{CHARTS_SECTION}}": """<div class="chart-frame">
  <canvas id="trajectoryChart"></canvas>
</div>
<script>
  new Chart(document.getElementById('trajectoryChart'), {
    type: 'line',
    data: {
      labels: ['Deck 1', 'Deck 2', 'Deck 3'],
      datasets: [
        { label: 'Aggregate Score', data: [46, 53, 56], borderColor: '#00f5ff', backgroundColor: 'rgba(0,245,255,0.1)', fill: true, tension: 0.3, pointRadius: 6 }
      ]
    },
    options: {
      animation: false, resizeDelay: 150, normalized: true, maintainAspectRatio: false, responsive: true,
      plugins: { legend: { labels: { color: '#e9f6ff' } }, title: { display: true, text: 'Conformance Convergence: 46 → 56 / 60', color: '#e9f6ff' } },
      scales: {
        y: { min: 40, max: 60, grid: { color: 'rgba(255,255,255,0.08)' }, ticks: { color: '#8ea3ad' } },
        x: { grid: { display: false }, ticks: { color: '#8ea3ad' } }
      }
    }
  });
</script>""",
    "{{LIMITATIONS_ALTERNATIVES}}": """<div class="summary-grid">
  <div class="column-card">
    <div class="column-label">Limitations</div>
    <ul>
      <li>Trajectory depends on manual scoring; no automated pixel-perfect comparison tool</li>
      <li>Logo image gap cannot be resolved without external assets</li>
      <li>Native chart insertion not implemented (shape-based workaround used)</li>
    </ul>
  </div>
  <div class="column-card">
    <div class="column-label">Second-Best Alternative</div>
    <ul>
      <li>Accept 56/60 as practical ceiling for text-generated decks</li>
      <li>Re-run with actual logo assets to reach 58/60</li>
      <li>Implement python-pptx native chart data model for D07</li>
    </ul>
  </div>
</div>""",
    "{{ERRORS_WARNINGS_FLAGS}}": """<ul>
  <li><strong>FLAG:</strong> D07 remained at 4/5 across all 3 decks — shape-based charts are a persistent workaround</li>
  <li><strong>FLAG:</strong> D09 peaked at 3/5 — actual logo images required for 4+</li>
</ul>""",
    "{{OPEN_QUESTIONS}}": """<ul>
  <li>Should Decks 1–3 be regenerated if Allotrope logo assets become available?</li>
  <li>Can python-pptx chart data model be added as a reusable utility?</li>
  <li>Is 56/60 sufficient for stakeholder presentation, or should manual touchup be expected?</li>
</ul>""",
}

for token, content in replacements.items():
    html = html.replace(token, content)

out_path = "reports/2026-05-06-allotrope-template-phase-5.html"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Phase report written to {out_path}")
