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

import math
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from reopt_pysam_vn.analysis.offsite_dppa import OrchestratorInputError
from reopt_pysam_vn.analysis.types import DealConfig
from reopt_pysam_vn.integration.settlement import (
    ContractParams,
    compute_buyer_benchmark,
    compute_hourly_settlement,
    run_strike_sweep,
)

__all__ = [
    "build_generic_generation_profile",
    "build_generic_offsite_artifact",
]

_HOURS = 8760
_DEFAULT_REGIME_ID = "decision_963_2026_current"
_MODEL = "generic_vn_dppa_offsite_artifact"


def _pad_to_8760(series: list[float]) -> list[float]:
    values = [float(value) for value in series[:_HOURS]]
    if len(values) < _HOURS:
        values.extend([0.0] * (_HOURS - len(values)))
    return values


def _calibrate_to_target(series: list[float], annual_target_kwh: float, cap_kw: float | None) -> list[float]:
    """Scale a shape to the annual target; AC-clip when a cap is supplied."""
    total = sum(series)
    scale = annual_target_kwh / total if total else 0.0
    if cap_kw is None:
        return [value * scale for value in series]
    out = [min(value * scale, cap_kw) for value in series]
    deficit = annual_target_kwh - sum(out)
    if deficit > 1.0:
        headroom = [cap_kw - value for value in out]
        head_total = sum(headroom)
        if head_total > 0.0:
            out = [
                value + deficit * (room / head_total)
                for value, room in zip(out, headroom)
            ]
    return out


