"""Generate a current-state project handoff HTML report."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_PHASE4_JSON = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-04_ninhsim-single-owner-finance.json"
)
DEFAULT_PHASE5_JSON = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-04_ninhsim-strike-price.json"
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
DEFAULT_HTML_OUT = (
    REPO_ROOT / "reports" / "2026-04-05-project-status-and-first-analysis-handoff.html"
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


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "null"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000.0:.2f}M USD"
    return f"{value:,.0f} USD"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value * 100.0:.2f}%"


def build_report_html(phase4: dict, phase5: dict, template_text: str) -> str:
    viability = phase5["viability"]
    sweep = phase5["sweep_results"]
    _viable_points = [row for row in sweep if row["is_viable"]]
    min_viable = viability["minimum_viable_strike_us_cents_per_kwh"]
    baseline = viability["phase4_baseline_strike_us_cents_per_kwh"]
    customer_band = baseline
    strike_gap = None if min_viable is None else min_viable - customer_band

    input_output_html = render_column(
        "Current State",
        [
            "Repository rename, package reorganization, and planning-home migration are already complete under `reopt-pysam-vn`.",
            "Ninhsim now has a real Phase 4 PySAM `Single Owner` finance artifact and a Phase 5 strike-discovery artifact.",
            "`plans/active/pysam_integration_reorg_plan.md` is now the canonical roadmap, with the old root path left as a pointer only.",
        ],
    ) + render_column(
        "Next Session Starting Point",
        [
            "Use the default Julia scenario runner for the fastest first Vietnam analysis health check from the repo root.",
            "If continuing PySAM roadmap work, start from the Phase 4 and Phase 5 Ninhsim artifacts instead of rebuilding assumptions.",
            "Treat the combined buyer-plus-developer commercial gap artifact as the next unresolved roadmap item.",
        ],
    )

    mermaid_diagram = """
flowchart TD
    A[Open repo root] --> B{Goal for session?}
    B -- First Vietnam analysis --> C[Set NREL credentials or confirm NREL_API.env]
    C --> D[Run Julia scenario runner with --no-solve]
    D --> E{Scenario validates?}
    E -- Yes --> F[Run full solve on default template or chosen case-study JSON]
    E -- No --> G[Fix inputs, paths, or credentials before solve]
    B -- Continue PySAM roadmap --> H[Open Phase 4 and Phase 5 Ninhsim artifacts]
    H --> I[Compare buyer-side ceiling with developer-side viable strike]
    I --> J[Build combined commercial-gap artifact]
    F --> K[Review JSON output in artifacts/results]
    J --> L[Publish next integration report]
