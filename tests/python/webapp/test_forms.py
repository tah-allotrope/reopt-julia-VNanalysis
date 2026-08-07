"""PHASE-03: scenario-template seeding and form -> DealConfig mapping."""

import pytest
from reopt_pysam_vn.webapp.forms import (
    deal_config_from_form,
    list_templates,
    template_defaults,
)

_HOURS = 8760


def test_list_templates_returns_four_archetypes():
    templates = list_templates()
    ids = {t["id"] for t in templates}
    assert ids == {
        "vn_commercial_rooftop_pv",
        "vn_industrial_pv_storage",
        "vn_hospital_resilience",
        "vn_offgrid_microgrid",
    }
    for t in templates:
        assert t["name"]
        assert t["description"]


def test_template_defaults_carries_site_and_finance_hints():
    defaults = template_defaults("vn_industrial_pv_storage")
    assert defaults["site"]["region"] == "south"
    assert defaults["site"]["customer_type"] == "industrial"
    assert defaults["site"]["voltage_level"]
    assert defaults["finance"]["discount_rate_fraction"] == pytest.approx(0.08)


def test_unknown_template_raises_key_error():
    with pytest.raises(KeyError):
        template_defaults("does_not_exist")


def test_deal_config_from_form_builds_valid_deal_config():
    form = {
        "case": "MY_DEAL",
        "mode": "onsite",
        "title": "My deal",
        "template_id": "vn_commercial_rooftop_pv",
        "site": {"region": "south", "customer_type": "commercial", "voltage_level": "medium_voltage_22kv_to_110kv"},
        "plant": {"capacity_mwp": 2.5, "bess_power_mw": 0.0, "bess_energy_mwh": 0.0},
        "contract": {"target_delivered_fraction": 0.6},
        "finance": {"discount_rate_fraction": 0.1},
    }
    loads_kw = [123.4] * _HOURS
    deal_config = deal_config_from_form(form, loads_kw=loads_kw)
    assert deal_config["case"] == "MY_DEAL"
    assert deal_config["mode"] == "onsite"
    assert deal_config["site"]["region"] == "south"
    assert deal_config["plant"]["capacity_mwp"] == 2.5
    assert len(deal_config["load"]["loads_kw"]) == _HOURS


def test_deal_config_from_form_rejects_missing_case():
    with pytest.raises(ValueError, match="case"):
        deal_config_from_form({"mode": "onsite"}, loads_kw=[1.0] * _HOURS)
