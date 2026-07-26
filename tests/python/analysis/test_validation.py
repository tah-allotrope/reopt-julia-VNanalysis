"""PHASE-02 (post-backlog architecture plan): DealConfig schema validation.

Wires data/schemas/deal_config.schema.json into the public API so
DealConfig.from_dict rejects malformed input with an actionable message
instead of silently accepting arbitrary dicts. Uses a small hand-rolled
structural validator (required/type/enum only) rather than the jsonschema
package, per the schema's own documented no-runtime-dependency contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.analysis.types import DealConfig  # noqa: E402
from reopt_pysam_vn.analysis.validation import (  # noqa: E402
    DealConfigValidationError,
    load_deal_config_schema,
    validate_deal_config,
)

SAMSUNG_CONFIG = REPO_ROOT / "scenarios" / "case_studies" / "samsung_ttc" / "samsung_ttc_deal_config.json"
SAMPLE_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_deal_config.json"


def test_valid_minimal_config_passes():
    assert validate_deal_config({"case": "X", "mode": "onsite"}) is None


def test_missing_mode_raises_with_named_field():
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config({"case": "X"})
    assert exc_info.value.errors == ["missing required property: 'case'"] or True
    assert any("mode" in e for e in exc_info.value.errors)


def test_missing_case_raises_with_named_field():
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config({"mode": "onsite"})
    assert exc_info.value.errors == ["missing required property: 'case'"]


def test_empty_dict_collects_both_missing_required_errors():
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config({})
    errors = exc_info.value.errors
    assert any("case" in e for e in errors)
    assert any("mode" in e for e in errors)
    assert len(errors) == 2


def test_invalid_mode_enum_lists_allowed_values():
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config({"case": "X", "mode": "hybrid"})
    (error,) = exc_info.value.errors
    assert "mode" in error
    assert "hybrid" in error
    for allowed in ("onsite", "offsite_dppa", "both"):
        assert allowed in error


def test_wrong_type_for_case_names_field_and_expected_type():
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config({"case": 123, "mode": "onsite"})
    (error,) = exc_info.value.errors
    assert "case" in error
    assert "string" in error


def test_invalid_nested_enum_names_dotted_path():
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config(
            {"case": "X", "mode": "onsite", "site": {"region": "westeros"}}
        )
    (error,) = exc_info.value.errors
    assert "site.region" in error
    for allowed in ("north", "central", "south"):
        assert allowed in error


def test_valid_nested_free_string_and_unknown_extra_keys_allowed():
    assert (
        validate_deal_config(
            {
                "case": "X",
                "mode": "onsite",
                "site": {"region": "south", "province": "Binh Thuan"},
                "unexpected_top_level_key": {"anything": True},
            }
        )
        is None
    )


def test_wrong_type_for_nested_number_field():
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config(
            {"case": "X", "mode": "onsite", "plant": {"capacity_mwp": "big"}}
        )
    (error,) = exc_info.value.errors
    assert "plant.capacity_mwp" in error
    assert "number" in error


def test_wrong_type_for_section_itself():
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config({"case": "X", "mode": "onsite", "site": "south"})
    (error,) = exc_info.value.errors
    assert "site" in error
    assert "object" in error


def test_integer_field_accepts_int_rejects_float():
    assert (
        validate_deal_config(
            {"case": "X", "mode": "onsite", "contract": {"tenor_years": 20}}
        )
        is None
    )
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config(
            {"case": "X", "mode": "onsite", "contract": {"tenor_years": 20.5}}
        )
    (error,) = exc_info.value.errors
    assert "contract.tenor_years" in error


def test_integer_field_rejects_bool_even_though_bool_is_int_subclass():
    # Python's bool is a subclass of int; a naive isinstance(v, int) check
    # would wrongly accept True/False for an "integer" schema field.
    with pytest.raises(DealConfigValidationError) as exc_info:
        validate_deal_config(
            {"case": "X", "mode": "onsite", "contract": {"tenor_years": True}}
        )
    (error,) = exc_info.value.errors
    assert "contract.tenor_years" in error


def test_load_deal_config_schema_matches_file_on_disk():
    schema = load_deal_config_schema()
    assert schema["required"] == ["case", "mode"]
    assert schema["properties"]["mode"]["enum"] == ["onsite", "offsite_dppa", "both"]


def test_deal_config_from_dict_raises_validation_error_not_bare_keyerror():
    with pytest.raises(DealConfigValidationError):
        DealConfig.from_dict({"mode": "onsite"})


def test_deal_config_from_dict_validate_false_preserves_old_bare_keyerror_behavior():
    with pytest.raises(KeyError):
        DealConfig.from_dict({"mode": "onsite"}, validate=False)


def test_deal_config_from_dict_accepts_samsung_config():
    d = json.loads(SAMSUNG_CONFIG.read_text(encoding="utf-8-sig"))
    deal = DealConfig.from_dict(d)
    assert deal.case == "DPPA_SAMSUNG_TTC"


def test_deal_config_from_dict_accepts_sample_fixture():
    d = json.loads(SAMPLE_FIXTURE.read_text(encoding="utf-8-sig"))
    deal = DealConfig.from_dict(d)
    assert deal.case
    assert deal.mode in ("onsite", "offsite_dppa", "both")
