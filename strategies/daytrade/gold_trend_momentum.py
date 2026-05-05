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
  BUY:  ADX>=20 + EMA9>EMA21 + 直近8本でEMA21到達/接近(PB) +
        陽線回復(Close>EMA9) + MACD-H正 or 反転 + DI gap>=5
  SELL: 対称

v7.3変更:
  - PB_LOOKBACK: 4→8 (1h→2h: 強トレンド中のプルバック間隔に対応)
  - プルバック検出緩和: Low <= EMA21 + ATR×0.3 (近接タッチを許容)
  - 強トレンドバイパス: ADX>=25 かつ DI gap>=10 → EMA21プルバック不要
    (強トレンド相場でEMA21到達を待つことの機会損失を解消)
    v7.4: ADX>=30, DI_gap>=15 → ADX>=25, DI_gap>=10 (15m足でより達成可能な閾値)

決済:
  SL: Swing L/H (8本) ± ATR×0.3, min ATR×1.2
  TP: ATR × 2.5
  MIN_RR: 1.5
"""
import os
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


class GoldTrendMomentum(StrategyBase):
    name = "gold_trend_momentum"
    mode = "daytrade"
    enabled = True

    # ── パラメータ ──
    ADX_MIN = 20              # トレンド閾値 (Wilder 1978)
    DI_GAP_MIN = 5            # +DI/-DI 最小乖離
    PB_LOOKBACK = 8           # v7.3: 4→8 プルバック検出ウィンドウ (8本=2h on 15m)
    SWING_LOOKBACK = 8        # SL用Swing H/L検出ウィンドウ
    TP_ATR_MULT = 2.5         # TP = ATR(14) × 2.5
    SL_ATR_MULT = 1.2         # SL min = ATR(14) × 1.2
    SL_BUFFER = 0.3           # Swing L/H からのバッファ (ATR倍率)
    MIN_RR = 1.5              # 最小RR
    BODY_MIN_ATR = 0.25       # 確認足の最小ボディ (ATR倍率)

    _enabled_symbols = frozenset({"XAUUSD"})
    _dedup_state: dict = {}

    @classmethod
    def reset_dedup_state(cls):
        cls._dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("GOLD_TREND_MOMENTUM_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if self._redesign_v2_enabled():
            return self._evaluate_redesign_v2(ctx)

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
        # 直近PB_LOOKBACK本でEMA21にタッチ or 近接
        # v7.3: Low <= EMA21 + ATR×0.3 (近接タッチを許容)
        # 根拠: 強トレンド中はEMA21に完全タッチせず0.3ATR手前で反発するケース多発。
        #       0.3ATR ≈ $6 (XAU ATR=$20想定) → EMA21近傍の押し目とみなす。
        _df = ctx.df
        _pb_found = False
        _pb_buffer = ctx.atr * 0.3  # EMA21近接バッファ (0.3ATR)

        if _ema_bull:
            for i in range(-self.PB_LOOKBACK, 0):
                try:
                    if float(_df["Low"].iloc[i]) <= ctx.ema21 + _pb_buffer:
                        _pb_found = True
                        break
                except (IndexError, KeyError):
                    pass
        else:
            for i in range(-self.PB_LOOKBACK, 0):
                try:
                    if float(_df["High"].iloc[i]) >= ctx.ema21 - _pb_buffer:
                        _pb_found = True
                        break
                except (IndexError, KeyError):
                    pass

        # ── 強トレンドバイパス ──
        # ADX>=25 かつ DI gap>=10 の強トレンド相場では
        # EMA21プルバック要件を免除 → トレンド継続エントリーに移行
        # 根拠: Wilder(1978) ADX>=25 = 強いトレンド (ADX>=30は"非常に強い"の上限)。
        #       15m足でADX>=30は稀。ADX25-29も十分なトレンド強度。
        #       金の強気相場(2026-04-) はEMA21に届かないまま継続上昇するケースが多発。
        #       プルバック待ちは機会損失 → 強トレンド中は現在のモメンタムで参入。
        #       DI gap>=10: +DI/-DI の明確な方向性確認 (>=15より達成しやすい閾値)
        _extreme_momentum = ctx.adx >= 25 and abs(_di_gap) >= 10
        if not _pb_found and not _extreme_momentum:
            return None

        # ── 確認足チェック ──
        _body = abs(ctx.entry - ctx.open_price)
        if _body < ctx.atr * self.BODY_MIN_ATR:
            return None

        # ── MACD-H方向確認 ──
        # 強トレンドバイパス中はMACD-Hを必須条件から除外。
        # 根拠: パラボリック上昇後のトップ付近でMACD-Hが負に転じることは頻発するが、
        #       ADX>=25+DI_gap>=10の強トレンド環境ではMACD-H陰転はトレンド終了ではなく
        #       モメンタム減速の一時的状態。ADX/DIが強トレンドを示す限り、
        #       MACD-Hが回復する前に機会を逃すコストが高い。
        # 通常プルバックエントリーではMACD-Hを維持（フィルター品質保持）。
        _macdh_ok = False
        if _ema_bull:
            _macdh_ok = ctx.macdh > 0 or (ctx.macdh > ctx.macdh_prev)
        else:
            _macdh_ok = ctx.macdh < 0 or (ctx.macdh < ctx.macdh_prev)

        if not _macdh_ok and not _extreme_momentum:
            return None  # 通常モード: MACD-H必須。強トレンドバイパス中はスキップ

        # ── シグナル生成 ──
        signal = None
        sl = 0.0
        tp = 0.0
        score = 2.5
        reasons = []
        _min_sl = ctx.atr * self.SL_ATR_MULT

        # extreme_momentum時はentry>ema9を免除: EMA9が価格に追随してギリギリ上に来ることで
        # 機会を逃すケースが多発。ADX/DI確認済みならEMA9条件は重複フィルター。
        _bull_ema9_ok = ctx.entry > ctx.ema9 or _extreme_momentum
        _bear_ema9_ok = ctx.entry < ctx.ema9 or _extreme_momentum

        if _ema_bull and ctx.entry > ctx.open_price and _bull_ema9_ok:
            signal = "BUY"
            _mode_label = "強トレンド継続" if (_extreme_momentum and not _pb_found) else "EMA21プルバック"
            reasons.append(f"✅ XAU上昇トレンド(ADX={ctx.adx:.1f}≥{self.ADX_MIN}, +DI={ctx.adx_pos:.1f}>-DI={ctx.adx_neg:.1f}) [{_mode_label}]")
            reasons.append(f"✅ EMA9={ctx.ema9:.2f}>EMA21={ctx.ema21:.2f} + 陽線Body={_body:.2f}")

            if _extreme_momentum and not _pb_found:
                # 強トレンドバイパス: ATR固定SL使用 (swing lowが遠すぎてRR崩壊防止)
                # RR = TP_ATR_MULT / SL_ATR_MULT = 2.5/1.2 = 2.08 (MIN_RR=1.5 通過保証)
                _sl_dist = _min_sl  # = ATR * 1.2
            else:
                # 通常: 直近Swing Low - ATR buffer
                _swing_low = float(_df["Low"].iloc[-self.SWING_LOOKBACK:].min())
                _sl_dist = max(ctx.entry - _swing_low + ctx.atr * self.SL_BUFFER, _min_sl)
            sl = ctx.entry - _sl_dist
            tp = ctx.entry + ctx.atr * self.TP_ATR_MULT

        elif _ema_bear and ctx.entry < ctx.open_price and _bear_ema9_ok:
            signal = "SELL"
            _mode_label = "強トレンド継続" if (_extreme_momentum and not _pb_found) else "EMA21プルバック"
            reasons.append(f"✅ XAU下降トレンド(ADX={ctx.adx:.1f}≥{self.ADX_MIN}, -DI={ctx.adx_neg:.1f}>+DI={ctx.adx_pos:.1f}) [{_mode_label}]")
            reasons.append(f"✅ EMA9={ctx.ema9:.2f}<EMA21={ctx.ema21:.2f} + 陰線Body={_body:.2f}")

            if _extreme_momentum and not _pb_found:
                _sl_dist = _min_sl  # = ATR * 1.2
            else:
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

    def _signal_bar_time(self, ctx: SignalContext):
        try:
            return ctx.df.index[-2]
        except Exception:
            return ctx.bar_time

    def _dedup_seen(self, ctx: SignalContext, signal: str, signal_bar_time) -> bool:
        key = (
            ctx.symbol.upper().replace("=X", "").replace("_", "").replace("/", ""),
            self.name,
            signal_bar_time,
        )
        if key in self._dedup_state:
            return True
        self._dedup_state[key] = signal
        return False

    def _evaluate_redesign_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        """V2 shadow variant: closed signal bar, current/next-bar execution, dedup."""
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "").replace("/", "")
        if _sym not in self._enabled_symbols:
            return None

        _min_bars = max(self.PB_LOOKBACK, self.SWING_LOOKBACK) + 3
        if ctx.df is None or len(ctx.df) < _min_bars:
            return None

        _df = ctx.df
        signal_bar = _df.iloc[-2]
        prev_signal_bar = _df.iloc[-3]
        signal_bar_time = self._signal_bar_time(ctx)

        _atr = float(signal_bar.get("atr", ctx.atr))
        if _atr <= 0:
            return None

        _adx = float(signal_bar.get("adx", ctx.adx))
        if _adx < self.ADX_MIN:
            return None

        _adx_pos = float(signal_bar.get("adx_pos", ctx.adx_pos))
        _adx_neg = float(signal_bar.get("adx_neg", ctx.adx_neg))
        _di_gap = _adx_pos - _adx_neg
        if abs(_di_gap) < self.DI_GAP_MIN:
            return None

        _ema9 = float(signal_bar.get("ema9", ctx.ema9))
        _ema21 = float(signal_bar.get("ema21", ctx.ema21))
        _ema_bull = _ema9 > _ema21
        _ema_bear = _ema9 < _ema21
        _di_bull = _di_gap > 0
        _di_bear = _di_gap < 0
        if not ((_ema_bull and _di_bull) or (_ema_bear and _di_bear)):
            return None

        _pb_window = _df.iloc[-self.PB_LOOKBACK - 1:-1]
        if len(_pb_window) < self.PB_LOOKBACK:
            return None

        _pb_buffer = _atr * 0.3
        if _ema_bull:
            _pb_found = bool((_pb_window["Low"].astype(float) <= _ema21 + _pb_buffer).any())
        else:
            _pb_found = bool((_pb_window["High"].astype(float) >= _ema21 - _pb_buffer).any())

        _extreme_momentum = _adx >= 25 and abs(_di_gap) >= 10
        if not _pb_found and not _extreme_momentum:
            return None

        _sig_open = float(signal_bar["Open"])
        _sig_close = float(signal_bar["Close"])
        _body = abs(_sig_close - _sig_open)
        if _body < _atr * self.BODY_MIN_ATR:
            return None

        _macdh = float(signal_bar.get("macd_hist", ctx.macdh))
        _macdh_prev = float(prev_signal_bar.get("macd_hist", ctx.macdh_prev))
        if _ema_bull:
            _macdh_ok = _macdh > 0 or (_macdh > _macdh_prev)
        else:
            _macdh_ok = _macdh < 0 or (_macdh < _macdh_prev)
        if not _macdh_ok and not _extreme_momentum:
            return None

        entry = ctx.entry
        _min_sl = _atr * self.SL_ATR_MULT
        score = 2.5
        reasons = []
        signal = None
        sl = 0.0
        tp = 0.0

        if _ema_bull and _sig_close > _sig_open and _sig_close > _ema9:
            signal = "BUY"
            _mode_label = "strong-trend continuation" if (_extreme_momentum and not _pb_found) else "EMA21 pullback"
            reasons.append(
                f"✅ GOLD_TREND_MOMENTUM_REDESIGN_V2 closed-bar BUY signal={signal_bar_time} [{_mode_label}]"
            )
            reasons.append(f"✅ closed confirmation: Close={_sig_close:.2f}>Open={_sig_open:.2f}, EMA9={_ema9:.2f}")
            if _extreme_momentum and not _pb_found:
                _sl_dist = _min_sl
            else:
                _swing_low = float(_pb_window["Low"].astype(float).tail(self.SWING_LOOKBACK).min())
                _sl_dist = max(entry - _swing_low + _atr * self.SL_BUFFER, _min_sl)
            sl = entry - _sl_dist
            tp = entry + _atr * self.TP_ATR_MULT

        elif _ema_bear and _sig_close < _sig_open and _sig_close < _ema9:
            signal = "SELL"
            _mode_label = "strong-trend continuation" if (_extreme_momentum and not _pb_found) else "EMA21 pullback"
            reasons.append(
                f"✅ GOLD_TREND_MOMENTUM_REDESIGN_V2 closed-bar SELL signal={signal_bar_time} [{_mode_label}]"
            )
            reasons.append(f"✅ closed confirmation: Close={_sig_close:.2f}<Open={_sig_open:.2f}, EMA9={_ema9:.2f}")
            if _extreme_momentum and not _pb_found:
                _sl_dist = _min_sl
            else:
                _swing_high = float(_pb_window["High"].astype(float).tail(self.SWING_LOOKBACK).max())
                _sl_dist = max(_swing_high - entry + _atr * self.SL_BUFFER, _min_sl)
            sl = entry + _sl_dist
            tp = entry - _atr * self.TP_ATR_MULT

        if signal is None:
            return None

        _tp_dist = abs(tp - entry)
        _sl_dist = abs(entry - sl)
        _rr = _tp_dist / max(_sl_dist, 1e-8)
        if _rr < self.MIN_RR:
            return None

        if self._dedup_seen(ctx, signal, signal_bar_time):
            return None

        if _adx >= 30:
            score += 0.6
            reasons.append(f"✅ closed-bar strong ADX={_adx:.1f}>=30")
        if abs(_di_gap) >= 15:
            score += 0.5
            reasons.append(f"✅ closed-bar DI gap={abs(_di_gap):.1f}>=15")
        if signal == "BUY" and _macdh > 0 and _macdh > _macdh_prev:
            score += 0.3
        elif signal == "SELL" and _macdh < 0 and _macdh < _macdh_prev:
            score += 0.3

        _htf_ag = ctx.htf.get("agreement", "mixed") if ctx.htf else "mixed"
        if (signal == "BUY" and _htf_ag == "bull") or (signal == "SELL" and _htf_ag == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF aligned({_htf_ag}) +0.5")
        elif (signal == "BUY" and _htf_ag == "bear") or (signal == "SELL" and _htf_ag == "bull"):
            score -= 1.0
            reasons.append(f"⚠️ HTF against({_htf_ag}) -1.0")

        _bb_width_pct = getattr(ctx, "bb_width_pct", 0) or 0
        if _bb_width_pct > 70:
            score += 0.3

        reasons.append(f"📊 RR={_rr:.1f} SL={sl:.2f} TP={tp:.2f} | ADX={_adx:.1f} DI_gap={abs(_di_gap):.1f}")
        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
