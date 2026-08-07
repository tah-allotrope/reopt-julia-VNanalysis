"""
Generate the Phase 13 Ninhsim customer-first annual path HTML report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_JSON_IN = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-02_ninhsim-customer-first-annual-path.json"
)
DEFAULT_HTML_OUT = (
    REPO_ROOT / "reports" / "2026-04-02-ninhsim-customer-first-annual-path.html"
)
DEFAULT_TEMPLATE = (
    Path.home()
    / ".config"
    / "opencode"
    / "skills"
    / "report"
    / "assets"
    / "report-template.html"
)
REPORT_DATE = "2026-04-02"
PROJECT_NAME = "Saigon18 REopt Integration"
PHASE_NAME = "Ninhsim Customer-First Annual Path"


def render_column(label: str, items: list[str]) -> str:
    bullets = "".join(f"<li>{item}</li>" for item in items)
    return (
        '<div class="column-card">'
        f'<h3 class="column-label">{label}</h3>'
        '<div class="splitter"></div>'
        f"<ul>{bullets}</ul>"
        "</div>"
    )


def render_tools_table(rows: list[tuple[str, str, str]]) -> str:
    body = "".join(
        f"<tr><td><code>{tool}</code></td><td>{purpose}</td><td>{outcome}</td></tr>"
        for tool, purpose, outcome in rows
    )
    return (
        "<table><thead><tr><th>Tool / Method</th><th>Purpose</th><th>Outcome</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def render_open_questions(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def render_chart_block(
    canvas_id: str,
    chart_type: str,
    data: dict,
    options: dict | None = None,
    height_px: int = 340,
) -> str:
    chart_json = json.dumps(
        {"type": chart_type, "data": data, "options": options or {}},
        ensure_ascii=True,
    )
    return (
        f'<div style="position: relative; height: {height_px}px; margin-bottom: 24px;">'
        f'<canvas id="{canvas_id}"></canvas>'
        "</div>"
        "<script>"
        f"new Chart(document.getElementById('{canvas_id}'), {chart_json});"
        "</script>"
    )


def build_report_html(results: dict, template_text: str) -> str:
    rec = results["customer_first_recommendation"]
    annual_path = results["customer_first_annual_path"]
    review_endpoint = results["review_endpoint"]

    input_output_html = render_column(
        "Input",
        [
            "Started from the Phase 12 shortlist and deliberately chose the customer-first recommendation rule: keep the highest-revenue shortlist band that still leaves customer savings positive.",
            f"Applied explicit finance-grade annual defaults of {rec['annual_generation_degradation_fraction'] * 100:.1f}%/yr renewable degradation, {rec['annual_load_growth_fraction'] * 100:.1f}%/yr load growth, and unmatched-energy monetization at {rec['unmatched_energy_price_fraction_of_evn'] * 100:.1f}% of the EVN benchmark.",
            "Reused the solved Ninhsim delivery/export shape so unmatched renewable energy is handled outside the customer bill instead of being silently ignored.",
        ],
    ) + render_column(
        "Output",
        [
            "Published the machine-readable Phase 13 artifact to `artifacts/reports/ninhsim/2026-04-02_ninhsim-customer-first-annual-path.json`.",
            f"The recommended customer-first band remains `{rec['recommended_band_label']}` at {rec['year_one_cppa_strike_vnd_per_kwh']:.2f} VND/kWh.",
            f"Under the richer annual path, customer savings NPV remains positive at ${rec['finance_grade_customer_savings_npv_usd'] / 1_000_000.0:.2f}M with no customer premium.",
        ],
    )

    math_html = (
        "<ul>"
        "<li>Select the customer-first band from the Phase 12 shortlist by maximizing developer revenue subject to customer savings staying positive in the screening view.</li>"
        "<li>For each year, scale renewable availability by <code>(1 - degradation)</code> and site load by <code>(1 + load_growth)</code> before recomputing matched, residual-grid, and unmatched renewable volumes.</li>"
        "<li>Keep unmatched renewable energy off the customer bill and value it separately at a merchant-price proxy tied to a fraction of the EVN benchmark.</li>"
        "<li>Discount the customer and developer cash views with the existing REopt discount rates so the customer-first recommendation can be compared on an NPV basis.</li>"
        "</ul>"
    )

    tools_html = render_tools_table(
        [
            (
                "tests/python/integration/test_ninhsim_cppa.py",
                "Lock the new annual-path contract before implementation",
                "Added regressions for degradation, load drift, unmatched-energy handling, and the customer-first recommendation hook.",
            ),
            (
                "scripts/python/integration/analyze_ninhsim_cppa.py",
                "Keep the finance-grade annual replay inside the existing Ninhsim analysis workflow",
                "Now emits customer_first_recommendation and customer_first_annual_path alongside the strike-band screen.",
            ),
            (
                "Solved delivery + export shapes",
                "Reuse real REopt output series instead of annual-total guesswork",
                "Preserved a customer-protective treatment where unmatched renewable energy is monetized separately rather than billed to the customer.",
            ),
            (
                "report-template.html",
                "Publish the annual-path result in the standard browser-safe report shell",
                "Generated the synced Phase 13 HTML artifact with fixed-height Chart.js containers.",
            ),
        ]
    )

    charts_html = render_chart_block(
        "ninhsimAnnualSavingsChart",
        "line",
        {
            "labels": [row["year"] for row in annual_path],
            "datasets": [
                {
                    "label": "Customer savings vs EVN (USD millions)",
                    "data": [
                        round(row["customer_savings_vs_evn_usd"] / 1_000_000.0, 3)
                        for row in annual_path
                    ],
                    "borderColor": "#39ff14",
                    "backgroundColor": "rgba(57, 255, 20, 0.18)",
                    "tension": 0.25,
                },
                {
                    "label": "Developer revenue (USD millions)",
                    "data": [
                        round(row["developer_revenue_usd"] / 1_000_000.0, 3)
                        for row in annual_path
                    ],
                    "borderColor": "#00f5ff",
                    "backgroundColor": "rgba(0, 245, 255, 0.18)",
                    "tension": 0.25,
                },
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"legend": {"position": "bottom"}},
            "scales": {"y": {"title": {"display": True, "text": "USD millions"}}},
        },
        height_px=320,
    ) + render_chart_block(
        "ninhsimVolumePathChart",
        "line",
        {
            "labels": [row["year"] for row in annual_path],
            "datasets": [
                {
                    "label": "Renewable delivered (GWh)",
                    "data": [
                        round(row["renewable_delivered_kwh"] / 1_000_000.0, 3)
                        for row in annual_path
                    ],
                    "borderColor": "#39ff14",
                    "backgroundColor": "rgba(57, 255, 20, 0.18)",
                    "tension": 0.25,
                },
                {
                    "label": "Unmatched renewable (GWh)",
                    "data": [
                        round(row["unmatched_renewable_kwh"] / 1_000_000.0, 3)
                        for row in annual_path
                    ],
                    "borderColor": "#ffb100",
                    "backgroundColor": "rgba(255, 177, 0, 0.18)",
                    "tension": 0.25,
                },
                {
                    "label": "Total load (GWh)",
                    "data": [
                        round(row["total_load_kwh"] / 1_000_000.0, 3)
                        for row in annual_path
                    ],
                    "borderColor": "#ff7a00",
                    "backgroundColor": "rgba(255, 122, 0, 0.18)",
                    "tension": 0.25,
                },
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"legend": {"position": "bottom"}},
            "scales": {"y": {"title": {"display": True, "text": "GWh"}}},
        },
        height_px=320,
    )

    limitations_html = render_open_questions(
        [
            "This is more finance-grade than Phase 12, but it is still a post-processed replay rather than a fresh optimization under degraded production and drifting load conditions.",
            "The customer-first path won over a developer-maximizing path because the request explicitly prioritized customer best interest, so the recommendation rule refuses shortlist bands that create customer premium in the screening view.",
            "Second-best alternative: hold the annual path at exact parity (`ceiling`) to minimize negotiation complexity; it lost because the `5% below ceiling` band preserves positive customer savings while still keeping strong developer revenue.",
        ]
    )

    warnings_html = render_open_questions(
        [
            "Unmatched renewable pricing still uses a proxy tied to the EVN benchmark rather than a project-specific merchant forecast, so merchant-value results should be treated as directional.",
            "No new Julia solve was run in this phase, so the annual path inherits the original optimized design and dispatch shape from the solved year-one scenario.",
            "Chart canvases are again wrapped in explicit-height containers to preserve browser rendering stability.",
        ]
    )

    open_questions_html = (
        render_open_questions(
            [
                review_endpoint["question"],
                f"Recommended band: {rec['recommended_band_label']} at {rec['year_one_cppa_strike_vnd_per_kwh']:.2f} VND/kWh.",
                f"Finance-grade customer savings NPV: ${rec['finance_grade_customer_savings_npv_usd'] / 1_000_000.0:.2f}M; customer premium NPV: ${rec['finance_grade_customer_premium_npv_usd'] / 1_000_000.0:.2f}M.",
                f"Year-1 unmatched renewable energy is {annual_path[0]['unmatched_renewable_kwh'] / 1_000_000.0:.2f} GWh and declines to {annual_path[-1]['unmatched_renewable_kwh'] / 1_000_000.0:.2f} GWh by year 20 as load growth absorbs more output.",
                "If the customer-first band still looks acceptable, the next phase should package it into a concise advance / hold / discard candidate memo for commercial review.",
            ]
        )
        + "<p><strong>Decision artifact:</strong> "
        + review_endpoint["decision_artifact"]
        + "</p>"
    )

    replacements = {
        "{{PHASE_NAME}}": PHASE_NAME,
        "{{DATE}}": REPORT_DATE,
        "{{PROJECT}}": PROJECT_NAME,
        "{{REPO}}": REPO_ROOT.name,
        "{{INPUT_OUTPUT_CONTENT}}": input_output_html,
        "{{MERMAID_DIAGRAM}}": """flowchart TD
