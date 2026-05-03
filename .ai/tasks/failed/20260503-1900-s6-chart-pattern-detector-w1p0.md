---
id: 20260503-1900-s6-chart-pattern-detector-w1p0
title: S6 Chart Pattern Detector — 12 patterns, USDJPY M5 only (Wave 1 Phase 0, detector-only)
owner: codex
status: queued
priority: P1
created_at: 2026-05-03T19:00:00+0900
roadmap_gate: 新戦略族 S6 Wave 1 Phase 0 (LIVE 露出なし、検出器+ラベル化のみ)
rule: R2
prerequisite_decision:
  - 2026-05-03 12-pattern math spec (本 spec §3 に LOCK 同梱)
  - feedback_codex_schema_hallucination — DDL を spec に直接記載
  - feedback_codex_mock_test_trap — 実 parquet で E2E 検証必須
---

## 0. 目的 (rev0)

ユーザー手書きノートの 12 チャートパターン (順張り 6 / 逆張り 6) を **数学的検出器**として実装し、USDJPY M5 12.3y 全バーに対して signal を生成、SQLite 表に格納する。

**本タスクは Wave 1 Phase 0 = 検出器とラベル化のみ。BT は別タスク (Wave 2)。LIVE 露出は Wave 4 まで一切なし。**

## 1. Wave 構成 (参考、本タスクは W1P0 のみ)

| Wave | スコープ | 本 task |
|---|---|---|
| W1P0 | 1 pair × 1 TF × 12 pattern, detector + 手動アノテート照合 | **★本 task** |
| W2 | 1 pair × 1 TF, 12 pattern × BT 12.3y, cell 単位 verdict | 別 task |
| W3 | 6 pair × 3 TF sweep (216 cells), Bonferroni m=216 | 別 task |
| W4 | Shadow promote / LIVE candidate 判定 (W3-1 H1 gate 経由) | 別 task |

## 2. 仮説

- **H1**: 12 パターンを ATR 正規化された幾何条件で検出すると、USDJPY M5 12.3y で各パターン N≥30 の signal が得られる
- **H2**: 手動アノテート 30 サンプル (各パターン最低 2-3 件含む) に対し recall ≥ 0.7, precision ≥ 0.6
- **H3**: bar-close gate と re-entry dedup により、同一 leg からの重複 signal は 0 件

## 3. パターン数学定義 (LOCK)

### 3.1 共通プリミティブ

**Swing pivot (window k=3)**:
- High pivot $H_i$: `high[i] > max(high[i-3..i-1])` AND `high[i] > max(high[i+1..i+3])`
- Low pivot $L_i$: 対称

