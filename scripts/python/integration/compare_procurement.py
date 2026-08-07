"""CLI entrypoint for procurement comparison (GAP-02 PHASE-04).

Usage:
    python scripts/python/integration/compare_procurement.py \
        --factory data/interim/saigon18/2026-03-20_saigon18_extracted_inputs.json \
        --output artifacts/reports/procurement_comparison.json \
        --report reports/procurement_comparison.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.procurement import (
    ProjectConfig,
    compare_procurement_options,
    evaluate_offsite,
    evaluate_onsite,
    load_factory_loads,
    load_tariff_rates,
)


def _synthetic_fmp_8760(base: float = 1.5) -> list[float]:
    return [base] * 8760


def _saigon18_generation_profile() -> list[float]:
    """Synthetic 8760 generation for saigon18 40 MWp solar + 66 MWh BESS."""
    cf = 0.203
    hourly = 40_000.0 * cf
    return [hourly] * 8760


def _ninhsim_generation_profile() -> list[float]:
    """Synthetic 8760 generation for ninhsim-style offsite 54 MW solar+wind."""
    cf = 0.28
    hourly = 54_000.0 * cf
    return [hourly] * 8760


def main():
    parser = argparse.ArgumentParser(description="Compare onsite vs offsite procurement options")
    parser.add_argument("--factory", type=str, required=True, help="Path to factory load JSON")
    parser.add_argument("--output", type=str, default="artifacts/reports/procurement_comparison.json")
    parser.add_argument("--report", type=str, default="reports/procurement_comparison.html")
    parser.add_argument("--onsite-strike", type=float, default=1012.0, help="Onsite strike VND/kWh")
    parser.add_argument("--offsite-strike", type=float, default=1800.0, help="Offsite strike VND/kWh")
    parser.add_argument("--fmp-base", type=float, default=1.5, help="FMP base VND/kWh")
    args = parser.parse_args()

    loads = load_factory_loads(args.factory)
    tariff = load_tariff_rates(REPO_ROOT / "data" / "vietnam")
    fmp = _synthetic_fmp_8760(args.fmp_base)

    onsite_project = ProjectConfig(
        project_id="saigon18_onsite",
        name="Saigon18 Onsite Solar+BESS (40 MWp + 66 MWh)",
        technology="solar_bess",
        capacity_mw=40.0,
        bess_mw=20.0,
        bess_mwh=66.0,
        grid_connection="onsite_private_wire",
        generation_profile_kw=_saigon18_generation_profile(),
        indicative_strike_vnd_kwh=args.onsite_strike,
    )

    offsite_project = ProjectConfig(
        project_id="ninhsim_offsite",
        name="Ninhsim Offsite Solar+Wind CfD (54 MW)",
        technology="solar_wind",
        capacity_mw=54.0,
        grid_connection="offsite_grid_connected",
        generation_profile_kw=_ninhsim_generation_profile(),
        indicative_strike_vnd_kwh=args.offsite_strike,
        dppa_structure="virtual_cfd",
    )

    print(f"Evaluating onsite: {onsite_project.name}")
    onsite = evaluate_onsite(loads, onsite_project, tariff)
    print(f"  Buyer cost: {onsite.settlement.annual_summary['buyer_cost_vnd']:,.0f} VND")
    print(f"  Buyer savings vs EVN: {onsite.buyer_savings_vs_evn_vnd:,.0f} VND")
    print(f"  RE penetration: {onsite.re_penetration_pct:.1f}%")

    print(f"\nEvaluating offsite: {offsite_project.name}")
    offsite = evaluate_offsite(loads, offsite_project, tariff, fmp)
    print(f"  Buyer cost: {offsite.settlement.annual_summary['buyer_cost_vnd']:,.0f} VND")
    print(f"  Buyer savings vs EVN: {offsite.buyer_savings_vs_evn_vnd:,.0f} VND")
    print(f"  RE penetration: {offsite.re_penetration_pct:.1f}%")
    print(f"  FMP risk score: {offsite.fmp_risk_score:.0f}/100")

    comparison = compare_procurement_options(
        onsite, offsite,
        {"factory_id": Path(args.factory).stem, "factory_path": args.factory},
    )

    print(f"\nRecommendation: {comparison.recommendation}")
    print(f"  Reason: {comparison.recommendation_reason}")
    if comparison.regulatory_flags:
        print(f"  Regulatory flags: {', '.join(comparison.regulatory_flags)}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(comparison.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nComparison artifact: {output_path}")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _generate_report(comparison, report_path)
    print(f"HTML report: {report_path}")


def _generate_report(comparison, report_path: Path):
    """Generate a simple HTML report with the comparison results."""
    onsite = comparison.onsite
    offsite = comparison.offsite
    delta = comparison.delta

    onsite_cost = onsite.settlement.annual_summary["buyer_cost_vnd"] if onsite else 0
    offsite_cost = offsite.settlement.annual_summary["buyer_cost_vnd"] if offsite else 0
    onsite_savings = onsite.buyer_savings_vs_evn_vnd if onsite else 0
    offsite_savings = offsite.buyer_savings_vs_evn_vnd if offsite else 0
    onsite_rev = onsite.settlement.annual_summary["developer_revenue_vnd"] if onsite else 0
    offsite_rev = offsite.settlement.annual_summary["developer_revenue_vnd"] if offsite else 0

    cost_delta = delta.get("buyer_cost_delta_vnd", 0)
    savings_delta = delta.get("buyer_savings_delta_vnd", 0)

    onsite_matched = f"{onsite.settlement.annual_summary['matched_mwh']:.1f}" if onsite else "N/A"
    offsite_matched = f"{offsite.settlement.annual_summary['matched_mwh']:.1f}" if offsite else "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Procurement Comparison — {comparison.factory_id}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #0d0d0d; color: #e9f6ff; margin: 0; padding: 32px; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ color: #00f5ff; }}
  h2 {{ color: #39ff14; margin-top: 32px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  th, td {{ padding: 12px; border: 1px solid #333; text-align: left; }}
  th {{ color: #39ff14; }}
  .rec {{ background: rgba(0, 245, 255, 0.1); border: 1px solid #00f5ff; border-radius: 12px; padding: 20px; margin: 20px 0; }}
  .flag {{ color: #ff6b6b; }}
  canvas {{ height: 320px !important; }}
</style>
</head>
<body>
<div class="container">
<h1>Procurement Comparison: {comparison.factory_id}</h1>
<p>Onsite (private-wire PPA) vs Offsite (virtual CfD DPPA)</p>

<div class="rec">
  <h2>Recommendation: {comparison.recommendation.upper()}</h2>
  <p>{comparison.recommendation_reason}</p>
</div>

<h2>Side-by-Side Economics</h2>
<table>
  <tr><th>Metric</th><th>Onsite</th><th>Offsite</th><th>Delta</th></tr>
  <tr><td>Buyer Cost (VND/yr)</td><td>{onsite_cost:,.0f}</td><td>{offsite_cost:,.0f}</td><td>{cost_delta:,.0f}</td></tr>
  <tr><td>Buyer Savings vs EVN (VND)</td><td>{onsite_savings:,.0f}</td><td>{offsite_savings:,.0f}</td><td>{savings_delta:,.0f}</td></tr>
  <tr><td>Developer Revenue (VND/yr)</td><td>{onsite_rev:,.0f}</td><td>{offsite_rev:,.0f}</td><td>{onsite_rev - offsite_rev:,.0f}</td></tr>
  <tr><td>RE Penetration (%)</td><td>{onsite.re_penetration_pct if onsite else 'N/A'}</td><td>{offsite.re_penetration_pct if offsite else 'N/A'}</td><td></td></tr>
  <tr><td>Matched Energy (MWh)</td><td>{onsite_matched}</td><td>{offsite_matched}</td><td></td></tr>
</table>

<h2>Visual Comparison</h2>
<canvas id="costChart"></canvas>

<h2>Regulatory Flags</h2>
"""
    if comparison.regulatory_flags:
        html += "<ul>"
        for flag in comparison.regulatory_flags:
            html += f'<li class="flag">{flag}</li>'
        html += "</ul>"
    else:
        html += "<p>No regulatory flags raised.</p>"

    html += f"""
</div>
<script>
  Chart.defaults.animation = false;
  new Chart(document.getElementById('costChart'), {{
    type: 'bar',
    data: {{
      labels: ['Buyer Cost (VND)', 'Buyer Savings (VND)', 'Developer Revenue (VND)'],
      datasets: [
        {{ label: 'Onsite', data: [{onsite_cost}, {onsite_savings}, {onsite_rev}], backgroundColor: 'rgba(0, 245, 255, 0.6)' }},
        {{ label: 'Offsite', data: [{offsite_cost}, {offsite_savings}, {offsite_rev}], backgroundColor: 'rgba(57, 255, 20, 0.6)' }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{ legend: {{ display: true }} }},
      scales: {{ y: {{ beginAtZero: true }} }}
    }}
  }});
</script>
</body>
</html>"""
    report_path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
