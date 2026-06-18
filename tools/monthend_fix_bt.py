#!/usr/bin/env python3
"""Backtest for the LOCKED month-end WMR fix pre-reg (H1 drift / H2 reversion).

Pre-reg: knowledge-base/wiki/decisions/monthend-fix-pre-reg-2026-06-18.md (LOCKED before this BT).
Data:    data/cache/research/monthend_fix/  (Phase 0, tools/monthend_fix_fetch.py)

Design (frozen by pre-reg — no tuning):
  - Signal rel = monthly_return(SX5E) - monthly_return(SPX), look-ahead-safe (only equity closes
    with date STRICTLY < entry date are used; baseline = last close of prior calendar month).
  - H1 drift:  rel>0 -> SHORT, rel<0 -> LONG. Entry 2nd-to-last BD @16:00 London close; exit last BD @16:00 London.
                TP=+0.6*ATR(20,D1), SL=-0.8*ATR(20,D1).
  - H2 revert: OPPOSITE sign. Entry last BD @16:00 London close; exit 1st BD next month @16:00 London.
                TP=+0.5*ATR(20,D1), SL=-0.7*ATR(20,D1).
  - 16:00 London is DST-aware (Europe/London -> UTC). Bars (MASSIVE/Polygon) stamped at bar START;
    bar close = stamp + 1h. Entry/exit bar = bar whose CLOSE is nearest 16:00 London on that date.
  - Intrabar SL-first; if both TP&SL touch in one bar -> SL. Else time-exit at exit-bar close.
  - Friction RT = 2.0 pip (EUR_USD, KB friction table) deducted per trade for NET.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "cache" / "research" / "monthend_fix"
OUT = ROOT / "knowledge-base" / "raw" / "bt-results"
OUT.mkdir(parents=True, exist_ok=True)

PIP = 0.0001
FRICTION_RT_PIP = 2.0
LONDON = ZoneInfo("Europe/London")
SEED = 42


def _load(name: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / name)
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


def london_1600_utc(date: pd.Timestamp) -> pd.Timestamp:
    """16:00 Europe/London on `date`, expressed in UTC (DST-aware)."""
    naive = pd.Timestamp(year=date.year, month=date.month, day=date.day, hour=16)
    return pd.Timestamp(naive.tz_localize(LONDON).tz_convert("UTC"))


def bar_nearest_fix(h1: pd.DataFrame, date, target_utc: pd.Timestamp):
    """Return (label, row) of the H1 bar whose CLOSE (stamp+1h) is nearest target_utc on `date`."""
    day = h1[(h1.index.date == date)]
    if day.empty:
        return None
    close_times = day.index + pd.Timedelta(hours=1)
    pos = int(np.argmin(np.abs((close_times - target_utc).total_seconds())))
    # require the nearest close to be within 3h of the fix (else the fix hour is missing for that day)
    if abs((close_times[pos] - target_utc).total_seconds()) > 3 * 3600:
        return None
    return day.index[pos], day.iloc[pos]


def atr20_d1(d1: pd.DataFrame, entry_date) -> float:
    """ATR(20) on D1 using only bars with date STRICTLY < entry_date (no look-ahead)."""
    prior = d1[d1.index.date < entry_date]
    if len(prior) < 21:
        return float("nan")
    h, l, c = prior["High"], prior["Low"], prior["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return float(tr.dropna().tail(20).mean())


def monthly_ret_before(idx_close: pd.Series, entry_date, prior_month_end_close: float) -> float:
    """ret = last close with date < entry_date  /  prior calendar month's last close - 1."""
    avail = idx_close[idx_close.index.date < entry_date]
    if avail.empty or not np.isfinite(prior_month_end_close) or prior_month_end_close == 0:
        return float("nan")
    return float(avail.iloc[-1] / prior_month_end_close - 1.0)


def month_end_close(idx_close: pd.Series, period) -> float:
    sub = idx_close[idx_close.index.to_period("M") == period]
    return float(sub.iloc[-1]) if len(sub) else float("nan")


