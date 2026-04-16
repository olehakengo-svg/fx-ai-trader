"""Edge Discovery Framework.

データ駆動でエッジ (positive EV pocket) を発見するための汎用ツール群。

Core modules:
- conditional_returns: 条件別 forward-return 分析
- regime_decomposer:    マクロレジーム別 P&L 分解 (TODO)
- event_profiler:       イベント近傍 drift 分析 (TODO)
- robustness:           Out-of-sample 検証ユーティリティ
"""
from research.edge_discovery.conditional_returns import (
    ConditionalReturnAnalyzer,
    EdgePocket,
)
from research.edge_discovery.robustness import (
    split_half_robustness,
    walk_forward_validate,
)

__all__ = [
    "ConditionalReturnAnalyzer",
    "EdgePocket",
    "split_half_robustness",
    "walk_forward_validate",
]
