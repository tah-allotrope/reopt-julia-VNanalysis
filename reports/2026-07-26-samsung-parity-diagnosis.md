# Samsung/TTC Parity Gate Diagnosis (2026-07-26)

## Context

PHASE-03 of `plans/2026-07-26-post-backlog-architecture-plan.md` requires
reproducing the Samsung/TTC parity divergence, determining whether it is
environmental (reproducible, safe to regenerate the golden) or a genuine
logical regression, and then either restoring the gate (Branch A) or
correcting the documentation to stop advertising an unenforced guarantee
(Branch B).

## Reproduction

```
PYTHONPATH= .venv/Scripts/python.exe -m pytest tests/python/analysis/test_samsung_ttc_parity.py -v -rX --runxfail
```

Result: `2 failed, 1 passed`.

- `test_samsung_parity_headline_settlement_exact` — **passes**. Deterministic
  settlement fields (`buyer_savings_vnd`, `buyer_cost_on_matched_vnd`,
  `evn_avoided_cost_on_matched_vnd`), the strike floor, and the recommended
  position all match the golden exactly.
- `test_samsung_parity_full_tree_within_bar` (xfail) — fails. First
  divergence: `/strike_sweep/negotiation_summary/buyer_saves_candidates[0]/developer_irr_fraction`:
  `0.02898076341984358` (new) vs `None` (golden).
- `test_samsung_parity_is_bit_exact` (xfail) — fails with max relative diff
  `1.1230198085530174`, at the same field family.

This matches the previously recorded symptom in `test_samsung_ttc_parity.py`'s
`xfail` reasons, which cite this exact divergence reproducing identically at
commit `fd8ceaf` (predating the webapp phase-1/phase-2 sessions) per
`plans/2026-07-22-ci-truth-correctness-sprint-plan.md` PHASE-02.

## Is the resource tracked? (TASK-03-02)

```
git ls-files data/interim/pysam_resources/
```
→ 3 tracked files (the Himawari/NSRDB PVWatts resource CSVs and the NSRDB
query-response JSON). The PVWatts resource itself is not the source of the
divergence — the run's `quality.solar_profile_source` reports `pvwatts` in
both the current run and the golden, so the same resource path is active in
both.

## Regeneration test (TASK-03-03, before committing anything)

Per MANUAL-002, the CLI was run to produce a *candidate* regenerated golden
into a scratch file (never written into `examples/`), then diffed field-by-
field against the tracked golden:

```
PYTHONPATH=src/python .venv/Scripts/python.exe -m reopt_pysam_vn.analysis offsite_dppa \
  --config scenarios/case_studies/samsung_ttc/samsung_ttc_deal_config.json \
  --extracted data/interim/samsung_ttc/samsung_ttc_extracted_inputs.json \
  --out <scratch>.json
```

Diff (15 leaf differences, all confined to `developer_*` PySAM Single-Owner
finance outputs in `strike_sweep`):

| Path | Golden | Regenerated |
|---|---|---|
| `negotiation_summary/buyer_saves_candidates[0]/developer_irr_fraction` | `None` | `0.02898...` |
| `negotiation_summary/buyer_saves_candidates[0]/developer_npv_usd` | `-80,394,514.87` | `-15,312,422.07` |
| `negotiation_summary/buyer_saves_candidates[1]/developer_irr_fraction` | `None` | `0.06332...` |
| `negotiation_summary/buyer_saves_candidates[1]/developer_npv_usd` | `-74,784,075.12` | `-9,701,982.32` |
| `sweep[0..3]/developer_irr_fraction` | `None` (×4) | numeric (×4) |
| `sweep[0..3]/developer_npv_usd` | large negative | smaller negative, same sign pattern |
| `sweep[4]/developer_passes` | `False` | `True` |

**This is more than the single documented `developer_irr_fraction`
None-vs-numeric field.** `developer_npv_usd` also moves substantially (not a
rounding-level shift — e.g. candidate 0 moves from -$80.4M to -$15.3M, a
~5x change in magnitude), and one candidate's pass/fail verdict
(`developer_passes`) flips from `False` to `True`. The prior investigation's
xfail reasons describe the divergence as a single field; the actual surface
is the entire PySAM Single-Owner developer-finance block for every swept
strike price.

## Root cause assessment

The deterministic settlement math (buyer-side, EVN-avoided-cost, strike
banding) is exact — confirming the offsite-DPPA settlement engine itself has
not drifted. The divergence is isolated to the PySAM Single-Owner developer
finance run invoked via `run_single_owner_model` (`dppa_samsung_ttc.py:823`).
Because this driven by the installed `nrel-pysam` package's internal SAM
financial-model implementation (not repo code), and reproduces identically
across commits predating this work, the most likely explanation is that the
golden was captured against a different `nrel-pysam` release (or PySAM was
unavailable at golden-capture time in a way that still populated a stale/
partial `outputs` dict with an NPV number but no IRR) than the `nrel-pysam
==7.1.0` pin now installed. Confirming the exact historical PySAM version is
not possible from repo state alone — no `pip freeze` snapshot from the golden's
generation date is tracked.

## Decision: Branch B (honest documentation)

Per RISK-03-01 / MANUAL-002: "If more than the known `developer_irr_fraction`
field changes, stop and take Branch B." The NPV and pass/fail movement shown
above is exactly that condition. Regenerating the golden here would risk
laundering a genuine PySAM-version-driven change into the baseline without a
verified explanation, and CON-001 requires the golden not be edited casually.

**Action taken:** `tests/python/analysis/test_samsung_ttc_parity.py` is left
unchanged (`golden_machine` marker and both `xfail` decorators retained).
`README.md` and `docs/onsite_vs_offsite.md` are corrected so neither claims an
enforced "parity-gated bit-for-bit" guarantee; both now state plainly that the
check is a local-only diagnostic, CI-excluded and currently `xfail`, pointing
here for the evidence. `docs/testing.md` gains a "What CI actually runs"
section, and `docs/architecture.md`'s Layer 3 equivalence claim is qualified
as manually-verified, not automated.

## Follow-up (out of scope for this plan)

Pin and record the exact `nrel-pysam` version used to generate
`examples/samsung-ttc_combined-decision.example.json`, or re-baseline the
golden in a dedicated, reviewed commit once the PySAM-version cause is
confirmed rather than assumed.
