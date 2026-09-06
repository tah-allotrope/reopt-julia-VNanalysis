"""Generic Vietnamese DPPA fallback orchestrator (PHASE-05, S3).

Assembles a ``directional``-flagged offsite/DPPA result for any ``DealConfig``
that has no bespoke orchestrator registered. The building blocks are the tested,
deal-agnostic components: hourly settlement, contract terms resolved from the
policy data layer, strike sweep, the shared market-reference series, and a
generation profile that prefers an explicit upload, then a cached PVWatts
resource, then a deterministic synthetic shape (never fetching over the network).

Every result is flagged ``quality.basis == "directional"`` and carries the
resolved ``market_reference_price_type`` and ``solar_profile_source`` so a
reader knows exactly what was computed and from what.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from reopt_pysam_vn.analysis.offsite_dppa import OrchestratorContext, OrchestratorInputError
from reopt_pysam_vn.analysis.types import DealConfig
from reopt_pysam_vn.integration.settlement import (
    ContractParams,
    build_settlement_inputs,
    compute_buyer_benchmark_typed,
    compute_hourly_settlement_typed,
    resolve_market_reference,
    run_strike_sweep_typed,
)
from reopt_pysam_vn.pysam.generation_profile import (
    SOURCE_EXTRACTED,
    ArrayConfig,
    calibrate_to_target,
    pad_to_8760,
    resolve_generation_profile,
)

__all__ = [
    "build_generic_generation_profile",
    "build_generic_offsite_artifact",
]

_HOURS = 8760
_DEFAULT_REGIME_ID = "decision_963_2026_current"
_MODEL = "generic_vn_dppa_offsite_artifact"


# The generation ladder — the shape resolution, the PVWatts adapter, the
# synthetic shape and this calibration — now lives in one module. These names
# are kept as re-exports because the orchestrator tests reach for them directly.
_pad_to_8760 = pad_to_8760
_calibrate_to_target = calibrate_to_target



def _array_config(deal_config: DealConfig, site_latitude: float | None) -> tuple[int, float]:
    """Return (array_type, tilt_degrees) for the deal's plant.mounting."""
    mounting = (deal_config.plant or {}).get("mounting", "fixed_open_rack")
    if mounting == "fixed_roof":
        return 1, float(site_latitude) if site_latitude is not None else 0.0
    if mounting == "single_axis_tracking":
        return 2, 0.0
    # default fixed_open_rack
    return 0, float(site_latitude) if site_latitude is not None else 0.0


def _dc_capacity_kw(deal_config: DealConfig) -> float | None:
    plant = deal_config.plant or {}
    capacity_mwac = plant.get("capacity_mwac")
    if capacity_mwac is not None:
        return float(capacity_mwac) * 1000.0 * 1.2
    annual_solar_gwh = (deal_config.contract or {}).get("annual_solar_gwh")
    if annual_solar_gwh is not None:
        # Nominal 1500 kWh/kWp/year capacity factor -> a defensible default size.
        return float(annual_solar_gwh) * 1e6 / 1500.0
    return None


def build_generic_generation_profile(
    extracted: dict[str, Any], deal_config: DealConfig
) -> dict[str, Any]:
    """Resolve an 8760 generation profile per S3 step 2 / ASM-006.

    Thin over ``pysam.generation_profile``: this function owns only what is
    deal-config-specific — the array configuration derived from ``mounting`` and
    site latitude, the DC sizing rule, and this orchestrator's published
    ``source`` label. The ladder itself lives behind one interface.
    """
    site = extracted.get("site", {}) or {}
    raw_lat = site.get("latitude")
    raw_lon = site.get("longitude")
    site_lat = float(raw_lat) if raw_lat is not None else None
    site_lon = float(raw_lon) if raw_lon is not None else None
    have_site = site_lat is not None and site_lon is not None

    dc_kw = _dc_capacity_kw(deal_config)
    array_type, tilt = _array_config(deal_config, site_lat)

    annual_solar_gwh = (deal_config.contract or {}).get("annual_solar_gwh")
    target_kwh = float(annual_solar_gwh) * 1e6 if annual_solar_gwh is not None else None
    capacity_mwac = (deal_config.plant or {}).get("capacity_mwac")
    cap_kw = float(capacity_mwac) * 1000.0 if capacity_mwac is not None else None

    profile = resolve_generation_profile(
        extracted_series=extracted.get("generation_kw"),
        target_kwh=target_kwh,
        cap_kw=cap_kw,
        system_capacity_kw_dc=dc_kw,
        array=ArrayConfig(array_type=array_type, tilt_degrees=tilt),
        use_pvwatts=have_site,
        pvwatts_skip_reason=(
            None if have_site else "site latitude/longitude not supplied, so PVWatts cannot run"
        ),
        site_latitude=site_lat,
        site_longitude=site_lon,
    )

    source = (
        "extracted_generation_kw" if profile.source == SOURCE_EXTRACTED else profile.source
    )
    return {
        "series_kw": profile.series_kw,
        "source": source,
        "calibrated_to_gwh": profile.calibrated_to_gwh,
        "provenance": profile.provenance,
        "warnings": profile.warnings,
    }



