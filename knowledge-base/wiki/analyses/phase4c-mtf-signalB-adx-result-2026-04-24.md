# Phase 4c Track B — MTF Signal B (ADX) Result (2026-04-24)

> **STATUS: Scenario A** (本 pre-reg 下で null, Track B closure にあらず)

**Pre-reg**: [[pre-registration-phase4c-mtf-signalB-adx-2026-04-24]] (LOCKED)
**Script**: `/tmp/phase4c_mtf_signalB_adx_test.py`
**Raw output**: `/tmp/phase4c_signalB_output.txt`
**Summary JSON**: `/tmp/phase4c_signalB_summary.json`
**Upstream (Signal A)**: [[phase4c-mtf-regime-result-2026-04-24]]

## Result (pre-reg primary decision)

```
Scenario A:  SURVIVOR=0  CANDIDATE=0  REJECT=1  INSUFFICIENT=7
Bonferroni alpha = 2.083e-3  (M=24: Signal B+C+D each x 8 strats)
Train: 841 trades (2026-04-08 ~ 2026-04-17)
Test:  841 trades (2026-04-17 ~ 2026-04-24)
```

**全体判定**: 本 pre-reg (Wilder ADX14, thresh 25/20, 50/50 split) では ADX-based
MTF regime classifier に **significant edge 不検出**.

## Primary table (test held-out)

| Strategy | Nat | H* | N_a | N_m | WR_a | Wilson95_a | WR_m | dWR | h | Fisher p | Verdict |
|----------|-----|----|-----|-----|------|-----------|------|-----|---|----------|---------|
| ema_trend_scalp | TREND | 30m | 132 | 191 | 19.7% | [13.8,27.3]% | 22.5% | −2.8% | −0.069 | 5.83e-1 | **REJECT** |
| stoch_trend_pullback | TREND | 1h | 6 | 35 | 16.7% | [3.0,56.4]% | 17.1% | −0.5% | −0.013 | 1.00 | INSUFFICIENT |
| bb_squeeze_breakout | BREAKOUT | 5m | 10 | 3 | 20.0% | [5.7,51.0]% | 0.0% | +20.0% | +0.927 | 1.00 | INSUFFICIENT |
| vol_surge_detector | BREAKOUT | 1h | 4 | 26 | 0.0% | [0.0,49.0]% | 30.8% | −30.8% | −1.176 | 5.50e-1 | INSUFFICIENT |
| bb_rsi_reversion | RANGE | 1h | 61 | 26 | 31.1% | [20.9,43.6]% | 23.1% | +8.1% | +0.182 | 6.06e-1 | INSUFFICIENT |
| engulfing_bb | RANGE | 30m | 48 | 23 | 20.8% | [11.7,34.3]% | 34.8% | **−13.9%** | −0.314 | 2.49e-1 | INSUFFICIENT |
| fib_reversal | RANGE | 1h | 34 | 10 | 17.6% | [8.3,33.5]% | 20.0% | −2.4% | −0.060 | 1.00 | INSUFFICIENT |
| sr_channel_reversal | RANGE | 5m | 33 | 12 | 21.2% | [10.7,37.8]% | 50.0% | **−28.8%** | −0.614 | 7.57e-2 | INSUFFICIENT |

**Kelly half (aligned)**: 全て負 (min −0.194 stp, max −0.102 bb_squeeze). 本 system は
aligned 側で entry しても test 期間で期待値負.

## Hypothesis vs result

| H | Prediction | Observation | Verdict |
|---|-----------|-------------|---------|
| H1 moderate | TREND 戦略 (ems, stp) は H=15m/30m で aligned WR ± | ems dWR=−2.8% (p=0.58), stp null | null (期待 range 内だが有意差なし) |
| H2 moderate | RANGE 戦略は RANGE regime で aligned WR +5〜10% | **Aggregate dWR=−7.1%** (reversed) | **falsified in direction** (p=0.26 なので有意ではないが signal 反転) |
| H3 weak | BREAKOUT は H=15m で positive dWR | Aggregate dWR=−13.3% (N=14 test aligned) | INSUFFICIENT (反転示唆) |
| H4 overall | 3/8 以上 SURVIVOR なら Scenario C | 0 SURVIVOR | Scenario A (pre-reg 予想外れ) |

## 本質的な所見 (quant, 深掘り)

### 1. counter-intuitive "逆方向" signal の reproducibility

**engulfing_bb** は train/test 両方で aligned (ADX-RANGE) が misaligned (ADX-TREND) より
WR が低い — 逆エッジの possibility:

| | Train (h=−0.586) | Test (h=−0.314) |
|-|------------------|-----------------|
| ADX-RANGE (aligned): WR | 18.2% (N=22) | 20.8% (N=48) |
| ADX-TREND (misaligned): WR | 44.8% (N=29) | 34.8% (N=23) |

Train dWR=−26.6%, Test dWR=−13.9%. **Sign flip なし, 符号安定**. Bonferroni 未達 だが
"RANGE 戦略は実は TREND regime で動く" hypothesis の seeds あり. これは a priori 直感
と逆で、post-hoc narrative に走らないよう慎重な解釈が必要.

### 2. stoch_trend_pullback の train→test decay

