#!/usr/bin/env python3
"""
sweep_reclaim_explore.py — 水平流動性 sweep & reclaim イベントのエッジ探索

思想 (このセッションの学び):
  オシレーター単体の方向トリガーは EUR_USD 15m で IC≈0 (織り込み済み)。
  勝っているのは「構造/イベント」(trendline_sweep=斜めTL の sweep, WR80%)。
  → 本ツールは「水平流動性 sweep & reclaim」(他人の SL が狩られる構造イベント) を
     トリガーにし、RSI/MACD/EMA/ADX は「方向トリガーでなくフィルタ」に格下げして検証する。
  理論: Osler (2003) リテールの逆指値は水平な直近高安に集中 → 大口が sweep して流動性獲得 → 反転。

絶対規律:
  1. 因果性: pivot は Williams Fractal(n) で center+n 本後に確定。sweep 判定は確定済み level のみ。
     entry=reclaim bar close で約定、exit は次 bar 以降の intrabar SL/TP。未来参照禁止。
  2. まず「イベント単体」(フィルタ off) の EV を測る → フィルタ ablation で改善するか。
  3. friction (EUR_USD RT 2.0pip) 込みで判定。train/holdout 分離。
  4. silent except 禁止。Regime でなく direction×session で分解。

CLI:
  python3 tools/sweep_reclaim_explore.py --pair EUR_USD --friction 2.0
  python3 tools/sweep_reclaim_explore.py --pair EUR_USD --friction 2.0 --filt session,adx

モジュールトップで副作用禁止。
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

# ── 凍結パラメータ ──
FRACTAL_N = 2          # pivot 確定 = center+n 本後
RECLAIM_BARS = 6       # sweep から reclaim までの最大バー数
LEVEL_MAX_AGE = 96     # level が「流動性として生きている」最大バー数 (24h)
LEVEL_MIN_AGE = FRACTAL_N + 1  # 確定直後の自己参照を避ける
ATR_LEN = 14
SL_BUF = 0.3           # SL = sweep extreme ± ATR*SL_BUF (trendline_sweep と同じ)
TP_MULT = 2.0          # TP = ATR*TP_MULT
MAX_HOLD = 48
# フィルタ閾値
ADX_LO, ADX_HI = 15.0, 45.0
RSI_LEN = 14
EMA_FAST, EMA_SLOW = 21, 55


def _pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


def _session_label(h: int) -> str:
    if h < 7:
        return "Tokyo"
    if h < 13:
        return "London"
    if h < 22:
        return "NY"
    return "Off"


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _atr(df: pd.DataFrame, period: int = ATR_LEN) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev = close.shift(1)
    tr = pd.concat([(high - low), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = RSI_LEN) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0.0).ewm(alpha=1.0 / period, adjust=False).mean()
    dn = (-d).clip(lower=0.0).ewm(alpha=1.0 / period, adjust=False).mean()
    rs = up / dn.replace(0.0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    up = high.diff()
    dn = -low.diff()
    plus_dm = ((up > dn) & (up > 0)) * up
    minus_dm = ((dn > up) & (dn > 0)) * dn
    prev = close.shift(1)
    tr = pd.concat([(high - low), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    pdi = 100 * plus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr.replace(0.0, np.nan)
    mdi = 100 * minus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr.replace(0.0, np.nan)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0.0, np.nan)
    return dx.ewm(alpha=1.0 / period, adjust=False).mean()


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return 0.0, 0.0, 0.0
    p = wins / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, c - h, c + h


@dataclass
class SkipCounter:
    counts: Counter = field(default_factory=Counter)

    def add(self, r: str, k: int = 1):
        self.counts[r] += k

    def report(self) -> str:
        if not self.counts:
            return "  (skip 0 件)"
        return "\n".join(f"  - {r}: {n}" for r, n in self.counts.most_common())


@dataclass
class Pivot:
    confirm_idx: int
    price: float
    kind: str  # "high"/"low"


def detect_pivots(high: np.ndarray, low: np.ndarray, n: int = FRACTAL_N) -> list[Pivot]:
    out = []
    m = len(high)
    for i in range(n, m - n):
        wh = high[i - n: i + n + 1]
        wl = low[i - n: i + n + 1]
        c = n
        if high[i] == wh.max() and (high[i] > np.delete(wh, c)).all():
            out.append(Pivot(i + n, float(high[i]), "high"))
        if low[i] == wl.min() and (low[i] < np.delete(wl, c)).all():
            out.append(Pivot(i + n, float(low[i]), "low"))
    out.sort(key=lambda p: p.confirm_idx)
    return out


def simulate(pair, m15, h1, filters: set, friction_pip: float, skips: SkipCounter,
             strict_bar: float = 0.0, strict_depth: float = 0.0, strict_reclaim: bool = False,
             htf_hours: int = 1, entry_mode: str = "market", limit_wait: int = 6) -> pd.DataFrame:
    """sweep & reclaim イベントをトリガーに BT。filters はインジ=フィルタの集合。
    厳格化: strict_bar=sweepバー range/ATR下限 (大口介入), strict_depth=sweep深度/ATR下限,
            strict_reclaim=reclaim足の方向確認 (SELL陰線/BUY陽線)。"""
    pip = _pip_size(pair)
    m15 = m15.copy()
    close = m15["Close"]
    m15["atr"] = _atr(m15)
    m15["rsi"] = _rsi(close)
    m15["adx"] = _adx(m15)
    o = m15["Open"].to_numpy(); h = m15["High"].to_numpy()
    l = m15["Low"].to_numpy(); c = close.to_numpy()
    atr = m15["atr"].to_numpy(); rsi = m15["rsi"].to_numpy(); adx = m15["adx"].to_numpy()
    idx = m15.index
    n = len(m15)

    # HTF (1h) EMA context (causal align)
    h1 = h1.copy()
    h1ef = _ema(h1["Close"], EMA_FAST); h1es = _ema(h1["Close"], EMA_SLOW)
    h1_close_t = (h1.index + pd.Timedelta(hours=htf_hours)).values.astype("int64")
    t15 = idx.values.astype("int64")
    pos = np.searchsorted(h1_close_t, t15, side="right") - 1
    h1_bull = np.full(n, np.nan);
    okp = pos >= 0
    ef = h1ef.to_numpy(); es = h1es.to_numpy()
    h1_bull[okp] = (ef[pos[okp]] > es[pos[okp]]).astype(float)

    pivots = detect_pivots(h, l, FRACTAL_N)
    highs = [p for p in pivots if p.kind == "high"]
    lows = [p for p in pivots if p.kind == "low"]
    hi_conf = np.array([p.confirm_idx for p in highs]); hi_px = np.array([p.price for p in highs])
    lo_conf = np.array([p.confirm_idx for p in lows]); lo_px = np.array([p.price for p in lows])

    def passes_filters(direction, i):
        # direction: +1 BUY / -1 SELL。フィルタは方向トリガーでなく「除外/確認」のみ。
        if "session" in filters and _session_label(idx[i].hour) not in ("London", "NY"):
            return False
        if "adx" in filters:
            if not np.isfinite(adx[i]) or not (ADX_LO <= adx[i] <= ADX_HI):
                return False
        if "htf" in filters:
            # sweep は逆張り (reversal) なので HTF と逆行を許すが、HTF と完全逆行の極端だけ除外:
            # BUY は HTF bear のみ許容外にしない。ここでは「HTF と同方向 or 中立」を確認に使う緩いフィルタ。
            hb = h1_bull[i]
            if np.isfinite(hb):
                if direction == 1 and hb == 0.0:
                    return False
                if direction == -1 and hb == 1.0:
                    return False
        if "rsi" in filters:
            # 確認: BUY は売られ気味 (rsi<55) で入る / SELL は買われ気味 (rsi>45)
            if direction == 1 and rsi[i] > 55:
                return False
            if direction == -1 and rsi[i] < 45:
                return False
        return True

    trades = []
    # active level: (price, confirm_idx, swept_extreme or None, sweep_start_idx)
    # sweep&reclaim を 1 level 1 回だけ発火 (dedup)。
    pos_until = -1
    # 各 level の状態管理は重いので、bar ループ内で「直近 LEVEL_MAX_AGE 内の確定 pivot」を走査
    for i in range(ATR_LEN + FRACTAL_N + 2, n - 1):
        if i <= pos_until:
            continue
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue

        sig_dir = 0
        sweep_extreme = None
        level_px = None
        w0 = max(i - RECLAIM_BARS, 0)
        o_i = o[i]
        # ── SELL: resistance (pivot high P) を sweep → 現足で下に reclaim (failed breakout) ──
        ksel = np.searchsorted(hi_conf, i - LEVEL_MIN_AGE, side="right")  # confirm_idx <= i-MIN_AGE
        for j in range(ksel - 1, -1, -1):
            if i - hi_conf[j] > LEVEL_MAX_AGE:
                break
            P = hi_px[j]
            if c[i] >= P:                       # まだ P 上 = reclaim していない
                continue
            seg = h[w0:i + 1]
            if not (seg > P).any():             # 窓内で P を上抜けしていない = sweep なし
                continue
            jrel = int(np.argmax(seg)); jbar = w0 + jrel
            ext = float(seg[jrel])
            # 厳格化 (満たさなければこの level はスキップ、次の level へ)
            if strict_bar > 0 and atr[jbar] > 0 and (h[jbar] - l[jbar]) / atr[jbar] < strict_bar:
                skips.add("sweep bar too small"); continue
            if strict_depth > 0 and (ext - P) / a < strict_depth:
                skips.add("sweep too shallow"); continue
            if strict_reclaim and not (c[i] < o_i):
                skips.add("reclaim not confirmed"); continue
            sig_dir = -1; sweep_extreme = ext; level_px = P; break
        # ── BUY: support (pivot low P) を sweep → 現足で上に reclaim ──
        if sig_dir == 0:
            ksel = np.searchsorted(lo_conf, i - LEVEL_MIN_AGE, side="right")
            for j in range(ksel - 1, -1, -1):
                if i - lo_conf[j] > LEVEL_MAX_AGE:
                    break
                P = lo_px[j]
                if c[i] <= P:
                    continue
                seg = l[w0:i + 1]
                if not (seg < P).any():
                    continue
                jrel = int(np.argmin(seg)); jbar = w0 + jrel
                ext = float(seg[jrel])
                if strict_bar > 0 and atr[jbar] > 0 and (h[jbar] - l[jbar]) / atr[jbar] < strict_bar:
                    skips.add("sweep bar too small"); continue
                if strict_depth > 0 and (P - ext) / a < strict_depth:
                    skips.add("sweep too shallow"); continue
                if strict_reclaim and not (c[i] > o_i):
                    skips.add("reclaim not confirmed"); continue
                sig_dir = 1; sweep_extreme = ext; level_px = P; break

        if sig_dir == 0:
            continue
        if not passes_filters(sig_dir, i):
            skips.add("filtered out")
            continue

        # ── 約定 (market=reclaim足close / limit=sweepされたlevel に指値を置き戻りを待つ) ──
        if entry_mode == "limit":
            fill_k = None
            lw = min(i + limit_wait, n - 1)
            for k in range(i + 1, lw + 1):
                if sig_dir == -1 and h[k] >= level_px:   # SELL limit at level: 上に戻ったら約定
                    fill_k = k; break
                if sig_dir == 1 and l[k] <= level_px:    # BUY limit at level: 下に戻ったら約定
                    fill_k = k; break
            if fill_k is None:
                skips.add("limit not filled"); continue
            entry = level_px
            anchor = fill_k
        else:
            entry = c[i]
            anchor = i

        if sig_dir == 1:
            sl_px = sweep_extreme - a * SL_BUF
            tp_px = entry + a * TP_MULT
            if sl_px >= entry:
                skips.add("bad SL geometry"); continue
        else:
            sl_px = sweep_extreme + a * SL_BUF
            tp_px = entry - a * TP_MULT
            if sl_px <= entry:
                skips.add("bad SL geometry"); continue

        last = min(anchor + MAX_HOLD, n - 1)
        exit_px = exit_reason = None
        for k in range(anchor + 1, last + 1):
            if sig_dir == 1:
                if l[k] <= sl_px:
                    exit_px, exit_reason = sl_px, "sl"; break
                if h[k] >= tp_px:
                    exit_px, exit_reason = tp_px, "tp"; break
            else:
                if h[k] >= sl_px:
                    exit_px, exit_reason = sl_px, "sl"; break
                if l[k] <= tp_px:
                    exit_px, exit_reason = tp_px, "tp"; break
        if exit_px is None:
            exit_px, exit_reason, k = c[last], "timestop", last

        gross = (exit_px - entry) / pip * sig_dir
        net = gross - friction_pip
        trades.append({
            "time": idx[i], "dir": sig_dir, "session": _session_label(idx[i].hour),
            "rr": abs(tp_px - entry) / abs(entry - sl_px), "net_pip": net, "win": net > 0,
            "reason": exit_reason,
        })
        pos_until = k

    return pd.DataFrame(trades)


def _agg(df):
    n = len(df)
    if n == 0:
        return dict(N=0, WR=0, PF=0, EV=0, sum=0, lo=0, hi=0)
    w = int(df["win"].sum())
    gp = df.loc[df.net_pip > 0, "net_pip"].sum()
    gl = -df.loc[df.net_pip <= 0, "net_pip"].sum()
    pf = gp / gl if gl > 0 else (999 if gp > 0 else 0)
    p, lo, hi = wilson(w, n)
    return dict(N=n, WR=100 * p, PF=pf, EV=df.net_pip.mean(), sum=df.net_pip.sum(), lo=100 * lo, hi=100 * hi)


def _block(title, df):
    a = _agg(df)
    print(f"\n── {title} ──")
    print(f"  全体: N={a['N']} WR={a['WR']:.1f}% (Wilson {a['lo']:.0f}-{a['hi']:.0f}) "
          f"PF={a['PF']:.2f} EV={a['EV']:+.2f}pip sum={a['sum']:+.0f}pip")
    if a["N"] == 0:
        return
    for d, lab in [(1, "BUY"), (-1, "SELL")]:
        s = _agg(df[df["dir"] == d])
        if s["N"]:
            flag = " ★" if (s["N"] >= 30 and s["lo"] > 50) else (" ·" if s["WR"] > 50 else "")
            print(f"  {lab:<5} N={s['N']:>4} WR={s['WR']:.1f}% PF={s['PF']:.2f} EV={s['EV']:+.2f}{flag}")
    for sess in ["Tokyo", "London", "NY", "Off"]:
        s = _agg(df[df["session"] == sess])
        if s["N"]:
            print(f"    {sess:<7} N={s['N']:>4} WR={s['WR']:.1f}% PF={s['PF']:.2f} EV={s['EV']:+.2f}")


def run_pair(pair, friction_pip, filters, strict_bar=0.0, strict_depth=0.0, strict_reclaim=False,
             tf="15m", entry_mode="market", limit_wait=6):
    skips = SkipCounter()
    # TF 切替: base TF と HTF を選ぶ。15m→HTF 1h、1h→HTF 4h。
    htf_map = {"15m": ("1h", 1), "1h": ("4h", 4)}
    htf_tf, htf_hours = htf_map.get(tf, ("1h", 1))
    f_base = DATA_DIR / f"{pair}_{tf}.parquet"; f_htf = DATA_DIR / f"{pair}_{htf_tf}.parquet"
    if not f_base.exists() or not f_htf.exists():
        print(f"[{pair}] データ欠損 ({f_base.name}/{f_htf.name})", file=sys.stderr); return 1
    m15 = pd.read_parquet(f_base); h1 = pd.read_parquet(f_htf)
    for d in (m15, h1):
        if d.index.tz is None:
            d.index = d.index.tz_localize("UTC")
    m15 = m15[(m15.index >= WINDOW_START) & (m15.index <= WINDOW_END)]
    h1 = h1[(h1.index >= WINDOW_START) & (h1.index <= WINDOW_END)]

    print("=" * 78)
    print(f"# sweep_reclaim — {pair} {tf} (HTF={htf_tf})  filters={sorted(filters) or '(なし=イベント単体)'}")
    print("=" * 78)
    print(f"窓 {m15.index.min().date()}〜{m15.index.max().date()} bars={len(m15)}  "
          f"friction={friction_pip}pip  entry={entry_mode}{f'(wait{limit_wait})' if entry_mode=='limit' else ''}")
    if strict_bar or strict_depth or strict_reclaim:
        print(f"厳格化: bar/ATR≥{strict_bar} depth/ATR≥{strict_depth} reclaim確認={strict_reclaim}")

    trades = simulate(pair, m15, h1, filters, friction_pip, skips, strict_bar, strict_depth, strict_reclaim,
                      htf_hours, entry_mode, limit_wait)
    if trades.empty:
        print("トレード 0 件"); print(skips.report()); return 0

    split_t = m15.index[int(len(m15) * TRAIN_FRAC)]
    tr = trades[trades.time < split_t]; ho = trades[trades.time >= split_t]
    print(f"split: train<{split_t.date()} N={len(tr)} | holdout N={len(ho)}")
    _block("全期間", trades)
    _block("TRAIN", tr)
    _block("HOLDOUT", ho)
    print(f"\n exit: " + " / ".join(f"{r}:{c}" for r, c in trades['reason'].value_counts().items()))
    print(f" 平均R:R = {trades['rr'].mean():.2f}")
    print(f"\n skip:\n{skips.report()}")
    return 0


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="sweep & reclaim event edge explorer")
    ap.add_argument("--pair", default="EUR_USD")
    ap.add_argument("--friction", type=float, default=2.0)
    ap.add_argument("--filt", default="", help="フィルタ comma: session,adx,htf,rsi (空=イベント単体)")
    ap.add_argument("--strict-bar", type=float, default=0.0, help="sweepバー range/ATR 下限 (大口介入, 例1.0)")
    ap.add_argument("--strict-depth", type=float, default=0.0, help="sweep深度/ATR 下限 (例0.5)")
    ap.add_argument("--strict-reclaim", action="store_true", help="reclaim足の方向確認")
    ap.add_argument("--tf", choices=["15m", "1h"], default="15m", help="ベースTF")
    ap.add_argument("--entry", choices=["market", "limit"], default="market", help="約定モデル")
    ap.add_argument("--limit-wait", type=int, default=6, help="指値の戻り待ちバー数")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    filters = {f.strip() for f in args.filt.split(",") if f.strip()}
    return run_pair(args.pair, args.friction, filters,
                    args.strict_bar, args.strict_depth, args.strict_reclaim,
                    args.tf, args.entry, args.limit_wait)


if __name__ == "__main__":
    raise SystemExit(main())
