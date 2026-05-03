---
id: 20260503-1715-w3-data-prep-gbpjpy-usdjpy-m5-12y
title: W3 Data Prep — Massive 経由で GBPJPY/USDJPY M5 12年 (2014-01-01〜2026-04-30) parquet artifact 化 (W3-3/W3-4 rerun 前提条件)
owner: claude_main
status: queued
priority: P0
created_at: 2026-05-03T17:15:00+0900
roadmap_gate: Wave 3 Tier 2 共通 data prep (W3-3/W3-4 rerun unblocker)
rule: R3
---

# Objective

Wave 3 Tier 2 の 3 タスクが全て同じ blocker で停滞:

- **W3-3** (S4 Connors-Raschke USDJPY M5 12年): CHANGES_REQUESTED — `parent test/ パス scope+M5 12年データ不足`
- **W3-4** (C-1 London Breakout GBPJPY M5 12年): BLOCKED_DATA — local cache 4.09% (184日/4503日)
- **W3-5** (S3 COT Pair-Pool FDR): Phase 1 (CFTC Socrata + yfinance fetch) が DNS 制限で Codex 不可

Codex sandbox は DNS blocked (memory 1112) のため、外部 API fetch は **Claude メイン側 (このセッション)** が Massive MCP / 他 MCP 経由で artifact 化する必要がある。本タスクは **Claude が実働** (例外 — `feedback_claude_codex_division` は通常 Codex=実働だが、network 取得は Claude のみ可能なので例外)。

完了後、W3-3 / W3-4 / W3-5 の Codex rerun が unblock される。

# Hypothesis

**H1** — Massive MCP の `query_data` / `call_api` 経由で GBPJPY/USDJPY M5 2014-01-01〜2026-04-30 (約 4503 日 × 288 bars/day ≈ 1.3M bars/pair) を取得・parquet 化できる。

**H2** — H1 が完了すれば W3-3/W3-4 は同じ seed (`20260503`) で rerun でき、data coverage 100% で Rule 1 の正式判定 (ACCEPT/REJECT/Shadow promote) が出せる。

# Scope

Claude (this session) MAY change:

- `tools/bt/price_cache/GBP_JPY_M5_2014-01-01_2026-04-30.parquet` (new)
- `tools/bt/price_cache/USD_JPY_M5_2014-01-01_2026-04-30.parquet` (new)
- `tools/bt/cot_cache/cot_tff_*.json` (new, 6 pair × CFTC weekly = ~3850 records 合計)
- `tools/bt/price_cache/{USD_JPY,USD_CAD,USD_CHF,GBP_USD,EUR_USD,NZD_USD}_D1_2014-01-01_2026-05-01.parquet` (new, W3-5 用 daily)
- `tools/bt/data_prep_manifest.json` (new) — 全 artifact の source/range/checksum/作成時刻
- `.ai/runs/<new-run-dir>/final.md` (new)
- `.gitignore` (cache 配下が既に存在すれば touch 不要)

Claude MAY NOT change:

- `app.py`, `modules/`, `strategies/`, `wiki/decisions/`, `wiki/index.md`, `wiki/tier-master.md`
- 他タスクの BT スクリプト本体 (`tools/bt/c1_london_breakout.py` など) — 既存 implementation は再利用するだけ
- 本番 DB, OANDA, `.env`, Render production
- 既存の `.ai/tasks/queue/` 内の他タスクファイル

# Required Reading

- `CLAUDE.md` (Rule 3, KB 運用ルール)
- `.ai/runs/20260503-171210-20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt/final.md` (W3-4 BLOCKED_DATA report)
- `wiki/learning/c1-london-breakout-bt-2026-05-03.md` (W3-4 partial verdict)
- W3-3 final report 相当 (project memory `project_w3_3_s4_connors_raschke_queued`)
- `.ai/tasks/queue/20260503-1644-w3-5-s3-pair-pool-fdr-bt.md` (W3-5 Phase 1 仕様)

# Steps (Claude メインセッションでの実働)

1. **Massive MCP discovery**:
   - `mcp__Massive_Market_Data__search_endpoints` で FX OHLC M5 / D1 endpoint 確認
   - `mcp__Massive_Market_Data__get_endpoint_docs` で response schema/rate limit 確認

