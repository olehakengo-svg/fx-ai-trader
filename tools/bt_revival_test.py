"""
BT Revival Test — 5 strategies targeted testing
Tests specific parameter adjustments for strategies under review.

Tests:
  1. liquidity_sweep: 365d DT BT across all 6 FX pairs (15m)
  2. vol_spike_mr: SPIKE_RATIO=2.7 + London-only filter (15m, USD_JPY)
  3. eurgbp_daily_mr: EUR_GBP 1h 500d BT
  4. dt_sr_channel_reversal: SL expansion (ATR×1.5) across all pairs (15m)
  5. gold_trend_momentum: FX pair transfer test (remove XAU filter) (15m)

Usage:
    python3 tools/bt_revival_test.py              # All 5 tests
    python3 tools/bt_revival_test.py --test 1     # Single test
    python3 tools/bt_revival_test.py --test 1,2,3 # Specific tests
"""

import os
import sys
import json
import time
import math
import traceback
import argparse
import warnings
from pathlib import Path
from datetime import datetime, timezone

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
except ImportError:
    pass

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ── Reuse bt_scanner infrastructure ──
from tools.bt_scanner import (
    PAIRS, CACHE_DIR, load_parquet,
    _setup_patch, _clear_patch, _install_monkey_patch, _restore_monkey_patch,
    _pnl, _sharpe, _profit_factor, _breakeven_wr, _walk_forward_stable,
    _binomial_pvalue,
    scan_combination,
)


def _clear_bt_caches():
    """Clear all BT result caches in app.py to force re-computation."""
    try:
        import app as _app
        _app._scalp_bt_cache.clear()
        _app._dt_bt_cache.clear()
        _app._1h_bt_cache.clear()
        _app._bt_cache.clear()
    except Exception:
        pass


def _patch_auxiliary_data():
    """
    Patch fetch_ohlcv to return empty DataFrames for auxiliary symbols
    (VIX, DXY, TNX, 6J=F, COT) to avoid slow API calls during BT.
    These don't affect core strategy logic, only institutional flow/master bias scoring.
    """
    import modules.data as _data_mod

    _real_fetch = _data_mod.fetch_ohlcv
    _AUX_SYMBOLS = {"6J=F", "DX-Y.NYB", "^VIX", "^TNX", "^GSPC"}

    def _fast_fetch(symbol="USDJPY=X", period="5d", interval="1m"):
        if symbol in _AUX_SYMBOLS:
            # Return minimal empty DF to avoid API call
            return pd.DataFrame()
        return _real_fetch(symbol, period=period, interval=interval)

    _data_mod.fetch_ohlcv = _fast_fetch
    try:
        import app as _app
        _app.fetch_ohlcv = _fast_fetch
    except Exception:
        pass
    return _real_fetch

OUTPUT_PATH = Path(_PROJECT_ROOT) / "data" / "cache" / "bt_revival_results.json"


# ══════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════

def analyze_trades(trades, strategy_name):
    """Analyze trade list for a specific strategy, return stats dict."""
    strat_trades = [t for t in trades if t.get("entry_type") == strategy_name]
    n = len(strat_trades)
    if n == 0:
        return None

    wins = sum(1 for t in strat_trades if t.get("outcome") == "WIN")
    wr = wins / n * 100 if n > 0 else 0
    pnls = [_pnl(t) for t in strat_trades]
    ev = round(np.mean(pnls), 4) if pnls else 0.0
    pf = _profit_factor(pnls)
    sharpe = _sharpe(pnls) if n >= 20 else None

    wins_pnl = [p for p in pnls if p > 0]
    losses_pnl = [abs(p) for p in pnls if p < 0]
    avg_win = np.mean(wins_pnl) if wins_pnl else 1.0
    avg_loss = np.mean(losses_pnl) if losses_pnl else 1.0
    be_wr = _breakeven_wr(avg_win, avg_loss)
    wf = _walk_forward_stable(strat_trades)
    p_val = _binomial_pvalue(wins, n, be_wr)

    # Session breakdown (London/NY/Asia)
    session_stats = {"london": {"n": 0, "wins": 0}, "ny": {"n": 0, "wins": 0}, "asia": {"n": 0, "wins": 0}}
    for t in strat_trades:
        et = t.get("entry_time", "")
        try:
            if isinstance(et, str):
                from datetime import datetime as _dt
                _t = _dt.fromisoformat(et.replace("Z", "+00:00"))
                h = _t.hour
            else:
                h = et.hour
        except Exception:
            continue
        if 7 <= h < 12:
            sess = "london"
        elif 12 <= h < 21:
            sess = "ny"
        else:
            sess = "asia"
        session_stats[sess]["n"] += 1
        if t.get("outcome") == "WIN":
            session_stats[sess]["wins"] += 1

    return {
        "n": n, "wins": wins, "wr": round(wr, 1), "ev": ev, "pf": pf,
        "sharpe": sharpe, "be_wr": round(be_wr, 4), "pnl": round(sum(pnls), 3),
        "wf_stable": wf, "p_value": round(p_val, 6),
        "session_breakdown": session_stats,
    }


