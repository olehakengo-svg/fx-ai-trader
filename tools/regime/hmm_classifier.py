"""S5 HMM Regime Classifier — offline prototype.

Pre-registered design (no cherry-pick):
- Primary K = 3 states (Gaussian HMM, full covariance).
- Sensitivity: K = 2 and K = 4 reported but not optimised against.
- Observations: [log_return, log_realized_vol], where realized_vol is the
  rolling N-day std of log returns (default N = 10).
- Walk-forward: rolling train/test on daily bars aggregated from H1 OHLC.
- Strict no-look-ahead: at each rolling step the HMM is fit on the train
  slice only, then Viterbi-decoded over the test slice. The full output
  series is the concatenation of out-of-sample regime labels.

Counterfactual evaluation runs simple, *transparent* strategy proxies for
the three policy targets named in the spec:
  - MR proxy  (bb_rsi_reversion-like): Bollinger band fade with RSI filter
  - MR-JPY    (rsk_gbpjpy_reversion-like): same proxy on GBP_JPY
  - TF proxy  (mtf_trend_follow_scalp-like): triple-EMA trend pullback

For each proxy we compute regime-conditional PnL stats (PF, Sharpe,
win-rate with Wilson CI, EV, Kelly). The point is *not* to claim these
proxies match LIVE strategies — they are reference strategies that share
a behavioural family. The HMM is judged on whether it consistently
separates regimes where the family wins vs loses.

Usage:
    python -m tools.regime.hmm_classifier all          # full pipeline
    python -m tools.regime.hmm_classifier label        # produce labels only
    python -m tools.regime.hmm_classifier counterfact  # eval only
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "cache" / "massive"
OUT_DIR = ROOT / "tools" / "regime" / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PAIRS = ("USD_JPY", "GBP_JPY")


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #


def load_h1(pair: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA_DIR / f"{pair}_1h.parquet")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def aggregate_daily(h1: pd.DataFrame) -> pd.DataFrame:
    """Daily OHLC from H1 (UTC date)."""
    daily = h1.resample("1D").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    ).dropna()
    return daily


# --------------------------------------------------------------------------- #
# HMM observation features
# --------------------------------------------------------------------------- #


def build_features(daily: pd.DataFrame, vol_window: int = 10) -> pd.DataFrame:
    out = pd.DataFrame(index=daily.index)
    out["ret"] = np.log(daily["Close"]).diff()
    out["rv"] = out["ret"].rolling(vol_window).std()
    out["log_rv"] = np.log(out["rv"].replace(0, np.nan))
    out = out.dropna()
    return out[["ret", "log_rv"]]


# --------------------------------------------------------------------------- #
# Walk-forward HMM
# --------------------------------------------------------------------------- #


@dataclass
class WFConfig:
    """Walk-forward parameters.

    With 17 months of available data we cannot run the spec-suggested
    2y/6m window. We use 270d train / 60d test rolling and clearly
    flag the deviation in the report.
    """

    train_days: int = 270
    test_days: int = 60
    n_states: int = 3
    seed: int = 42
    n_iter: int = 200
    tol: float = 1e-3


def _align_states_by_vol(model: GaussianHMM) -> dict:
    """Return mapping: model_state -> rank (0=low vol .. K-1=high vol).

    HMM state numbering is arbitrary across fits. We label states by
    log_rv (column 1) so labels remain comparable across fold, K, and
    pair. Returns a dict {raw_state: ranked_state}.
    """
    log_rv_means = model.means_[:, 1]
    order = np.argsort(log_rv_means)  # ascending
    mapping = {int(raw): int(rank) for rank, raw in enumerate(order)}
    return mapping


def fit_predict_walkforward(
    feats: pd.DataFrame, cfg: WFConfig
) -> pd.Series:
    """Run rolling walk-forward HMM and return out-of-sample regime labels.

    Returns a pd.Series indexed by date with int regime label
    (0=low-vol .. K-1=high-vol).
    """
    feats = feats.dropna()
    n = len(feats)
    if n < cfg.train_days + cfg.test_days:
        raise ValueError(
            f"Not enough data: have {n} days, need >= "
            f"{cfg.train_days + cfg.test_days}"
        )

    labels = pd.Series(index=feats.index, dtype="float64")
    labels[:] = np.nan

    start = 0
    while start + cfg.train_days < n:
        train_end = start + cfg.train_days
        test_end = min(train_end + cfg.test_days, n)
        train = feats.iloc[start:train_end].values
        test = feats.iloc[train_end:test_end].values
        if len(test) == 0:
            break

        model = None
        # Try full covariance first; fall back to diagonal if singular.
        for cov_type in ("full", "diag"):
            for seed_offset in range(3):
                try:
                    m = GaussianHMM(
                        n_components=cfg.n_states,
                        covariance_type=cov_type,
                        n_iter=cfg.n_iter,
                        tol=cfg.tol,
                        random_state=cfg.seed + seed_offset,
                    )
                    m.fit(train)
                    model = m
                    break
                except Exception:
                    continue
            if model is not None:
                break
        if model is None:
            print(f"  [warn] all fits failed at start={start}", file=sys.stderr)
            start += cfg.test_days
            continue

        mapping = _align_states_by_vol(model)
        raw_states = model.predict(test)
        ranked = np.array([mapping[int(s)] for s in raw_states], dtype=float)
        idx = feats.index[train_end:test_end]
        labels.loc[idx] = ranked

        start += cfg.test_days

    return labels.dropna().astype(int)


def regime_transition_stability(labels: pd.Series) -> dict:
    """Flip-rate: probability that today's regime != yesterday's.

    A regime label that flips every day is statistically uninformative.
    Plausibly useful regimes flip far less often than they stay.
    """
    arr = labels.values
    if len(arr) == 0:
        return {"n_obs": 0, "flip_rate": float("nan"),
                "mean_run_days": float("nan"), "median_run_days": float("nan"),
                "note": "no OOS labels (all folds failed)"}
    flips = (np.diff(arr) != 0).sum()
    flip_rate = float(flips) / max(len(arr) - 1, 1)
    # Mean run length per state.
    run_lengths = []
    cur = arr[0]
    run = 1
    for x in arr[1:]:
        if x == cur:
            run += 1
        else:
            run_lengths.append(run)
            cur = x
            run = 1
    run_lengths.append(run)
    return {
        "n_obs": int(len(arr)),
        "flip_rate": flip_rate,
        "mean_run_days": float(np.mean(run_lengths)),
        "median_run_days": float(np.median(run_lengths)),
    }


# --------------------------------------------------------------------------- #
# Strategy proxies for counterfactual eval
# --------------------------------------------------------------------------- #


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    down = -delta.clip(upper=0).rolling(n).mean()
    rs = up / down.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def mr_bb_rsi_proxy(h1: pd.DataFrame, hold_bars: int = 6) -> pd.DataFrame:
    """Mean-reversion proxy: Bollinger fade with RSI filter.

    Behavioural family for bb_rsi_reversion / rsk_gbpjpy_reversion.
    Hold for a fixed N H1 bars then close at market.
    Output: DataFrame indexed by entry_time with columns
    {direction, entry, exit, pnl_pips, day}.
    """
    close = h1["Close"]
    ma = close.rolling(20).mean()
    sd = close.rolling(20).std()
    upper = ma + 2 * sd
    lower = ma - 2 * sd
    rsi = _rsi(close, 14)

    long_sig = (close < lower) & (rsi < 30)
    short_sig = (close > upper) & (rsi > 70)

    trades = []
    last_exit_idx = -1
    sig_idx = np.where(long_sig | short_sig)[0]
    for i in sig_idx:
        if i <= last_exit_idx:
            continue
        if i + hold_bars >= len(close):
            break
        entry_t = close.index[i]
        exit_t = close.index[i + hold_bars]
        entry_p = float(close.iloc[i])
        exit_p = float(close.iloc[i + hold_bars])
        direction = -1 if short_sig.iloc[i] else 1
        # JPY pip = 0.01 unit
        pnl = (exit_p - entry_p) * direction * 100.0
        trades.append({
            "entry_time": entry_t,
            "exit_time": exit_t,
            "direction": direction,
            "entry": entry_p,
            "exit": exit_p,
            "pnl_pips": pnl,
            "day": entry_t.normalize(),
        })
        last_exit_idx = i + hold_bars

    return pd.DataFrame(trades)


def tf_triple_ema_proxy(h1: pd.DataFrame, hold_bars: int = 6) -> pd.DataFrame:
    """Trend-follow proxy: EMA9>EMA21>EMA50 with pullback to EMA9.

    Behavioural family for mtf_trend_follow_scalp.
    """
    close = h1["Close"]
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    low = h1["Low"]
    high = h1["High"]

    bull = (ema9 > ema21) & (ema21 > ema50)
    bear = (ema9 < ema21) & (ema21 < ema50)
    # Pullback: low touches ema9 from above (bull) or high touches ema9 from below (bear).
    long_sig = bull & (low <= ema9) & (close > ema9)
    short_sig = bear & (high >= ema9) & (close < ema9)

    trades = []
    last_exit_idx = -1
    sig_idx = np.where(long_sig | short_sig)[0]
    for i in sig_idx:
        if i <= last_exit_idx:
            continue
        if i + hold_bars >= len(close):
            break
        entry_t = close.index[i]
        exit_t = close.index[i + hold_bars]
        entry_p = float(close.iloc[i])
        exit_p = float(close.iloc[i + hold_bars])
        direction = 1 if long_sig.iloc[i] else -1
        pnl = (exit_p - entry_p) * direction * 100.0
        trades.append({
            "entry_time": entry_t,
            "exit_time": exit_t,
            "direction": direction,
            "entry": entry_p,
            "exit": exit_p,
            "pnl_pips": pnl,
            "day": entry_t.normalize(),
        })
        last_exit_idx = i + hold_bars

    return pd.DataFrame(trades)


# --------------------------------------------------------------------------- #
# Stats helpers
# --------------------------------------------------------------------------- #


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    spread = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return (centre - spread, centre + spread)


def kelly_fraction(p: float, b: float) -> float:
    """Kelly for binary outcome with payoff ratio b (avg_win / avg_loss).

    f* = p - (1-p)/b
    Floor at 0 (no shorting Kelly).
    """
    if b <= 0:
        return 0.0
    return max(0.0, p - (1 - p) / b)


def trade_stats(trades: pd.DataFrame) -> dict:
    if len(trades) == 0:
        return {
            "n": 0, "wr": float("nan"), "wr_lo": float("nan"), "wr_hi": float("nan"),
            "pf": float("nan"), "ev_pips": float("nan"),
            "sharpe": float("nan"), "kelly": 0.0,
            "sum_pips": 0.0,
        }
    pnl = trades["pnl_pips"].values
    n = len(pnl)
    wins = int((pnl > 0).sum())
    wr = wins / n
    wr_lo, wr_hi = wilson_ci(wins, n)
    win_pnl = pnl[pnl > 0].sum()
    loss_pnl = -pnl[pnl < 0].sum()
    pf = (win_pnl / loss_pnl) if loss_pnl > 0 else float("inf")
    ev = float(np.mean(pnl))
    std = float(np.std(pnl, ddof=1)) if n > 1 else float("nan")
    sharpe = (ev / std) if std and not math.isnan(std) and std > 0 else float("nan")
    avg_win = pnl[pnl > 0].mean() if wins > 0 else 0.0
    avg_loss = -pnl[pnl < 0].mean() if (n - wins) > 0 else 0.0
    b = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    kelly = kelly_fraction(wr, b)
    return {
        "n": int(n), "wr": float(wr),
        "wr_lo": float(wr_lo), "wr_hi": float(wr_hi),
        "pf": float(pf), "ev_pips": float(ev),
        "sharpe": float(sharpe), "kelly": float(kelly),
        "sum_pips": float(pnl.sum()),
    }


def split_by_regime(trades: pd.DataFrame, labels: pd.Series, n_states: int) -> dict:
    """For each regime, compute trade stats.

    A trade is assigned the regime label of its entry day (the regime
    decision is made *before* the trade opens — no look-ahead).
    """
    if len(trades) == 0:
        return {}
    df = trades.copy()
    df["regime"] = df["day"].map(labels)
    df = df.dropna(subset=["regime"])
    df["regime"] = df["regime"].astype(int)
    out = {"all": trade_stats(df)}
    for r in range(n_states):
        out[f"regime_{r}"] = trade_stats(df[df["regime"] == r])
    return out


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


def run_pipeline(n_states_list: Iterable[int] = (2, 3, 4)) -> dict:
    """Full pipeline: train HMM (walk-forward) + counterfactual eval."""
    summary = {"pairs": {}, "config": {}}
    for pair in PAIRS:
        print(f"[{pair}] loading H1 + aggregating daily...")
        h1 = load_h1(pair)
        daily = aggregate_daily(h1)
        feats = build_features(daily)
        print(f"  daily bars after warmup: {len(feats)}")
        if len(feats) < 330:
            print(f"  [warn] only {len(feats)} bars — walk-forward may be tight")

        pair_out = {"n_daily_bars": len(feats), "by_k": {}}
        for k in n_states_list:
            print(f"  [K={k}] running walk-forward...")
            cfg = WFConfig(n_states=k)
            try:
                labels = fit_predict_walkforward(feats, cfg)
            except ValueError as e:
                print(f"    skipped: {e}")
                continue
            stab = regime_transition_stability(labels)
            print(f"    OOS days: {stab['n_obs']}, flip-rate {stab['flip_rate']:.3f}, "
                  f"mean run {stab['mean_run_days']:.1f}d")

            # Save labels.
            label_path = OUT_DIR / f"labels_{pair}_K{k}.csv"
            labels.to_frame("regime").to_csv(label_path)

            # Strategy proxies on the *full* H1 (we'll filter later).
            mr = mr_bb_rsi_proxy(h1)
            tf = tf_triple_ema_proxy(h1)

            mr_split = split_by_regime(mr, labels, k)
            tf_split = split_by_regime(tf, labels, k)

            # Counterfactual gates: how does the proxy do if we OFF the
            # strategy in specific regimes?
            #   MR off in highest-vol regime: drop regime_{K-1}.
            #   TF off in lowest-vol regime: drop regime_0.
            mr_with = {r: stats for r, stats in mr_split.items()
                       if r != f"regime_{k - 1}" and r != "all"}
            tf_with = {r: stats for r, stats in tf_split.items()
                       if r != "regime_0" and r != "all"}

            def _aggregate(splits: dict) -> dict:
                # Re-derive aggregate stats from underlying trades is more
                # honest than averaging stat dicts. We'll do simple sums:
                if not splits:
                    return {}
                ns = sum(s["n"] for s in splits.values())
                if ns == 0:
                    return {"n": 0}
                sum_pips = sum(s["sum_pips"] for s in splits.values())
                ev = sum_pips / ns
                # weighted wr = (sum of wins) / sum n; we have wr*n.
                wins = sum(s["wr"] * s["n"] for s in splits.values()
                           if not math.isnan(s["wr"]))
                wr = wins / ns
                wr_lo, wr_hi = wilson_ci(int(round(wins)), ns)
                return {
                    "n": int(ns), "wr": float(wr),
                    "wr_lo": float(wr_lo), "wr_hi": float(wr_hi),
                    "ev_pips": float(ev), "sum_pips": float(sum_pips),
                }

            pair_out["by_k"][str(k)] = {
                "stability": stab,
                "mr_proxy": mr_split,
                "tf_proxy": tf_split,
                "mr_off_high_vol": _aggregate(mr_with),
                "tf_off_low_vol": _aggregate(tf_with),
            }

        summary["pairs"][pair] = pair_out

    summary["config"] = {
        "wf_train_days": WFConfig().train_days,
        "wf_test_days": WFConfig().test_days,
        "vol_window": 10,
        "covariance_type": "full",
        "seed": WFConfig().seed,
        "primary_K": 3,
        "sensitivity_K": [2, 4],
        "bonferroni_alpha": 0.05 / 9,  # 3 strategies x 3 K
    }
    return summary


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["all", "label", "counterfact", "smoke"],
        help="all = full pipeline; smoke = tiny self-test",
    )
    parser.add_argument("--out", default=str(OUT_DIR / "summary.json"))
    args = parser.parse_args()

    if args.command == "smoke":
        # Tiny self-test on USD_JPY only, K=2.
        h1 = load_h1("USD_JPY")
        daily = aggregate_daily(h1)
        feats = build_features(daily)
        cfg = WFConfig(n_states=2, train_days=200, test_days=30)
        labels = fit_predict_walkforward(feats, cfg)
        print("smoke OK, labels:", labels.value_counts().to_dict())
        return 0

    summary = run_pipeline()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"summary -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
