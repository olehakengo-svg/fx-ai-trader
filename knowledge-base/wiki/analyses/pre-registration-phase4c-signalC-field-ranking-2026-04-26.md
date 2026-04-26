# Pre-registration: Phase 4c Signal C — Trade-Snapshot Field Ranking (2026-04-26)

**Locked**: 2026-04-26 (本 doc 確定後変更禁止)
**Track**: B / Signal C (univariate trade-snapshot field edge ranking)
**Plan**: `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` Section 2 Phase I
**Phase 0 audit**: PASS — primary fields populated ≥99% (`/tmp/phase4c_phase0_audit.txt`)
**Upstream**: [[phase4c-mtf-regime-result-2026-04-24]] (Signal A null), [[phase4c-mtf-signalB-adx-result-2026-04-24]] (Signal B null)
**Memory**: [[feedback_success_until_achieved]], [[feedback_partial_quant_trap]], [[feedback_label_empirical_audit]]

## 0. Rationale

Signal A (EMA20 slope) と Signal B (Wilder ADX14) は両方 Scenario A. これらは
**自前で OANDA から higher-TF を fetch して naïve labeler を計算** する design で、
既に dead-end が validated 済 (regime_labeler.py の η²<0.005 finding) を再走した状態.

本 Signal C は別 angle: production trade に **既に attach 済の 8 種 regime/MTF field**
の univariate edge ranking. これらは:
- entry 時刻に live system が計算した値 (look-ahead-safe)
- D1→H4 hierarchy (mtf_regime_engine.py) や 4-feature composite (app.py
  detect_market_regime) や HMM 等、**異なる philosophy の classifier の outcome**
- 自前再計算不要 → 本 session で 8 field 同時 sweep 可能

仮説: 8 種 classifier の中で trade outcome (WIN/LOSS) と統計的に最も dependent な
field を特定し、それが Signal A/B のような naïve EMA/ADX より prop edge を持つかを
測る.

## 1. Strategy scope (LOCKED)

Signal A/B と同じ 8 strategy. nature 分類も同一:
- TREND: ema_trend_scalp, stoch_trend_pullback
- BREAKOUT: vol_surge_detector, bb_squeeze_breakout
- RANGE: bb_rsi_reversion, engulfing_bb, fib_reversal, sr_channel_reversal

## 2. Field scope (LOCKED, M_field = 8)

| # | Field | Source | Cardinality | Phase 0 populate rate |
|---|-------|--------|-------------|----------------------|
| 1 | `mtf_regime` | top-level | 7-class | 99.0% |
| 2 | `mtf_d1_label` | top-level | 5-level (-2,-1,0,1,2; 3=NaN) | 100% |
| 3 | `mtf_h4_label` | top-level | 3-level (-1,0,1; 3=NaN) | 100% |
| 4 | `mtf_vol_state` | top-level | 3-class (squeeze/normal/expansion) | 99.0% |
| 5 | `mtf_alignment` | top-level | aligned/conflict/neutral/unknown | 46.7% (cell N gating 厳しい) |
| 6 | `regime.regime` | JSON | 4-class (TREND_BULL/BEAR/RANGE/HIGH_VOL) | 99.8% |
| 7 | `regime.range_sub` | JSON | 3-class (SQUEEZE/WIDE_RANGE/TRANSITION; None=非range) | 47.1% |
| 8 | `regime.hmm_regime` | JSON | 2-class (ranging/trending; None=未学習) | 67.9% |

**LOCKED**: field 8 個固定. 後付け追加禁止. Field 内の値は **trade snapshot 生値を
そのまま** category として扱う (post-hoc binning 禁止).

## 3. Statistical procedure (LOCKED)

### 3.1 Per (field, strategy) cell

各 (field f, strategy s) について:

1. trade subset: strategy=s かつ field f が non-null
2. cross-tab: rows = field value, columns = WIN/LOSS (2×k)
3. cell size filter: 各 row N ≥ 5 (χ² validity), aggregated N ≥ 50
4. χ² test of independence: Pearson χ², df = (k−1)
5. Mutual information: I(F; W) = Σ p(f,w) log[p(f,w)/(p(f)p(w))], natural log, in **bits** (÷ ln 2)
6. Cramér's V: V = √(χ² / (N · min(k−1, 1)))
7. dWR_max−min: 最高 WR cell − 最低 WR cell (各々 N≥30)

### 3.2 Bonferroni (LOCKED)

Family size **M = 8 fields × 8 strategies = 64**.

