# Tier Master — 戦略分類マスタ

**自動生成**: `python3 tools/tier_integrity_check.py --write`
**最終更新**: 2026-05-18 05:39 UTC
**Source of Truth**: `modules/demo_trader.py`

---

## A. OANDA通過戦略（実弾転送される）

### A-1. ELITE_LIVE（1戦略 — 全ペア自動通過）

| # | 戦略名 | 365d BT JPY EV | EUR EV | GBP EV |
|---|---|---|---|---|
| 1 | trendline_sweep | — | +0.574 | +0.838 |

### A-2. PAIR_PROMOTED（18エントリ — 指定ペアのみ通過）

| # | 戦略名 | ペア | 365d BT EV |
|---|---|---|---|
| 1 | bb_squeeze_breakout | EUR_USD | — |
| 2 | doji_breakout | GBP_USD | +0.694 |
| 3 | doji_breakout | USD_JPY | +0.339 |
| 4 | dt_bb_rsi_mr | USD_JPY | — |
| 5 | dt_sr_channel_reversal | EUR_JPY | — |
| 6 | ema200_trend_reversal | USD_JPY | — |
| 7 | mqe_gbpusd_fix | GBP_USD | — |
| 8 | session_time_bias | EUR_USD | +0.251 |
| 9 | squeeze_release_momentum | EUR_USD | — |
| 10 | sr_fib_confluence | GBP_USD | — |
| 11 | trend_rebound | USD_JPY | — |
| 12 | vix_carry_unwind | USD_JPY | +0.506 |
| 13 | vol_momentum_scalp | EUR_JPY | — |
| 14 | vsg_jpy_reversal | EUR_JPY | — |
| 15 | wick_imbalance_reversion | GBP_USD | — |
| 16 | xs_momentum | EUR_USD | +0.126 |
| 17 | xs_momentum | GBP_USD | -0.013 |
| 18 | xs_momentum_rsi | USD_JPY | — |

## B. Shadow戦略（OANDA非通過 — デモのみ記録）

### B-1. FORCE_DEMOTED（24戦略 — 全ペア強制Shadow）

| # | 戦略名 | 365d BT JPY EV | EUR EV | GBP EV |
|---|---|---|---|---|
| 1 | atr_regime_break | — | — | — |
| 2 | donchian_momentum_breakout | — | — | — |
| 3 | ema_cross | — | — | — |
| 4 | ema_pullback | — | — | — |
| 5 | ema_ribbon_ride | — | — | — |
| 6 | ema_trend_scalp | — | — | — |
| 7 | engulfing_bb | — | — | — |
| 8 | fib_reversal | — | — | — |
| 9 | inducement_ob | — | — | — |
| 10 | intraday_seasonality | — | — | — |
| 11 | lin_reg_channel | — | — | — |
| 12 | macdh_reversal | — | — | — |
| 13 | orb_trap | — | — | — |
| 14 | post_news_vol | +1.119 | +0.844 | +1.302 |
| 15 | price_shock_rev_aud_jpy_h1_long | — | — | — |
| 16 | price_shock_rev_eur_aud_h1_long | — | — | — |
| 17 | price_shock_rev_eur_gbp_h1_long | — | — | — |
| 18 | price_shock_rev_nzd_jpy_h1_long | — | — | — |
| 19 | price_shock_rev_usd_cad_h1_long | — | — | — |
| 20 | sr_break_retest | — | — | — |
| 21 | sr_channel_reversal | — | — | — |
| 22 | stoch_trend_pullback | — | — | — |
| 23 | v_reversal | — | — | — |
| 24 | vwap_mean_reversion | +1.155 | +0.827 | +1.087 |

### B-2. SCALP_SENTINEL（10戦略 — Scalp最小ロットShadow）

| # | 戦略名 |
|---|---|
| 1 | bb_rsi_ema_aligned |
| 2 | bb_rsi_reversion |
| 3 | ma_mr_hybrid |
| 4 | ma_regime_switch |
| 5 | ma_trend_perfect |
| 6 | mtf_counter_trend_scalp |
| 7 | mtf_regime_range_cascade_scalp |
| 8 | mtf_regime_trend_cascade_scalp |
| 9 | mtf_trend_follow_scalp |
| 10 | vol_surge_detector |

### B-3. UNIVERSAL_SENTINEL（18戦略 — 全モードSentinel）

| # | 戦略名 | PP経由OANDA通過ペア |
|---|---|---|
| 1 | doji_breakout | GBP_USD, USD_JPY |
| 2 | dt_fib_reversal | なし |
| 3 | dt_sr_channel_reversal | EUR_JPY |
| 4 | eurgbp_daily_mr | なし |
| 5 | gotobi_fix | なし |
| 6 | liquidity_sweep | なし |
| 7 | london_close_reversal | なし |
| 8 | london_close_reversal_v2 | なし |
| 9 | macd_rsi_pullback | なし |
| 10 | pd_eurjpy_h20_bbpb3_sell | なし |
| 11 | post_news_vol | なし |
| 12 | price_shock_reversion | なし |
| 13 | session_time_bias | EUR_USD |
| 14 | squeeze_release_momentum | EUR_USD |
| 15 | sr_weighted_bounce | なし |
| 16 | sr_weighted_break | なし |
| 17 | vix_carry_unwind | USD_JPY |
| 18 | vol_spike_mr | なし |

