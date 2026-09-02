"""Generate the final closeout HTML report for Ninhsim DPPA Case 2."""

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
    final_summary = _read_json(FINAL)
    decision = final_summary["final_decision"]
    findings = final_summary["critical_findings"]

    chart = _chart_card(
        "Case 2 Closeout Timeline",
        "case2FinalChart",
        {
            "type": "bar",
            "data": {
                "labels": [entry["phase"] for entry in final_summary["case_history"]],
                "datasets": [
                    {
                        "label": "Phase count",
                        "data": [1, 1, 1, 1, 1],
                        "backgroundColor": [
                            "#00f5ff",
                            "#39ff14",
                            "#ffd700",
                            "#ff2d78",
                            "#7b61ff",
                        ],
                    }
                ],
            },
            "options": {"responsive": True, "maintainAspectRatio": False},
        },
    )

    sections = {
        "input_output": _io_html(
            "This final closeout report packages the full DPPA Case 2 journey into one review artifact so a reader can understand the ending without opening every phase report individually.",
            [
                "Published Phase C through Phase G artifacts and reports.",
                "Final combined decision artifact with explicit reject-or-revise recommendation.",
                "Need for a concise stakeholder-facing closeout view after a multi-phase workflow.",
            ],
            [
                "Published `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_final-summary.json`.",
                f"Published final closeout recommendation `{decision['recommended_position']}` with decision class `{decision['decision_class']}`.",
                "Created one stakeholder-ready final report that points back to the canonical phase artifacts.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Phase C physical sizing] --> B[Phase D buyer settlement]
    B --> C[Phase E sensitivity screen]
    C --> D[Phase F market replacement and PySAM validation]
    D --> E[Phase G combined decision]
    E --> F[Final closeout report]
""".strip(),
        "tools": _tools_html(
            [
                "`build_dppa_case_2_final_summary_artifact()` - turns the final decision package into a closeout-ready summary.",
                "Phase reports from C through G - provide the traceable evidence chain behind the final recommendation.",
                "Report skill template - reused for the final stakeholder-facing wrap-up because the workflow spans multiple technical phases.",
            ]
        ),
        "math": _math_html(
            [
                "The closeout summary does not introduce new economics; it carries forward the published combined-decision findings and phase history unchanged.",
                f"Final recommendation remains `{decision['recommended_position']}` because buyer premium stays positive at `{findings['buyer_premium_vnd']:.2f} VND` and the developer screen never clears the target hurdle.",
            ]
        ),
        "limits": _limits_html(
            [
                "The final report is only as strong as the combined decision artifact beneath it; it improves readability, not underlying evidence quality.",
                "Because the market series is still transferred from another site, the closeout conclusion should be treated as a current best screening answer rather than a final bankability memo.",
            ],
            [
                "A second-best alternative was to skip the final closeout report and stop at the Phase G report.",
                "The separate final report won because the workflow history is long enough that a concise end-state summary adds real review value.",
            ],
        ),
        "errors": _errors_html(
            [
                (
                    "WARN",
                    "The closeout recommendation remains contingent on a transferred market series and a simplified PySAM finance screen, so future revival work should change inputs before changing the write-up.",
                )
            ]
        ),
        "charts": _charts_html([chart]),
        "open_questions": _open_questions_html(
            [
                "Is there enough strategic value in Case 2 to reopen it with new assumptions, or should it remain closed as rejected under the current basis?",
            ],
            [
                "If reopened, start from the combined decision artifact and change one of: market basis, strike basis, DPPA adder, or physical design scope.",
            ],
        ),
    }

    output = _render_report("DPPA Case 2 Final", sections)
    print(f"Report saved -> {output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
