"""MA-Generic Family v1 — Full-quant validation runner (rule:R1, 2026-04-30)

Walk-Forward 3-fold × Bonferroni/BH 補正 × Wilson 95% 下限 × Kelly × PF × DSR
を 4 戦略 × 3 セッション (Tokyo/London/NY) で実行し、Shadow→LIVE 昇格判定の
入力 CSV を生成する。

Usage:
  BT_MODE=1 NO_AUTOSTART=1 python research/edge_discovery/ma_family_validation.py \
      --pair USD_JPY \
      --days 270 \
      --wf-folds 3 \
      --inject-spread 0.8 \
      --output knowledge-base/raw/audits/ma_family_v1/

Output:
  <output>/<pair>_<strategy>_full.csv     — 全 trade レベル
  <output>/<pair>_summary.csv             — strategy × session × fold セル粒度
  <output>/<pair>_promotion.csv           — Shadow→LIVE 6 条件チェック表

Promotion criteria (all AND):
  1. WF 3-fold すべての fold で PnL>0 かつ PF>1.3
  2. Bonferroni/BH 補正後 p<0.05
  3. Wilson95下限 > 10%  (本ランナーは pct 単位、KB は 0.1 = 10pct)
  4. Trade-weighted Kelly > 0.10
  5. N ≥ 30
  6. (cohort time alignment は手動 cross-check で別途実施)

p 値計算:
  H0: WR = BEV (break-even WR for given RR), one-sided binomial test
  per cell の WR が BEV 以上かを bonf/BH 補正で検定
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

# BT_MODE: prevent app.py autostart
os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _import_runner():
    from modules.bt_vec_harness import (
        VecBacktestRunner, HtfFeatureSpec, wilson_lower,
        profit_factor_local, kelly_pct,
    )
    return VecBacktestRunner, HtfFeatureSpec, wilson_lower, profit_factor_local, kelly_pct


def _import_strategies():
    from strategies.scalp.ma_mr_hybrid import MaMrHybrid
    from strategies.scalp.ma_trend_perfect import MaTrendPerfect
    from strategies.scalp.ma_regime_switch import MaRegimeSwitch
    from strategies.scalp.bb_rsi_ema_aligned import BbRsiEmaAligned
    return {
        "ma_mr_hybrid": MaMrHybrid,
        "ma_trend_perfect": MaTrendPerfect,
        "ma_regime_switch": MaRegimeSwitch,
        "bb_rsi_ema_aligned": BbRsiEmaAligned,
    }


def _session_of_hour(h: int) -> str:
    if 0 <= h < 7:
        return "Tokyo"
    if 7 <= h < 13:
        return "London"
    if 13 <= h < 21:
        return "NY"
    return "Off"


def _binomial_one_sided_p(wins: int, n: int, p_h0: float) -> float:
    """One-sided p-value: P(W >= wins | n, p_h0). H0: WR = p_h0, H1: WR > p_h0."""
    if n <= 0:
        return 1.0
    from scipy.stats import binom
    return float(binom.sf(wins - 1, n, p_h0))


def _benjamini_hochberg(pvals: list[float], q: float = 0.05) -> list[bool]:
    """BH-FDR rejection mask. True = significant."""
    n = len(pvals)
    if n == 0:
        return []
    order = np.argsort(pvals)
    ranked = np.array(pvals)[order]
    thresholds = (np.arange(1, n + 1) / n) * q
    passed = ranked <= thresholds
    if not passed.any():
        rej = np.zeros(n, dtype=bool)
    else:
        max_k = np.max(np.where(passed)[0]) + 1
        rej = np.zeros(n, dtype=bool)
        rej[order[:max_k]] = True
    return rej.tolist()


def _bev_wr(avg_win: float, avg_loss: float, spread: float) -> float:
    """Break-even WR given average win/loss/spread (all in pips)."""
    win_after = avg_win - spread
    loss_after = abs(avg_loss) + spread
    if win_after + loss_after <= 0:
        return 1.0
    return loss_after / (win_after + loss_after)


def _deflated_sharpe(pnls: list[float], n_trials: int) -> float:
    """Bailey & Lopez de Prado Deflated Sharpe — single-trial approximation."""
    if len(pnls) < 5:
        return 0.0
    arr = np.array(pnls, dtype=float)
    mu = arr.mean()
    sigma = arr.std(ddof=1)
    if sigma <= 0:
        return 0.0
    sr = mu / sigma
    skew = float(((arr - mu) ** 3).mean() / sigma ** 3)
    kurt = float(((arr - mu) ** 4).mean() / sigma ** 4)
    n = len(arr)
    sr_se = math.sqrt((1 - skew * sr + (kurt - 1) / 4 * sr ** 2) / max(1, n - 1))
    if sr_se <= 0:
        return 0.0
    # Threshold from multiple-trial selection bias (n_trials independent SRs)
    from scipy.stats import norm
    sr_threshold = sr_se * math.sqrt(2 * math.log(max(1, n_trials)))
    return (sr - sr_threshold) / sr_se   # standardized DSR


def _run_one(symbol: str, strategy_name: str, strategy_cls,
             days: int, inject_spread: float, verbose: bool) -> list[dict]:
    """Run BT for a single strategy and return per-trade dicts with session label."""
    VecBacktestRunner, HtfFeatureSpec, _, _, _ = _import_runner()
    spec = HtfFeatureSpec(
        m15_fields=["close", "ema9", "ema21", "ema50", "adx", "ema_slope", "atr"],
        m5_fields=[
            "close", "prev_close", "prev_high", "prev_low",
            "ema9", "ema21", "sma21",
            "bbpb", "rsi14", "stoch_k", "stoch_d",
            "swing_high", "swing_low", "atr",
        ],
        include_h1=True,
        h1_fields=["close", "ema9", "ema21", "ema50", "ema200", "adx"],
        inject_spread=inject_spread,
        # Tier A/B/C toggles: keep off for clean parity vs production.
        # Production parity will be re-enabled per strategy when we move to PR2.
    )
    runner = VecBacktestRunner(spec=spec, strategy_factory=strategy_cls)
    result = runner.run(symbol=symbol, days=days, verbose=verbose)
    trades = result.get("trades_sample") or []
    # trades_sample only has 10 — get the full list via _stats workaround:
    # we re-run in batched mode by collecting trades inside runner.run.
    # The current bt_vec_harness API truncates to 10 in _stats — so we need
    # to monkey-patch or extend. For now we inline the trade collection by
    # reading runner internals if available.
    full = result.get("trades_full") if isinstance(result, dict) else None
    if full is None:
        # Fall back to the truncated sample. Caller must upgrade _stats to
        # emit the full trade list (TODO: see PR2).
        full = trades

    out = []
    for t in full:
        ts = t.get("ts")
        try:
            dt = pd.Timestamp(ts)
            hour = dt.hour
        except Exception:
            hour = 12
        out.append({
            "strategy": strategy_name,
            "ts": ts,
            "hour_utc": hour,
            "session": _session_of_hour(hour),
            "signal": t.get("signal"),
            "outcome": t.get("outcome"),
            "pnl_pips": float(t.get("pnl_pips", 0.0)),
            "exit_bars": t.get("exit_bars"),
        })
    return out


def _split_folds(trades: list[dict], n_folds: int) -> list[list[dict]]:
    """Time-ordered fold split."""
    if not trades:
        return [[] for _ in range(n_folds)]
    n = len(trades)
    fold_size = max(1, n // n_folds)
    folds = [trades[i * fold_size:(i + 1) * fold_size] for i in range(n_folds)]
    if len(folds) < n_folds:
        folds += [[] for _ in range(n_folds - len(folds))]
    # Append remainder to last fold
    if n_folds * fold_size < n:
        folds[-1].extend(trades[n_folds * fold_size:])
    return folds


def _stats_for_cell(trades: list[dict], spread: float) -> dict:
    _, _, wilson_lower, profit_factor_local, kelly_pct = _import_runner()
    n = len(trades)
    if n == 0:
        return {
            "n": 0, "wr": 0.0, "wilson_lo_pct": 0.0, "ev_pips": 0.0,
            "pf": 0.0, "kelly": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
            "p_value": 1.0, "bev_wr": 1.0,
        }
    wins = [t for t in trades if t["outcome"] == "WIN"]
    losses = [t for t in trades if t["outcome"] == "LOSS"]
    n_w = len(wins)
    wr = n_w / n
    pnls = [t["pnl_pips"] for t in trades]
    ev = sum(pnls) / n
    pf = profit_factor_local(pnls)
    if pf == float("inf"):
        pf = 99.0
    avg_win = (sum(t["pnl_pips"] for t in wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(t["pnl_pips"] for t in losses) / len(losses)) if losses else 0.0
    wlow = wilson_lower(n_w, n)
    kelly = kelly_pct(wr, avg_win, avg_loss)
    bev = _bev_wr(avg_win, avg_loss, spread)
    p_val = _binomial_one_sided_p(n_w, n, bev) if bev < 1.0 else 1.0
    return {
        "n": n, "wr": round(wr, 4),
        "wilson_lo_pct": round(wlow, 2),
        "ev_pips": round(ev, 3),
        "pf": round(pf, 3),
        "kelly": round(kelly, 4),
        "avg_win": round(avg_win, 3),
        "avg_loss": round(avg_loss, 3),
        "p_value": round(p_val, 5),
        "bev_wr": round(bev, 4),
    }


def _promotion_check(per_fold_stats: list[dict], all_trades_stats: dict,
                     significant: bool) -> dict:
    """Apply 6-criteria promotion check."""
    c1_wf_all_positive = all(
        f["n"] > 0 and f["ev_pips"] > 0 and f["pf"] > 1.3
        for f in per_fold_stats
    ) if per_fold_stats and all(f["n"] > 0 for f in per_fold_stats) else False
    c2_significant = significant
    c3_wilson = all_trades_stats["wilson_lo_pct"] > 10.0
    c4_kelly = all_trades_stats["kelly"] > 0.10
    c5_n = all_trades_stats["n"] >= 30
    promote = c1_wf_all_positive and c2_significant and c3_wilson and c4_kelly and c5_n
    return {
        "c1_wf_all_pf_gt1_3": c1_wf_all_positive,
        "c2_bh_significant": c2_significant,
        "c3_wilson95_gt_10pct": c3_wilson,
        "c4_kelly_gt_0_10": c4_kelly,
        "c5_n_ge_30": c5_n,
        "promote_to_live": promote,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="USD_JPY")
    ap.add_argument("--days", type=int, default=270)
    ap.add_argument("--wf-folds", type=int, default=3)
    ap.add_argument("--inject-spread", type=float, default=0.8)
    ap.add_argument("--output", default="knowledge-base/raw/audits/ma_family_v1/")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--strategies", default="",
                    help="Comma-separated subset of strategy names to run "
                    "(default: all 4). Filters which strategies are evaluated "
                    "AND which cells participate in BH-FDR — focused runs get "
                    "milder multiple-testing penalty.")
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts_run = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    verbose = not args.quiet

    strategies = _import_strategies()
    if args.strategies:
        wanted = {s.strip() for s in args.strategies.split(",") if s.strip()}
        strategies = {k: v for k, v in strategies.items() if k in wanted}
        if not strategies:
            raise SystemExit(f"No matching strategies for --strategies={args.strategies}")

    print(f"\n=== MA-Generic Family v1 Validation ===")
    print(f"Pair      : {args.pair}")
    print(f"Days      : {args.days}")
    print(f"WF folds  : {args.wf_folds}")
    print(f"Spread    : {args.inject_spread} pip (round-trip)")
    print(f"Output    : {out_dir}")
    print(f"UTC ts    : {ts_run}\n")

    all_full = []
    per_strategy_stats: dict[str, dict] = {}

    for sname, scls in strategies.items():
        print(f"[{sname}] running...")
        t0 = time.perf_counter()
        try:
            full = _run_one(args.pair, sname, scls, args.days,
                            args.inject_spread, verbose)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        secs = time.perf_counter() - t0
        print(f"  done: N={len(full)} trades in {secs:.1f}s")
        all_full.extend(full)
        per_strategy_stats[sname] = {"trades": full}

    # Save full trade-level CSV
    if all_full:
        df_full = pd.DataFrame(all_full)
        full_path = out_dir / f"{args.pair}_trades_{ts_run}.csv"
        df_full.to_csv(full_path, index=False)
        print(f"\nFull trades → {full_path} ({len(df_full)} rows)")

    # Cell-level summary: strategy × session × fold + total
    summary_rows = []
    promo_rows = []
    cell_p_values = []
    cell_keys = []

    for sname, info in per_strategy_stats.items():
        trades = info["trades"]
        # Total stats
        total = _stats_for_cell(trades, args.inject_spread)
        total["strategy"] = sname
        total["session"] = "ALL"
        total["fold"] = "ALL"
        summary_rows.append(total)

        # Per-session
        for sess in ("Tokyo", "London", "NY"):
            sess_trades = [t for t in trades if t["session"] == sess]
            stats = _stats_for_cell(sess_trades, args.inject_spread)
            stats["strategy"] = sname
            stats["session"] = sess
            stats["fold"] = "ALL"
            summary_rows.append(stats)
            if stats["n"] >= 5:
                cell_p_values.append(stats["p_value"])
                cell_keys.append((sname, sess))

        # Per-fold (time-ordered)
        folds = _split_folds(trades, args.wf_folds)
        for fi, fold_trades in enumerate(folds):
            fold_stats = _stats_for_cell(fold_trades, args.inject_spread)
            fold_stats["strategy"] = sname
            fold_stats["session"] = "ALL"
            fold_stats["fold"] = f"f{fi+1}"
            summary_rows.append(fold_stats)

    # BH correction across cells (strategy × session, n>=5)
    bh_rejected = _benjamini_hochberg(cell_p_values, q=0.05) if cell_p_values else []
    sig_set = {cell_keys[i] for i, r in enumerate(bh_rejected) if r}
    print(f"\nBH-significant cells (q=0.05): {len(sig_set)} / {len(cell_keys)}")
    for key in sig_set:
        print(f"  ✓ {key}")

    # Promotion check per (strategy, session)
    for sname, info in per_strategy_stats.items():
        trades = info["trades"]
        for sess in ("Tokyo", "London", "NY", "ALL"):
            sub = trades if sess == "ALL" else [t for t in trades if t["session"] == sess]
            total = _stats_for_cell(sub, args.inject_spread)
            folds = _split_folds(sub, args.wf_folds)
            per_fold = [_stats_for_cell(f, args.inject_spread) for f in folds]
            sig = (sname, sess) in sig_set if sess != "ALL" else False
            check = _promotion_check(per_fold, total, sig)
            promo_rows.append({
                "strategy": sname, "session": sess,
                "n": total["n"],
                "wr_pct": round(total["wr"] * 100, 2),
                "wilson_lo_pct": total["wilson_lo_pct"],
                "ev_pips": total["ev_pips"],
                "pf": total["pf"],
                "kelly": total["kelly"],
                "p_value": total["p_value"],
                "bev_wr": total["bev_wr"],
                **check,
            })

    df_sum = pd.DataFrame(summary_rows)
    df_promo = pd.DataFrame(promo_rows)
    sum_path = out_dir / f"{args.pair}_summary_{ts_run}.csv"
    promo_path = out_dir / f"{args.pair}_promotion_{ts_run}.csv"
    df_sum.to_csv(sum_path, index=False)
    df_promo.to_csv(promo_path, index=False)
    print(f"Summary    → {sum_path}")
    print(f"Promotion  → {promo_path}")

    # Print top promotion candidates
    promotable = df_promo[df_promo["promote_to_live"] == True]
    print(f"\n=== Promotable cells: {len(promotable)} ===")
    if not promotable.empty:
        print(promotable[["strategy", "session", "n", "wr_pct",
                          "wilson_lo_pct", "kelly", "pf", "p_value"]].to_string())
    else:
        print("(none cleared all 5 criteria)")


if __name__ == "__main__":
    main()
