"""C3.1: report rendering is a module, and its template lives in the repo.

Report rendering had no module: 35 emitters under ``scripts/python/integration/``
each re-implemented template resolution and placeholder substitution. Twenty of
them read the template from a path outside the repo
(``~/.config/opencode/skills/report/assets/report-template.html`` or
``~/.claude/skills/report/assets/template.html``), neither of which exists — so
those emitters raised ``FileNotFoundError`` and the reports they produce could
not be regenerated on any other machine.

The repo already tracks the same template contract under ``assets/``. These
tests pin a module that owns resolution, substitution and writing.
"""

from __future__ import annotations

import pytest
from reopt_pysam_vn.common.reporting import (
    FINAL_REPORT_PLACEHOLDERS,
    PHASE_REPORT_PLACEHOLDERS,
    UnknownPlaceholderError,
    final_report_template,
    phase_report_template,
    render_report,
    write_report,
)


class TestTemplateResolution:
    def test_phase_template_is_tracked_in_the_repo(self):
        template = phase_report_template()

        assert template.is_file(), f"tracked phase template missing: {template}"
        assert template.parts[-2:] == ("assets", "report-template.html")

    def test_final_template_is_tracked_in_the_repo(self):
        template = final_report_template()

        assert template.is_file(), f"tracked final template missing: {template}"
        assert template.parts[-2:] == ("assets", "final-report-template.html")

    def test_no_template_path_points_outside_the_repo(self):
        for template in (phase_report_template(), final_report_template()):
            assert ".claude" not in template.parts
            assert "opencode" not in template.parts


class TestPlaceholderContracts:
    def test_phase_placeholders_match_the_tracked_template(self):
        import re

        text = phase_report_template().read_text(encoding="utf-8")
        in_template = set(re.findall(r"\{\{([A-Z_]+)\}\}", text))

        assert set(PHASE_REPORT_PLACEHOLDERS) == in_template

    def test_final_placeholders_match_the_tracked_template(self):
        import re

        text = final_report_template().read_text(encoding="utf-8")
        in_template = set(re.findall(r"\{\{([A-Z_]+)\}\}", text))

        assert set(FINAL_REPORT_PLACEHOLDERS) == in_template


class TestRendering:
    def test_fills_every_supplied_placeholder(self):
        html = render_report({name: f"<p>{name}</p>" for name in PHASE_REPORT_PLACEHOLDERS})

        assert "{{" not in html, "an unfilled placeholder survived into the output"
        assert "<p>PHASE_NAME</p>" in html

    def test_omitted_placeholders_render_empty_not_literal(self):
        html = render_report({"PHASE_NAME": "Phase 1"})

        assert "Phase 1" in html
        assert "{{DATE}}" not in html

    def test_an_unknown_placeholder_is_an_error_not_a_silent_no_op(self):
        """The old emitters used ``sections.get(key, "")`` — a typo vanished."""
        with pytest.raises(UnknownPlaceholderError, match="PHSAE_NAME"):
            render_report({"PHSAE_NAME": "typo"})

    def test_final_report_uses_the_final_template(self):
        html = render_report({"REPORT_TITLE": "Deal X"}, template=final_report_template())

        assert "Deal X" in html
        assert "{{" not in html


class TestWriting:
    def test_writes_utf8_html_and_returns_the_path(self, tmp_path):
        out = write_report(
            tmp_path / "report.html", {"PHASE_NAME": "Phase 2 — Ninh Thuận"}
        )

        assert out.is_file()
        assert "Ninh Thuận" in out.read_text(encoding="utf-8")

    def test_creates_the_output_directory(self, tmp_path):
        out = write_report(tmp_path / "nested" / "deep" / "r.html", {"PHASE_NAME": "P"})

        assert out.is_file()
