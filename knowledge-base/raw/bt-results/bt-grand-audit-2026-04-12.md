# Grand BT Audit: All Strategies x All Pairs x All Modes (2026-04-12 v8.6)
**10 BT runs, friction model v2, post-Friday-block-removal**

## Portfolio Summary
| Config | N | WR | PF | EV(ATR) | Sharpe |
|--------|---|-----|-----|---------|--------|
| **EUR_USD DT 55d** | **199** | **69.8%** | **1.63** | **+0.440** | **3.629 ★★★★★** |
| **GBP_USD DT 55d** | **269** | **68.0%** | **1.49** | **+0.372** | **2.997 ★★★★** |
| USD_JPY DT 55d | 285 | 59.6% | 1.00 | -0.000 | -0.002 |
| EUR_JPY DT 55d | 171 | 58.5% | 0.92 | -0.066 | -0.661 |
| USD_JPY 1H 60d | 15 | 40.0% | - | +0.195 | 1.520 |
| EUR_USD 1H 60d | 15 | 26.7% | - | -0.188 | -1.678 |
| USD_JPY Scalp 7d | 104 | 58.7% | 0.76 | -0.288 | -0.124 |
| EUR_USD Scalp 7d | 59 | 61.0% | 0.89 | -0.120 | -0.053 |
| GBP_USD Scalp 7d | 102 | 52.9% | 0.45 | -0.714 | -0.344 |
| EUR_JPY Scalp 7d | 114 | 58.8% | 0.65 | -0.363 | -0.191 |

## Key Finding: EUR_USD DT is the strongest portfolio (Sharpe=3.629)

### EUR_USD DT Top Strategies
| Strategy | WR | EV | PnL |
|----------|-----|-----|-----|
| htf_false_breakout | 100% | +2.692 | +10.77 |
| trendline_sweep | 88.9% | +1.677 | +15.09 |
| squeeze_release_momentum | 100% | +1.491 | +4.47 |
| post_news_vol | 66.7% | +1.031 | +3.09 |
| session_time_bias | 76.9% | +0.650 | +25.33 |
| orb_trap | 60.0% | +0.485 | +4.85 |
| xs_momentum | 69.0% | +0.345 | +24.52 |

### GBP_USD DT Top Strategies
| Strategy | WR | EV | PnL |
|----------|-----|-----|-----|
| post_news_vol | 100% | +3.253 | +9.76 |
| gbp_deep_pullback | 100% | +3.133 | +12.53 |
| orb_trap | 100% | +1.717 | +10.30 |
| trendline_sweep | 77.8% | +1.188 | +21.39 |
| london_fix_reversal | 75.0% | +0.318 | +1.27 |
| session_time_bias | 69.4% | +0.266 | +9.59 |
| xs_momentum | 65.0% | +0.182 | +18.71 |

### USD_JPY DT — session_time_bias improved
| Strategy | WR | EV | PnL |
|----------|-----|-----|-----|
| tokyo_nakane_momentum | 100% | +1.719 | +3.44 |
| orb_trap | 100% | +1.443 | +2.89 |
| vix_carry_unwind | 85.7% | +1.378 | +9.64 |
| session_time_bias | **70.8%** | **+0.373** | **+8.95** |

## Scalp: Mostly Negative EV (friction-dominated)
- USD_JPY: vol_momentum +0.387, fib_reversal +0.066, bb_rsi **-0.522**
- EUR_USD: bb_rsi **+0.943** (EUR scalp only positive pair)
- GBP_USD: **All strategies negative** (PF=0.45)
- EUR_JPY: vol_momentum +0.109, most negative

## Related
- [[edge-pipeline]] — 評価パイプライン
- [[friction-analysis]] — Scalp摩擦支配の根拠
- [[academic-audit-2026-04-12]] — DSR統計的有意性検証
