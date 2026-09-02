"""8760 series operations and REopt result readers — one definition each.

These four helpers were copied into every offsite case module. Three of them
were byte-identical triplicates; ``pad_to_8760`` had already drifted, with
``dppa_case_1`` returning its slice uncoerced while ``dppa_case_2`` and
``dppa_case_3`` coerced to ``float``. Duplication that drifts is the reason this
module exists: one definition, one semantic, one place to fix.

The coercing variant is canonical — it was the majority behaviour, and it makes
a series' element type independent of what the caller happened to hand in.
"""

from __future__ import annotations

from typing import Any

HOURS = 8760


def pad_to_8760(series: list[float]) -> list[float]:
    """Coerce to ``float`` and pad or truncate to exactly 8760 hours."""
    if len(series) >= HOURS:
        return [float(value) for value in series[:HOURS]]
    return [float(value) for value in series] + [0.0] * (HOURS - len(series))


def pad_to_length(series: list[float], length: int) -> list[float]:
    """``pad_to_8760`` for an arbitrary length."""
    if len(series) >= length:
        return [float(value) for value in series[:length]]
    return [float(value) for value in series] + [0.0] * (length - len(series))


def sum_series(*series_list: list[float]) -> list[float]:
    """Element-wise sum of any number of series, each padded to 8760 first."""
    padded = [pad_to_8760(series) for series in series_list]
    return [sum(values) for values in zip(*padded)]


def sum_series_to_length(length: int, *series_list: list[float]) -> list[float]:
    """``sum_series`` for an arbitrary length."""
    padded = [pad_to_length(series, length) for series in series_list]
    return [sum(values) for values in zip(*padded)]


def annual_energy_kwh(tech_results: dict[str, Any]) -> float:
    """Annual production from a REopt tech block, whichever key it carries."""
    return float(
        tech_results.get("year_one_energy_produced_kwh")
        or tech_results.get("annual_energy_produced_kwh")
        or 0.0
    )


def financial_value(results: dict[str, Any], key: str, default: float) -> float:
    """Read ``key`` from a REopt ``Financial`` block, falling back to ``default``.

    A stored falsy value (``0``, ``None``) also falls through to ``default``.
    That is the long-standing semantic of the helper this replaces; it is
    preserved deliberately rather than tightened, so no number moves.
    """
    return float(results.get("Financial", {}).get(key) or default)
