"""In-memory repository for stores and inventory items."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .detector import annotate_item
from .geo import find_nearby
from .models import InventoryItem, Store


class Repository:
    """Holds stores + items and answers location/clearance queries."""

    def __init__(self) -> None:
        self.stores: dict[str, Store] = {}
        self.items: dict[str, InventoryItem] = {}  # keyed by SKU

    def add_store(self, store: Store) -> None:
        self.stores[store.id] = store

    def add_item(self, item: InventoryItem) -> None:
        self.items[item.sku] = item

    def items_for_store(self, store_id: str) -> list[InventoryItem]:
        return [i for i in self.items.values() if i.store_id == store_id]

    def nearby(self, lat: float, lon: float, radius_km: float, today: date | None = None) -> list[dict[str, Any]]:
        """Stores within radius, annotated with flagged-item stats, nearest first."""
        today = today or date.today()
        out = []
        for store, dist in find_nearby(list(self.stores.values()), lat, lon, radius_km):
            flagged = [annotate_item(i, today) for i in self.items_for_store(store.id)]
            flagged = [f for f in flagged if f["signals"]]
            entry = store.to_dict()
            entry["distance_km"] = round(dist, 2)
            entry["flagged_count"] = len(flagged)
            entry["best_score"] = max((f["liquidation_score"] for f in flagged), default=0.0)
            entry["signals"] = sorted({s["kind"] for f in flagged for s in f["signals"]})
            out.append(entry)
        return out

    def store_detail(self, store_id: str, today: date | None = None) -> dict[str, Any] | None:
        today = today or date.today()
        store = self.stores.get(store_id)
        if store is None:
            return None
        data = store.to_dict()
        data["items"] = [
            annotate_item(i, today)
            for i in sorted(
                self.items_for_store(store_id),
                key=lambda i: i.sku,
            )
        ]
        data["items"].sort(key=lambda d: d["liquidation_score"], reverse=True)
        return data

    def item_detail(self, sku: str, today: date | None = None) -> dict[str, Any] | None:
        today = today or date.today()
        item = self.items.get(sku)
        if item is None:
            return None
        data = annotate_item(item, today)
        store = self.stores.get(item.store_id)
        data["store"] = store.to_dict() if store else None
        return data

    def alerts(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        min_score: float = 60.0,
        today: date | None = None,
    ) -> list[dict[str, Any]]:
        """All flagged items within radius with score >= min_score, best first."""
        today = today or date.today()
        out = []
        for store, dist in find_nearby(list(self.stores.values()), lat, lon, radius_km):
            for item in self.items_for_store(store.id):
                a = annotate_item(item, today)
                if a["liquidation_score"] >= min_score and a["signals"]:
                    a["store"] = store.to_dict()
                    a["distance_km"] = round(dist, 2)
                    out.append(a)
        out.sort(key=lambda a: (-a["liquidation_score"], a["distance_km"]))
        return out

    # --- optional JSON persistence -------------------------------------
    def save(self, path: str | Path) -> None:
        payload = {
            "stores": [s.to_dict() for s in self.stores.values()],
            "items": [i.to_dict() for i in self.items.values()],
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
