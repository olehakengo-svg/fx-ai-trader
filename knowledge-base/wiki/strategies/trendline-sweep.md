# Trendline Sweep

## Overview
- **Entry Type**: `trendline_sweep`
- **Category**: SMC / TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: PAIR_DEMOTED (全セル shadow-first — 2026-07-15, rule:R2)
- **Active Pairs**: なし (live)。EUR_USD / GBP_USD / EUR_GBP は `_PAIR_DEMOTED` で shadow 継続、残余ペアは Phase0 SHADOW

## 判断履歴

### 2026-07-15 (rule:R2): 全セル shadow-first demote — ELITE_LIVE all-pairs bypass 除去
- **Pre-reg**: `trendline_sweep_gbpusd_pairscope_2026-07-13` (`agents/cma/prereg_ledger.jsonl`, status=resolved, reviewer=SATISFIED, verdict 2026-07-13T20:58Z)。裁量ではなく pre-reg terminal action の執行。
- **根拠 (12y MASSIVE per-cell WF、本番 trigger 無変更)**:

| Cell | N | WR | netEV | grossEV | Wilson_lo | WF | p (BH-FDR) | Verdict |
|---|---|---|---|---|---|---|---|---|
| EUR_USD | 3036 | 43.8% | −0.483 | +0.945 | 0.4205 | 1/4 | 0.881 | FAIL |
| GBP_USD | 4884 | 41.1% | −3.121 | −0.095 | 0.3972 | 0/4 | 1.0 | FAIL |
| EUR_GBP | 2829 | 41.5% | −1.449 | +0.788 | 0.3973 | 0/4 | 1.0 | FAIL |

- BH-FDR (q=0.10, m_eff=4) 生存ゼロ。GBP_USD は **gross 段階で負** (両 leg net 負: BUY −8345.75p / SELL −6898.19p) = 摩擦修復では救えない。forward LIVE (N=19 WR=63.2% netEV=−2.35 RR=0.15) も corroborate。pre-reg 予測 EUR_USD=PASS は測定で反証され、そのまま報告 (honest contradiction)。
- **ELITE_LIVE の昇格根拠だった 365d favorable BT (GBP +0.60 / EUR +0.93、WR 73-81%) は 12y WF で反証** (WR 41-44% に崩壊、EV 符号反転)。
- **実装**: `modules/demo_trader.py` の `_ELITE_LIVE` から除去 (member ゼロ → 空集合化)、`_PAIR_DEMOTED` に 3 セル追加 (gbp_deep_pullback 2026-05-04 と同型の per-cell demote)。`TRENDLINE_SWEEP_REDESIGN_V2=1` env の live 復活パスも PAIR_DEMOTED 先勝ちで無効。shadow emit (is_shadow=1) は継続 (4原則#3、再LIVE化の N 蓄積に必須)。
- **再LIVE化条件 (R1、cell 単位)**: forward shadow N≥20 ∧ Wilson_lo≥0.40 (FDR) ∧ WR≥BE-WR@realized-payoff。favorable BT のみでの再昇格は不可。EUR_USD の live re-qual は WS3 §8.3(c) で別途管理。
- **BT**: `bt-results/trendline_sweep-12y-pairscope-2026-07-13.json` / 分析: `reports/loss_hunt-trendline_sweep-gbpusd-2026-07-13.md`

## BT Performance (365d, 15m) — 12y WF で反証済み (上記参照)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_USD | 73 | 80.8% | +0.927 | 2.52 | +67.7p |
| GBP_USD | 134 | 73.1% | +0.599 | 1.68 | +80.3p |

## Live Performance (post-cutoff)
- **2026-07-13 forward LIVE (pre-reg 内)**: GBP_USD LIVE N=19 WR=63.2% netEV=−2.35p RR=0.15 MFE+3.08 — gross 負、継続エッジなし。
- **2026-07-07 (rule:R2) HTF mixed cell stop**: GBP_USD × HTF mixed (4H+1D 不一致) セルの live 転送停止 + shadow 退避。clean live (06-03..07-03) mixed N=15 EV=−3.38p/−50.7p vs aligned N=4 +1.5p、shadow mixed N=7 EV=−7.20p corroborate。タグ「シグナル抑制中」は診断のみで mixed は DTE 候補に no-op だった構造の是正。再 live 化は R1 のみ。詳細: [[mtf-mixed-gate-noop-forensic-2026-07-07]]
- **2026-06-25**: Live N=24, WR=66.7%, PnL=-17.0pip (demo/stats, is_shadow=false). WR tracks the BT (73-81%) but cumulative PnL still net-negative — losses sized larger than the high-WR offsets on the current regime.
- 🟢 **Confirmed LIVE fill 2026-06-24 17:27 UTC**: daytrade_gbpusd GBP_USD SELL 5000u, **oanda#541666** (`bridge_status=filled`, non-empty trade id). First confirmed live fill for the ELITE_LIVE pipeline since the 06-16/17/19 awaiting-fill sends. Landed on GBP_USD — the book's #1 30d drag pair. Outcome of #541666 not yet in the closed-trade aggregate.
- Original FORCE_DEMOTION basis: Live N=2 WR=0% PnL=-29.8pip. BT 365d recovery path confirmed positive EV on EUR/GBP → ELITE_LIVE promotion (v9.0).

## Signal Logic
Trendline liquidity sweep strategy. Identifies trendlines where stop losses accumulate, enters after price sweeps beyond the trendline (triggering stops) then reverses back inside. Combines SMC stop-hunt logic with trendline-based entry zones.

## Current Configuration
- Lot Boost: default (1.0x)
- **PAIR_DEMOTED**: EUR_USD / GBP_USD / EUR_GBP (2026-07-15, rule:R2 — 全セル shadow-first。上記判断履歴参照)
- **HTF_MIXED_LIVE_STOP_CELLS**: GBP_USD (2026-07-07, rule:R2) — HTF mixed 時は live 停止・shadow のみ (`strategies/daytrade/__init__.py`)。2026-07-15 demote の部分集合だが defense-in-depth として残置 (再LIVE化時も独立に R1 解除が必要)
- PAIR_PROMOTED: none
- 履歴: FORCE_DEMOTED (Live N=2 WR=0% -29.8pip) → v9.0 で 365d BT GBP EV=+0.60 / EUR EV=+0.93 に基づき ELITE_LIVE 昇格 → 2026-07-15 に 12y WF で全セル反証、PAIR_DEMOTED (shadow-first) へ降格。

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
- [[mtf-mixed-gate-noop-forensic-2026-07-07]] — GBP_USD mixed cell stop
