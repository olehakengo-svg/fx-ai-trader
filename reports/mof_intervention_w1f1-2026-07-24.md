# W1-F1: MoF FX Intervention History — Data Fetch + Design Feasibility (2026-07-24)

## Sources
- **Full daily history CSV** (1991-04〜, official, CP932): `https://www.mof.go.jp/policy/international_policy/reference/feio/foreign_exchange_intervention_operations.csv`
  - Note: the task URL `.../feio/index.htm` is 404 — current index is `.../feio/index.html` → `data/index.html` links the CSV directly.
- **Monthly aggregate disclosures** (amount only, no dates/pair): `.../feio/data/monthly/index.html`
- Fetch/normalize script: `tools/mof_interventions_fetch.py` (re-runnable; cross-validates daily sums vs quarterly totals)
- Output: `data/external/mof_interventions.csv` (383 daily rows + 1 pending monthly-aggregate row)
- Stats JSON: `bt-results/mof_intervention_w1f1-2026-07-24.json`

## Data validation
| Check | Result |
|---|---|
| Daily events parsed | 383 (1991-05-13 → 2024-07-12) |
| Quarterly cross-check | Σdaily 1,103,777 oku vs Σquarterly 1,103,775 oku (diff 2 oku ≈ rounding, note2) |
| Required 2022/2024 dates | all 7 present (09-22/10-21/10-24/04-29/05-01/07-11/07-12) |
| Encoding | CP932; amounts 億円 → converted ×0.1 to ¥billions |
| Pairs | USD/JPY 358, EUR/JPY 18, USD/IDR 5, USD/DEM 1, DEM/JPY 1 |
| Directions | sell_JPY_buy_USD 319, sell_USD_buy_JPY 39, sell_JPY_buy_EUR 18, other 7 |

## 2010+ events (15 daily rows + 1 pending aggregate)
| date | pair | direction | ¥bn |
|---|---|---|---|
| 2010-09-15 | USD/JPY | sell_JPY_buy_USD | 2,124.9 |
| 2011-03-18 | USD/JPY | sell_JPY_buy_USD | 692.5 |
| 2011-08-04 | USD/JPY | sell_JPY_buy_USD | 4,512.9 |
| 2011-10-31 | USD/JPY | sell_JPY_buy_USD | 8,072.2 |
| 2011-11-01..04 | USD/JPY | sell_JPY_buy_USD | 282.6 / 227.9 / 202.8 / 306.2 (covert) |
| 2022-09-22 | USD/JPY | sell_USD_buy_JPY | 2,838.2 |
| 2022-10-21 | USD/JPY | sell_USD_buy_JPY | 5,620.2 |
| 2022-10-24 | USD/JPY | sell_USD_buy_JPY | 729.6 |
| 2024-04-29 | USD/JPY | sell_USD_buy_JPY | 5,918.5 |
| 2024-05-01 | USD/JPY | sell_USD_buy_JPY | 3,870.0 |
| 2024-07-11 | USD/JPY | sell_USD_buy_JPY | 3,167.8 |
| 2024-07-12 | USD/JPY | sell_USD_buy_JPY | 2,367.0 |
| **2026-04-28..05-27 (window)** | UNDISCLOSED | undisclosed_monthly_aggregate | **11,734.9** |

**2025–2026 status**: 2025 all four quarters = 0. **2026: one large episode exists** — the monthly disclosure for 2026-04-28..2026-05-27 shows ¥11.73T (largest single-window total on record); daily dates / pair / direction are NOT yet disclosed (Q2-2026 quarterly daily breakdown expected ~2026-08, based on Q1-2026 publish date 2026-05-12). Windows 03-30..04-27 and 05-28..06-26 = 0.

## Episode clustering (gap ≥ 30 days = new episode)
- All history: 383 events → 33 episodes. Dense mass is 1993–2004 (319 yen-**selling** days), zero events 2005–2009 and 2012–2021.
- 2010+: 15 events → **7 episodes** (2010-09, 2011-03, 2011-08, 2011-10/11, 2022-09/10, 2024-04/05, 2024-07) + 1 pending 2026 episode.
- Modern yen-**buying** regime (matches current market structure): **7 daily events in 3 episodes** (2022+), all USD/JPY.

## Design feasibility verdict
**Temporal explore/OOS split: NOT possible (as expected).**
- Usable modern events (2022+, within 12y parquet coverage, current friction regime): N=7 days in 3 episodes. Any temporal split yields ≤2 episodes per side; within-episode days are strongly correlated (same macro regime, back-to-back days). Zero statistical power; split boundary would be arbitrary and episode-confounded.
- Adding 2010–2011 (N=15, 7 episodes) mixes opposite intervention direction (yen-selling vs yen-buying) and a different microstructure era — not a valid OOS pool for a yen-buying hypothesis.

**Recommended design** (for W1-F2, not run here):
1. **All-event descriptive study with permutation null**: exit-free forward MFE/MAE + net move at h ∈ {4h,12h,24h,72h,120h} anchored at event-day boundaries; null = matched placebo days (same pair, weekday, vol regime), permutation p. Cluster by episode (block permutation / episode-level resampling) — days within an episode are one draw, effective N ≈ 3, so report as descriptive only, no Bonferroni-grade claim possible.
2. **Forward pre-reg (genuine OOS)**: LOCK hypothesis + measurement spec BEFORE the Q2-2026 quarterly daily disclosure (~2026-08). The pending 2026 episode (¥11.73T, dates unknown to us now) then serves as true out-of-sample data — likely 2–5 event days.
3. **Lookahead cautions**: (a) event granularity = calendar day, no intraday timestamp → anchor forward windows at next Tokyo-day open, never intra-event-day; (b) interventions are endogenous (triggered by price) → an "event-day return" is not tradeable unless detection is real-time; 2022-09-22 was officially confirmed same day, 2022-10 and 2011-11 were covert; (c) a disclosure-time (publication-date) design is the only fully tradeable variant.

## Not done here (per task scope)
No edge analysis, no MFE/MAE computation, no bootstrap — W1-F1 is data + feasibility only.
