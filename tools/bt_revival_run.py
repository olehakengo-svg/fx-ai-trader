"""
BT Revival — 5 Strategy Revival Tests
Runs all 5 tests with proper cache clearing between variants.
"""
import os, sys, json, time, math, warnings
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
warnings.filterwarnings("ignore")

OUTPUT_PATH = Path(_PROJECT_ROOT) / "data" / "cache" / "bt_revival_results_v2.json"

# Suppress demo_trader auto-start
os.environ["BT_MODE"] = "1"

from tools.bt_scanner import (
    PAIRS, load_parquet,
    _setup_patch, _clear_patch, _install_monkey_patch, _restore_monkey_patch,
    _pnl, _sharpe, _profit_factor, _breakeven_wr, _walk_forward_stable,
    _binomial_pvalue,
)


def _clear_all_caches():
    """Force-clear ALL BT caches to ensure fresh computation."""
    try:
        import app as _app
        _app._scalp_bt_cache.clear()
        _app._dt_bt_cache.clear()
        _app._1h_bt_cache.clear()
        _app._bt_cache.clear()
    except Exception:
        pass


def analyze(trades, strategy_name):
    """Analyze trades for a specific strategy."""
    st = [t for t in trades if t.get("entry_type") == strategy_name]
    n = len(st)
    if n == 0:
        return {"n": 0}

    wins = sum(1 for t in st if t.get("outcome") == "WIN")
    wr = wins / n * 100
    pnls = [_pnl(t) for t in st]
    ev_val = round(np.mean(pnls), 4)
    pf = _profit_factor(pnls)
    sharpe = _sharpe(pnls) if n >= 20 else None
    wp = [p for p in pnls if p > 0]
    lp = [abs(p) for p in pnls if p < 0]
    aw = np.mean(wp) if wp else 1.0
    al = np.mean(lp) if lp else 1.0
    be = _breakeven_wr(aw, al)
    wf = _walk_forward_stable(st)
    pv = _binomial_pvalue(wins, n, be)

    # Session breakdown
    sessions = {"london": {"n": 0, "wins": 0}, "ny": {"n": 0, "wins": 0}, "asia": {"n": 0, "wins": 0}}
    for t in st:
        et = t.get("entry_time")
        if et:
            try:
                if hasattr(et, "hour"):
                    h = et.hour
                else:
                    h = pd.Timestamp(et).hour
                if 7 <= h < 12:
                    s = "london"
                elif 12 <= h < 21:
                    s = "ny"
                else:
                    s = "asia"
                sessions[s]["n"] += 1
                if t.get("outcome") == "WIN":
                    sessions[s]["wins"] += 1
            except Exception:
                pass

    return {
        "n": n, "wins": wins, "wr": round(wr, 1), "ev": ev_val, "pf": round(pf, 2),
        "sharpe": sharpe, "be_wr": round(be, 4), "pnl": round(sum(pnls), 3),
        "wf_stable": wf, "p_value": round(pv, 6),
        "sessions": sessions,
    }


def run_dt(symbol, days, interval="15m"):
    from app import run_daytrade_backtest
    _clear_all_caches()
    return run_daytrade_backtest(symbol, lookback_days=days, interval=interval).get("trade_log", [])


def run_1h(symbol, days):
    from app import run_1h_backtest
    _clear_all_caches()
    return run_1h_backtest(symbol, lookback_days=days, interval="1h").get("trade_log", [])


