#!/usr/bin/env python3
"""
MAFE Dynamic Exit BT — pre-registered 365-day validation for bb_rsi_reversion.

Companion to:
    knowledge-base/wiki/analyses/pre-registration-mafe-dynamic-exit-2026-04-24.md

Hypothesis (H_primary):
    Under bb_rsi_reversion Shadow regime (WR=28.8%, EV=-1.39p), a dynamic exit rule
      (a) MAE_cumulative >= Z pips at any post-entry bar j, OR
      (b) bar j >= X and MFE_cumulative < Y pips
    exits at market and delivers ΔEV >= +0.5p vs baseline across 48 param cells
    with Bonferroni-corrected significance (alpha_cell = 1.04e-3).

Parameter grid (48 cells, LOCKED):
    X (time limit in 5m bars): {3, 5, 8, 12}
    Y (MFE min in pips):       {0, 1, 2, 3}
    Z (MAE limit in pips):     {3, 5, 8}

Binding success (SURVIVOR, all AND):
    DeltaEV >= +0.5 p/trade
    Welch p < 1.04e-3
    Fisher WR p < 1.04e-3
    Wilson 95% lower bound on V2_WR > BEV + 3pp (i.e. > 53%)
    WF 2-bucket same sign on DeltaEV
    V2_N >= 80 (>= ~40% of original N)
    exit_reason distribution in [20:80, 80:20] range

Binding CANDIDATE:
    DeltaEV >= +0.3 p/trade AND Welch p (uncorrected) < 0.01 AND WF 2-bucket same sign

All REJECT -> closure path, no code deployment.

Data source (requires env vars, loaded from .env via python-dotenv if present):
    MASSIVE_API_KEY   primary (5m OHLCV, up to 180d+ per call with pagination)
    OANDA_TOKEN       fallback (range fetch with chunked pagination)

Local setup (once):
    1. cp .env.example .env    (if .env missing)
    2. echo "MASSIVE_API_KEY=<your_key>" >> .env
    3. echo "OANDA_TOKEN=<your_token>"   >> .env
    .env is gitignored; keys are user-owned (same as configured on Render).

Usage (local or Render Shell):
    python3 scripts/mafe_dynamic_exit_bt.py \\
        --from 2025-04-09 \\
        --to   2026-04-08 \\
        --output-dir raw/bt-results/mafe-dynamic-exit-2026-04-24

Dry-run (logic check, synthetic trades, no data fetch):
    python3 scripts/mafe_dynamic_exit_bt.py --dry-run

Sanity run (smaller window to validate pipeline before full BT):
    python3 scripts/mafe_dynamic_exit_bt.py \\
        --from 2025-04-09 --to 2025-04-23 \\
        --output-dir /tmp/mafe-sanity

Outputs:
    summary.json          per-cell metrics, verdict (SURVIVOR/CANDIDATE/REJECT)
    trades.json           raw per-trade baseline + all 48 V2 simulations
    result-stub.md        human-readable summary (feeds into wiki/analyses/)

Implementation policy:
    This script ONLY runs the pre-registered BT and emits the verdict table.
    It does NOT propose code changes. Human judgement is required to act on
    SURVIVOR cells (per pre-reg §6.1 GO path), per lesson-reactive-changes.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Prevent app.py AutoStart from spawning live demo_trader threads when we
# later import compute_scalp_signal. Must be set before any `import app`.
os.environ.setdefault("BT_MODE", "1")

# Load .env so MASSIVE_API_KEY / OANDA_TOKEN are picked up for local runs
# (matches the pattern used in app.py and _bt_baseline_comparison.py).
try:
    from dotenv import load_dotenv
    _DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
    if _DOTENV_PATH.exists():
        load_dotenv(_DOTENV_PATH)
    else:
        load_dotenv()  # fall back to CWD / inherited env
except ImportError:
    pass  # dotenv optional; env vars may already be set by the shell

# ---------------------------------------------------------------------------
# Configuration (LOCKED from pre-reg)
# ---------------------------------------------------------------------------

PAIRS: List[str] = ["USDJPY=X", "EURUSD=X", "GBPUSD=X", "EURJPY=X", "GBPJPY=X"]
X_GRID: List[int] = [3, 5, 8, 12]
Y_GRID: List[int] = [0, 1, 2, 3]
Z_GRID: List[int] = [3, 5, 8]
MAX_HOLD_BARS = 40                         # 200 min horizon (5m bars)
TARGET_STRATEGY = "bb_rsi_reversion"
ALPHA_CELL = 0.05 / (len(X_GRID) * len(Y_GRID) * len(Z_GRID))  # 1.04e-3
BEV = 50.0                                 # symmetric R:R approximation (pre-reg)
BEV_LOWER_GATE = BEV + 3.0                 # 53%

# Per-pair friction (pips, Round-Trip). Exit-only half-friction used below.
FRICTION_RT: Dict[str, float] = {
    "USDJPY=X": 2.14,
    "EURUSD=X": 2.00,
    "GBPUSD=X": 4.53,
    "EURJPY=X": 2.50,
    "GBPJPY=X": 3.00,
}

PIP_MULT: Dict[str, float] = {
    "USDJPY=X": 100.0,
    "EURUSD=X": 10000.0,
    "GBPUSD=X": 10000.0,
    "EURJPY=X": 100.0,
    "GBPJPY=X": 100.0,
}


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (centre - margin) / denom * 100.0


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2 Fisher exact, two-sided. Returns p-value.
       Table:  [[a, b], [c, d]]  (e.g. V2 wins / losses  vs  BASE wins / losses)
    """
    from math import lgamma, exp

    def log_prob(a, b, c, d):
        n = a + b + c + d
        return (
            lgamma(a + b + 1) + lgamma(c + d + 1)
            + lgamma(a + c + 1) + lgamma(b + d + 1)
            - lgamma(a + 1) - lgamma(b + 1)
            - lgamma(c + 1) - lgamma(d + 1)
            - lgamma(n + 1)
        )

    n = a + b + c + d
    row0 = a + b
    col0 = a + c
    p_obs = log_prob(a, b, c, d)
    total_p = 0.0
    for a_i in range(max(0, row0 + col0 - n), min(row0, col0) + 1):
        b_i = row0 - a_i
        c_i = col0 - a_i
        d_i = n - a_i - b_i - c_i
        lp = log_prob(a_i, b_i, c_i, d_i)
        if lp <= p_obs + 1e-9:
            total_p += exp(lp)
    return min(1.0, total_p)


