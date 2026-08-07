"""PVWatts plus battery PySAM runtime for fuller PV+BESS case studies."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy_financial as npf

from reopt_pysam_vn.pysam.cashflow import build_annual_cashflow_table, trim_year_zero

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_RESOURCE_CACHE = REPO_ROOT / "data" / "interim" / "pysam_resources"
DEFAULT_SOLAR_RESOURCE_TYPE = "himawari"
DEFAULT_SOLAR_RESOURCE_YEAR = "2019"
DEFAULT_SOLAR_RESOURCE_INTERVAL_MIN = 60
DEFAULT_SOLAR_RESOURCE_FILE = DEFAULT_RESOURCE_CACHE / "ninhsim_himawari_2019_60min.csv"


@dataclass
class PVWattsBatterySingleOwnerInputs:
    """Normalized inputs for a PVWatts + Battwatts + Single Owner workflow."""

    system_capacity_kw: float
    battery_power_kw: float
    battery_capacity_kwh: float
    load_profile_kw: list[float]
    buy_rate_usd_per_kwh: list[float]
    sell_rate_usd_per_kwh: list[float]
    ppa_price_input_usd_per_kwh: float
    solar_resource_file: str
    analysis_years: int = 20
    dc_ac_ratio: float = 1.2
    inverter_efficiency_pct: float = 96.0
    losses_pct: float = 14.0
    degradation_fraction_per_year: float = 0.005
    debt_fraction: float = 0.70
    owner_tax_rate_fraction: float = 0.20          # VN CIT standard (was 0.0575 US effective)
    owner_discount_rate_fraction: float = 0.08
    offtaker_discount_rate_fraction: float = 0.10
    inflation_rate_fraction: float = 0.035
    debt_interest_rate_fraction: float = 0.085
    debt_tenor_years: int = 10
    ppa_escalation_rate_fraction: float = 0.05
    om_escalation_rate_fraction: float = 0.03     # VN default (was 0.04 US)
    installed_cost_usd: float = 1_000_000.0
    fixed_om_usd_per_year: float = 10_000.0
    battery_can_grid_charge: bool = False
    battery_dispatch_mode: str = "peak_shaving_look_ahead"
    # "vn_sl_15yr" = VN Circular 45 SL 15-yr (default)
    # "vn_sl_10yr" = VN SL 10-yr via custom schedule
    # "us_macrs_5yr" = US 5-yr MACRS (legacy / comparison only)
    depreciation_schedule: str = "vn_sl_15yr"
    case_metadata: dict = field(default_factory=dict)

    @property
    def battery_duration_hours(self) -> float:
        if self.battery_power_kw <= 0:
            return 0.0
        return float(self.battery_capacity_kwh) / float(self.battery_power_kw)


def _clean_number(value: float) -> float | None:
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def _percent_to_fraction(value) -> float | None:
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        value = value[-1]
    cleaned = _clean_number(value)
    if cleaned is None:
        return None
    return cleaned / 100.0


def _load_nrel_env() -> tuple[str, str]:
    env_path = REPO_ROOT / "NREL_API.env"
    api_key = os.environ.get("NREL_DEVELOPER_API_KEY")
    email = os.environ.get("NREL_DEVELOPER_EMAIL")

    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            value = value.strip().strip('"')
            if key.strip() == "API_KEY_NAME":
                api_key = api_key or value
            elif key.strip() == "API_KEY_EMAIL":
                email = email or value

    if not api_key or not email:
        raise FileNotFoundError(
            "NREL credentials not available. Set NREL_API.env or environment variables for detailed PySAM resource fetches."
        )
    return api_key, email


def ensure_solar_resource_file(
    *,
    latitude: float,
    longitude: float,
    cache_dir: Path | None = None,
    force_download: bool = False,
    cached_resource_file: Path | None = None,
    resource_type: str = DEFAULT_SOLAR_RESOURCE_TYPE,
    resource_year: str = DEFAULT_SOLAR_RESOURCE_YEAR,
    resource_interval_min: int = DEFAULT_SOLAR_RESOURCE_INTERVAL_MIN,
) -> Path:
    """Return a cached solar resource file, downloading it if needed."""

    if cached_resource_file is not None and cached_resource_file.is_file():
        return cached_resource_file

    cache_root = Path(cache_dir or DEFAULT_RESOURCE_CACHE)
    cache_root.mkdir(parents=True, exist_ok=True)

    expected = cache_root / (
        f"nsrdb_{latitude}_{longitude}_{resource_type}_{resource_interval_min}_{resource_year}.csv"
    )
    fallback = DEFAULT_SOLAR_RESOURCE_FILE
    if not force_download:
        if expected.is_file():
            return expected
        if fallback.is_file():
            return fallback

    from PySAM.ResourceTools import FetchResourceFiles

    api_key, email = _load_nrel_env()
    fetcher = FetchResourceFiles(
        "solar",
        api_key,
        email,
        resource_type=resource_type,
        resource_year=resource_year,
        resource_interval_min=resource_interval_min,
        resource_dir=str(cache_root),
        verbose=False,
    )
    fetched = fetcher.fetch([(longitude, latitude)]).resource_file_paths_dict.get(
        (longitude, latitude)
    )
    if not fetched:
        raise FileNotFoundError(
            f"Could not fetch solar resource file for ({latitude}, {longitude})"
        )
    return Path(fetched)


def build_pvwatts_battery_single_owner_inputs(
    **overrides,
) -> PVWattsBatterySingleOwnerInputs:
    """Build a validated PVWatts battery input bundle."""

    inputs = PVWattsBatterySingleOwnerInputs(**overrides)
    if inputs.system_capacity_kw <= 0.0:
        raise ValueError("system_capacity_kw must be positive")
    if inputs.battery_power_kw <= 0.0:
        raise ValueError("battery_power_kw must be positive")
    if inputs.battery_capacity_kwh <= 0.0:
        raise ValueError("battery_capacity_kwh must be positive")
    if len(inputs.load_profile_kw) != 8760:
        raise ValueError("load_profile_kw must contain 8760 values")
    if len(inputs.buy_rate_usd_per_kwh) != 8760:
        raise ValueError("buy_rate_usd_per_kwh must contain 8760 values")
    if len(inputs.sell_rate_usd_per_kwh) != 8760:
        raise ValueError("sell_rate_usd_per_kwh must contain 8760 values")
    return inputs


def _dispatch_mode_code(mode: str) -> int:
    codes = {
        "peak_shaving_look_ahead": 0,
        "peak_shaving_look_behind": 1,
        "custom": 2,
    }
    if mode not in codes:
        raise ValueError(f"Unsupported battery_dispatch_mode: {mode}")
    return codes[mode]


def _annual_or_sum(value, fallback_series) -> float:
    cleaned = _clean_number(value) if not isinstance(value, (list, tuple)) else None
    if cleaned is not None:
        return cleaned
    return float(sum(float(v) for v in fallback_series))


def _equity_irr_from_project_cashflows(
    size_of_equity_usd: float, cashflows: list[float]
) -> float | None:
    if size_of_equity_usd <= 0.0:
        return None
    irr = npf.irr([-float(size_of_equity_usd)] + [float(v) for v in cashflows])
    if irr is None:
        return None
    return _clean_number(irr)


def run_pvwatts_battery_single_owner_model(
    inputs: PVWattsBatterySingleOwnerInputs,
) -> dict:
    """Run a fuller PVWatts + Battwatts + Single Owner workflow."""

    if not Path(inputs.solar_resource_file).is_file():
        raise FileNotFoundError(
            f"solar_resource_file not found: {inputs.solar_resource_file}"
        )

    import PySAM.Battwatts as bw
    import PySAM.Pvwattsv8 as pv
    import PySAM.Singleowner as so
    import PySAM.Utilityrate5 as ur

    pv_model = pv.default("PVWattsSingleOwner")
    batt_model = bw.from_existing(pv_model, "PVWattsBatteryCommercial")
    utility_model = ur.from_existing(pv_model, "PVWattsBatteryCommercial")
    financial_model = so.from_existing(pv_model, "PVWattsSingleOwner")

    pv_model.SolarResource.solar_resource_file = str(inputs.solar_resource_file)
    pv_model.SystemDesign.system_capacity = float(inputs.system_capacity_kw)
    pv_model.SystemDesign.dc_ac_ratio = float(inputs.dc_ac_ratio)
    pv_model.SystemDesign.inv_eff = float(inputs.inverter_efficiency_pct)
    pv_model.SystemDesign.losses = float(inputs.losses_pct)
    pv_model.Lifetime.analysis_period = int(inputs.analysis_years)
    pv_model.Lifetime.system_use_lifetime_output = 0
    pv_model.Lifetime.dc_degradation = [
        float(inputs.degradation_fraction_per_year) * 100.0
    ]

    batt_model.Battery.batt_simple_enable = 1
    batt_model.Battery.batt_simple_chemistry = 1
    batt_model.Battery.batt_simple_kw = float(inputs.battery_power_kw)
    batt_model.Battery.batt_simple_kwh = float(inputs.battery_capacity_kwh)
    batt_model.Battery.batt_simple_meter_position = 0
    batt_model.Battery.inverter_efficiency = float(inputs.inverter_efficiency_pct)
    batt_model.Battery.load = [float(v) for v in inputs.load_profile_kw]
    batt_model.Battery.batt_simple_dispatch = _dispatch_mode_code(
        inputs.battery_dispatch_mode
    )

    utility_model.ElectricityRates.ur_metering_option = 2
    utility_model.ElectricityRates.ur_ts_buy_rate = [
        float(v) for v in inputs.buy_rate_usd_per_kwh
    ]
    utility_model.ElectricityRates.ur_ts_sell_rate = [
        float(v) for v in inputs.sell_rate_usd_per_kwh
    ]
    utility_model.ElectricityRates.ur_en_ts_buy_rate = 1
    utility_model.ElectricityRates.ur_en_ts_sell_rate = 1
    utility_model.ElectricityRates.rate_escalation = [
        float(inputs.ppa_escalation_rate_fraction) * 100.0
    ]

    financial_model.Revenue.ppa_soln_mode = 1
    financial_model.Revenue.ppa_price_input = [
        float(inputs.ppa_price_input_usd_per_kwh)
    ]
    financial_model.Revenue.ppa_escalation = (
        float(inputs.ppa_escalation_rate_fraction) * 100.0
    )
    financial_model.SystemCosts.total_installed_cost = float(inputs.installed_cost_usd)
    financial_model.SystemCosts.om_fixed = [float(inputs.fixed_om_usd_per_year)]
    financial_model.SystemCosts.om_capacity = [0.0]
    financial_model.SystemCosts.om_production = [0.0]
    financial_model.SystemCosts.om_fixed_escal = (
        float(inputs.om_escalation_rate_fraction) * 100.0
    )
    financial_model.SystemCosts.om_capacity_escal = 0.0
    financial_model.SystemCosts.om_production_escal = 0.0
    financial_model.FinancialParameters.analysis_period = int(inputs.analysis_years)
    financial_model.FinancialParameters.debt_option = 0
    financial_model.FinancialParameters.debt_percent = (
        float(inputs.debt_fraction) * 100.0
    )
    financial_model.FinancialParameters.federal_tax_rate = [
        float(inputs.owner_tax_rate_fraction) * 100.0
    ]
    financial_model.FinancialParameters.state_tax_rate = [0.0]
    financial_model.FinancialParameters.real_discount_rate = (
        float(inputs.owner_discount_rate_fraction) * 100.0
    )
    financial_model.FinancialParameters.inflation_rate = (
        float(inputs.inflation_rate_fraction) * 100.0
    )
    financial_model.FinancialParameters.term_int_rate = (
        float(inputs.debt_interest_rate_fraction) * 100.0
    )
    financial_model.FinancialParameters.term_tenor = int(inputs.debt_tenor_years)
    sched = inputs.depreciation_schedule
    if sched == "us_macrs_5yr":
        financial_model.Depreciation.depr_fedbas_method = 1
        financial_model.Depreciation.depr_stabas_method = 1
        financial_model.Depreciation.depr_alloc_macrs_5_percent = 100.0
        financial_model.Depreciation.depr_alloc_sl_15_percent = 0.0
        financial_model.Depreciation.depr_alloc_custom_percent = 0.0
    elif sched == "vn_sl_10yr":
        financial_model.Depreciation.depr_fedbas_method = 1
        financial_model.Depreciation.depr_stabas_method = 0
        financial_model.Depreciation.depr_alloc_macrs_5_percent = 0.0
        financial_model.Depreciation.depr_alloc_sl_15_percent = 0.0
        financial_model.Depreciation.depr_alloc_custom_percent = 100.0
        financial_model.Depreciation.depr_fedbas_custom = [10.0] * 10 + [0.0] * 15
    else:  # vn_sl_15yr (VN Circular 45 default)
        financial_model.Depreciation.depr_fedbas_method = 1
        financial_model.Depreciation.depr_stabas_method = 0
        financial_model.Depreciation.depr_alloc_macrs_5_percent = 0.0
        financial_model.Depreciation.depr_alloc_sl_15_percent = 100.0
        financial_model.Depreciation.depr_alloc_custom_percent = 0.0
    financial_model.Depreciation.depr_alloc_macrs_15_percent = 0.0
    financial_model.Depreciation.depr_alloc_sl_5_percent = 0.0
    financial_model.Depreciation.depr_alloc_sl_20_percent = 0.0
    financial_model.Depreciation.depr_alloc_sl_39_percent = 0.0
    financial_model.Depreciation.depr_bonus_fed = 0.0
    financial_model.Depreciation.depr_bonus_sta = 0.0
    financial_model.TaxCreditIncentives.itc_fed_percent = (0.0,)
    financial_model.TaxCreditIncentives.itc_sta_percent = (0.0,)
    financial_model.TaxCreditIncentives.itc_fed_amount = (0.0,)
    financial_model.TaxCreditIncentives.itc_sta_amount = (0.0,)
    financial_model.TaxCreditIncentives.ptc_fed_amount = (0.0,)
    financial_model.TaxCreditIncentives.ptc_sta_amount = (0.0,)
    financial_model.TaxCreditIncentives.ptc_fed_escal = 0.0
    financial_model.TaxCreditIncentives.ptc_sta_escal = 0.0

    pv_model.execute()
    batt_model.execute()
    utility_model.execute()
    financial_model.execute()

    analysis_years = int(inputs.analysis_years)
    revenue = trim_year_zero(financial_model.Outputs.cf_total_revenue, analysis_years)
    aftertax_cash = trim_year_zero(
        financial_model.Outputs.cf_project_return_aftertax_cash,
        analysis_years,
    )
    debt_service = trim_year_zero(
        financial_model.Outputs.cf_debt_payment_total,
        analysis_years,
    )
    debt_balance = trim_year_zero(
        financial_model.Outputs.cf_debt_balance, analysis_years
    )
    dscr = trim_year_zero(financial_model.Outputs.cf_pretax_dscr, analysis_years)

    annual_pv_ac_energy_kwh = _annual_or_sum(
        getattr(pv_model.Outputs, "ac_annual", None),
        batt_model.Outputs.gen_without_battery,
    )
    annual_export_kwh = _annual_or_sum(
        batt_model.Outputs.annual_export_to_grid_energy,
        batt_model.Outputs.system_to_grid,
    )
    annual_system_to_load_kwh = float(sum(batt_model.Outputs.system_to_load))
    annual_battery_charge_from_system_kwh = _annual_or_sum(
        batt_model.Outputs.batt_annual_charge_from_system,
        batt_model.Outputs.system_to_batt,
    )
    annual_battery_charge_from_grid_kwh = _annual_or_sum(
        batt_model.Outputs.batt_annual_charge_from_grid,
        batt_model.Outputs.grid_to_batt,
    )
    annual_battery_discharge_to_load_kwh = _annual_or_sum(
        batt_model.Outputs.batt_annual_discharge_energy,
        batt_model.Outputs.batt_to_load,
    )
    annual_estimated_curtailment_kwh = max(
        0.0,
        annual_pv_ac_energy_kwh
        - annual_system_to_load_kwh
        - annual_battery_charge_from_system_kwh
        - annual_export_kwh,
    )
    size_of_equity = float(financial_model.Outputs.size_of_equity)
    equity_irr = _equity_irr_from_project_cashflows(size_of_equity, aftertax_cash)

    return {
        "model": "PySAM PVWatts Battery Single Owner",
        "status": "ok",
        "runtime": {
            "country": "Vietnam",
            "currency": "USD",
            "python": ".venv/Scripts/python.exe",
            "system_config": "PVWattsSingleOwner + Battwatts + Utilityrate5 + Singleowner",
            "solar_resource_file": str(inputs.solar_resource_file),
        },
        "inputs": {
            "system_capacity_kw": float(inputs.system_capacity_kw),
            "battery_power_kw": float(inputs.battery_power_kw),
            "battery_capacity_kwh": float(inputs.battery_capacity_kwh),
            "battery_duration_hours": float(inputs.battery_duration_hours),
            "installed_cost_usd": float(inputs.installed_cost_usd),
            "fixed_om_usd_per_year": float(inputs.fixed_om_usd_per_year),
            "ppa_price_input_usd_per_kwh": float(inputs.ppa_price_input_usd_per_kwh),
            "analysis_years": analysis_years,
            "debt_fraction": float(inputs.debt_fraction),
            "owner_tax_rate_fraction": float(inputs.owner_tax_rate_fraction),
            "om_escalation_rate_fraction": float(inputs.om_escalation_rate_fraction),
            "depreciation_schedule": inputs.depreciation_schedule,
            "battery_can_grid_charge": bool(inputs.battery_can_grid_charge),
            "battery_dispatch_mode": inputs.battery_dispatch_mode,
        },
        "case": dict(inputs.case_metadata),
        "outputs": {
            "project_return_aftertax_npv_usd": float(
                financial_model.Outputs.project_return_aftertax_npv
            ),
            "project_return_aftertax_irr_fraction": _percent_to_fraction(
                financial_model.Outputs.project_return_aftertax_irr
            ),
            "project_return_pretax_npv_usd": _clean_number(
                financial_model.Outputs.cf_project_return_pretax_npv[-1]
            ),
            "project_return_pretax_irr_fraction": _percent_to_fraction(
                financial_model.Outputs.cf_project_return_pretax_irr
            ),
            "size_of_debt_usd": float(financial_model.Outputs.size_of_debt),
            "debt_fraction": float(financial_model.Outputs.debt_fraction) / 100.0,
            "min_dscr": _clean_number(financial_model.Outputs.min_dscr),
            "npv_ppa_revenue_usd": float(financial_model.Outputs.npv_ppa_revenue),
            "equity_irr_fraction": equity_irr,
            "size_of_equity_usd": size_of_equity,
        },
        "energy_summary": {
            "annual_pv_ac_energy_kwh": annual_pv_ac_energy_kwh,
            "annual_matched_load_kwh": annual_system_to_load_kwh
            + annual_battery_discharge_to_load_kwh,
            "annual_export_kwh": annual_export_kwh,
            "annual_battery_charge_from_system_kwh": annual_battery_charge_from_system_kwh,
            "annual_battery_charge_from_grid_kwh": annual_battery_charge_from_grid_kwh,
            "annual_battery_discharge_to_load_kwh": annual_battery_discharge_to_load_kwh,
            "annual_estimated_curtailment_kwh": annual_estimated_curtailment_kwh,
        },
        "annual_cashflows": build_annual_cashflow_table(
            analysis_years,
            revenue,
            aftertax_cash,
            debt_service,
            debt_balance,
            dscr,
        ),
        "notes": {
            "phase_scope": "DPPA Case 1 uses PVWatts plus Battwatts plus Single Owner to provide a fuller PV+BESS workflow than the earlier custom-generation finance shortcut.",
            "dispatch_note": "Battwatts simple dispatch is used as the stable fuller-PySAM battery path on this workstation; grid charging is represented as disabled in the case inputs and sell rate is zeroed to discourage export.",
        },
    }
