"""
Micro-Scalp Strategy Suite (Pseudo-Scalping, 1-sec resolution)
═══════════════════════════════════════════════════════════════

個人投資家の現実制約（スプレッド+通信遅延）下で収益可能な
疑似スキャルピング戦略群。数秒のHFTは除外し、数分〜15分の
マイクロトレンドを捉えることで取引コストを相対的に希釈する。

設計原則:
    1. ホールド期間: 3〜15分（HFT厳禁）
    2. 最低TP: 8 pips（スプレッド0.8 pips + slippage 0.2 pips の10倍）
    3. パラメータ: 各戦略最大2つ（過学習防止）
    4. Look-ahead bias: 厳格禁止（全指標は現在バー除外の履歴のみ）
    5. エントリーは tick/1秒解像度、判定ロジックは統計的有意性ベース

収録戦略:
    - TVSM: Tick Volume Spike Momentum (大口注文検知+順張り)
    - VBP: Volatility Breakout Pullback (ブレイクアウト後の押し目エントリー)
    - OFIMR: Order Flow Imbalance Mean Reversion (過剰オーダーフロー逆張り)
"""
from strategies.micro_scalp.base import (
    TickBar, MicroSignal, CostModel, MicroStrategyBase,
)
from strategies.micro_scalp.tvsm import TickVolumeSpikeMomentum
from strategies.micro_scalp.vbp import VolatilityBreakoutPullback
from strategies.micro_scalp.ofi_mr import OrderFlowImbalanceMR

__all__ = [
    "TickBar", "MicroSignal", "CostModel", "MicroStrategyBase",
    "TickVolumeSpikeMomentum",
    "VolatilityBreakoutPullback",
    "OrderFlowImbalanceMR",
]
