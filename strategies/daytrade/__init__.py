"""
DaytradeEngine — デイトレ戦略群の統括エンジン。

全戦略を順番に評価し、最高スコアの候補を選択。
"""
from __future__ import annotations
import logging
from typing import Optional
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext

logger = logging.getLogger("daytrade_engine")

from strategies.daytrade.ema_cross import EmaCross
from strategies.daytrade.sr_fib_confluence import SrFibConfluence
from strategies.daytrade.dt_fib_reversal import DtFibReversal
from strategies.daytrade.dt_sr_channel import DtSrChannelReversal
from strategies.daytrade.ema200_reversal import Ema200TrendReversal


class DaytradeEngine:
    """デイトレ戦略群を統括するエンジン。"""

    def __init__(self):
        self.strategies: list[StrategyBase] = [
            EmaCross(),
            SrFibConfluence(),
            DtFibReversal(),
            DtSrChannelReversal(),
            Ema200TrendReversal(),
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
        _rejected = []
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
            try:
                result = strategy.evaluate(ctx)
                if result is not None:
                    candidates.append(result)
                    logger.debug(f"[{strategy.name}] ✅ {result.signal} score={result.score:.2f} conf={result.confidence}")
                else:
                    _rejected.append(strategy.name)
            except Exception as e:
                logger.error(f"[{strategy.name}] Error: {e}")
                _rejected.append(f"{strategy.name}(ERR)")
        if candidates:
            logger.info(f"[DaytradeEngine] {len(candidates)}候補: {', '.join(c.entry_type for c in candidates)} | rejected: {', '.join(_rejected)}")
        else:
            logger.debug(f"[DaytradeEngine] 全戦略None: {', '.join(_rejected)}")
        return candidates

    def select_best(self, candidates: list[Candidate]) -> Optional[Candidate]:
        """最高スコアの候補を選択。"""
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.score)
