"""Generate the Phase 5 Ninhsim PySAM strike-price HTML report."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_JSON_IN = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-04_ninhsim-strike-price.json"
)
DEFAULT_HTML_OUT = (
    REPO_ROOT / "reports" / "2026-04-04-ninhsim-pysam-phase-5-strike-price.html"
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


def _fmt_fraction(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value * 100.0:.2f}%"


def build_report_html(results: dict, template_text: str) -> str:
    sweep = results["sweep_results"]
    settings = results["sweep_settings"]
    viability = results["viability"]
    _case = results["case"]
    viable_count = sum(1 for row in sweep if row["is_viable"])
    min_viable = viability["minimum_viable_strike_us_cents_per_kwh"]
    baseline = viability["phase4_baseline_strike_us_cents_per_kwh"]

    input_output_html = render_column(
        "Input",
        [
            "Started from the canonical Phase 4 Ninhsim PySAM artifact instead of rebuilding finance assumptions from scratch.",
            "Swept year-one strike prices from `5.0` to `15.0` US cents/kWh in `0.5`-cent steps under the same `Single Owner` structure.",
            "Kept the default developer hurdle at `10%` after-tax IRR, as requested for Phase 5 discovery.",
        ],
    ) + render_column(
        "Output",
        [
            "Implemented a real strike-sweep layer in `src/python/reopt_pysam_vn/integration/strike_search.py` on top of the existing Phase 4 bridge and runtime.",
            "Published the normalized discovery artifact to `artifacts/reports/ninhsim/2026-04-04_ninhsim-strike-price.json`.",
            f"Found the first strike inside the requested range that clears the hurdle at `{min_viable:.1f}` US cents/kWh.",
        ],
    )

    mermaid_diagram = """
flowchart TD
    A[Load Phase 4 Ninhsim finance artifact] --> B[Rebuild canonical Single Owner inputs from REopt plus memo artifacts]
    B --> C[Generate strike candidates 5.0 to 15.0 cents in 0.5-cent steps]
    C --> D[Run PySAM Single Owner once per candidate]
    D --> E[Extract after-tax IRR, NPV, and DSCR for each strike]
    E --> F{IRR >= 10%?}
    F -- No --> G[Mark candidate non-viable]
    F -- Yes --> H[Mark candidate viable]
    G --> I[Continue sweep until range end]
    H --> I
    I --> J[Pick first viable strike as minimum requested answer]
    J --> K[Write JSON artifact and synchronized HTML report]
