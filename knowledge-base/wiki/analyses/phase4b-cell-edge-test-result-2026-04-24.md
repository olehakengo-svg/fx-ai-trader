# Phase 4b Cell-Level Edge Test Result (2026-04-24)

**Pre-registration**: [[pre-registration-phase4b-cell-edge-test-2026-04-24]]
**Script**: `/tmp/phase4b_cell_edge_test.py`
**Raw output**: `/tmp/phase4b_output.txt` / `/tmp/phase4b_summary.json`
**Data**: Production API closed trades (2026-04-08 ~ 2026-04-24) + OANDA 5m bars for v5 cell re-labeling

## Result: **Scenario A** (SURVIVOR = 0, CANDIDATE = 0)

```
SURVIVOR=0  CANDIDATE=0  REJECT=2  INSUFFICIENT=70  (testable cells=72)
Bonferroni M = 10 cells × 8 strategies = 80, α_cell = 6.25e-04
```

### Trade scope

| Stage | Count |
|-------|-------|
| total trades fetched | 2578 |
| in scope (USD_JPY + EUR_USD, CLOSED, WIN/LOSS) | 1824 |
| mapped to v5 cells | 1340 |
| unmapped (bar lookup miss) | 0 |
| R0 (unclassified, excluded) | 484 |

### Strategy N filter

**Active (N ≥ 50 total mapped trades)**: 8 strategies

| Strategy | N |
|----------|---|
| ema_trend_scalp | 337 |
| bb_rsi_reversion | 197 |
| stoch_trend_pullback | 102 |
| sr_channel_reversal | 99 |
| engulfing_bb | 95 |
| fib_reversal | 84 |
| vol_surge_detector | 72 |
| bb_squeeze_breakout | 65 |

**Dropped (N < 50)**: 33 strategies (doji_breakout N=4, dt_bb_rsi_mr N=24, 他多数).

## Analysis of the 72 testable (strategy, cell) cells

### N distribution

| N bucket | Count |
|----------|-------|
| N ≥ 30 | **2** |
| N 20-29 | 4 |
| N 10-19 | 20 |
| N 5-9 | 11 |
| N 1-4 | 35 |

**Only 2 cells reach the N≥30 threshold** for SURVIVOR candidacy. Both are
ema_trend_scalp × high-vol trend cells, and **both show significant NEGATIVE edge**:

| Strategy × Cell | N | WR | BEV | Fisher p | Kelly | Verdict |
|-----------------|---|-----|-----|----------|-------|---------|
| ema_trend_scalp × R2_trend_down__V_high | 74 | 17.6% | 36.8% | **4.08e-04** | −0.229 | **REJECT** |
| ema_trend_scalp × R1_trend_up__V_high | 62 | 21.0% | 39.2% | 2.66e-03 | −0.245 | **REJECT** |

R2_V_high の p=4.08e-04 は α=6.25e-4 を下回る (Bonferroni 有意). R1_V_high は nominal
p<0.01 だが Bonferroni 通過せず. いずれにしても Kelly 大きく負で edge 方向が reverse
(この cell で entry すると期待値マイナス).

### 10 cells with positive Kelly but INSUFFICIENT N

```
sr_channel_reversal    × R2_trend_down__V_high   N=10  WR=70.0%  BEV=37.8%  K=+0.558
bb_rsi_reversion       × R2_trend_down__V_mid    N=12  WR=50.0%  BEV=41.4%  K=+0.331
engulfing_bb           × R1_trend_up__V_high     N=11  WR=54.5%  BEV=34.7%  K=+0.293
stoch_trend_pullback   × R1_trend_up__V_mid      N= 5  WR=40.0%  BEV=20.0%  K=+0.282
vol_surge_detector     × R2_trend_down__V_mid    N= 6  WR=50.0%  BEV=33.1%  K=+0.256
bb_squeeze_breakout    × R1_trend_up__V_high     N=10  WR=50.0%  BEV=38.8%  K=+0.230
ema_trend_scalp        × R6_reversal__V_high     N=16  WR=37.5%  BEV=34.4%  K=+0.108
bb_rsi_reversion       × R2_trend_down__V_high   N=27  WR=48.1%  BEV=43.3%  K=+0.068
```

いずれも N 不足で CANDIDATE 判定に至らず (Wilson 95% lower > BEV+0.03 不成立).

## Hypothesis verification (vs pre-reg §8)

