---
id: 20260504-0125-s6-w1p1-signal-validity-audit
title: S6 W1P1 — Chart Pattern Signal Validity Audit (outcome labeling on 22,094 signals)
owner: codex
status: queued
priority: P0
created_at: 2026-05-04T01:25:00+0900
roadmap_gate: Wave 1 Phase 1 — chart pattern signal の predictive power 計測 (Gate 1 Kelly Half 前提)
rule: R1
prereq_artifacts:
  - knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite  # 22,094 signals / 12 patterns x 2 dir / 2014-01-02 ~ 2026-04-30 / W1P0 inventory
  - data/cache/massive/USD_JPY_5m.parquet  # 903,828 bars / 12.3y / outcome 計測の 5m bar source
  - tools/s6_chart_pattern_detector.py  # 信号生成ロジック (entry/sl/tp 単価は signal 行に既に格納済)
related:
  - .ai/decisions/20260504-0125-s6-w1p0-inventory-manual-promote.md  # W1P0 を ACCEPT promote した経緯
  - .ai/tasks/done/20260504-0050-s6-w1p0-production-rerun.md  # W1P0 task (REJECT-but-promoted)
  - knowledge-base/wiki/strategies/s6-chart-pattern.md
---

# Hypothesis (仮説)

W1P0 で生成された 22,094 signals (12 patterns × 2 directions, 12.3 年 USDJPY M5) は **ランダムなパターンマッチではなく、TP / SL / time-out の outcome 分布に統計的偏り**を持つ。具体的に:

- **少なくとも 6 / 12 patterns が hit_rate > 50%** (= ランダム 50/50 を超える predictive power)
- bull/bear pair (例 double_top SELL / double_bottom BUY) の hit_rate が **対称に近い** (構造的整合)
- triple_top / triple_bottom (N=142, N=155) は **N が小さすぎて W1P2 BT には統計力不足**であることが定量化される
- **outcome 分布**: TP hit / SL hit / time-out (= max bar 経過後 forced exit) / data-missing が 4 カテゴリに整理される

これらが揃えば W1P2 (full BT with PF/Wilson/Bonferroni) を **どの patterns で / どの N で / どの Bonferroni m で** 走らせるかの根拠が揃う。

# 仕様 (PRE-REGISTERED, do not modify)

## Outcome 計測ロジック (Rule 1: outcome labeling)

各 signal について、`signal_ts` (= signal_ts_utc) 直後の M5 bar から **forward-walk** し、以下の最初に発生したイベントで outcome を決定する。

| Outcome | 条件 | Label |
|---|---|---|
| TP_HIT | bar の `low <= tp_px <= high` (BUY direction では `tp_px` は entry より上、SELL では下) | `TP` |
| SL_HIT | bar の `low <= sl_px <= high` | `SL` |
| TIME_OUT | TP/SL いずれも触らずに `MAX_HORIZON_BARS = 288` (= 24h M5) を経過 | `TO` |
| DATA_MISSING | parquet に signal_ts 以降の十分な bar が存在しない (= 期間末尾の signals) | `DM` |

**同一 bar 内 TP-SL 同時 hit** の場合: **conservative 取扱い** = `SL` (= unfavorable に丸める)。理由: M5 内 path 不明なので worst-case を採用、これにより hit_rate が過小評価されることを許容 (false positive を排除)。

**MAX_HORIZON_BARS = 288** の根拠: 24h を超える持ち越しは intraday strategy の想定外 (S2 Donchian breakout も実装で 24h cap を入れている)。後続 W1P2 BT で horizon を可変にすれば残りの outcome 分布も取れる。

## 出力 schema

W1P0 SQLite (`s6-w1p0-production-2026-05-04.sqlite`) を **不変**に保ち、W1P1 結果は同一 DB に**新テーブル** `chart_pattern_outcomes` を追加する:

```sql
CREATE TABLE chart_pattern_outcomes (
    signal_id INTEGER PRIMARY KEY,                   -- chart_pattern_signals(id) を FK 参照
    outcome TEXT NOT NULL CHECK (outcome IN ('TP','SL','TO','DM')),
    exit_ts TEXT,                                    -- TP/SL hit bar の timestamp、TO は horizon 末尾、DM は NULL
    bars_held INTEGER NOT NULL,                      -- signal_ts から exit までの bar 数
    pnl_pips REAL,                                   -- (exit_px - entry_px) * direction sign / 0.01 (USDJPY)
    audited_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(signal_id) REFERENCES chart_pattern_signals(id)
);
CREATE INDEX idx_cpo_outcome ON chart_pattern_outcomes(outcome);
```

## 集計 (Codex が `last_message` に出力するもの)

