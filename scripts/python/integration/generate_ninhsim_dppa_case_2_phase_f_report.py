"""Generate the Phase F HTML report for Ninhsim DPPA Case 2."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORT_DATE = "2026-04-15"
PROJECT = REPO_ROOT.name
REPO = str(REPO_ROOT)
TEMPLATE_PATH = (
    Path.home() / ".claude" / "skills" / "report" / "assets" / "template.html"
)
OUTPUT_DIR = REPO_ROOT / "reports"

MARKET = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_market-reference.json"
)
BENCHMARK = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_buyer-benchmark-actual-market.json"
)
PY_SAM = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_pysam-results.json"
)
SCREENING = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-15_ninhsim_dppa-case-2_developer-screening.json"
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
    market = _read_json(MARKET)
    benchmark = _read_json(BENCHMARK)
    pysam = _read_json(PY_SAM)
    screening = _read_json(SCREENING)

    buyer_delta = benchmark["year_one_costs"]["buyer_minus_benchmark_vnd"]
    irr = pysam["outputs"]["project_return_aftertax_irr_fraction"]
    npv = pysam["outputs"]["project_return_aftertax_npv_usd"]
    dscr = pysam["outputs"]["min_dscr"]

    decision_chart = _chart_card(
        "Phase F Buyer vs Developer",
        "phaseFDecisionChart",
        {
            "type": "bar",
            "data": {
                "labels": ["Buyer delta kVND", "IRR %", "NPV kUSD", "Min DSCR"],
                "datasets": [
                    {
                        "label": "Value",
                        "data": [
                            buyer_delta / 1000.0,
                            0.0 if irr is None else irr * 100.0,
                            npv / 1000.0,
                            dscr,
                        ],
                        "backgroundColor": ["#00f5ff", "#ff2d78", "#ffd700", "#39ff14"],
                    }
                ],
            },
            "options": {"responsive": True, "maintainAspectRatio": False},
        },
    )
    market_chart = _chart_card(
        "Market Reference Sample",
        "phaseFMarketChart",
        {
            "type": "line",
            "data": {
                "labels": ["1", "2", "3", "4", "5", "6"],
                "datasets": [
                    {
                        "label": "Market VND/kWh",
                        "data": market["hourly_series_vnd_per_kwh"][:6],
                        "borderColor": "#00f5ff",
                        "backgroundColor": "#00f5ff",
                        "fill": False,
                    }
                ],
            },
            "options": {"responsive": True, "maintainAspectRatio": False},
        },
    )

    sections = {
        "input_output": _io_html(
            "Phase F replaced the retail-scaled market proxy with the best repo-local hourly market series available, reran the buyer settlement against that source, and then executed the Case 2 PySAM developer screen so the current no-overlap story is validated with separate buyer and developer artifacts.",
            [
                "Phase E strike and contract-risk artifacts showing no viable overlap under the proxy market series.",
                "Repo-local Saigon18 extracted hourly CFMP/FMP series as the strongest available local market reference candidate.",
                "Existing Case 2 PySAM bridge and Single Owner runtime from the earlier PySAM phases.",
            ],
            [
                "Published `artifacts/reports/ninhsim/2026-04-15_ninhsim_dppa-case-2_market-reference.json`.",
                "Published actual-market buyer, PySAM, comparison, and screening artifacts for Phase F.",
                f"Final screening now reports `{screening['decision']['recommended_position']}` with combined pass `{screening['decision']['combined_pass']}`.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Read Phase E outputs and Case 2 physical result] --> B[Load repo-local hourly CFMP series]
    B --> C[Normalize to VND per kWh and rebuild buyer settlement]
    C --> D[Map Case 2 physical result into PySAM Single Owner]
    D --> E{Buyer and developer both pass?}
    E -->|Yes| F[Advance current case]
    E -->|No| G[Reject or revise current case]
    F --> H[Publish comparison and screening artifacts]
    G --> H
""".strip(),
        "tools": _tools_html(
            [
                "`build_dppa_case_2_market_reference_artifact()` - selects and normalizes the repo-local hourly CFMP/FMP transfer series.",
                "`run_dppa_case_2_buyer_settlement()` - recomputes the buyer view against the replaced hourly market series.",
                "`build_dppa_case_2_single_owner_inputs()` + `run_single_owner_model()` - execute the developer-side PySAM validation on the same Case 2 physical result.",
                "`build_dppa_case_2_reopt_pysam_comparison()` and `build_dppa_case_2_developer_screening()` - keep buyer, developer, and alignment results explicit.",
            ]
        ),
        "math": _math_html(
            [
                "Market replacement prefers hourly `CFMP` over `FMP` when both exist, then normalizes VND/MWh-like values to VND/kWh before settlement use.",
                "Buyer pass = savings versus EVN remains positive under the replaced hourly market series; developer pass = after-tax IRR clears the target hurdle.",
                "Phase F decision = advance only if both buyer and developer pass, otherwise classify the current case as revise or reject without blending the metrics.",
            ]
        ),
        "limits": _limits_html(
            [
                "The replaced market reference is stronger than the prior proxy but is still transferred from another Vietnam project, so it remains a documented quasi-actual series rather than a site-certified Ninhsim dataset.",
                "PySAM still runs the simplified Single Owner finance stack, so the developer view is a screening result rather than a lender-ready model.",
            ],
            [
                "A second-best alternative was to keep the retail-scaled proxy and run only the PySAM developer check.",
                "The chosen path won because Phase F specifically needed both proxy replacement and developer validation, and the repo already held a better local hourly CFMP source.",
            ],
        ),
        "errors": _errors_html(
            [
                (
                    "WARN",
                    "The selected hourly market series is transferred from `saigon18`, not extracted directly for Ninhsim, so Phase F improves credibility but does not fully eliminate market-basis risk.",
                ),
                (
                    "FLAG",
                    "If the current case still fails both buyer and developer screens after market replacement, the likely next move is to revise core assumptions rather than continue widening the same strike band.",
                ),
            ]
        ),
        "charts": _charts_html([decision_chart, market_chart]),
        "open_questions": _open_questions_html(
            [
                "Can a true Ninhsim-specific hourly CFMP/FMP dataset be sourced to replace the transferred Saigon18 market series?",
                "Should the next screening gate require non-negative NPV or minimum DSCR in addition to the IRR hurdle?",
            ],
            [
                "Move into Phase G with the new buyer, market, PySAM, and comparison artifacts consolidated into one final decision package.",
                "If the case remains non-viable, use Phase G to document whether the right action is reject, revise strike, or revisit physical design assumptions.",
            ],
        ),
    }

    output = _render_report("DPPA Case 2 Phase F", sections)
    print(f"Report saved -> {output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
