"""Assemble a schema-valid extracted-inputs dict from a DealConfig (PHASE-02, S3).

The assembler lives in ``reopt_pysam_vn.analysis`` so both the CLI and the
web layer share one implementation (DEC-004). It never fetches over the
network; every ingredient is already in the deal config or the Vietnam data
layer.
"""

from __future__ import annotations

from typing import Any

from reopt_pysam_vn.analysis.types import DealConfig

__all__ = ["build_extracted_inputs"]


def build_extracted_inputs(
    deal_config: DealConfig,
    *,
    vn: Any | None = None,
) -> dict[str, Any]:
    """Build a schema-valid extracted-inputs dict per Specification S3.

    Raises ``OrchestratorInputError`` when ``deal_config.load["loads_kw"]`` is
    missing or is not exactly 8760 non-negative numbers.
    """
    from reopt_pysam_vn.analysis.offsite_dppa import OrchestratorInputError
    from reopt_pysam_vn.analysis.validation import validate_extracted_inputs
    from reopt_pysam_vn.common.assumptions import exchange_rate, market_wholesale_reference_vnd_per_kwh
    from reopt_pysam_vn.integration.settlement import compute_buyer_benchmark
    from reopt_pysam_vn.reopt.preprocess import build_evn_tou_series_vnd_per_kwh, load_vietnam_data

    if vn is None:
        vn = load_vietnam_data()

    # 1. loads_kw
    loads_kw = deal_config.load.get("loads_kw")
    if not isinstance(loads_kw, list) or len(loads_kw) != 8760:
        got = len(loads_kw) if isinstance(loads_kw, list) else type(loads_kw).__name__
        raise OrchestratorInputError(
            f"generic offsite analysis needs deal_config.load['loads_kw'] with exactly 8760 "
            f"non-negative values; got {got}"
        )
    # Validate non-negative
    for idx, val in enumerate(loads_kw):
        try:
            fval = float(val)
        except (TypeError, ValueError):
            raise OrchestratorInputError(
                f"generic offsite analysis needs deal_config.load['loads_kw'] with exactly 8760 "
                f"non-negative values; got non-numeric at index {idx}: {val!r}"
            ) from None
        if fval < 0:
            raise OrchestratorInputError(
                f"generic offsite analysis needs deal_config.load['loads_kw'] with exactly 8760 "
                f"non-negative values; got negative at index {idx}: {val!r}"
            )
    loads = [float(v) for v in loads_kw]

    # 2. site with defaults
    site = dict(deal_config.site) if isinstance(deal_config.site, dict) else {}
    defaulted_fields: list[str] = []
    if "customer_type" not in site or not site["customer_type"]:
        site["customer_type"] = "industrial"
        defaulted_fields.append("customer_type")
    if "voltage_level" not in site or not site["voltage_level"]:
        site["voltage_level"] = "medium_voltage_22kv_to_110kv"
        defaulted_fields.append("voltage_level")

    # 3. project
    title = deal_config.title.strip() if isinstance(deal_config.title, str) else ""
    project = title if title else deal_config.case

    # 4. data_year
    data_year = 2024

    # Regime for tariff
    regime_id = (deal_config.contract or {}).get("regime_id", "decision_963_2026_current")

    # 5. TOU tariff series VND/kWh
    tariff_vnd = build_evn_tou_series_vnd_per_kwh(
        vn,
        customer_type=site["customer_type"],
        voltage_level=site["voltage_level"],
        regime_id=regime_id,
        year=data_year,
    )

    # 6-10 benchmarks
    annual_load_kwh = float(sum(loads))
    benchmark_info = compute_buyer_benchmark(loads, tariff_vnd)
    weighted_evn = float(benchmark_info["blended_rate_vnd_kwh"])
    wholesale = float(market_wholesale_reference_vnd_per_kwh(vn))
    fx = float(exchange_rate(vn))
    peak = float(max(loads)) if loads else 0.0

    result: dict[str, Any] = {
        "loads_kw": loads,
        "site": site,
        "project": project,
        "data_year": data_year,
        "evn_tariff": {"tou_energy_rates_vnd_per_kwh": tariff_vnd},
        "benchmark": {
            "annual_load_kwh": annual_load_kwh,
            "weighted_evn_price_vnd_per_kwh": weighted_evn,
            "wholesale_rate_vnd_per_kwh": wholesale,
            "exchange_rate_vnd_per_usd": fx,
            "peak_demand_kw": peak,
        },
        "extraction_meta": {
            "assembled_by": "build_extracted_inputs",
            "regime_id": regime_id,
            "tariff_year": data_year,
            "customer_type": site["customer_type"],
            "voltage_level": site["voltage_level"],
            "defaulted_fields": defaulted_fields,
        },
    }

    # Carry load_cleaning if present in deal_config.load
    load_cleaning = deal_config.load.get("load_cleaning")
    if isinstance(load_cleaning, dict):
        result["load_cleaning"] = dict(load_cleaning)

    # Validate before returning
    validate_extracted_inputs(result)

    return result
