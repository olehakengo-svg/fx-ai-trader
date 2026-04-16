"""
Micro-Scalp Base: 共通データ契約とコストモデル。

TickBar:
    1秒足（または集約tick）の最小単位。tick_volume は該当期間のtick数。
    ask/bid があればスプレッド動的算出、なければ cost_model から加算。

CostModel:
    スプレッド [pips] と 通信遅延 [ms] を受け取り、
    slippage_pips = vol_per_ms * latency_ms で約定価格を劣化させる。

MicroStrategyBase:
    全戦略の抽象基底。evaluate(bars: list[TickBar]) -> MicroSignal|None
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Literal
import math


# pip単位（JPY-cross以外）: 1pip = 0.0001
PIP_DEFAULT = 0.0001
PIP_JPY = 0.01


def pip_unit(symbol: str) -> float:
    return PIP_JPY if "JPY" in symbol.upper() else PIP_DEFAULT


@dataclass
class TickBar:
    """1秒足（tickから集約）。"""
    ts: float             # Unix時刻（秒、float可）
    open: float
    high: float
    low: float
    close: float
    tick_volume: int      # 該当秒のtick数（大口推定プロキシ）
    # Optional: 明示的なbid/askがあればスプレッドコスト精緻化
    bid: Optional[float] = None
    ask: Optional[float] = None

    @property
    def mid(self) -> float:
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2.0
        return self.close

    @property
    def spread(self) -> Optional[float]:
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None


@dataclass
class CostModel:
    """個人投資家の実運用コスト: スプレッド + 遅延slippage。"""
    spread_pips: float = 0.8         # X: 平均スプレッド [pips]
    latency_ms: float = 150.0        # Y: 通信遅延 [ms]
    # slippage推定係数: 遅延1ms当たりの平均変位 [pips/ms]。実測ベース:
    # 流動性高ペア平常時 ~0.001 pips/ms（USD/JPY東京時間）
    slippage_per_ms: float = 0.001
    symbol: str = "USD_JPY"

    @property
    def pip(self) -> float:
        return pip_unit(self.symbol)

    @property
    def total_cost_pips(self) -> float:
        """往復ではなく片道コスト [pips]。SL/TP計算時に entry 側で加算。"""
        return self.spread_pips + self.slippage_per_ms * self.latency_ms

    def apply_to_entry(self, side: Literal["BUY", "SELL"], mid_price: float) -> float:
        """シグナル中値 → 実約定価格（コスト後）に変換。

        BUY: ask側 (+spread/2) + slippage
        SELL: bid側 (-spread/2) - slippage
        """
        half_spread = (self.spread_pips / 2.0) * self.pip
        slip = (self.slippage_per_ms * self.latency_ms) * self.pip
        if side == "BUY":
            return mid_price + half_spread + slip
        return mid_price - half_spread - slip

    def apply_to_exit(self, side: Literal["BUY", "SELL"], mid_price: float) -> float:
        """決済側もスプレッドコストが発生する。"""
        half_spread = (self.spread_pips / 2.0) * self.pip
        slip = (self.slippage_per_ms * self.latency_ms) * self.pip
        # 決済方向はエントリーと反対
        if side == "BUY":
            return mid_price - half_spread - slip
        return mid_price + half_spread + slip


@dataclass
class MicroSignal:
    """マイクロスキャルプシグナル。"""
    side: Literal["BUY", "SELL"]
    entry: float            # コスト込み約定価格
    sl: float               # ストップ価格
    tp: float               # 利確価格
    max_hold_sec: int       # タイムストップ（秒）
    reason: str             # 根拠（ログ用）
    # 想定R/R比（事後検証）
    sl_pips: float = 0.0
    tp_pips: float = 0.0

    def __post_init__(self):
        # 最低TPガード: ≥ 8 pips（設計仕様）
        if self.tp_pips > 0 and self.tp_pips < 8.0:
            raise ValueError(
                f"MicroSignal violates design: TP={self.tp_pips:.1f} pips < 8.0 min"
            )


class MicroStrategyBase:
    """全Micro-Scalp戦略の抽象基底。"""
    name: str = "micro_base"
    max_hold_sec: int = 15 * 60  # 15分上限（HFT排除の要）
    min_tp_pips: float = 8.0     # Z: 最低TP [pips]

    def __init__(self, cost: CostModel):
        self.cost = cost
        self.pip = cost.pip

    def evaluate(self, bars: list[TickBar]) -> Optional[MicroSignal]:
        """bars = 直近1秒足の履歴（時系列昇順、最後が「現在バー」）。

        厳守: bars[-1] の close は既に確定しており、次バー bars[-0+1]（=発注遅延後の約定価格）
        で約定するモデル。したがって戦略は bars[:-1] の情報で判断 → bars[-1] 終値で発注 →
        次のtickで約定、というフロー。

        ここでは簡便のため bars[-1] までを判定に使用（終値確定前提）し、
        コストモデル側で遅延slippageを加算することで擬似的に next-tick fill を表現する。
        """
        raise NotImplementedError

    # ── 共通ヘルパ ──
    @staticmethod
    def _atr(bars: list[TickBar], n: int) -> float:
        """単純TR平均。nバー不足なら0を返す。"""
        if len(bars) < n + 1:
            return 0.0
        total = 0.0
        for i in range(-n, 0):
            b = bars[i]
            prev = bars[i - 1]
            tr = max(
                b.high - b.low,
                abs(b.high - prev.close),
                abs(b.low - prev.close),
            )
            total += tr
        return total / n

    @staticmethod
    def _mean_std(values: list[float]) -> tuple[float, float]:
        n = len(values)
        if n < 2:
            return 0.0, 0.0
        m = sum(values) / n
        v = sum((x - m) ** 2 for x in values) / (n - 1)
        return m, math.sqrt(v) if v > 0 else 0.0

    @staticmethod
    def _vwap(bars: list[TickBar]) -> float:
        num = 0.0
        den = 0
        for b in bars:
            num += b.mid * b.tick_volume
            den += b.tick_volume
        return num / den if den > 0 else (bars[-1].mid if bars else 0.0)
