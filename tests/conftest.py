"""Repo-root test conftest: the CI skip budget (PHASE-01).

CI sets ``REOPT_PYSAM_VN_MAX_SKIPS`` so any growth in the number of skipped
tests fails the build instead of silently shrinking the enforced suite. When
the variable is unset (local runs) the budget is not enforced.
"""

from __future__ import annotations

import os
import sys

import pytest

_skip_count = 0


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    global _skip_count
    if report.skipped:
        # A skipped test emits exactly one skipped report: `when == "setup"` for
        # ``@pytest.mark.skip`` and `when == "call"` for ``pytest.skip()`` inside
        # the body (verified empirically), so counting every skipped report
        # counts each skipped test exactly once.
        _skip_count += 1


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del exitstatus  # hook signature; not consumed here
    raw = os.environ.get("REOPT_PYSAM_VN_MAX_SKIPS")
    if raw is None:
        return
    budget = int(raw)
    if _skip_count > budget:
        print(
            f"SKIP BUDGET EXCEEDED: {_skip_count} skipped, budget {budget}",
            file=sys.stderr,
        )
        session.exitstatus = 1
