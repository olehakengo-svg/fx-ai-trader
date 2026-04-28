"""
G0a: Production routing audit (Phase 10 pivot).

G1 finding (raw/audits/never_logged_diagnosis_2026-04-28.md) showed that 3
strategies (vsg_jpy_reversal, rsk_gbpjpy_reversion, mqe_gbpusd_fix) fire
533 signals total in 365d BT but produce 0 production trades. This is a
**routing/pipeline failure**, not an entry-condition failure.

Before any further alpha work, we need to know:
  1. How many of the 47+ deployed strategies actually emit trades in
     production?
  2. Which strategies have Shadow trades but no Live? (= Live filter
     too strict, or just Shadow expansion mode)
  3. Which strategies never appear in the DB at all? (= silent loss
     before insert)

This tool reads ``demo_trades.db`` (local mirror of production) and
cross-references with the DT_QUALIFIED list in ``app.py``. Output: a
markdown report categorising every deployed strategy.

Plan: /Users/jg-n-012/.claude/plans/memoized-snuggling-eclipse.md
(Phase 10 G0a — pivot finding from G1)

Usage:
    python3 tools/production_routing_audit.py
        [--db demo_trades.db]
        [--days 30]
        [--out raw/audits/production_routing_audit_<date>.md]
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import date, timedelta
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(PROJECT_ROOT, "demo_trades.db")


def extract_dt_qualified() -> list[str]:
    """Extract the DT_QUALIFIED set from app.py."""
    app_py = os.path.join(PROJECT_ROOT, "app.py")
    content = open(app_py).read()
    m = re.search(r"DT_QUALIFIED = \{(.*?)\}", content, re.DOTALL)
    if not m:
        return []
    body = m.group(1)
    names = re.findall(r'"([a-z_0-9]+)"', body)
    return names


def query_strategy_counts(
    db_path: str, days: int
) -> dict[str, dict[str, Any]]:
    """Per-strategy trade counts grouped by is_shadow."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Validate days as a non-negative int and pass via parameter; the
    # SQLite ``datetime('now', ?)`` modifier accepts a string like '-30 days'.
    days_int = max(0, int(days))
    if days_int > 0:
        cutoff_arg = f"-{days_int} days"
        sql = (
            "SELECT entry_type, COUNT(*) AS total,"
            " SUM(CASE WHEN is_shadow = 0 THEN 1 ELSE 0 END) AS live_n,"
            " SUM(CASE WHEN is_shadow = 1 THEN 1 ELSE 0 END) AS shadow_n,"
            " MIN(created_at) AS first_seen, MAX(created_at) AS last_seen"
            " FROM demo_trades"
            " WHERE created_at >= datetime('now', ?)"
            " GROUP BY entry_type"
        )
        cur.execute(sql, (cutoff_arg,))
    else:
        sql = (
            "SELECT entry_type, COUNT(*) AS total,"
            " SUM(CASE WHEN is_shadow = 0 THEN 1 ELSE 0 END) AS live_n,"
            " SUM(CASE WHEN is_shadow = 1 THEN 1 ELSE 0 END) AS shadow_n,"
            " MIN(created_at) AS first_seen, MAX(created_at) AS last_seen"
            " FROM demo_trades GROUP BY entry_type"
        )
        cur.execute(sql)
    rows = cur.fetchall()
    by_strategy: dict[str, dict[str, Any]] = {}
    for r in rows:
        by_strategy[r["entry_type"]] = {
            "total": r["total"],
            "live_n": r["live_n"],
            "shadow_n": r["shadow_n"],
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
        }
    conn.close()
    return by_strategy


def query_db_summary(db_path: str) -> dict[str, Any]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM demo_trades")
    total, first, last = cur.fetchone()
    cur.execute(
        "SELECT SUM(CASE WHEN is_shadow=0 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN is_shadow=1 THEN 1 ELSE 0 END) FROM demo_trades"
    )
    live, shadow = cur.fetchone()
    cur.execute("SELECT COUNT(DISTINCT entry_type) FROM demo_trades")
    distinct_types = cur.fetchone()[0]
    conn.close()
    return {
        "total": total or 0,
        "live": live or 0,
        "shadow": shadow or 0,
        "first_seen": first,
        "last_seen": last,
        "distinct_entry_types": distinct_types,
    }


