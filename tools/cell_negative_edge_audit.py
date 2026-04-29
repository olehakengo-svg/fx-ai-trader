"""Cell Negative Edge Audit — Wilson-upper < 50% Live NG list.

Scans shadow trades across multiple cell axes and flags cells whose 95%
Wilson **upper** bound on WR is below 50% (or 55% with EV_net < -1 for the
weaker "likely" class). Such cells are structurally inadvisable for Live
promotion: even the optimistic side of the confidence interval loses on a
coin flip.

Bonferroni is intentionally NOT applied here. The Wilson interval is itself
conservative; we want the *union* of axis-views (a cell may be definitively
losing under one slicing even if other slicings lack power). Per CLAUDE.md
2026-04-28 "Shadow vs Live" rule, false positives are harmless because
shadow continuation costs nothing — only Live promotion is gated by this
list.

Phase 9 alignment:
- Uses ``research.edge_discovery.power_analysis.wilson_lower_at`` for
  symmetric Wilson interval (and inline ``wilson_upper_at``).
- Uses ``modules.friction_model_v2.friction_for(..., hour_utc=)`` so that
  hour-bin axes get the new hour-of-day adjustment (Phase 9 P5).
- Uses ``research.edge_discovery.clustering_artifacts.detect_repeat_firing``
  as a side-channel: NG cells that ALSO show clustering get an extra flag
  (most aggressive cleanup priority).

Persistence:
  ``live_ng_cells`` SQLite table (created idempotently if missing).

Usage::

    python3 tools/cell_negative_edge_audit.py --window all --shadow-only
    python3 tools/cell_negative_edge_audit.py --window 30d --shadow-only \\
        --persist
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.friction_model_v2 import friction_for  # noqa: E402
from modules.strategy_category import _normalize_session  # noqa: E402
from research.edge_discovery.clustering_artifacts import (  # noqa: E402
    detect_repeat_firing,
)
from research.edge_discovery.power_analysis import (  # noqa: E402
    WILSON_Z_95,
    wilson_lower_at,
)


# ─── Configuration ──────────────────────────────────────────────────────
MIN_N: int = 10
DEFINITELY_THR: float = 0.50
LIKELY_THR: float = 0.55
LIKELY_EV_NET_THR: float = -1.0


def wilson_upper_at(wr: float, n: int, z: float = WILSON_Z_95) -> float:
    """95% Wilson upper bound at observed WR=wr, sample n.

    Companion to research.edge_discovery.power_analysis.wilson_lower_at;
    not added there to avoid touching parallel-session code.
    """
    if n <= 0:
        return 1.0
    denom = 1.0 + (z * z) / n
    center = wr + (z * z) / (2.0 * n)
    margin = z * math.sqrt((wr * (1.0 - wr) + (z * z) / (4.0 * n)) / n)
    return min(1.0, (center + margin) / denom)


# ─── Session / hour-bin helpers ─────────────────────────────────────────
def _session_from_utc(entry_time_iso: str) -> str:
    if not entry_time_iso:
        return "default"
    try:
        ts = datetime.fromisoformat(entry_time_iso.replace("Z", "+00:00"))
        h = ts.astimezone(timezone.utc).hour
    except Exception:
        return "default"
    if h < 7:
        return "Tokyo"
    if h < 12:
        return "London"
    if h < 16:
        return "overlap_LN"
    if h < 21:
        return "NY"
    return "Sydney"


def _hour_bin_from_utc(entry_time_iso: str) -> str:
    if not entry_time_iso:
        return "default"
    try:
        ts = datetime.fromisoformat(entry_time_iso.replace("Z", "+00:00"))
        h = ts.astimezone(timezone.utc).hour
    except Exception:
        return "default"
    if h < 6:
        return "h00-06"
    if h < 12:
        return "h06-12"
    if h < 18:
        return "h12-18"
    return "h18-24"


# Representative hour for each 6-hour bin (used for hour_utc friction lookup)
_HOUR_BIN_MID = {"h00-06": 3, "h06-12": 9, "h12-18": 15, "h18-24": 21}


# ─── DB IO ──────────────────────────────────────────────────────────────
def _fetch_shadow_trades(db_path: str, since_iso: str | None
                         ) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if since_iso is not None:
        rows = conn.execute("""
            SELECT trade_id, entry_type, mode, instrument, direction, tf,
                   entry_time, entry_price, sl, spread_at_entry,
                   outcome, pnl_pips, is_shadow
            FROM demo_trades
            WHERE outcome IN ('WIN','LOSS') AND is_shadow = 1
              AND entry_time >= ?
        """, (since_iso,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT trade_id, entry_type, mode, instrument, direction, tf,
                   entry_time, entry_price, sl, spread_at_entry,
                   outcome, pnl_pips, is_shadow
            FROM demo_trades
            WHERE outcome IN ('WIN','LOSS') AND is_shadow = 1
        """).fetchall()
    conn.close()
    return rows


