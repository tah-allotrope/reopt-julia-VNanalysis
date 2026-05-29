"""GAP-03 PHASE-02: factory-to-project matching engine.

Scores each developer project in the catalog against a factory's energy
profile across five dimensions and returns a ranked list with per-dimension
scores, a human-readable explanation, and warning/blocker flags.

Direction is factory -> projects ("which projects fit this factory?"). Scoring
is heuristic, not optimization: the engine ranks and explains, it does not
prescribe. All five dimensions use equal default weights (20% each).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from reopt_pysam_vn.integration.project_catalog import ProjectRecord

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "physical": 0.20,
    "geographic": 0.20,
    "capacity": 0.20,
    "commercial": 0.20,
    "regulatory": 0.20,
}

# Indicative Vietnam annual capacity factors used to estimate annual generation
# from nameplate capacity when no 8760 generation profile is available.
SOLAR_CF = 0.18
WIND_CF = 0.32

# How well each technology coincides with a typical daytime-heavy industrial
# load (used by the capacity-only physical-fit estimate).
TECH_DAYTIME_COINCIDENCE: dict[str, float] = {
    "solar": 1.00,
    "solar_bess": 1.00,
    "hybrid": 0.70,
    "wind_bess": 0.55,
    "wind": 0.40,
}

# Region adjacency for the geographic-fit dimension.
_ADJACENT_REGIONS = {
    ("north", "central"),
    ("central", "north"),
    ("central", "south"),
    ("south", "central"),
}

VIABILITY_MIN_SCORE = 50.0

_ONSITE = "onsite_private_wire"


# --------------------------------------------------------------------------
# Data classes
# --------------------------------------------------------------------------


@dataclass
class FactoryProfile:
    """A factory's energy and site characteristics for matching."""

    name: str
    region: str
    annual_consumption_kwh: float
    peak_demand_kw: float
    loads_kw: list[float] = field(default_factory=list)
    voltage_level: str = "medium_voltage_22kv_to_110kv"
    colocated_project_id: str | None = None
    location: dict[str, Any] | None = None
    evn_baseline_usc_kwh: float = 7.8

    @classmethod
    def from_annuals(
        cls,
        name: str,
        region: str,
        annual_consumption_kwh: float,
        peak_demand_kw: float,
        **kwargs: Any,
    ) -> "FactoryProfile":
        return cls(
            name=name,
            region=region,
            annual_consumption_kwh=annual_consumption_kwh,
            peak_demand_kw=peak_demand_kw,
            **kwargs,
        )

    @classmethod
    def from_loads(
        cls, name: str, region: str, loads_kw: list[float], **kwargs: Any
    ) -> "FactoryProfile":
        if not loads_kw:
            raise ValueError("loads_kw must be non-empty")
        return cls(
            name=name,
            region=region,
            annual_consumption_kwh=float(sum(loads_kw)),
            peak_demand_kw=float(max(loads_kw)),
            loads_kw=list(loads_kw),
            **kwargs,
        )


@dataclass
class ProjectMatch:
    """A scored project-factory pairing."""

    project_id: str
    project_name: str
    overall_score: float
    dimension_scores: dict[str, float]
    fit_explanation: str
    flags: list[str] = field(default_factory=list)

    @property
    def is_viable(self) -> bool:
        has_blocker = any(f.startswith("BLOCKER") for f in self.flags)
        return (not has_blocker) and self.overall_score >= VIABILITY_MIN_SCORE


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def estimate_annual_generation_kwh(project: ProjectRecord) -> float:
    """Estimate a project's annual generation from nameplate capacity.

    Uses explicit ``solar_mw`` / ``wind_mw`` splits when present in the record's
    extra fields; otherwise maps the technology label to a single resource.
    """
    solar_mw = project.extra.get("solar_mw")
    wind_mw = project.extra.get("wind_mw")
    if solar_mw is not None or wind_mw is not None:
        solar_mw = float(solar_mw or 0.0)
        wind_mw = float(wind_mw or 0.0)
    else:
        tech = project.technology
        if tech in ("solar", "solar_bess"):
            solar_mw, wind_mw = project.capacity_mw, 0.0
        elif tech in ("wind", "wind_bess"):
            solar_mw, wind_mw = 0.0, project.capacity_mw
        else:  # hybrid without an explicit split: assume an even mix
            solar_mw = wind_mw = project.capacity_mw / 2.0
    annual_mwh = (solar_mw * SOLAR_CF + wind_mw * WIND_CF) * 8760.0
    return annual_mwh * 1000.0


# --- physical fit ---------------------------------------------------------


