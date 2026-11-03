"""Tests for geo helpers."""

import unittest

from clearance_radar.geo import find_nearby, haversine_km
from clearance_radar.models import Store


class TestHaversine(unittest.TestCase):
    def test_zero_distance(self):
        self.assertAlmostEqual(haversine_km(34.953, -120.4357, 34.953, -120.4357), 0.0)

    def test_known_distance_santa_maria_to_lompoc(self):
        # Santa Maria, CA -> Lompoc, CA great-circle distance is ~35 km.
        d = haversine_km(34.9530, -120.4357, 34.6392, -120.4579)
        self.assertGreater(d, 30.0)
        self.assertLess(d, 40.0)

    def test_symmetric(self):
        a = haversine_km(34.953, -120.4357, 40.7128, -74.006)
        b = haversine_km(40.7128, -74.006, 34.953, -120.4357)
        self.assertAlmostEqual(a, b, places=6)


class TestFindNearby(unittest.TestCase):
    def setUp(self):
        self.stores = [
            Store("a", "A", "chain", "1 Main St", "Santa Maria", "CA", 34.9530, -120.4357),
            Store("b", "B", "chain", "2 Main St", "Santa Maria", "CA", 34.9600, -120.4400),
            Store("c", "C", "chain", "3 Main St", "Orcutt", "CA", 34.8000, -120.3500),
        ]

    def test_radius_filter_and_sorting(self):
        hits = find_nearby(self.stores, 34.9530, -120.4357, 5.0)
        ids = [s.id for s, _ in hits]
        self.assertEqual(ids, ["a", "b"])  # nearest first, c is outside radius
        self.assertLessEqual(hits[0][1], hits[1][1])

    def test_empty_when_nothing_in_range(self):
        hits = find_nearby(self.stores, 40.7128, -74.006, 5.0)
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
