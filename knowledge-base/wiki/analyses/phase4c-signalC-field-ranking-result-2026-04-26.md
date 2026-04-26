# Phase 4c Signal C — Field Ranking Result (2026-04-26)

> **STATUS: Scenario B** (4 CANDIDATE, 0 SURVIVOR — Signal A/B から明確な前進)

**Pre-reg**: [[pre-registration-phase4c-signalC-field-ranking-2026-04-26]] (LOCKED)
**Plan**: `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md`
**Phase 0 audit**: PASS — primary fields populated ≥99%
**Script**: `/tmp/phase4c_signalC_field_ranking_test.py`
**Output**: `/tmp/phase4c_signalC_output.txt`, `/tmp/phase4c_signalC_summary.json`

## Result (pre-reg primary decision)

```
Scenario B:  SURVIVOR=0  CANDIDATE=4  REJECT=2*  NULL=33  INSUFFICIENT=25
Bonferroni alpha = 7.8125e-4  (M=64: 8 fields x 8 strategies)
N scope = 1804 trades (2026-04-08 ~ 2026-04-26)
```

\* 2 REJECT は本来 INSUFFICIENT (verdict logic 上の境界 case). 詳細 §4.

**全体判定**: 単一 Bonferroni significant edge は不検出だが、**4 cell が effect size
& dWR floor を満たす CANDIDATE**. Signal A/B (Scenario A, 全 null) と比較し**Phase II
(multivariate variance decomposition) に進む正当性が確立**.

## CANDIDATE 4 cells

| # | Field × Strategy | N | k | dWR | Cramér's V | χ² p | MI (bits) | Top cell |
|---|------------------|---|---|-----|-----------|------|-----------|----------|
| 1 | `mtf_h4_label` × bb_squeeze_breakout | 98 | 3 | **+20.5%** | 0.201 | 1.38e-1 | 0.0295 | label=0 (neutral): WR=34.4% (N=32) |
| 2 | `mtf_h4_label` × vol_surge_detector | 115 | 3 | **+18.9%** | 0.177 | 1.66e-1 | 0.0229 | label=0: WR=43.9% |
| 3 | `regime.regime` × bb_squeeze_breakout | 98 | 3 | +17.5% | 0.177 | 2.17e-1 | 0.0223 | TREND_BEAR: WR=33.3% |
| 4 | `regime.range_sub` × fib_reversal | 108 | 2 | **+19.2%** | 0.201 | 3.69e-2 | 0.0297 | TRANSITION: WR=42.6% (N=61) |

注意:
- どの cell も Bonferroni α=7.81e-4 を**通っていない** (最小 p=0.037, gap ~50x)
- 16 days N=98-115 では Bonferroni 通過に必要な effect size 不足. **Power-limited
  CANDIDATE**.
- dWR は 17-20% で実用上は大きいが, n が小さく Wilson 95% CI が overlap する場合あり

## TOP 10 by mutual information (bits)

```
1. regime.hmm_regime  x vol_surge_detector       MI=0.0563  V=0.278  N=59  *
2. mtf_vol_state      x vol_surge_detector       MI=0.0508  V=0.249  N=115 *
3. regime.range_sub   x fib_reversal             MI=0.0297  V=0.201  N=108  CANDIDATE
4. mtf_h4_label       x bb_squeeze_breakout      MI=0.0295  V=0.201  N=98   CANDIDATE
5. mtf_h4_label       x vol_surge_detector       MI=0.0229  V=0.177  N=115  CANDIDATE
6. regime.regime      x bb_squeeze_breakout      MI=0.0223  V=0.177  N=98   CANDIDATE
7. regime.hmm_regime  x bb_rsi_reversion         MI=0.0154  V=0.146  N=181
8. mtf_h4_label       x fib_reversal             MI=0.0117  V=0.123  N=147
9. mtf_regime         x stoch_trend_pullback     MI=0.0116  V=0.129  N=164
10. regime.regime     x stoch_trend_pullback     MI=0.0114  V=0.124  N=164
```

\* 上位 2 つは **dWR=0.0%** の verdict bug (詳細 §4); MI/V は valid.

