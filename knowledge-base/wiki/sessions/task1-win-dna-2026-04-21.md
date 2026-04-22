# Task 1 — WHY did TP-hit trades TP-hit? (WIN DNA analysis)

**As of**: 2026-04-21 (UTC), **Scope**: Shadow only, XAU 除外

- N_total = 1711, W = 474, baseline WR = 27.7%
- Cutoff = 2026-04-16 (WF split)
- Total (strat × feature × value) tests: 1921
- Bonferroni α/M = 2.60e-05

**凡例**: LR = P(feat=v | WIN) / P(feat=v | LOSS); LR>1 ⇒ WIN-enriched
MI = mutual information I(outcome; feature), bits. 高いほど outcome 予測力大
WR|v = P(WIN | feat=v); WF = walk-forward (pre/post cutoff WR|v)

**Global quartile edges**: conf=[53.0, 61.0, 69.0], spread=[0.8, 0.8, 0.8], adx=[20.3, 25.3, 31.7], atr_ratio=[0.95, 1.01, 1.09], close_vs_ema200=[-0.019, 0.001, 0.034]

---

## ema_trend_scalp (N=295, W=69, L=226, WR=23.4%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _conf_q | 0.0242 | 295 |
| instrument | 0.0096 | 295 |
| _hour_band | 0.0089 | 295 |
| _spread_q | 0.0086 | 295 |
| _atr_q | 0.0062 | 295 |
| mtf_gate_action | 0.0062 | 295 |
| _adx_q | 0.0060 | 295 |
| rj_hmm_regime | 0.0059 | 232 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _conf_q = Q3 | 104 | 35 | 33.7% | 1.66 | 37%(35) | 32%(69) | 0.0026 | ✗ |
| _atr_q = Q3 | 71 | 21 | 29.6% | 1.38 | 33%(9) | 29%(62) | 0.1975 | ✗ |
| _adx_q = Q1 | 67 | 20 | 29.9% | 1.39 | 36%(11) | 29%(56) | 0.1886 | ✗ |
| gate_group = mtf_gated | 63 | 18 | 28.6% | 1.31 | -(0) | 29%(63) | 0.3140 | ✗ |
| mtf_gate_action = kept | 46 | 14 | 30.4% | 1.43 | -(0) | 30%(46) | 0.2550 | ✗ |
| mtf_regime = range_wide | 12 | 4 | 33.3% | 1.64 | -(0) | 33%(12) | 0.4846 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _conf_q=Q3 ∧ _atr_q=Q3 | 21 | 11 | 52.4% | 3.60 | 50%(4)/53%(17) | 再現 |
| _conf_q=Q3 ∧ mtf_gate_action=kept | 15 | 8 | 53.3% | 3.74 | -(0)/53%(15) | WF N不足 |
| _atr_q=Q3 ∧ gate_group=mtf_gated | 20 | 9 | 45.0% | 2.68 | -(0)/45%(20) | WF N不足 |
| mtf_gate_action=kept ∧ mtf_regime=range_wide | 4 | 3 | 75.0% | 9.83 | -(0)/75%(4) | WF N不足 |
| _conf_q=Q3 ∧ gate_group=mtf_gated | 21 | 9 | 42.9% | 2.46 | -(0)/43%(21) | WF N不足 |
| _atr_q=Q3 ∧ mtf_gate_action=kept | 16 | 7 | 43.8% | 2.55 | -(0)/44%(16) | WF N不足 |
| gate_group=mtf_gated ∧ mtf_regime=range_wide | 7 | 4 | 57.1% | 4.37 | -(0)/57%(7) | WF N不足 |
| _conf_q=Q3 ∧ mtf_regime=range_wide | 5 | 3 | 60.0% | 4.91 | -(0)/60%(5) | WF N不足 |

---

## fib_reversal (N=187, W=66, L=121, WR=35.3%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _conf_q | 0.0424 | 187 |
| _cvema_q | 0.0375 | 186 |
| _hour_band | 0.0182 | 187 |
| rj_hmm_regime | 0.0175 | 57 |
| mtf_regime | 0.0140 | 187 |
| mtf_vol_state | 0.0140 | 187 |
| mtf_h4_label | 0.0140 | 187 |
| mtf_d1_label | 0.0140 | 187 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _conf_q = Q3 | 80 | 37 | 46.2% | 1.58 | 46%(65) | 47%(15) | 0.0085 | ✗ |
| _cvema_q = Q3 | 28 | 16 | 57.1% | 2.44 | 48%(21) | 86%(7) | 0.0169 | ✗ |
| _hour_band = 08-11 | 40 | 17 | 42.5% | 1.36 | 48%(29) | 27%(11) | 0.3509 | ✗ |
| _adx_q = Q4 | 13 | 6 | 46.2% | 1.57 | 60%(10) | 0%(3) | 0.3869 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 2 features
  - `_conf_q=Q3` — LR=1.58, pre/post WR = 46%(65)/47%(15)
  - `_cvema_q=Q3` — LR=2.44, pre/post WR = 48%(21)/86%(7)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _conf_q=Q3 ∧ _cvema_q=Q3 | 12 | 9 | 75.0% | 5.50 | 67%(9)/100%(3) | 再現 |
| _cvema_q=Q3 ∧ _adx_q=Q4 | 3 | 3 | 100.0% | inf | 100%(3)/-(0) | WF N不足 |
| _conf_q=Q3 ∧ _hour_band=08-11 | 14 | 7 | 50.0% | 1.83 | 50%(12)/50%(2) | WF N不足 |
| _cvema_q=Q3 ∧ _hour_band=08-11 | 10 | 5 | 50.0% | 1.83 | 44%(9)/100%(1) | WF N不足 |

---

## stoch_trend_pullback (N=142, W=41, L=101, WR=28.9%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _atr_q | 0.0578 | 140 |
| mtf_gate_action | 0.0340 | 142 |
| gate_group | 0.0288 | 142 |
| _session | 0.0271 | 142 |
| _hour_band | 0.0255 | 142 |
| mtf_regime | 0.0244 | 142 |
| mtf_vol_state | 0.0244 | 142 |
| mtf_h4_label | 0.0244 | 142 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _atr_q = Q1 | 51 | 23 | 45.1% | 2.02 | 44%(32) | 47%(19) | 0.0020 | ✗ |
| direction = BUY | 71 | 25 | 35.2% | 1.34 | 37%(41) | 33%(30) | 0.1380 | ✗ |
| _session = london | 33 | 14 | 42.4% | 1.82 | 32%(25) | 75%(8) | 0.0778 | ✗ |
| _conf_q = Q2 | 57 | 20 | 35.1% | 1.33 | 38%(40) | 29%(17) | 0.1918 | ✗ |
| _adx_q = Q2 | 41 | 15 | 36.6% | 1.42 | 40%(25) | 31%(16) | 0.2229 | ✗ |
| _cvema_q = Q4 | 38 | 14 | 36.8% | 1.44 | 39%(18) | 35%(20) | 0.2159 | ✗ |
| layer1_dir = bull | 17 | 7 | 41.2% | 1.72 | 43%(14) | 33%(3) | 0.2593 | ✗ |
| _hour_band = 08-11 | 25 | 9 | 36.0% | 1.39 | 33%(21) | 50%(4) | 0.4664 | ✗ |
| _cvema_q = Q3 | 13 | 5 | 38.5% | 1.54 | 44%(9) | 25%(4) | 0.5216 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 1 features
  - `_atr_q=Q1` — LR=2.02, pre/post WR = 44%(32)/47%(19)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _atr_q=Q1 ∧ direction=BUY | 24 | 14 | 58.3% | 3.45 | 60%(15)/56%(9) | 再現 |
