"""Scenario-template seeding and guided-form -> DealConfig mapping (PHASE-03,
DEC-006). The four ``scenarios/templates/*.json`` files are REopt-scenario
shaped (they carry a ``_template`` metadata block plus ``Site``/``PV``/
``Financial`` sections); this module reads the handful of fields that make
sensible form defaults (region, customer type, voltage level, lat/long,
discount rate, installed cost) rather than mapping the whole REopt scenario.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

__all__ = ["list_templates", "template_defaults", "deal_config_from_form"]

_TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "scenarios" / "templates"


def _template_path(template_id: str) -> Path:
    path = _TEMPLATES_DIR / f"{template_id}.json"
    if not path.exists():
        raise KeyError(f"no such template: {template_id!r}")
    return path


def _load_template(template_id: str) -> Dict[str, Any]:
    return json.loads(_template_path(template_id).read_text(encoding="utf-8-sig"))


def list_templates() -> List[Dict[str, str]]:
    out = []
    for path in sorted(_TEMPLATES_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        meta = raw.get("_template", {})
        out.append(
            {
                "id": path.stem,
                "name": meta.get("name", path.stem),
                "description": meta.get("description", ""),
            }
        )
    return out


def template_defaults(template_id: str) -> Dict[str, Any]:
    """Prefill values for the guided form, derived from a scenario template."""
    raw = _load_template(template_id)
    meta = raw.get("_template", {})
    site_block = raw.get("Site", {})
    pv_block = raw.get("PV", {})
    fin_block = raw.get("Financial", {})
    return {
        "site": {
            "region": meta.get("region", ""),
            "customer_type": meta.get("customer_type", ""),
            "voltage_level": meta.get("voltage_level", ""),
            "latitude": site_block.get("latitude"),
            "longitude": site_block.get("longitude"),
        },
        "finance": {
            "installed_cost_usd_per_kw": pv_block.get("installed_cost_per_kw"),
            "discount_rate_fraction": fin_block.get("owner_discount_rate_fraction"),
        },
    }


def deal_config_from_form(form: Dict[str, Any], *, loads_kw: List[float]) -> Dict[str, Any]:
    """Build a schema-shaped DealConfig dict from guided-form input.

    ``form`` sections mirror ``data/schemas/deal_config.schema.json``: only
    the key overrides a user actually changed need to be present (DEC-017);
    template ``site``/``finance`` defaults should already have been merged in
    by the caller before this is invoked, so this function only assembles the
    final structure and validates the required top-level fields.
    """
    case = form.get("case")
    if not case:
        raise ValueError("form is missing required field `case`")
    mode = form.get("mode")
    if not mode:
        raise ValueError("form is missing required field `mode`")

    return {
        "case": case,
        "mode": mode,
        "title": form.get("title", ""),
        "site": dict(form.get("site", {})),
        "plant": dict(form.get("plant", {})),
        "load": {**dict(form.get("load", {})), "loads_kw": list(loads_kw)},
        "contract": dict(form.get("contract", {})),
        "finance": dict(form.get("finance", {})),
    }
