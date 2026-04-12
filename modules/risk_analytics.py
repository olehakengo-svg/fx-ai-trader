"""
Risk Analytics Module -- VaR/CVaR, Monte Carlo Ruin, Kelly, Correlation, P&L Attribution
========================================================================================

Production risk analytics for the FX AI Trader system.

Features:
  1. Historical VaR (95%/99%) + CVaR (Expected Shortfall)
  2. Monte Carlo Ruin Probability (Bootstrap)
  3. Kelly Fraction Calculator
  4. Strategy Correlation Matrix
  5. P&L Attribution (Alpha / Friction / Sizing)

Dependencies: numpy, pandas (pip-based, available in production)
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple


# =====================================================================
#  1. Historical VaR / CVaR
# =====================================================================

def calculate_var_cvar(pnl_list: List[float]) -> dict:
    """
    Historical VaR (95%, 99%) and CVaR (Expected Shortfall) from trade PnL data.

    Args:
        pnl_list: List of trade PnL values (pips). Losses are negative.

    Returns:
        dict with var95, var99, cvar95, n_trades, mean_pnl, std_pnl
        VaR values are reported as positive loss amounts (convention).
    """
    if not pnl_list or len(pnl_list) < 2:
        return {
            "var95": 0.0, "var99": 0.0, "cvar95": 0.0,
            "n_trades": len(pnl_list) if pnl_list else 0,
            "mean_pnl": 0.0, "std_pnl": 0.0,
            "insufficient": True,
        }

    arr = np.array(pnl_list, dtype=np.float64)
    n = len(arr)

    # VaR: 5th and 1st percentile of PnL distribution (left tail)
    var95_raw = float(np.percentile(arr, 5))
    var99_raw = float(np.percentile(arr, 1))

    # CVaR (Expected Shortfall): mean of losses beyond VaR95 threshold
    tail_mask = arr <= var95_raw
    if tail_mask.sum() > 0:
        cvar95 = float(np.mean(arr[tail_mask]))
    else:
        cvar95 = var95_raw

    return {
        "var95": round(-var95_raw, 2),     # positive = loss magnitude
        "var99": round(-var99_raw, 2),
        "cvar95": round(-cvar95, 2),       # positive = expected loss beyond VaR
        "n_trades": n,
        "mean_pnl": round(float(np.mean(arr)), 2),
        "std_pnl": round(float(np.std(arr, ddof=1)), 2) if n > 1 else 0.0,
        "insufficient": n < 20,
    }


# =====================================================================
#  2. Monte Carlo Ruin Probability
# =====================================================================

def monte_carlo_ruin(pnl_list: List[float],
                     initial_capital: float = 1000.0,
                     ruin_dd_pct: float = 0.50,
                     n_simulations: int = 10000,
                     n_trades_forward: int = 500,
                     seed: int = 42) -> dict:
    """
    Bootstrap Monte Carlo simulation for ruin probability.

    Resamples from actual trade PnLs to project equity curves forward.
    Ruin = drawdown exceeds ruin_dd_pct of initial capital.

    Args:
        pnl_list: List of historical trade PnL (pips).
        initial_capital: Starting capital in pips (default 1000).
        ruin_dd_pct: DD threshold defining ruin (default 50%).
        n_simulations: Number of MC paths (default 10000).
        n_trades_forward: Trades per simulation path (default 500).
        seed: Random seed for reproducibility.

    Returns:
        dict with ruin_probability, median_max_dd, worst_case_dd_99,
        expected_trades_to_ruin, median_final_equity
    """
    if not pnl_list or len(pnl_list) < 5:
        return {
            "ruin_probability": 0.0,
            "median_max_dd": 0.0,
            "worst_case_dd_99": 0.0,
            "expected_trades_to_ruin": float('inf'),
            "median_final_equity": initial_capital,
            "n_simulations": 0,
            "insufficient": True,
        }

    rng = np.random.RandomState(seed)
    pnl_arr = np.array(pnl_list, dtype=np.float64)
    ruin_threshold = initial_capital * ruin_dd_pct

    ruin_count = 0
    max_dds = np.zeros(n_simulations)
    final_equities = np.zeros(n_simulations)
    trades_to_ruin_list = []

    for i in range(n_simulations):
        # Bootstrap resample: draw n_trades_forward trades with replacement
        sampled = rng.choice(pnl_arr, size=n_trades_forward, replace=True)

        # Track equity curve
        equity = initial_capital
        peak = initial_capital
        max_dd = 0.0
        ruined = False
        ruin_trade = -1

        for j, pnl in enumerate(sampled):
            equity += pnl
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
            if not ruined and dd >= ruin_threshold:
                ruined = True
                ruin_trade = j + 1

        max_dds[i] = max_dd
        final_equities[i] = equity

        if ruined:
            ruin_count += 1
            trades_to_ruin_list.append(ruin_trade)

    ruin_prob = ruin_count / n_simulations
    median_max_dd = float(np.median(max_dds))
    worst_case_dd_99 = float(np.percentile(max_dds, 99))

    if trades_to_ruin_list:
        expected_trades_to_ruin = float(np.mean(trades_to_ruin_list))
    else:
        expected_trades_to_ruin = float('inf')

    return {
        "ruin_probability": round(ruin_prob, 4),
        "median_max_dd": round(median_max_dd, 2),
        "worst_case_dd_99": round(worst_case_dd_99, 2),
        "expected_trades_to_ruin": (round(expected_trades_to_ruin, 0)
                                    if expected_trades_to_ruin != float('inf')
                                    else None),
        "median_final_equity": round(float(np.median(final_equities)), 2),
        "n_simulations": n_simulations,
        "n_trades_forward": n_trades_forward,
        "ruin_dd_pct": ruin_dd_pct,
        "initial_capital": initial_capital,
        "insufficient": False,
    }


# =====================================================================
#  3. Kelly Fraction Calculator
# =====================================================================

def kelly_fraction(win_rate: float, avg_win: float,
                   avg_loss: float) -> dict:
    """
    Calculate Kelly fractions for position sizing.

    Args:
        win_rate: Win rate as decimal (e.g., 0.55 for 55%).
        avg_win: Average winning trade PnL (positive, pips).
        avg_loss: Average losing trade PnL (positive magnitude, pips).

    Returns:
        dict with full_kelly, half_kelly, quarter_kelly, edge, odds_ratio,
        recommendation (always half_kelly for production).
    """
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return {
            "full_kelly": 0.0,
            "half_kelly": 0.0,
            "quarter_kelly": 0.0,
            "edge": 0.0,
            "odds_ratio": 0.0,
            "win_rate": win_rate,
            "recommendation": "half_kelly",
            "recommended_fraction": 0.0,
        }

    b = avg_win / avg_loss  # odds ratio
    p = win_rate
    q = 1 - p

    full_kelly = (p * b - q) / b
    edge = p * b - q

    full_kelly = max(0.0, full_kelly)
    half_kelly = full_kelly / 2
    quarter_kelly = full_kelly / 4

    return {
        "full_kelly": round(full_kelly, 4),
        "half_kelly": round(half_kelly, 4),
        "quarter_kelly": round(quarter_kelly, 4),
        "edge": round(edge, 4),
        "odds_ratio": round(b, 4),
        "win_rate": round(p, 4),
        "recommendation": "half_kelly",
        "recommended_fraction": round(half_kelly, 4),
    }


# =====================================================================
#  4. Strategy Correlation Matrix
# =====================================================================

def strategy_correlation(strategy_pnls: Dict[str, List[float]],
                         correlation_threshold: float = 0.5) -> dict:
    """
    Compute correlation matrix between strategy PnL streams.

    Args:
        strategy_pnls: Dict of {strategy_name: [pnl_per_trade]}.
            Each list can have different lengths; correlation computed
            on minimum overlapping length (aligned from start).
        correlation_threshold: Flag pairs above this |correlation|.

    Returns:
        dict with correlation_matrix (nested dict), flagged_pairs,
        strategy_names
    """
    if not strategy_pnls or len(strategy_pnls) < 2:
        return {
            "correlation_matrix": {},
            "flagged_pairs": [],
            "strategy_names": list(strategy_pnls.keys()) if strategy_pnls else [],
            "insufficient": True,
        }

    names = sorted(strategy_pnls.keys())

    # Build aligned DataFrame: pad shorter series with NaN
    max_len = max(len(v) for v in strategy_pnls.values())
    data = {}
    for name in names:
        pnl = strategy_pnls[name]
        padded = list(pnl) + [np.nan] * (max_len - len(pnl))
        data[name] = padded

    df = pd.DataFrame(data)

    # Compute pairwise correlation (Pearson, pairwise complete)
    corr_matrix = df.corr(method="pearson", min_periods=5)

    # Convert to nested dict for JSON serialization
    corr_dict = {}
    for name in names:
        corr_dict[name] = {}
        for other in names:
            val = corr_matrix.loc[name, other]
            corr_dict[name][other] = round(float(val), 4) if not np.isnan(val) else None

    # Flag pairs with high correlation
    flagged = []
    seen = set()
    for i, n1 in enumerate(names):
        for j, n2 in enumerate(names):
            if i >= j:
                continue
            pair_key = (n1, n2)
            if pair_key in seen:
                continue
            seen.add(pair_key)
            val = corr_matrix.loc[n1, n2]
            if not np.isnan(val) and abs(val) > correlation_threshold:
                flagged.append({
                    "pair": [n1, n2],
                    "correlation": round(float(val), 4),
                    "direction": "positive" if val > 0 else "negative",
                })

    return {
        "correlation_matrix": corr_dict,
        "flagged_pairs": flagged,
        "strategy_names": names,
        "insufficient": False,
    }


# =====================================================================
#  5. P&L Attribution
# =====================================================================

def pnl_attribution(trades: List[dict],
                    benchmark_pnl_pips: float = 0.0) -> dict:
    """
    P&L Attribution: Alpha, Friction, Sizing decomposition.

    Args:
        trades: List of closed trade dicts from DB, each with:
            - pnl_pips: actual trade PnL
            - spread_at_entry: spread at entry (pips)
            - spread_at_exit: spread at exit (pips)
            - slippage_pips: slippage (pips)
            - entry_type: strategy name
            - instrument: pair name
        benchmark_pnl_pips: Buy-and-hold PnL of underlying for the period.

    Returns:
        dict with:
            alpha: strategy returns minus benchmark
            friction: total spread + slippage costs
            sizing: difference between lot-weighted and equal-lot PnL
            gross_pnl: total raw PnL
            net_pnl: PnL after friction
    """
    if not trades:
        return {
            "alpha": 0.0, "friction": 0.0, "sizing": 0.0,
            "gross_pnl": 0.0, "net_pnl": 0.0,
            "n_trades": 0, "insufficient": True,
        }

    # Gross PnL
    pnl_values = [float(t.get("pnl_pips", 0) or 0) for t in trades]
    gross_pnl = sum(pnl_values)

    # Friction: total spread + slippage costs
    total_friction = 0.0
    for t in trades:
        spread_entry = abs(float(t.get("spread_at_entry", 0) or 0))
        spread_exit = abs(float(t.get("spread_at_exit", 0) or 0))
        slippage = abs(float(t.get("slippage_pips", 0) or 0))
        total_friction += spread_entry + spread_exit + slippage

    net_pnl = gross_pnl  # PnL already includes friction in this system

    # Alpha: strategy returns vs benchmark
    alpha = gross_pnl - benchmark_pnl_pips

    # Sizing: difference between actual (lot-weighted) and equal-lot PnL
    # In this system, lot sizes vary via 3-Factor Model.
    # Equal-lot PnL = simple mean * N (as if all trades were equal size)
    # Actual PnL = sum of actual PnLs (already lot-weighted in DB)
    n = len(pnl_values)
    equal_lot_pnl = np.mean(pnl_values) * n if n > 0 else 0.0
    sizing_effect = gross_pnl - equal_lot_pnl  # Should be ~0 since DB stores pip PnL

    return {
        "alpha": round(alpha, 2),
        "friction": round(total_friction, 2),
        "sizing": round(sizing_effect, 2),
        "gross_pnl": round(gross_pnl, 2),
        "net_pnl": round(net_pnl, 2),
        "benchmark_pnl": round(benchmark_pnl_pips, 2),
        "n_trades": n,
        "avg_friction_per_trade": round(total_friction / n, 2) if n > 0 else 0.0,
        "insufficient": n < 10,
    }


# =====================================================================
#  6. Graduated DD Multiplier (for demo_trader integration)
# =====================================================================

# DD thresholds and lot multipliers (graduated, not binary)
DD_LOT_TIERS = [
    (0.08, 0.20),   # DD >= 8%: lot * 0.20
    (0.06, 0.40),   # DD >= 6%: lot * 0.40
    (0.04, 0.60),   # DD >= 4%: lot * 0.60
    (0.02, 0.80),   # DD >= 2%: lot * 0.80
]
# Below 2% DD: lot * 1.0 (no reduction)


def get_dd_lot_multiplier(dd_pct: float) -> float:
    """
    Get graduated DD lot multiplier.
    Uses the same thresholds for both reduction and recovery
    (no instant full-open on recovery).

    Args:
        dd_pct: Current drawdown as decimal (e.g., 0.05 for 5%).

    Returns:
        Lot multiplier (0.20 to 1.0).
    """
    for threshold, multiplier in DD_LOT_TIERS:
        if dd_pct >= threshold:
            return multiplier
    return 1.0


# =====================================================================
#  7. Convenience: compute full risk dashboard from trade list
# =====================================================================

def compute_risk_dashboard(trades: List[dict],
                           initial_capital: float = 1000.0) -> dict:
    """
    Compute all risk metrics from a list of closed trade dicts.

    Args:
        trades: List of closed trade dicts from DB.
        initial_capital: Base capital in pips.

    Returns:
        Combined dict of all risk analytics results.
    """
    pnl_list = [float(t.get("pnl_pips", 0) or 0) for t in trades]

    # Group PnL by strategy
    strategy_pnls = {}
    for t in trades:
        et = t.get("entry_type", "unknown") or "unknown"
        strategy_pnls.setdefault(et, []).append(
            float(t.get("pnl_pips", 0) or 0)
        )

    # Win/loss stats for Kelly
    wins = [p for p in pnl_list if p > 0]
    losses = [p for p in pnl_list if p < 0]
    win_rate = len(wins) / len(pnl_list) if pnl_list else 0
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = abs(np.mean(losses)) if losses else 0.0

    # Per-strategy Kelly
    strategy_kelly = {}
    for strat, spnl in strategy_pnls.items():
        s_wins = [p for p in spnl if p > 0]
        s_losses = [p for p in spnl if p < 0]
        if len(spnl) >= 10 and s_wins and s_losses:
            s_wr = len(s_wins) / len(spnl)
            s_avg_win = float(np.mean(s_wins))
            s_avg_loss = abs(float(np.mean(s_losses)))
            strategy_kelly[strat] = kelly_fraction(s_wr, s_avg_win, s_avg_loss)
        else:
            strategy_kelly[strat] = {
                "insufficient": True,
                "n": len(spnl),
            }

    # v8.6: Deflated Sharpe Ratio — 多重検定補正
    from modules.stats_utils import deflated_sharpe_ratio
    _n_strategies = len(strategy_pnls)  # テストした戦略数
    _mean_pnl = float(np.mean(pnl_list)) if pnl_list else 0.0
    _std_pnl = float(np.std(pnl_list)) if len(pnl_list) > 1 else 1.0
    _sharpe_raw = _mean_pnl / _std_pnl if _std_pnl > 0 else 0.0

    # Per-strategy DSR
    strategy_dsr = {}
    for strat, spnl in strategy_pnls.items():
        if len(spnl) >= 5:
            _s_mean = float(np.mean(spnl))
            _s_std = float(np.std(spnl)) if len(spnl) > 1 else 1.0
            _s_sharpe = _s_mean / _s_std if _s_std > 0 else 0.0
            strategy_dsr[strat] = deflated_sharpe_ratio(
                sharpe_observed=_s_sharpe,
                n_trades=len(spnl),
                n_trials=max(_n_strategies, 1),
            )
        else:
            strategy_dsr[strat] = {"insufficient": True, "n": len(spnl)}

    return {
        "var_cvar": calculate_var_cvar(pnl_list),
        "monte_carlo": monte_carlo_ruin(
            pnl_list,
            initial_capital=initial_capital,
            n_simulations=5000,    # reduced for API response time
            n_trades_forward=300,
        ),
        "kelly": kelly_fraction(win_rate, float(avg_win), float(avg_loss)),
        "strategy_kelly": strategy_kelly,
        "strategy_dsr": strategy_dsr,  # v8.6: Deflated Sharpe Ratio per strategy
        "dsr_overall": deflated_sharpe_ratio(
            sharpe_observed=_sharpe_raw,
            n_trades=len(pnl_list),
            n_trials=max(_n_strategies, 1),
        ),
        "correlation": strategy_correlation(strategy_pnls),
        "attribution": pnl_attribution(trades),
        "n_total_trades": len(trades),
    }


def consolidation_simulation(
    all_trades: List[dict],
    tier1_strategies: List[str],
    fidelity_cutoff: str = "2026-04-08T00:00:00+00:00",
    post_cutoff_only: bool = True,
) -> dict:
    """
    Verify whether strategy consolidation improves performance by replaying
    the production trade history filtered to only Tier-1 strategies.

    Args:
        all_trades: List of closed trade dicts from DB (is_shadow=0 already filtered).
        tier1_strategies: Strategy names to keep in the consolidated portfolio.
        fidelity_cutoff: ISO datetime string; only trades after this are "clean".
        post_cutoff_only: If True, restrict baseline to post-cutoff trades only.

    Returns:
        dict with full_system, consolidated, removed_strategies, improvement, recommendation.
    """

    def _parse_time(t: dict) -> str:
        return t.get("exit_time") or t.get("entry_time") or ""

    # Filter to live trades only (is_shadow already excluded by get_stats caller)
    # Optionally restrict to post-fidelity-cutoff for clean data
    if post_cutoff_only:
        trades = [t for t in all_trades if _parse_time(t) >= fidelity_cutoff]
    else:
        trades = list(all_trades)

    if not trades:
        return {"error": "No trades after fidelity cutoff", "insufficient": True}

    def _metrics(trade_list: List[dict]) -> dict:
        if not trade_list:
            return {"n": 0, "wr": 0.0, "total_pnl": 0.0, "ev_per_trade": 0.0,
                    "kelly_edge": 0.0, "avg_win": 0.0, "avg_loss": 0.0}
        n = len(trade_list)
        pnls = [float(t.get("pnl_pips", 0) or 0) for t in trade_list]
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]
        wr = len(wins) / n
        avg_win = float(np.mean(wins)) if wins else 0.0
        avg_loss = float(np.mean(losses)) if losses else 0.0
        total_pnl = sum(pnls)
        ev = total_pnl / n

        # Kelly edge
        if avg_loss > 0 and wr > 0:
            odds = avg_win / avg_loss
            edge = wr * odds - (1 - wr)
        else:
            edge = 0.0

        # Friction estimate (spread_at_entry + spread_at_exit + slippage)
        frictions = []
        for t in trade_list:
            se = float(t.get("spread_at_entry") or 0)
            sx = float(t.get("spread_at_exit") or 0)
            sl = float(t.get("slippage_pips") or 0)
            frictions.append(se + sx + abs(sl))
        avg_friction = float(np.mean(frictions)) if frictions else 0.0

        return {
            "n": n,
            "wr": round(wr * 100, 2),
            "total_pnl": round(total_pnl, 2),
            "ev_per_trade": round(ev, 3),
            "kelly_edge": round(edge, 4),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_friction": round(avg_friction, 2),
        }

    # Full system metrics
    full_metrics = _metrics(trades)

    # Consolidated (Tier-1 only) metrics
    tier1_set = set(tier1_strategies)
    consolidated_trades = [t for t in trades if (t.get("entry_type") or "") in tier1_set]
    consolidated_metrics = _metrics(consolidated_trades)

    # Removed strategies breakdown
    removed_trades = [t for t in trades if (t.get("entry_type") or "") not in tier1_set]
    removed_by_strategy: Dict[str, dict] = {}
    for t in removed_trades:
        et = t.get("entry_type") or "unknown"
        if et not in removed_by_strategy:
            removed_by_strategy[et] = {"n": 0, "pnl": 0.0, "wins": 0}
        removed_by_strategy[et]["n"] += 1
        removed_by_strategy[et]["pnl"] += float(t.get("pnl_pips", 0) or 0)
        if t.get("outcome") == "WIN":
            removed_by_strategy[et]["wins"] += 1
    for et in removed_by_strategy:
        d = removed_by_strategy[et]
        d["pnl"] = round(d["pnl"], 2)
        d["avg_pnl"] = round(d["pnl"] / d["n"], 3) if d["n"] > 0 else 0.0
        d["wr"] = round(d["wins"] / d["n"] * 100, 1) if d["n"] > 0 else 0.0

    # Sort removed strategies by total PnL (worst first)
    removed_sorted = dict(sorted(removed_by_strategy.items(),
                                 key=lambda x: x[1]["pnl"]))

    # Improvement metrics
    delta_wr = consolidated_metrics["wr"] - full_metrics["wr"]
    delta_ev = consolidated_metrics["ev_per_trade"] - full_metrics["ev_per_trade"]
    delta_pnl = consolidated_metrics["total_pnl"] - full_metrics["total_pnl"]
    delta_kelly = consolidated_metrics["kelly_edge"] - full_metrics["kelly_edge"]

    # Statistical significance of WR improvement (Wilson approx)
    n_full = full_metrics["n"]
    n_tier1 = consolidated_metrics["n"]
    wins_tier1 = round(n_tier1 * consolidated_metrics["wr"] / 100)
    sig_wr = "N/A"
    if n_tier1 >= 10:
        # Binomial test: H0 WR <= full system WR
        null = full_metrics["wr"] / 100
        obs = consolidated_metrics["wr"] / 100
        if null > 0 and null < 1 and n_tier1 > 0:
            se = float(np.sqrt(null * (1 - null) / n_tier1))
            z = (obs - null) / se if se > 0 else 0.0
            sig_wr = f"z={round(z, 2)}"

    # Recommendation
    if consolidated_metrics["kelly_edge"] > 0.05 and delta_ev > 0.5:
        rec = "CONSOLIDATE: Tier-1 portfolio shows materially positive Kelly edge. Recommend stopping shadow recording of negative-Kelly strategies to concentrate data collection."
    elif consolidated_metrics["kelly_edge"] > 0:
        rec = "PARTIAL_CONSOLIDATE: Tier-1 shows positive edge but EV improvement is small. Friction reduction (Quick-Harvest緩和, 指値エントリー) must accompany consolidation to reach breakeven."
    elif delta_ev > 0:
        rec = "MARGINAL: Consolidation improves EV but Tier-1 portfolio still negative Kelly. Requires both consolidation AND friction reduction simultaneously."
    else:
        rec = "INSUFFICIENT_DATA: Post-cutoff Tier-1 trades too few for reliable conclusion. Continue data accumulation."

    # Friction wasted on removed strategies
    removed_friction_wasted = sum(
        removed_by_strategy[et]["n"] * full_metrics["avg_friction"]
        for et in removed_by_strategy
    ) if full_metrics["avg_friction"] > 0 else 0.0

    return {
        "full_system": full_metrics,
        "consolidated": consolidated_metrics,
        "removed_strategies": removed_sorted,
        "improvement": {
            "delta_wr_pp": round(delta_wr, 2),
            "delta_ev_per_trade": round(delta_ev, 3),
            "delta_pnl_total": round(delta_pnl, 2),
            "delta_kelly_edge": round(delta_kelly, 4),
            "wr_significance": sig_wr,
            "friction_wasted_on_removed": round(removed_friction_wasted, 2),
        },
        "tier1_strategies": sorted(tier1_set),
        "n_removed_strategies": len(removed_by_strategy),
        "recommendation": rec,
        "post_cutoff_only": post_cutoff_only,
        "fidelity_cutoff": fidelity_cutoff,
    }


def compute_slippage_stats(trades: List[dict]) -> dict:
    """
    Compute slippage statistics segmented by session, regime, strategy.

    Args:
        trades: List of closed trade dicts from DB.

    Returns:
        dict with by_session, by_regime, by_strategy slippage stats.
    """
    if not trades:
        return {
            "by_session": {}, "by_regime": {}, "by_strategy": {},
            "overall": {}, "n_trades": 0, "insufficient": True,
        }

    import json as _json
    from datetime import datetime as _dt

    def _session_from_hour(hour: int) -> str:
        if 0 <= hour < 7:
            return "tokyo"
        elif 7 <= hour < 13:
            return "london"
        elif 13 <= hour < 20:
            return "newyork"
        else:
            return "late_ny"

    def _compute_group_stats(group_trades: list) -> dict:
        slippages = [abs(float(t.get("slippage_pips", 0) or 0)) for t in group_trades]
        spreads_entry = [float(t.get("spread_at_entry", 0) or 0) for t in group_trades]
        spreads_exit = [float(t.get("spread_at_exit", 0) or 0) for t in group_trades]
        pnls = [float(t.get("pnl_pips", 0) or 0) for t in group_trades]

        if not slippages:
            return {"n": 0}

        return {
            "n": len(slippages),
            "slippage_mean": round(float(np.mean(slippages)), 3),
            "slippage_median": round(float(np.median(slippages)), 3),
            "slippage_p90": round(float(np.percentile(slippages, 90)), 3),
            "slippage_max": round(float(np.max(slippages)), 3),
            "spread_entry_mean": round(float(np.mean(spreads_entry)), 3),
            "spread_exit_mean": round(float(np.mean(spreads_exit)), 3),
            "total_friction": round(sum(slippages) + sum(spreads_entry) + sum(spreads_exit), 2),
            "avg_pnl": round(float(np.mean(pnls)), 2),
        }

    # Group by session
    by_session = {}
    for t in trades:
        try:
            hour = _dt.fromisoformat(t.get("entry_time", "")).hour
            session = _session_from_hour(hour)
        except Exception:
            session = "unknown"
        by_session.setdefault(session, []).append(t)

    # Group by regime
    by_regime = {}
    for t in trades:
        try:
            regime_data = _json.loads(t.get("regime", "{}") or "{}")
            regime = regime_data.get("regime", "unknown")
        except Exception:
            regime = "unknown"
        by_regime.setdefault(regime, []).append(t)

    # Group by strategy
    by_strategy = {}
    for t in trades:
        et = t.get("entry_type", "unknown") or "unknown"
        by_strategy.setdefault(et, []).append(t)

    return {
        "by_session": {k: _compute_group_stats(v) for k, v in by_session.items()},
        "by_regime": {k: _compute_group_stats(v) for k, v in by_regime.items()},
        "by_strategy": {k: _compute_group_stats(v) for k, v in by_strategy.items()},
        "overall": _compute_group_stats(trades),
        "n_trades": len(trades),
        "insufficient": len(trades) < 10,
    }
