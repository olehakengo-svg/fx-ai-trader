# BT Results: v8.5 All Pairs (2026-04-12)
**BT: DT 15m, friction model v2, 55 days**

## Cross-Pair Summary: New Strategies

| Strategy | USD_JPY | EUR_USD | GBP_USD | EUR_JPY | Verdict |
|----------|---------|---------|---------|---------|---------|
| **session_time_bias** | **+0.143** | **+0.993★** | -0.047 | N/A | **★★★★★ EUR最強, JPY正, GBP微負** |
| **london_fix_reversal** | -0.569 | N/A | **+1.009★** | N/A | **★★★★ GBP_USDで強いエッジ** |
| **xs_momentum** | -0.133 | **+0.192** | **+0.134** | N/A | **★★★ EUR/GBP正, JPY負** |
| **vix_carry_unwind** | **+2.222** | N/A | N/A | N/A | **★★★ JPY最高EV, 低頻度** |
| gotobi_fix | -2.692 | N/A | N/A | N/A | ★ 55d N不足 |
| hmm_regime_filter | N/A | N/A | N/A | N/A | 防御overlay(trade生成なし) |

## Per-Pair Detail

### USD_JPY (274t, WR=60.2%, PF=1.02)
| Strategy | WR | EV(ATR) | PnL | |
|----------|-----|---------|-----|---|
| vix_carry_unwind | 100% | +2.222 | +13.33 | ★ |
| session_time_bias | 66.7% | +0.143 | +2.14 | ✓ |
| xs_momentum | 58.3% | -0.133 | -12.74 | ✗ |
| london_fix_reversal | 33.3% | -0.569 | -1.71 | ✗ |
| gotobi_fix | 0.0% | -2.692 | -2.69 | ✗ |

### EUR_USD (185t, WR=68.6%, PF=1.546, Sharpe=3.231 ★★★)
| Strategy | WR | EV(ATR) | PnL | |
|----------|-----|---------|-----|---|
| **session_time_bias** | **87.5%** | **+0.993** | **+15.88** | **★★★★★** |
| xs_momentum | 65.3% | +0.192 | +13.84 | ✓ |

### GBP_USD (260t, WR=67.7%, PF=1.486, Sharpe=2.954 ★★★)
| Strategy | WR | EV(ATR) | PnL | |
|----------|-----|---------|-----|---|
| **london_fix_reversal** | **100%** | **+1.009** | **+1.01** | **★★★★★** |
| xs_momentum | 63.5% | +0.134 | +12.88 | ✓ |
| session_time_bias | 60.0% | -0.047 | -0.70 | △ (微負) |

### EUR_JPY (171t, WR=58.5%, PF=0.917)
- 新戦略は発火なし（EUR_JPYは既存戦略のみ）
