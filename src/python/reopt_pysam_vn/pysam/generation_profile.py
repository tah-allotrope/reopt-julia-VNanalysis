"""Resolve an 8760 generation profile — one module, one interface.

Before this module the profile was resolved twice: once in
``analysis.orchestrators.generic_vn_dppa`` and once in
``integration.dppa_samsung_ttc``. Each carried its own three-tier ladder
(explicit series -> PVWatts on a cached resource -> deterministic synthetic
shape), its own PySAM import guard, its own calibration, and its own ``source``
vocabulary — and each signalled a fall-back by returning ``None``, so a
degraded profile was indistinguishable from a real one at the call site.

The ladder now lives here. Callers pass what varies (capacity, array
configuration, annual target) and receive a
:class:`GenerationProfile` that states which adapter ran and why, with any
degradation carried in ``warnings`` rather than implied by ``None``.

Never fetches over the network: the PVWatts adapter runs only against an
already-cached resource file.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HOURS = 8760

#: Canonical source vocabulary. Callers that publish a legacy label (Samsung's
#: golden, the parity gate's ``"pvwatts" in source`` check) map from these.
SOURCE_EXTRACTED = "extracted"
SOURCE_PVWATTS = "pvwatts"
SOURCE_SYNTHETIC = "synthetic"


@dataclass(frozen=True)
class ArrayConfig:
    """The PVWatts system parameters a caller is allowed to vary.

    ``azimuth``, ``gcr`` and ``module_type`` were the values the two old ladders
    disagreed about — one set them explicitly, one inherited them. They are the
    PVWatts defaults, so making them explicit is value-preserving.
    """

    array_type: int
    tilt_degrees: float
    azimuth: float = 180.0
    gcr: float = 0.3
    module_type: int = 0
    dc_ac_ratio: float = 1.2
    losses_pct: float = 14.0
    inv_eff_pct: float = 96.0


@dataclass(frozen=True)
class GenerationProfile:
    """An 8760 kW series plus the provenance of how it was obtained."""

    series_kw: list[float]
    source: str
    calibrated_to_gwh: float | None = None
    native_annual_gwh: float | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_kw": self.series_kw,
            "source": self.source,
            "calibrated_to_gwh": self.calibrated_to_gwh,
            "native_annual_gwh": self.native_annual_gwh,
            "provenance": dict(self.provenance),
            "warnings": list(self.warnings),
        }


# ---------------------------------------------------------------------------
# Shared implementation: calibration and the synthetic shape
# ---------------------------------------------------------------------------


def pad_to_8760(series: list[float]) -> list[float]:
    """Coerce to float and pad or truncate to exactly 8760 hours."""
    if len(series) >= HOURS:
        return [float(value) for value in series[:HOURS]]
    return [float(value) for value in series] + [0.0] * (HOURS - len(series))


def calibrate_to_target(
    series: list[float], annual_target_kwh: float, cap_kw: float | None
) -> tuple[list[float], list[str]]:
    """Scale a shape to an annual target, AC-clipping at ``cap_kw``.

    Clip loss is redistributed only across the daylight set — hours where the
    input shape is non-zero — so redistribution can never place generation in a
    dark hour. Verified bit-identical to the previous Samsung single-pass
    calibration on that deal's real inputs before adoption.
    """
    warnings: list[str] = []
    total = sum(series)

    if cap_kw is None:
        if total == 0:
            return [0.0] * len(series), warnings
        scale = annual_target_kwh / total
        return [value * scale for value in series], warnings

    daylight = [index for index, value in enumerate(series) if value > 0]
    if not daylight:
        warnings.append("generation shape is entirely zero")
        return [0.0] * len(series), warnings

    emax = cap_kw * len(daylight)
    if annual_target_kwh > emax:
        out = [0.0] * len(series)
        for index in daylight:
            out[index] = cap_kw
        warnings.append(
            f"annual target {annual_target_kwh / 1e6:.3f} GWh is infeasible at "
            f"{cap_kw / 1000:.3f} MWac (max {emax / 1e6:.3f} GWh); series clipped at the AC cap"
        )
        return out, warnings

    scale = annual_target_kwh / total if total else 0.0
    out = [min(value * scale, cap_kw) for value in series]

    for _ in range(50):
        deficit = annual_target_kwh - sum(out)
        if deficit <= 1.0:
            break
        headroom = [0.0] * len(series)
        for index in daylight:
            headroom[index] = cap_kw - out[index]
        head_total = sum(headroom)
        if head_total <= 1e-9:
            break
        for index in daylight:
            out[index] = min(out[index] + deficit * headroom[index] / head_total, cap_kw)
    return out, warnings


def synthetic_shape_8760() -> list[float]:
    """Deterministic representative shape: half-sine daylight arc x seasonal term.

    Southern Vietnam: the dry season (~Jan) is sunnier than the wet (~Jul).

    The shape depends only on hour-of-day and day-of-year, both of which run
    1..365 over the first 8760 hours of any year, leap or not. The old Samsung
    ladder took a ``reference_year`` argument that therefore could not change
    the result; it is not part of this interface.
    """
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    weights: list[float] = []
    for hour_index in range(HOURS):
        timestamp = start + timedelta(hours=hour_index)
        hour = timestamp.hour
        arc = math.sin(math.pi * (hour - 6) / 12.0) if 6 <= hour < 18 else 0.0
        day_of_year = timestamp.timetuple().tm_yday
        seasonal = 1.0 + 0.18 * math.cos(2.0 * math.pi * (day_of_year - 15) / 365.0)
        weights.append(max(0.0, arc * seasonal))
    return weights


# ---------------------------------------------------------------------------
# The PVWatts adapter
# ---------------------------------------------------------------------------


def run_pvwatts(
    *,
    system_capacity_kw_dc: float,
    array: ArrayConfig,
    resource_file: str | Path,
) -> list[float] | None:
    """Run PVWatts v8 against an already-cached resource. ``None`` if unavailable.

    Returning ``None`` here is fine: this is the adapter, and
    :func:`resolve_generation_profile` converts it into a stated warning.
    """
    try:
        import PySAM.Pvwattsv8 as pv
    except ImportError:
        return None

    resource = Path(resource_file)
    if not resource.is_file():
        return None

    try:
        model = pv.default("PVWattsSingleOwner")
        model.SolarResource.solar_resource_file = str(resource)
        model.SystemDesign.system_capacity = float(system_capacity_kw_dc)
        model.SystemDesign.dc_ac_ratio = float(array.dc_ac_ratio)
        model.SystemDesign.inv_eff = float(array.inv_eff_pct)
        model.SystemDesign.losses = float(array.losses_pct)
        model.SystemDesign.array_type = float(array.array_type)
        model.SystemDesign.tilt = float(array.tilt_degrees)
        model.SystemDesign.azimuth = float(array.azimuth)
        model.SystemDesign.gcr = float(array.gcr)
        model.SystemDesign.module_type = float(array.module_type)
        model.execute(0)
        gen = list(model.Outputs.gen)
    except Exception:  # noqa: BLE001 - PySAM raises a bare Exception on simulation failure.
        return None

    return pad_to_8760([max(0.0, float(value)) for value in gen[:HOURS]])


def default_resource_file() -> Path | None:
    """The tracked cached solar resource, or ``None`` when it cannot be located."""
    try:
        from reopt_pysam_vn.pysam.pvwatts_battery import DEFAULT_SOLAR_RESOURCE_FILE
    except (ImportError, AttributeError):
        return None
    return Path(DEFAULT_SOLAR_RESOURCE_FILE)


def resource_provenance(
    resource: Path, site_latitude: float | None, site_longitude: float | None
) -> tuple[dict[str, Any], list[str]]:
    """Describe the resource file and how far it sits from the site."""
    provenance: dict[str, Any] = {"resource_file": resource.name}
    warnings: list[str] = []
    try:
        from reopt_pysam_vn.pysam.pvwatts_battery import great_circle_km, resource_coordinates
    except (ImportError, AttributeError):
        return provenance, warnings

    coords = resource_coordinates(resource)
    provenance["resource_latitude"] = coords[0] if coords else None
    provenance["resource_longitude"] = coords[1] if coords else None
    if coords is not None and site_latitude is not None and site_longitude is not None:
        distance = great_circle_km(site_latitude, site_longitude, coords[0], coords[1])
        provenance["distance_km"] = round(float(distance), 1)
    return provenance, warnings


# ---------------------------------------------------------------------------
# The interface
# ---------------------------------------------------------------------------


def resolve_generation_profile(
    *,
    extracted_series: list[float] | None = None,
    target_kwh: float | None = None,
    cap_kw: float | None = None,
    system_capacity_kw_dc: float | None = None,
    array: ArrayConfig | None = None,
    resource_file: str | Path | None = None,
    use_pvwatts: bool = True,
    pvwatts_skip_reason: str | None = None,
    site_latitude: float | None = None,
    site_longitude: float | None = None,
) -> GenerationProfile:
    """Resolve the 8760 generation profile, stating which adapter produced it.

    Ladder, first hit wins:

    1. ``extracted_series`` — an explicit 8760 series supplied by the caller.
    2. PVWatts against a cached resource (needs ``system_capacity_kw_dc`` and
       ``array``; never fetches over the network). A caller that skips this rung
       should say why via ``pvwatts_skip_reason`` so the warning is truthful.
    3. A deterministic synthetic shape.

    When ``target_kwh`` is given the series is calibrated to it, AC-clipped at
    ``cap_kw`` when supplied. Every degradation — a rejected series, an absent
    PySAM, an infeasible target — is appended to ``warnings``; the caller is
    never handed a silent substitute.
    """
    warnings: list[str] = []
    provenance: dict[str, Any] = {}
    native_annual_gwh: float | None = None
    series: list[float] | None = None
    source = SOURCE_SYNTHETIC

    if extracted_series is not None:
        if len(extracted_series) == HOURS:
            series = [float(value) for value in extracted_series]
            source = SOURCE_EXTRACTED
        else:
            warnings.append(
                f"supplied generation series has {len(extracted_series)} hours, not 8760; "
                "falling back to the resolved profile"
            )

    if series is None and use_pvwatts and system_capacity_kw_dc is not None and array is not None:
        resource = Path(resource_file) if resource_file else default_resource_file()
        if resource is None or not resource.is_file():
            warnings.append(
                "no cached solar resource file available; falling back to a synthetic profile"
            )
        else:
            gen = run_pvwatts(
                system_capacity_kw_dc=system_capacity_kw_dc,
                array=array,
                resource_file=resource,
            )
            if gen is None or sum(gen) <= 0.0:
                warnings.append(
                    "PySAM PVWatts unavailable or produced no generation; "
                    "falling back to a synthetic profile"
                )
            else:
                series = gen
                source = SOURCE_PVWATTS
                native_annual_gwh = sum(gen) / 1e6
                resource_prov, resource_warnings = resource_provenance(
                    resource, site_latitude, site_longitude
                )
                provenance.update(resource_prov)
                provenance["array_type"] = array.array_type
                provenance["tilt_degrees"] = float(array.tilt_degrees)
                warnings.extend(resource_warnings)

    if series is None:
        if source != SOURCE_SYNTHETIC:  # pragma: no cover - defensive
            source = SOURCE_SYNTHETIC
        if use_pvwatts and not any("synthetic" in w for w in warnings):
            warnings.append(
                "PySAM PVWatts was not run; falling back to a synthetic profile"
            )
        elif not use_pvwatts:
            warnings.append(
                f"{pvwatts_skip_reason or 'PVWatts not requested'}; using a synthetic profile"
            )
        series = synthetic_shape_8760()

    calibrated_to_gwh: float | None = None
    if target_kwh is not None:
        series, calibration_warnings = calibrate_to_target(series, target_kwh, cap_kw)
        warnings.extend(calibration_warnings)
        calibrated_to_gwh = target_kwh / 1e6
    elif source == SOURCE_SYNTHETIC:
        # A bare shape is not a kW series; scale it to a nominal 1 GWh.
        series, _ = calibrate_to_target(series, 1.0e6, cap_kw)

    return GenerationProfile(
        series_kw=pad_to_8760(series),
        source=source,
        calibrated_to_gwh=calibrated_to_gwh,
        native_annual_gwh=native_annual_gwh,
        provenance=provenance,
        warnings=warnings,
    )
