# Pre-registration: Phase 4b Cell-Level Edge Test (2026-04-24)

**Locked**: 2026-04-24 (v5 PHASE_B AUTHORIZED を受けて作成、本 doc 確定後変更禁止)
**Upstream**: [[phase4a-v5-classifier-stability-2026-04-23]] (v5, PHASE_B_CELLS=10)
**Classifier**: [[pre-registration-phase4-adaptive-regime-v4-2D-2026-04-23]] (2D)

## Purpose

v5 で PHASE_B AUTHORIZED された 10 cells × 17 strategies = **170 cells** で observational
edge detection を行う. Phase 2 [[cell-level-scan-2026-04-23]] で "全面 regime mismatch"
(0 / 240 survivor) を確認済だが、あれは session-based cell (asia/london/ny/off) で
evaluate した結果。**v5 は 2D (Regime × Vol) に再定義した cell space**. survivor が
存在するかを literal に検定する。

## 1. Scope (LOCKED)

### Cells (LOCKED from v5)

```
R1_trend_up × {V_low, V_mid, V_high}     (3 cells)
R2_trend_down × {V_mid, V_high}           (2 cells)
R5_breakout × {V_mid, V_high}             (2 cells)
R6_reversal × {V_low, V_mid, V_high}      (3 cells)
Total: 10 cells
```

### Pairs (LOCKED from v5)

- USD_JPY
- EUR_USD

(v5 で stability が authorize された pair のみ. 他 pair は別途 classifier stability 要)

### Strategies

**Definition**: Phase B の strategy scope は **本 pre-reg LOCK 時点で**
`/api/demo/trades` に `entry_type` として存在する全 distinct strategy 名のうち、
下記 N_min 要件を満たすもの。

**N_min filter**: 各 strategy で全 cell を通算して N ≥ 50 trades (post-cutoff 2026-04-08)
あるもののみ Phase B 対象。これ未満は "N_insufficient_strategy" として記録、検定外。

**理由**: 10 cells に分割する前に strategy-level で N ≥ 50 無ければ、cell-level で
N ≥ 5-10 per cell も困難。事前 power gate.

### Time window

- From: **2026-04-08** (Phase 0 cutoff、clean data 開始点)
- To: **2026-04-24** (本 session 実行時点)
- 約 16 days of closed trades

### Exclusions

- XAU: pair scope 外 (feedback_exclude_xau.md)
- is_shadow=0 and is_shadow=1 両方含む (Phase 2 と同じ方針)
- status != "CLOSED" の trade は除外

## 2. Cell mapping procedure (LOCKED)

各 trade について:

1. `instrument` と `entry_time` を取り出す
2. 該当 pair の 5m OHLCV bar (v5 classifier と同じ) を fetch
3. `entry_time` を含む 5m bar を特定 (bar start ≤ entry_time < bar start + 5min)
4. その bar の v4 classifier output (regime, vol) を lookup
5. cell = `{regime}__{vol}` (R0 の場合 cell="R0" で検定外)

実装: v5 script の df_f を再利用、entry_time から 5m index へ round-down で lookup.

## 3. Metrics per (strategy, cell) (LOCKED)

各 (strategy, cell) cell について:

| Metric | Definition | Threshold |
|--------|------------|-----------|
| N | trade 数 | ≥ 30 for survivor candidate |
| N_win | WIN 数 | — |
| WR | N_win / N | — |
| avg_pnl_pips | mean of pnl_pips | — |
| Wilson 95% CI | k=N_win, n=N から | lower > BEV_WR |
| Fisher exact 2-tail p | vs BEV_WR baseline | < α_cell |
| Kelly | WR × avg_win / avg_loss − (1-WR) | > 0 |
| WF 2-bucket | time-split (前半/後半) で WR 両方 ≥ BEV_WR | same-sign required |

### BEV_WR (break-even WR) per cell

Cell ごとに actual spread + slippage + SL:TP ratio から以下で計算:

```
BT_COST_pips = BT_COST[instrument]  # v3 Phase 2 と同じ: USDJPY=0.8, EURUSD=0.8
TP_target_pips = median(pnl_pips where outcome=WIN) (per cell)
SL_target_pips = |median(pnl_pips where outcome=LOSS)| (per cell)
BEV_WR = (SL_target_pips + BT_COST_pips) / (TP_target_pips + SL_target_pips + 2*BT_COST_pips)
```

## 4. Binding criteria — Survivor (LOCKED)

以下 **全 5 条件を満たす cell を survivor と宣言**:

