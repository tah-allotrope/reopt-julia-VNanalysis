"""
Layer 3: Cross-Validation - Julia vs Python

Ensures both modules produce identical preprocessed dicts from the same input.
Runs the Julia export_processed_dict.jl helper via subprocess, then compares
the output against Python's apply_vietnam_defaults on the same input.

Run: python tests/cross_language/cross_validate.py
  or: pytest tests/cross_language/cross_validate.py -v

Requirements:
    - Julia installed and on PATH
    - julia --project=legacy/julia works from REPO_ROOT
    - No solver or API key needed
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.preprocess import (
    apply_vietnam_defaults,
    build_vietnam_tariff,
    load_vietnam_data,
)

CROSS_VALIDATE_YEAR = 2025
TOLERANCE = 1e-10

# Minimal scenario used by both Julia and Python - must be identical
MINIMAL_SCENARIO = {
    "Site": {"latitude": 10.8, "longitude": 106.6},
    "ElectricLoad": {"doe_reference_name": "Hospital", "annual_kwh": 1_000_000},
    "PV": {"max_kw": 500},
    "Wind": {"max_kw": 200},
    "ElectricStorage": {"max_kw": 200, "max_kwh": 800},
    "Generator": {"max_kw": 100},
}

REGIME_CASES = [
    "decision_963_2026_current",
    "decision_14_2025_legacy",
    "decree57_rooftop_50pct_draft",
    "decree146_two_part_trial_2026",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _python_process(d: dict, regime_id: str) -> dict:
    """Apply Vietnam defaults in Python with fixed parameters."""
    vn = load_vietnam_data()

    apply_vietnam_defaults(
        d,
        vn,
        customer_type="industrial",
        voltage_level="medium_voltage_22kv_to_110kv",
        region="south",
        pv_type="rooftop",
        wind_type="onshore",
        financial_profile="standard",
        regime_id=regime_id,
        currency="USD",
        exchange_rate=26400.0,
    )

    # Rebuild tariff with fixed year for reproducibility (overwrite the one from apply_vietnam_defaults)
    tariff_dict = build_vietnam_tariff(
        vn,
        "industrial",
        "medium_voltage_22kv_to_110kv",
        regime_id=regime_id,
        exchange_rate=26400.0,
        year=CROSS_VALIDATE_YEAR,
    )
    for k, v in tariff_dict.items():
        d["ElectricTariff"][k] = v

    return d


def _julia_process(input_path: str, output_path: str, regime_id: str) -> dict:
    """Run Julia export_processed_dict.jl and return the output dict."""
    julia_script = str(REPO_ROOT / "legacy" / "julia" / "tests" / "export_processed_dict.jl")

    cmd = [
        "julia",
        f"--project={REPO_ROOT / 'legacy' / 'julia'}",
        julia_script,
        str(input_path),
        str(output_path),
        str(CROSS_VALIDATE_YEAR),
        regime_id,
    ]

    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Julia export_processed_dict.jl failed (exit {result.returncode}).\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    with open(output_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _compare_values(py_val, jl_val, path: str, diffs: list, tol: float = TOLERANCE):
    """Recursively compare two values, collecting differences."""
    if isinstance(py_val, dict) and isinstance(jl_val, dict):
        all_keys = set(py_val.keys()) | set(jl_val.keys())
        for k in sorted(all_keys):
            if k not in py_val:
                diffs.append(f"  {path}.{k}: missing in Python")
            elif k not in jl_val:
                diffs.append(f"  {path}.{k}: missing in Julia")
            else:
                _compare_values(py_val[k], jl_val[k], f"{path}.{k}", diffs, tol)
    elif isinstance(py_val, list) and isinstance(jl_val, list):
        if len(py_val) != len(jl_val):
            diffs.append(
                f"  {path}: length mismatch (Python={len(py_val)}, Julia={len(jl_val)})"
            )
        else:
            for i in range(len(py_val)):
                _compare_values(py_val[i], jl_val[i], f"{path}[{i}]", diffs, tol)
    elif isinstance(py_val, (int, float)) and isinstance(jl_val, (int, float)):
        if abs(float(py_val) - float(jl_val)) > tol:
            diffs.append(
                f"  {path}: Python={py_val}, Julia={jl_val}, diff={abs(float(py_val) - float(jl_val)):.2e}"
            )
    elif isinstance(py_val, bool) and isinstance(jl_val, bool):
        if py_val != jl_val:
            diffs.append(f"  {path}: Python={py_val}, Julia={jl_val}")
    elif type(py_val) is not type(jl_val):
        # Type mismatch - but allow int/float cross-comparison (handled above)
        # and bool vs int (Julia JSON may serialize bools as true/false)
        if isinstance(py_val, bool) or isinstance(jl_val, bool):
            if bool(py_val) != bool(jl_val):
                diffs.append(
                    f"  {path}: type/value mismatch Python={py_val!r}, Julia={jl_val!r}"
                )
        elif isinstance(py_val, (int, float)) and isinstance(jl_val, (int, float)):
            if abs(float(py_val) - float(jl_val)) > tol:
                diffs.append(f"  {path}: Python={py_val}, Julia={jl_val}")
        else:
            diffs.append(
                f"  {path}: type mismatch Python={type(py_val).__name__}({py_val!r}), Julia={type(jl_val).__name__}({jl_val!r})"
            )
    elif py_val != jl_val:
        diffs.append(f"  {path}: Python={py_val!r}, Julia={jl_val!r}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCrossValidation:
    """Layer 3: Verify Julia and Python produce identical processed dicts."""

    @pytest.mark.parametrize("regime_id", REGIME_CASES)
    def test_dict_equality(self, tmp_path, regime_id):
        """All values in the processed dicts must match within floating-point tolerance."""
        input_path = tmp_path / f"{regime_id}_input.json"
        jl_output_path = tmp_path / f"{regime_id}_julia_output.json"
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(MINIMAL_SCENARIO, f, indent=2)

        import copy

        py_dict = _python_process(copy.deepcopy(MINIMAL_SCENARIO), regime_id)
        jl_dict = _julia_process(str(input_path), str(jl_output_path), regime_id)
        diffs = []
        _compare_values(py_dict, jl_dict, "root", diffs)

        if diffs:
            diff_report = "\n".join(diffs[:50])  # cap at 50 diffs
            total = len(diffs)
            pytest.fail(
                f"Julia vs Python dict mismatch for {regime_id} ({total} differences):\n{diff_report}"
            )

    @pytest.mark.parametrize("regime_id", REGIME_CASES)
    def test_tariff_array_equality(self, tmp_path, regime_id):
        """Energy rate series must be identical between Julia and Python."""
        input_path = tmp_path / f"{regime_id}_input.json"
        jl_output_path = tmp_path / f"{regime_id}_julia_output.json"
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(MINIMAL_SCENARIO, f, indent=2)

        import copy

        py_dict = _python_process(copy.deepcopy(MINIMAL_SCENARIO), regime_id)
        jl_dict = _julia_process(str(input_path), str(jl_output_path), regime_id)

        py_rates = py_dict["ElectricTariff"]["tou_energy_rates_per_kwh"]
        jl_rates = jl_dict["ElectricTariff"]["tou_energy_rates_per_kwh"]

        assert len(py_rates) == len(jl_rates) == 8760

        max_diff = 0.0
        diff_count = 0
        for i in range(8760):
            diff = abs(float(py_rates[i]) - float(jl_rates[i]))
            if diff > TOLERANCE:
                diff_count += 1
                max_diff = max(max_diff, diff)

        assert diff_count == 0, (
            f"Tariff arrays differ at {diff_count} hours, max diff = {max_diff:.2e}"
        )

    @pytest.mark.parametrize("regime_id", REGIME_CASES)
    def test_emissions_array_equality(self, tmp_path, regime_id):
        """Emissions factor series must be identical between Julia and Python."""
        input_path = tmp_path / f"{regime_id}_input.json"
        jl_output_path = tmp_path / f"{regime_id}_julia_output.json"
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(MINIMAL_SCENARIO, f, indent=2)

        import copy

        py_dict = _python_process(copy.deepcopy(MINIMAL_SCENARIO), regime_id)
        jl_dict = _julia_process(str(input_path), str(jl_output_path), regime_id)

        py_ef = py_dict["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"]
        jl_ef = jl_dict["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"]

        assert len(py_ef) == len(jl_ef) == 8760

        for i in range(8760):
            assert abs(float(py_ef[i]) - float(jl_ef[i])) <= TOLERANCE, (
                f"Emissions differ at hour {i}: Python={py_ef[i]}, Julia={jl_ef[i]}"
            )

    @pytest.mark.parametrize("regime_id", REGIME_CASES)
    def test_financial_values_match(self, tmp_path, regime_id):
        """Financial block values must match exactly."""
        input_path = tmp_path / f"{regime_id}_input.json"
        jl_output_path = tmp_path / f"{regime_id}_julia_output.json"
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(MINIMAL_SCENARIO, f, indent=2)

        import copy

        py_dict = _python_process(copy.deepcopy(MINIMAL_SCENARIO), regime_id)
        jl_dict = _julia_process(str(input_path), str(jl_output_path), regime_id)

        py_fin = py_dict["Financial"]
        jl_fin = jl_dict["Financial"]

        for key in py_fin:
            assert key in jl_fin, f"Financial.{key} missing in Julia output"
            py_val = py_fin[key]
            jl_val = jl_fin[key]
            if isinstance(py_val, (int, float)):
                assert abs(float(py_val) - float(jl_val)) <= TOLERANCE, (
                    f"Financial.{key}: Python={py_val}, Julia={jl_val}"
                )

    @pytest.mark.parametrize("regime_id", REGIME_CASES)
    def test_tech_costs_match(self, tmp_path, regime_id):
        """Tech cost values must match for all tech blocks."""
        input_path = tmp_path / f"{regime_id}_input.json"
        jl_output_path = tmp_path / f"{regime_id}_julia_output.json"
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(MINIMAL_SCENARIO, f, indent=2)

        import copy

        py_dict = _python_process(copy.deepcopy(MINIMAL_SCENARIO), regime_id)
        jl_dict = _julia_process(str(input_path), str(jl_output_path), regime_id)

        for tech in ["PV", "Wind", "ElectricStorage", "Generator"]:
            py_tech = py_dict[tech]
            jl_tech = jl_dict[tech]

            for key in py_tech:
                if key not in jl_tech:
                    continue  # some keys may differ (e.g., list vs dict handling)
                py_val = py_tech[key]
                jl_val = jl_tech[key]
                if isinstance(py_val, (int, float)) and isinstance(
                    jl_val, (int, float)
                ):
                    assert abs(float(py_val) - float(jl_val)) <= TOLERANCE, (
                        f"{tech}.{key}: Python={py_val}, Julia={jl_val}"
                    )
                elif isinstance(py_val, bool) and isinstance(jl_val, bool):
                    assert py_val == jl_val, (
                        f"{tech}.{key}: Python={py_val}, Julia={jl_val}"
                    )

    @pytest.mark.parametrize("regime_id", REGIME_CASES)
    def test_export_rules_match(self, tmp_path, regime_id):
        """Export rule settings must match between Julia and Python."""
        input_path = tmp_path / f"{regime_id}_input.json"
        jl_output_path = tmp_path / f"{regime_id}_julia_output.json"
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(MINIMAL_SCENARIO, f, indent=2)

        import copy

        py_dict = _python_process(copy.deepcopy(MINIMAL_SCENARIO), regime_id)
        jl_dict = _julia_process(str(input_path), str(jl_output_path), regime_id)

        py_et = py_dict["ElectricTariff"]
        jl_et = jl_dict["ElectricTariff"]

        for key in ["wholesale_rate", "export_rate_beyond_net_metering_limit"]:
            assert abs(float(py_et[key]) - float(jl_et[key])) <= TOLERANCE, (
                f"ElectricTariff.{key}: Python={py_et[key]}, Julia={jl_et[key]}"
            )

        for key in [
            "can_net_meter",
            "can_wholesale",
            "can_export_beyond_nem_limit",
            "can_curtail",
        ]:
            assert py_dict["PV"][key] == jl_dict["PV"][key], (
                f"PV.{key}: Python={py_dict['PV'][key]}, Julia={jl_dict['PV'][key]}"
            )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import copy

    print("=" * 60)
    print("Layer 3: Cross-Validation - Julia vs Python")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        input_path = tmp_dir / "input.json"
        jl_output_path = tmp_dir / "julia_output.json"

        # Write shared input
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(MINIMAL_SCENARIO, f, indent=2)

        # Python processing
        print("\n[1/2] Running Python processing...")
        for regime_id in REGIME_CASES:
            print(f"\n[1/3] Running Python processing for {regime_id}...")
            py_input = copy.deepcopy(MINIMAL_SCENARIO)
            py_dict = _python_process(py_input, regime_id)
            print(f"  Python dict keys: {sorted(py_dict.keys())}")

            print(f"\n[2/3] Running Julia processing for {regime_id}...")
            try:
                jl_dict = _julia_process(str(input_path), str(jl_output_path), regime_id)
                print(f"  Julia dict keys: {sorted(jl_dict.keys())}")
            except RuntimeError as e:
                print(f"  ERROR: {e}")
                sys.exit(1)

            print(f"\n[3/3] Comparing outputs for {regime_id}...")
            diffs = []
            _compare_values(py_dict, jl_dict, "root", diffs)

            if diffs:
                print(f"\n[FAIL] {len(diffs)} differences found for {regime_id}:")
                for d in diffs[:30]:
                    print(d)
                if len(diffs) > 30:
                    print(f"  ... and {len(diffs) - 30} more")
                sys.exit(1)

            print("  [PASS] All values match within tolerance (1e-10)")
            py_rates = py_dict["ElectricTariff"]["tou_energy_rates_per_kwh"]
            jl_rates = jl_dict["ElectricTariff"]["tou_energy_rates_per_kwh"]
            max_diff = max(abs(float(a) - float(b)) for a, b in zip(py_rates, jl_rates))
            print(f"  Tariff array max diff: {max_diff:.2e}")
            print(f"  Tariff array length: Python={len(py_rates)}, Julia={len(jl_rates)}")

    print("\n[PASS] Layer 3: Cross-validation complete.")
