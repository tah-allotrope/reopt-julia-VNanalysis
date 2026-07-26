"""Generate HTML report for Saigon18 DPPA Case 3 Phase A."""

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
        "definition": _load_json(base / f"{prefix}_phase-a-definition.json"),
        "assumptions": _load_json(base / f"{prefix}_phase-a-assumptions-register.json"),
        "gap_register": _load_json(base / f"{prefix}_phase-a-gap-register.json"),
    }


def _io_html(artifacts: dict) -> str:
    d = artifacts["definition"]
    g = artifacts["gap_register"]
    inputs = [
        "<li>Saigon18 extracted 8760 load profile (<code>data/interim/saigon18/</code>)</li>",
        "<li>Saigon18 hourly CFMP/FMP market series</li>",
        "<li>Saigon18 tariff assumptions (peak/standard/off-peak rates)</li>",
        "<li>Case 2 rejected outcome (ninhsim, PV-only, transferred market)</li>",
        "<li>User decisions: Lane B only, 5% strike anchor, two tariff branches</li>",
    ]
    outputs = [
        f"<li>Case identity: <code>{d['case_identity']['scenario_family']}</code></li>",
        f"<li>Contract: <code>{d['case_identity']['contract_structure']}</code></li>",
        f"<li>Strike anchor: {d['strike_basis']['strike_discount_fraction'] * 100:.0f}% below weighted EVN</li>",
        f"<li>Year-one strike: {d['strike_basis']['year_one_strike_vnd_per_kwh']:.2f} VND/kWh</li>",
        "<li>Physical lane: bounded optimization only with storage floor</li>",
        "<li>Tariff branches: 22kV two-part + legacy TOU (side-by-side)</li>",
        f"<li>Gap register: {len(g['inherited_shortcomings'])} shortcomings linked to mitigations</li>",
        "<li>Site consistency: same_site_basis = True</li>",
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
    A[Case 1 + 2<br/>Shortcomings] --> B[Gap Register<br/>7 items]
    B --> C[User Decisions<br/>Lane B / 5% / 2 branches]
    C --> D[Phase A<br/>Definition Freeze]
    D --> E[Phase B<br/>Data Package]
    E --> F[Phase C<br/>Bounded Opt Solve]
    F --> G[Phase D<br/>Settlement]
    G --> H[Phase E<br/>Controller Gap]
    H --> I[Phase F<br/>PySAM Validation]
    I --> J[Phase G<br/>Final Decision]

    style A fill:#1a1a2e,stroke:#ff2d78
    style D fill:#0d2137,stroke:#00f5ff
    style J fill:#0d3721,stroke:#39ff14"""


def _math_html(artifacts: dict) -> str:
    d = artifacts["definition"]
    w = d["strike_basis"]["weighted_evn_price_vnd_per_kwh"]
    disc = d["strike_basis"]["strike_discount_fraction"]
    strike = d["strike_basis"]["year_one_strike_vnd_per_kwh"]
    return f"""<table>
<tr><th>Computation</th><th>Formula</th><th>Value</th></tr>
<tr><td>Weighted EVN</td><td>mean(tou_series[0..8759])</td><td>{w:.2f} VND/kWh</td></tr>
<tr><td>Strike anchor</td><td>weighted_evn * (1 - {disc})</td><td>{strike:.2f} VND/kWh</td></tr>
<tr><td>Storage floor</td><td>base_bess_kw * 0.75</td><td>{d["physical_scope"]["storage_floor_min_kw"]:.0f} kW</td></tr>
<tr><td>Storage floor</td><td>base_bess_kwh * 0.75</td><td>{d["physical_scope"]["storage_floor_min_kwh"]:.0f} kWh</td></tr>
<tr><td>PV bound min</td><td>base_pv * 0.75</td><td>{d["physical_scope"]["pv_bounds_kw"]["min"]:.0f} kW</td></tr>
<tr><td>PV bound max</td><td>base_pv * 1.50</td><td>{d["physical_scope"]["pv_bounds_kw"]["max"]:.0f} kW</td></tr>
</table>"""


def _tools_html() -> str:
    return """<ul>
<li><code>dppa_case_3.py</code> — Phase A definition, assumptions register, gap register, Phase B settlement design/schema/edge-cases</li>
<li><code>__init__.py</code> — 6 new Case 3 exports</li>
<li><code>prepare_saigon18_dppa_case_3_phase_ab.py</code> — writes 6 canonical JSON artifacts</li>
<li><code>test_dppa_case_3_phase_ab.py</code> — 9 regression tests</li>
<li>TOU reconstruction from saigon18 tariff assumptions (peak/standard/off-peak + weekday/weekend)</li>
<li>Weighted EVN computed from reconstructed 8760 TOU series</li>
</ul>"""


def _charts_html() -> str:
    return """<div class="empty-state">
<strong>No charts this phase</strong>
Phase A is definition-only. Charts begin in Phase C after the bounded-optimization solve.
</div>"""


def _limits_html() -> str:
    return """<div class="summary-grid">
<div class="column-card"><div class="column-label">Limitations</div><ul>
<li>Weighted EVN is reconstructed from saigon18 tariff assumptions, not an extracted benchmark field</li>
<li>22kV two-part tariff structure (demand charges) not yet encoded — deferred to Phase C</li>
<li>Controller dispatch windows not yet parameterized — deferred to Phase E</li>
<li>Exchange rate hardcoded at 25,450 VND/USD</li>
</ul></div>
<div class="column-card"><div class="column-label">Second-Best Alternative</div><ul>
<li>Run both Lane A (fixed) and Lane B (bounded opt) — rejected by user decision</li>
<li>Anchor strike at 15% below EVN matching real-project notes — rejected by user (keep 5%)</li>
<li>Use ninhsim load with saigon18 market — rejected to enforce site consistency</li>
</ul></div>
</div>"""


def _errors_html() -> str:
    return """<div class="empty-state">
<strong>No errors or warnings</strong>
All 9 tests passed on first green run after the storage_floor naming fix.
</div>"""


def _open_questions_html() -> str:
    return """<div class="summary-grid">
<div class="column-card"><div class="column-label">Open Questions</div><ul>
<li>Exact 22kV demand charge schedule for the two-part tariff branch</li>
<li>Controller charge/discharge window definitions for Phase E</li>
<li>Whether the DPPA adder (523.34 VND/kWh) and KPP (1.027263) should be recalibrated for saigon18</li>
</ul></div>
<div class="column-card"><div class="column-label">Next Phase Seeds</div><ul>
<li>Phase B: Build canonical data loader with scale_to_annual_kwh hook</li>
<li>Phase B: Add site-consistency metadata to every artifact</li>
<li>Phase B: Regression tests for strike-path and tariff-branch metadata</li>
<li>Phase C: Encode bounded-optimization scenario with hard storage floor</li>
</ul></div>
</div>"""


def _render_report(artifacts: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{PHASE_NAME}}", "DPPA Case 3 Phase A")
        .replace("{{DATE}}", REPORT_DATE)
        .replace("{{PROJECT}}", "REopt Vietnam")
        .replace("{{REPO}}", "reopt-pysam-vn")
        .replace("{{INPUT_OUTPUT_CONTENT}}", _io_html(artifacts))
        .replace("{{MERMAID_DIAGRAM}}", _mermaid_diagram())
        .replace("{{MATH_ALGORITHM_SECTION}}", _math_html(artifacts))
        .replace("{{TOOLS_METHODS}}", _tools_html())
        .replace("{{CHARTS_SECTION}}", _charts_html())
        .replace("{{LIMITATIONS_ALTERNATIVES}}", _limits_html())
        .replace("{{ERRORS_WARNINGS_FLAGS}}", _errors_html())
        .replace("{{OPEN_QUESTIONS}}", _open_questions_html())
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = _read_artifacts()
    html = _render_report(artifacts)
    output_path = OUTPUT_DIR / f"{REPORT_DATE}-dppa-case-3-phase-a.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
