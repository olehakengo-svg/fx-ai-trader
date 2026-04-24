# Pre-registration: Phase 4d v6 Cell Edge Test (2026-04-24)

**Locked**: 2026-04-24 (本 doc 確定後変更禁止)
**Upstream**: [[phase4c-v6-classifier-stability-result-2026-04-24]] (PHASE_D_CELLS=15 authorized)
**Upstream 2**: [[phase4b-cell-edge-test-result-2026-04-24]] (v5 power denial 実績)

## 0. Rationale

v6 classifier stability 検定で PHASE_D_CELLS = 15 cells (USDJPY ∩ EURUSD)
authorized. これら 15 cells × 8 active strategies = 120 (cell, strategy) combos に対し
**per-cell edge detection** を Phase 4b と同じ framework で実施する.

Phase 4b (v5 18 potentials, 72 testable) は SURVIVOR=0, CANDIDATE=0, REJECT=2,
INSUFFICIENT=70 の Scenario A (power denial) だった. v6 の cell 数は増えたが trades
は同じ (live 1340 mapped) のため **同様の power denial が想定される**. それでも本
Phase D を先に走らせる目的:

1. **null を記録** — BT 365d 再走査の前に live-only baseline を固定
2. **N distribution を v5 vs v6 で比較** — session axis 追加の N 分散効果計測
3. **REJECT 出現確認** — v5 で 2 REJECT あった cells が v6 session 分割で残るか

## 1. Data source (LOCKED)

**Primary**: Live closed trades from Render API
```
https://fx-ai-trader.onrender.com/api/demo/trades?limit=10000&status=closed
```

Filter:
- `instrument ∈ {USD_JPY, EUR_USD}`
- `status == "closed"`
- `entry_time >= 2026-04-08T00:00:00Z` (live cutoff date, Phase 4b と同じ)

## 2. Cell assignment (LOCKED)

v6 3D cell 定義 ([[phase4c-v6-classifier-stability-result-2026-04-24]]):

```
cell3d = f"{regime}__{vol_bin}__{session}"
regime ∈ {R1_trend_up, R2_trend_down, ..., R6_reversal}
vol_bin ∈ {V_low, V_mid, V_high}
session ∈ {Asia, London, NY, Off}  (UTC 0-7 / 7-13 / 13-21 / 21-24)
```

Trade → cell 割当は entry_time から 5m bar を bar 単位で lookup (Phase 4b と同じ).

**PHASE_D_CELLS (15, LOCKED)** — intersection from Phase 4c v6:
```
R1_trend_up__V_high__London, R1_trend_up__V_high__NY
R1_trend_up__V_mid__Asia, R1_trend_up__V_mid__London, R1_trend_up__V_mid__NY
R2_trend_down__V_high__NY
R2_trend_down__V_mid__London, R2_trend_down__V_mid__NY
R5_breakout__V_mid__Asia
R6_reversal__V_high__Asia, R6_reversal__V_high__London, R6_reversal__V_high__NY
R6_reversal__V_low__NY, R6_reversal__V_low__Off
R6_reversal__V_mid__Asia
```

## 3. Strategies (LOCKED)

Phase 4b と同じ 8 strategies (live N≥50 通過):
```
ema_trend_scalp (TREND), stoch_trend_pullback (TREND)
bb_squeeze_breakout (BREAKOUT), vol_surge_detector (BREAKOUT)
bb_rsi_reversion (RANGE), engulfing_bb (RANGE)
fib_reversal (RANGE), sr_channel_reversal (RANGE)
```

## 4. Statistical tests (LOCKED)

各 (strategy, cell) について:

- **N**: trades 数 (N_MIN = 30 for power sufficiency)
- **WR**: Win rate
- **Wilson 95% CI**: 下限・上限
- **Fisher exact 2-tail p** vs baseline WR_base (= strategy 全体の WR across all cells)
- **Kelly fraction**: `f* = max(0, (p − q/b)/b)` where p=WR, q=1-p, b=avg_win/avg_loss
- **WF 2-bucket same-sign**: trades chronological 前半/後半 split, 両方で h>0 or 両方で h<0

**Bonferroni correction**:
```
M = 15 × 8 = 120
α_family = 0.05
α_cell = 0.05 / 120 = 4.17e-4
```

## 5. Authorization rules (LOCKED)

### SURVIVOR (positive edge authorize)
- N ≥ 30
- Fisher p < 4.17e-4
- WR > WR_base (Cohen's h > 0.2)
- Kelly > 0.05 (economically meaningful)
- WF 2-bucket same-sign == True

### CANDIDATE (provisional, re-test next session)
- N ≥ 30
- Fisher p < 0.05 but ≥ α_cell
- WR > WR_base
- WF same-sign == True

### REJECT (negative edge, block candidate)
- N ≥ 30
- Fisher p < 4.17e-4
- WR < WR_base (Cohen's h < −0.2)
- Kelly < −0.05

### INSUFFICIENT
- N < 30 OR conflicting criteria

## 6. Scenario declarations (LOCKED)

- **Scenario A**: SURVIVOR=0, CANDIDATE<3 → power denial → Track D1 closure, Track D2 (BT 365d) に移行
- **Scenario B**: SURVIVOR ≥1 OR CANDIDATE ≥3 → limited authorize, Kelly Half routing 準備
- **Scenario C**: SURVIVOR ≥3 → full authorize, 本番 routing 実装

REJECT は scenario 判定に含めない (separate negative-knowledge として保持)

## 7. Pre-registered hypotheses

**H1 (moderate null)**: v5 で 2 REJECT だった cells (R1_V_high, R2_V_high) が
session 分割で REJECT 維持 (ema_trend_scalp × R2_trend_down__V_high__NY で N 十分かつ REJECT)

**H2 (weak)**: RANGE 戦略群 (4 strategies) のうち R6_reversal__V_mid__Asia で
WR 上昇 (reversal regime に RANGE 戦略が aligned)

**H3 (moderate null)**: 全体 Scenario A — v5 Phase 4b で 97% INSUFFICIENT だったので
120 combos でも 80-90% INSUFFICIENT 想定

## 8. Disallowed (post-hoc 禁止)

- α_cell 緩和 / N_MIN 切下
- PHASE_D_CELLS 再定義 / cell 追加
- Strategies 追加 / nature 再分類
- WF bucket 数変更 (現: 2)
- baseline WR 定義変更

## 9. Execution (本 session)

1. `/tmp/phase4d_v6_cell_edge_test.py` 作成 (phase4b script fork, cell assignment 3D 化)
2. Live trades fetch, v6 cell 割当, 120 combos 計測
3. Bonferroni α=4.17e-4 で判定
4. 結果を [[phase4d-v6-cell-edge-test-result-2026-04-24]] に記録
5. Scenario A なら Track D2 (BT 365d per-trade logging) pre-reg を次 session LOCK

## 10. References

- [[phase4c-v6-classifier-stability-result-2026-04-24]] (本 pre-reg 前提)
- [[phase4b-cell-edge-test-result-2026-04-24]] (v5 baseline)
- [[pre-registration-phase4b-cell-edge-test-2026-04-24]] (framework 継承元)
- [[lesson-premature-neutralization-2026-04-23]]
