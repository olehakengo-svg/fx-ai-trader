# Sessions Index — 3-Tier Classification

**Purpose**: `sessions/` 配下 55 ファイルを **Rich / Auto-Log / True-Stub** で分類。前回 (初版) は「placeholder 残存 = stub」と短絡し、1-commit 日付ファイルまで削除候補にしていたが、それらは commit log を保持しており MEMORY 参照経路の一部だった。**削除は不可**、本 index で navigation を整理。

最終更新: 2026-05-26

---

## Tier 1 — Rich Sessions (16, narrative あり または ≥50 lines)

**読む価値あり**。テーマ別 grep 推奨。

- [[2026-04-12-session]]
- [[2026-04-13-session]]
- [[2026-04-14-session]] (80 lines, 34 commits)
- [[2026-04-15-session]] (62 lines, 30 commits)
- [[2026-04-16-session]] (51 lines, 19 commits)
- [[2026-04-17-session]] (54 lines, 22 commits)
- [[2026-04-20-session]]
- [[2026-04-21-session]] (542 lines, 101 commits — **最大規模**)
- [[2026-04-22-session]]
- [[2026-04-23-session]] (134 lines, 105 commits)
- [[2026-04-24-session]]
- [[2026-04-25-session]]
- [[2026-05-12-session]] (64 lines, 12 commits)
- [[2026-05-13-session]]
- [[2026-05-14-session]] (60 lines, 50 commits)
- [[2026-05-15-session]] (52 lines, 30 commits)

## Tier 2 — Auto-Log Sessions (12, placeholder 残存だが commit log は valid)

narrative 未記入だが commit 履歴 (2+) を保持。MEMORY 参照経路の一部、**削除禁止**。検索時は commit メッセージで grep。

- [[2026-04-28-session]] (5 commits)
- [[2026-04-29-session]] (8 commits)
- [[2026-04-30-session]] (8 commits)
- [[2026-05-03-session]] (13 commits)
- [[2026-05-05-session]] (8 commits)
- [[2026-05-07-session]] (8 commits)
- [[2026-05-11-session]] (18 commits)
- [[2026-05-18-session]] (13 commits)
- [[2026-05-19-session]] (4 commits)
- [[2026-05-21-session]] (4 commits)
- [[2026-05-25-session]] (6 commits)
- [[2026-05-26-session]] (11 commits)

## Tier 3 — True Stubs (4, 1-commit のみ、placeholder)

1 コミットのみ。それでも MEMORY/decisions の参照経路となるため保持。次の commit を当日 narrative として補完する規律が望ましい。

- [[2026-05-08-session]] — SR-level quality audit (commit 364027e、 MEMORY: `project_sr_weight_phase1_accept_2026_05_11`)
- [[2026-05-10-session]] — phase1b daily re-run (commit 4f2e307、MEMORY: `project_phase1b_oanda_contrarian_bt_2026_05_07`)
- [[2026-05-20-session]] — codex-cloud audit queue (commit 54e659a6)
- [[2026-05-22-session]] — phase1b daily re-run + tz mismatch bug (commit f72ae357)

## Topic Sessions (30, 日次ではないテーマ別ログ)

特定テーマで切られた deep dive session log。

### BT / Live Divergence
- [[bt-live-divergence-scan-2026-04-22]]
- [[bt-live-divergence-v3-full-stack-2026-04-22]]

### Confidence (v10 系)
- [[confidence-formula-root-cause-2026-04-22]]
- [[confidence-q4-full-quant-2026-04-22]]
- [[confidence-q4-paradox-2026-04-22]]
- [[confidence-v10-live-observation-2026-04-22]]

### Design / Diagnose
- [[design-broken-diagnose-2026-05-18]]
- [[five-proposal-parallel-2026-04-22]]

### Handover (引き継ぎ)
- [[handover-2026-04-22]]
- [[handover-shadow-deep-analysis-2026-04-21]]
- [[handover-tp-hit-quant-analysis-2026-04-21]]

### Pre-reg / Prime
- [[prereg-6-prime-strategies-2026-04-21]]
- [[prime-reeval-2026-05-18]]
- [[prime-v2-shadow-audit-2026-05-18]]

### Quant Edge / Shadow / TP Hit
- [[quant-edge-scan-2026-04-23]]
- [[shadow-deep-analysis-2026-04-21]]
- [[shadow-deep-analysis-prereg-2026-04-21]]
- [[task1-shadow-tp-hit-deep-2026-04-21]]
- [[task1-win-dna-2026-04-21]]
- [[tp-hit-causal-deep-2026-04-22]]
- [[tp-sl-deep-mechanics-2026-04-22]]

### VWAP / Virtual Sim
- [[virtual-sim-6-primes-2026-04-21]]
- [[vwap-mr-live-analysis-2026-04-22]]

---

## Hook 自動化案 (将来実装)

session-end hook で以下を実行すれば Tier 3 自然消滅:

```bash
# placeholder + commit ≤ 1 の場合、warning を出して narrative 入力を要請
if grep -q "Claudeが記入" "$today_session" && [ "$(grep -cE '^[0-9]+\. ' "$today_session")" -le 1 ]; then
  echo "WARN: Today's session is a stub. Either write a Phase 1 narrative or commit will be blocked."
fi
```

詳細実装は `scripts/hooks/session-end-save.sh` に追加 (Task #7)。

---

Related:
- [[audit-index]] — KB ↔ MEMORY 双方向ハブ
- [[decisions/index]] — Decisions 84件カテゴリ index
- [[lessons/index]] — Lessons 教訓集
