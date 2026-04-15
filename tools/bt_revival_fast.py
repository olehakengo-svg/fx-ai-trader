"""
Fast BT Revival Tests — Uses bt_scanner infrastructure with 120d lookback.
Targeted tests for 5 strategies under review.
"""
import os, sys, json, time, math, traceback, warnings
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

OUTPUT_PATH = Path(_PROJECT_ROOT) / "data" / "cache" / "bt_revival_results.json"

# ── Suppress demo_trader auto-start during BT ──
os.environ["BT_MODE"] = "1"

from tools.bt_scanner import (
    PAIRS, CACHE_DIR, load_parquet,
    _setup_patch, _clear_patch, _install_monkey_patch, _restore_monkey_patch,
    _pnl, _sharpe, _profit_factor, _breakeven_wr, _walk_forward_stable,
    _binomial_pvalue,
)


def _clear_bt_caches():
    try:
        import app as _app
        _app._scalp_bt_cache.clear()
        _app._dt_bt_cache.clear()
        _app._1h_bt_cache.clear()
        _app._bt_cache.clear()
    except Exception:
        pass


def analyze_strat(trades, strategy_name):
    """Analyze trades for a specific strategy."""
    st = [t for t in trades if t.get("entry_type") == strategy_name]
    n = len(st)
    if n == 0:
        return {"n": 0}

    wins = sum(1 for t in st if t.get("outcome") == "WIN")
    wr = wins / n * 100
    pnls = [_pnl(t) for t in st]
    ev = round(np.mean(pnls), 4)
    pf = _profit_factor(pnls)
    sharpe = _sharpe(pnls) if n >= 20 else None
    wp = [p for p in pnls if p > 0]
    lp = [abs(p) for p in pnls if p < 0]
    aw = np.mean(wp) if wp else 1.0
    al = np.mean(lp) if lp else 1.0
    be = _breakeven_wr(aw, al)
    wf = _walk_forward_stable(st)
    pv = _binomial_pvalue(wins, n, be)

    return {
        "n": n, "wins": wins, "wr": round(wr, 1), "ev": ev, "pf": round(pf, 2),
        "sharpe": sharpe, "be_wr": round(be, 4), "pnl": round(sum(pnls), 3),
        "wf_stable": wf, "p_value": round(pv, 6),
    }


def run_dt_bt(symbol, days, interval="15m"):
    """Run DT backtest, return trade_log."""
    from app import run_daytrade_backtest
    _clear_bt_caches()
    bt = run_daytrade_backtest(symbol, lookback_days=days, interval=interval)
    return bt.get("trade_log", [])


def run_1h_bt(symbol, days):
    """Run 1H backtest, return trade_log."""
    from app import run_1h_backtest
    _clear_bt_caches()
    bt = run_1h_backtest(symbol, lookback_days=days, interval="1h")
    return bt.get("trade_log", [])


