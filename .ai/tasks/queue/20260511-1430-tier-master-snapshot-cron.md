---
id: 20260511-1430-tier-master-snapshot-cron
title: "[Strategies-UI Follow-up] tier-master 日次 snapshot を Render cron に登録"
owner: codex
status: queued
priority: P3
created_at: 2026-05-11T14:30:00+0900
roadmap_gate: "f6fedeb (feat(strategies-ui)) の follow-up。snapshot ファイルが自動蓄積されないと /strategies 期間比較 UI で実 diff が出ない。手動 backfill より cron 自動化の方が運用負荷低い。"
rule: R3
related:
  - scripts/save_tier_master_snapshot.py
  - render.yaml
  - .github/workflows/
---

# 0. 背景

`f6fedeb feat(strategies-ui): tier-master 日次 snapshot + /strategies 期間比較 UI` で:

- `/api/strategies/status?since=DATE` / `?compare_from=&compare_to=` 期間比較 API 実装済
- `scripts/save_tier_master_snapshot.py` で `knowledge-base/wiki/snapshots/tier-master-YYYY-MM-DD.json` 保存可能
- 受入時点では 2026-05-11 1 ファイルのみ存在

snapshot が日次で自動蓄積されないと:
- ユーザが `?since=2026-05-04` を選んでも `warning: no snapshot available` で diff 出ず
- UX 価値が「今日の snapshot vs 今日の current state」(= no-op) に縮退
- shadow-first quant 文脈で「最近大幅にエッジを更新したか」が見えない元の課題が解決しない

# 1. 仕様

## 1.1 自動実行

**実行頻度**: 1 日 1 回、UTC 00:00 (JST 09:00)
- 既存 cron 機構を踏襲。Render cron ジョブ or GitHub Actions schedule のどちらか
- 既存実装パターンを `render.yaml` / `.github/workflows/` で確認、同形式で追加

**コマンド**:
```bash
python3 scripts/save_tier_master_snapshot.py
```
引数なしで実行 → 今日の UTC 日付で snapshot 保存。

**git commit/push**:
- snapshot ファイルは `knowledge-base/wiki/snapshots/` 配下、コミット対象
- 既存 `auto: KB session-end save` / `data(bt): phase1b daily re-run` の auto-commit 機構と同形式
- コミットメッセージ: `auto: tier-master snapshot YYYY-MM-DD`

## 1.2 既存 cron との衝突確認

- `scripts/oanda_sentiment_cron.py` (毎時 hourly run、memory: project_phase1b_oanda_contrarian_bt_2026_05_07)
- phase1b BT daily re-run (06:34 local = JST?)
- KB session-end save (post-commit hook 経由、別系統)

新規 cron は UTC 00:00 固定で他と独立、衝突なし。

# 2. 受入基準

- [ ] Render cron job ないし GH Actions workflow が UTC 00:00 daily で `scripts/save_tier_master_snapshot.py` を実行
- [ ] 実行ログから snapshot file 生成確認
- [ ] 翌日以降、`knowledge-base/wiki/snapshots/tier-master-YYYY-MM-DD.json` が自動コミット & push される
- [ ] `/strategies` で `?since=2026-05-11` (= 初日) との比較が実 diff を返すか確認 (動的検証)
- [ ] cron 失敗時の通知経路 (既存 Sentry or Discord) に乗っているか確認

# 3. 非ゴール

- 過去日 snapshot のバックフィル (git history から `tier-master.json` の過去版を抜く処理は本タスクでは不要、将来別タスク)
- snapshot retention 制限 (今は無制限で良い、4MB 未満/年)
- snapshot diff の他用途流用 (KB index 更新等)

# 4. 実装ヒント

- `render.yaml` に既存 cron が定義されていれば同形式で追加
- GH Actions の場合は `.github/workflows/save-tier-master-snapshot.yml` 新規作成 (cron + checkout + python + commit + push)
- スクリプト自体は `git add` / `git commit` / `git push` を内包しないので、workflow 側で git 操作する
- 既存 `data(bt): phase1b daily re-run` 系のワークフローがあればそれを参照、最小 diff で済む

# 5. クオンツ的注意

- snapshot 自動コミットで main の commit 履歴が 1 日 1 件増える。既存 auto-commit ノイズと同レベル
- snapshot 内容は `tier-master.json` のコピーなので統計的に厳しい審査は不要 (UI 用 baseline)
- ただし `tier-master.json` 自体が更新された直後 (cell_edge_audit 反映等) のタイミングで snapshot を取ると、その日の baseline が "更新済" になる。これは仕様として許容 (元々日次の点描)
