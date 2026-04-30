"""v1b f3 macro forensic — USD/JPY 構造的レジーム変化の同定 (Tier 2)

Phase B Failure Condition #3 に従い、f3 (2026-02-09〜04-13) で v1b WR が
64%→56% に劣化した構造原因を価格アクション統計で定量化。

外部 news API なしで実施可能な regime metrics:
  - 週次 ATR 平均 (volatility level)
  - 週次 ADX 平均 (trend strength)
  - M15 perfect order 発火頻度 (v1b L3 ゲート通過率)
  - EMA21 break 後 N-bar continuation 確率 (v1b の真エッジ源)
"""
from __future__ import annotations
import sys
import math
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def compute_atr(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def compute_adx(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    up = h.diff(); dn = -l.diff()
    plus_dm = up.where((up > dn) & (up > 0), 0.0)
    minus_dm = dn.where((dn > up) & (dn > 0), 0.0)
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(n).mean()
    plus_di = 100 * (plus_dm.rolling(n).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(n).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.rolling(n).mean()


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def fold_stats(df, name, label):
    df = df.dropna()
    if len(df) == 0:
        return {"name": name, "label": label, "n": 0}
    return {
        "name": name, "label": label, "n": len(df),
        "atr_mean": float(df["atr"].mean()),
        "adx_mean": float(df["adx"].mean()),
        "po_any_pct": float((df["po_bull"] | df["po_bear"]).mean() * 100),
        "ema21_cross_count": int(df["ema21_cross"].sum()),
        "ema21_cross_continuation": (
            float(df.loc[df["ema21_cross"], "continuation_3bar"].mean() * 100)
            if df["ema21_cross"].sum() > 0 else 0.0
        ),
    }


def main():
    print("=" * 78)
    print("v1b f3 USD/JPY 構造解析 (Tier 2 macro forensic)")
    print("=" * 78)

    df = pd.read_parquet("data/cache/massive/USD_JPY_15m.parquet")
    df.index = pd.to_datetime(df.index, utc=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    df["atr"] = compute_atr(df, 14)
    df["adx"] = compute_adx(df, 14)
    df["ema9"] = ema(df["Close"], 9)
    df["ema21"] = ema(df["Close"], 21)
    df["ema50"] = ema(df["Close"], 50)
    df["po_bull"] = (df["ema9"] > df["ema21"]) & (df["ema21"] > df["ema50"])
    df["po_bear"] = (df["ema9"] < df["ema21"]) & (df["ema21"] < df["ema50"])
    df["ema21_cross"] = (df["Close"].shift(1) <= df["ema21"].shift(1)) & (df["Close"] > df["ema21"])
    df["continuation_3bar"] = (df["Close"].shift(-3) > df["Close"]) & df["ema21_cross"]

    f1 = df[(df.index >= "2025-10-17") & (df.index < "2025-12-11")]
    f2 = df[(df.index >= "2025-12-11") & (df.index < "2026-02-09")]
    f3 = df[(df.index >= "2026-02-09") & (df.index < "2026-04-13")]

    print()
    print("Fold-level price-action regime metrics (M15)")
    print("-" * 78)
    rows = [
        fold_stats(f1, "f1", "2025-10-17 → 2025-12-11"),
        fold_stats(f2, "f2", "2025-12-11 → 2026-02-09"),
        fold_stats(f3, "f3", "2026-02-09 → 2026-04-13"),
    ]
    print(f"{'fold':<5} {'period':<26} {'N':<6} {'ATR':<7} {'ADX':<7} {'PO%':<7} {'XCount':<7} {'XCont%':<8}")
    for r in rows:
        print(f"{r['name']:<5} {r['label']:<26} {r['n']:<6} {r['atr_mean']:<7.4f} {r['adx_mean']:<7.2f} {r['po_any_pct']:<7.2f} {r['ema21_cross_count']:<7} {r['ema21_cross_continuation']:<8.2f}")

    print()
    print("f1 vs f3 Δ — 何が劣化したか")
    print("-" * 78)
    f1s, f3s = rows[0], rows[2]
    print(f"{'metric':<30} {'f1':<12} {'f3':<12} {'Δ%':<10}")
    for k in ["atr_mean", "adx_mean", "po_any_pct", "ema21_cross_count",
              "ema21_cross_continuation"]:
        v1, v3 = f1s[k], f3s[k]
        pct = (v3 - v1) / v1 * 100 if v1 else 0
        print(f"{k:<30} {v1:<12.4f} {v3:<12.4f} {pct:<+10.2f}")

    print()
    print("結論:")
    if (f3s["atr_mean"] - f1s["atr_mean"]) / f1s["atr_mean"] > 0.10:
        print(f"  🔴 ATR vol expansion (+{(f3s['atr_mean']-f1s['atr_mean'])/f1s['atr_mean']*100:.1f}%) — vol regime mismatch が decay 主因")
    if abs(f3s["ema21_cross_continuation"] - f1s["ema21_cross_continuation"]) < 5:
        print(f"  ✓ EMA21 continuation 不変 — エッジ源は健全")
    else:
        d = f3s["ema21_cross_continuation"] - f1s["ema21_cross_continuation"]
        print(f"  EMA21 continuation Δ={d:+.1f}%")

    print()
    print(f"Phase B 監視 baseline (f3):")
    print(f"  ATR 14d 平均: {f3s['atr_mean']:.4f} (Failure #6: {f3s['atr_mean']*1.20:.4f} 以上で昇格中止)")
    print(f"  M15 perfect order 発火率: {f3s['po_any_pct']:.1f}% (Δ-5% で警報)")
    print(f"  EMA21 cross continuation: {f3s['ema21_cross_continuation']:.1f}% (Δ-5% で警報)")


if __name__ == "__main__":
    main()
