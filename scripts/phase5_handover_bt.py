#!/usr/bin/env python3
"""
Phase 5 — S1 Session Handover Stop Hunt — 365-day BT (pre-reg LOCKED 2026-04-25)

Companion to:
    knowledge-base/wiki/analyses/phase5-pure-edge-portfolio-2026-04-25.md (S1)

Hypothesis (LOCKED):
    Session 切替 (Tokyo close / London open / NY open) 前後の流動性薄域で発生する
    "stop hunt + ヒゲ reject" の binary パターンが、レンジ環境での高勝率エッジを
    生む. シグナルは時刻 + price action のみ (オシレーター完全排除 / TAP-1, TAP-5
    違反なし).

Cell grid (27 cells, LOCKED):
    swing_lookback_bars: {3, 6, 12}    (15min/30min/60min)
    handover_window: {Tokyo_close, London_open, NY_close}  (3 単独 + 全合算 → 主軸 3)
    tp_rr_mult: {1.0, 1.2, 1.5}

Bonferroni: alpha_cell = 0.05 / 27 = 0.00185

Binding success (SURVIVOR, all AND):
    EV > +1.0 p/trade
    PF > 1.5
    WR > 60% (要件: レンジ盾)
    N >= 30
    Wilson_lo > 50%
    Welch p < 0.00185 vs random baseline (= ランダム時刻にエントリー)
    WF 4/4 same-sign

MAE Breaker:
    pre-floor 期間中の MAE >= MAE_CATASTROPHIC_PIPS で強制 SL.
    breaker_pct > 30% で FLOOR_INFEASIBLE フラグ → 自動 REJECT.

Usage:
    python3 scripts/phase5_handover_bt.py --from 2025-04-26 --to 2026-04-25 \\
        --output-dir raw/bt-results/phase5-handover-2026-04-25
    python3 scripts/phase5_handover_bt.py --dry-run
"""
from __future__ import annotations

import argparse, json, math, os, random, statistics, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

os.environ.setdefault("BT_MODE", "1")

try:
    from dotenv import load_dotenv
    _DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
    if _DOTENV_PATH.exists():
        load_dotenv(_DOTENV_PATH)
    else:
        load_dotenv()
except ImportError:
    pass

# Reuse helpers from bb_squeeze harness
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bb_squeeze_rescue_bt import (  # type: ignore
    wilson_lower, welch_t_test, simulate_pnl,
    PIP_MULT, FRICTION_RT, PAIRS, MAX_HOLD_BARS, BAR_MIN,
    MAE_CATASTROPHIC_PIPS, _fetch_range_5m,
)

# ---------------------------------------------------------------------------
# Configuration (LOCKED from pre-reg)
# ---------------------------------------------------------------------------

# 3 handover windows (UTC hour, minute) ranges
HANDOVER_WINDOWS = {
    "Tokyo_close":  (6, 0, 7, 30),     # 06:00-07:30 UTC
    "London_open":  (7, 0, 8, 30),     # 07:00-08:30 UTC (slight overlap with Tokyo close)
    "NY_close":     (20, 30, 21, 30),  # 20:30-21:30 UTC
}

WICK_RATIO_MIN = 0.55           # ヒゲが (ヒゲ+ボディ) の 55% 以上
SL_ATR_OFFSET = 0.3             # SL = bar 高/安 ± 0.3 × ATR
REENTRY_BLOCK_BARS = 12         # 60min cool-down

# Cell grid
SWING_LOOKBACK_GRID = [3, 6, 12]
HANDOVER_KEYS_GRID = list(HANDOVER_WINDOWS.keys())
TP_RR_GRID = [1.0, 1.2, 1.5]
N_CELLS = len(SWING_LOOKBACK_GRID) * len(HANDOVER_KEYS_GRID) * len(TP_RR_GRID)
ALPHA_CELL = 0.05 / N_CELLS  # 0.00185

# Binding criteria
SURVIVOR_EV_MIN = 1.0
SURVIVOR_PF_MIN = 1.5
SURVIVOR_WR_MIN = 60.0
SURVIVOR_N_MIN = 30
SURVIVOR_WLO_MIN = 50.0
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

# ---------------------------------------------------------------------------
# Signal extraction (S1 strategy logic, no oscillator)
# ---------------------------------------------------------------------------

def _in_window(bar_time: datetime, window: Tuple[int, int, int, int]) -> bool:
    h0, m0, h1, m1 = window
    minute_now = bar_time.hour * 60 + bar_time.minute
    minute_lo = h0 * 60 + m0
    minute_hi = h1 * 60 + m1
    return minute_lo <= minute_now <= minute_hi

