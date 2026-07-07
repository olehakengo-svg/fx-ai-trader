#!/usr/bin/env python3
"""
session_bias_explore.py — session_time_bias (実需フロー時間構造) の複数年定常性検証

背景:
  session_time_bias は BT WR67-79% (USD_JPY EV+0.58) だが Live 壊滅 (N=9 WR22%, N=4 WR0%) で
  ELITE→UNIVERSAL_SENTINEL 降格。理論 (Breedon-Ranaldo 2013: 自国時間帯に通貨減価, 21年9ペア有意) は
  強いのに Live で負ける。本ツールは 1h 足で複数年 (2022-2026) BT し、
  「フロー時間エッジは定常か」「BT79%→Live負けの正体」を年次分解 + friction感度で解明する。

ロジック (strategies/daytrade/session_time_bias.py の時間窓×方向を移植, 1h版):
  Tokyo  (UTC 0-3): USD_JPY BUY
  London (UTC 7-10): GBP_USD SELL, EUR_GBP BUY
  NY     (UTC 13-15): USD_JPY BUY
  確認: bias 方向のローソク (BUY=陽線/SELL=陰線)。SL=ATR1h×1.5, TP=×2.0, time-stop 8本(8h)。
  1 セッション 1 トレード (dedup)。

絶対規律: 因果 (entry=確定足close, exit次足以降intrabar)。friction はKB friction-analysis実測値。
          train/holdout + 年次で定常性を見る。silent except 禁止。
モジュールトップ副作用禁止。
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cache" / "massive"
WINDOW_START = pd.Timestamp("2022-01-01", tz="UTC")
WINDOW_END = pd.Timestamp("2026-05-15", tz="UTC")
TRAIN_FRAC = 0.60
ATR_LEN = 14
SL_MULT, TP_MULT = 1.5, 2.0
MAX_HOLD = 8  # 1h bars = 8h 保有上限

# KB friction-analysis 実測 RT (pip)
FRICTION = {"USD_JPY": 2.14, "GBP_USD": 4.53, "EUR_GBP": 3.0, "EUR_USD": 2.0}
# entry window: pair -> [(hour_start, hour_end, direction)]  direction: +1 BUY / -1 SELL
WINDOWS = {
    "USD_JPY": [(0, 3, 1), (13, 15, 1)],   # Tokyo BUY, NY BUY (JPY減価/USD強)
    "GBP_USD": [(7, 10, -1)],              # London SELL (GBP減価)
    "EUR_GBP": [(7, 10, 1)],               # London BUY (GBP減価)
}


def pip_size(p):
    return 0.01 if p.endswith("_JPY") else 0.0001


def _atr(df, n=ATR_LEN):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def wilson(w, n, z=1.96):
    if n == 0:
        return 0, 0, 0
    p = w / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - half, c + half


@dataclass
class Skip:
    c: Counter = field(default_factory=Counter)

    def add(self, r, k=1):
        self.c[r] += k

    def rep(self):
        return "\n".join(f"  - {r}: {n}" for r, n in self.c.most_common()) or "  (0)"


def simulate(pair, df, friction, confirm, skips):
    pip = pip_size(pair)
    df = df.copy()
    df["atr"] = _atr(df)
    o = df["Open"].to_numpy(); h = df["High"].to_numpy()
    l = df["Low"].to_numpy(); c = df["Close"].to_numpy()
    atr = df["atr"].to_numpy(); idx = df.index
    n = len(df)
    wins = WINDOWS.get(pair, [])
    if not wins:
        return pd.DataFrame()
    trades = []
    pos_until = -1
    done = set()  # (date, hour_start) で 1 セッション 1 回 dedup
    for i in range(ATR_LEN + 1, n - 1):
        if i <= pos_until:
            continue
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        hr = idx[i].hour
        d = 0
        sess_key = None
        slab = None
        for hs, he, dd in wins:
            if hs <= hr < he:
                key = (idx[i].date(), hs)
                if key in done:
                    skips.add("session already traded")
                    break
                d = dd; sess_key = key
                slab = f"{hs:02d}h"
                break
        if d == 0:
            continue
        if confirm:
            if d == 1 and not (c[i] > o[i]):
                skips.add("candle not in bias dir"); continue
            if d == -1 and not (c[i] < o[i]):
                skips.add("candle not in bias dir"); continue
        entry = c[i]
        if d == 1:
            sl, tp = entry - a * SL_MULT, entry + a * TP_MULT
        else:
            sl, tp = entry + a * SL_MULT, entry - a * TP_MULT
        last = min(i + MAX_HOLD, n - 1)
        ex = rs = None
        for k in range(i + 1, last + 1):
            if d == 1:
                if l[k] <= sl:
                    ex, rs = sl, "sl"; break
                if h[k] >= tp:
                    ex, rs = tp, "tp"; break
            else:
                if h[k] >= sl:
                    ex, rs = sl, "sl"; break
                if l[k] <= tp:
                    ex, rs = tp, "tp"; break
        if ex is None:
            ex, rs, k = c[last], "timestop", last
        gross = (ex - entry) / pip * d
        net = gross - friction
        trades.append(dict(time=idx[i], dir=d, sess=slab, net_pip=net, win=net > 0, reason=rs))
        done.add(sess_key)
        pos_until = k
    return pd.DataFrame(trades)


def agg(df):
    n = len(df)
    if n == 0:
        return dict(N=0, WR=0, PF=0, EV=0, sum=0, lo=0, hi=0)
    w = int(df.win.sum())
    gp = df.loc[df.net_pip > 0, "net_pip"].sum()
    gl = -df.loc[df.net_pip <= 0, "net_pip"].sum()
    pf = gp / gl if gl > 0 else (999 if gp > 0 else 0)
    p, lo, hi = wilson(w, n)
    return dict(N=n, WR=100 * p, PF=pf, EV=df.net_pip.mean(), sum=df.net_pip.sum(), lo=100 * lo, hi=100 * hi)


def block(t, df):
    a = agg(df)
    print(f"\n── {t} ──")
    print(f"  N={a['N']} WR={a['WR']:.1f}% (Wilson {a['lo']:.0f}-{a['hi']:.0f}) "
          f"PF={a['PF']:.2f} EV={a['EV']:+.2f}pip sum={a['sum']:+.0f}")


def run(pair, confirm):
    skips = Skip()
    f = DATA_DIR / f"{pair}_1h.parquet"
    if not f.exists():
        print(f"[{pair}] {f.name} 不在", file=sys.stderr); return 1
    df = pd.read_parquet(f)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df[(df.index >= WINDOW_START) & (df.index <= WINDOW_END)]
    fr = FRICTION.get(pair, 2.0)
    print("=" * 72)
    print(f"# session_time_bias 1h — {pair}  friction={fr}pip(RT実測)  confirm={confirm}")
    print("=" * 72)
    print(f"窓 {df.index.min().date()}〜{df.index.max().date()} 1h={len(df)}")
    tr = simulate(pair, df, fr, confirm, skips)
    if tr.empty:
        print("0 trades"); print(skips.rep()); return 0
    split = df.index[int(len(df) * TRAIN_FRAC)]
    block("全期間 (friction込)", tr)
    block("TRAIN", tr[tr.time < split])
    block("HOLDOUT", tr[tr.time >= split])
    tr0 = tr.copy(); tr0["net_pip"] = tr0["net_pip"] + fr; tr0["win"] = tr0["net_pip"] > 0
    block("全期間 friction0 (生エッジ)", tr0)
    tr2 = tr.copy(); tr2["year"] = tr2.time.dt.year
    print(f"\n── 年次 EV (friction={fr}) ── 符号が年で反転するなら非定常")
    for y, s in tr2.groupby("year"):
        a = agg(s)
        print(f"  {y} N={a['N']:>4} WR={a['WR']:.1f}% PF={a['PF']:.2f} EV={a['EV']:+.2f}{'  ←負' if a['EV'] <= 0 else ''}")
    print(f"\n exit: " + " ".join(f"{r}:{c}" for r, c in tr['reason'].value_counts().items()))
    print(f" skip:\n{skips.rep()}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="session_time_bias 複数年定常性検証 (1h)")
    ap.add_argument("--pair", default="USD_JPY,GBP_USD,EUR_GBP")
    ap.add_argument("--no-confirm", action="store_true", help="ローソク方向確認を外す")
    a = ap.parse_args(argv)
    for p in [x.strip() for x in a.pair.split(",") if x.strip()]:
        run(p, not a.no_confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
