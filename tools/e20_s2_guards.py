#!/usr/bin/env python3
"""e20_s2_guards.py — E20 S2 診断の必須ガード 3 点 + financing overlay.

位置づけ: e20-rate-differential-feasibility-2026-07-22 §6-3 が S2 レポート必須項目として
凍結した教訓ガード (hull-ratediff / D1 TSMOM の NULL 解剖由来) を、rapid_edge_probe の
外側で日次パネルとして計測する:
  1. 金利差 quintile 単調性 — within-pair quintile × fwd 5 営業日リターン (pips) +
     pooled Spearman IC (探索窓のみ、シグナルは lag 1bd)
  2. USD-neutrality — sign(signal) ポジションの net USD / gross (D1 TSMOM は 54% で NULL)
  3. regime slice — rapid_edge_probe の窓別 run (pre2022 / 2022) が担当。本ツールは
     年別 fwd5d 平均を補助出力
  4. financing overlay (§5-2) — 政策金利差ベース ±diff/365 − markup 1%/365 (価格建て pips)。
     rapid_edge_probe の EV_fric には financing が入っていないため、k=5d/10d 保有の
     期待 financing を per-pair で別掲する (S3 では EV primitive への実装が必須)。

探索窓のみ: シグナル CSV は 2022-12-31 で切断済み (e20_rates_ingest)、価格も
EXPLORE_END で物理スライス。fwd リターンの末尾は NaN 落ち (OOS 非接触)。

CLI: python3 tools/e20_s2_guards.py run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from tools import event_modality_lib as L  # noqa: E402

E20_DIR = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "e20")
MASSIVE_DIR = os.path.join(_REPO, "data", "cache", "massive")
EXPLORE_START = "2014-06-01"
EXPLORE_END = "2022-12-31"
FWD_BDAYS = 5
LAG_BDAYS = 1
MARKUP_PCT_PER_YEAR = 1.0  # §5-2: OANDA financing markup の保守見積り

VARIANTS = {
    "carry_level": "e20_carry_level.csv",
    "mom63_2y": "e20_mom63_2y.csv",
}


def load_signal(csv_name: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(E20_DIR, csv_name), parse_dates=["date"])
    return df.set_index("date").sort_index()


def load_daily_close(pair: str) -> pd.Series:
    """15m parquet → NY17 roll daily Close (L 規約)。探索窓で物理スライス。"""
    f = os.path.join(MASSIVE_DIR, f"{pair}_15m.parquet")
    if not os.path.exists(f):
        return pd.Series(dtype=float)
    m15 = pd.read_parquet(f)
    if m15.index.tz is None:
        m15.index = m15.index.tz_localize("UTC")
    m15 = m15.loc[(m15.index >= pd.Timestamp(EXPLORE_START, tz="UTC")) &
                  (m15.index < pd.Timestamp(EXPLORE_END, tz="UTC") + pd.Timedelta(days=1))]
    if m15.empty:
        return pd.Series(dtype=float)
    daily = L.build_daily_from_m15(m15)
    s = daily["Close"].copy()
    s.index = pd.DatetimeIndex(s.index).tz_localize(None)
    return s


def pair_frame(signal: pd.DataFrame, pair: str) -> pd.DataFrame:
    """1 ペアの (signal_lagged, close, fwd5d_pips) 日次フレーム (探索窓、行 = 営業日)。"""
    close = load_daily_close(pair)
    if close.empty or pair not in signal.columns:
        return pd.DataFrame()
    sig = signal[pair].shift(LAG_BDAYS)
    df = pd.DataFrame({"sig": sig}).join(close.rename("close"), how="inner")
    df = df.loc[EXPLORE_START:EXPLORE_END]
    pip = L.pip_size(pair)
    df["fwd"] = (df["close"].shift(-FWD_BDAYS) - df["close"]) / pip
    return df.dropna(subset=["sig", "fwd"])


def quintile_table(frames: dict) -> dict:
    """within-pair quintile → fwd5d 平均 (pips) を pooled 平均。+ pooled Spearman。"""
    per_q = {q: [] for q in range(5)}
    pooled_sig, pooled_fwd = [], []
    for pair, df in frames.items():
        if len(df) < 100 or df["sig"].nunique() < 5:
            continue
        q = pd.qcut(df["sig"].rank(method="first"), 5, labels=False)
        for k in range(5):
            per_q[k].append(float(df["fwd"][q == k].mean()))
        z = (df["sig"] - df["sig"].mean()) / (df["sig"].std() or 1.0)
        pooled_sig.extend(z.tolist())
        pooled_fwd.extend(df["fwd"].tolist())
    means = {f"Q{k+1}": (round(float(np.mean(v)), 2) if v else None)
             for k, v in per_q.items()}
    rho, p = stats.spearmanr(pooled_sig, pooled_fwd) if len(pooled_sig) > 50 else (None, None)
    vals = [v for v in means.values() if v is not None]
    monotone = bool(all(b >= a for a, b in zip(vals, vals[1:]))) if len(vals) == 5 else None
    return {"quintile_mean_fwd5d_pips": means,
            "monotone_increasing": monotone,
            "pooled_spearman_ic": None if rho is None else round(float(rho), 4),
            "pooled_spearman_p": None if p is None else round(float(p), 4),
            "n_days_pooled": len(pooled_fwd)}


def usd_neutrality(frames: dict) -> dict:
    """日次 net USD / gross。long pair = long BASE。USD レグ: USD_x = +1、x_USD = −1。"""
    pos = pd.DataFrame({pair: np.sign(df["sig"]) for pair, df in frames.items()})
    usd_leg = {p: (1 if p.startswith("USD_") else (-1 if p.endswith("_USD") else 0))
               for p in pos.columns}
    net = sum(pos[p] * usd_leg[p] for p in pos.columns)
    gross = pos.abs().sum(axis=1)
    ratio = (net.abs() / gross.replace(0, np.nan)).dropna()
    return {"mean_abs_net_usd_over_gross": round(float(ratio.mean()), 3),
            "median": round(float(ratio.median()), 3),
            "n_cross_pairs": int(sum(1 for v in usd_leg.values() if v == 0)),
            "n_pairs": len(usd_leg),
            "reference": "D1 TSMOM NULL 解剖: net/gross 54% で実質単一 USD ベット"}


def financing_overlay(frames: dict, carry: pd.DataFrame) -> dict:
    """sign(signal) 方向の期待 financing (pips/保有)。政策金利差ベース、markup 1%/yr。"""
    out = {}
    for pair, df in frames.items():
        if pair not in carry.columns:
            continue
        pol = carry[pair].shift(LAG_BDAYS).reindex(df.index)
        pip = L.pip_size(pair)
        day = (np.sign(df["sig"]) * pol / 100.0 - MARKUP_PCT_PER_YEAR / 100.0) \
            / 365.0 * df["close"] / pip
        day = day.dropna()
        if day.empty:
            continue
        out[pair] = {"mean_pips_5d_hold": round(float(day.mean() * 7), 2),
                     "mean_pips_10d_hold": round(float(day.mean() * 14), 2)}
    if out:
        out["_pooled_mean_pips_5d"] = round(
            float(np.mean([v["mean_pips_5d_hold"] for k, v in out.items()
                           if not k.startswith("_")])), 2)
    return out


def yearly_slice(frames: dict) -> dict:
    """補助: 年別 pooled mean(sign(sig)×fwd5d) pips (方向付き、摩擦なし)。"""
    rows = []
    for pair, df in frames.items():
        rows.append(pd.Series((np.sign(df["sig"]) * df["fwd"]).values,
                              index=df.index))
    allv = pd.concat(rows).sort_index()
    return {str(y): {"mean_directed_fwd5d_pips": round(float(g.mean()), 2),
                     "n_pair_days": int(len(g))}
            for y, g in allv.groupby(allv.index.year)}


def run() -> dict:
    carry_sig = load_signal(VARIANTS["carry_level"])
    result = {"tool": "e20_s2_guards", "stage": "S2_R3_DIAGNOSTIC",
              "verdict_authority": "NONE — 探索診断。live/tier 判断禁止",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "window": [EXPLORE_START, EXPLORE_END],
              "lag_bdays": LAG_BDAYS, "fwd_bdays": FWD_BDAYS,
              "markup_pct_per_year": MARKUP_PCT_PER_YEAR,
              "variants": {}}
    for variant, csv_name in VARIANTS.items():
        signal = load_signal(csv_name)
        frames = {}
        for pair in signal.columns:
            df = pair_frame(signal, pair)
            if not df.empty:
                frames[pair] = df
        result["variants"][variant] = {
            "pairs_used": sorted(frames.keys()),
            "guard1_monotonicity": quintile_table(frames),
            "guard2_usd_neutrality": usd_neutrality(frames),
            "guard3_yearly_slice": yearly_slice(frames),
            "financing_overlay": financing_overlay(frames, carry_sig),
        }
    os.makedirs(E20_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    path = os.path.join(E20_DIR, f"e20_s2_guards_{stamp}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"guards written: {os.path.relpath(path, _REPO)}")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode")
    sub.add_parser("run")
    args = parser.parse_args(argv)
    if args.mode != "run":
        parser.print_help()
        return 1
    res = run()
    for v, r in res["variants"].items():
        g1 = r["guard1_monotonicity"]
        g2 = r["guard2_usd_neutrality"]
        print(f"{v}: monotone={g1['monotone_increasing']} "
              f"IC={g1['pooled_spearman_ic']} (p={g1['pooled_spearman_p']}) "
              f"|netUSD|/gross={g2['mean_abs_net_usd_over_gross']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
