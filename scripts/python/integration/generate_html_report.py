"""
Generate the final self-contained Saigon18 HTML analysis report.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RESULTS_DIR = REPO_ROOT / "artifacts" / "results" / "saigon18"
REPORTS_DIR = REPO_ROOT / "artifacts" / "reports" / "saigon18"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_money(value: float, decimals: int = 1) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.{decimals}f}M"
    return f"${value:,.0f}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def fmt_mwh(value: float) -> str:
    return f"{value:,.0f} MWh"


def delta_class(delta_fraction: float | None) -> str:
    if delta_fraction is None:
        return "neutral"
    delta = abs(delta_fraction)
    if delta <= 0.10:
        return "good"
    if delta <= 0.30:
        return "warn"
    return "bad"


def cell_class(actual: float | None, target: float | None) -> str:
    if actual is None or target in (None, 0):
        return ""
    return delta_class((actual - target) / abs(target))


def badge_class(ok: bool) -> str:
    return "badge-good" if ok else "badge-warn"


def build_scenario_summary(
    label: str, result: dict, settlement: dict | None = None, equity: dict | None = None
) -> dict:
    pv = result.get("PV", {})
    fin = result.get("Financial", {})
    storage = result.get("ElectricStorage", {})
    export_fraction = 0.0
    annual_prod = (
        pv.get("annual_energy_produced_kwh")
        or pv.get("year_one_energy_produced_kwh")
        or 0.0
    )
    if annual_prod:
        export_fraction = (pv.get("annual_energy_exported_kwh") or 0.0) / annual_prod

    npv = fin.get("npv") or 0.0
    year1 = fin.get("year_one_total_operating_cost_savings_before_tax") or 0.0
    if settlement:
        npv += settlement.get("settlement_npv_usd", 0.0)
        year1 += settlement.get("total_settlement_usd", 0.0)

    return {
        "label": label,
        "status": result.get("status", "unknown").upper(),
        "npv_usd": npv,
        "payback_years": fin.get("simple_payback_years") or 0.0,
        "unlevered_irr": fin.get("internal_rate_of_return") or 0.0,
        "equity_irr": None if equity is None else equity.get("equity_irr"),
        "year1_revenue_usd": year1,
        "pv_size_kw": pv.get("size_kw") or 0.0,
        "bess_kw": storage.get("size_kw") or 0.0,
        "bess_kwh": storage.get("size_kwh") or 0.0,
        "pv_prod_mwh": (pv.get("year_one_energy_produced_kwh") or 0.0) / 1_000.0,
        "pv_export_mwh": (pv.get("annual_energy_exported_kwh") or 0.0) / 1_000.0,
        "grid_mwh": (
            result.get("ElectricUtility", {}).get("annual_energy_supplied_kwh") or 0.0
        )
        / 1_000.0,
        "export_fraction": export_fraction,
        "settlement_usd": None
        if settlement is None
        else settlement.get("total_settlement_usd"),
        "settlement_npv_usd": None
        if settlement is None
        else settlement.get("settlement_npv_usd"),
        "contract_type": None
        if settlement is None
        else settlement.get("contract_type"),
    }


def split_bess(result: dict, scenario_json: dict) -> dict:
    rates = scenario_json["ElectricTariff"]["tou_energy_rates_per_kwh"]
    series = result.get("ElectricStorage", {}).get("storage_to_load_series_kw", [])
    levels = sorted({round(v, 10) for v in rates})
    offpeak, _standard, peak = levels[0], levels[1], levels[-1]
    buckets = {"peak": 0.0, "standard": 0.0, "offpeak": 0.0}
    for rate, value in zip(rates, series):
        rate = round(rate, 10)
        if rate == peak:
            buckets["peak"] += value
        elif rate == offpeak:
            buckets["offpeak"] += value
        else:
            buckets["standard"] += value
    return {k: v / 1_000.0 for k, v in buckets.items()}


def bar_rows(rows: list[tuple[str, float, str]], unit: str) -> str:
    max_value = max(value for _, value, _ in rows) if rows else 1.0
    html = []
    for label, value, color in rows:
        width = 0 if max_value == 0 else (value / max_value) * 100
        html.append(
            f'<div class="bar-row"><div class="bar-label">{label}</div><div class="bar-track"><div class="bar-fill {color}" style="width:{width:.1f}%"></div></div><div class="bar-value">{value:,.0f} {unit}</div></div>'
        )
    return "\n".join(html)


def main():
    result_a = load_json(
        RESULTS_DIR / "2026-03-23_scenario-a_fixed-sizing_evntou_reopt-results.json"
    )
    result_b = load_json(
        RESULTS_DIR
        / "2026-03-20_scenario-b_fixed-sizing_ppa-discount_reopt-results.json"
    )
    result_c = load_json(
        RESULTS_DIR / "2026-03-23_scenario-c_optimized-sizing_reopt-results.json"
    )
    result_d = load_json(
        RESULTS_DIR / "2026-03-20_scenario-d_dppa-baseline_reopt-results.json"
    )

    scenario_a = load_json(
        REPO_ROOT
        / "scenarios"
        / "case_studies"
        / "saigon18"
        / "2026-03-20_scenario-a_fixed-sizing_evntou.json"
    )
    scenario_d = load_json(
        REPO_ROOT
        / "scenarios"
        / "case_studies"
        / "saigon18"
        / "2026-03-20_scenario-d_dppa-baseline.json"
    )

    equity_a = load_json(REPORTS_DIR / "2026-03-22_equity-irr_summary.json")
    settlement_d = load_json(REPORTS_DIR / "2026-03-29_scenario-d_dppa-settlement.json")
    equity_d = load_json(REPORTS_DIR / "2026-03-29_scenario-d_equity-irr_summary.json")
    tariff_sens = load_json(REPORTS_DIR / "2026-03-29_two-part-tariff-sensitivity.json")
    bess_analysis = load_json(REPORTS_DIR / "2026-03-29_bess-dispatch-analysis.json")

    summary_a = build_scenario_summary(
        "A - Baseline EVN TOU", result_a, equity=equity_a
    )
    summary_b = build_scenario_summary("B - Bundled PPA", result_b)
    summary_c = build_scenario_summary("C - Optimized sizing", result_c)
    summary_d = build_scenario_summary(
        "D - DPPA private-wire", result_d, settlement_d, equity_d
    )
    scenarios = [summary_a, summary_b, summary_c, summary_d]

    bess_a = split_bess(result_a, scenario_a)
    bess_d = split_bess(result_d, scenario_d)

    excel_npv = 22_034_000.0
    excel_equity_irr = 0.194
    excel_payback = 6.0
    excel_year1 = 5_056_418.0

    out_path = REPORTS_DIR / "2026-03-29_saigon18-phase5.html"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Saigon18 Final Analysis Report</title>
<style>
  :root {{
    --blue:#1d4ed8; --blue-bg:#e0ecff; --green:#15803d; --green-bg:#e8f7ee;
    --amber:#b45309; --amber-bg:#fff4db; --red:#b91c1c; --red-bg:#fde8e8;
    --ink:#1f2937; --muted:#6b7280; --line:#d1d5db; --bg:#f5f7fb; --card:#ffffff;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:Segoe UI, system-ui, sans-serif; color:var(--ink); background:linear-gradient(180deg,#eef4ff 0%, var(--bg) 260px); }}
  .page {{ max-width:1180px; margin:0 auto; padding:28px 18px 64px; }}
  .hero {{ background:linear-gradient(135deg,#123f93,#1d4ed8 65%,#1f8f7a); color:#fff; border-radius:18px; padding:30px 28px; box-shadow:0 12px 30px rgba(29,78,216,.15); }}
  .hero h1 {{ margin:0 0 6px; font-size:32px; }}
  .hero p {{ margin:0; color:rgba(255,255,255,.86); }}
  .hero-pills {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }}
  .pill {{ padding:5px 10px; border-radius:999px; border:1px solid rgba(255,255,255,.25); background:rgba(255,255,255,.12); font-size:12px; }}
  h2 {{ margin:28px 0 12px; font-size:18px; color:#123f93; }}
  .grid-4 {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
  .grid-2 {{ display:grid; grid-template-columns:repeat(2,1fr); gap:14px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; box-shadow:0 4px 14px rgba(15,23,42,.04); }}
  .card h3 {{ margin:0 0 6px; font-size:14px; }}
  .eyebrow {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }}
  .big {{ font-size:28px; font-weight:800; color:#123f93; margin:4px 0; }}
  .sub {{ font-size:12px; color:var(--muted); }}
  .badge {{ display:inline-block; padding:3px 9px; border-radius:999px; font-size:11px; font-weight:700; }}
  .badge-good {{ background:var(--green-bg); color:var(--green); }}
  .badge-warn {{ background:var(--amber-bg); color:var(--amber); }}
  .scenario-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
  .scenario-card {{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:18px; }}
  .scenario-card .value {{ font-size:24px; font-weight:800; margin:6px 0 2px; color:#123f93; }}
  .scenario-card .row {{ display:flex; justify-content:space-between; gap:12px; padding:6px 0; border-bottom:1px solid #edf0f4; font-size:12px; }}
  .scenario-card .row:last-child {{ border-bottom:none; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:14px; overflow:hidden; }}
  th {{ background:#123f93; color:#fff; font-size:12px; text-align:left; padding:10px 12px; }}
  td {{ padding:9px 12px; border-bottom:1px solid #edf0f4; font-size:13px; }}
  tr:last-child td {{ border-bottom:none; }}
  td.good {{ background:var(--green-bg); color:var(--green); font-weight:700; }}
  td.warn {{ background:var(--amber-bg); color:var(--amber); font-weight:700; }}
  td.bad {{ background:var(--red-bg); color:var(--red); font-weight:700; }}
  .chart-card {{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:18px; }}
  .chart-title {{ font-size:13px; font-weight:700; margin-bottom:12px; }}
  .bar-row {{ display:grid; grid-template-columns:170px 1fr 92px; gap:10px; align-items:center; margin:8px 0; }}
  .bar-label {{ font-size:12px; color:var(--muted); text-align:right; }}
  .bar-track {{ height:18px; background:#e5e7eb; border-radius:999px; overflow:hidden; }}
  .bar-fill {{ height:100%; border-radius:999px; }}
  .blue {{ background:linear-gradient(90deg,#2563eb,#3b82f6); }}
  .green {{ background:linear-gradient(90deg,#16a34a,#22c55e); }}
  .amber {{ background:linear-gradient(90deg,#d97706,#f59e0b); }}
  .red {{ background:linear-gradient(90deg,#dc2626,#ef4444); }}
  .bar-value {{ font-size:12px; color:var(--ink); font-variant-numeric:tabular-nums; }}
  .callout {{ border-left:4px solid #123f93; background:#fff; border-radius:12px; padding:16px 18px; border:1px solid var(--line); }}
  .checklist {{ display:grid; gap:8px; }}
  .check {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:10px 12px; font-size:13px; }}
  .footer {{ margin-top:40px; font-size:12px; color:var(--muted); text-align:center; }}
  @media (max-width: 980px) {{ .grid-4, .scenario-grid, .grid-2 {{ grid-template-columns:1fr 1fr; }} }}
  @media (max-width: 700px) {{ .grid-4, .scenario-grid, .grid-2 {{ grid-template-columns:1fr; }} .bar-row {{ grid-template-columns:1fr; }} .bar-label {{ text-align:left; }} table {{ display:block; overflow-x:auto; }} }}
</style>
</head>
<body>
<div class="page">
  <div class="hero">
    <h1>Saigon18 REopt Analysis — Phase 5</h1>
    <p>40.36 MWp solar + 66 MWh BESS, Ninh Sim, Khanh Hoa. Phase 5 adds Decree 146/2025 two-part tariff sensitivity and BESS dispatch Option B comparison to the Phase 4 private-wire foundation.</p>
    <div class="hero-pills">
      <span class="pill">4 scenarios analyzed</span>
      <span class="pill">Decree 57 export cap enforced</span>
      <span class="pill">Scenario D: private-wire DPPA @ 1,100 VND/kWh</span>
      <span class="pill">Phase 5: Decree 146/2025 capacity charge + BESS dispatch Option B</span>
      <span class="pill">Site: Ninh Sim, Khanh Hoa (12.48°N, 109.09°E proxy)</span>
      <span class="pill">Generated 2026-03-29</span>
    </div>
  </div>

  <h2>Project Overview</h2>
  <div class="grid-4">
    <div class="card"><div class="eyebrow">Project</div><div class="big">Saigon18</div><div class="sub">40.36 MWp PV + 66 MWh BESS</div></div>
    <div class="card"><div class="eyebrow">Location</div><div class="big">Ninh Sim, Khanh Hoa</div><div class="sub">Proxy coords 12.48°N, 109.09°E — confirm actuals with site team</div></div>
    <div class="card"><div class="eyebrow">Excel Headline</div><div class="big">19.4%</div><div class="sub">Equity IRR, $22.0M NPV, 6-year payback</div></div>
    <div class="card"><div class="eyebrow">Method</div><div class="big">REopt + Python</div><div class="sub">Julia solve, private-wire DPPA settlement, equity DCF, HTML synthesis</div></div>
  </div>

  <h2>Scenario Dashboard</h2>
  <div class="scenario-grid">
    {"".join(f'''<div class="scenario-card"><div class="eyebrow">{s['label']}</div><div style="margin:6px 0 12px"><span class="badge {badge_class(s['status'] == 'OPTIMAL')}">{s['status']}</span></div><div class="value">{fmt_money(s['npv_usd'])}</div><div class="sub">NPV</div><div class="row"><span>Unlevered IRR</span><strong>{fmt_pct(s['unlevered_irr'])}</strong></div><div class="row"><span>Equity IRR</span><strong>{'-' if s['equity_irr'] is None else fmt_pct(s['equity_irr'])}</strong></div><div class="row"><span>Payback</span><strong>{s['payback_years']:.2f} yr</strong></div><div class="row"><span>Year-1 value</span><strong>{fmt_money(s['year1_revenue_usd'])}</strong></div></div>''' for s in scenarios)}
  </div>

  <h2>Financial KPIs</h2>
  <table>
    <tr><th>Metric</th><th>Excel</th><th>Scenario A</th><th>Scenario B</th><th>Scenario C</th><th>Scenario D</th></tr>
    <tr><td>NPV</td><td>{fmt_money(excel_npv)}</td><td class="{cell_class(summary_a["npv_usd"], excel_npv)}">{fmt_money(summary_a["npv_usd"])}</td><td class="{cell_class(summary_b["npv_usd"], excel_npv)}">{fmt_money(summary_b["npv_usd"])}</td><td class="{cell_class(summary_c["npv_usd"], excel_npv)}">{fmt_money(summary_c["npv_usd"])}</td><td class="{cell_class(summary_d["npv_usd"], excel_npv)}">{fmt_money(summary_d["npv_usd"])}</td></tr>
    <tr><td>Unlevered IRR</td><td>-</td><td>{fmt_pct(summary_a["unlevered_irr"])}</td><td>{fmt_pct(summary_b["unlevered_irr"])}</td><td>{fmt_pct(summary_c["unlevered_irr"])}</td><td>{fmt_pct(summary_d["unlevered_irr"])}</td></tr>
    <tr><td>Equity IRR</td><td>{fmt_pct(excel_equity_irr)}</td><td class="{cell_class(summary_a["equity_irr"], excel_equity_irr)}">{fmt_pct(summary_a["equity_irr"])}</td><td>-</td><td>-</td><td class="{cell_class(summary_d["equity_irr"], excel_equity_irr)}">{fmt_pct(summary_d["equity_irr"])}</td></tr>
    <tr><td>Simple payback</td><td>{excel_payback:.1f} yr</td><td class="{cell_class(summary_a["payback_years"], excel_payback)}">{summary_a["payback_years"]:.2f} yr</td><td class="{cell_class(summary_b["payback_years"], excel_payback)}">{summary_b["payback_years"]:.2f} yr</td><td class="{cell_class(summary_c["payback_years"], excel_payback)}">{summary_c["payback_years"]:.2f} yr</td><td class="{cell_class(summary_d["payback_years"], excel_payback)}">{summary_d["payback_years"]:.2f} yr</td></tr>
    <tr><td>Year-1 value</td><td>{fmt_money(excel_year1)}</td><td class="{cell_class(summary_a["year1_revenue_usd"], excel_year1)}">{fmt_money(summary_a["year1_revenue_usd"])}</td><td class="{cell_class(summary_b["year1_revenue_usd"], excel_year1)}">{fmt_money(summary_b["year1_revenue_usd"])}</td><td class="{cell_class(summary_c["year1_revenue_usd"], excel_year1)}">{fmt_money(summary_c["year1_revenue_usd"])}</td><td class="{cell_class(summary_d["year1_revenue_usd"], excel_year1)}">{fmt_money(summary_d["year1_revenue_usd"])}</td></tr>
  </table>

  <h2>Energy Flow Charts</h2>
  <div class="grid-2">
    <div class="chart-card"><div class="chart-title">Annual PV production by scenario</div>{bar_rows([(s["label"], s["pv_prod_mwh"], color) for s, color in zip(scenarios, ["blue", "amber", "green", "red"])], "MWh")}</div>
    <div class="chart-card"><div class="chart-title">PV export by scenario</div>{bar_rows([(s["label"], s["pv_export_mwh"], color) for s, color in zip(scenarios, ["blue", "amber", "green", "red"])], "MWh")}</div>
    <div class="chart-card"><div class="chart-title">Grid purchases by scenario</div>{bar_rows([(s["label"], s["grid_mwh"], color) for s, color in zip(scenarios, ["blue", "amber", "green", "red"])], "MWh")}</div>
    <div class="chart-card"><div class="chart-title">BESS dispatch by tariff period (Scenario A / D)</div>{bar_rows([("A peak", bess_a["peak"], "blue"), ("A standard", bess_a["standard"], "amber"), ("D peak", bess_d["peak"], "green"), ("D standard", bess_d["standard"], "red")], "MWh")}</div>
  </div>

  <h2>Equity IRR Deep Dive</h2>
  <div class="grid-4">
    <div class="card"><div class="eyebrow">Excel Equity IRR</div><div class="big">19.4%</div><div class="sub">Workbook headline return</div></div>
    <div class="card"><div class="eyebrow">Scenario A Equity IRR</div><div class="big">19.8%</div><div class="sub">REopt avoided-cost only; +0.4% vs Excel</div></div>
    <div class="card"><div class="eyebrow">Scenario D Equity IRR</div><div class="big">{fmt_pct(summary_d["equity_irr"])}</div><div class="sub">Private-wire DPPA @ 1,100 VND/kWh — strike × matched volume</div></div>
    <div class="card"><div class="eyebrow">Scenario D Year-1 DPPA Revenue</div><div class="big">{fmt_money(settlement_d["total_settlement_usd"])}</div><div class="sub">Private-wire: 1,100 VND/kWh × {settlement_d["total_q_mwh"]:,.0f} MWh delivery</div></div>
  </div>
  <div class="callout" style="margin-top:14px;">
    <strong>Phase 4 change:</strong> Scenario D now uses the confirmed private-wire contract type. Settlement formula changed from CfD differential (max(0, strike − FMP) × kWh) to direct revenue (strike × kWh). Strike lowered from 1,800 to 1,100 VND/kWh to comply with the south private-wire ceiling (1,149.86 VND/kWh). Combined EBITDA = REopt base + DPPA revenue; in private-wire, the settlement represents the developer's contracted receipt, a portion of which is already embedded in the REopt avoided-cost base.
  </div>

  <h2>Decree 57 Compliance</h2>
  <div class="grid-2">
    <div class="card"><div class="eyebrow">Scenario A export fraction</div><div class="big">{summary_a["export_fraction"] * 100:.2f}%</div><div class="sub">Well below the 20% annual export cap</div></div>
    <div class="card"><div class="eyebrow">Scenario C export fraction</div><div class="big">{summary_c["export_fraction"] * 100:.2f}%</div><div class="sub">Still below the cap after optimized sizing</div></div>
  </div>
  <div class="callout" style="margin-top:14px;">
    Scenario D is now modeled as <strong>private-wire</strong> at 1,100 VND/kWh — confirmed by the site owner. The prior grid-connected assumption at 1,800 VND/kWh exceeded the documented south private-wire ceiling (1,149.86 VND/kWh) and has been corrected in Phase 4.
  </div>

  <h2>Where REopt Differs From Excel</h2>
  <table>
    <tr><th>Metric</th><th>Excel</th><th>REopt</th><th>Gap</th><th>Explanation</th></tr>
    <tr><td>Scenario A NPV</td><td>{fmt_money(excel_npv)}</td><td>{fmt_money(summary_a["npv_usd"])}</td><td>-52%</td><td>Pure avoided-cost framing is much lower than the workbook's blended contract + financing headline.</td></tr>
    <tr><td>Scenario D NPV</td><td>{fmt_money(excel_npv)}</td><td>{fmt_money(summary_d["npv_usd"])}</td><td>+{(summary_d["npv_usd"]/excel_npv-1)*100:.0f}%</td><td>Private-wire DPPA settlement NPV ({fmt_money(settlement_d["settlement_npv_usd"])}) added to base REopt project value.</td></tr>
    <tr><td>BESS dispatch</td><td>Peak 7,364 / Standard 1,227 MWh</td><td>Peak {bess_a["peak"]:,.0f} / Standard {bess_a["standard"]:,.0f} MWh</td><td>Higher peak, lower standard</td><td>REopt concentrates battery value into peak periods instead of following the workbook's fixed standard-hour discharge target.</td></tr>
    <tr><td>PV export</td><td>1,087 MWh</td><td>{summary_a["pv_export_mwh"]:,.0f} MWh</td><td>-50%</td><td>The hard export cap path and dispatch decisions keep exports low, so Decree 57 is not binding for the fixed-size case.</td></tr>
  </table>

  <h2>Findings And Recommendations</h2>
  <div class="checklist">
    <div class="check"><strong>1.</strong> The original equity-IRR validation holds up: Scenario A still lands at 19.8% versus the workbook's 19.4%.</div>
    <div class="check"><strong>2.</strong> Phase 4 corrects Scenario D from grid-connected (illegal 1,800 VND/kWh strike) to private-wire at 1,100 VND/kWh. Settlement formula is now strike × matched delivery — no FMP exposure — lifting year-1 DPPA revenue from $1.1M to {fmt_money(settlement_d["total_settlement_usd"])}.</div>
    <div class="check"><strong>3.</strong> Combined project + DPPA NPV reaches {fmt_money(summary_d["npv_usd"])} and equity IRR {fmt_pct(summary_d["equity_irr"])} under private-wire. Note: the settlement is additive to the REopt base for framework consistency; in practice, private-wire revenue partially overlaps with avoided-cost savings already captured by REopt.</div>
    <div class="check"><strong>4.</strong> Scenario C still shows that pure REopt cost optimization prefers more PV and no battery, so the fixed battery design needs a non-energy rationale if it is to be retained.</div>
    <div class="check"><strong>5.</strong> Site coordinates updated to Ninh Sim, Khanh Hoa proxy (12.48°N, 109.09°E). All four scenario JSONs updated. Actual site coords to be confirmed with survey team.</div>
  </div>

  <h2>Outstanding Items</h2>
  <div class="checklist">
    <div class="check">[~] Site: Ninh Sim, Khanh Hoa confirmed. Proxy coords 12.48°N, 109.09°E applied — confirm actuals with survey team for precise NREL API solar data.</div>
    <div class="check">[x] DPPA legal structure: private-wire confirmed. Strike set to 1,100 VND/kWh (below south ceiling 1,149.86 VND/kWh). Actual negotiated strike TBD.</div>
    <div class="check">[x] Phase 5: Decree 146/2025 two-part tariff sensitivity — at pilot rate 60 kVND/kW-month, demand savings add $32K–$98K/yr to base energy savings.</div>
    <div class="check">[x] Phase 5: BESS dispatch Option B comparison — REopt free optimisation outperforms Excel fixed-window by +88.8% in annual dispatch value ($1.92M vs $1.02M target).</div>
    <div class="check">[ ] Phase 5: Full Layer 4 Julia integration test run (separate from Python suite).</div>
    <div class="check">[ ] Phase 6: Staff validation — North Thuan Wind+Solar+BESS (Scenario 3 re-run).</div>
  </div>

  <h2>Phase 5 — Decree 146/2025 Two-Part Tariff Sensitivity</h2>
  <div class="callout">
    Decree 146/2025 pilots a capacity charge (VND/kW-month) for industrial customers (Jan–Jun 2026).
    A capacity charge rewards assets that reduce peak demand. Saigon18's solar+BESS reduces the annual
    grid-import peak from {tariff_sens["bau_annual_peak_kw"]:,.0f} kW (BAU) to {tariff_sens["solar_bess_annual_peak_kw"]:,.0f} kW
    (current REopt dispatch) — a {tariff_sens["peak_reduction_current_kw"]:,.0f} kW reduction.
    With demand-shaving optimisation the estimated achievable peak is {tariff_sens["demand_shaved_annual_peak_kw"]:,.0f} kW
    (additional {tariff_sens["peak_reduction_shaved_kw"] - tariff_sens["peak_reduction_current_kw"]:,.0f} kW via BESS dispatch re-tuning).
  </div>
  <table style="margin-top:14px;">
    <tr><th>Capacity charge rate (VND/kW-month)</th><th>Demand savings — current dispatch ($/yr)</th><th>Demand savings — shaved dispatch ($/yr)</th><th>Total year-1 savings — current ($)</th><th>Total year-1 savings — shaved ($)</th></tr>
    {"".join(f'<tr><td>{"Decree 146 pilot →" if r["rate_vnd_per_kw_month"] == tariff_sens["decree_146_pilot_rate_vnd_per_kw_month"] else ""} {r["rate_vnd_per_kw_month"]:,}</td><td>${r["current_dispatch"]["demand_savings_usd"]:,.0f}</td><td>${r["demand_shaving_optimised"]["demand_savings_usd"]:,.0f}</td><td class="{"good" if r["rate_vnd_per_kw_month"] > 0 else ""}">${r["total_savings_current_usd"]:,.0f}</td><td class="{"good" if r["rate_vnd_per_kw_month"] > 0 else ""}">${r["total_savings_shaved_usd"]:,.0f}</td></tr>' for r in tariff_sens["sweep"])}
  </table>
  <div class="callout" style="margin-top:10px;">
    At the {tariff_sens["decree_146_pilot_rate_vnd_per_kw_month"]:,} VND/kW-month pilot rate, demand savings add
    ${tariff_sens["pilot_case"]["current_dispatch"]["demand_savings_usd"]:,.0f}/yr (current dispatch) to
    ${tariff_sens["pilot_case"]["demand_shaving_optimised"]["demand_savings_usd"]:,.0f}/yr (demand-shaving estimate) on top of base energy savings.
    This is modest relative to the ${tariff_sens["year1_energy_savings_usd"]:,.0f} energy saving but becomes material at higher rates.
    A full demand-charge re-optimisation in REopt would capture the upper bound.
  </div>

  <h2>Phase 5 — BESS Dispatch: REopt Free vs Option B Time-Locked</h2>
  <div class="grid-2" style="margin-top:12px;">
    <div class="chart-card">
      <div class="chart-title">Dispatch by tariff period (MWh)</div>
      {bar_rows([
        ("REopt peak", bess_analysis["reopt_free_optimization"]["peak_discharge_mwh"], "blue"),
        ("REopt standard", bess_analysis["reopt_free_optimization"]["standard_discharge_mwh"], "amber"),
        ("Excel target peak", bess_analysis["excel_option_b_fixed_window"]["peak_discharge_mwh"], "green"),
        ("Excel target std", bess_analysis["excel_option_b_fixed_window"]["standard_discharge_mwh"], "red"),
      ], "MWh")}
    </div>
    <div class="chart-card">
      <div class="chart-title">Annual dispatch value (USD)</div>
      {bar_rows([
        ("REopt free optimisation", bess_analysis["reopt_free_optimization"]["annual_value_usd"], "blue"),
        ("Simulated Option B (grid-charge)", bess_analysis["simulated_option_b"]["annual_value_usd"], "green"),
        ("Excel Option B target", bess_analysis["excel_option_b_fixed_window"]["annual_value_usd"], "amber"),
      ], "USD")}
    </div>
  </div>
  <table style="margin-top:12px;">
    <tr><th>Strategy</th><th>Peak discharge (MWh)</th><th>Standard (MWh)</th><th>Total throughput (MWh)</th><th>Annual dispatch value</th></tr>
    <tr><td>REopt free optimisation</td><td>{bess_analysis["reopt_free_optimization"]["peak_discharge_mwh"]:,.0f}</td><td>{bess_analysis["reopt_free_optimization"]["standard_discharge_mwh"]:,.0f}</td><td>{bess_analysis["reopt_free_optimization"]["total_discharge_mwh"]:,.0f}</td><td class="good">{fmt_money(bess_analysis["reopt_free_optimization"]["annual_value_usd"])}</td></tr>
    <tr><td>Simulated Option B (time-locked, grid-charge)</td><td>{bess_analysis["simulated_option_b"]["peak_discharge_mwh"]:,.0f}</td><td>{bess_analysis["simulated_option_b"]["standard_discharge_mwh"]:,.0f}</td><td>{bess_analysis["simulated_option_b"]["total_discharge_mwh"]:,.0f}</td><td class="warn">{fmt_money(bess_analysis["simulated_option_b"]["annual_value_usd"])}</td></tr>
    <tr><td>Excel Option B (target)</td><td>{bess_analysis["excel_option_b_fixed_window"]["peak_discharge_mwh"]:,.0f}</td><td>{bess_analysis["excel_option_b_fixed_window"]["standard_discharge_mwh"]:,.0f}</td><td>{bess_analysis["excel_option_b_fixed_window"]["total_discharge_mwh"]:,.0f}</td><td class="warn">{fmt_money(bess_analysis["excel_option_b_fixed_window"]["annual_value_usd"])}</td></tr>
  </table>
  <div class="callout" style="margin-top:10px;">
    REopt free optimisation outperforms the Excel Option B target by {bess_analysis["reopt_vs_excel_delta_pct"]:+.1f}%
    (${bess_analysis["reopt_vs_excel_delta_usd"]:+,.0f}/yr) by concentrating more volume into peak hours through
    active TOU arbitrage rather than a fixed charge/discharge window. The {bess_analysis["tariff_rates_vnd_per_kwh"]["peak"]:,.0f}/{bess_analysis["tariff_rates_vnd_per_kwh"]["standard"]:,.0f}/{bess_analysis["tariff_rates_vnd_per_kwh"]["offpeak"]:,.0f} VND/kWh
    (peak/standard/offpeak) spread rewards peak-concentrated dispatch.
  </div>

  <div class="footer">Generated by <code>scripts/python/integration/generate_html_report.py</code> — Phase 5 report includes Decree 146/2025 two-part tariff sensitivity and BESS dispatch Option B analysis.</div>
</div>
</body>
</html>
"""

    out_path.write_text(html, encoding="utf-8")
    print(f"Final HTML report written to: {out_path}")


if __name__ == "__main__":
    main()
