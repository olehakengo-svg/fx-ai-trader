# Pre-registration: Phase 4 Prime Directive — Adaptive Regime Classifier (2026-04-23)

**Locked**: 2026-04-23
**Scope**: **Upstream foundation**. 既存 D1-D4 strategies ([[pre-registration-phase4-regime-native-2026-04-23]])
は本 directive の downstream となる。本 classifier が stability 検定を通らない限り、
downstream strategy 設計は authorize されない。

## Purpose

[[regime-characterization-2026-04-23]] で current 市場が高 vol + chop と判明。
しかし「今の 16 日」に合わせた **static strategy fitting** は overfitting 危険。
**解決策** = intraday で trend/range/breakout を数回往復する事実を前提に、
**bar 単位で regime 判定 → strategy routing** の adaptive architecture を設計する。

Overfitting 論は adaptive と static で位相が異なる (下記 §0 参照)。本 doc は
adaptive 論理専用の validation framework を lock する。

## 0. Why adaptive ≠ overfit

| | Static param | Adaptive logic |
|---|---|---|
| Fit 対象 | 具体値 (SL=20p) | 関数係数 (k: SL=k×ATR) |
| 有効 N | fit 窓 trade 数 | fit 窓 × regime 遷移数 |
| Regime 変化耐性 | 破綻 | 追従 (設計通りなら) |
| Overfitting 判別 | PnL だけでは不可 | **classifier stability で可判** |
| Failure mode | 静かに劣化 | stability 検定で検知可 |

本 doc の validation は **classifier が regime-specific にならないこと** の検定に
focus. PnL 検定は下流 (per-regime edge test) に位置付け。

## 1. Regime taxonomy (LOCKED — data 見る前に確定)

6 class. 各 bar を以下に排他的に分類する:

| ID | Regime | Intuitive definition |
|----|--------|---------------------|
| R1 | trend_up | 直近 N bar で higher highs + higher lows + ADX > 上位 |
| R2 | trend_down | 直近 N bar で lower highs + lower lows + ADX > 上位 |
| R3 | range_tight | ATR 下位 + BB width 下位 + 方向性なし |
| R4 | range_wide | ATR 上位 + 方向性なし (chop) |
| R5 | breakout | BB width expansion + recent bar が BB を外れる + direction commit |
| R6 | reversal | 直前 breakout/trend が逆方向 bar 列で打ち消された |

**割り当て優先順**: R5 > R6 > R1/R2 > R4 > R3 (上位から評価、該当なしで下位へ)

## 2. Feature set (LOCKED)

各 bar で以下 6 features を計算:

| Feature | Formula | Use |
|---------|---------|-----|
| F1 | ATR(14) / ATR(100) の 200-bar percentile | vol regime |
| F2 | ADX(14) 200-bar percentile | trend strength |
| F3 | BB(20, 2) width / ATR(14) 200-bar percentile | expansion/contraction |
| F4 | Signed run of consecutive same-direction closes (last 5) | direction persistence |
| F5 | (Close - BB_mid) / BB_std の 200-bar percentile | position in band |
| F6 | (Close - 20bar_low) / (20bar_high - 20bar_low) | range position |

**重要**: 全て rolling percentile または rolling normalized → **固定閾値なし**。
vol regime が shift しても percentile 空間は保持される = adaptive。

## 3. Classifier logic (LOCKED — deterministic decision tree)

```
if F3 > 0.80 and |F4| >= 3:
    R5 (breakout)
elif F3 > 0.60 and sign(F4) != sign(previous_bar.F4) and |prev F4| >= 3:
    R6 (reversal)
elif F2 > 0.60:
    R1 if F4 > 0 else R2
elif F1 < 0.30 and F3 < 0.30:
    R3 (range_tight)
elif F1 > 0.70:
    R4 (range_wide)
else:
    R3 (default to range_tight)
```

**Thresholds (0.80 / 0.60 / 0.30 / 0.70)** は priori 選択。本 doc 確定後は
データを見て変更禁止。別 threshold の検討は **新 pre-registration** を立ち上げる。

## 4. Stability binding criteria (LOCKED — 検定の本体)

以下 **全 3 項パス** で classifier を "regime-agnostic" と認定する。
1 項 fail で下流 strategy 設計を authorize しない。

### S1: 月次 regime 分布の安定性 (primary)

各月 (≥ 20 営業日) について R1-R6 の出現率を算出。
連続月ペアの分布 KS 検定:
- **GO**: 全連続月ペアで KS test p > 0.05 (= distribution shift なし)
- **FAIL**: 1 ペアでも p < 0.05 → classifier が regime-period specific

