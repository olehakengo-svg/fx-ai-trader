#!/usr/bin/env python3
"""D1 Time-Series Momentum basket backtest (risk-premia harvest).

Pre-registration (LOCK 2026-06-08, .ai/plans/claude/20260608-2040-d1-tsmom-basket-pre-reg-bt.md):
  - Basket: 8 fixed G10 pairs (no post-hoc additions).
  - Signal: sign(close[t] / close[t-L] - 1) per pair, daily.
  - Primary hypothesis: L = 252 (12 months, Moskowitz-Ooi-Pedersen 2012). m=4 (L in {21,63,126,252}).
  - Sizing: inverse-vol equal-risk weights (realized 60d vol), positions = sign * weight.
  - Rebalance: monthly (first trading day). Hold constant within month. No TP/SL (hold to reversal).
  - Bonferroni m=4, alpha=0.05. Primary (252) must survive alone.
  - Walk-Forward: 3 contiguous OOS folds, report per-fold Sharpe + sign.

This is a risk-premia harvest (no prediction): we get paid to carry past-return sign with
diversification, not to forecast. Reports BOTH gross and net (friction) metrics because the
whole pivot thesis is that gross edge must clear friction (gross EV ~= -0.02 problem).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "massive"

# LOCKED basket (pre-reg) — do not add pairs post-hoc.
PAIRS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD",
    "USD_CAD", "USD_CHF", "NZD_USD", "EUR_JPY",
]
LOOKBACKS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}  # m=4
PRIMARY = "12m"
BONFERRONI_M = 4
BONFERRONI_ALPHA = 0.05
VOL_WINDOW = 60          # realized vol lookback (days) for inverse-vol weights
ANNUALIZER = 252

# Conservative round-trip friction in price fraction per unit notional rebalanced.
# Majors ~1.0-1.5 pip spread; JPY pairs ~1.5 pip. Use 0.00010 (1.0 pip on a 1.00 quote
# equiv) as a deliberately conservative blended estimate applied to turnover.
FRICTION_PER_TURNOVER = 0.00010


def load_closes() -> pd.DataFrame:
    cols = {}
    for p in PAIRS:
        fp = CACHE / f"{p}_1d.parquet"
        if not fp.exists():
            raise FileNotFoundError(f"missing D1 cache: {fp} (run fetch_massive_data --tf 1d)")
        df = pd.read_parquet(fp)
        cols[p] = df["Close"]
    closes = pd.DataFrame(cols).sort_index()
    # Align on common dates, forward-fill single missing prints (rare holiday mismatch).
    closes = closes.dropna(how="all").ffill().dropna()
    return closes


def build_positions(closes: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Monthly-rebalanced inverse-vol weighted TSMOM positions (lagged 1d, no lookahead)."""
    rets = closes.pct_change()
    signal = np.sign(closes / closes.shift(lookback) - 1.0)        # +1/-1/0 per pair, per day
    inv_vol = 1.0 / rets.rolling(VOL_WINDOW).std()
    inv_vol = inv_vol.replace([np.inf, -np.inf], np.nan)
    weights = inv_vol.div(inv_vol.sum(axis=1), axis=0)             # equal-risk, sum|w|=1
    raw_pos = signal * weights

    # Sample positions on the first trading day of each month, hold constant within month.
    month_key = raw_pos.index.tz_localize(None).to_period("M")
    is_rebal = pd.Series(month_key, index=raw_pos.index).ne(
        pd.Series(month_key, index=raw_pos.index).shift(1)
    )
    held = raw_pos.where(is_rebal).ffill()
    # Lag one day so a position formed from close[t] is applied to return[t+1].
    return held.shift(1).fillna(0.0)


def portfolio_returns(closes: pd.DataFrame, positions: pd.DataFrame):
    rets = closes.pct_change().fillna(0.0)
    gross = (positions * rets).sum(axis=1)
    turnover = positions.diff().abs().sum(axis=1).fillna(0.0)
    cost = turnover * FRICTION_PER_TURNOVER
    net = gross - cost
    return gross, net, turnover


