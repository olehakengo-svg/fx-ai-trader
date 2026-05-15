# EMA Trend Scalp

## Overview
- **Entry Type**: `ema_trend_scalp`
- **Category**: TF (Trend Following)
- **Timeframe**: Scalp 1m/5m
- **Status**: FORCE_DEMOTED (v9.2, 2026-04-17) — 全ペア強制Shadow
- **Active Pairs**: 全ペアShadow のみ (OANDA 転送なし、データ蓄積継続)

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
Post-cut N=11 WR=27.3% EV=-0.70 (BEV below threshold). LOT_BOOST reduced 1.5x to 1.0x in v8.9.

**v9.2 FORCE_DEMOTE 根拠 (2026-04-17)** — [[sell-bias-forensics-2026-04-17]]:

| Regime × Direction | N | Total | WR |
|---|---|---|---|
| up_trend × BUY | 20 | −? | 15% |
| uncertain × BUY | 9 | −21.0p | 11% |

全 regime で WR 11-15%。仕様はトレンドフォローだが up_trend でも勝てない。Live 9日合計で −43.6p 寄与。Shadow 継続でデータ蓄積、N≥30 で再評価。

**v9.5 Live pair-level 実測 (2026-04-20)** — [[ema-tr-live-breakdown-2026-04-20]]:

| Pair | Live N | WR% | PnL | EV |
|---|---|---|---|---|
| USD_JPY | 19 | 26.3 | −17.5 | −0.92 |
| EUR_USD | 16 | 25.0 | −19.5 | −1.22 |
| GBP_USD | 4 | 0.0 | −6.6 | −1.65 |
| **合計** | **39** | **23.1** | **−43.6** | **−1.12** |

全ペアで shadow と符号一致の負EV (USD_JPY shadow EV=−0.94 ≈ Live −0.92)。
Live 全 39件 は v9.2 FORCE_DEMOTE 直前 (2026-04-03〜04-16) に発生、v9.5 の demo_db migration 修正で shadow pool 化済。

## Signal Logic
Scalp-timeframe trend following using EMA alignment. Enters in the direction of EMA trend on short-term pullbacks, with tight stop loss and quick take profit. Designed for high-frequency entries during strong trending sessions.

## Current Configuration
- Lot Boost: 1.0x (v8.9: reduced from 1.5x, post-cut underperforming)
- PAIR_DEMOTED: EUR_USD (v8.9: N=8 WR=25.0% EV=-0.94 Kelly=-16.3%), USD_JPY (v9.5: Live N=19 WR=26.3% EV=-0.92 PnL=-17.5)
- PAIR_PROMOTED: none
- Previously: PAIR_DEMOTED×USD_JPY removed in v8.9 (SELL PB境界バグ修正→再蓄積) → v9.5 再追加 (v9.2 FORCE_DEMOTE 以降 "再蓄積" 方針は無効化)

## 2026-05-15 redesign audit — `aligned × BUY × GBP_USD` cell 発見

Live shadow DB (N=75 decided) を harness にした cell ablation で **`mtf_alignment='aligned' AND direction='BUY' AND instrument='GBP_USD'`** に N=10, WR=50%, EV=+2.16 pips の +EV cell を発見。

| Cell | N | WR | EV | NetP |
|---|---|---|---|---|
| aligned × BUY × GBP_USD | 10 | 50.0% | **+2.16** | **+21.6** |
| その他 全 cell 合計 | 65 | 20.0% | −1.94 | −126.0 |

- 3-axis 乖離: Python BT 365d WR=53-62% / TV WR=35.8% / Live WR=24% — Live が canonical
- N=10 は promotion gate 未到達 (要 N≥30〜50)
- Pre-reg LOCK: [[ema-trend-scalp-redesign-prereg-2026-05-15]] / audit: [[ema-trend-scalp-redesign-2026-05-14]]
- 次セッション punch list: `ETS_REDESIGN_V3` env flag 実装 + cell-conditional 180d BT + Sentinel shadow 累積 → N=30 で再 audit

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
- [[ema-trend-scalp-redesign-2026-05-14]] — 本 redesign audit
- [[ema-trend-scalp-redesign-prereg-2026-05-15]] — Pre-reg LOCK (本 audit の hash 固定)