# Strategies surfaced as production-NEVER_LOGGED in the Apr 28 audit.
G1_NEVER_LOGGED = {
    "sr_anti_hunt_bounce",
    "sr_liquidity_grab",
    "cpd_divergence",
    "vdr_jpy",
    "vsg_jpy_reversal",
    "rsk_gbpjpy_reversion",
    "mqe_gbpusd_fix",
}

# Strategies whose BT replay in G1 produced >0 signals (real entry conditions)
G1_BT_FIRING = {
    "vsg_jpy_reversal": 331,
    "rsk_gbpjpy_reversion": 182,
    "mqe_gbpusd_fix": 20,
}


def categorise(
    deployed: list[str], counts_30d: dict, counts_all: dict
) -> dict[str, list[dict]]:
    """Classify each deployed strategy by its production behaviour."""
    deployed_set = set(deployed)
    db_set = set(counts_all.keys())

    cats: dict[str, list[dict]] = {
        "live_active_30d": [],
        "shadow_only_30d": [],
        "deployed_but_db_silent_30d": [],
        "deployed_never_in_db": [],
        "in_db_but_not_deployed": [],
    }

    for name in deployed:
        c30 = counts_30d.get(name)
        call = counts_all.get(name)
        rec_base = {
            "name": name,
            "g1_bt_firing": G1_BT_FIRING.get(name, None),
            "g1_never_logged_flag": name in G1_NEVER_LOGGED,
        }
        if c30 and c30["live_n"] > 0:
            cats["live_active_30d"].append({**rec_base, **c30})
        elif c30 and c30["shadow_n"] > 0:
            cats["shadow_only_30d"].append({**rec_base, **c30})
        elif call:
            cats["deployed_but_db_silent_30d"].append({**rec_base, **call})
        else:
            cats["deployed_never_in_db"].append(rec_base)

    for name in db_set - deployed_set:
        rec = {"name": name, **counts_all[name]}
        cats["in_db_but_not_deployed"].append(rec)

    return cats


