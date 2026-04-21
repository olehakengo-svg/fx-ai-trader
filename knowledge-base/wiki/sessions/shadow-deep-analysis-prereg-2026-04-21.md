# Binding Pre-Registration — Shadow Deep Analysis (Tasks 1-4)

**Registered**: 2026-04-21 (UTC 09:59)
**Based on**: [[handover-shadow-deep-analysis-2026-04-21]] + [[shadow-deep-analysis-2026-04-21]]
**Re-evaluation date (binding)**: **2026-05-05** (post-Cutoff N doubling checkpoint)

---

## 0. Data pre-registration (binding)

| Field | Value |
|---|---|
| Source | `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2500` |
| Filter | `is_shadow=1 AND outcome IN (WIN, LOSS) AND instrument != XAU_USD` |
| N (at registration) | **1711** (WIN=474, LOSS=1237) |
| Baseline WR | **27.70%** |
| Distinct strategies with shadow | 44 |
| Axis (REQUIRED) | instrument × _session (UTC bands) × direction |
| XAU exclusion | Applied (memory: feedback_exclude_xau) |

## 1. Branch 1 — LIVE promotion candidates (binding)

**Gate criteria (binding, locked)**:
1. N_cell ≥ 10
2. cell WR ≥ 50%
3. Lift ≥ 1.5x baseline
4. Wilson 95% lower bound > pair BEV_WR (JPY=34.4%, non-JPY=36.0%)

### Result

**Promotion candidates that pass all 4 gates: 0**

Near-misses (documented, not promoted):

| Strategy | Cell | N | WR | Wilson下限 | BEV | Gap to pass |
|---|---|---:|---:|---:|---:|---|
| fib_reversal | USD_JPY×london×BUY | 12 | 58.3% | 32.0% | 34.4% | Wilson 下限 -2.4pp |
| sr_fib_confluence | GBP_USD×london×BUY | 14 | 50.0% | 26.8% | 36.0% | Wilson 下限 -9.2pp |

**Binding decision**: **No LIVE promotion from Branch 1 at 2026-04-21.** Re-evaluate at 2026-05-05 checkpoint when N may have doubled.

## 2. Branch 2 — Strategy rescue via LOSS-exclusion (binding)

**LOSS-cell exclusion rule (binding)**: cell_WR ≤ 15% AND LOSS_LR ≥ 2.0 AND N_cell ≥ 5 (fallback: WR≤20% AND LR≥1.5 AND N≥8).

**Promotion verdict thresholds (binding)**:
- **NEW_STRATEGY**: N_post ≥ 30 AND WR_post ≥ 50% AND Wilson下限 > 35%
- **NEW_STRATEGY_TENTATIVE**: N_post ≥ 20 AND WR_post ≥ 50%
- **UNSALVAGEABLE**: N_post ≥ 30 AND WR_post < 40%

### Result: Core decision for all 44 strategies

| Verdict | Count | Strategies |
|---|---:|---|
| ★NEW_STRATEGY | **0** | — |
| NEW_STRATEGY_TENTATIVE | **0** | — |
| MARGINAL_IMPROVEMENT | 2 | ema_cross (35→40%), dt_bb_rsi_mr (46→46%) |
| **UNSALVAGEABLE** | **12** | ema_trend_scalp, fib_reversal, stoch_trend_pullback, bb_rsi_reversion, sr_channel_reversal, macdh_reversal, sr_fib_confluence, engulfing_bb, bb_squeeze_breakout, vol_surge_detector, dt_sr_channel_reversal, ema_pullback |
| INSUFFICIENT_N_POST | 27 | (shadow N < 20 after filter — need accumulation) |
| NEEDS_MORE_DATA | 3 | trend_rebound, dual_sr_bounce, ema200_trend_reversal |

**Binding interpretation**:
> **LOSS 条件を排除しても、Shadow 44 戦略のうち WR ≥ 50% に到達する戦略はゼロ.**
> これは Task 4 Branch 2 の CORE 問い「LOSS 条件排除で勝てる戦略に生まれ変われるか?」への **data-driven NO answer**.

### 12 UNSALVAGEABLE strategies — FORCE_DEMOTE 候補リスト (2026-05-05 再評価で確定)

