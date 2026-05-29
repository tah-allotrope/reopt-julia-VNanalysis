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


def phase_02_sections() -> dict[str, str]:
    return {
        "PHASE_NAME": "GAP-03 PHASE-02 — Multi-Dimensional Matching Engine",
        "PROJECT": PROJECT_NAME,
        "DATE": "2026-05-29",
        "REPO": REPO_NAME,
        "INPUT_OUTPUT_CONTENT": """
        <p><strong>Inputs:</strong> a <code>FactoryProfile</code> (region, annual consumption, peak demand,
        voltage, optional 8760 loads, EVN baseline, and an optional co-located project id) plus the
        PHASE-01 project catalog.</p>
        <p><strong>Outputs:</strong></p>
        <ul>
          <li><code>src/python/reopt_pysam_vn/integration/matching.py</code> —
            <code>match_projects_to_factory()</code>, <code>score_project()</code>,
            <code>FactoryProfile</code>, <code>ProjectMatch</code>, <code>physical_fit_from_profile()</code>,
            <code>estimate_annual_generation_kwh()</code>.</li>
          <li>A ranked <code>list[ProjectMatch]</code>: per-dimension scores, overall score,
            human-readable <code>fit_explanation</code>, and <code>flags</code> (WARN / BLOCKER),
            with an <code>is_viable</code> property.</li>
          <li><code>tests/python/integration/test_matching.py</code> — 11 tests (Red/Green TDD).</li>
        </ul>
        """,
        "MERMAID_DIAGRAM": """flowchart TD
  F[FactoryProfile] --> M[match_projects_to_factory]
  C[ProjectRecord catalog] --> M
  M --> S[score_project per project]
  S --> D1[physical]
  S --> D2[geographic]
  S --> D3[capacity]
  S --> D4[commercial]
  S --> D5[regulatory]
  D1 --> O[overall = mean of 5]
  D2 --> O
  D3 --> O
  D4 --> O
  D5 --> O
  O --> R[ranked list&#91;ProjectMatch&#93;]""",
        "MATH_ALGORITHM_SECTION": """
        <p>Five equally-weighted dimensions (20% each); overall is their weighted mean.</p>
        <ul>
          <li><strong>Physical:</strong> with a generation profile, solar-absorption ratio
            <code>&Sigma; min(load+BESS, gen) / &Sigma; gen</code>. Without one, a capacity estimate:
            <code>0.45&middot;adequacy(cap/peak) + 0.35&middot;tech_coincidence + 0.20&middot;BESS_firming</code>,
            where adequacy is triangular (1.0 for cap/peak &isin; [0.8, 1.5]).</li>
          <li><strong>Geographic:</strong> onsite &rarr; 100 if co-located else 0 (BLOCKER);
            offsite &rarr; same region 100, adjacent 70, cross-country 40.</li>
          <li><strong>Capacity:</strong> annual generation / annual consumption — 100 in the [0.3, 0.7]
            DPPA sweet spot, degrading outward; ratio &lt; 0.1 or &gt; 3.0 is a BLOCKER.</li>
          <li><strong>Commercial:</strong> <code>50 + 250&middot;(baseline&minus;strike)/baseline</code>,
            clamped; missing strike &rarr; neutral 50.</li>
          <li><strong>Regulatory:</strong> private-wire requires co-location (else BLOCKER);
            Decree 57 export-cap headroom deduction when onsite capacity &gt; 1.6&times; peak;
            light 110kV-vs-low-voltage compatibility check.</li>
        </ul>
        <p>Annual generation is estimated from nameplate via Vietnam capacity factors
        (solar {sf}, wind {wf}), using explicit <code>solar_mw</code>/<code>wind_mw</code> splits when present.</p>
        <p><code>is_viable</code> = no BLOCKER flag <em>and</em> overall &ge; {vm}.</p>
        """.format(sf=0.18, wf=0.32, vm=50),
        "TOOLS_METHODS": """
        <ul>
          <li>Pure-Python heuristic scoring — no Julia solve, deterministic and fast.</li>
          <li>Physical-fit profile path mirrors <code>rank_case_study_offtakers.py</code>'s absorption proxy.</li>
          <li>pytest Red/Green TDD; controlled <code>FactoryProfile</code> fixtures grounded in real
            case-study magnitudes (Saigon18 ~30 MW peak / ~184 GWh annual).</li>
        </ul>
        """,
        "CHARTS_SECTION": """
        <p>Illustrative ranking for the Saigon18 factory (south, co-located with the onsite project):</p>
        <table>
          <thead><tr><th>Rank</th><th>Project</th><th>Physical</th><th>Geo</th><th>Capacity</th><th>Commercial</th><th>Regulatory</th><th>Overall</th></tr></thead>
          <tbody>
            <tr><td>1</td><td>Saigon18 onsite solar+BESS</td><td>~91</td><td>100</td><td>100</td><td>~63</td><td>~80</td><td><strong>~87</strong></td></tr>
            <tr><td>2</td><td>North Thuan hybrid+BESS</td><td>~71</td><td>70</td><td>~100</td><td>~47</td><td>100</td><td>~78</td></tr>
            <tr><td>3</td><td>Ninh Sim solar+wind</td><td>~61</td><td>70</td><td>~96</td><td>~40</td><td>100</td><td>~73</td></tr>
            <tr><td>—</td><td>Binh Duong onsite (not co-located)</td><td>—</td><td>0</td><td>—</td><td>—</td><td>10</td><td>BLOCKER</td></tr>
          </tbody>
        </table>
        <p>The co-located onsite solar+BESS project wins physical fit and overall, exactly as the
        demo narrative requires; the other onsite project is correctly blocked.</p>
        """,
        "LIMITATIONS_ALTERNATIVES": """
        <ul>
          <li><strong>RISK-02-01:</strong> dimension weights are subjective; defaults are equal (20% each) and documented in <code>DEFAULT_WEIGHTS</code>.</li>
          <li>Capacity-only physical fit is an estimate; supplying 8760 generation profiles activates the precise absorption path.</li>
          <li>Annual generation uses fixed capacity factors, not site-specific weather — adequate for screening, not bankable.</li>
        </ul>
        """,
        "ERRORS_WARNINGS_FLAGS": """
        <p>No errors. 11/11 PHASE-02 tests pass (21/21 with PHASE-01); 196 passed across the cleanly-collecting suite.</p>
        <p>During TDD the no-viable edge case surfaced a real gap: a 50 MW project scored ~55 against a
        0.5 MW factory. Fixed by promoting extreme capacity mismatch (ratio &lt; 0.1 or &gt; 3.0) from a
        WARN to a BLOCKER, so wildly mis-sized projects are no longer flagged viable.</p>
        """,
        "OPEN_QUESTIONS": """
        <ul>
          <li>Co-location is modeled via <code>FactoryProfile.colocated_project_id</code>. A future
            site-data service (research Idea 1) could resolve this automatically from coordinates.</li>
          <li>Should weights be tunable per client segment? Left as a constructor parameter for now.</li>
        </ul>
        """,
    }


PHASES = {"phase-01": phase_01_sections, "phase-02": phase_02_sections}


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