Train で stp の aligned-TREND が misaligned-RANGE より **41.6% 低い WR** (N_a=50,
N_m=27, h=−0.915) という極端な effect. Test では h=−0.013 に regress (N_a=6, N_m=35 で
aligned side 極小). 原因候補:
- **Selection bias**: argmax |h| 探索で極端に負の h が引き寄せられた (candidate H=4)
- **Train 期間特異性**: 2026-04-08〜04-17 の market condition artifact
- **Period instability**: stp 自体が過渡期 (直近 14 days の bt-live-divergence の影響)

Sign flip ではなく attenuation. これは over-fitting の古典的 pattern.

### 3. Train→Test sign flip 発生率

| Signal | Sign flip 戦略数 / 8 | Notes |
|--------|--------------------|-------|
| A (EMA slope, 70/30) | 3 (ems, efb, fr) | candidate H=4 argmax |
| B (ADX, 50/50) | 2 (brr, ems) | 同様の argmax 構造 |

Train ratio を 50% に下げた効果: **sign flip 頻度 1 戦略 減**. 完全解消せず.
Root cause は argmax-over-H selection bias であり、split ratio だけでは解けない.

### 4. Pair asymmetry (exploratory, Bonferroni 対象外)

| Pair | TREND nature × ADX-TREND aligned dWR | 方向 |
|------|------|-----|
| USD_JPY | +3.9% (N_a=67) | 弱 positive (直感通り) |
| EUR_USD | **−13.7%** (N_a=61) | negative (逆方向) |
| GBP_USD | −20.4% (N_a=10) | negative だが N 極小 |

USDJPY と EURUSD で方向が反対. Pair 別の **asset-specific regime dynamics** の可能性だが、
単一 pre-reg では検証不可. 次 session で pair-subset pre-reg 要検討.

### 5. 全 aligned side で half-Kelly 負 の意味

Primary 表 8 戦略の test aligned 側 half-Kelly は **−0.194 〜 −0.102** 全て負.
これは ADX signal が positive alignment を与える cell を選んでも **直近 1 週間で
全 strategy が負け continuum にある** ことを示唆. つまり:
- ADX signal の null は "ADX が効かない" の結果ではなく、
- "現在市場環境では any regime filter でも positive expectancy が出ない" の可能性
- Phase 4b の power denial と同じ root cause: **16 days では strategy 別 N 過少**

## Surviving negative knowledge (本 signal で確定)

1. **Wilder ADX(14) 25/20 classifier は、Signal A と同様、naïve MTF filter として機能しない**
   (16 days / 1682 trades scope)
2. **engulfing_bb は ADX-TREND regime で逆方向 edge の seeds** — train+test 一致の符号
   安定あり. 次 signal/session で RANGE-nature 戦略の ADX 逆向きフィルタを pre-reg 可能.
3. **stoch_trend_pullback は train で extreme negative h が argmax されやすい** — 次
   pre-reg は stp の H 探索空間制限 or 除外検討
4. **Pair asymmetry (USDJPY vs EURUSD) が TREND nature aligned dWR で逆転** — pair-subset
   の pre-reg が必要 (本 pre-reg の §8 Secondary に位置付けだったが、結果は subset の
   重要性を示唆)

## Authorization (per pre-reg §12)

Scenario A → **Signal B (ADX 25/20) 単独での routing design non-authorize**.

Track B 自体の closure にあらず — pre-reg §12 明文により Signal C, D, composite, pair-
subset 未検定. 次 session で移行.

## 次ステップ (必ず別 session で実施)

### Queued (優先順, 各 1 session)

1. **Signal C (structural HH/HL)** — pivot swing による structure break. pivot
   lookback 探索はせず, LOCK (例 5-bar pivot). Bonferroni family は M=24 のまま (Signal B+C+D).
2. **Signal D (composite)** — Signal A ∧ C (Signal B は null で composite 削除) または
   A ∧ B ∧ C の 3-way precision filter.
3. **Pair-subset pre-reg (USDJPY only)** — 本 result の pair asymmetry (USDJPY TREND
   aligned dWR +3.9%) を独立 pre-reg で再検定. Bonferroni は subset → α_cell = 0.05/3
   or 0.05/8 再考.
4. **Reversed alignment hypothesis** — engulfing_bb 逆方向 signal を pre-register (ただ
   し post-hoc narrative の余地があるので **慎重な separate pre-reg** 要)

### 暫定結論 (Signal A + B 後)

2 signals × 8 戦略 = 16 tests で **0 SURVIVOR, 0 CANDIDATE, 2 REJECT, 14 INSUFFICIENT**.
Power denial pattern が continuous. **Data 蓄積 (Phase C)** と **Signal family 拡張**
の両軸を並行で進める必要.

## References

- [[pre-registration-phase4c-mtf-signalB-adx-2026-04-24]] (本 pre-reg, LOCKED)
- [[pre-registration-phase4c-mtf-regime-2026-04-24]] (Signal A pre-reg)
- [[phase4c-mtf-regime-result-2026-04-24]] (Signal A result)
- [[phase4b-cell-edge-test-result-2026-04-24]] (先行 power denial)
- [[feedback_success_until_achieved]] (memory)
- [[feedback_label_empirical_audit]] (memory)
- [[feedback_partial_quant_trap]] (memory, PF/Wilson/Kelly 実装済)
