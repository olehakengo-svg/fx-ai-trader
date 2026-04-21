# Task 1 DEEP — Shadow TP-hit 条件詳細分析 (クオンツ再集計)

**As of**: 2026-04-21 (UTC), **Scope**: Shadow only (is_shadow=1), XAU 除外, outcome ∈ {WIN, LOSS}

- N_total = 1711, W = 474, baseline WR = **27.70%**
- Distinct strategies = 44
- Cutoff = 2026-04-16 (v9.2.1 regime populated)
- Bonferroni: M = 44 strats × 6 pairs × 4 sessions × 2 dirs = **2112 cells**
- Bonferroni α = 0.05/2112 = **2.37e-05**

**凡例**: N=trades, WR=勝率, PF=profit factor (Σwin_pips/|Σloss_pips|), EV=平均pips/trade, Payoff=avg_win/avg_loss, Kelly=f*=WR-(1-WR)/payoff, Wilson=95% CI下限, Lift=WR_cell/WR_strat_base, p_F=Fisher exact p, WF=walk-forward pre/post Cutoff

---

## ema_trend_scalp (L1: N=295, W=69, L=226, WR=23.4%, PF=0.58, EV=-1.33pips, Payoff=1.91, Kelly=-16.7%)

- Walk-forward: pre-Cutoff N=63 WR=27.0% | post-Cutoff N=232 WR=22.4%

### ema_trend_scalp — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| GBP_USD×london×BUY | 6 | 50.0% | 18.8% | 2.14x | 1.97 | +2.30 | 1.97 | 24.6% | 67%(3)/33%(3) | 0.1427 | ✗ |
| EUR_USD×tokyo×SELL | 9 | 44.4% | 18.9% | 1.90x | 1.50 | +0.93 | 1.87 | 14.8% | 0%(3)/67%(6) | 0.2211 | ✗ |
| EUR_USD×london×BUY | 25 | 36.0% | 20.2% | 1.54x | 1.18 | +0.36 | 2.09 | 5.4% | 50%(12)/23%(13) | 0.1386 | ✗ |
| GBP_USD×ny×SELL | 3 | 33.3% | 6.1% | 1.43x | 1.07 | +0.23 | 2.15 | 2.3% | 0%(0)/33%(3) | - | ✗ |
| USD_JPY×tokyo×SELL | 25 | 32.0% | 17.2% | 1.37x | 1.07 | +0.17 | 2.28 | 2.1% | 50%(4)/29%(21) | 0.3233 | ✗ |
| EUR_USD×ny×SELL | 20 | 30.0% | 14.5% | 1.28x | 0.73 | -0.70 | 1.71 | -10.9% | 33%(3)/29%(17) | 0.4266 | ✗ |
| USD_JPY×london×BUY | 24 | 29.2% | 14.9% | 1.25x | 0.66 | -0.93 | 1.61 | -14.7% | 20%(5)/32%(19) | 0.4595 | ✗ |
| USD_JPY×ny×SELL | 32 | 28.1% | 15.6% | 1.20x | 0.90 | -0.38 | 2.30 | -3.1% | 50%(4)/25%(28) | 0.5102 | ✗ |
| EUR_USD×tokyo×BUY | 9 | 22.2% | 6.3% | 0.95x | 0.45 | -1.46 | 1.57 | -27.5% | 25%(4)/20%(5) | 1.0000 | ✗ |
| EUR_USD×ny×BUY | 28 | 21.4% | 10.2% | 0.92x | 0.38 | -2.25 | 1.40 | -34.8% | 20%(10)/22%(18) | 1.0000 | ✗ |
| USD_JPY×ny×BUY | 31 | 19.4% | 9.2% | 0.83x | 0.47 | -1.77 | 1.97 | -21.7% | 0%(4)/22%(27) | 0.6599 | ✗ |
| USD_JPY×london×SELL | 16 | 18.8% | 6.6% | 0.80x | 0.45 | -1.46 | 1.95 | -22.9% | 0%(2)/21%(14) | 0.7709 | ✗ |
| GBP_USD×ny×BUY | 23 | 13.0% | 4.5% | 0.56x | 0.36 | -3.20 | 2.40 | -23.2% | 0%(6)/18%(17) | 0.3072 | ✗ |
| EUR_USD×london×SELL | 11 | 9.1% | 1.6% | 0.39x | 0.18 | -2.26 | 1.78 | -41.9% | 0%(2)/11%(9) | 0.4675 | ✗ |
| USD_JPY×tokyo×BUY | 14 | 7.1% | 1.3% | 0.31x | 0.13 | -3.49 | 1.63 | -49.8% | 0%(1)/8%(13) | 0.2008 | ✗ |
| GBP_USD×tokyo×SELL | 11 | 0.0% | 0.0% | 0.00x | 0.00 | -4.68 | 0.00 | -100.0% | 0%(0)/0%(11) | 0.0731 | ✗ |
| GBP_USD×london×SELL | 8 | 0.0% | 0.0% | 0.00x | 0.00 | -3.45 | 0.00 | -100.0% | 0%(0)/0%(8) | 0.2050 | ✗ |

#### Hour-level clustering inside top cell [EUR_USD×london×BUY]

| Hour UTC | N | W | WR |
|---:|---:|---:|---:|
| 08 | 8 | 2 | 25.0% |
| 09 | 4 | 1 | 25.0% |
| 10 | 1 | 0 | 0.0% |
| 11 | 4 | 2 | 50.0% |
| 12 | 8 | 4 | 50.0% |

---

## fib_reversal (L1: N=187, W=66, L=121, WR=35.3%, PF=0.68, EV=-0.73pips, Payoff=1.24, Kelly=-16.7%)

- Walk-forward: pre-Cutoff N=129 WR=38.8% | post-Cutoff N=58 WR=27.6%

