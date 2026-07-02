# London Breakout

## Overview
- **Entry Type**: `london_breakout`
- **Category**: Session / Breakout
- **Timeframe**: DT 15m
- **Status**: SHADOW; **USD_CHF セルは R2 shadow demote (2026-07-02)**
- **Active Pairs**: Shadow on all pairs except USD_CHF

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
London session open breakout strategy. Identifies the Asian session range and enters on the breakout of that range at London open (UTC 07:00-08:00). Directional bias from Asian session close position relative to range midpoint.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none
- SHADOW_DEMOTED_CELLS: USD_CHF (2026-07-02, rule:R2)

## 2026-07-02 R2: USD_CHF セル Shadow demote

daytrade_1h_usdchf モード監査 (本番API実測): clean N=37 WR=29.7% Wilson_lo=17.5%
sum=-88.6p (BUY -49.1p / SELL -39.5p — 両方向負)。R2 alert 13:55Z の WARN
(EV=-1.485, PF=0.30) と整合。モード内最大の現役 bleeder だったため per-cell 停止。
他ペアは非影響。再昇格は R1 のみ。詳細: [[usdchf-1h-cell-demotions-2026-07-02]]

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
