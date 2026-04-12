# MFE=0 Instant Death Analysis

## Core Finding
**90.6% of LOSS trades have MFE=0** -- they NEVER go favorable before hitting SL.
This is NOT an SL width problem. It is an **entry direction/timing problem**.

## By Strategy (503 closed trades, non-shadow)
| Strategy | Losses | MFE=0 | Rate | Avg Win MFE | Status |
|----------|--------|-------|------|-------------|--------|
| engulfing_bb | 5 | 5 | **100%** | 2.90 | FORCE_DEMOTED |
| ema_ribbon_ride | 8 | 8 | **100%** | 6.50 | FORCE_DEMOTED |
| inducement_ob | 8 | 8 | **100%** | 0.00 | FORCE_DEMOTED |
| sr_fib_confluence | 20 | 17 | **85%** | 1.02 | FORCE_DEMOTED |
| macdh_reversal | 38 | 32 | **84%** | 1.93 | FORCE_DEMOTED |
| stoch_trend_pullback | 6 | 5 | **83%** | 3.80 | Sentinel |
| dt_bb_rsi_mr | 5 | 4 | **80%** | 13.53 | Sentinel |
| bb_rsi_reversion | 58 | 45 | **77.6%** | 4.17 | PAIR_PROMOTED |
| fib_reversal | 58 | 44 | **75.9%** | 3.57 | Recovery path |
| ema_pullback | 18 | 13 | **72.2%** | 7.33 | FORCE_DEMOTED |
| **vol_momentum_scalp** | **2** | **0** | **0%** | **4.39** | **Benchmark** |

## Root Cause: vol_momentum (0%) vs bb_rsi (77.6%)
| Factor | bb_rsi (77.6%) | vol_momentum (0%) |
|--------|---------------|-------------------|
| Entry timing | Current bar (anticipatory) | Confirmed candle (reactive) |
| Candle confirm | **None** | Close>Open required |
| Environment | Any ADX | ADX>=25 mandatory |
| Momentum | Stoch K>D (weak) | DI gap>=8 (strong) |

## v8.3 Fixes Applied
- bb_rsi: confirmation candle + counter-trend block + ADX<15 floor
- fib_reversal: MACD-H required + Fib hierarchy + body 0.60
- ema_pullback: bounce ATR*0.2 + triple confirmation + body 0.35
- **Expected**: 77% -> 20-25% (bb_rsi), OOS verification pending

## Related
- [[bb-rsi-reversion]]
- [[fib-reversal]]
- [[vol-momentum-scalp]] (benchmark: 0% instant death)