### fib_reversal — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×london×BUY | 12 | 58.3% | 32.0% | 1.65x | 1.95 | +1.30 | 1.39 | 28.3% | 56%(9)/67%(3) | 0.1172 | ✗ |
| EUR_USD×ny×SELL | 11 | 45.5% | 21.3% | 1.29x | 0.64 | -0.53 | 0.77 | -25.3% | 44%(9)/50%(2) | 0.5225 | ✗ |
| EUR_USD×tokyo×BUY | 14 | 42.9% | 21.4% | 1.21x | 0.94 | -0.10 | 1.26 | -2.6% | 46%(13)/0%(1) | 0.5686 | ✗ |
| EUR_USD×london×BUY | 14 | 42.9% | 21.4% | 1.21x | 0.64 | -0.68 | 0.85 | -24.4% | 55%(11)/0%(3) | 0.5686 | ✗ |
| USD_JPY×tokyo×SELL | 22 | 40.9% | 23.3% | 1.16x | 1.18 | +0.40 | 1.71 | 6.4% | 50%(16)/17%(6) | 0.6363 | ✗ |
| USD_JPY×ny×BUY | 23 | 34.8% | 18.8% | 0.99x | 0.61 | -0.91 | 1.14 | -22.5% | 24%(17)/67%(6) | 1.0000 | ✗ |
| EUR_USD×london×SELL | 15 | 33.3% | 15.2% | 0.94x | 0.38 | -1.15 | 0.77 | -53.6% | 40%(10)/20%(5) | 1.0000 | ✗ |
| EUR_USD×ny×BUY | 16 | 31.2% | 14.2% | 0.89x | 0.64 | -0.86 | 1.42 | -17.3% | 40%(10)/17%(6) | 0.7918 | ✗ |
| USD_JPY×ny×SELL | 24 | 29.2% | 14.9% | 0.83x | 0.59 | -1.05 | 1.44 | -20.1% | 33%(15)/22%(9) | 0.6484 | ✗ |
| USD_JPY×tokyo×BUY | 17 | 23.5% | 9.6% | 0.67x | 0.49 | -1.42 | 1.58 | -24.8% | 25%(8)/22%(9) | 0.4255 | ✗ |
| USD_JPY×london×SELL | 11 | 18.2% | 5.1% | 0.52x | 0.18 | -3.15 | 0.80 | -83.9% | 33%(6)/0%(5) | 0.3332 | ✗ |
| EUR_USD×tokyo×SELL | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -1.80 | 0.00 | -100.0% | 0%(4)/0%(0) | - | ✗ |

#### Hour-level clustering inside top cell [USD_JPY×london×BUY]

| Hour UTC | N | W | WR |
|---:|---:|---:|---:|
| 08 | 2 | 1 | 50.0% |
| 09 | 2 | 1 | 50.0% |
| 10 | 2 | 2 | 100.0% |
| 11 | 3 | 2 | 66.7% |
| 12 | 3 | 1 | 33.3% |

---

## stoch_trend_pullback (L1: N=142, W=41, L=101, WR=28.9%, PF=0.64, EV=-0.98pips, Payoff=1.58, Kelly=-16.2%)

- Walk-forward: pre-Cutoff N=75 WR=32.0% | post-Cutoff N=67 WR=25.4%

### stoch_trend_pullback — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| EUR_USD×london×BUY | 8 | 50.0% | 21.5% | 1.73x | 1.63 | +0.97 | 1.63 | 19.4% | 43%(7)/100%(1) | 0.2282 | ✗ |
| USD_JPY×london×BUY | 7 | 42.9% | 15.8% | 1.48x | 1.23 | +0.43 | 1.64 | 8.0% | 33%(6)/100%(1) | 0.4118 | ✗ |
| USD_JPY×tokyo×BUY | 17 | 41.2% | 21.6% | 1.43x | 1.30 | +0.49 | 1.86 | 9.5% | 38%(8)/44%(9) | 0.2593 | ✗ |
| EUR_USD×ny×SELL | 5 | 40.0% | 11.8% | 1.39x | 1.17 | +0.40 | 1.76 | 5.9% | 33%(3)/50%(2) | 0.6264 | ✗ |
| USD_JPY×london×SELL | 11 | 36.4% | 15.2% | 1.26x | 1.23 | +0.44 | 2.16 | 6.9% | 25%(8)/67%(3) | 0.7297 | ✗ |
| USD_JPY×ny×BUY | 26 | 30.8% | 16.5% | 1.07x | 0.71 | -0.60 | 1.60 | -12.5% | 38%(13)/23%(13) | 0.8139 | ✗ |
| USD_JPY×tokyo×SELL | 19 | 26.3% | 11.8% | 0.91x | 0.68 | -0.92 | 1.90 | -12.4% | 57%(7)/8%(12) | 1.0000 | ✗ |
| EUR_USD×ny×BUY | 5 | 20.0% | 3.6% | 0.69x | 0.38 | -1.50 | 1.52 | -32.6% | 33%(3)/0%(2) | 1.0000 | ✗ |
| USD_JPY×ny×SELL | 25 | 12.0% | 4.2% | 0.42x | 0.13 | -4.11 | 0.94 | -81.2% | 18%(11)/7%(14) | 0.0511 | ✗ |
| GBP_USD×ny×SELL | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -4.75 | 0.00 | -100.0% | 0%(1)/0%(3) | - | ✗ |
| EUR_USD×london×SELL | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -3.15 | 0.00 | -100.0% | 0%(3)/0%(1) | - | ✗ |
| GBP_USD×ny×BUY | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -6.20 | 0.00 | -100.0% | 0%(1)/0%(2) | - | ✗ |

#### Hour-level clustering inside top cell [USD_JPY×tokyo×BUY]

| Hour UTC | N | W | WR |
|---:|---:|---:|---:|
| 00 | 1 | 1 | 100.0% |
| 01 | 2 | 1 | 50.0% |
| 02 | 3 | 1 | 33.3% |
| 03 | 3 | 1 | 33.3% |
| 04 | 1 | 1 | 100.0% |
| 05 | 2 | 1 | 50.0% |
| 06 | 4 | 1 | 25.0% |
| 07 | 1 | 0 | 0.0% |

---

## bb_rsi_reversion (L1: N=128, W=37, L=91, WR=28.9%, PF=0.50, EV=-1.65pips, Payoff=1.23, Kelly=-28.8%)

