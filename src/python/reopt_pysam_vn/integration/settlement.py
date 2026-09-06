"""Generalized DPPA settlement engine for private-wire and virtual-CfD modes.

Extracted from dppa_case_2.py's buyer settlement logic and parameterized to
support any factory+project pair. See GAP-04 plan for design rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

from reopt_pysam_vn.common.series import pad_to_8760

VALID_MODES = ("private_wire", "virtual_cfd")
VALID_SETTLEMENT_RULES = ("matched_only", "contracted_volume")
VALID_EXCESS_TREATMENTS = ("curtail", "export_at_surplus", "cfd_on_excess")

HOURS = 8760

SettlementMode = Literal["private_wire", "virtual_cfd"]
SettlementQuantityRule = Literal["matched_only", "contracted_volume"]
ExcessTreatment = Literal["curtail", "export_at_surplus", "cfd_on_excess"]
MarketReferenceType = Literal["cfmp", "fmp", "proxy_cfmp_or_fmp"]


@dataclass(frozen=True)
class HourlySeries:
    """One validated 8760-hour series.

    Coerces elements to ``float`` and rejects any length other than 8760.
    Padding a short series is the caller's job (``common.series.pad_to_8760``);
    the seam fails loudly instead of guessing.
    """

    values: tuple[float, ...]

    def __post_init__(self) -> None:
        coerced = tuple(float(value) for value in self.values)
        if len(coerced) != HOURS:
            raise ValueError(
                f"HourlySeries needs exactly {HOURS} values, got {len(coerced)}"
            )
        object.__setattr__(self, "values", coerced)

    def to_list(self) -> list[float]:
        return list(self.values)


@dataclass(frozen=True)
class MarketReference:
    """Resolved hourly market series plus how it was obtained."""

    series_vnd_per_kwh: HourlySeries
    reference_type: MarketReferenceType
    proxy_fraction_of_evn: float | None
    method: str
    notes: tuple[str, ...] = ()


def resolve_market_reference(
    *,
    retail_vnd_per_kwh: list[float],
    cfmp_vnd_per_mwh: list[float] | None = None,
    fmp_vnd_per_mwh: list[float] | None = None,
    weighted_evn_price_vnd_per_kwh: float | None = None,
    wholesale_rate_vnd_per_kwh: float | None = None,
    vn: Any | None = None,
) -> MarketReference:
    """Resolve the 8760 market-reference series from explicit arguments.

    Priority: explicit CFMP (VND/MWh, converted to VND/kWh), then explicit FMP,
    then the proxy (hourly EVN retail scaled by wholesale/weighted-retail).
    Takes values, not ``extracted`` dicts, so key-name leaks across the seam
    become type errors. Never loads the data layer itself: pass ``vn``
    (or an explicit wholesale rate) when the proxy must resolve wholesale
    from ``market_prices``; with neither, wholesale falls back to 0.0.
    """
    if cfmp_vnd_per_mwh:
        series = HourlySeries(
            values=tuple(value / 1_000.0 for value in cfmp_vnd_per_mwh)
        )
        return MarketReference(
            series_vnd_per_kwh=series,
            reference_type="cfmp",
            proxy_fraction_of_evn=None,
            method="extracted_cfmp_vnd_per_mwh",
            notes=("CFMP series supplied directly (VND/MWh, converted to VND/kWh).",),
        )
    if fmp_vnd_per_mwh:
        series = HourlySeries(
            values=tuple(value / 1_000.0 for value in fmp_vnd_per_mwh)
        )
        return MarketReference(
            series_vnd_per_kwh=series,
            reference_type="fmp",
            proxy_fraction_of_evn=None,
            method="extracted_fmp_vnd_per_mwh",
            notes=("FMP series supplied directly (VND/MWh, converted to VND/kWh).",),
        )
    wholesale = wholesale_rate_vnd_per_kwh
    if not wholesale and vn is not None:
        from reopt_pysam_vn.common.assumptions import (
            market_wholesale_reference_vnd_per_kwh,
        )

        wholesale = market_wholesale_reference_vnd_per_kwh(vn)
    wholesale_value = float(wholesale or 0.0)
    weighted_value = float(weighted_evn_price_vnd_per_kwh or 0.0)
    fraction = wholesale_value / weighted_value if weighted_value else 0.0
    retail = HourlySeries(values=tuple(retail_vnd_per_kwh))
    proxy = HourlySeries(
        values=tuple(rate * fraction for rate in retail.values)
    )
    return MarketReference(
        series_vnd_per_kwh=proxy,
        reference_type="proxy_cfmp_or_fmp",
        proxy_fraction_of_evn=fraction,
        method="hourly_evn_tariff_scaled_by_wholesale_ratio",
        notes=(
            "Proxy uses the repo wholesale benchmark divided by the weighted "
            "EVN tariff and scales the hourly EVN retail series by that ratio.",
            "Replace with actual hourly CFMP/FMP once a trusted market series "
            "is available.",
        ),
    )


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
    regime_id: str = "decree_57_2025_legacy"

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

    @classmethod
    def from_regime(
        cls,
        regime_id: str,
        *,
        mode: str,
        strike_vnd_kwh: float,
        vn: Any | None = None,
        **overrides: Any,
    ) -> ContractParams:
        """Build a `ContractParams` whose policy fields resolve from the data
        layer for `regime_id`. `**overrides` wins over resolution."""
        from reopt_pysam_vn.common.assumptions import (
            dppa_adder_vnd_per_kwh,
            export_cap_fraction,
            kpp_loss_pct,
            surplus_rate_vnd_per_kwh,
        )
        from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

        if vn is None:
            vn = load_vietnam_data()

        resolved: dict[str, Any] = {
            "export_cap_pct": export_cap_fraction(vn, regime_id=regime_id) * 100.0,
            "surplus_rate_vnd_kwh": surplus_rate_vnd_per_kwh(vn, regime_id=regime_id),
            "dppa_adder_vnd_kwh": dppa_adder_vnd_per_kwh(vn),
            "kpp_pct": kpp_loss_pct(vn),
        }
        resolved.update(overrides)
        return cls(
            mode=mode,
            strike_vnd_kwh=strike_vnd_kwh,
            regime_id=regime_id,
            **resolved,
        )


def resolve_strike_weighted_discount(
    weighted_evn_price_vnd_per_kwh: float,
    discount_fraction: float = 0.05,
) -> float:
    """Strike anchored to the weighted EVN tariff minus a discount fraction.

    Single home for the ``weighted * (1 - discount)`` anchor previously copied
    across ``dppa_case_2``, ``dppa_case_3`` and ``ninhsim_solar_storage_60pct``.
    """
    return float(weighted_evn_price_vnd_per_kwh) * (1.0 - float(discount_fraction))


def resolve_samsung_strike(
    southern_ceiling_vnd_per_kwh: float,
    standard_rate_vnd_per_kwh: float,
    sweep_fraction: float = 0.0,
) -> float:
    """Samsung strike: Southern ground-mount ceiling swept toward avoided cost.

    ``sweep_fraction = 0`` returns the directional base strike (ceiling);
    ``sweep_fraction = 1`` returns the sweep top (EVN standard-hour avoided
    cost). Pure float math; the caller supplies deal-anchored endpoints.
    """
    base = float(southern_ceiling_vnd_per_kwh)
    top = float(standard_rate_vnd_per_kwh)
    return base + float(sweep_fraction) * (top - base)


@dataclass(frozen=True)
class SettlementInputs:
    """Typed replacement for the legacy ``settlement_inputs: dict``.

    Key-name leaks (``strike_price_vnd_per_kwh`` vs ``strike_vnd_kwh``,
    ``load_kwh_series`` vs ``loads_kw``, ``kpp_factor`` vs ``kpp_pct``)
    become type errors, not silent KeyErrors.
    """

    loads_kw: HourlySeries
    generation_kw: HourlySeries
    tariff_vnd_per_kwh: HourlySeries
    market_vnd_per_kwh: HourlySeries
    contract: ContractParams
    market_type: MarketReferenceType
    exchange_rate_vnd_per_usd: float
    notes: tuple[str, ...] = ()


def build_settlement_inputs(
    *,
    loads_kw: list[float],
    generation_kw: list[float],
    tariff_vnd_per_kwh: list[float],
    market: MarketReference,
    contract: ContractParams,
    exchange_rate_vnd_per_usd: float,
    notes: tuple[str, ...] = (),
) -> SettlementInputs:
    """Validate raw series into one ``SettlementInputs`` at the seam."""
    return SettlementInputs(
        loads_kw=HourlySeries(values=tuple(loads_kw)),
        generation_kw=HourlySeries(values=tuple(generation_kw)),
        tariff_vnd_per_kwh=HourlySeries(values=tuple(tariff_vnd_per_kwh)),
        market_vnd_per_kwh=market.series_vnd_per_kwh,
        contract=contract,
        market_type=market.reference_type,
        exchange_rate_vnd_per_usd=float(exchange_rate_vnd_per_usd),
        notes=tuple(notes),
    )


@dataclass(frozen=True)
class BuyerBenchmark:
    """EVN-only cost vs buyer all-in cost for one ``SettlementInputs``."""

    evn_only_cost_vnd: float
    buyer_cost_vnd: float
    buyer_savings_vs_evn_vnd: float
    buyer_premium_vs_evn_vnd: float
    buyer_blended_cost_vnd_per_kwh: float
    benchmark_blended_cost_vnd_per_kwh: float
    total_load_kwh: float


@dataclass
class SettlementResult:
    hourly_ledger: list[dict]
    annual_summary: dict
    contract_params: ContractParams
    market_source_label: str = ""


_pad_to_8760 = pad_to_8760

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
    total_cost = sum(kw * t for kw, t in zip(loads, tariff))
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
        regime_id="decree_57_2025_legacy",
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
        regime_id="decree_57_2025_legacy",
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
        regime_id="decree_57_2025_legacy",
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
        regime_id="decision_963_2026_current",
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
        regime_id="decision_963_2026_current",
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


def compute_hourly_settlement_typed(inputs: SettlementInputs) -> SettlementResult:
    """Typed entry to the hourly ledger: validate once, then run the engine."""
    return compute_hourly_settlement(
        inputs.loads_kw.to_list(),
        inputs.generation_kw.to_list(),
        inputs.tariff_vnd_per_kwh.to_list(),
        inputs.market_vnd_per_kwh.to_list(),
        inputs.contract,
        market_source_label=inputs.market_type,
    )


def compute_buyer_benchmark_typed(inputs: SettlementInputs) -> BuyerBenchmark:
    """Buyer vs EVN-only benchmark for one ``SettlementInputs``."""
    benchmark = compute_buyer_benchmark(
        inputs.loads_kw.to_list(), inputs.tariff_vnd_per_kwh.to_list()
    )
    settlement = compute_hourly_settlement_typed(inputs)
    buyer_cost = float(settlement.annual_summary["buyer_cost_vnd"])
    evn_cost = float(benchmark["evn_only_cost_vnd"])
    total_load = float(benchmark["total_load_kwh"])
    return BuyerBenchmark(
        evn_only_cost_vnd=evn_cost,
        buyer_cost_vnd=buyer_cost,
        buyer_savings_vs_evn_vnd=max(0.0, evn_cost - buyer_cost),
        buyer_premium_vs_evn_vnd=max(0.0, buyer_cost - evn_cost),
        buyer_blended_cost_vnd_per_kwh=float(
            settlement.annual_summary["buyer_blended_rate_vnd_kwh"]
        ),
        benchmark_blended_cost_vnd_per_kwh=float(benchmark["blended_rate_vnd_kwh"]),
        total_load_kwh=total_load,
    )


def run_strike_sweep_typed(
    inputs: SettlementInputs,
    strike_range_vnd_per_kwh: list[float],
) -> list[dict]:
    """Strike sweep over the typed seam; per-strike overrides via ``replace``."""
    return run_strike_sweep(
        inputs.loads_kw.to_list(),
        inputs.generation_kw.to_list(),
        inputs.tariff_vnd_per_kwh.to_list(),
        inputs.market_vnd_per_kwh.to_list(),
        inputs.contract,
        list(strike_range_vnd_per_kwh),
        market_source_label=inputs.market_type,
    )


def contract_params_for_legacy_case2(
    strike_vnd_kwh: float,
    dppa_adder_vnd_kwh: float,
    kpp_factor: float,
) -> ContractParams:
    """Case-2 virtual-CfD contract from legacy dict fields.

    Single home for the ``kpp_factor``-to-``kpp_pct`` conversion every legacy
    caller repeated; the matched-only/curtail shape is the Case-2 invariant.
    """
    return ContractParams(
        mode="virtual_cfd",
        strike_vnd_kwh=float(strike_vnd_kwh),
        settlement_quantity_rule="matched_only",
        excess_treatment="curtail",
        dppa_adder_vnd_kwh=float(dppa_adder_vnd_kwh),
        kpp_pct=(float(kpp_factor) - 1.0) * 100.0,
    )


def settlement_inputs_from_legacy_case2_dict(
    settlement_inputs: dict,
    *,
    strike_vnd_kwh: float | None = None,
) -> SettlementInputs:
    """Translate a legacy Case-2 ``settlement_inputs`` dict onto the typed seam.

    Short series are padded to 8760 (the legacy engine's zip-shortest
    tolerance, made explicit); padded zero hours contribute nothing to the
    totals. ``strike_vnd_kwh`` overrides the dict's strike for deal-specific
    anchors (e.g. the Samsung Southern-ceiling strike).
    """
    from reopt_pysam_vn.common.assumptions import exchange_rate as _resolve_fx
    from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

    market_series = pad_to_8760(
        [float(v) for v in settlement_inputs["market_reference_price_vnd_per_kwh_series"]]
    )
    notes = tuple(settlement_inputs.get("notes", []))
    market = MarketReference(
        series_vnd_per_kwh=HourlySeries(values=tuple(market_series)),
        reference_type=settlement_inputs["market_reference_price_type"],
        proxy_fraction_of_evn=None,
        method="legacy_case_2_dict_inputs",
        notes=notes,
    )
    raw_strike = strike_vnd_kwh
    if raw_strike is None:
        raw_strike = settlement_inputs["strike_price_vnd_per_kwh"]
    return build_settlement_inputs(
        loads_kw=pad_to_8760([float(v) for v in settlement_inputs["load_kwh_series"]]),
        generation_kw=pad_to_8760(
            [float(v) for v in settlement_inputs["contracted_generation_kwh_series"]]
        ),
        tariff_vnd_per_kwh=pad_to_8760(
            [float(v) for v in settlement_inputs["evn_retail_rate_vnd_per_kwh_series"]]
        ),
        market=market,
        contract=contract_params_for_legacy_case2(
            float(raw_strike),
            float(settlement_inputs["dppa_adder_vnd_per_kwh"]),
            float(settlement_inputs["kpp_factor"]),
        ),
        exchange_rate_vnd_per_usd=_resolve_fx(
            load_vietnam_data(),
            caller_value=settlement_inputs.get("exchange_rate_vnd_per_usd"),
        ),
        notes=notes,
    )


def legacy_case2_dict_from_result(
    result: SettlementResult,
    inputs: SettlementInputs,
    *,
    market_reference_price_type: str,
    settlement_quantity_rule: str,
    excess_generation_treatment: str,
) -> dict:
    """Translate a typed result back onto the historical Case-2 dict shape.

    The ``hour_index`` ledger, ``summary`` block and USD conversions are
    byte-identical to the pre-typed engine for the same inputs.
    """
    summary = result.annual_summary
    buyer_total = float(summary["buyer_cost_vnd"])
    total_load = float(summary["total_load_kwh"])
    blended_cost = float(summary["buyer_blended_rate_vnd_kwh"])
    exchange_rate = float(inputs.exchange_rate_vnd_per_usd)
    contract = inputs.contract
    return {
        "model": "Ninhsim DPPA Case 2 Buyer Settlement",
        "status": "ok",
        "market_reference_price_type": market_reference_price_type,
        "settlement_quantity_rule": settlement_quantity_rule,
        "excess_generation_treatment": excess_generation_treatment,
        "parameters": {
            "strike_price_vnd_per_kwh": float(contract.strike_vnd_kwh),
            "dppa_adder_vnd_per_kwh": float(contract.dppa_adder_vnd_kwh),
            "kpp_factor": float(contract.kpp_factor),
            "exchange_rate_vnd_per_usd": exchange_rate,
        },
        "hourly_ledger": [
            {
                "hour_index": entry["hour"],
                "load_kwh": entry["load_kwh"],
                "contracted_generation_kwh": entry["generation_kwh"],
                "matched_quantity_kwh": entry["matched_kwh"],
                "shortfall_quantity_kwh": entry["shortfall_kwh"],
                "excess_quantity_kwh": entry["excess_kwh"],
                "market_reference_price_vnd_per_kwh": entry["market_price_vnd_kwh"],
                "evn_retail_rate_vnd_per_kwh": entry["retail_price_vnd_kwh"],
                "buyer_evn_matched_payment_vnd": entry["evn_matched_payment_vnd"],
                "buyer_dppa_charge_vnd": entry["dppa_charge_vnd"],
                "buyer_shortfall_payment_vnd": entry["shortfall_payment_vnd"],
                "buyer_cfd_payment_vnd": entry["buyer_cfd_payment_vnd"],
                "buyer_total_payment_vnd": entry["buyer_total_payment_vnd"],
            }
            for entry in result.hourly_ledger
        ],
        "summary": {
            "matched_quantity_kwh": float(summary["matched_mwh"]) * 1000.0,
            "shortfall_quantity_kwh": float(summary["shortfall_mwh"]) * 1000.0,
            "excess_quantity_kwh": float(summary["excess_mwh"]) * 1000.0,
            "buyer_evn_matched_payment_vnd": float(
                summary["buyer_evn_matched_payment_vnd"]
            ),
            "buyer_dppa_charge_vnd": float(summary["buyer_dppa_charge_vnd"]),
            "buyer_shortfall_payment_vnd": float(
                summary["buyer_shortfall_payment_vnd"]
            ),
            "buyer_cfd_payment_vnd": float(summary["buyer_cfd_payment_vnd"]),
            "buyer_total_payment_vnd": buyer_total,
            "buyer_total_payment_usd": buyer_total / exchange_rate,
            "buyer_blended_cost_vnd_per_kwh": blended_cost,
            "buyer_blended_cost_usd_per_kwh": blended_cost / exchange_rate,
            "total_consumed_load_kwh": total_load,
            "hours_with_negative_cfd_credit": int(summary["hours_with_negative_cfd"]),
        },
        "notes": list(inputs.notes),
    }
