# Edge Design Audit — Inventory

自動生成: `python3 tools/build_edge_audit_inventory.py`

## Tier 1 (LIVE)

| # | Strategy | Pairs | Source Tier |
|---|---|---|---|
| 1 | trendline_sweep | ALL | elite_live |
| 2 | doji_breakout | GBP_USD, USD_JPY | pair_promoted |
| 3 | ema200_trend_reversal | USD_JPY | pair_promoted |
| 4 | squeeze_release_momentum | EUR_USD | pair_promoted |
| 5 | streak_reversal | USD_JPY | pair_promoted |
| 6 | vol_momentum_scalp | EUR_JPY | pair_promoted |
| 7 | wick_imbalance_reversion | GBP_USD | pair_promoted |
| 8 | xs_momentum | EUR_USD, GBP_USD | pair_promoted |

## Tier 2 (Shadow)

| # | Strategy | Pairs | Source Tier |
|---|---|---|---|
| 1 | adx_trend_continuation | ALL | phase0_shadow |
| 2 | alpha_atr_regime_break | ALL | phase0_shadow |
| 3 | alpha_intraday_seasonality | ALL | phase0_shadow |
| 4 | alpha_wick_imbalance | ALL | phase0_shadow |
| 5 | asia_range_fade_v1 | ALL | phase0_shadow |
| 6 | bb_rsi | ALL | phase0_shadow |
| 7 | confluence_scalp | ALL | phase0_shadow |
| 8 | cpd_divergence | ALL | phase0_shadow |
| 9 | dt_sr_channel | ALL | phase0_shadow |
| 10 | ema200_reversal | ALL | phase0_shadow |
| 11 | ema_ribbon | ALL | phase0_shadow |
| 12 | fib | ALL | phase0_shadow |
| 13 | gold_pips | ALL | phase0_shadow |
| 14 | gold_trend_momentum | ALL | phase0_shadow |
| 15 | gold_vol_break | ALL | phase0_shadow |
| 16 | hmm_regime_filter | ALL | phase0_shadow |
| 17 | htf_false_breakout | ALL | phase0_shadow |
| 18 | jpy_basket_trend | ALL | phase0_shadow |
| 19 | keltner_squeeze_breakout | ALL | phase0_shadow |
| 20 | london_breakout | ALL | phase0_shadow |
| 21 | london_ny_swing | ALL | phase0_shadow |
| 22 | london_session_breakout | ALL | phase0_shadow |
| 23 | london_shrapnel | ALL | phase0_shadow |
| 24 | macdh | ALL | phase0_shadow |
| 25 | mqe_gbpusd_fix | ALL | phase0_shadow |
| 26 | mtf_confluence | ALL | phase0_shadow |
| 27 | ofi_mr | ALL | phase0_shadow |
| 28 | pullback_to_liquidity_v1 | ALL | phase0_shadow |
| 29 | rsk_gbpjpy_reversion | ALL | phase0_shadow |
| 30 | session_vol_expansion | ALL | phase0_shadow |
| 31 | squeeze | ALL | phase0_shadow |
| 32 | sr_anti_hunt_bounce | ALL | phase0_shadow |
| 33 | sr_liquidity_grab | ALL | phase0_shadow |
| 34 | stoch_pullback | ALL | phase0_shadow |
| 35 | three_bar_reversal | ALL | phase0_shadow |
| 36 | tokyo_nakane_momentum | ALL | phase0_shadow |
| 37 | tokyo_range_breakout | ALL | phase0_shadow |
| 38 | turtle_s2_donchian | ALL | phase0_shadow |
| 39 | turtle_soup | ALL | phase0_shadow |
| 40 | tvsm | ALL | phase0_shadow |
| 41 | vbp | ALL | phase0_shadow |
| 42 | vdr_jpy | ALL | phase0_shadow |
| 43 | vol_momentum | ALL | phase0_shadow |
| 44 | vol_surge | ALL | phase0_shadow |
| 45 | vsg_jpy_reversal | ALL | phase0_shadow |

## Tier 3 (FORCE_DEMOTED)

| # | Strategy | Pairs | Source Tier |
|---|---|---|---|
| 1 | atr_regime_break | ALL | force_demoted |
| 2 | donchian_momentum_breakout | ALL | force_demoted |
| 3 | dt_bb_rsi_mr | ALL | force_demoted |
| 4 | ema_cross | ALL | force_demoted |
| 5 | ema_pullback | ALL | force_demoted |
| 6 | ema_ribbon_ride | ALL | force_demoted |
| 7 | ema_trend_scalp | ALL | force_demoted |
| 8 | engulfing_bb | ALL | force_demoted |
| 9 | fib_reversal | ALL | force_demoted |
| 10 | inducement_ob | ALL | force_demoted |
| 11 | intraday_seasonality | ALL | force_demoted |
| 12 | lin_reg_channel | ALL | force_demoted |
| 13 | macdh_reversal | ALL | force_demoted |
| 14 | orb_trap | ALL | force_demoted |
| 15 | post_news_vol | ALL | force_demoted |
| 16 | sr_break_retest | ALL | force_demoted |
| 17 | sr_channel_reversal | ALL | force_demoted |
| 18 | sr_fib_confluence | ALL | force_demoted |
| 19 | stoch_trend_pullback | ALL | force_demoted |
| 20 | trend_rebound | ALL | force_demoted |
| 21 | v_reversal | ALL | force_demoted |
| 22 | vwap_mean_reversion | ALL | force_demoted |

## Tier 4 (SCALP_SENTINEL)

| # | Strategy | Pairs | Source Tier |
|---|---|---|---|
| 1 | bb_rsi_ema_aligned | ALL | scalp_sentinel |
| 2 | bb_rsi_reversion | ALL | scalp_sentinel |
| 3 | ma_mr_hybrid | ALL | scalp_sentinel |
| 4 | ma_regime_switch | ALL | scalp_sentinel |
| 5 | ma_trend_perfect | ALL | scalp_sentinel |
| 6 | mtf_counter_trend_scalp | ALL | scalp_sentinel |
| 7 | mtf_regime_range_cascade_scalp | ALL | scalp_sentinel |
| 8 | mtf_regime_trend_cascade_scalp | ALL | scalp_sentinel |
| 9 | mtf_trend_follow_scalp | ALL | scalp_sentinel |
| 10 | vol_surge_detector | ALL | scalp_sentinel |