def wilson_lower(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (centre - margin) / denom


def two_sided_p(t: float, dof: int) -> float:
    """Two-sided p-value for a t-stat. Uses a normal approx for large dof (D1, dof>>30)."""
    from statistics import NormalDist
    return 2 * (1 - NormalDist().cdf(abs(t)))


def metrics(daily: pd.Series, label: str) -> dict:
    daily = daily.dropna()
    n = len(daily)
    mean_d, std_d = daily.mean(), daily.std(ddof=1)
    sharpe = (mean_d / std_d) * math.sqrt(ANNUALIZER) if std_d > 0 else 0.0
    ann_ret = (1 + daily).prod() ** (ANNUALIZER / n) - 1 if n else 0.0
    equity = (1 + daily).cumprod()
    max_dd = float((equity / equity.cummax() - 1).min())
    calmar = ann_ret / abs(max_dd) if max_dd < 0 else float("inf")
    t_stat = mean_d / (std_d / math.sqrt(n)) if std_d > 0 else 0.0
    p_raw = two_sided_p(t_stat, n - 1)

    monthly = (1 + daily).resample("ME").prod() - 1
    wins = int((monthly > 0).sum())
    mn = len(monthly)
    pos = monthly[monthly > 0].sum()
    neg = monthly[monthly < 0].sum()
    pf = float(pos / abs(neg)) if neg < 0 else float("inf")
    kelly = (mean_d / (std_d ** 2)) if std_d > 0 else 0.0  # continuous Kelly fraction proxy

    return {
        "label": label,
        "days": n,
        "sharpe": round(sharpe, 3),
        "ann_return": round(ann_ret, 4),
        "max_dd": round(max_dd, 4),
        "calmar": round(calmar, 3),
        "t_stat": round(t_stat, 3),
        "p_raw": p_raw,
        "p_bonferroni": min(1.0, p_raw * BONFERRONI_M),
        "months": mn,
        "monthly_wr": round(wins / mn, 4) if mn else 0.0,
        "monthly_wr_wilson_lo": round(wilson_lower(wins, mn), 4),
        "profit_factor": round(pf, 3) if pf != float("inf") else None,
        "kelly_proxy": round(kelly, 4),
    }


def walk_forward(daily: pd.Series, folds: int = 3) -> list[dict]:
    daily = daily.dropna()
    idx = np.array_split(np.arange(len(daily)), folds)
    out = []
    for i, sl in enumerate(idx, 1):
        seg = daily.iloc[sl]
        std = seg.std(ddof=1)
        sharpe = (seg.mean() / std) * math.sqrt(ANNUALIZER) if std > 0 else 0.0
        out.append({
            "fold": i,
            "start": seg.index[0].date().isoformat(),
            "end": seg.index[-1].date().isoformat(),
            "sharpe": round(sharpe, 3),
            "total_return": round(float((1 + seg).prod() - 1), 4),
            "sign": "+" if seg.sum() > 0 else "-",
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "raw" / "bt-results" / "tsmom_basket_2026_06_08.json"))
    args = ap.parse_args()

    closes = load_closes()
    span = f"{closes.index[0].date()} → {closes.index[-1].date()} ({len(closes)} bars, {len(PAIRS)} pairs)"

    results = {}
    for name, L in LOOKBACKS.items():
        pos = build_positions(closes, L)
        gross, net, turnover = portfolio_returns(closes, pos)
        results[name] = {
            "lookback_days": L,
            "gross": metrics(gross, f"{name}_gross"),
            "net": metrics(net, f"{name}_net"),
            "avg_daily_turnover": round(float(turnover.mean()), 4),
            "walk_forward_net": walk_forward(net),
        }

    prim = results[PRIMARY]
    net = prim["net"]
    wf = prim["walk_forward_net"]
    wf_all_pos = all(f["sign"] == "+" for f in wf)
    verdict = (
        "SHADOW_CANDIDATE"
        if (net["p_bonferroni"] < BONFERRONI_ALPHA and wf_all_pos and net["sharpe"] > 0)
        else "NULL"
    )

    report = {
        "strategy": "d1_tsmom_basket",
        "pre_reg": ".ai/plans/claude/20260608-2040-d1-tsmom-basket-pre-reg-bt.md",
        "data_span": span,
        "pairs": PAIRS,
        "primary_lookback": PRIMARY,
        "bonferroni_m": BONFERRONI_M,
        "bonferroni_alpha": BONFERRONI_ALPHA,
        "friction_per_turnover": FRICTION_PER_TURNOVER,
        "results": results,
        "primary_net_verdict": verdict,
        "wf_all_positive": wf_all_pos,
    }

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    # Console summary
    print(f"\n=== D1 TSMOM Basket BT — {span} ===")
    hdr = f"{'L':>4} | {'Sharpe(g/n)':>13} | {'Ann(n)':>8} | {'maxDD':>7} | {'Calmar':>7} | {'t(n)':>6} | {'p_bonf':>7} | {'mWR_lo':>6}"
    print(hdr); print("-" * len(hdr))
    for name in LOOKBACKS:
        g, n = results[name]["gross"], results[name]["net"]
        star = " *primary" if name == PRIMARY else ""
        print(f"{name:>4} | {g['sharpe']:>6}/{n['sharpe']:<6} | {n['ann_return']:>8} | {n['max_dd']:>7} | "
              f"{n['calmar']:>7} | {n['t_stat']:>6} | {n['p_bonferroni']:>7.4f} | {n['monthly_wr_wilson_lo']:>6}{star}")
    print(f"\nPrimary ({PRIMARY}) net WF folds:")
    for f in wf:
        print(f"  fold{f['fold']} {f['start']}..{f['end']}  Sharpe={f['sharpe']:>6}  ret={f['total_return']:>8}  [{f['sign']}]")
    print(f"\nVERDICT (primary net): {verdict}  | WF all-positive: {wf_all_pos}")
    print(f"written: {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
