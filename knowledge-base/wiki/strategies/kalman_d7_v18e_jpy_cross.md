# Kalman D7 v18e JPY Cross Shadow

## Overview
- **Entry Type**: `kalman_d7_v18e`
- **Category**: TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: Shadow-only, default OFF
- **Active Pairs**: `AUD_JPY`, `EUR_JPY`
- **Rule**: R1 (Slow & Strict)

## Activation
- `KALMAN_D7_V18E_AUDJPY_SHADOW=1` enables AUD_JPY shadow collection.
- `KALMAN_D7_V18E_EURJPY_SHADOW=1` enables EUR_JPY shadow collection.
- This strategy is not registered in `LIVE_PROMOTE_LOSERS` and must not be routed Live by env alone.

## Pre-Registration Lock
- Pair: AUD_JPY, EUR_JPY
- Window: 365d M15 BT with Codex-reviewed Python port
- Stage-0 result:
  - AUD_JPY: N=109, PF=1.097, WR=65.14%, Net=+0.088%, MaxDD=-0.183%
  - EUR_JPY: N=119, PF=1.076, WR=64.71%, Net=+0.049%, MaxDD=-0.154%
- Shadow evidence target: N >= 30 after deployment
- Future Live promote criteria:
  - Wilson 95% lower bound WR >= 0.50
  - Shadow measured PF >= 1.10
  - BH-FDR survivor (m=2, q=0.10)
  - Max DD <= 5%
  - Sharpe > 0
- Retreat criteria:
  - Wilson 95% upper bound WR < 0.50
  - PF < 0.95 after N >= 30
  - 3 consecutive months net negative

## Signal Logic
- LONG-only.
- EMA 25/75/200 perfect-order UP transition.
- DIST: `(close - ema200) / ATR < 3.0`
- GAP: `(ema25 - ema200) / ATR < 3.0`
- ATR percentile gate: P20 <= ATR(14) < P80 over 200 bars.
- RSI(14) < 70.
- UTC session in ASN, LDN, or NY: hour < 7, 7 <= hour < 12, or 16 <= hour < 21.

## Exit Model
- Python signal port tracks the Pine v18e exit model:
  - Dynamic SL = entry - 2.0 * current ATR.
  - Trail activation = entry + 1.0 * current ATR.
  - Trail offset = 0.5 * current ATR.
  - JPY tick quantization uses mintick 0.001.
- Runtime candidate exposes SL/TP for the existing demo/OANDA plumbing; the deployment target is shadow evidence, not Live routing.

## Risk Notes
- PF is marginal at 1.07-1.10, so direct Live promotion is forbidden.
- MASSIVE vs OANDA candle differences may materially affect PF. OANDA direct-fetch re-BT is the next validation task and is not a blocker for shadow-only evidence collection.
- USD_JPY v18e Live wiring is separate and must remain untouched.

## Commit Message Lock
- `feat(kalman_d7): AUDJPY/EURJPY M15 shadow tier port [rule:R1]`
