---
date: 2026-05-03
task: 20260503-1815-r2-strategy-instrument-counterfactual
verdict: ACCEPT (Codex deliverable) / REJECT (Gate 0 救済 — Tier 1 LIVE が真犯人 H4 confirmed)
rule: R2
gate: Gate 0 (生存) / **月利100% ロードマップ根幹再評価**
---

# R2 Strategy × Instrument Counterfactual — REJECT (Tier 1 LIVE H4 confirmed)

## Verdict (Codex deliverable)

**ACCEPT** — 6 drag 戦略 × 4 instrument = 20 cell の greedy worst-first counterfactual を data-driven に実行。Bonferroni m=20, α'=0.0025。

## Verdict (Gate 0 救済)

**REJECT** — H4 確認: Tier 1 LIVE 戦略が aggregate Kelly 真犯人。

## Counterfactual Quant

| 状況 | raw Kelly | MC60d | N | EV | PF |
|---|---:|---:|---:|---:|---:|
| Baseline | -0.1737 | 100.00% | 917 | -0.79 | 0.695 |
| **Greedy 14-cell STOP** | **-0.1932 ⬇️** | 97.20% | 363 | -1.21 | 0.663 |
| All 20-cell STOP | -0.2536 ⬇️⬇️ | 99.40% | 317 | -1.50 | 0.589 |

Greedy STOP set:
1. sr_fib_confluence × USD_JPY
2. bb_rsi_reversion × EUR_USD
3. sr_channel_reversal × USD_JPY
4. macdh_reversal × EUR_USD
5. fib_reversal × EUR_USD
6. macdh_reversal × USD_JPY
7. fib_reversal × USD_JPY
8. bb_rsi_reversion × USD_JPY
9. vol_surge_detector × USD_JPY
10. sr_fib_confluence × GBP_JPY
11. sr_fib_confluence × EUR_JPY
12. sr_channel_reversal × EUR_USD
13. vol_surge_detector × GBP_USD
14. sr_fib_confluence × EUR_GBP

Bonferroni-significant positive keep: **0** — 6戦略には統計的有意 edge ゼロ。

## H4 confirmed — Tier 1 LIVE が真犯人

`gate-progression-audit-2026-05-03.md` strategy table:

| Tier 1 戦略 (ELITE_LIVE) | N | WR | Wilson_lo | EV | 過去 BT EV |
|---|---:|---:|---:|---:|---:|
| session_time_bias | 9 | 22.22% | 6.32% | **-4.82** | +0.215〜+0.580 |
| trendline_sweep | 6 | 33.33% | 9.68% | **-5.62** | +0.599〜+0.927 |
| gbp_deep_pullback | 3 | 66.67% | 20.77% | -4.43 | +1.064 |

**過去 BT +0.6〜+1.0 EV → Live -4〜-5 EV** の壊滅的乖離。

仮説:
- **構造的 BT-Live divergence** (memory `feedback_ma_filter_breaks_mr` / `feedback_hmm_gate_same_trap` 同類)
- **摩擦モデル誤差** (Spread/SL gate / QH 等が BT 想定より厳しい)
- **regime shift** (2026-04 cutoff 後の市場環境変化、過去 BT 期間と異質)
- **cohort time issue** (memory `feedback_cohort_time_check` — 過去 N で測定したのが現状と違う期間)

## Roadmap impact — 月利100% ロードマップ根幹再評価

ロードマップ v2.1 の前提:
- ELITE_LIVE 3戦略 (gbp_deep_pullback / trendline_sweep / session_time_bias) で年間+433pip → 月利寄与の幹

これが Live で **逆方向に -EV** で発火 → 月利100% 達成経路の前提崩壊。

選択肢:
1. **Tier 1 LIVE 全停止** + 全 Shadow 化、N が積み上がるまで観察
2. **構造的 divergence の RCA** (摩擦モデル誤差・regime・cohort) を特定、修正
3. **lot 大幅縮小** (defensive 0.05x → 0.02x) で時間稼ぎ
4. **portfolio 抜本見直し** (Tier 構造再設計、新しい Tier 1 候補発掘)

## Risks

- Codex sandbox DNS 失敗で Render mirror snapshot (2026-05-03 17:26) を使用 → 最新 Live でない可能性
- raw Kelly 悪化は Tier 1 LIVE 寄与だけでなく、N 減少での母数効果も含む可能性

## Next task

**`tier1-live-rca-bt-vs-live-divergence-2026-05-03`** — Tier 1 LIVE 3戦略の Live 実測 vs 過去 BT の divergence RCA。
- 摩擦モデル誤差 (実 spread / 実 slippage vs BT 仮定)
- regime cohort (Live 期間の VIX/DXY/ATR を BT 期間と比較)
- gate chain 効果 (post-gate-chain BT EV vs Live actual)
- promote 前 BT の N 信頼性 (Live N は十分か)

memory `feedback_label_empirical_audit` の規律遵守 — コード演繹ではなく Live trades の実測 query で root cause を特定する。
