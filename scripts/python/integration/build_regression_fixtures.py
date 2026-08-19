"""Build reduced regression fixtures from git-ignored artifacts (PHASE-06).

Reads the full artificats when present on a developer machine and writes
small, gzipped, tracked fixtures containing only the series and scalars the
tests consume. Exits 2 with a clear message when a required source is missing.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def build_ninhsim_fixture(source: Path, dest: Path) -> dict[str, int]:
    data = json.loads(source.read_text(encoding="utf-8"))
    ledger = data.get("hourly_ledger", [])
    out = {
        "load_kwh": [e["load_kwh"] for e in ledger],
        "contracted_generation_kwh": [e["contracted_generation_kwh"] for e in ledger],
        "market_reference_price_vnd_per_kwh": [e["market_reference_price_vnd_per_kwh"] for e in ledger],
        "evn_retail_rate_vnd_per_kwh": [e["evn_retail_rate_vnd_per_kwh"] for e in ledger],
        "parameters": data.get("parameters", {}),
        "summary": data.get("summary", {}),
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(dest, "wt", encoding="utf-8") as fh:
        json.dump(out, fh)
    return {"rows": len(ledger), "bytes": dest.stat().st_size}


def build_saigon18_fixture(settlement: Path, reopt: Path, dest: Path) -> dict[str, int]:
    s_data = json.loads(settlement.read_text(encoding="utf-8"))
    r_data = json.loads(reopt.read_text(encoding="utf-8"))
    pv = r_data.get("PV", {})
    storage = r_data.get("ElectricStorage", {})
    pv_to_load = pv.get("electric_to_load_series_kw", [])
    bess_to_load = storage.get("storage_to_load_series_kw", [])
    out = {
        "pv_electric_to_load_series_kw": [float(v) for v in pv_to_load[:8760]],
        "storage_to_load_series_kw": [float(v) for v in bess_to_load[:8760]],
        "delivery_factor": s_data.get("delivery_factor"),
        "strike_price_vnd_per_kwh": s_data.get("strike_price_vnd_per_kwh"),
        "total_q_kwh": s_data.get("total_q_kwh"),
        "total_settlement_vnd": s_data.get("total_settlement_vnd"),
    }
    # Preserve additional fields needed by tests: hours_with_settlement
    out["hours_with_settlement"] = s_data.get("hours_with_settlement")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(dest, "wt", encoding="utf-8") as fh:
        json.dump(out, fh)
    return {"rows": 8760, "bytes": dest.stat().st_size}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build reduced regression fixtures.")
    parser.add_argument("--ninhsim-source", type=Path, default=REPO_ROOT / "artifacts" / "reports" / "ninhsim" / "2026-04-14_ninhsim_dppa-case-2_buyer-settlement.json")
    parser.add_argument("--ninhsim-dest", type=Path, default=REPO_ROOT / "tests" / "fixtures" / "regression" / "ninhsim_case2_settlement.json.gz")
    parser.add_argument("--saigon18-settlement", type=Path, default=REPO_ROOT / "artifacts" / "reports" / "saigon18" / "2026-03-29_scenario-d_dppa-settlement.json")
    parser.add_argument("--saigon18-reopt", type=Path, default=REPO_ROOT / "artifacts" / "results" / "saigon18" / "2026-03-20_scenario-d_dppa-baseline_reopt-results.json")
    parser.add_argument("--saigon18-dest", type=Path, default=REPO_ROOT / "tests" / "fixtures" / "regression" / "saigon18_scenario_d.json.gz")
    args = parser.parse_args(argv)

    try:
        if not args.ninhsim_source.exists():
            print(f"missing ninhsim source: {args.ninhsim_source}", file=sys.stderr)
            return 2
        res = build_ninhsim_fixture(args.ninhsim_source, args.ninhsim_dest)
        print(f"ninhsim fixture: {res}")

        if not args.saigon18_settlement.exists():
            print(f"missing saigon18 settlement: {args.saigon18_settlement}", file=sys.stderr)
            return 2
        if not args.saigon18_reopt.exists():
            print(f"missing saigon18 reopt: {args.saigon18_reopt}", file=sys.stderr)
            return 2
        res2 = build_saigon18_fixture(args.saigon18_settlement, args.saigon18_reopt, args.saigon18_dest)
        print(f"saigon18 fixture: {res2}")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
