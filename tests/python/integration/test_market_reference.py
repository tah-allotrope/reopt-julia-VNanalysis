"""PHASE-04: shared market-reference (FMP/CFMP) resolution and its data layer.

``integration/market_reference.py`` lifts the market-proxy method out of
``dppa_case_2`` into a shared, deal-agnostic function, and adds a versioned
``market_prices`` data file behind ``manifest.json``. The value-preservation gate
below recomputes the Case-2 proxy inline rather than storing a new golden.
"""

from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))


def _load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load module spec for {relative_path}")
    spec_checked: ModuleSpec = spec
    module = importlib.util.module_from_spec(spec_checked)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_BUILD_EXTRACTED = _load_module(
    "build_ninhsim_extracted_inputs_market_ref_module",
    "scripts/python/integration/build_ninhsim_extracted_inputs.py",
)

from reopt_pysam_vn.common.assumptions import market_wholesale_reference_vnd_per_kwh
from reopt_pysam_vn.integration.dppa_case_2 import build_dppa_case_2_market_proxy
from reopt_pysam_vn.integration.market_reference import (
    market_proxy_fraction,
    resolve_market_reference_series,
)
from reopt_pysam_vn.reopt.preprocess import load_vietnam_data

build_extracted_inputs = _BUILD_EXTRACTED.build_extracted_inputs

_HOURS = 8760


def test_market_proxy_fraction_explicit_wholesale_and_weighted():
    assert market_proxy_fraction(
        {
            "benchmark": {
                "weighted_evn_price_vnd_per_kwh": 2000.0,
                "wholesale_rate_vnd_per_kwh": 671.0,
            }
        }
    ) == 0.3355


def test_market_proxy_fraction_zero_denominator_is_zero_not_error():
    assert market_proxy_fraction(
        {
            "benchmark": {
                "weighted_evn_price_vnd_per_kwh": 0.0,
                "wholesale_rate_vnd_per_kwh": 671.0,
            }
        }
    ) == 0.0


def test_market_proxy_fraction_falls_back_to_data_layer_when_wholesale_absent():
    vn = load_vietnam_data()
    assert market_proxy_fraction(
        {"benchmark": {"weighted_evn_price_vnd_per_kwh": 2000.0}}, vn=vn
    ) == 671.0 / 2000.0


def test_market_wholesale_reference_resolves_671():
    assert market_wholesale_reference_vnd_per_kwh(load_vietnam_data()) == 671.0


def test_resolve_cfmp_converts_vnd_per_mwh_to_kwh():
    series, market_type, provenance = resolve_market_reference_series(
        {"cfmp_vnd_per_mwh": [1_500_000.0] * _HOURS}
    )
    assert market_type == "cfmp"
    assert series[0] == 1500.0
    assert len(series) == _HOURS
    assert provenance["proxy_fraction_of_evn"] is None


def test_resolve_cfmp_wins_over_fmp():
    _, market_type, _ = resolve_market_reference_series(
        {
            "cfmp_vnd_per_mwh": [1_500_000.0] * _HOURS,
            "fmp_vnd_per_mwh": [1_200_000.0] * _HOURS,
        }
    )
    assert market_type == "cfmp"


def test_resolve_proxy_when_no_actual_series_present():
    extracted = {
        "evn_tariff": {"tou_energy_rates_vnd_per_kwh": [2000.0] * _HOURS},
        "benchmark": {
            "weighted_evn_price_vnd_per_kwh": 2000.0,
            "wholesale_rate_vnd_per_kwh": 671.0,
        },
    }
    series, market_type, provenance = resolve_market_reference_series(extracted)
    assert market_type == "proxy_cfmp_or_fmp"
    assert len(series) == _HOURS
    assert series[0] == 2000.0 * 0.3355
    assert provenance["proxy_fraction_of_evn"] == 0.3355
    assert provenance["method"] == "hourly_evn_tariff_scaled_by_wholesale_ratio"


def test_case_2_market_proxy_is_value_preserved_after_refactor():
    extracted = build_extracted_inputs()
    proxy = build_dppa_case_2_market_proxy(extracted)
    assert proxy["model"] == "Ninhsim DPPA Case 2 Market Proxy"
    assert proxy["status"] == "proxy"
    assert proxy["market_reference_price_type"] == "proxy_cfmp_or_fmp"
    assert proxy["proxy_method"] == "hourly_evn_tariff_scaled_by_weighted_wholesale_ratio"
    # Recomputed inline from the raw inputs (no stored golden): the shared
    # fraction must equal the per-deal division exactly.
    weighted = float(extracted["benchmark"]["weighted_evn_price_vnd_per_kwh"])
    wholesale = float(extracted["benchmark"]["wholesale_rate_vnd_per_kwh"])
    expected_fraction = wholesale / weighted
    assert proxy["proxy_fraction_of_evn"] == expected_fraction
    expected_series = [
        rate * expected_fraction
        for rate in extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]
    ]
    assert proxy["hourly_series_vnd_per_kwh"] == expected_series
    assert len(proxy["hourly_series_vnd_per_kwh"]) == len(
        extracted["evn_tariff"]["tou_energy_rates_vnd_per_kwh"]
    )


def test_load_vietnam_data_without_market_prices_key_still_loads(tmp_path):
    import json
    import shutil

    from reopt_pysam_vn.reopt.preprocess import load_vietnam_data as load

    data_dir = REPO_ROOT / "data" / "vietnam"
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("market_prices")
    for key, filename in manifest.items():
        if key == "_meta":
            continue
        shutil.copy(data_dir / filename, tmp_path / filename)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    vn = load(tmp_path / "manifest.json")
    assert vn.market_prices == {}