def _contract_mode(deal_config: DealConfig) -> str:
    mechanism = (deal_config.contract or {}).get("settlement_mechanism")
    if mechanism in ("financial_cfd", "virtual"):
        return "virtual_cfd"
    return "private_wire"


def _resolve_strike_vnd_kwh(extracted: dict[str, Any], deal_config: DealConfig) -> float:
    contract = deal_config.contract or {}
    strike = contract.get("strike_vnd_per_kwh")
    if strike is not None:
        return float(strike)
    weighted = (extracted.get("benchmark") or {}).get("weighted_evn_price_vnd_per_kwh")
    if weighted is not None:
        return float(weighted)
    raise OrchestratorInputError(
        "generic offsite analysis needs a strike price; set "
        "deal_config.contract['strike_vnd_per_kwh'] or supply "
        "extracted['benchmark']['weighted_evn_price_vnd_per_kwh']."
    )


def build_generic_offsite_artifact(
    extracted: dict[str, Any], ctx: OrchestratorContext
) -> dict[str, Any]:
    """Assemble the generic offsite result in the ``OffsiteDppaResult`` block
    vocabulary per S3.

    Speaks the declared orchestrator contract. The generic path is directional
    and does not run a PySAM developer screen, so it uses only
    ``ctx.deal_config`` and ignores the rest of the context.
    """
    deal_config = ctx.deal_config

    loads_kw = extracted.get("loads_kw")
    if not isinstance(loads_kw, list) or len(loads_kw) != _HOURS:
        raise OrchestratorInputError(
            f"generic offsite analysis needs extracted['loads_kw'] with exactly 8760 "
            f"values; got {len(loads_kw) if isinstance(loads_kw, list) else type(loads_kw).__name__}."
        )

    generation = build_generic_generation_profile(extracted, deal_config)
    generation_kw = generation["series_kw"]
    generation_warnings: list[str] = list(generation.get("warnings", []))
    provenance: dict[str, Any] = dict(generation.get("provenance", {}))

    tariff = extracted.get("evn_tariff", {}).get("tou_energy_rates_vnd_per_kwh")
    if not isinstance(tariff, list):
        raise OrchestratorInputError(
            "generic offsite analysis needs extracted['evn_tariff']['tou_energy_rates_vnd_per_kwh'] "
            "(an hourly EVN retail series in VND/kWh)."
        )
    tariff_kw = _pad_to_8760(tariff)

    from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_fx
    from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

    vn = load_vietnam_data()
    benchmark_block = extracted.get("benchmark") or {}
    market = resolve_market_reference(
        retail_vnd_per_kwh=tariff_kw,
        cfmp_vnd_per_mwh=extracted.get("cfmp_vnd_per_mwh"),
        fmp_vnd_per_mwh=extracted.get("fmp_vnd_per_mwh"),
        weighted_evn_price_vnd_per_kwh=benchmark_block.get(
            "weighted_evn_price_vnd_per_kwh"
        ),
        wholesale_rate_vnd_per_kwh=benchmark_block.get("wholesale_rate_vnd_per_kwh"),
        vn=vn,
    )
    market_type = market.reference_type

    regime_id = (deal_config.contract or {}).get("regime_id", _DEFAULT_REGIME_ID)
    mode = _contract_mode(deal_config)
    strike_vnd_kwh = _resolve_strike_vnd_kwh(extracted, deal_config)
    overrides: dict[str, Any] = {"excess_treatment": "export_at_surplus"}
    dppa_adder = (deal_config.contract or {}).get("dppa_adder_vnd_per_kwh")
    if dppa_adder is not None:
        overrides["dppa_adder_vnd_kwh"] = float(dppa_adder)
    params = ContractParams.from_regime(
        regime_id, mode=mode, strike_vnd_kwh=strike_vnd_kwh, vn=vn, **overrides
    )

    inputs = build_settlement_inputs(
        loads_kw=loads_kw,
        generation_kw=generation_kw,
        tariff_vnd_per_kwh=tariff_kw,
        market=market,
        contract=params,
        exchange_rate_vnd_per_usd=_resolve_fx(vn, extracted=extracted),
    )
    settlement = compute_hourly_settlement_typed(inputs)
    typed_benchmark = compute_buyer_benchmark_typed(inputs)
    benchmark = {
        "evn_only_cost_vnd": typed_benchmark.evn_only_cost_vnd,
        "total_load_kwh": typed_benchmark.total_load_kwh,
        "blended_rate_vnd_kwh": typed_benchmark.benchmark_blended_cost_vnd_per_kwh,
    }
    savings = benchmark["evn_only_cost_vnd"] - settlement.annual_summary["buyer_cost_vnd"]
    annual_summary = dict(settlement.annual_summary)
    annual_summary["buyer_savings_vs_evn_vnd"] = savings

    strike_points = [strike_vnd_kwh * (0.6 + 0.8 * i / 20.0) for i in range(21)]
    sweep = run_strike_sweep_typed(inputs, strike_points)

    viable = [entry for entry in sweep if entry["buyer_savings_vs_evn_vnd"] > 0.0]
    recommended_strike = (
        max(entry["strike_vnd_kwh"] for entry in viable) if viable else None
    )

    # Build quality block with resource provenance (PHASE-03).
    solar_source = str(generation["source"])
    distance_km = provenance.get("distance_km")
    warnings = [
        "Generic offsite result is directional: no bespoke orchestrator is registered for this case.",
    ]
    warnings.extend(generation_warnings)
    if distance_km is not None and distance_km >= 100.0:
        solar_source = "pvwatts_fallback_resource"
        warnings.append(
            f"solar resource {provenance.get('resource_file')} is {distance_km:.1f} km from site; using fallback resource"
        )

    quality: dict[str, Any] = {
        "basis": "directional",
        "orchestrator": "generic_vn_dppa",
        "market_reference_price_type": market_type,
        "market_reference_proxy_fraction_of_evn": market.proxy_fraction_of_evn,
        "solar_profile_source": solar_source,
        "solar_resource_file": provenance.get("resource_file"),
        "solar_resource_latitude": provenance.get("resource_latitude"),
        "solar_resource_longitude": provenance.get("resource_longitude"),
        "solar_resource_distance_km": distance_km,
        "array_type": provenance.get("array_type"),
        "tilt_degrees": provenance.get("tilt_degrees"),
        "warnings": warnings,
    }

    return {
        "case": deal_config.case,
        "model": _MODEL,
        "deal": {
            "case": deal_config.case,
            "regime_id": regime_id,
            "settlement_mechanism": (deal_config.contract or {}).get("settlement_mechanism"),
            "contract_mode": mode,
            "strike_vnd_per_kwh": strike_vnd_kwh,
        },
        "base_settlement": {
            "annual_summary": annual_summary,
            "hourly_ledger": settlement.hourly_ledger,
            "contract_params": asdict(settlement.contract_params),
            "market_source_label": settlement.market_source_label,
            "buyer_benchmark": benchmark,
        },
        "strike_sweep": {"sweep": sweep},
        "adder_sensitivity": {},
        "regime_stress": {},
        "decision": {
            "buyer_savings_positive": savings > 0.0,
            "recommended_strike_vnd_kwh": recommended_strike,
        },
        "quality": quality,
    }
