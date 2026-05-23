"""Cross-case-study validation: ingest each of 6 case studies and verify outputs."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python" / "integration"))

from reopt_pysam_vn.ingestion import (
    ingest_factory_load,
    extract_load_metadata,
    classify_industry_archetype,
    classify_tou_consumption,
)
from ingest_factory_load import build_artifact

CASE_STUDIES = REPO_ROOT / "scenarios" / "case_studies"

CASE_FILES = [
    ("saigon18", CASE_STUDIES / "saigon18" / "2026-03-20_scenario-a_fixed-sizing_evntou.json"),
    ("ninhsim", CASE_STUDIES / "ninhsim" / "NinhsimSample.csv"),
    ("regina", CASE_STUDIES / "regina" / "Regina.xlsx"),
    ("emivest", CASE_STUDIES / "emivest" / "Emivest.csv"),
    ("verdant", CASE_STUDIES / "verdant" / "Verdant.csv"),
    ("north_thuan", CASE_STUDIES / "north_thuan" / "north_thuan_scenario_a.json"),
]


@pytest.fixture(params=CASE_FILES, ids=[c[0] for c in CASE_FILES])
def case_study(request):
    name, path = request.param
    if not path.exists():
        pytest.skip(f"{name} file not available")
    return name, path


class TestCaseStudyIngestion:
    def test_produces_8760_loads(self, case_study):
        name, path = case_study
        result = ingest_factory_load(path)
        assert len(result.loads_kw) == 8760, f"{name}: expected 8760, got {len(result.loads_kw)}"

    def test_positive_peak_demand(self, case_study):
        name, path = case_study
        result = ingest_factory_load(path)
        meta = extract_load_metadata(result.loads_kw)
        assert meta.peak_demand_kw > 0, f"{name}: peak demand should be positive"

    def test_nonzero_annual_consumption(self, case_study):
        name, path = case_study
        result = ingest_factory_load(path)
        meta = extract_load_metadata(result.loads_kw)
        assert meta.annual_consumption_mwh > 0, f"{name}: annual consumption should be non-zero"

    def test_valid_archetype(self, case_study):
        name, path = case_study
        result = ingest_factory_load(path)
        archetype = classify_industry_archetype(result.loads_kw)
        assert archetype.archetype in [
            "continuous_process",
            "two_shift_factory",
            "single_shift_factory",
            "commercial_daytime",
            "commercial_extended",
        ], f"{name}: invalid archetype {archetype.archetype}"
        assert archetype.confidence in ["high", "medium", "low"]

    def test_tou_shares_sum_to_100(self, case_study):
        name, path = case_study
        result = ingest_factory_load(path)
        tou = classify_tou_consumption(result.loads_kw)
        total = tou.peak_share_pct + tou.offpeak_share_pct + tou.normal_share_pct
        assert abs(total - 100.0) < 0.01, f"{name}: TOU shares sum to {total}"


class TestArtifactWriter:
    def test_artifact_structure(self):
        path = CASE_STUDIES / "ninhsim" / "NinhsimSample.csv"
        if not path.exists():
            pytest.skip("ninhsim CSV not available")

        artifact = build_artifact(str(path), project_name="test_ninhsim")

        assert "_meta" in artifact
        assert "site" in artifact
        assert "loads_kw" in artifact
        assert "metadata" in artifact
        assert "cleaning" in artifact
        assert "classification" in artifact

        assert len(artifact["loads_kw"]) == 8760
        assert artifact["metadata"]["project_name"] == "test_ninhsim"
        assert artifact["metadata"]["peak_demand_kw"] > 0
        assert artifact["metadata"]["annual_consumption_mwh"] > 0
        assert artifact["classification"]["archetype"] in [
            "continuous_process", "two_shift_factory", "single_shift_factory",
            "commercial_daytime", "commercial_extended",
        ]
        assert artifact["classification"]["tou"]["peak_share_pct"] > 0

    def test_artifact_roundtrip_json(self):
        path = CASE_STUDIES / "ninhsim" / "NinhsimSample.csv"
        if not path.exists():
            pytest.skip("ninhsim CSV not available")

        artifact = build_artifact(str(path))

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(artifact, f, indent=2)
            out_path = Path(f.name)

        try:
            with out_path.open() as f:
                loaded = json.load(f)
            assert len(loaded["loads_kw"]) == 8760
            assert loaded["_meta"]["source_format"] == "csv"
        finally:
            out_path.unlink()

    def test_all_case_studies_produce_valid_artifacts(self):
        valid_count = 0
        for name, path in CASE_FILES:
            if not path.exists():
                continue
            try:
                artifact = build_artifact(str(path), project_name=name)
                assert len(artifact["loads_kw"]) == 8760
                assert artifact["metadata"]["peak_demand_kw"] > 0
                assert artifact["metadata"]["annual_consumption_mwh"] > 0
                assert artifact["classification"]["archetype"] in [
                    "continuous_process", "two_shift_factory",
                    "single_shift_factory", "commercial_daytime",
                    "commercial_extended",
                ]
                valid_count += 1
            except Exception as e:
                pytest.fail(f"{name} failed: {e}")

        assert valid_count >= 5, f"Only {valid_count} case studies produced valid artifacts"


class TestCLIEntrypoint:
    def test_cli_produces_output(self):
        input_path = CASE_STUDIES / "ninhsim" / "NinhsimSample.csv"
        if not input_path.exists():
            pytest.skip("ninhsim CSV not available")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            import subprocess
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "python" / "ingest_factory_load.py"),
                    "--input", str(input_path),
                    "--output", str(output_path),
                    "--year", "2024",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, f"CLI failed: {result.stderr}"

            with output_path.open() as f:
                artifact = json.load(f)
            assert len(artifact["loads_kw"]) == 8760
        finally:
            output_path.unlink(missing_ok=True)
