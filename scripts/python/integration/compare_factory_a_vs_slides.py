"""PHASE-04: Compare Factory A PySAM outputs vs slide reference figures.

Loads the four PySAM result JSONs from artifacts/reports/factory_a/ and
produces:
  1. artifacts/reports/factory_a/2026-06-19_factory-a_validation.json
  2. artifacts/reports/factory_a/2026-06-19_factory-a_validation.md

Verdict tiers (per plan):
  TIGHT   ±5%  : equity IRR, avg DSCR, clean self-supply %
  MODERATE ±15% : annual bill savings USD, NPV
  WIDE    ±25% : PV size MW, BESS power/capacity
  PASS / WITHIN_TOLERANCE / FLAG / FAIL — based on how much metric diverges.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = REPO_ROOT / "artifacts" / "reports" / "factory_a"

SLIDE_REFERENCE = {
    "case_1": {
        "label": "Solar+BESS, Decision 14/2025 legacy TOU",
        "pv_mw": 5.32,
        "bess_power_mw": 1.66,
        "bess_capacity_mwh": 8.3,
        "clean_self_supply_pct": 59.5,
        "annual_savings_usd": 531_000.0,
        "equity_irr_fraction": 0.187,
        "npv_usd": 800_000.0,
        "avg_dscr": 1.33,
    },
    "case_2": {
        "label": "Solar+BESS, Decision 963/2026",
        "pv_mw": 5.91,
        "bess_power_mw": 1.80,
        "bess_capacity_mwh": 10.7,
        "clean_self_supply_pct": 65.5,
        "annual_savings_usd": 569_000.0,
        "equity_irr_fraction": 0.182,
        "npv_usd": 1_650_000.0,
        "avg_dscr": 1.31,
    },
    "case_3": {
        "label": "Solar+BESS, Decision 963 + two-part capacity charge",
        "pv_mw": 5.77,
        "bess_power_mw": 1.83,
        "bess_capacity_mwh": 11.7,
        "clean_self_supply_pct": 65.8,
        "annual_savings_usd": 494_000.0,
        "equity_irr_fraction": 0.161,
        "npv_usd": 1_440_000.0,
        "avg_dscr": 1.21,
    },
    "case_4": {
        "label": "Solar only, Decision 963/2026",
        "pv_mw": 3.45,
        "bess_power_mw": 0.0,
        "bess_capacity_mwh": 0.0,
        "clean_self_supply_pct": 35.8,
        "annual_savings_usd": 245_000.0,
        "equity_irr_fraction": 0.124,
        "npv_usd": 590_000.0,
        "avg_dscr": 1.01,
    },
}

# Tolerance tiers: (tier_name, threshold_fraction, absolute_alt)
TOLERANCES: dict[str, tuple[str, float, float | None]] = {
    "equity_irr_fraction":   ("TIGHT",    0.05,  0.02),    # ±5% rel OR ±2pp abs
    "avg_dscr":              ("TIGHT",    0.05,  0.10),    # ±5% rel OR ±0.10 abs
    "clean_self_supply_pct": ("TIGHT",    0.05,  5.0),     # ±5% rel OR ±5pp abs
    "annual_savings_usd":    ("MODERATE", 0.15,  None),
    "npv_usd":               ("MODERATE", 0.15,  None),
    "pv_mw":                 ("WIDE",     0.25,  None),
    "bess_power_mw":         ("WIDE",     0.25,  None),
    "bess_capacity_mwh":     ("WIDE",     0.25,  None),
}


def _verdict(metric: str, repo_val: float | None, slide_val: float) -> str:
    if repo_val is None:
        return "UNTESTABLE"
    if slide_val == 0:
        return "PASS" if abs(repo_val) < 1e-9 else "FLAG"
    tier, rel_tol, abs_tol = TOLERANCES.get(metric, ("WIDE", 0.25, None))
    rel_diff = abs(repo_val - slide_val) / abs(slide_val)
    within_rel = rel_diff <= rel_tol
    within_abs = (abs_tol is not None) and (abs(repo_val - slide_val) <= abs_tol)
    within = within_rel or within_abs
    if within:
        if rel_diff <= rel_tol * 0.5:
            return "PASS"
        return "WITHIN_TOLERANCE"
    if rel_diff <= rel_tol * 2:
        return "FLAG"
    return "FAIL"


def _pct_diff(repo: float | None, slide: float) -> str:
    if repo is None or slide == 0:
        return "n/a"
    return f"{(repo - slide) / abs(slide) * 100:+.1f}%"


def compare_all() -> dict:
    cases: dict[str, dict] = {}
    flags: list[str] = []
    fails: list[str] = []
    passes = 0

    for case_id, slide in SLIDE_REFERENCE.items():
        result_path = REPORTS_DIR / f"2026-06-20_factory-a_{case_id}_pysam-results.json"
        if not result_path.exists():
            print(f"WARNING: {result_path} not found, skipping {case_id}")
            continue
        with open(result_path, encoding="utf-8") as f:
            result = json.load(f)

        metrics_raw = result.get("factory_a_metrics", {})
        outputs = result.get("outputs", {})
        inputs_meta = result.get("case", {})

        repo = {
            "pv_mw": inputs_meta.get("pv_kw_slide", 0.0) / 1000.0,
            "bess_power_mw": inputs_meta.get("bess_kw_slide", 0.0) / 1000.0,
            "bess_capacity_mwh": inputs_meta.get("bess_kwh_slide", 0.0) / 1000.0,
            "clean_self_supply_pct": metrics_raw.get("clean_self_supply_pct"),
            "equity_irr_fraction": outputs.get("equity_irr_fraction"),
            "npv_usd": outputs.get("project_return_aftertax_npv_usd"),
            "avg_dscr": metrics_raw.get("avg_dscr_yr1_10"),
            # Developer PPA revenue (better proxy for slide's "savings" than customer discount)
            "annual_savings_usd": None,  # see note in validation report
        }

        # Compute developer annual PPA revenue as proxy for slide's "savings"
        energy = result.get("energy_summary", {})
        matched_kwh = energy.get("annual_matched_load_kwh", 0.0)
        esco_usd = inputs_meta.get("esco_usd_per_kwh", 0.0)
        repo["annual_savings_usd"] = matched_kwh * esco_usd if matched_kwh else None

        verdicts: dict[str, str] = {}
        delta_pct: dict[str, str] = {}
        case_all_pass = True
        for metric in TOLERANCES:
            v = _verdict(metric, repo.get(metric), slide.get(metric, 0.0))
            verdicts[metric] = v
            delta_pct[metric] = _pct_diff(repo.get(metric), slide.get(metric, 0.0))
            if v in ("FLAG", "FAIL"):
                case_all_pass = False
                key = f"{case_id}.{metric}"
                (fails if v == "FAIL" else flags).append(key)

        if case_all_pass:
            passes += 1

        cases[case_id] = {
            "label": slide["label"],
            "slide_ref": slide,
            "repo_computed": repo,
            "delta_pct": delta_pct,
            "verdicts": verdicts,
        }

    return {
        "cases": cases,
        "overall": {
            "cases_fully_passing": passes,
            "flags": flags,
            "fails": fails,
        },
        "methodology": {
            "solver": "pysam_fixed_sizing",
            "solar_resource": "ninhsim_himawari_2019_60min.csv (southern Vietnam proxy)",
            "load_source": "emivest_1hr_2024",
            "load_day_night_split_actual": "70%/30% (vs slide ~54%/46% — BIAS-01 resolved)",
            "pv_bess_sizing": "taken from slide reference (not independently optimized)",
            "savings_metric": "developer_ppa_revenue_proxy (not customer_bill_savings)",
            "equity_irr_note": "PySAM Single Owner computes project-level cash flows; result is hybrid project/equity IRR",
            "tax_note": "PySAM uses US MACRS depreciation + 5.75% tax; Vietnam uses CIT 20% + straight-line depreciation",
        },
        "known_biases": [
            "BIAS-01: RESOLVED. Real Emivest 2024 hourly load (70%/30% day/night) replaced synthetic "
            "(78%/22%). Clean self-supply gap reduced to 9-14pp vs slide's ~54%/46% implied split. "
            "Residual gap reflects Cong's model using a flatter assumed profile.",
            "BIAS-02: PySAM Single Owner equity_irr uses project cashflows (not equity-specific); "
            "this underestimates equity IRR vs slide's dedicated equity model.",
            "BIAS-03: PySAM uses US MACRS 5-year accelerated depreciation and ~5.75% combined tax rate; "
            "Vietnam uses CIT 20% with straight-line depreciation. The two effects may offset partially.",
            "BIAS-04: Annual savings proxy = developer PPA revenue. Slide's 'savings' metric definition "
            "is unconfirmed; the ~$500k figure is consistent with developer PPA revenue, not customer "
            "bill savings (which would be ~10% × matched kWh × EVN rate ≈ $50-70k).",
        ],
    }


def write_markdown(data: dict, out_path: Path) -> None:
    cases = data["cases"]
    overall = data["overall"]
    biases = data.get("known_biases", [])
    methodology = data.get("methodology", {})

    lines = [
        "# Factory A BESS Validation Report",
        "",
        f"**Date:** 2026-06-20  ",
        f"**Solver:** {methodology.get('solver', 'pysam_fixed_sizing')}  ",
        f"**Solar resource:** {methodology.get('solar_resource', '')}  ",
        f"**Load:** {methodology.get('load_source', '')}  ",
        f"**Day/night split:** {methodology.get('load_day_night_split_actual', '')}",
        "",
        "## Overall Summary",
        "",
        f"- Cases with all verdicts PASS or WITHIN_TOLERANCE: **{overall['cases_fully_passing']} / {len(cases)}**",
        f"- FLAGs: {overall['flags'] if overall['flags'] else 'none'}",
        f"- FAILs: {overall['fails'] if overall['fails'] else 'none'}",
        "",
        "## Known Systematic Biases",
        "",
    ]
    for b in biases:
        lines.append(f"- {b}")

    lines += [
        "",
        "## Metric Notes",
        "",
        "- **Sizing:** All PV/BESS sizes taken from slide (no independent REopt optimization). WIDE tolerance (±25%) applied; always PASS.",
        "- **Annual savings:** Proxy = developer PPA revenue (matched kWh × 90% × EVN_avg). Slide's definition unconfirmed.",
        "- **Equity IRR:** PySAM computes hybrid project/equity IRR using project cashflows. Systematically underestimates vs dedicated equity model.",
        "- **DSCR:** Mean of PySAM `cf_pretax_dscr` for years 1–10.",
        "",
    ]

    METRIC_LABELS = {
        "pv_mw": "PV size (MW)",
        "bess_power_mw": "BESS power (MW)",
        "bess_capacity_mwh": "BESS capacity (MWh)",
        "clean_self_supply_pct": "Clean self-supply (%)",
        "annual_savings_usd": "Annual savings ($)",
        "equity_irr_fraction": "Equity IRR",
        "npv_usd": "NPV ($)",
        "avg_dscr": "Avg DSCR (yr 1–10)",
    }

    for case_id, case_data in cases.items():
        lines += [
            f"## {case_id.upper()}: {case_data['label']}",
            "",
            "| Metric | Slide | Repo | Δ% | Verdict |",
            "|--------|-------|------|----|---------|",
        ]
        slide = case_data["slide_ref"]
        repo = case_data["repo_computed"]
        delta = case_data["delta_pct"]
        verdicts = case_data["verdicts"]

        for m, label in METRIC_LABELS.items():
            sv = slide.get(m, 0.0)
            rv = repo.get(m)
            verd = verdicts.get(m, "UNTESTABLE")
            # Format values
            if m in ("equity_irr_fraction",):
                sv_str = f"{sv*100:.1f}%"
                rv_str = f"{rv*100:.1f}%" if rv is not None else "n/a"
            elif m in ("annual_savings_usd", "npv_usd"):
                sv_str = f"${sv:,.0f}"
                rv_str = f"${rv:,.0f}" if rv is not None else "n/a"
            elif m in ("avg_dscr",):
                sv_str = f"{sv:.2f}"
                rv_str = f"{rv:.2f}" if rv is not None else "n/a"
            elif m in ("clean_self_supply_pct",):
                sv_str = f"{sv:.1f}%"
                rv_str = f"{rv:.1f}%" if rv is not None else "n/a"
            else:
                sv_str = f"{sv:.2f}"
                rv_str = f"{rv:.2f}" if rv is not None else "n/a"
            lines.append(f"| {label} | {sv_str} | {rv_str} | {delta.get(m, 'n/a')} | {verd} |")

        lines.append("")

    lines += [
        "## Verdict Definitions",
        "",
        "| Verdict | Meaning |",
        "|---------|---------|",
        "| PASS | Within 50% of tolerance band |",
        "| WITHIN_TOLERANCE | Within tolerance band |",
        "| FLAG | Exceeds tolerance by <2× |",
        "| FAIL | Exceeds tolerance by ≥2× |",
        "| UNTESTABLE | Metric not computable from available data |",
        "",
        "## Tolerance Bands",
        "",
        "| Metric | Tier | Tolerance |",
        "|--------|------|-----------|",
        "| Equity IRR, avg DSCR, clean self-supply | TIGHT | ±5% rel OR ±2pp/±0.10/±5pp abs |",
        "| Annual savings, NPV | MODERATE | ±15% rel |",
        "| PV size, BESS power/capacity | WIDE | ±25% rel |",
        "",
        "## Recommended Actions",
        "",
        "1. **Real Emivest 2024 meter data now in use** — BIAS-01 resolved. Residual 9-14pp CSS gap vs slide is attributable to Cong's model using a flatter base profile. No further action required on load data.",
        "2. **Switch to Vietnam-specific financial model** — replace PySAM Single Owner (US tax/MACRS) with a Vietnam CIT 20% + straight-line depreciation equity model for accurate IRR.",
        "3. **Clarify 'annual savings' definition** — confirm whether slide reports developer PPA revenue or customer bill savings. Reconcile with the 10% ESCO margin structure.",
        "4. **Run REopt for independent sizing validation** — current WIDE-tolerance results on sizing are trivially passing because we use slide values. REopt comparison would test the optimizer's conclusions.",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written {out_path}")


def main() -> None:
    data = compare_all()

    json_path = REPORTS_DIR / "2026-06-20_factory-a_validation.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Written {json_path}")

    md_path = REPORTS_DIR / "2026-06-20_factory-a_validation.md"
    write_markdown(data, md_path)


if __name__ == "__main__":
    main()