**Baseline window**: 2024-01 以降の月次データ (最低 6 ヶ月)

### S2: Per-regime 特徴量 mean drift (secondary)

各 regime 内で ATR / ADX の月次 mean をとり、
drift / std_of_means の絶対値:
- **GO**: 全 regime × 2 features で |drift| / std < 0.3
- **FAIL**: 1 でも超過 → regime label が同じでも中身が時代で異なる

### S3: Regime persistence (tertiary)

各 regime の median duration (連続 bar 数) を月次算出:
- **GO**: 月次 median duration の coefficient of variation < 0.3
- **FAIL**: duration が月で大きく揺れる → classifier noise が大

### Downstream authorization rule

- **3/3 GO**: 下流 per-regime edge test + strategy 設計 authorize
- **2/3 GO**: 該当 regime のみ認可 (fail regime は使わない)
- **0-1/3 GO**: classifier redesign 必要 → 新 pre-registration

## 5. Per-regime edge test design (LOCKED — 下流)

Stability GO 後に実行する edge 検定:

### Test unit

(regime, strategy) cell. Bonferroni M = 6 regimes × 17 strategies = **102** cells.
α_family = 0.05 → α_cell = 4.9e-4.

### Metrics per cell

1. N ≥ 30 (regime instance 内 trade 数)
2. WR Wilson 95% lower > BEV_cell + 2pp
3. Fisher exact p < 4.9e-4
4. Kelly > 0.05 (BT_COST_inst 減算後)
5. **Regime-instance Walk-Forward**: regime instance を時系列に前後半分割、両半で WR ≥ BEV

### GO (strategy routing table 作成)

全 5 条件 met cell のみ "in regime X use strategy Y" として routing table に登録。

### Strategy 新規設計 (D1-D4 等)

Routing table が疎 (特定 regime で survivor 0) の場合に限り、
その regime 専用の新 strategy 設計を authorize。候補:
- range_wide (R4) 専用: vol-scaled MR (D4 相当) — chop で勝つ hypothesis の検証
- breakout (R5) 専用: wide SL breakout follow — vol-adaptive SL (D1 相当)

## 6. Execution plan

### Phase A (本 session 以降、code 変更必要)

1. **Historical bar data 調達**: OANDA API 経由で 5 pairs × 1m × 2024-01-2026-04-23
   (または既存 production DB の tick/bar table)
2. **Classifier 実装** (`modules/regime_classifier.py` 相当): §3 のロジックを
   **そのまま**コード化。パラメータ調整禁止
3. **Stability 検定 script**: §4 の S1-S3 を計算、GO/FAIL 判定
4. **KB 記録**: [[phase4-classifier-stability-<date>]] で結果を記録

### Phase B (Stability GO 時のみ)

5. **過去 trade に regime label 付与** (entry bar の regime で分類)
6. **Per-regime edge test** (§5)
7. **Routing table 作成** → [[phase4-routing-table-<date>]]

### Phase C (Routing 決定後)

8. **Shadow deploy** (routing logic を production signal 関数に backtest_mode
   分岐で統合、既存 strategies は unchanged、gate として動作)
9. **Shadow 14d N≥200 → [[pre-registration-phase4-adaptive-shadow-<date>]]**
   で promote/demote 判定

## 7. Disallowed (本 doc 確定後)

- §3 classifier thresholds の post-hoc 調整 (0.80 → 0.75 等)
- §4 stability criteria の緩和 (p > 0.05 → p > 0.01 等)
- §1 taxonomy の後付け追加/削除 (6 class 固定)
- Feature set §2 の拡張 (F1-F6 固定、追加は別 pre-reg)
- Stability FAIL 結果を「ほぼ pass」として扱う

新仮説は **別 pre-registration** を作成する。

## 8. Author accountability

**事前約束**:
- Stability FAIL 時は classifier redesign ではなく **hypothesis 棄却** を第一候補とする
- 「実装コストが高い」を理由に criteria を緩めない
- Phase B の per-regime edge test で M=102 Bonferroni を崩さない
- routing table が empty でも「実装した時間の sunk cost」で強行しない

## References

- [[regime-characterization-2026-04-23]] (post-cutoff 高 vol + chop 発見)
- [[cell-level-scan-2026-04-23]] (static 戦略 0 survivor 確定)
- [[pre-registration-phase4-regime-native-2026-04-23]] (D1-D4 candidate, 本 doc により downstream 化)
- [[pre-registration-label-holdout-2026-05-07]] (並行進行の label audit)
- CLAUDE.md §4 原則 (静的時間ブロック禁止、動的判定)
- [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
