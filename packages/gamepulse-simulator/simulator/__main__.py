from __future__ import annotations

import argparse
import os

from simulator.runner import run


def main() -> None:
    p = argparse.ArgumentParser(prog="simulator")
    p.add_argument("--players", type=int, default=10)
    p.add_argument("--duration", type=int, default=60, help="seconds")
    p.add_argument("--api-url", default=os.environ.get("GAMEPULSE_API_URL", "http://localhost:8000"))
    p.add_argument("--api-key", default=os.environ.get("GAMEPULSE_API_KEY", "demo-key-please-rotate"))
    p.add_argument("--project", default=os.environ.get("GAMEPULSE_PROJECT_SLUG", "demo"))
    args = p.parse_args()
    run(args.players, args.duration, args.api_url, args.api_key, args.project)


if __name__ == "__main__":
    main()
