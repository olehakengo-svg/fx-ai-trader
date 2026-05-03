---
id: 20260503-1525-a2-scalp-re-enable-pre-registration
title: A2 — Scalp re-enable pre-registration with mtf_regime_trend_cascade_scalp QUALIFIED_TYPES decision (Rule 1)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T15:25:00+0900
roadmap_gate: Gate 1 (Scalp 枝 N-acceleration)
rule: R1
---

# Objective

Produce a pre-registration document with verdict (Promote / Shadow / Reject) for re-enabling Scalp 枝 trading via the `mtf_regime_trend_cascade_scalp` strategy. The verdict must be backed by a 180-day BT (Codex run + cross-check against `modules/bt_vec_harness`) with full quant rigor: N, WR, EV, PF, Wilson 95% CI, Walk-Forward stability ≥ 2 folds, max DD, Bonferroni-corrected significance against the scalp candidate pool. Output is the LOCKED pre-registration markdown plus the BT evidence — **not** any code change to `app.py` `QUALIFIED_TYPES`. Registration happens only after Claude reviews the LOCKED pre-reg.

# Context

- Aggregate Kelly = 0 with Live N=29, edge=-20pp, Wilson CI [31.4%, 65.6%] — surgical demote impossible (`wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md`).
- B audit (`raw/audits/oanda-passthrough-gap-2026-05-03.md`) verdict `FLAG_DRIFT_BUG`: gates are working correctly, no structural blocker. **N-acceleration is the only Gate 1 unlock path**.
- A1 unblocked the BT validation path (loader parquet fallback works, USD_JPY 5m loads 36,060 bars from cache_ts=2026-04-15).
- `mtf_regime_trend_cascade_scalp` is currently absent from `app.py:5537` `QUALIFIED_TYPES` (run_scalp_backtest gate). This is the binding gate that prevented the 1117 BT validation from getting N>0.
- Scalp 枝 in roadmap-v2.1 estimates +200 pip/year if N accumulates. ELITE_LIVE three strategies (gbp_deep_pullback, session_time_bias, trendline_sweep) are in shadow due to insufficient N — not because they don't work. Re-enabling Scalp accelerates portfolio N at constant risk.
- Memory `feedback_ma_filter_breaks_mr` and `feedback_hmm_gate_same_trap` warn that conventional gates (MA, HMM) have repeatedly destroyed MR edge in BT vs. Live. Pre-reg LOCK must therefore use BT only as a sanity check, with Live as the source of truth for promotion.
- Memory `feedback_partial_quant_trap`: N/WR/EV alone insufficient. **PF/Wilson CI/WF/Bonferroni/Kelly all required**.
- Memory `feedback_success_until_achieved`: Null/Scenario A での closure 短絡禁止。If BT verdict is Reject, must explicitly enumerate alternative Scalp candidates from the pool (`bb_squeeze_breakout`, `engulfing_bb`, `fib_reversal`, `sr_channel_reversal` per roadmap-v2.1 Scalp枝 table).

# Scope

Codex may change:

- `knowledge-base/wiki/learning/scalp-re-enable-pre-registration-2026-05-03.md` — the LOCKED pre-registration document. Format follows `wiki/learning/s2-turtle-verdict-pre-registration-2026-05-03.md`.
- `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.json` — BT raw result.
- `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md` — BT readable summary with all quant fields.
- `tools/scalp_re_enable_bt.py` — thin wrapper that calls `run_scalp_backtest` AND `bt_vec_harness` for the same window/strategy/pair, reports both, and computes the Wilson/Bonferroni/WF stats. Reuse — do not duplicate — anything from `tools/aggregate_kelly_decomposition_audit.py`.
- `.ai/runs/<new-run-dir>/final.md` — run report.

Codex may NOT change:

- `app.py` `QUALIFIED_TYPES` — the registration decision is recorded in the pre-reg doc and EXECUTED in a separate task only after Claude review.
- Any module under `modules/oanda_*`, `modules/demo_trader.py`.
- Any strategy file under `strategies/`.
- Render API, production credentials, `.env`, production DB.
- `knowledge-base/wiki/decisions/`, `wiki/index.md`, `wiki/strategies/` — these are Claude's territory after pre-reg LOCK.
- `live_ng_cells` SQLite table.
- Existing uncommitted changes (see Codex Instructions).

# Required Reading

