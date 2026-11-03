"""Stdlib HTTP server exposing the Clearance Radar JSON API and web UI."""

from __future__ import annotations

import json
import re
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import DEFAULT_AGING_DAYS, DEFAULT_LOCATION, DEFAULT_RADIUS_KM, PENNY_PRICE, __version__
from .detector import SIGNAL_META
from .repository import Repository

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json",
}


def make_handler(repo: Repository, static_dir: Path = STATIC_DIR):
    """Build a request handler class bound to a repository."""

    class Handler(BaseHTTPRequestHandler):
        server_version = f"ClearanceRadar/{__version__}"

        # -- helpers ------------------------------------------------------
        def _json(self, payload, status: int = 200) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status: int, message: str) -> None:
            self._json({"error": message}, status)

        def _static(self, path: Path) -> None:
            try:
                resolved = (static_dir / path).resolve()
                resolved.relative_to(static_dir.resolve())
            except (ValueError, OSError):
                self._error(403, "forbidden")
                return
            if not resolved.is_file():
                self._error(404, "not found")
                return
            body = resolved.read_bytes()
            ctype = CONTENT_TYPES.get(resolved.suffix.lower(), "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _params(self, query: dict) -> dict:
            return {k: v[0] for k, v in query.items()}

        def _float(self, params: dict, key: str, default: float) -> float:
            try:
                return float(params.get(key, default))
            except (TypeError, ValueError):
                return default

        def log_message(self, fmt, *args):  # quieter logs
            pass

        # -- routing ------------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)
            params = self._params(query)
            today = date.today()

            if path == "/" or path == "/index.html":
                self._static(Path("index.html"))
                return
            if path.startswith("/static/"):
                self._static(Path(path[len("/static/"):]))
                return

            if path == "/api/health":
                self._json({"status": "ok", "version": __version__, "today": today.isoformat()})
                return

            if path == "/api/meta":
                self._json(
                    {
                        "version": __version__,
                        "penny_price": PENNY_PRICE,
                        "default_radius_km": DEFAULT_RADIUS_KM,
                        "aging_threshold_days": DEFAULT_AGING_DAYS,
                        "default_location": DEFAULT_LOCATION,
                        "signals": [
                            {"kind": k.value, **v} for k, v in SIGNAL_META.items()
                        ],
                    }
                )
                return

            if path == "/api/nearby":
                lat = self._float(params, "lat", DEFAULT_LOCATION["lat"])
                lon = self._float(params, "lon", DEFAULT_LOCATION["lon"])
                radius = self._float(params, "radius_km", DEFAULT_RADIUS_KM)
                if radius <= 0 or radius > 500:
                    self._error(400, "radius_km must be in (0, 500]")
                    return
                self._json(
                    {
                        "you": {"lat": lat, "lon": lon},
                        "radius_km": radius,
                        "store_count": len(repo.stores),
                        "stores": repo.nearby(lat, lon, radius, today),
                    }
                )
                return

            m = re.fullmatch(r"/api/stores/([\w-]+)", path)
            if m:
                detail = repo.store_detail(m.group(1), today)
                if detail is None:
                    self._error(404, "store not found")
                else:
                    self._json(detail)
                return

            m = re.fullmatch(r"/api/items/([\w-]+)", path)
            if m:
                detail = repo.item_detail(m.group(1), today)
                if detail is None:
                    self._error(404, "item not found")
                else:
                    self._json(detail)
                return

            if path == "/api/alerts":
                lat = self._float(params, "lat", DEFAULT_LOCATION["lat"])
                lon = self._float(params, "lon", DEFAULT_LOCATION["lon"])
                radius = self._float(params, "radius_km", DEFAULT_RADIUS_KM)
                min_score = self._float(params, "min_score", 60.0)
                alerts = repo.alerts(lat, lon, radius, min_score, today)
                self._json(
                    {
                        "you": {"lat": lat, "lon": lon},
                        "radius_km": radius,
                        "min_score": min_score,
                        "count": len(alerts),
                        "alerts": alerts,
                    }
                )
                return

            self._error(404, "not found")

    return Handler


def make_server(repo: Repository, host: str = "0.0.0.0", port: int = 8000) -> ThreadingHTTPServer:
    """Create (but do not start) the HTTP server."""
    server = ThreadingHTTPServer((host, port), make_handler(repo))
    server.daemon_threads = True
    return server


def run(host: str = "0.0.0.0", port: int = 8000, repo: Repository | None = None) -> None:
    from .seed import seed_repository

    repo = repo or Repository()
    seed_repository(repo)
    server = make_server(repo, host, port)
    print(f"Clearance Radar listening on http://{host}:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