""".strip()

    math_html = render_list(
        [
            "Candidate strike series = `5.0, 5.5, ..., 15.0` US cents/kWh, which yields `21` PySAM evaluations in the requested range.",
            "For each candidate, the workflow keeps all Phase 4 system, debt, tax, and escalation assumptions fixed and changes only `ppa_price_input_usd_per_kwh`.",
            "Viability rule = `project_return_aftertax_irr_fraction >= target_irr_fraction`, because the user asked for the minimum strike that achieves the target IRR.",
            f"Phase 4 baseline strike was `{baseline:.3f}` US cents/kWh, well below the discovered minimum viable point in this sweep.",
        ]
    )

    tools_html = render_tools_table(
        [
            (
                "reopt_pysam_vn.integration.strike_search",
                "Run the deterministic strike sweep on top of Phase 4 inputs",
                "Produced the ordered sweep table and machine-readable viability decision block.",
            ),
            (
                "scripts/python/pysam/strike_price_discovery.py",
                "Generate the canonical Phase 5 JSON artifact",
                "Saved the real Ninhsim discovery result without duplicating finance logic in the script layer.",
            ),
            (
                ".venv / Python 3.12",
                "Keep PySAM execution on the supported local runtime",
                "Allowed the full 21-point sweep to run locally on this workstation.",
            ),
            (
                "tests/python/pysam/test_strike_price_discovery.py",
                "Lock the sweep mechanics and the Ninhsim boundary result",
                "Confirmed both deterministic sweep ordering and the real minimum viable strike outcome.",
            ),
        ]
    )

    strike_labels = [f"{row['strike_price_us_cents_per_kwh']:.1f}" for row in sweep]
    irr_values = [
        None
        if row["outputs"]["project_return_aftertax_irr_fraction"] is None
        else round(row["outputs"]["project_return_aftertax_irr_fraction"] * 100.0, 3)
        for row in sweep
    ]
    npv_values = [
        round(row["outputs"]["project_return_aftertax_npv_usd"] / 1_000_000.0, 3)
        for row in sweep
    ]
    viable_flags = [1 if row["is_viable"] else 0 for row in sweep]
    target_line = [settings["target_irr_fraction"] * 100.0] * len(sweep)

    charts_html = render_chart_block(
        "phase5IrrChart",
        "line",
        {
            "labels": strike_labels,
            "datasets": [
                {
                    "label": "After-tax IRR (%)",
                    "data": irr_values,
                    "borderColor": "#00f5ff",
                    "backgroundColor": "rgba(0, 245, 255, 0.15)",
                    "spanGaps": False,
                    "fill": False,
                },
                {
                    "label": "Target IRR (%)",
                    "data": target_line,
                    "borderColor": "#ff7a00",
                    "backgroundColor": "rgba(255, 122, 0, 0.18)",
                    "borderDash": [6, 4],
                    "fill": False,
                },
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"legend": {"position": "bottom"}},
            "scales": {
                "x": {"title": {"display": True, "text": "Strike (US cents/kWh)"}},
                "y": {"title": {"display": True, "text": "After-tax IRR (%)"}},
            },
        },
        height_px=320,
    ) + render_chart_block(
        "phase5NpvChart",
        "bar",
        {
            "labels": strike_labels,
            "datasets": [
                {
                    "label": "After-tax NPV (USD millions)",
                    "data": npv_values,
                    "backgroundColor": [
                        "#39ff14" if flag == 1 else "#8a2be2" for flag in viable_flags
                    ],
                }
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"legend": {"position": "bottom"}},
            "scales": {
                "x": {"title": {"display": True, "text": "Strike (US cents/kWh)"}},
                "y": {"title": {"display": True, "text": "USD millions"}},
            },
        },
        height_px=320,
    )

    limitations_html = render_list(
        [
            "The requested range is binding: the first viable strike is exactly the upper bound `15.0` US cents/kWh, so this pass does not show whether the true threshold is only slightly below or above that point.",
            "Phase 5 keeps the same Phase 4 `Single Owner` structure and assumptions; it does not yet add CfD settlement logic, merchant shaping, or alternative finance structures.",
            "The selected decision rule is IRR-only because that was the explicit user request; the artifact still shows NPV and DSCR so follow-on phases can layer stricter screens if needed.",
        ]
    )

    warnings_html = render_list(
        [
            f"Only `{viable_count}` of `{len(sweep)}` tested strikes met the `10%` target IRR, which means the requested range leaves almost no headroom above the threshold.",
            f"The Phase 4 baseline strike at `{baseline:.3f}` US cents/kWh is far below the discovered minimum viable strike, so the accepted customer-first commercial band is not finance-viable under this developer-side screen.",
            f"Even the minimum viable point at `{min_viable:.1f}` US cents/kWh carries after-tax NPV `{viability['minimum_viable_npv_usd']:,.0f}` USD, so IRR clearance alone does not imply a broadly attractive finance result.",
        ]
    )

    next_html = render_list(
        [
            "Extend the sweep above `15.0` US cents/kWh or tighten the step near the boundary if the next phase needs a more precise minimum viable strike than the current endpoint answer.",
            "Compare the discovered developer-side viable strike against the buyer-side REopt parity ceiling to quantify the commercial gap directly instead of reviewing the two artifacts separately.",
            "Decide whether future strike screens should require a second condition such as non-negative NPV or minimum DSCR, now that the IRR-only boundary has been made explicit.",
        ]
    )

    replacements = {
        "{{PHASE_NAME}}": "Ninhsim PySAM Phase 5 Strike Price",
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
        "Phase 5 swept 21 year-one strike prices for Ninhsim and found that the first point meeting the requested "
        f"`10%` after-tax IRR target is `{min_viable:.1f}` US cents/kWh, with after-tax IRR {_fmt_fraction(viability['minimum_viable_irr_fraction'])}."
    )
    return html.replace("{{SUMMARY_SENTENCE}}", summary_line)


def main() -> None:
    results = json.loads(DEFAULT_JSON_IN.read_text(encoding="utf-8"))
    template_text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    html = build_report_html(results, template_text)
    DEFAULT_HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Phase 5 HTML report written to: {DEFAULT_HTML_OUT}")


if __name__ == "__main__":
    main()