- Walk-forward: pre-Cutoff N=18 WR=38.9% | post-Cutoff N=110 WR=27.3%

### bb_rsi_reversion — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| EUR_USD×ny×BUY | 5 | 80.0% | 37.6% | 2.77x | 4.68 | +3.90 | 1.17 | 62.9% | 0%(0)/80%(5) | 0.0244 | ✗ |
| USD_JPY×london×BUY | 3 | 66.7% | 20.8% | 2.31x | 3.30 | +2.83 | 1.65 | 46.4% | 0%(0)/67%(3) | - | ✗ |
| GBP_USD×ny×SELL | 6 | 50.0% | 18.8% | 1.73x | 1.36 | +1.00 | 1.36 | 13.3% | 50%(4)/50%(2) | 0.3546 | ✗ |
| EUR_USD×ny×SELL | 7 | 42.9% | 15.8% | 1.48x | 0.72 | -0.80 | 0.96 | -16.6% | 50%(2)/40%(5) | 0.4114 | ✗ |
| USD_JPY×ny×BUY | 15 | 40.0% | 19.8% | 1.38x | 0.71 | -0.77 | 1.06 | -16.5% | 33%(3)/42%(12) | 0.3661 | ✗ |
| USD_JPY×ny×SELL | 33 | 30.3% | 17.4% | 1.05x | 0.53 | -1.83 | 1.21 | -27.4% | 67%(3)/27%(30) | 0.8271 | ✗ |
| USD_JPY×tokyo×BUY | 18 | 22.2% | 9.0% | 0.77x | 0.43 | -1.67 | 1.50 | -29.5% | 0%(1)/24%(17) | 0.5862 | ✗ |
| USD_JPY×london×SELL | 9 | 22.2% | 6.3% | 0.77x | 0.25 | -2.37 | 0.88 | -65.7% | 0%(2)/29%(7) | 1.0000 | ✗ |
| USD_JPY×tokyo×SELL | 12 | 8.3% | 1.5% | 0.29x | 0.05 | -3.60 | 0.58 | -150.0% | 0%(0)/8%(12) | 0.1776 | ✗ |
| EUR_USD×london×SELL | 11 | 0.0% | 0.0% | 0.00x | 0.00 | -3.49 | 0.00 | -100.0% | 0%(1)/0%(10) | 0.0329 | ✗ |

#### Hour-level clustering inside top cell [USD_JPY×ny×BUY]

| Hour UTC | N | W | WR |
|---:|---:|---:|---:|
| 13 | 2 | 0 | 0.0% |
| 14 | 2 | 2 | 100.0% |
| 15 | 1 | 1 | 100.0% |
| 16 | 4 | 1 | 25.0% |
| 17 | 1 | 0 | 0.0% |
| 18 | 1 | 0 | 0.0% |
| 19 | 2 | 1 | 50.0% |
| 20 | 2 | 1 | 50.0% |

---

## sr_channel_reversal (L1: N=126, W=30, L=96, WR=23.8%, PF=0.50, EV=-1.43pips, Payoff=1.60, Kelly=-23.9%)

- Walk-forward: pre-Cutoff N=70 WR=20.0% | post-Cutoff N=56 WR=28.6%

### sr_channel_reversal — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| GBP_USD×ny×BUY | 4 | 50.0% | 15.0% | 2.10x | 1.45 | +1.60 | 1.45 | 15.6% | 100%(1)/33%(3) | - | ✗ |
| GBP_USD×ny×SELL | 6 | 33.3% | 9.7% | 1.40x | 1.18 | +0.47 | 2.37 | 5.2% | 33%(3)/33%(3) | 0.6277 | ✗ |
| EUR_USD×ny×BUY | 6 | 33.3% | 9.7% | 1.40x | 1.30 | +0.50 | 2.59 | 7.6% | 50%(2)/25%(4) | 0.6277 | ✗ |
| USD_JPY×ny×BUY | 13 | 30.8% | 12.7% | 1.29x | 0.39 | -1.65 | 0.89 | -47.3% | 29%(7)/33%(6) | 0.5071 | ✗ |
| USD_JPY×london×BUY | 13 | 30.8% | 12.7% | 1.29x | 0.71 | -0.85 | 1.60 | -12.4% | 22%(9)/50%(4) | 0.5071 | ✗ |
| USD_JPY×ny×SELL | 7 | 28.6% | 8.2% | 1.20x | 0.75 | -0.73 | 1.87 | -9.6% | 0%(3)/50%(4) | 0.6706 | ✗ |
| USD_JPY×london×SELL | 19 | 26.3% | 11.8% | 1.11x | 0.54 | -1.15 | 1.50 | -22.8% | 18%(11)/38%(8) | 0.7745 | ✗ |
| EUR_USD×ny×SELL | 10 | 20.0% | 5.7% | 0.84x | 0.33 | -2.14 | 1.31 | -41.2% | 22%(9)/0%(1) | 1.0000 | ✗ |
| USD_JPY×tokyo×SELL | 16 | 18.8% | 6.6% | 0.79x | 0.25 | -2.12 | 1.08 | -56.8% | 11%(9)/29%(7) | 0.7602 | ✗ |
| USD_JPY×tokyo×BUY | 15 | 13.3% | 3.7% | 0.56x | 0.16 | -2.43 | 1.03 | -70.5% | 25%(8)/0%(7) | 0.5187 | ✗ |
| EUR_USD×london×SELL | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -4.20 | 0.00 | -100.0% | 0%(4)/0%(0) | - | ✗ |
| EUR_USD×london×BUY | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -2.37 | 0.00 | -100.0% | 0%(1)/0%(2) | - | ✗ |

#### Hour-level clustering inside top cell [USD_JPY×ny×BUY]

| Hour UTC | N | W | WR |
|---:|---:|---:|---:|
| 13 | 3 | 1 | 33.3% |
| 14 | 1 | 1 | 100.0% |
| 15 | 2 | 0 | 0.0% |
| 16 | 2 | 0 | 0.0% |
| 17 | 2 | 0 | 0.0% |
| 18 | 1 | 1 | 100.0% |
| 19 | 1 | 1 | 100.0% |
| 21 | 1 | 0 | 0.0% |

