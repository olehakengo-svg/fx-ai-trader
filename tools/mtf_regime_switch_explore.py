#!/usr/bin/env python3
"""
mtf_regime_switch_explore.py — TV Pine `mtf_regime_switch` の Python 複数年クロスチェック

目的:
  TV Strategy Tester は本アカウントで 15m≈10ヶ月 (N≈400) しか BT できない。
  そこで Parquet キャッシュ (EUR_USD 15m=12年, 1h/4h=4.4年) を使い、共通窓 2022-01〜2026-05
  (≈4.4年) で同一ロジックを回し、TV で観測した「SELL 優位の非対称」が
  構造エッジか特定期間の方向バイアスかを判別する。

  TV 版B (bt-results/tv-overlays/mtf_regime_switch-EURUSD-15m-fullhist.pine) と
  ロジックを厳密一致させる (1m/5m timing-confirm 無し版)。

絶対規律:
  1. 因果性: entry は signal bar close で約定 (TV process_orders_on_close=true 相当)。
     exit は entry の次 bar 以降の intrabar SL/TP / timestop。MTF (1h/4h) は確定 bar のみ参照 (lookahead 無し)。
  2. friction: 第1パスは friction=0 で TV 数値を再現確認 → 第2パスで EUR_USD RT=2.0pip を引いて EV 判定。
     順序が逆だと「TV と一致するか」のクロスチェックにならない。
  3. train/holdout: 前半 60% を main、後半 40% を holdout として両方出す。
  4. silent except 禁止。集計は Regime×方向×session の粒度 (aggregate WR は嘘をつく)。

CLI:
  python3 tools/mtf_regime_switch_explore.py --pair EUR_USD
  python3 tools/mtf_regime_switch_explore.py --pair EUR_USD --friction 2.0

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

# ── 共通窓 (4h が 2021-12-24 起点。h4_level_edge_explore と同じ起点に揃える) ──
WINDOW_START = pd.Timestamp("2022-01-01", tz="UTC")
WINDOW_END = pd.Timestamp("2026-05-15", tz="UTC")
TRAIN_FRAC = 0.60

# ── 凍結パラメータ (Pine 版B のデフォルトと一致) ──
EMA_FAST, EMA_MID, EMA_SLOW = 8, 21, 55
HTF_FAST, HTF_SLOW = 21, 55
RSI_LEN = 14
RSI_OS, RSI_OB = 30.0, 70.0
RSI_XHI, RSI_XLO = 80.0, 20.0
MACD_FAST, MACD_SLOW, MACD_SIG = 12, 26, 9
DIV_LB = 8            # proxy 版の lookback
DIV_FRACTAL_N = 2     # pivot 版: Williams Fractal n (center±n、確定は center+n 本後)
PULL_LB = 6
ATR_LEN = 14
SL_MR, TP_MR = 1.2, 1.5
SL_TR, TP_TR = 1.5, 2.5
MAX_HOLD = 24


def _session_label(hour_utc: int) -> str:
    # Pine と同じ: <7 Tokyo, <13 London, <22 NY, else Off
    if hour_utc < 7:
        return "Tokyo"
    if hour_utc < 13:
        return "London"
    if hour_utc < 22:
        return "NY"
    return "Off"


def _pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


# ── 指標 (causal) ──
def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _atr(df: pd.DataFrame, period: int = ATR_LEN) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev = close.shift(1)
    tr = pd.concat([(high - low), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = RSI_LEN) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    # Pine ta.rsi は RMA (Wilder smoothing)
    roll_up = up.ewm(alpha=1.0 / period, adjust=False).mean()
    roll_down = down.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = roll_up / roll_down.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _macd_hist(close: pd.Series) -> pd.Series:
    macd_line = _ema(close, MACD_FAST) - _ema(close, MACD_SLOW)
    sig = _ema(macd_line, MACD_SIG)
    return macd_line - sig


def _pivot_divergence(low: np.ndarray, high: np.ndarray, osc: np.ndarray,
                      n: int = DIV_FRACTAL_N) -> tuple[np.ndarray, np.ndarray]:
    """本物のダイバージェンス (pivot ベース, causal)。
    - swing low/high を Williams Fractal n で検出 (center が窓内で厳密 min/max)。
    - bull: 価格 lower-low + oscillator higher-low (連続する 2 つの swing low を比較)。
    - bear: 価格 higher-high + oscillator lower-high。
    シグナルは pivot 確定バー (center+n) で True (center の low/osc はその時点で既知 = lookahead 無し)。
    """
    m = len(low)
    bull = np.zeros(m, dtype=bool)
    bear = np.zeros(m, dtype=bool)
    last_lo_price = last_lo_osc = None
    last_hi_price = last_hi_osc = None
    for i in range(n, m - n):
        wl = low[i - n: i + n + 1]
        wh = high[i - n: i + n + 1]
        center = n
        confirm = i + n
        # swing low
        if low[i] == wl.min() and (low[i] < np.delete(wl, center)).all():
            if last_lo_price is not None and low[i] < last_lo_price and osc[i] > last_lo_osc:
                bull[confirm] = True
            last_lo_price, last_lo_osc = low[i], osc[i]
        # swing high
        if high[i] == wh.max() and (high[i] > np.delete(wh, center)).all():
            if last_hi_price is not None and high[i] > last_hi_price and osc[i] < last_hi_osc:
                bear[confirm] = True
            last_hi_price, last_hi_osc = high[i], osc[i]
    return bull, bear


# ── Wilson 95% CI ──
def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return 0.0, 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, center - half, center + half


@dataclass
class SkipCounter:
    counts: Counter = field(default_factory=Counter)

    def add(self, reason: str, n: int = 1):
        self.counts[reason] += n

    def report(self) -> str:
        if not self.counts:
            return "  (skip 0 件)"
        return "\n".join(f"  - {r}: {n}" for r, n in self.counts.most_common())


# ── MTF causal align: chart bar 時刻に対し「確定済み」HTF bar の値を引く ──
def _align_htf(chart_idx: pd.DatetimeIndex, htf: pd.DataFrame, col: pd.Series, tf_hours: int) -> np.ndarray:
    """HTF bar i は close 時刻 = open + tf_hours。chart bar の close 時刻 t に対し
    close <= t を満たす最新 HTF bar の値を返す (lookahead 無し)。"""
    htf_close = (htf.index + pd.Timedelta(hours=tf_hours)).values.astype("int64")
    vals = col.to_numpy()
    t = chart_idx.values.astype("int64")
    pos = np.searchsorted(htf_close, t, side="right") - 1
    out = np.full(len(chart_idx), np.nan)
    ok = pos >= 0
    out[ok] = vals[pos[ok]]
    return out


# ── トレードシミュレーション ──
# Regime slot: 0=RANGE BUY, 1=RANGE SELL, 2=TREND BUY, 3=TREND SELL
SLOT_LABEL = {0: "RANGE BUY", 1: "RANGE SELL", 2: "TREND BUY", 3: "TREND SELL"}


@dataclass
class Computed:
    pip: float
    idx: pd.DatetimeIndex
    o: np.ndarray; h: np.ndarray; l: np.ndarray; c: np.ndarray
    atr: np.ndarray; rsi: np.ndarray
    h1_ef: np.ndarray; h4_ef: np.ndarray
    in_range: np.ndarray; aligned_bull: np.ndarray; aligned_bear: np.ndarray
    bull_div: np.ndarray; bear_div: np.ndarray
    mr_buy: np.ndarray; mr_sell: np.ndarray; tr_buy: np.ndarray; tr_sell: np.ndarray
    n: int


def _compute(pair: str, m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame,
             div_mode: str = "proxy") -> Computed:
    """指標 + regime + entry mask を計算 (simulate / diagnose で共有しロジック乖離を防ぐ)。
    div_mode: "proxy" (low<low[8]&hist>hist[8]) | "pivot" (Williams Fractal 本物のダイバ)。"""
    pip = _pip_size(pair)
    m15 = m15.copy()
    close = m15["Close"]
    atr = _atr(m15)
    ema_f = _ema(close, EMA_FAST); ema_m = _ema(close, EMA_MID); ema_s = _ema(close, EMA_SLOW)
    rsi = _rsi(close); hist = _macd_hist(close)

    h1_ef = _align_htf(m15.index, h1, _ema(h1["Close"], HTF_FAST), 1)
    h1_es = _align_htf(m15.index, h1, _ema(h1["Close"], HTF_SLOW), 1)
    h4_ef = _align_htf(m15.index, h4, _ema(h4["Close"], HTF_FAST), 4)
    h4_es = _align_htf(m15.index, h4, _ema(h4["Close"], HTF_SLOW), 4)

    o = m15["Open"].to_numpy(); h = m15["High"].to_numpy()
    l = m15["Low"].to_numpy(); c = close.to_numpy()
    atr = atr.to_numpy(); ema_f = ema_f.to_numpy(); ema_m = ema_m.to_numpy(); ema_s = ema_s.to_numpy()
    rsi = rsi.to_numpy(); hist = hist.to_numpy()

    h1_bull = h1_ef > h1_es; h1_bear = h1_ef < h1_es
    h4_bull = h4_ef > h4_es; h4_bear = h4_ef < h4_es
    bull_po = (ema_f > ema_m) & (ema_m > ema_s) & (c > ema_f)
    bear_po = (ema_f < ema_m) & (ema_m < ema_s) & (c < ema_f)
    aligned_bull = bull_po & h1_bull & h4_bull
    aligned_bear = bear_po & h1_bear & h4_bear
    in_trend = aligned_bull | aligned_bear
    in_range = ~in_trend

    if div_mode == "none":
        bull_div = np.ones(len(l), dtype=bool)
        bear_div = np.ones(len(l), dtype=bool)
    elif div_mode == "pivot":
        bull_div, bear_div = _pivot_divergence(l, h, hist, DIV_FRACTAL_N)
    else:
        lo_prev = np.roll(l, DIV_LB); hi_prev = np.roll(h, DIV_LB); hist_prev = np.roll(hist, DIV_LB)
        bull_div = (l < lo_prev) & (hist > hist_prev)
        bear_div = (h > hi_prev) & (hist < hist_prev)
        bull_div[:DIV_LB] = False; bear_div[:DIV_LB] = False

    rsi_s = pd.Series(rsi)
    recent_dip = (rsi_s.rolling(PULL_LB).min().shift(1) < 50).to_numpy()
    recent_pop = (rsi_s.rolling(PULL_LB).max().shift(1) > 50).to_numpy()
    rsi_prev = np.roll(rsi, 1)

    mr_buy = in_range & (rsi < RSI_OS) & bull_div
    mr_sell = in_range & (rsi > RSI_OB) & bear_div
    tr_buy = aligned_bull & (c > ema_f) & (rsi > rsi_prev) & recent_dip & (rsi < RSI_XHI)
    tr_sell = aligned_bear & (c < ema_f) & (rsi < rsi_prev) & recent_pop & (rsi > RSI_XLO)

    return Computed(pip, m15.index, o, h, l, c, atr, rsi, h1_ef, h4_ef,
                    in_range, aligned_bull, aligned_bear, bull_div, bear_div,
                    mr_buy, mr_sell, tr_buy, tr_sell, len(m15))


def simulate(pair: str, m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame,
             friction_pip: float, skips: SkipCounter,
             sl_mr=SL_MR, tp_mr=TP_MR, sl_tr=SL_TR, tp_tr=TP_TR,
             div_mode: str = "proxy", exit_mode: str = "fixed", trail_mult: float = 2.0,
             max_hold: int = MAX_HOLD) -> pd.DataFrame:
    cp = _compute(pair, m15, h1, h4, div_mode)
    pip = cp.pip; idx = cp.idx; n = cp.n
    o, h, l, c, atr, rsi = cp.o, cp.h, cp.l, cp.c, cp.atr, cp.rsi
    h1_ef, h4_ef = cp.h1_ef, cp.h4_ef
    mr_buy, mr_sell, tr_buy, tr_sell = cp.mr_buy, cp.mr_sell, cp.tr_buy, cp.tr_sell

    trades = []
    i = ATR_LEN + DIV_LB + 1
    pos_until = -1  # pyramiding=0: この index までポジション保有中
    while i < n - 1:
        if i <= pos_until:
            i += 1
            continue
        if not np.isfinite(atr[i]) or atr[i] <= 0 or not np.isfinite(rsi[i]):
            i += 1
            continue
        # HTF 未確定 (align NaN) は skip
        if not (np.isfinite(h1_ef[i]) and np.isfinite(h4_ef[i])):
            skips.add("htf not ready")
            i += 1
            continue

        is_buy = mr_buy[i] or tr_buy[i]
        is_sell = mr_sell[i] or tr_sell[i]
        if not (is_buy or is_sell):
            i += 1
            continue

        is_trend = (tr_buy[i] or tr_sell[i])
        direction = 1 if is_buy else -1
        slot = (2 if is_trend else 0) + (0 if is_buy else 1)
        entry = c[i]  # process_orders_on_close=true: signal bar close で約定
        sl_mult = sl_tr if is_trend else sl_mr
        tp_mult = tp_tr if is_trend else tp_mr
        sl_dist = atr[i] * sl_mult
        tp_dist = atr[i] * tp_mult
        if direction == 1:
            sl_px, tp_px = entry - sl_dist, entry + tp_dist
        else:
            sl_px, tp_px = entry + sl_dist, entry - tp_dist

        # exit 探索 (次 bar 以降の intrabar)。
        exit_px = None
        exit_reason = None
        last = min(i + max_hold, n - 1)
        if exit_mode == "fixed":
            # 固定 SL/TP。同一 bar 両ヒットは保守的に SL 優先。
            for k in range(i + 1, last + 1):
                if direction == 1:
                    if l[k] <= sl_px:
                        exit_px, exit_reason = sl_px, "sl"; break
                    if h[k] >= tp_px:
                        exit_px, exit_reason = tp_px, "tp"; break
                else:
                    if h[k] >= sl_px:
                        exit_px, exit_reason = sl_px, "sl"; break
                    if l[k] <= tp_px:
                        exit_px, exit_reason = tp_px, "tp"; break
        else:
            # trail: 初期 SL は固定。含み益の extreme から trail_dist 離した stop が
            # ratchet (long は上方向のみ更新)。trail_sl は entry〜k-1 の extreme で決め (causal)、
            # bar k の安値/高値で当たり判定 → その後 bar k で extreme 更新。TP は置かず伸びに任せる。
            trail_dist = atr[i] * trail_mult
            extreme = entry  # long:最高値 / short:最安値
            for k in range(i + 1, last + 1):
                if direction == 1:
                    eff_sl = max(sl_px, extreme - trail_dist)
                    if l[k] <= eff_sl:
                        exit_px, exit_reason = eff_sl, ("trail" if eff_sl > sl_px else "sl"); break
                    extreme = max(extreme, h[k])
                else:
                    eff_sl = min(sl_px, extreme + trail_dist)
                    if h[k] >= eff_sl:
                        exit_px, exit_reason = eff_sl, ("trail" if eff_sl < sl_px else "sl"); break
                    extreme = min(extreme, l[k])
        if exit_px is None:
            exit_px, exit_reason, k = c[last], "timestop", last

        gross_pip = (exit_px - entry) / pip * direction
        net_pip = gross_pip - friction_pip
        trades.append({
            "time": idx[i], "slot": slot, "dir": direction,
            "session": _session_label(idx[i].hour),
            "gross_pip": gross_pip, "net_pip": net_pip,
            "win": net_pip > 0, "reason": exit_reason,
        })
        pos_until = k
        i = k + 1  # ポジション解消 bar の次から再開

    return pd.DataFrame(trades)


def _agg(df: pd.DataFrame) -> dict:
    n = len(df)
    if n == 0:
        return {"N": 0, "WR": 0.0, "PF": 0.0, "EV": 0.0, "sum": 0.0, "lo": 0.0, "hi": 0.0}
    wins = int(df["win"].sum())
    gp = df.loc[df["net_pip"] > 0, "net_pip"].sum()
    gl = -df.loc[df["net_pip"] <= 0, "net_pip"].sum()
    pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
    p, lo, hi = wilson(wins, n)
    return {"N": n, "WR": 100 * p, "PF": pf, "EV": df["net_pip"].mean(),
            "sum": df["net_pip"].sum(), "lo": 100 * lo, "hi": 100 * hi}


def _print_block(title: str, df: pd.DataFrame):
    print(f"\n── {title} ──")
    a = _agg(df)
    print(f"  全体: N={a['N']} WR={a['WR']:.1f}% (Wilson {a['lo']:.0f}-{a['hi']:.0f}) "
          f"PF={a['PF']:.2f} EV={a['EV']:+.2f}pip sum={a['sum']:+.0f}pip")
    if a["N"] == 0:
        return
    # Regime×方向
    print(f"  {'Regime':<12}{'N':>5}{'WR%':>7}{'Wilson':>12}{'PF':>7}{'EV':>8}{'sum':>9}")
    for slot in range(4):
        sub = df[df["slot"] == slot]
        s = _agg(sub)
        if s["N"] == 0:
            print(f"  {SLOT_LABEL[slot]:<12}{0:>5}{'—':>7}")
            continue
        flag = " ★" if (s["N"] >= 30 and s["lo"] > 50) else (" ·" if s["WR"] > 50 else "")
        ci = f"{s['lo']:.0f}-{s['hi']:.0f}"
        print(f"  {SLOT_LABEL[slot]:<12}{s['N']:>5}{s['WR']:>7.1f}{ci:>12}"
              f"{s['PF']:>7.2f}{s['EV']:>+8.2f}{s['sum']:>+9.0f}{flag}")
    # 方向対称性
    buy = _agg(df[df["dir"] == 1]); sell = _agg(df[df["dir"] == -1])
    print(f"  方向対称性: BUY  N={buy['N']} PF={buy['PF']:.2f} EV={buy['EV']:+.2f} | "
          f"SELL N={sell['N']} PF={sell['PF']:.2f} EV={sell['EV']:+.2f}")
    # session
    print(f"  {'Session':<10}{'N':>5}{'WR%':>7}{'PF':>7}{'EV':>8}")
    for sess in ["Tokyo", "London", "NY", "Off"]:
        s = _agg(df[df["session"] == sess])
        if s["N"]:
            print(f"  {sess:<10}{s['N']:>5}{s['WR']:>7.1f}{s['PF']:>7.2f}{s['EV']:>+8.2f}")


def _bev_wr(rr: float, friction_pip: float, win_pip: float) -> tuple[float, float]:
    """R:R から break-even WR を返す (friction前, friction後)。
    win_pip = TP距離(pip), loss_pip = SL距離(pip) = win_pip/rr。
    BEV: WR*win - (1-WR)*loss = 0  → WR = loss/(win+loss) = 1/(1+rr)。
    friction後: WR*(win-f) - (1-WR)*(loss+f) = 0 → WR = (loss+f)/(win+loss)。
    """
    loss_pip = win_pip / rr
    bev0 = loss_pip / (win_pip + loss_pip)
    bevf = (loss_pip + friction_pip) / (win_pip + loss_pip)
    return 100 * bev0, 100 * bevf


def diagnose(pair: str, m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame,
             friction_pip: float, div_mode: str = "proxy") -> None:
    """なぜ勝てないかの構造分解。exit機構を外したエントリーの生の予測力 (forward-return) を測る。"""
    cp = _compute(pair, m15, h1, h4, div_mode)
    pip = cp.pip
    c = cp.c; atr = cp.atr; n = cp.n
    horizons = [4, 12, 48]  # 1h, 3h, 12h

    print("\n" + "=" * 78)
    print("# 診断: なぜ勝てないか")
    print("=" * 78)

    # ── (1) エントリーの生の予測力 (exit機構なし、forward-return) ──
    # 各 regime×方向のシグナル bar で、entry=close[i] から hz 本後 close までの
    # 方向調整 forward-return (pip) の平均と勝率 (>0)。ATR正規化平均も。
    print("\n── (1) エントリーの生の予測力 (exit機構を外した forward-return) ──")
    print("   ※ これが ~0 なら「エントリーに予測力なし」= exit/friction 以前の問題")
    masks = {0: cp.mr_buy, 1: cp.mr_sell, 2: cp.tr_buy, 3: cp.tr_sell}
    dirs = {0: 1, 1: -1, 2: 1, 3: -1}
    hdr = f"  {'Regime':<12}{'N':>6}" + "".join(f"{'fwd'+str(hz)+'(pip)':>13}{'hit%':>7}" for hz in horizons)
    print(hdr)
    for slot, mask in masks.items():
        d = dirs[slot]
        sig_idx = np.where(mask)[0]
        sig_idx = sig_idx[(sig_idx >= ATR_LEN + DIV_LB + 1) & (sig_idx < n - max(horizons) - 1)]
        if len(sig_idx) == 0:
            print(f"  {SLOT_LABEL[slot]:<12}{0:>6}")
            continue
        row = f"  {SLOT_LABEL[slot]:<12}{len(sig_idx):>6}"
        for hz in horizons:
            ret = (c[sig_idx + hz] - c[sig_idx]) / pip * d
            hit = 100.0 * np.mean(ret > 0)
            row += f"{np.mean(ret):>13.3f}{hit:>7.1f}"
        print(row)
    # ベースライン: 全 bar のランダム方向 forward-return abs (規模感)
    base = np.abs((c[ATR_LEN+1+horizons[1]:] - c[ATR_LEN+1:-horizons[1]]) / pip)
    print(f"   参考: |fwd12| の全 bar 平均規模 = {np.nanmean(base):.2f} pip "
          f"(シグナルの fwd がこれに対し有意に偏るか)")

    # ── (2) R:R と BEV_WR vs 実 WR ──
    print("\n── (2) R:R 算術: break-even WR に実 WR が届いているか ──")
    skips2 = SkipCounter()
    trades = simulate(pair, m15, h1, h4, friction_pip, skips2, div_mode=div_mode)
    # ATR中央値から TP/SL の pip 規模を出す
    atr_med_pip = np.nanmedian(atr) / pip
    for label, slot, rr, win_mult in [
        ("RANGE (R:R=1.25)", [0, 1], TP_MR / SL_MR, TP_MR),
        ("TREND (R:R=1.67)", [2, 3], TP_TR / SL_TR, TP_TR),
    ]:
        win_pip = win_mult * atr_med_pip
        bev0, bevf = _bev_wr(rr, friction_pip, win_pip)
        sub = trades[trades["slot"].isin(slot)]
        actual = 100 * sub["win"].mean() if len(sub) else 0.0
        gap = actual - bevf
        print(f"  {label}: TP≈{win_pip:.1f}pip SL≈{win_pip/rr:.1f}pip | "
              f"BEV_WR(friction0)={bev0:.1f}% BEV_WR(f={friction_pip})={bevf:.1f}% | "
              f"実WR={actual:.1f}% → gap={gap:+.1f}pp {'❌届かず' if gap < 0 else '✓超え'}")

    # ── (3) MACD divergence ablation (MR系) ──
    print("\n── (3) MACD divergence は MR にエッジを足しているか (forward-return) ──")
    for slot, base_mask, div_mask, d in [
        (0, cp.in_range & (cp.rsi < RSI_OS), cp.bull_div, 1),
        (1, cp.in_range & (cp.rsi > RSI_OB), cp.bear_div, -1),
    ]:
        for tag, mask in [("div有", base_mask & div_mask), ("div無", base_mask & ~div_mask)]:
            si = np.where(mask)[0]
            si = si[(si >= ATR_LEN + DIV_LB + 1) & (si < n - 13)]
            if len(si) < 10:
                print(f"  {SLOT_LABEL[slot]} {tag}: N={len(si)} (不足)")
                continue
            ret = (c[si + 12] - c[si]) / pip * d
            print(f"  {SLOT_LABEL[slot]} {tag}: N={len(si):>4} fwd12={np.mean(ret):+.3f}pip hit={100*np.mean(ret>0):.1f}%")

    # ── (4) SL/TP 感度 (friction0, 全体EV) — SLが近すぎ仮説の検証 ──
    print("\n── (4) SL/TP 感度 (friction0 全体EV) — SLを広げると改善するか ──")
    grid = [(1.2, 1.5, 1.5, 2.5), (2.0, 2.0, 2.0, 3.0), (2.5, 2.5, 3.0, 4.0), (3.0, 1.5, 3.0, 2.0)]
    print(f"  {'SL_mr/TP_mr/SL_tr/TP_tr':<26}{'N':>6}{'WR%':>7}{'PF':>7}{'EV(pip)':>10}")
    sk = SkipCounter()
    for smr, tmr, str_, ttr in grid:
        t = simulate(pair, m15, h1, h4, 0.0, sk, sl_mr=smr, tp_mr=tmr, sl_tr=str_, tp_tr=ttr, div_mode=div_mode)
        a = _agg(t)
        print(f"  {f'{smr}/{tmr}/{str_}/{ttr}':<26}{a['N']:>6}{a['WR']:>7.1f}{a['PF']:>7.2f}{a['EV']:>+10.3f}")


def run_pair(pair: str, friction_pip: float, do_diagnose: bool = False, div_mode: str = "proxy",
             exit_mode: str = "fixed", trail_mult: float = 2.0, max_hold: int = MAX_HOLD) -> int:
    skips = SkipCounter()
    f15 = DATA_DIR / f"{pair}_15m.parquet"
    f1h = DATA_DIR / f"{pair}_1h.parquet"
    f4h = DATA_DIR / f"{pair}_4h.parquet"
    for f in (f15, f1h, f4h):
        if not f.exists():
            print(f"[{pair}] データ欠損: {f.name} 不在 — 中断", file=sys.stderr)
            return 1

    m15 = pd.read_parquet(f15); h1 = pd.read_parquet(f1h); h4 = pd.read_parquet(f4h)
    for d in (m15, h1, h4):
        if d.index.tz is None:
            d.index = d.index.tz_localize("UTC")
    m15 = m15[(m15.index >= WINDOW_START) & (m15.index <= WINDOW_END)]
    h1 = h1[(h1.index >= WINDOW_START) & (h1.index <= WINDOW_END)]
    h4 = h4[(h4.index >= WINDOW_START) & (h4.index <= WINDOW_END)]
    if len(m15) < 2000:
        print(f"[{pair}] 共通窓 N 不足 (15m={len(m15)}) — 中断", file=sys.stderr)
        return 1

    print("=" * 78)
    print(f"# mtf_regime_switch Python BT — {pair}")
    print("=" * 78)
    print(f"共通窓 {m15.index.min().date()}〜{m15.index.max().date()}  "
          f"15m={len(m15)} 1h={len(h1)} 4h={len(h4)}")
    print(f"friction = {friction_pip:.1f} pip/trade  "
          f"({'TV 再現 (friction0)' if friction_pip == 0 else 'EV 判定モード'})")
    print(f"div_mode={div_mode}  exit_mode={exit_mode}"
          f"{f' (trail_mult={trail_mult})' if exit_mode == 'trail' else ''}  max_hold={max_hold}")

    trades = simulate(pair, m15, h1, h4, friction_pip, skips, div_mode=div_mode,
                      exit_mode=exit_mode, trail_mult=trail_mult, max_hold=max_hold)
    if trades.empty:
        print("トレード 0 件。skip:")
        print(skips.report())
        return 0

    # train/holdout split (chronological, 60/40)
    split_t = m15.index[int(len(m15) * TRAIN_FRAC)]
    tr = trades[trades["time"] < split_t]
    ho = trades[trades["time"] >= split_t]
    print(f"\nsplit: train < {split_t.date()} (N={len(tr)}) | holdout >= {split_t.date()} (N={len(ho)})")

    _print_block("全期間 (4.4年)", trades)
    _print_block(f"TRAIN 前半60% ({trades['time'].min().date()}〜{split_t.date()})", tr)
    _print_block(f"HOLDOUT 後半40% ({split_t.date()}〜{trades['time'].max().date()})", ho)

    print(f"\n── exit 内訳 ──")
    print("  " + " / ".join(f"{r}:{cnt}" for r, cnt in trades["reason"].value_counts().items()))
    print(f"\n── skip ──")
    print(skips.report())

    if do_diagnose:
        diagnose(pair, m15, h1, h4, friction_pip, div_mode)
    return 0


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="mtf_regime_switch Python multi-year cross-check")
    ap.add_argument("--pair", default="EUR_USD")
    ap.add_argument("--friction", type=float, default=0.0, help="pip/trade を引く (EUR_USD RT≈2.0)")
    ap.add_argument("--diagnose", action="store_true", help="なぜ勝てないかの構造分解を追加")
    ap.add_argument("--div", choices=["proxy", "pivot", "none"], default="proxy", help="ダイバージェンス実装 (none=フィルタ無効)")
    ap.add_argument("--exit", dest="exit_mode", choices=["fixed", "trail"], default="fixed", help="exit 機構")
    ap.add_argument("--trail-mult", type=float, default=2.0, help="トレール幅 (ATR倍, exit=trail時)")
    ap.add_argument("--max-hold", type=int, default=MAX_HOLD, help="最大保有バー数 (timestop)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    return run_pair(args.pair, args.friction, args.diagnose, args.div,
                    args.exit_mode, args.trail_mult, args.max_hold)


if __name__ == "__main__":
    raise SystemExit(main())
