#!/usr/bin/env python3
"""Clearance Radar launcher.

Usage:
    python3 run.py [--host 0.0.0.0] [--port 8000]

Then open http://localhost:8000 in a browser. The app uses your browser
geolocation to find nearby stores (falls back to Santa Maria, CA).
"""

from __future__ import annotations

import argparse

from clearance_radar.server import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Clearance Radar — nearby liquidation finder")
    parser.add_argument("--host", default="0.0.0.0", help="bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="bind port (default: 8000)")
    args = parser.parse_args()
    run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