- `CLAUDE.md` (especially クオンツ判断, Rule 1 Slow & Strict, KB read rules)
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md` (Scalp 枝 section + lot 配分ルール)
- `knowledge-base/wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md`
- `knowledge-base/raw/audits/oanda-passthrough-gap-2026-05-03.md` (B verdict)
- `knowledge-base/wiki/lessons/index.md` — at minimum:
  - "feedback_ma_filter_breaks_mr — MAトレンドフィルタは MR を破壊"
  - "feedback_hmm_gate_same_trap — HMM gate も MA filter と同じ罠"
  - "feedback_partial_quant_trap — 部分的クオンツの罠"
  - "feedback_success_until_achieved — 成功するまでやる"
- `knowledge-base/wiki/learning/s2-turtle-verdict-pre-registration-2026-05-03.md` (format precedent)
- `app.py:5338` (run_scalp_backtest), `app.py:5537` (QUALIFIED_TYPES), `app.py` (`_compute_bt_htf_bias` definition)
- `modules/bt_vec_harness.py` (oracle for cross-check)
- `tools/aggregate_kelly_decomposition_audit.py` (Wilson/Bonferroni helpers — reuse)

# Decision Procedure (Rule 1 Slow & Strict)

## Step 1: BT execution

Run BT on:

- Strategy: `mtf_regime_trend_cascade_scalp`
- Pair: USD_JPY
- Window: 180 days, 5m interval (the cache supports this)
- Exclude: pre-cutoff 2026-04-08 trades from the live-comparable subset (BT can use full window for stats, but report Live-comparable subset separately)

For BT execution, use a temporary local-only `QUALIFIED_TYPES` patch that includes `mtf_regime_trend_cascade_scalp` so `run_scalp_backtest` returns trades for this strategy. **The patch must be local to the BT script — do NOT modify `app.py` itself**. Use one of:

(a) Monkey-patch `app.QUALIFIED_TYPES` in the wrapper (preferred — leaves `app.py` untouched).
(b) Pass an override set via a kwarg if `run_scalp_backtest` supports it (check signature first).
(c) If neither is feasible, document the obstacle and fall back to `bt_vec_harness` exclusively. Report this clearly.

## Step 2: Required quant fields (all must appear in the BT report)

| Field | Required | Validation |
|---|---|---|
| N (total trades) | ✅ | N must be reported, even if N<30 (then verdict cannot be Promote) |
| Wins / Losses | ✅ | Sanity check WR computation |
| WR | ✅ | — |
| EV pip/trade | ✅ | — |
| PF | ✅ | profit_factor = sum(positive PnL) / abs(sum(negative PnL)) |
| Wilson 95% lo / hi | ✅ | reuse `wilson_lower` / `wilson_upper_at` from `tools/cell_edge_audit.py` |
| max DD (pip) | ✅ | required for verdict; cap-rule from S2 Turtle pre-reg |
| Walk-Forward (≥2 folds) | ✅ | split window 50/50 (IS/OOS); report PF_IS, PF_OOS, WR_IS, WR_OOS |
| Bonferroni adjusted p (one-sided WR > BEV_WR) | ✅ | α=0.05 / m=K where K is the number of scalp candidate strategies in roadmap-v2.1 (count and document) |
| BEV_WR (USD_JPY) | ✅ | 34.4% per `wiki/analyses/friction-analysis.md` |
| half-Kelly | ✅ | reuse `modules.stats_utils.kelly_criterion` |
| BT vs vec_harness consistency | ✅ | both N values must match within ±5%; if not, document and use vec_harness as oracle |

## Step 3: Verdict thresholds (PRE-REGISTERED before seeing BT output)

The wrapper must encode these thresholds as constants and emit the verdict deterministically:

| Verdict | All conditions must hold |
|---|---|
| **Promote (LIVE register)** | N≥30, PF≥1.30, Wilson_lo > BEV_WR + 5pp, WF: PF_IS≥1.20 AND PF_OOS≥1.20, Bonferroni p < α/K, max DD ≤ 30% |
| **Shadow (register but lot=0.1)** | N≥30, PF≥1.10, Wilson_lo > BEV_WR + 0pp, WF: PF_IS≥1.00 AND PF_OOS≥1.00, max DD ≤ 30% |
| **Reject** | any other configuration |
| **Insufficient** | N<30 (defer decision; report N gap and recommended cache-extension) |

## Step 4: If verdict ≠ Promote, evaluate alternative Scalp candidates

Per `feedback_success_until_achieved`, do not close on Reject without enumerating alternatives. Run abbreviated BT (same metrics, no LOCK) on:

- `bb_squeeze_breakout` USD_JPY 5m (BT EV +1.030 from roadmap-v2.1)
- `engulfing_bb` USD_JPY 5m (BT EV +0.677 from roadmap-v2.1)
- `fib_reversal` EUR_USD 1m (BT EV +0.426 from roadmap-v2.1)

Report which (if any) meet Promote/Shadow thresholds. Do NOT pre-register alternatives in this task; just identify the next pre-reg candidate.

# Acceptance Criteria

- [ ] `knowledge-base/wiki/learning/scalp-re-enable-pre-registration-2026-05-03.md` exists with sections: Strategy, Pre-registered thresholds, BT evidence (all 12 quant fields), Walk-Forward summary, Bonferroni K-value justification, Verdict, Lock statement, Live N target, stopping criteria.
- [ ] `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.{json,md}` exist.
- [ ] `tools/scalp_re_enable_bt.py` is deterministic on the parquet cache; verdict is computed from the constants, not hand-written.
- [ ] `python3 tools/scalp_re_enable_bt.py --dry-run` prints the pre-registered thresholds and exits 0 only when the wrapper is fully wired.
- [ ] `python3 tools/scalp_re_enable_bt.py --pair USD_JPY --strategy mtf_regime_trend_cascade_scalp --interval 5m --lookback 180` writes the three artifacts above.
- [ ] If verdict is Reject/Insufficient, the alternative-candidate scan section in the pre-reg doc is filled with at least one candidate's metrics.
- [ ] No edits under `app.py`, `modules/`, `strategies/`, `knowledge-base/wiki/decisions/`, `knowledge-base/wiki/index.md`, `knowledge-base/wiki/strategies/`.
- [ ] Run report under `.ai/runs/` includes status, files changed, verdict, top quant numbers (N/PF/Wilson_lo/WF), Bonferroni K and p-value, max DD, recommended next task.

# Verification Commands

```bash
# 1. Dry-run prints the LOCKED thresholds
python3 tools/scalp_re_enable_bt.py --dry-run

