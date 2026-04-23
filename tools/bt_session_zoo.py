#!/usr/bin/env python3
"""Session-Decomposition BT Scanner — Tokyo/London/NY 別エッジ検出

目的:
  既存 BT の trade_log を entry_time の UTC 時刻で session に分解し、
  戦略×ペア×session の粒度で N/WR/EV/PF を算出する。
  「Tokyo 時間に edge がある戦略は存在するか？」を 1 shot で判定。

セッション定義 (UTC, non-overlap):
  Tokyo:  00:00 – 07:00  (JST 09:00 – 16:00)
  London: 07:00 – 13:00  (UTC, London open → NY pre-market)
  NY:     13:00 – 21:00  (UTC, NY open → close)
  Off:    21:00 – 24:00  (light liquidity)

非侵襲:
  - `app.run_daytrade_backtest` を呼び、返ってくる trade_log を post-hoc 分類
  - BT ロジック / live path は一切変更しない

判断プロトコル (CLAUDE.md):
  - 観測のみ。Tokyo-edge 発見 → 次セッションで別期間 BT で再検証必須
  - 1 scan で filter 実装判断はしない (lesson-reactive-changes)

Usage:
    python3 tools/bt_session_zoo.py [--pairs USD_JPY,EUR_USD]
                                     [--lookback 365]
                                     [--interval 15m]
                                     [--min-n 10]
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

DEFAULT_PAIRS = [
    ("USDJPY=X", "USD_JPY"),
    ("EURUSD=X", "EUR_USD"),
    ("GBPUSD=X", "GBP_USD"),
    ("EURJPY=X", "EUR_JPY"),
    ("GBPJPY=X", "GBP_JPY"),
]

SESSION_BOUNDS = [
    ("Tokyo",  0,  7),
    ("London", 7,  13),
    ("NY",     13, 21),
    ("Off",    21, 24),
]


def parse_entry_time(et_str: str):
    try:
        ts = datetime.fromisoformat(et_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(et_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None


def classify_session(ts: datetime) -> str:
    h = ts.hour
    for name, start, end in SESSION_BOUNDS:
        if start <= h < end:
            return name
    return "Off"


def compute_pnl_pip(trade: dict) -> float:
    outcome = trade.get("outcome")
    tp_m = float(trade.get("tp_m") or 0.0)
    sl_m = float(trade.get("sl_m") or 0.0)
    friction = float(trade.get("exit_friction_m") or 0.0)
    if outcome == "WIN":
        return tp_m - friction
    actual_sl = trade.get("actual_sl_m")
    base = float(actual_sl) if actual_sl is not None else sl_m
    return -(base + friction)


def stats_block(trades: list[dict]) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for t in trades if t.get("outcome") == "WIN")
    pnls = [compute_pnl_pip(t) for t in trades]
    pos = sum(p for p in pnls if p > 0)
    neg = sum(-p for p in pnls if p < 0)
    pf = (pos / neg) if neg > 0.0 else float("inf")
    return {
        "n": n,
        "wr": round(wins / n * 100, 1),
        "ev": round(sum(pnls) / n, 3),
        "pnl": round(sum(pnls), 2),
        "pf": round(pf, 2) if pf != float("inf") else None,
    }


def scan_symbol(yf_symbol: str, pair: str, lookback: int, interval: str,
                min_n: int) -> dict:
    print(f"\n[bt] {pair} ({yf_symbol}) × {lookback}d {interval}...")
    import app
    app._dt_bt_cache.clear()

    try:
        result = app.run_daytrade_backtest(yf_symbol, lookback_days=lookback,
                                           interval=interval)
    except Exception as e:
        return {"pair": pair, "error": f"BT failed: {e}"}

    if result.get("error"):
        return {"pair": pair, "error": result["error"]}

    trades = result.get("trade_log", [])
    if not trades:
        return {"pair": pair, "error": "no trades"}

    # (strategy, session) -> list of trades
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    # strategy -> all trades (for aggregate)
    by_strategy: dict[str, list[dict]] = defaultdict(list)

    for t in trades:
        et = t.get("entry_type") or "unknown"
        ts = parse_entry_time(t.get("entry_time", ""))
        if ts is None:
            continue
        sess = classify_session(ts)
        buckets[(et, sess)].append(t)
        by_strategy[et].append(t)

    strategies = {}
    for strat, all_t in by_strategy.items():
        if len(all_t) < min_n:
            continue
        agg = stats_block(all_t)
        session_stats = {}
        for sess_name, _, _ in SESSION_BOUNDS:
            st = stats_block(buckets.get((strat, sess_name), []))
            session_stats[sess_name] = st
        strategies[strat] = {
            "aggregate": agg,
            "sessions": session_stats,
        }

    print(f"  {len(trades)} trades, {len(strategies)} strategies (N≥{min_n})")
    return {
        "pair": pair,
        "symbol": yf_symbol,
        "lookback_days": lookback,
        "interval": interval,
        "total_trades": len(trades),
        "overall_wr": result.get("win_rate"),
        "overall_ev": result.get("expected_value"),
        "strategies": strategies,
    }


def render_markdown(all_results: list[dict], lookback: int, interval: str,
                    min_n: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Session-Decomposition BT Scan",
        "",
        f"- **Generated**: {now}",
        f"- **Lookback**: {lookback}d / **Interval**: {interval}",
        f"- **Min N per (strategy × pair)**: {min_n}",
        "- **Sessions** (UTC, non-overlap):",
        "  - Tokyo: 00:00–07:00 / London: 07:00–13:00 / NY: 13:00–21:00 / Off: 21:00–24:00",
        "",
        "## 目的",
        "Tokyo 時間に edge がある戦略は存在するか？ portfolio の session-bias を可視化。",
        "",
        "## 全セル一覧 (Session 分解 × Pair × Strategy)",
        "",
        "| Pair | Strategy | All N | All EV | Tokyo (N / WR / EV) | London (N / WR / EV) | NY (N / WR / EV) | Off (N / WR / EV) |",
        "|------|----------|------:|-------:|--------------------|---------------------|------------------|-------------------|",
    ]

    rows = []
    for r in all_results:
        if "error" in r:
            lines.append(f"| {r['pair']} | — | — | — | — | — | — | — |")
            continue
        for strat, st in r["strategies"].items():
            agg = st["aggregate"]
            sess = st["sessions"]
            def fmt(s):
                if s.get("n", 0) == 0:
                    return "— / — / —"
                return f"{s['n']} / {s['wr']:.0f}% / {s['ev']:+.2f}"
            rows.append({
                "pair": r["pair"],
                "strategy": strat,
                "all_n": agg["n"],
                "all_ev": agg["ev"],
                "tokyo_n": sess["Tokyo"].get("n", 0),
                "tokyo_ev": sess["Tokyo"].get("ev", 0) if sess["Tokyo"].get("n", 0) else None,
                "london_ev": sess["London"].get("ev", 0) if sess["London"].get("n", 0) else None,
                "ny_ev": sess["NY"].get("ev", 0) if sess["NY"].get("n", 0) else None,
                "tokyo": fmt(sess["Tokyo"]),
                "london": fmt(sess["London"]),
                "ny": fmt(sess["NY"]),
                "off": fmt(sess["Off"]),
            })

    rows.sort(key=lambda x: (-x["all_n"],))

    for row in rows:
        lines.append(
            f"| {row['pair']} | {row['strategy']} | {row['all_n']} | {row['all_ev']:+.2f} "
            f"| {row['tokyo']} | {row['london']} | {row['ny']} | {row['off']} |"
        )

    # Tokyo-specific edges: N >= min_n AND EV > 0 in Tokyo
    tokyo_edges = [
        r for r in rows
        if r["tokyo_n"] >= min_n and r["tokyo_ev"] is not None and r["tokyo_ev"] > 0
    ]
    tokyo_edges.sort(key=lambda x: -x["tokyo_ev"])

    lines += [
        "",
        f"## 🗼 Tokyo-Session Edge Candidates (N≥{min_n}, EV>0)",
        "",
    ]
    if not tokyo_edges:
        lines.append("**該当なし** — Tokyo 時間に正 EV edge を持つ戦略×ペアは存在しない。")
    else:
        lines.append("| Pair | Strategy | Tokyo N | Tokyo EV | London EV | NY EV | 備考 |")
        lines.append("|------|----------|--------:|---------:|----------:|------:|------|")
        for r in tokyo_edges:
            london = f"{r['london_ev']:+.2f}" if r["london_ev"] is not None else "—"
            ny = f"{r['ny_ev']:+.2f}" if r["ny_ev"] is not None else "—"
            note = ""
            if r["london_ev"] is None or (r["london_ev"] is not None and r["london_ev"] <= 0):
                if r["ny_ev"] is None or (r["ny_ev"] is not None and r["ny_ev"] <= 0):
                    note = "**Tokyo-only edge**"
            elif r["tokyo_ev"] > max(r["london_ev"] or -99, r["ny_ev"] or -99):
                note = "Tokyo 優位"
            lines.append(
                f"| {r['pair']} | {r['strategy']} | {r['tokyo_n']} | {r['tokyo_ev']:+.2f} "
                f"| {london} | {ny} | {note} |"
            )

    # Session aggregate: all pairs × strategies combined
    sess_totals = {s: {"n": 0, "ev_sum": 0.0, "wins": 0, "pnl": 0.0}
                   for s in ["Tokyo", "London", "NY", "Off"]}
    for r in all_results:
        if "error" in r:
            continue
        for strat, st in r["strategies"].items():
            for sess_name in ["Tokyo", "London", "NY", "Off"]:
                s = st["sessions"][sess_name]
                n = s.get("n", 0)
                if n == 0:
                    continue
                sess_totals[sess_name]["n"] += n
                sess_totals[sess_name]["ev_sum"] += s["ev"] * n
                sess_totals[sess_name]["pnl"] += s["pnl"]
                sess_totals[sess_name]["wins"] += int(s["wr"] / 100 * n)

    lines += [
        "",
        "## Portfolio Session Aggregate (全 pair × 全 strategy)",
        "",
        "| Session | Total N | WR | Weighted EV | Total PnL | Share of N |",
        "|---------|--------:|---:|------------:|----------:|-----------:|",
    ]
    total_n_all = sum(v["n"] for v in sess_totals.values())
    for sess_name in ["Tokyo", "London", "NY", "Off"]:
        v = sess_totals[sess_name]
        if v["n"] == 0:
            lines.append(f"| {sess_name} | 0 | — | — | — | 0% |")
            continue
        wr = v["wins"] / v["n"] * 100
        wev = v["ev_sum"] / v["n"]
        share = v["n"] / total_n_all * 100 if total_n_all else 0
        lines.append(
            f"| {sess_name} | {v['n']} | {wr:.1f}% | {wev:+.3f} | {v['pnl']:+.2f} | {share:.1f}% |"
        )

    lines += [
        "",
        "## 判断プロトコル遵守 (CLAUDE.md)",
        "- 本スキャンは 1 回 BT の post-hoc 分解 → 実装判断は **保留** (lesson-reactive-changes)",
        "- Tokyo-edge 発見 → 別期間 (730d or w60 walk-forward) で再検証必須",
        "- session-specific filter 実装前に Shadow N≥30 での確認が必要",
        "",
        "## Source",
        "- Post-hoc classification of `app.run_daytrade_backtest` trade_log by entry_time hour (UTC)",
        "- Generated by: `tools/bt_session_zoo.py`",
    ]

    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="", help="Comma-separated OANDA pairs (default: all 5)")
    ap.add_argument("--lookback", type=int, default=365)
    ap.add_argument("--interval", default="15m")
    ap.add_argument("--min-n", type=int, default=10)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    if args.pairs:
        wanted = {p.strip().upper() for p in args.pairs.split(",")}
        pairs = [(yf, pair) for yf, pair in DEFAULT_PAIRS if pair in wanted]
    else:
        pairs = DEFAULT_PAIRS

    all_results = []
    for yf, pair in pairs:
        res = scan_symbol(yf, pair, args.lookback, args.interval, args.min_n)
        all_results.append(res)

    md = render_markdown(all_results, args.lookback, args.interval, args.min_n)

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = _PROJECT_ROOT / "knowledge-base" / "raw" / "bt-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = Path(args.out_md) if args.out_md else out_dir / f"session-zoo-{date}.md"
    json_path = Path(args.out_json) if args.out_json else out_dir / f"session-zoo-{date}.json"

    md_path.write_text(md, encoding="utf-8")
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, default=str, ensure_ascii=False, indent=2)

    print(f"\n✅ Report: {md_path}")
    print(f"   JSON:   {json_path}")


if __name__ == "__main__":
    main()
