"""Generate Phase A and B HTML reports for Ninhsim DPPA Case 2."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORT_DATE = "2026-04-14"
PROJECT = REPO_ROOT.name
REPO = str(REPO_ROOT)
TEMPLATE_PATH = (
    Path.home() / ".claude" / "skills" / "report" / "assets" / "template.html"
)
OUTPUT_DIR = REPO_ROOT / "reports"

PHASE_A_DEFINITION = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_phase-a-definition.json"
)
PHASE_A_ASSUMPTIONS = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_phase-a-assumptions-register.json"
)
PHASE_B_DESIGN = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_phase-b-settlement-design.json"
)
PHASE_B_SCHEMA = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_phase-b-settlement-schema.json"
)
PHASE_B_EDGE_CASES = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_phase-b-edge-case-matrix.json"
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _list_html(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _io_html(narrative: str, inputs: list[str], outputs: list[str]) -> str:
    return (
        f'<p class="narrative">{narrative}</p>'
        '<div class="io-grid">'
        '<div class="io-col io-col--in">'
        '<div class="io-col-label">Inputs</div>'
        f"{_list_html(inputs)}"
        "</div>"
        '<div class="io-col io-col--out">'
        '<div class="io-col-label">Outputs</div>'
        f"{_list_html(outputs)}"
        "</div>"
        "</div>"
    )


def _tools_html(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _math_html(items: list[str]) -> str:
    return '<div class="math-content">' + _list_html(items) + "</div>"


def _limits_html(limitations: list[str], alternative: list[str]) -> str:
    return (
        '<div class="limits-grid">'
        '<div class="limits-col limits-col--current">'
        '<div class="limits-col-label">Limitations</div>'
        f"{_list_html(limitations)}"
        "</div>"
        '<div class="limits-col limits-col--alt">'
        '<div class="limits-col-label">2nd-Best Alternative</div>'
        f"{_list_html(alternative)}"
        "</div>"
        "</div>"
    )


def _errors_html(entries: list[tuple[str, str]]) -> str:
    if not entries:
        return '<div class="no-data">Phase completed without errors, warnings, or flags.</div>'
    badge_class = {"ERROR": "error", "WARN": "warn", "FLAG": "flag"}
    items = []
    for severity, text in entries:
        items.append(
            "<li>"
            f'<span class="badge badge--{badge_class[severity]}">[{severity}]</span>'
            f"<span>{text}</span>"
            "</li>"
        )
    return '<ul class="errors-list">' + "".join(items) + "</ul>"


def _charts_html(charts: list[str]) -> str:
    return '<div class="charts-grid">' + "".join(charts) + "</div>"


def _chart_card(title: str, canvas_id: str, chart_config: dict) -> str:
    config_json = json.dumps(chart_config, ensure_ascii=True)
    return (
        '<div class="chart-card">'
        f'<div class="chart-card-title">{title}</div>'
        '<div class="chart-wrap">'
        f'<canvas id="{canvas_id}"></canvas>'
        "</div>"
        "<script>"
        f"new Chart(document.getElementById('{canvas_id}'), {config_json});"
        "</script>"
        "</div>"
    )


def _open_questions_html(questions: list[str], next_steps: list[str]) -> str:
    return (
        '<div class="questions-grid">'
        '<div class="questions-col questions-col--questions">'
        '<div class="questions-col-label">Open Questions</div>'
        f"{_list_html(questions)}"
        "</div>"
        '<div class="questions-col questions-col--next">'
        '<div class="questions-col-label">Next Phase Seeds</div>'
        f"{_list_html(next_steps)}"
        "</div>"
        "</div>"
    )


def _render_report(phase_name: str, sections: dict) -> Path:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "{{PHASE_NAME}}": phase_name,
        "{{DATE}}": REPORT_DATE,
        "{{PROJECT}}": PROJECT,
        "{{REPO}}": REPO,
        "{{INPUT_OUTPUT_CONTENT}}": sections["input_output"],
        "{{MERMAID_DIAGRAM}}": sections["mermaid"],
        "{{TOOLS_METHODS}}": sections["tools"],
        "{{MATH_ALGORITHM}}": sections["math"],
        "{{LIMITATIONS_ALTERNATIVE}}": sections["limits"],
        "{{ERRORS_WARNINGS}}": sections["errors"],
        "{{CHARTS_SECTION}}": sections["charts"],
        "{{OPEN_QUESTIONS}}": sections["open_questions"],
    }
    html = template
    for token, value in replacements.items():
        html = html.replace(token, value)
    output_path = OUTPUT_DIR / f"{REPORT_DATE}-{_slugify(phase_name)}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def build_phase_a_report() -> Path:
    definition = _read_json(PHASE_A_DEFINITION)
    assumptions = _read_json(PHASE_A_ASSUMPTIONS)
    strike = definition["strike_basis"]
    _site = definition["site_load_basis"]["site"]
    primary_count = len(definition["decision_metrics"]["primary_metrics"])
    secondary_count = len(definition["decision_metrics"]["secondary_metrics"])
    in_scope_count = len(definition["physical_scope"]["technologies_in_scope"])
    open_inputs_count = len(assumptions["known_open_inputs"])

    sections = {
        "input_output": _io_html(
            (
                "Phase A froze the DPPA Case 2 identity around the user-approved synthetic DPPA structure, the reused Ninhsim 8760 load basis, and an auditable assumptions register so later implementation can distinguish physical sizing from buyer-side settlement logic."
            ),
            [
                "User-approved `plans/active/dppa_case_2_plan.md` baseline with all 12 review answers resolved.",
                "Existing Ninhsim extracted inputs at `data/interim/ninhsim/ninhsim_extracted_inputs.json` for site, load, and tariff basis reuse.",
                "Constraint to treat customer best interest as the priority even if developer overlap is weak.",
            ],
            [
                "Published `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_phase-a-definition.json`.",
                "Published `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_phase-a-assumptions-register.json`.",
                f"Locked year-one strike anchor at `{strike['year_one_strike_vnd_per_kwh']:.6f} VND/kWh`, which is 5% below the current weighted EVN benchmark.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Read approved Case 2 plan] --> B{Freeze contract structure?}
    B -->|Synthetic only| C[Reuse Ninhsim site and 8760 load basis]
    C --> D[Anchor strike at 5% below weighted EVN tariff]
    D --> E[Capture user answers in assumptions register]
    E --> F[Publish canonical Phase A definition artifacts]
""".strip(),
        "tools": _tools_html(
            [
                "`apply_patch` - add the new Case 2 helper module, preparation script, and package exports.",
                "`pytest` - prove the new Phase A/B artifact contract before generating reports.",
                "`prepare_ninhsim_dppa_case_2_phase_ab.py` - write canonical Phase A and B JSON outputs.",
                "Report skill template - render the synchronized HTML phase report from the loaded `/report` workflow.",
            ]
        ),
        "math": _math_html(
            [
                f"Year-one strike = weighted EVN tariff x (1 - discount) = `{strike['weighted_evn_price_vnd_per_kwh']:.6f} x (1 - 0.05)` = `{strike['year_one_strike_vnd_per_kwh']:.6f} VND/kWh`.",
                "Phase A used a simple assumption-freeze procedure: convert every answered planning question into one canonical selected answer and one short implementation summary.",
                f"Primary metric count = `{primary_count}`, secondary metric count = `{secondary_count}`, which keeps buyer metrics ahead of developer and risk screens rather than blending them too early.",
            ]
        ),
        "limits": _limits_html(
            [
                "Phase A freezes assumptions, but it does not yet prove that the chosen REopt objective can be expressed cleanly in the existing solve surface.",
                "The market-price source is still unresolved for Ninhsim, so the settlement layer cannot yet distinguish actual hourly CFMP/FMP from a fallback proxy.",
            ],
            [
                "A lighter alternative was to defer the assumptions register and embed user answers only inside the markdown plan.",
                "The chosen JSON artifacts won because later code, tests, and reports can consume them directly without re-parsing prose from the plan file.",
            ],
        ),
        "errors": _errors_html(
            [
                (
                    "FLAG",
                    "Trusted Ninhsim hourly `FMP`/`CFMP` data is still open; Phase A records this as a known input gap instead of pretending the market series is already settled.",
                ),
                (
                    "FLAG",
                    "Battery remains optional by user instruction, so a valid Case 2 physical solve may still collapse to PV-only even though the broader repo has several solar-plus-storage precedents.",
                ),
            ]
        ),
        "charts": _charts_html(
            [
                _chart_card(
                    "Phase A Counts",
                    "phaseAChart",
                    {
                        "type": "bar",
                        "data": {
                            "labels": [
                                "Primary metrics",
                                "Secondary metrics",
                                "Tech in scope",
                                "Open inputs",
                            ],
                            "datasets": [
                                {
                                    "label": "Count",
                                    "data": [
                                        primary_count,
                                        secondary_count,
                                        in_scope_count,
                                        open_inputs_count,
                                    ],
                                    "backgroundColor": [
                                        "#00f5ff",
                                        "#39ff14",
                                        "#ffd700",
                                        "#ff2d78",
                                    ],
                                }
                            ],
                        },
                        "options": {
                            "responsive": True,
                            "maintainAspectRatio": False,
                            "plugins": {"legend": {"display": False}},
                        },
                    },
                )
            ]
        ),
        "open_questions": _open_questions_html(
            [
                "Can Ninhsim get a trusted hourly market-price series locally, or does Phase C/D need an external-source-backed proxy path first?",
                "Does the planned REopt objective need a custom post-processing screen rather than a direct solver objective translation?",
            ],
            [
                f"Use the frozen contract structure `{definition['case_identity']['contract_structure']}` as the only Case 2 commercial basis going into Phase B/C.",
                f"Carry the fixed strike anchor `{strike['year_one_strike_vnd_per_kwh']:.6f} VND/kWh` into the settlement design and future scenario metadata.",
            ],
        ),
    }
    return _render_report("DPPA Case 2 Phase A", sections)


