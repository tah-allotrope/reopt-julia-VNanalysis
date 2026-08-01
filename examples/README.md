# Golden Example Runs

Frozen, version-tracked reference outputs from the ReOpt + PySAM Vietnam pipeline.
They exist so a fresh clone retains representative results after the regenerable
`artifacts/` and `reports/*.html` trees were untracked from git (Sprint 1 de-bloat,
2026-06-12). These files are **golden references** — do not hand-edit them; regenerate
with the commands below if the pipeline changes.

| File | What it is | Regenerate with |
|---|---|---|
| `saigon18_scenario-a_reopt-solve.example.json` | A REopt (onsite/BTM) solve result for the Saigon18 fixed-sizing EVN-TOU scenario | `julia --project=legacy/julia --compile=min legacy/julia/scripts/run_vietnam_scenario.jl --scenario scenarios/case_studies/saigon18/2026-03-20_scenario-a_fixed-sizing_evntou.json` |
| `samsung-ttc_combined-decision.example.json` | An offsite/DPPA combined buyer+developer decision summary (Samsung-TTC) | `python scripts/python/integration/analyze_samsung_ttc_combined.py` |
| `samsung-ttc_final-report.example.html` | The client-facing final synthesis report for the Samsung-TTC DPPA analysis | `/report final plans/active/2026-06-04-samsung-ttc-dppa-economics-plan.md` (report skill, final mode) |

## Why renamed

The solve result was renamed from `*_reopt-results.json` to `*_reopt-solve.example.json`
so it is not caught by the `**/reopt-results.json` ignore rule and stays tracked here.

## Source of record

These were copied from (now git-ignored, still on disk locally):
- `artifacts/results/saigon18/2026-03-23_scenario-a_fixed-sizing_evntou_reopt-results.json`
- `artifacts/reports/samsung_ttc/2026-06-04_samsung-ttc_combined-decision.json`
- `reports/2026-06-04-final-samsung-ttc-dppa.html`
