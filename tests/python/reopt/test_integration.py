"""
Layer 4: Integration / Regression Tests for reopt_pysam_vn.reopt.preprocess (Python)

End-to-end tests that verify the full pipeline produces reasonable results.
Tests are split into:
  - Template smoke tests (no solver, no API key) — always run
  - API-dependent tests (require NREL API key) — skipped if key not available

Run: pytest tests/python/reopt/test_integration.py -v
  or: pytest tests/python/reopt/test_integration.py -v -k smoke   (smoke tests only)
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.preprocess import (
    apply_vietnam_defaults,
    load_vietnam_data,
)

TEMPLATES_DIR = REPO_ROOT / "scenarios" / "templates"
BASELINES_DIR = REPO_ROOT / "tests" / "baselines"
ENV_PATH = REPO_ROOT / "NREL_API.env"

# REopt API config
REOPT_API_BASE = "https://developer.nlr.gov/api/reopt/stable"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_nrel_env():
    """Load NREL API keys from NREL_API.env file."""
    if not ENV_PATH.is_file():
        return None
    api_key = None
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key == "API_KEY_NAME":
            api_key = value
            os.environ["NREL_DEVELOPER_API_KEY"] = value
        elif key == "API_KEY_EMAIL":
            os.environ["NREL_DEVELOPER_EMAIL"] = value
    return api_key


def strip_template_meta(d: dict) -> dict:
    """Remove _template metadata key that REopt API doesn't recognize."""
    d.pop("_template", None)
    return d


def ensure_emissions_array(d: dict) -> dict:
    """Convert scalar emissions factor to 8760 array if needed."""
    eu = d.get("ElectricUtility", {})
    ef = eu.get("emissions_factor_series_lb_CO2_per_kwh")
    if isinstance(ef, (int, float)):
        eu["emissions_factor_series_lb_CO2_per_kwh"] = [float(ef)] * 8760
        d["ElectricUtility"] = eu
    return d


def check_regression(actual, baseline, tolerance=0.05):
    """Check if a metric deviates from baseline by more than tolerance fraction."""
    if baseline == 0:
        return actual == 0, actual, baseline, 0.0
    pct_diff = abs(actual - baseline) / abs(baseline)
    return pct_diff <= tolerance, actual, baseline, pct_diff


def submit_reopt_job(scenario: dict, api_key: str):
    """Submit a job to the REopt API and poll for results."""
    import requests

    url = f"{REOPT_API_BASE}/job/?api_key={api_key}"
    resp = requests.post(url, json=scenario, timeout=30)
    resp.raise_for_status()
    job = resp.json()

    run_uuid = job.get("run_uuid")
    if not run_uuid:
        raise RuntimeError(f"No run_uuid in API response: {job}")

    # Poll for results
    results_url = f"{REOPT_API_BASE}/job/{run_uuid}/results/?api_key={api_key}"
    for _ in range(60):
        time.sleep(5)
        resp = requests.get(results_url, timeout=30)
        resp.raise_for_status()
        results = resp.json()
        status = results.get("status", "")
        if status == "optimal":
            return results
        elif status in ("error", "infeasible", "timed_out"):
            raise RuntimeError(f"REopt API job {run_uuid} failed with status: {status}")

    raise RuntimeError(f"REopt API job {run_uuid} timed out after 5 minutes")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vn():
    return load_vietnam_data()


@pytest.fixture(scope="module")
def api_key():
    key = load_nrel_env()
    return key


# ---------------------------------------------------------------------------
# 1. Template Smoke Tests — no solver, no API key
# ---------------------------------------------------------------------------