def simulate(direction, entry_row, entry_label, exit_label, h1, atr, tp_mult, sl_mult):
    """Intrabar SL-first walk from bar AFTER entry through exit bar. Returns gross pips (signed)."""
    entry = float(entry_row["Close"])
    if direction == "LONG":
        tp, sl = entry + tp_mult * atr, entry - sl_mult * atr
        if not (tp > entry > sl):
            return None  # side-sanity gate
    else:
        tp, sl = entry - tp_mult * atr, entry + sl_mult * atr
        if not (sl > entry > tp):
            return None
    path = h1[(h1.index > entry_label) & (h1.index <= exit_label)]
    if path.empty:
        return None
    for _, bar in path.iterrows():
        hi, lo = float(bar["High"]), float(bar["Low"])
        if direction == "LONG":
            hit_sl, hit_tp = lo <= sl, hi >= tp
        else:
            hit_sl, hit_tp = hi >= sl, lo <= tp
        if hit_sl:  # SL-first (covers both-touch)
            exit_px = sl
            return (exit_px - entry) / PIP if direction == "LONG" else (entry - exit_px) / PIP
        if hit_tp:
            exit_px = tp
            return (exit_px - entry) / PIP if direction == "LONG" else (entry - exit_px) / PIP
    exit_px = float(path.iloc[-1]["Close"])  # time-exit
    return (exit_px - entry) / PIP if direction == "LONG" else (entry - exit_px) / PIP


def wilson_lo(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return float((c - m) / d)


def bootstrap_p(pnls: np.ndarray, n_boot: int = 10000) -> float:
    """One-sided p that mean net PnL <= 0, IID resample. seed=42."""
    rng = np.random.default_rng(SEED)
    n = len(pnls)
    if n == 0:
        return 1.0
    means = pnls[rng.integers(0, n, size=(n_boot, n))].mean(axis=1)
    return float((means <= 0).mean())


def bh_fdr(pvals: dict, q: float = 0.10) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    survive, thr = {}, {}
    for i, (k, p) in enumerate(items, start=1):
        thr[k] = q * i / m
    # BH: largest i with p_(i) <= q*i/m; all <= that rank survive
    passed = [i for i, (k, p) in enumerate(items, start=1) if p <= q * i / m]
    cutoff_rank = max(passed) if passed else 0
    for i, (k, p) in enumerate(items, start=1):
        survive[k] = i <= cutoff_rank
    return {k: {"p": pvals[k], "bh_threshold": round(thr[k], 4), "survive": survive[k]} for k in pvals}


def run():
    h1 = _load("EUR_USD_1h_12y.parquet")
    d1 = _load("EUR_USD_1d_12y.parquet")
    spx = _load("GSPC_1d.parquet")["Close"]
    sx5e = _load("STOXX50E_1d.parquet")["Close"]

    # Business days = WEEKDAYS only. FX H1 data includes Sunday-evening session
    # bars (22:00-23:00 UTC, the Monday-week open) stamped on a Sunday date; those
    # are NOT business days and must not be selectable as the month's 1st/last BD
    # (the locked spec says "business day"). Sat/Sun dates are excluded here; the
    # intrabar path still uses every real H1 bar.
    dates = pd.Series([d for d in sorted(set(h1.index.date)) if d.weekday() < 5])
    by_month: dict = {}
    for dte in dates:
        by_month.setdefault((dte.year, dte.month), []).append(dte)
    months = sorted(by_month.keys())

    trades_h1, trades_h2 = [], []
    for i in range(1, len(months) - 1):  # need prior month (signal) and next month (H2 exit)
        ym = months[i]
        prev_ym = months[i - 1]
        next_ym = months[i + 1]
        mdays = by_month[ym]
        if len(mdays) < 2:
            continue
        last_bd = mdays[-1]
        second_last_bd = mdays[-2]
        next_first_bd = by_month[next_ym][0]
        prev_period = pd.Period(year=prev_ym[0], month=prev_ym[1], freq="M")

        # ---- signal (look-ahead-safe): rel as-of the EARLIEST entry (2nd-to-last BD) ----
        spx_base = month_end_close(spx, prev_period)
        sx5e_base = month_end_close(sx5e, prev_period)
        spx_ret = monthly_ret_before(spx, second_last_bd, spx_base)
        sx5e_ret = monthly_ret_before(sx5e, second_last_bd, sx5e_base)
        if not (np.isfinite(spx_ret) and np.isfinite(sx5e_ret)):
            continue
        rel = sx5e_ret - spx_ret
        if rel == 0:
            continue

        # ===== H1 drift: rel>0 SHORT, rel<0 LONG ; entry 2nd-last BD, exit last BD =====
        d1_dir = "SHORT" if rel > 0 else "LONG"
        atr_h1 = atr20_d1(d1, second_last_bd)
        e1 = bar_nearest_fix(h1, second_last_bd, london_1600_utc(pd.Timestamp(second_last_bd)))
        x1 = bar_nearest_fix(h1, last_bd, london_1600_utc(pd.Timestamp(last_bd)))
        if e1 and x1 and np.isfinite(atr_h1):
            g = simulate(d1_dir, e1[1], e1[0], x1[0], h1, atr_h1, 0.6, 0.8)
            if g is not None:
                trades_h1.append({"date": str(second_last_bd), "year": second_last_bd.year,
                                  "dir": d1_dir, "rel": rel, "atr_pip": atr_h1 / PIP,
                                  "gross": g, "net": g - FRICTION_RT_PIP})

        # ===== H2 reversion: OPPOSITE ; entry last BD, exit 1st BD next month =====
        d2_dir = "LONG" if rel > 0 else "SHORT"
        atr_h2 = atr20_d1(d1, last_bd)
        e2 = bar_nearest_fix(h1, last_bd, london_1600_utc(pd.Timestamp(last_bd)))
        x2 = bar_nearest_fix(h1, next_first_bd, london_1600_utc(pd.Timestamp(next_first_bd)))
        if e2 and x2 and np.isfinite(atr_h2):
            g = simulate(d2_dir, e2[1], e2[0], x2[0], h1, atr_h2, 0.5, 0.7)
            if g is not None:
                trades_h2.append({"date": str(last_bd), "year": last_bd.year,
                                  "dir": d2_dir, "rel": rel, "atr_pip": atr_h2 / PIP,
                                  "gross": g, "net": g - FRICTION_RT_PIP})

    result = {"H1_monthend_fix_drift": summarize(trades_h1),
              "H2_monthend_fix_reversion": summarize(trades_h2)}

    # BH-FDR across the m=2 campaign (one-sided bootstrap p on NET)
    pvals = {"H1": result["H1_monthend_fix_drift"]["bootstrap_p_net"],
             "H2": result["H2_monthend_fix_reversion"]["bootstrap_p_net"]}
    result["BH_FDR_m2_q0.10"] = bh_fdr(pvals, q=0.10)
    result["meta"] = {"friction_rt_pip": FRICTION_RT_PIP, "seed": SEED,
                      "h1_window": [str(dates.iloc[0]), str(dates.iloc[-1])],
                      "n_months": len(months)}

    (OUT / "monthend_fix_2026_06_18.json").write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result, indent=2, default=str))


