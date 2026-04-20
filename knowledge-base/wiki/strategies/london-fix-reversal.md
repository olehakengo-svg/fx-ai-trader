# London Fix Reversal — ロンドンFixリバーサル

## Stage: Phase0 Shadow Gate (v9.1) — PAIR_DEMOTED x USD_JPY

**現行**: PAIR_PROMOTED 指定なし → 全ペア Phase0 Shadow Gate (自動 Shadow)。USD_JPY のみ PAIR_DEMOTED (明示 Shadow)。

**履歴**: Previously PROMOTED (v8.6, GBP_USD PAIR_PROMOTED / USD_JPY DEMOTED)。v9.1 で 365d BT GBP EV=-0.239 WR=47.4% (旧 60d BT WR=75% が崩壊) → GBP PAIR_PROMOTED 削除、LOT_BOOST も 1.3→1.0。現状 ELITE/PP 未所属で自動 Shadow。

## Hypothesis
ロンドン4pm Fix前にUSDが上昇ドリフトし、Fix直後に反転する（Krohn et al 2024）。W字型の24時間リターンパターン。Fix後のリバーサルは5-15pip規模。

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| [[krohn-2024]] | USD Fix前上昇→Fix後下落のW字型パターン。21年9通貨で有意 | ★★★★★ |
| [[melvin-prins-2015]] | 月末の株式ヘッジングがFix前通貨下落を予測 | ★★★★ |

## Quantitative Definition
```python
# Entry: Fix前30分 (15:30 GMT) にFix前トレンド方向と逆にエントリー
#   Fix前30分がUSD上昇 → Fix直後にUSD SELL
# Exit: Fix後30-60分 (16:30-17:00 GMT)
# SL: 15pip
# TP: 8-12pip
# Filter: 月末最終3日は効果増大（Melvin & Prins）
# 対象: EUR/USD, GBP/USD, USD/JPY
```

## Friction Viability
| Pair | Friction(RT) | Est. SL | Friction/SL | BEV_WR |
|------|-------------|---------|-------------|--------|
| EUR/USD | 2.00pip | 15pip | 13.3% | ~56% |

## Correlation with Existing
| Strategy | Expected r | Basis |
|----------|-----------|-------|
| liquidity_sweep | 中 | Fix時のストップハントと概念的に類似 |
| orb_trap | 低 | 異なるセッション境界 |

## Implementation: 2/5 — 時刻+直前トレンド方向検出

## Related
- [[session-effects]]
- [[microstructure-stop-hunting]]
