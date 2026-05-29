"""GAP-03 phase report generator.

Fills ``assets/report-template.html`` with phase content and writes a
self-contained HTML report under ``reports/``. Reused across all GAP-03
phases so each phase ships a consistent artifact.
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = REPO_ROOT / "assets" / "report-template.html"
REPORTS_DIR = REPO_ROOT / "reports"

PLACEHOLDERS = (
    "PHASE_NAME",
    "PROJECT",
    "DATE",
    "REPO",
    "INPUT_OUTPUT_CONTENT",
    "MERMAID_DIAGRAM",
    "MATH_ALGORITHM_SECTION",
    "TOOLS_METHODS",
    "CHARTS_SECTION",
    "LIMITATIONS_ALTERNATIVES",
    "ERRORS_WARNINGS_FLAGS",
    "OPEN_QUESTIONS",
)


def render(sections: dict[str, str]) -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    for key in PLACEHOLDERS:
        html = html.replace("{{" + key + "}}", sections.get(key, ""))
    return html


def write_report(slug: str, sections: dict[str, str]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{slug}.html"
    out_path.write_text(render(sections), encoding="utf-8")
    return out_path


# --------------------------------------------------------------------------
# Phase content
# --------------------------------------------------------------------------

PROJECT_NAME = "GAP-03 Developer Project Catalog &amp; Matching Engine"
REPO_NAME = "reopt-pysam"


def phase_01_sections() -> dict[str, str]:
    return {
        "PHASE_NAME": "GAP-03 PHASE-01 — Project Catalog Schema &amp; Seed Data",
        "PROJECT": PROJECT_NAME,
        "DATE": "2026-05-29",
        "REPO": REPO_NAME,
        "INPUT_OUTPUT_CONTENT": """
        <p><strong>Inputs:</strong> existing case studies (saigon18, ninhsim, north_thuan),
        the real-project basis documented in <code>AGENTS.md</code> (3.2 MWp PV, 1 MW / 2.2 MWh BESS, 22kV),
        and the <code>data/vietnam/</code> versioned-data pattern.</p>
        <p><strong>Outputs:</strong></p>
        <ul>
          <li><code>data/projects/catalog_schema.json</code> — record schema (required fields, types, enums, nested location).</li>
          <li>5 seed project JSONs spanning technologies, sizes, regions, and DPPA structures:
            <code>saigon18_onsite_solar_bess</code>, <code>ninhsim_offsite_solar_wind</code>,
            <code>north_thuan_offsite_solar_wind_bess</code>, <code>real_project_onsite_solar_bess</code>,
            <code>prospective_offsite_wind</code>.</li>
          <li><code>src/python/reopt_pysam_vn/integration/project_catalog.py</code> — loader + dependency-free validator
            (<code>load_project_catalog</code>, <code>load_catalog_schema</code>, <code>validate_project</code>, <code>ProjectRecord</code>).</li>
          <li><code>tests/python/integration/test_project_catalog.py</code> — 10 schema-validation tests.</li>
        </ul>
        """,
        "MERMAID_DIAGRAM": """flowchart LR
  S[catalog_schema.json] --> V[validate_project]
  P1[saigon18_onsite_solar_bess] --> V
  P2[ninhsim_offsite_solar_wind] --> V
  P3[north_thuan_offsite_solar_wind_bess] --> V
  P4[real_project_onsite_solar_bess] --> V
  P5[prospective_offsite_wind] --> V
  V --> L[load_project_catalog]
  L --> R[list&#91;ProjectRecord&#93;]""",
        "MATH_ALGORITHM_SECTION": """
        <p>Validation is structural, not numeric. For each record the validator checks:</p>
        <ul>
          <li><strong>Required fields present</strong> — every name in <code>schema.required</code>.</li>
          <li><strong>Type match</strong> — JSON type maps to Python type (<code>number</code> excludes <code>bool</code>;
            <code>["string","null"]</code> unions supported for optional <code>generation_profile_path</code>).</li>
          <li><strong>Enum membership</strong> — <code>technology</code>, <code>grid_connection</code>,
            <code>dppa_structure</code>, <code>status</code>, and <code>location.region</code>.</li>
          <li><strong>Minimums</strong> — capacities are non-negative.</li>
          <li><strong>Nested <code>location</code></strong> — requires <code>lat</code>, <code>lon</code>, <code>province</code>, <code>region</code>.</li>
        </ul>
        """,
        "TOOLS_METHODS": """
        <ul>
          <li>Python 3.11 dataclasses; stdlib <code>json</code> only (no <code>jsonschema</code> dependency).</li>
          <li>pytest for Red/Green TDD — failing tests written first, then implemented to green.</li>
          <li>One JSON file per project, mirroring <code>data/vietnam/</code>; <code>_meta</code> envelope for provenance.</li>
        </ul>
        """,
        "CHARTS_SECTION": """
        <table>
          <thead><tr><th>Project</th><th>Tech</th><th>Capacity (MW)</th><th>BESS</th><th>Grid</th><th>Region</th><th>Status</th></tr></thead>
          <tbody>
            <tr><td>Saigon18</td><td>solar_bess</td><td>40.36</td><td>20 MW / 66 MWh</td><td>onsite private-wire</td><td>south</td><td>development</td></tr>
            <tr><td>Ninh Sim</td><td>hybrid</td><td>54.0</td><td>—</td><td>110kV</td><td>central</td><td>development</td></tr>
            <tr><td>North Thuan</td><td>hybrid</td><td>50.0</td><td>10 MW / 40 MWh</td><td>110kV</td><td>central</td><td>development</td></tr>
            <tr><td>Binh Duong</td><td>solar_bess</td><td>3.2</td><td>1 MW / 2.2 MWh</td><td>onsite 22kV</td><td>south</td><td>operational</td></tr>
            <tr><td>Quang Tri</td><td>wind</td><td>50.0</td><td>—</td><td>110kV</td><td>central</td><td>prospective</td></tr>
          </tbody>
        </table>
        """,
        "LIMITATIONS_ALTERNATIVES": """
        <ul>
          <li><strong>RISK-01-01:</strong> Indicative strike prices are not calibrated — labeled <code>indicative_staging</code> in each <code>_meta</code> block.</li>
          <li>Seed projects carry capacity metadata only; <code>generation_profile_path</code> is <code>null</code>.
            PHASE-02 physical-fit will estimate from capacity-vs-demand ratios and degrade gracefully when profiles are absent.</li>
          <li><strong>ALT-001:</strong> A SQLite catalog was rejected in favor of version-controlled JSON, consistent with the repo pattern.</li>
        </ul>
        """,
        "ERRORS_WARNINGS_FLAGS": """
        <p>No errors. 10/10 PHASE-01 tests pass. Full regression on cleanly-collecting Python tests: 185 passed.</p>
        <p><em>Note (pre-existing, unrelated):</em> several integration tests import CLI scripts that call
        <code>argparse.parse_args()</code> at import time, aborting a whole-suite <code>pytest</code> collection.
        This is environmental and predates GAP-03; affected files were run via the project's test runner, not bare pytest.</p>
        """,
        "OPEN_QUESTIONS": """
        <ul>
          <li><strong>Q-001 (resolved default):</strong> seed data is metadata-only; profiles optional via <code>generation_profile_path</code>.</li>
          <li>Should saigon18 / north_thuan get real 8760 generation profiles extracted from solved REopt results to sharpen physical-fit? Deferred — capacity estimation suffices for the demo.</li>
        </ul>
        """,
    }


PHASES = {"phase-01": phase_01_sections}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a GAP-03 phase HTML report.")
    parser.add_argument("phase", choices=sorted(PHASES), help="phase label, e.g. phase-01")
    parser.add_argument("--date", default="2026-05-29")
    args = parser.parse_args()

    sections = PHASES[args.phase]()
    slug = f"{args.date}-gap03-{args.phase}"
    out = write_report(slug, sections)
    print(f"wrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
