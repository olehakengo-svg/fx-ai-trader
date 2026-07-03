# Lesson: SSOT 指定 KB doc が worktree ブランチに滞留し main 未到達 (2026-07-02)

**発見日**: 2026-07-03 | **修正**: origin/main へ cherry-pick 復旧 (同日)

## 問題
Claude MEMORY が SSOT として参照する KB doc 2件が origin/main に存在しなかった:
1. `wiki/decisions/fable5-system-audit-2026-07-02.md` (MEMORY `project_fable5_audit_2026_07_02.md` が SSOT 指定) — commit `bd8de917` が `research/h4-level-edge` に滞留
2. `wiki/decisions/bb-rsi-t10-kill-2026-07-02.md` (MEMORY `project_bb_rsi_reversion_falsified.md` が SSOT 指定) — commit `367bb6c5` が `claude/busy-bose-b6af88` (未push worktree ブランチ) に滞留

## 症状
- 次セッションが MEMORY の SSOT 参照を辿ると対象ファイルが存在しない = **dangling SSOT**。「KB参照ゼロ→判断停止」ルールに抵触するか、監査25件のバックログ (P0×2含む) が不可視化される
- MEMORY の commit hash 参照も branch-local hash (`d00f441e`) で、main 上の等価 commit (`36c70d06`) と不一致

## 原因
「コード変更とKB更新は同一コミット」ルール自体は**守られていた** (bd8de917 は tool+KB 同梱、367bb6c5 は KB 一式)。病理は次の段:
1. 2026-07-02 セッションは複数 worktree (research/h4-level-edge, busy-bose, hotfix) で並行作業
2. 本番デプロイ用 PR #29 には**防御3コミットのみ選択的 cherry-pick** — 残り (feat(loop) + T10 verdict) の行き先を決めずにセッション終了
3. MEMORY への SSOT 記載はコミット直後に行われ、「main 到達」は確認されなかった

[[lesson-kb-drift-on-context-limit]] の変種: あちらは「コミット漏れ」、こちらは「コミット済みだが main 未到達」。**worktree 運用下では commit ≠ 永続化**。

## 修正
- 2026-07-03: `367bb6c5` / `bd8de917` を origin/main へ cherry-pick (conflict は origin/main 側が上位集合であることを確認して ours 解決)
- MEMORY の hash 参照を main 等価 hash に訂正

## 教訓
**KB doc は main 到達で初めて永続化。worktree/branch 上の commit は SSOT と呼べない。MEMORY に SSOT 参照を書く条件は「同セッション中に main 反映を確認したこと」。**

## 対策
1. セッション終了前チェック: `git log origin/main..HEAD -- knowledge-base/wiki/decisions/ knowledge-base/wiki/lessons/` が非空なら、main 反映 or 明示的な後続タスク化のどちらかを完了してから終了
2. hotfix PR を選択的 cherry-pick で作る場合、**選択しなかった commit の行き先を同時に決める** (後続 PR / queue タスク / 破棄の明示)
3. 残課題: `research/h4-level-edge` に main 未到達 commit 約55件が滞留 (falsified-edge verdict 4件 + explore tools 4本 + 月末WMR/wick-imb pre-reg 等、MEMORY 参照物を含む) — 別タスクでサルベージ判断
