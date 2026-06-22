"""Extract text from CEBA DPPA 2026.pptx into a flat text file for review.

Usage (from repo root):
    .venv/Scripts/python.exe scripts/python/integration/_extract_ceba_deck_text.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation

REPO_ROOT = Path(__file__).resolve().parents[3]
DECK_PATH = REPO_ROOT / "ceba-review" / "CEBA DPPA 2026.pptx"
OUT_PATH = REPO_ROOT / "ceba-review" / "ceba_dppa_2026_text.txt"


def _walk_shapes(shapes, depth: int = 0) -> list:
    """Recursively collect all shapes (including grouped)."""
    out = []
    for shape in shapes:
        out.append((shape, depth))
        if shape.shape_type == 6:  # GROUP
            out.extend(_walk_shapes(shape.shapes, depth + 1))
    return out


def extract_text(pptx_path: Path) -> str:
    prs = Presentation(str(pptx_path))
    lines: list[str] = []
    for i, slide in enumerate(prs.slides, start=1):
        lines.append(f"[Slide {i}]")
        for shape, _ in _walk_shapes(slide.shapes):
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = "".join(run.text for run in para.runs)
                    if text.strip():
                        lines.append(text)
            if shape.has_table:
                tbl = shape.table
                for row in tbl.rows:
                    cells = []
                    for cell in row.cells:
                        cell_text = " ".join(
                            p.text for p in cell.text_frame.paragraphs if p.text.strip()
                        )
                        cells.append(cell_text.strip())
                    lines.append(" | ".join(cells))
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    if not DECK_PATH.exists():
        print(f"Deck not found: {DECK_PATH}", file=sys.stderr)
        return 1
    text = extract_text(DECK_PATH)
    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"Extracted {len(text):,} chars -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
