---
id: 20260503-2310-r2-15cell-modules-lock-pr
title: R2 15-cell LOCK 実装 — modules/demo_trader.py SSOT 編集 (Gate 0 ACCEPT 達成 PR)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T23:10:00+0900
roadmap_gate: Gate 0 ACCEPT 達成 (raw Kelly +0.0094, MC60d 0.30%)
rule: R2
prerequisite_decisions:
  - 2026-05-03-2305-r2-tier1-extension-gate0-accept-path
  - 2026-05-03-2230-r2-14cell-blocked-pair-promoted-conflict
prerequisite_tasks:
  - 20260503-2230-r2-tier1-hour-bucket-extension (ACCEPT, +0.0094 Kelly)
  - 20260503-2240-r2-14cell-conflict-resolution (BLOCKED, scope=modules/)
---

## 0. なぜ今このタスクか

直前 2 task の決定:

- `r2-tier1-hour-bucket-extension`: **ACCEPT** verdict — 15-cell (14 base + `gbp_deep_pullback × GBP_USD`) demote で:
  - raw Kelly: -0.1326 → **+0.0094** (Gate 0 ACCEPT 閾値突破)
  - MC60d: 86.50% → **0.30%** (完全生存圏)
- `r2-14cell-conflict-resolution`: **BLOCKED** — scope 制約で `modules/demo_trader.py` 編集不可。runtime SSOT は同 file の `_PAIR_DEMOTED` / `_PAIR_PROMOTED` 定数。

本 task は **scope を拡張して `modules/demo_trader.py` 編集を許可**し、15-cell LOCK + 2 pair_promoted 削除 + 1 elite_live 解除を 1 commit で実装する。auto-regenerator (`tier_integrity_check.py --write`) で `tier-master.{md,json}` を同期。

これが Gate 0 ACCEPT 達成の **最終実装 PR**。

## 1. 仮説

**H1**: `modules/demo_trader.py:6158` `_PAIR_DEMOTED` に 11 cell 追加 (4 cell は no-op 既存) + `:6209` `_PAIR_PROMOTED` から 2 cell 削除 + `_ELITE_LIVE` から 1 cell 削除 で `tier_integrity_check.py --check` ERROR=0 WARN=0 を維持。

**H2**: post-edit `--write` で `tier-master.md` / `tier-master.json` が自動再生成され、JSON↔MD↔code 三者整合。

**H3**: post-merge Render auto-deploy 後、OANDA gate (`modules/demo_trader.py:5008-5009`) が 15 cell 全て SHADOW dispatch に切替。Live trade で `pair_demoted(...)` block_reason が記録される。

**H4**: 7d 後の Live audit で aggregate raw Kelly が -0.1854 → 0+ 範囲に到達 (counterfactual +0.0094 と完全一致は期待しないが positive 達成)。

## 2. 対象データ / 分離

| 用途 | 出典 | 混入禁止 |
|---|---|---|
| 編集対象 | `modules/demo_trader.py` の `_PAIR_DEMOTED` (+11), `_PAIR_PROMOTED` (-2), `_ELITE_LIVE` (-1) のみ | 他の constant、function logic |
| 自動生成 | `tier_integrity_check.py --write` で `tier-master.{md,json}` 同期 | 手動編集 |
| Drift check | TRUE_LIVE bucket (`is_shadow=0 oanda_trade_id != ''`...) | SHADOW/FLAG_DRIFT/XAU/EURGBP |
| Test | `pytest` 関連 test (tier integrity, demo_trader unit) | full suite で時間切れ防止 |

## 3. 確定 15-cell LOCK list (immutable)

`r2-tier1-hour-bucket-extension-2026-05-03.md` の Min extension demote set + R2 TRUE_LIVE counterfactual 14-cell:

```python
# _PAIR_DEMOTED に追加 (11 new — 4 cell は既存で no-op skip)
PAIR_DEMOTED_ADD = [
    ("vwap_mean_reversion", "GBP_USD"),
    ("vix_carry_unwind", "USD_JPY"),         # ★ _PAIR_PROMOTED から削除も必要
    ("sr_channel_reversal", "USD_JPY"),
    ("bb_rsi_reversion", "USD_JPY"),
    ("session_time_bias", "GBP_USD"),
    ("bb_squeeze_breakout", "USD_JPY"),       # ★ _PAIR_PROMOTED から削除も必要
    ("vol_surge_detector", "USD_JPY"),
    ("v_reversal", "USD_JPY"),
    ("trend_rebound", "USD_JPY"),
    ("sr_channel_reversal", "EUR_USD"),
    ("gbp_deep_pullback", "GBP_USD"),         # ★ _ELITE_LIVE から削除も必要 (Tier 1 拡張)
    # already in _PAIR_DEMOTED (no-op): bb_rsi_reversion×EUR_USD, engulfing_bb×USD_JPY, engulfing_bb×EUR_USD, stoch_trend_pullback×USD_JPY
]

PAIR_PROMOTED_REMOVE = [
    ("vix_carry_unwind", "USD_JPY"),
    ("bb_squeeze_breakout", "USD_JPY"),
]

ELITE_LIVE_REMOVE = [
    ("gbp_deep_pullback", "GBP_USD"),
]
```

## 4. ACCEPT / REJECT / NEEDS_MORE 条件

- **ACCEPT**: 上記 3 set 編集が単一 commit で完了 AND `tier_integrity_check.py --check` ERROR=0 WARN=0 AND `pytest` 関連 test pass AND drift check 15 cell 全て DEMOTE_OK 維持
- **CHANGES_REQUESTED**: partial 実装、明確な改善経路あり
- **REJECT**: integrity check ERROR、または 15 cell の 1 つ以上が drift で WR > BEV 反転 (= Rule 2 損失停止根拠喪失)

## 5. Scope

Codex MAY change:

- `modules/demo_trader.py` の `_PAIR_DEMOTED` set 内容
- `modules/demo_trader.py` の `_PAIR_PROMOTED` set 内容
- `modules/demo_trader.py` の `_ELITE_LIVE` set 内容
- `knowledge-base/wiki/tier-master.md` (auto-regen via `tier_integrity_check.py --write`)
- `knowledge-base/wiki/tier-master.json` (auto-regen)
- `.ai/runs/<run-dir>/final.md`
- 単一 commit を作成 (push しない、Claude/user review 後に手動 push)

Codex MAY NOT change:

- `modules/demo_trader.py` 内の他の logic / constant / function (上記 3 set のみ)
- `app.py`, `strategies/`, `tools/` (既存ファイル全て)
- `.env`, OANDA secrets, production credentials, `live_ng_cells` SQLite
- `wiki/decisions/` 既存ファイル, `wiki/index.md`, `wiki/strategies/` (新 decision doc 作成は OK)
- 既存未コミット変更

## 6. Required Reading

- `CLAUDE.md` (Rule 2 Fast & Reactive, KB 運用ルール)
- `.ai/decisions/2026-05-03-2305-r2-tier1-extension-gate0-accept-path.md` (Claude review)
- `wiki/decisions/r2-tier1-hour-bucket-extension-2026-05-03.md` (15-cell counterfactual SSOT)
- `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (14-cell base SSOT)
- `wiki/decisions/gate-progression-audit-2026-05-03.md` (Live aggregate baseline)
- `modules/demo_trader.py:6158-6300` (`_PAIR_DEMOTED`, `_PAIR_PROMOTED`, `_ELITE_LIVE` の現状)
- `tools/tier_integrity_check.py` (auto-regenerator 仕組み)
- `wiki/lessons/index.md` の `feedback_ma_filter_breaks_mr`, `feedback_label_empirical_audit`, `feedback_live_shadow_separation`

## 7. Acceptance Criteria

- [ ] `modules/demo_trader.py` の `_PAIR_DEMOTED` に 11 new cells 追加 (重複追加なし)
- [ ] `modules/demo_trader.py` の `_PAIR_PROMOTED` から `vix_carry_unwind × USD_JPY`, `bb_squeeze_breakout × USD_JPY` 削除
- [ ] `modules/demo_trader.py` の `_ELITE_LIVE` から `gbp_deep_pullback × GBP_USD` 削除
- [ ] `python3 tools/tier_integrity_check.py --write` 実行で `tier-master.md` / `tier-master.json` auto-regenerated
- [ ] `python3 tools/tier_integrity_check.py --check` exit 0, ERROR=0, WARN=0
- [ ] `pytest tests/test_tier_master.py tests/test_tier_integrity_check.py` (or 関連 test) pass
- [ ] Drift check: `python3 tools/r2_tier1_hour_bucket_extension.py --dry-run` で extension verdict ACCEPT 維持
- [ ] 単一 commit message: `rule:R2 type:lock cells:15 ref:r2-tier1-extension-2026-05-03 gate0-accept` を含む
- [ ] `app.py`, `strategies/`, `tools/` 既存ファイル touched=0
- [ ] `.ai/runs/<run-dir>/final.md` に: status, files changed, drift table, integrity check 出力, commit hash, residual risks, 7d post-merge audit 計画

## 8. Verification Commands

```bash
# 1. Drift check (15 cell 全て DEMOTE_OK 維持確認)
python3 tools/r2_tier1_hour_bucket_extension.py --dry-run --trades /tmp/live-trades-20260503.json --base-demote-set knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md --mc-iterations 1000

