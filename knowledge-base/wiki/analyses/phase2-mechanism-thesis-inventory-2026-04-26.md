# Phase 2: 全戦略 Mechanism Thesis 棚卸し (2026-04-26)

> **edge-reset Phase 2** ([[edge-reset-direction-2026-04-26]]) の実装. 既存 60 戦略 (scalp 21 + daytrade 39) の **mechanism thesis** を体系整理.
> **目的**: 「edge を作る」前に、既存戦略の **物理仮説 (mechanism)** が現市場で
> 機能する根拠があるかを 1 戦略ずつ検証.「無 mechanism = 削除候補」.

## 0. 評価軸 (4 軸)

各戦略について以下を判定:

| 軸 | 内容 |
|---|---|
| **Mechanism** | 物理仮説の有無 (= 「なぜ勝てるか」の理論) |
| **Live evidence** | 本日までの Live trade での EV 観察 (post-cutoff 2026-04-08〜) |
| **BT evidence** | 365日 BT での EV 観察 (本日 14 BT 結果含む) |
| **Verdict** | KEEP (条件付き) / DEAD / NO_MECHANISM |

## 1. ELITE_LIVE 3 戦略 (DT 幹候補)

| 戦略 | Mechanism | BT | Live | Verdict |
|---|---|---|---|---|
| **gbp_deep_pullback** | GBP cable 系 trend で深い押し → 大口 buy back | +1.06 (GBP) | N=1 (4/24 patch 後発火待ち) | KEEP (mechanism 強, Mon 観測) |
| **session_time_bias** | session 切替時の autocorrelation (Tokyo close で trend 反転) | +0.58 (JPY) | N=0 (発火待ち) | KEEP (Live 観測必須) |
| **trendline_sweep** | trend line break 後のリテスト (流動性 hunt) | +0.60 (GBP) | N=3 (4/24 まで) | KEEP (mechanism 中, Live 不足) |

## 2. PAIR_PROMOTED 18 戦略×PAIR

| 戦略 | PAIR | Mechanism | BT | Live | Verdict |
|---|---|---|---|---|---|
| **bb_squeeze_breakout** | USD_JPY | BB 収縮→拡大 (Bollinger 1992) | -0.26 (Live 23日) | 365日 BT で ALL_REJECT (本日) | **DEAD** — 5m TF で機能せず |
| doji_breakout | GBP_USD/USD_JPY | Doji 反転パターン | +0.69/+0.34 BT | N不足 | CANDIDATE (Live 観測待ち) |
| ema200_trend_reversal | USD_JPY | EMA200 タッチ + 反発 | — | Grail Sentinel 4/25 deploy | KEEP (Mon 観測) |
| **post_news_vol** | EUR_USD/GBP_USD | News 後 vol 急上昇 trend follow | +0.84/+1.30 | N不足 | CANDIDATE (Live 観測) |
| squeeze_release_momentum | EUR_USD | Squeeze 後 momentum | — | N不足 | UNCERTAIN |
| streak_reversal | USD_JPY | 連続 streak の反転 | +1.17 | N不足 | UNCERTAIN |
| **vix_carry_unwind** | USD_JPY | VIX 上昇時 carry unwind | +0.51 | Grail Sentinel 4/25 | KEEP (Mon 観測) |
| vol_momentum_scalp | EUR_JPY | Vol スパイク momentum | — | N不足 | UNCERTAIN |
| **vwap_mean_reversion** | 5 PAIR | VWAP からの mean revert | +0.83〜+1.16 BT | -4.77 Live → **緊急トリップ済 (4/24)** | **DEAD** (BT-Live 5p 乖離) |
| wick_imbalance_reversion | GBP_USD | Wick 戻り | — | N不足 | UNCERTAIN |
| xs_momentum | EUR_USD/USD_JPY | Cross-section momentum | +0.13/+0.27 | N不足 | UNCERTAIN |

## 3. 本日 Phase 5 BT で DEAD 確定 (Pure Edge 5m)

| 戦略 | Mechanism | BT 結果 | Verdict |
|---|---|---|---|
| Session Handover (S1) | session 切替 swing 抜きヒゲ reject | N=1900 全 REJECT, p=0.0000 損失方向有意 | **DEAD** |
| Vol Compression (S2) | Squeeze→Expansion energy | N=14000 全 REJECT, WR 2-4% | **DEAD** |
| Z-Exhaustion (S3) | |z|>3σ mean revert | N=300 全 REJECT, p=0.006 損失方向有意 | **DEAD** |
| Pure Divergence (S4) | RSI 極限 + price div | N=580 全 REJECT | **DEAD** |
| VA Reversion (S6) | Value Area 外縁回帰 | N=850 全 REJECT | **DEAD** |
| FVG (S8) | 3-bar gap fill | N=880 全 REJECT | **DEAD** |
| Z-Momentum 順張り (D3) | |z|>3σ continuation | TF 上げで悪化 | **DEAD** |
| BB Mean Revert TF Grid (D1) | BB 極限値 (15m〜4h) | 全 TF DEAD | **DEAD** |

## 4. SURVIVOR 兆候 (N不足で Bonferroni 不通, 副次仮説候補)

