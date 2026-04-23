# Phase 4a Classifier Stability Result (2026-04-23)

**Pre-registration**: [[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]]
**Script**: `/tmp/phase4a_classifier_stability.py`
**Raw**: `/tmp/phase4a_output.txt` / `/tmp/phase4a_summary.json`
**Data**: OANDA 5m candles, 2025-06-01 → 2026-04-23 (~10 months, N=66,543 / N=66,560)

## Result: ❌ 1/3 for both pairs → Classifier redesign 要

Per pre-reg §4 authorization rule: "0-1/3 GO: classifier redesign 必要 → 新 pre-registration".

| Pair | S1 monthly KS | S2 feature drift | S3 duration CV | Score |
|------|---------------|------------------|----------------|-------|
| USD_JPY | ❌ FAIL (min p=0.0000) | ❌ FAIL (max ratio=3.90) | ✅ GO (max CV=0.158) | **1/3** |
| EUR_USD | ❌ FAIL (min p=0.0050) | ❌ FAIL (max ratio=4.00) | ✅ GO (max CV=0.161) | **1/3** |

→ **Downstream strategy 設計 (D1-D4) は authorize されない**. Phase B (per-regime edge test) にも進まない.

## Regime distribution (informational)

両 pair でほぼ同様の分布:

| Regime | USD_JPY | EUR_USD |
|--------|---------|---------|
| R3_range_tight | 41.6% | 39.8% |
| R2_trend_down | 16.6% | 17.0% |
| R1_trend_up | 16.5% | 16.1% |
| R4_range_wide | 14.8% | 17.2% |
| R5_breakout | 5.3% | 4.9% |
| R6_reversal | 5.2% | 5.0% |

→ R3 (range_tight) が 40%と支配的。decision tree の default fallback が R3 であることが
原因の可能性 (§3 仕様)。現 threshold で trend/breakout/reversal をあまり拾えない構造。

## S1 FAIL 詳細

**USD_JPY** — 10 月次ペア中 最低 p=0.0000:
- 2025-08→2025-09: D=0.041 p=0.0001
- 2025-06→2025-07: D=0.009 p=0.9769 (この組は安定)
- `GO: 全 10 pairs で p > 0.05` → 複数 FAIL

**EUR_USD** — 最低 p=0.005.

→ **regime 分布が月ごとに shift**。classifier は adaptive のつもりで percentile 化したが、
構造 (tree 分岐の閾値) が固定であり、ある特徴量分布の mode shift に追従できなかった
可能性。

## S2 FAIL (metric 解釈に metadata)

**max_ratio ≈ 4.0 (target: < 0.3)**

### 実測 (USD_JPY)

| Regime | Feature | drift (max−min of月次 mean) | std of月次 mean | ratio |
|--------|---------|-----------------------------|------------------|-------|
| R2_trend_down | F1 | 0.062 | 0.016 | 3.90 |
| R3_range_tight | F2 | 0.023 | 0.006 | 3.85 |
| R4_range_wide | F1 | 0.023 | 0.006 | 3.82 |

### Metric 解釈について (honest note)

pre-reg §4 S2 は `|drift_month_to_month| / std < 0.3`. 本実装では
`drift = max(monthly_mean) − min(monthly_mean)`, `std = std(monthly_means)` と解釈した。

これは range/std 比であり、iid normal 11 months で理論期待値は約 3.1 (order statistics)。
実測 3.8-4.0 は iid null から大きく外れない → **S2 metric 自体が厳しすぎた可能性**。

ただし pre-reg は LOCKED であり、**本 run の判定はルール通り FAIL**. 再設計 pre-reg で
以下を検討:
- `drift = linear slope × span` (trend 型指標)
- or Mann-Kendall trend test p < 0.05 を FAIL 条件に
- std を monthly std (within-month) vs std of means で区別

## S3 PASS (参考)

Regime median duration は月ごとに安定。classifier noise は低。
両 pair で max CV ≈ 0.16 (threshold 0.3 以下).

## 判定と次のアクション

### 本 run の判定

- 両 pair で **1/3 GO** → pre-reg §4 authorization rule で "classifier redesign 要"
- **D1-D4 strategy 設計は authorize しない** ([[pre-registration-phase4-regime-native-2026-04-23]]
  の Phase B 待ち継続)

### 次の pre-registration に反映すべき知見

1. **S1 FAIL の根本原因**
   - 月次分布 shift → tree threshold (0.80 / 0.60 / 0.30 / 0.70) が特徴量分布の
     モード変化に硬直
   - 対案: threshold 自体を rolling percentile 系で動かす (例: "F3 が直近 500 bar の
     top 20% 内"で breakout) → これなら真に adaptive

2. **S2 metric 再設計**
   - range/std は iid でも約 sqrt(log N) 程度
   - Mann-Kendall or 線形 slope × span / std を使う

3. **R3 default dominance (40%)**
   - default fallback が支配的 = classifier の識別力不足
   - 対案: default なしで "unclassified" を許容、下流 edge test から除外

4. **分布の類似性** (両 pair で似た比率)
   - 同じ feature 設計が pair-agnostic に効く兆候はある
   - pair-specific tuning は後回しで良さそう

### Phase 4 Status Update

| Doc | Status |
|-----|--------|
| [[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]] | **FAIL 判定** (本 run). 新 pre-reg 要 |
| [[pre-registration-phase4-regime-native-2026-04-23]] | **BLOCKED** (upstream 未通過) |
| Downstream D1-D4 | **NOT AUTHORIZED** |

## 推奨 next session

1. **新 pre-registration** を作成: `pre-registration-phase4-adaptive-classifier-v2-<date>.md`
   - Threshold を rolling adaptive に変更 (メタ-percentile)
   - S2 metric を Mann-Kendall or slope-based に
   - Default R3 を "unclassified" に差し替え
2. v2 classifier 実装 + stability 再検定
3. 並行: [[pre-registration-label-holdout-2026-05-07]] は予定通り 2026-05-07 実行

### 保持する資産

- Feature set F1-F6 と rolling percentile 化の設計は **有効**
- Taxonomy 6 class は stability 検定の mechanism 自体を検証できた (= meta-validation OK)
- S1 KS / S3 CV の検定 framework は再利用可能

## References

- [[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]] (locked 前提)
- [[regime-characterization-2026-04-23]]
- [[cell-level-scan-2026-04-23]]
- [[pre-registration-phase4-regime-native-2026-04-23]] (blocked)
- [[pre-registration-label-holdout-2026-05-07]] (独立進行)
