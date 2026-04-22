#!/usr/bin/env python3
"""Alpha158 Shadow Snapshot — Bonferroni 有意 factor を Live signal 時点で取得

目的:
  2026-04-22 alpha-factor-zoo スキャンで Bonferroni 有意 (α=1.28e-04) と
  判定された 5 factor の値を、任意のタイムスタンプ（Shadow signal fire 時点）
  で取得し、Shadow trade 記録と結合するためのユーティリティを提供する。

非侵襲:
  - live path / BT signal 関数は一切変更しない
  - 本モジュールは read-only スナップショット算出のみ
  - 呼び出し側（別ファイル）で Shadow N≥30 になったら post-hoc 有効性を評価

有意 factor (2026-04-22 USD_JPY 15m horizon=1):
  KSFT2   IC=-0.0429  (今バーの shift が大きい → 次バー逆行)
  KSFT    IC=-0.0420
  RSV10   IC=-0.0360  (10バー Stochastic 上端 → 次バー下落)
  ROC10   IC=-0.0339  (10バー ROC 上 → 次バー平均回帰)
  QTLD5   IC=+0.0307  (5バー 20%分位 > 現値 → 次バー上昇)

判断プロトコル (CLAUDE.md):
  - 単独 factor は |IC|≈0.03 で弱い → 既存戦略フィルター合成用
  - Shadow N≥30 & WF CV<1.0 両方クリアで live 昇格判断
  - α予算 daily 0.020 消費（別途 alpha_budget_tracker.py で記録）

Usage:
    from tools.alpha_factor_snapshot import snapshot_at

    snap = snapshot_at(pair="USD_JPY", tf="15m", ts="2026-04-22T10:00:00Z")
    # -> {"KSFT2": -0.012, "KSFT": -0.004, "RSV10": 0.72, "ROC10": 0.003, "QTLD5": -0.008, "ts": "...", "stale_bars": 0}
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.bt_data_cache import BTDataCache

# Bonferroni 有意 factor (2026-04-22 alpha-factor-zoo スキャン根拠)
SIGNIFICANT_FACTORS = ["KSFT2", "KSFT", "RSV10", "ROC10", "QTLD5"]

# factor 符号（IC の符号 → signal 方向の解釈）
# 負IC: 高値は次バー下落予兆、正IC: 高値は次バー上昇予兆
FACTOR_SIGN = {"KSFT2": -1, "KSFT": -1, "RSV10": -1, "ROC10": -1, "QTLD5": +1}


def _compute_factors(df: pd.DataFrame) -> pd.DataFrame:
    """5 factor を最新バーまで計算して返す。"""
    if len(df) < 70:
        return pd.DataFrame()
    o, c, h, l = df["Open"], df["Close"], df["High"], df["Low"]
    eps = 1e-12
    feats = pd.DataFrame(index=df.index)
    # KSFT / KSFT2
    feats["KSFT"] = (2 * c - h - l) / (o + eps)
    feats["KSFT2"] = (2 * c - h - l) / (h - l + eps)
    # RSV10
    rmax = h.rolling(10).max()
    rmin = l.rolling(10).min()
    feats["RSV10"] = (c - rmin) / (rmax - rmin + eps)
    # ROC10
    feats["ROC10"] = c.pct_change(10)
    # QTLD5
    feats["QTLD5"] = c.rolling(5).quantile(0.2) / (c + eps) - 1
    return feats[SIGNIFICANT_FACTORS]


def snapshot_at(pair: str, tf: str = "15m", ts: str | datetime | None = None,
                days: int = 90) -> dict[str, Any]:
    """ts 時点における 5 有意 factor を返す。

    Args:
        pair: "USD_JPY" 等
        tf:   "15m"（他TFは IC 未検証のため警告）
        ts:   ISO-8601 文字列 or datetime。None → 最新バー
        days: OHLC lookback 日数（rolling window=10 のため最低 5 日必要）

    Returns:
        {factor: value} + {ts, stale_bars, bar_time}
        データ取得失敗時は {"error": "..."} を含む dict
    """
    if tf != "15m":
        return {"error": f"tf={tf} not validated (alpha-factor-zoo is 15m only)"}

    cache = BTDataCache()
    df = cache.get(pair, tf, days=days)
    if df is None or len(df) < 70:
        return {"error": "insufficient_data"}

    # Normalize column case
    if "Close" not in df.columns:
        df = df.rename(columns={c: c.capitalize() for c in df.columns})

    feats = _compute_factors(df)
    if feats.empty:
        return {"error": "factor_compute_failed"}

    # Select nearest bar ≤ ts
    if ts is None:
        bar = feats.iloc[-1]
        bar_idx = feats.index[-1]
        stale_bars = 0
    else:
        if isinstance(ts, str):
            ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            ts_dt = ts
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)
        # Index must be timezone-aware for comparison
        idx = feats.index
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
            feats.index = idx
        before = feats[feats.index <= ts_dt]
        if before.empty:
            return {"error": "ts_before_cache_start"}
        bar = before.iloc[-1]
        bar_idx = before.index[-1]
        stale_bars = len(feats[feats.index > bar_idx])

    out: dict[str, Any] = {f: float(bar[f]) if pd.notna(bar[f]) else None for f in SIGNIFICANT_FACTORS}
    out["ts"] = str(ts) if ts else "latest"
    out["bar_time"] = bar_idx.isoformat()
    out["stale_bars"] = stale_bars
    return out


def composite_score(snap: dict[str, Any]) -> float | None:
    """5 factor を IC 符号で揃えた合成スコア (z-score 単純平均)。

    Shadow 段階では「スコア > median」の trade と「< median」の trade で
    WR 差を測定する。
    """
    vals = []
    for f in SIGNIFICANT_FACTORS:
        v = snap.get(f)
        if v is None:
            return None
        # Sign-align: 負IC factor は符号反転
        vals.append(FACTOR_SIGN[f] * v)
    return float(np.mean(vals)) if vals else None


if __name__ == "__main__":
    # Smoke test
    import json
    snap = snapshot_at("USD_JPY", "15m")
    snap["composite"] = composite_score(snap)
    print(json.dumps(snap, indent=2, default=str))
