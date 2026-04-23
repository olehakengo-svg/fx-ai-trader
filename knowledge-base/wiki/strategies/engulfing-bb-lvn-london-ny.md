# Engulfing BB × LVN × London/NY Session (Shadow Variant)

## Overview
- **Entry Type**: `engulfing_bb_lvn_london_ny`
- **Base Strategy**: `engulfing_bb`
- **Category**: Scalp MR (filter-specialized variant)
- **Timeframe**: 15m (inherits base)
- **Status**: PHASE0_SHADOW (2026-04-23 〜, N 蓄積中)
- **Filter**: MassiveSignalEnhancer が "LVN内" または "低出来高ノード" を付与
  **かつ** UTC 7-12 (London) または UTC 16-21 (NY)

## Rationale (2026-04-23 quant analysis, refined)

### Stage 1: 初期仮説 (engulfing_bb × LVN 単独)
| Scope | N | WR | EV_cost | Bootstrap 95% EV CI |
|---|---|---|---|---|
| baseline (all) | 158 | 27.2% | -3.43p | [-8.25, -0.70] |
| + LVN filter | 51 | 39.2% | +0.22p | **[-1.35, +1.89]** ゼロ跨ぎ |

**Bootstrap EV_lo<0 で Kelly Half Live 昇格ゲート失格**。
実コスト (spread+slip 1.33p) 込みで EV −0.11p、Top1 抜きで EV −0.14p → tail-driven。

### Stage 2: セッション分解で真のエッジ源特定
| Session | N | WR | EV_cost |
|---|---|---|---|
| **NY** | 12 | 41.7% | **+2.40p** ★ |
| **London** | 13 | 53.8% | **+0.68p** ★ |
| Overlap | 15 | 20.0% | -1.56p (drag) |
| Tokyo | 11 | 45.5% | -0.27p |

Overlap と Tokyo が LVN エッジを打ち消していた。London/NY のみが真のエッジ源。

### Stage 3: 精密化後
- 合計 N=25 (London 13 + NY 12), 複合 EV ≈ +1.5p/trade
- Shadow で独立 N 蓄積 → 変種固有 Bootstrap EV_lo>0 確認後 Kelly Half Live 検討

## Signal Logic
Base `engulfing_bb` → MassiveSignalEnhancer → LVN フラグ判定 + UTC時間判定の両立時のみ
`entry_type` を `engulfing_bb_lvn_london_ny` に書き換え。

ルーティング実装: `modules/shadow_variants.py:derive_variant_entry_type()`

## Current Configuration
- **Tier**: PHASE0_SHADOW (新 entry_type として自動フォールバック)
- **Lot**: N/A (shadow only)
- **Promotion gate**:
  - 変種固有 N≥30 (過去 base subset N=25 は参考値、shadow 実測で再確認)
  - Bootstrap EV_cost_lo > 0 (実測 spread+slip 反映)
  - PF > 1.5, Wilson WR_lo > 0.35
  - Top1-drop test で EV 残る (tail-driven でない)
- **Demotion gate**: Shadow N=50 で EV_cost<0 または WR<35% → 破棄

## Lesson: 単独フィルタ → 多重フィルタへの精密化
- N/WR/EV だけなら LVN 単独で「改善」に見えた
- Bootstrap CI + 実コスト検証で失格判定
- セル分解で真のエッジ源 (LVN × London/NY) を特定し精密化
- 「部分的クオンツの罠」回避の典型例

## Related
- [[engulfing-bb]] — ベース戦略
- [[shadow-subcell-analysis-2026-04-23]] — 分析母体
- 検証スクリプト: `/tmp/bootstrap_engulfing_lvn.py`
- `modules/shadow_variants.py` — ルーティング実装
- `modules/massive_signals.py:218-301` — LVN 判定ロジック
