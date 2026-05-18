# Family A vs v_reversal Ablation

Generated: 2026-05-18T04:51:39.746731+00:00

## Design Diff
| Item | Family A Pure Vol Exhaustion Fade | Family B v_reversal current |
|---|---|---|
| Entry trigger | `body_t >= K * SMA20_prior(abs(body))` on the closed M5 bar | 10-bar pip drop/surge plus RSI, BB%B, Stoch, candle color, body-ratio, and Stoch recovery/rejection |
| K grid usage | Active body-exhaustion threshold | Inert label for one-to-one grid comparison; current v_reversal has no body/SMA K parameter |
| Direction | Fade the signal bar body | Reversal after 10-bar down/up move with confirming reversal candle |
| Exit | TP 1.0*ATR14, SL 1.5*ATR14, H-bar time stop | v_reversal TP 1.5*ATR7, SL 0.7*ATR7 plus recent high/low guard, H-bar time stop for cell comparability |
| Filters | Session only; no MA trend filter | RSI/BB%B/Stoch/MACD score internals; confidence ADX penalty is not part of this vector BT PnL |

## Per-cell Comparison
| K | H | Session | A N | A EV | A PF | A Verdict | B N | B EV | B PF | B Verdict |
|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---|
| 3 | 3 | ALL | 33362 | -2.52 | 0.31 | REJECT | 1725 | -3.30 | 0.27 | REJECT |
| 3 | 3 | ASIAN_15-22_UTC | 9096 | -2.19 | 0.32 | REJECT | 459 | -2.85 | 0.31 | REJECT |
| 3 | 3 | LONDON_07-14_UTC | 11501 | -2.68 | 0.33 | REJECT | 649 | -3.73 | 0.26 | REJECT |
| 3 | 3 | NY_12-20_UTC | 11315 | -2.57 | 0.35 | REJECT | 663 | -3.62 | 0.28 | REJECT |
| 3 | 6 | ALL | 33362 | -2.51 | 0.35 | REJECT | 1725 | -3.39 | 0.34 | REJECT |
| 3 | 6 | ASIAN_15-22_UTC | 9096 | -2.15 | 0.37 | REJECT | 459 | -2.69 | 0.42 | REJECT |
| 3 | 6 | LONDON_07-14_UTC | 11501 | -2.75 | 0.37 | REJECT | 649 | -3.94 | 0.31 | REJECT |
| 3 | 6 | NY_12-20_UTC | 11315 | -2.58 | 0.39 | REJECT | 663 | -3.74 | 0.35 | REJECT |
| 3 | 12 | ALL | 33362 | -2.53 | 0.38 | REJECT | 1725 | -3.28 | 0.39 | REJECT |
| 3 | 12 | ASIAN_15-22_UTC | 9096 | -2.14 | 0.40 | REJECT | 459 | -2.44 | 0.50 | REJECT |
| 3 | 12 | LONDON_07-14_UTC | 11501 | -2.77 | 0.39 | REJECT | 649 | -3.91 | 0.36 | REJECT |
| 3 | 12 | NY_12-20_UTC | 11315 | -2.58 | 0.42 | REJECT | 663 | -3.67 | 0.40 | REJECT |
| 3.5 | 3 | ALL | 22214 | -2.52 | 0.32 | REJECT | 1725 | -3.30 | 0.27 | REJECT |
| 3.5 | 3 | ASIAN_15-22_UTC | 6099 | -2.11 | 0.35 | REJECT | 459 | -2.85 | 0.31 | REJECT |
| 3.5 | 3 | LONDON_07-14_UTC | 7398 | -2.74 | 0.34 | REJECT | 649 | -3.73 | 0.26 | REJECT |
| 3.5 | 3 | NY_12-20_UTC | 7384 | -2.58 | 0.37 | REJECT | 663 | -3.62 | 0.28 | REJECT |
| 3.5 | 6 | ALL | 22214 | -2.53 | 0.36 | REJECT | 1725 | -3.39 | 0.34 | REJECT |
| 3.5 | 6 | ASIAN_15-22_UTC | 6099 | -2.12 | 0.39 | REJECT | 459 | -2.69 | 0.42 | REJECT |
| 3.5 | 6 | LONDON_07-14_UTC | 7398 | -2.81 | 0.38 | REJECT | 649 | -3.94 | 0.31 | REJECT |
| 3.5 | 6 | NY_12-20_UTC | 7384 | -2.64 | 0.40 | REJECT | 663 | -3.74 | 0.35 | REJECT |
| 3.5 | 12 | ALL | 22214 | -2.54 | 0.38 | REJECT | 1725 | -3.28 | 0.39 | REJECT |
| 3.5 | 12 | ASIAN_15-22_UTC | 6099 | -2.11 | 0.41 | REJECT | 459 | -2.44 | 0.50 | REJECT |
| 3.5 | 12 | LONDON_07-14_UTC | 7398 | -2.82 | 0.40 | REJECT | 649 | -3.91 | 0.36 | REJECT |
| 3.5 | 12 | NY_12-20_UTC | 7384 | -2.64 | 0.42 | REJECT | 663 | -3.67 | 0.40 | REJECT |
| 4 | 3 | ALL | 15172 | -2.59 | 0.33 | REJECT | 1725 | -3.30 | 0.27 | REJECT |
| 4 | 3 | ASIAN_15-22_UTC | 4201 | -2.06 | 0.38 | REJECT | 459 | -2.85 | 0.31 | REJECT |
| 4 | 3 | LONDON_07-14_UTC | 4960 | -2.94 | 0.34 | REJECT | 649 | -3.73 | 0.26 | REJECT |
| 4 | 3 | NY_12-20_UTC | 5085 | -2.67 | 0.38 | REJECT | 663 | -3.62 | 0.28 | REJECT |
| 4 | 6 | ALL | 15172 | -2.60 | 0.36 | REJECT | 1725 | -3.39 | 0.34 | REJECT |
| 4 | 6 | ASIAN_15-22_UTC | 4201 | -2.10 | 0.40 | REJECT | 459 | -2.69 | 0.42 | REJECT |
| 4 | 6 | LONDON_07-14_UTC | 4960 | -3.01 | 0.37 | REJECT | 649 | -3.94 | 0.31 | REJECT |
| 4 | 6 | NY_12-20_UTC | 5085 | -2.73 | 0.40 | REJECT | 663 | -3.74 | 0.35 | REJECT |
| 4 | 12 | ALL | 15172 | -2.61 | 0.38 | REJECT | 1725 | -3.28 | 0.39 | REJECT |
| 4 | 12 | ASIAN_15-22_UTC | 4201 | -2.11 | 0.42 | REJECT | 459 | -2.44 | 0.50 | REJECT |
| 4 | 12 | LONDON_07-14_UTC | 4960 | -3.01 | 0.39 | REJECT | 649 | -3.91 | 0.36 | REJECT |
| 4 | 12 | NY_12-20_UTC | 5085 | -2.73 | 0.42 | REJECT | 663 | -3.67 | 0.40 | REJECT |
| 4.5 | 3 | ALL | 10672 | -2.56 | 0.35 | REJECT | 1725 | -3.30 | 0.27 | REJECT |
| 4.5 | 3 | ASIAN_15-22_UTC | 3025 | -1.99 | 0.41 | REJECT | 459 | -2.85 | 0.31 | REJECT |
| 4.5 | 3 | LONDON_07-14_UTC | 3444 | -2.97 | 0.36 | REJECT | 649 | -3.73 | 0.26 | REJECT |
| 4.5 | 3 | NY_12-20_UTC | 3623 | -2.73 | 0.40 | REJECT | 663 | -3.62 | 0.28 | REJECT |
| 4.5 | 6 | ALL | 10672 | -2.58 | 0.38 | REJECT | 1725 | -3.39 | 0.34 | REJECT |
| 4.5 | 6 | ASIAN_15-22_UTC | 3025 | -2.05 | 0.42 | REJECT | 459 | -2.69 | 0.42 | REJECT |
| 4.5 | 6 | LONDON_07-14_UTC | 3444 | -3.04 | 0.38 | REJECT | 649 | -3.94 | 0.31 | REJECT |
| 4.5 | 6 | NY_12-20_UTC | 3623 | -2.79 | 0.41 | REJECT | 663 | -3.74 | 0.35 | REJECT |
| 4.5 | 12 | ALL | 10672 | -2.60 | 0.39 | REJECT | 1725 | -3.28 | 0.39 | REJECT |
| 4.5 | 12 | ASIAN_15-22_UTC | 3025 | -2.09 | 0.44 | REJECT | 459 | -2.44 | 0.50 | REJECT |
| 4.5 | 12 | LONDON_07-14_UTC | 3444 | -3.03 | 0.40 | REJECT | 649 | -3.91 | 0.36 | REJECT |
| 4.5 | 12 | NY_12-20_UTC | 3623 | -2.82 | 0.43 | REJECT | 663 | -3.67 | 0.40 | REJECT |
