# Pre-registration: Phase 4 Adaptive Regime Classifier v3 (2026-04-23)

**Locked**: 2026-04-23 (v2 2/3 結果を受けた S1 再定義版、本 doc 確定後変更禁止)
**Prev**: [[pre-registration-phase4-adaptive-regime-classifier-v2-2026-04-23]] (v2, 2/3 ambiguous)
**Prev result**: [[phase4a-v2-classifier-stability-2026-04-23]]

## Motivation (v2 → v3)

v2 で S2 (Mann-Kendall) / S3 (duration CV) は PASS。S1 (monthly KS) のみ FAIL.

v2 の S1 は **regime label の月次頻度分布** を KS 検定していた。meta-percentile 設計下では:
- 各特徴量の marginal 分布は construction 上 pin される
- しかし特徴量間の **joint 分布** (相関構造) は month 固有
- 結果: 月ごとに **label 頻度** は変動する (これは classifier bug ではなく regime の実態的変化)
- S1 は meta-percentile 設計下では "label 頻度の時代性" を測る指標に degenerate

**本質的な classifier stability = "各 regime label が付いた bar の意味論的性質が時代で変わらないこと"**。
これは label 頻度ではなく、**per-regime feature 分布**の時代安定性で測るべき。

v3 は S1 を **per-regime conditional feature KS** に再定義する。

## Changes from v2 (rationale 明文化)

| Component | v2 | v3 |
|-----------|----|----|
| Feature set F1-F6 | 同じ | **同じ (保持)** |
| Taxonomy (R0-R6) | 同じ | **同じ (保持)** |
| Classifier logic | meta-percentile tree | **同じ (保持)** |
| S1 (stability) | 月次 label 頻度 KS | **per-regime feature KS** (再定義) |
| S2 (stability) | Mann-Kendall on monthly means | **同じ (保持)** |
| S3 (stability) | duration CV | **同じ (保持)** |
| Authorization rule | 2/3 → selective | **3/3 required for full; 2/3 → per-regime selective (具体化)** |

**保持する資産**: v1 から継承した Feature set / Taxonomy / Rolling percentile normalization /
v2 で確定した meta-percentile thresholds / Mann-Kendall S2 / duration CV S3.

## 1. Regime taxonomy (LOCKED — v2 と同じ 6 active + unclassified)

R1 trend_up / R2 trend_down / R3 range_tight / R4 range_wide / R5 breakout / R6 reversal / R0 unclassified.

詳細は [[pre-registration-phase4-adaptive-regime-classifier-v2-2026-04-23]] §1.

## 2. Features (LOCKED — v2 と同じ)

F1-F6 変更なし。200-bar rolling percentile 正規化。

## 3. Classifier logic (LOCKED — v2 meta-percentile tree をそのまま)

```
P80(F3) / P60(F3) / P60(F2) / P30(F1) / P30(F3) / P70(F1) : 直近 500 bar rolling percentiles
(window=500 固定)

if F3 > P80(F3) and |F4| >= 3: R5 (breakout)
elif F3 > P60(F3) and sign(F4) != sign(prev.F4) and |prev.F4| >= 3: R6 (reversal)
elif F2 > P60(F2): R1 if F4 > 0 else R2
elif F1 < P30(F1) and F3 < P30(F3): R3 (range_tight)
elif F1 > P70(F1): R4 (range_wide)
else: R0 (unclassified)
```

優先順: R5 > R6 > R1/R2 > R3 > R4 > R0.

## 4. Stability binding criteria (LOCKED — v3)

### S1 v3: Per-regime conditional feature KS (**NEW — redesigned**)

**motivation**: label 頻度の時代性ではなく、**各 regime 内部の feature 分布の時代安定性**
を測る。classifier が「意味論的に同じもの」を月次でラベリングしているか検定。

**テスト対象**:
- 各 active regime (R1-R6, R0 除外)
- 各 feature ∈ {F1, F2, F3} (tree 分岐に使う 3 つ)

**手順**:
1. regime ごとに、当該 regime と labeled された bar を抽出
2. 連続する 2 ヶ月ペア (m, m+1) について、それぞれの月の feature 値列を取得
3. 2-sample KS 検定を実施 (D 統計量と p-value)
4. 同一 regime × 同一 feature の全月ペアで同じことを繰り返す

**N 要件**: 各月の regime 内 sample N ≥ 30 (少ないペアはスキップ、ただしスキップ率を記録)

