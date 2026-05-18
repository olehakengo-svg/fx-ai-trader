# Shadow Promote Shortlist (Phase A 分析)

## Verdict
**Tier 1 5 family / Tier 2 0 family / Tier 3 5 family / Tier 4 13 family**

## Tier 1 (TOP PROMOTE) - Phase B 実装最優先

### EUR_GBP_H1_LONG_SHOCK
- **Rep cell**: `EUR_GBP_H1_LONG_SHOCK_1_3_Q5` - pct=1, horizon=3, vol_q=Q5
- **Stats**: N=239, WR=0.728, Wilson_lo=0.668, PF=14.75, EV=0.7032% (55.81pip)
- **Robustness**: bonf=28/family=35 cell, horizon_cov=4/4, pct_cov=3/3
- **思想**: 価格が下位1% percentile 急変 + vol_q=Q5 -> next bar open ロング -> 3 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/scalp/price_shock_rev_eur_gbp_long.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: EUR_GBP only (cross-pair 拡張は別 BT 必要)

### EUR_AUD_H1_LONG_SHOCK
- **Rep cell**: `EUR_AUD_H1_LONG_SHOCK_1_12_Q5` - pct=1, horizon=12, vol_q=Q5
- **Stats**: N=262, WR=0.676, Wilson_lo=0.617, PF=4.05, EV=0.3790% (58.77pip)
- **Robustness**: bonf=24/family=28 cell, horizon_cov=4/4, pct_cov=3/3
- **思想**: 価格が下位1% percentile 急変 + vol_q=Q5 -> next bar open ロング -> 12 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/scalp/price_shock_rev_eur_aud_long.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: EUR_AUD only (cross-pair 拡張は別 BT 必要)

### USD_CAD_H1_LONG_SHOCK
- **Rep cell**: `USD_CAD_H1_LONG_SHOCK_1_3_Q5` - pct=1, horizon=3, vol_q=Q5
- **Stats**: N=247, WR=0.664, Wilson_lo=0.603, PF=5.30, EV=0.2172% (28.66pip)
- **Robustness**: bonf=7/family=13 cell, horizon_cov=4/4, pct_cov=3/3
- **思想**: 価格が下位1% percentile 急変 + vol_q=Q5 -> next bar open ロング -> 3 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/scalp/price_shock_rev_usd_cad_long.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: USD_CAD only (cross-pair 拡張は別 BT 必要)

### NZD_JPY_H1_LONG_SHOCK
- **Rep cell**: `NZD_JPY_H1_LONG_SHOCK_1_12_Q5` - pct=1, horizon=12, vol_q=Q5
- **Stats**: N=303, WR=0.640, Wilson_lo=0.585, PF=5.02, EV=0.7193% (58.88pip)
- **Robustness**: bonf=21/family=33 cell, horizon_cov=4/4, pct_cov=3/3
- **思想**: 価格が下位1% percentile 急変 + vol_q=Q5 -> next bar open ロング -> 12 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/scalp/price_shock_rev_nzd_jpy_long.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: NZD_JPY only (cross-pair 拡張は別 BT 必要)

### AUD_JPY_H1_LONG_SHOCK
- **Rep cell**: `AUD_JPY_H1_LONG_SHOCK_1_12_ALL` - pct=1, horizon=12, vol_q=ALL
- **Stats**: N=426, WR=0.638, Wilson_lo=0.592, PF=2.54, EV=0.3635% (32.25pip)
- **Robustness**: bonf=9/family=29 cell, horizon_cov=4/4, pct_cov=3/3
- **思想**: 価格が下位1% percentile 急変 + vol_q=ALL -> next bar open ロング -> 12 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/scalp/price_shock_rev_aud_jpy_long.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: AUD_JPY only (cross-pair 拡張は別 BT 必要)

## Tier 2 (PROMOTE)

該当なし。

## Tier 3 (WATCH)

### USD_CAD_H1_SHORT_SHOCK
- **Rep cell**: `USD_CAD_H1_SHORT_SHOCK_1_1_Q4` - pct=1, horizon=1, vol_q=Q4
- **Stats**: N=68, WR=0.735, Wilson_lo=0.620, PF=3.40, EV=0.0446% (6.00pip)
- **Robustness**: bonf=0/family=4 cell, horizon_cov=3/4, pct_cov=2/3
- **思想**: 価格が上位1% percentile 急変 + vol_q=Q4 -> next bar open ショート -> 1 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/scalp/price_shock_rev_usd_cad_short.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: USD_CAD only (cross-pair 拡張は別 BT 必要)

### AUD_JPY_H4_LONG_SHOCK
- **Rep cell**: `AUD_JPY_H4_LONG_SHOCK_5_6_Q3` - pct=5, horizon=6, vol_q=Q3
- **Stats**: N=54, WR=0.741, Wilson_lo=0.611, PF=4.35, EV=0.3099% (29.41pip)
- **Robustness**: bonf=0/family=3 cell, horizon_cov=2/4, pct_cov=1/3
- **思想**: 価格が下位5% percentile 急変 + vol_q=Q3 -> next bar open ロング -> 6 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/daytrade/price_shock_rev_aud_jpy_long.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: AUD_JPY only (cross-pair 拡張は別 BT 必要)