def _capacity_adequacy(ratio: float) -> float:
    """Triangular adequacy of project capacity vs factory peak demand (0..1)."""
    if 0.8 <= ratio <= 1.5:
        return 1.0
    if ratio < 0.8:
        if ratio <= 0.2:
            return 0.0
        return (ratio - 0.2) / (0.8 - 0.2)
    # ratio > 1.5
    if ratio >= 3.0:
        return 0.0
    return (3.0 - ratio) / (3.0 - 1.5)


def physical_fit_from_profile(
    load_kw: list[float], gen_kw: list[float], bess_power_kw: float = 0.0
) -> float:
    """Physical fit from 8760 profiles: solar-absorption ratio with a simple
    instantaneous BESS headroom proxy (mirrors rank_case_study_offtakers)."""
    n = min(len(load_kw), len(gen_kw))
    if n == 0:
        return 0.0
    total_gen = 0.0
    matched = 0.0
    for i in range(n):
        g = gen_kw[i]
        if g <= 0.0:
            continue
        total_gen += g
        matched += min(load_kw[i] + bess_power_kw, g)
    if total_gen <= 0.0:
        return 0.0
    return _clamp(100.0 * matched / total_gen)


def _physical_fit_estimate(project: ProjectRecord, factory: FactoryProfile) -> float:
    peak_mw = max(factory.peak_demand_kw / 1000.0, 1e-9)
    ratio = project.capacity_mw / peak_mw
    adequacy = _capacity_adequacy(ratio)
    tech = TECH_DAYTIME_COINCIDENCE.get(project.technology, 0.5)
    bess_hours = project.bess_mwh / peak_mw if peak_mw > 0 else 0.0
    bess_bonus = min(bess_hours / 4.0, 1.0)
    return _clamp(100.0 * (0.45 * adequacy + 0.35 * tech + 0.20 * bess_bonus))


def _physical_fit(project: ProjectRecord, factory: FactoryProfile) -> float:
    gen = project.extra.get("generation_profile_kw")
    if gen and factory.loads_kw:
        return physical_fit_from_profile(
            factory.loads_kw, gen, bess_power_kw=project.bess_mw * 1000.0
        )
    return _physical_fit_estimate(project, factory)


# --- geographic fit -------------------------------------------------------


def _geographic_fit(project: ProjectRecord, factory: FactoryProfile) -> tuple[float, list[str]]:
    flags: list[str] = []
    if project.grid_connection == _ONSITE:
        if factory.colocated_project_id == project.project_id:
            return 100.0, flags
        flags.append(
            "BLOCKER: private-wire (onsite) project is not co-located with this factory"
        )
        return 0.0, flags
    a, b = factory.region, project.location.get("region", "")
    if a == b:
        return 100.0, flags
    if (a, b) in _ADJACENT_REGIONS:
        return 70.0, flags
    flags.append("WARN: project is cross-country from the factory (transmission distance)")
    return 40.0, flags


# --- capacity fit ---------------------------------------------------------


def _capacity_fit(project: ProjectRecord, factory: FactoryProfile) -> tuple[float, list[str]]:
    flags: list[str] = []
    annual_gen = estimate_annual_generation_kwh(project)
    consumption = max(factory.annual_consumption_kwh, 1e-9)
    ratio = annual_gen / consumption
    if 0.3 <= ratio <= 0.7:
        score = 100.0
    elif ratio < 0.3:
        if ratio >= 0.1:
            score = 40.0 + (ratio - 0.1) / (0.3 - 0.1) * (100.0 - 40.0)
            flags.append("WARN: project is undersized relative to factory annual consumption")
        else:
            score = 10.0 + (ratio / 0.1) * (40.0 - 10.0)
            flags.append(
                "BLOCKER: project is far too small to serve this factory "
                f"(annual generation is ~{ratio * 100:.0f}% of consumption)"
            )
    elif ratio <= 1.5:
        score = 100.0 - (ratio - 0.7) / (1.5 - 0.7) * (100.0 - 60.0)
    elif ratio <= 3.0:
        score = 60.0 - (ratio - 1.5) / (3.0 - 1.5) * (60.0 - 20.0)
        flags.append("WARN: project is oversized relative to factory annual consumption")
    else:
        score = 10.0
        flags.append(
            "BLOCKER: project is far too large for this factory "
            f"(annual generation is ~{ratio:.1f}x consumption)"
        )
    return _clamp(score), flags


# --- commercial fit -------------------------------------------------------