def print_result(label, stats):
    n = stats.get("n", 0)
    if n > 0:
        wr = stats.get("wr", 0)
        ev = stats.get("ev", 0)
        pf = stats.get("pf", 0)
        pv = stats.get("p_value", 1)
        wf = stats.get("wf_stable")
        wf_s = "Y" if wf else ("N" if wf is not None else "?")
        sig = "*" if pv < 0.05 else ""
        print(f"  {label:25s} N={n:4d} WR={wr:5.1f}% EV={ev:+.4f} PF={pf:.2f} WF={wf_s} p={pv:.4f}{sig}")
    else:
        print(f"  {label:25s} N=0")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", default="1,2,3,4,5")
    parser.add_argument("--days", type=int, default=120, help="Lookback days (default 120)")
    args = parser.parse_args()
    tests = [int(x) for x in args.test.split(",")]
    DAYS = args.days

    print(f"BT REVIVAL FAST — {datetime.now(timezone.utc).isoformat()}")
    print(f"Lookback: {DAYS}d | Tests: {tests}")
    print("=" * 70)

    orig = _install_monkey_patch()

    # Patch auxiliary symbols (VIX, DXY, TNX, 6J) to return empty DF
    # These are used for institutional flow / master bias scoring (not core strategy logic)
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
        # TEST 1: liquidity_sweep across all pairs
        # ════════════════════════════════════════════════
        if 1 in tests:
            print("\n--- TEST 1: liquidity_sweep (all pairs, DT 15m) ---")
            t1 = time.time()
            r1 = {}
            for pair, sym in PAIRS.items():
                try:
                    df = load_parquet(pair, "15m")
                    d = min(DAYS, (df.index[-1] - df.index[0]).days)
                    _clear_patch(); _setup_patch(pair, "15m", df)
                    trades = run_dt_bt(sym, d)
                    stats = analyze_strat(trades, "liquidity_sweep")
                    r1[pair] = stats
                    print_result(pair, stats)
                except Exception as e:
                    r1[pair] = {"error": str(e)}
                    print(f"  {pair:25s} ERROR: {e}")
            all_results["liquidity_sweep"] = r1
            print(f"  elapsed: {time.time()-t1:.0f}s")

        # ════════════════════════════════════════════════
        # TEST 2: vol_spike_mr — SPIKE_RATIO variants
        # ════════════════════════════════════════════════
        if 2 in tests:
            print("\n--- TEST 2: vol_spike_mr (USD_JPY, SPIKE_RATIO variants) ---")
            t1 = time.time()
            import strategies.daytrade.vol_spike_mr as _vsm
            _orig = _vsm.VolSpikeMR.SPIKE_RATIO

            pair, sym = "USD_JPY", PAIRS["USD_JPY"]
            df = load_parquet(pair, "15m")
            d = min(DAYS, (df.index[-1] - df.index[0]).days)

            r2 = {}
            for label, val in [("2.3_baseline", 2.3), ("2.7_adjusted", 2.7), ("3.0_strict", 3.0)]:
                _vsm.VolSpikeMR.SPIKE_RATIO = val
                _clear_patch(); _setup_patch(pair, "15m", df)
                _clear_bt_caches()
                trades = run_dt_bt(sym, d)
                stats = analyze_strat(trades, "vol_spike_mr")
                r2[label] = stats
                print_result(f"RATIO={val}", stats)

            _vsm.VolSpikeMR.SPIKE_RATIO = _orig
            all_results["vol_spike_mr"] = r2
            print(f"  elapsed: {time.time()-t1:.0f}s")

        # ════════════════════════════════════════════════
        # TEST 3: eurgbp_daily_mr — EUR_GBP 1h + 15m
        # ════════════════════════════════════════════════
        if 3 in tests:
            print("\n--- TEST 3: eurgbp_daily_mr (EUR_GBP, 1h + 15m) ---")
            t1 = time.time()
            pair, sym = "EUR_GBP", PAIRS["EUR_GBP"]
            r3 = {}

            # 1h test
            try:
                df = load_parquet(pair, "1h")
                d = min(DAYS * 3, (df.index[-1] - df.index[0]).days)  # Allow longer for 1h
                _clear_patch(); _setup_patch(pair, "1h", df)
                trades = run_1h_bt(sym, d)
                stats = analyze_strat(trades, "eurgbp_daily_mr")
                r3["1h"] = stats
                print_result(f"EUR_GBP 1h ({d}d)", stats)
            except Exception as e:
                r3["1h"] = {"error": str(e)}
                print(f"  1h ERROR: {e}")

            # 15m test
            try:
                df = load_parquet(pair, "15m")
                d = min(DAYS, (df.index[-1] - df.index[0]).days)
                _clear_patch(); _setup_patch(pair, "15m", df)
                trades = run_dt_bt(sym, d)
                stats = analyze_strat(trades, "eurgbp_daily_mr")
                r3["15m"] = stats
                print_result(f"EUR_GBP 15m ({d}d)", stats)
            except Exception as e:
                r3["15m"] = {"error": str(e)}
                print(f"  15m ERROR: {e}")

            all_results["eurgbp_daily_mr"] = r3
            print(f"  elapsed: {time.time()-t1:.0f}s")

        # ════════════════════════════════════════════════
        # TEST 4: dt_sr_channel_reversal — baseline across pairs
        # (SL expansion requires code change — run baseline first)
        # ════════════════════════════════════════════════
        if 4 in tests:
            print("\n--- TEST 4: dt_sr_channel_reversal (all pairs, baseline) ---")
            t1 = time.time()
            r4 = {}
            for pair, sym in PAIRS.items():
                try:
                    df = load_parquet(pair, "15m")
                    d = min(DAYS, (df.index[-1] - df.index[0]).days)
                    _clear_patch(); _setup_patch(pair, "15m", df)
                    trades = run_dt_bt(sym, d)
                    stats = analyze_strat(trades, "dt_sr_channel_reversal")
                    r4[pair] = stats
                    print_result(pair, stats)
                except Exception as e:
                    r4[pair] = {"error": str(e)}
                    print(f"  {pair:25s} ERROR: {e}")
            all_results["dt_sr_channel_reversal"] = r4
            print(f"  elapsed: {time.time()-t1:.0f}s")

        # ════════════════════════════════════════════════
        # TEST 5: gold_trend_momentum — FX pair transfer
        # ════════════════════════════════════════════════
        if 5 in tests:
            print("\n--- TEST 5: gold_trend_momentum FX transfer (all pairs) ---")
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
                    _clear_bt_caches()
                    trades = run_dt_bt(sym, d)
                    stats = analyze_strat(trades, "gold_trend_momentum")
                    r5[pair] = stats
                    print_result(pair, stats)
                except Exception as e:
                    r5[pair] = {"error": str(e)}
                    print(f"  {pair:25s} ERROR: {e}")

            _gtm.GoldTrendMomentum._enabled_symbols = _orig_sym
            all_results["gold_trend_momentum"] = r5
            print(f"  elapsed: {time.time()-t1:.0f}s")

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

    print(f"\n{'='*70}")
    print(f"COMPLETE in {elapsed:.0f}s — saved to {OUTPUT_PATH}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