α_cell = 0.05 / 64 = **7.8125e-4**

### 3.3 SURVIVOR 基準 (LOCKED, 全部満たす)

1. Aggregated N ≥ 50
2. ≥2 cell が N≥30 (比較対象を確保)
3. dWR (最高 WR cell − 最低 WR cell, それぞれ N≥30) ≥ 0.05
4. Pearson χ² p < 7.8125e-4
5. Cramér's V ≥ 0.15 (effect size 下限)

### 3.4 CANDIDATE
1, 2, 3, 5 を満たすが χ² Bonferroni 未達 (nominal p<0.05 など).

### 3.5 INSUFFICIENT
N filter で testable cell 不足.

### 3.6 REJECT
χ² nominal p<0.05 だが dWR < 0.05 (有意だが effect size 不足).

## 4. Train/Test split (本 pre-reg では実施しない, LOCKED)

理由: Signal C は **explanatory variable selection** の段階. predictive validation
は次 phase (Phase II multivariate, Phase III per-pair) で実施. 本 phase は all-data
で MI/χ² ranking のみ.

**Disallowed**: 本 pre-reg 結果に基づき "選んだ field" で別 train/test 検定すること.
それは circular validation. 必ず **independent fresh data** (本 session 後の追加
trade) で別 pre-reg を立てる.

## 5. Disallowed (post-hoc 禁止)

- Field の事後追加 (例: `confidence`, `ema_conf` を加える)
- Field 内 binning (例: mtf_d1_label の +1/+2 を merge)
- α 緩和
- N 閾値緩和
- Cramér's V threshold 緩和
- Bonferroni M の縮小
- Strategy nature 修正

## 6. Secondary (exploratory, Bonferroni 対象外, 報告のみ)

以下は report のみ. **Decision rule に影響させない**:

- Per-pair × per-field cross-tab (24 pair-field cells)
- Wilson 95% CI for top WR cell vs bottom WR cell
- Profit factor and half-Kelly per cell
- Mutual information ranking (8 fields × 8 strategies → 64 個)
- Field 間 correlation matrix (Spearman) — Phase II の VIF 入力用

## 7. Pre-registered hypotheses

| H | Type | Prediction |
|---|------|-----------|
| H1 | moderate | `mtf_d1_label` (D1-dominant) は ≥1 strategy で SURVIVOR (mtf_regime_engine 設計 memo の D1 η²=0.018 と整合) |
| H2 | weak | `regime.regime` (4-class composite) は SURVIVOR ≥1 (multi-feature の方が単一 feature より edge を捉える) |
| H3 | weak | `regime.hmm_regime` (HMM 2-state) は CANDIDATE ≥1 (model-based なので threshold 不要) |
| H4 | overall null | 全 64 test で SURVIVOR=0 (Signal A/B 連続 null と同 root cause: 16 days power denial) |

## 8. Scenario & authorization

| Scenario | Rule | Action |
|----------|------|--------|
| A | SURVIVOR=0 ∧ CANDIDATE=0 | 本 phase 下 null → Phase II (multivariate) に移行 |
| B | SURVIVOR=0 ∧ CANDIDATE≥1 | Suggestive, Phase II で confounder control 後 SURVIVOR 化検討 |
| C | SURVIVOR ≥1 | 該当 (field, strategy) を Phase III primary feature として認可 |

**Track B 全体の closure 判定は Phase I-V 全て完了後にしか下さない** (plan Section 8).

## 9. Execution

- Script: `/tmp/phase4c_signalC_field_ranking_test.py`
- Output: `/tmp/phase4c_signalC_output.txt`, `/tmp/phase4c_signalC_summary.json`
- Result KB: `knowledge-base/wiki/analyses/phase4c-signalC-field-ranking-result-2026-04-26.md`

## References

- [[pre-registration-phase4c-mtf-regime-2026-04-24]] (Signal A pre-reg)
- [[pre-registration-phase4c-mtf-signalB-adx-2026-04-24]] (Signal B pre-reg)
- [[phase4c-mtf-regime-result-2026-04-24]] (Signal A result)
- [[phase4c-mtf-signalB-adx-result-2026-04-24]] (Signal B result)
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` (本 phase の上位 plan)
- `research/edge_discovery/mtf_regime_engine.py` (mtf_regime/d1/h4 source)
- `app.py` L7390-7501 `detect_market_regime` (regime.regime source)
- `modules/hmm_regime.py` (regime.hmm_regime source)
