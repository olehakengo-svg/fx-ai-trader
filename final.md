# final.md

Generated: 2026-05-15T14:10:09.806044+00:00

投入 cell 数: 3744
SHADOW_CANDIDATE 数: 227
CONDITIONAL 数: 15
REJECT 数: 3502
AUDJPY H4 下位5% 48H 実測: WR=60.00% N=315 EV=0.2148% Wilson=0.545 PF=1.55 p=0.008597 BH=0 Verdict=REJECT

## Qiita Reproduction Verification
| Cell | Spec | Qiita Reported | Our BT | Match? |
|---|---|---|---|---|
| AUD_JPY_H4_LONG_SHOCK_5_12_ALL | 下位5% 48H | WR=60.06% N=1369 EV=+0.2024% | WR=60.00% N=315 EV=0.2148% Wilson=0.545 PF=1.55 p=0.008597 BH=0 Verdict=REJECT | fail |
| AUD_JPY_H4_LONG_SHOCK_1_12_ALL | 下位1% 48H | WR=62.32% N=69 EV=+0.3856% | WR=67.21% N=61 EV=0.3011% Wilson=0.547 PF=1.84 p=0.055229 BH=0 Verdict=REJECT | fail |
| USD_JPY_H4_LONG_SHOCK_5_12_ALL | 下位5% 48H | Qiita: 反発弱い | WR=52.96% N=270 EV=0.0474% Wilson=0.470 PF=1.11 p=0.224375 BH=0 Verdict=REJECT | - |
| EUR_USD_H4_LONG_SHOCK_5_12_ALL | 下位5% 48H | Qiita: 値幅小 | WR=49.00% N=249 EV=0.0152% Wilson=0.428 PF=1.05 p=0.362775 BH=0 Verdict=REJECT | - |

## Qiita Reproduction Notes
- AUD_JPY H4 lower-5% 48H has WR/EV close to Qiita (WR 60.00% vs 60.06%, EV 0.2148% vs 0.2024%), but N is 315 vs 1369 (23.0%).
- The N gap is consistent with this BT's pre-registered rolling percentile design: H4 uses a 1512-bar warmup and then selects roughly 5% of eligible bars. Qiita likely used a different thresholding/counting method such as fixed/global percentile or overlapping sample construction.
- AUD_JPY H4 lower-5% 48H is REJECT here because BH-FDR fails (p=0.008597, BH=0) despite passing WR/PF/cost/year-flip gates.

## Top 10 Survivors / Evidence
- EUR_GBP_H1_LONG_SHOCK_1_12_Q5: N=239 WR=0.690 Wilson=0.629 PF=11.43 EV=60.74pip/0.7721% p=0.000003 flips=1 BH=1 Bonf=1
- EUR_GBP_H1_LONG_SHOCK_1_6_Q5: N=239 WR=0.724 Wilson=0.664 PF=12.85 EV=60.41pip/0.7699% p=0.000005 flips=1 BH=1 Bonf=1
- NZD_JPY_H1_LONG_SHOCK_1_12_Q5: N=303 WR=0.640 Wilson=0.585 PF=5.02 EV=58.88pip/0.7193% p=0.000000 flips=1 BH=1 Bonf=1
- EUR_AUD_H1_LONG_SHOCK_1_12_Q5: N=262 WR=0.676 Wilson=0.617 PF=4.05 EV=58.77pip/0.3790% p=0.000000 flips=0 BH=1 Bonf=1
- EUR_GBP_H1_LONG_SHOCK_1_3_Q5: N=239 WR=0.728 Wilson=0.668 PF=14.75 EV=55.81pip/0.7032% p=0.000002 flips=0 BH=1 Bonf=1
- NZD_JPY_H1_LONG_SHOCK_1_6_Q5: N=303 WR=0.620 Wilson=0.565 PF=5.73 EV=55.12pip/0.6738% p=0.000000 flips=0 BH=1 Bonf=1
- NZD_JPY_H1_LONG_SHOCK_1_3_Q5: N=303 WR=0.611 Wilson=0.555 PF=5.28 EV=50.92pip/0.6240% p=0.000000 flips=0 BH=1 Bonf=1
- EUR_JPY_H4_LONG_SHOCK_1_12_ALL: N=67 WR=0.627 Wilson=0.507 PF=2.54 EV=49.68pip/0.3344% p=0.002813 flips=0 BH=1 Bonf=0
- EUR_AUD_H1_LONG_SHOCK_1_6_Q5: N=262 WR=0.603 Wilson=0.543 PF=4.33 EV=49.39pip/0.3173% p=0.000000 flips=1 BH=1 Bonf=1
- EUR_AUD_H4_LONG_SHOCK_5_12_Q3: N=48 WR=0.646 Wilson=0.504 PF=3.43 EV=48.69pip/0.2966% p=0.002305 flips=1 BH=1 Bonf=0

## Skips
- none
