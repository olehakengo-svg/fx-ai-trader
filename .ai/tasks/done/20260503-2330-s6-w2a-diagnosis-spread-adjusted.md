---
id: 20260503-2330-s6-w2a-diagnosis-spread-adjusted
title: S6 W2a 診断 — spread-adjusted EV / 7 軸 cell deepdive (no LIVE)
owner: codex
status: queued
priority: P1
created_at: 2026-05-03T23:30:00+0900
roadmap_gate: 新戦略族 S6 Wave 2a (W2 REJECT の root cause 診断、Wave 2b 設計の土台)
rule: R2
prerequisite_decision:
  - 2026-05-03 W2 commit d3702dd — chart_pattern_bt_trades に 22,093 + 17,393 + 2,997 trade 行格納済み
  - feedback_label_empirical_audit — コード演繹禁止、実測クエリ必須
  - feedback_spread_basis_for_mafe — entry_price 基準で MAFE 計算
  - feedback_partial_quant_trap — N/WR/EV だけで判定禁止
  - feedback_ma_filter_breaks_mr — filter 追加は後 (W2b)、本 task は診断のみ
---

## 0. 目的

W2 BT で全 26 cell REJECT となった root cause を**実測で**診断し、Wave 2b で何を修正すべきか cell ごとに proposed fix を出す。

**新規 BT 実行は不要**。既存 `chart_pattern_bt_trades` (committed in d3702dd) を集計し、`spread_at_entry/exit` の実測 profile で pnl を再計算。

LIVE / Shadow 露出ゼロ。新規取引なし。

## 1. 仮説

- **H1 (主仮説)**: W2 の flat 1.5pip spread 仮定が prime-session signal を過大評価し、off-hours signal を過小評価している。実測 hour-of-day spread profile で再計算すると、少なくとも 1 cell が PROMOTE/SHADOW 圏に入る
- **H2**: TP 到達率が低い (TIMEOUT 多い) cell は TP geometry (= measured move) が遠すぎる。R:R 0.5×, 0.75×, 1.0× で再計算すると optimal R:R が見つかる
- **H3**: 特定 hour-bucket (London/NY 等) のみで edge が立つ cell が存在
- **H4 (反証用)**: 全 cell が hour-bucket / R:R / pivot quality いずれの軸でも edge を取り戻さなければ、ATR 12-pattern hypothesis 自体を park し別 hypothesis family へ移行
- **H5 (副次)**: triple_bottom isolated (W2 で唯一 PF 1.01 borderline) の WF fold 1 PF 0.33 は specific regime 依存 (VIX spike / DXY direction 等) の可能性

## 2. 対象データ (LOCKED)

| 用途 | 出典 | フィルタ |
|---|---|---|
| BT trades | `data/chart_patterns.db` table `chart_pattern_bt_trades` | 全 42,483 行 (isolated 22,093 + arbitrated 17,393 + reversed 2,997) |
| 実測 spread profile | `demo_trades.db` table `demo_trades` | `instrument='USD_JPY'`, `spread_at_entry > 0`, `entry_time IS NOT NULL` (is_shadow 区別は不要、spread はブローカー側) |
| Bar OHLC (regime tagging 用) | `data/cache/massive/USD_JPY_5m.parquet` | read-only |
| Cell 構造 | `chart_pattern_bt_verdicts` | W2 verdict 表との比較用 |

## 3. 診断 9 軸 (LOCK)

各 pattern × isolated mode で以下を集計:

### 3.1 Exit reason distribution
- `exit_reason` (TP / SL / TIMEOUT) の比率
- TIMEOUT > 30% → TP 遠すぎ仮説
- SL > 50% → SL 近すぎ or detection FP

### 3.2 MAFE/MFE distribution
- median / p25 / p75 / p95 の MAFE pips, MFE pips
- MAFE > 平均 SL 距離 → SL placement 妥当
- MFE が平均 TP の 50% 未満 → TP 遠すぎ確定

### 3.3 R:R 達成曲線 (recompute, no new BT)
既存 trade ごとに `entry_px`, `exit_px`, `mafe_pips`, `mfe_pips` から:
- TP at 0.50× / 0.75× / 1.00× / 1.25× / 1.50× pattern_height で hypothetical pnl を再計算
- SL 位置は固定 (W2 frozen)
- 各 R:R 設定での WR / EV / PF を出力
- **Optimal R:R (max EV) を pattern 別に特定**

