---
id: 20260504-0050-s6-w1p0-production-rerun
title: S6 W1P0 Chart Pattern Detector — Production Run 再実行 (M5 cache seed 後)
owner: codex
status: queued
priority: P0
created_at: 2026-05-04T00:50:00+0900
roadmap_gate: Wave 1 Phase 0 — chart pattern strategy family の signal inventory 確立 (Gate 1 Kelly Half 前提)
rule: R1
prereq_artifacts:
  - data/cache/massive/USD_JPY_5m.parquet  # 22 MB / W3 phase 0 で取得済 + 2026-05-04 worker 永続 disk に seed 完了
  - tools/s6_chart_pattern_detector.py     # 12 pattern detector + ATR + swing pivot + bar-close gate + SL/TP + SQLite DDL (commit acf12e4)
  - tools/s6_run_w1p0.py                    # parquet → detector → SQLite insert-or-ignore driver
  - tests/test_s6_chart_pattern_detector.py # 29 tests / synthetic + fixture replay
  - tests/fixtures/manual_chart_pattern_labels.csv  # 30 行 deterministic fixture
related:
  - .ai/tasks/done/20260503-1900-s6-chart-pattern-detector-w1p0.md  # 前回タスク (NEEDS_MORE_EVIDENCE — production parquet 不在で blocked)
  - knowledge-base/wiki/strategies/s6-chart-pattern.md
  - knowledge-base/wiki/decisions/s6-w1p0-detector-2026-05-03.md
  - fx-ai-trader-codex-runner README + docs/data-seeding.md  # 当該 cache の seed 経路
---

# Hypothesis (仮説)

S6 chart pattern detector (12 patterns / Linda Raschke + Bulkowski + 古典 reversal/continuation) は USDJPY M5 12.3年 (903,828 bars 想定) で **signal inventory を生成可能**であり、各 pattern が **bar-close gate + dedup** を経た上で SQLite に重複なく保存される。

**ロードマップ前進条件** (この W1P0 が達成すべきこと):
1. 12 pattern 全てが production data で signal を出す (= synthetic fixture と production の dynamics 乖離が致命でない)
2. 合計 signal count が ≥ 5000 (12年 M5 で sparse すぎるなら detector parameters 不適)
3. SQLite UNIQUE index (pair, pattern, timestamp, direction) が PK 違反 0 件 = bar-close gate の dedup が production でも機能
4. 既存 30-row fixture replay は **不変** (regression なし)

これらが揃えば **W1P1 (signal validity audit) → W1P2 (BT) → W1P3 (Bonferroni 12-test) → Wave 4 strategy 化** のパイプラインを通せる。1 つでも欠ければ detector 設計に戻る。

# Detector specification (PRE-REGISTERED, do not modify)

- 入力: `data/cache/massive/USD_JPY_5m.parquet` (M5 OHLC, columns: timestamp UTC, open, high, low, close, volume)
- 出力: `knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite`
  - schema は `tools/s6_chart_pattern_detector.py` の DDL を流用 (変更禁止)
  - PRIMARY KEY: (pair, pattern, signal_ts_utc, direction)
- pair: USD_JPY (W1P0 single pair; multi-pair は W1P2 以降)
- 12 patterns (固定リスト, 順序不問):
  `head_and_shoulders`, `inverse_head_and_shoulders`, `double_top`, `double_bottom`,
  `triple_top`, `triple_bottom`, `bull_flag`, `bear_flag`,
  `ascending_triangle`, `descending_triangle`, `rising_wedge`, `falling_wedge`
- bar-close gate: 最終 closed bar (live mode `closed_idx=-2`) でのみ emit
- dedup key: (pair, pattern, signal_ts_utc, direction) — re-detection で同 key の duplicate insert は **OR IGNORE**
- ATR period 14, swing pivot ≥3 bars on each side (existing detector defaults; 触らない)

# 採用 / 保留 / 棄却基準 (verdict matrix)

| 条件 | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT |
|---|---|---|---|
| 12 pattern 中の non-zero count | 12/12 | 9-11/12 | ≤ 8/12 |
| 合計 signal count | ≥ 5,000 | 1,000 ≤ x < 5,000 | < 1,000 |
| SQLite PK 違反 | 0 | (該当なし — 0 でない時点で REJECT) | ≥ 1 |
| 30-row fixture replay | 全 hit 一致 | (該当なし — 一致しない時点で REJECT) | 1 row でも mismatch |
| pytest tests/test_s6_chart_pattern_detector.py | 29/29 PASS | — | < 29 |

`ACCEPT` = 全条件クリア / `NEEDS_MORE_EVIDENCE` = pattern count か signal count が中間域 / それ以外は `REJECT`。

# データ分離 (重要)

- 本タスクは **BT ではない**。signal inventory 生成のみ。Live PnL や Shadow PnL とは独立。
- SQLite 出力先は `knowledge-base/raw/bt-results/` 配下 (BT 結果と同居だが detector inventory ファイル名で区別)
- 本番 DB (`/var/data/*.db` on Render fx-ai-trader main service) は一切触らない
- ローカル DB (`/Users/jg-n-012/test/fx-ai-trader/demo.db` 等) も触らない

# 統計条件 (W1P0 では不要、W1P2 以降の参照)

