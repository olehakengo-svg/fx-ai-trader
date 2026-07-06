"""Kalman D7 v18e JPY Cross-Pair BT (Claude in-session port from Pine v6).

Source of truth: /Users/jg-n-012/test/kalman_d7_strategies/v18e_05ATR_trail.pine

Run from fx-ai-trader root:
    python3 tools/kalman_d7_v18e_jpy_cross_bt.py
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

JPY_MINTICK = 0.001


# ============================================================================
# v18e Pine port
# ============================================================================

@dataclass
class Trade:
    entry_idx: int
    entry_time: pd.Timestamp
    entry_px: float
    exit_idx: int
    exit_time: pd.Timestamp
    exit_px: float
    pnl_pct: float  # P&L as % of equity at entry
    exit_reason: str  # "trail" | "stop_loss"


def ema(series: pd.Series, length: int) -> pd.Series:
    """Pine ta.ema() — exponential moving average with alpha=2/(N+1)."""
    return series.ewm(span=length, adjust=False).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Pine ta.atr() — RMA of true range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    # Pine RMA = Wilder's smoothing = ewm with alpha=1/N
    return tr.ewm(alpha=1.0 / length, adjust=False).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """Pine ta.rsi() — Wilder's smoothing."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0 / length, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1.0 / length, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def rolling_percentile(series: pd.Series, window: int, q: float) -> pd.Series:
    """Pine ta.percentile_linear_interpolation(src, length, q)."""
    return series.rolling(window=window, min_periods=window).quantile(q / 100.0)


