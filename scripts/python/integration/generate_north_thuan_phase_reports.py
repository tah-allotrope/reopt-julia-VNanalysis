"""
Generate report-skill-compatible HTML reports for each North Thuan phase.
"""

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORT_DATE = "2026-03-31"
PROJECT = "North Thuan REopt Validation"
REPO = REPO_ROOT.name


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def render_open_questions(items: list[str]) -> str:
    if not items:
        items = [
            "The phase closed cleanly. Optional next probe: rerun with measured North Thuan load and hourly market-price data."
        ]
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def render_empty_chart(message: str) -> str:
    return (
        '<div class="empty-state">'
        "<strong>No Chartable Data</strong>"
        f"<p>{message}</p>"
        "</div>"
    )


def render_chart(
    canvas_id: str, chart_type: str, data: dict, options: dict | None = None
) -> str:
    chart_json = json.dumps(
        {"type": chart_type, "data": data, "options": options or {}}
    )
    return (
        f'<canvas id="{canvas_id}"></canvas>'
        "<script>"
        f"new Chart(document.getElementById('{canvas_id}'), {chart_json});"
        "</script>"
    )


def render_report(template: str, phase: dict, output_dir: Path) -> Path:
    html = template
    for token, value in {
        "{{PHASE_NAME}}": phase["phase_name"],
        "{{DATE}}": REPORT_DATE,
        "{{PROJECT}}": PROJECT,
        "{{REPO}}": REPO,
        "{{INPUT_OUTPUT_CONTENT}}": phase["input_output_html"],
        "{{MERMAID_DIAGRAM}}": phase["mermaid"],
        "{{TOOLS_METHODS}}": phase["tools_html"],
        "{{CHARTS_SECTION}}": phase["charts_html"],
        "{{OPEN_QUESTIONS}}": phase["open_questions_html"],
    }.items():
        html = html.replace(token, value)

    filename = f"{REPORT_DATE}-{slugify(phase['phase_name'])}.html"
    output_path = output_dir / filename
    output_path.write_text(html, encoding="utf-8")
    return output_path


