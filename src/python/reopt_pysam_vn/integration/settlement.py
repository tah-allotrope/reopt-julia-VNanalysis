"""Generalized DPPA settlement engine for private-wire and virtual-CfD modes.

Extracted from dppa_case_2.py's buyer settlement logic and parameterized to
support any factory+project pair. See GAP-04 plan for design rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


VALID_MODES = ("private_wire", "virtual_cfd")
VALID_SETTLEMENT_RULES = ("matched_only", "contracted_volume")
VALID_EXCESS_TREATMENTS = ("curtail", "export_at_surplus", "cfd_on_excess")


@dataclass(frozen=True)
class ContractParams:
    mode: str
    strike_vnd_kwh: float
    escalation_rate: float = 0.05
    settlement_quantity_rule: str = "matched_only"
    excess_treatment: str = "curtail"
    export_cap_pct: float = 20.0
    surplus_rate_vnd_kwh: float = 671.0
    dppa_adder_vnd_kwh: float = 523.34
    kpp_pct: float = 2.7263
    shortfall_billing: str = "evn_tariff"

    def __post_init__(self):
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"mode must be one of {VALID_MODES}, got '{self.mode}'"
            )
        if self.settlement_quantity_rule not in VALID_SETTLEMENT_RULES:
            raise ValueError(
                f"settlement_quantity_rule must be one of {VALID_SETTLEMENT_RULES}, "
                f"got '{self.settlement_quantity_rule}'"
            )
        if self.excess_treatment not in VALID_EXCESS_TREATMENTS:
            raise ValueError(
                f"excess_treatment must be one of {VALID_EXCESS_TREATMENTS}, "
                f"got '{self.excess_treatment}'"
            )

    @property
    def kpp_factor(self) -> float:
        return 1.0 + self.kpp_pct / 100.0


@dataclass
class SettlementResult:
    hourly_ledger: list[dict]
    annual_summary: dict
    contract_params: ContractParams
    market_source_label: str = ""


def _pad_to_8760(series: list[float]) -> list[float]:
    if len(series) >= 8760:
        return [float(v) for v in series[:8760]]
    return [float(v) for v in series] + [0.0] * (8760 - len(series))


def compute_hourly_settlement(
    loads_kw: list[float],
    generation_kw: list[float],
    tariff_rates_vnd_kwh: list[float],
    fmp_vnd_kwh: list[float],
    contract_params: ContractParams,
    *,
    market_source_label: str = "",
) -> SettlementResult:
    loads = _pad_to_8760(loads_kw)
    generation = _pad_to_8760(generation_kw)
    tariff = _pad_to_8760(tariff_rates_vnd_kwh)
    fmp = _pad_to_8760(fmp_vnd_kwh)

    p = contract_params
    kpp = p.kpp_factor
    export_cap_fraction = p.export_cap_pct / 100.0

    hourly_ledger: list[dict] = []
    matched_total = 0.0
    shortfall_total = 0.0
    excess_total = 0.0
    exported_total = 0.0
    curtailed_total = 0.0
    evn_matched_total = 0.0
    dppa_charge_total = 0.0
    shortfall_payment_total = 0.0
    cfd_total = 0.0
    buyer_total = 0.0
    developer_revenue_total = 0.0
    negative_cfd_hours = 0

    for hour_idx in range(8760):
        load_kwh = loads[hour_idx]
        gen_kwh = generation[hour_idx]
        market_price = fmp[hour_idx]
        retail_price = tariff[hour_idx]

        matched = min(load_kwh, gen_kwh)
        shortfall = max(0.0, load_kwh - matched)
        excess = max(0.0, gen_kwh - matched)

        if p.excess_treatment == "curtail":
            exported = 0.0
            curtailed = excess
        elif p.excess_treatment == "export_at_surplus":
            max_export = gen_kwh * export_cap_fraction
            exported = min(excess, max_export)
            curtailed = excess - exported
        else:  # cfd_on_excess
            exported = 0.0
            curtailed = 0.0

        if p.mode == "virtual_cfd":
            evn_matched_payment = matched * market_price * kpp
            dppa_charge = matched * p.dppa_adder_vnd_kwh
            shortfall_payment = shortfall * retail_price
            buyer_cfd = matched * (p.strike_vnd_kwh - market_price)

            if p.excess_treatment == "cfd_on_excess":
                buyer_cfd += excess * (p.strike_vnd_kwh - market_price)

            buyer_total_h = (
                evn_matched_payment + dppa_charge + shortfall_payment + buyer_cfd
            )

            developer_revenue_h = (
                matched * p.strike_vnd_kwh
                + exported * p.surplus_rate_vnd_kwh
            )
        else:  # private_wire
            evn_matched_payment = matched * p.strike_vnd_kwh
            dppa_charge = 0.0
            shortfall_payment = shortfall * retail_price
            buyer_cfd = 0.0
            buyer_total_h = evn_matched_payment + shortfall_payment

            developer_revenue_h = (
                matched * p.strike_vnd_kwh
                + exported * p.surplus_rate_vnd_kwh
            )

        if buyer_cfd < 0.0:
            negative_cfd_hours += 1

        hourly_ledger.append({
            "hour": hour_idx + 1,
            "load_kwh": load_kwh,
            "generation_kwh": gen_kwh,
            "matched_kwh": matched,
            "shortfall_kwh": shortfall,
            "excess_kwh": excess,
            "exported_kwh": exported,
            "curtailed_kwh": curtailed,
            "market_price_vnd_kwh": market_price,
            "retail_price_vnd_kwh": retail_price,
            "evn_matched_payment_vnd": evn_matched_payment,
            "dppa_charge_vnd": dppa_charge,
            "shortfall_payment_vnd": shortfall_payment,
            "buyer_cfd_payment_vnd": buyer_cfd,
            "buyer_total_payment_vnd": buyer_total_h,
            "developer_revenue_vnd": developer_revenue_h,
        })

        matched_total += matched
        shortfall_total += shortfall
        excess_total += excess
        exported_total += exported
        curtailed_total += curtailed
        evn_matched_total += evn_matched_payment
        dppa_charge_total += dppa_charge
        shortfall_payment_total += shortfall_payment
        cfd_total += buyer_cfd
        buyer_total += buyer_total_h
        developer_revenue_total += developer_revenue_h

    total_load = sum(loads)
    blended_rate = buyer_total / total_load if total_load else 0.0

    annual_summary = {
        "matched_mwh": matched_total / 1000.0,
        "shortfall_mwh": shortfall_total / 1000.0,
        "excess_mwh": excess_total / 1000.0,
        "exported_mwh": exported_total / 1000.0,
        "curtailed_mwh": curtailed_total / 1000.0,
        "buyer_evn_matched_payment_vnd": evn_matched_total,
        "buyer_dppa_charge_vnd": dppa_charge_total,
        "buyer_shortfall_payment_vnd": shortfall_payment_total,
        "buyer_cfd_payment_vnd": cfd_total,
        "buyer_cost_vnd": buyer_total,
        "buyer_blended_rate_vnd_kwh": blended_rate,
        "developer_revenue_vnd": developer_revenue_total,
        "buyer_savings_vs_evn_vnd": 0.0,
        "total_load_kwh": total_load,
        "hours_with_negative_cfd": negative_cfd_hours,
    }

    return SettlementResult(
        hourly_ledger=hourly_ledger,
        annual_summary=annual_summary,
        contract_params=contract_params,
        market_source_label=market_source_label,
    )


def compute_buyer_benchmark(
    loads_kw: list[float],
    tariff_rates_vnd_kwh: list[float],
) -> dict:
    loads = _pad_to_8760(loads_kw)
    tariff = _pad_to_8760(tariff_rates_vnd_kwh)
    total_cost = sum(l * t for l, t in zip(loads, tariff))
    total_load = sum(loads)
    blended = total_cost / total_load if total_load else 0.0
    return {
        "evn_only_cost_vnd": total_cost,
        "total_load_kwh": total_load,
        "blended_rate_vnd_kwh": blended,
    }


PRESET_CONTRACTS: dict[str, ContractParams] = {
    "decree57_private_wire_standard": ContractParams(
        mode="private_wire",
        strike_vnd_kwh=1012.0,
        escalation_rate=0.05,
        settlement_quantity_rule="matched_only",
        excess_treatment="export_at_surplus",
        export_cap_pct=20.0,
        surplus_rate_vnd_kwh=671.0,
        dppa_adder_vnd_kwh=0.0,
        kpp_pct=0.0,
    ),
    "virtual_cfd_matched_only": ContractParams(
        mode="virtual_cfd",
        strike_vnd_kwh=1800.0,
        escalation_rate=0.05,
        settlement_quantity_rule="matched_only",
        excess_treatment="curtail",
        export_cap_pct=20.0,
        surplus_rate_vnd_kwh=671.0,
        dppa_adder_vnd_kwh=523.34,
        kpp_pct=2.7263,
    ),
    "virtual_cfd_full_volume": ContractParams(
        mode="virtual_cfd",
        strike_vnd_kwh=1800.0,
        escalation_rate=0.05,
        settlement_quantity_rule="contracted_volume",
        excess_treatment="cfd_on_excess",
        export_cap_pct=20.0,
        surplus_rate_vnd_kwh=671.0,
        dppa_adder_vnd_kwh=523.34,
        kpp_pct=2.7263,
    ),
    "physical_dppa_export_50pct": ContractParams(
        mode="private_wire",
        strike_vnd_kwh=1012.0,
        escalation_rate=0.05,
        settlement_quantity_rule="matched_only",
        excess_treatment="export_at_surplus",
        export_cap_pct=50.0,
        surplus_rate_vnd_kwh=671.0,
        dppa_adder_vnd_kwh=0.0,
        kpp_pct=0.0,
    ),
    "decree243_export_50pct_standard": ContractParams(
        mode="private_wire",
        strike_vnd_kwh=1012.0,
        escalation_rate=0.05,
        settlement_quantity_rule="matched_only",
        excess_treatment="export_at_surplus",
        export_cap_pct=50.0,
        surplus_rate_vnd_kwh=671.0,
        dppa_adder_vnd_kwh=0.0,
        kpp_pct=0.0,
    ),
}


def run_strike_sweep(
    loads_kw: list[float],
    generation_kw: list[float],
    tariff_rates_vnd_kwh: list[float],
    fmp_vnd_kwh: list[float],
    base_params: ContractParams,
    strike_range_vnd_kwh: list[float],
    *,
    market_source_label: str = "",
) -> list[dict]:
    benchmark = compute_buyer_benchmark(loads_kw, tariff_rates_vnd_kwh)
    evn_cost = benchmark["evn_only_cost_vnd"]

    results = []
    for strike in strike_range_vnd_kwh:
        params = replace(base_params, strike_vnd_kwh=strike)
        settlement = compute_hourly_settlement(
            loads_kw, generation_kw, tariff_rates_vnd_kwh, fmp_vnd_kwh,
            params, market_source_label=market_source_label,
        )
        summary = settlement.annual_summary
        savings = evn_cost - summary["buyer_cost_vnd"]
        results.append({
            "strike_vnd_kwh": strike,
            "buyer_cost_vnd": summary["buyer_cost_vnd"],
            "buyer_blended_rate_vnd_kwh": summary["buyer_blended_rate_vnd_kwh"],
            "developer_revenue_vnd": summary["developer_revenue_vnd"],
            "buyer_savings_vs_evn_vnd": savings,
            "matched_mwh": summary["matched_mwh"],
            "excess_mwh": summary["excess_mwh"],
            "hours_with_negative_cfd": summary["hours_with_negative_cfd"],
        })

    return results
