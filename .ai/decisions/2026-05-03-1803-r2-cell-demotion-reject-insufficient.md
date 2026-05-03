---
date: 2026-05-03
task: 20260503-1747-r2-cell-demotion-lock-list
verdict: ACCEPT (Codex deliverable) / REJECT_INSUFFICIENT (Gate 0 復帰)
rule: R2
gate: Gate 0 (生存 — cell-level cut では救済不能)
---

# R2 Cell-Level Demotion LOCK list — Cell単位cut無力検証

## Verdict (Codex deliverable)

**ACCEPT** — Codex 成果物は仕様通り、counterfactual simulation は data-driven、verdict は LOCK 閾値遵守。

## Counterfactual quant findings

| 指標 | Before | After cell cut | Δ |
|---|---:|---:|---:|
| aggregate raw Kelly | -0.1737 | -0.1381 | +0.0356 |
| MC60d 破産確率 | 100.00% | **99.70%** | -0.30pp |
| EV pip/trade | -0.79 | -0.63 | +0.16 |
| Wilson_lo | 0.3551 | 0.3653 | +1.0pp |
| N | 917 | 808 | -109 |
| PF | 0.695 | 0.749 | +0.054 |
| max DD | 74.80% | 55.05% | -19.75pp |
| total pip | -720.0 | -512.0 | +208.0 |

Bonferroni m = 394 cell, α' = 0.000127。LOCK STOP_OANDA=2 cell、LOT_HALF=3 cell、counterfactual extension WATCH→STOP=13 cell。

## 結論 — Gate 0 救済 fail

cell単位の cut では **MC60d 破産確率が 100% → 99.7%** にしか改善しない。aggregate raw Kelly も clipped 0 のまま。15+3 cell cut + KEEP 147 cell の総合効果が **insufficient**。

## 真因 — high-N 中程度負 EV 戦略

`gate-progression-audit-2026-05-03.md` の strategy 別テーブルによれば、aggregate を引き下げている真犯人:

| strategy | N | EV pip | raw Kelly | aggregate 寄与 |
|---|---:|---:|---:|---:|
| bb_rsi_reversion | 324 | -0.15 | -0.0467 | 35% of N |
| fib_reversal | 97 | -0.44 | -0.1423 | 11% of N |
| macdh_reversal | 62 | -0.90 | -0.3664 | 7% of N |
| vol_surge_detector | 47 | -0.19 | -0.0548 | 5% of N |
| sr_fib_confluence | 36 | -1.78 | -0.1907 | 4% of N |
| sr_channel_reversal | 34 | -0.71 | -0.1486 | 4% of N |
| **計** | **600** | — | — | **65% of N** |

これらは「極端な loss cell」ではなく「中程度負 EV を高 N で積み上げる drag」。Bonferroni 補正下では individual cell の significance は弱いが、**aggregate への drag は致命的**。

## 次の必要分析

`feedback_ma_filter_breaks_mr` の罠を考慮しつつ、strategy × instrument 単位の counterfactual:

- bb_rsi_reversion を pair 別 demote (例: EUR_USD 停止、GBP_USD 維持)
- 同様に fib_reversal / macdh_reversal / sr_fib_confluence

特定 instrument には Bonferroni-significant edge が残っている可能性 (memory `project_dexter_fx_phase0_2026_05_03` の S3 literal 教訓)。

## Roadmap impact

- Gate 0 (生存) は cell-level R2 では救済不能。**strategy × instrument level の demote counterfactual** が次必要。
- Tier 1 LIVE / PAIR_PROMOTED 戦略の lot 構造を再設計する大手術。
- 月利100% ロードマップは引き続き **凍結相当**。

## Next task

**`r2-strategy-instrument-counterfactual-2026-05-03`** — bb_rsi_reversion / fib_reversal / macdh_reversal / sr_fib_confluence / sr_channel_reversal の **strategy × instrument 単位** demote counterfactual。各組合せで MC60d / Kelly 改善幅を計測し、Gate 0 (MC60d ≤ 90%) 復帰経路を特定。
