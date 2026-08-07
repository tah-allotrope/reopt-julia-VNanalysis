"""
Generate the North Thuan REopt validation HTML report.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORTS_DIR = REPO_ROOT / "artifacts" / "reports" / "north_thuan"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_money(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "-"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.{decimals}f}M"
    return f"${value:,.0f}"


def fmt_pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "-"
    return f"{value:.{decimals}f}%"


def fmt_gwh(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:.{decimals}f} GWh"


def status_class(status: str) -> str:
    return {"OK": "good", "WARN": "warn", "INFO": "neutral"}.get(status, "neutral")


def main() -> None:
    payload = load_json(REPORTS_DIR / "2026-03-31_north-thuan-reopt-validation.json")
    scenario_a = payload["scenario_a"]
    scenario_b = payload.get("scenario_b")
    scenario_c = payload.get("scenario_c")
    settlement = payload["settlement_check"]
    summary = payload["summary"]

    metrics_a = scenario_a["metrics"]
    comp = {row["key"]: row for row in scenario_a["comparison"]}
    metrics_b = None if scenario_b is None else scenario_b["metrics"]
    metrics_c = None if scenario_c is None else scenario_c["metrics"]

    out_path = REPORTS_DIR / "2026-03-31_north-thuan-reopt-validation.html"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>North Thuan REopt Validation Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  :root {{
    --blue:#1456c3; --blue-bg:#dce9ff; --green:#147a44; --green-bg:#e7f7ee;
    --amber:#b76b00; --amber-bg:#fff1d8; --ink:#1d2939; --muted:#667085;
    --line:#d0d7e2; --bg:#f4f7fb; --card:#ffffff;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:Segoe UI,system-ui,sans-serif; color:var(--ink); background:linear-gradient(180deg,#eef5ff 0%,var(--bg) 260px); }}
  .page {{ max-width:1160px; margin:0 auto; padding:28px 18px 60px; }}
  .hero {{ background:linear-gradient(135deg,#0f3460,#1456c3 58%,#177245); color:#fff; border-radius:20px; padding:30px 28px; box-shadow:0 12px 32px rgba(20,86,195,.18); }}
  .hero h1 {{ margin:0 0 8px; font-size:30px; }}
  .hero p {{ margin:0; color:rgba(255,255,255,.88); }}
  .hero-pills {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }}
  .pill {{ padding:6px 10px; border-radius:999px; border:1px solid rgba(255,255,255,.24); background:rgba(255,255,255,.12); font-size:12px; }}
  h2 {{ margin:28px 0 12px; font-size:18px; color:#0f3460; }}
  .grid-4 {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
  .grid-3 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
  .grid-2 {{ display:grid; grid-template-columns:repeat(2,1fr); gap:14px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; box-shadow:0 4px 14px rgba(15,23,42,.04); }}
  .eyebrow {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }}
  .big {{ font-size:28px; font-weight:800; color:#0f3460; margin:4px 0; }}
  .sub {{ font-size:12px; color:var(--muted); }}
  .badge {{ display:inline-block; padding:4px 9px; border-radius:999px; font-size:11px; font-weight:700; }}
  .badge-good {{ background:var(--green-bg); color:var(--green); }}
  .badge-warn {{ background:var(--amber-bg); color:var(--amber); }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:14px; overflow:hidden; }}
  th {{ background:#0f3460; color:#fff; font-size:12px; text-align:left; padding:10px 12px; }}
  td {{ padding:9px 12px; border-bottom:1px solid #edf1f5; font-size:13px; }}
  tr:last-child td {{ border-bottom:none; }}
  td.good {{ background:var(--green-bg); color:var(--green); font-weight:700; }}
  td.warn {{ background:var(--amber-bg); color:var(--amber); font-weight:700; }}
  .callout {{ border-left:4px solid #1456c3; background:#fff; border-radius:12px; padding:16px 18px; border:1px solid var(--line); }}
  .chart-card {{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:16px 18px; }}
  .footer {{ margin-top:36px; text-align:center; font-size:12px; color:var(--muted); }}
  @media (max-width:980px) {{ .grid-4,.grid-3,.grid-2 {{ grid-template-columns:1fr 1fr; }} }}
  @media (max-width:720px) {{ .grid-4,.grid-3,.grid-2 {{ grid-template-columns:1fr; }} table {{ display:block; overflow-x:auto; }} }}
</style>
</head>
<body>
<div class="page">
  <div class="hero">
    <h1>North Thuan Wind+Solar+BESS - REopt Validation</h1>
    <p>Local-REopt validation framework for Scenario 3 using synthetic hourly load, fixed/optimized hybrid cases, and post-processed virtual DPPA settlement revenue.</p>
    <div class="hero-pills">
      <span class="pill">Scenario A - fixed 30 MW solar + 20 MW wind + 10 MW / 40 MWh BESS</span>
      <span class="pill">Scenario B - optimized sizing sensitivity</span>
      <span class="pill">Scenario C - no-BESS baseline</span>
      <span class="pill">Summary: {summary["ok"]} OK / {summary["warn"]} WARN</span>
      <span class="pill">Generated 2026-03-31</span>
    </div>
  </div>

  <h2>Executive Summary</h2>
  <div class="grid-4">
    <div class="card"><div class="eyebrow">Checks passed</div><div class="big">{summary["ok"]}</div><div class="sub">Within configured tolerance bands</div></div>
    <div class="card"><div class="eyebrow">Checks flagged</div><div class="big">{summary["warn"]}</div><div class="sub">Items needing scenario review</div></div>
    <div class="card"><div class="eyebrow">Scenario A matched volume</div><div class="big">{metrics_a["matched_gwh_yr1"]:.2f}</div><div class="sub">GWh/year delivered from RE + BESS</div></div>
    <div class="card"><div class="eyebrow">DPPA revenue check</div><div class="big">{fmt_money(settlement["developer_revenue_yr1_usd"])}</div><div class="sub">Staff claim: {fmt_money(settlement["staff_revenue_yr1_usd"])} <span class="badge {"badge-good" if settlement["status"] == "OK" else "badge-warn"}">{settlement["status"]}</span></div></div>
  </div>

  <h2>Energy Dispatch Comparison</h2>
  <table>
    <tr><th>Metric</th><th>Staff PDF</th><th>REopt Scenario A</th><th>Delta</th><th>Status</th></tr>
    <tr><td>Solar generation</td><td>51.00 GWh</td><td>{metrics_a["solar_gwh_yr1"]:.2f} GWh</td><td>{comp["solar_gwh_yr1"]["delta_pct"]:+.1f}%</td><td class="{status_class(comp["solar_gwh_yr1"]["status"])}">{comp["solar_gwh_yr1"]["status"]}</td></tr>
    <tr><td>Wind generation</td><td>66.60 GWh</td><td>{metrics_a["wind_gwh_yr1"]:.2f} GWh</td><td>{comp["wind_gwh_yr1"]["delta_pct"]:+.1f}%</td><td class="{status_class(comp["wind_gwh_yr1"]["status"])}">{comp["wind_gwh_yr1"]["status"]}</td></tr>
    <tr><td>Total RE generation</td><td>117.56 GWh</td><td>{metrics_a["total_gen_gwh_yr1"]:.2f} GWh</td><td>{comp["total_gen_gwh_yr1"]["delta_pct"]:+.1f}%</td><td class="{status_class(comp["total_gen_gwh_yr1"]["status"])}">{comp["total_gen_gwh_yr1"]["status"]}</td></tr>
    <tr><td>Matched volume</td><td>70.05 GWh</td><td>{metrics_a["matched_gwh_yr1"]:.2f} GWh</td><td>{comp["matched_gwh_yr1"]["delta_pct"]:+.1f}%</td><td class="{status_class(comp["matched_gwh_yr1"]["status"])}">{comp["matched_gwh_yr1"]["status"]}</td></tr>
    <tr><td>RE penetration</td><td>48.8%</td><td>{fmt_pct(metrics_a["re_penetration_pct"])}</td><td>{comp["re_penetration_pct"]["delta_pct"]:+.1f}%</td><td class="{status_class(comp["re_penetration_pct"]["status"])}">{comp["re_penetration_pct"]["status"]}</td></tr>
    <tr><td>Self-consumption</td><td>59.6%</td><td>{fmt_pct(metrics_a["self_consumption_pct"])}</td><td>{comp["self_consumption_pct"]["delta_pct"]:+.1f}%</td><td class="{status_class(comp["self_consumption_pct"]["status"])}">{comp["self_consumption_pct"]["status"]}</td></tr>
    <tr><td>Factory NPV proxy</td><td>{fmt_money(payload["staff_targets"]["factory_npv_usd"])}</td><td>{fmt_money(metrics_a["factory_npv_usd"])}</td><td>{comp["factory_npv_usd"]["delta_pct"]:+.1f}%</td><td class="{status_class(comp["factory_npv_usd"]["status"])}">{comp["factory_npv_usd"]["status"]}</td></tr>
  </table>

  <div class="grid-2" style="margin-top:14px;">
    <div class="chart-card">
      <div class="eyebrow">Energy comparison</div>
      <canvas id="energyChart"></canvas>
    </div>
    <div class="chart-card">
      <div class="eyebrow">Sizing sensitivity</div>
      <canvas id="sizingChart"></canvas>
    </div>
  </div>

  <h2>Sizing Sensitivity</h2>
  <div class="grid-3">
    <div class="card"><div class="eyebrow">Scenario A fixed case</div><div class="big">{metrics_a["pv_size_mw"]:.1f} / {metrics_a["wind_size_mw"]:.1f}</div><div class="sub">Solar / wind MW, BESS {metrics_a["bess_mw"]:.1f} MW / {metrics_a["bess_mwh"]:.1f} MWh</div></div>
    <div class="card"><div class="eyebrow">Scenario B optimized case</div><div class="big">{"-" if metrics_b is None else f"{metrics_b['pv_size_mw']:.1f} / {metrics_b['wind_size_mw']:.1f}"}</div><div class="sub">{"Solve result not available yet" if metrics_b is None else f"Solar / wind MW, BESS {metrics_b['bess_mw']:.1f} MW / {metrics_b['bess_mwh']:.1f} MWh"}</div></div>
    <div class="card"><div class="eyebrow">Scenario C no-BESS baseline</div><div class="big">{"-" if metrics_c is None else f"{metrics_c['pv_size_mw']:.1f} / {metrics_c['wind_size_mw']:.1f}"}</div><div class="sub">{"Solve result not available yet" if metrics_c is None else f"Solar / wind MW, storage fixed at {metrics_c['bess_mw']:.1f} MW / {metrics_c['bess_mwh']:.1f} MWh"}</div></div>
  </div>

  <h2>DPPA Revenue Check</h2>
  <div class="grid-2">
    <div class="card"><div class="eyebrow">Matched volume</div><div class="big">{settlement["matched_volume_mwh"]:,.0f}</div><div class="sub">MWh/year paid at strike price</div></div>
    <div class="card"><div class="eyebrow">Unmatched volume</div><div class="big">{settlement["unmatched_volume_mwh"]:,.0f}</div><div class="sub">MWh/year settled at FMP proxy</div></div>
    <div class="card"><div class="eyebrow">Developer revenue - year 1</div><div class="big">{fmt_money(settlement["developer_revenue_yr1_usd"])}</div><div class="sub">Strike revenue + merchant FMP revenue</div></div>
    <div class="card"><div class="eyebrow">Delta vs staff</div><div class="big">{settlement["delta_pct"]:+.1f}%</div><div class="sub"><span class="badge {"badge-good" if settlement["status"] == "OK" else "badge-warn"}">{settlement["status"]}</span> at +/-{summary["settlement_tolerance_pct"]:.0f}% tolerance</div></div>
  </div>

  <h2>Financial Metrics</h2>
  <table>
    <tr><th>Scenario</th><th>Factory NPV proxy</th><th>Year-1 savings proxy</th><th>Simple payback</th><th>Status</th></tr>
    <tr><td>A - fixed sizing</td><td>{fmt_money(metrics_a["factory_npv_usd"])}</td><td>{fmt_money(metrics_a["factory_gross_saving_yr1_usd"])}</td><td>{metrics_a["simple_payback_years"]:.2f} yr</td><td>{metrics_a["status"].upper()}</td></tr>
    <tr><td>B - optimized sizing</td><td>{"-" if metrics_b is None else fmt_money(metrics_b["factory_npv_usd"])}</td><td>{"-" if metrics_b is None else fmt_money(metrics_b["factory_gross_saving_yr1_usd"])}</td><td>{"-" if metrics_b is None else f"{metrics_b['simple_payback_years']:.2f} yr"}</td><td>{"not run" if metrics_b is None else metrics_b["status"].upper()}</td></tr>
    <tr><td>C - no BESS</td><td>{"-" if metrics_c is None else fmt_money(metrics_c["factory_npv_usd"])}</td><td>{"-" if metrics_c is None else fmt_money(metrics_c["factory_gross_saving_yr1_usd"])}</td><td>{"-" if metrics_c is None else f"{metrics_c['simple_payback_years']:.2f} yr"}</td><td>{"not run" if metrics_c is None else metrics_c["status"].upper()}</td></tr>
  </table>

  <h2>Methodology Notes</h2>
  <div class="callout">
    <strong>DPPA approximation:</strong> REopt does not natively model Vietnam's virtual DPPA CfD structure, so the optimization uses a flat 0.055 USD/kWh strike-price tariff and the developer-revenue check is post-processed from REopt annual dispatch. Scenario A compares the hybrid dispatch against the staff PDF claims, while the settlement check combines strike-price revenue on matched volume with FMP revenue on unmatched generation.
  </div>
  <div class="callout" style="margin-top:12px;">
    <strong>Known limitations:</strong> the factory load profile is synthetic, the FMP series is a flat year-1 proxy derived from the staff revenue claim, and the final quality of Scenario B/C conclusions depends on running full local Julia solves. The implementation is designed so measured load or hourly market-price data can replace the synthetic series later without changing the workflow shape.
  </div>

  <div class="footer">Generated by <code>scripts/python/integration/generate_north_thuan_reopt_report.py</code> from <code>artifacts/reports/north_thuan/2026-03-31_north-thuan-reopt-validation.json</code></div>
</div>
<script>
  const energyCtx = document.getElementById('energyChart');
  new Chart(energyCtx, {{
    type: 'bar',
    data: {{
      labels: ['Solar GWh', 'Wind GWh', 'Total RE GWh', 'Matched GWh'],
      datasets: [
        {{ label: 'Staff PDF', data: [51.0, 66.6, 117.56, 70.05], backgroundColor: '#8ec5ff' }},
        {{ label: 'REopt Scenario A', data: [{metrics_a["solar_gwh_yr1"]:.4f}, {metrics_a["wind_gwh_yr1"]:.4f}, {metrics_a["total_gen_gwh_yr1"]:.4f}, {metrics_a["matched_gwh_yr1"]:.4f}], backgroundColor: '#147a44' }}
      ]
    }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }} }}
  }});

  const sizingCtx = document.getElementById('sizingChart');
  new Chart(sizingCtx, {{
    type: 'bar',
    data: {{
      labels: ['PV MW', 'Wind MW', 'BESS MW', 'BESS MWh'],
      datasets: [
        {{ label: 'Scenario A fixed', data: [{metrics_a["pv_size_mw"]:.4f}, {metrics_a["wind_size_mw"]:.4f}, {metrics_a["bess_mw"]:.4f}, {metrics_a["bess_mwh"]:.4f}], backgroundColor: '#1456c3' }},
        {{ label: 'Scenario B optimized', data: [{0.0 if metrics_b is None else metrics_b["pv_size_mw"]:.4f}, {0.0 if metrics_b is None else metrics_b["wind_size_mw"]:.4f}, {0.0 if metrics_b is None else metrics_b["bess_mw"]:.4f}, {0.0 if metrics_b is None else metrics_b["bess_mwh"]:.4f}], backgroundColor: '#b76b00' }},
        {{ label: 'Scenario C no BESS', data: [{0.0 if metrics_c is None else metrics_c["pv_size_mw"]:.4f}, {0.0 if metrics_c is None else metrics_c["wind_size_mw"]:.4f}, {0.0 if metrics_c is None else metrics_c["bess_mw"]:.4f}, {0.0 if metrics_c is None else metrics_c["bess_mwh"]:.4f}], backgroundColor: '#147a44' }}
      ]
    }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }} }}
  }});
</script>
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"North Thuan REopt HTML report written to: {out_path}")


if __name__ == "__main__":
    main()
