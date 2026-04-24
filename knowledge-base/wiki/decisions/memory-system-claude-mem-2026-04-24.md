# Memory System 判断: claude-mem 導入 (Option B, On-Demand Search Only)

**Date**: 2026-04-24
**Decision Type**: アーキテクチャ変更（開発ツール層）
**Status**: IMPLEMENTED (Phase 1 install / Phase 2 exclusion 完了)

## 背景

ユーザーから「claude-mem ([thedotmack/claude-mem](https://github.com/thedotmack/claude-mem)) が現システムで有効か、KBと両立できるか」の問い。

現システムは既に以下4層の記憶レイヤーで構成されている:

| 層 | 場所 | 役割 |
|---|---|---|
| KB (Obsidian Vault) | `knowledge-base/` | 手動curation、Tier分類/BT/lesson/decision 等 quant 構造データ |
| .remember/ | プロジェクトroot | session handoff buffer (`now/today/recent/archive/core`) |
| auto memory | `~/.claude/projects/.../memory/` | user/feedback/project/reference 型 |
| session logs | `knowledge-base/wiki/sessions/` | 時系列作業記録（Stop hook 自動保存） |

SessionStart hook で ~30KB、UserPromptSubmit hook で毎ターン ~5KB (`KB_SYNC` + security guidance) を既に注入中。

## claude-mem の仕様（ソース確認済、2026-04-24）

- Claude Code プラグイン (global install via marketplace `thedotmack`)
- **7 Hooks** (plugin/hooks/hooks.json):
  - `Setup *` — smart-install.js（初回のみ、Bun/SQLite/Chroma setup、`~/.claude-mem/` 作成）
  - `SessionStart startup|clear|compact` — 3サブhook: ①smart-install確認 ②worker起動 ③**context注入**
  - `UserPromptSubmit` — session-init
  - `PreToolUse Read` — file-context capture
  - `PostToolUse *` — observation（全tool call capture）
  - `Stop` — summarize
  - `SessionEnd` — session-complete
- **Worker port**: 固定ではなく `$((37700 + UID % 100))` で計算（被らないため）
- **Env override**: `CLAUDE_MEM_WORKER_PORT` / `CLAUDE_MEM_WORKER_HOST` / `CLAUDE_MEM_DATA_DIR`
- Bun 管理 Worker Service、SQLite + Chroma ベクタ DB
- Claude Agent SDK で全 tool call を意味圧縮 → 次 session で過去 observation を自動注入
- 依存: Node 18+, Bun, uv, Claude Agent SDK

## 衝突分析

### HIGH RISK（実害あり）— 衝突
1. **SessionStart hook 二重走行**: claude-mem (user-level) + project `session-start.sh` の両方が実行される。KB auto-load の上に claude-mem observation が載り、コンテキスト予算を圧迫
2. **UserPromptSubmit 二重注入**: 現 `KB_SYNC` に加え毎ターン claude-mem injection → token 消費増
3. **PostToolUse 飽和**: 既存の `post-edit-check.sh` / `post-edit-wiki.sh` / `post-strategy-edit-check.sh` に加え全 tool call capture
4. **Stop/SessionEnd 重複**: `session-end-save.sh` が KB 保存、claude-mem も Agent SDK で summary 生成 → 追加 API 呼び出しコスト

### MEDIUM RISK
- スキーマ不一致: KB は quant 特化 (Tier/EV/WR/Bonferroni)、claude-mem は汎用 tool 操作ログ → 再 curation が必須で自動化メリット薄
- 非決定性: AI 圧縮 summary は seed 依存、監査可能性重視の現方針と相性悪い

### LOW RISK / 補完可能
- Tool-call 粒度の検索（「2026-03-15 に何を編集した？」）は KB に無い機能
- クロスプロジェクト記憶（fx-ai-trader 以外での作業記憶）

## 判断: Option B 採用

**「global install はするが、fx-ai-trader 内では on-demand 検索用途のみに限定」**

### 理由
1. KB の監査可能性・quant 特化スキーマを壊さない
2. 「historical tool-call search」は今の KB に無い機能でデバッグ時に有用
3. クロスプロジェクト利用（scratch 系）で観測価値を確認できる
4. install cost は小さく、設定で hook injection を無効化すれば可逆

### Option 比較
| Option | 内容 | 判断 |
|---|---|---|
| A | global install + fx-ai-trader 除外 | 検索すらできない → 棄却 |
| **B** | **global install + fx-ai-trader で injection hook 無効化、MCP 検索のみ有効** | **採用** |
| C | KB を claude-mem に置換 | 手動 curation で積んだ quant 知見を AI 圧縮に任せるのは月利100%目標に対しリスク高 → 棄却 |

## 実装計画

### Phase 1: Install (user 実行)
```
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem
```
または
```
! npx -y claude-mem install
```
→ Claude Code 再起動

### Phase 2: fx-ai-trader 側で injection 無効化 (Claude 実行) — DONE 2026-04-24
1. ~~`~/.claude-mem/settings.json` の hook injection 設定を確認~~ → 完了
2. ~~project `.claude/settings.json` で claude-mem の SessionStart / UserPromptSubmit hook を上書き無効化、または claude-mem の project-level exclusion 機能を使用~~ → claude-mem 側の native 機能で対応: `~/.claude-mem/settings.json` に `"CLAUDE_MEM_EXCLUDED_PROJECTS": "/Users/jg-n-012/test/fx-ai-trader"` を設定
3. MCP `search` / `timeline` / `get_observations` ツールのみ残す (他プロジェクトのデータを横断検索する用途)

**注意**: `CLAUDE_MEM_EXCLUDED_PROJECTS` は以下 3 hook のみを短絡する:
- `UserPromptSubmit` (session-init)
- `PostToolUse *` (observation)
- `PreToolUse Read` (file-context)

以下 3 hook は**対象外**（ただし capture 済データが無ければ実効空動作）:
- `SessionStart context` — 過去 observation がゼロなので注入内容も空
- `Stop summarize` / `SessionEnd` — 同上

結果: fx-ai-trader では claude-mem の自動注入・capture は発生しない。MCP 検索ツールは他プロジェクトのデータに対してのみ有効。

バックアップ: `~/.claude-mem/settings.json.bak-b1-2026-04-24`

### Phase 3: 動作確認
- [x] `~/.claude-mem/worker.pid` 生存確認 (pid 72034)
- [x] `CLAUDE_MEM_EXCLUDED_PROJECTS` regex マッチ確認 (cwd `/Users/jg-n-012/test/fx-ai-trader` 一致)
- [ ] 次 session 起動時に `KB_SYNC` 以外の自動注入が無いこと確認 (observational)
- [ ] PostToolUse に observation hook 呼び出しログが無いこと確認 (`~/.claude-mem/logs/`)

### Phase 4: 運用ルール確定
- **fx-ai-trader**: KB が single source of truth、claude-mem は他プロジェクトでのみ作動
- **他プロジェクト**: claude-mem 標準運用で可 (scratch/検証プロジェクト等)
- **撤退**: `mv ~/.claude-mem/settings.json.bak-b1-2026-04-24 ~/.claude-mem/settings.json` で即時 rollback

## Success Criteria
- [x] claude-mem worker が稼働 (port は `37700 + uid%100` = 37701)
- [x] fx-ai-trader cwd で `EXCLUDED_PROJECTS` 短絡条件が成立
- [ ] fx-ai-trader 新 session 起動時、KB auto-load 以外の自動注入が発生しない (次 session で observational verification)
- [ ] MCP `search` ツールで他プロジェクトの過去 tool-call を検索可能 (次 session で動作テスト)
- [x] 既存 PostToolUse hook (post-edit-check.sh 等) が壊れていない (本セッションで編集動作確認済)

## リスクと撤退基準
- Context 二重注入が発生（KB_SYNC サイズ > 50KB/ターン）→ Phase 2 再設定
- Worker service がトレード時間帯に port conflict や CPU spike → 即 uninstall
- BT/本番ロジックに claude-mem のログ書き込みが干渉 → uninstall

## Related
- [[claude-harness-design]] — quant analyst harness の基本設計
- [[lessons/index]]
