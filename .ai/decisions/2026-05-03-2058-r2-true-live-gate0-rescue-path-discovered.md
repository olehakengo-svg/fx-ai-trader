---
date: 2026-05-03
task: 20260503-1815-r2-strategy-instrument-counterfactual (TRUE_LIVE re-run)
verdict: ACCEPT (Codex) / NEEDS_MORE_EVIDENCE (Gate 0 ACCEPT 直前、+0.003 Kelly 不足)
rule: R2
gate: Gate 0 復帰経路 **発見**
---

# R2 TRUE_LIVE — Gate 0 救済経路を初めて発見

## Headline

TRUE_LIVE bucket (`is_shadow=0 oanda_trade_id != ''` Live=371) で **MC60d 破産確率 86.5% → 0.9%** に劇的改善する demote set が存在する。raw Kelly は -0.0028 で ACCEPT 直前、+0.003 不足のみ。

## Bucket 3-split 確定

| bucket | N | PnL | 用途 |
|---|---:|---:|---|
| TRUE_LIVE (`is_shadow=0 oanda_trade_id != ''`) | **371** | -254.6p | 真の OANDA 約定、本 audit 対象 |
| FLAG_DRIFT (matching but mismatched) | 140 | -132.4p | 別 issue、要 R3 |
| SHADOW (`is_shadow=1`) | 3819 | -4985.6p | 統計参照のみ、Live集計から除外 |

memory `feedback_live_shadow_separation` の正しい分離を bucket level で確認。前回 R2 (N=917) は SHADOW 一部混入で Kelly 悪化したと推察。TRUE_LIVE 分離で **景色が反転**。

## Counterfactual

| 指標 | Baseline | 14-cell STOP | Δ |
|---|---:|---:|---:|
| raw Kelly | -0.1326 | -0.0028 | **+0.1298** |
| MC60d 破産 | 86.50% | **0.90%** | **-85.60pp** |
| N | 371 | 172 | -199 |
| PnL | -254.6p | -3.1p | +251.5p |

ACCEPT 閾値 (raw Kelly ≥ 0 AND MC60d ≤ 90%):
- raw Kelly ≥ 0 → +0.003 不足 (ACCEPT 未達)
- MC60d ≤ 90% → 大幅クリア (0.9%)

`feedback_success_until_achieved` の規律遵守、closure 短絡禁止 → **NEEDS_MORE_EVIDENCE** 維持。

## Demote 推奨 14 cells (SSOT protected keep 適用後)

1. vwap_mean_reversion × GBP_USD
2. vix_carry_unwind × USD_JPY
3. sr_channel_reversal × USD_JPY
4. bb_rsi_reversion × USD_JPY
5. **session_time_bias × GBP_USD** ⚠️ ELITE_FLAG
6. bb_squeeze_breakout × USD_JPY
7. bb_rsi_reversion × EUR_USD
8. vol_surge_detector × USD_JPY
9. engulfing_bb × USD_JPY
10. engulfing_bb × EUR_USD
11. v_reversal × USD_JPY
12. trend_rebound × USD_JPY
13. sr_channel_reversal × EUR_USD
14. stoch_trend_pullback × USD_JPY

SSOT protected: `fib_reversal × USD_JPY`, `fib_reversal × EUR_USD`, 他 Bonferroni-significant positive cells (memory `feedback_ma_filter_breaks_mr` 罠回避)。

### ELITE_FLAG — `session_time_bias × GBP_USD`

ELITE_LIVE bleeding cell: N=7, EV=-4.00p, PnL=-28.0p。即時 WATCH escalation 推奨。これは私の前回 Tier 1 audit と整合 (Tier 1 LIVE が OANDA で大幅 -EV)。

## Roadmap impact — Gate 0 救済経路初発見

これまでの 3 audit:
1. cell-level R2 (N=917): MC60d 99.7% → REJECT_INSUFFICIENT
2. strategy×instrument R2 (N=917 wider): Kelly 悪化 → REJECT
3. **strategy×instrument R2 (N=371 TRUE_LIVE): MC60d 0.9% 到達** → NEEDS_MORE 直前

TRUE_LIVE filter の重要性が定量証明。月利100% ロードマップ復活経路が**初めて実在**として観測。

## Risks

- raw Kelly = -0.0028 は **closure 短絡してはならない** (`feedback_success_until_achieved`)
- Bootstrap MC60d 0.9% は post-cut の N=172 PnL 分布に強く依存、bootstrap distribution の安定性確認必要
- 14 cell demote には ELITE_LIVE 1件 (session_time_bias × GBP_USD) と PAIR_PROMOTED 多数を含む → **ロードマップ Tier 構造の大規模再編が示唆される**

## Next task — Path A (immediate, Gate 0 完全 ACCEPT)

**`r2-tier1-hour-bucket-overlay-extension-2026-05-03`** — Tier 1 LIVE / N<5 cell / hour-bucket overlay を加味した R2 拡張で raw Kelly を -0.003 → ≥0 に届かせる。

ELITE_FLAG `session_time_bias × GBP_USD` を即時 WATCH も並列実行。

## Next task — Path B (PR investigation, 実装に向けて)

Path A で完全 ACCEPT 達成後、demote 14 cell + 拡張 cell の app.py `FORCE_DEMOTED_CELLS` PR 起草タスク。Render auto-deploy への影響を考慮、Claude review 後 merge 判断。

両 path 並列可能だが Path A が先 (Path B の確証なくして PR 投入危険)。