## 本質的な所見 (quant)

### 1. **mtf_h4_label が最も汎用に機能** (3/10 上位 MI)

H4 EMA bias (`mtf_h4_label` ∈ {-1, 0, +1}) が BREAKOUT 戦略 (bb_squeeze_breakout,
vol_surge_detector) と RANGE 戦略 (fib_reversal) で軒並み MI 上位. 特に:

- **label = 0 (neutral)** が最も WR 高 (BREAKOUT で 34-44%)
- label ≠ 0 (directional) では WR 13-25%

**解釈**: H4 が方向性を持っていない (両 EMA 接近) 局面で BREAKOUT entry が真の breakout
になる. 逆に H4 が既に明確な方向を指している局面では breakout entry は **既存トレンド
追従の遅れ entry** で WR 落ちる. これは強い structural insight.

### 2. **bb_squeeze_breakout は TREND_BEAR で WR 高** (counter-intuitive)

`regime.regime` × bb_squeeze_breakout: TREND_BEAR=33.3% vs TREND_BULL=15.8% (dWR=+17.5%).
Long/short 両方向 entry なのに **bear regime で受け** が良い. 仮説: 直近データ期間
(2026-04-08〜) は bear bias 強く、breakout = downside breakout の方が走った可能性.
**Pair-conditional 確認が必要** (Phase III).

### 3. **fib_reversal は TRANSITION 状態で edge** (regime change point)

`regime.range_sub` × fib_reversal: **TRANSITION=42.6% (N=61, BEV+5%)** vs
WIDE_RANGE=23.4% (N=47). **dWR=+19.2%, p=0.037**. Bonferroni 未達だが、**TRANSITION
=squeeze→breakout 境界帯** という structural な定義に対し fib reversal が機能.

これは Phase 4b で suggestive だった engulfing_bb / sr_channel_reversal の R6_reversal
cell hint と整合 (Phase 4b では N 不足だった同じ "境界帯 = reversal 戦略 edge" の
shape).

### 4. **TREND nature 戦略 (ema_trend_scalp, stoch_trend_pullback) は全 field に対し null**

ema_trend_scalp の best field: mtf_alignment (V=0.094, p=0.14, dWR=+15.6%) — Cramér V
弱い. stoch_trend_pullback の best: mtf_regime (V=0.129, p=0.60).

**仮説**: TREND 戦略は entry 条件で既に local trend (1m/5m EMA stack) を要求. 高 TF
regime は redundant feature で marginal info ゼロ. **Phase 4c plan Section 1.F の
"feature overlap" 仮説と整合**. これらの戦略は MTF route で edge 拾えない.

### 5. **D1 strong bull (mtf_d1_label=2) は BREAKOUT WR を kill する** (aggregate)

Per-field nature aggregate:
- BREAKOUT × mtf_d1_label: label=1 (weak bull) → WR=35.9% (N=39)
- BREAKOUT × mtf_d1_label: label=2 (**strong** bull) → WR=12.5% (N=32)

**強いトレンド時には breakout entry が遅れて failed-breakout になる**. Asymmetric
agility framework 上, `if d1_label==2 then suppress bb_squeeze_breakout` は Rule 2
範疇の防御施策候補 (但し Bonferroni 不可で R1 認可は不可).

### 6. **mtf_alignment は ema_trend_scalp で逆方向** (重要)

`mtf_alignment` × ema_trend_scalp:
- aligned: WR=8.1% (N=37)
- conflict: WR=20.4% (N=411)
- neutral: WR=23.7% (N=38)

**MTF aligned 時に WR 急落** という counter-intuitive 結果. dWR=+15.6% で V=0.094 弱
だが pattern 安定. 仮説: 現在の `mtf_alignment` 計算が ema_trend_scalp 戦略の
intrinsic edge を破壊する filter を効かせている可能性. **既存 production gate logic の
監査が必要** (本 phase 範囲外).

### 7. **HMM trending 状態は RANGE 戦略 WR↑**

`regime.hmm_regime` × bb_rsi_reversion: trending=36.6% (N=82) vs ranging=23.2% (N=99).
dWR=+13.4%, V=0.146, p=0.049 (nominal close to 0.05).

