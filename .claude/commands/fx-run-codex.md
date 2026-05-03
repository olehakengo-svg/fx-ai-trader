---
description: Codex queued task runner for fx-ai-trader
argument-hint: [task-number-or-file]
---

# FX Run Codex

対象repoは必ず `/Users/jg-n-012/test/fx-ai-trader`。

まず次を実行して Codex タスク一覧を確認する:

```bash
cd /Users/jg-n-012/test/fx-ai-trader
./tools/ai_run_codex_companion.sh --list
```

`$ARGUMENTS` にタスク番号またはタスクファイルが指定されている場合だけ、次を実行する:

```bash
cd /Users/jg-n-012/test/fx-ai-trader
./tools/ai_run_codex_companion.sh $ARGUMENTS
```

`$ARGUMENTS` が空の場合は、Codex を実行せず、どの番号を実行するかユーザーに確認する。複数タスクがある状態で暗黙に最新タスクを走らせない。

実行は Claude Code の Codex companion 経由にする。raw Bash の `codex exec` は使わない。

実行後、出力された run directory、Codex companion Job ID、status command、result command、final report の場所を確認する。Codex アプリの左サイドバーはタイトルが省略・混線することがあるため、会話一覧の表示名では判断しない。必ず Job ID と Codex session ID で追跡する。

status/result は `./tools/ai_codex_status.sh <job_id>` / `./tools/ai_codex_status.sh --result <job_id>` を使う。Codex companion の job store は `codex-inline` / `codex-openai-codex` / 一時ディレクトリに分かれることがあるため、raw `codex-companion.mjs status` を直叩きしない。

ユーザーへは少なくとも以下を報告する:

- Job ID
- status command
- result command
- Codex session ID（status 出力にあれば）
- final report path

## クオンツ確認

- Codex結果を見るときは `BT` / `Shadow` / `Live is_shadow=0` / `OANDA` が混ざっていないか確認する。
- `N`, `WR`, `EV`, `PF`, `Kelly`, `Wilson lower`, `Bonferroni`, `OOS/WF` が必要なタスクでは、出力に含まれているか確認する。
- Rule 1/2/3、Gate、採用/保留/棄却の根拠が明示されているか確認する。
- 本番DB、`.env`、OANDA秘密情報を触るタスクなら実行前に止める。
- Codex が失敗した場合はログを読み、`.ai/tasks/queue/` に修正タスクを作る。
- 報告は必ず日本語で行う。
