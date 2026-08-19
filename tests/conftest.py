"""Repo-root test conftest: the CI skip + deselect budgets.

CI sets ``REOPT_PYSAM_VN_MAX_SKIPS`` and ``REOPT_PYSAM_VN_MAX_DESELECTED`` so
any growth in the number of skipped/deselected tests fails the build instead
of silently shrinking the enforced suite. When the variable is unset (local
runs) the budget is not enforced.
"""

from __future__ import annotations

import os
import sys

import pytest

_skip_count = 0
_deselected_count = 0


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    global _skip_count
    # A test that fails as expected under ``@pytest.mark.xfail`` also carries
    # ``report.skipped=True`` (with ``report.wasxfail`` set) — that is an xfail
    # outcome, not a skip, and must not count against the skip budget. A real
    # skip has ``wasxfail`` unset. A skipped test emits exactly one skipped
    # report (``setup`` for ``@pytest.mark.skip``/fixture skips, ``call`` for
    # ``pytest.skip()`` in the body), so counting every real-skip report counts
    # each skipped test once.
    if report.skipped and not getattr(report, "wasxfail", None):
        _skip_count += 1


def pytest_deselected(items: list[pytest.Item]) -> None:
    global _deselected_count
    _deselected_count += len(items)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del exitstatus  # hook signature; not consumed here
    raw = os.environ.get("REOPT_PYSAM_VN_MAX_SKIPS")
    if raw is not None:
        budget = int(raw)
        if _skip_count > budget:
            print(
                f"SKIP BUDGET EXCEEDED: {_skip_count} skipped, budget {budget}",
                file=sys.stderr,
            )
            session.exitstatus = 1
    raw_deselect = os.environ.get("REOPT_PYSAM_VN_MAX_DESELECTED")
    if raw_deselect is not None:
        deselect_budget = int(raw_deselect)
        if _deselected_count > deselect_budget:
            print(
                f"DESELECT BUDGET EXCEEDED: {_deselected_count} deselected, budget {deselect_budget}",
                file=sys.stderr,
            )
            session.exitstatus = 1