def pr(label, stats):
    n = stats.get("n", 0)
    if n > 0:
        wr = stats.get("wr", 0)
        ev_val = stats.get("ev", 0)
        pf = stats.get("pf", 0)
        pv = stats.get("p_value", 1)
        wf = stats.get("wf_stable")
        wf_s = "Y" if wf else ("N" if wf is not None else "?")
        sig = " *" if pv < 0.05 else ""
        print(f"  {label:30s} N={n:4d} WR={wr:5.1f}% EV={ev_val:+.4f} PF={pf:.2f} WF={wf_s} p={pv:.4f}{sig}", flush=True)
    else:
        print(f"  {label:30s} N=0", flush=True)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", default="1,2,3,4,5")
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()
    tests = [int(x) for x in args.test.split(",")]
    DAYS = args.days

    print(f"BT REVIVAL RUN — {datetime.now(timezone.utc).isoformat()}", flush=True)
    print(f"Lookback: {DAYS}d | Tests: {tests}", flush=True)
    print("=" * 70, flush=True)

    orig = _install_monkey_patch()

    # Patch auxiliary symbols to return empty DF (skip slow API calls)
    _AUX_SYMS = {"6J=F", "DX-Y.NYB", "^VIX", "^TNX", "^GSPC"}
    import modules.data as _dm
    _real_fetch = _dm.fetch_ohlcv

    def _fast_fetch(symbol="USDJPY=X", period="5d", interval="1m"):
        if symbol in _AUX_SYMS:
            return pd.DataFrame()
        return _real_fetch(symbol, period=period, interval=interval)

    _dm.fetch_ohlcv = _fast_fetch
    try:
        import app as _app_ref
        _app_ref.fetch_ohlcv = _fast_fetch
    except Exception:
        pass

    all_results = {}
    t0 = time.time()

    try:
        # ════════════════════════════════════════════════
        # TEST 1: liquidity_sweep — 365d all pairs
        # ════════════════════════════════════════════════
        if 1 in tests:
            print("\n--- TEST 1: liquidity_sweep (365d, all pairs) ---", flush=True)
            t1 = time.time()
            r1 = {}
            for pair, sym in PAIRS.items():
                try:
                    df = load_parquet(pair, "15m")
                    d = min(DAYS, (df.index[-1] - df.index[0]).days)
                    _clear_patch(); _setup_patch(pair, "15m", df)
                    _clear_all_caches()
                    trades = run_dt(sym, d)
                    stats = analyze(trades, "liquidity_sweep")
                    r1[pair] = stats
                    pr(pair, stats)
                except Exception as e:
                    r1[pair] = {"error": str(e)}
                    print(f"  {pair:30s} ERROR: {e}", flush=True)
            all_results["test1_liquidity_sweep"] = r1
            print(f"  elapsed: {time.time()-t1:.0f}s", flush=True)

        # ════════════════════════════════════════════════
        # TEST 2: vol_spike_mr — SPIKE_RATIO variants
        # ════════════════════════════════════════════════
        if 2 in tests:
            print("\n--- TEST 2: vol_spike_mr (SPIKE_RATIO variants) ---", flush=True)
            t1 = time.time()
            import strategies.daytrade.vol_spike_mr as _vsm
            _orig_ratio = _vsm.VolSpikeMR.SPIKE_RATIO

            pair, sym = "USD_JPY", PAIRS["USD_JPY"]
            df = load_parquet(pair, "15m")
            d = min(DAYS, (df.index[-1] - df.index[0]).days)

            r2 = {}
            for label, val in [("baseline_2.3", 2.3), ("adjusted_2.7", 2.7), ("strict_3.0", 3.0)]:
                _vsm.VolSpikeMR.SPIKE_RATIO = val
                _clear_patch(); _setup_patch(pair, "15m", df)
                _clear_all_caches()
                print(f"  Running SPIKE_RATIO={val}...", flush=True)
                trades = run_dt(sym, d)
                stats = analyze(trades, "vol_spike_mr")
                r2[label] = stats
                pr(f"RATIO={val}", stats)

            _vsm.VolSpikeMR.SPIKE_RATIO = _orig_ratio
            all_results["test2_vol_spike_mr"] = r2
            print(f"  elapsed: {time.time()-t1:.0f}s", flush=True)

        # ════════════════════════════════════════════════
        # TEST 3: eurgbp_daily_mr — EUR_GBP 1h 500d + 15m
        # ════════════════════════════════════════════════
        if 3 in tests:
            print("\n--- TEST 3: eurgbp_daily_mr (EUR_GBP, 1h + 15m) ---", flush=True)
            t1 = time.time()
            pair, sym = "EUR_GBP", PAIRS["EUR_GBP"]
            r3 = {}

            # 1h test (500d)
            try:
                df = load_parquet(pair, "1h")
                d = min(500, (df.index[-1] - df.index[0]).days)
                _clear_patch(); _setup_patch(pair, "1h", df)
                _clear_all_caches()
                trades = run_1h(sym, d)
                stats = analyze(trades, "eurgbp_daily_mr")
                r3["1h_500d"] = stats
                pr(f"EUR_GBP 1h ({d}d)", stats)
            except Exception as e:
                r3["1h_500d"] = {"error": str(e)}
                print(f"  1h ERROR: {e}", flush=True)

            # 15m test (365d)
            try:
                df = load_parquet(pair, "15m")
                d = min(DAYS, (df.index[-1] - df.index[0]).days)
                _clear_patch(); _setup_patch(pair, "15m", df)
                _clear_all_caches()
                trades = run_dt(sym, d)
                stats = analyze(trades, "eurgbp_daily_mr")
                r3["15m_365d"] = stats
                pr(f"EUR_GBP 15m ({d}d)", stats)
            except Exception as e:
                r3["15m_365d"] = {"error": str(e)}
                print(f"  15m ERROR: {e}", flush=True)

            all_results["test3_eurgbp_daily_mr"] = r3
            print(f"  elapsed: {time.time()-t1:.0f}s", flush=True)

        # ════════════════════════════════════════════════
        # TEST 4: dt_sr_channel_reversal — SL expansion
        # ════════════════════════════════════════════════
        if 4 in tests:
            print("\n--- TEST 4: dt_sr_channel_reversal (SL expansion) ---", flush=True)
            t1 = time.time()
            import strategies.daytrade.dt_sr_channel as _dsc

            r4 = {}
            _orig_evaluate = _dsc.DtSrChannelReversal.evaluate

            # Test on EUR_JPY (highest N=362) and USD_JPY (N=177)
            test_pairs = [("EUR_JPY", PAIRS["EUR_JPY"]), ("USD_JPY", PAIRS["USD_JPY"])]

            for pair, sym in test_pairs:
                try:
                    df = load_parquet(pair, "15m")
                    d = min(DAYS, (df.index[-1] - df.index[0]).days)

                    # Baseline (SL=ATR7*1.0, TP=ATR7*2.0)
                    _dsc.DtSrChannelReversal.evaluate = _orig_evaluate
                    _clear_patch(); _setup_patch(pair, "15m", df)
                    _clear_all_caches()
                    trades = run_dt(sym, d)
                    stats_base = analyze(trades, "dt_sr_channel_reversal")
                    r4[f"{pair}_sl1.0"] = stats_base
                    pr(f"{pair} SL=1.0 (base)", stats_base)

                    # SL Expansion: wrap evaluate to use ATR7*1.5
                    def _make_patched(orig_fn):
                        def _patched(self, ctx):
                            result = orig_fn(self, ctx)
                            if result is not None:
                                atr7 = ctx.atr7 if hasattr(ctx, 'atr7') else ctx.atr
                                if result.signal == "BUY":
                                    result.sl = ctx.entry - atr7 * 1.5
                                else:
                                    result.sl = ctx.entry + atr7 * 1.5
                            return result
                        return _patched

                    _dsc.DtSrChannelReversal.evaluate = _make_patched(_orig_evaluate)
                    _clear_patch(); _setup_patch(pair, "15m", df)
                    _clear_all_caches()
                    trades = run_dt(sym, d)
                    stats_exp = analyze(trades, "dt_sr_channel_reversal")
                    r4[f"{pair}_sl1.5"] = stats_exp
                    pr(f"{pair} SL=1.5 (exp)", stats_exp)

                except Exception as e:
                    r4[f"{pair}_error"] = {"error": str(e)}
                    print(f"  {pair:30s} ERROR: {e}", flush=True)

            # Restore original
            _dsc.DtSrChannelReversal.evaluate = _orig_evaluate
            all_results["test4_dt_sr_channel"] = r4
            print(f"  elapsed: {time.time()-t1:.0f}s", flush=True)

        # ════════════════════════════════════════════════
        # TEST 5: gold_trend_momentum — FX pair transfer
        # ════════════════════════════════════════════════
        if 5 in tests:
            print("\n--- TEST 5: gold_trend_momentum (FX pair transfer) ---", flush=True)
            t1 = time.time()
            import strategies.daytrade.gold_trend_momentum as _gtm
            _orig_sym = _gtm.GoldTrendMomentum._enabled_symbols
            _gtm.GoldTrendMomentum._enabled_symbols = frozenset({
                "USDJPY", "EURUSD", "GBPUSD", "EURJPY", "EURGBP", "GBPJPY"
            })

            r5 = {}
            for pair, sym in PAIRS.items():
                try:
                    df = load_parquet(pair, "15m")
                    d = min(DAYS, (df.index[-1] - df.index[0]).days)
                    _clear_patch(); _setup_patch(pair, "15m", df)
                    _clear_all_caches()
                    trades = run_dt(sym, d)
                    stats = analyze(trades, "gold_trend_momentum")
                    r5[pair] = stats
                    pr(pair, stats)
                except Exception as e:
                    r5[pair] = {"error": str(e)}
                    print(f"  {pair:30s} ERROR: {e}", flush=True)

            _gtm.GoldTrendMomentum._enabled_symbols = _orig_sym
            all_results["test5_gold_trend_momentum"] = r5
            print(f"  elapsed: {time.time()-t1:.0f}s", flush=True)

    finally:
        _restore_monkey_patch(orig)

    elapsed = time.time() - t0
    output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "lookback_days": DAYS,
        "total_elapsed": round(elapsed, 1),
        "results": all_results,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'='*70}", flush=True)
    print(f"COMPLETE in {elapsed:.0f}s — saved to {OUTPUT_PATH}", flush=True)
    print(f"{'='*70}", flush=True)


if __name__ == "__main__":
    main()
