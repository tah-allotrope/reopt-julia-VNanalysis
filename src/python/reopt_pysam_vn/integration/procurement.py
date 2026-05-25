"""Procurement comparison engine: onsite vs offsite energy procurement evaluation.

Evaluates the same factory under both onsite (private-wire PPA) and offsite
(virtual CfD DPPA) procurement models, producing side-by-side buyer economics,
developer returns, and a recommended procurement route.

See GAP-02 plan for design rationale.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from reopt_pysam_vn.integration.settlement import (
    ContractParams,
    SettlementResult,
    compute_buyer_benchmark,
    compute_hourly_settlement,
)


@dataclass
class ProjectConfig:
    """Configuration for a candidate energy project."""
    project_id: str
    name: str
    technology: str  # solar, wind, solar_bess, wind_bess, hybrid
    capacity_mw: float
    bess_mw: float = 0.0
    bess_mwh: float = 0.0
    grid_connection: str = "offsite"  # onsite_private_wire, offsite_grid_connected
    generation_profile_kw: list[float] = field(default_factory=list)  # 8760
    location: dict[str, Any] = field(default_factory=dict)
    indicative_strike_vnd_kwh: float = 0.0
    dppa_structure: str = "virtual_cfd"  # private_wire, virtual_cfd, physical_dppa


@dataclass
class OnsiteEvaluation:
    """Results of evaluating an onsite (private-wire) procurement option."""
    project_config: ProjectConfig
    settlement: SettlementResult
    buyer_benchmark: dict
    buyer_savings_vs_evn_vnd: float
    developer_irr_pct: float | None = None
    developer_npv_usd: float | None = None
    re_penetration_pct: float = 0.0
    export_exposure_pct: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_config.project_id,
            "project_name": self.project_config.name,
            "procurement_mode": "onsite_private_wire",
            "buyer_cost_vnd": self.settlement.annual_summary["buyer_cost_vnd"],
            "buyer_blended_rate_vnd_kwh": self.settlement.annual_summary["buyer_blended_rate_vnd_kwh"],
            "buyer_savings_vs_evn_vnd": self.buyer_savings_vs_evn_vnd,
            "developer_revenue_vnd": self.settlement.annual_summary["developer_revenue_vnd"],
            "developer_irr_pct": self.developer_irr_pct,
            "developer_npv_usd": self.developer_npv_usd,
            "re_penetration_pct": self.re_penetration_pct,
            "export_exposure_pct": self.export_exposure_pct,
            "matched_mwh": self.settlement.annual_summary["matched_mwh"],
            "exported_mwh": self.settlement.annual_summary["exported_mwh"],
            "curtailed_mwh": self.settlement.annual_summary["curtailed_mwh"],
            "notes": self.notes,
        }


@dataclass
class OffsiteEvaluation:
    """Results of evaluating an offsite (virtual CfD) procurement option."""
    project_config: ProjectConfig
    settlement: SettlementResult
    buyer_benchmark: dict
    buyer_savings_vs_evn_vnd: float
    developer_irr_pct: float | None = None
    developer_npv_usd: float | None = None
    re_penetration_pct: float = 0.0
    fmp_risk_score: float = 0.0  # 0-100, higher = more FMP volatility exposure
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_config.project_id,
            "project_name": self.project_config.name,
            "procurement_mode": "offsite_virtual_cfd",
            "buyer_cost_vnd": self.settlement.annual_summary["buyer_cost_vnd"],
            "buyer_blended_rate_vnd_kwh": self.settlement.annual_summary["buyer_blended_rate_vnd_kwh"],
            "buyer_savings_vs_evn_vnd": self.buyer_savings_vs_evn_vnd,
            "developer_revenue_vnd": self.settlement.annual_summary["developer_revenue_vnd"],
            "developer_irr_pct": self.developer_irr_pct,
            "developer_npv_usd": self.developer_npv_usd,
            "re_penetration_pct": self.re_penetration_pct,
            "fmp_risk_score": self.fmp_risk_score,
            "matched_mwh": self.settlement.annual_summary["matched_mwh"],
            "excess_mwh": self.settlement.annual_summary["excess_mwh"],
            "hours_with_negative_cfd": self.settlement.annual_summary["hours_with_negative_cfd"],
            "notes": self.notes,
        }


def evaluate_onsite(
    loads_kw: list[float],
    project: ProjectConfig,
    tariff_rates_vnd_kwh: list[float],
    contract_params: ContractParams | None = None,
    fmp_vnd_kwh: list[float] | None = None,
) -> OnsiteEvaluation:
    """Evaluate an onsite (private-wire) procurement option.

    Args:
        loads_kw: 8760 hourly factory load in kW.
        project: Project configuration with generation profile.
        tariff_rates_vnd_kwh: 8760 hourly EVN retail rates (VND/kWh).
        contract_params: Settlement contract parameters. Defaults to
            private-wire preset with project's indicative strike.
        fmp_vnd_kwh: 8760 hourly FMP (not used for private-wire settlement,
            but needed for benchmark computation).

    Returns:
        OnsiteEvaluation with buyer economics and project metrics.
    """
    if contract_params is None:
        strike = project.indicative_strike_vnd_kwh
        if strike <= 0:
            strike = 1012.0  # Default south ceiling for solar-only
        contract_params = ContractParams(
            mode="private_wire",
            strike_vnd_kwh=strike,
            excess_treatment="export_at_surplus",
            export_cap_pct=20.0,
            surplus_rate_vnd_kwh=671.0,
        )

    generation = project.generation_profile_kw
    if not generation:
        raise ValueError(
            f"Project {project.project_id} has no generation_profile_kw. "
            "Provide an 8760 hourly series or pre-solve with REopt."
        )

    settlement = compute_hourly_settlement(
        loads_kw, generation, tariff_rates_vnd_kwh,
        fmp_vnd_kwh or [0.0] * 8760, contract_params,
        market_source_label="onsite_private_wire",
    )

    benchmark = compute_buyer_benchmark(loads_kw, tariff_rates_vnd_kwh)
    evn_cost = benchmark["evn_only_cost_vnd"]
    buyer_cost = settlement.annual_summary["buyer_cost_vnd"]
    savings = evn_cost - buyer_cost

    total_load = sum(loads_kw)
    matched = settlement.annual_summary["matched_mwh"] * 1000.0
    re_penetration = (matched / total_load * 100.0) if total_load > 0 else 0.0

    exported = settlement.annual_summary["exported_mwh"] * 1000.0
    total_gen = sum(generation)
    export_exposure = (exported / total_gen * 100.0) if total_gen > 0 else 0.0

    return OnsiteEvaluation(
        project_config=project,
        settlement=settlement,
        buyer_benchmark=benchmark,
        buyer_savings_vs_evn_vnd=savings,
        re_penetration_pct=round(re_penetration, 2),
        export_exposure_pct=round(export_exposure, 2),
    )


def evaluate_offsite(
    loads_kw: list[float],
    project: ProjectConfig,
    tariff_rates_vnd_kwh: list[float],
    fmp_vnd_kwh: list[float],
    contract_params: ContractParams | None = None,
) -> OffsiteEvaluation:
    """Evaluate an offsite (virtual CfD) procurement option.

    Args:
        loads_kw: 8760 hourly factory load in kW.
        project: Project configuration with generation profile.
        tariff_rates_vnd_kwh: 8760 hourly EVN retail rates (VND/kWh).
        fmp_vnd_kwh: 8760 hourly FMP/CFMP (VND/kWh).
        contract_params: Settlement contract parameters. Defaults to
            virtual-CfD matched-only preset.

    Returns:
        OffsiteEvaluation with buyer economics and project metrics.
    """
    if contract_params is None:
        strike = project.indicative_strike_vnd_kwh
        if strike <= 0:
            strike = 1800.0  # Default CfD strike
        contract_params = ContractParams(
            mode="virtual_cfd",
            strike_vnd_kwh=strike,
            excess_treatment="curtail",
        )

    generation = project.generation_profile_kw
    if not generation:
        raise ValueError(
            f"Project {project.project_id} has no generation_profile_kw. "
            "Provide an 8760 hourly series or use a pre-solved result."
        )

    settlement = compute_hourly_settlement(
        loads_kw, generation, tariff_rates_vnd_kwh,
        fmp_vnd_kwh, contract_params,
        market_source_label="offsite_virtual_cfd",
    )

    benchmark = compute_buyer_benchmark(loads_kw, tariff_rates_vnd_kwh)
    evn_cost = benchmark["evn_only_cost_vnd"]
    buyer_cost = settlement.annual_summary["buyer_cost_vnd"]
    savings = evn_cost - buyer_cost

    total_load = sum(loads_kw)
    matched = settlement.annual_summary["matched_mwh"] * 1000.0
    re_penetration = (matched / total_load * 100.0) if total_load > 0 else 0.0

    # FMP risk score: based on CfD volatility
    negative_cfd_hours = settlement.annual_summary["hours_with_negative_cfd"]
    fmp_risk = min(100.0, (negative_cfd_hours / 8760.0) * 200.0)  # Scale: 50% negative = 100 risk

    return OffsiteEvaluation(
        project_config=project,
        settlement=settlement,
        buyer_benchmark=benchmark,
        buyer_savings_vs_evn_vnd=savings,
        re_penetration_pct=round(re_penetration, 2),
        fmp_risk_score=round(fmp_risk, 1),
    )


@dataclass
class ProcurementComparison:
    """Side-by-side comparison of onsite vs offsite procurement options."""
    factory_id: str
    factory_summary: dict
    onsite: OnsiteEvaluation | None
    offsite: OffsiteEvaluation | None
    delta: dict = field(default_factory=dict)
    recommendation: str = ""
    recommendation_reason: str = ""
    regulatory_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "factory_id": self.factory_id,
            "factory_summary": self.factory_summary,
            "onsite": self.onsite.to_dict() if self.onsite else None,
            "offsite": self.offsite.to_dict() if self.offsite else None,
            "delta": self.delta,
            "recommendation": self.recommendation,
            "recommendation_reason": self.recommendation_reason,
            "regulatory_flags": self.regulatory_flags,
        }


def compare_procurement_options(
    onsite: OnsiteEvaluation | None,
    offsite: OffsiteEvaluation | None,
    factory_metadata: dict | None = None,
) -> ProcurementComparison:
    """Produce a side-by-side comparison with recommendation.

    Args:
        onsite: Onsite evaluation results (None if not evaluated).
        offsite: Offsite evaluation results (None if not evaluated).
        factory_metadata: Optional factory metadata for the summary.

    Returns:
        ProcurementComparison with delta, recommendation, and regulatory flags.
    """
    factory_summary = factory_metadata or {}
    factory_id = factory_summary.get("factory_id", "unknown")

    delta: dict = {}
    recommendation = ""
    reason = ""
    flags: list[str] = []

    if onsite and offsite:
        cost_delta = onsite.settlement.annual_summary["buyer_cost_vnd"] - offsite.settlement.annual_summary["buyer_cost_vnd"]
        savings_delta = onsite.buyer_savings_vs_evn_vnd - offsite.buyer_savings_vs_evn_vnd
        dev_rev_delta = onsite.settlement.annual_summary["developer_revenue_vnd"] - offsite.settlement.annual_summary["developer_revenue_vnd"]

        delta = {
            "buyer_cost_delta_vnd": cost_delta,
            "buyer_savings_delta_vnd": savings_delta,
            "developer_revenue_delta_vnd": dev_rev_delta,
            "onsite_cheaper_by_pct": round(abs(cost_delta) / offsite.settlement.annual_summary["buyer_cost_vnd"] * 100, 1) if offsite.settlement.annual_summary["buyer_cost_vnd"] else 0.0,
        }

        onsite_viable = onsite.buyer_savings_vs_evn_vnd > 0
        offsite_viable = offsite.buyer_savings_vs_evn_vnd > 0

        if onsite_viable and offsite_viable:
            if onsite.settlement.annual_summary["buyer_cost_vnd"] < offsite.settlement.annual_summary["buyer_cost_vnd"]:
                recommendation = "onsite"
                reason = f"Onsite saves {abs(cost_delta):,.0f} VND more than offsite for the buyer"
            else:
                recommendation = "offsite"
                reason = f"Offsite saves {abs(cost_delta):,.0f} VND more than onsite for the buyer"
        elif onsite_viable:
            recommendation = "onsite"
            reason = "Only onsite produces buyer savings vs EVN"
        elif offsite_viable:
            recommendation = "offsite"
            reason = "Only offsite produces buyer savings vs EVN"
        else:
            recommendation = "neither"
            reason = "Both options produce buyer premium vs EVN — reconsider strike or physical sizing"

        # Regulatory flags
        if onsite.export_exposure_pct > 5.0:
            flags.append(f"Decree 57 export exposure: {onsite.export_exposure_pct:.1f}% of generation")
        if offsite.fmp_risk_score > 50.0:
            flags.append(f"High FMP volatility risk: {offsite.fmp_risk_score:.0f}/100 ({offsite.settlement.annual_summary['hours_with_negative_cfd']} negative CfD hours)")
        if onsite.settlement.annual_summary.get("exported_mwh", 0) * 1000 > 0:
            flags.append("Onsite export subject to Decree 57 surplus purchase rate (671 VND/kWh)")

    elif onsite:
        recommendation = "onsite"
        reason = "Only onsite option evaluated — no offsite comparison available"
        if onsite.export_exposure_pct > 5.0:
            flags.append(f"Decree 57 export exposure: {onsite.export_exposure_pct:.1f}%")
    elif offsite:
        recommendation = "offsite"
        reason = "Only offsite option evaluated — no onsite comparison available"
        if offsite.fmp_risk_score > 50.0:
            flags.append(f"High FMP volatility risk: {offsite.fmp_risk_score:.0f}/100")
    else:
        recommendation = "neither"
        reason = "No procurement options evaluated"

    return ProcurementComparison(
        factory_id=factory_id,
        factory_summary=factory_summary,
        onsite=onsite,
        offsite=offsite,
        delta=delta,
        recommendation=recommendation,
        recommendation_reason=reason,
        regulatory_flags=flags,
    )


def load_factory_loads(path: str | Path) -> list[float]:
    """Load 8760 hourly factory loads from an interim JSON artifact.

    Supports both `loads_kw` (GAP-01 format) and `load_profile_kw` (legacy format).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "loads_kw" in data:
        return data["loads_kw"][:8760]
    if "load_profile_kw" in data:
        return data["load_profile_kw"][:8760]
    if "data" in data and "loads_kw" in data["data"]:
        return data["data"]["loads_kw"][:8760]
    raise ValueError(
        f"Cannot find load profile in {path}. Expected 'loads_kw' or 'load_profile_kw' key."
    )


def load_tariff_rates(vn_data_path: str | Path, customer_type: str = "industrial",
                      voltage_level: str = "medium_voltage_22kv_to_110kv") -> list[float]:
    """Build 8760 EVN tariff rates from Vietnam data.

    Falls back to a flat rate if the tariff data cannot be loaded.
    """
    try:
        from reopt_pysam_vn.reopt.preprocess import load_vietnam_data, build_vietnam_tariff
        vn = load_vietnam_data(str(vn_data_path))
        tariff = build_vietnam_tariff(vn, customer_type, voltage_level)
        return tariff.get("tou_energy_rates_per_kwh", [2000.0] * 8760)[:8760]
    except Exception:
        return [2000.0] * 8760  # Flat fallback
