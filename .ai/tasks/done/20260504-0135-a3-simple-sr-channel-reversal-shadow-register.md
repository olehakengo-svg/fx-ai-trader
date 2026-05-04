---
id: 20260504-0135-a3-simple-sr-channel-reversal-shadow-register
title: A3-simple — sr_channel_reversal × EUR_USD 5m を _PAIR_PROMOTED に lot=0.1 trial 登録
owner: codex
status: queued
priority: P1 (Gate 0 reality 確認後に dispatch)
created_at: 2026-05-04T01:35:00+0900
roadmap_gate: Gate 1 候補 1 件目登録 (Gate 0 ACCEPT 確認後)
rule: R1
prerequisite_decisions:
  - 2026-05-03-2221-a2-alt-aggregate-sr-channel-reversal-promote (Promote 確定)
  - 2026-05-04-0017-r2-15cell-lock-gate0-accept-commit (Gate 0 ACCEPT 達成)
gate_to_dispatch: post-merge audit (2026-05-11) で aggregate raw Kelly ≥ 0 が **Live で実測確認**された後
---

## 0. なぜ今このタスクか — 事前起草 (dispatch は条件付き)

A2-alt aggregate verdict (`scalp-alt-pre-registration-2026-05-03.md`) で **`sr_channel_reversal × EUR_USD 5m` Promote 確定**:

- Bonferroni K=4 / α/K=0.0125 LOCK 下、唯一の Promote 候補
- 全 Promote 条件 pass (N=52, WR=61.54%, EV=+0.373p, PF=2.724, Wilson_lo=47.96% > BEV+5pp, WF IS/OOS PF=2.56/2.89, Bonferroni p=0.00418, max DD%=14.84%)