def extract_handover_entries(symbol: str, df, swing_lookback: int,
                             handover_key: str) -> List[Dict[str, Any]]:
    """S1 signal extraction. No oscillators, time + price action only."""
    window = HANDOVER_WINDOWS[handover_key]
    pip = PIP_MULT.get(symbol, 100.0)
    fric_half = FRICTION_RT.get(symbol, 2.0) / 2.0 / pip
    out: List[Dict[str, Any]] = []
    last_entry_bar = -REENTRY_BLOCK_BARS

    for i in range(max(swing_lookback + 1, 50), len(df) - MAX_HOLD_BARS - 1):
        if i - last_entry_bar < REENTRY_BLOCK_BARS:
            continue
        bar_time = df.index[i]
        if hasattr(bar_time, "tzinfo") and bar_time.tzinfo is None:
            bar_time = bar_time.replace(tzinfo=timezone.utc)
        if not _in_window(bar_time, window):
            continue
        # Swing detection (single bar)
        recent = df.iloc[i - swing_lookback: i]   # 直近 swing_lookback bar (current 含まず)
        recent_high = float(recent["High"].max())
        recent_low = float(recent["Low"].min())
        bar = df.iloc[i]
        bar_high = float(bar["High"])
        bar_low = float(bar["Low"])
        bar_open = float(bar["Open"])
        bar_close = float(bar["Close"])
        # ATR proxy
        atr = float(df["atr7"].iloc[i]) if "atr7" in df.columns else (bar_high - bar_low) * 1.0

        wick_top = bar_high - max(bar_open, bar_close)
        wick_bottom = min(bar_open, bar_close) - bar_low
        body = abs(bar_close - bar_open) + 1e-9

        sig_dir = None
        ep = None
        sl = None
        # SHORT: 上方 swing 抜き + 上ヒゲ reject
        wick_top_ratio = wick_top / (wick_top + body)
        if (bar_high > recent_high
                and wick_top_ratio >= WICK_RATIO_MIN
                and bar_close < recent_high):
            sig_dir = "SELL"
            ep = bar_close - fric_half  # SELL: short 摩擦
            sl = bar_high + SL_ATR_OFFSET * atr
        # LONG: 下方 swing 抜き + 下ヒゲ reject
        wick_bottom_ratio = wick_bottom / (wick_bottom + body)
        if sig_dir is None and (bar_low < recent_low
                                and wick_bottom_ratio >= WICK_RATIO_MIN
                                and bar_close > recent_low):
            sig_dir = "BUY"
            ep = bar_close + fric_half
            sl = bar_low - SL_ATR_OFFSET * atr
        if sig_dir is None:
            continue
        if i + 1 >= len(df):
            continue
        # capture forward bars
        future = df.iloc[i + 1: i + 1 + MAX_HOLD_BARS]
        bars = [(future.index[k],
                 float(future.iloc[k]["Open"]),
                 float(future.iloc[k]["High"]),
                 float(future.iloc[k]["Low"]),
                 float(future.iloc[k]["Close"])) for k in range(len(future))]
        out.append({
            "pair": symbol, "symbol": symbol,
            "direction": sig_dir,
            "entry_price": ep,
            "sl": sl,
            "tp": None,  # TP は cell ごとに後で計算
            "bars": bars,
            "entry_ts": bar_time.isoformat(),
            "swing_high": recent_high,
            "swing_low": recent_low,
            "atr": atr,
            "handover_key": handover_key,
        })
        last_entry_bar = i

    return out

def attach_tp(trade: Dict[str, Any], rr_mult: float) -> Dict[str, Any]:
    """TP を cell の RR mult に応じて計算."""
    ep = trade["entry_price"]
    sl = trade["sl"]
    sl_dist = abs(ep - sl)
    if trade["direction"] == "BUY":
        tp = ep + rr_mult * sl_dist
    else:
        tp = ep - rr_mult * sl_dist
    return {**trade, "tp": tp}

# ---------------------------------------------------------------------------
# Cell evaluation
# ---------------------------------------------------------------------------

