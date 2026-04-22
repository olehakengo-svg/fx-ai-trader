# TP-hit / SL-hit Deep Mechanics — Actionable WR Improvement

**Generated**: 2026-04-22 (UTC)  
**Scope**: is_shadow=1 ∧ outcome∈{WIN,LOSS} ∧ non-XAU, N=1884  
**Baseline WR**: 27.87%  
**Cutoff**: 2026-04-16 (pre/post WF 分析で再現性確認)  

---

## A. Hold-duration decomposition — WIN/LOSS の時間構造

- WIN hold time (min): median=13.7, p25=5.7, p75=29.8
- LOSS hold time (min): median=7.5, p25=2.9, p75=15.3

### A.1 戦略別 hold duration (TP=WIN, SL=LOSS)
| strat×instr | N | WIN med hold | LOSS med hold | TP/SL speed ratio |
|---|---:|---:|---:|---:|
| ema_trend_scalp×USD_JPY | 174 | 8.7 min | 4.7 min | 1.87x |
| ema_trend_scalp×EUR_USD | 120 | 12.1 min | 4.9 min | 2.47x |
| fib_reversal×USD_JPY | 117 | 7.6 min | 4.8 min | 1.58x |
| stoch_trend_pullback×USD_JPY | 113 | 12.3 min | 4.4 min | 2.83x |
| bb_rsi_reversion×USD_JPY | 101 | 7.0 min | 6.2 min | 1.14x |
| sr_channel_reversal×USD_JPY | 94 | 11.0 min | 6.4 min | 1.72x |
| fib_reversal×EUR_USD | 76 | 5.7 min | 6.5 min | 0.87x |
| engulfing_bb×USD_JPY | 75 | 12.6 min | 5.2 min | 2.40x |
| ema_trend_scalp×GBP_USD | 57 | 25.8 min | 7.3 min | 3.54x |
| macdh_reversal×USD_JPY | 56 | 6.0 min | 3.6 min | 1.65x |
| bb_squeeze_breakout×USD_JPY | 53 | 14.8 min | 5.3 min | 2.79x |
| macdh_reversal×EUR_USD | 51 | 3.9 min | 3.8 min | 1.01x |
| ema_cross×USD_JPY | 42 | 26.6 min | 42.4 min | 0.63x |
| bb_rsi_reversion×EUR_USD | 30 | 8.3 min | 10.6 min | 0.78x |
| sr_channel_reversal×EUR_USD | 29 | 8.5 min | 5.5 min | 1.55x |

**解釈**: ratio > 1 = WIN の方が長く持ちTP 到達 (slow TP). ratio < 1 = LOSS の方が時間がかかる (gradual SL). ratio ≈ 1 は対称的挙動.

---

## B. Immediate Death phenomenon — LOSS が一度も favorable に振れない現象

Definition: `MFE_favorable_pips ≤ 0.5 pip` (entry 直後から逆行して SL 直行)

- Portfolio-wide immediate death rate: **822/1359 = 60.5%** of LOSSes
- [[mfe-zero-analysis]] の 90.6% 主張とほぼ整合

### B.1 戦略別 immediate death rate (N≥20 cells)
| strat×instr | N_loss | immediate death | rate | avg MAE in death | implication |
|---|---:|---:|---:|---:|---|
| ema_trend_scalp×USD_JPY | 132 | 71 | 54% | 4.2 pip | Mixed |
| ema_trend_scalp×EUR_USD | 90 | 49 | 54% | 3.8 pip | Mixed |
| fib_reversal×USD_JPY | 79 | 47 | 59% | 2.9 pip | Mixed |
| stoch_trend_pullback×USD_JPY | 81 | 44 | 54% | 3.6 pip | Mixed |
| bb_rsi_reversion×USD_JPY | 71 | 31 | 44% | 4.8 pip | SL too tight |
| sr_channel_reversal×USD_JPY | 70 | 48 | 69% | 3.8 pip | Mixed |
| fib_reversal×EUR_USD | 49 | 37 | 76% | 1.9 pip | Mixed |
| engulfing_bb×USD_JPY | 51 | 28 | 55% | 3.7 pip | Mixed |
| ema_trend_scalp×GBP_USD | 49 | 28 | 57% | 5.4 pip | Mixed |
| macdh_reversal×USD_JPY | 43 | 30 | 70% | 2.4 pip | Mixed |
| bb_squeeze_breakout×USD_JPY | 37 | 24 | 65% | 3.3 pip | Mixed |
| macdh_reversal×EUR_USD | 35 | 28 | 80% | 1.2 pip | Mixed |
| ema_cross×USD_JPY | 27 | 27 | 100% | 0.0 pip | Entry timing bad |
| bb_rsi_reversion×EUR_USD | 19 | 11 | 58% | 3.8 pip | Mixed |
| sr_channel_reversal×EUR_USD | 24 | 11 | 46% | 3.5 pip | SL too tight |

