"""
JPY Basket Trend — 円バスケット・パーフェクトオーダー順張り

概要:
  USD/JPY と EUR/JPY が同時に15分足でパーフェクトオーダーを形成している時、
  「円安/円高トレンド」と判断して強く順張り。単一ペアではなく
  円全体の方向性が一致する高確信エントリー。

  ※ cross-pair data制約: 現在ペアのPO + ADX≥28 + HTF agreement を
  「円バスケットトレンド」のプロキシとして使用 (JPYペア相関 r≈0.85)

学術的根拠:
  - Currency basket momentum: Lustig et al. (2011, RFS) — 通貨バスケット・キャリーモメンタム
  - Perfect order: Murphy (1999) — EMA完全順列はトレンド成熟の証拠
  - Cross-pair correlation: Evans & Lyons (2002) — 同一通貨ペアの高相関性

エントリー:
  BUY:  EMA9 > EMA21 > EMA50 (パーフェクトオーダー)
        + ADX >= 28 (強トレンド = 円バスケット一致のプロキシ)
        + HTF agreement = bull
        + +DI > -DI + 陽線 + Close > EMA9 (トレンド乗り)
  SELL: 逆条件

決済:
  TP: ATR × 2.5 (トレンド追随)
  SL: EMA50 の反対側 + ATR × 0.3 (PO崩壊 = 撤退)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class JpyBasketTrend(StrategyBase):
    name = "jpy_basket_trend"
    mode = "daytrade"
    enabled = True

    # ── パラメータ ──
    adx_min = 28           # 強トレンド要件 (通常25だがバスケットプロキシ用に厳格化)
    tp_mult = 2.5          # TP = ATR × 2.5
    sl_atr_buffer = 0.3    # SL = EMA50 ± ATR×0.3

    _enabled_symbols = frozenset({"USDJPY", "EURJPY"})

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        if ctx.df is None or len(ctx.df) < 50:
            return None

        if ctx.atr <= 0:
            return None

        # ── 強ADX要件: バスケット一致のプロキシ ──
        if ctx.adx < self.adx_min:
            return None

        # ── パーフェクトオーダー判定 ──
        _bull_po = (ctx.ema9 > ctx.ema21 > ctx.ema50)
        _bear_po = (ctx.ema9 < ctx.ema21 < ctx.ema50)

        if not _bull_po and not _bear_po:
            return None

        # ── HTF agreement 必須 ──
        _htf_ag = ctx.htf.get("agreement", "mixed") if ctx.htf else "mixed"

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        _min_sl = 0.030  # JPYペア

        # ── BUY: Bull PO + HTF bull + DI方向 + 陽線 ──
        if (_bull_po
                and _htf_ag == "bull"
                and ctx.adx_pos > ctx.adx_neg
                and ctx.entry > ctx.open_price
                and ctx.entry > ctx.ema9):
            signal = "BUY"
            score = 4.5  # 高確信エントリー
            reasons.append(f"✅ JPYバスケット円安トレンド — パーフェクトオーダー(EMA9>21>50)")
            reasons.append(f"✅ ADX={ctx.adx:.1f}≥{self.adx_min} +DI={ctx.adx_pos:.1f}>-DI={ctx.adx_neg:.1f}")
            reasons.append(f"✅ HTF方向一致({_htf_ag}) — 4H+1D確認")
            reasons.append(f"✅ EMA9上(C={ctx.entry:.3f}>EMA9={ctx.ema9:.3f}) + 陽線")

            tp = ctx.entry + ctx.atr * self.tp_mult
            sl = ctx.ema50 - ctx.atr * self.sl_atr_buffer
            sl = min(sl, ctx.entry - _min_sl)

        # ── SELL: Bear PO + HTF bear + DI方向 + 陰線 ──
        elif (_bear_po
              and _htf_ag == "bear"
              and ctx.adx_neg > ctx.adx_pos
              and ctx.entry < ctx.open_price
              and ctx.entry < ctx.ema9):
            signal = "SELL"
            score = 4.5
            reasons.append(f"✅ JPYバスケット円高トレンド — パーフェクトオーダー(EMA9<21<50)")
            reasons.append(f"✅ ADX={ctx.adx:.1f}≥{self.adx_min} -DI={ctx.adx_neg:.1f}>+DI={ctx.adx_pos:.1f}")
            reasons.append(f"✅ HTF方向一致({_htf_ag}) — 4H+1D確認")
            reasons.append(f"✅ EMA9下(C={ctx.entry:.3f}<EMA9={ctx.ema9:.3f}) + 陰線")

            tp = ctx.entry - ctx.atr * self.tp_mult
            sl = ctx.ema50 + ctx.atr * self.sl_atr_buffer
            sl = max(sl, ctx.entry + _min_sl)

        if signal is None:
            return None

        # ── RR検証 ──
        _tp_dist = abs(tp - ctx.entry)
        _sl_dist = abs(ctx.entry - sl)
        if _tp_dist < _sl_dist * 1.2:
            return None

        # ── スコアボーナス ──
        # ADX超強
        if ctx.adx >= 40:
            score += 0.8
            reasons.append(f"✅ ADX超強({ctx.adx:.1f}≥40) +0.8")
        elif ctx.adx >= 35:
            score += 0.4

        # DI乖離
        _di_gap = abs(ctx.adx_pos - ctx.adx_neg)
        if _di_gap >= 15:
            score += 0.5
            reasons.append(f"✅ DI乖離大({_di_gap:.1f})")
        elif _di_gap >= 10:
            score += 0.3

        # MACD方向一致
        if signal == "BUY" and ctx.macdh > 0 and ctx.macdh > ctx.macdh_prev:
            score += 0.3
            reasons.append("✅ MACD-H上昇中")
        elif signal == "SELL" and ctx.macdh < 0 and ctx.macdh < ctx.macdh_prev:
            score += 0.3
            reasons.append("✅ MACD-H下降中")

        # EMA200方向一致
        if signal == "BUY" and ctx.ema200_bull:
            score += 0.3
            reasons.append("✅ EMA200上(長期トレンド一致)")
        elif signal == "SELL" and not ctx.ema200_bull:
            score += 0.3
            reasons.append("✅ EMA200下(長期トレンド一致)")

        # 時間帯ボーナス (London/NY: 8-17 UTC)
        if 8 <= ctx.hour_utc <= 17:
            score += 0.2
        elif ctx.hour_utc < 5 or ctx.hour_utc >= 22:
            score -= 0.5
            reasons.append(f"⚠️ 低流動性時間帯(UTC {ctx.hour_utc})")

        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