def _synthetic_generation_8760(annual_target_kwh: float, cap_kw: float | None) -> list[float]:
    """Deterministic representative profile (half-sine arc x seasonal)."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    weights: list[float] = []
    for hour_index in range(_HOURS):
        ts = start + timedelta(hours=hour_index)
        hour = ts.hour
        arc = math.sin(math.pi * (hour - 6) / 12.0) if 6 <= hour < 18 else 0.0
        day_of_year = ts.timetuple().tm_yday
        seasonal = 1.0 + 0.18 * math.cos(2.0 * math.pi * (day_of_year - 15) / 365.0)
        weights.append(max(0.0, arc * seasonal))
    return _calibrate_to_target(weights, annual_target_kwh, cap_kw)


def _try_pvwatts_generation(extracted: dict[str, Any], deal_config: DealConfig) -> list[float] | None:
    """Run PySAM PVWatts against a cached resource only; never fetch over the network."""
    site = extracted.get("site", {}) or {}
    if site.get("latitude") is None or site.get("longitude") is None:
        return None
    try:
        import PySAM.Pvwattsv8 as pv
    except ImportError:
        return None
    try:
        from reopt_pysam_vn.pysam.pvwatts_battery import DEFAULT_SOLAR_RESOURCE_FILE
    except (ImportError, AttributeError):
        return None
    resource = Path(DEFAULT_SOLAR_RESOURCE_FILE)
    if not resource.is_file():
        return None
    dc_kw = _dc_capacity_kw(deal_config)
    if dc_kw is None:
        return None
    try:
        model = pv.default("PVWattsSingleOwner")
        model.SolarResource.solar_resource_file = str(resource)
        model.SystemDesign.system_capacity = float(dc_kw)
        model.SystemDesign.dc_ac_ratio = 1.2
        model.SystemDesign.inv_eff = 96.0
        model.SystemDesign.losses = 14.0
        model.execute(0)
        gen = [max(0.0, float(value)) for value in list(model.Outputs.gen)[:_HOURS]]
    except Exception:  # noqa: BLE001 - PySAM raises bare Exception on simulation failure.
        return None
    return _pad_to_8760(gen)


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

    Prefers (1) an explicit ``extracted["generation_kw"]`` series, (2) PySAM
    PVWatts against a cached resource, (3) a deterministic synthetic profile —
    and records which one ran in ``source``. Never fetches over the network.
    """
    generation_kw = extracted.get("generation_kw")
    if generation_kw is not None and len(generation_kw) == _HOURS:
        series: list[float] | None = [float(value) for value in generation_kw]
        source = "extracted_generation_kw"
    else:
        series = _try_pvwatts_generation(extracted, deal_config)
        source = "pvwatts" if series is not None else "synthetic"

    annual_solar_gwh = (deal_config.contract or {}).get("annual_solar_gwh")
    calibrated_to_gwh: float | None = None
    if annual_solar_gwh is not None:
        target_kwh = float(annual_solar_gwh) * 1e6
        capacity_mwac = (deal_config.plant or {}).get("capacity_mwac")
        cap_kw = float(capacity_mwac) * 1000.0 if capacity_mwac is not None else None
        if source == "synthetic" and series is None:
            series = _synthetic_generation_8760(target_kwh, cap_kw)
        else:
            series = _calibrate_to_target(series or [], target_kwh, cap_kw)
        calibrated_to_gwh = float(annual_solar_gwh)
    elif series is None:
        # No generation supplied and no target: synthesize a nominal 1.0 GWh shape.
        series = _synthetic_generation_8760(1.0e6, None)

    return {
        "series_kw": series,
        "source": source,
        "calibrated_to_gwh": calibrated_to_gwh,
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
    extracted: dict[str, Any],
    *,
    deal_config: DealConfig,
    run_developer: bool = True,
    results: dict[str, Any] | None = None,
    scenario: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the generic offsite result in the ``OffsiteDppaResult`` block
    vocabulary per S3. ``run_developer``/``results``/``scenario`` are accepted
    for signature compatibility with the bespoke orchestrators; the generic path
    is directional and does not run a PySAM developer screen."""
    del run_developer, results, scenario

    loads_kw = extracted.get("loads_kw")
    if not isinstance(loads_kw, list) or len(loads_kw) != _HOURS:
        raise OrchestratorInputError(
            f"generic offsite analysis needs extracted['loads_kw'] with exactly 8760 "
            f"values; got {len(loads_kw) if isinstance(loads_kw, list) else type(loads_kw).__name__}."
        )

    generation = build_generic_generation_profile(extracted, deal_config)
    generation_kw = generation["series_kw"]

    tariff = extracted.get("evn_tariff", {}).get("tou_energy_rates_vnd_per_kwh")
    if not isinstance(tariff, list):
        raise OrchestratorInputError(
            "generic offsite analysis needs extracted['evn_tariff']['tou_energy_rates_vnd_per_kwh'] "
            "(an hourly EVN retail series in VND/kWh)."
        )
    tariff_kw = _pad_to_8760(tariff)

    from reopt_pysam_vn.integration.market_reference import resolve_market_reference_series

    market_kw, market_type, market_provenance = resolve_market_reference_series(extracted)

    regime_id = (deal_config.contract or {}).get("regime_id", _DEFAULT_REGIME_ID)
    mode = _contract_mode(deal_config)
    strike_vnd_kwh = _resolve_strike_vnd_kwh(extracted, deal_config)
    overrides: dict[str, Any] = {"excess_treatment": "export_at_surplus"}
    dppa_adder = (deal_config.contract or {}).get("dppa_adder_vnd_per_kwh")
    if dppa_adder is not None:
        overrides["dppa_adder_vnd_kwh"] = float(dppa_adder)
    params = ContractParams.from_regime(
        regime_id, mode=mode, strike_vnd_kwh=strike_vnd_kwh, **overrides
    )

    settlement = compute_hourly_settlement(
        loads_kw,
        generation_kw,
        tariff_kw,
        market_kw,
        params,
        market_source_label=market_type,
    )
    benchmark = compute_buyer_benchmark(loads_kw, tariff_kw)
    savings = benchmark["evn_only_cost_vnd"] - settlement.annual_summary["buyer_cost_vnd"]
    annual_summary = dict(settlement.annual_summary)
    annual_summary["buyer_savings_vs_evn_vnd"] = savings

    strike_points = [strike_vnd_kwh * (0.6 + 0.8 * i / 20.0) for i in range(21)]
    sweep = run_strike_sweep(
        loads_kw,
        generation_kw,
        tariff_kw,
        market_kw,
        params,
        strike_points,
        market_source_label=market_type,
    )

    viable = [entry for entry in sweep if entry["buyer_savings_vs_evn_vnd"] > 0.0]
    recommended_strike = (
        max(entry["strike_vnd_kwh"] for entry in viable) if viable else None
    )

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
        "quality": {
            "basis": "directional",
            "orchestrator": "generic_vn_dppa",
            "market_reference_price_type": market_type,
            "market_reference_proxy_fraction_of_evn": market_provenance["proxy_fraction_of_evn"],
            "solar_profile_source": generation["source"],
            "warnings": [
                "Generic offsite result is directional: no bespoke orchestrator is registered for this case.",
            ],
        },
    }
