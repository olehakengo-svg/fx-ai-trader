---
description: List queued Codex tasks for fx-ai-trader
---

# FX Tasks

対象repoは必ず `/Users/jg-n-012/test/fx-ai-trader`。

次を実行して Codex 側のキューを一覧表示する:

```bash
cd /Users/jg-n-012/test/fx-ai-trader
./tools/ai_run_codex.sh --list
```

出力を日本語で整理して報告する。実装や Codex 実行はしない。

## 報告形式

- 番号
- priority
- Rule
- Gate
- status
- title
- 推奨実行順

## クオンツ確認

- P0/P1 と Rule 3 構造バグを優先する。
- Rule 1 は `N`, `WR`, `EV`, `PF`, `Kelly`, `Wilson lower`, `Bonferroni`, `OOS/WF` の検証条件を意識する。
- `BT` / `Shadow` / `Live is_shadow=0` / `OANDA` の混在リスクを明記する。
- 報告は必ず日本語で行う。
