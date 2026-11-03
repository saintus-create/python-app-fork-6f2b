"""Liquidation signal detector.

Inspects each inventory item and emits the signals that mean "this product is
being liquidated or will be taken off the shelves":

* ``PENNY_PURGE``   — current price is one cent (the classic purge price)
* ``CLEARANCE``     — item is on the clearance rack
* ``LAST_ITEM``     — only one unit left in stock
* ``AGING``         — has been sitting on the shelf longer than the threshold
* ``DISCONTINUED``  — pulled from the catalog, will leave the shelf
* ``STEEP_MARKDOWN``— price trajectory points to a purge very soon

Signals are weighted into a 0-100 ``liquidation_score`` per item.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from . import DEFAULT_AGING_DAYS, PENNY_PRICE
from .models import InventoryItem
from .trajectory import Trajectory


class SignalKind(str, Enum):
    PENNY_PURGE = "penny_purge"
    CLEARANCE = "clearance"
    LAST_ITEM = "last_item"
    AGING = "aging"
    DISCONTINUED = "discontinued"
    STEEP_MARKDOWN = "steep_markdown"


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SIGNAL_META: dict[SignalKind, dict[str, Any]] = {
    SignalKind.PENNY_PURGE: {
        "label": "Penny purge ($0.01)",
        "severity": "critical",
        "weight": 40,
        "detail": "Priced at one cent — store is purging this item now.",
    },
    SignalKind.CLEARANCE: {
        "label": "Clearance rack",
        "severity": "high",
        "weight": 25,
        "detail": "Already moved to clearance — will be removed once sold through.",
    },
    SignalKind.LAST_ITEM: {
        "label": "Last one in stock",
        "severity": "high",
        "weight": 20,
        "detail": "Only a single unit left — shelf slot gets freed when it sells.",
    },
    SignalKind.AGING: {
        "label": "Shelf-sitter",
        "severity": "medium",
        "weight": 15,
        "detail": "Sitting on the shelf for a long time — prime liquidation candidate.",
    },
    SignalKind.DISCONTINUED: {
        "label": "Discontinued",
        "severity": "high",
        "weight": 15,
        "detail": "Discontinued SKU — store must take it off the shelves.",
    },
    SignalKind.STEEP_MARKDOWN: {
        "label": "Markdown trajectory",
        "severity": "medium",
        "weight": 20,
        "detail": "Price history projects a purge/clearance within ~2 weeks.",
    },
}


@dataclass
class Signal:
    kind: SignalKind
    label: str
    severity: str
    detail: str
    weight: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "severity": self.severity,
            "detail": self.detail,
            "weight": self.weight,
        }


def detect_signals(
    item: InventoryItem,
    today: date | None = None,
    aging_threshold_days: int = DEFAULT_AGING_DAYS,
    trajectory: Trajectory | None = None,
) -> list[Signal]:
    """Detect all liquidation signals for one item, most severe first."""
    today = today or date.today()
    signals: list[Signal] = []

    def add(kind: SignalKind) -> None:
        meta = SIGNAL_META[kind]
        signals.append(Signal(kind, meta["label"], meta["severity"], meta["detail"], meta["weight"]))

    if item.current_price <= PENNY_PRICE + 1e-9:
        add(SignalKind.PENNY_PURGE)
    if item.clearance:
        add(SignalKind.CLEARANCE)
    if item.quantity <= 1:
        add(SignalKind.LAST_ITEM)
    if item.days_on_shelf(today) >= aging_threshold_days:
        add(SignalKind.AGING)
    if item.discontinued:
        add(SignalKind.DISCONTINUED)
    if (
        trajectory is not None
        and trajectory.projected_penny_date is not None
        and (trajectory.projected_penny_date - today).days <= 14
        and trajectory.confidence >= 0.4
    ):
        add(SignalKind.STEEP_MARKDOWN)

    signals.sort(key=lambda s: (SEVERITY_ORDER[s.severity], -s.weight))
    return signals


def liquidation_score(
    signals: list[Signal], trajectory: Trajectory | None = None
) -> float:
    """Combine signal weights into a 0-100 liquidation likelihood score."""
    score = sum(s.weight for s in signals)
    if trajectory is not None and trajectory.confidence >= 0.4:
        # The more confident the falling price trajectory, the closer to purge.
        if trajectory.projected_penny_date is not None:
            score += 10 * trajectory.confidence
        if trajectory.days_until_sold_out is not None and trajectory.days_until_sold_out <= 7:
            score += 5
    return round(min(100.0, score), 1)


def annotate_item(
    item: InventoryItem,
    today: date | None = None,
    aging_threshold_days: int = DEFAULT_AGING_DAYS,
    trajectory: Trajectory | None = None,
) -> dict[str, Any]:
    """Full per-item analysis: model dict + signals + score + trajectory."""
    from .trajectory import fit_trajectory

    today = today or date.today()
    traj = trajectory or fit_trajectory(item, today)
    signals = detect_signals(item, today, aging_threshold_days, traj)
    data = item.to_dict(today)
    data["signals"] = [s.to_dict() for s in signals]
    data["liquidation_score"] = liquidation_score(signals, traj)
    data["trajectory"] = traj.to_dict()
    return data
