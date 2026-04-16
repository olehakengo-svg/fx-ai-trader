#!/usr/bin/env python3
"""BT Infrastructure Diagnostic — ローカルBTの0トレード問題を診断

Usage:
    BT_MODE=1 python3 tools/bt_diagnostic.py [symbol] [lookback_days]

Example:
    BT_MODE=1 python3 tools/bt_diagnostic.py USDJPY=X 60
"""
import os
import sys
import time

# Force BT_MODE before any imports
os.environ["BT_MODE"] = "1"
os.environ["NO_AUTOSTART"] = "1"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("  BT Diagnostic Tool — 0-Trade Root Cause Analysis")
print("=" * 60)

t0 = time.time()
print(f"\n[1/5] Importing app.py (BT_MODE={os.environ.get('BT_MODE')})...")
try:
    import app
    print(f"  ✅ Import OK ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"  ❌ Import FAILED: {e}")
    sys.exit(1)

symbol = sys.argv[1] if len(sys.argv) > 1 else "USDJPY=X"
lookback_days = int(sys.argv[2]) if len(sys.argv) > 2 else 60
interval = "15m"

print(f"\n[2/5] Fetching data: {symbol} {lookback_days}d {interval}...")
t1 = time.time()
try:
    df = app.fetch_ohlcv(symbol, period=f"{lookback_days}d", interval=interval)
    print(f"  Raw bars: {len(df)} ({time.time()-t1:.1f}s)")
    df = app.add_indicators(df)
    df_clean = df.dropna()
    print(f"  After indicators+dropna: {len(df_clean)}")
    if len(df_clean) < 100:
        print("  ❌ DATA INSUFFICIENT (<100 bars)")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ Data fetch FAILED: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

print(f"\n[3/5] Clearing BT cache...")
app._dt_bt_cache.clear()
print("  ✅ Cache cleared")

# ── Instrumented signal loop ──
print(f"\n[4/5] Running instrumented signal loop (bars={len(df_clean)})...")
MIN_BARS = 200
MAX_HOLD = 24
total_bars_checked = 0
signals_generated = 0
signals_wait = 0
signals_excepted = 0
signals_filtered = 0
entry_type_counts = {}
filter_reasons = {
    "volume": 0, "bar_range": 0, "session": 0,
    "cooldown": 0, "exception": 0, "wait": 0,
    "blocked_type": 0, "unqualified": 0,
    "confirmed_insufficient": 0,
}

# Use df_clean for iteration
_sym = symbol.upper()
_is_jpy = app._is_jpy_scale(symbol)

# Replicate filter logic from run_daytrade_backtest
DT_QUALIFIED = {
    "sr_fib_confluence", "ema_cross", "htf_false_breakout",
    "london_session_breakout", "tokyo_nakane_momentum",
    "adx_trend_continuation", "sr_break_retest", "lin_reg_channel",
    "orb_trap", "london_close_reversal", "gbp_deep_pullback",
    "turtle_soup", "trendline_sweep", "inducement_ob",
    "dual_sr_bounce", "london_ny_swing", "gold_vol_break",
    "jpy_basket_trend", "squeeze_release_momentum", "eurgbp_daily_mr",
    "dt_bb_rsi_mr", "gold_trend_momentum", "liquidity_sweep",
    "session_time_bias", "gotobi_fix", "london_fix_reversal",
    "vix_carry_unwind", "xs_momentum", "hmm_regime_filter",
    "vol_spike_mr", "doji_breakout", "dt_fib_reversal",
    "dt_sr_channel_reversal", "ema200_trend_reversal", "post_news_vol",
    "ny_close_reversal", "streak_reversal", "vwap_mean_reversion",
}
DT_BLOCKED = {"unknown", "wait"}

# Precompute SR
DT_SR_RECALC = 80
_dt_sr_cache = {}
for _ci in range(200, len(df_clean), DT_SR_RECALC):
    _sr_slice = df_clean.iloc[max(0, _ci - 400):_ci]
    _dt_sr_cache[_ci // DT_SR_RECALC] = app.find_sr_levels_weighted(
        _sr_slice, window=5, tolerance_pct=0.003, min_touches=2,
        max_levels=8, bars_per_day=96)

# HTF cache
try:
    _layer1 = app.get_master_bias(symbol)
except Exception:
    _layer1 = {"direction": "neutral", "label": "—", "score": 0}
_htf_cache = {
    "htf": app._compute_bt_htf_bias(df_clean, min(300, len(df_clean) - 1), mode="daytrade"),
    "layer1": _layer1,
}

last_bar = -99
sample_signals = []

t2 = time.time()
for i in range(max(MIN_BARS, 50), len(df_clean) - MAX_HOLD - 1):
    total_bars_checked += 1

    # Cooldown
    if i - last_bar < 1:
        filter_reasons["cooldown"] += 1
        continue

    row = df_clean.iloc[i]

    # Volume filter
    if "Volume" in df_clean.columns:
        vol = float(row["Volume"])
        if vol > 0 and vol < 100:
            filter_reasons["volume"] += 1
            continue

    # Bar range filter
    bar_range = float(row["High"]) - float(row["Low"])
    if _is_jpy:
        _min_bar_range = 0.030 if interval == "1h" else 0.010
    else:
        _min_bar_range = 0.00030 if interval == "1h" else 0.00010
    if bar_range < _min_bar_range:
        filter_reasons["bar_range"] += 1
        continue

    # Session filter
    if interval != "1h":
        _bt_hour = df_clean.index[i].hour if hasattr(df_clean.index[i], 'hour') else 12
        if _bt_hour < 5 or _bt_hour >= 22:
            _is_jpy_pure = "JPY" in _sym and "XAU" not in _sym
            if not (_is_jpy_pure and 0 <= _bt_hour <= 1):
                filter_reasons["session"] += 1
                continue

    # Signal generation
    _dt_key = i // DT_SR_RECALC
    current_sr_weighted = _dt_sr_cache.get(_dt_key, [])
    current_sr = [sr["price"] for sr in current_sr_weighted]

    bar_df = df_clean.iloc[max(0, i - 500):i + 1]
    bar_time = df_clean.index[i]
    if hasattr(bar_time, 'tzinfo') and bar_time.tzinfo is None:
        from datetime import timezone as tz
        bar_time = bar_time.replace(tzinfo=tz.utc)

    try:
        sig_result = app.compute_daytrade_signal(
            bar_df, tf=interval, sr_levels=current_sr,
            symbol=symbol, backtest_mode=True,
            bar_time=bar_time, htf_cache=_htf_cache,
        )
    except Exception as e:
        signals_excepted += 1
        filter_reasons["exception"] += 1
        if signals_excepted <= 3:
            print(f"  ⚠️ Exception at bar {i}: {e}")
        continue

    sig = sig_result.get("signal", "WAIT")
    if sig == "WAIT":
        signals_wait += 1
        filter_reasons["wait"] += 1
        continue

    entry_type = sig_result.get("entry_type", "unknown")
    signals_generated += 1

    # Track entry types
    entry_type_counts[entry_type] = entry_type_counts.get(entry_type, 0) + 1

    # Entry type filter
    if entry_type in DT_BLOCKED:
        filter_reasons["blocked_type"] += 1
        signals_filtered += 1
        continue

    _dt_reasons = sig_result.get("reasons", [])
    _dt_confirmed = sum(1 for r in _dt_reasons if "✅" in r)
    if entry_type == "ema_cross":
        if _dt_confirmed < 2:
            filter_reasons["confirmed_insufficient"] += 1
            signals_filtered += 1
            continue
    elif entry_type in DT_QUALIFIED:
        if _dt_confirmed < 1:
            filter_reasons["confirmed_insufficient"] += 1
            signals_filtered += 1
            continue
    else:
        filter_reasons["unqualified"] += 1
        signals_filtered += 1
        continue

    # This signal would proceed to trade simulation
    last_bar = i  # Simulate cooldown
    if len(sample_signals) < 10:
        sample_signals.append({
            "bar": i,
            "time": str(bar_time),
            "signal": sig,
            "entry_type": entry_type,
            "score": sig_result.get("score", 0),
            "confirmed": _dt_confirmed,
        })

loop_time = time.time() - t2

print(f"\n{'='*60}")
print(f"  DIAGNOSTIC RESULTS")
print(f"{'='*60}")
print(f"\n  Total bars checked:     {total_bars_checked}")
print(f"  Signals generated:      {signals_generated} (non-WAIT)")
print(f"  Signals excepted:       {signals_excepted}")
print(f"  Signals filtered:       {signals_filtered}")
print(f"  Signals passing all:    {signals_generated - signals_filtered}")
print(f"  Loop time:              {loop_time:.1f}s")

print(f"\n  Filter breakdown:")
for k, v in sorted(filter_reasons.items(), key=lambda x: -x[1]):
    if v > 0:
        pct = v / total_bars_checked * 100
        print(f"    {k:30s} {v:6d} ({pct:5.1f}%)")

if entry_type_counts:
    print(f"\n  Entry types detected:")
    for et, cnt in sorted(entry_type_counts.items(), key=lambda x: -x[1]):
        qualified = "✅" if et in DT_QUALIFIED else "❌"
        print(f"    {qualified} {et:35s} {cnt:4d}")

if sample_signals:
    print(f"\n  Sample passing signals (first {len(sample_signals)}):")
    for s in sample_signals:
        print(f"    [{s['time']}] {s['signal']:4s} {s['entry_type']:30s} "
              f"score={s['score']:.2f} ✅×{s['confirmed']}")

print(f"\n[5/5] Running actual run_daytrade_backtest (cache cleared)...")
t3 = time.time()
result = app.run_daytrade_backtest(symbol, lookback_days=lookback_days, interval=interval)
bt_time = time.time() - t3
print(f"  Completed in {bt_time:.1f}s")
print(f"  Trades: {result.get('trades', 0)}")
if result.get('error'):
    print(f"  Error: {result['error']}")
if result.get('win_rate'):
    print(f"  WR: {result['win_rate']}%  EV: {result['expected_value']}")
if result.get('entry_breakdown'):
    print(f"  Entry breakdown:")
    for et, stats in sorted(result['entry_breakdown'].items(), key=lambda x: -x[1]['total']):
        print(f"    {et:35s} N={stats['total']:3d} WR={stats['win_rate']:5.1f}% EV={stats['ev']:+.3f}")

print(f"\n  Total runtime: {time.time()-t0:.1f}s")
