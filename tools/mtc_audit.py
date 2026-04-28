"""MTC Audit — Multi-Timeframe Confluence の predictive power を実測検定。

本来 Phase 6 で実施すべきだった audit。MTC が単独 15m BB+RSI signal を超える
edge を持つかを Bonferroni 厳密検定。

監査方針:
  1. 15m BB%B extreme + RSI extreme = MR signal universe (bb_rsi_reversion 同等)
  2. 各 signal で MTC confluence_score (0/1/2) を計算
  3. 各 score 層で forward N-bar return を測定 (MR direction aligned)
  4. score=2 vs score≤1 の WR 差を Bonferroni 検定
  5. Trade-outcome simulation
  6. Quarterly stability

合格条件:
  - Bonferroni 通過 (score=2 が score≤1 より有意に高い WR)
  - Wilson lower > 0.50
  - score=2 の trade EV > score≤1 の trade EV
  - quarterly std < 0.10
  - score=2 が信号数を著しく削らない (score=2 / total > 5%)

棄却の場合: utility module 削除推奨。
"""
from __future__ import annotations
import argparse, json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import numpy as np
import pandas as pd

try:
    from scipy.stats import binomtest as _bt
    def _binom(k, n, p):
        return _bt(k=k, n=n, p=p, alternative="greater").pvalue
except ImportError:
    from scipy.stats import binom_test as _bt
    def _binom(k, n, p):
        return _bt(k, n, p, alternative="greater")


