# Phase 4a v3 Classifier Stability Result (2026-04-23)

**Pre-registration**: [[pre-registration-phase4-adaptive-regime-classifier-v3-2026-04-23]]
**Script**: `/tmp/phase4a_v3_classifier_stability.py`
**Raw**: `/tmp/phase4a_v3_output.txt` / `/tmp/phase4a_v3_summary.json`
**Data**: OANDA 5m × 10 months × 2 pairs (N≈66k each、v1/v2 と同じ)

## Result: **2/3 strict FAIL**, but **per-regime partial GO** identified

S1 v3 は strict 基準 (全 180 cells pass) では FAIL. しかし **per-regime verdict** で
survivor regime を同定できた:

| Pair | S1 strict | S2 Mann-Kendall | S3 duration CV | Per-regime GO (S1) |
|------|-----------|-----------------|----------------|---------------------|
| USD_JPY | FAIL (15/180 FAIL) | ✅ GO | ✅ GO | **R6_reversal** |
| EUR_USD | FAIL (14/180 FAIL) | ✅ GO | ✅ GO | **R5_breakout, R6_reversal** |

Per v3 §4 authorization rule: **"2/3 GO かつ S1 partial → その regime のみ Phase B authorize"**.

**両 pair 共通の survivor**: `R6_reversal`
**EUR_USD のみ**: `R5_breakout`

## Progression

| Version | Score | 本質 |
|---------|-------|------|
| v1 | 1/3 | 固定 threshold, 範囲/std metric (null 下で約3.1) |
| v2 | 2/3 (S1 label-freq FAIL) | meta-percentile + MK (S1 は structural FAIL) |
| v3 | 2/3 strict FAIL, per-regime partial GO | S1 を feature KS に再定義 → partial authorize 可能 |

v2 → v3 の利得: **"S1 FAIL" の実質内容を診断できた**. どの regime の feature 分布が
drift しているかが判明し、Phase B authorize の **specific scope** を定義できた。

## Detailed: S1 v3 per-regime verdicts

### USD_JPY

| Regime | Tested | GO | FAIL | min p | Verdict |
|--------|--------|----|----|-------|---------|
| R1_trend_up | 30 | 28 | 2 | 2.21e-06 | FAIL |
| R2_trend_down | 30 | 29 | 1 | 1.06e-06 | FAIL |
| R3_range_tight | 30 | 26 | 4 | 4.29e-07 | FAIL |
| R4_range_wide | 30 | 24 | 6 | 3.82e-07 | FAIL |
| R5_breakout | 30 | 28 | 2 | 3.57e-07 | FAIL |
| **R6_reversal** | 30 | 30 | 0 | 2.63e-03 | **GO** |

Bonferroni α_cell = 2.78e-4 (M=180).

### EUR_USD

| Regime | Tested | GO | FAIL | min p | Verdict |
|--------|--------|----|----|-------|---------|
| R1_trend_up | 30 | 29 | 1 | 9.76e-06 | FAIL |
| R2_trend_down | 30 | 27 | 3 | 4.99e-08 | FAIL |
| R3_range_tight | 30 | 25 | 5 | 3.05e-06 | FAIL |
| R4_range_wide | 30 | 25 | 5 | 1.80e-08 | FAIL |
| **R5_breakout** | 30 | 30 | 0 | 3.24e-03 | **GO** |
| **R6_reversal** | 30 | 30 | 0 | 7.77e-03 | **GO** |

## 観察: FAIL feature の偏り

**Top FAIL cells (USD_JPY)**: 5 件中 5 件が **F1 (ATR ratio)** drift. 分布の top 5 は全て F1.

**Top FAIL cells (EUR_USD)**: 5 件中 3 件が F1, 2 件が F2/F3.

→ **F1 (vol regime indicator) が月次で最も drift する**. これは [[regime-characterization-2026-04-23]]
で観測した "Aug→Sep の vol +30-70% shift" と整合する. Vol は本質的に非定常.

逆に **R6_reversal と R5_breakout は F1 drift の影響を受けにくい**:
- R5 (breakout) は F3 が高い bars のみ抽出 → F3 filter で vol-noise が除去される可能性
- R6 (reversal) は F4 sign change 条件で event-based → marginal vol の effect 小

→ **breakout/reversal のような event-based regime は vol drift に対して robust**.
一方 trend/range のような state-based regime は vol 環境に強く依存する.

## S2 / S3 は前 session と同一 (v2 結果を追認)

