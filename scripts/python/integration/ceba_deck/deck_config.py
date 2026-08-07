"""Deck-agnostic configuration for the repo-checked deck pipeline.

Both the CEBA 2026 deck and the DPPA July 2026 Case Studies deck share the same
verification scaffolding (a registry of checks, an orchestrator, a markdown
synthesizer, and a note-injector). The only things that differ are the deck
file, the registry module, the slide numbers, the output filenames, and the
deck title. This module is the single source of truth for those paths.

The default for every entry point is ``CEBA_2026`` so the committed CEBA
pipeline, registry, reports, and tests keep working unchanged. The July 2026
deck is invoked by passing ``--deck july`` (or the equivalent config arg).

Each DeckConfig carries:
  - source_pptx: path to the read-only deck binary
  - out_pptx:   path the injector writes its [repo-checked] copy to
  - text_txt:   path the text extractor writes the flat text dump to
  - registry_module: dotted path to the registry module (e.g.
    "integration.ceba_deck.july_deck_checks")
  - results_json: path the orchestrator writes its results to
  - report_md:   path the markdown synthesizer writes its report to
  - calibration_json: path the Case 5/6 calibration ledger is written to
  - deck_title: human-readable name used in the markdown header
  - known_gap_topic_filter: substring that distinguishes the deck's
    out-of-scope topics (e.g. "REC" / "GHG" for CEBA; not used for July)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class DeckConfig:
    key: str
    source_pptx: Path
    out_pptx: Path
    text_txt: Path
    registry_module: str
    results_json: Path
    report_md: Path
    calibration_json: Path | None
    deck_title: str
    plan_path: str


CEBA_2026 = DeckConfig(
    key="ceba",
    source_pptx=REPO_ROOT / "ceba-review" / "CEBA DPPA 2026.pptx",
    out_pptx=REPO_ROOT / "ceba-review" / "CEBA DPPA 2026 [repo-checked].pptx",
    text_txt=REPO_ROOT / "ceba-review" / "ceba_dppa_2026_text.txt",
    registry_module="integration.ceba_deck.deck_checks",
    results_json=REPO_ROOT / "reports" / "ceba_dppa_2026_repo_check.json",
    report_md=REPO_ROOT / "reports" / "ceba_dppa_2026_repo_check.md",
    calibration_json=None,
    deck_title="CEBA DPPA 2026",
    plan_path="plans/2026-06-23-ceba-deck-repo-verification-plan.md",
)

JULY_2026 = DeckConfig(
    key="july",
    source_pptx=REPO_ROOT / "ceba-review" / "DPPA Presentation July 2026 Case Studies.pptx",
    out_pptx=REPO_ROOT / "ceba-review" / "DPPA Presentation July 2026 Case Studies [repo-checked].pptx",
    text_txt=REPO_ROOT / "ceba-review" / "dppa_july_2026_case_studies_text.txt",
    registry_module="integration.ceba_deck.july_deck_checks",
    results_json=REPO_ROOT / "reports" / "dppa_july_2026_repo_check.json",
    report_md=REPO_ROOT / "reports" / "dppa_july_2026_repo_check.md",
    calibration_json=REPO_ROOT / "reports" / "dppa_july_2026_calibration.json",
    deck_title="DPPA July 2026 Case Studies",
    plan_path="plans/active/2026-06-26-dppa-july-deck-verification-plan.md",
)

DECKS: dict[str, DeckConfig] = {
    CEBA_2026.key: CEBA_2026,
    JULY_2026.key: JULY_2026,
}


def get_deck(name: str | None) -> DeckConfig:
    """Resolve a deck name (or alias) to a DeckConfig. Defaults to CEBA_2026."""
    if name is None:
        return CEBA_2026
    key = name.lower().strip()
    if key in ("ceba", "ceba_2026"):
        return CEBA_2026
    if key in ("july", "july_2026", "dppa_july_2026"):
        return JULY_2026
    raise SystemExit(
        f"unknown deck name: {name!r}. Known: {sorted(DECKS.keys())}"
    )