W1P0 は inventory 生成のみのため、Wilson / Bonferroni / OOS-WF / Kelly は **本タスクでは検証しない**。次の W1P1 (signal validity audit) で各 pattern の labelled outcome を取得し、W1P2 で BT による PF/Wilson/Bonferroni を取る設計。本タスクで signal count `N` が判明することで、後続 BT で必要な Bonferroni m が決まる (m=12 または m=non_zero pattern count)。

# 月利 100% ロードマップへの寄与

- Gate 1 (Kelly Half) 達成のためには **alpha source 多様化**が必要 (S2/S3/S4 だけでは collinearity)
- chart pattern family は existing strategies (MR/breakout/scalp) と異なる **構造的 alpha source** 候補 (Bulkowski の実証 PF 1.5+ がある patterns あり)
- 本 W1P0 が ACCEPT すれば W1P1 → W1P2 → W1P3 → Wave 4 promotion path に乗る
- もし REJECT なら detector 設計を見直すか chart pattern family を Wave 5 以降に押し下げる判断材料

# 検証コマンド (Codex 必須実行)

実行順:

```bash
cd /data/repo/fx-ai-trader

# 1. 既存 unit tests が green であることを再確認 (regression check)
python3 -m pytest tests/test_s6_chart_pattern_detector.py -v
# 期待: 29 passed

# 2. M5 parquet が読めるか sanity check
python3 -c "
import pandas as pd
df = pd.read_parquet('data/cache/massive/USD_JPY_5m.parquet')
print(f'shape={df.shape}')
print(f'columns={list(df.columns)}')
print(f'time_range={df.iloc[0,0]} -> {df.iloc[-1,0]}')
"
# 期待: shape (≥800k, ≥6), 列に open/high/low/close, time range が 12 年以上

# 3. Production run
python3 tools/s6_run_w1p0.py \
  --parquet data/cache/massive/USD_JPY_5m.parquet \
  --output knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite \
  --pair USD_JPY

# 4. SQLite signal count per pattern
python3 -c "
import sqlite3
conn = sqlite3.connect('knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite')
print('=== signal counts per pattern ===')
for row in conn.execute('SELECT pattern, COUNT(*) FROM signals GROUP BY pattern ORDER BY COUNT(*) DESC'):
    print(f'  {row[0]:30s} {row[1]:>8d}')
total = conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
print(f'TOTAL: {total}')
"

# 5. PK uniqueness check
python3 -c "
import sqlite3
conn = sqlite3.connect('knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite')
dup = conn.execute('SELECT pair, pattern, signal_ts_utc, direction, COUNT(*) c FROM signals GROUP BY 1,2,3,4 HAVING c > 1 LIMIT 5').fetchall()
print(f'PK duplicates: {len(dup)}')
"
# 期待: 0

# 6. 30-row fixture replay (regression)
python3 -m pytest tests/test_s6_chart_pattern_detector.py::test_fixture_replay -v
# 期待: PASS
```

# 出力すべきレポート (codex `--output-last-message` に書く内容)

タスク完了時、Codex は以下を `last_message` に出すこと:

1. **Verdict**: ACCEPT / NEEDS_MORE_EVIDENCE / REJECT のいずれか
2. **Pattern signal count table** (12 行、降順)
3. **Total signal count**
4. **PK violations**: 0 のはず
5. **Fixture replay status**: PASS / FAIL
6. **次にやるべきこと** (W1P1 への引き継ぎ): どの pattern が 0 hit か、N が小さい pattern はどれか、後続 BT で Bonferroni m をいくつにするか

# 禁止事項

- ❌ `.env`, OANDA API key, OPENAI API key を読む / 書く / log に出す
- ❌ `modules/`, `app.py`, `strategies/` を編集 (Live promotion は W1P3 後)
- ❌ 本番 DB (Render `/var/data/*.db`) への接続
- ❌ ローカル DB (`demo.db` 等) への書き込み
- ❌ 既存の未 commit 変更を上書き / stash / discard
- ❌ `data/cache/massive/*.parquet` を編集 / 削除 (read-only)
- ❌ `git push` / `git rebase --onto` 等の history rewrite (worker は通常 commit のみ)

# Rule R1 verification (新 inventory 投入)

- 365日 BT スキップ可 (本タスクは inventory 生成、BT は W1P2)
- pre-registration は本ファイルの "Detector specification" セクションが LOCK
- post-hoc に detector parameters / pattern list / SQLite schema を変更した場合、verdict は強制 INVALID

# 参考: 前回 (2026-05-03) の状況

前回タスク `20260503-1900-s6-chart-pattern-detector-w1p0.md` は以下で BLOCKED:

- ❌ `data/cache/massive/USD_JPY_5m.parquet not found` ← worker container clone が `.gitignore` 配下 cache を pull しなかったため
- ✅ `python3 tools/s6_chart_pattern_detector.py --self-test` PASS
- ✅ `python3 -m pytest -q tests/test_s6_chart_pattern_detector.py` 29 passed
- ✅ `python3 -m py_compile tools/s6_run_w1p0.py` PASS

**2026-05-04 解消済み**:
- M5 cache (USDJPY 22MB / GBPJPY 24MB) を fx-codex-runner worker `/data/repo/fx-ai-trader/data/cache/massive/` に手動 seed (private GitHub Release `m5-cache-2026-05-04` 経由)
- worker startup hook (`install_target_deps`) が requirements.txt から pytest/pandas/numpy 等を install 済 → `python3 -m pytest` も使える

これで前回の 2 ブロッカーが両方とも解消された。今回は **production run が初めて完走**することを期待する。