---

## macdh_reversal (L1: N=109, W=30, L=79, WR=27.5%, PF=0.39, EV=-1.47pips, Payoff=1.04, Kelly=-42.4%)

- Walk-forward: pre-Cutoff N=86 WR=31.4% | post-Cutoff N=23 WR=13.0%

### macdh_reversal — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| EUR_USD×ny×SELL | 6 | 50.0% | 18.8% | 1.82x | 1.18 | +0.42 | 1.18 | 7.8% | 50%(6)/0%(0) | 0.3434 | ✗ |
| EUR_USD×london×BUY | 9 | 44.4% | 18.9% | 1.61x | 0.53 | -0.79 | 0.67 | -39.0% | 50%(8)/0%(1) | 0.2560 | ✗ |
| USD_JPY×tokyo×SELL | 5 | 40.0% | 11.8% | 1.45x | 0.94 | -0.12 | 1.40 | -2.8% | 25%(4)/100%(1) | 0.6142 | ✗ |
| EUR_USD×london×SELL | 8 | 37.5% | 13.7% | 1.36x | 0.86 | -0.20 | 1.43 | -6.1% | 38%(8)/0%(0) | 0.6817 | ✗ |
| EUR_USD×tokyo×SELL | 8 | 37.5% | 13.7% | 1.36x | 0.24 | -1.49 | 0.40 | -120.6% | 38%(8)/0%(0) | 0.6817 | ✗ |
| USD_JPY×london×SELL | 3 | 33.3% | 6.1% | 1.21x | 1.55 | +0.77 | 3.10 | 11.8% | 0%(2)/100%(1) | - | ✗ |
| USD_JPY×london×BUY | 3 | 33.3% | 6.1% | 1.21x | 0.97 | -0.03 | 1.95 | -0.9% | 33%(3)/0%(0) | - | ✗ |
| USD_JPY×ny×BUY | 22 | 22.7% | 10.1% | 0.83x | 0.24 | -3.08 | 0.82 | -71.2% | 38%(13)/0%(9) | 0.7899 | ✗ |
| USD_JPY×ny×SELL | 15 | 20.0% | 7.0% | 0.73x | 0.32 | -1.66 | 1.29 | -42.2% | 30%(10)/0%(5) | 0.7561 | ✗ |
| EUR_USD×ny×BUY | 10 | 20.0% | 5.7% | 0.73x | 0.25 | -1.31 | 1.01 | -59.5% | 22%(9)/0%(1) | 0.7240 | ✗ |
| USD_JPY×tokyo×BUY | 7 | 14.3% | 2.6% | 0.52x | 0.04 | -2.07 | 0.24 | -345.2% | 17%(6)/0%(1) | 0.6710 | ✗ |
| EUR_USD×tokyo×BUY | 9 | 11.1% | 2.0% | 0.40x | 0.03 | -1.93 | 0.27 | -322.2% | 14%(7)/0%(2) | 0.4395 | ✗ |

#### Hour-level clustering inside top cell [EUR_USD×london×BUY]

| Hour UTC | N | W | WR |
|---:|---:|---:|---:|
| 08 | 2 | 1 | 50.0% |
| 09 | 1 | 1 | 100.0% |
| 10 | 1 | 0 | 0.0% |
| 11 | 2 | 1 | 50.0% |
| 12 | 3 | 1 | 33.3% |

---

## sr_fib_confluence (L1: N=102, W=25, L=77, WR=24.5%, PF=0.39, EV=-4.63pips, Payoff=1.19, Kelly=-39.1%)

- Walk-forward: pre-Cutoff N=60 WR=28.3% | post-Cutoff N=42 WR=19.0%

### sr_fib_confluence — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| GBP_USD×london×BUY | 14 | 50.0% | 26.8% | 2.04x | 1.54 | +2.31 | 1.54 | 17.6% | 67%(6)/38%(8) | 0.0386 | ✗ |
| EUR_USD×london×BUY | 6 | 50.0% | 18.8% | 2.04x | 1.95 | +3.37 | 1.95 | 24.3% | 40%(5)/100%(1) | 0.1556 | ✗ |
| GBP_USD×tokyo×BUY | 6 | 50.0% | 18.8% | 2.04x | 1.42 | +1.30 | 1.42 | 14.8% | 50%(6)/0%(0) | 0.1556 | ✗ |
| EUR_USD×ny×SELL | 4 | 50.0% | 15.0% | 2.04x | 1.22 | +1.05 | 1.22 | 9.1% | 50%(4)/0%(0) | - | ✗ |
| EUR_USD×tokyo×BUY | 4 | 50.0% | 15.0% | 2.04x | 2.15 | +3.60 | 2.15 | 26.8% | 50%(4)/0%(0) | - | ✗ |
| EUR_JPY×tokyo×SELL | 5 | 40.0% | 11.8% | 1.63x | 0.93 | -0.48 | 1.40 | -3.0% | 0%(0)/40%(5) | 0.5938 | ✗ |
| GBP_USD×ny×BUY | 3 | 33.3% | 6.1% | 1.36x | 0.12 | -10.90 | 0.23 | -253.5% | 100%(1)/0%(2) | - | ✗ |
| EUR_JPY×ny×BUY | 3 | 33.3% | 6.1% | 1.36x | 7.50 | +3.47 | 15.00 | 28.9% | 0%(1)/50%(2) | - | ✗ |
| USD_JPY×london×SELL | 4 | 25.0% | 4.6% | 1.02x | 0.19 | -13.53 | 0.57 | -106.5% | 25%(4)/0%(0) | - | ✗ |
| USD_JPY×ny×SELL | 10 | 20.0% | 5.7% | 0.82x | 0.02 | -8.63 | 0.10 | -784.5% | 20%(10)/0%(0) | 1.0000 | ✗ |
| EUR_JPY×tokyo×BUY | 7 | 0.0% | 0.0% | 0.00x | 0.00 | -13.40 | 0.00 | -100.0% | 0%(0)/0%(7) | 0.1895 | ✗ |
| USD_JPY×tokyo×SELL | 6 | 0.0% | 0.0% | 0.00x | 0.00 | -6.20 | 0.00 | -100.0% | 0%(3)/0%(3) | 0.3317 | ✗ |
| EUR_JPY×london×BUY | 5 | 0.0% | 0.0% | 0.00x | 0.00 | -9.84 | 0.00 | -100.0% | 0%(0)/0%(5) | 0.3303 | ✗ |
| EUR_USD×ny×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -13.93 | 0.00 | -100.0% | 0%(1)/0%(3) | - | ✗ |
| USD_JPY×ny×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -7.92 | 0.00 | -100.0% | 0%(4)/0%(0) | - | ✗ |
| GBP_JPY×tokyo×SELL | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -8.63 | 0.00 | -100.0% | 0%(0)/0%(3) | - | ✗ |
| GBP_USD×ny×SELL | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -9.50 | 0.00 | -100.0% | 0%(3)/0%(0) | - | ✗ |
| EUR_USD×london×SELL | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -5.87 | 0.00 | -100.0% | 0%(3)/0%(0) | - | ✗ |

