"""Smoke entry point for the Phase 4 Single Owner workflow."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.pysam.single_owner import (
    build_single_owner_inputs,
    run_single_owner_model,
)


def main() -> None:
    inputs = build_single_owner_inputs(system_capacity_kw=1000)
    results = run_single_owner_model(inputs)
    print(results["model"])
    print(results["outputs"])


if __name__ == "__main__":
    main()
