# DT SR Channel Reversal

## Overview
- **Entry Type**: `dt_sr_channel_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (未検証, Sentinel蓄積)
- **Active Pairs**: Sentinel on all pairs

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_JPY | 362 | 63.8% | +0.178 | 1.39 | +64.6p |

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| dt_sr_channel | USD_JPY | 9 | 3 | 6 | 33% | -37.6p |
| dt_sr_channel | GBP_USD | 6 | 1 | 5 | 17% | -27.5p |

## Signal Logic
Support/resistance channel reversal for daytrade timeframe. Identifies horizontal SR zones and channel boundaries, entering reversal trades when price reaches channel extremes with confirmation. DT-tuned version of sr_channel_reversal.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy

## 2026-07-02 LIVE demote (rule:R2)
`(dt_sr_channel_reversal, EUR_JPY)` を `_PAIR_PROMOTED` から除去。30d clean live N=10 WR=40% -30.9pip (Wlo=16.8 BFlo=9.5, 本番実測 2026-07-02)。昇格根拠 (shadow N=12 EV=+14.28 small-N / BT EV=+0.178 marginal) を live が反証。Shadow 継続。再昇格は R1 のみ。詳細: [[live-bleeder-demotions-2026-07-02]]

## 2026-11-06 shadow 記録 (wiki-daily 03:18Z、記録のみ — shadow 簿、live 統計 N 21 / −34.2 は不変)
- 11-05T02:02Z〜11-06T03:18Z の shadow 決済 94 本 −318.8 pip のうち **本戦略 20 本 −199.9 (2W / 18L、WR 10%) = 窓損失の 62.7%**。BUY 17 / SELL 3、EUR_USD 7 (−34.3) / GBP_JPY 6 (−86.6) / EUR_JPY 3 (−53.9) / GBP_USD 2 / EUR_GBP 1 / USD_JPY 1、close_reason `SL_HIT` 18 / `SIGNAL_REVERSE` 2。USD_JPY が 13:09Z 158.45 → 翌 00:00Z 157.484 (−97p) と下げた NY→Tokyo で JPY クロスの逆張り BUY が順に SL (記述級、outcome 判定には使わない)
- 10-22 以降の 700 行窓で shadow 決済 80 本 −228.6 (30W)、日次クラスタ最大 = 11-05 の 19 本 (次点 11-02 12 / 10-23 11)
- R2 alert 11-05 23:15Z: **CRITICAL 2 cell** = EUR_JPY (N 33 / EV −2.52 / WR 42.4% / PF 0.59) + GBP_JPY (N 36 / EV −8.30 / WR 16.7% / PF 0.16)、いずれも `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` (shadow、live 非接触)。読み手は R2 alert / autopilot、本 run は記録のみ。詳細 [[2026-11-06]] 発見 3
