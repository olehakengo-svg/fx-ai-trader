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
) -> dict:
    """Return expected friction for a pair × session × mode combination.

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

    Returns
    -------
    dict with keys:
        spread_pips: float
        slippage_pips: float
        rt_friction_pips: float — base round-trip cost
        adjusted_rt_pips: float — base × mode_mult × session_mult
        expected_cost_pips: float — alias of adjusted_rt_pips for clarity
        friction_atr_ratio: float | None — adjusted / atr_pips (Scalp DEAD line判定用)
        bev_wr: float — break-even WR (loss = win for given friction/RR)
        pair: str (normalized)
        mode: str
        session: str
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
            "unsupported": True,
        }

    adjusted = base["rt_friction"] * mode_mult * sess_mult
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
        "unsupported": False,
    }


def list_supported_pairs() -> list[str]:
    """Return list of pairs in the friction DB."""
    return sorted(_PAIR_FRICTION.keys())


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