### 3.4 早期到達分布
- TP hit 時の median `hold_bars` / SL hit 時の median `hold_bars`
- SL median < 3 bars → entry 直後に逆行 (微構造問題 or detection 不適切)

### 3.5 Hour-of-day × WR/EV (UTC bucket)
4 bucket: `Asia (00-08)`, `London (08-12)`, `London_NY_overlap (12-16)`, `NY+late (16-24)` UTC
- 各 bucket × pattern の N / WR / EV / PF
- Bonferroni 補正 m = 12 patterns × 4 buckets = 48, α/m = 0.00104

### 3.6 ★ Spread-adjusted EV (主軸、最重要)

#### 3.6.1 Empirical hour-of-day spread profile 構築
```sql
SELECT
  CAST(strftime('%H', entry_time) AS INTEGER) AS hour_utc,
  AVG(spread_at_entry + spread_at_exit) AS avg_round_trip_spread_pips,
  COUNT(*) AS n,
  MEDIAN(spread_at_entry + spread_at_exit) AS median_round_trip_spread_pips
FROM demo_trades
WHERE instrument='USD_JPY' AND spread_at_entry > 0 AND entry_time IS NOT NULL
GROUP BY hour_utc;
```
(MEDIAN は SQLite 拡張なら使用、なければ percentile_cont 相当を Python で計算)

24-hour profile を doc に表記。N が薄い hour は近接 hour と merge した bucket profile も用意。

#### 3.6.2 BT trade pnl 再計算
- 各 `chart_pattern_bt_trades` 行について `entry_ts` の hour_utc を抽出
- BT 想定 spread (1.5p) を外して raw_pnl を逆算
- empirical hour profile の round-trip spread を適用して `pnl_adjusted` を再計算
- pattern × mode × original_verdict ごとに spread-adjusted N/WR/EV/PF/Wilson_lo/Bonf_p/Kelly を再計算

#### 3.6.3 Verdict 比較
| pattern | flat-1.5p verdict | spread-adj verdict | flip 内容 |
|---|---|---|---|

flip した cell があれば doc に明示。

### 3.7 Pivot quality 別 (`pattern_height_atr` 分位)
- p25 / p50 / p75 で 4 quantile に分割
- 各 quantile × pattern の WR / EV
- 強い pattern (上位 quantile) のみで edge 復活する cell を特定

### 3.8 Regime 別 (D1 EMA200 alignment)
parquet から D1 EMA200 を計算、各 trade entry_ts で `D1_close > D1_EMA200` (BULL) / 反対 (BEAR) でタグ:
- pattern × regime × WR/EV
- Direction 整合性: BUY パターンは BULL regime でのみ評価、SELL は BEAR
- 教科書整合か、それとも逆張り regime か実測

### 3.9 Triple_bottom WF fold 1 deepdive (H5 用)
- WF1 (2019-2020) の triple_bottom signal の cluster 分析
- VIX bucket / DXY direction でフィルタした EV
- regime sensitivity の有無を判定

## 4. 出力テーブル DDL (LOCK)

```sql
-- spread profile snapshot
CREATE TABLE IF NOT EXISTS chart_pattern_bt_spread_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,
    hour_utc INTEGER NOT NULL CHECK (hour_utc BETWEEN 0 AND 23),
    n_observations INTEGER NOT NULL,
    avg_round_trip_spread_pips REAL NOT NULL,
    median_round_trip_spread_pips REAL,
    p95_round_trip_spread_pips REAL,
    source TEXT NOT NULL,           -- 'demo_trades_empirical'
    snapshot_ts TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pair, hour_utc, source)
);

-- diagnosis verdict (re-evaluation per axis)
CREATE TABLE IF NOT EXISTS chart_pattern_w2a_diagnosis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL,
    pattern_name TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    bt_run_id TEXT NOT NULL,                  -- 'isolated' / 'arbitrated' / 'reversed'
    axis TEXT NOT NULL,                       -- 'spread_adj' / 'rr_optimal' / 'hour_bucket' / 'pivot_quality' / 'regime'
    sub_key TEXT,                             -- e.g. 'London_NY_overlap', 'rr=0.75', 'q4'
    n INTEGER NOT NULL,
    wr REAL NOT NULL,
    ev_pips REAL NOT NULL,
    pf REAL,
    wilson_lo_95 REAL NOT NULL,
    bev_wr REAL NOT NULL,
    bonferroni_p REAL NOT NULL,
    bonferroni_alpha REAL NOT NULL,
    bonferroni_m INTEGER NOT NULL,
    kelly REAL NOT NULL,
    proposed_verdict TEXT NOT NULL CHECK (proposed_verdict IN ('PROMOTE','SHADOW','REJECT','INSUFFICIENT')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, bt_run_id, axis, sub_key)
);
```

