# Phase 4c Signal D — Multivariate Logit Result (2026-04-26)

> **STATUS: Scenario A / Verdict NULL** — regime block は confounder control 後に**有意な情報を持たない**. Plan Section 8 §3 の "Track B closure 妥当 evidence" 該当.

**Pre-reg**: [[pre-registration-phase4c-signalD-multivariate-logit-2026-04-26]] (LOCKED)
**Plan**: `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` Phase II
**Upstream**:
- [[phase4c-signalC-field-ranking-result-2026-04-26]] (Scenario B, 4 CANDIDATE)
- [[phase4c-mtf-alignment-bug-audit-2026-04-26]] (Finding 1-4 confounder 設計に反映)

**Script**: `/tmp/phase4c_signalD_multivariate_logit.py`
**Output**: `/tmp/phase4c_signalD_output.txt`, `/tmp/phase4c_signalD_summary.json`

## Result

```
N (analysis ready) = 1802 trades
WR overall = 27.3%

Primary LR test (regime + interaction adds info):
  chi2 = 22.03  df = 21  p = 3.98e-1  *** NOT pass alpha=0.05 ***

Per-strategy h4 interaction Wald (Bonferroni alpha=6.25e-3):
  best:  bb_squeeze_breakout p=0.125
  count Bonferroni-pass: 0/8

GBM feature importance:
  session    : impurity 26.8%  permutation 31.4%  ← dominant
  entry_type : impurity 25.9%  permutation 34.6%  ← dominant
  spread_q   : impurity 14.0%  permutation 14.0%  ← dominant
  mtf_h4_label : impurity 7.2%  permutation 6.6%
  regime_4   : impurity 6.9%  permutation 5.7%
  range_sub  : impurity 7.2%  permutation 0.7%   ← noise
  instrument : impurity 6.3%  permutation 3.0%
  mtf_vol_state: impurity 5.8%  permutation 3.9%

Regime block (h4+range_sub+regime_4):
  impurity 21.3%, permutation 13.0%
```

**Verdict: NULL** (primary LR p=0.40, regime block contributes essentially zero
likelihood improvement over confounders). **Scenario A**.

## 核心的な所見

### 1. Phase I の 4 CANDIDATE は **confounder artifact**

Phase I で観測した dWR 17-20% effect (mtf_h4_label × bb_squeeze_breakout 等) は、
Phase II で `session + spread_q + entry_type + instrument + vol_state` を control
すると **likelihood に有意な寄与なし** (LR p=0.40, ほぼ完全 null).

つまり Phase I の "regime signal" は実際には:
- bb_squeeze_breakout の特定 session × spread × pair の subset 効果
- fib_reversal の TRANSITION = 特定 vol_state proxy
を regime field 経由で捉えていた**間接 effect**. Direct な regime causal effect ではない.

### 2. **真の dominant signal は session, entry_type, spread**

GBM permutation importance:
- **session: 31.4%** (Tokyo/London/NY/Overlap)
- **entry_type: 34.6%** (戦略固有 base WR)
- **spread_q: 14.0%** (pair 内 spread quartile)

3 features 合計で **80% の predictive power**. Regime/MTF features 全部足しても 13%
(noise レベル). **MTF route から外れた所に勝ち筋がある** ことを implies.

### 3. **per-strategy h4 interaction は 0/8 で Bonferroni 通過なし**

| Strategy | Wald χ² | p | Bonferroni (α=6.25e-3) |
|----------|---------|---|------------------------|
| bb_squeeze_breakout | 4.15 | 0.125 | ✗ |
| vol_surge_detector | 3.04 | 0.219 | ✗ |
| fib_reversal | 2.01 | 0.366 | ✗ |
| ema_trend_scalp | 1.90 | 0.386 | ✗ |
| engulfing_bb | 1.26 | 0.532 | ✗ |
| sr_channel_reversal | 1.11 | 0.575 | ✗ |
| stoch_trend_pullback | 0.06 | 0.970 | ✗ |

最良 (bb_squeeze_breakout) でも Bonferroni 17x gap. **Phase III (per-pair) 進行も
原則否定的**. Phase III は per-pair で `entry_type×mtf_h4_label` を再検定だが、
Phase II の aggregated null から考えると per-pair partition で SURVIVOR 創出は厳しい.

### 4. **Tertiary 04-20+ alignment 検定は技術的に失敗** (LL=NaN)

`mtf_alignment` extended model は subset N=898 で fitting 不安定 (NaN log-likelihood).
原因: 04-20+ subset で alignment level 別 N が薄い + interaction terms で perfect
separation. **本検定は inconclusive**.

### 5. **range_sub は permutation で noise レベル (0.7%)**

GBM impurity 7.2% に対し permutation 0.7%. これは impurity が "splits per 4-level
feature" を inflate しているだけで、**実際の予測寄与はほぼゼロ**. Phase I で
fib_reversal × TRANSITION の dWR=+19.2% が CANDIDATE 化したのは、TRANSITION が
特定 vol/spread 条件と相関した結果の **collinearity-driven false signal**.

## Hypothesis verification (vs pre-reg §6)

| H | Prediction | Observation | Verdict |
|---|-----------|-------------|---------|
| H1 strong | Primary LR p<0.05 | p=0.40 | **❌ falsified** |
| H2 moderate | GBM regime importance 5-15% | 13% (permutation) | ✓ confirmed in range |
| H3 weak | ≥1 strategy interaction Bonferroni 通過 | 0/8 | **❌ falsified** |
| H4 overall | Scenario B (CANDIDATE) | Scenario A (NULL) | ❌ overshoot null |

**全 strong hypothesis が反証**. Phase I で見えた "信号" は confounder-mediated.