#### Hour-level clustering inside top cell [GBP_USD×london×BUY]

| Hour UTC | N | W | WR |
|---:|---:|---:|---:|
| 08 | 5 | 2 | 40.0% |
| 09 | 2 | 0 | 0.0% |
| 11 | 4 | 2 | 50.0% |
| 12 | 3 | 3 | 100.0% |

---

## engulfing_bb (L1: N=101, W=32, L=69, WR=31.7%, PF=0.86, EV=-0.32pips, Payoff=1.86, Kelly=-5.1%)

- Walk-forward: pre-Cutoff N=52 WR=30.8% | post-Cutoff N=49 WR=32.7%

### engulfing_bb — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| GBP_USD×london×BUY | 3 | 66.7% | 20.8% | 2.10x | 2.60 | +2.50 | 1.30 | 41.0% | 100%(1)/50%(2) | - | ✗ |
| USD_JPY×tokyo×BUY | 10 | 40.0% | 16.8% | 1.26x | 1.22 | +0.40 | 1.83 | 7.2% | 50%(4)/33%(6) | 0.7215 | ✗ |
| EUR_USD×tokyo×SELL | 5 | 40.0% | 11.8% | 1.26x | 2.69 | +2.98 | 4.04 | 25.1% | 67%(3)/0%(2) | 0.6507 | ✗ |
| USD_JPY×ny×SELL | 8 | 37.5% | 13.7% | 1.18x | 0.97 | -0.08 | 1.62 | -1.1% | 67%(3)/20%(5) | 0.7058 | ✗ |
| USD_JPY×tokyo×SELL | 11 | 36.4% | 15.2% | 1.15x | 1.07 | +0.14 | 1.87 | 2.3% | 40%(5)/33%(6) | 0.7391 | ✗ |
| USD_JPY×london×SELL | 6 | 33.3% | 9.7% | 1.05x | 0.95 | -0.08 | 1.89 | -1.9% | 20%(5)/100%(1) | 1.0000 | ✗ |
| GBP_USD×ny×SELL | 3 | 33.3% | 6.1% | 1.05x | 0.89 | -0.40 | 1.79 | -4.0% | 100%(1)/0%(2) | - | ✗ |
| EUR_USD×ny×SELL | 3 | 33.3% | 6.1% | 1.05x | 1.55 | +1.13 | 3.10 | 11.8% | 50%(2)/0%(1) | - | ✗ |
| EUR_USD×london×BUY | 11 | 27.3% | 9.7% | 0.86x | 0.81 | -0.43 | 2.16 | -6.5% | 20%(5)/33%(6) | 1.0000 | ✗ |
| USD_JPY×ny×BUY | 20 | 25.0% | 11.2% | 0.79x | 0.39 | -1.44 | 1.18 | -38.6% | 17%(12)/38%(8) | 0.5957 | ✗ |
| EUR_USD×london×SELL | 5 | 20.0% | 3.6% | 0.63x | 0.42 | -1.36 | 1.69 | -27.2% | 20%(5)/0%(0) | 1.0000 | ✗ |
| USD_JPY×london×BUY | 8 | 12.5% | 2.2% | 0.39x | 0.45 | -1.40 | 3.16 | -15.2% | 0%(3)/20%(5) | 0.4300 | ✗ |
| GBP_USD×london×SELL | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -5.30 | 0.00 | -100.0% | 0%(3)/0%(0) | - | ✗ |

#### Hour-level clustering inside top cell [USD_JPY×tokyo×BUY]

| Hour UTC | N | W | WR |
|---:|---:|---:|---:|
| 00 | 1 | 0 | 0.0% |
| 01 | 1 | 1 | 100.0% |
| 02 | 1 | 1 | 100.0% |
| 03 | 1 | 0 | 0.0% |
| 04 | 1 | 0 | 0.0% |
| 05 | 1 | 0 | 0.0% |
| 06 | 1 | 1 | 100.0% |
| 07 | 3 | 1 | 33.3% |

---

## bb_squeeze_breakout (L1: N=83, W=21, L=62, WR=25.3%, PF=0.93, EV=-0.17pips, Payoff=2.76, Kelly=-1.8%)

- Walk-forward: pre-Cutoff N=29 WR=20.7% | post-Cutoff N=54 WR=27.8%

