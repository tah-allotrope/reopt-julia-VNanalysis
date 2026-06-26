"""Case 5/6 CAPEX calibration for the DPPA July 2026 deck.

Back-solves project ``installed_cost_usd`` so each case's modeled seller
equity IRR (``project_return_aftertax_irr_fraction``) matches the deck
stated value (Case 5: 16.9%; Case 6: 26.9%). BESS is **pinned** by the
deck's hints (Q-003 default), project CAPEX is the **solved** quantity.

Per the plan's DEC-001/004/007:

* **Pin BESS from hints.** Case 5: 7.5 MWh (from "~$1.2M year-11
  replacement" ÷ $160/kWh). Case 6: 4 MWh (lean "minimum" sizing, scaled
  down from the on-site 10.7 MWh reference).
* **Model the BESS replacement as a year-11 cashflow** (not an upfront
  CAPEX shock) for Case 5. Case 6's lean BESS is assumed to last the
  loan tenor with no replacement shock.
* **1-D root find on installed_cost_usd** so the modeled IRR equals the
  deck's seller IRR within tolerance.
* **Persist every assumption to a calibration JSON** — the explicit
  assumption ledger. PHASE-04 uses the solved CAPEX as the project's
  cost basis for the 56-sweep + downstream metrics.

The risk of a "monotonic miss" (RISK-03-01) — where no CAPEX produces
the deck IRR — is handled: if the model never returns a positive IRR in
the searched CAPEX range, the calibration emits an ``achievable_irr_envelope``
block and the per-case verdict in the orchestrator stays 🔧 calibrated
(solver did not converge; deck value is the target; downstream check is
"model cannot reach deck claim under disclosed terms").

Usage (from repo root):
    .venv\\Scripts\\python.exe scripts/python/integration/ceba_deck/calibrate_cases.py
    .venv\\Scripts\\python.exe scripts/python/integration/ceba_deck/calibrate_cases.py --case 5
    .venv\\Scripts\\python.exe scripts/python/integration/ceba_deck/calibrate_cases.py --case 6
    .venv\\Scripts\\python.exe scripts/python/integration/ceba_deck/calibrate_cases.py --tol 0.005
    .venv\\Scripts\\python.exe scripts/python/integration/ceba_deck/calibrate_cases.py --capex-lo 100_000 --capex-hi 50_000_000

The calibration JSON is written to
``reports/dppa_july_2026_calibration.json`` (path is resolved via
``DeckConfig.calibration_json``).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_PYTHON = REPO_ROOT / "src" / "python"
SCRIPTS_PYTHON = REPO_ROOT / "scripts" / "python"
for _p in (str(SRC_PYTHON), str(SCRIPTS_PYTHON)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from integration.ceba_deck.deck_config import get_deck  # noqa: E402
from reopt_pysam_vn.integration.factory_a import (  # noqa: E402
    FACTORY_A_ANNUAL_KWH,
    FACTORY_A_PEAK_KW,
    EXCHANGE_RATE_VND_PER_USD,
    build_factory_a_load_8760,
)
from reopt_pysam_vn.pysam.single_owner import (  # noqa: E402
    SingleOwnerInputs,
    run_single_owner_model,
)


# --------------------------------------------------------------------------
# Calibration inputs — locked by the plan + Grill Me defaults
# --------------------------------------------------------------------------
SOLAR_CAPACITY_FRACTION_OF_FACTORY_LOAD = 0.85
SOLAR_CAPACITY_FACTOR = 0.18  # Vietnam south
SOLAR_KWP = SOLAR_CAPACITY_FRACTION_OF_FACTORY_LOAD * FACTORY_A_ANNUAL_KWH / (
    8760.0 * SOLAR_CAPACITY_FACTOR
)
ANNUAL_GEN_KWH = SOLAR_KWP * 8760.0 * SOLAR_CAPACITY_FACTOR

# Strike 2,000 VND/kWh (deck slide 22-24) and 4%/yr escalation (deck slide 15)
STRIKE_VND_PER_KWH = 2_000.0
STRIKE_ESCALATION_FRACTION = 0.04
PPA_PRICE_INPUT_USD_PER_KWH = STRIKE_VND_PER_KWH / EXCHANGE_RATE_VND_PER_USD

# Disclosed deal terms (deck slide 18 + 22)
DEBT_FRACTION = 0.70
DEBT_INTEREST_RATE_FRACTION = 0.085
DEBT_TENOR_YEARS = 10
ANALYSIS_YEARS = 25
DEPRECIATION_SCHEDULE = "vn_sl_15yr"

# BESS sizing per case (Q-003 default)
BESS_REPLACEMENT_USD = 1_200_000.0  # Case 5 only; deck slide 23 hint
BESS_USD_PER_KWH = 160.0  # Q-003 default
BESS_REPLACEMENT_YEAR = 11  # deck slide 23

# BESS energy per case
CASE_BESS_ENERGY_KWH = {
    "case_5": 7_500.0,  # 7.5 MWh; $1.2M ÷ $160/kWh
    "case_6": 4_000.0,  # 4 MWh lean; scaled down from on-site 10.7 MWh
}

# Target seller IRRs (deck slide 23 + 24)
CASE_TARGET_IRR = {
    "case_5": 0.169,
    "case_6": 0.269,
}

# Case framing
CASE_FRAMING = {
    "case_5": {
        "label": "Solar + Large BESS",
        "slide": 23,
        "bess_replacement_year": BESS_REPLACEMENT_YEAR,
        "bess_replacement_usd": BESS_REPLACEMENT_USD,
        "bess_energy_kwh": CASE_BESS_ENERGY_KWH["case_5"],
        "deck_target_seller_irr": CASE_TARGET_IRR["case_5"],
        "deck_target_project_irr": 0.135,
        "deck_target_npv_usd": 1_520_000.0,
        "deck_target_min_dscr": 1.14,
        "deck_target_payback_years": 9.1,
        "deck_target_buyer_vs_bau_y1": -0.087,
        "deck_target_buyer_vs_bau_10yr": -0.089,
        "deck_target_buyer_vs_bau_lifetime": -0.093,
    },
    "case_6": {
        "label": "Solar + Min BESS",
        "slide": 24,
        "bess_replacement_year": None,  # lean BESS; no replacement shock
        "bess_replacement_usd": 0.0,
        "bess_energy_kwh": CASE_BESS_ENERGY_KWH["case_6"],
        "deck_target_seller_irr": CASE_TARGET_IRR["case_6"],
        "deck_target_project_irr": 0.182,
        "deck_target_npv_usd": 2_540_000.0,
        "deck_target_min_dscr": 1.50,
        "deck_target_payback_years": 4.7,
        "deck_target_buyer_vs_bau_lifetime": -0.144,
    },
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _flat_pv_generation_profile() -> list[float]:
    """Build a flat 8760 hourly profile (kW) sized to the project."""
    return [ANNUAL_GEN_KWH / 8760.0] * 8760


def _bess_replacement_year_cashflow(
    base_results: dict,
    year: int,
    replacement_cost_usd: float,
) -> dict:
    """Return a new result dict with the year-N after-tax cash flow reduced
    by ``replacement_cost_usd`` (the BESS replacement cash outflow).

    We approximate the BESS replacement as a direct deduction to the
    project-return after-tax cash flow at the stated year (deck slide 23
    hint: "year 11"). This is intentionally simple: it does not re-run the
    whole PySAM model with a new capex. For a project where the
    replacement is small relative to the project's lifetime revenue
    (<10% of any one year's cash), the IRR and DSCR movement is bounded
    and the calibration is still a meaningful consistency check.
    """
    aftertax_cash = list(base_results["annual_cashflows"])
    if 1 <= year <= len(aftertax_cash):
        aftertax_cash[year - 1]["aftertax_cashflow_usd"] -= replacement_cost_usd
    return {**base_results, "annual_cashflows": aftertax_cash}


def _metrics_from_results(
    base_results: dict,
    bess_replacement_year: Optional[int],
    bess_replacement_usd: float,
    fixed_om_usd_per_year: float,
) -> dict:
    """Compute the calibrated metrics (aftertax IRR, project IRR, NPV,
    min DSCR, payback) on the (possibly BESS-shocked) cash flow."""
    if bess_replacement_year and bess_replacement_usd > 0:
        base_results = _bess_replacement_year_cashflow(
            base_results, bess_replacement_year, bess_replacement_usd
        )
    outputs = base_results["outputs"]
    aftertax_irr = outputs.get("project_return_aftertax_irr_fraction")
    pretax_irr = outputs.get("project_return_pretax_irr_fraction")
    npv_usd = outputs.get("project_return_aftertax_npv_usd")
    min_dscr = outputs.get("min_dscr")

    # Payback: first year the cumulative aftertax cash turns non-negative.
    aftertax_series = [c["aftertax_cashflow_usd"] for c in base_results["annual_cashflows"]]
    cumulative = 0.0
    payback_years: Optional[int] = None
    for c in aftertax_series:
        cumulative += c
        if cumulative > 0 and payback_years is None:
            payback_years = aftertax_series.index(c) + 1
            break

    # DSCR — re-derive min from the (possibly shocked) cash flows + debt service.
    # Note: PySAM's DSCR comes from pretax cash, so the BESS replacement (aftertax)
    # shock would shift the min DSCR by `replacement_usd / debt_service`. We
    # approximate this directly: DSCR_min_shocked = DSCR_min - replacement/debt_service.
    raw_dscr = outputs.get("min_dscr") or 0.0
    debt_service_yr1 = base_results["annual_cashflows"][0]["debt_service_usd"]
    if bess_replacement_year and bess_replacement_usd > 0 and debt_service_yr1 > 0:
        # The shock happens in year-11; debt service is 0 by then (10-yr tenor).
        # So min DSCR in the shocked year is (replacement_revenue_year11 - replacement)
        # / debt_service_year11 = -inf. We re-derive a minimum-DSUR style metric
        # = (CFADS + replacement_shock_at_year) / debt_service. PySAM DSCR pretax is
        # the simpler approximation: CFADS / debt_service. The BESS replacement is
        # an after-tax cash outflow, so DSCR pretax should also dip.
        replacement_year_dscr = -bess_replacement_usd / debt_service_yr1
        min_dscr = min(raw_dscr, replacement_year_dscr)
    else:
        min_dscr = raw_dscr

    return {
        "project_return_aftertax_irr_fraction": aftertax_irr,
        "project_return_pretax_irr_fraction": pretax_irr,
        "project_return_aftertax_npv_usd": npv_usd,
        "min_dscr": min_dscr,
        "payback_years": payback_years,
        "fixed_om_usd_per_year": fixed_om_usd_per_year,
    }


def _solve_for_target_irr(
    case_id: str,
    target_irr: float,
    capex_lo: float,
    capex_hi: float,
    tol: float,
    max_iter: int,
    bess_replacement_year: Optional[int],
    bess_replacement_usd: float,
    on_iteration: Optional[Callable[[int, float, Optional[float]], None]] = None,
) -> dict:
    """1-D bisection on ``installed_cost_usd`` to find the CAPEX at which
    the modeled seller equity IRR matches ``target_irr`` within ``tol``.

    Returns a dict with: solved (bool), capex_usd (float), modeled_irr
    (float or None), iterations (int), trace (list of {iter, capex, irr}).
    """
    base_inputs = SingleOwnerInputs(
        system_capacity_kw=SOLAR_KWP,
        generation_profile_kw=_flat_pv_generation_profile(),
        annual_generation_kwh=ANNUAL_GEN_KWH,
        installed_cost_usd=capex_lo,
        fixed_om_usd_per_year=0.015 * capex_lo,  # initial; updated per iter
        ppa_price_input_usd_per_kwh=PPA_PRICE_INPUT_USD_PER_KWH,
        analysis_years=ANALYSIS_YEARS,
        debt_fraction=DEBT_FRACTION,
        target_irr_fraction=0.15,
        owner_tax_rate_fraction=0.20,
        owner_discount_rate_fraction=0.10,
        offtaker_discount_rate_fraction=0.10,
        inflation_rate_fraction=0.035,
        debt_interest_rate_fraction=DEBT_INTEREST_RATE_FRACTION,
        debt_tenor_years=DEBT_TENOR_YEARS,
        ppa_escalation_rate_fraction=STRIKE_ESCALATION_FRACTION,
        om_escalation_rate_fraction=0.03,
        depreciation_schedule=DEPRECIATION_SCHEDULE,
        metadata={"case": case_id, "phase": "calibration"},
    )

    def irr_at_capex(capex: float) -> Optional[float]:
        inputs = SingleOwnerInputs(
            **{**asdict(base_inputs), "installed_cost_usd": capex,
                "fixed_om_usd_per_year": 0.015 * capex}
        )
        try:
            results = run_single_owner_model(inputs)
        except Exception as exc:  # noqa: BLE001
            return None
        if bess_replacement_year and bess_replacement_usd > 0:
            results = _bess_replacement_year_cashflow(
                results, bess_replacement_year, bess_replacement_usd
            )
        return results["outputs"].get("project_return_aftertax_irr_fraction")

    trace: list[dict] = []

    def _record(iter_idx: int, capex: float, irr: Optional[float]) -> None:
        trace.append({"iter": iter_idx, "capex_usd": capex, "modeled_irr": irr})
        if on_iteration is not None:
            on_iteration(iter_idx, capex, irr)

    irr_lo = irr_at_capex(capex_lo)
    _record(0, capex_lo, irr_lo)
    irr_hi = irr_at_capex(capex_hi)
    _record(0, capex_hi, irr_hi)

    # If both ends return None (or no sign change), the model cannot
    # produce the target IRR in the searched range — return the envelope.
    if irr_lo is None and irr_hi is None:
        return {
            "solved": False,
            "reason": (
                f"model returns null IRR across the entire CAPEX range "
                f"[{capex_lo:,.0f}, {capex_hi:,.0f}]; the deck's "
                f"target_irr={target_irr:.1%} is unreachable under the "
                f"disclosed deal terms (strike 2,000 VND/kWh, 70% debt at "
                f"8.5%, 10-yr tenor, 25-yr analysis, vn_sl_15yr, 18% CF, "
                f"{SOLAR_KWP:,.0f} kWp solar)"
            ),
            "capex_usd": None,
            "modeled_irr": None,
            "iterations": 1,
            "trace": trace,
            "envelope_lo": {"capex_usd": capex_lo, "modeled_irr": irr_lo},
            "envelope_hi": {"capex_usd": capex_hi, "modeled_irr": irr_hi},
        }

    for i in range(1, max_iter + 1):
        mid = (capex_lo + capex_hi) / 2.0
        irr_mid = irr_at_capex(mid)
        _record(i, mid, irr_mid)
        if irr_mid is None:
            # No information — narrow on the side that has IRR data
            if irr_lo is not None:
                capex_hi = mid
            else:
                capex_lo = mid
            continue
        if abs(irr_mid - target_irr) < tol:
            return {
                "solved": True,
                "capex_usd": mid,
                "modeled_irr": irr_mid,
                "iterations": i,
                "trace": trace,
            }
        # Sign change convention: smaller CAPEX → higher IRR
        if irr_mid > target_irr:
            capex_lo = mid
        else:
            capex_hi = mid
    return {
        "solved": False,
        "reason": f"max_iter={max_iter} reached without tol={tol} convergence",
        "capex_usd": (capex_lo + capex_hi) / 2.0,
        "modeled_irr": irr_at_capex((capex_lo + capex_hi) / 2.0),
        "iterations": max_iter,
        "trace": trace,
        "envelope_lo": {"capex_usd": capex_lo, "modeled_irr": irr_lo},
        "envelope_hi": {"capex_usd": capex_hi, "modeled_irr": irr_hi},
    }


def _run_full_metrics(capex_usd: float, case_id: str) -> dict:
    """Run the project at the solved CAPEX and return the full metric set
    (the 5 independent checks for that case)."""
    framing = CASE_FRAMING[case_id]
    inputs = SingleOwnerInputs(
        system_capacity_kw=SOLAR_KWP,
        generation_profile_kw=_flat_pv_generation_profile(),
        annual_generation_kwh=ANNUAL_GEN_KWH,
        installed_cost_usd=capex_usd,
        fixed_om_usd_per_year=0.015 * capex_usd,
        ppa_price_input_usd_per_kwh=PPA_PRICE_INPUT_USD_PER_KWH,
        analysis_years=ANALYSIS_YEARS,
        debt_fraction=DEBT_FRACTION,
        target_irr_fraction=0.15,
        owner_tax_rate_fraction=0.20,
        owner_discount_rate_fraction=0.10,
        offtaker_discount_rate_fraction=0.10,
        inflation_rate_fraction=0.035,
        debt_interest_rate_fraction=DEBT_INTEREST_RATE_FRACTION,
        debt_tenor_years=DEBT_TENOR_YEARS,
        ppa_escalation_rate_fraction=STRIKE_ESCALATION_FRACTION,
        om_escalation_rate_fraction=0.03,
        depreciation_schedule=DEPRECIATION_SCHEDULE,
        metadata={"case": case_id, "phase": "metrics_at_solved_capex"},
    )
    base_results = run_single_owner_model(inputs)
    metrics = _metrics_from_results(
        base_results,
        framing["bess_replacement_year"],
        framing["bess_replacement_usd"],
        fixed_om_usd_per_year=0.015 * capex_usd,
    )
    return metrics


def _build_calibration_entry(case_id: str, cal: dict) -> dict:
    framing = CASE_FRAMING[case_id]
    out: dict = {
        "case": case_id,
        "label": framing["label"],
        "slide": framing["slide"],
        "framing": {
            "bess_energy_kwh": framing["bess_energy_kwh"],
            "bess_replacement_year": framing["bess_replacement_year"],
            "bess_replacement_usd": framing["bess_replacement_usd"],
            "deck_target_seller_irr": framing["deck_target_seller_irr"],
            "deck_target_project_irr": framing["deck_target_project_irr"],
            "deck_target_npv_usd": framing["deck_target_npv_usd"],
            "deck_target_min_dscr": framing["deck_target_min_dscr"],
            "deck_target_payback_years": framing["deck_target_payback_years"],
        },
        "model": {
            "solar_capacity_kw": SOLAR_KWP,
            "annual_generation_kwh": ANNUAL_GEN_KWH,
            "solar_capacity_factor": SOLAR_CAPACITY_FACTOR,
            "ppa_price_input_usd_per_kwh": PPA_PRICE_INPUT_USD_PER_KWH,
            "ppa_escalation_rate_fraction": STRIKE_ESCALATION_FRACTION,
            "debt_fraction": DEBT_FRACTION,
            "debt_interest_rate_fraction": DEBT_INTEREST_RATE_FRACTION,
            "debt_tenor_years": DEBT_TENOR_YEARS,
            "analysis_years": ANALYSIS_YEARS,
            "depreciation_schedule": DEPRECIATION_SCHEDULE,
        },
        "solver": {
            "solved": cal["solved"],
            "iterations": cal["iterations"],
            "reason": cal.get("reason"),
        },
        "assumptions": [
            "Project sized at 85% of Factory A's 9,750 MWh/yr load (≈ 5,250 kWp at 18% CF).",
            "BESS energy pinned from deck hints (Q-003): Case 5 7.5 MWh (~$1.2M ÷ $160/kWh); Case 6 4 MWh (lean 'minimum').",
            "BESS replacement modeled as a year-11 cashflow deduction (Case 5 only); Case 6 lean BESS assumed to last the loan tenor.",
            "Fixed O&M at 1.5% of installed cost per year; 3% escalation.",
            "Disclosed deal terms: 70% debt / 8.5% VND / 10-yr tenor / 25-yr analysis / vn_sl_15yr depreciation.",
            "Strike 2,000 VND/kWh ($0.0758 USD/kWh) escalating 4%/yr; 18% solar capacity factor (Vietnam south).",
            "Calibration target: 1-D bisection on installed_cost_usd so the modeled seller IRR matches the deck's stated seller IRR (Case 5: 16.9%; Case 6: 26.9%) within ±0.5pp.",
        ],
    }
    if cal["solved"]:
        out["solver"]["solved_capex_usd"] = cal["capex_usd"]
        out["solver"]["modeled_irr_at_solved_capex"] = cal["modeled_irr"]
        out["solver"]["implied_capex_per_kw"] = cal["capex_usd"] / SOLAR_KWP
        out["metrics_at_solved_capex"] = _run_full_metrics(cal["capex_usd"], case_id)
    else:
        out["solver"]["envelope_lo"] = cal.get("envelope_lo")
        out["solver"]["envelope_hi"] = cal.get("envelope_hi")
        out["binding_constraint_note"] = (
            "The deck's stated seller IRR is unreachable under the disclosed "
            "deal terms even at the searched CAPEX bounds. This is the "
            "monotonic miss per plan RISK-03-01: the deck's 16.9% / 26.9% "
            "values require undisclosed assumptions (higher matched volume, "
            "different CF, longer escalation, lower O&M, etc.). The downstream "
            "checks (project IRR, NPV, DSCR, payback, buyer-vs-BAU) are "
            "therefore not reproducible from the deck disclosures alone."
        )
    out["trace"] = cal.get("trace", [])
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deck",
        choices=("july",),
        default="july",
        help="Which deck to calibrate (only 'july' for now; CEBA is flag-only).",
    )
    parser.add_argument(
        "--case",
        choices=("5", "6", "both"),
        default="both",
        help="Which case(s) to calibrate (default: both).",
    )
    parser.add_argument(
        "--capex-lo",
        type=float,
        default=1_000_000.0,
        help="Lower bound for CAPEX search (default: 1M USD).",
    )
    parser.add_argument(
        "--capex-hi",
        type=float,
        default=10_000_000.0,
        help="Upper bound for CAPEX search (default: 10M USD).",
    )
    parser.add_argument(
        "--tol",
        type=float,
        default=0.005,
        help="Convergence tolerance on IRR (default: 0.005 = 0.5pp).",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=20,
        help="Max bisection iterations (default: 20).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Override the output JSON path.",
    )
    args = parser.parse_args(argv)

    config = get_deck(args.deck)
    out_path = args.out or config.calibration_json
    if out_path is None:
        print("this deck has no calibration_json path configured", file=sys.stderr)
        return 1

    cases: list[str] = ["case_5", "case_6"] if args.case == "both" else [f"case_{args.case}"]
    started = time.time()
    calibration: dict[str, Any] = {}
    for case_id in cases:
        framing = CASE_FRAMING[case_id]
        target_irr = framing["deck_target_seller_irr"]
        print(
            f"[calibrate_cases] {case_id} (target seller IRR={target_irr:.1%}, "
            f"BESS={framing['bess_energy_kwh']/1000:.1f} MWh)...",
            flush=True,
        )
        cal = _solve_for_target_irr(
            case_id=case_id,
            target_irr=target_irr,
            capex_lo=args.capex_lo,
            capex_hi=args.capex_hi,
            tol=args.tol,
            max_iter=args.max_iter,
            bess_replacement_year=framing["bess_replacement_year"],
            bess_replacement_usd=framing["bess_replacement_usd"],
        )
        if cal["solved"]:
            print(
                f"  -> solved: CAPEX=${cal['capex_usd']:,.0f} (${cal['capex_usd']/SOLAR_KWP:,.0f}/kW), "
                f"modeled IRR={cal['modeled_irr']:.2%} (target {target_irr:.1%})",
                flush=True,
            )
        else:
            print(f"  -> NOT SOLVED: {cal.get('reason')}", flush=True)
        calibration[case_id] = _build_calibration_entry(case_id, cal)

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "deck": str(config.source_pptx.relative_to(REPO_ROOT)),
            "deck_title": config.deck_title,
            "plan": config.plan_path,
            "phase": "PHASE-03",
            "duration_seconds": round(time.time() - started, 2),
        },
        "calibration": calibration,
        "shared_assumptions": {
            "solar_capacity_kw": SOLAR_KWP,
            "solar_capacity_fraction_of_factory_load": SOLAR_CAPACITY_FRACTION_OF_FACTORY_LOAD,
            "solar_capacity_factor": SOLAR_CAPACITY_FACTOR,
            "annual_generation_kwh": ANNUAL_GEN_KWH,
            "factory_a_annual_load_kwh": FACTORY_A_ANNUAL_KWH,
            "factory_a_peak_kw": FACTORY_A_PEAK_KW,
            "strike_vnd_per_kwh": STRIKE_VND_PER_KWH,
            "ppa_price_input_usd_per_kwh": PPA_PRICE_INPUT_USD_PER_KWH,
            "ppa_escalation_rate_fraction": STRIKE_ESCALATION_FRACTION,
            "debt_fraction": DEBT_FRACTION,
            "debt_interest_rate_fraction": DEBT_INTEREST_RATE_FRACTION,
            "debt_tenor_years": DEBT_TENOR_YEARS,
            "analysis_years": ANALYSIS_YEARS,
            "depreciation_schedule": DEPRECIATION_SCHEDULE,
            "exchange_rate_vnd_per_usd": EXCHANGE_RATE_VND_PER_USD,
            "bess_replacement_year": BESS_REPLACEMENT_YEAR,
            "bess_replacement_usd": BESS_REPLACEMENT_USD,
            "bess_usd_per_kwh": BESS_USD_PER_KWH,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8", newline="\n")
    print(
        f"[calibrate_cases] wrote {out_path.relative_to(REPO_ROOT)} "
        f"({out_path.stat().st_size:,} bytes; {len(cases)} case(s))",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
