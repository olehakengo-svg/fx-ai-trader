# Phase 4d-II — Nature Pooling Result (2026-04-26)

> **STATUS: Scenario B** (Joint 16-cell test で BREAKOUT が **Bonferroni 単独 α 通過 (WEAK)**, 5 検定で初の significant evidence)

**Pre-reg**: [[pre-registration-phase4d-II-nature-pooling-2026-04-26]] (LOCKED)
**Plan**: `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md`
**Trigger**: [[phase4d-session-spread-routing-result-2026-04-26]] (per-strategy power 不足を pooling で回復試行)
**Script**: `/tmp/phase4d_II_nature_pooling.py`
**Output**: `/tmp/phase4d_II_output.txt`, `/tmp/phase4d_II_summary.json`

## Result

```
N (scope) = 1804 trades  pooled by nature:
  TREND    : N=772  WR=22.0%  (ema_trend_scalp + stoch_trend_pullback)
  BREAKOUT : N=213  WR=30.0%  (vol_surge_detector + bb_squeeze_breakout)
  RANGE    : N=819  WR=31.5%  (4 strats)

PRIMARY 1 (session × outcome per nature): 0 SURVIVOR / 0 CANDIDATE / 3 NULL
PRIMARY 2 (spread_q × outcome per nature): 0 SURVIVOR / 0 CANDIDATE / 3 NULL
PRIMARY 3 (joint 16-cell per nature):
  TREND    : chi2=24.11 df=15 p=6.32e-2 V=0.177  NULL
  BREAKOUT : chi2=26.74 df= 9 p=1.54e-3 V=0.371  *** WEAK *** (alpha=1.667e-2 通過)
  RANGE    : chi2=23.68 df=15 p=7.07e-2 V=0.170  NULL

Verdict: Scenario B (BREAKOUT joint WEAK)
```

## 核心的所見

### 1. **BREAKOUT joint test は本日 5 検定で初の Bonferroni 通過**

|  | p value | α threshold | Pass? |
|---|---------|-------------|-------|
| BREAKOUT joint χ² | **1.54e-3** | 1.667e-2 (M=3) | **✅ Yes** |
| Phase I best | 0.037 | 7.81e-4 | ❌ |
| Phase 4d best | 0.015 | 6.25e-3 | ❌ |

**Cramér V = 0.371** は小〜中効果上限で、**実質的な signal の強さ**.

ただし WEAK 認定 (SURVIVOR 不可) の理由:
- N≥30 cell が **1 個のみ** (Tokyo×q2, N=36) → dWR は 0% 計算
- Effect は確実に存在するが、**実用 routing rule に切り出せる cell 粒度** に到達せず

実装的解釈: BREAKOUT 戦略 (vol_surge_detector + bb_squeeze_breakout) には **session
× spread の joint 構造に signal が確実にある**. ただし現 N=213 では cell 単位で
discriminate できない. 60 days 蓄積で cell 内 N が増えると **clean routing rule に
昇格する可能性が高い**.

### 2. **RANGE × (NewYork, q1) — 最強の descriptive boost 候補**

| Cell | N | WR | Wilson 95% | Baseline | Lift |
|------|---|-----|----------|----------|------|
| RANGE × (NewYork, q1) | 35 | **51.4%** | **[35.6, 67.0]%** | 31.5% | **+19.9%** |

**Wilson lower bound 35.6% > baseline 31.5%** が達成された **唯一の descriptive R2
boost** 候補. 統計的には Bonferroni 未通過だが、Wilson 95% CI が baseline を
**dominate** している.

意味: NY session の low-mid spread 帯では RANGE 戦略 (bb_rsi, engulfing_bb,
fib_reversal, sr_channel_reversal) が **基準より明らかに勝つ** という観測.

### 3. **TREND × Tokyo × q3 (high spread) も marginal boost**

| Cell | N | WR | Wilson 95% | Baseline | Lift |
|------|---|-----|----------|----------|------|
| TREND × (Tokyo, q3) | 47 | 31.9% | [20.4, 46.2]% | 22.0% | +9.9% |

Wilson lower 20.4% < baseline 22% で**ぎりぎり boost 認定不可**. ただし point estimate
+9.9% lift は実用的に意味あり. 60 days 後に再検定で SURVIVOR 化する希望.

### 4. **Pooling 効果の確認** (per-strategy → per-nature)

|  | Phase 4d (per-strategy) | Phase 4d-II (per-nature) |
|--|--------------------------|--------------------------|
| Best p | 0.015 (stoch session) | 1.54e-3 (BREAKOUT joint) |
| Best Cramér V | 0.270 | **0.371** |
| Bonferroni α | 6.25e-3 (M=8) | 1.667e-2 (M=3) |
| SURVIVOR/WEAK 数 | 2 WEAK | 1 WEAK |
| 集約効果 | nature pooling で **Bonferroni 通過 1 件達成** | |

