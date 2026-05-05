"""
ScalperEngine — スキャルプ戦略群の統括エンジン。

全戦略を順番に評価し、最高スコアの候補を選択。
選択後に共通フィルター（EMA200, HTF）を適用して最終シグナルを返す。
"""
from __future__ import annotations
import logging
import os
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
from strategies.scalp.vol_momentum import VolMomentumScalp
from strategies.scalp.ema_ribbon import EmaRibbonRide
from strategies.scalp.vol_surge import VolSurgeDetector
from strategies.scalp.london_shrapnel import LondonShrapnel
from strategies.scalp.gold_pips import GoldPipsHunter
from strategies.scalp.confluence_scalp import ConfluenceScalp
from strategies.scalp.ema_trend_scalp import EmaTrendScalp
from strategies.scalp.mtf_trend_follow_scalp import MtfTrendFollowScalp
from strategies.scalp.mtf_counter_trend_scalp import MtfCounterTrendScalp
from strategies.scalp.mtf_regime_trend_cascade_scalp import MtfRegimeTrendCascadeScalp
from strategies.scalp.mtf_regime_range_cascade_scalp import MtfRegimeRangeCascadeScalp
# MA-Generic Family v1 (2026-04-30, ma_generic_family_v1, rule:R1) — Sentinel
# v1b は Shadow 稼働開始 (BT 180d Tokyo/NY 6/6 PASS)、v1a/c/d は BT 失敗で再設計待ち
from strategies.scalp.ma_trend_perfect import MaTrendPerfect
# REDESIGN_PENDING: from strategies.scalp.ma_mr_hybrid import MaMrHybrid    # v1a 閾値厳しすぎ N=66 不足
# REDESIGN_PENDING: from strategies.scalp.ma_regime_switch import MaRegimeSwitch  # v1c regime classifier 機能不全
# REDESIGN_PENDING: from strategies.scalp.bb_rsi_ema_aligned import BbRsiEmaAligned  # v1d EMA200 整合が MR エッジ破壊


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
            VolMomentumScalp(),     # 順張りBBブレイク (ADX>=30, trend-following)
            EmaRibbonRide(),        # パーフェクトオーダー押し目 (12-17 UTC優先)
            VolSurgeDetector(),     # 出来高急増クライマックス反転/モメンタム初動 (全ペア)
            LondonShrapnel(),       # London/NY異常ヒゲ反転 (EUR/GBP専用)
            GoldPipsHunter(),       # XAU/USD 5m方向同期包み足 (Gold専用)
            ConfluenceScalp(),     # Triple Confluence + MSS (UTC 12-17, HTF Hard Block)
            EmaTrendScalp(),       # EMA21プルバック順張り (ADX>=20, BB中間帯, bb_rsiのGAP補完)
            MtfTrendFollowScalp(),    # 教科書 MTF 15m→5m→1m 順張り (USD_JPY/EUR_USD, low-spread hour only)
            MtfCounterTrendScalp(),   # 教科書 MTF 15m→5m→1m 逆張り (5m BB%B+RSI div, 固定小幅TP)
            MtfRegimeTrendCascadeScalp(),  # 別軸: spread_gate最上位 + 15m regime classifier + ema_pullback継承 (rule:R1)
            MtfRegimeRangeCascadeScalp(),  # 別軸: spread_gate最上位 + 15m regime=range + bb_rsi継承 (rule:R1)
            # MA-Generic Family v1 (2026-04-30, ma_generic_family_v1, rule:R1)
            # v1b のみ Shadow 稼働 (BT 180d Tokyo/NY 6/6 PASS, NY-only LIVE 昇格パス検証中)
            # v1a/c/d は BT 失敗で再設計フェーズ (詳細: pre-reg-ma-trend-perfect-2026-04-30.md)
            MaTrendPerfect(),       # v1b: H1+M15 大循環 + M5 EMA21 再ブレイク順張り
            # REDESIGN_PENDING MaMrHybrid(),     # v1a 再設計待ち
            # REDESIGN_PENDING MaRegimeSwitch(), # v1c 再設計待ち
            # REDESIGN_PENDING BbRsiEmaAligned(),# v1d 再設計待ち
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
        # ATR=0ガード: ATR未算出時は全戦略スキップ (2026-04-06 audit fix)
        if ctx.atr <= 0:
            logger.debug("[ScalperEngine] ATR<=0 → skip all strategies")
            return []
        candidates = []
        _rejected = []
        # SL最低距離フロア: ATR(14)×1.0（ノイズレベル以下のSL防止）
        _min_sl_dist = ctx.atr * 1.0
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

    # Phase 5 (2026-04-30 silent-strategies-reactivation, rule:R2):
    # Mirror DaytradeEngine.SHADOW_ALWAYS_STRATEGIES — Scalp strategies that
    # should always emit Shadow trades even when they lose the max-score race.
    # Default empty (no behavior change). Populate via curation OR set
    # LOG_SCALP_LOSERS_AS_SHADOW=1 env to force all non-winners through the
    # Shadow emit path. The env override is the data-accumulation lever for
    # roadmap Gate 1-4 — when enabled, Wilson_lo / Kelly become computable
    # for every scalp strategy regardless of score-race outcome.
    SHADOW_ALWAYS_STRATEGIES: frozenset = frozenset()

    def split_shadow_always(self, candidates: list[Candidate],
                            best: Optional[Candidate]) -> list[Candidate]:
        """select_best で敗北した候補のうち Shadow 強制 emit 対象を返す。

        Behavior:
          - LOG_SCALP_LOSERS_AS_SHADOW=1 → all non-best candidates
          - Else → only candidates whose entry_type is in SHADOW_ALWAYS_STRATEGIES
        """
        if not candidates:
            return []
        log_all = os.getenv("LOG_SCALP_LOSERS_AS_SHADOW", "0").lower() in ("1", "true", "yes")
        if log_all:
            return [c for c in candidates if c is not best]
        _shadow_always = self.SHADOW_ALWAYS_STRATEGIES
        if (os.environ.get("BB_RSI_REDESIGN_V2") == "1"
                and os.environ.get("BB_RSI_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"bb_rsi_reversion"}
        if (os.environ.get("BB_RSI_EMA_ALIGNED_REDESIGN_V2") == "1"
                and os.environ.get("BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"bb_rsi_ema_aligned"}
        if (os.environ.get("CONFLUENCE_SCALP_REDESIGN_V2") == "1"
                and os.environ.get("CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"confluence_scalp"}
        if (os.environ.get("EMA_PULLBACK_REDESIGN_V2") == "1"
                and os.environ.get("EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"ema_pullback"}
        if (os.environ.get("EMA_RIBBON_REDESIGN_V2") == "1"
                and os.environ.get("EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"ema_ribbon_ride"}
        if (os.environ.get("EMA_TREND_SCALP_REDESIGN_V2") == "1"
                and os.environ.get("EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"ema_trend_scalp"}
        if (os.environ.get("ENGULFING_BB_REDESIGN_V2") == "1"
                and os.environ.get("ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"engulfing_bb"}
        if (os.environ.get("GOLD_PIPS_REDESIGN_V2") == "1"
                and os.environ.get("GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"gold_pips_hunter"}
        if (os.environ.get("LONDON_BREAKOUT_REDESIGN_V2") == "1"
                and os.environ.get("LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"london_breakout"}
        return [c for c in candidates
                if c is not best
                and c.entry_type in _shadow_always]
