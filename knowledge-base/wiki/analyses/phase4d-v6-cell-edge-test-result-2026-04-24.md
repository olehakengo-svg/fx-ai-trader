# Phase 4d — v6 Cell Edge Test Result (2026-04-24)

**Pre-reg**: [[pre-registration-phase4d-v6-cell-edge-test-2026-04-24]]
**Script**: `/tmp/phase4d_v6_cell_edge_test.py`
**Output**: `/tmp/phase4d_output.txt` / `/tmp/phase4d_summary.json`
**Data**: Live trades from Render API, 2026-04-08 ~ 2026-04-24 (16 days)

## Result: **Scenario A** (power denial, 95% near-empty)

```
SURVIVOR=0  CANDIDATE=0  REJECT=0  INSUFFICIENT=120 (total combos=120)
Bonferroni M = 15 × 8 = 120, α_cell = 4.17e-04
```

### Data flow
- Total trades: 2580 → in-scope (USDJPY/EURUSD closed): 1824
- v6 cell3d mapping: 1824 → mapped 1824 (100%), R0 count=0
- 8 strategies active (N≥50 global)

### Strategy N (global, after mapping)

| Strategy | Nature | N |
|----------|--------|---|
| ema_trend_scalp | TREND | **434** |
| bb_rsi_reversion | RANGE | 273 |
| sr_channel_reversal | RANGE | 169 |
| engulfing_bb | RANGE | 135 |
| stoch_trend_pullback | TREND | 139 |
| fib_reversal | RANGE | 131 |
| vol_surge_detector | BREAKOUT | 93 |
| bb_squeeze_breakout | BREAKOUT | 86 |

1460 total → 15 PHASE_D_CELLS の外に落ちた trades と、cell 内でも分散.

### N distribution (120 combos)

| Bucket | Count | % |
|--------|-------|---|
| N≥30 (testable) | 2 | 1.7% |
| 10≤N<30 (sub-power) | 4 | 3.3% |
| N<10 (near-empty) | 114 | 95.0% |

**Testable combos (N≥30)** — 両方とも ema_trend_scalp:

| Strategy | Cell | N | WR | BEV | Wilson_lo | Fisher p | Kelly | Verdict |
|----------|------|---|----|----|-----------|----------|-------|---------|
| ema_trend_scalp | R2_trend_down__V_high__NY | 44 | 15.9% | 37.8% | 7.9% | 2.68e-03 | −0.220 | INSUFFICIENT* |
| ema_trend_scalp | R1_trend_up__V_high__NY | 31 | 16.1% | 41.3% | 7.1% | 5.27e-03 | −0.269 | INSUFFICIENT* |

*N≥30 だが α_cell=4.17e-4 を clear しないので REJECT 判定にならず (WF も N). Cohen's h は両者 −0.5 以上の強い negative. v5 Phase 4b では REJECT だった cells が v6 session 分割で N dilute + α tightened で null.

### Negative edge candidates (N≥10)

| Strategy | Cell | N | WR | BEV | Fp | Kelly |
|----------|------|---|----|----|----|-------|
| ema_trend_scalp | R2_trend_down__V_high__NY | 44 | 15.9% | 37.8% | 2.68e-03 | −0.220 |
| ema_trend_scalp | R1_trend_up__V_high__NY | 31 | 16.1% | 41.3% | 5.27e-03 | −0.269 |
| ema_trend_scalp | R1_trend_up__V_mid__NY | 13 | 0.0% | 26.5% | 2.65e-02 | 0.000 |
| ema_trend_scalp | R1_trend_up__V_high__London | 28 | 28.6% | 37.1% | 4.36e-01 | −0.149 |

**Pattern**: ema_trend_scalp は **NY session × trend regime × V_high** で一貫して
大幅 negative. v5 で REJECT された ema × R1/R2 V_high が **NY 側に集中** していた
ことを v6 が明示.

### Positive candidates (N≥10)

