# Research — Heavy Reference Sources (not git-tracked)

Two large reference binaries in `research/` are **git-ignored** (Sprint 2 de-bloat, 2026-06-12)
to keep the repository lean. They remain on disk locally and are not required by any code or test
in this repo — they are background reference material only.

| File | Size | What it is | How to obtain |
|---|---|---|---|
| `TOU-Analysis_SolarBESS-ENG.pdf` | ~13.6 MB | English-language time-of-use (TOU) tariff analysis for a Solar + BESS project — reference for the Vietnam TOU modeling. | Recover from git history (tracked through commit `17b83a1`'s parent line, pre-2026-06-12), or request from the original project owner. |
| `fmp_modeling.csv` | ~12 MB | Full-Market-Price (FMP) modeling dataset behind the FMP overlay research notes. | Recover from git history (pre-2026-06-12) or regenerate from the FMP source model. |

## Recovering a file from history

```bash
# find the last commit that had the file, then extract it
git log --oneline -- research/fmp_modeling.csv | head -1
git show <commit>:research/fmp_modeling.csv > research/fmp_modeling.csv
```

## Why untracked

These are multi-megabyte binaries that bloated every clone but are not consumed by the
ReOpt/PySAM pipeline. The decision (Sprint 2, Q-001) was **untrack + external + manifest** —
no Git LFS and no history rewrite, so existing clones are undisturbed.
