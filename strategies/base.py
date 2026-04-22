"""
StrategyBase — 全戦略の共通インターフェース。

各戦略は StrategyBase を継承し、evaluate() を実装する。
evaluate() は条件を評価して Candidate を返すか、None を返す。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


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

    def as_tuple(self) -> tuple:
        """旧形式の candidates タプルに変換（後方互換）。"""
        return (self.signal, self.confidence, self.sl, self.tp,
                self.reasons, self.entry_type, self.score)


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
