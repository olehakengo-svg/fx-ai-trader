# R2 strategy x instrument counterfactual - 2026-05-03

Verdict: NEEDS_MORE_EVIDENCE
Aggregate post-cut: raw Kelly=-0.0028, MC60d=0.0090, N=172
Min demote set: none; no strategy x instrument demote set reached aggregate raw Kelly >= 0 and MC60d <= 90%
Greedy tested set: vwap_mean_reversion x GBP_USD x0.0, vix_carry_unwind x USD_JPY x0.0, sr_channel_reversal x USD_JPY x0.0, bb_rsi_reversion x USD_JPY x0.0, session_time_bias x GBP_USD x0.0, bb_squeeze_breakout x USD_JPY x0.0, bb_rsi_reversion x EUR_USD x0.0, vol_surge_detector x USD_JPY x0.0, engulfing_bb x USD_JPY x0.0, engulfing_bb x EUR_USD x0.0, v_reversal x USD_JPY x0.0, trend_rebound x USD_JPY x0.0, sr_channel_reversal x EUR_USD x0.0, stoch_trend_pullback x USD_JPY x0.0
ELITE_FLAG: session_time_bias x GBP_USD -> N=7, EV=-4.00, PnL=-28.0, action=STOP_OANDA; recommend immediate WATCH escalation as separate action.

## Bucket 3-split (post-cutoff, excluding XAU_USD/EUR_GBP)

| bucket | N | wins | losses | breakevens | WR | EV pip | PnL pip |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRUE_LIVE | 371 | 148 | 223 | 0 | 39.89% | -0.686 | -254.6 |
| FLAG_DRIFT | 140 | 46 | 94 | 0 | 32.86% | -0.946 | -132.4 |
| SHADOW | 3819 | 911 | 2906 | 2 | 23.85% | -1.305 | -4985.6 |

## Source / separation

- 一次ソース: `/tmp/live-trades-20260503.json`
- Live抽出: `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status='CLOSED' AND outcome IN (...) AND pnl_pips IS NOT NULL AND instrument NOT IN ('XAU_USD','EUR_GBP') AND entry_time >= '2026-04-08'`。
- modeフィルタは未使用。
- TRUE_LIVE N: 371 / Live期間: 2026-04-08T02:01:16.663697+00:00 -> 2026-05-01T13:55:29.085059+00:00。
- Bonferroni母数 m: **24 TRUE_LIVE N>=5 strategy x instrument cells**。alpha'=0.05/24=0.002083。
- MC仕様: iterations=1000, horizon=60d, bootstrap=Live PnL分布。
- OANDA転送停止・lot変更・本番DB書き込みは未実施。

## Aggregate counterfactual

Baseline TRUE_LIVE: N=371, raw Kelly=-0.1326, clipped Kelly=0.0000, MC60d=0.8650, EV=-0.69p, Wilson_lo=0.3504, PF=0.751, maxDD=0.2962, total=-254.6p
Greedy post-cut: N=172, raw Kelly=-0.0028, clipped Kelly=0.0000, MC60d=0.0090, EV=-0.02p, Wilson_lo=0.3978, PF=0.994, maxDD=0.0818, total=-3.1p
All negative N>=5 STOP: N=172, raw Kelly=-0.0028, clipped Kelly=0.0000, MC60d=0.0090, EV=-0.02p, Wilson_lo=0.3978, PF=0.994, maxDD=0.0818, total=-3.1p

## Strategy x instrument cells