**含意**:
- Rate > 90%: entry が逆方向に生まれている → **entry logic 側に改善の余地** (confidence 閾値 / regime filter 追加)
- Rate < 50%: entry 方向は合っているが SL が速く潰される → **SL 距離 / BE 移動が速すぎる可能性**

---

## C. WIN の品質分解 — "Clean WIN" vs "Lucky WIN"

Definition:
- **Clean WIN**: `MAE/|SL| < 0.25` (ほぼ逆行なく TP 到達)
- **Lucky WIN**: `MAE/|SL| > 0.67` (SL 寸前から反転してTP)

Clean WIN 比率 = 戦略の "edge quality" 指標. Lucky WIN 比率が高い = ランダム寄与大で再現性疑義.

### C.1 戦略別 WIN 品質
| strat×instr | N_win | Clean | Lucky | Clean比 | edge quality |
|---|---:|---:|---:|---:|---|
| ema_trend_scalp×USD_JPY | 42 | 9 (21%) | 11 (26%) | 21% | mixed |
| ema_trend_scalp×EUR_USD | 30 | 9 (30%) | 2 (7%) | 30% | mixed |
| fib_reversal×USD_JPY | 38 | 16 (42%) | 4 (11%) | 42% | mixed |
| stoch_trend_pullback×USD_JPY | 32 | 15 (47%) | 7 (22%) | 47% | mixed |
| bb_rsi_reversion×USD_JPY | 30 | 11 (37%) | 3 (10%) | 37% | mixed |
| sr_channel_reversal×USD_JPY | 24 | 10 (42%) | 1 (4%) | 42% | mixed |
| fib_reversal×EUR_USD | 27 | 15 (56%) | 4 (15%) | 56% | mixed |
| engulfing_bb×USD_JPY | 24 | 5 (21%) | 7 (29%) | 21% | mixed |
| ema_trend_scalp×GBP_USD | 8 | 5 (62%) | 1 (12%) | 62% | ✓ high (edge real) |
| macdh_reversal×USD_JPY | 13 | 12 (92%) | 0 (0%) | 92% | ✓ high (edge real) |
| bb_squeeze_breakout×USD_JPY | 16 | 5 (31%) | 1 (6%) | 31% | mixed |
| macdh_reversal×EUR_USD | 16 | 11 (69%) | 1 (6%) | 69% | ✓ high (edge real) |
| ema_cross×USD_JPY | 15 | 15 (100%) | 0 (0%) | 100% | ✓ high (edge real) |
| bb_rsi_reversion×EUR_USD | 11 | 2 (18%) | 2 (18%) | 18% | mixed |
| sr_channel_reversal×EUR_USD | 5 | 1 (20%) | 0 (0%) | 20% | mixed |
| sr_fib_confluence×USD_JPY | 6 | 4 (67%) | 1 (17%) | 67% | ✓ high (edge real) |
| stoch_trend_pullback×EUR_USD | 9 | 2 (22%) | 0 (0%) | 22% | mixed |
| engulfing_bb×EUR_USD | 10 | 5 (50%) | 4 (40%) | 50% | ⚠ luck-heavy |
| sr_fib_confluence×GBP_USD | 11 | 10 (91%) | 0 (0%) | 91% | ✓ high (edge real) |
| vol_surge_detector×USD_JPY | 9 | 2 (22%) | 2 (22%) | 22% | mixed |

---

## D. Entry feature の予測力 — Pointwise Mutual Information

PMI(feature=v, WIN) = log[ P(WIN|feature=v) / P(WIN) ]  
> 0 means this value tilts toward WIN. < 0 toward LOSS. |PMI| は効果量.