def backtest_v18e(df: pd.DataFrame,
                  sl_atr_mul: float = 2.0,
                  trail_act_mul: float = 1.0,
                  trail_off_mul: float = 0.5,
                  commission_pct: float = 0.002,  # one-way percent of trade value
                  slippage_ticks: int = 1,
                  mintick: float = JPY_MINTICK,
                  initial_capital: float = 100_000.0,
                  qty_pct: float = 10.0,  # % of equity per trade
                  exit_mode: str = "next_open",
                  ) -> dict:
    """Run v18e backtest on a DataFrame with columns Open/High/Low/Close.

    Pine logic match:
    - Entry: PO-UP transition + 5 filter (DIST<3, GAP<3, ATR_Q P20-P80, RSI<70, sess)
    - Exit: 0.5*ATR trail (activate @ +1*ATR) OR dynamic SL = entry - 2.0*current ATR
    - process_orders_on_close = True: exit stop detection uses bar close, with default
      fills on next bar open to match the closest TV benchmark variant found here.
    """
    # Ensure UTC datetime index
    if df.index.tz is None:
        df = df.copy()
        df.index = df.index.tz_localize('UTC')

    close = df['Close']
    high = df['High']
    low = df['Low']

    ema_fast = ema(close, 25)
    ema_mid = ema(close, 75)
    ema_slow = ema(close, 200)
    atr_val = atr(high, low, close, 14)
    rsi_val = rsi(close, 14)

    perfect_up = ((ema_fast > ema_mid) & (ema_mid > ema_slow) & (close > ema_fast)).astype(bool)
    perfect_up_prev = perfect_up.shift(1, fill_value=False).astype(bool)
    po_up_start = perfect_up & ~perfect_up_prev

    dist_atr = (close - ema_slow) / atr_val
    gap_atr = (ema_fast - ema_slow) / atr_val

    atr_p20 = rolling_percentile(atr_val, 200, 20)
    atr_p80 = rolling_percentile(atr_val, 200, 80)
    atr_ok = (atr_val >= atr_p20) & (atr_val < atr_p80)

    hour_utc = df.index.hour
    sess_ok = ((hour_utc < 7) | ((hour_utc >= 7) & (hour_utc < 12)) | ((hour_utc >= 16) & (hour_utc < 21)))
    sess_ok = pd.Series(sess_ok, index=df.index)

    entry_signal = (po_up_start
                    & (dist_atr < 3.0)
                    & (gap_atr < 3.0)
                    & atr_ok
                    & (rsi_val < 70)
                    & sess_ok)

    valid_exit_modes = {"intrabar", "close_only", "next_open", "conservative_intrabar"}
    if exit_mode not in valid_exit_modes:
        raise ValueError(f"exit_mode must be one of {sorted(valid_exit_modes)}, got {exit_mode!r}")

    # Walk bars
    trades: list[Trade] = []
    equity = initial_capital
    in_position = False
    entry_idx = -1
    entry_px = 0.0
    trail_active = False
    highest_high_since_act = 0.0  # for trail tracking
    position_size_units = 0.0  # units of base currency
    pending_next_open_exit: tuple[int, str] | None = None

    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    opens = df['Open'].values
    atrs = atr_val.values
    entry_signal_arr = entry_signal.fillna(False).values

    times = df.index

    for i in range(len(df)):
        if in_position and pending_next_open_exit is not None:
            pending_idx, pending_reason = pending_next_open_exit
            if i == pending_idx:
                exit_px = opens[i] - slippage_ticks * mintick
                pnl_per_unit = exit_px - entry_px
                gross_pnl = pnl_per_unit * position_size_units
                exit_trade_value = exit_px * position_size_units
                entry_trade_value = entry_px * position_size_units
                entry_commission = entry_trade_value * (commission_pct / 100.0)
                exit_commission = exit_trade_value * (commission_pct / 100.0)
                net_pnl = gross_pnl - entry_commission - exit_commission
                equity += gross_pnl - exit_commission
                pnl_pct = net_pnl / entry_trade_value
                trades.append(Trade(
                    entry_idx=entry_idx,
                    entry_time=times[entry_idx],
                    entry_px=entry_px,
                    exit_idx=i,
                    exit_time=times[i],
                    exit_px=exit_px,
                    pnl_pct=pnl_pct * 100,
                    exit_reason=pending_reason,
                ))
                in_position = False
                position_size_units = 0.0
                pending_next_open_exit = None

        if not in_position:
            # Check entry signal — execute at close of signal bar
            if entry_signal_arr[i] and not pd.isna(atrs[i]):
                trade_value = equity * (qty_pct / 100.0)
                entry_px = closes[i] + slippage_ticks * mintick
                position_size_units = trade_value / entry_px
                entry_idx = i
                trail_active = False
                highest_high_since_act = closes[i]  # init, not yet activated
                in_position = True
                pending_next_open_exit = None
                # commission on entry
                equity -= trade_value * (commission_pct / 100.0)
        else:
            # Pine v18e: each bar re-evaluates with CURRENT bar's ATR:
            #   init_sl = entry_px - sl_atr_mul * current_atr  (dynamic SL)
            #   trail activation threshold = entry_px + rounded ticks from current_atr
            #   trail offset = rounded ticks from current_atr
            # Pine's trail_points/trail_offset are integer tick counts; for JPY pairs
            # syminfo.mintick is 0.001, so raw ATR distances must be tick-quantized.
            # Intra-bar simulation:
            #   Bullish bar (close >= open): open → low → high → close
            #   Bearish bar (close < open):  open → high → low → close
            cur_atr = atrs[i]
            if pd.isna(cur_atr):
                continue  # ATR not ready, skip
            init_sl_dyn = entry_px - sl_atr_mul * cur_atr
            trail_act_dyn = round((trail_act_mul * cur_atr) / mintick) * mintick
            trail_off_dyn = round((trail_off_mul * cur_atr) / mintick) * mintick
            trail_act_threshold = entry_px + trail_act_dyn

            bar_bullish = closes[i] >= opens[i]
            exited = False

            def _exit_now(price, reason):
                nonlocal in_position, position_size_units, equity
                exit_px = price - slippage_ticks * mintick
                pnl_per_unit = exit_px - entry_px
                gross_pnl = pnl_per_unit * position_size_units
                exit_trade_value = exit_px * position_size_units
                entry_trade_value = entry_px * position_size_units
                entry_commission = entry_trade_value * (commission_pct / 100.0)
                exit_commission = exit_trade_value * (commission_pct / 100.0)
                net_pnl = gross_pnl - entry_commission - exit_commission
                equity += gross_pnl - exit_commission
                pnl_pct = net_pnl / entry_trade_value
                trades.append(Trade(
                    entry_idx=entry_idx,
                    entry_time=times[entry_idx],
                    entry_px=entry_px,
                    exit_idx=i,
                    exit_time=times[i],
                    exit_px=exit_px,
                    pnl_pct=pnl_pct * 100,
                    exit_reason=reason,
                ))
                in_position = False
                position_size_units = 0.0

            def _effective_stop():
                if trail_active:
                    return highest_high_since_act - trail_off_dyn
                return init_sl_dyn

            if exit_mode in {"close_only", "next_open"}:
                if not trail_active and closes[i] >= trail_act_threshold:
                    trail_active = True
                    highest_high_since_act = closes[i]
                elif trail_active and closes[i] > highest_high_since_act:
                    highest_high_since_act = closes[i]

                if closes[i] <= _effective_stop():
                    reason = "trail" if trail_active else "stop_loss"
                    if exit_mode == "next_open" and i + 1 < len(df):
                        pending_next_open_exit = (i + 1, reason)
                    else:
                        _exit_now(closes[i], reason)
                        exited = True
            elif bar_bullish:
                # Phase 1: low — check stop (trail not yet updated this bar)
                if lows[i] <= _effective_stop():
                    fill_px = lows[i] if exit_mode == "conservative_intrabar" else _effective_stop()
                    _exit_now(fill_px, "trail" if trail_active else "stop_loss")
                    exited = True
                # Phase 2: high — trail activation/HWM update
                if not exited:
                    if not trail_active and highs[i] >= trail_act_threshold:
                        trail_active = True
                        highest_high_since_act = highs[i]
                    elif trail_active and highs[i] > highest_high_since_act:
                        highest_high_since_act = highs[i]
            else:
                # Bearish: Phase 1: high — trail activation/HWM update first
                if not trail_active and highs[i] >= trail_act_threshold:
                    trail_active = True
                    highest_high_since_act = highs[i]
                elif trail_active and highs[i] > highest_high_since_act:
                    highest_high_since_act = highs[i]
                # Phase 2: low — check stop
                if lows[i] <= _effective_stop():
                    fill_px = lows[i] if exit_mode == "conservative_intrabar" else _effective_stop()
                    _exit_now(fill_px, "trail" if trail_active else "stop_loss")
                    exited = True

    # Close any open trade at last bar
    if in_position:
        exit_px = closes[-1] - slippage_ticks * mintick
        pnl_per_unit = exit_px - entry_px
        gross_pnl = pnl_per_unit * position_size_units
        entry_trade_value = entry_px * position_size_units
        exit_trade_value = exit_px * position_size_units
        entry_commission = entry_trade_value * (commission_pct / 100.0)
        exit_commission = exit_trade_value * (commission_pct / 100.0)
        net_pnl = gross_pnl - entry_commission - exit_commission
        equity += gross_pnl - exit_commission
        pnl_pct = net_pnl / entry_trade_value
        trades.append(Trade(
            entry_idx=entry_idx,
            entry_time=times[entry_idx],
            entry_px=entry_px,
            exit_idx=len(df) - 1,
            exit_time=times[-1],
            exit_px=exit_px,
            pnl_pct=pnl_pct * 100,
            exit_reason="eod",
        ))

    return compute_metrics(trades, initial_capital, equity)


