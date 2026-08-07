"""GAP-03 PHASE-03: CLI to match a factory load against the developer catalog.

Ingests a factory load file (CSV / XLSX / JSON via the GAP-01 ingestion
module), builds a FactoryProfile, scores it against every project in the
catalog, and writes a ranked match-result artifact.

Usage:
    python scripts/python/match_factory_to_projects.py \
        --factory scenarios/case_studies/ninhsim/NinhsimSample.csv \
        --region south \
        --output /tmp/matches.json --top-n 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.ingestion import ingest_factory_load
from reopt_pysam_vn.integration.matching import (
    FactoryProfile,
    build_match_artifact,
    match_projects_to_factory,
)
from reopt_pysam_vn.integration.project_catalog import load_project_catalog

DEFAULT_CATALOG = REPO_ROOT / "data" / "projects"
DEFAULT_BASELINE_USC_KWH = 7.8


def build_factory_profile(
    factory_path: str | Path,
    *,
    name: str | None = None,
    region: str = "south",
    voltage_level: str = "medium_voltage_22kv_to_110kv",
    baseline_usc_kwh: float = DEFAULT_BASELINE_USC_KWH,
    colocated_project_id: str | None = None,
    column_hint: str | None = None,
) -> FactoryProfile:
    """Ingest a factory load file and wrap it in a FactoryProfile."""
    factory_path = Path(factory_path)
    result = ingest_factory_load(factory_path, column_hint=column_hint)
    return FactoryProfile.from_loads(
        name=name or factory_path.stem,
        region=region,
        loads_kw=result.loads_kw,
        voltage_level=voltage_level,
        colocated_project_id=colocated_project_id,
        evn_baseline_usc_kwh=baseline_usc_kwh,
    )


def run(
    factory_path: str | Path,
    *,
    catalog_dir: str | Path = DEFAULT_CATALOG,
    name: str | None = None,
    region: str = "south",
    voltage_level: str = "medium_voltage_22kv_to_110kv",
    baseline_usc_kwh: float = DEFAULT_BASELINE_USC_KWH,
    colocated_project_id: str | None = None,
    column_hint: str | None = None,
    top_n: int | None = 5,
) -> dict:
    factory = build_factory_profile(
        factory_path,
        name=name,
        region=region,
        voltage_level=voltage_level,
        baseline_usc_kwh=baseline_usc_kwh,
        colocated_project_id=colocated_project_id,
        column_hint=column_hint,
    )
    catalog = load_project_catalog(catalog_dir)
    matches = match_projects_to_factory(factory, catalog)
    return build_match_artifact(
        factory, matches, catalog_size=len(catalog), top_n=top_n
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Match a factory load profile against the developer project catalog."
    )
    parser.add_argument("--factory", required=True, help="Path to factory load file (CSV/XLSX/JSON).")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Catalog directory.")
    parser.add_argument("--output", required=True, help="Output JSON artifact path.")
    parser.add_argument("--name", default=None, help="Factory display name (default: file stem).")
    parser.add_argument(
        "--region",
        default="south",
        choices=["north", "central", "south"],
        help="Factory region for geographic fit.",
    )
    parser.add_argument(
        "--voltage-level",
        default="medium_voltage_22kv_to_110kv",
        help="Factory grid voltage level.",
    )
    parser.add_argument(
        "--baseline-usc-kwh",
        type=float,
        default=DEFAULT_BASELINE_USC_KWH,
        help="Factory EVN blended baseline cost (US cents/kWh) for commercial fit.",
    )
    parser.add_argument(
        "--colocated-project-id",
        default=None,
        help="Project id the factory is physically co-located with (enables onsite private-wire).",
    )
    parser.add_argument("--column", dest="column_hint", default=None, help="Load column hint for raw files.")
    parser.add_argument("--top-n", type=int, default=5, help="Number of ranked matches to emit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifact = run(
        args.factory,
        catalog_dir=args.catalog,
        name=args.name,
        region=args.region,
        voltage_level=args.voltage_level,
        baseline_usc_kwh=args.baseline_usc_kwh,
        colocated_project_id=args.colocated_project_id,
        column_hint=args.column_hint,
        top_n=args.top_n,
    )
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    top = artifact["matches"][0] if artifact["matches"] else None
    print(f"Wrote {out_path} — {artifact['catalog_size']} projects scored, "
          f"{artifact['viable_count']} viable.")
    if top:
        print(f"Top match: {top['project_name']} ({top['overall_score']}/100)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