## Plan Section 8 mapping

| 期待される転帰 | 該当判定 |
|--------------|--------|
| 1. Phase I で SURVIVOR 1+ → MTF route alive | ❌ |
| 2. Phase I null, Phase II で regime LR p<0.05 | ❌ (Phase II も null) |
| **3. Phase II null, GBM importance <5% (or 中程度) → MTF/regime 否定 evidence** | **△ 該当** (permutation 13% で marginal だが LR p=0.40 で full null) |
| 4. engulfing_bb reverse alignment SURVIVOR | n/a (Phase V 未実施) |
| 5. 全部 INSUFFICIENT → data 蓄積待ち | n/a |

**転帰 3 が最有力**. Track B (MTF approach) **closure 妥当な evidence が揃った**.
ただし plan Section 8 § "本 6-phase plan で系統的に検定し切る" 通り、Phase III/IV/V
を完全に skip するのではなく、**重みを下げて Phase III 1-2 セッションだけで結論
踏み固め** する判断.

## 新方向 (Phase II の真の収穫)

### 信号源の pivot

| 旧仮説 (Phase I/II で否定) | 新仮説 (GBM が示唆) |
|---------------------------|---------------------|
| MTF regime alignment が edge source | session × spread × strategy interaction |
| D1/H4/regime composite が WR を condition | UTC hour bucket と spread quartile が主要 confounder |
| 戦略の nature (TREND/RANGE) ごとに regime filter | 戦略固有の "勝てる時間帯 × 勝てる spread" を mining |

### 直接 actionable な未検証仮説

1. **session × strategy interaction**: GBM permutation で session 31.4% (regime 13%
   の 2.4x). 各戦略の "win session" × "lose session" を Bonferroni で identify.
2. **spread_q × strategy**: Audit F4 の "ema_trend_scalp × GBP_USD aligned 8.1%" は
   実は **spread_q=3 (上位 quartile)** で起きている可能性高い. spread_q 1-2 で
   re-routing する R2 提案が次の defensive 候補.
3. **session × spread interaction**: London Overlap × low-spread cell が universal
   high-WR と仮説. 確認できれば全戦略 baseline で可.

## Authorization (per plan Section 8)

- **Track B (MTF approach) は本 phase で closure 評価入り** — Phase III は
  "確認 of nullness" 1 session のみ実施し、追加 evidence なければ Track B 終了.
- **新 Track (Session × Spread routing) を Phase 4d として開始**.
- **既存 production の MTF gate 機能は留保** — Phase D A/B 比較 (mtf_gated vs
  label_only) は引き続き ground-truth 提供.
- **Audit R1-A (labeler bear-detection 改修)** は本 closure と独立に有効. EMA200
  anchor 問題は long-term USD/JPY 構造的限界で、別 horizon (60-120 days quantile)
  で再検定する価値ある (将来 bear market でこそ露呈する).

## 「MTF判定が出来ない」User の問いへの最終回答 (本日 4-phase 検証総括)

```
Signal A (EMA20 slope)        : Scenario A (η²<0.005, regime_labeler 既証)
Signal B (Wilder ADX 14)      : Scenario A (sign flip, power-limited)
Signal C (snapshot field rank): Scenario B (4 CANDIDATE, dWR 17-20%)
Signal D (multivariate logit) : Scenario A (CANDIDATE は confounder artifact 確定)
─────────────────────────────────────────────────────────────────
最終解: 「MTF判定」は元々**観測可能な edge を持たない**.
      Phase I の見かけ上の signal は session/strategy/spread に
      mediated された pseudo-signal.
      勝ち筋は MTF ではなく session × spread × strategy 構造.
```

## 暫定的 negative knowledge

1. **regime block (h4_label + range_sub + regime_4) は LR 検定で完全 null**
   (p=0.40, df=21). データ N=1802 で moderate effect ならあるべき水準を下回る.
2. **fib_reversal × TRANSITION の Phase I edge (dWR=+19.2%) は range_sub の
   collinearity-driven artifact**. permutation importance 0.7% で confirmed.
3. **bb_squeeze_breakout × mtf_h4_label=0 の Phase I edge も confounder mediated**.
   per-strategy Wald p=0.125, Bonferroni 17x gap.
4. **Track B 全 4 signal で 0 SURVIVOR**. 1804 trades / 18 days / 4 signal × 8
   strats = 256 testable cells で SURVIVOR 0. **MTF approach は本 data scope では
   dead.**

## 次セッション (3 paths, 優先順)

1. **Phase 4d Pre-reg: Session × Spread × Strategy routing** ← **Top priority**
   - GBM 上位 3 features の interaction を Bonferroni 厳格 pre-reg
   - 戦略別 "勝てる session × spread" cell 抽出
   - Phase II の真の収穫を直接 actionable に
2. **Phase III light**: Track B closure 確認 1 session
   - per-pair で USD_JPY のみ subset で Phase II 再走
   - null 確認後 Track B closure
3. **R1-A Labeler bear-detection 改修**: Independent track
   - 60-120 days quantile-based anchor 設計
   - long-term USD/JPY bull saturation 解消

## References

- [[pre-registration-phase4c-signalD-multivariate-logit-2026-04-26]] (本 pre-reg)
- [[phase4c-signalC-field-ranking-result-2026-04-26]] (Phase I, 4 CANDIDATE)
- [[phase4c-mtf-alignment-bug-audit-2026-04-26]] (audit findings 反映)
- [[phase4c-mtf-regime-result-2026-04-24]] (Signal A null)
- [[phase4c-mtf-signalB-adx-result-2026-04-24]] (Signal B null)
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` (上位 plan, Section 8 §3)
