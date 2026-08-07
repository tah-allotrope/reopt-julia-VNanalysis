"""Generate the Phase 4 Ninhsim PySAM Single Owner HTML report."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_JSON_IN = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-04_ninhsim-single-owner-finance.json"
)
DEFAULT_HTML_OUT = REPO_ROOT / "reports" / "2026-04-04-ninhsim-pysam-phase-4-mvp.html"
DEFAULT_TEMPLATE = (
    Path.home()
    / ".config"
    / "opencode"
    / "skills"
    / "report"
    / "assets"
    / "report-template.html"
)


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


def render_list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def render_chart_block(
    canvas_id: str, chart_type: str, data: dict, options: dict, height_px: int = 320
) -> str:
    chart_json = json.dumps(
        {"type": chart_type, "data": data, "options": options}, ensure_ascii=True
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
    outputs = results["outputs"]
    annual = results["annual_cashflows"]
    case = results["case"]

    input_output_html = render_column(
        "Input",
        [
            "Started from the solved Ninhsim REopt result, the canonical scenario JSON, and the accepted commercial memo instead of building a finance case by hand.",
            "Used the accepted `5% below ceiling` commercial candidate as the year-one strike default for developer-side finance.",
            "Ran the workflow under a local Python 3.12 `.venv` because the workstation's global Python 3.14 cannot install `nrel-pysam`.",
        ],
    ) + render_column(
        "Output",
        [
            "Implemented the first real Phase 4 `Single Owner` wrapper under `src/python/reopt_pysam_vn/pysam/`.",
            "Added a Ninhsim bridge that maps canonical REopt and memo artifacts into a runnable PySAM finance input set.",
            "Published the normalized Phase 4 finance artifact to `artifacts/reports/ninhsim/2026-04-04_ninhsim-single-owner-finance.json`.",
        ],
    )

    mermaid_diagram = """
flowchart TD
    A[Synced repo and Phase 16 scaffolding] --> B{Folder blocker still real?}
    B -- No --> C[Close blocker with path check]
    B -- Yes --> D[Leave non-destructive note]
    C --> E[Install Python 3.12 in local .venv]
    E --> F[Write failing Phase 4 PySAM tests]
    F --> G[Map Ninhsim REopt + memo artifacts to Single Owner inputs]
    G --> H[Execute CustomGenerationProfileSingleOwner locally]
    H --> I{Runtime and outputs valid?}
    I -- No --> J[Inspect live PySAM fields and patch normalizers]
    J --> H
    I -- Yes --> K[Write normalized JSON artifact]
    K --> L[Generate synchronized HTML phase report]
