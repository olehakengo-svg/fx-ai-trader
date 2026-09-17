# R2 Tier 1 + hour-bucket extension - 2026-05-03

Verdict: ACCEPT
Aggregate post-extension: raw Kelly=+0.0094, MC60d=0.0030, EV=+0.06p, PF=1.021, N=169
Min extension demote set: tier1_pair:gbp_deep_pullback|GBP_USD
Bonferroni m_add: 14; alpha'_add=0.003571; keep_sig=12

## Source / separation

- 一次ソース: `/tmp/live-trades-20260503.json`
- base demote source: `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md`
- TRUE_LIVE抽出: `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status='CLOSED' AND outcome IN (...) AND pnl_pips IS NOT NULL AND instrument NOT IN ('XAU_USD','EUR_GBP') AND entry_time >= '2026-04-08'`。
- TRUE_LIVE N: 371 / Live期間: 2026-04-08T02:01:16.663697+00:00 -> 2026-05-01T13:55:29.085059+00:00。
- MC仕様: iterations=1000, horizon=60d, bootstrap=Live PnL分布。
- 本レポートは LOCK proposal。OANDA転送停止・lot変更・本番DB書き込みは未実施。

## Bucket 3-split

| bucket | N | wins | losses | breakevens | WR | EV pip | PnL pip |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRUE_LIVE | 371 | 148 | 223 | 0 | 39.89% | -0.686 | -254.6 |
| FLAG_DRIFT | 140 | 46 | 94 | 0 | 32.86% | -0.946 | -132.4 |
| SHADOW | 3819 | 911 | 2906 | 2 | 23.85% | -1.305 | -4985.6 |

## Aggregate counterfactual

Baseline TRUE_LIVE: N=371, raw Kelly=-0.1326, clipped Kelly=0.0000, MC60d=0.8650, EV=-0.69p, Wilson_lo=0.3504, PF=0.751, total=-254.6p
Base 14-cell post-cut: N=172, raw Kelly=-0.0028, clipped Kelly=0.0000, MC60d=0.0090, EV=-0.02p, Wilson_lo=0.3978, PF=0.994, total=-3.1p
Aggregate post-extension: N=169, raw Kelly=+0.0094, clipped Kelly=0.0094, MC60d=0.0030, EV=+0.06p, Wilson_lo=0.3938, PF=1.021, total=+10.2p
Kelly improvement: -0.1326 -> -0.0028 -> +0.0094
MC60d improvement: 0.8650 -> 0.0090 -> 0.0030

## Existing 14-cell base demote

| rank | strategy | instrument | N | EV pip | total pip |
|---:|---|---|---:|---:|---:|
| 1 | vwap_mean_reversion | GBP_USD | 5 | -11.62 | -58.1 |
| 2 | vix_carry_unwind | USD_JPY | 7 | -6.04 | -42.3 |
| 3 | sr_channel_reversal | USD_JPY | 22 | -1.40 | -30.8 |
| 4 | bb_rsi_reversion | USD_JPY | 58 | -0.52 | -29.9 |
| 5 | session_time_bias | GBP_USD | 7 | -4.00 | -28.0 |
| 6 | bb_squeeze_breakout | USD_JPY | 9 | -1.40 | -12.6 |
| 7 | bb_rsi_reversion | EUR_USD | 12 | -0.97 | -11.6 |
| 8 | vol_surge_detector | USD_JPY | 26 | -0.36 | -9.4 |
| 9 | engulfing_bb | USD_JPY | 9 | -0.83 | -7.5 |
| 10 | engulfing_bb | EUR_USD | 6 | -0.98 | -5.9 |
| 11 | v_reversal | USD_JPY | 5 | -0.98 | -4.9 |
| 12 | trend_rebound | USD_JPY | 8 | -0.50 | -4.0 |
| 13 | sr_channel_reversal | EUR_USD | 8 | -0.49 | -3.9 |
| 14 | stoch_trend_pullback | USD_JPY | 17 | -0.15 | -2.6 |

## Extension candidates / actions