- S2 Mann-Kendall USD_JPY min_p=0.0293 > Bonf α=0.0042 → GO
- S2 Mann-Kendall EUR_USD min_p=0.1195 → GO
- S3 duration CV USD_JPY 0.280 / EUR_USD 0.276 → GO (threshold 0.3)

## 判定

### v3 authorization rule に literal 従う

**両 pair で `R6_reversal` が partial GO** →
**Phase B per-regime edge test は R6_reversal に対して authorize 可能**.

EUR_USD では **R5_breakout** も追加. ただし USD_JPY では R5 が FAIL のため pair-specific.

### Phase B の scope 計算

#### Option 1: Pair-agnostic conservative (両 pair 共通)
- 対象 regime: {R6_reversal}
- 対象 strategies: 17 (全)
- Bonferroni M = 1 × 17 = **17**, α_cell = 0.05/17 = **2.94e-3**

#### Option 2: Pair-specific
- USD_JPY: R6 のみ → M=17, α=2.94e-3
- EUR_USD: R5 + R6 → M=34, α=1.47e-3
- 合計 Bonferroni: M=17+34 = 51, α=9.80e-4

#### Option 3: 全 6 regimes × 2 pairs (全面 authorize の場合の baseline 比較)
- 全面では M=6×17=102 (per pair), α=4.90e-4
- v3 で縮小された scope は統計的 power を大きく改善

**推奨 Option 1** (conservative, pair-agnostic):
- 単一 regime R6 のみなら false positive risk 最小
- 結果解釈が clean: "R6 で edge がある strategy が見つかる or 見つからない"
- Bonferroni 緩和 (α=2.94e-3 vs 4.90e-4) で検定 power 6倍改善

## 不足分: 時代性の明示的留保

S1 で R1-R4 が FAIL した実態は:
- R1/R2 (trend) は F1 vol drift で月ごとに "同じ label の trend" の vol-profile が変動
- R3 (range_tight) は vol 圧縮が月次で drift
- R4 (range_wide) は vol 拡大が月次で drift

→ これらの regime は classifier bug ではなく **"vol regime 依存性"** を持つ. Phase B で
これらを使う場合、backtest の vol 分布と live の vol 分布が一致するとは限らない.

R5/R6 (event-based) はこの懸念が小さい。

## Phase B 実施 plan (v3 authorization scope)

### Scope (LOCKED)

- **Target regime**: `R6_reversal` (両 pair)
- Pairs: USDJPY, EURUSD (XAU 除外)
- Strategies: 17 (全 entry_types)
- Bonferroni M = 17, α_cell = 2.94e-3
- Per-cell metric: (Fisher exact 2-tail p, Wilson 95% CI, Kelly)
- **R6 以外の regime での edge 発見は Phase B の authorize 範囲外** (post-hoc 扱い)

### 実行 (次 session)

1. R6_reversal で labeled された bars を identify (v3 classifier から直接)
2. 各 strategy × R6 で Fisher p, Wilson CI, Kelly 計算
3. Bonferroni 通過 cell を survivor として抽出
4. Walk-forward validation (2-bucket same-sign)

### Pre-registration 更新

Phase B 用の pre-reg を別 doc で作成:
`pre-registration-phase4b-r6-edge-test-<next_date>.md`.

## Status update

| Doc | Status |
|-----|--------|
| v1 pre-reg | 1/3 FAIL (historical) |
| v2 pre-reg | 2/3 ambiguous (historical) |
| **v3 pre-reg** | **2/3 strict FAIL, per-regime partial GO (R6 両 pair)** |
| v4 redesign | **不要** (v3 で Phase B scope 同定済) |
| Phase B (R6) | **authorized, 次 session で実行** |
| D1-D4 strategies | **BLOCKED until Phase B result** |
| [[pre-registration-label-holdout-2026-05-07]] | 独立、予定通り |

## Retained assets

- Feature set F1-F6 + meta-percentile thresholds
- Taxonomy (6 active + R0)
- Mann-Kendall S2 + duration CV S3
- **v3 knowledge: どの regime が semantic-stable か**
  - event-based (R5/R6) = stable
  - state-based (R1-R4) = vol-regime dependent

## References

- [[pre-registration-phase4-adaptive-regime-classifier-v3-2026-04-23]] (本 run の prereg)
- [[phase4a-v2-classifier-stability-2026-04-23]] (v2 result)
- [[phase4a-classifier-stability-2026-04-23]] (v1 result)
- [[regime-characterization-2026-04-23]] (vol shift 観測)
- [[lesson-premature-neutralization-2026-04-23]] (discipline 根拠)
- [[pre-registration-phase4-regime-native-2026-04-23]] (D1-D4 downstream, still blocked)
