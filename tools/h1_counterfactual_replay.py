#!/usr/bin/env python3
"""H-1 Hour-Bucket Counterfactual Replay Tool (W2-4, 2026-05-03).

Reads closed trades from a snapshot source (Render API JSON dump or local
demo_trades.db), applies the H1 hour-bucket promotion gate hypothetically,
and reports how each (strategy, instrument, hour_bucket) cell's verdict
would change.

Spec: wiki/learning/h1-hour-bucket-design-2026-05-03.md
Parent audit: wiki/learning/h1-spread-time-audit-2026-05-03.md

Usage:
    python tools/h1_counterfactual_replay.py \\
        --source local --db demo_trades.db --output raw/h1_replay.md
    python tools/h1_counterfactual_replay.py \\
        --source render-dump --json /path/to/trades.json \\
        --output raw/h1_replay.md
    python tools/h1_counterfactual_replay.py \\
        --source render --base-url https://fx-ai-trader.onrender.com

This tool **never modifies** the database or _promoted_types — it is purely
a counterfactual report. Use for pre-impl verification (per spec section
"必須事前検証") and for A/B baseline reporting.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy-import config so the tool can run from a checkout without app deps.
try:
    from modules import config as _cfg
    HOUR_TO_BUCKET = _cfg.hour_to_bucket
    UTC_HOUR = _cfg.utc_hour_from_iso
    H1_BUCKET_N_MIN = _cfg.H1_BUCKET_N_MIN
    H1_BUCKET_N_MIN_SHADOW = _cfg.H1_BUCKET_N_MIN_SHADOW
    H1_BUCKET_WILSON_MIN = _cfg.H1_BUCKET_WILSON_MIN
    H1_BUCKET_EV_MIN_PIP = _cfg.H1_BUCKET_EV_MIN_PIP
    H1_GRANDFATHERED_LIVE = _cfg.H1_GRANDFATHERED_LIVE
except Exception:  # fallback constants
    HOUR_TO_BUCKET = None
    UTC_HOUR = None
    H1_BUCKET_N_MIN = 30
    H1_BUCKET_N_MIN_SHADOW = 20
    H1_BUCKET_WILSON_MIN = 0.40
    H1_BUCKET_EV_MIN_PIP = -0.5
    H1_GRANDFATHERED_LIVE = frozenset({"bb_rsi_reversion"})


def _utc_hour(iso_ts: str) -> int | None:
    if UTC_HOUR is not None:
        return UTC_HOUR(iso_ts)
    if not iso_ts:
        return None
    try:
        return datetime.fromisoformat(iso_ts).hour
    except Exception:
        return None


def _bucket(hr: int | None, mode: str = "4_bucket") -> str | None:
    if hr is None:
        return None
    if HOUR_TO_BUCKET is not None:
        return HOUR_TO_BUCKET(hr, mode)
    if mode == "24_bucket":
        return f"H{hr:02d}"
    if 0 <= hr < 6:
        return "A_00-05"
    if 6 <= hr < 12:
        return "B_06-11"
    if 12 <= hr < 18:
        return "C_12-17"
    if 18 <= hr < 24:
        return "D_18-23"
    return None


def _wilson_bf_lower(wins: int, n: int, z: float = 3.29) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / den)


def _decide(cell: dict, current: str, grandfathered: bool) -> tuple[str, str]:
    """Replicate DemoTrader._decide_hour_bucket_action with gate forced ON."""
    if grandfathered:
        return current, "grandfather"
    n_min = H1_BUCKET_N_MIN if current == "live" else H1_BUCKET_N_MIN_SHADOW
    if cell["n"] < n_min:
        return current, "n_below_min"
    if (cell["wilson_lo"] > H1_BUCKET_WILSON_MIN
            and cell["ev"] > H1_BUCKET_EV_MIN_PIP):
        return current, "bucket_pass"
    if current == "live":
        return "shadow", "bucket_fail_demote_to_shadow"
    if current in ("shadow", "pending"):
        return "demoted", "bucket_fail_demote_from_shadow"
    return current, "already_demoted"


# ─────────────────────────────────────────────────────────────────────────
# Source loaders
# ─────────────────────────────────────────────────────────────────────────

def load_local(db_path: str) -> list[dict]:
    """Load CLOSED trades from local SQLite."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT entry_type, instrument, entry_time, pnl_pips, outcome,
                  is_shadow
           FROM demo_trades
           WHERE UPPER(status)='CLOSED'"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_render_dump(json_path: str) -> list[dict]:
    """Load from a JSON dump (e.g. saved /api/demo/trades response)."""
    with open(json_path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        rows = data.get("trades") or data.get("data") or []
    else:
        rows = data
    return [r for r in rows if (r.get("status") or "").upper() == "CLOSED"]


def load_render_api(base_url: str, limit: int = 50000) -> list[dict]:
    """Fetch directly from Render API (no auth — public endpoint).

    Security: uses ``requests`` (which only supports http/https schemes,
    closing the urllib file:// SSRF vector) and validates the parsed
    scheme before issuing the request.
    """
    import requests
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Refusing to fetch — only http/https scheme allowed, "
            f"got {parsed.scheme!r}"
        )
    if not parsed.netloc:
        raise ValueError(f"Invalid base_url (no host): {base_url!r}")
    url = f"{base_url.rstrip('/')}/api/demo/trades"
    resp = requests.get(url, params={"limit": int(limit)}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        rows = data.get("trades") or data.get("data") or []
    else:
        rows = data
    return [r for r in rows if (r.get("status") or "").upper() == "CLOSED"]


# ─────────────────────────────────────────────────────────────────────────
# Aggregation
# ─────────────────────────────────────────────────────────────────────────

def aggregate(rows: list[dict], bucket_mode: str = "4_bucket") -> dict:
    """Aggregate trades into (strategy, instrument, bucket, is_shadow) cells."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        et = r.get("entry_type")
        inst = r.get("instrument")
        if not et or not inst:
            continue
        hr = _utc_hour(r.get("entry_time"))
        bk = _bucket(hr, bucket_mode)
        if bk is None:
            continue
        is_shadow = int(r.get("is_shadow") or 0)
        cells[(et, inst, bk, is_shadow)].append(r)

    summary = {}
    for key, group in cells.items():
        n = len(group)
        wins = sum(1 for g in group if (g.get("outcome") or "") == "WIN")
        ev = sum((g.get("pnl_pips") or 0.0) for g in group) / n
        wL = _wilson_bf_lower(wins, n)
        summary[key] = {
            "n": n, "wins": wins,
            "wr": round(100.0 * wins / n, 1),
            "ev": round(ev, 3),
            "wilson_lo": round(wL, 4),
        }
    return summary


# ─────────────────────────────────────────────────────────────────────────
# Replay
# ─────────────────────────────────────────────────────────────────────────

def replay(cells: dict, current_promotions: dict | None = None) -> list[dict]:
    """Run the H1 gate against each cell. Returns a list of decisions.

    current_promotions: optional {entry_type: "promoted"|"demoted"|"pending"}.
    If absent, infer from is_shadow flag in the cell key (is_shadow=0 → live,
    is_shadow=1 → shadow).
    """
    rows = []
    for (et, inst, bk, is_shadow), stats in cells.items():
        if current_promotions:
            cur_status = current_promotions.get(et, "pending")
            current = ("live" if cur_status == "promoted"
                       else cur_status)
        else:
            current = "live" if is_shadow == 0 else "shadow"
        grand = (et in H1_GRANDFATHERED_LIVE) or (current == "live"
                                                   and current_promotions
                                                   is None
                                                   and is_shadow == 0)
        new, reason = _decide(stats, current, grand)
        rows.append({
            "entry_type": et, "instrument": inst, "bucket": bk,
            "is_shadow": is_shadow,
            "n": stats["n"], "wr": stats["wr"], "ev": stats["ev"],
            "wilson_lo": stats["wilson_lo"],
            "current": current, "new": new, "reason": reason,
            "grandfathered": grand,
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────

def render_report(decisions: list[dict], n_total_rows: int,
                  source_label: str, bucket_mode: str) -> str:
    out = []
    out.append("# H-1 Hour-Bucket Counterfactual Replay Report")
    out.append("")
    out.append(f"- **Generated**: {datetime.utcnow().isoformat()}Z")
    out.append(f"- **Source**: {source_label}")
    out.append(f"- **Bucket mode**: {bucket_mode}")
    out.append(f"- **Total closed rows**: {n_total_rows}")
    out.append(f"- **Cells evaluated**: {len(decisions)}")
    out.append(f"- **Gate params**: N_min(live)={H1_BUCKET_N_MIN}, "
               f"N_min(shadow)={H1_BUCKET_N_MIN_SHADOW}, "
               f"wilson_lo>{H1_BUCKET_WILSON_MIN}, "
               f"ev>{H1_BUCKET_EV_MIN_PIP}pip")
    out.append("")

    by_verdict = defaultdict(int)
    for d in decisions:
        by_verdict[d["reason"]] += 1
    out.append("## Verdict distribution")
    out.append("")
    out.append("| Verdict | Count |")
    out.append("|---|--:|")
    for k, v in sorted(by_verdict.items(), key=lambda x: -x[1]):
        out.append(f"| {k} | {v} |")
    out.append("")

    # Cells that would change tier
    changed = [d for d in decisions if d["new"] != d["current"]]
    out.append(f"## Cells that would change tier ({len(changed)})")
    out.append("")
    if changed:
        out.append("| Strategy | Instrument | Bucket | is_shadow | "
                   "N | WR% | EV pip | Wilson_lo | Current → New | Reason |")
        out.append("|---|---|---|--:|--:|--:|--:|--:|---|---|")
        for d in sorted(changed,
                         key=lambda r: (r["entry_type"], r["instrument"],
                                        r["bucket"])):
            out.append(
                f"| {d['entry_type']} | {d['instrument']} | {d['bucket']} | "
                f"{d['is_shadow']} | {d['n']} | {d['wr']} | {d['ev']:+.2f} | "
                f"{d['wilson_lo']:.3f} | {d['current']} → {d['new']} | "
                f"{d['reason']} |"
            )
    else:
        out.append("(none)")
    out.append("")

    # LIVE strategy summary (grandfather check)
    live_changed = [d for d in changed if d["current"] == "live"
                     and not d["grandfathered"]]
    out.append("## LIVE strategy regression check")
    out.append("")
    if live_changed:
        out.append(f"⚠️ **{len(live_changed)} non-grandfathered LIVE cells would demote** — "
                   "review before enabling gate.")
        for d in live_changed:
            out.append(
                f"- {d['entry_type']} × {d['instrument']} × {d['bucket']}: "
                f"N={d['n']} WR={d['wr']}% EV={d['ev']:+.2f} → {d['new']}"
            )
    else:
        out.append("✓ No non-grandfathered LIVE cells would demote.")
    out.append("")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", choices=("local", "render-dump", "render"),
                   default="local")
    p.add_argument("--db", default="demo_trades.db",
                   help="Path to local SQLite DB (source=local)")
    p.add_argument("--json", help="Render API JSON dump (source=render-dump)")
    p.add_argument("--base-url", default="https://fx-ai-trader.onrender.com",
                   help="Render base URL (source=render)")
    p.add_argument("--bucket-mode", choices=("4_bucket", "24_bucket"),
                   default="4_bucket")
    p.add_argument("--output", default="-",
                   help="Markdown output path, or - for stdout")
    p.add_argument("--current-promotions",
                   help="Optional JSON {strategy: promoted|demoted|pending}")
    args = p.parse_args(argv)

    if args.source == "local":
        rows = load_local(args.db)
        src_label = f"local SQLite ({args.db})"
    elif args.source == "render-dump":
        if not args.json:
            p.error("--json required when source=render-dump")
        rows = load_render_dump(args.json)
        src_label = f"Render JSON dump ({args.json})"
    else:
        rows = load_render_api(args.base_url)
        src_label = f"Render API ({args.base_url})"

    cur_promo = None
    if args.current_promotions:
        with open(args.current_promotions) as f:
            cur_promo = json.load(f)

    cells = aggregate(rows, bucket_mode=args.bucket_mode)
    decisions = replay(cells, current_promotions=cur_promo)
    report = render_report(decisions, len(rows), src_label, args.bucket_mode)

    if args.output == "-":
        print(report)
    else:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