### bb_squeeze_breakout — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×ny×SELL | 8 | 50.0% | 21.5% | 1.98x | 5.61 | +7.09 | 5.61 | 41.1% | 0%(3)/80%(5) | 0.1069 | ✗ |
| EUR_USD×ny×BUY | 4 | 50.0% | 15.0% | 1.98x | 1.24 | +0.53 | 1.24 | 9.8% | 67%(3)/0%(1) | - | ✗ |
| USD_JPY×ny×BUY | 10 | 40.0% | 16.8% | 1.58x | 1.83 | +1.89 | 2.75 | 18.2% | 0%(1)/44%(9) | 0.2640 | ✗ |
| USD_JPY×tokyo×BUY | 13 | 30.8% | 12.7% | 1.22x | 0.44 | -1.32 | 0.98 | -39.8% | 33%(3)/30%(10) | 0.7297 | ✗ |
| USD_JPY×london×SELL | 11 | 27.3% | 9.7% | 1.08x | 0.87 | -0.31 | 2.33 | -3.9% | 20%(5)/33%(6) | 1.0000 | ✗ |
| USD_JPY×tokyo×SELL | 5 | 20.0% | 3.6% | 0.79x | 0.71 | -0.70 | 2.84 | -8.1% | 33%(3)/0%(2) | 1.0000 | ✗ |
| EUR_USD×london×BUY | 7 | 14.3% | 2.6% | 0.56x | 0.07 | -3.10 | 0.41 | -193.8% | 20%(5)/0%(2) | 0.6727 | ✗ |
| EUR_USD×ny×SELL | 7 | 0.0% | 0.0% | 0.00x | 0.00 | -3.23 | 0.00 | -100.0% | 0%(2)/0%(5) | 0.1831 | ✗ |
| USD_JPY×london×BUY | 6 | 0.0% | 0.0% | 0.00x | 0.00 | -3.68 | 0.00 | -100.0% | 0%(1)/0%(5) | 0.3296 | ✗ |
| EUR_USD×london×SELL | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -2.93 | 0.00 | -100.0% | 0%(1)/0%(2) | - | ✗ |

#### Hour-level clustering inside top cell [USD_JPY×ny×SELL]

| Hour UTC | N | W | WR |
|---:|---:|---:|---:|
| 14 | 3 | 3 | 100.0% |
| 15 | 1 | 1 | 100.0% |
| 16 | 1 | 0 | 0.0% |
| 17 | 1 | 0 | 0.0% |
| 18 | 1 | 0 | 0.0% |
| 19 | 1 | 0 | 0.0% |

---

## ema_cross (L2: N=46, W=16, L=30, WR=34.8%, PF=0.63, EV=-1.97pips, Payoff=1.19, Kelly=-20.2%)

- Walk-forward: pre-Cutoff N=45 WR=35.6% | post-Cutoff N=1 WR=0.0%

### ema_cross — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×ny×SELL | 24 | 50.0% | 31.4% | 1.44x | 1.31 | +1.21 | 1.31 | 11.9% | 50%(24)/0%(0) | 0.0324 | ✗ |
| USD_JPY×london×BUY | 11 | 18.2% | 5.1% | 0.52x | 0.37 | -4.98 | 1.65 | -31.4% | 18%(11)/0%(0) | 0.2822 | ✗ |
| USD_JPY×ny×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -5.55 | 0.00 | -100.0% | 0%(4)/0%(0) | - | ✗ |

---

## vol_surge_detector (L2: N=41, W=10, L=31, WR=24.4%, PF=0.87, EV=-0.40pips, Payoff=2.71, Kelly=-3.5%)

- Walk-forward: pre-Cutoff N=12 WR=25.0% | post-Cutoff N=29 WR=24.1%

### vol_surge_detector — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×london×SELL | 5 | 60.0% | 23.1% | 2.46x | 6.94 | +11.64 | 4.63 | 51.4% | 0%(1)/75%(4) | 0.0835 | ✗ |
| USD_JPY×tokyo×BUY | 9 | 33.3% | 12.1% | 1.37x | 0.65 | -1.00 | 1.30 | -18.1% | 100%(1)/25%(8) | 0.6622 | ✗ |
| EUR_USD×tokyo×BUY | 4 | 25.0% | 4.6% | 1.03x | 0.68 | -0.68 | 2.05 | -11.6% | 33%(3)/0%(1) | - | ✗ |
| USD_JPY×tokyo×SELL | 10 | 10.0% | 1.8% | 0.41x | 0.15 | -3.46 | 1.39 | -54.9% | 0%(2)/12%(8) | 0.4019 | ✗ |
| EUR_USD×ny×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -5.05 | 0.00 | -100.0% | 0%(1)/0%(3) | - | ✗ |

---

## dt_sr_channel_reversal (L2: N=38, W=12, L=26, WR=31.6%, PF=0.56, EV=-1.89pips, Payoff=1.22, Kelly=-24.7%)

- Walk-forward: pre-Cutoff N=19 WR=31.6% | post-Cutoff N=19 WR=31.6%

### dt_sr_channel_reversal — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×london×BUY | 5 | 60.0% | 23.1% | 1.90x | 2.22 | +3.12 | 1.48 | 33.0% | 33%(3)/100%(2) | 0.3007 | ✗ |
| USD_JPY×tokyo×BUY | 4 | 25.0% | 4.6% | 0.79x | 0.10 | -4.72 | 0.29 | -236.2% | 25%(4)/0%(0) | - | ✗ |
| GBP_USD×london×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -5.05 | 0.00 | -100.0% | 0%(0)/0%(4) | - | ✗ |
| EUR_USD×london×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -6.03 | 0.00 | -100.0% | 0%(0)/0%(4) | - | ✗ |
| GBP_USD×ny×SELL | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -2.73 | 0.00 | -100.0% | 0%(3)/0%(0) | - | ✗ |

---

## ema_pullback (L2: N=36, W=13, L=23, WR=36.1%, PF=1.11, EV=+0.20pips, Payoff=1.97, Kelly=3.6%)

- Walk-forward: pre-Cutoff N=35 WR=37.1% | post-Cutoff N=1 WR=0.0%

### ema_pullback — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×ny×SELL | 8 | 62.5% | 30.6% | 1.73x | 2.54 | +2.24 | 1.53 | 37.9% | 62%(8)/0%(0) | 0.1072 | ✗ |
| USD_JPY×ny×BUY | 7 | 42.9% | 15.8% | 1.19x | 2.27 | +1.13 | 3.03 | 24.0% | 43%(7)/0%(0) | 0.6856 | ✗ |
| EUR_USD×ny×SELL | 3 | 33.3% | 6.1% | 0.92x | 0.87 | -0.07 | 1.75 | -4.8% | 33%(3)/0%(0) | - | ✗ |
| USD_JPY×london×SELL | 7 | 28.6% | 8.2% | 0.79x | 0.78 | -0.61 | 1.95 | -8.1% | 33%(6)/0%(1) | 1.0000 | ✗ |
| EUR_USD×london×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -2.40 | 0.00 | -100.0% | 0%(4)/0%(0) | - | ✗ |
| USD_JPY×london×BUY | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -3.53 | 0.00 | -100.0% | 0%(3)/0%(0) | - | ✗ |