DB path: `data/chart_patterns.db` (append、既存表は read-only)

## 5. 受入条件 (LOCK)

- [ ] `chart_pattern_bt_signals` / `chart_pattern_bt_trades` / `chart_pattern_bt_verdicts` 行数不変 (W2 frozen)
- [ ] `chart_pattern_bt_spread_profile` に 24 行 (USD_JPY 全 hour) または 4 行 (4-bucket simplified、両方推奨)
- [ ] `chart_pattern_w2a_diagnosis` に各 axis × pattern の集計行
- [ ] `wiki/decisions/s6-w2a-diagnosis-2026-05-03.md` に 9 軸の表 + cell 別 root cause + Wave 2b proposed fix
- [ ] H1〜H5 仮説それぞれに ACCEPT / REJECT / INCONCLUSIVE の verdict
- [ ] spread-adj verdict で flip した cell があれば PROMOTE/SHADOW/REJECT を明示、なければ「flat-1.5p で REJECT 妥当」を明示
- [ ] Wave 2b の prioritized fix list (top 3 candidate cells with proposed entry hour / R:R / regime filter)
- [ ] `pytest tests/test_s6_w2a_diagnosis.py -q` 全 pass (≥ 10 tests)
  - 必須: spread profile builder の hour bucket SQL test
  - 必須: pnl 再計算の analytic 一致 test
  - 必須: Bonferroni m 計算 test (axis ごとに正しい m)
  - 必須: R:R 達成曲線の hypothetical pnl 計算 test
- [ ] `app.py` / `modules/` / `strategies/` 編集 0 件
- [ ] LIVE / Shadow データ書き込みなし

## 6. Scope

Codex MAY change:

- `tools/s6_w2a_diagnosis.py` (new) — 9 軸の診断ロジック
- `tools/s6_run_w2a.py` (new) — driver
- `tests/test_s6_w2a_diagnosis.py` (new)
- `knowledge-base/wiki/decisions/s6-w2a-diagnosis-2026-05-03.md` (new)
- `knowledge-base/wiki/strategies/s6-chart-pattern.md` (UPDATE Wave Plan section, Stage は変更不要)
- `data/chart_patterns.db` (append spread_profile + diagnosis tables のみ、既存 read-only)
- `.ai/runs/<run-dir>/final.md`

Codex MAY NOT change:

- `app.py`, `modules/`, `strategies/` (Wave 4 まで触らない)
- `chart_pattern_signals` / `chart_pattern_bt_trades` / `chart_pattern_bt_verdicts` (W2 frozen)
- `data/cache/massive/*.parquet` (read-only)
- `demo_trades.db` (read-only、spread 集計のみ)
- `.env`, OANDA secrets
- `wiki/index.md`, `wiki/tier-master.json`
- 既存未コミット変更

## 7. Required Reading

- `CLAUDE.md` (Rule 2 適用、診断のみ)
- `knowledge-base/wiki/analyses/friction-analysis.md` (既存 spread 知見)
- `knowledge-base/wiki/decisions/s6-w2-bt-2026-05-03.md` (W2 verdict)
- `knowledge-base/wiki/lessons/index.md` の `feedback_label_empirical_audit`, `feedback_spread_basis_for_mafe`, `feedback_partial_quant_trap`, `feedback_ma_filter_breaks_mr`
- `tools/s6_chart_pattern_bt.py` (BT engine 仕様)

## 8. Verification Commands