**ATR**: `ATR_14` of M5 bars, EMA-smoothed (Wilder's)

**Trendline (2-point)**: 連続する同種 pivot 2 点を直線で結ぶ。傾き $a = (y_2 - y_1) / (t_2 - t_1)$。3 点以上時は最新 2 点を採用。

**閾値定数 (LOCK)**:
- `EPS_FLAT = 0.05 * ATR / bar` (水平判定)
- `EPS_SLOPE = 0.10 * ATR / bar` (傾き有意性)
- `MIN_PATTERN_HEIGHT = 1.5 * ATR`
- `MIN_DURATION_BARS = 5`
- `MAX_DURATION_BARS = 80`
- `BREAKOUT_BUFFER = 0.10 * ATR`
- `SL_BUFFER = 0.50 * ATR`
- `PIVOT_TOLERANCE = 0.30 * ATR` (双子/三子の同値判定)

### 3.2 各パターン

| ID | name | direction | 幾何条件 (LOCK) |
|---|---|---|---|
| 1 | ascending_triangle | BUY | $\|a_u\| < \epsilon_{\text{flat}}$, $a_l > \epsilon_{\text{slope}}$, H pivots ≥2, L pivots ≥2, 交互, 高さ≥`MIN_PATTERN_HEIGHT` |
| 2 | rising_wedge | BUY | $a_u > 0, a_l > 0, a_l > a_u$, 収束率≥50% |
| 3 | bull_flag | BUY | Pole 直前 N=10〜20 で $\Delta \geq 3 \cdot \text{ATR}$, Flag $a_u < 0, a_l < 0$, $\|a_u-a_l\| < \epsilon$, Flag 振幅≤0.5 Pole |
| 4 | descending_triangle | SELL | #1 鏡像 |
| 5 | falling_wedge | SELL | #2 鏡像 |
| 6 | bear_flag | SELL | #3 鏡像 |
| 7 | double_bottom | BUY | $L_1, L_2$: $\|L_1-L_2\| ≤ \text{PIVOT\_TOLERANCE}$, 中間 $H_m - \min(L) ≥ \text{MIN\_PATTERN\_HEIGHT}$, $5 ≤ t_2-t_1 ≤ 50$ |
| 8 | triple_bottom | BUY | $L_1, L_2, L_3$: max-min ≤ tolerance, 中間 2H 平坦性 ≤ 0.4·ATR, 期間≤80 |
| 9 | inverse_head_shoulders | BUY | $L_S, L_H, L_{S'}$, $L_H < L_S$ かつ $L_H < L_{S'}$, $\|L_S - L_{S'}\| ≤ 0.5 \cdot \text{ATR}$, 時間対称比 ≤ 0.4 |
| 10 | double_top | SELL | #7 鏡像 |
| 11 | triple_top | SELL | #8 鏡像 |
| 12 | head_shoulders | SELL | #9 鏡像 |

### 3.3 Entry / SL / TP (LOCK)

**Entry trigger**: `close[t] > breakout_level + BREAKOUT_BUFFER` (BUY) / `close[t] < breakout_level - BREAKOUT_BUFFER` (SELL)
- breakout_level: triangle/wedge/flag → 上側 trendline; H&S → neckline; double/triple → 中間 H/L

**SL**:
- BUY: `min(L_pivots in pattern) - SL_BUFFER`
- SELL: `max(H_pivots in pattern) + SL_BUFFER`

**TP** (measured move):
- triangle/wedge/flag: Entry ± pattern_height
- double/triple bottom/top: Entry ± (neckline - extreme_pivot)
- H&S: Entry ± (neckline - head)

**Bar-close gate**: wick-only breakout は無効。`close[t]` が水準を超えた bar のみ trigger。

**Re-entry dedup**: 同一 pattern instance (同一 pivots set) からの再 fire 禁止。Pattern instance 識別は `(pattern_id, anchor_pivot_ts, opposite_pivot_ts)` の tuple。

## 4. SQLite DDL (LOCK, paste 直接)

```sql
CREATE TABLE IF NOT EXISTS chart_pattern_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL CHECK (pattern_id BETWEEN 1 AND 12),
    pattern_name TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('BUY','SELL')),
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_ts TEXT NOT NULL,            -- ISO8601 UTC of breakout bar close
    detection_ts TEXT NOT NULL,         -- pattern が完成した bar (breakout 前最後の pivot)
    entry_px REAL NOT NULL,
    sl_px REAL NOT NULL,
    tp_px REAL NOT NULL,
    pattern_height_atr REAL NOT NULL,   -- pattern_height / ATR_at_detection
    duration_bars INTEGER NOT NULL,
    atr_at_detection REAL NOT NULL,
    pivot_anchor_ts TEXT NOT NULL,
    pivot_opposite_ts TEXT NOT NULL,
    pivot_count INTEGER NOT NULL,
    confidence_score REAL,              -- optional: 幾何適合度 0-1 (収束率・対称性等の合成)
    raw_geometry_json TEXT,             -- debug 用 JSON (pivots, slopes, neckline 等)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, pair, timeframe, pivot_anchor_ts, pivot_opposite_ts)
);

CREATE INDEX IF NOT EXISTS idx_cps_pair_tf_ts ON chart_pattern_signals(pair, timeframe, signal_ts);
CREATE INDEX IF NOT EXISTS idx_cps_pattern ON chart_pattern_signals(pattern_id, pair, timeframe);
```

DB path: `data/chart_patterns.db` (新規)

## 5. 入出力

| 用途 | 出典 | フィルタ |
|---|---|---|
| OHLC | `data/cache/massive/USD_JPY_5m.parquet` | range 全期間 (2014-01-02 〜 2026-04-30, 903828 bars) |
| Signal 出力 | `data/chart_patterns.db` | `pair='USD_JPY', timeframe='M5'` |
| Ground truth | `tests/fixtures/manual_chart_pattern_labels.csv` (Codex が生成、本 spec で 30 件指定) | 各 pattern 最低 2 件、明確に視認できる instance |

### 5.1 Ground truth 30 サンプル仕様

Codex はランダムに 30 ウィンドウ (各 200 bars) を 12.3y から sampling し、視覚パターンを判定する代わりに、**以下のルール for 各 pattern を満たす最初の合成 instance を fixture に記載**:

> 注: 真の手動アノテートは Wave 1 Phase 1 で人間 (ユーザー) が実施。本 task では「detector が決定論的に再現できる」ことを test fixture で証明するのみ。

各 pattern について、Codex は以下を生成:
- 最初に検出される signal の `signal_ts`, `entry_px`, `sl_px`, `tp_px`, `pattern_height_atr`
- これを fixture CSV に固定し、`pytest` で「同じ入力 → 同じ出力」を保証 (regression test)

## 6. 統計条件 (本 task の受入)

本 task は detector のみなので Bonferroni / WF / Kelly は **適用範囲外**。Wave 2 で適用。

ただし以下を verify:
- 12 pattern 全体で signal 総数 N ≥ 360 (各 pattern N ≥ 30 を期待)
- 各 pattern の duration_bars 分布 (median, p95)
- Re-entry dedup 結果: 同一 pivot tuple 重複 0 件
- Bar-close gate 結果: wick-only breakout が除外されることを test で証明

## 7. Scope

Codex MAY change:

- `tools/s6_chart_pattern_detector.py` (new) — 12 pattern 検出ロジック, ATR 計算, swing pivot, trendline 回帰, dedup
- `tools/s6_run_w1p0.py` (new) — driver: parquet 読み → detector → SQLite 書き
- `tests/test_s6_chart_pattern_detector.py` (new)
  - 必須 unit test:
    - swing pivot 検出 (合成 OHLC で k=3)
    - ATR 計算 (Wilder's EMA)
    - 12 pattern 各々の合成 instance で hit
    - bar-close gate (wick-only breakout が除外されること)
    - re-entry dedup (同 pivot tuple で 1 件のみ)
    - SL/TP/Entry 計算の正しさ (各 pattern について analytic 値と一致)
- `tests/fixtures/manual_chart_pattern_labels.csv` (new) — Codex 生成の regression fixture
- `knowledge-base/wiki/strategies/s6-chart-pattern.md` (new) — strategy doc, 12 pattern 数学仕様, Wave 計画
- `knowledge-base/wiki/decisions/s6-w1p0-detector-2026-05-03.md` (new) — Phase 0 verdict
- `data/chart_patterns.db` (new, .gitignore 確認)
- `.ai/runs/<run-dir>/final.md`

Codex MAY NOT change:

- `app.py`, `modules/`, `strategies/` (LIVE/Shadow 配信は Wave 4 まで触らない)
- 既存の戦略 / Tier / config
- `data/cache/massive/*.parquet` (read-only)
- `.env`, OANDA secrets
- 既存未コミット変更

## 8. Required Reading

- `CLAUDE.md` (Rule 2 Fast & Reactive: detector は LIVE 露出なし、Wave 1 は実装・テストのみ)
- `wiki/lessons/index.md` の `feedback_codex_schema_hallucination`, `feedback_codex_mock_test_trap`, `feedback_label_empirical_audit`
- `wiki/strategies/s4-connors-raschke-80-20.md` (新戦略 doc 構造の参考)
- `tools/s4_connors_raschke_bt.py` (もし存在: parquet 読み込みパターンの参考)

## 9. Acceptance Criteria

- [ ] `python3 tools/s6_chart_pattern_detector.py --self-test` で 12 pattern 全ての合成 hit を表示
- [ ] `pytest tests/test_s6_chart_pattern_detector.py -q` 全 pass (≥ 20 tests)
  - 必須: bar-close gate test
  - 必須: re-entry dedup test
  - 必須: 12 pattern 各々の synthetic hit test
  - 必須: SL/TP の analytic 値一致 test
- [ ] `python3 tools/s6_run_w1p0.py --pair USD_JPY --tf M5` 実行で:
  - signal 総数 ≥ 360 (各 pattern N ≥ 30 を期待、足りない pattern は doc に明示)
  - SQLite UNIQUE 制約違反 0 件
  - 実行時間 ≤ 10 分
- [ ] `data/chart_patterns.db` の `chart_pattern_signals` 表に行が入る
  - `SELECT pattern_name, COUNT(*), MIN(signal_ts), MAX(signal_ts) FROM chart_pattern_signals GROUP BY pattern_name` で 12 行
- [ ] `wiki/strategies/s6-chart-pattern.md` に: 12 pattern 数学定義, Wave 計画, Phase 0 結果, next task 候補
- [ ] `wiki/decisions/s6-w1p0-detector-2026-05-03.md` に: signal 数分布, duration 分布 (median/p95), pattern_height_atr 分布, sample signal table (各 pattern 1 件), verdict
- [ ] `.ai/runs/<run-dir>/final.md` に: status, files changed, signal 総数, pattern 別内訳, residual risks, 次タスク (= Wave 2 BT)
- [ ] `app.py` / `modules/` / `strategies/` 編集 0 件

## 10. Verification Commands

```bash
# 0. parquet 確認
python3 -c "import pandas as pd; df=pd.read_parquet('data/cache/massive/USD_JPY_5m.parquet'); print(df.shape, df.index.min(), df.index.max())"
# 期待: (903828, 7) 2014-01-02 04:55:00+00:00 2026-04-30 23:55:00+00:00

# 1. Self-test (合成 instance で 12 pattern hit)
python3 tools/s6_chart_pattern_detector.py --self-test

# 2. Unit tests
python3 -m pytest -q tests/test_s6_chart_pattern_detector.py

# 3. Production run
python3 tools/s6_run_w1p0.py --pair USD_JPY --tf M5 \
  --parquet data/cache/massive/USD_JPY_5m.parquet \
  --db data/chart_patterns.db

# 4. Signal 集計
sqlite3 data/chart_patterns.db "SELECT pattern_name, COUNT(*) AS n, ROUND(AVG(duration_bars),1) AS dur_mean, ROUND(AVG(pattern_height_atr),2) AS h_atr FROM chart_pattern_signals GROUP BY pattern_name ORDER BY pattern_id;"

# 5. UNIQUE 違反 0 件確認
sqlite3 data/chart_patterns.db "SELECT pattern_id, pivot_anchor_ts, pivot_opposite_ts, COUNT(*) FROM chart_pattern_signals GROUP BY 1,2,3 HAVING COUNT(*) > 1;"
# 期待: 0 行

# 6. Bar-close gate 効果
sqlite3 data/chart_patterns.db "SELECT pattern_name, MIN(signal_ts), MAX(signal_ts) FROM chart_pattern_signals GROUP BY pattern_name;"
```

## 11. Codex Instructions

これは **Rule 2 (Fast & Reactive)** タスク。LIVE / Shadow 配信は Wave 4 まで一切なし、本 task は detector + ラベル化のみ。

**絶対遵守**:
- §3 の 12 pattern 数学定義は LOCK。閾値定数を勝手に変えない。
- §4 の SQLite DDL を `tools/s6_chart_pattern_detector.py` 冒頭にコメント or schema constant として直接埋め込む (`feedback_codex_schema_hallucination` 回避)
- bar-close gate / re-entry dedup の test を書かずに実装すると `feedback_codex_mock_test_trap` 違反
- パターン #2 (rising_wedge) / #5 (falling_wedge) はノートに従い順張り方向で実装。BT 結果次第で Wave 2 で逆転判定 (S3 COT literal の教訓)
- detector は時系列 forward-only に動作させる (look-ahead bias 禁止: bar `t` の signal は `bar[0..t]` のみで決定)
- Pattern instance 単位の dedup は UNIQUE 制約 + insert-or-ignore で実装

**禁止事項**:
- `app.py` / `modules/` / `strategies/` の編集
- BT loop の実装 (Wave 2 別 task)
- Live trading / OANDA bridge への接続
- `wiki/index.md` / `wiki/tier-master.md` の更新 (新戦略は Wave 4 で初めて Tier 登録)

`feedback_success_until_achieved` 通り、verdict が ACCEPT 未満で closure 短絡禁止。
- signal 総数 < 360 → Phase 0 NEEDS_MORE_EVIDENCE: どの pattern が hit 不足か analyses/ で原因特定
- pattern 別 N < 30 が 3 つ以上 → 数学定義の閾値再検討提案 (LOCK 解除には別 task)

PR 作成は本タスクで実行しない。proposal doc + detector 実装 + test のみ。Claude review 後、別 task で commit/deploy。

最終レポートには status, files changed, signal 総数 (pattern 別内訳), regression fixture 30 件の固定値, residual risks, 次タスク (= Wave 2 BT spec proposal) を含む。


## Error (2026-05-03T12:38:47Z)

```
Reading prompt from stdin...
OpenAI Codex v0.128.0 (research preview)
--------
workdir: /data/repo/fx-ai-trader
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019dedd8-f411-7be1-92a4-60cab8487374
--------
user
## 0. 目的 (rev0)

ユーザー手書きノートの 12 チャートパターン (順張り 6 / 逆張り 6) を **数学的検出器**として実装し、USDJPY M5 12.3y 全バーに対して signal を生成、SQLite 表に格納する。

**本タスクは Wave 1 Phase 0 = 検出器とラベル化のみ。BT は別タスク (Wave 2)。LIVE 露出は Wave 4 まで一切なし。**

## 1. Wave 構成 (参考、本タスクは W1P0 のみ)

| Wave | スコープ | 本 task |
|---|---|---|
| W1P0 | 1 pair × 1 TF × 12 pattern, detector + 手動アノテート照合 | **★本 task** |
| W2 | 1 pair × 1 TF, 12 pattern × BT 12.3y, cell 単位 verdict | 別 task |
| W3 | 6 pair × 3 TF sweep (216 cells), Bonferroni m=216 | 別 task |
| W4 | Shadow promote / LIVE candidate 判定 (W3-1 H1 gate 経由) | 別 task |

## 2. 仮説

- **H1**: 12 パターンを ATR 正規化された幾何条件で検出すると、USDJPY M5 12.3y で各パターン N≥30 の signal が得られる
- **H2**: 手動アノテート 30 サンプル (各パターン最低 2-3 件含む) に対し recall ≥ 0.7, precision ≥ 0.6
- **H3**: bar-close gate と re-entry dedup により、同一 leg からの重複 signal は 0 件

## 3. パターン数学定義 (LOCK)

### 3.1 共通プリミティブ

**Swing pivot (window k=3)**:
- High pivot $H_i$: `high[i] > max(high[i-3..i-1])` AND `high[i] > max(high[i+1..i+3])`
- Low pivot $L_i$: 対称

**ATR**: `ATR_14` of M5 bars, EMA-smoothed (Wilder's)

**Trendline (2-point)**: 連続する同種 pivot 2 点を直線で結ぶ。傾き $a = (y_2 - y_1) / (t_2 - t_1)$。3 点以上時は最新 2 点を採用。

**閾値定数 (LOCK)**:
- `EPS_FLAT = 0.05 * ATR / bar` (水平判定)
- `EPS_SLOPE = 0.10 * ATR / bar` (傾き有意性)
- `MIN_PATTERN_HEIGHT = 1.5 * ATR`
- `MIN_DURATION_BARS = 5`
- `MAX_DURATION_BARS = 80`
- `BREAKOUT_BUFFER = 0.10 * ATR`
- `SL_BUFFER = 0.50 * ATR`
- `PIVOT_TOLERANCE = 0.30 * ATR` (双子/三子の同値判定)

### 3.2 各パターン

| ID | name | direction | 幾何条件 (LOCK) |
|---|---|---|---|
| 1 | ascending_triangle | BUY | $\|a_u\| < \epsilon_{\text{flat}}$, $a_l > \epsilon_{\text{slope}}$, H pivots ≥2, L pivots ≥2, 交互, 高さ≥`MIN_PATTERN_HEIGHT` |
| 2 | rising_wedge | BUY | $a_u > 0, a_l > 0, a_l > a_u$, 収束率≥50% |
| 3 | bull_flag | BUY | Pole 直前 N=10〜20 で $\Delta \geq 3 \cdot \text{ATR}$, Flag $a_u < 0, a_l < 0$, $\|a_u-a_l\| < \epsilon$, Flag 振幅≤0.5 Pole |
| 4 | descending_triangle | SELL | #1 鏡像 |
| 5 | falling_wedge | SELL | #2 鏡像 |
| 6 | bear_flag | SELL | #3 鏡像 |
| 7 | double_bottom | BUY | $L_1, L_2$: $\|L_1-L_2\| ≤ \text{PIVOT\_TOLERANCE}$, 中間 $H_m - \min(L) ≥ \text{MIN\_PATTERN\_HEIGHT}$, $5 ≤ t_2-t_1 ≤ 50$ |
| 8 | triple_bottom | BUY | $L_1, L_2, L_3$: max-min ≤ tolerance, 中間 2H 平坦性 ≤ 0.4·ATR, 期間≤80 |
| 9 | inverse_head_shoulders | BUY | $L_S, L_H, L_{S'}$, $L_H < L_S$ かつ $L_H < L_{S'}$, $\|L_S - L_{S'}\| ≤ 0.5 \cdot \text{ATR}$, 時間対称比 ≤ 0.4 |
| 10 | double_top | SELL | #7 鏡像 |
| 11 | triple_top | SELL | #8 鏡像 |
| 12 | head_shoulders | SELL | #9 鏡像 |

### 3.3 Entry / SL / TP (LOCK)

**Entry trigger**: `close[t] > breakout_level + BREAKOUT_BUFFER` (BUY) / `close[t] < breakout_level - BREAKOUT_BUFFER` (SELL)
- breakout_level: triangle/wedge/flag → 上側 trendline; H&S → neckline; double/triple → 中間 H/L

**SL**:
- BUY: `min(L_pivots in pattern) - SL_BUFFER`
- SELL: `max(H_pivots in pattern) + SL_BUFFER`

**TP** (measured move):
- triangle/wedge/flag: Entry ± pattern_height
- double/triple bottom/top: Entry ± (neckline - extreme_pivot)
- H&S: Entry ± (neckline - head)

**Bar-close gate**: wick-only breakout は無効。`close[t]` が水準を超えた bar のみ trigger。

**Re-entry dedup**: 同一 pattern instance (同一 pivots set) からの再 fire 禁止。Pattern instance 識別は `(pattern_id, anchor_pivot_ts, opposite_pivot_ts)` の tuple。

## 4. SQLite DDL (LOCK, paste 直接)

```sql
CREATE TABLE IF NOT EXISTS chart_pattern_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL CHECK (pattern_id BETWEEN 1 AND 12),
    pattern_name TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('BUY','SELL')),
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_ts TEXT NOT NULL,            -- ISO8601 UTC of breakout bar close
    detection_ts TEXT NOT NULL,         -- pattern が完成した bar (breakout 前最後の pivot)
    entry_px REAL NOT NULL,
    sl_px REAL NOT NULL,
    tp_px REAL NOT NULL,
    pattern_height_atr REAL NOT NULL,   -- pattern_height / ATR_at_detection
    duration_bars INTEGER NOT NULL,
    atr_at_detection REAL NOT NULL,
    pivot_anchor_ts TEXT NOT NULL,
    pivot_opposite_ts TEXT NOT NULL,
    pivot_count INTEGER NOT NULL,
    confidence_score REAL,              -- optional: 幾何適合度 0-1 (収束率・対称性等の合成)
    raw_geometry_json TEXT,             -- debug 用 JSON (pivots, slopes, neckline 等)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, pair, timeframe, pivot_anchor_ts, pivot_opposite_ts)
);

