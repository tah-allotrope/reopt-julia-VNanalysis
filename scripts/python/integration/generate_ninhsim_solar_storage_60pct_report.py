"""Generate the Ninhsim solar-storage 60% DPPA HTML report."""

from __future__ import annotations

import json
from pathlib import Path

from reopt_pysam_vn.common.reporting import phase_report_template

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_ANALYSIS_IN = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-08_ninhsim_solar-storage_60pct_analysis.json"
)
DEFAULT_COMBINED_IN = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-08_ninhsim_solar-storage_60pct_combined-decision.json"
)
DEFAULT_HTML_OUT = (
    REPO_ROOT / "reports" / "2026-04-08-ninhsim-solar-storage-60pct-dppa.html"
)
DEFAULT_TEMPLATE = phase_report_template()
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


def build_report_html(analysis: dict, combined: dict, template_text: str) -> str:
    coverage = analysis["coverage_summary"]
    fixed = analysis["fixed_strike"]
    decision = combined["decision"]
    finance = combined["developer_finance_summary"]
    optimal_mix = analysis["optimal_mix"]
    revenue_path = analysis["developer_revenue_path"]
    year_one = analysis["year_one_financial_screen"]

    input_output_html = render_column(
        "Input",
        [
            "Started from the canonical Ninhsim 8760 load, Vietnam tariff defaults, and the agreed solar-plus-storage-only study scope.",
            "Pinned the year-one DPPA strike to 95% of the weighted EVN industrial tariff for `22-110 kV`, then escalated it with the same EVN-style rate used in the scenario financials.",
            "Treated excess renewable energy as merchant-sold volume using the repo's wholesale-to-weighted-EVN price ratio as the rough FMP proxy requested in the plan.",
        ],
    ) + render_column(
        "Output",
        [
            f"Solved a solar-plus-storage REopt case with `PV {optimal_mix['pv_size_mw']:.2f} MW`, `BESS {optimal_mix['bess_mw']:.2f} MW / {optimal_mix['bess_mwh']:.2f} MWh`, and delivered-energy coverage `{coverage['achieved_delivered_fraction_of_load'] * 100.0:.2f}%`.",
            f"Built the paired developer-finance artifact at a year-one realized blended price of `{year_one['realized_blended_price_vnd_per_kwh']:.2f} VND/kWh` after merchant exports are included.",
            f"Published the combined decision artifact and flagged the case as `{'financeable' if decision['financeable_at_default_target_irr'] else 'not financeable'}` at the default `{decision['target_project_irr_fraction'] * 100.0:.0f}%` project-IRR hurdle.",
        ],
    )

    mermaid_diagram = """
flowchart TD
    A[Reuse Ninhsim 8760 load and EVN tariff basis] --> B[Build solar plus storage only REopt scenario]
    B --> C[Apply Site renewable_electricity_min_fraction target]
    C --> D[Run REopt solve for PV plus BESS sizes]
    D --> E[Measure delivered renewable fraction and exported volume]
    E --> F{Delivered fraction >= requested 60%?}
    F -- No --> G[Report nearest feasible result and keep the achieved fraction explicit]
    F -- Yes --> H[Mark physical target achieved]
    G --> I[Peg year-one strike to 95% of weighted EVN tariff]
    H --> I
    I --> J[Estimate merchant revenue for excess energy with wholesale proxy]
    J --> K[Build PySAM Single Owner inputs from blended realized revenue price]
    K --> L[Run developer finance screen and combine REopt plus PySAM outputs]
""".strip()

    math_html = render_list(
        [
            "Coverage rule = `renewable_delivered_to_load / total_site_load`, with exported renewable energy excluded from the target basis even though it is still monetized separately for the developer.",
            f"Year-one strike = `0.95 x weighted EVN tariff` = `{fixed['year_one_strike_vnd_per_kwh']:.2f} VND/kWh`, then escalated by `{fixed['escalation_rate_fraction'] * 100.0:.1f}%/yr`.",
            f"Merchant proxy = `weighted EVN x wholesale ratio` = `{fixed['merchant_price_fraction_of_evn'] * 100.0:.1f}%` of the weighted EVN price in year one.",
            "PySAM receives a blended realized price stream because the local `Single Owner` wrapper models one escalated revenue price, not separate customer and merchant contracts.",
        ]
    )

    tools_html = render_tools_table(
        [
            (
                "scripts/python/integration/build_ninhsim_reopt_input.py",
                "Build the dedicated solar-plus-storage 60% REopt case",
                "Added Scenario C with wind removed and the delivered-energy target pinned onto the Site block.",
            ),
            (
                "reopt_pysam_vn.integration.ninhsim_solar_storage_60pct",
                "Hold the reusable 60% coverage, tariff peg, merchant proxy, and decision-artifact logic",
                "Kept the new phase logic in one canonical Python integration module instead of scattering it across scripts.",
            ),
            (
                "reopt_pysam_vn.integration.bridge",
                "Map the solved solar-plus-storage case into PySAM Single Owner inputs",
                "Built a dedicated Ninhsim 60% bridge without disturbing the older memo-driven Phase 4 path.",
            ),
            (
                "tests/python/integration/test_ninhsim_cppa.py + tests/python/pysam/test_single_owner_phase4.py",
                "Lock the tariff peg, coverage basis, scenario shape, and new PySAM bridge behavior",
                "Confirmed the new workflow contracts before the end-to-end run.",
            ),
        ]
    )

    labels = [str(entry["year"]) for entry in revenue_path[:10]]
    revenue_values = [
        round(entry["developer_revenue_usd"] / 1_000_000.0, 3)
        for entry in revenue_path[:10]
    ]
    customer_values = [
        round(entry["developer_revenue_from_customer_usd"] / 1_000_000.0, 3)
        for entry in revenue_path[:10]
    ]
    merchant_values = [
        round(entry["developer_revenue_from_merchant_usd"] / 1_000_000.0, 3)
        for entry in revenue_path[:10]
    ]
    coverage_values = [
        round(coverage["achieved_delivered_fraction_of_load"] * 100.0, 3),
        round(coverage["requested_target_fraction"] * 100.0, 3),
        round(coverage["enforced_target_fraction"] * 100.0, 3),
    ]

    charts_html = render_chart_block(
        "ninhsim60RevenueChart",
        "bar",
        {
            "labels": labels,
            "datasets": [
                {
                    "label": "Developer revenue (USD millions)",
                    "data": revenue_values,
                    "backgroundColor": "#00f5ff",
                },
                {
                    "label": "Customer revenue share",
                    "data": customer_values,
                    "backgroundColor": "#39ff14",
                },
                {
                    "label": "Merchant revenue share",
                    "data": merchant_values,
                    "backgroundColor": "#ff7a00",
                },
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "animation": False,
            "resizeDelay": 150,
            "normalized": True,
            "plugins": {"legend": {"position": "bottom"}},
            "scales": {
                "x": {"title": {"display": True, "text": "Year"}},
                "y": {"title": {"display": True, "text": "USD millions"}},
            },
        },
        height_px=320,
    ) + render_chart_block(
        "ninhsim60CoverageChart",
        "bar",
        {
            "labels": ["Achieved delivered", "Requested", "Enforced"],
            "datasets": [
                {
                    "label": "Coverage of site load (%)",
                    "data": coverage_values,
                    "backgroundColor": ["#00f5ff", "#ff7a00", "#39ff14"],
                }
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "animation": False,
            "resizeDelay": 150,
            "normalized": True,
            "plugins": {"legend": {"position": "bottom"}},
            "scales": {
                "x": {"title": {"display": True, "text": "Coverage basis"}},
                "y": {"title": {"display": True, "text": "Percent of load"}},
            },
        },
        height_px=320,
    )

    limitations_html = render_list(
        [
            "The local REopt case uses the site-level renewable-fraction constraint surface available in REopt; if solver behavior ever diverges from the intended delivered-to-load basis, the workflow will still rely on the explicit post-solve coverage calculation as the decision truth.",
            "PySAM Single Owner still accepts one escalated revenue price stream, so this phase approximates mixed customer plus merchant revenue with a blended realized price rather than a fully separated two-stream finance model.",
            "The merchant-energy value remains a rough proxy tied to the repo wholesale benchmark because the user asked for an estimated FMP path, not a project-specific nodal or hourly market forecast.",
        ]
    )

    warnings = list(analysis.get("warnings", []))
    if not warnings:
        warnings = ["The phase completed without notable implementation warnings."]
    if finance.get("project_return_aftertax_irr_fraction") is None:
        warnings.append(
            "PySAM returned a null-equivalent after-tax IRR, which usually means the configured cashflow never crosses into positive territory under the current revenue and cost assumptions."
        )
    elif not decision["financeable_at_default_target_irr"]:
        warnings.append(
            f"The developer finance screen stays below the default `{decision['target_project_irr_fraction'] * 100.0:.0f}%` project-IRR hurdle, so this exact commercial package is not yet investable without repricing or scope changes."
        )
    warnings_html = render_list(warnings)

    next_html = render_list(
        [
            "If the achieved delivered-energy coverage misses the requested 60% target, decide whether the next phase should widen the sensitivity band or keep the current nearest-feasible-result rule as the final answer.",
            "If the finance screen fails, test whether the gap should be closed by higher strike, lower capex assumptions, or a different export monetization path before changing the physical sizing logic.",
            "If merchant revenue becomes decision-critical, add a dedicated two-stream PySAM revenue model so customer-settled and spot-sold energy are no longer blended into one price input.",
        ]
    )

    replacements = {
        "{{PHASE_NAME}}": "Ninhsim Solar Storage 60% DPPA",
        "{{DATE}}": "2026-04-08",
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

    summary_sentence = (
        "This phase implemented the Ninhsim solar-plus-storage DPPA workflow, pegged the year-one strike to 95% of the weighted EVN tariff, "
        f"achieved `{coverage['achieved_delivered_fraction_of_load'] * 100.0:.2f}%` delivered renewable coverage, and flagged the case as "
        f"`{'financeable' if decision['financeable_at_default_target_irr'] else 'not financeable'}` at the default project-IRR hurdle."
    )
    return html.replace("{{SUMMARY_SENTENCE}}", summary_sentence)


def main() -> None:
    analysis = json.loads(DEFAULT_ANALYSIS_IN.read_text(encoding="utf-8"))
    combined = json.loads(DEFAULT_COMBINED_IN.read_text(encoding="utf-8"))
    template_text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    html = build_report_html(analysis, combined, template_text)
    DEFAULT_HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Ninhsim 60% HTML report written to: {DEFAULT_HTML_OUT}")


if __name__ == "__main__":
    main()
