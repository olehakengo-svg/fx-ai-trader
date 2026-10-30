# Kalman D7 Trail ATR (v18e)

## Overview
- **Entry Type**: `kalman_d7_trail_atr`
- **Category**: TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: 🔻 **LIVE 停止 (R2、2026-10-30)** — pre-reg LOCK 09-01 §R2「LIVE N≥10 ∧ EV<0 → live 停止」成立 (prefix 合算 N=12、demo EV −1.71p / broker ≈ −3.0p、両基準負)。code pin `_KALMAN_D7_R2_LIVE_STOP=True` で `_kalman_d7_live_eligible` を閉鎖、shadow (UNIVERSAL_SENTINEL) 蓄積は継続。再 live 化 = R1 ([[kalman-d7-r2-live-stop-2026-10-30]])。旧: SHADOW by default; LIVE via `KALMAN_D7_LIVE_ENABLE=1` env var (rule:R1 例外, 2026-05-20 → 09-01 LOCK 1000u carve-out)
- **Active Pairs**: USDJPY only

## BT Performance (TV Pine, 10.5mo M15)
- **N**: 65
- **WR**: 55.38%
- **PF**: 1.181
- **Net P&L**: +72.66 JPY (+0.07%)
- **Max DD**: 0.08%
- **Avg Win**: 13 JPY / **Avg Loss**: 14 JPY
- **W/L ratio**: 0.95×

⚠️ BT 期間 = USDJPY uptrend (2025-07-01 → 2026-05-19)。Regime-bound edge。

## Signal Logic
Same entry as v17/v18f.

## Exit Logic
- **TP**: 1.5×ATR (tight, small winner mass production)
- **SL**: 2.0×ATR
- **Max hold**: 60 bars (~15h)
- **Broker trail recommended**: TV 元仕様は trail_points = 1×ATR activation + trail_offset = 0.5×ATR
- 高 WR (55%) → psychological 楽な variant

## Current Configuration
- Lot Boost: default (1.0x)
- Mode: enabled, evaluated by DaytradeEngine
- Live promotion: depends on tier system

## Risk Notes
- Same regime-bound, post-hoc, single-sample biases as siblings
- Low Win/Loss ratio (0.95) → commission impact 大、edge thin

## Related
- [[kalman-d7-po-dn-flip]] — sibling (v17 variant, max-ride)
- [[kalman-d7-ema75-break]] — sibling (v18f variant, balanced)
- [[index]] — Tier classification


## 🔻 2026-10-30 更新 (autopilot、rule:R2): kalman_d7 3 variant の LIVE 停止 — prefix 合算 clean live N=12 (本 variant は live fill 0) で pre-reg R2 ゲート (N≥10 ∧ EV<0) 成立。code pin `_KALMAN_D7_R2_LIVE_STOP` で live 経路を閉鎖、shadow 継続。詳細 [[kalman-d7-r2-live-stop-2026-10-30]]
