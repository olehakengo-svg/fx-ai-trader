"""BB-RSI + ADX/Gold Hours フィルタ (v1d-rev) — LIVE 実証ボーナスの増幅

Revision history:
  v1d (2026-04-30): bb_rsi_reversion + H1 EMA200 整合 → BT 90d N=1131
                    Kelly=0 EV=-0.73 で大失敗。**EMA200 整合が MR エッジを破壊**
                    という重要発見 (feedback_ma_filter_breaks_mr.md に記録)
  v1d-rev (2026-04-30 再設計):
    - **H1 EMA200 整合フィルタを完全撤去**
    - 代替: bb_rsi v7.0 LIVE で実証された 2 ボーナス条件を **必須化**:
      1. ADX >= 30 (USD_JPY 「トレンド中BB反発 WR=60%」条件)
      2. Tokyo/London Gold Hours のみ (UTC 5-8, 19-23, LIVE 高 WR 時間帯)
    - これにより N は減るが、cell-level Kelly が大幅向上を狙う

設計意図:
  v1d 失敗の教訓は「LIVE で勝っているエッジに健全に見えるフィルタを足す
  と、絞った先のエッジが消える」。LIVE で実証されたボーナス条件 (ADX≥30
  と Gold Hours) は本来 +pip 寄与する条件群なので、これを必須化することで
  **MR 機構を破壊せずにエッジを集中** させる。

カスケード:
  L1 ペアゲート       : USD_JPY のみ
  L2 ADX >= 30        : 必須 (LIVE bb_rsi USD_JPY ボーナス → 必須化)
  L3 Gold Hours       : UTC ∈ {5,6,7,8,19,20,21,22,23} のみ
  L4 bb_rsi 親ロジック : BB%B + RSI + Stoch + 確認足
  L5 entry_type 書換  : "bb_rsi_ema_aligned" にして集計分離
"""
from __future__ import annotations
from typing import Optional

from strategies.context import SignalContext
from strategies.base import Candidate
from strategies.scalp.bb_rsi import BBRsiReversion


_ALLOWED_PAIRS = {"USD_JPY"}
_ADX_MIN = 30.0
_GOLD_HOURS = frozenset({5, 6, 7, 8, 19, 20, 21, 22, 23})


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


class BbRsiEmaAligned(BBRsiReversion):
    name = "bb_rsi_ema_aligned"   # 名前は維持 (集計連続性のため)
    mode = "scalp"
    enabled = True
    strategy_type = "MR"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # L1: USD_JPY 限定
        if _normalize_pair(ctx.symbol) not in _ALLOWED_PAIRS:
            return None

        # L2: ADX>=30 必須 (LIVE bb_rsi USD_JPY 高 WR 条件を強制化)
        if ctx.adx < _ADX_MIN:
            return None

        # L3: Tokyo/London Gold Hours のみ
        if ctx.hour_utc not in _GOLD_HOURS:
            return None

        # L4: 親クラス bb_rsi の MR ロジック
        cand = super().evaluate(ctx)
        if cand is None:
            return None

        # L5: entry_type を本戦略名に書き換え (集計分離のため)
        cand.entry_type = self.name
        cand.reasons = [
            f"✅ ADX={ctx.adx:.1f}>={_ADX_MIN} (LIVE 高WR必須化)",
            f"✅ Gold Hour UTC={ctx.hour_utc} ∈ {{5-8,19-23}}",
        ] + cand.reasons
        return cand
