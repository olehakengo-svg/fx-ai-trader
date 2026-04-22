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
from strategies.daytrade.htf_false_breakout import HtfFalseBreakout
from strategies.daytrade.london_session_breakout import LondonSessionBreakout
from strategies.daytrade.tokyo_nakane_momentum import TokyoNakaneMomentum
from strategies.daytrade.adx_trend_continuation import AdxTrendContinuation
from strategies.daytrade.sr_break_retest import SrBreakRetest
from strategies.daytrade.lin_reg_channel import LinRegChannel
from strategies.daytrade.orb_trap import OrbTrap
from strategies.daytrade.london_close_reversal import LondonCloseReversal
from strategies.daytrade.london_close_reversal_v2 import LondonCloseReversalV2
from strategies.daytrade.gbp_deep_pullback import GbpDeepPullback
from strategies.daytrade.turtle_soup import TurtleSoup
from strategies.daytrade.trendline_sweep import TrendlineSweep
from strategies.daytrade.inducement_ob import InducementOrderBlock
from strategies.daytrade.post_news_vol import PostNewsVol
from strategies.daytrade.london_ny_swing import LondonNySwing
from strategies.daytrade.gold_vol_break import GoldVolBreak
from strategies.daytrade.gold_trend_momentum import GoldTrendMomentum
from strategies.daytrade.jpy_basket_trend import JpyBasketTrend
from strategies.daytrade.squeeze_release_momentum import SqueezeReleaseMomentum
from strategies.daytrade.eurgbp_daily_mr import EurgbpDailyMR
from strategies.daytrade.dt_bb_rsi_mr import DtBbRsiMR
from strategies.daytrade.liquidity_sweep import LiquiditySweep
from strategies.daytrade.session_time_bias import SessionTimeBias
from strategies.daytrade.gotobi_fix import GotobiFix
from strategies.daytrade.xs_momentum import XsMomentum
from strategies.daytrade.hmm_regime_filter import HmmRegimeFilter
from strategies.daytrade.london_fix_reversal import LondonFixReversal
from strategies.daytrade.vix_carry_unwind import VixCarryUnwind
from strategies.daytrade.vol_spike_mr import VolSpikeMR
from strategies.daytrade.doji_breakout import DojiBreakout
# v9.1: Alpha探索戦略
from strategies.daytrade.alpha_intraday_seasonality import IntradaySeasonality
from strategies.daytrade.alpha_wick_imbalance import WickImbalanceReversion
from strategies.daytrade.alpha_atr_regime_break import AtrRegimeBreak