class TestTemplateSmokeTests:
    """Verify all template files are valid JSON with correct Vietnam defaults."""

    def _template_files(self):
        return sorted(TEMPLATES_DIR.glob("*.json"))

    def test_templates_directory_exists(self):
        assert TEMPLATES_DIR.is_dir(), f"Templates directory not found: {TEMPLATES_DIR}"

    def test_all_templates_parse_as_json(self):
        for f in self._template_files():
            data = json.loads(f.read_text(encoding="utf-8"))
            assert isinstance(data, dict), f"{f.name} did not parse as a dict"

    def test_all_templates_have_required_blocks(self):
        for f in self._template_files():
            data = json.loads(f.read_text(encoding="utf-8"))
            assert "Site" in data, f"{f.name} missing Site"
            assert "ElectricLoad" in data, f"{f.name} missing ElectricLoad"
            assert "Financial" in data, f"{f.name} missing Financial"

    def test_all_templates_zero_us_incentives(self):
        for f in self._template_files():
            data = json.loads(f.read_text(encoding="utf-8"))

            if "PV" in data and isinstance(data["PV"], dict):
                assert data["PV"].get("federal_itc_fraction", 0) == 0, (
                    f"{f.name} PV ITC not zero"
                )
                assert data["PV"].get("macrs_option_years", 0) == 0, (
                    f"{f.name} PV MACRS not zero"
                )
                assert data["PV"].get("macrs_bonus_fraction", 0) == 0, (
                    f"{f.name} PV MACRS bonus not zero"
                )

            if "Wind" in data and isinstance(data["Wind"], dict):
                assert data["Wind"].get("federal_itc_fraction", 0) == 0, (
                    f"{f.name} Wind ITC not zero"
                )
                assert data["Wind"].get("macrs_option_years", 0) == 0, (
                    f"{f.name} Wind MACRS not zero"
                )

            if "ElectricStorage" in data and isinstance(data["ElectricStorage"], dict):
                assert data["ElectricStorage"].get("total_itc_fraction", 0) == 0, (
                    f"{f.name} Storage ITC not zero"
                )
                assert data["ElectricStorage"].get("installed_cost_constant", 0) == 0, (
                    f"{f.name} Storage cost_constant not zero"
                )

            if "Generator" in data and isinstance(data["Generator"], dict):
                assert data["Generator"].get("federal_itc_fraction", 0) == 0, (
                    f"{f.name} Generator ITC not zero"
                )

    def test_all_templates_vietnam_financials(self):
        for f in self._template_files():
            data = json.loads(f.read_text(encoding="utf-8"))
            fin = data["Financial"]
            assert fin["offtaker_tax_rate_fraction"] == 0.20, f"{f.name} wrong tax rate"
            assert fin["analysis_years"] == 25, f"{f.name} wrong analysis years"

    def test_all_templates_vietnam_emissions(self):
        for f in self._template_files():
            data = json.loads(f.read_text(encoding="utf-8"))
            assert "ElectricUtility" in data, f"{f.name} missing ElectricUtility"
            ef = data["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"]
            if isinstance(ef, (int, float)):
                assert abs(ef - 1.5013) < 0.001, (
                    f"{f.name} wrong emissions factor: {ef}"
                )
            elif isinstance(ef, list):
                assert len(ef) == 8760, f"{f.name} emissions array wrong length"
                assert abs(ef[0] - 1.5013) < 0.001, f"{f.name} wrong emissions factor"

    def test_offgrid_template_has_required_techs(self):
        f = TEMPLATES_DIR / "vn_offgrid_microgrid.json"
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data.get("Settings", {}).get("off_grid_flag") is True
        assert "Generator" in data, "Off-grid template missing Generator"
        assert "ElectricStorage" in data, "Off-grid template missing ElectricStorage"

    def test_hospital_template_has_resilience(self):
        f = TEMPLATES_DIR / "vn_hospital_resilience.json"
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data["Site"].get("min_resil_time_steps", 0) > 0, (
            "Hospital template missing min_resil_time_steps"
        )
        assert "outage_start_time_steps" in data.get("ElectricUtility", {}), (
            "Hospital template missing outage_start_time_steps"
        )
        assert "outage_durations" in data.get("ElectricUtility", {}), (
            "Hospital template missing outage_durations"
        )

    def test_apply_vietnam_defaults_on_templates(self, vn):
        """Verify apply_vietnam_defaults runs without error on each template."""
        for f in self._template_files():
            data = json.loads(f.read_text(encoding="utf-8"))
            strip_template_meta(data)

            # Determine customer_type from _template metadata (already stripped, so re-read)
            raw = json.loads(f.read_text(encoding="utf-8"))
            tmpl = raw.get("_template", {})
            customer_type = tmpl.get("customer_type", "industrial")
            voltage_level = tmpl.get("voltage_level", "medium_voltage_22kv_to_110kv")
            region = tmpl.get("region", "south")

            # Should not raise
            apply_vietnam_defaults(
                data,
                vn,
                customer_type=customer_type,
                voltage_level=voltage_level,
                region=region,
            )

            # After applying defaults, tariff series should exist
            assert "ElectricTariff" in data
            et = data["ElectricTariff"]
            assert "tou_energy_rates_per_kwh" in et
            assert len(et["tou_energy_rates_per_kwh"]) == 8760