# 2. Full BT for primary candidate
python3 tools/scalp_re_enable_bt.py \
  --pair USD_JPY --strategy mtf_regime_trend_cascade_scalp \
  --interval 5m --lookback 180 \
  --output knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md

# 3. If primary verdict ≠ Promote, abbreviated BT on alternatives
python3 tools/scalp_re_enable_bt.py \
  --pair USD_JPY --strategy bb_squeeze_breakout \
  --interval 5m --lookback 180 \
  --abbreviated

# 4. Cross-check vec_harness consistency
python3 -c "
from modules.bt_vec_harness import run_vec_harness
out = run_vec_harness('USD_JPY', '5m', lookback_days=180,
                      strategies=['mtf_regime_trend_cascade_scalp'])
print(out)
"

# 5. File presence
test -s knowledge-base/wiki/learning/scalp-re-enable-pre-registration-2026-05-03.md
test -s knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md
```

# Codex Instructions

Work in this repository. Respect existing uncommitted changes — do not touch `modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, or `knowledge-base/raw/cell_deepdive/`. The new tools `tools/render_trades_snapshot.py`, `tools/aggregate_kelly_decomposition_audit.py`, `tools/oanda_passthrough_gap_audit.py`, `tools/dedup_violation_triage.py`, `tools/h1_hour_bucket_counterfactual.py` are read-only context.

This is a Rule 1 task. The verdict thresholds in Step 3 are PRE-REGISTERED — they must be encoded as constants in `tools/scalp_re_enable_bt.py` BEFORE running BT, and the BT result must not modify them. Walk-Forward fold split (50/50 IS/OOS) is also pre-registered.

Do not:

- modify `app.py` `QUALIFIED_TYPES` directly
- modify any strategy file
- skip Bonferroni correction or claim K=1 without justification
- close on Reject without enumerating at least one alternative candidate
- soften the verdict thresholds based on observed BT numbers

If parquet cache for the strategy/pair/TF combination is missing, document precisely what data is needed and exit `Insufficient`. Do not fabricate.

If `bt_vec_harness` and `run_scalp_backtest` disagree by >5% in N, treat `bt_vec_harness` as oracle and document the discrepancy as a finding (likely a sign that the M15/M5 cache fix from A1 has a behavior gap, which would itself be a separate diagnostic task).

In the final report, include status, files changed, the verdict, the 12 quant fields summary, Bonferroni K with derivation, max DD, the alternative-candidate scan summary if applicable, remaining risks, and the next recommended task. The next task after Promote verdict is **A3 — execute QUALIFIED_TYPES registration with PR review**; after Shadow it's **A3-shadow — register at lot=0.1 with monitoring task**; after Reject/Insufficient it's **A2-alt — pre-reg the next candidate**.
