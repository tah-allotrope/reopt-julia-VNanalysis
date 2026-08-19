"""Python preprocessing for Vietnam-specific REopt inputs.

Mirror of the Julia module at `legacy/julia/src/REoptVietnam.jl`. All Vietnam-specific values are
loaded at runtime from versioned JSON files in `data/vietnam/`, driven by `manifest.json`.
This module contains logic only - no hardcoded policy values.

Usage:
    from reopt_pysam_vn.reopt.preprocess import (
        load_vietnam_data,
        apply_vietnam_defaults,
        run_vietnam_reopt,
    )
    import json, os

    vn = load_vietnam_data()
    d = json.load(open("my_project.json"))
    apply_vietnam_defaults(d, vn, customer_type="industrial", region="south")
    results = run_vietnam_reopt(d, api_key=os.environ["NREL_DEVELOPER_API_KEY"])
"""

import json
import logging
import time
import warnings
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "vietnam"
DEFAULT_MANIFEST = DEFAULT_DATA_DIR / "manifest.json"
DEFAULT_EXCHANGE_RATE = 26_400.0  # VND per USD fallback

VALID_CUSTOMER_TYPES = ("industrial", "commercial")
VALID_REGIONS = ("north", "central", "south")

HOURS_PER_YEAR = 8760
DECREE57_META_KEY = "decree57_max_export_fraction"
DEFAULT_REGIME_ID = "decision_963_2026_current"

REOPT_API_BASE_URL = "https://developer.nlr.gov/api/reopt/stable"

# US incentive fields to zero out, grouped by tech
PV_WIND_INCENTIVE_FIELDS = [
    "macrs_option_years",
    "macrs_bonus_fraction",
    "federal_itc_fraction",
    "federal_rebate_per_kw",
    "state_ibi_fraction",
    "state_ibi_max",
    "state_rebate_per_kw",
    "utility_ibi_fraction",
    "utility_ibi_max",
    "utility_rebate_per_kw",
    "production_incentive_per_kwh",
    "production_incentive_max_benefit",
    "production_incentive_years",
]

STORAGE_INCENTIVE_FIELDS = [
    "macrs_option_years",
    "macrs_bonus_fraction",
    "total_itc_fraction",
    "total_rebate_per_kw",
]

GENERATOR_INCENTIVE_FIELDS = [
    "macrs_option_years",
    "macrs_bonus_fraction",
    "federal_itc_fraction",
    "federal_rebate_per_kw",
]

# ---------------------------------------------------------------------------
# VNData — holds all loaded Vietnam data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VNData:
    """Immutable container for all Vietnam assumption data loaded from manifest-driven JSON files."""

    tariff: dict[str, Any]
    tech_costs: dict[str, Any]
    financials: dict[str, Any]
    emissions: dict[str, Any]
    export_rules: dict[str, Any]
    regimes: dict[str, Any]
    deal_defaults: dict[str, Any]
    exchange_rate: float
    data_dir: str
    # Optional: absent from manifests that predate the market_prices key (PHASE-04).
    # Declared last with a default so the frozen dataclass stays constructible.
    market_prices: dict[str, Any] = field(default_factory=dict)


