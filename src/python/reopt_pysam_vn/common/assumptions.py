"""Canonical assumption resolver (S1-S3 of the post-backlog architecture plan).

For any assumption needed by any module, resolve in this exact order and stop
at the first hit:

1. An explicit function argument passed by the caller.
2. A per-deal value in the deal's ``*_extracted_inputs.json``.
3. The regime-resolved data layer (``resolve_vietnam_regime(vn, regime_id)``).
4. The deal-defaults data file (``vn_deal_defaults_2026.json`` -> ``data.*``).

Never a module-level literal. There is no step 5.
"""

from __future__ import annotations

from typing import Any

from reopt_pysam_vn.reopt.preprocess import VNData, resolve_vietnam_regime

DEFAULT_REGIME_ID = "decision_963_2026_current"


def exchange_rate(
    vn: VNData,
    *,
    caller_value: float | None = None,
    extracted: dict[str, Any] | None = None,
) -> float:
    """Resolve VND-per-USD per S2's precedence chain.

    Precedence: ``caller_value`` > ``extracted["benchmark"]["exchange_rate_vnd_per_usd"]``
    > ``vn.deal_defaults["exchange_rate"]["vnd_per_usd"]`` > ``vn.exchange_rate``.
    """
    candidates = [
        caller_value,
        (extracted or {}).get("benchmark", {}).get("exchange_rate_vnd_per_usd"),
        vn.deal_defaults.get("exchange_rate", {}).get("vnd_per_usd"),
        vn.exchange_rate,
    ]
    for candidate in candidates:
        if candidate is not None:
            resolved = float(candidate)
            if resolved <= 0:
                raise ValueError(f"exchange_rate_vnd_per_usd must be positive, got {resolved}")
            return resolved
    raise ValueError("no exchange rate could be resolved")


def export_cap_fraction(vn: VNData, *, regime_id: str = DEFAULT_REGIME_ID) -> float:
    """Return ``max_export_fraction`` (a fraction in ``[0, 1]``) for ``regime_id``."""
    regime = resolve_vietnam_regime(vn, regime_id)
    return float(regime["export_rules"]["rooftop_solar"]["max_export_fraction"])


def surplus_rate_vnd_per_kwh(vn: VNData, *, regime_id: str = DEFAULT_REGIME_ID) -> float:
    """Return the surplus purchase rate in VND per kWh for ``regime_id``."""
    regime = resolve_vietnam_regime(vn, regime_id)
    return float(regime["export_rules"]["rooftop_solar"]["surplus_purchase_rate_vnd_per_kwh"])


def dppa_adder_vnd_per_kwh(vn: VNData) -> float:
    """Return ``data.dppa_settlement.adder_vnd_per_kwh`` from the deal-defaults file."""
    return float(vn.deal_defaults["dppa_settlement"]["adder_vnd_per_kwh"])


def kpp_loss_pct(vn: VNData) -> float:
    """Return ``data.dppa_settlement.kpp_loss_pct`` as a percentage (e.g. ``2.7263``)."""
    return float(vn.deal_defaults["dppa_settlement"]["kpp_loss_pct"])
