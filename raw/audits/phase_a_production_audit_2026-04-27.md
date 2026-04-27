# Phase A Production Audit — 2026-04-27

**Input**: `/tmp/render_trades_v2.json`
**Cutoff**: post-2026-04-16, is_shadow=0, outcome WIN/LOSS only

## 1. Aggregate Live Kelly

- N (Live closed) = 26
- Wins = 9 / Losses = 17
- Avg R per trade = -0.1638
- **Aggregate Kelly (full) = -0.1230**

**Agent#3 比較**: 報告 Live Kelly = +0.0157 (Gate 1 通過)
- 一致条件: 本数字 >= +0.005 ならば Agent#3 と同方向

## 2. WR<35% AND N>=20 Live cells (M4 deny candidates)

**(該当 cell ゼロ)**

## 3. bb_rsi_reversion × USD_JPY × {scalp, scalp_5m} Live

| mode | N | WR | Wilson_lo | sum_R | sum_pips |
|---|---:|---:|---:|---:|---:|
| scalp | 6 | 16.7% | 3.0% | -4.03 | -12.2 |
| scalp_5m | 2 | 0.0% | 0.0% | -2.03 | -8.6 |

**Agent#3 報告 (claimed)**: N=74, WR=44.6%, Wlo=33.8%, sum_R=+7.21

## 4. Agent#3 hinted DENY cells comparison

| cell | production_N | production_WR | matches_hint? |
|---|---:|---:|:-:|
| sr_channel_reversal × USD_JPY × scalp | (no production data) | — | ✗ |
| ema_trend_scalp × EUR_USD × scalp | (no production data) | — | ✗ |
| ema_trend_scalp × USD_JPY × scalp | (no production data) | — | ✗ |
| ema_trend_scalp × GBP_USD × scalp | (no production data) | — | ✗ |
| stoch_trend_pullback × USD_JPY × scalp | (no production data) | — | ✗ |

## 5. Top 20 Live cells by N

| cell | N | WR | Wilson_lo | sum_R | kelly |
|---|---:|---:|---:|---:|---:|
| bb_rsi_reversion × USD_JPY × scalp | 6 | 16.7% | 3.0% | -4.03 | -0.564 |
| vwap_mean_reversion × EUR_JPY × daytrade_eurjpy | 4 | 50.0% | 15.0% | -1.82 | -5.056 |
| vwap_mean_reversion × GBP_USD × daytrade_gbpusd | 4 | 25.0% | 4.6% | -2.65 | -3.487 |
| trendline_sweep × GBP_USD × daytrade_gbpusd | 3 | 33.3% | 6.2% | -0.16 | -0.072 |
| bb_rsi_reversion × USD_JPY × scalp_5m | 2 | 0.0% | 0.0% | -2.03 | +0.000 |
| bb_rsi_reversion × GBP_USD × scalp_5m_gbp | 2 | 0.0% | 0.0% | -2.25 | +0.000 |
| vwap_mean_reversion × GBP_JPY × daytrade_gbpjpy | 2 | 50.0% | 9.4% | +1.37 | +0.288 |
| gbp_deep_pullback × GBP_USD × daytrade_gbpusd | 1 | 100.0% | 20.6% | +6.23 | +0.000 |
| doji_breakout × USD_JPY × daytrade | 1 | 100.0% | 20.6% | +1.02 | +0.000 |
| post_news_vol × GBP_USD × daytrade_gbpusd | 1 | 100.0% | 20.6% | +0.06 | +0.000 |

---

本 audit は production /api/demo/trades?limit=2000 直接 read。Agent#3 の集計が local DB の古い snapshot を使っている可能性ありで、両方の結果を cell-by-cell 比較するための fact-check 用。