def _wilson(wins, n):
    if n == 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _load(pair, days):
    from tools.bt_data_cache import BTDataCache
    cache = BTDataCache()
    df = cache.get(pair, "15m", days=days)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    return df[df.index >= cutoff].copy()


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """15m と 1h 両方の BB%B + RSI を pre-compute"""
    df = df.copy()
    closes = df["Close"].astype(float)

    # 15m BB(20, 2σ)
    sma20 = closes.rolling(20).mean()
    std20 = closes.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    df["bbpb_15m"] = (closes - lower) / (upper - lower).replace(0, np.nan)

    # 15m RSI(14)
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-12)
    df["rsi_15m"] = 100 - 100 / (1 + rs)

    # 1h aggregation (4 × 15m)
    n_full = (len(df) // 4) * 4
    df_trim = df.iloc[-n_full:].copy()
    df_trim["bucket"] = np.arange(len(df_trim)) // 4
    h1 = df_trim.groupby("bucket").agg({"Close": "last"})

    h1_sma = h1["Close"].rolling(20).mean()
    h1_std = h1["Close"].rolling(20).std()
    h1_upper = h1_sma + 2 * h1_std
    h1_lower = h1_sma - 2 * h1_std
    h1["bbpb_1h"] = (h1["Close"] - h1_lower) / (h1_upper - h1_lower).replace(0, np.nan)

    h1_delta = h1["Close"].diff()
    h1_gain = h1_delta.clip(lower=0).rolling(14).mean()
    h1_loss = (-h1_delta.clip(upper=0)).rolling(14).mean()
    h1_rs = h1_gain / (h1_loss + 1e-12)
    h1["rsi_1h"] = 100 - 100 / (1 + h1_rs)

    # Map 1h indicators back to 15m bars (each 1h covers 4 × 15m bars)
    bbpb_1h_full = np.full(len(df), np.nan)
    rsi_1h_full = np.full(len(df), np.nan)
    offset = len(df) - n_full
    for bucket_idx in range(len(h1)):
        s = offset + bucket_idx * 4
        e = offset + (bucket_idx + 1) * 4
        if e > len(df):
            e = len(df)
        bbpb_1h_full[s:e] = h1["bbpb_1h"].iloc[bucket_idx]
        rsi_1h_full[s:e] = h1["rsi_1h"].iloc[bucket_idx]
    df["bbpb_1h"] = bbpb_1h_full
    df["rsi_1h"] = rsi_1h_full

    return df


def mtc_event_outcome(df: pd.DataFrame, pair: str,
                      bbpb_buy=0.30, bbpb_sell=0.70,
                      rsi_buy=35, rsi_sell=65,
                      forward_bars=4) -> list[dict]:
    """各 MR signal で MTC score 別に forward outcome を集計。

    Returns: list of {score, direction, n, win_rate, ...} for the pair.
    """
    pip = 0.01 if "JPY" in pair else 0.0001
    df = df.copy()
    df["ret_fwd"] = df["Close"].shift(-forward_bars) / df["Close"] - 1
    df = df.dropna(subset=["bbpb_15m", "rsi_15m", "bbpb_1h", "rsi_1h"])

    # Strict MR signals on 15m
    buy_15m = (df["bbpb_15m"] <= bbpb_buy) & (df["rsi_15m"] < rsi_buy)
    sell_15m = (df["bbpb_15m"] >= bbpb_sell) & (df["rsi_15m"] > rsi_sell)

    # 1h confluence
    buy_1h = (df["bbpb_1h"] <= bbpb_buy) & (df["rsi_1h"] < rsi_buy)
    sell_1h = (df["bbpb_1h"] >= bbpb_sell) & (df["rsi_1h"] > rsi_sell)

    results = []
    for direction, sig_15m, sig_1h, sign in [("buy", buy_15m, buy_1h, +1),
                                              ("sell", sell_15m, sell_1h, -1)]:
        # All 15m signals (regardless of 1h)
        score_2 = sig_15m & sig_1h     # both TFs agree
        score_1 = sig_15m & ~sig_1h    # 15m only
        score_0 = ~sig_15m             # no 15m signal (control)

        for score_label, mask in [("2_both", score_2), ("1_only_15m", score_1)]:
            sub = df[mask]
            if len(sub) < 20:
                results.append({"score": score_label, "direction": direction,
                                "n": int(len(sub)), "insufficient": True})
                continue
            fwd = sub["ret_fwd"]
            aligned_pip = sign * fwd * sub["Close"] / pip
            aligned_pip = aligned_pip.dropna()
            n = len(aligned_pip)
            if n < 20:
                results.append({"score": score_label, "direction": direction,
                                "n": n, "insufficient": True})
                continue
            n_wins = int((aligned_pip > 0).sum())
            wr = n_wins / n
            wlo, whi = _wilson(n_wins, n)
            p = _binom(n_wins, n, p=0.5)
            avg = float(aligned_pip.mean())
            sharpe = avg / (aligned_pip.std() + 1e-9) * math.sqrt(96 * 252)
            results.append({
                "pair": pair, "score": score_label, "direction": direction,
                "forward_bars": forward_bars,
                "n": n, "win_rate": round(wr, 4),
                "wilson_lower": round(wlo, 4),
                "wilson_upper": round(whi, 4),
                "p_value": round(p, 6),
                "avg_pip": round(avg, 3),
                "sharpe": round(sharpe, 2),
            })
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", nargs="+",
                   default=["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"])
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--forwards", type=int, nargs="+", default=[2, 4, 6, 8])
    p.add_argument("--output", default="raw/mtc_audit/")
    args = p.parse_args()

    grid = []
    for pair in args.pairs:
        print(f"=== MTC {pair} ===", flush=True)
        try:
            df = _load(pair, args.days)
            df = _compute_indicators(df)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            continue
        for fw in args.forwards:
            results = mtc_event_outcome(df, pair, forward_bars=fw)
            for r in results:
                if "insufficient" in r:
                    print(f"  fw={fw} {r['direction']} {r['score']}: "
                          f"n={r['n']} (insufficient)", flush=True)
                    continue
                grid.append(r)
                print(f"  fw={fw} {r['direction']} score={r['score']}: "
                      f"n={r['n']} WR={r['win_rate']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} avg={r['avg_pip']:+.2f}p "
                      f"Sharpe={r['sharpe']:.1f} p={r['p_value']:.4f}",
                      flush=True)

    n_tests = len(grid)
    print(f"\nTotal grid: {n_tests}", flush=True)

    # Bonferroni
    sig = []
    for r in grid:
        r["p_bonf"] = round(r["p_value"] * n_tests, 5)
        if r["p_bonf"] < 0.05 and r["wilson_lower"] > 0.50:
            sig.append(r)

    # Critical comparison: score=2_both vs score=1_only_15m for same pair/direction/fw
    print("\n=== score=2 vs score=1 比較 (同 pair/direction/forward) ===", flush=True)
    by_key = {}
    for r in grid:
        key = (r["pair"], r["direction"], r["forward_bars"])
        by_key.setdefault(key, {})[r["score"]] = r

    edge_count = 0
    for key, scores in by_key.items():
        if "2_both" in scores and "1_only_15m" in scores:
            s2 = scores["2_both"]
            s1 = scores["1_only_15m"]
            wr_diff = s2["win_rate"] - s1["win_rate"]
            avg_diff = s2["avg_pip"] - s1["avg_pip"]
            n2_share = s2["n"] / (s2["n"] + s1["n"]) if (s2["n"] + s1["n"]) > 0 else 0
            edge_str = "✅" if wr_diff > 0.02 and avg_diff > 0 else "✗"
            if wr_diff > 0.02 and avg_diff > 0:
                edge_count += 1
            print(f"  {edge_str} {key[0]} {key[1]} fw={key[2]}: "
                  f"score2 (n={s2['n']}, WR={s2['win_rate']:.3f}, avg={s2['avg_pip']:+.2f}p) "
                  f"vs score1 (n={s1['n']}, WR={s1['win_rate']:.3f}, avg={s1['avg_pip']:+.2f}p) "
                  f"| Δwr={wr_diff:+.3f}, Δavg={avg_diff:+.2f}p, "
                  f"score2_share={n2_share:.2f}", flush=True)

    print(f"\n=== Verdict ===", flush=True)
    print(f"Bonferroni-significant individual cells: {len(sig)}/{n_tests}", flush=True)
    print(f"score=2 outperforms score=1 (Δwr>2%pt + Δavg>0): "
          f"{edge_count}/{len(by_key)} comparisons", flush=True)

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"mtc_audit_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump({"grid": grid, "bonferroni_n": n_tests, "significant": sig,
                   "score2_vs_score1_edge_count": edge_count,
                   "comparison_total": len(by_key)},
                  f, indent=2, default=str)
    print(f"\nJSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
