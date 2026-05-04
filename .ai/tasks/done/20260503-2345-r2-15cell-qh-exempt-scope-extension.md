---
id: 20260503-2345-r2-15cell-qh-exempt-scope-extension
title: R2 15-cell LOCK 実装 (再走) — `_QUICK_HARVEST_EXEMPT` 含む 4-set scope で WARN=0 達成
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T23:45:00+0900
roadmap_gate: Gate 0 ACCEPT 達成 (raw Kelly +0.0094, MC60d 0.30%)
rule: R2
prerequisite_decisions:
  - 2026-05-03-2337-r2-15cell-blocked-qh-exempt (3rd blocker, QH_EXEMPT)
  - 2026-05-03-2305-r2-tier1-extension-gate0-accept-path (Gate 0 ACCEPT counterfactual)
prerequisite_tasks:
  - 20260503-2310-r2-15cell-modules-lock-pr (BLOCKED, working tree に変更残置)
---

## 0. なぜ今このタスクか

直前 task (`r2-15cell-modules-lock-pr`) が 3rd blocker で BLOCKED:

- 3 set (`_PAIR_DEMOTED`, `_PAIR_PROMOTED`, `_ELITE_LIVE`) 編集は完了 (working tree)
- `tier_integrity_check.py --check` で **WARN=2** 検出:
  - `QUICK_HARVEST_EXEMPT (gbp_deep_pullback, GBP_USD) not in ELITE/PAIR_PROMOTED`
  - `QUICK_HARVEST_EXEMPT (vix_carry_unwind, USD_JPY) not in ELITE/PAIR_PROMOTED`
- Codex は WARN=2 で deploy-ready でないと判断 → partial commit 拒否 (規律遵守)

本 task は scope を `_QUICK_HARVEST_EXEMPT` に拡張、4-set atomic alignment で WARN=0 を達成して Gate 0 ACCEPT PR を完成させる。

## 1. 仮説

**H1**: `_QUICK_HARVEST_EXEMPT` から `gbp_deep_pullback × GBP_USD`, `vix_carry_unwind × USD_JPY` を削除すれば `tier_integrity_check.py --check` が ERROR=0 WARN=0 で pass。

**H2**: 4-set atomic 編集 (PAIR_DEMOTED+11, PAIR_PROMOTED-2, ELITE_LIVE-1, QUICK_HARVEST_EXEMPT-2) で `tier-master.{md,json}` auto-regen 後の三者整合 (code ↔ MD ↔ JSON) 達成。

**H3**: post-merge Render auto-deploy 後、Live trade で `pair_demoted(...)` block_reason が記録され 7d 後の audit で aggregate raw Kelly が -0.1854 → 0+ 範囲到達。

## 2. Working tree 取り扱い

直前 task が working tree に未 commit 変更を残した:
- `modules/demo_trader.py` (3 set edited)
- `knowledge-base/wiki/tier-master.md` (regenerated)
- `knowledge-base/wiki/tier-master.json` (regenerated)

**対応方針**: clean start で再実装。Codex は既存 working tree 変更を inspect してから:
- (a) 既存変更を継承して `_QUICK_HARVEST_EXEMPT` 削除のみ追加 (推奨、再走時間短縮)
- (b) `git stash` で変更を保存 → クリーンチェックアウトから 4-set atomic 編集 (再現性最高)

(a) が安全かつ最小 diff なので推奨。ただし git stash は user 確認後でないと avoid (existing uncommitted changes を破壊しない方針)。

## 3. 確定編集セット (4-set atomic, immutable)

`modules/demo_trader.py` 内:

```python
# Set 1: _PAIR_DEMOTED に 11 cell 追加 (4 既存で no-op, 既存 working tree で適用済か確認)
PAIR_DEMOTED_ADD = [
    ("vwap_mean_reversion", "GBP_USD"),
    ("vix_carry_unwind", "USD_JPY"),
    ("sr_channel_reversal", "USD_JPY"),
    ("bb_rsi_reversion", "USD_JPY"),
    ("session_time_bias", "GBP_USD"),
    ("bb_squeeze_breakout", "USD_JPY"),
    ("vol_surge_detector", "USD_JPY"),
    ("v_reversal", "USD_JPY"),
    ("trend_rebound", "USD_JPY"),
    ("sr_channel_reversal", "EUR_USD"),
    ("gbp_deep_pullback", "GBP_USD"),  # Tier 1 拡張
]

# Set 2: _PAIR_PROMOTED から削除
PAIR_PROMOTED_REMOVE = [
    ("vix_carry_unwind", "USD_JPY"),
    ("bb_squeeze_breakout", "USD_JPY"),
]

# Set 3: _ELITE_LIVE から削除
ELITE_LIVE_REMOVE = [
    ("gbp_deep_pullback", "GBP_USD"),
]

# Set 4: _QUICK_HARVEST_EXEMPT から削除 (★ 本 task で新規 scope)
QUICK_HARVEST_EXEMPT_REMOVE = [
    ("gbp_deep_pullback", "GBP_USD"),  # L6451
    ("vix_carry_unwind", "USD_JPY"),   # L6459
]
```

