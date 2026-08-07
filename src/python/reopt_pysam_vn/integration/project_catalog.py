"""GAP-03: Developer project catalog — versioned data layer and loader.

The catalog is a directory of JSON files (one per project) under
``data/projects/``, mirroring the ``data/vietnam/`` versioned-data pattern.
``catalog_schema.json`` declares the record schema; ``validate_project``
performs lightweight, dependency-free validation (required fields, types,
enums, and the nested ``location`` object) so the matching engine (PHASE-02)
can rely on well-formed records.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CATALOG_DIR = REPO_ROOT / "data" / "projects"
SCHEMA_FILENAME = "catalog_schema.json"


@dataclass
class ProjectRecord:
    """A single developer project in the catalog."""

    project_id: str
    name: str
    developer: str
    location: dict[str, Any]
    technology: str
    capacity_mw: float
    bess_mw: float
    bess_mwh: float
    grid_connection: str
    indicative_strike_usc_kwh: float
    available_from: str
    dppa_structure: str
    status: str
    notes: str
    generation_profile_path: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ProjectRecord:
        known = {
            "project_id",
            "name",
            "developer",
            "location",
            "technology",
            "capacity_mw",
            "bess_mw",
            "bess_mwh",
            "grid_connection",
            "indicative_strike_usc_kwh",
            "available_from",
            "dppa_structure",
            "status",
            "notes",
            "generation_profile_path",
        }
        extra = {k: v for k, v in raw.items() if k not in known and not k.startswith("_")}
        return cls(
            project_id=raw["project_id"],
            name=raw["name"],
            developer=raw["developer"],
            location=raw["location"],
            technology=raw["technology"],
            capacity_mw=float(raw["capacity_mw"]),
            bess_mw=float(raw["bess_mw"]),
            bess_mwh=float(raw["bess_mwh"]),
            grid_connection=raw["grid_connection"],
            indicative_strike_usc_kwh=float(raw["indicative_strike_usc_kwh"]),
            available_from=raw["available_from"],
            dppa_structure=raw["dppa_structure"],
            status=raw["status"],
            notes=raw["notes"],
            generation_profile_path=raw.get("generation_profile_path"),
            extra=extra,
        )


def load_catalog_schema(catalog_dir: Path | str | None = None) -> dict[str, Any]:
    """Load and return the catalog schema definition."""
    catalog_dir = Path(catalog_dir) if catalog_dir is not None else DEFAULT_CATALOG_DIR
    schema_path = catalog_dir / SCHEMA_FILENAME
    return json.loads(schema_path.read_text(encoding="utf-8"))


_PY_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "number": (int, float),
    "object": (dict,),
    "array": (list,),
    "boolean": (bool,),
}


def _type_ok(value: Any, declared: str | list[str]) -> bool:
    declared_list = declared if isinstance(declared, list) else [declared]
    for name in declared_list:
        if name == "null" and value is None:
            return True
        py = _PY_TYPES.get(name)
        if py is None:
            continue
        # bool is a subclass of int; exclude it from numbers unless declared boolean
        if name == "number" and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def _validate_field(name: str, value: Any, spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    declared = spec.get("type")
    if declared is not None and not _type_ok(value, declared):
        errors.append(f"{name}: expected type {declared}, got {type(value).__name__}")
        return errors
    enum = spec.get("enum")
    if enum is not None and value not in enum:
        errors.append(f"{name}: {value!r} not in allowed values {enum}")
    minimum = spec.get("min")
    if (
        minimum is not None
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value < minimum
    ):
        errors.append(f"{name}: {value} below minimum {minimum}")
    return errors


def validate_project(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty == valid)."""
    errors: list[str] = []
    fields_spec: dict[str, Any] = schema.get("fields", {})

    for required in schema.get("required", []):
        if required not in record:
            errors.append(f"{required}: required field is missing")

    for name, value in record.items():
        if name.startswith("_"):
            continue
        spec = fields_spec.get(name)
        if spec is None:
            continue  # unknown extra fields are allowed
        errors.extend(_validate_field(name, value, spec))
        # Validate nested location object
        if name == "location" and isinstance(value, dict) and "fields" in spec:
            for sub_required in spec.get("required", []):
                if sub_required not in value:
                    errors.append(f"location.{sub_required}: required field is missing")
            for sub_name, sub_value in value.items():
                sub_spec = spec["fields"].get(sub_name)
                if sub_spec is not None:
                    errors.extend(
                        _validate_field(f"location.{sub_name}", sub_value, sub_spec)
                    )

    return errors


def load_project_catalog(
    catalog_dir: Path | str | None = None,
    *,
    validate: bool = True,
) -> list[ProjectRecord]:
    """Load every project JSON in ``catalog_dir`` into ``ProjectRecord`` objects.

    Skips ``catalog_schema.json``. When ``validate`` is True, raises
    ``ValueError`` if any record fails schema validation.
    """
    catalog_dir = Path(catalog_dir) if catalog_dir is not None else DEFAULT_CATALOG_DIR
    schema = load_catalog_schema(catalog_dir) if validate else None

    records: list[ProjectRecord] = []
    for path in sorted(catalog_dir.glob("*.json")):
        if path.name == SCHEMA_FILENAME:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if validate and schema is not None:
            errors = validate_project(raw, schema)
            if errors:
                raise ValueError(f"{path.name} failed schema validation: {errors}")
        records.append(ProjectRecord.from_dict(raw))
    return records
