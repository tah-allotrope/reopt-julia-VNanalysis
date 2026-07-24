"""Mechanically enforce repo conventions that have previously decayed silently:
the flat-script ban (2026-06-12), the no-tracked-artifacts rule, and the
no-tracked-root-binaries rule. See
plans/2026-07-22-ci-truth-correctness-sprint-plan.md PHASE-02/PHASE-03.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ROOT_BINARY_SUFFIXES = {".png", ".pptx", ".xlsx", ".xlsm"}


def _tracked_files(prefix: str = "") -> list[str]:
    command = ["git", "ls-files"]
    if prefix:
        command += ["--", prefix]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def test_no_flat_python_scripts():
    flat_scripts = [
        path
        for path in _tracked_files("scripts/python")
        if path.count("/") == 2 and path.endswith(".py") and Path(path).name != "__init__.py"
    ]
    assert flat_scripts == [], (
        "scripts must live under scripts/python/{reopt,pysam,integration}/, "
        f"not the flat scripts/python/ level: {flat_scripts}"
    )


def test_no_tracked_artifacts():
    tracked = _tracked_files("artifacts")
    assert tracked == [], f"artifacts/ is git-ignored by design; found tracked files: {tracked}"


def test_no_root_level_binaries():
    root_binaries = [
        path
        for path in _tracked_files()
        if "/" not in path and Path(path).suffix in ROOT_BINARY_SUFFIXES
    ]
    assert root_binaries == [], f"tracked root-level binaries found: {root_binaries}"