def evaluate_cell(trades: List[Dict[str, Any]], cell: Dict[str, Any],
                  baseline_pnls: Optional[List[float]] = None) -> Dict[str, Any]:
    """1 cell の評価. trades は当該 swing_lookback × handover_key の抽出結果."""
    # Apply TP per cell
    tp_trades = [attach_tp(t, cell["tp_rr"]) for t in trades]
    # Simulate (no time-floor; this strategy is short-term, MAE Breaker only)
    sims = [simulate_pnl(t, time_floor_min=0) for t in tp_trades]
    pnls = [s["pnl_pips"] for s in sims]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    sum_pos = sum(p for p in pnls if p > 0)
    sum_neg = -sum(p for p in pnls if p < 0)
    ev = sum(pnls) / n if n else 0.0
    pf = sum_pos / sum_neg if sum_neg > 0 else (float("inf") if sum_pos > 0 else 0.0)
    wlo = wilson_lower(wins, n)
    rate = wins / n * 100 if n else 0.0
    if baseline_pnls is not None and len(baseline_pnls) >= 2 and n >= 2:
        _, p_welch = welch_t_test(pnls, baseline_pnls)
    else:
        p_welch = 1.0
    # WF
    wf_signs: List[int] = []
    if n >= WF_WINDOWS * 5:
        chunk = n // WF_WINDOWS
        for w in range(WF_WINDOWS):
            seg = pnls[w*chunk:(w+1)*chunk] if w < WF_WINDOWS-1 else pnls[w*chunk:]
            if seg:
                wf_signs.append(1 if statistics.mean(seg) > 0 else (-1 if statistics.mean(seg) < 0 else 0))
    wf_agree = max(wf_signs.count(1), wf_signs.count(-1)) if wf_signs else 0
    breaker_n = sum(1 for s in sims if s["exit_reason"] == "MAE_BREAKER")
    breaker_pct = breaker_n / n * 100 if n else 0.0
    floor_infeasible = breaker_pct > FLOOR_INFEASIBLE_BREAKER_PCT
    survivor_conds = {
        "EV>1.0": ev > SURVIVOR_EV_MIN,
        "PF>1.5": pf > SURVIVOR_PF_MIN,
        "WR>60%": rate > SURVIVOR_WR_MIN,
        "N>=30": n >= SURVIVOR_N_MIN,
        "Wlo>50%": wlo > SURVIVOR_WLO_MIN,
        f"p<{ALPHA_CELL:.5f}": p_welch < ALPHA_CELL,
        "WF_4/4": wf_agree >= SURVIVOR_WF_AGREE,
        "FLOOR_FEASIBLE": not floor_infeasible,
    }
    verdict = "SURVIVOR" if all(survivor_conds.values()) else "REJECT"
    return {
        "cell_id": cell["id"], "params": cell,
        "n": n, "wins": wins, "rate_pct": rate,
        "ev": ev, "pf": pf, "wilson_lo_pct": wlo,
        "p_welch": p_welch, "wf_signs": wf_signs, "wf_agree": wf_agree,
        "mae_breaker_n": breaker_n, "mae_breaker_pct": breaker_pct,
        "floor_infeasible": floor_infeasible,
        "survivor_conds": survivor_conds,
        "verdict": verdict, "pnls": pnls,
    }

# ---------------------------------------------------------------------------
# Random baseline (for Welch comparison): エントリー時刻をランダム化
# ---------------------------------------------------------------------------

def synth_random_baseline(seed: int = 42, n: int = 300) -> List[Dict[str, Any]]:
    """ランダム時刻 + ランダム direction の baseline (null hypothesis 用)."""
    from bb_squeeze_rescue_bt import synth_null_trades
    return synth_null_trades(n, seed=seed)

# ---------------------------------------------------------------------------
# Real extraction across pairs
# ---------------------------------------------------------------------------

