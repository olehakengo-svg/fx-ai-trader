#!/usr/bin/env python3
"""kalman_d7_po_dn_flip — live exit スタック (C0〜C6) 付き制約 BT (診断専用、rule:R3).

Codex queue `20260925-0300-kalman-d7-live-constrained-bt` の Python port 実装。
registry `kalman-d7-live-exit-spec-mismatch-disposition` (2026-10-08) の user 決裁 packet に
「どの overlay が BT edge をどれだけ削るか / winner・loser 別 hold・exit 分布 / 8h 内完結 winner 比率」
を供給する。**本ツールの数字から keep / demote を決めない** (task 文書「判定の扱い」)。

設計上の注意 (task 文書の凍結ラベル):
- 走 0  = 宣言 BT 再現 (harness 検証)。exit は 2 変種で走らせる —
    `flip` : PO-DN flip (EMA200 > EMA75 > EMA25 で成行) + SL 1.5×ATR + 480 bars cap  (TV v17 canon の推定)
    `tp5`  : TP 5×ATR + SL 1.5×ATR + 480 bars cap                                    (Python live 宣言 = 近似)
  カード BT (WR 23.91% / PF 3.866) は payoff 12.3× を要求し、固定 TP/SL (上限 3.33×) では算術的に
  出ないので、canon は `flip` 側でしか再現できない (本ツールで実測)。
- 走 0′〜4 = 「C0 近似 + intrabar 順序近似」。順序仮定は adverse_first (既定・保守側) と favorable_first の 2 方向。
- 走 5 = C6 近似 (PO 崩れサロゲート)。参考値のみ、「full live stack」とは呼ばない。
- 摩擦 = USD_JPY RT 2.14 pip / trade (wiki/analyses/friction-analysis.md)。

standalone: live 戦略モジュールを import しない (indicator は tools/kalman_d7_v18e_python_port を再利用、
SR は modules/indicators.find_sr_levels_weighted を live と同じ引数で呼ぶ)。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.kalman_d7_v18e_python_port import add_v18e_indicators  # noqa: E402
from modules.indicators import find_sr_levels_weighted  # noqa: E402

# ── 凍結定数 (live 実装の写し。出典 = modules/demo_trader.py 2026-09-27 origin/main) ──
MINTICK = 0.001
PIP = 0.01
FRICTION_PIPS = 2.14          # USD_JPY RT friction (friction-analysis.md)
DECL_SL_ATR = 1.5             # 宣言 SL
DECL_TP_ATR = 5.0             # 宣言 TP (Python live 近似)
CANON_MAX_BARS = 480          # 宣言 max hold (bars)
C0_ATR_SL_MULT = 1.0          # daytrade fallback (`_atr_mult` daytrade=1.0)
C0_SR_MARGIN_ATR = 0.3        # `_sl_margin = _atr * 0.3`
C0_SR_RR_FLOOR = 1.0
C0_SR_EXCLUDE_ATR = 0.05      # sr_entry_map: price < entry - atr*0.05
C0_MIN_SL = 0.050             # MIN_SL_DIST daytrade JPY (5 pip)
C0_MAX_SL = 0.200             # MAX_SL_DIST daytrade JPY (20 pip)
C0_LOWLIQ_HOURS = frozenset({0, 1, 18, 19, 20, 21})
C0_LOWLIQ_ATR = 0.2
C0_RN_STEP = 0.500
C0_RN_BAND = 0.020
C0_RN_NUDGE = 0.025
C0_BROKER_TP_MULT = 0.85      # _QUICK_HARVEST_MULT
C0_MTF_TP_BONUS = 1.3
C0_SR_LOOKBACK_BARS = 500     # ⚠️ 仮定: live の 15m fetch 本数は fill 行に無いので 500 本で近似
C1_MAX_HOLD_SEC = 28800       # MAX_HOLD_SEC["daytrade"]
C5_HALF_HOLD_SEC = 14400      # C1 半分時点
C3_BE_ATR = 0.8
C3_BE_SPREAD = 0.008          # fallback spread (bid/ask 無し時の live 既定)
C4_TRAIL_TRIGGER_ATR = 1.5
C4_TRAIL_OFFSET_ATR = 0.5
C6_MIN_HOLD_SEC = 600
C6_PROFIT_GUARD_ATR = 0.3

CANON = {"n": 46, "wr": 0.2391, "pf": 3.866, "avg_win_bars": 458}
HARNESS_TOL = 0.10

WINDOW_START = "2025-07-01"
WINDOW_END = "2026-05-19 23:59:59"
WARMUP_START = "2025-04-01"


@dataclass(frozen=True)
class StackConfig:
    label: str = "walk0_flip"
    exit_mode: str = "flip"          # flip | tp5
    canon_cap: bool = True           # 480 bars cap (宣言)
    c0: bool = False
    c0_sl_mode: str = "atr"          # atr | sr
    c0_clamp: bool = True
    c0_lowliq: bool = True
    c0_rn: bool = True
    c0_mtf: float = 1.0              # 1.0 | 1.3 (一致判定は再現不能 → 2 値併記)
    c0_broker_tp: bool = True
    c1: bool = False
    c2: bool = False
    c3c4: bool = False
    c5: bool = False
    c6: bool = False
    order: str = "adverse_first"     # adverse_first | favorable_first
    friction_pips: float = FRICTION_PIPS


@dataclass
class SimTrade:
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    atr: float
    decl_sl: float
    decl_tp: float
    sl0: float
    tp0: float
    sl_branch: str
    c0_flags: dict
    bars_held: int
    hold_sec: float
    exit_reason: str
    gross_pips: float
    net_pips: float
    mfe_pips: float
    mae_pips: float


# ─────────────────────────────────────────────────────────────────────────────
# indicators / data
# ─────────────────────────────────────────────────────────────────────────────
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    data = add_v18e_indicators(df)
    data["perfect_dn"] = (data["ema200"] > data["ema75"]) & (data["ema75"] > data["ema25"])
    return data


def slice_window(data: pd.DataFrame, start: str, end: str, warmup: str) -> pd.DataFrame:
    d = data.loc[pd.Timestamp(warmup, tz="UTC"):pd.Timestamp(end, tz="UTC")].copy()
    d["in_window"] = d.index >= pd.Timestamp(start, tz="UTC")
    return d


# ─────────────────────────────────────────────────────────────────────────────
# C0: entry 時 SL/TP 変換 (live `_tick_entry` の写し、近似ラベル)
# ─────────────────────────────────────────────────────────────────────────────
def nearest_support_sr(hist: pd.DataFrame, entry: float, atr: float) -> float | None:
    """live `sr_entry_map["nearest_support"]` の近似 (app.py compute_daytrade_signal)。"""
    if len(hist) < 50:
        return None
    levels = find_sr_levels_weighted(
        hist[["High", "Low"]], window=5, tolerance_pct=0.003, min_touches=2,
        max_levels=10, bars_per_day=96,
    )
    sup = [s for s in levels if s["price"] < entry - atr * C0_SR_EXCLUDE_ATR]
    if not sup:
        return None
    return max(s["price"] for s in sup)


def apply_c0(entry: float, atr: float, entry_ts: pd.Timestamp, hist: pd.DataFrame,
             cfg: StackConfig) -> tuple[float, float, str, dict]:
    """Return (sl, tp, sl_branch, flags). cfg.c0=False なら宣言値そのまま。"""
    decl_sl = entry - DECL_SL_ATR * atr
    decl_tp = entry + DECL_TP_ATR * atr
    flags: dict[str, Any] = {"clamp": "none", "lowliq": 0, "rn": 0, "mtf": 1.0, "broker": 0}
    if not cfg.c0:
        return round(decl_sl, 3), round(decl_tp, 3), "preserve", flags

    tp_dist = DECL_TP_ATR * atr * cfg.c0_mtf
    flags["mtf"] = cfg.c0_mtf

    atr_sl = entry - atr * C0_ATR_SL_MULT
    branch = "atr_nosr"
    sl = atr_sl
    if cfg.c0_sl_mode == "sr":
        ns = nearest_support_sr(hist, entry, atr)
        if ns is not None:
            sr_sl = ns - atr * C0_SR_MARGIN_ATR
            sr_dist = entry - sr_sl
            if sr_dist > 0 and tp_dist / sr_dist >= C0_SR_RR_FLOOR:
                sl = sr_sl
                branch = "sr"
            else:
                branch = "atr_rrlow"
    else:
        branch = "atr"
    sl = round(sl, 3)
    sl_dist = entry - sl

    if cfg.c0_clamp:
        if sl_dist < C0_MIN_SL:
            sl_dist = C0_MIN_SL
            flags["clamp"] = "min"
            sl = round(entry - sl_dist, 3)
        elif sl_dist > C0_MAX_SL:
            sl_dist = C0_MAX_SL
            flags["clamp"] = "max"
            sl = round(entry - sl_dist, 3)

    if cfg.c0_lowliq and entry_ts.hour in C0_LOWLIQ_HOURS:
        flags["lowliq"] = 1
        sl_dist += atr * C0_LOWLIQ_ATR
        sl = round(entry - sl_dist, 3)

    if cfg.c0_rn:
        frac = sl % C0_RN_STEP
        if frac < C0_RN_BAND or frac > C0_RN_STEP - C0_RN_BAND:
            flags["rn"] = 1
            sl = round(sl - C0_RN_NUDGE, 3)

    if cfg.c0_broker_tp:
        flags["broker"] = 1
        tp = entry + tp_dist * C0_BROKER_TP_MULT
    else:
        tp = entry + tp_dist
    return sl, round(tp, 3), branch, flags


# ─────────────────────────────────────────────────────────────────────────────
# simulation
# ─────────────────────────────────────────────────────────────────────────────
def _is_last_bar_before_weekend(idx: pd.DatetimeIndex, j: int) -> bool:
    """bar j が金曜最終 bar (次 bar まで 6h 超のギャップ ∧ 金曜) なら True。
    live は金曜 21:45Z 以降の最初の tick で全クローズ。Massive M15 の金曜最終 bar は 20:45 (close 21:00)
    なので、その bar close で決済したと近似する (⚠️ 21:00→21:45 の値動きは未再現)。"""
    ts = idx[j]
    if ts.weekday() != 4:
        return False
    if j + 1 >= len(idx):
        return True
    return (idx[j + 1] - ts).total_seconds() > 6 * 3600


def simulate(data: pd.DataFrame, cfg: StackConfig) -> list[SimTrade]:
    idx = data.index
    n = len(data)
    o = data["Open"].to_numpy(float)
    h = data["High"].to_numpy(float)
    lo = data["Low"].to_numpy(float)
    c = data["Close"].to_numpy(float)
    atr_a = data["atr"].to_numpy(float)
    sig_a = data["entry_signal"].to_numpy(bool)
    pup = data["perfect_up"].to_numpy(bool)
    pdn = data["perfect_dn"].to_numpy(bool)
    in_w = data["in_window"].to_numpy(bool)
    hours = idx.hour.to_numpy()

    trades: list[SimTrade] = []
    i = 0
    while i < n - 1:
        if not (sig_a[i] and in_w[i]):
            i += 1
            continue
        atr = atr_a[i]
        if not math.isfinite(atr) or atr <= 0:
            i += 1
            continue
        # TV process_orders_on_close=true → signal bar close で約定 (+1 tick slippage)
        entry = c[i] + MINTICK
        entry_ts = idx[i] + pd.Timedelta(minutes=15)
        hist = data.iloc[max(0, i - C0_SR_LOOKBACK_BARS + 1): i + 1]
        sl, tp, branch, flags = apply_c0(entry, atr, entry_ts, hist, cfg)
        decl_sl = round(entry - DECL_SL_ATR * atr, 3)
        decl_tp = round(entry + DECL_TP_ATR * atr, 3)
        sl0, tp0 = sl, tp
        sl_moved = None  # "BE" | "TRAIL"
        highest = entry
        lowest = entry
        exit_px: float | None = None
        reason = ""
        exit_j = i + 1
        exit_ts = None

        for j in range(i + 1, n):
            ts = idx[j]
            hold_open = (ts - entry_ts).total_seconds()
            bars = j - i  # bars since signal bar (bar j is the bars-th bar held)

            # ── tick-based checks at bar open (live は毎 tick、ここでは open で近似) ──
            if cfg.c1 and hold_open >= C1_MAX_HOLD_SEC:
                exit_px, reason = o[j] - MINTICK, "MAX_HOLD_TIME"
                exit_j, exit_ts = j, ts
                break
            if cfg.c5 and hold_open > C5_HALF_HOLD_SEC and o[j] < entry:
                exit_px, reason = o[j] - MINTICK, "TIME_DECAY_EXIT"
                exit_j, exit_ts = j, ts
                break

            bar_hi, bar_lo = h[j], lo[j]
            hit_sl = hit_tp = False

            def _update_be_trail(mfe_px: float) -> None:
                nonlocal sl, sl_moved
                fav = mfe_px - entry
                if fav >= C4_TRAIL_TRIGGER_ATR * atr:
                    new_sl = round(mfe_px - C4_TRAIL_OFFSET_ATR * atr, 3)
                    if new_sl > sl:
                        sl, sl_moved = new_sl, "TRAIL"
                elif fav >= C3_BE_ATR * atr:
                    new_sl = round(entry + C3_BE_SPREAD, 3)
                    if new_sl > sl:
                        sl, sl_moved = new_sl, "BE"

            if cfg.order == "adverse_first":
                if bar_lo <= sl:
                    hit_sl = True
                elif cfg.exit_mode == "tp5" and bar_hi >= tp:
                    hit_tp = True
                if not hit_sl and not hit_tp and cfg.c3c4:
                    _update_be_trail(max(highest, bar_hi))
            else:  # favorable_first
                if cfg.c3c4:
                    _update_be_trail(max(highest, bar_hi))
                if cfg.exit_mode == "tp5" and bar_hi >= tp:
                    hit_tp = True
                elif bar_lo <= sl:
                    hit_sl = True

            highest = max(highest, bar_hi)
            lowest = min(lowest, bar_lo)

            if hit_sl:
                exit_px = sl - MINTICK
                reason = sl_moved or "SL_HIT"
                exit_j, exit_ts = j, ts + pd.Timedelta(minutes=15)
                break
            if hit_tp:
                exit_px, reason = tp, "TP_HIT"
                exit_j, exit_ts = j, ts + pd.Timedelta(minutes=15)
                break

            # ── C5 intrabar (open ≥ entry だが bar 内で entry を割った): 最初の tick で決済 ≈ entry ──
            if cfg.c5 and hold_open > C5_HALF_HOLD_SEC and bar_lo < entry <= o[j]:
                exit_px, reason = entry - MINTICK, "TIME_DECAY_EXIT"
                exit_j, exit_ts = j, ts + pd.Timedelta(minutes=15)
                break

            # ── bar close checks ──
            if cfg.exit_mode == "flip" and pdn[j]:
                exit_px, reason = c[j] - MINTICK, "PO_DN_FLIP"
                exit_j, exit_ts = j, ts + pd.Timedelta(minutes=15)
                break
            if cfg.c6 and hold_open + 900 >= C6_MIN_HOLD_SEC and not pup[j] \
                    and (c[j] - entry) <= C6_PROFIT_GUARD_ATR * atr:
                exit_px, reason = c[j] - MINTICK, "SIGNAL_REVERSE_APPROX"
                exit_j, exit_ts = j, ts + pd.Timedelta(minutes=15)
                break
            if cfg.c2 and _is_last_bar_before_weekend(idx, j):
                exit_px, reason = c[j] - MINTICK, "WEEKEND_CLOSE"
                exit_j, exit_ts = j, ts + pd.Timedelta(minutes=15)
                break
            if cfg.canon_cap and bars >= CANON_MAX_BARS:
                exit_px, reason = c[j] - MINTICK, "CANON_CAP_480"
                exit_j, exit_ts = j, ts + pd.Timedelta(minutes=15)
                break

        if exit_px is None:
            exit_j = n - 1
            exit_ts = idx[exit_j] + pd.Timedelta(minutes=15)
            exit_px, reason = c[exit_j] - MINTICK, "EOD"

        gross = (exit_px - entry) / PIP
        net = gross - cfg.friction_pips
        trades.append(SimTrade(
            signal_time=idx[i].isoformat(), entry_time=entry_ts.isoformat(),
            exit_time=exit_ts.isoformat(), entry=round(entry, 3), exit=round(exit_px, 3),
            atr=round(atr, 4), decl_sl=decl_sl, decl_tp=decl_tp, sl0=sl0, tp0=tp0,
            sl_branch=branch, c0_flags=flags, bars_held=int(exit_j - i),
            hold_sec=float((exit_ts - entry_ts).total_seconds()), exit_reason=reason,
            gross_pips=round(gross, 2), net_pips=round(net, 2),
            mfe_pips=round((highest - entry) / PIP, 2), mae_pips=round((entry - lowest) / PIP, 2),
        ))
        i = exit_j + 1
    return trades


# ─────────────────────────────────────────────────────────────────────────────
# stats
# ─────────────────────────────────────────────────────────────────────────────
def wilson_lower(wins: int, n: int, z: float = 1.959964) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom


def _dist(vals: list[float]) -> dict[str, float | None]:
    if not vals:
        return {"n": 0, "p25": None, "median": None, "p75": None, "mean": None}
    a = np.array(vals, float)
    return {"n": int(len(a)), "p25": float(np.percentile(a, 25)), "median": float(np.median(a)),
            "p75": float(np.percentile(a, 75)), "mean": float(a.mean())}


def summarize(trades: list[SimTrade], cfg: StackConfig) -> dict[str, Any]:
    n = len(trades)
    net = [t.net_pips for t in trades]
    gross = [t.gross_pips for t in trades]
    wins = [t for t in trades if t.net_pips > 0]
    losses = [t for t in trades if t.net_pips <= 0]
    gw = sum(t.net_pips for t in wins)
    gl = -sum(t.net_pips for t in losses)
    pf = (gw / gl) if gl > 0 else (math.inf if gw > 0 else 0.0)
    reasons: dict[str, int] = {}
    for t in trades:
        reasons[t.exit_reason] = reasons.get(t.exit_reason, 0) + 1
    branches: dict[str, int] = {}
    flags_ct = {"clamp_min": 0, "clamp_max": 0, "lowliq": 0, "rn": 0}
    for t in trades:
        branches[t.sl_branch] = branches.get(t.sl_branch, 0) + 1
        if t.c0_flags.get("clamp") == "min":
            flags_ct["clamp_min"] += 1
        if t.c0_flags.get("clamp") == "max":
            flags_ct["clamp_max"] += 1
        flags_ct["lowliq"] += int(t.c0_flags.get("lowliq", 0))
        flags_ct["rn"] += int(t.c0_flags.get("rn", 0))
    win_bars = [t.bars_held for t in wins]
    return {
        "label": cfg.label,
        "order": cfg.order,
        "config": asdict(cfg),
        "n": n,
        "wins": len(wins),
        "wr": (len(wins) / n) if n else 0.0,
        "wilson95_lower": wilson_lower(len(wins), n),
        "pf_net": pf if math.isfinite(pf) else None,
        "ev_net_pips": (sum(net) / n) if n else 0.0,
        "ev_gross_pips": (sum(gross) / n) if n else 0.0,
        "total_net_pips": sum(net),
        "avg_win_pips": (gw / len(wins)) if wins else 0.0,
        "avg_loss_pips": (-gl / len(losses)) if losses else 0.0,
        "payoff": (gw / len(wins)) / (gl / len(losses)) if wins and losses else None,
        "exit_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
        "sl_branches": branches,
        "c0_flags": flags_ct,
        "hold_bars_winners": _dist(win_bars),
        "hold_bars_losers": _dist([t.bars_held for t in losses]),
        "winners_within_8h_share": (sum(1 for b in win_bars if b <= 32) / len(win_bars)) if win_bars else None,
        "winners_within_480_share": (sum(1 for b in win_bars if b <= 480) / len(win_bars)) if win_bars else None,
        "mfe_pips_winners": _dist([t.mfe_pips for t in wins]),
        "mfe_pips_losers": _dist([t.mfe_pips for t in losses]),
        "exit_reason_by_outcome": {
            "winners": _count([t.exit_reason for t in wins]),
            "losers": _count([t.exit_reason for t in losses]),
        },
    }


def _count(items: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def harness_check(s: dict[str, Any]) -> dict[str, Any]:
    """走 0 が canon (N=46 / WR 23.91% / PF 3.866 / avg winner bars 458) を ±10% で再現するか。
    WR/PF は gross (摩擦前) で比較する — TV 側は commission 0.002% + slippage 1 tick なので gross 相当。"""
    checks = {}
    checks["n"] = {"canon": CANON["n"], "port": s["n"],
                   "ok": abs(s["n"] - CANON["n"]) / CANON["n"] <= HARNESS_TOL}
    checks["wr"] = {"canon": CANON["wr"], "port": s["wr_gross"],
                    "ok": abs(s["wr_gross"] - CANON["wr"]) / CANON["wr"] <= HARNESS_TOL}
    pf = s["pf_gross"] if s["pf_gross"] is not None else float("inf")
    checks["pf"] = {"canon": CANON["pf"], "port": pf,
                    "ok": math.isfinite(pf) and abs(pf - CANON["pf"]) / CANON["pf"] <= HARNESS_TOL}
    awb = s["hold_bars_winners_gross"]["mean"] or 0.0
    checks["avg_win_bars"] = {"canon": CANON["avg_win_bars"], "port": awb,
                              "ok": abs(awb - CANON["avg_win_bars"]) / CANON["avg_win_bars"] <= HARNESS_TOL}
    checks["all_ok"] = all(v["ok"] for k, v in checks.items() if k != "all_ok")
    return checks


def gross_stats(trades: list[SimTrade]) -> dict[str, Any]:
    wins = [t for t in trades if t.gross_pips > 0]
    losses = [t for t in trades if t.gross_pips <= 0]
    gw = sum(t.gross_pips for t in wins)
    gl = -sum(t.gross_pips for t in losses)
    pf = (gw / gl) if gl > 0 else None
    return {"wr_gross": (len(wins) / len(trades)) if trades else 0.0,
            "pf_gross": pf,
            "hold_bars_winners_gross": _dist([t.bars_held for t in wins])}


# ─────────────────────────────────────────────────────────────────────────────
# walk plan
# ─────────────────────────────────────────────────────────────────────────────
def build_walks(base_c0: StackConfig) -> list[StackConfig]:
    """走 0 (flip / tp5) → 走 0′ (+C0) → 走 1 (+C1) → 走 2 (+C2) → 走 3 (+C3C4) → 走 4 (+C5) → 走 5 (+C6 近似)。
    走 0′〜5 は base_c0 (C0 の what-if 設定) を土台にし、tp5 exit (live 宣言) で走る。"""
    w0f = StackConfig(label="walk0_flip_canon", exit_mode="flip")
    w0t = StackConfig(label="walk0_tp5_decl", exit_mode="tp5")
    w0p = replace(base_c0, label="walk0p_C0", exit_mode="tp5", c0=True)
    w1 = replace(w0p, label="walk1_C0+C1", c1=True)
    w2 = replace(w1, label="walk2_+C2", c2=True)
    w3 = replace(w2, label="walk3_+C3C4", c3c4=True)
    w4 = replace(w3, label="walk4_+C5", c5=True)
    w5 = replace(w4, label="walk5_+C6approx", c6=True)
    return [w0f, w0t, w0p, w1, w2, w3, w4, w5]


def build_marginals(base_c0: StackConfig) -> list[StackConfig]:
    """限界分解: 走 0′ (C0) を土台に overlay を 1 つずつ単独で載せる + C3C4 抜きの累積 (C5 の単独効果の可視化)。"""
    w0p = replace(base_c0, label="walk0p_C0", exit_mode="tp5", c0=True)
    return [
        replace(w0p, label="marg_C1_only", c1=True),
        replace(w0p, label="marg_C2_only", c2=True),
        replace(w0p, label="marg_C3C4_only", c3c4=True),
        replace(w0p, label="marg_C5_only", c5=True),
        replace(w0p, label="marg_C6approx_only", c6=True),
        replace(w0p, label="walk4b_C0+C1+C2+C5_noC3C4", c1=True, c2=True, c5=True),
    ]


FLIP_DEFS = {
    "perfect_dn": "EMA200 > EMA75 > EMA25 (完全下順) — 既定",
    "not_perfect_up": "perfect_up が偽になる (close < EMA25 含む)",
    "close_lt_ema75": "close < EMA75",
    "close_lt_ema200": "close < EMA200",
    "ema25_lt_ema75": "EMA25 < EMA75",
}


def add_flip_columns(data: pd.DataFrame) -> pd.DataFrame:
    d = data
    d["flip_perfect_dn"] = (d["ema200"] > d["ema75"]) & (d["ema75"] > d["ema25"])
    d["flip_not_perfect_up"] = ~d["perfect_up"].astype(bool)
    d["flip_close_lt_ema75"] = d["Close"] < d["ema75"]
    d["flip_close_lt_ema200"] = d["Close"] < d["ema200"]
    d["flip_ema25_lt_ema75"] = d["ema25"] < d["ema75"]
    return d


def harness_identification(data: pd.DataFrame) -> list[dict[str, Any]]:
    """v17 canon Pine はリポジトリに無い (TV slot は 2026-05-21 に上書き) ので、flip exit の定義候補を
    走らせて canon にどれが最も近いかを記録する。**識別のみ** — パラメータ最適化ではない (entry / SL / cap は不変)。"""
    rows = []
    for name, desc in FLIP_DEFS.items():
        d = data.copy()
        d["perfect_dn"] = d[f"flip_{name}"]
        cfg = StackConfig(label=f"walk0_flip[{name}]", exit_mode="flip")
        tr = simulate(d, cfg)
        s = summarize(tr, cfg)
        s.update(gross_stats(tr))
        chk = harness_check(s)
        rows.append({"flip_def": name, "desc": desc, "n": s["n"], "wr_gross": s["wr_gross"],
                     "pf_gross": s["pf_gross"], "avg_win_bars": s["hold_bars_winners_gross"]["mean"],
                     "ev_gross_pips": s["ev_gross_pips"], "payoff": s["payoff"],
                     "exit_reasons": s["exit_reasons"], "harness_ok": chk["all_ok"],
                     "harness": chk})
    return rows


def c0_whatifs(base: StackConfig) -> dict[str, StackConfig]:
    """C0 感度 (BT 側 what-if)。それぞれ base から 1 要素だけ変える。"""
    return {
        "base": base,
        "i_atr_only": replace(base, c0_sl_mode="atr"),
        "ii_sr_priority": replace(base, c0_sl_mode="sr"),
        "iii_no_clamp": replace(base, c0_clamp=False),
        "iv_no_lowliq": replace(base, c0_lowliq=False),
        "v_mtf_1p3": replace(base, c0_mtf=1.3),
        "vi_no_rn": replace(base, c0_rn=False),
        "vii_no_broker_tp": replace(base, c0_broker_tp=False),
    }


def run_all(data: pd.DataFrame, orders: tuple[str, ...] = ("adverse_first", "favorable_first"),
            keep_trades: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"walks": {}, "marginals": {}, "harness": {}, "harness_identification": [],
                           "c0_whatifs": {}, "trades": {}}
    data = add_flip_columns(data)
    w = data[data["in_window"]]
    out["signals"] = {"entry_signal_in_window": int(w["entry_signal"].sum()),
                      "po_up_start_in_window": int(w["po_up_start"].sum())}
    out["harness_identification"] = harness_identification(data)
    base_c0 = StackConfig(c0=True, c0_sl_mode="atr")
    for order in orders:
        out["walks"][order] = []
        for cfg in build_walks(base_c0):
            cfg = replace(cfg, order=order)
            trades = simulate(data, cfg)
            s = summarize(trades, cfg)
            s.update(gross_stats(trades))
            out["walks"][order].append(s)
            if keep_trades:
                out["trades"][f"{order}/{cfg.label}"] = [asdict(t) for t in trades]
            if cfg.label.startswith("walk0_") and order == orders[0]:
                out["harness"][cfg.label] = harness_check(s)
        out["marginals"][order] = []
        for cfg in build_marginals(base_c0):
            cfg = replace(cfg, order=order)
            trades = simulate(data, cfg)
            s = summarize(trades, cfg)
            out["marginals"][order].append(s)
        # C0 what-if: 走 0′〜4 を各 what-if で再集計 (走 5 は参考値なので省く)
        out["c0_whatifs"][order] = {}
        for name, wcfg in c0_whatifs(replace(base_c0, order=order)).items():
            rows = []
            for cfg in build_walks(wcfg)[2:7]:
                cfg = replace(cfg, order=order)
                trades = simulate(data, cfg)
                s = summarize(trades, cfg)
                rows.append({k: s[k] for k in ("label", "n", "wr", "pf_net", "ev_net_pips", "total_net_pips",
                                                 "winners_within_8h_share", "exit_reasons", "sl_branches",
                                                 "c0_flags")})
            out["c0_whatifs"][order][name] = rows
    out["harness_unverified"] = not any(h["all_ok"] for h in out["harness"].values())
    return out


# ─────────────────────────────────────────────────────────────────────────────
# report
# ─────────────────────────────────────────────────────────────────────────────
def _f(x: Any, nd: int = 2) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        if math.isinf(x):
            return "∞"
        return f"{x:.{nd}f}"
    return str(x)


def render_md(res: dict[str, Any], meta: dict[str, Any]) -> str:
    L: list[str] = []
    L.append(f"# kalman_d7_po_dn_flip — live 制約付き BT (Python port、診断専用) {meta['run_date']}")
    L.append("")
    L.append(f"- data: `{meta['data']}` (Massive USD_JPY M15、TV 側は OANDA feed = ベンダー差あり)")
    L.append(f"- window: {meta['start']} → {meta['end']} (warmup {meta['warmup']}), bars in window = {meta['bars']}")
    L.append(f"- friction: {FRICTION_PIPS} pip / trade (USD_JPY RT)。WR / PF / EV は **net** (摩擦後)、harness 比較のみ gross")
    L.append("- ラベル: 走 0 = 宣言 BT 再現 (2 変種) / 走 0′〜4 = **C0 近似 + intrabar 順序近似** / 走 5 = **C6 近似 (参考値)**")
    sg = res.get("signals", {})
    L.append(f"- window 内 raw entry signal = {sg.get('entry_signal_in_window')} (po_up_start {sg.get('po_up_start_in_window')})。"
             "1 建玉制 (Pine pyramiding=0) なので N は exit 長で変わる")
    L.append("")
    if res.get("harness_unverified"):
        L.append("> 🔴 **HARNESS 未検証**: 走 0 のどの変種も canon (N=46 / WR 23.91% / PF 3.866 / avg winner bars 458) を ±10% で再現しない。"
                 "task 文書「走 0 が現行 BT を再現できないまま制約付きの数字を出さない」に従い、**以下の全数値は引用禁止 — "
                 "packet に載せるのは分解の順位・向き・exit 種別の構造のみ**。要因: (1) v17 canon Pine がリポジトリに無い "
                 "(TV slot は 2026-05-21 上書き、TV は本セッションで接続不可) → flip exit の定義は推定、(2) データが Massive "
                 "(TV は OANDA feed)、(3) EMA 初期化 / percentile 実装差。")
        L.append("")
    L.append("## Harness 検証 (走 0 vs canon N=46 / WR 23.91% / PF 3.866 / avg winner bars 458、±10%)")
    L.append("")
    L.append("| 走 0 変種 | 指標 | canon | port | ok |")
    L.append("|---|---|---|---|---|")
    for lab, chk in res["harness"].items():
        for k in ("n", "wr", "pf", "avg_win_bars"):
            v = chk[k]
            L.append(f"| {lab} | {k} | {_f(v['canon'], 4)} | {_f(v['port'], 4)} | {'✅' if v['ok'] else '❌'} |")
        L.append(f"| {lab} | **all** | | | {'✅' if chk['all_ok'] else '❌'} |")
    L.append("")
    L.append("### flip exit 定義の識別 (canon Pine 不在のため。entry / SL 1.5×ATR / 480 cap は固定、gross)")
    L.append("")
    L.append("| flip 定義 | 説明 | N | WR | PF | avg win bars | EV gross | payoff | exits | harness |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in res["harness_identification"]:
        ex = ", ".join(f"{k} {v}" for k, v in r["exit_reasons"].items())
        L.append(f"| {r['flip_def']} | {r['desc']} | {r['n']} | {_f(r['wr_gross']*100,1)}% | {_f(r['pf_gross'])} | "
                 f"{_f(r['avg_win_bars'],0)} | {_f(r['ev_gross_pips'])} | {_f(r['payoff'])} | {ex} | {'✅' if r['harness_ok'] else '❌'} |")
    L.append("")
    for order, rows in res["walks"].items():
        L.append(f"## 走 0〜5 — bar 内順序仮定 = `{order}`" + (" (既定・保守側)" if order == "adverse_first" else " (感度)"))
        L.append("")
        L.append("| 走 | N | WR | Wilson lo | PF (net) | EV net p/t | Σ net p | avg win p | avg loss p | payoff | winner ≤8h | winner hold bars med (p25–p75) | loser hold bars med | exit 種別 |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for s in rows:
            hw, hl = s["hold_bars_winners"], s["hold_bars_losers"]
            ex = ", ".join(f"{k} {v}" for k, v in s["exit_reasons"].items())
            L.append(
                f"| {s['label']} | {s['n']} | {_f(s['wr']*100,1)}% | {_f(s['wilson95_lower']*100,1)}% | {_f(s['pf_net'])} | "
                f"{_f(s['ev_net_pips'])} | {_f(s['total_net_pips'],1)} | {_f(s['avg_win_pips'],1)} | {_f(s['avg_loss_pips'],1)} | "
                f"{_f(s['payoff'])} | {_f((s['winners_within_8h_share'] or 0)*100,0)}% | "
                f"{_f(hw['median'],0)} ({_f(hw['p25'],0)}–{_f(hw['p75'],0)}) | {_f(hl['median'],0)} | {ex} |"
            )
        L.append("")
        L.append("winner / loser 別 exit 種別:")
        L.append("")
        L.append("| 走 | winners | losers |")
        L.append("|---|---|---|")
        for s in rows:
            eb = s["exit_reason_by_outcome"]
            L.append(f"| {s['label']} | {', '.join(f'{k} {v}' for k, v in eb['winners'].items()) or '—'} | "
                     f"{', '.join(f'{k} {v}' for k, v in eb['losers'].items()) or '—'} |")
        L.append("")
        L.append(f"限界分解 (走 0′ に overlay を単独で載せる、順序 = `{order}`):")
        L.append("")
        L.append("| 構成 | N | WR | PF (net) | EV net p/t | Σ net p | winner ≤8h | exit 種別 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for s in res["marginals"][order]:
            ex = ", ".join(f"{k} {v}" for k, v in s["exit_reasons"].items())
            L.append(f"| {s['label']} | {s['n']} | {_f(s['wr']*100,1)}% | {_f(s['pf_net'])} | {_f(s['ev_net_pips'])} | "
                     f"{_f(s['total_net_pips'],1)} | {_f((s['winners_within_8h_share'] or 0)*100,0)}% | {ex} |")
        L.append("")
    L.append("## C0 感度 (BT 側 what-if、走 0′〜4 を再集計。live 実測率は marker 付き live N 蓄積後に差し替え)")
    L.append("")
    for order, wi in res["c0_whatifs"].items():
        L.append(f"### 順序仮定 = `{order}`")
        L.append("")
        L.append("| what-if | 走 | N | WR | PF | EV net | Σ net | winner ≤8h | SL 分岐 | flags |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for name, rows in wi.items():
            for r in rows:
                L.append(f"| {name} | {r['label']} | {r['n']} | {_f(r['wr']*100,1)}% | {_f(r['pf_net'])} | "
                         f"{_f(r['ev_net_pips'])} | {_f(r['total_net_pips'],1)} | {_f((r['winners_within_8h_share'] or 0)*100,0)}% | "
                         f"{r['sl_branches']} | {r['c0_flags']} |")
        L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=str(ROOT / "data/cache/massive/USD_JPY_15m.parquet"))
    ap.add_argument("--start", default=WINDOW_START)
    ap.add_argument("--end", default=WINDOW_END)
    ap.add_argument("--warmup", default=WARMUP_START)
    ap.add_argument("--out-json", default=str(ROOT / "knowledge-base/raw/bt-results/kalman_d7_live_constrained_bt_2026_09_27.json"))
    ap.add_argument("--out-md", default="")
    ap.add_argument("--keep-trades", action="store_true")
    ap.add_argument("--run-date", default=pd.Timestamp.utcnow().strftime("%Y-%m-%d"))
    args = ap.parse_args()
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)

    data = slice_window(load_data(Path(args.data)), args.start, args.end, args.warmup)
    res = run_all(data, keep_trades=args.keep_trades)
    meta = {"data": args.data, "start": args.start, "end": args.end, "warmup": args.warmup,
            "bars": int(data["in_window"].sum()), "run_date": args.run_date,
            "constants": {k: (sorted(v) if isinstance(v, frozenset) else v) for k, v in globals().items()
                          if k.isupper() and isinstance(v, (int, float, str, frozenset, dict))}}
    res["meta"] = meta
    md = render_md(res, meta)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