| _atr_q=Q1 ∧ _adx_q=Q2 | 20 | 11 | 55.0% | 3.01 | 58%(12)/50%(8) | 再現 |
| _atr_q=Q1 ∧ _conf_q=Q2 | 24 | 12 | 50.0% | 2.46 | 53%(17)/43%(7) | 再現 |
| _atr_q=Q1 ∧ _session=london | 11 | 7 | 63.6% | 4.31 | 50%(8)/100%(3) | 再現 |
| direction=BUY ∧ _conf_q=Q2 | 35 | 15 | 42.9% | 1.85 | 44%(25)/40%(10) | 片側のみ |
| direction=BUY ∧ _session=london | 17 | 9 | 52.9% | 2.77 | 43%(14)/100%(3) | 再現 |
| _conf_q=Q2 ∧ _cvema_q=Q4 | 21 | 10 | 47.6% | 2.24 | 42%(12)/56%(9) | 再現 |
| _atr_q=Q1 ∧ _cvema_q=Q4 | 13 | 7 | 53.8% | 2.87 | 57%(7)/50%(6) | 再現 |

---

## bb_rsi_reversion (N=128, W=37, L=91, WR=28.9%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _session | 0.0410 | 128 |
| _hour_band | 0.0334 | 128 |
| mtf_gate_action | 0.0208 | 128 |
| rj_hmm_regime | 0.0203 | 110 |
| direction | 0.0202 | 128 |
| _adx_q | 0.0181 | 128 |
| _conf_q | 0.0171 | 128 |
| _atr_q | 0.0127 | 128 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _session = ny | 67 | 26 | 38.8% | 1.56 | 50%(12) | 36%(55) | 0.0114 | ✗ |
| direction = BUY | 46 | 18 | 39.1% | 1.58 | 33%(6) | 40%(40) | 0.0685 | ✗ |
| _hour_band = 12-15 | 44 | 17 | 38.6% | 1.55 | 56%(9) | 34%(35) | 0.1009 | ✗ |
| rj_hmm_regime = trending | 51 | 18 | 35.3% | 1.34 | -(0) | 35%(51) | 0.2337 | ✗ |
| _atr_q = Q2 | 36 | 13 | 36.1% | 1.39 | 60%(5) | 32%(31) | 0.2834 | ✗ |
| mtf_regime = range_tight | 26 | 10 | 38.5% | 1.54 | -(0) | 38%(26) | 0.2354 | ✗ |
| mtf_vol_state = squeeze | 26 | 10 | 38.5% | 1.54 | -(0) | 38%(26) | 0.2354 | ✗ |
| mtf_alignment = aligned | 26 | 10 | 38.5% | 1.54 | -(0) | 38%(26) | 0.2354 | ✗ |
| mtf_h4_label = -1 | 26 | 10 | 38.5% | 1.54 | -(0) | 38%(26) | 0.2354 | ✗ |
| mtf_d1_label = 0 | 26 | 10 | 38.5% | 1.54 | -(0) | 38%(26) | 0.2354 | ✗ |
| _adx_q = Q2 | 26 | 10 | 38.5% | 1.54 | 40%(5) | 38%(21) | 0.2354 | ✗ |
| _adx_q = Q3 | 21 | 8 | 38.1% | 1.51 | -(0) | 38%(21) | 0.3063 | ✗ |
| mtf_gate_action = none | 18 | 7 | 38.9% | 1.57 | -(0) | 39%(18) | 0.4002 | ✗ |
| gate_group = label_only | 18 | 7 | 38.9% | 1.57 | -(0) | 39%(18) | 0.4002 | ✗ |
| instrument = EUR_USD | 26 | 9 | 34.6% | 1.30 | 50%(4) | 32%(22) | 0.4760 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 2 features
  - `_session=ny` — LR=1.56, pre/post WR = 50%(12)/36%(55)
  - `_adx_q=Q2` — LR=1.54, pre/post WR = 40%(5)/38%(21)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| direction=BUY ∧ _hour_band=12-15 | 12 | 8 | 66.7% | 4.92 | 100%(1)/64%(11) | WF N不足 |
| _session=ny ∧ _hour_band=12-15 | 34 | 16 | 47.1% | 2.19 | 62%(8)/42%(26) | 再現 |
| direction=BUY ∧ rj_hmm_regime=trending | 20 | 11 | 55.0% | 3.01 | -(0)/55%(20) | WF N不足 |
| _hour_band=12-15 ∧ _atr_q=Q2 | 18 | 10 | 55.6% | 3.07 | 60%(5)/54%(13) | 再現 |
| _session=ny ∧ rj_hmm_regime=trending | 30 | 14 | 46.7% | 2.15 | -(0)/47%(30) | WF N不足 |
| _session=ny ∧ _atr_q=Q2 | 25 | 12 | 48.0% | 2.27 | 75%(4)/43%(21) | 再現 |
| _session=ny ∧ direction=BUY | 21 | 10 | 47.6% | 2.24 | 33%(3)/50%(18) | 片側のみ |
| direction=BUY ∧ _atr_q=Q2 | 13 | 6 | 46.2% | 2.11 | 100%(1)/42%(12) | WF N不足 |

---

