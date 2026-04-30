"""Spread/Friction Hard Gate — top-priority scalp filter (rule:R1)

設計意図 (2026-04-29, 別軸 cascade scalp の Layer 0):
  走行中の mtf_trend_follow_scalp は friction_model_v2.hour_mult ≤ 0.95 を
  ソフトに利用するのみで、quoted spread / tick volume / ATR 比は見ていない。
  既存スカルプ戦略の敗因のひとつとして「スプレッド異常時にも発火している」
  という仮説に応えるため、戦略評価より前段に置く 4 重ハードゲートを提供する。

CLAUDE.md 4 原則準拠:
  - 動的検出のみ (静的時間ブロック禁止)
  - hour_mult / quoted spread / tick volume / ATR 比 は全て市場状態から導出
  - 攻撃機会を残しつつ、構造的に EV 負の cell のみを遮断する

呼び出し側 (例):
  blocked, info = should_block("USD_JPY", ctx.hour_utc, ctx.df)
  if blocked: return None  # 戦略は何も発火しない
"""
from __future__ import annotations
from typing import Optional, Tuple
import pandas as pd

from modules.friction_model_v2 import friction_for, hour_mult_for


# ─── 閾値 (BT で感度分析、初期値は friction-analysis.md 由来) ─────────
HOUR_MULT_MAX = 0.85          # 0.85 以下 (低スプレッド時間帯) のみ通過
QUOTED_SPREAD_MAX_PIPS = 1.2  # 静的 spread_pips (per-pair baseline) の上限
ADJUSTED_RT_MAX_PIPS = 2.5    # 動的 adjusted_rt_pips (mode×session×hour 補正後) の上限
TICK_VOLUME_RATIO_MIN = 0.4   # 直近15分平均 / 直前165分平均
ATR_SPREAD_RATIO_MIN = 1.5    # ATR / adjusted_rt_pips 下限 (摩擦の 1.5 倍 ATR で edge 余地)
                              # v2 (2026-04-30 smoke): 3.0 は USD_JPY 1m で 25% block 過大.
                              # 1.5 は ATR 2.25pip / adjusted 1.5pip で確保.


def _infer_session(hour_utc: int) -> str:
    """簡易セッション判定 (friction_model_v2 の Session 列挙に合わせる)."""
    h = int(hour_utc) if hour_utc is not None else 12
    if 7 <= h <= 11:
        return "London"
    if 12 <= h <= 16:
        return "overlap_LN"
    if 17 <= h <= 21:
        return "NY"
    if 0 <= h <= 6:
        return "Tokyo"
    return "Sydney"


def should_block(
    symbol: str,
    hour_utc: int,
    df_1m: Optional[pd.DataFrame] = None,
    *,
    pip_mult: int = 100,
) -> Tuple[bool, dict]:
    """Layer 0: スプレッド/摩擦ハードゲート。

    Parameters
    ----------
    symbol : str
        通貨ペア ('USD_JPY' / 'USDJPY=X' どちらも可)
    hour_utc : int
        UTC hour (0-23)
    df_1m : pd.DataFrame | None
        1m candles (volume + atr14 列を含む). None の場合は volume/ATR 系
        ゲートをスキップ (hour_mult / quoted spread のみ評価)。
    pip_mult : int
        100 (JPY) or 10000 (FX). df_1m.atr14 は価格単位なので pip 換算に使用。

    Returns
    -------
    (blocked, info)
        blocked : True なら戦略評価をスキップ
        info    : {"reason": str, "f": friction_dict, ...} 診断用
    """
    # 1) hour_mult ハードゲート
    h_mult = hour_mult_for(hour_utc)
    if h_mult > HOUR_MULT_MAX:
        return True, {"reason": "low_liquidity", "hour_mult": h_mult}

    # 2) friction_for で adjusted_rt_pips 取得
    f = friction_for(symbol, mode="Scalp", session=_infer_session(hour_utc), hour_utc=hour_utc)
    if f.get("unsupported"):
        return True, {"reason": "unsupported_pair", "f": f}
    spread = float(f.get("spread_pips", float("nan")))
    adj = float(f.get("adjusted_rt_pips", float("nan")))
    # 2-a) 静的 spread (per-pair baseline) — 低スプレッドペアのみ許容
    if spread != spread or spread > QUOTED_SPREAD_MAX_PIPS:
        return True, {"reason": "spread_high", "spread_pips": spread, "f": f}
    # 2-b) 動的 adjusted_rt (mode×session×hour 補正後) — 異常 widening 遮断
    if adj != adj or adj > ADJUSTED_RT_MAX_PIPS:
        return True, {"reason": "adjusted_rt_high", "adjusted_rt_pips": adj, "f": f}

    # 3) tick volume sanity (df_1m 提供時のみ)
    if df_1m is not None and "Volume" in df_1m.columns and len(df_1m) >= 180:
        try:
            recent = float(df_1m["Volume"].iloc[-15:].mean())
            baseline = float(df_1m["Volume"].iloc[-180:-15].mean())
            if baseline > 0 and recent < baseline * TICK_VOLUME_RATIO_MIN:
                return True, {"reason": "stale_market", "recent": recent, "baseline": baseline, "f": f}
        except Exception:
            pass  # volume 取得失敗時はスキップ (保守: 通過させる)

    # 4) ATR / spread 比 (df_1m 提供時のみ)
    if df_1m is not None:
        atr_pips = None
        if "atr14" in df_1m.columns:
            try:
                atr_price = float(df_1m["atr14"].iloc[-1])
                atr_pips = atr_price * pip_mult
            except Exception:
                atr_pips = None
        elif "atr" in df_1m.columns:
            try:
                atr_price = float(df_1m["atr"].iloc[-1])
                atr_pips = atr_price * pip_mult
            except Exception:
                atr_pips = None
        if atr_pips is not None and atr_pips > 0:
            ratio = atr_pips / max(adj, 0.1)
            if ratio < ATR_SPREAD_RATIO_MIN:
                return True, {"reason": "atr_spread_ratio_low", "ratio": ratio,
                              "atr_pips": atr_pips, "adjusted_rt_pips": adj, "f": f}

    return False, {"reason": "ok", "hour_mult": h_mult, "f": f}
