# Price Shock Reversion Grid SUMMARY

Generated: 2026-05-15T08:24:34.034053+00:00

## Verdict
🔴 **NO-GO / hypothesis kill pending commander review**

## Rec
- **Generated cells**: 864
- **SHADOW_CANDIDATE**: 0
- **CONDITIONAL**: 0
- **REJECT**: 864
- **Loaded pair/TF**: 6
- **Skipped pair/TF**: 21

## Evidence
- **EUR_JPY_H1_LONG_SHOCK_1_12_Q2: N=2 WR=1.000 Wilson=0.342 PF=inf EV=62.85pip/0.3650% p=0.130498 flips=0 BH=0 Bonf=0**
- **USD_JPY_H1_LONG_SHOCK_1_12_Q2: N=3 WR=0.667 Wilson=0.208 PF=2.21 EV=27.87pip/0.1660% p=0.329610 flips=1 BH=0 Bonf=0**
- **EUR_USD_H1_SHORT_SHOCK_2p5_12_Q1: N=1 WR=1.000 Wilson=0.207 PF=inf EV=27.20pip/0.2315% p=1.000000 flips=0 BH=0 Bonf=0**
- **EUR_USD_H1_SHORT_SHOCK_2p5_6_Q1: N=1 WR=1.000 Wilson=0.207 PF=inf EV=24.00pip/0.2042% p=1.000000 flips=0 BH=0 Bonf=0**
- **GBP_JPY_H1_LONG_SHOCK_1_12_Q4: N=15 WR=0.733 Wilson=0.480 PF=3.19 EV=22.82pip/0.1105% p=0.056206 flips=0 BH=0 Bonf=0**
- **USD_JPY_H1_LONG_SHOCK_1_1_Q2: N=3 WR=1.000 Wilson=0.439 PF=inf EV=22.03pip/0.1463% p=0.031496 flips=0 BH=0 Bonf=0**
- **GBP_JPY_H1_LONG_SHOCK_1_6_Q4: N=15 WR=0.733 Wilson=0.480 PF=7.03 EV=20.83pip/0.0999% p=0.006430 flips=0 BH=0 Bonf=0**
- **GBP_JPY_H1_LONG_SHOCK_1_12_Q2: N=3 WR=0.667 Wilson=0.208 PF=2.18 EV=20.73pip/0.1033% p=0.312750 flips=1 BH=0 Bonf=0**
- **EUR_USD_H1_LONG_SHOCK_1_3_Q1: N=1 WR=1.000 Wilson=0.207 PF=inf EV=20.00pip/0.1704% p=1.000000 flips=0 BH=0 Bonf=0**
- **EUR_USD_H1_SHORT_SHOCK_1_12_Q4: N=18 WR=0.667 Wilson=0.437 PF=6.15 EV=18.53pip/0.1582% p=0.009374 flips=0 BH=0 Bonf=0**

## 思想
価格予測ではなく、価格自身の極値分位後の固定horizon平均回帰を検定した。

## 設計欠陥
現ローカルMASSIVE cacheは指定14 pair x 2 TFを満たしていないため、未存在pair/TFはskipされた。

## 再設計案
post-hoc gate緩和はせず、必要ならMASSIVE H4/欠損pair履歴を補完して同一pre-reg gridを再実行する。
