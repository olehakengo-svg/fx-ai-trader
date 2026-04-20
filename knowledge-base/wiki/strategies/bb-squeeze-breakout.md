# BB Squeeze Breakout

## Overview
- **Entry Type**: `bb_squeeze_breakout`
- **Category**: Breakout / VOL
- **Timeframe**: Scalp 1m/5m, DT 15m
- **Status**: FORCE_DEMOTED (global) — v9.1 PAIR_PROMOTED 死コード削除; v9.x (2026-04-20) demo_db legacy override も削除
- **Active Pairs**: none (shadow only)

## BT Performance (365d, 15m)
BT data not available for this entry_type in DT comprehensive scan.

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| bb_squeeze | EUR_USD | 8 | 0 | 8 | 0% | -25.7p |

## Signal Logic
Detects Bollinger Band squeeze (bandwidth contraction below threshold), then enters on the breakout direction when bands expand. Momentum confirmation via volume or candle body size filters breakout validity.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED globally
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: **なし** (v9.1 で全削除, v9.x 2026-04-20 で demo_db legacy override も削除)

## 2026-04-20 判断履歴 (Priority 2 PAIR_PROMOTED 監査)
短期 BT (180d Scalp) で正 EV 候補が複数存在するが、全て N<100:
- USD_JPY 5m: N=18 EV=+0.457
- EUR_USD 1m: N=46 EV=+0.274 (60d EV=+0.473 → 180d 低下)
- EUR_JPY 5m: N=19 EV=+0.422
- GBP_JPY 1m: N=67 EV=+0.340

**Live 実績 (post 2026-04-07):**
- USD_JPY: N=52 (shadow=42, live=10) WR=26.9% EV=+0.406 (実弾 live=10 のみ)
- EUR_USD: N=26 (shadow=22, live=4) WR=11.5% EV=-2.323 **壊滅的**

Gate2 (N≥100) 未通過, Gate5 (Live N≥10) も境界 — 365d Scalp BT 実装後に再審査。
参照: [[pair-promoted-candidates-2026-04-20]]

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
