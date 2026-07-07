#!/usr/bin/env python3
"""
limit_fill_predictor.py — 指値約定の予測器 (約定確率 × 約定後EV) + 見送り効果の解明

背景 (このセッションの到達点):
  生エッジ +0.8〜1.3pip < リテール成行 friction 2pip。唯一 friction を超えたのは
  sweep&reclaim の「指値約定」(holdout +0.85, friction0.5-1.0)。
  指値が勝つ正体は (a) 良い価格 (スプレッド回避+戻りで有利) と
  (b) 見送り効果 (levelに戻らない=強い逆行=大負け場面で指値は約定せず自動回避) の 2 つ。
  本ツールは各 sweep&reclaim シグナルに特徴量・約定ラベル・指値PnL・仮想成行PnLを付与し、
  「約定しやすく かつ 約定後に勝てる」条件を IC で予測可能化する。同時に見送り効果を定量し、
  指値の優位が本物のフィルタか後知恵バイアスかを切り分ける。

絶対規律:
  1. 因果: 特徴量は reclaim 足 i の確定時点で既知のもののみ。約定/PnL は i+1 以降の intrabar。
  2. 見送り効果は「仮想成行PnL」を全シグナルで計算 (約定有無に関わらず reclaim足close で成行入った場合)。
     E[market|filled] vs E[market|not filled] の差が「指値が回避した損」。
  3. train/holdout 分離。silent except 禁止。
  4. IC は連続特徴量と (約定bool / 約定後net_pip) の Spearman。閾値最適化しない。

CLI:
  python3 tools/limit_fill_predictor.py --pair EUR_USD --fric-limit 0.7 --fric-market 2.0

モジュールトップ副作用禁止。
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cache" / "massive"
WINDOW_START = pd.Timestamp("2022-01-01", tz="UTC")
WINDOW_END = pd.Timestamp("2026-05-15", tz="UTC")
TRAIN_FRAC = 0.60

FRACTAL_N = 2
RECLAIM_BARS = 6
LEVEL_MAX_AGE = 96
LEVEL_MIN_AGE = FRACTAL_N + 1
ATR_LEN = 14
SL_BUF = 0.3
TP_MULT = 2.0
MAX_HOLD = 48
LIMIT_WAIT = 6
STRICT_BAR = 1.0          # 大口介入: sweepバー range/ATR 下限 (前回の最良)
ATR_MED_WIN = 480         # atr_regime 用長期中央値窓 (15m, ≈5日)


def _pip(p):
    return 0.01 if p.endswith("_JPY") else 0.0001


def _atr(df, n=ATR_LEN):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def _ema(s, span):
    return s.ewm(span=span, adjust=False).mean()


@dataclass
class Skip:
    c: Counter = field(default_factory=Counter)

    def add(self, r, k=1):
        self.c[r] += k

    def rep(self):
        return "\n".join(f"  - {r}: {n}" for r, n in self.c.most_common()) or "  (0)"


@dataclass
class Pivot:
    confirm_idx: int
    price: float
    kind: str


def detect_pivots(high, low, n=FRACTAL_N):
    out = []
    m = len(high)
    for i in range(n, m - n):
        wh = high[i - n: i + n + 1]
        wl = low[i - n: i + n + 1]
        cc = n
        if high[i] == wh.max() and (high[i] > np.delete(wh, cc)).all():
            out.append(Pivot(i + n, float(high[i]), "high"))
        if low[i] == wl.min() and (low[i] < np.delete(wl, cc)).all():
            out.append(Pivot(i + n, float(low[i]), "low"))
    out.sort(key=lambda p: p.confirm_idx)
    return out


def _exit_pnl(o, h, l, c, n, anchor, entry, sl_px, tp_px, direction, pip, friction, max_hold):
    """anchor 足の次から intrabar SL/TP/timestop で決済し net_pip を返す。"""
    last = min(anchor + max_hold, n - 1)
    ex = None
    for k in range(anchor + 1, last + 1):
        if direction == 1:
            if l[k] <= sl_px:
                ex = sl_px; break
            if h[k] >= tp_px:
                ex = tp_px; break
        else:
            if h[k] >= sl_px:
                ex = sl_px; break
            if l[k] <= tp_px:
                ex = tp_px; break
    if ex is None:
        ex = c[last]
    return (ex - entry) / pip * direction - friction


def build(pair, m15, h1, fric_limit, fric_market, skips):
    pip = _pip(pair)
    m15 = m15.copy()
    close = m15["Close"]
    m15["atr"] = _atr(m15)
    m15["atr_med"] = m15["atr"].rolling(ATR_MED_WIN, min_periods=60).median()
    o = m15["Open"].to_numpy(); h = m15["High"].to_numpy()
    l = m15["Low"].to_numpy(); c = close.to_numpy()
    atr = m15["atr"].to_numpy(); atr_med = m15["atr_med"].to_numpy()
    idx = m15.index
    n = len(m15)

    # HTF 1h EMA align (causal)
    h1 = h1.copy()
    ef = _ema(h1["Close"], 21).to_numpy(); es = _ema(h1["Close"], 55).to_numpy()
    h1ct = (h1.index + pd.Timedelta(hours=1)).values.astype("int64")
    pos = np.searchsorted(h1ct, idx.values.astype("int64"), side="right") - 1
    htf_bull = np.full(n, np.nan)
    ok = pos >= 0
    htf_bull[ok] = (ef[pos[ok]] > es[pos[ok]]).astype(float)

    pivots = detect_pivots(h, l, FRACTAL_N)
    highs = [p for p in pivots if p.kind == "high"]
    lows = [p for p in pivots if p.kind == "low"]
    hi_conf = np.array([p.confirm_idx for p in highs]); hi_px = np.array([p.price for p in highs])
    lo_conf = np.array([p.confirm_idx for p in lows]); lo_px = np.array([p.price for p in lows])

    rows = []
    pos_until = -1
    for i in range(ATR_LEN + FRACTAL_N + 2, n - 1):
        if i <= pos_until:
            continue
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        am = atr_med[i]
        if not np.isfinite(am) or am <= 0:
            continue
        w0 = max(i - RECLAIM_BARS, 0)
        sig_dir = 0; level_px = ext = jbar = None
        # SELL: resistance sweep & reclaim
        ks = np.searchsorted(hi_conf, i - LEVEL_MIN_AGE, side="right")
        for j in range(ks - 1, -1, -1):
            if i - hi_conf[j] > LEVEL_MAX_AGE:
                break
            P = hi_px[j]
            if c[i] >= P:
                continue
            seg = h[w0:i + 1]
            if not (seg > P).any():
                continue
            jrel = int(np.argmax(seg)); jb = w0 + jrel; e = float(seg[jrel])
            if atr[jb] > 0 and (h[jb] - l[jb]) / atr[jb] < STRICT_BAR:
                continue
            sig_dir = -1; level_px = P; ext = e; jbar = jb; conf_idx = hi_conf[j]; break
        if sig_dir == 0:
            ks = np.searchsorted(lo_conf, i - LEVEL_MIN_AGE, side="right")
            for j in range(ks - 1, -1, -1):
                if i - lo_conf[j] > LEVEL_MAX_AGE:
                    break
                P = lo_px[j]
                if c[i] <= P:
                    continue
                seg = l[w0:i + 1]
                if not (seg < P).any():
                    continue
                jrel = int(np.argmin(seg)); jb = w0 + jrel; e = float(seg[jrel])
                if atr[jb] > 0 and (h[jb] - l[jb]) / atr[jb] < STRICT_BAR:
                    continue
                sig_dir = 1; level_px = P; ext = e; jbar = jb; conf_idx = lo_conf[j]; break
        if sig_dir == 0:
            continue

        # ── 特徴量 (reclaim 足 i の確定時点で既知) ──
        sweep_bar_atr = (h[jbar] - l[jbar]) / atr[jbar] if atr[jbar] > 0 else 0.0
        sweep_depth_atr = abs(ext - level_px) / a
        reclaim_body_atr = abs(c[i] - o[i]) / a
        # reclaim_frac: level からどれだけ戻ったか (close と level の距離 / sweep深度)
        reclaim_frac = abs(level_px - c[i]) / max(abs(ext - level_px), 1e-9)
        atr_regime = a / am
        hour = idx[i].hour
        hb = htf_bull[i]
        htf_align = 0.0
        if np.isfinite(hb):
            # bias(逆張り)方向と HTF の整合: SELL かつ HTF bear=+1, BUY かつ HTF bull=+1
            htf_align = 1.0 if ((sig_dir == 1 and hb == 1.0) or (sig_dir == -1 and hb == 0.0)) else -1.0
        level_age = float(i - conf_idx)

        # ── 約定判定 (limit: level に戻るか) ──
        lwait = min(i + LIMIT_WAIT, n - 1)
        fill_k = None
        for k in range(i + 1, lwait + 1):
            if sig_dir == -1 and h[k] >= level_px:
                fill_k = k; break
            if sig_dir == 1 and l[k] <= level_px:
                fill_k = k; break
        filled = fill_k is not None

        # ── SL/TP geometry (limit entry=level / market entry=close[i]) ──
        if sig_dir == 1:
            sl_l = ext - a * SL_BUF; tp_l = level_px + a * TP_MULT
            sl_m = ext - a * SL_BUF; tp_m = c[i] + a * TP_MULT
        else:
            sl_l = ext + a * SL_BUF; tp_l = level_px - a * TP_MULT
            sl_m = ext + a * SL_BUF; tp_m = c[i] - a * TP_MULT

        # limit net (filled のみ): entry=level, manage from fill_k+1
        limit_net = np.nan
        if filled and ((sig_dir == 1 and sl_l < level_px) or (sig_dir == -1 and sl_l > level_px)):
            limit_net = _exit_pnl(o, h, l, c, n, fill_k, level_px, sl_l, tp_l, sig_dir, pip, fric_limit, MAX_HOLD)
        # market net (全件): entry=close[i], manage from i+1
        market_net = np.nan
        if (sig_dir == 1 and sl_m < c[i]) or (sig_dir == -1 and sl_m > c[i]):
            market_net = _exit_pnl(o, h, l, c, n, i, c[i], sl_m, tp_m, sig_dir, pip, fric_market, MAX_HOLD)

        rows.append(dict(
            time=idx[i], dir=sig_dir, filled=filled,
            sweep_bar_atr=sweep_bar_atr, sweep_depth_atr=sweep_depth_atr,
            reclaim_body_atr=reclaim_body_atr, reclaim_frac=reclaim_frac,
            atr_regime=atr_regime, hour=float(hour), htf_align=htf_align, level_age=level_age,
            limit_net=limit_net, market_net=market_net,
        ))
        # dedup: 約定したらそのexitまで、不約定なら limit_wait まで占有
        pos_until = (fill_k if filled else lwait)

    return pd.DataFrame(rows)


FEATURES = ["sweep_bar_atr", "sweep_depth_atr", "reclaim_body_atr", "reclaim_frac",
            "atr_regime", "hour", "htf_align", "level_age"]


def spearman(x, y):
    m = x.notna() & y.notna()
    xn, yn = x[m], y[m]
    if len(xn) < 20 or xn.nunique() < 3:
        return np.nan, np.nan, int(m.sum())
    rho, p = stats.spearmanr(xn, yn)
    return float(rho), float(p), int(m.sum())


def report(pair, ev, fric_limit, fric_market):
    n = len(ev)
    nf = int(ev["filled"].sum())
    print("\n" + "=" * 76)
    print(f"# {pair} 指値約定予測器  signals={n}  約定={nf} ({100*nf/n:.1f}%)")
    print(f"  friction: limit={fric_limit} market={fric_market}")
    print("=" * 76)

    # ── 見送り効果 (指値エッジの正体) ──
    filled = ev[ev["filled"]]
    notf = ev[~ev["filled"]]
    em_fill = filled["market_net"].mean()
    em_notf = notf["market_net"].mean()
    el_fill = filled["limit_net"].mean()
    print("\n── 見送り効果 (指値エッジの正体) ──")
    print(f"  約定群の仮想成行EV   E[market|filled]     = {em_fill:+.3f}pip (N={len(filled)})")
    print(f"  不約定群の仮想成行EV E[market|not filled] = {em_notf:+.3f}pip (N={len(notf)})")
    print(f"  → 見送り効果 = {em_fill - em_notf:+.3f}pip (正なら指値は良い場面を選別=本物のフィルタ)")
    print(f"  約定群の指値EV       E[limit|filled]      = {el_fill:+.3f}pip")
    print(f"  → 良い価格効果 = E[limit|filled]-E[market|filled] = {el_fill - em_fill:+.3f}pip "
          f"(指値entryの価格改善+friction差)")

    # ── 特徴量 IC ──
    bonf = 0.05 / len(FEATURES)
    # (1) 約定確率: 全シグナルで feature vs filled(0/1)
    # (2) 約定後EV: 約定群で feature vs limit_net
    for label, sub, target in [
        ("約定確率 (filled 0/1)", ev, ev["filled"].astype(float)),
        ("約定後EV (limit_net | filled)", filled, filled["limit_net"]),
    ]:
        print(f"\n── 特徴量 IC vs {label} [Bonferroni α={bonf:.4f}, ★=p<α ·=p<0.05] ──")
        print(f"  {'feature':<18}{'IC':>9}{'p':>11}{'N':>8}  sig")
        rows = []
        for f in FEATURES:
            rho, p, nn = spearman(sub[f], target)
            rows.append((f, rho, p, nn))
        rows.sort(key=lambda r: (-abs(r[1]) if np.isfinite(r[1]) else 0))
        for f, rho, p, nn in rows:
            if not np.isfinite(rho):
                print(f"  {f:<18}{'n/a':>9}{'n/a':>11}{nn:>8}  -")
                continue
            star = "★" if (np.isfinite(p) and p < bonf) else ("·" if p < 0.05 else "")
            print(f"  {f:<18}{rho:>9.4f}{p:>11.2e}{nn:>8}  {star}")


def predict_select(tr, ho):
    """約定後EVの予測特徴量で score を作り (train標準化)、score上位群の約定後EVを
    train/holdout で比較。選別でEVが上がり holdout で再現すれば予測の仕組みが機能。
    score = z(reclaim_frac) - z(sweep_depth_atr) - z(atr_regime)  (約定後EV IC の符号に合わせる)"""
    trf = tr[tr["filled"] & tr["limit_net"].notna()].copy()
    hof = ho[ho["filled"] & ho["limit_net"].notna()].copy()
    if len(trf) < 100 or len(hof) < 100:
        print("\n(予測選別: N不足)"); return
    feats = [("reclaim_frac", 1), ("sweep_depth_atr", -1), ("atr_regime", -1)]
    params = {}
    for f, sign in feats:
        mu, sd = trf[f].mean(), trf[f].std()
        params[f] = (mu, sd if sd > 0 else 1.0, sign)

    def score(df):
        s = pd.Series(0.0, index=df.index)
        for f, (mu, sd, sign) in params.items():
            s = s + sign * (df[f] - mu) / sd
        return s
    trf["score"] = score(trf); hof["score"] = score(hof)
    print("\n── 予測スコア選別による約定後EV (train標準化 → holdout検証) ──")
    print("   score = z(reclaim_frac) - z(sweep_depth) - z(atr_regime)")
    print(f"  {'群':<14}{'TRAIN (N / EV)':>22}{'HOLDOUT (N / EV)':>22}")
    print(f"  {'全約定':<14}{f'{len(trf)} / {trf.limit_net.mean():+.3f}':>22}"
          f"{f'{len(hof)} / {hof.limit_net.mean():+.3f}':>22}")
    for q in [0.5, 0.7, 0.8, 0.9]:
        thr = trf["score"].quantile(q)  # train の閾値を holdout にも適用 (絶対値固定)
        ts = trf[trf["score"] >= thr]; hs = hof[hof["score"] >= thr]
        lab = f"score上位{int(round((1-q)*100))}%"
        te = f"{len(ts)} / {ts.limit_net.mean():+.3f}" if len(ts) else "0 / -"
        he = f"{len(hs)} / {hs.limit_net.mean():+.3f}" if len(hs) else "0 / -"
        print(f"  {lab:<14}{te:>22}{he:>22}")


def run(pair, fric_limit, fric_market):
    skips = Skip()
    f15 = DATA_DIR / f"{pair}_15m.parquet"; f1h = DATA_DIR / f"{pair}_1h.parquet"
    if not f15.exists() or not f1h.exists():
        print(f"[{pair}] データ欠損", file=sys.stderr); return 1
    m15 = pd.read_parquet(f15); h1 = pd.read_parquet(f1h)
    for d in (m15, h1):
        if d.index.tz is None:
            d.index = d.index.tz_localize("UTC")
    m15 = m15[(m15.index >= WINDOW_START) & (m15.index <= WINDOW_END)]
    h1 = h1[(h1.index >= WINDOW_START) & (h1.index <= WINDOW_END)]

    ev = build(pair, m15, h1, fric_limit, fric_market, skips)
    if ev.empty:
        print("シグナル0件"); print(skips.rep()); return 0

    split = m15.index[int(len(m15) * TRAIN_FRAC)]
    tr = ev[ev["time"] < split]; ho = ev[ev["time"] >= split]
    print(f"\n窓 {m15.index.min().date()}〜{m15.index.max().date()}  split={split.date()}")
    print("\n########## TRAIN (前半60%) ##########")
    report(pair, tr, fric_limit, fric_market)
    print("\n########## HOLDOUT (後半40%) ##########")
    report(pair, ho, fric_limit, fric_market)
    print("\n########## 予測選別 (train標準化→holdout検証) ##########")
    predict_select(tr, ho)
    return 0


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="指値約定の予測器 + 見送り効果解明")
    ap.add_argument("--pair", default="EUR_USD")
    ap.add_argument("--fric-limit", type=float, default=0.7)
    ap.add_argument("--fric-market", type=float, default=2.0)
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    return run(args.pair, args.fric_limit, args.fric_market)


if __name__ == "__main__":
    raise SystemExit(main())
