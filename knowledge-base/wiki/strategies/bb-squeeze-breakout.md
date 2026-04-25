# BB Squeeze Breakout

## Overview
- **Entry Type**: `bb_squeeze_breakout`
- **Category**: Breakout / VOL
- **Timeframe**: Scalp 1m/5m, DT 15m
- **Status**: PAIR_PROMOTED (USD_JPY) — EUR/GBP/JPYcross は PAIR_DEMOTED で保護
- **Active Pairs**: USD_JPY (trial, 1.0x lot)

## BT Performance (365d, 5m Scalp)

| Pair | N | WR | EV | PnL | 判定 |
|---|---|---|---|---|---|
| USD_JPY | 43 | 74.4% | +0.354 | +22.5p | ✅ PAIR_PROMOTED |
| EUR_USD | shadow EV=-3.05 (5d) | — | — | — | ❌ PAIR_DEMOTED 継続 |
| GBP_USD | shadow N=4 (5d) | — | — | — | ❌ PAIR_DEMOTED 継続 |

### 深部クオンツ分析 (USD_JPY, 2026-04-21 追加検証)

| Metric | Value | 基準 | 判定 |
|---|---:|---|---|
| Profit Factor | **1.818** | > 1.1 | ✅ 65% margin |
| Wilson 95% CI for WR | [59.8%, 85.1%] | 下限 > BEV_WR 34.4% | ✅ 25pp margin |
| Sharpe (per-trade) | +0.294 | positive | ✅ σ=1.78 |
| Walk-Forward 3バケット EV | +0.09 / +1.03 / +0.45 | 全 bucket > 0 | ✅ regime 遷移耐性 |
| Monthly positive ratio | 8/11 (73%) | > 60% | ✅ consistency |

**W3 (2026-01〜04) の意義**: range_tight dominant 期間 N=15 WR=73.3% EV=+0.453
→ 「BO が range_tight 依存」仮説は否定. trending 期間 (W2) の方が強い (+1.03) が range 期間も黒字.

## Shadow Performance (2026-04-21 現在)

| Pair | pre-Cutoff (〜4/15) | post-Cutoff (4/16〜) |
|---|---|---|
| USD_JPY | N=42 EV=+0.406 ✅ | N=41 EV=+1.55 ✅ |
| EUR_USD | — | N=14 EV=-3.05 ❌ |
| GBP_USD | — | N=4 EV=+5.97 (N小) |

### 2026-04-25 監視: USD_JPY Shadow direction-asymmetric edge

post-cutoff (>=2026-04-16) Shadow (WEEKEND_CLOSE 除外) を direction 分解:

| Side | N | WR | EV | 判定 |
|---|---|---|---|---|
| **SELL** | 15 | 46.7% | **+4.94p** | ★ 正方向 edge 候補 |
| BUY | 26 | 19.2% | -0.73p | ✗ 負 EV |
| Aggregate | 41 | 29.3% | +1.34p | ▲ direction 混合 (誤解を招く) |

aggregate「N=41 EV=+1.55」は SELL の正 EV が BUY 負を相殺した混合。実態は SELL のみ. cell-level (USD_JPY × SELL) で Shadow N≥20 蓄積後 pre-reg LOCK 候補 (mechanism: filter-type → Wilson WR + EV CI 下限 binding gate). Live 04-16 以降 0 fire (PAIR_PROMOTED USD_JPY は active だが、Q4/MTF gate or cooldown で抑制中の可能性).

**注**: aggregate-only 表記は [[lesson-confounding-in-pooled-metrics-2026-04-23]] と同類のリスク。cell-level monitor 推奨.

## 2026-04-21 PAIR_PROMOTED 判断

**根拠:**
- 365d BT USD_JPY 5m: N=42 WR=76.2% EV=+0.426 (CLAUDE.md N≥30 GO 条件クリア)
- Shadow USD_JPY 累計 N=83 (pre+post) 両期間で正 EV
- EUR_USD は shadow EV=-3.05 で pair-specific promotion が正解
- FORCE_DEMOTED 元理由「ブレイクアウト直後のスプレッド構造赤字」は GBPUSD 1.0pip に有効だが USD_JPY 0.5pip では BT が正 EV を示した

**実装:** `_PAIR_PROMOTED` に `("bb_squeeze_breakout", "USD_JPY")` 追加 (FORCE_DEMOTED 残存)
**Lot**: 1.0x trial (N≥50 & WR継続 → 1.3x昇格候補)

**次回審査条件**: 詳細基準は **[[pre-registration-2026-04-21]]** §3.1 (binding pre-reg)
- N=10 Wilson 下限<20% → 即 PAIR_DEMOTE / N=15 WR<40% + sum<-5 → PAIR_DEMOTE
- N=20 PF<0.9 → PAIR_DEMOTE / N=30 PF≥1.5 + Sharpe>0.25 → lot 1.3x 昇格

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