## sr_channel_reversal (N=126, W=30, L=96, WR=23.8%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| mtf_alignment | 0.0327 | 126 |
| mtf_gate_action | 0.0275 | 126 |
| _hour_band | 0.0211 | 126 |
| mtf_regime | 0.0180 | 126 |
| mtf_d1_label | 0.0180 | 126 |
| mtf_vol_state | 0.0169 | 126 |
| mtf_h4_label | 0.0169 | 126 |
| gate_group | 0.0167 | 126 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| mtf_alignment = aligned | 28 | 11 | 39.3% | 2.07 | -(0) | 39%(28) | 0.0429 | ✗ |
| mtf_d1_label = 0 | 27 | 10 | 37.0% | 1.88 | -(0) | 37%(27) | 0.0789 | ✗ |
| _session = ny | 46 | 14 | 30.4% | 1.40 | 28%(25) | 33%(21) | 0.1992 | ✗ |
| _cvema_q = Q1 | 27 | 9 | 33.3% | 1.60 | 31%(16) | 36%(11) | 0.2081 | ✗ |
| mtf_gate_action = kept | 15 | 6 | 40.0% | 2.13 | -(0) | 40%(15) | 0.1918 | ✗ |
| _conf_q = Q3 | 32 | 10 | 31.2% | 1.45 | 24%(17) | 40%(15) | 0.3360 | ✗ |
| mtf_regime = range_tight | 19 | 7 | 36.8% | 1.87 | -(0) | 37%(19) | 0.1549 | ✗ |
| mtf_vol_state = squeeze | 19 | 7 | 36.8% | 1.87 | -(0) | 37%(19) | 0.1549 | ✗ |
| mtf_h4_label = -1 | 19 | 7 | 36.8% | 1.87 | -(0) | 37%(19) | 0.1549 | ✗ |
| _atr_q = Q1 | 38 | 11 | 28.9% | 1.30 | 28%(25) | 31%(13) | 0.3728 | ✗ |
| _hour_band = 12-15 | 34 | 10 | 29.4% | 1.33 | 25%(16) | 33%(18) | 0.4798 | ✗ |
| gate_group = mtf_gated | 17 | 6 | 35.3% | 1.75 | -(0) | 35%(17) | 0.2343 | ✗ |
| mtf_gate_action = none | 14 | 5 | 35.7% | 1.78 | -(0) | 36%(14) | 0.3187 | ✗ |
| gate_group = label_only | 14 | 5 | 35.7% | 1.78 | -(0) | 36%(14) | 0.3187 | ✗ |
| _hour_band = 16-19 | 15 | 5 | 33.3% | 1.60 | 36%(11) | 25%(4) | 0.3480 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| mtf_alignment=aligned ∧ _conf_q=Q3 | 7 | 4 | 57.1% | 4.27 | -(0)/57%(7) | WF N不足 |
| mtf_d1_label=0 ∧ _conf_q=Q3 | 7 | 4 | 57.1% | 4.27 | -(0)/57%(7) | WF N不足 |
| _session=ny ∧ _conf_q=Q3 | 11 | 5 | 45.5% | 2.67 | 67%(3)/38%(8) | 片側のみ |
| mtf_alignment=aligned ∧ mtf_gate_action=kept | 15 | 6 | 40.0% | 2.13 | -(0)/40%(15) | WF N不足 |
| mtf_alignment=aligned ∧ _cvema_q=Q1 | 6 | 3 | 50.0% | 3.20 | -(0)/50%(6) | WF N不足 |
| mtf_d1_label=0 ∧ _cvema_q=Q1 | 6 | 3 | 50.0% | 3.20 | -(0)/50%(6) | WF N不足 |
| _session=ny ∧ _cvema_q=Q1 | 10 | 4 | 40.0% | 2.13 | 33%(6)/50%(4) | 片側のみ |

---

## macdh_reversal (N=109, W=30, L=79, WR=27.5%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| rj_hmm_regime | 0.0743 | 23 |
| _cvema_q | 0.0305 | 108 |
| _hour_band | 0.0254 | 109 |
| _atr_q | 0.0220 | 108 |
| _conf_q | 0.0108 | 109 |
| _session | 0.0104 | 109 |
| mtf_regime | 0.0086 | 109 |
| mtf_vol_state | 0.0086 | 109 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _cvema_q = Q3 | 25 | 11 | 44.0% | 2.07 | 44%(25) | -(0) | 0.0439 | ✗ |
| _atr_q = Q4 | 37 | 13 | 35.1% | 1.43 | 41%(32) | 0%(5) | 0.2581 | ✗ |
| _hour_band = 08-11 | 23 | 9 | 39.1% | 1.69 | 37%(19) | 50%(4) | 0.1916 | ✗ |
| _session = london | 27 | 10 | 37.0% | 1.55 | 35%(23) | 50%(4) | 0.2209 | ✗ |
| _atr_q = Q3 | 11 | 4 | 36.4% | 1.50 | 38%(8) | 33%(3) | 0.4906 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 1 features
  - `_hour_band=08-11` — LR=1.69, pre/post WR = 37%(19)/50%(4)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _cvema_q=Q3 ∧ _atr_q=Q4 | 12 | 7 | 58.3% | 3.69 | 58%(12)/-(0) | WF N不足 |
| _atr_q=Q4 ∧ _hour_band=08-11 | 5 | 3 | 60.0% | 3.95 | 60%(5)/-(0) | WF N不足 |
| _atr_q=Q4 ∧ _session=london | 9 | 4 | 44.4% | 2.11 | 44%(9)/-(0) | WF N不足 |

---

## sr_fib_confluence (N=102, W=25, L=77, WR=24.5%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| sr_basis | 0.3186 | 102 |
| rj_hmm_regime | 0.0835 | 40 |
| instrument | 0.0786 | 102 |
| _cvema_q | 0.0672 | 102 |
| _hour_band | 0.0214 | 102 |
| mtf_regime | 0.0203 | 102 |
| mtf_alignment | 0.0203 | 102 |
| mtf_d1_label | 0.0203 | 102 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| sr_basis = 1.342 | 7 | 5 | 71.4% | 7.70 | 71%(7) | -(0) | 0.0092 | ✗ |
| _cvema_q = Q2 | 43 | 16 | 37.2% | 1.83 | 34%(32) | 45%(11) | 0.0187 | ✗ |
| instrument = GBP_USD | 26 | 11 | 42.3% | 2.26 | 50%(16) | 30%(10) | 0.0193 | ✗ |
| _session = london | 35 | 11 | 31.4% | 1.41 | 33%(21) | 29%(14) | 0.3321 | ✗ |
| _adx_q = Q2 | 40 | 12 | 30.0% | 1.32 | 25%(24) | 38%(16) | 0.3495 | ✗ |
| _hour_band = 12-15 | 28 | 9 | 32.1% | 1.46 | 40%(20) | 12%(8) | 0.3068 | ✗ |
| sr_basis = 1.322 | 6 | 3 | 50.0% | 3.08 | 50%(6) | -(0) | 0.1556 | ✗ |
| instrument = EUR_USD | 22 | 7 | 31.8% | 1.44 | 33%(18) | 25%(4) | 0.4063 | ✗ |
| _atr_q = Q2 | 23 | 7 | 30.4% | 1.35 | 27%(11) | 33%(12) | 0.5820 | ✗ |
| _conf_q = Q2 | 16 | 5 | 31.2% | 1.40 | 36%(14) | 0%(2) | 0.5321 | ✗ |
| sr_basis = 1.35 | 8 | 3 | 37.5% | 1.85 | -(0) | 38%(8) | 0.4015 | ✗ |
| _cvema_q = Q3 | 10 | 3 | 30.0% | 1.32 | 60%(5) | 0%(5) | 0.7036 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| sr_basis=1.342 ∧ _adx_q=Q2 | 3 | 3 | 100.0% | inf | 100%(3)/-(0) | WF N不足 |
| sr_basis=1.342 ∧ _hour_band=12-15 | 3 | 3 | 100.0% | inf | 100%(3)/-(0) | WF N不足 |
| sr_basis=1.342 ∧ instrument=GBP_USD | 7 | 5 | 71.4% | 7.70 | 71%(7)/-(0) | WF N不足 |
| instrument=GBP_USD ∧ _adx_q=Q2 | 13 | 7 | 53.8% | 3.59 | 67%(6)/43%(7) | 再現 |
| sr_basis=1.342 ∧ _session=london | 6 | 4 | 66.7% | 6.16 | 67%(6)/-(0) | WF N不足 |
| instrument=GBP_USD ∧ _session=london | 14 | 7 | 50.0% | 3.08 | 67%(6)/38%(8) | 片側のみ |
| _cvema_q=Q2 ∧ _adx_q=Q2 | 21 | 9 | 42.9% | 2.31 | 33%(12)/56%(9) | 片側のみ |
| sr_basis=1.342 ∧ _cvema_q=Q2 | 5 | 3 | 60.0% | 4.62 | 60%(5)/-(0) | WF N不足 |

