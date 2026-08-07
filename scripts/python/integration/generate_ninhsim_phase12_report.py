"""
Generate the Phase 12 Ninhsim strike sensitivity HTML report.
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
    / "2026-04-02_ninhsim-cppa-strike-sensitivity.json"
)
DEFAULT_HTML_OUT = (
    REPO_ROOT / "reports" / "2026-04-02-ninhsim-strike-sensitivity-bands.html"
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
PHASE_NAME = "Ninhsim Strike Sensitivity Bands"


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
    pricing = results["pricing"]
    bands = results["strike_sensitivity_bands"]
    review_endpoint = results["review_endpoint"]
    suggested_bands = review_endpoint["suggested_review_bands"]
    middle_band_labels = set(suggested_bands)
    middle_bands = [band for band in bands if band["band_label"] in middle_band_labels]

    input_output_html = render_column(
        "Input",
        [
            "Started from the already-solved Ninhsim bundled-CPPA result and the Phase 11 finance-screening artifact; no new REopt optimization run was required.",
            "Swept strike bands around the customer-equivalent ceiling so the post-processing could show savings and premium tradeoffs instead of only the exact zero-savings point.",
            "Kept the annual replay assumption explicit: year-one renewable delivery and residual EVN volumes still stay fixed while unit prices escalate with the REopt tariff-growth assumption.",
        ],
    ) + render_column(
        "Output",
        [
            "Published the machine-readable sensitivity artifact to `artifacts/reports/ninhsim/2026-04-02_ninhsim-cppa-strike-sensitivity.json`.",
            f"Created a clear self-review endpoint around {', '.join(suggested_bands)} so the next commercial pass can choose between savings, parity, or premium bands.",
            f"At the current ceiling the year-one strike stays {pricing['max_cppa_strike_vnd_per_kwh']:.2f} VND/kWh and keeps the customer exactly at the weighted EVN benchmark.",
        ],
    )

    math_html = (
        "<ul>"
        "<li>Start from the Phase 11 ceiling strike where customer total cost equals the weighted EVN benchmark.</li>"
        "<li>Apply a relative strike multiplier for each band: <code>strike_band = ceiling_strike x (1 + adjustment)</code>.</li>"
        "<li>Replay the same solved renewable and residual-grid volumes across all years, escalating both CPPA and EVN prices at the REopt electricity escalation rate.</li>"
        "<li>Discount developer revenue with the owner discount rate and customer costs with the offtaker discount rate to compare NPV tradeoffs on each band.</li>"
        "</ul>"
    )

    tools_html = render_tools_table(
        [
            (
                "tests/python/integration/test_ninhsim_cppa.py",
                "Lock the strike-band payload shape and parity/savings/premium behavior before implementation",
                "Added two regressions and verified the focused Ninhsim suite passes.",
            ),
            (
                "scripts/python/integration/analyze_ninhsim_cppa.py",
                "Extend the existing Ninhsim analyzer instead of splitting logic across multiple scripts",
                "Now emits strike_sensitivity_bands plus a review_endpoint alongside the existing pricing views.",
            ),
            (
                "Phase 11 financial screening path",
                "Reuse the established multi-year CPPA replay and discount-rate assumptions",
                "Kept this pass consistent with the repo's explicit post-processing scope and caveats.",
            ),
            (
                "report-template.html",
                "Publish the phase result in the standard HTML report shell with explicit chart heights",
                "Generated a browser-safe phase report that matches the repo's report workflow.",
            ),
        ]
    )

    charts_html = render_chart_block(
        "ninhsimDeveloperRevenueChart",
        "bar",
        {
            "labels": [band["band_label"] for band in bands],
            "datasets": [
                {
                    "label": "Developer revenue NPV (USD millions)",
                    "data": [
                        round(band["developer_revenue_npv_usd"] / 1_000_000.0, 3)
                        for band in bands
                    ],
                    "backgroundColor": [
                        "#39ff14",
                        "#5df87b",
                        "#00f5ff",
                        "#53b7ff",
                        "#ff7a00",
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
    ) + render_chart_block(
        "ninhsimCustomerTradeoffChart",
        "line",
        {
            "labels": [band["band_label"] for band in bands],
            "datasets": [
                {
                    "label": "Customer savings NPV (USD millions)",
                    "data": [
                        round(band["customer_savings_npv_usd"] / 1_000_000.0, 3)
                        for band in bands
                    ],
                    "borderColor": "#39ff14",
                    "backgroundColor": "rgba(57, 255, 20, 0.18)",
                    "tension": 0.25,
                },
                {
                    "label": "Customer premium NPV (USD millions)",
                    "data": [
                        round(band["customer_premium_npv_usd"] / 1_000_000.0, 3)
                        for band in bands
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
            "scales": {"y": {"title": {"display": True, "text": "USD millions"}}},
        },
        height_px=320,
    )

    shortlist_items = []
    for band in middle_bands:
        shortlist_items.append(
            "<strong>"
            f"{band['band_label']}"
            "</strong><br>"
            f"Year-1 strike {band['year_one_cppa_strike_vnd_per_kwh']:.2f} VND/kWh; "
            f"developer revenue NPV ${band['developer_revenue_npv_usd'] / 1_000_000.0:.2f}M; "
            f"customer savings NPV ${band['customer_savings_npv_usd'] / 1_000_000.0:.2f}M; "
            f"customer premium NPV ${band['customer_premium_npv_usd'] / 1_000_000.0:.2f}M."
        )

    limitations_html = render_open_questions(
        [
            "This remains a screening model, not full project finance: it still replays solved year-one renewable delivery and grid volumes instead of modeling degradation, load drift, or merchant handling for unmatched energy.",
            "The chosen path won over a re-solve loop because the immediate user review need is commercial strike selection, and that can be answered faster with post-processing on the existing optimal mix.",
            "Second-best alternative: jump directly to a finance-grade multi-year volume model now; that would be more realistic, but it would slow the decision loop before confirming whether any strike band is commercially attractive.",
        ]
    )

    warnings_html = render_open_questions(
        [
            "The first implementation pass produced a tiny false premium at the ceiling due to benchmark basis and floating-point residue; this was fixed by benchmarking against total load and clamping near-zero deltas.",
            "No new external API or Julia-solve warnings were introduced in this phase; validation stayed inside the focused Python Ninhsim workflow.",
            "Chart canvases are wrapped in fixed-height containers to avoid the prior browser rendering issue recorded in lessons.md.",
        ]
    )

    open_questions_html = (
        render_open_questions(
            [
                review_endpoint["question"],
                f"Immediate review shortlist: {', '.join(suggested_bands)}.",
                *shortlist_items,
                "If a savings band is chosen, the next phase should test whether the same recommendation survives degradation, load drift, and unmatched-energy treatment.",
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
A[Solved Ninhsim bundled-CPPA result] --> B[Read Phase 11 pricing and discount assumptions]
B --> C[Add failing regressions for strike-band sweep]
C --> D[Implement strike sensitivity bands around customer-equivalent ceiling]
D --> E{Ceiling still shows premium or savings residue?}
E -- Yes --> F[Fix benchmark basis and clamp near-zero float dust]
F --> G[Re-run focused Ninhsim pytest suite]
E -- No --> G
G --> H[Regenerate machine-readable sensitivity artifact]
H --> I[Publish HTML report with shortlist review endpoint]""",
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
        description="Generate the Phase 12 Ninhsim strike sensitivity HTML report"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_JSON_IN),
        help="Path to the Ninhsim strike sensitivity JSON artifact",
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
    print(f"Wrote Ninhsim Phase 12 HTML report: {html_out}")


if __name__ == "__main__":
    main()