# ══════════════════════════════════════════════════════════
#  Test 1: liquidity_sweep 365d all pairs
# ══════════════════════════════════════════════════════════

def test_1_liquidity_sweep():
    """365d DT BT for liquidity_sweep across all 6 FX pairs."""
    print("\n" + "=" * 60)
    print("TEST 1: liquidity_sweep — 365d DT BT (all pairs)")
    print("=" * 60)

    from app import run_daytrade_backtest
    results = {}

    for pair, symbol in PAIRS.items():
        print(f"\n  [{pair}] Loading 15m cache...")
        try:
            df = load_parquet(pair, "15m")
            days = (df.index[-1] - df.index[0]).days
            print(f"  [{pair}] {len(df)} bars, {days} days")
        except FileNotFoundError:
            print(f"  [{pair}] SKIP - no 15m cache")
            continue

        _clear_patch()
        _clear_bt_caches()
        _setup_patch(pair, "15m", df)

        print(f"  [{pair}] Running BT ({days}d)...")
        try:
            bt = run_daytrade_backtest(symbol, lookback_days=days, interval="15m")
            trades = bt.get("trade_log", [])
            stats = analyze_trades(trades, "liquidity_sweep")
            if stats:
                results[pair] = stats
                print(f"  [{pair}] N={stats['n']} WR={stats['wr']:.1f}% EV={stats['ev']:+.3f} PF={stats['pf']:.2f}")
            else:
                print(f"  [{pair}] N=0 (no trades)")
                results[pair] = {"n": 0}
        except Exception as e:
            print(f"  [{pair}] ERROR: {e}")
            traceback.print_exc()
            results[pair] = {"error": str(e)}

    return {"test": "liquidity_sweep_365d", "results": results}


# ══════════════════════════════════════════════════════════
#  Test 2: vol_spike_mr — SPIKE_RATIO=2.7 + London filter
# ══════════════════════════════════════════════════════════

def test_2_vol_spike_mr():
    """Test vol_spike_mr with SPIKE_RATIO=2.7 and London-only filter."""
    print("\n" + "=" * 60)
    print("TEST 2: vol_spike_mr — SPIKE_RATIO variants + London filter")
    print("=" * 60)

    from app import run_daytrade_backtest

    # We'll run 3 variants: baseline(2.3), adjusted(2.7), strict(3.0)
    # + session filter analysis
    import strategies.daytrade.vol_spike_mr as _vsm
    _orig_ratio = _vsm.VolSpikeMR.SPIKE_RATIO

    pair = "USD_JPY"
    symbol = PAIRS[pair]

    print(f"\n  Loading 15m cache for {pair}...")
    df = load_parquet(pair, "15m")
    days = (df.index[-1] - df.index[0]).days
    print(f"  {len(df)} bars, {days} days")

    _clear_patch()
    _setup_patch(pair, "15m", df)

    results = {}

    for ratio_label, ratio_val in [("baseline_2.3", 2.3), ("adjusted_2.7", 2.7), ("strict_3.0", 3.0)]:
        _vsm.VolSpikeMR.SPIKE_RATIO = ratio_val
        _clear_bt_caches()  # Force re-computation with new parameter
        _clear_patch()
        _setup_patch(pair, "15m", df)
        print(f"\n  [{ratio_label}] SPIKE_RATIO={ratio_val}...")
        try:
            bt = run_daytrade_backtest(symbol, lookback_days=days, interval="15m")
            trades = bt.get("trade_log", [])
            stats = analyze_trades(trades, "vol_spike_mr")
            if stats:
                results[ratio_label] = stats
                print(f"  [{ratio_label}] N={stats['n']} WR={stats['wr']:.1f}% EV={stats['ev']:+.3f} PF={stats['pf']:.2f}")
                sess = stats.get("session_breakdown", {})
                for s, sd in sess.items():
                    sn = sd["n"]
                    sw = sd["wins"]
                    swr = sw / sn * 100 if sn > 0 else 0
                    print(f"    {s}: N={sn} WR={swr:.1f}%")
            else:
                print(f"  [{ratio_label}] N=0")
                results[ratio_label] = {"n": 0}
        except Exception as e:
            print(f"  [{ratio_label}] ERROR: {e}")
            results[ratio_label] = {"error": str(e)}

    # Restore original
    _vsm.VolSpikeMR.SPIKE_RATIO = _orig_ratio

    return {"test": "vol_spike_mr_variants", "pair": pair, "results": results}


