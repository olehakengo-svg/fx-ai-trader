#!/usr/bin/env python3
"""
Live Source Sanity Check — Render API vs local DB drift detection + orphan app.py guard.

Usage:
    python3 tools/check_live_source.py            # exit 0 if Render is reachable and
                                                  # local DB has no critical drift
    python3 tools/check_live_source.py --verbose  # show details of all checks
    python3 tools/check_live_source.py --no-render  # skip Render (offline mode)

Purpose:
    Audit 2026-05-01 (Pillar 3.0/3.7) revealed that analyses silently read a
    stale local demo_trades.db (Live N=36) instead of the authoritative Render
    API (Live N=309 at the time). CLAUDE.md `feedback_check_orphan_local_app.md`
    requires that any analysis path verify Render is the primary source and no
    local app.py orphan is contaminating the local DB.

Checks (in order):
    1. ORPHAN: `pgrep -f "python.* app.py"` finds no foreign Python processes
       running app.py on this machine (orphans corrupt local DB with phantom
       trades).
    2. RENDER REACHABLE: GET https://fx-ai-trader.onrender.com/api/risk/dashboard
       returns 200 and yields a numeric `n_total_trades`.
    3. LOCAL EXISTS: there is a non-empty demo_trades.db inside the repo, and
       not a stray 0-byte file at the repo parent that could be opened by
       mistake.
    4. DRIFT: |local_live_count - render_live_count| / render_live_count <= 5%.
       If exceeded, the local DB is too stale to inform any analysis and the
       caller should query Render directly.

Exit codes:
    0  All checks passed (or --no-render skipped item 2/4).
    1  ORPHAN detected.
    2  RENDER unreachable (no network / 5xx).
    3  LOCAL DB invalid (missing / 0-byte / stray sibling).
    4  DRIFT > 5% (local DB stale; do NOT use for analysis).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DB = os.path.join(REPO_ROOT, "demo_trades.db")
PARENT_STRAY_DB = os.path.join(os.path.dirname(REPO_ROOT), "demo_trades.db")
_RENDER_BASE_RAW = os.environ.get("RENDER_PUBLIC_URL", "https://fx-ai-trader.onrender.com").rstrip("/")
RENDER_TIMEOUT_S = float(os.environ.get("RENDER_CHECK_TIMEOUT", "15"))
DRIFT_THRESHOLD = 0.05  # 5%


def _safe_render_base(raw: str) -> str:
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise SystemExit(
            f"refusing to use RENDER_PUBLIC_URL={raw!r}: only http(s) schemes allowed"
        )
    if not parsed.netloc:
        raise SystemExit(f"refusing to use RENDER_PUBLIC_URL={raw!r}: missing host")
    return raw


RENDER_BASE = _safe_render_base(_RENDER_BASE_RAW)


def check_orphan(verbose: bool) -> tuple[bool, str]:
    try:
        out = subprocess.run(
            ["pgrep", "-fa", "python.* app.py"],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return True, f"pgrep unavailable ({e}); skipping orphan check"
    procs = [line for line in (out.stdout or "").strip().splitlines() if line]
    procs = [p for p in procs if "check_live_source" not in p]
    if procs:
        return False, "ORPHAN app.py processes found:\n  " + "\n  ".join(procs)
    return True, "no orphan app.py processes"


_HTTP_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(),
)
_HTTP_OPENER.addheaders = [("User-Agent", "check_live_source/1.0")]


def check_render(verbose: bool) -> tuple[bool, dict | None, str]:
    url = f"{RENDER_BASE}/api/risk/dashboard"
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, None, f"refusing non-http(s) URL: {url}"
    try:
        # Opener has only HTTP/HTTPS handlers installed; file://, ftp://,
        # data:// etc. are rejected before the request is dispatched. The
        # explicit prefix check above also makes the intent obvious to
        # static analyzers (semgrep CWE-939).
        with _HTTP_OPENER.open(url, timeout=RENDER_TIMEOUT_S) as resp:  # noqa: S310 - validated above
            if resp.status != 200:
                return False, None, f"Render {url} returned HTTP {resp.status}"
            data = json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
        return False, None, f"Render unreachable: {e}"
    n = data.get("n_total_trades")
    if not isinstance(n, int):
        return False, None, f"Render dashboard missing n_total_trades (got {n!r})"
    return True, data, f"Render OK, n_total_trades={n}"


def check_local_db(verbose: bool) -> tuple[bool, str]:
    if os.path.exists(PARENT_STRAY_DB):
        sz = os.path.getsize(PARENT_STRAY_DB)
        if sz == 0:
            return False, (
                f"stray 0-byte demo_trades.db at {PARENT_STRAY_DB}; "
                "may be opened by mistake if CWD is wrong. Delete it."
            )
    if not os.path.exists(LOCAL_DB):
        return False, f"local DB not found at {LOCAL_DB}"
    if os.path.getsize(LOCAL_DB) == 0:
        return False, f"local DB at {LOCAL_DB} is 0 bytes"
    return True, f"local DB OK ({os.path.getsize(LOCAL_DB)} bytes)"


def count_local_live() -> int:
    conn = sqlite3.connect(LOCAL_DB)
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM demo_trades "
            "WHERE status='CLOSED' AND (is_shadow IS NULL OR is_shadow=0)"
        )
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def check_drift(local_n: int, render_n: int) -> tuple[bool, str]:
    if render_n == 0:
        return True, "Render reports 0 trades; drift undefined"
    drift = abs(local_n - render_n) / render_n
    msg = f"local Live={local_n}, Render Live={render_n}, drift={drift*100:.1f}%"
    if drift > DRIFT_THRESHOLD:
        return False, (
            f"DRIFT {drift*100:.1f}% > {DRIFT_THRESHOLD*100:.0f}% — "
            "local DB is stale, do NOT use for analysis. " + msg
        )
    return True, msg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-render", action="store_true",
                    help="skip Render reachability and drift checks (offline)")
    args = ap.parse_args()

    print(f"[check_live_source] repo={REPO_ROOT}")
    print(f"[check_live_source] local={LOCAL_DB}")
    print(f"[check_live_source] render={RENDER_BASE}")

    ok, msg = check_orphan(args.verbose)
    print(f"[1/4] orphan: {'OK' if ok else 'FAIL'} — {msg}")
    if not ok:
        return 1

    ok, msg = check_local_db(args.verbose)
    print(f"[2/4] local-db: {'OK' if ok else 'FAIL'} — {msg}")
    if not ok:
        return 3

    if args.no_render:
        print("[3/4] render: SKIPPED (--no-render)")
        print("[4/4] drift: SKIPPED (--no-render)")
        return 0

    ok, render_data, msg = check_render(args.verbose)
    print(f"[3/4] render: {'OK' if ok else 'FAIL'} — {msg}")
    if not ok:
        return 2

    render_n = int(render_data["n_total_trades"])
    try:
        local_n = count_local_live()
    except sqlite3.Error as e:
        print(f"[4/4] drift: FAIL — local DB query error: {e}")
        return 3
    ok, msg = check_drift(local_n, render_n)
    print(f"[4/4] drift: {'OK' if ok else 'FAIL'} — {msg}")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