1. **N ≥ 30** (WR estimate の minimal power)
2. **Wilson 95% lower > BEV_WR + 0.03** (実質 edge margin)
3. **Fisher exact 2-tail p < α_cell** (Bonferroni corrected)
4. **Kelly > 0.05** (practical deployment 価値)
5. **WF 2-bucket same-sign** (時代安定性 — 前半/後半 WR が両方 ≥ BEV_WR)

### Bonferroni α_cell

```
M = |cells| × |strategies_N50| = 10 × |strategies_N50|
α_cell = 0.05 / M
```

|strategies_N50| は本 run で確定. 期待 range: 5-15.

| |strategies_N50| | M | α_cell |
|-----------------|---|--------|
| 5 | 50 | 1.00e-3 |
| 10 | 100 | 5.00e-4 |
| 15 | 150 | 3.33e-4 |
| 17 | 170 | 2.94e-4 |

## 5. Candidate vs Survivor (LOCKED)

Phase 2 と同じ 2-level hierarchy:

- **CANDIDATE**: 条件 1, 2, 4 を満たす (N ≥ 30, Wilson lower > BEV+0.03, Kelly > 0.05)
  が Fisher Bonferroni には届かない cells
- **SURVIVOR**: 全 5 条件満たす

### Scenario definitions

| Scenario | Condition | Action |
|----------|-----------|--------|
| A | SURVIVOR = 0 且 CANDIDATE = 0 | 全面 regime mismatch 再確認. 実装停止 |
| B | SURVIVOR = 0 且 CANDIDATE ≥ 1 | marginal edge あり. Phase C (N 蓄積) |
| C | SURVIVOR ≥ 1 | D1-D4 strategy routing design authorize |

## 6. Authorization rule (LOCKED)

- **Scenario C**: D1-D4 (strategy routing table, per-cell selective) design 許可.
  ただし survivor cells のみが target.
- **Scenario B**: Phase C pre-registration 作成. 追加 N 蓄積方針検討.
- **Scenario A**: Phase 4 closure. 別 approach (v6 classifier redesign, 他 features,
  holdout test 独立進行) に pivot.

## 7. Disallowed (post-hoc 禁止)

- Cell definition の拡張 (pair-specific, union, etc.)
- Strategy scope の事後 filter (例: "EV 高い strategy のみ")
- α_cell の緩和
- BEV_WR の再定義
- WF bucket 数の変更 (2 に LOCK)
- N_min の緩和 (30 に LOCK)
- Candidate threshold の緩和
- Survivor 発見後の cell 追加

## 8. Expected outcomes (pre-registered hypothesis)

**H1 (moderate, 最有力)**: N 不足で多数の (strategy, cell) が測定不能.
Actual testable cells は 170 中 30-60%、α_cell 計算は実 strategy 数で決定.

**H2 (moderate)**: 1-3 cells が CANDIDATE (Scenario B).
v5 classifier が semantic stable cell を identify したので、Phase 2 の 0/240 よりは
改善が期待される。

**H3 (weak optimistic)**: 1 cell が SURVIVOR (Scenario C) — Bonferroni 170 を通過する
strong edge が存在する。

**H4 (null)**: Scenario A 再確認. 現 17 strategies は vol-conditioning しても
regime mismatch のまま.

H2 (Scenario B) が最も想定される結果。Scenario C は ambitious target.

## 9. Execution (this session)

1. `/tmp/phase4b_cell_edge_test.py` 新規作成
2. Production API で trade 取得
3. 5m bar fetch + v5 cell classification 再計算 (per pair)
4. trade → cell mapping
5. per (strategy, cell) で metrics 計算
6. Bonferroni 判定 + survivor/candidate 抽出
7. KB 記録: [[phase4b-cell-edge-test-result-2026-04-24]]
8. Commit

## 10. Handoff (next session)

- **Scenario C 時**: D1-D4 (strategy routing) design 着手
- **Scenario B 時**: Phase C pre-reg 作成
- **Scenario A 時**: session closure、holdout 独立進行継続

## References

- [[pre-registration-phase4-adaptive-regime-v5-per-cell-rule-2026-04-23]] (v5 classifier prereg)
- [[phase4a-v5-classifier-stability-2026-04-23]] (v5 result, PHASE_B_CELLS locked)
- [[pre-registration-phase2-cell-level-2026-04-23]] (Phase 2, session-based)
- [[cell-level-scan-2026-04-23]] (Phase 2 result, Scenario A)
- [[phase0-data-integrity-2026-04-23]] (data cutoff)
- [[lesson-premature-neutralization-2026-04-23]] (discipline 根拠)
