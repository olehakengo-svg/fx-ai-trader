# EMA Trend Scalp × NY Session (Shadow Variant)

## Overview
- **Entry Type**: `ema_trend_scalp_ny`
- **Base Strategy**: `ema_trend_scalp`
- **Category**: Scalp TF (session-specialized variant)
- **Timeframe**: 15m (inherits base)
- **Status**: PHASE0_SHADOW (2026-04-23 〜, N 蓄積中)
- **Filter**: UTC 16〜21 時 (NY session) に発火したシグナルのみ

## Rationale (2026-04-23 quant analysis)

`ema_trend_scalp` ベースライン (shadow post-cutoff):

| Scope | WR | EV_cost | Wilson |
|---|---|---|---|
| baseline (all sessions) | 負 EV | 負 EV | — |
| **session=NY** | **上振れ** | **+EV 領域** | **lo>0 相当** |

NY セッションが Lever-B 分析で最上位セル。詳細ロジック:
- ema_trend_scalp は trend-following、NY は USD 主導のクリーンな directional move が出やすい
- Tokyo/London は range/breakout 混在で ema pullback のシグナル品質が劣化

生データ: `/tmp/improve_strategy.py` Lever B 出力参照。

## Signal Logic
Base `ema_trend_scalp` のゲート通過後、`datetime.now(timezone.utc).hour` が `16 <= h < 21` の場合のみ
`entry_type` を `ema_trend_scalp_ny` に書き換え。

ルーティング実装: `modules/shadow_variants.py:derive_variant_entry_type()`

## Current Configuration
- **Tier**: PHASE0_SHADOW (新 entry_type として自動フォールバック)
- **Lot**: N/A (shadow only)
- **Promotion gate**: Shadow N≥30 かつ Bootstrap EV_lo > 0 で Kelly Half Live 検討
- **Demotion gate**: Shadow N=50 で EV_cost<0 または WR<40% → 破棄

## Related
- [[ema-trend-scalp]] — ベース戦略
- [[shadow-subcell-analysis-2026-04-23]] — 分析母体
- `modules/shadow_variants.py` — ルーティング実装