""".strip()

    math_html = render_list(
        [
            "Generation profile = hourly PV-to-load + Wind-to-load + Storage-to-load series from the solved Ninhsim REopt result.",
            "Year-one strike = accepted commercial candidate `5% below ceiling` converted from VND/kWh to USD/kWh using the repo exchange rate `26,400 VND/USD`.",
            "Fixed O&M = PV size x PV O&M/kW + Wind size x Wind O&M/kW + storage initial capital cost x storage O&M fraction.",
            "PySAM then computes debt service, after-tax cash flow, DSCR, and NPV through `CustomGenerationProfileSingleOwner` with wrapper-driven Vietnam defaults and zeroed US-style incentives.",
        ]
    )

    tools_html = render_tools_table(
        [
            (
                ".venv / Python 3.12",
                "Provide a PySAM-supported local runtime",
                "Unblocked `nrel-pysam` installation without changing the workstation's global Python.",
            ),
            (
                "tests/python/pysam/test_single_owner_phase4.py",
                "Lock the Phase 4 bridge and runtime contract before implementation",
                "Added failing coverage for Ninhsim mapping and real local `Single Owner` execution.",
            ),
            (
                "reopt_pysam_vn.integration.bridge",
                "Map canonical REopt and memo artifacts into a finance-ready input set",
                "Defaults to the accepted `5% below ceiling` candidate from the commercial memo.",
            ),
            (
                "PySAM CustomGenerationProfileSingleOwner",
                "Run the first real developer-side finance model",
                "Produced normalized annual cash-flow, NPV, and DSCR outputs.",
            ),
        ]
    )

    charts_html = render_chart_block(
        "phase4RevenueChart",
        "bar",
        {
            "labels": [str(row["year"]) for row in annual[:5]],
            "datasets": [
                {
                    "label": "Revenue (USD millions)",
                    "data": [
                        round(row["total_revenue_usd"] / 1_000_000.0, 3)
                        for row in annual[:5]
                    ],
                    "backgroundColor": "#00f5ff",
                },
                {
                    "label": "After-tax cashflow (USD millions)",
                    "data": [
                        round(row["aftertax_cashflow_usd"] / 1_000_000.0, 3)
                        for row in annual[:5]
                    ],
                    "backgroundColor": "#39ff14",
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
        "phase4DebtChart",
        "line",
        {
            "labels": [str(row["year"]) for row in annual[:10]],
            "datasets": [
                {
                    "label": "Debt balance (USD millions)",
                    "data": [
                        round(row["debt_balance_usd"] / 1_000_000.0, 3)
                        for row in annual[:10]
                    ],
                    "borderColor": "#ff7a00",
                    "backgroundColor": "rgba(255, 122, 0, 0.18)",
                    "fill": True,
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

    limitations_html = render_list(
        [
            "The Phase 4 MVP uses a local Python 3.12 `.venv`; the global Python 3.14 environment still cannot install `nrel-pysam`.",
            "This pass uses a `Single Owner` custom-generation profile only; it does not yet implement strike search, baseload shaping, CfD settlement, or richer contract structures.",
            "The second-best alternative was to leave PySAM at scaffold level and postpone real execution until the environment changed; the chosen path won because a local supported runtime was available and made a real MVP possible now.",
        ]
    )

    warnings_html = render_list(
        [
            "Original blocker note was stale: the old local folder path no longer exists and the repo already lives at `reopt-pysam-vn`.",
            "`nrel-pysam` has no wheel for Python 3.14 on this workstation, so Phase 4 validation had to move into a local Python 3.12 environment.",
            "PySAM can emit null-equivalent IRR values when the selected strike and cost assumptions do not produce a positive-return cashflow profile; the result normalizer preserves that as `null` rather than fabricating a number.",
        ]
    )

    next_html = render_list(
        [
            "Use the new Phase 4 artifact as the finance-side input for Phase 5 strike-price discovery between buyer-side REopt parity and developer-side return thresholds.",
            "Decide whether to standardize repo-local PySAM execution around `.venv` in docs and automation, or add a dedicated helper script for environment bootstrapping.",
            "Add a second case-study bridge once the first strike-search path is stable, so Phase 4 does not stay Ninhsim-only.",
        ]
    )

    replacements = {
        "{{PHASE_NAME}}": "Ninhsim PySAM Phase 4 MVP",
        "{{DATE}}": "2026-04-04",
        "{{PROJECT}}": "Saigon18 REopt Integration",
        "{{REPO}}": "reopt-pysam-vn",
        "{{INPUT_OUTPUT_CONTENT}}": input_output_html,
        "{{MERMAID_DIAGRAM}}": mermaid_diagram,
        "{{MATH_ALGORITHM_SECTION}}": math_html,
        "{{TOOLS_METHODS}}": tools_html,
        "{{CHARTS_SECTION}}": charts_html,
        "{{LIMITATIONS_ALTERNATIVES}}": limitations_html,
        "{{ERRORS_WARNINGS_FLAGS}}": warnings_html,
        "{{OPEN_QUESTIONS}}": next_html,
    }

    html = template_text
    for token, value in replacements.items():
        html = html.replace(token, value)

    summary_line = (
        "Phase 4 landed a real local PySAM `Single Owner` workflow for Ninhsim, "
        f"defaulting to the accepted `{case['recommended_band_label']}` candidate and producing normalized developer-finance outputs. "
        f"Current after-tax NPV is {outputs['project_return_aftertax_npv_usd']:,.0f} USD and minimum DSCR is "
        f"{outputs['min_dscr'] if outputs['min_dscr'] is not None else 'null'} under the selected assumptions."
    )
    return html.replace("{{SUMMARY_SENTENCE}}", summary_line)


def main() -> None:
    results = json.loads(DEFAULT_JSON_IN.read_text(encoding="utf-8"))
    template_text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    html = build_report_html(results, template_text)
    DEFAULT_HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Phase 4 HTML report written to: {DEFAULT_HTML_OUT}")


if __name__ == "__main__":
    main()
