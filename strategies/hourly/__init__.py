"""
HourlyEngine — 1H足戦略群の統括エンジン。

DaytradeEngineと同一パターン: 全戦略を順番に評価し、最高スコアの候補を選択。
1H足特有の大きなTP/SL、トレーリングストップ対応。
"""
from __future__ import annotations
import logging
import os
from typing import Optional
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext

logger = logging.getLogger("hourly_engine")

from strategies.hourly.keltner_squeeze_breakout import KeltnerSqueezeBreakout
from strategies.hourly.donchian_momentum_breakout import DonchianMomentumBreakout
from strategies.hourly.ob_retest import ObRetestH1
from strategies.hourly.price_shock_rev_eur_gbp_h1_long import PriceShockRevEurGbpH1Long
from strategies.hourly.price_shock_rev_eur_aud_h1_long import PriceShockRevEurAudH1Long
from strategies.hourly.price_shock_rev_usd_cad_h1_long import PriceShockRevUsdCadH1Long
from strategies.hourly.price_shock_rev_nzd_jpy_h1_long import PriceShockRevNzdJpyH1Long
from strategies.hourly.price_shock_rev_aud_jpy_h1_long import PriceShockRevAudJpyH1Long


class HourlyEngine:
    """1H足戦略群を統括するエンジン。"""

    def __init__(self):
        self.strategies: list[StrategyBase] = [
            KeltnerSqueezeBreakout(),       # KSB: ケルトナースクイーズブレイクアウト (EUR専用)
            DonchianMomentumBreakout(),     # DMB: ドンチアンモメンタムブレイクアウト
            ObRetestH1(),                   # OB Retest H1: pre-reg FAIL, registered disabled for reevaluation
            PriceShockRevEurGbpH1Long(),    # Phase B-1 Shadow: EUR_GBP H1 1%-shock LONG
            PriceShockRevEurAudH1Long(),    # Phase B-1 Shadow: EUR_AUD H1 1%-shock LONG
            PriceShockRevUsdCadH1Long(),    # Phase B-1 Shadow: USD_CAD H1 1%-shock LONG
            PriceShockRevNzdJpyH1Long(),    # Phase B-1 Shadow: NZD_JPY H1 1%-shock LONG
            PriceShockRevAudJpyH1Long(),    # Phase B-1 Shadow: AUD_JPY H1 1%-shock LONG
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
        # SL最低距離フロア: ATR(14)×1.5 (1H足は15mより広い最低SL)
        _min_sl_dist = ctx.atr * 1.5 if ctx.atr > 0 else 0
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
                    logger.debug(
                        f"[{strategy.name}] ✅ {result.signal} "
                        f"score={result.score:.2f} conf={result.confidence}"
                    )
                else:
                    _rejected.append(strategy.name)
            except Exception as e:
                logger.error(f"[{strategy.name}] Error: {e}")
                _rejected.append(f"{strategy.name}(ERR)")
        if candidates:
            logger.info(
                f"[HourlyEngine] {len(candidates)}候補: "
                f"{', '.join(c.entry_type for c in candidates)} | "
                f"rejected: {', '.join(_rejected)}"
            )
        else:
            logger.debug(f"[HourlyEngine] 全戦略None: {', '.join(_rejected)}")
        return candidates

    def select_best(self, candidates: list[Candidate]) -> Optional[Candidate]:
        """最高スコアの候補を選択。"""
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.score)

    def split_shadow_always(self, candidates: list[Candidate],
                             best: Optional[Candidate]) -> list[Candidate]:
        """Opt-in shadow emit list for hourly redesign variants."""
        if not candidates:
            return []
        _shadow_always = frozenset({
            "price_shock_rev_eur_gbp_h1_long",
            "price_shock_rev_eur_aud_h1_long",
            "price_shock_rev_usd_cad_h1_long",
            "price_shock_rev_nzd_jpy_h1_long",
            "price_shock_rev_aud_jpy_h1_long",
        })
        if (os.environ.get("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2") == "1"
                and os.environ.get("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"donchian_momentum_breakout"}
        if (os.environ.get("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2") == "1"
                and os.environ.get("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"keltner_squeeze_breakout"}
        return [c for c in candidates
                if c is not best
                and c.entry_type in _shadow_always]