def welch_t_test(xs: List[float], ys: List[float]) -> Tuple[float, float]:
    """Two-sample Welch t-test. Returns (t, two-sided p)."""
    if len(xs) < 2 or len(ys) < 2:
        return (0.0, 1.0)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    vx, vy = statistics.variance(xs), statistics.variance(ys)
    nx, ny = len(xs), len(ys)
    se = math.sqrt(vx / nx + vy / ny) if (vx / nx + vy / ny) > 0 else 0.0
    if se == 0:
        return (0.0, 1.0)
    t = (mx - my) / se
    # Welch-Satterthwaite df
    df_num = (vx / nx + vy / ny) ** 2
    df_den = (vx / nx) ** 2 / max(nx - 1, 1) + (vy / ny) ** 2 / max(ny - 1, 1)
    df = df_num / df_den if df_den > 0 else 1.0
    # Approximate two-sided p via survival function of Student-t (abramowitz)
    x = df / (df + t * t)
    # Regularized incomplete beta via continued fraction (approx)
    p = _betai(df / 2.0, 0.5, x)
    return (t, min(1.0, max(0.0, p)))


def _betai(a: float, b: float, x: float) -> float:
    """Incomplete beta function I_x(a,b), used for Student-t p-value approx."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1.0 - x) / b


def _betacf(a: float, b: float, x: float, max_iter: int = 200, eps: float = 3e-7) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


# ---------------------------------------------------------------------------
# Data fetch — pair-wise 5m OHLCV for [from_date, to_date]
# ---------------------------------------------------------------------------

def _fetch_range_5m(symbol: str, from_iso: str, to_iso: str):
    """Try MASSIVE, then OANDA range, raise on both fail."""
    import pandas as pd
    last_err = None
    try:
        from modules.data import fetch_ohlcv_massive
        days = (datetime.fromisoformat(to_iso[:10]) - datetime.fromisoformat(from_iso[:10])).days + 5
        df = fetch_ohlcv_massive(symbol, "5m", days=days)
        df = df.loc[(df.index >= from_iso) & (df.index <= to_iso)]
        if len(df) > 1000:
            print(f"[MASSIVE] {symbol}: {len(df)} bars", flush=True)
            return df
        last_err = f"massive returned only {len(df)} bars"
    except Exception as e:
        last_err = f"massive failed: {e}"

    try:
        from modules.data import fetch_ohlcv_range
        df1 = fetch_ohlcv_range(symbol, from_iso, to_iso, interval="5m")
        if len(df1) > 1000:
            print(f"[OANDA/range] {symbol}: {len(df1)} bars", flush=True)
            return df1
        last_err = f"oanda returned only {len(df1)} bars"
    except Exception as e:
        last_err = f"oanda failed: {e}; prev: {last_err}"

    raise RuntimeError(f"Both data sources failed for {symbol}: {last_err}")


# ---------------------------------------------------------------------------
# Entry extraction — replay bb_rsi_reversion via compute_scalp_signal
# ---------------------------------------------------------------------------

def extract_bb_rsi_entries(symbol: str, df) -> List[Dict[str, Any]]:
    """Walk bars, call compute_scalp_signal(backtest_mode=True), filter to
       entry_type == TARGET_STRATEGY. Return list of entry dicts.
    """
    # Deferred imports to avoid loading app.py in --dry-run
    from app import compute_scalp_signal, _compute_bt_htf_bias, get_master_bias
    try:
        _layer1 = get_master_bias(symbol)
    except Exception:
        _layer1 = {"direction": "neutral", "label": "-", "score": 0}

    MIN_BARS = 200
    entries: List[Dict[str, Any]] = []

    _htf_cache = {
        "htf": _compute_bt_htf_bias(df, min(300, len(df) - 1), mode="scalp"),
        "layer1": _layer1,
    }
    _last_htf_recalc = 0
    _HTF_RECALC = 48  # every 48 * 5min = 4h

    last_entry_bar = -99

    for i in range(max(MIN_BARS, 50), len(df) - MAX_HOLD_BARS - 1):
        if i - last_entry_bar < 1:
            continue
        if i - _last_htf_recalc >= _HTF_RECALC:
            _htf_cache["htf"] = _compute_bt_htf_bias(df, i, mode="scalp")
            _last_htf_recalc = i

        bar_df = df.iloc[max(0, i - 500): i + 1]
        bar_time = df.index[i]
        if hasattr(bar_time, "tzinfo") and bar_time.tzinfo is None:
            bar_time = bar_time.replace(tzinfo=timezone.utc)

        try:
            sig_result = compute_scalp_signal(
                bar_df, tf="5m", sr_levels=[],
                symbol=symbol, backtest_mode=True,
                bar_time=bar_time, htf_cache=_htf_cache,
            )
        except Exception:
            continue

        if sig_result.get("signal") == "WAIT":
            continue
        if sig_result.get("entry_type") != TARGET_STRATEGY:
            continue

        if i + 1 >= len(df):
            continue

        ep_raw = float(df.iloc[i + 1]["Open"])
        friction_half = FRICTION_RT[symbol] / 2.0 / PIP_MULT[symbol]
        sig = sig_result["signal"]
        ep = ep_raw + friction_half if sig == "BUY" else ep_raw - friction_half

        entries.append({
            "pair": symbol,
            "bar_idx": i,
            "entry_time": str(bar_time),
            "sig": sig,
            "ep": ep,
            "tp": float(sig_result.get("tp", ep)),
            "sl": float(sig_result.get("sl", ep)),
        })
        last_entry_bar = i

    print(f"[entries] {symbol}: {len(entries)} {TARGET_STRATEGY} entries", flush=True)
    return entries


# ---------------------------------------------------------------------------
# Baseline + V2 trade simulation
# ---------------------------------------------------------------------------

def simulate_trade(entry: Dict[str, Any], df) -> Dict[str, Any]:
    """Simulate both BASELINE (pure SL/TP within MAX_HOLD) and 48 V2 variants.
       Returns a dict with baseline_pnl_pips and v2 matrix {(X,Y,Z): pnl_pips}.
    """
    pair = entry["pair"]
    pip = PIP_MULT[pair]
    ep = entry["ep"]
    sig = entry["sig"]
    tp = entry["tp"]
    sl = entry["sl"]
    dir_sign = 1.0 if sig == "BUY" else -1.0
    exit_friction = FRICTION_RT[pair] / 2.0   # pips (exit-side half-friction)

    bar_idx = entry["bar_idx"]
    # Precompute per-bar cumulative MFE / MAE (pips) up to MAX_HOLD
    mfe_arr: List[float] = []  # pips
    mae_arr: List[float] = []  # pips
    close_price_arr: List[float] = []

    max_mfe = 0.0
    max_mae = 0.0
    exit_bar_base: Optional[int] = None
    base_pnl_pips: Optional[float] = None

    for j in range(1, MAX_HOLD_BARS + 1):
        k = bar_idx + 1 + j
        if k >= len(df):
            break
        fut = df.iloc[k]
        hi, lo, cl = float(fut["High"]), float(fut["Low"]), float(fut["Close"])

        if sig == "BUY":
            bar_mfe = (hi - ep) * pip
            bar_mae = (ep - lo) * pip
        else:
            bar_mfe = (ep - lo) * pip
            bar_mae = (hi - ep) * pip

        max_mfe = max(max_mfe, bar_mfe)
        max_mae = max(max_mae, bar_mae)
        mfe_arr.append(max_mfe)
        mae_arr.append(max_mae)
        close_price_arr.append(cl)

        # Baseline pure SL/TP hit check (no BE/TS/SR — clean comparator)
        if exit_bar_base is None:
            if sig == "BUY":
                hit_tp = hi >= tp
                hit_sl = lo <= sl
                if hit_tp and hit_sl:
                    out = "WIN" if cl >= ep else "LOSS"
                    exit_bar_base = j
                    base_pnl_pips = ((tp - ep) if out == "WIN" else (sl - ep)) * pip - exit_friction
                elif hit_tp:
                    exit_bar_base = j
                    base_pnl_pips = (tp - ep) * pip - exit_friction
                elif hit_sl:
                    exit_bar_base = j
                    base_pnl_pips = (sl - ep) * pip - exit_friction
            else:
                hit_tp = lo <= tp
                hit_sl = hi >= sl
                if hit_tp and hit_sl:
                    out = "WIN" if cl <= ep else "LOSS"
                    exit_bar_base = j
                    base_pnl_pips = ((ep - tp) if out == "WIN" else (ep - sl)) * pip - exit_friction
                elif hit_tp:
                    exit_bar_base = j
                    base_pnl_pips = (ep - tp) * pip - exit_friction
                elif hit_sl:
                    exit_bar_base = j
                    base_pnl_pips = (ep - sl) * pip - exit_friction

    # If baseline never hit SL/TP, close at max-hold bar close
    if base_pnl_pips is None:
        if close_price_arr:
            last_cl = close_price_arr[-1]
            base_pnl_pips = (last_cl - ep) * pip * dir_sign - exit_friction
            exit_bar_base = len(close_price_arr)
        else:
            base_pnl_pips = -exit_friction
            exit_bar_base = 0

    # V2 matrix
    v2_pnl: Dict[str, float] = {}
    v2_exit_reason: Dict[str, str] = {}
    v2_exit_bar: Dict[str, int] = {}
    base_bars = exit_bar_base if exit_bar_base is not None else 0

    for X in X_GRID:
        for Y in Y_GRID:
            for Z in Z_GRID:
                key = f"X{X}Y{Y}Z{Z}"
                # scan from bar 1..base_bars (never extend beyond baseline)
                v2_exit_j: Optional[int] = None
                v2_reason: str = "baseline"
                max_scan = min(base_bars, len(mae_arr))
                for j in range(1, max_scan + 1):
                    mfe_j = mfe_arr[j - 1]
                    mae_j = mae_arr[j - 1]
                    # (a) MAE breach — exit at MAE level (conservative)
                    if mae_j >= Z:
                        v2_exit_j = j
                        v2_reason = "mae_breach"
                        break
                    # (b) time-decay low-MFE — exit at bar close
                    if j >= X and mfe_j < Y:
                        v2_exit_j = j
                        v2_reason = "time_decay_low_mfe"
                        break

                if v2_exit_j is None:
                    # no V2 truncation — fall through to baseline outcome
                    v2_pnl[key] = base_pnl_pips
                    v2_exit_reason[key] = "baseline"
                    v2_exit_bar[key] = base_bars
                elif v2_reason == "mae_breach":
                    # stopped at -Z level + exit friction
                    v2_pnl[key] = -float(Z) - exit_friction
                    v2_exit_reason[key] = "mae_breach"
                    v2_exit_bar[key] = v2_exit_j
                else:
                    # time-decay: market exit at bar close
                    cl_j = close_price_arr[v2_exit_j - 1]
                    v2_pnl[key] = (cl_j - ep) * pip * dir_sign - exit_friction
                    v2_exit_reason[key] = "time_decay_low_mfe"
                    v2_exit_bar[key] = v2_exit_j

    return {
        "pair": pair,
        "entry_time": entry["entry_time"],
        "sig": sig,
        "baseline": {
            "pnl_pips": round(base_pnl_pips, 3),
            "exit_bar": base_bars,
        },
        "v2": {
            k: {
                "pnl_pips": round(v2_pnl[k], 3),
                "exit_reason": v2_exit_reason[k],
                "exit_bar": v2_exit_bar[k],
            } for k in v2_pnl
        },
    }


# ---------------------------------------------------------------------------
# Aggregation + binding criteria
# ---------------------------------------------------------------------------

def aggregate_cell(trades: List[Dict[str, Any]], X: int, Y: int, Z: int) -> Dict[str, Any]:
    key = f"X{X}Y{Y}Z{Z}"
    base_pnls = [t["baseline"]["pnl_pips"] for t in trades]
    v2_pnls = [t["v2"][key]["pnl_pips"] for t in trades]
    base_wins = sum(1 for p in base_pnls if p > 0)
    v2_wins = sum(1 for p in v2_pnls if p > 0)
    n = len(trades)

    base_ev = statistics.mean(base_pnls) if base_pnls else 0.0
    v2_ev = statistics.mean(v2_pnls) if v2_pnls else 0.0
    delta_ev = v2_ev - base_ev

    # Fisher (V2 vs BASE WR) as a 2x2 paired approximation: treat as independent
    a, b = v2_wins, n - v2_wins
    c, d = base_wins, n - base_wins
    fisher_p = fisher_exact_two_sided(a, b, c, d)

    # Welch t on per-trade PnL difference
    t_stat, welch_p = welch_t_test(v2_pnls, base_pnls)

    wilson_lo = wilson_lower(v2_wins, n) if n > 0 else 0.0
    v2_wr = (v2_wins / n * 100.0) if n > 0 else 0.0
    base_wr = (base_wins / n * 100.0) if n > 0 else 0.0

    # Walk-forward 2-bucket (first/second half of trades chronologically)
    half = n // 2
    wf_sign_match = False
    if half >= 10:
        v2a = [t["v2"][key]["pnl_pips"] for t in trades[:half]]
        v2b = [t["v2"][key]["pnl_pips"] for t in trades[half:]]
        ba = [t["baseline"]["pnl_pips"] for t in trades[:half]]
        bb = [t["baseline"]["pnl_pips"] for t in trades[half:]]
        d1 = statistics.mean(v2a) - statistics.mean(ba)
        d2 = statistics.mean(v2b) - statistics.mean(bb)
        wf_sign_match = (d1 > 0 and d2 > 0) or (d1 < 0 and d2 < 0)

    # exit_reason distribution
    reasons = [t["v2"][key]["exit_reason"] for t in trades]
    n_mae = sum(1 for r in reasons if r == "mae_breach")
    n_time = sum(1 for r in reasons if r == "time_decay_low_mfe")
    n_base = sum(1 for r in reasons if r == "baseline")
    v2_n = n_mae + n_time    # trades truncated by V2 (i.e. "engaged" V2)
    truncated_ratio = v2_n / n if n > 0 else 0.0

    # Binding criteria
    survivor = (
        delta_ev >= 0.5
        and welch_p < ALPHA_CELL
        and fisher_p < ALPHA_CELL
        and wilson_lo > BEV_LOWER_GATE
        and wf_sign_match
        and v2_n >= 80
        and (n_mae / max(v2_n, 1) >= 0.2 if v2_n > 0 else False)
        and (n_mae / max(v2_n, 1) <= 0.8 if v2_n > 0 else False)
    )
    candidate = (
        not survivor
        and delta_ev >= 0.3
        and welch_p < 0.01
        and wf_sign_match
    )
    verdict = "SURVIVOR" if survivor else ("CANDIDATE" if candidate else "REJECT")

    return {
        "X": X, "Y": Y, "Z": Z,
        "n": n,
        "base_wr": round(base_wr, 2),
        "v2_wr": round(v2_wr, 2),
        "base_ev": round(base_ev, 3),
        "v2_ev": round(v2_ev, 3),
        "delta_ev": round(delta_ev, 3),
        "welch_p": round(welch_p, 6),
        "fisher_p": round(fisher_p, 6),
        "wilson_lo": round(wilson_lo, 2),
        "wf_sign_match": wf_sign_match,
        "exit_dist": {"mae_breach": n_mae, "time_decay": n_time, "baseline": n_base},
        "v2_engaged_n": v2_n,
        "truncated_ratio": round(truncated_ratio, 3),
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run(args) -> int:
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    from_iso = f"{args.from_date}T00:00:00Z"
    to_iso = f"{args.to_date}T00:00:00Z"

    if args.dry_run:
        print("[dry-run] generating 50 synthetic trades for logic validation...", flush=True)
        trades = _synthetic_trades(50)
    else:
        # Fail fast if neither data-source credential is present.
        has_massive = bool(os.environ.get("MASSIVE_API_KEY"))
        has_oanda = bool(os.environ.get("OANDA_TOKEN") or os.environ.get("OANDA_API_TOKEN"))
        print(
            f"[env] MASSIVE_API_KEY={'set' if has_massive else 'MISSING'} | "
            f"OANDA_TOKEN={'set' if has_oanda else 'MISSING'}",
            flush=True,
        )
        if not (has_massive or has_oanda):
            print(
                "[fatal] neither MASSIVE_API_KEY nor OANDA_TOKEN found. "
                "For local runs, put them in .env at the repo root (see script "
                "docstring). For Render, set them in the service env.",
                file=sys.stderr,
            )
            return 2
        from modules.indicators import add_indicators
        all_entries: List[Dict[str, Any]] = []
        pair_df: Dict[str, Any] = {}
        for sym in PAIRS:
            print(f"[fetch] {sym} {from_iso[:10]} -> {to_iso[:10]}", flush=True)
            df = _fetch_range_5m(sym, from_iso, to_iso)
            df = add_indicators(df).dropna()
            pair_df[sym] = df
            entries = extract_bb_rsi_entries(sym, df)
            all_entries.extend(entries)

        print(f"[sim] simulating {len(all_entries)} trades x 48 cells...", flush=True)
        trades = []
        for ent in all_entries:
            t = simulate_trade(ent, pair_df[ent["pair"]])
            trades.append(t)

    # Sort trades chronologically for WF bucketing
    trades.sort(key=lambda t: t["entry_time"])

    print(f"[agg] computing 48-cell matrix over N={len(trades)}", flush=True)
    cells = []
    for X in X_GRID:
        for Y in Y_GRID:
            for Z in Z_GRID:
                cells.append(aggregate_cell(trades, X, Y, Z))

    summary = {
        "pre_registration": (
            "knowledge-base/wiki/analyses/"
            "pre-registration-mafe-dynamic-exit-2026-04-24.md"
        ),
        "target_strategy": TARGET_STRATEGY,
        "bt_window": {"from": args.from_date, "to": args.to_date},
        "pairs": PAIRS,
        "total_trades": len(trades),
        "alpha_cell": ALPHA_CELL,
        "bev_lower_gate": BEV_LOWER_GATE,
        "counts": {
            "SURVIVOR": sum(1 for c in cells if c["verdict"] == "SURVIVOR"),
            "CANDIDATE": sum(1 for c in cells if c["verdict"] == "CANDIDATE"),
            "REJECT": sum(1 for c in cells if c["verdict"] == "REJECT"),
        },
        "cells": cells,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    (outdir / "summary.json").write_text(json.dumps(summary, indent=2))
    (outdir / "trades.json").write_text(json.dumps(trades[:5000], indent=2))
    (outdir / "result-stub.md").write_text(_render_md(summary))

    print(
        f"[done] SURVIVOR={summary['counts']['SURVIVOR']} "
        f"CANDIDATE={summary['counts']['CANDIDATE']} "
        f"REJECT={summary['counts']['REJECT']}",
        flush=True,
    )
    print(f"[done] outputs under {outdir}/", flush=True)
    return 0


def _synthetic_trades(n: int) -> List[Dict[str, Any]]:
    import random
    random.seed(42)
    trades = []
    base_time = datetime(2025, 4, 9, tzinfo=timezone.utc)
    for i in range(n):
        pnl = random.gauss(-1.4, 4.0)  # approximate bb_rsi Shadow distribution
        t = {
            "pair": "USDJPY=X",
            "entry_time": (base_time.replace(minute=(i * 5) % 60)).isoformat(),
            "sig": "BUY" if i % 2 == 0 else "SELL",
            "baseline": {"pnl_pips": round(pnl, 3), "exit_bar": 10},
            "v2": {},
        }
        for X in X_GRID:
            for Y in Y_GRID:
                for Z in Z_GRID:
                    key = f"X{X}Y{Y}Z{Z}"
                    # Dry-run: V2 = baseline + small random adjustment
                    delta = random.gauss(0.2, 0.8)
                    reason = random.choice(["baseline", "mae_breach", "time_decay_low_mfe"])
                    t["v2"][key] = {
                        "pnl_pips": round(pnl + delta, 3),
                        "exit_reason": reason,
                        "exit_bar": random.randint(1, 15),
                    }
        trades.append(t)
    return trades


def _render_md(summary: Dict[str, Any]) -> str:
    counts = summary["counts"]
    lines = [
        f"# MAFE Dynamic Exit — BT Result ({summary['bt_window']['from']} to {summary['bt_window']['to']})",
        "",
        f"**Pre-reg**: {summary['pre_registration']}",
        f"**Target**: {summary['target_strategy']} | **N trades**: {summary['total_trades']}",
        f"**Alpha_cell (Bonferroni)**: {summary['alpha_cell']:.2e}",
        f"**Generated**: {summary['generated_at']}",
        "",
        "## Verdict counts",
        "",
        f"- SURVIVOR: **{counts['SURVIVOR']}**",
        f"- CANDIDATE: **{counts['CANDIDATE']}**",
        f"- REJECT: **{counts['REJECT']}**",
        "",
        "## Top 10 cells by DeltaEV",
        "",
        "| X | Y | Z | N | base_ev | v2_ev | dEV | v2_wr | wilson_lo | welch_p | fisher_p | WF | verdict |",
        "|--:|--:|--:|--:|--------:|------:|----:|------:|----------:|--------:|---------:|:--:|:-------:|",
    ]
    for c in sorted(summary["cells"], key=lambda x: -x["delta_ev"])[:10]:
        lines.append(
            f"| {c['X']} | {c['Y']} | {c['Z']} | {c['n']} | {c['base_ev']:+.2f} | "
            f"{c['v2_ev']:+.2f} | {c['delta_ev']:+.2f} | {c['v2_wr']:.1f} | "
            f"{c['wilson_lo']:.1f} | {c['welch_p']:.2e} | {c['fisher_p']:.2e} | "
            f"{'Y' if c['wf_sign_match'] else 'N'} | {c['verdict']} |"
        )
    lines.append("")
    lines.append("## Next step (per pre-reg §6)")
    lines.append("")
    if counts["SURVIVOR"] > 0:
        lines.append(
            "- **§6.1 GO path**: pick the minimum-complexity SURVIVOR cell "
            "(smallest X, then Y=0 preferred). Draft Shadow-deploy PR under a "
            "separate pre-reg."
        )
    elif counts["CANDIDATE"] > 0:
        lines.append(
            "- **§6.2 Extended Shadow path**: CANDIDATE(s) present but below "
            "Bonferroni. Wait for holdout 2026-05-07 additional N and re-evaluate."
        )
    else:
        lines.append(
            "- **§6.3 Closure path**: all 48 cells REJECT. Log lesson to "
            "wiki/lessons/ and maintain FORCE_DEMOTED for bb_rsi_reversion. "
            "Do NOT rescue via parameter expansion (pre-reg §7 forbids)."
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="from_date", default="2025-04-09")
    ap.add_argument("--to", dest="to_date", default="2026-04-08")
    ap.add_argument("--output-dir", dest="output_dir",
                    default="raw/bt-results/mafe-dynamic-exit-2026-04-24")
    ap.add_argument("--dry-run", action="store_true",
                    help="synthetic trades, no data fetch (logic validation only)")
    args = ap.parse_args()
    sys.path.insert(0, os.getcwd())
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
