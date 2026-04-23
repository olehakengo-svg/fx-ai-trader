#!/usr/bin/env python3
"""Tokyo Range Breakout — Walk-Forward Validation (T3)

目的:
  tokyo_range_breakout.py で発見した USD_JPY UP breakout edge (WR 72.4%, mean +17.67pip)
  が「期間依存なエッジ」か「構造的エッジ」かを 2 分割 walk-forward で検証。

方法:
  365 日を 2 window に分割:
    - IS (in-sample):  first  183 日 (~6 months)
    - OOS (out-of-sample): next 182 日 (~6 months)
  両 window で独立に T3 統計を計算し、consistency を判定。

判定基準:
  - IS と OOS の mean pip 差 < 30% → stable
  - IS と OOS の WR 差 < 10pp → stable
  - OOS mean > 0 かつ OOS WR > 55% → out-of-sample で edge 生存

判断プロトコル (CLAUDE.md):
  - 観測のみ。両 window 成立しても Shadow N≥30 必須
  - WF 検証を通らなかった edge は放棄 (カーブフィッティング判定)
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


def compute_daily_breakouts(df: pd.DataFrame, pair: str) -> list:
    pm = pip_mult(pair)
    out = []
    for day, grp in df.groupby("date"):
        tok = grp[(grp["hour"] >= 0) & (grp["hour"] < 7)]
        lon_open = grp[(grp["hour"] >= 7) & (grp["hour"] < 9)]
        lon_follow = grp[(grp["hour"] >= 9) & (grp["hour"] < 13)]
        if len(tok) < 20 or len(lon_open) < 4 or len(lon_follow) < 4:
            continue
        tok_high = tok["high"].max()
        tok_low = tok["low"].min()
        lon_open_max = lon_open["high"].max()
        lon_open_min = lon_open["low"].min()
        breakout_up = lon_open_max > tok_high
        breakout_down = lon_open_min < tok_low
        entry_close = float(lon_open["close"].iloc[0])
        follow_close = float(lon_follow["close"].iloc[-1])
        net_return_pip = (follow_close - entry_close) / pm

        if breakout_up and not breakout_down:
            direction = "UP"
            signed_return = net_return_pip
        elif breakout_down and not breakout_up:
            direction = "DOWN"
            signed_return = -net_return_pip
        elif breakout_up and breakout_down:
            direction = "BOTH"
            signed_return = 0.0
        else:
            direction = "NONE"
            signed_return = net_return_pip

        out.append({
            "date": str(day),
            "direction": direction,
            "signed_return_pip": signed_return,
        })
    return out


def stats_by_direction(rows: list) -> dict:
    res = {}
    for d in ["UP", "DOWN", "NONE"]:
        sub = [r for r in rows if r["direction"] == d]
        if not sub:
            res[d] = None
            continue
        vals = np.array([r["signed_return_pip"] for r in sub])
        wins = (vals > 0).sum()
        res[d] = {
            "n": len(sub),
            "mean_pip": float(vals.mean()),
            "std_pip": float(vals.std()),
            "wr_positive": float(wins / len(sub) * 100),
            "t_stat": float(vals.mean() / (vals.std() / np.sqrt(len(sub)))) if vals.std() > 0 else 0.0,
        }
    return res


def verdict(is_stats: dict, oos_stats: dict, direction: str) -> dict:
    """Compare IS vs OOS for a given breakout direction."""
    is_s = is_stats.get(direction)
    oos_s = oos_stats.get(direction)
    if not is_s or not oos_s:
        return {"verdict": "INSUFFICIENT_DATA"}

    mean_diff_pct = abs(is_s["mean_pip"] - oos_s["mean_pip"]) / (abs(is_s["mean_pip"]) + 1e-6) * 100
    wr_diff_pp = abs(is_s["wr_positive"] - oos_s["wr_positive"])
    oos_alive = oos_s["mean_pip"] > 0 and oos_s["wr_positive"] > 55

    stability_ok = mean_diff_pct < 30 and wr_diff_pp < 10

    if oos_alive and stability_ok:
        v = "STABLE_EDGE"
    elif oos_alive and not stability_ok:
        v = "NOISY_BUT_ALIVE"
    elif not oos_alive and is_s["mean_pip"] > 3:
        v = "CURVE_FITTED"
    else:
        v = "WEAK"

    return {
        "verdict": v,
        "is_mean": is_s["mean_pip"],
        "is_wr": is_s["wr_positive"],
        "oos_mean": oos_s["mean_pip"],
        "oos_wr": oos_s["wr_positive"],
        "mean_diff_pct": round(mean_diff_pct, 1),
        "wr_diff_pp": round(wr_diff_pp, 1),
        "oos_alive": oos_alive,
        "stability_ok": stability_ok,
    }


def analyze_pair(yf_symbol: str, pair: str, lookback_days: int = 365):
    print(f"\n[t3-wfa] {pair} ({yf_symbol})")
    df = fetch_ohlcv(yf_symbol, period=f"{lookback_days}d", interval="15m")
    if df is None or df.empty or len(df) < 200:
        return None

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    if "datetime" in df.columns:
        df["ts"] = pd.to_datetime(df["datetime"], utc=True)
    else:
        df["ts"] = pd.to_datetime(df.index, utc=True)
    df["date"] = df["ts"].dt.date
    df["hour"] = df["ts"].dt.hour

    # Split by median date
    all_dates = sorted(df["date"].unique())
    mid = len(all_dates) // 2
    is_dates = set(all_dates[:mid])
    oos_dates = set(all_dates[mid:])

    is_df = df[df["date"].isin(is_dates)]
    oos_df = df[df["date"].isin(oos_dates)]

    is_rows = compute_daily_breakouts(is_df, pair)
    oos_rows = compute_daily_breakouts(oos_df, pair)

    is_stats = stats_by_direction(is_rows)
    oos_stats = stats_by_direction(oos_rows)

    up_verdict = verdict(is_stats, oos_stats, "UP")
    down_verdict = verdict(is_stats, oos_stats, "DOWN")

    return {
        "pair": pair,
        "is_window": {"start": str(all_dates[0]), "end": str(all_dates[mid-1]), "days": len(is_dates)},
        "oos_window": {"start": str(all_dates[mid]), "end": str(all_dates[-1]), "days": len(oos_dates)},
        "is_stats": is_stats,
        "oos_stats": oos_stats,
        "up_verdict": up_verdict,
        "down_verdict": down_verdict,
    }


def render_report(results, out_md, out_json):
    lines = [
        "# Tokyo Range Breakout — Walk-Forward Validation (T3)",
        "",
        f"- **Generated**: {datetime.now(timezone.utc).isoformat()}",
        "- **Method**: 365d を 2 分割 (IS 182d / OOS 182d) で consistency 検証",
        "- **Verdict**:",
        "  - STABLE_EDGE: OOS alive & IS-OOS 差 < 30%/10pp → カーブフィッティングではない",
        "  - NOISY_BUT_ALIVE: OOS alive だが IS-OOS 差大 → sample-size 依存",
        "  - CURVE_FITTED: IS strong だが OOS 消滅 → 過学習",
        "  - WEAK: 元々弱い",
        "",
    ]

    for res in results:
        pair = res["pair"]
        lines.append(f"## {pair}")
        lines.append("")
        lines.append(f"- IS window: {res['is_window']['start']} .. {res['is_window']['end']} ({res['is_window']['days']} days)")
        lines.append(f"- OOS window: {res['oos_window']['start']} .. {res['oos_window']['end']} ({res['oos_window']['days']} days)")
        lines.append("")

        lines.append("### IS vs OOS by direction")
        lines.append("| Dir | Window | N | mean (pip) | WR(>0)% | t-stat |")
        lines.append("|-----|--------|--:|-----------:|--------:|-------:|")
        for d in ["UP", "DOWN", "NONE"]:
            is_s = res["is_stats"].get(d)
            oos_s = res["oos_stats"].get(d)
            if is_s:
                lines.append(f"| {d} | IS  | {is_s['n']} | {is_s['mean_pip']:+.2f} | {is_s['wr_positive']:.1f}% | {is_s['t_stat']:+.2f} |")
            if oos_s:
                lines.append(f"| {d} | OOS | {oos_s['n']} | {oos_s['mean_pip']:+.2f} | {oos_s['wr_positive']:.1f}% | {oos_s['t_stat']:+.2f} |")
        lines.append("")

        lines.append("### Verdicts")
        for name, v in [("UP breakout", res["up_verdict"]), ("DOWN breakout", res["down_verdict"])]:
            if v.get("verdict") == "INSUFFICIENT_DATA":
                lines.append(f"- **{name}**: INSUFFICIENT_DATA")
                continue
            marker = "🟢" if v["verdict"] == "STABLE_EDGE" else ("🟡" if v["verdict"] == "NOISY_BUT_ALIVE" else "🔴")
            lines.append(f"- **{name}** {marker} **{v['verdict']}**")
            lines.append(f"  - IS: {v['is_mean']:+.2f}pip / {v['is_wr']:.1f}%")
            lines.append(f"  - OOS: {v['oos_mean']:+.2f}pip / {v['oos_wr']:.1f}%")
            lines.append(f"  - mean diff: {v['mean_diff_pct']:.1f}%, WR diff: {v['wr_diff_pp']:.1f}pp")
            lines.append(f"  - oos_alive={v['oos_alive']}, stability_ok={v['stability_ok']}")
        lines.append("")

    lines.extend([
        "## 判断プロトコル (CLAUDE.md)",
        "- STABLE_EDGE: Shadow N≥30 蓄積で live 検討可",
        "- NOISY_BUT_ALIVE: 追加 window で 3-fold 検証必要",
        "- CURVE_FITTED: 放棄",
        "- WEAK: 再検討価値なし",
        "",
        "## Source",
        "- Generated by: tools/tokyo_range_breakout_wfa.py",
        "- Related: tools/tokyo_range_breakout.py, knowledge-base/raw/bt-results/tokyo-range-breakout-2026-04-23.md",
    ])

    out_md.write_text("\n".join(lines))
    out_json.write_text(json.dumps(results, indent=2, default=str))
    print(f"[done] {out_md}")


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
    out_md = out_dir / f"tokyo-range-breakout-wfa-{today}.md"
    out_json = out_dir / f"tokyo-range-breakout-wfa-{today}.json"
    render_report(results, out_md, out_json)


if __name__ == "__main__":
    main()
