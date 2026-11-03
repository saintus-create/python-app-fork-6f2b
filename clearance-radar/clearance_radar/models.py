"""Data models for Clearance Radar."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


def parse_date(value: Any) -> date:
    """Parse an ISO date/datetime string (or pass through a ``date``)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


@dataclass
class PricePoint:
    """A single observation of an item's price."""

    date: date
    price: float

    def to_dict(self) -> dict[str, Any]:
        return {"date": self.date.isoformat(), "price": round(self.price, 2)}


@dataclass
class StockPoint:
    """A single observation of an item's on-hand quantity."""

    date: date
    quantity: int

    def to_dict(self) -> dict[str, Any]:
        return {"date": self.date.isoformat(), "quantity": self.quantity}


@dataclass
class InventoryItem:
    """A product sitting on a store's shelf."""

    sku: str
    store_id: str
    name: str
    category: str
    current_price: float
    original_price: float
    quantity: int
    listed_date: date  # when the item first appeared on the shelf
    clearance: bool = False  # already moved to the clearance rack
    discontinued: bool = False  # pulled from the catalog -> leaving the shelf
    price_history: list[PricePoint] = field(default_factory=list)
    stock_history: list[StockPoint] = field(default_factory=list)

    def days_on_shelf(self, today: date | None = None) -> int:
        """How many days the item has been sitting on the shelf."""
        today = today or date.today()
        return max(0, (today - self.listed_date).days)

    def markdown_pct(self) -> float:
        """Discount vs. the original price, as a percentage (0-100)."""
        if self.original_price <= 0:
            return 0.0
        return max(0.0, (1.0 - self.current_price / self.original_price) * 100.0)

    def to_dict(self, today: date | None = None) -> dict[str, Any]:
        today = today or date.today()
        return {
            "sku": self.sku,
            "store_id": self.store_id,
            "name": self.name,
            "category": self.category,
            "current_price": round(self.current_price, 2),
            "original_price": round(self.original_price, 2),
            "markdown_pct": round(self.markdown_pct(), 1),
            "quantity": self.quantity,
            "listed_date": self.listed_date.isoformat(),
            "days_on_shelf": self.days_on_shelf(today),
            "clearance": self.clearance,
            "discontinued": self.discontinued,
            "price_history": [p.to_dict() for p in self.price_history],
            "stock_history": [s.to_dict() for s in self.stock_history],
        }


@dataclass
class Store:
    """A retail location."""

    id: str
    name: str
    chain: str
    address: str
    city: str
    state: str
    lat: float
    lon: float
    phone: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "chain": self.chain,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "lat": self.lat,
            "lon": self.lon,
            "phone": self.phone,
        }
