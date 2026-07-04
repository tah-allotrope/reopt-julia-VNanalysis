"""PHASE-05: two-run comparison view-model."""

from reopt_pysam_vn.webapp.compare import build_compare_model

_A = {
    "case": "A",
    "sizing": {"pv_kw": 3000.0},
    "dispatch": {"achieved_delivered_fraction_of_load": 0.6},
    "economics": {"npv": 1000000.0},
}
_B = {
    "case": "B",
    "sizing": {"pv_kw": 4000.0},
    "dispatch": {"achieved_delivered_fraction_of_load": 0.7},
    "economics": {"npv": 1200000.0},
}


def test_compare_aligns_shared_metrics_with_deltas():
    model = build_compare_model("onsite", _A, "onsite", _B)
    rows = {r["label"]: r for r in model["rows"]}
    assert rows["PV size (kW)"]["a"] == 3000.0
    assert rows["PV size (kW)"]["b"] == 4000.0
    assert rows["PV size (kW)"]["delta"] == 1000.0


def test_compare_mixed_modes_uses_intersection_only():
    model = build_compare_model("onsite", _A, "offsite_dppa", {"decision": {"recommended_position": "PROCEED"}})
    labels = {r["label"] for r in model["rows"]}
    assert labels == set()
