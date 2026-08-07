"""Analyze Saigon18 DPPA Case 3 Phase C/D results."""

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
    DEFAULT_STRIKE_DISCOUNT_FRACTION,
    load_saigon18_cfmp_series,
    load_saigon18_fmp_series,
    load_saigon18_load_series,
    load_saigon18_tou_series,
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


def compute_storage_metrics(reopt: dict, tariff_branch: str) -> dict:
    es = reopt.get("ElectricStorage", {})
    pv = reopt.get("PV", {})
    fin = reopt.get("Financial", {})

    pv_kw = pv.get("size_kw", 0.0)
    bess_kw = es.get("size_kw", 0.0)
    bess_kwh = es.get("size_kwh", 0.0)
    pv_energy = pv.get("year_one_energy_produced_kwh", 0.0)
    bess_energy = es.get("year_one_energy_produced_kwh", 0.0)
    bess_charging = es.get("year_one_energy_charged_kwh", 0.0)
    bess_discharging = es.get("year_one_energy_discharged_kwh", 0.0)

    lcc = fin.get("lcc", 0.0)
    npv = fin.get("npv", 0.0)
    capital = fin.get("initial_capital_costs", 0.0)

    storage_floor_met = (
        bess_kw >= BASE_BESS_KW * 0.75 and bess_kwh >= BASE_BESS_KWH * 0.75
    )

    return {
        "tariff_branch": tariff_branch,
        "pv_size_kw": round(pv_kw, 2),
        "bess_power_kw": round(bess_kw, 2),
        "bess_energy_kwh": round(bess_kwh, 2),
        "pv_year_one_energy_kwh": round(pv_energy, 2),
        "bess_year_one_energy_produced_kwh": round(bess_energy, 2),
        "bess_year_one_energy_charged_kwh": round(bess_charging, 2),
        "bess_year_one_energy_discharged_kwh": round(bess_discharging, 2),
        "lcc_usd": round(lcc, 2),
        "npv_usd": round(npv, 2),
        "capital_usd": round(capital, 2),
        "storage_floor_respected": storage_floor_met,
        "pv_within_bounds": BASE_PV_KWP * 0.75 <= pv_kw <= BASE_PV_KWP * 1.50,
        "bess_within_bounds": BASE_BESS_KW * 0.75 <= bess_kw <= BASE_BESS_KW * 1.50,
    }


def compute_buyer_settlement(
    reopt: dict,
    extracted: dict,
    tariff_branch: str,
    strike_vnd_per_kwh: float,
) -> dict:
    load = load_saigon18_load_series(extracted)
    cfmp = load_saigon18_cfmp_series(extracted)
    fmp = load_saigon18_fmp_series(extracted)
    tou = load_saigon18_tou_series(extracted)

    gen = reopt.get("PV", {}).get("year_one_energy_produced_kwh", 0.0)
    pv_kw = reopt.get("PV", {}).get("size_kw", 0.0)
    bess_kw = reopt.get("ElectricStorage", {}).get("size_kw", 0.0)

    annual_load_kwh = sum(load)
    annual_gen_kwh = gen

    matched_kwh = min(annual_load_kwh, annual_gen_kwh)
    shortfall_kwh = max(0.0, annual_load_kwh - annual_gen_kwh)
    excess_kwh = max(0.0, annual_gen_kwh - annual_load_kwh)

    avg_cfmp = sum(cfmp) / len(cfmp) if cfmp else 0.0
    avg_fmp = sum(fmp) / len(fmp) if fmp else 0.0
    market_price = avg_cfmp if avg_cfmp > 0 else avg_fmp

    kpp = DEFAULT_KPP_FACTOR
    adder = DEFAULT_DPPA_ADDER_VND_PER_KWH
    strike = strike_vnd_per_kwh

    evn_matched_payment = matched_kwh * market_price * kpp
    dppa_charge = matched_kwh * adder
    shortfall_payment = shortfall_kwh * (sum(tou) / len(tou))
    cfd = matched_kwh * (strike - market_price)

    total_buyer_payment = evn_matched_payment + dppa_charge + shortfall_payment + cfd
    blended_cost = total_buyer_payment / annual_load_kwh if annual_load_kwh > 0 else 0.0

    evn_total = annual_load_kwh * (sum(tou) / len(tou))
    buyer_savings = evn_total - total_buyer_payment

    return {
        "tariff_branch": tariff_branch,
        "annual_load_kwh": round(annual_load_kwh, 2),
        "annual_generation_kwh": round(annual_gen_kwh, 2),
        "matched_quantity_kwh": round(matched_kwh, 2),
        "shortfall_quantity_kwh": round(shortfall_kwh, 2),
        "excess_quantity_kwh": round(excess_kwh, 2),
        "market_reference_price_vnd_per_kwh": round(market_price, 6),
        "strike_price_vnd_per_kwh": round(strike, 6),
        "dppa_adder_vnd_per_kwh": adder,
        "kpp_factor": kpp,
        "evn_matched_payment_vnd": round(evn_matched_payment, 2),
        "dppa_charge_vnd": round(dppa_charge, 2),
        "shortfall_payment_vnd": round(shortfall_payment, 2),
        "cfd_payment_vnd": round(cfd, 2),
        "total_buyer_payment_vnd": round(total_buyer_payment, 2),
        "blended_cost_vnd_per_kwh": round(blended_cost, 6),
        "buyer_savings_vs_evn_vnd": round(buyer_savings, 2),
        "evn_total_cost_vnd": round(evn_total, 2),
        "pv_size_kw": round(pv_kw, 2),
        "bess_power_kw": round(bess_kw, 2),
    }