---

## engulfing_bb (N=101, W=32, L=69, WR=31.7%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _hour_band | 0.0292 | 101 |
| _adx_q | 0.0268 | 101 |
| _cvema_q | 0.0180 | 101 |
| mtf_gate_action | 0.0170 | 101 |
| _session | 0.0143 | 101 |
| gate_group | 0.0112 | 101 |
| _conf_q | 0.0072 | 101 |
| mtf_regime | 0.0068 | 101 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _cvema_q = Q4 | 22 | 10 | 45.5% | 1.80 | 50%(12) | 40%(10) | 0.1281 | ✗ |
| _session = tokyo | 29 | 12 | 41.4% | 1.52 | 50%(12) | 35%(17) | 0.2378 | ✗ |
| _hour_band = 00-03 | 9 | 5 | 55.6% | 2.70 | 50%(4) | 60%(5) | 0.1374 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 3 features
  - `_cvema_q=Q4` — LR=1.80, pre/post WR = 50%(12)/40%(10)
  - `_session=tokyo` — LR=1.52, pre/post WR = 50%(12)/35%(17)
  - `_hour_band=00-03` — LR=2.70, pre/post WR = 50%(4)/60%(5)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _session=tokyo ∧ _hour_band=00-03 | 9 | 5 | 55.6% | 2.70 | 50%(4)/60%(5) | 再現 |
| _cvema_q=Q4 ∧ _session=tokyo | 7 | 3 | 42.9% | 1.62 | 50%(4)/33%(3) | 片側のみ |

---

## bb_squeeze_breakout (N=83, W=21, L=62, WR=25.3%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _hour_band | 0.1034 | 83 |
| _cvema_q | 0.0725 | 83 |
| _conf_q | 0.0654 | 83 |
| _session | 0.0391 | 83 |
| instrument | 0.0339 | 83 |
| _adx_q | 0.0319 | 83 |
| mtf_regime | 0.0147 | 83 |
| mtf_vol_state | 0.0147 | 83 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _cvema_q = Q1 | 24 | 11 | 45.8% | 2.50 | 27%(11) | 62%(13) | 0.0110 | ✗ |
| _conf_q = Q1 | 16 | 8 | 50.0% | 2.95 | 20%(5) | 64%(11) | 0.0219 | ✗ |
| _hour_band = 12-15 | 20 | 9 | 45.0% | 2.42 | 40%(5) | 47%(15) | 0.0360 | ✗ |
| _session = ny | 32 | 12 | 37.5% | 1.77 | 20%(10) | 45%(22) | 0.0681 | ✗ |
| _adx_q = Q4 | 21 | 7 | 33.3% | 1.48 | 33%(6) | 33%(15) | 0.3872 | ✗ |
| _hour_band = 16-19 | 13 | 5 | 38.5% | 1.85 | 17%(6) | 57%(7) | 0.2983 | ✗ |
| rj_hmm_regime = trending | 19 | 6 | 31.6% | 1.36 | -(0) | 32%(19) | 0.5506 | ✗ |
| _conf_q = Q4 | 16 | 5 | 31.2% | 1.34 | 50%(2) | 29%(14) | 0.5362 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 1 features
  - `_hour_band=12-15` — LR=2.42, pre/post WR = 40%(5)/47%(15)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _cvema_q=Q1 ∧ _hour_band=12-15 | 9 | 8 | 88.9% | 23.62 | 100%(1)/88%(8) | WF N不足 |
| _conf_q=Q1 ∧ _session=ny | 7 | 6 | 85.7% | 17.71 | 0%(1)/100%(6) | WF N不足 |
| _conf_q=Q1 ∧ _hour_band=16-19 | 4 | 4 | 100.0% | inf | -(0)/100%(4) | WF N不足 |
| _hour_band=12-15 ∧ _adx_q=Q4 | 5 | 4 | 80.0% | 11.81 | 50%(2)/100%(3) | WF N不足 |
| _cvema_q=Q1 ∧ _session=ny | 12 | 6 | 50.0% | 2.95 | 0%(4)/75%(8) | 片側のみ |
| _hour_band=12-15 ∧ _session=ny | 16 | 7 | 43.8% | 2.30 | 33%(3)/46%(13) | 片側のみ |
| _session=ny ∧ _adx_q=Q4 | 7 | 4 | 57.1% | 3.94 | 33%(3)/75%(4) | 片側のみ |
| _cvema_q=Q1 ∧ _conf_q=Q1 | 5 | 3 | 60.0% | 4.43 | 50%(2)/67%(3) | WF N不足 |

---

