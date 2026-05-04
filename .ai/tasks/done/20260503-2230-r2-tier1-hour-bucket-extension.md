---
id: 20260503-2230-r2-tier1-hour-bucket-extension
title: R2 拡張 — Tier 1 LIVE + hour-bucket overlay で raw Kelly -0.003 → ≥ 0 達成 (Gate 0 ACCEPT)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T22:30:00+0900
roadmap_gate: Gate 0 ACCEPT (R2 TRUE_LIVE 14-cell base + 拡張 demote で raw Kelly ≥ 0 達成)
rule: R2
prerequisite_decision: 2026-05-03-2058-r2-true-live-gate0-rescue-path-discovered (NEEDS_MORE_EVIDENCE, +0.003 不足)
prerequisite_audit: 20260503-1815-r2-strategy-instrument-counterfactual (TRUE_LIVE re-run, 14-cell demote set 確定)
---

## 0. なぜ今このタスクか

R2 strategy × instrument TRUE_LIVE 再起動版 (`r2-strategy-instrument-counterfactual-2026-05-03.md`) で **Gate 0 救済経路を初めて発見**:

| 指標 | Baseline (TRUE_LIVE N=371) | 14-cell STOP 後 | Δ |
|---|---:|---:|---:|
| MC60d 破産 | 86.50% | **0.90%** 🎯 | -85.60pp |
| raw Kelly | -0.1326 | **-0.0028** | +0.1298 |
| PnL | -254.6p | -3.1p | +251.5p |

**raw Kelly あと +0.003 で ACCEPT 確定**。MC60d=0.9% は完全生存圏。残るは Kelly を 0+ に押し込む拡張のみ。

R2 TRUE_LIVE が **strategy × instrument 単位** で 14 cell を STOP した後の N=172 の中に、まだ負 EV cell が残存している。Tier 1 LIVE の小 N cell (`session_time_bias × GBP_USD` ELITE_FLAG N=7 など) と **hour-bucket overlay** (時間帯別の負 EV pocket) を加味して **追加 demote set** を特定する。

## 1. 仮説

**H1**: 既存 14-cell demote (TRUE_LIVE strategy × instrument level) に **追加 demote dimension** を加えれば raw Kelly ≥ 0 を達成できる。候補:
- (a) Tier 1 LIVE bleeding cell の追加 STOP (`session_time_bias × GBP_USD`, `gbp_deep_pullback × GBP_USD` ELITE_FLAG)
- (b) hour-bucket overlay (例: `bb_rsi_reversion × USD_JPY × 16:00 UTC` のような時間帯 cell)
- (c) (a) + (b) の組合せ

**H2**: H1 で raw Kelly ≥ 0 達成すると同時に MC60d ≤ 90% が維持される (前回 0.90% → 拡張で 0-2% 程度に維持されるはず)。

**H3 (反証)**: 全候補の追加 demote でも raw Kelly < 0 のまま → portfolio 構造的に Live 負 EV が支配的、月利100% ロードマップ前提崩壊確定 → portfolio 抜本見直し必要。

## 2. 対象データ / 分離

| 用途 | 出典 | 混入禁止 |
|---|---|---|
| TRUE_LIVE bucket | `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status='CLOSED' AND outcome IN ('WIN','LOSS','BREAKEVEN') AND pnl_pips IS NOT NULL AND instrument NOT IN ('XAU_USD','EUR_GBP') AND entry_time >= '2026-04-08'` (前回 R2 と完全一致) | FLAG_DRIFT N=140 / SHADOW N=3819 / XAU |
| 既存 14-cell demote | 前回 R2 出力 `r2-strategy-instrument-counterfactual-2026-05-03.md` の Min demote set | 前回 SSOT protected keep cells (`fib_reversal × USD_JPY/EUR_USD` 等) |
| 追加候補 | (a) Tier 1 LIVE 全 cell 列挙 / (b) hour-bucket × strategy × instrument 3次元 cell 列挙 | hardcode demote 候補 |
| Counterfactual MC | iterations=1000, horizon=60d, ruin_dd=50% of 1000p, bootstrap=PnL分布 | hardcode 改善目標 |

## 3. 統計条件

- 追加 cell 候補は N≥3 (R2 Fast & Reactive は小 N 許容)
- Bonferroni 補正: 追加 cell 候補数 m_add に対し α'_add = 0.05/m_add (greedy worst-first)
- Bonferroni-significant **positive** edge cell (one-sided binomial p < α/m, WR > BEV) は **keep** (memory `feedback_ma_filter_breaks_mr` 罠回避)
- hour-bucket は UTC 整数時 (0-23)

## 4. ACCEPT / REJECT / NEEDS_MORE 条件

- **ACCEPT**: 既存 14-cell + 追加 demote N+ で raw Kelly ≥ 0 AND MC60d ≤ 90% AND Bonferroni-significant cell は keep されている
- **NEEDS_MORE_EVIDENCE**: raw Kelly が 0 まで届かないが +0.0 の閾値内で踏みとどまる (-0.001 ≤ Kelly < 0)
- **REJECT (H3 confirmed)**: Tier 1 + hour-bucket × 全候補 demote でも raw Kelly < -0.001 のまま → portfolio 抜本見直し task へ移行

## 5. Scope

Codex MAY change:

