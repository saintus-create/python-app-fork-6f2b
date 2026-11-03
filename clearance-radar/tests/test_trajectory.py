"""Tests for the price/stock trajectory engine."""

import unittest
from datetime import date, timedelta

from clearance_radar import PENNY_PRICE
from clearance_radar.models import InventoryItem, PricePoint, StockPoint
from clearance_radar.trajectory import fit_trajectory, linear_regression

TODAY = date(2026, 11, 3)


class TestRegression(unittest.TestCase):
    def test_perfect_line(self):
        reg = linear_regression([0, 1, 2, 3], [10, 8, 6, 4])
        self.assertAlmostEqual(reg.slope, -2.0)
        self.assertAlmostEqual(reg.intercept, 10.0)
        self.assertAlmostEqual(reg.r2, 1.0)
        self.assertAlmostEqual(reg.x_at(0.01), (0.01 - 10.0) / -2.0)

    def test_flat_line_has_no_crossing(self):
        reg = linear_regression([0, 1, 2], [5.0, 5.0, 5.0])
        self.assertEqual(reg.slope, 0.0)
        self.assertIsNone(reg.x_at(PENNY_PRICE))

    def test_single_point(self):
        reg = linear_regression([3], [7.5])
        self.assertEqual(reg.n_points, 1)
        self.assertEqual(reg.intercept, 7.5)


class TestTrajectory(unittest.TestCase):
    def _item(self, prices, qtys=None):
        qtys = qtys or [10]
        hist = [PricePoint(TODAY - timedelta(days=len(prices) - 1 - i), p) for i, p in enumerate(prices)]
        stocks = [
            StockPoint(TODAY - timedelta(days=len(qtys) - 1 - i), q)
            for i, q in enumerate(qtys)
        ]
        return InventoryItem(
            sku="x", store_id="s", name="n", category="c",
            current_price=prices[-1], original_price=prices[0],
            quantity=qtys[-1] if qtys else 10,
            listed_date=TODAY - timedelta(days=len(prices) - 1),
            price_history=hist, stock_history=stocks,
        )

    def test_projected_penny_date(self):
        # Price drops $2/day from $20 -> $0.01 in ~10 days.
        item = self._item([20, 18, 16, 14, 12, 10, 8])
        traj = fit_trajectory(item, TODAY)
        self.assertEqual(traj.price_trend, "falling")
        self.assertIsNotNone(traj.projected_penny_date)
        delta = (traj.projected_penny_date - TODAY).days
        self.assertGreaterEqual(delta, 3)
        self.assertLessEqual(delta, 6)

    def test_no_projection_when_flat(self):
        item = self._item([10, 10, 10, 10])
        traj = fit_trajectory(item, TODAY)
        self.assertEqual(traj.price_trend, "flat")
        self.assertIsNone(traj.projected_penny_date)

    def test_no_projection_when_rising(self):
        item = self._item([5, 6, 7, 8])
        traj = fit_trajectory(item, TODAY)
        self.assertEqual(traj.price_trend, "rising")
        self.assertIsNone(traj.projected_penny_date)

    def test_sellout_projection(self):
        # Stock drops 2/day from 10 -> out in ~5 days.
        item = self._item([10, 10, 10, 10], qtys=[10, 8, 6, 4])
        traj = fit_trajectory(item, TODAY)
        self.assertIsNotNone(traj.days_until_sold_out)
        self.assertGreater(traj.days_until_sold_out, 1)
        self.assertLess(traj.days_until_sold_out, 4)

    def test_confidence_grows_with_history(self):
        short = fit_trajectory(self._item([20, 10]), TODAY)
        long = fit_trajectory(self._item([20, 18, 16, 14, 12, 10, 8, 6]), TODAY)
        self.assertGreater(long.confidence, short.confidence)

    def test_projection_points_forward_only(self):
        item = self._item([20, 16, 12, 8])
        traj = fit_trajectory(item, TODAY)
        self.assertTrue(traj.projection_points)
        for p in traj.projection_points:
            self.assertGreaterEqual(p["price"], 0.0)


if __name__ == "__main__":
    unittest.main()