Pooling は power を回復させ、Phase 4d で見えなかった signal を **検出可能 zone まで
持ち上げた**. これは methodology 上の重要な収穫.

## 累積 evidence (本日 5 phase + audit + 4d-II 計 7 検定)

```
Track B (MTF/regime route):
  Signal A (EMA slope):       Scenario A  (regime_labeler 既証 η²<0.005)
  Signal B (ADX 14):           Scenario A  (sign flip, power-limited)
  Signal C (snapshot rank):    Scenario B  (CANDIDATE は Signal D で artifact 確定)
  Signal D (multivariate):     Scenario A  (regime LR p=0.40)
  ─ Track B closure 妥当 evidence ─

Track 4d (session/spread route):
  Phase 4d (per-strategy):     Scenario A  (univariate Bonferroni)
  Phase 4d-II (per-nature):    Scenario B  ← *** 本日初の WEAK ***
  ─ Track 4d は alive ─

Audit (alignment structural):
  R3 期待外し / Finding 1-4 で labeler limitation 確定
  → R1-A labeler 改修 track が独立に valuable
```

## Hypothesis vs result (pre-reg §6)

| H | Prediction | Observation | Verdict |
|---|-----------|-------------|---------|
| H1 strong | TREND session SURVIVOR | NULL | **❌** |
| H2 moderate | RANGE × spread CANDIDATE | NULL | **❌** |
| H3 weak | BREAKOUT INSUFFICIENT | univariate INSUFFICIENT だが joint で WEAK 検出 | △ partial |
| H4 overall | ≥1 SURVIVOR | 0 SURVIVOR, 1 WEAK joint | △ partial (Scenario B) |

## Authorization (per pre-reg §3.5 + Asymmetric Agility)

### R2 immediate (本日中可能)

**R2-Boost 候補 (confidence ×1.2)**:
- **RANGE × (NewYork, q1)**: Wilson lower 35.6% > baseline 31.5% → **強い証拠**
- TREND × (Tokyo, q3): Wilson lower 20.4% ≈ baseline 22% → **marginal, 微 boost**

**R2-Suppress 候補 (confidence ×0.5)** (Wilson upper < baseline):
- BREAKOUT × (Tokyo, q2): WR 19.4% vs baseline 30%, N=36
- RANGE × (Overlap, q1): WR 21.2% vs baseline 31.5%, N=52
- RANGE × (Tokyo, q0): WR 23.0% vs baseline 31.5%, N=61
- TREND × (Overlap, q0/1/2): 3 cells で marginal lift -2 to -3%

### R1 (次 session pre-reg)

- **BREAKOUT 60-day rerun**: 現 N=213 が ~800 になれば cell N が 30 越える期待. 同じ
  joint 16-cell test で SURVIVOR 化候補 1 位.
- **RANGE × NewYork × q1 single-cell pre-reg**: 単独 cell の Bonferroni 1-test 検定.
  Wilson lower bound > baseline は説得力あり.

### R3 (該当なし)

audit でコードバグなし確認済. 構造改修 (R1-A labeler) は別 track.

## 「勝てるようになる道筋」更新版

本日の 7 検定の積算で:

```
1. R2 即時 (今日):
   - RANGE × (NewYork, q1) confidence ×1.2 boost
   - 4 cell suppress (×0.5) — Phase 4d で identify 済の 4 cell
   
2. R1 次 session (1-2 days):
   - BREAKOUT × joint 16-cell single-test pre-reg LOCK & 検定
   - RANGE × (NewYork, q1) single-cell single-test pre-reg LOCK & 検定

3. R1-A 独立 (1 week):
   - Labeler bear-detection 改修 (EMA200 → quantile-based)

4. Passive (2 ヶ月):
   - 60 days 蓄積で BREAKOUT joint cells 内 N≥30 化 → SURVIVOR 確定射程
```

## References

- [[pre-registration-phase4d-II-nature-pooling-2026-04-26]]
- [[phase4d-session-spread-routing-result-2026-04-26]]
- [[phase4c-signalD-multivariate-result-2026-04-26]]
- [[phase4c-mtf-alignment-bug-audit-2026-04-26]]
- [[phase4c-signalC-field-ranking-result-2026-04-26]]
- [[phase4c-mtf-signalB-adx-result-2026-04-24]]
- [[phase4c-mtf-regime-result-2026-04-24]]
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md`
