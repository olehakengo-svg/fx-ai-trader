# Tier Master — 戦略分類マスタ

**自動生成**: `python3 tools/tier_integrity_check.py --write`
**最終更新**: 2026-04-30 08:23 UTC
**Source of Truth**: `modules/demo_trader.py`

---

## A. OANDA通過戦略（実弾転送される）

### A-1. ELITE_LIVE（3戦略 — 全ペア自動通過）

| # | 戦略名 | 365d BT JPY EV | EUR EV | GBP EV |
|---|---|---|---|---|
| 1 | gbp_deep_pullback | — | — | +0.603 |
| 2 | session_time_bias | +0.195 | +0.251 | +0.149 |
| 3 | trendline_sweep | — | +0.574 | +0.838 |

### A-2. PAIR_PROMOTED（16エントリ — 指定ペアのみ通過）

| # | 戦略名 | ペア | 365d BT EV |
|---|---|---|---|
| 1 | bb_squeeze_breakout | USD_JPY | — |
| 2 | doji_breakout | GBP_USD | +0.694 |
| 3 | doji_breakout | USD_JPY | +0.339 |
| 4 | ema200_trend_reversal | USD_JPY | — |
| 5 | squeeze_release_momentum | EUR_USD | — |
| 6 | streak_reversal | USD_JPY | +1.169 |
| 7 | vix_carry_unwind | USD_JPY | +0.506 |
| 8 | vol_momentum_scalp | EUR_JPY | — |
| 9 | vwap_mean_reversion | EUR_JPY | +1.155 |
| 10 | vwap_mean_reversion | EUR_USD | +0.827 |
| 11 | vwap_mean_reversion | GBP_JPY | +1.155 |
| 12 | vwap_mean_reversion | GBP_USD | +1.087 |
| 13 | vwap_mean_reversion | USD_JPY | +1.155 |
| 14 | wick_imbalance_reversion | GBP_USD | — |
| 15 | xs_momentum | EUR_USD | +0.126 |
| 16 | xs_momentum | GBP_USD | -0.013 |

## B. Shadow戦略（OANDA非通過 — デモのみ記録）

### B-1. FORCE_DEMOTED（18戦略 — 全ペア強制Shadow）

| # | 戦略名 | 365d BT JPY EV | EUR EV | GBP EV |
|---|---|---|---|---|
| 1 | atr_regime_break | — | — | — |
| 2 | dt_bb_rsi_mr | — | — | — |
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
| 15 | sr_break_retest | — | — | — |
| 16 | sr_channel_reversal | — | — | — |
| 17 | sr_fib_confluence | — | — | — |
| 18 | stoch_trend_pullback | — | — | — |

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

### B-3. UNIVERSAL_SENTINEL（15戦略 — 全モードSentinel）

| # | 戦略名 | PP経由OANDA通過ペア |
|---|---|---|
| 1 | doji_breakout | GBP_USD, USD_JPY |
| 2 | dt_fib_reversal | なし |
| 3 | dt_sr_channel_reversal | なし |
| 4 | eurgbp_daily_mr | なし |
| 5 | gotobi_fix | なし |
| 6 | liquidity_sweep | なし |
| 7 | london_close_reversal | なし |
| 8 | london_close_reversal_v2 | なし |
| 9 | pd_eurjpy_h20_bbpb3_sell | なし |
| 10 | post_news_vol | なし |
| 11 | squeeze_release_momentum | EUR_USD |
| 12 | trend_rebound | なし |
| 13 | v_reversal | なし |
| 14 | vix_carry_unwind | USD_JPY |
| 15 | vol_spike_mr | なし |

### B-4. PAIR_DEMOTED（21エントリ — 特定ペアのみ強制Shadow）

