#!/usr/bin/env python
"""GamePulse demo seed script.

Runs the simulator with a larger, multi-persona workload designed to produce
realistic-looking charts for a presentation walkthrough.

Usage:
    python scripts/demo_seed.py [--api-url URL] [--api-key KEY] [--quick]

The --quick flag runs a shorter burst (30 s, 15 players) — useful when you
just want to check connectivity. The default runs a realistic 5-minute session
with 60 players across 4 personas.
"""
from __future__ import annotations

import argparse
import os
import sys

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.gamepulse_simulator.simulator.runner import run  # type: ignore[import]


def main() -> None:
    p = argparse.ArgumentParser(prog="demo_seed")
    p.add_argument("--api-url", default=os.environ.get("GAMEPULSE_API_URL", "http://localhost:8000"))
    p.add_argument("--api-key", default=os.environ.get("GAMEPULSE_API_KEY", "demo-key-please-rotate"))
    p.add_argument("--project", default=os.environ.get("GAMEPULSE_PROJECT_SLUG", "demo"))
    p.add_argument("--quick", action="store_true", help="Short 30-second burst with 15 players")
    args = p.parse_args()

    if args.quick:
        players, duration = 15, 30
    else:
        players, duration = 60, 300  # 5 minutes of realistic traffic

    print(f"[demo_seed] Starting: {players} players for {duration}s → {args.api_url}")
    print("[demo_seed] This will generate sessions, progression, economy, and crash events.")
    print("[demo_seed] Open the dashboard at http://localhost:8501 while this runs.\n")

    run(
        players=players,
        duration_s=duration,
        api_url=args.api_url,
        api_key=args.api_key,
        project=args.project,
    )
    print("\n[demo_seed] Done. Refresh the dashboard — all charts should now have data.")


if __name__ == "__main__":
    main()
