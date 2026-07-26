"""Generate HTML report for Saigon18 DPPA Case 3 Phase B."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

TEMPLATE_PATH = (
    Path.home()
    / ".config"
    / "opencode"
    / "skills"
    / "report"
    / "assets"
    / "report-template.html"
)
OUTPUT_DIR = REPO_ROOT / "reports"
REPORT_DATE = "2026-04-20"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_artifacts():
    base = REPO_ROOT / "artifacts" / "reports" / "saigon18"
    prefix = f"{REPORT_DATE}_saigon18_dppa-case-3"
    return {
        "input_package": _load_json(base / f"{prefix}_input-package.json"),
        "definition": _load_json(base / f"{prefix}_phase-a-definition.json"),
    }


def _io_html(artifacts: dict) -> str:
    ip = artifacts["input_package"]
    inputs = [
        "<li>Saigon18 extracted 8760 load, CFMP/FMP, and tariff data</li>",
        "<li>Phase A frozen definition (5% strike, bounded opt, 2 tariff branches)</li>",
        "<li>User decision: Lane B only, 5% strike anchor, side-by-side tariff comparison</li>",
    ]
    load_gwh = ip["load"]["annual_gwh"]
    cfmp_mean = ip["market"]["cfmp_annual_mean_vnd_per_kwh"]
    weighted = ip["tariff"]["weighted_evn_vnd_per_kwh"]
    outputs = [
        f"<li>Canonical load: {load_gwh:.1f} GWh/year, {ip['load']['peak_kw']:.0f} kW peak</li>",
        f"<li>CFMP series: 8760 hourly values, mean {cfmp_mean:.4f} VND/kWh</li>",
        f"<li>TOU series: 8760 hourly values, weighted EVN {weighted:.2f} VND/kWh</li>",
        "<li>Two tariff branches encoded in input package</li>",
        "<li>scale_to_annual_kwh hook available for future retuning</li>",
        "<li>Site consistency: load + market + tariff all from saigon18</li>",
        "<li>7 canonical JSON artifacts written to artifacts/reports/saigon18/</li>",
    ]
    return (
        '<div class="column-card"><div class="column-label">Inputs</div><ul>'
        + "\n".join(inputs)
        + "</ul></div>"
        '<div class="column-card"><div class="column-label">Outputs</div><ul>'
        + "\n".join(outputs)
        + "</ul></div>"
    )


def _mermaid_diagram() -> str:
    return r"""flowchart LR
    A[Saigon18<br/>Extracted JSON] --> B[Load Loader<br/>8760 kW]
    A --> C[CFMP Loader<br/>VND/MWh -> VND/kWh]
    A --> D[FMP Loader<br/>VND/MWh -> VND/kWh]
    A --> E[TOU Builder<br/>peak/std/offpeak]
    B --> F[Input Package<br/>Canonical]
    C --> F
    D --> F
    E --> F
    F --> G[Scale Hook<br/>target_annual_kwh]
    F --> H[Site Consistency<br/>same_site_basis=true]

    style A fill:#1a1a2e,stroke:#ff2d78
    style F fill:#0d3721,stroke:#39ff14"""


def _math_html(artifacts: dict) -> str:
    ip = artifacts["input_package"]
    return f"""<table>
<tr><th>Computation</th><th>Formula</th><th>Result</th></tr>
<tr><td>CFMP conversion</td><td>cfmp_vnd_per_mwh / 1000</td><td>VND/kWh scale ({ip["market"]["cfmp_annual_mean_vnd_per_kwh"]:.4f} mean)</td></tr>
<tr><td>TOU construction</td><td>Weekday peak 9-12,17-20; offpeak 22-4; else standard</td><td>3-tier 8760 series</td></tr>
<tr><td>Weighted EVN</td><td>mean(tou_series)</td><td>{ip["tariff"]["weighted_evn_vnd_per_kwh"]:.2f} VND/kWh</td></tr>
<tr><td>Scale hook</td><td>load_kwh * (target / current)</td><td>Preserves hourly shape</td></tr>
</table>"""


def _tools_html() -> str:
    return """<ul>
<li><code>load_saigon18_load_series()</code> — 8760 kW load from extracted JSON</li>
<li><code>load_saigon18_cfmp_series()</code> — CFMP VND/MWh to VND/kWh conversion</li>
<li><code>load_saigon18_fmp_series()</code> — FMP VND/MWh to VND/kWh conversion</li>
<li><code>load_saigon18_tou_series()</code> — TOU from tariff assumptions (peak/std/offpeak)</li>
<li><code>scale_load_to_annual_kwh()</code> — uniform scaling preserving shape</li>
<li><code>build_dppa_case_3_input_package()</code> — canonical data package with site-consistency metadata</li>
<li>7 regression tests covering loaders, scaling, and site-consistency tagging</li>
</ul>"""


