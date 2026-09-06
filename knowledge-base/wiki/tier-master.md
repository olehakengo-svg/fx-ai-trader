# Tier Master — 戦略分類マスタ

**自動生成**: `python3 tools/tier_integrity_check.py --write`
**最終更新**: 2026-09-06 09:30 UTC
**Source of Truth**: `modules/demo_trader.py`

---

## A. OANDA通過戦略（実弾転送される）

### A-1. ELITE_LIVE（0戦略 — 全ペア自動通過）

| # | 戦略名 | 365d BT JPY EV | EUR EV | GBP EV |
|---|---|---|---|---|

### A-2. PAIR_PROMOTED（21エントリ — 指定ペアのみ通過）

| # | 戦略名 | ペア | 365d BT EV |
|---|---|---|---|
| 1 | bb_squeeze_breakout | EUR_USD | — |
| 2 | doji_breakout | GBP_USD | +0.694 |
| 3 | doji_breakout | USD_JPY | +0.339 |
| 4 | donchian_momentum_breakout | NZD_JPY | — |
| 5 | donchian_momentum_breakout | NZD_USD | — |
| 6 | dt_bb_rsi_mr | USD_JPY | — |
| 7 | ema200_trend_reversal | USD_JPY | — |
| 8 | mqe_gbpusd_fix | GBP_USD | — |
| 9 | pivot_detector_v2_5 | EUR_USD | — |
| 10 | price_shock_rev_aud_jpy_h1_long | AUD_JPY | — |
| 11 | price_shock_rev_eur_aud_h1_long | EUR_AUD | — |
| 12 | price_shock_rev_eur_gbp_h1_long | EUR_GBP | — |
| 13 | price_shock_rev_nzd_jpy_h1_long | NZD_JPY | — |
| 14 | price_shock_rev_usd_cad_h1_long | USD_CAD | — |
| 15 | squeeze_release_momentum | EUR_USD | — |
| 16 | vol_momentum_scalp | EUR_JPY | — |
| 17 | vsg_jpy_reversal | EUR_JPY | — |
| 18 | weekend_gap_fade | AUD_USD | — |
| 19 | weekend_gap_fade | EUR_USD | — |
| 20 | weekend_gap_fade | USD_JPY | — |
| 21 | xs_momentum_rsi | USD_JPY | — |

## B. Shadow戦略（OANDA非通過 — デモのみ記録）

### B-1. FORCE_DEMOTED（20戦略 — 全ペア強制Shadow）

| # | 戦略名 | 365d BT JPY EV | EUR EV | GBP EV |
|---|---|---|---|---|
| 1 | atr_regime_break | — | — | — |
| 2 | ema_cross | — | — | — |
| 3 | ema_pullback | — | — | — |
| 4 | ema_ribbon_ride | — | — | — |
| 5 | ema_trend_scalp | — | — | — |
| 6 | engulfing_bb | — | — | — |
| 7 | fib_reversal | — | — | — |
| 8 | inducement_ob | — | — | — |
| 9 | intraday_seasonality | — | — | — |
| 10 | lin_reg_channel | — | — | — |
| 11 | macdh_reversal | — | — | — |
| 12 | ob_retest | — | — | — |
| 13 | orb_trap | — | — | — |
| 14 | post_news_vol | +1.119 | +0.844 | +1.302 |
| 15 | sr_break_retest | — | — | — |
| 16 | sr_channel_reversal | — | — | — |
| 17 | stoch_trend_pullback | — | — | — |
| 18 | trend_rebound | — | — | — |
| 19 | v_reversal | — | — | — |
| 20 | vwap_mean_reversion | +1.155 | +0.827 | +1.087 |

### B-2. SCALP_SENTINEL（8戦略 — Scalp最小ロットShadow）

| # | 戦略名 |
|---|---|
| 1 | bb_rsi_reversion |
| 2 | ma_regime_switch |
| 3 | ma_trend_perfect |
| 4 | mtf_counter_trend_scalp |
| 5 | mtf_regime_range_cascade_scalp |
| 6 | mtf_regime_trend_cascade_scalp |
| 7 | mtf_trend_follow_scalp |
| 8 | vol_surge_detector |

### B-3. UNIVERSAL_SENTINEL（22戦略 — 全モードSentinel）

