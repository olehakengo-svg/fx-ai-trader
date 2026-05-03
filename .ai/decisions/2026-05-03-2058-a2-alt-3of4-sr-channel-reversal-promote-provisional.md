---
date: 2026-05-03
task: 20260503-1700-a2-alt-simple-structure-scalp-pre-reg
verdict: BLOCKED_NEEDS_EVIDENCE (3/4 確定、fib_reversal 待ち)
rule: R1
gate: Gate 1 (Scalp 枝 N-acceleration)
---

# A2-alt 3/4 候補確定 — `sr_channel_reversal × EUR_USD 5m` provisional Promote

## Status

**BLOCKED_NEEDS_EVIDENCE** — Bonferroni K=4 / α/K=0.0125 LOCK 下で 3/4 確定、`fib_reversal` の foreground BT 結果待ち。

## 3 候補 verdicts (確定)

| 候補 | Verdict | N | WR | EV | PF | Bonferroni p |
|---|---|---:|---:|---:|---:|---:|
| bb_squeeze_breakout × USD_JPY 5m | **Insufficient** | 24 | 75.000% | +0.913 | 4.872 | 0.00023 (N<30 pre-reg fail) |
| engulfing_bb × USD_JPY 5m | **Reject** | 30 | 53.333% | +0.212 | 1.557 | 0.0930 (α/K=0.0125 未達) |
| sr_channel_reversal × EUR_USD 5m | **Promote 🎯** | 52 | 61.538% | +0.373 | 2.724 | 0.00418 (**pass**) |
| fib_reversal × EUR_USD 1m | MISSING | — | — | — | — | — |

## sr_channel_reversal 注目

- **N=52 (≥30 ✓)**, WR=61.5% (BEV_EURUSD 39.7% +21.8pp)
- PF=2.72 (≥1.30 promote 閾値クリア)
- Bonferroni p=0.00418 < α/K=0.0125 → 統計的有意 ✓
- WF IS/OOS は final.md 詳細で確認必要 (run report に未記載)
- **OVERFIT_SUSPECTED flag**: not triggered

暫定的に **EUR_USD 5m sr_channel_reversal を Promote 候補**。ただし 4-candidate K=4 LOCK 下で aggregate verdict は fib_reversal 完了後に最終確定。

## 重要な観察 — bb_squeeze_breakout vs Insufficient

`bb_squeeze_breakout × USD_JPY 5m`: N=24 (gap_to_30=6) で WR=75% PF=4.87 EV=+0.913p — **数字が極めて良い**が N<30 pre-reg LOCK で Insufficient。memory `feedback_partial_quant_trap` 通り、N不足では promote 不可。180-365日延長で N≥30 達成すれば Promote 候補化する見込み。

## fib_reversal 進行状況

3 process duplicate run 中 (R3 wrapper fingerprint で stale 防止するが concurrent overwrite は別問題):
- PID 4527 (7:14PM, 24min CPU)
- PID 24281 (8:51PM, 17min CPU)
- PID 53439 (9:11PM, 4min CPU)

EUR_USD 1m TF は USDJPY 5m の 5x bars (260K vs 52K) → 重い。完了見込み 30-60min。

## Roadmap impact

Gate 1 unlock 候補が**初めて 1 つ確定**: `sr_channel_reversal × EUR_USD 5m`。fib_reversal が Promote/Shadow なら 2 候補、Reject なら 1 候補で進行。

注意: Gate 0 が崩壊状態 (raw Kelly < 0) で Gate 1 に進む意義は限定的。Gate 0 復帰経路 (R2 TRUE_LIVE 14-cell demote) と並行で進める必要。

## Next steps

1. fib_reversal foreground BT 完了待ち (R3 fingerprint で stale 拒否、最新 process が成功すれば fib JSON 生成)
2. Aggregate verdict 確定 (`scalp_alt_pre_reg_bt.py --aggregate`)
3. sr_channel_reversal の WF IS/OOS / max DD 詳細確認
4. Promote 候補 → A3-simple register task (lot=0.1 Shadow 段階での monitoring 設計)
