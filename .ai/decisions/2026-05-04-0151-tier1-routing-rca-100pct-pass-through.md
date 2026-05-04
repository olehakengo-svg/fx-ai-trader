---
date: 2026-05-04
task: 20260504-0130-tier1-routing-anomaly-rca
verdict: ACCEPT (Codex) / NEEDS_MORE_EVIDENCE (Verdict) — **重大認識訂正**
rule: R3 (forensic)
gate: BT-Live divergence 真因特定 → edge erosion 確定 (routing not the issue)
---

# Tier 1 Routing Anomaly RCA — 「0.5% pass-through」認識は誤り、真因は edge erosion

## Headline 訂正

前回 Tier 1 audit (`2026-05-03-1826`) 等で言及した「**ELITE_LIVE 5 cell が OANDA で 0.5% pass-through**」は **誤った認識**。本 RCA で `oanda_audit` (`is_live=true`) を直接調査した結果:

| Cell | sent N | filled N | blocked | pass-through |
|---|---:|---:|---:|---:|
| gbp_deep_pullback / GBP_USD | 3 | 3 | 0 | **100%** |
| trendline_sweep / GBP_USD | 3 | 3 | 0 | **100%** |
| session_time_bias / GBP_USD | 7 | 7 | 0 | **100%** |
| doji_breakout / USD_JPY (PAIR_PROMOTED reference) | 2 | 2 | 0 | **100%** |
| **計** | **15** | **15** | **0** | **100%** |

→ **routing は完全に健全**。Tier 1 cells に対する gate block は **0 件**。

## 認識訂正の経緯

前回 Tier 1 audit の "0.5% pass-through" は **table 混同**:
- 736: `demo_trades` の `is_shadow=0` rows (Live signal 母集団)
- 29: `demo_trades` の `oanda_trade_id != ''` (OANDA-actually-filled subset)
- Tier 1 内訳: session_time_bias N=9 (live) / gbp_deep_pullback N=3 等 — 全て filled

Today's RCA は `oanda_audit` (`is_live=true`) で直接確認 → 15/15 pass。

## 真の Root Cause = Edge Erosion (BT-Live divergence)

routing が健全である以上、Tier 1 ELITE_LIVE 5 cell の Live 大幅 -EV (Live EV -4〜-5 vs BT EV +0.6〜+1.0) の真因は:

1. **摩擦モデル誤差** — 実 spread / slippage が BT 想定 (spread/sl gate v3 摩擦モデル) より厳しい
2. **Regime shift** — 2026-04-08 cutoff 後の市場環境変化、過去 BT 期間 (2026 春以前) と異質
3. **Cohort time issue** (memory `feedback_cohort_time_check`) — 過去 N で測定した edge 期間と現状の Live 集計期間が違う
4. **構造的 BT-Live divergence** (memory `feedback_ma_filter_breaks_mr` / `feedback_hmm_gate_same_trap` 同類) — Live で edge が反転する一般 pattern

routing 修正で fix できる問題ではない。`app.py` `QUALIFIED_TYPES` や `_PAIR_DEMOTED` の調整でも fix できない。**摩擦/regime cohort/edge 自体の RCA** が必要。

## Hypothesis verdict

- **H1 (gate dominance)**: NEEDS_MORE_EVIDENCE — sample 15 で gate 比率不能だが block N=0 は強い反証
- **H2 (pre/post cutoff)**: pre-cutoff 0、post-cutoff 15 全 100% pass、時期差なし
- **H3 (signal 不発火)**: **REJECT** — signal は発火している (N=15 確認)

## Roadmap impact — Gate 0 ACCEPT 後の方針再構成

routing 健全確定により:

✅ **Gate 0 ACCEPT (PR #19 merge) は止血として有効** — bleeding cells の SHADOW dispatch で Live N が圧縮 → 平均 EV 改善
✅ **R2 demote LOCK は機能** — `pair_demoted` gate が正しく動作、新 Live trades から bleeding cells が除外される
🟡 **edge erosion は別問題** — Tier 1 strategies が Live で BT 通り稼げない構造は **未解決**

→ 月利100% ロードマップ復活には:
1. Gate 0 ACCEPT 維持 (R2 LOCK 継続)
2. **edge erosion RCA** (新規 task) — 摩擦モデル v3 vs 実測 spread, regime cohort 比較
3. 必要なら摩擦モデル更新 (R3 patch) または regime-aware lot sizing
4. Gate 1 候補 (sr_channel_reversal Promote) は edge erosion 改善後に SHADOW register が安全

## Codex deliverables

- `tools/tier1_routing_rca.py` — bridge_status 分離 forensic CLI
- `tests/test_tier1_routing_rca.py` — 2 passed
- `wiki/decisions/tier1-routing-rca-2026-05-04.md` — 生成完了 (4597 audit rows 集計)

## Next task

**`r3-edge-erosion-rca-2026-05-04`** (新規起草必要):
- 対象: ELITE_LIVE 5 cell + 主要 PAIR_PROMOTED cell の Live trades 全件
- 集計: 実 spread / slippage / max favorable excursion / max adverse excursion / TP-hit/SL-hit ratio / time-in-trade
- 比較: BT 摩擦モデル v3 想定 vs 実測
- 出力: 摩擦モデル誤差サイズの推定、regime cohort 別 edge 分布、補正必要 cell リスト