def build_phase_b_report() -> Path:
    design = _read_json(PHASE_B_DESIGN)
    schema = _read_json(PHASE_B_SCHEMA)
    edge_cases = _read_json(PHASE_B_EDGE_CASES)
    buyer_output_count = len(design["separate_outputs"]["buyer_view"])
    developer_output_count = len(design["separate_outputs"]["developer_view"])
    risk_output_count = len(design["separate_outputs"]["risk_view"])
    edge_case_count = len(edge_cases["cases"])
    required_count = len(schema["required"])

    sections = {
        "input_output": _io_html(
            (
                "Phase B turned the approved commercial assumptions into a canonical settlement ledger design, a machine-readable schema, and an edge-case matrix so Case 2 now has an explicit buyer-payment contract before any physical solve or PySAM finance run is wired in."
            ),
            [
                "Phase A definition and assumptions register from the new Case 2 design artifacts.",
                "Buyer-guide research requirement to keep EVN payment, DPPA adder, KPP, and CfD true-up explicit.",
                "User instruction to exclude excess generation from buyer settlement while still reporting it separately.",
            ],
            [
                "Published `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_phase-b-settlement-design.json`.",
                "Published `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_phase-b-settlement-schema.json`.",
                "Published `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_phase-b-edge-case-matrix.json` with four canonical settlement test scenarios.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Start from Phase A assumptions] --> B[Define matched shortfall and excess formulas]
    B --> C[Define buyer EVN payment DPPA adder and CfD formulas]
    C --> D{How is excess treated?}
    D -->|Excluded| E[Cap buyer settlement at matched quantity]
    E --> F[Publish settlement schema and edge-case matrix]
""".strip(),
        "tools": _tools_html(
            [
                "`reopt_pysam_vn.integration.dppa_case_2` - holds the settlement design, schema, and edge-case matrix builders.",
                "`pytest` - validates the schema and design surfaces through `tests/python/integration/test_dppa_case_2_phase_ab.py`.",
                "JSON schema pattern - freezes required hourly inputs and enumerated business-rule choices before implementation expands.",
                "Report skill template - renders the synchronized Phase B HTML output in the standard 9-section report shape.",
            ]
        ),
        "math": _math_html(
            [
                "Matched quantity formula = `min(load_kwh, contracted_generation_kwh)`.",
                "Shortfall quantity formula = `max(0, load_kwh - matched_quantity_kwh)`.",
                "Excess quantity formula = `max(0, contracted_generation_kwh - matched_quantity_kwh)` and is explicitly excluded from buyer settlement in this first-pass design.",
                "Buyer total payment formula = `EVN matched payment + DPPA adder + shortfall payment + buyer CfD payment`.",
                f"The schema currently requires `{required_count}` core fields so the future settlement runner cannot silently skip market price, tariff, strike, adder, or KPP inputs.",
            ]
        ),
        "limits": _limits_html(
            [
                "Phase B still freezes a design contract rather than a runnable settlement engine, so it validates structure but not yet full hourly arithmetic against real Ninhsim inputs.",
                "Fixed DPPA adder and fixed KPP are deliberate user choices, but they remain placeholders until grounded in the final selected data source for Case 2.",
            ],
            [
                "A broader alternative was to implement the full settlement runner immediately and let the contract emerge from code behavior.",
                "The chosen design-first step won because the buyer-payment mechanics are policy-sensitive and benefit from a frozen schema and edge-case matrix before arithmetic code is allowed to sprawl.",
            ],
        ),
        "errors": _errors_html(
            [
                (
                    "WARN",
                    "The current settlement design allows negative buyer CfD credit on matched quantity when market price exceeds strike, which is faithful to the buyer guide but still needs confirmation once the exact market-price source is selected.",
                ),
                (
                    "FLAG",
                    "Excess generation is excluded from buyer settlement by user decision, which deliberately removes one stressed-risk path from the first-pass economics and should be revisited later if contract terms change.",
                ),
                (
                    "FLAG",
                    "The schema points first to actual hourly `CFMP`/`FMP` but does not yet identify a trusted Ninhsim source file, so Phase C/D must resolve the series before final settlement outputs are treated as bankable.",
                ),
            ]
        ),
        "charts": _charts_html(
            [
                _chart_card(
                    "Settlement Surface Counts",
                    "phaseBChart",
                    {
                        "type": "bar",
                        "data": {
                            "labels": [
                                "Buyer outputs",
                                "Developer outputs",
                                "Risk outputs",
                                "Edge cases",
                                "Required schema fields",
                            ],
                            "datasets": [
                                {
                                    "label": "Count",
                                    "data": [
                                        buyer_output_count,
                                        developer_output_count,
                                        risk_output_count,
                                        edge_case_count,
                                        required_count,
                                    ],
                                    "backgroundColor": [
                                        "#00f5ff",
                                        "#39ff14",
                                        "#ff2d78",
                                        "#ffd700",
                                        "#bf5fff",
                                    ],
                                }
                            ],
                        },
                        "options": {
                            "responsive": True,
                            "maintainAspectRatio": False,
                            "plugins": {"legend": {"display": False}},
                        },
                    },
                )
            ]
        ),
        "open_questions": _open_questions_html(
            [
                "Should the future runnable settlement engine prefer `CFMP` over `FMP` whenever both are available, or expose both series explicitly in the result artifact?",
                "How should the developer-side PySAM path consume the new buyer settlement outputs without collapsing them back into one blended revenue price?",
            ],
            [
                "Implement the runnable hourly settlement engine against the frozen schema before building combined buyer benchmark artifacts.",
                "Resolve the actual-versus-proxy market series question early in Phase C/D so the first buyer-cost outputs are not blocked by source ambiguity.",
            ],
        ),
    }
    return _render_report("DPPA Case 2 Phase B", sections)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    phase_a_path = build_phase_a_report()
    phase_b_path = build_phase_b_report()
    print(f"Report saved -> {phase_a_path.relative_to(REPO_ROOT)}")
    print(f"Report saved -> {phase_b_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
