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

    def test_combined_fees_reconciles_to_dppa_adder(self) -> None:
        """The deck's 360 + 163.3 = 523.3 must reconcile to ContractParams.dppa_adder_vnd_kwh."""
        from reopt_pysam_vn.integration.settlement import ContractParams
        params = ContractParams(mode="virtual_cfd", strike_vnd_kwh=1_500.0)
        a04 = next(c for c in CHECKS if c.id == "A04_combined_dppa_fees")
        self.assertEqual(a04.deck_value, 523.3, "A04 deck value should be 360+163.3=523.3")
        self.assertAlmostEqual(
            params.dppa_adder_vnd_kwh,
            523.3,
            delta=0.05,
            msg=f"ContractParams.dppa_adder_vnd_kwh={params.dppa_adder_vnd_kwh} should match deck's 523.3",
        )

    def test_no_phantom_checks(self) -> None:
        """Each check's deck_value must be plausible (a non-zero value or a labeled
        qualitative statement); phantom numbers (deck claims that don't appear
        anywhere in the deck) should be caught and removed."""
        # A13 used to be a phantom "deck_value=235414 demand charge" that didn't
        # appear in the deck text. Make sure no check has deck_value 235414.
        for c in CHECKS:
            if isinstance(c.deck_value, (int, float)):
                self.assertNotAlmostEqual(
                    float(c.deck_value),
                    235414.0,
                    places=0,
                    msg=f"{c.id} deck_value={c.deck_value} looks like the phantom A13 demand charge — verify it's a real deck claim",
                )

    def test_eavced_citation_on_module2(self) -> None:
        """Deck Slide 11 explicitly says 'Source: EAVCED public training' which
        covers the Module-2 5-line sim (B01-B03) and the related A-bucket
        claims (A03 avg retail, A06 k, A07 Kpp). Those should carry that
        citation so DEC-008 reconcile fires on divergent values."""
        ids_with_eavced = {
            "A03_avg_retail_price",
            "A04_combined_dppa_fees",
            "A06_k_loss_factor",
            "A07_kpp_loss_factor",
            "B01_simulation_5line_total_evnbill",
            "B02_simulation_cfd_settlement",
            "B03_simulation_effective_blended_rate",
        }
        by_id = {c.id: c for c in CHECKS}
        for cid in ids_with_eavced:
            self.assertIn(cid, by_id, f"{cid} missing from registry")
            self.assertIn(
                "EAVCED",
                (by_id[cid].deck_citation or ""),
                f"{cid} should carry the EAVCED public training citation (deck Slide 11)",
            )

    def test_capital_structure_coverage(self) -> None:
        """TASK-01-02 requires A-bucket coverage of the deck's full capital
        structure: debt fraction, debt rate, debt tenor, equity target, CIT
        holiday, and PV degradation."""
        by_id = {c.id: c for c in CHECKS}
        for cid in (
            "A09_debt_fraction",
            "A10_debt_rate_vnd",
            "A14_debt_tenor_years",
            "A15_equity_irr_target",
            "A16_cit_holiday",
            "A11_pv_degradation",
        ):
            self.assertIn(cid, by_id, f"{cid} missing from registry")

    def test_all_rows_helper(self) -> None:
        rows = all_rows()
        self.assertEqual(len(rows), len(CHECKS) + len(KNOWN_GAPS))


if __name__ == "__main__":
    unittest.main()