A[Phase 12 shortlist] --> B[Choose customer-first rule]
B --> C[Write failing annual-path regressions]
C --> D[Replay solved delivery plus export shapes]
D --> E[Apply degradation load growth and merchant handling]
E --> F{Customer savings still positive?}
F -- Yes --> G[Keep 5% below ceiling as recommended band]
F -- No --> H[Fall back to lower-risk band]
G --> I[Regenerate machine-readable annual-path artifact]
H --> I
I --> J[Publish synced HTML report for self-review]""",
        "{{MATH_ALGORITHM_SECTION}}": math_html,
        "{{TOOLS_METHODS}}": tools_html,
        "{{CHARTS_SECTION}}": charts_html,
        "{{LIMITATIONS_ALTERNATIVES}}": limitations_html,
        "{{ERRORS_WARNINGS_FLAGS}}": warnings_html,
        "{{OPEN_QUESTIONS}}": open_questions_html,
    }

    html = template_text
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Phase 13 Ninhsim customer-first annual-path HTML report"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_JSON_IN),
        help="Path to the Ninhsim customer-first annual-path JSON artifact",
    )
    parser.add_argument(
        "--html-out",
        default=str(DEFAULT_HTML_OUT),
        help="Output path for the HTML phase report",
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE),
        help="Report template path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    template_path = Path(args.template)
    html_out = Path(args.html_out)

    results = json.loads(input_path.read_text(encoding="utf-8"))
    template_text = template_path.read_text(encoding="utf-8")
    html = build_report_html(results, template_text)

    html_out.parent.mkdir(parents=True, exist_ok=True)
    html_out.write_text(html, encoding="utf-8")
    print(f"Wrote Ninhsim Phase 13 HTML report: {html_out}")


if __name__ == "__main__":
    main()
