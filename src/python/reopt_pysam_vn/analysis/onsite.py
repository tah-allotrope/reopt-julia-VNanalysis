"""Generalized onsite (behind-the-meter) analysis pipeline.

``run_onsite(deal_config)`` turns a deal config into an ``OnsiteResult`` — REopt
PV+BESS sizing, dispatch coverage, and economics — by post-processing a REopt
results dict. The results are either injected (deterministic, test/parity path)
or produced by a caller-supplied ``solve_fn`` (the slow Julia path). The pipeline
never invokes the Julia solver implicitly.

The dispatch-coverage block reproduces ``integration.ninhsim_solar_storage_60pct
.calculate_ninhsim_coverage_summary`` exactly (DEC-002 exact bucket); the helpers
below intentionally mirror that module's ``_pad_to_8760`` / ``_sum_series``.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from reopt_pysam_vn.analysis.types import DealConfig, OnsiteResult

__all__ = ["run_onsite", "build_onsite_scenario"]

_HOURS = 8760
_DEFAULT_TARGET_FRACTION = 0.6


def _pad_to_8760(series: List[float]) -> List[float]:
    if len(series) >= _HOURS:
        return list(series[:_HOURS])
    return list(series) + [0.0] * (_HOURS - len(series))


def _sum_series(*series_list: List[float]) -> List[float]:
    padded = [_pad_to_8760(series) for series in series_list]
    return [sum(values) for values in zip(*padded)]


def _delivery_profile(results: Dict[str, Any]) -> List[float]:
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    storage = results.get("ElectricStorage", {})
    return _sum_series(
        pv.get("electric_to_load_series_kw", []),
        wind.get("electric_to_load_series_kw", []),
        storage.get("storage_to_load_series_kw", []),
    )


def _export_profile(results: Dict[str, Any]) -> List[float]:
    pv = results.get("PV", {})
    wind = results.get("Wind", {})
    return _sum_series(
        pv.get("electric_to_grid_series_kw", []),
        wind.get("electric_to_grid_series_kw", []),
    )


def _grid_profile(results: Dict[str, Any]) -> List[float]:
    return _pad_to_8760(results.get("ElectricUtility", {}).get("electric_to_load_series_kw", []))


def _coverage(results: Dict[str, Any], extracted: Dict[str, Any], target_fraction: float) -> Dict[str, Any]:
    renewable_delivered_kwh = sum(max(0.0, v) for v in _delivery_profile(results))
    exported_renewable_kwh = sum(max(0.0, v) for v in _export_profile(results))
    grid_supplied_kwh = sum(max(0.0, v) for v in _grid_profile(results))
    total_load_kwh = sum(max(0.0, v) for v in _pad_to_8760(extracted.get("loads_kw", [])))
    achieved = renewable_delivered_kwh / total_load_kwh if total_load_kwh else 0.0
    return {
        "renewable_delivered_kwh": renewable_delivered_kwh,
        "exported_renewable_kwh": exported_renewable_kwh,
        "sold_renewable_kwh": renewable_delivered_kwh + exported_renewable_kwh,
        "grid_supplied_kwh": grid_supplied_kwh,
        "total_load_kwh": total_load_kwh,
        "achieved_delivered_fraction_of_load": achieved,
        "target_delivered_fraction": float(target_fraction),
        "meets_target": achieved + 1e-9 >= float(target_fraction),
    }


def _sizing(results: Dict[str, Any]) -> Dict[str, Any]:
    storage = results.get("ElectricStorage", {})
    return {
        "pv_kw": float(results.get("PV", {}).get("size_kw", 0.0) or 0.0),
        "wind_kw": float(results.get("Wind", {}).get("size_kw", 0.0) or 0.0),
        "bess_power_kw": float(storage.get("size_kw", 0.0) or 0.0),
        "bess_energy_kwh": float(storage.get("size_kwh", 0.0) or 0.0),
    }


def _economics(results: Dict[str, Any]) -> Dict[str, Any]:
    fin = results.get("Financial", {})
    keys = (
        "npv",
        "lifecycle_capital_costs",
        "lcc",
        "year_one_bill_before_tax",
        "initial_capital_costs",
    )
    return {k: float(fin[k]) for k in keys if fin.get(k) is not None}


def build_onsite_scenario(deal_config: DealConfig) -> Dict[str, Any]:
    """Map a DealConfig onto a REopt input dict with Vietnam defaults applied.

    Used by the solve path (``solve_fn``). Kept import-light so the deterministic
    post-processing path does not require REopt/Julia.
    """
    from reopt_pysam_vn.reopt.preprocess import apply_vietnam_defaults, load_vietnam_data

    site = deal_config.site
    plant = deal_config.plant
    site_block: Dict[str, Any] = {}
    if site.get("latitude") is not None:
        site_block["latitude"] = float(site["latitude"])
    if site.get("longitude") is not None:
        site_block["longitude"] = float(site["longitude"])
    scenario: Dict[str, Any] = {
        "Site": site_block,
        "ElectricLoad": {},
        "PV": {"max_kw": float(plant.get("capacity_mwp", 0.0)) * 1000.0},
        "ElectricStorage": {
            "max_kw": float(plant.get("bess_power_mw", 0.0)) * 1000.0,
            "max_kwh": float(plant.get("bess_energy_mwh", 0.0)) * 1000.0,
        },
    }
    if deal_config.load.get("loads_kw"):
        scenario["ElectricLoad"]["loads_kw"] = list(deal_config.load["loads_kw"])
    vn = load_vietnam_data()
    voltage_level = site.get("voltage_level")
    defaults_kwargs: Dict[str, Any] = {
        "customer_type": site.get("customer_type", "industrial"),
        "region": site.get("region", "south"),
    }
    if voltage_level is not None:
        defaults_kwargs["voltage_level"] = voltage_level
    apply_vietnam_defaults(scenario, vn, **defaults_kwargs)
    return scenario


def run_onsite(
    deal_config: DealConfig,
    *,
    results: Optional[Dict[str, Any]] = None,
    extracted: Optional[Dict[str, Any]] = None,
    target_fraction: Optional[float] = None,
    solve_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> OnsiteResult:
    """Run the onsite BTM analysis for ``deal_config``.

    Parameters
    ----------
    results:
        Pre-solved REopt results dict. If ``None``, the scenario is built from
        ``deal_config`` and solved with ``solve_fn``; if neither is given, raises
        ``ValueError`` rather than silently invoking the Julia solver.
    extracted:
        Inputs carrying ``loads_kw``. If ``None``, derived from ``deal_config.load``.
    target_fraction:
        Onsite renewable delivered-energy target. Defaults to
        ``deal_config.contract['target_delivered_fraction']`` then ``0.6``.
    """
    if results is None:
        if solve_fn is None:
            raise ValueError(
                "run_onsite needs a pre-solved `results` dict or a `solve_fn` to "
                "solve the REopt scenario; refusing to invoke the Julia solver implicitly."
            )
        results = solve_fn(build_onsite_scenario(deal_config))

    if extracted is None:
        extracted = {"loads_kw": list(deal_config.load.get("loads_kw", []))}

    tf = (
        target_fraction
        if target_fraction is not None
        else float(deal_config.contract.get("target_delivered_fraction", _DEFAULT_TARGET_FRACTION))
    )

    return OnsiteResult(
        case=deal_config.case,
        sizing=_sizing(results),
        dispatch=_coverage(results, extracted, tf),
        economics=_economics(results),
        raw={"mode": "onsite"},
    )
