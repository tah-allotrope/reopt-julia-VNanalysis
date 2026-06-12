import os
from datetime import datetime

template_path = "assets/report-template.html"
if not os.path.exists(template_path):
    template_path = os.path.expanduser("~/.config/opencode/skills/report/assets/report-template.html")

with open(template_path, "r", encoding="utf-8") as f:
    html = f.read()

replacements = {
    "{{PHASE_NAME}}": "allotrope-template-phase-4",
    "{{DATE}}": "2026-05-06",
    "{{PROJECT}}": "reopt-pysam-vn",
    "{{REPO}}": "C:\\Users\\tukum\\Downloads\\reopt-pysam-vn",
    "{{INPUT_OUTPUT_CONTENT}}": """<div class="column-card">
  <div class="column-label">Inputs</div>
  <ul>
    <li>Case 3 final HTML report: <code>reports/2026-04-21-dppa-case-3-final.html</code></li>
    <li>Allotrope template rubric: <code>reports/decks/conformance/allotrope-template-rubric.md</code></li>
    <li>Deck 1 and Deck 2 conformance files with cumulative lessons</li>
  </ul>
</div>
<div class="column-card">
  <div class="column-label">Outputs</div>
  <ul>
    <li>Deck 3 PPTX: <code>reports/decks/2026-04-21-dppa-case-3.pptx</code> (10 slides)</li>
    <li>Conformance file: <code>reports/decks/conformance/2026-04-21-dppa-case-3-conformance.md</code></li>
    <li>Conformance score: <strong>56/60</strong> (+3 vs Deck 2, +10 vs Deck 1)</li>
    <li>Cumulative trajectory table across all 3 decks</li>
  </ul>
</div>""",
    "{{MERMAID_DIAGRAM}}": """flowchart LR
    A[Read Deck 1+2 Lessons] --> B[Generate Deck 3 PPTX]
    B --> C[Suppress cover footer]
    B --> D[Add bar chart shapes]
    B --> E[Full teal closing bg]
    B --> F[Partner logo placeholders]
    C --> G[Inspect with python-pptx]
    D --> G
    E --> G
    F --> G
    G --> H[Score against Rubric]
    H --> I[Write Conformance + Trajectory]
    style B fill:#00f5ff,stroke:#00f5ff,color:#000
    style I fill:#39ff14,stroke:#39ff14,color:#000""",
    "{{MATH_ALGORITHM_SECTION}}": """<p><strong>Conformance Scoring:</strong> Each dimension scored 0–5 using median across applicable slides. Aggregate = sum of 12 dimensions (max 60).</p>
<p><strong>Deck 3 New Improvements (applied from Deck 2 lessons):</strong></p>
<ul>
  <li>Footer suppressed on cover slide (D01 +1, D08 maintained)</li>
  <li>Simple bar chart shapes added to Financial Summary slide (D07 maintained at 4, visual improvement)</li>
  <li>Full teal background (#155B55) on closing slide (D11 +1)</li>
  <li>Partner logo text placeholders on cover and closing (D09 +1)</li>
</ul>
<p><strong>Cumulative improvements across 3 decks:</strong> 11 of 12 dimensions improved by +1. Only D07 (charts/tables) remained at 4/5 across all decks because shape-based charts are used instead of native chart objects.</p>""",
    "{{TOOLS_METHODS}}": """<ul>
  <li>python-pptx (Presentation, shapes, tables, RGBColor)</li>
  <li>Allotrope template rubric (12 dimensions, 0–5 scale)</li>
  <li>Manual slide-by-slide inspection with python-pptx programmatic checks</li>
  <li>Shape-based bar chart representation (rectangles with scaled widths)</li>
</ul>""",
    "{{CHARTS_SECTION}}": """<div class="chart-frame">
  <canvas id="trajectoryChart"></canvas>
</div>
<script>
  new Chart(document.getElementById('trajectoryChart'), {
    type: 'bar',
    data: {
      labels: ['D01','D02','D03','D04','D05','D06','D07','D08','D09','D10','D11','D12'],
      datasets: [
        { label: 'Deck 1', data: [4,4,4,4,4,4,4,4,2,4,4,4], backgroundColor: '#666666' },
        { label: 'Deck 2', data: [4,5,5,5,5,5,4,5,2,5,4,5], backgroundColor: '#00f5ff' },
        { label: 'Deck 3', data: [5,5,5,5,5,5,4,5,3,5,5,5], backgroundColor: '#39ff14' }
      ]
    },
    options: {
      animation: false, resizeDelay: 150, normalized: true, maintainAspectRatio: false, responsive: true,
      plugins: { legend: { labels: { color: '#e9f6ff' } }, title: { display: true, text: 'Conformance Trajectory: 46 → 53 → 56 / 60', color: '#e9f6ff' } },
      scales: {
        y: { max: 5, grid: { color: 'rgba(255,255,255,0.08)' }, ticks: { color: '#8ea3ad' } },
        x: { grid: { display: false }, ticks: { color: '#8ea3ad' } }
      }
    }
  });
</script>""",
    "{{LIMITATIONS_ALTERNATIVES}}": """<div class="summary-grid">
  <div class="column-card">
    <div class="column-label">Limitations</div>
    <ul>
      <li>No actual Allotrope logo image available — text placeholder only</li>
      <li>Bar charts use rectangle shapes, not native PowerPoint chart objects</li>
      <li>Partner logos are text placeholders, not actual logo images</li>
      <li>Deck 3 cannot exceed 56/60 without external image assets</li>
    </ul>
  </div>
  <div class="column-card">
    <div class="column-label">Second-Best Alternative</div>
    <ul>
      <li>Use python-pptx chart data model to insert native bar charts</li>
      <li>Source actual Allotrope + partner logo PNG/SVG files</li>
      <li>Accept 56/60 as the practical ceiling for text-generated decks</li>
    </ul>
  </div>
</div>""",
    "{{ERRORS_WARNINGS_FLAGS}}": """<ul>
  <li><strong>WARN:</strong> Green rule line on closing slide is visually subdued against full teal background — acceptable but not ideal</li>
  <li><strong>FLAG:</strong> Shape-based charts are not editable as charts in PowerPoint — user must re-create if data changes</li>
</ul>""",
    "{{OPEN_QUESTIONS}}": """<ul>
  <li>Can we source the actual Allotrope logo SVG/PNG for a future re-run?</li>
  <li>Should we implement native python-pptx chart insertion for D07?</li>
  <li>Next: Phase 5 trajectory summary <code>2026-05-03-allotrope-conformance-trajectory.md</code></li>
  <li>Should the 3 decks be regenerated with logo images once assets are available?</li>
</ul>""",
}

for token, content in replacements.items():
    html = html.replace(token, content)

out_path = "reports/2026-05-06-allotrope-template-phase-4.html"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Report written to {out_path}")
