# PRIME v2 Shadow Audit Report (2026-05-18)

## Total hypothesis space
- 6 strategies × <=5 cells = m_total = 9 (<=30)
- Bonferroni alpha = 0.05 / 9 = 0.005556
- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=10000`
- Fetched rows: 6456; shadow rows: 5644; WIN/LOSS shadow non-XAU rows: 5121
- Target strategy rows: 307; API coverage observed: 2026-04-02 08:17:17 UTC to 2026-05-18 08:51:07 UTC
- Regime quartile edges from shadow regime JSON: ADX=[19.5, 24.7, 31.6], ATR=[0.95, 1.01, 1.09]

## Per-strategy audits

### Strategy: gbp_deep_pullback

**Verdict**: THESIS_VALID + DESIGN_VALID_NEEDS_N

**1. 思想 (Thesis)**: ADX TC の GBP/USD 特化版。GBP/USD は浅い押し目ではノイズに巻き込まれるため、BB 下限/上限または EMA50 付近の深い押し目・戻り目から反発を狙う。

**2. 8 軸監査**:
| 軸 | 値 | 評価 |
|---|---|:---:|
| 1. 全期間 shadow N / WR / Wilson_lo | **12/25.0%/0.089** | 🟠 |
| 2. spread-adjusted EV (entry_price 基準) | **+2.42p** | 🟢 |
| 3. Profit Factor | **1.21** | 🟢 |
| 4. Kelly fraction | **0.022** | 🟠 |
| 5. 直近 30d vs 全期間 (drift detection) | **30d N=12 WR=25.0% EV=+2.42p deltaWR=+0.0%** | 🟢 |
| 6. session × direction WR matrix | **n/a** | 🔴 |
| 7. regime (ADX/ATR quartile) WR matrix | **n/a** | 🔴 |
| 8. Walk-Forward (3-fold) EV+ count | **1/3** | 🔴 |

**3. 設計欠陥候補**:
- No pre-registered session × direction cell reached N>=10 and WR>=50%; timing/direction thesis is not isolating edge.
- No ADX/ATR quartile cell reached N>=10 and WR>=50%; regime filter is not yet separating winners.

**4. 再設計案 (新 PRIME 候補 cell; locked before stats)**:
- **Cell 1**: gbp_deep_pullback_ALL, predicate=`entry_type == strategy`, expected_N>=20
- Bonferroni alpha contribution uses global m_total=9 (alpha=0.005556)

**5. 候補 cell 実測**:
| cell | N | WR | Wlo | Fisher p | Bonf p×m | FDR q10 | WF | Kelly | spread-adj EV | verdict |
|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|:---:|
| gbp_deep_pullback_ALL | 12 | 25.0% | 0.089 | 0.661 | 1 | N | 1/3 | 0.022 | +2.42 | REJECT |

**6. PRIME v2 への組込み推奨**:
- SELECTED cell なし。PRIME v2 への組込みは REJECT; shadow N+30d で再評価。

### Strategy: orb_trap

**Verdict**: THESIS_VALID + DESIGN_VALID_NEEDS_N

**1. 思想 (Thesis)**: Opening Range Breakout Trap。London/NY の opening range を一度抜けた後、range 内に実体回帰する false breakout を逆張りで fade する。

**2. 8 軸監査**:
| 軸 | 値 | 評価 |
|---|---|:---:|
| 1. 全期間 shadow N / WR / Wilson_lo | **19/42.1%/0.231** | 🟠 |
| 2. spread-adjusted EV (entry_price 基準) | **+1.99p** | 🟢 |
| 3. Profit Factor | **1.43** | 🟢 |
| 4. Kelly fraction | **0.063** | 🟢 |
| 5. 直近 30d vs 全期間 (drift detection) | **30d N=18 WR=44.4% EV=+2.77p deltaWR=+2.3%** | 🟢 |
| 6. session × direction WR matrix | **n/a** | 🔴 |
| 7. regime (ADX/ATR quartile) WR matrix | **n/a** | 🔴 |
| 8. Walk-Forward (3-fold) EV+ count | **2/3** | 🟠 |

**3. 設計欠陥候補**:
- No pre-registered session × direction cell reached N>=10 and WR>=50%; timing/direction thesis is not isolating edge.
- No ADX/ATR quartile cell reached N>=10 and WR>=50%; regime filter is not yet separating winners.

**4. 再設計案 (新 PRIME 候補 cell; locked before stats)**:
- **Cell 1**: orb_trap_ALL, predicate=`entry_type == strategy`, expected_N>=20
- Bonferroni alpha contribution uses global m_total=9 (alpha=0.005556)

**5. 候補 cell 実測**:
| cell | N | WR | Wlo | Fisher p | Bonf p×m | FDR q10 | WF | Kelly | spread-adj EV | verdict |
|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|:---:|
| orb_trap_ALL | 19 | 42.1% | 0.231 | 0.107 | 0.962 | N | 2/3 | 0.063 | +1.99 | REJECT |

**6. PRIME v2 への組込み推奨**:
- SELECTED cell なし。PRIME v2 への組込みは REJECT; shadow N+30d で再評価。

### Strategy: ob_retest

**Verdict**: THESIS_VALID + DESIGN_VALID_NEEDS_N

**1. 思想 (Thesis)**: H1 Order Block Retest strategy。impulse 前の order block を検出し、fresh retest とentry confirmation で反発を狙う。M5 ob_retest は demote 済みで H1 へ思想移行中。

**2. 8 軸監査**:
| 軸 | 値 | 評価 |
|---|---|:---:|
| 1. 全期間 shadow N / WR / Wilson_lo | **40/42.5%/0.285** | 🟢 |
| 2. spread-adjusted EV (entry_price 基準) | **+2.68p** | 🟢 |
| 3. Profit Factor | **1.40** | 🟢 |
| 4. Kelly fraction | **0.060** | 🟢 |
| 5. 直近 30d vs 全期間 (drift detection) | **30d N=40 WR=42.5% EV=+2.68p deltaWR=+0.0%** | 🟢 |
| 6. session × direction WR matrix | **ob_retest_OVERLAP_BUY N=11 WR=63.6%** | 🟢 |
| 7. regime (ADX/ATR quartile) WR matrix | **n/a** | 🔴 |
| 8. Walk-Forward (3-fold) EV+ count | **3/3** | 🟢 |

**3. 設計欠陥候補**:
- No ADX/ATR quartile cell reached N>=10 and WR>=50%; regime filter is not yet separating winners.

**4. 再設計案 (新 PRIME 候補 cell; locked before stats)**:
- **Cell 1**: ob_retest_ALL, predicate=`entry_type == strategy`, expected_N>=20
- **Cell 2**: ob_retest_OVERLAP_BUY, predicate=`session == overlap and direction == BUY`, expected_N>=20
- Bonferroni alpha contribution uses global m_total=9 (alpha=0.005556)

**5. 候補 cell 実測**:
| cell | N | WR | Wlo | Fisher p | Bonf p×m | FDR q10 | WF | Kelly | spread-adj EV | verdict |
|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|:---:|
| ob_retest_ALL | 40 | 42.5% | 0.285 | 0.0218 | 0.196 | Y | 3/3 | 0.060 | +2.68 | REJECT |
| ob_retest_OVERLAP_BUY | 11 | 63.6% | 0.354 | 0.0111 | 0.0996 | Y | 2/3 | 0.263 | +13.73 | REJECT |

**6. PRIME v2 への組込み推奨**:
- SELECTED cell なし。PRIME v2 への組込みは REJECT; shadow N+30d で再評価。

### Strategy: trend_rebound

**Verdict**: THESIS_INVALID

**1. 思想 (Thesis)**: Trend Rebound。強トレンド時に Stoch/RSI/BB%B の極端値と反転足を使い、短期の逆張りリバウンドを狙う。

**2. 8 軸監査**:
| 軸 | 値 | 評価 |
|---|---|:---:|
| 1. 全期間 shadow N / WR / Wilson_lo | **60/33.3%/0.227** | 🟠 |
| 2. spread-adjusted EV (entry_price 基準) | **-1.29p** | 🔴 |
| 3. Profit Factor | **0.65** | 🔴 |
| 4. Kelly fraction | **0.000** | 🔴 |
| 5. 直近 30d vs 全期間 (drift detection) | **30d N=47 WR=34.0% EV=-1.19p deltaWR=+0.7%** | 🔴 |
| 6. session × direction WR matrix | **n/a** | 🔴 |
| 7. regime (ADX/ATR quartile) WR matrix | **trend_rebound_ATRQ2 N=12 WR=50.0%** | 🟢 |
| 8. Walk-Forward (3-fold) EV+ count | **0/3** | 🔴 |

**3. 設計欠陥候補**:
- `trend_rebound` aggregate spread-adjusted EV is non-positive (-1.29p), so raw WR is not paying for friction.
- `trend_rebound` PF < 1.0 after entry-price/spread basis; TP/SL geometry or direction filter needs redesign.
- No pre-registered session × direction cell reached N>=10 and WR>=50%; timing/direction thesis is not isolating edge.

**4. 再設計案 (新 PRIME 候補 cell; locked before stats)**:
- **Cell 1**: trend_rebound_ALL, predicate=`entry_type == strategy`, expected_N>=20
- **Cell 2**: trend_rebound_ATRQ2, predicate=`ATR quartile == Q2`, expected_N>=20
- Bonferroni alpha contribution uses global m_total=9 (alpha=0.005556)

**5. 候補 cell 実測**:
| cell | N | WR | Wlo | Fisher p | Bonf p×m | FDR q10 | WF | Kelly | spread-adj EV | verdict |
|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|:---:|
| trend_rebound_ALL | 60 | 33.3% | 0.227 | 0.154 | 1 | N | 0/3 | 0.000 | -1.29 | REJECT |
| trend_rebound_ATRQ2 | 12 | 50.0% | 0.254 | 0.0724 | 0.652 | N | 1/3 | 0.005 | +0.05 | REJECT |

**6. PRIME v2 への組込み推奨**:
- SELECTED cell なし。PRIME v2 への組込みは REJECT; shadow N+30d で再評価。

### Strategy: dt_sr_channel_reversal

**Verdict**: THESIS_VALID + DESIGN_BROKEN

**1. 思想 (Thesis)**: DT SR/Channel Reversal。15m 足の SR または parallel channel 境界付近で、RSI/MACD-H 反転を伴うバウンスを狙う。

**2. 8 軸監査**:
| 軸 | 値 | 評価 |
|---|---|:---:|
| 1. 全期間 shadow N / WR / Wilson_lo | **106/33.0%/0.248** | 🟠 |
| 2. spread-adjusted EV (entry_price 基準) | **-4.28p** | 🔴 |
| 3. Profit Factor | **0.44** | 🔴 |
| 4. Kelly fraction | **0.000** | 🔴 |
| 5. 直近 30d vs 全期間 (drift detection) | **30d N=68 WR=33.8% EV=-3.82p deltaWR=+0.8%** | 🔴 |
| 6. session × direction WR matrix | **n/a** | 🔴 |
| 7. regime (ADX/ATR quartile) WR matrix | **dt_sr_channel_reversal_ADXQ2 N=10 WR=60.0%** | 🟢 |
| 8. Walk-Forward (3-fold) EV+ count | **0/3** | 🔴 |

**3. 設計欠陥候補**:
- `dt_sr_channel_reversal` aggregate spread-adjusted EV is non-positive (-4.28p), so raw WR is not paying for friction.
- `dt_sr_channel_reversal` PF < 1.0 after entry-price/spread basis; TP/SL geometry or direction filter needs redesign.
- No pre-registered session × direction cell reached N>=10 and WR>=50%; timing/direction thesis is not isolating edge.

**4. 再設計案 (新 PRIME 候補 cell; locked before stats)**:
- **Cell 1**: dt_sr_channel_reversal_ALL, predicate=`entry_type == strategy`, expected_N>=20
- **Cell 2**: dt_sr_channel_reversal_ADXQ2, predicate=`ADX quartile == Q2`, expected_N>=20
- Bonferroni alpha contribution uses global m_total=9 (alpha=0.005556)

**5. 候補 cell 実測**:
| cell | N | WR | Wlo | Fisher p | Bonf p×m | FDR q10 | WF | Kelly | spread-adj EV | verdict |
|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|:---:|
| dt_sr_channel_reversal_ALL | 106 | 33.0% | 0.248 | 0.087 | 0.783 | N | 0/3 | 0.000 | -4.28 | REJECT |
| dt_sr_channel_reversal_ADXQ2 | 10 | 60.0% | 0.313 | 0.0272 | 0.244 | Y | 2/3 | 0.077 | +2.32 | REJECT |

**6. PRIME v2 への組込み推奨**:
- SELECTED cell なし。PRIME v2 への組込みは REJECT; shadow N+30d で再評価。

### Strategy: wick_imbalance_reversion

**Verdict**: THESIS_VALID + DESIGN_BROKEN

**1. 思想 (Thesis)**: Wick Imbalance Reversion。直近ローソク足の上ヒゲ/下ヒゲ偏りが極端な場合、流動性消費後の反対方向への平均回帰を狙う。

**2. 8 軸監査**:
| 軸 | 値 | 評価 |
|---|---|:---:|
| 1. 全期間 shadow N / WR / Wilson_lo | **70/38.6%/0.280** | 🟢 |
| 2. spread-adjusted EV (entry_price 基準) | **-2.88p** | 🔴 |
| 3. Profit Factor | **0.66** | 🔴 |
| 4. Kelly fraction | **0.000** | 🔴 |
| 5. 直近 30d vs 全期間 (drift detection) | **30d N=69 WR=39.1% EV=-2.88p deltaWR=+0.6%** | 🔴 |
| 6. session × direction WR matrix | **n/a** | 🔴 |
| 7. regime (ADX/ATR quartile) WR matrix | **n/a** | 🔴 |
| 8. Walk-Forward (3-fold) EV+ count | **1/3** | 🔴 |

**3. 設計欠陥候補**:
- `wick_imbalance_reversion` aggregate spread-adjusted EV is non-positive (-2.88p), so raw WR is not paying for friction.
- `wick_imbalance_reversion` PF < 1.0 after entry-price/spread basis; TP/SL geometry or direction filter needs redesign.
- No pre-registered session × direction cell reached N>=10 and WR>=50%; timing/direction thesis is not isolating edge.
- No ADX/ATR quartile cell reached N>=10 and WR>=50%; regime filter is not yet separating winners.

**4. 再設計案 (新 PRIME 候補 cell; locked before stats)**:
- **Cell 1**: wick_imbalance_reversion_ALL, predicate=`entry_type == strategy`, expected_N>=20
- Bonferroni alpha contribution uses global m_total=9 (alpha=0.005556)

**5. 候補 cell 実測**:
| cell | N | WR | Wlo | Fisher p | Bonf p×m | FDR q10 | WF | Kelly | spread-adj EV | verdict |
|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|:---:|
| wick_imbalance_reversion_ALL | 70 | 38.6% | 0.280 | 0.0195 | 0.175 | Y | 1/3 | 0.000 | -2.88 | REJECT |

**6. PRIME v2 への組込み推奨**:
- SELECTED cell なし。PRIME v2 への組込みは REJECT; shadow N+30d で再評価。

## Aggregate verdict
| strategy | thesis | design | shadow N | best cell | verdict | proposed tier |
|---|---|---|---:|---|---|---|
| gbp_deep_pullback | VALID | VALID_NEEDS_N | 12 | gbp_deep_pullback_ALL | THESIS_VALID + DESIGN_VALID_NEEDS_N | REJECT |
| orb_trap | VALID | VALID_NEEDS_N | 19 | orb_trap_ALL | THESIS_VALID + DESIGN_VALID_NEEDS_N | REJECT |
| ob_retest | VALID | VALID_NEEDS_N | 40 | ob_retest_OVERLAP_BUY | THESIS_VALID + DESIGN_VALID_NEEDS_N | REJECT |
| trend_rebound | INVALID | N/A | 60 | trend_rebound_ATRQ2 | THESIS_INVALID | REJECT |
| dt_sr_channel_reversal | VALID | BROKEN | 106 | dt_sr_channel_reversal_ADXQ2 | THESIS_VALID + DESIGN_BROKEN | REJECT |
| wick_imbalance_reversion | VALID | BROKEN | 70 | wick_imbalance_reversion_ALL | THESIS_VALID + DESIGN_BROKEN | REJECT |

## PRIME v2 candidate proposal
- No `_PRIMES` deltas recommended. All design-driven v2 cells are REJECT under corrected m_total Bonferroni.

## Next steps
- NULL result retained. Future re-eval @ shadow N+30d with the same design-driven cell lock.
- Near-miss cells (N>=10 and uncorrected Fisher p<0.05):
  - ob_retest_OVERLAP_BUY: N=11 WR=63.6% Fisher p=0.0111 EV=+13.73p
  - wick_imbalance_reversion_ALL: N=70 WR=38.6% Fisher p=0.0195 EV=-2.88p
  - ob_retest_ALL: N=40 WR=42.5% Fisher p=0.0218 EV=+2.68p
  - dt_sr_channel_reversal_ADXQ2: N=10 WR=60.0% Fisher p=0.0272 EV=+2.32p
