# EUR_USD Scalp レジーム分析 (2026-04-15)

## 問題

60日BT: fib_reversal EUR EV=+0.271, bb_squeeze EUR EV=+0.473 → 正EV
180日BT: fib_reversal EUR EV=-0.147, engulfing_bb EUR EV=-0.186 → 負EV

当初の判断: 「60日固有のレジームだった」→ **間違い**

## 3期間分割分析

| Period | 日付 | ATR | BBwidth | Trend | Range% |
|---|---|---|---|---|---|
| P1 (oldest) | 2025-10-14 ~ 2025-12-11 | 0.0003 | 0.0006 | RANGE(50.5%) | 99.1% |
| P2 (middle) | 2025-12-11 ~ 2026-02-13 | 0.0003 | 0.0007 | RANGE(50.4%) | 99.3% |
| P3 (newest) | 2026-02-13 ~ 2026-04-15 | 0.0003 | 0.0009 | RANGE(48.5%) | 96.9% |

**市場レジームは全期間でRANGE。大きな差なし。**

## Raw MR Edge検証

### BB Lower Touch → BUY (生のMRシグナル)
| Period | N | WR | AvgRet |
|---|---|---|---|
| P1 | 2,981 | **56.4%** | +0.36pip |
| P2 | 3,002 | **56.2%** | +0.40pip |
| P3 | 3,010 | **56.7%** | +0.40pip |

**全期間でWR=56%+の安定した正EV。rawエッジは消えていない。**

## 根本原因

```
raw BB MR edge: WR=56% → 安定した正EV（全180日間）
fib_reversal:   WR低下 → 負EV（180日間の累積で）

矛盾の解消: エッジは存在する → strategy implementationが問題
```

### 具体的な実装問題

1. **SLが狭すぎる**: fib_reversal SL=ATR×0.75 ≈ 2.3pip。rawエッジ+0.40pipに対してSL hit時-2.3pipではRR比が合わない
2. **フィルターによる過剰除外**: raw BBタッチ N=3,000 → fib_reversal N=108。**97%の機会がフィルターで除外**
3. **フィルター通過分のEVが低い**: 除外された97%に正EVが分散している可能性

## 結論

```
❌ 「60日固有のレジーム」→ 間違い。raw edgeは全期間安定
❌ 「EUR Scalp SENTINEL撤回」→ 間違い。エッジを捨てることになる
✅ 「fib_reversal実装がエッジを破壊している」→ 正しい根本原因
✅ 「実装改善でエッジを拾う」→ 正しい対策方向
```

## 対策候補

1. fib_reversal SL幅テスト: ATR×0.75 → ATR×1.0/1.2 で180日BT
2. フィルター緩和テスト: 確認足条件を1つ減らして再BT
3. vwap_mean_reversion × EUR_USD Scalp: よりシンプルなMR実装
4. raw BB MR + 最小フィルターの新戦略: N=3,000 WR=56%を直接活用

## 教訓

**表面的なEV比較（60日 vs 180日）だけでは判断を誤る。** rawエッジの有無を確認してから、戦略実装の問題を切り分けるべき。

## Related
- [[friction-analysis]] — EUR_USD摩擦 RT=2.0pip
- [[bt-live-divergence]] — 6つのBTバイアス
- [[lesson-reactive-changes]] — 1日データで判断しない
- [[macro-data-analysis-protocol]] — マクロ条件分析フロー
