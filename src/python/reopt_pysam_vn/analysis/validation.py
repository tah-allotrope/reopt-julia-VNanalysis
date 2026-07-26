"""Structural validation for DealConfig against data/schemas/deal_config.schema.json.

Hand-rolled rather than the ``jsonschema`` package: the schema file's own
``description`` promises "no jsonschema dependency required at runtime", and
this schema only ever uses three JSON Schema keywords — ``required``, ``type``,
and ``enum`` (one level of ``properties`` nesting for the six known sections).
Supporting exactly those keeps the validator small and keeps the promise.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = [
    "DealConfigValidationError",
    "load_deal_config_schema",
    "validate_deal_config",
]

_SCHEMA_PATH = Path(__file__).resolve().parents[3].parent / "data" / "schemas" / "deal_config.schema.json"

_JSON_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
}

_schema_cache: Optional[Dict[str, Any]] = None


class DealConfigValidationError(ValueError):
    """Raised when a dict fails structural validation against the deal-config schema.

    Carries every violation found (not just the first) in ``.errors``.
    """

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load_deal_config_schema() -> Dict[str, Any]:
    """Load and cache data/schemas/deal_config.schema.json (utf-8-sig, per repo convention)."""
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    return _schema_cache


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def _check_type(value: Any, expected_type: str, path: str, errors: List[str]) -> bool:
    """Return True if value matches expected_type; append an error and return False otherwise."""
    checker = _JSON_TYPE_CHECKS.get(expected_type)
    if checker is None:
        return True
    if not checker(value):
        errors.append(f"{path}: expected type '{expected_type}', got '{_type_name(value)}' ({value!r})")
        return False
    return True


def _check_enum(value: Any, allowed: List[Any], path: str, errors: List[str]) -> None:
    if value not in allowed:
        allowed_str = ", ".join(repr(a) for a in allowed)
        errors.append(f"{path}: value {value!r} is not one of the allowed values [{allowed_str}]")


def _validate_object(
    data: Dict[str, Any],
    schema: Dict[str, Any],
    path_prefix: str,
    errors: List[str],
) -> None:
    for required_key in schema.get("required", []):
        if required_key not in data:
            errors.append(f"missing required property: '{required_key}'")

    properties = schema.get("properties", {})
    for key, prop_schema in properties.items():
        if key not in data:
            continue
        value = data[key]
        field_path = f"{path_prefix}{key}" if not path_prefix else f"{path_prefix}.{key}"
        expected_type = prop_schema.get("type")
        if expected_type is not None and not _check_type(value, expected_type, field_path, errors):
            continue
        if "enum" in prop_schema:
            _check_enum(value, prop_schema["enum"], field_path, errors)
        if expected_type == "object" and "properties" in prop_schema:
            _validate_object(value, prop_schema, field_path, errors)


def validate_deal_config(d: Dict[str, Any], *, schema: Optional[Dict[str, Any]] = None) -> None:
    """Validate ``d`` against the deal-config schema.

    Returns ``None`` on success. Raises ``DealConfigValidationError`` carrying
    every violation found (not just the first) when ``d`` does not conform.
    """
    if schema is None:
        schema = load_deal_config_schema()
    errors: List[str] = []
    _validate_object(d, schema, "", errors)
    if errors:
        raise DealConfigValidationError(errors)