def build_phases() -> list[dict]:
    _extracted = load_json(
        REPO_ROOT
        / "data"
        / "interim"
        / "north_thuan"
        / "north_thuan_extracted_inputs.json"
    )
    comparison = load_json(
        REPO_ROOT
        / "artifacts"
        / "reports"
        / "north_thuan"
        / "2026-03-31_north-thuan-reopt-validation.json"
    )

    metrics_a = comparison["scenario_a"]["metrics"]
    metrics_b = comparison["scenario_b"]["metrics"]
    metrics_c = comparison["scenario_c"]["metrics"]
    settlement = comparison["settlement_check"]
    summary = comparison["summary"]

    phases = []

    phases.append(
        {
            "phase_name": "North Thuan Phase 1 Environment And Data Preparation",
            "input_output_html": render_column(
                "Input",
                [
                    "Used the staff PDF summary values: 240.90 GWh annual load, 27.5 MW mean demand, 134.1 MW peak demand, 30 MW solar, 20 MW wind, and 10 MW / 40 MWh storage.",
                    "Needed an 8760 load series even though only annual, mean, and peak statistics were available.",
                    "Needed a deterministic fallback for Vietnam market-price and wind-shape inputs so the local Julia workflow could run without custom external data files.",
                ],
            )
            + render_column(
                "Output",
                [
                    "Created `data/interim/north_thuan/north_thuan_extracted_inputs.json` with a synthetic 8760 industrial load profile.",
                    "Matched the annual energy target at 240.90 GWh and the peak-demand target at 134.1 MW.",
                    "Stored a flat year-1 FMP proxy of 0.04520 USD/kWh and a synthetic 38% annual-CF wind production-factor series.",
                ],
            ),
            "mermaid": """flowchart TD\nA[Staff PDF summary inputs] --> B{8760 load available?}\nB -- No --> C[Build synthetic industrial diurnal profile]\nC --> D[Scale to 240.90 GWh annual load]\nD --> E[Pin one hour to 134.1 MW peak]\nE --> F[Derive flat FMP proxy and wind PF fallback]\nF --> G[Write extracted inputs JSON]""",
            "tools_html": render_tools_table(
                [
                    (
                        "build_north_thuan_load_profile.py",
                        "Transform PDF summary inputs into machine-usable hourly data",
                        "Wrote the canonical extracted-inputs JSON.",
                    ),
                    (
                        "Synthetic load shaping",
                        "Preserve annual energy while creating realistic industrial timing",
                        "Produced a deterministic 8760 series with day/night and weekday/weekend structure.",
                    ),
                    (
                        "FMP back-solve",
                        "Anchor the revenue proxy to the staff year-1 revenue claim",
                        "Derived 0.04520 USD/kWh as the year-1 merchant-price proxy.",
                    ),
                ]
            ),
            "charts_html": render_empty_chart(
                "This phase created the canonical 8760 input assets; the meaningful quantitative comparisons happen after the scenario solves."
            ),
            "open_questions_html": render_open_questions(
                [
                    "Replace the synthetic load profile with measured hourly factory demand if developer data becomes available.",
                    "Replace the flat FMP proxy with hourly North Thuan market-price data to tighten settlement realism.",
                    "Confirm whether the site proxy coordinate should be moved once the exact wind project location is known.",
                ]
            ),
        }
    )

    phases.append(
        {
            "phase_name": "North Thuan Phase 2 REopt Scenario Construction",
            "input_output_html": render_column(
                "Input",
                [
                    "Needed three scenario variants from the plan: fixed sizing, optimized sizing, and fixed sizing without storage.",
                    "Needed Vietnam preprocessing to zero US incentives and keep the local REopt schema aligned with repo conventions.",
                    "Needed a wind-data fallback because the North Thuan proxy location is outside the NREL Wind Toolkit coverage used by default REopt fetches.",
                ],
            )
            + render_column(
                "Output",
                [
                    "Created `scenarios/case_studies/north_thuan/north_thuan_scenario_a.json`, `scenarios/case_studies/north_thuan/north_thuan_scenario_b.json`, and `scenarios/case_studies/north_thuan/north_thuan_scenario_c.json`.",
                    "Modeled the DPPA approximation inside REopt as a flat 0.055 USD/kWh tariff for all hours.",
                    "Injected `Wind.production_factor_series` directly so local Julia solves do not fail on missing Wind Toolkit coverage.",
                ],
            ),
            "mermaid": """flowchart TD\nA[Extracted inputs JSON] --> B[Build base North Thuan scenario]\nB --> C[Apply Vietnam defaults]\nC --> D{Scenario variant}\nD -- A --> E[Fix PV, Wind, and BESS sizes]\nD -- B --> F[Open sizing bounds for optimization]\nD -- C --> G[Set storage max bounds to zero]\nE --> H[Write scenario JSONs]\nF --> H\nG --> H""",
            "tools_html": render_tools_table(
                [
                    (
                        "build_north_thuan_reopt_input.py",
                        "Create scenario JSONs that match the repo's case-study pattern",
                        "Generated the A/B/C scenario files in the canonical path.",
                    ),
                    (
                        "apply_vietnam_defaults()",
                        "Reuse repo-standard tariff, emissions, and incentive preprocessing",
                        "Kept North Thuan aligned with the dual-language Vietnam pipeline.",
                    ),
                    (
                        "Flat strike tariff",
                        "Approximate the DPPA economics inside REopt",
                        "Set all Scenario A/B/C tariff hours to 0.055 USD/kWh.",
                    ),
                ]
            ),
            "charts_html": render_empty_chart(
                "This phase was about schema-correct scenario assembly; the scenario-size comparison becomes meaningful after the Julia solves."
            ),
            "open_questions_html": render_open_questions(
                [
                    "If measured wind data becomes available, swap out the synthetic wind production-factor series and re-run all three scenarios.",
                    "Decide whether Scenario B upper bounds should be tightened once the real interconnection envelope is known.",
                ]
            ),
        }
    )

    phases.append(
        {
            "phase_name": "North Thuan Phase 3 Local Julia Runner And Solve Path",
            "input_output_html": render_column(
                "Input",
                [
                    "Needed the existing Julia runner to route North Thuan outputs into a dedicated result folder instead of the generic `artifacts/results/` root.",
                    "Needed proof that the scenario JSONs pass `Scenario()` validation before spending time on full solves.",
                    "Needed a solve-path fix after the first North Thuan run failed on the Wind Toolkit API for the Vietnam proxy coordinate.",
                ],
            )
            + render_column(
                "Output",
                [
                    "Updated `scripts/julia/run_vietnam_scenario.jl` so North Thuan scenario paths now save into `artifacts/results/north_thuan/`.",
                    "Validated Scenario A with `--no-solve` and then solved Scenarios A/B/C locally with HiGHS.",
                    "Recorded three optimal local solves after switching the wind input to a deterministic `production_factor_series` fallback.",
                ],
            ),
            "mermaid": """flowchart TD\nA[North Thuan scenario JSONs] --> B[No-solve Scenario() validation]\nB --> C{Runner routing correct?}\nC -- No --> D[Patch Julia out_dir detection]\nD --> E[Re-run validation]\nE --> F[Full local solve]\nF --> G{Wind Toolkit available?}\nG -- No --> H[Inject synthetic wind PF fallback]\nH --> I[Rebuild scenarios]\nI --> J[Solve A, B, and C to optimality]""",
            "tools_html": render_tools_table(
                [
                    (
                        "run_vietnam_scenario.jl",
                        "Validate and solve case-study JSONs through the local Julia path",
                        "North Thuan results now land in `artifacts/results/north_thuan/`.",
                    ),
                    (
                        "run_north_thuan_reopt.py",
                        "Batch the build-plus-run workflow from Python",
                        "Rebuilt inputs and dispatched Scenario A/B/C solves.",
                    ),
                    (
                        "HiGHS via REopt.jl",
                        "Run the actual local optimization path requested by the plan",
                        "All three scenarios reached `status=optimal` after the wind fallback patch.",
                    ),
                ]
            ),
            "charts_html": render_empty_chart(
                "This phase focused on pipeline correctness and execution reliability; the downstream comparison phases carry the meaningful quantitative outputs."
            ),
            "open_questions_html": render_open_questions(
                [
                    "The Julia environment still emits ArchGDAL precompile noise, although it did not block validation or solving.",
                    "Non-US AVERT/EASIUR/Cambium warnings remain expected for the Vietnam coordinate and should not be mistaken for solve failures.",
                ]
            ),
        }
    )

    phases.append(
        {
            "phase_name": "North Thuan Phase 4 Energy Comparison Extraction",
            "input_output_html": render_column(
                "Input",
                [
                    "Needed a new comparison path for North Thuan because the prior staff-validation script only recomputed finance from PDF assumptions and never touched REopt results.",
                    "Needed exact result-key handling for hybrid REopt outputs, including Wind's `annual_energy_produced_kwh` field and the average-annual series accounting used in REopt result writers.",
                    f"Needed to evaluate Scenario A against the staff targets with a {summary['tolerance_pct']:.0f}% warning threshold.",
                ],
            )
            + render_column(
                "Output",
                [
                    "Created `scripts/python/integration/compare_north_thuan_reopt_vs_staff.py` and regression coverage in `tests/python/integration/test_north_thuan_reopt.py`.",
                    f"Generated `artifacts/reports/north_thuan/2026-03-31_north-thuan-reopt-validation.json` with {summary['ok']} OK and {summary['warn']} WARN checks.",
                    f"Scenario A landed at {metrics_a['total_gen_gwh_yr1']:.2f} GWh total RE generation, {metrics_a['matched_gwh_yr1']:.2f} GWh matched volume, and {metrics_a['re_penetration_pct']:.1f}% RE penetration.",
                ],
            ),
            "mermaid": """flowchart TD\nA[Scenario A REopt results] --> B[Extract PV, Wind, storage, and grid series]\nB --> C{Hybrid key mapping correct?}\nC -- No --> D[Add Wind annual fallback and storage-charging generation accounting]\nD --> E[Re-run regression tests]\nE --> F[Compare against staff PDF metrics]\nF --> G[Persist comparison JSON]""",
            "tools_html": render_tools_table(
                [
                    (
                        "compare_north_thuan_reopt_vs_staff.py",
                        "Turn solved REopt outputs into staff-comparison metrics",
                        "Persisted the solved comparison artifact for Scenario A/B/C.",
                    ),
                    (
                        "REopt result schema review",
                        "Map North Thuan fields to the actual REopt writers",
                        "Corrected the wind and generation accounting bug in the first comparison pass.",
                    ),
                    (
                        "pytest regression file",
                        "Lock the North Thuan mapping so it cannot silently drift later",
                        "Added six passing regression tests around load building, scenario creation, and comparison math.",
                    ),
                ]
            ),
            "charts_html": render_chart(
                "phase4EnergyChart",
                "bar",
                {
                    "labels": [
                        "Solar GWh",
                        "Wind GWh",
                        "Total RE GWh",
                        "Matched GWh",
                        "RE Penetration %",
                        "Self-Consumption %",
                    ],
                    "datasets": [
                        {
                            "label": "Staff PDF",
                            "data": [51.0, 66.6, 117.56, 70.05, 48.8, 59.6],
                            "backgroundColor": "#5fb9ff",
                        },
                        {
                            "label": "REopt Scenario A",
                            "data": [
                                round(metrics_a["solar_gwh_yr1"], 3),
                                round(metrics_a["wind_gwh_yr1"], 3),
                                round(metrics_a["total_gen_gwh_yr1"], 3),
                                round(metrics_a["matched_gwh_yr1"], 3),
                                round(metrics_a["re_penetration_pct"], 3),
                                round(metrics_a["self_consumption_pct"], 3),
                            ],
                            "backgroundColor": "#39ff14",
                        },
                    ],
                },
                {"responsive": True, "plugins": {"legend": {"position": "bottom"}}},
            ),
            "open_questions_html": render_open_questions(
                [
                    "Scenario A matched volume is far above the staff 70.05 GWh claim, which suggests the synthetic load and flat strike tariff allow much higher direct absorption than the staff dispatch model assumed.",
                    "Solar production is 10.1% below the staff claim because the local PVWatts result at the proxy coordinate is lower than the staff's 19.4% solar-CF assumption.",
                    "Factory-NPV comparison is directionally useful but still mixes REopt LCC framing with the staff's finance framing.",
                ]
            ),
        }
    )

    phases.append(
        {
            "phase_name": "North Thuan Phase 5 DPPA Settlement Post Processing",
            "input_output_html": render_column(
                "Input",
                [
                    "Needed a post-processing revenue path because REopt does not natively model Vietnam's virtual DPPA settlement structure.",
                    "Needed the helper to preserve the existing Saigon18 settlement workflow while also supporting the North Thuan strike-plus-FMP framing.",
                    f"Needed a direct check against the staff's $6.0M year-1 developer revenue claim with a {summary['settlement_tolerance_pct']:.0f}% warning band.",
                ],
            )
            + render_column(
                "Output",
                [
                    "Extended `scripts/python/reopt/dppa_settlement.py` with `compute_virtual_dppa_developer_revenue()` for the North Thuan virtual-DPPA proxy.",
                    f"Scenario A settlement check landed at {settlement['matched_volume_mwh'] / 1000.0:.2f} GWh matched volume and {settlement['developer_revenue_yr1_usd'] / 1_000_000.0:.2f}M USD year-1 developer revenue.",
                    f"The revenue delta versus the staff claim is {settlement['delta_pct']:+.1f}% -> {settlement['status']}.",
                ],
            ),
            "mermaid": """flowchart TD\nA[Scenario A dispatch metrics] --> B[Build matched RE delivery series]\nB --> C[Build total RE generation proxy]\nC --> D[Apply strike price to matched volume]\nD --> E[Apply FMP proxy to unmatched volume]\nE --> F{Revenue within 15%?}\nF -- Yes --> G[Lock settlement check as OK]\nF -- No --> H[Flag settlement mismatch for review]""",
            "tools_html": render_tools_table(
                [
                    (
                        "compute_virtual_dppa_developer_revenue()",
                        "Model the strike-price plus merchant-price revenue split outside REopt",
                        "Kept the North Thuan DPPA check consistent with the plan's post-processing approach.",
                    ),
                    (
                        "Strike + FMP decomposition",
                        "Separate contracted matched volume from merchant exposure",
                        "Showed that the current synthetic setup leaves almost no unmatched generation in Scenario A.",
                    ),
                    (
                        "Shared settlement regression",
                        "Protect the earlier Saigon18 workflow from collateral breakage",
                        "The full Saigon18 + North Thuan regression suite remained green after the helper extension.",
                    ),
                ]
            ),
            "charts_html": render_chart(
                "phase5SettlementChart",
                "doughnut",
                {
                    "labels": ["Matched volume (MWh)", "Unmatched volume (MWh)"],
                    "datasets": [
                        {
                            "data": [
                                round(settlement["matched_volume_mwh"], 2),
                                round(settlement["unmatched_volume_mwh"], 2),
                            ],
                            "backgroundColor": ["#00f5ff", "#ffb100"],
                        }
                    ],
                },
                {"responsive": True, "plugins": {"legend": {"position": "bottom"}}},
            )
            + render_chart(
                "phase5RevenueChart",
                "bar",
                {
                    "labels": ["Staff claim", "Scenario A revenue"],
                    "datasets": [
                        {
                            "label": "Year-1 developer revenue (USD)",
                            "data": [
                                6_000_000.0,
                                round(settlement["developer_revenue_yr1_usd"], 2),
                            ],
                            "backgroundColor": ["#5fb9ff", "#39ff14"],
                        }
                    ],
                },
                {"responsive": True, "plugins": {"legend": {"display": False}}},
            ),
            "open_questions_html": render_open_questions(
                [
                    "The settlement check is close to the staff claim, but it is being driven by a much larger matched-volume result than the staff model assumed.",
                    "Hourly FMP data is still the biggest realism gap for this phase because the current run uses a flat year-1 FMP proxy.",
                ]
            ),
        }
    )

    phases.append(
        {
            "phase_name": "North Thuan Phase 6 HTML Report Synthesis",
            "input_output_html": render_column(
                "Input",
                [
                    "Needed one self-contained North Thuan HTML analysis artifact for the solved REopt pipeline.",
                    "Needed the final report to cover the fixed case, the sizing sensitivity cases, and the settlement check in one place.",
                    "Needed six separate phase reports in `reports/` because the user explicitly asked for a report-skill-style HTML artifact at the end of each phase.",
                ],
            )
            + render_column(
                "Output",
                [
                    "Created `scripts/python/integration/generate_north_thuan_reopt_report.py` and wrote `artifacts/reports/north_thuan/2026-03-31_north-thuan-reopt-validation.html`.",
                    "Created `scripts/python/integration/generate_north_thuan_phase_reports.py` and generated six phase reports under `reports/` using the report-skill template shell.",
                    f"Captured the sizing story: Scenario A NPV {metrics_a['factory_npv_usd'] / 1_000_000.0:.2f}M, Scenario B NPV {metrics_b['factory_npv_usd'] / 1_000_000.0:.2f}M, Scenario C NPV {metrics_c['factory_npv_usd'] / 1_000_000.0:.2f}M.",
                ],
            ),
            "mermaid": """flowchart TD\nA[Comparison JSON + scenario solves] --> B[Build North Thuan HTML analysis report]\nB --> C[Load report-skill template]\nC --> D[Render six phase-specific HTML summaries]\nD --> E[Write reports/2026-03-31-*.html]\nE --> F[Capture final review notes and paths]""",
            "tools_html": render_tools_table(
                [
                    (
                        "generate_north_thuan_reopt_report.py",
                        "Create the final stakeholder-facing North Thuan HTML artifact",
                        "Published the solved REopt comparison as a standalone HTML page.",
                    ),
                    (
                        "report-template.html",
                        "Use the loaded report-skill shell instead of building a new page shell from scratch",
                        "All six phase reports share the requested dark + neon report structure.",
                    ),
                    (
                        "Chart.js",
                        "Visualize the phase outputs where numbers add value",
                        "Rendered comparison, sizing, and settlement charts directly inside the report pages.",
                    ),
                ]
            ),
            "charts_html": render_chart(
                "phase6ScenarioChart",
                "bar",
                {
                    "labels": [
                        "Scenario A fixed",
                        "Scenario B optimized",
                        "Scenario C no BESS",
                    ],
                    "datasets": [
                        {
                            "label": "Factory NPV proxy (USD)",
                            "data": [
                                round(metrics_a["factory_npv_usd"], 2),
                                round(metrics_b["factory_npv_usd"], 2),
                                round(metrics_c["factory_npv_usd"], 2),
                            ],
                            "backgroundColor": ["#00f5ff", "#39ff14", "#ffb100"],
                        }
                    ],
                },
                {"responsive": True, "plugins": {"legend": {"position": "bottom"}}},
            ),
            "open_questions_html": render_open_questions(
                [
                    "Scenario B optimizes to 24.59 MW solar, 50 MW wind, and no battery, which is far more aggressive on wind than the staff case and should be reviewed against real project constraints.",
                    "The final North Thuan HTML report is useful as a solved local-validation artifact, but its financial interpretation still depends on synthetic load and merchant-price assumptions.",
                ]
            ),
        }
    )

    return phases


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate report-skill-compatible HTML reports for each North Thuan phase"
    )
    parser.add_argument(
        "--template",
        required=True,
        help="Path to the report skill HTML template",
    )
    parser.add_argument(
        "--outdir",
        default="reports",
        help="Output directory for generated reports",
    )
    args = parser.parse_args()

    template = Path(args.template).read_text(encoding="utf-8")
    output_dir = REPO_ROOT / args.outdir
    output_dir.mkdir(parents=True, exist_ok=True)

    for phase in build_phases():
        out_path = render_report(template, phase, output_dir)
        print(f"Generated phase report: {out_path}")


if __name__ == "__main__":
    main()