| Strategy | Cell | N | WR | BEV | Fp | Kelly |
|----------|------|---|----|----|----|-------|
| ema_trend_scalp | R6_reversal__V_high__NY | 10 | 50.0% | 34.5% | 3.29e-01 | +0.272 |
| bb_rsi_reversion | R2_trend_down__V_high__NY | 15 | 53.3% | 45.9% | 6.11e-01 | +0.127 |

N 不足で何も authorize 不能.

## v5 → v6 比較

| Metric | v5 Phase 4b | v6 Phase 4d |
|--------|-------------|-------------|
| Cells | 10 (2D) | 15 (3D intersection) |
| M | 80 | 120 |
| α_cell | 6.25e-4 | 4.17e-4 |
| Live mapped | 1340 | 1824 (grew) |
| SURVIVOR | 0 | 0 |
| CANDIDATE | 0 | 0 |
| REJECT | 2 | 0 |
| INSUFFICIENT | 70 | 120 |
| N≥30 combos | 2.8% (2/72) | 1.7% (2/120) |

**Session axis は dilution factor**. v5 で REJECT だった ema × R1/R2_V_high が
session 分割で Asia/London/NY に分かれ、NY のみ N sufficient だが α tightened で
α_cell clear 不可. Track A で "session axis は feature として情報 positive" と
記録したが、**edge detection 段階では N dilution が先に効く**.

## Hypothesis verification (vs pre-reg §7)

| H | Prediction | Result |
|---|-----------|--------|
| H1 moderate null | R1/R2_V_high × ema で REJECT 維持 | ❌ null (α tightened + N split で sub-threshold). ただし effect 方向は一貫 negative |
| H2 weak | R6_reversal__V_mid__Asia で RANGE 戦略 WR↑ | ❌ 全 RANGE 戦略 N≤2 で検定不能 |
| H3 moderate null | 80-90% INSUFFICIENT | ✅ **95% INSUFFICIENT で上回る** |

## 本質的な所見

### 1. Live 16日 1824 trades では v6 3D cells 全体が power 不足

Phase 4b (v5) と同じ結論. Cell 数 10 → 15 (50%↑) で N 密度は悪化. session 分割
が negative edge 信号を dilute.

### 2. Session 軸は edge detection では逆効果、stability では正効果

Track A (stability) で +5 cells 獲得した session 軸が、Phase D (edge) では
N 分散によりむしろ α clear を困難にする. これは **2 pipelines 間で session の
役割が非対称** であることを示す非自明な発見.

### 3. ema_trend_scalp × NY × V_high の pattern は v5/v6 で robust

具体的な点 edge は見つからないが、ema_trend_scalp の negative edge が
**NY session (UTC 13-21) × 高 vol regime** に集中する pattern は v5/v6 両方で
確認された. これは live で entry 抑制 (negative routing) の **strong candidate**.

## Authorization (pre-reg §6)

Scenario A → **Track D1 (live-only) closure**, Track D2 (BT 365d per-trade
logging) pre-reg を次 session で LOCK.

## 次ステップ

### Track D2 design (別 session)

Live 1824 trades が N 不足なら、BT 365d (~20,000+ trades 期待) に per-trade
entry_time logging を載せて cell re-bucketing で N 増強.

**方針候補**:
1. `run_scalp_backtest()` / `run_daytrade_backtest()` の trade_log に entry_time
   が既に含まれることを phase4d pre-reg 後に確認済. pair 別 365d BT を 8 戦略対応で回し、JSON 保存
2. BT 出力を cell3d lookup で re-bucket
3. Live と BT で verdict 一致する cells を **strong edge** として authorize

### Negative routing candidate (保留、要 BT 確認)

ema_trend_scalp × {R1_trend_up, R2_trend_down} × V_high × NY の block を
Phase D3 (BT 365d) で confirm すれば、本番 OANDA で entry 抑制すべき高信頼
negative cell として認定可能.

## References

- [[pre-registration-phase4d-v6-cell-edge-test-2026-04-24]] (本 pre-reg)
- [[phase4c-v6-classifier-stability-result-2026-04-24]] (PHASE_D_CELLS 15 authorization)
- [[phase4b-cell-edge-test-result-2026-04-24]] (v5 Phase D baseline)
- [[feedback_success_until_achieved]] (Null closure 禁止)