def compute_metrics(trades: list[Trade], initial_capital: float, final_equity: float) -> dict:
    if not trades:
        return {"N": 0, "WR": None, "PF": None, "net_pct": 0.0, "trades": []}

    pnl_pcts = [t.pnl_pct for t in trades]
    wins = [p for p in pnl_pcts if p > 0]
    losses = [p for p in pnl_pcts if p <= 0]

    N = len(trades)
    WR = len(wins) / N
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = -sum(losses) if losses else 0.0
    PF = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    net_pct = (final_equity / initial_capital - 1.0) * 100

    # Max drawdown (on equity curve)
    eq_curve = [initial_capital]
    for t in trades:
        # Approximate: apply pnl proportionally to current equity
        e = eq_curve[-1]
        e_new = e * (1 + t.pnl_pct / 100.0 * 0.1)  # 10% of equity per trade
        eq_curve.append(e_new)
    eq_arr = np.array(eq_curve)
    running_max = np.maximum.accumulate(eq_arr)
    drawdown = (eq_arr - running_max) / running_max * 100
    max_dd_pct = float(drawdown.min())

    # Wilson 95% CI for WR
    z = 1.96
    p = WR
    denom = 1 + z**2 / N
    centre = (p + z**2 / (2 * N)) / denom
    half = z * math.sqrt(p * (1 - p) / N + z**2 / (4 * N**2)) / denom
    wilson_lo = centre - half
    wilson_hi = centre + half

    # Avg win/loss
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0

    return {
        "N": N,
        "WR": WR,
        "WR_pct": WR * 100,
        "wilson_lo": wilson_lo,
        "wilson_hi": wilson_hi,
        "PF": PF if PF != float('inf') else None,
        "PF_str": f"{PF:.3f}" if PF != float('inf') else "inf",
        "gross_profit_pct": gross_profit,
        "gross_loss_pct": gross_loss,
        "net_pct": net_pct,
        "max_dd_pct": max_dd_pct,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "trades": [asdict(t) | {"entry_time": t.entry_time.isoformat(), "exit_time": t.exit_time.isoformat()} for t in trades],
    }


