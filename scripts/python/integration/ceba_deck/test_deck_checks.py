"""Smoke test: confirm deck_checks registry imports + enumerates as expected.

Run with:
    .venv\\Scripts\\python.exe -m unittest scripts.python.integration.ceba_deck.test_deck_checks
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python"))

from integration.ceba_deck.deck_checks import CHECKS, KNOWN_GAPS, all_rows


class DeckChecksRegistryTest(unittest.TestCase):
    def test_registry_enumerates(self) -> None:
        # The plan exit criterion: at least 20 checks across buckets A/B/C
        # plus the known_gap rows.
        self.assertGreaterEqual(
            len(CHECKS),
            20,
            f"expected >=20 checks, got {len(CHECKS)}",
        )
        buckets = {c.bucket for c in CHECKS}
        self.assertEqual(buckets, {"A", "B", "C"})

    def test_every_check_has_a_slide_and_repo_fn(self) -> None:
        for c in CHECKS:
            self.assertGreater(c.slide, 0, f"{c.id} missing slide number")
            self.assertTrue(c.repo_fn, f"{c.id} missing repo_fn")
            self.assertTrue(c.repo_source_ref, f"{c.id} missing repo_source_ref")

    def test_unique_ids(self) -> None:
        ids = [c.id for c in CHECKS] + [g.id for g in KNOWN_GAPS]
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids in registry")

    def test_known_gaps_present(self) -> None:
        # The plan calls out: decree-146 two-part tariff, RECs/EACs, GHG scopes.
        topics = {g.topic for g in KNOWN_GAPS}
        self.assertTrue(any("146" in t or "two-part" in t.lower() for t in topics))
        self.assertTrue(any("REC" in t or "EAC" in t for t in topics))
        self.assertTrue(any("GHG" in t or "Scope" in t for t in topics))

    def test_all_rows_helper(self) -> None:
        rows = all_rows()
        self.assertEqual(len(rows), len(CHECKS) + len(KNOWN_GAPS))


if __name__ == "__main__":
    unittest.main()
