---
title: autopilot クラウド・ギャップフィラー Routine 新設 — ローカル Mac 依存の解消
date: 2026-09-17
type: decision
status: ACTIVE (初回発火 2026-09-18 で検証)
related: [[claude-codex-division-of-labor-2026-07-02]], [[lesson-bsd-stat-cloud-hook-blackout-2026-09-14]]
---

# autopilot クラウド・ギャップフィラー Routine (2026-09-17、user 承認「推奨で進めて」)

## 背景

- Claude 自律実行の全経路 (fx-roadmap-autopilot 毎日 10:01 JST、fx-daily-quant-loop、wiki-daily-update 等) は
  **ローカル Mac アプリ起動中のみ実行**される scheduled task だった
  ([[claude-codex-division-of-labor-2026-07-02]] が機構的弱点として明文化。wiki-daily 06-26〜07-01 の 6 日欠落が実例)
- 2026-09-14 の棚卸しでクラウドセッション側の KB 注入フック全損も発見・修理済み (PR #255、
  [[lesson-bsd-stat-cloud-hook-blackout-2026-09-14]])。これでクラウドセッションが KB 規律下で動く前提が整った

## 決定

claude.ai の Routine (クラウド側スケジューラ) に **日次ギャップフィラー**を新設した。
Mac が起動していれば何もしない。起動していなかった日だけ autopilot の代役を務める。

| 項目 | 値 |
|---|---|
| Trigger ID | `trig_01SYbHe1n9GmvBnLBhoq3bKX` |
| スケジュール | 毎日 UTC 04:00 = **JST 13:00** (ローカル autopilot 10:01 JST の 3 時間後) |
| 実行形態 | 発火ごとに新規クラウドセッション (fresh session) |
| 発火主体 (到達経路) | claude.ai Routines (アカウント側)。停止/編集は claude.ai の Routines UI から可能 |

## 動作設計 (プロンプトに組込み済み)

1. **stand-down 条件**: 当日 (JST) の main コミット / session log に autopilot 実行痕跡があれば
   **何もせず終了** (コミット・PR・KB 変更なし) — ローカルとの二重発火を構造的に防ぐ
2. 痕跡がなければ roadmap 未完了項目から **Rule 2 / Rule 3 で実行可能な 1 タスクのみ**完遂
   (KB 必読 → 分析→判断→実装 → rule タグ付きコミット → PR → CI green → 自走マージ)。
   **Rule 1 事項は実行禁止・起票のみ** (roadmap v2.3 の autopilot 権限と同一)
3. **user 決裁事項は不可侵**: Render env var 操作 / `shadow_demote_registry.py` の human-approved 編集は
   数値根拠付き起票のみ
4. レース対策: first-to-main 原則、session log は union 解決、マージ直前に origin/main 再取得

## 制約 (既知)

- **MASSIVE_API_KEY はクラウドに存在しない** (prereg registry の execution_subject 記載どおり local-.env only)。
  ローカル BT キャッシュ更新が必要なタスクは選ばず、コミット済みキャッシュ + 本番 API を使う。
  スキップした候補は報告に明記する仕様
- **claude.ai コネクタ未格納**: Routine 作成時に「stores no MCP connectors」警告あり。発火セッションは
  claude.ai コネクタ (mcp__<server>__*) なしで走る。git push / PR 操作は CCR 基盤経路で動く想定だが、
  **初回発火 (2026-09-18 JST 13:05 頃) の実走で検証すること**。不足があれば claude.ai の Routines UI から
  再作成する (UI 作成ならコネクタを付与できる)

## 検証計画

- 初回発火後に確認: (a) stand-down 判定が正しく効いたか、(b) 代役実行時に PR 作成〜マージまで完走できたか
- 失敗時は `list_triggers` の last_run と発火セッションのトランスクリプトで診断し、本ページに追記