| 戦略 | 条件 | BT (兆候) | Mechanism 強度 |
|---|---|---|---|
| **S5 VWAP BOTH touch** | EUR/USD × pullback 1.5ATR × VWAP+EMA50_HTF 両方 | N=11 EV+2.75 (2y) | 強 (機関大口物理仮説) |
| **S7 ORB** | GBP系 × London/NY open × vol×2.5 | N=12 EV+5.77 (2y) | 強 (macro flow 物理仮説) |
| **S9 VSA C09** | USD/JPY × vol×3 × body<0.3 | N=35 EV+1.59 (2y) | 中 (Wyckoff 仮説) |
| **D2 EMA Pullback 1h** | EUR/USD × 1h × EMA50 touch | N=36 EV+2.70 | 中 (Moskowitz 2012) |

これら 4 cluster は **Phase 3 (1-3 ヶ月) 研究対象** として継続観察. data-look-blind
追検定が必要 (現状 HARKing 慎重起案フェーズ).

## 5. _FORCE_DEMOTED 17 戦略 (永久停止維持)

| 戦略 | Mechanism (推定) | 削除可能性 |
|---|---|---|
| ema_trend_scalp | EMA pullback (Phase 5 D2 で 5m DEAD 確定) | **削除候補** (TAP-1 中間帯フィルタ汚染) |
| macdh_reversal | MACD-H reversal | **削除推奨** (med MFE=0.00, lookback overfit 確定) |
| fib_reversal | Fibonacci 反発 | **削除推奨** (Live N=269 EV-0.59, 救済 cell 0) |
| sr_channel_reversal | SR 反発 | **削除推奨** (TAP-1 violation) |
| stoch_trend_pullback | Stoch pullback | **削除推奨** (TAP-1) |
| engulfing_bb | 包み足 + BB | **削除推奨** (TAP-2 N-bar pattern) |
| sr_break_retest | SR break retest | UNCERTAIN |
| sr_fib_confluence | SR + Fib | UNCERTAIN |
| dt_bb_rsi_mr | DT BB RSI MR | UNCERTAIN |
| dt_fib_reversal | DT Fib | UNCERTAIN |
| dt_sr_channel_reversal | DT SR | UNCERTAIN |
| ema_cross | EMA crossover | UNCERTAIN |
| ema_pullback | EMA pullback (scalp) | UNCERTAIN |
| ema_ribbon_ride | EMA ribbon | UNCERTAIN |
| inducement_ob | Order block | UNCERTAIN |
| intraday_seasonality | seasonality | UNCERTAIN |
| lin_reg_channel | linear regression | UNCERTAIN |
| orb_trap | ORB trap | UNCERTAIN |
| atr_regime_break | ATR regime | UNCERTAIN |

## 6. _SCALP_SENTINEL / _UNI_SENTINEL (16 戦略, Sentinel 状態)

| 戦略 | 状態 | 物理仮説 |
|---|---|---|
| bb_rsi_reversion | **緊急トリップ (4/25)** | BB+RSI 極端 mean revert (RR=1.17 算数破綻 → 4/25 RR 2.5/3.0 修正) |
| vol_surge_detector | Sentinel | Vol surge detector |
| 他 14 (UNI_SENTINEL) | Sentinel | 大半 UNCERTAIN |

## 7. Phase0 自動 Shadow 19 戦略

PP/EL 未指定で自動 Shadow. mechanism thesis 未確認のため、**Phase 2 でこれら全部
NO_MECHANISM 候補**として Phase 1 統合判定で削除可否決定.

## 8. 集約 Verdict

| Verdict | 数 | アクション |
|---|---|---|
| **KEEP (Mon 観測必須)** | 3 (ELITE) + 5 (PAIR_PROMOTED 強 mechanism) | Live N 蓄積で再判定 |
| **CANDIDATE** | 5 (PAIR_PROMOTED, BT EV+ but N 不足) | Phase 1 holdout (5/7) で再判定 |
| **削除推奨 (DEAD 確定)** | 6 (Phase 5 + macdh + fib + ema_trend) | `_FORCE_DEMOTED` 維持 + 戦略 ID から削除候補 |
| **DEAD** | 8 (Phase 5 全 9 戦略 + S6 + S8) | 同上 |
| **UNCERTAIN** | 30+ | mechanism thesis 不在のため Phase 3 で削除 or 物理仮説起案 |

## 9. Phase 3 (1-3 ヶ月) 研究方向

1. **副次 4 SURVIVOR 兆候 cluster** (S5/S7/S9/D2) を 3-5 年データで N 確保 + 別 pre-reg LOCK
2. **ELITE 3 戦略の Live 発火実証** (4/24 patch 後 N≥10 達成 → BT 実証性確認)
3. **削除推奨 6 戦略の `_FORCE_DEMOTED` 削除** (戦略 ID から完全消去)
4. **UNCERTAIN 30 戦略の mechanism 起案 or 削除**

## 10. メモリ整合性

- [部分的クオンツの罠]: 全戦略について WR/EV/PF 評価 (ただし N 不足で確定不能多数) ⚠️
- [ラベル実測主義]: Live N 蓄積待ち戦略多数 ⚠️
- [成功するまでやる]: UNCERTAIN 戦略は Phase 3 で深掘り継続 ✅
- [Asymmetric Agility Rule 1]: Phase 1/2 は構造修正で Rule 3 適用可 ✅

## 11. 参照
- [[edge-reset-direction-2026-04-26]] (本 Phase 2 の起点)
- [[lesson-label-neutralization-was-symptom-treatment-2026-04-26]] (根本誤り認識)
- [[lesson-pure-edge-5m-structural-failure-2026-04-25]] (Phase 5 結果)
- [[lesson-toxic-anti-patterns-2026-04-25]] (Gate -1 / TAP)
- [[tier-master]] (現状 tier 配置)
