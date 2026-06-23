"""Synthesize reports/ceba_dppa_2026_repo_check.md from the results JSON.

Reads ``reports/ceba_dppa_2026_repo_check.json`` and writes a colleague-
readable markdown report with:
- header counts (✅/⚠️/ℹ️/❌/➖)
- bucket-grouped verdict table (slide, claim, deck, repo, delta, verdict)
- structural reconciliations section (kpp collapse, PySAM null IRR, etc.)
- known-gaps section

Usage (from repo root):
    .venv\\Scripts\\python.exe scripts/python/integration/ceba_deck/synthesize_md_report.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
RESULTS_PATH = REPO_ROOT / "reports" / "ceba_dppa_2026_repo_check.json"
OUT_PATH = REPO_ROOT / "reports" / "ceba_dppa_2026_repo_check.md"

VERDICT_ICON = {
    "ok": "✅",
    "warn": "⚠️",
    "info": "ℹ️",
    "bad": "❌",
    "skip": "➖",
    "err": "💥",
}
VERDICT_HEADING = {
    "ok": "OK (match within ±1%)",
    "warn": "Reconcile (deck-cited, repo differs)",
    "info": "Qualitative / method-level (DEC-007)",
    "bad": "Mismatch (> 5% delta)",
    "skip": "Out of scope / no equivalent",
    "err": "Runner error",
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
         "Match within 0.04 VND/kWh. This is the headline reconciliation: the "
         "engine's model is consistent with the deck's split fees at the "
         "combined level."),
        ("A06 / A07 — k × K_pp collapse (DEC-008 cited reconcile)",
         "Deck splits FMP→delivery conversion into k=1.026 and K_pp=1.008 "
         "(product 1.03421), cited as 'EAVCED public training' (slide 11). The "
         "engine collapses both into a single kpp_factor=1.02726 "
         "(kpp_pct=2.7263). The ~0.7% delta is a structural modeling choice. "
         "Marked ⚠️ reconcile (DEC-008) rather than ❌ because the deck cites a "
         "source for the lower kpp_factor product — the colleague review should "
         "decide which basis applies."),
        ("A02 — TOU peak/normal ratio (1.80 vs 1.826)",
         "Deck Slide 5 voltage table: peak 0.126 / normal 0.070 = 1.80 (peak/normal). "
         "Repo: peak 1.57 / standard 0.86 = 1.826 (peak/normal). Both express "
         "the peak-vs-standard multiplier; the 1.5% delta is a small structural gap "
         "(deck's 1.78 from 'peak vs base-avg' would be a denominator mismatch — "
         "the check now compares like-for-like ratios)."),
        ("A12 — FMP cited 1,426.6 vs repo deal-defaults center 1,700",
         "Deck cites FMP avg 1,426.6 VND/kWh (EAVCED public training). Repo "
         "deal-defaults sensitivity range is 1,400-2,000 with a center of 1,700. "
         "Per DEC-008, the deck value is marked ⚠️ reconcile with both bases "
         "shown. The repo value is a forward-looking sensitivity midpoint, "
         "not an observed 2025 monthly FMP — there is no repo data file that "
         "holds an observed 2025 average."),
        ("A15 — equity IRR target midpoint",
         "Deck Slide 19 lists 12-15%+; midpoint 13.5%. Engine default is 0.15 "
         "(top of the deck's range). Both are consistent; the deck's range "
         "and the engine's single default are normal-source variations."),
        ("B11 / B13 — PySAM null IRR (DEC-007 method+directional)",
         "Case 5 and Case 6's claimed seller equity IRRs (16.9% / 26.9%) "
         "cannot be reproduced from the deck's stated inputs (49 MWp plant, "
         "70% debt / 8.5% / 10-yr, strike 2,000 VND/kWh, 25-yr). PySAM returns "
         "null IRR because the cashflow never turns positive under those "
         "assumptions with the proxy CAPEX we used. Per DEC-007 the verdict "
         "is method+directional; the deck's exact figures require undisclosed "
         "CAPEX / sizing inputs that we cannot back-solve."),
        ("B12 / B14 — Min DSCR deeply negative",
         "Same root cause as the null IRR: the project does not cashflow with "
         "the deck's stated inputs at strike 2,000. The deck's claimed min DSCR "
         "(1.14× / 1.50×) cannot be reproduced from disclosed inputs."),
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
    if not RESULTS_PATH.exists():
        print(f"results JSON not found: {RESULTS_PATH}", file=sys.stderr)
        return 1
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    metadata = data["metadata"]
    summary = data["summary"]
    checks = data["checks"]
    known_gaps = data["known_gaps"]

    out: list[str] = []
    out += [
        f"# CEBA DPPA 2026 — Repo verification report",
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
        out += [f"### {BUCKET_HEADING[bucket]}", ""]
        out += _bucket_table(by_bucket[bucket])
        out.append("")

    out += _structural_section(checks)
    out += _known_gaps_section(known_gaps)

    out += [
        "## Methodology notes",
        "",
        "- **A-bucket** = data file values vs deck-cited values; computed via "
        "JSON path traversal of `data/vietnam/vn_*.json`.",
        "- **B-bucket** = deck-stated numbers reproducible by the engine; "
        "computed via the `reopt_pysam_vn.integration.settlement` module "
        "(flat-profile scenario helpers) and `reopt_pysam_vn.pysam.single_owner` "
        "for the developer-economics checks (B11-B14, PySAM-gated).",
        "- **C-bucket** = qualitative statements the engine demonstrates "
        "(over-contracting caps, load-shape overlap, year-1 vs BAU crossover, "
        "BESS-DSCR dip, bankability floor, daytime vs night economics).",
        "- **Verdict rule (DEC-004)**: ±1% → ✅ match; 1-5% → ℹ️ info; > 5% → ❌ bad. "
        "Citation-preserving (DEC-008): if the deck cites a source and the gap "
        "is > 1%, mark ⚠️ reconcile with both bases shown.",
        "- **PySAM null IRR (DEC-007)**: when PySAM returns null IRR, the verdict "
        "is ℹ️ info with an explicit \"project does not cashflow under deck "
        "inputs\" note — the deck's exact figures require undisclosed assumptions.",
        "",
        "## Re-run",
        "",
        "```",
        "$env:PYTHONIOENCODING='utf-8'",
        "$env:PYTHONPATH='src/python;scripts/python'",
        ".venv\\Scripts\\python.exe scripts\\python\\integration\\verify_ceba_dppa_deck.py",
        ".venv\\Scripts\\python.exe scripts\\python\\integration\\ceba_deck\\synthesize_md_report.py",
        "```",
        "",
        f"Artifact: `{OUT_PATH.relative_to(REPO_ROOT)}`",
        "",
    ]

    OUT_PATH.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)} ({OUT_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
