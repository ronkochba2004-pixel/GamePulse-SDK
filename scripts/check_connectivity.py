#!/usr/bin/env python
"""Quick connectivity check for a GamePulse deployment.

Usage:
    python scripts/check_connectivity.py [--api-url URL] [--api-key KEY]

Returns exit code 0 if everything is reachable, 1 otherwise.
"""
from __future__ import annotations

import argparse
import os
import sys

import httpx


def check(api_url: str, api_key: str) -> bool:
    ok = True
    headers = {"X-GamePulse-Key": api_key}

    print(f"Checking API at {api_url} …")

    # Health
    try:
        r = httpx.get(f"{api_url}/healthz", timeout=5.0)
        if r.status_code == 200:
            print("  ✅ /healthz OK")
        else:
            print(f"  ❌ /healthz returned {r.status_code}")
            ok = False
    except Exception as e:
        print(f"  ❌ /healthz unreachable: {e}")
        return False

    # Auth
    try:
        r = httpx.get(f"{api_url}/v1/query/overview", headers=headers, timeout=5.0)
        if r.status_code == 200:
            totals = r.json().get("totals", {})
            print(f"  ✅ /v1/query/overview OK — {totals.get('sessions', 0)} sessions")
        elif r.status_code == 401:
            print(f"  ❌ /v1/query/overview: invalid API key ({api_key[:6]}…)")
            ok = False
        else:
            print(f"  ⚠ /v1/query/overview returned {r.status_code}: {r.text[:200]}")
            ok = False
    except Exception as e:
        print(f"  ❌ /v1/query/overview error: {e}")
        ok = False

    return ok


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--api-url", default=os.environ.get("GAMEPULSE_API_URL", "http://localhost:8000"))
    p.add_argument("--api-key", default=os.environ.get("GAMEPULSE_API_KEY", "demo-key-please-rotate"))
    args = p.parse_args()

    success = check(args.api_url, args.api_key)
    print("\nResult:", "✅ All good" if success else "❌ Issues found")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