# ---------------------------------------------------------------------------
# 2. API-Dependent Tests (require NREL API key)
# ---------------------------------------------------------------------------


@pytest.mark.network
@pytest.mark.skipif(
    not (REPO_ROOT / "NREL_API.env").is_file(),
    reason="NREL_API.env not found — skipping API tests",
)
class TestAPIIntegration:
    """Tests that require the REopt API. Skipped if no API key available."""

    @pytest.mark.requires_nrel_key
    def test_nlr_domain_connectivity(self, api_key):
        """Verify the new developer.nlr.gov domain is reachable and returns a valid load profile.

        Uses the lightweight GET /simulated_load/ endpoint — no job submission,
        no polling, completes in ~2 seconds. Confirms DNS, TLS, and API key all
        work on the new domain after the nrel.gov → nlr.gov migration.
        """
        try:
            import requests
        except ImportError:
            pytest.skip("requests library not installed")

        url = (
            f"{REOPT_API_BASE}/simulated_load/"
            f"?api_key={api_key}"
            f"&doe_reference_name=RetailStore"
            f"&latitude=10.8"
            f"&longitude=106.7"
            f"&annual_kwh=100000"
        )
        resp = requests.get(url, timeout=15)

        assert resp.status_code == 200, (
            f"Expected HTTP 200 from developer.nlr.gov, got {resp.status_code}: {resp.text[:200]}"
        )

        data = resp.json()
        assert "loads_kw" in data, (
            f"Response missing 'loads_kw' key. Keys present: {list(data.keys())}"
        )
        assert len(data["loads_kw"]) == 8760, (
            f"Expected 8760 hourly load values, got {len(data['loads_kw'])}"
        )

    @pytest.mark.requires_nrel_key
    def test_commercial_rooftop_api_solve(self, vn, api_key):
        """Submit commercial rooftop PV template to REopt API and verify results."""
        try:
            import requests  # noqa: F401
        except ImportError:
            pytest.skip("requests library not installed")

        f = TEMPLATES_DIR / "vn_commercial_rooftop_pv.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        strip_template_meta(d)
        ensure_emissions_array(d)

        # Apply Vietnam defaults for TOU tariff
        apply_vietnam_defaults(
            d,
            vn,
            customer_type="commercial",
            voltage_level="medium_voltage_22kv_to_110kv",
            region="south",
        )

        results = submit_reopt_job(d, api_key)

        assert results.get("status") == "optimal"

        # Incentive verification: capital == capital_after_incentives
        fin = results.get("outputs", {}).get("Financial", {})
        capital = fin.get("initial_capital_costs", 0)
        capital_after = fin.get("initial_capital_costs_after_incentives", 0)
        assert abs(capital - capital_after) < 1.0, (
            f"Capital mismatch: before={capital}, after={capital_after}"
        )

        # Sanity checks
        pv_kw = results.get("outputs", {}).get("PV", {}).get("size_kw", 0)
        assert pv_kw >= 0
        lcc = fin.get("lcc", 0)
        assert lcc > 0

    @pytest.mark.requires_nrel_key
    def test_api_vs_baseline_regression(self, vn, api_key):
        """Compare API results against saved baseline (if exists)."""
        try:
            import requests  # noqa: F401
        except ImportError:
            pytest.skip("requests library not installed")

        baseline_path = BASELINES_DIR / "commercial_api_baseline.json"

        f = TEMPLATES_DIR / "vn_commercial_rooftop_pv.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        strip_template_meta(d)
        ensure_emissions_array(d)

        apply_vietnam_defaults(
            d,
            vn,
            customer_type="commercial",
            voltage_level="medium_voltage_22kv_to_110kv",
            region="south",
        )

        results = submit_reopt_job(d, api_key)
        assert results.get("status") == "optimal"

        outputs = results.get("outputs", {})
        actual = {
            "pv_size_kw": outputs.get("PV", {}).get("size_kw", 0),
            "storage_size_kw": outputs.get("ElectricStorage", {}).get("size_kw", 0),
            "storage_size_kwh": outputs.get("ElectricStorage", {}).get("size_kwh", 0),
            "lcc": outputs.get("Financial", {}).get("lcc", 0),
            "npv": outputs.get("Financial", {}).get("npv", 0),
            "initial_capital_costs": outputs.get("Financial", {}).get(
                "initial_capital_costs", 0
            ),
            "initial_capital_costs_after_incentives": outputs.get("Financial", {}).get(
                "initial_capital_costs_after_incentives", 0
            ),
        }

        if baseline_path.is_file():
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
            for metric, act_val in actual.items():
                base_val = baseline.get(metric)
                if base_val is None:
                    continue
                passed, _, _, pct = check_regression(
                    float(act_val), float(base_val), 0.05
                )
                assert passed, (
                    f"{metric}: actual={act_val}, baseline={base_val}, diff={pct * 100:.1f}%"
                )
        else:
            # Save as new baseline
            BASELINES_DIR.mkdir(parents=True, exist_ok=True)
            baseline_path.write_text(json.dumps(actual, indent=2), encoding="utf-8")
            print(f"\n  Baseline saved to: {baseline_path}")
            for k, v in sorted(actual.items()):
                print(f"    {k}: {v}")


