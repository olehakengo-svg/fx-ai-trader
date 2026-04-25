#!/usr/bin/env python3
"""
bb_squeeze_breakout Rescue BT — pre-registered 365-day validation.

Companion to:
    knowledge-base/wiki/analyses/bb-squeeze-rescue-2026-04-25.md

Hypothesis (H1):
    bb_squeeze_breakout (Live N=113, EV=-0.26p, PF=0.89) can be rescued by
    Cell-Filter (USD_JPY × London × TREND_BEAR) and/or Time-Floor (hold≥20m).
    At least one of A1/A2/A3 cells achieves SURVIVOR criteria.

Cell grid (4 main + 2 secondary, LOCKED):
    A0 baseline   : no filter, no time floor (current state)
    A1 cell only  : USD_JPY × London (UTC 6-13) × TREND_BEAR
    A2 time only  : hold ≥ 20min before TP/SL/TIME_DECAY_EXIT eligible
    A3 cell+time  : both A1 + A2
    Secondary (Bonferroni-exempt):
    A4 USD_JPY × London (any regime) + hold ≥ 20m
    A5 USD_JPY × any session × TREND_BEAR + hold ≥ 20m

Binding success (SURVIVOR, all AND, alpha_cell = 0.05/4 = 0.0125):
    EV > +1.0 p/trade
    PF > 1.30
    N >= 30
    Wilson_lo (WR) > BE_required (= (1-WR)/WR)
    Welch p < 0.0125 vs A0 baseline
    Walk-forward 90d × 4 windows: same-sign EV in all 4

Binding CANDIDATE:
    EV > +0.5 p/trade AND Welch p < 0.05 AND WF >= 3 same-sign

All REJECT -> bb_squeeze_breakout to _FORCE_DEMOTED (per pre-reg §6).

Survivor-bias defence (pre-floor catastrophic MAE breaker):
    During the time-floor period (hold < TIME_FLOOR_MIN), if running MAE breaches
    MAE_CATASTROPHIC = -15 pips (any pair), force-close as a loss at -SL_dist.
    This prevents the BT from being optimistic about "wait it out" when actually
    account would be wiped during the wait.

Usage:
    python3 scripts/bb_squeeze_rescue_bt.py --from 2025-04-26 --to 2026-04-25 \\
        --output-dir raw/bt-results/bb-squeeze-rescue-2026-04-25
    python3 scripts/bb_squeeze_rescue_bt.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
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

# ---------------------------------------------------------------------------
# Configuration (LOCKED from pre-reg)
# ---------------------------------------------------------------------------

TARGET_STRATEGY = "bb_squeeze_breakout"

PAIRS: List[str] = ["USDJPY=X", "EURUSD=X", "GBPUSD=X", "EURJPY=X", "GBPJPY=X"]

# 4 main cells (Bonferroni: alpha = 0.05 / 4 = 0.0125)
N_MAIN_CELLS = 4
ALPHA_CELL = 0.05 / N_MAIN_CELLS  # 0.0125

CELLS_MAIN: List[Dict[str, Any]] = [
    {"id": "A0", "label": "baseline",
     "filter": {"pair": None, "session": None, "regime": None}, "time_floor_min": 0},
    {"id": "A1", "label": "cell_only",
     "filter": {"pair": "USD_JPY", "session": "London", "regime": "TREND_BEAR"},
     "time_floor_min": 0},
    {"id": "A2", "label": "time_only",
     "filter": {"pair": None, "session": None, "regime": None}, "time_floor_min": 20},
    {"id": "A3", "label": "cell_and_time",
     "filter": {"pair": "USD_JPY", "session": "London", "regime": "TREND_BEAR"},
     "time_floor_min": 20},
]
CELLS_SECONDARY: List[Dict[str, Any]] = [
    {"id": "A4", "label": "USDJPY_london_anyregime_floor20",
     "filter": {"pair": "USD_JPY", "session": "London", "regime": None}, "time_floor_min": 20},
    {"id": "A5", "label": "USDJPY_anysession_TBEAR_floor20",
     "filter": {"pair": "USD_JPY", "session": None, "regime": "TREND_BEAR"}, "time_floor_min": 20},
]

# Binding criteria (LOCKED, AND for SURVIVOR)
SURVIVOR_EV_MIN = 1.0
SURVIVOR_PF_MIN = 1.30
SURVIVOR_N_MIN = 30
SURVIVOR_WF_WINDOWS = 4
SURVIVOR_WF_AGREE = 4   # all 4 same sign

# CANDIDATE criteria (relaxed)
CAND_EV_MIN = 0.5
CAND_P_MAX = 0.05
CAND_WF_AGREE_MIN = 3

# Survivor-bias defence
MAE_CATASTROPHIC_PIPS = 15.0  # if MAE breaches before time floor → force SL

# Per-pair friction (pips, Round-Trip)
FRICTION_RT: Dict[str, float] = {
    "USDJPY=X": 2.14, "EURUSD=X": 2.00, "GBPUSD=X": 4.53,
    "EURJPY=X": 2.50, "GBPJPY=X": 3.00,
}
PIP_MULT: Dict[str, float] = {
    "USDJPY=X": 100.0, "EURUSD=X": 10000.0, "GBPUSD=X": 10000.0,
    "EURJPY=X": 100.0, "GBPJPY=X": 100.0,
}

MAX_HOLD_BARS = 40   # 200 min horizon (5m bars)
BAR_MIN = 5

# ---------------------------------------------------------------------------
# Statistics helpers (shared with mafe_dynamic_exit_bt — kept inline for portability)
# ---------------------------------------------------------------------------

def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0: return 0.0
    p = wins / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (centre - margin) / denom * 100.0

def welch_t_test(xs: List[float], ys: List[float]) -> Tuple[float, float]:
    if len(xs) < 2 or len(ys) < 2:
        return (0.0, 1.0)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    vx, vy = statistics.variance(xs), statistics.variance(ys)
    nx, ny = len(xs), len(ys)
    se = math.sqrt(vx/nx + vy/ny) if (vx/nx + vy/ny) > 0 else 0.0
    if se == 0:
        return (0.0, 1.0)
    t = (mx - my) / se
    df_num = (vx/nx + vy/ny) ** 2
    df_den = (vx/nx)**2 / max(nx-1,1) + (vy/ny)**2 / max(ny-1,1)
    df = df_num / df_den if df_den > 0 else 1.0
    x = df / (df + t * t)
    p = _betai(df/2.0, 0.5, x)
    return (t, min(1.0, max(0.0, p)))

def _betai(a: float, b: float, x: float) -> float:
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = (math.lgamma(a+b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1.0-x) / b

def _betacf(a: float, b: float, x: float, max_iter: int = 200, eps: float = 3e-7) -> float:
    qab = a + b; qap = a + 1.0; qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30: d = 1e-30
    d = 1.0 / d; h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d
        delta = d * c; h *= delta
        if abs(delta - 1.0) < eps: break
    return h

# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------

def _utc_session(hour: int) -> str:
    if 0 <= hour < 6:  return "Tokyo"
    if 6 <= hour < 13: return "London"
    if 13 <= hour < 22: return "NY"
    return "OffHrs"

def cell_passes_filter(trade: Dict[str, Any], cell: Dict[str, Any]) -> bool:
    f = cell["filter"]
    pair = trade.get("pair") or trade.get("symbol") or ""
    pair_norm = pair.replace("=X", "").replace("_", "")
    if f.get("pair"):
        target = f["pair"].replace("_", "")
        if target not in pair_norm:
            return False
    if f.get("session"):
        try:
            ts = trade.get("entry_ts") or trade.get("entry_time")
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                dt = ts
            sess = _utc_session(dt.hour)
            if sess != f["session"]:
                return False
        except Exception:
            return False
    if f.get("regime"):
        if (trade.get("regime") or "").upper() != f["regime"].upper():
            return False
    return True

# ---------------------------------------------------------------------------
# PnL simulator with time-floor + catastrophic MAE breaker
# ---------------------------------------------------------------------------

def simulate_pnl(trade: Dict[str, Any], time_floor_min: int) -> Dict[str, Any]:
    """Apply time-floor and catastrophic MAE breaker to a baseline trade.

    Inputs (trade):
      direction:           "BUY"|"SELL"
      entry_price          float
      tp / sl              float
      bars: list of (ts, open, high, low, close)  — 5m bars from entry
      pair                 e.g. "USDJPY=X"
    Output:
      pnl_pips             realized after rule
      exit_reason          "TP"|"SL"|"MAE_BREAKER"|"FLOOR_TP"|"FLOOR_SL"|"TIMEOUT"
      hold_min             int
      max_mae_pips_pre_floor  float  (for survivor-bias diagnostics)
    """
    direction = trade.get("direction", "BUY")
    ep = trade["entry_price"]
    tp = trade["tp"]
    sl = trade["sl"]
    bars = trade.get("bars", [])
    pair = trade.get("pair") or "USDJPY=X"
    pip = PIP_MULT.get(pair, 100.0)
    fric_exit_half = FRICTION_RT.get(pair, 2.0) / 2.0
    sign = 1 if direction == "BUY" else -1

    max_mae_pre = 0.0
    floor_reached = (time_floor_min == 0)
    exit_reason = "TIMEOUT"
    hold_bars = 0
    realized = 0.0
    for j, (ts, o, h, l, c) in enumerate(bars):
        hold_bars = j + 1
        hold_min = hold_bars * BAR_MIN
        # Running MAE (worst adverse excursion in pips)
        if direction == "BUY":
            mae = (ep - l) * pip
        else:
            mae = (h - ep) * pip
        if not floor_reached and mae > max_mae_pre:
            max_mae_pre = mae
        # Survivor-bias catastrophic breaker
        if not floor_reached and mae >= MAE_CATASTROPHIC_PIPS:
            realized = -mae - fric_exit_half  # force SL at MAE depth
            exit_reason = "MAE_BREAKER"
            break
        # Pre-floor: TP/SL touches are deferred (kept open) per Time-Floor rule
        if not floor_reached:
            if hold_min >= time_floor_min:
                floor_reached = True
            else:
                continue
        # Post-floor: TP/SL eligibility
        if direction == "BUY":
            if l <= sl:
                realized = (sl - ep) * pip * sign - fric_exit_half
                exit_reason = "FLOOR_SL" if time_floor_min > 0 else "SL"
                break
            if h >= tp:
                realized = (tp - ep) * pip * sign - fric_exit_half
                exit_reason = "FLOOR_TP" if time_floor_min > 0 else "TP"
                break
        else:
            if h >= sl:
                realized = (sl - ep) * pip * sign - fric_exit_half
                exit_reason = "FLOOR_SL" if time_floor_min > 0 else "SL"
                break
            if l <= tp:
                realized = (tp - ep) * pip * sign - fric_exit_half
                exit_reason = "FLOOR_TP" if time_floor_min > 0 else "TP"
                break
    else:
        # Hit max bars without TP/SL
        last_close = bars[-1][4] if bars else ep
        realized = (last_close - ep) * pip * sign - fric_exit_half
        exit_reason = "TIMEOUT"
        hold_bars = len(bars)
    return {
        "pnl_pips": realized,
        "exit_reason": exit_reason,
        "hold_min": hold_bars * BAR_MIN,
        "max_mae_pre_floor": max_mae_pre,
    }

# ---------------------------------------------------------------------------
# Cell-level evaluation
# ---------------------------------------------------------------------------

def evaluate_cell(trades: List[Dict[str, Any]], cell: Dict[str, Any],
                  baseline_pnls: Optional[List[float]] = None,
                  wf_windows: int = 4) -> Dict[str, Any]:
    """Compute metrics for one cell on the given trade universe.

    Returns: dict with n, wins, ev, pf, wlo, p_welch, wf, verdict.
    """
    matched = [t for t in trades if cell_passes_filter(t, cell)]
    sims = [simulate_pnl(t, cell["time_floor_min"]) for t in matched]
    pnls = [s["pnl_pips"] for s in sims]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    sum_pos = sum(p for p in pnls if p > 0)
    sum_neg = -sum(p for p in pnls if p < 0)
    ev = (sum(pnls) / n) if n else 0.0
    pf = (sum_pos / sum_neg) if sum_neg > 0 else (float("inf") if sum_pos > 0 else 0.0)
    wlo = wilson_lower(wins, n)
    rate = (wins / n) if n else 0.0
    be_required_wr = ((1 - rate) / rate * 100.0) if rate > 0 else float("inf")
    # Welch vs baseline
    if baseline_pnls is not None and cell["id"] != "A0" and len(baseline_pnls) >= 2 and n >= 2:
        _, p_welch = welch_t_test(pnls, baseline_pnls)
    else:
        p_welch = 1.0
    # Walk-forward: split sims into wf_windows by index
    wf_signs: List[int] = []
    if n >= wf_windows * 5 and wf_windows > 1:
        chunk = n // wf_windows
        for w in range(wf_windows):
            seg = pnls[w*chunk:(w+1)*chunk] if w < wf_windows-1 else pnls[w*chunk:]
            if not seg: continue
            seg_ev = statistics.mean(seg)
            wf_signs.append(1 if seg_ev > 0 else (-1 if seg_ev < 0 else 0))
    wf_agree = max(wf_signs.count(1), wf_signs.count(-1)) if wf_signs else 0
    # Catastrophic MAE breaker stats (diagnostics)
    breaker_n = sum(1 for s in sims if s["exit_reason"] == "MAE_BREAKER")
    breaker_pct = breaker_n / n * 100 if n else 0.0
    # Verdict
    verdict = "REJECT"
    survivor_conds = {
        "EV": ev > SURVIVOR_EV_MIN,
        "PF": pf > SURVIVOR_PF_MIN,
        "N": n >= SURVIVOR_N_MIN,
        "Wilson>BE": wlo > be_required_wr,
        "p<0.0125": p_welch < ALPHA_CELL if cell["id"] != "A0" else True,
        "WF_all_same": wf_agree >= SURVIVOR_WF_AGREE,
    }
    candidate_conds = {
        "EV": ev > CAND_EV_MIN,
        "p<0.05": p_welch < CAND_P_MAX if cell["id"] != "A0" else True,
        "WF>=3_same": wf_agree >= CAND_WF_AGREE_MIN,
    }
    if cell["id"] != "A0" and all(survivor_conds.values()):
        verdict = "SURVIVOR"
    elif cell["id"] != "A0" and all(candidate_conds.values()):
        verdict = "CANDIDATE"
    return {
        "cell_id": cell["id"], "label": cell["label"],
        "n": n, "wins": wins, "losses": losses, "rate_pct": rate * 100,
        "ev": ev, "pf": pf, "wilson_lo_pct": wlo, "be_required_wr_pct": be_required_wr,
        "p_welch": p_welch, "wf_signs": wf_signs, "wf_agree": wf_agree,
        "mae_breaker_n": breaker_n, "mae_breaker_pct": breaker_pct,
        "survivor_conds": survivor_conds, "candidate_conds": candidate_conds,
        "verdict": verdict, "pnls_for_baseline_comparison": pnls,
    }

# ---------------------------------------------------------------------------
# Synthetic / dry-run trade generator
# ---------------------------------------------------------------------------

def synth_null_trades(n: int = 200, seed: int = 42) -> List[Dict[str, Any]]:
    """Generate null-hypothesis trades: random walk → BT should yield REJECT."""
    rng = random.Random(seed)
    trades = []
    base_ts = datetime(2025, 6, 1, tzinfo=timezone.utc)
    for i in range(n):
        pair = rng.choice(PAIRS)
        pip = PIP_MULT[pair]
        direction = rng.choice(["BUY", "SELL"])
        ep = 150.0 if "JPY" in pair else 1.10
        tp_dist = 5.0  # pips
        sl_dist = 3.0  # pips
        sign = 1 if direction == "BUY" else -1
        tp = ep + sign * tp_dist / pip
        sl = ep - sign * sl_dist / pip
        # 5m bars: random walk with std ~1pip / bar
        bars = []
        price = ep
        for j in range(MAX_HOLD_BARS):
            ts = base_ts + timedelta(hours=i*4, minutes=(j+1)*BAR_MIN)
            step = rng.gauss(0, 1.0 / pip)
            o = price; price += step
            h = max(o, price) + abs(rng.gauss(0, 0.5/pip))
            l = min(o, price) - abs(rng.gauss(0, 0.5/pip))
            c = price
            bars.append((ts, o, h, l, c))
        regime = rng.choice(["TREND_BEAR", "RANGE", "TREND_BULL"])
        sess_hour = rng.choice([2, 9, 15])  # Tokyo / London / NY
        entry_ts = (base_ts + timedelta(hours=i*4)).replace(hour=sess_hour)
        trades.append({
            "pair": pair, "symbol": pair,
            "direction": direction, "entry_price": ep, "tp": tp, "sl": sl,
            "bars": bars, "regime": regime, "entry_ts": entry_ts.isoformat(),
        })
    return trades

# ---------------------------------------------------------------------------
# Real trade extraction (stub — full implementation parallel to mafe harness)
# ---------------------------------------------------------------------------

def extract_real_trades(from_iso: str, to_iso: str) -> List[Dict[str, Any]]:
    """Replay bb_squeeze_breakout entries via compute_scalp_signal across PAIRS.
    Implemented only when not in --dry-run. Mirrors mafe_dynamic_exit_bt.py
    extract_bb_rsi_entries pattern but filters to TARGET_STRATEGY.
    """
    # Deferred imports
    from app import compute_scalp_signal, _compute_bt_htf_bias, get_master_bias
    from modules.data import fetch_ohlcv_massive, fetch_ohlcv_range
    out: List[Dict[str, Any]] = []
    for symbol in PAIRS:
        try:
            df = None
            try:
                days = (datetime.fromisoformat(to_iso[:10]) - datetime.fromisoformat(from_iso[:10])).days + 5
                df = fetch_ohlcv_massive(symbol, "5m", days=days)
                df = df.loc[(df.index >= from_iso) & (df.index <= to_iso)]
            except Exception:
                df = fetch_ohlcv_range(symbol, from_iso, to_iso, interval="5m")
            if df is None or len(df) < 200:
                print(f"[skip] {symbol}: insufficient data", flush=True)
                continue
            try:
                _layer1 = get_master_bias(symbol)
            except Exception:
                _layer1 = {"direction": "neutral", "label": "-", "score": 0}
            _htf = _compute_bt_htf_bias(df, min(300, len(df) - 1), mode="scalp")
            for i in range(max(200, 50), len(df) - MAX_HOLD_BARS - 1):
                bar_df = df.iloc[max(0, i - 500): i + 1]
                bar_time = df.index[i]
                if hasattr(bar_time, "tzinfo") and bar_time.tzinfo is None:
                    bar_time = bar_time.replace(tzinfo=timezone.utc)
                try:
                    sig = compute_scalp_signal(
                        bar_df, tf="5m", sr_levels=[],
                        symbol=symbol, backtest_mode=True,
                        bt_layer1=_layer1, bt_htf=_htf,
                    )
                except Exception:
                    continue
                if not sig: continue
                if (sig.get("entry_type") or "") != TARGET_STRATEGY: continue
                # Capture bars after entry for simulator
                future = df.iloc[i+1: i+1+MAX_HOLD_BARS]
                bars = [(future.index[k],
                         float(future.iloc[k]["Open"]),
                         float(future.iloc[k]["High"]),
                         float(future.iloc[k]["Low"]),
                         float(future.iloc[k]["Close"])) for k in range(len(future))]
                out.append({
                    "pair": symbol, "symbol": symbol,
                    "direction": sig.get("signal", "BUY"),
                    "entry_price": float(sig.get("entry_price") or bar_df.iloc[-1]["Close"]),
                    "tp": float(sig.get("tp") or 0),
                    "sl": float(sig.get("sl") or 0),
                    "bars": bars,
                    "regime": (sig.get("regime") or {}).get("regime", "UNK"),
                    "entry_ts": bar_time.isoformat(),
                })
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
    ap.add_argument("--output-dir", default="raw/bt-results/bb-squeeze-rescue-2026-04-25")
    ap.add_argument("--dry-run", action="store_true",
                    help="Use synthetic null trades; expects all REJECT")
    ap.add_argument("--n-synth", type=int, default=200)
    args = ap.parse_args()

    print("=" * 78)
    print(f"bb_squeeze_breakout Rescue BT — pre-reg LOCKED 2026-04-25")
    print(f"  alpha_cell = {ALPHA_CELL} (Bonferroni 0.05/{N_MAIN_CELLS})")
    print(f"  SURVIVOR: EV>{SURVIVOR_EV_MIN} PF>{SURVIVOR_PF_MIN} N>={SURVIVOR_N_MIN} "
          f"Wilson>BE Welch_p<{ALPHA_CELL} WF={SURVIVOR_WF_AGREE}/{SURVIVOR_WF_WINDOWS}")
    print(f"  MAE_CATASTROPHIC_PIPS = {MAE_CATASTROPHIC_PIPS} (survivor-bias defence)")
    print("=" * 78)

    if args.dry_run:
        print(f"[DRY-RUN] generating {args.n_synth} synthetic null trades (random walk)")
        trades = synth_null_trades(args.n_synth)
    else:
        print(f"[LIVE] extracting real {TARGET_STRATEGY} entries {args.from_iso} → {args.to_iso}")
        trades = extract_real_trades(args.from_iso, args.to_iso)

    print(f"  N entries: {len(trades)}")
    if not trades:
        print("[FATAL] no trades to evaluate — abort"); return 2

    # First evaluate baseline (A0) to obtain pnls_for_baseline_comparison
    base_eval = evaluate_cell(trades, CELLS_MAIN[0])
    base_pnls = base_eval["pnls_for_baseline_comparison"]

    # All cells
    results = []
    for cell in CELLS_MAIN + CELLS_SECONDARY:
        r = evaluate_cell(trades, cell, baseline_pnls=base_pnls if cell["id"] != "A0" else None)
        results.append(r)

    # Print summary
    print("\n--- Cell results ---")
    print(f"{'cell':<6}{'label':<28}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}"
          f"{'Wlo%':>6}{'BE%':>6}{'p_welch':>9}{'WF':>5}{'MAE!%':>7}{'verdict':>10}")
    for r in results:
        be_s = f"{r['be_required_wr_pct']:.1f}" if r['be_required_wr_pct'] != float("inf") else " inf"
        pf_s = f"{r['pf']:.2f}" if r['pf'] != float("inf") else " inf"
        print(f"{r['cell_id']:<6}{r['label'][:27]:<28}{r['n']:>5}{r['rate_pct']:>6.1f}"
              f"{r['ev']:>+7.2f}{pf_s:>6}{r['wilson_lo_pct']:>6.1f}{be_s:>6}"
              f"{r['p_welch']:>9.4f}{r['wf_agree']:>3}/{len(r['wf_signs'])}"
              f"{r['mae_breaker_pct']:>6.1f}%{r['verdict']:>10}")

    # Meta verdict
    survivors = [r for r in results if r["cell_id"] in ("A1", "A2", "A3") and r["verdict"] == "SURVIVOR"]
    candidates = [r for r in results if r["cell_id"] in ("A1", "A2", "A3") and r["verdict"] == "CANDIDATE"]
    if survivors:
        meta = "SURVIVOR_PRESENT"
    elif candidates:
        meta = "CANDIDATE_PRESENT"
    else:
        meta = "ALL_REJECT"
    print(f"\nMeta verdict: {meta}")
    print(f"  survivors: {[r['cell_id'] for r in survivors]}")
    print(f"  candidates: {[r['cell_id'] for r in candidates]}")

    # Write outputs
    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "pre_reg": "knowledge-base/wiki/analyses/bb-squeeze-rescue-2026-04-25.md",
        "alpha_cell": ALPHA_CELL,
        "mae_catastrophic_pips": MAE_CATASTROPHIC_PIPS,
        "from": args.from_iso, "to": args.to_iso,
        "dry_run": args.dry_run,
        "n_trades": len(trades),
        "meta_verdict": meta,
        "cells": [{k: v for k, v in r.items() if k != "pnls_for_baseline_comparison"} for r in results],
    }
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n[written] {out_dir / 'summary.json'}")

    # Dry-run sanity: null data should produce ALL_REJECT
    if args.dry_run:
        if meta == "ALL_REJECT":
            print("[DRY-RUN OK] null hypothesis correctly rejected (no false positives)")
            return 0
        else:
            print("[DRY-RUN FAIL] null data produced non-REJECT — investigate harness")
            return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
