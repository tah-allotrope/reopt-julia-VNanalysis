"""Configuration helpers for PySAM-backed Vietnam finance workflows."""

from __future__ import annotations

from dataclasses import dataclass

from reopt_pysam_vn.reopt.preprocess import VNData


@dataclass(frozen=True)
class PySAMRuntimeConfig:
    """Runtime configuration for the Phase 4 Single Owner workflow."""

    model_name: str = "PySAM Single Owner"
    system_config: str = "CustomGenerationProfileSingleOwner"
    currency: str = "USD"
    country: str = "Vietnam"
    local_python: str = ".venv/Scripts/python.exe"


@dataclass(frozen=True)
class VietnamFinanceDefaults:
    """Vietnam-focused finance defaults applied by the local wrapper layer."""

    analysis_years: int
    owner_tax_rate_fraction: float
    owner_discount_rate_fraction: float
    offtaker_discount_rate_fraction: float
    elec_cost_escalation_rate_fraction: float
    om_cost_escalation_rate_fraction: float
    inflation_rate_fraction: float
    debt_fraction: float
    debt_interest_rate_fraction: float
    debt_tenor_years: int
    # "vn_sl_15yr" = VN Circular 45 SL 15-yr | "vn_sl_10yr" = SL 10-yr custom | "us_macrs_5yr" = US MACRS
    depreciation_schedule: str


def build_vietnam_finance_defaults(vn: VNData) -> VietnamFinanceDefaults:
    """Build wrapper-driven Vietnam finance defaults from repo data and precedent."""

    profile = vn.financials["renewable_energy_preferential"]
    blended_tax_rate = float(
        profile.get("tax_holiday", {}).get(
            "effective_blended_rate_25yr",
            profile["owner_tax_rate_fraction"],
        )
    )
    reference_rates = vn.financials.get("reference_rates", {})
    inflation_rate_fraction = float(
        reference_rates.get("inflation_rate_5yr_avg", 0.035)
    )

    return VietnamFinanceDefaults(
        analysis_years=int(profile["analysis_years"]),
        owner_tax_rate_fraction=blended_tax_rate,
        owner_discount_rate_fraction=float(profile["owner_discount_rate_fraction"]),
        offtaker_discount_rate_fraction=float(
            profile["offtaker_discount_rate_fraction"]
        ),
        elec_cost_escalation_rate_fraction=float(
            profile["elec_cost_escalation_rate_fraction"]
        ),
        om_cost_escalation_rate_fraction=float(
            profile["om_cost_escalation_rate_fraction"]
        ),
        inflation_rate_fraction=inflation_rate_fraction,
        debt_fraction=0.70,
        debt_interest_rate_fraction=0.085,
        debt_tenor_years=10,
        depreciation_schedule="vn_sl_15yr",
    )