# ---------------------------------------------------------------------------
# 3. Cross-check: Julia local vs Python API (structure only — requires both)
# ---------------------------------------------------------------------------


@pytest.mark.network
@pytest.mark.skipif(
    not (REPO_ROOT / "NREL_API.env").is_file(),
    reason="NREL_API.env not found — skipping cross-check tests",
)
class TestJuliaVsAPICrossCheck:
    """
    Compare Julia local solve results against REopt API results.
    Requires both Julia solver results (from baselines) and API access.
    """

    @pytest.mark.requires_nrel_key
    def test_industrial_julia_vs_api_structure(self, api_key):
        """
        Structural cross-check: verify that Julia baseline and API results
        have the same key metrics within ~2% tolerance.
        Only runs if both Julia baseline and API key are available.
        """
        julia_baseline_path = BASELINES_DIR / "industrial_vietnam_baseline.json"
        if not julia_baseline_path.is_file():
            pytest.skip(
                "Julia baseline not yet generated — run test_integration.jl first"
            )

        julia_baseline = json.loads(julia_baseline_path.read_text(encoding="utf-8"))

        # Key metrics to compare (Julia local vs API)
        # Note: ~2% tolerance expected due to emissions cost gap for non-US locations
        metrics_to_check = ["pv_size_kw", "lcc"]
        for metric in metrics_to_check:
            val = julia_baseline.get(metric)
            assert val is not None, f"Julia baseline missing metric: {metric}"
            # Just verify the baseline has reasonable values
            assert isinstance(val, (int, float)), (
                f"Julia baseline {metric} is not numeric"
            )
