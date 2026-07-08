# Trendline Sweep

## Overview
- **Entry Type**: `trendline_sweep`
- **Category**: SMC / TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: ELITE_LIVE (全ペア自動通過)
- **Active Pairs**: 全ペア (ELITE_LIVE bypasses promotion system)

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_USD | 73 | 80.8% | +0.927 | 2.52 | +67.7p |
| GBP_USD | 134 | 73.1% | +0.599 | 1.68 | +80.3p |

## Live Performance (post-cutoff)
- **2026-07-07 (rule:R2) HTF mixed cell stop**: GBP_USD × HTF mixed (4H+1D 不一致) セルの live 転送停止 + shadow 退避。clean live (06-03..07-03) mixed N=15 EV=−3.38p/−50.7p vs aligned N=4 +1.5p、shadow mixed N=7 EV=−7.20p corroborate。タグ「シグナル抑制中」は診断のみで mixed は DTE 候補に no-op だった構造の是正。再 live 化は R1 のみ。詳細: [[mtf-mixed-gate-noop-forensic-2026-07-07]]
- **2026-06-25**: Live N=24, WR=66.7%, PnL=-17.0pip (demo/stats, is_shadow=false). WR tracks the BT (73-81%) but cumulative PnL still net-negative — losses sized larger than the high-WR offsets on the current regime.
- 🟢 **Confirmed LIVE fill 2026-06-24 17:27 UTC**: daytrade_gbpusd GBP_USD SELL 5000u, **oanda#541666** (`bridge_status=filled`, non-empty trade id). First confirmed live fill for the ELITE_LIVE pipeline since the 06-16/17/19 awaiting-fill sends. Landed on GBP_USD — the book's #1 30d drag pair. Outcome of #541666 not yet in the closed-trade aggregate.
- Original FORCE_DEMOTION basis: Live N=2 WR=0% PnL=-29.8pip. BT 365d recovery path confirmed positive EV on EUR/GBP → ELITE_LIVE promotion (v9.0).

## Signal Logic
Trendline liquidity sweep strategy. Identifies trendlines where stop losses accumulate, enters after price sweeps beyond the trendline (triggering stops) then reverses back inside. Combines SMC stop-hunt logic with trendline-based entry zones.

## Current Configuration
- Lot Boost: default (1.0x)
- **HTF_MIXED_LIVE_STOP_CELLS**: GBP_USD (2026-07-07, rule:R2) — HTF mixed 時は live 停止・shadow のみ (`strategies/daytrade/__init__.py`)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none (ELITE_LIVE 所属のため PP 指定は冗長 — v9.0 で整理。Historical: EUR_USD v2.1 BT EV=+0.927 WR=80.8% / GBP_USD v2.1 BT EV=+0.599 WR=73.1%)
- 履歴: Previously FORCE_DEMOTED (Live N=2 WR=0% -29.8pip)。v9.0 で 365d BT GBP EV=+0.60 / EUR EV=+0.93 に基づき ELITE_LIVE 昇格、FORCE_DEMOTED / PAIR_PROMOTED 整理。

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
