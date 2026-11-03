"""End-to-end tests for the HTTP API."""

import json
import threading
import unittest
import urllib.request
from datetime import date

from clearance_radar.repository import Repository
from clearance_radar.seed import seed_repository
from clearance_radar.server import make_server

TODAY = date.today()


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Repository()
        seed_repository(cls.repo, TODAY)
        cls.server = make_server(cls.repo, "127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        with urllib.request.urlopen(url, timeout=10) as res:
            return res.status, json.loads(res.read().decode())

    def get_error(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=10) as res:
                return res.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_health(self):
        status, body = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_meta(self):
        status, body = self.get("/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual(body["penny_price"], 0.01)
        kinds = {s["kind"] for s in body["signals"]}
        self.assertIn("penny_purge", kinds)
        self.assertIn("last_item", kinds)
        self.assertIn("aging", kinds)

    def test_nearby_default_location(self):
        status, body = self.get("/api/nearby?lat=34.9530&lon=-120.4357&radius_km=25")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(body["stores"]), 8)
        # sorted by distance
        dists = [s["distance_km"] for s in body["stores"]]
        self.assertEqual(dists, sorted(dists))
        # every store reports flagged counts
        self.assertTrue(all("flagged_count" in s for s in body["stores"]))
        # at least one penny purge in the demo data
        self.assertTrue(any("penny_purge" in s["signals"] for s in body["stores"]))

    def test_nearby_small_radius(self):
        status, body = self.get("/api/nearby?lat=34.9530&lon=-120.4357&radius_km=1")
        self.assertEqual(status, 200)
        self.assertLessEqual(len(body["stores"]), 3)

    def test_bad_radius_rejected(self):
        self.assertEqual(self.get_error("/api/nearby?lat=1&lon=1&radius_km=-5"), 400)

    def test_store_detail(self):
        status, body = self.get("/api/stores/target-sm")
        self.assertEqual(status, 200)
        self.assertEqual(body["id"], "target-sm")
        self.assertGreater(len(body["items"]), 0)
        top = body["items"][0]
        self.assertIn("liquidation_score", top)
        self.assertIn("trajectory", top)
        self.assertIn("signals", top)
        # sorted best-first
        scores = [i["liquidation_score"] for i in body["items"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_store_detail_404(self):
        self.assertEqual(self.get_error("/api/stores/nope"), 404)

    def test_item_detail(self):
        status, body = self.get("/api/items/target-sm-001")
        self.assertEqual(status, 200)
        self.assertEqual(body["current_price"], 0.01)
        kinds = {s["kind"] for s in body["signals"]}
        self.assertIn("penny_purge", kinds)
        self.assertIn("discontinued", kinds)
        self.assertIsNotNone(body["store"])

    def test_alerts(self):
        status, body = self.get("/api/alerts?lat=34.9530&lon=-120.4357&radius_km=25&min_score=60")
        self.assertEqual(status, 200)
        self.assertGreater(body["count"], 0)
        scores = [a["liquidation_score"] for a in body["alerts"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(s >= 60 for s in scores))

    def test_alerts_high_threshold(self):
        status, body = self.get("/api/alerts?lat=34.9530&lon=-120.4357&radius_km=25&min_score=95")
        self.assertEqual(status, 200)
        self.assertTrue(all(a["liquidation_score"] >= 95 for a in body["alerts"]))

    def test_index_served(self):
        url = f"http://127.0.0.1:{self.port}/"
        with urllib.request.urlopen(url, timeout=10) as res:
            html = res.read().decode()
        self.assertIn("Clearance Radar", html)

    def test_static_js_served(self):
        url = f"http://127.0.0.1:{self.port}/static/app.js"
        with urllib.request.urlopen(url, timeout=10) as res:
            self.assertIn("javascript", res.headers["Content-Type"])

    def test_path_traversal_blocked(self):
        self.assertIn(self.get_error("/static/../clearance_radar/server.py"), (403, 404))

    def test_unknown_api_404(self):
        self.assertEqual(self.get_error("/api/nope"), 404)


if __name__ == "__main__":
    unittest.main()
