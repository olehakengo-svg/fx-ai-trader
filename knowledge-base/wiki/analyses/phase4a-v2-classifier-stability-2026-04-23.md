# Phase 4a v2 Classifier Stability Result (2026-04-23)

**Pre-registration**: [[pre-registration-phase4-adaptive-regime-classifier-v2-2026-04-23]]
**Script**: `/tmp/phase4a_v2_classifier_stability.py`
**Raw**: `/tmp/phase4a_v2_output.txt` / `/tmp/phase4a_v2_summary.json`
**Data**: OANDA 5m × 10 months × 2 pairs (N≈66k each), identical to v1

## Result: **2/3 GO for both pairs**

Per pre-reg §4 authorization rule: **2/3 → "該当 regime selective に authorize (FAIL regime 除外)"**.

| Pair | S1 monthly KS | S2 Mann-Kendall | S3 duration CV | Score |
|------|---------------|------------------|----------------|-------|
| USD_JPY | ❌ min p=0.0000 | ✅ min p=0.0293 (Bonf α=0.0042) | ✅ max cv=0.280 | **2/3** |
| EUR_USD | ❌ min p=0.0123 | ✅ min p=0.1195 | ✅ max cv=0.276 | **2/3** |

v1 → v2 進展: 1/3 → 2/3. 本質的 failure mode (S2) は解決.

## Distribution (v2 — meta-percentile 化で R0 許容)

| Regime | USD_JPY | EUR_USD |
|--------|---------|---------|
| R0_unclassified | 34.5% | 34.2% |
| R1_trend_up | 16.4% | 16.1% |
| R2_trend_down | 16.4% | 16.9% |
| R3_range_tight | 7.9% | 6.9% |
| R4_range_wide | 14.8% | 16.3% |
| R5_breakout | 5.1% | 4.7% |
| R6_reversal | 5.0% | 4.9% |

R3 が 40% → 8% に縮小 (v1 default fallback 廃止の効果). R0 34% が active regime に
当てはまらない bar を吸収. R1+R2 (trend) が 33% と厚く、tradable な regime が
明確に分離された。

## 詳細: S2 Mann-Kendall (本質的な stability 指標) PASS

Mann-Kendall は **方向性のあるtrend drift** を検出する。v1 の range/std metric が
iid null でも大きく出ることを反映し、v2 で Bonferroni-corrected p-value ベースに
置換 (pre-reg v2 §4).

**USD_JPY** (12 cells, Bonf α=0.0042):
- 最小 p = 0.0293 (R3_range_tight F1, S=+29, Z=+2.18) — **Bonf 閾値通過**
- 他 11 cells も p > 0.06 → **trend drift 無し**

**EUR_USD** (12 cells):
- 最小 p = 0.1195 (R1_trend_up F2) → trend drift 完全に無し

→ **semantic stability 確認**. 各 regime の feature 分布は月ごとに drift しない.

## 詳細: S3 duration CV PASS (marginal)

| Pair | max CV | margin |
|------|--------|--------|
| USD_JPY | 0.280 (R3) | threshold 0.3 まで 0.020 |
| EUR_USD | 0.276 (R2) | 0.024 |

閾値ギリギリだが pass. duration consistency あり.

## 詳細: S1 monthly KS FAIL の honest 解釈

### 実測

**USD_JPY**: 10 ペア中複数で p < 0.05. 最悪 2025-08→2025-09 で p=0.0000 (D=0.062).
**EUR_USD**: 最小 p=0.0123, より軽微な FAIL.

### なぜ meta-percentile でも S1 FAIL するか (structural 分析)

meta-percentile 化は **各特徴量 marginal 分布**を pin するが、**joint 分布 (F2 × F3 × F4 の
相関構造)** は固定しない。

例:
- Trending month: F2 (ADX) が高い時に F4 (direction run) も同方向に固まる
  → R1 or R2 の頻度が上がる
- Chop month: F2 高と F4 不規則が同時発生
  → R0 (unclassified) の頻度が上がる

**これは classifier の bug ではなく "regime の実態的変化" を正しく反映している**。
labels の意味 (= 各 regime の feature 分布 content) は S2 通り安定。

