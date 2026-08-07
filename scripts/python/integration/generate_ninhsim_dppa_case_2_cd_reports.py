"""Generate Phase C and D HTML reports for Ninhsim DPPA Case 2."""

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

PHYSICAL = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_physical-summary.json"
)
SETTLEMENT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_buyer-settlement.json"
)
BENCHMARK = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-14_ninhsim_dppa-case-2_buyer-benchmark.json"
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


def build_phase_c_report() -> Path:
    physical = _read_json(PHYSICAL)
    mix = physical["optimal_mix"]
    energy = physical["energy_summary"]
    matched_pct = energy["matched_fraction_of_load"] * 100.0
    contracted_pct = energy["contracted_fraction_of_load"] * 100.0
    chart = _chart_card(
        "Phase C Physical Mix",
        "phaseCChart",
        {
            "type": "bar",
            "data": {
                "labels": ["PV MW", "BESS MW", "BESS MWh", "Matched %", "Contracted %"],
                "datasets": [
                    {
                        "label": "Value",
                        "data": [
                            mix["pv_size_mw"],
                            mix["bess_mw"],
                            mix["bess_mwh"],
                            matched_pct,
                            contracted_pct,
                        ],
                        "backgroundColor": [
                            "#00f5ff",
                            "#39ff14",
                            "#ffd700",
                            "#ff2d78",
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
    sections = {
        "input_output": _io_html(
            "Phase C turned the frozen Case 2 assumptions into a runnable REopt scenario shape and a canonical physical-summary artifact so the synthetic DPPA settlement layer now has a stable hourly energy-flow basis to consume.",
            [
                "Frozen Phase A/B Case 2 design artifacts and Ninhsim extracted inputs.",
                "Existing Ninhsim REopt scenario patterns from Case 1 and the 60% solar-storage workflow.",
                "Requirement to remove private-wire shortcuts while keeping storage optional.",
            ],
            [
                "Published `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_physical-summary.json`.",
                "Added the canonical scenario builder and executable runner for `DPPA Case 2`.",
                f"Locked the physical output surface around `{matched_pct:.2f}%` matched load and `{contracted_pct:.2f}%` contracted generation share for the solved case.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Read frozen Case 2 assumptions] --> B[Build synthetic DPPA scenario JSON]
    B --> C{Wind or private-wire shortcuts?}
    C -->|No| D[Keep PV plus optional storage only]
    D --> E[Read REopt results and compute physical summary]
    E --> F[Publish Phase C physical artifact]
""".strip(),
        "tools": _tools_html(
            [
                "`apply_patch` - added the Case 2 physical scenario, runner, analyzer, and report generator surfaces.",
                "`pytest` - locked the Phase C scenario and physical-summary contracts before implementation settled.",
                "`build_ninhsim_reopt_input.py` - now emits the new `dppa_case_2` scenario family.",
                "Report skill template - reused the repo-standard 9-section HTML report shape.",
            ]
        ),
        "math": _math_html(
            [
                "Contracted generation series = renewable-to-load + renewable-to-grid, while storage discharge stays in physical delivery only so buyer settlement remains capped to renewable generator output.",
                f"Matched fraction of load = `{energy['matched_delivery_kwh']:.2f} / {energy['total_load_kwh']:.2f}` = `{matched_pct:.2f}%`.",
                f"Contracted fraction of load = `{energy['contracted_generation_kwh']:.2f} / {energy['total_load_kwh']:.2f}` = `{contracted_pct:.2f}%`.",
            ]
        ),
        "limits": _limits_html(
            [
                "Phase C trusts the existing REopt objective surface and records buyer-cost intent in metadata rather than encoding a true custom multi-objective solve inside REopt.",
                "The physical artifact is only as strong as the upstream solved REopt result, so a no-solve validation alone does not prove buyer economics.",
            ],
            [
                "A second-best path was to clone the 60% solar-storage scenario builder and specialize it inline for Case 2.",
                "The chosen path won because a dedicated Case 2 builder keeps the commercial identity explicit and avoids leaking target-fraction logic into the synthetic DPPA workflow.",
            ],
        ),
        "errors": _errors_html(
            [
                (
                    "FLAG",
                    "Storage remains optional by design, so Case 2 can still collapse to PV-only under some solve outcomes even though the buyer-settlement workflow itself is storage-aware.",
                ),
                (
                    "FLAG",
                    "The physical summary preserves exports and curtailment for auditability, but those quantities still require policy interpretation in later developer-side finance work.",
                ),
            ]
        ),
        "charts": _charts_html([chart]),
        "open_questions": _open_questions_html(
            [
                "Should a later Case 2 branch constrain exports or curtailment if buyer contract-shape risk turns out to dominate the commercial outcome?",
                "Does the future PySAM pass need plant-side generation decomposed into more categories than the current physical summary publishes?",
            ],
            [
                "Carry the physical summary directly into the buyer settlement engine so field names stay frozen.",
                "Use the solved Case 2 result to test developer-side finance only after the buyer benchmark is trusted.",
            ],
        ),
    }
    return _render_report("DPPA Case 2 Phase C", sections)


def build_phase_d_report() -> Path:
    settlement = _read_json(SETTLEMENT)
    benchmark = _read_json(BENCHMARK)
    summary = settlement["summary"]
    year_one = benchmark["year_one_costs"]
    chart = _chart_card(
        "Phase D Buyer Ledger",
        "phaseDChart",
        {
            "type": "bar",
            "data": {
                "labels": [
                    "Matched kWh",
                    "Shortfall kWh",
                    "Excess kWh",
                    "Buyer total kVND",
                    "Benchmark kVND",
                ],
                "datasets": [
                    {
                        "label": "Value",
                        "data": [
                            summary["matched_quantity_kwh"],
                            summary["shortfall_quantity_kwh"],
                            summary["excess_quantity_kwh"],
                            year_one["buyer_total_payment_vnd"] / 1000.0,
                            year_one["benchmark_evn_total_cost_vnd"] / 1000.0,
                        ],
                        "backgroundColor": [
                            "#00f5ff",
                            "#ffd700",
                            "#ff2d78",
                            "#39ff14",
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
    sections = {
        "input_output": _io_html(
            "Phase D implemented the runnable hourly buyer-settlement ledger, benchmark comparison, and customer-pass/fail decision surface so Case 2 now computes matched, shortfall, excess, EVN-linked, adder, and CfD values explicitly instead of leaving them in planning prose.",
            [
                "Phase B settlement schema and edge-case matrix.",
                "Phase C physical summary plus solved REopt generation and grid series.",
                "User instruction to exclude excess generation from buyer settlement while still reporting it.",
            ],
            [
                "Published `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_buyer-settlement.json`.",
                "Published `artifacts/reports/ninhsim/2026-04-14_ninhsim_dppa-case-2_buyer-benchmark.json`.",
                f"Computed buyer blended cost at `{summary['buyer_blended_cost_vnd_per_kwh']:.2f} VND/kWh` against EVN benchmark `{year_one['benchmark_blended_cost_vnd_per_kwh']:.2f} VND/kWh`.",
            ],
        ),
        "mermaid": """
flowchart TD
    A[Load physical summary and tariff series] --> B[Build hourly settlement inputs]
    B --> C[Compute matched shortfall and excess by hour]
    C --> D[Compute EVN matched payment DPPA adder shortfall and CfD]
    D --> E{Buyer better than EVN?}
    E -->|Yes| F[Flag buyer savings]
    E -->|No| G[Flag customer premium]
""".strip(),
        "tools": _tools_html(
            [
                "`run_dppa_case_2_buyer_settlement()` - computes the canonical hourly ledger and summary block.",
                "`build_dppa_case_2_market_proxy()` - supplies a documented hourly proxy market series when actual CFMP/FMP is unavailable.",
                "`build_dppa_case_2_buyer_benchmark()` - compares synthetic DPPA buyer cost against the EVN retail benchmark.",
                "`pytest` - locks matched, shortfall, excess, and negative-CfD behavior through regression coverage.",
            ]
        ),
        "math": _math_html(
            [
                "Matched quantity = `min(load, contracted_generation)`; shortfall = `max(0, load - matched)`; excess = `max(0, contracted_generation - matched)`.",
                "Buyer EVN matched payment = `matched x market_reference x KPP`.",
                "Buyer CfD payment = `matched x (strike - market_reference)` and can go negative when the market price is above strike.",
                "Buyer total payment = `EVN matched payment + DPPA adder + shortfall payment + CfD payment`.",
                f"Year-one buyer minus benchmark = `{year_one['buyer_total_payment_vnd']:.2f} - {year_one['benchmark_evn_total_cost_vnd']:.2f}` = `{year_one['buyer_minus_benchmark_vnd']:.2f} VND`.",
            ]
        ),
        "limits": _limits_html(
            [
                "Phase D currently uses a documented hourly proxy market series unless an external CFMP/FMP series is injected, so bankability still depends on upgrading the price source.",
                "The developer-side PySAM path is not yet fed by this richer settlement structure, so buyer and developer results still remain in separate artifacts for now.",
            ],
            [
                "A second-best alternative was to keep using one flat wholesale proxy or one blended strike-only revenue price for all follow-on analysis.",
                "The chosen hourly ledger won because it preserves auditable contract mechanics and makes negative CfD hours, shortfall exposure, and excess exclusion visible.",
            ],
        ),
        "errors": _errors_html(
            [
                (
                    "WARN",
                    "The current Phase D base case still falls back to a proxy market series when no trusted hourly CFMP/FMP file is supplied, so the buyer-cost result should be treated as directional rather than bankable.",
                ),
                (
                    "FLAG",
                    "Excess generation is intentionally excluded from buyer settlement in the first-pass ledger, which protects the customer view but leaves some project-value pathways for later sensitivity work.",
                ),
            ]
        ),
        "charts": _charts_html([chart]),
        "open_questions": _open_questions_html(
            [
                "What trusted hourly CFMP/FMP source should replace the current proxy for Ninhsim?",
                "Should future sensitivities expose excess-generation settlement variants once the base buyer ledger is accepted?",
            ],
            [
                "Move next into Phase E strike and contract-rule sensitivities using the new benchmark artifact as the base screen.",
                "Feed the Phase D settlement outputs into the future PySAM developer workflow without collapsing them back to one blended strike-only story.",
            ],
        ),
    }
    return _render_report("DPPA Case 2 Phase D", sections)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    phase_c = build_phase_c_report()
    phase_d = build_phase_d_report()
    print(f"Report saved -> {phase_c.relative_to(REPO_ROOT)}")
    print(f"Report saved -> {phase_d.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