def summarize(trades: list) -> dict:
    if not trades:
        return {"N": 0}
    df = pd.DataFrame(trades)
    net = df["net"].to_numpy()
    n = len(df)
    wins = int((net > 0).sum())
    # walk-forward: 4 equal time-folds by chronological order
    folds = np.array_split(np.arange(n), 4)
    fold_net = [float(net[f].sum()) if len(f) else 0.0 for f in folds]
    wf_pos = int(sum(1 for x in fold_net if x > 0))
    # per-year & drop-one-year robustness
    per_year = df.groupby("year")["net"].sum().round(2).to_dict()
    total = float(net.sum())
    drop_one = {int(y): round(total - v, 2) for y, v in per_year.items()}
    # signed legs
    long_net = float(df[df["dir"] == "LONG"]["net"].sum())
    short_net = float(df[df["dir"] == "SHORT"]["net"].sum())
    return {
        "N": n,
        "WR": round(wins / n, 4),
        "wins": wins,
        "wilson_lo_WR": round(wilson_lo(wins, n), 4),
        "mean_net_pip": round(float(net.mean()), 3),
        "total_net_pip": round(total, 2),
        "total_gross_pip": round(float(df["gross"].sum()), 2),
        "mean_atr_pip": round(float(df["atr_pip"].mean()), 1),
        "bootstrap_p_net": round(bootstrap_p(net), 4),
        "wf_fold_net": [round(x, 2) for x in fold_net],
        "wf_pos_folds": wf_pos,
        "long_net_pip": round(long_net, 2),
        "short_net_pip": round(short_net, 2),
        "long_n": int((df["dir"] == "LONG").sum()),
        "short_n": int((df["dir"] == "SHORT").sum()),
        "per_year_net": per_year,
        "drop_one_year_total": drop_one,
        "both_legs_net_pos": bool(long_net > 0 and short_net > 0),
    }


if __name__ == "__main__":
    run()