def render_markdown(
    summary: dict, deployed: list[str], cats: dict, days: int
) -> str:
    lines = []
    lines.append(f"# G0a: Production Routing Audit ({date.today().isoformat()})")
    lines.append("")
    lines.append(
        f"- DB span: {summary['first_seen']} → {summary['last_seen']}"
    )
    lines.append(
        f"- Total trades: {summary['total']} "
        f"(Live: {summary['live']}, Shadow: {summary['shadow']})"
    )
    lines.append(
        f"- Distinct entry_types in DB: {summary['distinct_entry_types']}"
    )
    lines.append(f"- Deployed (DT_QUALIFIED) strategies: {len(deployed)}")
    lines.append(f"- Window for 'active': last {days} days")
    lines.append("")
    lines.append("## Top finding")
    lines.append("")
    n_live = len(cats["live_active_30d"])
    n_shadow_only = len(cats["shadow_only_30d"])
    n_db_silent = len(cats["deployed_but_db_silent_30d"])
    n_never_in_db = len(cats["deployed_never_in_db"])
    lines.append(
        f"- **Live-active (≥1 Live trade in {days}d)**: {n_live} / "
        f"{len(deployed)} ({100*n_live/len(deployed):.0f}%)"
    )
    lines.append(
        f"- **Shadow-only (any Shadow, 0 Live)**: {n_shadow_only}"
    )
    lines.append(
        f"- **DB-silent in {days}d but ever logged**: {n_db_silent}"
    )
    lines.append(
        f"- **Deployed but NEVER in DB (any time)**: {n_never_in_db} 🔴"
    )
    lines.append("")
    if n_never_in_db > 0:
        lines.append(
            "→ The most alarming bucket: strategies enabled in code but no DB"
            " row has *ever* appeared. Likely a routing-layer drop. These"
            " warrant the highest-priority pipeline trace."
        )
    lines.append("")

    sections = [
        ("🔴 Deployed but NEVER in DB (any time)", "deployed_never_in_db",
         ["name", "g1_bt_firing", "g1_never_logged_flag"]),
        (f"🟡 Deployed but DB-silent in last {days}d (ever logged before)",
         "deployed_but_db_silent_30d",
         ["name", "total", "live_n", "shadow_n", "last_seen"]),
        (f"🟢 Shadow-only in last {days}d (no Live)",
         "shadow_only_30d",
         ["name", "total", "live_n", "shadow_n", "last_seen"]),
        (f"✅ Live-active in last {days}d",
         "live_active_30d",
         ["name", "total", "live_n", "shadow_n", "last_seen"]),
        ("⚠️ In DB but NOT in DT_QUALIFIED (legacy or strategy renamed)",
         "in_db_but_not_deployed",
         ["name", "total", "live_n", "shadow_n", "last_seen"]),
    ]
    for title, key, columns in sections:
        rows = cats[key]
        lines.append(f"## {title} ({len(rows)})")
        lines.append("")
        if not rows:
            lines.append("(empty)")
            lines.append("")
            continue
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("|" + "---|" * len(columns))
        # Sort by name for the silent buckets, by live_n desc for active
        if key == "live_active_30d":
            rows = sorted(rows, key=lambda r: -r.get("live_n", 0))
        else:
            rows = sorted(rows, key=lambda r: r["name"])
        for r in rows:
            cells = [str(r.get(c, "")) for c in columns]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    lines.append("## Cross-reference: G1 BT firing vs production")
    lines.append("")
    lines.append("| Strategy | G1 BT signals (365d) | Prod total | Prod Live | "
                 "verdict |")
    lines.append("|---|---|---|---|---|")
    for name, bt_n in sorted(G1_BT_FIRING.items(), key=lambda x: -x[1]):
        prod = counts_for(name, cats)
        if prod is None:
            verdict = "🔴 BT fires but **never in DB** — pipeline drop"
            row = f"| {name} | {bt_n} | 0 | 0 | {verdict} |"
        else:
            verdict = (
                "🟢 BT fires & in DB"
                if prod.get("live_n", 0) > 0
                else "🟡 BT fires, in DB but Shadow only"
            )
            row = (f"| {name} | {bt_n} | {prod['total']} | "
                   f"{prod.get('live_n', 0)} | {verdict} |")
        lines.append(row)
    lines.append("")

    lines.append("## Recommended next actions (Phase 10 reordered)")
    lines.append("")
    lines.append(
        "1. **G0b: trace pipeline drop** for any strategy in the 🔴 \"NEVER"
        " in DB\" bucket. Likely candidates:")
    lines.append("   - Strategy class registered in `__init__.py` but missing "
                 "from `DT_QUALIFIED` (gate filter)")
    lines.append("   - tier-master.json gating before insert")
    lines.append("   - DaytradeEngine signal aggregation suppressing cross-pair")
    lines.append("   - Demo_trader QUALIFIED_TYPES check")
    lines.append("2. **Pause new strategy adoption** until ≥80% of deployed "
                 "strategies have ≥1 Shadow trade in 30 days.")
    lines.append("3. **Re-run G1** with proper sr_levels for sr_anti_hunt_bounce / "
                 "sr_liquidity_grab to disambiguate diagnostic harness limit "
                 "vs real 0-firing.")
    lines.append("")
    return "\n".join(lines)


def counts_for(name: str, cats: dict) -> dict | None:
    for key in ("live_active_30d", "shadow_only_30d",
                "deployed_but_db_silent_30d"):
        for r in cats[key]:
            if r["name"] == name:
                return r
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    out = args.out or os.path.join(
        PROJECT_ROOT, "raw", "audits",
        f"production_routing_audit_{date.today().isoformat()}.md",
    )

    deployed = extract_dt_qualified()
    summary = query_db_summary(args.db)
    counts_30d = query_strategy_counts(args.db, args.days)
    counts_all = query_strategy_counts(args.db, days=0)
    cats = categorise(deployed, counts_30d, counts_all)
    md = render_markdown(summary, deployed, cats, args.days)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(md)

    print(f"Wrote {out}")
    print(f"Live-active: {len(cats['live_active_30d'])}/{len(deployed)} deployed")
    print(f"NEVER in DB: {len(cats['deployed_never_in_db'])}/{len(deployed)} 🔴")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