**Bonferroni correction**:
- 総 cell 数 M = 6 regimes × 3 features × 月ペア数 (=9 for 10 months) = **162**
- α_cell = 0.05 / 162 ≈ **3.09e-4**
- 各 cell の GO 判定: p > 3.09e-4

**GO 基準**:
- **Strict**: 全 cell (162) で p > α_cell → **S1 GO**
- **Partial**: 特定 regime で全 cell GO なら当該 regime は selective 通過可

### S2 v3: Mann-Kendall on per-regime monthly means (LOCKED — v2 と同じ)

v2 と完全同一。F1, F2 の月次 mean に Mann-Kendall.
Bonferroni M = 6 × 2 = 12, α_cell = 0.05/12 ≈ 4.2e-3.

### S3 v3: Regime duration CV (LOCKED — v2 と同じ)

v2 と同一. GO: 各 active regime で月次 median duration CV < 0.3.

### Authorization rule (v3 で厳密化)

| Score | Interpretation | Action |
|-------|----------------|--------|
| 3/3 GO (全 test 通過) | Full classifier stability confirmed | Phase B (全 regime で per-regime edge test) authorize |
| 2/3 GO かつ S1 partial | S1 で一部 regime のみ通過 | **その regime のみ** Phase B authorize, 他は除外 |
| 2/3 GO かつ S1 fully FAIL | semantic stability 不明 | v4 redesign 要 |
| ≤1/3 GO | redesign 要 | 実装停止, v4 pre-registration |

**"selective"** の明確化: S1 partial で 6 regimes 中 k regimes が通過した場合、
Phase B は **k regimes × 17 strategies = 17k cells** のみ検定対象。Bonferroni の M も
縮小する (v2 で不明瞭だった点の補強).

## 5. Per-regime edge test (unchanged ただし S1 partial で対象縮小)

[[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]] §5 と同じ.
- 全 6 regimes 通過時: M = 6 × 17 = 102, α_cell = 4.9e-4
- k regimes 通過時: M = k × 17, α_cell = 0.05 / (k × 17)
- R0 (unclassified) は edge test 対象外 (不変)

## 6. Disallowed (v3)

- meta-percentile window (500) の変更
- Meta-percentile rank values の変更
- S1 Bonferroni α_cell (3.09e-4) の緩和
- N≥30 閾値の緩和
- S2/S3 の既存条件緩和
- **S1 が fully FAIL の状況で Phase B を authorize する** (v3 の core discipline)
- 検定 post-hoc での feature subset 変更

## 7. Execution (this session)

1. `/tmp/phase4a_v3_classifier_stability.py` を新規作成
   - v2 script をベースに `s1_per_regime_feature_ks()` を追加
   - s1_monthly_ks は legacy 参照として残すが GO 判定は v3 S1 が primary
2. v2 と同じ OANDA 5m × 10 months × 2 pairs でテスト
3. KB 記録: [[phase4a-v3-classifier-stability-2026-04-23]]
4. Commit

## 8. Expected outcomes (pre-registered hypothesis)

以下は結果確認前に書く。post-hoc narrative 防止のため。

**H1 (strongest)**: meta-percentile 設計により per-regime feature 分布は時代安定
→ S1 v3 は 3/3 GO に近い。R0 除外の効果もあり。

**H2 (moderate)**: 一部の regime (特に低頻度 R3, R5, R6) で N<30 の月ペアが多発
→ スキップが支配的になり、実効検定数が M より大幅に小さい可能性。その場合は
"N不足により検定不能" として該当 cell は保留、判定は他 cell で行う。

**H3 (weak, null hypothesis)**: 一部 regime で feature 分布が月次で drift している
→ v3 S1 も partial FAIL。その場合 FAIL regime を除外しての selective Phase B.

H2 (N 不足) が支配的な場合、v4 では長い evaluation window (2年?) を検討する余地あり。

## References

- [[pre-registration-phase4-adaptive-regime-classifier-v2-2026-04-23]] (v2 prereg)
- [[phase4a-v2-classifier-stability-2026-04-23]] (v2 result, 2/3)
- [[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]] (v1 prereg)
- [[phase4a-classifier-stability-2026-04-23]] (v1 result, 1/3)
- [[lesson-premature-neutralization-2026-04-23]] (discipline 根拠)
- [[pre-registration-phase4-regime-native-2026-04-23]] (downstream, still blocked)
