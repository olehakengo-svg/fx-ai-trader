"""
Comprehensive BT Scanner — All strategies x All pairs x All timeframes
Uses Parquet cache for instant data access (no API calls).

Usage:
    python3 tools/bt_scanner.py                    # Full scan, results to JSON
    python3 tools/bt_scanner.py --pairs USD_JPY    # Specific pair
    python3 tools/bt_scanner.py --tf 15m           # Specific TF
    python3 tools/bt_scanner.py --mode daytrade    # Specific mode only
    python3 tools/bt_scanner.py --min-n 10         # Min trades filter
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

# ── Project root setup (same pattern as bt_data_cache.py) ──
_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# .env loading
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
except ImportError:
    pass

import numpy as np
import pandas as pd

# Suppress warnings during BT runs
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ══════════════════════════════════════════════════════════
#  Configuration
# ══════════════════════════════════════════════════════════

CACHE_DIR = Path(_PROJECT_ROOT) / "data" / "cache" / "massive"
OUTPUT_PATH = Path(_PROJECT_ROOT) / "data" / "cache" / "bt_scan_results.json"

# OANDA pair -> yFinance symbol mapping
PAIRS = {
    "USD_JPY": "USDJPY=X",
    "EUR_USD": "EURUSD=X",
    "GBP_USD": "GBPUSD=X",
    "EUR_JPY": "EURJPY=X",
    "EUR_GBP": "EURGBP=X",
    "GBP_JPY": "GBPJPY=X",
}

# Mode definitions: which BT function, which TFs, which pairs, lookback
MODE_CONFIG = {
    "scalp": {
        "func_name": "run_scalp_backtest",
        "intervals": {"1m": 30, "5m": 55},    # interval -> lookback_days
        "pairs": list(PAIRS.keys()),           # all pairs
    },
    "daytrade": {
        "func_name": "run_daytrade_backtest",
        "intervals": {"15m": 55, "5m": 55},
        "pairs": list(PAIRS.keys()),
    },
    "1h": {
        "func_name": "run_1h_backtest",
        "intervals": {"1h": 90},
        "pairs": list(PAIRS.keys()),
    },
}


# ══════════════════════════════════════════════════════════
#  PnL calculation (friction-adjusted, from trade dicts)
# ══════════════════════════════════════════════════════════

def _pnl(t):
    """Compute PnL in ATR multiples for a single trade dict."""
    ef = t.get("exit_friction_m", 0) or 0
    if t.get("outcome") == "WIN":
        return (t.get("tp_m", 0) or 0) - ef
    else:
        return -((t.get("actual_sl_m") or t.get("sl_m", 0) or 0) + ef)


# ══════════════════════════════════════════════════════════
#  Statistical helpers
# ══════════════════════════════════════════════════════════

def _binomial_pvalue(wins, n, p0):
    """
    One-sided binomial test: P(X >= wins) under H0: p = p0.
    Uses scipy if available, otherwise a normal approximation.
    """
    if n == 0:
        return 1.0
    try:
        from scipy.stats import binomtest
        result = binomtest(wins, n, p0, alternative="greater")
        return result.pvalue
    except ImportError:
        pass
    try:
        from scipy.stats import binom_test
        return binom_test(wins, n, p0, alternative="greater")
    except ImportError:
        pass
    # Normal approximation fallback
    if n < 5:
        return 1.0
    mu = n * p0
    sigma = math.sqrt(n * p0 * (1 - p0))
    if sigma < 1e-9:
        return 0.0 if wins > mu else 1.0
    z = (wins - 0.5 - mu) / sigma  # continuity correction
    # Standard normal CDF approximation
    return 0.5 * math.erfc(z / math.sqrt(2))


def _sharpe(pnls):
    """Sharpe ratio from a list of per-trade PnLs."""
    if len(pnls) < 2:
        return None
    arr = np.array(pnls, dtype=float)
    mu = arr.mean()
    std = arr.std(ddof=1)
    if std < 1e-9:
        return None
    return round(float(mu / std), 3)


def _profit_factor(pnls):
    """Profit factor = gross_profit / gross_loss."""
    gross_p = sum(p for p in pnls if p > 0)
    gross_l = abs(sum(p for p in pnls if p < 0))
    if gross_l < 1e-9:
        return 99.9 if gross_p > 0 else 0.0
    return round(gross_p / gross_l, 3)


def _breakeven_wr(avg_win, avg_loss):
    """Breakeven win rate for a given avg_win/avg_loss ratio."""
    if avg_win + avg_loss < 1e-9:
        return 0.5
    return avg_loss / (avg_win + avg_loss)


def _walk_forward_stable(trades, n_splits=3):
    """
    Check walk-forward stability: is EV positive in at least
    (n_splits - 1) out of n_splits chronological windows?
    """
    if len(trades) < n_splits * 3:
        return None  # not enough data
    chunk_size = len(trades) // n_splits
    positive_windows = 0
    for i in range(n_splits):
        start = i * chunk_size
        end = start + chunk_size if i < n_splits - 1 else len(trades)
        chunk = trades[start:end]
        chunk_pnls = [_pnl(t) for t in chunk]
        if sum(chunk_pnls) > 0:
            positive_windows += 1
    return positive_windows >= (n_splits - 1)


# ══════════════════════════════════════════════════════════
#  Parquet data loader
# ══════════════════════════════════════════════════════════

def load_parquet(pair: str, tf: str) -> pd.DataFrame:
    """Load cached Parquet file for a pair/TF combination."""
    path = CACHE_DIR / f"{pair}_{tf}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Cache not found: {path}")
    df = pd.read_parquet(path)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


# ══════════════════════════════════════════════════════════
#  Monkey-patch fetch_ohlcv to return cached data
# ══════════════════════════════════════════════════════════

# Cache storage for the patched function
_patch_cache = {}  # key: (symbol, interval) -> DataFrame


def _setup_patch(pair, tf, df):
    """Register a DataFrame in the patch cache."""
    symbol = PAIRS.get(pair, f"{pair.replace('_', '')}=X")
    _patch_cache[(symbol, tf)] = df


def _clear_patch():
    """Clear the patch cache."""
    _patch_cache.clear()


def _install_monkey_patch():
    """
    Install monkey-patch on modules.data.fetch_ohlcv to intercept
    calls and return cached DataFrames instead of making API calls.
    Returns the original function for later restoration.
    """
    import modules.data as _data_mod
    _orig_fetch = _data_mod.fetch_ohlcv

    def _patched_fetch(symbol="USDJPY=X", period="5d", interval="1m"):
        key = (symbol, interval)
        if key in _patch_cache:
            return _patch_cache[key].copy()
        # Fallback: check without exact interval match (for 5m supplement etc.)
        for (s, i), cached_df in _patch_cache.items():
            if s == symbol:
                return cached_df.copy()
        # Last resort: original fetch (will hit API)
        print(f"  [WARN] No cache for {symbol}/{interval}, falling back to API")
        return _orig_fetch(symbol, period=period, interval=interval)

    _data_mod.fetch_ohlcv = _patched_fetch
    # Also patch it in app module if already imported
    try:
        import app as _app_mod
        _app_mod.fetch_ohlcv = _patched_fetch
    except Exception:
        pass
    return _orig_fetch


def _restore_monkey_patch(orig_fn):
    """Restore the original fetch_ohlcv function."""
    try:
        import modules.data as _data_mod
        _data_mod.fetch_ohlcv = orig_fn
    except Exception:
        pass
    try:
        import app as _app_mod
        _app_mod.fetch_ohlcv = orig_fn
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
#  Core scanner
# ══════════════════════════════════════════════════════════

def scan_combination(bt_func, symbol, pair, tf, lookback_days):
    """
    Run a single BT and extract per-strategy results.

    Returns list of dicts, one per strategy found in entry_breakdown.
    """
    results = []

    try:
        result = bt_func(symbol, lookback_days=lookback_days, interval=tf)
    except Exception as e:
        print(f"  [ERROR] BT failed for {pair}/{tf}: {e}")
        traceback.print_exc()
        return results

    if "error" in result:
        print(f"  [SKIP] {pair}/{tf}: {result['error']}")
        return results

    entry_breakdown = result.get("entry_breakdown") or {}
    trade_log = result.get("trade_log") or []
    mode = result.get("mode", "unknown")

    # Group trades by entry_type for per-strategy analysis
    trades_by_type = {}
    for t in trade_log:
        et = t.get("entry_type") or t.get("type", "unknown")
        trades_by_type.setdefault(et, []).append(t)

    # Process each strategy
    for strat_name, eb_stats in entry_breakdown.items():
        strat_trades = trades_by_type.get(strat_name, [])
        n = eb_stats.get("total", 0)
        if n == 0:
            continue

        wins = eb_stats.get("wins", 0)
        wr = eb_stats.get("win_rate", 0.0)

        # Compute PnL from trade_log if available
        if strat_trades:
            pnls = [_pnl(t) for t in strat_trades]
            total_pnl = round(sum(pnls), 3)
            ev = round(np.mean(pnls), 4) if pnls else 0.0
            pf = _profit_factor(pnls)
            sharpe = _sharpe(pnls) if len(pnls) >= 20 else None

            # Breakeven WR for binomial test
            wins_pnl = [p for p in pnls if p > 0]
            losses_pnl = [abs(p) for p in pnls if p < 0]
            avg_win = np.mean(wins_pnl) if wins_pnl else 1.0
            avg_loss = np.mean(losses_pnl) if losses_pnl else 1.0
            be_wr = _breakeven_wr(avg_win, avg_loss)

            # Walk-forward stability
            wf_stable = _walk_forward_stable(strat_trades, n_splits=3)
        else:
            # Fallback to entry_breakdown stats only
            ev = eb_stats.get("ev", 0.0)
            total_pnl = round(ev * n, 3)
            pf = 0.0
            sharpe = None
            be_wr = 0.5
            wf_stable = None

        results.append({
            "strategy": strat_name,
            "pair": pair,
            "mode": mode,
            "tf": tf,
            "n": n,
            "wr": round(wr, 1),
            "ev": round(ev, 4),
            "pf": round(pf, 3),
            "pnl": total_pnl,
            "sharpe": sharpe,
            "be_wr": round(be_wr, 4),
            "wins": wins,
            "wf_stable": wf_stable,
        })

    return results


def run_full_scan(pairs=None, timeframes=None, modes=None, min_n=5):
    """
    Run comprehensive BT scan across all combinations.

    Args:
        pairs: list of pair names (e.g. ["USD_JPY"]), or None for all
        timeframes: list of TFs (e.g. ["15m"]), or None for all
        modes: list of modes (e.g. ["daytrade"]), or None for all
        min_n: minimum trade count to include in results

    Returns:
        dict with scan results
    """
    pairs = pairs or list(PAIRS.keys())
    modes = modes or list(MODE_CONFIG.keys())

    print("=" * 70)
    print("  BT Scanner — Comprehensive Strategy Scan")
    print(f"  Pairs: {', '.join(pairs)}")
    print(f"  Modes: {', '.join(modes)}")
    print(f"  Min N: {min_n}")
    print("=" * 70)

    # Verify cache exists
    available_files = list(CACHE_DIR.glob("*.parquet"))
    if not available_files:
        print(f"[FATAL] No Parquet cache files found in {CACHE_DIR}")
        return {"error": "No cache files"}
    print(f"  Cache: {len(available_files)} files in {CACHE_DIR}")

    # Install monkey-patch
    print("  Installing fetch_ohlcv monkey-patch...")
    orig_fetch = _install_monkey_patch()

    # Import BT functions from app (after monkey-patch)
    try:
        from app import run_scalp_backtest, run_daytrade_backtest, run_1h_backtest
        bt_funcs = {
            "run_scalp_backtest": run_scalp_backtest,
            "run_daytrade_backtest": run_daytrade_backtest,
            "run_1h_backtest": run_1h_backtest,
        }
    except ImportError as e:
        print(f"[FATAL] Cannot import BT functions from app: {e}")
        _restore_monkey_patch(orig_fetch)
        return {"error": f"Import failed: {e}"}

    all_results = []
    total_combinations = 0
    errors = []
    t_start = time.time()

    for mode_name in modes:
        cfg = MODE_CONFIG.get(mode_name)
        if cfg is None:
            print(f"  [WARN] Unknown mode: {mode_name}")
            continue

        bt_func = bt_funcs.get(cfg["func_name"])
        if bt_func is None:
            print(f"  [WARN] BT function not found: {cfg['func_name']}")
            continue

        intervals = cfg["intervals"]
        # Filter intervals by user-specified TFs
        if timeframes:
            intervals = {k: v for k, v in intervals.items() if k in timeframes}
        if not intervals:
            continue

        mode_pairs = [p for p in cfg["pairs"] if p in pairs]

        for pair in mode_pairs:
            symbol = PAIRS[pair]
            for tf, lookback_days in intervals.items():
                total_combinations += 1
                print(f"\n  [{mode_name}] {pair} / {tf} (lookback={lookback_days}d)...")

                # Load and register cached data
                try:
                    df = load_parquet(pair, tf)
                    _setup_patch(pair, tf, df)

                    # For scalp mode, also preload 5m data if running 1m
                    if mode_name == "scalp" and tf == "1m":
                        try:
                            df_5m = load_parquet(pair, "5m")
                            _patch_cache[(symbol, "5m")] = df_5m
                        except FileNotFoundError:
                            pass

                except FileNotFoundError as e:
                    print(f"  [SKIP] {e}")
                    errors.append({"pair": pair, "tf": tf, "mode": mode_name,
                                   "error": str(e)})
                    continue

                # Run BT
                try:
                    combo_results = scan_combination(
                        bt_func, symbol, pair, tf, lookback_days)
                    all_results.extend(combo_results)
                    n_strats = len(combo_results)
                    n_trades = sum(r["n"] for r in combo_results)
                    print(f"    -> {n_strats} strategies, {n_trades} total trades")
                except Exception as e:
                    print(f"  [ERROR] {pair}/{tf}/{mode_name}: {e}")
                    traceback.print_exc()
                    errors.append({"pair": pair, "tf": tf, "mode": mode_name,
                                   "error": str(e)})
                finally:
                    _clear_patch()

    # Restore original fetch
    _restore_monkey_patch(orig_fetch)

    elapsed = time.time() - t_start
    print(f"\n  Scan complete in {elapsed:.1f}s")

    # ── Filter by min N ──
    filtered = [r for r in all_results if r["n"] >= min_n]
    print(f"  Total strategy results: {len(all_results)}, after N>={min_n} filter: {len(filtered)}")

    # ── Bonferroni correction ──
    n_tests = max(len(filtered), 1)
    alpha_bonf = 0.05 / n_tests
    print(f"  Bonferroni threshold: p < {alpha_bonf:.6f} (0.05 / {n_tests})")

    for r in filtered:
        # Binomial test: is WR significantly above breakeven?
        p_val = _binomial_pvalue(r["wins"], r["n"], r["be_wr"])
        r["p_value"] = round(p_val, 6)
        r["bonferroni_significant"] = p_val < alpha_bonf

        # Recommendation
        if r["bonferroni_significant"] and r.get("wf_stable") is True and r["ev"] > 0:
            r["recommendation"] = "STRONG"
        elif r["ev"] > 0 and r["pf"] > 1.0 and r["n"] >= 20:
            r["recommendation"] = "MODERATE"
        elif r["ev"] > 0:
            r["recommendation"] = "WEAK"
        else:
            r["recommendation"] = "AVOID"

    # Sort by recommendation strength, then by EV
    rec_order = {"STRONG": 0, "MODERATE": 1, "WEAK": 2, "AVOID": 3}
    filtered.sort(key=lambda r: (rec_order.get(r["recommendation"], 9), -r["ev"]))

    sig_count = sum(1 for r in filtered if r.get("bonferroni_significant"))

    # ── Build output ──
    output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "total_combinations": total_combinations,
        "total_strategy_results": len(all_results),
        "filtered_results": len(filtered),
        "bonferroni_alpha": round(alpha_bonf, 8),
        "significant_after_bonferroni": sig_count,
        "errors": errors,
        "results": filtered,
    }

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Results saved to {OUTPUT_PATH}")

    # ── Print summary table ──
    _print_summary(filtered, sig_count, total_combinations, alpha_bonf)

    return output


def _print_summary(results, sig_count, total_combos, alpha):
    """Print a human-readable summary table to stdout."""
    print("\n" + "=" * 110)
    print("  SCAN SUMMARY")
    print(f"  Combinations tested: {total_combos}")
    print(f"  Bonferroni significant: {sig_count}")
    print("=" * 110)

    if not results:
        print("  No results to display.")
        return

    # Header
    hdr = (f"{'Rec':>6s}  {'Strategy':<30s}  {'Pair':<8s}  {'Mode':<10s}  "
           f"{'TF':<4s}  {'N':>5s}  {'WR%':>6s}  {'EV':>7s}  "
           f"{'PF':>6s}  {'PnL':>8s}  {'Sharpe':>7s}  {'WF':>3s}  {'Bonf':>4s}")
    print(hdr)
    print("-" * 110)

    for r in results:
        wf_str = "Y" if r.get("wf_stable") is True else ("N" if r.get("wf_stable") is False else "-")
        bonf_str = "*" if r.get("bonferroni_significant") else ""
        sharpe_str = f"{r['sharpe']:.2f}" if r.get("sharpe") is not None else "-"
        rec = r.get("recommendation", "?")

        line = (f"{rec:>6s}  {r['strategy']:<30s}  {r['pair']:<8s}  {r['mode']:<10s}  "
                f"{r['tf']:<4s}  {r['n']:>5d}  {r['wr']:>5.1f}%  {r['ev']:>7.4f}  "
                f"{r['pf']:>6.3f}  {r['pnl']:>8.3f}  {sharpe_str:>7s}  {wf_str:>3s}  {bonf_str:>4s}")
        print(line)

    print("=" * 110)
    print(f"  * = Bonferroni significant (p < {alpha:.6f})")
    print(f"  WF = Walk-Forward stable (EV+ in >= 2/3 windows)")
    print()


# ══════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BT Scanner: scan all strategies x pairs x timeframes")
    parser.add_argument("--pairs", type=str, default=None,
                        help="Comma-separated pairs (e.g. USD_JPY,EUR_USD)")
    parser.add_argument("--tf", type=str, default=None,
                        help="Comma-separated timeframes (e.g. 15m,1h)")
    parser.add_argument("--mode", type=str, default=None,
                        help="Comma-separated modes (e.g. daytrade,scalp)")
    parser.add_argument("--min-n", type=int, default=5,
                        help="Minimum trade count to include (default: 5)")
    args = parser.parse_args()

    pairs = args.pairs.split(",") if args.pairs else None
    tfs = args.tf.split(",") if args.tf else None
    modes = args.mode.split(",") if args.mode else None

    run_full_scan(pairs=pairs, timeframes=tfs, modes=modes, min_n=args.min_n)


if __name__ == "__main__":
    main()
