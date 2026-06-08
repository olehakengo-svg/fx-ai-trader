"""
StrategyBase — 全戦略の共通インターフェース。

各戦略は StrategyBase を継承し、evaluate() を実装する。
evaluate() は条件を評価して Candidate を返すか、None を返す。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Candidate:
    """戦略が生成するエントリー候補。"""
    signal: str          # "BUY" / "SELL"
    confidence: int      # 0-100
    sl: float
    tp: float
    reasons: list        # ["✅ ...", "⚠️ ..."]
    entry_type: str      # "bb_rsi_reversion" etc.
    score: float         # スコア（候補選択に使用）
    max_hold_bars: Optional[int] = None  # Optional strategy-specific BT time stop
    sr_meta: Optional[dict] = None
    # SIZE lever — Edge cell redesign 2026-06-08
    # (docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md).
    # Strategy can boost (1.5x) / reduce (0.5x) / pass (1.0x) per per-cell evidence.
    # Consumed by demo_trader._apply_candidate_lot_multiplier (added in Task 2).
    # Negative values clamped to 0 (= skip) downstream.
    lot_multiplier: float = 1.0

    def as_tuple(self) -> tuple:
        """旧形式の candidates タプルに変換（後方互換）。"""
        return (self.signal, self.confidence, self.sl, self.tp,
                self.reasons, self.entry_type, self.score)

    @staticmethod
    def sr_meta_from_level(level: Any, signal_price: float,
                           atr_at_signal: Optional[float]) -> dict:
        """Normalize a selected S/R level into oanda_audit metadata."""
        if isinstance(level, dict):
            price = level.get("price")
            strength = level.get("strength")
            touches = level.get("touches")
            days_span = level.get("days_span")
            is_strong = level.get("is_strong")
        else:
            price = level
            strength = touches = days_span = is_strong = None

        distance_atr = None
        try:
            atr = float(atr_at_signal) if atr_at_signal is not None else 0.0
            if atr > 0 and price is not None:
                distance_atr = round(abs(float(price) - float(signal_price)) / atr, 10)
        except (TypeError, ValueError):
            distance_atr = None

        return {
            "strength": float(strength) if strength is not None else None,
            "touches": int(touches) if touches is not None else None,
            "days_span": float(days_span) if days_span is not None else None,
            "is_strong": bool(is_strong) if is_strong is not None else None,
            "distance_atr": distance_atr,
        }

    @staticmethod
    def sr_meta_from_price(levels: list, price: float, signal_price: float,
                           atr_at_signal: Optional[float]) -> dict:
        """Find the weighted level nearest to price, then normalize it."""
        if not levels:
            return Candidate.sr_meta_from_level(price, signal_price, atr_at_signal)
        best = None
        best_dist = float("inf")
        for level in levels:
            try:
                level_price = float(level.get("price") if isinstance(level, dict) else level)
                dist = abs(level_price - float(price))
            except (TypeError, ValueError):
                continue
            if dist < best_dist:
                best = level
                best_dist = dist
        return Candidate.sr_meta_from_level(
            best if best is not None else price,
            signal_price,
            atr_at_signal,
        )


class StrategyBase:
    """全戦略の基底クラス。"""

    name: str = "unknown"          # 戦略識別子（entry_type と一致）
    mode: str = "scalp"            # "scalp" or "daytrade"
    enabled: bool = True           # False で無効化（A/Bテスト用）

    # Strategy type — drives confidence_v2 anti-trend penalty.
    # "trend" (default): legacy conf preserved (formula is trend-follow consistent).
    # "MR" / "reversal": ADX>25 → conf penalty (mean-reversion inverse-edge).
    # "pullback": ADX>31 → sharp conf penalty (strong trend = no pullback develops).
    # See: modules/confidence_v2.py and KB confidence-formula-root-cause-2026-04-22.md
    strategy_type: str = "trend"

    # 戦略固有のパラメータ（サブクラスでオーバーライド）
    # 学習エンジンから動的に調整可能
    params: dict = {}

    def evaluate(self, ctx) -> Optional[Candidate]:
        """
        市場状態 ctx を評価し、エントリー候補を返す。
        条件不成立なら None を返す。

        Args:
            ctx: SignalContext — 全インジケータ + レイヤー情報
        Returns:
            Candidate or None
        """
        raise NotImplementedError(f"{self.__class__.__name__}.evaluate()")
