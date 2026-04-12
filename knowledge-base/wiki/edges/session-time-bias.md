# Session Time Bias — セッション時刻バイアス

## Stage: DISCOVERED

## Hypothesis
通貨は自国のトレーディング時間帯に減価する傾向がある（Breedon & Ranaldo 2013）。東京時間にJPY売り、ロンドン時間にGBP売りの方向性ドリフトが存在。

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| [[breedon-ranaldo-2013]] | 自国時間帯に通貨が減価。21年間9通貨ペアで統計的に高度に有意 | ★★★★★ |

## Quantitative Definition
```python
# Entry: セッションオープン付近で自国通貨SELL
# Tokyo (UTC 0): SELL JPY → BUY USD/JPY
# London (UTC 7): SELL GBP → BUY EUR/GBP or SELL GBP/USD
# Exit: 次のセッション移行前（4-8時間保有）
# SL: ATR(1H) × 1.5
# TP: ATR(1H) × 2.0
```

## Friction Viability
| Pair | Friction(RT) | Est. SL | Friction/SL | BEV_WR | Margin |
|------|-------------|---------|-------------|--------|--------|
| USD_JPY | 2.14pip | ~25pip | 8.6% | ~33% | 研究値で十分 |

## Correlation with Existing
| Strategy | Expected r | Basis |
|----------|-----------|-------|
| orb_trap | 低〜中 | 時間帯重複あるが、ORフェイクアウト vs 方向性ドリフトで別メカニズム |
| bb_rsi | 低 | MR vs ドリフト、独立 |

## Implementation Path
- [x] Stage 1: DISCOVERED (2026-04-12)
- [ ] Stage 2: FORMULATED — 時刻別リターンのBT
- [ ] Stage 3: BACKTESTED — 55d+ period, N>=30

## Key Advantage
**実装複雑度 1/5** — 時刻ルールのみ。最もシンプルな新エッジ。

## Related
- [[session-effects]]
- [[research/index]]
