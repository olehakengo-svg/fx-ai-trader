# Regime-Gate Phase B2.5 Summary

- generated_at: 2026-05-13T03:48:37.901300+00:00
- data_source_required: MASSIVE parquet (`BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`)
- pair baseline trades: USDJPY=2130, EURUSD=1520, GBPUSD=1967
- all family universe: 66; observed BT families: 34
- zero-trade families: asia_range_fade_v1, bb_rsi_ema_aligned, bb_rsi_reversion, bb_squeeze_breakout, cpd_divergence, engulfing_bb, eurgbp_daily_mr, gold_trend_momentum, gold_vol_break, gotobi_fix, hmm_regime_filter, london_breakout, london_close_reversal, london_close_reversal_v2, london_session_breakout, ma_regime_switch, mtf_regime_range_cascade_scalp, mtf_regime_trend_cascade_scalp, mtf_reversal_confluence, ny_close_reversal, pd_eurjpy_h20_bbpb3_sell, pullback_to_liquidity_v1, rsk_gbpjpy_reversion, sr_liquidity_grab, stoch_trend_pullback, three_bar_reversal, tokyo_nakane_momentum, trend_rebound, vdr_jpy, vol_momentum_scalp, vsg_jpy_reversal, vwap_mean_reversion
- NOT_CATASTROPHIC proposals: 17

## Tier A Reproduction Benchmark

| condition | N | WR | EV |
|---|---:|---:|---:|
| baseline | 0 | 0.000 | +0.000 |
| gated_TRENDING | 0 | 0.000 | +0.000 |
| gated_RANGING | 0 | 0.000 | +0.000 |
| gated_CHOP | 0 | 0.000 | +0.000 |

Expected reference: baseline ~316 / WR ~60% / EV ~+0.01; TRENDING ~104 / WR ~64% / EV ~+0.11; RANGING ~51 / WR ~47% / EV ~-0.39; CHOP ~161 / WR ~62% / EV ~+0.07.

## Top 10 Shadow Proposals

| proposal | N | WR | EV | PF |
|---|---:|---:|---:|---:|
| sr_anti_hunt_bounce__regime_CHOP | 49 | 0.816 | +3.915 | 4.320264 |
| streak_reversal__regime_TRENDING | 105 | 0.752 | +1.227 | 3.159914 |
| post_news_vol__regime_CHOP | 39 | 0.718 | +1.146 | 2.335231 |
| streak_reversal__regime_RANGING | 94 | 0.745 | +1.003 | 2.316252 |
| vix_carry_unwind__regime_CHOP | 41 | 0.780 | +0.954 | 2.208247 |
| streak_reversal__regime_CHOP | 273 | 0.678 | +0.796 | 1.99513 |
| trendline_sweep__regime_CHOP | 92 | 0.750 | +0.762 | 2.070795 |
| vix_carry_unwind__regime_TRENDING | 51 | 0.686 | +0.561 | 1.535967 |
| turtle_soup__regime_CHOP | 31 | 0.677 | +0.330 | 1.430869 |
| htf_false_breakout__regime_CHOP | 38 | 0.658 | +0.322 | 1.592118 |

## Next Action

司令塔側で artifacts と Tier A 再現ベンチマークを確認し、commit する。BT 結果は Shadow 候補生成のみで、Live 昇格判定には使わない。
