# Clearance Radar 📡

A self-contained, **zero-dependency** Python web app that answers:

> "Which retail stores are near me, and which of their products are being
> liquidated or taken off the shelves right now?"

It detects the classic liquidation signals:

| Signal | Meaning |
|---|---|
| 🟥 **Penny purge ($0.01)** | Priced at one cent — purged from the shelf now |
| 🟧 **Clearance rack** | Already marked down to clear |
| 🟧 **Last one in stock** | Quantity = 1 — slot frees up when it sells |
| 🟨 **Shelf-sitter (aging)** | On the shelf longer than the aging threshold (45 d) |
| 🟧 **Discontinued** | Pulled from the catalog — must leave the shelf |
| 🟨 **Markdown trajectory** | Price history projects a purge within ~2 weeks |

…and turns each item's **price & stock history into a trajectory**: a
least-squares fit that projects **when the price will hit $0.01**, when it
crosses 50% off, and **how many days of stock remain** — with a confidence
score from the fit quality (R² × sample size).

## Run it

```bash
cd clearance-radar
python3 run.py --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

The UI uses your browser's geolocation ("📍 Use my location") and falls back
to Santa Maria, CA. Adjust the radius slider or type coordinates manually.

## JSON API

| Endpoint | Description |
|---|---|
| `GET /api/health` | Liveness + version |
| `GET /api/meta` | Signal legend, thresholds, default location |
| `GET /api/nearby?lat=&lon=&radius_km=` | Stores within radius, nearest first, with flagged-item counts |
| `GET /api/stores/{id}` | Store detail: every item with signals, score, trajectory |
| `GET /api/items/{sku}` | One item: full analysis + store info |
| `GET /api/alerts?lat=&lon=&radius_km=&min_score=60` | High-likelihood liquidation feed, best first |

Example:

```bash
curl 'http://localhost:8000/api/alerts?lat=34.9530&lon=-120.4357&radius_km=25&min_score=60'
```

## Architecture

```
clearance-radar/
├── run.py                    # launcher (stdlib only)
├── clearance_radar/
│   ├── models.py             # Store / InventoryItem / PricePoint / StockPoint
│   ├── geo.py                # haversine + radius search
│   ├── detector.py           # liquidation signals + 0-100 score
│   ├── trajectory.py         # regression -> purge-date & sell-out projections
│   ├── repository.py         # queries: nearby / store detail / alerts
│   ├── seed.py               # demo dataset (stores around Santa Maria, CA)
│   └── server.py             # stdlib HTTP server + JSON API + static UI
├── static/                   # single-page UI (geolocation, sparklines, filters)
└── tests/                    # unittest suite (also runs under pytest)
```

The data layer is feed-agnostic: `seed.py` ships a demo dataset, but any
store inventory feed (scraper, POS export, partner API) can be loaded into
the same `Repository` and the detectors/trajectories work unchanged.

## Tests

```bash
cd clearance-radar
python3 -m unittest discover -s tests -v    # or: pytest tests/
```
