"""Portfolio Kelly optimization — v1b + bb_rsi + vol_momentum 配分最適化

Objective:
  単体 v1b に全資金を賭けるのではなく、相関が低い既存 LIVE 戦略
  (bb_rsi_reversion, vol_momentum_scalp) と組み合わせた portfolio Kelly で
  combined Sharpe / Kelly を最大化する lot 配分を導出。

Mathematical foundation:
  Multivariate Kelly (Thorp 1969, Vince 1992):
    f* = Σ^(-1) · μ

  where:
    f* = optimal fraction vector (per strategy)
    Σ  = covariance matrix of strategy returns
    μ  = mean return vector

  Combined Sharpe:
    S_p = (w · μ) / √(w · Σ · w)

Data sources:
  - bb_rsi_reversion: production LIVE trades (N=234 USD_JPY)
  - vol_momentum_scalp: production LIVE trades (N=17 USD_JPY) — small N caveat
  - ma_trend_perfect (v1b): BT 180d trades (N=369) — proxy until LIVE accumulates

Output:
  - Pearson correlation matrix
  - Mean return / std per strategy
  - Optimal Kelly weights (Σ^-1 μ)
  - Recommended Quarter-Kelly lot allocation
  - Combined vs individual Sharpe comparison
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import math

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def load_render_live_trades(json_path: str, strats: set, instrument: str = "USD_JPY") -> pd.DataFrame:
    with open(json_path) as f:
        data = json.load(f)
    trades = data if isinstance(data, list) else data.get("trades", [])
    rows = []
    for t in trades:
        if t.get("instrument") != instrument:
            continue
        if t.get("is_shadow"):
            continue
        if t.get("entry_type") not in strats:
            continue
        et_time = t.get("entry_time")
        if not et_time:
            continue
        rows.append({
            "strategy": t["entry_type"],
            "entry_time": pd.Timestamp(et_time),
            "pnl_pips": float(t.get("pnl_pips") or 0),
            "outcome": t.get("close_reason", ""),
        })
    return pd.DataFrame(rows)


def load_v1b_bt_trades(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["entry_time"] = pd.to_datetime(df["ts"])
    df["strategy"] = df["strategy"]
    df["pnl_pips"] = df["pnl_pips"].astype(float)
    return df[["strategy", "entry_time", "pnl_pips"]]


def compute_daily_pnl(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot trades into daily PnL series per strategy."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["entry_time"], utc=True).dt.date
    daily = df.groupby(["date", "strategy"])["pnl_pips"].sum().unstack(fill_value=0.0)
    return daily


def compute_stats(returns: pd.Series) -> dict:
    if len(returns) < 5:
        return {"n": len(returns), "mean": 0, "std": 0, "sharpe": 0, "wr": 0, "kelly": 0}
    mean = float(returns.mean())
    std = float(returns.std(ddof=1))
    sharpe = (mean / std * math.sqrt(252)) if std > 0 else 0
    wr = float((returns > 0).mean())
    # Kelly approximation: Kelly ~ mean / variance for small returns
    var = std ** 2
    kelly = (mean / var) if var > 0 else 0
    return {
        "n": int(len(returns)),
        "mean": round(mean, 3),
        "std": round(std, 3),
        "sharpe": round(sharpe, 3),
        "wr": round(wr, 3),
        "kelly_singular": round(kelly, 3),  # single-strategy Kelly
    }


def portfolio_kelly(daily: pd.DataFrame, strats: list) -> dict:
    """Multivariate Kelly: f* = Σ^-1 μ."""
    sub = daily[strats].dropna(how="all").fillna(0.0)
    mu = sub.mean().values
    cov = sub.cov().values
    if cov.shape[0] < 2:
        return {"error": "insufficient strategies"}
    try:
        cov_inv = np.linalg.pinv(cov)
    except Exception as e:
        return {"error": f"singular cov: {e}"}
    f_star = cov_inv @ mu
    # Project to non-negative (Kelly with no shorting)
    f_pos = np.maximum(f_star, 0)
    if f_pos.sum() > 0:
        f_norm = f_pos / f_pos.sum()
    else:
        f_norm = np.zeros_like(f_pos)
    # Combined Sharpe with optimal weights
    w = f_norm
    port_mean = float(w @ mu)
    port_var = float(w @ cov @ w)
    port_std = math.sqrt(port_var) if port_var > 0 else 0
    port_sharpe = (port_mean / port_std * math.sqrt(252)) if port_std > 0 else 0
    # Individual Sharpes for comparison
    individual_sharpes = {}
    for s in strats:
        m = float(sub[s].mean())
        st = float(sub[s].std(ddof=1)) if sub[s].std(ddof=1) > 0 else 0
        individual_sharpes[s] = round((m / st * math.sqrt(252)) if st > 0 else 0, 3)
    return {
        "n_days_overlap": int(len(sub)),
        "raw_kelly": dict(zip(strats, [round(float(f), 3) for f in f_star])),
        "normalized_weights": dict(zip(strats, [round(float(f), 3) for f in f_norm])),
        "portfolio_mean_pip": round(port_mean, 3),
        "portfolio_std_pip": round(port_std, 3),
        "portfolio_sharpe_annual": round(port_sharpe, 3),
        "individual_sharpe_annual": individual_sharpes,
    }


def hr(t):
    print()
    print("═" * 78); print(t); print("═" * 78)


def section(t):
    print()
    print("─" * 78); print(t); print("─" * 78)


def main():
    hr("Portfolio Kelly Analysis — v1b + bb_rsi + vol_momentum")

    # Load LIVE data
    live = load_render_live_trades(
        "/tmp/render_trades.json",
        strats={"bb_rsi_reversion", "vol_momentum_scalp"},
    )
    print(f"LIVE trades loaded: {len(live)}")
    print(live.groupby("strategy").size())

    # Load v1b BT proxy
    # Auto-detect latest v1b 180d BT trades CSV
    import glob
    v1b_csvs = sorted(glob.glob("knowledge-base/raw/audits/ma_family_v1/USD_JPY_trades_*.csv"))
    if not v1b_csvs:
        raise SystemExit("No v1b BT trades CSV found")
    v1b = load_v1b_bt_trades(v1b_csvs[-1])
    v1b = v1b[v1b["strategy"] == "ma_trend_perfect"].copy()
    print(f"\nv1b BT trades (proxy): {len(v1b)}")

    all_trades = pd.concat([live, v1b], ignore_index=True)

    section("(1) Per-strategy stats (raw)")
    for s in ["bb_rsi_reversion", "vol_momentum_scalp", "ma_trend_perfect"]:
        sub = all_trades[all_trades["strategy"] == s]["pnl_pips"]
        print(f"  {s:25s} N={len(sub):4d}  mean={sub.mean():.3f}  std={sub.std():.3f}  "
              f"WR={(sub>0).mean()*100:.1f}%  PF={sub[sub>0].sum()/(-sub[sub<0].sum() if (sub<0).any() else 1):.2f}")

    section("(2) Daily PnL aggregation")
    daily = compute_daily_pnl(all_trades)
    print(f"  Date range: {daily.index.min()} → {daily.index.max()}")
    print(f"  Strategies: {list(daily.columns)}")
    print(f"  Days with any trade: {len(daily)}")
    print()
    print("  Daily stats:")
    for s in daily.columns:
        st = compute_stats(daily[s][daily[s] != 0])
        print(f"    {s:25s} active_days={st['n']:3d}  mean={st['mean']:.3f}  "
              f"std={st['std']:.3f}  Sharpe={st['sharpe']:.2f}  Kelly_s={st['kelly_singular']:.2f}")

    section("(3) Cross-strategy daily correlation matrix")
    corr = daily.corr()
    print(corr.round(3).to_string())

    section("(4) Portfolio Kelly (multivariate)")
    strats = list(daily.columns)
    result = portfolio_kelly(daily, strats)
    for k, v in result.items():
        print(f"  {k}: {v}")

    section("(5) Lot allocation recommendation")
    if "normalized_weights" in result:
        weights = result["normalized_weights"]
        port_sharpe = result["portfolio_sharpe_annual"]
        ind = result["individual_sharpe_annual"]
        max_ind = max(ind.values()) if ind else 0
        diversification_gain = (port_sharpe / max_ind - 1) if max_ind > 0 else 0
        print(f"  Combined portfolio Sharpe: {port_sharpe:.3f}")
        print(f"  Best individual Sharpe   : {max_ind:.3f}")
        print(f"  Diversification gain     : {diversification_gain*100:+.1f}%")
        print()
        print("  Quarter-Kelly recommendation (conservative scaling 0.25):")
        for s, w in weights.items():
            qk = w * 0.25
            print(f"    {s:25s} weight={w:.2f}  quarter_kelly_lot={qk:.3f}")

    print()
    print("Caveats:")
    print("  - vol_momentum_scalp N=17 LIVE — small sample, weight unreliable")
    print("  - ma_trend_perfect N=369 BT proxy — LIVE may diverge")
    print("  - Daily aggregation assumes intra-day hedge effects washed out")


if __name__ == "__main__":
    main()
