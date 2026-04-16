"""
Strategy #2: Volatility Breakout Pullback (VBP)
═══════════════════════════════════════════════

■ 仮説
  局所的ボラティリティ・ブレイクアウト（過去30分の高値/安値
  ブレイク）は情報アービトラージの開始点。しかし個人投資家が
  ブレイクと同時にエントリーすると、HFTが既に先行しておりコスト負け。
  一方、ブレイクから最初の押し目/戻りは平均的に38.2%-50%の
  フィボ戻しで発生し、そこからの二番動き（測定エイプロン）
  を取りに行く方が現実的エッジが高い。

  Lo, Mamaysky, Wang (2000) "Foundations of Technical Analysis"
  の統計的検証で、ブレイク後のpullbackパターンは他の時間帯より
  有意に正リターンを示す。

■ ロジック
  1. 過去 lookback_sec 秒（1800s=30分）の高値H/安値L を算出
  2. 現在バーまでの間に、ある参照バー[t_break] で close > H_prev
     または close < L_prev が発生（ブレイク確認）
  3. ブレイク後、価格が直近高/安から pullback_ratio 以上
     逆行（0.5=50%戻し）で押し目形成
  4. 押し目底から反発（直近3バーで方向反転）を確認してエントリー
  5. SL = 押し目極値 - 0.5*ATR(60s)
     TP = ブレイクの初速幅（H - L_prev or L - H_prev）の倍返し
          ただし max(計算値, Z pips)

■ パラメータ（2つのみ）
  - lookback_sec: レンジ計算ウィンドウ（デフォルト 1800=30分）
  - pullback_ratio: 戻し率（デフォルト 0.5=50%）

■ Look-ahead bias防止
  - H, L は bars[-(lookback+1):-1] で算出（現在バー除外）
  - ブレイク検知 → 押し目形成 → 反発確認すべて過去バー情報のみ
  - エントリー価格は現在バー終値ベース

■ 学術根拠
  - Lo, Mamaysky, Wang (2000) "Foundations of Technical Analysis"
  - Brock, Lakonishok, LeBaron (1992) "Simple Technical Trading Rules"
"""
from __future__ import annotations
from typing import Optional
from strategies.micro_scalp.base import (
    MicroStrategyBase, MicroSignal, TickBar, CostModel,
)


class VolatilityBreakoutPullback(MicroStrategyBase):
    name = "vbp"

    def __init__(
        self,
        cost: CostModel,
        lookback_sec: int = 1800,
        pullback_ratio: float = 0.5,
    ):
        super().__init__(cost)
        self.lookback_sec = lookback_sec
        self.pullback_ratio = pullback_ratio

    def evaluate(self, bars: list[TickBar]) -> Optional[MicroSignal]:
        L = self.lookback_sec
        if len(bars) < L + 10:
            return None

        # ── 現在バー除外のレンジ ──
        hist = bars[-(L + 1):-1]
        H_prev = max(b.high for b in hist)
        L_prev = min(b.low for b in hist)
        range_prev = H_prev - L_prev
        if range_prev <= 0:
            return None

        # ── ブレイク発生バーを探索 (直近20秒以内) ──
        # 長時間前のブレイクは既にエッジ消失済みと判断
        t_break = None
        break_side = None
        break_price = None
        for i in range(-20, -3):
            b = bars[i]
            if b.close > H_prev:
                t_break = i
                break_side = "UP"
                break_price = b.close
                break
            if b.close < L_prev:
                t_break = i
                break_side = "DOWN"
                break_price = b.close
                break

        if t_break is None:
            return None

        # ── ブレイク後の極値とpullback判定 ──
        post_break = bars[t_break:]
        if break_side == "UP":
            extreme = max(b.high for b in post_break)
            pullback_target = extreme - self.pullback_ratio * (extreme - H_prev)
            current = bars[-1].close
            pb_low = min(b.low for b in bars[t_break:])
            # pullback完了条件: 最安値 <= target AND 現在が反発中
            if pb_low > pullback_target:
                return None
            # 反発確認: 直近3バーが陽線傾向
            last3 = bars[-3:]
            upmoves = sum(1 for b in last3 if b.close > b.open)
            if upmoves < 2:
                return None
            if bars[-1].close <= pb_low:
                return None  # まだ反発していない
            side = "BUY"
            sl_extreme = pb_low
        else:
            extreme = min(b.low for b in post_break)
            pullback_target = extreme + self.pullback_ratio * (L_prev - extreme)
            pb_high = max(b.high for b in bars[t_break:])
            if pb_high < pullback_target:
                return None
            last3 = bars[-3:]
            downmoves = sum(1 for b in last3 if b.close < b.open)
            if downmoves < 2:
                return None
            if bars[-1].close >= pb_high:
                return None
            side = "SELL"
            sl_extreme = pb_high

        # ── SL/TP ──
        atr = self._atr(bars[:-1], 60)
        if atr <= 0:
            return None

        mid = bars[-1].close
        entry = self.cost.apply_to_entry(side, mid)

        if side == "BUY":
            sl = sl_extreme - 0.5 * atr
            sl_dist = entry - sl
            # TP: ブレイク初速幅相当（H_prev → break_price までの幅 × 2）
            burst = break_price - H_prev
            tp_dist = max(burst * 2.0, self.min_tp_pips * self.pip)
            tp = entry + tp_dist
        else:
            sl = sl_extreme + 0.5 * atr
            sl_dist = sl - entry
            burst = L_prev - break_price
            tp_dist = max(burst * 2.0, self.min_tp_pips * self.pip)
            tp = entry - tp_dist

        # R/R サニティチェック: SL距離が0以下やTP<SLはrefuse
        if sl_dist <= 0 or tp_dist <= 0:
            return None
        if tp_dist < sl_dist * 0.8:
            return None  # R:R < 0.8 の悪質trade拒否

        return MicroSignal(
            side=side,
            entry=entry,
            sl=sl,
            tp=tp,
            max_hold_sec=self.max_hold_sec,
            reason=(
                f"[VBP] break_side={break_side} range={range_prev/self.pip:.1f}pips "
                f"pullback={self.pullback_ratio:.0%} burst={burst/self.pip:+.1f}pips"
            ),
            sl_pips=sl_dist / self.pip,
            tp_pips=tp_dist / self.pip,
        )
