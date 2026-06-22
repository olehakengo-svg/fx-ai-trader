#!/usr/bin/env python3
"""Backtest — LOCKED pre-reg `wick_imbalance_continuation_gbpusd` (GBP_USD H1, 12y MASSIVE).

Pre-reg (LOCKED, commit before BT):
  knowledge-base/wiki/decisions/wick-imbalance-gbpusd-continuation-pre-reg-2026-06-22.md
  agents/cma/prereg_ledger.jsonl  id=wick_imbalance_gbpusd_continuation_2026-06-22
Forensic + frozen spec:
  data/cache/research/wick_imb_gbpusd/hypothesis.md

WHAT THIS IS: convert the losing E10 (wick_imbalance_reversion x GBP_USD) by adding ONE binary
DoF — a closed-bar D1 trend gate — turning a counter-trend knife-catch into a with-trend
CONTINUATION entry. TP is frozen FLAT at 2.5xATR (drops the |WIR|-scaled TP DoF). Nothing else
about the trigger changes.

TRIGGER — reuses the PRODUCTION WIR logic (NOT a re-derivation):
  strategies.daytrade.alpha_wick_imbalance.WickImbalanceReversion.evaluate() is called per bar
  with REDESIGN_V2 closed-bar convention (env WICK_IMBALANCE_REVERSION_REDESIGN_V2=1):
    - WIR over df.iloc[-10:-2] (window=8), threshold=0.45
    - confirm bar = df.iloc[-2] (last CLOSED bar)
    - filters kept: |confirm_body| >= 0.05*ATR  AND  bb_width_pct >= 0.15
  evaluate() returns BUY when WIR<-0.45 & confirm_body>0 ; SELL when WIR>+0.45 & confirm_body<0.

DIRECTION (the ONLY change vs the existing strategy) — with-trend continuation gated by d1_label:
  LONG  = (production BUY trigger)  AND d1_label in {+1,+2}  -> BUY  at next H1 open
  SHORT = (production SELL trigger) AND d1_label in {-1,-2}  -> SELL at next H1 open
  NO-TRADE if d1_label in {0,3}, |WIR|<0.45, or |confirm_body|<0.05*ATR.

EXITS (frozen): SL = 1.5*ATR14(H1), TP = 2.5*ATR14(H1) FLAT. RR=1.67, breakeven WR=37.5%. pip=0.0001.
d1_label: PRODUCTION labeler research/edge_discovery/mtf_regime_engine.py::label_d1, on the PRIOR
  COMPLETED GBP_USD daily bar (causal — no look-ahead).
ATR14(H1): production add_indicators ATR14 (ta Wilder), read at the confirm bar (causal closed-bar).
Fill: intrabar SL-first (conservative). TP/SL side-sanity gate logged if it ever fires.

FAITHFUL-IMPLEMENTATION NOTES (spec was silent -> documented, not silently changed):
  [N1] entry = next H1 open (open[c+1]); the production evaluate()'s own SL/TP (derived from
       ctx.entry=Close) are DISCARDED — only its BUY/SELL/None trigger decision is used. SL/TP are
       re-applied per the frozen 1.5/2.5 ATR spec off the real entry (next H1 open).
  [N2] ctx.atr passed to evaluate() and used for SL/TP sizing = ATR14 at the CONFIRM bar c (last
       closed bar) = causal. Production live reads ctx.atr from the forming bar (df.iloc[-1]); using
       the forming bar here would be a 1-bar look-ahead, which the pre-reg ("causal, no look-ahead")
       forbids. Difference is one bar's TR contribution (negligible).
  [N3] ctx.bb_width_pct = fraction of the trailing 50 bars ENDING AT the confirm bar c whose bb_width
       < bb_width[c] (production from_df semantics, ended at the closed bar for causality).
  [N4] Position model = sequential, one-position-at-a-time (house convention, tools/ob_retest_h1...).
       While a trade is open, new triggers are skipped. This is realistic AND keeps the trade sample
       closer to IID for the bootstrap. The spec is silent on overlap; documented here.
  [N5] No artificial time-stop DoF (the frozen spec gives none). Walk to SL/TP; the single trade
       still open at end-of-data is time-exited at the last close. Hold-bar distribution recorded.
  [N6] WR for the G4/breakeven comparison is GROSS win rate (win=gross_pips>0), matching the gross
       RR-derived breakeven 37.5%. Net WR also reported.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# REDESIGN_V2 closed-bar convention MUST be enabled before importing/strategy use.
os.environ.setdefault("WICK_IMBALANCE_REVERSION_REDESIGN_V2", "1")

from modules.indicators import add_indicators  # noqa: E402
from strategies.context import SignalContext  # noqa: E402
from strategies.daytrade.alpha_wick_imbalance import WickImbalanceReversion  # noqa: E402
from research.edge_discovery.mtf_regime_engine import label_d1, MTFConfig  # noqa: E402

PIP = 0.0001
FRICTION_RT_PIP = 1.8          # task-specified round-trip friction
SL_MULT = 1.5
TP_MULT = 2.5                  # FROZEN FLAT (no |WIR| scaling)
WINDOW = 8
THRESHOLD = 0.45
SEED = 42

H1_PATH = ROOT / "data" / "cache" / "massive" / "GBP_USD_1h_12y_massive.parquet"
D1_PATH = ROOT / "data" / "cache" / "massive" / "GBP_USD_1d_12y_massive.parquet"
OUT = ROOT / "raw" / "bt-results"
OUT.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT / "wick_imb_continuation_gbpusd_2026_06_22.json"


# ──────────────────────────────────────────────────────────────────────────
# Data load
# ──────────────────────────────────────────────────────────────────────────
def _load(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


# ──────────────────────────────────────────────────────────────────────────
# Stats helpers (shared conventions with tools/monthend_fix_bt.py)
# ──────────────────────────────────────────────────────────────────────────
def wilson_lo(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return float((c - m) / d)


def bootstrap_p(pnls: np.ndarray, n_boot: int = 10000) -> float:
    """One-sided p that mean net PnL <= 0 (IID resample, fixed seed=42)."""
    rng = np.random.default_rng(SEED)
    n = len(pnls)
    if n == 0:
        return 1.0
    means = pnls[rng.integers(0, n, size=(n_boot, n))].mean(axis=1)
    return float((means <= 0).mean())


def bh_fdr(pvals: dict, q: float = 0.10) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    thr = {k: q * i / m for i, (k, p) in enumerate(items, start=1)}
    passed = [i for i, (k, p) in enumerate(items, start=1) if p <= q * i / m]
    cutoff_rank = max(passed) if passed else 0
    rank = {k: i for i, (k, p) in enumerate(items, start=1)}
    return {k: {"p": round(pvals[k], 6), "bh_threshold": round(thr[k], 4),
                "survive": rank[k] <= cutoff_rank} for k in pvals}


# ──────────────────────────────────────────────────────────────────────────
# d1_label causal lookup (prior completed daily bar)
# ──────────────────────────────────────────────────────────────────────────
def build_d1_lookup(d1: pd.DataFrame):
    """Return (sorted np.array of daily python-dates, np.array of int labels)."""
    inp = d1.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
    labels = label_d1(inp, MTFConfig())  # Series indexed by daily ts
    dates = np.array([ts.date() for ts in labels.index])
    vals = labels.to_numpy().astype(int)
    order = np.argsort(dates)
    return dates[order], vals[order]


def d1_label_for(entry_date, d1_dates, d1_vals) -> int:
    """Label of the most-recent daily bar with date STRICTLY < entry_date (causal).

    Mirrors demo_trader's label_d1(...).iloc[-2] convention: the daily bar covering
    the entry's own day is still forming, so we use the last fully-closed daily bar.
    Returns 3 (insufficient-data sentinel) if no prior daily bar exists.
    """
    pos = int(np.searchsorted(d1_dates, entry_date, side="left"))
    if pos <= 0:
        return 3
    return int(d1_vals[pos - 1])


# ──────────────────────────────────────────────────────────────────────────
# Core BT
# ──────────────────────────────────────────────────────────────────────────
def run():
    h1_raw = _load(H1_PATH)
    d1 = _load(D1_PATH)
    h1 = add_indicators(h1_raw.copy())  # production indicators (atr14, bb_width, ...)

    d1_dates, d1_vals = build_d1_lookup(d1)

    strat = WickImbalanceReversion()

    ohlc = h1[["Open", "High", "Low", "Close"]]
    open_arr = h1["Open"].to_numpy()
    high_arr = h1["High"].to_numpy()
    low_arr = h1["Low"].to_numpy()
    close_arr = h1["Close"].to_numpy()
    atr_arr = h1["atr"].to_numpy()
    bw_arr = h1["bb_width"].to_numpy()
    idx = h1.index
    n = len(h1)

    trades = []
    side_sanity_fires = 0
    exit_reasons = {"SL": 0, "TP": 0, "TIME_EOD": 0}

    c = WINDOW + 2  # earliest confirm bar with a full WIR window
    while c < n - 1:
        atr_c = float(atr_arr[c])
        if not np.isfinite(atr_c) or atr_c <= 0:
            c += 1
            continue

        # bb_width_pct over trailing 50 ending at confirm bar c (causal)
        lo50 = max(0, c - 49)
        seg = bw_arr[lo50:c + 1]
        bbp = float((seg < bw_arr[c]).sum()) / 50.0

        df_win = ohlc.iloc[c - WINDOW: c + 2]   # 10 rows: df.iloc[-2]=bar c, [-10:-2]=c-8..c-1
        entry_px = float(open_arr[c + 1])       # entry = next H1 open (faithful note N1)
        ctx = SignalContext(df=df_win, atr=atr_c, bb_width_pct=bbp, entry=entry_px)

        cand = strat.evaluate(ctx)              # PRODUCTION trigger (N1)
        if cand is None:
            c += 1
            continue

        # ---- D1 trend gate + with-trend continuation direction mapping ----
        entry_ts = idx[c + 1]
        d1lab = d1_label_for(entry_ts.date(), d1_dates, d1_vals)
        if cand.signal == "BUY":
            if d1lab not in (1, 2):
                c += 1
                continue
            direction = "LONG"
        elif cand.signal == "SELL":
            if d1lab not in (-1, -2):
                c += 1
                continue
            direction = "SHORT"
        else:
            c += 1
            continue

        # ---- frozen SL/TP off real entry; side-sanity gate ----
        if direction == "LONG":
            sl = entry_px - SL_MULT * atr_c
            tp = entry_px + TP_MULT * atr_c
            if not (tp > entry_px > sl):
                side_sanity_fires += 1
                c += 1
                continue
        else:
            sl = entry_px + SL_MULT * atr_c
            tp = entry_px - TP_MULT * atr_c
            if not (sl > entry_px > tp):
                side_sanity_fires += 1
                c += 1
                continue

        # ---- intrabar SL-first walk from entry bar c+1 (inclusive) ----
        exit_px = None
        exit_reason = None
        exit_pos = n - 1
        for j in range(c + 1, n):
            hi, loo = float(high_arr[j]), float(low_arr[j])
            if direction == "LONG":
                hit_sl, hit_tp = loo <= sl, hi >= tp
            else:
                hit_sl, hit_tp = hi >= sl, loo <= tp
            if hit_sl:          # SL-first (covers both-touch within a bar)
                exit_px, exit_reason, exit_pos = sl, "SL", j
                break
            if hit_tp:
                exit_px, exit_reason, exit_pos = tp, "TP", j
                break
        if exit_px is None:     # never resolved -> time-exit at last close (N5)
            exit_px, exit_reason, exit_pos = float(close_arr[n - 1]), "TIME_EOD", n - 1

        exit_reasons[exit_reason] += 1
        if direction == "LONG":
            gross = (exit_px - entry_px) / PIP
        else:
            gross = (entry_px - exit_px) / PIP
        net = gross - FRICTION_RT_PIP

        trades.append({
            "entry_time": entry_ts.isoformat(),
            "exit_time": idx[exit_pos].isoformat(),
            "year": int(entry_ts.year),
            "dir": direction,
            "d1_label": d1lab,
            "wir_signal": cand.signal,
            "entry": round(entry_px, 6),
            "sl": round(sl, 6),
            "tp": round(tp, 6),
            "exit": round(exit_px, 6),
            "exit_reason": exit_reason,
            "atr_pip": round(atr_c / PIP, 3),
            "tp_pip": round(TP_MULT * atr_c / PIP, 3),
            "hold_bars": int(exit_pos - (c + 1) + 1),
            "gross": round(gross, 4),
            "net": round(net, 4),
        })

        c = exit_pos  # sequential, no overlap (N4): next confirm = exit bar (closed)

    # ── data window actually used ──
    data_window = {
        "h1_raw_rows": int(len(h1_raw)),
        "h1_indicator_rows": int(n),
        "h1_start": idx[0].isoformat(),
        "h1_end": idx[-1].isoformat(),
        "d1_rows": int(len(d1)),
        "d1_start": d1.index[0].isoformat(),
        "d1_end": d1.index[-1].isoformat(),
    }

    df_all = pd.DataFrame(trades)
    legs = {
        "COMBINED": df_all,
        "LONG": df_all[df_all["dir"] == "LONG"] if len(df_all) else df_all,
        "SHORT": df_all[df_all["dir"] == "SHORT"] if len(df_all) else df_all,
    }

    # walk-forward: 4 CONTIGUOUS equal-time folds over the H1 data window
    wf_edges = pd.date_range(idx[0], idx[-1], periods=5)

    summaries = {k: summarize(v, wf_edges) for k, v in legs.items()}

    pvals = {
        "LONG": summaries["LONG"].get("bootstrap_p_net", 1.0),
        "SHORT": summaries["SHORT"].get("bootstrap_p_net", 1.0),
    }
    bh = bh_fdr(pvals, q=0.10)

    # friction as % of TP (G5)
    if len(df_all):
        med_atr = float(df_all["atr_pip"].median())
        mean_atr = float(df_all["atr_pip"].mean())
    else:
        med_atr = mean_atr = float("nan")
    friction_pct_of_tp = {
        "median_atr_pip": round(med_atr, 2),
        "mean_atr_pip": round(mean_atr, 2),
        "tp_pip_at_median_atr": round(TP_MULT * med_atr, 2),
        "friction_pct_of_tp_median": round(100 * FRICTION_RT_PIP / (TP_MULT * med_atr), 3) if med_atr else None,
        "friction_pct_of_tp_mean": round(100 * FRICTION_RT_PIP / (TP_MULT * mean_atr), 3) if mean_atr else None,
    }

    result = {
        "strategy_id": "wick_imbalance_continuation_gbpusd",
        "pair": "GBP_USD",
        "tf": "H1",
        "prereg_id": "wick_imbalance_gbpusd_continuation_2026-06-22",
        "prereg_doc": "knowledge-base/wiki/decisions/wick-imbalance-gbpusd-continuation-pre-reg-2026-06-22.md",
        "meta": {
            "friction_rt_pip": FRICTION_RT_PIP,
            "sl_mult": SL_MULT, "tp_mult": TP_MULT, "tp_frozen_flat": True,
            "window": WINDOW, "threshold": THRESHOLD,
            "seed": SEED, "n_bootstrap": 10000,
            "redesign_v2": True,
            "fill": "intrabar SL-first; sequential one-position-at-a-time",
            "wr_basis_for_gates": "gross (win=gross_pips>0)",
            "wf_fold_edges": [str(t) for t in wf_edges],
        },
        "data_window": data_window,
        "side_sanity_gate_fires": side_sanity_fires,
        "exit_reason_counts": exit_reasons,
        "legs": summaries,
        "BH_FDR_m2_q0.10": bh,
        "friction_g5": friction_pct_of_tp,
        "trades": trades,
    }

    OUT_FILE.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result, indent=2, default=str))
    return result


def summarize(df: pd.DataFrame, wf_edges) -> dict:
    if df is None or len(df) == 0:
        return {"N": 0}
    net = df["net"].to_numpy()
    gross = df["gross"].to_numpy()
    n = len(df)
    wins_gross = int((gross > 0).sum())
    wins_net = int((net > 0).sum())

    # walk-forward: contiguous time folds
    et = pd.to_datetime(df["entry_time"], utc=True)
    fold_net, fold_n = [], []
    for i in range(4):
        lo, hi = wf_edges[i], wf_edges[i + 1]
        if i < 3:
            mask = (et >= lo) & (et < hi)
        else:
            mask = (et >= lo) & (et <= hi)
        fold_net.append(round(float(df.loc[mask.values, "net"].sum()), 2))
        fold_n.append(int(mask.sum()))
    wf_pos = int(sum(1 for x in fold_net if x > 0))

    per_year = {int(y): round(float(v), 2) for y, v in df.groupby("year")["net"].sum().items()}
    total_net = float(net.sum())
    drop_one = {int(y): round(total_net - v, 2) for y, v in per_year.items()}
    per_year_n = {int(y): int(v) for y, v in df.groupby("year").size().items()}

    long_net = float(df[df["dir"] == "LONG"]["net"].sum())
    short_net = float(df[df["dir"] == "SHORT"]["net"].sum())

    return {
        "N": n,
        "WR_gross": round(wins_gross / n, 4),
        "WR_net": round(wins_net / n, 4),
        "wins_gross": wins_gross,
        "wilson_lo_WR_gross": round(wilson_lo(wins_gross, n), 4),
        "mean_net_pip": round(float(net.mean()), 4),
        "mean_gross_pip": round(float(gross.mean()), 4),
        "total_net_pip": round(total_net, 2),
        "total_gross_pip": round(float(gross.sum()), 2),
        "median_atr_pip": round(float(df["atr_pip"].median()), 2),
        "mean_hold_bars": round(float(df["hold_bars"].mean()), 1),
        "bootstrap_p_net": round(bootstrap_p(net), 6),
        "wf_fold_net": fold_net,
        "wf_fold_n": fold_n,
        "wf_pos_folds": wf_pos,
        "long_n": int((df["dir"] == "LONG").sum()),
        "short_n": int((df["dir"] == "SHORT").sum()),
        "long_net_pip": round(long_net, 2),
        "short_net_pip": round(short_net, 2),
        "both_legs_net_pos": bool(long_net > 0 and short_net > 0),
        "per_year_net": per_year,
        "per_year_n": per_year_n,
        "drop_one_year_total_net": drop_one,
    }


if __name__ == "__main__":
    run()
