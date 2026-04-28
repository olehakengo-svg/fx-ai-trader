"""Friction Model v2 — Pair × Session × Mode aware friction estimation

目的:
  従来の BT_COST=1.0pip 固定モデルを置き換え、Live 実測 friction に基づく
  pair × session × mode 別の dynamic friction estimation を提供する。

背景 (2026-04-26 Edge Reset Phase 1.7):
  - bt-live-divergence.md: Scalp 摩擦が DT の 5.4× で同一 cost model が誤校正
  - friction-analysis.md: pair 別 RT_friction が 2.0-4.5pip と幅広い
  - 旧モデルでは Scalp 戦略の Live edge が構造的に過大評価されていた
  - Phase 3 新エッジ BT で「Live で再現する EV」を計算する前提

設計原則:
  - Pure data: friction-analysis.md の実測値を JSON 構造化
  - 副作用なし: BT 統合は本モジュールでは行わない (Phase 3 で配線)
  - Lookup-based: 通貨ペア × session × mode から定数 fetch
  - Backward compat: 既存 BT 経路を破壊しない

データソース:
  /Users/jg-n-012/test/fx-ai-trader/knowledge-base/wiki/analyses/friction-analysis.md
  最終更新: 2026-04-21 (commit a22fa14)
"""
from __future__ import annotations

from typing import Optional, Literal

# ─── Per-pair friction (RT = Round Trip, in pips) ─────────────────────
# Source: friction-analysis.md "Per-Pair Friction" 表 (post-v8.4 FX-only)
_PAIR_FRICTION: dict[str, dict[str, float]] = {
    "USD_JPY": {"spread": 0.7, "slippage": 0.5, "rt_friction": 2.14, "bev_wr": 0.344},
    "EUR_USD": {"spread": 0.7, "slippage": 0.5, "rt_friction": 2.00, "bev_wr": 0.397},
    "GBP_USD": {"spread": 1.3, "slippage": 1.0, "rt_friction": 4.53, "bev_wr": 0.379},
    "EUR_JPY": {"spread": 1.0, "slippage": 0.5, "rt_friction": 2.50, "bev_wr": 0.337},
    "GBP_JPY": {"spread": 1.5, "slippage": 0.8, "rt_friction": 3.50, "bev_wr": 0.380},
    # EUR_GBP and XAU_USD are stopped (structurally impossible / kill-switch)
}

# ─── Mode multipliers ────────────────────────────────────────────────
# bt-live-divergence.md: "DTとScalpで摩擦構造が5.4倍異なる" (friction/ATR base)
# Scalp ATR は DT より小さいため、絶対 friction 自体は同等だが ATR 比で大きく見える。
# ここでは絶対 pip ベースの multiplier を提供 (ATR 比較は呼び出し側で計算)。
_MODE_MULTIPLIER: dict[str, float] = {
    "DT":     1.0,    # Daytrade (15m, baseline)
    "Scalp":  1.05,   # 1m: わずかに広め (entry race)
    "Swing":  0.95,   # 1h-4h: 広めの market-order でほぼ同等、極小割引
    "default": 1.0,
}

# ─── Session multipliers (spread expansion) ───────────────────────────
# friction-analysis.md "Friction by Session" の FX-only 推定値ベース.
# London (0.86pip) を 1.0 として normalize.
_SESSION_MULTIPLIER: dict[str, float] = {
    "London":     1.00,    # Best (基準)
    "NY":         1.20,    # NY 移行帯はやや広い
    "Tokyo":     1.45,    # Asia 早朝で広がる
    "Sydney":     1.60,    # 流動性最低、最大
    "Asia_early": 1.55,    # Tokyo 始まる前 (00-02 UTC)
    "overlap_LN": 0.85,    # London-NY overlap (12-16 UTC) で最良
    "default":    1.10,    # session 不明時の保守値
}

