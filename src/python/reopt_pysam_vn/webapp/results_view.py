"""Results view-model: headline metrics + chart series for the results page,
and a self-contained standalone HTML report for download (PHASE-04).

Only reads the summary dicts ``OnsiteResult``/``OffsiteDppaResult`` already
produce (sizing/dispatch/economics; deal/base_settlement/decision/...) — no
hourly series are available at this layer, so charts are built from those
aggregate numbers (coverage buckets, sizing, settlement), not 8760-hour
dispatch. RISK-04-01 / Grill-Me Q-003: this replaces wrapping
``integration/generate_html_report.py`` (built for the bespoke case modules'
input shape, not the generalized ``analysis`` result contract) with a small
report renderer written for the generalized contract instead.
"""

from __future__ import annotations

import html
from typing import Any

__all__ = ["build_view_model", "render_standalone_report_html"]


def _onsite_metrics(result: dict[str, Any]) -> list[dict[str, Any]]:
    sizing = result.get("sizing", {})
    dispatch = result.get("dispatch", {})
    economics = result.get("economics", {})
    metrics = [
        {"label": "PV size (kW)", "value": sizing.get("pv_kw")},
        {"label": "BESS power (kW)", "value": sizing.get("bess_power_kw")},
        {"label": "BESS energy (kWh)", "value": sizing.get("bess_energy_kwh")},
        {"label": "Delivered fraction", "value": dispatch.get("achieved_delivered_fraction_of_load")},
        {"label": "Meets target", "value": dispatch.get("meets_target")},
        {"label": "NPV", "value": economics.get("npv")},
        {"label": "Lifecycle capital cost", "value": economics.get("lifecycle_capital_costs")},
    ]
    return [m for m in metrics if m["value"] is not None]


def _onsite_charts(result: dict[str, Any]) -> list[dict[str, Any]]:
    dispatch = result.get("dispatch", {})
    if not dispatch:
        return []
    return [
        {
            "title": "Energy coverage (kWh/yr)",
            "type": "bar",
            "data": {
                "labels": ["Renewable delivered", "Exported", "Grid supplied"],
                "values": [
                    dispatch.get("renewable_delivered_kwh", 0.0),
                    dispatch.get("exported_renewable_kwh", 0.0),
                    dispatch.get("grid_supplied_kwh", 0.0),
                ],
            },
        }
    ]


def _offsite_metrics(result: dict[str, Any]) -> list[dict[str, Any]]:
    decision = result.get("decision", {})
    settlement = result.get("base_settlement", {}).get("contracted_slice", {})
    metrics = [
        {"label": "Recommended position", "value": decision.get("recommended_position")},
        {"label": "Buyer savings (VND)", "value": settlement.get("buyer_savings_vnd")},
        {"label": "Buyer cost on matched (VND)", "value": settlement.get("buyer_cost_on_matched_vnd")},
    ]
    return [m for m in metrics if m["value"] is not None]


def _offsite_charts(result: dict[str, Any]) -> list[dict[str, Any]]:
    strike = result.get("strike_sweep", {}).get("strike_band", {})
    if not strike:
        return []
    return [
        {
            "title": "Strike band (VND/kWh)",
            "type": "bar",
            "data": {
                "labels": ["Floor", "Ceiling"],
                "values": [strike.get("floor_vnd_per_kwh", 0.0), strike.get("ceiling_vnd_per_kwh", 0.0)],
            },
        }
    ]


def _single_mode_view(mode: str, result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {"mode": mode, "metrics": [], "charts": []}
    if mode == "onsite":
        return {"mode": mode, "metrics": _onsite_metrics(result), "charts": _onsite_charts(result)}
    return {"mode": mode, "metrics": _offsite_metrics(result), "charts": _offsite_charts(result)}


def build_view_model(mode: str, result: dict[str, Any] | None) -> dict[str, Any]:
    """Build the results-page view model for ``mode`` ("onsite" | "offsite_dppa" | "both")."""
    if mode == "both":
        onsite_result = (result or {}).get("onsite")
        offsite_result = (result or {}).get("offsite_dppa")
        return {
            "mode": "both",
            "onsite": _single_mode_view("onsite", onsite_result),
            "offsite_dppa": _single_mode_view("offsite_dppa", offsite_result),
            "metrics": [],
            "charts": [],
        }
    return _single_mode_view(mode, result)


def render_standalone_report_html(run_id: str, deal_config: dict[str, Any], result: dict[str, Any]) -> str:
    """A minimal, self-contained HTML report (no external assets) for download."""
    mode = deal_config.get("mode", "")
    vm = build_view_model(mode, result)
    sections = [vm] if mode != "both" else [
        {**vm["onsite"], "heading": "Onsite"},
        {**vm["offsite_dppa"], "heading": "Offsite DPPA"},
    ]

    rows = []
    for section in sections:
        heading = section.get("heading", section.get("mode", ""))
        rows.append(f"<h2>{html.escape(str(heading))}</h2><table>")
        for m in section.get("metrics", []):
            rows.append(
                f"<tr><td>{html.escape(str(m['label']))}</td><td>{html.escape(str(m['value']))}</td></tr>"
            )
        rows.append("</table>")

    title = html.escape(deal_config.get("title") or deal_config.get("case", run_id))
    case = html.escape(deal_config.get("case", ""))
    body = "\n".join(rows)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title} - report</title>
<style>body{{font-family:sans-serif;margin:2rem;}}table{{border-collapse:collapse;}}td{{padding:4px 12px;border-bottom:1px solid #ccc;}}</style>
</head><body>
<h1>{title}</h1>
<p>Case: {case} &middot; Run: {html.escape(run_id)}</p>
{body}
</body></html>"""
