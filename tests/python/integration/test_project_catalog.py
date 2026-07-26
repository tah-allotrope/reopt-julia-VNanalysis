"""GAP-03 PHASE-01: Developer project catalog schema validation tests.

Validates that the seed project catalog under ``data/projects/`` exists, that
every record conforms to ``catalog_schema.json``, and that the loader surfaces
the records as structured ``ProjectRecord`` objects for the matching engine.
"""

from __future__ import annotations

import json
from pathlib import Path


from reopt_pysam_vn.integration.project_catalog import (
    ProjectRecord,
    load_catalog_schema,
    load_project_catalog,
    validate_project,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_DIR = REPO_ROOT / "data" / "projects"
SCHEMA_PATH = CATALOG_DIR / "catalog_schema.json"

EXPECTED_PROJECT_IDS = {
    "saigon18_onsite_solar_bess",
    "ninhsim_offsite_solar_wind",
    "north_thuan_offsite_solar_wind_bess",
    "real_project_onsite_solar_bess",
    "prospective_offsite_wind",
}

VALID_TECHNOLOGIES = {"solar", "wind", "solar_bess", "wind_bess", "hybrid"}
VALID_GRID = {"onsite_private_wire", "grid_connected_22kv", "grid_connected_110kv"}
VALID_DPPA = {"private_wire", "virtual_cfd", "physical_dppa"}
VALID_STATUS = {"operational", "construction", "development", "prospective"}
VALID_REGION = {"north", "central", "south"}


def test_catalog_directory_and_schema_exist():
    assert CATALOG_DIR.is_dir(), "data/projects/ catalog directory must exist"
    assert SCHEMA_PATH.is_file(), "catalog_schema.json must exist"


def test_schema_loads_and_declares_required_fields():
    schema = load_catalog_schema()
    required = set(schema["required"])
    for field in (
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
    ):
        assert field in required, f"schema must require {field!r}"


def test_catalog_has_five_seed_projects():
    catalog = load_project_catalog()
    assert len(catalog) == 5
    assert {p.project_id for p in catalog} == EXPECTED_PROJECT_IDS


def test_every_project_is_a_project_record():
    catalog = load_project_catalog()
    for project in catalog:
        assert isinstance(project, ProjectRecord)


def test_all_seed_projects_pass_schema_validation():
    schema = load_catalog_schema()
    for raw_path in sorted(CATALOG_DIR.glob("*.json")):
        if raw_path.name == "catalog_schema.json":
            continue
        record = json.loads(raw_path.read_text(encoding="utf-8"))
        errors = validate_project(record, schema)
        assert errors == [], f"{raw_path.name} failed validation: {errors}"


def test_required_enum_fields_are_valid():
    catalog = load_project_catalog()
    for project in catalog:
        assert project.project_id
        assert project.technology in VALID_TECHNOLOGIES
        assert project.grid_connection in VALID_GRID
        assert project.dppa_structure in VALID_DPPA
        assert project.status in VALID_STATUS
        assert project.location["region"] in VALID_REGION
        assert project.capacity_mw > 0


def test_saigon18_seed_is_onsite_solar_bess():
    catalog = {p.project_id: p for p in load_project_catalog()}
    saigon18 = catalog["saigon18_onsite_solar_bess"]
    assert saigon18.technology == "solar_bess"
    assert saigon18.grid_connection == "onsite_private_wire"
    assert saigon18.dppa_structure == "private_wire"
    assert saigon18.bess_mw > 0 and saigon18.bess_mwh > 0
    assert saigon18.location["region"] == "south"


def test_prospective_wind_is_prospective_status():
    catalog = {p.project_id: p for p in load_project_catalog()}
    wind = catalog["prospective_offsite_wind"]
    assert wind.status == "prospective"
    assert wind.technology == "wind"
    assert wind.bess_mw == 0


def test_validation_rejects_missing_required_field():
    schema = load_catalog_schema()
    bad = {"project_id": "x"}  # missing nearly everything
    errors = validate_project(bad, schema)
    assert errors, "validator must report errors for an incomplete record"


def test_validation_rejects_bad_enum():
    schema = load_catalog_schema()
    catalog = load_project_catalog()
    record = json.loads(
        (CATALOG_DIR / "saigon18_onsite_solar_bess.json").read_text(encoding="utf-8")
    )
    record["technology"] = "fusion_reactor"
    errors = validate_project(record, schema)
    assert any("technology" in e for e in errors)
    assert catalog  # sanity: real catalog still loads