| Strategy | N | base WR | 最大 exclusion 後 WR | N_post | Wilson下限 |
|---|---:|---:|---:|---:|---:|
| ema_trend_scalp | 295 | 23.4% | 28.1% | 228 | 22.6% |
| fib_reversal | 187 | 35.3% | 36.4% | 176 | 29.6% |
| stoch_trend_pullback | 142 | 28.9% | 32.5% | 117 | 24.7% |
| bb_rsi_reversion | 128 | 28.9% | 34.3% | 105 | 25.9% |
| sr_channel_reversal | 126 | 23.8% | 25.2% | 111 | 18.1% |
| macdh_reversal | 109 | 27.5% | 30.1% | 93 | 21.7% |
| sr_fib_confluence | 102 | 24.5% | 29.8% | 84 | 21.0% |
| engulfing_bb | 101 | 31.7% | 33.3% | 93 | 24.6% |
| bb_squeeze_breakout | 83 | 25.3% | 31.7% | 63 | 21.6% |
| vol_surge_detector | 41 | 24.4% | 29.0% | 31 | 16.1% |
| dt_sr_channel_reversal | 38 | 31.6% | 31.6% | 38 | 19.1% |
| ema_pullback | 36 | 36.1% | 36.1% | 36 | 22.5% |

## 3. FORCE_DEMOTE 実行条件 (binding, pre-registered)

**2026-05-05 再評価時に以下全て満たせば FORCE_DEMOTE 実行**:

1. Shadow N (strategy level) が 2026-04-21 時点から ≥ +30% 増加していること (データ不足排除)
2. 再実行した Branch 2 analysis で依然として UNSALVAGEABLE verdict (WR_post < 40% AND N_post ≥ 30)
3. Wilson 95% 上限 < BEV_WR (統計的に break-even 未達が確定)

**FORCE_DEMOTE 対象**: `entry_type` を `modules/demo_trader.py::_SHADOW_ONLY_TYPES` に追加 (OANDA 送信遮断). LIVE に漏れていたものは `_FORCE_DEMOTED_TYPES` へ.

## 4. Branch 1 再評価 (binding, pre-registered)

**2026-05-05 再評価時、以下セルで gate 再検証**:

- fib_reversal × USD_JPY × london × BUY (at 2026-04-21: N=12, WR=58.3%, Wilson下限 32.0%)
- sr_fib_confluence × GBP_USD × london × BUY (at 2026-04-21: N=14, WR=50.0%, Wilson下限 26.8%)
- bb_rsi_reversion × EUR_USD × ny × BUY (at 2026-04-21: N=5 too small; watch for N≥10)

**Gate pass 条件**: 上記 4 gates 全てクリア + Bonferroni α/M (M=探索空間 cells 数) で補正. M 2026-05-05 時点で再計算.

## 5. Multiple testing 補正 (Bonferroni, binding)

- 探索空間: 44 strategies × 6 pairs × 4 sessions × 2 directions = **2112 cells**
- Bonferroni α = 0.05 / 2112 = **2.37e-5**
- **本 analysis における Fisher exact p**: 最小値は sr_fib_confluence × GBP_USD×london×BUY の p=0.0386 (>α/M).
- **結論**: strict Bonferroni で有意な cell は **0件**.
- **運用判断**: Bonferroni は "hypothesis 発見器" として使用, 確定 promotion には追加 N で out-of-sample 検証必須.

## 6. 次回セッション protocol (2026-05-05)

1. 同スクリプト再実行: `python3 knowledge-base/wiki/sessions/shadow-deep-analysis-2026-04-21.py`
2. diff を 2026-04-21 結果と比較 (JSON 同士 diff)
3. FORCE_DEMOTE 条件充足 strategy を確定
4. Branch 1 near-miss cells の再 gate check
5. 本ファイル内の binding thresholds は変更禁止 (goalpost-moving 回避)

## 7. 守るべきこと (protocol compliance)

- [x] Shadow only (is_shadow=1) — Live data 混在なし
- [x] XAU_USD 除外 — memory: feedback_exclude_xau
- [x] pair × session × direction を軸に含める
- [x] 閾値を事前 binding 登録
- [x] 観測後の基準変更なし
- [x] Bonferroni 多重検定補正を明記
- [x] Wilson CI 下限を judgement に使用
- [ ] Live 昇格: 今回ゼロ (該当なし)

---

**Status**: BINDING — 2026-05-05 まで変更禁止.
