# Pre-registration: Phase 4 Adaptive Regime Classifier v4 — 2D (Regime × Vol) (2026-04-23)

**Locked**: 2026-04-23 (v3 strict FAIL を受けた 2D 化版、本 doc 確定後変更禁止)
**Prev**: [[pre-registration-phase4-adaptive-regime-classifier-v3-2026-04-23]] (v3, strict FAIL / R6 partial GO)
**Prev result**: [[phase4a-v3-classifier-stability-2026-04-23]]
**Rationale doc**: このセッションの分析 (v3 の S1 FAIL が F1 drift 単一要因であることを演繹で同定)

## Motivation (v3 → v4)

v3 S1 の FAIL cell の **top 5 中 5 件が F1 (ATR ratio) drift**. 1D regime label では vol
環境の時代性を吸収できない. これは pre-reg v3 §8 H3 で予見した現象で、**演繹的 refinement**
として 2D 化は正当化される (post-hoc narrative に非該当).

**v3 が示したこと**:
- regime の mean (S2) と持続 (S3) は stable
- しかし regime 内 feature **分布形状** は vol 環境で drift する
- event-based regime (R5/R6) は vol-robust だが N 不足で Phase B power 不足

**v4 の解決**:
- Regime axis に **Vol axis** を直交追加
- F1 を axis に昇格させ、各 cell 内では F1 drift が事実上消える
- state-based regime (R1-R4) も各 vol バケット内で stability 検定可能に
- Phase B は 18 cells × 17 strategies で統合的に power を確保

## Changes from v3

| Component | v3 | v4 |
|-----------|----|----|
| Feature set F1-F6 | 同じ | **同じ (保持)** |
| Regime taxonomy | R1-R6 + R0 | **同じ (保持)** |
| Regime classifier (meta-percentile tree) | 同じ | **同じ (保持)** |
| **Vol axis** | なし | **V_low/V_mid/V_high (3 bucket)** ← 新規 |
| Final cell | 6 active regimes × 1 = 6 | **6 × 3 = 18 (R0 除外)** |
| S1 stability | per-regime × F1/F2/F3 KS | **per-cell × F2/F3 のみ KS** (F1 は axis) |
| S2 stability | Mann-Kendall on F1/F2 | **Mann-Kendall on F2 のみ** (F1 は axis) |
| S3 stability | duration CV by regime | **duration CV by cell (18)** |
| Bonferroni (Phase B) | M=17 (R6 only) | **M = 18 × 17 = 306** |

## 1. Regime taxonomy (LOCKED — v3 と同じ)

R1-R6 + R0 (unclassified). 詳細 [[pre-registration-phase4-adaptive-regime-classifier-v2-2026-04-23]] §1.

## 2. Features (LOCKED — v3 と同じ)

F1-F6 変更なし、200-bar rolling percentile 正規化.

## 3. Vol axis definition (LOCKED — 新規)

**Vol state** は F1 (ATR14/ATR100 の 200-bar percentile) を直接使う:

```
V_low:  F1 ∈ [0.00, 0.33)
V_mid:  F1 ∈ [0.33, 0.67)
V_high: F1 ∈ [0.67, 1.00]
```

**Rationale**:
- F1 は既に 200-bar rolling percentile で adaptive に正規化済
- 固定 cutpoint 0.33/0.67 は construction 上 uniform (1/3 ずつに近い)
- 新しい rolling window の導入は不要 (F1 自体が adaptive)

**注意**: F1 は regime classifier 内部でも使われる (R3/R4 の分岐条件). これは
regime × vol の **相関** を生むが、直交性は検定で検証 (§4 s4_independence)。

## 4. Classifier logic (LOCKED — v4 2D)

```python
# Step 1: Regime (v2/v3 から継承、meta-percentile tree)
regime = classify_v2_bar(row, prev_row)  # R0-R6

# Step 2: Vol bucket
if row.F1 < 0.33:    vol = "V_low"
elif row.F1 < 0.67:  vol = "V_mid"
else:                vol = "V_high"

# Step 3: 2D cell
if regime == "R0_unclassified":
    cell = "R0"  # vol axis も無意味
else:
    cell = f"{regime}__{vol}"
```

**Cell space**:
- Active cells: 6 regimes × 3 vol = **18**
- Unclassified: R0 (1)
- Total labels: 19

## 5. Stability binding criteria (LOCKED — v4)

### S1 v4: Per-cell conditional feature KS (F2/F3 only)

**Target**:
- 各 active cell (18) × 各 feature ∈ {F2, F3} × 各連続月ペア (9)
- F1 は axis に昇格したので対象外 (axis 内 drift が定義上除去される)

