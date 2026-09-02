"""Generate the Phase E HTML report for Ninhsim DPPA Case 2."""

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

STRIKE = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_strike-sensitivity.json"
)
RISK = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_contract-risk.json"
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
    strike = _read_json(STRIKE)
    risk = _read_json(RISK)

    strike_results = strike["strike_sweep_results"]
    adder_results = risk["adder_sensitivity"]["results"]
    overlap_found = strike["negotiation_summary"]["overlap_found"]
    recommended = strike["negotiation_summary"]["recommended_position"]

    strike_chart = _chart_card(
        "Strike Sweep Buyer vs Developer",
        "phaseEStrikeChart",
        {
            "type": "bar",
            "data": {
                "labels": [
                    f"{entry['strike_price_vnd_per_kwh']:.0f}"
                    for entry in strike_results
                ],
                "datasets": [
                    {
                        "label": "Buyer delta vs EVN (kVND)",
                        "data": [
                            entry["buyer_minus_benchmark_vnd"] / 1000.0
                            for entry in strike_results
                        ],
                        "backgroundColor": "#00f5ff",
                    },
                    {
                        "label": "Developer IRR %",
                        "data": [
                            0.0
                            if entry["developer_irr_fraction"] is None
                            else entry["developer_irr_fraction"] * 100.0
                            for entry in strike_results
                        ],
                        "backgroundColor": "#ff2d78",
                    },
                ],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
            },
        },
    )
    risk_chart = _chart_card(
        "Adder Sensitivity Customer Delta",
        "phaseERiskChart",
        {
            "type": "line",
            "data": {
                "labels": [
                    f"{entry['dppa_adder_vnd_per_kwh']:.0f}" for entry in adder_results
                ],
                "datasets": [
                    {
                        "label": "Buyer delta vs EVN (kVND)",
                        "data": [
                            entry["buyer_minus_benchmark_vnd"] / 1000.0
                            for entry in adder_results
                        ],
                        "borderColor": "#ffd700",
                        "backgroundColor": "#ffd700",
                        "fill": False,
                    }
                ],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
            },
        },
    )

    sections = {
        "input_output": _io_html(
            "Phase E turned the frozen Phase D buyer ledger into an executable negotiation screen by sweeping strike and contract-rule variants, then comparing buyer acceptability against developer finance viability without collapsing the two views into one blended metric.",
            [
                "Solved Phase C physical summary and Phase D buyer settlement baseline.",
                "Existing PySAM Single Owner bridge so the developer screen reuses repo finance logic.",
                "User request to implement Phase E and publish the synchronized report artifact on completion.",
            ],
            [
                "Published `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_strike-sensitivity.json`.",
                "Published `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_contract-risk.json`.",
                f"Negotiation summary now reports overlap `{overlap_found}` with recommended position `{recommended}`.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Load Phase D settlement baseline] --> B[Build PySAM developer inputs from Case 2 physical outputs]
    B --> C[Sweep strike candidates and re-run buyer ledger]
    C --> D{Buyer and developer both pass?}
    D -->|Yes| E[Record overlap candidates]
    D -->|No| F[Record buyer-only or developer-only candidates]
    F --> G[Sweep adder KPP and excess-treatment stress cases]
    E --> G
    G --> H[Publish Phase E JSON artifacts and HTML report]
""".strip(),
        "tools": _tools_html(
            [
                "`build_dppa_case_2_strike_sensitivity()` - replays the buyer ledger across strike variants and optional PySAM developer checks.",
                "`build_dppa_case_2_contract_risk_sensitivity()` - stresses DPPA adder, KPP, and excess-generation treatment without changing the physical solve.",
                "`build_dppa_case_2_single_owner_inputs()` - maps the Case 2 physical output into the existing Single Owner finance runtime.",
                "Report skill template - reused the repo-standard 9-section self-contained HTML structure.",
            ]
        ),
        "math": _math_html(
            [
                "Strike sweep anchor = weighted EVN tariff x (1 - strike discount fraction), evaluated against the frozen Phase D buyer ledger and the existing developer IRR threshold.",
                "Buyer pass = negative or zero `buyer_minus_benchmark_vnd`; developer pass = after-tax IRR greater than or equal to the target IRR fraction.",
                "Contract-risk sweeps keep physical quantities fixed and vary only DPPA adder, KPP factor, and whether excess renewable generation creates extra CfD exposure.",
            ]
        ),
        "limits": _limits_html(
            [
                "The developer overlap still inherits PySAM Single Owner simplifications, so Phase E is a screening surface rather than a full negotiated contract model.",
                "Strike overlap conclusions remain sensitive to the proxy market-price series until a trusted hourly CFMP/FMP dataset replaces it.",
            ],
            [
                "A second-best alternative was to run buyer-only strike sweeps and postpone the developer side to Phase F.",
                "The chosen path won because the user asked for Phase E execution now, and the repo already had enough bridge infrastructure to expose buyer-versus-developer mismatch explicitly.",
            ],
        ),
        "errors": _errors_html(
            [
                (
                    "WARN",
                    "Phase E still relies on the proxy market-price path inherited from Phase D, so the overlap screen should be treated as directional until the market series is upgraded.",
                ),
                (
                    "FLAG",
                    "The current base case may produce no buyer/developer overlap, which is a useful commercial result but not yet a financeable recommendation.",
                ),
            ]
        ),
        "charts": _charts_html([strike_chart, risk_chart]),
        "open_questions": _open_questions_html(
            [
                "Which actual hourly CFMP/FMP series should replace the provisional proxy before the negotiation screen is treated as bankable?",
                "Should later phases add a second developer hurdle such as non-negative NPV or minimum DSCR on top of IRR?",
            ],
            [
                "Use the Phase E outputs to decide whether Phase F should validate only overlap candidates or also document no-overlap scenarios explicitly in PySAM.",
                "Add the final combined decision artifact in Phase G so buyer, developer, and contract-risk conclusions are reviewed in one place.",
            ],
        ),
    }

    output = _render_report("DPPA Case 2 Phase E", sections)
    print(f"Report saved -> {output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