| # | 戦略名 | PP経由OANDA通過ペア |
|---|---|---|
| 1 | doji_breakout | GBP_USD, USD_JPY |
| 2 | dt_fib_reversal | なし |
| 3 | dt_sr_channel_reversal | なし |
| 4 | eurgbp_daily_mr | なし |
| 5 | gotobi_fix | なし |
| 6 | kalman_d7_ema75_break | なし |
| 7 | kalman_d7_po_dn_flip | なし |
| 8 | kalman_d7_trail_atr | なし |
| 9 | liquidity_sweep | なし |
| 10 | london_close_reversal | なし |
| 11 | london_close_reversal_v2 | なし |
| 12 | macd_rsi_pullback | なし |
| 13 | pd_eurjpy_h20_bbpb3_sell | なし |
| 14 | post_news_vol | なし |
| 15 | price_shock_reversion | なし |
| 16 | session_time_bias | なし |
| 17 | squeeze_release_momentum | EUR_USD |
| 18 | sr_weighted_bounce | なし |
| 19 | sr_weighted_break | なし |
| 20 | vix_carry_unwind | なし |
| 21 | vol_spike_mr | なし |
| 22 | weekend_gap_fade | AUD_USD, EUR_USD, USD_JPY |

### B-4. PAIR_DEMOTED（41エントリ — 特定ペアのみ強制Shadow）

| # | 戦略名 | ペア |
|---|---|---|
| 1 | bb_rsi_reversion | EUR_JPY |
| 2 | bb_rsi_reversion | EUR_USD |
| 3 | bb_rsi_reversion | GBP_USD |
| 4 | bb_rsi_reversion | USD_JPY |
| 5 | bb_squeeze_breakout | EUR_GBP |
| 6 | bb_squeeze_breakout | EUR_JPY |
| 7 | bb_squeeze_breakout | GBP_JPY |
| 8 | bb_squeeze_breakout | GBP_USD |
| 9 | bb_squeeze_breakout | USD_JPY |
| 10 | donchian_momentum_breakout | AUD_JPY |
| 11 | donchian_momentum_breakout | AUD_USD |
| 12 | donchian_momentum_breakout | EUR_AUD |
| 13 | donchian_momentum_breakout | EUR_USD |
| 14 | donchian_momentum_breakout | USD_CAD |
| 15 | donchian_momentum_breakout | USD_JPY |
| 16 | dt_bb_rsi_mr | EUR_USD |
| 17 | ema_cross | USD_JPY |
| 18 | ema_trend_scalp | EUR_USD |
| 19 | ema_trend_scalp | USD_JPY |
| 20 | engulfing_bb | EUR_USD |
| 21 | engulfing_bb | USD_JPY |
| 22 | gbp_deep_pullback | GBP_USD |
| 23 | london_fix_reversal | USD_JPY |
| 24 | macdh_reversal | GBP_USD |
| 25 | post_news_vol | USD_JPY |
| 26 | sr_channel_reversal | EUR_USD |
| 27 | sr_channel_reversal | USD_JPY |
| 28 | stoch_trend_pullback | USD_JPY |
| 29 | streak_reversal | USD_JPY |
| 30 | trendline_sweep | EUR_GBP |
| 31 | trendline_sweep | EUR_USD |
| 32 | trendline_sweep | GBP_USD |
| 33 | v_reversal | USD_JPY |
| 34 | vix_carry_unwind | USD_JPY |
| 35 | vol_surge_detector | EUR_JPY |
| 36 | vol_surge_detector | USD_JPY |
| 37 | vwap_mean_reversion | GBP_USD |
| 38 | wick_imbalance_reversion | GBP_USD |
| 39 | xs_momentum | EUR_USD |
| 40 | xs_momentum | GBP_USD |
| 41 | xs_momentum | USD_JPY |

### B-5. Phase B-1 Shadow candidate pairs

| # | 戦略名 | ペア | 制約 |
|---|---|---|---|
| 1 | price_shock_reversion | USD_CAD | Tier 1 #3; Phase B Wave 1 candidate; Live promotion disabled in this task |
| 2 | price_shock_reversion | USD_CHF | Tier 3 WATCH; Phase B Wave 1 candidate; Live promotion disabled in this task |
| 3 | price_shock_reversion | AUD_JPY | Shadow candidate; Live promotion disabled in this task |
| 4 | price_shock_reversion | NZD_JPY | Shadow candidate; Live promotion disabled in this task |
| 5 | price_shock_reversion | AUD_USD | Shadow candidate; Live promotion disabled in this task |
| 6 | price_shock_reversion | NZD_USD | Shadow candidate; Live promotion disabled in this task |
| 7 | price_shock_reversion | EUR_AUD | Shadow candidate; Live promotion disabled in this task |

### B-5. Phase0 Shadow Gate（42戦略 — 自動Shadow）