**N 要件**: N ≥ 30 per cell-month (v3 と同じ). 少ないペアは skip (記録).

**Bonferroni**:
- M = 18 × 2 × 9 = **324**
- α_cell = 0.05 / 324 ≈ **1.54e-4**

**GO 基準**:
- Strict: 全 324 cells (non-skipped) で p > α_cell
- Partial: 特定 cell のみ pass、他は skip や FAIL → 該当 cell 群を Phase B の target に

### S2 v4: Per-cell Mann-Kendall on F2 monthly mean

**Target**: 18 cells × 1 feature (F2)
**Bonferroni**: M = 18, α_cell = 0.05/18 ≈ **2.78e-3**
**N_months 要件**: ≥ 6

### S3 v4: Per-cell duration CV

**Target**: 18 cells
**GO**: 各 cell で月次 median duration CV < 0.4 (v2/v3 は 0.3 だったが cell 細分化で
N 減少を考慮して 0.4 に調整、pre-reg LOCK 時点で明示)

**N_months 要件**: ≥ 3

### S4 v4: Independence check (新規、参考指標)

Regime と Vol の対数尤度比独立性を chi-square で確認 (informational, 判定影響せず).

### Authorization rule (v4)

| Score | Action |
|-------|--------|
| 3/3 GO (strict) | 全 18 cells で Phase B authorize (M=306) |
| 2/3 GO (S1 partial) | partial-pass cell 群のみ Phase B authorize (M=通過 cell × 17) |
| ≤1/3 GO | v5 redesign 要 (multi-scale vol, longer window など) |

## 6. Per-cell edge test scope (LOCKED)

- Target: 全 18 active cells × 17 strategies = 306 cells (max)
- Per-cell metric: Fisher exact 2-tail p, Wilson 95% CI, Kelly
- Survivor: p < α_cell かつ Kelly > 0 かつ Wilson CI lower > 0
- **N_min**: 各 cell で ≥ 30 trades (Phase B pre-reg で別途 LOCK)
- R0 は edge test 対象外

## 7. Disallowed (v4)

- Vol cutpoint (0.33/0.67) を post-hoc で調整
- Vol bucket 数 (3) の事後変更
- F2/F3 以外の feature を S1 に追加
- S1 α_cell 緩和
- S3 CV 閾値 0.4 の緩和
- Strict FAIL 時の Phase B authorize 拡大
- regime と vol の correlation を "相殺" として扱う議論

## 8. Execution (this session)

1. `/tmp/phase4a_v4_classifier_stability.py` 作成
   - v2/v3 の classifier を再利用
   - vol bucket 付与、per-cell S1/S2/S3 集計
2. v1-v3 と同じ OANDA 5m × 10 months × 2 pairs で検定
3. KB 記録: [[phase4a-v4-classifier-stability-2026-04-23]]
4. Commit

## 9. Pre-registered hypotheses (結果確認前)

**H1 (strongest)**: F1 axis 化により S1 の FAIL 源泉が除去される
→ S1 v4 は 3/3 GO 近く、特に state-based regime (R1-R4) が救済される

**H2 (moderate)**: Cell 細分化 (18 cells) により N<30 skip が増加
→ 特に R5_breakout/R6_reversal (元 5% each) は V_high に集中する等の偏在で
  V_low/V_mid の cell で skip 多発

**H3 (weak, null)**: 2D 化しても S1 で残存 drift あり
→ F1 以外の vol-related 構造 (F3 = BB width) が寄与している可能性
  v5 で F3 も axis 化を検討する

H2 (skip 支配) が支配的な場合、Phase B authorize は "N 十分 cell のみ" となり
実質 scope は狭まる。これは想定内 (pre-reg にて事前認識).

## 10. Handoff to Phase B

v4 が 2/3 以上で pass した場合、Phase B pre-registration:
- `pre-registration-phase4b-cell-edge-test-<next_date>.md`
- 対象: v4 で GO 判定の cell 群 × 17 strategies
- Bonferroni: M は authorized cell count に依存

## References

- [[pre-registration-phase4-adaptive-regime-classifier-v3-2026-04-23]] (v3 prereg)
- [[phase4a-v3-classifier-stability-2026-04-23]] (v3 result, strict FAIL)
- [[pre-registration-phase4-adaptive-regime-classifier-v2-2026-04-23]] (v2 prereg)
- [[regime-characterization-2026-04-23]] (vol shift 観測の出発点)
- [[lesson-premature-neutralization-2026-04-23]]
- [[pre-registration-phase4-regime-native-2026-04-23]] (D1-D4, still blocked)