---

## dt_bb_rsi_mr (L2: N=35, W=16, L=19, WR=45.7%, PF=1.06, EV=+0.21pips, Payoff=1.26, Kelly=2.7%)

- Walk-forward: pre-Cutoff N=26 WR=46.2% | post-Cutoff N=9 WR=44.4%

### dt_bb_rsi_mr — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| EUR_USD×london×BUY | 4 | 75.0% | 30.1% | 1.64x | 3.65 | +4.50 | 1.22 | 54.4% | 100%(2)/50%(2) | - | ✗ |
| GBP_USD×ny×SELL | 3 | 66.7% | 20.8% | 1.46x | 1.74 | +2.80 | 0.87 | 28.3% | 67%(3)/0%(0) | - | ✗ |
| GBP_USD×tokyo×BUY | 5 | 60.0% | 23.1% | 1.31x | 1.90 | +2.54 | 1.27 | 28.4% | 100%(1)/50%(4) | 0.6418 | ✗ |
| USD_JPY×london×SELL | 6 | 50.0% | 18.8% | 1.09x | 0.96 | -0.10 | 0.96 | -2.1% | 50%(6)/0%(0) | 1.0000 | ✗ |
| GBP_USD×london×BUY | 3 | 33.3% | 6.1% | 0.73x | 0.68 | -1.80 | 1.36 | -15.7% | 100%(1)/0%(2) | - | ✗ |
| USD_JPY×ny×BUY | 4 | 25.0% | 4.6% | 0.55x | 0.75 | -0.75 | 2.24 | -8.5% | 25%(4)/0%(0) | - | ✗ |

---

## sr_break_retest (L2: N=24, W=3, L=21, WR=12.5%, PF=0.23, EV=-7.10pips, Payoff=1.58, Kelly=-43.1%)

- Walk-forward: pre-Cutoff N=11 WR=18.2% | post-Cutoff N=13 WR=7.7%

### sr_break_retest — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×tokyo×BUY | 6 | 16.7% | 3.0% | 1.33x | 0.65 | -1.72 | 3.27 | -8.8% | 0%(1)/20%(5) | 1.0000 | ✗ |
| USD_JPY×london×BUY | 5 | 0.0% | 0.0% | 0.00x | 0.00 | -7.58 | 0.00 | -100.0% | 0%(1)/0%(4) | 1.0000 | ✗ |

---

## trend_rebound (L2: N=22, W=9, L=13, WR=40.9%, PF=1.23, EV=+0.61pips, Payoff=1.78, Kelly=7.7%)

- Walk-forward: pre-Cutoff N=5 WR=40.0% | post-Cutoff N=17 WR=41.2%

### trend_rebound — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×ny×BUY | 3 | 66.7% | 20.8% | 1.63x | 4.29 | +6.90 | 2.14 | 51.1% | 0%(0)/67%(3) | - | ✗ |
| EUR_USD×london×SELL | 3 | 66.7% | 20.8% | 1.63x | 2.67 | +2.17 | 1.33 | 41.7% | 50%(2)/100%(1) | - | ✗ |
| USD_JPY×tokyo×SELL | 3 | 33.3% | 6.1% | 0.81x | 0.87 | -0.30 | 1.74 | -5.1% | 0%(0)/33%(3) | - | ✗ |

---

## dual_sr_bounce (L2: N=22, W=2, L=20, WR=9.1%, PF=0.23, EV=-5.57pips, Payoff=2.32, Kelly=-30.0%)

- Walk-forward: pre-Cutoff N=17 WR=5.9% | post-Cutoff N=5 WR=20.0%

### dual_sr_bounce — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×tokyo×SELL | 3 | 33.3% | 6.1% | 3.67x | 2.10 | +3.73 | 4.20 | 17.4% | 33%(3)/0%(0) | - | ✗ |
| USD_JPY×ny×BUY | 6 | 16.7% | 3.0% | 1.83x | 0.42 | -3.58 | 2.11 | -22.8% | 0%(3)/33%(3) | 0.4805 | ✗ |
| EUR_JPY×ny×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -11.18 | 0.00 | -100.0% | 0%(4)/0%(0) | - | ✗ |
| GBP_USD×ny×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -7.05 | 0.00 | -100.0% | 0%(4)/0%(0) | - | ✗ |

---

## ema200_trend_reversal (L2: N=20, W=8, L=12, WR=40.0%, PF=1.30, EV=+1.36pips, Payoff=1.94, Kelly=9.1%)

- Walk-forward: pre-Cutoff N=3 WR=100.0% | post-Cutoff N=17 WR=29.4%

### ema200_trend_reversal — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×ny×SELL | 6 | 66.7% | 30.0% | 1.67x | 13.70 | +8.47 | 6.85 | 61.8% | 100%(3)/33%(3) | 0.1611 | ✗ |
| USD_JPY×london×BUY | 4 | 50.0% | 15.0% | 1.25x | 1.51 | +2.20 | 1.51 | 16.9% | 0%(0)/50%(4) | - | ✗ |

---

## vol_momentum_scalp (L3: N=19, W=2, L=17, WR=10.5%, PF=0.26, EV=-2.88pips, Payoff=2.23, Kelly=-29.7%)

- Walk-forward: pre-Cutoff N=13 WR=7.7% | post-Cutoff N=6 WR=16.7%

### vol_momentum_scalp — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| GBP_USD×london×BUY | 7 | 14.3% | 2.6% | 1.36x | 0.43 | -1.77 | 2.56 | -19.3% | 14%(7)/0%(0) | 1.0000 | ✗ |
| GBP_USD×ny×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -5.17 | 0.00 | -100.0% | 0%(4)/0%(0) | - | ✗ |

---