| rank | action | lot | keep | strategy | instrument | N | WR | Wilson lo | EV pip | total pip | PF | raw Kelly | p(edge) | Bonf p(edge) | max DD | reason |
|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | STOP_OANDA | 0.0 |  | vwap_mean_reversion | GBP_USD | 5 | 20.00% | 3.62% | -11.62 | -58.1 | 0.020 | -9.6833 | 0.9688 | 1.0000 | 5.93% | worst-first 0.5x insufficient; stop |
| 2 | STOP_OANDA | 0.0 |  | vix_carry_unwind | USD_JPY | 7 | 28.57% | 8.22% | -6.04 | -42.3 | 0.410 | -0.4111 | 0.9375 | 1.0000 | 4.23% | worst-first 0.5x insufficient; stop |
| 3 | STOP_OANDA | 0.0 |  | sr_channel_reversal | USD_JPY | 22 | 22.73% | 10.12% | -1.40 | -30.8 | 0.294 | -0.5469 | 0.9978 | 1.0000 | 3.08% | worst-first 0.5x insufficient; stop |
| 4 | STOP_OANDA | 0.0 |  | bb_rsi_reversion | USD_JPY | 58 | 39.66% | 28.09% | -0.52 | -29.9 | 0.725 | -0.1503 | 0.9561 | 1.0000 | 4.98% | worst-first 0.5x insufficient; stop |
| 5 | STOP_OANDA | 0.0 |  | session_time_bias | GBP_USD | 7 | 28.57% | 8.22% | -4.00 | -28.0 | 0.085 | -3.0769 | 0.9375 | 1.0000 | 2.93% | worst-first 0.5x insufficient; stop |
| 6 | STOP_OANDA | 0.0 |  | bb_squeeze_breakout | USD_JPY | 9 | 33.33% | 12.06% | -1.40 | -12.6 | 0.344 | -0.6364 | 0.9102 | 1.0000 | 1.86% | worst-first 0.5x insufficient; stop |
| 7 | STOP_OANDA | 0.0 |  | bb_rsi_reversion | EUR_USD | 12 | 25.00% | 8.89% | -0.97 | -11.6 | 0.523 | -0.2283 | 0.9807 | 1.0000 | 1.16% | worst-first 0.5x insufficient; stop |
| 8 | STOP_OANDA | 0.0 |  | vol_surge_detector | USD_JPY | 26 | 46.15% | 28.76% | -0.36 | -9.4 | 0.792 | -0.1212 | 0.7214 | 1.0000 | 2.15% | worst-first 0.5x insufficient; stop |
| 9 | STOP_OANDA | 0.0 |  | engulfing_bb | USD_JPY | 9 | 33.33% | 12.06% | -0.83 | -7.5 | 0.522 | -0.3049 | 0.9102 | 1.0000 | 0.75% | worst-first 0.5x insufficient; stop |
| 10 | STOP_OANDA | 0.0 |  | engulfing_bb | EUR_USD | 6 | 16.67% | 3.01% | -0.98 | -5.9 | 0.524 | -0.1513 | 0.9844 | 1.0000 | 1.24% | worst-first 0.5x insufficient; stop |
| 11 | STOP_OANDA | 0.0 |  | v_reversal | USD_JPY | 5 | 20.00% | 3.62% | -0.98 | -4.9 | 0.642 | -0.1114 | 0.9688 | 1.0000 | 1.01% | worst-first 0.5x insufficient; stop |
| 12 | STOP_OANDA | 0.0 |  | trend_rebound | USD_JPY | 8 | 37.50% | 13.68% | -0.50 | -4.0 | 0.697 | -0.1630 | 0.8555 | 1.0000 | 0.68% | worst-first 0.5x insufficient; stop |
| 13 | STOP_OANDA | 0.0 |  | sr_channel_reversal | EUR_USD | 8 | 25.00% | 7.15% | -0.49 | -3.9 | 0.772 | -0.0739 | 0.9648 | 1.0000 | 1.21% | worst-first 0.5x insufficient; stop |
| 14 | STOP_OANDA | 0.0 |  | stoch_trend_pullback | USD_JPY | 17 | 35.29% | 17.31% | -0.15 | -2.6 | 0.904 | -0.0376 | 0.9283 | 1.0000 | 2.20% | worst-first 0.5x insufficient; stop |
|  | KEEP | 1.0 | KEEP_SIG | bb_rsi_reversion | GBP_USD | 5 | 40.00% | 11.76% | +0.42 | +2.1 | 1.159 | +0.0549 | 0.8125 | 1.0000 | 1.32% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | bb_squeeze_breakout | EUR_USD | 5 | 40.00% | 11.76% | +0.56 | +2.8 | 1.354 | +0.1047 | 0.8125 | 1.0000 | 0.49% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | dt_bb_rsi_mr | USD_JPY | 7 | 57.14% | 25.05% | +1.50 | +10.5 | 1.840 | +0.2609 | 0.5000 | 1.0000 | 0.64% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | ema_trend_scalp | EUR_USD | 10 | 40.00% | 16.82% | +0.35 | +3.5 | 1.197 | +0.0657 | 0.8281 | 1.0000 | 1.45% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | fib_reversal | EUR_USD | 13 | 46.15% | 23.21% | +0.20 | +2.6 | 1.094 | +0.0397 | 0.7095 | 1.0000 | 1.51% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | fib_reversal | USD_JPY | 13 | 38.46% | 17.71% | -0.18 | -2.3 | 0.906 | -0.0400 | 0.8666 | 1.0000 | 1.39% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | stoch_trend_pullback | EUR_USD | 9 | 33.33% | 12.06% | +0.21 | +1.9 | 1.123 | +0.0364 | 0.9102 | 1.0000 | 1.25% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | trend_rebound | EUR_USD | 8 | 37.50% | 13.68% | +0.25 | +2.0 | 1.149 | +0.0487 | 0.8555 | 1.0000 | 1.04% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | vol_momentum_scalp | USD_JPY | 13 | 61.54% | 35.52% | +0.90 | +11.7 | 1.600 | +0.2308 | 0.2905 | 1.0000 | 0.99% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | vol_surge_detector | EUR_USD | 6 | 66.67% | 30.00% | +1.93 | +11.6 | 4.742 | +0.5261 | 0.3438 | 1.0000 | 0.31% | SSOT/Bonferroni positive edge; protected keep |

