---
description: Check recent Codex companion task completion status
argument-hint: [count]
allowed-tools: Bash
---

# FX Codex Check

対象repoは必ず `/Users/jg-n-012/test/fx-ai-trader`。

Codex companion の直近runについて、完了済みか実行中かを短く確認する。

`$ARGUMENTS` が空なら直近8件を見る。数字が指定されている場合はその件数を見る。

実行する:

```bash
cd /Users/jg-n-012/test/fx-ai-trader
./tools/ai_codex_check.sh ${ARGUMENTS:-8}
```

報告は日本語で、以下だけを簡潔に伝える:

- ACTIVE の job があるか
- BAD / CHECK があるか
- 最新 job の STATE と PHASE
- 詳細確認が必要なら `./tools/ai_codex_status.sh <job_id>` を提示

Codex.app の会話一覧表示は判定材料にしない。公式判定は `.ai/runs/*/codex-job.txt` と `./tools/ai_codex_check.sh` の出力。
