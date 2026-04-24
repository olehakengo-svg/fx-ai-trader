# Pre-registration: Phase 4c MTF Alignment Regime Classifier (2026-04-24)

**Locked**: 2026-04-24 (本 doc 確定後変更禁止)
**Track**: B (他 features approach, MTF alignment)
**並行**: [[pre-registration-phase4c-v6-feature-redesign-2026-04-24]] (Track A)
**Upstream**: [[phase4b-cell-edge-test-result-2026-04-24]] (Scenario A, power-limited)

## 0. Rationale

Phase 4b で F1-F6 (ATR 比・値幅・duration) ベースの v5 classifier は regime-conditioned
edge を検出できず (power-limited). Track B は feature の発想を変え、**higher-TF の
方向性と native TF trade の outcome 関係** を検定する. トレーダーが daily chart を見て
"上昇 trend か" を判断する直感を数学的に formal 化.

## 1. Strategy native nature 分類 (LOCKED a priori)

Code inspection (entry logic) に基づく:

| Strategy | Native Nature | 期待挙動 |
|----------|---------------|---------|
| ema_trend_scalp | TREND | UP/DOWN regime で WR↑ |
| stoch_trend_pullback | TREND | UP/DOWN regime で WR↑ |
| vol_surge_detector | BREAKOUT | UP/DOWN (momentum) で WR↑ |
| bb_squeeze_breakout | BREAKOUT | UP/DOWN (expansion) で WR↑ |
| bb_rsi_reversion | RANGE | RANGE regime で WR↑ |
| engulfing_bb | RANGE | RANGE regime で WR↑ |
| fib_reversal | RANGE | RANGE regime で WR↑ |
| sr_channel_reversal | RANGE | RANGE regime で WR↑ |

**Group labels**: TREND={ems, stp}, BREAKOUT={vsd, bsb}, RANGE={brr, ebb, fr, src}
**検定対象 (Phase 4b active)**: 8 strategies

## 2. Native TF (per-trade `mode` field から derive)

| Mode | Native TF | Candidate higher-TFs (H) |
|------|-----------|-------------------------|
| scalp / scalp_eur | 1m | **5m, 15m, 30m, 1h** |
| scalp_5m / scalp_5m_eur / scalp_5m_gbp | 5m | **15m, 30m, 1h, 4h** |
| daytrade / daytrade_eur / daytrade_gbpusd / daytrade_eurjpy / daytrade_gbpjpy / daytrade_eurgbp | 15m | **30m, 1h, 4h, 1d** |
| daytrade_1h / daytrade_1h_eur | 1h | **4h, 1d** |

Trade の `mode` field で native TF を lookup. 不明 mode は検定外.

## 3. Regime signal definition (LOCKED)

### Signal A: Higher-TF EMA slope
```
EMA20_H[t] = 20-bar EMA on higher-TF H bars aligned with trade entry time
slope_H = (EMA20_H[t] − EMA20_H[t−5]) / σ_return_H
  where σ_return_H = stdev of 5-bar EMA diff over 100-bar rolling window
regime_H := UP    if slope_H > +0.5
          := DOWN  if slope_H < −0.5
          := RANGE otherwise
```

**Parameters (LOCKED)**: EMA period=20, lookback k=5, σ window=100, threshold=0.5.

理由: 20 bars ≈ 日内 trend filter 相当、k=5 で最新 direction、σ 正規化で TF 共通基準化.

### 適用フロー
1. Trade の `entry_time` と `instrument` を取り出す
2. Mode から native TF 判定
3. Candidate H (§2) 各々で higher-TF 5m multiple bars を OANDA から fetch
4. `entry_time` を含む H bar を特定、その bar 時点の regime_H を計算
5. Trade に regime_H label 付与

## 4. MTF 選択手続き (LOCKED)

### Train / Test split
- 全 trades を entry_time で sort
- **Train**: 最古 70%
- **Test**: 最新 30% (held-out)

