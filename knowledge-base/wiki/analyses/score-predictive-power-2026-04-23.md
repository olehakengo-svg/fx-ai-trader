# Score 予測力検証 — Post-cutoff Within-Strategy 分析 (2026-04-23)

## TL;DR
[[handover-tp-hit-quant-analysis-2026-04-21]] の「score TP-hit 予測力 p=0.42」を post-cutoff データ (N=1,338) で再検証。**aggregate p=0.55 で noise 結論強化**。さらに within-strategy 分解で **bb_rsi_reversion が inverse correlation (Bonferroni 後非有意)** を発見。`DaytradeEngine.select_best()` の score-based 選択は、一部戦略で逆効果の可能性あり — **要モニタリング**。

## 検証 (post-cutoff, 2026-04-16+)

### Aggregate
| outcome | N | μ_score |
|---|---|---|
| WIN | 341 | 0.461 |
| LOSS | 997 | 0.407 |
| diff | — | +0.054 |

Welch t=0.596, p=0.551 — **noise** (handover 結論を post-cutoff で確認)。

### Per-strategy (N≥30)

| strategy | N | μ_win | μ_loss | diff | p | 備考 |
|---|---|---|---|---|---|---|
| bb_rsi_reversion | 148 | 0.34 | 0.54 | **-0.20** | **0.0238*** | 逆相関 |
| vwap_mean_reversion | 30 | 2.13 | 1.49 | +0.64 | 0.226 | N 小 |
| sr_fib_confluence | 54 | 4.60 | 3.13 | +1.47 | 0.314 | 正方向だが非有意 |
| macdh_reversal | 30 | 0.00 | 0.04 | -0.04 | 0.317 | ほぼ score 未使用 |
| fib_reversal | 82 | 0.26 | 0.25 | +0.01 | 0.938 | ほぼ 0 |
| ema_trend_scalp | 375 | 0.00 | 0.00 | 0.00 | 1.000 | **score 未使用** |
| sr_channel_reversal | 119 | 0.00 | 0.00 | 0.00 | 1.000 | **score 未使用** |
| stoch_trend_pullback | 92 | 0.00 | 0.00 | 0.00 | 1.000 | **score 未使用** |
| engulfing_bb | 90 | 0.00 | 0.00 | 0.00 | 1.000 | **score 未使用** |
| bb_squeeze_breakout | 61 | 0.00 | 0.00 | 0.00 | 1.000 | **score 未使用** |
| vol_surge_detector | 54 | 0.00 | 0.00 | 0.00 | 1.000 | **score 未使用** |

### Simpson paradox 確認
- Aggregate diff: +0.054
- Within-strategy avg diff: +0.171 (但し N=30 戦略が混入)
- Within-strategy sign consensus: **3/11 positive, 8/11 ≤0**
- 判定: **within-strategy でも score は予測力なし or 逆相関傾向**

## 主要発見

### 1. score 未使用戦略が 7/11 を占める
`Candidate.score=0.0` または固定値で出している戦略: ema_trend_scalp, sr_channel_reversal, stoch_trend_pullback, engulfing_bb, bb_squeeze_breakout, vol_surge_detector, macdh_reversal (post-cutoff N=901 / 1,338 = 67%)。

→ **`select_best(candidates) = max(candidates, key=lambda c: c.score)` において、score=0 戦略は事実上無視される**。score を populate する戦略 (bb_rsi, sr_fib, vwap_mr) の候補が優先される構造。

### 2. bb_rsi_reversion の inverse correlation
- 生の p=0.024 だが 11 戦略マルチテスト → **Bonferroni 補正で p=0.26 (非有意)**
- 方向性 (WIN μ=0.34 < LOSS μ=0.54) は **handover の 298 件 TP-hit × bb_rsi_reversion で観測された同様パターンと一致**
- effect size は非ゼロ (20% of score std) — N 蓄積で確証を狙える

### 3. select_best() の構造的バイアス
`select_best` は score 最大を選ぶため:
- bb_rsi_reversion の score=0.8 候補 > bb_rsi_reversion の score=0.3 候補 が優先される
- bb_rsi で score が逆相関なら、**select_best は系統的に悪い候補を選ぶ**

## 判断 (CLAUDE.md 判断プロトコル準拠)

| 項目 | 結論 |
|---|---|
| 根拠データ | post-cutoff N=148 (bb_rsi) ✅ N≥30 |
| Bonferroni 後有意性 | **非有意** (p=0.26) |
| 実装提案 | **なし** — N 蓄積待ち |
| 監視優先度 | **🟡 Watch** — bb_rsi_reversion score N≥200 到達時に再検証 |
| P1 Sentinel bypass 正当性 | **強化** (score 予測力ゼロ + 一部 inverse) |

## Next action
- [ ] bb_rsi_reversion post-cutoff N>=200 到達時に score inverse を Bootstrap CI で再検証
- [ ] score=0 戦略の候補選択ロジックを確認 — `select_best` が score=0 を無視するかどうか実装確認
- [ ] handover のタスク close: `score 計算方法見直し` → **ACTIVE WATCH** (現 N 不足)

## Related
- [[handover-tp-hit-quant-analysis-2026-04-21]] (原題)
- [[spread-at-entry-confounding-2026-04-23]] (同手法での前例)
- [[lesson-confounding-in-pooled-metrics-2026-04-23]]
- [[lesson-confidence-ic-zero]] — confidence も同様の予測力問題

## Source
- Analysis: 2026-04-23 07:2X UTC
- Data: `/api/demo/trades?status=closed&date_from=2026-04-16` paginated (N=1,483 raw / 1,338 with score)
- Script: inline Python (Welch t + Simpson paradox check)
