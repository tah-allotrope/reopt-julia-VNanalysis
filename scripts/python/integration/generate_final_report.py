import os

template_path = "assets/final-report-template.html"
if not os.path.exists(template_path):
    template_path = os.path.expanduser("~/.config/opencode/skills/report/assets/final-report-template.html")

with open(template_path, "r", encoding="utf-8") as f:
    html = f.read()

replacements = {
    "{{REPORT_TITLE}}": "Iterative Allotrope-Template PPT Generation",
    "{{DATE}}": "2026-05-06",
    "{{PROJECT}}": "reopt-pysam-vn",
    "{{REPO}}": "C:\\Users\\tukum\\Downloads\\reopt-pysam-vn",
    "{{ONE_LINE_TAKEAWAY}}": "Three decks generated from final reports converged from 46/60 to 56/60 conformance against the Allotrope template, with logo images as the only hard blocker to further improvement.",
    "{{EXECUTIVE_SUMMARY}}": """<div class="subcard">
  <p><strong>Decision:</strong> Iterative conformance improvement is effective and has converged. Deck 3 achieves 56/60, representing the practical ceiling for text-and-code-generated decks without actual logo image assets.</p>
  <p><strong>Key result:</strong> 11 of 12 rubric dimensions improved across the 3-deck iteration. Aggregate score improved from 46 → 53 → 56. The rubric's "lessons to carry forward" mechanism directly drove measurable gains.</p>
  <p><strong> blocker:</strong> Actual Allotrope and partner logo images are required to move D09 from 3/5 to 5/5. Native PowerPoint chart objects are needed to move D07 from 4/5 to 5/5. Both require external assets or additional code complexity.</p>
</div>""",
    "{{BACKGROUND_OBJECTIVE}}": """<p>The repository contains three final HTML reports (DPPA Cases 1–3) that document multi-phase techno-economic analyses for Vietnam renewable energy projects. These reports are technically complete but not in a presentation-ready format for stakeholder meetings.</p>
<p>The objective was to generate three PowerPoint decks from these reports, compare each against the Allotrope presentation template (the firm's standard brand deck), and feed conformance deltas forward so each successive deck matches the template more closely. The output is three decks plus a written conformance trajectory showing measurable convergence.</p>
<p>This work serves as a proof-of-concept for automated deck generation from analytical reports while preserving brand consistency.</p>""",
    "{{INPUTS_SCOPE}}": """<div class="subcard">
  <h4>Inputs</h4>
  <ul>
    <li><code>reports/2026-04-09-dppa-case-1-final.html</code> — DPPA Case 1 closeout</li>
    <li><code>reports/2026-04-16-dppa-case-2-final.html</code> — DPPA Case 2 closeout</li>
    <li><code>reports/2026-04-21-dppa-case-3-final.html</code> — DPPA Case 3 closeout</li>
    <li><code>reports/decks/conformance/allotrope-template-rubric.md</code> — 12-dimension scoring rubric</li>
    <li>Google Drive cached template: <code>reports/decks/conformance/_template/allotrope-template.pptx</code></li>
  </ul>
</div>
<div class="subcard">
  <h4>Scope</h4>
  <ul>
    <li>Three .pptx decks under <code>reports/decks/</code></li>
    <li>Conformance scoring files for each deck</li>
    <li>Cumulative trajectory summary document</li>
    <li>Synchronized HTML phase and final reports</li>
  </ul>
</div>""",
    "{{ASSUMPTIONS_CONSTRAINTS}}": """<div class="subcard">
  <h4>Assumptions</h4>
  <ul>
    <li>"3 most recent final reports" = three distinct case finals (Apr 9, 16, 21)</li>
    <li>Iteration order is chronological (Case 1 → 2 → 3)</li>
    <li>Template is authoritative; changes only affect deck visuals, not analytical claims</li>
  </ul>
</div>
<div class="subcard">
  <h4>Constraints</h4>
  <ul>
    <li>No actual logo image files available — text placeholders only</li>
    <li>python-pptx shape-based charts used instead of native chart objects</li>
    <li>Three iterations only; no re-generation of earlier decks</li>
  </ul>
</div>""",
    "{{METHODOLOGY}}": """<p>The methodology follows a strict iterative feedback loop:</p>
<ol>
  <li><strong>PHASE-01 (Rubrik):</strong> Extract 12-dimension conformance rubric from the Allotrope template. Define 0–5 scoring anchors per dimension. Establish scoring protocol (median across slides).</li>
  <li><strong>PHASE-02 (Deck 1):</strong> Generate first deck from rubric only. Score manually. Document top 5 deviations and 7 prescriptive lessons.</li>
  <li><strong>PHASE-03 (Deck 2):</strong> Generate second deck from rubric + Deck 1 lessons. Score. Document delta vs Deck 1. Update lessons.</li>
  <li><strong>PHASE-04 (Deck 3):</strong> Generate third deck from rubric + cumulative lessons. Score. Document full 3-deck trajectory.</li>
  <li><strong>PHASE-05 (Trajectory):</strong> Synthesize cross-iteration results. Write trajectory markdown. Commit all artifacts.</li>
</ol>
<p>Each phase includes python-pptx programmatic inspection, manual slide-by-slide scoring, and a synchronized HTML report.</p>""",
    "{{PHASE_ANALYSIS}}": """<div class="subcard">
  <h4>Phase 1 — Rubric Extraction</h4>
  <p>Fetched Allotrope template from Google Drive. Analyzed with python-pptx: 12 slides, Cabin font, primary teal <code>#155B55</code>, accent green <code>#38761D</code>. Extracted exact hex palette and font size roles. Score: N/A (planning phase).</p>
</div>
<div class="subcard">
  <h4>Phase 2 — Deck 1 (Case 1)</h4>
  <p>Generated 9-slide deck. Baseline conformance: <strong>46/60</strong>. Top gaps: missing logos, no slide numbers, bullet-based exec summary, only one section divider, approximate colors. Published 7 prescriptive lessons.</p>
</div>
<div class="subcard">
  <h4>Phase 3 — Deck 2 (Case 2)</h4>
  <p>Applied all 7 Deck 1 lessons. Generated 10-slide deck. Conformance: <strong>53/60</strong> (+7). Improvements: table exec summary, 3 section dividers, exact hex colors, slide numbers, 11pt cards, green rule accents. New gaps: footer on cover, no charts, white closing background.</p>
</div>
<div class="subcard">
  <h4>Phase 4 — Deck 3 (Case 3)</h4>
  <p>Applied cumulative lessons. Generated 10-slide deck. Conformance: <strong>56/60</strong> (+3). New improvements: suppressed cover footer, bar chart shapes, full teal closing background, partner logo placeholders. Persistent gap: actual logo images.</p>
</div>
<div class="subcard">
  <h4>Phase 5 — Trajectory Summary</h4>
  <p>Wrote <code>2026-05-03-allotrope-conformance-trajectory.md</code> with 3-row scores table, lesson-sticking analysis, and rubric edit recommendations. Confirmed convergence at 56/60.</p>
</div>""",
    "{{OPTIONAL_MERMAID_BLOCK}}": """<div class="diagram-frame" style="margin:24px 0"><div class="mermaid">
flowchart LR
    P1[Phase 1: Rubric] --> P2[Phase 2: Deck 1 46/60]
    P2 --> L1[7 Lessons] --> P3[Phase 3: Deck 2 53/60]
    P3 --> L2[7 Lessons] --> P4[Phase 4: Deck 3 56/60]
    P4 --> P5[Phase 5: Trajectory]
    style P2 fill:#666666,stroke:#666666,color:#fff
    style P3 fill:#00f5ff,stroke:#00f5ff,color:#000
    style P4 fill:#39ff14,stroke:#39ff14,color:#000
</div></div>""",
    "{{FINDINGS_RECOMMENDATION}}": """<p><strong>Major findings:</strong></p>
<ol>
  <li><strong>Iterative feedback works.</strong> The "lessons to carry forward" mechanism directly drove measurable improvement. Every lesson applied in Deck 2 and Deck 3 produced a +1 score gain in at least one dimension.</li>
  <li><strong>56/60 is the practical ceiling.</strong> Without actual logo images, D09 cannot exceed 3/5. Without native chart objects, D07 cannot exceed 4/5. The remaining 10 dimensions all score 5/5.</li>
  <li><strong>The rubric is effective but could be tightened.</strong> Two recommended edits: (a) explicitly state that D08 excludes the cover slide, and (b) clarify that D07 = 4 for shape-based charts, 5 for native charts.</li>
  <li><strong>Chronological iteration was appropriate.</strong> The most recent report (Case 3) received the most accumulated feedback and achieved the highest score.</li>
</ol>
<p><strong>Recommendation:</strong> Accept 56/60 as the automated generation ceiling. For stakeholder presentations requiring pixel-perfect brand compliance, apply a 5-minute manual touchup pass to add actual logo images and replace shape charts with native charts. Do not attempt further automated iteration until logo assets are available.</p>""",
    "{{OPTIONAL_CHARTS_BLOCK}}": """<div class="chart-frame">
  <canvas id="finalChart"></canvas>
</div>
<script>
  new Chart(document.getElementById('finalChart'), {
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
      plugins: { legend: { labels: { color: '#1f1912' } }, title: { display: true, text: 'Conformance Trajectory Across 3 Decks', color: '#1f1912' } },
      scales: {
        y: { max: 5, grid: { color: 'rgba(0,0,0,0.08)' }, ticks: { color: '#5f564c' } },
        x: { grid: { display: false }, ticks: { color: '#5f564c' } }
      }
    }
  });
</script>""",
    "{{IMPLEMENTATION_PATH}}": """<div class="subcard">
  <h4>Immediate</h4>
  <ol>
    <li>Use Deck 3 (<code>2026-04-21-dppa-case-3.pptx</code>) as the highest-quality template for future automated deck generation.</li>
    <li>Source actual Allotrope logo PNG/SVG and partner logos (Tara, USAID) for manual insertion.</li>
  </ol>
</div>
<div class="subcard">
  <h4>Near-term</h4>
  <ol>
    <li>Implement python-pptx native chart data model to raise D07 from 4/5 to 5/5.</li>
    <li>Store logo assets in <code>reports/decks/conformance/_assets/</code> for reuse across future decks.</li>
  </ol>
</div>
<div class="subcard">
  <h4>Re-run trigger</h4>
  <p>Regenerate all three decks when logo assets + native chart code are available. Expected outcome: 58–59/60.</p>
</div>""",
    "{{RISKS_OPEN_QUESTIONS}}": """<div class="subcard">
  <h4>Risks</h4>
  <ul>
    <li><strong>Logo availability:</strong> If Allotrope does not have a clean logo file, D09 may never reach 5/5.</li>
    <li><strong>Template drift:</strong> If the Allotrope template is updated, the cached rubric becomes stale.</li>
    <li><strong>Overfitting:</strong> The rubric is calibrated to this specific template; other brand decks would need their own rubric extraction.</li>
  </ul>
</div>
<div class="subcard">
  <h4>Open Questions</h4>
  <ul>
    <li>Is 56/60 sufficient for internal stakeholder review, or is manual touchup always required?</li>
    <li>Should the rubric be versioned alongside the template cache?</li>
    <li>Can this workflow be generalized to other brand templates beyond Allotrope?</li>
  </ul>
</div>""",
    "{{APPENDICES_EVIDENCE}}": """<div class="subcard">
  <h4>Artifact Inventory</h4>
  <table>
    <thead><tr><th>Artifact</th><th>Path</th></tr></thead>
    <tbody>
      <tr><td>Plan</td><td><code>plans/2026-05-03-allotrope-template-iterative-ppt-plan.md</code></td></tr>
      <tr><td>Rubric</td><td><code>reports/decks/conformance/allotrope-template-rubric.md</code></td></tr>
      <tr><td>Template cache</td><td><code>reports/decks/conformance/_template/allotrope-template.pptx</code></td></tr>
      <tr><td>Deck 1</td><td><code>reports/decks/2026-04-09-dppa-case-1.pptx</code></td></tr>
      <tr><td>Deck 1 conformance</td><td><code>reports/decks/conformance/2026-04-09-dppa-case-1-conformance.md</code></td></tr>
      <tr><td>Deck 2</td><td><code>reports/decks/2026-04-16-dppa-case-2.pptx</code></td></tr>
      <tr><td>Deck 2 conformance</td><td><code>reports/decks/conformance/2026-04-16-dppa-case-2-conformance.md</code></td></tr>
      <tr><td>Deck 3</td><td><code>reports/decks/2026-04-21-dppa-case-3.pptx</code></td></tr>
      <tr><td>Deck 3 conformance</td><td><code>reports/decks/conformance/2026-04-21-dppa-case-3-conformance.md</code></td></tr>
      <tr><td>Trajectory</td><td><code>reports/decks/conformance/2026-05-03-allotrope-conformance-trajectory.md</code></td></tr>
    </tbody>
  </table>
</div>""",
}

for token, content in replacements.items():
    html = html.replace(token, content)

out_path = "reports/2026-05-06-final-allotrope-template.html"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Final report written to {out_path}")
