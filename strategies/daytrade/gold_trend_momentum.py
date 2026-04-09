"""
Gold Trend Momentum — XAU/USD 15分足トレンドフォロー（EMA21プルバックエントリー）

学術的根拠:
  - Gold momentum: Baur & McDermott (2010, J Banking & Finance) —
    金は短中期で有意な正のモメンタムを示す
  - Erb & Harvey (2006, Financial Analysts Journal) —
    コモディティモメンタムの実証
  - ADX trend filter: Wilder (1978) — ADX>=20でトレンド存在を識別
  - Pullback entry: Covel (2004, Trend Following) —
    確立トレンド内の押し目で参入（ブレイクアウトの偽シグナル回避）

設計思想:
  XAU/USDの構造的モメンタム特性（安全資産フロー持続性）を活用。
  gold_vol_breakのATRサージ(1.3x)条件が厳しすぎて発火しない問題を
  プルバックアプローチで解決。EMA21回帰はトレンド中に頻繁に発生する
  自然なエントリーポイント。

  広いSL/TP(ATRベース)でスプレッドコストを自然に吸収:
  - SL ~120pip, TP ~250pip → spread_sl_gate 4.2% (閾値35%以下)
  - Round-trip 10pip / TP 250pip → spread_guard 4% (閾値40%以下)

エントリー:
  BUY:  ADX>=20 + EMA9>EMA21 + 直近4本でEMA21到達(PB) +
        陽線回復(Close>EMA9) + MACD-H正 or 反転 + DI gap>=5
  SELL: 対称

決済:
  SL: Swing L/H (8本) ± ATR×0.3, min ATR×1.2
  TP: ATR × 2.5
  MIN_RR: 1.5
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class GoldTrendMomentum(StrategyBase):
    name = "gold_trend_momentum"
    mode = "daytrade"
    enabled = True

    # ── パラメータ ──
    ADX_MIN = 20              # トレンド閾値 (Wilder 1978)
    DI_GAP_MIN = 5            # +DI/-DI 最小乖離
    PB_LOOKBACK = 4           # プルバック検出ウィンドウ (4本=1h on 15m)
    SWING_LOOKBACK = 8        # SL用Swing H/L検出ウィンドウ
    TP_ATR_MULT = 2.5         # TP = ATR(14) × 2.5
    SL_ATR_MULT = 1.2         # SL min = ATR(14) × 1.2
    SL_BUFFER = 0.3           # Swing L/H からのバッファ (ATR倍率)
    MIN_RR = 1.5              # 最小RR
    BODY_MIN_ATR = 0.25       # 確認足の最小ボディ (ATR倍率)

    _enabled_symbols = frozenset({"XAUUSD"})

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── シンボルフィルター ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        if ctx.df is None or len(ctx.df) < self.SWING_LOOKBACK + 2:
            return None

        if ctx.atr <= 0:
            return None

        # ── ADXフィルター ──
        if ctx.adx < self.ADX_MIN:
            return None

        # ── DIギャップ ──
        _di_gap = ctx.adx_pos - ctx.adx_neg
        if abs(_di_gap) < self.DI_GAP_MIN:
            return None

        # ── EMAトレンド判定 ──
        _ema_bull = ctx.ema9 > ctx.ema21
        _ema_bear = ctx.ema9 < ctx.ema21
        _di_bull = _di_gap > 0  # +DI > -DI
        _di_bear = _di_gap < 0  # -DI > +DI

        if not ((_ema_bull and _di_bull) or (_ema_bear and _di_bear)):
            return None  # EMAとDIの方向不一致

        # ── プルバック検出 ──
        # 直近PB_LOOKBACK本でEMA21にタッチ（Low <= EMA21 for BUY, High >= EMA21 for SELL）
        _df = ctx.df
        _pb_found = False

        if _ema_bull:
            for i in range(-self.PB_LOOKBACK, 0):
                try:
                    if float(_df["Low"].iloc[i]) <= ctx.ema21:
                        _pb_found = True
                        break
                except (IndexError, KeyError):
                    pass
        else:
            for i in range(-self.PB_LOOKBACK, 0):
                try:
                    if float(_df["High"].iloc[i]) >= ctx.ema21:
                        _pb_found = True
                        break
                except (IndexError, KeyError):
                    pass

        if not _pb_found:
            return None

        # ── 確認足チェック ──
        _body = abs(ctx.entry - ctx.open_price)
        if _body < ctx.atr * self.BODY_MIN_ATR:
            return None

        # ── MACD-H方向確認 ──
        _macdh_ok = False
        if _ema_bull:
            _macdh_ok = ctx.macdh > 0 or (ctx.macdh > ctx.macdh_prev)
        else:
            _macdh_ok = ctx.macdh < 0 or (ctx.macdh < ctx.macdh_prev)

        if not _macdh_ok:
            return None

        # ── シグナル生成 ──
        signal = None
        sl = 0.0
        tp = 0.0
        score = 2.5
        reasons = []
        _min_sl = ctx.atr * self.SL_ATR_MULT

        if _ema_bull and ctx.entry > ctx.open_price and ctx.entry > ctx.ema9:
            signal = "BUY"
            reasons.append(f"✅ XAU上昇トレンド(ADX={ctx.adx:.1f}≥{self.ADX_MIN}, +DI={ctx.adx_pos:.1f}>-DI={ctx.adx_neg:.1f})")
            reasons.append(f"✅ EMA21プルバック回復(EMA9={ctx.ema9:.2f}>EMA21={ctx.ema21:.2f})")
            reasons.append(f"✅ 陽線確認(Body={_body:.2f}≥ATR×{self.BODY_MIN_ATR}={ctx.atr*self.BODY_MIN_ATR:.2f})")

            # SL: 直近Swing Low - ATR buffer
            _swing_low = float(_df["Low"].iloc[-self.SWING_LOOKBACK:].min())
            _sl_dist = max(ctx.entry - _swing_low + ctx.atr * self.SL_BUFFER, _min_sl)
            sl = ctx.entry - _sl_dist
            tp = ctx.entry + ctx.atr * self.TP_ATR_MULT

        elif _ema_bear and ctx.entry < ctx.open_price and ctx.entry < ctx.ema9:
            signal = "SELL"
            reasons.append(f"✅ XAU下降トレンド(ADX={ctx.adx:.1f}≥{self.ADX_MIN}, -DI={ctx.adx_neg:.1f}>+DI={ctx.adx_pos:.1f})")
            reasons.append(f"✅ EMA21プルバック回復(EMA9={ctx.ema9:.2f}<EMA21={ctx.ema21:.2f})")
            reasons.append(f"✅ 陰線確認(Body={_body:.2f}≥ATR×{self.BODY_MIN_ATR}={ctx.atr*self.BODY_MIN_ATR:.2f})")

            # SL: 直近Swing High + ATR buffer
            _swing_high = float(_df["High"].iloc[-self.SWING_LOOKBACK:].max())
            _sl_dist = max(_swing_high - ctx.entry + ctx.atr * self.SL_BUFFER, _min_sl)
            sl = ctx.entry + _sl_dist
            tp = ctx.entry - ctx.atr * self.TP_ATR_MULT

        if signal is None:
            return None

        # ── RR検証 ──
        _tp_dist = abs(tp - ctx.entry)
        _sl_dist = abs(ctx.entry - sl)
        _rr = _tp_dist / max(_sl_dist, 1e-8)
        if _rr < self.MIN_RR:
            return None

        # ── スコアボーナス ──
        if ctx.adx >= 30:
            score += 0.6
            reasons.append(f"✅ 強トレンド(ADX={ctx.adx:.1f}≥30) +0.6")

        if abs(_di_gap) >= 15:
            score += 0.5
            reasons.append(f"✅ DI乖離大({abs(_di_gap):.1f}≥15) +0.5")

        # MACD-H加速
        if signal == "BUY" and ctx.macdh > 0 and ctx.macdh > ctx.macdh_prev:
            score += 0.3
        elif signal == "SELL" and ctx.macdh < 0 and ctx.macdh < ctx.macdh_prev:
            score += 0.3

        # HTF方向
        _htf_ag = ctx.htf.get("agreement", "mixed") if ctx.htf else "mixed"
        if (signal == "BUY" and _htf_ag == "bull") or (signal == "SELL" and _htf_ag == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_htf_ag}) +0.5")
        elif (signal == "BUY" and _htf_ag == "bear") or (signal == "SELL" and _htf_ag == "bull"):
            score -= 1.0
            reasons.append(f"⚠️ HTF逆行({_htf_ag}) -1.0")

        # BB幅拡大 (トレンド継続シグナル)
        _bb_width_pct = getattr(ctx, "bb_width_pct", 0) or 0
        if _bb_width_pct > 70:
            score += 0.3

        reasons.append(f"📊 RR={_rr:.1f} SL={sl:.2f} TP={tp:.2f} | ADX={ctx.adx:.1f} DI_gap={abs(_di_gap):.1f}")

        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
