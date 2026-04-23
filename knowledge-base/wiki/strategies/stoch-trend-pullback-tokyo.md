# Stoch Trend Pullback × Tokyo Session (Shadow Variant)

## Overview
- **Entry Type**: `stoch_trend_pullback_tokyo`
- **Base Strategy**: `stoch_trend_pullback`
- **Category**: Scalp TF-pullback (session-specialized variant)
- **Timeframe**: 15m (inherits base)
- **Status**: PHASE0_SHADOW (2026-04-23 〜, N 蓄積中)
- **Filter**: UTC 0〜7 時 (Tokyo session) に発火したシグナルのみ

## Rationale (2026-04-23 quant analysis)

`stoch_trend_pullback` ベースライン (shadow post-cutoff):

| Scope | N | WR | EV_cost | Wilson 95% |
|---|---|---|---|---|
| baseline (all sessions) | — | — | 負 EV | — |
| **session=Tokyo** | **上位セル** | **勝率上振れ** | **+EV領域** | **lo>0 相当** |

Tokyo session セルが Lever-B (条件付き勝率) 分析で最上位。詳細ロジック:
- USD_JPY 主体の base stoch_trend_pullback は、東京時間の実需フロー (仲値前後) とレンジ性が pullback 仕様と相性良
- London/NY の breakout 環境では trend 継続側に抜けて pullback が不成立

生データ: `/tmp/improve_strategy.py` Lever B 出力参照。

## Signal Logic
Base `stoch_trend_pullback` のゲート通過後、`datetime.now(timezone.utc).hour` が `0 <= h < 7` の場合のみ
`entry_type` を `stoch_trend_pullback_tokyo` に書き換え。

ルーティング実装: `modules/shadow_variants.py:derive_variant_entry_type()`

## Current Configuration
- **Tier**: PHASE0_SHADOW (新 entry_type として自動フォールバック)
- **Lot**: N/A (shadow only)
- **Promotion gate**: Shadow N≥30 かつ Bootstrap EV_lo > 0 で Kelly Half Live 検討
- **Demotion gate**: Shadow N=50 で EV_cost<0 または WR<40% → 破棄

## Related
- [[stoch-trend-pullback]] — ベース戦略
- [[shadow-subcell-analysis-2026-04-23]] — 分析母体
- `modules/shadow_variants.py` — ルーティング実装