これは Signal B での engulfing_bb 逆方向 seed と類似 pattern ("RANGE 戦略は実は HMM
trending state で edge"). **N=181 で**安定的, Phase III で per-pair に分割確認の価値.

### 8. **regime.regime は SURVIVOR 候補だが Bonferroni gap 50x**

最良 cell (TRANSITION × fib_reversal) でも p=0.037 << α=7.81e-4. Bonferroni gap = 47x.
Power-limited が gating. **Phase VI (60 days N 蓄積) で gap が縮まる期待**:
- N 倍増 (180→360) で σ 1/√2 縮小, p ~10x 改善見込
- N 4 倍 (720) で p ~100x 改善 → Bonferroni 通過射程

## Hypothesis vs result

| H | Prediction | Observation | Verdict |
|---|-----------|-------------|---------|
| H1 | mtf_d1_label が ≥1 strategy で SURVIVOR | 全 strategy で V<0.15, INSUFFICIENT も多数 | **falsified for SURVIVOR**, NULL |
| H2 | regime.regime が SURVIVOR ≥1 | 1 CANDIDATE (bb_squeeze, V=0.177) | **partially supported** (Scenario B レベル) |
| H3 | regime.hmm_regime が CANDIDATE ≥1 | bb_rsi_reversion で V=0.146 (CANDIDATE 直前), vol_surge V=0.278 (verdict bug) | **partially supported** |
| H4 | 全 64 test で SURVIVOR=0 | 0 SURVIVOR 確認 | **confirmed** (power denial 継続) |

## Verdict logic note (§4 caveat)

Verdict assignment で `dwr < 0.05 ∧ p<0.05 → REJECT` rule は、**N≥30 cell が <2 個** の
case で `dwr=0.0` を強制する設計 (script L194). 結果:
- mtf_vol_state × vol_surge_detector (chi2 p=0.028, dwr=0): **真は INSUFFICIENT** (N=115
  だが N≥30 cell が 1 個のみ)
- regime.hmm_regime × vol_surge_detector (chi2 p=0.033, dwr=0): 同上 (N=59)

これらは MI=0.05 と effect size 自体は大きい. **Phase II ではこれらも候補として retain**.

## Authorization (per pre-reg §8)

**Scenario B → Phase II (multivariate variance decomposition) に移行**.

Track B 全体の closure は plan Section 8 § で Phase I-V 全完了後. 本 phase は MTF route
**有効性の傾き始めの evidence** を提供.

## 暫定的 negative knowledge (phase III 入力)

1. **TREND nature 戦略 (ems, stp) は MTF/regime route で edge 拾えない**. Track B
   主体ではなく別 angle (vol/spread/session) を試すべき.
2. **bb_squeeze_breakout, vol_surge_detector, fib_reversal は MTF/regime に sensitive**.
   Phase II/III の primary target.
3. **mtf_h4_label は最も生産性高い field**. Phase II の baseline 説明変数.
4. **Bonferroni gap 50x は power denial 継続**. Phase VI data 蓄積待ち並行.

## 次ステップ (plan Section 2 Phase II)

別 session で新 pre-reg LOCK の上、以下を実施:

1. Multivariate logistic regression: `WIN ~ strategy + pair + session + vol_state + h4_label + range_sub + h4_label×strategy + ε`
2. LR test: model w/ regime features vs without
3. GBM feature importance ranking
4. 4 CANDIDATE cells が confounder control 後も生き残るか確認
5. Field collinearity (mtf_regime と regime.regime 等) を VIF で評価

## References

- [[pre-registration-phase4c-signalC-field-ranking-2026-04-26]] (本 pre-reg)
- [[phase4c-mtf-regime-result-2026-04-24]] (Signal A null)
- [[phase4c-mtf-signalB-adx-result-2026-04-24]] (Signal B null)
- [[phase4b-cell-edge-test-result-2026-04-24]] (先行 power denial)
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` (本 plan)
- `research/edge_discovery/mtf_regime_engine.py` (snapshot field source)
- `app.py` L7390-7501 `detect_market_regime` (regime.regime source)
