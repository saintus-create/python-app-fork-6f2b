"""Demo dataset: retail stores around Santa Maria, California.

Histories are generated relative to ``today`` so aging / trajectory math
always behaves realistically, no matter when the app is run.

In production these rows would come from store inventory feeds / scrapers;
the data model and detectors are feed-agnostic.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from .models import InventoryItem, PricePoint, Store, StockPoint

RNG = random.Random(20261103)

STORES: list[Store] = [
    Store("target-sm", "Target", "Target", "3350 S College Dr", "Santa Maria", "CA", 34.9446, -120.4560, "805-555-0141"),
    Store("walmart-sm", "Walmart Supercenter", "Walmart", "2255 S Bradley Rd", "Santa Maria", "CA", 34.9250, -120.4400, "805-555-0177"),
    Store("costco-sm", "Costco Wholesale", "Costco", "2055 W Clark Ave", "Santa Maria", "CA", 34.9180, -120.4500, "805-555-0122"),
    Store("homedepot-sm", "The Home Depot", "Home Depot", "1750 N College Dr", "Santa Maria", "CA", 34.9365, -120.4425, "805-555-0163"),
    Store("lowes-sm", "Lowe's Home Improvement", "Lowe's", "3601 S Broadway", "Santa Maria", "CA", 34.9120, -120.4600, "805-555-0188"),
    Store("bestbuy-sm", "Best Buy", "Best Buy", "3405 S College Dr", "Santa Maria", "CA", 34.9410, -120.4580, "805-555-0134"),
    Store("tjmaxx-sm", "T.J. Maxx", "T.J. Maxx", "3400 S College Dr", "Santa Maria", "CA", 34.9455, -120.4570, "805-555-0119"),
    Store("ross-sm", "Ross Dress for Less", "Ross", "3420 S College Dr", "Santa Maria", "CA", 34.9448, -120.4585, "805-555-0152"),
    Store("groceryoutlet-sm", "Grocery Outlet", "Grocery Outlet", "1650 E Betteravia Rd", "Santa Maria", "CA", 34.9390, -120.4520, "805-555-0171"),
    Store("big5-sm", "Big 5 Sporting Goods", "Big 5", "2210 S Broadway", "Santa Maria", "CA", 34.9500, -120.4350, "805-555-0108"),
]

# (name, category, original_price, current_price, quantity, days_on_shelf,
#  clearance, discontinued, history_kind)
# history_kind: "markdown" (steady weekly markdowns), "flat" (no movement),
# "penny" (dropped to $0.01), "cliff" (sudden deep cut at the end)
ITEM_TEMPLATES: dict[str, list[tuple]] = {
    "target-sm": [
        ("55\" TCL 4K Roku Smart TV (2023 model)", "Electronics", 449.99, 0.01, 3, 210, False, True, "penny"),
        ("Threshold™ patio umbrella, 9 ft", "Patio", 89.99, 26.99, 1, 160, True, False, "markdown"),
        ("Goodfellow™ 6-ft folding table", "Furniture", 59.99, 17.99, 4, 140, True, False, "markdown"),
        ("Room Essentials™ throw blanket", "Home", 12.99, 3.89, 22, 95, False, False, "markdown"),
        ("Segway Ninebot e-scooter (open box)", "Sporting", 329.99, 148.99, 2, 60, True, False, "cliff"),
        ("Kids' LEGO-compatible brick set 500 pc", "Toys", 24.99, 9.99, 8, 40, False, False, "markdown"),
        ("Hearth & Hand™ ceramic vase, retired color", "Home", 19.99, 5.99, 6, 120, False, True, "markdown"),
    ],
    "walmart-sm": [
        ("Onn. 50\" Class 4K UHD Roku Smart TV", "Electronics", 268.00, 0.01, 2, 190, False, True, "penny"),
        ("Hyper Tough 20V drill/driver kit", "Tools", 79.88, 23.96, 1, 75, True, False, "markdown"),
        ("Mainstays 10-piece cookware set", "Kitchen", 49.97, 14.99, 5, 110, True, False, "markdown"),
        ("Ozark Trail 6-person tent (last season)", "Outdoors", 89.00, 35.60, 3, 150, True, False, "markdown"),
        ("Great Value organic honey 24 oz", "Grocery", 8.48, 4.24, 30, 25, False, False, "flat"),
        ("Better Living 12\" air fryer", "Appliances", 39.99, 15.99, 7, 80, False, False, "markdown"),
    ],
    "costco-sm": [
        ("Casper Queen mattress (floor model)", "Furniture", 1499.00, 599.00, 1, 90, True, False, "cliff"),
        ("Kirkland Signature 65\" 4K TV (2022)", "Electronics", 649.99, 0.01, 1, 240, False, True, "penny"),
        ("Webber Genesis 3-burner grill (display)", "Patio", 499.00, 199.00, 2, 130, True, False, "markdown"),
        ("Kirkland down-alternative comforter", "Bedding", 49.99, 24.99, 12, 30, False, False, "flat"),
    ],
    "homedepot-sm": [
        ("Ryobi 18V ONE+ drill + 2 batteries", "Tools", 129.00, 0.01, 4, 180, False, True, "penny"),
        ("Husky 26 in. tool cabinet (scratched)", "Storage", 298.00, 119.00, 1, 100, True, False, "markdown"),
        ("TrafficMaster LifeProof LVP flooring, per plank closeout", "Flooring", 3.99, 0.99, 40, 220, True, False, "markdown"),
        ("Home Decorators ceiling fan, oil-rubbed bronze", "Lighting", 119.00, 47.60, 6, 85, False, False, "markdown"),
        ("EGO 56V string trimmer (discontinued model)", "Outdoor Power", 249.00, 99.00, 3, 160, False, True, "cliff"),
    ],
    "lowes-sm": [
        ("Samsung 65\" Crystal UHD TV (2023, discontinued)", "Electronics", 547.98, 0.01, 2, 200, False, True, "penny"),
        ("Kobalt 24V cordless combo kit", "Tools", 149.00, 59.00, 1, 70, True, False, "markdown"),
        ("Style Selections 8-ft patio pergola (floor model)", "Patio", 899.00, 359.00, 1, 140, True, False, "cliff"),
        ("allen + roth bathroom vanity 36\"", "Bath", 449.00, 179.00, 4, 110, True, False, "markdown"),
        ("Project Source LED shop light 4 ft", "Lighting", 34.98, 13.99, 15, 50, False, False, "flat"),
    ],
    "bestbuy-sm": [
        ("Insignia™ 32\" Fire TV (2021 model)", "TV & Audio", 119.99, 0.01, 5, 230, False, True, "penny"),
        ("Sony WH-CH520 headphones (open box)", "Audio", 49.99, 19.99, 1, 45, True, False, "cliff"),
        ("LG 27\" UltraGear gaming monitor (display)", "Computing", 249.99, 129.99, 2, 95, True, False, "markdown"),
        ("RCA tablet 10\" Android (refurb)", "Computing", 89.99, 35.99, 6, 130, False, True, "markdown"),
        ("KitchenAid hand mixer, Empire Red", "Appliances", 49.99, 29.99, 9, 20, False, False, "flat"),
    ],
    "tjmaxx-sm": [
        (" Calvin Klein down jacket, last season", "Apparel", 179.00, 0.01, 1, 175, True, False, "penny"),
        ("Steve Madden leather ankle boots 7.5", "Shoes", 99.99, 39.99, 1, 90, True, False, "markdown"),
        ("Kate Spade wallet (discontinued style)", "Accessories", 75.00, 29.99, 3, 140, False, True, "markdown"),
        ("Betsey Johnson floral midi dress", "Apparel", 69.00, 27.60, 8, 60, False, False, "markdown"),
    ],
    "ross-sm": [
        ("Nike running shoes, retired colorway", "Shoes", 89.97, 0.01, 2, 160, True, True, "penny"),
        ("Champion reverse-weave hoodie", "Apparel", 49.99, 19.99, 1, 100, True, False, "markdown"),
        ("Adidas kids' sneakers size 12", "Shoes", 39.99, 15.99, 4, 120, True, False, "markdown"),
        ("L.O.L. Surprise! doll 4-pack", "Toys", 12.99, 4.99, 20, 35, False, False, "flat"),
    ],
    "groceryoutlet-sm": [
        ("KIND protein bars variety pack (close-dated)", "Grocery", 17.99, 0.01, 12, 150, True, False, "penny"),
        ("Oatly oat milk 64 oz (overstock)", "Grocery", 5.49, 2.19, 40, 10, False, False, "flat"),
        (" Dave's Killer Bread, best-by this week", "Bakery", 5.99, 0.01, 25, 60, True, False, "penny"),
        ("Kerrygold butter 8 oz", "Dairy", 4.99, 2.49, 18, 15, False, False, "flat"),
    ],
    "big5-sm": [
        ("Dick's Sporting-style fishing rod combo (their brand)", "Fishing", 59.99, 0.01, 1, 200, False, True, "penny"),
        ("Coleman 4-person tent (2024 floor model)", "Camping", 129.99, 51.99, 2, 170, True, False, "markdown"),
        ("Under Armour kids' cleats size 3", "Athletic Shoes", 44.99, 17.99, 1, 85, True, False, "markdown"),
        ("Wilson Evolution basketball (indoor/outdoor)", "Sports", 29.99, 14.99, 10, 30, False, False, "flat"),
    ],
}


def _history(kind: str, original: float, current: float, days: int, today: date) -> tuple[list[PricePoint], list[StockPoint]]:
    """Build a plausible weekly price/stock history ending at ``current``."""
    weeks = max(2, days // 7)
    prices: list[PricePoint] = []
    stocks: list[StockPoint] = []
    start_qty = RNG.randint(8, 30)
    for w in range(weeks + 1):
        d = today - timedelta(days=days - 7 * w)
        if kind == "flat":
            price = original
        elif kind == "penny":
            # sat at full price, then a mid markdown, then the penny purge
            if w >= weeks:
                price = current
            elif w >= weeks - 2:
                price = original * 0.4
            else:
                price = original
        elif kind == "cliff":
            price = original if w < weeks - 1 else current
        else:  # markdown: steady geometric slide from original to current
            if weeks == 0:
                price = current
            else:
                frac = w / weeks
                price = original * (1 - frac) + current * frac
                price = round(price + RNG.uniform(-1.5, 1.5), 2)
        price = max(0.01, round(price, 2))
        qty = max(1, start_qty - w * max(1, (start_qty - 1) // weeks) + RNG.randint(-1, 1))
        prices.append(PricePoint(d, price))
        stocks.append(StockPoint(d, qty))
    # Ensure the last observation matches the item's current state.
    prices[-1] = PricePoint(today, round(current, 2))
    stocks[-1] = StockPoint(today, max(1, min(stocks[-1].quantity, 60)))
    return prices, stocks


def build_items(today: date | None = None) -> list[InventoryItem]:
    """Build the full demo inventory for all stores."""
    today = today or date.today()
    items: list[InventoryItem] = []
    for store in STORES:
        for i, tpl in enumerate(ITEM_TEMPLATES[store.id]):
            name, category, original, current, qty, days, clearance, discontinued, kind = tpl
            prices, stocks = _history(kind, original, current, days, today)
            items.append(
                InventoryItem(
                    sku=f"{store.id}-{i + 1:03d}",
                    store_id=store.id,
                    name=name.strip(),
                    category=category,
                    current_price=current,
                    original_price=original,
                    quantity=qty,
                    listed_date=today - timedelta(days=days),
                    clearance=clearance,
                    discontinued=discontinued,
                    price_history=prices,
                    stock_history=stocks,
                )
            )
    return items


def seed_repository(repo, today: date | None = None) -> None:
    """Populate a repository with the demo dataset."""
    today = today or date.today()
    for store in STORES:
        repo.add_store(store)
    for item in build_items(today):
        repo.add_item(item)
