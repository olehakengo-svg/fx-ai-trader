"""
Break-even WR (BEV) per pair × mode.

Wilson CI下限 > BEV_WR を Tier B gate判定で使う (daily-tierB-protocol.md §4.2)。

BEV計算式:
    BEV_WR = (|sl_m| + 2*spread_pip + slippage_pip) / (|sl_m| + tp_m)
    ただし tp_m, sl_m は ATR倍率表記、spread は pip実数 → ATR換算が必要

実装では pair × mode 別の ATR typical × TP/SL倍率テーブルで事前計算。
BT再走時に更新予定 (現状は 2026-04-20 スナップショット値)。
"""
from __future__ import annotations

# BEV_WR per (instrument, mode). mode ∈ {daytrade, scalp}
# 更新日: 2026-04-22 (初版)
# 計算前提: TP倍率=2.0, SL倍率=1.2, typical ATR / typical spread 込み
#
# 根拠:
#   - typical ATR14 (15m) per pair × 2026 Q1 median
#   - spread_at_entry median per pair × mode × 30d (/api/demo/stats)
#   - slippage budget = 0.3pip (OANDA live median)
_BEV_TABLE: dict[tuple[str, str], float] = {
    ("USDJPY", "daytrade"): 0.38,
    ("USDJPY", "scalp"):    0.44,
    ("EURUSD", "daytrade"): 0.39,
    ("EURUSD", "scalp"):    0.45,
    ("GBPUSD", "daytrade"): 0.40,
    ("GBPUSD", "scalp"):    0.46,
    ("EURJPY", "daytrade"): 0.39,
    ("EURJPY", "scalp"):    0.45,
}

DEFAULT_BEV = 0.42  # 未登録ペア × mode 用の保守的default


def normalize_instrument(instrument: str) -> str:
    """'USD_JPY' / 'USDJPY=X' / 'USDJPY' → 'USDJPY'"""
    s = instrument.replace("_", "").replace("=X", "").upper()
    return s


def bev_wr(instrument: str, mode: str = "daytrade") -> float:
    """Break-even WR を返す。未登録なら DEFAULT_BEV。"""
    key = (normalize_instrument(instrument), mode.lower())
    return _BEV_TABLE.get(key, DEFAULT_BEV)


def all_pairs() -> list[str]:
    """登録済みpair一覧 (unique, instrument側)。"""
    return sorted({k[0] for k in _BEV_TABLE})
