"""Geographic helpers: haversine distance and radius search."""

from __future__ import annotations

import math

from .models import Store

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def find_nearby(
    stores: list[Store], lat: float, lon: float, radius_km: float
) -> list[tuple[Store, float]]:
    """Return ``(store, distance_km)`` pairs within ``radius_km``, nearest first."""
    hits = [
        (s, haversine_km(lat, lon, s.lat, s.lon))
        for s in stores
        if haversine_km(lat, lon, s.lat, s.lon) <= radius_km
    ]
    hits.sort(key=lambda pair: pair[1])
    return hits