| Hypothesis | Prediction | Result |
|-----------|-----------|--------|
| H1 (moderate) | N 不足で 30-60% が測定不能 | ✅ **確認**. 72/170 = 42% testable, N≥30 は 2/170 のみ |
| H2 (moderate) | 1-3 cells が CANDIDATE (Scenario B) | ❌ **起きず**. 0 CANDIDATE |
| H3 (weak) | 1 cell が SURVIVOR (Scenario C) | ❌ **起きず**. 0 SURVIVOR |
| H4 (null) | Scenario A 再確認 | ✅ **該当**. ただし Phase 2 と性質が異なる |

## Phase 2 との差異

| 軸 | Phase 2 (session-based) | Phase 4b (v5 2D cells) |
|----|------------------------|------------------------|
| SURVIVOR | 0 / 240 | 0 / 80 |
| CANDIDATE | 0 / 240 | 0 / 80 |
| REJECT | 240 ほぼ全 (edge denial) | 2 (N=62, 74) |
| INSUFFICIENT | 少数 | **70 (97%)** |
| 主因 | 全面 regime mismatch | **N 不足 (16 days of data)** |

**Phase 2 は edge denial (Scenario A)**. **Phase 4b は power denial** であり、
edge の不在を実証したわけでは**ない**. 16 days の trade log で 170 cells を cover
するには structural に不足 (期待値: 1340 mapped / 170 cells ≈ 8 trades/cell).

## Key findings

1. **v5 classifier の cell mapping は機能している** — 1340/1824 mapped, 0 unmapped,
   484 R0 (expected: 2D cell 分類で ~25% R0 は妥当)
2. **ema_trend_scalp は high-vol trend cell で確実に逆エッジ** — 2 cells で Kelly≈-0.24,
   N=74 R2_V_high は Bonferroni 有意 (Fp=4e-4)
3. **10 cells で positive Kelly 候補あり**, ただし N=5-27 で判定不能
   - sr_channel_reversal × R2_V_high (K=+0.558, N=10) が最強候補
   - engulfing_bb × R1_V_high (K=+0.293, N=11) と bb_squeeze_breakout × R1_V_high (K=+0.230, N=10) は
     R1_V_high で **ema_trend_scalp と逆方向の edge** を示唆 (興味深い dual behavior)
4. **N 不足が gating constraint** — 期待 survivor power に 3-5x の data 蓄積が必要

## Authorization (per pre-reg §6)

Scenario A → **Phase 4 closure**. D1-D4 strategy routing design は authorize されない.

ただし pre-reg §6 は "pivot to other approaches" を許容. 本結果の **power-limited** な
性質を踏まえ、以下の 2 択を次 session で user 判断:

### Option 1 (pre-reg literal): Phase 4 closure
- v6 classifier redesign or holdout independent
- 現 v5 classifier は保持 (asset として)
- negative knowledge: ema_trend_scalp × high-vol trend = avoid

### Option 2 (Phase C pre-registration): N accumulation plan
- 現 170 cells scope を保持、追加 ~30-60 days の trade 蓄積待機
- Pre-register 条件: N≥30 reached cells subset に対し同じ Bonferroni criteria 適用
- Scenario A 再定義: N 不足 ≠ edge 不在、Phase C 後に再検定

**Phase C 案は post-hoc narrative ではなく、Phase 4b pre-reg H1 (N 不足期待) で
既に foreseen されていた状況への contingency**. ただし v5 pre-reg §6 は明示的に
Phase C を mention しておらず、authorize するには次 session で新規 pre-reg LOCK 要.

## Retained knowledge

- **v5 classifier**: LOCKED, 10 cells PHASE_B authorized (unchanged)
- **Negative edge confirmed (Bonferroni)**: ema_trend_scalp × R2_trend_down__V_high
  (Kelly=-0.229, Fp=4.08e-4, N=74)
- **Suggestive (not survivor)**: sr_channel_reversal × R2_V_high (K=+0.558 at N=10),
  engulfing_bb × R1_V_high (K=+0.293 at N=11)
- **8 strategies pass N≥50 total** (post-cutoff 2026-04-08)
- **BEV_WR framework**: per-cell TP/SL 中央値から計算、multi-pair 混在 cell も算出可能

## References

- [[pre-registration-phase4b-cell-edge-test-2026-04-24]] (本 pre-reg)
- [[phase4a-v5-classifier-stability-2026-04-23]] (v5 classifier, PHASE_B_CELLS authorize)
- [[cell-level-scan-2026-04-23]] (Phase 2, session-based)
- [[pre-registration-phase2-cell-level-2026-04-23]] (Phase 2 pre-reg)
- [[lesson-premature-neutralization-2026-04-23]] (Scenario A で strategy 全停止に走らない discipline)
- [[pre-registration-label-holdout-2026-05-07]] (独立 holdout, 並行進行)
