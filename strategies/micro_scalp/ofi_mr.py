"""
Strategy #3: Order Flow Imbalance Mean Reversion (OFIMR)
══════════════════════════════════════════════════════════

■ 仮説
  Tickレベルで Σ sign(Δprice) * tick_volume は Order Flow
  Imbalance (OFI)の近似指標。極端なOFI偏り（2σ超）が発生し、
  それによって価格が micro-VWAP から大きく乖離した場合、
  一時的な流動性枯渇と在庫不均衡が原因であり、
  数分以内に micro-VWAP 方向への平均回帰が期待できる。

  これは Kyle (1985) のノイズトレーダー・リスクモデルの
  ショートホライズン版。Chordia & Subrahmanyam (2004)
  "Order imbalance and individual stock returns" は
  日足でこの現象を示したが、FXの1分〜10分スケールでも
  観測可能とされる（Evans & Lyons 2002）。

  重要: 「大きすぎる偏り → 反転」であり、「偏り発生 → 順張り」
  ではない。戦略#1(TVSM)のモメンタムは発生直後1〜3分の
  慣性を取るが、本戦略はその慣性が尽きたreversionポイントで
  fade する。よって TVSM と OFIMR は時間差で補完関係にある。

■ ロジック
  1. 過去 window_sec 秒（デフォルト 180s=3分）の
     OFI = Σ sign(close_i - close_{i-1}) * tick_volume_i
  2. OFIの分布（過去1800秒=30分）から μ_OFI, σ_OFI を算出
  3. |OFI_now| > z_thresh * σ_OFI のとき「過剰偏り」と判定
  4. 価格が micro_VWAP(window_sec) から OFI 方向に
     1.0 * ATR(60s)以上乖離している場合にエントリー
  5. エントリー方向は OFI と逆（fade）
  6. SL = 直近N秒の極値 + 0.3*ATR(60s)
     TP = micro_VWAP 位置（平均回帰目標）
          ただし max(到達距離, Z pips)

■ パラメータ（2つのみ）
  - window_sec: OFI集計+VWAP窓（デフォルト 180=3分）
  - z_thresh: OFI偏りのZ閾値（デフォルト 2.0）

■ Look-ahead bias防止
  - OFI分布は bars[-(1800+window):-window] から構築（現在窓除外）
  - VWAP、ATRは現在バー除外のrolling windowで計算
  - エントリー判定は bars[-1].close ベース（確定値）

■ 学術根拠
  - Kyle (1985) "Continuous Auctions and Insider Trading"
  - Chordia & Subrahmanyam (2004) "Order imbalance and stock returns"
  - Evans & Lyons (2002) "Order flow and exchange rate dynamics"
"""
from __future__ import annotations
from typing import Optional
from strategies.micro_scalp.base import (
    MicroStrategyBase, MicroSignal, TickBar, CostModel,
)


class OrderFlowImbalanceMR(MicroStrategyBase):
    name = "ofi_mr"
    max_hold_sec: int = 10 * 60   # 平均回帰狙いなので10分上限に短縮

    def __init__(self, cost: CostModel, window_sec: int = 180, z_thresh: float = 2.0):
        super().__init__(cost)
        self.window_sec = window_sec
        self.z_thresh = z_thresh

    @staticmethod
    def _compute_ofi(bars: list[TickBar]) -> float:
        if len(bars) < 2:
            return 0.0
        ofi = 0.0
        for i in range(1, len(bars)):
            dp = bars[i].close - bars[i - 1].close
            if dp > 0:
                ofi += bars[i].tick_volume
            elif dp < 0:
                ofi -= bars[i].tick_volume
        return ofi

    def evaluate(self, bars: list[TickBar]) -> Optional[MicroSignal]:
        W = self.window_sec
        DIST_BARS = 1800  # OFI分布構築窓

        if len(bars) < DIST_BARS + W + 10:
            return None

        # ── 現在窓のOFI ──
        current_window = bars[-W:]
        ofi_now = self._compute_ofi(current_window)

        # ── 過去OFI分布: 現在窓を除外してローリングOFI ──
        # 計算負荷低減のためストライド30秒でサンプリング
        dist_bars = bars[-(DIST_BARS + W):-W]
        ofis = []
        stride = 30
        for start in range(0, len(dist_bars) - W, stride):
            chunk = dist_bars[start:start + W]
            ofis.append(self._compute_ofi(chunk))

        if len(ofis) < 20:
            return None

        mu, sigma = self._mean_std(ofis)
        if sigma <= 0:
            return None

        z_ofi = (ofi_now - mu) / sigma
        if abs(z_ofi) < self.z_thresh:
            return None

        # ── 価格がVWAPから乖離しているか ──
        vwap = self._vwap(current_window)
        current_price = bars[-1].close
        displacement = current_price - vwap

        atr = self._atr(bars[:-1], 60)
        if atr <= 0:
            return None

        # Cost-aware ボラティリティ gate (2026-04-17):
        # ATR < 2×cost では VWAP到達距離がコストに負けるため発射しない
        entry_slip_price = self.cost.total_cost_pips * self.pip
        if atr < 2.0 * entry_slip_price:
            return None

        # 偏り方向と価格乖離方向が一致しているかチェック
        # OFI > 0 (買い圧優勢) → 価格もVWAP上方 → SELL fade
        # OFI < 0 (売り圧優勢) → 価格もVWAP下方 → BUY fade
        if z_ofi > 0 and displacement > atr * 1.0:
            side = "SELL"
        elif z_ofi < 0 and displacement < -atr * 1.0:
            side = "BUY"
        else:
            return None

        # ── SL/TP (cost-aware SL buffer 適用) ──
        recent = bars[-W:]
        cost_buffer = 2.0 * entry_slip_price + 0.3 * atr
        if side == "BUY":
            sl_extreme = min(b.low for b in recent)
            mid = bars[-1].close
            entry = self.cost.apply_to_entry(side, mid)
            # SL: 極値ベースとコストベースの大きい方
            sl = min(sl_extreme - 0.3 * atr, entry - cost_buffer)
            sl_dist = entry - sl
            tp_target_price = vwap  # mean reversion goal
            tp_dist_calc = tp_target_price - entry
            tp_dist = max(tp_dist_calc, self.min_tp_pips * self.pip)
            tp = entry + tp_dist
        else:
            sl_extreme = max(b.high for b in recent)
            mid = bars[-1].close
            entry = self.cost.apply_to_entry(side, mid)
            sl = max(sl_extreme + 0.3 * atr, entry + cost_buffer)
            sl_dist = sl - entry
            tp_target_price = vwap
            tp_dist_calc = entry - tp_target_price
            tp_dist = max(tp_dist_calc, self.min_tp_pips * self.pip)
            tp = entry - tp_dist

        if sl_dist <= 0 or tp_dist <= 0:
            return None
        # R:R ≥ 0.7 最低ライン（MR戦略は典型的にR:R低めだが最低基準設定）
        if tp_dist < sl_dist * 0.7:
            return None

        return MicroSignal(
            side=side,
            entry=entry,
            sl=sl,
            tp=tp,
            max_hold_sec=self.max_hold_sec,
            reason=(
                f"[OFIMR] z_ofi={z_ofi:+.2f} (thr=±{self.z_thresh}) "
                f"disp={displacement/self.pip:+.1f}pips "
                f"VWAP={vwap:.5f} ATR={atr/self.pip:.1f}pips"
            ),
            sl_pips=sl_dist / self.pip,
            tp_pips=tp_dist / self.pip,
        )
