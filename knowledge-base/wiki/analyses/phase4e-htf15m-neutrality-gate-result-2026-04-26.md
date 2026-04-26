# Phase 4e — 15m HTF Neutrality Gate Result (2026-04-26)

> **Status: PARTIAL — Step A complete, Step B/C deferred (BT runtime bottleneck)**

**Pre-reg**: [[pre-registration-phase4e-htf15m-neutrality-gate-2026-04-26]]
**Scripts**: `/tmp/phase4e_step_a_label_distribution.py`, `/tmp/phase4e_step_b_bt.py`
**Outputs**:
- `/tmp/phase4e_step_a_output.txt`
- `knowledge-base/raw/bt-results/phase4e-step-a-label-distribution-2026-04-26.json`

## Summary

Step A (descriptive 15m HTF label distribution) **完了**. Step B/C (365d BT × cell
edge test) は **runtime bottleneck により defer**. 別セッションで BT 高速化策込みで
再実行が必要 (詳細: §"Deferred work" 下).

Pre-reg LOCK は unchanged. Step B/C は同 pre-reg 下で次セッション実行する.

## Step A: 15m HTF label distribution (descriptive, ✅ complete)

OANDA 365d × 2 pairs × 15m bars (24,744 defined bars/pair after σ-window warmup).

| Pair | bars | TREND_UP | NEUTRAL | TREND_DOWN | UNDEFINED |
|------|-----:|---------:|--------:|-----------:|----------:|
| USD_JPY | 24,768 | 33.28% | **38.89%** | 27.83% | 0.10% |
| EUR_USD | 24,768 | 30.42% | **39.58%** | 30.01% | 0.10% |

### Run-length statistics

| Pair | NEUTRAL median | NEUTRAL max | TREND median | TREND max |
|------|---------------:|------------:|-------------:|----------:|
| USD_JPY | 75 min (5 bars) | 945 min | 120-135 min | 1,275 min |
| EUR_USD | 75 min (5 bars) | 1,275 min | 120 min | 1,185 min |

### Label switch rate

USD_JPY: 10.56%/bar, EUR_USD: 10.40%/bar — label persistence ~10 bars (~150 min)
平均、scalp 1 trade hold horizon (2-5 bars) と整合.

### Hypothesis verification (partial)

| H | Prediction | Result |
|---|-----------|--------|
| **H4 (null)** | NEUTRAL stay rate < 30% | **❌ Falsified** (USD_JPY 38.89%, EUR_USD 39.58%) |

NEUTRAL 帯の N 不足懸念は initial level で解消. ±0.5σ threshold は正規分布近似
中央 38.3% と整合 (slope_z は概ね Gaussian). H1/H2/H3/H5 は Step B/C で検定.

## Step B/C: BT 365d × cell edge test (deferred)

### 試行内容

`run_scalp_backtest(365d, interval=5m)` を 2 strategies × 2 pairs で実行し、
trade_log を 15m label で bucketing する script `/tmp/phase4e_step_b_bt.py` 作成.

### 失敗モード

**run_scalp_backtest 365d × 5m が極めて遅い**:

- 1st run (auto_start ON): 100+ 分経過しても USDJPY scalp BT 完了せず. demo_trader
  background threads (12 modes) が CPU 競合させているのが主因と推定.
- 2nd run (`BT_MODE=1 NO_AUTOSTART=1`): demo_trader auto-start skip 確認したが、
  scalp BT 自体が依然 70+ 分で USDJPY 単体 unfinished. CPU R 状態 active のまま.

### 原因分析

- ~75,000 5m bars/pair × `compute_scalp_signal` per bar
- BT 内で個別の OHLCV fetch (run_scalp_backtest L5159) で OANDA pagination
- 365d は default (7d) の **52x scale** だが non-linear (cache miss + indicator
  rolling window 再計算)

### 工学的解決候補 (次セッション pre-reg amend OR 工程変更)

1. **Vectorized signal compute**: `for bar in df: ...` を `df.apply(...)` に書き換え
   → 5-10x 高速化期待
2. **Multi-process pair parallel**: USD_JPY/EUR_USD を別 process で並列実行
   → wall-clock ~50% 短縮
3. **Cache + chunk**: OANDA bars を 1 度 fetch して disk cache、scalp BT は
   `_df_override` で再 fetch skip
4. **Lookback step**: 30d 単位で incremental BT → progress 可視化 + 中途 abort 可能

### Pre-reg LOCK 整合

§9 Execution Step B "BT 365d × 2 strategies × 2 pairs を実行" が deferred 状態.
**Pre-reg parameter は unchanged** (365d, 2 strategies, 2 pairs, M=6, α_cell=8.33e-3).
Post-hoc 修正なし. 次セッションで同 pre-reg 下で BT 再実行 (高速化策込みで).

## Authorization (deferred)

Scenario 判定は Step B/C 完了まで pending.

- ✅ Step A NEUTRAL 滞在率 39% 確認 → cell power 確保見込みあり
- ⏳ Step B/C → 次セッション

## EDGE.md reflection

本セッションでは **edge 検出未確定** のため EDGE.md 変更なし. 変更は Step C 結果後.

## 残課題 (next session)

1. BT 高速化 (vectorize / parallel / cache のいずれか) を選択して script 改修
2. `BT_MODE=1` で再実行 → trade_log 取得
3. 同 script Step C bucketing で per-cell metrics 計算
4. Bonferroni 判定 → SURVIVOR/CANDIDATE/REJECT 確定
5. Scenario B/C なら EDGE.md update

## 本セッションでの気付き (process knowledge)

- **`BT_MODE=1` env var で auto-start skip 可能** (app.py L13548). 今後の BT script
  必ずこの flag を front に明示すべき
- **`run_scalp_backtest` の 365d × 5m はデフォルト用法外**. lookback 7d (default)
  からの scaling が線形でない. 大規模 BT は dedicated runner (例:
  `tools/bt_365d_runner.py`) を使うべきだが、これも要 BT_MODE 確認

## References

- [[pre-registration-phase4e-htf15m-neutrality-gate-2026-04-26]] (本 pre-reg, LOCK 維持)
- [[phase4c-signalC-field-ranking-result-2026-04-26]] (H4 +20.5%/+18.9% 発見元)
- [[phase4d-v6-cell-edge-test-result-2026-04-24]] (live 16d power denial)
- [[manifests/SPEC]] (EDGE.md routing infrastructure)
- [[feedback_success_until_achieved]] (closure 短絡禁止 — defer は closure ではない)
