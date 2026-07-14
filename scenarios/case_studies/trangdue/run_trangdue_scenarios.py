"""Solve the two Trang Due validation scenarios (PHASE-02 of
plans/2026-07-14-hai-phong-jv-year-one-financials-plan.md, cpi workspace):

  1. Archetype: 1,200 kWp solar-only, Mid-size-B load (3,000,000 kWh/yr).
  2. Flagship: Green Works, 1,999 kWp PV + 1,000 kW / 2,000 kWh BESS,
     load 8,923,200 kWh/yr (~743,600 kWh/month).

Fixed sizing (min_kw == max_kw) so REopt validates yield/dispatch for the
named capacities rather than re-optimizing size. Solves via the NREL REopt
public API (run_vietnam_reopt), reading credentials from NREL_API.env.
Vietnam defaults: customer_type="industrial", region="north" (Trang Due,
Hai Phong — approx. 20.844N, 106.552E).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.preprocess import (  # noqa: E402
    apply_vietnam_defaults,
    load_vietnam_data,
    run_vietnam_reopt,
)

from make_loads import build_synthetic_load  # noqa: E402

TRANGDUE_LAT = 20.844
TRANGDUE_LON = 106.552

ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "results" / "trangdue"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_api_key() -> str:
    env_path = REPO_ROOT / "NREL_API.env"
    key = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("API_KEY_NAME"):
            key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        raise RuntimeError("API_KEY_NAME not found in NREL_API.env")
    return key


def build_scenario(pv_kw: float, bess_kw: float, bess_kwh: float, annual_kwh: float) -> dict:
    d = {
        "Site": {"latitude": TRANGDUE_LAT, "longitude": TRANGDUE_LON},
        "ElectricLoad": {"loads_kw": build_synthetic_load(annual_kwh), "year": 2025},
        "PV": {"min_kw": pv_kw, "max_kw": pv_kw},
    }
    if bess_kw > 0:
        d["ElectricStorage"] = {
            "min_kw": bess_kw,
            "max_kw": bess_kw,
            "min_kwh": bess_kwh,
            "max_kwh": bess_kwh,
        }
    return d


def solve(name: str, d: dict, api_key: str, vn) -> dict:
    print(f"\n=== Solving {name} ===")
    results = run_vietnam_reopt(
        d,
        api_key=api_key,
        vn=vn,
        customer_type="industrial",
        region="north",
    )
    out_path = ARTIFACTS_DIR / f"2026-07-14_trangdue-{name}_reopt-results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return results


def summarize(name: str, results: dict, annual_kwh_load: float) -> dict:
    outputs = results.get("outputs", {}) if isinstance(results, dict) else {}
    pv = outputs.get("PV", {})
    storage = outputs.get("ElectricStorage", {})
    size_kw = pv.get("size_kw")
    year1_kwh = pv.get("year_one_energy_produced_kwh")
    exported_kwh = pv.get("annual_energy_exported_kwh")
    specific_yield = (year1_kwh / size_kw) if (size_kw and year1_kwh) else None
    pv_energy_as_pct_of_load = min(1.0, year1_kwh / annual_kwh_load) if year1_kwh else None
    summary = {
        "name": name,
        "pv_size_kw": size_kw,
        "pv_year1_kwh": year1_kwh,
        "pv_annual_energy_exported_kwh": exported_kwh,
        "specific_yield_kwh_per_kwp": specific_yield,
        "pv_energy_as_pct_of_load": pv_energy_as_pct_of_load,
        "bess_size_kw": storage.get("size_kw"),
        "bess_size_kwh": storage.get("size_kwh"),
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    vn = load_vietnam_data()
    api_key = _load_api_key()

    archetype_scn = build_scenario(pv_kw=1200.0, bess_kw=0.0, bess_kwh=0.0, annual_kwh=3_000_000.0)
    flagship_scn = build_scenario(pv_kw=1998.6, bess_kw=1000.0, bess_kwh=2000.0, annual_kwh=8_923_200.0)

    archetype_results = solve("archetype_1200kwp_solar", archetype_scn, api_key, vn)
    flagship_results = solve("flagship_1999kwp_bess1mw2mwh", flagship_scn, api_key, vn)

    summaries = [
        summarize("archetype", archetype_results, 3_000_000.0),
        summarize("flagship", flagship_results, 8_923_200.0),
    ]
    (ARTIFACTS_DIR / "2026-07-14_trangdue-summary.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8"
    )
