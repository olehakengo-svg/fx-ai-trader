# BB Squeeze Breakout

## Overview
- **Entry Type**: `bb_squeeze_breakout`
- **Category**: Breakout / VOL
- **Timeframe**: Scalp 1m/5m, DT 15m
- **Status**: PAIR_PROMOTED (USD_JPY のみ) + FORCE_DEMOTED (EUR/GBP 保護)
- **Active Pairs**: USD_JPY (trial, 1.0x lot)

## BT Performance (365d, 5m Scalp)

| Pair | N | WR | EV | PnL | 判定 |
|---|---|---|---|---|---|
| USD_JPY | 42 | 76.2% | +0.426 | +17.9p | ✅ PAIR_PROMOTED |
| EUR_USD | shadow EV=-3.05 (5d) | — | — | — | ❌ FORCE_DEMOTED 継続 |
| GBP_USD | shadow N=4 (5d) | — | — | — | ❌ FORCE_DEMOTED 継続 |

## Shadow Performance (2026-04-21 現在)

| Pair | pre-Cutoff (〜4/15) | post-Cutoff (4/16〜) |
|---|---|---|
| USD_JPY | N=42 EV=+0.406 ✅ | N=41 EV=+1.55 ✅ |
| EUR_USD | — | N=14 EV=-3.05 ❌ |
| GBP_USD | — | N=4 EV=+5.97 (N小) |

## 2026-04-21 PAIR_PROMOTED 判断

**根拠:**
- 365d BT USD_JPY 5m: N=42 WR=76.2% EV=+0.426 (CLAUDE.md N≥30 GO 条件クリア)
- Shadow USD_JPY 累計 N=83 (pre+post) 両期間で正 EV
- EUR_USD は shadow EV=-3.05 で pair-specific promotion が正解
- FORCE_DEMOTED 元理由「ブレイクアウト直後のスプレッド構造赤字」は GBPUSD 1.0pip に有効だが USD_JPY 0.5pip では BT が正 EV を示した

**実装:** `_PAIR_PROMOTED` に `("bb_squeeze_breakout", "USD_JPY")` 追加 (FORCE_DEMOTED 残存)
**Lot**: 1.0x trial (N≥50 & WR継続 → 1.3x昇格候補)

**次回審査条件:**
- Live N≥20 到達時に WR/EV 確認
- WR < 55% or EV < 0 が 15件連続 → PAIR_DEMOTED 候補

## Signal Logic
Detects Bollinger Band squeeze (bandwidth contraction below threshold), then enters on the breakout direction when bands expand. Momentum confirmation via volume or candle body size filters breakout validity.

## 2026-04-20 判断履歴 (Priority 2 PAIR_PROMOTED 監査)
短期 BT (180d Scalp) で正 EV 候補が複数存在するが、全て N<100:
- USD_JPY 5m: N=18 EV=+0.457
- EUR_USD 1m: N=46 EV=+0.274 (60d EV=+0.473 → 180d 低下)
- EUR_JPY 5m: N=19 EV=+0.422
- GBP_JPY 1m: N=67 EV=+0.340

**Live 実績 (post 2026-04-07):**
- USD_JPY: N=52 (shadow=42, live=10) WR=26.9% EV=+0.406 (実弾 live=10 のみ)
- EUR_USD: N=26 (shadow=22, live=4) WR=11.5% EV=-2.323 **壊滅的**

Gate2 (N≥100) 未通過のため保留 → 2026-04-21 に 365d BT 実施で条件クリア。

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
