"""Generate an HTML comparison report from the TOU financial delta CSV.

Reads the CSV produced by tou_financial_delta.py and creates a self-contained
HTML page with per-case-study tables and a bar chart showing percentage changes
in annual energy cost across regimes.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

REGIME_NEW = "decision_963_2026_current"
REGIME_LEGACY = "decision_14_2025_legacy"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TOU Regime Comparison Report &mdash; Decision 963 vs Decision 14</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {{ --bg: #f8f9fa; --card: #fff; --border: #dee2e6; --text: #212529; --accent: #0066cc; --accent2: #28a745; --warn: #dc3545; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; }}
h1 {{ color: var(--accent); font-size: 1.5rem; margin-bottom: 0.25rem; }}
h2 {{ color: var(--accent); font-size: 1.15rem; margin: 2rem 0 0.75rem; border-bottom: 2px solid var(--border); padding-bottom: 0.25rem; }}
.subtitle {{ color: #6c757d; font-size: 0.85rem; margin-bottom: 1.5rem; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin: 1rem 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 0.5rem 0; font-size: 0.85rem; }}
th, td {{ text-align: right; padding: 0.4rem 0.6rem; border-bottom: 1px solid var(--border); }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ background: #e9ecef; font-weight: 600; }}
.positive {{ color: var(--warn); }}
.negative {{ color: var(--accent2); }}
.chart-container {{ max-width: 100%; height: 350px; }}
.assumptions {{ font-size: 0.85rem; color: #495057; }}
.assumptions li {{ margin: 0.25rem 0; }}
</style>
</head>
<body>

<h1>TOU Regime Comparison Report</h1>
<p class="subtitle">Decision 963/QD-BCT (current) vs Decision 14/2025 (legacy) &mdash; {date}</p>

<h2>Executive Summary</h2>
<div class="card">
<p>This report compares project economics under <strong>Decision 963</strong> (evening-only peak 17:30&ndash;22:30, effective 2026-04-22) versus <strong>Decision 14/2025</strong> (split peak 09:30&ndash;11:30 + 17:00&ndash;20:00, legacy). The peak-window shift removes the morning peak and extends the evening peak, fundamentally changing solar and BESS value.</p>
<p><strong>{summary_text}</strong></p>
</div>

<h2>Annual Energy Cost Comparison</h2>
<div class="card">
<div class="chart-container"><canvas id="costChart"></canvas></div>
</div>

<h2>Per-Scenario Detail Tables</h2>
{detail_tables}

<h2>Assumptions &amp; Limitations</h2>
<div class="card assumptions">
<ul>
<li><strong>ASM-001:</strong> Decision 14 rate multipliers (peak 1.57, standard 0.86, off-peak 0.56 for production/medium-voltage) are assumed to carry forward unchanged under Decision 963 windows. MOIT has not yet published replacement multipliers.</li>
<li><strong>ASM-002:</strong> Hourly discretization maps the 17:30 boundary to hour [17], causing ~2.8% peak-energy overcount at industrial loads.</li>
<li>The comparison is purely tariff-window-driven; system sizing may differ if the optimizer can re-size PV or BESS capacity.</li>
<li>Results labeled "no_results" indicate the Julia REopt solve has not been run or did not complete.</li>
</ul>
</div>

<script>
Chart.defaults.devicePixelRatio = 1;
Chart.defaults.animation = false;
Chart.defaults.maintainAspectRatio = false;

const ctx = document.getElementById('costChart').getContext('2d');
new Chart(ctx, {{
  type: 'bar',
  data: {{
    labels: {labels},
    datasets: [
      {{
        label: 'Decision 14 (legacy)',
        data: {legacy_data},
        backgroundColor: 'rgba(40, 167, 69, 0.7)',
        borderColor: 'rgba(40, 167, 69, 1)',
        borderWidth: 1
      }},
      {{
        label: 'Decision 963 (current)',
        data: {new_data},
        backgroundColor: 'rgba(0, 102, 204, 0.7)',
        borderColor: 'rgba(0, 102, 204, 1)',
        borderWidth: 1
      }}
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{
      title: {{ display: true, text: 'Annual Energy Cost (USD)' }},
      tooltip: {{ mode: 'index', intersect: false }}
    }},
    scales: {{
      y: {{ beginAtZero: false }}
    }}
  }}
}});
</script>

</body>
</html>"""


def fmt(val, precision=2):
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:,.{precision}f}"
    return str(val)


