"""PHASE-03 tests: strike sweep (buyer-premium surface), developer screen, adder lever.

The buyer side is pure Python (no PySAM). The developer screen is exercised with
an injected deterministic fake runner so these tests pass with or without PySAM;
the real PySAM Single Owner run happens in the analyze script under .venv.
"""

from __future__ import annotations

import pytest

from reopt_pysam_vn.integration.dppa_samsung_ttc import (
    build_samsung_ttc_adder_sensitivity,
    build_samsung_ttc_extracted_inputs,
    build_samsung_ttc_strike_sweep,
)


def _fake_developer_runner(inputs):
    """Deterministic stand-in for run_single_owner_model: IRR/NPV rise with PPA price."""
    ppa = float(inputs.ppa_price_input_usd_per_kwh)
    return {
        "status": "ok",
        "outputs": {
            "project_return_aftertax_irr_fraction": ppa * 3.0,
            "project_return_aftertax_npv_usd": (ppa - 0.045) * 5e8,
        },
    }


def test_strike_sweep_endpoints_anchor_ceiling_and_avoided():
    ex = build_samsung_ttc_extracted_inputs()
    sweep = build_samsung_ttc_strike_sweep(ex, run_developer=False)
    rows = sweep["sweep"]
    assert rows[0]["strike_vnd_per_kwh"] == pytest.approx(1012.0)
    assert rows[-1]["strike_vnd_per_kwh"] == pytest.approx(
        ex["benchmark"]["standard_rate_vnd_per_kwh"]
    )
    assert sweep["strike_band"]["floor_vnd_per_kwh"] == pytest.approx(1012.0)
    assert sweep["strike_band"]["ceiling_vnd_per_kwh"] > 1012.0


def test_buyer_premium_monotonic_in_strike():
    ex = build_samsung_ttc_extracted_inputs()
    sweep = build_samsung_ttc_strike_sweep(ex, run_developer=False)
    deltas = [r["buyer_minus_benchmark_vnd"] for r in sweep["sweep"]]
    # Higher strike => buyer pays more => buyer-minus-benchmark strictly increases.
    assert all(b > a for a, b in zip(deltas, deltas[1:]))
    # At the base strike (Southern ceiling 1,012) the buyer saves vs EVN.
    assert sweep["sweep"][0]["buyer_minus_benchmark_vnd"] < 0
    assert sweep["sweep"][0]["buyer_passes"] is True


def test_developer_screen_with_injected_runner():
    ex = build_samsung_ttc_extracted_inputs()
    sweep = build_samsung_ttc_strike_sweep(ex, developer_runner=_fake_developer_runner)
    irrs = [r["developer_irr_fraction"] for r in sweep["sweep"]]
    assert all(v is not None for v in irrs)
    # Developer IRR rises with the strike (more revenue per kWh).
    assert all(b > a for a, b in zip(irrs, irrs[1:]))
    assert sweep["developer_screen"]["ran"] is True
    assert sweep["developer_screen"]["target_irr_fraction"] == pytest.approx(0.15)
    assert sweep["developer_screen"]["system_capacity_kw"] == pytest.approx(49_000.0)
    assert sweep["developer_screen"]["installed_cost_usd"] == pytest.approx(
        49_000.0 * 750.0
    )
    assert sweep["negotiation_summary"]["recommended_position"] in (
        "buyer_and_developer_overlap",
        "buyer_saves_developer_subeconomic",
        "no_viable_strike_found",
    )


def test_adder_sensitivity_flips_buyer_to_premium():
    ex = build_samsung_ttc_extracted_inputs()
    risk = build_samsung_ttc_adder_sensitivity(ex, adder_multipliers=(0.0, 1.0, 2.0))
    results = risk["adder_sensitivity"]["results"]
    deltas = [r["buyer_minus_benchmark_vnd"] for r in results]
    # Higher DPPA grid-service adder => worse for buyer => delta increasing.
    assert all(b > a for a, b in zip(deltas, deltas[1:]))
    # Zero adder => buyer clearly saves; 2x adder => buyer flips to a premium.
    assert deltas[0] < 0
    assert deltas[-1] > 0
    assert risk["quality"]["basis"] == "directional"


def test_strike_sweep_directional_flags():
    ex = build_samsung_ttc_extracted_inputs()
    sweep = build_samsung_ttc_strike_sweep(ex, run_developer=False)
    assert sweep["quality"]["basis"] == "directional"
    assert sweep["quality"]["market_reference_price_type"] == "proxy_cfmp_or_fmp"
    assert sweep["quality"]["solar_profile_source"].split("_")[0] in (
        "pvwatts",
        "synthetic",
    )
