"""PHASE-03: Run PySAM Single Owner for Factory A cases 1-4.

Uses PV/BESS sizes from slide reference (ALT-001 path per plan CON-001:
REopt Julia solver not required). Writes one result JSON per case to
artifacts/reports/factory_a/.

Financial assumptions match slide disclosures:
  - 70% debt, 8.5% VND, 10-yr tenor, 10% owner discount, 25-yr analysis
  - ESCO price = 90% x load-weighted EVN TOU rate
  - BESS grid charging disabled

Case 3 demand-charge post-processing:
  Adds monthly peak-demand savings at the slide's 209,459 VND/kW/month rate
  (and the repo medium-voltage 235,414 VND/kW/month for sensitivity).
  Monthly demand peak = max hourly grid-import kW per month.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.factory_a import (
    CAPEX_USD,
    EXCHANGE_RATE_VND_PER_USD,
    FACTORY_A_ANALYSIS_YEARS,
    FACTORY_A_DEBT_FRACTION,
    FACTORY_A_DEBT_INTEREST_RATE,
    FACTORY_A_DEBT_TENOR_YEARS,
    FACTORY_A_OWNER_DISCOUNT_RATE,
    OM_USD_PER_YEAR,
    SLIDE_REFERENCE,
    CAPACITY_CHARGE_SLIDE_VND_PER_KW_MONTH,
    CAPACITY_CHARGE_REPO_VND_PER_KW_MONTH,
    build_factory_a_load_8760,
    build_hourly_rate_series_vnd,
    _decision_14_tou_schedule,
    _load_weighted_avg_vnd,
    FACTORY_A_CUSTOMER_TYPE,
    FACTORY_A_VOLTAGE,
    FACTORY_A_ESCO_FRACTION,
)
from reopt_pysam_vn.pysam.pvwatts_battery import (
    DEFAULT_SOLAR_RESOURCE_FILE,
    run_pvwatts_battery_single_owner_model,
    PVWattsBatterySingleOwnerInputs,
)
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data


def _build_inputs_for_case(
    case_id: str,
    loads_kw: list[float],
    tariff_data: dict,
) -> PVWattsBatterySingleOwnerInputs:
    """Construct PVWattsBatterySingleOwnerInputs for one Factory A case."""
    ref = SLIDE_REFERENCE[case_id]

    # Tariff series — Decision 14 uses legacy schedule override
    if ref["tariff_regime"] == "decision_14_2025_legacy":
        rates_vnd = build_hourly_rate_series_vnd(
            tariff_data,
            FACTORY_A_CUSTOMER_TYPE,
            FACTORY_A_VOLTAGE,
            tou_schedule_override=_decision_14_tou_schedule(),
        )
    else:
        rates_vnd = build_hourly_rate_series_vnd(
            tariff_data, FACTORY_A_CUSTOMER_TYPE, FACTORY_A_VOLTAGE
        )

    # ESCO PPA price = 90% × load-weighted avg TOU rate (USD/kWh)
    avg_vnd = _load_weighted_avg_vnd(loads_kw, rates_vnd)
    esco_usd = FACTORY_A_ESCO_FRACTION * avg_vnd / EXCHANGE_RATE_VND_PER_USD

    buy_rate_usd = [r / EXCHANGE_RATE_VND_PER_USD for r in rates_vnd]
    sell_rate_usd = [0.0] * 8760  # no export revenue for BTM ESCO

    # PV and BESS from slide reference (ALT-001 path)
    pv_kw = ref["pv_mw"] * 1_000.0
    bess_kw = ref["bess_power_mw"] * 1_000.0
    bess_kwh = ref["bess_capacity_mwh"] * 1_000.0

    # For solar-only Case 4 PySAM requires battery_power_kw > 0 to avoid
    # validation errors. Use a nominal 1 kW / 1 kWh (will contribute
    # negligibly to results) and flag it in case metadata.
    solar_only = not ref["has_bess"]
    if solar_only:
        bess_kw = 1.0
        bess_kwh = 1.0

    return PVWattsBatterySingleOwnerInputs(
        system_capacity_kw=pv_kw,
        battery_power_kw=bess_kw,
        battery_capacity_kwh=bess_kwh,
        load_profile_kw=loads_kw,
        buy_rate_usd_per_kwh=buy_rate_usd,
        sell_rate_usd_per_kwh=sell_rate_usd,
        ppa_price_input_usd_per_kwh=esco_usd,
        solar_resource_file=str(DEFAULT_SOLAR_RESOURCE_FILE),
        analysis_years=FACTORY_A_ANALYSIS_YEARS,
        debt_fraction=FACTORY_A_DEBT_FRACTION,
        debt_interest_rate_fraction=FACTORY_A_DEBT_INTEREST_RATE,
        debt_tenor_years=FACTORY_A_DEBT_TENOR_YEARS,
        owner_discount_rate_fraction=FACTORY_A_OWNER_DISCOUNT_RATE,
        installed_cost_usd=CAPEX_USD[case_id],
        fixed_om_usd_per_year=OM_USD_PER_YEAR[case_id],
        battery_can_grid_charge=False,
        battery_dispatch_mode="peak_shaving_look_ahead",
        case_metadata={
            "case_id": case_id,
            "tariff_regime": ref["tariff_regime"],
            "solar_only": solar_only,
            "pv_kw_slide": ref["pv_mw"] * 1_000.0,
            "bess_kw_slide": ref["bess_power_mw"] * 1_000.0,
            "bess_kwh_slide": ref["bess_capacity_mwh"] * 1_000.0,
            "esco_usd_per_kwh": esco_usd,
            "load_weighted_avg_vnd": avg_vnd,
            "sizing_source": "slide_reference",
        },
    )


def _compute_demand_charge_savings(
    grid_to_load: list[float],
    loads_kw: list[float],
    capacity_rate_vnd_per_kw_month: float,
) -> dict:
    """Monthly demand-charge delta between BAU (no solar) and post-solar.

    Monthly demand peak = max hourly grid-import kW in that calendar month
    (hourly resolution; slide Case 3 note says 30-min cycle but repo data
    is hourly — Q-002 answer: use hourly max).
    """
    from datetime import datetime, timedelta

    start = datetime(2024, 1, 1)
    monthly_bau_peak: dict[int, float] = {m: 0.0 for m in range(1, 13)}
    monthly_post_peak: dict[int, float] = {m: 0.0 for m in range(1, 13)}

    for i in range(8760):
        m = (start + timedelta(hours=i)).month
        monthly_bau_peak[m] = max(monthly_bau_peak[m], loads_kw[i])
        monthly_post_peak[m] = max(monthly_post_peak[m], grid_to_load[i])

    rate_usd = capacity_rate_vnd_per_kw_month / EXCHANGE_RATE_VND_PER_USD
    annual_demand_savings_usd = sum(
        (monthly_bau_peak[m] - monthly_post_peak[m]) * rate_usd
        for m in range(1, 13)
    )
    return {
        "monthly_bau_peak_kw": monthly_bau_peak,
        "monthly_post_solar_peak_kw": monthly_post_peak,
        "capacity_rate_vnd_per_kw_month": capacity_rate_vnd_per_kw_month,
        "annual_demand_savings_usd": annual_demand_savings_usd,
    }


def run_all_cases() -> dict[str, dict]:
    vn = load_vietnam_data()
    tariff = vn.tariff
    loads_kw = build_factory_a_load_8760()

    results: dict[str, dict] = {}
    for case_id in ["case_1", "case_2", "case_3", "case_4"]:
        print(f"\n--- {case_id}: {SLIDE_REFERENCE[case_id]['label']} ---")
        inputs = _build_inputs_for_case(case_id, loads_kw, tariff)
        result = run_pvwatts_battery_single_owner_model(inputs)

        # Extract equity IRR and DSCR from annual cashflows
        cashflows = result.get("annual_cashflows", [])
        dscr_values = [row["dscr"] for row in cashflows if row.get("dscr") not in (None, 0)]
        avg_dscr = sum(dscr_values[:10]) / min(10, len(dscr_values)) if dscr_values else None
        min_dscr = min(dscr_values[:10]) if dscr_values else None

        energy = result.get("energy_summary", {})
        total_load = sum(loads_kw)
        matched_kwh = energy.get("annual_matched_load_kwh", 0.0)
        clean_pct = matched_kwh / total_load * 100.0 if total_load > 0 else 0.0

        # Year-1 bill savings approximation: load × buy_rate - grid_from_utility × buy_rate
        # PySAM Single Owner doesn't directly output "bill savings"; use NPV uplift proxy
        # Best proxy: year_one_bill_savings not directly available in this model config.
        # Use: savings = pv_ac_energy × ESCO_price / 0.90 × (1 - ESCO_fraction)
        #   = energy delivered × (EVN_rate - ESCO_rate)
        esco_usd = inputs.ppa_price_input_usd_per_kwh
        evn_avg_usd = esco_usd / FACTORY_A_ESCO_FRACTION
        approx_annual_savings_usd = matched_kwh * (evn_avg_usd - esco_usd)

        result["factory_a_metrics"] = {
            "clean_self_supply_pct": round(clean_pct, 2),
            "avg_dscr_yr1_10": avg_dscr,
            "min_dscr_yr1_10": min_dscr,
            "approx_annual_savings_usd": round(approx_annual_savings_usd, 0),
            "equity_irr_fraction": result["outputs"].get("equity_irr_fraction"),
            "npv_usd": result["outputs"].get("project_return_aftertax_npv_usd"),
        }

        # Case 3: add demand-charge savings
        if case_id == "case_3":
            # Approximate grid-to-load from PySAM energy balance
            grid_to_load = [
                max(0.0, l - s)
                for l, s in zip(
                    loads_kw,
                    [
                        energy.get("annual_matched_load_kwh", 0) / 8760.0
                    ]
                    * 8760,
                )
            ]
            dc_slide = _compute_demand_charge_savings(
                grid_to_load, loads_kw, CAPACITY_CHARGE_SLIDE_VND_PER_KW_MONTH
            )
            dc_repo = _compute_demand_charge_savings(
                grid_to_load, loads_kw, CAPACITY_CHARGE_REPO_VND_PER_KW_MONTH
            )
            result["demand_charge_post_processing"] = {
                "slide_rate": dc_slide,
                "repo_rate": dc_repo,
                "total_savings_usd_slide_rate": (
                    approx_annual_savings_usd + dc_slide["annual_demand_savings_usd"]
                ),
                "total_savings_usd_repo_rate": (
                    approx_annual_savings_usd + dc_repo["annual_demand_savings_usd"]
                ),
            }

        results[case_id] = result
        irr = result["outputs"].get("equity_irr_fraction")
        npv = result["outputs"].get("project_return_aftertax_npv_usd")
        print(f"  Clean supply: {clean_pct:.1f}% | IRR: {irr*100:.1f}% | NPV: ${npv:,.0f} | avgDSCR: {avg_dscr:.2f}")
        print(f"  Approx savings: ${approx_annual_savings_usd:,.0f}/yr")

    return results


def main() -> None:
    out_dir = REPO_ROOT / "artifacts" / "reports" / "factory_a"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = run_all_cases()

    for case_id, result in results.items():
        out_path = out_dir / f"2026-06-19_factory-a_{case_id}_pysam-results.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
