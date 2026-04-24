# Phase 4c Track B — MTF Regime Result (2026-04-24)

**Pre-reg**: [[pre-registration-phase4c-mtf-regime-2026-04-24]]
**Script**: `/tmp/phase4c_mtf_regime_test.py`
**Output**: `/tmp/phase4c_mtf_output.txt` / `/tmp/phase4c_mtf_summary.json`

## Result: **Scenario A** (SURVIVOR=0, CANDIDATE=0, REJECT=1, INSUFFICIENT=7)

```
Bonferroni α = 6.25e-3
Train: 1177 trades (2026-04-08 ~ 2026-04-21, 13 days)
Test:  505 trades (2026-04-21 ~ 2026-04-24, 3 days)
```

## Per-strategy result (test held-out)

| Strategy | Nature | H* (train) | N_a | N_m | WR_a | WR_m | dWR | h | Fisher p | Verdict |
|----------|--------|-----------|-----|-----|------|------|-----|---|----------|---------|
| ema_trend_scalp | TREND | 5m | 92 | 37 | 19.6% | 35.1% | **−15.6%** | −0.35 | 7.13e-2 | **REJECT** |
| stoch_trend_pullback | TREND | 15m | 24 | 5 | 20.8% | 0.0% | +20.8% | +0.95 | 5.53e-1 | INSUFFICIENT |
| bb_squeeze_breakout | BREAKOUT | 15m | 8 | 2 | 25.0% | 0.0% | +25.0% | +1.05 | 1.00e0 | INSUFFICIENT |
| vol_surge_detector | BREAKOUT | 5m | 10 | 6 | 50.0% | 33.3% | +16.7% | +0.34 | 6.33e-1 | INSUFFICIENT |
| bb_rsi_reversion | RANGE | 5m | 11 | 11 | 18.2% | 63.6% | **−45.5%** | −0.97 | 8.05e-2 | INSUFFICIENT |
| engulfing_bb | RANGE | 5m | 11 | 19 | 36.4% | 26.3% | +10.0% | +0.22 | 6.87e-1 | INSUFFICIENT |
| fib_reversal | RANGE | 5m | 7 | 15 | 0.0% | 13.3% | −13.3% | −0.75 | 1.00e0 | INSUFFICIENT |
| sr_channel_reversal | RANGE | 30m | 27 | 50 | 33.3% | 32.0% | +1.3% | +0.03 | 1.00e0 | INSUFFICIENT |

## 本質的な所見

### 1. Train→Test sign flip が著しい (overfitting evidence)

| Strategy | Train h | Test h | Sign flip |
|----------|---------|--------|-----------|
| ema_trend_scalp | +0.307 | −0.353 | **Yes** |
| engulfing_bb | +0.513 | +0.217 | No (weak) |
| fib_reversal | +0.200 | −0.748 | **Yes** |
| sr_channel_reversal | +0.020 | +0.028 | No |

Train で選んだ H* が test で完全に reverse する strategy が複数. これは:
- **candidate H=4** から argmax 選択 → multiple comparison burden が effective に inflate
- Train 13 days は 4-option 探索に対し **undertrained**
- 選択された H* の多くが最短 (5m) = **data 量多い方向に偏った artifact**

### 2. Power 不足 (7/8 INSUFFICIENT)

Test 3 days = 505 trades → strategy 別 10-90 trades → aligned/misaligned 分割で
殆どが N<30. Pre-reg §8 H3 (BREAKOUT INSUFFICIENT 期待) は of予想通り、だが **全 nature で** 同じ状況.

### 3. 部分的に有意な signal の存在

- ema_trend_scalp test: WR_a=19.6% vs WR_m=35.1%, **Fisher p=0.07** (unique direction)
  - TREND regime で **逆に WR 下がる** → Phase 4b の R1/R2_V_high REJECT と整合
- bb_rsi_reversion test: RANGE regime で WR=18.2% vs UP/DOWN regime で 63.6%
  - RANGE 戦略が RANGE regime で **負け** という逆結果 (N=11 で弱い)

これらは hint レベルだが、**MTF regime signal 自体は情報を持つ** 可能性示唆.

## Hypothesis verification (vs pre-reg §8)

| H | Prediction | Result |
|---|-----------|--------|
| H1 moderate | TREND aligned WR +5-10% | ❌ 逆方向 (ema) or INSUFFICIENT (stp) |
| H2 weak | RANGE regime で RANGE 戦略 WR↑ | ❌ 逆方向 (brr) |
| H3 moderate null | BREAKOUT INSUFFICIENT | ✅ 確認 |
| H4 overall null | Scenario A | ✅ **確認** |

## Authorization (pre-reg §5)

Scenario A → **Track B closure**. MTF-based routing design は authorize されない.

ただし以下は **保持する negative knowledge**:

1. **Signal A (EMA slope) は naïve には使えない** — train→test sign flip が頻発
2. **TREND 戦略 (ema_trend_scalp) は "trend regime で WR ↑" の直感と**逆**の挙動** — Phase 4b で既に示唆されていた pattern と整合
3. **Held-out 3 days test は power 不足** — Phase C 相当で N 蓄積後再検定する余地はある
4. 現データ量 (16 days, 1682 trades) では MTF alignment は practical edge source に**ならない**

## 本 Track の closure に関する解釈

"MTF alignment 自体が効かない" と結論してはいけない. 本結果は:
- **16 days 1682 trades での power denial**
- **Signal A (EMA slope, single definition) での null**

Signal B (ADX), C (structural HH/HL), D (2-TF composite) は未検定. また時間蓄積
(3-6 ヶ月) 後に同じ pre-reg で再検定する余地あり. ただし本 pre-reg §5 の literal で
**Track B は本 session で closure**.

## References

- [[pre-registration-phase4c-mtf-regime-2026-04-24]] (本 pre-reg)
- [[phase4b-cell-edge-test-result-2026-04-24]] (先行 power denial)
- [[phase4c-v6-classifier-stability-result-2026-04-24]] (parallel Track A result)
- [[lesson-premature-neutralization-2026-04-23]]
