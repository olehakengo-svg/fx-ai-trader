# FX Next — Codexタスクを1つ作る

fx-ai-traderのロードマップ達成に向けて、Codexに渡す次の1タスクを `.ai/tasks/queue/` に作成する。

## 手順

1. `CLAUDE.md` を読む。
2. `knowledge-base/wiki/syntheses/roadmap-v2.1.md` を読む。
3. `knowledge-base/wiki/index.md` と `knowledge-base/wiki/tier-master.md` を読む。
4. `git status --short` を確認し、既存の未コミット変更を壊さないスコープにする。
5. `.ai/tasks/queue/` に未処理タスクがある場合は、新規作成の前にその内容を確認する。

## タスク選定ルール

優先順位は以下。

1. 本番統計の信頼性を壊すP0/P1バグ
2. OANDA転送ロスト、重複、is_shadow drift、Daily Loss Gateなどの本番安全性
3. Roadmap Gate 0/1の未達条件を証明または解消する監査
4. S候補戦略のPhase 3 BT
5. KB/roadmapの整合性更新

## 出力

`.ai/task-template.md` を元に、次の形式で1ファイルだけ作成する。

` .ai/tasks/queue/YYYYMMDD-HHMM-short-slug.md`

## 制約

- 1タスク1目的にする。
- Codexが実装・検証まで完了できる粒度にする。
- 本番DBや秘密情報を破壊しうる操作は禁止事項に明記する。
- 受け入れ条件と検証コマンドを必ず書く。

作成後、ファイルパスと「なぜ今このタスクか」を短く報告する。
