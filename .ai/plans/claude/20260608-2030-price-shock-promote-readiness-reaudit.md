---
id: 20260608-2030-price-shock-promote-readiness-reaudit
priority: P1
gate: R1
rule: R1
status: queued
created: 2026-06-08
owner: claude
---

# Price-Shock Reversion — Shadow N 蓄積後の promote-readiness 再監査

**Rule classification**: R1 (Slow & Strict — Live lot-ramp 昇格判定の pre-reg 評価)
**Purpose**: Phase B-1 (commit 35961351 + activation fix 458392d8、2026-05-18) で Shadow 投入した 5 戦略が、約3週間の蓄積を経て promote gate に到達したかを実測評価する。当てに行く新規探索ではなく、**既に当てている脈を規律通りに育てる**作業。

## 背景

- 再現成功: AUDJPY H4 WR 60.00% / EUR_GBP H1 Wilson_lo 0.66 ([[project_price_shock_reproduction_success_2026_05_15]])
- Phase B-1: 5 戦略 Shadow 投入。`auto_start=False` で 0 件発火していた問題は 458392d8 で frozenset 強制 shadow 化 + ramp 修正済 ([[project_price_shock_phase_b1_done_2026_05_18]])
- **発火確認が前提**: 監査前にまず「2026-05-18 以降に実際に発火しているか」を確認すること。0 件なら promote 評価以前の問題として即報告。

## 対象 entry_type (m=5、Bonferroni 設計済)

```
price_shock_rev_aud_jpy_h
price_shock_rev_eur_aud_h
price_shock_rev_eur_gbp_h
price_shock_rev_nzd_jpy_h
price_shock_rev_usd_cad_h
```

## Gate (既存 evaluator の定数を変更しない)

`tools/price_shock_rev_promote_evaluator.py` の locked 定数:
- `WILSON_MIN = 0.50`
- `BONFERRONI_M = 5`, `BONFERRONI_ALPHA = 0.01`
- N>=30 (lot-ramp 提案の必要条件)

判定は `wilson_lower >= 0.50 AND p_value_bonferroni < 0.01 AND N >= 30`。

## Required scope

### 1. データソース (重要 — Codex sandbox 制約)

Shadow 実測は **Render production の sentinel API が一次ソース** ([[feedback_check_orphan_local_app]]: ローカル DB は phantom 汚染リスク)。

- API: `/api/sentinel/stats?entry_type=price_shock_rev_*&after_date=2026-05-18`
- **Codex sandbox は SSH/DNS 不可 ([[project_tp_hit_12cell_portfolio_2026_06_05]] と同制約)**。Render API に到達できない場合は **データ取得を司令塔 (Claude) に差し戻す** — Codex は勝手にローカル SQLite に fallback してはならない。司令塔が CSV export して `.ai/data/price_shock_shadow_2026_06_08.csv` に配置する運用。
- `is_shadow=1` のみ集計 ([[feedback_live_shadow_separation]])。Live 混入で景色が反転した前例あり。

### 2. 評価

- 5 entry_type 各々に `price_shock_rev_promote_evaluator.py` を適用、N / WR / EV / PF / Wilson_lo / p_bonf / Kelly を表で出力。
- N>=30 到達した戦略のみ lot-ramp 提案。N<30 は「shadow 継続、N>=30 待ち」と明記（[[project_tp_hit_12cell_portfolio_2026_06_05]] の orb_trap と同じ正順 — N 不足は設計欠陥ではない、[[feedback_audit_purpose_design_not_n]]）。
- **時間コホート整合** ([[feedback_cohort_time_check]]): good な数字を見たら 05-18→現在の発火時系列を確認し、単一期間集中でないかを検証。

### 3. 成果物

- `knowledge-base/wiki/decisions/price-shock-promote-readiness-2026-06-08.md` に判定表 + verdict (PROMOTE / SHADOW_CONTINUE / NO_FIRE)。
- promote 候補が出た場合も **本タスクでは Live 投入しない**。pre-reg LOCK doc を作り、司令塔の最終判断に回す。

## Codex 注意

- mock-only テストで PASS しても無意味 ([[feedback_codex_mock_test_trap]]) — 実 sentinel データ (または司令塔 CSV) での E2E 必須。
- final.md を信用せず、成果物の git 反映を `git log/diff` で実 verify ([[feedback_codex_stash_leak]])。
