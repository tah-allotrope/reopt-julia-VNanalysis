"""Render an HTML report from a tracked template — one module, one interface.

Report rendering had no module. Thirty-five emitters under
``scripts/python/integration/`` each re-implemented template resolution and
placeholder substitution, and twenty of them resolved the template out of a
user's home directory (``~/.config/opencode/skills/report/assets/`` or
``~/.claude/skills/report/assets/``) rather than the repo. Neither path exists,
so those emitters raised ``FileNotFoundError`` and their reports could not be
regenerated anywhere.

The templates are tracked under ``assets/``. This module owns resolving them,
filling their placeholders, and writing the result.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_ASSETS_DIR = _REPO_ROOT / "assets"

#: Placeholders in ``assets/report-template.html`` (per-phase reports).
PHASE_REPORT_PLACEHOLDERS: tuple[str, ...] = (
    "CHARTS_SECTION",
    "DATE",
    "ERRORS_WARNINGS_FLAGS",
    "INPUT_OUTPUT_CONTENT",
    "LIMITATIONS_ALTERNATIVES",
    "MATH_ALGORITHM_SECTION",
    "MERMAID_DIAGRAM",
    "OPEN_QUESTIONS",
    "PHASE_NAME",
    "PROJECT",
    "REPO",
    "TOOLS_METHODS",
)

#: Placeholders in ``assets/final-report-template.html`` (client-shareable reports).
FINAL_REPORT_PLACEHOLDERS: tuple[str, ...] = (
    "APPENDICES_EVIDENCE",
    "ASSUMPTIONS_CONSTRAINTS",
    "BACKGROUND_OBJECTIVE",
    "DATE",
    "EXECUTIVE_SUMMARY",
    "FINDINGS_RECOMMENDATION",
    "IMPLEMENTATION_PATH",
    "INPUTS_SCOPE",
    "METHODOLOGY",
    "ONE_LINE_TAKEAWAY",
    "OPTIONAL_CHARTS_BLOCK",
    "OPTIONAL_MERMAID_BLOCK",
    "PHASE_ANALYSIS",
    "PROJECT",
    "REPORT_TITLE",
    "REPO",
    "RISKS_OPEN_QUESTIONS",
)


class UnknownPlaceholderError(KeyError):
    """A section name that no template placeholder matches.

    The emitters this module replaces used ``sections.get(key, "")``, so a typo
    in a section name silently produced an empty block in the report. Raising
    turns that into a caught mistake.
    """


def phase_report_template() -> Path:
    """The tracked per-phase report template."""
    return _ASSETS_DIR / "report-template.html"


def final_report_template() -> Path:
    """The tracked client-shareable final report template."""
    return _ASSETS_DIR / "final-report-template.html"


def _placeholders_in(template: Path) -> tuple[str, ...]:
    if template == final_report_template():
        return FINAL_REPORT_PLACEHOLDERS
    return PHASE_REPORT_PLACEHOLDERS


def render_report(sections: dict[str, str], *, template: Path | None = None) -> str:
    """Fill ``template`` with ``sections``, keyed by bare placeholder name.

    Placeholders the caller omits render empty. A section name that matches no
    placeholder raises :class:`UnknownPlaceholderError` rather than being
    dropped.
    """
    template = template or phase_report_template()
    known = _placeholders_in(template)

    unknown = sorted(set(sections) - set(known))
    if unknown:
        raise UnknownPlaceholderError(
            f"no such placeholder in {template.name}: {', '.join(unknown)}. "
            f"Known placeholders: {', '.join(known)}"
        )

    html = template.read_text(encoding="utf-8")
    for name in known:
        html = html.replace("{{" + name + "}}", sections.get(name, ""))
    return html


def write_report(
    out_path: str | Path, sections: dict[str, str], *, template: Path | None = None
) -> Path:
    """Render and write a report, creating parent directories as needed."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(sections, template=template), encoding="utf-8")
    return path
