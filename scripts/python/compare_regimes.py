"""Convenience wrapper for the regime comparison CLI (GAP-05, PHASE-03, TASK-03-05).

Delegates to scripts/python/reopt/compare_regimes.py so the tool is reachable from
the top-level scripts/python directory. All arguments are forwarded unchanged.

Example:
    python scripts/python/compare_regimes.py --factory <load> --regime-a <id> --regime-b <id>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "reopt"))

from compare_regimes import main  # noqa: E402  (re-export the reopt CLI entrypoint)

if __name__ == "__main__":
    raise SystemExit(main())
