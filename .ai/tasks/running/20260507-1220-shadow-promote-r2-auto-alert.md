---
id: 20260507-1220-shadow-promote-r2-auto-alert
title: "[R2-Auto-Alert] SHADOW_PROMOTE=1 戦略のデータ汚染検知 monitoring tool"
owner: codex
status: queued
priority: P0
created_at: 2026-05-07T12:20:00+0900
roadmap_gate: "R2 auto-demotion gate 不在問題 — 61戦略 SHADOW_PROMOTE=1 投入後のデータ汚染リスク即時封じ"
rule: R3
related:
  - knowledge-base/wiki/lessons/feedback_shadow_first_quant_architecture.md
  - knowledge-base/wiki/lessons/lesson-shadow-always-emit-cleanup-2026-04-28.md
  - tools/post_promotion_watchdog.py
  - tools/auto_force_demoted_recovery.py
---

# 0. 背景と目的

2026-05-07 に W4-Shadow-Redesign v2 の paradigm fix で **61戦略 (Round 1+2 既設定 16 + Round 3 新規 45) を SHADOW_PROMOTE=1** で本番投入。

**問題**: 既存の R2 demotion gate (`strategies/daytrade/__init__.py:205` の `SHADOW_ALWAYS_STRATEGIES`) は **ハードコード集合**。EV<0 を検出しても **自動除外しない** 。`post_promotion_watchdog.py` は read-only 警告のみ。

**KB 教訓** (`feedback_shadow_first_quant_architecture` + `lesson-shadow-always-emit-cleanup-2026-04-28`):
> 無条件 emit 設計は EV<0 で自動的にデータ汚染源化する。SHADOW_ALWAYS 等の bypass 機構には必ず R2 自動 demotion gate を併設する。

**本タスクの目的**: 新規 61戦略の Live shadow trade を 6h ごとに監査、EV<0 / N>=10 cell を検出して Discord alert。**コード自動編集はしない** (read-only)。

# 1. 仕様

## 1.1 入力

- **対象戦略リスト**: SHADOW_PROMOTE=1 env が設定された全戦略
  - 取得方法: `os.environ` を grep して `*_REDESIGN_V2_SHADOW_PROMOTE=1` を抽出
  - もしくは `strategies/*/__init__.py` の `split_shadow_always` 内 env チェック箇所を静的に走査
  - 期待件数: 61 (記録時点)

- **データソース**: Render 本番 API `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
  - `is_shadow=1` のみ抽出
  - 過去 30日間の shadow trade

## 1.2 集計

各 (strategy, instrument) セルで:
- N (trade count, completed only — pnl_pips が NULL でないもの)
- EV (mean of pnl_pips)
- WR (wins / N)
- PF (gross_win_pips / gross_loss_pips)
- Wilson lower (Z=1.96 で簡易、95% CI)

## 1.3 警報判定

```python
if N >= 10 and EV < 0:
    severity = "WARN" if N < 30 else "CRITICAL"
    alert(strategy, instrument, N, EV, severity)
```

- WARN: N=10〜29 (早期警報、観測継続)
- CRITICAL: N>=30 (R2 demote 候補確定、要手動対応)

## 1.4 出力

1. **Markdown report**: `knowledge-base/raw/audits/shadow-promote-r2-alert-{YYYYMMDD-HHMM}.md`
   - 全 61 戦略の per-cell EV/N/WR/Wilson
   - WARN / CRITICAL 該当 cell リスト
   - R2 demote 推奨アクション (env 削除コマンド + コード編集箇所)

2. **JSON**: `--json` flag で stdout に構造化出力 (Discord bot が消費可能形式)

3. **Discord alert** (CRITICAL のみ): 既存 Discord MCP / webhook 経由
   - WARN は report 記録のみ、alert 出さない (ノイズ防止)

4. **exit code**:
   - 0: 全 cell OK
   - 1: 1件以上 CRITICAL (CI/scheduled task で fail として扱う)
   - 2: ネットワーク / API エラー

## 1.5 禁止事項 (read-only 厳守)

- ❌ Render env vars の自動削除
- ❌ `strategies/*/__init__.py` の自動編集
- ❌ tier-master.json / KB 同期書き込み
- ❌ 本番 DB 直接アクセス (Render API のみ)
- ✅ Markdown report 生成のみ allowed
- ✅ Discord alert (CRITICAL only) allowed

# 2. 実装

## 2.1 新規ツール

`tools/shadow_promote_r2_alert.py`

設計:
- `tools/post_promotion_watchdog.py` をテンプレートに参照 (同じ API client + Wilson 計算)
- `tools/auto_force_demoted_recovery.py` を参照 (環境 env vars 走査 pattern)
- XAU 除外ルール (`feedback_exclude_xau`) を必ず適用 — XAU instruments を skip

## 2.2 失敗テスト (TDD)

`tests/test_shadow_promote_r2_alert.py`:
- 合成 trades fixture (synthetic shadow trade セット) で WARN/CRITICAL 判定の境界条件
- N=9 → no alert
- N=10 EV=-1.0 → WARN
- N=30 EV=-0.5 → CRITICAL
- N=30 EV=+0.5 → no alert
- network error → exit 2
- empty trades → exit 0

## 2.3 スケジュール

- Render Cron Job として 6h ごと (00:00, 06:00, 12:00, 18:00 UTC)
- もしくは scheduled-tasks MCP 経由
- 後者推奨 (Render side で別 service 不要)

# 3. クオンツ条件 (Rule 1/2/3 整合)

- **Rule 3 (構造バグ)**: 自動 demotion gate 不在は構造的データ汚染リスク → 即時 monitoring 整備
- **Rule 2 (Fast & Reactive)**: WARN N>=10 で人間の判断介入準備、CRITICAL N>=30 で R2 demote 即断
- **Rule 1 適用外**: 本タスクは monitoring tool の追加であり、戦略 promotion 判断ではない

# 4. データ分離

- BT: 不使用 (read-only Live shadow audit のみ)
- Shadow: is_shadow=1 のみ集計
- Live: is_shadow=0 は除外
- OANDA: 関与しない

# 5. Acceptance Criteria

- 新規ツール `tools/shadow_promote_r2_alert.py` 動作 (smoke test pass)
- 失敗テスト緑 (合成 fixture 判定 6パターン)
- 1回の実 API 実行で `knowledge-base/raw/audits/shadow-promote-r2-alert-2026-05-07-{HHMM}.md` 生成
- 報告に CRITICAL 件数 / WARN 件数 / OK 件数を含む
- exit code 整合性確認

# 6. Out of Scope

- 自動 demotion 実装 (env 削除 / SHADOW_ALWAYS_STRATEGIES 編集) — 別 task
- Bonferroni 補正下の formal promotion judgement — Wave 5 spec で扱う
- 過去データ遡及 monitoring — 直近 30日のみ

# 7. Notes

- `post_promotion_watchdog` は同期ロジックが似ているが、対象が異なる (PAIR_PROMOTED 2 cells vs SHADOW_PROMOTE=1 61 戦略)
- 既存 `tools/auto_force_demoted_recovery.py` が「FORCE_DEMOTED → 復帰」方向なので、本タスクは逆向き「SHADOW_PROMOTE → demote 警告」
- Discord MCP 経由通知は env `DISCORD_WEBHOOK_URL` が無ければ stdout fallback
