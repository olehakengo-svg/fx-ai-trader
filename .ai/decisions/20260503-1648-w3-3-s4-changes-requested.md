---
id: 20260503-1648-w3-3-s4-changes-requested
title: W3-3 S4 Connors-Raschke BT — CHANGES_REQUESTED (sandbox scope + data prep blocker)
date: 2026-05-03T16:48:00+0900
verdict: CHANGES_REQUESTED
related_task: .ai/tasks/failed/20260503-1640-w3-3-s4-connors-raschke-80-20-bt.md
related_run: .ai/runs/20260503-164857-20260503-1640-w3-3-s4-connors-raschke-80-20-bt/final.md
rule: R1
---

# Verdict: CHANGES_REQUESTED

Codex 実行は task-mopgysld-71znyk でサンドボックス制約により BLOCKED_BY_SANDBOX_WRITE_SCOPE。Codex は BT を一行も実行せず、判断は正しく Scenario C / Insufficient Data として停止 (no fabrication, `feedback_success_until_achieved` 準拠)。

## ブロッカー (3 つ)

1. **Write scope**: Codex sandbox は `fx-ai-trader/`、`/private/tmp`、`/private/var/folders/.../T`、`~/.codex/memories` のみ書き込み可。タスク仕様が要求した `/Users/jg-n-012/test/tools/bt/`、`/Users/jg-n-012/test/wiki/learning/`、`/Users/jg-n-012/test/data/cache/` は全て書き込み不可。**起票仕様の不備** (Claude 司令塔の責任)。
2. **データ不足**: `fx-ai-trader/data/cache/massive/USD_JPY_5m.parquet` は `2025-10-14..2026-04-15` (約6ヶ月) のみ。タスク要求 `2014-01-01..2026-04-30` (12年) の 80% 以下しか無い → Scenario A 不可能。
3. **LIVE / network 不可**: Codex sandbox は `pgrep` 不可 (sysmond 不在)、Render API DNS 不可、yfinance も同様。fib_reversal correlation / broker cross-check / orphan ガードが Codex 単独では実行不能。

## クオンツ確認

- Rule: R1 → 必要な BT 軸 (N/WR/EV/PF/Wilson/Bonferroni/OOS-WF/Sharpe/Kelly) は **未測定**。判断材料ゼロ。
- BT / Shadow / Live / OANDA の混在: なし (BT 自体が走っていない)。
- 本番 DB / `.env` / OANDA: 触られていない (sandbox 制約で物理的に不可)。
- Gate 進捗: Wave 3 Tier 2 新規 alpha 補充 1/3 は **進まず**。再起票で再開可能。

## 修正方針 (3 軸)

### A. パス scope を fx-ai-trader 配下に揃える

兄弟タスク W3-4 / W3-5 が既に `fx-ai-trader/tools/bt/`、`fx-ai-trader/knowledge-base/wiki/learning/` 規約で起票済み。W3-3 もこれに揃える:

- `tools/bt/s4_connors_raschke.py` (fx-ai-trader 内)
- `knowledge-base/wiki/learning/s4-connors-raschke-bt-2026-05-03.md`
- `knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03.{json,md}`
- (Scenario A 時) `knowledge-base/wiki/decisions/s4-connors-raschke-pre-registration-2026-05-03.md`
- データキャッシュ: `data/cache/massive/USD_JPY_5m_2014_2026.parquet` (既存 cache と同階層)

`/Users/jg-n-012/test/wiki/learning/` の catalog §B-2 と verdict matrix v1 は **読み取り専用参照** に固定。

### B. データ準備を Claude (司令塔) 側でフロント実行

Massive Market Data MCP は Claude Code ホストから呼べるが Codex sandbox からは呼べない。**Claude が先に M5 12年データを fetch** して `fx-ai-trader/data/cache/massive/` に書き込み、Codex はキャッシュを読むだけにする。これが **Phase 0 prerequisite**。

### C. Validity check #2 / #4 を Claude 側に委譲

- fib_reversal LIVE corr (Render API + `pgrep`): Claude が実行し、結果 JSON を `knowledge-base/raw/audits/s4-fib-reversal-live-corr-2026-05-03.json` に焼き付け。Codex はそれを読む。
- yfinance broker cross-check: 同様に Claude が daily-resolution USDJPY=X を fetch して artifact 化。

これにより Codex は完全 offline で BT + null bootstrap + 27-cell grid + cohort 表のみを担当する。

## 次の一手 (1つ)

**Phase 0 — Massive Market Data MCP で USDJPY M5 2014-01-01..2026-04-30 を fetch し、`fx-ai-trader/data/cache/massive/USD_JPY_5m_2014_2026.parquet` に書き出す**

この prerequisite が完了したら W3-3-rerun task を queue に投入。fib_reversal LIVE corr と yfinance cross-check は並行で Claude が artifact 化。