# ══════════════════════════════════════════════════════════
#  Test 3: eurgbp_daily_mr — EUR_GBP 1h 500d
# ══════════════════════════════════════════════════════════

def test_3_eurgbp_daily_mr():
    """EUR_GBP 1h 500d BT for eurgbp_daily_mr."""
    print("\n" + "=" * 60)
    print("TEST 3: eurgbp_daily_mr — EUR_GBP 1h 500d BT")
    print("=" * 60)

    from app import run_1h_backtest, run_daytrade_backtest

    pair = "EUR_GBP"
    symbol = PAIRS[pair]

    results = {}

    # Test on 1h timeframe
    print(f"\n  Loading 1h cache for {pair}...")
    try:
        df_1h = load_parquet(pair, "1h")
        days_1h = (df_1h.index[-1] - df_1h.index[0]).days
        print(f"  {len(df_1h)} bars, {days_1h} days")

        _clear_patch()
        _clear_bt_caches()
        _setup_patch(pair, "1h", df_1h)

        print(f"  Running 1h BT ({days_1h}d)...")
        bt = run_1h_backtest(symbol, lookback_days=days_1h, interval="1h")
        trades = bt.get("trade_log", [])
        stats = analyze_trades(trades, "eurgbp_daily_mr")
        if stats:
            results["1h"] = stats
            print(f"  [1h] N={stats['n']} WR={stats['wr']:.1f}% EV={stats['ev']:+.3f} PF={stats['pf']:.2f}")
        else:
            print(f"  [1h] N=0")
            results["1h"] = {"n": 0}
    except Exception as e:
        print(f"  [1h] ERROR: {e}")
        traceback.print_exc()
        results["1h"] = {"error": str(e)}

    # Also test on 15m (365d)
    print(f"\n  Loading 15m cache for {pair}...")
    try:
        df_15m = load_parquet(pair, "15m")
        days_15m = (df_15m.index[-1] - df_15m.index[0]).days
        print(f"  {len(df_15m)} bars, {days_15m} days")

        _clear_patch()
        _clear_bt_caches()
        _setup_patch(pair, "15m", df_15m)

        print(f"  Running 15m DT BT ({days_15m}d)...")
        bt = run_daytrade_backtest(symbol, lookback_days=days_15m, interval="15m")
        trades = bt.get("trade_log", [])
        stats = analyze_trades(trades, "eurgbp_daily_mr")
        if stats:
            results["15m"] = stats
            print(f"  [15m] N={stats['n']} WR={stats['wr']:.1f}% EV={stats['ev']:+.3f} PF={stats['pf']:.2f}")
        else:
            print(f"  [15m] N=0")
            results["15m"] = {"n": 0}
    except Exception as e:
        print(f"  [15m] ERROR: {e}")
        traceback.print_exc()
        results["15m"] = {"error": str(e)}

    return {"test": "eurgbp_daily_mr_500d", "pair": pair, "results": results}


