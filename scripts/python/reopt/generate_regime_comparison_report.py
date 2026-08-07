"""Generate a self-contained HTML regime-comparison report (GAP-05, PHASE-03).

Builds a client-facing "instant regime toggle" report with Chart.js visualizations:
factory load profile, color-coded TOU windows per regime, annual bill comparison,
solar avoided-cost and BESS arbitrage impact, and a regulatory timeline.

Example:
    python scripts/python/reopt/generate_regime_comparison_report.py \
        --factory scenarios/case_studies/saigon18/2026-03-20_scenario-a_fixed-sizing_evntou.json \
        --regimes decision_963_2026_current,decision_14_2025_legacy,decree146_two_part_trial_2026 \
        --solar-profile-synthetic --bess-power 1000 \
        --output reports/2026-05-30-saigon18-regime-comparison.html
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.ingestion.loader import ingest_factory_load
from reopt_pysam_vn.reopt.preprocess import (
    load_vietnam_data,
    resolve_vietnam_regime,
)
from reopt_pysam_vn.reopt.regime_impact import (
    OFFPEAK,
    PEAK,
    STANDARD,
    build_regime_comparison,
    compute_multi_regime_impact,
)

# Regulatory timeline for the report footer narrative (effective dates from the registry).
REGULATORY_TIMELINE = [
    ("2025-05-29", "Decision 14/2025", "Split TOU peak: morning 09:30-11:30 + evening 17:00-20:00."),
    ("2026-04-22", "Decision 963/QD-BCT", "Single evening peak 17:30-22:30 becomes active default."),
    ("2026-01-01", "Decree 57/2025 (draft)", "Rooftop surplus-export cap sensitivity (20% -> 50%)."),
    ("2026-01-01", "Decree 146/2025 (trial)", "Two-part tariff trial: adds a monthly demand charge."),
]


def _load_series(path):
    return ingest_factory_load(path).loads_kw


def _weekday_classes(vn, regime_id):
    """Return a 24-element weekday TOU class list for a regime."""
    schedule = resolve_vietnam_regime(vn, regime_id)["tariff"]["tou_schedule"]["weekday"]
    classes = [STANDARD] * 24
    for h in schedule.get("peak_hours", []):
        classes[int(h)] = PEAK
    for h in schedule.get("offpeak_hours", []):
        classes[int(h)] = OFFPEAK
    for h in schedule.get("standard_hours", []):
        classes[int(h)] = STANDARD
    return classes


def _avg_hourly_profile(loads_kw):
    """Average load by hour-of-day across the year (24 values)."""
    sums = [0.0] * 24
    counts = [0] * 24
    for h, v in enumerate(loads_kw):
        sums[h % 24] += v
        counts[h % 24] += 1
    return [round(sums[i] / counts[i], 1) if counts[i] else 0.0 for i in range(24)]


def _synthetic_daytime_pv(peak_kw):
    """A simple daytime PV profile (07:00-16:59) for illustrative avoided-cost value."""
    pv = []
    for h in range(8760):
        hour = h % 24
        pv.append(float(peak_kw) if 7 <= hour <= 16 else 0.0)
    return pv


def build_report_html(data):
    """Render the report HTML from the assembled ``data`` dict."""
    payload = json.dumps(data)
    title = data["factory_name"]
    generated = data["generated_at"]
    timeline_rows = "".join(
        f"<tr><td>{d}</td><td><strong>{name}</strong></td><td>{desc}</td></tr>"
        for d, name, desc in REGULATORY_TIMELINE
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Regime Comparison :: {title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  :root {{ --bg:#0b1118; --panel:#121b25; --line:#1f2d3a; --text:#e8f1f8; --muted:#8aa0b2; --blue:#22d3ee; --green:#34d399; --amber:#fbbf24; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:linear-gradient(180deg,#0b1118,#0e1620); color:var(--text); font-family:"Segoe UI",Helvetica,Arial,sans-serif; line-height:1.6; }}
  .shell {{ width:min(1140px, calc(100vw - 32px)); margin:0 auto; padding:28px 0 64px; }}
  .hero {{ padding:26px; border:1px solid var(--line); border-radius:18px; background:var(--panel); margin-bottom:20px; }}
  h1 {{ margin:0 0 6px; font-size:clamp(1.6rem,3vw,2.4rem); }}
  .sub {{ color:var(--muted); margin:0; }}
  .grid2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }}
  .card {{ padding:20px; border:1px solid var(--line); border-radius:16px; background:var(--panel); margin-top:16px; }}
  .card h2 {{ margin:0 0 14px; font-size:1.15rem; }}
  .chart-frame {{ position:relative; height:300px; }}
  canvas {{ max-height:300px !important; }}
  table {{ width:100%; border-collapse:collapse; }}
  th,td {{ padding:10px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:0.92rem; }}
  th {{ color:var(--green); text-transform:uppercase; font-size:0.72rem; letter-spacing:0.1em; }}
  .tou-strip {{ display:grid; grid-template-columns:repeat(24,1fr); gap:2px; margin:6px 0 14px; }}
  .tou-cell {{ height:26px; border-radius:3px; font-size:0.6rem; display:flex; align-items:center; justify-content:center; color:#06121a; font-weight:700; }}
  .tou-peak {{ background:var(--amber); }} .tou-standard {{ background:#3b82f6; color:#eef; }} .tou-offpeak {{ background:var(--green); }}
  .tou-label {{ color:var(--muted); font-size:0.8rem; margin:4px 0; }}
  .legend {{ display:flex; gap:14px; flex-wrap:wrap; color:var(--muted); font-size:0.8rem; margin-top:6px; }}
  .swatch {{ display:inline-block; width:12px; height:12px; border-radius:3px; vertical-align:middle; margin-right:5px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:8px; }}
  .kpi {{ padding:14px; border:1px solid var(--line); border-radius:12px; background:#0e1822; }}
  .kpi .l {{ color:var(--muted); font-size:0.72rem; text-transform:uppercase; letter-spacing:0.08em; }}
  .kpi .v {{ font-size:1.25rem; font-weight:700; color:var(--blue); margin-top:6px; }}
  @media (max-width:860px) {{ .grid2 {{ grid-template-columns:1fr; }} .kpis {{ grid-template-columns:1fr; }} }}
  @media print {{ body {{ background:#fff; color:#111; }} .card,.hero {{ border-color:#ccc; }} }}
</style>
</head>
<body>
<div class="shell">
  <div class="hero">
    <h1>Regulatory Regime Comparison</h1>
    <p class="sub">{title} &middot; generated {generated} &middot; Python-only tariff math, no REopt solve</p>
    <div class="kpis" id="kpis"></div>
  </div>

  <div class="card">
    <h2>Annual EVN Bill by Regime</h2>
    <div class="chart-frame"><canvas id="billChart"></canvas></div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>Factory Load Profile (avg by hour)</h2>
      <div class="chart-frame"><canvas id="loadChart"></canvas></div>
    </div>
    <div class="card">
      <h2>TOU Windows (weekday)</h2>
      <div id="touWindows"></div>
      <div class="legend">
        <span><span class="swatch tou-peak"></span>Peak</span>
        <span><span class="swatch tou-standard"></span>Standard</span>
        <span><span class="swatch tou-offpeak"></span>Off-peak</span>
      </div>
    </div>
  </div>

  <div class="grid2" id="reTechBlock">
    <div class="card">
      <h2>Solar Avoided-Cost Value</h2>
      <div class="chart-frame"><canvas id="solarChart"></canvas></div>
    </div>
    <div class="card">
      <h2>BESS Arbitrage (theoretical max)</h2>
      <div class="chart-frame"><canvas id="bessChart"></canvas></div>
    </div>
  </div>

  <div class="card">
    <h2>Regulatory Timeline</h2>
    <table>
      <thead><tr><th>Effective</th><th>Instrument</th><th>What changed</th></tr></thead>
      <tbody>{timeline_rows}</tbody>
    </table>
  </div>
</div>

<script>
const DATA = {payload};
const fmtB = (v) => (v/1e9).toFixed(2) + ' B VND';
if (window.Chart) {{
  Chart.defaults.animation = false; Chart.defaults.maintainAspectRatio = false; Chart.defaults.responsive = true;
  Chart.defaults.color = '#8aa0b2';
  const grid = {{ color:'rgba(255,255,255,0.06)' }};
  const palette = ['#22d3ee','#34d399','#fbbf24','#f472b6','#a78bfa'];

  // KPIs
  const kpiEl = document.getElementById('kpis');
  const base = DATA.regimes[0];
  let kpiHtml = `<div class="kpi"><div class="l">Baseline (${{base.name}})</div><div class="v">${{fmtB(base.annual_bill_vnd)}}</div></div>`;
  if (DATA.regimes[1]) {{
    const d = DATA.regimes[1];
    kpiHtml += `<div class="kpi"><div class="l">${{d.name}}</div><div class="v">${{fmtB(d.annual_bill_vnd)}}</div></div>`;
    kpiHtml += `<div class="kpi"><div class="l">Delta (baseline -> ${{d.name}})</div><div class="v">${{(d.delta_pct>=0?'+':'')+d.delta_pct.toFixed(2)}}%</div></div>`;
  }}
  kpiEl.innerHTML = kpiHtml;

  new Chart(document.getElementById('billChart'), {{
    type:'bar',
    data:{{ labels: DATA.regimes.map(r=>r.name), datasets:[{{ label:'Annual bill (VND)', data: DATA.regimes.map(r=>r.annual_bill_vnd), backgroundColor: DATA.regimes.map((_,i)=>palette[i%palette.length]) }}] }},
    options:{{ plugins:{{ legend:{{display:false}} }}, scales:{{ x:{{grid}}, y:{{grid, ticks:{{ callback:(v)=>(v/1e9).toFixed(0)+'B' }}, title:{{display:true,text:'VND'}} }} }} }}
  }});

  new Chart(document.getElementById('loadChart'), {{
    type:'line',
    data:{{ labels:[...Array(24).keys()].map(h=>h+':00'), datasets:[{{ label:'kW (avg)', data: DATA.avg_hourly, borderColor:'#22d3ee', backgroundColor:'rgba(34,211,238,0.15)', fill:true, tension:0.3, pointRadius:0 }}] }},
    options:{{ plugins:{{ legend:{{display:false}} }}, scales:{{ x:{{grid}}, y:{{grid, title:{{display:true,text:'kW'}} }} }} }}
  }});

  // TOU windows colored strips
  const tw = document.getElementById('touWindows');
  DATA.regimes.forEach((r)=>{{
    const lab = document.createElement('div'); lab.className='tou-label'; lab.textContent = r.name; tw.appendChild(lab);
    const strip = document.createElement('div'); strip.className='tou-strip';
    r.weekday_classes.forEach((c,h)=>{{
      const cell = document.createElement('div');
      cell.className = 'tou-cell tou-' + c;
      cell.title = h + ':00 ' + c;
      cell.textContent = h;
      strip.appendChild(cell);
    }});
    tw.appendChild(strip);
  }});

  // Solar + BESS (optional)
  if (DATA.solar) {{
    new Chart(document.getElementById('solarChart'), {{
      type:'bar',
      data:{{ labels:[DATA.regimes[0].name, DATA.regimes[1].name], datasets:[{{ label:'Solar avoided cost (VND/yr)', data:[DATA.solar.regime_a_value_vnd, DATA.solar.regime_b_value_vnd], backgroundColor:['#22d3ee','#34d399'] }}] }},
      options:{{ plugins:{{ legend:{{display:false}} }}, scales:{{ x:{{grid}}, y:{{grid, ticks:{{callback:(v)=>(v/1e9).toFixed(1)+'B'}}, title:{{display:true,text:'VND/yr'}} }} }} }}
    }});
  }} else {{ document.getElementById('solarChart').closest('.card').querySelector('.chart-frame').innerHTML = '<p style="color:#8aa0b2">No solar profile supplied.</p>'; }}

  if (DATA.bess) {{
    new Chart(document.getElementById('bessChart'), {{
      type:'bar',
      data:{{ labels:[DATA.regimes[0].name+' ('+DATA.bess.regime_a_cycles_per_day+'/day)', DATA.regimes[1].name+' ('+DATA.bess.regime_b_cycles_per_day+'/day)'], datasets:[{{ label:'Arbitrage (VND/yr)', data:[DATA.bess.regime_a_annual_arbitrage_vnd, DATA.bess.regime_b_annual_arbitrage_vnd], backgroundColor:['#22d3ee','#34d399'] }}] }},
      options:{{ plugins:{{ legend:{{display:false}} }}, scales:{{ x:{{grid}}, y:{{grid, ticks:{{callback:(v)=>(v/1e9).toFixed(1)+'B'}}, title:{{display:true,text:'VND/yr'}} }} }} }}
    }});
  }} else {{ document.getElementById('bessChart').closest('.card').querySelector('.chart-frame').innerHTML = '<p style="color:#8aa0b2">No BESS sizing supplied.</p>'; }}
}}
</script>
</body>
</html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate an HTML regime-comparison report.")
    parser.add_argument("--factory", required=True, help="Factory load file (CSV/XLSX/JSON).")
    parser.add_argument(
        "--regimes",
        default="decision_963_2026_current,decision_14_2025_legacy,decree146_two_part_trial_2026",
        help="Comma-separated regime ids; the first is the baseline.",
    )
    parser.add_argument("--customer-type", default="industrial")
    parser.add_argument("--voltage-level", default="medium_voltage_22kv_to_110kv")
    parser.add_argument("--solar-profile", default=None, help="Optional PV kW profile file.")
    parser.add_argument(
        "--solar-profile-synthetic",
        action="store_true",
        help="Use a synthetic daytime PV profile sized to the factory peak.",
    )
    parser.add_argument("--bess-power", type=float, default=None)
    parser.add_argument("--bess-capacity", type=float, default=None)
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--output", required=True, help="Output HTML path.")
    parser.add_argument("--factory-name", default=None, help="Display name for the report.")
    args = parser.parse_args(argv)

    vn = load_vietnam_data()
    loads = _load_series(args.factory)
    regime_ids = [r.strip() for r in args.regimes.split(",") if r.strip()]
    if len(regime_ids) < 2:
        parser.error("--regimes needs at least two regime ids")

    multi = compute_multi_regime_impact(
        loads, regime_ids, args.customer_type, args.voltage_level, vn=vn, year=args.year
    )

    pv = None
    if args.solar_profile:
        pv = _load_series(args.solar_profile)
    elif args.solar_profile_synthetic:
        pv = _synthetic_daytime_pv(max(loads) * 0.3)

    bess_power = args.bess_power
    bess_capacity = args.bess_capacity
    if bess_power is not None and bess_capacity is None:
        bess_capacity = bess_power * 4.0

    # Solar/BESS computed for the baseline vs the second regime.
    pair = build_regime_comparison(
        loads,
        regime_ids[0],
        regime_ids[1],
        args.customer_type,
        args.voltage_level,
        pv_profile_kw=pv,
        bess_power_kw=bess_power,
        bess_capacity_kwh=bess_capacity,
        vn=vn,
        year=args.year,
    )

    regimes_payload = []
    for imp in multi:
        side = imp.regime_b
        regimes_payload.append({
            "id": side.id,
            "name": side.name,
            "annual_bill_vnd": side.annual_bill_vnd,
            "delta_pct": imp.delta.delta_pct,
            "peak_consumption_mwh": side.peak_consumption_mwh,
            "weekday_classes": _weekday_classes(vn, side.id),
        })

    data = {
        "factory_name": args.factory_name or Path(args.factory).stem,
        "generated_at": datetime.now(timezone.utc).date().isoformat(),
        "regimes": regimes_payload,
        "avg_hourly": _avg_hourly_profile(loads),
        "solar": (
            {
                "regime_a_value_vnd": pair.solar.regime_a_value_vnd,
                "regime_b_value_vnd": pair.solar.regime_b_value_vnd,
                "delta_pct": pair.solar.delta_pct,
            }
            if pair.solar
            else None
        ),
        "bess": (
            {
                "regime_a_cycles_per_day": pair.bess.regime_a_cycles_per_day,
                "regime_b_cycles_per_day": pair.bess.regime_b_cycles_per_day,
                "regime_a_annual_arbitrage_vnd": pair.bess.regime_a_annual_arbitrage_vnd,
                "regime_b_annual_arbitrage_vnd": pair.bess.regime_b_annual_arbitrage_vnd,
            }
            if pair.bess
            else None
        ),
    }

    html = build_report_html(data)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote regime comparison report: {out_path}")
    print(f"  Regimes: {', '.join(regime_ids)}")
    print(f"  Baseline bill: {multi[0].regime_a.annual_bill_vnd:,.0f} VND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
