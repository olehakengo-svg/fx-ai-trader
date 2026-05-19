# Family A vs v_reversal-Flipped Ablation

Generated: 2026-05-18T10:36:29.788173+00:00

## Design Diff
| Item | Family A Pure HighVol Continuation | Family B v_reversal flipped |
|---|---|---|
| Entry trigger | `body_t >= K * SMA20_prior(abs(body))` at configured UTC hours | Current v_reversal shock + RSI/BB%B/Stoch reversal trigger |
| Direction | Continuation of signal bar body | Opposite of current v_reversal signal direction |
| Exit | H-bar close time stop | Same H-bar close time stop for comparability |
| Spread | Round-trip spread grid applied to each trade | Same |

## Baseline Spread 0.5 Per-cell Comparison
| K | H | Hourset | A N | A EV | A PF | A Verdict | B N | B EV | B PF | B Verdict |
|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---|
| 2.5 | 3 | AGENT_9_11_15 | 5231 | -0.31 | 0.89 | REJECT | 203 | 1.05 | 1.47 | REJECT |
| 2.5 | 3 | ALL | 51189 | -0.69 | 0.77 | REJECT | 1725 | 0.58 | 1.22 | REJECT |
| 2.5 | 3 | ASIAN_15_22 | 14193 | -1.06 | 0.64 | REJECT | 459 | 0.12 | 1.05 | REJECT |
| 2.5 | 3 | LONDON_07_14 | 18076 | -0.54 | 0.83 | REJECT | 649 | 1.24 | 1.48 | REJECT |
| 2.5 | 3 | NY_12_20 | 17793 | -0.86 | 0.75 | REJECT | 663 | 0.97 | 1.35 | REJECT |
| 2.5 | 6 | AGENT_9_11_15 | 5231 | -0.29 | 0.92 | REJECT | 203 | 1.74 | 1.67 | REJECT |
| 2.5 | 6 | ALL | 51189 | -0.68 | 0.83 | REJECT | 1725 | 0.43 | 1.11 | REJECT |
| 2.5 | 6 | ASIAN_15_22 | 14193 | -1.10 | 0.70 | REJECT | 459 | -0.36 | 0.91 | REJECT |
| 2.5 | 6 | LONDON_07_14 | 18076 | -0.45 | 0.90 | REJECT | 649 | 0.93 | 1.24 | REJECT |
| 2.5 | 6 | NY_12_20 | 17793 | -0.87 | 0.81 | REJECT | 663 | 0.02 | 1.00 | REJECT |
| 2.5 | 12 | AGENT_9_11_15 | 5231 | -0.49 | 0.91 | REJECT | 203 | 0.06 | 1.01 | REJECT |
| 2.5 | 12 | ALL | 51189 | -0.67 | 0.87 | REJECT | 1725 | 0.18 | 1.03 | REJECT |
| 2.5 | 12 | ASIAN_15_22 | 14193 | -1.24 | 0.74 | REJECT | 459 | -1.40 | 0.77 | REJECT |
| 2.5 | 12 | LONDON_07_14 | 18076 | -0.36 | 0.94 | REJECT | 649 | 1.38 | 1.27 | REJECT |
| 2.5 | 12 | NY_12_20 | 17793 | -0.84 | 0.86 | REJECT | 663 | -0.35 | 0.94 | REJECT |
| 3 | 3 | AGENT_9_11_15 | 3066 | -0.16 | 0.94 | REJECT | 203 | 1.05 | 1.47 | REJECT |
| 3 | 3 | ALL | 33362 | -0.70 | 0.78 | REJECT | 1725 | 0.58 | 1.22 | REJECT |
| 3 | 3 | ASIAN_15_22 | 9096 | -1.21 | 0.62 | REJECT | 459 | 0.12 | 1.05 | REJECT |
| 3 | 3 | LONDON_07_14 | 11501 | -0.47 | 0.86 | REJECT | 649 | 1.24 | 1.48 | REJECT |
| 3 | 3 | NY_12_20 | 11315 | -0.89 | 0.76 | REJECT | 663 | 0.97 | 1.35 | REJECT |
| 3 | 6 | AGENT_9_11_15 | 3066 | -0.21 | 0.94 | REJECT | 203 | 1.74 | 1.67 | REJECT |
| 3 | 6 | ALL | 33362 | -0.65 | 0.84 | REJECT | 1725 | 0.43 | 1.11 | REJECT |
| 3 | 6 | ASIAN_15_22 | 9096 | -1.29 | 0.68 | REJECT | 459 | -0.36 | 0.91 | REJECT |
| 3 | 6 | LONDON_07_14 | 11501 | -0.26 | 0.94 | REJECT | 649 | 0.93 | 1.24 | REJECT |
| 3 | 6 | NY_12_20 | 11315 | -0.83 | 0.83 | REJECT | 663 | 0.02 | 1.00 | REJECT |
| 3 | 12 | AGENT_9_11_15 | 3066 | -0.36 | 0.94 | REJECT | 203 | 0.06 | 1.01 | REJECT |
| 3 | 12 | ALL | 33362 | -0.71 | 0.87 | REJECT | 1725 | 0.18 | 1.03 | REJECT |
| 3 | 12 | ASIAN_15_22 | 9096 | -1.51 | 0.71 | REJECT | 459 | -1.40 | 0.77 | REJECT |
| 3 | 12 | LONDON_07_14 | 11501 | -0.22 | 0.96 | REJECT | 649 | 1.38 | 1.27 | REJECT |
| 3 | 12 | NY_12_20 | 11315 | -0.88 | 0.86 | REJECT | 663 | -0.35 | 0.94 | REJECT |
| 3.5 | 3 | AGENT_9_11_15 | 1842 | -0.17 | 0.94 | REJECT | 203 | 1.05 | 1.47 | REJECT |
| 3.5 | 3 | ALL | 22214 | -0.75 | 0.78 | REJECT | 1725 | 0.58 | 1.22 | REJECT |
| 3.5 | 3 | ASIAN_15_22 | 6099 | -1.34 | 0.62 | REJECT | 459 | 0.12 | 1.05 | REJECT |
| 3.5 | 3 | LONDON_07_14 | 7398 | -0.51 | 0.86 | REJECT | 649 | 1.24 | 1.48 | REJECT |
| 3.5 | 3 | NY_12_20 | 7384 | -1.00 | 0.76 | REJECT | 663 | 0.97 | 1.35 | REJECT |
| 3.5 | 6 | AGENT_9_11_15 | 1842 | -0.24 | 0.94 | REJECT | 203 | 1.74 | 1.67 | REJECT |
| 3.5 | 6 | ALL | 22214 | -0.65 | 0.85 | REJECT | 1725 | 0.43 | 1.11 | REJECT |
| 3.5 | 6 | ASIAN_15_22 | 6099 | -1.27 | 0.70 | REJECT | 459 | -0.36 | 0.91 | REJECT |
| 3.5 | 6 | LONDON_07_14 | 7398 | -0.29 | 0.94 | REJECT | 649 | 0.93 | 1.24 | REJECT |
| 3.5 | 6 | NY_12_20 | 7384 | -0.78 | 0.85 | REJECT | 663 | 0.02 | 1.00 | REJECT |
| 3.5 | 12 | AGENT_9_11_15 | 1842 | -0.07 | 0.99 | REJECT | 203 | 0.06 | 1.01 | REJECT |
| 3.5 | 12 | ALL | 22214 | -0.65 | 0.89 | REJECT | 1725 | 0.18 | 1.03 | REJECT |
| 3.5 | 12 | ASIAN_15_22 | 6099 | -1.46 | 0.73 | REJECT | 459 | -1.40 | 0.77 | REJECT |
| 3.5 | 12 | LONDON_07_14 | 7398 | -0.21 | 0.97 | REJECT | 649 | 1.38 | 1.27 | REJECT |
| 3.5 | 12 | NY_12_20 | 7384 | -0.83 | 0.88 | REJECT | 663 | -0.35 | 0.94 | REJECT |
| 4 | 3 | AGENT_9_11_15 | 1121 | 0.03 | 1.01 | REJECT | 203 | 1.05 | 1.47 | REJECT |
| 4 | 3 | ALL | 15172 | -0.69 | 0.81 | REJECT | 1725 | 0.58 | 1.22 | REJECT |
| 4 | 3 | ASIAN_15_22 | 4201 | -1.47 | 0.62 | REJECT | 459 | 0.12 | 1.05 | REJECT |
| 4 | 3 | LONDON_07_14 | 4960 | -0.35 | 0.91 | REJECT | 649 | 1.24 | 1.48 | REJECT |
| 4 | 3 | NY_12_20 | 5085 | -0.99 | 0.78 | REJECT | 663 | 0.97 | 1.35 | REJECT |
| 4 | 6 | AGENT_9_11_15 | 1121 | -0.29 | 0.93 | REJECT | 203 | 1.74 | 1.67 | REJECT |
| 4 | 6 | ALL | 15172 | -0.61 | 0.87 | REJECT | 1725 | 0.43 | 1.11 | REJECT |
| 4 | 6 | ASIAN_15_22 | 4201 | -1.41 | 0.69 | REJECT | 459 | -0.36 | 0.91 | REJECT |
| 4 | 6 | LONDON_07_14 | 4960 | -0.07 | 0.99 | REJECT | 649 | 0.93 | 1.24 | REJECT |
| 4 | 6 | NY_12_20 | 5085 | -0.69 | 0.87 | REJECT | 663 | 0.02 | 1.00 | REJECT |
| 4 | 12 | AGENT_9_11_15 | 1121 | 0.02 | 1.00 | REJECT | 203 | 0.06 | 1.01 | REJECT |
| 4 | 12 | ALL | 15172 | -0.54 | 0.91 | REJECT | 1725 | 0.18 | 1.03 | REJECT |
| 4 | 12 | ASIAN_15_22 | 4201 | -1.61 | 0.72 | REJECT | 459 | -1.40 | 0.77 | REJECT |
| 4 | 12 | LONDON_07_14 | 4960 | 0.12 | 1.02 | REJECT | 649 | 1.38 | 1.27 | REJECT |
| 4 | 12 | NY_12_20 | 5085 | -0.71 | 0.90 | REJECT | 663 | -0.35 | 0.94 | REJECT |
| 4.5 | 3 | AGENT_9_11_15 | 735 | 0.18 | 1.06 | REJECT | 203 | 1.05 | 1.47 | REJECT |
| 4.5 | 3 | ALL | 10672 | -0.83 | 0.79 | REJECT | 1725 | 0.58 | 1.22 | REJECT |
| 4.5 | 3 | ASIAN_15_22 | 3025 | -1.81 | 0.58 | REJECT | 459 | 0.12 | 1.05 | REJECT |
| 4.5 | 3 | LONDON_07_14 | 3444 | -0.37 | 0.91 | REJECT | 649 | 1.24 | 1.48 | REJECT |
| 4.5 | 3 | NY_12_20 | 3623 | -1.14 | 0.77 | REJECT | 663 | 0.97 | 1.35 | REJECT |
| 4.5 | 6 | AGENT_9_11_15 | 735 | -0.36 | 0.92 | REJECT | 203 | 1.74 | 1.67 | REJECT |
| 4.5 | 6 | ALL | 10672 | -0.75 | 0.85 | REJECT | 1725 | 0.43 | 1.11 | REJECT |
| 4.5 | 6 | ASIAN_15_22 | 3025 | -1.75 | 0.65 | REJECT | 459 | -0.36 | 0.91 | REJECT |
| 4.5 | 6 | LONDON_07_14 | 3444 | -0.06 | 0.99 | REJECT | 649 | 0.93 | 1.24 | REJECT |
| 4.5 | 6 | NY_12_20 | 3623 | -0.81 | 0.87 | REJECT | 663 | 0.02 | 1.00 | REJECT |
| 4.5 | 12 | AGENT_9_11_15 | 735 | 0.59 | 1.10 | REJECT | 203 | 0.06 | 1.01 | REJECT |
| 4.5 | 12 | ALL | 10672 | -0.63 | 0.90 | REJECT | 1725 | 0.18 | 1.03 | REJECT |
| 4.5 | 12 | ASIAN_15_22 | 3025 | -1.83 | 0.70 | REJECT | 459 | -1.40 | 0.77 | REJECT |
| 4.5 | 12 | LONDON_07_14 | 3444 | 0.25 | 1.04 | REJECT | 649 | 1.38 | 1.27 | REJECT |
| 4.5 | 12 | NY_12_20 | 3623 | -0.71 | 0.91 | REJECT | 663 | -0.35 | 0.94 | REJECT |