## ema_cross (N=46, W=16, L=30, WR=34.8%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| sr_basis | 0.2014 | 46 |
| _conf_q | 0.1531 | 46 |
| _adx_q | 0.1408 | 44 |
| _atr_q | 0.1156 | 44 |
| direction | 0.0554 | 46 |
| _session | 0.0537 | 46 |
| _hour_band | 0.0448 | 46 |
| instrument | 0.0301 | 46 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _conf_q = Q2 | 24 | 13 | 54.2% | 2.22 | 54%(24) | -(0) | 0.0055 | ✗ |
| _adx_q = Q2 | 8 | 5 | 62.5% | 3.12 | 62%(8) | -(0) | 0.1051 | ✗ |
| direction = SELL | 26 | 12 | 46.2% | 1.61 | 46%(26) | -(0) | 0.1173 | ✗ |
| _atr_q = Q3 | 13 | 7 | 53.8% | 2.19 | 58%(12) | 0%(1) | 0.1674 | ✗ |
| _adx_q = Q1 | 6 | 3 | 50.0% | 1.88 | 60%(5) | 0%(1) | 0.4055 | ✗ |
| _atr_q = Q4 | 9 | 4 | 44.4% | 1.50 | 44%(9) | -(0) | 0.6982 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _conf_q=Q2 ∧ _adx_q=Q2 | 5 | 5 | 100.0% | inf | 100%(5)/-(0) | WF N不足 |
| _adx_q=Q2 ∧ direction=SELL | 5 | 5 | 100.0% | inf | 100%(5)/-(0) | WF N不足 |
| _conf_q=Q2 ∧ direction=SELL | 23 | 12 | 52.2% | 2.05 | 52%(23)/-(0) | WF N不足 |
| _adx_q=Q2 ∧ _atr_q=Q3 | 3 | 3 | 100.0% | inf | 100%(3)/-(0) | WF N不足 |
| _conf_q=Q2 ∧ _atr_q=Q3 | 11 | 7 | 63.6% | 3.28 | 64%(11)/-(0) | WF N不足 |
| direction=SELL ∧ _atr_q=Q3 | 11 | 6 | 54.5% | 2.25 | 55%(11)/-(0) | WF N不足 |
| _conf_q=Q2 ∧ _atr_q=Q4 | 7 | 4 | 57.1% | 2.50 | 57%(7)/-(0) | WF N不足 |
| direction=SELL ∧ _atr_q=Q4 | 9 | 4 | 44.4% | 1.50 | 44%(9)/-(0) | WF N不足 |

---

## vol_surge_detector (N=41, W=10, L=31, WR=24.4%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _conf_q | 0.1162 | 41 |
| _atr_q | 0.0897 | 41 |
| mtf_regime | 0.0530 | 41 |
| mtf_vol_state | 0.0530 | 41 |
| mtf_alignment | 0.0530 | 41 |
| mtf_gate_action | 0.0530 | 41 |
| mtf_h4_label | 0.0530 | 41 |
| mtf_d1_label | 0.0530 | 41 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _conf_q = Q1 | 11 | 5 | 45.5% | 2.58 | 100%(2) | 33%(9) | 0.0981 | ✗ |
| _session = london | 9 | 4 | 44.4% | 2.48 | 0%(1) | 50%(8) | 0.1849 | ✗ |
| _hour_band = 12-15 | 13 | 5 | 38.5% | 1.94 | 50%(2) | 36%(11) | 0.2414 | ✗ |
| _atr_q = Q4 | 27 | 8 | 29.6% | 1.31 | 22%(9) | 33%(18) | 0.4474 | ✗ |
| rj_hmm_regime = trending | 10 | 4 | 40.0% | 2.07 | -(0) | 40%(10) | 0.2221 | ✗ |
| _adx_q = Q4 | 15 | 5 | 33.3% | 1.55 | 29%(7) | 38%(8) | 0.4527 | ✗ |
| _cvema_q = Q1 | 11 | 4 | 36.4% | 1.77 | 25%(4) | 43%(7) | 0.4132 | ✗ |
| _conf_q = Q2 | 8 | 3 | 37.5% | 1.86 | 0%(1) | 43%(7) | 0.3780 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _conf_q=Q1 ∧ _atr_q=Q4 | 4 | 3 | 75.0% | 9.30 | 100%(1)/67%(3) | WF N不足 |
| _session=london ∧ rj_hmm_regime=trending | 7 | 4 | 57.1% | 4.13 | -(0)/57%(7) | WF N不足 |
| _hour_band=12-15 ∧ _adx_q=Q4 | 5 | 3 | 60.0% | 4.65 | 100%(1)/50%(4) | WF N不足 |
| _session=london ∧ _hour_band=12-15 | 8 | 4 | 50.0% | 3.10 | -(0)/50%(8) | WF N不足 |
| _session=london ∧ _atr_q=Q4 | 9 | 4 | 44.4% | 2.48 | 0%(1)/50%(8) | WF N不足 |
| _hour_band=12-15 ∧ rj_hmm_regime=trending | 10 | 4 | 40.0% | 2.07 | -(0)/40%(10) | WF N不足 |
| _atr_q=Q4 ∧ rj_hmm_regime=trending | 10 | 4 | 40.0% | 2.07 | -(0)/40%(10) | WF N不足 |

---

## dt_sr_channel_reversal (N=38, W=12, L=26, WR=31.6%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| sr_basis | 0.6167 | 38 |
| _adx_q | 0.2322 | 38 |
| instrument | 0.2223 | 38 |
| _cvema_q | 0.1299 | 38 |
| mtf_regime | 0.0726 | 38 |
| mtf_vol_state | 0.0726 | 38 |
| mtf_alignment | 0.0726 | 38 |
| mtf_h4_label | 0.0726 | 38 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _adx_q = Q4 | 20 | 9 | 45.0% | 1.77 | 36%(14) | 67%(6) | 0.0860 | ✗ |
| _session = tokyo | 7 | 4 | 57.1% | 2.89 | 40%(5) | 100%(2) | 0.1765 | ✗ |
| _hour_band = 00-03 | 7 | 4 | 57.1% | 2.89 | 40%(5) | 100%(2) | 0.1765 | ✗ |
| instrument = USD_JPY | 12 | 6 | 50.0% | 2.17 | 33%(9) | 100%(3) | 0.1386 | ✗ |
| _cvema_q = Q4 | 5 | 3 | 60.0% | 3.25 | 50%(4) | 100%(1) | 0.3007 | ✗ |
| _cvema_q = Q1 | 13 | 6 | 46.2% | 1.86 | 29%(7) | 67%(6) | 0.2701 | ✗ |
| direction = SELL | 13 | 5 | 38.5% | 1.35 | 27%(11) | 100%(2) | 0.7144 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 1 features
  - `_adx_q=Q4` — LR=1.77, pre/post WR = 36%(14)/67%(6)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _session=tokyo ∧ _hour_band=00-03 | 7 | 4 | 57.1% | 2.89 | 40%(5)/100%(2) | WF N不足 |
| _adx_q=Q4 ∧ _cvema_q=Q1 | 13 | 6 | 46.2% | 1.86 | 29%(7)/67%(6) | 片側のみ |
| _adx_q=Q4 ∧ instrument=USD_JPY | 9 | 4 | 44.4% | 1.73 | 29%(7)/100%(2) | WF N不足 |
| instrument=USD_JPY ∧ _cvema_q=Q1 | 9 | 4 | 44.4% | 1.73 | 29%(7)/100%(2) | WF N不足 |