CREATE INDEX IF NOT EXISTS idx_cps_pair_tf_ts ON chart_pattern_signals(pair, timeframe, signal_ts);
CREATE INDEX IF NOT EXISTS idx_cps_pattern ON chart_pattern_signals(pattern_id, pair, timeframe);
```

DB path: `data/chart_patterns.db` (新規)

## 5. 入出力

| 用途 | 出典 | フィルタ |
|---|---|---|
| OHLC | `data/cache/massive/USD_JPY_5m.parquet` | range 全期間 (2014-01-02 〜 2026-04-30, 903828 bars) |
| Signal 出力 | `data/chart_patterns.db` | `pair='USD_JPY', timeframe='M5'` |
| Ground truth | `tests/fixtures/manual_chart_pattern_labels.csv` (Codex が生成、本 spec で 30 件指定) | 各 pattern 最低 2 件、明確に視認できる instance |

### 5.1 Ground truth 30 サンプル仕様

Codex はランダムに 30 ウィンドウ (各 200 bars) を 12.3y から sampling し、視覚パターンを判定する代わりに、**以下のルール for 各 pattern を満たす最初の合成 instance を fixture に記載**:

> 注: 真の手動アノテートは Wave 1 Phase 1 で人間 (ユーザー) が実施。本 task では「detector が決定論的に再現できる」ことを test fixture で証明するのみ。

各 pattern について、Codex は以下を生成:
- 最初に検出される signal の `signal_ts`, `entry_px`, `sl_px`, `tp_px`, `pattern_height_atr`
- これを fixture CSV に固定し、`pytest` で「同じ入力 → 同じ出力」を保証 (regression test)

## 6. 統計条件 (本 task の受入)

本 task は detector のみなので Bonferroni / WF / Kelly は **適用範囲外**。Wave 2 で適用。

ただし以下を verify:
- 12 pattern 全体で signal 総数 N ≥ 360 (各 pattern N ≥ 30 を期待)
- 各 pattern の duration_bars 分布 (median, p95)
- Re-entry dedup 結果: 同一 pivot tuple 重複 0 件
- Bar-close gate 結果: wick-only breakout が除外されることを test で証明

## 7. Scope

Codex MAY change:

- `tools/s6_chart_pattern_detector.py` (new) — 12 pattern 検出ロジック, ATR 計算, swing pivot, trendline 回帰, dedup
- `tools/s6_run_w1p0.py` (new) — driver: parquet 読み → detector → SQLite 書き
- `tests/test_s6_chart_pattern_detector.py` (new)
  - 必須 unit test:
    - swing pivot 検出 (合成 OHLC で k=3)
    - ATR 計算 (Wilder's EMA)
    - 12 pattern 各々の合成 instance で hit
    - bar-close gate (wick-only breakout が除外されること)
    - re-entry dedup (同 pivot tuple で 1 件のみ)
    - SL/TP/Entry 計算の正しさ (各 pattern について analytic 値と一致)
- `tests/fixtures/manual_chart_pattern_labels.csv` (new) — Codex 生成の regression fixture
- `knowledge-base/wiki/strategies/s6-chart-pattern.md` (new) — strategy doc, 12 pattern 数学仕様, Wave 計画
- `knowledge-base/wiki/decisions/s6-w1p0-detector-2026-05-03.md` (new) — Phase 0 verdict
- `data/chart_patterns.db` (new, .gitignore 確認)
- `.ai/runs/<run-dir>/final.md`

Codex MAY NOT change:

- `app.py`, `modules/`, `strategies/` (LIVE/Shadow 配信は Wave 4 まで触らない)
- 既存の戦略 / Tier / config
- `data/cache/massive/*.parquet` (read-only)
- `.env`, OANDA secrets
- 既存未コミット変更

## 8. Required Reading

- `CLAUDE.md` (Rule 2 Fast & Reactive: detector は LIVE 露出なし、Wave 1 は実装・テストのみ)
- `wiki/lessons/index.md` の `feedback_codex_schema_hallucination`, `feedback_codex_mock_test_trap`, `feedback_label_empirical_audit`
- `wiki/strategies/s4-connors-raschke-80-20.md` (新戦略 doc 構造の参考)
- `tools/s4_connors_raschke_bt.py` (もし存在: parquet 読み込みパターンの参考)

## 9. Acceptance Criteria

- [ ] `python3 tools/s6_chart_pattern_detector.py --self-test` で 12 pattern 全ての合成 hit を表示
- [ ] `pytest tests/test_s6_chart_pattern_detector.py -q` 全 pass (≥ 20 tests)
  - 必須: bar-close gate test
  - 必須: re-entry dedup test
  - 必須: 12 pattern 各々の synthetic hit test
  - 必須: SL/TP の analytic 値一致 test
- [ ] `python3 tools/s6_run_w1p0.py --pair USD_JPY --tf M5` 実行で:
  - signal 総数 ≥ 360 (各 pattern N ≥ 30 を期待、足りない pattern は doc に明示)
  - SQLite UNIQUE 制約違反 0 件
  - 実行時間 ≤ 10 分
- [ ] `data/chart_patterns.db` の `chart_pattern_signals` 表に行が入る
  - `SELECT pattern_name, COUNT(*), MIN(signal_ts), MAX(signal_ts) FROM chart_pattern_signals GROUP BY pattern_name` で 12 行
- [ ] `wiki/strategies/s6-chart-pattern.md` に: 12 pattern 数学定義, Wave 計画, Phase 0 結果, next task 候補
- [ ] `wiki/decisions/s6-w1p0-detector-2026-05-03.md` に: signal 数分布, duration 分布 (median/p95), pattern_height_atr 分布, sample signal table (各 pattern 1 件), verdict
- [ ] `.ai/runs/<run-dir>/final.md` に: status, files changed, signal 総数, pattern 別内訳, residual risks, 次タスク (= Wave 2 BT)
- [ ] `app.py` / `modules/` / `strategies/` 編集 0 件

## 10. Verification Commands

```bash
# 0. parquet 確認
python3 -c "import pandas as pd; df=pd.read_parquet('data/cache/massive/USD_JPY_5m.parquet'); print(df.shape, df.index.min(), df.index.max())"
# 期待: (903828, 7) 2014-01-02 04:55:00+00:00 2026-04-30 23:55:00+00:00

# 1. Self-test (合成 instance で 12 pattern hit)
python3 tools/s6_chart_pattern_detector.py --self-test

# 2. Unit tests
python3 -m pytest -q tests/test_s6_chart_pattern_detector.py

# 3. Production run
python3 tools/s6_run_w1p0.py --pair USD_JPY --tf M5 \
  --parquet data/cache/massive/USD_JPY_5m.parquet \
  --db data/chart_patterns.db

# 4. Signal 集計
sqlite3 data/chart_patterns.db "SELECT pattern_name, COUNT(*) AS n, ROUND(AVG(duration_bars),1) AS dur_mean, ROUND(AVG(pattern_height_atr),2) AS h_atr FROM chart_pattern_signals GROUP BY pattern_name ORDER BY pattern_id;"

# 5. UNIQUE 違反 0 件確認
sqlite3 data/chart_patterns.db "SELECT pattern_id, pivot_anchor_ts, pivot_opposite_ts, COUNT(*) FROM chart_pattern_signals GROUP BY 1,2,3 HAVING COUNT(*) > 1;"
# 期待: 0 行

# 6. Bar-close gate 効果
sqlite3 data/chart_patterns.db "SELECT pattern_name, MIN(signal_ts), MAX(signal_ts) FROM chart_pattern_signals GROUP BY pattern_name;"
```

## 11. Codex Instructions

これは **Rule 2 (Fast & Reactive)** タスク。LIVE / Shadow 配信は Wave 4 まで一切なし、本 task は detector + ラベル化のみ。

**絶対遵守**:
- §3 の 12 pattern 数学定義は LOCK。閾値定数を勝手に変えない。
- §4 の SQLite DDL を `tools/s6_chart_pattern_detector.py` 冒頭にコメント or schema constant として直接埋め込む (`feedback_codex_schema_hallucination` 回避)
- bar-close gate / re-entry dedup の test を書かずに実装すると `feedback_codex_mock_test_trap` 違反
- パターン #2 (rising_wedge) / #5 (falling_wedge) はノートに従い順張り方向で実装。BT 結果次第で Wave 2 で逆転判定 (S3 COT literal の教訓)
- detector は時系列 forward-only に動作させる (look-ahead bias 禁止: bar `t` の signal は `bar[0..t]` のみで決定)
- Pattern instance 単位の dedup は UNIQUE 制約 + insert-or-ignore で実装

**禁止事項**:
- `app.py` / `modules/` / `strategies/` の編集
- BT loop の実装 (Wave 2 別 task)
- Live trading / OANDA bridge への接続
- `wiki/index.md` / `wiki/tier-master.md` の更新 (新戦略は Wave 4 で初めて Tier 登録)

`feedback_success_until_achieved` 通り、verdict が ACCEPT 未満で closure 短絡禁止。
- signal 総数 < 360 → Phase 0 NEEDS_MORE_EVIDENCE: どの pattern が hit 不足か analyses/ で原因特定
- pattern 別 N < 30 が 3 つ以上 → 数学定義の閾値再検討提案 (LOCK 解除には別 task)

PR 作成は本タスクで実行しない。proposal doc + detector 実装 + test のみ。Claude review 後、別 task で commit/deploy。

最終レポートには status, files changed, signal 総数 (pattern 別内訳), regression fixture 30 件の固定値, residual risks, 次タスク (= Wave 2 BT spec proposal) を含む。

2026-05-03T12:38:32.259312Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
2026-05-03T12:38:32.607806Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
2026-05-03T12:38:33.134972Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 2/5
2026-05-03T12:38:33.929911Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 3/5
2026-05-03T12:38:35.075227Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 4/5
2026-05-03T12:38:36.916844Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 5/5
2026-05-03T12:38:40.287405Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 1/5
ERROR: Reconnecting... 2/5
ERROR: Reconnecting... 3/5
ERROR: Reconnecting... 4/5
ERROR: Reconnecting... 5/5
ERROR: unexpected status 401 Unauthorized: Missing bearer or basic authentication in header, url: https://api.openai.com/v1/responses, cf-ray: 9f5f531f0851b84b-PDX, request id: req_d18832f64c2242ef9e98abb411036403
ERROR: unexpected status 401 Unauthorized: Missing bearer or basic authentication in header, url: https://api.openai.com/v1/responses, cf-ray: 9f5f531f0851b84b-PDX, request id: req_d18832f64c2242ef9e98abb411036403

```
