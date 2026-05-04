# Tier 1 LIVE routing anomaly RCA - 2026-05-04

Verdict: NEEDS_MORE_EVIDENCE
Top block reason: none (0 / 0, 0.00%)
Pass-through rate: 15 / 15 = 100.00%
Sent-to-fill rate: 15 / 15 = 100.00%

## Source / separation

- Source: `/tmp/oanda-audit-tier1-rca.json`
- `bridge_status='sent'` は strategy 名、`bridge_status='filled'` は OANDA mode 名の可能性があるため、GROUP BY 前に分離。
- `filled` は同一 `demo_trade_id` の `sent` 親 row へ解決してから cell に帰属。
- `blocked/skipped` の `block_reason` は gate 分布用。Shadow/非live row (`is_live=false`) は除外。
- Status counts: {'blocked': 56, 'filled': 409, 'sent': 267, 'skipped': 3865}
- Excluded non-live audit rows: 3921

## Cell pass-through

| Cell | signal N | sent N | filled N | blocked/skipped N | pass-through | sent-fill | top block reason |
|---|---:|---:|---:|---:|---:|---:|---|
| gbp_deep_pullback / GBP_USD | 3 | 3 | 3 | 0 | 100.00% | 100.00% | none (0 / 0, 0.00%) |
| trendline_sweep / GBP_USD | 3 | 3 | 3 | 0 | 100.00% | 100.00% | none (0 / 0, 0.00%) |
| trendline_sweep / EUR_USD | 0 | 0 | 0 | 0 | 0.00% | 0.00% | none (0 / 0, 0.00%) |
| session_time_bias / USD_JPY | 0 | 0 | 0 | 0 | 0.00% | 0.00% | none (0 / 0, 0.00%) |
| session_time_bias / EUR_USD | 0 | 0 | 0 | 0 | 0.00% | 0.00% | none (0 / 0, 0.00%) |
| session_time_bias / GBP_USD | 7 | 7 | 7 | 0 | 100.00% | 100.00% | none (0 / 0, 0.00%) |
| xs_momentum / USD_JPY | 0 | 0 | 0 | 0 | 0.00% | 0.00% | none (0 / 0, 0.00%) |
| xs_momentum / EUR_USD | 0 | 0 | 0 | 0 | 0.00% | 0.00% | none (0 / 0, 0.00%) |
| doji_breakout / USD_JPY | 2 | 2 | 2 | 0 | 100.00% | 100.00% | none (0 / 0, 0.00%) |
| squeeze_release_momentum / EUR_USD | 0 | 0 | 0 | 0 | 0.00% | 0.00% | none (0 / 0, 0.00%) |

## Pre/post-cutoff comparison

| Cell | period | signal N | sent N | filled N | blocked/skipped N | pass-through | top block reason |
|---|---|---:|---:|---:|---:|---:|---|
| gbp_deep_pullback / GBP_USD | post | 3 | 3 | 3 | 0 | 100.00% | none (0 / 0, 0.00%) |
| trendline_sweep / GBP_USD | post | 3 | 3 | 3 | 0 | 100.00% | none (0 / 0, 0.00%) |
| session_time_bias / GBP_USD | post | 7 | 7 | 7 | 0 | 100.00% | none (0 / 0, 0.00%) |
| doji_breakout / USD_JPY | post | 2 | 2 | 2 | 0 | 100.00% | none (0 / 0, 0.00%) |

## Gate block distribution

| reason | N | share |
|---|---:|---:|
| none | 0 | 0.00% |

## Hypothesis verdicts

- H1: NEEDS_MORE_EVIDENCE - 対象 cell の blocked/skipped 行が0で、gate別 block 比率を特定できない。
- H2: pre/post table above. 判定は top reason と share の期間差を参照。
- H3: REJECT - 対象 cell の signal-path rows N=15。

## Recommended fix

- 別 task: hour bucket / session / instrument side を追加した second-pass RCA。単一 gate 支配の証拠がまだ不足。