def _deep_merge_dicts(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively overlay overrides onto a deep copy of base."""
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def resolve_vietnam_regime(vn: VNData, regime_id: str = DEFAULT_REGIME_ID) -> dict[str, Any]:
    """Resolve a named regime bundle onto the base tariff and export-rule payloads.

    If the regime entry contains an ``alias_of`` key, the alias is followed
    transparently so that callers receive the target bundle's data while
    still referencing the original (alias) identifier.
    """
    regimes = vn.regimes.get("regimes", {})
    if regime_id not in regimes:
        available = ", ".join(sorted(regimes.keys()))
        raise ValueError(f'Unknown regime_id "{regime_id}". Available: {available}')

    entry = regimes[regime_id]

    # Follow alias_of redirects (e.g. decision_14_2025_current -> decision_14_2025_legacy)
    if "alias_of" in entry:
        target_id = entry["alias_of"]
        if target_id not in regimes:
            raise ValueError(
                f'Alias target "{target_id}" not found in regime registry.'
            )
        bundle = deepcopy(regimes[target_id])
    else:
        bundle = deepcopy(entry)

    tariff_overrides = bundle.get("tariff_overrides", {})
    export_overrides = bundle.get("export_rule_overrides", {})
    postprocess_overrides = bundle.get("postprocess_overrides", {})

    resolved_tariff = _deep_merge_dicts(vn.tariff, tariff_overrides)
    resolved_export_rules = _deep_merge_dicts(vn.export_rules, export_overrides)

    return {
        "regime_id": regime_id,
        "registry_version": vn.regimes.get("_meta", {}).get("version"),
        "label": bundle.get("label", regime_id),
        "effective_date": bundle.get("effective_date"),
        "status": bundle.get("status"),
        "source_refs": deepcopy(bundle.get("source_refs", [])),
        "notes": bundle.get("notes"),
        "tariff": resolved_tariff,
        "export_rules": resolved_export_rules,
        "postprocess_overrides": deepcopy(postprocess_overrides),
    }


# ---------------------------------------------------------------------------
# load_vietnam_data
# ---------------------------------------------------------------------------


def load_vietnam_data(manifest_path: str | Path | None = None) -> VNData:
    """Read manifest.json, load all active versioned data files, return a VNData instance.

    Call once at startup; the returned object is immutable and reusable across scenarios.
    """
    if manifest_path is None:
        manifest_path = DEFAULT_MANIFEST
    manifest_path = Path(manifest_path)
    data_dir = manifest_path.parent

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    required_keys = (
        "tariff",
        "tech_costs",
        "financials",
        "emissions",
        "export_rules",
        "regimes",
        "deal_defaults",
    )
    for k in required_keys:
        if k not in manifest:
            raise KeyError(f'manifest.json missing required key: "{k}"')

    def _load(key: str) -> dict:
        filename = manifest[key]
        filepath = data_dir / filename
        if not filepath.is_file():
            raise FileNotFoundError(
                f'Data file not found: {filepath} (referenced by manifest key "{key}")'
            )
        with open(filepath, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if "data" not in raw:
            raise KeyError(f'Data file {filename} missing "data" block')
        return raw

    tariff_raw = _load("tariff")
    tech_costs_raw = _load("tech_costs")
    financials_raw = _load("financials")
    emissions_raw = _load("emissions")
    export_rules_raw = _load("export_rules")
    regimes_raw = _load("regimes")
    deal_defaults_raw = _load("deal_defaults")

    # market_prices is optional (PHASE-04): manifests that predate the key still load.
    market_prices_raw = _load("market_prices") if "market_prices" in manifest else {}

    # Extract exchange rate from tariff _meta (VND-denominated file), with fallback
    exchange_rate = tariff_raw.get("_meta", {}).get(
        "exchange_rate_vnd_per_usd", DEFAULT_EXCHANGE_RATE
    )

    return VNData(
        tariff=tariff_raw["data"],
        tech_costs=tech_costs_raw["data"],
        financials=financials_raw["data"],
        emissions=emissions_raw["data"],
        export_rules=export_rules_raw["data"],
        regimes={**regimes_raw["data"], "_meta": regimes_raw.get("_meta", {})},
        deal_defaults=deal_defaults_raw["data"],
        exchange_rate=float(exchange_rate),
        data_dir=str(data_dir),
        market_prices=market_prices_raw["data"] if market_prices_raw else {},
    )


# ---------------------------------------------------------------------------
# Currency helpers
# ---------------------------------------------------------------------------


def convert_vnd_to_usd(
    value: float, exchange_rate: float = DEFAULT_EXCHANGE_RATE
) -> float:
    """Convert a value from VND to USD using the given exchange rate (VND per USD)."""
    if exchange_rate <= 0:
        raise ValueError(f"exchange_rate must be positive, got {exchange_rate}")
    return float(value) / float(exchange_rate)


def convert_usd_to_vnd(
    value: float, exchange_rate: float = DEFAULT_EXCHANGE_RATE
) -> float:
    """Convert a value from USD to VND using the given exchange rate (VND per USD)."""
    if exchange_rate <= 0:
        raise ValueError(f"exchange_rate must be positive, got {exchange_rate}")
    return float(value) * float(exchange_rate)


# ---------------------------------------------------------------------------
# Helpers: non-destructive set (user values always win)
# ---------------------------------------------------------------------------


def _set_default(d: dict, key: str, value: Any) -> None:
    """Set d[key] = value only if key is not already present. User values are preserved."""
    if key not in d:
        d[key] = value


def _ensure_block(d: dict, key: str) -> dict:
    """Ensure d[key] exists as a dict; create it if missing. Returns the sub-dict."""
    if key not in d:
        d[key] = {}
    return d[key]


# ---------------------------------------------------------------------------
# zero_us_incentives
# ---------------------------------------------------------------------------


def zero_us_incentives(d: dict) -> dict:
    """Zero out all US-specific incentive fields on every tech block present in the dict."""

    def _zero_fields(block: dict, fields: list[str]) -> None:
        for f in fields:
            block[f] = 0

    # PV — may be a dict or a list of dicts
    if "PV" in d:
        pv = d["PV"]
        if isinstance(pv, dict):
            _zero_fields(pv, PV_WIND_INCENTIVE_FIELDS)
        elif isinstance(pv, list):
            for p in pv:
                if isinstance(p, dict):
                    _zero_fields(p, PV_WIND_INCENTIVE_FIELDS)

    if "Wind" in d:
        _zero_fields(d["Wind"], PV_WIND_INCENTIVE_FIELDS)

    if "ElectricStorage" in d:
        _zero_fields(d["ElectricStorage"], STORAGE_INCENTIVE_FIELDS)

    if "Generator" in d:
        _zero_fields(d["Generator"], GENERATOR_INCENTIVE_FIELDS)

    return d


# ---------------------------------------------------------------------------
# apply_vietnam_financials
# ---------------------------------------------------------------------------


def apply_vietnam_financials(
    d: dict,
    vn: VNData,
    financial_profile: str = "standard",
    **kwargs,
) -> dict:
    """Inject Vietnam financial defaults into the Financial block of d.

    Uses the specified financial_profile from the financials data file.
    Keyword arguments matching Financial field names override data file values.
    User values already in d["Financial"] are never overwritten.
    """
    if financial_profile not in vn.financials:
        available = [k for k in vn.financials if k != "reference_rates"]
        raise ValueError(
            f'Unknown financial_profile "{financial_profile}". Available: {", ".join(available)}'
        )

    profile = vn.financials[financial_profile]
    fin = _ensure_block(d, "Financial")

    # Track which keys the user already set (before we inject anything)
    user_keys = set(fin.keys())

    fin_fields = [
        "offtaker_tax_rate_fraction",
        "offtaker_discount_rate_fraction",
        "owner_tax_rate_fraction",
        "owner_discount_rate_fraction",
        "elec_cost_escalation_rate_fraction",
        "om_cost_escalation_rate_fraction",
        "analysis_years",
    ]

    for fld in fin_fields:
        if fld in profile:
            if fld in kwargs:
                _set_default(fin, fld, kwargs[fld])
            else:
                _set_default(fin, fld, profile[fld])

    # If using RE preferential profile with blended tax rate, apply it.
    # Overwrite the profile's raw rate — but only if user didn't set it themselves.
    if (
        financial_profile == "renewable_energy_preferential"
        and "tax_holiday" in profile
    ):
        blended = profile["tax_holiday"].get("effective_blended_rate_25yr")
        if blended is not None and "owner_tax_rate_fraction" not in user_keys:
            fin["owner_tax_rate_fraction"] = blended

    return d


# ---------------------------------------------------------------------------
# build_vietnam_tariff
# ---------------------------------------------------------------------------


def build_evn_tou_series_vnd_per_kwh(
    vn: VNData,
    *,
    customer_type: str,
    voltage_level: str,
    regime_id: str = DEFAULT_REGIME_ID,
    year: int | None = None,
) -> list[float]:
    """Return an 8760-element EVN TOU energy-rate series in VND per kWh."""
    if year is None:
        year = datetime.now(timezone.utc).date().year

    tariff = resolve_vietnam_regime(vn, regime_id)["tariff"]
    base_vnd = tariff["base_avg_price_vnd_per_kwh"]
    schedule = tariff["tou_schedule"]
    multipliers = tariff["rate_multipliers"]

    if customer_type == "household":
        avg_mult = multipliers["household"].get("tier_2_101_to_200kwh", 1.0)
        rate_vnd = base_vnd * avg_mult
        return [float(rate_vnd)] * HOURS_PER_YEAR

    if customer_type not in VALID_CUSTOMER_TYPES:
        raise ValueError(
            f'Unknown customer_type "{customer_type}". '
            f"Valid: {', '.join(VALID_CUSTOMER_TYPES)}, household"
        )
    if customer_type not in multipliers:
        raise ValueError(f'No rate multipliers for customer_type "{customer_type}"')
    cust_mults = multipliers[customer_type]
    vl = _resolve_tariff_multiplier_block(customer_type, cust_mults, voltage_level)

    peak_vnd = base_vnd * vl["peak"]
    standard_vnd = base_vnd * vl["standard"]
    offpeak_vnd = base_vnd * vl["offpeak"]

    weekday_rates = _build_hourly_rates(schedule["weekday"], peak_vnd, standard_vnd, offpeak_vnd)
    sunday_key = "sunday" if "sunday" in schedule else "sunday_and_public_holidays"
    sunday_rates = _build_hourly_rates(schedule[sunday_key], peak_vnd, standard_vnd, offpeak_vnd)

    return _build_8760_rates(weekday_rates, sunday_rates, year)


def build_vietnam_tariff(
    vn: VNData,
    customer_type: str,
    voltage_level: str,
    regime_id: str = DEFAULT_REGIME_ID,
    exchange_rate: float | None = None,
    year: int | None = None,
) -> dict:
    """Generate an 8760-hour TOU energy rate array from the tariff data file.

    Returns a dict suitable for merging into d["ElectricTariff"].
    """
    if exchange_rate is None:
        exchange_rate = vn.exchange_rate
    if year is None:
        year = datetime.now(timezone.utc).date().year

    vnd_rates = build_evn_tou_series_vnd_per_kwh(
        vn,
        customer_type=customer_type,
        voltage_level=voltage_level,
        regime_id=regime_id,
        year=year,
    )
    rates = [convert_vnd_to_usd(v, exchange_rate=exchange_rate) for v in vnd_rates]

    tariff = resolve_vietnam_regime(vn, regime_id)["tariff"]
    demand_vnd = tariff.get("demand_charge", {}).get(
        "monthly_demand_rate_vnd_per_kw", 0
    )
    demand_usd = convert_vnd_to_usd(demand_vnd, exchange_rate=exchange_rate)

    return {
        "urdb_label": "",
        "blended_annual_energy_rate": 0,
        "tou_energy_rates_per_kwh": rates,
        "monthly_demand_rates": [demand_usd] * 12,
    }


def _build_hourly_rates(
    schedule_block: dict, peak: float, standard: float, offpeak: float
) -> list[float]:
    """Build a 24-element list mapping hour index (0-23) to the appropriate rate."""
    rates = [standard] * 24
    for h in schedule_block.get("peak_hours", []):
        rates[int(h)] = peak
    for h in schedule_block.get("offpeak_hours", []):
        rates[int(h)] = offpeak
    for h in schedule_block.get("standard_hours", []):
        rates[int(h)] = standard
    return rates


def _resolve_commercial_voltage(voltage_level: str) -> str:
    if voltage_level in (
        "medium_voltage_22kv_to_110kv",
        "medium_voltage_above_1kv_to_35kv",
        "medium_voltage_and_above_1kv",
    ):
        return "medium_voltage_and_above_1kv"
    if voltage_level in (
        "low_voltage_below_22kv",
        "low_voltage_1kv_and_below",
        "low_voltage",
    ):
        return "low_voltage_1kv_and_below"
    return voltage_level


def _resolve_industrial_voltage(voltage_level: str) -> str:
    if voltage_level == "low_voltage_below_22kv":
        return "low_voltage_1kv_and_below"
    if voltage_level == "medium_voltage_above_1kv_to_35kv":
        return "medium_voltage_22kv_to_110kv"
    return voltage_level


def _resolve_tariff_multiplier_block(
    customer_type: str, customer_mults: dict, voltage_level: str
) -> dict:
    if customer_type != "commercial":
        normalized_vl = (
            _resolve_industrial_voltage(voltage_level)
            if customer_type == "industrial"
            else voltage_level
        )
        if normalized_vl not in customer_mults:
            raise ValueError(
                f'Unknown voltage_level "{voltage_level}" for {customer_type}. '
                f"Available: {', '.join(customer_mults.keys())}"
            )
        return customer_mults[normalized_vl]

    if voltage_level in customer_mults:
        return customer_mults[voltage_level]

    normalized_vl = _resolve_commercial_voltage(voltage_level)
    subcategories = [
        key
        for key, value in customer_mults.items()
        if isinstance(value, dict) and normalized_vl in value
    ]
    if not subcategories:
        available = ", ".join(
            key for key, value in customer_mults.items() if isinstance(value, dict)
        )
        raise ValueError(
            f'Unknown voltage_level "{voltage_level}" for commercial. '
            f"Available subcategories: {available}"
        )

    selected = (
        "other_commercial" if "other_commercial" in subcategories else subcategories[0]
    )
    return customer_mults[selected][normalized_vl]


def _build_8760_rates(
    weekday_rates: list[float], sunday_rates: list[float], year: int
) -> list[float]:
    """Build 8760-length rate list. Weekday schedule Mon-Sat; Sunday schedule Sun."""
    rates: list[float] = []
    start_date = date(year, 1, 1)
    for day_offset in range(365):
        d = start_date + timedelta(days=day_offset)
        dow = d.isoweekday()  # 1=Monday ... 7=Sunday
        hourly = sunday_rates if dow == 7 else weekday_rates
        rates.extend(hourly)
    return rates


# ---------------------------------------------------------------------------
# apply_vietnam_emissions
# ---------------------------------------------------------------------------


def apply_vietnam_emissions(d: dict, vn: VNData) -> dict:
    """Set ElectricUtility.emissions_factor_series_lb_CO2_per_kwh from emissions data file."""
    eu = _ensure_block(d, "ElectricUtility")
    ef = float(vn.emissions["grid_emission_factor_lb_CO2_per_kwh"])
    _set_default(eu, "emissions_factor_series_lb_CO2_per_kwh", [ef] * HOURS_PER_YEAR)
    return d


# ---------------------------------------------------------------------------
# apply_vietnam_tech_costs
# ---------------------------------------------------------------------------


def apply_vietnam_tech_costs(
    d: dict,
    vn: VNData,
    region: str = "south",
    pv_type: str = "rooftop",
    wind_type: str = "onshore",
    exchange_rate: float | None = None,
    currency: str = "USD",
) -> dict:
    """Inject PV, Wind, Battery, and Generator costs from the tech costs data file."""
    if exchange_rate is None:
        exchange_rate = vn.exchange_rate

    if region not in VALID_REGIONS:
        raise ValueError(
            f'Unknown region "{region}". Valid: {", ".join(VALID_REGIONS)}'
        )

    tc = vn.tech_costs
    conv = (
        (lambda v: convert_vnd_to_usd(v, exchange_rate=exchange_rate))
        if currency == "VND"
        else (lambda v: v)
    )

    # --- PV ---
    if "PV" in d:
        pv_data = tc["PV"]
        pv_block = (
            d["PV"]
            if isinstance(d["PV"], dict)
            else (
                d["PV"][0] if isinstance(d["PV"], list) and len(d["PV"]) > 0 else None
            )
        )

        if (
            pv_block is not None
            and pv_type in pv_data
            and region in pv_data.get(pv_type, {})
        ):
            regional = pv_data[pv_type][region]
            _set_default(
                pv_block,
                "installed_cost_per_kw",
                conv(regional["installed_cost_per_kw"]),
            )
            _set_default(pv_block, "om_cost_per_kw", conv(regional["om_cost_per_kw"]))

        if "common_defaults" in pv_data:
            targets = d["PV"] if isinstance(d["PV"], list) else [d["PV"]]
            for t in targets:
                if not isinstance(t, dict):
                    continue
                for k, v in pv_data["common_defaults"].items():
                    if k == "tilt_rule":
                        continue
                    _set_default(t, k, v)

    # --- Wind ---
    if "Wind" in d:
        wind_data = tc["Wind"]
        wind_block = d["Wind"]

        if wind_type in wind_data and region in wind_data.get(wind_type, {}):
            regional = wind_data[wind_type][region]
            _set_default(
                wind_block,
                "installed_cost_per_kw",
                conv(regional["installed_cost_per_kw"]),
            )
            _set_default(wind_block, "om_cost_per_kw", conv(regional["om_cost_per_kw"]))

        if "common_defaults" in wind_data:
            for k, v in wind_data["common_defaults"].items():
                _set_default(wind_block, k, v)

    # --- ElectricStorage ---
    if "ElectricStorage" in d:
        es_data = tc["ElectricStorage"]
        es_block = d["ElectricStorage"]

        if "li_ion" in es_data and region in es_data.get("li_ion", {}):
            regional = es_data["li_ion"][region]
            _set_default(
                es_block,
                "installed_cost_per_kw",
                conv(regional["installed_cost_per_kw"]),
            )
            _set_default(
                es_block,
                "installed_cost_per_kwh",
                conv(regional["installed_cost_per_kwh"]),
            )

        if "common_defaults" in es_data:
            for k, v in es_data["common_defaults"].items():
                _set_default(es_block, k, v)

    # --- Generator ---
    if "Generator" in d:
        gen_data = tc["Generator"]
        gen_block = d["Generator"]

        if "diesel" in gen_data:
            for k, v in gen_data["diesel"].items():
                _set_default(gen_block, k, conv(v))

        if "common_defaults" in gen_data:
            for k, v in gen_data["common_defaults"].items():
                _set_default(gen_block, k, v)

    return d


# ---------------------------------------------------------------------------
# apply_decree57_export
# ---------------------------------------------------------------------------


def apply_decree57_export(
    d: dict,
    vn: VNData,
    regime_id: str = DEFAULT_REGIME_ID,
    max_export_fraction: float | None = None,
    exchange_rate: float | None = None,
) -> dict:
    """Configure export rules per Decree 57/2025 as amended by Decree 243/2026
    (surplus cap 50% from 2026-06-26; resolved from the active export-rules
    data file)."""
    if exchange_rate is None:
        exchange_rate = vn.exchange_rate

    resolved_regime = resolve_vietnam_regime(vn, regime_id)
    er = resolved_regime["export_rules"]
    rooftop = er.get("rooftop_solar", {})
    data_default = rooftop.get("max_export_fraction", 0.20)
    if max_export_fraction is None:
        max_export_fraction = data_default

    if not 0 <= max_export_fraction <= 1:
        raise ValueError(
            f"max_export_fraction must be between 0 and 1, got {max_export_fraction}"
        )

    if max_export_fraction != data_default:
        warnings.warn(
            f"max_export_fraction={max_export_fraction} is stored for Vietnam custom solve wrappers, "
            "but plain REopt.run_reopt(...) will NOT enforce it automatically.",
            UserWarning,
            stacklevel=2,
        )

    et = _ensure_block(d, "ElectricTariff")

    surplus_usd = rooftop.get("surplus_purchase_rate_usd_per_kwh")
    if surplus_usd is None:
        surplus_vnd = rooftop.get("surplus_purchase_rate_vnd_per_kwh", 671)
        surplus_usd = convert_vnd_to_usd(surplus_vnd, exchange_rate=exchange_rate)
    _set_default(et, "wholesale_rate", surplus_usd)

    _set_default(et, "export_rate_beyond_net_metering_limit", 0)

    if "PV" in d:
        targets = d["PV"] if isinstance(d["PV"], list) else [d["PV"]]
        for pv in targets:
            if not isinstance(pv, dict):
                continue
            _set_default(pv, "can_net_meter", False)
            _set_default(pv, "can_wholesale", True)
            _set_default(pv, "can_export_beyond_nem_limit", False)
            _set_default(pv, "can_curtail", True)

    meta = _ensure_block(d, "_meta")
    _set_default(meta, DECREE57_META_KEY, float(max_export_fraction))
    _set_default(meta, "resolved_regime_id", regime_id)
    _set_default(meta, "regime_registry_version", resolved_regime["registry_version"])

    for key, value in resolved_regime["postprocess_overrides"].items():
        _set_default(meta, key, deepcopy(value))

    return d


# ---------------------------------------------------------------------------
# apply_vietnam_defaults — master function
# ---------------------------------------------------------------------------


def apply_vietnam_defaults(
    d: dict,
    vn: VNData | None = None,
    customer_type: str = "industrial",
    voltage_level: str = "medium_voltage_22kv_to_110kv",
    region: str = "south",
    pv_type: str = "rooftop",
    wind_type: str = "onshore",
    financial_profile: str = "standard",
    regime_id: str = DEFAULT_REGIME_ID,
    currency: str = "USD",
    exchange_rate: float | None = None,
    apply_tariff: bool = True,
    apply_emissions: bool = True,
    apply_tech_costs: bool = True,
    apply_export_rules: bool = True,
    apply_financials: bool = True,
    apply_zero_incentives: bool = True,
    **kwargs,
) -> dict:
    """Master preprocessing function. Calls all sub-functions in sequence.

    All settings are non-destructive: user-provided values in d are never overwritten.
    If vn is None, loads Vietnam data automatically.
    """
    if vn is None:
        vn = load_vietnam_data()

    if exchange_rate is None:
        exchange_rate = vn.exchange_rate

    # 1. Zero US incentives
    if apply_zero_incentives:
        zero_us_incentives(d)

    # 2. Financial defaults
    if apply_financials:
        apply_vietnam_financials(d, vn, financial_profile=financial_profile, **kwargs)

    # 3. TOU tariff
    if apply_tariff:
        tariff_dict = build_vietnam_tariff(
            vn,
            customer_type,
            voltage_level,
            regime_id=regime_id,
            exchange_rate=exchange_rate,
        )
        et = _ensure_block(d, "ElectricTariff")
        for k, v in tariff_dict.items():
            _set_default(et, k, v)

    # 4. Emissions
    if apply_emissions:
        apply_vietnam_emissions(d, vn)

    # 5. Tech costs
    if apply_tech_costs:
        apply_vietnam_tech_costs(
            d,
            vn,
            region=region,
            pv_type=pv_type,
            wind_type=wind_type,
            exchange_rate=exchange_rate,
            currency=currency,
        )

    # 6. Decree 57 export rules
    if apply_export_rules:
        apply_decree57_export(
            d,
            vn,
            regime_id=regime_id,
            exchange_rate=exchange_rate,
        )

    if apply_tariff or apply_export_rules:
        meta = _ensure_block(d, "_meta")
        resolved_regime = resolve_vietnam_regime(vn, regime_id)
        _set_default(meta, "resolved_regime_id", regime_id)
        _set_default(meta, "regime_registry_version", resolved_regime["registry_version"])
        for key, value in resolved_regime["postprocess_overrides"].items():
            _set_default(meta, key, deepcopy(value))

    return d


# ---------------------------------------------------------------------------
# run_vietnam_reopt — convenience wrapper for REopt API
# ---------------------------------------------------------------------------


def run_vietnam_reopt(
    d: dict,
    api_key: str,
    vn: VNData | None = None,
    poll_interval: int = 5,
    max_polls: int = 120,
    apply_defaults: bool = True,
    **kwargs,
) -> dict:
    """Convenience: apply Vietnam defaults → POST to REopt API → poll → return results.

    Args:
        d: REopt input dict (will be modified in-place if apply_defaults=True).
        api_key: NREL developer API key.
        vn: Pre-loaded VNData (auto-loaded if None).
        poll_interval: Seconds between status polls.
        max_polls: Maximum number of polls before timeout.
        apply_defaults: Whether to apply Vietnam defaults before submitting.
        **kwargs: Forwarded to apply_vietnam_defaults.

    Returns:
        REopt results dict.
    """
    if apply_defaults:
        if vn is None:
            vn = load_vietnam_data()
        apply_vietnam_defaults(d, vn, **kwargs)

    # POST job
    post_url = f"{REOPT_API_BASE_URL}/job/?api_key={api_key}"
    resp = requests.post(post_url, json=d, timeout=60)
    resp.raise_for_status()
    post_data = resp.json()

    run_uuid = post_data.get("run_uuid")
    if not run_uuid:
        raise RuntimeError(f"REopt API did not return run_uuid. Response: {post_data}")

    logger.info("REopt job submitted: run_uuid=%s", run_uuid)

    # Poll for results
    results_url = f"{REOPT_API_BASE_URL}/job/{run_uuid}/results/?api_key={api_key}"
    for i in range(max_polls):
        time.sleep(poll_interval)
        resp = requests.get(results_url, timeout=60)
        resp.raise_for_status()
        results = resp.json()

        status = results.get("status", "")
        if status == "optimal":
            logger.info("REopt job completed: optimal (poll %d)", i + 1)
            return results
        elif status in ("error", "infeasible", "timed_out"):
            raise RuntimeError(
                f"REopt job failed with status: {status}. Messages: {results.get('messages', {})}"
            )
        else:
            logger.info("Poll %d/%d: status=%s", i + 1, max_polls, status)

    raise TimeoutError(
        f"REopt job {run_uuid} did not complete within {max_polls * poll_interval}s"
    )