# ─── Hour-of-day multipliers (UTC) ────────────────────────────────────
# Phase 8 post-mortem D6: session 粒度の friction 平均化が hour=20 (London
# close pre-window) のような流動性ピーク時の 30-40% spread 縮小を捉えられず、
# 該当 cell の EV を systematically 過小評価していた。
#
# 設計: session multiplier に追加で hour mult を乗じる。Hour mult は
# session base の更に細粒度補正で、平均が ~1.0 を目標に校正。
# 出典: friction-analysis.md daily spread profile + OANDA tick spread 観察。
#
# 乗算例: hour=20 NY session DT
#   adjusted = rt_friction × DT(1.0) × NY(1.20) × hour20(0.75) = 0.90×base
# vs Phase 8 までの NY session base 1.20×base — 25% 下方補正される。
_HOUR_MULTIPLIER_UTC: dict[int, float] = {
    # Asia thin overnight (UTC 22-00 = Sydney close, Tokyo not open)
    22: 1.30, 23: 1.30, 0: 1.25,
    # Tokyo open (UTC 0-3): liquidity ramp, JPY pairs improve
    1: 1.10, 2: 1.05, 3: 1.00,
    # Tokyo full (UTC 3-7): stable; JPY pairs benefit
    4: 0.95, 5: 0.95, 6: 0.95, 7: 0.95,
    # Tokyo-London handover (UTC 7-8): brief spread widen
    8: 1.05,
    # London open (UTC 8-12): liquidity peak start
    9: 0.90, 10: 0.90, 11: 0.90,
    # London-NY overlap (UTC 12-16): tightest spreads of the day
    12: 0.80, 13: 0.80, 14: 0.80, 15: 0.80,
    # NY full (UTC 16-19): NY trading dominant, EUR_USD/GBP_USD tighter
    16: 0.90, 17: 0.95, 18: 1.00, 19: 1.00,
    # London close window (UTC 20-21): liquidity surge from EOD flow
    # — Phase 8 hour=20 cells were systematically penalized by NY session
    #   1.20 multiplier; reality is closer to 0.90×base for fix-window flow.
    20: 0.75,
    21: 0.85,
}

# Sanity: hour multipliers should average ≈ 1.0 (session means do)
# weighted average of above is ~0.99 — acceptable.

Mode = Literal["DT", "Scalp", "Swing", "default"]
Session = Literal["London", "NY", "Tokyo", "Sydney", "Asia_early", "overlap_LN", "default"]


def _normalize_pair(pair: str) -> str:
    """Normalize pair to OANDA format ('USD_JPY')."""
    if not pair:
        return ""
    s = pair.upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


def friction_for(
    pair: str,
    mode: Mode = "DT",
    session: Session = "default",
    *,
    atr_pips: Optional[float] = None,
    hour_utc: Optional[int] = None,
) -> dict:
    """Return expected friction for a pair × session × mode × (optional) hour.

    Parameters
    ----------
    pair : str
        Currency pair ('USDJPY=X' / 'USD_JPY' / 'USD/JPY' all accepted)
    mode : str
        'DT' (default) | 'Scalp' | 'Swing'
    session : str
        'London' | 'NY' | 'Tokyo' | 'Sydney' | 'Asia_early' | 'overlap_LN' | 'default'
    atr_pips : float, optional
        ATR in pips for the bar/window. If provided, friction_atr_ratio is computed
        (Scalp戦略の摩擦評価用; bt-live-divergence.md "Scalp 5.4× DT" 解析用).
    hour_utc : int, optional
        UTC hour 0-23. When supplied, an hour-of-day multiplier is applied on
        top of the session multiplier. Phase 8 post-mortem (D6) showed that
        session-level averaging systematically over-penalised liquidity-peak
        cells like UTC 20 (London close fix flow). Out-of-range or None
        values fall back to neutral (1.0) so existing callers are unaffected.

    Returns
    -------
    dict with keys:
        spread_pips: float
        slippage_pips: float
        rt_friction_pips: float — base round-trip cost
        adjusted_rt_pips: float — base × mode_mult × session_mult × hour_mult
        expected_cost_pips: float — alias of adjusted_rt_pips for clarity
        friction_atr_ratio: float | None — adjusted / atr_pips (Scalp DEAD line判定用)
        bev_wr: float — break-even WR (loss = win for given friction/RR)
        pair: str (normalized)
        mode: str
        session: str
        hour_utc: int | None
        hour_multiplier: float — 1.0 if hour_utc not supplied or out of range
        unsupported: bool — True if pair not in DB

    Notes
    -----
    Source numbers from friction-analysis.md (post-v8.4 FX-only).
    EUR_GBP and XAU_USD return unsupported=True (stopped strategies).
    """
    p = _normalize_pair(pair)
    base = _PAIR_FRICTION.get(p)
    mode_mult = _MODE_MULTIPLIER.get(mode, _MODE_MULTIPLIER["default"])
    sess_mult = _SESSION_MULTIPLIER.get(session, _SESSION_MULTIPLIER["default"])
    hour_mult = (
        _HOUR_MULTIPLIER_UTC.get(int(hour_utc), 1.0)
        if hour_utc is not None and 0 <= int(hour_utc) <= 23
        else 1.0
    )

    if base is None:
        return {
            "spread_pips": float("nan"),
            "slippage_pips": float("nan"),
            "rt_friction_pips": float("nan"),
            "adjusted_rt_pips": float("nan"),
            "expected_cost_pips": float("nan"),
            "friction_atr_ratio": None,
            "bev_wr": float("nan"),
            "pair": p,
            "mode": mode,
            "session": session,
            "hour_utc": hour_utc,
            "hour_multiplier": hour_mult,
            "unsupported": True,
        }

    adjusted = base["rt_friction"] * mode_mult * sess_mult * hour_mult
    atr_ratio = None
    if atr_pips is not None and atr_pips > 0:
        atr_ratio = adjusted / atr_pips

    return {
        "spread_pips": base["spread"],
        "slippage_pips": base["slippage"],
        "rt_friction_pips": base["rt_friction"],
        "adjusted_rt_pips": adjusted,
        "expected_cost_pips": adjusted,  # alias
        "friction_atr_ratio": atr_ratio,
        "bev_wr": base["bev_wr"],
        "pair": p,
        "mode": mode,
        "session": session,
        "hour_utc": hour_utc,
        "hour_multiplier": hour_mult,
        "unsupported": False,
    }


