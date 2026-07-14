"""CLI for pruning stale runs from the web app's filesystem run store
(PHASE-01, DEC-105).

    python -m reopt_pysam_vn.webapp.prune --days 30          # dry run (default)
    python -m reopt_pysam_vn.webapp.prune --days 30 --apply  # actually delete

Only runs in a terminal state (``done``/``error``) older than ``--days`` are
ever selected; ``queued``/``solving``/``analyzing`` runs are never pruned
regardless of age.
"""

from __future__ import annotations

import argparse
import sys

from reopt_pysam_vn.webapp.storage import RunStorage, default_runs_dir

__all__ = ["main"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Prune stale webapp runs.")
    parser.add_argument("--days", type=int, required=True, help="age threshold in days")
    parser.add_argument(
        "--apply", action="store_true", help="actually delete (default is a dry run)"
    )
    args = parser.parse_args(argv)

    storage = RunStorage(default_runs_dir())
    stale = storage.prune(args.days, dry_run=not args.apply)

    if not stale:
        print("no stale runs found")
        return 0

    verb = "deleted" if args.apply else "would delete"
    for run_id in stale:
        print(f"{verb}: {run_id}")
    print(f"{verb} {len(stale)} run(s) older than {args.days} day(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