# ============================================================================
# Per-pair driver
# ============================================================================

def load_pair(pair: str, repo_root: Path) -> pd.DataFrame:
    parquet = repo_root / "data" / "cache" / "massive" / f"{pair}_15m.parquet"
    df = pd.read_parquet(parquet)
    return df


def main():
    repo_root = Path("/Users/jg-n-012/test/fx-ai-trader")
    pairs = ["USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY"]

    print("=" * 80)
    print("Kalman D7 v18e — JPY Cross-Pair BT (Claude in-session port)")
    print("=" * 80)

    all_results = {}

    # Stage 1: common 13mo window (intersect all 4 pair date ranges)
    # USDJPY ends 2026-04-28, others start ~2025-04-11/29 and end 2026-04-29..06-01
    # Common window: 2025-04-29 (AUDJPY start) to 2026-04-28 (USDJPY end)
    common_start = pd.Timestamp("2025-04-29 00:00:00", tz="UTC")
    common_end = pd.Timestamp("2026-04-28 23:59:59", tz="UTC")

    print(f"\n--- Stage 1: Common 13mo window {common_start.date()} to {common_end.date()} ---\n")

    for pair in pairs:
        df = load_pair(pair, repo_root)
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        df_window = df.loc[common_start:common_end].copy()
        if len(df_window) < 1000:
            print(f"  {pair}: SKIP (only {len(df_window)} bars in window)")
            continue
        result = backtest_v18e(df_window)
        all_results[pair] = result
        print(f"  {pair}: N={result['N']:4d}  WR={result['WR_pct']:5.2f}%  PF={result['PF_str']:>7}  Net={result['net_pct']:+7.3f}%  MaxDD={result['max_dd_pct']:+.3f}%  Wilson_lo={result['wilson_lo']:.3f}")

    # Stage 2: EURJPY 12y full bonus
    print(f"\n--- Stage 2: EUR_JPY full 12y BT ---\n")
    eurjpy_full = load_pair("EUR_JPY", repo_root)
    if eurjpy_full.index.tz is None:
        eurjpy_full.index = eurjpy_full.index.tz_localize('UTC')
    eurjpy_result_12y = backtest_v18e(eurjpy_full)
    all_results["EUR_JPY_12y"] = eurjpy_result_12y
    print(f"  EUR_JPY 12y: N={eurjpy_result_12y['N']:4d}  WR={eurjpy_result_12y['WR_pct']:5.2f}%  PF={eurjpy_result_12y['PF_str']:>7}  Net={eurjpy_result_12y['net_pct']:+8.3f}%  MaxDD={eurjpy_result_12y['max_dd_pct']:+.3f}%  Wilson_lo={eurjpy_result_12y['wilson_lo']:.3f}")

    # Save results
    out_dir = repo_root / "raw" / "bt-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "kalman-d7-v18e-jpy-cross-pair-bt-2026-06-03.json"
    # Strip large 'trades' arrays from main summary, keep separately
    summary = {pair: {k: v for k, v in r.items() if k != 'trades'} for pair, r in all_results.items()}
    summary["__meta__"] = {
        "common_window_start": common_start.isoformat(),
        "common_window_end": common_end.isoformat(),
        "pine_source": "/Users/jg-n-012/test/kalman_d7_strategies/v18e_05ATR_trail.pine",
        "engine": "tools/kalman_d7_v18e_jpy_cross_bt.py",
        "run_date": pd.Timestamp.now(tz="UTC").isoformat(),
    }
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved summary to {out_path}")

    # Save trades separately
    trades_path = out_dir / "kalman-d7-v18e-jpy-cross-pair-bt-2026-06-03-trades.json"
    trades_dump = {pair: r['trades'] for pair, r in all_results.items()}
    with open(trades_path, "w") as f:
        json.dump(trades_dump, f, indent=2, default=str)
    print(f"Saved trades to {trades_path}")

    return all_results


if __name__ == "__main__":
    main()