| rank | action | keep | dimension | strategy | instrument | hour_utc | N | WR | EV pip | total pip | raw Kelly | p(edge) | Bonf p(edge) | reason |
|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | STOP_OANDA |  | tier1_pair | gbp_deep_pullback | GBP_USD | - | 3 | 66.67% | -4.43 | -13.3 | -0.9638 | 0.5000 | 1.0000 | greedy worst-first extension |
|  | KEEP | SSOT_KEEP | hour_overlay | ema_trend_scalp | EUR_USD | 07 | 3 | 66.67% | +2.53 | +7.6 | +0.4780 | 0.5000 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | ema_trend_scalp | EUR_USD | 12 | 3 | 33.33% | +1.17 | +3.5 | +0.1178 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | fib_reversal | EUR_USD | 07 | 3 | 66.67% | +2.93 | +8.8 | +0.4103 | 0.5000 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | fib_reversal | EUR_USD | 09 | 3 | 33.33% | -2.63 | -7.9 | -3.2917 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | fib_reversal | EUR_USD | 10 | 3 | 0.00% | -2.53 | -7.6 | +0.0000 | 1.0000 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | fib_reversal | USD_JPY | 04 | 5 | 20.00% | -0.88 | -4.4 | -0.1600 | 0.9688 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | stoch_trend_pullback | EUR_USD | 07 | 3 | 33.33% | +0.83 | +2.5 | +0.0969 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | stoch_trend_pullback | EUR_USD | 08 | 3 | 33.33% | -0.70 | -2.1 | -0.1667 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | trend_rebound | EUR_USD | 10 | 3 | 33.33% | -0.33 | -1.0 | -0.0654 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | vol_momentum_scalp | USD_JPY | 11 | 4 | 100.00% | +4.20 | +16.8 | +0.0000 | 0.0625 | 0.8750 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | vol_momentum_scalp | USD_JPY | 15 | 3 | 66.67% | +0.53 | +1.6 | +0.2133 | 0.5000 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | vol_surge_detector | EUR_USD | 11 | 4 | 50.00% | +0.48 | +1.9 | +0.1900 | 0.6875 | 1.0000 | SSOT protected pair keep |
|  | KEEP |  | tier1_pair | trendline_sweep | GBP_USD | - | 4 | 50.00% | -0.97 | -3.9 | -0.6964 | 0.6875 | 1.0000 | not needed after recovery |

## Bonferroni-significant keep protection

- Bonferroni-significant positive or SSOT protected keep cell数: 12
- SSOT protected pair (`fib_reversal x USD_JPY/EUR_USD` 等) は hour-bucket overlay でも STOP 対象外。

| rank | action | keep | dimension | strategy | instrument | hour_utc | N | WR | EV pip | total pip | raw Kelly | p(edge) | Bonf p(edge) | reason |
|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
|  | KEEP | SSOT_KEEP | hour_overlay | ema_trend_scalp | EUR_USD | 07 | 3 | 66.67% | +2.53 | +7.6 | +0.4780 | 0.5000 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | ema_trend_scalp | EUR_USD | 12 | 3 | 33.33% | +1.17 | +3.5 | +0.1178 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | fib_reversal | EUR_USD | 07 | 3 | 66.67% | +2.93 | +8.8 | +0.4103 | 0.5000 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | fib_reversal | EUR_USD | 09 | 3 | 33.33% | -2.63 | -7.9 | -3.2917 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | fib_reversal | EUR_USD | 10 | 3 | 0.00% | -2.53 | -7.6 | +0.0000 | 1.0000 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | fib_reversal | USD_JPY | 04 | 5 | 20.00% | -0.88 | -4.4 | -0.1600 | 0.9688 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | stoch_trend_pullback | EUR_USD | 07 | 3 | 33.33% | +0.83 | +2.5 | +0.0969 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | stoch_trend_pullback | EUR_USD | 08 | 3 | 33.33% | -0.70 | -2.1 | -0.1667 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | trend_rebound | EUR_USD | 10 | 3 | 33.33% | -0.33 | -1.0 | -0.0654 | 0.8750 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | vol_momentum_scalp | USD_JPY | 11 | 4 | 100.00% | +4.20 | +16.8 | +0.0000 | 0.0625 | 0.8750 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | vol_momentum_scalp | USD_JPY | 15 | 3 | 66.67% | +0.53 | +1.6 | +0.2133 | 0.5000 | 1.0000 | SSOT protected pair keep |
|  | KEEP | SSOT_KEEP | hour_overlay | vol_surge_detector | EUR_USD | 11 | 4 | 50.00% | +0.48 | +1.9 | +0.1900 | 0.6875 | 1.0000 | SSOT protected pair keep |

## Verdict rationale

- 既存14-cell + 最小拡張STOPで raw Kelly >= 0 かつ MC60d <= 90% を達成。
- Bonferroni-significant positive / SSOT protected keep cell は demote していない。
- `app.py` / `modules` / `strategies` は本タスクでは編集しない。