```bash
# 0. Frozen tables 行数確認
sqlite3 data/chart_patterns.db "SELECT 'signals' AS t, COUNT(*) FROM chart_pattern_signals UNION ALL SELECT 'trades', COUNT(*) FROM chart_pattern_bt_trades UNION ALL SELECT 'verdicts', COUNT(*) FROM chart_pattern_bt_verdicts;"
# 期待: signals=22094, trades=42483, verdicts=26

# 1. demo_trades 実測 spread サンプル
sqlite3 demo_trades.db "SELECT COUNT(*), AVG(spread_at_entry), AVG(spread_at_exit) FROM demo_trades WHERE instrument='USD_JPY' AND spread_at_entry > 0;"

# 2. Self-test
python3 tools/s6_w2a_diagnosis.py --self-test

# 3. Unit tests
python3 -m pytest -q tests/test_s6_w2a_diagnosis.py

# 4. Production run
python3 tools/s6_run_w2a.py --pair USD_JPY --tf M5 --mode isolated

# 5. Spread profile 確認
sqlite3 data/chart_patterns.db "SELECT hour_utc, n_observations, ROUND(avg_round_trip_spread_pips,2), ROUND(median_round_trip_spread_pips,2) FROM chart_pattern_bt_spread_profile WHERE pair='USD_JPY' ORDER BY hour_utc;"

# 6. Spread-adj verdict flip 集計
sqlite3 data/chart_patterns.db "SELECT pattern_name, axis, sub_key, ROUND(ev_pips,2), ROUND(pf,2), proposed_verdict FROM chart_pattern_w2a_diagnosis WHERE axis='spread_adj' ORDER BY pattern_id;"

# 7. Frozen tables 行数不変確認
sqlite3 data/chart_patterns.db "SELECT 'signals' AS t, COUNT(*) FROM chart_pattern_signals UNION ALL SELECT 'trades', COUNT(*) FROM chart_pattern_bt_trades UNION ALL SELECT 'verdicts', COUNT(*) FROM chart_pattern_bt_verdicts;"
# 期待: 不変
```

## 9. Codex Instructions

**Rule 2 (Fast & Reactive) タスク**。LIVE 露出ゼロ、診断のみ。

**絶対遵守**:
- §2 frozen tables を絶対に書き換えない (W2 commit d3702dd の immutable 入力)
- §3.6 empirical spread profile は demo_trades 実測のみ。リテラチャ推定値や hardcode を使わない (`feedback_label_empirical_audit`)
- §3.6.2 pnl 再計算は existing trades の `entry_px / exit_px / exit_reason` を基に hypothetical recompute (新規 BT 実行禁止)
- Bonferroni m は axis ごとに適切に設定 (例: spread-adj は m=12, hour-bucket は m=48)
- spread profile が薄い hour (n<30) は merged bucket を使うか doc に warning 明示
- `feedback_ma_filter_breaks_mr` の罠回避: 本 task は診断のみで filter 追加 / 戦略変更は Wave 2b で別 task

**禁止事項**:
- `app.py` / `modules/` / `strategies/` の編集
- `chart_pattern_signals` / `chart_pattern_bt_trades` / `chart_pattern_bt_verdicts` への書き込み
- 新規 BT loop の実装 (既存 trades の集計と再計算のみ)
- LIVE / Shadow / OANDA bridge への接続
- `wiki/index.md` / `wiki/tier-master.json` の更新

**Verdict logic**:
- spread-adj で 1 cell でも PROMOTE 圏入り → Wave 2b で「spread-aware entry hour 制約」が optimal fix
- R:R で optimal が見つかる → Wave 2b で TP geometry 改修
- regime alignment で edge → Wave 2b で D1 trend filter (`feedback_ma_filter_breaks_mr` の罠あり、cell 単体実測必須)
- 全 axis で edge なし → H4 ACCEPT、S6 family park

PR 作成は本タスクで実行しない。proposal doc + diagnosis 実装 + test のみ。Claude review 後、別 task で commit/deploy。

最終レポートには status, files changed, 9 axis 集計表, H1〜H5 verdict, spread-adj で flip した cell 一覧, Wave 2b prioritized fix list (top 3), residual risks, 次タスク (= Wave 2b 設計 spec proposal or S6 park 判断) を含む。