def fmt_pct(val):
    if val is None:
        return "N/A"
    return f"{val:+.1%}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML TOU comparison report from CSV.")
    parser.add_argument("--csv", default=str(REPO_ROOT / "artifacts" / "reports" / "tou_comparison" / "financial_delta_summary.csv"),
                        help="Path to financial delta CSV")
    parser.add_argument("--output", default=str(REPO_ROOT / "artifacts" / "reports" / "tou_comparison" / "tou_comparison_report.html"),
                        help="Output HTML path")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    output_path = Path(args.output)

    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(f)]

    labels = []
    legacy_costs = []
    new_costs = []
    summary_parts = []

    for row in rows:
        slug = row.get("scenario", "unknown")
        labels.append(f'"{slug}"')

        new_cost = row.get("annual_energy_cost_usd_new")
        legacy_cost = row.get("annual_energy_cost_usd_legacy")
        pct_change = row.get("annual_energy_cost_pct_change")

        try:
            legacy_costs.append(float(legacy_cost) if legacy_cost and legacy_cost != "None" else 0)
        except (ValueError, TypeError):
            legacy_costs.append(0)
        try:
            new_costs.append(float(new_cost) if new_cost and new_cost != "None" else 0)
        except (ValueError, TypeError):
            new_costs.append(0)

        if pct_change and pct_change != "None":
            try:
                pct = float(pct_change)
                direction = "increase" if pct > 0 else "decrease" if pct < 0 else "no change"
                summary_parts.append(f"{slug}: {direction} of {abs(pct)*100:.1f}%")
            except (ValueError, TypeError):
                summary_parts.append(f"{slug}: insufficient data")

    summary_text = "; ".join(summary_parts) if summary_parts else "Insufficient data for summary."

    detail_tables = ""
    for row in rows:
        slug = row.get("scenario", "unknown")
        detail_tables += f'<h3>{slug}</h3>\n<table>\n<thead><tr>'
        detail_tables += '<th>Metric</th><th>Decision 14 (Legacy)</th><th>Decision 963 (Current)</th><th>Delta</th><th>% Change</th></tr></thead><tbody>'

        metric_rows = [
            ("annual_energy_cost_usd", "Annual Energy Cost ($)"),
            ("lifecycle_cost_usd", "Lifecycle Cost ($)"),
            ("pv_capacity_kw", "PV Capacity (kW)"),
            ("annual_pv_production_kwh", "Annual PV Production (kWh)"),
            ("annual_grid_purchases_kwh", "Annual Grid Purchases (kWh)"),
            ("npv_usd", "NPV ($)"),
            ("simple_payback_years", "Simple Payback (years)"),
        ]

        for csv_key, display_name in metric_rows:
            new_v = row.get(f"{csv_key}_new")
            legacy_v = row.get(f"{csv_key}_legacy")
            delta_v = row.get(f"{csv_key}_delta")
            pct_v = row.get(f"{csv_key}_pct_change")

            delta_float = None
            try:
                delta_float = float(delta_v) if delta_v and delta_v != "None" else None
            except (ValueError, TypeError):
                pass

            pct_float = None
            try:
                pct_float = float(pct_v) if pct_v and pct_v != "None" else None
            except (ValueError, TypeError):
                pass

            legacy_float = None
            try:
                legacy_float = float(legacy_v) if legacy_v and legacy_v != "None" else None
            except (ValueError, TypeError):
                pass

            new_float = None
            try:
                new_float = float(new_v) if new_v and new_v != "None" else None
            except (ValueError, TypeError):
                pass

            css_class = ""
            if delta_float is not None:
                css_class = ' class="positive"' if delta_float > 0 else (' class="negative"' if delta_float < 0 else "")

            detail_tables += f'<tr><td>{display_name}</td><td>{fmt(legacy_float)}</td><td>{fmt(new_float)}</td><td{css_class}>{fmt(delta_float)}</td><td>{fmt_pct(pct_float)}</td></tr>'

        detail_tables += '</tbody></table>\n'

    html = HTML_TEMPLATE.replace("{date}", str(csv_path.stat().st_mtime)[:10] if csv_path.exists() else "N/A")
    html = html.replace("{summary_text}", summary_text)
    html = html.replace("{labels}", "[" + ", ".join(labels) + "]")
    html = html.replace("{legacy_data}", str(legacy_costs))
    html = html.replace("{new_data}", str(new_costs))
    html = html.replace("{detail_tables}", detail_tables)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()