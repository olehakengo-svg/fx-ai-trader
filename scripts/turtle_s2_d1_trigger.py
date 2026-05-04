"""Trigger the web-process Turtle S2 D1 runner from Render cron."""
from __future__ import annotations

import json
import os
import sys
from urllib import error, request


def main() -> int:
    api_base = os.environ.get("API_BASE", "").rstrip("/")
    cron_secret = os.environ.get("CRON_SECRET", "")
    if not api_base:
        print("API_BASE is required", file=sys.stderr)
        return 2
    if not cron_secret:
        print("CRON_SECRET is required", file=sys.stderr)
        return 2

    req = request.Request(
        f"{api_base}/api/internal/turtle_s2_d1/run",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-Cron-Secret": cron_secret,
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            payload = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"turtle_s2_d1 trigger failed: {exc}", file=sys.stderr)
        return 1

    parsed = json.loads(payload)
    print(json.dumps(parsed, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
