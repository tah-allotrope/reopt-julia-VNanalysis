"""Generate the Ninhsim DPPA Case 1 HTML report."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_SUMMARY_IN = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1_reopt-summary.json"
)
DEFAULT_COMPARISON_IN = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1_comparison.json"
)
DEFAULT_COMBINED_IN = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1_combined-decision.json"
)
DEFAULT_HTML_OUT = REPO_ROOT / "reports" / "2026-04-09-dppa-case-1-final.html"
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


def build_report_html(
    summary: dict, comparison: dict, combined: dict, template_text: str
) -> str:
    energy = summary["energy_summary"]
    mix = summary["optimal_mix"]
    strike = summary["private_wire_strike"]
    comparison_energy = comparison["energy_alignment"]
    finance_alignment = comparison["financial_alignment"]
    decision = combined["decision"]
    _pysam = combined["pysam_summary"]

    input_output_html = render_column(
        "Input",
        [
            "Started from the canonical Ninhsim 8760 industrial load, south-region tariff basis, and a private-wire DPPA case definition.",
            "Locked the REopt battery to an exact 2-hour duration, disabled wind, disabled PV export pathways, and kept battery grid charging off.",
            "Mapped the solved REopt PV and BESS sizes into a fuller PySAM `PVWatts + Battwatts + Utilityrate5 + Singleowner` flow with a private-wire strike ceiling and zero sell rate.",
        ],
    ) + render_column(
        "Output",
        [
            f"Built a REopt summary with `PV {mix['pv_size_mw']:.2f} MW`, `BESS {mix['bess_mw']:.2f} MW / {mix['bess_mwh']:.2f} MWh`, and export fraction `{energy['export_fraction_of_generation'] * 100.0:.3f}%`.",
            f"Carried the south private-wire strike basis at `{strike['year_one_private_wire_strike_vnd_per_kwh']:.2f} VND/kWh` and checked whether the solved battery clears the BESS-qualified ceiling thresholds.",
            f"Combined the REopt and fuller PySAM views into a final recommendation of `{'advance_for_review' if decision['recommended_position'] == 'advance_for_review' else 'needs_reprice_or_resize'}` using both project and equity IRR hurdles.",
        ],
    )

    mermaid_diagram = """
flowchart TD
    A[Reuse Ninhsim 8760 load and tariff basis] --> B[Build DPPA Case 1 REopt scenario]
    B --> C[Disable wind and export, lock 2-hour BESS, keep solar-only charging]
    C --> D[Run REopt for first-pass PV plus BESS sizing]
    D --> E[Summarize export, curtailment, battery duration, and private-wire strike basis]
    E --> F[Map solved sizes into PVWatts plus Battwatts plus Singleowner]
    F --> G[Run fuller PySAM PV plus battery and finance workflow]
    G --> H[Compare REopt and PySAM energy alignment]
    H --> I[Screen project IRR and equity IRR]
    I --> J[Publish combined DPPA Case 1 decision artifact]
