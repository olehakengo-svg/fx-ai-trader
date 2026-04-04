"""
ScalperEngine — スキャルプ戦略群の統括エンジン。

全戦略を順番に評価し、最高スコアの候補を選択。
選択後に共通フィルター（EMA200, HTF）を適用して最終シグナルを返す。
"""
from __future__ import annotations
import logging
from typing import Optional
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext

logger = logging.getLogger("scalper_engine")

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
from strategies.scalp.session_vol_expansion import SessionVolExpansion


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
            SessionVolExpansion(),  # EUR/USD ロンドンオープン圧縮ブレイク
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
        _rejected = []
        # SL最低距離フロア: ATR(14)×1.0（ノイズレベル以下のSL防止）
        _min_sl_dist = ctx.atr * 1.0 if ctx.atr > 0 else 0
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
            try:
                result = strategy.evaluate(ctx)
                if result is not None:
                    # SLフロア適用
                    if _min_sl_dist > 0:
                        if result.signal == "BUY" and (ctx.entry - result.sl) < _min_sl_dist:
                            result.sl = ctx.entry - _min_sl_dist
                        elif result.signal == "SELL" and (result.sl - ctx.entry) < _min_sl_dist:
                            result.sl = ctx.entry + _min_sl_dist
                    candidates.append(result)
                    logger.debug(f"[{strategy.name}] ✅ {result.signal} score={result.score:.2f} conf={result.confidence}")
                else:
                    _rejected.append(strategy.name)
            except Exception as e:
                logger.error(f"[{strategy.name}] Error: {e}")
                _rejected.append(f"{strategy.name}(ERR)")
        if candidates:
            logger.info(f"[ScalperEngine] {len(candidates)}候補: {', '.join(c.entry_type for c in candidates)} | rejected: {', '.join(_rejected)}")
        else:
            logger.info(f"[ScalperEngine] 全戦略None: {', '.join(_rejected)}")
        return candidates

    def select_best(self, candidates: list[Candidate]) -> Optional[Candidate]:
        """最高スコアの候補を選択。"""
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.score)
