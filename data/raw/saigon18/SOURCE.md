# Saigon18 Raw Workbook — Source (not git-tracked)

`2026-01-29_saigon18_excel_model_v2.xlsm` (~9.5 MB) is the source EPC-grade Excel feasibility
model for the Saigon18 onsite Solar + BESS project. It is **git-ignored** (Sprint 2 de-bloat,
2026-06-12) and kept on disk locally.

## The pipeline does not depend on the raw workbook

Its contents were already distilled into the canonical, tracked interim file:

- `data/interim/saigon18/2026-03-20_saigon18_extracted_inputs.json`

produced by `scripts/python/reopt/extract_excel_inputs.py`. Day-to-day analysis and tests read the
distilled JSON, not the `.xlsm`. Verified: `tests/python/integration/test_saigon18_data.py` passes
without the workbook being tracked.

## Re-extracting (only if the source model changes)

```powershell
python scripts/python/reopt/extract_excel_inputs.py `
  --excel data/raw/saigon18/2026-01-29_saigon18_excel_model_v2.xlsm
```

## Recovering the workbook from history

```bash
git log --oneline -- data/raw/saigon18/2026-01-29_saigon18_excel_model_v2.xlsm | head -1
git show <commit>:data/raw/saigon18/2026-01-29_saigon18_excel_model_v2.xlsm > \
  data/raw/saigon18/2026-01-29_saigon18_excel_model_v2.xlsm
```
