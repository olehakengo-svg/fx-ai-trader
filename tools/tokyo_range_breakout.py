#!/usr/bin/env python3
"""Tokyo Range Breakout — T3 hypothesis analyzer

理論 (Andersen-Bollerslev 1997 + Ito-Hashimoto 2006):
  Tokyo session (UTC 0-7) の日中 range は相対的に狭く、
  London open (UTC 7-9) でその range を breakout する場合、
  流動性流入により trend 継続が発生する確率が高い。

Math:
  per day:
    Tokyo_range = max(H[0..7]) - min(L[0..7])
    Tokyo_high = max(H[0..7])
    Tokyo_low  = min(L[0..7])
    breakout_up   = close[UTC7-9] > Tokyo_high
    breakout_down = close[UTC7-9] < Tokyo_low

  H0: E[Δ_next_4h | breakout] = E[Δ_next_4h | no breakout]
  H1: |E[Δ_next_4h | breakout]| > |E[Δ_next_4h | no breakout]|

検定:
  - day level aggregation
  - breakout 方向の 4h return を計測

非侵襲:
  - 既存 fetch_ohlcv のみ
  - BT trade_log 不要 (raw bar-level statistic)

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
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
except Exception:
    pass

from modules.data import fetch_ohlcv

DEFAULT_PAIRS = [
    ("USDJPY=X", "USD_JPY"),
    ("EURUSD=X", "EUR_USD"),
    ("GBPUSD=X", "GBP_USD"),
    ("EURJPY=X", "EUR_JPY"),
    ("GBPJPY=X", "GBP_JPY"),
]


def pip_mult(pair: str) -> float:
    return 0.01 if "JPY" in pair else 0.0001


def analyze_pair(yf_symbol: str, pair: str, lookback_days: int = 365):
    print(f"\n[tokyo-range-breakout] {pair} ({yf_symbol})")
    period = f"{lookback_days}d"
    df = fetch_ohlcv(yf_symbol, period=period, interval="15m")
    if df is None or df.empty or len(df) < 200:
        print(f"[SKIP] insufficient data: {0 if df is None else len(df)}")
        return None

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    if "datetime" in df.columns:
        df["ts"] = pd.to_datetime(df["datetime"], utc=True)
    else:
        df["ts"] = pd.to_datetime(df.index, utc=True)
    df["date"] = df["ts"].dt.date
    df["hour"] = df["ts"].dt.hour
    pm = pip_mult(pair)

    # Per-day aggregation
    daily_results = []
    for day, grp in df.groupby("date"):
        tok = grp[(grp["hour"] >= 0) & (grp["hour"] < 7)]
        lon_open = grp[(grp["hour"] >= 7) & (grp["hour"] < 9)]
        lon_follow = grp[(grp["hour"] >= 9) & (grp["hour"] < 13)]
        if len(tok) < 20 or len(lon_open) < 4 or len(lon_follow) < 4:
            continue
        tok_high = tok["high"].max()
        tok_low = tok["low"].min()
        tok_range_pip = (tok_high - tok_low) / pm

        lon_open_max = lon_open["high"].max()
        lon_open_min = lon_open["low"].min()

        breakout_up = lon_open_max > tok_high
        breakout_down = lon_open_min < tok_low

        # Entry price = close of first london_open breakout bar (approximation: use lon_open first close)
        entry_close = float(lon_open["close"].iloc[0])
        follow_close = float(lon_follow["close"].iloc[-1])
        net_return_pip = (follow_close - entry_close) / pm  # LONG sign

        if breakout_up and not breakout_down:
            direction = "UP"
            signed_return = net_return_pip
        elif breakout_down and not breakout_up:
            direction = "DOWN"
            signed_return = -net_return_pip
        elif breakout_up and breakout_down:
            direction = "BOTH"
            signed_return = 0.0  # whipsaw, exclude
        else:
            direction = "NONE"
            signed_return = net_return_pip  # for no-breakout baseline, use absolute drift

        daily_results.append({
            "date": str(day),
            "tok_range_pip": tok_range_pip,
            "direction": direction,
            "signed_return_pip": signed_return,
            "abs_return_pip": abs(net_return_pip),
        })

    if not daily_results:
        return None

    # Aggregate by direction
    by_dir = {"UP": [], "DOWN": [], "BOTH": [], "NONE": []}
    for r in daily_results:
        by_dir[r["direction"]].append(r)

    def stats(rows, use_signed=True):
        if not rows:
            return None
        if use_signed:
            vals = np.array([r["signed_return_pip"] for r in rows])
        else:
            vals = np.array([r["abs_return_pip"] for r in rows])
        return {
            "n": len(rows),
            "mean_pip": float(vals.mean()),
            "median_pip": float(np.median(vals)),
            "std_pip": float(vals.std()),
            "wr_positive": float((vals > 0).mean() * 100),
        }

    # Quintile by Tokyo range
    all_rows = daily_results
    ranges = np.array([r["tok_range_pip"] for r in all_rows])
    cuts = np.quantile(ranges, np.linspace(0, 1, 6))
    range_quintiles = []
    for i in range(5):
        sub = [r for r in all_rows if cuts[i] <= r["tok_range_pip"] < (cuts[i + 1] if i < 4 else cuts[i + 1] + 1e-9)]
        if len(sub) < 5:
            continue
        s = stats(sub, use_signed=False)
        s["q"] = i + 1
        s["range_lo"] = float(cuts[i])
        s["range_hi"] = float(cuts[i + 1])
        range_quintiles.append(s)

    return {
        "pair": pair,
        "n_days": len(daily_results),
        "by_direction": {k: stats(v) for k, v in by_dir.items()},
        "range_quintiles": range_quintiles,
    }


def render_report(results, out_md, out_json):
    lines = [
        "# Tokyo Range Breakout — T3 Analysis",
        "",
        f"- **Generated**: {datetime.now(timezone.utc).isoformat()}",
        "- **Theory**: Andersen-Bollerslev (1997) + Ito-Hashimoto (2006)",
        "- **Windows**:",
        "  - Tokyo: UTC 0-7 (range calculation)",
        "  - London open: UTC 7-9 (breakout detection)",
        "  - London follow: UTC 9-13 (next 4h return measurement)",
        "",
        "## 読み方",
        "- **UP breakout**: London open が Tokyo high を upside breakout",
        "- **DOWN breakout**: London open が Tokyo low を downside breakout",
        "- **signed_return**: breakout 方向に揃えた return (UP は LONG 視点、DOWN は SHORT 視点)",
        "- **NONE**: Tokyo range 内に止まった日 (baseline)",
        "",
        "**仮説**: UP/DOWN の signed_return > NONE の |return|",
        "",
    ]

    for res in results:
        pair = res["pair"]
        lines.append(f"## {pair} (n_days={res['n_days']})")
        lines.append("")
        lines.append("### By breakout direction")
        lines.append("| Direction | N | mean (pip) | median (pip) | std (pip) | WR(>0)% |")
        lines.append("|-----------|--:|-----------:|-------------:|----------:|--------:|")
        for d in ["UP", "DOWN", "BOTH", "NONE"]:
            s = res["by_direction"].get(d)
            if s:
                lines.append(f"| {d} | {s['n']} | {s['mean_pip']:+.2f} | {s['median_pip']:+.2f} | {s['std_pip']:.2f} | {s['wr_positive']:.1f}% |")
        lines.append("")

        lines.append("### By Tokyo range quintile (abs return for all days in bin)")
        lines.append("| Q | Tokyo range (pip) | N | mean |return| (pip) | WR(>0)% |")
        lines.append("|---|-------------------|--:|---------------------:|--------:|")
        for q in res["range_quintiles"]:
            lines.append(f"| Q{q['q']} | {q['range_lo']:.1f}..{q['range_hi']:.1f} | {q['n']} | {q['mean_pip']:.2f} | {q['wr_positive']:.1f}% |")
        lines.append("")

    lines.extend([
        "## 判断プロトコル (CLAUDE.md)",
        "- 観測のみ。GO 条件:",
        "  (a) UP signed_return mean ≥ 3.0 pip AND DOWN signed_return mean ≥ 3.0 pip",
        "  (b) UP/DOWN WR ≥ 55%",
        "  (c) Q5 (wide Tokyo range) での breakout が Q1 より優位",
        "- 成立しても Shadow N≥30 + walk-forward 730d 必須",
        "",
        "## Source",
        "- Generated by: tools/tokyo_range_breakout.py",
        "- Related: wiki/analyses/edge-matrix-2026-04-23.md T3 仮説",
    ])

    out_md.write_text("\n".join(lines))
    out_json.write_text(json.dumps(results, indent=2, default=str))
    print(f"[done] {out_md}")
    print(f"[done] {out_json}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=",".join([p[1] for p in DEFAULT_PAIRS]))
    ap.add_argument("--lookback", type=int, default=365)
    args = ap.parse_args()

    wanted = set(s.strip() for s in args.pairs.split(","))
    pairs = [(yf, p) for yf, p in DEFAULT_PAIRS if p in wanted]

    results = []
    for yf_symbol, pair in pairs:
        try:
            r = analyze_pair(yf_symbol, pair, args.lookback)
            if r:
                results.append(r)
        except Exception as e:
            print(f"[ERROR] {pair}: {e}")
            import traceback
            traceback.print_exc()

    out_dir = _PROJECT_ROOT / "knowledge-base" / "raw" / "bt-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_md = out_dir / f"tokyo-range-breakout-{today}.md"
    out_json = out_dir / f"tokyo-range-breakout-{today}.json"
    render_report(results, out_md, out_json)


if __name__ == "__main__":
    main()