---

## ema_pullback (N=36, W=13, L=23, WR=36.1%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _session | 0.1505 | 36 |
| _cvema_q | 0.1144 | 36 |
| _adx_q | 0.0996 | 36 |
| _hour_band | 0.0694 | 36 |
| _atr_q | 0.0544 | 36 |
| layer1_dir | 0.0203 | 36 |
| instrument | 0.0110 | 36 |
| direction | 0.0059 | 36 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _session = ny | 20 | 11 | 55.0% | 2.16 | 55%(20) | -(0) | 0.0140 | ✗ |
| _cvema_q = Q1 | 8 | 5 | 62.5% | 2.95 | 62%(8) | -(0) | 0.1072 | ✗ |
| _hour_band = 12-15 | 15 | 8 | 53.3% | 2.02 | 57%(14) | 0%(1) | 0.0895 | ✗ |
| _atr_q = Q2 | 9 | 5 | 55.6% | 2.21 | 62%(8) | 0%(1) | 0.2347 | ✗ |
| layer1_dir = neutral | 21 | 9 | 42.9% | 1.33 | 45%(20) | 0%(1) | 0.4837 | ✗ |
| _adx_q = Q4 | 16 | 7 | 43.8% | 1.38 | 44%(16) | -(0) | 0.4932 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _session=ny ∧ _hour_band=12-15 | 9 | 8 | 88.9% | 14.15 | 89%(9)/-(0) | WF N不足 |
| _session=ny ∧ layer1_dir=neutral | 10 | 7 | 70.0% | 4.13 | 70%(10)/-(0) | WF N不足 |
| _session=ny ∧ _adx_q=Q4 | 11 | 7 | 63.6% | 3.10 | 64%(11)/-(0) | WF N不足 |
| _hour_band=12-15 ∧ layer1_dir=neutral | 5 | 4 | 80.0% | 7.08 | 100%(4)/0%(1) | WF N不足 |
| _hour_band=12-15 ∧ _adx_q=Q4 | 7 | 5 | 71.4% | 4.42 | 71%(7)/-(0) | WF N不足 |
| _cvema_q=Q1 ∧ layer1_dir=neutral | 8 | 5 | 62.5% | 2.95 | 62%(8)/-(0) | WF N不足 |
| _session=ny ∧ _cvema_q=Q1 | 6 | 4 | 66.7% | 3.54 | 67%(6)/-(0) | WF N不足 |
| _session=ny ∧ _atr_q=Q2 | 4 | 3 | 75.0% | 5.31 | 75%(4)/-(0) | WF N不足 |

---

## dt_bb_rsi_mr (N=35, W=16, L=19, WR=45.7%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| sr_basis | 0.5487 | 35 |
| _atr_q | 0.1982 | 35 |
| rj_hmm_regime | 0.1427 | 9 |
| _adx_q | 0.0816 | 35 |
| _cvema_q | 0.0534 | 35 |
| _conf_q | 0.0363 | 35 |
| mtf_regime | 0.0330 | 35 |
| mtf_vol_state | 0.0330 | 35 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _atr_q = Q2 | 7 | 6 | 85.7% | 7.12 | 100%(4) | 67%(3) | 0.0318 | ✗ |
| _adx_q = Q1 | 25 | 14 | 56.0% | 1.51 | 56%(18) | 57%(7) | 0.0712 | ✗ |
| instrument = GBP_USD | 11 | 6 | 54.5% | 1.43 | 80%(5) | 33%(6) | 0.7160 | ✗ |
| _hour_band = 12-15 | 11 | 6 | 54.5% | 1.43 | 50%(10) | 100%(1) | 0.7160 | ✗ |
| _spread_q = Q4 | 11 | 6 | 54.5% | 1.43 | 80%(5) | 33%(6) | 0.7160 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 2 features
  - `_atr_q=Q2` — LR=7.12, pre/post WR = 100%(4)/67%(3)
  - `_adx_q=Q1` — LR=1.51, pre/post WR = 56%(18)/57%(7)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _atr_q=Q2 ∧ _adx_q=Q1 | 7 | 6 | 85.7% | 7.12 | 100%(4)/67%(3) | 再現 |
| _adx_q=Q1 ∧ _hour_band=12-15 | 6 | 5 | 83.3% | 5.94 | 80%(5)/100%(1) | WF N不足 |
| instrument=GBP_USD ∧ _spread_q=Q4 | 11 | 6 | 54.5% | 1.43 | 80%(5)/33%(6) | 片側のみ |
| _atr_q=Q2 ∧ instrument=GBP_USD | 4 | 3 | 75.0% | 3.56 | 100%(1)/67%(3) | WF N不足 |
| _atr_q=Q2 ∧ _spread_q=Q4 | 4 | 3 | 75.0% | 3.56 | 100%(1)/67%(3) | WF N不足 |
| _adx_q=Q1 ∧ instrument=GBP_USD | 9 | 5 | 55.6% | 1.48 | 75%(4)/40%(5) | 片側のみ |
| _adx_q=Q1 ∧ _spread_q=Q4 | 9 | 5 | 55.6% | 1.48 | 75%(4)/40%(5) | 片側のみ |

---

## sr_break_retest (N=24, W=3, L=21, WR=12.5%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| sr_basis | 0.5436 | 24 |
| _cvema_q | 0.2079 | 24 |
| instrument | 0.1603 | 24 |
| _hour_band | 0.1432 | 24 |
| _session | 0.1031 | 24 |
| _conf_q | 0.0836 | 24 |
| _atr_q | 0.0803 | 24 |
| _adx_q | 0.0683 | 24 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| (no LR≥1.3 with N_win≥3 — WIN-DNA 皆無) | | | | | | | | |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| (no 2-way conjunction with WR|AND≥40% and N_win≥3) | | | | | | |

---

## trend_rebound (N=22, W=9, L=13, WR=40.9%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _atr_q | 0.2721 | 22 |
| _hour_band | 0.1681 | 22 |
| instrument | 0.0398 | 22 |
| rj_hmm_regime | 0.0251 | 17 |
| mtf_regime | 0.0237 | 22 |
| mtf_vol_state | 0.0237 | 22 |
| mtf_gate_action | 0.0237 | 22 |
| mtf_h4_label | 0.0237 | 22 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _atr_q = Q3 | 8 | 6 | 75.0% | 4.33 | 67%(3) | 80%(5) | 0.0260 | ✗ |
| instrument = EUR_USD | 5 | 3 | 60.0% | 2.17 | 50%(4) | 100%(1) | 0.6090 | ✗ |
| _hour_band = 08-11 | 5 | 3 | 60.0% | 2.17 | 33%(3) | 100%(2) | 0.6090 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 1 features
  - `_atr_q=Q3` — LR=4.33, pre/post WR = 67%(3)/80%(5)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _atr_q=Q3 ∧ instrument=EUR_USD | 3 | 3 | 100.0% | inf | 100%(2)/100%(1) | WF N不足 |

