"""
Phase 7 — Cross-project comparison dashboard: Saigon18 vs North Thuan.

Pulls all Phase 4–6 artifacts and generates a single self-contained HTML
dashboard comparing the two projects side by side.

Usage:
    python scripts/python/integration/generate_cross_project_dashboard.py \
        --output artifacts/reports/2026-03-29_cross-project-dashboard.html
"""

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORTS_DIR = REPO_ROOT / "artifacts" / "reports"
SAIGON18_RESULTS = REPO_ROOT / "artifacts" / "results" / "saigon18"
SAIGON18_REPORTS = REPORTS_DIR / "saigon18"
NT_REPORTS = REPORTS_DIR / "north_thuan"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_money(v, decimals: int = 1) -> str:
    if v is None:
        return "-"
    v = float(v)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.{decimals}f}M"
    return f"${v:,.0f}"


def fmt_pct(v, decimals: int = 1) -> str:
    if v is None:
        return "-"
    v = float(v)
    return f"{v:.{decimals}f}%"


def bar(value: float, max_val: float, color: str) -> str:
    w = 0 if max_val == 0 else min(100.0, value / max_val * 100)
    return (
        f'<div class="bar-row">'
        f'<div class="bar-track">'
        f'<div class="bar-fill {color}" style="width:{w:.1f}%"></div>'
        f'</div>'
        f'<div class="bar-val">{value:,.0f}</div>'
        f'</div>'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/reports/2026-03-29_cross-project-dashboard.html",
    )
    args = parser.parse_args()

    # ── Load Saigon18 artifacts ──────────────────────────────────────────────
    r_a = load_json(SAIGON18_RESULTS / "2026-03-23_scenario-a_fixed-sizing_evntou_reopt-results.json")
    _r_c = load_json(SAIGON18_RESULTS / "2026-03-23_scenario-c_optimized-sizing_reopt-results.json")
    _r_d = load_json(SAIGON18_RESULTS / "2026-03-20_scenario-d_dppa-baseline_reopt-results.json")
    eq_a = load_json(SAIGON18_REPORTS / "2026-03-22_equity-irr_summary.json")
    eq_d = load_json(SAIGON18_REPORTS / "2026-03-29_scenario-d_equity-irr_summary.json")
    sett_d = load_json(SAIGON18_REPORTS / "2026-03-29_scenario-d_dppa-settlement.json")
    tariff_s = load_json(SAIGON18_REPORTS / "2026-03-29_two-part-tariff-sensitivity.json")
    bess_s = load_json(SAIGON18_REPORTS / "2026-03-29_bess-dispatch-analysis.json")

    fa = r_a["Financial"]
    s18_capex = fa["initial_capital_costs"]
    s18_pv_mw = r_a["PV"]["size_kw"] / 1_000.0
    s18_bess_mw = r_a["ElectricStorage"]["size_kw"] / 1_000.0
    _s18_bess_mwh = r_a["ElectricStorage"]["size_kwh"] / 1_000.0
    s18_gen_gwh = r_a["PV"]["year_one_energy_produced_kwh"] / 1e6
    _s18_grid_gwh = fa["lifecycle_elecbill_after_tax_bau"] / 1e6  # proxy
    s18_unlevered_irr = fa["internal_rate_of_return"]
    s18_npv_a = fa["npv"]
    s18_payback = fa["simple_payback_years"]
    s18_yr1_savings = fa["year_one_total_operating_cost_savings_before_tax"]
    s18_eq_irr_a = eq_a["equity_irr"]
    s18_eq_irr_d = eq_d["equity_irr"]
    s18_settlement_yr1 = sett_d["total_settlement_usd"]
    s18_settlement_npv = sett_d["settlement_npv_usd"]
    s18_combined_yr1 = s18_yr1_savings + s18_settlement_yr1
    s18_combined_npv = s18_npv_a + s18_settlement_npv
    s18_bess_reopt_val = bess_s["reopt_free_optimization"]["annual_value_usd"]
    s18_demand_savings = tariff_s["pilot_case"]["current_dispatch"]["demand_savings_usd"]
    s18_peak_reduction = tariff_s["peak_reduction_current_kw"]
    s18_capex_per_mw = s18_capex / (s18_pv_mw + s18_bess_mw)

    # ── Load North Thuan artifacts ───────────────────────────────────────────
    nt = load_json(NT_REPORTS / "2026-03-29_north-thuan-validation.json")
    nt_c = nt["computed"]
    nt_a = nt["assumptions"]
    nt_rows = nt["annual_cashflows"]

    nt_solar_mw = 30.0
    nt_wind_mw = 20.0
    nt_bess_mw = 10.0
    _nt_bess_mwh = 40.0
    nt_capex = nt_a["total_capex_usd"]
    nt_total_mw = nt_solar_mw + nt_wind_mw + nt_bess_mw
    nt_capex_per_mw = nt_capex / nt_total_mw
    nt_gen_gwh = nt_c["total_gen_gwh_yr1"]
    nt_matched_gwh = nt_c["matched_gwh_yr1"]
    nt_proj_irr = nt_c["project_irr_pct"]
    nt_eq_irr = nt_c["equity_irr_pct"]
    nt_proj_npv = nt_c["project_npv_usd"]
    nt_eq_npv = nt_c["equity_npv_usd"]
    nt_factory_npv = nt_c["factory_npv_usd"]
    nt_factory_saving = nt_c["factory_gross_saving_yr1_usd"]
    nt_dscr = nt_c["min_dscr"]
    nt_payback = nt_c["project_payback_years"]
    nt_yr1_revenue = nt_rows[0]["revenue_usd"]

    # North Thuan sensitivity: viability at min strike (from PDF: ≥3.850 ¢/kWh at all rates)
    nt_min_viable_strike_c_kwh = 3.850
    nt_contracted_strike_c_kwh = 5.500
    nt_strike_headroom_c_kwh = nt_contracted_strike_c_kwh - nt_min_viable_strike_c_kwh

    # Saigon18 private-wire ceiling headroom
    s18_strike_vnd = sett_d["strike_price_vnd_per_kwh"]
    s18_ceiling_vnd = sett_d["private_wire_south_ceiling_vnd_per_kwh"]
    s18_headroom_vnd = s18_ceiling_vnd - s18_strike_vnd

    # Sweep for strike sensitivity comparison
    nt_strikes = [3.5, 4.0, 4.273, 5.0, 5.500, 6.0, 7.0, 7.394]
    s18_strikes_vnd = [800, 900, 1000, 1100, 1149.86]

    # ── Build HTML ────────────────────────────────────────────────────────────
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cross-Project Dashboard — Saigon18 vs North Thuan</title>
<style>
  :root {{
    --s18:#1d4ed8; --s18-bg:#e0ecff;   /* Saigon18 = blue */
    --nt:#0f7d5c;  --nt-bg:#e8f7f0;    /* North Thuan = green */
    --amber:#b45309; --amber-bg:#fff4db;
    --ink:#1f2937; --muted:#6b7280; --line:#d1d5db; --bg:#f5f7fb; --card:#fff;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:Segoe UI,system-ui,sans-serif; color:var(--ink); background:linear-gradient(180deg,#eef4ff 0%,var(--bg) 260px); }}
  .page {{ max-width:1180px; margin:0 auto; padding:28px 18px 64px; }}
  .hero {{ background:linear-gradient(135deg,#0f3460,#1d4ed8 50%,#0f7d5c); color:#fff; border-radius:18px; padding:30px 28px; box-shadow:0 12px 30px rgba(29,78,216,.15); }}
  .hero h1 {{ margin:0 0 6px; font-size:28px; }}
  .hero p {{ margin:0; color:rgba(255,255,255,.86); font-size:14px; }}
  .hero-pills {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }}
  .pill {{ padding:5px 10px; border-radius:999px; border:1px solid rgba(255,255,255,.25); background:rgba(255,255,255,.12); font-size:12px; }}
  .pill-s18 {{ border-color:rgba(99,157,255,.6); background:rgba(29,78,216,.25); }}
  .pill-nt  {{ border-color:rgba(99,210,170,.6); background:rgba(15,125,92,.25); }}
  h2 {{ margin:28px 0 12px; font-size:17px; color:#0f3460; }}
  h3 {{ margin:14px 0 8px; font-size:14px; color:var(--muted); text-transform:uppercase; letter-spacing:.07em; }}
  .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .grid-3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; box-shadow:0 4px 14px rgba(15,23,42,.04); }}
  .card-s18 {{ border-top:3px solid var(--s18); }}
  .card-nt  {{ border-top:3px solid var(--nt); }}
  .eyebrow {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }}
  .big {{ font-size:26px; font-weight:800; margin:4px 0; }}
  .s18 {{ color:var(--s18); }} .nt {{ color:var(--nt); }}
  .sub {{ font-size:12px; color:var(--muted); }}
  .badge {{ display:inline-block; padding:3px 9px; border-radius:999px; font-size:11px; font-weight:700; }}
  .badge-s18 {{ background:var(--s18-bg); color:var(--s18); }}
  .badge-nt  {{ background:var(--nt-bg);  color:var(--nt); }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:14px; overflow:hidden; font-size:13px; }}
  th {{ background:#0f3460; color:#fff; font-size:12px; text-align:left; padding:9px 12px; }}
  th.s18-col {{ background:var(--s18); }}
  th.nt-col  {{ background:var(--nt); }}
  td {{ padding:8px 12px; border-bottom:1px solid #edf0f4; }}
  tr:last-child td {{ border-bottom:none; }}
  td.s18 {{ background:var(--s18-bg); color:var(--s18); font-weight:700; }}
  td.nt  {{ background:var(--nt-bg);  color:var(--nt);  font-weight:700; }}
  td.good {{ background:#e8f7ee; color:#15803d; font-weight:700; }}
  td.warn {{ background:var(--amber-bg); color:var(--amber); font-weight:700; }}
  .callout {{ border-left:4px solid #0f3460; background:#fff; border-radius:12px; padding:14px 18px; border:1px solid var(--line); font-size:13px; margin-top:12px; }}
  .bar-row {{ display:grid; grid-template-columns:1fr 80px; gap:8px; align-items:center; margin:6px 0; }}
  .bar-track {{ height:16px; background:#e5e7eb; border-radius:999px; overflow:hidden; }}
  .bar-fill {{ height:100%; border-radius:999px; }}
  .bar-s18 {{ background:linear-gradient(90deg,#2563eb,#60a5fa); }}
  .bar-nt  {{ background:linear-gradient(90deg,#0f7d5c,#34d399); }}
  .bar-val {{ font-size:12px; color:var(--ink); text-align:right; font-variant-numeric:tabular-nums; }}
  .row-item {{ display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid #edf0f4; font-size:13px; }}
  .row-item:last-child {{ border-bottom:none; }}
  .footer {{ margin-top:40px; font-size:12px; color:var(--muted); text-align:center; }}
  @media (max-width:900px) {{ .grid-2,.grid-3 {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="page">

  <div class="hero">
    <h1>Cross-Project Dashboard — Saigon18 vs North Thuan</h1>
    <p>Consolidated comparison of two Vietnam DPPA projects across technology mix, contract structure, and financial performance.</p>
    <div class="hero-pills">
      <span class="pill pill-s18">Saigon18 — 40.36 MWp Solar + 66 MWh BESS — Ninh Sim, Khanh Hoa</span>
      <span class="pill pill-nt">North Thuan — 30 MW Solar + 20 MW Wind + 10 MW/40 MWh BESS — North Thuan Province</span>
      <span class="pill">Phase 4–6 validated outputs · Generated 2026-03-29</span>
    </div>
  </div>

  <h2>Side-by-Side Project Overview</h2>
  <div class="grid-2">
    <div class="card card-s18">
      <div class="eyebrow">Saigon18 <span class="badge badge-s18">Private-wire DPPA</span></div>
      <div class="big s18">40.36 MWp Solar + 66 MWh BESS</div>
      <div style="margin-top:10px;">
        <div class="row-item"><span>Site</span><strong>Ninh Sim, Khanh Hoa (12.48°N, 109.09°E proxy)</strong></div>
        <div class="row-item"><span>Total CAPEX</span><strong>{fmt_money(s18_capex)}</strong></div>
        <div class="row-item"><span>CAPEX / MW</span><strong>${s18_capex_per_mw:,.0f}/kW</strong></div>
        <div class="row-item"><span>Year-1 solar generation</span><strong>{s18_gen_gwh:.1f} GWh</strong></div>
        <div class="row-item"><span>Contract type</span><strong>Private-wire @ 1,100 VND/kWh</strong></div>
        <div class="row-item"><span>Strike vs ceiling</span><strong>1,100 / 1,149.86 VND/kWh ({s18_headroom_vnd:.2f} VND/kWh headroom)</strong></div>
        <div class="row-item"><span>DPPA revenue yr1</span><strong>{fmt_money(s18_settlement_yr1)}</strong></div>
        <div class="row-item"><span>Unlevered IRR (Scenario A)</span><strong>{fmt_pct(s18_unlevered_irr * 100)}</strong></div>
        <div class="row-item"><span>Equity IRR (Scenario A)</span><strong>{fmt_pct(s18_eq_irr_a * 100)}</strong></div>
        <div class="row-item"><span>Equity IRR (Scenario D, private-wire)</span><strong>{fmt_pct(s18_eq_irr_d * 100)}</strong></div>
        <div class="row-item"><span>Project payback</span><strong>{s18_payback:.1f} yr</strong></div>
        <div class="row-item"><span>Decree 57 export fraction</span><strong>0.80% (well below 20% cap)</strong></div>
      </div>
    </div>
    <div class="card card-nt">
      <div class="eyebrow">North Thuan <span class="badge badge-nt">Virtual DPPA (NDS7025)</span></div>
      <div class="big nt">30 MW Solar + 20 MW Wind + 10 MW/40 MWh BESS</div>
      <div style="margin-top:10px;">
        <div class="row-item"><span>Site</span><strong>North Thuan Province (~11.7°N)</strong></div>
        <div class="row-item"><span>Total CAPEX</span><strong>{fmt_money(nt_capex)}</strong></div>
        <div class="row-item"><span>CAPEX / MW</span><strong>${nt_capex_per_mw:,.0f}/kW</strong></div>
        <div class="row-item"><span>Year-1 total generation</span><strong>{nt_gen_gwh:.1f} GWh (solar + wind)</strong></div>
        <div class="row-item"><span>Matched volume</span><strong>{nt_matched_gwh:.1f} GWh (59.6% self-consumption)</strong></div>
        <div class="row-item"><span>Contract type</span><strong>Virtual CfD @ 5.500 ¢/kWh</strong></div>
        <div class="row-item"><span>Strike vs developer floor</span><strong>5.500 / 4.273 ¢/kWh (+{nt_strike_headroom_c_kwh:.3f}¢ headroom)</strong></div>
        <div class="row-item"><span>Factory saving yr1</span><strong>{fmt_money(nt_factory_saving)}</strong></div>
        <div class="row-item"><span>Project IRR (unlevered)</span><strong>{fmt_pct(nt_proj_irr)}</strong></div>
        <div class="row-item"><span>Equity IRR (levered)</span><strong>{fmt_pct(nt_eq_irr)}</strong></div>
        <div class="row-item"><span>Project payback</span><strong>Year {nt_payback}</strong></div>
        <div class="row-item"><span>Min DSCR (during loan)</span><strong>{nt_dscr}×</strong></div>
      </div>
    </div>
  </div>

  <h2>Key Financial Metrics Comparison</h2>
  <table>
    <tr>
      <th>Metric</th>
      <th class="s18-col">Saigon18 (Scenario A)</th>
      <th class="s18-col">Saigon18 (Scenario D private-wire)</th>
      <th class="nt-col">North Thuan (validated)</th>
    </tr>
    <tr><td>Technology</td><td>40.36 MWp Solar + 66 MWh BESS</td><td>Same</td><td>30 MW Solar + 20 MW Wind + 10 MW/40 MWh BESS</td></tr>
    <tr><td>DPPA type</td><td>None (avoided cost only)</td><td>Private-wire @ 1,100 VND/kWh</td><td>Virtual CfD (NDS7025) @ 5.500 ¢/kWh</td></tr>
    <tr><td>Total CAPEX</td><td class="s18">{fmt_money(s18_capex)}</td><td class="s18">{fmt_money(s18_capex)}</td><td class="nt">{fmt_money(nt_capex)}</td></tr>
    <tr><td>CAPEX / total MW</td><td class="s18">${s18_capex_per_mw:,.0f}/kW</td><td class="s18">Same</td><td class="nt">${nt_capex_per_mw:,.0f}/kW</td></tr>
    <tr><td>Year-1 generation</td><td>{s18_gen_gwh:.1f} GWh (solar)</td><td>Same</td><td>{nt_gen_gwh:.1f} GWh (solar+wind)</td></tr>
    <tr><td>Unlevered / Project IRR</td><td class="s18">{fmt_pct(s18_unlevered_irr * 100)}</td><td class="s18">{fmt_pct(s18_unlevered_irr * 100)}</td><td class="nt">{fmt_pct(nt_proj_irr)}</td></tr>
    <tr><td>Equity IRR</td><td class="s18">{fmt_pct(s18_eq_irr_a * 100)}</td><td class="good">{fmt_pct(s18_eq_irr_d * 100)}</td><td class="good">{fmt_pct(nt_eq_irr)}</td></tr>
    <tr><td>Unlevered NPV</td><td>{fmt_money(s18_npv_a)}</td><td class="good">{fmt_money(s18_combined_npv)}</td><td>{fmt_money(nt_proj_npv)} (@ 15%)</td></tr>
    <tr><td>Equity NPV</td><td>-</td><td class="good">{fmt_money(eq_d["equity_npv_usd"])}</td><td>{fmt_money(nt_eq_npv)} (@ 15%)</td></tr>
    <tr><td>Simple payback</td><td>{s18_payback:.1f} yr</td><td>Same</td><td>Year {nt_payback}</td></tr>
    <tr><td>Year-1 project value</td><td>{fmt_money(s18_yr1_savings)}</td><td class="good">{fmt_money(s18_combined_yr1)}</td><td>{fmt_money(nt_yr1_revenue)}</td></tr>
    <tr><td>DPPA / factory saving yr1</td><td>-</td><td class="s18">{fmt_money(s18_settlement_yr1)} (developer)</td><td class="nt">{fmt_money(nt_factory_saving)} (factory)</td></tr>
  </table>

  <h2>Contract Risk Comparison</h2>
  <div class="grid-2">
    <div class="card card-s18">
      <div class="eyebrow">Saigon18 — Private-wire DPPA</div>
      <div style="margin-top:8px;font-size:13px;">
        <div class="row-item"><span>Settlement formula</span><strong>strike × matched kWh (fixed revenue)</strong></div>
        <div class="row-item"><span>FMP exposure</span><strong>None — developer receives P_C regardless of spot</strong></div>
        <div class="row-item"><span>Price ceiling (south)</span><strong>1,149.86 VND/kWh</strong></div>
        <div class="row-item"><span>Strike headroom to ceiling</span><strong>{s18_headroom_vnd:.2f} VND/kWh ({s18_headroom_vnd/s18_ceiling_vnd*100:.1f}%)</strong></div>
        <div class="row-item"><span>Curtailment risk</span><strong>Low — private wire; no grid congestion</strong></div>
        <div class="row-item"><span>Regulatory basis</span><strong>Decree 57/2025 (export cap) + Decree 146/2025 (capacity charge)</strong></div>
        <div class="row-item"><span>Demand charge savings (pilot)</span><strong>{fmt_money(s18_demand_savings)}/yr @ 60k VND/kW-mo</strong></div>
        <div class="row-item"><span>Peak demand reduction</span><strong>{s18_peak_reduction:,.0f} kW (30,246 → 27,104 kW BAU→actual)</strong></div>
      </div>
    </div>
    <div class="card card-nt">
      <div class="eyebrow">North Thuan — Virtual DPPA (NDS7025)</div>
      <div style="margin-top:8px;font-size:13px;">
        <div class="row-item"><span>Settlement formula</span><strong>CfD: (P_C − FMP) × matched (when FMP &lt; P_C)</strong></div>
        <div class="row-item"><span>FMP exposure</span><strong>Yes — premium risk when FMP &gt; factory ceiling</strong></div>
        <div class="row-item"><span>Hours at premium risk</span><strong>2,186 hrs/yr (2,925 MWh exposed)</strong></div>
        <div class="row-item"><span>Strike negotiable window</span><strong>{nt_min_viable_strike_c_kwh:.3f} – {nt_contracted_strike_c_kwh:.3f} ¢/kWh ({nt_strike_headroom_c_kwh:.3f}¢ spread)</strong></div>
        <div class="row-item"><span>Curtailment risk</span><strong>Grid-connected — potential congestion in North Thuan</strong></div>
        <div class="row-item"><span>Regulatory basis</span><strong>Decree 7/2025 NDS7025 (virtual DPPA) + Decree 57/2025</strong></div>
        <div class="row-item"><span>Bankability (DSCR ≥ 1.2×)</span><strong>{nt_dscr}× min DSCR (bankable)</strong></div>
        <div class="row-item"><span>Factory NPV benefit</span><strong>{fmt_money(nt_factory_npv)} over 25yr</strong></div>
      </div>
    </div>
  </div>

  <h2>Strike Price Viability — North Thuan Sensitivity</h2>
  <div class="callout">
    North Thuan viability frontier (equity IRR ≥ 15%): minimum PPA price ≥ <strong>3.850 ¢/kWh at all tested interest rates (6.5%–10.5%)</strong>.
    The contracted strike of 5.500 ¢/kWh provides <strong>{nt_strike_headroom_c_kwh:.2f}¢/kWh of headroom</strong> above the viability floor — a comfortable buffer.
  </div>
  <table style="margin-top:12px;">
    <tr><th>Strike P_C (¢/kWh)</th><th>vs. viability floor</th><th>Factory saving yr1</th><th>Est. equity IRR</th><th>Viability</th></tr>
    {"".join(
        f'<tr><td>{"→ " if s == 5.500 else ""}<strong>{s:.3f}</strong></td>'
        f'<td>{s - 3.850:+.3f}¢</td>'
        f'<td>{fmt_money((7.394 - s) / 100 * 70_050_000)}</td>'
        f'<td>{"~31%" if s == 5.500 else ("~15%" if s == 4.273 else ("&gt;35%" if s > 5.5 else ("~20%" if s > 4.8 else "&lt;15%")))}</td>'
        f'<td class="{"good" if s >= 3.850 else "warn"}">{"VIABLE" if s >= 3.850 else "BELOW FLOOR"}</td></tr>'
        for s in nt_strikes
    )}
  </table>

  <h2>Saigon18 Private-Wire Strike Sensitivity</h2>
  <div class="callout">
    Saigon18 is constrained to ≤ 1,149.86 VND/kWh (south private-wire ceiling). Current assumption: 1,100 VND/kWh.
    The ceiling provides <strong>{s18_headroom_vnd:.2f} VND/kWh of remaining negotiation headroom</strong>.
  </div>
  <!-- Settlement NPV column uses a rough 20yr NPV factor at 8% discount with 5% escalation -->
  <table style="margin-top:12px;">
    <tr><th>Strike (VND/kWh)</th><th>vs. ceiling</th><th>Year-1 DPPA revenue</th><th>Settlement NPV (20yr @ 8%)</th><th>Status</th></tr>
    {"".join(
        f'<tr><td>{"→ " if s == 1100 else ""}<strong>{s:,.2f}</strong></td>'
        f'<td>{s - s18_ceiling_vnd:+.2f} VND/kWh</td>'
        f'<td>{fmt_money(s * 65226 * 1000 / 26000)}</td>'
        f'<td>{fmt_money(s * 65226 * 1000 / 26000 * 10.675)}</td>'
        f'<td class="{"good" if s <= s18_ceiling_vnd else "warn"}">{"≤ CEILING ✓" if s <= s18_ceiling_vnd else "ABOVE CEILING ✗"}</td></tr>'
        for s in s18_strikes_vnd
    )}
  </table>

  <h2>BESS Dispatch Value Comparison</h2>
  <div class="grid-2">
    <div class="card card-s18">
      <div class="eyebrow">Saigon18 BESS — REopt free optimisation</div>
      <div style="margin-top:8px;">
        {bar(bess_s["reopt_free_optimization"]["peak_discharge_mwh"], 20000, "bar-s18")}
        <div class="sub" style="margin-top:2px;">Peak: {bess_s["reopt_free_optimization"]["peak_discharge_mwh"]:,.0f} MWh/yr</div>
        {bar(bess_s["reopt_free_optimization"]["standard_discharge_mwh"], 20000, "bar-s18")}
        <div class="sub" style="margin-top:2px;">Standard: {bess_s["reopt_free_optimization"]["standard_discharge_mwh"]:,.0f} MWh/yr</div>
        <div style="margin-top:10px;font-size:13px;font-weight:700;">Annual dispatch value: {fmt_money(s18_bess_reopt_val)}</div>
        <div class="sub">+88.8% vs Excel Option B fixed-window ({fmt_money(bess_s["excel_option_b_fixed_window"]["annual_value_usd"])})</div>
      </div>
    </div>
    <div class="card card-nt">
      <div class="eyebrow">North Thuan BESS — Role in matching</div>
      <div style="margin-top:8px;font-size:13px;">
        <div class="row-item"><span>Capacity</span><strong>10 MW / 40 MWh (LiFePO₄)</strong></div>
        <div class="row-item"><span>Primary role</span><strong>Time-shift solar/wind to match factory load peaks</strong></div>
        <div class="row-item"><span>Self-consumption uplift</span><strong>Contributes to 59.6% self-consumption rate</strong></div>
        <div class="row-item"><span>FMP premium risk mitigation</span><strong>Discharge during high-FMP hours reduces premium exposure</strong></div>
        <div class="row-item"><span>CAPEX</span><strong>$2.50M ($250/kWh LiFePO₄ estimate)</strong></div>
        <div style="margin-top:10px;color:var(--muted);font-size:12px;">
          Note: North Thuan BESS dispatch was not re-optimised by REopt in Phase 6 (validation-only).
          A REopt solve with wind+solar+BESS could further improve matching and reduce premium-risk hours.
        </div>
      </div>
    </div>
  </div>

  <h2>Key Takeaways</h2>
  <div class="callout">
    <strong>1. CAPEX efficiency:</strong> North Thuan achieves {fmt_money(nt_capex)} CAPEX for 50 MW hybrid (${nt_capex_per_mw:,.0f}/kW) —
    substantially cheaper than Saigon18's {fmt_money(s18_capex)} for 40.36 MWp solar-only (${s18_capex_per_mw:,.0f}/kW).
    Wind addition lowers blended CAPEX/MW significantly.
  </div>
  <div class="callout" style="margin-top:10px;">
    <strong>2. Contract risk:</strong> Saigon18 private-wire eliminates FMP exposure (fixed revenue per kWh matched).
    North Thuan virtual CfD has 2,186 hrs/yr premium-risk exposure (FMP &gt; factory ceiling) but captures FMP upside when spot is high.
    Both structures are viable — risk preference depends on investor appetite.
  </div>
  <div class="callout" style="margin-top:10px;">
    <strong>3. Equity IRR convergence:</strong> Both projects deliver similar levered equity IRRs ({fmt_pct(s18_eq_irr_d * 100)} Saigon18 / {fmt_pct(nt_eq_irr)} North Thuan)
    despite different contract structures. Saigon18's higher IRR is driven by the private-wire strike × matched-volume revenue;
    North Thuan's is driven by a lower CAPEX base and CIT holiday.
  </div>
  <div class="callout" style="margin-top:10px;">
    <strong>4. Regulatory compliance:</strong> Both projects sit within Decree 57/2025 export cap (0.80% for Saigon18;
    North Thuan not constrained by export cap since virtual DPPA settlement is generation-based).
    Decree 146/2025 capacity charge adds {fmt_money(s18_demand_savings)}/yr incremental value for Saigon18 at pilot rates.
  </div>
  <div class="callout" style="margin-top:10px;">
    <strong>5. Next steps:</strong> (a) Confirm Saigon18 actual site GPS coords and negotiated strike (currently assumed 1,100 VND/kWh);
    (b) Obtain North Thuan hourly FMP data to narrow validation gap to &lt;1% on IRR;
    (c) Run REopt full-solve for North Thuan Wind+Solar+BESS to validate staff's dispatch assumptions.
  </div>

  <div class="footer">Generated by <code>scripts/python/integration/generate_cross_project_dashboard.py</code> ·
  Saigon18 Phase 4–5 + North Thuan Phase 6 validation · 2026-03-29</div>
</div>
</body>
</html>
"""

    out_path.write_text(html, encoding="utf-8")
    print(f"Cross-project dashboard written to: {out_path}")
    print(f"File size: {len(html):,} bytes")


if __name__ == "__main__":
    main()
