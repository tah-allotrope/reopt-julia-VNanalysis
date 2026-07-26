"""
Solve REopt scenarios via NREL API.

Reuses the existing run_vietnam_reopt() from the Python preprocess module
which POSTs to https://developer.nlr.gov/api/reopt/stable and polls for results.

Usage:
    python scripts/python/reopt/solve_via_api.py \
        --scenario scenarios/generated/tou_comparison/.../input.json \
        --output-dir artifacts/results/tou_comparison/<name>/

    python scripts/python/reopt/solve_via_api.py \
        --scenario <path> --output-dir <dir> --no-apply-defaults

Environment:
    NREL_DEVELOPER_API_KEY or NREL_API_KEY (loaded from NREL_API.env or env var)
"""

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.preprocess import (
    run_vietnam_reopt,
)


def load_api_key() -> str:
    api_key = os.environ.get("NREL_DEVELOPER_API_KEY") or os.environ.get("NREL_API_KEY")
    if api_key:
        return api_key

    env_path = REPO_ROOT / "NREL_API.env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            k, v = stripped.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"')
            if k == "API_KEY_NAME":
                return v

    raise RuntimeError(
        "NREL API key not found. Set NREL_DEVELOPER_API_KEY env var or "
        "create NREL_API.env with API_KEY_NAME=<key>"
    )


def main():
    parser = argparse.ArgumentParser(description="Solve REopt via NREL API")
    parser.add_argument("--scenario", required=True, help="Path to scenario JSON")
    parser.add_argument("--output-dir", required=True, help="Output directory for results")
    parser.add_argument("--no-apply-defaults", action="store_true",
                        help="Skip Vietnam defaults (scenario already preprocessed)")
    parser.add_argument("--customer-type", default="commercial")
    parser.add_argument("--voltage-level", default="medium_voltage_22kv_to_110kv")
    parser.add_argument("--region", default="south")
    parser.add_argument("--regime-id", default=None)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--max-polls", type=int, default=120)
    args = parser.parse_args()

    api_key = load_api_key()
    scenario_path = Path(args.scenario)
    output_dir = Path(args.output_dir)

    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_path}")

    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    apply_defaults = not args.no_apply_defaults

    if apply_defaults:
        scenario.pop("_meta", None)
        scenario.pop("_template", None)

    print(f"Solving: {scenario_path.name}")
    print("  via:    https://developer.nlr.gov/api/reopt/stable")
    print(f"  apply_defaults: {apply_defaults}")

    kwargs = {}
    if apply_defaults:
        kwargs = {
            "customer_type": args.customer_type,
            "voltage_level": args.voltage_level,
            "region": args.region,
        }
        if args.regime_id:
            kwargs["regime_id"] = args.regime_id

    results = run_vietnam_reopt(
        scenario,
        api_key=api_key,
        poll_interval=args.poll_interval,
        max_polls=args.max_polls,
        apply_defaults=apply_defaults,
        **kwargs,
    )

    # Normalize API v3 response: results may be wrapped in 'outputs' key
    normalized = results.get("outputs", results)
    if normalized is not results:
        normalized["status"] = results.get("status", "unknown")
        normalized["api_version"] = results.get("api_version")
        normalized["_api_raw"] = {
            "run_uuid": results.get("run_uuid"),
            "reopt_version": results.get("reopt_version"),
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "reopt-results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)

    print(f"\nResults saved to: {out_path}")
    status = normalized.get("status", "unknown")
    print(f"Status: {status}")

    if hasattr(normalized, "get"):
        pv = normalized.get("PV", {})
        storage = results.get("ElectricStorage", {})
        fin = results.get("Financial", {})
        if pv:
            print(f"PV:   {pv.get('size_kw', 'N/A'):>10} kW  year-1: {pv.get('year_one_energy_produced_kwh', 'N/A')} kWh")
        if storage:
            print(f"BESS: {storage.get('size_kw', 'N/A'):>10} kW  {storage.get('size_kwh', 'N/A')} kWh")
        if fin:
            print(f"NPV:  ${fin.get('npv', 'N/A'):>10,.0f}")


if __name__ == "__main__":
    main()