def extract_all_handover_trades(from_iso: str, to_iso: str,
                                swing_lookback: int, handover_key: str
                                ) -> List[Dict[str, Any]]:
    from modules.indicators import add_indicators
    out: List[Dict[str, Any]] = []
    for symbol in PAIRS:
        try:
            df = _fetch_range_5m(symbol, from_iso, to_iso)
            df = add_indicators(df).dropna()
            ents = extract_handover_entries(symbol, df, swing_lookback, handover_key)
            print(f"[entries] {symbol} L{swing_lookback} {handover_key}: {len(ents)}", flush=True)
            out.extend(ents)
        except Exception as e:
            print(f"[err] {symbol}: {e}", flush=True)
    return out

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_iso", default="2025-04-26")
    ap.add_argument("--to", dest="to_iso", default="2026-04-25")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.output_dir is None:
        args.output_dir = ("/tmp/phase5-handover-dryrun" if args.dry_run
                           else "raw/bt-results/phase5-handover-2026-04-25")
    _proj_root = str(Path(__file__).resolve().parents[1])
    if _proj_root not in sys.path:
        sys.path.insert(0, _proj_root)

    print("=" * 90)
    print("Phase 5 S1 — Session Handover Stop Hunt 365日 BT (pre-reg LOCKED 2026-04-25)")
    print(f"  alpha_cell = {ALPHA_CELL:.5f} (Bonferroni 0.05/{N_CELLS})")
    print(f"  swing_lookback × handover × tp_rr = {len(SWING_LOOKBACK_GRID)}×{len(HANDOVER_KEYS_GRID)}×{len(TP_RR_GRID)} = {N_CELLS} cells")
    print(f"  SURVIVOR: EV>{SURVIVOR_EV_MIN} PF>{SURVIVOR_PF_MIN} WR>{SURVIVOR_WR_MIN}% "
          f"N>={SURVIVOR_N_MIN} Wlo>{SURVIVOR_WLO_MIN}% p<{ALPHA_CELL:.5f} WF=4/4")
    print(f"  MAE_CATASTROPHIC_PIPS = {MAE_CATASTROPHIC_PIPS}")
    print("=" * 90)

    # Random baseline (for Welch comparison)
    if args.dry_run:
        print("[DRY-RUN] using synthetic random baseline + synth handover trades")
        baseline_trades = synth_random_baseline(seed=42, n=300)
        # synthetic handover trades (random walk)
        per_extraction: Dict[Tuple[int, str], List[Dict[str, Any]]] = {}
        for sl in SWING_LOOKBACK_GRID:
            for hk in HANDOVER_KEYS_GRID:
                per_extraction[(sl, hk)] = synth_random_baseline(seed=hash((sl, hk)) & 0xff, n=50)
    else:
        print(f"[LIVE] extracting {args.from_iso} → {args.to_iso}")
        # Random baseline = ランダム時刻のサンプル (handover 外の時刻)
        # 実装上は、extract された trades の sub-set を null として使うか、
        # 時刻を shuffle する. ここでは synth baseline で代替 (将来改善余地).
        baseline_trades = synth_random_baseline(seed=42, n=300)
        per_extraction = {}
        for sl in SWING_LOOKBACK_GRID:
            for hk in HANDOVER_KEYS_GRID:
                ents = extract_all_handover_trades(args.from_iso, args.to_iso, sl, hk)
                per_extraction[(sl, hk)] = ents

    baseline_sims = [simulate_pnl(t, 0) for t in baseline_trades]
    baseline_pnls = [s["pnl_pips"] for s in baseline_sims]

    # Evaluate full grid
    print(f"\n--- Cell results ---")
    print(f"{'cell':<6}{'L':>3}{'window':<14}{'RR':>5}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}"
          f"{'Wlo%':>6}{'p_welch':>9}{'WF':>5}{'MAE!%':>7}{'verdict':>10}")
    grid: List[Dict[str, Any]] = []
    cell_id = 0
    for sl in SWING_LOOKBACK_GRID:
        for hk in HANDOVER_KEYS_GRID:
            for rr in TP_RR_GRID:
                cell_id += 1
                cell = {"id": f"C{cell_id:02d}", "swing_lookback": sl,
                        "handover": hk, "tp_rr": rr}
                trades = per_extraction.get((sl, hk), [])
                r = evaluate_cell(trades, cell, baseline_pnls=baseline_pnls)
                grid.append(r)
                pf_s = f"{r['pf']:.2f}" if r['pf'] != float("inf") else " inf"
                print(f"{r['cell_id']:<6}{sl:>3}{hk[:13]:<14}{rr:>5.1f}"
                      f"{r['n']:>5}{r['rate_pct']:>6.1f}{r['ev']:>+7.2f}{pf_s:>6}"
                      f"{r['wilson_lo_pct']:>6.1f}{r['p_welch']:>9.4f}"
                      f"{r['wf_agree']:>3}/{len(r['wf_signs'])}"
                      f"{r['mae_breaker_pct']:>6.1f}%{r['verdict']:>10}")

    survivors = [r for r in grid if r["verdict"] == "SURVIVOR"]
    meta = "SURVIVOR_PRESENT" if survivors else "ALL_REJECT"
    print(f"\nMeta verdict: {meta}")
    print(f"  survivors: {[r['cell_id'] for r in survivors]}")

    # Output
    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "pre_reg": "knowledge-base/wiki/analyses/phase5-pure-edge-portfolio-2026-04-25.md (S1)",
        "alpha_cell": ALPHA_CELL,
        "n_cells": N_CELLS,
        "mae_catastrophic_pips": MAE_CATASTROPHIC_PIPS,
        "from": args.from_iso, "to": args.to_iso,
        "dry_run": args.dry_run,
        "meta_verdict": meta,
        "survivors_count": len(survivors),
        "cells": [{k: v for k, v in r.items() if k != "pnls"} for r in grid],
    }
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n[written] {out_dir / 'summary.json'}")

    if args.dry_run:
        if not survivors:
            print("[DRY-RUN OK] null hypothesis correctly rejected (no false SURVIVOR)")
            return 0
        else:
            print("[DRY-RUN FAIL] null produced SURVIVOR — investigate")
            return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