2. **GBPJPY M5 fetch** (W3-4 用):
   - 2014-01-01〜2026-04-30 range
   - chunked download (例: 6ヶ月 / call) で rate limit 回避
   - parquet 形式で `tools/bt/price_cache/GBP_JPY_M5_2014-01-01_2026-04-30.parquet` に保存
   - schema: `[timestamp, open, high, low, close, volume]` (既存 `c1_london_breakout.py` 互換)

3. **USDJPY M5 fetch** (W3-3 用):
   - 同上、`USD_JPY_M5_2014-01-01_2026-04-30.parquet`

4. **CFTC TFF fetch** (W3-5 Phase 1):
   - Socrata API: `https://publicreporting.cftc.gov/resource/72hh-3qpy.json`
   - 6 pair (USDJPY/USDCAD/USDCHF/GBPUSD/EURUSD/NZDUSD)
   - Date range 2014-01-07〜2026-04-28 (weekly)
   - 各 pair separate JSON: `tools/bt/cot_cache/cot_tff_{pair}_2014-2026.json`
   - Field minimum: `report_date_as_yyyy_mm_dd, change_in_dealer_long_all, change_in_dealer_short_all, market_and_exchange_names`

5. **Daily price fetch** (W3-5 用):
   - yfinance (Massive 経由可なら同), 6 pair, D1, 2014-01-01〜2026-05-01
   - parquet: `tools/bt/price_cache/{pair}_D1_2014-01-01_2026-05-01.parquet`

6. **Manifest 生成**:
   - `tools/bt/data_prep_manifest.json` に各 artifact の (file, source, range, n_bars, sha256, fetched_at_utc) を記録
   - これで W3-3/W3-4/W3-5 の Codex rerun 時に source 検証できる

7. **Sanity check**:
   - Wave 1 USDJPY COT (Wave 1 BT で使用済の値) と新規 fetch で **PF=1.21 ±5%** が再現できるか確認 (W3-5 用 USDJPY だけ)
   - GBPJPY M5 で 2024 年の代表的な London Open (例: 2024-04-01 06:00 UTC〜07:00 UTC) の OHLC が独立 source (yahoo finance UI 等) と ±0.1pip で一致するか目視確認 (sample 1 件)
   - 各 parquet で `n_bars` が **要求 4503 日 × 288 bars/day = 1,296,864 ±5%** に収まるか (週末除外考慮)

# Deliverables

1. 6 parquet (GBPJPY M5, USDJPY M5, 6 pair × D1)
2. 6 JSON (CFTC TFF, 6 pair)
3. `data_prep_manifest.json`
4. `.ai/runs/<run-dir>/final.md` — fetch log + sanity check 結果

# Verdict format (final.md)

```
## Verdict
- Status: [SUCCESS / PARTIAL / FAILED]
- Artifacts: [list of files with N bars + sha256]
- Coverage check: [GBPJPY M5: X% of expected, USDJPY M5: Y%, ...]
- Wave 1 USDJPY COT regression sanity: [PASS/FAIL, PF deviation %]
- Sample OHLC cross-check (yfinance UI): [PASS/FAIL]
- Unblocks: [W3-3 ✓, W3-4 ✓, W3-5 ✓]
```

# Out of Scope

- W3-3/W3-4/W3-5 の BT スクリプト修正 — Claude は data prep のみ。BT 実装は既存
- Codex キューの rerun 起動 — 本タスク完了後にユーザーに報告し、別途 `/fx-run-codex` で起動
- Live/Shadow データの artifact 化 — 本タスクは BT 用 historical data のみ

# Coordination

- 本タスク完了 → 既存 W3-3 task ファイル (done に既存) を copy + rename して新 queue にする (or W3-3-rerun タスクを別途作成)
- W3-4 (done に移動済) を W3-4-rerun として queue 復活
- W3-5 は既存 queue タスクがそのまま使える (`--use-cache-only` flag で Phase 2 のみ実行)

# Pre-reg LOCK

- 全 parquet schema は既存 BT スクリプトと strict 互換 (column 名・dtype・timezone を変更しない)
- 12 年範囲 (2014-01-01〜2026-04-30) の固定。範囲変更時は別タスク
- coverage 95% 以上を SUCCESS の閾値とする (週末除外で 100% は不可能)
