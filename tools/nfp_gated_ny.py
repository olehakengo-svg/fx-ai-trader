#!/usr/bin/env python3
"""News-Gated NY Session Filter — N1 hypothesis analyzer

理論:
  NY session の friction は主要 US 経済指標発表時に集中する (Andersen et al. 2003)。
  主要発表時刻 (UTC):
    - 12:30 UTC: NFP, CPI, Retail Sales, GDP, Initial Jobless Claims
    - 14:00 UTC: FOMC statement, Fed minutes (monthly)
    - 18:00 UTC: FOMC rate decision (FOMC days)

  発表前後 ±30 分を除外すると、NY trade の WR/EV が向上するか検定。

非侵襲:
  - BT trade_log を post-hoc 分類
  - 既存 run_daytrade_backtest を呼んで結果を news-window フィルタ

分類:
  - pre-news:   entry ∈ [release - 30m, release - 1m]
  - news-hot:   entry ∈ [release - 1m, release + 30m]
  - post-news:  entry ∈ [release + 30m, release + 2h]
  - news-free:  それ以外の NY trade

判断プロトコル (CLAUDE.md):
  - 観測のみ。live 実装は walk-forward 730d 後
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

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

# 主要 US 発表の定刻 (UTC)
#   12:30 = 7:30am ET winter / 8:30am ET summer (DST shift)
#     NFP (first Fri of month), CPI (mid-month), Retail Sales, GDP, Jobless Claims (every Thu)
#   14:00 = FOMC minutes (3 weeks after meeting)
#   18:00 = FOMC rate decision (8 meetings/year)
#
# このスキャナでは:
#   - 毎 Thursday の 12:30 UTC (Jobless Claims)
#   - 毎月 first Friday の 12:30 UTC (NFP)
#   - 毎月 15 前後 12:30 UTC (CPI, Retail Sales)
#   を静的生成して近似する。
#
# 本番運用では ForexFactory / FRED API を使うべきだが、本 post-hoc 分析では
# 発表密集日 (Thu + first Fri + mid-month) を合成することで近似する。

MAJOR_NEWS_HOURS = (12, 30)     # UTC 12:30 — NFP/CPI/Retail/GDP/Claims 共通
FOMC_RATE_HOUR = (18, 0)        # UTC 18:00 — FOMC rate decision
FOMC_MINUTES_HOUR = (14, 0)     # UTC 14:00 — FOMC minutes


def generate_news_events(start_date: datetime, end_date: datetime):
    """Return list of (event_ts_utc, event_type) for approximation."""
    from datetime import timedelta
    events = []
    d = start_date
    while d < end_date:
        # 毎 Thursday: Jobless Claims (UTC 12:30)
        if d.weekday() == 3:
            ev = d.replace(hour=MAJOR_NEWS_HOURS[0], minute=MAJOR_NEWS_HOURS[1], second=0, microsecond=0)
            events.append((ev, "Claims"))
        # First Friday of month: NFP (UTC 12:30)
        if d.weekday() == 4 and d.day <= 7:
            ev = d.replace(hour=MAJOR_NEWS_HOURS[0], minute=MAJOR_NEWS_HOURS[1], second=0, microsecond=0)
            events.append((ev, "NFP"))
        # Mid-month weekday: CPI / Retail Sales proxy (UTC 12:30)
        if 13 <= d.day <= 16 and d.weekday() < 5:
            ev = d.replace(hour=MAJOR_NEWS_HOURS[0], minute=MAJOR_NEWS_HOURS[1], second=0, microsecond=0)
            events.append((ev, "CPI/Retail"))
        # FOMC meetings — approximate 8/year: Mar/Apr/May/Jun/Jul/Sep/Oct/Nov/Dec, third Wed
        if d.month in {1, 3, 5, 6, 7, 9, 10, 11, 12} and d.weekday() == 2:
            week_of_month = (d.day - 1) // 7 + 1
            if week_of_month == 3:
                ev = d.replace(hour=FOMC_RATE_HOUR[0], minute=FOMC_RATE_HOUR[1], second=0, microsecond=0)
                events.append((ev, "FOMC"))
        d += timedelta(days=1)
    return events


def classify_trade_vs_news(entry_ts: datetime, events: list):
    """Return ('pre-news'|'news-hot'|'post-news'|'news-free', event_type, delta_min)."""
    from datetime import timedelta
    # Binary search would be faster but N is small (~250 events × ~8000 trades = 2M comp, OK)
    closest = None
    closest_delta = None
    for ev_ts, ev_type in events:
        delta = (entry_ts - ev_ts).total_seconds() / 60.0  # minutes
        if abs(delta) < abs(closest_delta or 1e9):
            closest_delta = delta
            closest = (ev_ts, ev_type)
    if closest is None:
        return "news-free", None, None
    delta = closest_delta
    ev_type = closest[1]
    if -30 <= delta < -1:
        return "pre-news", ev_type, delta
    if -1 <= delta <= 30:
        return "news-hot", ev_type, delta
    if 30 < delta <= 120:
        return "post-news", ev_type, delta
    return "news-free", None, None


def pip_mult(pair: str) -> float:
    return 0.01 if "JPY" in pair else 0.0001


def compute_pnl_pip(trade: dict, pair: str) -> float:
    try:
        pnl = trade.get("pnl_pip")
        if pnl is not None:
            return float(pnl)
        entry = float(trade.get("entry_price", 0))
        exit_p = float(trade.get("exit_price", 0))
        direction = trade.get("direction", "LONG").upper()
        sign = 1 if direction == "LONG" else -1
        return sign * (exit_p - entry) / pip_mult(pair)
    except Exception:
        return 0.0


def parse_ts(s):
    try:
        ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    except Exception:
        return None


def analyze_pair(yf_symbol: str, pair: str, lookback_days: int, events: list):
    print(f"\n[nfp-gated-ny] {pair} ({yf_symbol})")
    import app as app_module
    try:
        bt_result = app_module.run_daytrade_backtest(yf_symbol, lookback_days=lookback_days)
    except Exception as e:
        print(f"[ERROR] BT failed: {e}")
        return None
    trade_log = bt_result.get("trade_log", []) if isinstance(bt_result, dict) else []
    if not trade_log:
        return None

    by_bucket = {"news-free": [], "pre-news": [], "news-hot": [], "post-news": []}
    ny_trades = 0
    for t in trade_log:
        et_raw = t.get("entry_time") or t.get("entry_datetime")
        if not et_raw:
            continue
        ets = parse_ts(et_raw)
        if ets is None:
            continue
        h = ets.hour
        if not (13 <= h < 21):  # NY session only
            continue
        ny_trades += 1
        bucket, ev_type, delta = classify_trade_vs_news(ets, events)
        pnl = compute_pnl_pip(t, pair)
        strat = t.get("entry_type", "unknown")
        by_bucket[bucket].append({
            "pnl_pip": pnl,
            "win": int(pnl > 0),
            "strategy": strat,
            "event": ev_type,
            "delta_min": delta,
        })

    def stats(rows):
        if not rows:
            return None
        pnl = np.array([r["pnl_pip"] for r in rows])
        wins = np.array([r["win"] for r in rows])
        pos_pnl = pnl[pnl > 0].sum()
        neg_pnl = abs(pnl[pnl < 0].sum())
        return {
            "n": len(rows),
            "wr": float(wins.mean() * 100),
            "ev": float(pnl.mean()),
            "pnl_total": float(pnl.sum()),
            "pf": float(pos_pnl / neg_pnl) if neg_pnl > 1e-6 else float("inf"),
        }

    result = {
        "pair": pair,
        "ny_trades_total": ny_trades,
        "buckets": {k: stats(v) for k, v in by_bucket.items()},
    }
    return result


def render_report(results, events, out_md, out_json):
    lines = [
        "# News-Gated NY Session Filter (N1)",
        "",
        f"- **Generated**: {datetime.now(timezone.utc).isoformat()}",
        f"- **News events approximated**: {len(events)}",
        "  - Every Thursday UTC 12:30 (Jobless Claims)",
        "  - First Friday UTC 12:30 (NFP)",
        "  - Mid-month weekday UTC 12:30 (CPI/Retail proxy)",
        "  - Third-Wednesday UTC 18:00 (FOMC)",
        "",
        "## 読み方",
        "- **pre-news (-30 .. -1 min)**: 発表直前 — friction 上昇開始",
        "- **news-hot (-1 .. +30 min)**: 発表瞬間 — spread widening, 勝率低下予想",
        "- **post-news (+30 min .. +2h)**: 発表後余韻 — trend 継続も",
        "- **news-free**: その他の NY trade",
        "",
        "**仮説**: news-free >> news-hot の EV 差。news-free > overall NY EV なら フィルタ効果あり。",
        "",
    ]

    # Summary table
    lines.append("## Summary (pair × bucket)")
    lines.append("| Pair | Bucket | N | WR% | EV (pip) | PnL | PF |")
    lines.append("|------|--------|--:|----:|---------:|----:|---:|")
    for res in results:
        pair = res["pair"]
        for bucket in ["news-free", "pre-news", "news-hot", "post-news"]:
            s = res["buckets"].get(bucket)
            if s:
                pf_str = f"{s['pf']:.2f}" if s['pf'] != float("inf") else "∞"
                lines.append(f"| {pair} | {bucket} | {s['n']} | {s['wr']:.1f}% | {s['ev']:+.3f} | {s['pnl_total']:+.2f} | {pf_str} |")
    lines.append("")

    lines.extend([
        "## 判断プロトコル (CLAUDE.md)",
        "- 観測のみ。GO 条件:",
        "  (a) news-free EV ≥ overall NY EV + 0.1 pip",
        "  (b) news-hot EV < 0 (avoid 期待値マイナス)",
        "  (c) news-free N ≥ 100 (統計的有意性)",
        "- 成立しても Shadow N≥30 + walk-forward 730d 必須",
        "",
        "## Caveats",
        "- 静的 news calendar は近似。本番運用では ForexFactory API などを使うべき",
        "- 個別 event impact は未区別 (NFP と Claims を同重み)",
        "- 日中 Trump/Fed speech などの不定期 event は捕捉できない",
        "",
        "## Source",
        "- Generated by: tools/nfp_gated_ny.py",
        "- Related: wiki/analyses/edge-matrix-2026-04-23.md N1 仮説",
    ])

    out_md.write_text("\n".join(lines))
    out_json.write_text(json.dumps(results, indent=2, default=str))
    print(f"[done] {out_md}")
    print(f"[done] {out_json}")


def main():
    from datetime import timedelta
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=",".join([p[1] for p in DEFAULT_PAIRS]))
    ap.add_argument("--lookback", type=int, default=365)
    args = ap.parse_args()

    wanted = set(s.strip() for s in args.pairs.split(","))
    pairs = [(yf, p) for yf, p in DEFAULT_PAIRS if p in wanted]

    # Generate news calendar
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.lookback + 10)
    events = generate_news_events(start, end)
    print(f"[nfp-gated-ny] Generated {len(events)} news events over {args.lookback}d")

    results = []
    for yf_symbol, pair in pairs:
        try:
            r = analyze_pair(yf_symbol, pair, args.lookback, events)
            if r:
                results.append(r)
        except Exception as e:
            print(f"[ERROR] {pair}: {e}")
            import traceback
            traceback.print_exc()

    out_dir = _PROJECT_ROOT / "knowledge-base" / "raw" / "bt-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_md = out_dir / f"nfp-gated-ny-{today}.md"
    out_json = out_dir / f"nfp-gated-ny-{today}.json"
    render_report(results, events, out_md, out_json)


if __name__ == "__main__":
    main()