```sql
-- summary 1: pattern x direction x outcome
SELECT s.pattern_name, s.direction, o.outcome, COUNT(*)
FROM chart_pattern_signals s
JOIN chart_pattern_outcomes o ON o.signal_id = s.id
GROUP BY s.pattern_name, s.direction, o.outcome
ORDER BY s.pattern_name, s.direction, o.outcome;

-- summary 2: hit_rate per (pattern, direction) where DM excluded
WITH base AS (
  SELECT s.pattern_name, s.direction, o.outcome
  FROM chart_pattern_signals s JOIN chart_pattern_outcomes o ON o.signal_id = s.id
  WHERE o.outcome != 'DM'
)
SELECT pattern_name, direction,
       SUM(CASE outcome WHEN 'TP' THEN 1 ELSE 0 END) AS tp,
       SUM(CASE outcome WHEN 'SL' THEN 1 ELSE 0 END) AS sl,
       SUM(CASE outcome WHEN 'TO' THEN 1 ELSE 0 END) AS to_,
       COUNT(*) AS n_total,
       1.0 * SUM(CASE outcome WHEN 'TP' THEN 1 ELSE 0 END) / COUNT(*) AS hit_rate
FROM base
GROUP BY pattern_name, direction;
```

## 採用 / 保留 / 棄却基準 (W1P1 verdict matrix)

| 条件 | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT |
|---|---|---|---|
| 22,094 signals 全件に outcome label が付く (TP/SL/TO/DM のいずれか) | ≥ 99% (DM ≤ 1%) | 95-99% | < 95% |
| TP+SL+TO の合計 (= DM 除外後) | ≥ 21,800 | 20,000-21,800 | < 20,000 |
| 12 patterns 中、hit_rate > 50% を満たすもの | ≥ 6 | 3-5 | ≤ 2 |
| bull/bear pair の hit_rate 対称性 (例 double_top SELL hit_rate と double_bottom BUY hit_rate の差) | 全 6 ペアで diff ≤ 10% | 4-5 ペアで diff ≤ 10% | 3 ペア以下 |
| `pnl_pips` 中央値が pattern 全体で正 (BUY/SELL 通算) | ✓ | (該当なし) | ✗ |

`ACCEPT` = 全条件クリア → W1P2 BT 設計に進む / `NEEDS_MORE_EVIDENCE` = 中間 (例: pattern によっては outcome 分布が薄い) → 当該 pattern を W1P2 から除外する案を W1P2 task spec で書く / `REJECT` = signal 全体に predictive power がない (= chart pattern family は Wave 5 以降に格下げ)。

# データ分離 (重要)

- 本タスクは **BT ではない**。outcome labeling のみ。Live PnL や Shadow PnL とは独立。
- 入力 SQLite (`s6-w1p0-production-2026-05-04.sqlite`) は read-only であり、`chart_pattern_signals` テーブルは **絶対に更新しない**。新テーブル `chart_pattern_outcomes` の追加のみ。
- 本番 DB (`/var/data/*.db` on Render fx-ai-trader main service) は一切触らない。
- ローカル DB (`/Users/jg-n-012/test/fx-ai-trader/demo.db` 等) も触らない。
- M5 cache (`data/cache/massive/USD_JPY_5m.parquet`) は read-only。

# 統計条件

- N: 各 pattern × direction で N が出力される (signal 数)
- WR (= hit_rate): TP / (TP + SL + TO) で計算 (DM 除外、TO は SL と同じく失敗扱い)
  - **この WR は raw signal の "TP 到達率"** であり、PF/Kelly に直結する true win rate ではない (W1P2 で BT 化して取る)
- EV / PF / Kelly / Wilson lower / Bonferroni / OOS / WF: **本タスクでは計算しない** (W1P2 task の責務)
- 1000-bootstrap や Monte Carlo: **本タスクでは不要** (W1P2 で実施)

W1P1 が出すのは **labelled dataset** であり、統計検定はしない。`hit_rate` を見るだけ。

# 月利 100% ロードマップへの寄与

- W1P0 (signal生成) → **W1P1 (本タスク: outcome labeling)** → W1P2 (full BT) → W1P3 (Bonferroni m=12 or 24) → Wave 4 promotion
- Gate 1 (Kelly Half) 達成のため新 alpha source family を整備する道
- W1P1 で hit_rate < 50% の patterns を早期除外できれば、W1P2 BT の compute cost を削減できる (Bonferroni m が小さくなる → 検出力 up)
- 月利 100% に対する寄与: chart pattern が ACCEPT なら Wave 4 で平均 PF 1.3 alpha source が 6+ 種追加見込み

# 検証コマンド (Codex 必須実行)

実行順:

```bash
cd /data/repo/fx-ai-trader

# 1. parquet と SQLite が読めるか sanity check
python3 -c "
import pandas as pd, sqlite3
df = pd.read_parquet('data/cache/massive/USD_JPY_5m.parquet')
print(f'parquet shape={df.shape}')
con = sqlite3.connect('knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite')
n = con.execute('SELECT COUNT(*) FROM chart_pattern_signals').fetchone()[0]
print(f'signals N={n}')
"
# 期待: parquet shape (903828, 7), signals N=22094

# 2. W1P1 audit script 実装 (Codex が新規作成、tools/ 配下)
#    → tools/s6_w1p1_outcome_audit.py を作る
#    使い方: python3 tools/s6_w1p1_outcome_audit.py \
#      --parquet data/cache/massive/USD_JPY_5m.parquet \
#      --signals knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite \
#      --output  knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite \
#      --max-horizon-bars 288

# 3. 集計レポート出力
python3 -c "
import sqlite3
con = sqlite3.connect('knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite')
print('=== outcome distribution ===')
for row in con.execute(\"SELECT s.pattern_name, s.direction, o.outcome, COUNT(*) FROM chart_pattern_signals s JOIN chart_pattern_outcomes o ON o.signal_id=s.id GROUP BY 1,2,3 ORDER BY 1,2,3\"):
    print(f'  {row[0]:25s} {row[1]:4s} {row[2]:3s} {row[3]:>5d}')
print()
print('=== hit_rate per (pattern, direction), DM excluded ===')
for row in con.execute(\"\"\"
WITH base AS (SELECT s.pattern_name p, s.direction d, o.outcome o FROM chart_pattern_signals s JOIN chart_pattern_outcomes o ON o.signal_id=s.id WHERE o.outcome!='DM')
SELECT p, d, SUM(CASE o WHEN 'TP' THEN 1 ELSE 0 END) tp, SUM(CASE o WHEN 'SL' THEN 1 ELSE 0 END) sl, SUM(CASE o WHEN 'TO' THEN 1 ELSE 0 END) to_, COUNT(*) n, ROUND(100.0*SUM(CASE o WHEN 'TP' THEN 1 ELSE 0 END)/COUNT(*),1) hr
FROM base GROUP BY p,d ORDER BY hr DESC
\"\"\"):
    print(f'  {row[0]:25s} {row[1]:4s} TP={row[2]:>4d} SL={row[3]:>4d} TO={row[4]:>4d} N={row[5]:>5d} hit_rate={row[6]:>5.1f}%')
"
```

# 出力すべきレポート (codex `--output-last-message` に書く内容)

タスク完了時、Codex は以下を `last_message` に出すこと:

1. **Verdict**: ACCEPT / NEEDS_MORE_EVIDENCE / REJECT
2. **Outcome distribution table** (12 patterns × 2 directions × 4 outcomes)
3. **Hit rate per (pattern, direction)** ranked descending
4. **Bull/bear pair symmetry check** (6 pairs)
5. **DM rate** (期間末尾で outcome 計測できなかった signals の比率)
6. **Median pnl_pips per pattern** (BUY/SELL 通算)
7. **次にやるべきこと** (W1P2 への引き継ぎ): どの patterns を W1P2 BT に含めるか、Bonferroni m はいくつにするか

# 禁止事項

- ❌ `.env`, OANDA / OPENAI / Render API key を読む / 書く / log に出す
- ❌ `modules/`, `app.py`, `strategies/` を編集 (Live promotion は W1P3 後)
- ❌ 本番 DB (Render `/var/data/*.db`) への接続
- ❌ ローカル DB (`demo.db` 等) への書き込み
- ❌ 既存の未 commit 変更を上書き / stash / discard
- ❌ `data/cache/massive/*.parquet` を編集 / 削除 (read-only)
- ❌ `chart_pattern_signals` テーブルへの UPDATE / DELETE / DROP (read-only)
- ❌ `git push` / `git rebase --onto` 等の history rewrite
- ❌ MAX_HORIZON_BARS の post-hoc 調整 (= cherry-pick disguise) — 288 で fix

# Rule R1 verification

- 365日 BT スキップ可 (本タスクは outcome labeling、BT は W1P2)
- pre-registration は本ファイルの "仕様" + "verdict matrix" + "MAX_HORIZON_BARS=288" が LOCK
- post-hoc に MAX_HORIZON_BARS / outcome 定義 / DM threshold を変更した場合、verdict は強制 INVALID

# 参考: W1P0 → W1P1 の引き継ぎ

W1P0 (`.ai/decisions/20260504-0125-s6-w1p0-inventory-manual-promote.md`) で manual promote 確定:

- Inventory: 22,094 signals
- 最大 N: double_top SELL 4,869
- 最小 N: triple_top SELL 142 (W1P2 で除外候補になる可能性高)
- 全 12 patterns × 2 directions が non-zero
- PK duplicate 0

W1P1 はこの inventory に **outcome label を付ける**だけのタスク。BT ではない、predictive power の statistical test もしない。次の W1P2 にバトンを渡すための clean labelled dataset を作る。
