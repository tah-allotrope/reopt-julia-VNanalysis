"""Mechanically enforce repo conventions that have previously decayed silently:
the flat-script ban (2026-06-12), the no-tracked-artifacts rule, the
no-tracked-root-binaries rule, the test-shim ban, and the regulatory-watch
review dates. See plans/2026-07-22-ci-truth-correctness-sprint-plan.md
PHASE-02/PHASE-03 and plans/2026-08-06-ci-gate-integrity-and-second-orchestrator-plan.md
PHASE-02.
"""

from __future__ import annotations

import datetime
import re
import subprocess
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


def test_no_test_shims():
    """A .py file directly under tests/ that just delegates to another file is
    the same shape of shim the flat scripts/python/*.py ban removed (2026-06-12);
    tests/cross_validate.py was deleted for it on 2026-08-06."""
    shims = [
        path
        for path in _tracked_files("tests")
        if "/" not in path and path.endswith(".py") and Path(path).name != "__init__.py"
    ]
    assert shims == [], f"test shims must not live flat under tests/: {shims}"


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


def test_regulatory_watch_rows_are_not_overdue():
    """Every row in docs/regulatory-watch.md must carry a Next review date that
    is today or later; the failure message names every overdue row and date."""
    watch = (REPO_ROOT / "docs" / "regulatory-watch.md").read_text(encoding="utf-8")
    header_line = next(
        (line for line in watch.splitlines() if line.startswith("| Manifest key")),
        "",
    )
    assert "Next review" in header_line, "regulatory-watch.md table must have a Next review column"
    header_cells = [c.strip() for c in header_line.strip("|").split("|")]
    next_review_idx = header_cells.index("Next review")

    today = datetime.date.today()
    overdue: list[tuple[str, str]] = []
    for line in watch.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) <= next_review_idx or cells[0] in ("", "---", "Manifest key"):
            continue
        key, next_review = cells[0], cells[next_review_idx]
        match = re.search(r"(\d{4}-\d{2}-\d{2})", next_review)
        if match is None:
            overdue.append((key, f"missing date ({next_review!r})"))
            continue
        if datetime.date.fromisoformat(match.group(1)) < today:
            overdue.append((key, match.group(1)))

    assert not overdue, "regulatory-watch rows are overdue; refresh the policy data or the review date: " + "; ".join(
        f"{key} -> {date}" for key, date in overdue
    )
