"""Daily Live Monitor (N7, 2026-04-27)

C1-PROMOTE / WATCH cells / Wave 2 gates の Live 状況を毎日 snapshot し、
rollback gate proximity と fast-track 条件を自動評価する。

Usage:
  python3 tools/daily_live_monitor.py [--db demo_trades.db] [--window 24h|7d]
  python3 tools/daily_live_monitor.py --check-rollback   # CI 用、非0で abort

Output:
  - stdout: 状況サマリ (人間向け)
  - raw/audits/daily_live_<date>.md (履歴)
  - raw/audits/daily_live_latest.json (machine 読み取り用 — alert subsystem 連携)
  - exit code: 0 通常、1 rollback 警告、2 critical (連続 LOSS / Wlo<40%)
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─── Tracked cells (Pre-reg LOCK 2026-04-27) ────────────────────────────
PROMOTED_CELLS = [
    {
        "id": "C1",
        "name": "fib_reversal × Tokyo × q0 × Scalp",
        "entry_type": "fib_reversal",
        "instrument": "USD_JPY",
        "mode_pattern": "scalp",  # exact match (1m only)
        "session_hours_utc": (0, 7),
        "spread_max_pips": 0.8,
        "current_lot": 0.01,  # 0.05→0.01 縮小済 (commit 1467d7e)
    },
]

# ELITE_LIVE 3 strategies (post-M1 fix tracking, 2026-04-27 evening)
# M1 修正: spread_sl_gate ELITE_LIVE 免除 (commit 641bfe4)
# 期待: post-M1 (2026-04-27 ~14:51 JST) で ELITE 3 戦略の Live fire 再開
ELITE_LIVE_CELLS = [
    {
        "id": "E1",
        "name": "session_time_bias (any pair)",
        "entry_type": "session_time_bias",
        "instrument": None,  # any
        "mode_pattern": None,  # any
        "session_hours_utc": None,  # any
        "spread_max_pips": None,
    },
    {
        "id": "E2",
        "name": "trendline_sweep (any pair)",
        "entry_type": "trendline_sweep",
        "instrument": None,
        "mode_pattern": None,
        "session_hours_utc": None,
        "spread_max_pips": None,
    },
    {
        "id": "E3",
        "name": "gbp_deep_pullback (any pair)",
        "entry_type": "gbp_deep_pullback",
        "instrument": None,
        "mode_pattern": None,
        "session_hours_utc": None,
        "spread_max_pips": None,
    },
]

# M1 修正デプロイ時刻 (post-deploy filter 用)
M1_DEPLOY_TIME = "2026-04-27T05:51:00"  # 641bfe4 push 時刻 (UTC)

WATCH_CELLS = [
    {
        "id": "W1",
        "name": "bb_rsi_reversion × Tokyo × q0 × Scalp",
        "entry_type": "bb_rsi_reversion",
        "instrument": "USD_JPY",
        "mode_pattern": "scalp",
        "session_hours_utc": (0, 7),
        "spread_max_pips": 0.8,
    },
    {
        "id": "W2",
        "name": "bb_rsi_reversion × London × q0 × Scalp",
        "entry_type": "bb_rsi_reversion",
        "instrument": "USD_JPY",
        "mode_pattern": "scalp",
        "session_hours_utc": (7, 12),
        "spread_max_pips": 0.8,
    },
]

WAVE2_GATES = ["A2 SL clamp", "A3 cost throttle", "A4 vol_scale"]
WAVE2_REASON_PATTERNS = {
    "A2 SL clamp": ["SL clamp", "sl clamped"],
    "A3 cost throttle": ["A3 cost throttle", "cost_throttle", "C3 throttle"],
    "A4 vol_scale": ["vol_scale", "A4 vol scale", "vol-scaled"],
}


# ─── Statistics ─────────────────────────────────────────────────────────
def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


def consecutive_losses_at_tail(rows: list[sqlite3.Row]) -> int:
    """Number of trailing LOSS in rows ordered by entry_time DESC."""
    n = 0
    for r in rows:
        if r["outcome"] == "LOSS":
            n += 1
        else:
            break
    return n


# ─── Cell matchers ──────────────────────────────────────────────────────
def cell_matches(row: sqlite3.Row, cell: dict) -> bool:
    """Match a row to a cell. Cell fields with None are wildcards."""
    if row["entry_type"] != cell["entry_type"]:
        return False
    if cell.get("instrument") is not None and row["instrument"] != cell["instrument"]:
        return False
    mode = (row["mode"] or "").lower()
    if cell.get("mode_pattern") is not None and mode != cell["mode_pattern"]:
        return False
    if cell.get("session_hours_utc") is not None:
        try:
            h = datetime.fromisoformat(
                (row["entry_time"] or "").replace("Z", "+00:00")
            ).astimezone(timezone.utc).hour
        except Exception:
            return False
        lo, hi = cell["session_hours_utc"]
        if not (lo <= h < hi):
            return False
    if cell.get("spread_max_pips") is not None:
        spread = row["spread_at_entry"] if row["spread_at_entry"] is not None else 0.0
        if spread > cell["spread_max_pips"]:
            return False
    return True


def fetch_closed_trades(db_path: str, live_only: bool = False) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if live_only:
        rows = conn.execute("""
            SELECT * FROM demo_trades
            WHERE outcome IN ('WIN','LOSS') AND is_shadow = 0
            ORDER BY datetime(entry_time) DESC
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM demo_trades
            WHERE outcome IN ('WIN','LOSS')
            ORDER BY datetime(entry_time) DESC
        """).fetchall()
    conn.close()
    return rows


# ─── Cell stats ─────────────────────────────────────────────────────────
def cell_stats(cell: dict, all_rows: list[sqlite3.Row]) -> dict:
    """Compute stats for this cell across Live + Shadow."""
    matched = [r for r in all_rows if cell_matches(r, cell)]
    live_matched = [r for r in matched if not r["is_shadow"]]
    shadow_matched = [r for r in matched if r["is_shadow"]]

    def stats(rows: list[sqlite3.Row]) -> dict:
        n = len(rows)
        if n == 0:
            return {"n": 0, "wins": 0, "wr": 0.0, "wilson_lower": 0.0,
                    "ev_pip": 0.0, "consec_loss_tail": 0}
        wins = sum(1 for r in rows if r["outcome"] == "WIN")
        wl = wilson_lower(wins, n)
        ev = sum((r["pnl_pips"] or 0.0) for r in rows) / n
        # rows are sorted DESC, so head = most recent
        consec = consecutive_losses_at_tail(rows)
        return {"n": n, "wins": wins, "wr": round(wins/n, 4),
                "wilson_lower": round(wl, 4),
                "ev_pip": round(ev, 3),
                "consec_loss_tail": consec}
    return {
        "id": cell["id"],
        "name": cell["name"],
        "live": stats(live_matched),
        "shadow": stats(shadow_matched),
        "total": stats(matched),
    }


# ─── Rollback gate evaluation ───────────────────────────────────────────
def evaluate_rollback(c1: dict) -> tuple[int, list[str]]:
    """Return (severity, alerts).

    severity: 0 OK, 1 warning, 2 critical (immediate action required)
    """
    alerts: list[str] = []
    sev = 0
    live = c1["live"]
    n = live["n"]
    wr = live["wr"]
    wl = live["wilson_lower"]
    consec = live["consec_loss_tail"]

    # Critical (即 0.05 lot 復帰 or Shadow 復帰)
    if consec >= 3:
        alerts.append(f"CRITICAL: {c1['id']} 連続 {consec} LOSS — 即 0.05 lot 復帰推奨")
        sev = max(sev, 2)
    if n >= 10 and wl < 0.40:
        alerts.append(
            f"CRITICAL: {c1['id']} Live N={n} Wilson lower {wl:.1%} < 40% — Shadow 復帰推奨"
        )
        sev = max(sev, 2)
    if n >= 5 and wr < 0.50:
        alerts.append(
            f"WARNING: {c1['id']} Live N={n} WR {wr:.1%} < 50% — 0.05 lot 維持/observation 延長"
        )
        sev = max(sev, 1)
    if 0 < n < 5:
        alerts.append(
            f"INFO: {c1['id']} Live N={n} まだ初期。WR={wr:.1%} 監視継続"
        )

    # Lot graduation milestones (informational)
    if n >= 10 and wl > 0.50 and consec == 0:
        alerts.append(f"GRADUATE OK: {c1['id']} Live N={n} Wlo {wl:.1%}>50% — 0.10 lot 昇格条件達成")
    if n >= 10 and wr >= 0.80 and wl > 0.60 and consec == 0:
        alerts.append(
            f"FAST-TRACK OK: {c1['id']} Live N={n} WR {wr:.1%}≥80% Wlo {wl:.1%}>60% "
            f"— 0.20 lot 直接昇格条件達成 (Pre-reg LOCK §Fast-track)"
        )
    return sev, alerts


# ─── Wave 2 gate firing rate ────────────────────────────────────────────
# Wave 2 commit (4df389f) は 2026-04-27 にデプロイ。それ以前のトレードには
# Wave 2 reason は含まれないので、デプロイ後のトレードのみで firing rate 評価。
WAVE2_DEPLOY_DATE = "2026-04-27"


def wave2_firing_rate(all_rows: list[sqlite3.Row]) -> dict:
    """Count how often each Wave 2 gate fired (search reasons field).

    Only considers trades created on or after WAVE2_DEPLOY_DATE.
    """
    post_deploy = [
        r for r in all_rows
        if (r["created_at"] or "") >= WAVE2_DEPLOY_DATE
    ]
    total = len(post_deploy)
    out: dict[str, dict] = {}
    for gate, patterns in WAVE2_REASON_PATTERNS.items():
        fired = 0
        for r in post_deploy:
            reasons_str = r["reasons"] or ""
            for p in patterns:
                if p.lower() in reasons_str.lower():
                    fired += 1
                    break
        rate = (fired / total * 100) if total else 0.0
        anomaly: str | None = None
        # Need ≥ 50 post-deploy trades before alerting on anomalies
        if total >= 50:
            if rate == 0:
                anomaly = "0% 発火 — 閾値 too strict / 配線ミス疑い"
            elif rate > 90:
                anomaly = f"{rate:.0f}% 発火 — 閾値 too loose"
        out[gate] = {
            "fired": fired,
            "rate_pct": round(rate, 1),
            "post_deploy_n": total,
            "anomaly": anomaly,
        }
    return out


# ─── Markdown rendering ─────────────────────────────────────────────────
def render_md(snapshot: dict) -> str:
    L: list[str] = [
        f"# Daily Live Monitor — {snapshot['date']}",
        "",
        f"DB: {snapshot['db_path']} (closed trades total = {snapshot['total_closed']}, Live = {snapshot['total_live']})",
        f"Severity: **{snapshot['severity_label']}**",
        "",
        "## C1-PROMOTE Live状況",
        "",
        "| Cell | Live N | WR | Wilson lo | EV pip | tail LOSS | Shadow N (ref) |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in snapshot["promoted"]:
        L.append(
            f"| {c['name']} | {c['live']['n']} | {c['live']['wr']:.1%} | "
            f"{c['live']['wilson_lower']:.1%} | {c['live']['ev_pip']:+.2f} | "
            f"{c['live']['consec_loss_tail']} | {c['shadow']['n']} |"
        )
    L += ["", "## WATCH cells (PROMOTE 候補・Live N 蓄積待ち)", "",
          "| Cell | Live N | WR | Wilson lo | EV pip |",
          "|---|---|---|---|---|"]
    for c in snapshot["watch"]:
        L.append(
            f"| {c['name']} | {c['live']['n']} | {c['live']['wr']:.1%} | "
            f"{c['live']['wilson_lower']:.1%} | {c['live']['ev_pip']:+.2f} |"
        )

    # ELITE_LIVE 3戦略の追跡 (M1 修正効果監視)
    L += [
        "",
        "## ELITE_LIVE 3戦略 (M1 修正効果監視)",
        f"M1 deploy: **{snapshot['m1_deploy_time']} UTC** (commit 641bfe4)",
        f"Post-M1 total trades: {snapshot.get('post_m1_total_rows', 0)}",
        "",
        "### 全期間 (BT-Live divergence baseline)",
        "",
        "| Cell | Live N | WR | EV pip | Shadow N |",
        "|---|---|---|---|---|",
    ]
    for c in snapshot.get("elite_live_all", []):
        L.append(
            f"| {c['name']} | {c['live']['n']} | {c['live']['wr']:.1%} | "
            f"{c['live']['ev_pip']:+.2f} | {c['shadow']['n']} |"
        )
    L += [
        "",
        "### Post-M1 (修正後 only)",
        "",
        "| Cell | Live N | WR | EV pip | Shadow N |",
        "|---|---|---|---|---|",
    ]
    for c in snapshot.get("elite_live_post_m1", []):
        L.append(
            f"| {c['name']} | {c['live']['n']} | {c['live']['wr']:.1%} | "
            f"{c['live']['ev_pip']:+.2f} | {c['shadow']['n']} |"
        )
    L += ["", "## Alerts",  ""]
    if snapshot["alerts"]:
        for a in snapshot["alerts"]:
            L.append(f"- {a}")
    else:
        L.append("_No alerts._")
    # Wave 2 firing rate header
    if snapshot["wave2"]:
        first = next(iter(snapshot["wave2"].values()))
        post_n = first.get("post_deploy_n", 0)
    else:
        post_n = 0
    L += [
        "",
        f"## Wave 2 gate firing rate (post-deploy {WAVE2_DEPLOY_DATE}+, N={post_n})",
        "",
        "| Gate | fired | rate | anomaly |",
        "|---|---|---|---|",
    ]
    for gate, info in snapshot["wave2"].items():
        anomaly = info["anomaly"] or "-"
        L.append(f"| {gate} | {info['fired']} | {info['rate_pct']:.1f}% | {anomaly} |")
    if post_n < 50:
        L += [
            "",
            f"_post-deploy N={post_n} < 50 のため、anomaly 判定はサンプル蓄積待ち_"
        ]
    return "\n".join(L) + "\n"


SEV_LABEL = {0: "OK", 1: "WARNING", 2: "CRITICAL"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="demo_trades.db")
    parser.add_argument("--out-dir", default="raw/audits")
    parser.add_argument("--check-rollback", action="store_true",
                        help="Exit non-zero on rollback alerts (CI integration)")
    args = parser.parse_args()

    all_rows = fetch_closed_trades(args.db, live_only=False)
    live_total = sum(1 for r in all_rows if not r["is_shadow"])

    promoted = [cell_stats(c, all_rows) for c in PROMOTED_CELLS]
    watch = [cell_stats(c, all_rows) for c in WATCH_CELLS]
    wave2 = wave2_firing_rate(all_rows)

    # ELITE_LIVE 3 戦略の追跡 (M1 修正 post-deploy 効果監視)
    elite = [cell_stats(c, all_rows) for c in ELITE_LIVE_CELLS]
    # post-M1 (2026-04-27T05:51 UTC+) のみで集計
    post_m1_rows = [r for r in all_rows if (r["entry_time"] or "") >= M1_DEPLOY_TIME]
    elite_post_m1 = [cell_stats(c, post_m1_rows) for c in ELITE_LIVE_CELLS]

    severity = 0
    alerts: list[str] = []
    for c in promoted:
        sev, msgs = evaluate_rollback(c)
        severity = max(severity, sev)
        alerts.extend(msgs)
    # Wave 2 anomaly aggregation
    for gate, info in wave2.items():
        if info["anomaly"]:
            alerts.append(f"WAVE2 {gate}: {info['anomaly']}")
            severity = max(severity, 1)

    # ─── net_edge_audit (P0-2, 2026-04-27) ─────────────────────────────
    # 戦略の WR vs benchmark (同期間×同 pair×同 direction 他戦略 Shadow) を比較し、
    # 市場ベータ便乗エッジを検出する。net_edge_wr_pt < -10 を warning として記録。
    # 詳細: reports/deployment-wave-analysis-2026-04-27.md §4
    net_edge_summary: list[dict] = []
    try:
        from tools.net_edge_audit import audit_strategy
        from modules.demo_db import DemoDB
        _db = DemoDB(db_path=args.db)
        with _db._safe_conn() as _conn:
            _ets = [r[0] for r in _conn.execute(
                "SELECT DISTINCT entry_type FROM demo_trades "
                "WHERE entry_type IS NOT NULL AND entry_type != '' "
                "AND (instrument IS NULL OR instrument NOT LIKE '%XAU%') "
                "AND status='CLOSED'"
            ).fetchall()]
        for et in sorted(_ets):
            r = audit_strategy(_db, et, window_h=0)
            if r.get("n_strat", 0) >= 5:
                net_edge_summary.append(r)
                if r.get("net_edge_wr_pt", 0) <= -10:
                    alerts.append(
                        f"NET_EDGE {et}: {r['net_edge_wr_pt']:+.1f}pt "
                        f"({r['net_edge_pip']:+.2f}pip) N={r['n_strat']}"
                    )
                    severity = max(severity, 1)
    except Exception as _e:
        alerts.append(f"NET_EDGE audit failed: {type(_e).__name__}: {_e}")

    today = datetime.now(timezone.utc).date().isoformat()
    snapshot = {
        "date": today,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": args.db,
        "total_closed": len(all_rows),
        "total_live": live_total,
        "promoted": promoted,
        "watch": watch,
        "wave2": wave2,
        "elite_live_all": elite,           # M1 修正前後 全期間
        "elite_live_post_m1": elite_post_m1,  # M1 deploy 後のみ
        "m1_deploy_time": M1_DEPLOY_TIME,
        "post_m1_total_rows": len(post_m1_rows),
        "net_edge": net_edge_summary,      # P0-2 (2026-04-27): 戦略 WR vs market beta
        "alerts": alerts,
        "severity": severity,
        "severity_label": SEV_LABEL[severity],
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"daily_live_{today}.md"
    json_path = out_dir / "daily_live_latest.json"
    md_path.write_text(render_md(snapshot))
    json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))

    print(f"[daily_live_monitor] severity={SEV_LABEL[severity]} "
          f"closed={len(all_rows)} live={live_total} alerts={len(alerts)}")
    for a in alerts:
        print(f"  - {a}")
    print(f"[daily_live_monitor] {md_path}")
    print(f"[daily_live_monitor] {json_path}")

    if args.check_rollback and severity >= 1:
        return 1 if severity == 1 else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
