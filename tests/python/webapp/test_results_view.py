"""PHASE-04: results view-model (headline metrics + chart series) built from
OnsiteResult / OffsiteDppaResult dicts, without forking analytics logic."""

from reopt_pysam_vn.webapp.results_view import build_view_model, render_standalone_report_html

_ONSITE_RESULT = {
    "case": "TEST",
    "sizing": {"pv_kw": 3000.0, "wind_kw": 0.0, "bess_power_kw": 1000.0, "bess_energy_kwh": 2000.0},
    "dispatch": {
        "renewable_delivered_kwh": 900000.0,
        "exported_renewable_kwh": 100000.0,
        "grid_supplied_kwh": 400000.0,
        "total_load_kwh": 1300000.0,
        "achieved_delivered_fraction_of_load": 0.69,
        "target_delivered_fraction": 0.6,
        "meets_target": True,
    },
    "economics": {"npv": 1500000.0, "lifecycle_capital_costs": 3000000.0},
    "mode": "onsite",
}


def test_build_view_model_onsite_headline_metrics():
    vm = build_view_model("onsite", _ONSITE_RESULT)
    labels = {m["label"] for m in vm["metrics"]}
    assert "PV size (kW)" in labels
    assert "NPV" in labels
    assert vm["mode"] == "onsite"


def test_build_view_model_onsite_has_a_coverage_chart():
    vm = build_view_model("onsite", _ONSITE_RESULT)
    assert any(c["title"].lower().startswith("energy") for c in vm["charts"])


def test_build_view_model_both_mode_nests_onsite_and_offsite():
    both = {"onsite": _ONSITE_RESULT, "offsite_dppa": {"decision": {"recommended_position": "PROCEED"}}}
    vm = build_view_model("both", both)
    assert vm["onsite"] is not None
    assert vm["offsite_dppa"] is not None


def test_build_view_model_handles_missing_result():
    vm = build_view_model("onsite", None)
    assert vm["metrics"] == []
    assert vm["charts"] == []


def test_render_standalone_report_html_includes_case_and_metrics():
    html = render_standalone_report_html("run-1", {"case": "TEST", "mode": "onsite"}, _ONSITE_RESULT)
    assert "TEST" in html
    assert "NPV" in html
    assert "<html" in html.lower()
