# PHASE-01 — Parametrize the pipeline + July registry + deck text

_Generated 2026-06-26 from the in-progress plan
`plans/active/2026-06-26-dppa-july-deck-verification-plan.md`._

## Goal

Make the CEBA verification pipeline deck-agnostic and stand up a July-scoped
check registry, without disturbing the committed CEBA path.

## What shipped

- **`scripts/python/integration/ceba_deck/deck_config.py`** — new
  `DeckConfig` dataclass (`source_pptx`, `out_pptx`, `text_txt`,
  `registry_module`, `results_json`, `report_md`, `calibration_json`,
  `deck_title`) with two pre-defined configs: `CEBA_2026` (default for
  every existing entry point) and `JULY_2026`. `get_deck(name)` resolves a
  short alias (`ceba` / `july`) to the right config.
- **`scripts/python/integration/ceba_deck/july_deck_checks.py`** — new
  registry. **50 checks** across **15 slides** (4, 8, 11, 12, 15, 16, 18,
  19, 20, 22, 23, 24, 25, 26, 28). Buckets:
  - **A (16)** — tariff/TOU, fees, kpp, escalation, debt terms, CIT
    holiday, PV degradation, FMP, deal frame.
  - **B (25)** — worked example (4 checks at slides 11–12) + Case 5/6
    metrics (8+6=14) + 56-sweep gate rows (5) + Case 5/6 deal frame (1).
  - **C (9)** — over-contracting cap, three gates, BESS-DSCR dip, bankability
    floor, Y1 premium, financing structure, voltage/K_pp.
  - Includes a per-registry `JULY_CALIBRATED_CHECKS` set (14 ids, the
    Case 5/6 family) and `JULY_SWEEP_CHECKS` set (5 ids, the 56-sweep).
- **`scripts/python/integration/_extract_ceba_deck_text.py`** — now
  accepts `--deck {ceba,july}` and reads paths from `DeckConfig`; emits
  `ceba-review/dppa_july_2026_case_studies_text.txt` (15,893 chars,
  28 slides, all slide markers present).
- **`scripts/python/integration/verify_ceba_dppa_deck.py`** — refactored
  to (a) take `--deck {ceba,july}`, (b) load the registry dynamically
  via `config.registry_module`, (c) carry the deck title + per-deck
  source path in the results JSON, (d) extend the verdict set with
  `calibrated` (a 🔧 tier for solver-targeted checks; see DEC-001/004/007).
- **`scripts/python/integration/ceba_deck/synthesize_md_report.py`** —
  accepts `--deck {ceba,july}`; resolves input + output paths from
  `DeckConfig`; handles the new `calibrated` verdict; emits a
  deck-specific header. CEBA-only `KNOWN_GAPS` section is suppressed for
  the July deck (which has none).
- **`scripts/python/integration/ceba_deck/inject_repo_notes.py`** —
  accepts `--deck {ceba,july}`; paths come from `DeckConfig`; the
  `calibrated` 🔧 icon is in the per-check block. The idempotency
  delimiter (`=== [Repo check] (generated) ===`) and the byte-stability
  test (CON-003) are unchanged.
- **`scripts/python/integration/ceba_deck/test_july_deck_checks.py`** —
  new smoke test. **8 tests**, all pass:
  1. `test_registry_enumerates` — ≥ 30 checks across A/B/C.
  2. `test_every_check_has_a_slide_and_repo_fn` — every check carries
     a positive slide, non-empty `repo_fn` + `repo_source_ref` + claim.
  3. `test_unique_ids` — no duplicate check ids.
  4. `test_slides_match_extracted_text` — every slide number cited in
     the registry appears in the extracted deck text
     (`[Slide N]` marker present).
  5. `test_calibrated_set_consistent` — calibrated set ⊂ registry ids;
     sweep set ⊂ registry ids; sets are disjoint.
  6. `test_case5_case6_disclosures_present` — all 8 Case 5 + 6 Case 6
     + 5 sweep gate rows present.
  7. `test_a12_fmp_notes_anchor` — A12 records the deck-as-anchor and
     repo-as-sensitivity assumption in its `assumptions` block.
  8. `test_all_rows_helper` — `all_rows()` returns ≥ 30 rows.