### B-4. PAIR_DEMOTED（30エントリ — 特定ペアのみ強制Shadow）

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
| 10 | dt_bb_rsi_mr | EUR_USD |
| 11 | ema_cross | USD_JPY |
| 12 | ema_trend_scalp | EUR_USD |
| 13 | ema_trend_scalp | USD_JPY |
| 14 | engulfing_bb | EUR_USD |
| 15 | engulfing_bb | USD_JPY |
| 16 | gbp_deep_pullback | GBP_USD |
| 17 | london_fix_reversal | USD_JPY |
| 18 | macdh_reversal | GBP_USD |
| 19 | post_news_vol | USD_JPY |
| 20 | session_time_bias | GBP_USD |
| 21 | sr_channel_reversal | EUR_USD |
| 22 | sr_channel_reversal | USD_JPY |
| 23 | stoch_trend_pullback | USD_JPY |
| 24 | streak_reversal | USD_JPY |
| 25 | trend_rebound | EUR_USD |
| 26 | v_reversal | USD_JPY |
| 27 | vol_surge_detector | EUR_JPY |
| 28 | vol_surge_detector | USD_JPY |
| 29 | vwap_mean_reversion | GBP_USD |
| 30 | xs_momentum | USD_JPY |

### B-5. Phase B-1 Shadow candidate pairs

| # | 戦略名 | ペア | 制約 |
|---|---|---|---|
| 1 | price_shock_reversion | AUD_JPY | Shadow candidate; Live promotion disabled in this task |
| 2 | price_shock_reversion | NZD_JPY | Shadow candidate; Live promotion disabled in this task |
| 3 | price_shock_reversion | AUD_USD | Shadow candidate; Live promotion disabled in this task |
| 4 | price_shock_reversion | NZD_USD | Shadow candidate; Live promotion disabled in this task |
| 5 | price_shock_reversion | EUR_AUD | Shadow candidate; Live promotion disabled in this task |

### B-5. Phase0 Shadow Gate（32戦略 — 自動Shadow）

| # | 戦略名 | mode | 理由 |
|---|---|---|---|
| 1 | adx_trend_continuation | daytrade | PP/EL未指定 → 自動Shadow |
| 2 | asia_range_fade_v1 | daytrade | PP/EL未指定 → 自動Shadow |
| 3 | confluence_scalp | scalp | PP/EL未指定 → 自動Shadow |
| 4 | cpd_divergence | daytrade | PP/EL未指定 → 自動Shadow |
| 5 | dual_sr_bounce | inline | PP/EL未指定 → 自動Shadow |
| 6 | gbp_deep_pullback | daytrade | PAIR_DEMOTED: GBP_USD |
| 7 | gold_pips_hunter | scalp | PP/EL未指定 → 自動Shadow |
| 8 | gold_trend_momentum | daytrade | PP/EL未指定 → 自動Shadow |
| 9 | gold_vol_break | daytrade | PP/EL未指定 → 自動Shadow |
| 10 | hmm_regime_filter | daytrade | PP/EL未指定 → 自動Shadow |
| 11 | htf_false_breakout | daytrade | PP/EL未指定 → 自動Shadow |
| 12 | jpy_basket_trend | daytrade | PP/EL未指定 → 自動Shadow |
| 13 | keltner_squeeze_breakout | hourly | PP/EL未指定 → 自動Shadow |
| 14 | london_breakout | scalp | PP/EL未指定 → 自動Shadow |
| 15 | london_fix_reversal | daytrade | PAIR_DEMOTED: USD_JPY |
| 16 | london_ny_swing | daytrade | PP/EL未指定 → 自動Shadow |
| 17 | london_session_breakout | daytrade | PP/EL未指定 → 自動Shadow |
| 18 | london_shrapnel | scalp | PP/EL未指定 → 自動Shadow |
| 19 | mtf_reversal_confluence | scalp | PP/EL未指定 → 自動Shadow |
| 20 | ny_close_reversal | inline | PP/EL未指定 → 自動Shadow |
| 21 | ob_retest_h1 | hourly | PP/EL未指定 → 自動Shadow |
| 22 | pullback_to_liquidity_v1 | daytrade | PP/EL未指定 → 自動Shadow |
| 23 | rsk_gbpjpy_reversion | daytrade | PP/EL未指定 → 自動Shadow |
| 24 | session_vol_expansion | scalp | PP/EL未指定 → 自動Shadow |
| 25 | sr_anti_hunt_bounce | daytrade | PP/EL未指定 → 自動Shadow |
| 26 | sr_liquidity_grab | daytrade | PP/EL未指定 → 自動Shadow |
| 27 | streak_reversal | inline | PAIR_DEMOTED: USD_JPY |
| 28 | three_bar_reversal | scalp | PP/EL未指定 → 自動Shadow |
| 29 | tokyo_nakane_momentum | daytrade | PP/EL未指定 → 自動Shadow |
| 30 | tokyo_range_breakout_up | daytrade | PP/EL未指定 → 自動Shadow |
| 31 | turtle_soup | daytrade | PP/EL未指定 → 自動Shadow |
| 32 | vdr_jpy | daytrade | PP/EL未指定 → 自動Shadow |

## C. 整合性チェック結果

✅ **全チェックパス** — FORCE_DEMOTED残存なし、矛盾なし
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
