# Lesson: VWAP alignment ラベルが逆校正だった

**Date**: 2026-04-23
**Source**: 3軸並行監査 (/tmp/triple_audit.py) の副産物として発見

## 症状

MassiveSignalEnhancer の VWAP ゾーン分析で付与される「BUY確度UP / SELL確度UP / 方向不一致」ラベルが、
実測 WR と逆相関していた。

| ラベル | N | WR | EV_cost |
|---|---|---|---|
| aligned (BUY確度UP / SELL確度UP) | 570 | **20.0%** | -5.16p |
| conflict (方向不一致) | 1008 | **26.7%** | -2.24p |

6.7pp の逆転。現行コードが「aligned」に confidence を加点する方向は明確に誤り。

## 根本原因

`modules/massive_signals.py:_vwap_zone_analysis` のゾーン評価ロジックは
**trend-following 前提**:

- 価格 > VWAP → BUY に +2 加点 ("BUY確度UP")
- 価格 < VWAP → SELL に +2 加点 ("SELL確度UP")

しかし shadow データの多くは mean-reversion 戦略 (bb_rsi_reversion,
sr_channel_reversal, engulfing_bb, fib_reversal, stoch_trend_pullback) で、
MR 戦略にとって「VWAP上位 = BUY」は support/resistance として逆作用:
- 価格 > VWAP で BUY = resistance に飛び込む → WR 低下
- 価格 < VWAP で BUY = support からの反発狙い → WR 高い

## 同時発見: Confidence score は WR 無相関

| conf bucket | N | WR |
|---|---|---|
| 30-39 | 91 | 34.1% |
| 50-54 | 266 | 33.1% |
| 60-64 | 312 | 25.0% |
| **70-79** | **514** | **21.8%** |
| 80-99 | 61 | 26.2% |

Low-conf avg 28.7%, High-conf avg 25.8% → confidence gate は有効に機能していない。
むしろ 70-79 bucket で WR 最低。overconfidence bias の兆候。

## 修正 (2026-04-23)

`massive_signals.py:_vwap_zone_analysis`:
- VWAP zone の `conf_adj` を全て 0 に中立化 (TF 前提の加点を停止)
- slope の `conf_adj` も中立化
- ラベル文言から「BUY確度UP / SELL確度UP / 方向一致/不一致」を除去
  (観察事実「VWAP上位 (+1.2sigma)」のみ残す)
- `zone` 情報は保持 (reasons tag として分析・ログ用)

Confidence gate 自体は temporary に保留 (既存 gate ロジックに影響範囲が広い)。
Phase 2 で isotonic regression 再校正 or gate 撤去を検討。

## 教訓

1. **Signal enhancer の conf_adj は戦略カテゴリ依存**。TF 用加点を MR 戦略に適用すると逆効果
2. **ラベル文言と実測を定期検証**。「BUY確度UP」のような断定的ラベルはデータで検証するまで誤認を再生産する
3. **Confidence score 自体の calibration を信用しない**。bucket-level WR 分析で monotonic でないなら gate 閾値は根拠なし
4. 新 signal enhancement を追加する前に必ず WR 相関を実測 (Bootstrap CI 付き)

## 今後の作業 (Phase 2)

- VWAP conf_adj を **戦略カテゴリ別** に復活 (TF は +2 加点、MR は -2 加点か中立)
- Confidence gate の isotonic regression 再校正 or Platt scaling
- 過去トレードで aligned/conflict 反転した場合の retrospective Bootstrap lift 測定

## References

- 検証スクリプト: `/tmp/triple_audit.py`
- 対象コード: `modules/massive_signals.py:_vwap_zone_analysis`
- 関連分析: [[shadow-subcell-analysis-2026-04-23]]
