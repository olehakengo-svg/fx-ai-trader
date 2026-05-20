---
id: 20260520-cleanup-malformed-queue-finals
title: "[Queue Hygiene] price-shock final.md misfiled in queue/ → move to done/ (2 files)"
owner: codex
status: queued
priority: P2
created_at: 2026-05-20T12:30:00+0900
roadmap_gate: "Render worker (fx-codex-runner) が `.ai/tasks/queue/*-final.md` 2 件を YAML frontmatter 不在で永遠に skip。これは final.md スタイル完了レポートが done/ ではなく queue/ に置かれた misfile であり、対応する親 task は既に done/ 配下に存在する。worker ログ noise の解消と queue/ 整理が目的。"
rule: hygiene
related:
  - .ai/tasks/queue/20260518-1352-price-shock-rev-phase-b1-final.md       # misfiled
  - .ai/tasks/queue/20260518-1457-price-shock-live-shadow-monitor-final.md # misfiled
  - .ai/tasks/done/20260518-1352-price-shock-rev-phase-b1.md              # 親 task (done 済)
  - .ai/tasks/done/20260518-1620-price-shock-live-shadow-monitor-retry.md # 親 task (done 済)
---

# 1. 問題

Render worker ログ抜粋 (2026-05-20T04:11:25Z):
```
WARNING worker.queue: skipping malformed queue file .../20260518-1352-price-shock-rev-phase-b1-final.md
ValueError: missing YAML frontmatter
WARNING worker.queue: skipping malformed queue file .../20260518-1457-price-shock-live-shadow-monitor-final.md
ValueError: missing YAML frontmatter
```

両 file とも `# Price-Shock ... Final` で始まる完了レポート形式で、queue/ ではなく done/ に置かれるべきだった。

# 2. 完了条件

1. `.ai/tasks/queue/20260518-1352-price-shock-rev-phase-b1-final.md` を **`.ai/tasks/done/`** へ `git mv`
2. `.ai/tasks/queue/20260518-1457-price-shock-live-shadow-monitor-final.md` を **`.ai/tasks/done/`** へ `git mv`
3. commit: `chore(queue): move misfiled final.md reports from queue/ to done/`
4. push (--no-verify 可、pre-existing demo_trader.py:3253 hook 失敗のため)
5. push 後 30 秒以内に Render worker ログから "missing YAML frontmatter" WARNING が消えていることを final.md に明記

# 3. 司令塔ガード

- [ ] file 内容は **編集しない**。move のみ。
- [ ] 親 task の done file には触れない。
- [ ] queue/ 配下の他 file (20260519-1832-fix-pyr-strategy-attribution-and-dedup, 20260520-bigbeluga-displacement-delta-bt) には触れない。
- [ ] git mv で history 保持。`mv` (UNIX) は禁止。
- [ ] stash 漏れ禁止、git status clean で終了。

# 4. 想定実行時間

5 分以内 (mv 2 件 + commit + push + 確認)。
