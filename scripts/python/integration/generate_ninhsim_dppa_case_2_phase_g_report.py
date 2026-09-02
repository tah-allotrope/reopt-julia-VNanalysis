"""Generate the Phase G HTML report for Ninhsim DPPA Case 2."""

from __future__ import annotations

import json
import re
from pathlib import Path

from reopt_pysam_vn.common.reporting import phase_report_template

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORT_DATE = "2026-04-15"
PROJECT = REPO_ROOT.name
REPO = str(REPO_ROOT)
TEMPLATE_PATH = phase_report_template()
OUTPUT_DIR = REPO_ROOT / "reports"

COMBINED = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_combined-decision.json"
)
FINAL = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_final-summary.json"
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
    return _list_html(items)


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


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    combined = _read_json(COMBINED)
    _final_summary = _read_json(FINAL)

    decision = combined["decision"]
    findings = combined["critical_findings"]
    chart = _chart_card(
        "Phase G Critical Findings",
        "phaseGDecisionChart",
        {
            "type": "bar",
            "data": {
                "labels": [
                    "Buyer premium kVND",
                    "Best dev NPV kUSD",
                    "Excess stress kVND",
                ],
                "datasets": [
                    {
                        "label": "Value",
                        "data": [
                            findings["buyer_premium_vnd"] / 1000.0,
                            findings["best_tested_developer_npv_usd"] / 1000.0,
                            findings["excess_cfd_stress_vnd"] / 1000.0,
                        ],
                        "backgroundColor": ["#ff2d78", "#ffd700", "#00f5ff"],
                    }
                ],
            },
            "options": {"responsive": True, "maintainAspectRatio": False},
        },
    )

    sections = {
        "input_output": _io_html(
            "Phase G assembled the published Phase C-F artifacts into one explicit Case 2 decision package, then added a final closeout summary because the workflow now spans multiple phases and ends with a clear reject-or-revise recommendation.",
            [
                "Published Phase C physical summary, Phase E sensitivities, and Phase F developer screening artifacts.",
                "Existing combined-decision and final-report patterns from earlier Ninhsim workflows.",
                "Requirement to make the final recommendation explicit instead of leaving it spread across separate phase outputs.",
            ],
            [
                "Published `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_combined-decision.json`.",
                "Published `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_final-summary.json`.",
                f"Phase G now records the final decision as `{decision['recommended_position']}` with decision class `{decision['decision_class']}`.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Read published Phase C-F artifacts] --> B[Assemble physical buyer contract-risk and developer views]
    B --> C[Compute critical findings and market-quality classification]
    C --> D{Advance revise or reject?}
    D -->|Reject| E[Publish combined decision artifact]
    D -->|Revise| E
    D -->|Advance| E
    E --> F[Publish final closeout summary and reports]
""".strip(),
        "tools": _tools_html(
            [
                "`build_dppa_case_2_combined_decision_artifact()` - consolidates the Phase C-F outputs into one machine-readable recommendation surface.",
                "`build_dppa_case_2_final_summary_artifact()` - creates a closeout artifact that captures the full Case 2 phase history and final recommendation.",
                "`scripts/python/integration/analyze_ninhsim_dppa_case_2_phase_g.py` - regenerates the final decision package from canonical artifact paths.",
                "Report skill template - reused for both the implementation-phase report and the optional final closeout report because the workflow now justifies both.",
            ]
        ),
        "math": _math_html(
            [
                "Decision class is derived from the published screening recommendation: `advance*` -> advance, `reject*` -> reject, and everything else -> revise.",
                "Critical finding rollup keeps the highest-value contract-risk and commercial stressors visible: buyer premium, best tested developer NPV, and excess-generation CfD stress.",
                "Market-reference quality is downgraded to `transferred_repo_local` when the selected series comes from another case rather than a site-specific Ninhsim dataset.",
            ]
        ),
        "limits": _limits_html(
            [
                "Phase G does not improve the underlying economics; it only makes the existing Phase C-F conclusions explicit and reviewable in one place.",
                "The final package still inherits the transferred-market-series limitation from Phase F and the simplified Single Owner finance screen.",
            ],
            [
                "A second-best alternative was to stop at the Phase F report and let reviewers infer the overall outcome from separate artifacts.",
                "The chosen path won because the user asked for Phase G, and the repo plan explicitly called for one combined decision package plus final reporting when warranted.",
            ],
        ),
        "errors": _errors_html(
            [
                (
                    "WARN",
                    "The final recommendation remains constrained by the transferred `saigon18` market series and should not be interpreted as a site-certified bankability result.",
                ),
                (
                    "FLAG",
                    "Phase G confirms a reject-or-revise outcome rather than uncovering a hidden viable band, so further work should change assumptions instead of only repackaging the same case again.",
                ),
            ]
        ),
        "charts": _charts_html([chart]),
        "open_questions": _open_questions_html(
            [
                "Can a true Ninhsim hourly CFMP/FMP series be sourced before any future Case 2 revival?",
                "If the case is revised, should the first knob be strike basis, DPPA adder, or physical design scope?",
            ],
            [
                "Use the new final summary to brief stakeholders on whether Case 2 should be rejected outright or reopened only with materially different assumptions.",
                "If a future restart happens, begin from the combined decision artifact instead of replaying the full Phase C-F history from scratch.",
            ],
        ),
    }

    output = _render_report("DPPA Case 2 Phase G", sections)
    print(f"Report saved -> {output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
