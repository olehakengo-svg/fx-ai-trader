# VIX Carry Unwind — VIX急騰キャリー巻き戻し

## Stage: SENTINEL (v8.5, 低頻度 年2-5回)

## Hypothesis
VIX急騰（90pctile超）時にキャリートレード巻き戻しが加速し、JPY急騰が発生。初動1週間が最も急速（Brunnermeier 2009, IMF 2019）。

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| [[brunnermeier-2009]] | キャリー通貨リターンは負のスキュー。巻き戻しは自己強化的スパイラル | ★★★★★ |
| [[menkhoff-2012]] | グローバルFXボラリスクが通貨リターンの90%を説明 | ★★★★★ |
| IMF WP/19/136 | VIX 90pctile超で巻き戻し速度3倍。初動1週間が最急速 | ★★★★ |

## Quantitative Definition
```python
# Trigger: VIX daily close > VIX 90-day 90th percentile
# AND VIX daily change > +20%
# Entry: USD/JPY SELL (JPY long) at next day open
# Exit: 5 trading days後 or TP到達
# SL: ATR(1D) × 2.0 (~200pip)
# TP: ATR(1D) × 3.0 (~300pip)
# 対象: USD/JPY, AUD/JPY
```

## Key Characteristic
**低頻度・高インパクト**: 年2-5回のイベント。1回で100-500pipの動き。

## Friction Viability
日次→週次保有のため摩擦は無視可能。

## Integration
vol_momentumの「VIXブーストモード」として統合が最適。独立戦略の価値は頻度から見て低い。

## Live Performance (post-cutoff, 2026-04-08〜)
| Strategy | Pairs | N | WR | PnL |
|---|---|---|---|---|
| vix_carry_unwind | all | 2 | 0.0% | -30.9 pip |

N=2 is below judgment threshold (min N=10). Low-frequency strategy — observe over full VIX cycle.
Data source: /api/demo/stats?date_from=2026-04-08 (2026-04-20)

## Related
- [[research/index]]
- [[vol-momentum-scalp]]