## 4. ACCEPT / REJECT / NEEDS_MORE 条件

- **ACCEPT**: 4-set 編集が単一 commit で完了 AND `tier_integrity_check.py --check` ERROR=0 **WARN=0** AND drift check 15 cell 全て DEMOTE_OK 維持
- **CHANGES_REQUESTED**: ERROR=0 で WARN ≤ 1 (例: `_STRATEGY_LOT_BOOST` の `gbp_deep_pullback` 残置のみ)、明確に文書化された acceptable warning
- **REJECT**: ERROR ≥ 1、または 4 set のいずれかで構造的衝突発生

`_STRATEGY_LOT_BOOST` の `gbp_deep_pullback` は前 task の Codex note で「integrity check 非ブロック」と判明、**本 task scope 外** (touched=0)。WARN 出ない想定だが、もし出たら CHANGES_REQUESTED で別 task。

## 5. Scope

Codex MAY change:

- `modules/demo_trader.py` の 4 sets (`_PAIR_DEMOTED`, `_PAIR_PROMOTED`, `_ELITE_LIVE`, `_QUICK_HARVEST_EXEMPT`) のみ
- `knowledge-base/wiki/tier-master.md` (auto-regen via `tier_integrity_check.py --write`)
- `knowledge-base/wiki/tier-master.json` (auto-regen)
- `.ai/runs/<run-dir>/final.md`
- 単一 commit を作成 (push しない)

Codex MAY NOT change:

- `modules/demo_trader.py` 内の他 set (`_STRATEGY_LOT_BOOST` 等) や logic / function / 他 constant
- `app.py`, `strategies/`, `tools/` (既存ファイル全て)
- `.env`, OANDA secrets, production credentials, `live_ng_cells`
- `wiki/decisions/` / `wiki/index.md` / `wiki/strategies/` (新 decision doc 作成は OK)
- 既存未コミット変更 (working tree の前 task 変更は継承可、`git stash` 等で破壊しない)

## 6. Required Reading

- `CLAUDE.md` (Rule 2 Fast & Reactive, KB 運用ルール)
- `.ai/decisions/2026-05-03-2337-r2-15cell-blocked-qh-exempt.md` (本 task の根拠、3rd blocker 詳細)
- `.ai/decisions/2026-05-03-2305-r2-tier1-extension-gate0-accept-path.md` (Gate 0 ACCEPT counterfactual)
- `wiki/decisions/r2-tier1-hour-bucket-extension-2026-05-03.md` (15-cell SSOT)
- `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (14-cell base SSOT)
- `modules/demo_trader.py:6158-6500` (4 sets の現状確認)
- `tools/tier_integrity_check.py` (regenerator + integrity check)

## 7. Acceptance Criteria

- [ ] `modules/demo_trader.py` の `_PAIR_DEMOTED` に 11 new cells 存在 (4 既存 no-op)
- [ ] `modules/demo_trader.py` の `_PAIR_PROMOTED` から 2 cells 削除済 (`vix_carry_unwind × USDJPY`, `bb_squeeze_breakout × USDJPY`)
- [ ] `modules/demo_trader.py` の `_ELITE_LIVE` から 1 cell 削除済 (`gbp_deep_pullback × GBP_USD`)
- [ ] `modules/demo_trader.py` の `_QUICK_HARVEST_EXEMPT` から 2 cells 削除済 (`gbp_deep_pullback × GBP_USD`, `vix_carry_unwind × USDJPY`)
- [ ] `python3 tools/tier_integrity_check.py --write` 実行で `tier-master.md` / `tier-master.json` auto-regenerated
- [ ] `python3 tools/tier_integrity_check.py --check` exit 0, ERROR=0, **WARN=0**
- [ ] Drift check: `python3 tools/r2_tier1_hour_bucket_extension.py --dry-run` で extension verdict ACCEPT 維持
- [ ] 単一 commit message: `rule:R2 type:lock cells:15 ref:r2-tier1-extension-2026-05-03 gate0-accept qh-coupled` を含む
- [ ] `app.py`, `strategies/`, `tools/` 既存ファイル touched=0
- [ ] `_STRATEGY_LOT_BOOST` 触れず (前 task の Codex note 通り integrity 非ブロック前提)
- [ ] `.ai/runs/<run-dir>/final.md` に: status, files changed, drift table 再掲, integrity check 出力 (WARN=0 確認), commit hash, residual risks (LOT_BOOST 残置の言及), 7d post-merge audit 計画

## 8. Verification Commands

```bash
# 1. Working tree 確認
git status --short

