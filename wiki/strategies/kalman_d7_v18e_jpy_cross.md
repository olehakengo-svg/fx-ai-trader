# Kalman D7 v18e JPY Cross Shadow Card

- Rule: R1 Slow & Strict, shadow tier only.
- Entry type: `kalman_d7_v18e`.
- Pairs: `AUD_JPY`, `EUR_JPY`.
- Timeframe: M15.
- Enable flags: `KALMAN_D7_V18E_AUDJPY_SHADOW=1`, `KALMAN_D7_V18E_EURJPY_SHADOW=1`.
- Default: off. Live tier is not enabled for this entry type.

## Locked Conditions

- 365d BT after corrected Python port:
  - AUDJPY: PF 1.097, N 109, WR 65.14%, Net +0.088%, MaxDD -0.183%.
  - EURJPY: PF 1.076, N 119, WR 64.71%, Net +0.049%, MaxDD -0.154%.
- Shadow accumulation target: N>=30, expected 3-6 months.
- Promotion requires Wilson 95% lower WR >= 0.50, PF >= 1.10, BH-FDR survivor
  with m=2 q=0.10, Max DD <= 5%, Sharpe > 0.
- Retreat if Wilson 95% upper WR < 0.50, PF < 0.95 at N>=30, or 3 months net
  negative.

## Logic

- EMA 25/75/200 perfect-order UP start.
- DIST `(close - ema200) / ATR < 3`.
- GAP `(ema25 - ema200) / ATR < 3`.
- ATR(14) percentile gate P20 <= ATR < P80 over 200 bars.
- RSI(14) < 70.
- UTC sessions: ASN 00-06, LDN 07-11, NY 16-20.
- Exit model for shadow record: initial dynamic stop at entry - 2.0 ATR,
  trail activation at entry + 1.0 ATR, trail offset 0.5 ATR.
- JPY tick quantization: 0.001.

