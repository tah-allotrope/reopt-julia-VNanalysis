"""Shared analysis contract: the deal-config input and the result types both
generalized pipelines produce.

Design notes
------------
- ``DealConfig`` is a higher-level descriptor than the existing input layers
  (the REopt ``Scenario`` dict and the ``*_extracted_inputs.json`` dict). The
  pipelines map a ``DealConfig`` down onto whichever input layer the underlying
  engine consumes; this keeps "describe a future Vietnam project" to one config.
- ``OffsiteDppaResult`` mirrors, key-for-key, the combined-decision artifact the
  bespoke case modules already emit (see
  ``examples/samsung-ttc_combined-decision.example.json``) so the PHASE-04 parity
  gate can compare ``to_dict()`` against the golden JSON exactly.
- Every type keeps a ``raw`` escape hatch for case-specific blocks that do not
  fit the common contract, so generalization never silently drops data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from reopt_pysam_vn.analysis.validation import validate_deal_config

__all__ = [
    "CombinedDecision",
    "DealConfig",
    "OffsiteDppaResult",
    "OnsiteResult",
]

# Analysis modes a DealConfig can request.
MODES = ("onsite", "offsite_dppa", "both")

# Top-level blocks of the offsite/DPPA combined-decision artifact, in emit order.
_OFFSITE_BLOCKS = (
    "deal",
    "base_settlement",
    "strike_sweep",
    "adder_sensitivity",
    "regime_stress",
    "decision",
    "quality",
)


@dataclass
class DealConfig:
    """A Vietnam project/deal description that drives the analysis pipelines.

    ``site``/``plant``/``load``/``contract``/``finance`` are open dicts (validated
    structurally against ``data/schemas/deal_config.schema.json``) so a deal can
    carry mode-specific detail without a rigid schema fighting real cases.
    """

    case: str
    mode: str
    title: str = ""
    site: dict[str, Any] = field(default_factory=dict)
    plant: dict[str, Any] = field(default_factory=dict)
    load: dict[str, Any] = field(default_factory=dict)
    contract: dict[str, Any] = field(default_factory=dict)
    finance: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"DealConfig.mode must be one of {MODES}, got {self.mode!r}")

    @classmethod
    def from_dict(cls, d: dict[str, Any], *, validate: bool = True) -> DealConfig:
        """Build a DealConfig from a dict.

        When ``validate`` is True (the default), structurally validates ``d``
        against ``data/schemas/deal_config.schema.json`` first and raises
        ``DealConfigValidationError`` (collecting every violation, not just the
        first) rather than a bare ``KeyError`` on malformed input. Pass
        ``validate=False`` to skip the check and fall back to the old bare
        ``KeyError`` behavior for a deliberately partial dict.
        """
        if validate:
            validate_deal_config(d)
        known = {"case", "mode", "title", "site", "plant", "load", "contract", "finance"}
        return cls(
            case=d["case"],
            mode=d["mode"],
            title=d.get("title", ""),
            site=dict(d.get("site", {})),
            plant=dict(d.get("plant", {})),
            load=dict(d.get("load", {})),
            contract=dict(d.get("contract", {})),
            finance=dict(d.get("finance", {})),
            raw={k: v for k, v in d.items() if k not in known},
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"case": self.case, "mode": self.mode, "title": self.title}
        for section in ("site", "plant", "load", "contract", "finance"):
            out[section] = dict(getattr(self, section))
        out.update(self.raw)
        return out


@dataclass
class OnsiteResult:
    """Behind-the-meter REopt PV+BESS outcome for a deal config."""

    case: str
    sizing: dict[str, Any] = field(default_factory=dict)
    dispatch: dict[str, Any] = field(default_factory=dict)
    economics: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OnsiteResult:
        known = {"case", "sizing", "dispatch", "economics"}
        return cls(
            case=d["case"],
            sizing=dict(d.get("sizing", {})),
            dispatch=dict(d.get("dispatch", {})),
            economics=dict(d.get("economics", {})),
            raw={k: v for k, v in d.items() if k not in known},
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"case": self.case}
        for section in ("sizing", "dispatch", "economics"):
            out[section] = dict(getattr(self, section))
        out.update(self.raw)
        return out


@dataclass
class OffsiteDppaResult:
    """Offsite/DPPA outcome — settlement, strike sweep, adder lever, regime
    stress, and decision — mirroring the bespoke combined-decision artifact."""

    case: str
    model: str = ""
    deal: dict[str, Any] = field(default_factory=dict)
    base_settlement: dict[str, Any] = field(default_factory=dict)
    strike_sweep: dict[str, Any] = field(default_factory=dict)
    adder_sensitivity: dict[str, Any] = field(default_factory=dict)
    regime_stress: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OffsiteDppaResult:
        known = {"case", "model", *_OFFSITE_BLOCKS}
        return cls(
            case=d["case"],
            model=d.get("model", ""),
            raw={k: v for k, v in d.items() if k not in known},
            **{block: dict(d.get(block, {})) for block in _OFFSITE_BLOCKS},
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"case": self.case}
        if self.model:
            out["model"] = self.model
        for block in _OFFSITE_BLOCKS:
            out[block] = getattr(self, block)
        out.update(self.raw)
        return out


@dataclass
class CombinedDecision:
    """Top-level wrapper combining the two analysis modes plus a recommendation."""

    case: str
    onsite: OnsiteResult | None = None
    offsite_dppa: OffsiteDppaResult | None = None
    recommendation: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CombinedDecision:
        known = {"case", "onsite", "offsite_dppa", "recommendation"}
        onsite = d.get("onsite")
        offsite = d.get("offsite_dppa")
        return cls(
            case=d["case"],
            onsite=OnsiteResult.from_dict(onsite) if onsite else None,
            offsite_dppa=OffsiteDppaResult.from_dict(offsite) if offsite else None,
            recommendation=d.get("recommendation", ""),
            raw={k: v for k, v in d.items() if k not in known},
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "case": self.case,
            "recommendation": self.recommendation,
            "onsite": self.onsite.to_dict() if self.onsite else None,
            "offsite_dppa": self.offsite_dppa.to_dict() if self.offsite_dppa else None,
        }
        out.update(self.raw)
        return out
