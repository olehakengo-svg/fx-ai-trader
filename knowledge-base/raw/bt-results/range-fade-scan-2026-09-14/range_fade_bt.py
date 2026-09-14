#!/usr/bin/env python3
"""
range_fade_bt.py — Range-boundary resting-limit fade BT harness
(spec: range_boundary_limit_fade_v1_prereg, declared 2026-09-14, frozen grid K=32)

Usage:
    python3 range_fade_bt.py --pair USD_JPY --spec range_fade_spec.json --out results_USD_JPY.json
    python3 range_fade_bt.py --pair USD_JPY --spec ... --out ... --smoke   # last 60 days of spec window

================================================================================
ADVERSARIAL-REVIEW FIXES (2026-09-14) — all applied in this version
================================================================================
[C1] Entry-bar TP look-ahead FIXED: on the entry bar (k == t) TP is no longer
     judged on the full-bar High/Low (the extreme may pre-date the intra-bar
     limit fill). TP on the entry bar now requires a provably post-fill
     crossing: buy TP iff Close[t] >= tp_price; sell TP iff Close[t] <= tp_price.
     Proof: the fill occurs at the first strict boundary penetration; for a buy
     the sub-boundary Low is necessarily post-fill and Close comes after the
     Low, so Close >= tp_price implies a post-fill upward crossing of tp_price.
     SL on the entry bar keeps the full-bar extreme (the SL level lies beyond
     the entry boundary, reachable only after passing the boundary = after the
     fill; provably post-fill). Bars k > t: full-bar checks, SL first.
[M2] Both-side same-bar penetration: the skip is now conditioned on BOTH sides
     being ARMED (only then do two resting orders coexist and the first-fill
     order is path-ambiguous). If exactly one side is armed, that side's order
     is the only order in the market and MUST fill -> the trade is taken
     (previously dropped: look-ahead selection). Unarmed-both events place no
     orders (no ambiguity, no event). Diagnostics now report the three counts,
     the ambiguous-skip ratio vs fills, and per-event counterfactual PnL of
     both hypothetical fills under the same SL-first engine (spec-level live-
     divergence caveat material for any PASS).
[M3/M6] BT window is PINNED to spec['bt_windows'][pair] (start_utc/end_utc).
     The harness hard-fails unless df.index[-1] == end_utc EXACTLY (tolerance
     0) — a cache refresh can no longer silently slide the pre-reg window.
     --smoke uses [end_utc - 60d, end_utc], still tail-asserted. Warm-up
     coverage (window start - 120d) is also asserted. Data freeze: the pair
     parquet's sha256 is computed every run; it is verified against a freeze
     manifest JSON next to the spec (created on first run per pair, hard fail
     on any later mismatch), and recorded in meta.
[M4] p_boot resolution: default --iters raised 500 -> 10000
     (min achievable p = 1/(iters+1); with 10000 -> 9.999e-5 < alpha
     0.0015625). meta now records min_achievable_p and machine-readable flags:
     p_boot is NEVER the spec gate statistic (different null), and the spec's
     recentered stationary block bootstrap (mean block 10, 10k iters, H0 mean
     0, dependence preserved) is now IMPLEMENTED here as p_block per cell.
[M5] Random-entry null redesigned: null trades no longer clone each real
     trade's realized hold_bars as their time stop (that shrank null per-trade
     variance -> anti-conservative p). Null trades now run the SAME exit
     policy as the strategy: same TP/SL distances, per-bar SL-first scan,
     time stop = the cell's time_stop_bars (48); hold is endogenous.

================================================================================
FILL MODEL
================================================================================
Data: data/cache/massive/{PAIR}_15m.parquet, UTC DatetimeIndex.
  Only Open/High/Low/Close are read (pd.read_parquet(columns=[...])).
  Volume/vwap are NEVER loaded into the BT frame (E12 volume forward pre-reg
  LOCK, first look 2027-02-05; E1 positioning LOCK: price-only features).

Range (per cell lookback lb in {96,192} bars):
  range_high[t] = max(High[t-lb .. t-1])   (current bar t EXCLUDED)
  range_low[t]  = min(Low [t-lb .. t-1])   (current bar t EXCLUDED)
  W = range_high - range_low.
  All boundary values for bar t are fixed by data through bar t-1 => the resting
  limit order priced off them contains no look-ahead. Orders are live for bar t
  only; boundaries refresh every bar.

Boundary age arming (sides armed independently):
  A side is armed at bar t iff the bar that set the extreme is >= 16 bars (4h)
  before t. If the extreme value occurs on multiple bars in the window, the
  MOST RECENT occurrence is used (conservative: youngest possible age).
  An UNARMED side places NO order.

Eligibility at bar t (all computed from data available at t-1 close /
prior-UTC-day close — no look-ahead):
  - W >= min_width_pips (per-pair 20x RT floor, from spec)
  - W <= max_width_atr_d1_mult x ATR_D1(14), Wilder (prior-day value)
  - regime 'lowvol' cells only: prior-day ATR_D1(14) strictly below the median
    of the trailing 30 D1 ATR observations (ending that same prior day)
  - 1 position per cell: while a position is open no new entries in that cell;
    next entry is allowed from the bar AFTER the exit bar.

Entry (resting limit AT the boundary, fade direction, NO confirmation):
  BUY : limit at range_low;  fills iff Low[t]  <  range_low STRICTLY
        (penetration); entry price = range_low exactly.
  SELL: limit at range_high; fills iff High[t] >  range_high STRICTLY;
        entry price = range_high exactly.
  No slippage credit or debit.
  BOTH boundaries penetrated on the same bar:
    - both sides ARMED  -> two resting orders coexist, first fill is path-
      ambiguous -> NO entry (spec-declared skip), event logged with
      counterfactual PnL of both hypothetical fills (SL-first engine).
    - exactly ONE side armed -> only one order exists, no ambiguity -> that
      side FILLS and is a normal trade (fix M2; the old code dropped it).
    - NEITHER side armed -> no orders, nothing happens (counted separately).
  Buy and sell are POOLED within a cell; per-side counts are diagnostics only.

Exit (frozen at entry; BE/trail FORBIDDEN per project ablation +20pp WR bias):
  exit_key 'midasym': TP = entry -/+ 0.50*W toward range interior (range mid),
                      SL = 0.35*W beyond the boundary (outside the range).
  exit_key 'sym1r'  : TP = 0.50*W interior, SL = 0.50*W outside.
  Evaluation starts ON the entry bar but is restricted to provably POST-FILL
  information (fix C1):
    entry bar t : SL on full-bar extreme (provably post-fill);
                  TP only iff Close[t] reaches tp_price (provably post-fill);
                  SL checked BEFORE TP (conservative).
    bars k > t  : full-bar High/Low, SL checked BEFORE TP.
  Time stop: if neither level is hit by bar t+48 (48 bars = 12h after entry),
  exit at Close[t+48]. If the data series ends first, exit at the last
  available Close (reason 'data_end').
  hold_bars = exit_bar_index - entry_bar_index (same-bar exit => 0).

Friction: full declared RT pips deducted from EVERY trade
  (USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 / EUR_JPY 2.50;
   pip = 0.01 JPY crosses, 0.0001 otherwise; values taken from the spec cells).
  net_pips = direction * (exit_price - entry_price) / pip_size - rt_pips.

BT window (fix M3/M6): win_start/win_end are read from spec['bt_windows'][pair]
(start_utc/end_utc), NEVER derived from the parquet tail. Hard asserts before
any simulation: (1) parquet tail == end_utc exactly; (2) parquet head covers
win_start - 120 calendar days (feature warm-up). --smoke restricts the entry
window to [end_utc - smoke_days, end_utc] (still spec-pinned + tail-asserted;
recorded in meta). sha256 of the parquet is verified against the freeze
manifest (see above) and recorded in meta.

================================================================================
STATISTICS (per cell)
================================================================================
n           : number of filled trades (sides pooled).
wr          : share of trades with net_pips > 0 (friction-adjusted; ties=loss).
ev_pips     : mean net_pips per trade (friction-adjusted EV).
total_pips  : sum of net_pips.
wilson_lo   : Wilson score lower bound (z=1.95996) on the net win rate.
p_boot      : DIAGNOSTIC random-entry null, one-sided p on the mean.
              iters (default 10000) iterations; each iteration re-simulates the
              SAME NUMBER of trades, where synthetic trade i copies actual
              trade i's direction and TP/SL DISTANCES, enters AT MARKET (bar
              Open) on a bar drawn uniformly at random from the BT window
              (constrained so the full time-stop horizon fits in the data),
              and runs the SAME EXIT POLICY as the strategy (per-bar SL-first,
              time stop = cell time_stop_bars; hold ENDOGENOUS — fix M5).
              Full-bar H/L checks are valid on the null entry bar because the
              market fill at Open precedes the bar's extremes.
              p = (1 + #{null mean >= observed mean}) / (iters + 1).
              p_boot is NOT the spec gate statistic (different null); the
              machine-readable meta flags say so (fix M4).
p_block     : SPEC GATE statistic (fix M4) — recentered stationary block
              bootstrap on the cell's net per-trade PnL sequence (trade order
              preserved), mean block length 10 trades, 10,000 iterations,
              one-sided: p = (1 + #{bootstrap mean of the recentered (H0:
              mean 0, dependence preserved) series >= observed mean})
              / (iters + 1). Pass gate: p_block < alpha = 0.05/32 = 0.0015625
              (gate applied downstream with min_n/EV/walk-forward jointly).
wf_signs    : walk-forward 3-fold — the spec window is split into 3 equal
              contiguous time segments; trades assigned by entry timestamp;
              per fold the SIGN of net total pips (+1/-1; 0 if no trades).
              Fold trade counts are in diagnostics (spec gate treats folds
              with <5 trades as non-agreeing; applied downstream).
median_hold_bars : median of hold_bars over the cell's trades.
diagnostics.both_pen : ambiguous_skipped / one_armed_filled / unarmed counts,
              ambiguous skip ratio vs fills, and per-event counterfactual
              net pips (both hypothetical fills, SL-first engine) for the
              skipped ambiguous events — REQUIRED caveat material for any
              PASS on cells where the ratio is non-trivial (fix M2).

RNG: numpy default_rng seeded from --seed (default 20260914) xor a stable
per-cell hash, with separate ":null" / ":block" sub-streams so each statistic
is reproducible independently of execution order and of the other statistic.

Curve-fitting discipline: the grid is read from the frozen spec; this script
adds no cells, changes no parameters, and applies no post-hoc slicing.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

Z95 = 1.959963984540054

EXIT_PARAMS = {
    # exit_key -> (tp_mult_of_W_toward_interior, sl_mult_of_W_outside)
    "midasym": (0.50, 0.35),
    "sym1r": (0.50, 0.50),
}


# ----------------------------------------------------------------------------
# data / features
# ----------------------------------------------------------------------------

def load_bars(path):
    """Read OHLC only. Volume/vwap are never loaded (E12 LOCK)."""
    df = pd.read_parquet(path, columns=["Open", "High", "Low", "Close"])
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_freeze(manifest_path, pair, data_path):
    """Freeze-manifest sha256 check (fix M3/M6, spec hard_precondition #3).

    - manifest exists & has pair -> sha must match EXACTLY else hard fail.
    - manifest exists, pair missing -> add entry (first run for pair).
    - manifest missing -> create it with this pair (freeze-on-first-run).
    Returns (sha, status_string)."""
    sha = file_sha256(data_path)
    manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        want = manifest.get(pair, {}).get("sha256")
        if want is not None:
            if want != sha:
                sys.exit(
                    f"FATAL [freeze]: sha256 mismatch for {pair}: manifest "
                    f"{want} != file {sha} ({data_path}). Frozen cache has "
                    f"drifted — NO refetch/backfill without a separate freeze "
                    f"+ audit (MASSIVE vendor drift lesson 2026-07-29).")
            return sha, "verified"
        status = "created_entry"
    else:
        status = "created_manifest"
    manifest[pair] = {"sha256": sha, "path": data_path,
                      "frozen_at": datetime.now(timezone.utc).isoformat()}
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    return sha, status


def rolling_boundaries(df, lb):
    """range_high/low over [t-lb, t-1] plus most-recent-extreme offset o
    (o >= 15 <=> setter bar >= 16 bars before t). Returns dict of np arrays."""
    high = df["High"]
    low = df["Low"]

    def last_max_offset(a):
        return float(np.argmax(a[::-1]))

    def last_min_offset(a):
        return float(np.argmin(a[::-1]))

    rmax = high.rolling(lb).max().shift(1)
    rmin = low.rolling(lb).min().shift(1)
    o_hi = high.rolling(lb).apply(last_max_offset, raw=True).shift(1)
    o_lo = low.rolling(lb).apply(last_min_offset, raw=True).shift(1)
    return {
        "range_high": rmax.to_numpy(),
        "range_low": rmin.to_numpy(),
        "off_high": o_hi.to_numpy(),
        "off_low": o_lo.to_numpy(),
    }


def daily_atr_features(df):
    """ATR_D1(14, Wilder) prior-day value and lowvol flag per 15m bar.

    D1 = UTC-day resample of the same 15m source, empty days dropped. For a
    bar on day d:
      atr_prior[bar]  = ATR through day d-1 (prior available D1 row)
      lowvol[bar]     = ATR[d-1] < median(ATR[d-30 .. d-1])  (strict, 30 obs)
    Both are NaN/False when history is insufficient (bar then ineligible).
    """
    d1 = pd.DataFrame({
        "High": df["High"].resample("1D").max(),
        "Low": df["Low"].resample("1D").min(),
        "Close": df["Close"].resample("1D").last(),
    }).dropna()
    prev_close = d1["Close"].shift(1)
    tr = pd.concat([
        d1["High"] - d1["Low"],
        (d1["High"] - prev_close).abs(),
        (d1["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / 14.0, adjust=False, min_periods=14).mean()

    atr_v = atr.to_numpy()
    n = len(atr_v)
    med30 = np.full(n, np.nan)
    for i in range(29, n):
        w = atr_v[i - 29:i + 1]
        if not np.isnan(w).any():
            med30[i] = np.median(w)
    lowvol_d1 = (atr_v < med30) & ~np.isnan(med30) & ~np.isnan(atr_v)

    day_idx = d1.index.to_numpy()  # normalized UTC midnights
    bar_days = df.index.normalize().to_numpy()
    pos = np.searchsorted(day_idx, bar_days, side="right") - 1
    prior = pos - 1
    atr_prior = np.full(len(df), np.nan)
    lowvol = np.zeros(len(df), dtype=bool)
    ok = prior >= 0
    atr_prior[ok] = atr_v[prior[ok]]
    lowvol[ok] = lowvol_d1[prior[ok]]
    return atr_prior, lowvol


# ----------------------------------------------------------------------------
# simulation
# ----------------------------------------------------------------------------

def simulate_exit(H, L, C, t, direction, tp_price, sl_price, time_stop):
    """Per-bar SL-first exit scan from entry bar t through t+time_stop.

    Entry bar (k == t) — LIMIT fill happens intra-bar at the first boundary
    penetration, so the bar's extremes are NOT all post-fill (fix C1):
      * SL: full-bar extreme allowed — the SL level lies beyond the entry
        boundary and can only be reached after passing the boundary
        (= after the fill). Provably post-fill.
      * TP: judged on Close[t] ONLY — buy: Close[t] >= tp_price proves a
        post-fill upward crossing (the sub-boundary Low is necessarily
        post-fill, Close comes after the Low); the bar High alone may
        pre-date the fill and is never used on the entry bar. Sell symmetric.
      * SL is checked before TP (conservative same-bar rule).
    Bars k > t are entirely post-fill: full-bar High/Low checks, SL first.
    Returns (exit_pos, exit_price, reason)."""
    last = len(C) - 1
    end = min(t + time_stop, last)
    for k in range(t, end + 1):
        if direction > 0:
            if L[k] <= sl_price:
                return k, sl_price, "SL"
            if k == t:
                if C[k] >= tp_price:
                    return k, tp_price, "TP"
            elif H[k] >= tp_price:
                return k, tp_price, "TP"
        else:
            if H[k] >= sl_price:
                return k, sl_price, "SL"
            if k == t:
                if C[k] <= tp_price:
                    return k, tp_price, "TP"
            elif L[k] <= tp_price:
                return k, tp_price, "TP"
    if end == t + time_stop:
        return end, C[end], "TIME"
    return end, C[end], "data_end"


def run_cell(df, feats, atr_prior, lowvol, cell, win_mask, pip, rt):
    """Event loop over the BT window for one cell. Returns (trades, diags)."""
    H = df["High"].to_numpy()
    L = df["Low"].to_numpy()
    C = df["Close"].to_numpy()
    rh = feats["range_high"]
    rl = feats["range_low"]
    off_hi = feats["off_high"]
    off_lo = feats["off_low"]

    tp_mult, sl_mult = EXIT_PARAMS[cell["exit_key"]]
    time_stop = int(cell["exit"]["time_stop_bars"])
    age_min = int(cell["eligibility"]["boundary_age_min_bars"])  # 16
    min_w_price = float(cell["eligibility"]["min_width_pips"]) * pip
    max_mult = float(cell["eligibility"]["max_width_atr_d1_mult"])
    is_lowvol_cell = cell["regime"] == "lowvol"

    positions = np.flatnonzero(win_mask)
    trades = []
    both_pen_ambiguous = 0     # both sides armed -> two orders, path ambiguous
    both_pen_one_armed = 0     # one order only -> filled (fix M2)
    both_pen_unarmed = 0       # no orders -> non-event
    cf_buy = []                # counterfactual net pips of skipped ambiguous
    cf_sell = []               # events (SL-first engine, both sides)
    pos_until = -1

    for t in positions:
        if t <= pos_until:
            continue
        b_rh = rh[t]
        b_rl = rl[t]
        if np.isnan(b_rh) or np.isnan(b_rl):
            continue
        W = b_rh - b_rl
        a = atr_prior[t]
        if np.isnan(a):
            continue
        if W < min_w_price or W > max_mult * a:
            continue
        if is_lowvol_cell and not lowvol[t]:
            continue

        # arming FIRST (fix M2): an unarmed side has NO resting order, so its
        # penetration creates no ambiguity and can never cancel the other
        # side's fill. offset o >= age_min-1 <=> setter >= age_min bars before t
        armed_low = off_lo[t] >= age_min - 1
        armed_high = off_hi[t] >= age_min - 1
        pen_low = L[t] < b_rl
        pen_high = H[t] > b_rh

        if pen_low and pen_high:
            if armed_low and armed_high:
                # two resting orders coexist; which fills first is intra-bar
                # path ambiguous -> spec-declared skip, logged with
                # counterfactual PnL of both hypothetical fills (diagnostics
                # only; live-divergence caveat for PASS judgment).
                both_pen_ambiguous += 1
                for d, entry_cf in ((1, b_rl), (-1, b_rh)):
                    tp_cf = entry_cf + d * tp_mult * W
                    sl_cf = entry_cf - d * sl_mult * W
                    _, px_cf, _ = simulate_exit(
                        H, L, C, t, d, tp_cf, sl_cf, time_stop)
                    net_cf = d * (px_cf - entry_cf) / pip - rt
                    (cf_buy if d > 0 else cf_sell).append(float(net_cf))
                continue
            if not armed_low and not armed_high:
                both_pen_unarmed += 1
                continue
            both_pen_one_armed += 1
            # exactly one order rests -> unambiguous fill; fall through

        if pen_low and armed_low:
            direction = 1
            entry = b_rl
            tp_price = entry + tp_mult * W
            sl_price = entry - sl_mult * W
        elif pen_high and armed_high:
            direction = -1
            entry = b_rh
            tp_price = entry - tp_mult * W
            sl_price = entry + sl_mult * W
        else:
            continue

        exit_pos, exit_price, reason = simulate_exit(
            H, L, C, t, direction, tp_price, sl_price, time_stop)
        net = direction * (exit_price - entry) / pip - rt
        trades.append({
            "entry_pos": int(t),
            "entry_time": df.index[t].isoformat(),
            "direction": direction,
            "entry": float(entry),
            "tp_dist": float(abs(tp_price - entry)),
            "sl_dist": float(abs(sl_price - entry)),
            "exit_pos": int(exit_pos),
            "exit_price": float(exit_price),
            "reason": reason,
            "hold_bars": int(exit_pos - t),
            "net_pips": float(net),
        })
        pos_until = exit_pos  # next entry allowed from exit bar + 1

    n_tr = len(trades)
    denom = n_tr + both_pen_ambiguous
    diags = {
        "both_pen": {
            "ambiguous_skipped": int(both_pen_ambiguous),
            "one_armed_filled": int(both_pen_one_armed),
            "unarmed_no_orders": int(both_pen_unarmed),
            "ambiguous_skip_ratio_vs_fills": (
                float(both_pen_ambiguous / denom) if denom else None),
            "counterfactual_sl_first": {
                "note": "per skipped ambiguous event: both hypothetical fills"
                        " simulated independently under the same SL-first"
                        " engine (entry-bar TP close-proof incl.), full RT"
                        " deducted; diagnostics only — spec-level live"
                        " divergence caveat, required in any PASS writeup",
                "buy_net_pips": [round(v, 3) for v in cf_buy],
                "sell_net_pips": [round(v, 3) for v in cf_sell],
                "buy_total": round(float(sum(cf_buy)), 3),
                "sell_total": round(float(sum(cf_sell)), 3),
                "worst_case_total": round(float(sum(
                    min(b, s) for b, s in zip(cf_buy, cf_sell))), 3),
            },
        },
        "n_buy": int(sum(1 for x in trades if x["direction"] > 0)),
        "n_sell": int(sum(1 for x in trades if x["direction"] < 0)),
        "exit_reasons": {
            r: int(sum(1 for x in trades if x["reason"] == r))
            for r in ("TP", "SL", "TIME", "data_end")
        },
    }
    return trades, diags


# ----------------------------------------------------------------------------
# statistics
# ----------------------------------------------------------------------------

def wilson_lower(wins, n, z=Z95):
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2 * n)
    rad = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return float((center - rad) / denom)


def null_bootstrap_p(df, trades, win_mask, pip, rt, time_stop, iters, rng):
    """DIAGNOSTIC random-entry null, one-sided p on the mean (fix M5 design).

    Per iteration, one synthetic trade per actual trade — same direction and
    TP/SL distances, market entry at bar Open on a uniform random window bar
    (constrained so the full time-stop horizon fits in the data), run under
    the SAME EXIT POLICY as the strategy: per-bar SL-first scan with time
    stop = the cell's time_stop_bars; hold is ENDOGENOUS. Full RT deducted.

    Fix M5 rationale: the previous design cloned each real trade's realized
    hold_bars as the null's time stop; real TP/SL exits carry large |PnL|
    (0.35-0.5W) while short-horizon null clones mostly time-exit near -RT,
    so null per-trade variance was systematically too small and the null
    mean distribution over-tight around -RT -> anti-conservative p.

    Full-bar H/L checks on the null ENTRY bar are legitimate here because the
    market fill at Open precedes the bar's extremes (unlike the strategy's
    intra-bar limit fill).

    p = (1 + #{null mean >= observed mean}) / (iters + 1), one-sided.
    NOT the spec gate statistic (see p_block)."""
    if not trades:
        return None
    O = df["Open"].to_numpy()
    H = df["High"].to_numpy()
    L = df["Low"].to_numpy()
    C = df["Close"].to_numpy()
    last = len(C) - 1
    win_pos = np.flatnonzero(win_mask)
    elig = win_pos[win_pos + time_stop <= last]
    if len(elig) == 0:
        return None
    obs_mean = float(np.mean([x["net_pips"] for x in trades]))

    tot = np.zeros(iters)
    for x in trades:  # vectorized over iterations per actual trade
        d = x["direction"]
        starts = elig[rng.integers(0, len(elig), size=iters)]
        entry = O[starts]
        if d > 0:
            tp = entry + x["tp_dist"]
            sl = entry - x["sl_dist"]
        else:
            tp = entry - x["tp_dist"]
            sl = entry + x["sl_dist"]
        price = np.full(iters, np.nan)
        alive = np.ones(iters, dtype=bool)
        for k in range(time_stop + 1):
            if not alive.any():
                break
            Hk = H[starts + k]
            Lk = L[starts + k]
            if d > 0:
                hit_sl = alive & (Lk <= sl)
                price[hit_sl] = sl[hit_sl]
                alive &= ~hit_sl
                hit_tp = alive & (Hk >= tp)
                price[hit_tp] = tp[hit_tp]
                alive &= ~hit_tp
            else:
                hit_sl = alive & (Hk >= sl)
                price[hit_sl] = sl[hit_sl]
                alive &= ~hit_sl
                hit_tp = alive & (Lk <= tp)
                price[hit_tp] = tp[hit_tp]
                alive &= ~hit_tp
        if alive.any():
            price[alive] = C[starts[alive] + time_stop]  # time-stop exit
        tot += d * (price - entry) / pip - rt
    null_means = tot / len(trades)
    p = (1.0 + float(np.sum(null_means >= obs_mean))) / (iters + 1.0)
    return float(p)


def stationary_block_bootstrap_p(nets, iters, mean_block, rng):
    """SPEC GATE statistic (fix M4): recentered stationary block bootstrap
    (Politis-Romano) on the cell's net per-trade PnL sequence, trade order
    preserved, mean block length `mean_block`, circular continuation.
    The series is recentered (x - mean) so H0: mean 0 holds while the
    dependence structure is preserved; one-sided
    p = (1 + #{bootstrap mean of recentered series >= observed mean})
        / (iters + 1)."""
    n = len(nets)
    if n == 0:
        return None
    x = np.asarray(nets, dtype=float)
    obs = float(x.mean())
    xc = x - obs  # H0 recentering
    idx = np.empty((iters, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, size=iters)
    if n > 1:
        restart = rng.random((iters, n - 1)) < (1.0 / mean_block)
        newstart = rng.integers(0, n, size=(iters, n - 1))
        for j in range(1, n):
            cont = (idx[:, j - 1] + 1) % n
            idx[:, j] = np.where(restart[:, j - 1], newstart[:, j - 1], cont)
    boot_means = xc[idx].mean(axis=1)
    p = (1.0 + float(np.sum(boot_means >= obs))) / (iters + 1.0)
    return float(p)


def walk_forward_signs(trades, win_start, win_end):
    """3 equal contiguous time folds; sign of net total pips per fold."""
    span = (win_end - win_start) / 3
    edges = [win_start + span, win_start + 2 * span]
    totals = [0.0, 0.0, 0.0]
    counts = [0, 0, 0]
    for x in trades:
        ts = pd.Timestamp(x["entry_time"])
        f = 0 if ts < edges[0] else (1 if ts < edges[1] else 2)
        totals[f] += x["net_pips"]
        counts[f] += 1
    signs = [(1 if v > 0 else (-1 if v < 0 else 0)) if c > 0 else 0
             for v, c in zip(totals, counts)]
    return signs, counts, totals


def cell_seed(base_seed, key):
    h = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    return (base_seed ^ h) & 0x7FFFFFFF


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--pair", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-root", default="/Users/jg-n-012/test/fx-ai-trader/data/cache/massive")
    ap.add_argument("--smoke", action="store_true",
                    help="smoke test: last 60 days of the SPEC window only")
    ap.add_argument("--smoke-days", type=int, default=60)
    ap.add_argument("--iters", type=int, default=10000,
                    help="random-entry null iterations (fix M4: default 10000;"
                         " min achievable p = 1/(iters+1))")
    ap.add_argument("--block-iters", type=int, default=10000,
                    help="recentered stationary block bootstrap iterations"
                         " (spec gate: 10000)")
    ap.add_argument("--mean-block", type=int, default=10,
                    help="mean block length in trades (spec gate: 10)")
    ap.add_argument("--freeze-manifest", default=None,
                    help="sha256 freeze manifest JSON; default:"
                         " <spec dir>/range_fade_freeze_manifest.json")
    ap.add_argument("--seed", type=int, default=20260914)
    args = ap.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)

    cells = [c for c in spec["cells"] if c["pair"] == args.pair]
    if not cells:
        sys.exit(f"no cells for pair {args.pair} in spec")

    # ---- window pinning + data-freeze hard preconditions (fix M3/M6) ----
    bw = spec.get("bt_windows", {}).get(args.pair)
    if not bw:
        sys.exit(f"FATAL: spec has no bt_windows entry for {args.pair}")
    spec_start = pd.Timestamp(bw["start_utc"])
    spec_end = pd.Timestamp(bw["end_utc"])

    data_path = f"{args.data_root}/{args.pair}_15m.parquet"
    manifest_path = args.freeze_manifest or os.path.join(
        os.path.dirname(os.path.abspath(args.spec)),
        "range_fade_freeze_manifest.json")
    data_sha, freeze_status = verify_freeze(manifest_path, args.pair, data_path)

    df_full = load_bars(data_path)
    tail = df_full.index[-1]
    if tail != spec_end:
        sys.exit(
            f"FATAL: parquet tail {tail.isoformat()} != spec bt_windows"
            f" end_utc {spec_end.isoformat()} for {args.pair} (tolerance 0)."
            f" The frozen cache has drifted or been refreshed — the pre-reg"
            f" window may no longer be reproducible. NO refetch; re-freeze +"
            f" audit required before any run.")

    if args.smoke:
        win_end = spec_end
        win_start = spec_end - pd.Timedelta(days=args.smoke_days)
        window_source = (f"spec bt_windows end_utc - {args.smoke_days}d"
                         f" (smoke; tail-asserted == end_utc)")
    else:
        win_start = spec_start
        win_end = spec_end
        window_source = "spec bt_windows (pinned; tail-asserted == end_utc)"

    warmup_start = win_start - pd.Timedelta(days=120)
    if df_full.index[0] > warmup_start:
        sys.exit(
            f"FATAL: parquet head {df_full.index[0].isoformat()} does not"
            f" cover feature warm-up start {warmup_start.isoformat()}")

    df = df_full.loc[warmup_start:].copy()
    win_mask = (df.index >= win_start) & (df.index <= win_end)

    # gate alpha for machine-readable resolution flags (fix M4)
    try:
        gate_alpha = float(spec["gates"]["primary"]["null_bootstrap"]["alpha"])
    except (KeyError, TypeError, ValueError):
        gate_alpha = 0.05 / 32
    min_p_boot = 1.0 / (args.iters + 1)
    min_p_block = 1.0 / (args.block_iters + 1)

    atr_prior, lowvol = daily_atr_features(df)
    feat_cache = {}
    for lb in sorted({c["lookback_bars"] for c in cells}):
        feat_cache[lb] = rolling_boundaries(df, lb)

    out_cells = []
    for cell in cells:
        pip = float(cell["friction"]["pip_size"])
        rt = float(cell["friction"]["rt_pips"])
        time_stop = int(cell["exit"]["time_stop_bars"])
        trades, diags = run_cell(
            df, feat_cache[cell["lookback_bars"]], atr_prior, lowvol,
            cell, win_mask, pip, rt)

        n = len(trades)
        nets = np.array([x["net_pips"] for x in trades]) if n else np.array([])
        wins = int(np.sum(nets > 0)) if n else 0
        wr = float(wins / n) if n else None
        ev = float(nets.mean()) if n else None
        total = float(nets.sum()) if n else 0.0
        wl = wilson_lower(wins, n) if n else None
        rng_null = np.random.default_rng(
            cell_seed(args.seed, cell["cell_id"] + ":null"))
        rng_block = np.random.default_rng(
            cell_seed(args.seed, cell["cell_id"] + ":block"))
        p_boot = null_bootstrap_p(df, trades, win_mask, pip, rt, time_stop,
                                  args.iters, rng_null) if n else None
        p_block = stationary_block_bootstrap_p(
            nets, args.block_iters, args.mean_block, rng_block) if n else None
        wf_signs, wf_counts, wf_totals = walk_forward_signs(
            trades, win_start, win_end)
        med_hold = float(np.median([x["hold_bars"] for x in trades])) if n else None

        diags["wf_fold_n"] = wf_counts
        diags["wf_fold_total_pips"] = [round(v, 3) for v in wf_totals]

        out_cells.append({
            "cell_id": cell["cell_id"],
            "n": n,
            "wr": wr,
            "ev_pips": ev,
            "total_pips": total,
            "wilson_lo": wl,
            "p_boot": p_boot,
            "p_block": p_block,
            "wf_signs": wf_signs,
            "median_hold_bars": med_hold,
            "params": {
                "lookback_bars": cell["lookback_bars"],
                "regime": cell["regime"],
                "exit_key": cell["exit_key"],
                "tp_mult_W": EXIT_PARAMS[cell["exit_key"]][0],
                "sl_mult_W": EXIT_PARAMS[cell["exit_key"]][1],
                "time_stop_bars": time_stop,
                "boundary_age_min_bars": cell["eligibility"]["boundary_age_min_bars"],
                "min_width_pips": cell["eligibility"]["min_width_pips"],
                "max_width_atr_d1_mult": cell["eligibility"]["max_width_atr_d1_mult"],
                "rt_pips": rt,
                "pip_size": pip,
            },
            "diagnostics": diags,
        })

    result = {
        "pair": args.pair,
        "window": {"start": win_start.isoformat(), "end": win_end.isoformat()},
        "cells": out_cells,
        "meta": {
            "spec_name": spec.get("spec_name"),
            "smoke": bool(args.smoke),
            "window_source": window_source,
            "spec_bt_window": {"start_utc": bw["start_utc"],
                               "end_utc": bw["end_utc"]},
            "parquet_tail_assert": "passed (== spec end_utc, tolerance 0)",
            "data_sha256": data_sha,
            "freeze_manifest": manifest_path,
            "freeze_status": freeze_status,
            "boot_iters": args.iters,
            "block_boot_iters": args.block_iters,
            "mean_block_len": args.mean_block,
            "seed": args.seed,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "bonferroni_alpha": gate_alpha,
            "min_achievable_p_boot": min_p_boot,
            "min_achievable_p_block": min_p_block,
            "p_boot_is_spec_gate_statistic": False,
            "p_boot_usable_for_bonferroni_gate": False,
            "p_boot_resolution_ok_for_alpha": bool(min_p_boot < gate_alpha),
            "p_block_is_spec_gate_statistic": True,
            "p_block_usable_for_bonferroni_gate": bool(
                min_p_block < gate_alpha),
            "p_boot_definition": "random-entry null (market fill at Open,"
                                 " uniform random window bar; same direction"
                                 " + TP/SL distances as each actual trade;"
                                 " SAME exit policy: per-bar SL-first,"
                                 " time stop = cell time_stop_bars, hold"
                                 " endogenous — fix M5), one-sided, add-one"
                                 " smoothed. DIAGNOSTIC ONLY — never the"
                                 " Bonferroni gate statistic.",
            "p_block_definition": "recentered stationary block bootstrap on"
                                  " the cell's net per-trade PnL sequence"
                                  " (order preserved), mean block length"
                                  f" {args.mean_block} trades,"
                                  f" {args.block_iters} iters, one-sided,"
                                  " add-one smoothed; H0 = mean 0 with"
                                  " dependence preserved (spec gate"
                                  " statistic).",
            "entry_bar_tp_rule": "entry bar TP requires post-fill proof via"
                                 " Close (buy: Close>=tp; sell: Close<=tp);"
                                 " full-bar High/Low never used for TP on the"
                                 " entry bar; SL full-bar (provably"
                                 " post-fill); SL before TP (fix C1).",
            "both_pen_policy": "skip only when BOTH sides armed (two resting"
                               " orders, path ambiguous; spec-declared);"
                               " one-armed side fills normally (fix M2);"
                               " counterfactual SL-first PnL of skipped"
                               " events in diagnostics.",
        },
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=1)

    for c in out_cells:
        bp = c["diagnostics"]["both_pen"]
        print(f"{c['cell_id']:36s} n={c['n']:4d} "
              f"wr={c['wr'] if c['wr'] is None else round(c['wr'], 3)} "
              f"ev={c['ev_pips'] if c['ev_pips'] is None else round(c['ev_pips'], 2)} "
              f"tot={round(c['total_pips'], 1)} "
              f"wilson_lo={c['wilson_lo'] if c['wilson_lo'] is None else round(c['wilson_lo'], 3)} "
              f"p_boot={c['p_boot']} p_block={c['p_block']} "
              f"wf={c['wf_signs']} hold={c['median_hold_bars']} "
              f"both_pen[amb/1armed/un]={bp['ambiguous_skipped']}/"
              f"{bp['one_armed_filled']}/{bp['unarmed_no_orders']}")
    print(f"written: {args.out}")


if __name__ == "__main__":
    main()
