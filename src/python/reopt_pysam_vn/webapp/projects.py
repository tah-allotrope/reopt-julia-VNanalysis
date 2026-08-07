"""Project-catalog loader for the webapp map overlay.

Reads ``data/projects/*.json`` directly (no new persistence), returning the
subset of fields useful for map markers and tooltips.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["list_projects"]

_PROJECTS_DIR = Path(__file__).resolve().parents[4] / "data" / "projects"


def _is_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def list_projects() -> list[dict[str, Any]]:
    """Return catalog projects with valid point locations.

    Skips ``catalog_schema.json`` and any record whose ``location.lat`` or
    ``location.lon`` is missing or non-numeric so a malformed file cannot break
    the map overlay.
    """
    out: list[dict[str, Any]] = []
    if not _PROJECTS_DIR.exists():
        return out

    for path in sorted(_PROJECTS_DIR.glob("*.json")):
        if path.name == "catalog_schema.json":
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        location = raw.get("location") or {}
        lat = location.get("lat")
        lon = location.get("lon")
        if not _is_numeric(lat) or not _is_numeric(lon):
            continue

        out.append(
            {
                "project_id": raw.get("project_id"),
                "name": raw.get("name"),
                "technology": raw.get("technology"),
                "capacity_mw": raw.get("capacity_mw"),
                "status": raw.get("status"),
                "indicative_strike_usc_kwh": raw.get("indicative_strike_usc_kwh"),
                "location": {
                    "lat": lat,
                    "lon": lon,
                    "province": location.get("province"),
                    "region": location.get("region"),
                },
            }
        )
    return out
