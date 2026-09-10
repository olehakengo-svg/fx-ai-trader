# G0 RT 実測 — commodity_cross_range_mr (#21) — 2026-08-03

> rule:R3 摩擦実測 (fwd/シグナル非接触)。凍結仕様: [[commodity-cross-g0-rt-freeze-2026-08-03]]。60 営業日 / M5 BA candles / OANDA live。

| pair | n_bars | p50 | p75 | p90 | p99 | rollover p75 (21-22) | liquid p75 (07-16) | stressed_RT | verdict |
|---|---|---|---|---|---|---|---|---|---|
| AUD_NZD | 17848 | 2.60 | 2.80 | 3.00 | 18.75 | 12.70 | 2.70 | **3.80** | PASS |
| AUD_CAD | 17853 | 2.50 | 2.70 | 3.10 | 15.45 | 11.60 | 2.50 | **3.70** | PASS |
| NZD_CAD | 17849 | 2.70 | 2.90 | 3.20 | 17.60 | 12.10 | 2.70 | **3.90** | PASS |
| AUD_USD | 17852 | 1.30 | 1.40 | 1.50 | 6.40 | 4.30 | 1.40 | **2.40** | (anchor) |
| USD_JPY | 17851 | 1.60 | 1.70 | 1.90 | 8.60 | 6.00 | 1.60 | **2.70** | (anchor) |

## Family verdict: **PROCEED (>=1 PASS)**

anchor sanity: OK
