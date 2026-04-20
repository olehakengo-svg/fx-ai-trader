# EMA Pullback

## Overview
- **Entry Type**: `ema_pullback`
- **Category**: TF (Trend Following)
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED (全ペア強制 Shadow) — v9.1 PAIR_PROMOTED / PAIR_LOT_BOOST 死コード削除; v9.x (2026-04-20) demo_db legacy override も削除
- **Active Pairs**: none (shadow only)

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan (365d DT 15m で発火 0).

## Live Performance
USD_JPY (all cutoffs, fetched 2026-04-20):
- Cutoff 2026-04-07 post: N=18 (shadow=3, live=15) WR=38.9% PnL=+17.1p EV=+0.950
- Cutoff 2026-04-14 post: N=4 (shadow=3, live=1) WR=25.0% PnL=+1.8p EV=+0.450
- Cutoff 2026-04-17 post: N=0
詳細: [[pair-promoted-candidates-2026-04-20]]

## Signal Logic
Enters on pullbacks to key EMA levels (EMA21/EMA50) within an established trend. Requires higher timeframe trend alignment and waits for price to retrace to EMA support/resistance before entering in the trend direction.

## Current Configuration
- Lot Boost: default (1.0x) globally — FORCE_DEMOTED
- PAIR_DEMOTED: none
- PAIR_PROMOTED: **なし** (v9.1 で USD_JPY 削除, v9.x 2026-04-20 Priority 2 監査で demo_db override も削除。Historical: USD_JPY v8.9 N=14 WR=42.9% EV=+1.09)
- PAIR_LOT_BOOST: **なし** (v9.1 で全削除 — 死コード化のため)

## 2026-04-20 判断履歴 (Priority 2 PAIR_PROMOTED 監査)
Live N=18 (post 2026-04-07) は Shadow 主体 (shadow=3, live=15) で EV+0.95 を示すが、
365d DT BT で発火 0 のため Gate1 (EV≥+0.2) と Gate2 (N≥100) を満たさない。
demo_db.py の legacy override も削除 → 新規トレードは is_shadow=1 で確定。
参照: [[pair-promoted-candidates-2026-04-20]], [[shadow-baseline-2026-04-20]]

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
