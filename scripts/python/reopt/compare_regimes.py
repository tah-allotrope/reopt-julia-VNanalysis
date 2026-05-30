"""CLI: rapid regulatory-regime comparison for a factory load (GAP-05, PHASE-02).

Compares a factory's annual EVN bill (and optional solar/BESS value) under two
regulatory regimes — Python-only, no Julia/REopt solve — and writes a JSON artifact.

Example:
    python scripts/python/reopt/compare_regimes.py \
        --factory scenarios/case_studies/ninhsim/NinhsimSample.csv \
        --regime-a decision_963_2026_current \
        --regime-b decision_14_2025_legacy \
        --customer-type industrial \
        --voltage-level medium_voltage_22kv_to_110kv \
        --output artifacts/reports/ninhsim_regime_comparison.json
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.ingestion.loader import ingest_factory_load  # noqa: E402
from reopt_pysam_vn.reopt.regime_impact import build_regime_comparison  # noqa: E402


def _load_series(path: str) -> list:
    """Load an 8760-hour kW series from a factory file (CSV/XLSX/JSON) via the ingestion module."""
    result = ingest_factory_load(path)
    return result.loads_kw


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare a factory load under two Vietnam regulatory regimes."
    )
    parser.add_argument("--factory", required=True, help="Path to factory load file (CSV/XLSX/JSON).")
    parser.add_argument("--regime-a", required=True, help="Baseline regime id (the 'from' side).")
    parser.add_argument("--regime-b", required=True, help="Comparison regime id (the 'to' side).")
    parser.add_argument("--customer-type", default="industrial", help="industrial | commercial.")
    parser.add_argument(
        "--voltage-level",
        default="medium_voltage_22kv_to_110kv",
        help="Voltage level key, e.g. medium_voltage_22kv_to_110kv.",
    )
    parser.add_argument("--solar-profile", default=None, help="Optional path to an 8760 PV kW profile file.")
    parser.add_argument("--bess-power", type=float, default=None, help="Optional BESS power (kW).")
    parser.add_argument(
        "--bess-capacity",
        type=float,
        default=None,
        help="Optional BESS energy capacity (kWh). Defaults to bess-power x 4h if power is set.",
    )
    parser.add_argument("--year", type=int, default=None, help="Calendar year for the 8760 schedule.")
    parser.add_argument("--output", default=None, help="Path to write the JSON artifact.")
    args = parser.parse_args(argv)

    loads = _load_series(args.factory)

    pv = _load_series(args.solar_profile) if args.solar_profile else None

    bess_power = args.bess_power
    bess_capacity = args.bess_capacity
    if bess_power is not None and bess_capacity is None:
        bess_capacity = bess_power * 4.0  # default 4-hour duration

    artifact = build_regime_comparison(
        loads,
        args.regime_a,
        args.regime_b,
        args.customer_type,
        args.voltage_level,
        pv_profile_kw=pv,
        bess_power_kw=bess_power,
        bess_capacity_kwh=bess_capacity,
        year=args.year,
    )
    payload = artifact.to_dict()

    impact = artifact.regime_impact
    print(f"Regime A: {impact.regime_a.id} -> {impact.regime_a.annual_bill_vnd:,.0f} VND")
    print(f"Regime B: {impact.regime_b.id} -> {impact.regime_b.annual_bill_vnd:,.0f} VND")
    print(
        f"Bill delta (A->B): {impact.delta.annual_bill_delta_vnd:,.0f} VND "
        f"({impact.delta.delta_pct:+.2f}%), peak_hours_changed={impact.delta.peak_hours_changed}"
    )
    if artifact.solar is not None:
        print(
            f"Solar avoided-cost delta (A->B): {artifact.solar.delta_value_vnd:,.0f} VND "
            f"({artifact.solar.delta_pct:+.2f}%)"
        )
    if artifact.bess is not None:
        print(
            f"BESS arbitrage cycles/day A={artifact.bess.regime_a_cycles_per_day} "
            f"B={artifact.bess.regime_b_cycles_per_day}; "
            f"annual delta (A->B): {artifact.bess.delta_annual_arbitrage_vnd:,.0f} VND"
        )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote artifact: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
