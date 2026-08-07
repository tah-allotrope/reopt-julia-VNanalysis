"""Phase E: Controller-vs-optimizer dispatch gap analysis for Saigon18 DPPA Case 3."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.integration.dppa_case_3 import (
    BASE_BESS_KW,
    BASE_BESS_KWH,
    BASE_PV_KWP,
    DEFAULT_DPPA_ADDER_VND_PER_KWH,
    DEFAULT_KPP_FACTOR,
    load_saigon18_cfmp_series,
    load_saigon18_fmp_series,
    load_saigon18_load_series,
)

REPORT_DATE = "2026-04-21"
DEFAULT_EXTRACTED = (
    REPO_ROOT
    / "data"
    / "interim"
    / "saigon18"
    / "2026-03-20_saigon18_extracted_inputs.json"
)
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "reports" / "saigon18"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


CONTROLLER_CHARGE_WINDOW_HOURS = list(range(10, 16))
CONTROLLER_DISCHARGE_WINDOW_HOURS = list(range(18, 23))
CONTROLLER_BESS_KW = BASE_BESS_KW
CONTROLLER_BESS_KWH = BASE_BESS_KWH
CONTROLLER_BESS_ROUNDTRIP = 0.9025
CONTROLLER_DOD = 0.85


def compute_controller_dispatch(
    load: list[float],
    pv_kw: float,
    bess_kw: float,
    bess_kwh: float,
    pv_production_series: list[float] | None = None,
) -> dict:
    n = len(load)
    bess_soc = [bess_kwh * CONTROLLER_DOD] * n
    bess_to_load = [0.0] * n
    bess_to_grid = [0.0] * n
    cur_soc = bess_kwh * CONTROLLER_DOD

    if pv_production_series is None:
        solar_fraction = 0.4
        peak_solar_hour = 12
        pv_series = [
            max(0.0, pv_kw * solar_fraction * (1.0 - abs(h - peak_solar_hour) / 6.0))
            for h in range(n)
        ]
    else:
        pv_series = pv_production_series

    for h in range(n):
        day = h // 24
        hour = h % 24
        weekday = day % 7 < 5

        excess = max(0.0, pv_series[h] - load[h])
        if hour in CONTROLLER_CHARGE_WINDOW_HOURS and weekday:
            available_capacity = bess_kwh - cur_soc
            charge_kw = min(bess_kw, available_capacity / 1.0, excess)
            cur_soc += charge_kw
            bess_soc[h] = cur_soc
            bess_to_load[h] = 0.0
            bess_to_grid[h] = 0.0
        elif hour in CONTROLLER_DISCHARGE_WINDOW_HOURS and weekday:
            discharge_kw = min(bess_kw, cur_soc - (bess_kwh * 0.2))
            cur_soc -= discharge_kw
            bess_soc[h] = cur_soc
            bess_to_load[h] = discharge_kw
            bess_to_grid[h] = 0.0
        else:
            bess_soc[h] = cur_soc
            bess_to_load[h] = 0.0
            bess_to_grid[h] = 0.0

    annual_discharged = sum(bess_to_load)
    annual_charged = sum(bess_to_grid)
    annual_pv_gen = sum(pv_series)
    annual_load = sum(load)

    return {
        "controller_bess_kw": bess_kw,
        "controller_bess_kwh": bess_kwh,
        "annual_pv_generation_kwh": round(annual_pv_gen, 2),
        "annual_load_kwh": round(annual_load, 2),
        "annual_bess_discharged_kwh": round(annual_discharged, 2),
        "annual_bess_charged_kwh": round(annual_charged, 2),
        "matched_kwh": round(annual_discharged, 2),
        "shortfall_kwh": round(
            max(0.0, annual_load - annual_pv_gen - annual_discharged), 2
        ),
        "excess_kwh": round(max(0.0, annual_pv_gen - annual_load - annual_charged), 2),
    }


def compute_settlement_from_dispatch(
    dispatch: dict,
    load: list[float],
    market_price: float,
    strike: float,
    tou_avg: float,
    bess_kw: float,
    pv_kw: float,
) -> dict:
    matched = dispatch["matched_kwh"]
    shortfall = dispatch["shortfall_kwh"]
    excess = dispatch["excess_kwh"]

    evn_matched = matched * market_price * DEFAULT_KPP_FACTOR
    dppa_charge = matched * DEFAULT_DPPA_ADDER_VND_PER_KWH
    shortfall_payment = shortfall * tou_avg
    cfd = matched * (strike - market_price)
    total = evn_matched + dppa_charge + shortfall_payment + cfd
    blended = total / sum(load) if sum(load) > 0 else 0.0
    evn_total = sum(load) * tou_avg
    savings = evn_total - total

    return {
        "matched_kwh": matched,
        "shortfall_kwh": shortfall,
        "excess_kwh": excess,
        "market_price_vnd_per_kwh": round(market_price, 6),
        "strike_vnd_per_kwh": round(strike, 6),
        "evn_matched_payment_vnd": round(evn_matched, 2),
        "dppa_charge_vnd": round(dppa_charge, 2),
        "shortfall_payment_vnd": round(shortfall_payment, 2),
        "cfd_payment_vnd": round(cfd, 2),
        "total_buyer_payment_vnd": round(total, 2),
        "blended_cost_vnd_per_kwh": round(blended, 6),
        "buyer_savings_vnd": round(savings, 2),
        "evn_total_cost_vnd": round(evn_total, 2),
        "pv_kw": round(pv_kw, 2),
        "bess_kw": round(bess_kw, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase E: Controller-vs-optimizer dispatch gap"
    )
    parser.add_argument("--reopt", type=Path)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args()

    extracted = _load_json(args.extracted)
    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    load = load_saigon18_load_series(extracted)
    cfmp = load_saigon18_cfmp_series(extracted)
    fmp = load_saigon18_fmp_series(extracted)
    avg_cfmp = sum(cfmp) / len(cfmp) if cfmp else 0.0
    avg_fmp = sum(fmp) / len(fmp) if fmp else 0.0
    market_price = avg_cfmp if avg_cfmp > 0 else avg_fmp
    strike = 1809.613356

    tou = [1811.0] * 8760
    tou_avg = sum(tou) / len(tou)

    controller_results = compute_controller_dispatch(
        load=load,
        pv_kw=BASE_PV_KWP,
        bess_kw=CONTROLLER_BESS_KW,
        bess_kwh=CONTROLLER_BESS_KWH,
    )

    optimizer_results = None
    if args.reopt and args.reopt.exists():
        reopt = _load_json(args.reopt)
        pv_size = reopt.get("PV", {}).get("size_kw", 0.0)
        es_size = reopt.get("ElectricStorage", {}).get("size_kw", 0.0)
        es_kwh = reopt.get("ElectricStorage", {}).get("size_kwh", 0.0)
        pv_gen = reopt.get("PV", {}).get("year_one_energy_produced_kwh", 0.0)
        es_discharged = reopt.get("ElectricStorage", {}).get(
            "year_one_energy_discharged_kwh", 0.0
        )
        annual_load = sum(load)
        optimizer_gen = pv_gen
        optimizer_matched = es_discharged
        optimizer_shortfall = max(0.0, annual_load - optimizer_gen - optimizer_matched)
        optimizer_excess = max(0.0, optimizer_gen - annual_load - optimizer_matched)
        optimizer_results = {
            "pv_size_kw": round(pv_size, 2),
            "bess_kw": round(es_size, 2),
            "bess_kwh": round(es_kwh, 2),
            "pv_gen_kwh": round(pv_gen, 2),
            "bess_discharged_kwh": round(es_discharged, 2),
            "matched_kwh": round(optimizer_matched, 2),
            "shortfall_kwh": round(optimizer_shortfall, 2),
            "excess_kwh": round(optimizer_excess, 2),
        }

    controller_settlement = compute_settlement_from_dispatch(
        controller_results,
        load,
        market_price,
        strike,
        tou_avg,
        CONTROLLER_BESS_KW,
        BASE_PV_KWP,
    )

    optimizer_settlement = None
    if optimizer_results:
        optimizer_settlement = compute_settlement_from_dispatch(
            optimizer_results,
            load,
            market_price,
            strike,
            tou_avg,
            optimizer_results["bess_kw"],
            optimizer_results["pv_size_kw"],
        )

    gap = {}
    if optimizer_settlement and optimizer_results:
        gap = {
            "matched_kwh_delta": round(
                controller_results["matched_kwh"] - optimizer_results["matched_kwh"], 2
            ),
            "shortfall_kwh_delta": round(
                controller_results["shortfall_kwh"]
                - optimizer_results["shortfall_kwh"],
                2,
            ),
            "blended_cost_delta_vnd_per_kwh": round(
                controller_settlement["blended_cost_vnd_per_kwh"]
                - optimizer_settlement["blended_cost_vnd_per_kwh"],
                6,
            ),
            "total_payment_delta_vnd": round(
                controller_settlement["total_buyer_payment_vnd"]
                - optimizer_settlement["total_buyer_payment_vnd"],
                2,
            ),
            "controller_bess_kw": CONTROLLER_BESS_KW,
            "optimizer_bess_kw": optimizer_results["bess_kw"],
            "bess_kw_delta": CONTROLLER_BESS_KW - optimizer_results["bess_kw"],
        }

    controller_gap = {
        "model": "Saigon18 DPPA Case 3 Phase E Controller Gap",
        "status": "computed",
        "dispatch_windows": {
            "charge_hours_utc": CONTROLLER_CHARGE_WINDOW_HOURS,
            "discharge_hours_utc": CONTROLLER_DISCHARGE_WINDOW_HOURS,
            "note": "Simplified controller proxy; real project uses fixed windows from operator schedule",
        },
        "controller": {
            "pv_kw": BASE_PV_KWP,
            "bess_kw": CONTROLLER_BESS_KW,
            "bess_kwh": CONTROLLER_BESS_KWH,
            "dispatch_results": controller_results,
            "settlement": controller_settlement,
        },
        "optimizer": {
            **(
                {"results": optimizer_results, "settlement": optimizer_settlement}
                if optimizer_results
                else {}
            ),
        },
        "gap": gap,
        "interpretation": (
            "Controller dispatch uses fixed 1MW BESS with simple solar-peak charge and evening discharge. "
            "Optimizer (where BESS > 0) can shift dispatch to maximize matched renewable delivery within the same physical bounds. "
            "The gap shows how much value is lost when dispatch is constrained to controller-style windows."
        )
        if optimizer_results
        else (
            "Optimizer results not available (bounded-opt solve timed out). Controller results shown for reference. "
            "The bounded-optimization scenario with mandatory storage floor must be solved to compute the real gap."
        ),
    }

    out_path = (
        args.artifact_dir
        / f"{REPORT_DATE}_saigon18_dppa-case-3_phase-e-controller-gap.json"
    )
    _write_json(out_path, controller_gap)
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
