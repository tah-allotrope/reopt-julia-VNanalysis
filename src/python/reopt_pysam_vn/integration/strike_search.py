"""Strike-price sweep helpers for REopt plus PySAM workflows."""

from __future__ import annotations

from dataclasses import replace

from reopt_pysam_vn.pysam.single_owner import SingleOwnerInputs, run_single_owner_model


def bounded_midpoint(lower: float, upper: float) -> float:
    return (float(lower) + float(upper)) / 2.0


def _candidate_strikes(
    min_strike_cents_per_kwh: float,
    max_strike_cents_per_kwh: float,
    step_cents_per_kwh: float,
) -> list[float]:
    minimum = float(min_strike_cents_per_kwh)
    maximum = float(max_strike_cents_per_kwh)
    step = float(step_cents_per_kwh)
    if step <= 0.0:
        raise ValueError("step_cents_per_kwh must be positive")
    if maximum < minimum:
        raise ValueError("max_strike_cents_per_kwh must be >= min_strike_cents_per_kwh")

    count = round((maximum - minimum) / step)
    values = [round(minimum + step * idx, 10) for idx in range(count + 1)]
    if abs(values[-1] - maximum) > 1e-9:
        raise ValueError("strike sweep bounds must align with the requested step size")
    return values


def _is_viable(irr_fraction: float | None, target_irr_fraction: float) -> bool:
    return irr_fraction is not None and float(irr_fraction) >= float(
        target_irr_fraction
    )


def _phase4_baseline_strike_cents(phase4_results: dict) -> float:
    return float(phase4_results["inputs"]["ppa_price_input_usd_per_kwh"]) * 100.0


def sweep_strike_prices(
    phase4_results: dict,
    base_inputs: SingleOwnerInputs,
    target_irr_fraction: float,
    min_strike_cents_per_kwh: float,
    max_strike_cents_per_kwh: float,
    step_cents_per_kwh: float,
    runner=run_single_owner_model,
) -> dict:
    """Evaluate a fixed strike sweep on top of the Phase 4 input bundle."""

    target = float(target_irr_fraction)
    candidate_strikes = _candidate_strikes(
        min_strike_cents_per_kwh=min_strike_cents_per_kwh,
        max_strike_cents_per_kwh=max_strike_cents_per_kwh,
        step_cents_per_kwh=step_cents_per_kwh,
    )

    sweep_results = []
    first_viable = None
    for idx, strike_cents in enumerate(candidate_strikes):
        strike_usd_per_kwh = float(strike_cents) / 100.0
        candidate_inputs = replace(
            base_inputs,
            ppa_price_input_usd_per_kwh=strike_usd_per_kwh,
            target_irr_fraction=target,
            metadata={
                **dict(base_inputs.metadata),
                "strike_price_us_cents_per_kwh": float(strike_cents),
                "strike_price_usd_per_kwh": strike_usd_per_kwh,
            },
        )
        result = runner(candidate_inputs)
        irr_fraction = result["outputs"].get("project_return_aftertax_irr_fraction")
        is_viable = _is_viable(irr_fraction, target)
        sweep_entry = {
            "index": idx,
            "strike_price_us_cents_per_kwh": float(strike_cents),
            "strike_price_usd_per_kwh": strike_usd_per_kwh,
            "is_viable": is_viable,
            "inputs": result.get("inputs", {}),
            "outputs": result.get("outputs", {}),
            "case": result.get("case", {}),
        }
        sweep_results.append(sweep_entry)
        if is_viable and first_viable is None:
            first_viable = sweep_entry

    viability = {
        "target_irr_fraction": target,
        "phase4_baseline_strike_us_cents_per_kwh": _phase4_baseline_strike_cents(
            phase4_results
        ),
        "phase4_baseline_irr_fraction": phase4_results["outputs"].get(
            "project_return_aftertax_irr_fraction"
        ),
        "minimum_viable_found": first_viable is not None,
        "minimum_viable_index": (
            first_viable["index"] if first_viable is not None else None
        ),
        "minimum_viable_strike_us_cents_per_kwh": (
            first_viable["strike_price_us_cents_per_kwh"]
            if first_viable is not None
            else None
        ),
        "minimum_viable_strike_usd_per_kwh": (
            first_viable["strike_price_usd_per_kwh"]
            if first_viable is not None
            else None
        ),
        "minimum_viable_irr_fraction": (
            first_viable["outputs"].get("project_return_aftertax_irr_fraction")
            if first_viable is not None
            else None
        ),
        "minimum_viable_npv_usd": (
            first_viable["outputs"].get("project_return_aftertax_npv_usd")
            if first_viable is not None
            else None
        ),
        "minimum_viable_min_dscr": (
            first_viable["outputs"].get("min_dscr")
            if first_viable is not None
            else None
        ),
    }

    return {
        "sweep_settings": {
            "target_irr_fraction": target,
            "min_strike_us_cents_per_kwh": float(min_strike_cents_per_kwh),
            "max_strike_us_cents_per_kwh": float(max_strike_cents_per_kwh),
            "step_us_cents_per_kwh": float(step_cents_per_kwh),
            "candidate_count": len(candidate_strikes),
        },
        "sweep_results": sweep_results,
        "viability": viability,
    }


def build_strike_price_summary(
    phase4_results: dict,
    base_inputs: SingleOwnerInputs,
    target_irr_fraction: float,
    min_strike_cents_per_kwh: float,
    max_strike_cents_per_kwh: float,
    step_cents_per_kwh: float,
    phase4_artifact_path: str = "artifacts/reports/ninhsim/2026-04-04_ninhsim-single-owner-finance.json",
    runner=run_single_owner_model,
) -> dict:
    """Build the normalized Phase 5 strike-price summary."""

    sweep = sweep_strike_prices(
        phase4_results=phase4_results,
        base_inputs=base_inputs,
        target_irr_fraction=target_irr_fraction,
        min_strike_cents_per_kwh=min_strike_cents_per_kwh,
        max_strike_cents_per_kwh=max_strike_cents_per_kwh,
        step_cents_per_kwh=step_cents_per_kwh,
        runner=runner,
    )
    return {
        "model": "PySAM Strike Price Discovery",
        "status": "ok",
        "phase4_reference": {
            "artifact_path": phase4_artifact_path,
            "baseline_outputs": phase4_results.get("outputs", {}),
        },
        "runtime": phase4_results.get("runtime", {}),
        "inputs": {
            **phase4_results.get("inputs", {}),
            "target_irr_fraction": float(target_irr_fraction),
        },
        "case": dict(base_inputs.metadata),
        "sweep_settings": sweep["sweep_settings"],
        "sweep_results": sweep["sweep_results"],
        "viability": sweep["viability"],
        "notes": {
            "phase_scope": "Phase 5 sweeps year-one PPA strike prices on top of the Phase 4 Ninhsim Single Owner artifact and returns the minimum strike that clears the target developer IRR.",
            "range_units": "All strike sweep inputs are expressed in US cents per kWh for the decision screen, with USD per kWh retained for PySAM execution.",
        },
    }