| # | 戦略名 | mode | 理由 |
|---|---|---|---|
| 1 | adx_trend_continuation | daytrade | PP/EL未指定 → 自動Shadow |
| 2 | asia_range_fade_v1 | daytrade | PP/EL未指定 → 自動Shadow |
| 3 | bb_rsi_ema_aligned | scalp | PP/EL未指定 → 自動Shadow |
| 4 | confluence_scalp | scalp | PP/EL未指定 → 自動Shadow |
| 5 | cpd_divergence | daytrade | PP/EL未指定 → 自動Shadow |
| 6 | dual_sr_bounce | inline | PP/EL未指定 → 自動Shadow |
| 7 | gbp_deep_pullback | daytrade | PAIR_DEMOTED: GBP_USD |
| 8 | gold_pips_hunter | scalp | PP/EL未指定 → 自動Shadow |
| 9 | gold_trend_momentum | daytrade | PP/EL未指定 → 自動Shadow |
| 10 | gold_vol_break | daytrade | PP/EL未指定 → 自動Shadow |
| 11 | hmm_regime_filter | daytrade | PP/EL未指定 → 自動Shadow |
| 12 | htf_false_breakout | daytrade | PP/EL未指定 → 自動Shadow |
| 13 | hull_donchian_fade | daytrade | PP/EL未指定 → 自動Shadow |
| 14 | jpy_basket_trend | daytrade | PP/EL未指定 → 自動Shadow |
| 15 | keltner_squeeze_breakout | hourly | PP/EL未指定 → 自動Shadow |
| 16 | london_breakout | scalp | PP/EL未指定 → 自動Shadow |
| 17 | london_fix_reversal | daytrade | PAIR_DEMOTED: USD_JPY |
| 18 | london_ny_swing | daytrade | PP/EL未指定 → 自動Shadow |
| 19 | london_session_breakout | daytrade | PP/EL未指定 → 自動Shadow |
| 20 | london_shrapnel | scalp | PP/EL未指定 → 自動Shadow |
| 21 | ma_mr_hybrid | scalp | PP/EL未指定 → 自動Shadow |
| 22 | mtf_reversal_confluence | scalp | PP/EL未指定 → 自動Shadow |
| 23 | ny_close_reversal | inline | PP/EL未指定 → 自動Shadow |
| 24 | ob_retest_h1 | hourly | PP/EL未指定 → 自動Shadow |
| 25 | pullback_to_liquidity_v1 | daytrade | PP/EL未指定 → 自動Shadow |
| 26 | rsk_gbpjpy_reversion | daytrade | PP/EL未指定 → 自動Shadow |
| 27 | session_vol_expansion | scalp | PP/EL未指定 → 自動Shadow |
| 28 | sr_anti_hunt_bounce | daytrade | PP/EL未指定 → 自動Shadow |
| 29 | sr_fib_confluence | daytrade | PP/EL未指定 → 自動Shadow |
| 30 | sr_liquidity_grab | daytrade | PP/EL未指定 → 自動Shadow |
| 31 | streak_reversal | inline | PAIR_DEMOTED: USD_JPY |
| 32 | sweep_reversion_eurgbp_late | daytrade | PP/EL未指定 → 自動Shadow |
| 33 | three_bar_reversal | scalp | PP/EL未指定 → 自動Shadow |
| 34 | tokyo_nakane_momentum | daytrade | PP/EL未指定 → 自動Shadow |
| 35 | tokyo_range_breakout_up | daytrade | PP/EL未指定 → 自動Shadow |
| 36 | trendline_sweep | daytrade | PAIR_DEMOTED: EUR_GBP, EUR_USD, GBP_USD |
| 37 | turtle_soup | daytrade | PP/EL未指定 → 自動Shadow |
| 38 | usdjpy_carry_dip_accumulator | hourly | PP/EL未指定 → 自動Shadow |
| 39 | vdr_jpy | daytrade | PP/EL未指定 → 自動Shadow |
| 40 | wick_imbalance_reversion | daytrade | PAIR_DEMOTED: GBP_USD |
| 41 | xs_momentum | daytrade | PAIR_DEMOTED: EUR_USD, GBP_USD, USD_JPY |
| 42 | zz_pivot_v60_sr | daytrade | PP/EL未指定 → 自動Shadow |

## C. 整合性チェック結果

### ⚠️ WARN（2件）
- QUICK_HARVEST_EXEMPT (hull_donchian_fade, EUR_USD) not in ELITE/PAIR_PROMOTED
- No strategy file found for 'ob_retest'

### ℹ️ INFO（14件）
- Legacy dead inline 'bb_bounce' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'divergence' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'donchian' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'dual_sr_breakout' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'ema_trend' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'fib_pullback' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'hs_neckbreak' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'ihs_neckbreak' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'momentum' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'ob_retest' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'reg_channel' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'sr_bounce' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'strong_sr_breakout' assigned in app.py — no production firing in 30+ days. Candidate for removal.
- Legacy dead inline 'tokyo_bb' assigned in app.py — no production firing in 30+ days. Candidate for removal.
