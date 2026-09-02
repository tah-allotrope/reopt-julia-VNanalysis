"""Generate interim HTML reports for Ninhsim DPPA Case 1 phases A, B, and C."""

from __future__ import annotations

import json
import re
from pathlib import Path

from reopt_pysam_vn.common.reporting import phase_report_template

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORT_DATE = "2026-04-09"
PROJECT = "Saigon18 REopt Integration"
REPO = REPO_ROOT.name
DEFAULT_TEMPLATE = phase_report_template()
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
DEFAULT_SCENARIO_IN = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "reports"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "phase-report"


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


def render_empty_chart(message: str) -> str:
    return (
        '<div class="empty-state">'
        "<strong>No Chartable Data</strong>"
        f"<p>{message}</p>"
        "</div>"
    )


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


def render_report(template: str, phase: dict, output_dir: Path) -> Path:
    replacements = {
        "{{PHASE_NAME}}": phase["phase_name"],
        "{{DATE}}": REPORT_DATE,
        "{{PROJECT}}": PROJECT,
        "{{REPO}}": REPO,
        "{{INPUT_OUTPUT_CONTENT}}": phase["input_output_html"],
        "{{MERMAID_DIAGRAM}}": phase["mermaid"],
        "{{MATH_ALGORITHM_SECTION}}": phase["math_html"],
        "{{TOOLS_METHODS}}": phase["tools_html"],
        "{{CHARTS_SECTION}}": phase["charts_html"],
        "{{LIMITATIONS_ALTERNATIVES}}": phase["limitations_html"],
        "{{ERRORS_WARNINGS_FLAGS}}": phase["warnings_html"],
        "{{OPEN_QUESTIONS}}": phase["open_questions_html"],
    }
    html = template
    for token, value in replacements.items():
        html = html.replace(token, value)
    html = html.replace("{{SUMMARY_SENTENCE}}", phase["summary_sentence"])

    output_path = output_dir / f"{REPORT_DATE}-{slugify(phase['phase_name'])}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def build_phases(
    summary: dict, comparison: dict, combined: dict, scenario: dict
) -> list[dict]:
    energy = summary["energy_summary"]
    mix = summary["optimal_mix"]
    strike = summary["private_wire_strike"]
    decision = combined["decision"]
    scenario_meta = scenario.get("_meta", {})

    phase_a = {
        "phase_name": "DPPA Case 1 Phase A",
        "input_output_html": render_column(
            "Input",
            [
                "Started from the approved DPPA Case 1 plan, the canonical Ninhsim 8760 load basis, and the agreed private-wire commercial structure.",
                "Needed one frozen case definition that preserved near-zero-export intent, exact 2-hour BESS intent, solar-only charging, and project plus equity IRR as the final decision metrics.",
                "Needed naming and artifact paths that match the repo's existing Ninhsim workflow conventions.",
            ],
        )
        + render_column(
            "Output",
            [
                "Published the canonical scenario definition at `scenarios/case_studies/ninhsim/2026-04-09_ninhsim_dppa-case-1.json`.",
                f"Captured the frozen case intent as `{scenario_meta.get('target_design_intent', 'near_zero_export_full_site_use')}`, contract type `{scenario_meta.get('contract_type', 'private_wire')}`, and REopt objective `{scenario_meta.get('reopt_objective', 'minimum_lifecycle_cost_with_no_export_intent')}`.",
                "Locked the workflow onto the fuller `PVWatts + Battwatts + Utilityrate5 + Singleowner` PySAM path for downstream validation.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Review approved DPPA Case 1 plan] --> B[Freeze private-wire commercial basis]
    B --> C[Freeze near-zero-export and solar-only charging intent]
    C --> D[Lock exact 2-hour battery design intent]
    D --> E[Choose fuller PySAM module path]
    E --> F[Publish canonical scenario naming and artifact paths]
""".strip(),
        "math_html": render_list(
            [
                "Design intent is near-zero export first, not merchant optimization, so exports are discouraged and reported explicitly rather than treated as revenue upside.",
                "Battery intent is exact `2.0 h`, which means any final solve that returns `0 h` or another value must be treated as a failed design fit even if the optimization itself is feasible.",
                "Final screening metric pair is project IRR plus equity IRR, so the case cannot advance on export compliance alone.",
            ]
        ),
        "tools_html": render_tools_table(
            [
                (
                    "plans/active/dppa_case_1_plan.md",
                    "Hold the canonical case definition and agreed defaults",
                    "Kept the DPPA Case 1 interpretation stable before implementation started.",
                ),
                (
                    "activeContext.md",
                    "Track the implementation checklist and outputs",
                    "Preserved one synchronized execution log for the phase.",
                ),
                (
                    "build_ninhsim_reopt_input.py",
                    "Provide the canonical scenario surface",
                    "Added a dedicated `dppa_case_1` builder entrypoint and filename.",
                ),
            ]
        ),
        "charts_html": render_empty_chart(
            "Phase A freezes the case definition and implementation path; the meaningful quantitative outputs begin once the REopt scenario is built and run."
        ),
        "limitations_html": render_list(
            [
                "This checkpoint is intent-focused rather than result-focused, so it does not prove the chosen objective will actually force storage into the solution.",
                "The fuller PySAM path was selected for workstation stability, not because it is the most detailed physically possible option in PySAM.",
            ]
        ),
        "warnings_html": render_list(
            [
                "The agreed capex-minimization objective can still conflict with the exact-storage requirement if storage is not economically necessary under the current constraints.",
            ]
        ),
        "open_questions_html": render_list(
            [
                "If exact 2-hour storage is non-negotiable, the next phase may need to convert that requirement from intent into a stricter REopt minimum-storage formulation.",
            ]
        ),
        "summary_sentence": "DPPA Case 1 Phase A froze the scenario identity, private-wire basis, no-export intent, and fuller PySAM module path so implementation could proceed against one stable case definition.",
    }

    phase_b = {
        "phase_name": "DPPA Case 1 Phase B",
        "input_output_html": render_column(
            "Input",
            [
                "Needed a REopt case that removed wind, discouraged export, locked the battery design intent to 2 hours, and kept grid charging off.",
                "Needed new REopt-side analysis helpers that summarize export, curtailment, battery duration, and private-wire strike eligibility in machine-readable form.",
                "Needed proof that the new scenario validates and solves through the existing Julia runner path.",
            ],
        )
        + render_column(
            "Output",
            [
                f"Solved the first DPPA Case 1 REopt pass at `PV {mix['pv_size_mw']:.3f} MW` and `BESS {mix['bess_mw']:.3f} MW / {mix['bess_mwh']:.3f} MWh`.",
                f"Recorded `export {energy['export_fraction_of_generation'] * 100.0:.3f}%` of PV generation, `{energy['curtailed_renewable_kwh'] / 1_000_000.0:.3f} GWh` curtailment, and `{energy['renewable_delivered_kwh'] / 1_000_000.0:.3f} GWh` renewable delivery.",
                f"Produced the canonical REopt summary at `artifacts/reports/ninhsim/2026-04-09_ninhsim_dppa-case-1_reopt-summary.json`, which shows the case falls back to the `{strike['private_wire_tariff_key']}` private-wire ceiling at `{strike['year_one_private_wire_strike_vnd_per_kwh']:.2f} VND/kWh`.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Build DPPA Case 1 scenario JSON] --> B[No-solve Scenario validation]
    B --> C[Run full REopt solve]
    C --> D[Summarize export, curtailment, and battery duration]
    D --> E[Check private-wire BESS threshold eligibility]
    E --> F[Write canonical REopt summary artifact]
""".strip(),
        "math_html": render_list(
            [
                f"Solved export fraction = `{energy['exported_renewable_kwh']:.1f} / ({energy['pv_gwh']:.6f} x 1e6)` = `{energy['export_fraction_of_generation'] * 100.0:.3f}%`.",
                f"Solved battery duration = `{mix['bess_mwh']:.3f} / {mix['bess_mw']:.3f}` which collapses to `{mix['bess_duration_hours']:.3f} h` because REopt selected zero storage.",
                f"Private-wire tariff selection remains `{strike['private_wire_tariff_key']}` because the solved battery power fraction `{strike['battery_power_fraction_of_pv']:.3f}` and duration `{strike['battery_duration_hours']:.3f} h` do not clear the BESS thresholds.",
            ]
        ),
        "tools_html": render_tools_table(
            [
                (
                    "build_ninhsim_reopt_input.py",
                    "Assemble the DPPA Case 1 REopt scenario",
                    "Disabled wind and export pathways while preserving the Ninhsim load and tariff basis.",
                ),
                (
                    "run_vietnam_scenario.jl",
                    "Validate and solve the case through the canonical Julia path",
                    "Produced the solved REopt result JSON under `artifacts/results/ninhsim/`.",
                ),
                (
                    "reopt_pysam_vn.integration.dppa_case_1",
                    "Build the REopt-side summary and private-wire strike checks",
                    "Centralized the DPPA Case 1 design checks instead of scattering them across scripts.",
                ),
            ]
        ),
        "charts_html": render_chart_block(
            "dppaCase1PhaseBEnergy",
            "bar",
            {
                "labels": [
                    "PV energy",
                    "Delivered",
                    "Grid supplied",
                    "Curtailment",
                    "Export",
                ],
                "datasets": [
                    {
                        "label": "Energy (GWh)",
                        "data": [
                            round(energy["pv_gwh"], 3),
                            round(energy["renewable_delivered_kwh"] / 1_000_000.0, 3),
                            round(energy["grid_supplied_kwh"] / 1_000_000.0, 3),
                            round(energy["curtailed_renewable_kwh"] / 1_000_000.0, 3),
                            round(energy["exported_renewable_kwh"] / 1_000_000.0, 3),
                        ],
                        "backgroundColor": [
                            "#00f5ff",
                            "#39ff14",
                            "#ff7a00",
                            "#ff4d6d",
                            "#ffd400",
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
        ),
        "limitations_html": render_list(
            [
                "The current objective solves a feasible low-export case, but it does not guarantee a nonzero battery buildout.",
                "The solve also inherits the usual non-US AVERT/EASIUR/Cambium warnings from the Vietnam coordinate, which are expected but noisy.",
            ]
        ),
        "warnings_html": render_list(
            [
                "REopt selected zero battery in this first pass, so the case fails the practical exact-2-hour-storage requirement even though the optimization status is optimal.",
            ]
        ),
        "open_questions_html": render_list(
            [
                "The next iteration likely needs either a stricter storage floor or an objective change if the project must include a real 2-hour battery rather than allowing storage to optimize away.",
            ]
        ),
        "summary_sentence": "DPPA Case 1 Phase B built and solved the dedicated REopt scenario, proving the no-export-intent path works but also exposing that the current capex-minimizing formulation optimizes battery capacity away entirely.",
    }

    phase_c = {
        "phase_name": "DPPA Case 1 Phase C",
        "input_output_html": render_column(
            "Input",
            [
                "Needed a fuller PySAM runner that could map the REopt candidate into `PVWatts + Battwatts + Utilityrate5 + Singleowner` with solar-only charging and zero export value.",
                "Needed comparison and combined-decision artifacts that remain machine-readable even if the REopt outcome does not contain a real battery to simulate.",
                "Needed review surfaces that explain whether the case advances or needs resize/reprice action.",
            ],
        )
        + render_column(
            "Output",
            [
                "Added the fuller PySAM bridge and runner, then produced a canonical placeholder PySAM artifact instead of crashing when the REopt result came back with zero battery.",
                f"Published the REopt-vs-PySAM comparison and combined decision artifacts; the current recommendation is `{decision['recommended_position']}`.",
                "The combined decision passes export design but fails finance advancement because both project and equity IRR screens remain unavailable once the battery workflow is skipped for the zero-battery solve.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Load solved REopt candidate] --> B[Build fuller PySAM PVWatts battery inputs]
    B --> C{Battery selected by REopt?}
    C -- Yes --> D[Run fuller PySAM battery and finance workflow]
    C -- No --> E[Emit canonical skipped PySAM placeholder]
    D --> F[Compare REopt and PySAM]
    E --> F
    F --> G[Build combined decision artifact]
    G --> H[Publish final and interim HTML reports]
""".strip(),
        "math_html": render_list(
            [
                f"Current decision state = export passes `{decision['export_design_passes']}`, project IRR passes `{decision['financeable_at_default_project_irr']}`, equity IRR passes `{decision['financeable_at_default_equity_irr']}`.",
                "When REopt returns zero battery, the fuller PySAM lane is skipped intentionally and emits null finance metrics instead of a runtime failure so the workflow remains reviewable.",
                f"Comparison alignment is still exact on delivered energy and curtailment in the placeholder path, with delivered delta `{comparison['energy_alignment']['delivered_delta_kwh']:.3f} kWh` and export delta `{comparison['energy_alignment']['pysam_export_delta_kwh']:.3f} kWh`.",
            ]
        ),
        "tools_html": render_tools_table(
            [
                (
                    "reopt_pysam_vn.pysam.pvwatts_battery",
                    "Hold the fuller PySAM PV+battery runtime",
                    "Provides the stable workstation-supported PVWatts battery path for future nonzero-storage runs.",
                ),
                (
                    "run_ninhsim_dppa_case_1_pvwatts.py",
                    "Execute the fuller PySAM stage or emit a canonical placeholder",
                    "Kept the end-to-end workflow from failing when REopt selected zero battery.",
                ),
                (
                    "analyze_ninhsim_dppa_case_1.py",
                    "Build comparison and combined-decision artifacts",
                    "Produced the machine-readable recommendation used by the final reports.",
                ),
            ]
        ),
        "charts_html": render_chart_block(
            "dppaCase1PhaseCDecision",
            "bar",
            {
                "labels": ["Export pass", "Project IRR pass", "Equity IRR pass"],
                "datasets": [
                    {
                        "label": "Decision flags",
                        "data": [
                            1 if decision["export_design_passes"] else 0,
                            1 if decision["financeable_at_default_project_irr"] else 0,
                            1 if decision["financeable_at_default_equity_irr"] else 0,
                        ],
                        "backgroundColor": ["#39ff14", "#ff7a00", "#ff4d6d"],
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
                    "x": {"title": {"display": True, "text": "Decision screen"}},
                    "y": {
                        "title": {"display": True, "text": "Pass = 1 / Fail = 0"},
                        "ticks": {"stepSize": 1},
                    },
                },
            },
        ),
        "limitations_html": render_list(
            [
                "This phase proves the orchestration and fallback behavior, but it does not yet produce a real fuller-battery finance result because the first REopt solve contains no storage.",
                "The placeholder PySAM artifact is intentionally conservative: it preserves energy alignment but does not invent finance values that the battery workflow did not actually compute.",
            ]
        ),
        "warnings_html": render_list(
            [
                "The workflow is operationally complete, but the current business result is still a red flag because the solve selected zero battery under a case that was meant to represent a 2-hour battery project.",
            ]
        ),
        "open_questions_html": render_list(
            [
                "The next material modeling decision is whether to force a nonzero battery in REopt or to change the commercial objective so storage remains part of the optimal solution before rerunning the fuller PySAM lane.",
            ]
        ),
        "summary_sentence": "DPPA Case 1 Phase C completed the fuller PySAM orchestration, comparison, and decision surfaces, but the current recommendation remains `needs_reprice_or_resize` because the first REopt solve eliminated storage and forced the battery lane into a conservative skipped state.",
    }

    return [phase_a, phase_b, phase_c]


def main() -> None:
    template = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    summary = json.loads(DEFAULT_SUMMARY_IN.read_text(encoding="utf-8"))
    comparison = json.loads(DEFAULT_COMPARISON_IN.read_text(encoding="utf-8"))
    combined = json.loads(DEFAULT_COMBINED_IN.read_text(encoding="utf-8"))
    scenario = json.loads(DEFAULT_SCENARIO_IN.read_text(encoding="utf-8"))
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for phase in build_phases(summary, comparison, combined, scenario):
        out_path = render_report(template, phase, DEFAULT_OUTPUT_DIR)
        print(f"Generated phase report: {out_path}")


if __name__ == "__main__":
    main()
