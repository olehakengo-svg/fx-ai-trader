"""
Strategy #1: Tick Volume Spike Momentum (TVSM)
═══════════════════════════════════════════════

■ 仮説
  大口注文の板消化や成行スイープは1秒足のtick_volumeに
  強いスパイク（平時の3σ超）として現れ、その方向に
  数分間のマイクロトレンドが形成される。これは情報
  非対称性（Kyle 1985）および注文フロー持続性
  （Biais et al. 1995）で裏付けられる現象。

  ただし「スパイク検知 → 即エントリー」は本質的にHFTの
  領域で個人投資家は取れない（遅延負け）。本戦略は
  スパイク発生から数秒後、方向性が確定した時点で
  エントリーし、数分の慣性を取りに行く。

■ ロジック
  1. 過去300秒（=300バー、5分）の tick_volume 分布を作る
  2. 現在バーの tick_volume が平均+k_spike*σ を超過 (k_spike=3.0デフォルト)
  3. スパイクバーの実体方向（close - open）で方向判定
  4. スパイク発生から2バー（2秒）経過しても方向が維持されている
     （close[t-1] と close[t] が同方向）場合にエントリー
  5. SL = 1.2 * ATR(60s)
     TP = max(3.0 * ATR(60s), 8 pips)   ← 最低Z pipsガード

■ パラメータ（2つのみ）
  - spike_z: tick_volumeスパイクのZ閾値（デフォルト 3.0）
  - tp_atr_mult: TP倍率（デフォルト 3.0）

■ Look-ahead bias防止
  - μ, σ はバー[:-3] で計算（直近3バーを分布から除外）
  - スパイク判定は bars[-3]、確認は bars[-2] と bars[-1]

■ 学術根拠
  - Kyle (1985) "Continuous Auctions and Insider Trading"
  - Biais, Hillion, Spatt (1995) "An Empirical Analysis of the LOB"
"""
from __future__ import annotations
from typing import Optional
from strategies.micro_scalp.base import (
    MicroStrategyBase, MicroSignal, TickBar, CostModel,
)


class TickVolumeSpikeMomentum(MicroStrategyBase):
    name = "tvsm"

    def __init__(self, cost: CostModel, spike_z: float = 3.0, tp_atr_mult: float = 3.0):
        super().__init__(cost)
        self.spike_z = spike_z
        self.tp_atr_mult = tp_atr_mult

    def evaluate(self, bars: list[TickBar]) -> Optional[MicroSignal]:
        # 必要履歴: 分布300s + 確認3s + 余裕
        LOOKBACK = 300
        if len(bars) < LOOKBACK + 5:
            return None

        # ── μ, σ 構築: 現在バー[t]とスパイクバー[t-2]を除外 ──
        # 厳密にはスパイク判定時点[t-2]より前のみを使うべき
        hist = bars[-(LOOKBACK + 3):-3]
        volumes = [float(b.tick_volume) for b in hist]
        mu, sigma = self._mean_std(volumes)
        if sigma <= 0:
            return None

        spike_bar = bars[-3]     # スパイク候補（3秒前）
        conf_bar = bars[-2]      # 確認1（2秒前）
        latest = bars[-1]        # 現在バー（発注判定）

        # ── スパイク判定 ──
        z_spike = (float(spike_bar.tick_volume) - mu) / sigma
        if z_spike < self.spike_z:
            return None

        # ── スパイクバーの方向 ──
        body = spike_bar.close - spike_bar.open
        if abs(body) < (0.3 * self.pip):
            return None  # 方向不明確

        side = "BUY" if body > 0 else "SELL"

        # ── 確認: conf_bar と latest が同方向持続 ──
        move_1 = conf_bar.close - spike_bar.close
        move_2 = latest.close - conf_bar.close
        if side == "BUY" and (move_1 <= 0 or move_2 <= 0):
            return None
        if side == "SELL" and (move_1 >= 0 or move_2 >= 0):
            return None

        # ── ATR(60s)とTP/SL算出 ──
        atr = self._atr(bars[:-1], 60)  # 現在バー除外
        if atr <= 0:
            return None

        # Cost-aware SL buffer (2026-04-17 diagnostic 修正):
        # entry slip の2倍 + 0.5×ATR をSL下限にし、即死を防ぐ
        entry_slip_price = self.cost.total_cost_pips * self.pip
        sl_dist_atr = 1.2 * atr
        sl_dist_cost_aware = 2.0 * entry_slip_price + 0.5 * atr
        sl_dist = max(sl_dist_atr, sl_dist_cost_aware)

        # ATR が slippage に埋もれる低ボラ環境では発射しない
        if atr < 2.0 * entry_slip_price:
            return None

        tp_dist_atr = self.tp_atr_mult * atr
        # Z pipsガード
        min_tp_dist = self.min_tp_pips * self.pip
        tp_dist = max(tp_dist_atr, min_tp_dist)

        # R:R sanity: TP/SL < 1.5 はエッジ不足として拒否
        if tp_dist < sl_dist * 1.5:
            return None

        mid = latest.close
        entry = self.cost.apply_to_entry(side, mid)
        if side == "BUY":
            sl = entry - sl_dist
            tp = entry + tp_dist
        else:
            sl = entry + sl_dist
            tp = entry - tp_dist

        return MicroSignal(
            side=side,
            entry=entry,
            sl=sl,
            tp=tp,
            max_hold_sec=self.max_hold_sec,
            reason=(
                f"[TVSM] spike_z={z_spike:.2f} (thr={self.spike_z}) "
                f"body={body/self.pip:+.1f}pips ATR={atr/self.pip:.1f}pips"
            ),
            sl_pips=sl_dist / self.pip,
            tp_pips=tp_dist / self.pip,
        )