def compute_evn_benchmark(extracted: dict, tariff_branch: str) -> dict:
    load = load_saigon18_load_series(extracted)
    tou = load_saigon18_tou_series(extracted)
    annual_load_kwh = sum(load)
    weighted_evn = sum(tou) / len(tou) if tou else 0.0
    evn_total = annual_load_kwh * weighted_evn
    return {
        "tariff_branch": tariff_branch,
        "annual_load_kwh": round(annual_load_kwh, 2),
        "weighted_evn_vnd_per_kwh": round(weighted_evn, 6),
        "evn_total_cost_vnd": round(evn_total, 2),
        "evn_blended_cost_vnd_per_kwh": round(weighted_evn, 6),
    }


def compute_contract_risk(
    reopt: dict,
    extracted: dict,
    tariff_branch: str,
    strike_vnd_per_kwh: float,
) -> dict:
    load = load_saigon18_load_series(extracted)
    cfmp = load_saigon18_cfmp_series(extracted)

    gen = reopt.get("PV", {}).get("year_one_energy_produced_kwh", 0.0)
    annual_load_kwh = sum(load)
    matched_kwh = min(annual_load_kwh, gen)
    excess_kwh = max(0.0, gen - annual_load_kwh)
    shortfall_kwh = max(0.0, annual_load_kwh - gen)

    avg_cfmp = sum(cfmp) / len(cfmp) if cfmp else 0.0
    strike = strike_vnd_per_kwh
    cfd_per_kwh = strike - avg_cfmp

    return {
        "tariff_branch": tariff_branch,
        "matched_quantity_kwh": round(matched_kwh, 2),
        "shortfall_quantity_kwh": round(shortfall_kwh, 2),
        "excess_quantity_kwh": round(excess_kwh, 2),
        "cfd_per_kwh_vnd": round(cfd_per_kwh, 6),
        "strike_above_market": cfd_per_kwh > 0,
        "hours_with_negative_cfd_credit": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Saigon18 DPPA Case 3 Phase C/D results"
    )
    parser.add_argument("--reopt-tou", type=Path)
    parser.add_argument("--reopt-22kv", type=Path)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args()

    extracted = _load_json(args.extracted)
    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    _load = load_saigon18_load_series(extracted)
    tou = load_saigon18_tou_series(extracted)
    weighted_evn = sum(tou) / len(tou)
    strike_vnd = weighted_evn * (1.0 - DEFAULT_STRIKE_DISCOUNT_FRACTION)

    artifacts = {}

    if args.reopt_tou and args.reopt_tou.exists():
        reopt_tou = _load_json(args.reopt_tou)
        artifacts["tou"] = {
            "physical": compute_storage_metrics(reopt_tou, "legacy_tou_one_component"),
            "settlement": compute_buyer_settlement(
                reopt_tou, extracted, "legacy_tou_one_component", strike_vnd
            ),
            "benchmark": compute_evn_benchmark(extracted, "legacy_tou_one_component"),
            "risk": compute_contract_risk(
                reopt_tou, extracted, "legacy_tou_one_component", strike_vnd
            ),
        }

    if args.reopt_22kv and args.reopt_22kv.exists():
        reopt_22kv = _load_json(args.reopt_22kv)
        artifacts["22kv"] = {
            "physical": compute_storage_metrics(reopt_22kv, "22kv_two_part_evn"),
            "settlement": compute_buyer_settlement(
                reopt_22kv, extracted, "22kv_two_part_evn", strike_vnd
            ),
            "benchmark": compute_evn_benchmark(extracted, "22kv_two_part_evn"),
            "risk": compute_contract_risk(
                reopt_22kv, extracted, "22kv_two_part_evn", strike_vnd
            ),
        }

    if "tou" in artifacts and "22kv" in artifacts:
        delta_settlement = {
            k: round(
                artifacts["tou"]["settlement"][k] - artifacts["22kv"]["settlement"][k],
                2,
            )
            for k in artifacts["tou"]["settlement"]
            if isinstance(artifacts["tou"]["settlement"][k], (int, float))
        }
        artifacts["delta"] = {"settlement": delta_settlement}

    for key, sub in artifacts.items():
        for subkey, data in sub.items():
            slug = f"{REPORT_DATE}_saigon18_dppa-case-3_{key}_{subkey}.json"
            path = args.artifact_dir / slug
            _write_json(path, data)
            print(f"Written: {path}")

    combined = {
        "model": "Saigon18 DPPA Case 3 Phase CD Combined",
        "status": "analyzed",
        "strike_vnd_per_kwh": round(strike_vnd, 6),
        "weighted_evn_vnd_per_kwh": round(weighted_evn, 6),
        "artifacts": artifacts,
    }
    combined_path = (
        args.artifact_dir / f"{REPORT_DATE}_saigon18_dppa-case-3_phase-cd-combined.json"
    )
    _write_json(combined_path, combined)
    print(f"Written: {combined_path}")


if __name__ == "__main__":
    main()
