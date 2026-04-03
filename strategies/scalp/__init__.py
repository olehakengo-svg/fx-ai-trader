"""
ScalperEngine — スキャルプ戦略群の統括エンジン。

全戦略を順番に評価し、最高スコアの候補を選択。
選択後に共通フィルター（EMA200, HTF）を適用して最終シグナルを返す。
"""
from __future__ import annotations
from typing import Optional
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext

# 各戦略をインポート
from strategies.scalp.bb_rsi import BBRsiReversion
from strategies.scalp.macdh import MacdhReversal
from strategies.scalp.stoch_pullback import StochTrendPullback
from strategies.scalp.squeeze import BBSqueezeBreakout
from strategies.scalp.fib import FibReversal
from strategies.scalp.ema_pullback import EmaPullback
from strategies.scalp.mtf_confluence import MtfReversalConfluence
from strategies.scalp.london_breakout import LondonBreakout
from strategies.scalp.trend_rebound import TrendRebound
from strategies.scalp.v_reversal import VReversal
from strategies.scalp.engulfing_bb import EngulfingBB
from strategies.scalp.three_bar_reversal import ThreeBarReversal
from strategies.scalp.sr_channel_reversal import SrChannelReversal


class ScalperEngine:
    """スキャルプ戦略群を統括するエンジン。"""

    def __init__(self):
        # 戦略リスト（評価順序は不問 — 最高スコアを選択）
        # enabled=False の戦略は evaluate_all() でスキップされる
        self.strategies: list[StrategyBase] = [
            BBRsiReversion(),
            BBSqueezeBreakout(),
            StochTrendPullback(),
            MacdhReversal(),
            FibReversal(),
            MtfReversalConfluence(),
            EmaPullback(),
            LondonBreakout(),
            TrendRebound(),
            VReversal(),
            EngulfingBB(),          # enabled=False
            ThreeBarReversal(),     # enabled=False
            SrChannelReversal(),    # enabled=False
        ]

    def get_strategy(self, name: str) -> Optional[StrategyBase]:
        """名前で戦略を取得。"""
        for s in self.strategies:
            if s.name == name:
                return s
        return None

    def evaluate_all(self, ctx: SignalContext) -> list[Candidate]:
        """全有効戦略を評価し、候補リストを返す。"""
        candidates = []
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
            try:
                result = strategy.evaluate(ctx)
                if result is not None:
                    candidates.append(result)
            except Exception as e:
                print(f"[ScalperEngine/{strategy.name}] Error: {e}")
        return candidates

    def select_best(self, candidates: list[Candidate]) -> Optional[Candidate]:
        """最高スコアの候補を選択。"""
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.score)
