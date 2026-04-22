# VWAP Mean Reversion

## Overview
- **Entry Type**: `vwap_mean_reversion`
- **Category**: MR (Mean Reversion)
- **Timeframe**: Scalp 1m, DT 15m/1h
- **Status**: PAIR_PROMOTED (EUR_JPY, GBP_JPY); LOT_BOOST 1.5x
- **Active Pairs**: EUR_JPY (PAIR_PROMOTED), GBP_JPY (PAIR_PROMOTED)

## BT Performance (365d, 15m)
From massive alpha scan (Bonferroni significant, friction-adjusted):
| Edge | Pair | TF | Hold | N | fWR | fEV(pip) | Annual PnL |
|---|---|---|---|---|---|---|---|
| VW2s BUY | EUR_JPY | 15m | 16b(4h) | 737 | 55.8% | +3.85 | +2,837p |
| VW2s BUY | GBP_JPY | 15m | 16b(4h) | 740 | 56.2% | +5.17 | +3,827p |
| VW2s BUY | USD_JPY | 15m | 16b(4h) | 705 | 55.0% | +2.98 | +2,099p |
| VW2s BUY | GBP_JPY | 1h | 16b | 245 | 56.3% | +13.4 | +3,290p |
| VW2s BUY | EUR_JPY | 1h | 16b | 226 | 58.0% | +6.32 | +1,428p |

### Fresh 365d × 15m BT (2026-04-22, `raw/bt-results/bt-365d-jpy-2026-04-22.json`)
| Pair | N | WR | EV | PnL | Walk-forward EV (w1/w2/w3) |
|---|---|---|---|---|---|
| EUR_JPY | 223 | 68.2% | +0.672 | +149.9 pip | +0.103 / +0.219 / +0.101 |
| GBP_JPY | 267 | 78.3% | +1.025 | +273.7 pip | +0.338 / +0.205 / +0.313 |

PAIR_PROMOTED の既存根拠を 2026-04-22 スキャンで再確証（walk-forward 全窓で正 EV、GBP_JPY は最強セル）。

Scalp (Bonferroni significant):
| Edge | Pair | TF | Hold | N | fWR | fEV(pip) | Annual PnL |
|---|---|---|---|---|---|---|---|
| VW2s BUY | EUR_JPY | 1m | 16min | 2,574 | 56.5% | +0.81 | +2,087p |
| VW2s BUY | GBP_JPY | 1m | 16min | 2,028 | 53.6% | +0.48 | +975p |

### Scalp BT 2026-04-22 バグ発覚 + 修正完了
180d Scalp BT では `vwap_mean_reversion` の発火が 10 cell すべてでゼロ。原因は `app.py:_compute_scalp_signal_v2` 内で `htf_agreement` 変数が未定義、silent except で NameError が飲み込まれていた。2026-04-22 に `app.py:L7992` で `htf_agreement = htf.get("agreement", "mixed")` を追加して修正（commit `0981945`）。

Post-fix 180d × {1m, 5m} × JPY crosses (`raw/bt-results/bt-scalp-180d-jpy-postfix-2026-04-22.json`):
| Pair | TF | N | WR | EV | PnL |
|---|---|---|---|---|---|
| EUR_JPY | 1m | 17 | — | -0.272 | 負 |
| EUR_JPY | 5m | 2 | 100% | +0.874 | 小 N |
| GBP_JPY | 1m | 14 | 50.0% | -0.114 | 負 |
| GBP_JPY | 5m | 3 | 66.7% | +0.132 | 小 N |

- ✅ 発火復活、signal は機能
- ⚠️ 1m 版は両ペア負 EV、5m 版は正 EV だが N=2-3 で結論不可
- 🚫 Scalp 全体 EV は改善せず、Scalp vwap_mr は Live 配置候補として保留（365d 延長 BT or 1 年 N 蓄積まで）

## Live Performance (post-cutoff, 2026-04-08〜)
| Strategy | Pairs | N | WR | PnL |
|---|---|---|---|---|
| vwap_mean_reversion | all | 2 | 50.0% | +36.9 pip |

Top performer in post-cutoff period. Small N — continue monitoring.
Data source: /api/demo/stats?date_from=2026-04-08 (2026-04-21, no new trades)

## Signal Logic
VWAP 2-sigma mean reversion. Enters BUY when price drops below VWAP minus 2 standard deviations, expecting reversion to VWAP. Massive API exclusive alpha — requires intraday VWAP calculation from tick/volume data. Bonferroni-corrected p<10^-7 across JPY crosses.

## Current Configuration
- Lot Boost: 1.5x (strategy-level)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: EUR_JPY (15m 16bar: annual +2,837pip), GBP_JPY (15m 16bar: annual +3,827pip, strongest alpha)
- PAIR_LOT_BOOST: EUR_JPY 1.8x, GBP_JPY 1.8x

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
