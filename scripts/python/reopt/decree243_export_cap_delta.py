"""Decree 243/2026 export-cap delta memo (20% -> 50%, effective 2026-06-26).

Thin CLI over reopt_pysam_vn.reopt.decree243_delta. Quantifies, on a fixed
dispatch (no re-optimization), the first-order effect of the Decree 243/2026
rooftop-solar surplus export-cap change on a tracked golden REopt solve, and
writes a markdown memo. See
plans/2026-07-18-decree-243-currency-webapp-hardening-plan.md PHASE-03.

Usage:
    .venv/Scripts/python.exe scripts/python/reopt/decree243_export_cap_delta.py \
        --results-json examples/saigon18_scenario-a_reopt-solve.example.json \
        --out-md reports/2026-07-18-decree243-export-cap-delta.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.decree243_delta import (
    compute_export_cap_delta,
    extract_saigon18_series,
)

DEFAULT_RESULTS_JSON = REPO_ROOT / "examples" / "saigon18_scenario-a_reopt-solve.example.json"
DEFAULT_OUT_MD = REPO_ROOT / "reports" / "2026-07-18-decree243-export-cap-delta.md"
DEFAULT_EXCHANGE_RATE = 26_400.0


def build_memo(results_json_path: Path, delta: dict, exchange_rate: float) -> str:
    return f"""# Decree 243/2026 Export-Cap Delta — Fixed-Dispatch First-Order Estimate

**Date:** 2026-07-18
**Input:** `{results_json_path.relative_to(REPO_ROOT).as_posix()}`
**Method:** `reopt_pysam_vn.reopt.decree243_delta.compute_export_cap_delta`

## Caveat

This is a **fixed-dispatch** comparison: the underlying REopt solve was not
re-optimized under the new 50% cap. It answers "given the PV/BESS sizing and
dispatch REopt already chose under the old 20%-cap assumption, how much more
of the *already-curtailed* surplus becomes exportable under Decree 243/2026's
50% cap" — a **lower bound** on the true benefit. A re-optimized solve under
the 50% cap would likely size PV larger and could capture additional value;
that re-optimization is flagged as follow-on work, not performed here.

## Presets compared

- **Decree 57/2025 (legacy, 20% cap):** `decree57_private_wire_standard`
- **Decree 243/2026 (active, 50% cap):** `decree243_export_50pct_standard`

Both are `private_wire` mode, `strike_vnd_kwh=1012.0`,
`excess_treatment="export_at_surplus"`, `surplus_rate_vnd_kwh=671.0` — the
only difference is `export_cap_pct` (20.0 vs 50.0).

## Results (annual)

| Metric | 20% cap (Decree 57) | 50% cap (Decree 243) | Delta |
|---|---:|---:|---:|
| Exported energy (kWh/yr) | {delta['exported_kwh_cap20']:,.0f} | {delta['exported_kwh_cap50']:,.0f} | {delta['delta_exported_kwh']:,.0f} |
| Curtailed energy (kWh/yr) | {delta['curtailed_kwh_cap20']:,.0f} | {delta['curtailed_kwh_cap50']:,.0f} | {delta['curtailed_kwh_cap50'] - delta['curtailed_kwh_cap20']:,.0f} |
| Surplus revenue (VND/yr) | {delta['surplus_revenue_vnd_cap20']:,.0f} | {delta['surplus_revenue_vnd_cap50']:,.0f} | {delta['delta_surplus_revenue_vnd']:,.0f} |

**Headline: Decree 243/2026's 50% cap is worth an additional
{delta['delta_surplus_revenue_vnd']:,.0f} VND/yr (~{delta['delta_surplus_revenue_usd']:,.0f} USD/yr at
{exchange_rate:,.0f} VND/USD) in surplus export revenue on this fixed dispatch,
before any re-optimization.**

## Reproduce

```
.venv/Scripts/python.exe scripts/python/reopt/decree243_export_cap_delta.py
```
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decree 243/2026 export-cap delta memo (fixed dispatch, no re-optimization)."
    )
    parser.add_argument(
        "--results-json",
        type=Path,
        default=DEFAULT_RESULTS_JSON,
        help="REopt results JSON to read the fixed dispatch from.",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=DEFAULT_OUT_MD,
        help="Output markdown memo path.",
    )
    parser.add_argument(
        "--exchange-rate",
        type=float,
        default=DEFAULT_EXCHANGE_RATE,
        help="VND per USD exchange rate for the USD delta figure.",
    )
    args = parser.parse_args()

    series = extract_saigon18_series(
        args.results_json, exchange_rate_vnd_per_usd=args.exchange_rate
    )
    delta = compute_export_cap_delta(
        series["loads_kw"],
        series["generation_kw"],
        series["tariff_vnd_per_kwh"],
        exchange_rate_vnd_per_usd=args.exchange_rate,
    )

    memo = build_memo(args.results_json, delta, args.exchange_rate)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(memo, encoding="utf-8")

    print(f"Wrote {args.out_md}")
    print(f"delta_surplus_revenue_vnd = {delta['delta_surplus_revenue_vnd']:,.0f}")
    print(f"delta_surplus_revenue_usd = {delta['delta_surplus_revenue_usd']:,.0f}")


if __name__ == "__main__":
    main()
