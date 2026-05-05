"""
Gold Vol Break — XAU/USD BB(2.5σ)ボラティリティ・ブレイクアウト

概要:
  15分足でBB(2.5σ)をATR急増を伴って突破した瞬間に追随。
  ゴールドの爆発的ボラを高RR(1:3+)で捕捉するデイトレード戦略。

学術的根拠:
  - BB extreme breakout: Bollinger (2001) — σ2.5超はイベントドリブン
  - Volatility clustering: Mandelbrot (1963) — ボラは自己相関する
  - Gold momentum: Baur & Lucey (2010) — 金価格のモメンタム持続性

エントリー:
  BUY:  Custom BB %B≥1.0(2.5σ) + ATR surge (ATR7>ATR14×1.05)
        + ADX>=20 + +DI>-DI + 陽線ボディ≥ATR7×0.4
  SELL: Custom BB %B≤0.0(2.5σ) + ATR surge
        + ADX>=20 + -DI>+DI + 陰線ボディ≥ATR7×0.4

v7.3変更:
  - ATRサージ: 1.15→1.05 (BBブレイク自体が選択性担う。5%増で十分)
  - sigma計算バグ修正: ctx.bb_width(正規化値≈0.008) → (bb_upper-bb_lower)/4.0 で
    実際の価格σ($10-15)を正しく算出。旧: sigma=0.002→BB幅±$0.005=無効

決済:
  TP: ATR7 × 3.0 (RR=1:3以上を確保)
  SL: ATR7 × 1.0
"""
import os
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class GoldVolBreak(StrategyBase):
    name = "gold_vol_break"
    mode = "daytrade"
    enabled = True

    # ── パラメータ ──
    bb_sigma = 2.5           # BB σ倍率
    atr_surge_ratio = 1.05   # v7.3: 1.3→1.15→1.05 (BB(2.5σ)breakoutが主フィルター → surge=5%でOK)
    adx_min = 20
    body_min_atr = 0.4       # 最小ボディ長(ATR7倍率)
    tp_mult = 3.0            # TP = ATR7 × 3.0 (高RR)
    sl_mult = 1.0            # SL = ATR7 × 1.0

    _enabled_symbols = frozenset({"XAUUSD"})
    _dedup_state: dict = {}

    @classmethod
    def reset_dedup_state(cls):
        cls._dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("GOLD_VOL_BREAK_REDESIGN_V2") == "1"

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

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if self._redesign_v2_enabled():
            return self._evaluate_redesign_v2(ctx)

        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        if ctx.df is None or len(ctx.df) < 30:
            return None

        if ctx.atr <= 0 or ctx.atr7 <= 0:
            return None

        if ctx.adx < self.adx_min:
            return None

        # ── ATRサージ判定 ──
        _atr_surge = ctx.atr7 > ctx.atr * self.atr_surge_ratio
        if not _atr_surge:
            return None

        # ── Custom BB(2.5σ) ブレイク判定 ──
        # 標準BB(2σ): bb_upper = MA + 2σ, bb_lower = MA - 2σ
        # band_abs = bb_upper - bb_lower = 4σ → σ = band_abs / 4
        # v7.3 バグ修正: ctx.bb_width は正規化値 (band/mid ≈ 0.008) であり
        # sigma算出には使えない。bb_upper - bb_lower の絶対値で σ を算出する
        _band_abs = ctx.bb_upper - ctx.bb_lower
        _sigma = _band_abs / 4.0 if _band_abs > 0 else 0
        if _sigma <= 0:
            return None

        _bb_upper_25 = ctx.bb_mid + self.bb_sigma * _sigma
        _bb_lower_25 = ctx.bb_mid - self.bb_sigma * _sigma

        # ── ボディサイズ確認 ──
        _body = abs(ctx.entry - ctx.open_price)
        if _body < ctx.atr7 * self.body_min_atr:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        _min_sl = 0.030  # XAU/USD (JPYスケール)

        # ── BUY: 上方ブレイク ──
        if (ctx.entry > _bb_upper_25
                and ctx.adx_pos > ctx.adx_neg
                and ctx.entry > ctx.open_price):
            signal = "BUY"
            score = 4.0
            _dist = round((ctx.entry - _bb_upper_25) / _sigma, 2)
            reasons.append(f"✅ BB({self.bb_sigma}σ)上方突破(距離={_dist}σ) — 爆発ブレイク")
            reasons.append(f"✅ ATRサージ(ATR7={ctx.atr7:.2f}>ATR14×{self.atr_surge_ratio}={ctx.atr * self.atr_surge_ratio:.2f})")
            reasons.append(f"✅ ADX={ctx.adx:.1f} +DI={ctx.adx_pos:.1f}>-DI={ctx.adx_neg:.1f} + 陽線body={_body:.2f}")

            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl_dist = max(ctx.atr7 * self.sl_mult, _min_sl)
            sl = ctx.entry - sl_dist

        # ── SELL: 下方ブレイク ──
        elif (ctx.entry < _bb_lower_25
              and ctx.adx_neg > ctx.adx_pos
              and ctx.entry < ctx.open_price):
            signal = "SELL"
            score = 4.0
            _dist = round((_bb_lower_25 - ctx.entry) / _sigma, 2)
            reasons.append(f"✅ BB({self.bb_sigma}σ)下方突破(距離={_dist}σ) — 爆発ブレイク")
            reasons.append(f"✅ ATRサージ(ATR7={ctx.atr7:.2f}>ATR14×{self.atr_surge_ratio}={ctx.atr * self.atr_surge_ratio:.2f})")
            reasons.append(f"✅ ADX={ctx.adx:.1f} -DI={ctx.adx_neg:.1f}>+DI={ctx.adx_pos:.1f} + 陰線body={_body:.2f}")

            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl_dist = max(ctx.atr7 * self.sl_mult, _min_sl)
            sl = ctx.entry + sl_dist

        if signal is None:
            return None

        # ── RR検証 (1:3以上) ──
        _tp_dist = abs(tp - ctx.entry)
        _sl_dist = abs(ctx.entry - sl)
        _rr = _tp_dist / max(_sl_dist, 1e-8)
        if _rr < 2.0:  # v7.2: 2.5→2.0 (SL floorでRR圧縮時の不必要なブロック回避)
            return None

        # ── スコアボーナス ──
        if ctx.adx >= 35:
            score += 0.8
            reasons.append(f"✅ ADX超強({ctx.adx:.1f}≥35) +0.8")
        elif ctx.adx >= 28:
            score += 0.4

        # DI乖離
        _di_gap = abs(ctx.adx_pos - ctx.adx_neg)
        if _di_gap >= 15:
            score += 0.5
            reasons.append(f"✅ DI乖離大({_di_gap:.1f}≥15)")

        # MACD方向一致
        if signal == "BUY" and ctx.macdh > 0 and ctx.macdh > ctx.macdh_prev:
            score += 0.3
        elif signal == "SELL" and ctx.macdh < 0 and ctx.macdh < ctx.macdh_prev:
            score += 0.3

        # HTF方向一致
        _htf_ag = ctx.htf.get("agreement", "mixed") if ctx.htf else "mixed"
        if (signal == "BUY" and _htf_ag == "bull") or (signal == "SELL" and _htf_ag == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_htf_ag})")
        elif (signal == "BUY" and _htf_ag == "bear") or (signal == "SELL" and _htf_ag == "bull"):
            score -= 1.5
            reasons.append(f"⚠️ HTF逆行({_htf_ag}) — 大幅減点")

        reasons.append(f"📊 RR={_rr:.1f}:1 (TP={self.tp_mult}ATR, SL={self.sl_mult}ATR)")
        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )

    def _evaluate_redesign_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        """V2 shadow variant: closed signal bar, next/current bar execution, dedup."""
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "").replace("/", "")
        if _sym not in self._enabled_symbols:
            return None

        if ctx.df is None or len(ctx.df) < 30:
            return None

        _df = ctx.df
        signal_bar = _df.iloc[-2]
        prev_signal_bar = _df.iloc[-3]
        signal_bar_time = self._signal_bar_time(ctx)

        _atr14 = float(signal_bar.get("atr", ctx.atr))
        _atr7 = float(signal_bar.get("atr7", ctx.atr7))
        if _atr14 <= 0 or _atr7 <= 0:
            return None

        _adx = float(signal_bar.get("adx", ctx.adx))
        if _adx < self.adx_min:
            return None

        _atr_surge = _atr7 > _atr14 * self.atr_surge_ratio
        if not _atr_surge:
            return None

        _bb_upper = float(signal_bar.get("bb_upper", ctx.bb_upper))
        _bb_lower = float(signal_bar.get("bb_lower", ctx.bb_lower))
        _bb_mid = float(signal_bar.get("bb_mid", ctx.bb_mid))
        _band_abs = _bb_upper - _bb_lower
        _sigma = _band_abs / 4.0 if _band_abs > 0 else 0
        if _sigma <= 0:
            return None

        _bb_upper_25 = _bb_mid + self.bb_sigma * _sigma
        _bb_lower_25 = _bb_mid - self.bb_sigma * _sigma

        _sig_open = float(signal_bar["Open"])
        _sig_close = float(signal_bar["Close"])
        _body = abs(_sig_close - _sig_open)
        if _body < _atr7 * self.body_min_atr:
            return None

        _adx_pos = float(signal_bar.get("adx_pos", ctx.adx_pos))
        _adx_neg = float(signal_bar.get("adx_neg", ctx.adx_neg))
        entry = ctx.entry

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        _min_sl = 0.030

        if (_sig_close > _bb_upper_25
                and _sig_close > _sig_open
                and _adx_pos > _adx_neg):
            signal = "BUY"
            score = 4.0
            _dist = round((_sig_close - _bb_upper_25) / _sigma, 2)
            reasons.append(
                f"✅ GOLD_VOL_BREAK_REDESIGN_V2 closed-bar BUY signal={signal_bar_time} "
                f"BB({self.bb_sigma}σ) breakout distance={_dist}σ"
            )
            reasons.append(
                f"✅ closed ATR surge ATR7={_atr7:.2f}>ATR14×{self.atr_surge_ratio}={_atr14 * self.atr_surge_ratio:.2f}"
            )
            reasons.append(f"✅ closed ADX={_adx:.1f} +DI={_adx_pos:.1f}>-DI={_adx_neg:.1f} body={_body:.2f}")
            tp = entry + _atr7 * self.tp_mult
            sl = entry - max(_atr7 * self.sl_mult, _min_sl)

        elif (_sig_close < _bb_lower_25
              and _sig_close < _sig_open
              and _adx_neg > _adx_pos):
            signal = "SELL"
            score = 4.0
            _dist = round((_bb_lower_25 - _sig_close) / _sigma, 2)
            reasons.append(
                f"✅ GOLD_VOL_BREAK_REDESIGN_V2 closed-bar SELL signal={signal_bar_time} "
                f"BB({self.bb_sigma}σ) breakout distance={_dist}σ"
            )
            reasons.append(
                f"✅ closed ATR surge ATR7={_atr7:.2f}>ATR14×{self.atr_surge_ratio}={_atr14 * self.atr_surge_ratio:.2f}"
            )
            reasons.append(f"✅ closed ADX={_adx:.1f} -DI={_adx_neg:.1f}>+DI={_adx_pos:.1f} body={_body:.2f}")
            tp = entry - _atr7 * self.tp_mult
            sl = entry + max(_atr7 * self.sl_mult, _min_sl)

        if signal is None:
            return None

        _tp_dist = abs(tp - entry)
        _sl_dist = abs(entry - sl)
        _rr = _tp_dist / max(_sl_dist, 1e-8)
        if _rr < 2.0:
            return None

        if self._dedup_seen(ctx, signal, signal_bar_time):
            return None

        if _adx >= 35:
            score += 0.8
            reasons.append(f"✅ closed-bar ADX super strong {_adx:.1f}>=35")
        elif _adx >= 28:
            score += 0.4

        _di_gap = abs(_adx_pos - _adx_neg)
        if _di_gap >= 15:
            score += 0.5
            reasons.append(f"✅ closed-bar DI gap {_di_gap:.1f}>=15")

        _macdh = float(signal_bar.get("macd_hist", ctx.macdh))
        _macdh_prev = float(prev_signal_bar.get("macd_hist", ctx.macdh_prev))
        if signal == "BUY" and _macdh > 0 and _macdh > _macdh_prev:
            score += 0.3
        elif signal == "SELL" and _macdh < 0 and _macdh < _macdh_prev:
            score += 0.3

        _htf_ag = ctx.htf.get("agreement", "mixed") if ctx.htf else "mixed"
        if (signal == "BUY" and _htf_ag == "bull") or (signal == "SELL" and _htf_ag == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF aligned({_htf_ag})")
        elif (signal == "BUY" and _htf_ag == "bear") or (signal == "SELL" and _htf_ag == "bull"):
            score -= 1.5
            reasons.append(f"⚠️ HTF against({_htf_ag})")

        reasons.append(f"📊 RR={_rr:.1f}:1 (TP={self.tp_mult}ATR, SL={self.sl_mult}ATR)")
        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
