# FX Review Result — Codex結果レビュー

Codexが `.ai/runs/` に出した最新レポートをレビューし、ロードマップ/KB/次タスクに反映する。

## 手順

1. `.ai/runs/` の最新ディレクトリまたは最新 `final.md` を読む。
2. 対応する `.ai/tasks/queue/` のタスクを読む。
3. Codexの変更差分を `git diff --stat` と必要な `git diff -- <file>` で確認する。
4. 検証コマンドの結果が十分か判断する。
5. `CLAUDE.md` のRule 1/2/3判断プロトコルに従って採用/差し戻し/追加検証を決める。

## 判定

以下のいずれかを明示する。

- `ACCEPT`: ロードマップ前進。必要ならKB/roadmap更新。
- `NEEDS_MORE_EVIDENCE`: 実装は保留または追加BT/監査が必要。
- `CHANGES_REQUESTED`: Codexに修正タスクを戻す。
- `REJECT`: 根拠不足または危険。

## 更新先

必要に応じて以下を更新する。

- `knowledge-base/wiki/syntheses/roadmap-v2.1.md`
- `knowledge-base/wiki/index.md`
- `knowledge-base/wiki/decisions/`
- `knowledge-base/wiki/sessions/`
- `.ai/decisions/YYYYMMDD-HHMM-review.md`

## タスク整理

- `ACCEPT` の場合、対応タスクを `.ai/tasks/done/` に移動する。
- `CHANGES_REQUESTED` または `NEEDS_MORE_EVIDENCE` の場合、次のCodexタスクを `.ai/tasks/queue/` に作成する。
- `REJECT` の場合、対応タスクを `.ai/tasks/failed/` に移動し、理由を `.ai/decisions/` に残す。

最後に、現在のロードマップ上の次の一手を1つだけ提示する。