# ══════════════════════════════════════════════════════════
#  Test 4: dt_sr_channel_reversal — SL expansion
# ══════════════════════════════════════════════════════════

def test_4_dt_sr_channel():
    """Test dt_sr_channel_reversal with wider SL (ATR×1.5 vs baseline 1.0)."""
    print("\n" + "=" * 60)
    print("TEST 4: dt_sr_channel_reversal — SL expansion test")
    print("=" * 60)

    from app import run_daytrade_backtest
    import strategies.daytrade.dt_sr_channel as _dsc

    # We need to modify the SL multiplier in evaluate()
    # The strategy uses atr7 * 1.0 for SL. We'll monkey-patch to test wider SL.
    _orig_evaluate = _dsc.DtSrChannelReversal.evaluate

    def _make_patched_evaluate(sl_mult):
        """Create a patched evaluate with custom SL multiplier."""
        def _patched_evaluate(self, ctx):
            # Call original
            result = _orig_evaluate(self, ctx)
            if result is None:
                return None
            # Adjust SL: widen by multiplier
            entry = ctx.entry
            if result.signal == "BUY":
                orig_sl_dist = entry - result.sl
                new_sl_dist = orig_sl_dist * sl_mult
                result.sl = entry - new_sl_dist
            else:
                orig_sl_dist = result.sl - entry
                new_sl_dist = orig_sl_dist * sl_mult
                result.sl = entry + new_sl_dist
            return result
        return _patched_evaluate

    results = {}

    for pair, symbol in PAIRS.items():
        print(f"\n  [{pair}] Loading 15m cache...")
        try:
            df = load_parquet(pair, "15m")
            days = (df.index[-1] - df.index[0]).days
        except FileNotFoundError:
            print(f"  [{pair}] SKIP")
            continue

        _clear_patch()
        _setup_patch(pair, "15m", df)

        pair_results = {}

        for sl_label, sl_mult in [("baseline_1.0x", 1.0), ("wider_1.5x", 1.5), ("wide_2.0x", 2.0)]:
            if sl_mult == 1.0:
                _dsc.DtSrChannelReversal.evaluate = _orig_evaluate
            else:
                _dsc.DtSrChannelReversal.evaluate = _make_patched_evaluate(sl_mult)

            _clear_bt_caches()
            _clear_patch()
            _setup_patch(pair, "15m", df)

            try:
                bt = run_daytrade_backtest(symbol, lookback_days=days, interval="15m")
                trades = bt.get("trade_log", [])
                stats = analyze_trades(trades, "dt_sr_channel_reversal")
                if stats:
                    pair_results[sl_label] = stats
                    print(f"  [{pair}/{sl_label}] N={stats['n']} WR={stats['wr']:.1f}% EV={stats['ev']:+.3f} PF={stats['pf']:.2f}")
                else:
                    pair_results[sl_label] = {"n": 0}
            except Exception as e:
                print(f"  [{pair}/{sl_label}] ERROR: {e}")
                pair_results[sl_label] = {"error": str(e)}

        results[pair] = pair_results

    # Restore
    _dsc.DtSrChannelReversal.evaluate = _orig_evaluate

    return {"test": "dt_sr_channel_sl_expansion", "results": results}


# ══════════════════════════════════════════════════════════
#  Test 5: gold_trend_momentum — FX pair transfer
# ══════════════════════════════════════════════════════════

