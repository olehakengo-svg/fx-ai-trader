# Kalman D7 PO-DN Flip (v17)

## Overview
- **Entry Type**: `kalman_d7_po_dn_flip`
- **Category**: TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: SHADOW by default; LIVE via `KALMAN_D7_LIVE_ENABLE=1` env var (rule:R1 例外, 2026-05-20)
- **Active Pairs**: USDJPY only

## BT Performance (TV Pine, 10.5mo M15)
- **N**: 46
- **WR**: 23.91%
- **PF**: 3.866
- **Net P&L**: +997.28 JPY (+1.00%)
- **Max DD**: 0.11%
- **Avg Win**: 122 JPY / **Avg Loss**: 9.94 JPY
- **W/L ratio**: 12.30×
- **Avg bars in winners**: 458 (~115h)

⚠️ BT 期間 = USDJPY uptrend (2025-07-01 → 2026-05-19)。Regime-bound edge。

## Signal Logic
Perfect Order UP (close > EMA25 > EMA75 > EMA200) の **transition (start)** で LONG。
Entry filters (v16 forensic 導出):
- DIST(close-ema200)/ATR < 3.0
- GAP(ema25-ema200)/ATR < 3.0
- ATR Q2-Q4 (P20 ≤ ATR < P80)
- RSI < 70
- Session ∈ {ASN, LDN, NY} UTC (OVL/DEAD除外)

## Exit Logic
- **TP**: 5.0×ATR (PO-DN regime flip approximation, hold for max winner ride)
- **SL**: 1.5×ATR
- **Max hold**: 480 bars (~120h)

## Current Configuration
- Lot Boost: default (1.0x)
- Mode: enabled, evaluated by DaytradeEngine
- Live promotion: depends on tier system

## Risk Notes
- **Regime-bound**: USDJPY uptrend continuation 前提
- **Strategy 間相関**: 同 entry の v18f / v18e と高相関 (3 spec 同時 entry 多)
- **Post-hoc selection bias**: v16 forensic で 35 cells から選択 (m=35 補正未実施)
- **Single sample bias**: 10.5ヶ月 single period

## Emergency stops
- USDJPY close < D1 EMA200 → entry 停止検討
- Aggregate (3 spec) DD > 5% → 全停止
- PF < 0.8 over N≥30 → 該当 spec 単独停止

## Related
- [[kalman-d7-ema75-break]] — sibling (v18f variant)
- [[kalman-d7-trail-atr]] — sibling (v18e variant)
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
