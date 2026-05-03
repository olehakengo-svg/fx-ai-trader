# Dedup Violation Triage — 2026-05-03

- Cutoff used: `2026-05-03T02:57:13+09:00` (lesson commit date fallback policy)
- Underlying audit drift guard: `total=46`, `live=0`
- Verdict: `ACTIVE_GAP_PROBABLE=0`; all 46 rows are historical unless a later snapshot introduces post-cutoff rows.

## Summary Counts

| Classification | Rows |
|---|---:|
| HISTORICAL_LEGACY | 46 |
| ACTIVE_GAP_PROBABLE | 0 |
| INDETERMINATE | 0 |
| TOTAL | 46 |

## Per-Combo Table

| Classification | Strategy | Pair | TF | Rows | Dup PnL | Tier |
|---|---|---|---|---:|---:|---|
| HISTORICAL_LEGACY | sr_break_retest | USD_JPY | 15m | 3 | -144.9p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | fib_reversal | USD_JPY | 1m | 9 | +137.7p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | dt_bb_rsi_mr | GBP_USD | 15m | 3 | +71.8p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | post_news_vol | USD_JPY | 15m | 2 | -34.5p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | sr_fib_confluence | USD_JPY | 15m | 3 | +30.5p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | intraday_seasonality | GBP_USD | 15m | 2 | +30.2p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | doji_breakout | USD_JPY | 15m | 2 | -25.1p | PAIR_PROMOTED |
| HISTORICAL_LEGACY | sr_break_retest | GBP_JPY | 15m | 1 | -20.0p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | engulfing_bb | GBP_USD | 5m | 1 | +19.9p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | sr_fib_confluence | GBP_JPY | 15m | 1 | -16.9p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | session_time_bias | GBP_USD | 15m | 1 | -14.2p | UNIVERSAL_SENTINEL |
| HISTORICAL_LEGACY | ema_cross | GBP_USD | 15m | 1 | +12.5p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | vol_surge_detector | GBP_USD | 5m | 2 | -11.6p | SCALP_SENTINEL |
| HISTORICAL_LEGACY | vol_spike_mr | USD_JPY | 15m | 4 | -9.3p | UNIVERSAL_SENTINEL |
| HISTORICAL_LEGACY | sr_fib_confluence | GBP_USD | 15m | 1 | -5.8p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | dt_sr_channel_reversal | GBP_USD | 15m | 1 | -5.2p | UNIVERSAL_SENTINEL |
| HISTORICAL_LEGACY | ema200_trend_reversal | GBP_USD | 15m | 1 | -4.9p | REGISTERED_SHADOW |
| HISTORICAL_LEGACY | ema_trend_scalp | USD_JPY | 5m | 1 | -4.6p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | ema_trend_scalp | EUR_USD | 5m | 2 | +4.2p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | ema_trend_scalp | USD_JPY | 1m | 1 | -0.4p | FORCE_DEMOTED |
| HISTORICAL_LEGACY | vol_surge_detector | USD_JPY | 5m | 2 | +0.2p | SCALP_SENTINEL |
| HISTORICAL_LEGACY | dt_fib_reversal | EUR_JPY | 15m | 1 | -0.1p | UNIVERSAL_SENTINEL |
| HISTORICAL_LEGACY | stoch_trend_pullback | USD_JPY | 1m | 1 | -0.1p | FORCE_DEMOTED |

## ACTIVE_GAP List

- None. No post-cutoff registered strategy rows were found.

## Promotion Impact

- doji_breakout / USD_JPY / 15m — tier `PAIR_PROMOTED`, 2 duplicated shadow rows, duplicate PnL -25.1p.
- session_time_bias / GBP_USD / 15m — tier `UNIVERSAL_SENTINEL`, 1 duplicated shadow rows, duplicate PnL -14.2p.
- post_news_vol / USD_JPY / 15m — tier `FORCE_DEMOTED`, 2 duplicated shadow rows, duplicate PnL -34.5p.
- Wilson/EV impact verdict: current live promotion math does not move directly here because `violations_with_oanda_fill=0`; the risk is shadow candidate inflation/deflation in follow-up promotion audits, not live fill contamination.

## Cutoff-Date Sensitivity

| Cutoff | HIST | ACTIVE | INDET |
|---|---:|---:|---:|
| cutoff-3d | 46 | 0 | 0 |
| cutoff | 46 | 0 | 0 |
| cutoff+3d | 46 | 0 | 0 |

- Result is stable under cutoff +/-3 days: ACTIVE_GAP count does not change.