def _ensure_table(db_path: str) -> None:
    """Idempotently create live_ng_cells table; backfill missing columns."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS live_ng_cells (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at          TEXT DEFAULT (datetime('now')),
                axis            TEXT NOT NULL,
                cell_key        TEXT NOT NULL,
                entry_type      TEXT,
                pair            TEXT,
                session         TEXT,
                hour_bin        TEXT,
                direction       TEXT,
                n               INTEGER,
                wr              REAL,
                wilson_upper    REAL,
                ev_net_pip      REAL,
                ng_class        TEXT NOT NULL,
                clustering      TEXT,
                data_window     TEXT NOT NULL,
                data_scope      TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_live_ng_cells_run_at
                ON live_ng_cells(run_at);
            CREATE INDEX IF NOT EXISTS idx_live_ng_cells_entry_type
                ON live_ng_cells(entry_type);
        """)
        # Backfill clustering column on pre-existing tables (if missing)
        cols = {row[1] for row in conn.execute(
            "PRAGMA table_info(live_ng_cells)").fetchall()}
        if "clustering" not in cols:
            conn.execute("ALTER TABLE live_ng_cells ADD COLUMN clustering TEXT")
        conn.commit()
    finally:
        conn.close()


def _persist(db_path: str, records: list[dict], data_window: str,
             data_scope: str) -> int:
    if not records:
        return 0
    _ensure_table(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.executemany(
            """INSERT INTO live_ng_cells
                   (axis, cell_key, entry_type, pair, session, hour_bin,
                    direction, n, wr, wilson_upper, ev_net_pip, ng_class,
                    clustering, data_window, data_scope)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(r["axis"], r["cell_key"], r.get("entry_type"), r.get("pair"),
              r.get("session"), r.get("hour_bin"), r.get("direction"),
              r["n"], r["wr"], r["wilson_upper"], r["ev_net_pip"],
              r["ng_class"], r.get("clustering"), data_window, data_scope)
             for r in records],
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ─── Axis specs ─────────────────────────────────────────────────────────
def _key_session(r):
    return _normalize_session(_session_from_utc(r["entry_time"]))


def _key_hour_bin(r):
    return _hour_bin_from_utc(r["entry_time"])


AXES: list[dict] = [
    {"name": "by-strategy", "keys": ["entry_type"],
     "keyfn": lambda r: ((r["entry_type"] or "unknown"),)},
    {"name": "by-pair", "keys": ["pair"],
     "keyfn": lambda r: ((r["instrument"] or "USD_JPY"),)},
    {"name": "by-session", "keys": ["session"],
     "keyfn": lambda r: (_key_session(r),)},
    {"name": "by-direction", "keys": ["direction"],
     "keyfn": lambda r: (((r["direction"] or "?").upper()),)},
    {"name": "by-hour-bin", "keys": ["hour_bin"],
     "keyfn": lambda r: (_key_hour_bin(r),)},
    {"name": "by-strategy-pair", "keys": ["entry_type", "pair"],
     "keyfn": lambda r: ((r["entry_type"] or "unknown"),
                         (r["instrument"] or "USD_JPY"))},
    {"name": "by-strategy-session", "keys": ["entry_type", "session"],
     "keyfn": lambda r: ((r["entry_type"] or "unknown"), _key_session(r))},
    {"name": "by-strategy-direction", "keys": ["entry_type", "direction"],
     "keyfn": lambda r: ((r["entry_type"] or "unknown"),
                         (r["direction"] or "?").upper())},
    {"name": "by-strategy-hour-bin", "keys": ["entry_type", "hour_bin"],
     "keyfn": lambda r: ((r["entry_type"] or "unknown"), _key_hour_bin(r))},
    {"name": "by-pair-session", "keys": ["pair", "session"],
     "keyfn": lambda r: ((r["instrument"] or "USD_JPY"), _key_session(r))},
    {"name": "by-pair-hour-bin", "keys": ["pair", "hour_bin"],
     "keyfn": lambda r: ((r["instrument"] or "USD_JPY"), _key_hour_bin(r))},
    {"name": "by-pair-direction", "keys": ["pair", "direction"],
     "keyfn": lambda r: ((r["instrument"] or "USD_JPY"),
                         (r["direction"] or "?").upper())},
    {"name": "by-direction-hour-bin", "keys": ["direction", "hour_bin"],
     "keyfn": lambda r: (((r["direction"] or "?").upper()),
                         _key_hour_bin(r))},
    {"name": "by-strategy-pair-direction",
     "keys": ["entry_type", "pair", "direction"],
     "keyfn": lambda r: ((r["entry_type"] or "unknown"),
                         (r["instrument"] or "USD_JPY"),
                         (r["direction"] or "?").upper())},
    {"name": "by-strategy-pair-hour-bin",
     "keys": ["entry_type", "pair", "hour_bin"],
     "keyfn": lambda r: ((r["entry_type"] or "unknown"),
                         (r["instrument"] or "USD_JPY"),
                         _key_hour_bin(r))},
    {"name": "by-strategy-direction-hour-bin",
     "keys": ["entry_type", "direction", "hour_bin"],
     "keyfn": lambda r: ((r["entry_type"] or "unknown"),
                         (r["direction"] or "?").upper(),
                         _key_hour_bin(r))},
]


# ─── Friction lookup per axis ───────────────────────────────────────────
def _friction_for_axis(rec: dict, mode_default: str = "DT") -> float | None:
    """Best-effort friction lookup (hour-aware when hour_bin in cell key)."""
    pair = rec.get("pair")
    if not pair:
        return None
    sess = rec.get("session", "default") or "default"
    hour_bin = rec.get("hour_bin")
    hour_utc = _HOUR_BIN_MID.get(hour_bin) if hour_bin else None
    f = friction_for(pair, mode=mode_default, session=sess, hour_utc=hour_utc)
    if f.get("unsupported"):
        return None
    val = f.get("adjusted_rt_pips")
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    return float(val)


# ─── Scan ───────────────────────────────────────────────────────────────
def _aggregate(rows: Iterable[sqlite3.Row],
               keyfn: Callable) -> dict[tuple, list]:
    cells: dict[tuple, list] = defaultdict(list)
    for r in rows:
        cells[keyfn(r)].append(r)
    return cells


def _classify(stats: dict, ev_net: float | None) -> str | None:
    n = stats["n"]
    if n < MIN_N:
        return None
    wu = stats["wilson_upper"]
    ev = ev_net if ev_net is not None else stats["ev_pip"]
    if wu < DEFINITELY_THR and ev < 0:
        return "definitely"
    if wu < LIKELY_THR and ev < LIKELY_EV_NET_THR:
        return "likely"
    return None


def _stats(sub_rows: list[sqlite3.Row]) -> dict:
    n = len(sub_rows)
    wins = sum(1 for r in sub_rows if r["outcome"] == "WIN")
    pnls = [float(r["pnl_pips"] or 0.0) for r in sub_rows]
    pnl_sum = sum(pnls)
    gp = sum(p for p in pnls if p > 0)
    gl = sum(-p for p in pnls if p < 0)
    wr = wins / n if n else 0.0
    return {
        "n": n,
        "wins": wins,
        "wr": round(wr, 4),
        "wilson_lower": round(wilson_lower_at(wr, n), 4) if n else 0.0,
        "wilson_upper": round(wilson_upper_at(wr, n), 4) if n else 0.0,
        "ev_pip": round(pnl_sum / n, 3) if n else 0.0,
        "pf": round(gp / gl, 3) if gl > 0 else None,
    }


def scan(rows: list[sqlite3.Row]) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple] = set()
    for ax in AXES:
        cells = _aggregate(rows, ax["keyfn"])
        for k, sub_rows in cells.items():
            stats = _stats(sub_rows)
            if stats["n"] < MIN_N:
                continue
            cell_dim = {kn: kv for kn, kv in zip(ax["keys"], k)}
            friction = _friction_for_axis(cell_dim)
            ev_net = (round(stats["ev_pip"] - friction, 3)
                      if friction is not None else None)
            ng = _classify(stats, ev_net)
            if not ng:
                continue
            dedup_key = (ax["name"], "/".join(str(x) for x in k))
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            cluster_v = detect_repeat_firing(
                sub_rows, pair=cell_dim.get("pair"))
            out.append({
                "axis": ax["name"],
                "cell_key": "/".join(str(x) for x in k),
                **cell_dim,
                **stats,
                "friction_pip": (round(friction, 3)
                                 if friction is not None else None),
                "ev_net_pip": ev_net,
                "ng_class": ng,
                "clustering": cluster_v["verdict"],
                "clustering_flags": cluster_v["flags"],
            })
    out.sort(key=lambda x: (x["wilson_upper"],
                            x["ev_net_pip"] if x["ev_net_pip"] is not None
                            else x["ev_pip"]))
    return out


# ─── Render ─────────────────────────────────────────────────────────────
def _render_md(records: list[dict], scope: str, window: str,
               total_trades: int) -> str:
    definitely = [r for r in records if r["ng_class"] == "definitely"]
    likely = [r for r in records if r["ng_class"] == "likely"]
    artifactual = [r for r in records if r["clustering"] == "artifactual"]
    lines = [
        f"# Cell Negative Edge Audit "
        f"({datetime.now(timezone.utc).date().isoformat()})",
        "",
        f"Scope: **{scope}** | Window: **{window}** | "
        f"Total trades scanned: **{total_trades}**",
        "",
        f"- **Definitely-losing** (N≥{MIN_N} AND Wilson upper < "
        f"{DEFINITELY_THR:.0%} AND ev_net<0): **{len(definitely)}**",
        f"- **Likely-losing** (N≥{MIN_N} AND Wilson upper < "
        f"{LIKELY_THR:.0%} AND ev_net<{LIKELY_EV_NET_THR}): "
        f"**{len(likely)}**",
        f"- **Clustering = artifactual** (subset, prioritize): "
        f"**{len(artifactual)}**",
        "",
        "Bonferroni intentionally not applied — Wilson interval is itself "
        "conservative. Shadow continuation harmless; Live promotion NG.",
        "Hour-aware friction (Phase 9 P5) used when cell key contains "
        "``hour_bin``; falls back to session-level otherwise.",
        "",
        "## Definitely-losing cells",
        "",
    ]
    if definitely:
        lines += [
            "| axis | cell_key | N | wins | WR | Wilson [lo, hi] | EV | "
            "EV_net | PF | clustering |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in definitely:
            ev_net = (f"{r['ev_net_pip']:+.2f}"
                      if r["ev_net_pip"] is not None else "n/a")
            pf_str = f"{r['pf']:.2f}" if r["pf"] is not None else "n/a"
            cl = r["clustering"]
            cl_marker = ("⚠️ " if cl == "artifactual"
                         else ("· " if cl == "weak_clustering" else ""))
            lines.append(
                f"| {r['axis']} | {r['cell_key']} | {r['n']} | {r['wins']} | "
                f"{r['wr']:.1%} | [{r['wilson_lower']:.1%}, "
                f"{r['wilson_upper']:.1%}] | {r['ev_pip']:+.2f} | "
                f"{ev_net} | {pf_str} | {cl_marker}{cl} |"
            )
    else:
        lines.append("_None._")

    lines += ["", "## Likely-losing cells", ""]
    if likely:
        lines += [
            "| axis | cell_key | N | wins | WR | Wilson [lo, hi] | EV | "
            "EV_net | PF | clustering |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in likely:
            ev_net = (f"{r['ev_net_pip']:+.2f}"
                      if r["ev_net_pip"] is not None else "n/a")
            pf_str = f"{r['pf']:.2f}" if r["pf"] is not None else "n/a"
            lines.append(
                f"| {r['axis']} | {r['cell_key']} | {r['n']} | {r['wins']} | "
                f"{r['wr']:.1%} | [{r['wilson_lower']:.1%}, "
                f"{r['wilson_upper']:.1%}] | {r['ev_pip']:+.2f} | "
                f"{ev_net} | {pf_str} | {r['clustering']} |"
            )
    else:
        lines.append("_None._")
    return "\n".join(lines) + "\n"


# ─── CLI ────────────────────────────────────────────────────────────────
def _window_to_iso(window: str) -> str | None:
    if window in (None, "", "all"):
        return None
    if not window.endswith("d"):
        raise ValueError(
            f"Invalid --window {window!r}; expected '7d'/'14d'/'30d'/'all'")
    days = int(window[:-1])
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="demo_trades.db")
    parser.add_argument("--shadow-only", action="store_true",
                        help="Use is_shadow=1 trades only (default behavior)")
    parser.add_argument("--window", default="all")
    parser.add_argument("--out-dir", default="raw/audits")
    parser.add_argument("--persist", action="store_true",
                        help="Insert results into live_ng_cells table")
    args = parser.parse_args()

    scope = "shadow"  # tool is shadow-only by design; flag accepted for clarity
    since = _window_to_iso(args.window)
    rows = _fetch_shadow_trades(args.db, since_iso=since)
    if not rows:
        print(f"[neg_edge] No shadow trades for window={args.window}",
              file=sys.stderr)
        return 1

    records = scan(rows)

    today = datetime.now(timezone.utc).date().isoformat()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"{today}_{args.window}_{scope}"
    json_path = out_dir / f"cell_negative_edge_{suffix}.json"
    md_path = out_dir / f"cell_negative_edge_{suffix}.md"

    n_def = sum(1 for r in records if r["ng_class"] == "definitely")
    n_likely = sum(1 for r in records if r["ng_class"] == "likely")
    n_artifact = sum(1 for r in records if r["clustering"] == "artifactual")

    json_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "window": args.window,
        "total_trades": len(rows),
        "definitely_losing": n_def,
        "likely_losing": n_likely,
        "artifactual_clustering": n_artifact,
        "records": records,
    }, ensure_ascii=False, indent=2))
    md_path.write_text(_render_md(records, scope, args.window, len(rows)))

    inserted = 0
    if args.persist:
        inserted = _persist(args.db, records, args.window, scope)

    print(f"[neg_edge] {len(rows)} shadow trades, window={args.window}: "
          f"definitely={n_def}, likely={n_likely}, "
          f"artifactual_cluster={n_artifact}, persisted={inserted}")
    print(f"[neg_edge] Output: {json_path} + {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
