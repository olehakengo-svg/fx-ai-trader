<!-- audits/edge_design/_TIER1_GATE.md -->
# Tier 1 Early-Stop Gate (spec §6) — 🚨 HALT TRIGGERED

**Decision:** **HALT — `THESIS_VALID_DESIGN_BROKEN` ≥ 3 件 (実測 3 件 / 8 LIVE 戦略中)**

Spec §6 stop condition 1 を満たすため、Tier 2-4 dispatch は user の明示承認まで停止。

## Audited (7/8) + dispatched (1/8 in flight: xs_momentum)

| # | Tier 1 Strategy | Pair(s) | Verdict | Recommendation |
|---|---|---|---|---|
| 1 | trendline_sweep | ALL (ELITE_LIVE) | THESIS_VALID_INSUFFICIENT_EVIDENCE | A |
| 2 | doji_breakout | GBP_USD, USD_JPY | **THESIS_VALID_DESIGN_BROKEN** | A |
| 3 | ema200_trend_reversal | USD_JPY | THESIS_VALID_INSUFFICIENT_EVIDENCE | A |
| 4 | squeeze_release_momentum | EUR_USD | THESIS_VALID_TIMING_BROKEN | A |
| 5 | streak_reversal | USD_JPY (INLINE app.py) | **THESIS_VALID_DESIGN_BROKEN** | A |
| 6 | vol_momentum_scalp | EUR_JPY | THESIS_VALID_TIMING_BROKEN | A |
| 7 | wick_imbalance_reversion | GBP_USD | **THESIS_VALID_DESIGN_BROKEN** | B |
| 8 | xs_momentum | EUR_USD, GBP_USD | (in flight) | — |

## Counts (7 audited + 1 in flight)

| Category | Count | Halt Threshold |
|---|---|---|
| THESIS_VALID_DESIGN_BROKEN | **3** | **≥ 3 → HALT** ✗ |
| THESIS_VALID_TIMING_BROKEN | 2 | — |
| THESIS_VALID_INSUFFICIENT_EVIDENCE | 2 | — |
| THESIS_INVALID | 0 | ≥ 30% → HALT |
| THESIS_VALID_DESIGN_VALID | **0** | — |

## Common failure pattern (across DESIGN_BROKEN cluster)

**HTF / trend filter applied to MR thesis** — same root cause as memory entries:
- `feedback_ma_filter_breaks_mr.md` (bb_rsi_reversion: H1 EMA200 整合追加で Kelly 0.43→0)
- `feedback_hmm_gate_same_trap.md` (HMM regime gate で USDJPY TF +478p→-4p)

streak_reversal (PF=3.07, Bonferroni p=1.3e-5, Kelly=0.487) と wick_imbalance_reversion
(WF folds=4 positive ratio=1.00) はどちらも HTF hard block で MR の tail event を
切り捨てている。**この修正だけで防御的 PnL 復活が見込める。**

doji_breakout は別軸で、breakout trigger が「Doji レンジ外 close」を要求していない
構造的トリガー誤り (Axis 2 MISMATCH)。

## Recommended user-facing actions (escalation request)

1. **防御 patch P0 候補（即適用検討）:**
   - streak_reversal daytrade variant の `_stk_htf_blocked` を hard reject → soft penalty
   - wick_imbalance_reversion の HTF Hard Block を hard reject → soft penalty
   - これらは memory MR-filter 失敗パターンの直接適用例

2. **Routing scope 縮小（即適用検討）:**
   - trendline_sweep `ALLOWED_PAIRS` を EUR_USD, GBP_USD に限定（pair-level evidence なし pair を shadow へ）

3. **Tier 2-4 進行可否判断:**
   - 即進行 (Wave 4 全体観点で他 tier の発見も必要) — 推奨
   - 一旦停止して LIVE 防御 patch を先に Wave 4 で実施 — 安全側
   - Tier 3 (FORCE_DEMOTED, 22 戦略) は「思想は正、設計が誤」仮説の本命検証群なので、
     早めに走らせた方が再設計 candidate を発見できる

**Gate Decision:** **HALT — Tier 2-4 待機中、user 判断要**
**Updated:** 2026-05-04
