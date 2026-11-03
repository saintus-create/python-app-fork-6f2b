"""Tests for liquidation signal detection and scoring."""

import unittest
from datetime import date, timedelta

from clearance_radar import PENNY_PRICE
from clearance_radar.detector import (
    SignalKind,
    annotate_item,
    detect_signals,
    liquidation_score,
)
from clearance_radar.models import InventoryItem, PricePoint, StockPoint
from clearance_radar.trajectory import fit_trajectory

TODAY = date(2026, 11, 3)


def make_item(**kw):
    defaults = dict(
        sku="t-1",
        store_id="s-1",
        name="Widget",
        category="Misc",
        current_price=10.0,
        original_price=20.0,
        quantity=5,
        listed_date=TODAY - timedelta(days=10),
    )
    defaults.update(kw)
    return InventoryItem(**defaults)


class TestDetectSignals(unittest.TestCase):
    def test_penny_purge(self):
        item = make_item(current_price=PENNY_PRICE, quantity=2)
        kinds = {s.kind for s in detect_signals(item, TODAY)}
        self.assertIn(SignalKind.PENNY_PURGE, kinds)

    def test_last_item(self):
        item = make_item(quantity=1)
        kinds = {s.kind for s in detect_signals(item, TODAY)}
        self.assertIn(SignalKind.LAST_ITEM, kinds)

    def test_aging_shelf_sitter(self):
        item = make_item(listed_date=TODAY - timedelta(days=120))
        kinds = {s.kind for s in detect_signals(item, TODAY, aging_threshold_days=45)}
        self.assertIn(SignalKind.AGING, kinds)
        fresh = make_item(listed_date=TODAY - timedelta(days=5))
        self.assertNotIn(
            SignalKind.AGING, {s.kind for s in detect_signals(fresh, TODAY, aging_threshold_days=45)}
        )

    def test_clearance_and_discontinued(self):
        item = make_item(clearance=True, discontinued=True)
        kinds = {s.kind for s in detect_signals(item, TODAY)}
        self.assertIn(SignalKind.CLEARANCE, kinds)
        self.assertIn(SignalKind.DISCONTINUED, kinds)

    def test_no_signals_for_healthy_item(self):
        item = make_item(quantity=9, listed_date=TODAY - timedelta(days=3))
        self.assertEqual(detect_signals(item, TODAY), [])

    def test_steep_markdown_from_trajectory(self):
        # Steadily falling price history ending in a sharp final markdown
        # -> projected penny date within 14 days.
        days = [28, 21, 14, 7, 0]
        prices = [30.0, 26.0, 22.0, 18.0, 8.0]
        hist = [PricePoint(TODAY - timedelta(days=d), p) for d, p in zip(days, prices)]
        item = make_item(current_price=8.0, price_history=hist)
        traj = fit_trajectory(item, TODAY)
        kinds = {s.kind for s in detect_signals(item, TODAY, trajectory=traj)}
        self.assertIn(SignalKind.STEEP_MARKDOWN, kinds)
        self.assertIsNotNone(traj.projected_penny_date)

    def test_signals_sorted_by_severity(self):
        item = make_item(current_price=PENNY_PRICE, quantity=1, clearance=True,
                         listed_date=TODAY - timedelta(days=200), discontinued=True)
        signals = detect_signals(item, TODAY)
        self.assertEqual(signals[0].kind, SignalKind.PENNY_PURGE)


class TestScoring(unittest.TestCase):
    def test_score_capped_at_100(self):
        item = make_item(current_price=PENNY_PRICE, quantity=1, clearance=True,
                         discontinued=True, listed_date=TODAY - timedelta(days=300))
        signals = detect_signals(item, TODAY)
        score = liquidation_score(signals)
        self.assertGreaterEqual(score, 90)
        self.assertLessEqual(score, 100)

    def test_clean_item_scores_zero(self):
        item = make_item()
        self.assertEqual(liquidation_score(detect_signals(item, TODAY)), 0.0)


class TestAnnotate(unittest.TestCase):
    def test_annotate_item_shape(self):
        item = make_item(current_price=PENNY_PRICE, quantity=1)
        data = annotate_item(item, TODAY)
        for key in ("signals", "liquidation_score", "trajectory", "days_on_shelf", "markdown_pct"):
            self.assertIn(key, data)
        self.assertGreater(data["liquidation_score"], 0)
        self.assertIn("projected_penny_date", data["trajectory"])


if __name__ == "__main__":
    unittest.main()
