"""
Generate the Phase 14 Ninhsim commercial candidate memo HTML report.
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
    / "2026-04-02_ninhsim-commercial-candidate-memo.json"
)
DEFAULT_HTML_OUT = (
    REPO_ROOT / "reports" / "2026-04-02-ninhsim-commercial-candidate-memo.html"
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
PHASE_NAME = "Ninhsim Commercial Candidate Memo"


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
    memo = results["commercial_candidate_memo"]
    recommendation = results["customer_first_recommendation"]
    candidates = memo["candidates"]

    input_output_html = render_column(
        "Input",
        [
            "Started from the accepted customer-first annual path, so the memo no longer asks whether customer savings survive richer assumptions; it translates that answer into a commercial shortlist.",
            "Kept the shortlist intentionally small and decision-oriented: recommended customer-first band, exact-parity fallback, and premium band for rejection.",
            "Used status labels that map directly to action: advance, hold, and discard.",
        ],
    ) + render_column(
        "Output",
        [
            "Published the machine-readable Phase 14 memo artifact to `artifacts/reports/ninhsim/2026-04-02_ninhsim-commercial-candidate-memo.json`.",
            f"Primary recommendation: `{memo['recommended_band_label']}` with decision `{memo['decision']}`.",
            f"The memo outcome is: {memo['decision_summary']}",
        ],
    )

    math_html = (
        "<ul>"
        "<li>Start from the Phase 13 accepted customer-first recommendation and the Phase 12 shortlist.</li>"
        "<li>Mark the accepted customer-first band as <code>advance</code>.</li>"
        "<li>Mark a non-premium fallback band as <code>hold</code> when it preserves customer protection but offers weaker customer value than the recommendation.</li>"
        "<li>Mark any shortlist band with positive customer premium as <code>discard</code> under the current commercial framing.</li>"
        "</ul>"
    )

    tools_html = render_tools_table(
        [
            (
                "tests/python/integration/test_ninhsim_cppa.py",
                "Lock the memo classification contract before implementation",
                "Added regressions that require advance / hold / discard statuses and the final recommendation to match the accepted customer-first framing.",
            ),
            (
                "scripts/python/integration/analyze_ninhsim_cppa.py",
                "Keep the memo view in the canonical Ninhsim analysis payload",
                "Now emits commercial_candidate_memo alongside the earlier pricing, sensitivity, and annual-path outputs.",
            ),
            (
                "Customer-first annual path",
                "Use the richer annual-path result as the policy anchor for commercial recommendation",
                "Ensured the memo does not drift back toward a premium band after the customer-first decision was accepted.",
            ),
            (
                "report-template.html",
                "Publish the memo in the standard reviewable HTML format",
                "Generated a synced commercial shortlist report with browser-safe charts.",
            ),
        ]
    )

    charts_html = render_chart_block(
        "ninhsimCandidateStatusChart",
        "bar",
        {
            "labels": [candidate["band_label"] for candidate in candidates],
            "datasets": [
                {
                    "label": "Developer revenue NPV (USD millions)",
                    "data": [
                        round(candidate["developer_revenue_npv_usd"] / 1_000_000.0, 3)
                        for candidate in candidates
                    ],
                    "backgroundColor": [
                        "#39ff14",
                        "#00f5ff",
                        "#ff7a00",
                    ],
                },
                {
                    "label": "Customer savings NPV (USD millions)",
                    "data": [
                        round(candidate["customer_savings_npv_usd"] / 1_000_000.0, 3)
                        for candidate in candidates
                    ],
                    "backgroundColor": "rgba(57, 255, 20, 0.22)",
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
        "ninhsimPremiumChart",
        "bar",
        {
            "labels": [candidate["band_label"] for candidate in candidates],
            "datasets": [
                {
                    "label": "Customer premium NPV (USD millions)",
                    "data": [
                        round(candidate["customer_premium_npv_usd"] / 1_000_000.0, 3)
                        for candidate in candidates
                    ],
                    "backgroundColor": [
                        "rgba(57, 255, 20, 0.15)",
                        "rgba(0, 245, 255, 0.15)",
                        "rgba(255, 122, 0, 0.55)",
                    ],
                }
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"legend": {"position": "bottom"}},
            "scales": {"y": {"title": {"display": True, "text": "USD millions"}}},
        },
        height_px=320,
    )

    limitations_html = render_open_questions(
        [
            "This memo is intentionally a decision layer, not a new economic model; it depends on the earlier screening and customer-first annual-path assumptions already accepted in Phase 12 and Phase 13.",
            "The memo favors customer protection over maximum developer upside, so the premium band is rejected even though it produces the highest developer revenue NPV.",
            "Second-best alternative: advance both `5% below ceiling` and `ceiling` together as co-equal commercial options; it lost because the accepted customer-first framing already provided enough evidence to prioritize one lead candidate and keep one fallback only.",
        ]
    )

    warnings_html = render_open_questions(
        [
            "Candidate statuses are policy labels derived from the accepted customer-first rule, not probabilistic deal-outcome forecasts.",
            "The memo still inherits the merchant-price proxy from Phase 13, so any major change to merchant assumptions could justify rechecking the shortlist later.",
            "Chart canvases remain inside fixed-height wrappers to preserve the browser-safe report pattern recorded in repo lessons.",
        ]
    )

    candidate_lines = []
    for candidate in candidates:
        candidate_lines.append(
            "<strong>"
            f"{candidate['band_label']} - {candidate['status']}"
            "</strong><br>"
            f"Year-1 strike {candidate['year_one_cppa_strike_vnd_per_kwh']:.2f} VND/kWh; "
            f"developer revenue NPV ${candidate['developer_revenue_npv_usd'] / 1_000_000.0:.2f}M; "
            f"customer savings NPV ${candidate['customer_savings_npv_usd'] / 1_000_000.0:.2f}M; "
            f"customer premium NPV ${candidate['customer_premium_npv_usd'] / 1_000_000.0:.2f}M."
        )

    open_questions_html = (
        render_open_questions(
            [
                f"Advance recommendation: {memo['recommended_band_label']}.",
                memo["decision_summary"],
                *candidate_lines,
                f"Accepted customer-first anchor: {recommendation['finance_grade_customer_savings_npv_usd'] / 1_000_000.0:.2f}M customer savings NPV with no premium under the richer annual path.",
                "Next optional step is to package the advance candidate into a short negotiation-ready memo or slide for external discussion.",
            ]
        )
        + "<p><strong>Decision artifact:</strong> Review `commercial_candidate_memo` and confirm the shortlist action labels before any external sharing.</p>"
    )

    replacements = {
        "{{PHASE_NAME}}": PHASE_NAME,
        "{{DATE}}": REPORT_DATE,
        "{{PROJECT}}": PROJECT_NAME,
        "{{REPO}}": REPO_ROOT.name,
        "{{INPUT_OUTPUT_CONTENT}}": input_output_html,
        "{{MERMAID_DIAGRAM}}": """flowchart TD
A[Accepted customer-first band] --> B[Read shortlist candidates]
B --> C[Add failing memo regressions]
C --> D[Classify candidate statuses]
D --> E{Customer premium positive?}
E -- Yes --> F[Mark discard]
E -- No --> G{Is it the accepted customer-first band?}
G -- Yes --> H[Mark advance]
G -- No --> I[Mark hold]
F --> J[Build commercial memo artifact]
H --> J
I --> J
J --> K[Publish synced HTML memo report]""",
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
        description="Generate the Phase 14 Ninhsim commercial candidate memo HTML report"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_JSON_IN),
        help="Path to the Ninhsim commercial memo JSON artifact",
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
    print(f"Wrote Ninhsim Phase 14 HTML report: {html_out}")


if __name__ == "__main__":
    main()