---

## ema200_trend_reversal (N=20, W=8, L=12, WR=40.0%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| sr_basis | 0.8710 | 20 |
| _conf_q | 0.2435 | 20 |
| _adx_q | 0.2234 | 20 |
| _hour_band | 0.2079 | 20 |
| _atr_q | 0.1772 | 20 |
| instrument | 0.1620 | 20 |
| direction | 0.1245 | 20 |
| _cvema_q | 0.0759 | 20 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| sr_basis = 159.082 | 4 | 4 | 100.0% | inf | 100%(2) | 100%(2) | 0.0144 | ✗ |
| _hour_band = 12-15 | 7 | 5 | 71.4% | 3.75 | 100%(2) | 60%(5) | 0.0623 | ✗ |
| direction = SELL | 10 | 6 | 60.0% | 2.25 | 100%(3) | 43%(7) | 0.1698 | ✗ |
| _adx_q = Q1 | 15 | 8 | 53.3% | 1.71 | 100%(3) | 42%(12) | 0.0547 | ✗ |
| instrument = USD_JPY | 11 | 6 | 54.5% | 1.80 | 100%(3) | 38%(8) | 0.1968 | ✗ |
| _spread_q = Q1 | 12 | 6 | 50.0% | 1.50 | 100%(3) | 33%(9) | 0.3729 | ✗ |
| _atr_q = Q2 | 5 | 3 | 60.0% | 2.25 | 100%(1) | 50%(4) | 0.3473 | ✗ |
| mtf_regime =  | 10 | 5 | 50.0% | 1.50 | 100%(3) | 29%(7) | 0.6499 | ✗ |
| mtf_vol_state =  | 10 | 5 | 50.0% | 1.50 | 100%(3) | 29%(7) | 0.6499 | ✗ |
| mtf_alignment =  | 10 | 5 | 50.0% | 1.50 | 100%(3) | 29%(7) | 0.6499 | ✗ |
| mtf_gate_action =  | 10 | 5 | 50.0% | 1.50 | 100%(3) | 29%(7) | 0.6499 | ✗ |
| mtf_h4_label = 3 | 10 | 5 | 50.0% | 1.50 | 100%(3) | 29%(7) | 0.6499 | ✗ |
| mtf_d1_label = 3 | 10 | 5 | 50.0% | 1.50 | 100%(3) | 29%(7) | 0.6499 | ✗ |
| gate_group =  | 10 | 5 | 50.0% | 1.50 | 100%(3) | 29%(7) | 0.6499 | ✗ |
| _cvema_q = Q2 | 6 | 3 | 50.0% | 1.50 | 100%(2) | 25%(4) | 0.6424 | ✗ |

**再現性通過 (pre&post Cutoff どちらも WR>35%)**: 3 features
  - `direction=SELL` — LR=2.25, pre/post WR = 100%(3)/43%(7)
  - `_adx_q=Q1` — LR=1.71, pre/post WR = 100%(3)/42%(12)
  - `instrument=USD_JPY` — LR=1.80, pre/post WR = 100%(3)/38%(8)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| _hour_band=12-15 ∧ instrument=USD_JPY | 5 | 5 | 100.0% | inf | 100%(2)/100%(3) | WF N不足 |
| _hour_band=12-15 ∧ _spread_q=Q1 | 5 | 5 | 100.0% | inf | 100%(2)/100%(3) | WF N不足 |
| sr_basis=159.082 ∧ _hour_band=12-15 | 4 | 4 | 100.0% | inf | 100%(2)/100%(2) | WF N不足 |
| sr_basis=159.082 ∧ _adx_q=Q1 | 4 | 4 | 100.0% | inf | 100%(2)/100%(2) | WF N不足 |
| sr_basis=159.082 ∧ instrument=USD_JPY | 4 | 4 | 100.0% | inf | 100%(2)/100%(2) | WF N不足 |
| sr_basis=159.082 ∧ _spread_q=Q1 | 4 | 4 | 100.0% | inf | 100%(2)/100%(2) | WF N不足 |
| _hour_band=12-15 ∧ _adx_q=Q1 | 6 | 5 | 83.3% | 7.50 | 100%(2)/75%(4) | WF N不足 |
| _hour_band=12-15 ∧ direction=SELL | 3 | 3 | 100.0% | inf | 100%(2)/100%(1) | WF N不足 |

---

## xs_momentum (N=14, W=3, L=11, WR=21.4%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| sr_basis | 0.3210 | 14 |
| _cvema_q | 0.2570 | 14 |
| _hour_band | 0.2042 | 14 |
| instrument | 0.1593 | 14 |
| _session | 0.1593 | 14 |
| _spread_q | 0.1593 | 14 |
| _adx_q | 0.1432 | 14 |
| _atr_q | 0.1213 | 14 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| sr_basis = 1.342 | 6 | 3 | 50.0% | 3.67 | 50%(6) | -(0) | 0.0549 | ✗ |
| _cvema_q = Q3 | 7 | 3 | 42.9% | 2.75 | 43%(7) | -(0) | 0.1923 | ✗ |
| _hour_band = 12-15 | 8 | 3 | 37.5% | 2.20 | 38%(8) | -(0) | 0.2088 | ✗ |
| instrument = GBP_USD | 9 | 3 | 33.3% | 1.83 | 33%(9) | -(0) | 0.2582 | ✗ |
| _session = ny | 9 | 3 | 33.3% | 1.83 | 33%(9) | -(0) | 0.2582 | ✗ |
| _spread_q = Q4 | 9 | 3 | 33.3% | 1.83 | 33%(9) | -(0) | 0.2582 | ✗ |
| direction = BUY | 10 | 3 | 30.0% | 1.57 | 30%(10) | -(0) | 0.5055 | ✗ |
| layer1_dir = neutral | 10 | 3 | 30.0% | 1.57 | 30%(10) | -(0) | 0.5055 | ✗ |
| _conf_q = Q4 | 11 | 3 | 27.3% | 1.38 | 27%(11) | -(0) | 1.0000 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| sr_basis=1.342 ∧ _hour_band=12-15 | 5 | 3 | 60.0% | 5.50 | 60%(5)/-(0) | WF N不足 |
| sr_basis=1.342 ∧ _session=ny | 5 | 3 | 60.0% | 5.50 | 60%(5)/-(0) | WF N不足 |
| sr_basis=1.342 ∧ _cvema_q=Q3 | 6 | 3 | 50.0% | 3.67 | 50%(6)/-(0) | WF N不足 |
| sr_basis=1.342 ∧ instrument=GBP_USD | 6 | 3 | 50.0% | 3.67 | 50%(6)/-(0) | WF N不足 |
| sr_basis=1.342 ∧ _spread_q=Q4 | 6 | 3 | 50.0% | 3.67 | 50%(6)/-(0) | WF N不足 |
| _cvema_q=Q3 ∧ _hour_band=12-15 | 6 | 3 | 50.0% | 3.67 | 50%(6)/-(0) | WF N不足 |
| _cvema_q=Q3 ∧ _session=ny | 6 | 3 | 50.0% | 3.67 | 50%(6)/-(0) | WF N不足 |
| _hour_band=12-15 ∧ instrument=GBP_USD | 6 | 3 | 50.0% | 3.67 | 50%(6)/-(0) | WF N不足 |