# 2. Drift check
python3 tools/r2_tier1_hour_bucket_extension.py --dry-run --trades /tmp/live-trades-20260503.json --base-demote-set knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md --mc-iterations 1000

# 3. Integrity regen + check (WARN=0 必達)
python3 tools/tier_integrity_check.py --write
python3 tools/tier_integrity_check.py --check

# 4. Commit (push なし)
git status
git diff --stat
git add modules/demo_trader.py knowledge-base/wiki/tier-master.md knowledge-base/wiki/tier-master.json
git commit -m "rule:R2 type:lock cells:15 ref:r2-tier1-extension-2026-05-03 gate0-accept qh-coupled

Apply 15-cell LOCK + Tier 1 demote per r2-tier1-hour-bucket-extension-2026-05-03.md.
Counterfactual: raw Kelly -0.1326 → +0.0094, MC60d 0.8650 → 0.0030.
- _PAIR_DEMOTED += 11 new cells (4 already present)
- _PAIR_PROMOTED -= [vix_carry_unwind/USDJPY, bb_squeeze_breakout/USDJPY]
- _ELITE_LIVE -= [gbp_deep_pullback/GBPUSD]
- _QUICK_HARVEST_EXEMPT -= [gbp_deep_pullback/GBPUSD, vix_carry_unwind/USDJPY] (coupled with tier downgrade)

Note: gbp_deep_pullback remains in _STRATEGY_LOT_BOOST (integrity non-blocking, separate review).
"

# 5. 副作用ゼロ確認
git diff HEAD~1..HEAD -- app.py strategies/ tools/ | wc -l  # → 0 expected
```

## 9. Codex Instructions

これは **Rule 2 Fast & Reactive** 実装タスク (再走)。前 task の BLOCKED 経験から `_QUICK_HARVEST_EXEMPT` を含む 4-set atomic alignment が必要と判明。

**Working tree 取り扱い**: 前 task が `modules/demo_trader.py` (3 set), `tier-master.{md,json}` (auto-regen) に未 commit 変更を残置。これらは正しい変更なので、本 task は **既存変更を継承**して `_QUICK_HARVEST_EXEMPT` 削除のみ追加し、最後に `tier_integrity_check.py --write` 再実行 + commit。`git stash` 等での破壊禁止。

**重要**: `_STRATEGY_LOT_BOOST` の `gbp_deep_pullback` は前 task で「integrity 非ブロック」と判明。本 task scope 外、touched=0 で進める。WARN 出たら CHANGES_REQUESTED で別 task に escalate。

`feedback_success_until_achieved` 通り、partial 実装で closure 短絡禁止。WARN=0 必達。

PR は **本タスクで作成しない**。1 commit を作成、push しない。Claude/user review 後に user が `git push` 判断。

最終レポートには status, files changed, 15 cell drift table 再掲, integrity check 出力 (ERROR=0 WARN=0 確認), commit hash, 副作用ゼロ確認, `_STRATEGY_LOT_BOOST` 残置 note, 7d post-merge audit 計画, 次タスク。

ACCEPT 達成後の次タスク:
- 7d 後 `r2-postmerge-audit-2026-05-10.md` (Live N 蓄積後の aggregate Kelly 改善幅実測)
- 並行 `a3-simple-sr-channel-reversal-shadow-register` (A2-alt Promote 候補を Gate 0 ACCEPT merge 後に lot=0.1 SHADOW 登録)
- 必要時 `r2-strategy-lot-boost-cleanup` (`gbp_deep_pullback` 残置の整理、低優先度)