""".strip()

    math_html = render_list(
        [
            f"Phase 4 baseline year-one strike is `{baseline:.3f}` US cents/kWh from the accepted customer-first band.",
            f"Phase 5 found the first developer-side IRR-clearing point at `{min_viable:.1f}` US cents/kWh within the requested `5.0` to `15.0` range.",
            f"Current visible strike gap is `{strike_gap:.3f}` US cents/kWh between the customer-first Phase 4 strike and the first developer-side viable point."
            if strike_gap is not None
            else "Current strike gap is unresolved because no viable developer-side point was found in the tested range.",
            f"At the first viable point, after-tax IRR is `{_fmt_pct(viability['minimum_viable_irr_fraction'])}`, after-tax NPV is `{_fmt_money(viability['minimum_viable_npv_usd'])}`, and minimum DSCR is `{viability['minimum_viable_min_dscr']:.3f}`.",
        ]
    )

    tools_html = render_tools_table(
        [
            (
                "plans/active/pysam_integration_reorg_plan.md",
                "Keep one canonical active roadmap in the project root",
                "Eliminates duplicate editable plan state and makes next-phase ownership obvious.",
            ),
            (
                "scripts/julia/run_vietnam_scenario.jl",
                "Run the first Vietnam analysis from templates or case-study JSON",
                "Provides the cleanest health-check path for the next session.",
            ),
            (
                ".venv\\Scripts\\python.exe",
                "Run PySAM-dependent finance and reporting workflows on a supported runtime",
                "Keeps `nrel-pysam` execution off the unsupported global Python 3.14 environment.",
            ),
            (
                "artifacts/reports/ninhsim/*.json",
                "Reuse canonical Ninhsim artifacts instead of re-deriving assumptions",
                "Preserves deterministic Phase 4 and Phase 5 finance history for follow-on integration work.",
            ),
        ]
    )

    charts_html = render_chart_block(
        "handoffStrikeChart",
        "bar",
        {
            "labels": ["Phase 4 customer-first", "Phase 5 first viable"],
            "datasets": [
                {
                    "label": "Strike (US cents/kWh)",
                    "data": [round(customer_band, 3), round(min_viable or 0.0, 3)],
                    "backgroundColor": ["#00f5ff", "#ff7a00"],
                }
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"legend": {"position": "bottom"}},
            "scales": {"y": {"title": {"display": True, "text": "US cents per kWh"}}},
        },
        height_px=320,
    ) + render_chart_block(
        "handoffFinanceChart",
        "bar",
        {
            "labels": ["After-tax IRR", "Min DSCR", "After-tax NPV (USD M)"],
            "datasets": [
                {
                    "label": "First viable point",
                    "data": [
                        round(
                            (viability["minimum_viable_irr_fraction"] or 0.0) * 100.0, 3
                        ),
                        round(viability["minimum_viable_min_dscr"] or 0.0, 3),
                        round(
                            (viability["minimum_viable_npv_usd"] or 0.0) / 1_000_000.0,
                            3,
                        ),
                    ],
                    "backgroundColor": ["#39ff14", "#00f5ff", "#8a2be2"],
                }
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"legend": {"position": "bottom"}},
            "scales": {"y": {"title": {"display": True, "text": "Mixed units"}}},
        },
        height_px=320,
    )

    limitations_html = render_list(
        [
            "The first developer-side viable strike is still pinned to the top of the requested sweep, so the precise threshold remains unresolved.",
            "The current commercial view still spans multiple artifacts: earlier REopt customer-ceiling work, the Phase 4 PySAM finance artifact, and the Phase 5 strike sweep.",
            "PySAM workflows still require the repo-local Python 3.12 `.venv` on this workstation.",
        ]
    )

    warnings_html = render_list(
        [
            "Do not edit both `plans/pysam_integration_reorg_plan.md` and `plans/active/pysam_integration_reorg_plan.md`; only the file under `plans/active/` is live.",
            f"The current first viable developer-side point still has after-tax NPV `{_fmt_money(viability['minimum_viable_npv_usd'])}` and minimum DSCR `{viability['minimum_viable_min_dscr']:.3f}`, so IRR clearance is not a full finance green light.",
            "The quickest first-session validation path is `--no-solve`; do that before a full optimization if environment health is uncertain.",
        ]
    )

    next_html = render_list(
        [
            "First-analysis quick check: `julia --project --compile=min scripts/julia/run_vietnam_scenario.jl --no-solve`.",
            "First full template solve: `julia --project --compile=min scripts/julia/run_vietnam_scenario.jl`.",
            "Case-study solve example: `julia --project --compile=min scripts/julia/run_vietnam_scenario.jl --scenario scenarios/case_studies/ninhsim/2026-04-01_ninhsim_scenario-b_optimized-cppa.json --no-solve`, then rerun without `--no-solve` once validation passes.",
            "PySAM continuation path: `.venv\\Scripts\\python.exe scripts/python/pysam/strike_price_discovery.py` to refresh the finance-side sweep before building the combined commercial-gap artifact.",
        ]
    )

    replacements = {
        "{{PHASE_NAME}}": "Project Status and First Analysis Handoff",
        "{{DATE}}": "2026-04-05",
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
        "The repository is now structurally synchronized under `reopt-pysam-vn`, "
        "with one canonical active roadmap, a working Ninhsim PySAM Phase 4 finance artifact, "
        f"and a Phase 5 strike sweep showing the first developer-side IRR-clearing point at {min_viable:.1f} US cents/kWh versus a Phase 4 customer-first strike near {baseline:.3f} US cents/kWh. "
        "The next session can either run a fresh Vietnam analysis through the Julia scenario runner or close the remaining buyer-plus-developer integration gap."
    )
    return html.replace("{{SUMMARY_SENTENCE}}", summary_line)


def main() -> None:
    phase4 = json.loads(DEFAULT_PHASE4_JSON.read_text(encoding="utf-8"))
    phase5 = json.loads(DEFAULT_PHASE5_JSON.read_text(encoding="utf-8"))
    template_text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    html = build_report_html(phase4, phase5, template_text)
    DEFAULT_HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Project status handoff report written to: {DEFAULT_HTML_OUT}")


if __name__ == "__main__":
    main()
