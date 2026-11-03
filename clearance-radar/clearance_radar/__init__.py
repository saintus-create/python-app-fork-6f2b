"""Clearance Radar — location-based liquidation & purge finder for retail stores.

Finds retail stores near a given location and intelligently flags inventory
that is being liquidated or pulled from shelves:

* penny purges (current price == $0.01)
* clearance-rack items
* last-one-in-stock items
* aging "shelf-sitter" items (on the shelf too long)
* discontinued items (will be taken off the shelves)

Each flagged item's price/stock history is turned into a *trajectory* that
projects when the item will hit the penny price or sell out.
"""

__version__ = "1.0.0"

PENNY_PRICE = 0.01
DEFAULT_RADIUS_KM = 25.0
DEFAULT_AGING_DAYS = 45

# Default reference location: Santa Maria, California, US.
DEFAULT_LOCATION = {"lat": 34.9530, "lon": -120.4357, "label": "Santa Maria, CA"}
