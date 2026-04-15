# 全戦略BTスキャン (2026-04-15) — 180日Scalp + 365日DT + 500日1H

**データ**: Massive API Parquetキャッシュ (180日1m/5m, 365日15m, 500日1h)
**BT Bias修正**: ④RANGE TP Override + ⑤Quick-Harvest反映済み
**Scalp結果**: 実行中（完了次第追記）

---

## DT 15m (365日, 6ペア) — BT Bias④⑤反映版

### STRONG (N≥10, EV>0.3, PF>1.2)

| Strategy | Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|---|
| post_news_vol | GBP_USD | 26 | 84.6% | +1.589 | 3.30 | +41.3p |
| htf_false_breakout | USD_JPY | 14 | 100% | +1.291 | — | +18.1p |
| gbp_deep_pullback | GBP_USD | 84 | 72.6% | +1.104 | 1.95 | +92.7p |
| trendline_sweep | EUR_USD | 67 | 82.1% | +0.987 | 2.75 | +66.1p |
| post_news_vol | USD_JPY | 25 | 80.0% | +0.933 | 1.82 | +23.3p |
| post_news_vol | EUR_USD | 26 | 73.1% | +0.836 | 1.72 | +21.7p |
| doji_breakout | GBP_USD | 20 | 80.0% | +0.793 | 2.70 | +15.9p |
| trendline_sweep | GBP_USD | 127 | 76.4% | +0.774 | 2.04 | +98.3p |
| **vwap_mean_reversion** | **GBP_USD** | **254** | **70.9%** | **+0.758** | **2.69** | **+192.6p** |
| htf_false_breakout | EUR_USD | 12 | 83.3% | +0.625 | 2.04 | +7.5p |
| **vwap_mean_reversion** | **EUR_USD** | **210** | **72.9%** | **+0.615** | **2.53** | **+129.2p** |
| turtle_soup | GBP_USD | 60 | 71.7% | +0.560 | 1.79 | +33.6p |
| **vix_carry_unwind** | **USD_JPY** | **103** | **69.9%** | **+0.521** | **1.48** | **+53.7p** |
| squeeze_release_momentum | EUR_USD | 15 | 66.7% | +0.460 | 1.91 | +6.9p |
| htf_false_breakout | GBP_USD | 25 | 72.0% | +0.411 | 1.62 | +10.3p |
| ema_cross | EUR_JPY | 32 | 71.9% | +0.337 | 1.67 | +10.8p |
| **vwap_mean_reversion** | **EUR_JPY** | **380** | **68.2%** | **+0.318** | **1.70** | **+120.8p** |
| dt_fib_reversal | GBP_USD | 22 | 72.7% | +0.310 | 1.63 | +6.8p |
| adx_trend_continuation | EUR_USD | 11 | 63.6% | +0.303 | 1.31 | +3.3p |
| **session_time_bias** | **EUR_USD** | **526** | **69.0%** | **+0.301** | **1.47** | **+158.2p** |

### 前回(60日)との比較 — 主要戦略

| Strategy | Pair | 60日EV | 365日EV | 変化 | 判定 |
|---|---|---|---|---|---|
| session_time_bias | USD_JPY | +0.580 | +0.206 | -0.374 | EVは低下したがまだ正EV |
| session_time_bias | EUR_USD | +0.215 | +0.301 | +0.086 | **改善** |
| trendline_sweep | GBP_USD | +0.599 | +0.774 | +0.175 | **改善** |
| gbp_deep_pullback | GBP_USD | +1.064 | +1.104 | +0.040 | 安定 |
| vwap_mean_reversion | GBP_USD | — | +0.758 | 新規 | **BT Bias修正で正EV出現** |
| vwap_mean_reversion | EUR_JPY | — | +0.318 | 新規 | **BT Bias修正で出現** |
| vix_carry_unwind | USD_JPY | +0.212 | +0.521 | +0.309 | **大幅改善(N倍増)** |

### 1Hモード (500日) — 全戦略AVOID

h1_breakout_retestのみ発火。全ペアで負EV。1Hモードはα不在確定。

## Scalp結果（追記予定）

実行中。完了次第追記。

## Related
- [[comprehensive-bt-scan-2026-04-14]] — 前回の60日スキャン（比較用）
- [[massive-alpha-scan-2026-04-14]] — Massive固有α
- [[roadmap-v2.1]] — 戦略ポートフォリオ
