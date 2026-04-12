# BT Results: v8.6 Time Window Expansion (2026-04-12)

## Before vs After Comparison

### session_time_bias
| Pair | v8.5 EV | v8.6 EV | Change | v8.5 WR | v8.6 WR |
|------|---------|---------|--------|---------|---------|
| USD_JPY | +0.143 | **+0.427** | **+199%** | 66.7% | **73.1%** |
| EUR_USD | +0.993 | **+0.650** | -35% (wider window = lower avg) | 87.5% | **76.9%** |
| GBP_USD | -0.047 | **+0.266** | **NEGATIVE→POSITIVE** | 60.0% | **69.4%** |

**重大改善**: GBP_USDが微負→正EVに転換。JPYは+199%改善。EURのEV低下はN増加による平均希釈（WRは依然76.9%で堅実）。

### london_fix_reversal
| Pair | v8.5 EV | v8.6 EV | Change | v8.5 WR | v8.6 WR |
|------|---------|---------|--------|---------|---------|
| GBP_USD | +1.009 | **+0.318** | -69% (N増=より現実的) | 100% | **75.0%** |
| EUR_USD | N/A | **-0.110** | NEW (発火開始) | N/A | **57.1%** |
| USD_JPY | -0.569 | **-0.752** | 悪化 | 33.3% | 28.6% |

**重要**: GBP WR=100%→75%は過学習の除去（N増による統計的安定化）。GBP EV=+0.318は依然正。EUR_USDで初めて発火（WR=57.1%）。

### xs_momentum
| Pair | v8.5 EV | v8.6 EV | Change |
|------|---------|---------|--------|
| EUR_USD | +0.192 | **+0.308** | **+60%** |
| GBP_USD | +0.134 | **+0.141** | +5% |
| USD_JPY | -0.133 | **-0.129** | 微改善 |

### 全体ポートフォリオ改善
| Pair | v8.5 total | v8.6 total | Change |
|------|-----------|-----------|--------|
| USD_JPY | 274t PF=1.02 | **285t PF=1.038** | +11t, PF改善 |
| EUR_USD | 185t PF=1.546 | **197t PF=1.598** | +12t, PF改善 |
| GBP_USD | 260t PF=1.486 | **269t PF=1.546** | +9t, PF改善 |

## Related
- [[edge-pipeline]] — 評価パイプライン
- [[session-time-bias]] — 時間窓拡張の主対象
