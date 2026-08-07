"""
Compute DPPA CfD settlement revenue from REopt dispatch.

Reuses the fixed-size REopt dispatch from the EVN TOU solve and then adds a
DPPA top-up settlement in Python because REopt does not model Vietnam's
contract-for-difference structure directly.

Usage:
    python scripts/python/reopt/dppa_settlement.py \
        --extracted data/interim/saigon18/2026-03-20_saigon18_extracted_inputs.json \
        --reopt artifacts/results/saigon18/2026-03-20_scenario-d_dppa-baseline_reopt-results.json \
        --config data/vietnam/vn_deal_defaults_2026.json \
        --output artifacts/reports/saigon18/2026-03-26_scenario-d_dppa-settlement.json
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_exchange_rate
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

EXCHANGE_RATE_VND_PER_USD = _resolve_exchange_rate(load_vietnam_data())
DEFAULT_ANALYSIS_YEARS = 20
DEFAULT_ESCALATION = 0.05
DEFAULT_DISCOUNT_RATE = 0.08
DEFAULT_CONTRACT_TYPE = "private_wire"
DEFAULT_DELIVERY_FACTOR = 0.98
PRIVATE_WIRE_SOUTH_CEILING_VND_PER_KWH = 1_149.86


def load_deal_config(config_path: str | None) -> dict:
    """Load deal defaults from JSON config. Returns empty dict if no path."""
    if not config_path:
        return {}
    raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return raw.get("data", raw)


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) == 8760:
        return list(series)
    if len(series) > 8760:
        return list(series[:8760])
    return list(series) + [0.0] * (8760 - len(series))


def _sum_series(*series_list: list[float]) -> list[float]:
    padded = [_pad_to_8760(s) for s in series_list]
    return [sum(values) for values in zip(*padded)]


def normalize_fmp_vnd_per_kwh(fmp_series: list[float]) -> tuple[list[float], str]:
    """Normalize extracted FMP data to VND/kWh.

    The extracted Saigon18 series is labeled as VND/MWh in the workbook notes, but
    the observed values are already in the VND/kWh range (~250 to ~1,944). Treating
    them as VND/MWh would understate FMP by 1000x and inflate the settlement.
    """
    if not fmp_series:
        raise ValueError("FMP series is empty")

    max_val = max(fmp_series)
    min_val = min(fmp_series)

    if max_val > 10_000:
        return [v / 1_000.0 for v in fmp_series], "vnd_per_mwh_converted_to_vnd_per_kwh"

    if min_val >= 0 and max_val < 10_000:
        warnings.warn(
            "FMP series values already look like VND/kWh despite the extracted field "
            "name `fmp_vnd_per_mwh`; using them as-is to avoid a 1000x settlement "
            "overstatement.",
            stacklevel=2,
        )
        return list(fmp_series), "vnd_per_kwh_as_extracted"

    raise ValueError(f"Unexpected FMP value range: min={min_val}, max={max_val}")


def load_reopt_delivery_profile(results: dict) -> list[float]:
    """Extract hourly buyer delivery from the actual REopt result schema.

    Buyer delivery is PV-to-load plus storage-to-load in each hour.
    """
    pv = results.get("PV", {})
    storage = results.get("ElectricStorage", {})

    pv_to_load = pv.get("electric_to_load_series_kw", [])
    bess_to_load = storage.get("storage_to_load_series_kw", [])

    if not pv_to_load and not bess_to_load:
        warnings.warn(
            "REopt results missing PV.electric_to_load_series_kw and "
            "ElectricStorage.storage_to_load_series_kw; returning zero delivery profile.",
            stacklevel=2,
        )
        return [0.0] * 8760

    return _sum_series(pv_to_load, bess_to_load)


def compute_dppa_annual_revenue(
    q_delivered_kw: list[float],
    fmp_vnd_per_kwh: list[float],
    strike_price_vnd_per_kwh: float,
    delivery_factor: float = DEFAULT_DELIVERY_FACTOR,
    contract_type: str = DEFAULT_CONTRACT_TYPE,
    exchange_rate_vnd_per_usd: float = EXCHANGE_RATE_VND_PER_USD,
) -> dict:
    """Compute one year of DPPA CfD settlement revenue.

    `delivery_factor` is the net multiplier applied to hourly delivery before
    settlement. For this repo, it is the explicit combined delivery assumption used
    instead of undocumented `k_factor`/`kpp` spreadsheet terms.

    Contract-type settlement formulas:
      private_wire  — developer sells directly to factory at strike price;
                      no FMP exposure. Revenue = strike × net_delivery_kwh
                      per hour (all hours with non-zero delivery settle).
                      Strike must be ≤ PRIVATE_WIRE_SOUTH_CEILING_VND_PER_KWH.
      grid_connected — CfD differential: revenue = max(0, strike − FMP) ×
                      net_delivery_kwh. Settles only in hours when FMP < strike.
    """
    q_delivered_kw = _pad_to_8760(q_delivered_kw)
    fmp_vnd_per_kwh = _pad_to_8760(fmp_vnd_per_kwh)

    if contract_type not in {"private_wire", "grid_connected"}:
        raise ValueError(
            f"contract_type must be 'private_wire' or 'grid_connected', got {contract_type}"
        )

    if (
        contract_type == "private_wire"
        and strike_price_vnd_per_kwh > PRIVATE_WIRE_SOUTH_CEILING_VND_PER_KWH
    ):
        warnings.warn(
            f"Strike price {strike_price_vnd_per_kwh:.2f} VND/kWh exceeds the documented "
            f"south private-wire ceiling {PRIVATE_WIRE_SOUTH_CEILING_VND_PER_KWH:.2f} VND/kWh. "
            "This run should be interpreted as grid-connected DPPA economics unless legal "
            "confirmation says otherwise.",
            stacklevel=2,
        )

    total_settlement_vnd = 0.0
    total_q_kwh = 0.0
    hours_with_settlement = 0
    avg_spread_vnd_per_kwh = 0.0

    for q_kw, fmp in zip(q_delivered_kw, fmp_vnd_per_kwh):
        net_q_kwh = q_kw * delivery_factor
        if contract_type == "private_wire":
            # Direct sale: factory pays developer at strike for all delivered kWh.
            # No spot-market exposure; settlement is positive for every hour with
            # non-zero delivery regardless of the prevailing FMP.
            settlement_h = strike_price_vnd_per_kwh * net_q_kwh
            spread = strike_price_vnd_per_kwh  # spread = full strike (no FMP netting)
        else:
            # Grid-connected CfD: developer receives positive settlement only when
            # spot price (FMP) is below the contracted strike.
            spread = max(0.0, strike_price_vnd_per_kwh - fmp)
            settlement_h = spread * net_q_kwh
        total_settlement_vnd += settlement_h
        total_q_kwh += net_q_kwh
        avg_spread_vnd_per_kwh += spread
        if settlement_h > 0:
            hours_with_settlement += 1

    avg_settlement_vnd_per_kwh = (
        total_settlement_vnd / total_q_kwh if total_q_kwh else 0.0
    )

    return {
        "contract_type": contract_type,
        "strike_price_vnd_per_kwh": round(strike_price_vnd_per_kwh, 4),
        "delivery_factor": round(delivery_factor, 6),
        "total_settlement_vnd": round(total_settlement_vnd, 0),
        "total_settlement_usd": round(
            total_settlement_vnd / exchange_rate_vnd_per_usd, 2
        ),
        "total_q_kwh": round(total_q_kwh, 0),
        "total_q_mwh": round(total_q_kwh / 1_000.0, 2),
        "avg_settlement_vnd_per_kwh": round(avg_settlement_vnd_per_kwh, 4),
        "avg_spread_vnd_per_kwh": round(avg_spread_vnd_per_kwh / 8760.0, 4),
        "hours_with_settlement": hours_with_settlement,
        "private_wire_south_ceiling_vnd_per_kwh": PRIVATE_WIRE_SOUTH_CEILING_VND_PER_KWH,
        "exceeds_private_wire_ceiling": strike_price_vnd_per_kwh
        > PRIVATE_WIRE_SOUTH_CEILING_VND_PER_KWH,
    }


def compute_virtual_dppa_developer_revenue(
    matched_series_kw: list[float],
    generation_series_kw: list[float],
    strike_price_usd_per_kwh: float,
    fmp_usd_per_kwh: list[float],
) -> dict:
    """Compute annual developer revenue for a virtual DPPA proxy.

    Matched energy is settled at the strike price. Unmatched generation is sold
    at the market price proxy (FMP).
    """
    matched_series_kw = _pad_to_8760(matched_series_kw)
    generation_series_kw = _pad_to_8760(generation_series_kw)
    fmp_usd_per_kwh = _pad_to_8760(fmp_usd_per_kwh)

    matched_kwh = sum(max(0.0, value) for value in matched_series_kw)
    generation_kwh = sum(max(0.0, value) for value in generation_series_kw)
    unmatched_kwh = max(0.0, generation_kwh - matched_kwh)

    strike_revenue_usd = matched_kwh * strike_price_usd_per_kwh
    merchant_revenue_usd = 0.0

    if generation_kwh > 0 and unmatched_kwh > 0:
        for generation_kw, fmp in zip(generation_series_kw, fmp_usd_per_kwh):
            generation_share = max(0.0, generation_kw) / generation_kwh
            merchant_revenue_usd += unmatched_kwh * generation_share * fmp

    total_revenue_usd = strike_revenue_usd + merchant_revenue_usd

    return {
        "strike_price_usd_per_kwh": strike_price_usd_per_kwh,
        "matched_volume_mwh": matched_kwh / 1_000.0,
        "unmatched_volume_mwh": unmatched_kwh / 1_000.0,
        "total_generation_mwh": generation_kwh / 1_000.0,
        "revenue_from_matched_usd": strike_revenue_usd,
        "revenue_from_unmatched_usd": merchant_revenue_usd,
        "developer_revenue_yr1_usd": total_revenue_usd,
        "avg_realized_price_usd_per_kwh": (
            total_revenue_usd / generation_kwh if generation_kwh else 0.0
        ),
    }


def project_dppa_cashflows(
    year_one_settlement_usd: float,
    analysis_years: int = DEFAULT_ANALYSIS_YEARS,
    escalation_rate: float = DEFAULT_ESCALATION,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
) -> dict:
    annual_cashflows = [
        year_one_settlement_usd * (1 + escalation_rate) ** (year - 1)
        for year in range(1, analysis_years + 1)
    ]

    npv_usd = 0.0
    for year, cashflow in enumerate(annual_cashflows, start=1):
        npv_usd += cashflow / ((1 + discount_rate) ** year)

    return {
        "analysis_years": analysis_years,
        "escalation_rate_fraction": escalation_rate,
        "discount_rate_fraction": discount_rate,
        "annual_cashflows_usd": [round(v, 2) for v in annual_cashflows],
        "settlement_npv_usd": round(npv_usd, 2),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute DPPA CfD settlement revenue from REopt dispatch"
    )
    parser.add_argument(
        "--extracted",
        default="data/interim/saigon18/2026-03-20_saigon18_extracted_inputs.json",
        help="Extracted Excel data JSON (contains FMP series)",
    )
    parser.add_argument(
        "--reopt", required=True, help="REopt results JSON"
    )
    parser.add_argument(
        "--config",
        help="Deal defaults JSON (e.g. data/vietnam/vn_deal_defaults_2026.json). "
        "CLI args override config values.",
    )
    parser.add_argument(
        "--strike-vnd",
        type=float,
        default=None,
        dest="strike_vnd",
        help="DPPA strike price in VND/kWh (default: 1100)",
    )
    parser.add_argument(
        "--contract-type",
        choices=["private_wire", "grid_connected"],
        default=None,
        help="DPPA contract structure",
    )
    parser.add_argument(
        "--delivery-factor",
        type=float,
        default=None,
        help="Net multiplier applied to hourly buyer delivery before settlement",
    )
    parser.add_argument(
        "--analysis-years",
        type=int,
        default=None,
        help="Years used for settlement NPV projection",
    )
    parser.add_argument(
        "--escalation-rate",
        type=float,
        default=None,
        help="Annual escalation applied to settlement cash flows",
    )
    parser.add_argument(
        "--discount-rate",
        type=float,
        default=None,
        help="Discount rate used for settlement NPV",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/saigon18/2026-03-29_scenario-d_dppa-settlement.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    cfg = load_deal_config(args.config)
    dppa_cfg = cfg.get("dppa", {})
    analysis_cfg = cfg.get("analysis", {})
    xr_cfg = cfg.get("exchange_rate", {})

    strike_vnd = args.strike_vnd if args.strike_vnd is not None else dppa_cfg.get("strike_vnd_per_kwh", 1100.0)
    contract_type = args.contract_type or dppa_cfg.get("contract_type", DEFAULT_CONTRACT_TYPE)
    delivery_factor = args.delivery_factor if args.delivery_factor is not None else dppa_cfg.get("delivery_factor", DEFAULT_DELIVERY_FACTOR)
    analysis_years = args.analysis_years if args.analysis_years is not None else analysis_cfg.get("analysis_years", DEFAULT_ANALYSIS_YEARS)
    escalation_rate = args.escalation_rate if args.escalation_rate is not None else dppa_cfg.get("escalation_rate", DEFAULT_ESCALATION)
    discount_rate = args.discount_rate if args.discount_rate is not None else analysis_cfg.get("discount_rate", DEFAULT_DISCOUNT_RATE)
    exchange_rate = xr_cfg.get("vnd_per_usd", EXCHANGE_RATE_VND_PER_USD)

    extracted = json.loads(Path(args.extracted).read_text(encoding="utf-8"))
    results = json.loads(Path(args.reopt).read_text(encoding="utf-8"))

    fmp_vnd_per_kwh, fmp_units_used = normalize_fmp_vnd_per_kwh(
        extracted["fmp_vnd_per_mwh"]
    )
    q_delivered = load_reopt_delivery_profile(results)
    settlement = compute_dppa_annual_revenue(
        q_delivered_kw=q_delivered,
        fmp_vnd_per_kwh=fmp_vnd_per_kwh,
        strike_price_vnd_per_kwh=strike_vnd,
        delivery_factor=delivery_factor,
        contract_type=contract_type,
        exchange_rate_vnd_per_usd=exchange_rate,
    )
    settlement_projection = project_dppa_cashflows(
        year_one_settlement_usd=settlement["total_settlement_usd"],
        analysis_years=analysis_years,
        escalation_rate=escalation_rate,
        discount_rate=discount_rate,
    )

    output = {
        **settlement,
        **settlement_projection,
        "exchange_rate_vnd_per_usd": exchange_rate,
        "config_source": args.config or "built-in defaults",
        "fmp_units_used": fmp_units_used,
        "source_reopt": str(Path(args.reopt)),
        "source_extracted": str(Path(args.extracted)),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"DPPA settlement results saved to: {output_path}")
    print(f"  Contract type : {output['contract_type']}")
    print(f"  Strike price  : {output['strike_price_vnd_per_kwh']:,.2f} VND/kWh")
    print(f"  Delivery      : {output['total_q_mwh']:,.0f} MWh/year")
    print(f"  Year-1 top-up : ${output['total_settlement_usd']:,.0f}")
    print(f"  Settlement NPV: ${output['settlement_npv_usd']:,.0f}")


if __name__ == "__main__":
    main()
