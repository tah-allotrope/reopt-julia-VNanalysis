"""Structural validation for the deal-config and extracted-inputs schemas.

Hand-rolled rather than the ``jsonschema`` package: both schema files promise
"no jsonschema dependency required at runtime". ``deal_config.schema.json`` only
ever uses ``required``/``type``/``enum``; ``extracted_inputs.schema.json`` adds
``minItems``/``maxItems``/``minLength``/``minimum``/``maximum``. Supporting
exactly those keeps the validator small and keeps the promise.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = [
    "DealConfigValidationError",
    "ExtractedInputsValidationError",
    "load_deal_config_schema",
    "load_extracted_inputs_schema",
    "validate_deal_config",
    "validate_extracted_inputs",
]

_SCHEMA_DIR = Path(__file__).resolve().parents[3].parent / "data" / "schemas"
_DEAL_CONFIG_SCHEMA_PATH = _SCHEMA_DIR / "deal_config.schema.json"
_EXTRACTED_INPUTS_SCHEMA_PATH = _SCHEMA_DIR / "extracted_inputs.schema.json"

_JSON_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
}

_deal_config_schema_cache: dict[str, Any] | None = None
_extracted_inputs_schema_cache: dict[str, Any] | None = None


class DealConfigValidationError(ValueError):
    """Raised when a dict fails structural validation against the deal-config schema.

    Carries every violation found (not just the first) in ``.errors``.
    """

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class ExtractedInputsValidationError(ValueError):
    """Raised when a dict fails structural validation against the extracted-inputs schema.

    Carries every violation found (not just the first) in ``.errors``.
    """

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load_deal_config_schema() -> dict[str, Any]:
    """Load and cache data/schemas/deal_config.schema.json (utf-8-sig, per repo convention)."""
    global _deal_config_schema_cache
    if _deal_config_schema_cache is None:
        _deal_config_schema_cache = json.loads(_DEAL_CONFIG_SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    return _deal_config_schema_cache


def load_extracted_inputs_schema() -> dict[str, Any]:
    """Load and cache data/schemas/extracted_inputs.schema.json (utf-8-sig, per repo convention)."""
    global _extracted_inputs_schema_cache
    if _extracted_inputs_schema_cache is None:
        _extracted_inputs_schema_cache = json.loads(
            _EXTRACTED_INPUTS_SCHEMA_PATH.read_text(encoding="utf-8-sig")
        )
    return _extracted_inputs_schema_cache


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


def _check_type(value: Any, expected_type: str, path: str, errors: list[str]) -> bool:
    """Return True if value matches expected_type; append an error and return False otherwise."""
    checker = _JSON_TYPE_CHECKS.get(expected_type)
    if checker is None:
        return True
    if not checker(value):
        errors.append(f"{path}: expected type '{expected_type}', got '{_type_name(value)}' ({value!r})")
        return False
    return True


def _check_enum(value: Any, allowed: list[Any], path: str, errors: list[str]) -> None:
    if value not in allowed:
        allowed_str = ", ".join(repr(a) for a in allowed)
        errors.append(f"{path}: value {value!r} is not one of the allowed values [{allowed_str}]")


def _apply_constraints(value: Any, prop_schema: dict[str, Any], path: str, errors: list[str]) -> None:
    """Apply the numeric/length bound keywords (minimum/maximum/minItems/maxItems/minLength)."""
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if "minimum" in prop_schema and value < prop_schema["minimum"]:
            errors.append(f"{path}: expected value >= {prop_schema['minimum']}, got {value!r}")
        if "maximum" in prop_schema and value > prop_schema["maximum"]:
            errors.append(f"{path}: expected value <= {prop_schema['maximum']}, got {value!r}")
    elif isinstance(value, list):
        if "minItems" in prop_schema and len(value) < prop_schema["minItems"]:
            errors.append(f"{path}: expected at least {prop_schema['minItems']} items, got {len(value)}")
        if "maxItems" in prop_schema and len(value) > prop_schema["maxItems"]:
            errors.append(f"{path}: expected at most {prop_schema['maxItems']} items, got {len(value)}")
    elif isinstance(value, str):
        if "minLength" in prop_schema and len(value) < prop_schema["minLength"]:
            errors.append(f"{path}: expected at least {prop_schema['minLength']} characters, got {len(value)}")


def _validate_object(
    data: dict[str, Any],
    schema: dict[str, Any],
    path_prefix: str,
    errors: list[str],
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
        _apply_constraints(value, prop_schema, field_path, errors)
        if expected_type == "object" and "properties" in prop_schema:
            _validate_object(value, prop_schema, field_path, errors)


def validate_deal_config(d: dict[str, Any], *, schema: dict[str, Any] | None = None) -> None:
    """Validate ``d`` against the deal-config schema.

    Returns ``None`` on success. Raises ``DealConfigValidationError`` carrying
    every violation found (not just the first) when ``d`` does not conform.
    """
    if schema is None:
        schema = load_deal_config_schema()
    errors: list[str] = []
    _validate_object(d, schema, "", errors)
    if errors:
        raise DealConfigValidationError(errors)


def validate_extracted_inputs(d: dict[str, Any], *, schema: dict[str, Any] | None = None) -> None:
    """Validate ``d`` against the extracted-inputs schema.

    Returns ``None`` on success. Raises ``ExtractedInputsValidationError``
    carrying every violation found (not just the first) when ``d`` does not
    conform.
    """
    if schema is None:
        schema = load_extracted_inputs_schema()
    errors: list[str] = []
    _validate_object(d, schema, "", errors)
    if errors:
        raise ExtractedInputsValidationError(errors)
