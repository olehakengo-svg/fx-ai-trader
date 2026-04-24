# Pre-registration: Phase 4c MTF Signal B — ADX Regime Classifier (2026-04-24)

**Locked**: 2026-04-24 (本 doc 確定後変更禁止)
**Track**: B — Signal B (ADX)
**Upstream**: [[pre-registration-phase4c-mtf-regime-2026-04-24]] (Signal A, Scenario A closure)
**Next session queued**: Signal C (structural HH/HL), Signal D (composite)
**Parent memory**: [[feedback_success_until_achieved]]

## 0. Rationale (何故 Signal B を別 pre-reg で検定するか)

Signal A (higher-TF EMA20 slope) は 16 days / 1682 trades で Scenario A (1 REJECT,
7 INSUFFICIENT). 敗因は:
- Train→Test sign flip (engulfing_bb, ema_trend_scalp, fib_reversal で train/test の
  Cohen's h 符号が反転) → over-fitting from argmax H selection across 4 candidates
- Test held-out 3 days (70/30 split) で per-strategy N が殆ど <30
- EMA slope は "方向性" に敏感だが "市場性質 (trend vs range)" を直接定量化していない

Signal B (ADX) は Wilder の古典的 directional movement indicator で、**方向ではなく
trend 強度** を測る. ADX ≥ 25 = 強い directional 動き, ≤ 20 = 低振幅 range. Signal A と
数学的に独立 (slope = 符号あり方向量, ADX = 符号なし強度量) で相関は弱い.

本 pre-reg は Signal A で得た 2 つの negative lesson を事前に反映:
1. **Train ratio 50/50** に変更 (70/30 から) — Test N 増強で detection power 向上
2. **Bonferroni family 拡張** — 並行計画する Signal B+C+D (3 signals × 8 strategies) を
   一括 family-wise error control (α_cell = 0.05/24 = 2.083e-3)

## 1. Strategy nature (Signal A pre-reg §1 と完全同一, LOCKED)

TREND={ema_trend_scalp, stoch_trend_pullback}
BREAKOUT={vol_surge_detector, bb_squeeze_breakout}
RANGE={bb_rsi_reversion, engulfing_bb, fib_reversal, sr_channel_reversal}

M = 8 strategies.

## 2. Native TF と candidate H (Signal A pre-reg §2 と完全同一, LOCKED)

| Mode group | Native TF | Candidate higher-TFs (H) |
|------------|-----------|--------------------------|
| scalp 系 | 1m | 5m, 15m, 30m, 1h |
| scalp_5m 系 | 5m | 15m, 30m, 1h, 4h |
| daytrade 15m 系 | 15m | 30m, 1h, 4h, 1d |
| daytrade_1h 系 | 1h | 4h, 1d |

## 3. Signal B definition (LOCKED)

### 計算手続き

Wilder's Directional Movement Index on higher-TF H bars:

```
TR      = max(H[t]-L[t], |H[t]-C[t-1]|, |L[t]-C[t-1]|)
+DM[t]  = H[t]-H[t-1]  if (H[t]-H[t-1]) > (L[t-1]-L[t]) and > 0 else 0
-DM[t]  = L[t-1]-L[t]  if (L[t-1]-L[t]) > (H[t]-H[t-1]) and > 0 else 0
ATR14   = Wilder-smoothed TR over 14 bars
+DI14   = 100 * Wilder-smoothed(+DM) / ATR14
-DI14   = 100 * Wilder-smoothed(-DM) / ATR14
DX      = 100 * |+DI14 - -DI14| / (+DI14 + -DI14)
ADX14   = Wilder-smoothed(DX) over 14 bars
```

Wilder smoothing: S[0] = sum of first 14 values, S[t] = S[t-1] - S[t-1]/14 + X[t].
Standard equivalent to EMA α=1/14 after initial SMA prime.

### Regime labeling (LOCKED)

```
regime_H := TREND  if ADX14[t] >= 25
         := RANGE  if ADX14[t] <= 20
         := NEUTRAL (excluded from analysis)  otherwise
```

**Parameter LOCK**: period=14, trend_thresh=25, range_thresh=20. 以下は**事前に禁止**:
- period 探索 (10, 20, 28 等)
- threshold 探索 (22/18 等)
- median ADX cutoff 等の代替定義

理由: 25/20 は Wilder (1978) 原本定義. "古典値" を pre-LOCK することで後付けチューニング
の余地を完全排除.

## 4. Alignment rule (LOCKED)

```
aligned    := (nature ∈ {TREND, BREAKOUT}  ∧  regime_H = TREND)
           ∨  (nature = RANGE             ∧  regime_H = RANGE)
misaligned := (nature ∈ {TREND, BREAKOUT}  ∧  regime_H = RANGE)
           ∨  (nature = RANGE             ∧  regime_H = TREND)
excluded   := regime_H = NEUTRAL
```

## 5. Train / Test split (LOCKED, Signal A から変更)

- 全 trades を `entry_time` で sort
- **Train: 最古 50%** (vs Signal A: 70%)
- **Test:  最新 50%** (held-out)

変更理由: Signal A で Test 3 days N<30 が gating. 50/50 にすることで Test ~8 days
期待. Train 側は 1 signal あたり 4 candidate H 探索できるだけの N があれば十分
(strategy 別 20-100 ≥ 20).

## 6. Train 上での H* 選択 (LOCKED, Signal A §4 と同手続き)

```
H*(S) = argmax_H  Cohen_h_train(S, H)
      where Cohen_h = 2·(arcsin√p_aligned − arcsin√p_misaligned)
```

Tie-break: より短い H (data 量優先).

制約: train で aligned, misaligned 各々 N≥5 ない H は除外 (Cohen's h 推定不安定).

## 7. Test 上での validation (LOCKED)

### Primary test: Fisher exact 2-tail on test held-out

```
H0: Pr[WIN | aligned, test] = Pr[WIN | misaligned, test]
H1: two-sided difference (pre-reg は direction-agnostic — 逆エッジも検出)
```

Fisher exact p_2tail.

### Bonferroni correction (LOCKED, 重要な変更点)

家族サイズ:
- 計画 signals: B (本 pre-reg), C (次 session), D (その次)
- Strategies per signal: 8
- **Family size M = 3 × 8 = 24**
- α_cell = 0.05 / 24 = **2.083e-3**

注意:
- Signal A は別 pre-reg で α=6.25e-3 既 closure → 本 family には含めない
- Signal C, D 未実施だが prospective に M に含める (post-hoc に α 緩和しない保険)
- もし Signal C, D が将来 cancel されれば、本 signal の α は **事後修正しない** (保守側)

### SURVIVOR 基準 (LOCKED, 5 条件全て)

1. **N_aligned ≥ 30** (test data, power floor)
2. **N_misaligned ≥ 30** (test data)
3. **|WR_aligned − WR_misaligned| ≥ 0.05** (effect floor, δ=5%)
4. **Fisher 2-tail p < 2.083e-3** (Bonferroni)
5. **|Cohen h| ≥ 0.2** (small effect)

### CANDIDATE
条件 1, 2, 3, 5 を満たすが Fisher Bonferroni 未達.

### Direction 要件

H1 は 2-tail. **正の dWR と負の dWR を区別しない**. 逆エッジ (aligned の方が WR 低い)
も SURVIVOR になりうる — これは "ADX signal は情報を持つ" の証拠として扱い、
実運用では逆向き使用 (misaligned で entry) を意味する.

## 8. Secondary (exploratory, Bonferroni 対象外, 報告のみ)

以下は **decision rule ではなく exploratory report**. この結果単独で Scenario 判定を
変更しない:

- Per-pair WR (USDJPY, EURUSD, GBPUSD, EURJPY, GBPJPY, EURGBP)
- Nature-level aggregate (TREND aggregated, BREAKOUT aggregated, RANGE aggregated)
- Wilson 95% CI for WR_aligned, WR_misaligned
- Profit factor (PF = Σwin_pips / |Σloss_pips|) per strategy × regime
- Kelly half fraction (K/2 = (WR·(avg_win/avg_loss) − (1−WR)) / (avg_win/avg_loss))
- Train 上での Cohen h, Test 上での Cohen h (sign flip 検出)

Secondary 結果は **次 pre-reg の仮説生成** 用途でのみ参照.

## 9. Disallowed (post-hoc 禁止, 違反は結果破棄)

- §3 の period/threshold 調整
- §5 の Train ratio 変更
- §7 の α/δ/Cohen h threshold 緩和
- §1 strategy nature 事後修正
- §2 candidate H 拡張
- Test data peeking (model selection に使う)
- Bonferroni M の縮小 (24 → 8 など)
- Exclusion rule の事後変更 (NEUTRAL band 圧縮等)
- Secondary 結果で primary 判定を書き換える

## 10. Data & execution

- **Data source**: Production API `/api/demo/trades?status=closed&date_from=2026-04-08`
  (CUTOFF は Signal A と同じ 2026-04-08 = Phase 4 launch 以降)
- **END_TS**: `datetime.now(UTC) - 10 min` で clamp (前 bug fix 踏襲)
- **OANDA**: `fetch_ohlcv_range(sym, from=2025-10-01, to=END_TS, interval=H)` —
  warm-up 6.5 ヶ月は Wilder ADX14 convergence (>200 bars) 確保に十分
- **Script**: `/tmp/phase4c_mtf_signalB_adx_test.py` (new)
- **Output**: `/tmp/phase4c_signalB_output.txt`, `/tmp/phase4c_signalB_summary.json`
- **KB result**: `knowledge-base/wiki/analyses/phase4c-mtf-signalB-adx-result-2026-04-24.md`

## 11. Pre-registered hypotheses

| H | Type | Prediction |
|---|------|-----------|
| H1 | moderate | TREND 戦略 (ems, stp) は H=15m/30m で aligned WR −5〜+10% (方向 neutral) |
| H2 | moderate | RANGE 戦略 (brr, ebb, fr, src) は RANGE regime で aligned WR +5〜+10% |
| H3 | weak | BREAKOUT は ADX signal と相互作用あり (H=15m で positive dWR 期待) |
| H4 | overall | 3/8 以上 SURVIVOR なら Scenario C (Signal B は edge source) |

H2 が primary bet (Signal A で bb_rsi_reversion が test 逆エッジを示した — ADX RANGE
filter は RANGE-nature 戦略の逆行局面を正しく除外する可能性).

## 12. Scenario & authorization

| Scenario | Rule | Action |
|----------|------|--------|
| A | SURVIVOR = 0 ∧ CANDIDATE = 0 | 本 signal 下 null. Signal C に移行 (next session) |
| B | SURVIVOR = 0 ∧ CANDIDATE ≥ 1 | Suggestive, N 蓄積待ち vs Signal C 並行 |
| C | SURVIVOR ≥ 1 | ADX routing design 認可 (本 survivor cell のみ) |

**Scenario A でも Track B 本体の closure は禁止** — Signal C, D, composite 未検定で
Track B 終了は誤り.

## References

- [[pre-registration-phase4c-mtf-regime-2026-04-24]] (Signal A, upstream)
- [[phase4c-mtf-regime-result-2026-04-24]] (Signal A result, Scenario A provisional)
- [[phase4b-cell-edge-test-result-2026-04-24]] (先行 power denial evidence)
- [[feedback_success_until_achieved]] (memory, 継続 mandate)
- Wilder, J.W. (1978). *New Concepts in Technical Trading Systems*. ADX / DMI 原論.
