# Kalman D7 EMA75 Break (v18f)

## Overview
- **Entry Type**: `kalman_d7_ema75_break`
- **Category**: TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: SHADOW (new strategy, 2026-05-20 deployment)
- **Active Pairs**: USDJPY only

## BT Performance (TV Pine, 10.5mo M15)
- **N**: 68
- **WR**: 30.88%
- **PF**: 2.087
- **Net P&L**: +567.64 JPY (+0.57%)
- **Max DD**: 0.10%
- **Avg Win**: 52 JPY / **Avg Loss**: 11 JPY
- **W/L ratio**: 4.67×
- **Avg bars in winners**: 102 (~25h)

⚠️ BT 期間 = USDJPY uptrend (2025-07-01 → 2026-05-19)。Regime-bound edge。

## Signal Logic
Same entry as v17 (kalman_d7_po_dn_flip):
- Perfect Order UP transition + DIST < 3 ATR + GAP < 3 ATR + ATR Q2-Q4 + RSI < 70 + ASN/LDN/NY session

## Exit Logic
- **TP**: 2.5×ATR (EMA75 close break approximation, balanced)
- **SL**: 2.5×ATR
- **Max hold**: 120 bars (~30h)
- 1:1 RR with wider SL = more breathing room, balanced timing

## Current Configuration
- Lot Boost: default (1.0x)
- Mode: enabled, evaluated by DaytradeEngine
- Live promotion: depends on tier system

## Risk Notes
- Same as v17 sibling (regime-bound, post-hoc, single sample)

## Related
- [[kalman-d7-po-dn-flip]] — sibling (v17 variant, max-ride)
- [[kalman-d7-trail-atr]] — sibling (v18e variant, tight trail)
- [[index]] — Tier classification