def list_supported_pairs() -> list[str]:
    """Return list of pairs in the friction DB."""
    return sorted(_PAIR_FRICTION.keys())


# ─── Wave 2 / A3: Cost-aware Frequency Throttle ──────────────────────
# 出典: C3_Ishikawa Online DRL — spread 0.01%→0.05% で WR 59.5%→49.2%、
# Sharpe 2.04→0.68 と急落。コスト感度カーブが極めて急峻なので、
# 閾値超のセルでは取引頻度自体を絞る (confidence減衰 = effective gate)。
def cost_throttle_factor(
    pair: str,
    mode: Mode = "DT",
    session: Session = "default",
    *,
    threshold_ratio: float = 1.55,
    throttle: float = 0.7,
) -> tuple[float, dict]:
    """Return confidence multiplier based on adjusted/base friction ratio.

    adjusted_rt_pips / rt_friction_pips が threshold_ratio を超えるとき、
    confidence に throttle 倍率を掛けて取引頻度を絞る。

    Returns
    -------
    (factor, detail)
        factor : 1.0 (通常) または throttle 値 (例: 0.7) — confidence multiplier
        detail : {"ratio": float, "adjusted": float, "base": float, "applied": bool}

    Notes
    -----
    DT mode (mode_mult=1.0) では ratio = session_mult。
    threshold=1.55 (empirical, 2026-04-27 N1 audit): Tokyo Scalp(ratio=1.52, N=44 WR=61.4%
    EV=+5.89pip) を保護するため初期案 1.5 から引き上げ。
    発火: Sydney DT(1.60) / Asia_early DT(1.55, edge case) / Sydney Scalp(1.68)。
    非発火: Tokyo Scalp(1.52) / Tokyo DT(1.45) / overlap_LN(0.85) 等。
    """
    f = friction_for(pair, mode=mode, session=session)
    if f.get("unsupported"):
        return 1.0, {"ratio": None, "applied": False, "reason": "unsupported_pair"}
    base = f["rt_friction_pips"]
    adjusted = f["adjusted_rt_pips"]
    if base <= 0:
        return 1.0, {"ratio": None, "applied": False, "reason": "invalid_base"}
    ratio = adjusted / base
    applied = ratio >= threshold_ratio
    factor = throttle if applied else 1.0
    return factor, {
        "ratio": round(ratio, 3),
        "adjusted": round(adjusted, 3),
        "base": round(base, 3),
        "applied": applied,
    }


def is_scalp_dead(pair: str, atr_pips: float, threshold: float = 0.30) -> bool:
    """Return True if Scalp strategy is structurally dead for this pair given ATR.

    bt-live-divergence.md ベース: "Scalp JPY 摩擦/ATR 36.3% は DEAD line".
    threshold 30% を超えると edge 構築が数学的にほぼ不可能。

    Parameters
    ----------
    pair : str
    atr_pips : float
        Recent ATR in pips
    threshold : float
        Dead line ratio (default 0.30 = friction が ATR の 30% 以上で DEAD)
    """
    f = friction_for(pair, mode="Scalp", session="default", atr_pips=atr_pips)
    if f.get("unsupported") or f.get("friction_atr_ratio") is None:
        return True  # unsupported/unknown もまず DEAD 扱い (保守)
    return f["friction_atr_ratio"] >= threshold


def integrity_check() -> dict:
    """Sanity check: friction-analysis.md numerical integrity.

    Returns
    -------
    dict with 'ok' (bool) and 'errors' (list[str]).
    """
    errors = []
    for pair, vals in _PAIR_FRICTION.items():
        # spread + slippage <= rt_friction (within 0.5 pip tolerance)
        if vals["spread"] + vals["slippage"] > vals["rt_friction"] + 0.5:
            errors.append(
                f"{pair}: spread+slippage ({vals['spread']+vals['slippage']:.2f}) "
                f"exceeds rt_friction ({vals['rt_friction']:.2f}) — table inconsistent?"
            )
        # bev_wr should be in (0.30, 0.65) range
        if not (0.30 < vals["bev_wr"] < 0.65):
            errors.append(
                f"{pair}: bev_wr ({vals['bev_wr']:.3f}) outside expected range (0.30, 0.65)"
            )
    return {"ok": len(errors) == 0, "errors": errors}