- **`.gitignore`** — added `ceba-review/DPPA Presentation July 2026 Case
  Studies.pptx`, `ceba-review/*[repo-checked].pptx`,
  `ceba-review/*.idempotency-test.pptx`, `ceba-review/*[*reviewed*].pptx`,
  `ceba-review/cong bess session.pptx`, `ceba-review/CEBA DPPA 2026.pptx`
  to keep deck binaries (source + [repo-checked]) untracked per CON-002.
- **`activeContext.md`** — phase status updated; PHASE-01 marked done;
  Q-001/Q-002/Q-003 decisions recorded.

## Grill Me answers (locked 2026-06-26)

- **Q-001** — Solar sized to ~85% of factory 9,750 MWh/yr load
  (≈ 5.25 MWp at 18% CF, per the 56-sweep volume axis). Generation
  sets the matched Q_Khc, which drives both buyer-vs-BAU and developer
  CfD revenue — hence every Case 5/6 metric and the whole sweep.
- **Q-002** — "Seller equity IRR" = `project_return_aftertax_irr_fraction`
  (levered, aftertax). Calibrate CAPEX to that. "Project IRR" =
  `project_return_pretax_irr_fraction` (unlevered), consistency check
  only.
- **Q-003** — ~$160/kWh → Case 5 BESS = 7.5 MWh (pinned from the
  "~$1.2M year-11 replacement" hint). Case 6 = 4 MWh (lean "minimum"
  sizing, scaled down from the 10.7 MWh on-site reference).

## Exit criteria check

- [x] `pytest tests/python/.../test_deck_checks.py` (CEBA) still passes
      unchanged → 13 tests, 12 pass + 1 skip.
- [x] New `july_deck_checks.py` imports cleanly; `all_rows()` returns the
      remapped/new check set with unique IDs → 50 rows, all unique.
- [x] Every check carries `slide`, `repo_fn`, `repo_source_ref` →
      covered by `test_every_check_has_a_slide_and_repo_fn`.
- [x] `dppa_july_2026_case_studies_text.txt` exists and slide numbers
      in the registry match it → covered by
      `test_slides_match_extracted_text`.
- [x] New `test_july_deck_checks.py` passes → 8 tests, 0 failures.
- [x] `DeckConfig` parametrize across all 3 entry points
      (orchestrator, synthesizer, injector) → `--deck {ceba,july}` wired.
- [x] `🔧 calibrated` verdict added to `classify()` + verdict sets in
      the synthesizer and injector.

## What did NOT ship (deferred to later phases)

- The `J_*`-id runner map (the orchestrator's `_SCENARIO_RUNNERS` only
  carries the CEBA `*_*_*` ids). A `J_A04` check will currently report
  `verdict=err` because no runner is registered for that id. This is the
  PHASE-02 work item: wire the A-bucket + worked-example (B01-B04)
  runners to the July ids (a 1:1 copy + J-prefix, plus the deck-text
  confirmations for the slide-anchored values).
- The Case 5/6 PySAM runners (B06..B20) and the 56-sweep
  (`run_strike_sweep` integration). PHASE-03 + PHASE-04.
- The delta markdown report and the `[repo-checked]` deck injection.
  PHASE-05.
- The idempotency-test extension to the July injector. PHASE-05.

## Verification commands

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='src/python;scripts/python'

# 1) Extract the July deck text
.venv\Scripts\python.exe scripts\python\integration\_extract_ceba_deck_text.py --deck july

# 2) Confirm the registry imports + structural integrity
.venv\Scripts\python.exe -m unittest scripts.python.integration.ceba_deck.test_july_deck_checks

# 3) Confirm the CEBA path is still green
.venv\Scripts\python.exe -m unittest scripts.python.integration.ceba_deck.test_deck_checks
```