- `tools/r2_tier1_hour_bucket_extension.py` (new) — 既存 R2 cell + Tier 1 + hour-bucket overlay の greedy worst-first counterfactual
- `tests/test_r2_tier1_hour_bucket_extension.py` (new)
- `knowledge-base/wiki/decisions/r2-tier1-hour-bucket-extension-2026-05-03.md` (new) — 拡張 demote LOCK list + verdict
- `.ai/runs/<run-dir>/final.md`

Codex MAY NOT change:

- `app.py` (実装は別タスク、本タスクは LOCK proposal のみ)
- `modules/`, `strategies/`
- `tools/r2_strategy_instrument_counterfactual.py` (前タスク成果物、参照のみ)
- `tools/gate_progression_audit.py`, `tools/r2_cell_demotion_audit.py` (helpers 再利用のみ)
- `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (前タスク decision、immutable)
- `.env`, OANDA secrets, production credentials, `live_ng_cells` SQLite
- 既存未コミット変更

## 6. Required Reading

- `CLAUDE.md` (Rule 2 Fast & Reactive, クオンツ判断)
- `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (前 R2 TRUE_LIVE 結果)
- `.ai/decisions/2026-05-03-2058-r2-true-live-gate0-rescue-path-discovered.md` (Claude review)
- `wiki/decisions/gate-progression-audit-2026-05-03.md` (Live aggregate baseline)
- `wiki/lessons/index.md` の `feedback_ma_filter_breaks_mr`, `feedback_partial_quant_trap`, `feedback_label_empirical_audit`, `feedback_live_shadow_separation`, `feedback_success_until_achieved`
- `tools/r2_strategy_instrument_counterfactual.py` (helpers + greedy logic 再利用)
- `tools/gate_progression_audit.py` (Wilson/Bonferroni helpers)
- `tools/r2_cell_demotion_audit.py` (cell-level helpers)

## 7. Acceptance Criteria

- [ ] `tools/r2_tier1_hour_bucket_extension.py --dry-run` で TRUE_LIVE bucket 確認 (N=371 一致), 既存 14-cell demote 列挙, 追加候補列挙
- [ ] `pytest tests/test_r2_tier1_hour_bucket_extension.py` pass
- [ ] `wiki/decisions/r2-tier1-hour-bucket-extension-2026-05-03.md` に: Bonferroni m_add 値 / Bonferroni-significant keep cell 印 / 追加 demote LOCK list / verdict / aggregate post-extension Kelly/MC60d
- [ ] verdict は `ACCEPT / NEEDS_MORE_EVIDENCE / REJECT` のいずれか deterministic
- [ ] `.ai/runs/<run-dir>/final.md` に: 最小拡張 demote set, aggregate post-extension Kelly 改善幅, MC60d 改善幅, 次タスク (PR 起草 or H3 portfolio 見直し)
- [ ] `app.py`/`modules/`/`strategies/` 編集 0件

## 8. Verification Commands

```bash
# 1. Dry-run
python3 tools/r2_tier1_hour_bucket_extension.py --dry-run

# 2. Tests
python3 -m pytest -q tests/test_r2_tier1_hour_bucket_extension.py

# 3. Production run (parent Claude DNS可なら curl 後に実行)
curl -s 'https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000' -o /tmp/live-trades-r2-ext.json
python3 tools/r2_tier1_hour_bucket_extension.py \
  --trades /tmp/live-trades-r2-ext.json \
  --base-demote-set knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md \
  --output knowledge-base/wiki/decisions/r2-tier1-hour-bucket-extension-2026-05-03.md \
  --mc-iterations 1000 --mc-horizon 60

# 4. Verdict 確認
grep -E "^Verdict:|^Aggregate post-extension|^Min extension demote set|^Bonferroni" knowledge-base/wiki/decisions/r2-tier1-hour-bucket-extension-2026-05-03.md
```

## 9. Codex Instructions

これは **Rule 2 (Fast & Reactive)** タスク、365日 BT 不要、Bonferroni 補正は α/m_add で適用。

**重要**: 前 R2 SSOT protected keep cells (`fib_reversal × USD_JPY`, `fib_reversal × EUR_USD`, 他 Bonferroni-significant positive Live cells) は **絶対に** 拡張 demote 対象外。memory `feedback_ma_filter_breaks_mr` 罠回避。

`feedback_success_until_achieved` 通り、verdict が ACCEPT 未満で closure 短絡禁止。NEEDS_MORE_EVIDENCE なら HOUR_BUCKET 単位を細分化提案、REJECT (H3) なら **portfolio 抜本見直し task** を提案。

PR 作成は本タスクで実行しない。proposal doc 生成のみ。実装は Claude review 後の別 task で。

最終レポートには status, files changed, verdict, 既存 14-cell + 追加 cell の合算 demote set, aggregate post-extension Kelly/MC60d/EV/PF/N, residual risks, 次タスクを含む。

ACCEPT verdict 達成後の次タスク:
- **`a3-r2-demote-pr-2026-05-03`** — `app.py` `FORCE_DEMOTED_CELLS` 編集 PR 起草、Claude review 後 merge
- 並行: **`a3-simple-sr-channel-reversal-shadow-register-2026-05-03`** — A2-alt の sr_channel_reversal Promote 候補を Gate 0 ACCEPT 確認後に lot=0.1 SHADOW で register

REJECT (H3) verdict なら:
- **`portfolio-restructure-deep-rca-2026-05-03`** — Tier 構造再設計、月利100% ロードマップ v3 起草