---

## v_reversal (N=13, W=3, L=10, WR=23.1%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| _atr_q | 0.2503 | 13 |
| _adx_q | 0.1831 | 13 |
| _hour_band | 0.1232 | 13 |
| mtf_regime | 0.1014 | 13 |
| mtf_vol_state | 0.1014 | 13 |
| mtf_alignment | 0.1014 | 13 |
| mtf_gate_action | 0.1014 | 13 |
| mtf_h4_label | 0.1014 | 13 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| mtf_regime =  | 10 | 3 | 30.0% | 1.43 | 50%(2) | 25%(8) | 0.5280 | ✗ |
| mtf_vol_state =  | 10 | 3 | 30.0% | 1.43 | 50%(2) | 25%(8) | 0.5280 | ✗ |
| mtf_alignment =  | 10 | 3 | 30.0% | 1.43 | 50%(2) | 25%(8) | 0.5280 | ✗ |
| mtf_gate_action =  | 10 | 3 | 30.0% | 1.43 | 50%(2) | 25%(8) | 0.5280 | ✗ |
| mtf_h4_label = 3 | 10 | 3 | 30.0% | 1.43 | 50%(2) | 25%(8) | 0.5280 | ✗ |
| mtf_d1_label = 3 | 10 | 3 | 30.0% | 1.43 | 50%(2) | 25%(8) | 0.5280 | ✗ |
| gate_group =  | 10 | 3 | 30.0% | 1.43 | 50%(2) | 25%(8) | 0.5280 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| (no 2-way conjunction with WR|AND≥40% and N_win≥3) | | | | | | |

---

## trendline_sweep (N=8, W=3, L=5, WR=37.5%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| direction | 0.5488 | 8 |
| sr_basis | 0.3601 | 8 |
| _hour_band | 0.3476 | 8 |
| _conf_q | 0.2988 | 8 |
| _atr_q | 0.2657 | 8 |
| _cvema_q | 0.2044 | 8 |
| _session | 0.0976 | 8 |
| instrument | 0.0924 | 8 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| direction = BUY | 4 | 3 | 75.0% | 5.00 | 67%(3) | 100%(1) | 0.1429 | ✗ |
| _cvema_q = Q3 | 6 | 3 | 50.0% | 1.67 | 40%(5) | 100%(1) | - | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| direction=BUY ∧ _cvema_q=Q3 | 4 | 3 | 75.0% | 5.00 | 67%(3)/100%(1) | WF N不足 |

---

## orb_trap (N=7, W=4, L=3, WR=57.1%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| sr_basis | 0.6995 | 7 |
| mtf_gate_action | 0.2917 | 7 |
| gate_group | 0.2917 | 7 |
| _atr_q | 0.2359 | 7 |
| _conf_q | 0.1281 | 7 |
| _adx_q | 0.1281 | 7 |
| direction | 0.0202 | 7 |
| instrument | 0.0060 | 7 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _atr_q = Q4 | 4 | 3 | 75.0% | 2.25 | 75%(4) | -(0) | 0.4857 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| (no 2-way conjunction with WR|AND≥40% and N_win≥3) | | | | | | |

---

## post_news_vol (N=7, W=4, L=3, WR=57.1%)

### MI ranking (top 8, non-zero)

| Feature | I(O;F) bits | Coverage N |
|---|---:|---:|
| sr_basis | 0.9852 | 7 |
| _hour_band | 0.5917 | 7 |
| _adx_q | 0.3060 | 7 |
| _session | 0.2917 | 7 |
| instrument | 0.1981 | 7 |
| direction | 0.1281 | 7 |
| _spread_q | 0.1281 | 7 |
| _atr_q | 0.1281 | 7 |

### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)

| Feature = value | N | N_win | WR\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |
|---|---:|---:|---:|---:|---|---|---:|:---:|
| _spread_q = Q1 | 4 | 3 | 75.0% | 2.25 | 75%(4) | -(0) | 0.4857 | ✗ |
| _atr_q = Q4 | 4 | 3 | 75.0% | 2.25 | 75%(4) | -(0) | 0.4857 | ✗ |

**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)

### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)

| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\|AND | LR_AND | WF pre/post | 判定 |
|---|---:|---:|---:|---:|---|:---:|
| (no 2-way conjunction with WR|AND≥40% and N_win≥3) | | | | | | |

---


## Cross-strategy: どの特徴が outcome を最も説明するか?

全 Shadow trades 集計での I(outcome; feature)
| Feature | I(O;F) bits | Coverage N | Relative |
|---|---:|---:|---:|
| sr_basis | 0.0670 | 1711 | 7.87% |
| _conf_q | 0.0061 | 1711 | 0.72% |
| _hour_band | 0.0043 | 1711 | 0.51% |
| instrument | 0.0036 | 1711 | 0.43% |
| mtf_alignment | 0.0035 | 1711 | 0.41% |
| _cvema_q | 0.0012 | 1693 | 0.14% |
| _spread_q | 0.0012 | 1711 | 0.14% |
| mtf_regime | 0.0011 | 1711 | 0.13% |
| mtf_d1_label | 0.0010 | 1711 | 0.12% |
| _adx_q | 0.0009 | 1693 | 0.10% |
| mtf_gate_action | 0.0007 | 1711 | 0.08% |
| rj_hmm_regime | 0.0007 | 846 | 0.08% |
| _session | 0.0007 | 1711 | 0.08% |
| layer1_dir | 0.0007 | 1711 | 0.08% |
| mtf_vol_state | 0.0006 | 1711 | 0.07% |
| mtf_h4_label | 0.0006 | 1711 | 0.07% |
| gate_group | 0.0004 | 1711 | 0.05% |
| _atr_q | 0.0003 | 1693 | 0.03% |
| direction | 0.0000 | 1711 | 0.00% |

H(outcome) baseline = 0.8514 bits. 各特徴が outcome entropy を何%削減するか
