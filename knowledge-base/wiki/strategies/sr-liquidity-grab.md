# SR Liquidity Grab

## Overview
- **Entry Type**: `sr_liquidity_grab`
- **Category**: Reversal (Smart Money Concept / Liquidity Sweep)
- **Timeframe**: DT 15m
- **Status**: SHADOW_DEMOTED — R2 triggered 2026-04-28 (本番実測 EV<0 確定、SHADOW_ALWAYS から除外、enabled=True は維持)
- **Active Pairs**: USDJPY, EURUSD, GBPUSD, EURJPY, GBPJPY (全5 majors) — primary 競争通過時のみ trade 化

## 本番実測 (2026-04-28, 4 日, N=300 closed)

| Pair | N | WR | mean pnl | sum |
|---|---:|---:|---:|---:|
| USD_JPY | 173 | 26% | -1.41p | -243.9p |
| EUR_USD | 64 | 19% | -1.33p | -85.1p |
| GBP_USD | 50 | 34% | +0.31p | +15.5p |
| EUR_JPY | 9 | 22% | -6.60p | -59.4p |
| GBP_JPY | 4 | 25% | -4.47p | -17.9p |
| **合計** | **300** | — | **-0.65p** | **-390.8p** |

→ sr_anti_hunt_bounce と**同じパターン**: GBP_USD 以外で EV<0、sim 楽観バイアス。
→ OANDA forwarding 確認: 4 件流入。
→ R2 適用で SHADOW_ALWAYS_STRATEGIES から除外。

## 教訓
- [[../lessons/lesson-shadow-always-emit-cleanup-2026-04-28]]
- [[../lessons/lesson-data-source-production-first-2026-04-28]]

## 攻めの姿勢
audit weak pair も Live で確認。Shadow data 蓄積 → 30 trade で per-pair PAIR_PROMOTED 判定。

## Phase 2 Audit Findings (365d, M15, k=2.0)
- 全 pair で reversal WR が benchmark を上回る (Bonferroni 有意)
- 但し trade-outcome simulation で USD/JPY/EUR/USD/GBP/USD のみ EV>0
- Quarterly stability: USD_JPY のみ std<0.10 安定、EUR_USD/GBP_USD やや揺らぎ、JPY cross は要 Live 確認

## Signal Logic (offensive — post-hunt reversal)
1. 5 majors すべて
2. SR 近接 (`|entry - level| < 0.5 × ATR`)
3. ADX < 30
4. 直近 1-2 bar 以内に hunt 検出 (k=2.0 × ATR threshold)
5. 現在足が hunt と逆方向に動いている確認
6. SL = hunt_extreme ± 0.3 × ATR
7. TP: 対側 SR or RR=1.5

## Differentiation from `liquidity_sweep`
既存 `liquidity_sweep` (Osler 2003) は wick 構造ベースで **S/R level に紐づかない**。
本戦略は **検出された S/R level での hunt** に限定 → より selective

## Related
- [[sr-anti-hunt-bounce]] — 守備側
- [[liquidity-sweep]] — 既存の wick-based liquidity sweep