### つまり S1 が測っているもの

**S1 = 「各月でどの regime に属する bar が何 % 居るか」の分布 shift 検定**.
meta-percentile 設計下では:
- 特徴量 marginal は pin される
- 特徴量 joint (相関) は month 固有
- よって label frequency は month 固有
- よって KS はほぼ必然的に FAIL する

→ **S1 は v2 設計下で "irrelevant test" に近い**. これは pre-reg v2 の Caveat
("S1 は sanity check 役") で予測できたが明示的に "FAIL 時の handling" を LOCK して
いなかった点は v3 で要補強.

### セマンティック vs 頻度

| 指標 | v1 問題 | v2 状況 |
|------|--------|--------|
| 各 regime の意味 (semantic) | 不明 (S2 metric 不適切) | ✅ S2 Mann-Kendall PASS → stable |
| 各 regime の出現頻度 (frequency) | FAIL | FAIL (structural, not bug) |
| Regime persistence (duration) | PASS | PASS |

**Phase B (per-regime edge test) で意味を持つのは semantic stability**. 頻度は
sample size に影響するが per-regime Bonferroni 検定の妥当性を害さない.

## 判定

### Literal pre-reg reading

- 2/3 → "regime-selective authorize (FAIL regime 除外)"
- S1 は regime-global FAIL のため「除外する regime」を特定できない
- → literal には **Phase B authorization ambiguous**

### Semantic reading (analytical)

- S2 (semantic stability) + S3 (persistence) PASS
- S1 FAIL は meta-percentile 設計下では structural. 頻度変動は regime の実態的
  変化を反映しており、classifier の不安定性ではない
- → Phase B (per-regime edge test) は条件付き authorize 可能

### 判断保留ポイント

本 doc はユーザー判断待ち。2 択:

**Option A**: 保守的、v3 pre-reg で S1 を "per-regime conditional KS" に差替え
  再検定後に Phase B 許可. 時間コスト: 1 session 分.

**Option B**: 分析的判断、2/3 を "Phase B 条件付き authorize" と読み替える.
  ただし Phase B 結果解釈時に S1 FAIL を **頻度分布の時代性**として留意
  (= backtest の regime 配分と live の配分がずれる可能性を事前告知).

私 (Claude) としては Option A を推奨: pre-reg discipline の一貫性
([[lesson-premature-neutralization-2026-04-23]]) を考えれば、literal に解釈する方が
decision hygiene を損なわない。

## Phase 4 Status Update

| Doc | Status |
|-----|--------|
| [[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]] v1 | FAIL 1/3 (historical) |
| [[pre-registration-phase4-adaptive-regime-classifier-v2-2026-04-23]] | **2/3** (ambiguous per literal rule) |
| v3 (不足分: S1 redesign) | 必要 (Option A 採択時) |
| [[pre-registration-phase4-regime-native-2026-04-23]] D1-D4 | BLOCKED (upstream authorize 未確定) |
| [[pre-registration-label-holdout-2026-05-07]] | 独立、予定通り |

## 保持する資産

- Feature set F1-F6 + meta-percentile normalization: ✅ 有効
- R0_unclassified: ✅ 識別力向上に寄与
- Mann-Kendall S2: ✅ 適切な stability 指標として確定
- S3 duration CV: ✅ 持続

## 次のアクション (user 判断後)

**Option A 選択時**:
1. v3 pre-reg 作成: S1 を "per-regime conditional feature KS" に再定義
2. v3 stability 検定再走
3. 3/3 or 2/3(明確) で Phase B 許可

**Option B 選択時**:
1. Phase B (per-regime edge test) 直接着手
2. Bonferroni M=102 で既存 17 strategies × 6 regimes 検定
3. Survivor cell で strategy routing table 構築

## References

- [[pre-registration-phase4-adaptive-regime-classifier-v2-2026-04-23]] (本 run の prereg)
- [[phase4a-classifier-stability-2026-04-23]] (v1 FAIL)
- [[pre-registration-phase4-regime-native-2026-04-23]] (downstream)
- [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
- [[lesson-premature-neutralization-2026-04-23]]
