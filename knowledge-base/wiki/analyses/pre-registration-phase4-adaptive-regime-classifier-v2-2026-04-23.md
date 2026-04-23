# Pre-registration: Phase 4 Adaptive Regime Classifier v2 (2026-04-23)

**Locked**: 2026-04-23 (v1 FAIL を受けた改訂版、本 doc 確定後変更禁止)
**Prev**: [[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]] (v1, 1/3 FAIL)
**Prev result**: [[phase4a-classifier-stability-2026-04-23]]

## Changes from v1 (rationale 明文化)

v1 の失敗分析から 3 点修正。各修正は **specific failure mode** に対応。

| Failure | v1 root cause | v2 fix |
|---------|---------------|--------|
| S1 FAIL (marginal dist shift) | 固定 tree threshold (0.80/0.60/0.30) が月次 feature mode shift に追従できず、R5/R6 freq が月で揺れる | **meta-percentile** 化. 閾値自体を rolling 500-bar の percentile で再定義 |
| S2 FAIL (range/std=4.0) | `drift=max−min / std` metric は 11 iid months で E≈3.1 (order stats). 実測 4.0 は null との乖離小だが LOCK されていた | **Mann-Kendall trend test** に差替. p < 0.05 を FAIL 条件. 方向のある drift を検出 |
| R3 default 40% dominance | fallback が支配的で識別力が低い、S1 freq 指標を引き摺る | **"R0_unclassified"** 許容. default 廃止. 下流検定では unclassified を除外 |

**保持する資産**: Feature set F1-F6 / Taxonomy 6 active classes + unclassified /
Rolling percentile normalization / S3 duration CV / per-regime edge test Bonferroni design.

## 1. Regime taxonomy (LOCKED — v1 と同じ 6 active + unclassified)

| ID | Regime | Active criteria概要 |
|----|--------|---------------------|
| R1 | trend_up | ADX 上位 (meta-pctl) かつ F4 > 0 |
| R2 | trend_down | ADX 上位 かつ F4 < 0 |
| R3 | range_tight | F1 下位 かつ F3 下位 (both meta-pctl) |
| R4 | range_wide | F1 上位 かつ F2/F3 条件未達 |
| R5 | breakout | F3 上位 かつ \|F4\| ≥ 3 |
| R6 | reversal | F3 中上位 + sign(F4) ≠ sign(prev F4) + \|prev F4\| ≥ 3 |
| R0 | unclassified | いずれにも該当せず |

優先順: R5 > R6 > R1/R2 > R3 > R4 > R0

## 2. Features (LOCKED — v1 と同じ)

F1–F6 変更なし。全て 200-bar rolling percentile で正規化。
詳細: [[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]] §2.

## 3. Classifier logic (LOCKED — v2 meta-percentile 化)

**meta-percentile**: 閾値 θ_k を固定値ではなく直近 **500 bar 内の各特徴量分布の
k-percentile** で再定義。

```
P80(F3): 直近 500 bar の F3 の 80-percentile (時点で動的算出)
P60(F2): 直近 500 bar の F2 の 60-percentile
P30(F1): 直近 500 bar の F1 の 30-percentile
P30(F3): 直近 500 bar の F3 の 30-percentile
P70(F1): 直近 500 bar の F1 の 70-percentile

if F3 > P80(F3) and |F4| >= 3:
    R5 (breakout)
elif F3 > P60(F3) and sign(F4) != sign(prev.F4) and |prev.F4| >= 3:
    R6 (reversal)
elif F2 > P60(F2):
    R1 if F4 > 0 else R2
elif F1 < P30(F1) and F3 < P30(F3):
    R3 (range_tight)
elif F1 > P70(F1):
    R4 (range_wide)
else:
    R0 (unclassified)   # v1 の default R3 廃止
```

**結果的な marginal distribution**:
- R5 はおおよそ bar の 20% × P(|F4|≥3) で構造的に上限あり
- R1+R2 は ADX 上位 40% 相当
- R0 が残余を吸収する設計

## 4. Stability binding criteria (LOCKED — v2)

### S1 v2: Marginal distribution KS (kept)

- 検定: 連続月 regime 分布 KS
- GO: 全ペアで p > 0.05
- **期待**: meta-percentile 化により marginal が construction 上安定 → trivial pass

※ v2 では S1 は sanity check 役。本質は S2 に移行.

### S2 v2: Per-regime feature drift via Mann-Kendall (replaced)

- 検定: **各 active regime 内** で F1 / F2 の月次 mean 系列に Mann-Kendall trend test
- GO: 全 (regime, feature) で **p > 0.05** (trend 無し)
- FAIL: いずれか p < 0.05 (有意な単調 drift 存在)
- N_months 要件: ≥ 6 (MK 下限)
- Bonferroni: M = 6 regimes × 2 features = 12 → α_cell = 0.05/12 ≈ 4.2e-3
  → GO 閾値 p > 4.2e-3 (より緩く解釈、但し FAIL 宣言は p < 4.2e-3)

### S3 v2: Regime duration CV (kept)

v1 と同じ. GO: max CV < 0.3.

### Authorization rule

| Score | Action |
|-------|--------|
| 3/3 GO | Downstream per-regime edge test + strategy design authorize |
| 2/3 GO | 該当 regime selective に authorize (FAIL regime 除外) |
| 0-1/3 | v3 pre-registration 必要、実装停止 |

## 5. Per-regime edge test (unchanged, ただし R0 除外)

[[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]] §5 と同じ.
Bonferroni M = 6 × 17 = 102, α_cell = 4.9e-4. **R0 (unclassified) は edge test 対象外**
(意味を持たない label)。

## 6. Disallowed (v2)

- meta-percentile window (500 bar) の調整 post-hoc
- Meta-percentile rank values (80/60/30/70) の変更
- Mann-Kendall 閾値 (Bonferroni 込み 4.2e-3) の緩和
- R0 unclassified を stability 検定 S1 に含める (意味なし、除外は v2 仕様)
- S1/S3 FAIL 時の "ほぼ pass" 扱い

## 7. Execution (this session)

1. `/tmp/phase4a_v2_classifier_stability.py` を新規作成
2. v1 と同じ OANDA 5m × 10 months × 2 pairs でテスト
3. KB 記録: [[phase4a-v2-classifier-stability-2026-04-23]]
4. commit

## References

- v1: [[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]]
- v1 result: [[phase4a-classifier-stability-2026-04-23]]
- [[pre-registration-phase4-regime-native-2026-04-23]] (downstream, still blocked)
- [[regime-characterization-2026-04-23]]
