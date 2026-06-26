"""Synthesize a deck report markdown from the orchestrator's results JSON.

Reads ``reports/ceba_dppa_2026_repo_check.json`` (default CEBA path) or
``reports/dppa_july_2026_repo_check.json`` (``--deck july``) and writes a
colleague-readable markdown report with:
- header counts (✅/⚠️/ℹ️/❌/➖/🔧)
- bucket-grouped verdict table (slide, claim, deck, repo, delta, verdict)
- structural reconciliations section (kpp collapse, PySAM null IRR, etc.)
- known-gaps section (CEBA only; July has none)

Usage (from repo root):
    .venv\\Scripts\\python.exe scripts/python/integration/ceba_deck/synthesize_md_report.py
    .venv\\Scripts\\python.exe scripts/python/integration/ceba_deck/synthesize_md_report.py --deck july
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_PYTHON = REPO_ROOT / "scripts" / "python"
if str(SCRIPTS_PYTHON) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PYTHON))
from integration.ceba_deck.deck_config import get_deck  # noqa: E402

VERDICT_ICON = {
    "ok": "✅",
    "warn": "⚠️",
    "info": "ℹ️",
    "bad": "❌",
    "skip": "➖",
    "err": "💥",
    "calibrated": "🔧",
}
VERDICT_HEADING = {
    "ok": "OK (match within ±1%)",
    "warn": "Reconcile (deck-cited, repo differs)",
    "info": "Qualitative / method-level (DEC-007)",
    "bad": "Mismatch (> 5% delta)",
    "skip": "Out of scope / no equivalent",
    "err": "Runner error",
    "calibrated": "Calibrated (deck value was the solver's target)",
}
BUCKET_HEADING = {
    "A": "Bucket A — Assumption checks (data file values vs deck-cited values)",
    "B": "Bucket B — Finding checks (deck-stated numbers reproducible by the engine)",
    "C": "Bucket C — Insight checks (qualitative statements the engine demonstrates)",
}


def _md_value(v: Any) -> str:
    if v is None:
        return "_(none)_"
    if isinstance(v, float):
        if abs(v) < 0.01:
            return f"{v:.2e}"
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, list):
        if len(v) > 8:
            return f"[…{len(v)} items…]"
        return "[" + ", ".join(_md_value(x) for x in v) + "]"
    if isinstance(v, str):
        return v if len(v) < 60 else v[:57] + "…"
    return str(v)


def _table_row(check: dict) -> str:
    icon = VERDICT_ICON.get(check["verdict"], "?")
    delta = check.get("delta_pct")
    delta_str = "—" if delta is None else f"{delta:+.2%}"
    return (
        f"| {check['slide']} "
        f"| {icon} "
        f"| {check['id']} "
        f"| {_md_value(check['deck_value'])} {check['deck_unit']} "
        f"| {_md_value(check['repo_value'])} "
        f"| {delta_str} "
        f"| {check.get('takeaway') or ''} |"
    )


def _bucket_table(checks: list[dict]) -> list[str]:
    lines = [
        "| Slide | Verdict | Check id | Deck value | Repo value | Δ% | Takeaway |",
        "|---:|:---:|---|---:|---:|---:|---|",
    ]
    for c in checks:
        lines.append(_table_row(c))
    return lines


def _summary_block(summary: dict) -> list[str]:
    icon = VERDICT_ICON
    total = sum(summary.values())
    lines = [
        "## Verdict counts",
        "",
        "| Verdict | Count | Share |",
        "|---|---:|---:|",
    ]
    for v in ("ok", "warn", "info", "bad", "skip", "err"):
        n = summary.get(v, 0)
        pct = (n / total * 100.0) if total else 0.0
        lines.append(f"| {icon[v]} {VERDICT_HEADING[v]} | {n} | {pct:.0f}% |")
    lines.append(f"| **Total** | **{total}** | 100% |")
    lines.append("")
    return lines


def _structural_section(checks: list[dict]) -> list[str]:
    """Call out structural reconciliations — items that look like deltas but
    are really different model formulations."""
    lines = ["## Structural reconciliations", ""]
    items = [
        ("A04 — DPPA fees: deck 360 + 163.3 = 523.3 ≈ repo dppa_adder 523.34 ✅",
         "The deck splits fixed DPPA fees into service (C_dppa_dv = 360) and "
         "balancing (P_cl = 163.3) for a combined 523.3 VND/kWh (slides 9, 11, "
         "13, 30, 37, 175, 356). The repo's settlement engine takes one combined "
         "input: ``ContractParams.dppa_adder_vnd_kwh = 523.34`` "
         "([settlement.py:26](src/python/reopt_pysam_vn/integration/settlement.py:26)). "
         "Match within 0.04 VND/kWh. This is the headline reconciliation."),
        ("A06 / A07 — k × K_pp collapse (DEC-008 cited reconcile)",
         "Deck splits FMP→delivery conversion into k=1.026 and K_pp=1.008 "
         "(product 1.03421), cited as 'EAVCED public training' (slide 11). The "
         "engine collapses both into a single kpp_factor=1.02726 "
         "(kpp_pct=2.7263). The ~0.7% delta is a structural modeling choice. "
         "Marked ⚠️ reconcile (DEC-008) rather than ❌ because the deck cites a "
         "source for the lower kpp_factor product."),
        ("A02 — TOU peak/normal ratio (1.80 vs 1.826)",
         "Deck Slide 5 voltage table: peak 0.126 / normal 0.070 = 1.80 (peak/normal). "
         "Repo: peak 1.57 / standard 0.86 = 1.826 (peak/normal). Both express "
         "the peak-vs-standard multiplier; the 1.5% delta is a small structural gap."),
        ("A12 — FMP cited 1,426.6 vs repo deal-defaults center 1,700",
         "Deck cites FMP avg 1,426.6 VND/kWh (EAVCED public training). Repo "
         "deal-defaults sensitivity range is 1,400-2,000 with a center of 1,700. "
         "Per DEC-008, the deck value is marked ⚠️ reconcile with both bases "
         "shown. The repo value is a forward-looking sensitivity midpoint, "
         "not an observed 2025 monthly FMP — there is no repo data file that "
         "holds an observed 2025 average."),
        ("A15 — equity IRR target (range consistency, not value match)",
         "Deck Slide 19 lists the equity IRR target as a range 12-15%+; the "
         "engine's ``target_irr_fraction`` is a single tunable default of 0.15. "
         "A value comparison is meaningless (a tunable knob is not "
         "authoritative), so the check is a range-consistency check: the "
         "engine's default 0.15 falls within the deck's range 0.12-0.15+. ✅"),
        ("B11 / B13 / B12 / B14 — Case 5/6 PySAM: DEC-007 method+directional",
         "The deck's Case 5 / Case 6 numbers (16.9% / 26.9% seller equity IRR, "
         "1.14× / 1.50× min DSCR) cannot be exactly reproduced from disclosed "
         "inputs. PySAM with proxy CAPEX does not produce a financeable project "
         "at the deck's stated strike 2,000 VND/kWh. Per DEC-007 the verdict "
         "is method+directional only and is never forced to ❌ even when the "
         "numeric delta is large. Colleague review should ask the deck author "
         "to disclose the inputs that close the gap."),
        ("C04 — oversized BESS dips DSCR (DEC-007 directional)",
         "C04 is now a directional comparison: run two PySAM scenarios (lean "
         "BESS vs oversized BESS with $1.2M replacement shock) and check that "
         "oversized BESS has a lower min DSCR than lean BESS. The deck's "
         "specific 1.14× value is not reproducible with the proxy CAPEX — the "
         "verdict reports the directional relationship only."),
        ("C05 — bankability floor (real strike sweep, not single PySAM call)",
         "C05 now runs the repo's actual ``sweep_strike_prices`` "
         "([integration/strike_search.py:44](src/python/reopt_pysam_vn/integration/strike_search.py:44)) "
         "across 5-15 USc/kWh to find the min strike clearing a 15% seller "
         "IRR. The deck's Lesson 2 ('a strike below the bankability floor "
         "means no project') is verified as a method+direction; the exact "
         "floor value is not authoritative with proxy CAPEX."),
    ]
    for title, body in items:
        lines.append(f"### {title}")
        lines.append("")
        lines.append(body)
        lines.append("")
    return lines


def _known_gaps_section(known_gaps: list[dict]) -> list[str]:
    lines = ["## Known gaps (out of repo scope)", ""]
    lines.append("These slides are relevant to the deck's thesis but intentionally out of "
                 "scope for the repo. They get a `➖ out of repo scope` note in the deck "
                 "(DEC-006) but no quantitative check.")
    lines.append("")
    for g in known_gaps:
        lines.append(f"### {g['id']} — Slide {g['slide']}: {g['topic']}")
        lines.append("")
        lines.append(g["note"])
        lines.append("")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deck",
        choices=("ceba", "july"),
        default="ceba",
        help="Which deck to render (default: ceba).",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=None,
        help="Override the input results JSON path.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Override the output markdown path.",
    )
    args = parser.parse_args(argv)

    config = get_deck(args.deck)
    results_path = args.results or config.results_json
    out_path = args.out or config.report_md

    if not results_path.exists():
        print(f"results JSON not found: {results_path}", file=sys.stderr)
        return 1
    data = json.loads(results_path.read_text(encoding="utf-8"))
    metadata = data["metadata"]
    summary = data["summary"]
    checks = data["checks"]
    known_gaps = data.get("known_gaps", [])

    out: list[str] = []
    out += [
        f"# {config.deck_title} — Repo verification report",
        "",
        f"_Generated {metadata['generated_at_utc']} from "
        f"`{Path(metadata['deck']).name}`_",
        "",
        f"- **Plan:** `{metadata['plan']}`",
        f"- **Registry size:** {metadata['registry_size']}",
        f"- **Executed:** {metadata['executed']}",
        f"- **Errors:** {len(metadata['errors'])}",
        "",
    ]
    out += _summary_block(summary)

    out += ["## Per-bucket verdict tables", ""]
    by_bucket: dict[str, list[dict]] = {"A": [], "B": [], "C": []}
    for c in checks:
        by_bucket.setdefault(c["bucket"], []).append(c)
    for bucket in ("A", "B", "C"):
        if not by_bucket[bucket]:
            continue
        out += [f"### {BUCKET_HEADING[bucket]}", ""]
        out += _bucket_table(by_bucket[bucket])
        out.append("")

    if known_gaps:
        out += _structural_section(checks)
        out += _known_gaps_section(known_gaps)
    else:
        # July deck: no known_gaps list; emit a slim structural note instead.
        out += [
            "## Structural reconciliations",
            "",
            "The July deck has no `KNOWN_GAPS` out-of-scope topics; every slide is "
            "either covered by a check (A/B/C) or by the calibration ledger. "
            "The structural reconciliations live in `reports/dppa_july_2026_repo_check.md` "
            "(generated by this script) and in the calibration ledger at "
            "`reports/dppa_july_2026_calibration.json`.",
            "",
        ]

    out += [
        "## Methodology notes",
        "",
        "- **A-bucket** = data file values vs deck-cited values; computed via "
        "JSON path traversal of `data/vietnam/vn_*.json`.",
        "- **B-bucket** = deck-stated numbers reproducible by the engine; "
        "computed via the `reopt_pysam_vn.integration.settlement` module "
        "(flat-profile scenario helpers) and `reopt_pysam_vn.pysam.single_owner` "
        "for the developer-economics checks.",
        "- **C-bucket** = qualitative statements the engine demonstrates "
        "(over-contracting caps, load-shape overlap, year-1 vs BAU crossover, "
        "BESS-DSCR dip, bankability floor, daytime vs night economics).",
        "- **Verdict rule (DEC-004)**: ±1% → ✅ match; 1-5% → ℹ️ info; > 5% → ❌ bad. "
        "Citation-preserving (DEC-008): if the deck cites a source and the gap "
        "is > 1%, mark ⚠️ reconcile with both bases shown.",
        "- **PySAM null IRR (DEC-007)**: when PySAM returns null IRR, the verdict "
        "is ℹ️ info with an explicit \"project does not cashflow under deck "
        "inputs\" note — the deck's exact figures require undisclosed assumptions.",
        "- **Calibrated tier (DEC-001, DEC-004, DEC-007)**: 🔧 `calibrated` is reserved "
        "for checks where the deck's numeric target was the solver's objective "
        "(e.g. Case 5/6 seller IRR in the July deck — back-solved CAPEX). The "
        "model hits the deck value by construction; the verdict records that "
        "fact, not a numeric comparison. Independent checks (the other Case 5/6 "
        "metrics, the sweep) get the standard ±1% / 1-5% / >5% verdict.",
        "",
        "## Re-run",
        "",
        "```",
        "$env:PYTHONIOENCODING='utf-8'",
        "$env:PYTHONPATH='src/python;scripts/python'",
        f".venv\\Scripts\\python.exe scripts\\python\\integration\\verify_ceba_dppa_deck.py --deck {config.key}",
        f".venv\\Scripts\\python.exe scripts\\python\\integration\\ceba_deck\\synthesize_md_report.py --deck {config.key}",
        "```",
        "",
        f"Artifact: `{out_path.relative_to(REPO_ROOT)}`",
        "",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote {out_path.relative_to(REPO_ROOT)} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
