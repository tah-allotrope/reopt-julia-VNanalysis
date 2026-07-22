import json
from pathlib import Path

import pytest

from reopt_pysam_vn.integration.bridge import build_ninhsim_single_owner_inputs
from reopt_pysam_vn.integration.strike_search import (
    build_strike_price_summary,
    sweep_strike_prices,
)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PHASE4_ARTIFACT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-04_ninhsim-single-owner-finance.json"
)
NINHSIM_REOPT = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "ninhsim"
    / "2026-04-01_ninhsim_scenario-b_optimized-cppa_reopt-results.json"
)
NINHSIM_SCENARIO = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "ninhsim"
    / "2026-04-01_ninhsim_scenario-b_optimized-cppa.json"
)
NINHSIM_MEMO = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-02_ninhsim-commercial-candidate-memo.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.requires_artifacts
def test_sweep_strike_prices_returns_first_viable_candidate_with_ordered_results():
    phase4 = _load_json(PHASE4_ARTIFACT)
    base_inputs = build_ninhsim_single_owner_inputs(
        reopt_results=_load_json(NINHSIM_REOPT),
        scenario=_load_json(NINHSIM_SCENARIO),
        commercial_memo=_load_json(NINHSIM_MEMO),
    )

    def fake_runner(inputs):
        irr = round(inputs.ppa_price_input_usd_per_kwh - 0.05, 6)
        return {
            "model": "PySAM Single Owner",
            "status": "ok",
            "inputs": {
                "ppa_price_input_usd_per_kwh": inputs.ppa_price_input_usd_per_kwh,
                "target_irr_fraction": inputs.target_irr_fraction,
            },
            "case": dict(inputs.metadata),
            "outputs": {
                "project_return_aftertax_irr_fraction": irr,
                "project_return_aftertax_npv_usd": irr * 1_000_000.0,
                "min_dscr": irr,
            },
            "annual_cashflows": [],
        }

    results = sweep_strike_prices(
        phase4_results=phase4,
        base_inputs=base_inputs,
        target_irr_fraction=0.10,
        min_strike_cents_per_kwh=5.0,
        max_strike_cents_per_kwh=15.0,
        step_cents_per_kwh=0.5,
        runner=fake_runner,
    )

    assert results["sweep_settings"]["candidate_count"] == 21
    assert results["sweep_results"][0][
        "strike_price_us_cents_per_kwh"
    ] == pytest.approx(5.0)
    assert results["sweep_results"][-1][
        "strike_price_us_cents_per_kwh"
    ] == pytest.approx(15.0)
    assert results["viability"][
        "minimum_viable_strike_us_cents_per_kwh"
    ] == pytest.approx(15.0)
    assert results["viability"]["minimum_viable_index"] == 20
    assert results["viability"]["target_irr_fraction"] == pytest.approx(0.10)
    assert results["sweep_results"][0]["is_viable"] is False
    assert results["sweep_results"][-1]["is_viable"] is True
    assert results["sweep_results"][-1]["case"]["source_case"] == "ninhsim"


PySAM = pytest.importorskip("PySAM")


@pytest.mark.xfail(
    reason="numeric benchmark drift, red since 2026-07-04, tracked in activeContext.md 'Known pre-existing test failures'",
    strict=False,
)
def test_build_strike_price_summary_finds_minimum_viable_ninhsim_strike():
    phase4 = _load_json(PHASE4_ARTIFACT)
    base_inputs = build_ninhsim_single_owner_inputs(
        reopt_results=_load_json(NINHSIM_REOPT),
        scenario=_load_json(NINHSIM_SCENARIO),
        commercial_memo=_load_json(NINHSIM_MEMO),
    )

    results = build_strike_price_summary(
        phase4_results=phase4,
        base_inputs=base_inputs,
        target_irr_fraction=0.10,
        min_strike_cents_per_kwh=5.0,
        max_strike_cents_per_kwh=15.0,
        step_cents_per_kwh=0.5,
    )

    assert results["status"] == "ok"
    assert results["case"]["source_case"] == "ninhsim"
    assert results["phase4_reference"]["artifact_path"].endswith(
        "2026-04-04_ninhsim-single-owner-finance.json"
    )
    assert results["sweep_settings"] == {
        "target_irr_fraction": 0.10,
        "min_strike_us_cents_per_kwh": 5.0,
        "max_strike_us_cents_per_kwh": 15.0,
        "step_us_cents_per_kwh": 0.5,
        "candidate_count": 21,
    }
    assert len(results["sweep_results"]) == 21
    assert results["viability"][
        "minimum_viable_strike_us_cents_per_kwh"
    ] == pytest.approx(15.0)
    assert results["viability"]["minimum_viable_irr_fraction"] >= 0.10
    assert results["viability"][
        "phase4_baseline_strike_us_cents_per_kwh"
    ] == pytest.approx(phase4["inputs"]["ppa_price_input_usd_per_kwh"] * 100.0)
    assert (
        results["sweep_results"][0]["outputs"]["project_return_aftertax_irr_fraction"]
        is None
    )
    assert (
        results["sweep_results"][-1]["outputs"]["project_return_aftertax_irr_fraction"]
        >= 0.10
    )