しかし **Gate 0 が崩壊状態だった時点では追加 Live 露出は危険**。Gate 0 ACCEPT (PR #19 merge 済) の **reality 検証完了後** (2026-05-11 post-merge audit で aggregate raw Kelly ≥ 0 が Live で実測確認) に dispatch する。

**本 task spec は事前起草**、user が dispatch 判断を待機して queue 残置。

## 1. 仮説

**H1**: `sr_channel_reversal × EUR_USD 5m` を `_PAIR_PROMOTED` に lot=0.1 (1/10 標準) で登録すると、Live で BT EV (+0.373p) を実測検証可能な N が 30 日で蓄積される。

**H2**: SHADOW 段階の Live edge が positive を維持すれば (Wilson_lo > BEV+0pp, EV>0), 90日後に lot=1.0 段階昇格が可能。

**H3 (リスク)**: Live で BT-Live divergence が発生し EV が反転する可能性 (memory `feedback_ma_filter_breaks_mr` 同類)。lot=0.1 制約により被害は限定的、即座に降格判定可能。

## 2. 対象データ / 分離

| 用途 | 出典 | 混入禁止 |
|---|---|---|
| 編集対象 | `modules/demo_trader.py` の `_PAIR_PROMOTED` set + 既存 `_PAIR_DEMOTED` conflict の除去 | 他 set (`_ELITE_LIVE`, `_FORCE_DEMOTED`) |
| Lot 制御 | `_PAIR_LOT_BOOST[("sr_channel_reversal", "EUR_USD")] = 0.1` | strategy-wide lot / hardcode 全 strategy lot |
| KB sync | `tier_integrity_check.py --write` で `tier-master.{md,json}` 再生成 | 手動編集 |
| Verification | TRUE_LIVE bucket で post-register Live N 集計 | Shadow / FLAG_DRIFT 混入 |

## 3. 統計条件 (Live monitoring spec)

- Promote SHADOW → LIVE 段階昇格条件 (90日後想定):
  - N≥30 Live (`is_shadow=0 oanda_trade_id != ''`)
  - WR > 50% AND Wilson_lo > BEV+5pp
  - PF ≥ 1.30
  - max DD ≤ 30%
  - Bonferroni 補正 p < α/K (K=現在の SHADOW Promote 候補数)

- 即座降格条件 (R2 Fast & Reactive):
  - N≥10 で Wilson_lo < BEV-5pp (反証強い)
  - Live 連続 5 LOSS かつ累計 -20p 以上
  - aggregate raw Kelly が再び -0.05 を下回る

## 4. ACCEPT / REJECT / NEEDS_MORE

- **ACCEPT (dispatch 後)**: `_PAIR_PROMOTED` 編集 + `tier_integrity_check --check` ERROR=0 WARN=0 + lot=0.1 設定確認 + 単一 commit
- **REJECT**: integrity 違反、または lot=0.1 設定 mechanism が `modules/` に存在しない (構造調整必要)
- **NEEDS_MORE_EVIDENCE**: lot 制御 mechanism 追加開発が必要

## 5. Scope

Codex MAY change:

- `modules/demo_trader.py` の `_PAIR_PROMOTED` set: `("sr_channel_reversal", "EUR_USD")` 追加
- `modules/demo_trader.py` の `_PAIR_DEMOTED` set: 既存 `("sr_channel_reversal", "EUR_USD")` を削除
- `_PAIR_LOT_BOOST`: `("sr_channel_reversal", "EUR_USD"): 0.1`
- `tier-master.{md,json}`: `tier_integrity_check.py --write` で auto-regen
- `wiki/strategies/sr-channel-reversal.md`: status 更新 (PAIR_PROMOTED に追加)
- `.ai/runs/<run-dir>/final.md`
- 単一 commit 作成 (push しない、PR で review)

Codex MAY NOT change:

- `app.py`, `strategies/`, `tools/` 既存ファイル
- `_ELITE_LIVE`, `_FORCE_DEMOTED` の他 set
- `modules/demo_trader.py` の他 logic / function
- 既存未コミット変更

## 6. Required Reading

- `CLAUDE.md` (Rule 1 Slow & Strict)
- `wiki/learning/scalp-alt-pre-registration-2026-05-03.md` (Promote 確定 SSOT)
- `.ai/decisions/2026-05-03-2221-a2-alt-aggregate-sr-channel-reversal-promote-provisional.md` (Claude review)
- `wiki/decisions/r2-tier1-hour-bucket-extension-2026-05-03.md` (Gate 0 ACCEPT path)
- `modules/demo_trader.py:6209` (`_PAIR_PROMOTED` 現状 + 編集場所)
- `wiki/lessons/index.md` の `feedback_ma_filter_breaks_mr`, `feedback_partial_quant_trap`, `feedback_label_empirical_audit`

## 7. Acceptance Criteria

- [ ] `modules/demo_trader.py` の `_PAIR_PROMOTED` に `("sr_channel_reversal", "EUR_USD")` 追加
- [ ] `modules/demo_trader.py` の `_PAIR_DEMOTED` から `("sr_channel_reversal", "EUR_USD")` 削除
- [ ] `_PAIR_LOT_BOOST` に `("sr_channel_reversal", "EUR_USD"): 0.1` 設定
- [ ] lot floor 回帰テストで 0.1 が 0.3 に切り上がらないことを確認
- [ ] `tier_integrity_check.py --write` で `tier-master.{md,json}` regenerate
- [ ] `tier_integrity_check.py --check` ERROR=0 WARN=0
- [ ] `wiki/strategies/sr-channel-reversal.md` 更新
- [ ] 単一 commit message: `rule:R1 type:promote-shadow strategy:sr_channel_reversal pair:EUR_USD lot:0.1 ref:scalp-alt-pre-reg-2026-05-03` を含む
- [ ] `app.py`, `strategies/`, `tools/`, `_ELITE_LIVE`, `_FORCE_DEMOTED` touched=0
- [ ] PR 作成、push しない

## 8. Verification Commands

```bash
# 1. Integrity regen + check
python3 tools/tier_integrity_check.py --write
python3 tools/tier_integrity_check.py --check

# 2. lot 設定確認
grep -B2 -A5 "sr_channel_reversal" modules/demo_trader.py | head -30

# 3. Strategies drift check
python3 tools/strategies_drift_check.py

# 4. Commit
git add modules/demo_trader.py knowledge-base/wiki/tier-master.md knowledge-base/wiki/tier-master.json knowledge-base/wiki/strategies/sr-channel-reversal.md
git commit -m "..."

# 5. Side-effect 確認
git diff HEAD~1..HEAD -- app.py strategies/ tools/ | wc -l  # → 0 expected
```

## 9. Codex Instructions

これは **Rule 1 Slow & Strict** タスク。Bonferroni K=4 LOCK 下で確定済 Promote 候補の SHADOW 段階登録。

**重要**: Gate 0 ACCEPT (`r2-postmerge-audit-2026-05-10`) で **Live aggregate raw Kelly ≥ 0 が実測確認**されてから dispatch する。これは task spec ではなく **dispatch 判断** の問題。spec は事前起草。

`feedback_partial_quant_trap` 通り、N/WR/EV/PF/Wilson_lo/Bonferroni/WF/max DD 全て pass の Promote 条件 evidence は既に確定済。再 BT 不要。

`feedback_ma_filter_breaks_mr` 罠回避: lot=0.1 SHADOW 段階で 30-90日 Live 検証。即座 LIVE lot=1.0 昇格は禁止。

PR 作成までで止まる。Render auto-deploy への影響は merge 時に発生 → Claude/user review 必須。

最終レポートに: status, files changed, lot=0.1 設定確認, integrity check 出力, commit hash, 90日後 LIVE 段階昇格条件 reaffirm, 次タスク (90日 monitoring + 段階昇格 verification spec)。


## Result (2026-05-04T05:30:52Z)

exit=0 · 15s

```
Status: **DEFERRED / dispatch 待機**

現在日は **2026-05-04** なので、指定条件の **2026-05-11 post-merge audit で Live aggregate raw Kelly ≥ 0 を実測確認後** にはまだ到達していません。したがって、この turn では `_PAIR_PROMOTED` 登録、lot=0.1 設定、KB regen、commit、PR 作成は実行しません。

現時点の扱い:

- Files changed: なし
- Commit: なし
- PR: なし
- Reason: Gate 0 reality 検証未完了のため dispatch 条件未成立
- Next dispatch condition: `r2-postmerge-audit-2026-05-10/11` で TRUE_LIVE aggregate raw Kelly ≥ 0 を確認

dispatch 後に実行する内容はこの spec の通りで問題ありません。特に `sr_channel_reversal × EUR_USD` は **lot=0.1 SHADOW 登録のみ**、90日後の LIVE lot=1.0 昇格は別判定として、N≥30 / WR / Wilson_lo / PF / DD / Bonferroni を再確認する前提で扱います。
```