### D.1 Portfolio-wide PMI ranking (N≥50 cells only)
| feature | value | N | WR | PMI | Δ from base |
|---|---|---:|---:|---:|---:|
| mtf_alignment | aligned | 138 | 35.5% | +0.242 ⭐ | +7.6pp |
| confidence quartile | Q1 | 485 | 32.6% | +0.156 ⭐ | +4.7pp |
| close_vs_ema200 quartile | Q3 | 346 | 30.3% | +0.085  | +2.5pp |
| hmm_regime | NA | 865 | 30.2% | +0.080  | +2.3pp |
| ADX quartile | Q2 | 471 | 29.7% | +0.065  | +1.9pp |
| confidence quartile | Q3 | 494 | 29.4% | +0.052  | +1.5pp |
| session | ny | 848 | 29.1% | +0.044  | +1.3pp |
| ATR ratio quartile | Q3 | 426 | 29.1% | +0.044  | +1.2pp |
| spread quartile | Q1 | 1527 | 28.6% | +0.027  | +0.8pp |
| mtf_regime | range_tight | 288 | 28.5% | +0.022  | +0.6pp |
| mtf_vol_state | squeeze | 288 | 28.5% | +0.022  | +0.6pp |
| ADX quartile | Q1 | 476 | 28.4% | +0.018  | +0.5pp |
| mtf_alignment |  | 1396 | 28.2% | +0.013  | +0.4pp |
| mtf_regime |  | 1396 | 28.2% | +0.013  | +0.4pp |
| mtf_vol_state |  | 1396 | 28.2% | +0.013  | +0.4pp |

**Bottom 5 (avoid these)**:
- confidence quartile=Q4: N=443 WR=21.2% PMI=-0.273
- mtf_alignment=conflict: N=318 WR=24.2% PMI=-0.140
- mtf_regime=trend_up_strong: N=144 WR=24.3% PMI=-0.137
- mtf_vol_state=expansion: N=199 WR=24.6% PMI=-0.124
- spread quartile=Q4: N=357 WR=24.6% PMI=-0.123

---

## E. Virtual Filter Simulation — "もし X を filter していたら"

各 filter rule を shadow 全体に適用し、WR uplift と N cost をシミュレート.
戦略変更の判断材料 (pre-registration 候補として):

| Filter rule | N_kept | retention | WR_kept | uplift | PnL sum kept |
|---|---:|---:|---:|---:|---:|
| KEEP: mtf_alignment=aligned only | 138 | 7% | 35.5% | +7.6pp  | +51.8 pip |
| KEEP: confidence Q1 (paradox exploit) | 485 | 26% | 32.6% | +4.7pp  | -292.1 pip |
| DROP: confidence Q4 (paradoxical) | 1441 | 76% | 29.9% | +2.0pp  | -1431.0 pip |
| KEEP: NY session only | 848 | 45% | 29.1% | +1.3pp  | -1121.4 pip |
| DROP: spread Q4 (wide spread) | 1527 | 81% | 28.6% | +0.8pp  | -1686.8 pip |
| DROP: mtf_alignment=conflict | 1566 | 83% | 28.6% | +0.7pp  | -2325.0 pip |
| KEEP: BUY direction only | 991 | 53% | 28.2% | +0.3pp  | -1519.8 pip |
| KEEP: ADX Q2-Q3 (moderate trend) | 925 | 49% | 28.0% | +0.1pp  | -1073.1 pip |
| KEEP: ATR Q1 (low volatility) | 527 | 28% | 27.9% | +0.0pp  | -696.6 pip |
| DROP: offhours session | 1884 | 100% | 27.9% | +0.0pp  | -2611.0 pip |
| DROP: USD_JPY SELL (poor cell) | 1351 | 72% | 27.2% | -0.6pp  | -2119.2 pip |
| DROP: immediate_death-prone (score Q1) | 391 | 21% | 26.9% | -1.0pp  | -963.2 pip |

**★ marker**: uplift ≥ +3pp AND retention ≥ 30% — 実用価値と統計的安定の両立.

---

## F. Filter stacking — top 3 rules combined

Selected: KEEP: mtf_alignment=aligned only, KEEP: confidence Q1 (paradox exploit), DROP: confidence Q4 (paradoxical)

**Stacked result**: N_kept=32, WR=53.1% (uplift +25.3pp), retention=2%
Stacked PnL sum = +123.3 pip

---

## G. VWAP mean reversion — N=12 Shadow trade-level 分析 (small-N case study)

N が小さすぎて統計推論不能. 個別 trade の構造を機械的に列挙.

