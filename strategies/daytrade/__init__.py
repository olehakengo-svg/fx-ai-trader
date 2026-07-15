"""
DaytradeEngine — デイトレ戦略群の統括エンジン。

全戦略を順番に評価し、最高スコアの候補を選択。
"""
from __future__ import annotations
import logging
import os
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
from strategies.daytrade.sweep_reversion_eurgbp_late import SweepReversionEurgbpLate
from strategies.daytrade.dt_bb_rsi_mr import DtBbRsiMR
from strategies.daytrade.liquidity_sweep import LiquiditySweep
from strategies.daytrade.session_time_bias import SessionTimeBias
from strategies.daytrade.gotobi_fix import GotobiFix
from strategies.daytrade.xs_momentum import XsMomentum
from strategies.daytrade.xs_momentum_rsi import XsMomentumRsi
from strategies.daytrade.macd_rsi_pullback import MacdRsiPullback
from strategies.daytrade.hmm_regime_filter import HmmRegimeFilter
from strategies.daytrade.london_fix_reversal import LondonFixReversal
from strategies.daytrade.vix_carry_unwind import VixCarryUnwind
from strategies.daytrade.vol_spike_mr import VolSpikeMR
from strategies.daytrade.doji_breakout import DojiBreakout
# v9.1: Alpha探索戦略
from strategies.daytrade.alpha_intraday_seasonality import IntradaySeasonality
from strategies.daytrade.alpha_wick_imbalance import WickImbalanceReversion
from strategies.daytrade.alpha_atr_regime_break import AtrRegimeBreak
# v9.x (2026-04-23): T3 Tokyo Range Breakout — Minimum Live (USD_JPY BUY-only)
from strategies.daytrade.tokyo_range_breakout import TokyoRangeBreakout
# v10 (2026-04-27): SR Anti-Hunt 二段構え (5 majors Shadow 全走、KDE+hunt-aware SL)
from strategies.daytrade.sr_anti_hunt_bounce import SrAntiHuntBounce
# v11 (2026-05-13): SR Weighted Bounce — heavy wall reversal with composite weight gate (Shadow-only)
from strategies.daytrade.sr_weighted_bounce import SrWeightedBounce
# v11 (2026-05-13): SR Weighted Break — heavy wall breakout retest with composite weight gate (Shadow-only, break family pair of sr_weighted_bounce)
from strategies.daytrade.sr_weighted_break import SrWeightedBreak
from strategies.daytrade.sr_liquidity_grab import SrLiquidityGrab
from strategies.daytrade.pullback_to_liquidity_v1 import PullbackToLiquidityV1
# v11 (2026-04-27): Phase 2-5 audit-driven edges
from strategies.daytrade.cpd_divergence import CpdDivergence
from strategies.daytrade.vdr_jpy import VdrJpy
from strategies.daytrade.vsg_jpy_reversal import VsgJpyReversal
from strategies.daytrade.rsk_gbpjpy_reversion import RskGbpjpyReversion
from strategies.daytrade.mqe_gbpusd_fix import MqeGbpusdFix
# Phase 8 (2026-04-28): Track A 3-way interaction discovery (Sentinel override)
from strategies.daytrade.pd_eurjpy_h20_bbpb3_sell import PdEurJpyH20Bbpb3Sell
# 2026-05-20: Kalman D7 3-spec trend-follow portfolio (USDJPY M15)
# Reference: knowledge-base/wiki/strategies/kalman_d7_*.md
# Shadow-first quant の意図的例外 (user判断): regime-bound discretionary edge
from strategies.daytrade.kalman_d7_trend import (
    KalmanD7PODNFlip,
    KalmanD7EMA75Break,
    KalmanD7TrailATR,
)
from strategies.intraday.kalman_d7_v18e_jpy_cross import KalmanD7V18eJpyCross
# 2026-05-26: Pivot Detector v2.5 — EUR_USD M15 Long-Only MR (TV OOS PF 1.544, WR 64.29%, N=28)
# LIVE intentional exception (Path B, user judgment) — Rule 1 override, pre-reg LOCK
# Reference: knowledge-base/wiki/decisions/pivot_detector_v2_5_live_exception_2026_05_26.md
from strategies.daytrade.pivot_detector_v2_5 import PivotDetectorV25
# 2026-05-28: ZZ Pivot v60 + SizeReduce — EUR_USD M15 MR at Trend Extreme (peak/trough)
# LIVE intentional exception (Path B / Rule 1 override) — 3 stacked exceptions per user judgment:
# (1) Shadow skip → Live 1.0x direct, (2) WFO 3/3 directional only (p=0.125 not sig.), (3) manual review
# TV 1y OOS: PF 1.222 (baseline) → 1.294 (SizeReduce), WFO 3-fold ΔPF +24.9%/+4.0%/+7.6%
# Dual entry_type for SizeReduce: zz_pivot_v60_sr (1.0x lot) / zz_pivot_v60_sr_lo (0.5x lot)
# Memory: project_zz_pivot_v60_sr_live_queue_2026_05_28 / feedback_size_lever_beats_skip_filter
from strategies.daytrade.zz_pivot_v60_sr import ZzPivotV60Sr
# 2026-06-12: Hull x Donchian FADE — EUR_USD M15 compression-gated dual-confirmation fade
# LIVE intentional exception (user judgment) — Kalman D7 / carry_dip / ZZ v60 と同型。
# Holdout 2022-2026 (untouched): WR 78% / net+1.34p / PF 1.19 (忠実度BT, spread 0.6p込)。
# env HULL_DONCHIAN_FADE_LIVE_ENABLE=1 + MIN lot 1000u。card: wiki/strategies/hull_donchian_fade.md
from strategies.daytrade.hull_donchian_fade import HullDonchianFade


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
            SweepReversionEurgbpLate(),    # EUR/GBP LATE sweep戻りBUY: 12y grid唯一のBonferroni生存 (2026-06-12 LIVE例外)
            DtBbRsiMR(),                   # DT BB RSI MR: 15m BB%B+RSI14+Stoch 平均回帰 (Bollinger 1992)
            LiquiditySweep(),              # Liquidity Sweep: Wick構造ストップ狩りリバーサル (Osler 2003, Kyle 1985)
            SessionTimeBias(),             # STB: セッション時間帯通貨減価バイアス (Breedon & Ranaldo 2013)
            GotobiFix(),                   # 五十日仲値: USD/JPY BUY専用 (Bessho 2023, Ito & Yamada 2017)
            XsMomentum(),                  # XS Momentum: 通貨ペア内正規化モメンタム順張り (Menkhoff 2012)
            XsMomentumRsi(),               # v11 (2026-05-13): xs_momentum_rsi — H1 RSI direction filter variant (USD_JPY Live, TV Phase 2 Config 3 edge)
            MacdRsiPullback(),             # v11 (2026-05-14): macd_rsi_pullback — USD_JPY 1H MACD hist_dir + H1 RSI 60/40 gate trend-pullback (TV 3.5y BT canonical +EV, SCALP_SENTINEL shadow-first)
            HmmRegimeFilter(),             # HMM Regime: 防御オーバーレイ (Nystrup 2024, シグナル生成なし)
            LondonFixReversal(),           # LFR: London 4pm Fix後のUSD反転 (Krohn et al. 2024, Melvin & Prins 2015)
            VixCarryUnwind(),              # VCU: VIXスパイク時キャリートレード巻き戻し (Brunnermeier et al. 2009)
            VolSpikeMR(),                  # Vol Spike MR: ボラスパイク平均回帰 (Osler 2003, USD/JPY専用)
            DojiBreakout(),                # Doji Breakout: 連続Doji圧縮→ブレイクアウト (Mandelbrot 1963)
            IntradaySeasonality(),         # Alpha#1: 日中リターン季節性 (Breedon & Ranaldo 2013)
            WickImbalanceReversion(),      # Alpha#2: ヒゲ不均衡平均回帰 (Osler 2003)
            AtrRegimeBreak(),              # Alpha#3: ATRレジーム転換ブレイクアウト (Engle 1982)
            TokyoRangeBreakout(),          # T3: Tokyo Range UP breakout (Andersen-Bollerslev 1997, WFA STABLE_EDGE) — Minimum Live USD_JPY BUY-only (2026-04-23)
            SrAntiHuntBounce(),            # SR Anti-Hunt Bounce: KDE+hunt-aware SL (5 majors Shadow 全走 2026-04-27)
            SrLiquidityGrab(),             # SR Liquidity Grab: SMC post-hunt reversal (5 majors Shadow 全走 2026-04-27)
            SrWeightedBounce(),            # SR Weighted Bounce v1: heavy wall + composite weight gate (Shadow-only 2026-05-13)
            SrWeightedBreak(),             # SR Weighted Break v1: heavy wall breakout retest (Shadow-only 2026-05-13, break family pair)
            CpdDivergence(),               # Phase 2: EUR/GBP_USD cointegration breakdown convergence (Sentinel)
            VdrJpy(),                      # Phase 3: VWAP deviation reversion JPY-only (Sentinel)
            VsgJpyReversal(),              # Phase 4: EWMA vol surprise reversal EUR/GBP_JPY (Bonferroni 7 通過)
            RskGbpjpyReversion(),          # Phase 5: realized skewness reversion GBP_JPY (Bonferroni 13 通過)
            MqeGbpusdFix(),                # Phase 5: month-end fix reversal GBP_USD (Bonferroni 3, WR 69.8%)
            PdEurJpyH20Bbpb3Sell(),        # Phase 8 Track A: EUR_JPY hour=20 bbpb=3 SELL (Sentinel, override)
            DtFibReversal(),
            DtSrChannelReversal(),
            Ema200TrendReversal(),
            # 2026-05-20: Kalman D7 3-spec trend-follow portfolio (USDJPY M15)
            # Pre-reg LOCK: SPEC at knowledge-base/wiki/strategies/kalman_d7_*.md
            # BT 10.5mo: PF 3.866 / 2.087 / 1.181 — regime-bound (USDJPY uptrend期間)
            KalmanD7PODNFlip(),    # v17: SL 1.5×ATR, TP 5.0×ATR (PO-DN flip approx, max winner ride)
            KalmanD7EMA75Break(),  # v18f: SL 2.5×ATR, TP 2.5×ATR (mid winners)
            KalmanD7TrailATR(),    # v18e: SL 2.0×ATR, TP 1.5×ATR (small winners + broker trail recommended)
            # 2026-05-26: Pivot Detector v2.5 — EUR_USD M15 Long-Only Mean-Reversion
            # LIVE intentional exception (Path B / Rule 1 override per user judgment)
            # TV OOS (Feb-May 2026): PF 1.544, WR 64.29%, N=28, Wilson_lo ≈ 0.46
            # Pre-reg withdrawal: N=30 WR<35% or PF<1.0 demote / Max DD>8% emergency stop
            # Score ~4.0-5.0 (mid-tier) — needs LIVE_PROMOTE_LOSERS side-channel
            # Memory: project_pivot_detector_v2_5_live_exception_2026_05_26
            PivotDetectorV25(),
            # 2026-05-28: ZZ Pivot v60 + SizeReduce (EUR_USD M15 MR at Trend Extreme)
            # Dual entry_type: zz_pivot_v60_sr (1.0x normal) / zz_pivot_v60_sr_lo (0.5x loser zone)
            # Pre-reg withdrawal: N=30 WR<35% or PF<1.0 demote / MaxDD>1% emergency / 14日連敗停止
            # Memory: project_zz_pivot_v60_sr_live_queue_2026_05_28
            ZzPivotV60Sr(),
            # 2026-06-12: Hull x Donchian FADE (EUR_USD M15 compression-gated fade)
            # Pre-reg 撤退: LiveN>=10 EV<0 demote / N>=30 WR<55% or PF<1.0 demote
            # SHORTxmacro-UP cell N>=30 EV<-0.5p → SHORT lot 0.5x (SIZE lever)
            HullDonchianFade(),
        ]
        if (os.environ.get("KALMAN_D7_V18E_AUDJPY_SHADOW") == "1"
                or os.environ.get("KALMAN_D7_V18E_EURJPY_SHADOW") == "1"):
            self.strategies.append(KalmanD7V18eJpyCross())
        if os.environ.get("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2") == "1":
            self.strategies.append(PullbackToLiquidityV1())

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
            _enabled = strategy.enabled
            if (strategy.name == "sr_weighted_bounce"
                    and os.environ.get("SR_WEIGHTED_BOUNCE_ENABLE") == "1"):
                _enabled = True
            if (strategy.name == "sr_weighted_break"
                    and os.environ.get("SR_WEIGHTED_BREAK_ENABLE") == "1"):
                _enabled = True
            if not _enabled:
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

    # 2026-04-28 (sr-strategies-signal-track plan):
    # 戦略 score が低くても Shadow trade として無条件記録すべき戦略の集合。
    # select_best で他戦略に敗北しても Shadow N 蓄積路を残す。
    # 詳細: knowledge-base/wiki/decisions/sr-strategies-signal-track-2026-04-28.md
    #
    # 2026-04-28 R2 demotion (rule:R2):
    # 本番実測 4 日 / N=300 で sr_anti_hunt_bounce と sr_liquidity_grab 両戦略とも
    # EV<0 を確認 (USDJPY: EV=-1.41p WR=26%, EURUSD: EV=-1.12p WR=20%, ほか)。
    # SHADOW_EMIT 経路は Phase 8 cell_edge_audit の N に直接乗るため、EV<0 で
    # 強制 emit を継続するとデータ汚染で Wilson_BF / Bonferroni / Kelly が誤誘導
    # される。R2 警報閾値 (N>=30, EV<0) で **両戦略を SHADOW_ALWAYS から除外**。
    # 戦略本体の enabled=True は維持 → primary 競争で勝てば trade 化、shadow 強制
    # emit のみ停止。詳細: lesson-shadow-always-emit-cleanup-2026-04-28.md
    #
    # 2026-04-29 Phase 10 G2 promotion (rule:R3):
    # G1 BT 検証 (raw/audits/never_logged_diagnosis_2026-04-28.md) と G0a
    # production routing audit で 3 戦略が **Bonferroni-significant BT edge × prod
    # 0-fire** を実証:
    #   - vsg_jpy_reversal:    331 BT signals (EUR_JPY 145 + GBP_JPY 186), prod 0
    #   - rsk_gbpjpy_reversion:182 BT signals (GBP_JPY only),               prod 0
    #   - mqe_gbpusd_fix:       20 BT signals (GBP_USD only),                prod 0
    # Root cause: select_best max-score bottleneck — Phase 5 戦略の score 設計が
    # 4.0-6.0 のため、6+ score を出す確立済 strategy に primary slot で必ず敗北。
    # 構造バグとして R3 即修正 — SHADOW_EMIT 経路で N 蓄積を解禁し、N>=30 / EV<0
    # に達したら R2 で SHADOW_ALWAYS から除外 (sr_* と同じ flow)。
    # 詳細: wiki/decisions/phase10-g2-investigation-2026-04-29.md
    SHADOW_ALWAYS_STRATEGIES = frozenset({
        # 2026-05-07 volume emergency: vsg_jpy_reversal and mqe_gbpusd_fix
        # moved to PAIR_PROMOTED cells, so they must not also emit through
        # the shadow-always side path.
        "rsk_gbpjpy_reversion",   # Phase 5 (Bonferroni 13 通過, 2026-04-29 g2)
        # 2026-05-19 G2 follow-up (rule:R3): xs_momentum_rsi + macd_rsi_pullback
        # were registered 2026-05-13/14 with PAIR_PROMOTED (xs_momentum_rsi) /
        # SCALP_SENTINEL (macd_rsi_pullback) tiers, but neither was added to
        # the SHADOW_ALWAYS path. Production audit 5/14-5/19 (4 LDN-NY sessions,
        # base xs_momentum 5 USD_JPY shadow fires on 5/14) shows 0 prod fires
        # for both: select_best max-score bottleneck silently drops their
        # candidates. Safety-net path here ensures N shadow accumulation; the
        # Live-capable path is handled by LIVE_PROMOTE_LOSERS below.
        "xs_momentum_rsi",
        "macd_rsi_pullback",
    })

    # 2026-05-19 (rule:R3): PAIR_PROMOTED / SCALP_SENTINEL strategies that
    # were intended to fire as Live (PAIR_PROMOTED for xs_momentum_rsi USD_JPY,
    # shadow-first Live N>=30 path for macd_rsi_pullback) but lose select_best
    # competition to higher-score primaries (session_time_bias / london_fix_reversal
    # / vix_carry_unwind typically 6.0-6.5 vs xs_momentum_rsi ~5.6).
    #
    # Unlike SHADOW_ALWAYS_STRATEGIES (which force is_shadow=True via direct
    # open_trade), LIVE_PROMOTE_LOSERS emits go through demo_trader._tick_entry
    # so the PAIR_PROMOTED / Sentinel tier gates can decide Live vs Shadow
    # naturally. If demo_trader's slot/hedge/dedup constraints block the live
    # path, the trade still falls through to shadow recording.
    LIVE_PROMOTE_LOSERS = frozenset({
        "xs_momentum_rsi",       # PAIR_PROMOTED USD_JPY (user override 2026-05-13)
        "macd_rsi_pullback",     # SCALP_SENTINEL shadow-first (2026-05-14)
        # 2026-05-22 (rule:R3): same 2026-05-19 G2 bug recurrence — Kalman D7
        # trio was deployed 2026-05-20 (commit 1972bd8b) with intended LIVE
        # via KALMAN_D7_LIVE_ENABLE env (c7b4ab52, 2026-05-21) but never
        # registered in the side-channel. Score range 4.0-4.8 (base 4.0 +
        # ema200_bull 0.3 + adx25 0.3 + macdh 0.2) loses every select_best
        # competition to session_time_bias / london_fix_reversal /
        # vix_carry_unwind (typically 6.0-6.5). Result: prod audit
        # 2026-05-14..05-22 shows 0 kalman shadow fires despite 35 UP
        # transitions on USDJPY M15 (filter audit confirmed passing).
        # Memory: project_kalman_d7_regime_bound_live_2026_05_20
        "kalman_d7_po_dn_flip",     # v17 PF=3.866 BT (max winner ride)
        "kalman_d7_ema75_break",    # v18f PF=2.087 BT (balanced)
        "kalman_d7_trail_atr",      # v18e PF=1.181 BT (tight trail)
        # 2026-05-26 (rule:R1 EXCEPTION): Pivot Detector v2.5 — EUR_USD M15 Long-Only MR.
        # Same pattern as Kalman D7 trio: base score ~4.0-5.0 loses select_best to
        # session_time_bias / london_fix_reversal / vix_carry_unwind (~6.0-6.5).
        # Without LIVE_PROMOTE_LOSERS side-channel, prod fires=0 (silently dropped).
        # PAIR_PROMOTED EUR_USD with 1000u lot; demote path via watchdog.
        # Memory: project_pivot_detector_v2_5_live_exception_2026_05_26.
        "pivot_detector_v2_5",
        # 2026-06-12 (rule:R1 EXCEPTION): hull_donchian_fade — 同 select_best ボトルネック
        # の 5 回目回避 (Kalman/pivot/ZZ/sweep と同パターン)。score 3.0-5.0 は
        # session_time_bias 等 (~6.0-6.5) に敗北し side-channel 不在だと prod fires=0。
        # Codex review I-3 (2026-06-12)。
        "hull_donchian_fade",
        # 2026-06-12 (rule:R1 EXCEPTION): sweep_reversion_eurgbp_late — 同 select_best
        # ボトルネックの 6 回目回避。score 3.0-5.0 (sweep depth 依存) は同 bar の
        # 他候補に敗北し得る。hull の Codex review I-3 が「sweep も同パターン」と
        # 指摘 → side-channel 登録漏れを是正 (LIVE 投入同日)。
        # 12y grid survivor (N=543 t=4.46)、発火 3-4回/月、取り逃しは N 蓄積に致命的。
        # Memory: project_sweep_reversion_grid_survivor_2026_06_12.
        "sweep_reversion_eurgbp_late",
        # 2026-06-02 (rule:R3): same select_best max-score bottleneck — third
        # recurrence of 2026-05-19 / 2026-05-22 / 2026-05-26 bug pattern. ZZ
        # Pivot v60 SR was deployed 2026-05-28 (commit 068cc0db) as LIVE
        # intentional exception (PAIR_PROMOTED EUR_USD 1.0x / _lo 0.5x via
        # _PAIR_LOT_BOOST) but never registered in this side-channel. Score
        # base 4.0 (MR strategy, see strategies/daytrade/zz_pivot_v60_sr.py)
        # loses every select_best competition to session_time_bias /
        # vol_surge_detector (~5.0-6.0+) at the same M15 EUR_USD bar.
        #
        # Production evidence (knowledge-base/raw/audits/kalman-zz-zero-fire-
        # 2026-06-02.md): 6 filter-pass bars 2026-05-28..06-02, only 1 audit
        # row (2026-05-28 12:08 SELL), and that row was bridge_status=skipped
        # / shadow_tracking — the other 5 silently dropped at select_best
        # because session_time_bias / vol_surge_detector won by score.
        # Render log confirms: 06-02 12:31 [MTF_MONITOR] entry=session_time_bias,
        # 06-01 13:15 [MTF_MONITOR] entry=vol_surge_detector — never zz_pivot.
        #
        # Dual entry_type included: _sr (1.0x normal zone) + _sr_lo (0.5x
        # loser zone) match _PAIR_LOT_BOOST and _SHIELD_EUR_DT_WHITELIST.
        # Memory: project_zz_pivot_v60_sr_live_queue_2026_05_28,
        # feedback_label_empirical_audit, project_kalman_d7_silent_drop_recovery_2026_05_28.
        "zz_pivot_v60_sr",
        "zz_pivot_v60_sr_lo",
    })

    def select_best(self, candidates: list[Candidate]) -> Optional[Candidate]:
        """最高スコアの候補を選択。"""
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.score)

    def split_shadow_always(self, candidates: list[Candidate],
                             best: Optional[Candidate]) -> list[Candidate]:
        """SHADOW_ALWAYS_STRATEGIES に該当する候補で best 以外のものを返す。

        select_best で primary slot を取れなかった shadow-always strategy を
        Shadow trade として並行記録するための補助メソッド。
        """
        if not candidates:
            return []
        _shadow_always = self.SHADOW_ALWAYS_STRATEGIES
        if (os.environ.get("ADX_TREND_CONTINUATION_REDESIGN_V2") == "1"
                and os.environ.get("ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"adx_trend_continuation"}
        if (os.environ.get("ALPHA_ATR_REGIME_BREAK_REDESIGN_V2") == "1"
                and os.environ.get("ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"atr_regime_break"}
        if (os.environ.get("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2") == "1"
                and os.environ.get("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"intraday_seasonality"}
        if ((os.environ.get("WICK_IMBALANCE_REVERSION_REDESIGN_V2") == "1"
                and os.environ.get("WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE") == "1")
                or (os.environ.get("ALPHA_WICK_IMBALANCE_REDESIGN_V2") == "1"
                    and os.environ.get("ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE") == "1")):
            _shadow_always = _shadow_always | {"wick_imbalance_reversion"}
        if (os.environ.get("ASIA_RANGE_FADE_V1_REDESIGN_V2") == "1"
                and os.environ.get("ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"asia_range_fade_v1"}
        if (os.environ.get("CPD_DIVERGENCE_REDESIGN_V2") == "1"
                and os.environ.get("CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"cpd_divergence"}
        if (os.environ.get("DT_BB_RSI_MR_REDESIGN_V2") == "1"
                and os.environ.get("DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"dt_bb_rsi_mr"}
        if (os.environ.get("DT_SR_CHANNEL_REDESIGN_V2") == "1"
                and os.environ.get("DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"dt_sr_channel_reversal"}
        if (os.environ.get("EMA200_REVERSAL_REDESIGN_V2") == "1"
                and os.environ.get("EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"ema200_trend_reversal"}
        if (os.environ.get("EMA200_TREND_REVERSAL_REDESIGN_V2") == "1"
                and os.environ.get("EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"ema200_trend_reversal"}
        if (os.environ.get("EMA_CROSS_REDESIGN_V2") == "1"
                and os.environ.get("EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"ema_cross"}
        if (os.environ.get("FIB_REDESIGN_V2") == "1"
                and os.environ.get("FIB_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"dt_fib_reversal"}
        if (os.environ.get("GOLD_TREND_MOMENTUM_REDESIGN_V2") == "1"
                and os.environ.get("GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"gold_trend_momentum"}
        if (os.environ.get("GOLD_VOL_BREAK_REDESIGN_V2") == "1"
                and os.environ.get("GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"gold_vol_break"}
        if (os.environ.get("HTF_FALSE_BREAKOUT_REDESIGN_V2") == "1"
                and os.environ.get("HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"htf_false_breakout"}
        if (os.environ.get("INDUCEMENT_OB_REDESIGN_V2") == "1"
                and os.environ.get("INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"inducement_ob"}
        if (os.environ.get("JPY_BASKET_TREND_REDESIGN_V2") == "1"
                and os.environ.get("JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"jpy_basket_trend"}
        if (os.environ.get("LIN_REG_CHANNEL_REDESIGN_V2") == "1"
                and os.environ.get("LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"lin_reg_channel"}
        if (os.environ.get("LONDON_SESSION_BREAKOUT_REDESIGN_V2") == "1"
                and os.environ.get("LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"london_session_breakout"}
        if (os.environ.get("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2") == "1"
                and os.environ.get("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"tokyo_nakane_momentum"}
        if (os.environ.get("TOKYO_RANGE_BREAKOUT_REDESIGN_V2") == "1"
                and os.environ.get("TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"tokyo_range_breakout_up"}
        if (os.environ.get("LONDON_NY_SWING_REDESIGN_V2") == "1"
                and os.environ.get("LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"london_ny_swing"}
        if (os.environ.get("ORB_TRAP_REDESIGN_V2") == "1"
                and os.environ.get("ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"orb_trap"}
        if (os.environ.get("POST_NEWS_VOL_REDESIGN_V2") == "1"
                and os.environ.get("POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"post_news_vol"}
        if (os.environ.get("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2") == "1"
                and os.environ.get("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"pullback_to_liquidity_v1"}
        if (os.environ.get("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2") == "1"
                and os.environ.get("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"squeeze_release_momentum"}
        if (os.environ.get("XS_MOMENTUM_REDESIGN_V2") == "1"
                and os.environ.get("XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"xs_momentum"}
        if (os.environ.get("SR_BREAK_RETEST_REDESIGN_V2") == "1"
                and os.environ.get("SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"sr_break_retest"}
        if (os.environ.get("SR_FIB_CONFLUENCE_REDESIGN_V2") == "1"
                and os.environ.get("SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"sr_fib_confluence", "ob_retest"}
        if (os.environ.get("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2") == "1"
                and os.environ.get("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"sr_anti_hunt_bounce"}
        if (os.environ.get("SR_LIQUIDITY_GRAB_REDESIGN_V2") == "1"
                and os.environ.get("SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"sr_liquidity_grab"}
        if (os.environ.get("TRENDLINE_SWEEP_REDESIGN_V2") == "1"
                and os.environ.get("TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"trendline_sweep"}
        if (os.environ.get("TURTLE_SOUP_REDESIGN_V2") == "1"
                and os.environ.get("TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"turtle_soup"}
        if (os.environ.get("VDR_JPY_REDESIGN_V2") == "1"
                and os.environ.get("VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"vdr_jpy"}
        if (os.environ.get("VWAP_MEAN_REVERSION_REDESIGN_V2") == "1"
                and os.environ.get("VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"vwap_mean_reversion"}
        if (os.environ.get("SR_WEIGHTED_BOUNCE_ENABLE") == "1"
                and os.environ.get("SR_WEIGHTED_BOUNCE_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"sr_weighted_bounce"}
        if (os.environ.get("SR_WEIGHTED_BREAK_ENABLE") == "1"
                and os.environ.get("SR_WEIGHTED_BREAK_SHADOW_PROMOTE") == "1"):
            _shadow_always = _shadow_always | {"sr_weighted_break"}
        if (os.environ.get("KALMAN_D7_V18E_AUDJPY_SHADOW") == "1"
                or os.environ.get("KALMAN_D7_V18E_EURJPY_SHADOW") == "1"):
            _shadow_always = _shadow_always | {"kalman_d7_v18e"}
        return [c for c in candidates
                if c is not best
                and c.entry_type in _shadow_always]

    def split_live_promote_emits(self, candidates: list[Candidate],
                                  best: Optional[Candidate]) -> list[Candidate]:
        """LIVE_PROMOTE_LOSERS に該当する候補で best 以外のものを返す。

        2026-05-19 (rule:R3): PAIR_PROMOTED / SCALP_SENTINEL の Live 発火意図を
        持つ戦略 (xs_momentum_rsi USD_JPY, macd_rsi_pullback) が select_best
        max-score 競争で他 primary に負けて prod 0-fire になる構造バグを修正する
        ためのサイドチャネル。consumer (demo_trader) は通常の _tick_entry 経由で
        処理するため、PAIR_PROMOTED / Sentinel tier の live/shadow 判定が自然に
        効く。SHADOW_ALWAYS と二重 emit にならないよう、両 set を持つ戦略では
        consumer 側で 60s dedup が key 空間共有で抑止する。
        """
        if not candidates:
            return []
        return [c for c in candidates
                if c is not best
                and c.entry_type in self.LIVE_PROMOTE_LOSERS]

    # 2026-07-03 (rule:R3, P-S1(b)): HTF Hard Block shadow 退避対象。
    # v9.1 HTF Hard Block は候補リスト段階で除外するため、shadow/side-channel
    # の全記録経路より前に silent drop する。逆張り (MR) 戦略は発火瞬間が構造的
    # に counter-HTF なので kill 率 ~100% になり、4原則#3 (Shadow データ蓄積は
    # 削らない、2026-05-28 user 明文化) に違反する。ここに登録された戦略の
    # blocked 候補は shadow_emit_signals (is_shadow=1 強制) へ退避し、live 送信
    # はゼロのまま N 蓄積のみ復元する。live exemption (P-S1(a)) は別途 user 決裁。
    # 詳細: knowledge-base/wiki/analyses/zero-fire-diagnosis-carrydip-vix-2026-07-02.md §3
    HTF_BLOCK_SHADOW_RESCUE = frozenset({
        "sweep_reversion_eurgbp_late",  # 12y grid survivor, HTF gate なしで pre-reg 検証済み
    })

    def split_htf_block_shadow_rescue(self, blocked: list[Candidate],
                                      htf_agreement: str = "") -> list[Candidate]:
        """HTF Hard Block で除外された候補のうち shadow 退避対象を返す。

        戻り値の候補には [HTF_BLOCK_SHADOW_RESCUE] タグを付与し、通常 shadow と
        区別可能にする (P-S1(a) live exemption 決裁用のセグメント分離)。
        """
        if not blocked:
            return []
        rescued = []
        for c in blocked:
            if c.entry_type not in self.HTF_BLOCK_SHADOW_RESCUE:
                continue
            c.reasons = list(c.reasons or []) + [
                f"[HTF_BLOCK_SHADOW_RESCUE] htf={htf_agreement or '?'} — "
                f"live 経路は HTF Hard Block、shadow のみ記録 (4原則#3)"
            ]
            rescued.append(c)
        return rescued

    # 2026-07-07 (rule:R2): HTF mixed (4H+1D 不一致) 時に live 転送を停止する
    # 戦略×ペア セル。close_analysis タグ「⚖️ 4H+1D 不一致 → シグナル抑制中」は
    # 診断のみで、v9.1 HTF Hard Block は bull/bear 時しか候補を除外しない
    # (mixed = 候補フィルタ no-op)。本番 clean live (oanda_trade_id != '',
    # 2026-06-03..07-03): trendline_sweep×GBP_USD mixed N=15 EV=-3.38p/-50.7p
    # vs aligned N=4 +1.5p。shadow mixed N=7 EV=-7.20p が corroborate。
    # 30d 大負け4発 -53.6p (T1 forensic §7) は全て mixed タグ付き live。
    # blocked 候補は shadow 退避 (is_shadow=1) で N 蓄積継続 (4原則#3)。
    # 再 live 化は R1 (365d BT or clean live N>=30 + Bonferroni) のみ。
    # Ref: knowledge-base/wiki/analyses/mtf-mixed-gate-noop-forensic-2026-07-07.md
    #
    # 2026-07-15 (rule:R2): trendline_sweep は pre-reg
    # trendline_sweep_gbpusd_pairscope_2026-07-13 の執行で全セル
    # _PAIR_DEMOTED (demo_trader.py) へ demote 済み — 本 cell stop は
    # その部分集合 (HTF mixed 時のみ) だが、defense-in-depth として残置。
    # trendline_sweep×GBP_USD が将来 R1 で再LIVE化されても、この mixed
    # cell stop は独立に R1 解除されるまで有効のまま (矛盾なし)。
    HTF_MIXED_LIVE_STOP_CELLS = frozenset({
        ("trendline_sweep", "GBP_USD"),
    })

    def split_htf_mixed_live_stop(
            self, candidates: list[Candidate], symbol: str,
            htf_agreement: str = "") -> tuple[list[Candidate], list[Candidate]]:
        """HTF mixed 時に live 停止セルの候補を (残候補, shadow退避) に分割する。

        mixed 以外の agreement では無変換で返す (bull/bear は既存 v9.1
        Hard Block の責務)。停止候補には [HTF_MIXED_LIVE_STOP] タグを付与し、
        HTF_BLOCK_SHADOW_RESCUE 由来の shadow とセグメント分離可能にする。
        """
        if htf_agreement != "mixed" or not candidates:
            return list(candidates or []), []
        kept: list[Candidate] = []
        stopped: list[Candidate] = []
        for c in candidates:
            cell = (getattr(c, "entry_type", ""), symbol)
            if cell in self.HTF_MIXED_LIVE_STOP_CELLS:
                c.reasons = list(c.reasons or []) + [
                    "[HTF_MIXED_LIVE_STOP] htf=mixed — live 転送停止 "
                    "(rule:R2 clean live N=15 EV=-3.38p)、shadow のみ記録 (4原則#3)"
                ]
                stopped.append(c)
            else:
                kept.append(c)
        return kept, stopped
