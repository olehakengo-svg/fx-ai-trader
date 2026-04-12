# Cross-Sectional Momentum + Dispersion Filter

## Stage: DISCOVERED

## Hypothesis
過去1-3ヶ月のウィナー通貨ロング/ルーザー通貨ショートで年率5-10%の超過リターン。リターン分散が高い時にモメンタムが強く効く（Menkhoff 2012, Eriksen 2019）。

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| [[menkhoff-2012b]] | 通貨モメンタム年率最大10%。TC後も有意 | ★★★★★ |
| [[eriksen-2019]] | 分散コンディショナルモメンタム: TC後5.7-5.8% (GitHub公開) | ★★★★ |
| [[iwanaga-sakemoto-2024]] | 株式先物→通貨クロス予測力あり | ★★★ |

## Quantitative Definition
```python
# Universe: USD/JPY, EUR/USD, GBP/USD, AUD/USD, NZD/USD, USD/CAD, USD/CHF
# Signal: 1M return ranking
# Position: Top 2 LONG, Bottom 2 SHORT
# Dispersion filter: XS return std > median → full position, else half
# Cross-asset: Nikkei 1M return > 0 → JPY short bias
# Rebalance: Monthly
# SL: None (portfolio-level DD control)
# TP: None (hold until rebalance)
```

## Friction Viability
月次リバランス → 2-4pip RT × 4ペア × 12回/年 ≈ 150pip/年のコスト。
年率5-10%のリターン（500-1000pip相当）に対して十分。

## Correlation with Existing
| Strategy | Expected r | Basis |
|----------|-----------|-------|
| vol_momentum_scalp | 中 | 時系列Mom vs XS Mom — 異なるファクター |
| bb_rsi | 低 | MR vs Mom、独立 |

## Implementation Complexity: 2/5
OHLCVのみ。月次リターン計算+ソート+分散フィルター。Eriksenのコード公開あり。

## Key Risk
- 2012年以降のリターン低下傾向（アノマリー認知の普及）
- 単体Sharpe 0.3-0.5 → 他シグナルとの組み合わせが前提

## Related
- [[research/index]]
- [[momentum-anomaly]]
- [[vol-momentum-scalp]]