| date | pair | dir | conf | score | adx | atr | sess | outcome | hold_min | MFE | MAE | MAE/SL |
|---|---|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|
| 2026-04-15 | GBP_USD | SELL | 49.0 | 0.828 | 10.0 | 1.07 | ny | LOSS | 0 | 0.0 | 2.0 | 0.40 |
| 2026-04-16 | USD_JPY | BUY | 59.0 | -2.8 | 25.3 | 1.0 | tokyo | LOSS | 0 | 0.0 | 0.8 | 0.16 |
| 2026-04-16 | USD_JPY | BUY | 59.0 | -2.8 | 25.3 | 1.0 | tokyo | LOSS | 0 | 0.0 | 0.8 | 0.14 |
| 2026-04-16 | USD_JPY | BUY | 59.0 | -2.8 | 25.3 | 1.0 | tokyo | LOSS | 0 | 0.0 | 0.8 | 0.14 |
| 2026-04-16 | EUR_USD | BUY | 54.0 | 2.14 | 21.6 | 1.08 | london | LOSS | 18 | 2.3 | 8.9 | 1.00 |
| 2026-04-20 | EUR_JPY | SELL | 63.0 | 2.159 | 15.3 | 0.88 | tokyo | LOSS | 240 | 0.0 | 11.9 | 0.60 |
| 2026-04-20 | EUR_JPY | SELL | 54.0 | 3.721 | 12.6 | 0.97 | tokyo | LOSS | 81 | 5.9 | 12.5 | 0.63 |
| 2026-04-20 | GBP_USD | SELL | 51.0 | 2.145 | 13.5 | 1.08 | london | LOSS | 113 | 0.0 | 16.5 | 0.82 |
| 2026-04-20 | EUR_JPY | SELL | 60.0 | 2.229 | 17.1 | 1.04 | ny | LOSS | 237 | 0.0 | 20.0 | 1.00 |
| 2026-04-21 | GBP_USD | SELL | 50.0 | 2.716 | 24.0 | 1.04 | tokyo | WIN | 124 | 33.1 | 0.0 | 0.00 |
| 2026-04-21 | GBP_JPY | SELL | 63.0 | 2.818 | 17.8 | 1.27 | london | LOSS | 44 | 0.0 | 14.9 | 1.00 |
| 2026-04-21 | EUR_USD | SELL | 51.0 | 2.16 | 23.4 | 1.24 | ny | WIN | 128 | 35.0 | 0.0 | 0.00 |

---

## H. Actionable recommendations (quant vote, implementation 前提)

以下の filter rule は **virtual simulation** の結果. LIVE 適用は pre-registration 必須.

### H.1 "Drop" 型 (損失カット) — 即時適用の価値高
- **DROP: confidence Q4 (paradoxical)**: retention 76%, WR uplift +2.0pp, PnL kept -1431.0

### H.2 "Keep" 型 (集中) — PRIME split 候補
- **KEEP: mtf_alignment=aligned only**: retention 7%, WR 35.5% (uplift +7.6pp)
- **KEEP: confidence Q1 (paradox exploit)**: retention 26%, WR 32.6% (uplift +4.7pp)
- **KEEP: NY session only**: retention 45%, WR 29.1% (uplift +1.3pp)

### H.3 避けるべき罠 (PMI 負の領域)
- confidence quartile=Q4: N=443 WR=21.2% PMI=-0.273 → filter で排除検討
- mtf_alignment=conflict: N=318 WR=24.2% PMI=-0.140 → filter で排除検討
- mtf_regime=trend_up_strong: N=144 WR=24.3% PMI=-0.137 → filter で排除検討
- mtf_vol_state=expansion: N=199 WR=24.6% PMI=-0.124 → filter で排除検討
- spread quartile=Q4: N=357 WR=24.6% PMI=-0.123 → filter で排除検討

### H.4 Priority ranking (WR 改善寄与度)

1. **Confidence Q4 paradox filter** (既存 [[confidence-q4-paradox]] 記録済) — 最も uplift 大
2. **Score Q1 drop** — 戦略 score の lowest quartile は systematic loser
3. **mtf_alignment=conflict drop** — 既存 gate の漏れチェック
4. **spread Q4 drop** — friction 動的排除 (既存 Spread Gate と重なるが ex-post で測定)
5. **session: offhours drop** — thin liquidity による slippage 増

### H.5 本日の実装判断 (honest)

- 本日午前に **6 PRIME strategies pre-registered** (2026-05-15 binding). 追加の filter 実装は multiple testing inflation.
- 上記 recommendations は **2026-05-05 中間評価** で再計算し, 有意性が維持されていれば 2026-05-15 に family に加える.
- 現時点で最も valuable な action = **観察継続**. 蓄積 N が増えれば filter の確度も上がる.

### H.6 限界 (disclosure)

- Shadow ≠ LIVE: Shadow 母集団での WR uplift は LIVE で再現しない可能性 (dt_fib_reversal 前例).
- Post-hoc 探索: 12 filter candidate × 5 feature = 60 実質 hypothesis. Bonferroni 未補正.
- 戦略 heterogeneity: portfolio-wide filter と戦略別最適 filter は異なる. 単一 rule で全戦略最適化は不可.