## Bonferroni-significant keep protection

- protected keep cell数: 10
- `KEEP_SIG` は SSOTのLive黒字/keep指定、または N>=5, EV>0, one-sided binomial positive-edge p <= alpha' の cell。該当 cell は demote 候補から除外。

| rank | action | lot | keep | strategy | instrument | N | WR | Wilson lo | EV pip | total pip | PF | raw Kelly | p(edge) | Bonf p(edge) | max DD | reason |
|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
|  | KEEP | 1.0 | KEEP_SIG | bb_rsi_reversion | GBP_USD | 5 | 40.00% | 11.76% | +0.42 | +2.1 | 1.159 | +0.0549 | 0.8125 | 1.0000 | 1.32% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | bb_squeeze_breakout | EUR_USD | 5 | 40.00% | 11.76% | +0.56 | +2.8 | 1.354 | +0.1047 | 0.8125 | 1.0000 | 0.49% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | dt_bb_rsi_mr | USD_JPY | 7 | 57.14% | 25.05% | +1.50 | +10.5 | 1.840 | +0.2609 | 0.5000 | 1.0000 | 0.64% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | ema_trend_scalp | EUR_USD | 10 | 40.00% | 16.82% | +0.35 | +3.5 | 1.197 | +0.0657 | 0.8281 | 1.0000 | 1.45% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | fib_reversal | EUR_USD | 13 | 46.15% | 23.21% | +0.20 | +2.6 | 1.094 | +0.0397 | 0.7095 | 1.0000 | 1.51% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | fib_reversal | USD_JPY | 13 | 38.46% | 17.71% | -0.18 | -2.3 | 0.906 | -0.0400 | 0.8666 | 1.0000 | 1.39% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | stoch_trend_pullback | EUR_USD | 9 | 33.33% | 12.06% | +0.21 | +1.9 | 1.123 | +0.0364 | 0.9102 | 1.0000 | 1.25% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | trend_rebound | EUR_USD | 8 | 37.50% | 13.68% | +0.25 | +2.0 | 1.149 | +0.0487 | 0.8555 | 1.0000 | 1.04% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | vol_momentum_scalp | USD_JPY | 13 | 61.54% | 35.52% | +0.90 | +11.7 | 1.600 | +0.2308 | 0.2905 | 1.0000 | 0.99% | SSOT/Bonferroni positive edge; protected keep |
|  | KEEP | 1.0 | KEEP_SIG | vol_surge_detector | EUR_USD | 6 | 66.67% | 30.00% | +1.93 | +11.6 | 4.742 | +0.5261 | 0.3438 | 1.0000 | 0.31% | SSOT/Bonferroni positive edge; protected keep |

## ELITE_FLAG

- `session_time_bias x GBP_USD` は ELITE_LIVE 出血セルとして別アクションで WATCH 格上げを推奨。
- Current grid evidence: N=7, EV=-4.00, PnL=-28.0, action=STOP_OANDA

## Verdict rationale

- raw Kelly は -0.05 以上まで近づいた、または全N>=5出血cell STOPで -0.05 以上に入った。Gate 0救済には拡張範囲が必要。
- Live黒字cellは greedy demote 候補から除外。
- 本レポートは LOCK proposal。実装PRや `app.py` 変更は別タスク。
