"""Phase 8 Track E — Regime-Stratified Edge Mining.

Pre-registered LOCK: knowledge-base/wiki/decisions/pre-reg-phase8-track-e-2026-04-28.md

Stratifications:
  S1: HMM regime × hour × pair × dir × forward
  S2: ATR percentile × bbpb_15m × dir × pair × forward
  S3: Regime transition events × pair × dir × forward

Stages:
  1: Training (275d) — generate cells, BH-FDR(0.10) + gates
  2: Holdout (90d) OOS — N≥10, WR>0.50, EV>0

Bonus: Phase 7 sole survivor (hour=20 × JPY × SELL) を regime stratify。

Usage:
    python3 tools/phase8_track_e.py --stage 1 --days 275
    python3 tools/phase8_track_e.py --stage 2 --input raw/phase8/track_e/stage1_<tag>.json
    python3 tools/phase8_track_e.py --bonus --days 275
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

try:
    from scipy.stats import binomtest as _bt
    def _binom(k, n, p):
        return _bt(k=k, n=n, p=p, alternative="two-sided").pvalue
except ImportError:
    from scipy.stats import binom_test as _bt
    def _binom(k, n, p):
        return _bt(k, n, p, alternative="two-sided")

from tools.lib.trade_sim import simulate_cell_trades, aggregate_trade_stats
from tools.pattern_discovery import (
    _load_pair, _add_features, wilson_lower, benjamini_hochberg,
    PAIRS_LOCK, DIRECTIONS_LOCK, FORWARD_BARS_LOCK,
    HOLDOUT_DAYS_LOCK, TRAINING_DAYS_LOCK,
    SL_ATR_MULT_LOCK, TP_ATR_MULT_LOCK,
)
from research.edge_discovery.regime_labeler import (
    compute_slope_t, compute_adx, RegimeConfig,
)


# ─────────────────────────────────────────────────────────────
# Regime labelling on 15m timeframe (right-aligned)
# ─────────────────────────────────────────────────────────────
def _add_regime_15m(df: pd.DataFrame, cfg: RegimeConfig | None = None) -> pd.DataFrame:
    """Attach regime column to a 15m OHLC DataFrame.

    Look-ahead 防止: slope_t/ADX は right-aligned (bar(t) 含む last N bars)。
    bar(t) の regime は bar(t).Close 確定時点で利用可能 → bar(t+1) Open entry が
    look-ahead-safe。Track E の signal は bar(t).regime をシフトせずそのまま使う
    (= 「bar(t-1) の regime」として bar(t) に attach する慣行は使わない、代わりに
    bar(t) regime + bar(t+1) Open entry で同等の look-ahead-safety を担保)。

    columns mapping: df has 'Open/High/Low/Close', we adapt to 'open/high/low/close'.
    """
    if cfg is None:
        cfg = RegimeConfig()
    work = pd.DataFrame({
        "open": df["Open"].astype(float).values,
        "high": df["High"].astype(float).values,
        "low": df["Low"].astype(float).values,
        "close": df["Close"].astype(float).values,
    }, index=df.index)

    slope_df = compute_slope_t(work["close"], window=cfg.slope_window)
    work["slope_t"] = slope_df["slope_t"].values
    work["adx"] = compute_adx(work, period=cfg.adx_period).values

    def _classify(st, adx):
        if pd.isna(st) or pd.isna(adx):
            return "uncertain"
        if st > cfg.slope_t_trend and adx > cfg.adx_trend:
            return "up_trend"
        if st < -cfg.slope_t_trend and adx > cfg.adx_trend:
            return "down_trend"
        if abs(st) < cfg.slope_t_range and adx < cfg.adx_range:
            return "range"
        return "uncertain"

    df = df.copy()
    df["regime_15m"] = [
        _classify(work["slope_t"].iloc[i], work["adx"].iloc[i])
        for i in range(len(work))
    ]
    # regime transition (bar t-1 → bar t) — 最初の row は NaN
    df["regime_15m_prev"] = df["regime_15m"].shift(1)
    return df


REGIMES = ("up_trend", "down_trend", "range", "uncertain")
TRANSITIONS_LOCK = (
    ("up_trend", "down_trend"),
    ("down_trend", "up_trend"),
    ("range", "up_trend"),
    ("range", "down_trend"),
)


# ─────────────────────────────────────────────────────────────
# Stage 1 — three stratifications
# ─────────────────────────────────────────────────────────────
def _run_cell(df: pd.DataFrame, sig_idx: list, direction: str,
              fw: int, pair: str, days: int) -> dict | None:
    if len(sig_idx) < 100:
        return None
    trades = simulate_cell_trades(
        df, sig_idx, direction, atr_series=df["atr"],
        sl_atr_mult=SL_ATR_MULT_LOCK, tp_atr_mult=TP_ATR_MULT_LOCK,
        max_hold_bars=fw, pair=pair, dedup=True,
    )
    stats = aggregate_trade_stats(trades)
    if stats["n_trades"] < 100:
        return None
    wlo = wilson_lower(stats["n_wins"], stats["n_trades"])
    p = _binom(stats["n_wins"], stats["n_trades"], 0.5)
    months = days / 30.0
    per_month = stats["n_trades"] / months
    return {
        "n_trades": stats["n_trades"],
        "n_wins": stats["n_wins"],
        "wr": stats["wr"],
        "wilson_lower": round(wlo, 4),
        "ev_net_pip": stats["ev_net_pip"],
        "pf": stats["pf"],
        "kelly": stats["kelly"],
        "sharpe_per_event": stats["sharpe_per_event"],
        "trades_per_month": round(per_month, 1),
        "p_value": round(float(p), 6),
    }


def stage1_scan(days: int = TRAINING_DAYS_LOCK,
                pairs: list | None = None,
                forwards: list | None = None) -> dict:
    pairs = pairs or PAIRS_LOCK
    forwards = forwards or FORWARD_BARS_LOCK
    all_results: list[dict] = []
    cell_counter = 0

    for pair in pairs:
        print(f"\n=== Stage 1 — {pair} ===", flush=True)
        try:
            df = _load_pair(pair, days)
        except Exception as e:
            print(f"  load failed: {e}", flush=True)
            continue
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
        df = df[df.index < cutoff]
        df = _add_features(df).dropna(subset=["atr", "bbpb_15m", "rsi_15m"])
        if len(df) < 1000:
            print(f"  insufficient bars after holdout: {len(df)}", flush=True)
            continue
        df = _add_regime_15m(df)
        print(f"  Training bars: {len(df)} | regime dist: "
              f"{df['regime_15m'].value_counts().to_dict()}", flush=True)

        # ── S1: regime × hour × dir × fw ─────────────────────
        for regime in REGIMES:
            r_mask = df["regime_15m"] == regime
            r_idx = df[r_mask].index
            if len(r_idx) < 100:
                continue
            for hour in range(24):
                cell_idx = df[r_mask & (df["hour_utc"] == hour)].index
                sig_indices = [df.index.get_loc(t) for t in cell_idx]
                for direction in DIRECTIONS_LOCK:
                    for fw in forwards:
                        res = _run_cell(df, sig_indices, direction, fw, pair, days)
                        if res is None:
                            continue
                        res.update({
                            "stratification": "S1",
                            "pair": pair,
                            "regime": regime,
                            "hour_utc": hour,
                            "direction": direction,
                            "forward_bars": fw,
                        })
                        all_results.append(res)
                        cell_counter += 1

        # ── S2: atr_pct × bbpb × dir × fw ────────────────────
        for atr_b in (0, 1, 2):
            for bbpb_b in (0, 1, 2, 3, 4):
                cell_idx = df[(df["atr_pct_60d_b"] == atr_b) &
                              (df["bbpb_15m_b"] == bbpb_b)].index
                sig_indices = [df.index.get_loc(t) for t in cell_idx]
                for direction in DIRECTIONS_LOCK:
                    for fw in forwards:
                        res = _run_cell(df, sig_indices, direction, fw, pair, days)
                        if res is None:
                            continue
                        res.update({
                            "stratification": "S2",
                            "pair": pair,
                            "atr_pct_60d_b": atr_b,
                            "bbpb_15m_b": bbpb_b,
                            "direction": direction,
                            "forward_bars": fw,
                        })
                        all_results.append(res)
                        cell_counter += 1

        # ── S3: regime transition × dir × fw ─────────────────
        for r_from, r_to in TRANSITIONS_LOCK:
            mask = (df["regime_15m_prev"] == r_from) & (df["regime_15m"] == r_to)
            cell_idx = df[mask].index
            sig_indices = [df.index.get_loc(t) for t in cell_idx]
            for direction in DIRECTIONS_LOCK:
                for fw in forwards:
                    res = _run_cell(df, sig_indices, direction, fw, pair, days)
                    if res is None:
                        continue
                    res.update({
                        "stratification": "S3",
                        "pair": pair,
                        "regime_from": r_from,
                        "regime_to": r_to,
                        "direction": direction,
                        "forward_bars": fw,
                    })
                    all_results.append(res)
                    cell_counter += 1

    print(f"\nTotal cells generated: {cell_counter}")
    return {"results": all_results, "n_cells": cell_counter}


def stage1_apply_gates(results: list, q: float = 0.10) -> list:
    if not results:
        return []
    p_values = [r["p_value"] for r in results]
    bh_sig = benjamini_hochberg(p_values, q=q)
    survivors = []
    for r, sig in zip(results, bh_sig):
        gates = {
            "bh_fdr": sig,
            "wilson_gt_50": r["wilson_lower"] > 0.50,
            "n_ge_100": r["n_trades"] >= 100,
            "ev_pos": r["ev_net_pip"] > 0,
            "capacity": r["trades_per_month"] >= 5,
            "sharpe_pos": (r["sharpe_per_event"] or 0) > 0.05,
        }
        if all(gates.values()):
            r["gates"] = gates
            survivors.append(r)
    return survivors


# ─────────────────────────────────────────────────────────────
# Stage 2 — Holdout OOS
# ─────────────────────────────────────────────────────────────
def _signal_indices_holdout(df_all: pd.DataFrame, df_hold: pd.DataFrame,
                            r: dict) -> list:
    s = r["stratification"]
    if s == "S1":
        mask = ((df_hold["regime_15m"] == r["regime"]) &
                (df_hold["hour_utc"] == r["hour_utc"]))
    elif s == "S2":
        mask = ((df_hold["atr_pct_60d_b"] == r["atr_pct_60d_b"]) &
                (df_hold["bbpb_15m_b"] == r["bbpb_15m_b"]))
    elif s == "S3":
        mask = ((df_hold["regime_15m_prev"] == r["regime_from"]) &
                (df_hold["regime_15m"] == r["regime_to"]))
    else:
        return []
    return [df_all.index.get_loc(t) for t in df_hold[mask].index]


def stage2_holdout(survivors_s1: list, days: int) -> list:
    pair_dfs: dict[str, pd.DataFrame] = {}
    survivors_s2 = []
    for r in survivors_s1:
        pair = r["pair"]
        if pair not in pair_dfs:
            try:
                df = _load_pair(pair, days + HOLDOUT_DAYS_LOCK)
                df = _add_features(df).dropna(subset=["atr", "bbpb_15m", "rsi_15m"])
                df = _add_regime_15m(df)
                pair_dfs[pair] = df
            except Exception as e:
                print(f"  load failed {pair}: {e}")
                continue
        df_all = pair_dfs[pair]
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
        df_hold = df_all[df_all.index >= cutoff]
        sig_idx = _signal_indices_holdout(df_all, df_hold, r)
        if len(sig_idx) < 10:
            r["stage2_holdout"] = {"n": len(sig_idx), "pass": False,
                                    "reason": "n<10"}
            continue
        trades = simulate_cell_trades(
            df_all, sig_idx, r["direction"], df_all["atr"],
            sl_atr_mult=SL_ATR_MULT_LOCK, tp_atr_mult=TP_ATR_MULT_LOCK,
            max_hold_bars=r["forward_bars"], pair=pair, dedup=True,
        )
        s = aggregate_trade_stats(trades)
        wlo = wilson_lower(s["n_wins"], s["n_trades"]) if s["n_trades"] > 0 else 0
        passed = (s["wr"] > 0.50) and (s["ev_net_pip"] > 0)
        r["stage2_holdout"] = {
            "n": s["n_trades"], "wr": s["wr"],
            "wilson_lower": round(wlo, 4),
            "ev_net_pip": s["ev_net_pip"],
            "pass": passed,
        }
        if passed:
            survivors_s2.append(r)
    return survivors_s2


# ─────────────────────────────────────────────────────────────
# Bonus — Phase 7 hour=20×JPY×SELL を regime stratify
# ─────────────────────────────────────────────────────────────
def bonus_phase7_regime_stratify(days: int) -> dict:
    """Phase 7 唯一 survivor (hour=20 × JPY × SELL) を regime stratify。"""
    out: dict = {"strategy": "phase7_hour20_jpy_sell", "by_regime": {}}
    jpy_pairs = ["USD_JPY", "EUR_JPY", "GBP_JPY"]
    for pair in jpy_pairs:
        try:
            df = _load_pair(pair, days)
        except Exception as e:
            print(f"  load failed {pair}: {e}")
            continue
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
        df = df[df.index < cutoff]
        df = _add_features(df).dropna(subset=["atr", "bbpb_15m", "rsi_15m"])
        df = _add_regime_15m(df)
        for regime in REGIMES:
            mask = (df["hour_utc"] == 20) & (df["regime_15m"] == regime)
            cell_idx = df[mask].index
            sig_idx = [df.index.get_loc(t) for t in cell_idx]
            if len(sig_idx) < 20:
                out["by_regime"].setdefault(pair, {})[regime] = {"n": len(sig_idx)}
                continue
            trades = simulate_cell_trades(
                df, sig_idx, "SELL", df["atr"],
                sl_atr_mult=SL_ATR_MULT_LOCK, tp_atr_mult=TP_ATR_MULT_LOCK,
                max_hold_bars=8, pair=pair, dedup=True,
            )
            s = aggregate_trade_stats(trades)
            wlo = wilson_lower(s["n_wins"], s["n_trades"]) if s["n_trades"] > 0 else 0
            out["by_regime"].setdefault(pair, {})[regime] = {
                "n": s["n_trades"], "wr": s["wr"],
                "wilson_lower": round(wlo, 4),
                "ev_net_pip": s["ev_net_pip"],
                "sharpe_pe": s["sharpe_per_event"],
            }
    return out


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=int, choices=[1, 2], default=None)
    p.add_argument("--bonus", action="store_true")
    p.add_argument("--days", type=int, default=TRAINING_DAYS_LOCK)
    p.add_argument("--pairs", nargs="+", default=PAIRS_LOCK)
    p.add_argument("--forwards", type=int, nargs="+", default=FORWARD_BARS_LOCK)
    p.add_argument("--input", default=None)
    p.add_argument("--bh-q", type=float, default=0.10)
    p.add_argument("--output", default="raw/phase8/track_e/")
    args = p.parse_args()

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    if args.bonus:
        print("=" * 60)
        print("  Bonus — Phase 7 hour20×JPY×SELL regime stratification")
        print("=" * 60)
        bonus = bonus_phase7_regime_stratify(args.days)
        json_path = out_dir / f"regime_conditional_phase17_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(bonus, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")
        for pair, by_r in bonus.get("by_regime", {}).items():
            print(f"\n{pair}:")
            for regime, s in by_r.items():
                if "wr" in s:
                    print(f"  {regime}: n={s['n']} WR={s['wr']:.3f} "
                          f"Wilson_lo={s['wilson_lower']:.3f} "
                          f"EV={s['ev_net_pip']:+.2f}p Sharpe={s['sharpe_pe']:.3f}")
                else:
                    print(f"  {regime}: n={s['n']} (insufficient)")
        return 0

    if args.stage == 1:
        print("=" * 60)
        print("  Stage 1 — Regime-Stratified Scan (BH-FDR primary)")
        print(f"  Pairs: {args.pairs} | Days: {args.days} (training only)")
        print(f"  Holdout reserved: last {HOLDOUT_DAYS_LOCK} days")
        print("=" * 60)
        scan = stage1_scan(days=args.days, pairs=args.pairs,
                           forwards=args.forwards)
        survivors = stage1_apply_gates(scan["results"], q=args.bh_q)
        print(f"\n=== Stage 1 Verdict ===")
        print(f"Total cells: {scan['n_cells']}")
        print(f"Survivors (all gates + BH-FDR q={args.bh_q}): {len(survivors)}")
        if survivors:
            print(f"\nTop 20 by EV_net_pip:")
            top = sorted(survivors, key=lambda x: -x["ev_net_pip"])[:20]
            for r in top:
                key = (f"S1 {r.get('regime')} h={r.get('hour_utc')}"
                       if r["stratification"] == "S1" else
                       f"S2 atr={r.get('atr_pct_60d_b')} bbpb={r.get('bbpb_15m_b')}"
                       if r["stratification"] == "S2" else
                       f"S3 {r.get('regime_from')}→{r.get('regime_to')}")
                print(f"  {r['pair']} {r['direction']} fw={r['forward_bars']} "
                      f"[{key}]: n={r['n_trades']} WR={r['wr']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} EV={r['ev_net_pip']:+.2f}p "
                      f"Sharpe={r['sharpe_per_event']:.3f}")

        # by-stratification breakdown
        by_strat = {}
        for r in survivors:
            by_strat[r["stratification"]] = by_strat.get(r["stratification"], 0) + 1
        print(f"\nSurvivors by stratification: {by_strat}")

        out = {
            "stage": 1,
            "params": {
                "days": args.days, "pairs": args.pairs,
                "forwards": args.forwards, "bh_q": args.bh_q,
                "holdout_days": HOLDOUT_DAYS_LOCK,
                "sl_atr": SL_ATR_MULT_LOCK, "tp_atr": TP_ATR_MULT_LOCK,
            },
            "n_cells_total": scan["n_cells"],
            "n_survivors": len(survivors),
            "survivors_by_stratification": by_strat,
            "all_results": scan["results"],
            "survivors": survivors,
        }
        json_path = out_dir / f"stage1_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")
        return 0

    if args.stage == 2:
        print("=" * 60)
        print("  Stage 2 — Holdout 90d OOS")
        print("=" * 60)
        if not args.input:
            print("ERROR: --input <stage1.json> required", file=sys.stderr)
            return 1
        with open(args.input) as f:
            stage1 = json.load(f)
        survivors_s1 = stage1.get("survivors", [])
        if not survivors_s1:
            print("Stage 1 had no survivors — Stage 2 cannot proceed")
            # Still write a stub
            out = {"stage": 2, "n_tested": 0, "n_survivors": 0,
                   "survivors": [], "note": "Stage 1 empty"}
            json_path = out_dir / f"stage2_{date_tag}.json"
            with open(json_path, "w") as f:
                json.dump(out, f, indent=2, default=str)
            print(f"\nJSON: {json_path}")
            return 0

        print(f"Stage 1 survivors: {len(survivors_s1)}")
        survivors_s2 = stage2_holdout(survivors_s1, days=args.days)
        print(f"\n=== Stage 2 Verdict ===")
        print(f"Tested: {len(survivors_s1)} | Survivors: {len(survivors_s2)}")
        if survivors_s2:
            for r in sorted(survivors_s2,
                            key=lambda x: -x["stage2_holdout"]["ev_net_pip"]):
                h = r["stage2_holdout"]
                print(f"  ✅ {r['pair']} {r['direction']} fw={r['forward_bars']} "
                      f"[{r['stratification']}]: holdout n={h['n']} "
                      f"WR={h['wr']:.3f} EV={h['ev_net_pip']:+.2f}p")

        out = {
            "stage": 2, "params": {"days": args.days,
                                    "holdout_days": HOLDOUT_DAYS_LOCK},
            "n_tested": len(survivors_s1),
            "n_survivors": len(survivors_s2),
            "survivors": survivors_s2,
            "all_holdout": survivors_s1,
        }
        json_path = out_dir / f"stage2_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")
        return 0

    print("ERROR: --stage 1|2 or --bonus required", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
