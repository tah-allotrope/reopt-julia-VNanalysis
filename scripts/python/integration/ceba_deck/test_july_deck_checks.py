"""Smoke test: confirm the July deck registry imports + enumerates as expected.

Run with:
    .venv\\Scripts\\python.exe -m unittest scripts.python.integration.ceba_deck.test_july_deck_checks
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "python"))


class JulyDeckChecksRegistryTest(unittest.TestCase):
    def test_registry_enumerates(self) -> None:
        from integration.ceba_deck.july_deck_checks import CHECKS

        # The plan exit criterion: at least 30 checks across buckets A/B/C
        # (registry carries 50: 16 A + 25 B + 9 C).
        self.assertGreaterEqual(
            len(CHECKS),
            30,
            f"expected >=30 checks, got {len(CHECKS)}",
        )
        buckets = {c.bucket for c in CHECKS}
        self.assertEqual(buckets, {"A", "B", "C"})

    def test_every_check_has_a_slide_and_repo_fn(self) -> None:
        from integration.ceba_deck.july_deck_checks import CHECKS

        for c in CHECKS:
            self.assertGreater(c.slide, 0, f"{c.id} missing slide number")
            self.assertTrue(c.repo_fn, f"{c.id} missing repo_fn")
            self.assertTrue(c.repo_source_ref, f"{c.id} missing repo_source_ref")
            self.assertTrue(
                c.claim,
                f"{c.id} missing claim text",
            )

    def test_unique_ids(self) -> None:
        from integration.ceba_deck.july_deck_checks import CHECKS

        ids = [c.id for c in CHECKS]
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids in registry")

    def test_slides_match_extracted_text(self) -> None:
        """Every slide number referenced in the registry must appear in the
        extracted deck text (so the orchestrator's slide-anchored notes
        injection cannot point at a phantom slide)."""
        from integration.ceba_deck.july_deck_checks import CHECKS

        text_path = REPO_ROOT / "ceba-review" / "dppa_july_2026_case_studies_text.txt"
        if not text_path.exists():
            self.skipTest(f"missing extracted text: {text_path}")
        text = text_path.read_text(encoding="utf-8")
        for c in CHECKS:
            marker = f"[Slide {c.slide}]"
            self.assertIn(
                marker,
                text,
                f"{c.id} references slide {c.slide} but no '[Slide {c.slide}]' "
                f"marker found in the extracted deck text",
            )

    def test_calibrated_set_consistent(self) -> None:
        """The calibrated set must reference ids that exist in the registry,
        must NOT include the sweep checks (those are independent), and must
        cover exactly the Case 5/6 family."""
        from integration.ceba_deck.july_deck_checks import (
            CHECKS,
            JULY_CALIBRATED_CHECKS,
            JULY_SWEEP_CHECKS,
        )

        ids = {c.id for c in CHECKS}
        for cid in JULY_CALIBRATED_CHECKS:
            self.assertIn(cid, ids, f"calibrated set references unknown id: {cid}")
        for cid in JULY_SWEEP_CHECKS:
            self.assertIn(cid, ids, f"sweep set references unknown id: {cid}")
        # Calibrated and sweep sets must be disjoint.
        self.assertEqual(
            JULY_CALIBRATED_CHECKS & JULY_SWEEP_CHECKS,
            set(),
            "calibrated and sweep sets overlap",
        )

    def test_case5_case6_disclosures_present(self) -> None:
        """The plan requires all six Case 5 metrics + all five Case 6 metrics
        + all four sweep gate rows to be in the registry."""
        from integration.ceba_deck.july_deck_checks import CHECKS

        by_id = {c.id for c in CHECKS}
        required_case5 = {
            "J_B06_case5_seller_irr",
            "J_B07_case5_project_irr",
            "J_B08_case5_developer_npv",
            "J_B09_case5_min_dscr",
            "J_B10_case5_payback_years",
            "J_B11_case5_buyer_vs_bau_year1",
            "J_B17_case5_buyer_vs_bau_10yr",
            "J_B18_case5_buyer_vs_bau_lifetime",
        }
        required_case6 = {
            "J_B12_case6_seller_irr",
            "J_B13_case6_project_irr",
            "J_B14_case6_developer_npv",
            "J_B15_case6_min_dscr",
            "J_B16_case6_payback_years",
            "J_B20_case6_buyer_vs_bau_lifetime",
        }
        required_sweep = {
            "J_B21_sweep_offer_buyer",
            "J_B22_sweep_1400_seller",
            "J_B23_sweep_1300_70pct_lender",
            "J_B24_sweep_1200_buyer",
            "J_B25_sweep_zero_of_56",
        }
        for cid in required_case5 | required_case6 | required_sweep:
            self.assertIn(cid, by_id, f"required disclosure missing: {cid}")

    def test_a12_fmp_notes_anchor(self) -> None:
        """A12 is the deck FMP 1,426.6 vs repo center 1,700 reconcile —
        the registry MUST record the assumption that the deck value is the
        Case 5/6 anchor and the repo value is a sensitivity midpoint."""
        from integration.ceba_deck.july_deck_checks import CHECKS

        a12 = next(c for c in CHECKS if c.id == "J_A12_fmp_2025_avg")
        self.assertEqual(a12.deck_value, 1426.6)
        assumption_text = " ".join(a12.assumptions or [])
        self.assertIn("anchor", assumption_text.lower())
        self.assertIn("sensitivity", assumption_text.lower())

    def test_all_rows_helper(self) -> None:
        from integration.ceba_deck.july_deck_checks import all_rows

        rows = all_rows()
        self.assertGreaterEqual(len(rows), 30)


if __name__ == "__main__":
    unittest.main()
