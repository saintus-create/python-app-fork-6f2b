"""Trajectory engine: turn price/stock history into liquidation projections.

For every item we fit a least-squares line to its price history (price vs.
days) and to its stock history (quantity vs. days). From the price line we
project forward to the dates the price would cross meaningful liquidation
thresholds (the $0.01 penny purge, 50% off original). From the stock line we
project how many days of inventory remain. A good fit (high R^2) means the
trajectory is trustworthy; a poor fit means the projection is speculative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from . import PENNY_PRICE
from .models import InventoryItem, StockPoint, PricePoint


@dataclass
class Regression:
    """Simple linear regression y = slope * x + intercept."""

    slope: float
    intercept: float
    r2: float
    n_points: int

    def predict(self, x: float) -> float:
        return self.slope * x + self.intercept

    def x_at(self, y: float) -> float | None:
        """x value at which the line reaches ``y`` (None if never / flat)."""
        if self.slope == 0:
            return None
        return (y - self.intercept) / self.slope


def linear_regression(xs: list[float], ys: list[float]) -> Regression:
    """Least-squares fit; returns a flat line when there is not enough data."""
    n = len(xs)
    if n == 0:
        return Regression(0.0, 0.0, 0.0, 0)
    if n == 1:
        return Regression(0.0, ys[0], 1.0, 1)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    if sxx == 0:
        return Regression(0.0, mean_y, 1.0, n)
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    syy = sum((y - mean_y) ** 2 for y in ys)
    r2 = 1.0 if syy == 0 else max(0.0, 1.0 - (sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys)) / syy))
    return Regression(slope, intercept, r2, n)


@dataclass
class Trajectory:
    """Projected liquidation timeline for one item."""

    today: date
    price_regression: Regression
    stock_regression: Regression
    projected_penny_date: date | None = None  # when price hits $0.01
    projected_half_price_date: date | None = None  # when price hits 50% off
    days_until_sold_out: float | None = None
    price_trend: str = "flat"  # "falling" | "rising" | "flat"
    confidence: float = 0.0  # 0-1, from R^2 of the price fit
    projection_points: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "today": self.today.isoformat(),
            "price_trend": self.price_trend,
            "price_slope_per_day": round(self.price_regression.slope, 4),
            "price_r2": round(self.price_regression.r2, 3),
            "confidence": round(self.confidence, 3),
            "projected_penny_date": (
                self.projected_penny_date.isoformat() if self.projected_penny_date else None
            ),
            "projected_half_price_date": (
                self.projected_half_price_date.isoformat()
                if self.projected_half_price_date
                else None
            ),
            "days_until_sold_out": (
                round(self.days_until_sold_out, 1) if self.days_until_sold_out is not None else None
            ),
            "projection_points": self.projection_points,
        }


def _to_xy(points: list[PricePoint] | list[StockPoint], today: date, price: bool) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for p in sorted(points, key=lambda p: p.date):
        x = (p.date - today).days  # negative = in the past
        ys.append(p.price if price else p.quantity)
        xs.append(float(x))
    return xs, ys


def fit_trajectory(item: InventoryItem, today: date | None = None) -> Trajectory:
    """Fit price/stock trajectories for an item and project liquidation dates."""
    today = today or date.today()

    px, py = _to_xy(item.price_history, today, price=True)
    price_reg = linear_regression(px, py)

    sx, sy = _to_xy(item.stock_history, today, price=False)
    stock_reg = linear_regression(sx, sy)

    traj = Trajectory(today=today, price_regression=price_reg, stock_regression=stock_reg)

    # Price trend label.
    if price_reg.n_points >= 2 and price_reg.slope < -1e-9:
        traj.price_trend = "falling"
    elif price_reg.n_points >= 2 and price_reg.slope > 1e-9:
        traj.price_trend = "rising"
    else:
        traj.price_trend = "flat"

    # Confidence: blend R^2 with sample size (more history -> more trust).
    sample_factor = min(1.0, price_reg.n_points / 6.0)
    traj.confidence = round(price_reg.r2 * sample_factor, 3)

    # Project crossing dates (only forward in time makes sense).
    half = item.original_price * 0.5
    if item.current_price <= PENNY_PRICE + 1e-9:
        traj.projected_penny_date = today  # already at the penny price
    elif price_reg.slope < 0:
        x_penny = price_reg.x_at(PENNY_PRICE)
        if x_penny is not None and x_penny >= 0:
            traj.projected_penny_date = today + timedelta(days=int(x_penny))
    if item.current_price <= half + 1e-9:
        traj.projected_half_price_date = today  # already at 50% off or more
    elif price_reg.slope < 0 and half > item.current_price:
        x_half = price_reg.x_at(half)
        if x_half is not None and x_half >= 0:
            traj.projected_half_price_date = today + timedelta(days=int(x_half))

    # Project sell-out from stock depletion (only if stock is shrinking).
    if stock_reg.slope < 0 and stock_reg.n_points >= 2:
        x_out = stock_reg.x_at(0.0)
        if x_out is not None and x_out >= 0:
            traj.days_until_sold_out = round(x_out, 1)

    # Forward projection polyline for the UI sparkline (30 days out).
    if price_reg.n_points >= 2:
        last_x = max(px) if px else 0.0
        pts = []
        for day in range(int(last_x), int(last_x) + 31, 3):
            pts.append(
                {
                    "date": (today + timedelta(days=day)).isoformat(),
                    "price": round(max(0.0, price_reg.predict(day)), 2),
                }
            )
        traj.projection_points = pts

    return traj
