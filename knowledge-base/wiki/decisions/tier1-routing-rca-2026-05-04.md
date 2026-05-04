# Tier 1 LIVE routing anomaly RCA - 2026-05-04

Verdict: ACCEPT
Top block reason: shadow_tracking (74 / 77, 96.10%)
Pass-through rate: matched filled/sent 15 / 15 = 100.00%
Audited route-through rate: matched filled/(sent+blocked/skipped) 15 / 92 = 16.30%
Live-only top block reason: none (0 / 0, 0.00%)
Shadow/reference top block reason: shadow_tracking (74 / 77, 96.10%)

## Source / separation

- Source: `/tmp/oanda-audit-tier1-rca.json`
- `bridge_status='sent'` は strategy 名、`bridge_status='filled'` は OANDA mode 名の可能性があるため、GROUP BY 前に分離。
- `filled` は同一 `demo_trade_id` の `sent` 親 row へ解決してから cell に帰属。PYR 等の mode 名を cell 集計へ混入させない。
- `is_live=true` の sent/blocked は Live bucket、`is_live=false` の skipped は Shadow/reference bucket として分離。
- Status counts: {'blocked': 56, 'filled': 409, 'sent': 267, 'skipped': 3915}
- Non-live audit rows: 3971

## Machine summary

Cell: gbp_deep_pullback / GBP_USD sent=3 filled=3 live_block=0 shadow_block=3 route_through=50.00% top=shadow_tracking (3 / 3, 100.00%)
Cell: trendline_sweep / GBP_USD sent=3 filled=3 live_block=0 shadow_block=8 route_through=27.27% top=shadow_tracking (8 / 8, 100.00%)
Cell: trendline_sweep / EUR_USD sent=0 filled=0 live_block=0 shadow_block=4 route_through=0.00% top=shadow_tracking (4 / 4, 100.00%)
Cell: session_time_bias / USD_JPY sent=0 filled=0 live_block=0 shadow_block=0 route_through=0.00% top=none (0 / 0, 0.00%)
Cell: session_time_bias / EUR_USD sent=0 filled=0 live_block=0 shadow_block=10 route_through=0.00% top=shadow_tracking (10 / 10, 100.00%)
Cell: session_time_bias / GBP_USD sent=7 filled=7 live_block=0 shadow_block=16 route_through=30.43% top=shadow_tracking (14 / 16, 87.50%)
Cell: xs_momentum / USD_JPY sent=0 filled=0 live_block=0 shadow_block=14 route_through=0.00% top=shadow_tracking (13 / 14, 92.86%)
Cell: xs_momentum / EUR_USD sent=0 filled=0 live_block=0 shadow_block=19 route_through=0.00% top=shadow_tracking (19 / 19, 100.00%)
Cell: doji_breakout / USD_JPY sent=2 filled=2 live_block=0 shadow_block=3 route_through=40.00% top=shadow_tracking (3 / 3, 100.00%)
Cell: squeeze_release_momentum / EUR_USD sent=0 filled=0 live_block=0 shadow_block=0 route_through=0.00% top=none (0 / 0, 0.00%)

## Cell pass-through

| Cell | sent N | filled N | live blocked/skipped N | shadow/reference blocked N | sent-fill | route-through | top block reason |
|---|---:|---:|---:|---:|---:|---:|---|
| gbp_deep_pullback / GBP_USD | 3 | 3 | 0 | 3 | 100.00% | 50.00% | shadow_tracking (3 / 3, 100.00%) |
| trendline_sweep / GBP_USD | 3 | 3 | 0 | 8 | 100.00% | 27.27% | shadow_tracking (8 / 8, 100.00%) |
| trendline_sweep / EUR_USD | 0 | 0 | 0 | 4 | 0.00% | 0.00% | shadow_tracking (4 / 4, 100.00%) |
| session_time_bias / USD_JPY | 0 | 0 | 0 | 0 | 0.00% | 0.00% | none (0 / 0, 0.00%) |
| session_time_bias / EUR_USD | 0 | 0 | 0 | 10 | 0.00% | 0.00% | shadow_tracking (10 / 10, 100.00%) |
| session_time_bias / GBP_USD | 7 | 7 | 0 | 16 | 100.00% | 30.43% | shadow_tracking (14 / 16, 87.50%) |
| xs_momentum / USD_JPY | 0 | 0 | 0 | 14 | 0.00% | 0.00% | shadow_tracking (13 / 14, 92.86%) |
| xs_momentum / EUR_USD | 0 | 0 | 0 | 19 | 0.00% | 0.00% | shadow_tracking (19 / 19, 100.00%) |
| doji_breakout / USD_JPY | 2 | 2 | 0 | 3 | 100.00% | 40.00% | shadow_tracking (3 / 3, 100.00%) |
| squeeze_release_momentum / EUR_USD | 0 | 0 | 0 | 0 | 0.00% | 0.00% | none (0 / 0, 0.00%) |

## Pre/post-cutoff comparison

| Cell | period | sent N | filled N | live block N | shadow/ref block N | route-through | top block reason |
|---|---|---:|---:|---:|---:|---:|---|
| gbp_deep_pullback / GBP_USD | post | 3 | 3 | 0 | 3 | 50.00% | shadow_tracking (3 / 3, 100.00%) |
| trendline_sweep / GBP_USD | post | 3 | 3 | 0 | 8 | 27.27% | shadow_tracking (8 / 8, 100.00%) |
| trendline_sweep / EUR_USD | post | 0 | 0 | 0 | 4 | 0.00% | shadow_tracking (4 / 4, 100.00%) |
| session_time_bias / EUR_USD | post | 0 | 0 | 0 | 10 | 0.00% | shadow_tracking (10 / 10, 100.00%) |
| session_time_bias / GBP_USD | post | 7 | 7 | 0 | 16 | 30.43% | shadow_tracking (14 / 16, 87.50%) |
| xs_momentum / USD_JPY | post | 0 | 0 | 0 | 14 | 0.00% | shadow_tracking (13 / 14, 92.86%) |
| xs_momentum / EUR_USD | post | 0 | 0 | 0 | 19 | 0.00% | shadow_tracking (19 / 19, 100.00%) |
| doji_breakout / USD_JPY | post | 2 | 2 | 0 | 3 | 40.00% | shadow_tracking (3 / 3, 100.00%) |

## Gate block distribution

| reason | N | share |
|---|---:|---:|
| shadow_tracking | 74 | 96.10% |
| mode_daytrade_gbpusd_not_allowed | 2 | 2.60% |
| pair_demoted | 1 | 1.30% |

## Live-only gate block distribution

| reason | N | share |
|---|---:|---:|
| none | 0 | 0.00% |

## Shadow/reference block distribution

| reason | N | share |
|---|---:|---:|
| shadow_tracking | 74 | 96.10% |
| mode_daytrade_gbpusd_not_allowed | 2 | 2.60% |
| pair_demoted | 1 | 1.30% |

## Hypothesis verdicts

- H1: ACCEPT - Top block reason=shadow_tracking (74/77, 96.10%)
- H2: ACCEPT - pre/post table above shows the post-cutoff blocker concentration; compare route-through and top reason by period.
- H3: REJECT - 対象 cell の route rows N=92、sent rows N=15。

## Recommended fix

- R3 patch candidate: `shadow_tracking` route を target cell 限定で再評価。Live sent→filled は通っているため、routing gate 緩和ではなく demotion/shadow dispatch と edge erosion の整合を次 task で検証。
