# Tier Master — 戦略分類マスタ

**自動生成**: `python3 tools/tier_integrity_check.py --write`
**最終更新**: 2026-04-21 06:42 UTC
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
| 4 | dt_fib_reversal | GBP_USD | — |
| 5 | post_news_vol | EUR_USD | +0.844 |
| 6 | post_news_vol | GBP_USD | +1.302 |
| 7 | squeeze_release_momentum | EUR_USD | — |
| 8 | vix_carry_unwind | USD_JPY | +0.506 |
| 9 | vol_momentum_scalp | EUR_JPY | — |
| 10 | vwap_mean_reversion | EUR_JPY | +1.155 |
| 11 | vwap_mean_reversion | EUR_USD | +0.827 |
| 12 | vwap_mean_reversion | GBP_JPY | +1.155 |
| 13 | vwap_mean_reversion | GBP_USD | +1.087 |
| 14 | wick_imbalance_reversion | GBP_USD | — |
| 15 | xs_momentum | EUR_USD | +0.126 |
| 16 | xs_momentum | GBP_USD | -0.013 |

## B. Shadow戦略（OANDA非通過 — デモのみ記録）

### B-1. FORCE_DEMOTED（17戦略 — 全ペア強制Shadow）

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
| 14 | sr_break_retest | — | — | — |
| 15 | sr_channel_reversal | — | — | — |
| 16 | sr_fib_confluence | — | — | — |
| 17 | stoch_trend_pullback | — | — | — |

### B-2. SCALP_SENTINEL（2戦略 — Scalp最小ロットShadow）

| # | 戦略名 |
|---|---|
| 1 | bb_rsi_reversion |
| 2 | vol_surge_detector |

### B-3. UNIVERSAL_SENTINEL（14戦略 — 全モードSentinel）

| # | 戦略名 | PP経由OANDA通過ペア |
|---|---|---|
| 1 | doji_breakout | GBP_USD, USD_JPY |
| 2 | dt_fib_reversal | GBP_USD |
| 3 | dt_sr_channel_reversal | なし |
| 4 | ema200_trend_reversal | なし |
| 5 | eurgbp_daily_mr | なし |
| 6 | gotobi_fix | なし |
| 7 | liquidity_sweep | なし |
| 8 | london_close_reversal | なし |
| 9 | post_news_vol | EUR_USD, GBP_USD |
| 10 | squeeze_release_momentum | EUR_USD |
| 11 | trend_rebound | なし |
| 12 | v_reversal | なし |
| 13 | vix_carry_unwind | USD_JPY |
| 14 | vol_spike_mr | なし |

### B-4. PAIR_DEMOTED（23エントリ — 特定ペアのみ強制Shadow）

| # | 戦略名 | ペア |
|---|---|---|
| 1 | bb_rsi_reversion | EUR_JPY |
| 2 | bb_rsi_reversion | EUR_USD |
| 3 | bb_rsi_reversion | GBP_USD |
| 4 | bb_rsi_reversion | USD_JPY |
| 5 | bb_squeeze_breakout | EUR_GBP |
| 6 | bb_squeeze_breakout | EUR_JPY |
| 7 | bb_squeeze_breakout | EUR_USD |
| 8 | bb_squeeze_breakout | GBP_JPY |
| 9 | bb_squeeze_breakout | GBP_USD |
| 10 | dt_bb_rsi_mr | EUR_USD |
| 11 | ema200_trend_reversal | USD_JPY |
| 12 | ema_cross | USD_JPY |
| 13 | ema_trend_scalp | EUR_USD |
| 14 | ema_trend_scalp | USD_JPY |
| 15 | engulfing_bb | EUR_USD |
| 16 | engulfing_bb | USD_JPY |
| 17 | london_fix_reversal | USD_JPY |
| 18 | macdh_reversal | GBP_USD |
| 19 | post_news_vol | USD_JPY |
| 20 | stoch_trend_pullback | USD_JPY |
| 21 | trend_rebound | EUR_USD |
| 22 | vol_surge_detector | EUR_JPY |
| 23 | xs_momentum | USD_JPY |

### B-5. Phase0 Shadow Gate（19戦略 — 自動Shadow）

| # | 戦略名 | mode | 理由 |
|---|---|---|---|
| 1 | adx_trend_continuation | daytrade | PP/EL未指定 → 自動Shadow |
| 2 | confluence_scalp | scalp | PP/EL未指定 → 自動Shadow |
| 3 | gold_pips_hunter | scalp | PP/EL未指定 → 自動Shadow |
| 4 | gold_trend_momentum | daytrade | PP/EL未指定 → 自動Shadow |
| 5 | gold_vol_break | daytrade | PP/EL未指定 → 自動Shadow |
| 6 | hmm_regime_filter | daytrade | PP/EL未指定 → 自動Shadow |
| 7 | htf_false_breakout | daytrade | PP/EL未指定 → 自動Shadow |
| 8 | jpy_basket_trend | daytrade | PP/EL未指定 → 自動Shadow |
| 9 | london_breakout | scalp | PP/EL未指定 → 自動Shadow |
| 10 | london_fix_reversal | daytrade | PAIR_DEMOTED: USD_JPY |
| 11 | london_ny_swing | daytrade | PP/EL未指定 → 自動Shadow |
| 12 | london_session_breakout | daytrade | PP/EL未指定 → 自動Shadow |
| 13 | london_shrapnel | scalp | PP/EL未指定 → 自動Shadow |
| 14 | mtf_reversal_confluence | scalp | PP/EL未指定 → 自動Shadow |
| 15 | session_vol_expansion | scalp | PP/EL未指定 → 自動Shadow |
| 16 | streak_reversal | inline | PP/EL未指定 → 自動Shadow |
| 17 | three_bar_reversal | scalp | PP/EL未指定 → 自動Shadow |
| 18 | tokyo_nakane_momentum | daytrade | PP/EL未指定 → 自動Shadow |
| 19 | turtle_soup | daytrade | PP/EL未指定 → 自動Shadow |

## C. 整合性チェック結果

✅ **全チェックパス** — FORCE_DEMOTED残存なし、矛盾なし