# 2. Integrity regen + check
python3 tools/tier_integrity_check.py --write
python3 tools/tier_integrity_check.py --check

# 3. Tests
python3 -m pytest -q tests/test_tier_master.py tests/test_tier_integrity_check.py

# 4. Commit (push なし)
git status
git diff --stat
git add modules/demo_trader.py knowledge-base/wiki/tier-master.md knowledge-base/wiki/tier-master.json
git commit -m "rule:R2 type:lock cells:15 ref:r2-tier1-extension-2026-05-03 gate0-accept

Apply 15-cell LOCK + Tier 1 demote per r2-tier1-hour-bucket-extension-2026-05-03.md.
Counterfactual: raw Kelly -0.1326 → +0.0094, MC60d 0.8650 → 0.0030.
- _PAIR_DEMOTED += 11 new cells (4 already present)
- _PAIR_PROMOTED -= [vix_carry_unwind/USDJPY, bb_squeeze_breakout/USDJPY]
- _ELITE_LIVE -= [gbp_deep_pullback/GBPUSD]
"

# 5. 副作用ゼロ確認
git diff HEAD~1..HEAD -- app.py strategies/ tools/ | wc -l  # → 0 expected
```

## 9. Codex Instructions

これは **Rule 2 Fast & Reactive** 実装タスク。365日 BT 不要、loss stop と portfolio 整合が目的。

**重要な scope 拡張理由**: 旧 R2 task 2 件で `modules/` 編集禁止だったが、blocked 結果から runtime SSOT が `modules/demo_trader.py` 定数だと判明。tier-master.json/md は auto-generated で SSOT ではない。本 task は構造正解として `modules/` 編集を解禁。

ただし **scope 厳格**: `_PAIR_DEMOTED`, `_PAIR_PROMOTED`, `_ELITE_LIVE` の 3 set 内容変更のみ。`modules/demo_trader.py` 内の logic / function / 他 constant は触らない。

`feedback_success_until_achieved` 通り、partial 実装で closure 短絡禁止。15 cell 全 LOCK + 2 pair_promoted 削除 + 1 elite_live 解除が ACCEPT 条件。

PR は **本タスクで作成しない**。1 commit を作成、push しない。Claude/user review 後に user が `git push` 判断。

DNS 失敗で Render snapshot 取れない場合、`/tmp/live-trades-20260503.json` フォールバック。

最終レポートには status, files changed, 15 cell drift table 再掲, integrity check 出力, commit hash, 副作用ゼロ確認 (`git diff HEAD~1..HEAD -- app.py strategies/ tools/` 出力空), 7d post-merge audit 計画, 次タスク。

ACCEPT 達成後の次タスク:
- 7d 後 `r2-postmerge-audit-2026-05-10.md` (Live N 蓄積後の aggregate Kelly 改善幅実測, counterfactual +0.0094 と reality 比較)
- 並行 `a3-simple-sr-channel-reversal-shadow-register` (A2-alt Promote 候補を Gate 0 ACCEPT 確認後に lot=0.1 SHADOW 登録)
- 必要時 `tier1-routing-anomaly-rca-2026-05-04` (前回 Tier 1 audit で発覚した OANDA 0.5% 発火率の構造解析)

REJECT (drift で 1 cell 反転) なら:
- `r2-cell-recheck-2026-05-04` で当該 cell 単独監査、demote 維持/解除を Rule 2 即断
