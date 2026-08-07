"""Run the Ninhsim DPPA Case 1 fuller PySAM PVWatts+battery workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.bridge import build_dppa_case_1_pvwatts_inputs
from reopt_pysam_vn.integration.dppa_case_1 import (
    build_dppa_case_1_placeholder_pysam_results,
    build_dppa_case_1_reopt_summary,
)
from reopt_pysam_vn.pysam import (
    DEFAULT_SOLAR_RESOURCE_FILE,
    ensure_solar_resource_file,
    run_pvwatts_battery_single_owner_model,
)

DEFAULT_REOPT = (
    REPO_ROOT
    / "artifacts"
    / "results"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1_reopt-results.json"
)
DEFAULT_SCENARIO = (
    REPO_ROOT
    / "scenarios"
    / "case_studies"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1.json"
)
DEFAULT_EXTRACTED = (
    REPO_ROOT / "data" / "interim" / "ninhsim" / "ninhsim_extracted_inputs.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "reports"
    / "ninhsim"
    / "2026-04-09_ninhsim_dppa-case-1_pysam-results.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Ninhsim DPPA Case 1 fuller PySAM PVWatts+battery workflow"
    )
    parser.add_argument("--reopt", type=Path, default=DEFAULT_REOPT)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--solar-resource-file",
        type=Path,
        default=DEFAULT_SOLAR_RESOURCE_FILE,
        help="Use an existing cached solar resource file when present",
    )
    parser.add_argument(
        "--force-download-resource",
        action="store_true",
        help="Force a fresh NSRDB/Himawari resource fetch instead of reusing cache",
    )
    args = parser.parse_args()

    extracted = _load_json(args.extracted)
    reopt_results = _load_json(args.reopt)
    scenario = _load_json(args.scenario)
    if float(reopt_results.get("ElectricStorage", {}).get("size_kw") or 0.0) <= 0.0:
        summary = build_dppa_case_1_reopt_summary(reopt_results, extracted, scenario)
        results = build_dppa_case_1_placeholder_pysam_results(summary)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"DPPA Case 1 PySAM artifact written to: {args.output}")
        print("  PySAM status          : skipped (REopt selected zero battery)")
        return

    site = extracted["site"]
    resolved_resource = ensure_solar_resource_file(
        latitude=float(site["latitude"]),
        longitude=float(site["longitude"]),
        force_download=bool(args.force_download_resource),
        cached_resource_file=args.solar_resource_file,
    )

    inputs = build_dppa_case_1_pvwatts_inputs(
        reopt_results=reopt_results,
        scenario=scenario,
        extracted=extracted,
        solar_resource_file=str(resolved_resource),
    )
    results = run_pvwatts_battery_single_owner_model(inputs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"DPPA Case 1 PySAM artifact written to: {args.output}")
    print(f"  Solar resource        : {resolved_resource}")


if __name__ == "__main__":
    main()
