"""WGF Audit — Weekend Gap Fade.

仮説 (French-Roll 1986):
  金曜 NY close 〜 月曜 Tokyo open のギャップは、週末ニュースへの
  retail panic 反応で overshoot を含む。Asia session 0-2h で fade。

Output: raw/wgf_audit/wgf_audit_{date}.md
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import numpy as np
import pandas as pd

try:
    from scipy.stats import binomtest as _bt
    def _binom(k, n, p):
        return _bt(k=k, n=n, p=p, alternative="greater").pvalue
except ImportError:
    from scipy.stats import binom_test as _bt
    def _binom(k, n, p):
        return _bt(k, n, p, alternative="greater")


def _wilson(wins, n):
    if n == 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, c - h), min(1.0, c + h))


PAIRS = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]


def _load(pair, days):
    from tools.bt_data_cache import BTDataCache
    cache = BTDataCache()
    df = cache.get(pair, "15m", days=days)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    df = df[df.index >= cutoff].copy()
    h, l, c = df["High"].astype(float), df["Low"].astype(float), df["Close"].astype(float)
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()],
                   axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    return df.dropna(subset=["atr"])


def find_weekend_gaps(df: pd.DataFrame, pair: str,
                      gap_atr_min: float = 0.3,
                      asia_window_bars: int = 8) -> pd.DataFrame:
    """Detect Mon Tokyo open gaps vs Fri NY close.

    Friday NY close ≈ last bar of Friday (UTC ~ 22:00 Friday)
    Monday Tokyo open ≈ first bar Monday after gap (UTC ~22:00 Sunday)
    Asia window: first 2 hours = 8 × 15min bars
    """
    pip = 0.01 if "JPY" in pair else 0.0001
    df = df.copy()
    df["dow"] = df.index.dayofweek  # 0=Mon, 4=Fri, 6=Sun
    df["hour"] = df.index.hour
    df["date"] = df.index.date

    rows = []
    # Group by week
    df["week"] = df.index.isocalendar().week
    df["year"] = df.index.isocalendar().year
    for (yr, wk), grp in df.groupby(["year", "week"]):
        # Find last Friday bar
        fri = grp[grp["dow"] == 4]
        if len(fri) == 0:
            continue
        fri_close = float(fri["Close"].iloc[-1])
        fri_atr = float(fri["atr"].iloc[-1])
        fri_time = fri.index[-1]

        # Find first Monday Tokyo open (Mon dow=0 OR Sun late = dow=6 after 22 UTC)
        mon_or_sun = grp[(grp["dow"] == 0) | ((grp["dow"] == 6) & (grp["hour"] >= 22))]
        mon_or_sun = mon_or_sun[mon_or_sun.index > fri_time]
        if len(mon_or_sun) < asia_window_bars:
            continue
        open_bar = mon_or_sun.iloc[0]
        open_price = float(open_bar["Open"])

        gap_pip = (open_price - fri_close) / pip
        gap_atr_ratio = abs(open_price - fri_close) / fri_atr if fri_atr > 0 else 0

        if gap_atr_ratio < gap_atr_min:
            continue

        # Asia window outcome: did price retrace at least 50% of gap?
        window = mon_or_sun.iloc[:asia_window_bars]
        # If gap was UP, retracement = price drops below (fri_close + open_price)/2
        # If gap was DOWN, retracement = price rises above
        target_50 = (fri_close + open_price) / 2  # 50% retrace target
        signal = -np.sign(gap_pip)  # fade direction

        # Track: did price hit 50% retrace within window?
        hit_50 = False
        bars_to_50 = None
        for i, row in window.iterrows():
            if signal > 0:  # fade UP gap → expect price drop
                if float(row["Low"]) <= target_50:
                    hit_50 = True
                    bars_to_50 = (i - open_bar.name).total_seconds() / 900
                    break
            else:  # fade DOWN gap → expect price rise
                if float(row["High"]) >= target_50:
                    hit_50 = True
                    bars_to_50 = (i - open_bar.name).total_seconds() / 900
                    break

        # Final close after window
        final_close = float(window["Close"].iloc[-1])
        retrace_pip = signal * (final_close - open_price) / pip

        rows.append({
            "fri_close": fri_close,
            "open_price": open_price,
            "gap_pip": gap_pip,
            "gap_atr_ratio": gap_atr_ratio,
            "fri_atr_pip": fri_atr / pip,
            "hit_50": hit_50,
            "bars_to_50": bars_to_50,
            "asia_close_retrace_pip": retrace_pip,
            "open_time": open_bar.name,
        })

    return pd.DataFrame(rows)


def analyze_gaps(gaps: pd.DataFrame) -> dict:
    if len(gaps) < 5:
        return {"n": int(len(gaps)), "insufficient": True}
    n = len(gaps)
    n_hit_50 = int(gaps["hit_50"].sum())
    rate_50 = n_hit_50 / n
    wlo50, whi50 = _wilson(n_hit_50, n)
    p_50 = _binom(n_hit_50, n, p=0.5)

    # Asia close retrace > 0
    n_pos = int((gaps["asia_close_retrace_pip"] > 0).sum())
    rate_pos = n_pos / n
    wlo_p, whi_p = _wilson(n_pos, n)
    p_pos = _binom(n_pos, n, p=0.5)

    avg_retrace = float(gaps["asia_close_retrace_pip"].mean())
    avg_gap = float(gaps["gap_pip"].abs().mean())
    return {
        "n": n,
        "rate_50_retrace": round(rate_50, 4),
        "wilson_50_lo": round(wlo50, 4),
        "p_50": round(p_50, 5),
        "asia_close_pos_rate": round(rate_pos, 4),
        "wilson_close_lo": round(wlo_p, 4),
        "p_close_pos": round(p_pos, 5),
        "avg_gap_pip": round(avg_gap, 2),
        "avg_retrace_pip": round(avg_retrace, 2),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", nargs="+", default=PAIRS)
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--gap-atr-min", type=float, default=0.3)
    p.add_argument("--output", default="raw/wgf_audit/")
    args = p.parse_args()

    results = []
    for pair in args.pairs:
        print(f"=== WGF {pair} ===", flush=True)
        try:
            df = _load(pair, args.days)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            continue
        gaps = find_weekend_gaps(df, pair, gap_atr_min=args.gap_atr_min)
        print(f"  Gaps detected (>={args.gap_atr_min} ATR): {len(gaps)}", flush=True)
        if len(gaps) < 5:
            continue
        r = analyze_gaps(gaps)
        r["pair"] = pair
        results.append(r)
        print(f"  50% retrace: {r['rate_50_retrace']:.3f} (Wilson_lo={r['wilson_50_lo']:.3f}, "
              f"p={r['p_50']:.4f})", flush=True)
        print(f"  Asia close positive: {r['asia_close_pos_rate']:.3f} "
              f"(Wilson_lo={r['wilson_close_lo']:.3f}, p={r['p_close_pos']:.4f})",
              flush=True)
        print(f"  Avg gap: {r['avg_gap_pip']:.1f} pip / Avg retrace: {r['avg_retrace_pip']:+.1f} pip",
              flush=True)

    n_tests = len(results) * 2  # 2 metrics per pair
    print(f"\nBonferroni family: {n_tests} (2 metrics × {len(results)} pairs)",
          flush=True)
    for r in results:
        bonf_50 = r["p_50"] * n_tests
        bonf_close = r["p_close_pos"] * n_tests
        sig_50 = "✅" if bonf_50 < 0.05 else "✗"
        sig_cl = "✅" if bonf_close < 0.05 else "✗"
        print(f"  {r['pair']}: 50%retrace bonf={bonf_50:.4f} {sig_50}, "
              f"close_pos bonf={bonf_close:.4f} {sig_cl}", flush=True)

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"wgf_audit_{date_tag}.json"
    md_path = out_dir / f"wgf_audit_{date_tag}.md"

    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    md = ["# WGF Audit (Weekend Gap Fade)", ""]
    md.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"Days: {args.days}, gap_atr_min: {args.gap_atr_min}")
    md.append("")
    md.append("## Per-pair results")
    md.append("| pair | n | 50%retrace_rate | Wilson_lo | p_50 | close_pos_rate | "
              "Wilson_lo | p_close | avg_gap | avg_retrace |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        md.append(f"| {r['pair']} | {r['n']} | {r['rate_50_retrace']:.3f} | "
                  f"{r['wilson_50_lo']:.3f} | {r['p_50']:.4f} | "
                  f"{r['asia_close_pos_rate']:.3f} | "
                  f"{r['wilson_close_lo']:.3f} | {r['p_close_pos']:.4f} | "
                  f"{r['avg_gap_pip']:.1f} | {r['avg_retrace_pip']:+.1f} |")
    md.append(f"\nBonferroni family: {n_tests}")
    with open(md_path, "w") as f:
        f.write("\n".join(md))
    print(f"\nJSON: {json_path}\nMD: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
