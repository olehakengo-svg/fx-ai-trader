# Engulfing BB × LVN (Shadow Variant)

## Overview
- **Entry Type**: `engulfing_bb_lvn`
- **Base Strategy**: `engulfing_bb`
- **Category**: Scalp MR (filter-specialized variant)
- **Timeframe**: 15m (inherits base)
- **Status**: PHASE0_SHADOW (2026-04-23 〜, N 蓄積中)
- **Filter**: MassiveSignalEnhancer により `reasons` に "LVN内" または "低出来高ノード" が付与されたシグナルのみ

## Rationale (2026-04-23 quant analysis)

`engulfing_bb` ベースライン (shadow post-cutoff):

| Scope | N | WR | EV_cost | EV_raw |
|---|---|---|---|---|
| baseline | 158 | 27.2% | -3.43p | -2.43p |
| **+ LVN filter** | **51** | **39.2%** | **+0.22p** | +1.22p |

**EV lift: +3.65p/trade**  (statistical uplift confirmed via `/tmp/vwap_analysis.py`)

### なぜLVN (Low Volume Node) で勝率が上がるか
- engulfing_bb は「包み足 + BB逆張り」= mean-reversion 前提
- LVN = 出来高が薄い価格帯 = 素通りしやすい
- 通常ゾーンでは HVN の壁に吸収されて MR が効かないケースが多い
- LVN 内で包み足が出ると price discovery のズレが戻る確率が高い (+12.0% WR)

## Signal Logic
Base `engulfing_bb` のゲート通過後、MassiveSignalEnhancer の Volume Profile 分析で
現在価格帯が LVN と判定された場合のみ `entry_type` を `engulfing_bb_lvn` に書き換え。

ルーティング実装: `modules/shadow_variants.py:derive_variant_entry_type()`

## Current Configuration
- **Tier**: PHASE0_SHADOW (新 entry_type として自動フォールバック)
- **Lot**: N/A (shadow only)
- **Promotion gate**: Shadow N≥30 かつ Bootstrap EV_lo > 0 で Kelly Half Live 検討
- **Demotion gate**: Shadow N=50 で EV_cost<0 または WR<35% → 破棄

## Related
- [[engulfing-bb]] — ベース戦略
- [[shadow-subcell-analysis-2026-04-23]] — 分析母体
- `modules/shadow_variants.py` — ルーティング実装
- `modules/massive_signals.py:218-301` — LVN 判定ロジック