def test_5_gold_fx_transfer():
    """Test gold_trend_momentum logic on FX pairs (remove XAU filter)."""
    print("\n" + "=" * 60)
    print("TEST 5: gold_trend_momentum — FX pair transfer test")
    print("=" * 60)

    from app import run_daytrade_backtest
    import strategies.daytrade.gold_trend_momentum as _gtm

    # Remove XAU-only filter
    _orig_symbols = _gtm.GoldTrendMomentum._enabled_symbols
    _gtm.GoldTrendMomentum._enabled_symbols = frozenset({
        "USDJPY", "EURUSD", "GBPUSD", "EURJPY", "EURGBP", "GBPJPY"
    })

    results = {}

    for pair, symbol in PAIRS.items():
        print(f"\n  [{pair}] Loading 15m cache...")
        try:
            df = load_parquet(pair, "15m")
            days = (df.index[-1] - df.index[0]).days
        except FileNotFoundError:
            print(f"  [{pair}] SKIP")
            continue

        _clear_patch()
        _clear_bt_caches()
        _setup_patch(pair, "15m", df)

        try:
            bt = run_daytrade_backtest(symbol, lookback_days=days, interval="15m")
            trades = bt.get("trade_log", [])
            stats = analyze_trades(trades, "gold_trend_momentum")
            if stats:
                results[pair] = stats
                print(f"  [{pair}] N={stats['n']} WR={stats['wr']:.1f}% EV={stats['ev']:+.3f} PF={stats['pf']:.2f}")
            else:
                print(f"  [{pair}] N=0")
                results[pair] = {"n": 0}
        except Exception as e:
            print(f"  [{pair}] ERROR: {e}")
            results[pair] = {"error": str(e)}

    # Restore
    _gtm.GoldTrendMomentum._enabled_symbols = _orig_symbols

    return {"test": "gold_trend_fx_transfer", "results": results}


# ══════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════

ALL_TESTS = {
    1: ("liquidity_sweep 365d", test_1_liquidity_sweep),
    2: ("vol_spike_mr variants", test_2_vol_spike_mr),
    3: ("eurgbp_daily_mr 500d", test_3_eurgbp_daily_mr),
    4: ("dt_sr_channel SL expansion", test_4_dt_sr_channel),
    5: ("gold_trend FX transfer", test_5_gold_fx_transfer),
}


def main():
    parser = argparse.ArgumentParser(description="BT Revival Tests")
    parser.add_argument("--test", type=str, default="1,2,3,4,5",
                        help="Comma-separated test numbers (default: all)")
    args = parser.parse_args()

    test_nums = [int(x.strip()) for x in args.test.split(",")]

    print("=" * 60)
    print("BT REVIVAL TEST SUITE")
    print(f"Tests: {test_nums}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Install monkey-patches: auxiliary data (fast) + parquet cache
    _real_aux = _patch_auxiliary_data()
    orig_fn = _install_monkey_patch()

    all_results = []
    t0 = time.time()

    try:
        for num in test_nums:
            if num not in ALL_TESTS:
                print(f"\n  [WARN] Unknown test #{num}, skipping")
                continue
            label, func = ALL_TESTS[num]
            print(f"\n{'#' * 60}")
            print(f"# Starting Test #{num}: {label}")
            print(f"{'#' * 60}")
            t1 = time.time()
            result = func()
            elapsed = time.time() - t1
            result["elapsed_seconds"] = round(elapsed, 1)
            all_results.append(result)
            print(f"\n  Test #{num} completed in {elapsed:.1f}s")
    finally:
        _restore_monkey_patch(orig_fn)

    total_elapsed = time.time() - t0

    # Save results
    output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_elapsed": round(total_elapsed, 1),
        "tests": all_results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n{'=' * 60}")
    print(f"ALL TESTS COMPLETE in {total_elapsed:.1f}s")
    print(f"Results saved to: {OUTPUT_PATH}")
    print(f"{'=' * 60}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in all_results:
        test_name = r.get("test", "?")
        print(f"\n--- {test_name} ({r.get('elapsed_seconds', 0):.0f}s) ---")
        res = r.get("results", {})
        for k, v in res.items():
            if isinstance(v, dict):
                n = v.get("n", 0)
                if n > 0:
                    wr = v.get("wr", 0)
                    ev = v.get("ev", 0)
                    pf = v.get("pf", 0)
                    pval = v.get("p_value", 1)
                    wf = v.get("wf_stable")
                    wf_str = "✓" if wf else ("✗" if wf is not None else "?")
                    sig = "★" if pval < 0.05 else " "
                    print(f"  {k:20s}  N={n:4d}  WR={wr:5.1f}%  EV={ev:+.3f}  PF={pf:.2f}  WF={wf_str}  p={pval:.4f} {sig}")
                else:
                    err = v.get("error", "")
                    print(f"  {k:20s}  N=0 {err}")


if __name__ == "__main__":
    main()