### EUR_GBP_H4_LONG_SHOCK
- **Rep cell**: `EUR_GBP_H4_LONG_SHOCK_5_6_Q2` - pct=5, horizon=6, vol_q=Q2
- **Stats**: N=30, WR=0.767, Wilson_lo=0.591, PF=4.28, EV=0.1772% (15.16pip)
- **Robustness**: bonf=0/family=1 cell, horizon_cov=1/4, pct_cov=1/3
- **思想**: 価格が下位5% percentile 急変 + vol_q=Q2 -> next bar open ロング -> 6 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/daytrade/price_shock_rev_eur_gbp_long.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: EUR_GBP only (cross-pair 拡張は別 BT 必要)

### USD_CHF_H4_SHORT_SHOCK
- **Rep cell**: `USD_CHF_H4_SHORT_SHOCK_2p5_12_Q4` - pct=2.5, horizon=12, vol_q=Q4
- **Stats**: N=48, WR=0.708, Wilson_lo=0.568, PF=2.43, EV=0.2021% (17.38pip)
- **Robustness**: bonf=0/family=7 cell, horizon_cov=2/4, pct_cov=3/3
- **思想**: 価格が上位2.5% percentile 急変 + vol_q=Q4 -> next bar open ショート -> 12 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/daytrade/price_shock_rev_usd_chf_short.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: USD_CHF only (cross-pair 拡張は別 BT 必要)

### USD_CHF_H1_LONG_SHOCK
- **Rep cell**: `USD_CHF_H1_LONG_SHOCK_5_3_Q2` - pct=5, horizon=3, vol_q=Q2
- **Stats**: N=216, WR=0.630, Wilson_lo=0.563, PF=1.76, EV=0.0419% (3.74pip)
- **Robustness**: bonf=0/family=3 cell, horizon_cov=3/4, pct_cov=2/3
- **思想**: 価格が下位5% percentile 急変 + vol_q=Q2 -> next bar open ロング -> 3 bars 後 close
- **Phase B 実装要点**:
  - Strategy file: `strategies/scalp/price_shock_rev_usd_chf_long.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: USD_CHF only (cross-pair 拡張は別 BT 必要)

## Tier 4 (REJECT)
| Family | Rep Wilson_lo | Rep N | bonf_pass | Reason |
|---|---:|---:|---:|---|
| NZD_USD_H1_LONG_SHOCK | 0.590 | 236 | 22 | REJECT: Tier 1 qualified but exceeded max family cap |
| AUD_USD_H1_LONG_SHOCK | 0.544 | 370 | 10 | REJECT: Tier 1 qualified but exceeded max family cap |
| EUR_JPY_H4_LONG_SHOCK | 0.558 | 144 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| EUR_USD_H4_SHORT_SHOCK | 0.556 | 65 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| EUR_USD_H1_SHORT_SHOCK | 0.546 | 96 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| EUR_AUD_H4_LONG_SHOCK | 0.527 | 246 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| NZD_USD_H1_SHORT_SHOCK | 0.521 | 62 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| GBP_USD_H1_LONG_SHOCK | 0.516 | 341 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| GBP_JPY_H1_LONG_SHOCK | 0.515 | 281 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| EUR_JPY_H1_LONG_SHOCK | 0.512 | 154 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| USD_JPY_H4_SHORT_SHOCK | 0.508 | 81 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| EUR_USD_H1_LONG_SHOCK | 0.508 | 359 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |
| USD_CHF_H1_SHORT_SHOCK | 0.507 | 1597 | 0 | REJECT: Tier 3 qualified but exceeded max family cap |

## 思想
価格自身の極値分位後 mean reversion edge。Family 単位で dedup し、horizon/percentile/vol_q overlap を真の独立 edge から切り分けた。

## 設計欠陥 (現時点で見える)
- BT は固定 horizon exit (動的 SL/TP なし) - Live では cost-aware exit が edge を削る可能性
- Q5 (高ボラ) 集中 - vol 分位の look-ahead 排除確認済 (rolling 1512-bar) だが、Live regime shift で Q5 定義が変動するリスク
- Cross-pair correlation 未補正 - EUR_GBP / EUR_AUD / EUR_USD 同時 trigger で portfolio concentration risk

## Phase B 推奨スケジュール
1. **Week 1**: Tier 1 上位 3 family を strategy module 化、unit test
2. **Week 2**: demo_trader 統合 + shadow execution 開始
3. **Week 3-6**: N >= 30 Live Shadow 蓄積、Wilson_lo 維持確認
4. **Week 7**: Live promote 判定 (R1: 365日BT + Bonferroni、または Live N >= 30 + Wilson_lo >= 0.50)
