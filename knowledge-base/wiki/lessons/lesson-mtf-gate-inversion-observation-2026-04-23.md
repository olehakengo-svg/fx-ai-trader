# Lesson: MTF Gate は alignment ラベルで LIVE/SHADOW を逆選別している疑い

**Date**: 2026-04-23
**Status**: 観察のみ (gate 自体は未変更、A/B 実験継続中)

## 観察

[[vwap-calibration-baseline-2026-04-23]] と [[tf-inverse-rootcause-2026-04-23]] で
MTF alignment ラベル別 WR を測定したところ:

### TF 戦略群 (N=568) 内 MTF alignment 別

| Label | N | WR | EV_cost |
|---|---|---|---|
| **aligned** | 30 | **10.0%** | -3.59p |
| conflict | 282 | 20.2% | -1.98p |
| unknown | 18 | 33.3% | -1.27p |
| (blank) | 238 | 25.6% | -1.90p |

### 全 shadow post-cutoff (VWAP audit, N=1578)

| Label | N | WR | EV_cost |
|---|---|---|---|
| aligned (VWAP-based) | 570 | 20.0% | -5.16p |
| conflict (VWAP-based) | 1008 | 26.7% | -2.24p |

## 現行 MTF Gate 実装 ([modules/demo_trader.py:3430-3450](../../../modules/demo_trader.py))

```
Group A (mtf_gated):  alignment=conflict -> LIVE→SHADOW 降格
Group B (label_only): ラベル付与のみ
```

Hash-based 50/50 A/B 振り分け中。

## 問題

- `conflict` は **WR が高い方** (20.2% vs 10.0%, +10.2pp)
- それを LIVE→SHADOW に降格 = **良いトレードを shadow にしまっている**
- `aligned` (WR 10%) は gate 通過 (LIVE 残留) = **悪いトレードが実弾領域に残る**
- 結果として gate は EV を**負方向に働かせている**

## なぜ即修正しないか

1. MTF aligned N=30 は小標本 (Wilson 95% CI 下限 2.1% なので有意性はあるが、
   broader data で再現するか確認が必要)
2. Hash-based A/B 実験が Phase D で進行中、介入で計測が汚れる
3. [[lesson-reactive-changes]] — 実データなしの即応は過去に失敗している

## 観察プロトコル

1. 週次 `tools/vwap_calibration_monitor.py` 実行時に MTF alignment 列も追加計測
2. N=100 aligned まで蓄積したら再判定
3. aligned WR が依然 <20% で conflict >25% なら gate を **反転** (aligned→SHADOW) or **撤廃**

## 代替候補

| 案 | リスク | 期待効果 |
|---|---|---|
| A. 現状維持 (A/B 継続) | 0 (計測の質保持) | データ蓄積 |
| B. MTF gate 中立化 (downgrade 停止) | 低 (単に LIVE trades が増える) | +2-3p/trade (推定) |
| C. MTF gate 反転 (aligned→SHADOW) | 中 (aligned LIVE trades が減る) | +3-5p/trade (推定) |
| D. Gate 撤廃 | 中 (A/B 実験が終わる) | A/B 結論確定 |

**現時点の推奨**: A (観察継続)。ただし N=100 aligned 到達時に改めて判定。

## Phase 2a での関連修正

同日 (2026-04-23) に以下を neutralize 済:
- `_vwap_zone_analysis`: conf_adj 0, "BUY確度UP/SELL確度UP" 削除
- `_volume_profile`: HVN/LVN conf_adj 0, "S/R確度UP" 削除
- `_institutional_flow`: conf_adj 0, "BUY/SELL方向一致 (+3)" 削除

これらは *confidence score への加点* を止めるもので、MTF gate の LIVE/SHADOW 振り分け
とは別レイヤー。今回の lesson は「gate logic」に関するもので未着手。

## References

- [[vwap-calibration-baseline-2026-04-23]]
- [[tf-inverse-rootcause-2026-04-23]]
- [[roadmap-vwap-calibration-2026-04-23]]
- Gate code: `modules/demo_trader.py:3400-3450`
