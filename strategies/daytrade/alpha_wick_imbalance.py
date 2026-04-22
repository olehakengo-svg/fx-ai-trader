"""
Alpha #2: Wick Imbalance Reversion (ヒゲ不均衡平均回帰)
══════════════════════════════════════════════════════════

■ 仮説
  直近N本のローソク足において、上ヒゲ総長と下ヒゲ総長の比率が極端に
  偏っている場合、一方向への流動性消費（ストップ狩り・アイスバーグ注文
  の吸収）が完了し、反対方向への平均回帰が起こりやすい。

  ヒゲは「拒絶された価格領域」を表す。上ヒゲが支配的 = 上値が繰り返し
  拒絶されている = 売り圧力の蓄積 → 下方向へのブレイク、またはその逆。

  ただしこの直感の逆を取る: ヒゲの偏りが極端な場合、それは
  流動性プールが枯渇した側への「反発」を意味する。
  (Osler 2003 "Currency orders and exchange rate dynamics")

■ ロジック
  1. 直近 window 本（パラメータ1）のローソク足について
     - upper_wick = High - max(Open, Close)
     - lower_wick = min(Open, Close) - Low
  2. Wick Imbalance Ratio (WIR) を計算:
     WIR = (Σ upper_wick - Σ lower_wick) / (Σ upper_wick + Σ lower_wick)
     → 範囲: [-1, +1]
     → +1 = 全て上ヒゲ（上値拒絶）, -1 = 全て下ヒゲ（下値拒絶）
  3. |WIR| > threshold（パラメータ2）で、現在のバーの body が反転方向を
     確認した場合にエントリー:
     - WIR > threshold (上値拒絶蓄積) → 確認バーが陰線ならSELL
     - WIR < -threshold (下値拒絶蓄積) → 確認バーが陽線ならBUY

■ パラメータ（2つ）
  - window: ヒゲ集計本数（デフォルト8）
  - threshold: WIR閾値（デフォルト0.45）

■ Look-ahead bias防止
  - WIRは直前window本(iloc[-window-1:-1])で計算
  - 現在バー(iloc[-1])はエントリー確認にのみ使用

■ 学術根拠
  - Osler (2003) "Currency orders and exchange rate dynamics" (stop-loss clustering)
  - Mandelbrot (1963) "The variation of certain speculative prices" (fat tails from clustered activity)
"""
from __future__ import annotations
from typing import Optional
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty


class WickImbalanceReversion(StrategyBase):
    name = "wick_imbalance_reversion"
    mode = "daytrade"
    enabled = True
    strategy_type = "MR"   # v11.1: ヒゲ偏り反発 = MR by construction (Osler 2003)
    params = {
        "window": 8,          # ヒゲ集計本数
        "threshold": 0.45,    # WIR閾値
    }

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        df = ctx.df
        if df is None:
            return None

        window = self.params.get("window", 8)
        threshold = self.params.get("threshold", 0.45)

        # window + 1本必要 (window本の集計 + 1本の確認バー)
        if len(df) < window + 2:
            return None

        if ctx.atr <= 0:
            return None

        # ── 直前 window 本のヒゲを集計（現在バー除外） ──
        lookback = df.iloc[-(window + 1):-1]  # 現在バーの1つ前まで

        total_upper = 0.0
        total_lower = 0.0
        for i in range(len(lookback)):
            row = lookback.iloc[i]
            high = row["High"]
            low = row["Low"]
            op = row["Open"]
            cl = row["Close"]

            body_top = max(op, cl)
            body_bot = min(op, cl)

            upper_wick = high - body_top
            lower_wick = body_bot - low

            # 負値ガード（データ異常）
            total_upper += max(0.0, upper_wick)
            total_lower += max(0.0, lower_wick)

        total_wick = total_upper + total_lower
        if total_wick == 0:
            return None

        # ── Wick Imbalance Ratio ──
        wir = (total_upper - total_lower) / total_wick

        if abs(wir) < threshold:
            return None

        # ── 現在バーのbodyで方向確認 ──
        current_close = df.iloc[-1]["Close"]
        current_open = df.iloc[-1]["Open"]
        current_body = current_close - current_open

        # 追加フィルタ: 現在バーのbodyがATRの5%以上（微小bodyは無視）
        if abs(current_body) < ctx.atr * 0.05:
            return None

        signal = None
        if wir > threshold and current_body < 0:
            # 上ヒゲ蓄積 + 確認陰線 → SELL
            signal = "SELL"
        elif wir < -threshold and current_body > 0:
            # 下ヒゲ蓄積 + 確認陽線 → BUY
            signal = "BUY"

        if signal is None:
            return None

        # ── HTF Hard Block (v9.1) ──
        _htf = ctx.htf or {}
        _htf_agreement = _htf.get("agreement", "mixed")
        if _htf_agreement == "bull" and signal == "SELL":
            return None
        if _htf_agreement == "bear" and signal == "BUY":
            return None

        # ── ボラティリティ・レジームフィルタ ──
        # BB width percentile が極端に低い（圧縮相場）ではWIRが歪むので除外
        if ctx.bb_width_pct < 0.15:
            return None

        # ── SL/TP: ATRベース ──
        atr = ctx.atr
        sl_mult = 1.5
        # TPはWIR偏りの強さに応じて拡大（最大2.5ATR）
        tp_mult = min(2.5, 1.2 + abs(wir) * 2.0)

        if signal == "BUY":
            sl = ctx.entry - atr * sl_mult
            tp = ctx.entry + atr * tp_mult
        else:
            sl = ctx.entry + atr * sl_mult
            tp = ctx.entry - atr * tp_mult

        # ── スコアリング ──
        base_score = 5.0
        wir_bonus = min(0.8, (abs(wir) - threshold) / 0.4)
        # 確認バーのbody強度ボーナス
        body_strength = min(0.5, abs(current_body) / (atr * 0.5))
        score = base_score + wir_bonus + body_strength

        _legacy_confidence = int(min(85, 50 + score * 3))
        confidence = apply_penalty(_legacy_confidence, self.strategy_type, ctx.adx, conf_max=85)

        reasons = [
            f"🕯️ [WickImb] WIR={wir:+.3f} (thr={threshold}) "
            f"upper={total_upper:.5f} lower={total_lower:.5f}",
            f"confirm_body={current_body/atr:.2f}ATR window={window}",
        ]

        return Candidate(
            signal=signal,
            confidence=confidence,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=self.name,
            score=score,
        )
