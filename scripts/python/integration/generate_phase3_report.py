import os
from datetime import datetime

template_path = "assets/report-template.html"
if not os.path.exists(template_path):
    # Fallback to skill assets
    template_path = os.path.expanduser("~/.config/opencode/skills/report/assets/report-template.html")

with open(template_path, "r", encoding="utf-8") as f:
    html = f.read()

replacements = {
    "{{PHASE_NAME}}": "allotrope-template-phase-3",
    "{{DATE}}": "2026-05-06",
    "{{PROJECT}}": "reopt-pysam-vn",
    "{{REPO}}": "C:\\Users\\tukum\\Downloads\\reopt-pysam-vn",
    "{{INPUT_OUTPUT_CONTENT}}": """<div class="column-card">
  <div class="column-label">Inputs</div>
  <ul>
    <li>Case 2 final HTML report: <code>reports/2026-04-16-dppa-case-2-final.html</code></li>
    <li>Allotrope template rubric: <code>reports/decks/conformance/allotrope-template-rubric.md</code></li>
    <li>Deck 1 conformance file with 7 lessons to carry forward</li>
  </ul>
</div>
<div class="column-card">
  <div class="column-label">Outputs</div>
  <ul>
    <li>Deck 2 PPTX: <code>reports/decks/2026-04-16-dppa-case-2.pptx</code> (10 slides)</li>
    <li>Conformance file: <code>reports/decks/conformance/2026-04-16-dppa-case-2-conformance.md</code></li>
    <li>Conformance score: <strong>53/60</strong> (+7 vs Deck 1)</li>
  </ul>
</div>""",
    "{{MERMAID_DIAGRAM}}": """flowchart LR
    A[Read Deck 1 Lessons] --> B[Generate Deck 2 PPTX]
    B --> C[Inspect with python-pptx]
    C --> D[Score against Rubric]
    D --> E[Write Conformance File]
    E --> F[Compare Deck 1 vs Deck 2]
    style B fill:#00f5ff,stroke:#00f5ff,color:#000
    style D fill:#39ff14,stroke:#39ff14,color:#000""",
    "{{MATH_ALGORITHM_SECTION}}": """<p><strong>Conformance Scoring:</strong> Each dimension scored 0–5 using median across applicable slides. Aggregate = sum of 12 dimensions (max 60).</p>
<p><strong>Deck 2 Improvements (applied from Deck 1 lessons):</strong></p>
<ul>
  <li>Slide numbers added (Cabin 8pt, bottom-right)</li>
  <li>Executive Summary uses structured table format (5 rows × 2 cols)</li>
  <li>Three section dividers: Context, Analysis, Next Steps</li>
  <li>Exact hex colors locked from rubric palette</li>
  <li>Card body font size increased to 11pt</li>
  <li>Green rule line accent (#38761D) on every slide</li>
</ul>""",
    "{{TOOLS_METHODS}}": """<ul>
  <li>python-pptx (Presentation, shapes, tables, RGBColor)</li>
  <li>Allotrope template rubric (12 dimensions, 0–5 scale)</li>
  <li>Manual slide-by-slide inspection with python-pptx programmatic checks</li>
</ul>""",
    "{{CHARTS_SECTION}}": """<div class="chart-frame">
  <canvas id="conformanceChart"></canvas>
</div>
<script>
  new Chart(document.getElementById('conformanceChart'), {
    type: 'bar',
    data: {
      labels: ['D01','D02','D03','D04','D05','D06','D07','D08','D09','D10','D11','D12'],
      datasets: [
        { label: 'Deck 1', data: [4,4,4,4,4,4,4,4,2,4,4,4], backgroundColor: '#666666' },
        { label: 'Deck 2', data: [4,5,5,5,5,5,4,5,2,5,4,5], backgroundColor: '#00f5ff' }
      ]
    },
    options: {
      animation: false, resizeDelay: 150, normalized: true, maintainAspectRatio: false, responsive: true,
      plugins: { legend: { labels: { color: '#e9f6ff' } } },
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
      <li>Footer appears on cover slide (template convention excludes it)</li>
      <li>No embedded charts — only tables used</li>
      <li>Closing slide lacks full teal background</li>
    </ul>
  </div>
  <div class="column-card">
    <div class="column-label">Second-Best Alternative</div>
    <ul>
      <li>Post-process .pptx with python-pptx to suppress footer on cover</li>
      <li>Use matplotlib to generate simple chart images and embed them</li>
      <li>Apply full slide background fill on closing slide</li>
    </ul>
  </div>
</div>""",
    "{{ERRORS_WARNINGS_FLAGS}}": """<ul>
  <li><strong>FIXED:</strong> ImportError for RgbColor → corrected to RGBColor</li>
  <li><strong>FIXED:</strong> AttributeError on TextFrame.add_run → corrected to paragraph.add_run</li>
  <li><strong>WARN:</strong> Green rule line shape appears in color inspection as #38761D — confirmed correct</li>
</ul>""",
    "{{OPEN_QUESTIONS}}": """<ul>
  <li>Can we source the actual Allotrope logo SVG/PNG for Deck 3?</li>
  <li>Should Deck 3 suppress footer on cover and section divider slides?</li>
  <li>Can we add a simple bar chart to the Results slide for Deck 3?</li>
  <li>Will Deck 3 apply full teal background on closing slide?</li>
  <li>Next: Phase 4 (Deck 3) applying cumulative lessons from Decks 1+2</li>
</ul>""",
}

for token, content in replacements.items():
    html = html.replace(token, content)

out_path = "reports/2026-05-06-allotrope-template-phase-3.html"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Report written to {out_path}")
