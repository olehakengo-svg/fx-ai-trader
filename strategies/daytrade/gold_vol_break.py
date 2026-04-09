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
  BUY:  Custom BB %B≥1.0(2.5σ) + ATR surge (ATR7>ATR14×1.3)
        + ADX>=20 + +DI>-DI + 陽線ボディ≥ATR7×0.4
  SELL: Custom BB %B≤0.0(2.5σ) + ATR surge
        + ADX>=20 + -DI>+DI + 陰線ボディ≥ATR7×0.4

決済:
  TP: ATR7 × 3.0 (RR=1:3以上を確保)
  SL: ATR7 × 1.0
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class GoldVolBreak(StrategyBase):
    name = "gold_vol_break"
    mode = "daytrade"
    enabled = True

    # ── パラメータ ──
    bb_sigma = 2.5           # BB σ倍率
    atr_surge_ratio = 1.15   # v7.2: 1.3→1.15 (Gold vol clusteringで持続的高vol → 低サージで十分)
    adx_min = 20
    body_min_atr = 0.4       # 最小ボディ長(ATR7倍率)
    tp_mult = 3.0            # TP = ATR7 × 3.0 (高RR)
    sl_mult = 1.0            # SL = ATR7 × 1.0

    _enabled_symbols = frozenset({"XAUUSD"})

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
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
        # 標準BB(2σ)の%B=1.0はBB upper = MA+2σ
        # 2.5σ相当を%Bで計算:
        # %B_2.5 = (Close - (MA-2.5σ)) / (5σ)
        # 既存の bb_mid + bb_width から σ を逆算
        # bb_width = upper - lower = 4σ → σ = bb_width / 4
        _sigma = ctx.bb_width / 4.0 if ctx.bb_width > 0 else 0
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
