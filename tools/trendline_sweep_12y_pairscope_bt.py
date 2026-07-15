#!/usr/bin/env python3
"""12y MASSIVE walk-forward PER-CELL (pair x direction) BT of the PRODUCTION
`trendline_sweep` trigger.

Pre-reg LOCK: knowledge-base/wiki/learning/trendline-sweep-gbpusd-loss-conversion-prereg-2026-07-13.md
Ledger id  : trendline_sweep_gbpusd_pairscope_2026-07-13  (gates G1..G6 LOCKED)

This is a ROUTING / pair-scope test. The production strategy
`strategies/daytrade/trendline_sweep.py` is used UNCHANGED (no parameter
tuning, no new signal). The ONLY thing under test is whether the trigger's
edge is pair(-direction)-specific.

Data: MASSIVE 15m parquet cache ONLY (Yahoo is FORBIDDEN, 60d limit).
      BT_MODE=1, BT_REQUIRE_MASSIVE_CACHE=1.

Two configurations are run and reported in full:
  * CONFIG-PROD : strategy fully UNCHANGED (SELL_ONLY_PAIRS applied).
                  -> EUR_USD SELL-only, GBP_USD BUY+SELL, EUR_GBP SELL-only.
                  This is the literal "production trigger unchanged" population;
                  it drives G1-G5 (the actually-traded population).
  * CONFIG-RAW  : SELL_ONLY_PAIRS lifted at RUNTIME (the file on disk is NOT
                  modified). Exposes the BUY leg for EUR_USD / EUR_GBP so the
                  "no single-side artifact" gate G6 can be evaluated honestly
                  on both legs of every pair.

Exit model: fixed bracket (SL / TP / time-stop) = the TV-aligned default the
production daytrade engine now uses (fixed SL, no BE inflation). Conservative
SL-first tie-break inside a bar. Single open position per pair (non-overlapping,
independent trades) for valid Wilson / t-test statistics.

Entry TRIGGER is 100% the unchanged production `TrendlineSweep().evaluate(ctx)`.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("BT_REQUIRE_MASSIVE_CACHE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")
sys.modules.setdefault("pytest", object())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as sp_stats  # noqa: E402

from modules.indicators import add_indicators  # noqa: E402
from strategies.context import SignalContext  # noqa: E402
from strategies.daytrade.trendline_sweep import TrendlineSweep  # noqa: E402

# ── Reproduce the repo's standard BT friction/spread model ──────────────
# Verbatim from app.py:_bt_spread / _bt_classify_session / _BT_SLIPPAGE
# (app.py is not importable here because it pulls in flask; the numeric model
# below is byte-identical to the production definitions as of 2026-07-13).
from modules.friction_model_v2 import _SESSION_MULTIPLIER  # noqa: E402

# app.py:_BT_SLIPPAGE  (per-SIDE slippage, price units)
_BT_SLIPPAGE = {
    "USDJPY": 0.005,
    "EURJPY": 0.005,
    "EURUSD": 0.00005,  # 0.5 pip / side
    "GBPUSD": 0.0001,   # 1.0 pip / side  (friction-analysis.md nominal, largest fix)
    "EURGBP": 0.00005,  # 0.5 pip / side
    "XAUUSD": 0.025,
}


def _bt_get_slippage(symbol: str) -> float:
    _s = symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
    for k, v in _BT_SLIPPAGE.items():
        if k in _s:
            return v
    if "JPY" in _s:
        return 0.004
    elif "XAU" in _s:
        return 0.025
    return 0.00004


def _bt_classify_session(h: int) -> str:
    if 13 <= h < 17:
        return "overlap_LN"
    if 13 <= h < 22:
        return "NY"
    if 7 <= h < 13:
        return "London"
    if 2 <= h < 7:
        return "Tokyo"
    if 0 <= h < 2:
        return "Asia_early"
    return "Sydney"


def _bt_spread(hour: int, symbol: str) -> float:
    """Per-side SPREAD (price units), pair x hour x session-multiplier.
    Byte-identical numeric model to app.py:_bt_spread."""
    h = hour
    _s = symbol.upper()
    _is_gold = "XAU" in _s
    _is_eur_gbp = "EURGBP" in _s or "EUR_GBP" in _s
    _is_gbp_usd = "GBPUSD" in _s or "GBP_USD" in _s
    _is_eur_usd = "EURUSD" in _s or "EUR_USD" in _s
    _is_eur_jpy = "EURJPY" in _s or "EUR_JPY" in _s
    _is_jpy = "JPY" in _s

    if _is_gold:
        base = 0.050 if h < 2 else 0.040 if h < 7 else 0.030 if h < 16 else 0.035 if h < 20 else 0.050
    elif _is_eur_gbp:
        base = 0.00020 if h < 2 else 0.00015 if h < 7 else 0.00010 if h < 16 else 0.00012 if h < 20 else 0.00020
    elif _is_gbp_usd:
        base = 0.00018 if h < 2 else 0.00012 if h < 7 else 0.00008 if h < 16 else 0.00010 if h < 20 else 0.00018
    elif _is_eur_usd:
        base = 0.00010 if h < 2 else 0.00005 if h < 7 else 0.00003 if h < 16 else 0.00004 if h < 20 else 0.00010
    elif _is_eur_jpy:
        base = 0.015 if h < 2 else 0.008 if h < 7 else 0.005 if h < 16 else 0.007 if h < 20 else 0.015
    elif _is_jpy:
        base = 0.010 if h < 2 else 0.005 if h < 7 else 0.003 if h < 16 else 0.004 if h < 20 else 0.010
    else:
        base = 0.00010 if h < 2 else 0.00006 if h < 7 else 0.00003 if h < 16 else 0.00004 if h < 20 else 0.00010

    sess = _bt_classify_session(h)
    mult = _SESSION_MULTIPLIER.get(sess, _SESSION_MULTIPLIER.get("default", 1.0))
    return base * mult


def round_turn_friction_price(entry_hour: int, exit_hour: int, symbol: str) -> float:
    """Production round-turn cost (price units):
    entry = spread(entry_hour)/2 + slip ; exit = spread(exit_hour)/2 + slip.
    => (spread_entry + spread_exit)/2 + 2*slip."""
    slip = _bt_get_slippage(symbol)
    return (_bt_spread(entry_hour, symbol) + _bt_spread(exit_hour, symbol)) / 2.0 + 2.0 * slip


# ── Config ──────────────────────────────────────────────────────────────
PAIRS = {
    "EUR_USD": "data/cache/massive/EUR_USD_15m_2014_2026.parquet",
    "GBP_USD": "data/cache/massive/GBP_USD_15m_2014_2026.parquet",
    "EUR_GBP": "data/cache/massive/EUR_GBP_15m.parquet",
}
SYMBOL = {"EUR_USD": "EUR_USD", "GBP_USD": "GBP_USD", "EUR_GBP": "EUR_GBP"}
INTERVAL = "15m"
WINDOW = 300          # ctx.df window; >=106 & >=last-100+50 => identical trendline result vs prod 3500
MAX_HOLD = 24         # 15m production daytrade time-stop (6h)
PIP_MULT = 10000      # all three are non-JPY majors
Z95 = 1.959963984540054
FDR_Q = 0.10
WILSON_GATE = 0.40
FRICTION_TP_GATE = 0.10
OUTFILE = ROOT / "bt-results" / "trendline_sweep-12y-pairscope-2026-07-13.json"


def _wilson_lower(wins: int, n: int, z: float = Z95) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def _pf(pnls) -> float:
    gp = sum(p for p in pnls if p > 0)
    gl = -sum(p for p in pnls if p < 0)
    if gl <= 0:
        return float("inf") if gp > 0 else 0.0
    return gp / gl


def _one_sided_p_gt0(pnls) -> float:
    """One-sided t-test, H0: mean <= 0 vs H1: mean > 0. Returns p-value."""
    a = np.asarray(pnls, dtype=float)
    n = len(a)
    if n < 2:
        return 1.0
    if a.std(ddof=1) == 0:
        return 0.0 if a.mean() > 0 else 1.0
    t = a.mean() / (a.std(ddof=1) / math.sqrt(n))
    # survival function of t-dist with n-1 dof (one-sided upper)
    return float(sp_stats.t.sf(t, df=n - 1))


def simulate_pair(df: pd.DataFrame, pair: str, sell_only: bool):
    """Single-open-position sequential bracket sim over the full history.
    Returns list of trade dicts. Entry TRIGGER = unchanged TrendlineSweep().evaluate."""
    symbol = SYMBOL[pair]
    strat = TrendlineSweep()

    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values
    opens = df["Open"].values
    adx = df["adx"].values
    hours = np.array([t.hour for t in df.index])
    weekday = np.array([t.weekday() for t in df.index])

    n = len(df)
    trades = []
    i = WINDOW
    end = n - MAX_HOLD - 1

    while i < end:
        h = int(hours[i])
        # cheap pre-filter matching the strategy's own gates (skip most bars)
        if h < strat.ACTIVE_HOURS_START or h >= strat.ACTIVE_HOURS_END:
            i += 1
            continue
        if weekday[i] == 4 and h >= strat.FRIDAY_BLOCK_HOUR:
            i += 1
            continue
        a = adx[i]
        if not (strat.ADX_MIN <= a <= strat.ADX_MAX):
            i += 1
            continue

        w = df.iloc[i - WINDOW + 1:i + 1]
        bar_time = df.index[i]
        ctx = SignalContext.from_df(
            w, w.iloc[-1], symbol, INTERVAL, [],
            {}, {}, {}, {}, {}, {}, {},
            backtest_mode=True, bar_time=bar_time,
        )
        cand = strat.evaluate(ctx)
        if cand is None:
            i += 1
            continue

        direction = cand.signal  # BUY / SELL
        if sell_only and pair in ("EUR_USD", "EUR_GBP") and direction == "BUY":
            # replicate production SELL_ONLY_PAIRS behaviour (unchanged strategy)
            i += 1
            continue

        entry = float(closes[i])
        sl = float(cand.sl)
        tp = float(cand.tp)
        is_buy = direction == "BUY"
        sl_dist = abs(entry - sl)
        tp_dist = abs(tp - entry)
        if sl_dist <= 0 or tp_dist <= 0:
            i += 1
            continue

        # simulate exit over the next MAX_HOLD bars (fixed bracket, SL-first tie)
        outcome = None
        exit_idx = None
        for j in range(i + 1, min(i + 1 + MAX_HOLD, n)):
            hi = highs[j]
            lo = lows[j]
            if is_buy:
                sl_hit = lo <= sl
                tp_hit = hi >= tp
            else:
                sl_hit = hi >= sl
                tp_hit = lo <= tp
            if sl_hit and tp_hit:
                outcome = "SL"  # conservative: assume SL touched first
                exit_idx = j
                break
            if sl_hit:
                outcome = "SL"
                exit_idx = j
                break
            if tp_hit:
                outcome = "TP"
                exit_idx = j
                break
        if outcome is None:
            # time-stop at close of last held bar
            exit_idx = min(i + MAX_HOLD, n - 1)
            outcome = "TIME"

        exit_hour = int(hours[exit_idx])
        friction_price = round_turn_friction_price(h, exit_hour, symbol)
        friction_pips = friction_price * PIP_MULT

        if outcome == "TP":
            gross_price = tp_dist
        elif outcome == "SL":
            gross_price = -sl_dist
        else:  # TIME: exit at close
            exit_close = float(closes[exit_idx])
            gross_price = (exit_close - entry) if is_buy else (entry - exit_close)
        gross_pips = gross_price * PIP_MULT
        net_pips = gross_pips - friction_pips

        trades.append({
            "pair": pair,
            "direction": direction,
            "entry_time": bar_time.isoformat(),
            "exit_time": df.index[exit_idx].isoformat(),
            "outcome": outcome,
            "gross_pips": round(gross_pips, 4),
            "friction_pips": round(friction_pips, 4),
            "net_pips": round(net_pips, 4),
            "tp_dist_pips": round(tp_dist * PIP_MULT, 4),
            "sl_dist_pips": round(sl_dist * PIP_MULT, 4),
        })

        # non-overlapping: resume scanning after the exit bar
        i = exit_idx + 1

    return trades


def wf_positive_folds(trades, window_start, window_end, k=4):
    """Split the FULL calendar window into k equal chronological folds; count
    folds whose net pip sum > 0. shadow N is NOT re-split (trades assigned by
    entry_time)."""
    if not trades:
        return 0, [0, 0, 0, 0]
    span = (window_end - window_start) / k
    fold_net = [0.0] * k
    fold_n = [0] * k
    for t in trades:
        et = datetime.fromisoformat(t["entry_time"])
        idx = int((et - window_start) / span)
        idx = max(0, min(k - 1, idx))
        fold_net[idx] += t["net_pips"]
        fold_n[idx] += 1
    positive = sum(1 for x in fold_net if x > 0)
    return positive, [round(x, 2) for x in fold_net], fold_n


def cell_metrics(trades):
    pnls = [t["net_pips"] for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    ev = sum(pnls) / n if n else 0.0
    pf = _pf(pnls)
    avg_tp = (sum(t["tp_dist_pips"] for t in trades) / n) if n else 0.0
    avg_fric = (sum(t["friction_pips"] for t in trades) / n) if n else 0.0
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n else 0.0,
        "netEV_pip": round(ev, 4),
        "netPnL_pip": round(sum(pnls), 2),
        "PF": (round(pf, 4) if math.isfinite(pf) else "inf"),
        "wilson_lo": round(_wilson_lower(wins, n), 4),
        "avg_tp_pip": round(avg_tp, 2),
        "avg_friction_pip": round(avg_fric, 3),
        "friction_pct_of_tp": round(avg_fric / avg_tp, 4) if avg_tp > 0 else None,
        "outcomes": {
            "TP": sum(1 for t in trades if t["outcome"] == "TP"),
            "SL": sum(1 for t in trades if t["outcome"] == "SL"),
            "TIME": sum(1 for t in trades if t["outcome"] == "TIME"),
        },
    }


def bh_fdr(pvals_by_pair: dict, q=FDR_Q):
    """Benjamini-Hochberg FDR at level q across the m pair-level tests."""
    items = [(pair, p) for pair, p in pvals_by_pair.items()]
    m = len(items)
    ordered = sorted(items, key=lambda x: x[1])
    survive = {pair: False for pair, _ in items}
    max_k = 0
    for k, (pair, p) in enumerate(ordered, start=1):
        if p <= (k / m) * q:
            max_k = k
    for k, (pair, p) in enumerate(ordered, start=1):
        if k <= max_k:
            survive[pair] = True
    return survive, {pair: round(p, 6) for pair, p in items}


def main() -> int:
    started = time.time()
    print("=" * 100)
    print("trendline_sweep 12y MASSIVE per-cell (pair x direction) walk-forward BT")
    print("Strategy UNCHANGED: strategies/daytrade/trendline_sweep.py | Data: MASSIVE parquet only")
    print("=" * 100, flush=True)

    loaded = {}
    data_windows = {}
    row_counts = {}
    for pair, rel in PAIRS.items():
        path = ROOT / rel
        if not path.exists():
            print(f"MISSING cache: {rel}")
            return 2
        raw = pd.read_parquet(path)
        raw_rows = len(raw)
        df = add_indicators(raw).dropna()
        loaded[pair] = df
        row_counts[pair] = {"raw_rows": raw_rows, "post_indicator_rows": len(df)}
        data_windows[pair] = {
            "cache_file": rel,
            "start": df.index[0].isoformat(),
            "end": df.index[-1].isoformat(),
        }
        print(f"[{pair}] {rel}  raw={raw_rows}  usable={len(df)}  "
              f"{df.index[0].date()} -> {df.index[-1].date()}", flush=True)

    # ── run both configs ──
    # CONFIG_RAW lifts the strategy's OWN internal SELL_ONLY_PAIRS filter at
    # RUNTIME ONLY (the file on disk is NOT modified) so the BUY leg of the
    # SELL-only pairs (EUR_USD, EUR_GBP) becomes observable for the G6
    # "no single-side artifact" diagnostic. CONFIG_PROD restores the unchanged
    # production filter.
    _ORIG_SELL_ONLY = TrendlineSweep.SELL_ONLY_PAIRS
    results = {"CONFIG_PROD": {}, "CONFIG_RAW": {}}
    raw_trades = {"CONFIG_PROD": {}, "CONFIG_RAW": {}}
    for cfg, sell_only in (("CONFIG_PROD", True), ("CONFIG_RAW", False)):
        if sell_only:
            TrendlineSweep.SELL_ONLY_PAIRS = _ORIG_SELL_ONLY
        else:
            TrendlineSweep.SELL_ONLY_PAIRS = frozenset()  # runtime diagnostic; file unchanged
        print(f"\n--- {cfg} (SELL_ONLY {'applied' if sell_only else 'lifted (runtime diag)'}) "
              f"[strategy.SELL_ONLY_PAIRS={sorted(TrendlineSweep.SELL_ONLY_PAIRS)}] ---", flush=True)
        for pair in PAIRS:
            t0 = time.time()
            trades = simulate_pair(loaded[pair], pair, sell_only=sell_only)
            raw_trades[cfg][pair] = trades
            nb = sum(1 for t in trades if t["direction"] == "BUY")
            ns = sum(1 for t in trades if t["direction"] == "SELL")
            print(f"  [{pair}] trades={len(trades)} (BUY {nb} / SELL {ns})  "
                  f"{time.time()-t0:.1f}s", flush=True)
    TrendlineSweep.SELL_ONLY_PAIRS = _ORIG_SELL_ONLY

    # ── per (pair x direction) metrics from CONFIG_RAW (all 6 cells populated) ──
    per_cell = {}
    for pair in PAIRS:
        for direction in ("BUY", "SELL"):
            tr = [t for t in raw_trades["CONFIG_RAW"][pair] if t["direction"] == direction]
            per_cell[f"{pair}_{direction}"] = cell_metrics(tr)

    # ── per (pair x direction) metrics from CONFIG_PROD (production-routed) ──
    per_cell_prod = {}
    for pair in PAIRS:
        for direction in ("BUY", "SELL"):
            tr = [t for t in raw_trades["CONFIG_PROD"][pair] if t["direction"] == direction]
            per_cell_prod[f"{pair}_{direction}"] = cell_metrics(tr)

    # ── pair-level metrics (CONFIG_PROD = actually-traded population) ──
    pair_prod = {}
    pvals = {}
    global_start = min(loaded[p].index[0].to_pydatetime() for p in PAIRS)
    global_end = max(loaded[p].index[-1].to_pydatetime() for p in PAIRS)
    for pair in PAIRS:
        tr = raw_trades["CONFIG_PROD"][pair]
        m = cell_metrics(tr)
        wf_start = loaded[pair].index[0].to_pydatetime()
        wf_end = loaded[pair].index[-1].to_pydatetime()
        pos_folds, fold_net, fold_n = wf_positive_folds(tr, wf_start, wf_end, k=4)
        m["wf_positive_folds"] = pos_folds
        m["wf_fold_net_pip"] = fold_net
        m["wf_fold_n"] = fold_n
        pair_prod[pair] = m
        pvals[pair] = _one_sided_p_gt0([t["net_pips"] for t in tr])

    survive, pvals_rounded = bh_fdr(pvals, q=FDR_Q)

    # ── both-legs net (G6) — from CONFIG_RAW so both legs always exist ──
    both_legs = {}
    for pair in PAIRS:
        buy = [t["net_pips"] for t in raw_trades["CONFIG_RAW"][pair] if t["direction"] == "BUY"]
        sell = [t["net_pips"] for t in raw_trades["CONFIG_RAW"][pair] if t["direction"] == "SELL"]
        both_legs[pair] = {
            "raw_BUY_net_pip": round(sum(buy), 2), "raw_BUY_N": len(buy),
            "raw_BUY_EV": round(sum(buy) / len(buy), 4) if buy else None,
            "raw_SELL_net_pip": round(sum(sell), 2), "raw_SELL_N": len(sell),
            "raw_SELL_EV": round(sum(sell) / len(sell), 4) if sell else None,
        }

    # ── gate evaluation (per pair, m=3) ──
    gates = {}
    for pair in PAIRS:
        m = pair_prod[pair]
        bl = both_legs[pair]
        g1 = m["netEV_pip"] > 0
        g2 = bool(survive[pair])
        g3 = m["wf_positive_folds"] >= 3
        g4 = m["wilson_lo"] >= WILSON_GATE
        fpt = m["friction_pct_of_tp"]
        g5 = (fpt is not None) and (fpt <= FRICTION_TP_GATE)
        # G6: no single-side artifact. Uses raw both-legs (SELL_ONLY lifted) so
        # the BUY leg exists even for production SELL-only pairs.
        buy_ok = (bl["raw_BUY_N"] == 0) or (bl["raw_BUY_net_pip"] >= 0)
        sell_ok = (bl["raw_SELL_N"] == 0) or (bl["raw_SELL_net_pip"] >= 0)
        g6 = buy_ok and sell_ok
        passes = g1 and g2 and g3 and g4 and g5 and g6
        gates[pair] = {
            "G1_netEV_gt0": g1,
            "G2_BHFDR_q10_survive": g2,
            "G3_WF_ge_3of4": g3,
            "G4_wilson_lo_ge_0.40": g4,
            "G5_friction_le_10pct_TP": g5,
            "G6_both_legs_net_ge0": g6,
            "PASSES_ALL": passes,
            "p_value_one_sided": pvals_rounded[pair],
        }

    elapsed = round(time.time() - started, 1)
    friction_assumption = {
        "model": "repo standard BT friction (app.py:_bt_spread + _bt_get_slippage), round-turn",
        "formula_price": "(spread(entry_hour) + spread(exit_hour))/2 + 2*slippage_per_side",
        "spread_model": "pair x hour base spread * friction_model_v2._SESSION_MULTIPLIER (verbatim from app.py:_bt_spread)",
        "slippage_per_side_pips": {"EUR_USD": 0.5, "GBP_USD": 1.0, "EUR_GBP": 0.5},
        "note": ("Round-turn = spread + 2x per-side slippage. GBP_USD round-turn (~2.7-2.8p) is "
                 "higher than the ~1.2-1.5p hint because the repo GBP_USD slippage is 1.0p/side "
                 "(friction-analysis.md nominal, the largest upward correction). EUR_USD ~1.2-1.3p, "
                 "EUR_GBP ~1.9-2.0p. This is the conservative production-faithful model; lighter "
                 "friction would only make netEV MORE positive."),
        "realized_avg_roundturn_pips_CONFIG_PROD": {
            pair: pair_prod[pair]["avg_friction_pip"] for pair in PAIRS
        },
    }

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "trendline_sweep",
        "strategy_file": "strategies/daytrade/trendline_sweep.py (UNCHANGED)",
        "test_type": "routing / pair-scope edge test (12y MASSIVE walk-forward, per cell = pair x direction)",
        "prereg_ledger_id": "trendline_sweep_gbpusd_pairscope_2026-07-13",
        "prereg_doc": "knowledge-base/wiki/learning/trendline-sweep-gbpusd-loss-conversion-prereg-2026-07-13.md",
        "interval": INTERVAL,
        "bt_mode": os.environ.get("BT_MODE"),
        "bt_require_massive_cache": os.environ.get("BT_REQUIRE_MASSIVE_CACHE"),
        "data_source": "MASSIVE parquet cache only (Yahoo forbidden)",
        "data_windows": data_windows,
        "row_counts": row_counts,
        "exit_model": {
            "type": "fixed bracket (SL/TP/time-stop), TV-aligned (fixed SL, no BE)",
            "max_hold_bars": MAX_HOLD,
            "tie_break": "SL-first (conservative) when SL and TP both touched in a bar",
            "position_model": "single open position per pair, non-overlapping trades",
            "ctx_window_bars": WINDOW,
            "window_equivalence_note": ("trendline_sweep only inspects the last ~100 bars for swings "
                                        "and the respect loop covers idx2+1..current; a 300-bar window "
                                        "yields IDENTICAL signals to production's 3500-bar window."),
        },
        "friction_assumption": friction_assumption,
        "gate_definitions": {
            "m_tests": 3,
            "G1": "netEV > 0 (post-friction, 12y)",
            "G2": "BH-FDR q=0.10 survive (m=3 pair-level tests, one-sided t-test mean>0)",
            "G3": "walk-forward >= 3/4 chronological folds net-positive",
            "G4": "Wilson_lo (95%) >= 0.40",
            "G5": "friction <= 10% of TP distance",
            "G6": "both-legs BUY net >= 0 AND SELL net >= 0 (no single-side artifact; evaluated on CONFIG_RAW)",
            "PASSES_ALL": "all of G1..G6",
            "eval_population": ("G1-G5 on CONFIG_PROD (unchanged strategy = actually-traded population); "
                                "G6 on CONFIG_RAW both legs (SELL_ONLY lifted at runtime, file unchanged)"),
        },
        "gates": gates,
        "bh_fdr": {"q": FDR_Q, "p_values": pvals_rounded, "survive": survive},
        "pair_level_CONFIG_PROD": pair_prod,
        "per_cell_CONFIG_PROD": per_cell_prod,
        "per_cell_CONFIG_RAW": per_cell,
        "both_legs_CONFIG_RAW": both_legs,
        "prereg_prediction": {
            "EUR_USD": "PASS", "GBP_USD": "FAIL", "EUR_GBP": "FAIL",
        },
        "elapsed_s": elapsed,
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── print tables ──
    def _fmt(v):
        return "inf" if v == "inf" else (f"{v:.3f}" if isinstance(v, float) else str(v))

    print("\n" + "=" * 108)
    print("PER-CELL (pair x direction) METRICS  [CONFIG_RAW: SELL_ONLY lifted, all 6 cells]")
    print("=" * 108)
    hdr = f"{'cell':<16}{'N':>6}{'WR':>8}{'netEV':>9}{'PF':>8}{'Wilson_lo':>11}{'fric/TP':>9}{'avgTP':>8}{'avgFric':>9}"
    print(hdr)
    print("-" * 108)
    for pair in PAIRS:
        for direction in ("BUY", "SELL"):
            c = per_cell[f"{pair}_{direction}"]
            fpt = c["friction_pct_of_tp"]
            print(f"{pair+'_'+direction:<16}{c['N']:>6}{c['WR']:>8.3f}{c['netEV_pip']:>9.3f}"
                  f"{_fmt(c['PF']):>8}{c['wilson_lo']:>11.3f}"
                  f"{(f'{fpt:.3f}' if fpt is not None else 'n/a'):>9}"
                  f"{c['avg_tp_pip']:>8.2f}{c['avg_friction_pip']:>9.3f}")

    print("\n" + "=" * 108)
    print("PER-CELL (pair x direction) METRICS  [CONFIG_PROD: unchanged strategy, SELL_ONLY applied]")
    print("=" * 108)
    print(hdr)
    print("-" * 108)
    for pair in PAIRS:
        for direction in ("BUY", "SELL"):
            c = per_cell_prod[f"{pair}_{direction}"]
            fpt = c["friction_pct_of_tp"]
            note = "  <- suppressed by SELL_ONLY" if (c["N"] == 0 and direction == "BUY" and pair in ("EUR_USD", "EUR_GBP")) else ""
            print(f"{pair+'_'+direction:<16}{c['N']:>6}{c['WR']:>8.3f}{c['netEV_pip']:>9.3f}"
                  f"{_fmt(c['PF']):>8}{c['wilson_lo']:>11.3f}"
                  f"{(f'{fpt:.3f}' if fpt is not None else 'n/a'):>9}"
                  f"{c['avg_tp_pip']:>8.2f}{c['avg_friction_pip']:>9.3f}{note}")

    print("\n" + "=" * 108)
    print("PAIR-LEVEL GATE TABLE  (m=3; G1-G5 on CONFIG_PROD, G6 on CONFIG_RAW both-legs)")
    print("=" * 108)
    print(f"{'pair':<10}{'N':>6}{'netEV':>9}{'WR':>7}{'Wilson_lo':>11}{'WF':>6}"
          f"{'fric/TP':>9}{'p_val':>9}  G1 G2 G3 G4 G5 G6  PASS")
    print("-" * 108)
    for pair in PAIRS:
        m = pair_prod[pair]
        g = gates[pair]
        def b(x):
            return " Y" if x else " ."
        fpt = m["friction_pct_of_tp"]
        print(f"{pair:<10}{m['N']:>6}{m['netEV_pip']:>9.3f}{m['WR']:>7.3f}{m['wilson_lo']:>11.3f}"
              f"{str(m['wf_positive_folds'])+'/4':>6}"
              f"{(f'{fpt:.3f}' if fpt is not None else 'n/a'):>9}{g['p_value_one_sided']:>9.4f} "
              f"{b(g['G1_netEV_gt0'])} {b(g['G2_BHFDR_q10_survive'])} {b(g['G3_WF_ge_3of4'])} "
              f"{b(g['G4_wilson_lo_ge_0.40'])} {b(g['G5_friction_le_10pct_TP'])} {b(g['G6_both_legs_net_ge0'])}"
              f"   {'PASS' if g['PASSES_ALL'] else 'FAIL'}")

    print("\nBoth-legs (CONFIG_RAW, for G6):")
    for pair in PAIRS:
        bl = both_legs[pair]
        print(f"  {pair}: BUY net={bl['raw_BUY_net_pip']} (N={bl['raw_BUY_N']}) | "
              f"SELL net={bl['raw_SELL_net_pip']} (N={bl['raw_SELL_N']})")

    print(f"\nBH-FDR q={FDR_Q}: p={pvals_rounded} survive={survive}")
    print(f"\nWF folds (CONFIG_PROD, net pip per fold):")
    for pair in PAIRS:
        print(f"  {pair}: {pair_prod[pair]['wf_fold_net_pip']} "
              f"(positive {pair_prod[pair]['wf_positive_folds']}/4, N/fold {pair_prod[pair]['wf_fold_n']})")

    passing = [p for p in PAIRS if gates[p]["PASSES_ALL"]]
    print(f"\nPASSING pairs (all G1..G6): {passing if passing else 'NONE'}")
    print(f"Pre-reg prediction: EUR_USD=PASS, GBP_USD=FAIL, EUR_GBP=FAIL")
    print(f"\nSaved: {OUTFILE}")
    print(f"Elapsed: {elapsed}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
