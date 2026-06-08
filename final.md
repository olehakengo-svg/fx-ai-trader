# Edge Cell Filter MASSIVE 12y BT - Stage B

Generated: 2026-06-08T12:52:10.369494+00:00

BT guards: `BT_REQUIRE_MASSIVE_CACHE=1`, native MASSIVE parquets only, no resample, no Yahoo fallback.
Gate: `PROMOTE_SHADOW` requires PF>=1.05, WFO>=2/3 PF>1, Bonferroni m=12 Wilson_lo>=0.30. PF<1.0 is `REJECT`.

## Verdicts

| Strategy | Pair | TF | Baseline N | Baseline PF | Baseline mean | Proposed N | Proposed PF | Proposed mean | Wilson_lo Bonf m12 | WFO PF>1 | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| session_time_bias | EUR_USD | 15m | 7939 | 0.936286 | -0.468 | 5152 | 0.939658 | -0.545 | 0.422 | 0/3 | REJECT |
| session_time_bias | GBP_USD | 15m | 8165 | 0.850175 | -1.550 | 5174 | 0.852125 | -1.865 | 0.407 | 0/3 | REJECT |
| session_time_bias | USD_JPY | 5m | 11700 | 0.700119 | -1.582 | 0 | 0.0 | 0.000 | 0.000 | 0/3 | REJECT |
| bb_rsi_reversion | USD_JPY | 5m | 27585 | 0.652176 | -1.426 | 27585 | 0.655804 | -1.142 | 0.284 | 0/3 | REJECT |
| bb_rsi_reversion | EUR_USD | 15m | 8662 | 0.725841 | -1.230 | 0 | 0.0 | 0.000 | 0.000 | 0/3 | REJECT |
| bb_rsi_reversion | GBP_USD | 15m | 8374 | 0.769979 | -1.316 | 0 | 0.0 | 0.000 | 0.000 | 0/3 | REJECT |
| bb_rsi_reversion | USD_CHF | 1h | 543 | 0.71202 | -2.226 | 0 | 0.0 | 0.000 | 0.000 | 0/3 | REJECT |
| bb_rsi_reversion | EUR_JPY | 15m | 8846 | 0.708821 | -2.181 | 0 | 0.0 | 0.000 | 0.000 | 0/3 | REJECT |
| bb_rsi_reversion | USD_CAD | 1h | 517 | 0.848459 | -1.424 | 0 | 0.0 | 0.000 | 0.000 | 0/3 | REJECT |

## Decision

- `session_time_bias`: REJECT all tested pairs. Proposed PF remains <1 on EUR_USD and GBP_USD; USD_JPY has zero proposed trades because the LDN filter is incompatible with the Tokyo-only STB USD_JPY bias.
- `bb_rsi_reversion`: REJECT all tested pairs. USD_JPY did not verify as positive on 12y native 5m (PF=0.655804, WFO 0/3); GBP_USD and USD_CHF baseline checks are catastrophic and are correctly killed by the proposed whitelist.
- Coverage caveat: USD_JPY 12y native coverage is available only as native 5m. USD_CHF and USD_CAD have no native 15m 12y cache and are included with native H1 coverage failure rather than synthetic data.

## 40-day Production Comparison

- `session_time_bias` production baseline: N=396, WR=30.1%, mean=-2.06p, PF=0.601. Proposed in-sample cell: N=126, WR=45.2%, mean=+0.93p.
- `bb_rsi_reversion` production baseline: N=239, WR=30.1%, mean=-0.77p, PF=0.688. Proposed in-sample USD_JPY: N=96, WR=43.8%, mean=+0.10p, PF=1.04.