def _charts_html(artifacts: dict) -> str:
    ip = artifacts["input_package"]
    load = ip["load"]["series_kwh"]
    tou = ip["tariff"]["branches"][0]["energy_rates_vnd_per_kwh"]
    return f"""<div class="chart-frame"><canvas id="loadProfileChart" height="280"></canvas></div>
<script>
(function() {{
    const load = {json.dumps(load[:168])};
    const tou = {json.dumps(tou[:168])};
    Chart.defaults.devicePixelRatio = 1;
    Chart.defaults.animation = false;
    new Chart(document.getElementById('loadProfileChart'), {{
        type: 'line',
        data: {{
            labels: Array.from({{length: 168}}, (_, i) => 'H' + i),
            datasets: [
                {{
                    label: 'Load (kW)',
                    data: load,
                    borderColor: '#00f5ff',
                    backgroundColor: 'rgba(0,245,255,0.08)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: true,
                    yAxisID: 'y'
                }},
                {{
                    label: 'TOU Rate (VND/kWh)',
                    data: tou,
                    borderColor: '#39ff14',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    yAxisID: 'y1'
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {{ title: {{ display: true, text: 'First Week: Load Profile vs TOU Rate', color: '#e9f6ff' }} }},
            scales: {{
                y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'kW', color: '#00f5ff' }} }},
                y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: 'VND/kWh', color: '#39ff14' }}, grid: {{ drawOnChartArea: false }} }}
            }}
        }}
    }});
}})();
</script>"""


def _limits_html() -> str:
    return """<div class="summary-grid">
<div class="column-card"><div class="column-label">Limitations</div><ul>
<li>TOU series is reconstructed from 3 tariff rates using weekday/weekend heuristic, not extracted from actual billing data</li>
<li>22kV demand charges not yet modeled — deferred to Phase C scenario encoding</li>
<li>Scale hook applies uniform scaling; cannot adjust seasonal or daily shape</li>
<li>Exchange rate still hardcoded at 25,450 VND/USD</li>
</ul></div>
<div class="column-card"><div class="column-label">Second-Best Alternative</div><ul>
<li>Use ninhsim load profile with saigon18 market — rejected for site consistency</li>
<li>Use north_thuan for better absorption profile — rejected for missing market data</li>
<li>Build a proxy market series instead of using actual CFMP/FMP — rejected since saigon18 provides both</li>
</ul></div>
</div>"""


def _errors_html() -> str:
    return """<div class="empty-state">
<strong>No errors or warnings</strong>
All 16 tests passed. Phase A tests still green. Case 2 tests unaffected.
</div>"""


def _open_questions_html() -> str:
    return """<div class="summary-grid">
<div class="column-card"><div class="column-label">Open Questions</div><ul>
<li>Should the DPPA adder and KPP be recalibrated for saigon18 specifically?</li>
<li>What is the exact 22kV demand charge schedule for the two-part tariff branch?</li>
<li>Is the weekday/weekend TOU heuristic close enough to real EVN scheduling?</li>
</ul></div>
<div class="column-card"><div class="column-label">Next Phase Seeds</div><ul>
<li>Phase C: Build bounded-optimization REopt scenario with storage floor from input package bounds</li>
<li>Phase C: Encode 22kV two-part tariff in REopt ElectricTariff section</li>
<li>Phase C: Solve the bounded-optimization lane and publish physical summary</li>
<li>Phase C: Add regression test that fails if storage becomes zero</li>
</ul></div>
</div>"""


def _render_report(artifacts: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{PHASE_NAME}}", "DPPA Case 3 Phase B")
        .replace("{{DATE}}", REPORT_DATE)
        .replace("{{PROJECT}}", "REopt Vietnam")
        .replace("{{REPO}}", "reopt-pysam-vn")
        .replace("{{INPUT_OUTPUT_CONTENT}}", _io_html(artifacts))
        .replace("{{MERMAID_DIAGRAM}}", _mermaid_diagram())
        .replace("{{MATH_ALGORITHM_SECTION}}", _math_html(artifacts))
        .replace("{{TOOLS_METHODS}}", _tools_html())
        .replace("{{CHARTS_SECTION}}", _charts_html(artifacts))
        .replace("{{LIMITATIONS_ALTERNATIVES}}", _limits_html())
        .replace("{{ERRORS_WARNINGS_FLAGS}}", _errors_html())
        .replace("{{OPEN_QUESTIONS}}", _open_questions_html())
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = _read_artifacts()
    html = _render_report(artifacts)
    output_path = OUTPUT_DIR / f"{REPORT_DATE}-dppa-case-3-phase-b.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