class DaytradeEngine:
    """デイトレ戦略群を統括するエンジン。"""

    def __init__(self):
        self.strategies: list[StrategyBase] = [
            EmaCross(),
            SrFibConfluence(),
            HtfFalseBreakout(),            # EUR/USD False Breakout Fade
            LondonSessionBreakout(),        # EUR/USD ロンドンセッションブレイクアウト
            TokyoNakaneMomentum(),          # USD/JPY 仲値リバーサル BUY専用
            AdxTrendContinuation(),         # ADX TC: トレンド押し目/戻り目 (Wilder 1978)
            SrBreakRetest(),               # SBR: SR Break & Retest (Edwards & Magee 1948)
            LinRegChannel(),               # LRC: Linear Regression Channel (Gauss-Markov)
            OrbTrap(),                     # ORB Trap: Opening Range Fakeout Reversal
            LondonCloseReversal(),         # LCR: London Close Wick Reversal (DISABLED)
            LondonCloseReversalV2(),       # LCR v2: H-2026-04-22-005 (UTC 20:30-21:00, push+RSI極値) — Sentinel
            GbpDeepPullback(),             # GBP Deep PB: BB-2σ/EMA50 deep pullback
            TurtleSoup(),                  # Turtle Soup: Liquidity Grab Reversal (Connors 1995)
            TrendlineSweep(),              # TL Sweep: Trendline Sweep Trap (Edwards & Magee)
            InducementOrderBlock(),        # IOB: Inducement & Order Block Trap (Kyle 1985)
            PostNewsVol(),                 # PNV: Post-News Volatility Run (Ederington 1993)
            LondonNySwing(),               # London H/L Break → 前日H/L (EUR/GBP専用)
            GoldVolBreak(),                # XAU BB(2.5σ) ATR surge breakout (RR 1:3)
            GoldTrendMomentum(),           # XAU Trend Momentum: EMA21 PB 順張り (Baur 2010)
            JpyBasketTrend(),              # JPYバスケットPO順張り (USD/EUR JPY専用)
            SqueezeReleaseMomentum(),      # SRM: Squeeze Release Momentum v3 (2段フィルター, EUR/GBP限定)
            EurgbpDailyMR(),               # EUR/GBP Daily MR: 20日レンジ極値フェード (日足MR)
            DtBbRsiMR(),                   # DT BB RSI MR: 15m BB%B+RSI14+Stoch 平均回帰 (Bollinger 1992)
            LiquiditySweep(),              # Liquidity Sweep: Wick構造ストップ狩りリバーサル (Osler 2003, Kyle 1985)
            SessionTimeBias(),             # STB: セッション時間帯通貨減価バイアス (Breedon & Ranaldo 2013)
            GotobiFix(),                   # 五十日仲値: USD/JPY BUY専用 (Bessho 2023, Ito & Yamada 2017)
            XsMomentum(),                  # XS Momentum: 通貨ペア内正規化モメンタム順張り (Menkhoff 2012)
            HmmRegimeFilter(),             # HMM Regime: 防御オーバーレイ (Nystrup 2024, シグナル生成なし)
            LondonFixReversal(),           # LFR: London 4pm Fix後のUSD反転 (Krohn et al. 2024, Melvin & Prins 2015)
            VixCarryUnwind(),              # VCU: VIXスパイク時キャリートレード巻き戻し (Brunnermeier et al. 2009)
            VolSpikeMR(),                  # Vol Spike MR: ボラスパイク平均回帰 (Osler 2003, USD/JPY専用)
            DojiBreakout(),                # Doji Breakout: 連続Doji圧縮→ブレイクアウト (Mandelbrot 1963)
            IntradaySeasonality(),         # Alpha#1: 日中リターン季節性 (Breedon & Ranaldo 2013)
            WickImbalanceReversion(),      # Alpha#2: ヒゲ不均衡平均回帰 (Osler 2003)
            AtrRegimeBreak(),              # Alpha#3: ATRレジーム転換ブレイクアウト (Engle 1982)
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
        # ATR=0ガード: ATR未算出時は全戦略スキップ (2026-04-05 audit fix)
        if ctx.atr <= 0:
            logger.debug("[DaytradeEngine] ATR<=0 → skip all strategies")
            return []
        candidates = []
        _rejected = []
        # SL最低距離フロア: ATR(14)×1.0（ノイズレベル以下のSL防止）
        _min_sl_dist = ctx.atr * 1.0
        # v7.2: XAU instrument → XAU専用戦略のみ評価
        # 根拠: FX戦略(sr_break_retest等)がXAUで誤発火→タイトSL→spread_sl_gate多発
        # _enabled_symbols に "XAUUSD" を含む戦略のみ通過 (GoldVolBreak / GoldTrendMomentum)
        _sym_clean = ctx.symbol.upper().replace("=X", "").replace("_", "").replace("/", "") if ctx.symbol else ""
        _is_xau = "XAU" in _sym_clean
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
            # XAU: _enabled_symbols に XAUUSD が含まれない戦略はスキップ
            if _is_xau:
                _strat_syms = getattr(strategy, '_enabled_symbols', None)
                if _strat_syms is None or "XAUUSD" not in _strat_syms:
                    _rejected.append(f"{strategy.name}(xau_skip)")
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
            logger.info(f"[DaytradeEngine] {len(candidates)}候補: {', '.join(c.entry_type for c in candidates)} | rejected: {', '.join(_rejected)}")
        else:
            logger.debug(f"[DaytradeEngine] 全戦略None: {', '.join(_rejected)}")
        return candidates

    def select_best(self, candidates: list[Candidate]) -> Optional[Candidate]:
        """最高スコアの候補を選択。"""
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.score)