| # | 戦略名 | ペア |
|---|---|---|
| 1 | bb_rsi_reversion | EUR_JPY |
| 2 | bb_rsi_reversion | EUR_USD |
| 3 | bb_rsi_reversion | GBP_USD |
| 4 | bb_squeeze_breakout | EUR_GBP |
| 5 | bb_squeeze_breakout | EUR_JPY |
| 6 | bb_squeeze_breakout | EUR_USD |
| 7 | bb_squeeze_breakout | GBP_JPY |
| 8 | bb_squeeze_breakout | GBP_USD |
| 9 | dt_bb_rsi_mr | EUR_USD |
| 10 | ema_cross | USD_JPY |
| 11 | ema_trend_scalp | EUR_USD |
| 12 | ema_trend_scalp | USD_JPY |
| 13 | engulfing_bb | EUR_USD |
| 14 | engulfing_bb | USD_JPY |
| 15 | london_fix_reversal | USD_JPY |
| 16 | macdh_reversal | GBP_USD |
| 17 | post_news_vol | USD_JPY |
| 18 | stoch_trend_pullback | USD_JPY |
| 19 | trend_rebound | EUR_USD |
| 20 | vol_surge_detector | EUR_JPY |
| 21 | xs_momentum | USD_JPY |

### B-5. Phase0 Shadow Gate（30戦略 — 自動Shadow）

| # | 戦略名 | mode | 理由 |
|---|---|---|---|
| 1 | adx_trend_continuation | daytrade | PP/EL未指定 → 自動Shadow |
| 2 | asia_range_fade_v1 | daytrade | PP/EL未指定 → 自動Shadow |
| 3 | confluence_scalp | scalp | PP/EL未指定 → 自動Shadow |
| 4 | cpd_divergence | daytrade | PP/EL未指定 → 自動Shadow |
| 5 | dual_sr_bounce | inline | PP/EL未指定 → 自動Shadow |
| 6 | gold_pips_hunter | scalp | PP/EL未指定 → 自動Shadow |
| 7 | gold_trend_momentum | daytrade | PP/EL未指定 → 自動Shadow |
| 8 | gold_vol_break | daytrade | PP/EL未指定 → 自動Shadow |
| 9 | hmm_regime_filter | daytrade | PP/EL未指定 → 自動Shadow |
| 10 | htf_false_breakout | daytrade | PP/EL未指定 → 自動Shadow |
| 11 | jpy_basket_trend | daytrade | PP/EL未指定 → 自動Shadow |
| 12 | london_breakout | scalp | PP/EL未指定 → 自動Shadow |
| 13 | london_fix_reversal | daytrade | PAIR_DEMOTED: USD_JPY |
| 14 | london_ny_swing | daytrade | PP/EL未指定 → 自動Shadow |
| 15 | london_session_breakout | daytrade | PP/EL未指定 → 自動Shadow |
| 16 | london_shrapnel | scalp | PP/EL未指定 → 自動Shadow |
| 17 | mqe_gbpusd_fix | daytrade | PP/EL未指定 → 自動Shadow |
| 18 | mtf_reversal_confluence | scalp | PP/EL未指定 → 自動Shadow |
| 19 | ny_close_reversal | inline | PP/EL未指定 → 自動Shadow |
| 20 | pullback_to_liquidity_v1 | daytrade | PP/EL未指定 → 自動Shadow |
| 21 | rsk_gbpjpy_reversion | daytrade | PP/EL未指定 → 自動Shadow |
| 22 | session_vol_expansion | scalp | PP/EL未指定 → 自動Shadow |
| 23 | sr_anti_hunt_bounce | daytrade | PP/EL未指定 → 自動Shadow |
| 24 | sr_liquidity_grab | daytrade | PP/EL未指定 → 自動Shadow |
| 25 | three_bar_reversal | scalp | PP/EL未指定 → 自動Shadow |
| 26 | tokyo_nakane_momentum | daytrade | PP/EL未指定 → 自動Shadow |
| 27 | tokyo_range_breakout_up | daytrade | PP/EL未指定 → 自動Shadow |
| 28 | turtle_soup | daytrade | PP/EL未指定 → 自動Shadow |
| 29 | vdr_jpy | daytrade | PP/EL未指定 → 自動Shadow |
| 30 | vsg_jpy_reversal | daytrade | PP/EL未指定 → 自動Shadow |

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