""".strip()

    math_html = render_list(
        [
            "Private-wire strike basis uses the Decree 57 south-region ceiling, switching to the `solar_ground_with_bess` ceiling only when the solved battery clears the repo's BESS threshold checks.",
            f"Battery duration check = `size_kwh / size_kw` = `{mix['bess_duration_hours']:.3f} h`, and the design passes only when that stays exactly at `2.0 h` within tolerance.",
            f"Export design check = `exported_renewable_kwh / PV year-one generation` = `{energy['export_fraction_of_generation'] * 100.0:.3f}%`, with the current negligible-export threshold set to `0.5%`.",
            "Final recommendation logic requires negligible-export design plus both project IRR and equity IRR to clear the default hurdles before the case advances.",
        ]
    )

    tools_html = render_tools_table(
        [
            (
                "scripts/python/integration/build_ninhsim_reopt_input.py",
                "Build the dedicated DPPA Case 1 REopt scenario",
                "Created a private-wire, solar-only, no-export-intent case with exact 2-hour storage bounds.",
            ),
            (
                "reopt_pysam_vn.integration.dppa_case_1",
                "Hold the canonical REopt summary, strike basis, comparison, and combined-decision logic",
                "Kept the DPPA Case 1 screening rules in one reusable integration module.",
            ),
            (
                "reopt_pysam_vn.pysam.pvwatts_battery",
                "Run the fuller PVWatts battery PySAM path",
                "Used the workstation-stable fuller PySAM stack instead of the older finance-only custom generation shortcut.",
            ),
            (
                "scripts/python/integration/run_ninhsim_dppa_case_1*.py",
                "Provide end-to-end orchestration and a dedicated fuller PySAM runner",
                "Matched the script shape of the existing Ninhsim workflows so artifacts land in canonical repo paths.",
            ),
        ]
    )

    chart_html = render_chart_block(
        "dppaCase1EnergyChart",
        "bar",
        {
            "labels": [
                "REopt delivered",
                "PySAM delivered",
                "REopt export",
                "PySAM export",
                "REopt curtailment",
                "PySAM curtailment",
            ],
            "datasets": [
                {
                    "label": "Energy (GWh)",
                    "data": [
                        round(energy["renewable_delivered_kwh"] / 1_000_000.0, 3),
                        round(
                            comparison_energy["pysam_delivered_kwh"] / 1_000_000.0, 3
                        ),
                        round(energy["exported_renewable_kwh"] / 1_000_000.0, 3),
                        round(comparison_energy["pysam_export_kwh"] / 1_000_000.0, 3),
                        round(energy["curtailed_renewable_kwh"] / 1_000_000.0, 3),
                        round(
                            comparison_energy["pysam_curtailment_kwh"] / 1_000_000.0, 3
                        ),
                    ],
                    "backgroundColor": [
                        "#00f5ff",
                        "#39ff14",
                        "#ff7a00",
                        "#ffd400",
                        "#ff4d6d",
                        "#7b61ff",
                    ],
                }
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "animation": False,
            "resizeDelay": 150,
            "normalized": True,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "x": {"title": {"display": True, "text": "Energy channel"}},
                "y": {"title": {"display": True, "text": "GWh"}},
            },
        },
    ) + render_chart_block(
        "dppaCase1FinanceChart",
        "bar",
        {
            "labels": ["Project IRR", "Equity IRR", "Project target", "Equity target"],
            "datasets": [
                {
                    "label": "IRR (%)",
                    "data": [
                        round(
                            float(finance_alignment.get("project_irr_fraction") or 0.0)
                            * 100.0,
                            3,
                        ),
                        round(
                            float(finance_alignment.get("equity_irr_fraction") or 0.0)
                            * 100.0,
                            3,
                        ),
                        round(
                            float(summary["financial"]["target_project_irr_fraction"])
                            * 100.0,
                            3,
                        ),
                        round(
                            float(summary["financial"]["target_equity_irr_fraction"])
                            * 100.0,
                            3,
                        ),
                    ],
                    "backgroundColor": ["#00f5ff", "#39ff14", "#ff7a00", "#ff4d6d"],
                }
            ],
        },
        {
            "responsive": True,
            "maintainAspectRatio": False,
            "animation": False,
            "resizeDelay": 150,
            "normalized": True,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "x": {"title": {"display": True, "text": "Finance metric"}},
                "y": {"title": {"display": True, "text": "Percent"}},
            },
        },
    )

    warnings = list(summary.get("warnings", [])) + list(combined.get("warnings", []))
    if not warnings:
        warnings = ["The DPPA Case 1 artifacts did not report any explicit warnings."]
    if not decision["export_design_passes"]:
        warnings.append(
            "The REopt design still exports enough energy to fail the current negligible-export screen, so the case should be resized or repriced before advancing."
        )
    if (
        not decision["financeable_at_default_project_irr"]
        or not decision["financeable_at_default_equity_irr"]
    ):
        warnings.append(
            "The fuller PySAM finance screen does not currently clear both default IRR hurdles, so the case should not advance without repricing or a bounded resize."
        )
    warnings_html = render_list(warnings)

    limitations_html = render_list(
        [
            "The fuller PySAM lane uses `PVWatts + Battwatts` rather than the more detailed `Pvsamv1` stack because that path was the stable workstation-supported configuration during implementation.",
            "REopt still provides the first-pass sizing truth, so any material REopt-versus-PySAM mismatch should trigger a bounded iteration rather than treating the PySAM pass as a fresh optimizer.",
            "The current report assumes the private-wire price ceiling is the governing commercial anchor; if a negotiated discount or upside sharing rule is added later, the finance screen should be rerun with that contract path explicitly modeled.",
        ]
    )

    next_html = render_list(
        [
            "If the combined decision fails, decide whether the next pass should change strike, capex assumptions, or the initial REopt size bounds before widening scope.",
            "If REopt and PySAM disagree materially on export or curtailment, add a bounded resize loop that nudges the REopt candidate down until both engines stay inside the no-excess tolerance.",
            "If this case becomes the preferred commercial template, add interim phase report generation so the repo also publishes the requested `phase-a`, `phase-b`, and `phase-c` HTML checkpoints automatically.",
        ]
    )

    replacements = {
        "{{PHASE_NAME}}": "Ninhsim DPPA Case 1",
        "{{DATE}}": "2026-04-09",
        "{{PROJECT}}": "Saigon18 REopt Integration",
        "{{REPO}}": "reopt-pysam-vn",
        "{{INPUT_OUTPUT_CONTENT}}": input_output_html,
        "{{MERMAID_DIAGRAM}}": mermaid_diagram,
        "{{MATH_ALGORITHM_SECTION}}": math_html,
        "{{TOOLS_METHODS}}": tools_html,
        "{{CHARTS_SECTION}}": chart_html,
        "{{LIMITATIONS_ALTERNATIVES}}": limitations_html,
        "{{ERRORS_WARNINGS_FLAGS}}": warnings_html,
        "{{OPEN_QUESTIONS}}": next_html,
    }

    html = template_text
    for token, value in replacements.items():
        html = html.replace(token, value)

    summary_sentence = (
        "This phase implemented the Ninhsim DPPA Case 1 workflow, carried a private-wire no-excess REopt sizing pass into a fuller PySAM PV-plus-battery model, and "
        f"ended with a recommendation of `{decision['recommended_position']}` after checking both export tolerance and the default project plus equity IRR hurdles."
    )
    return html.replace("{{SUMMARY_SENTENCE}}", summary_sentence)


def main() -> None:
    summary = json.loads(DEFAULT_SUMMARY_IN.read_text(encoding="utf-8"))
    comparison = json.loads(DEFAULT_COMPARISON_IN.read_text(encoding="utf-8"))
    combined = json.loads(DEFAULT_COMBINED_IN.read_text(encoding="utf-8"))
    template_text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    html = build_report_html(summary, comparison, combined, template_text)
    DEFAULT_HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_HTML_OUT.write_text(html, encoding="utf-8")
    print(f"DPPA Case 1 HTML report written to: {DEFAULT_HTML_OUT}")


if __name__ == "__main__":
    main()
