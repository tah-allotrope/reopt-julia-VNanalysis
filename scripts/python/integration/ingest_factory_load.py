"""CLI entrypoint for generic factory load ingestion.

Usage:
    python scripts/python/integration/ingest_factory_load.py \
        --input scenarios/case_studies/ninhsim/NinhsimSample.csv \
        --output data/interim/test/test_ingestion.json \
        --year 2024
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.ingestion import (
    ingest_factory_load,
    extract_load_metadata,
    classify_tou_consumption,
    classify_industry_archetype,
)


def build_artifact(
    input_path: str,
    project_name: str | None = None,
    customer_type: str = "industrial",
    voltage_level: str = "medium_voltage_22kv_to_110kv",
    region: str = "south",
    year: int = 2024,
    column_hint: str | None = None,
    sheet_name: str | None = None,
) -> dict:
    result = ingest_factory_load(
        input_path,
        column_hint=column_hint,
        sheet_name=sheet_name,
    )

    meta = extract_load_metadata(result.loads_kw, year=year)

    try:
        vn = None
        from reopt_pysam_vn.reopt.preprocess import load_vietnam_data
        vn = load_vietnam_data()
    except Exception:
        pass

    tou = classify_tou_consumption(
        result.loads_kw,
        customer_type=customer_type,
        voltage_level=voltage_level,
        year=year,
        vn=vn,
    )

    archetype = classify_industry_archetype(result.loads_kw, year=year)

    if not project_name:
        project_name = Path(input_path).stem

    return {
        "_meta": {
            "generator": "ingest_factory_load.py",
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_path": str(input_path),
            "source_format": result.source_format,
            "detected_column": result.detected_column,
            "synthesis_method": result.synthesis_method,
        },
        "site": {
            "region": region,
            "voltage_level": voltage_level,
            "customer_type": customer_type,
        },
        "loads_kw": result.loads_kw,
        "metadata": {
            "project_name": project_name,
            "data_year": year,
            "peak_demand_kw": round(meta.peak_demand_kw, 1),
            "annual_consumption_mwh": round(meta.annual_consumption_mwh, 1),
            "average_demand_kw": round(meta.average_demand_kw, 1),
            "load_factor": round(meta.load_factor, 4),
            "min_demand_kw": round(meta.min_demand_kw, 1),
            "daytime_avg_kw": round(meta.daytime_avg_kw, 1),
            "nighttime_avg_kw": round(meta.nighttime_avg_kw, 1),
            "weekend_avg_kw": round(meta.weekend_avg_kw, 1),
            "weekday_avg_kw": round(meta.weekday_avg_kw, 1),
        },
        "cleaning": result.cleaning_summary,
        "classification": {
            "archetype": archetype.archetype,
            "confidence": archetype.confidence,
            "weekend_weekday_ratio": archetype.weekend_weekday_ratio,
            "night_day_ratio": archetype.night_day_ratio,
            "peak_concentration": archetype.peak_concentration,
            "tou": {
                "regime_id": tou.regime_id,
                "peak_consumption_mwh": round(tou.peak_consumption_mwh, 1),
                "offpeak_consumption_mwh": round(tou.offpeak_consumption_mwh, 1),
                "normal_consumption_mwh": round(tou.normal_consumption_mwh, 1),
                "peak_share_pct": round(tou.peak_share_pct, 2),
                "offpeak_share_pct": round(tou.offpeak_share_pct, 2),
                "normal_share_pct": round(tou.normal_share_pct, 2),
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Ingest factory load data and produce a standardized JSON artifact."
    )
    parser.add_argument("--input", required=True, help="Path to input file (CSV, XLSX, or JSON)")
    parser.add_argument("--output", required=True, help="Path for output JSON artifact")
    parser.add_argument("--column", default=None, help="Explicit load column name")
    parser.add_argument("--sheet", default=None, help="XLSX sheet name")
    parser.add_argument("--year", type=int, default=2024, help="Data year (default: 2024)")
    parser.add_argument("--project-name", default=None, help="Project name for artifact")
    parser.add_argument("--customer-type", default="industrial", help="Customer type")
    parser.add_argument("--voltage-level", default="medium_voltage_22kv_to_110kv", help="Voltage level")
    parser.add_argument("--region", default="south", help="Region (north/central/south)")

    args = parser.parse_args()

    artifact = build_artifact(
        input_path=args.input,
        project_name=args.project_name,
        customer_type=args.customer_type,
        voltage_level=args.voltage_level,
        region=args.region,
        year=args.year,
        column_hint=args.column,
        sheet_name=args.sheet,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)

    meta = artifact["metadata"]
    cls = artifact["classification"]
    print(f"Ingested: {args.input}")
    print(f"  Peak demand: {meta['peak_demand_kw']:,.0f} kW")
    print(f"  Annual consumption: {meta['annual_consumption_mwh']:,.0f} MWh")
    print(f"  Load factor: {meta['load_factor']:.3f}")
    print(f"  Archetype: {cls['archetype']} ({cls['confidence']})")
    print(f"  TOU peak share: {cls['tou']['peak_share_pct']:.1f}%")
    print(f"  Synthesis: {artifact['_meta']['synthesis_method']}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