def _commercial_fit(project: ProjectRecord, factory: FactoryProfile) -> tuple[float, list[str]]:
    flags: list[str] = []
    strike = project.indicative_strike_usc_kwh
    baseline = factory.evn_baseline_usc_kwh
    if not strike or strike <= 0 or baseline <= 0:
        flags.append("WARN: no indicative strike price; commercial fit is neutral")
        return 50.0, flags
    savings_pct = (baseline - strike) / baseline
    score = 50.0 + savings_pct * 250.0
    if savings_pct < 0:
        flags.append("WARN: indicative strike is above the factory's EVN baseline (buyer premium)")
    return _clamp(score), flags


# --- regulatory fit -------------------------------------------------------


def _regulatory_fit(project: ProjectRecord, factory: FactoryProfile) -> tuple[float, list[str]]:
    flags: list[str] = []
    # DPPA structure / private-wire eligibility.
    if project.dppa_structure == "private_wire" or project.grid_connection == _ONSITE:
        if factory.colocated_project_id != project.project_id:
            flags.append(
                "BLOCKER: private-wire / onsite structure requires the factory at the project site"
            )
            return 10.0, flags
        score = 100.0
        # Decree 57 export-cap headroom: onsite generation well above peak risks
        # export beyond the permitted cap.
        if project.capacity_mw > 1.6 * (factory.peak_demand_kw / 1000.0):
            score -= 20.0
            flags.append("WARN: onsite capacity may exceed Decree 57 export-cap headroom")
    else:
        # Offsite virtual CfD / physical DPPA: broadly eligible.
        score = 100.0

    # Voltage compatibility (light check).
    if project.grid_connection == "grid_connected_110kv" and factory.voltage_level in (
        "low_voltage",
        "low_voltage_below_1kv",
    ):
        score -= 15.0
        flags.append("WARN: 110kV interconnection may not suit a low-voltage factory connection")

    return _clamp(score), flags


# --------------------------------------------------------------------------
# Explanation
# --------------------------------------------------------------------------


def _build_explanation(
    project: ProjectRecord, dims: dict[str, float], overall: float
) -> str:
    best = max(dims, key=dims.get)
    worst = min(dims, key=dims.get)
    verdict = (
        "strong fit" if overall >= 75 else "moderate fit" if overall >= 50 else "weak fit"
    )
    return (
        f"{project.name} ({project.technology}, {project.capacity_mw:.1f} MW, "
        f"{project.location.get('region', '?')}) is a {verdict} at {overall:.0f}/100 overall: "
        f"strongest on {best} ({dims[best]:.0f}), weakest on {worst} ({dims[worst]:.0f})."
    )


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def score_project(
    project: ProjectRecord,
    factory: FactoryProfile,
    weights: dict[str, float] | None = None,
) -> ProjectMatch:
    """Score a single project against a factory across all five dimensions."""
    weights = weights or DEFAULT_WEIGHTS
    flags: list[str] = []

    physical = _physical_fit(project, factory)
    geographic, geo_flags = _geographic_fit(project, factory)
    capacity, cap_flags = _capacity_fit(project, factory)
    commercial, com_flags = _commercial_fit(project, factory)
    regulatory, reg_flags = _regulatory_fit(project, factory)
    flags.extend(geo_flags + cap_flags + com_flags + reg_flags)

    dims = {
        "physical": round(physical, 1),
        "geographic": round(geographic, 1),
        "capacity": round(capacity, 1),
        "commercial": round(commercial, 1),
        "regulatory": round(regulatory, 1),
    }
    overall = round(sum(dims[d] * weights[d] for d in dims), 1)
    explanation = _build_explanation(project, dims, overall)

    return ProjectMatch(
        project_id=project.project_id,
        project_name=project.name,
        overall_score=overall,
        dimension_scores=dims,
        fit_explanation=explanation,
        flags=flags,
    )


def match_projects_to_factory(
    factory: FactoryProfile,
    project_catalog: list[ProjectRecord],
    tariff_params: dict[str, Any] | None = None,
    weights: dict[str, float] | None = None,
) -> list[ProjectMatch]:
    """Score every project in the catalog against ``factory`` and rank them.

    ``tariff_params`` may carry an ``evn_baseline_usc_kwh`` override used for the
    commercial-fit baseline when the factory profile does not set one.
    """
    if tariff_params and tariff_params.get("evn_baseline_usc_kwh"):
        factory = FactoryProfile(
            **{**factory.__dict__, "evn_baseline_usc_kwh": tariff_params["evn_baseline_usc_kwh"]}
        )

    matches = [score_project(p, factory, weights) for p in project_catalog]
    matches.sort(key=lambda m: m.overall_score, reverse=True)
    return matches