## xs_momentum (L3: N=14, W=3, L=11, WR=21.4%, PF=0.69, EV=-2.25pips, Payoff=2.54, Kelly=-9.5%)

- Walk-forward: pre-Cutoff N=14 WR=21.4% | post-Cutoff N=0 WR=0.0%

### xs_momentum — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| GBP_USD×ny×BUY | 6 | 50.0% | 18.8% | 2.33x | 2.87 | +7.70 | 2.87 | 32.6% | 50%(6)/0%(0) | 0.0549 | ✗ |

---

## v_reversal (L3: N=13, W=3, L=10, WR=23.1%, PF=0.41, EV=-2.49pips, Payoff=1.36, Kelly=-33.7%)

- Walk-forward: pre-Cutoff N=2 WR=50.0% | post-Cutoff N=11 WR=18.2%

### v_reversal — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×ny×BUY | 6 | 16.7% | 3.0% | 0.72x | 0.32 | -3.08 | 1.61 | -35.0% | 50%(2)/0%(4) | 1.0000 | ✗ |
| USD_JPY×london×BUY | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -6.77 | 0.00 | -100.0% | 0%(0)/0%(3) | - | ✗ |

---

## vwap_mean_reversion (L3: N=11, W=1, L=10, WR=9.1%, PF=0.39, EV=-4.80pips, Payoff=3.85, Kelly=-14.5%)

- Walk-forward: pre-Cutoff N=1 WR=0.0% | post-Cutoff N=10 WR=10.0%

### vwap_mean_reversion — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×tokyo×BUY | 3 | 0.0% | 0.0% | 0.00x | 0.00 | -0.80 | 0.00 | -100.0% | 0%(0)/0%(3) | - | ✗ |

---

## inducement_ob (L3: N=10, W=1, L=9, WR=10.0%, PF=0.03, EV=-3.36pips, Payoff=0.29, Kelly=-305.5%)

- Walk-forward: pre-Cutoff N=10 WR=10.0% | post-Cutoff N=0 WR=0.0%

### inducement_ob — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| EUR_GBP×ny×BUY | 4 | 0.0% | 0.0% | 0.00x | 0.00 | -5.15 | 0.00 | -100.0% | 0%(4)/0%(0) | - | ✗ |

---

## ema_ribbon_ride (L3: N=10, W=2, L=8, WR=20.0%, PF=0.39, EV=-1.41pips, Payoff=1.58, Kelly=-30.7%)

- Walk-forward: pre-Cutoff N=10 WR=20.0% | post-Cutoff N=0 WR=0.0%

### ema_ribbon_ride — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|

---

## trendline_sweep (L3: N=8, W=3, L=5, WR=37.5%, PF=1.80, EV=+3.55pips, Payoff=3.00, Kelly=16.6%)

- Walk-forward: pre-Cutoff N=7 WR=28.6% | post-Cutoff N=1 WR=100.0%

### trendline_sweep — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|

---

## dt_fib_reversal (L3: N=7, W=2, L=5, WR=28.6%, PF=0.67, EV=-2.30pips, Payoff=1.68, Kelly=-13.9%)

- Walk-forward: pre-Cutoff N=1 WR=0.0% | post-Cutoff N=6 WR=33.3%

### dt_fib_reversal — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|

---

## orb_trap (L3: N=7, W=4, L=3, WR=57.1%, PF=2.41, EV=+5.34pips, Payoff=1.81, Kelly=33.4%)

- Walk-forward: pre-Cutoff N=5 WR=60.0% | post-Cutoff N=2 WR=50.0%

### orb_trap — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|

---

## post_news_vol (L3: N=7, W=4, L=3, WR=57.1%, PF=1.89, EV=+6.09pips, Payoff=1.42, Kelly=26.9%)

- Walk-forward: pre-Cutoff N=5 WR=80.0% | post-Cutoff N=2 WR=0.0%

### post_news_vol — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| GBP_USD×tokyo×BUY | 3 | 33.3% | 6.1% | 0.58x | 0.73 | -3.60 | 1.46 | -12.3% | 100%(1)/0%(2) | - | ✗ |

---

## vix_carry_unwind (L3: N=6, W=2, L=4, WR=33.3%, PF=0.96, EV=-0.47pips, Payoff=1.92, Kelly=-1.4%)

- Walk-forward: pre-Cutoff N=2 WR=100.0% | post-Cutoff N=4 WR=0.0%

### vix_carry_unwind — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×tokyo×SELL | 5 | 20.0% | 3.6% | 0.60x | 0.40 | -8.32 | 1.61 | -29.6% | 100%(1)/0%(4) | - | ✗ |

---

## pivot_breakout (L3: N=5, W=2, L=3, WR=40.0%, PF=0.36, EV=-8.56pips, Payoff=0.53, Kelly=-72.5%)

- Walk-forward: pre-Cutoff N=5 WR=40.0% | post-Cutoff N=0 WR=0.0%

### pivot_breakout — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×ny×BUY | 5 | 40.0% | 11.8% | 1.00x | 0.36 | -8.56 | 0.53 | -72.5% | 40%(5)/0%(0) | - | ✗ |

---

## h1_fib_reversal (L3: N=5, W=1, L=4, WR=20.0%, PF=0.13, EV=-4.18pips, Payoff=0.50, Kelly=-139.3%)

- Walk-forward: pre-Cutoff N=5 WR=20.0% | post-Cutoff N=0 WR=0.0%

### h1_fib_reversal — Cell-level profile (N≥3, sorted by WR desc)

| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|
| USD_JPY×london×SELL | 5 | 20.0% | 3.6% | 1.00x | 0.13 | -4.18 | 0.50 | -139.3% | 20%(5)/0%(0) | - | ✗ |

---


## Bonferroni-significant cells (p < α/M)

α/M = 2.37e-05 (M = 2112 cells)

| Strategy | Cell | N | WR | p_F | ΔWR vs baseline |
|---|---|---:|---:|---:|---:|
| — | — | — | — | — | — |

**結論**: Bonferroni-strict 基準 (α/M=2.37e-05) で有意な cell は **ゼロ**. 全ての 'golden cell' は multiple-testing artifact の可能性.