### Train 上での H 選択 (per strategy)
各 strategy S について、candidate H 集合から **1 つの最適 H** を:

```
H*(S) = argmax_H Cohen_h_train(S, H)
  where Cohen_h = 2(arcsin√p_aligned − arcsin√p_misaligned)
        aligned := (S in TREND ∪ BREAKOUT ∧ regime_H ∈ {UP,DOWN})
                 ∨ (S in RANGE ∧ regime_H = RANGE)
```

Cohen's h は effect size、MI より effect direction が interpretable.
Tie-break: より短い H を選ぶ (data 量優先).

### Test 上での validation
選ばれた H* の下で **held-out test data** のみで以下検定:

```
H0: regime_H* と outcome は独立 (WR_aligned = WR_misaligned)
H1: TREND/BREAKOUT 戦略 → WR_aligned > WR_misaligned + δ (δ=0.05)
    RANGE 戦略 → 同様
```

検定統計量: Fisher exact 2-tail p.

### Bonferroni (LOCKED)
- M = 8 strategies (each evaluated once on test with its selected H*)
- α_cell = 0.05 / 8 = **6.25e-3**

Test 段階で H 選択は済んでいるため、multiple testing inflation は 8 のみ.

## 5. Binding criteria — SURVIVOR (LOCKED)

Strategy × H* が **以下 5 条件を全て test data で満たせば SURVIVOR**:

1. **N_aligned ≥ 30** (power floor)
2. **N_misaligned ≥ 30** (comparison 可能)
3. **WR_aligned − WR_misaligned ≥ 0.05** (δ)
4. **Fisher exact p < 6.25e-3** (Bonferroni)
5. **Cohen's h ≥ 0.2** (small effect threshold)

### CANDIDATE
条件 1, 2, 3, 5 を満たすが Fisher Bonferroni 未達.

### Scenario (per pre-reg §7)
| Scenario | Rule | Action |
|----------|------|--------|
| A | SURVIVOR = 0 ∧ CANDIDATE = 0 | MTF alignment で edge 検出不能. Track B closure |
| B | SURVIVOR = 0 ∧ CANDIDATE ≥ 1 | Suggestive, Phase 4d (N 蓄積 or 他 signal) |
| C | SURVIVOR ≥ 1 | MTF-based routing design authorize |

## 6. Disallowed (post-hoc 禁止)

- Pre-reg LOCK 後の parameter 調整 (EMA period, k, threshold)
- Strategy nature の事後修正
- H 探索空間拡大 (§2 以外の TF 追加)
- δ, α, Cohen's h threshold の緩和
- Selection 基準変更 (Cohen_h 以外)
- Test data の訓練的利用 (peeking)
- Bonferroni 分母の縮小

## 7. Execution

1. `/tmp/phase4c_mtf_regime_test.py` 作成
2. Live trades + OANDA higher-TF bars fetch
3. Per trade: regime_H* compute
4. Train/Test split → select H* per strategy → test Fisher
5. KB 結果記録: [[phase4c-mtf-regime-result-2026-04-24]]
6. Commit

## 8. Pre-registered hypotheses

**H1 (moderate)**: TREND 戦略 (ems, stp) は H=1h or 4h で aligned WR +0.05-0.10 差
**H2 (weak)**: RANGE 戦略 (brr, ebb) は RANGE regime で +0.05-0.10 差
**H3 (moderate null)**: BREAKOUT は N 不足で CANDIDATE まで (Scenario B)
**H4 (overall null)**: MTF alignment 自体が FX では weak signal で Scenario A

H2 期待値が最も strong (Phase 4b で bb_rsi_reversion だけが positive EV).

## References

- [[phase4b-cell-edge-test-result-2026-04-24]] (upstream)
- [[pre-registration-phase4c-v6-feature-redesign-2026-04-24]] (parallel Track A)
- [[phase4a-v5-classifier-stability-2026-04-23]] (v5 LOCKED 資産)
- [[lesson-premature-neutralization-2026-04-23]]
